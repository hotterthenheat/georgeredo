"""
ema_system.py — the engine of RULEBOOK_v0.md (the owner's EMA options strategy, v0 defaults), for the one-week PREVIEW.

Reads files only (scanner_lib's chain / open-interest / EOD-volume readers and its Black-Scholes delta). No vendor call.
Deterministic; the random baseline is seeded. Section numbers (§) are the rulebook's.
"""
from __future__ import annotations

import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass scanner'))
import scanner_lib as S  # noqa: E402

DAYS = ('2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16')
NAMES = ('SPXW', 'SPY', 'QQQ', 'IWM')
WARM = 60                                 # trading days of warm-up before the first preview day (§2)
NBAR = 390
FIRST_M, LAST_M, FLAT_M = 15, 360, 388    # 09:45, 15:30, 15:58 (§3, §5)
FEE_EQ = 0.68748
R_RATE = 0.045

CONFIGS = {
    'A': dict(align=(5, 15, 20, 50), pull=20, cross=(5, 15)),
    'B': dict(align=(9, 21, 50), pull=21, cross=(9, 21)),
}
EXITS = ('X1', 'X2', 'X3', 'X4')


def fee(name: str, premium: float) -> float:
    """a contract, one way (§5)"""
    if name == 'SPXW':
        return 1.18748 if premium < 1.0 else 1.27748
    return FEE_EQ


# ---- bars (§1) -----------------------------------------------------------------------------------------------------------------

def index_bars(d: str):
    """SPX: the print stamped t is the close of bar t − 1; O = H = L = C; no volume"""
    p = S.THETA / 'data' / 'index' / 'SPX' / f'{d}.parquet'
    if not p.exists():
        return None
    x = pl.read_parquet(p).with_columns(S._mcol().alias('m'))
    x = x.filter((pl.col('m') >= 1) & (pl.col('m') <= NBAR) & pl.col('price').is_not_null() & pl.col('price').is_not_nan())
    c = np.full(NBAR, np.nan)
    c[x['m'].to_numpy() - 1] = x['price'].to_numpy().astype(float)
    return c.copy(), c.copy(), c.copy(), c.copy(), np.full(NBAR, np.nan)


def raw_bars(name: str, d: str):
    if name == 'SPXW':
        return index_bars(d)
    b = S.day_bars(name, d)
    return None if b is None else tuple(a.copy() for a in b)


def warm_days(first: str = DAYS[0], n: int = WARM) -> list[str]:
    td = S.trading_days()
    i = td.index(first)
    return list(td[i - n:i])


# ---- indicators -----------------------------------------------------------------------------------------------------------------

def ema_seq(x: np.ndarray, n: int) -> np.ndarray:
    """EMA(n) over a sequence, alpha 2/(n+1), seeded with the first finite value; NaN entries carry the last value"""
    a = 2.0 / (n + 1)
    out = np.full(x.size, np.nan)
    e = np.nan
    for i, v in enumerate(x):
        if np.isfinite(v):
            e = v if not np.isfinite(e) else e + a * (v - e)
        out[i] = e
    return out


def rsi_wilder(x: np.ndarray, n: int = 14) -> np.ndarray:
    """Wilder RSI over a sequence (NaN entries skipped, the value carried); first value after n changes = simple means"""
    out = np.full(x.size, np.nan)
    prev = np.nan
    gains, losses = [], []
    ag = al = np.nan
    for i, v in enumerate(x):
        if not np.isfinite(v):
            out[i] = out[i - 1] if i else np.nan
            continue
        if np.isfinite(prev):
            ch = v - prev
            g, l_ = max(ch, 0.0), max(-ch, 0.0)
            if not np.isfinite(ag):
                gains.append(g)
                losses.append(l_)
                if len(gains) == n:
                    ag, al = sum(gains) / n, sum(losses) / n
            else:
                ag = (ag * (n - 1) + g) / n
                al = (al * (n - 1) + l_) / n
        prev = v
        if np.isfinite(ag):
            out[i] = 100.0 if al == 0 and ag > 0 else (50.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al))
    return out


def bucket_close(c: np.ndarray, size: int) -> np.ndarray:
    """clock-aligned buckets of one session: the close of the last present bar in each bucket (NaN when none)"""
    nb = NBAR // size
    out = np.full(nb, np.nan)
    for j in range(nb):
        seg = c[size * j:size * j + size]
        ok = np.where(np.isfinite(seg))[0]
        if ok.size:
            out[j] = seg[ok[-1]]
    return out


class Series:
    """one name's regular-session bars over the warm-up and the preview days, and every indicator of §2"""

    def __init__(self, name: str, days=DAYS, warm: list[str] | None = None, override: dict | None = None):
        self.name = name
        self.days = list(warm if warm is not None else warm_days(days[0])) + list(days)
        bars = []
        for d in self.days:
            b = override[d] if (override and d in override) else raw_bars(name, d)
            if b is None:
                b = tuple(np.full(NBAR, np.nan) for _ in range(5))
            bars.append(b)
        self.O, self.H, self.L, self.C, self.V = (np.array([b[k] for b in bars]) for k in range(5))   # (ndays, 390)
        nd = len(self.days)
        flat = self.C.reshape(-1)
        self.ema1 = {n: ema_seq(flat, n).reshape(nd, NBAR) for n in (5, 9, 15, 20, 21, 50)}
        self.rsi = rsi_wilder(flat).reshape(nd, NBAR)
        self.c5 = np.array([bucket_close(self.C[i], 5) for i in range(nd)])        # (nd, 78)
        self.c15 = np.array([bucket_close(self.C[i], 15) for i in range(nd)])      # (nd, 26)
        self.ema5 = {n: ema_seq(self.c5.reshape(-1), n).reshape(nd, -1) for n in (5, 9, 15, 20, 21, 50)}
        self.ema15 = {n: ema_seq(self.c15.reshape(-1), n).reshape(nd, -1) for n in (50, 200)}
        # VWAP (§2; SPX: the time-weighted mean of closes)
        self.vwap = np.full((nd, NBAR), np.nan)
        for i in range(nd):
            c = self.C[i]
            ok = np.isfinite(c)
            if name == 'SPXW':
                w = ok.astype(float)
                tp = np.where(ok, c, 0.0)
            else:
                w = np.where(ok, np.nan_to_num(self.V[i]), 0.0)
                tp = np.where(ok, (self.H[i] + self.L[i] + c) / 3.0, 0.0)
            cw, cpv = np.cumsum(w), np.cumsum(tp * w)
            with np.errstate(invalid='ignore', divide='ignore'):
                self.vwap[i] = np.where(cw > 0, cpv / cw, np.nan)
        # RVOL: bar volume ÷ mean of the same stamp over the previous 10 sessions that have it (>= 5)
        self.rvol = np.full((nd, NBAR), np.nan)
        if name != 'SPXW':
            for i in range(nd):
                prior = self.V[max(0, i - 10):i]
                if prior.shape[0] == 0:
                    continue
                cnt = np.isfinite(prior).sum(axis=0)
                with np.errstate(invalid='ignore', divide='ignore'):
                    mv = np.nansum(prior, axis=0) / cnt
                    self.rvol[i] = np.where((cnt >= 5) & (mv > 0), self.V[i] / mv, np.nan)

    def di(self, d: str) -> int:
        return self.days.index(d)

    # the 1m value at global position (day i, bar s), stepping back across sessions for s < 0
    def prev_pos(self, i: int, s: int, k: int):
        s -= k
        while s < 0:
            i -= 1
            s += NBAR
        return i, s

    def roc5(self, i: int, s: int) -> float:
        j, t = self.prev_pos(i, s, 5)
        return self.C[i, s] / self.C[j, t] - 1.0

    def last15(self, i: int, m: int):
        j = m // 15 - 1
        return (i, j) if j >= 0 else (i - 1, 25)

    def last5(self, i: int, m: int):
        j = m // 5 - 1
        return (i, j) if j >= 0 else (i - 1, 77)

    def bias(self, i: int, m: int) -> int:
        a, j = self.last15(i, m)
        c, e = self.c15[a, j], self.ema15[50][a, j]
        return 1 if c > e else (-1 if c < e else 0)

    def ctx200(self, i: int, m: int) -> int:
        a, j = self.last15(i, m)
        c, e = self.c15[a, j], self.ema15[200][a, j]
        return 1 if c > e else (-1 if c < e else 0)

    def align(self, i: int, m: int, cfg: str) -> int:
        a, j = self.last5(i, m)
        v = [self.ema5[n][a, j] for n in CONFIGS[cfg]['align']]
        if all(v[k] > v[k + 1] for k in range(len(v) - 1)):
            return 1
        if all(v[k] < v[k + 1] for k in range(len(v) - 1)):
            return -1
        return 0

    def structure(self, i: int, s: int) -> int:
        """+1 rising (last two confirmed swing highs and lows rising), -1 falling, 0 otherwise; swing at t known at bar t+2"""
        H, L = self.H[i], self.L[i]
        sh, sl = [], []
        for t in range(2, s - 1):                    # t + 2 <= s
            if not (np.isfinite(H[t - 2:t + 3]).all()):
                continue
            if H[t] >= H[t - 2:t + 3].max():
                sh.append(H[t])
            if L[t] <= L[t - 2:t + 3].min():
                sl.append(L[t])
        if len(sh) >= 2 and len(sl) >= 2:
            if sh[-1] > sh[-2] and sl[-1] > sl[-2]:
                return 1
            if sh[-1] < sh[-2] and sl[-1] < sl[-2]:
                return -1
        return 0


# ---- the rule (§3) -------------------------------------------------------------------------------------------------------------

def full_signal(X: Series, i: int, m: int, cfg: str) -> int:
    """+1 bull, -1 bear, 0 none, from bars <= s = m - 1 only"""
    s = m - 1
    if s < 5 or not np.isfinite(X.C[i, s - 4:s + 1]).all():
        return 0
    b = X.bias(i, m)
    if b == 0 or X.align(i, m, cfg) != b:
        return 0
    pl_ = X.ema1[CONFIGS[cfg]['pull']][i]
    e50 = X.ema1[50][i]
    vw = X.vwap[i]
    W = range(s - 4, s + 1)
    if b > 0:
        touch = any(X.L[i, t] <= max(pl_[t], vw[t]) for t in W)
        bad = any(X.C[i, t] < e50[t] for t in W)
        trig = X.C[i, s] > X.H[i, s - 1] and X.C[i, s] > vw[s]
        conf = X.rsi[i, s] > 50 and X.roc5(i, s) > 0
    else:
        touch = any(X.H[i, t] >= min(pl_[t], vw[t]) for t in W)
        bad = any(X.C[i, t] > e50[t] for t in W)
        trig = X.C[i, s] < X.L[i, s - 1] and X.C[i, s] < vw[s]
        conf = X.rsi[i, s] < 50 and X.roc5(i, s) < 0
    if X.name != 'SPXW':
        conf = conf and bool(X.rvol[i, s] >= 1.5)
    return b if (touch and not bad and trig and conf) else 0


def cross_signal(X: Series, i: int, m: int, cfg: str) -> int:
    f, sl = CONFIGS[cfg]['cross']
    s = m - 1
    j, t = X.prev_pos(i, s, 1)
    a1, b1 = X.ema1[f][i, s], X.ema1[sl][i, s]
    a0, b0 = X.ema1[f][j, t], X.ema1[sl][j, t]
    if a1 > b1 and a0 <= b0:
        return 1
    if a1 < b1 and a0 >= b0:
        return -1
    return 0


def align_state(X: Series, i: int, m: int, cfg: str) -> int:
    b = X.bias(i, m)
    return b if (b != 0 and X.align(i, m, cfg) == b) else 0


def align_signal(X: Series, i: int, m: int, cfg: str) -> int:
    st = align_state(X, i, m, cfg)
    if st == 0:
        return 0
    if m == FIRST_M:
        return st
    return st if align_state(X, i, m - 1, cfg) != st else 0


SIGNALS = {'full': full_signal, 'cross': cross_signal, 'align': align_signal}


# ---- the contract (§4) ---------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=None)
def pick(name: str, d: str, m: int, side: int, spot: float):
    ch = S.chain(name, d)
    if ch is None:
        return None, 'no chain file'
    K, bid, ask = ch
    r = 0 if side > 0 else 1
    b, a = bid[m, :, r], ask[m, :, r]
    oi = S.oi_day(name, d)
    if oi is None:
        return None, 'no open interest file'
    vol = S.prev_volume(name, d)
    if vol is None:
        return None, 'no previous-session volume file'
    q = np.isfinite(a) & np.isfinite(b) & (a > b) & (b > 0)
    mid = np.where(q, (a + b) / 2.0, np.nan)
    spr = np.where(q, (a - b) / np.where(q, mid, 1.0), np.inf)
    T = (NBAR - m) / 525600.0
    dl = S.bs_delta(mid, spot, K, T, np.full(K.shape, side > 0))
    root = 'SPXW' if name == 'SPXW' else name
    o = np.array([oi.get(S.occ(root, d, r, k), 0) for k in K], float)
    v = np.array([vol.get((float(k), r), 0) for k in K], float)
    f1 = q
    f2 = f1 & (spr <= 0.12 + 1e-12)
    f3 = f2 & np.isfinite(dl) & (dl >= 0.30 - 1e-12) & (dl <= 0.60 + 1e-12)
    f4 = f3 & (o >= 250)
    f5 = f4 & (v >= 100)
    for f, why in ((f1, 'no standing quote'), (f2, 'spread > 12%'), (f3, 'no delta 0.30-0.60'), (f4, 'OI < 250'),
                   (f5, 'prev volume < 100')):
        if not f.any():
            return None, why
    cand = np.where(f5)[0]
    i = min(cand, key=lambda k: (round(abs(dl[k] - 0.45), 12), spr[k], K[k]))
    return dict(K=float(K[i]), i=int(i), r=r, ask=float(a[i]), bid=float(b[i]), spread=float(spr[i]), delta=float(dl[i]),
                oi=int(o[i]), pvol=int(v[i])), 'ok'


# ---- one trade (§5) ------------------------------------------------------------------------------------------------------------

def simulate(X: Series, d: str, m: int, side: int, exit_v: str, cfg: str):
    """the trade entered at minute m; None and a reason when it cannot be entered"""
    i = X.di(d)
    s = m - 1
    W = range(s - 4, s + 1)
    entry_u = float(X.C[i, s])
    level = float(min(X.L[i, t] for t in W)) if side > 0 else float(max(X.H[i, t] for t in W))
    R = abs(entry_u - level)
    if not R > 0:
        return None, 'zero R'
    c, why = pick(X.name, d, m, side, entry_u)
    if c is None:
        return None, why
    K, bid, ask = S.chain(X.name, d)
    qty = 10 if exit_v == 'X4' else 1
    lots = {'t1': 2, 't2': 3, 'run': 5} if exit_v == 'X4' else None
    legs = []                                      # (qty, exit minute, bid, reason)
    open_q = qty
    hit1 = hit2 = False
    e = None
    for t in range(s + 1, FLAT_M):                 # bar t completes at minute t + 1 <= 388
        ct = X.C[i, t]
        if not np.isfinite(ct):
            continue
        mv = (ct - entry_u) * side
        ex = t + 1
        if (side > 0 and ct < level) or (side < 0 and ct > level):
            legs.append((open_q, ex, 'stop'))
            open_q = 0
        else:
            x3 = False
            if t % 5 == 4:
                j = t // 5
                c5, e9 = X.c5[i, j], X.ema5[9][i, j]
                x3 = (c5 < e9) if side > 0 else (c5 > e9)
            if exit_v == 'X1' and mv >= R - 1e-12:
                legs.append((open_q, ex, '+1R')); open_q = 0
            elif exit_v == 'X2' and mv >= 2 * R - 1e-12:
                legs.append((open_q, ex, '+2R')); open_q = 0
            elif exit_v == 'X3' and x3:
                legs.append((open_q, ex, 'runner')); open_q = 0
            elif exit_v == 'X4':
                if not hit1 and mv >= R - 1e-12:
                    legs.append((lots['t1'], ex, '+1R')); open_q -= lots['t1']; hit1 = True
                if not hit2 and mv >= 2 * R - 1e-12:
                    legs.append((lots['t2'], ex, '+2R')); open_q -= lots['t2']; hit2 = True
                if x3 and open_q > 0:
                    legs.append((open_q, ex, 'runner')); open_q = 0
        if open_q == 0:
            e = ex
            break
    if open_q > 0:
        legs.append((open_q, FLAT_M, 'flat'))
        e = FLAT_M
    ii, r = c['i'], c['r']
    out_legs = [(q, ex, S.exit_quote(bid, ex, ii, r), why) for q, ex, why in legs]
    gross = sum(q * (px - c['ask']) * 100 for q, ex, px, why in out_legs)
    fees = qty * fee(X.name, c['ask']) + sum(q * fee(X.name, px) for q, ex, px, why in out_legs)
    path = [S.exit_quote(bid, mm, ii, r) for mm in range(m + 1, e + 1)]
    ex_u = sum(q * X.C[i, ex - 1] for q, ex, px, why in out_legs) / qty
    reason = 'stop' if any(w == 'stop' for *_, w in out_legs) else out_legs[-1][3]
    return dict(name=X.name, day=d, cfg=cfg, exit=exit_v, m=m, entry=S.mtxt(m), side=side, K=c['K'],
                right='C' if side > 0 else 'P', ask=c['ask'], bid_in=c['bid'], spread=c['spread'], delta=c['delta'],
                oi=c['oi'], pvol=c['pvol'], qty=qty, level=level, R=R, entry_u=entry_u, exit_u=float(ex_u),
                exit_m=e, hold=e - m, reason=reason, legs=out_legs, gross=gross, fees=fees, net=gross - fees,
                cost=qty * c['ask'] * 100, mfe=(max(path) / c['ask'] - 1) if path else 0.0,
                mae=(min(path) / c['ask'] - 1) if path else 0.0,
                move_bp=side * (ex_u - entry_u) / entry_u * 1e4, move_R=side * (ex_u - entry_u) / R,
                ctx200=X.ctx200(i, m), struct=X.structure(i, s)), 'ok'


# ---- a session under the risk rules (§6) ---------------------------------------------------------------------------------------

def run_day(X: Series, d: str, cfg: str, exit_v: str, sig: str = 'full'):
    fn = SIGNALS[sig]
    i = X.di(d)
    trades, skips = [], {}
    nxt, n = FIRST_M, 0
    for m in range(FIRST_M, LAST_M + 1):
        if m < nxt or n >= 5:
            continue
        side = fn(X, i, m, cfg)
        if not side:
            continue
        tr, why = simulate(X, d, m, side, exit_v, cfg)
        if tr is None:
            skips[why] = skips.get(why, 0) + 1
            continue
        trades.append(tr)
        n += 1
        nxt = tr['exit_m'] + (5 if tr['reason'] == 'stop' else 1)
    return trades, skips


@lru_cache(maxsize=8)
def series(name: str) -> Series:
    return Series(name)


def run(cfg: str, exit_v: str, sig: str = 'full', names=NAMES, days=DAYS):
    T, K = [], {}
    for nm in names:
        X = series(nm)
        for d in days:
            t, k = run_day(X, d, cfg, exit_v, sig)
            T += t
            for a, b in k.items():
                K[(nm, a)] = K.get((nm, a), 0) + b
    return T, K


# ---- the random baseline (§7c) ----------------------------------------------------------------------------------------------------

@lru_cache(maxsize=None)
def random_trade(name: str, d: str, m: int, side: int, cfg: str):
    tr, _ = simulate(series(name), d, m, side, 'X2', cfg)
    return None if tr is None else (tr['net'], tr['gross'], tr['fees'])


def random_baseline(full: list[dict], cfg: str, trials: int = 500, seed: int = 20261023, names=NAMES, days=DAYS):
    mins = np.array([t['m'] for t in full])
    callp = float(np.mean([t['side'] > 0 for t in full])) if full else 0.5
    cnt = {nm: sum(1 for t in full if t['name'] == nm) for nm in names}
    rng = np.random.default_rng(seed)
    tot, per, wins = [], [], []
    for _ in range(trials):
        nets = []
        for nm in names:
            for _k in range(cnt[nm]):
                for _try in range(50):
                    d = days[int(rng.integers(len(days)))]
                    m = int(mins[int(rng.integers(mins.size))])
                    sd = 1 if rng.random() < callp else -1
                    r = random_trade(nm, d, m, sd, cfg)
                    if r is not None:
                        nets.append(r[0])
                        break
        nets = np.array(nets)
        tot.append(nets.sum())
        per.append(nets.mean() if nets.size else np.nan)
        wins.append((nets > 0).mean() if nets.size else np.nan)
    return dict(total=np.array(tot), per=np.array(per), win=np.array(wins), n=int(sum(cnt.values())), callp=callp)
