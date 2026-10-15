"""V6 (amendment A13): do price levels hold more often than distance-matched placebo levels?
  python3 -I v6_levels.py build                 # levels.parquet: every real level and its five placebos
  python3 -I v6_levels.py analyze [--holdout]
"""
import datetime as dt, json, math, os, sys, zlib
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import numpy as np, polars as pl
from engine import calendar as cal
import pa_atlas as A

OUT = os.path.join(HERE, '..', 'results', 'v1', 'v6_levels'); os.makedirs(OUT, exist_ok=True)
DEV_END, VAL_END = dt.date(2021, 12, 31), dt.date(2024, 12, 31)
NPLACEBO, ZMAX = 5, 3.0

def split_of(d): return 'dev' if d <= DEV_END else ('val' if d <= VAL_END else 'holdout')

def unit(p):
    """the largest of {1, 2.5, 5} x 10^j not above 0.5 % of p"""
    best = None
    for j in range(-3, 6):
        for k in (1, 2.5, 5):
            u = k * 10 ** j
            if u <= 0.005 * p and (best is None or u > best): best = u
    return best

def outcome(H, L, c, p, lvl):
    """touched after 10:00 and held (the close stays on p's side) for one level on one session"""
    if lvl > p: t = H[30:].max() >= lvl; held = t and c <= lvl
    else: t = L[30:].min() <= lvl; held = t and c >= lvl
    return bool(t), bool(held)

def name_rows(sym):
    S, G = A.grid(sym)
    if len(S) < 300: return []
    O, H, L, C = G['open'], G['high'], G['low'], G['close']
    op, cl, hi, lo = O[:, 0], C[:, -1], H.max(1), L.min(1)
    prev_hi = np.r_[np.nan, hi[:-1]]; prev_lo = np.r_[np.nan, lo[:-1]]; prev_cl = np.r_[np.nan, cl[:-1]]
    consec = np.r_[False, np.array([cal.prev_session(S[i]) == S[i - 1] for i in range(1, len(S))])]
    ratio = op / prev_cl
    split = np.array([np.isfinite(x) and any(abs(x / f - 1) <= 0.10 for f in A.SPLITS) for x in ratio])
    okprev = consec & ~split
    p10 = C[:, 29]; r = np.log(cl / p10)
    sig = np.full(len(S), np.nan)
    for i in range(20, len(S)): sig[i] = np.sqrt(np.nanmean(r[i - 20:i] ** 2))
    valid = np.where(np.isfinite(sig) & (sig > 0) & np.isfinite(p10))[0]
    rng = np.random.default_rng(zlib.crc32(sym.encode()))      # fixed per name: the placebos are the same on every run
    rows = []
    for i in valid:
        p = p10[i]; levels = []
        if okprev[i]:
            if prev_hi[i] > p: levels.append(('A', 'above', prev_hi[i]))
            if prev_lo[i] < p: levels.append(('A', 'below', prev_lo[i]))
        u = unit(p)
        ra = math.floor(p / u + 1e-9) * u + u; rb = math.ceil(p / u - 1e-9) * u - u
        levels += [('B', 'above', ra), ('B', 'below', rb)]
        for fam, side, lvl in levels:
            z = math.log(lvl / p) / sig[i]
            if abs(z) > ZMAX: continue
            t, h = outcome(H[i], L[i], cl[i], p, lvl)
            others = valid[valid != i]
            pick = rng.choice(others, size=NPLACEBO, replace=False)
            pt, ph = [], []
            for j in pick:
                l2 = p10[j] * math.exp(z * sig[j])
                a, b = outcome(H[j], L[j], cl[j], p10[j], l2); pt.append(a); ph.append(b)
            rows.append(dict(symbol=sym, session=S[i], split=split_of(S[i]), family=fam, side=side, z=z, touched=t, held=h,
                             p_touched=float(np.mean(pt)), p_held=float(np.mean(ph)), p_n_touched=int(np.sum(pt)), p_n_held=int(np.sum(ph))))
    return rows

def build():
    syms = sorted(A.ROOTS)
    out = []
    import multiprocessing as mp                                    # spawn: the parent has started polars' threads (a fork can hang)
    with ProcessPoolExecutor(int(os.environ.get('V6_PROCS', '3')), mp_context=mp.get_context('spawn')) as ex:
        for sym, r in zip(syms, ex.map(name_rows, syms)):
            out.extend(r); print(sym, len(r), flush=True)
    df = pl.DataFrame(out); df.write_parquet(os.path.join(OUT, 'levels.parquet')); print('levels', df.height)

def held_share(d):
    """real: held among touched; placebo: held among touched placebos (counts pooled)"""
    rt = d['touched'].sum(); rh = d['held'].sum(); pt = d['p_n_touched'].sum(); ph = d['p_n_held'].sum()
    return (rh / rt if rt else np.nan), (ph / pt if pt else np.nan)

def boot(d, B=10000, seed=9):
    g = d.group_by('session').agg(pl.col('touched').sum().alias('rt'), pl.col('held').sum().alias('rh'), pl.col('p_n_touched').sum().alias('pt'), pl.col('p_n_held').sum().alias('ph')).sort('session')
    rt, rh, pt, ph = (g[c].to_numpy().astype(float) for c in ('rt', 'rh', 'pt', 'ph'))
    real, plac = rh.sum() / rt.sum(), ph.sum() / pt.sum()
    rng = np.random.default_rng(seed); idx = rng.integers(0, len(rt), size=(B, len(rt)))
    diff = rh[idx].sum(1) / rt[idx].sum(1) - ph[idx].sum(1) / pt[idx].sum(1)
    return dict(levels=d.height, touched=int(rt.sum()), real_held=real, placebo_held=plac, diff=real - plac,
                lo=float(np.quantile(diff, 0.025)), hi=float(np.quantile(diff, 0.975)), p_one_sided=float(max((diff <= 0).mean(), 1 / B)),
                real_touch_rate=float(d['touched'].mean()), placebo_touch_rate=float(d['p_touched'].mean()))

def analyze(holdout=False):
    D = pl.read_parquet(os.path.join(OUT, 'levels.parquet'))
    if holdout:
        flag = os.path.join(OUT, 'holdout_opened.json')
        if os.path.exists(flag): print('hold-out already opened:', open(flag).read())
        else: json.dump({'opened_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}, open(flag, 'w'))
    else: D = D.filter(pl.col('split') != 'holdout')
    rows = []
    for fam in ('A', 'B'):
        for sp in ['devval', 'dev', 'val'] + (['holdout'] if holdout else []):
            d = D.filter(pl.col('family') == fam)
            d = d.filter(pl.col('split') != 'holdout') if sp == 'devval' else d.filter(pl.col('split') == sp)
            rows.append(dict(family={'A': 'prior-day high/low', 'B': 'round numbers'}[fam], split=sp, **boot(d)))
    R = pl.DataFrame(rows)
    base = R.filter(pl.col('split') == 'devval').sort('p_one_sided'); k = base.height; holm = {}; run = 0.0
    for i, (f, p) in enumerate(base.select('family', 'p_one_sided').iter_rows()): run = max(run, min(1.0, (k - i) * p)); holm[f] = run
    R = R.with_columns(pl.col('family').replace_strict(holm, default=None).alias('p_holm_devval'))
    tag = '_holdout' if holdout else ''
    R.write_csv(os.path.join(OUT, f'tests{tag}.csv')); pl.Config.set_tbl_cols(16); pl.Config.set_tbl_width_chars(250); print(R)
    # descriptive: by side and distance, by name
    Dd = D if holdout else D
    desc = []
    for (fam, side), g in Dd.group_by(['family', 'side']):
        for lo_z, hi_z in ((0, 0.5), (0.5, 1), (1, 2), (2, 3)):
            d = g.filter(pl.col('z').abs().is_between(lo_z, hi_z, closed='left'))
            if d.height < 200: continue
            r, pp = held_share(d)
            desc.append(dict(family=fam, side=side, distance=f'{lo_z}-{hi_z} sigma', levels=d.height, real_touch=float(d['touched'].mean()), placebo_touch=float(d['p_touched'].mean()), real_held=r, placebo_held=pp))
    X = pl.DataFrame(desc).sort('family', 'side', 'distance'); X.write_csv(os.path.join(OUT, f'by_distance{tag}.csv')); print(X)
    nm = []
    for (sym, fam), g in Dd.group_by(['symbol', 'family']):
        r, pp = held_share(g); nm.append(dict(symbol=sym, family=fam, levels=g.height, real_held=r, placebo_held=pp, diff=r - pp))
    pl.DataFrame(nm).sort('family', 'symbol').write_csv(os.path.join(OUT, f'by_name{tag}.csv'))

if __name__ == '__main__':
    if sys.argv[1] == 'build': build()
    else: analyze('--holdout' in sys.argv)
