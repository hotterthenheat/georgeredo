"""Tier D analysis (daily lifecycles), development (<= 2021) and validation (2022-2023) only; the hold-out (2024 ->) is
not read. Writes results/tier_d/: setup x bucket x structure x policy cells (real and control), real-minus-control,
policy against holding to expiry, the dev-chosen policy's validation result, and a yearly walk-forward."""
import os, sys, json, time, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import datetime as dt
import numpy as np
import polars as pl
from lc import analyze as an, reports as rp, paths, daily_runner as dr

OUT = os.environ.get('TIERD_OUT', f'{paths.RESULTS}/tier_d'); os.makedirs(OUT, exist_ok=True)
roots = sys.argv[1].split(',') if len(sys.argv) > 1 else sorted(os.listdir(f'{paths.WORK}/runs/dgrid'))
t0 = time.time()
def log(m): print(f'{time.time() - t0:6.0f}s {m}', flush=True)
MIN_N = 30   # a comparison is reported only when both sides have at least 30 trades (cells with 0-29 gave spurious intervals)
names = [p[0] for p in dr.daily_policies()]; fams = {p[0]: p[1] for p in dr.daily_policies()}
def split_of(d): return 'dev' if d <= dr.DEV_END else ('val' if d <= dr.VAL_END else 'holdout')
fr = []
for r in roots:
    f = f'{paths.WORK}/runs/dgrid/{r}/daily.parquet'
    if os.path.exists(f): fr.append(pl.read_parquet(f).with_columns(pl.lit(r).alias('root')))
daily = pl.concat(fr).filter(pl.col('session') < dr.HOLDOUT_START)
daily = daily.with_columns(pl.col('setup').str.split('|').list.get(0).alias('setup0'), pl.col('setup').str.split('|').list.get(1).alias('bucket'))
daily = daily.drop('setup').rename({'setup0': 'setup'})
daily = daily.with_columns(pl.col('policy').map_elements(lambda i: names[i], return_dtype=pl.Utf8).alias('pname'),
                           pl.col('session').map_elements(split_of, return_dtype=pl.Utf8).alias('split'),
                           pl.col('root').is_in(['SPY', 'QQQ', 'IWM']).map_elements(lambda x: 'index_etf' if x else 'single', return_dtype=pl.Utf8).alias('group'))
log(f'daily rows {daily.height} roots {daily["root"].n_unique()}')
boot = an.Boot(daily['session'].to_list(), B=1000)
keys = ['group', 'setup', 'bucket', 'structure', 'pname']
cells = []
for side, cv in (('real', 0), ('ctrl', 1)):
    for per in ('dev', 'val', 'all'):
        sub = daily.filter(pl.col('ctrl') == cv)
        if per != 'all': sub = sub.filter(pl.col('split') == per)
        if sub.height == 0: continue
        cells.append(an.cell_table(sub, keys, boot).with_columns(pl.lit(side).alias('side'), pl.lit(per).alias('period')))
cells = pl.concat(cells, how='diagonal_relaxed')
cells.write_csv(f'{OUT}/cells.csv')
log('cells written')
# real minus random-session control (directional setups only have controls)
sub = daily.with_columns(pl.when(pl.col('ctrl') == 0).then(pl.lit('real')).otherwise(pl.lit('ctrl')).alias('side'))
pr = an.paired(sub, keys, {'side': 'real'}, {'side': 'ctrl'}, boot)
pr.filter((pl.col('n_a') >= MIN_N) & (pl.col('n_b') >= MIN_N)).write_csv(f'{OUT}/real_vs_control.csv')
# each directional setup against the all-days control with the same bucket, structure and policy: bullish structures
# against D_ALLL (every Monday, long), bearish against D_ALLS. The days differ, so the bootstrap resamples calendar days
# over both sides (not a same-day pairing). This separates timing from the market's drift over the period.
BULL = ('LC-S', 'LC-B', 'DCS', 'CPS', 'CSP'); BEAR = ('LP-S', 'LP-B', 'DPS')
vs = []
# each policy against holding to expiry (debit and straddle) or D13_expiry (credit), real events
pairs = []
real = daily.filter(pl.col('ctrl') == 0)
for pname in real['pname'].unique().to_list():
    for ref in ('D0_expiry',):
        if pname == ref: continue
        a = real.filter(pl.col('pname') == pname).drop('pname', 'policy'); b = real.filter(pl.col('pname') == ref).drop('pname', 'policy')
        both = pl.concat([a.with_columns(pl.lit('a').alias('arm')), b.with_columns(pl.lit('b').alias('arm'))], how='diagonal_relaxed')
        p = an.paired(both, ['group', 'bucket', 'structure'], {'arm': 'a'}, {'arm': 'b'}, boot).with_columns(pl.lit(pname).alias('pname'), pl.lit(ref).alias('ref'))
        pairs.append(p)
pl.concat(pairs).write_csv(f'{OUT}/policy_vs_expiry.csv')
real = daily.filter(pl.col('ctrl') == 0)
for setup in ('D_TP', 'D_BO', 'D_BOF', 'D_BN', 'D_BNF'):
    for ref, structs in (('D_ALLL', BULL), ('D_ALLS', BEAR)):
        sub = real.filter(pl.col('setup').is_in([setup, ref]) & pl.col('structure').is_in(list(structs)))
        if sub.filter(pl.col('setup') == setup).height == 0: continue
        vs.append(an.paired(sub, ['group', 'bucket', 'structure', 'pname'], {'setup': setup}, {'setup': ref}, boot).with_columns(pl.lit(setup).alias('setup'), pl.lit(ref).alias('ref')))
if vs: pl.concat(vs).filter((pl.col('n_a') >= MIN_N) & (pl.col('n_b') >= MIN_N)).write_csv(f'{OUT}/setup_vs_alldays.csv')
log('policy pairs written')
# dev choice -> validation
dv = cells.filter((pl.col('side') == 'real') & (pl.col('period') == 'dev') & (pl.col('n') >= 100))
best = dv.sort('exp_lo', descending=True).group_by(['group', 'setup', 'bucket', 'structure'], maintain_order=True).first()
val = cells.filter((pl.col('side') == 'real') & (pl.col('period') == 'val')).select(['group', 'setup', 'bucket', 'structure', 'pname', 'n', 'exp', 'exp_lo', 'exp_hi', 'win_rate', 'ret_on_premium'])
best.select(['group', 'setup', 'bucket', 'structure', 'pname', 'n', 'exp', 'exp_lo', 'win_rate']).join(val, on=['group', 'setup', 'bucket', 'structure', 'pname'], how='left', suffix='_val').write_csv(f'{OUT}/dev_choice_then_val.csv')
# yearly walk-forward 2018 .. 2023: a policy chosen per cell on all earlier years
wf_rows = []; ch_rows = []
for y in range(2018, 2024):
    tr = real.filter(pl.col('session') < dt.date(y, 1, 1))
    te = real.filter((pl.col('session') >= dt.date(y, 1, 1)) & (pl.col('session') <= dt.date(y, 12, 31)))
    if tr.height == 0 or te.height == 0: continue
    bt = an.Boot(tr['session'].to_list(), B=300)
    t = an.cell_table(tr, ['group', 'setup', 'bucket', 'structure', 'pname'], bt).filter(pl.col('n') >= 100)
    b = t.sort('exp_lo', descending=True).group_by(['group', 'setup', 'bucket', 'structure'], maintain_order=True).first()
    ch_rows.append(b.select(['group', 'setup', 'bucket', 'structure', 'pname', 'n', 'exp', 'exp_lo']).with_columns(pl.lit(y).alias('year')))
    sel = te.join(b.select(['group', 'setup', 'bucket', 'structure', 'pname']), on=['group', 'setup', 'bucket', 'structure', 'pname'])
    wf_rows.append(sel.with_columns(pl.lit(y).alias('year')))
if wf_rows:
    W = pl.concat(wf_rows)
    bw = an.Boot(W['session'].to_list(), B=1000)
    an.cell_table(W, ['group', 'setup', 'bucket', 'structure'], bw).write_csv(f'{OUT}/walkforward_oos.csv')
    pl.concat(ch_rows).write_csv(f'{OUT}/walkforward_choices.csv')
json.dump({'roots': roots, 'daily_rows': daily.height, 'cells': cells.height, 'configurations': int(daily.select(['group', 'setup', 'bucket', 'structure', 'pname']).unique().height)},
          open(f'{OUT}/counts.json', 'w'), indent=1)
log('done')
