"""S05 data pull: 1-minute bars for the Tier A universe (the union of Tier A in every year available in
data_lake/universe/tiers.parquet, plus the index/ETF group), 2017-06-01 -> 2026-10-09 (or from the symbol's first listed
expiration if later), into $SP/theta/fetch_cache/underlying/{symbol}/{date}.parquet. Month-sized requests, resumable.
The stock EOD job must be paused. Usage: python3 s05_pull_tierA_bars.py [start] [end] [max_symbols]"""
import datetime as dt, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import polars as pl
from engine.data.theta_fetch import ThetaFetcher
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CACHE = os.path.join(SP, 'theta', 'fetch_cache')
start = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else dt.date(2017, 6, 1)
end = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2026, 10, 9)
maxn = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
tiers = pl.read_parquet(os.path.join(ROOT, 'data_lake', 'universe', 'tiers.parquet'))
syms = tiers.filter(pl.col('tier') == 'A').sort(['year', 'rank']).select('symbol').unique(maintain_order=True)['symbol'].to_list()
for s in ['SPY', 'QQQ', 'IWM', 'DIA']:
    if s not in syms: syms.insert(0, s)
# already cached in the research dataset (SPY/QQQ/IWM 2017->) need no pull
have = {d for d in os.listdir(os.path.join(SP, 'theta', 'data', 'underlying'))}
syms = [s for s in syms if s not in have][:maxn]
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
log('symbols', len(syms), syms[:20])
f = ThetaFetcher(CACHE, nw=8, log=log)
jobs = [('stock_minutes', s, start, end) for s in syms]
f.run_jobs(jobs, 'tierA bars')
log('S05 PULL DONE', f.stats)
