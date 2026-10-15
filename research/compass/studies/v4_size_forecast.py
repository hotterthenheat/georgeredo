"""V4 (amendment A11): does a price-action forecast of the 10:00 -> 15:50 move beat the same-day straddle's implied move?

  python3 -I v4_size_forecast.py forecast            # per-name forecasts from one-minute bars -> forecasts.parquet
  python3 -I v4_size_forecast.py index               # SPY/QQQ/IWM same-day straddles, both sides (exploratory family)
  python3 -I v4_size_forecast.py analyze [--holdout] # V4s, V4l, V4e on V3's trades; the index family alongside
"""
import datetime as dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import numpy as np, polars as pl
from engine import bars as B, calendar as cal
import v3_single_name_0dte as v3

SP = v3.SP
OUT = os.path.join(HERE, '..', 'results', 'v1', 'v4_size_forecast'); os.makedirs(OUT, exist_ok=True)
SPLITS = [x for k in (2, 3, 4, 5, 8, 10, 15, 20, 25, 30, 40, 50) for x in (k, 1 / k)]
INDEX = {'SPY': dt.date(2022, 11, 11), 'QQQ': dt.date(2022, 11, 11), 'IWM': dt.date(2024, 4, 19)}
I_DEV, I_VAL = dt.date(2024, 6, 30), dt.date(2025, 6, 30)        # index family splits (exploratory)
log = v3.log

def bars_of(name):
    """one-minute bars for a name; META is FB before 2022-06-09 (A10.3); index ETFs from the research dataset"""
    if name in INDEX: return B.load_minutes(name, f'{SP}/theta/data/underlying', dt.date(2017, 6, 1), v3.END)
    parts = []
    for r, a, b in v3.roots(name):
        if os.path.isdir(os.path.join(v3.CACHE, 'underlying', r)): parts.append(B.load_minutes(r, os.path.join(v3.CACHE, 'underlying'), a, b))
    return pl.concat(parts, how='vertical_relaxed') if parts else None

def session_rows(name):
    df = bars_of(name)
    if df is None or df.height == 0: return None
    rows = []
    for (d,), g in df.group_by(['session'], maintain_order=True):
        if cal.is_early_close(d) or not v3.usable(g): continue                # A10.4
        mins = g['minute'].to_numpy(); cls = g['close'].to_numpy()
        def at(m):                                                         # the last bar's close at or before minute m
            k = np.searchsorted(mins, m, side='right') - 1
            return float(cls[k]) if k >= 0 else None
        o0 = float(g['open'][0]) if mins[0] <= 4 else None                 # the session's first bar opens by 09:34
        pts = [at(m) for m in range(29, 380, 5)]                           # 10:00, 10:05, ..., 15:50 (71 prices)
        opn = [o0] + [at(m) for m in range(4, 30, 5)]                      # 09:30 open, 09:35, ..., 10:00
        if o0 is None or any(p is None or not np.isfinite(p) for p in pts + opn): continue
        lr = np.diff(np.log(pts)); lo = np.diff(np.log(opn))
        rows.append(dict(name=name, session=d, rv=float(np.sum(lr ** 2)), rvo=float(np.sum(lo ** 2)), open=o0, last=float(g['close'][-1]),
                         p10=pts[0], p1550=pts[-1]))
    s = pl.DataFrame(rows).sort('session')
    prev_last = s['last'].shift(1).to_list(); ses = s['session'].to_list()
    g, flag = [], []
    for i, (o, d) in enumerate(zip(s['open'].to_list(), ses)):
        ok = i > 0 and cal.prev_session(d) == ses[i - 1]
        r = o / prev_last[i] if ok else np.nan
        g.append(np.log(r) if ok else np.nan)
        flag.append(bool(ok and any(abs(r / f - 1) <= 0.10 for f in SPLITS)))
    s = s.with_columns(pl.Series('g', g), pl.Series('split', flag))
    # A11: split sessions and the session after them leave fits and lags
    bad = s['split'].to_list(); bad = [b or (i > 0 and bad[i - 1]) for i, b in enumerate(bad)]
    return s.with_columns(pl.Series('skip', bad))

def features(s):
    rv = s['rv'].to_numpy(); skip = s['skip'].to_numpy(); out = []
    good = [i for i in range(len(rv)) if not skip[i] and rv[i] > 0]
    pos = {i: k for k, i in enumerate(good)}
    for i in good:
        k = pos[i]
        if k < 22: out.append(None); continue
        h = [rv[good[j]] for j in range(k - 22, k)]
        out.append((np.log(h[-1]), np.log(np.mean(h[-5:])), np.log(np.mean(h)), i))
    return good, out

def forecast():
    allrows = []
    for name in v3.NAMES + list(INDEX):
        s = session_rows(name)
        if s is None: log(name, 'no bars'); continue
        good, feats = features(s)
        rvo = s['rvo'].to_numpy(); g = s['g'].to_numpy(); rv = s['rv'].to_numpy(); ses = s['session'].to_list()
        recs = [(f[3], f[0], f[1], f[2]) for f in feats if f is not None]
        first = ses[0]
        for y in range(2019, 2027):
            cut = dt.date(y, 1, 1)
            if (cut - first).days < 730: continue
            fit = [r for r in recs if ses[r[0]] < cut and rvo[r[0]] > 0 and np.isfinite(g[r[0]])]
            if len(fit) < 250: continue
            c = float(np.median([g[r[0]] ** 2 for r in fit]))
            X = np.array([[1, r[1], r[2], r[3], np.log(rvo[r[0]]), np.log(g[r[0]] ** 2 + c)] for r in fit]); Y = np.array([np.log(rv[r[0]]) for r in fit])
            beta, *_ = np.linalg.lstsq(X, Y, rcond=None); s2 = float(np.mean((Y - X @ beta) ** 2))
            for r in recs:
                d = ses[r[0]]
                if d.year != y or rvo[r[0]] <= 0 or not np.isfinite(g[r[0]]): continue
                x = np.array([1, r[1], r[2], r[3], np.log(rvo[r[0]]), np.log(g[r[0]] ** 2 + c)])
                erv = float(np.exp(x @ beta + s2 / 2))
                allrows.append(dict(name=name, session=d, fit_year=y, fit_n=len(fit), rv=float(rv[r[0]]), erv=erv, m_hat=float(np.sqrt(2 / np.pi * erv)),
                                    realised_move=abs(s['p1550'][r[0]] / s['p10'][r[0]] - 1), b=json.dumps([round(float(v), 4) for v in beta])))
        log(name, 'forecasts', sum(1 for r in allrows if r['name'] == name))
    F = pl.DataFrame(allrows); F.write_parquet(os.path.join(OUT, 'forecasts.parquet'))
    # out-of-sample calibration of the forecast itself (no option data)
    F2 = F.with_columns((pl.col('rv').log() - pl.col('erv').log()).alias('e'))
    print(F2.group_by('name').agg(pl.len(), pl.corr(pl.col('rv').log(), pl.col('erv').log()).pow(2).alias('r2_ln_rv'),
                                  pl.col('e').mean().alias('mean_ln_err')).sort('name'))

def index_trades():
    """SPY/QQQ (2022-11-11 ->) and IWM (2024-04-19 ->) same-day ATM straddles under V3's rules (entry 10:00, exit 15:50,
    A10.1 exit quotes, A10.4 bars), both sides. Exploratory (A11, A11.1)."""
    from engine import run as R
    rows = []
    for sym, first in INDEX.items():
        bars = B.load_minutes(sym, f'{SP}/theta/data/underlying', first, v3.END)
        bars = {k[0]: g for k, g in bars.group_by('session')}
        root = f'{SP}/theta/data_full/chains/{sym}'
        for f in sorted(os.listdir(root)):
            d = dt.date.fromisoformat(f[:10])
            if d < first or d > v3.END or cal.is_early_close(d): continue
            day = bars.get(d)
            if day is None or not v3.usable(day): continue
            spot0 = v3.price_at(day, 29)
            if spot0 is None: continue
            ch = pl.read_parquet(os.path.join(root, f), columns=['timestamp', 'strike', 'right', 'bid', 'ask']).with_columns(pl.col('timestamp').dt.replace_time_zone(None))
            s_in = v3.snap(ch, dt.datetime.combine(d, dt.time(10, 0))); s_out = v3.snap(ch, dt.datetime.combine(d, dt.time(15, 50)))
            if s_in.height == 0 or s_out.height == 0: continue
            q_in = {(k, r): dict(bid=b, ask=a) for k, r, b, a in s_in.select('strike', 'right', 'bid', 'ask').iter_rows()}
            q_out = {(k, r): dict(bid=b, ask=a) for k, r, b, a in s_out.select('strike', 'right', 'bid', 'ask').iter_rows()}
            ks = sorted({k for (k, r) in q_in if v3.two_sided(q_in.get((k, 'CALL'))) and v3.two_sided(q_in.get((k, 'PUT')))})
            if not ks: continue
            K = min(ks, key=lambda k: (abs(k - spot0), k))
            ci, pi, co, po = q_in[(K, 'CALL')], q_in[(K, 'PUT')], q_out.get((K, 'CALL')), q_out.get((K, 'PUT'))
            mid = (ci['bid'] + ci['ask'] + pi['bid'] + pi['ask']) / 2
            row = dict(symbol=sym, session=d, implied_move=mid / spot0, straddle_mid=mid)
            ok = co is not None and po is not None and all(np.isfinite(x[k]) for x in (co, po) for k in ('bid', 'ask'))
            if ok and co['ask'] > 0 and po['ask'] > 0:
                row['a_r'] = ((ci['bid'] + pi['bid'] - co['ask'] - po['ask']) * 100 - 4 * v3.FEE) / (mid * 100)
            if ok and co['bid'] >= 0 and po['bid'] >= 0:
                row['c_r'] = ((co['bid'] + po['bid'] - ci['ask'] - pi['ask']) * 100 - 4 * v3.FEE) / (mid * 100)
            rows.append(row)
        log(sym, 'straddles', sum(1 for r in rows if r['symbol'] == sym))
    T = pl.DataFrame(rows, infer_schema_length=None); T.write_parquet(os.path.join(OUT, 'index_trades.parquet'))

def boot_diff(sub, base, col, B=10000, seed=9):
    """mean over the conditional trades minus the mean over every trade, sessions resampled together"""
    a = sub.filter(pl.col(col).is_not_null() & pl.col(col).is_finite()).group_by('session').agg(pl.col(col).sum().alias('s'), pl.len().alias('n'))
    b = base.filter(pl.col(col).is_not_null() & pl.col(col).is_finite()).group_by('session').agg(pl.col(col).sum().alias('s2'), pl.len().alias('n2'))
    m = b.join(a, on='session', how='left').fill_null(0).sort('session')
    if m['n'].sum() < 10: return float('nan'), float('nan'), float('nan')
    s, n, s2, n2 = (m[c].to_numpy() for c in ('s', 'n', 's2', 'n2')); rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), size=(B, len(s)))
    ns = n[idx].sum(1); d = np.where(ns > 0, s[idx].sum(1) / np.maximum(ns, 1), np.nan) - s2[idx].sum(1) / n2[idx].sum(1)
    return float(s.sum() / n.sum() - s2.sum() / n2.sum()), float(np.nanquantile(d, 0.025)), float(np.nanquantile(d, 0.975))

def encompass(df, B=2000, seed=9):
    """ln(max(realised move, 1 bp)) on ln m and ln m_hat; session-resampled 95 % interval on each slope"""
    d = df.filter(pl.col('implied_move') > 0).with_columns(pl.max_horizontal(pl.col('realised_move'), pl.lit(1e-4)).log().alias('y'),
                                                           pl.col('implied_move').log().alias('x1'), pl.col('m_hat').log().alias('x2'))
    if d.height < 50: return {}
    X = np.c_[np.ones(d.height), d['x1'].to_numpy(), d['x2'].to_numpy()]; y = d['y'].to_numpy()
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    ses = d['session'].to_numpy(); u, inv = np.unique(ses, return_inverse=True)   # np.unique sorts: a fixed order; groups = [np.where(inv == i)[0] for i in range(len(u))]
    rng = np.random.default_rng(seed); bs = []
    for _ in range(B):
        pick = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        bs.append(np.linalg.lstsq(X[pick], y[pick], rcond=None)[0])
    bs = np.array(bs)
    r2 = lambda Xm: 1 - np.sum((y - Xm @ np.linalg.lstsq(Xm, y, rcond=None)[0]) ** 2) / np.sum((y - y.mean()) ** 2)
    return dict(n=d.height, sessions=len(u), b_implied=float(beta[1]), b_implied_lo=float(np.quantile(bs[:, 1], 0.025)), b_implied_hi=float(np.quantile(bs[:, 1], 0.975)),
                b_forecast=float(beta[2]), b_forecast_lo=float(np.quantile(bs[:, 2], 0.025)), b_forecast_hi=float(np.quantile(bs[:, 2], 0.975)),
                r2_implied_only=float(r2(X[:, :2])), r2_forecast_only=float(r2(X[:, [0, 2]])), r2_both=float(r2(X)))

def analyze(holdout=False):
    F = pl.read_parquet(os.path.join(OUT, 'forecasts.parquet')).select('name', 'session', 'm_hat', pl.col('realised_move').alias('rm_f'))
    T = pl.read_parquet(os.path.join(v3.OUT, 'trades.parquet')).join(F, left_on=['symbol', 'session'], right_on=['name', 'session'], how='inner')
    T = T.filter(~pl.col('event') & (pl.col('session') >= dt.date(2019, 6, 3)))
    T = T.with_columns((pl.col('implied_move') / pl.col('m_hat')).alias('R'),
                       pl.when(pl.col('session') <= v3.DEV_END).then(pl.lit('dev')).when(pl.col('session') <= v3.VAL_END).then(pl.lit('val')).otherwise(pl.lit('holdout')).alias('split'))
    if holdout:
        flag = os.path.join(OUT, 'holdout_opened.json')
        if os.path.exists(flag): print('hold-out already opened:', open(flag).read())
        else: json.dump({'opened_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}, open(flag, 'w'))
    else: T = T.filter(pl.col('split') != 'holdout')
    lo, hi = T.filter(pl.col('split') == 'dev').select(pl.col('R').quantile(1 / 3).alias('a'), pl.col('R').quantile(2 / 3).alias('b')).row(0)
    log(f'tercile cut-offs on development R: {lo:.4f} / {hi:.4f}')
    rows = []
    for col, lab, f in (('a_r', 'V4s short straddle, R top tercile', pl.col('R') >= hi), ('a_r_adv', 'V4s, one tick worse', pl.col('R') >= hi),
                        ('c_r', 'V4l long straddle, R bottom tercile', pl.col('R') <= lo), ('c_r_adv', 'V4l, one tick worse', pl.col('R') <= lo)):
        for sp in ['dev', 'val', 'devval'] + (['holdout'] if holdout else []):
            base = T.filter(pl.col('split') != 'holdout') if sp == 'devval' else T.filter(pl.col('split') == sp)
            sub = base.filter(f)
            n, m, l, h, p = v3.cboot(sub, col)
            dm, dl, dh = boot_diff(sub, base, col)
            rows.append(dict(test=lab, col=col, split=sp, trades=n, mean=m, lo=l, hi=h, p=p, minus_unconditional=dm, diff_lo=dl, diff_hi=dh))
    Rz = pl.DataFrame(rows)
    base = Rz.filter((pl.col('split') == 'devval') & pl.col('col').is_in(['a_r', 'c_r'])).sort('p'); k = base.height; holm = {}; run = 0.0
    for i, (c, p) in enumerate(base.select('col', 'p').iter_rows()): run = max(run, min(1.0, (k - i) * p)); holm[c] = run
    Rz = Rz.with_columns(pl.col('col').replace_strict(holm, default=None).alias('p_holm_devval'))
    tag = '_holdout' if holdout else ''
    Rz.write_csv(os.path.join(OUT, f'results{tag}.csv')); pl.Config.set_tbl_rows(60); pl.Config.set_tbl_cols(14); print(Rz)
    enc = []
    for sp in ['dev', 'val', 'devval'] + (['holdout'] if holdout else []):
        d = T.filter(pl.col('split') != 'holdout') if sp == 'devval' else T.filter(pl.col('split') == sp)
        enc.append(dict(family='single names', split=sp, **encompass(d)))
    # exploratory: the index family on its whole window (A11, A11.1)
    I = pl.read_parquet(os.path.join(OUT, 'index_trades.parquet'))
    Fi = pl.read_parquet(os.path.join(OUT, 'forecasts.parquet')).select('name', 'session', 'm_hat', 'realised_move')
    I = I.join(Fi, left_on=['symbol', 'session'], right_on=['name', 'session'], how='inner').with_columns((pl.col('implied_move') / pl.col('m_hat')).alias('R'))
    enc.append(dict(family='index (exploratory)', split='2022-11 -> 2026-10', **encompass(I)))
    E = pl.DataFrame(enc); E.write_csv(os.path.join(OUT, f'encompassing{tag}.csv')); print(E)
    ilo, ihi = I.select(pl.col('R').quantile(1 / 3).alias('a'), pl.col('R').quantile(2 / 3).alias('b')).row(0)
    ex = []
    for col, lab, f in (('a_r', 'index short, R top tercile (cut-offs on the whole window: in-sample)', pl.col('R') >= ihi), ('c_r', 'index long, R bottom tercile', pl.col('R') <= ilo),
                        ('a_r', 'index short, every session', pl.lit(True)), ('c_r', 'index long, every session', pl.lit(True))):
        n, m, l, h, _ = v3.cboot(I.filter(f), col); ex.append(dict(cell=lab, trades=n, mean=m, lo=l, hi=h))
    X = pl.DataFrame(ex); X.write_csv(os.path.join(OUT, f'index_exploratory{tag}.csv')); print(X)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'forecast': forecast()
    elif cmd == 'index': index_trades()
    elif cmd == 'analyze': analyze('--holdout' in sys.argv)
