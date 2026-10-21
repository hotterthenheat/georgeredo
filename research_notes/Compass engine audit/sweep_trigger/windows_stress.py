"""The few cells that read positive in dollars, stress-tested by day: the 09:55-10:35 fade window (all, high side),
the OR sweeps whose level lies within 0.2% of PDH/PDL, the first-hour cells; by product in % of premium too.
Merged trigger (any level, X=0, k=1, confirm=0), nearest-OTM fade, three exits.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I windows_stress.py
"""
import os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S
from common_analysis import load_events, summarise, fmt

def line(df, col, label):
    st = S.stress(df, col); print(f'   {label}: ' + ', '.join(f'{a}={b:.3g}' if isinstance(b, float) else f'{a}={b}' for a, b in st.items()))

if __name__ == '__main__':
    E = load_events().filter((pl.col('level') != 'DISP') & (pl.col('X') == 0) & (pl.col('k') == '1') & (pl.col('confirm') == 0)).unique(['product', 'session', 'entry_m', 'side'])
    cells = {'fade1 all': E.filter(pl.col('window') == 'fade1'), 'fade1 hi': E.filter((pl.col('window') == 'fade1') & (pl.col('side') == 'hi')),
             'fade1 hi ex-SPXW': E.filter((pl.col('window') == 'fade1') & (pl.col('side') == 'hi') & (pl.col('product') != 'SPXW')),
             'chase1 hi': E.filter((pl.col('window') == 'chase1') & (pl.col('side') == 'hi'))}
    for name, df in cells.items():
        print('==', name)
        print(fmt(summarise(df, trade='fo', by=['product', 'period']).select(['product', 'period', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_pct', 'hold_usd', 'hold_pct', 'fwd30', 'fwdclose'])))
        for per in ('2022-24', '2025-26'):
            for ex in ('trail', 'tgt', 'hold'):
                line(df.filter(pl.col('period') == per), f'fo_{ex}_net', f'{per} {ex} $')
            line(df.filter(pl.col('period') == per), 'fo_trail_ret', f'{per} trail %')
        print(fmt(df.group_by('year').agg(pl.len().alias('n'), pl.col('fo_trail_net').mean().alias('trail_usd'), pl.col('fo_trail_ret').mean().alias('trail_pct')).sort('year')))
    # % of premium pooled, by product, the merged trigger: the honest cross-product figure
    print('== merged trigger, % of premium a trade, by product and year')
    print(fmt(E.group_by('product', 'year').agg(pl.len().alias('n'), pl.col('fo_trail_ret').mean().alias('trail_pct'), pl.col('fo_tgt_ret').mean().alias('tgt_pct'), pl.col('fo_hold_ret').mean().alias('hold_pct')).sort('product', 'year')))
    for p in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        for per in ('2022-24', '2025-26'): line(E.filter((pl.col('product') == p) & (pl.col('period') == per)), 'fo_trail_ret', f'{p} {per} trail %')
