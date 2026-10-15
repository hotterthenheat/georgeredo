"""Volatility and Fed-day setups (VOLC, VOLR, EVF against their all-days controls ALL10V, ALL10P, ALL1330), development +
validation only: cells per setup x structure x policy, the flag's value (flagged days minus all days, paired by day),
real minus random-minute controls, and the same quarterly walk-forward finalist rule as Tier I (mechanical; the
hold-out for any finalist is opened by holdout_tier1-style scoring, once)."""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import analyze as an, reports as rp, paths, policies as pol

OUT = f'{paths.RESULTS}/vol'; os.makedirs(OUT, exist_ok=True)
t0 = time.time()
def log(m): print(f'{time.time() - t0:6.0f}s {m}', flush=True)
daily = an.load_daily('vol_grid')
SPLIT = lambda c: pl.when(pl.col(c) <= an.DEV_END).then(pl.lit('dev')).when(pl.col(c) <= an.VAL_END).then(pl.lit('val')).otherwise(pl.lit('holdout'))
daily = daily.with_columns(SPLIT('session').alias('split'))
boot = an.Boot(daily['session'].to_list(), B=1000)
real = daily.filter(pl.col('ctrl') == 0)
cells = pl.concat([an.cell_table(real if p == 'all' else real.filter(pl.col('split') == p), ['setup', 'structure', 'pname', 'family'], boot).with_columns(pl.lit(p).alias('period'))
                   for p in ('all', 'dev', 'val')])
cells.write_csv(f'{OUT}/cells.csv')
log('cells')
# the flag against all days, same structure and policy, paired by day
pairs = []
for flag, base in (('VOLC', 'ALL10V'), ('VOLR', 'ALL10P'), ('EVF', 'ALL1330')):
    sub = real.filter(pl.col('setup').is_in([flag, base]))
    p = an.paired(sub, ['structure', 'pname'], {'setup': flag}, {'setup': base}, boot).with_columns(pl.lit(flag).alias('flag'), pl.lit(base).alias('base'))
    pairs.append(p)
pl.concat(pairs).write_csv(f'{OUT}/flag_vs_alldays.csv')
# real against random minutes on the same sessions
sub = daily.with_columns(pl.when(pl.col('ctrl') == 0).then(pl.lit('real')).otherwise(pl.lit('rnd')).alias('side'))
an.paired(sub, ['setup', 'structure', 'pname'], {'side': 'real'}, {'side': 'rnd'}, boot).write_csv(f'{OUT}/real_vs_random_minute.csv')
log('pairs')
# walk-forward finalists (same rule as Tier I)
choices, oos = an.walk_forward(real, ['setup', 'structure'], 'pname', min_trades=150, B=300)
choices.write_csv(f'{OUT}/walkforward_choices.csv')
fin = []
if oos.height:
    bw = an.Boot(oos['session'].to_list(), B=1000)
    wf = an.cell_table(oos, ['setup', 'structure'], bw); wf.write_csv(f'{OUT}/walkforward_oos.csv')
    full = an.cell_table(real, ['setup', 'structure', 'pname'], boot).filter(pl.col('n') >= 150)
    frozen = full.sort('exp_lo', descending=True).group_by(['setup', 'structure'], maintain_order=True).first()
    for r in wf.filter((pl.col('exp') > 0) & (pl.col('exp_lo') > 0)).sort('exp_lo', descending=True).iter_rows(named=True):
        fz = frozen.filter((pl.col('setup') == r['setup']) & (pl.col('structure') == r['structure']))
        if fz.height == 0: continue
        pn = fz['pname'][0]
        s2 = real.filter((pl.col('setup') == r['setup']) & (pl.col('structure') == r['structure']) & pl.col('pname').is_in([pn, 'M0_cutoff']))
        s2 = s2.with_columns(pl.when(pl.col('pname') == pn).then(pl.lit('a')).otherwise(pl.lit('b')).alias('arm'))
        pr = an.paired(s2, ['setup'], {'arm': 'a'}, {'arm': 'b'}, boot)
        fin.append({'setup': r['setup'], 'structure': r['structure'], 'oos_n': r['n'], 'oos_exp': r['exp'], 'oos_lo': r['exp_lo'], 'frozen_policy': pn,
                    'frozen_exp': fz['exp'][0], 'frozen_lo': fz['exp_lo'][0], 'vs_M0': pr['diff'][0], 'vs_M0_hi': pr['diff_hi'][0],
                    'qualifies': bool(pn == 'M0_cutoff' or pr['diff_hi'][0] >= 0)})
(pl.DataFrame(fin) if fin else pl.DataFrame({'note': ['no cell has a walk-forward out-of-sample lower bound above zero']})).write_csv(f'{OUT}/finalists.csv')
json.dump({'daily_rows': daily.height, 'configurations': int(real.select(['setup', 'structure', 'pname']).unique().height), 'finalists': len(fin)}, open(f'{OUT}/counts.json', 'w'), indent=1)
log(f'done, finalists {len(fin)}')
