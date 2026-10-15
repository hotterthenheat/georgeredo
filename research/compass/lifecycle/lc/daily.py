"""Tier D: daily lifecycles from option EOD (the closing NBBO each session), for the Swing, Position, Long-Dated and
LEAPS buckets, single names, and multi-week credit, debit and cash-secured structures (lifecycle protocol §1, §4, §5).

One expiration of one root becomes a DailyChain: contracts x sessions from the first session the panel holds (at most
420 calendar days before expiry) to the last trading day. bid/ask are the vendor's closing NBBO for the session; spot is
the underlying's 16:00 close (the close of the 15:59 minute bar). The same position engine (lc.position) runs on it with
the minute axis read as sessions: TIME_EXIT and CUTOFF count sessions; THESIS=1 reads a daily close.

Stated limits: the option's closing quote for ETF options can be stamped up to 16:15 while spot is 16:00; decisions and
fills are once a session at the close (no intraday stop in this tier); an assigned share position is sold at the next
session's open unless a variant holds it."""
from __future__ import annotations
import datetime as dt, glob, os, sys
from dataclasses import dataclass, field
import numpy as np
import polars as pl
from . import paths
sys.path.insert(0, os.path.dirname(paths.HERE))
from engine import calendar as cal, indicators as ind  # noqa: E402

EOD = f'{paths.FETCH_CACHE}/eod_all'
BYEXP = f'{paths.WORK}/eod_by_exp'
SINGLE_UNDERLYING = f'{paths.FETCH_CACHE}/underlying'

def repartition(root: str, chunk: int = 40, log=print):
    """Weekly files -> one parquet per expiration month (hive dirs, several parts each). Idempotent per root: rebuilt
    when the weekly file count changed."""
    files = sorted(glob.glob(f'{EOD}/{root}/*.parquet'))
    out = f'{BYEXP}/{root}'
    stamp = f'{out}/_files_{len(files)}'
    if os.path.exists(stamp): return out
    if os.path.isdir(out):
        for f in glob.glob(f'{out}/**/*.parquet', recursive=True): os.remove(f)
        for f in glob.glob(f'{out}/_files_*'): os.remove(f)
    os.makedirs(out, exist_ok=True)
    for i in range(0, len(files), chunk):
        df = pl.concat([pl.read_parquet(f) for f in files[i:i + chunk]])
        df = df.with_columns(pl.col('expiration').dt.strftime('%Y-%m').alias('em'))
        for (em,), part in df.group_by(['em']):
            d = f'{out}/{em}'; os.makedirs(d, exist_ok=True)
            part.drop('em').write_parquet(f'{d}/part_{i:05d}.parquet', compression='zstd')
    open(stamp, 'w').close()
    log(f'{root}: repartitioned {len(files)} weekly files')
    return out

_LISTED = {}
def listed_ranges(root: str) -> dict:
    """expiration -> (first, last) session it was quoted, from the per-expiration-month files; cached under WORK by the
    weekly-file stamp. An expiration is only tradeable on a session inside its range: a weekly is listed a few weeks
    ahead, so a picker that looked only at days to expiry would choose expirations that did not exist yet."""
    if root in _LISTED: return _LISTED[root]
    stamp = sorted(glob.glob(f'{BYEXP}/{root}/_files_*'))
    tag = os.path.basename(stamp[-1]) if stamp else 'none'
    cache = f'{paths.WORK}/daily_listed/{root}__{tag}.parquet'
    if os.path.exists(cache):
        df = pl.read_parquet(cache)
    else:
        parts = []
        for d in sorted(glob.glob(f'{BYEXP}/{root}/*-*')):
            x = pl.read_parquet(f'{d}/*.parquet', columns=['expiration', 'date'])
            parts.append(x.group_by('expiration').agg(pl.col('date').min().alias('first'), pl.col('date').max().alias('last')))
        df = pl.concat(parts).group_by('expiration').agg(pl.col('first').min(), pl.col('last').max()).sort('expiration')
        os.makedirs(os.path.dirname(cache), exist_ok=True); df.write_parquet(cache)
    out = {e: (a, b) for e, a, b in zip(df['expiration'].to_list(), df['first'].to_list(), df['last'].to_list())}
    _LISTED[root] = out
    return out

def expirations(root: str) -> list[dt.date]:
    out = []
    for d in sorted(glob.glob(f'{BYEXP}/{root}/*-*')):
        df = pl.read_parquet(f'{d}/*.parquet', columns=['expiration'])
        out += df['expiration'].unique().to_list()
    return sorted(set(out))

_UND = {}
_USET = {}
def underlying_daily(root: str) -> pl.DataFrame:
    """Daily OHLC from the 1-minute bars (open = first bar's open, close = the 15:59 bar's close) for every session cached."""
    if root in _UND: return _UND[root]
    d = f'{paths.UNDERLYING}/{root}' if os.path.isdir(f'{paths.UNDERLYING}/{root}') else f'{SINGLE_UNDERLYING}/{root}'
    files = sorted(glob.glob(f'{d}/*.parquet'))
    cache = f'{paths.WORK}/daily_bars/{root}_{len(files)}_{len(glob.glob(f"{BYEXP}/{root}/_files_*")) and os.path.basename(glob.glob(f"{BYEXP}/{root}/_files_*")[0])}.parquet'
    if os.path.exists(cache):
        _UND[root] = pl.read_parquet(cache); return _UND[root]
    rows = []
    for f in files:
        if not cal.is_session(dt.date.fromisoformat(os.path.basename(f)[:10])): continue
        x = pl.read_parquet(f, columns=['open', 'high', 'low', 'close', 'volume'])
        x = x.with_columns([pl.col(c).cast(pl.Float64, strict=False) for c in ('open', 'high', 'low', 'close', 'volume')])   # some files store prices as text
        x = x.drop_nulls(['close']).filter(pl.col('close').is_not_nan() & pl.col('open').is_not_nan())
        if x.height < 30: continue
        rows.append((dt.date.fromisoformat(os.path.basename(f)[:10]), float(x['open'][0]), float(x['high'].max()), float(x['low'].min()), float(x['close'][-1]), float(x['volume'].sum())))
    df = pl.DataFrame(rows, schema=['session', 'open', 'high', 'low', 'close', 'volume'], orient='row').sort('session').with_columns(pl.lit('minute').alias('src'))
    par = parity_closes(root)
    if par.height:
        par = par.filter(~pl.col('session').is_in(df['session'].implode()) if df.height else pl.lit(True))
        df = pl.concat([df, par], how='diagonal_relaxed').sort('session')
    df = df.with_columns(_split_factor(df).alias('adj'))
    os.makedirs(os.path.dirname(cache), exist_ok=True); df.write_parquet(cache)
    _UND[root] = df
    return df

def parity_closes(root: str, r: float = 0.0025) -> pl.DataFrame:
    """The underlying's close implied by put-call parity on the option chain itself, for sessions the minute bars do not
    cover (index ETFs before 2017): on the nearest expiration at least 5 calendar days out, at the strike where |C - P|
    of the closing mids is smallest, S = K e^{-rt} + C - P. open/high/low are set to the close (close-only history),
    src = 'parity'. r = 0.25 % (fed funds were 0.1-0.7 % over 2012-2016; no rate history is entitled). Measured on SPY
    2017-06..12 against real closes with the period's ~1 % rate: median +0.6 bp, 10th-90th percentile -10.9 to +9.9 bp
    (the option close is stamped up to 16:15, the stock's at 16:00). Cached per root."""
    cache = f'{BYEXP}/{root}/_parity.parquet'
    if os.path.exists(cache): return pl.read_parquet(cache)
    rows = []
    for d in sorted(glob.glob(f'{BYEXP}/{root}/*-*')):
        df = pl.read_parquet(f'{d}/*.parquet', columns=['date', 'expiration', 'strike', 'right', 'bid', 'ask'])
        df = df.filter((pl.col('bid') > 0) & (pl.col('ask') >= pl.col('bid')) & (pl.col('date') < dt.date(2017, 6, 1)))
        if df.height == 0: continue
        df = df.with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
        c = df.filter(pl.col('right') == 'C').select(['date', 'expiration', 'strike', pl.col('mid').alias('c')])
        q = df.filter(pl.col('right') == 'P').select(['date', 'expiration', 'strike', pl.col('mid').alias('p')])
        rows.append(c.join(q, on=['date', 'expiration', 'strike']))
    if not rows: return pl.DataFrame()
    cp = pl.concat(rows).with_columns((pl.col('expiration') - pl.col('date')).dt.total_days().alias('dte')).filter(pl.col('dte') >= 5)
    near = cp.group_by('date').agg(pl.col('dte').min().alias('dmin'))
    cp = cp.join(near, on='date').filter(pl.col('dte') == pl.col('dmin'))
    cp = cp.with_columns((pl.col('c') - pl.col('p')).abs().alias('gap')).sort(['date', 'gap']).group_by('date', maintain_order=True).first()
    cp = cp.with_columns((pl.col('strike') * (-r * pl.col('dte') / 365.0).exp() + pl.col('c') - pl.col('p')).alias('close'))
    out = cp.select([pl.col('date').alias('session'), pl.col('close').alias('open'), pl.col('close').alias('high'), pl.col('close').alias('low'), 'close']).with_columns(
        pl.lit(0.0).alias('volume'), pl.lit('parity').alias('src')).sort('session')
    out.write_parquet(cache)
    return out

def _split_factor(df: pl.DataFrame) -> pl.Series:
    """Cumulative split factor (for indicator history only; strikes and quotes stay unadjusted): a close-to-next-open
    ratio within 4 % of 1/k or k for k in 2,3,4,5,8,10,15,20,25,30 marks a split; prices before it are divided by it."""
    c = df['close'].to_numpy(); o = df['open'].to_numpy()
    f = np.ones(c.size)
    ks = (2, 3, 4, 5, 8, 10, 15, 20, 25, 30)
    for i in range(1, c.size):
        r = o[i] / c[i - 1]
        for k in ks:
            if abs(r * k - 1) < 0.04: f[:i] *= k; break          # forward split: earlier prices / k
            if abs(r / k - 1) < 0.04: f[:i] /= k; break          # reverse split
    return pl.Series(f)

@dataclass
class DailyChain:
    root: str
    expiration: dt.date
    sessions: list
    strike: np.ndarray
    is_call: np.ndarray
    bid: np.ndarray        # [C, T]
    ask: np.ndarray
    volume: np.ndarray
    spot: np.ndarray       # [T] 16:00 close
    next_open: float       # the session after the last trading day
    meta: dict = field(default_factory=dict)

    @property
    def n_min(self): return len(self.sessions)

_MONTHS: dict = {}
def _month(root: str, em: str) -> pl.DataFrame | None:
    """One expiration month of a root, kept for reuse (the last 6 months read)."""
    k = (root, em)
    if k in _MONTHS: return _MONTHS[k]
    d = f'{BYEXP}/{root}/{em}'
    if not os.path.isdir(d): return None
    df = pl.read_parquet(f'{d}/*.parquet')
    _MONTHS[k] = df
    if len(_MONTHS) > 6: _MONTHS.pop(next(iter(_MONTHS)))
    return df

def load(root: str, expiration: dt.date, am_settled: bool = False) -> DailyChain | None:
    df = _month(root, f'{expiration:%Y-%m}')
    if df is None: return None
    df = df.filter(pl.col('expiration') == expiration)
    if df.height == 0: return None
    ltd = cal.last_trading_day(expiration, am_settled)
    und = underlying_daily(root)
    if root not in _USET: _USET[root] = set(und['session'].to_list())
    ss = sorted(set(df['date'].unique().to_list()) & _USET[root])
    ss = [s for s in ss if s <= ltd]
    if len(ss) < 2: return None
    keys = df.select(['strike', 'right']).unique().sort(['right', 'strike']).with_row_index('cid')
    df = df.join(keys, on=['strike', 'right']).filter(pl.col('date').is_in(ss))
    ix = {s: i for i, s in enumerate(ss)}
    C, T = keys.height, len(ss)
    bid = np.full((C, T), np.nan); ask = np.full((C, T), np.nan); vol = np.zeros((C, T))
    ci = df['cid'].to_numpy(); ti = np.array([ix[s] for s in df['date'].to_list()])
    bid[ci, ti] = df['bid'].to_numpy().astype(float); ask[ci, ti] = df['ask'].to_numpy().astype(float); vol[ci, ti] = df['volume'].fill_null(0).to_numpy()
    u = und.filter(pl.col('session').is_between(ss[0], ss[-1])).filter(pl.col('session').is_in(ss)).sort('session')
    spot = u['close'].to_numpy().astype(float)
    later = und.filter(pl.col('session') > ltd)
    nop = float(later['open'][0]) if later.height else np.nan
    return DailyChain(root=root, expiration=expiration, sessions=ss, strike=keys['strike'].to_numpy().astype(float),
                      is_call=keys['right'].to_numpy() == 'C', bid=bid, ask=ask, volume=vol, spot=spot, next_open=nop,
                      meta={'ltd': ltd, 'am_settled': am_settled})

_DS = {}
def daily_series(root: str) -> pl.DataFrame:
    if root not in _DS: _DS[root] = _daily_series(root)
    return _DS[root]

def _daily_series(root: str) -> pl.DataFrame:
    """Daily decision series on split-adjusted closes: EMA 20/50/200, RSI 14, ATR 14, 20-session high/low before the
    day, a 20-session z-score of the close, and 20-session realized vol (annualised)."""
    u = underlying_daily(root)
    c = (u['close'] / u['adj']).to_numpy(); h = (u['high'] / u['adj']).to_numpy(); l = (u['low'] / u['adj']).to_numpy(); o = (u['open'] / u['adj']).to_numpy()
    s = pl.Series(c)
    lr = np.r_[np.nan, np.diff(np.log(c))]
    out = u.with_columns([
        pl.Series('c_adj', c), pl.Series('o_adj', o), pl.Series('h_adj', h), pl.Series('l_adj', l),
        pl.Series('ema20', ind.ema(c, 20)), pl.Series('ema50', ind.ema(c, 50)), pl.Series('ema200', ind.ema(c, 200)),
        pl.Series('rsi14', ind.rsi(c, 14)), pl.Series('atr14', ind.atr(h, l, c, 14)),
        pl.Series('hi20', pl.Series(h).shift(1).rolling_max(20).to_numpy()), pl.Series('lo20', pl.Series(l).shift(1).rolling_min(20).to_numpy()),
        pl.Series('z20', ((s - s.rolling_mean(20)) / s.rolling_std(20)).to_numpy()),
        pl.Series('rv20', (pl.Series(lr).rolling_std(20) * np.sqrt(252)).to_numpy()),
    ])
    return out
