"""Q5: the contract picker's spread/mid <= 5% rule. From out/spread_<P>.parquet (every session, every minute 09:35-15:58,
the nearest-OTM call and put): the share passing by half-hour of the day, product and year; and on the sweep events,
the share of the fade picks (nearest OTM and 0.30-0.45 delta) that pass, and their EV passing against failing.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I spread.py
"""
import os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S
from common_analysis import load_events, summarise, fmt, PRODUCTS

if __name__ == '__main__':
    P = pl.concat([pl.read_parquet(os.path.join(S.OUT, f'spread_{p}.parquet')) for p in PRODUCTS if os.path.exists(os.path.join(S.OUT, f'spread_{p}.parquet'))])
    P = P.with_columns(((pl.col('m') + 570) // 30 * 30).alias('t30'), pl.col('session').dt.year().alias('year'), (pl.col('spr') <= 0.05).alias('pass'))
    print('rows', P.height)
    A = P.group_by('product', 't30').agg(pl.len().alias('n'), pl.col('pass').mean().alias('pass_share'), pl.col('spr').median().alias('spr_median'), pl.col('mid').median().alias('mid_median')).sort('product', 't30')
    A = A.with_columns((pl.col('t30') // 60).cast(pl.Utf8) + ':' + (pl.col('t30') % 60).cast(pl.Utf8).str.zfill(2))
    print('== share of nearest-OTM candidates with spread/mid <= 5%, by product and half hour (all sessions)'); print(fmt(A.pivot(on='product', index='t30', values='pass_share').sort('t30')))
    print('== median spread/mid'); print(fmt(A.pivot(on='product', index='t30', values='spr_median').sort('t30')))
    A.write_csv(os.path.join(S.OUT, 'spread_by_halfhour.csv'))
    Y = P.group_by('product', 'year').agg(pl.col('pass').mean().alias('pass_share'), pl.col('spr').median().alias('spr_median')).sort('product', 'year')
    print('== by product and year'); print(fmt(Y.pivot(on='product', index='year', values='pass_share').sort('year'))); Y.write_csv(os.path.join(S.OUT, 'spread_by_year.csv'))
    # on the sweep picks
    E = load_events().filter((pl.col('level') != 'DISP') & (pl.col('X') == 0) & (pl.col('k') == '1') & (pl.col('confirm') == 0)).unique(['product', 'session', 'entry_m', 'side'])
    for pick in ('fo', 'fd'):
        e = E.filter(pl.col(f'{pick}_ask').is_not_null()).with_columns((pl.col(f'{pick}_spr') <= 0.05).alias('pass'))
        print(f'== sweep picks ({pick}): share passing by product and period, and EV passing vs failing (trailing stop)')
        print(fmt(e.group_by('product', 'period', 'pass').agg(pl.len().alias('n'), pl.col(f'{pick}_trail_net').mean().alias('trail_usd'), pl.col(f'{pick}_trail_ret').mean().alias('trail_pct'), pl.col(f'{pick}_hold_net').mean().alias('hold_usd'), pl.col(f'{pick}_ask').mean().alias('ask')).sort('product', 'period', 'pass')))
        print(fmt(e.group_by('window', 'pass').agg(pl.len().alias('n'), pl.col(f'{pick}_trail_net').mean().alias('trail_usd'), pl.col(f'{pick}_spr').median().alias('spr_med')).sort('window', 'pass')))
    # the delta pick's availability
    print('== delta pick (0.30-0.45) available at the sweep minute, by product and window')
    print(fmt(E.group_by('product', 'window').agg(pl.len().alias('n'), pl.col('fd_ask').is_not_null().mean().alias('delta_pick_available'), pl.col('fo_delta').abs().median().alias('otm_delta_median')).sort('product', 'window')))
