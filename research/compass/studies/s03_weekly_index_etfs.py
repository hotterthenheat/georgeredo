"""Study S03: the baseline rule on index ETFs with WEEKLY-category expirations (1-7 calendar days), 2017-06-01 →
2026-10-09, from the chains pulled by s03_pull_index_weekly.py (most-open-interest weekly expiration per session), with
open-interest and intraday-volume filters applied (OI and OHLC are in the pull). Holds up to 3 sessions; exits as the
Trend-Plays-style set with a 30 % premium stop. Usage: python3 s03_weekly_index_etfs.py [out_dir] [symbols]"""
import datetime as dt, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from engine import store, run
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'v1', 's03_weekly_index_etfs_baseline')
SYMS = sys.argv[2].split(',') if len(sys.argv) > 2 else ['SPY', 'QQQ', 'IWM']
CACHE = os.path.join(SP, 'theta', 'fetch_cache')

class WeeklyStore(store.FetchStore):
    """The weekly expiration per session is the one the pull chose (weekly_choice.jsonl); no fetching here."""
    def __init__(self):
        super().__init__(f'{SP}/theta/data/underlying', f'{SP}/theta/data_full/chains', f'{SP}/theta/data/index', f'{SP}/universe/expirations.jsonl', CACHE, fetcher=None)
        self.choice = {}
        p = os.path.join(CACHE, 'weekly_choice.jsonl')
        if os.path.exists(p):
            for line in open(p):
                r = json.loads(line); self.choice[(r['root'], r['session'])] = dt.date.fromisoformat(r['expiration'])
    def expirations(self, root):
        return sorted(set(self.choice[k] for k in self.choice if k[0] == root))
    def chain_minutes(self, root, session, expiration):
        return store.FetchStore.chain_minutes(self, root, session, expiration) if expiration != session else self._read_exp(root, session, expiration)
    def _read_exp(self, root, session, expiration):
        df = self._read('chains_exp', root, session, expiration, None)
        if df is None: return None
        import polars as pl
        return df.select(['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size']).with_columns(pl.col('timestamp').dt.replace_time_zone(None))

run.FAMILIES['weekly_index'] = dict(category='weekly', signal={'entry_start_minute': 15, 'entry_end_minute': 360}, exits={'max_hold_min': 3 * 390, 'session_cutoff_minute': 390, 'stop_pct': 0.30}, symbols_rule='index_products', warmup_sessions=30)

if __name__ == '__main__':
    st = WeeklyStore()
    # the runner picks the expiration by category among store.expirations(); restrict to the pull's choice for that session
    import polars as pl
    from engine import contracts
    orig = contracts.pick_expiration
    def pick(expirations, decision_date, category, root, oi_by_exp=None):
        e = st.choice.get((root, str(decision_date)))
        return e if e is not None else orig(expirations, decision_date, category, root, oi_by_exp)
    contracts.pick_expiration = pick
    cov = {}
    for sym in SYMS:
        sess = [k[1] for k in st.choice if k[0] == sym]
        have = lambda kind: sum(os.path.exists(os.path.join(CACHE, kind, sym, f"{d}__{st.choice[(sym, d)]}.parquet")) for d in sess)
        cov[sym] = {'sessions_chosen': len(sess), 'chains': have('chains_exp'), 'ohlc': have('ohlc_exp'), 'oi': have('oi')}
    print('data coverage per symbol (sessions with cached files):', json.dumps(cov), flush=True)
    summ = run.run_family(st, 'weekly_index', SYMS, dt.date(2017, 6, 1), dt.date(2026, 10, 9), OUT, select_params={'min_oi': 250, 'min_volume': 100}, log=lambda *a: print(*a, flush=True))
    summ['data_coverage'] = cov
    json.dump(summ, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: summ[k] for k in summ if k in ('signals', 'status_counts', 'filled', 'all', 'baseline_pooled', 'strategy_minus_baseline')}, indent=1, default=str))
