import os, json, time, datetime as dt, re, concurrent.futures as cf
import thetadata
OUT='/home/user/georgeredo/research/thetadata/provider_checks'; D=dt.date
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+','REDACTED',str(s))
c=thetadata.ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='pandas')
res=[]
def run(name, fn, **kw):
    t0=time.time()
    try:
        df=fn(**kw); r=dict(check=name, ok=True, rows=len(df), ms=int((time.time()-t0)*1000))
    except Exception as e:
        m=red(f'{type(e).__name__}: {e}'); m=re.sub(r'\s+',' ',m); r=dict(check=name, ok=False, error=m[:300], ms=int((time.time()-t0)*1000))
    res.append(r); print(('OK ' if r['ok'] else 'ERR'), f"{name:52s}", r.get('rows',''), r.get('error','')[:150], flush=True); return r
# Tier boundaries from the Subscriptions page: options VALUE 1m from 2020-01-01 / STANDARD tick from 2016-01-01 / PRO tick from 2012-06-01;
# stocks VALUE 1m from 2021-01-01 / STANDARD 1m from 2016-01-01 / PRO tick from 2012-06-01; indices VALUE 1m from 2023-01-01 / STANDARD from 2022-01-01 / PRO from 2017-01-01.
run('options_1m_2018-06-01 (STANDARD+)', c.option_history_quote, symbol='SPY', expiration=D(2018,6,1), interval='1m', date=D(2018,6,1), strike='*', right='call', start_time='12:59:00', end_time='13:00:00')
run('options_1m_2014-06-02 (PRO only)', c.option_history_quote, symbol='SPY', expiration=D(2014,6,6), interval='1m', date=D(2014,6,2), strike='*', right='call', start_time='12:59:00', end_time='13:00:00')
run('options_tick_tradequote_2017-06-02 (STANDARD+)', c.option_history_trade_quote, symbol='SPY', expiration=D(2017,6,2), date=D(2017,6,2), strike='*', right='call', start_time='13:00:00', end_time='13:01:00')
run('options_tick_tradequote_2013-06-07 (PRO only)', c.option_history_trade_quote, symbol='SPY', expiration=D(2013,6,7), date=D(2013,6,7), strike='*', right='call', start_time='13:00:00', end_time='13:01:00')
run('stocks_1m_2018-06-01 (STANDARD+)', c.stock_history_ohlc, symbol='SPY', interval='1m', date=D(2018,6,1))
run('stocks_1m_2014-06-02 (PRO only)', c.stock_history_ohlc, symbol='SPY', interval='1m', date=D(2014,6,2))
run('stocks_tick_trade_2026-03-02 (PRO tick)', c.stock_history_trade, symbol='SPY', date=D(2026,3,2), start_time='13:00:00', end_time='13:00:10')
run('stocks_tick_quote_1s_2026-03-02', c.stock_history_quote, symbol='SPY', interval='1s', date=D(2026,3,2), start_time='13:00:00', end_time='13:00:10')
run('index_1m_2021-06-01 (PRO only)', c.index_history_price, symbol='SPX', interval='1m', date=D(2021,6,1))
run('index_1m_2019-06-03 (PRO only)', c.index_history_price, symbol='SPX', interval='1m', date=D(2019,6,3))
run('index_1m_2017-06-01 (PRO only)', c.index_history_price, symbol='SPX', interval='1m', date=D(2017,6,1))
run('index_1s_2026-03-02 (sub-minute)', c.index_history_price, symbol='SPX', interval='1s', date=D(2026,3,2), start_time='13:00:00', end_time='13:00:30')
run('index_VIX_1m_2021-06-01', c.index_history_price, symbol='VIX', interval='1m', date=D(2021,6,1))
run('index_RUT_1m_2021-06-01', c.index_history_price, symbol='RUT', interval='1m', date=D(2021,6,1))
run('index_NDX_eod_2026-03-02', c.index_history_eod, symbol='NDX', start_date=D(2026,3,2), end_date=D(2026,3,3))
# concurrency: 8 simultaneous option requests (PRO allows 8, STANDARD 4, VALUE 2)
def one(i):
    t0=time.time()
    try: df=c.option_history_quote(symbol='SPY', expiration=D(2026,3,2), interval='1m', date=D(2026,3,2), strike=str(675+i), right='call'); return (i, True, len(df), int((time.time()-t0)*1000))
    except Exception as e: return (i, False, red(str(e))[:120], int((time.time()-t0)*1000))
with cf.ThreadPoolExecutor(8) as ex: outs=list(ex.map(one, range(8)))
ok=sum(1 for o in outs if o[1]); print('concurrency 8: ok', ok, 'errors', [o[2] for o in outs if not o[1]][:3]); res.append(dict(check='concurrency_8_option_requests', ok=ok==8, rows=ok, detail=[o for o in outs]))
json.dump(res, open(f'{OUT}/_tier_probe.json','w'), indent=1, default=str)
