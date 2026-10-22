"""
fcommon.py — the shared pieces of the Compass features study (PREREG_FEATURES.md, commit a2e14e4): paths, the calendar,
the holdout split, the fees and the return, the Black-76 solver, the forward / implied move / strike distance (prereg 2.2),
the strike buckets (2.4) and the readers of the stored files.

Reads files only. No vendor call. Deterministic. POLARS_MAX_THREADS=1 is expected from the caller's environment when run
in parallel workers.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
FOLDER = HERE.parent
REPO = HERE.parents[2]
OUT = FOLDER / 'out'
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402  (expected_sessions, block_draws, weights_from, pct_ci, session_stats, NYSE calendars)

SP = Path(os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'))
THETA = SP / 'theta'
UW = SP / 'features_data' / 'uw'
STAGING = SP / 'features_data' / 'theta_staging'
WORK = SP / 'features_work'
PREREG = FOLDER / 'PREREG_FEATURES.md'
PREREG_COMMIT = 'a2e14e4'

# ---- the universe and the holdout (prereg sections 1 and 5) -------------------------------------------------------------------------

TICKERS = ['SPY', 'QQQ', 'IWM', 'SPXW', 'AAPL', 'AMZN', 'AVGO', 'GOOGL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'INTC', 'MU', 'META']
ETFS = ('SPY', 'QQQ', 'IWM')
INDEX = ('SPY', 'QQQ', 'IWM', 'SPXW')
SINGLES = ('AAPL', 'AMZN', 'AVGO', 'GOOGL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'INTC', 'MU', 'META')
MONTHS = [f'{y}-{m:02d}' for y in range(2012, 2027) for m in range(1, 13) if '2012-06' <= f'{y}-{m:02d}' <= '2026-10']


def draw_holdout():
    """exactly the prereg's code (section 5)"""
    held_t = sorted(np.random.default_rng(20261022).choice(TICKERS, size=3, replace=False).tolist())
    k = int(np.floor(0.25 * len(MONTHS) + 0.5))
    held_m = sorted(np.random.default_rng(20261023).choice(MONTHS, size=k, replace=False).tolist())
    return held_t, held_m


HELD_T = ('AVGO', 'MU', 'QQQ')
HELD_M = tuple('''2012-11 2013-05 2014-06 2014-09 2015-01 2015-03 2015-06 2015-07 2015-09 2015-10 2015-11 2016-01 2016-04 2016-08
2017-02 2017-06 2018-05 2018-12 2019-01 2019-06 2019-08 2020-01 2021-09 2021-10 2021-12 2022-03 2022-09 2022-10 2023-02 2023-03
2023-06 2023-09 2023-10 2024-01 2024-06 2024-11 2025-01 2025-06 2025-10 2025-11 2026-04 2026-06 2026-10'''.split())
_ht, _hm = draw_holdout()
assert tuple(_ht) == HELD_T and tuple(_hm) == HELD_M, 'the holdout draw does not reproduce the prereg'
HELD_M_SET = frozenset(HELD_M)
EXPL_T = tuple(t for t in TICKERS if t not in HELD_T)

# the split a process may touch: set once by the caller; every reader checks it
_MODE = {'split': None}


def set_split(split: str):
    assert split in ('expl', 'hold')
    _MODE['split'] = split


def guard_ticker(t: str):
    """a held-out ticker's file is never opened before the final test"""
    u = {'SPX': 'SPXW', 'FB': 'META'}.get(t, t)
    if _MODE['split'] != 'hold' and u in HELD_T:
        raise RuntimeError(f'held-out ticker {t} opened outside the holdout run')


def held_month(day: str) -> bool:
    return day[:7] in HELD_M_SET


# ---- the calendar (prereg 2.1) ------------------------------------------------------------------------------------------------------

PRE2022_HALF = frozenset('''2012-07-03 2012-11-23 2012-12-24 2013-07-03 2013-11-29 2013-12-24 2014-07-03 2014-11-28 2014-12-24
2015-11-27 2015-12-24 2016-11-25 2017-07-03 2017-11-24 2018-07-03 2018-11-23 2018-12-24 2019-07-03 2019-11-29 2019-12-24
2020-11-27 2020-12-24 2021-11-26'''.split())
HALF_DAYS = PRE2022_HALF | AL.NYSE_HALF_DAYS
FIRST_DAY, LAST_DAY = '2012-06-01', '2026-10-21'


@lru_cache(maxsize=1)
def spy_eod_dates() -> tuple[str, ...]:
    out = set()
    for f in sorted((THETA / 'fetch_cache' / 'eod_all' / 'SPY').glob('*.parquet')):
        out |= {d.isoformat() for d in pl.read_parquet(f, columns=['date'])['date'].unique().to_list()}
    return tuple(sorted(out))


@lru_cache(maxsize=1)
def trading_days() -> tuple[str, ...]:
    """every NYSE trading day (half days included): SPY's EOD dates before 2022, the rule from 2022"""
    pre = [d for d in spy_eod_dates() if FIRST_DAY <= d < '2022-01-01']
    post = [d for d in AL.weekdays('2022-01-01', LAST_DAY) if d not in AL.NYSE_HOLIDAYS]
    return tuple(pre + post)


@lru_cache(maxsize=1)
def sessions() -> tuple[str, ...]:
    """full sessions (prereg 2.1): half days out"""
    return tuple(d for d in trading_days() if d not in HALF_DAYS)


@lru_cache(maxsize=1)
def calendar_disagreements() -> list[tuple[str, str]]:
    """2022 →: the rule's full sessions against SPY's EOD file dates minus half days (listed in the report)"""
    rule = set(AL.expected_sessions('2022-01-01', LAST_DAY))
    files = {d for d in spy_eod_dates() if d >= '2022-01-01' and d not in HALF_DAYS}
    return sorted([(d, 'rule only') for d in rule - files] + [(d, 'files only') for d in files - rule])


@lru_cache(maxsize=1)
def session_index() -> dict[str, int]:
    return {d: i for i, d in enumerate(sessions())}


@lru_cache(maxsize=1)
def tday_index() -> dict[str, int]:
    return {d: i for i, d in enumerate(trading_days())}


def prev_tday(d: str) -> str | None:
    td = trading_days()
    i = tday_index().get(d)
    if i is None:
        import bisect
        i = bisect.bisect_left(td, d)
        return td[i - 1] if i > 0 else None
    return td[i - 1] if i > 0 else None


def next_tday(d: str) -> str | None:
    td = trading_days()
    import bisect
    i = bisect.bisect_right(td, d)
    return td[i] if i < len(td) else None


def prev_session(d: str) -> str | None:
    import bisect
    s = sessions()
    i = bisect.bisect_left(s, d)
    return s[i - 1] if i > 0 else None


def nth_session_after(d: str, n: int) -> str | None:
    import bisect
    s = sessions()
    i = bisect.bisect_right(s, d) + n - 1
    return s[i] if i < len(s) else None


def sessions_between(a: str, b: str) -> list[str]:
    """full sessions in (a, b]"""
    import bisect
    s = sessions()
    return list(s[bisect.bisect_right(s, a):bisect.bisect_right(s, b)])


def last_trading_day(expiry: str) -> str:
    """an expiration's last trading day: the listed date if it trades, else the trading day before it (the Saturday-dated
    monthlies before 2015, a Good Friday)"""
    if expiry in tday_index():
        return expiry
    return prev_tday(expiry)


def cal_days(a: str, b: str) -> int:
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def window_held(entry: str, exit_: str) -> bool:
    """a trade belongs to the holdout if any session from its entry to its exit falls in a held-out month"""
    m = entry[:7]
    while m <= exit_[:7]:
        if m in HELD_M_SET:
            return True
        y, mo = int(m[:4]), int(m[5:])
        mo += 1
        if mo == 13:
            y, mo = y + 1, 1
        m = f'{y}-{mo:02d}'
    return False


# ---- fees and the return (prereg 2.6) ----------------------------------------------------------------------------------------------

FEE_ETF = 0.65 + 0.01248 + 0.025                   # 0.68748
FEE_SPXW_LO, FEE_SPXW_HI = 1.18748, 1.27748


def fee(name: str, px: float) -> float:
    if not (px > 0):
        return 0.0
    if name == 'SPXW':
        return FEE_SPXW_LO if px < 1.0 - 1e-9 else FEE_SPXW_HI
    return FEE_ETF


def ret(name: str, ask: float, exit_px: float, exit_fee: float) -> tuple[float, float]:
    """(return as a fraction of the debit, dollar P&L) for one contract"""
    pnl = (exit_px - ask) * 100.0 - fee(name, ask) - exit_fee
    return pnl / (ask * 100.0), pnl


# ---- Black-76 on the parity forward, discount factor 1 (prereg 2.2) ----------------------------------------------------------------

def _ncdf(x):
    from scipy.special import ndtr
    return ndtr(x)


def b76(F, K, T, v, is_call):
    F, K, T, v = (np.asarray(a, float) for a in (F, K, T, v))
    sv = v * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sv * sv) / sv
    d2 = d1 - sv
    c = F * _ncdf(d1) - K * _ncdf(d2)
    p = c - (F - K)
    return np.where(is_call, c, p)


def b76_iv(price, F, K, T, is_call, lo=1e-4, hi=8.0, it=80):
    """vectorized bisection; NaN where the price is outside (intrinsic, upper bound)"""
    price, F, K, T = (np.asarray(a, float) for a in (price, F, K, T))
    is_call = np.asarray(is_call, bool)
    intr = np.where(is_call, np.maximum(F - K, 0), np.maximum(K - F, 0))
    upper = np.where(is_call, F, K)
    ok = np.isfinite(price) & np.isfinite(F) & (T > 0) & (price > intr + 1e-12) & (price < upper)
    a = np.full(price.shape, lo)
    b = np.full(price.shape, hi)
    for _ in range(it):
        m = 0.5 * (a + b)
        pm = b76(F, K, T, m, is_call)
        up = pm > price
        b = np.where(up, m, b)
        a = np.where(up, a, m)
    v = 0.5 * (a + b)
    return np.where(ok, v, np.nan)


def b76_delta(F, K, T, v, is_call):
    F, K, T, v = (np.asarray(a, float) for a in (F, K, T, v))
    sv = v * np.sqrt(T)
    d1 = (np.log(F / K) + 0.5 * sv * sv) / sv
    return np.where(is_call, _ncdf(d1), _ncdf(d1) - 1.0)


def years(minutes: float) -> float:
    return minutes / 525600.0


# ---- the forward, the implied move, x (prereg 2.2) and the buckets (2.4) ------------------------------------------------------------

def forward_im(K: np.ndarray, cb, ca, pb, pa):
    """K ascending; call/put bid/ask arrays (NaN = no quote). → (K*, F, IM, C_mid*, P_mid*) or None when no strike has both
    a standing call and a standing put"""
    cs = (cb > 0) & (ca > 0) & (ca >= cb)
    ps = (pb > 0) & (pa > 0) & (pa >= pb)
    both = cs & ps
    if not both.any():
        return None
    cm = (cb + ca) / 2.0
    pm = (pb + pa) / 2.0
    d = np.where(both, np.abs(cm - pm), np.inf)
    i = int(np.argmin(d))                 # first minimum = the lower strike on a tie (K ascending)
    F = K[i] + cm[i] - pm[i]
    IM = cm[i] + pm[i]
    if not (IM > 0):
        return None
    return float(K[i]), float(F), float(IM), float(cm[i]), float(pm[i])


BUCKETS = (('ITM', -0.50, -0.15, -0.325), ('ATM', -0.15, 0.15, 0.0), ('OTM1', 0.15, 0.50, 0.325), ('OTM2', 0.50, 1.00, 0.75),
           ('OTM3', 1.00, 1.50, 1.25))
BUCKET_NAMES = tuple(b[0] for b in BUCKETS)


def in_bucket(x: np.ndarray, name: str) -> np.ndarray:
    eps = 1e-12
    if name == 'ITM':
        return (x >= -0.50 - eps) & (x < -0.15 - eps)
    if name == 'ATM':
        return (x >= -0.15 - eps) & (x <= 0.15 + eps)
    if name == 'OTM1':
        return (x > 0.15 + eps) & (x <= 0.50 + eps)
    if name == 'OTM2':
        return (x > 0.50 + eps) & (x <= 1.00 + eps)
    return (x > 1.00 + eps) & (x <= 1.50 + eps)


def select_buckets(K: np.ndarray, standing: np.ndarray, x: np.ndarray) -> dict[str, int]:
    """bucket → index into K of the contract whose x is nearest the bucket centre (ties: the lower strike)"""
    out = {}
    for name, _, _, c in BUCKETS:
        ok = standing & in_bucket(x, name)
        if ok.any():
            d = np.where(ok, np.abs(x - c), np.inf)
            dmin = d.min()
            cand = np.where(np.abs(d - dmin) <= 1e-12)[0]
            out[name] = int(cand[np.argmin(K[cand])])
    return out


def bucket_of_value(v: float) -> str:
    """ES3: the strike bucket containing x_RM (x_RM ≤ 0.15: ATM; above 1.5: OTM3)"""
    if v <= 0.15:
        return 'ATM'
    if v <= 0.50:
        return 'OTM1'
    if v <= 1.00:
        return 'OTM2'
    return 'OTM3'


# ---- entry minutes (prereg 2.3) ------------------------------------------------------------------------------------------------------

ENTRY_TXT = ('09:45', '10:15', '10:45', '11:15', '11:45', '12:15', '12:45', '13:15', '13:45', '14:15', '14:45', '15:15', '15:30')


def mi(t: str) -> int:
    h, m = t.split(':')
    return int(h) * 60 + int(m) - 570


ENTRY_M = tuple(mi(t) for t in ENTRY_TXT)
FLAT = mi('15:58')            # 388
X3_M = mi('14:00')            # 270
EOD_M = 390                   # an EOD entry is stamped 16:00 for every point-in-time rule
NMIN = 391


def mtxt(m: int) -> str:
    h, mm = divmod(570 + int(m), 60)
    return f'{h:02d}:{mm:02d}'


# ---- file locations ------------------------------------------------------------------------------------------------------------------

def chain_0dte_path(name: str, d: str) -> Path | None:
    """the same-day (expiry-day) 1-minute chain; None when not on disk"""
    guard_ticker(name)
    if name in INDEX:
        p = THETA / 'data_full' / 'chains' / name / f'{d}.parquet'
        if p.exists():
            return p
        s = STAGING / '_staging'
        if s.exists():
            for q in sorted(s.glob(f'*/data_full/chains/{name}/{d}.parquet')):
                return q
        return None
    root = 'FB' if (name == 'META' and d <= '2022-06-08') else name
    p = THETA / 'fetch_cache' / 'chains_exp' / root / f'{d}__{d}.parquet'
    if p.exists():
        return p
    q = STAGING / 'fetch_cache' / 'chains_exp' / root / f'{d}__{d}.parquet'
    return q if (q.exists() and staged_sound(q)) else None


@lru_cache(maxsize=1)
def staging_failures() -> dict[str, list[str]]:
    """the fetch's verification failures, by staged file (its log's 'FAILED verify' lines; the last one a file got)"""
    import ast
    out = {}
    log = SP / 'features_data' / 'theta_stdout.log'
    if log.exists():
        for line in log.read_text(errors='replace').splitlines():
            if 'FAILED verify (kept in staging)' in line:
                rest = line.split('FAILED verify (kept in staging) ', 1)[1]
                f, probs = rest.split(' ', 1)
                try:
                    out[f] = ast.literal_eval(probs)
                except Exception:
                    out[f] = [probs]
    return out


@lru_cache(maxsize=256)
def staged_sound(q: Path) -> bool:
    """a staged single-name chain is read only when the fetch's one complaint was 'N mids that are not (bid + ask) / 2' and
    those N rows are exactly the rows without a quote (NaN mid: the verifier's NaN comparison), every quoted row's mid being
    (bid + ask) / 2, no bid above its ask and no negative price; any other complaint (one-sided strikes, too few rows or
    strikes) and the file is treated as not on disk"""
    import re
    rel = str(q.relative_to(STAGING))
    probs = staging_failures().get(rel)
    if not probs or len(probs) != 1:
        return False
    m = re.fullmatch(r'(\d+) mids that are not \(bid \+ ask\) / 2', probs[0])
    if not m:
        return False
    x = pl.read_parquet(q, columns=['bid', 'ask', 'mid'])
    nan_mid = int(x['mid'].is_nan().sum() + x['mid'].is_null().sum())
    qd = x.filter(pl.col('bid').is_not_nan() & pl.col('ask').is_not_nan() & pl.col('bid').is_not_null() & pl.col('ask').is_not_null())
    ok_mid = bool(((qd['mid'] - (qd['bid'] + qd['ask']) / 2).abs() <= 1e-9).all())
    sound = bool(((qd['bid'] >= 0) & (qd['ask'] >= 0)).all()) and int(((qd['bid'] > qd['ask']) & (qd['ask'] > 0)).sum()) == 0
    return nan_mid == int(m.group(1)) and ok_mid and sound


def staged(p: Path | None) -> bool:
    return p is not None and str(p).startswith(str(STAGING))


@lru_cache(maxsize=64)
def chain_days(name: str) -> tuple[str, ...]:
    guard_ticker(name)
    if name in INDEX:
        ds = {f.stem for f in (THETA / 'data_full' / 'chains' / name).glob('*.parquet')}
        s = STAGING / '_staging'
        ds |= {f.stem for f in s.glob(f'*/data_full/chains/{name}/*.parquet')} if s.exists() else set()
        return tuple(sorted(ds))
    out = set()
    for root in (('FB', 'META') if name == 'META' else (name,)):
        for base in (THETA / 'fetch_cache' / 'chains_exp' / root, STAGING / 'fetch_cache' / 'chains_exp' / root):
            if base.exists():
                for f in base.glob('*.parquet'):
                    a, b = f.stem.split('__')
                    if a == b and (root != 'META' or a > '2022-06-08') and (root != 'FB' or a <= '2022-06-08'):
                        out.add(a)
    return tuple(sorted(out))


def bars_path(u: str, d: str) -> Path | None:
    """1-minute underlying bars: the ETFs' stored bars, the singles' fetched bars (FB before 2022-06-09)"""
    guard_ticker(u)
    if u in ETFS:
        p = THETA / 'data' / 'underlying' / u / f'{d}.parquet'
    else:
        root = 'FB' if (u == 'META' and d <= '2022-06-08') else u
        p = THETA / 'fetch_cache' / 'underlying' / root / f'{d}.parquet'
        if not p.exists():
            q = STAGING / 'fetch_cache' / 'underlying' / root / f'{d}.parquet'
            p = q if q.exists() else p
    return p if p.exists() else None


def mcol(c='timestamp'):
    return (pl.col(c).dt.hour().cast(pl.Int32) * 60 + pl.col(c).dt.minute().cast(pl.Int32)) - 570


def minute_array(df: pl.DataFrame, val: str) -> np.ndarray:
    a = np.full(NMIN, np.nan)
    if df.height:
        k = df['m'].to_numpy()
        v = df[val].to_numpy().astype(float)
        ok = (k >= 0) & (k < NMIN) & np.isfinite(v)
        a[k[ok]] = v[ok]
    return a


@lru_cache(maxsize=4096)
def bars(u: str, d: str):
    """(high, low, close) by bar stamp minute 0..390; NaN where none. For SPXW the SPX prints (high = low = close = print)."""
    if u in ('SPXW', 'SPX'):
        p = THETA / 'data' / 'index' / 'SPX' / f'{d}.parquet'
        if not p.exists():
            return None
        x = pl.read_parquet(p).with_columns(mcol().alias('m')).filter(pl.col('price').is_not_null() & pl.col('price').is_not_nan())
        a = minute_array(x, 'price')
        return a, a, a
    p = bars_path(u, d)
    if p is None:
        return None
    x = pl.read_parquet(p, columns=['timestamp', 'high', 'low', 'close']).with_columns(mcol().alias('m'))
    x = x.filter(pl.col('close').is_not_null() & pl.col('close').is_not_nan())
    return minute_array(x, 'high'), minute_array(x, 'low'), minute_array(x, 'close')


def price_at_entry(u: str, d: str, m: int) -> float:
    """the underlying at entry minute m: the close of the bar stamped m − 1 (ETF, single); SPXW: the SPX print at m.
    An EOD entry (m = 390) reads the 15:59 bar (SPX: the 15:59 print)."""
    b = bars(u, d)
    if b is None:
        return float('nan')
    c = b[2]
    if u == 'SPXW':
        return float(c[389] if m >= EOD_M else c[m])
    return float(c[m - 1]) if m >= 1 else float('nan')


# ---- official closes ----------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=1)
def official_spx() -> dict[str, float]:
    import csv
    out = {}
    with open(REPO / 'data' / 'official_closes' / 'cboe_SPX_History_2026-10-22.csv') as f:
        for r in csv.DictReader(f):
            mm, dd, yy = r['DATE'].split('/')
            out[f'{yy}-{mm}-{dd}'] = float(r['SPX'])
    return out


@lru_cache(maxsize=16)
def official_etf(sym: str) -> dict[str, tuple[float, str]]:
    """the ETF's official close: Theta's stock EOD close (by last-trade date), else UW's daily bar"""
    guard_ticker(sym)
    out = {}
    try:
        e = AL.theta_eod((sym,))
        for r in e.iter_rows(named=True):
            if r['close_theta'] is not None and r['close_theta'] > 0:
                out[r['day_lt']] = (float(r['close_theta']), 'theta_stock_eod')
    except Exception:
        pass
    try:
        u = AL.uw_daily((sym,))
        for r in u.iter_rows(named=True):
            if r['day'] not in out and r['close_uw'] is not None:
                out[r['day']] = (float(r['close_uw']), 'uw_daily')
    except Exception:
        pass
    return out


# ---- splits (prereg 2.5: a multi-day trade spanning one is not formed) ------------------------------------------------------------------

SPLITS = {'NVDA': ['2021-07-20', '2024-06-10'], 'TSLA': ['2020-08-31', '2022-08-25'], 'AAPL': ['2020-08-31'],
          'AMZN': ['2022-06-06'], 'GOOGL': ['2022-07-18'], 'AVGO': ['2024-07-15']}


def spans_split(name: str, entry: str, exit_: str) -> str | None:
    for s in SPLITS.get(name, []):
        if entry < s <= exit_:
            return s
    return None


# ---- small io helpers -------------------------------------------------------------------------------------------------------------

def jdump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.part')
    tmp.write_text(json.dumps(obj, indent=1, default=str))
    tmp.replace(path)


def write_parquet(df: pl.DataFrame, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.part')
    df.write_parquet(tmp, compression='zstd')
    tmp.replace(path)
