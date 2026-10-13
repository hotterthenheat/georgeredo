"""Re-page dark-pool prints for ticker-days whose first pass returned <1000 RTH prints (a transient HTTP error is not cached and breaks the paging loop)."""
import concurrent.futures, sys, time, csv
import pandas as pd
from common import *
cv = pd.read_csv(os.path.join(OUT, 'darkpool_coverage.csv')); gaps = cv[cv.prints < 1000]
print('gap ticker-days', len(gaps), flush=True); t0 = time.time()
def dp(j):
    t, d = j; rows, pages, trunc = darkpool_rth(t, d); rth, _ = data.underlying_bars(t, d)
    return dict(ticker=t, date=d, prints=len(rows), pages=pages, truncated=trunc, dp_shares=sum(r['size'] for r in rows), bar_volume=sum(b['v'] for b in rth), uw_volume_field_max=max((r.get('volume') or 0) for r in rows) if rows else None,
                first=min((r['executed_at'] for r in rows), default=''), last=max((r['executed_at'] for r in rows), default=''), at_mid=sum(1 for r in rows if f(r['price']) == (f(r['nbbo_bid']) + f(r['nbbo_ask'])) / 2), no_nbbo=sum(1 for r in rows if not r.get('nbbo_bid') or not r.get('nbbo_ask')))
with concurrent.futures.ThreadPoolExecutor(max_workers=int(sys.argv[1]) if len(sys.argv) > 1 else 1) as ex:
    res = list(ex.map(dp, [(r.ticker, r.date) for r in gaps.itertuples()]))
for r in res:
    cv.loc[(cv.ticker == r['ticker']) & (cv.date == r['date']), list(r.keys())] = list(r.values())
    print(r['ticker'], r['date'], 'prints', r['prints'], 'pages', r['pages'], 'first', r['first'], flush=True)
cv.to_csv(os.path.join(OUT, 'darkpool_coverage.csv'), index=False)
print('refetch done', data.STATS, round(time.time() - t0), 's', 'still <1000:', int((cv.prints < 1000).sum()), flush=True)
