"""Study S07 (04_protocol.md amendment A2): daily-resolution trigger screen on the stock EOD lake, every optionable root
with prior-year median dollar volume >= $50M, 2024 -> 2026 (2023 provides the point-in-time universe and warm-up).
Usage: python3 s07_daily_screen.py [out_name] [lake_root] [first_year] [last_year]"""
import datetime as dt, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import polars as pl
from engine import daily_screen as ds
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
name = sys.argv[1] if len(sys.argv) > 1 else 's07_daily_screen'
root = sys.argv[2] if len(sys.argv) > 2 else f'{SP}/lake/stock_eod'
y0 = int(sys.argv[3]) if len(sys.argv) > 3 else 2023
y1 = int(sys.argv[4]) if len(sys.argv) > 4 else 2026
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'v1', name)
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
t0 = time.time()
df = ds.load_lake(root, list(range(y0, y1 + 1))); log(f'lake rows {df.height:,} symbols {df["symbol"].n_unique():,} ({time.time() - t0:.0f}s)')
elig = ds.universe(df); log('eligible symbol-years', elig.height, elig.group_by('year').len().sort('year').to_dicts())
f = ds.features(df); log(f'features ({time.time() - t0:.0f}s)')
rows = ds.screen(f, elig, log=log)
elig.write_parquet(os.path.join(OUT, 'universe.parquet')) if os.path.isdir(OUT) else (os.makedirs(OUT, exist_ok=True), elig.write_parquet(os.path.join(OUT, 'universe.parquet')))
md = ds.report(rows, OUT, f'{name}: daily triggers on the optionable universe (prior-year median $ volume ≥ $50M), {y0 + 1} → {y1}')
print(md); log(f'S07 DONE ({time.time() - t0:.0f}s)')
