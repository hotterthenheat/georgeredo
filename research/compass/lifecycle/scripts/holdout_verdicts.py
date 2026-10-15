"""Score every hold-out finalist against the six promotion rules (protocol §6) from the hold-out rows and the
development grid: (1) expectancy > 0 with the bootstrap one-sided p below the Holm threshold across the finalists;
(2) real minus random-minute control, paired lower bound > 0; (3) profit factor > 1; (4) >= 100 trades on >= 60
sessions; (5) still > 0 at +$0.01 a side and with 1-minute latency; (6) development plateau: the median expectancy of
the same family's policies on the same cell > 0."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
from lc import analyze as an, reports as rp, paths, policies as pol

R = f'{paths.RESULTS}/tier1'
H = pl.read_parquet(f'{paths.WORK}/holdout_rows.parquet')
t = pl.read_csv(f'{R}/holdout_finalists.csv')
fin = pl.read_csv(f'{R}/finalists.csv').filter(pl.col('qualifies'))
real = H.filter(pl.col('ctrl') == -1)
boot = an.Boot(H['session'].to_list(), B=10000, seed=17)
fam = {n: f for n, f, _ in pol.grid()}
grid_dev = pl.read_csv(f'{R}/grid_by_setup.csv').filter(pl.col('period') == 'dev')
rows = []
for r in fin.iter_rows(named=True):
    base = f"{r['frozen_policy']}|base"
    sub = real.filter((pl.col('setup') == r['setup']) & (pl.col('structure') == r['structure']) & (pl.col('pname') == base))
    d = rp.rows_to_daily(sub, ['setup'])
    cell, M = boot.mat(d, ['setup'], ['n', 'pnl'])
    est, lo, hi, b = boot.ratio_ci(M['pnl'], M['n'])
    p_one = float(np.mean(b[:, 0] <= 0))
    tr = t.filter((pl.col('setup') == r['setup']) & (pl.col('structure') == r['structure']))
    g = lambda v: tr.filter(pl.col('pname') == f"{r['frozen_policy']}|{v}").row(0, named=True)
    gb = g('base'); gs = g('slip1'); gl = g('lat1')
    fam_dev = grid_dev.filter((pl.col('setup') == r['setup']) & (pl.col('structure') == r['structure']) & (pl.col('family') == fam[r['frozen_policy']]))
    plateau = float(fam_dev['exp'].median()) if fam_dev.height else float('nan')
    rows.append({'setup': r['setup'], 'structure': r['structure'], 'policy': r['frozen_policy'], 'n': gb['n'], 'days': gb['days'], 'exp': gb['exp'],
                 'exp_lo': gb['exp_lo'], 'p_one_sided': p_one, 'pf': gb['profit_factor'], 'edge_vs_rnd': gb['edge_vs_rnd'], 'edge_lo': gb['edge_lo'],
                 'exp_slip1': gs['exp'], 'exp_lat1': gl['exp'], 'dev_family_median': plateau, 'win_rate': gb['win_rate'], 'ret_on_premium': gb['ret_on_premium'],
                 'worst_usd': gb['worst_usd']})
v = pl.DataFrame(rows).sort('p_one_sided')
k = v.height
holm = [0.05 / (k - i) for i in range(k)]
passed_so_far = True; r1 = []
for i, p in enumerate(v['p_one_sided'].to_list()):
    ok = passed_so_far and p <= holm[i]; r1.append(ok); passed_so_far = ok
v = v.with_columns(pl.Series('holm_threshold', holm), pl.Series('R1_exp_holm', r1),
                   (pl.col('edge_lo') > 0).alias('R2_beats_random'), (pl.col('pf') > 1).alias('R3_pf'),
                   ((pl.col('n') >= 100) & (pl.col('days') >= 60)).alias('R4_sample'),
                   ((pl.col('exp_slip1') > 0) & (pl.col('exp_lat1') > 0)).alias('R5_execution'),
                   (pl.col('dev_family_median') > 0).alias('R6_plateau'))
v = v.with_columns(pl.all_horizontal(['R1_exp_holm', 'R2_beats_random', 'R3_pf', 'R4_sample', 'R5_execution', 'R6_plateau']).alias('PROMOTED'))
v.write_csv(f'{R}/holdout_verdicts.csv')
pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(250)
print(v.select(['setup', 'structure', 'policy', 'n', 'exp', 'p_one_sided', 'holm_threshold', 'R1_exp_holm', 'R2_beats_random', 'R3_pf', 'R4_sample', 'R5_execution', 'R6_plateau', 'PROMOTED']))
