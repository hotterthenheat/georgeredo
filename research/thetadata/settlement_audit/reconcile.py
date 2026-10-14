"""Reconcile SPXW settlement proxies against Cboe's published SPX closing values (PM-settled SPXW settle to the SPX
closing value computed from component closing prices). Inputs: Cboe SPX_History.csv (public, cdn.cboe.com), ThetaData
SPX EOD close (index_tests cache) and the 16:00 SPX minute print (dataset index/SPX). Output: per-session table + summary."""
import csv, glob, gzip, json, os, statistics, datetime as dt
import polars as pl
SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
OUT = os.path.dirname(os.path.abspath(__file__))
START, END = '2022-05-13', '2026-10-09'
cboe = {}
for r in csv.DictReader(open(SP + '/cboe/SPX_History.csv')):
    d = dt.datetime.strptime(r['DATE'], '%m/%d/%Y').date().isoformat()
    if START <= d <= END: cboe[d] = float(r['SPX'])
eod = {}
for f in glob.glob(SP + '/theta/cache/index_tests/index_history_eod__*symbol=SPX.csv.gz'):
    for r in csv.DictReader(gzip.open(f, 'rt')):
        ts = r.get('created') or r.get('timestamp') or r.get('date') or ''
        d = ts[:10]
        if START <= d <= END and r.get('close') not in (None, '', 'nan'): eod[d] = float(r['close'])
rows = []
for d in sorted(cboe):
    p = f'{SP}/theta/data/index/SPX/{d}.parquet'
    m1600 = None
    if os.path.exists(p):
        u = pl.read_parquet(p).filter(pl.col('timestamp').dt.time() == dt.time(16, 0))
        if u.height and u['price'][0] is not None: m1600 = float(u['price'][0])
    c = cboe[d]; e = eod.get(d)
    rows.append(dict(date=d, cboe_close=c, theta_eod_close=e, spx_1600_print=m1600,
                     eod_minus_cboe=(round(e - c, 4) if e is not None else None),
                     print1600_minus_cboe=(round(m1600 - c, 4) if m1600 is not None else None)))
with open(OUT + '/settlement_reconciliation.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); [w.writerow(r) for r in rows]
def summ(key):
    v = [abs(r[key]) for r in rows if r[key] is not None]
    big = sorted(((abs(r[key]), r['date'], r[key]) for r in rows if r[key] is not None), reverse=True)[:8]
    return dict(n=len(v), exact_within_0_01=sum(1 for x in v if x <= 0.01), mean_abs_pts=round(statistics.mean(v), 4),
                median_abs_pts=round(statistics.median(v), 4), max_abs_pts=round(max(v), 4), over_1pt=sum(1 for x in v if x > 1),
                over_5pt=sum(1 for x in v if x > 5), largest=[(d, x) for _, d, x in big])
S = dict(sessions=len(rows), source='https://cdn.cboe.com/api/global/us_indices/daily_prices/SPX_History.csv',
         missing_theta_eod=sum(1 for r in rows if r['theta_eod_close'] is None), missing_1600=sum(1 for r in rows if r['spx_1600_print'] is None),
         theta_eod_vs_cboe=summ('eod_minus_cboe'), print1600_vs_cboe=summ('print1600_minus_cboe'))
json.dump(S, open(OUT + '/summary.json', 'w'), indent=1); print(json.dumps(S, indent=1))
