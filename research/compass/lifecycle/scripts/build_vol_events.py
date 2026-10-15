"""Volatility and Fed-day events (lc.vol) per root; writes WORK/events_vol/<root>.parquet and the session table."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import vol, paths
out = f'{paths.WORK}/events_vol'; os.makedirs(out, exist_ok=True)
fomc = vol.load_fomc()
for root in sys.argv[1].split(','):
    t0 = time.time()
    ev, tab = vol.events(root, fomc)
    ev.write_parquet(f'{out}/{root}.parquet'); tab.write_parquet(f'{out}/{root}_sessions.parquet')
    print(root, ev.height, ev.group_by('setup').agg(pl.len()).sort('setup').to_dict(as_series=False), f'{time.time() - t0:.0f}s', flush=True)
    print('  ratio median', round(float(tab['ratio'].median()), 3), 'iv10 median', round(float(tab['iv10'].median()), 3), flush=True)
