"""Throughput of the daily-lifecycle source: option EOD (OHLC, volume, closing NBBO) for every expiration of a root,
one session per request, sequential and four at a time; and a five-session request. Writes probe_throughput.json."""
import os, json, time, datetime as dt, logging
from concurrent.futures import ThreadPoolExecutor
logging.getLogger('thetadata').setLevel(logging.ERROR)
from thetadata import ThetaClient
c = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars'); D = dt.date
days = [D(2019, 3, 4) + dt.timedelta(days=i) for i in range(14)]
days = [d for d in days if d.weekday() < 5][:10]
res = {}
def one(sym, d):
    t0 = time.time()
    try: df = c.option_history_eod(symbol=sym, expiration='*', start_date=d, end_date=d, strike='*', right='both'); n = df.height
    except Exception as e: n = -1
    return round(time.time() - t0, 2), n
seq = [one('SPY', d) for d in days[:5]]
res['SPY_seq'] = seq; print('SPY sequential', seq, flush=True)
with ThreadPoolExecutor(4) as ex:
    t0 = time.time(); par = list(ex.map(lambda a: one(*a), [(s, d) for s in ['AAPL', 'MSFT', 'NVDA', 'XOM'] for d in days[:5]])); wall = time.time() - t0
res['par4'] = {'calls': par, 'wall': round(wall, 1), 'per_sec': round(len(par) / wall, 2)}; print('4 parallel', res['par4']['wall'], 's for', len(par), 'calls', res['par4']['per_sec'], '/s', flush=True)
t0 = time.time()
try: df = c.option_history_eod(symbol='SPY', expiration='*', start_date=days[0], end_date=days[4], strike='*', right='both'); res['SPY_5day'] = {'secs': round(time.time() - t0, 1), 'rows': df.height}
except Exception as e: res['SPY_5day'] = {'secs': round(time.time() - t0, 1), 'error': type(e).__name__}
print('SPY five sessions in one request', res['SPY_5day'], flush=True)
json.dump(res, open('probe_throughput.json', 'w'), indent=1)
