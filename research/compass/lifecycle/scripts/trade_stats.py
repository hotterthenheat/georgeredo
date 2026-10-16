"""Trade statistics for every cell of the setup x option type matrix, on the management rule the cell is scored on
(its best policy), development + validation, one contract: trades, average trade, average win, average loss, biggest
win, biggest loss and win rate. Read from the per-trade rows: stage1 (same day), vol_best (volatility and Fed-day
setups) and dbest (the daily tier; both from scripts/run_best_rows.py). Before anything is written, every cell's trade
count, expectancy and win rate are checked against the published cells (stage1_cells.csv, vol/cells.csv,
tier_d/cells.csv); a mismatch stops the script.

  python3 -I scripts/trade_stats.py      -> results/matrix/trade_stats.csv
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import paths, runner, daily_runner as dr

R, W = paths.RESULTS, f'{paths.WORK}/runs'
M = f'{R}/matrix'
PNL = pl.col('pnl')
AGG = [pl.len().alias('n'), (PNL > 0).sum().alias('wins'), PNL.sum().alias('pnl'),
       pl.when(PNL > 0).then(PNL).otherwise(0).sum().alias('win_pnl'), pl.when(PNL < 0).then(PNL).otherwise(0).sum().alias('loss_pnl'),
       PNL.max().alias('best'), PNL.min().alias('worst')]

def per_root(stage, root, pos_cols, cutoff, extra=None):
    d = f'{W}/{stage}/{root}'
    names = json.load(open(f'{d}/run.json'))['policies']            # the policy index is the position in the run's own list
    o = pl.scan_parquet(f'{d}/outcomes.parquet').select('pos_id', 'policy', 'filled', 'pnl')
    p = pl.scan_parquet(f'{d}/positions.parquet').select(['pos_id', 'session', 'ctrl'] + pos_cols)
    p = p.filter((pl.col('ctrl') == -1) & (pl.col('session') < cutoff))
    j = o.join(p, on='pos_id', how='inner').filter(pl.col('filled') > 0)
    j = j.with_columns(pl.col('policy').cast(pl.Int64).replace_strict(dict(enumerate(names)), return_dtype=pl.Utf8).alias('pname'))
    if extra is not None: j = j.with_columns(extra)
    return j

def combine(frames, keys):
    df = pl.concat(frames).group_by(keys).agg(pl.col('n').sum(), pl.col('wins').sum(), pl.col('pnl').sum(), pl.col('win_pnl').sum(),
                                              pl.col('loss_pnl').sum(), pl.col('best').max(), pl.col('worst').min())
    return df.with_columns((pl.col('pnl') / pl.col('n')).alias('avg_trade'), (pl.col('wins') / pl.col('n')).alias('win_rate'),
                           (pl.col('win_pnl') / pl.col('wins')).alias('avg_win'), (pl.col('loss_pnl') / (pl.col('n') - pl.col('wins'))).alias('avg_loss'))

def check(stats, cells, keys, label):
    j = stats.join(cells.select(keys + [pl.col('n').alias('n_pub'), pl.col('exp').alias('exp_pub'), pl.col('win_rate').alias('wr_pub')]), on=keys, how='inner')
    bad = j.filter(((pl.col('n') - pl.col('n_pub')).abs() > 0.5) | ((pl.col('avg_trade') - pl.col('exp_pub')).abs() > 0.01 + 1e-4 * pl.col('exp_pub').abs())
                   | ((pl.col('win_rate') - pl.col('wr_pub')).abs() > 1e-4))
    print(f'{label}: {j.height} cells compared, {bad.height} differ; max |n diff| {(j["n"] - j["n_pub"]).abs().max()}, '
          f'max |avg trade diff| {(j["avg_trade"] - j["exp_pub"]).abs().max():.6f}, max |win rate diff| {(j["win_rate"] - j["wr_pub"]).abs().max():.2e}')
    if bad.height: print(bad.head(10)); raise SystemExit(f'{label}: trade rows do not reproduce the published cells')

out = []
# same day, the 12 setups (stage1 per-row outcomes)
k1 = ['setup', 'structure', 'pname']
fr = [per_root('stage1', r, ['setup', 'structure'], runner.HOLDOUT_START).group_by(k1).agg(AGG).collect() for r in ('SPY', 'QQQ', 'IWM', 'SPXW')]
s1 = combine(fr, k1)
check(s1, pl.read_csv(f'{R}/tier1/stage1_cells.csv').filter(pl.col('period') == 'all'), k1, 'same day')
t1 = pl.read_csv(f'{M}/tier1_matrix.csv').select('setup', 'structure', pl.col('best_policy').alias('pname'))
out.append(t1.join(s1, on=k1, how='left').with_columns(pl.lit('I').alias('tier'), pl.lit('0DTE').alias('bucket'), pl.lit('index_etf').alias('group')))
# same day, volatility and Fed-day setups
fr = [per_root('vol_best', r, ['setup', 'structure'], runner.HOLDOUT_START).group_by(k1).agg(AGG).collect() for r in ('SPY', 'QQQ', 'IWM', 'SPXW')]
sv = combine(fr, k1)
check(sv, pl.read_csv(f'{R}/vol/cells.csv').filter(pl.col('period') == 'all'), k1, 'volatility setups')
tv = pl.read_csv(f'{M}/tier1_vol_matrix.csv').select('setup', 'structure', pl.col('best_policy').alias('pname'))
out.append(tv.join(sv, on=k1, how='left').with_columns(pl.lit('I').alias('tier'), pl.lit('0DTE').alias('bucket'), pl.lit('index_etf').alias('group')))
# the daily tier
kd = ['group', 'setup', 'bucket', 'structure', 'pname']
fr = []
for r in ('SPY', 'QQQ', 'IWM', 'FB'):
    g = 'index_etf' if r in ('SPY', 'QQQ', 'IWM') else 'single'
    fr.append(per_root('dbest', r, ['setup', 'bucket', 'structure'], dr.HOLDOUT_START, pl.lit(g).alias('group')).group_by(kd).agg(AGG).collect())
sd = combine(fr, kd)
check(sd, pl.read_csv(f'{R}/tier_d/cells.csv').filter((pl.col('side') == 'real') & (pl.col('period') == 'all')), kd, 'daily tier')
td = pl.read_csv(f'{M}/tier_d_matrix.csv').select('group', 'setup', 'bucket', 'structure', pl.col('best_policy').alias('pname'))
out.append(td.join(sd, on=kd, how='left').with_columns(pl.lit('D').alias('tier')))

T = pl.concat(out, how='diagonal_relaxed').select('tier', 'group', 'setup', 'bucket', 'structure', 'pname', 'n', 'avg_trade', 'avg_win', 'avg_loss', 'best', 'worst', 'win_rate')
missing = T.filter(pl.col('n').is_null())
print(f'cells {T.height}, without trade rows {missing.height}')
if missing.height: print(missing)
T.write_csv(f'{M}/trade_stats.csv'); print('wrote', f'{M}/trade_stats.csv')
