"""Prefetch dark-pool prints (paged, RTH) for a 90-session random sample x 3 tickers, then flow-per-strike-intraday for the first 40 of those sessions."""
import concurrent.futures, time, random, json, csv
from common import *
rng = random.Random(7)
SAMPLE90 = sorted(rng.sample(DAYS, 90)); SAMPLE40 = sorted(rng.sample(SAMPLE90, 40))
json.dump({'dp_sessions': SAMPLE90, 'fps_sessions': SAMPLE40}, open(os.path.join(OUT, 'samples.json'), 'w'), indent=1)
t0 = time.time(); rows_out = []
def dp(j):
    t, d = j; rows, pages, trunc = darkpool_rth(t, d)
    rth, _ = data.underlying_bars(t, d); vol = sum(b['v'] for b in rth)
    lastvol = max((r.get('volume') or 0) for r in rows) if rows else None
    return dict(ticker=t, date=d, prints=len(rows), pages=pages, truncated=trunc, dp_shares=sum(r['size'] for r in rows), bar_volume=vol, uw_volume_field_max=lastvol,
                first=min((r['executed_at'] for r in rows), default=''), last=max((r['executed_at'] for r in rows), default=''), at_mid=sum(1 for r in rows if f(r['price']) == (f(r['nbbo_bid']) + f(r['nbbo_ask'])) / 2), no_nbbo=sum(1 for r in rows if not r.get('nbbo_bid') or not r.get('nbbo_ask')))
jobs = [(t, d) for d in SAMPLE90 for t in TICKERS]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    for i, r in enumerate(ex.map(dp, jobs)):
        rows_out.append(r)
        if i % 20 == 0: print('dp', i, '/', len(jobs), r, data.STATS, round(time.time() - t0), 's', flush=True)
with open(os.path.join(OUT, 'darkpool_coverage.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys())); w.writeheader(); w.writerows(rows_out)
print('darkpool done', round(time.time() - t0), 's', flush=True)
def fps(j):
    t, d = j; r = data.get(f'stock/{t}/flow-per-strike-intraday', {'date': d}); return j, len((r or {}).get('data') or [])
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    for i, (j, n) in enumerate(ex.map(fps, [(t, d) for d in SAMPLE40 for t in TICKERS])):
        if i % 20 == 0: print('fps', i, j, n, round(time.time() - t0), 's', flush=True)
print('fps done', data.STATS, round(time.time() - t0), 's', flush=True)
