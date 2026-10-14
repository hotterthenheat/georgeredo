"""Study S09: the owner's baseline (Quick Scalps) on SPXW same-day expirations, 2022-05-13 -> 2026-10-09, with the signal
computed on SPX index minute values (open/close) and SPY minute volume as the volume proxy (engine.store.IndexProxyStore);
fills at the SPXW 1-minute NBBO. Usage: python3 s09_spxw_0dte_baseline.py [out_dir]"""
import datetime as dt, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from engine import store, run, report, registry
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'v1', 's09_spxw_0dte_baseline')
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
st = store.IndexProxyStore(f'{SP}/theta/data/underlying', f'{SP}/theta/data_full/chains', f'{SP}/theta/data/index', f'{SP}/universe/expirations.jsonl')
t0 = time.time()
s = run.run_family(st, 'quick_scalps', ['SPXW'], dt.date(2022, 5, 13), dt.date(2026, 10, 9), OUT, select_params={'min_oi': None, 'min_volume': None}, log=log)
log('done', f'{time.time() - t0:.0f}s', {k: s.get(k) for k in ('signals', 'filled', 'status_counts')}, s.get('all', {}).get('mean'), s.get('all', {}).get('ci_lo'), s.get('all', {}).get('ci_hi'))
report.write(OUT, 'S09 — owner baseline (Quick Scalps) on SPXW same-day expirations, SPX signal with SPY volume proxy, 2022-05-13 → 2026-10-09', f'{SP}/theta/data/index')
log('S09 DONE')
