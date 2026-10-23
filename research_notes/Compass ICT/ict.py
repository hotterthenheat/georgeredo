"""
ict.py — the engine of PREREG_COMPASS_ICT.md (the owner's sweep -> displacement/MSS -> FVG rule), for the two-week PREVIEW.

Reads files only (no vendor call). Section letters are the prereg's. Deterministic; the random draws are seeded.
Minutes: a bar stamped t (0 = 09:30) covers t..t+1 and completes at minute t + 1; chain row m is the quote stamped m.
"""
from __future__ import annotations

import math
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import polars as pl
from scipy.special import ndtr

SP = Path(os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'))
TH = SP / 'theta'
DAYS = ('2026-10-09', '2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16', '2026-10-19', '2026-10-20',
        '2026-10-21', '2026-10-22')
HTF_FROM = '2026-09-01'          # the held-out 2026-08 is not read, even as context (prereg 5)
NBAR, FLAT = 390, 388
SWEEP_BP, CLOSE_BACK, DISP_WIN, DISP_K, MED_N, ENTRY_WIN = 0.0002, 5, 15, 1.5, 20, 30
QTY = 2


def fee(px: float) -> float:
    if not (px > 0):
        return 0.0
    return 1.18748 if px < 1.0 else 1.27748


def _m(ts):
    return ts.dt.hour().cast(pl.Int32) * 60 + ts.dt.minute().cast(pl.Int32) - 570


# ---- files ---------------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=None)
def spx_days() -> tuple[str, ...]:
    return tuple(sorted(p.stem for p in (TH / 'data' / 'index' / 'SPX').glob('*.parquet')))


@lru_cache(maxsize=None)
def spx_prints(d: str) -> np.ndarray:
    """price by stamp 0..390 (the print stamped t = the close of bar t - 1); NaN where none"""
    x = pl.read_parquet(TH / 'data' / 'index' / 'SPX' / f'{d}.parquet')
    m = _m(x['timestamp']).to_numpy()
    p = x['price'].fill_null(np.nan).to_numpy().astype(float)
    a = np.full(NBAR + 1, np.nan)
    ok = (m >= 0) & (m <= NBAR)
    a[m[ok]] = p[ok]
    return a


@lru_cache(maxsize=None)
def spy_bars(d: str) -> np.ndarray:
    """(4, 390): open, high, low, close by stamp; NaN where missing"""
    x = pl.read_parquet(TH / 'data' / 'underlying' / 'SPY' / f'{d}.parquet', columns=['timestamp', 'open', 'high', 'low', 'close'])
    m = _m(x['timestamp']).to_numpy()
    out = np.full((4, NBAR), np.nan)
    ok = (m >= 0) & (m < NBAR)
    for i, c in enumerate(('open', 'high', 'low', 'close')):
        out[i, m[ok]] = x[c].fill_null(np.nan).to_numpy().astype(float)[ok]
    return out


@lru_cache(maxsize=None)
def chain(d: str):
    x = pl.read_parquet(TH / 'data_full' / 'chains' / 'SPXW' / f'{d}.parquet', columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    m = _m(x['timestamp']).to_numpy()
    K = np.array(sorted(set(x['strike'].to_list())), float)
    ki = {k: i for i, k in enumerate(K)}
    bid = np.full((NBAR + 1, K.size, 2), np.nan)
    ask = np.full((NBAR + 1, K.size, 2), np.nan)
    si = np.array([ki[k] for k in x['strike'].to_list()])
    r = np.where(x['right'].to_numpy() == 'CALL', 0, 1)
    ok = (m >= 0) & (m <= NBAR)
    bid[m[ok], si[ok], r[ok]] = x['bid'].fill_null(np.nan).to_numpy().astype(float)[ok]
    ask[m[ok], si[ok], r[ok]] = x['ask'].fill_null(np.nan).to_numpy().astype(float)[ok]
    return K, bid, ask


def prev_day(d: str) -> str:
    s = spx_days()
    return s[s.index(d) - 1]


def ratio(d: str) -> float:
    """SPX print stamped 09:31 (close of the 09:30 bar) / SPY's 09:30 close"""
    return float(spx_prints(d)[1] / spy_bars(d)[3, 0])


# ---- a day's inputs, optionally cut at minute `cut` (the look-ahead test) ----------------------------------------------------------

class Day:
    def __init__(self, d: str, cut: int | None = None):
        self.d = d
        p = prev_day(d)
        self.R = ratio(d)
        Rp = ratio(p)
        b = spy_bars(d) * self.R
        bp = spy_bars(p) * Rp
        self.spx = spx_prints(d).copy()
        K, bid, ask = chain(d)
        bid, ask = bid.copy(), ask.copy()
        if cut is not None:                      # bars completed by `cut` (stamp < cut), prints and quotes stamped <= cut
            b = b.copy()
            b[:, cut:] = np.nan
            self.spx[cut + 1:] = np.nan
            bid[cut + 1:] = np.nan
            ask[cut + 1:] = np.nan
        self.K, self.bid, self.ask = K, bid, ask
        self.b1 = b                               # today's scaled 1-min bars (4, 390)
        self.bp1 = bp                             # the prior session's (4, 390), its own ratio
        pb = spy_bars(p) * self.R                 # PDH / PDL in today's units (prereg 1)
        self.PDH, self.PDL = float(np.nanmax(pb[1])), float(np.nanmin(pb[2]))
        self.bias = htf_bias(d)
        fi = forward_im(self, 1)
        self.IM = fi[2] if fi else float('nan')


# ---- (a) the HTF bias on SPX daily bars built from 1-min prints ------------------------------------------------------------------

@lru_cache(maxsize=None)
def daily(d: str):
    a = spx_prints(d)[1:]
    return float(np.nanmax(a)), float(np.nanmin(a)), float(a[-1])


def htf_bias(d: str) -> int:
    days = [x for x in spx_days() if HTF_FROM <= x < d]
    H = np.array([daily(x)[0] for x in days])
    L = np.array([daily(x)[1] for x in days])
    C = np.array([daily(x)[2] for x in days])
    n = len(days)
    bias = 0
    for k in range(n):
        sh = [j for j in range(2, k - 1) if j + 2 <= k and H[j] >= max(H[j - 2], H[j - 1], H[j + 1], H[j + 2])]
        sl = [j for j in range(2, k - 1) if j + 2 <= k and L[j] <= min(L[j - 2], L[j - 1], L[j + 1], L[j + 2])]
        up = bool(sh) and C[k] > H[sh[-1]]
        dn = bool(sl) and C[k] < L[sl[-1]]
        if up and not dn:
            bias = 1
        elif dn and not up:
            bias = -1
    return bias


# ---- the chain: forward, implied move, Black-76 (h) ---------------------------------------------------------------------------------

def forward_im(D: Day, m: int):
    cb, ca, pb, pa = D.bid[m, :, 0], D.ask[m, :, 0], D.bid[m, :, 1], D.ask[m, :, 1]
    both = (cb > 0) & (ca > 0) & (ca >= cb) & (pb > 0) & (pa > 0) & (pa >= pb)
    if not both.any():
        return None
    cm, pm = (cb + ca) / 2, (pb + pa) / 2
    i = int(np.argmin(np.where(both, np.abs(cm - pm), np.inf)))
    return float(D.K[i]), float(D.K[i] + cm[i] - pm[i]), float(cm[i] + pm[i])


def b76(F, K, T, v, call):
    sv = v * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sv * sv) / sv
    c = F * ndtr(d1) - K * ndtr(d1 - sv)
    return np.where(call, c, c - (F - K))


def b76_delta(price, F, K, T, call):
    intr = np.maximum(F - K, 0) if call else np.maximum(K - F, 0)
    up = F if call else K
    ok = np.isfinite(price) & (price > intr + 1e-12) & (price < up) & (T > 0)
    a, b = np.full(price.shape, 1e-4), np.full(price.shape, 8.0)
    for _ in range(80):
        mid = 0.5 * (a + b)
        hi = b76(F, K, T, mid, call) > price
        b, a = np.where(hi, mid, b), np.where(hi, a, mid)
    v = 0.5 * (a + b)
    d1 = (np.log(F / K) + 0.5 * v * v * T) / (v * np.sqrt(T))
    return np.where(ok, np.abs(ndtr(d1) if call else ndtr(d1) - 1.0), np.nan)


def pick(D: Day, m: int, side: int):
    fi = forward_im(D, m)
    if fi is None:
        return None, 'no forward'
    F = fi[1]
    r = 0 if side > 0 else 1
    b, a = D.bid[m, :, r], D.ask[m, :, r]
    q = np.isfinite(a) & np.isfinite(b) & (a > b) & (b > 0)
    mid = np.where(q, (a + b) / 2, np.nan)
    spr = np.where(q, (a - b) / np.where(q, mid, 1), np.inf)
    dl = b76_delta(mid, F, D.K, (NBAR - m) / 525600.0, side > 0)
    ok = q & (spr <= 0.10 + 1e-12) & np.isfinite(dl) & (dl >= 0.45 - 1e-12) & (dl <= 0.60 + 1e-12)
    if not ok.any():
        return None, ('spread' if not (q & (spr <= 0.10 + 1e-12)).any() else 'delta 0.45-0.60')
    i = min(np.where(ok)[0], key=lambda k: (round(abs(dl[k] - 0.5), 12), spr[k], D.K[k]))
    return dict(K=float(D.K[i]), i=int(i), r=r, ask=float(a[i]), bid=float(b[i]), spread=float(spr[i]), delta=float(dl[i]),
                F=F), 'ok'


def exit_bid(D: Day, m: int, i: int, r: int) -> float:
    for mm in range(m, max(-1, m - 11), -1):
        v = D.bid[mm, i, r]
        if np.isfinite(v):
            return max(0.0, float(v))
    return 0.0


# ---- bars at the setup's timeframe (V4: 5-min) -------------------------------------------------------------------------------------

def tf_bars(b1: np.ndarray, tf: int) -> np.ndarray:
    if tf == 1:
        return b1
    n = NBAR // tf
    out = np.full((4, n), np.nan)
    for j in range(n):
        seg = b1[:, tf * j:tf * j + tf]
        ok = np.isfinite(seg[3])
        if not ok.any():
            continue
        out[0, j] = seg[0][ok][0]
        out[1, j] = np.nanmax(seg[1])
        out[2, j] = np.nanmin(seg[2])
        out[3, j] = seg[3][ok][-1]
    return out


class Bars:
    """the prior session and today on the setup's timeframe, concatenated; today's bar b sits at P + b"""

    def __init__(self, D: Day, tf: int):
        self.tf = tf
        p, t = tf_bars(D.bp1, tf), tf_bars(D.b1, tf)
        self.P = p.shape[1]
        self.O, self.H, self.L, self.C = np.concatenate([p, t], axis=1)
        self.n = self.O.size
        self.sh = np.zeros(self.n, bool)
        self.sl = np.zeros(self.n, bool)
        for x in range(2, self.n - 2):
            w = slice(x - 2, x + 3)
            if np.isfinite(self.H[w]).all():
                self.sh[x] = self.H[x] >= self.H[w].max()
                self.sl[x] = self.L[x] <= self.L[w].min()

    def comp(self, g: int) -> int:
        """the 1-min minute at which today's bar at global index g completes"""
        return self.tf * (g - self.P + 1)

    def last_swing(self, kind: str, upto: int, below: float | None = None, above: float | None = None):
        """the latest swing (kind 'h' or 'l') at x with x + 2 <= upto, optionally below / above a price"""
        arr, val = (self.sh, self.H) if kind == 'h' else (self.sl, self.L)
        for x in range(upto - 2, 1, -1):
            if arr[x] and (below is None or val[x] < below) and (above is None or val[x] > above):
                return float(val[x])
        return None

    def med_body(self, j: int) -> float:
        bd = np.abs(self.C[max(0, j - MED_N):j] - self.O[max(0, j - MED_N):j])
        bd = bd[np.isfinite(bd)]
        return float(np.median(bd)) if bd.size else float('nan')


# ---- the setups (d, e, f, g) ---------------------------------------------------------------------------------------------------

def in_kz(t: int, P: dict, D: Day) -> bool:
    if P['kz'] == 'all':
        return 5 <= t + 1 <= 360
    am, pm = 0 <= t < 90, 270 <= t < 330
    if am and P.get('v3'):
        if t < 29 or not (D.rng30 >= 0.76 * D.IM):
            return False
    return am or pm


def disp_ok(B: Bars, j: int, side: int) -> bool:
    o, c = B.O[j], B.C[j]
    if not (np.isfinite(o) and np.isfinite(c)) or (c - o) * side <= 0:
        return False
    mb = B.med_body(j)
    if not (abs(c - o) >= DISP_K * mb - 1e-12):
        return False
    if side < 0:
        s = B.last_swing('l', j)
        return s is not None and c < s
    s = B.last_swing('h', j)
    return s is not None and c > s


def fvg(B: Bars, j: int, side: int):
    if j + 1 >= B.n:
        return None
    if side < 0 and B.L[j - 1] > B.H[j + 1]:
        return (float(B.H[j + 1]), float(B.L[j - 1]))
    if side > 0 and B.H[j - 1] < B.L[j + 1]:
        return (float(B.H[j - 1]), float(B.L[j + 1]))
    return None


def find_entry(D: Day, B: Bars, P: dict, j: int, side: int, ext: float, zone):
    """the first killzone 1-min bar into the entry zone within 30 bars of bar 3's completion; (t, how)"""
    b1 = D.b1
    if P['entry'] == 'disp':                          # the no-FVG ablation: at the displacement bar's close
        t = B.comp(j) - 1
        return (t, 'disp') if (0 <= t < NBAR and in_kz(t, P, D)) else (None, 'entry outside killzone')
    if P['entry'] == 'ote':
        de = B.L[j] if side < 0 else B.H[j]
        leg = abs(ext - de)
        lo, hi = (de + 0.62 * leg, de + 0.79 * leg) if side < 0 else (de - 0.79 * leg, de - 0.62 * leg)
    else:
        lo, hi = zone
    t0 = B.comp(j + 1)
    for t in range(t0, min(t0 + ENTRY_WIN, NBAR)):
        if not np.isfinite(b1[3, t]):
            continue
        into = (b1[1, t] >= lo) if side < 0 else (b1[2, t] <= hi)
        if into and in_kz(t, P, D):
            return t, 'zone'
    return None, 'no entry in window'


def setups(D: Day, P: dict):
    """candidate setups and a funnel of reasons"""
    B = Bars(D, P['tf'])
    why: dict[str, int] = {}
    out = []

    def note(k):
        why[k] = why.get(k, 0) + 1

    if P['bias'] and D.bias == 0:
        note('no HTF bias')
        return out, why, B

    def finish(j, side, ext, sweep_s):
        z = fvg(B, j, side)
        if z is None and P['entry'] != 'disp':
            note('no FVG')
            return
        t, w = find_entry(D, B, P, j, side, ext, z)
        if t is None:
            note(w)
            return
        out.append(dict(t=t, side=side, ext=ext, j=j - B.P, zone=z, sweep=sweep_s))

    nb = B.n
    if P['sweep']:
        for lvl, side in ((D.PDH, -1), (D.PDL, 1)):
            if P['bias'] and side != D.bias:
                continue
            s = B.P
            while s < nb:
                hit = (B.H[s] >= lvl * (1 + SWEEP_BP)) if side < 0 else (B.L[s] <= lvl * (1 - SWEEP_BP))
                if not (np.isfinite(B.C[s]) and hit):
                    s += 1
                    continue
                k = next((k for k in range(s, min(s + CLOSE_BACK + 1, nb))
                          if np.isfinite(B.C[k]) and ((B.C[k] < lvl) if side < 0 else (B.C[k] > lvl))), None)
                if k is None:
                    prev_beyond = s > B.P and ((B.H[s - 1] >= lvl * (1 + SWEEP_BP)) if side < 0 else (B.L[s - 1] <= lvl * (1 - SWEEP_BP)))
                    if not prev_beyond:                # counted once an excursion beyond the level (reporting only)
                        note('sweep without close-back')
                    s += 1
                    continue
                ext = float(np.nanmax(B.H[s:k + 1])) if side < 0 else float(np.nanmin(B.L[s:k + 1]))
                j = next((j for j in range(k, min(k + DISP_WIN + 1, nb - 1)) if disp_ok(B, j, side)), None)
                if j is None:
                    note('no displacement + MSS')
                else:
                    finish(j, side, ext, s - B.P)
                s = k + 1
        if not out and not why:
            note('no sweep')
    else:
        sides = (D.bias,) if P['bias'] else (-1, 1)
        for side in sides:
            for j in range(B.P, nb - 1):
                if disp_ok(B, j, side):
                    ext = float(np.nanmax(B.H[j - 15:j + 1])) if side < 0 else float(np.nanmin(B.L[j - 15:j + 1]))
                    finish(j, side, ext, None)
    out.sort(key=lambda x: (x['t'], x['j']))
    return out, why, B


# ---- one trade (exits) ------------------------------------------------------------------------------------------------------------

def levels_for(D: Day, B: Bars, t: int, side: int, entry_u: float):
    """TP1: the latest opposite swing confirmed by the entry minute t + 1; TP2: the opposite day level unless already beyond"""
    upto = B.P + (t + 1) // B.tf - 1      # the last bar of the setup's tf completed by minute t + 1 (swings need x + 2 <= it)
    tp1 = B.last_swing('l', upto, below=entry_u) if side < 0 else B.last_swing('h', upto, above=entry_u)
    tp2 = D.PDL if side < 0 else D.PDH
    if (side < 0 and entry_u <= tp2) or (side > 0 and entry_u >= tp2):
        tp2 = None
    return tp1, tp2


def simulate(D: Day, B: Bars, P: dict, t: int, side: int, ext: float, c: dict | None = None):
    m = t + 1
    if c is None:
        c, w = pick(D, m, side)
        if c is None:
            return None, w
    entry_u = float(D.b1[3, t])
    tp1, tp2 = levels_for(D, B, t, side, entry_u)
    stop = ext
    q, legs, tp1_done = QTY, [], False
    for u in range(t + 1, FLAT):
        if P.get('v2') and m < 270 and u + 1 > 270:
            break
        H, L, C = D.b1[1, u], D.b1[2, u], D.b1[3, u]
        if not np.isfinite(C):
            continue
        ex = u + 1
        if tp1 is not None and not tp1_done and ((L <= tp1) if side < 0 else (H >= tp1)):
            n = q if tp2 is None else 1
            legs.append((n, ex, 'TP1'))
            q -= n
            tp1_done = True
            stop = entry_u
        if q and tp2 is not None and ((L <= tp2) if side < 0 else (H >= tp2)):
            legs.append((q, ex, 'TP2'))
            q = 0
        if q and ((C > stop) if side < 0 else (C < stop)):
            legs.append((q, ex, 'stop' if stop == ext else 'stop@entry'))
            q = 0
        if q == 0:
            break
    if q:
        if P.get('v2') and m < 270:
            legs.append((q, 270, '14:00'))
        else:
            legs.append((q, FLAT, 'flat 15:58'))
    ii, r = c['i'], c['r']
    lg = [(n, ex, exit_bid(D, ex, ii, r), w) for n, ex, w in legs]
    gross = sum(n * (px - c['ask']) * 100 for n, ex, px, w in lg)
    fees = QTY * fee(c['ask']) + sum(n * fee(px) for n, ex, px, w in lg)
    s0 = D.spx[m]
    s1 = sum(n * D.spx[ex] for n, ex, px, w in lg) / QTY
    mv = side * (s1 - s0)
    return dict(day=D.d, t=t, m=m, side=side, ext=ext, entry_u=entry_u, tp1=tp1, tp2=tp2, K=c['K'], ask=c['ask'],
                delta=c['delta'], spread=c['spread'], legs=lg, exit_m=max(ex for n, ex, px, w in lg),
                reason=lg[-1][3] if len(lg) == 1 else '+'.join(w for *_, w in lg), gross=gross, fees=fees, net=gross - fees,
                pct=(gross - fees) / (QTY * c['ask'] * 100), bp=mv / s0 * 1e4, im=mv / D.IM,
                kz='AM' if t < 90 else ('PM' if 270 <= t < 330 else 'other')), 'ok'


# ---- a session under the limits ------------------------------------------------------------------------------------------------

VARIANTS = {
    'v0': dict(tf=1, bias=True, sweep=True, entry='fvg', kz='kz'),
    'V1 OTE': dict(tf=1, bias=True, sweep=True, entry='ote', kz='kz'),
    'V2 out 14:00': dict(tf=1, bias=True, sweep=True, entry='fvg', kz='kz', v2=True),
    'V3 range gate': dict(tf=1, bias=True, sweep=True, entry='fvg', kz='kz', v3=True),
    'V4 5-min': dict(tf=5, bias=True, sweep=True, entry='fvg', kz='kz'),
    'A no HTF bias': dict(tf=1, bias=False, sweep=True, entry='fvg', kz='kz'),
    'A no sweep': dict(tf=1, bias=True, sweep=False, entry='fvg', kz='kz'),
    'A no FVG': dict(tf=1, bias=True, sweep=True, entry='disp', kz='kz'),
    'A no killzones': dict(tf=1, bias=True, sweep=True, entry='fvg', kz='all'),
}


def prep(D: Day):
    b = D.b1
    D.rng30 = float(np.nanmax(b[1, :30]) - np.nanmin(b[2, :30]))
    return D


def run_day(d: str, P: dict, cut: int | None = None):
    D = prep(Day(d, cut))
    S, why, B = setups(D, P)
    trades, last = [], -1
    for s in S:
        if s['t'] + 1 <= last:
            why['trade open'] = why.get('trade open', 0) + 1
            continue
        if len(trades) >= 2:
            why['session limit'] = why.get('session limit', 0) + 1
            continue
        tr, w = simulate(D, B, P, s['t'], s['side'], s['ext'])
        if tr is None:
            why['picker: ' + w] = why.get('picker: ' + w, 0) + 1
            continue
        tr['setup'] = s
        trades.append(tr)
        last = tr['exit_m']
    return trades, why, S, D, B


def flip_trade(d: str, P: dict, tr: dict):
    """the same entry with the side flipped: stop mirrored at the same distance, its own TP1 / TP2 (prereg 5)"""
    D = prep(Day(d))
    B = Bars(D, P['tf'])
    side = -tr['side']
    ext = tr['entry_u'] + (tr['entry_u'] - tr['ext'])
    return simulate(D, B, P, tr['t'], side, ext)[0]
