"""Per-ticker playbook (descriptive, development + validation only; the hold-outs are not read). For every ticker the
lifecycle archive holds, writes results/playbook/:
  day_shape.csv       when the session's high and low form on the underlying, and the day's range (0DTE tickers)
  after_entry.csv     how far a position ran up and down after a setup's entry, against a random later minute (0DTE)
  entry_hour.csv      the spread paid and what holding to the 15:30 cutoff returned, by the hour of entry (0DTE)
  exits.csv           every management policy's dollars per trade by ticker and structure, development and validation
  exits_random.csv    the same policies on random later-minute entries (the clean control), where it was run
  daily_after.csv     the daily tier's run-up and drawdown by ticker, expiry bucket and structure
  daily_exits.csv     the daily tier's management policies by ticker, bucket and structure
The best and worst points are hindsight (no rule could know them in advance); only the policy tables are executable."""
import os, sys, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
from lc import analyze as an, paths, runner, chainmat, daily_runner as dr

OUT = f'{paths.RESULTS}/playbook'; os.makedirs(OUT, exist_ok=True)
RUNS = f'{paths.WORK}/runs'
ROOTS = ['SPY', 'QQQ', 'IWM', 'SPXW']
DROOTS = ['SPY', 'QQQ', 'IWM', 'FB']
SUMS = ('n', 'wins', 'pnl', 'win_pnl', 'loss_pnl', 'cost', 'capital', 'hold', 'fees')
LOTS = ('lot_initial', 'lot_add', 'lot_dd', 'lot_scale', 'partial1', 'partial2', 'runner')
def log(m): print(m, flush=True)
def split_i(d): return 'dev' if d <= an.DEV_END else 'val'
def split_d(d): return 'dev' if d <= dr.DEV_END else 'val'

# 1. the day's high and low on the underlying, full sessions before the hold-out
rows = []
for root in ROOTS:
    for s in chainmat.sessions_0dte(root):
        if s >= runner.HOLDOUT_START or chainmat.cal.is_early_close(s): continue
        try: spot, hi, lo = chainmat.underlying_path(root, s, 391)
        except Exception: continue
        if not np.isfinite(spot[0]) or np.isnan(hi[1:]).all(): continue
        H, L = np.nanmax(hi[1:]), np.nanmin(lo[1:])
        th, tl = int(np.nanargmax(hi[1:])), int(np.nanargmin(lo[1:]))      # minutes after 09:30 at which the bar closed
        rows.append({'root': root, 'session': s, 'open': spot[0], 'high': H, 'low': L, 'close': spot[-1], 't_high': th, 't_low': tl,
                     'or30_has_high': bool(np.nanmax(hi[1:31]) >= H), 'or30_has_low': bool(np.nanmin(lo[1:31]) <= L)})
D = pl.DataFrame(rows).with_columns(((pl.col('high') - pl.col('low')) / pl.col('open') * 100).alias('range_pct'),
                                    ((pl.col('close') - pl.col('low')) / (pl.col('high') - pl.col('low'))).alias('close_loc'))
def share(c): return c.mean()
ds = D.group_by('root').agg(
    pl.len().alias('sessions'), pl.col('session').min().alias('first'), pl.col('session').max().alias('last'),
    pl.col('range_pct').median().alias('range_med'), pl.col('range_pct').quantile(0.25).alias('range_p25'),
    pl.col('range_pct').quantile(0.75).alias('range_p75'), pl.col('range_pct').quantile(0.9).alias('range_p90'),
    (pl.col('t_high') < 30).mean().alias('high_first30'), (pl.col('t_high') >= 330).mean().alias('high_last60'),
    (pl.col('t_low') < 30).mean().alias('low_first30'), (pl.col('t_low') >= 330).mean().alias('low_last60'),
    (pl.col('or30_has_high') | pl.col('or30_has_low')).mean().alias('first30_has_high_or_low'),
    (pl.col('or30_has_high') & pl.col('or30_has_low')).mean().alias('first30_has_both'),
    ((pl.col('t_high') >= 120) & (pl.col('t_high') < 270)).mean().alias('high_midday_1130_1400'),
    ((pl.col('t_low') >= 120) & (pl.col('t_low') < 270)).mean().alias('low_midday_1130_1400'),
    (pl.col('t_high') < pl.col('t_low')).mean().alias('high_before_low'),
    pl.col('close_loc').median().alias('close_location_med')).sort('root')
ds.write_csv(f'{OUT}/day_shape.csv')
D.with_columns((pl.col('t_high') // 30).alias('hb'), (pl.col('t_low') // 30).alias('lb')).group_by('root').agg(
    *[(pl.col('hb') == k).mean().alias(f'high_{9 + (30 + 30 * k) // 60}:{(30 + 30 * k) % 60:02d}') for k in range(13)],
    *[(pl.col('lb') == k).mean().alias(f'low_{9 + (30 + 30 * k) // 60}:{(30 + 30 * k) % 60:02d}') for k in range(13)]).sort('root').write_csv(f'{OUT}/day_shape_by_half_hour.csv')
log('day shape written')

# 2. after a setup's entry against a random later minute: hindsight best and worst, and value at the cutoff
def after(pos, side):
    p = pos.filter(pl.col('skip').is_null() & (pl.col('cost0').abs() >= 1.0))
    c = pl.col('cost0').abs()
    return p.with_columns((pl.col('mfe_liq') / c).fill_nan(None).alias('best'), (pl.col('mae_liq') / c).fill_nan(None).alias('worst'),
                          (pl.col('liq_cutoff') / c).fill_nan(None).alias('cut')).group_by(['root', 'structure']).agg(
        pl.len().alias('n'), pl.col('cost0').median().alias('cost_med'), pl.col('rel_spread').median().alias('spread_med'),
        pl.col('best').median().alias('best_med'), pl.col('best').quantile(0.75).alias('best_p75'),
        (pl.col('best') >= 0.25).mean().alias('reach_25'), (pl.col('best') >= 0.5).mean().alias('reach_50'), (pl.col('best') >= 1.0).mean().alias('reach_100'),
        pl.col('t_mfe').median().alias('min_to_best_med'),
        pl.col('worst').median().alias('worst_med'), pl.col('worst').quantile(0.25).alias('worst_p25'),
        (pl.col('worst') <= -0.5).mean().alias('hit_minus50'), (pl.col('worst') <= -0.9).mean().alias('hit_minus90'),
        pl.col('t_mae').median().alias('min_to_worst_med'), (pl.col('t_mfe') < pl.col('t_mae')).mean().alias('best_came_first'),
        pl.col('cut').median().alias('at_cutoff_med'), pl.col('cut').mean().alias('at_cutoff_mean'), (pl.col('cut') > 0).mean().alias('green_at_cutoff'),
    ).with_columns(pl.lit(side).alias('entries'))
aft, hrs = [], []
for root in ROOTS:
    cols = ['session', 'ctrl', 'setup', 'structure', 'm', 'skip', 'cost0', 'rel_spread', 'mfe_liq', 't_mfe', 'mae_liq', 't_mae', 'liq_cutoff']
    real = pl.read_parquet(f'{RUNS}/grid/{root}/positions.parquet', columns=cols).filter(pl.col('ctrl') < 0).with_columns(pl.lit(root).alias('root'))
    rnd = pl.read_parquet(f'{RUNS}/ctrl_after/{root}/positions.parquet', columns=cols).filter(pl.col('ctrl') >= 0).with_columns(pl.lit(root).alias('root'))
    aft += [after(real, 'setup'), after(rnd, 'random later minute')]
    for side, p in (('setup', real), ('random later minute', rnd)):
        p = p.filter(pl.col('skip').is_null() & (pl.col('cost0').abs() >= 1.0)).with_columns(((pl.col('m') + 30) // 60 + 9).alias('hour'),
                                                                                           pl.col('liq_cutoff').fill_nan(None))
        hrs.append(p.group_by(['root', 'structure', 'hour']).agg(pl.len().alias('n'), pl.col('rel_spread').median().alias('spread_med'),
                   (pl.col('liq_cutoff') / pl.col('cost0').abs()).mean().alias('held_to_cutoff_mean'),
                   (pl.col('liq_cutoff') > 0).mean().alias('green_at_cutoff'), pl.col('liq_cutoff').mean().alias('held_to_cutoff_usd')).with_columns(pl.lit(side).alias('entries')))
pl.concat(aft).sort(['root', 'structure', 'entries']).write_csv(f'{OUT}/after_entry.csv')
pl.concat(hrs).sort(['root', 'structure', 'entries', 'hour']).write_csv(f'{OUT}/entry_hour.csv')
log('after entry written')

# 3. every management policy by ticker and structure (setup entries; pooled over setups), development and validation
ex, exr = [], []
for root in ROOTS:
    for stage, out, ctrl in (('grid', ex, 0), ('ctrl_after', exr, 1)):
        f = f'{RUNS}/{stage}/{root}/daily.parquet'
        if not os.path.exists(f): continue
        pol = json.load(open(f'{RUNS}/{stage}/{root}/run.json'))['policies']
        d = pl.scan_parquet(f).filter(pl.col('ctrl') == ctrl).collect()
        lots = [c for c in LOTS if c in d.columns]
        d = d.group_by(['session', 'structure', 'policy']).agg([pl.col(c).sum() for c in SUMS + tuple(lots)])
        d = d.with_columns(pl.col('policy').map_elements(lambda i: pol[i], return_dtype=pl.Utf8).alias('pname'),
                           pl.col('session').map_elements(split_i, return_dtype=pl.Utf8).alias('split'))
        boot = an.Boot(d['session'].to_list(), B=1000)
        for sp in ('dev', 'val'):
            sub = d.filter(pl.col('split') == sp)
            t = an.cell_table(sub, ['structure', 'pname'], boot)
            if lots:
                lt = sub.group_by(['structure', 'pname']).agg([(pl.col(c).sum() / pl.col('n').sum()).alias(f'{c}_per_trade') for c in lots])
                t = t.join(lt, on=['structure', 'pname'], how='left')
            out.append(t.with_columns(pl.lit(root).alias('root'), pl.lit(sp).alias('split')))
    log(f'exits {root}')
keep = ['root', 'structure', 'pname', 'split', 'n', 'days', 'exp', 'exp_lo', 'exp_hi', 'win_rate', 'avg_win', 'avg_loss', 'ret_on_premium', 'hold_min', 'fees_per_trade']
X = pl.concat(ex, how='diagonal_relaxed')
X.select(keep + [c for c in X.columns if c.endswith('_per_trade') and c != 'fees_per_trade']).sort(['root', 'structure', 'split', 'pname']).write_csv(f'{OUT}/exits.csv')
pl.concat(exr, how='diagonal_relaxed').select(keep).sort(['root', 'structure', 'split', 'pname']).write_csv(f'{OUT}/exits_random.csv')

# 4. the daily tier (Weekly .. LEAPS), by ticker
names = [p[0] for p in dr.daily_policies()]
da, dx = [], []
for root in DROOTS:
    f = f'{RUNS}/drows/{root}/positions.parquet'
    if os.path.exists(f):
        p = pl.read_parquet(f).filter(pl.col('skip').is_null() & (pl.col('session') < dr.HOLDOUT_START) & (pl.col('cost0').abs() >= 1.0))
        o = pl.read_parquet(f'{RUNS}/drows/{root}/outcomes.parquet', columns=['pos_id', 'policy', 'pnl'])
        rp = list(dr.ROWS_POLICIES)
        o = o.filter(pl.col('policy') == rp.index('D0_expiry')).select(['pos_id', pl.col('pnl').alias('expiry_pnl')])
        p = p.join(o, on='pos_id', how='left').with_columns(pl.when(pl.col('ctrl') < 0).then(pl.lit('setup')).otherwise(pl.lit('random day')).alias('entries'))
        c = pl.col('cost0').abs()
        da.append(p.with_columns((pl.col('mfe_liq') / c).alias('best'), (pl.col('mae_liq') / c).alias('worst'), (pl.col('expiry_pnl') / c).fill_nan(None).alias('exp_pct'))
                  .group_by(['bucket', 'structure', 'entries']).agg(
                      pl.len().alias('n'), pl.col('dte').median().alias('dte_med'), pl.col('cost0').median().alias('cost_med'),
                      pl.col('best').median().alias('best_med'), (pl.col('best') >= 0.5).mean().alias('reach_50'), (pl.col('best') >= 1.0).mean().alias('reach_100'),
                      pl.col('t_mfe').median().alias('sessions_to_best_med'), pl.col('worst').median().alias('worst_med'),
                      (pl.col('worst') <= -0.5).mean().alias('hit_minus50'), (pl.col('t_mfe') < pl.col('t_mae')).mean().alias('best_came_first'),
                      pl.col('exp_pct').median().alias('held_to_expiry_med'), pl.col('exp_pct').mean().alias('held_to_expiry_mean'))
                  .with_columns(pl.lit(root).alias('root')))
    f = f'{RUNS}/dgrid/{root}/daily.parquet'
    if os.path.exists(f):
        d = pl.read_parquet(f).filter((pl.col('ctrl') == 0) & (pl.col('session') < dr.HOLDOUT_START))
        d = d.with_columns(pl.col('setup').str.split('|').list.get(1).alias('bucket'),
                           pl.col('policy').map_elements(lambda i: names[i], return_dtype=pl.Utf8).alias('pname'),
                           pl.col('session').map_elements(split_d, return_dtype=pl.Utf8).alias('split'))
        d = d.group_by(['session', 'bucket', 'structure', 'pname', 'split']).agg([pl.col(c).sum() for c in SUMS])
        boot = an.Boot(d['session'].to_list(), B=1000)
        for sp in ('dev', 'val'):
            t = an.cell_table(d.filter(pl.col('split') == sp), ['bucket', 'structure', 'pname'], boot)
            dx.append(t.with_columns(pl.lit(root).alias('root'), pl.lit(sp).alias('split')))
    log(f'daily {root}')
pl.concat(da).sort(['root', 'bucket', 'structure', 'entries']).write_csv(f'{OUT}/daily_after.csv')
pl.concat(dx, how='diagonal_relaxed').select(['root', 'bucket', 'structure', 'pname', 'split', 'n', 'days', 'exp', 'exp_lo', 'exp_hi', 'win_rate', 'ret_on_premium']) \
    .sort(['root', 'bucket', 'structure', 'split', 'pname']).write_csv(f'{OUT}/daily_exits.csv')
log('done')
