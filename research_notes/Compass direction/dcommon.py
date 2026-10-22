"""
dcommon.py — shared pieces of the Compass direction study (PREREG_DIRECTION.md, commit 38b11bf): paths, the calendar, the
events' dates (R, P, E1, the exit), the bars, the liquidity floor, the split rule, the fees and the return, the forward / implied
move / strike buckets. The calendar, fees, forward and buckets are copied unchanged from research_notes/Compass features/run/
fcommon.py at e5dd8c6 (PREREG_FEATURES §2), so another study's later edits cannot move them.

Reads files only. No vendor call.
"""
from __future__ import annotations

import bisect
import datetime as dt
import glob
import gzip
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402

SP_OLD = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')   # the stored data
THETA = SP_OLD / 'theta'
STORE = Path('/tmp/claude-0/-home-user/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/dir/store')     # this study's fetch
WORK = Path('/tmp/claude-0/-home-user/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/dir/work')
OUT = HERE / 'out'
PREREG = HERE / 'PREREG_DIRECTION.md'
PREREG_COMMIT = '38b11bf'

HOLD_FROM, HOLD_TO = '2019-04-01', '2022-12-31'
EXPL_FROM, EXPL_LAST = '2019-04-01', '2026-10-21'
LIQ_MIN, LIQ_DAYS, LIQ_NEED = 50e6, 60, 50
EXIT_N = 10
PARITY_TOL = 0.05

# the on-disk names (opened) and the spans of their stored option EOD (every expiry, every day)
DISK_SPAN = {'AAPL': ('2015-03-02', '2026-10-21'), 'FB': ('2017-06-01', '2022-06-08')}
for _n in ('AMZN', 'AVGO', 'GOOGL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'INTC', 'MU', 'META'):
    DISK_SPAN[_n] = ('2022-11-01', '2026-10-21')


def ledger() -> dict:
    return json.loads((HERE / 'ledger.json').read_text())


def event_lists() -> dict:
    with gzip.open(HERE / 'events.json.gz', 'rt') as fh:
        return json.load(fh)


# ---- the calendar (PREREG_FEATURES 2.1; fcommon at e5dd8c6) -------------------------------------------------------------------------

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
    pre = [d for d in spy_eod_dates() if FIRST_DAY <= d < '2022-01-01']
    post = [d for d in AL.weekdays('2022-01-01', LAST_DAY) if d not in AL.NYSE_HOLIDAYS]
    return tuple(pre + post)


@lru_cache(maxsize=1)
def sessions() -> tuple[str, ...]:
    return tuple(d for d in trading_days() if d not in HALF_DAYS)


@lru_cache(maxsize=1)
def tday_set() -> frozenset:
    return frozenset(trading_days())


def next_tday(d: str) -> str | None:
    td = trading_days()
    i = bisect.bisect_right(td, d)
    return td[i] if i < len(td) else None


def prev_tday(d: str) -> str | None:
    td = trading_days()
    i = bisect.bisect_left(td, d)
    return td[i - 1] if i > 0 else None


def nth_session_after(d: str, n: int) -> str | None:
    s = sessions()
    i = bisect.bisect_right(s, d) + n - 1
    return s[i] if i < len(s) else None


def sessions_in(a: str, b: str) -> list[str]:
    s = sessions()
    return list(s[bisect.bisect_left(s, a):bisect.bisect_right(s, b)])


def last_trading_day(expiry: str) -> str | None:
    if expiry in tday_set():
        return expiry
    return prev_tday(expiry)


def cal_days(a: str, b: str) -> int:
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def tier_days(e1: str) -> tuple[str, str] | None:
    """the 10th and the 20th of the 20 full sessions before the first session of E1's month"""
    s = sessions()
    i = bisect.bisect_left(s, e1[:7] + '-01')
    win = s[max(0, i - 20):i]
    if len(win) < 20:
        return None
    return win[9], win[19]


# ---- an event's dates (PREREG_DIRECTION §4) ----------------------------------------------------------------------------------------

def event_dates(report_date: str, report_time: str) -> dict:
    """R, P, E1 and the exit; status 'ok' or why the event is not formed. Calendar only."""
    td = tday_set()
    if report_time == 'premarket':
        R = report_date if report_date in td else next_tday(report_date)
    elif report_time == 'postmarket':
        R = next_tday(report_date)
    else:
        return dict(status='no report time')
    if R is None:
        return dict(status='after the calendar')
    P = prev_tday(R)
    E1 = next_tday(R)
    if E1 is None:
        return dict(status='after the calendar', R=R, P=P)
    if E1 in HALF_DAYS:
        return dict(status='entry session is a half day', R=R, P=P, E1=E1)
    X = nth_session_after(E1, EXIT_N)
    return dict(status='ok', R=R, P=P, E1=E1, X=X)


# ---- bars: ThetaData stock EOD (2019 in the old scratch lake, 2020 → in the repository) ---------------------------------------------

BAR_GLOBS = [str(SP_OLD / 'lake' / 'stock_eod' / 'year=2019' / '*.parquet'),
             str(REPO / 'data_lake' / 'thetadata' / 'stock_eod' / 'year=*' / '*.parquet')]


def load_bars(symbols) -> dict[str, pl.DataFrame]:
    """symbol → (day, close, volume) sorted by day; a row counts for the day of its last trade (one row a day)"""
    syms = sorted(set(symbols))
    fs = sorted({f for g in BAR_GLOBS for f in glob.glob(g)})
    parts = [pl.scan_parquet(f).filter(pl.col('symbol').is_in(syms)).select('symbol', 'created', 'last_trade', 'close', 'volume')
             .collect() for f in fs]
    e = pl.concat([p for p in parts if p.height])
    e = e.with_columns(pl.col('last_trade').dt.strftime('%Y-%m-%d').alias('day'),
                       (pl.col('created').dt.strftime('%Y-%m-%d') == pl.col('last_trade').dt.strftime('%Y-%m-%d')).alias('same'))
    e = e.filter(pl.col('close').is_not_null() & (pl.col('close') > 0))
    e = e.sort(['symbol', 'day', 'same'], descending=[False, False, True]).unique(['symbol', 'day'], keep='first', maintain_order=True)
    out = {}
    for (s,), g in e.group_by(['symbol']):
        out[s] = g.select('day', pl.col('close').cast(pl.Float64), pl.col('volume').cast(pl.Float64)).sort('day')
    return out


class Bars:
    def __init__(self, df: pl.DataFrame):
        self.days = df['day'].to_list()
        self.close = df['close'].to_numpy()
        self.vol = df['volume'].to_numpy()
        self.ix = {d: i for i, d in enumerate(self.days)}

    def c(self, d: str) -> float | None:
        i = self.ix.get(d)
        return float(self.close[i]) if i is not None else None

    def liquid(self, P: str) -> tuple[bool, float | None, int]:
        """median close × volume over the 60 trading days ending at P (at least 50 present)"""
        td = trading_days()
        j = bisect.bisect_right(td, P)
        win = td[max(0, j - LIQ_DAYS):j]
        dv = [self.close[self.ix[d]] * self.vol[self.ix[d]] for d in win if d in self.ix]
        if len(dv) < LIQ_NEED:
            return False, None, len(dv)
        m = float(np.median(dv))
        return m >= LIQ_MIN, m, len(dv)

    def split_between(self, a: str, b: str) -> str | None:
        """A10.2: a close-to-close ratio within 10 % of a split ratio of 2:1 or larger on a trading day in (a, b]"""
        ratios = [1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10, 1 / 20, 1 / 50, 2, 3, 4, 5, 10, 20, 50]
        td = trading_days()
        days = td[bisect.bisect_right(td, a):bisect.bisect_right(td, b)]
        prev = self.c(a)
        for d in days:
            x = self.c(d)
            if x is None:
                continue
            if prev:
                q = x / prev
                for r in ratios:
                    if abs(q / r - 1) <= 0.10:
                        return d
            prev = x
        return None


# ---- fees and the return (PREREG_FEATURES 2.6) -----------------------------------------------------------------------------------

FEE = 0.65 + 0.01248 + 0.025          # 0.68748


def fee(px: float) -> float:
    return FEE if px > 0 else 0.0


def ret(ask: float, exit_px: float) -> tuple[float, float]:
    pnl = (exit_px - ask) * 100.0 - fee(ask) - fee(exit_px)
    return pnl / (ask * 100.0), pnl


# ---- the forward, the implied move, x and the buckets (PREREG_FEATURES 2.2, 2.4; fcommon at e5dd8c6) --------------------------------

def forward_im(K, cb, ca, pb, pa):
    cs = (cb > 0) & (ca > 0) & (ca >= cb)
    ps = (pb > 0) & (pa > 0) & (pa >= pb)
    both = cs & ps
    if not both.any():
        return None
    cm = (cb + ca) / 2.0
    pm = (pb + pa) / 2.0
    d = np.where(both, np.abs(cm - pm), np.inf)
    i = int(np.argmin(d))
    F = K[i] + cm[i] - pm[i]
    IM = cm[i] + pm[i]
    if not (IM > 0):
        return None
    return float(K[i]), float(F), float(IM)


BUCKETS = (('ITM', -0.325), ('ATM', 0.0), ('OTM1', 0.325), ('OTM2', 0.75), ('OTM3', 1.25))
BUCKET_NAMES = tuple(b[0] for b in BUCKETS)


def in_bucket(x, name):
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


def select_buckets(K, standing, x) -> dict[str, int]:
    out = {}
    for name, c in BUCKETS:
        ok = standing & in_bucket(x, name)
        if ok.any():
            d = np.where(ok, np.abs(x - c), np.inf)
            dmin = d.min()
            cand = np.where(np.abs(d - dmin) <= 1e-12)[0]
            out[name] = int(cand[np.argmin(K[cand])])
    return out


def choose_expiry(e1: str, expirations) -> str | None:
    """the listed expiration whose last trading day is 31-60 calendar days after E1, nearest 45 (ties: the earlier)"""
    c = []
    for e in set(expirations):
        le = last_trading_day(e)
        if le is None:
            continue
        dte = cal_days(e1, le)
        if 31 <= dte <= 60:
            c.append((abs(dte - 45), le, e))
    if not c:
        return None
    c.sort()
    return c[0][2]


def grid(x: pl.DataFrame):
    """one expiry's rows → K ascending and call/put bid, ask arrays (NaN = no row)"""
    K = np.unique(x['strike'].to_numpy().astype(float))
    cb, ca, pb, pa = (np.full(K.size, np.nan) for _ in range(4))
    ki = np.searchsorted(K, x['strike'].to_numpy().astype(float))
    isc = x['right'].to_numpy() == 'C'
    bid = x['bid'].to_numpy().astype(float)
    ask = x['ask'].to_numpy().astype(float)
    cb[ki[isc]], ca[ki[isc]] = bid[isc], ask[isc]
    pb[ki[~isc]], pa[ki[~isc]] = bid[~isc], ask[~isc]
    return K, cb, ca, pb, pa


# ---- the stored option EOD: this study's fetch, or the old store's weekly files for the on-disk names --------------------------------

COLS = ['date', 'expiration', 'strike', 'right', 'bid', 'ask', 'volume']


def norm(x: pl.DataFrame) -> pl.DataFrame:
    x = x.select(COLS).with_columns(pl.col('date').cast(pl.String), pl.col('expiration').cast(pl.String),
                                    pl.col('strike').cast(pl.Float64).round(4), pl.col('bid').cast(pl.Float64).round(4),
                                    pl.col('ask').cast(pl.Float64).round(4), pl.col('volume').cast(pl.Int64).fill_null(0),
                                    pl.col('right').cast(pl.String))
    return x.unique(['date', 'expiration', 'strike', 'right'], keep='first', maintain_order=True)


def store_path(sym: str, day: str, what: str) -> Path:
    """what: 'ALL' (every expiry) or an expiration date"""
    return STORE / sym / f'{day}__{what}.parquet'


@lru_cache(maxsize=64)
def _disk_week_index(root: str) -> tuple:
    out = []
    for f in sorted((THETA / 'fetch_cache' / 'eod_all' / root).glob('*.parquet')):
        a, b = f.stem.split('__')
        out.append((a, b, str(f)))
    return tuple(out)


@lru_cache(maxsize=256)
def _disk_week(path: str) -> pl.DataFrame:
    return norm(pl.read_parquet(path, columns=COLS))


def disk_root(name: str, day: str) -> str:
    return 'FB' if (name in ('META', 'FB') and day <= '2022-06-08') else name


def chain(name: str, day: str, expiry: str | None = None, disk: bool = False) -> pl.DataFrame | None:
    """the option EOD rows of a name on a day (every expiry, or one); None when not stored"""
    if disk:
        root = disk_root(name, day)
        for a, b, f in _disk_week_index(root):
            if a <= day <= b:
                x = _disk_week(f).filter(pl.col('date') == day)
                if expiry is not None:
                    x = x.filter(pl.col('expiration') == expiry)
                return x if x.height else None
        return None
    p = store_path(name, day, 'ALL')
    if p.exists():
        x = norm(pl.read_parquet(p))
        return x.filter(pl.col('expiration') == expiry) if expiry is not None else x
    if expiry is not None:
        q = store_path(name, day, expiry)
        if q.exists():
            return norm(pl.read_parquet(q))
    return None


def tier_of(volume: float | None, spread: float | None) -> str:
    if volume is None or spread is None or not math.isfinite(spread):
        return 'U'
    if volume >= 900_000 and spread <= 0.05:
        return '1'
    if volume < 400_000 or spread > 0.10:
        return '3'
    return '2'


def tier_measure(rows: list[pl.DataFrame]) -> tuple[float | None, float | None]:
    """PREREG_FEATURES 2.7 on the sampled sessions: volume = the median day total; spread = the median (ask − bid)/mid over the
    standing 1–60 DTE contracts with |x| ≤ 0.5 (x by its own expiry's F and IM), pooled over the days"""
    vols, sps = [], []
    for x in rows:
        day = x['date'][0]
        vols.append(float(x['volume'].sum()))
        for (e,), xe in x.group_by(['expiration']):
            le = last_trading_day(e)
            if le is None:
                continue
            dte = cal_days(day, le)
            if dte < 1 or dte > 60:
                continue
            K, cb, ca, pb, pa = grid(xe)
            fim = forward_im(K, cb, ca, pb, pa)
            if fim is None:
                continue
            _, F, IM = fim
            for b_, a_, xx in ((cb, ca, (K - F) / IM), (pb, pa, (F - K) / IM)):
                st = (b_ > 0) & (a_ > 0) & (a_ >= b_)
                ok = st & (np.abs(xx) <= 0.5 + 1e-12)
                sps += list(((a_ - b_) / ((a_ + b_) / 2))[ok])
    if not vols:
        return None, None
    return float(np.median(vols)), (float(np.median(sps)) if sps else float('nan'))


def jdump(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.part')
    tmp.write_text(json.dumps(obj, indent=1, default=str))
    tmp.replace(path)
