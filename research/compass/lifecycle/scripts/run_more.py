"""Entry-rule runs (stage-1 policies, real events, per-row outcomes) and the volatility/Fed-day setups (grid in daily
sums with controls, stage-1 per row), for one root; development and validation sessions only."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lc import runner, policies as pol, paths
root = sys.argv[1]; what = sys.argv[2]
log = lambda m: print(time.strftime('%H:%M:%S'), m, flush=True)
if what == 'entry':
    for rule in ('E1L1', 'E1L3', 'E1L3g', 'E2', 'E2g', 'E3', 'E3atr'):
        runner.run_root(root, f'entry_{rule}', pol.stage1(), mode='rows', entry_rule=rule, with_controls=False, log=log)
if what == 'vol':
    ev = f'{paths.WORK}/events_vol/{root}.parquet'
    runner.run_root(root, 'vol_grid', pol.grid(), mode='daily', events_file=ev, log=log)
    runner.run_root(root, 'vol_stage1', pol.stage1(), mode='rows', events_file=ev, log=log)
