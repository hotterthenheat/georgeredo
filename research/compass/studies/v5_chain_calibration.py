"""V5 (amendment A12): are the same-day chain's prices calibrated? One-strike OTM verticals, realised payoff minus mid price
per unit width, by distance in implied moves; SPXW primary, SPY/QQQ/IWM alongside.

  python3 -I v5_chain_calibration.py build        # pairs.parquet (one row a vertical, session and decision time)
  python3 -I v5_chain_calibration.py analyze      # development, validation, previously analysed; the four tests
"""
import datetime as dt, os, sys
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', 'lifecycle'))
import numpy as np, polars as pl
from engine import calendar as cal

OUT = os.path.join(HERE, '..', 'results', 'v1', 'v5_chain_calibration'); os.makedirs(OUT, exist_ok=True)
ROOTS = ['SPXW', 'SPY', 'QQQ', 'IWM']
TIMES = {30: '10:00', 210: '13:00'}
FEE = 0.70
DEV_END, VAL_END, PREV_END = dt.date(2024, 12, 31), dt.date(2025, 9, 30), dt.date(2026, 10, 9)
BUCKETS = [(0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0)]

def tick(root, p): return (0.05 if p < 3 else 0.10) if root == 'SPXW' else 0.01

def split(d): return 'dev' if d <= DEV_END else ('val' if d <= VAL_END else ('prev' if d <= PREV_END else 'forward'))

def one(args):
    root, sess = args
    from lc.chainmat import load_0dte
    cd = load_0dte(root, sess)
    if cd is None or cd.n_min != 391: return []
    ST = cd.spot[390]
    if not np.isfinite(ST): return []
    rows = []
    for t, tl in TIMES.items():
        S = cd.spot[t]
        if not np.isfinite(S): continue
        b, a = cd.bid[:, t], cd.ask[:, t]
        ok = np.isfinite(b) & np.isfinite(a) & (b > 0) & (a >= b)
        mid = np.where(ok, (a + b) / 2, np.nan); rel = np.where(ok, (a - b) / mid, np.nan)
        use = ok & (rel <= 0.20)
        # implied move from the ATM straddle (strike nearest S with both legs two-sided)
        calls = {k: i for i, (k, c) in enumerate(zip(cd.strike, cd.is_call)) if c}
        puts = {k: i for i, (k, c) in enumerate(zip(cd.strike, cd.is_call)) if not c}
        both = [k for k in calls if k in puts and ok[calls[k]] and ok[puts[k]]]
        if not both: continue
        K0 = min(both, key=lambda k: (abs(k - S), k))
        m = (mid[calls[K0]] + mid[puts[K0]]) / S
        if not (m > 0): continue
        hi_after = np.nanmax(np.r_[cd.spot[t + 1:391], cd.spot_hi[t + 1:391]]); lo_after = np.nanmin(np.r_[cd.spot[t + 1:391], cd.spot_lo[t + 1:391]])
        for side, book in (('call', calls), ('put', puts)):
            ks = sorted(book)
            for k1, k2 in zip(ks[:-1], ks[1:]):
                i1, i2 = book[k1], book[k2]
                if not (use[i1] and use[i2]): continue
                if side == 'call' and k1 < S: continue
                if side == 'put' and k2 > S: continue
                w = k2 - k1
                if side == 'call':
                    price = (mid[i1] - mid[i2]) / w; real = min(max(ST - k1, 0.0), w) / w
                    sell = (b[i1] - a[i2]) / w; buy = (a[i1] - b[i2]) / w; touch = float(hi_after >= k1)
                    sell_adv = (max(b[i1] - tick(root, b[i1]), 0) - a[i2] - tick(root, a[i2])) / w
                    buy_adv = (a[i1] + tick(root, a[i1]) - max(b[i2] - tick(root, b[i2]), 0)) / w
                else:
                    price = (mid[i2] - mid[i1]) / w; real = min(max(k2 - ST, 0.0), w) / w
                    sell = (b[i2] - a[i1]) / w; buy = (a[i2] - b[i1]) / w; touch = float(lo_after <= k2)
                    sell_adv = (max(b[i2] - tick(root, b[i2]), 0) - a[i1] - tick(root, a[i1])) / w
                    buy_adv = (a[i2] + tick(root, a[i2]) - max(b[i1] - tick(root, b[i1]), 0)) / w
                fee = 2 * FEE / (100 * w)
                d = np.log(((k1 + k2) / 2) / S) / m
                rows.append(dict(root=root, session=sess, time=tl, side=side, k1=k1, k2=k2, width=w, spot=S, settle=ST, implied_move=m, dist=float(d),
                                 price=price, realised=real, edge_mid=real - price, seller_net=sell - real - fee, buyer_net=real - buy - fee,
                                 seller_net_adv=sell_adv - real - fee, buyer_net_adv=real - buy_adv - fee, touch=touch))
    return rows

def build():
    from lc.chainmat import sessions_0dte
    jobs = [(r, s) for r in ROOTS for s in sessions_0dte(r) if not cal.is_early_close(s)]
    print(len(jobs), 'chain-days', flush=True)
    out = []
    import multiprocessing as mp                                    # spawn: never fork a process that has started polars' threads
    with ProcessPoolExecutor(int(os.environ.get('V5_PROCS', '3')), mp_context=mp.get_context('spawn')) as ex:
        for i, r in enumerate(ex.map(one, jobs, chunksize=8)):
            out.extend(r)
            if (i + 1) % 500 == 0: print(i + 1, len(out), flush=True)
    df = pl.DataFrame(out).with_columns(pl.col('session').map_elements(split, return_dtype=pl.Utf8).alias('split'),
                                        pl.col('dist').abs().alias('absd'))
    df.write_parquet(os.path.join(OUT, 'pairs.parquet')); print('pairs', df.height)

def sess_level(df, col):
    """one value per session: the mean over that session's verticals"""
    return df.group_by('session').agg(pl.col(col).mean().alias('v')).sort('session')   # a fixed order: the same seed, the same draws

def boot(df, col, B=10000, seed=9):
    s = sess_level(df, col)['v'].drop_nans().to_numpy()
    if len(s) < 20: return len(s), np.nan, np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed); b = s[rng.integers(0, len(s), size=(B, len(s)))].mean(1)
    p = 2 * min((b <= 0).mean(), (b >= 0).mean())
    return len(s), float(s.mean()), float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975)), float(max(p, 1 / B))

def analyze():
    P = pl.read_parquet(os.path.join(OUT, 'pairs.parquet'))
    band = (pl.col('absd') > 0.5) & (pl.col('absd') <= 1.5)
    rows = []
    for t in TIMES.values():
        for side in ('put', 'call'):
            for sp, f in (('devval', pl.col('split').is_in(['dev', 'val'])), ('dev', pl.col('split') == 'dev'), ('val', pl.col('split') == 'val'), ('prev (previously analysed)', pl.col('split') == 'prev')):
                d = P.filter((pl.col('root') == 'SPXW') & (pl.col('time') == t) & (pl.col('side') == side) & band & f)
                r = dict(time=t, side=side, split=sp, pairs=d.height)
                for col in ('edge_mid', 'seller_net', 'buyer_net', 'seller_net_adv', 'buyer_net_adv'):
                    n, m, lo, hi, p = boot(d, col)
                    r.update({f'{col}': m, f'{col}_lo': lo, f'{col}_hi': hi, **({'sessions': n, 'p_edge': p} if col == 'edge_mid' else {})})
                r['price_mean'] = float(d['price'].mean()) if d.height else np.nan; r['realised_mean'] = float(d['realised'].mean()) if d.height else np.nan
                rows.append(r)
    T = pl.DataFrame(rows)
    prim = T.filter(pl.col('split') == 'devval').sort('p_edge'); k = prim.height; holm = {}; run = 0.0
    for i, (t, s, p) in enumerate(prim.select('time', 'side', 'p_edge').iter_rows()): run = max(run, min(1.0, (k - i) * p)); holm[(t, s)] = run
    T = T.with_columns(pl.struct('time', 'side').map_elements(lambda x: holm.get((x['time'], x['side'])), return_dtype=pl.Float64).alias('p_holm_devval'))
    T.write_csv(os.path.join(OUT, 'tests.csv')); pl.Config.set_tbl_rows(40); pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300)
    print(T.select('time', 'side', 'split', 'sessions', 'pairs', 'price_mean', 'realised_mean', 'edge_mid', 'edge_mid_lo', 'edge_mid_hi', 'p_edge', 'p_holm_devval',
                   'seller_net', 'seller_net_lo', 'seller_net_hi', 'buyer_net', 'buyer_net_lo', 'buyer_net_hi'))
    # descriptive curve: every root, time, side, bucket and split
    cur = []
    for (root, t, side, sp), g in P.group_by(['root', 'time', 'side', 'split']):
        for lo_b, hi_b in BUCKETS:
            d = g.filter((pl.col('absd') > lo_b) & (pl.col('absd') <= hi_b))
            if d.height == 0: continue
            n, m, lo, hi, _ = boot(d, 'edge_mid', B=2000)
            sn, sm, slo, shi, _ = boot(d, 'seller_net', B=2000)
            cur.append(dict(root=root, time=t, side=side, split=sp, bucket=f'{lo_b}-{hi_b}', sessions=n, pairs=d.height, price=float(d['price'].mean()), realised=float(d['realised'].mean()),
                            edge_mid=m, edge_lo=lo, edge_hi=hi, seller_net=sm, seller_lo=slo, seller_hi=shi, touch=float(d['touch'].mean()),
                            touch_over_2price=float(d['touch'].mean() / (2 * d['price'].mean())) if d['price'].mean() > 0 else np.nan))
    C = pl.DataFrame(cur).sort('root', 'time', 'side', 'split', 'bucket'); C.write_csv(os.path.join(OUT, 'curve.csv'))
    print(C.filter(pl.col('root') == 'SPXW').filter(pl.col('split').is_in(['dev', 'val'])))

def band():
    """the 0.5-1.5 implied-move band on every root, development + validation (descriptive outside SPXW)"""
    P = pl.read_parquet(os.path.join(OUT, 'pairs.parquet'))
    f = (pl.col('absd') > 0.5) & (pl.col('absd') <= 1.5) & pl.col('split').is_in(['dev', 'val'])
    rows = []
    for root in ROOTS:
        for t in TIMES.values():
            for side in ('put', 'call'):
                d = P.filter((pl.col('root') == root) & (pl.col('time') == t) & (pl.col('side') == side) & f)
                n, m, lo, hi, _ = boot(d, 'edge_mid'); _, sm, slo, shi, _ = boot(d, 'seller_net'); _, bm, blo, bhi, _ = boot(d, 'buyer_net')
                rows.append(dict(root=root, time=t, side=side, sessions=n, price=float(d['price'].mean()), realised=float(d['realised'].mean()), edge=m, edge_lo=lo, edge_hi=hi,
                                 seller=sm, seller_lo=slo, seller_hi=shi, buyer=bm, buyer_lo=blo, buyer_hi=bhi))
    R = pl.DataFrame(rows); R.write_csv(os.path.join(OUT, 'band_all_roots_devval.csv')); print(R)

if __name__ == '__main__':
    {'build': build, 'analyze': analyze, 'band': band}[sys.argv[1]]()
