"""V8 (amendment A15): the month-end 13:00 long straddle on same-day chains no study here has read.
  python3 -I v8_monthend.py pull       # ThetaData: SPXW's expiration list, then each month-end's same-day chain
  python3 -I v8_monthend.py build      # trades.parquet + skipped.parquet
  python3 -I v8_monthend.py analyze
"""
import datetime as dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import numpy as np, polars as pl
from engine import calendar as cal, regime

SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
CACHE = os.path.join(SP, 'theta', 'fetch_cache')
OUT = os.path.join(HERE, '..', 'results', 'v1', 'v8_monthend'); os.makedirs(OUT, exist_ok=True)
EXPDIR = os.path.join(HERE, '..', 'results', 'expiry_calendar')
WINDOW = {'SPXW': (dt.date(2017, 6, 1), dt.date(2022, 4, 29)), 'SPY': (dt.date(2017, 6, 1), dt.date(2022, 10, 31))}
FEE = 0.70
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)

def expirations(root):
    p = os.path.join(EXPDIR, f'theta_expirations_{root}.parquet')
    if os.path.exists(p): return set(pl.read_parquet(p)['expiration'].to_list())
    if root == 'SPY':
        e = pl.read_parquet(os.path.join(EXPDIR, 'theta_expirations.parquet')).filter(pl.col('name') == 'SPY')
        return set(e['expiration'].to_list())
    return None

def month_ends(root):
    a, b = WINDOW[root]; ev = regime.event_days(); out, skipped = [], []
    ses = cal.sessions(a, b)
    for i, d in enumerate(ses):
        if i + 1 < len(ses) and ses[i + 1].month == d.month: continue
        if d.month == b.month and d.year == b.year and d != cal.sessions(d.replace(day=1), b)[-1]: continue
        if cal.is_early_close(d): skipped.append((d, 'half-day')); continue
        if 'FOMC' in ev.get(d, set()): skipped.append((d, 'FOMC day')); continue
        out.append(d)
    return out, skipped

def pull():
    from engine.data.theta_fetch import ThetaFetcher
    f = ThetaFetcher(CACHE, nw=4, log=log)
    p = os.path.join(EXPDIR, 'theta_expirations_SPXW.parquet')
    if not os.path.exists(p):
        df, err = f.call('option_list_expirations', symbol='SPXW')
        if err: raise SystemExit(f'SPXW expirations: {err}')
        col = [c for c in df.columns if 'exp' in c.lower()][0]
        x = df.select(pl.col(col).cast(pl.Utf8).str.slice(0, 10).alias('e')).with_columns(
            pl.when(pl.col('e').str.contains('-')).then(pl.col('e').str.to_date('%Y-%m-%d', strict=False)).otherwise(pl.col('e').str.to_date('%Y%m%d', strict=False)).alias('expiration'))
        x.select('expiration').drop_nulls().write_parquet(p); log('SPXW expirations', x.height)
    jobs = []
    for root in WINDOW:
        exp = expirations(root); me, _ = month_ends(root)
        jobs += [('chain_quotes', root, d, d) for d in me if d in exp]
    log('chains to pull', len(jobs)); f.run_jobs(jobs, 'v8 chains')

def spot_path(root, d):
    """price at the instant 09:30 + m (m = 0..390): SPX its print; SPY the close of the bar ending then"""
    if root == 'SPXW':
        df = pl.read_parquet(os.path.join(SP, 'theta', 'data', 'index', 'SPX', f'{d}.parquet'))
        m = ((df['timestamp'].dt.replace_time_zone(None) - dt.datetime.combine(d, dt.time(9, 30))).dt.total_minutes()).to_numpy()
        s = np.full(391, np.nan); ok = (m >= 0) & (m <= 390); s[m[ok]] = df['price'].to_numpy()[ok]
    else:
        df = pl.read_parquet(os.path.join(SP, 'theta', 'data', 'underlying', 'SPY', f'{d}.parquet'))
        m = ((df['timestamp'].dt.replace_time_zone(None) - dt.datetime.combine(d, dt.time(9, 30))).dt.total_minutes()).to_numpy()
        s = np.full(391, np.nan); c = df['close'].to_numpy()
        for mi, ci in zip(m, c):
            if 0 <= mi + 1 <= 390 and np.isfinite(ci): s[mi + 1] = ci
    for i in range(1, 391):
        if np.isnan(s[i]): s[i] = s[i - 1]
    return s

def tick(root, p): return (0.05 if p < 3 else 0.10) if root == 'SPXW' else 0.01

def build():
    rows, skipped = [], []
    for root in WINDOW:
        exp = expirations(root); me, sk = month_ends(root)
        skipped += [dict(root=root, session=d, reason=r) for d, r in sk]
        for d in me:
            if exp is None or d not in exp: skipped.append(dict(root=root, session=d, reason='no expiration dated that session')); continue
            p = os.path.join(CACHE, 'chains_exp', root, f'{d}__{d}.parquet')
            if not os.path.exists(p): skipped.append(dict(root=root, session=d, reason='chain not pulled or vendor returned none')); continue
            s = spot_path(root, d); S, ST = s[210], s[390]
            if not (np.isfinite(S) and np.isfinite(ST)): skipped.append(dict(root=root, session=d, reason='no 13:00 or 16:00 price')); continue
            ch = pl.read_parquet(p, columns=['timestamp', 'strike', 'right', 'bid', 'ask']).with_columns(pl.col('timestamp').dt.replace_time_zone(None))
            q = ch.filter(pl.col('timestamp') == dt.datetime.combine(d, dt.time(13, 0)))
            book = {(k, r[0].upper()): (bd, ak) for k, r, bd, ak in q.select('strike', 'right', 'bid', 'ask').iter_rows()}
            two = lambda x: x is not None and np.isfinite(x[0]) and np.isfinite(x[1]) and x[0] > 0 and x[1] >= x[0]
            ks = sorted({k for (k, r) in book if two(book.get((k, 'C'))) and two(book.get((k, 'P')))})
            if not ks: skipped.append(dict(root=root, session=d, reason='no two-sided straddle at 13:00')); continue
            K = min(ks, key=lambda k: (abs(k - S), k)); (cb, ca), (pb, pa) = book[(K, 'C')], book[(K, 'P')]
            mid = (cb + ca + pb + pa) / 2; pay = abs(ST - K); fee = 2 * FEE / 100
            rows.append(dict(root=root, session=d, year=d.year, S=S, ST=ST, K=K, mid=mid, ask=ca + pa, pay=pay,
                             implied_move=mid / S, realised_move=abs(ST / S - 1),
                             r=(pay - (ca + pa) - fee) / mid, r_adv=(pay - (ca + tick(root, ca) + pa + tick(root, pa)) - fee) / mid))
    T = pl.DataFrame(rows); T.write_parquet(os.path.join(OUT, 'trades.parquet'))
    X = pl.DataFrame(skipped); X.write_parquet(os.path.join(OUT, 'skipped.parquet'))
    print(T.group_by('root').agg(pl.len())); print(X.group_by('root', 'reason').agg(pl.len()))

def boot(v, B=10000, seed=9):
    v = np.asarray(v, float); rng = np.random.default_rng(seed); b = v[rng.integers(0, len(v), size=(B, len(v)))].mean(1)
    return float(v.mean()), float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975)), float(max((b <= 0).mean(), 1 / B))

def analyze():
    T = pl.read_parquet(os.path.join(OUT, 'trades.parquet')); rows = []
    for root in WINDOW:
        g = T.filter(pl.col('root') == root).sort('session')
        m, lo, hi, p = boot(g['r'].to_numpy()); ma, la, ha, _ = boot(g['r_adv'].to_numpy())
        rows.append(dict(root=root, days=g.height, mean=m, lo=lo, hi=hi, p_one_sided=p, median=float(g['r'].median()), mean_adverse=ma, lo_adverse=la, hi_adverse=ha,
                         realised_over_implied_median=float((g['realised_move'] / g['implied_move']).median()),
                         by_year=json.dumps({str(y): round(float(x['r'].mean()), 3) for (y,), x in g.group_by(['year'], maintain_order=True)})))
    R = pl.DataFrame(rows).sort('p_one_sided'); k = R.height; run = 0.0; holm = []
    for i, p in enumerate(R['p_one_sided'].to_list()): run = max(run, min(1.0, (k - i) * p)); holm.append(run)
    R = R.with_columns(pl.Series('p_holm', holm)); R.write_csv(os.path.join(OUT, 'tests.csv'))
    pl.Config.set_tbl_cols(16); pl.Config.set_tbl_width_chars(250); print(R)

if __name__ == '__main__':
    {'pull': pull, 'build': build, 'analyze': analyze}[sys.argv[1]]()
