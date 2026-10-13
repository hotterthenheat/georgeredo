import os, re, json, time, datetime as dt, traceback
import thetadata
from thetadata.errors import NoDataFoundError
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+','REDACTED',str(s))
c = thetadata.ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='pandas')
D = dt.date
def run(name, fn, **kw):
    t0=time.time()
    try:
        df = fn(**kw)
        n = len(df); cols=list(df.columns)
        print(f"OK  {name}: rows={n} cols={cols[:14]} ms={int((time.time()-t0)*1000)}")
        print(df.head(4).to_string()); print('  ...'); print(df.tail(3).to_string())
        return df
    except NoDataFoundError as e:
        print(f"NODATA {name}: {red(e)[:200]}")
    except Exception as e:
        print(f"ERR {name}: {red(type(e).__name__+': '+str(e))[:400]}")
run('index_list_dates SPX', c.index_list_dates, symbol='SPX')
run('calendar_year 2017', c.calendar_year, year='2017')
run('calendar_on_date 2017-07-04', c.calendar_on_date, date=D(2017,7,4))
run('index_history_price SPX 1m range 2017-06-01..06-07', c.index_history_price, symbol='SPX', interval='1m', start_date=D(2017,6,1), end_date=D(2017,6,7))
run('index_at_time_price SPX 15:30 2017-06-01..06-30', c.index_at_time_price, symbol='SPX', start_date=D(2017,6,1), end_date=D(2017,6,30), time_of_day='15:30:00')
run('stock_history_ohlc SPY 1m range 2017-06-01..06-02', c.stock_history_ohlc, symbol='SPY', interval='1m', start_date=D(2017,6,1), end_date=D(2017,6,2))
run('stock_at_time_trade SPY 15:30 2017-06-01..06-30', c.stock_at_time_trade, symbol='SPY', start_date=D(2017,6,1), end_date=D(2017,6,30), time_of_day='15:30:00')
run('option_list_strikes SPXW 2025-06-02', c.option_list_strikes, symbol='SPXW', expiration=D(2025,6,2))
run('index_history_price SPX 1m holiday 2017-07-04', c.index_history_price, symbol='SPX', interval='1m', date=D(2017,7,4))
run('index_history_price SPX 1m halfday 2025-07-03', c.index_history_price, symbol='SPX', interval='1m', date=D(2025,7,3))
run('index_history_price VIX 1m 2017-06-01', c.index_history_price, symbol='VIX', interval='1m', date=D(2017,6,1))
