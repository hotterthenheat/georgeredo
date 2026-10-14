"""Builds RESULTS.md from the files in results/ (no computation beyond formatting and simple group-bys of grid.csv.gz)."""
import os, sys, json, hashlib
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import analyze as A

R = C.OUT


def f2(x, d=2):
    if x is None or (isinstance(x, float) and (np.isnan(x))): return 'n/a'
    return f'{x:+.{d}f}' if isinstance(x, float) else str(x)


def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]


def main():
    P = []; w = P.append
    G = pl.read_csv(os.path.join(R, 'grid.csv.gz'))
    S = pl.read_csv(os.path.join(R, 'selected_test.csv'))
    Y = pl.read_csv(os.path.join(R, 'selected_by_year.csv'))
    Bs = pl.read_csv(os.path.join(R, 'baselines.csv'))
    M = pl.read_csv(os.path.join(R, 'marginal_effects.csv'))
    WR = pl.read_csv(os.path.join(R, 'wr_vs_expectancy.csv'))
    CV = pl.read_csv(os.path.join(R, 'coverage.csv'))
    J = json.load(open(os.path.join(R, 'grid_test_summary.json')))
    scopes = [s for s in A.SCOPES if s in J['scopes']]
    w('# SPY / QQQ / IWM 0DTE short-premium grid at measured NBBO: results\n')
    w(f'Protocol: `PREREGISTRATION.md` (sha256 {sha(os.path.join(C.HERE, "PREREGISTRATION.md"))}…, amendment A1 only), TRAIN selection in '
      f'`results/selection_train.json` (sha256 {J["selection_sha256"][:16]}…), written before any TEST trade was computed.  All $ are per 1-lot '
      '(one contract per leg), after bid/ask fills and $0.70 per contract per side.  CIs: 95 % bootstrap over trading days (5,000 draws, seed 7).  '
      'Every number is labelled TRAIN (2022-11-11 → 2024-12-31; IWM from 2024-04-19) or TEST (2025-01-02 → 2026-10-09).\n')
    w('Grid: 7 structure-k cells × 4 entries × 3 TP × 3 stops × 2 exits × 4 filters = 2,016 configurations per scope (1,890 distinct: '
      'F2 at 14:05 equals F0); plus 1,008 diagnostic E0 (buy back everything at 15:55) configurations that are never selected.  '
      f'Scopes with results: {", ".join(scopes)}.\n')
    if os.path.exists(os.path.join(R, 'reproduction.md')):
        w('## 0. Sanity check: reproduction of the published T-A lane\n')
        w(open(os.path.join(R, 'reproduction.md')).read().split('\n', 2)[2])
    # ---- selections
    w('## 1. TRAIN-selected configurations and what they did in TEST\n')
    w('S1 = best TRAIN lower bound (TRAIN n ≥ 100); S2 = best TRAIN lower bound among TRAIN win rate ≥ 70 %.  PH-… = post-hoc '
      'selections by the same TRAIN-only rule restricted to the E1 exit (not pre-registered; added after the E2 diagnostics).\n')
    w('| scope | sel | configuration | TRAIN n / win / mean [CI] | TEST n / win / mean [CI] | TEST PF / maxDD $ / worst-5-day sum $ | TEST cost $ | random baseline mean (5 seeds) | lane − baseline (paired CI) | gate: LB>0, n≥150, ≥3 mo, beats random by > cost | TEST win ≥ 70 % |')
    w('|---|---|---|---|---|---|---|---|---|---|---|')
    for r in S.iter_rows(named=True):
        w5 = sum(int(x.split(' ')[1]) for x in r['test_worst5'].split('; ')) if isinstance(r['test_worst5'], str) else float('nan')
        g = ''.join('✓' if r[k] else '✗' for k in ('gate_lb_pos', 'gate_n150', 'gate_months3', 'gate_beats_random'))
        w(f"| {r['scope']} | {r['selection']} | `{r['cfg']}` {r['desc']} | {r['train_n']} / {r['train_wr']:.1f} % / {r['train_mean']:+.2f} [{r['train_lo']:+.2f}, {r['train_hi']:+.2f}] | "
          f"{r['test_n']} / {r['test_wr']:.1f} % / {r['test_mean']:+.2f} [{r['test_lo']:+.2f}, {r['test_hi']:+.2f}] | {r['test_pf']:.2f} / {r['test_mdd']:.0f} / {w5} | {r['test_cost']:.2f} | "
          f"{r['base_mean']:+.2f} ({r['base_seed_means']}) | {r['lane_minus_base']:+.2f} ({r['paired_diff']:+.2f} [{r['paired_lo']:+.2f}, {r['paired_hi']:+.2f}]) | "
          f"{g} → **{'PASS' if r['gate_pass'] else 'FAIL'}** | {'yes' if r['objective_wr70'] else 'no'} |")
    w('\nWorst five TEST days of each selection (date, $ summed over the scope\'s tickers):\n')
    for r in S.iter_rows(named=True):
        w(f"- {r['scope']} {r['selection']} `{r['cfg']}`: {r['test_worst5']}")
    w('\nBy calendar year (TEST):\n')
    w('| scope | sel | config | year | n | win % | mean $ [CI] | PF | maxDD $ |')
    w('|---|---|---|---|---|---|---|---|---|')
    for r in Y.iter_rows(named=True):
        w(f"| {r['scope']} | {r['selection']} | `{r['cfg']}` | {r['year']} | {r['n']} | {r['wr']} | {r['mean']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] | {r['pf']} | {r['mdd']:.0f} |")
    w('\nRandom-entry baselines (TEST; entry minute uniform 10:00–14:30, seeds 11–15; same structure, k, TP, stop, exit, filter):\n')
    w('| scope | sel | seed | n | win % | mean $ [CI] |')
    w('|---|---|---|---|---|---|')
    for r in Bs.iter_rows(named=True):
        w(f"| {r['scope']} | {r['selection']} | {r['seed']} | {r['n']} | {r['wr']} | {r['mean']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] |")
    # ---- full grid
    w('\n## 2. Full grid in TEST: how many configurations have a positive lower bound, and is that more than chance?\n')
    w('Chance count: recentred joint day bootstrap (seed 8) — under a global null of zero mean for every configuration, the number whose lower bound would exceed 0 '
      '(mean and 95th percentile over 5,000 draws; correlation across configurations kept).  Reality check: studentised max-t over configurations with TEST n ≥ 30.\n')
    w('| scope | distinct configs | TEST days | TEST LB > 0 | chance mean / p95 | TEST LB > 0 among TRAIN-win≥70 configs | chance mean / p95 | TEST win ≥ 70 % & LB > 0 | White RC: best t, p | Romano–Wolf rejections (FWER 5 %) | Spearman TRAIN vs TEST mean |')
    w('|---|---|---|---|---|---|---|---|---|---|---|')
    for sc in scopes:
        j = J['scopes'][sc]
        w(f"| {sc} | {j['distinct_configs']} | {j['test_days']} | {j['lb_pos']} | {j['chance_lb_pos_mean']} / {j['chance_lb_pos_p95']:.0f} | {j['lb_pos_among_train_wr70']} of {j['train_wr70_configs']} | "
          f"{j['chance_among_train_wr70_mean']} / {j['chance_among_train_wr70_p95']:.0f} | {j['lb_pos_and_wr70']} | {j['rc_best_t']} (`{j['rc_best_cfg']}`), p = {j['rc_p']} | {j['romano_wolf_rejections']} | {j['spearman_train_test_mean']} |")
    w('\nRomano–Wolf-rejected configurations by exit and structure (TEST):\n')
    w('| scope | E1 | E2 | straddle/strangle | iron condor |')
    w('|---|---|---|---|---|')
    for sc in scopes:
        rj = J['scopes'][sc]['rw_rejected']
        w(f"| {sc} | {sum(1 for c in rj if '|E1|' in c)} | {sum(1 for c in rj if '|E2|' in c)} | {sum(1 for c in rj if c.startswith('S'))} | {sum(1 for c in rj if c.startswith('I'))} |")
    w('\nTEST lower-bound quantiles over the distinct grid:\n')
    for sc in scopes: w(f"- {sc}: {J['scopes'][sc]['test_lb_quantiles']}")
    # ---- by structure and exit
    w('\n## 3. Win rate vs expectancy across the grid\n')
    w('Median over the distinct configurations in each cell (all entries, TPs, stops, filters):\n')
    w('| scope | structure-k | exit | TRAIN median win % | TRAIN median mean $ | TRAIN LB>0 | TEST median win % | TEST median mean $ | TEST LB>0 | median delta proxy |')
    w('|---|---|---|---|---|---|---|---|---|---|')
    D = G.filter(~pl.col('dup') & (pl.col('ex') != 'E0'))
    for sc in scopes:
        t = D.filter(pl.col('scope') == sc).group_by(['sk', 'ex']).agg(pl.col('train_wr').median().alias('a'), pl.col('train_mean').median().alias('b'), (pl.col('train_lo') > 0).sum().alias('c'),
                                                                      pl.col('test_wr').median().alias('d'), pl.col('test_mean').median().alias('e'), (pl.col('test_lo') > 0).sum().alias('f'),
                                                                      pl.col('test_dprox').median().alias('g')).sort(['sk', 'ex'])
        for r in t.iter_rows(named=True):
            w(f"| {sc} | {r['sk']} | {r['ex']} | {r['a']:.1f} | {f2(r['b'])} | {r['c']} | {r['d']:.1f} | {r['e']:+.2f} | {r['f']} | {r['g']:.3f} |")
    w('\nBy TRAIN win-rate bin (distinct configurations):\n')
    w('| scope | TRAIN win % bin | configs | TRAIN median mean $ | TRAIN LB>0 | TEST median win % | TEST median mean $ | TEST LB>0 | TEST mean > 0 (% of configs) |')
    w('|---|---|---|---|---|---|---|---|---|')
    for r in WR.iter_rows(named=True):
        w(f"| {r['scope']} | {r['train_wr_bin']} | {r['configs']} | {r['train_mean_median']:+.2f} | {r['train_lb_pos']} | {r['test_wr_median']} | {r['test_mean_median']:+.2f} | {r['test_lb_pos']} | {r['test_mean_pos_share']} |")
    w('\nSpearman correlation between win rate and mean P&L across configurations: ' + '; '.join(
        f"{sc} TRAIN {J['scopes'][sc]['spearman_wr_mean_train']}, TEST {J['scopes'][sc]['spearman_wr_mean_test']}" for sc in scopes) + '.\n')
    # ---- marginal effects
    w('## 4. What each rule does to win rate and expectancy (matched pairs: configurations identical except for the factor; both n ≥ 30)\n')
    w('| scope | period | factor: ref → alt | pairs | median Δ win (pts) | share with higher win | median Δ mean $ | mean Δ mean $ | share with higher mean | median Δ LB $ | note |')
    w('|---|---|---|---|---|---|---|---|---|---|---|')
    for r in M.filter(pl.col('scope').is_in(['SPY+QQQ', 'IWM'])).iter_rows(named=True):
        w(f"| {r['scope']} | {r['period']} | {r['factor']}: {r['ref']} → {r['alt']} | {r['pairs']} | {r['d_wr_median']:+.2f} | {r['share_wr_up']} % | {r['d_mean_median']:+.2f} | {r['d_mean_mean']:+.2f} | {r['share_mean_up']} % | {r['d_lo_median']:+.2f} | {r['note'] or ''} |")
    w('\n(Per-ticker rows: `results/marginal_effects.csv`.)\n')
    # ---- coverage
    w('## 5. Coverage by structure-k (share of eligible sessions with a trade; mean over the four entry times)\n')
    cv = CV.group_by(['ticker', 'period', 'sk']).agg(pl.col('coverage').mean().round(1), pl.col('dprox_median').median().round(3), pl.col('credit_median').median(),
                                                     pl.col('sessions').first()).sort(['ticker', 'period', 'sk'])
    w('| ticker | period | sessions | ' + ' | '.join(f'{s}{k:g}' for s, k in C.SK) + ' |')
    w('|---|---|---|' + '---|' * len(C.SK))
    for (tk, per), g in cv.group_by(['ticker', 'period'], maintain_order=True):
        d = {r['sk']: r for r in g.iter_rows(named=True)}
        w(f"| {tk} | {per} | {g['sessions'][0]} | " + ' | '.join(f"{d[f'{s}{k:g}']['coverage']} % (Δ≈{d[f'{s}{k:g}']['dprox_median']}, ${d[f'{s}{k:g}']['credit_median']:.0f})" if f'{s}{k:g}' in d else 'n/a' for s, k in C.SK) + ' |')
    w('\nCells: coverage % (median short-leg delta proxy, median credit $).  Skip reasons per entry in `results/coverage.csv` '
      '(`out_of_band` = strike beyond the stored ±2 % band; `out_of_band_spot` = spot outside the band at entry (amendment A1); `zero_bid` = a leg bid 0, mostly iron-condor wings).\n')
    if os.path.exists(os.path.join(R, 'diagnostics.md')):
        w('## 6. Post-hoc diagnostics of the hold-to-expiry (E2) result\n')
        w(open(os.path.join(R, "diagnostics.md")).read().split("\n", 3)[3].replace("\n## ", "\n### "))
    open(os.path.join(C.HERE, 'RESULTS.md'), 'w').write('\n'.join(P) + '\n')
    print('RESULTS.md', len(P), 'lines')


if __name__ == '__main__':
    main()
