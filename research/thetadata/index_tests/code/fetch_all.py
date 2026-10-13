"""Single ThetaData session (the server allows one login per key): T-C per-session tasks first, then T-B monthly ranges; two worker threads sharing one client."""
import os, sys, csv, datetime as dt, time, concurrent.futures, threading
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import td_cache as td
D = dt.date
OUT = os.environ['TC_OUT']; os.makedirs(OUT, exist_ok=True)
cal = pd.read_csv(os.environ['CAL_FILE']); early = set(cal.loc[cal['type'] == 'early_close', 'date'])
rows = [r for r in csv.DictReader(open('/home/user/georgeredo/research/short_vol_session/csv/t1_straddles.csv')) if r['ticker'] == 'SPY' and r['time'] == '13:00' and r['variant'] == 'short_hold']
dates = [d for d in sorted(set(r['date'] for r in rows)) if d not in early]
print('T-C sessions', len(dates), dates[0], dates[-1], flush=True)
rng = np.random.default_rng(11); draws = []
for k in range(5):
    for d in dates: draws.append(dict(draw=k + 1, date=d, minute=int(rng.integers(9 * 60 + 35, 14 * 60 + 30 + 1))))
pd.DataFrame(draws).to_csv(os.path.join(OUT, 'random_baseline_minutes.csv'), index=False)
by_date = {}
for r in draws: by_date.setdefault(r['date'], []).append(r)
def px_at(spx, hhmm):
    s = spx[spx['timestamp'].str.slice(11, 16) == hhmm]
    return float(s['price'].iloc[0]) if len(s) and pd.notna(s['price'].iloc[0]) else None
def nearest(strikes, x, step=5):
    k = round(x / step) * step
    if k in strikes: return float(k), False
    return float(min(strikes, key=lambda s: (abs(s - x), s))), True
log = []; llock = threading.Lock(); t0 = time.time()
def tc_task(d):
    dd = D.fromisoformat(d)
    spx = td.fetch('index_history_price', symbol='SPX', interval='1m', date=dd)
    st = td.fetch('option_list_strikes', symbol='SPXW', expiration=dd)
    strikes = set(float(x) for x in st['strike']) if len(st) else set()
    need = {}; p13 = px_at(spx, '13:00')
    if p13 is not None and strikes: k, fb = nearest(strikes, p13); need[('13:00', 0)] = (p13, k, fb)
    for r in by_date[d]:
        hhmm = f"{r['minute'] // 60:02d}:{r['minute'] % 60:02d}"; p = px_at(spx, hhmm)
        if p is not None and strikes: k, fb = nearest(strikes, p); need[(hhmm, r['draw'])] = (p, k, fb)
    out = []
    for (hhmm, draw), (p, k, fb) in need.items():
        n = {}
        for right in ('call', 'put'):
            q = td.fetch('option_history_quote', symbol='SPXW', expiration=dd, interval='1m', date=dd, strike=str(int(k)) if float(k).is_integer() else str(k), right=right); n[right] = len(q)
        out.append(dict(date=d, entry=hhmm, draw=draw, spx=p, strike=k, fallback=int(fb), call_rows=n['call'], put_rows=n['put']))
    return f'{d} spx13={p13} strikes={len(strikes)} legs={len(out)}', out
def tb_task(ab):
    a, b = ab; res = []
    for name, kw in [('index_history_price', dict(symbol='SPX', interval='1m', start_date=a, end_date=b)),
                     ('index_history_price', dict(symbol='VIX', interval='1m', start_date=a, end_date=b)),
                     ('index_history_eod', dict(symbol='SPX', start_date=a, end_date=b)),
                     ('stock_history_eod', dict(symbol='SPY', start_date=a, end_date=b)),
                     ('stock_history_ohlc', dict(symbol='SPY', interval='1m', start_date=a, end_date=b))]:
        df = td.fetch(name, **kw); res.append(f'{kw["symbol"]}:{name[:5]}={len(df)}')
    return f'{a}..{b} ' + ' '.join(res), []
tasks = [('tc', d) for d in dates] + [('tb', ab) for ab in td.month_ranges(D(2017, 6, 1), D(2026, 10, 9))]
def run(t):
    kind, arg = t
    for attempt in range(3):
        try:
            msg, out = tc_task(arg) if kind == 'tc' else tb_task(arg)
            with llock: log.extend(out)
            return f'OK {kind} {msg}'
        except Exception as e:
            err = td.red(e)[:200]; time.sleep(5)
    return f'FAIL {kind} {arg} {err}'
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
    for n, m in enumerate(ex.map(run, tasks)):
        print(f'{n+1}/{len(tasks)} {m} t={int(time.time()-t0)}s {td.STATS}', flush=True)
        if n % 25 == 0: pd.DataFrame(log).to_csv(os.path.join(OUT, 'fetch_log.csv'), index=False)
pd.DataFrame(log).to_csv(os.path.join(OUT, 'fetch_log.csv'), index=False)
print('DONE', td.STATS, flush=True)
