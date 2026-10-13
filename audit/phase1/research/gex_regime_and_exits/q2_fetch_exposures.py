"""Fetch UW 1-minute spot exposures for SPY on a deterministic 60-session sample (evenly spaced over the range). Cached by data.get."""
import concurrent.futures, json
import numpy as np
from common import *
days = [d for d in DAYS if len(data.underlying_bars('SPY', d)[0]) >= 300]
idx = np.unique(np.round(np.linspace(0, len(days) - 1, 60)).astype(int))
sample = [days[i] for i in idx]
json.dump(sample, open(OUT + '/q2_sessions.json', 'w'))
print('sessions', len(sample), sample[0], sample[-1], flush=True)
def fetch(d):
    r = data.get('stock/SPY/spot-exposures', {'date': d})
    return d, len(r.get('data') or []), r.get('error')
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    for d, n, err in ex.map(fetch, sample):
        print(d, n, err or '', flush=True)
print('STATS', data.STATS)
