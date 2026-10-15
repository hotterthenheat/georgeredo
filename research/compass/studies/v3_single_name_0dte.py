"""V3 (amendment A10): same-day (0DTE) premium on the eleven single names that list Monday/Wednesday/Friday expirations.

  python3 -I v3_single_name_0dte.py jobs        # the (name, session) list from ThetaData's expirations, counts only
  python3 -I v3_single_name_0dte.py pull        # same-day chains, INTC bars 2025->, stock EOD closes (ThetaData login:
                                                #   bulk_fetch.py paused, outside 13:00-21:00 UTC)
  python3 -I v3_single_name_0dte.py build       # trades.parquet + exclusions.parquet
  python3 -I v3_single_name_0dte.py analyze [--holdout]
"""
import datetime as dt, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import numpy as np, polars as pl
from engine import calendar as cal

SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
CACHE = os.path.join(SP, 'theta', 'fetch_cache')
OUT = os.path.join(HERE, '..', 'results', 'v1', 'v3_single_name_0dte'); os.makedirs(OUT, exist_ok=True)
EXP = os.path.join(HERE, '..', 'results', 'expiry_calendar', 'theta_expirations.parquet')
NAMES = ['AAPL', 'AMD', 'AMZN', 'AVGO', 'GOOGL', 'INTC', 'META', 'MSFT', 'MU', 'NVDA', 'TSLA']
START, END = dt.date(2017, 6, 1), dt.date(2026, 10, 9)
DEV_END, VAL_END = dt.date(2022, 12, 31), dt.date(2024, 12, 31)
FEE = 0.70
SPLIT_FACTORS = [1/2, 1/3, 1/4, 1/5, 1/10, 1/20, 1/50, 2, 3, 4, 5, 8, 10, 15, 20, 25, 30, 40, 50]   # A10.2: A8.1's without 3:2
SPLIT_TOL = 0.10
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)

# A10.3: Facebook is root FB before 2022-06-09 and META from then; the symbol META before that was another security
ROOTS_OF = {'META': [('FB', START, dt.date(2022, 6, 8)), ('META', dt.date(2022, 6, 9), END)]}
EXP_EXTRA = os.path.join(HERE, '..', 'results', 'expiry_calendar', 'theta_expirations_extra.parquet')

def roots(t): return ROOTS_OF.get(t, [(t, START, END)])

def root_of(t, d): return next(r for r, a, b in roots(t) if a <= d <= b)

def jobs():
    e = pl.read_parquet(EXP).select('name', 'expiration')
    if os.path.exists(EXP_EXTRA): e = pl.concat([e, pl.read_parquet(EXP_EXTRA).select('name', 'expiration')])
    have = {}
    for r, d in e.iter_rows(): have.setdefault(r, set()).add(d)
    out = []
    for t in NAMES:
        for r, a, b in roots(t):
            out += [(t, d) for d in have.get(r, ()) if a <= d <= b and START <= d <= END and cal.is_session(d)]
    return sorted(set(out))

def eod_path(t): return os.path.join(CACHE, 'v3_eod', f'{t}.parquet')

def pull():
    from engine.data.theta_fetch import ThetaFetcher
    f = ThetaFetcher(CACHE, nw=int(os.environ.get('V3_NW', '6')), log=log)
    # stock end-of-day closes, one call a name a year
    os.makedirs(os.path.join(CACHE, 'v3_eod'), exist_ok=True)
    if not os.path.exists(EXP_EXTRA):                    # every expiration FB listed (Facebook before the ticker change)
        df, err = f.call('option_list_expirations', symbol='FB')
        if err: raise SystemExit(f'FB expirations: {err}')
        col = [c for c in df.columns if 'exp' in c.lower()][0]
        x = df.select(pl.col(col).cast(pl.Utf8).str.slice(0, 10).alias('e')).with_columns(
            pl.when(pl.col('e').str.contains('-')).then(pl.col('e').str.to_date('%Y-%m-%d', strict=False)).otherwise(pl.col('e').str.to_date('%Y%m%d', strict=False)).alias('expiration'))
        x.select('expiration').drop_nulls().with_columns(pl.lit('FB').alias('name')).write_parquet(EXP_EXTRA); log('FB expirations', x.height)
    for t in sorted({r for n in NAMES for r, _, _ in roots(n)}):
        if os.path.exists(eod_path(t)): continue
        frames = []
        for y in range(START.year, END.year + 1):
            df, err = f.call('stock_history_eod', symbol=t, start_date=dt.date(y, 1, 1), end_date=min(dt.date(y, 12, 31), END))
            if err: log(t, y, 'eod', err); continue
            frames.append(df)
        df = pl.concat(frames, how='diagonal_relaxed')
        df.write_parquet(eod_path(t)); log(t, 'eod rows', df.height, df.columns)
    f.stock_minutes('INTC', dt.date(2025, 1, 1), END)
    f.stock_minutes('FB', START, dt.date(2022, 6, 8))
    J = [('chain_quotes', root_of(t, d), d, d) for t, d in jobs()]
    if os.environ.get('V3_LIMIT'): J = J[:int(os.environ['V3_LIMIT'])]
    f.run_jobs(J, 'v3 chains')

def eod(t):
    df = pl.read_parquet(eod_path(t))
    tcol = 'created' if 'created' in df.columns else ('date' if 'date' in df.columns else 'timestamp')
    d = df.with_columns(pl.col(tcol).cast(pl.Utf8).str.slice(0, 10).str.to_date().alias('session'))
    return d.select('session', pl.col('close').cast(pl.Float64)).unique('session').sort('session')

def usable(day):
    """A10.4: at least one bar in each of the 13 half-hours"""
    return set((m // 30) for m in day['minute'].to_list() if 0 <= m < 390) >= set(range(13))

def price_at(day, m, stale=5):
    """A10.4: the close of the last bar at or before minute m (the bar ending m+1), at most `stale` minutes earlier"""
    x = day.filter((pl.col('minute') <= m) & (pl.col('minute') >= m - stale)).sort('minute')
    return float(x['close'][-1]) if x.height else None

def snap(ch, ts):
    """the chain's quotes at one minute stamp (run._snapshot_at without the size columns)"""
    return ch.filter(pl.col('timestamp') == ts).select('strike', 'right', 'bid', 'ask')

def tick(p): return 0.01 if p < 3 else 0.05

def two_sided(r): return r is not None and np.isfinite(r['bid']) and np.isfinite(r['ask']) and r['bid'] > 0 and r['ask'] >= r['bid']

def event_sessions(t):
    """A10/A10.1: the report date for pre-market, the next session for post-market, both for an unknown time"""
    e = pl.read_parquet(os.path.join(HERE, '..', '..', '..', 'data_lake', 'unusualwhales', 'earnings.parquet'), columns=['ticker', 'report_date', 'report_time'])
    e = e.filter(pl.col('ticker').is_in([t, 'FB'] if t == 'META' else [t]) & pl.col('report_date').is_not_null()).unique(['report_date'])
    out = set()
    for rd, rt in e.select('report_date', 'report_time').iter_rows():
        d = dt.date.fromisoformat(rd[:10])
        if d < START - dt.timedelta(days=10) or d > END + dt.timedelta(days=10): continue
        s0 = d if cal.is_session(d) else cal.next_session(d)
        if rt == 'premarket': out.add(s0)
        elif rt == 'postmarket': out.add(cal.next_session(d))
        else: out.update({s0, cal.next_session(d)})
    return out

def split_sessions(closes):
    """A10.2: a close-to-close ratio within 10 % of a split ratio of 2:1 or larger; the split session and the four after it"""
    c = closes.with_columns((pl.col('close') / pl.col('close').shift(1)).alias('r'))
    out = set()
    for d, r in c.select('session', 'r').iter_rows():
        if r is None or not np.isfinite(r): continue
        if any(abs(r / f - 1) <= SPLIT_TOL for f in SPLIT_FACTORS):
            x = d
            for _ in range(5): out.add(x); x = cal.next_session(x)
    return out

def build():
    from engine import bars as B, run as R
    J = jobs(); rows, excl = [], []
    by = {}
    for t, d in J: by.setdefault(t, []).append(d)
    for t in NAMES:
        bars, close, spl = {}, {}, set()
        for r, a, b in roots(t):
            bb = B.load_minutes(r, os.path.join(CACHE, 'underlying'), a, b)
            bars.update({k[0]: g for k, g in bb.group_by('session')})
            closes = eod(r).filter(pl.col('session').is_between(a - dt.timedelta(days=10), b))
            close.update({d: c for d, c in closes.iter_rows() if a <= d <= b}); spl |= {d for d in split_sessions(closes) if a <= d <= b}
        ev = event_sessions(t)
        log(t, 'sessions', len(by[t]), 'events', len(ev), 'split sessions', sorted(spl))
        for d in by[t]:
            base = dict(symbol=t, root=root_of(t, d), session=d)
            def ex(why): excl.append({**base, 'reason': why})
            if cal.is_early_close(d): ex('half-day session'); continue
            if d in spl: ex('split window'); continue
            day = bars.get(d)
            if day is None or not usable(day): ex('a half-hour with no bar (A10.4)'); continue
            spot0, spot1 = price_at(day, 29), price_at(day, 379)
            if spot0 is None or spot1 is None: ex('no bar within five minutes of 10:00 or 15:50 (A10.4)'); continue
            cl = close.get(d)
            if cl is None or not np.isfinite(cl): ex('no end-of-day close'); continue
            f = os.path.join(CACHE, 'chains_exp', base['root'], f'{d}__{d}.parquet')
            if not os.path.exists(f): ex('no same-day chain (vendor returned none)' if os.path.exists(f[:-8] + '.nodata') else 'chain not pulled'); continue
            ch = pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'bid', 'ask']).with_columns(pl.col('timestamp').dt.replace_time_zone(None))
            s_in = snap(ch, dt.datetime.combine(d, dt.time(10, 0))); s_out = snap(ch, dt.datetime.combine(d, dt.time(15, 50)))
            if s_in.height == 0 or s_out.height == 0: ex('no 10:00 or 15:50 chain snapshot'); continue
            q_in = {(k, r): dict(bid=bd, ask=ak) for k, r, bd, ak in s_in.select('strike', 'right', 'bid', 'ask').iter_rows()}
            q_out = {(k, r): dict(bid=bd, ask=ak) for k, r, bd, ak in s_out.select('strike', 'right', 'bid', 'ask').iter_rows()}
            ks = sorted({k for (k, r) in q_in if two_sided(q_in.get((k, 'CALL'))) and two_sided(q_in.get((k, 'PUT')))})
            if not ks: ex('no two-sided straddle at 10:00'); continue
            K = min(ks, key=lambda k: (abs(k - spot0), k))
            ci, pi, co, po = q_in[(K, 'CALL')], q_in[(K, 'PUT')], q_out.get((K, 'CALL')), q_out.get((K, 'PUT'))
            mid_in = (ci['bid'] + ci['ask'] + pi['bid'] + pi['ask']) / 2
            row = {**base, 'wd': d.isoweekday(), 'year': d.year, 'event': d in ev, 'spot0': spot0, 'spot1': spot1, 'close': cl, 'K': K,
                   'straddle_mid': mid_in, 'implied_move': mid_in / spot0, 'realised_move': abs(spot1 / spot0 - 1),
                   'rel_spread': (ci['ask'] + pi['ask'] - ci['bid'] - pi['bid']) / mid_in,
                   'split': 'dev' if d <= DEV_END else ('val' if d <= VAL_END else 'holdout')}
            ok_out = co is not None and po is not None and all(np.isfinite(x[k]) for x in (co, po) for k in ('bid', 'ask'))
            if ok_out and co['ask'] > 0 and po['ask'] > 0:
                pnl = (ci['bid'] + pi['bid'] - co['ask'] - po['ask']) * 100 - 4 * FEE
                adv = (max(ci['bid'] - tick(ci['bid']), 0) + max(pi['bid'] - tick(pi['bid']), 0) - co['ask'] - tick(co['ask']) - po['ask'] - tick(po['ask'])) * 100 - 4 * FEE
                row.update(a_status='ok', a_pnl=pnl, a_r=pnl / (mid_in * 100), a_r_adv=adv / (mid_in * 100))
            else: row.update(a_status='no exit quote at 15:50')
            if ok_out and co['bid'] >= 0 and po['bid'] >= 0:
                pnl = (co['bid'] + po['bid'] - ci['ask'] - pi['ask']) * 100 - 4 * FEE
                adv = (max(co['bid'] - tick(co['bid']), 0) + max(po['bid'] - tick(po['bid']), 0) - ci['ask'] - tick(ci['ask']) - pi['ask'] - tick(pi['ask'])) * 100 - 4 * FEE
                row.update(c_status='ok', c_pnl=pnl, c_r=pnl / (mid_in * 100), c_r_adv=adv / (mid_in * 100))
            else: row.update(c_status='no exit quote at 15:50')
            target = spot0 - mid_in
            kp = [k for (k, r) in q_in if r == 'PUT' and k < spot0 and two_sided(q_in[(k, r)])]
            if kp:
                Kp = min(kp, key=lambda k: (abs(k - target), -k)); q = q_in[(Kp, 'PUT')]
                pm = (q['bid'] + q['ask']) / 2; intr = max(Kp - cl, 0.0)
                pnl = (q['bid'] - intr) * 100 - FEE; adv = (max(q['bid'] - tick(q['bid']), 0) - intr) * 100 - FEE
                row.update(b_status='ok', b_K=Kp, b_mid=pm, b_bid=q['bid'], b_intrinsic=intr, b_pnl=pnl, b_r=pnl / (pm * 100), b_r_adv=adv / (pm * 100))
            else: row.update(b_status='no two-sided put below spot at 10:00')
            rows.append(row)
    T = pl.DataFrame(rows, infer_schema_length=None); X = pl.DataFrame(excl)
    T.write_parquet(os.path.join(OUT, 'trades.parquet')); X.write_parquet(os.path.join(OUT, 'exclusions.parquet'))
    log('trades', T.height, 'exclusions', X.height); print(X.group_by('reason').agg(pl.len()).sort('len', descending=True))
    print(T.group_by('a_status').agg(pl.len()), T.group_by('b_status').agg(pl.len()))

def cboot(df, col, B=10000, seed=9):
    """mean per trade, 95 % interval resampling sessions (every name on a date together); as V2's cboot"""
    d = df.filter(pl.col(col).is_not_null() & pl.col(col).is_finite())
    if d.height < 10: return d.height, float('nan'), float('nan'), float('nan'), float('nan')
    g = d.group_by('session').agg(pl.col(col).sum().alias('s'), pl.len().alias('n')).sort('session')   # a fixed order: the same seed, the same draws
    s, n = g['s'].to_numpy(), g['n'].to_numpy(); rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), size=(B, len(s)))
    b = s[idx].sum(1) / n[idx].sum(1)
    p = 2 * min((b <= 0).mean(), (b >= 0).mean())
    return d.height, float(d[col].mean()), float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975)), float(max(p, 1 / B))

TESTS = (('a_r', 'V3a short straddle 10:00-15:50'), ('a_r_adv', 'V3a, one tick worse'), ('b_r', 'V3b short put to the close'),
         ('b_r_adv', 'V3b, one tick worse'), ('c_r', 'V3c long straddle 10:00-15:50'), ('c_r_adv', 'V3c, one tick worse'))

def analyze(holdout=False):
    T = pl.read_parquet(os.path.join(OUT, 'trades.parquet'))
    if holdout:
        flag = os.path.join(OUT, 'holdout_opened.json')
        if os.path.exists(flag): print('hold-out already opened:', open(flag).read())
        else: json.dump({'opened_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}, open(flag, 'w'))
    else: T = T.filter(pl.col('split') != 'holdout')
    P = T.filter(~pl.col('event'))
    rows = []
    for col, lab in TESTS:
        for sp in ['dev', 'val', 'devval'] + (['holdout'] if holdout else []):
            d = P.filter(pl.col('split') != 'holdout') if sp == 'devval' else P.filter(pl.col('split') == sp)
            n, m, lo, hi, p = cboot(d, col)
            rows.append({'test': lab, 'col': col, 'split': sp, 'trades': n, 'mean': m, 'lo': lo, 'hi': hi, 'p': p})
    R = pl.DataFrame(rows)
    # Holm across V3a, V3b, V3c on the development + validation p-values
    base = R.filter((pl.col('split') == 'devval') & pl.col('col').is_in(['a_r', 'b_r', 'c_r'])).sort('p')
    k = base.height; holm = {}; run = 0.0
    for i, (c, p) in enumerate(base.select('col', 'p').iter_rows()):
        run = max(run, min(1.0, (k - i) * p)); holm[c] = run
    R = R.with_columns(pl.col('col').replace_strict(holm, default=None).alias('p_holm_devval'))
    tag = '_holdout' if holdout else ''
    R.write_csv(os.path.join(OUT, f'results{tag}.csv'))
    pl.Config.set_tbl_rows(100); pl.Config.set_tbl_cols(10); print(R)
    # descriptive, never promoted
    D = T.filter(pl.col('split') != 'holdout') if not holdout else T
    desc = []
    def add(cut, sub):
        for col in ('a_r', 'b_r', 'c_r'):
            n, m, lo, hi, _ = cboot(sub, col); desc.append({'cut': cut, 'col': col, 'trades': n, 'mean': m, 'lo': lo, 'hi': hi})
    for t in NAMES: add(f'name {t}', D.filter(~pl.col('event') & (pl.col('symbol') == t)))
    for w, nm in ((1, 'Monday'), (3, 'Wednesday'), (4, 'Thursday'), (5, 'Friday'), (2, 'Tuesday')): add(f'weekday {nm}', D.filter(~pl.col('event') & (pl.col('wd') == w)))
    for y in sorted(D['year'].unique().to_list()): add(f'year {y}', D.filter(~pl.col('event') & (pl.col('year') == y)))
    q = D.filter(~pl.col('event'))['rel_spread'].quantile([1 / 3, 2 / 3]) if False else None
    qs = D.filter(~pl.col('event')).select(pl.col('rel_spread').quantile(1 / 3).alias('a'), pl.col('rel_spread').quantile(2 / 3).alias('b')).row(0)
    add(f'relative spread low (<= {qs[0]:.3f})', D.filter(~pl.col('event') & (pl.col('rel_spread') <= qs[0])))
    add('relative spread middle', D.filter(~pl.col('event') & (pl.col('rel_spread') > qs[0]) & (pl.col('rel_spread') <= qs[1])))
    add(f'relative spread high (> {qs[1]:.3f})', D.filter(~pl.col('event') & (pl.col('rel_spread') > qs[1])))
    add('event sessions (excluded from the tests)', D.filter(pl.col('event')))
    Dn = D.filter(~pl.col('event'))
    ratio = (Dn['realised_move'] / Dn['implied_move']).to_numpy()
    desc.append({'cut': 'realised 10:00-15:50 move / straddle-implied move, median [IQR]', 'col': 'ratio', 'trades': len(ratio), 'mean': float(np.median(ratio)), 'lo': float(np.quantile(ratio, 0.25)), 'hi': float(np.quantile(ratio, 0.75))})
    desc.append({'cut': 'straddle relative spread at 10:00, median [IQR]', 'col': 'rel_spread', 'trades': Dn.height, 'mean': float(Dn['rel_spread'].median()), 'lo': float(Dn['rel_spread'].quantile(0.25)), 'hi': float(Dn['rel_spread'].quantile(0.75))})
    Dd = pl.DataFrame(desc); Dd.write_csv(os.path.join(OUT, f'descriptive{tag}.csv')); print(Dd)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'jobs':
        J = jobs(); df = pl.DataFrame(J, schema=['name', 'session'], orient='row').with_columns(pl.col('session').dt.weekday().alias('wd'))
        print(len(J)); print(df.group_by('name').agg(pl.len(), (pl.col('wd') == 1).sum().alias('mon'), (pl.col('wd') == 3).sum().alias('wed'), pl.col('session').min().alias('first'), pl.col('session').max().alias('last')).sort('name'))
    elif cmd == 'pull': pull()
    elif cmd == 'build': build()
    elif cmd == 'analyze': analyze('--holdout' in sys.argv)
