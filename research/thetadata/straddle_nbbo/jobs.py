"""Job list for the straddle NBBO re-test: the session list, tickers, entry times and ATM strikes come from the
modelled-spread study (research/short_vol_session/csv/t1_straddles.csv, variant short_hold), de-duplicated on (time, ticker, date)
(that file holds 20 byte-identical duplicate rows).  The random-time baseline draws one RTH minute per (ticker, date) with seed 11."""
import csv, random, datetime as dt, collections
import pandas as pd
T1 = '/home/user/georgeredo/research/short_vol_session/csv/t1_straddles.csv'
TICKERS = ['SPY', 'QQQ', 'IWM']
TIMES = ['09:35', '10:00', '11:00', '13:00', '14:30']
START, END = '2025-06-02', '2026-10-09'

def okey(tk, d, strike): return f'{tk}_{d}_{int(strike)}_both_{d}_1m'
def skey(tk, d): return f'STK_{tk}_{d}_1m'

def load_t1():
    """{(time, ticker, date): row} for the short_hold rows at the fixed entry times (first row wins for duplicates; duplicates are identical)."""
    out = {}
    for r in csv.DictReader(open(T1)):
        if r['variant'] != 'short_hold' or r['time'] not in TIMES: continue
        k = (r['time'], r['ticker'], r['date'])
        if k not in out: out[k] = r
    return out

def sessions():
    return sorted({d for (_, _, d) in load_t1()})

def random_minutes(seed=11):
    """One uniformly random RTH entry minute per (ticker, date) in [09:31, 15:54] (entry must precede the 15:55 exit). Sorted iteration, fixed seed."""
    rng = random.Random(seed); out = {}
    for d in sessions():
        for tk in TICKERS:
            out[(tk, d)] = rng.randrange(9 * 60 + 31, 15 * 60 + 55)
    return out

def mstr(m): return f'{m // 60:02d}:{m % 60:02d}'

def random_strike(stock_df, T):
    """ATM strike at minute T = round(close of the 1-minute bar that ENDS at T, i.e. the row stamped T-1 which covers [T-1, T)).
    Mirrors the modelled study (close of the last bar starting before T)."""
    if stock_df is None or len(stock_df) == 0: return None
    ts = pd.to_datetime(stock_df['timestamp'], utc=True).dt.tz_convert('America/New_York')
    mins = ts.dt.hour * 60 + ts.dt.minute
    prior = stock_df[(mins < T) & stock_df['close'].notna()]
    if len(prior) == 0: return None
    return int(round(float(prior.iloc[-1]['close'])))

def jobs_for_phase(ph):
    t1 = load_t1()
    if ph in TIMES:
        return [('opt', tk, d, int(float(r['strike']))) for (t, tk, d), r in sorted(t1.items()) if t == ph]
    if ph == 'stock':
        return [('stock', tk, d) for d in sessions() for tk in TICKERS]
    if ph == 'random':
        rm = random_minutes()
        return [('random', tk, d, T) for (tk, d), T in sorted(rm.items())]
    raise SystemExit('unknown phase ' + ph)
