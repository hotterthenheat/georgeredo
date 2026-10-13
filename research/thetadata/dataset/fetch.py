"""0DTE research dataset builder (ThetaData PRO).  ONE login per process tree: the parent authenticates once; worker
processes reuse the session token via ThetaClient(existing_authorized_client=...) (no further logins).  <= NWORK requests in flight.
Usage: set -a; . "$SP/secrets/research.env"; set +a; python3 -I fetch.py [phase ...]   phases: underlying chains ohlc (default: all)
Env: THETA_DS_ROOT (default $SP/theta/data), THETA_DS_MAX_SECS (stop feeding new jobs after this many seconds), THETA_DS_NWORK (6),
     THETA_DS_LIMIT (debug: max sessions per symbol).  The key is read from THETADATA_KEY only and never printed; exception text is redacted."""
import os, re, sys, csv, time, json, glob, queue, random, logging, datetime as dt, multiprocessing as mp
logging.getLogger('thetadata').setLevel(logging.ERROR)
import polars as pl
import grpc
from thetadata import ThetaClient
from thetadata.errors import NoDataFoundError
from thetadata._proto.endpoints_pb2 import AuthToken

SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
ROOT = os.environ.get('THETA_DS_ROOT', SP + '/theta/data')
CAL = '/home/user/georgeredo/research/thetadata/index_tests/code/calendar_2017_2026.csv'
IDX_CACHE = SP + '/theta/cache/index_tests'
EXP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'expirations')
BAND = 0.02
NWORK = int(os.environ.get('THETA_DS_NWORK', '6'))
MAX_SECS = float(os.environ.get('THETA_DS_MAX_SECS', '13200'))
LIMIT = int(os.environ.get('THETA_DS_LIMIT', '0'))
U_START, U_END = dt.date(2017, 6, 1), dt.date(2026, 10, 9)
END = dt.date(2026, 10, 9)
FIRST_DAILY = {'SPY': '2022-11-11', 'QQQ': '2022-11-11', 'SPXW': '2022-05-13', 'IWM': '2024-04-19'}   # from first_daily.py (option_list_expirations)
UNDER = {'SPY': ('underlying', 'SPY'), 'QQQ': ('underlying', 'QQQ'), 'IWM': ('underlying', 'IWM'), 'SPXW': ('index', 'SPX')}
REQ_TIMEOUT = 420
RETRY = (grpc.StatusCode.RESOURCE_EXHAUSTED, grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.UNKNOWN, grpc.StatusCode.INTERNAL, grpc.StatusCode.ABORTED)

def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s))
def now(): return dt.datetime.now().strftime('%H:%M:%S')
def log(*a):
    print(now(), *[red(x) for x in a], flush=True)

def sessions(a, b):
    hol = {r['date'] for r in csv.DictReader(open(CAL)) if r['type'] == 'full_close'}
    d = a; out = []
    while d <= b:
        if d.weekday() < 5 and d.isoformat() not in hol: out.append(d.isoformat())
        d += dt.timedelta(days=1)
    return out

def month_ranges(start, end):
    out = []; d = start
    while d <= end:
        nxt = (d.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        out.append((d, min(nxt - dt.timedelta(days=1), end))); d = nxt
    return out

DIRNAME = {'chain': 'chains'}
def path(kind, sym, d): return os.path.join(ROOT, DIRNAME.get(kind, kind), sym, d + '.parquet')
def marker(kind, sym, d, what): return os.path.join(ROOT, DIRNAME.get(kind, kind), sym, d + '.' + what)
def done(kind, sym, d): return os.path.exists(path(kind, sym, d)) or os.path.exists(marker(kind, sym, d, 'nodata'))

def write_parquet(df, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp%d' % os.getpid()
    df.write_parquet(tmp, compression='zstd'); os.replace(tmp, p)

def norm_ts(df, col='timestamp'):
    """Datetime(ms, America/New_York); float NaN -> null for every float column."""
    df = df.with_columns(pl.col(col).dt.convert_time_zone('America/New_York').dt.cast_time_unit('ms'))
    fl = [c for c, t in zip(df.columns, df.dtypes) if t in (pl.Float64, pl.Float32)]
    if fl: df = df.with_columns([pl.col(c).fill_nan(None) for c in fl])
    return df

def ref_price(ukind, usym, d):
    """09:31 underlying print.  index: price stamped 09:31:00; stock: open of the bar stamped 09:31:00.  Fallback: first non-null at/after 09:31."""
    p = path(ukind, usym, d)
    if not os.path.exists(p): return None, None, 'no_underlying_file'
    u = pl.read_parquet(p)
    col = 'price' if ukind == 'index' else 'open'
    u = u.filter(pl.col('timestamp').dt.time() >= dt.time(9, 31)).filter(pl.col(col).is_not_null()).sort('timestamp')
    if u.height == 0: return None, None, 'no_underlying_price'
    t = u['timestamp'][0]
    return float(u[col][0]), t.strftime('%H:%M:%S'), ('ok' if t.time() == dt.time(9, 31) else 'fallback')

# ----------------------------------------------------------------------------------------------------------- worker
class _Auth: pass
def make_client(tok):
    a = _Auth(); a.auth_token = AuthToken(session_uuid=tok['sid']); a.email = tok['email']; a.api_key = None
    a.stock_subscription = tok['subs'][0]; a.options_subscription = tok['subs'][1]; a.index_subscription = tok['subs'][2]
    a.creds_file = None; a.mdds_type = tok['mdds_type']; a.mdds_host = tok['host']; a.mdds_port = tok['port']
    c = ThetaClient(existing_authorized_client=a, dataframe_type='polars')
    stub = c.stub
    class _Stub:
        def __getattr__(self, name):
            m = getattr(stub, name)
            return lambda request, **kw: m(request, timeout=REQ_TIMEOUT, **kw)
    c.stub = _Stub()
    return c

def fetch_raw(c, job):
    kind, sym, d = job['kind'], job['sym'], job['date']
    D = dt.date.fromisoformat(d)
    if kind == 'chain': return c.option_history_quote(symbol=sym, expiration=D, interval='1m', date=D, strike='*', right='both')
    if kind == 'ohlc': return c.option_history_ohlc(symbol=sym, expiration=D, interval='1m', date=D, strike='*', right='both')
    if kind == 'stock_month':
        a, b = dt.date.fromisoformat(job['a']), dt.date.fromisoformat(job['b'])
        return c.stock_history_ohlc(symbol=sym, interval='1m', start_date=a, end_date=b)
    if kind == 'stock_day': return c.stock_history_ohlc(symbol=sym, interval='1m', date=D)
    if kind == 'index_day': return c.index_history_price(symbol=sym, interval='1m', date=D)
    raise ValueError(kind)

CHAIN_COLS = ['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size', 'mid']
OHLC_COLS = ['timestamp', 'strike', 'right', 'open', 'high', 'low', 'close', 'volume', 'count', 'vwap']

def process(job, df):
    """Filter/shape the raw frame and write parquet; returns stats dict."""
    kind, sym, d = job['kind'], job['sym'], job['date']
    st = dict(raw_rows=df.height)
    if kind in ('chain', 'ohlc'):
        ukind, usym = UNDER[sym]
        ref, rt, rs = ref_price(ukind, usym, d)
        st.update(ref_price=ref, ref_time=rt, ref_status=rs)
        if ref is None: raise RuntimeError('no underlying reference price: ' + rs)
        lo, hi = ref * (1 - BAND) - 1e-9, ref * (1 + BAND) + 1e-9
        ks = df['strike'].unique()
        st.update(raw_strikes=len(ks), raw_kmin=float(ks.min()), raw_kmax=float(ks.max()), band_lo=round(lo, 4), band_hi=round(hi, 4))
        out = df.filter((pl.col('strike') >= lo) & (pl.col('strike') <= hi))
        if kind == 'chain':
            out = out.with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
            out = out.select(CHAIN_COLS).with_columns(pl.col('bid_size').cast(pl.Int32), pl.col('ask_size').cast(pl.Int32))
        else:
            out = out.select(OHLC_COLS).with_columns(pl.col('volume').cast(pl.Int64), pl.col('count').cast(pl.Int32))
        out = norm_ts(out).sort(['strike', 'right', 'timestamp'])
        kk = out['strike'].unique()
        st.update(rows=out.height, strikes=len(kk), kmin=(float(kk.min()) if len(kk) else None), kmax=(float(kk.max()) if len(kk) else None))
        write_parquet(out, path(kind, sym, d))
        return st
    if kind in ('stock_month', 'stock_day', 'index_day'):
        out = norm_ts(df.select(df.columns)).sort('timestamp')
        ukind = 'index' if kind == 'index_day' else 'underlying'
        n = 0; ses = set(sessions(U_START, U_END))
        for (day,), part in out.group_by([pl.col('timestamp').dt.date()], maintain_order=True):
            if day.isoformat() not in ses: continue           # the server pads holidays with all-null bars
            write_parquet(part, path(ukind, sym, day.isoformat())); n += 1
        st.update(rows=out.height, days=n)
        return st

def worker_main(wid, jobq, resq, shared):
    random.seed(wid)
    c = None; ctok = None
    while True:
        job = jobq.get()
        if job is None: break
        resq.put(('start', wid, job))
        t0 = time.time(); delay = 2.0; attempt = 0; result = None; codes = []
        while True:
            tok = shared['tok']
            if c is None or ctok != tok['sid']:
                try: c = make_client(tok); ctok = tok['sid']
                except Exception as e: result = ('err', wid, job, 'make_client: ' + red(e)[:300]); break
            try:
                df = fetch_raw(c, job)
                st = process(job, df); st['secs'] = round(time.time() - t0, 1); st['attempts'] = attempt + 1; st['retry_codes'] = codes
                result = ('ok', wid, job, st); break
            except NoDataFoundError:
                os.makedirs(os.path.dirname(path(job['kind'], job['sym'], job['date'])), exist_ok=True)
                open(marker(job['kind'], job['sym'], job['date'], 'nodata'), 'w').close()
                result = ('nodata', wid, job, dict(secs=round(time.time() - t0, 1))); break
            except grpc.RpcError as e:
                code = e.code() if hasattr(e, 'code') else None
                det = red(getattr(e, 'details', lambda: '')())
                if code == grpc.StatusCode.UNAUTHENTICATED or 'session' in det.lower() or 'auth' in det.lower():
                    result = ('unauth', wid, job, dict(gen=tok['gen'], code=str(code), det=det[:200])); break
                attempt += 1; codes.append(str(code).replace('StatusCode.', ''))
                if code in RETRY and attempt < 8:
                    time.sleep(delay + random.random()); delay = min(30.0, delay * 2); continue
                result = ('err', wid, job, f'{code}: {det[:300]}'); break
            except Exception as e:
                attempt += 1; codes.append(type(e).__name__)
                if attempt < 4: time.sleep(delay); delay = min(30.0, delay * 2); continue
                result = ('err', wid, job, red(f'{type(e).__name__}: {e}')[:300]); break
        resq.put(result)

# ----------------------------------------------------------------------------------------------------------- parent
def login():
    c = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars')
    return c, dict(sid=c.auth_token.session_uuid, email=c.email, subs=(c.stock_subscription, c.options_subscription, c.index_subscription),
                   mdds_type=c.mdds_type, host=c.mdds_host, port=c.mdds_port)

def convert_cache():
    """index_tests cache (monthly gzip CSV from the same client, pandas) -> per-date parquet for SPX, VIX (index) and SPY (underlying)."""
    spec = [('index', 'SPX', 'index_history_price__end_date={b}__interval=1m__start_date={a}__symbol=SPX.csv.gz'),
            ('index', 'VIX', 'index_history_price__end_date={b}__interval=1m__start_date={a}__symbol=VIX.csv.gz'),
            ('underlying', 'SPY', 'stock_history_ohlc__end_date={b}__interval=1m__start_date={a}__symbol=SPY.csv.gz')]
    n = 0; ses = set(sessions(U_START, U_END))
    for ukind, sym, pat in spec:
        for a, b in month_ranges(U_START, U_END):
            f = os.path.join(IDX_CACHE, pat.format(a=a.isoformat(), b=b.isoformat()))
            if not os.path.exists(f): log('cache missing', f); continue
            df = pl.read_csv(f, schema_overrides={'timestamp': pl.String})
            if df.height == 0: continue
            if all(done(ukind, sym, d) for d in {t[:10] for t in df['timestamp']} if d in ses): continue
            df = df.with_columns(pl.col('timestamp').str.to_datetime('%Y-%m-%d %H:%M:%S%z'))
            df = norm_ts(df).sort('timestamp')
            for (day,), part in df.group_by([pl.col('timestamp').dt.date()], maintain_order=True):
                if day.isoformat() not in ses: continue           # the cache pads holidays with all-null bars
                write_parquet(part, path(ukind, sym, day.isoformat())); n += 1
    log('convert_cache wrote', n, 'session files')

def build_jobs(phases):
    jobs = []
    ses_all = sessions(U_START, U_END)
    if 'underlying' in phases:
        for sym in ('QQQ', 'IWM'):
            for a, b in month_ranges(U_START, U_END):
                days = [d for d in ses_all if a.isoformat() <= d <= b.isoformat()]
                if days and not all(done('underlying', sym, d) for d in days):
                    jobs.append(dict(kind='stock_month', sym=sym, date=a.isoformat(), a=a.isoformat(), b=b.isoformat()))
        # gaps in the converted cache
        for ukind, sym in (('index', 'SPX'), ('index', 'VIX'), ('underlying', 'SPY')):
            miss = [d for d in ses_all if not done(ukind, sym, d)]
            for d in miss: jobs.append(dict(kind=('index_day' if ukind == 'index' else 'stock_day'), sym=sym, date=d))
            if miss: log('underlying gaps', sym, len(miss), miss[:5])
    for kind in ('chain', 'ohlc'):
        if kind + 's' not in phases and kind not in phases: continue
        for sym in ('SPY', 'QQQ', 'SPXW', 'IWM'):
            ses = sessions(dt.date.fromisoformat(FIRST_DAILY[sym]), END)
            if LIMIT: ses = ses[:LIMIT]
            jobs += [dict(kind=kind, sym=sym, date=d) for d in ses if not done(kind, sym, d)]
    return jobs

def main(phases):
    os.makedirs(ROOT, exist_ok=True)
    if 'underlying' in phases: convert_cache()
    jobs = build_jobs(phases)
    log('jobs to run', len(jobs), json.dumps({'/'.join(k): sum(1 for j in jobs if (j['kind'], j['sym']) == k) for k in sorted({(j['kind'], j['sym']) for j in jobs})}))
    if not jobs: return
    c, tok = login(); tok['gen'] = 1; log('login ok (gen 1)')
    ctx = mp.get_context('spawn'); mgr = ctx.Manager(); shared = mgr.dict(); shared['tok'] = tok
    jobq = ctx.Queue(); resq = ctx.Queue()
    workers = {}
    def spawn(wid):
        p = ctx.Process(target=worker_main, args=(wid, jobq, resq, shared), daemon=True); p.start(); workers[wid] = p
    for wid in range(NWORK): spawn(wid)
    pending = list(jobs); inflight = {}; t0 = time.time(); last_login = time.time()
    stats = {}; ndone = 0; jl = open(os.path.join(ROOT, '_jobs.jsonl'), 'a')
    def key(j): return f"{j['kind']}/{j['sym']}"
    def bump(j, s): stats.setdefault(key(j), dict(ok=0, nodata=0, err=0, unauth=0, secs=0.0)); stats[key(j)][s] += 1
    def progress(final=False):
        prog = dict(time=dt.datetime.now().isoformat(timespec='seconds'), elapsed_s=int(time.time() - t0), done=ndone, pending=len(pending), inflight=len(inflight), login_gen=shared['tok']['gen'], stats=stats, final=final)
        tmp = os.path.join(ROOT, 'progress.json.tmp'); json.dump(prog, open(tmp, 'w'), indent=1); os.replace(tmp, os.path.join(ROOT, 'progress.json'))
        log('PROGRESS', json.dumps(dict(done=ndone, pending=len(pending), inflight=len(inflight), elapsed=int(time.time() - t0), gen=shared['tok']['gen'])), json.dumps({k: f"{v['ok']}/{v['nodata']}/{v['err']}" for k, v in stats.items()}))
    def feed():
        while pending and jobq.qsize() < NWORK * 2 and (time.time() - t0) < MAX_SECS:
            jobq.put(pending.pop(0))
    feed(); stop_requested = False
    while True:
        if not inflight and jobq.empty() and (not pending or (time.time() - t0) >= MAX_SECS):
            if pending and not stop_requested: log('MAX_SECS reached; stopping with', len(pending), 'jobs pending'); stop_requested = True
            try: r = resq.get(timeout=5)          # a worker may have taken a job without posting 'start' yet
            except queue.Empty: break
        else:
          try:
            r = resq.get(timeout=REQ_TIMEOUT + 120)
          except queue.Empty:
            dead = [w for w, p in workers.items() if not p.is_alive()]
            log('result timeout; dead workers', dead, 'inflight', len(inflight))
            for w in dead:
                if w in inflight: pending.insert(0, inflight.pop(w))
                spawn(w)
            if not dead and inflight:
                log('workers alive but silent; waiting more'); continue
            feed(); continue
        kind = r[0]
        if kind == 'start':
            inflight[r[1]] = r[2]; continue
        _, wid, job, info = r
        inflight.pop(wid, None)
        if kind == 'unauth':
            bump(job, 'unauth')
            if info['gen'] == shared['tok']['gen']:
                wait = max(0.0, 20.0 - (time.time() - last_login))
                log('UNAUTHENTICATED (gen %d): %s; re-login in %.0fs' % (info['gen'], info['det'][:120], wait + 3)); time.sleep(wait + 3)
                try:
                    c, ntok = login(); ntok['gen'] = shared['tok']['gen'] + 1; shared['tok'] = ntok; last_login = time.time(); log('re-login ok (gen %d)' % ntok['gen'])
                except Exception as e:
                    log('re-login FAILED', red(e)[:200]); time.sleep(30)
            pending.insert(0, job); feed(); continue
        ndone += 1; bump(job, kind)
        rec = dict(kind=job['kind'], sym=job['sym'], date=job['date'], status=kind, wid=wid)
        if kind == 'ok':
            stats[key(job)]['secs'] += info.get('secs', 0); rec.update(info)
            log(kind, key(job), job['date'], f"rows={info.get('rows')} strikes={info.get('strikes')} [{info.get('kmin')}..{info.get('kmax')}] raw={info.get('raw_rows')}/{info.get('raw_strikes')} ref={info.get('ref_price')} {info.get('ref_status','')} {info.get('secs')}s {info.get('retry_codes') or ''}" if job['kind'] in ('chain', 'ohlc') else f"rows={info.get('rows')} days={info.get('days')} {info.get('secs')}s {info.get('retry_codes') or ''}")
        else:
            rec['info'] = info; log(kind.upper(), key(job), job['date'], red(info)[:300])
        jl.write(json.dumps(rec, default=str) + '\n'); jl.flush()
        if ndone % 100 == 0: progress()
        feed()
    progress(final=True)
    for _ in workers: jobq.put(None)
    for p in workers.values(): p.join(timeout=30)
    log('DONE', json.dumps(stats))

if __name__ == '__main__':
    main(sys.argv[1:] or ['underlying', 'chains', 'ohlc'])
