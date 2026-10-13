"""Data access for the backtest: Unusual Whales REST with a gzip disk cache. Keys come from env only."""
import os, json, gzip, time, hashlib, urllib.request, urllib.parse, datetime, zoneinfo, threading
ET = zoneinfo.ZoneInfo('America/New_York')
BASE = 'https://api.unusualwhales.com/api/'
CACHE = os.environ.get('BT_CACHE', os.path.dirname(os.path.abspath(__file__)) + '/cache')
TOKEN = os.environ.get('UW_API_TOKEN')
_lock = threading.Lock(); STATS = {'hits': 0, 'misses': 0, 'errors': 0}

def _key(path, params):
    s = path + '?' + urllib.parse.urlencode(sorted(params.items()))
    return hashlib.sha1(s.encode()).hexdigest()[:24] + '_' + s.replace('/', '_').replace('?', '_').replace('&', '_').replace('=', '-')[:90]

def get(path, params=None, ttl_days=None):
    params = params or {}
    f = os.path.join(CACHE, _key(path, params) + '.json.gz')
    if os.path.exists(f):
        with _lock: STATS['hits'] += 1
        with gzip.open(f, 'rt') as fh: return json.load(fh)
    url = BASE + path + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/json'})
    last = None
    for i in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: data = json.loads(r.read())
            with gzip.open(f, 'wt') as fh: json.dump(data, fh)
            with _lock: STATS['misses'] += 1
            return data
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 502, 503, 504): time.sleep(3 * (i + 1)); continue
            if e.code in (404, 422, 400):
                with gzip.open(f, 'wt') as fh: json.dump({'error': e.code}, fh)
                return {'error': e.code}
            time.sleep(2)
        except Exception as e:
            last = e; time.sleep(2)
    with _lock: STATS['errors'] += 1
    return {'error': str(last)}

def et(ts):
    return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(ET)

def underlying_bars(ticker, date):
    """Return (rth, pre) lists of dicts with t (ET datetime), o,h,l,c,v for one session."""
    d = get(f'stock/{ticker}/ohlc/1m', {'date': date, 'limit': 2000})
    rows = d.get('data') or []
    rth, pre = [], []
    for r in rows:
        try:
            b = dict(t=et(r['start_time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close']), v=int(r.get('volume') or 0))
        except Exception: continue
        if b['t'].strftime('%Y-%m-%d') != date: continue
        if r.get('market_time') == 'r': rth.append(b)
        elif r.get('market_time') == 'pr': pre.append(b)
    rth.sort(key=lambda b: b['t']); pre.sort(key=lambda b: b['t'])
    return rth, pre

def gex_levels(ticker, date):
    d = get(f'stock/{ticker}/gex-levels', {'date': date}).get('data') or {}
    out = {}
    for k in ('gamma_flip', 'call_wall', 'put_wall', 'gamma_magnet'):
        try: out[k] = float(d.get(k))
        except Exception: out[k] = None
    return out

def iv_context(ticker, date):
    d = get(f'stock/{ticker}/interpolated-iv', {'date': date}).get('data') or []
    for r in d:
        if r.get('days') == 1:
            try: return dict(iv1d=float(r['volatility']), pct=float(r['percentile']))
            except Exception: pass
    return dict(iv1d=None, pct=None)

def contract_id(ticker, expiry, side, strike):
    return f"{ticker}{expiry.strftime('%y%m%d')}{side}{int(round(strike * 1000)):08d}"

def option_bars(cid, date):
    d = get(f'option-contract/{cid}/intraday', {'date': date})
    rows = d.get('data') or []
    out = []
    for r in rows:
        try:
            out.append(dict(t=et(r['start_time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close']), vw=float(r['avg_price']) if r.get('avg_price') else None,
                            vol=int(r.get('volume_ask_side') or 0) + int(r.get('volume_bid_side') or 0) + int(r.get('volume_mid_side') or 0) + int(r.get('volume_no_side') or 0),
                            ask_p=float(r.get('premium_ask_side') or 0), bid_p=float(r.get('premium_bid_side') or 0)))
        except Exception: continue
    out.sort(key=lambda b: b['t'])
    return out
