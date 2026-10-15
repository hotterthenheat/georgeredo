"""Result A for the daily tier (hindsight, development + validation): for every debit structure bought at a session's
close, the best liquidation value before expiry (best bid for the structure, in sessions) against what holding to
expiry or selling at the session before the last trading day returned. Retrospective: no rule could know the best day."""
import os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import paths, daily_runner as dr

INDEX = ('SPY', 'QQQ', 'IWM')
fr = []
for d in sorted(glob.glob(f'{paths.WORK}/runs/drows/*')):
    root = os.path.basename(d)
    if not os.path.exists(f'{d}/positions.parquet') or not os.path.exists(f'{d}/outcomes.parquet'): continue
    p = pl.read_parquet(f'{d}/positions.parquet').filter(pl.col('skip').is_null() & (pl.col('ctrl') < 0) & (pl.col('session') < dr.HOLDOUT_START))
    o = pl.read_parquet(f'{d}/outcomes.parquet')
    pol_names = list(dr.ROWS_POLICIES)
    o = o.with_columns(pl.col('policy').map_elements(lambda i: pol_names[i], return_dtype=pl.Utf8).alias('pname')).filter(pl.col('pname').is_in(['D0_expiry', 'D0_ltd1']))
    o = o.pivot(index='pos_id', on='pname', values='pnl')
    x = p.join(o, on='pos_id', how='left').with_columns(pl.lit(root).alias('root'))
    fr.append(x.select(['root', 'session', 'setup', 'bucket', 'structure', 'cost0', 'mfe_liq', 't_mfe', 'mae_liq', 'dte'] + [c for c in ('D0_expiry', 'D0_ltd1') if c in x.columns]))
X = pl.concat(fr, how='diagonal_relaxed').filter(pl.col('cost0') > 0)          # debit structures (a credit's cost0 is negative)
X = X.with_columns(pl.when(pl.col('root').is_in(list(INDEX))).then(pl.lit('index_etf')).otherwise(pl.lit('single')).alias('group'),
                   (pl.col('mfe_liq') / pl.col('cost0')).alias('best_pct'), (pl.col('D0_expiry') / pl.col('cost0')).alias('expiry_pct'),
                   (pl.col('D0_ltd1') / pl.col('cost0')).alias('ltd1_pct'))
t = X.group_by(['group', 'bucket', 'structure']).agg(pl.len().alias('entries'), pl.col('best_pct').mean().alias('best_exit_mean'),
                                                     (pl.col('best_pct') >= 0.5).mean().alias('reached_plus50'), pl.col('t_mfe').median().alias('median_sessions_to_best'),
                                                     pl.col('ltd1_pct').mean().alias('sold_day_before_ltd'), pl.col('expiry_pct').mean().alias('held_to_expiry'))
t = t.sort(['group', 'structure', 'bucket'])
os.makedirs(f'{paths.RESULTS}/tier_d', exist_ok=True)
t.write_csv(f'{paths.RESULTS}/tier_d/result_A.csv')
pl.Config.set_tbl_rows(80); pl.Config.set_tbl_width_chars(200)
print(t.with_columns([pl.col(c).round(3) for c in ('best_exit_mean', 'reached_plus50', 'sold_day_before_ltd', 'held_to_expiry')]))
