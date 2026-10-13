"""Prefetch net-prem-ticks (3 tickers) and market-tide for every session in range (cached under BT_CACHE)."""
import concurrent.futures, time, sys
from common import *
jobs = [('npt', t, d) for d in DAYS for t in TICKERS] + [('tide', None, d) for d in DAYS]
def work(j):
    kind, t, d = j
    if kind == 'npt': return j, len(net_prem_ticks(t, d))
    return j, len(market_tide(d))
t0 = time.time(); short = []
with concurrent.futures.ThreadPoolExecutor(max_workers=int(sys.argv[1]) if len(sys.argv) > 1 else 5) as ex:
    for i, (j, n) in enumerate(ex.map(work, jobs)):
        if n < 300 and j[0] == 'npt' or n < 70 and j[0] == 'tide': short.append((j, n))
        if i % 100 == 0: print('progress', i, '/', len(jobs), data.STATS, round(time.time() - t0), 's', flush=True)
print('done', len(jobs), 'short', len(short), short[:40], data.STATS, round(time.time() - t0), 's', flush=True)
