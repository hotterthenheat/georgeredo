"""Study S06: entry-trigger screen on the underlying (engine.screen) for a symbol list, 2017-06-01 -> 2026-10-09 (or the
symbol's available range). Usage: python3 s06_signal_screen.py <out_name> [symbols,comma | tierA] [start] [end]"""
import datetime as dt, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import polars as pl
from engine import bars, screen
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
name = sys.argv[1] if len(sys.argv) > 1 else 's06_signal_screen_index'
arg = sys.argv[2] if len(sys.argv) > 2 else 'SPY,QQQ,IWM'
start = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date(2017, 6, 1)
end = dt.date.fromisoformat(sys.argv[4]) if len(sys.argv) > 4 else dt.date(2026, 10, 9)
if arg == 'tierA':
    tiers = pl.read_parquet(os.path.join(ROOT, 'data_lake', 'universe', 'tiers.parquet'))
    syms = tiers.filter(pl.col('tier') == 'A').sort(['year', 'rank']).select('symbol').unique(maintain_order=True)['symbol'].to_list()
else: syms = arg.split(',')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'v1', name)
def loader(sym):
    for root in (f'{SP}/theta/data/underlying', f'{SP}/theta/fetch_cache/underlying'):
        if os.path.isdir(os.path.join(root, sym)):
            df = bars.load_minutes(sym, root, start, end)
            if df.height: return df
    return None
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
tab = screen.run(syms, loader, OUT, log=log)
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_width_chars(220)
cols = ['symbol', 'trigger', 'filters', 'n', 'fwd_30m_bp', 'random_30m_bp', 'vs_random_30m_bp', 'vs_random_30m_lo', 'vs_random_30m_hi', 'vs_random_60m_bp', 'vs_random_60m_lo', 'hit_30m']
print(tab.select([c for c in cols if c in tab.columns]).with_columns([pl.col(c).round(2) for c in cols[4:] if c in tab.columns]))
