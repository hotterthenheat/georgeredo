"""Step 1 of the NBBO study: fetch 1-second NBBO windows around every reported entry/exit second (2 workers, cached). Run:
  set -a; . "$SP/secrets/research.env"; set +a; SP="$SP" python3 -I nbbo_fetch.py
Progress -> $SP/theta/georgefi_nbbo_fetch.log ; summary -> $SP/theta/georgefi_nbbo_fetch_summary.json"""
import sys, os, json, time, collections, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbbo_common as N

LOG = os.path.join(N.SP, 'theta', 'georgefi_nbbo_fetch.log')
def log(s):
    with open(LOG, 'a') as fh: fh.write(time.strftime('%H:%M:%S ') + N.red(s) + '\n')

rows = N.load_rows()
merged = N.build_requests(rows)
tasks = [(ck, s, e) for ck, ws in merged.items() for s, e in ws]
def _done(ck, s, e):
    p = N.cache_paths(N.req_id(ck, s, e)[1])[1]
    if not os.path.exists(p): return False
    st = json.load(open(p)); return bool(st.get('ok') or st.get('nodata'))
n_cached = sum(1 for ck, s, e in tasks if _done(ck, s, e))
log(f'rows={len(rows)} contract-days={len(merged)} requests={len(tasks)} already cached={n_cached}')
N.get_client(); log('auth OK')
T0 = time.time(); done = 0; stats = collections.Counter(); errs = []
def work(t):
    ck, s, e = t
    return t, N.fetch_one(None, ck, s, e)
with cf.ThreadPoolExecutor(max_workers=2) as ex:
    for t, st in ex.map(work, tasks):
        done += 1
        if st.get('ok'): stats['ok'] += 1
        elif st.get('nodata'): stats['nodata'] += 1
        else: stats['error'] += 1; errs.append(dict(key=st['key'], error=st.get('error')))
        if done % 50 == 0 or done == len(tasks):
            log(f'{done}/{len(tasks)} ok={stats["ok"]} nodata={stats["nodata"]} error={stats["error"]} elapsed={time.time() - T0:.0f}s')
summary = dict(rows=len(rows), contract_days=len(merged), requests=len(tasks), cached_before=n_cached, ok=stats['ok'], nodata=stats['nodata'], error=stats['error'], seconds=round(time.time() - T0), errors=errs[:50])
json.dump(summary, open(os.path.join(N.SP, 'theta', 'georgefi_nbbo_fetch_summary.json'), 'w'), indent=1)
log('DONE ' + json.dumps({k: v for k, v in summary.items() if k != 'errors'}))
