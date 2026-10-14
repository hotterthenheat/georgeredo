"""ThetaData boundary audit: the first and last available date per product, discovered through the API
(list_dates where it exists, else history probes). One login. Key from THETADATA_KEY only; exceptions redacted.
Writes JSON incrementally to OUT (env) so a crash keeps partial results."""
import os, re, sys, json, time, inspect, datetime as dt, logging
logging.getLogger('thetadata').setLevel(logging.ERROR)
import polars as pl, grpc
from thetadata import ThetaClient
from thetadata.errors import NoDataFoundError
OUT = os.environ.get('OUT', 'boundaries.json')
KEY = os.environ['THETADATA_KEY']
c = ThetaClient(api_key=KEY, dataframe_type='polars')
D = dt.date
res = {'generated_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'methods': {}, 'list_dates': {}, 'history': {}}
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s)).replace(KEY, 'REDACTED')
def save(): json.dump(res, open(OUT, 'w'), indent=1, default=str)
def log(*a): print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *[red(x) for x in a], flush=True)

# 1. every history/list method and its signature (the client is the entitlement surface)
for m in sorted(dir(c)):
    if m.startswith('_'): continue
    f = getattr(c, m)
    if callable(f) and any(k in m for k in ('history', 'list', 'flat', 'snapshot', 'greek', 'implied')):
        try: res['methods'][m] = str(inspect.signature(f))
        except Exception: res['methods'][m] = '?'
save()

def call(name, **kw):
    t0 = time.time()
    try:
        out = getattr(c, name)(**kw)
        return out, round(time.time() - t0, 1), None
    except NoDataFoundError: return None, round(time.time() - t0, 1), 'NO_DATA'
    except grpc.RpcError as e: return None, round(time.time() - t0, 1), f'{e.code()} {red(e.details())[:160]}'
    except Exception as e: return None, round(time.time() - t0, 1), f'{type(e).__name__} {red(e)[:160]}'

def summarize(df):
    if df is None: return None
    if isinstance(df, pl.DataFrame):
        col = next((x for x in df.columns if x.lower() in ('date', 'created', 'dates', 'ms_of_day')), df.columns[0])
        vals = df[col]
        return {'rows': df.height, 'columns': df.columns, 'first': str(vals.min())[:10], 'last': str(vals.max())[:10]}
    s = str(df); return {'repr': s[:300]}

# 2. list_dates per product, per request type (introspect allowed request types by trying the common ones)
REQ = ['EOD', 'OHLC', 'QUOTE', 'TRADE', 'TRADE_QUOTE', 'OPEN_INTEREST', 'IMPLIED_VOLATILITY', 'GREEKS', 'PRICE']
for sym in ['SPY', 'AAPL', 'MSFT', 'IWM', 'GME']:
    for r in REQ:
        out, secs, err = call('stock_list_dates', request_type=r, symbol=sym)
        res['list_dates'][f'stock/{sym}/{r}'] = {'secs': secs, 'error': err, **(summarize(out) or {})}
        log('stock_list_dates', sym, r, err or summarize(out)); save()
for sym in ['SPX', 'VIX', 'RUT', 'NDX', 'DJI', 'VIX1D']:
    out, secs, err = call('index_list_dates', symbol=sym)
    res['list_dates'][f'index/{sym}'] = {'secs': secs, 'error': err, **(summarize(out) or {})}
    log('index_list_dates', sym, err or summarize(out)); save()
for sym in ['SPY', 'AAPL', 'SPXW', 'SPX', 'TSLA', 'GME']:
    out, secs, err = call('option_list_expirations', symbol=sym)
    s = summarize(out); res['list_dates'][f'option_expirations/{sym}'] = {'secs': secs, 'error': err, **(s or {})}
    log('option_list_expirations', sym, err or s); save()
    if out is not None and isinstance(out, pl.DataFrame) and out.height:
        col = out.columns[0]; exps = sorted(out[col].to_list())
        first_exp = exps[0]; last_exp = exps[-1]
        for r in ['EOD', 'QUOTE', 'TRADE', 'OHLC', 'OPEN_INTEREST', 'IMPLIED_VOLATILITY', 'GREEKS']:
            out2, secs2, err2 = call('option_list_dates', request_type=r, symbol=sym, expiration=first_exp)
            res['list_dates'][f'option/{sym}/{r}/exp={first_exp}'] = {'secs': secs2, 'error': err2, **(summarize(out2) or {})}
            log('option_list_dates', sym, r, first_exp, err2 or summarize(out2)); save()
save()

# 3. history probes at the edges (small windows) to confirm the floors and the column sets
H = [
 ('stock_history_eod', dict(symbol='SPY', start_date=D(2012, 1, 1), end_date=D(2012, 12, 31))),
 ('stock_history_eod', dict(symbol='SPY', start_date=D(2011, 1, 1), end_date=D(2011, 12, 31))),
 ('stock_history_ohlc', dict(symbol='SPY', start_date=D(2014, 6, 2), end_date=D(2014, 6, 2), interval='1m')),
 ('stock_history_ohlc', dict(symbol='SPY', start_date=D(2012, 6, 4), end_date=D(2012, 6, 4), interval='1m')),
 ('stock_history_quote', dict(symbol='SPY', start_date=D(2014, 6, 2), end_date=D(2014, 6, 2), interval='1m')),
 ('stock_history_trade', dict(symbol='SPY', start_date=D(2012, 6, 4), end_date=D(2012, 6, 4))),
 ('index_history_eod', dict(symbol='SPX', start_date=D(2013, 1, 1), end_date=D(2013, 12, 31))),
 ('index_history_eod', dict(symbol='SPX', start_date=D(2016, 1, 1), end_date=D(2016, 12, 31))),
 ('index_history_eod', dict(symbol='SPX', start_date=D(2019, 1, 1), end_date=D(2019, 12, 31))),
 ('index_history_price', dict(symbol='SPX', start_date=D(2017, 6, 1), end_date=D(2017, 6, 1), interval='1m')),
 ('index_history_price', dict(symbol='SPX', start_date=D(2016, 6, 1), end_date=D(2016, 6, 1), interval='1m')),
 ('option_history_eod', dict(symbol='SPY', expiration='*', start_date=D(2012, 6, 4), end_date=D(2012, 6, 8))),
 ('option_history_eod', dict(symbol='SPY', expiration='*', start_date=D(2013, 6, 3), end_date=D(2013, 6, 7))),
 ('option_history_open_interest', dict(symbol='SPY', expiration='*', start_date=D(2013, 6, 3), end_date=D(2013, 6, 7))),
 ('option_history_open_interest', dict(symbol='SPY', expiration='*', start_date=D(2012, 6, 4), end_date=D(2012, 6, 8))),
]
# greeks / IV history, if the client exposes them (names vary by version)
for name in list(res['methods']):
    if name.startswith('option_history') and ('greek' in name or 'implied' in name):
        H.append((name, dict(symbol='SPY', expiration='*', start_date=D(2013, 6, 3), end_date=D(2013, 6, 3))))
        H.append((name, dict(symbol='SPY', expiration='*', start_date=D(2016, 6, 1), end_date=D(2016, 6, 1))))
for name, kw in H:
    if name not in res['methods'] and not hasattr(c, name):
        res['history'][f'{name} {kw}'] = {'error': 'method not in client'}; continue
    out, secs, err = call(name, **kw)
    s = summarize(out)
    res['history'][f"{name} {kw.get('symbol')} {kw.get('start_date')}..{kw.get('end_date')} {kw.get('interval','')}"] = {'secs': secs, 'error': err, **(s or {})}
    log(name, kw.get('symbol'), kw.get('start_date'), kw.get('interval', ''), err or {k: v for k, v in s.items() if k != 'columns'}); save()
log('PROBE DONE')
