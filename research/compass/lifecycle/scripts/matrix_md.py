"""Renders 09_setup_strategy_matrix.md from results/matrix/*.csv (scripts/build_matrix.py). Nothing in it is typed by hand."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import paths

M = f'{paths.RESULTS}/matrix'
OUT = os.path.join(paths.HERE, '09_setup_strategy_matrix.md')
SHORT = {'failed': 'F', 'failed on the hold-out': 'H', 'inconclusive': '?', 'insufficient': 'n', 'carry, not setup': 'C', 'promising': 'P'}
STRUCT = ['LC-S', 'LP-S', 'LC-B', 'LP-B', 'DCS', 'DPS', 'CPS', 'CSP', 'STR', 'STG']
NAMES = {'QS': 'Quick Scalps', 'TP': 'Trend pullback', 'BO': 'Breakout', 'BOF': 'Failed breakout', 'LS': 'Liquidity sweep (ICT)',
         'MSS': 'Market-structure shift (ICT)', 'FVG': 'Fair-value gap (ICT)', 'TPp': 'Trend pullback, trigger only', 'BOp': '5m breakout, trigger only',
         'BOr': 'Breakout retest, trigger only', 'BNp': 'Bounce, trigger only', 'VWR': 'VWAP reclaim',
         'D_TP': 'Trend pullback (daily)', 'D_BO': 'Breakout (daily)', 'D_BOF': 'Failed breakout (daily)', 'D_BN': 'Bounce (daily)',
         'D_BNF': 'Failed bounce (daily)', 'D_EARN': 'Pre-earnings (5 sessions before)', 'D_FOMC': 'Day before the Fed',
         'D_ALLL': 'Baseline: every Monday, long', 'D_ALLS': 'Baseline: every Monday, short', 'D_ALLV': 'Baseline: every Monday, straddle',
         'D_ALLP': 'Baseline: every Monday, put sale', 'D_ALLF': 'Baseline: non-Fed weeks'}

def grid(df, index_cols):
    cols = [c for c in STRUCT if c in df['structure'].unique().to_list()]
    p = df.with_columns(pl.col('label').replace(SHORT).alias('s')).pivot(index=index_cols, on='structure', values='s')
    for c in cols:
        if c not in p.columns: p = p.with_columns(pl.lit(None, pl.Utf8).alias(c))
    p = p.select(index_cols + cols).sort(index_cols)
    head = '| ' + ' | '.join(index_cols + cols) + ' |\n|' + '---|' * (len(index_cols) + len(cols)) + '\n'
    body = ''
    for r in p.iter_rows(named=True):
        lab = [NAMES.get(r[c], r[c]) if c == 'setup' else str(r[c]) for c in index_cols]
        body += '| ' + ' | '.join(lab + [r[c] or '·' for c in cols]) + ' |\n'
    return head + body

def detail(df, keys):
    x = df.filter(pl.col('label') != 'failed').sort(keys)
    if x.height == 0: return '_none_\n'
    has_after = 'edge_after' in x.columns; has_ctrl = 'edge_ctrl' in x.columns; has_ho = 'holdout' in x.columns
    hdr = keys + ['best policy', 'trades', 'expectancy [95 %]', 'walk-forward [95 %]'] + (['vs a later minute [95 %]'] if has_after else []) \
        + (['vs a random day [95 %]'] if has_ctrl else []) + (['hold-out'] if has_ho else []) + ['label']
    out = '| ' + ' | '.join(hdr) + ' |\n|' + '---|' * len(hdr) + '\n'
    f = lambda v: '—' if v is None else f'{v:+.1f}'
    for r in x.iter_rows(named=True):
        row = [NAMES.get(r[k], r[k]) if k == 'setup' else str(r[k]) for k in keys]
        row += [r['best_policy'], f"{int(r['n_max']):,}", f"{f(r['exp'])} [{f(r['exp_lo'])}, {f(r['exp_hi'])}]",
                f"{f(r.get('wf_exp'))} [{f(r.get('wf_lo'))}, {f(r.get('wf_hi'))}]"]
        if has_after: row.append(f"{f(r.get('edge_after'))} [{f(r.get('after_lo'))}, {f(r.get('after_hi'))}]")
        if has_ctrl: row.append(f"{f(r.get('edge_ctrl'))} [{f(r.get('ctrl_lo'))}, {f(r.get('ctrl_hi'))}]")
        if has_ho: row.append(r.get('holdout') or '—')
        row.append(r['label'])
        out += '| ' + ' | '.join(row) + ' |\n'
    return out

doc = """# Lifecycle research — 9. Setup × strategy matrix (deliverable 5)

Every setup × structure cell tested, classified by `scripts/build_matrix.py` from the result files and rendered by
`scripts/matrix_md.py`. Nothing here is typed by hand. A cell's label is the first that applies:

| Code | Label | Rule |
|---|---|---|
| n | insufficient | fewer than 100 trades or 60 sessions |
| F | failed | every policy's interval below zero, or the walk-forward interval below zero |
| H | failed on the hold-out | tested once on the hold-out and not promoted (`07_validation.md` §4) |
| C | carry, not setup | some policy's lower bound > 0 and walk-forward > 0, but no better than its clean control |
| P | promising | as C, and better than its clean control; still not validated without a hold-out |
| ? | inconclusive | intervals span zero |
| · | not applicable | the structure does not follow the setup's direction, or was not run |

**Structures**
- LC-S / LP-S: Steady call / put.
- LC-B / LP-B: Big Payoff call / put.
- DCS / DPS: debit call / put spread.
- CPS: credit put spread.
- CSP: cash-secured put.
- STR / STG: long straddle / strangle.

**How a cell is scored**
- Its best policy is the stage-1 policy with the highest lower bound on development + validation.
- The walk-forward column picks a policy each quarter (Tier I) or year (daily tier) on earlier data alone.

"""
a = pl.read_csv(f'{M}/tier1_matrix.csv')
counts = a.group_by('label').len().sort('label')
doc += '## 1. Same-day options (Tier I: SPY, QQQ, IWM, SPXW 0DTE, 2022-05 → 2025-09; hold-out 2025-10 → 2026-10)\n\n'
doc += 'Counts: ' + ', '.join(f"{r['label']} {r['len']}" for r in counts.iter_rows(named=True)) + '.\n\n'
doc += grid(a, ['setup']) + '\n### Cells that did not simply fail\n\n' + detail(a, ['setup', 'structure']) + '\n'
if os.path.exists(f'{M}/tier1_vol_matrix.csv'):
    v = pl.read_csv(f'{M}/tier1_vol_matrix.csv')
    doc += '### Volatility and Fed-day setups (Tier I)\n\n' + grid(v, ['setup']) + '\n' + detail(v, ['setup', 'structure']) + '\n'
if os.path.exists(f'{M}/tier_d_matrix.csv'):
    b = pl.read_csv(f'{M}/tier_d_matrix.csv')
    counts = b.group_by('label').len().sort('label')
    doc += '## 2. Daily lifecycles (daily tier: Weekly, Swing, Position, Long-Dated, LEAPS; development ≤ 2021, validation 2022–2023)\n\n'
    doc += 'Counts: ' + ', '.join(f"{r['label']} {r['len']}" for r in counts.iter_rows(named=True)) + '.\n\n'
    for g in sorted(b['group'].unique().to_list()):
        doc += f"### {'Index ETFs (SPY, QQQ, IWM)' if g == 'index_etf' else 'Single names'}\n\n"
        doc += grid(b.filter(pl.col('group') == g), ['setup', 'bucket']) + '\n'
    doc += '### Cells that did not simply fail\n\n' + detail(b, ['group', 'setup', 'bucket', 'structure']) + '\n'
else:
    doc += '## 2. Daily lifecycles\n\n_Running: filled when the daily tier finishes (`06_daily_tier.md`)._\n'
open(OUT, 'w').write(doc)
print('written', OUT)
