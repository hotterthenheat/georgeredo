import os, re, json, time, datetime as dt
import thetadata, pandas as pd
from thetadata.errors import NoDataFoundError
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+','REDACTED',str(s))
c = thetadata.ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='pandas')
D = dt.date
def run(name, fn, show=True, **kw):
    t0=time.time()
    try:
        df = fn(**kw); print(f"OK  {name}: rows={len(df)} ms={int((time.time()-t0)*1000)}")
        if show: print(df.to_string(max_rows=14))
        return df
    except NoDataFoundError as e: print(f"NODATA {name}")
    except Exception as e: print(f"ERR {name}: {red(type(e).__name__+': '+str(e))[:300]}")
# timestamp convention: 1s vs 1m around 15:30 and 16:00
s = run('SPX 1s 15:29:55-15:30:05', c.index_history_price, symbol='SPX', interval='1s', date=D(2026,3,2), start_time='15:29:55', end_time='15:30:05')
m = run('SPX 1m 15:29-15:31', c.index_history_price, symbol='SPX', interval='1m', date=D(2026,3,2), start_time='15:29:00', end_time='15:31:00')
s2 = run('SPX 1s 15:59:55-16:00:10', c.index_history_price, symbol='SPX', interval='1s', date=D(2026,3,2), start_time='15:59:55', end_time='16:00:10')
m2 = run('SPX 1m 15:59-16:00', c.index_history_price, symbol='SPX', interval='1m', date=D(2026,3,2), start_time='15:59:00', end_time='16:00:00')
run('SPX eod 2026-03-02', c.index_history_eod, symbol='SPX', start_date=D(2026,3,2), end_date=D(2026,3,3))
run('SPY 1m utp_cta 15:58-16:00', c.stock_history_ohlc, symbol='SPY', interval='1m', date=D(2026,3,2), start_time='15:58:00', end_time='16:00:00', venue='utp_cta')
run('SPY 1m nqb 15:58-16:00', c.stock_history_ohlc, symbol='SPY', interval='1m', date=D(2026,3,2), start_time='15:58:00', end_time='16:00:00')
run('SPY eod 2026-03-02', c.stock_history_eod, symbol='SPY', start_date=D(2026,3,2), end_date=D(2026,3,3))
run('SPY 1m utp_cta 09:30-09:31', c.stock_history_ohlc, symbol='SPY', interval='1m', date=D(2026,3,2), start_time='09:30:00', end_time='09:31:00', venue='utp_cta')
# range limits
run('SPX 1m 3-month range 2024-01-01..03-31', c.index_history_price, show=False, symbol='SPX', interval='1m', start_date=D(2024,1,1), end_date=D(2024,3,31))
run('SPY 1m utp_cta 1-month range 2024-01-01..01-31', c.stock_history_ohlc, show=False, symbol='SPY', interval='1m', start_date=D(2024,1,1), end_date=D(2024,1,31), venue='utp_cta')
# calendar: early closes 2017-2026
rows=[]
for y in range(2017, 2027):
    df = run(f'calendar {y}', c.calendar_year, show=False, year=str(y))
    if df is not None: rows.append(df)
cal = pd.concat(rows); cal.to_csv(os.environ['CAL_OUT'], index=False); print(cal[cal['type']!='full_close'].to_string())
# SPXW quote request timing, full afternoon
run('SPXW 2025-06-02 P5935 13:00-16:00 1m', c.option_history_quote, show=False, symbol='SPXW', expiration=D(2025,6,2), interval='1m', date=D(2025,6,2), strike='5935', right='put', start_time='13:00:00', end_time='16:00:00')
run('SPXW 2025-06-02 P5935 full day 1m', c.option_history_quote, show=False, symbol='SPXW', expiration=D(2025,6,2), interval='1m', date=D(2025,6,2), strike='5935', right='put')
run('SPXW 2025-06-02 P5937 (nonexistent)', c.option_history_quote, show=False, symbol='SPXW', expiration=D(2025,6,2), interval='1m', date=D(2025,6,2), strike='5937', right='put')
