"""Loader for the ThetaData 0DTE research dataset (built by fetch.py; layout and conventions in README.md).

Root (outside the repo): $THETA_DS_ROOT, default <scratchpad>/theta/data.  Parquet (zstd), one file per symbol-session:
    chains/{SPY,QQQ,IWM,SPXW}/{YYYY-MM-DD}.parquet   1-minute NBBO of the same-day expiration, strikes within the band
    ohlc/{SPY,QQQ,IWM,SPXW}/{YYYY-MM-DD}.parquet     1-minute option OHLC/volume/vwap for the same strikes (only minutes with trades)
    underlying/{SPY,QQQ,IWM}/{YYYY-MM-DD}.parquet    1-minute stock OHLC 09:30-16:00, 2017-06-01 .. 2026-10-09
    index/{SPX,VIX}/{YYYY-MM-DD}.parquet             1-minute index price 09:30-16:00, 2017-06-01 .. 2026-10-09
A `.nodata` marker next to a missing chain/ohlc file means the API answered "no data" for that session.

Strike band: strikes K with  ref*(1-BAND) <= K <= ref*(1+BAND), BAND = 0.02, where ref is the 09:31 underlying print:
  - ETFs (SPY, QQQ, IWM): `open` of the 1-minute stock bar stamped 09:31:00 (the first trade at/after 09:31:00);
  - SPXW: the SPX index `price` stamped 09:31:00 (the index value at exactly 09:31:00).
  If that value is null the first non-null value at/after 09:31 is used (ref_status = 'fallback' in the manifest).
Timezone: every `timestamp` is polars Datetime('ms', 'America/New_York').  Option 1-minute quote rows are stamped at the minute
boundary and hold the last NBBO at that timestamp; the 09:30:00 row of a 1-minute series is a placeholder (null prices).
OHLC bars are stamped at the bar's opening minute.  Missing numeric values are null (never NaN).  `right` is 'CALL' / 'PUT'.
`mid` = (bid + ask) / 2, null when either side is null (a 0.0 bid is kept as is)."""
import os, csv, datetime as dt
import polars as pl

SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
ROOT = os.environ.get('THETA_DS_ROOT', SP + '/theta/data')
HERE = os.path.dirname(os.path.abspath(__file__))
BAND = 0.02
TZ = 'America/New_York'
UNDER = {'SPY': ('underlying', 'SPY'), 'QQQ': ('underlying', 'QQQ'), 'IWM': ('underlying', 'IWM'), 'SPXW': ('index', 'SPX')}
FIRST_DAILY = {'SPY': '2022-11-11', 'QQQ': '2022-11-11', 'SPXW': '2022-05-13', 'IWM': '2024-04-19'}
CALENDAR = os.path.join(HERE, 'calendar_2017_2026.csv')   # NYSE full closes and early closes

def path(kind, symbol, date):
    """kind: 'chains' | 'ohlc' | 'underlying' | 'index'; date: 'YYYY-MM-DD' or datetime.date."""
    d = date.isoformat() if hasattr(date, 'isoformat') else str(date)
    return os.path.join(ROOT, kind, symbol, d + '.parquet')

def read(kind, symbol, date, as_pandas=False):
    """One symbol-session frame (polars by default).  Raises FileNotFoundError when the session is absent."""
    df = pl.read_parquet(path(kind, symbol, date))
    return to_pandas(df) if as_pandas else df

def to_pandas(df):
    """polars -> pandas without pyarrow (timestamps become tz-aware datetime64 in America/New_York)."""
    import pandas as pd
    return pd.DataFrame(df.to_dict(as_series=False))

def chain(symbol, date, as_pandas=False): return read('chains', symbol, date, as_pandas)
def ohlc(symbol, date, as_pandas=False): return read('ohlc', symbol, date, as_pandas)
def underlying(symbol, date, as_pandas=False): return read('underlying', symbol, date, as_pandas)
def index(symbol, date, as_pandas=False): return read('index', symbol, date, as_pandas)

def underlying_for(option_symbol, date, as_pandas=False):
    """The underlying/index minute series the band of this option symbol was defined on (SPX for SPXW)."""
    kind, usym = UNDER[option_symbol]
    return read(kind, usym, date, as_pandas)

def ref_price(option_symbol, date):
    """(price, 'HH:MM:SS', status) for the 09:31 reference print, exactly as the builder computed it."""
    kind, usym = UNDER[option_symbol]
    u = pl.read_parquet(path(kind, usym, date))
    col = 'price' if kind == 'index' else 'open'
    u = u.filter(pl.col('timestamp').dt.time() >= dt.time(9, 31)).filter(pl.col(col).is_not_null()).sort('timestamp')
    if u.height == 0: return None, None, 'no_underlying_price'
    t = u['timestamp'][0]
    return float(u[col][0]), t.strftime('%H:%M:%S'), ('ok' if t.time() == dt.time(9, 31) else 'fallback')

def band(ref, band=BAND):
    """Inclusive strike band [lo, hi] for a reference price."""
    return ref * (1 - band), ref * (1 + band)

def sessions(kind, symbol):
    """Sorted session dates that have a parquet file."""
    d = os.path.join(ROOT, kind, symbol)
    return sorted(f[:10] for f in os.listdir(d) if f.endswith('.parquet')) if os.path.isdir(d) else []

def nodata_sessions(kind, symbol):
    d = os.path.join(ROOT, kind, symbol)
    return sorted(f[:10] for f in os.listdir(d) if f.endswith('.nodata')) if os.path.isdir(d) else []

def trading_sessions(start, end):
    """Weekdays minus NYSE full closes from calendar_2017_2026.csv (early closes are sessions)."""
    hol = {r['date'] for r in csv.DictReader(open(CALENDAR)) if r['type'] == 'full_close'}
    a = dt.date.fromisoformat(start) if isinstance(start, str) else start
    b = dt.date.fromisoformat(end) if isinstance(end, str) else end
    out = []; d = a
    while d <= b:
        if d.weekday() < 5 and d.isoformat() not in hol: out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out

def manifest():
    """manifest.csv.gz as a polars frame (one row per file)."""
    return pl.read_csv(os.path.join(HERE, 'manifest.csv.gz'))

def scan(kind, symbol, start=None, end=None):
    """Lazy concatenation of a symbol's sessions in [start, end] (strings) with a `date` column added; collect() when needed."""
    ds = [d for d in sessions(kind, symbol) if (start is None or d >= start) and (end is None or d <= end)]
    return pl.concat([pl.scan_parquet(path(kind, symbol, d)).with_columns(pl.lit(d).alias('date')) for d in ds]) if ds else None

if __name__ == '__main__':
    import sys
    sym, d = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ('SPY', sessions('chains', 'SPY')[0])
    c = chain(sym, d); print(sym, d, 'ref', ref_price(sym, d), 'band', band(ref_price(sym, d)[0]))
    print(c.head(3)); print(c.shape, c.dtypes)
