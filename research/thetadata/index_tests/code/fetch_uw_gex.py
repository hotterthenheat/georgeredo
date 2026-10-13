import os, sys, json, gzip, urllib.request, urllib.parse, concurrent.futures, time, datetime as dt
sys.path.insert(0, '/home/user/georgeredo/backtest')
import data
TOK = os.environ['UW_API_TOKEN']; OUT = os.environ['UW_OUT']
def once(path, params):
    f = os.path.join(data.CACHE, data._key(path, params) + '.json.gz')
    if os.path.exists(f):
        with gzip.open(f, 'rt') as fh: return 'cache', json.load(fh)
    url = data.BASE + path + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOK, 'Accept': 'application/json'})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: d = json.loads(r.read())
            with gzip.open(f, 'wt') as fh: json.dump(d, fh)
            return 200, d
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503, 504): time.sleep(3 * (i + 1)); continue
            return e.code, None
        except Exception as e:
            time.sleep(2)
    return 'fail', None
d0, d1 = dt.date(2023, 11, 1), dt.date(2026, 10, 9)
days = []; d = d0
while d <= d1:
    if d.weekday() < 5: days.append(d.isoformat())
    d += dt.timedelta(days=1)
jobs = [(tk, d) for tk in ('SPY', 'SPX') for d in days]
def f(j):
    tk, d = j; code, r = once(f'stock/{tk}/gex-levels', {'date': d})
    dd = (r or {}).get('data') or {}
    return dict(ticker=tk, date=d, http=code, **{"uw_" + k: dd.get(k) for k in ('date', 'time', 'gamma_flip', 'call_wall', 'put_wall', 'gamma_magnet', 'source')})
out = []
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    for n, r in enumerate(ex.map(f, jobs)):
        out.append(r)
        if n % 100 == 0: print(n, len(jobs), r, flush=True)
import csv
with open(OUT, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print('DONE', len(out), flush=True)
