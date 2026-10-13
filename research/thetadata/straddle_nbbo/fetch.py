"""Fetch 1-minute option NBBO (call+put, full RTH day) and 1-minute stock OHLC from ThetaData for the straddle re-test.
Usage:  python3 -I fetch.py 13:00 [09:35 10:00 11:00 14:30 random]
Key: THETADATA_KEY from the environment only (never printed; exception text is redacted).
Cache: $THETA_CACHE (default <scratchpad>/theta/cache/straddle), one gzip CSV per (symbol, expiration, strike, right, date, interval);
       a key that returned NoDataFoundError is recorded as <key>.nodata and never refetched.
Concurrency: 2 worker threads, one ThetaClient per thread; gRPC RESOURCE_EXHAUSTED / UNAVAILABLE / DEADLINE_EXCEEDED -> back off 2..30 s, up to 8 tries."""
import os, re, sys, csv, json, time, gzip, io, random, threading, datetime as dt, concurrent.futures
import pandas as pd
import grpc
from thetadata import ThetaClient
from thetadata.errors import NoDataFoundError
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)   # python3 -I drops the script directory
import jobs as J

SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
CACHE = os.environ.get('THETA_CACHE', SP + '/theta/cache/straddle')
os.makedirs(CACHE, exist_ok=True)
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s))
def log(*a): print(dt.datetime.now().strftime('%H:%M:%S'), *[red(x) for x in a], flush=True)

import logging; logging.getLogger('thetadata').setLevel(logging.ERROR)   # the library logs the auth response at INFO
# ONE login per process: every ThetaClient() is a new terminal session and invalidates the previous one ("Invalid session ID").
# Other studies share this key, so a session can be invalidated from outside; on UNAUTHENTICATED we re-login (once, under a lock).
_C = dict(c=None, gen=0); _clock = threading.Lock()
def client():
    with _clock:
        if _C['c'] is None: _C['c'] = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='pandas'); _C['gen'] += 1
        return _C['c'], _C['gen']
def relogin(gen):
    with _clock:
        if _C['gen'] == gen:
            time.sleep(3); _C['c'] = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='pandas'); _C['gen'] += 1; log('re-login, generation', _C['gen'])

RETRY = (grpc.StatusCode.RESOURCE_EXHAUSTED, grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.UNKNOWN, grpc.StatusCode.INTERNAL)
STATS = dict(hit=0, fetched=0, nodata=0, error=0, retries=0, relogin=0); _lock = threading.Lock()

def _get(key, fn):
    """Return a DataFrame (possibly empty) for the cache key; fetch with fn() if not cached."""
    f = os.path.join(CACHE, key + '.csv.gz'); nd = os.path.join(CACHE, key + '.nodata')
    if os.path.exists(f):
        with _lock: STATS['hit'] += 1
        return pd.read_csv(f)
    if os.path.exists(nd):
        with _lock: STATS['hit'] += 1
        return pd.DataFrame()
    delay = 2.0
    for attempt in range(8):
        c, gen = client()
        try:
            df = fn(c)
            tmp = f + '.tmp.%d' % threading.get_ident()
            df.to_csv(tmp, index=False, compression='gzip'); os.replace(tmp, f)
            with _lock: STATS['fetched'] += 1
            return df
        except NoDataFoundError:
            open(nd, 'w').close()
            with _lock: STATS['nodata'] += 1
            return pd.DataFrame()
        except grpc.RpcError as e:
            code = e.code() if hasattr(e, 'code') else None
            if code == grpc.StatusCode.UNAUTHENTICATED and attempt < 7:
                with _lock: STATS['relogin'] += 1
                relogin(gen); continue
            if code in RETRY and attempt < 7:
                with _lock: STATS['retries'] += 1
                log('retry', key, str(code), 'sleep', delay); time.sleep(delay); delay = min(30.0, delay * 2); continue
            log('ERROR', key, red(f'{type(e).__name__}: {code}: {getattr(e, "details", lambda: "")()}')[:300])
            with _lock: STATS['error'] += 1
            return None
        except Exception as e:
            if attempt < 3:
                with _lock: STATS['retries'] += 1
                log('retry', key, red(f'{type(e).__name__}: {e}')[:200], 'sleep', delay); time.sleep(delay); delay = min(30.0, delay * 2); continue
            log('ERROR', key, red(f'{type(e).__name__}: {e}')[:300])
            with _lock: STATS['error'] += 1
            return None

def option_quotes(tk, d, strike):
    """Full-RTH 1-minute NBBO for both rights of one 0DTE contract pair.  d: 'YYYY-MM-DD'; strike: int."""
    key = J.okey(tk, d, strike)
    D = dt.date.fromisoformat(d)
    return _get(key, lambda c: c.option_history_quote(symbol=tk, expiration=D, interval='1m', date=D, strike=str(strike), right='both', start_time='09:30:00', end_time='16:00:00'))

def stock_ohlc(tk, d):
    key = J.skey(tk, d)
    D = dt.date.fromisoformat(d)
    return _get(key, lambda c: c.stock_history_ohlc(symbol=tk, interval='1m', date=D, start_time='09:30:00', end_time='16:00:00'))

def run_job(job):
    kind = job[0]
    try:
        if kind == 'opt': df = option_quotes(*job[1:]); return job, (None if df is None else len(df))
        if kind == 'stock': df = stock_ohlc(*job[1:]); return job, (None if df is None else len(df))
        if kind == 'random':
            _, tk, d, T = job
            s = stock_ohlc(tk, d)
            K = J.random_strike(s, T)
            if K is None: return job, 'no-underlying'
            df = option_quotes(tk, d, K); return job, (None if df is None else len(df))
    except Exception as e:
        log('JOB ERROR', job, red(f'{type(e).__name__}: {e}')[:300]); return job, None

def main(phases):
    client()   # single login up front
    for ph in phases:
        jobs = J.jobs_for_phase(ph)
        log('phase', ph, 'jobs', len(jobs))
        t0 = time.time(); done = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            for job, res in ex.map(run_job, jobs):
                done += 1
                if done % 50 == 0 or done == len(jobs):
                    log('phase', ph, done, '/', len(jobs), json.dumps(STATS), '%.0fs' % (time.time() - t0))
        log('phase', ph, 'DONE', json.dumps(STATS))
    json.dump(STATS, open(os.path.join(CACHE, '_stats_%s.json' % '_'.join(p.replace(':', '') for p in phases)), 'w'))

if __name__ == '__main__':
    main(sys.argv[1:] or ['13:00'])
