"""Markdown tables from results/tier1/*.csv for the lifecycle reports (the narrative is written by hand around them).
Writes results/tier1/tables/*.md."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import reports as rp, paths

R = f'{paths.RESULTS}/tier1'; T = f'{R}/tables'; os.makedirs(T, exist_ok=True)
def w(name, text): open(f'{T}/{name}.md', 'w').write(text + '\n')

s1 = pl.read_csv(f'{R}/stage1_cells.csv')
for pname in ('M0_cutoff', 'M1_t30', 'M2_s35_t50', 'M0_expiry', 'M13_tp50_s2', 'M5_thesis1m'):
    x = s1.filter((pl.col('period') == 'all') & (pl.col('pname') == pname)).sort(['structure', 'setup'])
    w(f'stage1_{pname}', rp.fmt_table(x, [('setup', 'Setup', 'str'), ('structure', 'Structure', 'str'), ('n', 'Trades', 'int'), ('days', 'Days', 'int'),
        ('win_rate', 'Win', 'rate'), ('avg_win', 'Avg win $', 'usd'), ('avg_loss', 'Avg loss $', 'usd'), ('exp', 'Exp $', 'usd'),
        ('exp_lo', '95% lo', 'usd'), ('exp_hi', '95% hi', 'usd'), ('profit_factor', 'PF', 'num'), ('mean_pct', 'Mean %', 'pct'),
        ('median_pct', 'Median %', 'pct'), ('edge_vs_rnd', 'vs RND $', 'usd'), ('edge_lo', 'lo', 'usd'), ('edge_hi', 'hi', 'usd'),
        ('mfe_pct', 'MFE % (A)', 'pct'), ('share_mfe50', 'MFE>=50% (A)', 'rate'), ('t_mfe_med', 't MFE min', 'num')]))
g = pl.read_csv(f'{R}/grid_by_structure.csv')
for st in g['structure'].unique().sort().to_list():
    for side in ('real', 'rnd'):
        x = g.filter((pl.col('structure') == st) & (pl.col('side') == side)).sort('exp', descending=True)
        w(f'grid_{st}_{side}', rp.fmt_table(x, [('pname', 'Policy', 'str'), ('family', 'Family', 'str'), ('n', 'Trades', 'int'), ('win_rate', 'Win', 'rate'),
            ('exp', 'Exp $', 'usd'), ('exp_lo', '95% lo', 'usd'), ('exp_hi', '95% hi', 'usd'), ('ret_on_premium', 'Ret/prem', 'pct'),
            ('vs_M0', 'vs M0 $', 'usd'), ('vs_M0_lo', 'lo', 'usd'), ('vs_M0_hi', 'hi', 'usd'), ('profit_factor', 'PF', 'num'), ('hold_min', 'Hold min', 'num'),
            ('partial1_per_trade', 'P1 $', 'usd'), ('partial2_per_trade', 'P2 $', 'usd'), ('runner_per_trade', 'Runner $', 'usd'),
            ('lot_add_per_trade', 'Adds $', 'usd'), ('lot_dd_per_trade', 'DD $', 'usd'), ('lot_scale_per_trade', 'Scale $', 'usd')]))
for name in ('walkforward_oos', 'dev_choice_then_val', 'finalists', 'entry_rules_vs_E0', 'entry_filters'):
    f = f'{R}/{name}.csv'
    if not os.path.exists(f): continue
    x = pl.read_csv(f)
    cols = [(c, c, 'usd' if x.schema[c] in (pl.Float64, pl.Float32) and any(k in c for k in ('exp', 'diff', 'pnl', 'vs_M0', 'oos', 'frozen', 'train')) else
             ('rate' if c in ('win_rate', 'taken_share', 'win_rate_val') else ('int' if c in ('n', 'n_val', 'oos_n', 'days', 'n_a', 'n_b') else ('num' if x.schema[c] in (pl.Float64, pl.Float32) else 'str'))))
            for c in x.columns if c not in ('wins', 'pnl', 'win_pnl', 'loss_pnl', 'cost', 'capital', 'hold', 'fees')]
    w(name, rp.fmt_table(x, cols))
print('tables written to', T)
