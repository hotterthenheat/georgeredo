"""Shared definitions for the SPY/QQQ/IWM 0DTE short-premium grid (see PREREGISTRATION.md).
Reads the local ThetaData dataset through research/thetadata/dataset/load.py; never contacts ThetaData."""
import os, sys, csv, math, datetime as dt
import numpy as np
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'research', 'thetadata', 'dataset'))
import load as L  # noqa: E402

SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
WORK = os.environ.get('HWR_WORK', SP + '/hwr_grid')          # per-trade data (outside the repo)
OUT = os.path.join(HERE, 'results')
FEE = 0.70
M0 = 570                                                      # 09:30 in minutes after midnight
NM = 391                                                      # 09:30 .. 16:00
TICKERS = ('SPY', 'QQQ', 'IWM')
FIRST = {'SPY': '2022-11-11', 'QQQ': '2022-11-11', 'IWM': '2024-04-19'}
LAST = '2026-10-09'
TRAIN = ('2022-11-11', '2024-12-31')
TEST = ('2025-01-02', '2026-10-09')
ENTRIES = {'10:00': 600, '11:00': 660, '13:00': 780, '14:05': 845}
RAND_SEEDS = (11, 12, 13, 14, 15)
RAND_LO, RAND_HI = 600, 870                                   # 10:00 .. 14:30 inclusive
MON_LAST = 15 * 60 + 54                                       # last monitoring minute
CLOSE_M = 15 * 60 + 55                                        # E1 / E0 exit row
SETTLE_BAR = 15 * 60 + 59                                     # bar whose close is the 16:00 close
SK = (('S', 0.0), ('S', 0.5), ('S', 1.0), ('S', 1.5), ('I', 0.5), ('I', 1.0), ('I', 1.5))
TPS = (0, 25, 50)
STOPS = (0, 1, 2)
EXITS = ('E1', 'E2')                                          # grid exits; 'E0' is a diagnostic
FILTERS = ('F0', 'F1', 'F2', 'F3')


def sk_name(s, k): return f'{s}{k:g}'


def period_of(d):
    if TRAIN[0] <= d <= TRAIN[1]: return 'TRAIN'
    if TEST[0] <= d <= TEST[1]: return 'TEST'
    return None


def early_closes():
    return {r['date'] for r in csv.DictReader(open(L.CALENDAR)) if r['type'] == 'early_close'}


def fomc_days():
    f = os.path.join(REPO, 'research', 'thetadata', 'vol_filters', 'events.csv')
    return {r['date'] for r in csv.DictReader(open(f)) if r['event'] == 'FOMC'}


def month_ends():
    """Last NYSE session of each calendar month (sessions through 2026-12-31, so 2026-10-09 is not a month-end)."""
    s = L.trading_sessions('2017-06-01', '2026-12-31')
    return {a for a, b in zip(s, s[1:]) if a[:7] != b[:7]} | {s[-1]}


def calendar_sessions(tk):
    """Committed contract-day list for the random baseline: calendar sessions (not a cache listing)."""
    return L.trading_sessions(FIRST[tk], LAST)


def random_minutes():
    """{(seed, ticker, date): minute} — seed s draws one minute per (ticker, date) in sorted order (SPY, QQQ, IWM; dates ascending)."""
    keys = [(tk, d) for tk in TICKERS for d in calendar_sessions(tk)]
    out = {}
    for s in RAND_SEEDS:
        rng = np.random.default_rng(s)
        mins = rng.integers(RAND_LO, RAND_HI + 1, size=len(keys))
        for (tk, d), m in zip(keys, mins): out[(s, tk, d)] = int(m)
    return out


def mstr(m): return f'{m // 60:02d}:{m % 60:02d}'


# ---------------------------------------------------------------- day arrays
def day_arrays(tk, d):
    """Quote cube for one ticker-session: strikes (nK,), bid/ask raw (2, nK, NM) [0 = CALL, 1 = PUT], usable mask, forward-filled
    bid/ask, and the underlying minute closes (NM,).  Returns None when a file is missing."""
    try:
        c = L.chain(tk, d)
        u = L.underlying(tk, d)
    except FileNotFoundError:
        return None
    c = c.with_columns(((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32)) - M0).alias('mi'))
    c = c.filter((pl.col('mi') >= 0) & (pl.col('mi') < NM))
    strikes = np.array(sorted(c['strike'].unique().to_list()), float)
    ki = {k: i for i, k in enumerate(strikes)}
    bid = np.full((2, len(strikes), NM), np.nan); ask = np.full((2, len(strikes), NM), np.nan)
    r = (c['right'].to_numpy() == 'PUT').astype(int)
    k = np.array([ki[x] for x in c['strike'].to_list()])
    mi = c['mi'].to_numpy()
    b = c['bid'].to_numpy().astype(float); a = c['ask'].to_numpy().astype(float)   # nulls -> nan
    bid[r, k, mi] = b; ask[r, k, mi] = a
    with np.errstate(invalid='ignore'):
        ok = np.isfinite(bid) & np.isfinite(ask) & (ask > 0) & (ask >= bid) & (bid >= 0)
    idx = np.where(ok, np.arange(NM)[None, None, :], 0)
    idx = np.maximum.accumulate(idx, axis=2)
    seen = np.maximum.accumulate(ok, axis=2)
    bff = np.take_along_axis(np.where(ok, bid, np.nan), idx, axis=2); aff = np.take_along_axis(np.where(ok, ask, np.nan), idx, axis=2)
    bff[~seen] = np.nan; aff[~seen] = np.nan
    u = u.with_columns(((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32)) - M0).alias('mi'))
    close = np.full(NM, np.nan)
    uu = u.filter((pl.col('mi') >= 0) & (pl.col('mi') < NM) & pl.col('close').is_not_null())
    close[uu['mi'].to_numpy()] = uu['close'].to_numpy().astype(float)
    return dict(strikes=strikes, bid=bid, ask=ask, ok=ok, bff=bff, aff=aff, close=close)


def last_close_before(close, mi):
    """Close of the bar stamped mi-1, or the last non-null close before minute index mi."""
    j = mi - 1
    while j >= 0 and not np.isfinite(close[j]): j -= 1
    return float(close[j]) if j >= 0 else float('nan')


# ---------------------------------------------------------------- bootstrap (identical draws to straddle_nbbo/analyze.py boot_ci)
def boot_weights(n_days, B=5000, seed=7):
    """(B, n_days) matrix of how often each day is drawn: rng.integers(0, J, (B, J)) exactly as boot_ci, counted per row."""
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n_days, (B, n_days))
    W = np.zeros((B, n_days), np.float64)
    rows = np.repeat(np.arange(B), n_days)
    np.add.at(W, (rows, idx.ravel()), 1.0)
    return W


def boot_ci(v, clusters=None, B=5000, seed=7):
    """Copied from research/thetadata/straddle_nbbo/analyze.py (itself from research/short_vol_session/common.py)."""
    v = np.asarray(v, float); n = len(v)
    if n < 5: return (float('nan'), float('nan'))
    rng = np.random.default_rng(seed)
    if clusters is None:
        means = np.empty(B); step = max(1, min(B, 20_000_000 // n))
        for s in range(0, B, step):
            idx = rng.integers(0, n, (min(step, B - s), n)); means[s:s + idx.shape[0]] = v[idx].mean(1)
    else:
        keys = {}; cl = np.array([keys.setdefault(c, len(keys)) for c in clusters]); Jn = len(keys)
        S = np.bincount(cl, weights=v, minlength=Jn); N = np.bincount(cl, minlength=Jn).astype(float)
        idx = rng.integers(0, Jn, (B, Jn)); means = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def maxdd(v):
    c = np.cumsum(v); peak = np.maximum.accumulate(np.concatenate([[0.0], c]))[1:]
    return float((c - peak).min()) if len(c) else 0.0
