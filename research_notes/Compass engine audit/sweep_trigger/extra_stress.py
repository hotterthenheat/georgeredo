"""Stress tests for the remaining cells that read positive somewhere: the four grid definitions whose 2022-24 dollar
mean stayed positive on 2025-26, the positive-gamma 09:55-10:35 cell, and the delta pick on the merged trigger.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I extra_stress.py
"""
import os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S
from common_analysis import load_events, summarise, fmt

def line(df, col, label):
    st = S.stress(df, col); print(f'   {label}: ' + ', '.join(f'{a}={b:.3g}' if isinstance(b, float) else f'{a}={b}' for a, b in st.items()))

if __name__ == '__main__':
    E = load_events().filter(pl.col('level') != 'DISP')
    for lv, X, k, c in (('OR', 2, '5', 1), ('OR', 5, '5', 1), ('OR', 5, '5', 0), ('PD', 5, '5', 0)):
        d = E.filter((pl.col('level') == lv) & (pl.col('X') == X) & (pl.col('k') == k) & (pl.col('confirm') == c))
        print(f'== {lv} X={X} k={k} confirm={c}')
        print(fmt(summarise(d, trade='fo', by=['product', 'period']).select(['product', 'period', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_pct', 'hold_pct', 'fwd30'])))
        for per in ('2022-24', '2025-26'):
            line(d.filter(pl.col('period') == per), 'fo_trail_net', f'{per} trail $'); line(d.filter(pl.col('period') == per), 'fo_trail_ret', f'{per} trail %')
        print(fmt(d.group_by('year').agg(pl.len().alias('n'), pl.col('fo_trail_net').mean().alias('trail_usd'), pl.col('fo_trail_ret').mean().alias('trail_pct')).sort('year')))
    M = E.filter((pl.col('X') == 0) & (pl.col('k') == '1') & (pl.col('confirm') == 0)).unique(['product', 'session', 'entry_m', 'side'])
    g = pl.concat([pl.read_parquet(f'/home/user/georgeredo/data_lake/unusualwhales/greek-exposure.part0{i}.parquet') for i in (1, 2)])
    g = g.filter(pl.col('ticker').is_in(['SPY', 'QQQ', 'IWM', 'SPX'])).with_columns(pl.col('date').str.to_date().alias('session'),
        (pl.col('call_gamma').cast(pl.Float64) + pl.col('put_gamma').cast(pl.Float64)).alias('net_gamma'), pl.when(pl.col('ticker') == 'SPX').then(pl.lit('SPXW')).otherwise(pl.col('ticker')).alias('product'))
    g = g.with_columns(pl.when(pl.col('net_gamma') > 0).then(pl.lit('positive')).otherwise(pl.lit('negative')).alias('gamma_sign')).select('product', 'session', 'gamma_sign')
    pg = M.join(g, on=['product', 'session']).filter((pl.col('gamma_sign') == 'positive') & (pl.col('window') == 'fade1'))
    print('== positive gamma, fade1 window (UW coverage only)')
    print(fmt(summarise(pg, trade='fo', by=['product']).select(['product', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'hold_pct', 'fwd30'])))
    line(pg, 'fo_trail_net', 'trail $'); line(pg, 'fo_trail_ret', 'trail %')
    print('== merged trigger, delta pick (fd), stress by period')
    for per in ('2022-24', '2025-26'):
        line(M.filter(pl.col('period') == per), 'fd_trail_net', f'{per} fd trail $'); line(M.filter(pl.col('period') == per), 'fd_trail_ret', f'{per} fd trail %')
        line(M.filter(pl.col('period') == per), 'fd_tgt_ret', f'{per} fd tgt %'); line(M.filter(pl.col('period') == per), 'fd_hold_ret', f'{per} fd hold %')
    print(fmt(summarise(M, trade='fd', by=['product', 'period']).select(['product', 'period', 'events', 'filled', 'trail_pct', 'tgt_pct', 'hold_pct', 'trail_win'])))
    # events a session for the merged trigger
    print(fmt(M.group_by('product', 'period').agg(pl.len().alias('events'), pl.col('session').n_unique().alias('sessions')).with_columns((pl.col('events') / pl.col('sessions')).alias('per_session')).sort('product', 'period')))
