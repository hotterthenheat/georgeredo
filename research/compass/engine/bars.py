"""1-minute bars: loading from the Parquet cache, session/minute indexing, resampling to higher timeframes with
closed-bar semantics, and alignment of higher-timeframe values onto 1-minute decisions without look-ahead.

Conventions: `timestamp` is the bar's OPENING minute in America/New_York; a 1-minute bar stamped t closes at t+1 min. A
higher-timeframe bar of M minutes opened at t closes at t+M min (or at the session close for a partial last bar) and is
usable for a decision at the close of a 1-minute bar only when its close time <= that 1-minute bar's close time.
"""
from __future__ import annotations
import datetime as dt
import glob, os
import numpy as np
import polars as pl
from . import calendar as cal

NY = 'America/New_York'

def session_bounds(day: dt.date) -> tuple[dt.datetime, dt.datetime]:
    open_ = dt.datetime.combine(day, dt.time(9, 30))
    close = dt.datetime.combine(day, cal.close_time(day))
    return open_, close

def load_minutes(symbol: str, root: str, start: dt.date | None = None, end: dt.date | None = None, regular_only: bool = True) -> pl.DataFrame:
    """Concatenate `{root}/{symbol}/{date}.parquet` files (schema: timestamp, open, high, low, close, volume[, count, vwap]).
    Adds `session` (date), `minute` (0 at 09:30), `close_ts` (bar close time). Bars outside 09:30-close are dropped when
    regular_only."""
    files = sorted(glob.glob(os.path.join(root, symbol, '*.parquet')))
    frames = []
    for f in files:
        d = dt.date.fromisoformat(os.path.basename(f)[:10])
        if start and d < start: continue
        if end and d > end: continue
        if not cal.is_session(d): continue  # a file on a holiday is a vendor artefact, never a session
        df = pl.read_parquet(f, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        # one schema whatever a file holds (a session with no bars may have been written with null/string columns)
        df = df.with_columns([pl.col(c).cast(pl.Float64, strict=False) for c in ('open', 'high', 'low', 'close', 'volume')])
        df = df.filter(pl.col('open').is_not_null() & pl.col('close').is_not_null())  # the vendor's 16:00 placeholder row has nulls
        if df.height == 0: continue
        frames.append(df.with_columns(pl.lit(d).alias('session')))
    if not frames:
        return pl.DataFrame(schema={'timestamp': pl.Datetime('ms', NY), 'open': pl.Float64, 'high': pl.Float64, 'low': pl.Float64, 'close': pl.Float64, 'volume': pl.Float64, 'session': pl.Date})
    df = pl.concat(frames, how='vertical_relaxed').sort('timestamp')
    df = df.with_columns(pl.col('timestamp').dt.replace_time_zone(None).alias('ts_naive'))
    df = df.with_columns(
        ((pl.col('ts_naive') - pl.col('session').cast(pl.Datetime('ms'))).dt.total_minutes() - 570).cast(pl.Int32).alias('minute'),
    )
    if regular_only:
        last = {d: (cal.close_time(d).hour * 60 + cal.close_time(d).minute - 570) for d in df['session'].unique().to_list()}
        df = df.with_columns(pl.col('session').replace_strict(last, return_dtype=pl.Int32).alias('_last'))
        df = df.filter((pl.col('minute') >= 0) & (pl.col('minute') < pl.col('_last'))).drop('_last')
    df = df.with_columns((pl.col('ts_naive') + pl.duration(minutes=1)).alias('close_ts')).drop('ts_naive')
    return df.with_columns(pl.col('volume').cast(pl.Float64))

def resample(df1: pl.DataFrame, minutes: int) -> pl.DataFrame:
    """Higher-timeframe bars within each session: bucket = minute // minutes; open/high/low/close/volume; `close_ts` =
    min(open + minutes, session close)."""
    if minutes == 1: return df1
    g = df1.with_columns((pl.col('minute') // minutes).alias('_b'))
    out = g.group_by(['session', '_b'], maintain_order=True).agg([
        pl.col('timestamp').first(), pl.col('open').first(), pl.col('high').max(), pl.col('low').min(), pl.col('close').last(),
        pl.col('volume').sum(), pl.col('minute').first().alias('minute'), pl.col('close_ts').last().alias('close_ts'),
    ]).drop('_b')
    return out.sort('timestamp')

def daily_from_minutes(df1: pl.DataFrame) -> pl.DataFrame:
    out = df1.group_by('session', maintain_order=True).agg([
        pl.col('timestamp').first(), pl.col('open').first(), pl.col('high').max(), pl.col('low').min(), pl.col('close').last(),
        pl.col('volume').sum(), pl.col('close_ts').last().alias('close_ts'),
    ])
    return out.with_columns(pl.lit(0, dtype=pl.Int32).alias('minute')).sort('session')

def align_closed(df1: pl.DataFrame, df_tf: pl.DataFrame, cols: list[str], suffix: str) -> pl.DataFrame:
    """For each 1-minute bar, attach the latest higher-timeframe row whose close_ts <= the 1-minute bar's close_ts
    (backward as-of join on close_ts). Columns are renamed `{col}{suffix}`."""
    right = df_tf.select(['close_ts'] + cols).rename({c: f'{c}{suffix}' for c in cols}).sort('close_ts')
    return df1.sort('close_ts').join_asof(right, on='close_ts', strategy='backward')

def with_session_arrays(df: pl.DataFrame) -> dict[str, np.ndarray]:
    """numpy views the indicator functions take."""
    return {
        'open': df['open'].to_numpy(), 'high': df['high'].to_numpy(), 'low': df['low'].to_numpy(), 'close': df['close'].to_numpy(),
        'volume': df['volume'].to_numpy(), 'session': df['session'].cast(pl.Int32).to_numpy(), 'minute': df['minute'].to_numpy(),
    }
