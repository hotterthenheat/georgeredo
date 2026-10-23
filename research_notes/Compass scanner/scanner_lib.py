"""
scanner_lib.py — the shared pieces of the Compass scanner study (PREREG_COMPASS_SCANNER.md): paths, the calendar, the
holdout draw and the Pick / Check splits, the 1-minute bar window, the Compass scanner's indicators and score (section 1
of the prereg, word for word there), the chain readers, the Black-Scholes delta, the contract pick, the forward / implied
move of PREREG_FEATURES 2.2, and the trade engine.

Reads files only. No vendor call. Deterministic. Every random draw is seeded.
"""
from __future__ import annotations

import datetime as dt
import math
import os
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import polars as pl
from numpy.lib.stride_tricks import sliding_window_view

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OUT = HERE / 'out'
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402  (block_draws, weights_from, session_stats, the NYSE calendar 2022 →)

SP = Path(os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'))
THETA = SP / 'theta'
OI_DIR = SP / 'features_data' / 'uw' / 'oi_chain'
WORK = SP / 'scanner_work'

PRIMARY = ('SPY', 'QQQ', 'IWM')
SINGLES = ('AAPL', 'AMD', 'AMZN', 'AVGO', 'GOOGL', 'INTC', 'META', 'MSFT', 'MU', 'NVDA', 'TSLA')

# ---- the holdout (prereg section 3), drawn once ---------------------------------------------------------------------------------------

MONTHS = [f'{y}-{m:02d}' for y in range(2017, 2027) for m in range(1, 13) if '2017-06' <= f'{y}-{m:02d}' <= '2026-10']


def draw_holdout():
    k = int(np.floor(0.25 * len(MONTHS) + 0.5))                                                         # 25% of 113 -> 28
    held_m = sorted(np.random.default_rng(2026102301).choice(MONTHS, size=k, replace=False).tolist())
    kt = int(np.floor(0.20 * len(SINGLES) + 0.5))                                                       # 20% of 11 -> 2
    held_t = sorted(np.random.default_rng(2026102302).choice(list(SINGLES), size=kt, replace=False).tolist())
    return held_m, held_t


HELD_M = tuple('''2017-06 2017-09 2017-10 2018-01 2019-07 2019-08 2020-06 2020-08 2020-11 2020-12 2021-01 2021-03 2021-05 2021-11
2022-04 2022-12 2023-05 2023-11 2024-05 2024-06 2024-07 2024-08 2024-11 2025-08 2025-11 2026-03 2026-04 2026-08'''.split())
HELD_T = ('AMD', 'AVGO')
_hm, _ht = draw_holdout()
assert tuple(_hm) == HELD_M and tuple(_ht) == HELD_T, 'the holdout draw does not reproduce the prereg'
HELD_M_SET = frozenset(HELD_M)
SINGLES_OPEN = tuple(t for t in SINGLES if t not in HELD_T)

# the guard: before the one holdout read, no held-out month is read for an outcome or a selection, no held-out ticker at all
_MODE = {'hold': False}


def open_holdout():
    _MODE['hold'] = True


def held_month(d: str) -> bool:
    return d[:7] in HELD_M_SET


def guard(name: str, d: str | None = None):
    if _MODE['hold']:
        return
    if name in HELD_T:
        raise RuntimeError(f'held-out ticker {name} opened before the holdout read')
    if d is not None and held_month(d):
        raise RuntimeError(f'held-out month {d} read before the holdout read')


# ---- the calendar ------------------------------------------------------------------------------------------------------------------

PRE2022_HALF = frozenset('''2012-07-03 2012-11-23 2012-12-24 2013-07-03 2013-11-29 2013-12-24 2014-07-03 2014-11-28 2014-12-24
2015-11-27 2015-12-24 2016-11-25 2017-07-03 2017-11-24 2018-07-03 2018-11-23 2018-12-24 2019-07-03 2019-11-29 2019-12-24
2020-11-27 2020-12-24 2021-11-26'''.split())
HALF_DAYS = PRE2022_HALF | AL.NYSE_HALF_DAYS
LAST_DAY = '2026-10-21'


@lru_cache(maxsize=1)
def spy_eod_dates() -> tuple[str, ...]:
    import json
    cache = WORK / 'spy_eod_dates.json'
    if cache.exists():
        return tuple(json.loads(cache.read_text()))
    out = set()
    for f in sorted((THETA / 'fetch_cache' / 'eod_all' / 'SPY').glob('*.parquet')):
        out |= {d.isoformat() for d in pl.read_parquet(f, columns=['date'])['date'].unique().to_list()}
    WORK.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(sorted(out)))
    return tuple(sorted(out))


@lru_cache(maxsize=1)
def trading_days() -> tuple[str, ...]:
    """every NYSE trading day (half days included): SPY's option EOD dates before 2022, the audit calendar from 2022"""
    pre = [d for d in spy_eod_dates() if '2017-01-01' <= d < '2022-01-01']
    post = [d for d in AL.weekdays('2022-01-01', LAST_DAY) if d not in AL.NYSE_HOLIDAYS]
    return tuple(pre + post)


@lru_cache(maxsize=1)
def tday_set() -> frozenset:
    return frozenset(trading_days())


def full_sessions(a: str, b: str) -> list[str]:
    return [d for d in trading_days() if a <= d <= b and d not in HALF_DAYS]


@lru_cache(maxsize=1)
def tday_index() -> dict:
    return {d: i for i, d in enumerate(trading_days())}


def prev_tday(d: str) -> str | None:
    i = tday_index().get(d)
    if i is None or i == 0:
        return None
    return trading_days()[i - 1]


# ---- the splits (prereg section 3) ------------------------------------------------------------------------------------------------

SIGNAL_START, OPTION_START = '2017-06-01', '2022-11-11'


def split_sessions(layer: str) -> dict[str, list[str]]:
    a = SIGNAL_START if layer == 'signal' else OPTION_START
    s = full_sessions(a, LAST_DAY)
    nonheld = [d for d in s if not held_month(d)]
    n_pick = int(math.floor(0.6 * len(nonheld) + 0.5))
    return {'all': s, 'pick': nonheld[:n_pick], 'check': nonheld[n_pick:], 'hold': [d for d in s if held_month(d)]}


# ---- minutes ---------------------------------------------------------------------------------------------------------------------

def mtxt(m: int) -> str:
    h, mm = divmod(570 + int(m), 60)
    return f'{h:02d}:{mm:02d}'


EVAL_FIRST, EVAL_LAST = 1, 360            # 09:31 .. 15:30 (minutes after 09:30)
FLAT = 388                                # 15:58
NBAR = 390                                # bar stamps 0..389 = 09:30 .. 15:59


def _mcol():
    return (pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32)) - 570


# ---- 1-minute bars -----------------------------------------------------------------------------------------------------------------

def bar_path(name: str, d: str) -> Path | None:
    if name in PRIMARY:
        p = THETA / 'data' / 'underlying' / name / f'{d}.parquet'
    else:
        root = 'FB' if (name == 'META' and d <= '2022-06-08') else name
        p = THETA / 'fetch_cache' / 'underlying' / root / f'{d}.parquet'
    return p if p.exists() else None


@lru_cache(maxsize=8192)
def day_bars(name: str, d: str):
    """(o, h, l, c, v) arrays by bar stamp 0..389, NaN where the bar is missing or its close is null/NaN; None if no file"""
    p = bar_path(name, d)
    if p is None:
        return None
    x = pl.read_parquet(p, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']).with_columns(_mcol().alias('m'))
    x = x.filter((pl.col('m') >= 0) & (pl.col('m') < NBAR) & pl.col('close').is_not_null() & pl.col('close').is_not_nan()
                 & pl.col('high').is_not_null() & pl.col('low').is_not_null() & pl.col('open').is_not_null())
    out = []
    k = x['m'].to_numpy()
    for col in ('open', 'high', 'low', 'close', 'volume'):
        a = np.full(NBAR, np.nan)
        a[k] = x[col].to_numpy().astype(float)
        out.append(a)
    return tuple(out)


SPLITS = {'NVDA': ('2021-07-20', '2024-06-10'), 'TSLA': ('2020-08-31', '2022-08-25'), 'AAPL': ('2020-08-31',),
          'AMZN': ('2022-06-06',), 'GOOGL': ('2022-07-18',), 'AVGO': ('2024-07-15',)}


def window_days(d: str) -> list[str]:
    """the trading days among the calendar days d-2, d-1, d (prereg: sessions within the last 3 calendar days, including today)"""
    D = dt.date.fromisoformat(d)
    days = [(D - dt.timedelta(days=j)).isoformat() for j in (2, 1, 0)]
    return [x for x in days if x in tday_set()]


# ---- the Compass scanner's indicators and score (prereg section 1) ---------------------------------------------------------------

def _rsi_rows(closes: np.ndarray, kmax: int) -> np.ndarray:
    """RSI(14), simple average, for every prefix length k = 0..kmax of `closes` (out[k] uses closes[:k])"""
    out = np.full(kmax + 1, 50.0)
    if closes.size >= 15:
        dC = np.diff(closes)
        win = sliding_window_view(dC, 14)            # row j = dC[j : j + 14]; prefix k uses row k - 15
        G = np.maximum(win, 0).mean(axis=1)
        L = np.maximum(-win, 0).mean(axis=1)
        with np.errstate(divide='ignore', invalid='ignore'):
            r = np.where(L == 0, np.where(G == 0, 50.0, 100.0), 100.0 - 100.0 / (1.0 + G / np.where(L == 0, 1, L)))
        ks = np.arange(15, min(kmax, closes.size) + 1)
        out[ks] = r[ks - 15]
    return out


def bucket_closes(c: np.ndarray, nb: int | None = None) -> list[tuple[int, float]]:
    """clock-aligned 5-minute buckets of one session: (bucket index, close of the last present bar in the bucket)"""
    out = []
    for j in range(NBAR // 5 if nb is None else nb):
        seg = c[5 * j:5 * j + 5]
        ok = np.where(np.isfinite(seg))[0]
        if ok.size:
            out.append((j, float(seg[ok[-1]])))
    return out


COMP = ('rsi1', 'rsi5', 'vwap', 'rvol', 'volx', 'trend', 'bos', 'mss')


def scan(name: str, d: str) -> dict | None:
    """the scanner's state after each of today's bars completes. Index s = bar stamp 0..389 (the state at minute s + 1).
    Arrays NaN / False where bar s is missing or fewer than 30 bars are in the window. Returns None without today's bars."""
    today = day_bars(name, d)
    if today is None or not np.isfinite(today[3]).any():
        return None
    O, H, L, C, V, five = [], [], [], [], [], []
    for sp_day in SPLITS.get(name, ()):
        if window_days(d)[0] < sp_day <= d:
            raise RuntimeError(f'{name} {d}: the bar window crosses the split of {sp_day}')
    for x in window_days(d):
        b = day_bars(name, x) if x != d else today
        if b is None:
            continue
        ok = np.where(np.isfinite(b[3]))[0]
        if x != d:
            for j, a in enumerate((O, H, L, C, V)):
                a.append(b[j][ok])
            five.extend(v for _, v in bucket_closes(b[3]))
    prior_n = sum(a.size for a in C)
    prior_five = np.array(five, float)
    t_ok = np.where(np.isfinite(today[3]))[0]
    O = np.concatenate(O + [today[0][t_ok]]); H = np.concatenate(H + [today[1][t_ok]])
    L = np.concatenate(L + [today[2][t_ok]]); C = np.concatenate(C + [today[3][t_ok]])
    V = np.concatenate(V + [np.nan_to_num(today[4][t_ok])])
    n = C.size
    widx = np.full(NBAR, -1)
    widx[t_ok] = prior_n + np.arange(t_ok.size)

    # per prefix k (bars in the window) ------------------------------------------------------------------------------------------
    rsi1_k = _rsi_rows(C, n)
    # RVOL and volume_expanding
    rvol_k = np.ones(n + 1)
    volx_k = np.zeros(n + 1, bool)
    csV = np.concatenate([[0.0], np.cumsum(V)])
    for k in range(2, n + 1):
        lo = max(0, k - 21)
        cnt = (k - 1) - lo
        mv = (csV[k - 1] - csV[lo]) / cnt
        rvol_k[k] = V[k - 1] / mv if mv > 0 else 1.0
        volx_k[k] = V[k - 1] > V[k - 2]
    # swings: bar i is a swing high if H[i] = max(H[i-2..i+2]); known once bar i+2 is complete (prefix k >= i + 3)
    sh = np.zeros(n, bool)
    sl = np.zeros(n, bool)
    if n >= 5:
        hw = sliding_window_view(H, 5)
        lw = sliding_window_view(L, 5)
        sh[2:n - 2] = H[2:n - 2] >= hw.max(axis=1)
        sl[2:n - 2] = L[2:n - 2] <= lw.min(axis=1)
    SH = np.where(sh)[0]
    SL = np.where(sl)[0]

    # per bar stamp s of today ------------------------------------------------------------------------------------------------
    st = {f: np.full(NBAR, np.nan) for f in ('C', 'H', 'L', 'O', 'vwap', 'rsi1', 'rsi5', 'rvol', 'sh_last', 'sl_last',
                                              'score', 'score_b1', 'grade_pts')}
    st['valid'] = np.zeros(NBAR, bool)
    st['bull'] = np.zeros(NBAR, bool)
    st['mixed'] = np.zeros(NBAR, bool)
    st['stretch'] = np.zeros(NBAR, bool)
    st['comp'] = np.zeros((NBAR, len(COMP)))      # points each component earns in the v0 direction (before the stretch filter)
    st['comp_b1'] = np.zeros((NBAR, 2))           # B1: BOS / MSS points scored only in the trade's direction
    tc = today[3]
    tv = np.nan_to_num(today[4])
    tp = (today[1] + today[2] + today[3]) / 3.0
    cum_pv = np.nancumsum(np.where(np.isfinite(tc), tp * tv, 0.0))
    cum_v = np.nancumsum(np.where(np.isfinite(tc), tv, 0.0))
    tb = bucket_closes(tc)                            # today's buckets (index, close)
    tb_idx = np.array([j for j, _ in tb], int)
    tb_val = np.array([v for _, v in tb], float)
    for s in t_ok:
        k = widx[s] + 1
        c = C[k - 1]
        st['C'][s], st['H'][s], st['L'][s], st['O'][s] = c, H[k - 1], L[k - 1], O[k - 1]
        vw = cum_pv[s] / cum_v[s] if cum_v[s] > 0 else np.nan
        st['vwap'][s] = vw
        # 5-minute series: prior sessions' buckets + today's buckets completed by bar s (bucket j ends at stamp 5j + 4)
        f5 = np.concatenate([prior_five, tb_val[tb_idx <= (s - 4) // 5] if s >= 4 else np.array([])])
        r5 = _rsi_rows(f5, f5.size)[f5.size]
        r1 = rsi1_k[k]
        st['rsi1'][s], st['rsi5'][s] = r1, r5
        st['rvol'][s] = rvol_k[k]
        p = np.searchsorted(SH, k - 3, side='right')
        h2 = H[SH[p - 1]] if p >= 1 else np.nan
        h1 = H[SH[p - 2]] if p >= 2 else np.nan
        q = np.searchsorted(SL, k - 3, side='right')
        l2 = L[SL[q - 1]] if q >= 1 else np.nan
        l1 = L[SL[q - 2]] if q >= 2 else np.nan
        st['sh_last'][s], st['sl_last'][s] = h2, l2
        if k < 30 or not np.isfinite(vw):
            continue
        st['valid'][s] = True
        HH, LH, HL, LL = h2 > h1, h2 < h1, l2 > l1, l2 < l1          # False where a swing is missing (NaN compares False)
        up = HH and HL
        down = LH and LL
        bos_up = bool(np.isfinite(h2) and c > h2)
        bos_dn = bool(np.isfinite(l2) and c < l2)
        bos = bos_up or bos_dn
        mss_dn = bool(up and np.isfinite(l2) and c < l2)              # uptrend broken down
        mss_up = bool(down and np.isfinite(h2) and c > h2)            # downtrend broken up
        mss = mss_dn or mss_up
        bull = (c >= vw) and (r1 >= 50)
        st['bull'][s] = bull
        st['mixed'][s] = (c >= vw) != (r1 >= 50)
        aligned = (bull and up) or ((not bull) and down)
        rv = rvol_k[k]
        comp = np.array([
            15.0 if ((r1 > 55) if bull else (r1 < 45)) else 0.0,
            15.0 if ((r5 > 52) if bull else (r5 < 48)) else 0.0,
            15.0 if ((c > vw) if bull else (c < vw)) else 0.0,
            15.0 if rv >= 1.5 else (8.0 if rv >= 1.2 else 0.0),
            10.0 if volx_k[k] else 0.0,
            15.0 if aligned else 0.0,
            10.0 if bos else 0.0,
            5.0 if mss else 0.0])
        st['comp'][s] = comp
        st['comp_b1'][s] = (10.0 if (bos_up if bull else bos_dn) else 0.0, 5.0 if (mss_up if bull else mss_dn) else 0.0)
        # the stretch filter
        s1 = abs(c - vw) / vw > 0.018
        s2 = (bull and r1 >= 82) or ((not bull) and r1 <= 18)
        s3 = False
        if k >= 3:
            hl = H[k - 3:k] - L[k - 3:k]
            body = np.abs(C[k - 3:k] - O[k - 3:k])
            ratio = np.where(hl > 0, body / np.where(hl > 0, hl, 1), 0.0)
            s3 = bool((ratio > 0.75).all())
        sw = l2 if bull else h2
        s4 = bool(np.isfinite(sw) and abs(c - sw) / c > 0.025)
        stretch = s1 or s2 or s3 or s4
        st['stretch'][s] = stretch
        st['score'][s] = 0.0 if stretch else min(100.0, comp.sum())
        cb = comp.copy()
        cb[6], cb[7] = st['comp_b1'][s]
        st['score_b1'][s] = 0.0 if stretch else min(100.0, cb.sum())
    return st


def score_of(st: dict, s: int, drop: int | None = None, b1: bool = False) -> float:
    """the score at state s; drop = a component index removed (ablation); b1 = variant B1's directional BOS/MSS"""
    if not st['valid'][s]:
        return float('nan')
    if st['stretch'][s]:
        return 0.0
    comp = st['comp'][s].copy()
    if b1:
        comp[6], comp[7] = st['comp_b1'][s]
    if drop is not None:
        comp[drop] = 0.0
    return float(min(100.0, comp.sum()))


def grade(score: float) -> str:
    if score >= 90:
        return 'A+'
    if score >= 80:
        return 'A'
    if score >= 70:
        return 'B'
    if score >= 60:
        return 'C'
    return 'IGNORE'


# ---- chains ------------------------------------------------------------------------------------------------------------------------

def chain_path(name: str, d: str) -> Path | None:
    if name in PRIMARY or name == 'SPXW':
        p = THETA / 'data_full' / 'chains' / name / f'{d}.parquet'
    else:
        root = 'FB' if (name == 'META' and d <= '2022-06-08') else name
        p = THETA / 'fetch_cache' / 'chains_exp' / root / f'{d}__{d}.parquet'
    return p if p.exists() else None


@lru_cache(maxsize=64)
def chain(name: str, d: str):
    """the expiry-day chain as dense arrays: strikes (ascending), and bid/ask by [minute 0..390, strike, right (0 call, 1 put)]"""
    guard(name, d)
    p = chain_path(name, d)
    if p is None:
        return None
    x = pl.read_parquet(p, columns=['timestamp', 'strike', 'right', 'bid', 'ask']).with_columns(_mcol().alias('m'))
    x = x.filter((pl.col('m') >= 0) & (pl.col('m') <= 390))
    K = np.array(sorted(x['strike'].unique().to_list()), float)
    ki = {k: i for i, k in enumerate(K)}
    bid = np.full((391, K.size, 2), np.nan)
    ask = np.full((391, K.size, 2), np.nan)
    m = x['m'].to_numpy()
    si = np.array([ki[k] for k in x['strike'].to_list()])
    r = np.where(x['right'].to_numpy() == 'CALL', 0, 1)
    bid[m, si, r] = x['bid'].fill_null(np.nan).to_numpy().astype(float)
    ask[m, si, r] = x['ask'].fill_null(np.nan).to_numpy().astype(float)
    return K, bid, ask


def exit_quote(arr: np.ndarray, m: int, i: int, r: int) -> float:
    """a quote (bid or mid array) at minute m; a missing value takes the last non-missing in the previous 10 minutes; none -> 0"""
    for mm in range(m, max(-1, m - 11), -1):
        v = arr[mm, i, r]
        if np.isfinite(v):
            return max(0.0, float(v))
    return 0.0


# ---- open interest (UW dated chain: the open_interest field of the chain dated D) and previous-session volume (Theta EOD) ----------

UW_TICKER = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}


def occ(root: str, expiry: str, right: int, strike: float) -> str:
    return f'{root}{expiry[2:4]}{expiry[5:7]}{expiry[8:10]}{"C" if right == 0 else "P"}{int(round(strike * 1000)):08d}'


@lru_cache(maxsize=64)
def oi_day(name: str, d: str) -> dict | None:
    """{OCC symbol: open interest} from the chain dated d; None when no file (before 2023-11-21)"""
    p = OI_DIR / UW_TICKER.get(name, name) / f'{d}.parquet'
    if not p.exists():
        return None
    x = pl.read_parquet(p, columns=['option_symbol', 'open_interest'])
    return {a: int(b) for a, b in x.iter_rows() if b is not None}


@lru_cache(maxsize=16)
def eod_files(name: str) -> list[tuple[str, str, Path]]:
    root = 'FB' if name == 'FB' else name
    out = []
    for f in sorted((THETA / 'fetch_cache' / 'eod_all' / root).glob('*.parquet')):
        a, b = f.stem.split('__')
        out.append((a, b, f))
    return out


@lru_cache(maxsize=64)
def prev_volume(name: str, d: str) -> dict | None:
    """{(strike, right): volume} on the previous trading day P of the contracts expiring d; None when P's file is absent"""
    P = prev_tday(d)
    if P is None:
        return None
    root = 'FB' if (name == 'META' and P <= '2022-06-08') else name
    fs = [f for a, b, f in eod_files(root) if a <= P <= b]
    if not fs:
        return None
    x = pl.concat([pl.read_parquet(f, columns=['date', 'expiration', 'strike', 'right', 'volume']) for f in fs])
    x = x.filter((pl.col('date') == dt.date.fromisoformat(P)) & (pl.col('expiration') == dt.date.fromisoformat(d)))
    if x.height == 0:
        # the file holds P but no row of this expiry: every contract's volume is unknown -> 0 (stated)
        return {}
    return {(float(k), 0 if r == 'C' else 1): int(v or 0) for k, r, v in x.select('strike', 'right', 'volume').iter_rows()}


# ---- Black-Scholes delta solved from the mid (r = 0.045, no dividend, T to the expiry's 16:00) --------------------------------------

R_RATE = 0.045


def _ncdf(x):
    from scipy.special import ndtr
    return ndtr(x)


def bs_price(S, K, T, v, call):
    sv = v * np.sqrt(T)
    d1 = (np.log(S / K) + (R_RATE + 0.5 * v * v) * T) / sv
    d2 = d1 - sv
    df = np.exp(-R_RATE * T)
    c = S * _ncdf(d1) - K * df * _ncdf(d2)
    return np.where(call, c, c - S + K * df)


def bs_delta(price, S, K, T, call, lo=1e-4, hi=10.0, it=80):
    """|delta| per contract (vectorized bisection on the vol); NaN where the mid admits no vol in [lo, hi]"""
    price, K = np.asarray(price, float), np.asarray(K, float)
    call = np.asarray(call, bool)
    df = math.exp(-R_RATE * T)
    lo_b = np.where(call, np.maximum(S - K * df, 0), np.maximum(K * df - S, 0))
    up_b = np.where(call, S, K * df)
    ok = np.isfinite(price) & (price > lo_b + 1e-12) & (price < up_b) & (T > 0)
    a = np.full(price.shape, lo)
    b = np.full(price.shape, hi)
    for _ in range(it):
        m = 0.5 * (a + b)
        up = bs_price(S, K, T, m, call) > price
        b = np.where(up, m, b)
        a = np.where(up, a, m)
    v = 0.5 * (a + b)
    d1 = (np.log(S / K) + (R_RATE + 0.5 * v * v) * T) / (v * np.sqrt(T))
    dl = np.where(call, _ncdf(d1), _ncdf(d1) - 1.0)
    return np.where(ok, np.abs(dl), np.nan)


# ---- the contract (prereg section 1 "Contract", and the variants) ------------------------------------------------------------------

def pick_contract(name: str, d: str, m: int, bull: bool, E: float, oi_mode: str = 'v0', spread_max: float = 0.12,
                  delta_pick: bool = False):
    """the 0DTE contract the rule buys at minute m. oi_mode: 'v0' (OI >= 250 filter and OI in the ranking), 'nofilter' (the
    filter off, OI still ranked), 'none' (no OI anywhere: liquidity = min(vol/100, 5), the OI key dropped).
    Returns (dict | None, reason)."""
    ch = chain(name, d)
    if ch is None:
        return None, 'no chain file'
    K, bid, ask = ch
    r = 0 if bull else 1
    b = bid[m, :, r]
    a = ask[m, :, r]
    if not np.isfinite(b).any() and not np.isfinite(a).any():
        return None, 'no quote at the entry minute'
    vol = prev_volume(name, d)
    if vol is None:
        return None, 'no previous-session volume file'
    oi = oi_day(name, d) if oi_mode != 'none' else None
    if oi_mode != 'none' and oi is None:
        return None, 'no open interest file'
    mid = (a + b) / 2.0
    q_ok = np.isfinite(a) & np.isfinite(b) & (a > b) & (b > 0)
    spr = np.where(q_ok, (a - b) / np.where(q_ok, mid, 1), np.inf)
    T = (390 - m) / 525600.0
    dlt = bs_delta(np.where(q_ok, mid, np.nan), E, K, T, np.full(K.shape, bull))
    v_arr = np.array([(vol or {}).get((float(k), r), 0) for k in K], float)
    root = 'SPXW' if name == 'SPXW' else name
    if oi is not None:
        o_arr = np.array([oi.get(occ(root, d, r, k), 0) for k in K], float)
    else:
        o_arr = np.zeros(K.size)
    f_q = q_ok
    f_sp = f_q & (spr <= spread_max + 1e-12)
    f_dl = f_sp & np.isfinite(dlt) & (dlt >= 0.30 - 1e-12) & (dlt <= 0.60 + 1e-12)
    f_v = f_dl & (v_arr >= 100)
    f_oi = f_v & ((o_arr >= 250) if oi_mode == 'v0' else True)
    cand = np.where(f_oi)[0]
    if cand.size == 0:
        if not f_q.any():
            why = 'no standing quote (ask > bid > 0)'
        elif not f_sp.any():
            why = 'spread'
        elif not f_dl.any():
            why = 'delta'
        elif not f_v.any():
            why = 'volume'
        else:
            why = 'open interest'
        return None, why
    rows = []
    for i in cand:
        liq = min(v_arr[i] / 100.0, 5.0) + (min(o_arr[i] / 250.0, 5.0) if oi_mode != 'none' else 0.0)
        dsc = 1.0 - abs(dlt[i] - 0.45) / 0.15
        last = (1.0 - spr[i] / 0.12) + 1.0 / (1.0 + abs(0 - 7))           # DTE = 0 for every contract here
        key = (liq,) + ((o_arr[i],) if oi_mode != 'none' else ()) + (v_arr[i], dsc, last)
        if delta_pick:                                                     # E3: nearest |delta| 0.45 first, then v0's tuple
            key = (-round(abs(dlt[i] - 0.45), 12),) + key
        key = key + (-abs(K[i] - E), -K[i])                                # ties: nearest the underlying, then the lower strike
        rows.append((key, i))
    rows.sort(key=lambda t: t[0], reverse=True)
    i = rows[0][1]
    return dict(K=float(K[i]), i=int(i), r=r, ask=float(a[i]), bid=float(b[i]), mid=float(mid[i]), spread=float(spr[i]),
                delta=float(dlt[i]), vol=int(v_arr[i]), oi=int(o_arr[i])), 'ok'


# ---- the forward and the implied move (PREREG_FEATURES 2.2) -----------------------------------------------------------------------

def forward_im(name: str, d: str, m: int):
    """(K*, F, IM) from the chain row stamped m: K* the strike with both sides standing and |C_mid - P_mid| smallest (ties:
    the lower strike), F = K* + C_mid - P_mid, IM = C_mid + P_mid; None when no strike has both sides standing"""
    ch = chain(name, d)
    if ch is None:
        return None
    K, bid, ask = ch
    cb, ca, pb, pa = bid[m, :, 0], ask[m, :, 0], bid[m, :, 1], ask[m, :, 1]
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
    return float(K[i]), float(K[i] + cm[i] - pm[i]), float(IM)


IM_MINUTE = 1          # the "09:30 implied move" is read on the row stamped 09:31: every stored 09:30 row is unquoted


# ---- the bootstrap at any level ---------------------------------------------------------------------------------------------------

def pct(x: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float('nan'), float('nan')
    return float(np.percentile(x, 100 * alpha / 2)), float(np.percentile(x, 100 * (1 - alpha / 2)))


def boot_W(n: int, block: int = 20) -> np.ndarray:
    return AL.weights_from(AL.block_draws(n, block), n)
