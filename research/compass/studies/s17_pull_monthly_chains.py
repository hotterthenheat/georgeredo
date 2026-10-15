"""S17 data pull (amendment A7): option end-of-day NBBO for every strike of each SPY/QQQ standard monthly expiration from
the previous monthly's last trading day (the roll date) to its own last trading day, 2012-06 -> 2026-10.
Writes $SP/theta/fetch_cache/eod_monthly/{root}/{entry}__{exp}.parquet. The stock EOD job must be paused.
Usage: python3 s17_pull_monthly_chains.py [roots]"""
import datetime as dt, gzip, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from engine import calendar as cal
from engine.data.theta_fetch import ThetaFetcher
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CACHE = os.path.join(SP, 'theta', 'fetch_cache')
roots = (sys.argv[1] if len(sys.argv) > 1 else 'SPY,QQQ').split(',')
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
def monthlies(root):
    with gzip.open(os.path.join(ROOT, 'data_lake', 'universe', 'expirations.jsonl.gz'), 'rt') as fh:
        for line in fh:
            r = json.loads(line)
            if r['root'] == root:
                e = [dt.date.fromisoformat(x) for x in r['expirations']]
                return sorted(x for x in e if ((x.weekday() == 4 and 15 <= x.day <= 21) or (x.weekday() == 5 and 16 <= x.day <= 22)) and dt.date(2012, 6, 1) <= x <= dt.date(2026, 10, 16))
def ltd(exp):  # last trading day: Saturday expirations trade through Friday; holiday Fridays move to Thursday
    d = exp - dt.timedelta(days=1) if exp.weekday() == 5 else exp
    while not cal.is_session(d): d -= dt.timedelta(days=1)
    return d
f = ThetaFetcher(CACHE, nw=int(os.environ.get('S17_NW', '4')), log=log)
def eod_cycle(root, entry, exp):
    # two single-day requests (the roll date and the last trading day): a month-long request for a large chain hangs
    p = f._p('eod_monthly', root, entry, exp)
    if f._done(p): f.stats['skipped'] += 1; return p
    import polars as pl
    frames = []
    for d in (entry, ltd(exp)):
        df, err = f.call('option_history_eod', symbol=root, expiration=exp, start_date=d, end_date=d)
        if df is None or not df.height: return f._finish(None, err or 'nodata', p, None)
        frames.append(df)
    return f._finish(pl.concat(frames, how='diagonal_relaxed'), None, p, None)
f.eod_cycle = eod_cycle
jobs = []
LIMIT = int(os.environ.get('S17_LIMIT', '0'))
for root in roots:
    m = monthlies(root)
    for a, b in zip(m[:-1], m[1:]): jobs.append(('eod_cycle', root, ltd(a), b))
jobs = jobs[-LIMIT:] if LIMIT else jobs
log('cycles', len(jobs))
f.run_jobs(jobs, 'S17 monthly chains')
log('S17 PULL DONE', f.stats)
