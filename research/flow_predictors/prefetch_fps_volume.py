"""Second pass of flow-per-strike-intraday with filter=Volume (top-8 strikes by day volume) for the 40-session sample."""
import concurrent.futures, time, json
from common import *
S = json.load(open(os.path.join(OUT, 'samples.json')))['fps_sessions']
def fps(j):
    t, d = j; r = data.get(f'stock/{t}/flow-per-strike-intraday', {'date': d, 'filter': 'Volume'}); return j, len((r or {}).get('data') or [])
t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    for i, (j, n) in enumerate(ex.map(fps, [(t, d) for d in S for t in TICKERS])):
        if i % 30 == 0: print('fpsV', i, j, n, round(time.time() - t0), 's', flush=True)
print('fpsV done', data.STATS, round(time.time() - t0), 's', flush=True)
