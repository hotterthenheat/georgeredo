"""Lifecycle audit, pass 3 (2026-10-15): the questions the lifecycle brief adds to 02_coverage_matrix.md.
Delisted and renamed underlyings (survivorship), vendor Greeks floor 2015-2020, interest-rate history, tick-level and
1-second option quotes, whole-chain request cost on an index ETF and on single names (to size an archive).
One login; key from THETADATA_KEY only; exceptions redacted; writes probe3.json."""
import os, re, json, time, datetime as dt, logging
logging.getLogger('thetadata').setLevel(logging.ERROR)
import polars as pl, grpc
from thetadata import ThetaClient
from thetadata.errors import NoDataFoundError
KEY = os.environ['THETADATA_KEY']
c = ThetaClient(api_key=KEY, dataframe_type='polars')
D = dt.date
res = {'generated_utc': dt.datetime.now(dt.timezone.utc).isoformat(), 'methods_with_rate': [m for m in dir(c) if 'rate' in m.lower()], 'probes': {}}
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s)).replace(KEY, 'REDACTED')
def save(): json.dump(res, open('probe3.json', 'w'), indent=1, default=str)
def call(name, **kw):
    t0 = time.time()
    try: return getattr(c, name)(**kw), round(time.time() - t0, 2), None
    except NoDataFoundError: return None, round(time.time() - t0, 2), 'NO_DATA'
    except grpc.RpcError as e: return None, round(time.time() - t0, 2), f'{e.code()} {red(e.details())[:160]}'
    except Exception as e: return None, round(time.time() - t0, 2), f'{type(e).__name__} {red(e)[:160]}'
def probe(label, name, **kw):
    out, secs, err = call(name, **kw)
    s = None
    if isinstance(out, pl.DataFrame):
        s = {'rows': out.height, 'columns': out.columns, 'est_bytes': int(out.estimated_size())}
        for col in ('timestamp', 'date', 'expiration', 'created'):
            if col in out.columns:
                s['first'] = str(out[col].min())[:19]; s['last'] = str(out[col].max())[:19]; break
    res['probes'][label] = {'method': name, 'args': {k: str(v) for k, v in kw.items()}, 'secs': secs, 'error': err, **(s or {})}
    print(label, err or {k: v for k, v in (s or {}).items() if k != 'columns'}, secs, flush=True); save()
    return out
def exps(sym):
    out = probe(f'expirations/{sym}', 'option_list_expirations', symbol=sym)
    if out is None: return []
    return sorted(str(x)[:10] for x in out[out.columns[-1]].to_list())
# 1. survivorship: a delisted name (TWTR, taken private 2022-10-27), a renamed one (FB -> META 2022-06-09), a bankrupt one (BBBY)
for sym in ['TWTR', 'FB', 'META', 'BBBY']:
    ex = exps(sym)
    res['probes'][f'expirations/{sym}']['n'] = len(ex)
    if ex: res['probes'][f'expirations/{sym}']['range'] = [ex[0], ex[-1]]
    save()
tw = [e for e in exps('TWTR') if '2022-09-01' <= e <= '2022-11-30']
if tw:
    probe('quote_1m/TWTR/2022-10-20', 'option_history_quote', symbol='TWTR', expiration=D.fromisoformat(tw[0]), start_date=D(2022, 10, 20), end_date=D(2022, 10, 20), strike='*', right='both', interval='1m')
probe('stock_eod/TWTR/2022', 'stock_history_eod', symbol='TWTR', start_date=D(2022, 1, 1), end_date=D(2022, 12, 31))
# 2. vendor Greeks floor
spy = exps('SPY')
def exp_after(d):
    return next(D.fromisoformat(e) for e in spy if e >= d.isoformat())
for y in [2015, 2016, 2017, 2018, 2019]:
    d = D(y, 6, 3) if D(y, 6, 3).weekday() < 5 else D(y, 6, 5)
    e = exp_after(d + dt.timedelta(days=10))
    probe(f'greeks_eod/SPY/{y}', 'option_history_greeks_eod', symbol='SPY', expiration=e, start_date=d, end_date=d, strike='*', right='both')
    probe(f'greeks_iv_1m/SPY/{y}', 'option_history_greeks_implied_volatility', symbol='SPY', expiration=e, start_date=d, end_date=d, strike='*', right='both', interval='1m')
# 3. interest rates
for m in res['methods_with_rate']:
    if 'history' in m:
        probe(f'{m}/SOFR/2015-2026', m, symbol='SOFR', start_date=D(2015, 1, 1), end_date=D(2026, 10, 14))
# 4. granularity and request cost: whole chain, one expiration, one day
d = D(2024, 6, 4); e = exp_after(d + dt.timedelta(days=2))
probe('quote_1s/SPY/2024-06-04/one_contract', 'option_history_quote', symbol='SPY', expiration=e, start_date=d, end_date=d, strike='530', right='call', interval='1s')
probe('quote_tick/SPY/2024-06-04/one_contract', 'option_history_quote', symbol='SPY', expiration=e, start_date=d, end_date=d, strike='530', right='call', interval='tick')
probe('trade_quote/SPY/2024-06-04/chain', 'option_history_trade_quote', symbol='SPY', expiration=e, start_date=d, end_date=d, strike='*', right='both')
probe('quote_1m/SPY/2024-06-04/chain_weekly', 'option_history_quote', symbol='SPY', expiration=e, start_date=d, end_date=d, strike='*', right='both', interval='1m')
for sym in ['AAPL', 'AMD', 'CRWD']:
    ex = exps(sym); e2 = next(D.fromisoformat(x) for x in ex if x >= '2024-06-14')
    probe(f'quote_1m/{sym}/2024-06-04/chain_exp={e2}', 'option_history_quote', symbol=sym, expiration=e2, start_date=d, end_date=d, strike='*', right='both', interval='1m')
    probe(f'ohlc_1m/{sym}/2024-06-04/chain_exp={e2}', 'option_history_ohlc', symbol=sym, expiration=e2, start_date=d, end_date=d, strike='*', right='both', interval='1m')
    probe(f'eod/{sym}/2024-06/all_exps', 'option_history_eod', symbol=sym, expiration='*', start_date=d, end_date=d, strike='*', right='both')
print('PROBE3 DONE')
