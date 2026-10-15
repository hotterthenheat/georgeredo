"""Result A from the contract lifecycle archive (development + validation sessions only): for every 0DTE contract with
|delta| 0.05-0.95 entered at the ask on a 5-minute grid, the hindsight best bid before 15:50 against the executable bid at
fixed horizons and at the cutoff, and the expiry value. Labelled retrospective; no rule could know the best minute."""
import os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import paths, runner
fs = sorted(glob.glob(f'{paths.WORK}/archive/*/*.parquet'))
a = pl.scan_parquet(fs).filter(pl.col('session') < runner.HOLDOUT_START)
a = a.with_columns([
    pl.col('delta0').abs().cut([0.15, 0.30, 0.45, 0.60, 0.80], labels=['0.05-0.15', '0.15-0.30', '0.30-0.45', '0.45-0.60', '0.60-0.80', '0.80-0.95']).alias('delta_bin'),
    pl.when(pl.col('m') < 90).then(pl.lit('a 09:35-11:00')).when(pl.col('m') < 270).then(pl.lit('b 11:00-14:00')).otherwise(pl.lit('c 14:00-15:45')).alias('tod'),
    ((pl.col('best_bid') - pl.col('ask0')) / pl.col('ask0')).alias('hind_best'),
    ((pl.col('best_mid') - pl.col('mid0')) / pl.col('mid0')).alias('hind_best_mid'),
    ((pl.col('liq15') - pl.col('ask0')) / pl.col('ask0')).alias('r15'), ((pl.col('liq30') - pl.col('ask0')) / pl.col('ask0')).alias('r30'),
    ((pl.col('liq60') - pl.col('ask0')) / pl.col('ask0')).alias('r60'), ((pl.col('liq_cut') - pl.col('ask0')) / pl.col('ask0')).alias('rcut'),
    ((pl.col('settle') - pl.col('ask0')) / pl.col('ask0')).alias('rexp'),
    ((pl.col('worst_bid') - pl.col('ask0')) / pl.col('ask0')).alias('hind_worst'),
])
a = a.with_columns([pl.col(c).fill_nan(None) for c in ('hind_best', 'hind_best_mid', 'r15', 'r30', 'r60', 'rcut', 'rexp', 'hind_worst')])
keys = ['root', 'right', 'delta_bin', 'tod']
out = a.group_by(keys).agg([
    pl.len().alias('entries'), pl.col('session').n_unique().alias('days'), pl.col('ask0').median().alias('ask_med'), pl.col('rel_spread0').median().alias('rel_spread_med'),
    pl.col('hind_best').mean().alias('A_best_exit_mean'), pl.col('hind_best').median().alias('A_best_exit_median'),
    (pl.col('hind_best') >= 0.5).mean().alias('A_share_best_ge_50pct'), (pl.col('hind_best') >= 1.0).mean().alias('A_share_best_ge_100pct'),
    pl.col('t_best').median().alias('A_t_best_median_min'), pl.col('hind_worst').mean().alias('A_worst_mean'), pl.col('t_worst').median().alias('A_t_worst_median_min'),
    pl.col('hind_best_mid').mean().alias('A_best_mid_exit_mean'),
    pl.col('r15').mean().alias('B_hold15_mean'), pl.col('r30').mean().alias('B_hold30_mean'), pl.col('r60').mean().alias('B_hold60_mean'),
    pl.col('rcut').mean().alias('B_to_1550_mean'), pl.col('rexp').mean().alias('B_to_expiry_mean'),
    (pl.col('r30') > 0).mean().alias('B_hold30_win'), (pl.col('rcut') > 0).mean().alias('B_to_1550_win'),
]).sort(keys).collect()
os.makedirs(f'{paths.RESULTS}/archive', exist_ok=True)
out.write_csv(f'{paths.RESULTS}/archive/result_A_by_delta_tod.csv')
pooled = a.group_by(['right', 'delta_bin']).agg([pl.len().alias('entries'), pl.col('hind_best').mean().alias('A_best_exit_mean'), (pl.col('hind_best') >= 0.5).mean().alias('A_share_best_ge_50pct'),
    pl.col('r30').mean().alias('B_hold30_mean'), pl.col('rcut').mean().alias('B_to_1550_mean'), pl.col('rexp').mean().alias('B_to_expiry_mean'), pl.col('rel_spread0').median().alias('rel_spread_med')]).sort(['right', 'delta_bin']).collect()
pooled.write_csv(f'{paths.RESULTS}/archive/result_A_pooled.csv')
pl.Config.set_tbl_rows(30); pl.Config.set_tbl_cols(12); pl.Config.set_tbl_width_chars(220)
print(pooled.with_columns([pl.col(c).round(3) for c in pooled.columns if pooled.schema[c] == pl.Float64]))
