"""Amendment L-A4: the daily tier's finalists, chosen from development + validation alone, then the hold-out
(2024-01-01 -> 2026-10-09) opened once for them. Refuses a second run (lock file).

Finalist: yearly walk-forward out-of-sample expectancy > 0 with lower bound > 0 on >= 100 trades and >= 60 sessions;
frozen policy = the cell's best development + validation lower bound with >= 100 trades. Baselines (D_ALL*) are
never finalists. Promotion: R1 (Holm), R2 (random-day control, hold-out sessions), R2b (all-days baseline), R3 (PF),
R4 (sample), R5 (+$0.05 a side), R6 (development family median)."""
import os, sys, json, glob, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import polars as pl
from lc import analyze as an, daily_runner as dr, position as ps, paths

D = f'{paths.RESULTS}/tier_d'
LOCK = f'{D}/holdout_opened.json'
if os.path.exists(LOCK): sys.exit(f'already run: {open(LOCK).read()}')
INDEX = ('SPY', 'QQQ', 'IWM')
BASE = {1: 'D_ALLL', -1: 'D_ALLS', 0: 'D_ALLV'}
BULL = ('LC-S', 'LC-B', 'DCS', 'CPS', 'CSP'); BEAR = ('LP-S', 'LP-B', 'DPS')
keys = ['group', 'setup', 'bucket', 'structure']

wf = pl.read_csv(f'{D}/walkforward_oos.csv')
cells = pl.read_csv(f'{D}/cells.csv')
fin = wf.filter((pl.col('exp') > 0) & (pl.col('exp_lo') > 0) & (pl.col('n') >= 100) & (pl.col('days') >= 60) & ~pl.col('setup').str.starts_with('D_ALL'))
dv = cells.filter((pl.col('side') == 'real') & (pl.col('period') == 'all') & (pl.col('n') >= 100))
frozen = dv.sort('exp_lo', descending=True).group_by(keys, maintain_order=True).first().select(keys + [pl.col('pname').alias('policy')])
fin = fin.select(keys + ['n', 'exp', 'exp_lo']).join(frozen, on=keys, how='inner')
fin.write_csv(f'{D}/finalists.csv')
print(f'{fin.height} finalists'); print(fin)
if fin.height == 0:
    json.dump({'opened_utc': None, 'finalists': 0, 'note': 'no finalist; the hold-out stays unopened'}, open(f'{D}/holdout_verdicts.json', 'w'), indent=1)
    sys.exit(0)

# the frozen policies and their +$0.05 slippage twins
pol_names = sorted(set(fin['policy'].to_list()))
base_pols = dr.daily_policies()
extra = []
for name, fam, cut, pv in base_pols:
    if name in pol_names:
        q = pv.copy(); q[ps.P['SLIP']] = q[ps.P['SLIP']] + 0.05
        extra.append((f'{name}|slip05', fam, cut, q))
dr.daily_policies = lambda: base_pols + extra
run_names = tuple(pol_names + [f'{n}|slip05' for n in pol_names])
# run_root numbers policies within the filtered list, in daily_policies() order
names_all = [p[0] for p in dr.daily_policies() if p[0] in run_names]

setups = sorted(set(fin['setup'].to_list()) | set(BASE.values()))
buckets = tuple(sorted(set(fin['bucket'].to_list())))
roots = []
for g in fin['group'].unique().to_list():
    if g == 'index_etf': roots += list(INDEX)
    else: roots += [os.path.basename(p) for p in glob.glob(f'{paths.WORK}/runs/dgrid/*') if os.path.basename(p) not in INDEX]
opened = dt.datetime.now(dt.timezone.utc).isoformat()
json.dump({'opened_utc': opened, 'finalists': fin.height}, open(LOCK, 'w'))
for r in sorted(set(roots)):
    dr.run_root(r, 'dholdout', mode='daily', include_holdout=True, start=dr.HOLDOUT_START, buckets=buckets, setups=tuple(setups),
                policy_names=run_names, log=lambda m: None)
fr = []
for r in sorted(set(roots)):
    f = f'{paths.WORK}/runs/dholdout/{r}/daily.parquet'
    if os.path.exists(f): fr.append(pl.read_parquet(f).with_columns(pl.lit(r).alias('root')))
H = pl.concat(fr).filter(pl.col('session') >= dr.HOLDOUT_START)
H = H.with_columns(pl.col('setup').str.split('|').list.get(0).alias('s0'), pl.col('setup').str.split('|').list.get(1).alias('bucket'),
                   pl.col('policy').map_elements(lambda i: names_all[i] if i < len(names_all) else None, return_dtype=pl.Utf8).alias('pname'),
                   pl.when(pl.col('root').is_in(list(INDEX))).then(pl.lit('index_etf')).otherwise(pl.lit('single')).alias('group'))
H = H.drop('setup').rename({'s0': 'setup'})
boot = an.Boot(H['session'].to_list(), B=10000, seed=31)
dev_cells = cells.filter((pl.col('side') == 'real') & (pl.col('period') == 'dev'))
fam_of = {p[0]: p[1] for p in base_pols}

def ratio(sub):
    g = sub.group_by('session').agg(pl.col('n').sum(), pl.col('pnl').sum())
    N = np.zeros(len(boot.days)); P = np.zeros(len(boot.days))
    for s, n, p in zip(g['session'].to_list(), g['n'].to_list(), g['pnl'].to_list()): N[boot.ix[s]] += n; P[boot.ix[s]] += p
    return (P.sum() / N.sum() if N.sum() else np.nan), (boot.W @ P) / np.maximum(boot.W @ N, 1e-9), N.sum(), int((N > 0).sum())

rows = []
for f in fin.iter_rows(named=True):
    sel = (pl.col('group') == f['group']) & (pl.col('bucket') == f['bucket']) & (pl.col('structure') == f['structure'])
    real = H.filter(sel & (pl.col('setup') == f['setup']) & (pl.col('ctrl') == 0) & (pl.col('pname') == f['policy']))
    ctrl = H.filter(sel & (pl.col('setup') == f['setup']) & (pl.col('ctrl') == 1) & (pl.col('pname') == f['policy']))
    slip = H.filter(sel & (pl.col('setup') == f['setup']) & (pl.col('ctrl') == 0) & (pl.col('pname') == f"{f['policy']}|slip05"))
    d0 = 0 if f['structure'] in ('STR', 'STG') else (1 if f['structure'] in BULL else -1)
    base = H.filter(sel & (pl.col('setup') == BASE[d0]) & (pl.col('ctrl') == 0) & (pl.col('pname') == f['policy']))
    e, b, n, days = ratio(real)
    ec, bc, nc, _ = ratio(ctrl) if ctrl.height else (np.nan, np.full(len(boot.W), np.nan), 0, 0)
    eb, bb, nbase, _ = ratio(base) if base.height else (np.nan, np.full(len(boot.W), np.nan), 0, 0)
    es, _, _, _ = ratio(slip) if slip.height else (np.nan, None, 0, 0)
    wins = real['wins'].sum(); wp = real['win_pnl'].sum(); lp = real['loss_pnl'].sum()
    fam_dev = dev_cells.filter((pl.col('group') == f['group']) & (pl.col('setup') == f['setup']) & (pl.col('bucket') == f['bucket']) & (pl.col('structure') == f['structure'])
                               & pl.col('pname').is_in([k for k, v in fam_of.items() if v == fam_of[f['policy']]]))
    rows.append({**f, 'h_n': float(n), 'h_days': days, 'h_exp': float(e), 'h_lo': float(np.nanquantile(b, 0.025)), 'h_hi': float(np.nanquantile(b, 0.975)),
                 'p_one_sided': float(np.mean(b <= 0)), 'win_rate': float(wins / max(n, 1)), 'pf': float(wp / max(-lp, 1e-9)),
                 'ctrl_n': float(nc), 'edge_ctrl': float(e - ec) if ctrl.height else None, 'ctrl_lo': float(np.nanquantile(b - bc, 0.025)) if ctrl.height else None,
                 'base_n': float(nbase), 'edge_base': float(e - eb) if base.height else None, 'base_lo': float(np.nanquantile(b - bb, 0.025)) if base.height else None,
                 'exp_slip05': float(es), 'dev_family_median': float(fam_dev['exp'].median()) if fam_dev.height else None})
v = pl.DataFrame(rows, infer_schema_length=None).sort('p_one_sided')
k = v.height; ok = True; r1 = []
for i, p in enumerate(v['p_one_sided'].to_list()):
    ok = ok and p < 0.05 / (k - i); r1.append(ok)
v = v.with_columns(pl.Series('R1', r1), (pl.col('ctrl_lo').fill_null(-1) > 0).alias('R2'), (pl.col('base_lo').fill_null(-1) > 0).alias('R2b'),
                   (pl.col('pf') > 1).alias('R3'), ((pl.col('h_n') >= 100) & (pl.col('h_days') >= 60)).alias('R4'),
                   (pl.col('exp_slip05') > 0).alias('R5'), (pl.col('dev_family_median').fill_null(-1) > 0).alias('R6'))
v = v.with_columns(pl.all_horizontal(['R1', 'R2', 'R2b', 'R3', 'R4', 'R5', 'R6']).alias('PROMOTED'))
v.write_csv(f'{D}/holdout_verdicts.csv')
print(v)
