"""What does a 1-minute ThetaData quote row represent?  Compare the 1m row at T with the 1s rows around T.
Key: THETADATA_KEY from the environment (never printed).  Output: verify_interval.json (sanitized) + stdout."""
import os, re, json, sys, datetime as dt
import pandas as pd
from thetadata import ThetaClient
HERE = os.path.dirname(os.path.abspath(__file__))
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s))
c = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='pandas')
out = []
cases = [('SPY', dt.date(2026, 3, 2), '682', 'call', '13:00:00'), ('SPY', dt.date(2025, 9, 29), '663', 'put', '13:00:00'),
         ('QQQ', dt.date(2026, 5, 27), None, 'call', '15:55:00'), ('IWM', dt.date(2025, 9, 29), None, 'put', '14:30:00')]
import csv
rows = [r for r in csv.DictReader(open('/home/user/georgeredo/research/short_vol_session/csv/t1_straddles.csv')) if r['variant'] == 'short_hold']
def strike_for(tk, d, t):
    for r in rows:
        if r['ticker'] == tk and r['date'] == d.isoformat() and r['time'] == t: return str(int(float(r['strike'])))
for tk, d, K, right, T in cases:
    if K is None: K = strike_for(tk, d, '13:00')
    try:
        t0 = (dt.datetime.combine(d, dt.time.fromisoformat(T)) - dt.timedelta(minutes=2)).time().isoformat()
        t1 = (dt.datetime.combine(d, dt.time.fromisoformat(T)) + dt.timedelta(minutes=1)).time().isoformat()
        m = c.option_history_quote(symbol=tk, expiration=d, interval='1m', date=d, strike=K, right=right, start_time=t0, end_time=t1)
        s = c.option_history_quote(symbol=tk, expiration=d, interval='1s', date=d, strike=K, right=right, start_time=t0, end_time=t1)
        m['ts'] = m['timestamp'].dt.strftime('%H:%M:%S'); s['ts'] = s['timestamp'].dt.strftime('%H:%M:%S')
        mrow = m[m['ts'] == T].iloc[0]
        srow = s[s['ts'] == T].iloc[0]
        Tm1 = (dt.datetime.combine(d, dt.time.fromisoformat(T)) - dt.timedelta(seconds=1)).time().isoformat()
        prev = s[s['ts'] == Tm1].iloc[0]
        # last distinct quote change before T within the 1s stream
        before = s[s['ts'] < T]
        # 1s rows within the minute starting at T
        Tend = (dt.datetime.combine(d, dt.time.fromisoformat(T)) + dt.timedelta(seconds=59)).time().isoformat()
        win = s[(s['ts'] >= T) & (s['ts'] <= Tend)]
        rec = dict(symbol=tk, date=d.isoformat(), strike=K, right=right, T=T,
                   m1=dict(bid=float(mrow['bid']), ask=float(mrow['ask']), bid_size=int(mrow['bid_size']), ask_size=int(mrow['ask_size'])),
                   s1_at_T=dict(bid=float(srow['bid']), ask=float(srow['ask']), bid_size=int(srow['bid_size']), ask_size=int(srow['ask_size'])),
                   s1_at_T_minus_1s=dict(bid=float(prev['bid']), ask=float(prev['ask']), bid_size=int(prev['bid_size']), ask_size=int(prev['ask_size'])),
                   s1_last_before_T=dict(bid=float(before.iloc[-1]['bid']), ask=float(before.iloc[-1]['ask'])) if len(before) else None,
                   s1_minute_window=dict(bid_min=float(win['bid'].min()), bid_max=float(win['bid'].max()), ask_min=float(win['ask'].min()), ask_max=float(win['ask'].max()),
                                          first=dict(bid=float(win.iloc[0]['bid']), ask=float(win.iloc[0]['ask'])), last=dict(bid=float(win.iloc[-1]['bid']), ask=float(win.iloc[-1]['ask']))),
                   n_1s_rows=int(len(s)), n_1m_rows=int(len(m)))
        rec['match_1m_eq_1s_at_T'] = rec['m1']['bid'] == rec['s1_at_T']['bid'] and rec['m1']['ask'] == rec['s1_at_T']['ask'] and rec['m1']['bid_size'] == rec['s1_at_T']['bid_size'] and rec['m1']['ask_size'] == rec['s1_at_T']['ask_size']
        rec['match_1m_eq_1s_T_minus_1s'] = rec['m1']['bid'] == rec['s1_at_T_minus_1s']['bid'] and rec['m1']['ask'] == rec['s1_at_T_minus_1s']['ask'] and rec['m1']['bid_size'] == rec['s1_at_T_minus_1s']['bid_size']
        rec['match_1m_eq_last_of_minute_window'] = rec['m1']['bid'] == rec['s1_minute_window']['last']['bid'] and rec['m1']['ask'] == rec['s1_minute_window']['last']['ask']
    except Exception as e:
        rec = dict(symbol=tk, date=d.isoformat(), strike=K, right=right, T=T, error=red(f'{type(e).__name__}: {e}')[:300])
    out.append(rec); print(json.dumps(rec), flush=True)
# stock OHLC timestamp semantics: 1m row at 13:00:00 vs 1s rows
try:
    d = dt.date(2026, 3, 2)
    m = c.stock_history_ohlc(symbol='SPY', interval='1m', date=d, start_time='12:58:00', end_time='13:02:00')
    s = c.stock_history_ohlc(symbol='SPY', interval='1s', date=d, start_time='12:58:00', end_time='13:02:00')
    m['ts'] = m['timestamp'].dt.strftime('%H:%M:%S'); s['ts'] = s['timestamp'].dt.strftime('%H:%M:%S')
    mrow = m[m['ts'] == '13:00:00'].iloc[0]
    fwd = s[(s['ts'] >= '13:00:00') & (s['ts'] < '13:01:00')]; bwd = s[(s['ts'] > '12:59:00') & (s['ts'] <= '13:00:00')]
    rec = dict(check='stock_ohlc_1m_vs_1s', m1=dict(open=float(mrow['open']), high=float(mrow['high']), low=float(mrow['low']), close=float(mrow['close']), volume=int(mrow['volume'])),
               fwd_window=dict(open=float(fwd.iloc[0]['open']), high=float(fwd['high'].max()), low=float(fwd['low'].min()), close=float(fwd.iloc[-1]['close']), volume=int(fwd['volume'].sum())),
               bwd_window=dict(open=float(bwd.iloc[0]['open']), high=float(bwd['high'].max()), low=float(bwd['low'].min()), close=float(bwd.iloc[-1]['close']), volume=int(bwd['volume'].sum())),
               m_first_ts=str(m['ts'].iloc[0]), m_rows=int(len(m)))
except Exception as e:
    rec = dict(check='stock_ohlc_1m_vs_1s', error=red(f'{type(e).__name__}: {e}')[:300])
out.append(rec); print(json.dumps(rec), flush=True)
json.dump(out, open(HERE + '/verify_interval.json', 'w'), indent=1)
