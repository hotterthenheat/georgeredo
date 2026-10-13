"""ThetaData fetch helper with a gzip-CSV disk cache keyed by request. The key is read from the environment only; never printed."""
import os, re, time, io, gzip, threading, datetime as dt
import pandas as pd
import thetadata
from thetadata.errors import NoDataFoundError
CACHE = os.environ.get('TD_CACHE', '/tmp/td_cache')
os.makedirs(CACHE, exist_ok=True)
_client = None; _lock = threading.Lock()
STATS = {'hits': 0, 'misses': 0, 'nodata': 0, 'errors': 0, 'backoffs': 0}
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s))
def client():
    global _client
    with _lock:
        if _client is None:
            _client = thetadata.ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='pandas')
    return _client
def _key(method, kw):
    parts = [method] + [f"{k}={kw[k].isoformat() if hasattr(kw[k], 'isoformat') else kw[k]}" for k in sorted(kw)]
    return re.sub(r'[^A-Za-z0-9_.=,:-]+', '_', '__'.join(parts))[:200]
def fetch(method, **kw):
    """Return a DataFrame (possibly empty when the API reports no data). Cached on disk; never refetched."""
    f = os.path.join(CACHE, _key(method, kw) + '.csv.gz')
    if os.path.exists(f):
        with _lock: STATS['hits'] += 1
        try:
            return pd.read_csv(f, compression='gzip')
        except Exception:
            pass  # unreadable (e.g. written concurrently): refetch below
    last = None
    for attempt in range(7):
        try:
            df = getattr(client(), method)(**kw)
            df = df.copy()
            for c in df.columns:
                if str(df[c].dtype).startswith('datetime'): df[c] = df[c].astype(str)
            tmp = f + f'.tmp{os.getpid()}'
            df.to_csv(tmp, index=False, compression='gzip'); os.replace(tmp, f)
            with _lock: STATS['misses'] += 1
            return pd.read_csv(f, compression='gzip')
        except NoDataFoundError:
            pd.DataFrame().to_csv(f, index=False, compression='gzip')
            with _lock: STATS['nodata'] += 1
            return pd.DataFrame()
        except Exception as e:
            last = e; msg = red(e)
            if 'UNAUTHENTICATED' in msg or 'session' in msg.lower():
                global _client
                with _lock: STATS['reauth'] = STATS.get('reauth', 0) + 1; _client = None
                time.sleep(15 * (attempt + 1)); continue
            if 'RESOURCE_EXHAUSTED' in msg or 'UNAVAILABLE' in msg or 'DEADLINE' in msg or 'Unavailable' in msg:
                with _lock: STATS['backoffs'] += 1
                time.sleep(5 * (attempt + 1)); continue
            if attempt < 2: time.sleep(2); continue
            break
    with _lock: STATS['errors'] += 1
    raise RuntimeError(f'{method} {_key(method, kw)}: {red(last)[:300]}')
def month_ranges(start, end):
    """[(first, last)] month chunks covering start..end inclusive."""
    out = []; d = start
    while d <= end:
        nxt = (d.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        out.append((d, min(nxt - dt.timedelta(days=1), end))); d = nxt
    return out
