"""Q1: the sweep-definition grid. Events a session and the fade's EV with real 0DTE quotes for every definition
(level x X x k x confirm, sides pooled), the nearest-OTM pick and the 0.30-0.45 delta pick, three exits, fees in.
The definition is chosen on 2022-24 (the largest mean net $ a contract with the trailing stop, >= 500 events) and
read on 2025-26 with the stress test. The underlying's own forward return after the sweep is reported beside it.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I grid.py
"""
import os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S
from common_analysis import load_events, summarise, fmt, PRODUCTS

if __name__ == '__main__':
    E = load_events().filter(pl.col('level') != 'DISP')
    print('events', E.height, 'sessions', E['session'].n_unique(), 'products', E['product'].unique().to_list())
    print(E.group_by('product').agg(pl.col('session').min().alias('first'), pl.col('session').max().alias('last'), pl.col('session').n_unique().alias('sessions')).sort('product'))
    keys = ['level', 'X', 'k', 'confirm']
    # the grid, both periods, nearest OTM and delta pick
    rows = []
    for trade in ('fo', 'fd'):
        g = summarise(E, trade=trade, by=keys + ['period']).with_columns(pl.lit(trade).alias('pick'))
        rows.append(g)
    G = pl.concat(rows).sort('pick', 'period', *keys)
    G.write_csv(os.path.join(S.OUT, 'grid_full.csv'))
    # events a session
    nsess = E.group_by('period').agg(pl.col('session').n_unique().alias('ns'))
    G = G.join(nsess, on='period').with_columns((pl.col('events') / pl.col('ns')).alias('per_session'))
    print('\n== nearest-OTM fade, trailing stop, by definition (2022-24)')
    print(fmt(G.filter((pl.col('pick') == 'fo') & (pl.col('period') == '2022-24')).select(keys + ['events', 'per_session', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'hold_usd', 'fwd30', 'fwd30_pos', 'fwdclose'])))
    print('\n== nearest-OTM fade, trailing stop, by definition (2025-26)')
    print(fmt(G.filter((pl.col('pick') == 'fo') & (pl.col('period') == '2025-26')).select(keys + ['events', 'per_session', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'hold_usd', 'fwd30', 'fwd30_pos', 'fwdclose'])))
    # choose on 2022-24
    tr = G.filter((pl.col('pick') == 'fo') & (pl.col('period') == '2022-24') & (pl.col('events') >= 500)).sort('trail_usd', descending=True)
    best = tr.head(10).select(keys + ['events', 'trail_usd', 'trail_pct', 'trail_win'])
    print('\n== top 10 definitions on 2022-24 by trailing-stop net $ a contract (>= 500 events)'); print(fmt(best))
    chosen = {k: best[k][0] for k in keys}
    te = G.filter((pl.col('pick') == 'fo') & (pl.col('period') == '2025-26'))
    print('\n== the same ten read on 2025-26')
    print(fmt(best.select(keys).join(te, on=keys, how='left').select(keys + ['events', 'trail_usd', 'trail_pct', 'trail_win'])))
    # by level type, X = 0, k = 1 and 3, both periods, all exits, both picks -> the compact table for the notes
    print('\n== by level type (sides pooled), X=0, confirm 0, both periods')
    C = G.filter((pl.col('X') == 0) & (pl.col('confirm') == 0) & pl.col('k').is_in(['1', '3', '5m'])).select(
        ['pick', 'period'] + keys + ['events', 'per_session', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'tgt_pct', 'tgt_win', 'hold_usd', 'hold_pct', 'hold_win', 'fwd5', 'fwd15', 'fwd30', 'fwd60', 'fwdclose', 'fwd30_pos'])
    print(fmt(C.sort('pick', 'level', 'k', 'period')))
    C.write_csv(os.path.join(S.OUT, 'grid_by_level.csv'))
    # by X at k=1, confirm 0 and 1, level pooled
    print('\n== by X and confirm, k=1, levels pooled (fo)')
    P = summarise(E.filter(pl.col('k') == '1'), trade='fo', by=['X', 'confirm', 'period'])
    print(fmt(P.select(['X', 'confirm', 'period', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'hold_usd', 'fwd30', 'fwd30_pos'])))
    P.write_csv(os.path.join(S.OUT, 'grid_by_x_confirm.csv'))
    # merged trigger: any level, one entry a (product, session, minute, side); X=0, k=1, confirm 0
    for X, k, confirm in ((0, '1', 0), (chosen['X'], chosen['k'], chosen['confirm'])):
        M = E.filter((pl.col('X') == X) & (pl.col('k') == k) & (pl.col('confirm') == confirm)).unique(['product', 'session', 'entry_m', 'side'])
        print(f'\n== merged trigger (any level, one entry a minute and side), X={X} k={k} confirm={confirm}')
        print(fmt(summarise(M, trade='fo', by=['product', 'period']).select(['product', 'period', 'events', 'sessions', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'hold_usd', 'fwd30', 'fwd30_pos', 'fwdclose'])))
        for per in ('2022-24', '2025-26'):
            for ex in ('trail', 'tgt', 'hold'):
                st = S.stress(M.filter(pl.col('period') == per), f'fo_{ex}_net')
                print(f'   stress {per} {ex}: ' + ', '.join(f'{a}={b:.3g}' if isinstance(b, float) else f'{a}={b}' for a, b in st.items()))
        print(fmt(summarise(M, trade='fo', by=['year']).select(['year', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'hold_usd', 'fwd30'])))
    # the chosen definition: stress by product and year, both picks
    print('\n== CHOSEN on 2022-24:', chosen)
    Cc = E.filter((pl.col('level') == chosen['level']) & (pl.col('X') == chosen['X']) & (pl.col('k') == chosen['k']) & (pl.col('confirm') == chosen['confirm']))
    for trade in ('fo', 'fd'):
        print(f'-- {trade} by product and period'); print(fmt(summarise(Cc, trade=trade, by=['product', 'period']).select(['product', 'period', 'events', 'filled', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'tgt_pct', 'hold_usd', 'hold_pct'])))
        for per in ('2022-24', '2025-26'):
            for ex in ('trail', 'tgt', 'hold'):
                st = S.stress(Cc.filter(pl.col('period') == per), f'{trade}_{ex}_net')
                print(f'   stress {trade} {per} {ex}: ' + ', '.join(f'{a}={b:.3g}' if isinstance(b, float) else f'{a}={b}' for a, b in st.items()))
    print(fmt(summarise(Cc, trade='fo', by=['year']).select(['year', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'hold_usd', 'fwd30', 'fwdclose'])))
    # the underlying's forward return by level, X=0, k=1 (the trigger's information, no option cost)
    print('\n== underlying forward return (bps, fade direction) after a sweep, X=0 k=1 confirm=0, by level and period')
    U = E.filter((pl.col('X') == 0) & (pl.col('k') == '1') & (pl.col('confirm') == 0)).group_by('level', 'period').agg(
        pl.len().alias('events'), *[pl.col(f'fwd_{h}').mean().alias(f'fwd{h}') for h in ('5', '15', '30', '60', 'close')],
        *[pl.col(f'fwd_{h}').median().alias(f'med{h}') for h in ('30', 'close')], (pl.col('fwd_30') > 0).mean().alias('p30_pos'), (pl.col('fwd_30') >= 10).mean().alias('p30_ge10'),
        (pl.col('fwd_30').std() / pl.len().sqrt()).alias('se30')).sort('level', 'period')
    print(fmt(U)); U.write_csv(os.path.join(S.OUT, 'underlying_fwd.csv'))
