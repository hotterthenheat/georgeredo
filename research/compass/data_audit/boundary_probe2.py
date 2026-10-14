"""ThetaData boundary audit, pass 2: pin the floors the first pass left open, with correct argument types
(expiration as a date). Stock EOD floor by year; stock quote/trade floors; index EOD floor; option quote/trade/OHLC
floors; Greeks/IV history with a real expiration. One login. Key from THETADATA_KEY only; exceptions redacted."""
import os, re, sys, json, time, datetime as dt, logging
logging.getLogger('thetadata').setLevel(logging.ERROR)
import polars as pl, grpc
from thetadata import ThetaClient
from thetadata.errors import NoDataFoundError
OUT = os.environ.get('OUT', 'boundaries2.json')
KEY = os.environ['THETADATA_KEY']
c = ThetaClient(api_key=KEY, dataframe_type='polars')
D = dt.date
res = {'generated_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'probes': {}}
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s)).replace(KEY, 'REDACTED')
def save(): json.dump(res, open(OUT, 'w'), indent=1, default=str)
def log(*a): print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *[red(x) for x in a], flush=True)
def call(name, **kw):
    t0 = time.time()
    try: return getattr(c, name)(**kw), round(time.time() - t0, 1), None
    except NoDataFoundError: return None, round(time.time() - t0, 1), 'NO_DATA'
    except grpc.RpcError as e: return None, round(time.time() - t0, 1), f'{e.code()} {red(e.details())[:160]}'
    except Exception as e: return None, round(time.time() - t0, 1), f'{type(e).__name__} {red(e)[:160]}'
def summarize(df):
    if df is None or not isinstance(df, pl.DataFrame): return None if df is None else {'repr': str(df)[:200]}
    col = next((x for x in df.columns if x.lower() in ('date', 'created', 'dates', 'timestamp')), df.columns[0])
    return {'rows': df.height, 'columns': df.columns, 'first': str(df[col].min())[:19], 'last': str(df[col].max())[:19]}
def probe(label, name, **kw):
    out, secs, err = call(name, **kw)
    s = summarize(out)
    res['probes'][label] = {'method': name, 'args': {k: str(v) for k, v in kw.items()}, 'secs': secs, 'error': err, **(s or {})}
    log(label, err or {k: v for k, v in s.items() if k != 'columns'}, f'{secs}s'); save()
    return out

# A. stock EOD floor, by year, two symbols (the all-symbol download depends on this)
for sym in ['SPY', 'AAPL']:
    for y in range(2012, 2020):
        probe(f'stock_eod/{sym}/{y}', 'stock_history_eod', symbol=sym, start_date=D(y, 1, 1), end_date=D(y, 12, 31))
# B. stock quotes and trades: floors
for y in [2012, 2014, 2016, 2018, 2020, 2024]:
    d = D(y, 6, 2) if D(y, 6, 2).weekday() < 5 else D(y, 6, 3)
    probe(f'stock_quote_1m/SPY/{y}', 'stock_history_quote', symbol='SPY', start_date=d, end_date=d, interval='1m')
    probe(f'stock_trade/SPY/{y}', 'stock_history_trade', symbol='SPY', start_date=d, end_date=d)
# C. index EOD floor and 1-min price floor
for y in [2017, 2018]:
    probe(f'index_eod/SPX/{y}', 'index_history_eod', symbol='SPX', start_date=D(y, 1, 1), end_date=D(y, 12, 31))
for y in [2017, 2018, 2019, 2020]:
    probe(f'index_eod/VIX/{y}', 'index_history_eod', symbol='VIX', start_date=D(y, 1, 1), end_date=D(y, 12, 31))
probe('index_price_1m/VIX/2017-06-01', 'index_history_price', symbol='VIX', start_date=D(2017, 6, 1), end_date=D(2017, 6, 1), interval='1m')
probe('index_price_1m/RUT/2017-06-01', 'index_history_price', symbol='RUT', start_date=D(2017, 6, 1), end_date=D(2017, 6, 1), interval='1m')
# D. option quotes / trades / OHLC floors on SPY, nearest monthly expiration to each probe date
exps = call('option_list_expirations', symbol='SPY')[0]
col = exps.columns[-1]; expl = sorted(str(x)[:10] for x in exps[col].to_list())
res['spy_expirations'] = {'count': len(expl), 'first': expl[0], 'last': expl[-1]}
def exp_after(d):
    for e in expl:
        if e >= d.isoformat(): return D.fromisoformat(e)
for y in [2012, 2013, 2014, 2016, 2020, 2024]:
    d = D(y, 6, 4) if D(y, 6, 4).weekday() < 5 else D(y, 6, 5)
    e = exp_after(d + dt.timedelta(days=10))
    for kind, kw in [('quote_1m', dict(interval='1m')), ('trade', {}), ('ohlc_1m', dict(interval='1m')), ('trade_quote', {})]:
        probe(f'option_{kind}/SPY/{y}/exp={e}', f'option_history_{kind.replace("_1m", "")}', symbol='SPY', expiration=e, start_date=d, end_date=d, strike='*', right='both', **kw)
    for kind in ['greeks_all', 'greeks_implied_volatility', 'greeks_first_order', 'binomial_greeks_all']:
        probe(f'option_{kind}/SPY/{y}/exp={e}', f'option_history_{kind}', symbol='SPY', expiration=e, start_date=d, end_date=d, strike='*', right='both', interval='1m')
    probe(f'option_greeks_eod/SPY/{y}/exp={e}', 'option_history_greeks_eod', symbol='SPY', expiration=e, start_date=d, end_date=d, strike='*', right='both')
# E. list_dates with correct types (one expiration), stock request types that exist
e0 = exp_after(D(2013, 6, 14))
for r in ['EOD', 'QUOTE', 'TRADE', 'OHLC', 'OPEN_INTEREST']:
    probe(f'option_list_dates/SPY/{r}/exp={e0}', 'option_list_dates', request_type=r, symbol='SPY', expiration=e0)
log('PROBE2 DONE')
