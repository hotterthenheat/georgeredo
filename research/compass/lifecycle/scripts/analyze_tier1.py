"""Tier I analysis, development + validation only (the hold-out is not read): the setup x structure baseline matrix with
Result A and the random-entry comparison (stage-1 rows), the management grid against doing nothing (daily sums), the
contributions of partials, runners, adds, double-downs and scale-ins, the warnings, and the walk-forward selection.
Writes CSV/JSON under results/tier1/."""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
from lc import analyze as an, reports as rp, paths, policies as pol

OUT = os.environ.get('TIER1_OUT', f'{paths.RESULTS}/tier1'); os.makedirs(OUT, exist_ok=True)
ROOTS = tuple(sys.argv[1].split(',')) if len(sys.argv) > 1 else an.ROOTS
t0 = time.time()
def log(m): print(f'{time.time() - t0:6.0f}s {m}', flush=True)
counts = {}

# ---------------------------------------------------------------- A. stage 1: setup x structure x policy, real and RND
rows = an.load_rows('stage1', roots=ROOTS)
SPLIT = lambda c: pl.when(pl.col(c) <= an.DEV_END).then(pl.lit('dev')).when(pl.col(c) <= an.VAL_END).then(pl.lit('val')).otherwise(pl.lit('holdout'))
rows = rows.with_columns(SPLIT('session').alias('split'))
log(f'stage-1 rows {rows.height}')
counts['stage1_rows'] = rows.height
real = rows.filter(pl.col('ctrl') == -1); ctrl = rows.filter(pl.col('ctrl') >= 0)
keys = ['setup', 'structure', 'pname']
boot = an.Boot(rows['session'].to_list(), B=1000)
cells = []
for name, sub in (('all', real), ('dev', real.filter(pl.col('split') == 'dev')), ('val', real.filter(pl.col('split') == 'val'))):
    d = rp.rows_to_daily(sub, keys)
    c = an.cell_table(d, keys, boot).join(rp.trade_level(sub, keys), on=keys, how='left').with_columns(pl.lit(name).alias('period'))
    cells.append(c)
cells = pl.concat(cells, how='diagonal_relaxed')
# real minus the random-minute controls (same setup, structure, policy; controls pooled over 5 seeds)
both = pl.concat([rp.rows_to_daily(real, keys).with_columns(pl.lit('real').alias('side')),
                  rp.rows_to_daily(ctrl, keys).with_columns(pl.lit('ctrl').alias('side'))])
pr = an.paired(both, keys, {'side': 'real'}, {'side': 'ctrl'}, boot).rename({'exp_a': 'exp_real', 'exp_b': 'exp_rnd', 'diff': 'edge_vs_rnd', 'diff_lo': 'edge_lo', 'diff_hi': 'edge_hi', 'n_a': 'n_real', 'n_b': 'n_rnd'})
cells = cells.join(pr.select(keys + ['exp_rnd', 'edge_vs_rnd', 'edge_lo', 'edge_hi', 'n_rnd']), on=keys, how='left')
cells.write_csv(f'{OUT}/stage1_cells.csv')
# by root (all periods), M0_cutoff and M1_t30 only
d = rp.rows_to_daily(real.filter(pl.col('pname').is_in(['M0_cutoff', 'M1_t30', 'M2_s35_t50'])), ['root'] + keys)
an.cell_table(d, ['root'] + keys, boot).write_csv(f'{OUT}/stage1_cells_by_root.csv')
log('stage-1 cells written')
# keep only what the later parts read, then free the per-trade frame before the grid is loaded
base_rows = real.select(['root', 'session', 'setup', 'event_i', 'structure', 'pname', 'pnl', 'filled'])
f_rows = real.filter((pl.col('filled') > 0) & pl.col('pname').is_in(['M0_cutoff', 'M1_t30'])).select(
    ['root', 'session', 'setup', 'structure', 'pname', 'm', 'rel_spread', 'filled', 'pnl', 'cost0', 'capital_peak', 'hold_min', 'fees'])
import gc; del rows, real, ctrl, both, d; gc.collect()

# ---------------------------------------------------------------- B. the management grid
daily = an.load_daily('grid', roots=ROOTS)
daily = daily.with_columns(SPLIT('session').alias('split'))
counts['grid_daily_rows'] = daily.height
counts['grid_policies'] = len(pol.grid())
bootg = an.Boot(daily['session'].to_list(), B=1000)
daily = daily.with_columns(pl.col('structure').cast(pl.Utf8).replace_strict({s: pol.kind_of(s) for s in ('LC-S','LP-S','LC-B','LP-B','DCS','DPS','CPS','CSP','STR','STG')}).alias('kind'))
# B1: pooled over setups and roots, by structure x policy, real events and controls
out = []
for side, cv in (('real', 0), ('rnd', 1)):
    sub = daily.filter(pl.col('ctrl') == cv)
    t = an.cell_table(sub, ['structure', 'pname', 'family'], bootg).with_columns(pl.lit(side).alias('side'))
    out.append(t)
grid_cells = pl.concat(out, how='diagonal_relaxed')
# paired against doing nothing (M0_cutoff) on the same events, per structure x policy
pairs = []
for side, cv in (('real', 0), ('rnd', 1)):
    sub = daily.filter(pl.col('ctrl') == cv)
    base = sub.filter(pl.col('pname') == 'M0_cutoff').drop('pname', 'family', 'policy')
    for pname in sub['pname'].unique().to_list():
        if pname == 'M0_cutoff': continue
        x = sub.filter(pl.col('pname') == pname).drop('pname', 'family', 'policy')
        both = pl.concat([x.with_columns(pl.lit('a').alias('arm')), base.with_columns(pl.lit('b').alias('arm'))], how='diagonal_relaxed')
        p = an.paired(both, ['structure'], {'arm': 'a'}, {'arm': 'b'}, bootg).with_columns(pl.lit(pname).alias('pname'), pl.lit(side).alias('side'))
        pairs.append(p)
pairs = pl.concat(pairs).rename({'diff': 'vs_M0', 'diff_lo': 'vs_M0_lo', 'diff_hi': 'vs_M0_hi'})
grid_cells = grid_cells.join(pairs.select(['structure', 'pname', 'side', 'vs_M0', 'vs_M0_lo', 'vs_M0_hi']), on=['structure', 'pname', 'side'], how='left')
# contributions (sums per trade) for the families that split a position
contrib = daily.group_by(['structure', 'pname', 'family', 'ctrl']).agg([pl.col(c).sum() for c in ('n', 'pnl', 'partial1', 'partial2', 'runner', 'lot_initial', 'lot_add', 'lot_dd', 'lot_scale')])
contrib = contrib.with_columns([(pl.col(c) / pl.col('n')).alias(f'{c}_per_trade') for c in ('pnl', 'partial1', 'partial2', 'runner', 'lot_initial', 'lot_add', 'lot_dd', 'lot_scale')])
grid_cells = grid_cells.join(contrib.with_columns(pl.when(pl.col('ctrl') == 0).then(pl.lit('real')).otherwise(pl.lit('rnd')).alias('side')).select(
    ['structure', 'pname', 'side'] + [c for c in contrib.columns if c.endswith('_per_trade')]), on=['structure', 'pname', 'side'], how='left')
grid_cells.write_csv(f'{OUT}/grid_by_structure.csv')
log('grid by structure written')
# B2: per setup x structure x policy (real), dev and val separately
per = []
for split in ('dev', 'val'):
    sub = daily.filter((pl.col('ctrl') == 0) & (pl.col('split') == split))
    per.append(an.cell_table(sub, ['setup', 'structure', 'pname', 'family'], bootg).with_columns(pl.lit(split).alias('period')))
per = pl.concat(per)
per.write_csv(f'{OUT}/grid_by_setup.csv')
log('grid by setup written')
# B3: dev-chosen best policy per setup x structure (by the lower bound, >= 150 trades), then its validation result
dev = per.filter((pl.col('period') == 'dev') & (pl.col('n') >= 150)).sort('exp_lo', descending=True).group_by(['setup', 'structure'], maintain_order=True).first()
val = per.filter(pl.col('period') == 'val').select(['setup', 'structure', 'pname', 'n', 'exp', 'exp_lo', 'exp_hi', 'win_rate', 'ret_on_premium'])
sel = dev.select(['setup', 'structure', 'pname', 'n', 'exp', 'exp_lo', 'win_rate']).join(val, on=['setup', 'structure', 'pname'], how='left', suffix='_val')
sel.write_csv(f'{OUT}/dev_choice_then_val.csv')
# B4: walk-forward, a policy re-chosen each quarter per setup x structure (2024Q1 .. 2025Q3)
choices, oos = an.walk_forward(daily.filter(pl.col('ctrl') == 0), ['setup', 'structure'], 'pname', min_trades=150, B=300)
choices.write_csv(f'{OUT}/walkforward_choices.csv')
if oos.height:
    bw = an.Boot(oos['session'].to_list(), B=1000)
    wf = an.cell_table(oos, ['setup', 'structure'], bw)
    wf.write_csv(f'{OUT}/walkforward_oos.csv')
    allwf = an.cell_table(oos.with_columns(pl.lit('all').alias('all')), ['all'], bw)
    allwf.write_csv(f'{OUT}/walkforward_oos_pooled.csv')
counts['walkforward_quarters'] = choices['quarter'].n_unique() if choices.height else 0
counts['configurations_evaluated_dev_val'] = int(daily.select(['setup', 'structure', 'pname']).unique().height)
json.dump(counts, open(f'{OUT}/counts.json', 'w'), indent=1)
log(f'done {counts}')

# ---------------------------------------------------------------- C. finalists (protocol §6), chosen without the hold-out
# A finalist is a cell (setup x structure) whose walk-forward out-of-sample series (each quarter's policy chosen on data
# before it) has a positive expectancy with a positive day-clustered lower bound, and whose frozen policy (the same rule
# applied to all development + validation data) is not worse than doing nothing on the same events. At most 10, ranked
# by the out-of-sample lower bound.
fin = []
if oos.height:
    wf = pl.read_csv(f'{OUT}/walkforward_oos.csv')
    cand = wf.filter((pl.col('exp') > 0) & (pl.col('exp_lo') > 0))
    allsub = daily.filter(pl.col('ctrl') == 0)
    bt = an.Boot(allsub['session'].to_list(), B=1000)
    full = an.cell_table(allsub, ['setup', 'structure', 'pname'], bt).filter(pl.col('n') >= 150)
    frozen = full.sort('exp_lo', descending=True).group_by(['setup', 'structure'], maintain_order=True).first()
    for r in cand.sort('exp_lo', descending=True).iter_rows(named=True):
        fz = frozen.filter((pl.col('setup') == r['setup']) & (pl.col('structure') == r['structure']))
        if fz.height == 0: continue
        pn = fz['pname'][0]
        sub = allsub.filter((pl.col('setup') == r['setup']) & (pl.col('structure') == r['structure']) & pl.col('pname').is_in([pn, 'M0_cutoff']))
        sub = sub.with_columns(pl.when(pl.col('pname') == pn).then(pl.lit('a')).otherwise(pl.lit('b')).alias('arm'))
        pr = an.paired(sub, ['setup'], {'arm': 'a'}, {'arm': 'b'}, bt)
        ok = pn == 'M0_cutoff' or pr['diff_hi'][0] >= 0          # not significantly worse than holding to the cutoff
        fin.append({'setup': r['setup'], 'structure': r['structure'], 'oos_n': r['n'], 'oos_exp': r['exp'], 'oos_lo': r['exp_lo'], 'frozen_policy': pn,
                    'frozen_exp': fz['exp'][0], 'frozen_lo': fz['exp_lo'][0], 'vs_M0': pr['diff'][0], 'vs_M0_lo': pr['diff_lo'][0], 'vs_M0_hi': pr['diff_hi'][0], 'qualifies': bool(ok)})
fin = pl.DataFrame(fin) if fin else pl.DataFrame({'note': ['no cell has a walk-forward out-of-sample lower bound above zero']})
fin.write_csv(f'{OUT}/finalists.csv')
log(f'finalists: {fin.height if "setup" in fin.columns else 0}')

# ---------------------------------------------------------------- D. entry rules against entering at the signal (paired)
er = []
for rule in ('E1L1', 'E1L3', 'E1L3g', 'E2', 'E2g', 'E3', 'E3atr'):
    try: rr = an.load_rows(f'entry_{rule}', roots=ROOTS)
    except Exception as e: log(f'entry {rule}: {e}'); continue
    rr = rr.filter(pl.col('ctrl') == -1)
    pos_all = rr.select(['root', 'session', 'setup', 'event_i', 'structure']).unique()
    # every event the rule saw, filled or not: a skipped or unfilled order is a trade not taken (P&L 0) in the paired view
    took = rr.filter(pl.col('filled') > 0).select(['root', 'session', 'setup', 'event_i', 'structure', 'pname', 'pnl'])
    for pname in ('M0_cutoff', 'M1_t30', 'M2_s35_t50'):
        b = base_rows.filter((pl.col('pname') == pname) & (pl.col('filled') > 0))
        a = took.filter(pl.col('pname') == pname)
        j = b.join(a, on=['root', 'session', 'setup', 'event_i', 'structure'], how='left', suffix='_r').with_columns(pl.col('pnl_r').fill_null(0.0))
        fill_rate = j.select(pl.col('pname_r').is_not_null().mean()).item()
        d = pl.concat([j.group_by(['structure', 'session']).agg(pl.len().alias('n'), pl.col('pnl_r').sum().alias('pnl')).with_columns(pl.lit('rule').alias('arm')),
                       j.group_by(['structure', 'session']).agg(pl.len().alias('n'), pl.col('pnl').sum()).with_columns(pl.lit('E0').alias('arm'))])
        p = an.paired(d, ['structure'], {'arm': 'rule'}, {'arm': 'E0'}, boot).with_columns(pl.lit(rule).alias('rule'), pl.lit(pname).alias('pname'), pl.lit(fill_rate).alias('taken_share'))
        # the trades the rule actually took, compared with E0 on those same events
        jt = j.filter(pl.col('pname_r').is_not_null())
        p = p.with_columns(pl.lit(float(jt['pnl_r'].mean()) if jt.height else None).alias('exp_rule_taken'), pl.lit(float(jt['pnl'].mean()) if jt.height else None).alias('exp_E0_same_events'))
        er.append(p)
if er:
    pl.concat(er).write_csv(f'{OUT}/entry_rules_vs_E0.csv')
    log('entry rules written')

# ---------------------------------------------------------------- E. entry filters read from the stage-1 rows (E5, E6, E7)
def vix_prior_close():
    import glob, datetime as _dt
    out = {}
    fs = sorted(glob.glob(f'{paths.INDEX}/VIX/*.parquet'))
    prev = None
    for f in fs:
        d = _dt.date.fromisoformat(os.path.basename(f)[:10])
        x = pl.read_parquet(f).filter(pl.col('price').is_not_null())
        if prev is not None: out[d] = prev
        if x.height: prev = float(x['price'][-1])
    return out
vix = vix_prior_close()
f = f_rows.with_columns(pl.col('session').replace_strict(vix, default=None, return_dtype=pl.Float64).alias('vix_prev'))
f = f.with_columns([
    pl.when(pl.col('m') < 90).then(pl.lit('a 09:45-11:00')).when(pl.col('m') < 270).then(pl.lit('b 11:00-14:00')).otherwise(pl.lit('c 14:00-15:00')).alias('tod'),
    pl.when(pl.col('rel_spread') <= 0.05).then(pl.lit('<=5%')).when(pl.col('rel_spread') <= 0.10).then(pl.lit('5-10%')).otherwise(pl.lit('>10%')).alias('spread_bin'),
    pl.when(pl.col('vix_prev') < 15).then(pl.lit('VIX<15')).when(pl.col('vix_prev') < 20).then(pl.lit('VIX15-20')).otherwise(pl.lit('VIX>=20')).alias('vix_bin'),
])
filt = []
for col in ('tod', 'spread_bin', 'vix_bin'):
    d = rp.rows_to_daily(f, ['structure', 'pname', col])
    filt.append(an.cell_table(d, ['structure', 'pname', col], boot).rename({col: 'level'}).with_columns(pl.lit(col).alias('filter')))
pl.concat(filt, how='diagonal_relaxed').write_csv(f'{OUT}/entry_filters.csv')
log('entry filters written')
