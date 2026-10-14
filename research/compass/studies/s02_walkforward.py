"""S02 post-processing: single-factor grid table and chronological walk-forward selection over the S02 variant directories
plus the S01 baseline (04_protocol.md §8–§9). Runs on whatever variants have finished (partial grids are labelled as such).
Usage: python3 s02_walkforward.py [out_name]"""
import datetime as dt, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import polars as pl
from engine import walkforward, stats
HERE = os.path.dirname(os.path.abspath(__file__))
GRID = os.path.join(HERE, '..', 'results', 'v1', 's02_quick_scalps_grid')
S01 = os.path.join(HERE, '..', 'results', 'v1', 's01_quick_scalps_0dte_baseline')
from s02_quick_scalps_grid import VARIANTS
name = sys.argv[1] if len(sys.argv) > 1 else 's02_walkforward'
OUT = os.path.join(HERE, '..', 'results', 'v1', name); os.makedirs(OUT, exist_ok=True)

dirs = {'baseline': S01}
for v in VARIANTS:
    if os.path.exists(os.path.join(GRID, v, 'summary.json')): dirs[v] = os.path.join(GRID, v)
missing = [v for v in VARIANTS if v not in dirs]
print(f'{len(dirs) - 1} of {len(VARIANTS)} variants finished; missing: {missing}', flush=True)

# 1. grid table: full-sample result per variant with its matched random baseline and the paired difference
rows = []
for n, d in dirs.items():
    s = json.load(open(os.path.join(d, 'summary.json'))); a = s.get('all', {}); b = s.get('baseline_pooled', {}) or {}; diff = s.get('strategy_minus_baseline', {}) or {}
    rows.append({'variant': n, 'change': json.dumps(VARIANTS.get(n, {})), 'signals': s.get('signals'), 'filled': s.get('filled'), 'days': a.get('days'),
                 'mean': a.get('mean'), 'ci_lo': a.get('ci_lo'), 'ci_hi': a.get('ci_hi'), 'win_rate': a.get('win_rate'), 'profit_factor': a.get('profit_factor'),
                 'max_drawdown': a.get('max_drawdown'), 'gross_mean': a.get('gross_mean'), 'random_mean': b.get('mean'), 'random_ci_lo': b.get('ci_lo'), 'random_ci_hi': b.get('ci_hi'),
                 'minus_random': diff.get('mean'), 'minus_random_lo': diff.get('ci_lo'), 'minus_random_hi': diff.get('ci_hi'),
                 'by_year': {str(y['year']): round(y['mean'], 2) for y in s.get('by_year', []) if y.get('mean') is not None}})
tab = pl.DataFrame(rows).sort('ci_lo', descending=True, nulls_last=True)
tab.with_columns(pl.col('by_year').map_elements(json.dumps, return_dtype=pl.Utf8)).write_csv(os.path.join(OUT, 'grid_table.csv'))

# 2. walk-forward: choose the best training-period candidate each year, score it on the held-out year
wf = {}
for kind in ('lb', 'mean', 'ep_ewd'):
    wf[kind] = walkforward.run(dirs, [2024, 2025, 2026], os.path.join(OUT, f'walkforward_{kind}.json'), objective_kind=kind, min_trades=150, min_train_years=2, embargo_sessions=5)

# 3. multiplicity: how many of the n variants have a positive lower bound (expected ~2.5 % by chance at 95 %)
pos = tab.filter(pl.col('ci_lo') > 0)['variant'].to_list()
beats = tab.filter(pl.col('minus_random_lo') > 0)['variant'].to_list()
best = tab.row(0, named=True)
summary = {'variants_finished': len(dirs) - 1, 'variants_total': len(VARIANTS), 'missing': missing, 'positive_lower_bound': pos, 'beats_random_lower_bound': beats,
           'best_by_lower_bound': {k: best[k] for k in ('variant', 'filled', 'mean', 'ci_lo', 'ci_hi', 'win_rate', 'profit_factor', 'minus_random', 'minus_random_lo')},
           'walkforward': {k: {'folds': [{kk: f.get(kk) for kk in ('test_year', 'selected', 'skipped', 'train_score', 'test')} for f in v['folds']], 'oos': v.get('oos'), 'oos_by_year': v.get('oos_by_year')} for k, v in wf.items()}}
json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)

# 4. markdown
L = [f'# S02 — single-factor grid around the Quick Scalps baseline, {len(dirs) - 1} of {len(VARIANTS)} variants' + (' (PARTIAL)' if missing else ''), '',
     'SPY/QQQ/IWM same-day expirations 2022-11-11 → 2026-10-09; ask in / bid out at the 1-minute NBBO; $0.70/contract/side; day-clustered 95 % CIs; '
     'matched random = 5 seeds of random entry minutes (±45 min) on the same symbol/date/direction with the variant\'s own contract rule and exits.', '',
     '| variant | change | filled | days | mean $/ct | 95 % CI | win | PF | max DD | random mean | strategy − random [CI] | by year |', '|---|---|---|---|---|---|---|---|---|---|---|---|']
f = lambda x, d=2: '' if x is None else f'{x:.{d}f}'
for r in tab.iter_rows(named=True):
    L.append(f"| {r['variant']} | `{r['change']}` | {r['filled']} | {r['days']} | **{f(r['mean'])}** | [{f(r['ci_lo'])}, {f(r['ci_hi'])}] | {f((r['win_rate'] or 0) * 100, 1)} % | {f(r['profit_factor'])} | {f(r['max_drawdown'], 0)} | {f(r['random_mean'])} | {f(r['minus_random'])} [{f(r['minus_random_lo'])}, {f(r['minus_random_hi'])}] | {r['by_year']} |")
L += ['', f'Variants with a positive full-sample lower bound: {pos or "none"}. Variants beating their matched random control (paired lower bound > 0): {beats or "none"}.', '',
      '## Walk-forward selection (train on all prior years with a 5-session embargo, ≥150 training trades, test on the next year)', '']
for kind, v in wf.items():
    L.append(f'### objective = {kind}'); L.append('')
    L.append('| test year | selected | training score | training trades | OOS n | OOS mean | OOS 95 % CI | win | PF |'); L.append('|---|---|---|---|---|---|---|---|---|')
    for fo in v['folds']:
        if fo.get('skipped'): L.append(f"| {fo['test_year']} | — | {fo['skipped']} | | | | | | |"); continue
        t = fo['test']; L.append(f"| {fo['test_year']} | {fo['selected']} | {f(fo['train_score'])} | {fo['train_trades']} | {t.get('n')} | {f(t.get('mean'))} | [{f(t.get('ci_lo'))}, {f(t.get('ci_hi'))}] | {f((t.get('win_rate') or 0) * 100, 1)} % | {f(t.get('profit_factor'))} |")
    o = v.get('oos')
    if o: L.append(f"\nPooled out-of-sample: n {o['n']}, mean {f(o['mean'])} [{f(o['ci_lo'])}, {f(o['ci_hi'])}], win {f(o['win_rate'] * 100, 1)} %, PF {f(o['profit_factor'])}, max DD {f(o['max_drawdown'], 0)}, net {f(o['net_total'], 0)}.")
    L.append('')
open(os.path.join(OUT, 'REPORT.md'), 'w').write('\n'.join(L) + '\n')
print('\n'.join(L[:8])); print('...'); print('\n'.join(L[-22:]))
