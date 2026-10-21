"""Loading and summarising helpers for the analysis scripts."""
import datetime as dt, os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S

PRODUCTS = ('SPY', 'QQQ', 'IWM', 'SPXW')
SPLIT = dt.date(2025, 1, 1)

def load_events(products=PRODUCTS, columns=None):
    frames = []
    for p in products:
        f = os.path.join(S.OUT, f'events_{p}.parquet')
        if not os.path.exists(f): continue
        frames.append(pl.read_parquet(f, columns=columns))
    E = pl.concat(frames, how='diagonal_relaxed')
    # an unfilled pick was written as NaN: make it null so means skip it and is_not_null() reads as 'filled'
    E = E.with_columns([pl.col(c).fill_nan(None) for c, t in E.schema.items() if t == pl.Float64])
    # an entry at 15:58 has no minute left to sell in: the window is 09:35-15:57 for entries, 15:58 for the sale
    E = E.filter(pl.col('entry_m') < S.LAST_SELL)
    return E.with_columns(pl.when(pl.col('session') < SPLIT).then(pl.lit('2022-24')).otherwise(pl.lit('2025-26')).alias('period'),
                          pl.col('session').dt.year().alias('year'))

def summarise(df, trade='fo', exits=('trail', 'tgt', 'hold'), by=()):
    """per group: events, sessions, events a session, fill share, and per exit the mean net $ a contract, mean % a trade,
    win rate, plus the underlying's forward returns in the fade direction"""
    by = list(by)
    aggs = [pl.len().alias('events'), pl.col('session').n_unique().alias('sessions'),
            pl.col(f'{trade}_ask').is_not_null().mean().alias('filled')]
    for ex in exits:
        n = pl.col(f'{trade}_{ex}_net'); r = pl.col(f'{trade}_{ex}_ret')
        aggs += [n.mean().alias(f'{ex}_usd'), r.mean().alias(f'{ex}_pct'), (n > 0).mean().alias(f'{ex}_win'), n.count().alias(f'{ex}_n')]
    for hz in ('5', '15', '30', '60', 'close'):
        aggs += [pl.col(f'fwd_{hz}').mean().alias(f'fwd{hz}'), (pl.col(f'fwd_{hz}') > 0).mean().alias(f'fwd{hz}_pos')]
    out = df.group_by(by).agg(aggs) if by else df.select(aggs)
    return out.sort(by) if by else out

def fmt(df, floats=3):
    pl.Config.set_tbl_cols(60); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_rows(200); pl.Config.set_float_precision(floats)
    return df
