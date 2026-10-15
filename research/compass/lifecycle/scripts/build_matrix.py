"""Deliverable 5: every setup x structure cell classified from the result files, never by hand.
Tier I (same-day): stage-1 cells (development + validation), walk-forward, the clean controls (L-A2), the hold-out tests.
Tier D (daily lifecycles): results/tier_d (development + validation; the hold-out where it was opened).

Labels (the first that applies):
  insufficient     fewer than 100 trades or 60 sessions in the cell
  failed           every policy's interval lies below zero, or the walk-forward interval lies below zero
  carry, not setup positive (some policy's lower bound > 0, walk-forward > 0) but not better than a random later minute
                   (RND-after) / a random day in the same direction (Tier D): the structure earns it, not the setup
  promising        positive as above AND better than its clean control (lower bound > 0)
  inconclusive     anything else (intervals span zero)
A promising cell is still not validated: validation needs the hold-out (07_validation.md)."""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import paths

R = f'{paths.RESULTS}/tier1'
MIN_N, MIN_DAYS = 100, 60

def label(n, days, best_lo, best_hi_max, wf_exp, wf_hi, ctrl_lo):
    if n is None or n < MIN_N or (days or 0) < MIN_DAYS: return 'insufficient'
    if (best_hi_max is not None and best_hi_max < 0) or (wf_hi is not None and wf_hi < 0): return 'failed'
    if best_lo is not None and best_lo > 0 and (wf_exp is None or wf_exp > 0):
        return 'promising' if (ctrl_lo is not None and ctrl_lo > 0) else 'carry, not setup'
    return 'inconclusive'

def tier1() -> pl.DataFrame:
    c = pl.read_csv(f'{R}/stage1_cells.csv').filter(pl.col('period') == 'all')
    best = c.sort('exp_lo', descending=True).group_by(['setup', 'structure'], maintain_order=True).first()
    agg = c.group_by(['setup', 'structure']).agg(pl.col('n').max().alias('n_max'), pl.col('days').max().alias('days_max'), pl.col('exp_hi').max().alias('hi_max'))
    wf = pl.read_csv(f'{R}/walkforward_oos.csv').select(['setup', 'structure', pl.col('exp').alias('wf_exp'), pl.col('exp_lo').alias('wf_lo'), pl.col('exp_hi').alias('wf_hi')])
    t = best.select(['setup', 'structure', pl.col('pname').alias('best_policy'), 'exp', 'exp_lo', 'exp_hi', 'win_rate', 'ret_on_premium']).join(agg, on=['setup', 'structure']).join(wf, on=['setup', 'structure'], how='left')
    cs = f'{R}/controls_summary.csv'
    if os.path.exists(cs):
        k = pl.read_csv(cs).select(['setup', 'structure', pl.col('pname').alias('best_policy'), 'edge_after', 'after_lo', 'after_hi', 'edge_flip', 'flip_lo', 'flip_hi'])
        t = t.join(k, on=['setup', 'structure', 'best_policy'], how='left')
    else:
        t = t.with_columns([pl.lit(None, pl.Float64).alias(x) for x in ('edge_after', 'after_lo', 'after_hi', 'edge_flip', 'flip_lo', 'flip_hi')])
    rows = []
    for r in t.iter_rows(named=True):
        rows.append({**r, 'tier': 'I (0DTE)', 'bucket': '0DTE',
                     'label': label(r['n_max'], r['days_max'], r['exp_lo'], r['hi_max'], r['wf_exp'], r['wf_hi'], r['after_lo'])})
    return pl.DataFrame(rows, infer_schema_length=None)

def tier_d() -> pl.DataFrame | None:
    D = f'{paths.RESULTS}/tier_d'
    if not os.path.exists(f'{D}/cells.csv'): return None
    c = pl.read_csv(f'{D}/cells.csv').filter((pl.col('side') == 'real') & (pl.col('period') == 'all'))
    keys = ['group', 'setup', 'bucket', 'structure']
    best = c.sort('exp_lo', descending=True).group_by(keys, maintain_order=True).first()
    agg = c.group_by(keys).agg(pl.col('n').max().alias('n_max'), pl.col('days').max().alias('days_max'), pl.col('exp_hi').max().alias('hi_max'))
    t = best.select(keys + [pl.col('pname').alias('best_policy'), 'exp', 'exp_lo', 'exp_hi', 'win_rate', 'ret_on_premium']).join(agg, on=keys)
    if os.path.exists(f'{D}/walkforward_oos.csv'):
        wf = pl.read_csv(f'{D}/walkforward_oos.csv').select(keys + [pl.col('exp').alias('wf_exp'), pl.col('exp_lo').alias('wf_lo'), pl.col('exp_hi').alias('wf_hi')])
        t = t.join(wf, on=keys, how='left')
    if os.path.exists(f'{D}/real_vs_control.csv'):
        rc = pl.read_csv(f'{D}/real_vs_control.csv').select(keys + [pl.col('pname').alias('best_policy'), pl.col('diff').alias('edge_ctrl'), pl.col('diff_lo').alias('ctrl_lo'), pl.col('diff_hi').alias('ctrl_hi')])
        t = t.join(rc, on=keys + ['best_policy'], how='left')
    rows = []
    for r in t.iter_rows(named=True):
        rows.append({**r, 'tier': 'D (daily)', 'label': label(r['n_max'], r['days_max'], r['exp_lo'], r['hi_max'], r.get('wf_exp'), r.get('wf_hi'), r.get('ctrl_lo'))})
    return pl.DataFrame(rows, infer_schema_length=None)

if __name__ == '__main__':
    out = f'{paths.RESULTS}/matrix'; os.makedirs(out, exist_ok=True)
    a = tier1(); a.write_csv(f'{out}/tier1_matrix.csv')
    print(a.group_by('label').len().sort('label'))
    b = tier_d()
    if b is not None:
        b.write_csv(f'{out}/tier_d_matrix.csv'); print(b.group_by('label').len().sort('label'))
