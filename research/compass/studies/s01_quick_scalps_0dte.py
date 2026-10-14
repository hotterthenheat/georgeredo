"""Study S01: Quick Scalps baseline (the owner's parameters) on index ETFs with same-day expirations, full 0DTE history
from the cached full-strike chains (SPY/QQQ from 2022-11-11, IWM from 2024-04-19, to 2026-10-09). No OI/volume filters
yet (open interest and intraday option volume are not in the chain cache; pulled in a later pass and reported as an
ablation). Usage: python3 s01_quick_scalps_0dte.py [out_dir]"""
import datetime as dt, os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from engine import store, run
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'v1', 's01_quick_scalps_0dte_baseline')
st = store.CacheStore(f'{SP}/theta/data/underlying', f'{SP}/theta/data_full/chains', f'{SP}/theta/data/index', f'{SP}/universe/expirations.jsonl')
summ = run.run_family(st, 'quick_scalps', ['SPY', 'QQQ', 'IWM'], dt.date(2022, 11, 11), dt.date(2026, 10, 9), OUT,
                      select_params={'min_oi': None, 'min_volume': None}, log=lambda *a: print(*a, flush=True))
print(json.dumps({k: summ[k] for k in summ if k in ('signals', 'status_counts', 'filled', 'all', 'baseline_pooled', 'strategy_minus_baseline')}, indent=1, default=str))
