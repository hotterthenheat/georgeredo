"""Point-in-time option universe, step 1: every listed expiration per option root, from ThetaData
(option_list_expirations — the full historical list, delisted roots included). One login, NW threads, resumable:
results append to {OUT}/expirations.jsonl (one line per root) and roots already present are skipped.
Key from THETADATA_KEY only; exceptions redacted. Usage: set -a; . "$SP/secrets/research.env"; set +a; NW=8 OUT=... python3 -I list_expirations.py"""
import os, re, sys, json, time, threading, logging, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
logging.getLogger('thetadata').setLevel(logging.ERROR)
import polars as pl, grpc
from thetadata import ThetaClient
from thetadata.errors import NoDataFoundError
HERE = os.path.dirname(os.path.abspath(__file__))
ROOTS = os.environ.get('ROOTS', os.path.join(HERE, '..', '..', 'data_inventory', 'thetadata_option_roots.txt'))
OUT = os.environ['OUT']; os.makedirs(OUT, exist_ok=True)
NW = int(os.environ.get('NW', '8'))
KEY = os.environ['THETADATA_KEY']
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s)).replace(KEY, 'REDACTED')
def log(*a): print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *[red(x) for x in a], flush=True)
lock = threading.Lock(); state = {'c': None, 'gen': 0}
def client(seen=None):
    with lock:
        if state['c'] is None or (seen is not None and seen == state['gen']):
            state['c'] = ThetaClient(api_key=KEY, dataframe_type='polars'); state['gen'] += 1; log('login gen', state['gen'])
        return state['c'], state['gen']
def fetch(root):
    for attempt in range(6):
        c, g = client()
        try:
            df = c.option_list_expirations(symbol=root)
            col = df.columns[-1]
            exps = sorted(str(x)[:10] for x in df[col].to_list())
            return {'root': root, 'n': len(exps), 'first': exps[0] if exps else None, 'last': exps[-1] if exps else None, 'expirations': exps}
        except NoDataFoundError: return {'root': root, 'n': 0, 'first': None, 'last': None, 'expirations': []}
        except grpc.RpcError as e:
            code = e.code()
            if code == grpc.StatusCode.UNAUTHENTICATED: client(g); continue
            if code in (grpc.StatusCode.RESOURCE_EXHAUSTED, grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.INTERNAL, grpc.StatusCode.UNKNOWN): time.sleep(2 + 3 * attempt); continue
            return {'root': root, 'error': f'{code} {red(e.details())[:160]}'}
        except Exception as e: return {'root': root, 'error': f'{type(e).__name__} {red(e)[:160]}'}
    return {'root': root, 'error': 'retries exhausted'}
if __name__ == '__main__':
    roots = [r for r in open(ROOTS).read().split() if r]
    path = os.path.join(OUT, 'expirations.jsonl')
    done = set()
    if os.path.exists(path):
        for line in open(path):
            try: done.add(json.loads(line)['root'])
            except Exception: pass
    todo = [r for r in roots if r not in done]
    log('roots', len(roots), 'done', len(done), 'todo', len(todo))
    t0 = time.time(); n = 0; err = 0
    with open(path, 'a') as fh, ThreadPoolExecutor(NW) as ex:
        futs = {ex.submit(fetch, r): r for r in todo}
        for f in as_completed(futs):
            rec = f.result(); fh.write(json.dumps(rec) + '\n'); n += 1; err += 'error' in rec
            if n % 500 == 0: fh.flush(); log('progress', n, '/', len(todo), 'errors', err, round(time.time() - t0, 1), 's')
    log('DONE', n, 'roots', 'errors', err, round(time.time() - t0, 1), 's')
