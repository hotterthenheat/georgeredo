"""
dr_gce.py — the DR-GCE section-7 gate, exactly as GATE_PREREG.md pins it. Files only; no vendor call; deterministic
(the baseline and the bootstrap are seeded). Section numbers are the prereg's.

  python3 dr_gce.py            # signals, outcomes, the 500-draw baseline, the bootstrap -> out/
"""
from __future__ import annotations

import json
import math
import sys
from functools import lru_cache
import multiprocessing as mp
from pathlib import Path

import numpy as np
import polars as pl
from scipy.special import ndtr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import guard as G  # noqa: E402  (wraps polars' readers first)

REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass scanner'))
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402
import scanner_lib as S  # noqa: E402  (chain, forward_im, occ)

OUT = HERE / 'out'
SP = S.SP
THETA = S.THETA
NBAR = 390
R = 0.045
MIN_YEAR = 525600.0
SQ = math.sqrt(252 * 390)
TR_CLOCK = math.sqrt(252 * 390 / MIN_YEAR)        # Amendment 1: sigma_ATM on the trading-minute clock
MODES = (1, 2)
W1 = ((15, 135), (240, 345))
W2 = ((30, 315),)
SEED = 20261023
TRIALS = 500


def sessions() -> list[str]:
    return [d for d in AL.expected_sessions('2023-11-21', '2026-10-09') if not G.held_out(d)]


def all_tdays() -> list[str]:
    return [d for d in AL.weekdays('2023-01-01', '2026-10-09') if d not in AL.NYSE_HOLIDAYS]


TD = all_tdays()
TDI = {d: i for i, d in enumerate(TD)}


def prev_tday(d: str) -> str:
    return TD[TDI[d] - 1]


def in_win(t: int, wins) -> bool:
    return any(a <= t <= b for a, b in wins)


# ---- inputs ----------------------------------------------------------------------------------------------------------------

def spx_closes(d: str) -> np.ndarray:
    """S[s], s = 0..389: the print stamped s + 1 (the close of bar s)"""
    x = pl.read_parquet(THETA / 'data' / 'index' / 'SPX' / f'{d}.parquet').with_columns(S._mcol().alias('m'))
    x = x.filter((pl.col('m') >= 1) & (pl.col('m') <= NBAR) & pl.col('price').is_not_null() & pl.col('price').is_not_nan())
    c = np.full(NBAR, np.nan)
    c[x['m'].to_numpy() - 1] = x['price'].to_numpy().astype(float)
    return c


def spy_bars(d: str):
    x = pl.read_parquet(THETA / 'data' / 'underlying' / 'SPY' / f'{d}.parquet').with_columns(S._mcol().alias('m'))
    x = x.filter((pl.col('m') >= 0) & (pl.col('m') < NBAR))
    out = []
    for col in ('open', 'high', 'low', 'close', 'volume'):
        a = np.full(NBAR, np.nan)
        a[x['m'].to_numpy()] = x[col].fill_null(np.nan).to_numpy().astype(float)
        out.append(a)
    return tuple(out)


def oi_arrays(d: str, K: np.ndarray):
    p = S.OI_DIR / 'SPX' / f'{d}.parquet'
    x = pl.read_parquet(p, columns=['option_symbol', 'open_interest'])
    oi = {a: int(b) for a, b in x.iter_rows() if b is not None}
    return (np.array([oi.get(S.occ('SPXW', d, 0, k), 0) for k in K], float),
            np.array([oi.get(S.occ('SPXW', d, 1, k), 0) for k in K], float))


class Day:
    """one session's inputs; `cut` (a chain row) blanks every input after it (the lookahead rebuild)"""

    def __init__(self, d: str, cut: int | None = None, peek: int = 0):
        self.d = d
        Sx = spx_closes(d)
        O, H, L, C, V = spy_bars(d)
        K, bid, ask = S.chain('SPXW', d)
        bid, ask = bid.copy(), ask.copy()
        if peek:                                 # the control: reads `peek` minutes ahead (a deliberate lookahead)
            Sx = np.r_[Sx[peek:], np.full(peek, np.nan)]
        if cut is not None:                      # known at chain row `cut` = minute cut: bars 0..cut-1, rows 0..cut
            for a in (Sx, O, H, L, C, V):
                a[cut:] = np.nan
            bid[cut + 1:] = np.nan
            ask[cut + 1:] = np.nan
        self.S, self.O, self.H, self.L, self.C, self.V = Sx, O, H, L, C, V
        self.K, self.bid, self.ask = K, bid, ask
        self.oiC, self.oiP = oi_arrays(d, K)
        tp = (H + L + C) / 3.0
        ok = np.isfinite(tp) & np.isfinite(V)
        num = np.cumsum(np.where(ok, tp * V, 0.0))
        den = np.cumsum(np.where(ok, V, 0.0))
        self.vwap_spy = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
        self.vwap = self.vwap_spy * Sx / C
        # returns: today's r_j (j = 1..389), preceded by the previous trading day's returns when it is an exploration day
        r_today = np.r_[np.nan, np.log(Sx[1:] / Sx[:-1])]
        p = prev_tday(d)
        if not G.held_out(p):
            Sp = spx_closes(p)
            rp = np.log(Sp[1:] / Sp[:-1])
            self.r_prev = rp[-60:]
        else:
            self.r_prev = np.zeros(0)
        self.r = r_today
        self._sig = {}
        self._book = {}

    # 3.1
    def sigma(self, t: int) -> float:
        if t in self._sig:
            return self._sig[t]
        today = self.r[1:t + 1]
        w = np.r_[self.r_prev, today][-60:] if today.size < 60 else today[-60:]
        v = float('nan')
        if w.size == 60:
            w = w[np.isfinite(w)]
            if w.size >= 50:
                v = 1.4826 * float(np.median(np.abs(w - np.median(w))))
                v = v if v > 0 else float('nan')
        self._sig[t] = v
        return v

    def zvel(self, t: int) -> float:
        s = self.sigma(t)
        if t < 3 or not np.isfinite(s):
            return float('nan')
        return math.log(self.S[t] / self.S[t - 3]) / (math.sqrt(3) * s)

    def vol_ok(self, t: int) -> bool:
        if t < 15:
            return False
        prior = self.V[max(0, t - 30):t]
        prior = prior[np.isfinite(prior)]
        if prior.size < 15 or not np.isfinite(self.V[t]):
            return False
        return self.V[t] >= 1.8 * float(np.median(prior)) - 1e-9

    # 3.2 / 3.3 — the book at bar t, read on chain row t + 1
    def book(self, t: int):
        if t in self._book:
            return self._book[t]
        self._book[t] = b = book_of(self, t + 1, float(self.S[t]))
        return b


# ---- Black-76 --------------------------------------------------------------------------------------------------------------

def _phi(x):
    return np.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def b76(F, K, T, v, call):
    sv = v * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * v * v * T) / sv
    d2 = d1 - sv
    df = math.exp(-R * T)
    c = df * (F * ndtr(d1) - K * ndtr(d2))
    return np.where(call, c, c - df * (F - K))


def b76_iv(price, F, K, T, call, it=60):
    price, K = np.asarray(price, float), np.asarray(K, float)
    call = np.broadcast_to(np.asarray(call, bool), K.shape)
    df = math.exp(-R * T)
    lo_b = df * np.where(call, np.maximum(F - K, 0), np.maximum(K - F, 0))
    up_b = df * np.where(call, F, K)
    ok = np.isfinite(price) & (price > lo_b + 1e-12) & (price < up_b) & (T > 0)
    a = np.full(K.shape, 1e-4)
    b = np.full(K.shape, 10.0)
    pr = np.where(ok, price, 0.0)
    for _ in range(it):
        m = 0.5 * (a + b)
        up = b76(F, K, T, m, call) > pr
        b = np.where(up, m, b)
        a = np.where(up, a, m)
    return np.where(ok, 0.5 * (a + b), np.nan)


def greeks(F, Sx, K, T, v, call):
    """spot delta and gamma per SPX point (Black-76 on F, dF/dS = F/S)"""
    sv = v * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * v * v * T) / sv
    df = math.exp(-R * T)
    q = F / Sx
    dl = df * np.where(call, ndtr(d1), ndtr(d1) - 1.0) * q
    gm = df * _phi(d1) / (F * sv) * q * q
    return dl, gm


def quotes(day: Day, m: int, r: int):
    b, a = day.bid[m, :, r], day.ask[m, :, r]
    ok = np.isfinite(a) & np.isfinite(b) & (a >= b) & (b > 0)
    return b, a, ok


def book_of(day: Day, m: int, St: float):
    """the GEX book at chain row m with spot St: dict or None (no forward / no spot)"""
    if not np.isfinite(St):
        return None
    fw = forward_cut(day, m)
    if fw is None:
        return None
    Ks, F, _ = fw
    T = (NBAR - m) / MIN_YEAR
    K = day.K
    band = np.abs(K - St) <= 0.025 * St + 1e-9
    ivs = []
    for r in (0, 1):
        b, a, ok = quotes(day, m, r)
        mid = np.where(ok & band, (a + b) / 2.0, np.nan)
        ivs.append(b76_iv(mid, F, K, T, r == 0))
    ivC, ivP = ivs
    iks = int(np.where(K == Ks)[0][0])
    sa = np.nanmean([ivC[iks], ivP[iks]]) if np.isfinite([ivC[iks], ivP[iks]]).any() else float('nan')

    def gex_at(x: np.ndarray) -> np.ndarray:
        """ΣGEX at each spot of x (sticky strike, F scales with spot)"""
        Fx = x * (F / St)
        tot = np.zeros(x.size)
        for iv, oi, sgn in ((ivC, day.oiC, 1.0), (ivP, day.oiP, -1.0)):
            use = band & np.isfinite(iv) & (oi > 0)
            if not use.any():
                continue
            kk, vv, oo = K[use][None, :], iv[use][None, :], oi[use][None, :]
            sv = vv * math.sqrt(T)
            d1 = (np.log(Fx[:, None] / kk) + 0.5 * vv * vv * T) / sv
            q = (Fx / x)[:, None]
            gm = math.exp(-R * T) * _phi(d1) / (Fx[:, None] * sv) * q * q
            tot += sgn * (oo * 100 * gm * (x[:, None] ** 2) * 0.01).sum(1)
        return tot

    # per strike at St
    gk = np.zeros(K.size)
    for iv, oi, sgn, call in ((ivC, day.oiC, 1.0, True), (ivP, day.oiP, -1.0, False)):
        use = band & np.isfinite(iv) & (oi > 0)
        if use.any():
            _, gm = greeks(F, St, K[use], T, iv[use], call)
            gk[use] += sgn * oi[use] * 100 * gm * St * St * 0.01
    tot0 = float(gk[band].sum())
    grid = np.arange(math.ceil(0.975 * St), math.floor(1.025 * St) + 1, 1.0)
    g = gex_at(grid)
    sgn = np.sign(g)
    cross = np.where((sgn[:-1] * sgn[1:] < 0) | (g[:-1] == 0))[0]
    if cross.size:
        zs = []
        for i in cross:
            g0, g1 = g[i], g[i + 1]
            zs.append(grid[i] if g0 == 0 else grid[i] + (grid[i + 1] - grid[i]) * abs(g0) / (abs(g0) + abs(g1)))
        zs = np.array(zs)
        Z = float(zs[np.argmin(np.abs(zs - St))])
        regime = -1 if St < Z else (1 if St > Z else 0)
    else:
        Z = float('nan')
        regime = -1 if tot0 < 0 else (1 if tot0 > 0 else 0)
    inb = np.where(band)[0]
    pos = [i for i in inb if gk[i] > 0]
    neg = [i for i in inb if gk[i] < 0]
    CW = float(K[max(pos, key=lambda i: gk[i])]) if pos else float('nan')
    PW = float(K[min(neg, key=lambda i: gk[i])]) if neg else float('nan')
    up = [i for i in pos if K[i] > St]
    dn = [i for i in neg if K[i] < St]
    CWa = float(K[max(up, key=lambda i: gk[i])]) if up else float('nan')
    PWb = float(K[min(dn, key=lambda i: gk[i])]) if dn else float('nan')
    near = [i for i in inb if abs(K[i] - St) <= 0.01 * St + 1e-9 and gk[i] != 0]
    Mg = float(K[max(near, key=lambda i: (abs(gk[i]), -abs(K[i] - St), -K[i]))]) if near else float('nan')
    return dict(F=F, Ks=Ks, sigma_atm=float(sa), Z=Z, regime=regime, tot=tot0, CW=CW, PW=PW, CWa=CWa, PWb=PWb, Mg=Mg,
                S=St)


def forward_cut(day: Day, m: int):
    """forward_im on the Day's own (possibly blanked) arrays"""
    cb, ca, pb, pa = day.bid[m, :, 0], day.ask[m, :, 0], day.bid[m, :, 1], day.ask[m, :, 1]
    with np.errstate(invalid='ignore'):
        cs = (cb > 0) & (ca > 0) & (ca >= cb)
        ps = (pb > 0) & (pa > 0) & (pa >= pb)
    both = cs & ps
    if not both.any():
        return None
    cm, pm = (cb + ca) / 2.0, (pb + pa) / 2.0
    dd = np.where(both, np.abs(cm - pm), np.inf)
    i = int(np.argmin(dd))
    IM = cm[i] + pm[i]
    if not (IM > 0):
        return None
    return float(day.K[i]), float(day.K[i] + cm[i] - pm[i]), float(IM)


def vol_ratio(day: Day, t: int, bk) -> float:
    s = day.sigma(t)
    return bk['sigma_atm'] * TR_CLOCK / (s * SQ) if bk and np.isfinite(s) and np.isfinite(bk['sigma_atm']) else float('nan')


# ---- the contract and G_max (7) ---------------------------------------------------------------------------------------------

def pick(day: Day, m: int, side: int, sig: float, St: float):
    fw = forward_cut(day, m)
    if fw is None:
        return None, 'no forward'
    _, F, _ = fw
    r = 0 if side > 0 else 1
    b, a, ok = quotes(day, m, r)
    T = (NBAR - m) / MIN_YEAR
    K = day.K
    mid = np.where(ok, (a + b) / 2.0, np.nan)
    iv = b76_iv(mid, F, K, T, side > 0)
    good = ok & np.isfinite(iv)
    if not good.any():
        return None, 'no standing quote'
    dl, gm = greeks(F, St, K, T, np.where(good, iv, 0.2), side > 0)
    spr = np.where(ok, (a - b) / np.where(ok, a, 1.0), np.inf)
    f = good & (np.abs(dl) >= 0.40 - 1e-12) & (np.abs(dl) <= 0.54 + 1e-12) & (spr <= 0.035 + 1e-12)
    if not f.any():
        return None, 'no contract'
    dS = 3.0 * sig * St
    T5 = max(T - 5.0 / MIN_YEAR, 0.0)
    v0 = b76(F, K, T, np.where(good, iv, 0.2), side > 0)
    if T5 > 0:
        v5 = b76(F, K, T5, np.where(good, iv, 0.2), side > 0)
    else:
        v5 = np.maximum((F - K) if side > 0 else (K - F), 0.0)
    th = np.abs(v0 - v5)
    CK = (np.abs(dl) * dS + 0.5 * gm * dS * dS) / (th + (a - b))
    cand = np.where(f)[0]
    i = max(cand, key=lambda k: (round(float(CK[k]), 12), -abs(K[k] - F), -K[k]))
    return dict(i=int(i), K=float(K[i]), r=r, ask=float(a[i]), bid=float(b[i]), delta=float(dl[i]), gamma=float(gm[i]),
                iv=float(iv[i]), CK=float(CK[i]), F=F), 'ok'


def struct_move(bk, side: int, mode: int, St: float) -> float:
    if mode == 1:
        w = bk['CWa'] if side > 0 else bk['PWb']
    else:
        w = bk['CW'] if side > 0 else bk['PW']
    cands = [x for x in (bk['Mg'], w) if np.isfinite(x) and (x - St) * side > 0]
    return min(abs(x - St) for x in cands) if cands else 0.025 * St


def outcome(day: Day, m: int, c: dict, gmax: float):
    """touch / stop on rows m+1..m+4: (touch 0/1, why, last row watched)"""
    i, r, A = c['i'], c['r'], c['ask']
    stop = 0.76 if gmax >= 0.85 else 0.82
    for k in range(m + 1, min(m + 4, NBAR) + 1):
        b = day.bid[k, i, r]
        if not np.isfinite(b):
            continue
        if b <= stop * A + 1e-9:
            return 0, 'stop', k
        if b >= 1.18 * A - 1e-9:
            return 1, 'touch', k
    return 0, 'none', min(m + 4, NBAR)


def trade(day: Day, mode: int, sbar: int, bbar: int, side: int):
    """entry on row sbar + 1; the book of bar bbar; δS from σ̂1m at sbar. (dict | None, reason)"""
    m = sbar + 1
    sig = day.sigma(sbar)
    St = float(day.S[sbar])
    if not (np.isfinite(sig) and np.isfinite(St)):
        return None, 'no sigma'
    bk = day.book(bbar)
    if bk is None:
        return None, 'no book'
    c, why = pick(day, m, side, sig, St)
    if c is None:
        return None, why
    dS = struct_move(bk, side, mode, float(day.S[bbar]))
    gmax = (abs(c['delta']) * dS + 0.5 * c['gamma'] * dS * dS) / c['ask']
    tch, how, last = outcome(day, m, c, gmax)
    return dict(d=day.d, mode=mode, sbar=sbar, bbar=bbar, entry_row=m, side=side, K=c['K'], ask=c['ask'],
                bid=c['bid'], delta=c['delta'], gamma=c['gamma'], CK=c['CK'], dS=dS, gmax=gmax,
                stop=0.76 if gmax >= 0.85 else 0.82, touch=tch, how=how, last=last), 'ok'


# ---- the modes (6) ---------------------------------------------------------------------------------------------------------

def mode1_at(day: Day, t: int) -> int:
    """the Mode 1 side at bar t (0 = none); stateless"""
    if not in_win(t, W1):
        return 0
    z = day.zvel(t)
    if not np.isfinite(z) or abs(z) < 2.60 - 1e-12:
        return 0
    St, vw = day.S[t], day.vwap[t]
    if not (np.isfinite(St) and np.isfinite(vw)):
        return 0
    side = 1 if (z >= 2.60 and St > vw) else (-1 if (z <= -2.60 and St < vw) else 0)
    if not side or not day.vol_ok(t):
        return 0
    bk = day.book(t)
    if bk is None or bk['regime'] != -1:
        return 0
    vr = vol_ratio(day, t, bk)
    if not (vr <= 1.18 + 1e-12):
        return 0
    w = bk['CWa'] if side > 0 else bk['PWb']
    dist = abs(w - St) if np.isfinite(w) else 0.025 * St
    if dist < 4.5 * math.sqrt(5) * day.sigma(t) * St - 1e-9:
        return 0
    return side


def mode2_trigger(day: Day, t: int) -> int:
    """Mode 2's trigger at bar t: the trade side (−1 after a high-side stretch, +1 after a low-side one), 0 = none"""
    if not in_win(t, W2):
        return 0
    s = day.sigma(t)
    St, vw = day.S[t], day.vwap[t]
    if not (np.isfinite(s) and np.isfinite(St) and np.isfinite(vw)) or St == vw:
        return 0
    if abs(St - vw) / (s * St * math.sqrt(t + 1)) < 2.80 - 1e-12:
        return 0
    bk = day.book(t)
    if bk is None or bk['regime'] != 1:
        return 0
    walls = [w for w in (bk['CW'], bk['PW']) if np.isfinite(w) and abs(St - w) <= 0.0015 * St + 1e-9]
    if not walls:
        return 0
    vr = vol_ratio(day, t, bk)
    if not (vr <= 1.18 + 1e-12):
        return 0
    return -1 if St > vw else 1


def mode2_at(day: Day, t: int) -> int:
    """Mode 2's signal at bar t (the confirmation bar; the trigger is bar t − 1)"""
    if t < 1:
        return 0
    side = mode2_trigger(day, t - 1)
    if not side:
        return 0
    o, c, c1 = day.O[t - 1], day.C[t - 1], day.C[t]
    if not (np.isfinite(o) and np.isfinite(c) and np.isfinite(c1)):
        return 0
    if not (min(o, c) < c1 < max(o, c)):
        return 0
    z1 = day.zvel(t)
    if not np.isfinite(z1) or not (z1 * side > 0):          # opposing the stretch = in the trade's direction
        return 0
    return side


def run_session(d: str):
    day = Day(d)
    out, skip = [], {}
    for mode, fn in ((1, mode1_at), (2, mode2_at)):
        free = -1
        for t in range(0, NBAR - 5):
            side = fn(day, t)
            if not side:
                continue
            if t + 1 <= free:
                skip[f'm{mode}:overlap'] = skip.get(f'm{mode}:overlap', 0) + 1
                continue
            tr, why = trade(day, mode, t, t if mode == 1 else t - 1, side)
            if tr is None:
                skip[f'm{mode}:{why}'] = skip.get(f'm{mode}:{why}', 0) + 1
                continue
            out.append(tr)
            free = tr['last']
    return d, out, skip


# ---- the baseline ----------------------------------------------------------------------------------------------------------

def base_session(args):
    d, cells = args                               # cells: [(mode, entry_row)]
    day = Day(d)
    res = {}
    for mode, m in cells:
        sbar = m - 1
        bbar = sbar if mode == 1 else sbar - 1
        for side in (1, -1):
            tr, _ = trade(day, mode, sbar, bbar, side)
            res[(mode, m, side)] = None if tr is None else tr['touch']
    return d, res


def boot_rate(touch_by_s: np.ndarray, n_by_s: np.ndarray, block: int = 20):
    n = touch_by_s.size
    W = AL.weights_from(AL.block_draws(n, block), n)
    rates = (W @ touch_by_s) / np.maximum(W @ n_by_s, 1)
    return AL.pct_ci(rates)


def main(procs: int = 4):
    print(G.selftest())
    OUT.mkdir(exist_ok=True)
    days = sessions()
    with mp.get_context('spawn').Pool(procs) as p:
        res = p.map(run_session, days)
    trades, skips = [], {}
    for d, t, k in res:
        trades += t
        for a, b in k.items():
            skips[a] = skips.get(a, 0) + b
    pl.DataFrame(trades).write_csv(OUT / 'signals.csv') if trades else None
    # baseline table
    cells = sorted({(t['mode'], t['entry_row']) for t in trades})
    with mp.get_context('spawn').Pool(procs) as p:
        tab = dict(p.map(base_session, [(d, cells) for d in days]))
    rng = np.random.default_rng(SEED)
    draws = {1: [], 2: [], 0: []}
    redraws = 0
    for _ in range(TRIALS):
        hits = {1: [], 2: []}
        for t in trades:
            for _try in range(50):
                d = days[int(rng.integers(len(days)))]
                sd = 1 if rng.random() < 0.5 else -1
                v = tab[d].get((t['mode'], t['entry_row'], sd))
                if v is not None:
                    hits[t['mode']].append(v)
                    break
                redraws += 1
        for mo in (1, 2):
            draws[mo].append(np.mean(hits[mo]) if hits[mo] else np.nan)
        allh = hits[1] + hits[2]
        draws[0].append(np.mean(allh) if allh else np.nan)
    # signals' block interval
    di = {d: i for i, d in enumerate(days)}
    summ = {'sessions': len(days), 'skips': skips, 'baseline_redraws': redraws}
    for mo, name in ((0, 'pooled'), (1, 'mode1'), (2, 'mode2')):
        sel = [t for t in trades if mo == 0 or t['mode'] == mo]
        tb, nb = np.zeros(len(days)), np.zeros(len(days))
        for t in sel:
            tb[di[t['d']]] += t['touch']
            nb[di[t['d']]] += 1
        rate = float(tb.sum() / nb.sum()) if nb.sum() else float('nan')
        ci = boot_rate(tb, nb) if nb.sum() else (float('nan'),) * 2
        bd = np.array(draws[mo], float)
        summ[name] = dict(n=int(nb.sum()), touches=int(tb.sum()), rate=rate, ci=ci,
                          stops=sum(t['how'] == 'stop' for t in sel), none=sum(t['how'] == 'none' for t in sel),
                          base_mean=float(np.nanmean(bd)) if np.isfinite(bd).any() else float('nan'),
                          base_ci=AL.pct_ci(bd), calls=sum(t['side'] > 0 for t in sel),
                          stop24=sum(t['stop'] == 0.76 for t in sel))
        summ[name]['pass'] = bool(np.isfinite(ci[0]) and ci[0] > summ[name]['base_ci'][1])
        yrs = {}
        for t in sel:
            y = t['d'][:4]
            a = yrs.setdefault(y, [0, 0])
            a[0] += t['touch']
            a[1] += 1
        summ[name]['years'] = {y: dict(n=b, touches=a, rate=a / b) for y, (a, b) in sorted(yrs.items())}
    (OUT / 'summary.json').write_text(json.dumps(summ, indent=1, default=float))
    print(json.dumps(summ, indent=1, default=float))


if __name__ == '__main__':
    main()
