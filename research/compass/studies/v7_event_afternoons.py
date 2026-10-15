"""V7 (amendment A14): are event afternoons priced at what they then move? The 13:00 same-day straddle against the move
to 16:00, on FOMC and month-end sessions, against the previous 20 event-free sessions.
  python3 -I v7_event_afternoons.py build      # sessions.parquet: I, R, x for every full session and root
  python3 -I v7_event_afternoons.py analyze
"""
import datetime as dt, os, sys
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', 'lifecycle'))
import numpy as np, polars as pl
from engine import calendar as cal, regime

OUT = os.path.join(HERE, '..', 'results', 'v1', 'v7_event_afternoons'); os.makedirs(OUT, exist_ok=True)
ROOTS = ['SPXW', 'SPY', 'QQQ', 'IWM']
T13 = 210

def one(args):
    root, sess = args
    from lc.chainmat import load_0dte
    cd = load_0dte(root, sess)
    if cd is None or cd.n_min != 391: return None
    S, ST = cd.spot[T13], cd.spot[390]
    if not (np.isfinite(S) and np.isfinite(ST)): return None
    b, a = cd.bid[:, T13], cd.ask[:, T13]
    ok = np.isfinite(b) & np.isfinite(a) & (b > 0) & (a >= b)
    calls = {k: i for i, (k, c) in enumerate(zip(cd.strike, cd.is_call)) if c}
    puts = {k: i for i, (k, c) in enumerate(zip(cd.strike, cd.is_call)) if not c}
    both = [k for k in calls if k in puts and ok[calls[k]] and ok[puts[k]]]
    if not both: return None
    K = min(both, key=lambda k: (abs(k - S), k)); ic, ip = calls[K], puts[K]
    I = ((b[ic] + a[ic]) / 2 + (b[ip] + a[ip]) / 2) / S
    R = abs(ST / S - 1)
    return dict(root=root, session=sess, S=float(S), ST=float(ST), K=float(K), I=float(I), R=float(R), x=float(np.log(max(R, 1e-4) / I)))

def build():
    from lc.chainmat import sessions_0dte
    import multiprocessing as mp
    jobs = [(r, s) for r in ROOTS for s in sessions_0dte(r) if not cal.is_early_close(s)]
    with ProcessPoolExecutor(3, mp_context=mp.get_context('spawn')) as ex:
        rows = [r for r in ex.map(one, jobs, chunksize=16) if r is not None]
    ev = regime.event_days()
    df = pl.DataFrame(rows).with_columns(
        pl.col('session').map_elements(lambda d: 'FOMC' in ev.get(d, set()), return_dtype=pl.Boolean).alias('fomc'),
        pl.col('session').map_elements(lambda d: bool(ev.get(d, set()) & {'CPI', 'NFP'}), return_dtype=pl.Boolean).alias('cpi_nfp'),
        pl.col('session').map_elements(regime.is_month_end, return_dtype=pl.Boolean).alias('month_end')).sort('root', 'session')
    df.write_parquet(os.path.join(OUT, 'sessions.parquet')); print(df.group_by('root').agg(pl.len(), pl.col('fomc').sum(), pl.col('month_end').sum()))

def event_rows(g, kind):
    """each event day's x, I and R against the median over its previous 20 event-free sessions"""
    g = g.sort('session'); ses = g['session'].to_list()
    plain = (~g['fomc'] & ~g['cpi_nfp'] & ~g['month_end']).to_list()
    x, I, R = g['x'].to_numpy(), g['I'].to_numpy(), g['R'].to_numpy()
    is_ev = (g['fomc'] if kind == 'FOMC' else (g['month_end'] & ~g['fomc'])).to_list()
    out = []
    for i, e in enumerate(is_ev):
        if not e: continue
        ctrl = [j for j in range(i - 1, -1, -1) if plain[j]][:20]
        if len(ctrl) < 20: continue
        out.append(dict(session=ses[i], d=float(x[i] - np.median(x[ctrl])), implied_multiple=float(I[i] / np.median(I[ctrl])),
                        realised_multiple=float(R[i] / np.median(R[ctrl])), x=float(x[i]), x_ctrl=float(np.median(x[ctrl]))))
    return pl.DataFrame(out)

def boot(v, B=10000, seed=9):
    v = np.asarray(v, float); rng = np.random.default_rng(seed)
    b = v[rng.integers(0, len(v), size=(B, len(v)))].mean(1)
    return float(v.mean()), float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975)), float(max((b <= 0).mean(), 1 / B))

def analyze():
    D = pl.read_parquet(os.path.join(OUT, 'sessions.parquet'))
    rows = []
    for root in ROOTS:
        g = D.filter(pl.col('root') == root)
        for kind in ('FOMC', 'month-end'):
            E = event_rows(g, kind)
            if E.height < 5: continue
            m, lo, hi, p = boot(E['d'].to_numpy())
            rows.append(dict(root=root, event=kind, days=E.height, diff_log=m, lo=lo, hi=hi, p_one_sided=p, ratio=float(np.exp(m)),
                             implied_multiple_median=float(E['implied_multiple'].median()), realised_multiple_median=float(E['realised_multiple'].median()),
                             realised_over_implied_event=float(np.exp(E['x'].median())), realised_over_implied_control=float(np.exp(E['x_ctrl'].median()))))
            E.write_csv(os.path.join(OUT, f'events_{root}_{kind}.csv'))
    R = pl.DataFrame(rows)
    prim = R.filter(pl.col('root') == 'SPXW').sort('p_one_sided'); k = prim.height; holm = {}; run = 0.0
    for i, (e, p) in enumerate(prim.select('event', 'p_one_sided').iter_rows()): run = max(run, min(1.0, (k - i) * p)); holm[e] = run
    R = R.with_columns(pl.when(pl.col('root') == 'SPXW').then(pl.col('event').replace_strict(holm, default=None)).otherwise(None).alias('p_holm_spxw'))
    R.write_csv(os.path.join(OUT, 'tests.csv')); pl.Config.set_tbl_cols(16); pl.Config.set_tbl_width_chars(250); print(R)

if __name__ == '__main__':
    {'build': build, 'analyze': analyze}[sys.argv[1]]()
