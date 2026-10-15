"""EXPLORATORY, run after V7's result (A15 says so): the 13:00 ATM same-day straddle bought at the ask and held to the
16:00 settlement, on month-end afternoons (not FOMC) and on every fifth ordinary afternoon, SPXW, SPY, QQQ, 2022 -> 2026-10.
It generated V8's hypothesis; it is never evidence for it.
  python3 -I v7_monthend_explore.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, os.path.join(HERE, '..', 'lifecycle'))
import numpy as np, polars as pl
from lc.chainmat import load_0dte
OUT = os.path.join(HERE, '..', 'results', 'v1', 'v7_event_afternoons')
FEE = 0.70

def straddle(root, d):
    cd = load_0dte(root, d); t = 210
    S, ST = cd.spot[t], cd.spot[390]; b, a = cd.bid[:, t], cd.ask[:, t]
    ok = np.isfinite(b) & np.isfinite(a) & (b > 0) & (a >= b)
    calls = {k: i for i, (k, c) in enumerate(zip(cd.strike, cd.is_call)) if c}; puts = {k: i for i, (k, c) in enumerate(zip(cd.strike, cd.is_call)) if not c}
    both = [k for k in calls if k in puts and ok[calls[k]] and ok[puts[k]]]
    K = min(both, key=lambda k: (abs(k - S), k)); ic, ip = calls[K], puts[K]
    mid = (b[ic] + a[ic] + b[ip] + a[ip]) / 2; ask = a[ic] + a[ip]; pay = abs(ST - K)
    return dict(root=root, session=d, mid=mid, ask=ask, pay=pay, r_mid=(pay - mid) / mid, r_ask=(pay - ask - 2 * FEE / 100) / mid)

D = pl.read_parquet(os.path.join(OUT, 'sessions.parquet'))
rows = []
for root in ('SPXW', 'SPY', 'QQQ'):
    g = D.filter((pl.col('root') == root) & pl.col('month_end') & ~pl.col('fomc'))
    rows += [{**straddle(root, d), 'group': 'month-end'} for d in g['session'].to_list()]
    g2 = D.filter((pl.col('root') == root) & ~pl.col('month_end') & ~pl.col('fomc') & ~pl.col('cpi_nfp'))
    rows += [{**straddle(root, d), 'group': 'ordinary (every 5th)'} for d in g2['session'].to_list()[::5]]
X = pl.DataFrame(rows); X.write_parquet(os.path.join(OUT, 'explore_monthend_straddles.parquet'))
rng = np.random.default_rng(9); out = []
for (root, grp), g in X.group_by(['root', 'group'], maintain_order=True):
    for col in ('r_mid', 'r_ask'):
        v = g[col].to_numpy(); b = v[rng.integers(0, len(v), size=(10000, len(v)))].mean(1)
        out.append(dict(root=root, group=grp, col=col, days=len(v), mean=float(v.mean()), lo=float(np.quantile(b, .025)), hi=float(np.quantile(b, .975)), median=float(np.median(v))))
R = pl.DataFrame(out); R.write_csv(os.path.join(OUT, 'explore_monthend_straddles.csv')); print(R)
