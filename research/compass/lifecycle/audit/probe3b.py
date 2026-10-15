"""Pass 3b: survivorship checks with expirations alive on the probe date (pass 3 picked a TWTR expiration that had
already expired). Appends to probe3.json."""
import os, re, json, time, datetime as dt, logging
logging.getLogger('thetadata').setLevel(logging.ERROR)
import polars as pl, grpc
from thetadata import ThetaClient
from thetadata.errors import NoDataFoundError
KEY = os.environ['THETADATA_KEY']; c = ThetaClient(api_key=KEY, dataframe_type='polars'); D = dt.date
res = json.load(open('probe3.json'))
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s)).replace(KEY, 'REDACTED')
def probe(label, name, **kw):
    t0 = time.time()
    try: out = getattr(c, name)(**kw); err = None
    except NoDataFoundError: out, err = None, 'NO_DATA'
    except grpc.RpcError as e: out, err = None, f'{e.code()} {red(e.details())[:160]}'
    except Exception as e: out, err = None, f'{type(e).__name__} {red(e)[:160]}'
    s = {'rows': out.height} if isinstance(out, pl.DataFrame) else {}
    if isinstance(out, pl.DataFrame) and 'timestamp' in out.columns: s.update(first=str(out['timestamp'].min())[:19], last=str(out['timestamp'].max())[:19])
    res['probes'][label] = {'method': name, 'args': {k: str(v) for k, v in kw.items()}, 'secs': round(time.time() - t0, 2), 'error': err, **s}
    print(label, err or s, flush=True); json.dump(res, open('probe3.json', 'w'), indent=1, default=str)
def exps(sym):
    out = c.option_list_expirations(symbol=sym); return sorted(str(x)[:10] for x in out[out.columns[-1]].to_list())
for sym, day in [('TWTR', D(2022, 10, 20)), ('TWTR', D(2022, 10, 27)), ('FB', D(2022, 5, 2)), ('META', D(2022, 6, 10)), ('BBBY', D(2023, 4, 20))]:
    e = next(D.fromisoformat(x) for x in exps(sym) if x >= (day + dt.timedelta(days=1)).isoformat())
    probe(f'quote_1m/{sym}/{day}/exp={e}', 'option_history_quote', symbol=sym, expiration=e, start_date=day, end_date=day, strike='*', right='both', interval='1m')
# the listed TWTR expirations after the delisting: is anything quoted?
late = [x for x in exps('TWTR') if x >= '2023-01-01'][:1]
for x in late:
    probe(f'list_dates/TWTR/QUOTE/exp={x}', 'option_list_dates', request_type='QUOTE', symbol='TWTR', expiration=D.fromisoformat(x))
print('PROBE3B DONE')
