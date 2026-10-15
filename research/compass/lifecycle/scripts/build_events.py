"""Build every setup event for the Tier I roots over their 0DTE windows; one parquet per root under WORK/events."""
import os, sys, time, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import events, aux, chainmat as cm, paths
st = aux.make_store()
out = f'{paths.WORK}/events'; os.makedirs(out, exist_ok=True)
for root in sys.argv[1].split(','):
    ss = cm.sessions_0dte(root)
    t0 = time.time()
    ev = events.all_events(st, root, ss[0], ss[-1])
    ev = ev.filter(pl.col('session').is_in(ss))
    ev.write_parquet(f'{out}/{root}.parquet')
    print(root, ss[0], ss[-1], len(ss), 'sessions', ev.height, 'events', f'{time.time() - t0:.0f}s', flush=True)
    print(ev.group_by('setup').agg(pl.len()).sort('setup').to_dict(as_series=False), flush=True)
