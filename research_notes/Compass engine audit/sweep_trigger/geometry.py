"""Q3: module 9's geometry on the same sweep events. For each episode (X=0, k=1 and k=3, confirm 0; one row an
episode) the four entries are compared on the nearest-OTM fade contract with the three exits:
  close   - the ask at the close of the return bar (the baseline);
  confirm - the next bar closes in the fade direction, the ask at its close (the confirm=1 row of the same episode);
  ote     - the 0.62-0.705 retrace of the impulse from the sweep extreme (sweeplib.ote_fill), filled within 30 bars;
  ob      - the last opposite candle before the return bar (sweeplib.order_block), filled within 30 bars.
Fill rate, EV, win rate and time in trade by period; the FVG split (triple confirmation) on the baseline entry.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I geometry.py
"""
import os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S
from common_analysis import load_events, summarise, fmt

EX = ('trail', 'tgt', 'hold')

def entry_table(df, prefix, label, by=('period',)):
    by = list(by)
    aggs = [pl.len().alias('episodes'), pl.col(f'{prefix}_ask').is_not_null().mean().alias('fill_rate')]
    for ex in EX:
        n = pl.col(f'{prefix}_{ex}_net')
        aggs += [n.mean().alias(f'{ex}_usd'), pl.col(f'{prefix}_{ex}_ret').mean().alias(f'{ex}_pct'), (n > 0).mean().alias(f'{ex}_win'),
                 (pl.col(f'{prefix}_{ex}_m') - pl.col(f'{prefix}_entry')).mean().alias(f'{ex}_mins')]
    aggs += [(pl.col(f'{prefix}_entry') - pl.col('r')).mean().alias('wait_mins'), pl.col(f'{prefix}_ask').mean().alias('ask_paid')]
    return df.group_by(by).agg(aggs).with_columns(pl.lit(label).alias('entry')).sort(by)

if __name__ == '__main__':
    E = load_events().filter((pl.col('level') != 'DISP') & (pl.col('X') == 0))
    rows = []
    for k in ('1', '3'):
        b = E.filter((pl.col('k') == k) & (pl.col('confirm') == 0)).unique(['product', 'session', 'level', 'side', 'e'])
        c = E.filter((pl.col('k') == k) & (pl.col('confirm') == 1)).select(['product', 'session', 'level', 'side', 'e', 'entry_m'] + [f'fo_{x}' for x in ('ask', 'spr')] + [f'fo_{ex}_{f}' for ex in EX for f in ('m', 'net', 'ret')])
        c = c.rename({col: col.replace('fo_', 'cf_') for col in c.columns if col.startswith('fo_')}).rename({'entry_m': 'cf_entry'})
        b = b.join(c, on=['product', 'session', 'level', 'side', 'e'], how='left')
        b = b.with_columns(pl.col('entry_m').alias('fo_entry'), pl.col('ote_m').alias('ote_entry'), pl.col('ob_m').alias('ob_entry'))
        print(f'\n==== k={k}: {b.height} episodes, {b["session"].n_unique()} sessions')
        T = pl.concat([entry_table(b, 'fo', 'close'), entry_table(b, 'cf', 'confirm'), entry_table(b, 'ote', 'OTE'), entry_table(b, 'ob', 'order block')])
        T = T.with_columns(pl.lit(k).alias('k')); rows.append(T)
        print(fmt(T.select(['entry', 'period', 'episodes', 'fill_rate', 'wait_mins', 'ask_paid', 'trail_usd', 'trail_pct', 'trail_win', 'trail_mins', 'tgt_usd', 'tgt_pct', 'tgt_win', 'hold_usd', 'hold_pct', 'hold_win']).sort('period', 'entry')))
        # the same episodes only: where the OTE / OB filled, the baseline on those episodes
        for g in ('ote', 'ob', 'cf'):
            sub = b.filter(pl.col(f'{g}_ask').is_not_null())
            print(f'-- episodes where {g} filled: baseline close-entry on the same episodes')
            print(fmt(pl.concat([entry_table(sub, 'fo', 'close'), entry_table(sub, g, g)]).select(['entry', 'period', 'episodes', 'trail_usd', 'trail_pct', 'trail_win', 'trail_mins', 'tgt_usd', 'hold_usd', 'hold_pct']).sort('period', 'entry')))
        for per in ('2022-24', '2025-26'):
            for g in ('fo', 'cf', 'ote', 'ob'):
                st = S.stress(b.filter(pl.col('period') == per), f'{g}_trail_net')
                print(f'   stress {g} trail {per}: ' + ', '.join(f'{a}={b_:.3g}' if isinstance(b_, float) else f'{a}={b_}' for a, b_ in st.items()))
        # FVG and OB presence splits on the baseline entry
        print('-- FVG present (triple confirmation) against not, baseline close entry')
        print(fmt(summarise(b, trade='fo', by=['fvg', 'period']).select(['fvg', 'period', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'tgt_win', 'hold_usd', 'hold_win', 'fwd30', 'fwd30_pos'])))
        print(fmt(summarise(b, trade='fo', by=['fvg', 'ob', 'period']).select(['fvg', 'ob', 'period', 'events', 'trail_usd', 'trail_win', 'hold_usd', 'fwd30'])))
        for per in ('2022-24', '2025-26'):
            for f in (0, 1):
                st = S.stress(b.filter((pl.col('period') == per) & (pl.col('fvg') == f)), 'fo_trail_net')
                print(f'   stress fvg={f} trail {per}: ' + ', '.join(f'{a}={b_:.3g}' if isinstance(b_, float) else f'{a}={b_}' for a, b_ in st.items()))
        summarise(b, trade='fo', by=['product', 'fvg', 'ob', 'period']).write_csv(os.path.join(S.OUT, f'fvg_split_k{k}.csv'))
    pl.concat(rows).write_csv(os.path.join(S.OUT, 'geometry_entries.csv'))
