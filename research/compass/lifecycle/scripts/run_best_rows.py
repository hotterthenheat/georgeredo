"""Per-trade rows for the management rule each matrix cell is scored on, where the original run kept only daily sums
(the daily tier's dgrid and the volatility setups' vol_grid). Real trades only (no random controls), development and
validation only, the same events, chains and policy definitions as the original runs, so the trades are the same trades:
scripts/trade_stats.py checks every cell's count, expectancy and win rate against the published cells before using them.

  python3 -I scripts/run_best_rows.py daily SPY,QQQ,IWM,FB
  python3 -I scripts/run_best_rows.py vol SPY,QQQ,IWM,SPXW
"""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import daily_runner as dr, runner, policies as pol, paths

log = lambda m: print(time.strftime('%H:%M:%S'), m, flush=True)
M = f'{paths.RESULTS}/matrix'
what, roots = sys.argv[1], sys.argv[2].split(',')
if what == 'daily':
    names = tuple(sorted(set(pl.read_csv(f'{M}/tier_d_matrix.csv')['best_policy'].to_list())))
    log(f'daily policies {names}')
    for r in roots:
        dr.run_root(r, 'dbest', mode='rows', policy_names=names, with_controls=False, log=log)
elif what == 'vol':
    want = set(pl.read_csv(f'{M}/tier1_vol_matrix.csv')['best_policy'].to_list())
    ps = [p for p in pol.grid() if p[0] in want]
    log(f'vol policies {[p[0] for p in ps]}')
    for r in roots:
        runner.run_root(r, 'vol_best', ps, mode='rows', events_file=f'{paths.WORK}/events_vol/{r}.parquet', with_controls=False, log=log)
