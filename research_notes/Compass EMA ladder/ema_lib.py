"""
ema_lib.py — the Compass EMA ladder (PREREG_EMA_LADDER.md, 0dd8c5d): option mid charts, EMA ladder states, the best-R/R
execution contract, the GEX and premium filters, and the trade engine for the 13 versions.

Reads files only. No vendor call. Deterministic. Uses scanner_lib for the calendar, the holdout list and the guarded chain
reader; every other reader here calls the guard itself.
"""
from __future__ import annotations

import datetime as dt
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import polars as pl
from scipy.special import ndtr

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass scanner'))
import scanner_lib as S  # noqa: E402  (calendar, HELD_M, guarded chain(), day_bars, exit_quote)

NAMES = ('SPY', 'QQQ', 'IWM')
FEE = 0.68748
R = 0.045
E_FIRST, E_LAST, FLAT, X3 = 15, 360, 388, 270      # 09:45, 15:30, 15:58, 14:00 (minutes after 09:30)
NC = 390                                          # completion minutes 0..389 (row stamps); charts use 1..389
TOP = {'L1': 1, 'L2': 5, 'L3': 15}
UW = S.SP / 'features_data' / 'uw'

_MODE = {'hold': False}


def open_holdout():
    _MODE['hold'] = True
    S.open_holdout()


def guard(d: str):
    if not _MODE['hold'] and S.held_month(d):
        raise RuntimeError(f'held-out month {d} read before the holdout read')


# ---- data -----------------------------------------------------------------------------------------------------------------------------

def spot_of(name: str, d: str):
    """S[m] = close of today's latest bar stamped <= m-1 (NaN when none), m = 0..390"""
    guard(d)
    b = S.day_bars(name, d)
    if b is None:
        return None
    c = b[3]
    out = np.full(391, np.nan)
    last = np.nan
    for m in range(1, 391):
        if np.isfinite(c[m - 1]):
            last = c[m - 1]
        out[m] = last
    return out


def ny_minute(col):
    return (col.dt.convert_time_zone('America/New_York').dt.hour().cast(pl.Int32) * 60
            + col.dt.convert_time_zone('America/New_York').dt.minute().cast(pl.Int32)) - 570


@lru_cache(maxsize=256)
def gex_of(name: str, d: str):
    """G[m] = gamma_per_one_percent_move_oi of the latest row with time <= m:00 and start_time <= m-1 minute; NaN when none"""
    guard(d)
    p = UW / 'spot_exposures' / name / f'{d}.parquet'
    G = np.full(391, np.nan)
    if not p.exists():
        return G
    x = pl.read_parquet(p, columns=['time', 'start_time', 'gamma_per_one_percent_move_oi']).sort('time')
    day0 = dt.datetime.fromisoformat(d + 'T09:30:00').replace(tzinfo=__import__('zoneinfo').ZoneInfo('America/New_York'))
    t = [(v - day0).total_seconds() / 60.0 for v in x['time'].to_list()]          # minutes after 09:30, fractional
    st = [(v - day0).total_seconds() / 60.0 for v in x['start_time'].to_list()]
    g = x['gamma_per_one_percent_move_oi'].to_list()
    for m in range(391):
        best = None
        for ti, si, gi in zip(t, st, g):
            if ti <= m and si <= m - 1 and gi is not None:
                if best is None or ti >= best[0]:
                    best = (ti, gi)
        if best is not None:
            G[m] = best[1]
    return G


@lru_cache(maxsize=256)
def prem_of(name: str, d: str):
    """P[m] = sum(net_call_premium - net_put_premium) over rows with tape_time from 09:30 to m-1; NaN when no file"""
    guard(d)
    p = UW / 'net_prem_ticks' / name / f'{d}.parquet'
    P = np.full(391, np.nan)
    if not p.exists():
        return P
    x = pl.read_parquet(p, columns=['tape_time', 'net_call_premium', 'net_put_premium'])
    x = x.with_columns(ny_minute(pl.col('tape_time')).alias('k'))
    v = np.zeros(391)
    for k, c, q in x.select('k', 'net_call_premium', 'net_put_premium').iter_rows():
        if k is not None and 0 <= k < 390:
            v[k] += (c or 0.0) - (q or 0.0)
    cum = np.cumsum(v)                       # cum[k] = sum over rows stamped 0..k
    P[0] = 0.0
    P[1:] = cum[:390]                        # P[m] = rows stamped <= m-1
    return P


# ---- charts ---------------------------------------------------------------------------------------------------------------------------

def carried_mid(bid, ask):
    """valid mid (bid > 0, ask >= bid) carried forward along the row axis; [391, nK, 2]"""
    ok = np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask >= bid)
    mid = np.where(ok, 0.5 * (bid + ask), np.nan)
    out = mid.copy()
    for m in range(1, out.shape[0]):
        miss = ~np.isfinite(out[m])
        out[m][miss] = out[m - 1][miss]
    return mid, out


def ladder_states(cm, n: int):
    """for each TF in (1, 5, 15): A[m, k, r] (last completed candle above its EMA at m) and B[m, k, r] (a break completing
    at m), plus BELOW[m, k, r] (a candle completing at m closes below its EMA). cm = carried mid by row; closes = cm[c], c>=1"""
    a = 2.0 / (n + 1)
    nK = cm.shape[1]
    out = {}
    for tf in (1, 5, 15):
        comps = list(range(tf, NC, tf))                 # completion minutes (c <= 389)
        A = np.zeros((391, nK, 2), bool)
        B = np.zeros((391, nK, 2), bool)
        BL = np.zeros((391, nK, 2), bool)
        ema = np.full((nK, 2), np.nan)
        prev_above = np.zeros((nK, 2), bool)
        have_prev = np.zeros((nK, 2), bool)
        state = np.zeros((nK, 2), bool)
        ci = 0
        for m in range(391):
            if ci < len(comps) and comps[ci] == m:
                c = cm[m]
                fin = np.isfinite(c)
                seed = fin & ~np.isfinite(ema)
                ema = np.where(seed, c, np.where(fin, a * c + (1 - a) * ema, ema))
                above = fin & (c > ema)
                below = fin & (c < ema)
                B[m] = above & have_prev & ~prev_above
                BL[m] = below
                prev_above = np.where(fin, above, prev_above)
                have_prev = have_prev | fin
                state = np.where(fin, above, state)
                ci += 1
            A[m] = state
        out[tf] = (A, B, BL)
    return out


def bs_val(Sx, K, T, v, call):
    sv = v * np.sqrt(T)
    d1 = (np.log(Sx / K) + (R + 0.5 * v * v) * T) / sv
    d2 = d1 - sv
    df = np.exp(-R * T)
    c = Sx * ndtr(d1) - K * df * ndtr(d2)
    return np.where(call, c, c - Sx + K * df)


def iv_delta(price, Sx, K, T, call, lo=1e-4, hi=10.0, it=80):
    """IV by bisection on [lo, hi] from the mid, and |delta|; NaN where the mid admits no vol"""
    price, K = np.asarray(price, float), np.asarray(K, float)
    df = math.exp(-R * T)
    lo_b = np.maximum(Sx - K * df, 0) if call else np.maximum(K * df - Sx, 0)
    up_b = Sx if call else K * df
    ok = np.isfinite(price) & (price > lo_b + 1e-12) & (price < up_b) & (T > 0)
    a = np.full(price.shape, lo)
    b = np.full(price.shape, hi)
    for _ in range(it):
        mm = 0.5 * (a + b)
        up = bs_val(Sx, K, T, mm, call) > price
        b = np.where(up, mm, b)
        a = np.where(up, a, mm)
    v = 0.5 * (a + b)
    d1 = (np.log(Sx / K) + (R + 0.5 * v * v) * T) / (v * np.sqrt(T))
    dl = ndtr(d1) if call else ndtr(d1) - 1.0
    return np.where(ok, v, np.nan), np.where(ok, np.abs(dl), np.nan)


def pick_rr(K, bid, ask, m, r, Sx, M, cap):
    """the best-R/R contract of right r at row m; returns (index, delta, rr, spread) or None"""
    b, a = bid[m, :, r], ask[m, :, r]
    ok = np.isfinite(b) & np.isfinite(a) & (a > b) & (b > 0)
    mid = 0.5 * (a + b)
    sp = np.where(ok, (a - b) / mid, np.inf)
    ok &= sp <= cap + 1e-12
    if not ok.any():
        return None
    T = (390 - m) / 525600.0
    call = r == 0
    iv, de = iv_delta(np.where(ok, mid, np.nan), Sx, K, T, call)
    ok &= np.isfinite(de) & (de >= 0.15) & (de <= 0.50)
    if not ok.any():
        return None
    Sm = Sx + M if call else Sx - M
    val = bs_val(Sm, K, T, np.where(ok, iv, 0.2), call)
    rr = np.where(ok, (val - a) / a, -np.inf)
    idx = sorted(np.nonzero(ok)[0], key=lambda i: (-rr[i], sp[i], abs(K[i] - Sx), K[i]))
    i = idx[0]
    return int(i), float(de[i]), float(rr[i]), float(sp[i])


# ---- versions -------------------------------------------------------------------------------------------------------------------------

def version(vid: str, base: str = 'V1') -> dict:
    lad = {'V1': (9, 'L1'), 'V2': (9, 'L2'), 'V3': (9, 'L3'), 'V4': (20, 'L1'), 'V5': (20, 'L2'), 'V6': (20, 'L3')}
    if vid in lad:
        n, L = lad[vid]
        return dict(id=vid, n=n, L=L, gex=False, prem=False, x3=False, cap=0.12, atm=False)
    v = version(base)
    v['id'] = vid
    if vid in ('V7', 'V9'):
        v['gex'] = True
    if vid in ('V8', 'V9'):
        v['prem'] = True
    if vid == 'V10':
        v['x3'] = True
    if vid == 'V11':
        v['cap'] = 0.10
    if vid == 'V12':
        v['cap'] = 0.03
    if vid == 'V13':
        v['atm'] = True
    return v


@lru_cache(maxsize=8)
def day_data(name: str, d: str):
    guard(d)
    ch = S.chain(name, d)
    Sx = spot_of(name, d)
    if ch is None or Sx is None:
        return None
    K, bid, ask = ch
    mid, cm = carried_mid(bid, ask)
    st = {n: ladder_states(cm, n) for n in (9, 20)}
    return K, bid, ask, mid, cm, Sx, st


def atm_index(K, s):
    j = int(np.searchsorted(K, s))
    cands = [i for i in (j - 1, j) if 0 <= i < K.size]
    return min(cands, key=lambda i: (abs(K[i] - s), K[i]))


def run_day(name: str, d: str, v: dict):
    """trades and no-trade counts of version v on one name-session"""
    dd = day_data(name, d)
    if dd is None:
        return [], {}
    K, bid, ask, mid, cm, Sx, st = dd
    A1, B1, _ = st[v['n']][1]
    A5, B5, _ = st[v['n']][5]
    A15, B15, _ = st[v['n']][15]
    top = TOP[v['L']]
    BLtop = st[v['n']][top][2]
    G = gex_of(name, d) if v['gex'] else None
    P = prem_of(name, d) if v['prem'] else None
    trades, nt = [], {}
    last = E_LAST if not v['x3'] else min(E_LAST, X3 - 1)
    m = E_FIRST
    while m <= last:
        s = Sx[m]
        if not np.isfinite(s):
            m += 1
            continue
        k = atm_index(K, s)
        q = []
        for r in (0, 1):
            if v['L'] == 'L1':
                ok = B1[m, k, r]
            elif v['L'] == 'L2':
                ok = A1[m, k, r] and A5[m, k, r] and (B1[m, k, r] or B5[m, k, r])
            else:
                ok = A1[m, k, r] and A5[m, k, r] and A15[m, k, r] and (B1[m, k, r] or B5[m, k, r] or B15[m, k, r])
            if ok:
                q.append(r)
        if not q:
            m += 1
            continue
        if len(q) == 2:
            nt['both sides'] = nt.get('both sides', 0) + 1
            m += 1
            continue
        r = q[0]
        if G is not None and not (np.isfinite(G[m]) and G[m] < 0):
            nt['GEX'] = nt.get('GEX', 0) + 1
            m += 1
            continue
        if P is not None and not (np.isfinite(P[m]) and ((P[m] > 0) if r == 0 else (P[m] < 0))):
            nt['premium'] = nt.get('premium', 0) + 1
            m += 1
            continue
        if v['atm']:
            b0, a0 = bid[m, k, r], ask[m, k, r]
            if not (np.isfinite(b0) and np.isfinite(a0) and a0 > b0 > 0):
                nt['ATM no quote'] = nt.get('ATM no quote', 0) + 1
                m += 1
                continue
            ex, de, rr, sp = k, float('nan'), float('nan'), float((a0 - b0) / (0.5 * (a0 + b0)))
        else:
            M = cm[m, k, 0] + cm[m, k, 1]
            if not np.isfinite(M):
                nt['no implied move'] = nt.get('no implied move', 0) + 1
                m += 1
                continue
            pk = pick_rr(K, bid, ask, m, r, s, M, v['cap'])
            if pk is None:
                nt['no R/R contract'] = nt.get('no R/R contract', 0) + 1
                m += 1
                continue
            ex, de, rr, sp = pk
        a_in = float(ask[m, ex, r])
        mid_in = 0.5 * (a_in + float(bid[m, ex, r]))
        end = X3 if v['x3'] else FLAT
        x, why = end, ('14:00' if v['x3'] else '15:58')
        for c in range(m + 1, end + 1):
            if c % top == 0 and BLtop[c, k, r]:
                x, why = c, 'signal'
                break
        b_out = S.exit_quote(bid, x, ex, r)
        m_out = S.exit_quote(mid, x, ex, r)
        fee_out = FEE if b_out > 0 else 0.0
        usd = (b_out - a_in) * 100 - FEE - fee_out
        trades.append(dict(ver=v['id'], name=name, date=d, m=m, side='C' if r == 0 else 'P', k_sig=float(K[k]),
                           k_ex=float(K[ex]), delta=de, rr=rr, spread=sp, ask=a_in, x=x, why=why, bid_out=b_out,
                           usd=usd, ret=usd / (a_in * 100), ret_mid=(m_out - mid_in) / mid_in))
        m = x + 1
    return trades, nt


def run(names, days, v):
    T, NT = [], {}
    for d in days:
        for nm in names:
            t, nt = run_day(nm, d, v)
            T += t
            for a, b in nt.items():
                NT[a] = NT.get(a, 0) + b
    return T, NT
