"""Amendment L-A2 §3 (post hoc): the six hold-out finalists' R2 re-scored against RND-after (a random later minute,
same session, same direction, same structure and frozen policy). Reported beside the original R2; it cannot promote a
configuration (R1 had already failed for all six)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
from lc import analyze as an, policies as pol, paths

R = f'{paths.RESULTS}/tier1'
fin = ('M13_tpnone_s15', 'M13_tpnone_s20', 'M0_expiry', 'M13_tp25_snone')
pset = [p for p in pol.grid() if p[0] in fin]
d = an.load_daily('ctrl_after_holdout', holdout=True, policy_set=pset)
boot = an.Boot(d['session'].to_list(), B=10000, seed=29)
v = pl.read_csv(f'{R}/holdout_verdicts.csv')
rows = []
for r in v.iter_rows(named=True):
    sub = d.filter((pl.col('setup') == r['setup']) & (pl.col('structure') == r['structure']) & (pl.col('pname') == r['policy']))
    def arm(c):
        g = sub.filter(pl.col('ctrl') == c).group_by('session').agg(pl.col('n').sum(), pl.col('pnl').sum())
        N = np.zeros(len(boot.days)); P = np.zeros(len(boot.days))
        for s, n, p in zip(g['session'].to_list(), g['n'].to_list(), g['pnl'].to_list()): N[boot.ix[s]] += n; P[boot.ix[s]] += p
        return P.sum() / max(N.sum(), 1e-9), (boot.W @ P) / np.maximum(boot.W @ N, 1e-9), N.sum()
    ea, ba, na = arm(0); eb, bb, nb = arm(1)
    dd = ba - bb
    rows.append({'setup': r['setup'], 'structure': r['structure'], 'policy': r['policy'], 'n': na, 'exp': ea, 'n_rnd_after': nb, 'exp_rnd_after': eb,
                 'edge_after': ea - eb, 'lo': float(np.nanquantile(dd, 0.025)), 'hi': float(np.nanquantile(dd, 0.975)), 'p_one_sided': float(np.mean(dd <= 0)),
                 'R2_original_edge': r['edge_vs_rnd'], 'R2_original_lo': r['edge_lo'], 'R2_after_pass': bool(np.nanquantile(dd, 0.025) > 0)})
out = pl.DataFrame(rows)
out.write_csv(f'{R}/holdout_r2_after.csv')
pl.Config.set_tbl_width_chars(220); pl.Config.set_tbl_cols(16)
print(out)
