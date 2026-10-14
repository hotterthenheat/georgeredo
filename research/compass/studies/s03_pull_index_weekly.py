"""S03 data pull: for SPY/QQQ/IWM and every session 2017-06-01 -> 2026-10-09, the Weekly-category expiration (1-7
calendar days to its last trading day), chosen by the most open interest among the listed candidates (open interest is
pulled for every candidate first), then that expiration's full 1-minute NBBO chain and 1-minute option OHLC. Writes to
$SP/theta/fetch_cache/{oi,chains_exp,ohlc_exp}/. The stock EOD job must be paused (one login per key).
Usage: python3 s03_pull_index_weekly.py [symbols,comma] [start] [end]"""
import datetime as dt, gzip, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from engine import calendar as cal
from engine.data.theta_fetch import ThetaFetcher
import polars as pl
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
CACHE = os.path.join(SP, 'theta', 'fetch_cache')
syms = (sys.argv[1] if len(sys.argv) > 1 else 'SPY,QQQ,IWM').split(',')
start = dt.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else dt.date(2017, 6, 1)
end = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date(2026, 10, 9)
exps = {}
for line in open(os.path.join(SP, 'universe', 'expirations.jsonl')):
    r = json.loads(line)
    if r['root'] in syms: exps[r['root']] = [dt.date.fromisoformat(x) for x in r['expirations']]
log = lambda *a: print(dt.datetime.utcnow().strftime('%H:%M:%S'), *a, flush=True)
f = ThetaFetcher(CACHE, nw=8, log=log)
choice_path = os.path.join(CACHE, 'weekly_choice.jsonl')
chosen = {}
if os.path.exists(choice_path):
    for line in open(choice_path):
        r = json.loads(line); chosen[(r['root'], r['session'])] = r['expiration']
for sym in syms:
    sessions = cal.sessions(start, end)
    cands = {}
    for d in sessions:
        c = [e for e in exps[sym] if cal.expiry_category(d, cal.last_trading_day(e, cal.is_spx_am_settled(sym, e))) == 'weekly']
        if c: cands[d] = c
    log(sym, 'sessions', len(sessions), 'with weekly candidates', len(cands), 'candidate expirations', sum(len(v) for v in cands.values()))
    jobs = [('open_interest', sym, d, e) for d, c in cands.items() if (sym, str(d)) not in chosen for e in c]
    f.run_jobs(jobs, f'{sym} OI')
    with open(choice_path, 'a') as fh:
        for d, c in cands.items():
            if (sym, str(d)) in chosen: continue
            best, best_oi = None, -1
            for e in c:
                p = os.path.join(CACHE, 'oi', sym, f'{d}__{e}.parquet')
                oi = int(pl.read_parquet(p)['open_interest'].sum()) if os.path.exists(p) else 0
                if oi > best_oi: best, best_oi = e, oi
            if best is None: best = min(c)
            chosen[(sym, str(d))] = str(best); fh.write(json.dumps({'root': sym, 'session': str(d), 'expiration': str(best), 'oi': best_oi, 'candidates': [str(x) for x in c]}) + '\n')
    jobs = []
    for d in cands:
        e = dt.date.fromisoformat(chosen[(sym, str(d))])
        jobs += [('chain_quotes', sym, d, e), ('chain_ohlc', sym, d, e)]
    f.run_jobs(jobs, f'{sym} chains+ohlc')
log('S03 PULL DONE', f.stats)
