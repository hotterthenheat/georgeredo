"""Tier D research for roots whose pull has finished: the full daily policy set as daily sums (with controls), and the
headline policies per row (distributions), development + validation only (sessions before 2024-01-01)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lc import daily_runner as dr
log = lambda m: print(time.strftime('%H:%M:%S'), m, flush=True)
for root in sys.argv[1].split(','):
    dr.run_root(root, 'dgrid', mode='daily', log=log)
    dr.run_root(root, 'drows', mode='rows', policy_names=dr.ROWS_POLICIES, log=log)
