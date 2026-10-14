"""All-ticker history from Unusual Whales: the per-ticker endpoints that return a whole history in one request.
All UW tickers: info, ohlc/1d (limit 2500), earnings. Optionable UW tickers: greek-exposure, iv-rank, volatility/realized,
volatility/variance-risk-premium, max-pain. Raw JSON (gzip) per ticker under $LAKE/uw/<endpoint>/; resumable; <= 3 concurrent
(UW concurrency cap). Token from UW_API_TOKEN only; never printed. Usage: python3 -I uw_bulk_fetch.py"""
import os, sys, gzip, json, time, urllib.request, urllib.parse, urllib.error, threading, datetime as dt
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
LAKE = os.environ.get('LAKE', SP + '/lake'); BASE = 'https://api.unusualwhales.com/api/'
TOK = os.environ['UW_API_TOKEN']
ALL = [l.split('\t')[0] for l in open(HERE + '/unusualwhales_tickers.txt').read().splitlines()[1:] if l.strip()]
OPT = [l.strip() for l in open(SP + '/lake_uw_optionable.txt') if l.strip()]
JOBS = [('info', ALL, {}), ('ohlc/1d', ALL, {'limit': 2500}), ('earnings', ALL, {}),
        ('greek-exposure', OPT, {}), ('iv-rank', OPT, {}), ('volatility/realized', OPT, {}),
        ('volatility/variance-risk-premium', OPT, {}), ('max-pain', OPT, {}),
        ('iv-rank', OPT, {'timespan': '1y'}, '__1y')]   # added 2026-10-14: default iv-rank returns ~5 days; timespan=1y returns the year
SEL = os.environ.get('UW_ONLY')   # optional: run only the job whose folder name equals this
lk = threading.Lock(); cnt = {}
def log(*a): print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
def fetch(ep, t, params, tag=''):
    d = f"{LAKE}/uw/{ep.replace('/', '__')}{tag}"; p = f'{d}/{t.replace("/", "_")}.json.gz'
    if os.path.exists(p): return 'skip'
    url = BASE + 'stock/' + urllib.parse.quote(t, safe='') + '/' + ep + ('?' + urllib.parse.urlencode(params) if params else '')
    for a in range(6):
        try:
            req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOK, 'Accept': 'application/json', 'User-Agent': 'research'})
            body = urllib.request.urlopen(req, timeout=60).read(); st = 'ok'; break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504): time.sleep(1.5 * (a + 1)); continue
            body = json.dumps({'error': e.code}).encode(); st = f'http{e.code}'; break
        except Exception as e:
            time.sleep(2 * (a + 1)); body = json.dumps({'error': type(e).__name__}).encode(); st = 'neterr'
    os.makedirs(d, exist_ok=True); tmp = p + '.tmp'
    with gzip.open(tmp, 'wb') as f: f.write(body)
    os.replace(tmp, p); return st
for job in JOBS:
    ep, tick, params = job[:3]; tag = job[3] if len(job) > 3 else ''
    if SEL and SEL != ep.replace('/', '__') + tag: continue
    t0 = time.time(); c = {}
    with ThreadPoolExecutor(3) as ex:
        for st in ex.map(lambda t: fetch(ep, t, params, tag), tick): c[st] = c.get(st, 0) + 1
    log('UW', ep, len(tick), 'tickers', json.dumps(c), round(time.time() - t0), 's')
log('DONE')
