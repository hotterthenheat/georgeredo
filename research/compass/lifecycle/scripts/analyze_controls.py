"""Amendment L-A2: each setup x structure x stage-1 policy against the two clean controls, development + validation.
  after  the setup minus a random later minute in the same direction (paired by day, 5 seeds pooled)
  flip   the setup minus the opposite direction at the same minute: the setup's structure against its mirror
         (LC-S vs LP-S, LC-B vs LP-B, DCS vs DPS) on the same events
Writes results/tier1/controls_after.csv, controls_flip.csv and controls_summary.csv (the two beside the original
window control from stage1_cells.csv)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import analyze as an, policies as pol, paths

OUT = f'{paths.RESULTS}/tier1'
MIRROR = {'LC-S': 'LP-S', 'LP-S': 'LC-S', 'LC-B': 'LP-B', 'LP-B': 'LC-B', 'DCS': 'DPS', 'DPS': 'DCS'}
s1 = pol.stage1()
res = {}
for mode in ('after', 'flip'):
    d = an.load_daily(f'ctrl_{mode}', policy_set=s1)
    if mode == 'flip':
        # a flip row carries the mirrored structure: label it with the structure of the event it mirrors
        d = d.with_columns(pl.when(pl.col('ctrl') == 1).then(pl.col('structure').replace(MIRROR)).otherwise(pl.col('structure')).alias('structure'))
        d = d.filter(pl.col('structure').is_in(list(MIRROR)))
    boot = an.Boot(d['session'].to_list(), B=2000)
    t = an.paired(d, ['setup', 'structure', 'pname'], {'ctrl': 0}, {'ctrl': 1}, boot)
    t = t.rename({'exp_a': 'exp_setup', 'exp_b': f'exp_{mode}', 'diff': f'edge_{mode}', 'diff_lo': f'{mode}_lo', 'diff_hi': f'{mode}_hi', 'n_a': 'n', 'n_b': f'n_{mode}'})
    pooled = an.paired(d, ['structure', 'pname'], {'ctrl': 0}, {'ctrl': 1}, boot).with_columns(pl.lit('ALL').alias('setup'))
    pooled = pooled.rename({'exp_a': 'exp_setup', 'exp_b': f'exp_{mode}', 'diff': f'edge_{mode}', 'diff_lo': f'{mode}_lo', 'diff_hi': f'{mode}_hi', 'n_a': 'n', 'n_b': f'n_{mode}'})
    t = pl.concat([t, pooled.select(t.columns)])
    t.write_csv(f'{OUT}/controls_{mode}.csv')
    res[mode] = t
    if mode == 'flip':
        # drift-neutral: a setup's bullish and bearish events together, each against its own mirror. In a rising market a
        # call beats a put at any minute, so the bullish flip is flattered and the bearish one penalised; pooling both
        # directions of the same setup cancels most of that (exactly, when its events are evenly split)
        fam = {'LC-S': 'Steady', 'LP-S': 'Steady', 'LC-B': 'Big Payoff', 'LP-B': 'Big Payoff', 'DCS': 'Debit spread', 'DPS': 'Debit spread'}
        dn = d.with_columns(pl.col('structure').replace(fam).alias('family'))
        fn = an.paired(dn, ['setup', 'family', 'pname'], {'ctrl': 0}, {'ctrl': 1}, boot)
        fp = an.paired(dn, ['family', 'pname'], {'ctrl': 0}, {'ctrl': 1}, boot).with_columns(pl.lit('ALL').alias('setup'))
        fn = pl.concat([fn, fp.select(fn.columns)]).rename({'exp_a': 'exp_setup', 'exp_b': 'exp_flip', 'diff': 'edge_flip_dn', 'diff_lo': 'flip_dn_lo', 'diff_hi': 'flip_dn_hi', 'n_a': 'n', 'n_b': 'n_flip'})
        fn.write_csv(f'{OUT}/controls_flip_drift_neutral.csv')
        print(fn.filter(pl.col('pname') == 'M1_t30').sort(['family', 'setup']))
orig = pl.read_csv(f'{OUT}/stage1_cells.csv').filter(pl.col('period') == 'all').select(['setup', 'structure', 'pname', pl.col('edge_vs_rnd').alias('edge_window'),
                                                                                    pl.col('edge_lo').alias('window_lo'), pl.col('edge_hi').alias('window_hi')])
s = res['after'].join(res['flip'].select(['setup', 'structure', 'pname', 'exp_flip', 'edge_flip', 'flip_lo', 'flip_hi', 'n_flip']), on=['setup', 'structure', 'pname'], how='left')
s = s.join(orig, on=['setup', 'structure', 'pname'], how='left').sort(['pname', 'structure', 'setup'])
s.write_csv(f'{OUT}/controls_summary.csv')
print(s.filter(pl.col('pname') == 'M1_t30').select(['setup', 'structure', 'n', pl.col('exp_setup').round(2), pl.col('edge_after').round(2), pl.col('after_lo').round(1), pl.col('after_hi').round(1),
                                                    pl.col('edge_flip').round(2), pl.col('flip_lo').round(1), pl.col('flip_hi').round(1), pl.col('edge_window').round(1)]))
