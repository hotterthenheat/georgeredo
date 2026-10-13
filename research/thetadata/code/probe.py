import os, sys, json, time, datetime as dt, traceback, re
import thetadata
OUT='/home/user/georgeredo/research/thetadata/provider_checks'
KEY=os.environ.get('THETADATA_KEY')
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+','REDACTED',str(s))
res=[]
def run(name, fn, **kw):
    t0=time.time()
    try:
        df=fn(**kw)
        try:
            n=len(df); cols=list(df.columns)[:14]
            head=df.head(3).to_dict(orient='records') if hasattr(df,'to_dict') else str(df)[:300]
            first=last=None
            for c in df.columns:
                if 'time' in c.lower() or 'date' in c.lower():
                    first, last = str(df[c].iloc[0]), str(df[c].iloc[-1]); break
        except Exception as e:
            n=None; cols=None; head=str(df)[:300]; first=last=None
        r=dict(check=name, ok=True, rows=n, cols=cols, first=first, last=last, ms=int((time.time()-t0)*1000), head=json.loads(json.dumps(head, default=str)))
    except Exception as e:
        r=dict(check=name, ok=False, error=red(f'{type(e).__name__}: {e}')[:600], ms=int((time.time()-t0)*1000))
    res.append(r); print(f"{'OK ' if r['ok'] else 'ERR'} {name:55s} rows={r.get('rows')} {r.get('first','')}..{r.get('last','')} {r.get('error','')[:160]}", flush=True)
    json.dump(r, open(f'{OUT}/{re.sub(r"[^A-Za-z0-9_-]+","_",name)}.json','w'), indent=1, default=str)
    return r
try:
    c=thetadata.ThetaClient(api_key=KEY, dataframe_type='pandas'); print('auth OK', flush=True)
except Exception as e:
    print('AUTH FAILED', red(str(e))[:400]); sys.exit(1)
D=dt.date
run('index_list_symbols', c.index_list_symbols)
for d in (D(2026,3,2), D(2024,6,3), D(2023,1,3), D(2022,1,3)):
    run(f'index_history_price_SPX_1m_{d}', c.index_history_price, symbol='SPX', interval='1m', date=d)
run('index_history_price_VIX_1m_2026-03-02', c.index_history_price, symbol='VIX', interval='1m', date=D(2026,3,2))
run('index_history_price_NDX_1m_2026-03-02', c.index_history_price, symbol='NDX', interval='1m', date=D(2026,3,2))
run('index_history_price_RUT_1m_2026-03-02', c.index_history_price, symbol='RUT', interval='1m', date=D(2026,3,2))
run('stock_history_ohlc_SPY_1m_2026-03-02', c.stock_history_ohlc, symbol='SPY', interval='1m', date=D(2026,3,2))
run('stock_history_ohlc_SPY_1m_2021-01-04', c.stock_history_ohlc, symbol='SPY', interval='1m', date=D(2021,1,4))
run('stock_history_quote_SPY_1m_2026-03-02', c.stock_history_quote, symbol='SPY', interval='1m', date=D(2026,3,2))
run('option_list_expirations_SPY', c.option_list_expirations, symbol='SPY')
for strike in ('682', '682.0', '682000', '682.000'):
    r=run(f'option_history_quote_SPY_2026-03-02_C_strike_{strike}_1m', c.option_history_quote, symbol='SPY', expiration=D(2026,3,2), interval='1m', date=D(2026,3,2), strike=strike, right='call')
    if r['ok'] and r.get('rows'): SK=strike; break
else: SK='682'
run('option_history_ohlc_SPY_2026-03-02_C682_1m', c.option_history_ohlc, symbol='SPY', expiration=D(2026,3,2), interval='1m', date=D(2026,3,2), strike=SK, right='call')
run('option_history_quote_SPY_2026-03-02_C682_1s', c.option_history_quote, symbol='SPY', expiration=D(2026,3,2), interval='1s', date=D(2026,3,2), strike=SK, right='call', start_time='12:59:00', end_time='13:02:00')
run('option_history_trade_quote_SPY_2026-03-02_C682', c.option_history_trade_quote, symbol='SPY', expiration=D(2026,3,2), date=D(2026,3,2), strike=SK, right='call', start_time='12:59:00', end_time='13:05:00')
run('option_history_quote_SPY_2025-06-02_ATM_1m', c.option_history_quote, symbol='SPY', expiration=D(2025,6,2), interval='1m', date=D(2025,6,2), strike='*', right='call', start_time='12:59:00', end_time='13:01:00')
run('option_history_quote_SPY_2022-01-03_1m', c.option_history_quote, symbol='SPY', expiration=D(2022,1,3), interval='1m', date=D(2022,1,3), strike='*', right='call', start_time='12:59:00', end_time='13:01:00')
run('option_history_quote_SPY_2020-06-01_1m', c.option_history_quote, symbol='SPY', expiration=D(2020,6,1), interval='1m', date=D(2020,6,1), strike='*', right='call', start_time='12:59:00', end_time='13:01:00')
run('option_history_quote_SPXW_2026-03-04_C6815_1m', c.option_history_quote, symbol='SPXW', expiration=D(2026,3,4), interval='1m', date=D(2026,3,4), strike='6815', right='call', start_time='12:59:00', end_time='13:01:00')
run('option_history_quote_SPX_2026-03-04_C6815_1m', c.option_history_quote, symbol='SPX', expiration=D(2026,3,4), interval='1m', date=D(2026,3,4), strike='6815', right='call', start_time='12:59:00', end_time='13:01:00')
run('option_at_time_quote_SPY_0DTE_13h_week', c.option_at_time_quote, symbol='SPY', start_date=D(2026,3,2), end_date=D(2026,3,6), time_of_day='13:00:00', expiration='0DTE', strike='*', right='both')
run('option_history_quote_SPY_2026-03-02_C682_tick', c.option_history_quote, symbol='SPY', expiration=D(2026,3,2), interval='0', date=D(2026,3,2), strike=SK, right='call', start_time='13:00:00', end_time='13:00:30')
json.dump(res, open(f'{OUT}/_summary.json','w'), indent=1, default=str)
print('checks', len(res), 'ok', sum(1 for r in res if r['ok']))
