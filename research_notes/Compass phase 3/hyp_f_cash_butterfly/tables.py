"""Hypothesis F: render the markdown tables for the notes from out/cells.csv, out/kstar.csv, out/fills.csv,
out/magdiff.csv (no computation beyond formatting) -> out/tables.md."""
import os, sys, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
C = pl.read_csv(os.path.join(OUT, 'cells.csv')); K = pl.read_csv(os.path.join(OUT, 'kstar.csv')); FI = pl.read_csv(os.path.join(OUT, 'fills.csv')); M = pl.read_csv(os.path.join(OUT, 'magdiff.csv'))
L = []
def p(s=''): L.append(s)
def pc(x): return f'{x*100:+.2f}'
def yr(s):
    # '2025:+6.2$(+2.9%,n493) 2026:...' -> '25: +2.9 / 26: +5.1'
    out = []
    for tok in s.split(' '):
        y = tok[:4]; pct = tok.split('(')[1].split('%')[0]
        out.append(f'{y[2:]}: {pct}')
    return ' / '.join(out)
FORM = {'call': 'long call ±5', 'put': 'long put ±5', 'iron': 'iron ±5 (spread approval)'}

p('## T1. The primary and secondary cells, every k and stress — SPY + QQQ pooled, OOS 2025-01-02 → 2026-10-09')
p()
p('| time | form | k | stress $/leg | n | mean $ | mean % [95 % CI] | win | avg W / L $ | p5 / p1 / worst $ | worst session | PF | MDD $ | streak | wo5 % | SPY / QQQ % | by year % |')
p('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for t in [1530, 1500]:
    for form in ['call', 'put', 'iron']:
        for r in C.filter((pl.col('t') == t) & (pl.col('product') == 'SPY+QQQ') & (pl.col('form') == form) & (pl.col('period') == 'oos')).sort('k', 'stress').iter_rows(named=True):
            p(f"| {str(t)[:2]}:{str(t)[2:]} | {FORM[form]} | {r['k']:.2f} | {r['stress']:.2f} | {r['n']:,} | {r['mean_usd']:+.2f} | {pc(r['mean_pct'])} [{pc(r['ci_lo_pct'])}, {pc(r['ci_hi_pct'])}] | {r['win_rate']:.3f} | {r['avg_win_usd']:+.0f} / {r['avg_loss_usd']:+.0f} | {r['p5_usd']:+.0f} / {r['p1_usd']:+.0f} / {r['worst_usd']:+.0f} | {r['worst_session']} ({r['worst_session_usd']:+.0f}) | {r['profit_factor']:.2f} | {r['max_dd_usd']:+.0f} | {r['longest_losing']} | {pc(r['wo_best5_pct'])} | {pc(r['SPY_mean_pct'])} / {pc(r['QQQ_mean_pct'])} | {yr(r['by_year'])} |")
p()
p('## T2. The same cells on FIT 2022-11-11 → 2024-12-31 (SPY + QQQ pooled)')
p()
p('| time | form | k | stress | n | mean $ | mean % [95 % CI] | win | PF | MDD $ | streak | wo5 % | SPY / QQQ % | by year % |')
p('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for t in [1530, 1500]:
    for form in ['call', 'put', 'iron']:
        for r in C.filter((pl.col('t') == t) & (pl.col('product') == 'SPY+QQQ') & (pl.col('form') == form) & (pl.col('period') == 'fit')).sort('k', 'stress').iter_rows(named=True):
            p(f"| {str(t)[:2]}:{str(t)[2:]} | {FORM[form]} | {r['k']:.2f} | {r['stress']:.2f} | {r['n']:,} | {r['mean_usd']:+.2f} | {pc(r['mean_pct'])} [{pc(r['ci_lo_pct'])}, {pc(r['ci_hi_pct'])}] | {r['win_rate']:.3f} | {r['profit_factor']:.2f} | {r['max_dd_usd']:+.0f} | {r['longest_losing']} | {pc(r['wo_best5_pct'])} | {pc(r['SPY_mean_pct'])} / {pc(r['QQQ_mean_pct'])} | {yr(r['by_year'])} |")
p()
p('## T3. By name, OOS, k = 0 and the stresses (and k = 0.25 / 0.5 at stress 0)')
p()
p('| time | name | form | k | stress | n | mean $ | mean % [95 % CI] | win | PF | MDD $ | streak | wo5 % | worst session | by year % |')
p('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for t in [1530, 1500]:
    for nm in ['SPY', 'QQQ']:
        for form in ['call', 'put', 'iron']:
            for r in C.filter((pl.col('t') == t) & (pl.col('product') == nm) & (pl.col('form') == form) & (pl.col('period') == 'oos') & ((pl.col('k') == 0) | (pl.col('stress') == 0))).sort('k', 'stress').iter_rows(named=True):
                p(f"| {str(t)[:2]}:{str(t)[2:]} | {nm} | {FORM[form]} | {r['k']:.2f} | {r['stress']:.2f} | {r['n']} | {r['mean_usd']:+.2f} | {pc(r['mean_pct'])} [{pc(r['ci_lo_pct'])}, {pc(r['ci_hi_pct'])}] | {r['win_rate']:.3f} | {r['profit_factor']:.2f} | {r['max_dd_usd']:+.0f} | {r['longest_losing']} | {pc(r['wo_best5_pct'])} | {r['worst_session']} ({r['worst_session_usd']:+.0f}) | {yr(r['by_year'])} |")
p()
p('## T4. Break-even fill improvement k*, the gross (mid-to-mid) result and friction')
p()
p('k* = −mean(k = 0) / (100 × mean slip): the k at which the OOS mean crosses zero; negative = the cell stays positive even at fills WORSE than the NBBO, by |k*| × the slip. "$/leg to zero" = mean(k = 0) / 400: the worse-fill per leg that takes the mean to zero. Gross = (payoff − mid package) × 100, no fees; friction = gross − net(k = 0) = NBBO slip + $2.60 of fees.')
p()
p('| time | name | form | period | n | mean $ at k = 0 | slip $ (NBBO − mid, a fly) | mean at k = 0.25 / 0.5 / 1 (mid) | k* | $/leg to zero | gross $ | friction $ | friction / gross |')
p('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
for r in K.join(FI, on=['t', 'product', 'form', 'period', 'n']).sort('t', 'product', 'form', 'period', descending=[True, False, False, False]).iter_rows(named=True):
    t = str(r['t'])
    p(f"| {t[:2]}:{t[2:]} | {r['product']} | {FORM[r['form']]} | {r['period']} | {r['n']:,} | {r['mean_nbbo_usd']:+.2f} | {r['mean_slip_usd']:.2f} (med {r['slip_med_usd']:.2f}) | {r['mean_at_k025']:+.2f} / {r['mean_at_k05']:+.2f} / {r['mean_mid']:+.2f} | {r['kstar']:+.2f} | {r['breakeven_usd_per_leg']:+.4f} | {r['gross_mean_usd']:+.2f} | {r['friction_mean_usd']:.2f} | {r['friction_share_of_gross']:.2f} |")
p()
p('## T5. Quoted size on the legs at the entry minute (the side hit: ask size on a long leg, bid size on a short leg)')
p()
p('| time | name | form | period | n | min leg size: median / p10 | every leg ≥ 1 | every leg ≥ its lots (2 on the short K0 of a call/put fly) | every leg ≥ 10 | NBBO max risk $ |')
p('|---|---|---|---|---|---|---|---|---|---|')
for r in FI.sort('t', 'product', 'form', 'period', descending=[True, False, False, False]).iter_rows(named=True):
    t = str(r['t'])
    p(f"| {t[:2]}:{t[2:]} | {r['product']} | {FORM[r['form']]} | {r['period']} | {r['n']:,} | {r['min_size_med']:.0f} / {r['min_size_p10']:.0f} | {r['share_all_legs_ge1']*100:.1f} % | {r['share_all_legs_ge_lots']*100:.1f} % | {r['share_all_legs_ge10']*100:.1f} % | {r['nbbo_risk_mean']:.2f} |")
p()
p('## T6. moc_mag Q1–Q2 vs Q3–Q5 (C\'s definition and scores), k = 0, % of max risk; diff = Q12 − Q345 with a session bootstrap in each group')
p()
p('| time | name | form | period | n Q12 / Q345 | Q12 % (win) | Q345 % (win) | diff [95 % CI] |')
p('|---|---|---|---|---|---|---|---|')
for r in M.sort('t', 'product', 'form', 'period', descending=[True, False, False, False]).iter_rows(named=True):
    t = str(r['t'])
    p(f"| {t[:2]}:{t[2:]} | {r['product']} | {FORM[r['form']]} | {r['period']} | {r['n_Q12']} / {r['n_Q345']} | {pc(r['Q12_pct'])} ({r['Q12_win']:.2f}) | {pc(r['Q345_pct'])} ({r['Q345_win']:.2f}) | {pc(r['diff_pct'])} [{pc(r['diff_lo'])}, {pc(r['diff_hi'])}] |")
open(os.path.join(OUT, 'tables.md'), 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
