"""S11 data pull (amendment A4): for a year-stratified subsample of S07 20-day-breakout events and S08 top-tercile beats,
the end-of-day NBBO of every strike of the nearest 30-45-calendar-day expiration from the event session to 25 sessions
later (one option_history_eod request per event), into $SP/theta/fetch_cache/eod_exp/{root}/{event_date}__{exp}.parquet
plus the event list $SP/theta/fetch_cache/s11_events.parquet. The stock EOD job must be paused (one login per key).
Usage: python3 s11_pull_event_chains.py [n_per_group_per_year]"""
import datetime as dt, gzip, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import calendar as cal
from engine.data.theta_fetch import ThetaFetcher
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(SP, 'theta', 'fetch_cache')
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
# events
import importlib.util
spec = importlib.util.spec_from_file_location('ds', os.path.join(HERE, '..', 'engine', 'daily_screen.py'))
from engine import daily_screen as ds
lake = f'{SP}/lake/stock_eod'
df = ds.load_lake(lake, [2023, 2024, 2025, 2026]); elig = ds.universe(df); f = ds.features(df).with_columns(pl.col('date').dt.year().alias('year'))
f = f.join(elig, on=['symbol', 'year'], how='semi').filter(pl.col('i') >= 200)
d = ds.trigger_direction(f, 'breakout20'); idx = np.flatnonzero(d != 0)
brk = f[idx].with_columns(pl.Series('direction', d[idx])).select(['symbol', 'date', 'year', 'direction', 'close']).with_columns(pl.lit('breakout20').alias('group'))
s08 = pl.read_parquet(os.path.join(HERE, '..', 'results', 'v1', 's08_earnings_daily', 'events.parquet'))
beats = s08.filter(pl.col('tercile') == 3).select(['symbol', 'date', 'year']).with_columns(pl.lit(1).alias('direction'), pl.lit(None).cast(pl.Float64).alias('close'), pl.lit('beat_top_tercile').alias('group'))
beats = beats.join(f.select(['symbol', 'date', 'close']), on=['symbol', 'date'], how='left', suffix='_f').with_columns(pl.col('close_f').alias('close')).drop('close_f')
# pre-earnings group (A5.2): every quarterly report in the universe with a report time, regardless of surprise; the pull
# window for these starts 11 sessions before the event session so that the 10-session pre-event trade is priced
pre = s08.select(['symbol', 'date', 'year']).with_columns(pl.lit(1).alias('direction'), pl.lit(None).cast(pl.Float64).alias('close'), pl.lit('pre_earnings').alias('group'))
pre = pre.join(f.select(['symbol', 'date', 'close']), on=['symbol', 'date'], how='left', suffix='_f').with_columns(pl.col('close_f').alias('close')).drop('close_f')
ev = pl.concat([brk, beats, pre], how='diagonal_relaxed').filter(pl.col('date') <= dt.date(2026, 9, 1))  # need 25 sessions of marks after the event
# deterministic stratified subsample: N per group per year, ordered by a hash of (symbol, date)
import hashlib
ev = ev.with_columns(pl.struct(['symbol', 'date']).map_elements(lambda s: int(hashlib.sha256(f"{s['symbol']}|{s['date']}".encode()).hexdigest()[:8], 16), return_dtype=pl.Int64).alias('h'))
ev = ev.sort('h').group_by(['group', 'year'], maintain_order=True).head(N).sort(['group', 'date', 'symbol'])
log('events', ev.group_by(['group', 'year']).len().sort(['group', 'year']).to_dicts())
# expirations per root (point in time: listed expirations from the universe file)
exps = {}
with gzip.open(os.path.join(ROOT, 'data_lake', 'universe', 'expirations.jsonl.gz'), 'rt') as fh:
    roots = set(ev['symbol'].unique().to_list())
    for line in fh:
        r = json.loads(line)
        if r['root'] in roots: exps[r['root']] = [dt.date.fromisoformat(x) for x in r['expirations']]
def choose(sym, d):
    c = [e for e in exps.get(sym, []) if 30 <= (e - d).days <= 45]
    if not c: c = [e for e in exps.get(sym, []) if 25 <= (e - d).days <= 60]
    return min(c, key=lambda e: abs((e - d).days - 37)) if c else None
# matched control: a random session of the same symbol and year at least 15 sessions from any report date of that symbol
rd_all = s08.select(['symbol', 'date']).rename({'date': 'rd'})
near = set()
for r in rd_all.iter_rows(named=True):
    d = r['rd']
    for k in range(-15, 16):
        near.add((r['symbol'], d + dt.timedelta(days=k)))
sym_dates = f.select(['symbol', 'date', 'year']).filter(pl.col('date') <= dt.date(2026, 9, 1))
ctrl_rows = []
for r in ev.iter_rows(named=True):
    cand = sym_dates.filter((pl.col('symbol') == r['symbol']) & (pl.col('year') == r['year']))['date'].to_list()
    cand = [c for c in cand if (r['symbol'], c) not in near and abs((c - r['date']).days) > 15]
    if not cand: continue
    seed = int(hashlib.sha256(f"ctrl|{r['symbol']}|{r['date']}".encode()).hexdigest()[:8], 16)
    c = cand[seed % len(cand)]
    ctrl_rows.append({'symbol': r['symbol'], 'date': c, 'year': r['year'], 'direction': r['direction'], 'close': None, 'group': r['group'] + '_control', 'h': r['h'], 'event_date': r['date']})
ctrl = pl.DataFrame(ctrl_rows, infer_schema_length=None).join(f.select(['symbol', 'date', 'close']), on=['symbol', 'date'], how='left', suffix='_f').with_columns(pl.col('close_f').alias('close')).drop('close_f')
ev = ev.with_columns(pl.col('date').alias('event_date'))
ev = pl.concat([ev, ctrl], how='diagonal_relaxed')
ev = ev.with_columns(pl.struct(['symbol', 'date']).map_elements(lambda s: choose(s['symbol'], s['date']), return_dtype=pl.Date).alias('expiration'))
ev = ev.filter(pl.col('expiration').is_not_null()).sort(['h', 'event_date', 'group'])  # event and its control adjacent
ev.write_parquet(os.path.join(CACHE, 's11_events.parquet'))
log('events with an expiration', ev.height, 'roots', ev['symbol'].n_unique())
if os.environ.get('S11_DRY'): log('dry run: events written, no pull'); sys.exit(0)
fch = ThetaFetcher(CACHE, nw=int(os.environ.get('S11_NW', '6')), log=log)
def eod_exp(root, d, exp, group='breakout20'):
    group = group.replace('_control', '')
    p = fch._p('eod_exp', root, d, exp)
    if fch._done(p): fch.stats['skipped'] += 1; return p
    start = d
    if group == 'pre_earnings':
        for _ in range(11): start = cal.prev_session(start, 1)
    end = cal.next_session(d)
    for _ in range(25): end = cal.next_session(end)
    end = min(end, exp)
    df, err = fch.call('option_history_eod', symbol=root, expiration=exp, start_date=start, end_date=end)
    return fch._finish(df, err, p, None)
fch.eod_exp = eod_exp
jobs = [('eod_exp', r['symbol'], r['date'], r['expiration'], r['group']) for r in ev.iter_rows(named=True)]
fch.run_jobs(jobs, 'S11 event chains')
log('S11 PULL DONE', fch.stats)
