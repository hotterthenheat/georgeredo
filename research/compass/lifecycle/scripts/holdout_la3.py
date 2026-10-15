"""Amendment L-A3, run once: QS -> debit call spread held to expiry (M0_expiry) on the hold-out (2025-10-01 ->
2026-10-09), with RND-after controls.
  H-DCS-1  hold-out expectancy > 0 (one-sided bootstrap p < 0.05)
  H-DCS-2  the cell minus RND-after, paired by day (one-sided p < 0.05)
Holm across the two. Refuses a second run (lock file)."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
from lc import runner, policies as pol, analyze as an, chainmat as cm, paths

OUT = f'{paths.RESULTS}/tier1'
LOCK = f'{OUT}/holdout_la3_opened.json'
if os.path.exists(LOCK): sys.exit(f'already run: {open(LOCK).read()}')
pset = [p for p in pol.stage1() if p[0] == 'M0_expiry']
for root in an.ROOTS:
    ss = [d for d in cm.sessions_0dte(root) if d >= runner.HOLDOUT_START]
    runner.run_root(root, 'la3_holdout', pset, sessions=ss, mode='daily', include_holdout=True, setups=('QS',), structures=('DCS',),
                    ctrl_mode='after', log=lambda m: None)
d = an.load_daily('la3_holdout', holdout=True, policy_set=pset)
boot = an.Boot(d['session'].to_list(), B=10000, seed=23)
res = {}
real = d.filter(pl.col('ctrl') == 0)
cell, M = boot.mat(real.with_columns(pl.lit('x').alias('k')), ['k'], ['n', 'pnl'])
est, lo, hi, b = boot.ratio_ci(M['pnl'], M['n'])
res['H-DCS-1'] = {'n': float(real['n'].sum()), 'days': int(real['session'].n_unique()), 'exp': float(est[0]), 'lo': float(lo[0]), 'hi': float(hi[0]),
                  'p_one_sided': float(np.mean(b[:, 0] <= 0)), 'win_rate': float(real['wins'].sum() / max(real['n'].sum(), 1))}
# H-DCS-2: the same paired-difference estimator as every control comparison, with its bootstrap draws for the p-value
def arm(c):
    g = d.filter(pl.col('ctrl') == c).group_by('session').agg(pl.col('n').sum(), pl.col('pnl').sum())
    N = np.zeros(len(boot.days)); P = np.zeros(len(boot.days))
    for s, n, p in zip(g['session'].to_list(), g['n'].to_list(), g['pnl'].to_list()): N[boot.ix[s]] += n; P[boot.ix[s]] += p
    return P.sum() / N.sum(), (boot.W @ P) / (boot.W @ N), N.sum()
ea, ba, na = arm(0); eb, bb, nb = arm(1)
dd = ba - bb
res['H-DCS-2'] = {'exp_cell': float(ea), 'exp_rnd_after': float(eb), 'diff': float(ea - eb), 'lo': float(np.nanquantile(dd, 0.025)), 'hi': float(np.nanquantile(dd, 0.975)),
                  'p_one_sided': float(np.mean(dd <= 0)), 'n_cell': float(na), 'n_ctrl': float(nb)}
ps = sorted((res[t]['p_one_sided'], t) for t in res)
ok = True
for i, (p, t) in enumerate(ps):
    thr = 0.05 / (len(ps) - i); ok = ok and p < thr
    res[t]['holm_threshold'] = thr; res[t]['holm_pass'] = bool(ok)
res['by_root'] = real.group_by('root').agg(pl.col('n').sum(), (pl.col('pnl').sum() / pl.col('n').sum()).alias('exp')).sort('root').to_dicts()
json.dump(res, open(f'{OUT}/holdout_la3.json', 'w'), indent=1, default=str)
json.dump({'opened_utc': dt.datetime.now(dt.timezone.utc).isoformat()}, open(LOCK, 'w'))
print(json.dumps(res, indent=1, default=str))
