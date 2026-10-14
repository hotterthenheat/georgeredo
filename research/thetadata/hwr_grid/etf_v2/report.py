"""Builds RESULTS.md (etf_v2) from the files in results/ (formatting and simple group-bys only; every number comes from a results file).
Original-study numbers shown for comparison are read from ../etf/results/."""
import os, sys, json, hashlib
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import analyze as A

R = C.OUT
RO = os.path.join(C.ORIG, 'results')


def f2(x, d=2):
    if x is None or (isinstance(x, float) and np.isnan(x)): return 'n/a'
    return f'{x:+.{d}f}' if isinstance(x, (float, int)) else str(x)


def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def ck(b): return '✓' if b else '✗'


def main():
    P = []; w = P.append
    G = pl.read_csv(os.path.join(R, 'grid.csv.gz'), infer_schema_length=10000)
    S = pl.read_csv(os.path.join(R, 'selected_test.csv'))
    SO = pl.read_csv(os.path.join(RO, 'selected_test.csv'))
    Y = pl.read_csv(os.path.join(R, 'selected_by_year.csv'))
    Bs = pl.read_csv(os.path.join(R, 'baselines.csv'))
    M = pl.read_csv(os.path.join(R, 'marginal_effects.csv'))
    WR = pl.read_csv(os.path.join(R, 'wr_vs_expectancy.csv'))
    CV = pl.read_csv(os.path.join(R, 'coverage.csv'), infer_schema_length=10000)
    J = json.load(open(os.path.join(R, 'grid_test_summary.json')))
    JO = json.load(open(os.path.join(RO, 'grid_test_summary.json')))
    IJ = json.load(open(os.path.join(R, 'integrity.json')))
    IS = pl.read_csv(os.path.join(R, 'integrity_summary.csv'))
    IM = pl.read_csv(os.path.join(R, 'integrity_missing.csv'), infer_schema_length=10000)
    IR = pl.read_csv(os.path.join(R, 'integrity_recovered.csv'))
    IRe = pl.read_csv(os.path.join(R, 'integrity_reach.csv'))
    V = json.load(open(os.path.join(R, 'validation_band_reproduction.json')))
    SE = pl.read_csv(os.path.join(R, 'settlement_spy.csv'))
    HS = pl.read_csv(os.path.join(R, 'stress_hist_summary.csv'))
    ST = pl.read_csv(os.path.join(R, 'stress_selected.csv'))
    SX = pl.read_csv(os.path.join(R, 'stress_extreme_days.csv'), infer_schema_length=10000)
    GT = pl.read_csv(os.path.join(R, 'gates.csv'))
    sel_v2 = json.load(open(os.path.join(R, 'selection_train.json')))
    sel_o = json.load(open(os.path.join(RO, 'selection_train.json')))
    scopes = [s for s in A.SCOPES if s in J['scopes']]

    w('# SPY / QQQ / IWM 0DTE short-premium grid on complete option chains (etf_v2): results\n')
    w(f'Re-run of the pre-registered grid of `../etf/` (protocol `PREREGISTRATION_original.md`, sha256 {sha(os.path.join(C.HERE, "PREREGISTRATION_original.md"))[:16]}…, '
      'identical to `../etf/PREREGISTRATION.md`; no rule changed) on the full same-day chains (`data_full`: every listed strike, no ±2 % band).  '
      f'TRAIN re-selection: `results/selection_train.json` (sha256 {J["selection_sha256"][:16]}…), written by `analyze.py train` from TRAIN trades only before '
      f'`analyze.py test` ran.  Original selections: `../etf/results/selection_train.json` (sha256 {sha(os.path.join(RO, "selection_train.json"))[:16]}…).  '
      'All $ are per 1-lot (one contract per leg) after bid/ask fills and $0.70 per contract per side.  CIs: 95 % bootstrap over trading days '
      '(5,000 draws, seed 7).  TRAIN 2022-11-11 → 2024-12-31 (IWM from 2024-04-19); TEST 2025-01-02 → 2026-10-09.  The TEST window was already '
      'seen (on band data) by the original study, so it is out of sample for the selection rule but not a fresh holdout.\n')
    w('**Code validation.**  Run on the original band dataset, this folder\'s engine reproduces the original per-trade and skip files exactly: ' +
      '; '.join(f"{k} {'identical' if v.get('trades_identical') and v.get('skips_identical') else 'DIFFERENT'} ({v.get('rows_orig')} rows)"
                for k, v in V.items() if isinstance(v, dict) and 'rows_orig' in v) +
      (f"; TRAIN selections identical: {V.get('selections_identical')}; selected-TEST rows compared {V.get('selected_test_rows_compared')}, "
       f"max |difference| {V.get('selected_test_max_abs_diff')}" if 'selections_identical' in V else '') + ' (`results/validation_band_reproduction.json`).\n')

    # ---------------------------------------------------------------- 1. data integrity
    w('## 1. Data integrity (full chains)\n')
    w('| ticker | sessions in window | full-chain files | .nodata | listed strikes per session, median (min) | sessions whose listed strikes span the whole 09:30–16:00 price range: full chains / original band | band rows found unchanged in the full pull |')
    w('|---|---|---|---|---|---|---|')
    for tk in C.TICKERS:
        m = IJ.get(f'{tk}_manifest')
        if not m: continue
        w(f"| {tk} | {m['sessions']} (of which {m['early_close']} early closes, excluded by design) | {m['full_files']} (sha256 each, `data_manifest.csv`) | {m['nodata']} | {m['strikes_median']} ({m['strikes_min']}) | "
          f"{m['covers_day_range']} / {IJ.get(f'{tk}_band_data_covers_day_range', 'n/a')} | {m['overlap_rows'] - m['overlap_quote_diff_rows']:,} of {m['overlap_rows']:,} quote rows identical; "
          f"band strikes ⊆ full strikes: {m['band_subset_all']}; band rows missing from the full pull: {m['band_rows_missing_in_full']} |")
    w('\nPer-entry check (engine.py `entry_status`, the trade loop\'s own skip rules, at every pre-registered entry, every seed-11..15 random-baseline minute, and every '
      'minute 10:00–14:30): a slot is one entry × structure-k.  Data reasons = a needed strike is not listed beyond spot ± k·EM / (k+1)·EM (`out_of_band`), spot outside '
      'the listed range (`out_of_band_spot`, amendment A1), or no usable quote at the entry minute (`no_quote`).  Market reasons (`zero_bid`, `no_credit`) are '
      'pre-registered skips that reflect the quote, not missing data.\n')
    w('| ticker | period | entry set | slots | traded-eligible (ok) | out_of_band | out_of_band_spot (A1) | no_quote | zero_bid | no_credit |')
    w('|---|---|---|---|---|---|---|---|---|---|')
    agg = IS.group_by(['ticker', 'period', 'entries']).agg([pl.col(c).sum() for c in ['slots', 'ok', 'out_of_band', 'out_of_band_spot', 'no_quote', 'zero_bid', 'no_credit']])
    for tk in C.TICKERS:
        for per in ('TRAIN', 'TEST'):
            for es in ('fixed', 'random', 'all_minutes'):
                g = agg.filter((pl.col('ticker') == tk) & (pl.col('period') == per) & (pl.col('entries') == es))
                if g.height == 0: continue
                r = g.row(0, named=True)
                w(f"| {tk} | {per} | {es} | {r['slots']:,} | {r['ok']:,} | {r['out_of_band']} | {r['out_of_band_spot']} | {r['no_quote']} | {r['zero_bid']} | {r['no_credit']} |")
    w(f"\nFixed or random-baseline entry slots still missing a needed strike or quote: **{IJ['missing_fixed_or_random_entries']}** "
      f"(by reason {IJ['missing_by_reason']}; list in `results/integrity_missing.csv`).")
    if IM.height:
        w('\n| ticker | period | date | entry | sk | reason |')
        w('|---|---|---|---|---|---|')
        for r in IM.head(40).iter_rows(named=True): w(f"| {r['ticker']} | {r['period']} | {r['date']} | {r['entry']} | {r['sk']} | {r['reason']} |")
        if IM.height > 40: w(f'\n({IM.height - 40} more rows in `results/integrity_missing.csv`.)')
    w('\nEntries the original band-data run skipped, and what they are on the full chains (`results/integrity_recovered.csv`):\n')
    w('| ticker | period | entries | original skip reason | now | entry × structure-k slots | sessions |')
    w('|---|---|---|---|---|---|---|')
    for r in IR.iter_rows(named=True):
        w(f"| {r['ticker']} | {r['period']} | {r['entries']} | {r['orig_reason']} | {r['now']} | {r['n']} | {r['sessions']} |")
    w('\nAmendment A1 (skip when spot at entry is outside the stored strike range): ' + '; '.join(
        f"{tk} {per}: originally {IJ.get(f'{tk}_{per}_orig_spot_outside_band_fixed')} fixed-entry slots on {IJ.get(f'{tk}_{per}_orig_spot_outside_band_fixed_sessions')} sessions, "
        f"now traded {IJ.get(f'{tk}_{per}_orig_spot_outside_band_fixed_now_traded')}"
        for tk in C.TICKERS for per in ('TRAIN', 'TEST') if f'{tk}_{per}_orig_spot_outside_band_fixed' in IJ) + '.\n')
    w('How far the listed strikes reach beyond spot, in units of the entry-time expected move EM (the widest structure needs 2.5 EM: condor k = 1.5 wings):\n')
    w('| ticker | period | entry set | slots | strikes per session (median) | reach above spot: min / 1st pct / median | reach below spot: min / 1st pct / median | slots with reach < 2.5 EM on either side |')
    w('|---|---|---|---|---|---|---|---|')
    for r in IRe.iter_rows(named=True):
        w(f"| {r['ticker']} | {r['period']} | {r['entries']} | {r['n']:,} | {r['strikes_median']} | {r['reach_up_min']} / {r['reach_up_p01']} / {r['reach_up_median']} | "
          f"{r['reach_dn_min']} / {r['reach_dn_p01']} / {r['reach_dn_median']} | {r['slots_reach_below_2p5EM']} |")

    # ---------------------------------------------------------------- 2. selections
    w('\n## 2. TRAIN selections and their TEST results on complete data\n')
    w('S1 = best TRAIN lower bound (TRAIN n ≥ 100); S2 = best TRAIN lower bound among TRAIN win ≥ 70 % (pre-registered).  `S1`/`S2` = re-selected on the full-chain '
      'TRAIN data; `S1-orig`/`S2-orig` = the original band-data TRAIN selections evaluated on complete TEST data; `PH-…` = the original post-hoc E1-only rule applied to '
      'the full-chain TRAIN grid (not pre-registered, not promotable).\n')
    w('| scope | original S1 / S2 (band TRAIN) | full-chain S1 / S2 | same? |')
    w('|---|---|---|---|')
    for sc in scopes:
        o = sel_o['scopes'].get(sc, {}); v = sel_v2['scopes'].get(sc, {})
        oc = (o.get('S1', {}).get('cfg'), (o.get('S2') or {}).get('cfg')); vc = (v.get('S1', {}).get('cfg'), (v.get('S2') or {}).get('cfg'))
        w(f"| {sc} | `{oc[0]}` / `{oc[1]}` | `{vc[0]}` / `{vc[1]}` | S1 {'yes' if oc[0] == vc[0] else 'no'}, S2 {'yes' if oc[1] == vc[1] else 'no'} |")
    w('\n| scope | sel | configuration | TRAIN (full chains) n / win / mean [CI] | TEST on band data (original run) n / mean [CI] | **TEST on complete data** n / win / mean [CI] | Bonferroni-8 LB | Romano–Wolf | PF / maxDD $ / worst trade $ | trades added by the full chains: n, Σ $, worst | common trades max |Δ| $ |')
    w('|---|---|---|---|---|---|---|---|---|---|---|')
    for r in S.iter_rows(named=True):
        o = SO.filter((pl.col('scope') == r['scope']) & (pl.col('cfg') == r['cfg']))
        ob = f"{o['test_n'][0]} / {o['test_mean'][0]:+.2f} [{o['test_lo'][0]:+.2f}, {o['test_hi'][0]:+.2f}]" if o.height else 'not evaluated'
        nw = (r['new_only_worst'].split('; ')[0] if isinstance(r.get('new_only_worst'), str) and r['new_only_worst'] else '')
        w(f"| {r['scope']} | {r['selection']} | `{r['cfg']}` {r['desc']} | {r['train_n']} / {r['train_wr']:.1f} % / {r['train_mean']:+.2f} [{r['train_lo']:+.2f}, {r['train_hi']:+.2f}] | {ob} | "
          f"**{r['test_n']} / {r['test_wr']:.1f} % / {r['test_mean']:+.2f} [{r['test_lo']:+.2f}, {r['test_hi']:+.2f}]** | {r['test_lo_bonf8']:+.2f} | {'rejected' if r['rw_rejected_test'] else 'not rejected'} | "
          f"{r['test_pf']:.2f} / {r['test_mdd']:.0f} / {r['test_worst_trade']:.0f} | {r.get('new_only_n')}, {f2(r.get('new_only_sum'))}, {nw} | {f2(r.get('common_max_abs_diff'), 4)} |")
    w('\nWorst five TEST days of each selection on complete data (date, $ summed over the scope\'s tickers):\n')
    seen = set()
    for r in S.iter_rows(named=True):
        if (r['scope'], r['cfg']) in seen: continue
        seen.add((r['scope'], r['cfg']))
        w(f"- {r['scope']} `{r['cfg']}`: {r['test_worst5']}")
    w('\nBy calendar year (TEST, complete data):\n')
    w('| scope | sel | config | year | n | win % | mean $ [CI] | PF | maxDD $ |')
    w('|---|---|---|---|---|---|---|---|---|')
    for r in Y.iter_rows(named=True):
        w(f"| {r['scope']} | {r['selection']} | `{r['cfg']}` | {r['year']} | {r['n']} | {r['wr']} | {r['mean']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] | {r['pf']} | {r['mdd']:.0f} |")

    # ---------------------------------------------------------------- 3. random baselines
    w('\n## 3. Random-entry baselines on matched days\n')
    w('Entry minute uniform 10:00–14:30 (seeds 11–15, the committed minute list), same structure, k, TP, stop, exit and filter.  Pre-registered gate item: TEST mean − '
      'mean of the five baselines > mean round-trip cost (unpaired).  Matched: lane and baseline on the same (ticker, date) pairs only (paired, averaged over seeds, day-clustered CI).  '
      '"Baseline-only" = baseline trades on days the lane did not trade (the one-sided days of the original study).\n')
    w('| scope | sel | config | lane TEST mean | baseline mean (5 seeds) | unpaired diff (pre-registered) | matched pairs | matched lane mean | matched baseline mean | paired diff [CI] | round trip $ | baseline-only trades (mean $) | beats random by > cost: unpaired / matched |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for r in S.iter_rows(named=True):
        w(f"| {r['scope']} | {r['selection']} | `{r['cfg']}` | {r['test_mean']:+.2f} | {r['base_mean']:+.2f} | {r['lane_minus_base']:+.2f} | {r['paired_n']} | {r['matched_lane_mean']:+.2f} | "
          f"{r['matched_base_mean']:+.2f} | {r['paired_diff']:+.2f} [{r['paired_lo']:+.2f}, {r['paired_hi']:+.2f}] | {r['test_cost']:.2f} | {r['base_only_trades']} ({f2(r['base_only_mean'])}) | "
          f"{ck(r['gate_beats_random'])} / {ck(r['gate_beats_random_matched'])} |")
    w('\nPre-registered four-item gate of the original study (TEST LB > 0, n ≥ 150, ≥ 3 months, beats random by > cost, unpaired), on complete data:\n')
    w('| scope | sel | config | items | verdict | TEST win ≥ 70 % |')
    w('|---|---|---|---|---|---|')
    for r in S.iter_rows(named=True):
        g = ''.join(ck(r[k]) for k in ('gate_lb_pos', 'gate_n150', 'gate_months3', 'gate_beats_random'))
        w(f"| {r['scope']} | {r['selection']} | `{r['cfg']}` | {g} | **{'PASS' if r['gate_pass'] else 'FAIL'}** | {'yes' if r['objective_wr70'] else 'no'} |")
    w('\nPer-seed baselines (TEST, complete data):\n')
    w('| scope | sel | seed | n | win % | mean $ [CI] |')
    w('|---|---|---|---|---|---|')
    for r in Bs.iter_rows(named=True):
        w(f"| {r['scope']} | {r['selection']} | {r['seed']} | {r['n']} | {r['wr']} | {r['mean']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] |")

    # ---------------------------------------------------------------- 4. full grid
    w('\n## 4. Full grid in TEST: lower bounds > 0 vs chance, and the max-statistic reality check\n')
    w('Chance count: recentred joint day bootstrap (seed 8, 5,000 draws, correlation across configurations kept).  Reality check: studentised max-t over configurations with TEST n ≥ 30; '
      'Romano–Wolf step-down at FWER 5 %.  "band" = the original run on band data (`../etf/results/grid_test_summary.json`).\n')
    w('| scope | data | distinct configs | TEST days | TEST LB > 0 | chance mean / p95 | LB > 0 among TRAIN-win≥70 | chance mean / p95 | win ≥ 70 % & LB > 0 | White RC best t (config), p | Romano–Wolf rejections | Spearman TRAIN vs TEST mean |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for sc in scopes:
        for lab, JJ in (('band', JO), ('complete', J)):
            j = JJ['scopes'].get(sc)
            if not j: continue
            w(f"| {sc} | {lab} | {j['distinct_configs']} | {j['test_days']} | {j['lb_pos']} | {j['chance_lb_pos_mean']} / {j['chance_lb_pos_p95']:.0f} | {j['lb_pos_among_train_wr70']} of {j['train_wr70_configs']} | "
              f"{j['chance_among_train_wr70_mean']} / {j['chance_among_train_wr70_p95']:.0f} | {j['lb_pos_and_wr70']} | {j['rc_best_t']} (`{j['rc_best_cfg']}`), p = {j['rc_p']} | {j['romano_wolf_rejections']} | {j['spearman_train_test_mean']} |")
    w('\nRomano–Wolf-rejected configurations by exit and structure (TEST, complete data):\n')
    w('| scope | E1 | E2 | straddle/strangle | iron condor |')
    w('|---|---|---|---|---|')
    for sc in scopes:
        rj = J['scopes'][sc]['rw_rejected']
        w(f"| {sc} | {sum(1 for c in rj if '|E1|' in c)} | {sum(1 for c in rj if '|E2|' in c)} | {sum(1 for c in rj if c.startswith('S'))} | {sum(1 for c in rj if c.startswith('I'))} |")
    w('\nTEST lower-bound quantiles over the distinct grid (complete data): ' + '; '.join(f"{sc} {J['scopes'][sc]['test_lb_quantiles']}" for sc in scopes) + '\n')

    # ---------------------------------------------------------------- 5. grid structure
    w('## 5. Win rate vs expectancy, rule effects and coverage (complete data)\n')
    w('Median over the distinct configurations in each cell:\n')
    w('| scope | structure-k | exit | TRAIN median win % | TRAIN median mean $ | TRAIN LB>0 | TEST median win % | TEST median mean $ | TEST LB>0 |')
    w('|---|---|---|---|---|---|---|---|---|')
    D = G.filter(~pl.col('dup') & (pl.col('ex') != 'E0'))
    for sc in scopes:
        t = D.filter(pl.col('scope') == sc).group_by(['sk', 'ex']).agg(pl.col('train_wr').median().alias('a'), pl.col('train_mean').median().alias('b'), (pl.col('train_lo') > 0).sum().alias('c'),
                                                                      pl.col('test_wr').median().alias('d'), pl.col('test_mean').median().alias('e'), (pl.col('test_lo') > 0).sum().alias('f')).sort(['sk', 'ex'])
        for r in t.iter_rows(named=True):
            w(f"| {sc} | {r['sk']} | {r['ex']} | {r['a']:.1f} | {f2(r['b'])} | {r['c']} | {r['d']:.1f} | {r['e']:+.2f} | {r['f']} |")
    w('\nBy TRAIN win-rate bin:\n')
    w('| scope | TRAIN win % bin | configs | TRAIN median mean $ | TRAIN LB>0 | TEST median win % | TEST median mean $ | TEST LB>0 | TEST mean > 0 (% of configs) |')
    w('|---|---|---|---|---|---|---|---|---|')
    for r in WR.iter_rows(named=True):
        w(f"| {r['scope']} | {r['train_wr_bin']} | {r['configs']} | {r['train_mean_median']:+.2f} | {r['train_lb_pos']} | {r['test_wr_median']} | {r['test_mean_median']:+.2f} | {r['test_lb_pos']} | {r['test_mean_pos_share']} |")
    w('\nMatched-pair rule effects (SPY+QQQ and IWM; per-ticker rows in `results/marginal_effects.csv`):\n')
    w('| scope | period | factor: ref → alt | pairs | median Δ win (pts) | median Δ mean $ | share with higher mean | median Δ LB $ | note |')
    w('|---|---|---|---|---|---|---|---|---|')
    for r in M.filter(pl.col('scope').is_in(['SPY+QQQ', 'IWM'])).iter_rows(named=True):
        w(f"| {r['scope']} | {r['period']} | {r['factor']}: {r['ref']} → {r['alt']} | {r['pairs']} | {r['d_wr_median']:+.2f} | {r['d_mean_median']:+.2f} | {r['share_mean_up']} % | {r['d_lo_median']:+.2f} | {r['note'] or ''} |")
    w('\nCoverage (share of sessions with a trade, mean over the four entries; `results/coverage.csv`):\n')
    cv = CV.group_by(['ticker', 'period', 'sk']).agg(pl.col('coverage').mean().round(1), pl.col('sessions').first()).sort(['ticker', 'period', 'sk'])
    w('| ticker | period | sessions | ' + ' | '.join(f'{s}{k:g}' for s, k in C.SK) + ' |')
    w('|---|---|---|' + '---|' * len(C.SK))
    for (tk, per), g in cv.group_by(['ticker', 'period'], maintain_order=True):
        d = {r['sk']: r for r in g.iter_rows(named=True)}
        w(f"| {tk} | {per} | {g['sessions'][0]} | " + ' | '.join(f"{d[f'{s}{k:g}']['coverage']} %" if f'{s}{k:g}' in d else 'n/a' for s, k in C.SK) + ' |')

    # ---------------------------------------------------------------- 6. settlement
    w('\n## 6. Settlement realism of hold-to-expiry (E2) — optimistic for the ETFs\n')
    w('SPY, QQQ and IWM options are American and physically settled; they trade until 16:15 ET and can be exercised on after-hours moves.  Every E2 number in this file values the '
      'legs at intrinsic against the 16:00 close (15:59-bar close) and is **optimistic**.  Only SPY can be re-valued (inputs: EOD close and 17:15 quote mid per date in '
      '`../etf/results/diag_settlement_spy.csv`, unchanged).  Columns as in the original diagnostic B; `results/settlement_spy.csv`.\n')
    w('| config | used by | period | trades (with after-hours data) | (1) as run, 16:00 | (2) EOD close | (3) auto-exercise, shares closed 17:15 | (4) rational after-hours exercise | (5) pessimistic |')
    w('|---|---|---|---|---|---|---|---|---|')
    for r in SE.iter_rows(named=True):
        cell = lambda k: f"{r[k + '_mean']:+.2f} [{r[k + '_lo']:+.2f}, {r[k + '_hi']:+.2f}]"
        w(f"| `{r['cfg']}` | {r['used_by']} | {r['period']} | {r['n_trades']} ({r['n_with_ah']}) | {cell('as_run_1600')} | {cell('eod_close')} | {cell('auto_exercise_ah')} | {cell('rational_ah')} | {cell('pessimistic_ah')} |")

    # ---------------------------------------------------------------- 7. stress
    w('\n## 7. Tail stress\n')
    w('Historical entry-to-close moves (close of the 15:59 bar vs close of the bar before entry), 1-minute underlying series, all full sessions 2017-06-01 → 2026-10-09 '
      '(`results/stress_hist_summary.csv`, top 10 per side in `results/stress_hist_moves.csv`):\n')
    w('| ticker | entry | sessions | worst down % (date) | worst up % (date) | 2025-04-09 % |')
    w('|---|---|---|---|---|---|')
    for r in HS.iter_rows(named=True):
        w(f"| {r['ticker']} | {r['entry'] if r['entry'] != 'any' else 'any minute 10:00–14:30'} | {r['sessions']} | {r['worst_down_pct']:+.2f} ({r['worst_down_date']}) | {r['worst_up_pct']:+.2f} ({r['worst_up_date']}) | {f2(r['move_20250409_pct'])} |")
    w('\nSettlement P&L per 1-lot if the underlying ends the day at entry spot × (1 + move), every leg expiring (unprotected: no stop fill assumed), over the selection\'s TEST trades '
      '(median trade / worst trade); capital per lot for an 8 % max-loss budget; margin estimates per lot (formula-based, not broker-verified).  `results/stress_selected.csv`.\n')
    w('| scope | sel | config | n | median credit $ | −5 % | +5 % | −8.42 % | +8.42 % | −10 % | +10 % | −15 % | +15 % | worst historical down (move) | worst historical up (move) | capital/lot, 8 % budget, ±15 % (median trade) | stop at trigger (optimistic) | Reg-T 20 % / 15 % | PM-style −8/+6 % |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for r in ST.iter_rows(named=True):
        c = lambda x: f"{r[f'pnl_{x}_median']:+.0f} / {r[f'pnl_{x}_worst']:+.0f}"
        w(f"| {r['scope']} | {r['selection']} | `{r['cfg']}` | {r['n']} | {r['credit_median']:.0f} | {c('-5.00')} | {c('+5.00')} | {c('-8.42')} | {c('+8.42')} | {c('-10.00')} | {c('+10.00')} | {c('-15.00')} | {c('+15.00')} | "
          f"{r['pnl_hist_down_median']:+.0f} / {r['pnl_hist_down_worst']:+.0f} ({r['hist_down_pct']}) | {r['pnl_hist_up_median']:+.0f} / {r['pnl_hist_up_worst']:+.0f} ({r['hist_up_pct']}) | "
          f"{r['capital_8pct_budget_15pct_median']:,.0f} | {f2(r['stop_trigger_loss_median'], 0)} | {r['regt_20pct_median']:,.0f} / {r['regt_15pct_median']:,.0f} | {r['pm_scen_-8_+6_median']:,.0f} |")
    w('\nRealized P&L of the pre-registered selections on the largest-move TEST days (now priced; `results/stress_extreme_days.csv`):\n')
    w('| scope | sel | config | date | move entry→close % | traded | P&L $ | exit |')
    w('|---|---|---|---|---|---|---|---|')
    for r in SX.filter(~pl.col('selection').str.starts_with('PH')).iter_rows(named=True):
        w(f"| {r['scope']} | {r['selection']} | `{r['cfg']}` | {r['date']} | {r['move_from_entry_pct']} | {r['traded']} | {f2(r['pnl'])} | {r['exit'] or ''} |")

    # ---------------------------------------------------------------- 8. gates
    w('\n## 8. COMPASS §10 gate verdicts\n')
    w('Carry lane = data integrity, execution realism, statistical validity (complete data, out of sample, Bonferroni over the 8 pre-registered selections), tail survival, '
      'forward validation, classification.  Signal lane = the same plus beating random entry on the same days by more than one round trip.  `results/gates.csv` has the detail text.\n')
    w('| scope | sel | config | data integrity | execution realism | statistical validity | tail survival | forward validation | classification | beats random (matched) | carry verdict | signal verdict |')
    w('|---|---|---|---|---|---|---|---|---|---|---|---|')
    for r in GT.iter_rows(named=True):
        w(f"| {r['scope']} | {r['selection']}{' (post-hoc)' if r['post_hoc'] else ''} | `{r['cfg']}` | {ck(r['data_integrity'])} | {ck(r['execution_realism'])} | {ck(r['statistical_validity'])} | "
          f"{ck(r['tail_survival'])} | {ck(r['forward_validation'])} | carry | {ck(r['beats_random_matched'])} | **{r['carry_verdict']}** | **{r['signal_verdict']}** |")
    w('\nItem detail for the full-chain TRAIN selections:\n')
    for r in GT.filter(pl.col('selection').is_in(['S1', 'S2'])).iter_rows(named=True):
        w(f"- **{r['scope']} {r['selection']} `{r['cfg']}`** — data: {r['data_integrity_detail']}. Execution: {r['execution_realism_detail']}. Statistics: {r['statistical_validity_detail']}. "
          f"Tail: {r['tail_survival_detail']}. Forward: {r['forward_validation_detail']}. Random entry: {r['beats_random_detail']}.")
    open(os.path.join(os.path.dirname(os.path.abspath(C.OUT)), 'RESULTS.md'), 'w').write('\n'.join(P) + '\n')   # etf_v2/RESULTS.md
    print('RESULTS.md', len(P), 'lines')


if __name__ == '__main__':
    main()
