"""Every expiration ThetaData lists for each of V2's names, and V2's trades where a listed expiration fell on or after the
event session and before the Friday V2 used (A9 probed Fridays only). One ThetaData call a name; needs the one login
(bulk_fetch.py and any other ThetaData job paused, outside 13:00-21:00 UTC).
  python3 -I expiry_calendar_v2names.py"""
import datetime as dt, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import polars as pl
from engine.data.theta_fetch import ThetaFetcher
OUT = os.path.join(HERE, '..', 'results', 'expiry_calendar')
P = os.path.join(OUT, 'v2_names_expirations.parquet')
T = pl.read_parquet(os.path.join(HERE, '..', 'results', 'v1', 'v2_earnings_vol', 'trades.parquet'))
names = sorted(T['symbol'].unique().to_list())
have = pl.read_parquet(P) if os.path.exists(P) else pl.DataFrame(schema={'name': pl.Utf8, 'expiration': pl.Date})
todo = [n for n in names if n not in set(have['name'].to_list())]
f = ThetaFetcher(os.path.join(OUT, 'theta_cache'), nw=1)
frames, errs = [have], []
for i, n in enumerate(todo):
    df, err = f.call('option_list_expirations', symbol=n)
    if err: errs.append((n, err)); continue
    col = [c for c in df.columns if 'exp' in c.lower()][0]
    x = df.select(pl.col(col).cast(pl.Utf8).str.slice(0, 10).alias('e')).with_columns(
        pl.when(pl.col('e').str.contains('-')).then(pl.col('e').str.to_date('%Y-%m-%d', strict=False)).otherwise(pl.col('e').str.to_date('%Y%m%d', strict=False)).alias('expiration'))
    frames.append(x.select('expiration').drop_nulls().with_columns(pl.lit(n).alias('name')).select('name', 'expiration'))
    if (i + 1) % 100 == 0:
        pl.concat(frames).unique().write_parquet(P); print(i + 1, len(todo), flush=True)
E = pl.concat(frames).unique(); E.write_parquet(P)
print('names', E['name'].n_unique(), 'of', len(names), 'errors', len(errs), errs[:10])
by = {}
for n, d in E.iter_rows(): by.setdefault(n, []).append(d)
rows = []
for r in T.iter_rows(named=True):
    if r['E'] is None or r['symbol'] not in by: continue
    earlier = [d for d in by[r['symbol']] if r['event'] <= d < r['E']]
    if earlier: rows.append(dict(symbol=r['symbol'], event=r['event'], split=r['split'], friday_E=r['E'], nearest_listed=min(earlier), a_status=r['a_status'], b_status=r['b_status']))
A = pl.DataFrame(rows) if rows else pl.DataFrame()
print('V2 trades with an earlier listed expiration:', A.height, 'of', T.height)
if A.height: print(A.sort('event')); A.write_csv(os.path.join(OUT, 'v2_affected_all_names.csv'))
