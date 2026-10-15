"""Run one root through the full management grid (daily aggregates) and the stage-1 set (per-row outcomes), development
and validation sessions only (the hold-out stays untouched)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lc import runner, policies as pol
root = sys.argv[1]
which = sys.argv[2] if len(sys.argv) > 2 else 'both'
log = lambda m: print(time.strftime('%H:%M:%S'), m, flush=True)
if which in ('both', 'grid'): runner.run_root(root, 'grid', pol.grid(), mode='daily', log=log)
if which in ('both', 'stage1'): runner.run_root(root, 'stage1', pol.stage1(), mode='rows', log=log)
