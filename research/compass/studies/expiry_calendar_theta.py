"""Every expiration ThetaData lists for each name (option_list_expirations), the independent check on expiry_calendar.py.
Needs the one ThetaData login: run only while bulk_fetch.py is paused, outside 13:00-21:00 UTC.
  python3 -I expiry_calendar_theta.py"""
import datetime as dt, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import polars as pl
from engine.data.theta_fetch import ThetaFetcher
from expiry_calendar import SINGLE, ETF, CONTROL, OUT

f = ThetaFetcher(cache=os.path.join(OUT, 'theta_cache'), nw=1)
frames = []
for t in [CONTROL] + SINGLE + ETF:
    df, err = f.call('option_list_expirations', symbol=t)
    if err: print(t, 'error', err); continue
    col = [c for c in df.columns if 'exp' in c.lower()][0]
    e = df.select(pl.col(col).cast(pl.Utf8).str.slice(0, 10).alias('e'))
    e = e.with_columns(pl.when(pl.col('e').str.contains('-')).then(pl.col('e').str.to_date('%Y-%m-%d', strict=False))
                        .otherwise(pl.col('e').str.to_date('%Y%m%d', strict=False)).alias('expiration')).drop('e')
    frames.append(e.with_columns(pl.lit(t).alias('name')))
    print(t, df.columns, e.height, e['expiration'].min(), e['expiration'].max(), flush=True)
out = pl.concat(frames).drop_nulls().unique().sort('name', 'expiration')
out.write_parquet(os.path.join(OUT, 'theta_expirations.parquet'))
print('wrote', out.height)
