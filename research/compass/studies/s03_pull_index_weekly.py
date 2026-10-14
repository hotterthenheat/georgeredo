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
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
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
    # deterministic, point-in-time choice: the nearest Friday expiration in the weekly category (1-7 calendar days),
    # else the nearest weekly candidate. (An earlier version chose the most-open-interest candidate, which cost one OI
    # request per candidate per session - about 3.7 per session - before any chain could be pulled.)
    with open(choice_path, 'a') as fh:
        for d, c in cands.items():
            if (sym, str(d)) in chosen: continue
            fri = [e for e in c if e.weekday() == 4]
            best = min(fri) if fri else min(c)
            chosen[(sym, str(d))] = str(best); fh.write(json.dumps({'root': sym, 'session': str(d), 'expiration': str(best), 'rule': 'nearest_friday', 'candidates': [str(x) for x in c]}) + '\n')
    if os.environ.get('S03_OI', '1') != '0':  # S03_OI=0 skips the OI phase (the study applies the OI filter only where OI is cached)
        jobs = [('open_interest', sym, d, dt.date.fromisoformat(chosen[(sym, str(d))])) for d in cands]
        f.run_jobs(jobs, f'{sym} OI (chosen expiration)')
    jobs = []
    for d in cands:
        e = dt.date.fromisoformat(chosen[(sym, str(d))])
        jobs += [('chain_quotes', sym, d, e), ('chain_ohlc', sym, d, e)]
    f.run_jobs(jobs, f'{sym} chains+ohlc')
log('S03 PULL DONE', f.stats)
