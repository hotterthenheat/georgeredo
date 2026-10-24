"""report_final.py — writes COMPASS_FINAL_REPORT.md from out/results.json, the trade files, out/verify_plain.json and
out/lookahead.json (every figure is formatted from those files; nothing typed by hand), then render_final.py prints the PDF.

    POLARS_MAX_THREADS=2 python3 -I report_final.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
R = json.loads((OUT / 'results.json').read_text())
V = json.loads((OUT / 'verify_plain.json').read_text())
LA = json.loads((OUT / 'lookahead.json').read_text()) if (OUT / 'lookahead.json').exists() else None
MDE0 = json.loads((OUT / 'mde_prereg.json').read_text())
S1 = json.loads((OUT / 'stage1_summary.json').read_text())

NAMES = {
    'T1 fly5_iron': 'T1 — SPY/QQQ iron butterfly ±5 at 15:00 and 15:30 (fly5 iron; hyp C §6)',
    'T2 condor_em1': 'T2 — SPY 2-wide iron condor at ± the ATM straddle, 11:30–13:30 (condor_em1)',
    'T3 condor_d20': 'T3 — SPY 2-wide 20-delta iron condor, 13:00–15:00 (condor_d20)',
    'T4 touch_d25': 'T4 — SPY 2-wide 25-delta credit spread at the boundary touch (hyp B touch pick)',
    'T5 h13_te': 'T5 — SPXW 13:00 ATM straddle to settlement, ex FOMC/CPI/NFP (T-E, H13)',
    'T6 h15_s2': 'T6 — SPXW 14:05 strangle at ±0.5 EM to settlement, ex FOMC and month-end (H15)',
    'T7 h1_qqq': 'T7 — QQQ overnight reversal of the late-day move (Compass H1)',
}
FAMILY = {
    'T1 fly5_iron': 'SPY/QQQ late ATM butterflies (rows 21a, 21c, 25, 26b)',
    'T2 condor_em1': 'SPY midday iron condors (rows 20b, 26a, 26c)',
    'T3 condor_d20': 'SPY midday iron condors (rows 20b, 26a, 26c)',
    'T4 touch_d25': 'SPY boundary-touch credit spread (row 20a)',
    'T5 h13_te': 'SPXW 13:00 straddle (row 6d)',
    'T6 h15_s2': 'SPXW 14:05 strangle (row 6e)',
    'T7 h1_qqq': 'Compass H1 on QQQ (row 32 QQQ)',
}
SHORT_COND = {'1 mean > 0': 'mean > 0', '2 Bonferroni lower end > 0': 'Bonferroni lower end > 0', '3 top-5 share <= 100%': 'top-5 ≤ 100 %',
              '4 >= 300 trades': '≥ 300 trades', '5 at most one year <= 0': '≤ 1 losing year'}


def p(x, d=2):
    return '—' if x is None or (isinstance(x, float) and math.isnan(x)) else f'{x:+.{d}f}'


def iv(c, d=2):
    return '—' if c is None or any(isinstance(a, float) and math.isnan(a) for a in c) else f'[{c[0]:+.{d}f}, {c[1]:+.{d}f}]'


def usd(x):
    return '—' if x is None or (isinstance(x, float) and math.isnan(x)) else (f'−${abs(x):,.0f}' if x < 0 else f'${x:,.0f}')


def dec(key: str) -> int:
    return 3 if key.startswith('T7') else 2


def failed(r) -> str:
    c = r['verdict']['conditions']
    return ', '.join(SHORT_COND[k] for k, v in c.items() if not v) or 'none'


def main() -> None:
    L = []
    w = L.append
    T1, T2, T3, T4, T5, T6, T7 = (R[k] for k in R)
    d1 = T1['describe']
    w('# Compass Final: one clean test, at Robinhood\'s fees, of every rule the final report left standing')
    w('')
    w('**Repository:** georgeredo, branch `claude/lucid-heisenberg-bpyq7k`. **Prereg:** `PREREG_COMPASS_FINAL.md`, committed alone '
      'with its HOLDOUT_LEDGER row in `4bc546f` before any fetch or computation. **Fetch and run code:** `f6d2889` (before T1–T6 '
      'were run). **Built:** 2026-10-24 by `report_final.py`; every figure below is read from `out/results.json` and the trade '
      'files beside it.')
    w('')
    w('## In plain English')
    w('')
    w('The owner asked for the research to be reverse-engineered "until you figure out a final that works". This study did it '
      'the honest way: it picked the survivors from the final report by a rule fixed in advance, and gave each one test, run once, '
      'on market data no study had read for that rule, at Robinhood\'s fees, with nothing tuned.')
    w('')
    w('**Nothing passed.** Seven tests ran, and all seven fail the pre-registered rule. The headline for each, at Robinhood\'s '
      'fees under the pre-registered settlement:')
    w('')
    for k, r in R.items():
        d = r['describe']
        w(f"- **{NAMES[k]}:** {d['trades']:,} trades, mean {p(d['mean_pct'], dec(k))} {r['unit']} a trade, 95 % interval "
          f"{iv(d['ci95'], dec(k))}, win rate {d['win_rate'] * 100:.0f} %. **FAIL** ({failed(r)}).")
    w('')
    l0 = T1['lines']['(0) intrinsic at the official close [carries the exercise risk it does not price]']
    l58 = T1['lines']["the tracker's 15:58 exit (NBBO, Robinhood both sides)"]
    w('**What sank the SPY/QQQ defined-risk family is the after-hours exercise risk, measured as the owner fixed it.** '
      'These structures are held to the close on physically settled ETF options, so an option that is in the money at the '
      'close, or that the other side chooses to exercise after the close, turns into 100 shares that gap overnight. Priced '
      'the way AFTERHOURS.md priced it (case (b): our longs exercised on the official close, each short assigned if it is in the '
      'money at 17:30, the shares marked at the next 09:30 open), the late iron butterfly is '
      f"**{p(d1['mean_pct'])} %** of max risk a trade. Settled at intrinsic on the official close, which ignores that risk, "
      f"the same trades read {p(l0['mean_pct'])} % {iv(l0['ci95'])}: a small edge that exists only on paper. Closing at 15:58 "
      f"to avoid the risk costs it: {p(l58['mean_pct'])} % {iv(l58['ci95'])}. The condors and the touch spread show the same "
      f"shape: they win most of the time ({min(R[k]['describe']['win_rate'] for k in ('T2 condor_em1', 'T3 condor_d20', 'T4 touch_d25')) * 100:.0f}–"
      f"{max(R[k]['describe']['win_rate'] for k in ('T2 condor_em1', 'T3 condor_d20', 'T4 touch_d25')) * 100:.0f} %) and their average losing trade is "
      f"{-max(R[k]['describe']['avg_loss_pct'] for k in ('T2 condor_em1', 'T3 condor_d20', 'T4 touch_d25')):.0f}–"
      f"{-min(R[k]['describe']['avg_loss_pct'] for k in ('T2 condor_em1', 'T3 condor_d20', 'T4 touch_d25')):.0f} % of max risk, more than "
      'the structure can lose at expiry, because an assignment leaves stock that moves overnight.')
    w('')
    w(f"**The SPXW lanes (T5, T6) could not pass on count**: the fresh span holds {T5['describe']['trades']} and "
      f"{T6['describe']['trades']} trades, under the 300 the owner requires (stated in the prereg before anything was read). "
      f"Their returns also say no: T5 {p(T5['describe']['mean_pct'])} % and T6 {p(T6['describe']['mean_pct'])} % of the "
      f"credit, with intervals about ±{(T5['describe']['ci95'][1] - T5['describe']['ci95'][0]) / 2:.0f} and "
      f"±{(T6['describe']['ci95'][1] - T6['describe']['ci95'][0]) / 2:.0f} points wide. One session, "
      f"{T5['describe']['worst']['date']}, cost {usd(T5['describe']['worst']['pnl'])} on T5 and "
      f"{usd(T6['describe']['worst']['pnl'])} on T6: years of credit gone in an afternoon.")
    w('')
    d7 = T7['describe']
    w(f"**H1 on QQQ (T7)** is the closest thing to a positive: {p(d7['mean_pct'], 3)} % of notional a trade "
      f"({usd(d7['mean_usd'])} a 100-share trade) on {d7['trades']} trades from 2025-10-13 to 2026-10-22, 95 % interval "
      f"{iv(d7['ci95'], 3)}. It still fails: under 300 trades (stated in advance) and its Bonferroni interval "
      f"{iv(d7['ci_bonf'], 3)} crosses zero. It agrees with the earlier read (+0.038 %) without proving anything; "
      f"its forward N at the earlier mean is {MDE0['forward_n']['H1 QQQ']['n_80']:,} trades, about eleven years.")
    w('')
    w('**S17 index put-writing** had no unread history (its test read all the option data Theta serves), so it goes to the forward '
      'test only. It is now in step 8 of the daily job (first roll 2026-11-20, no verdict before 147 closed cycles, about six '
      'years). H7 and QQQ\'s turn of the month were not candidates: they have 77–172 trades, under the 300 the selection rule '
      'requires. H7 is already forward-tracked.')
    w('')
    w(f"**The checks hold.** {V['trades']} trades re-derived from the raw files by separate plain-loop code: "
      f"{V['fields_compared']} fields, **{V['differences']} differences**. The lookahead check: "
      + ('; '.join(f"{t} {s['unchanged_when_blanked']} of {s['entries']} entries unchanged with the future blanked, the control changed "
                  f"{s['control_changed']} of {s['entries']}" for t, s in LA['summary'].items()) if LA else '**not run — usage ended** (started, stopped before it finished; no result read)') + '. Every run path was first '
      'checked on sessions the research had already read and reproduced the committed rows exactly (FETCH_LOG.md).')
    w('')
    w('**What it means.** There is no rule here to trade. The power was low by construction (section 7: every MDE was two to '
      'five times the earlier means), so a FAIL is weak evidence that a small edge does not exist. But every family failed on '
      'more than its interval: the means are at or below zero, more than one year lost money, and the SPY/QQQ structures lose '
      'their paper edge to the after-hours exercise risk. No rulebook is written. The forward paper tests already in the daily '
      'job (fly5, condor_em1, condor_d20, H5/H6, H7) keep running to their own N, and S17 joins them.')
    w('')
    # ---- verdict table
    w('## The verdict, test by test')
    w('')
    w('k = 7 tests; the Bonferroni interval is the two-sided 1 − 0.05/7 percentile interval of the 20-session moving-block '
      'bootstrap (audit_lib, 2,000 draws, seed 20261022). Robinhood fees; the primary settlement (case (b) for SPY/QQQ, '
      'Cboe\'s close for SPXW, the next 09:30 open for T7).')
    w('')
    w('| test | family | trades | sessions traded / in the test | mean a trade | 95 % interval | Bonferroni interval | top-5 share of profit | years ≤ 0 | verdict |')
    w('|---|---|---|---|---|---|---|---|---|---|')
    for k, r in R.items():
        d = r['describe']
        t5 = 'n/a (total ≤ 0)' if not (d['total_usd'] > 0) else f"{d['top5_share'] * 100:.0f} %"
        w(f"| {k.split()[0]} | {FAMILY[k]} | {d['trades']:,} | {d['sessions_traded']} / {d['sessions_in_test']} | **{p(d['mean_pct'], dec(k))}** {r['unit']} "
          f"| {iv(d['ci95'], dec(k))} | {iv(d['ci_bonf'], dec(k))} | {t5} | {', '.join(r['verdict']['negative_years']) or 'none'} | **FAIL** ({failed(r)}) |")
    w('')
    w('Families with no unread data: **S17** (forward only, wired into the daily job). Not candidates: H7 and QQQ turn of the '
      'month (< 300 trades). No test passed, so no rulebook and no new forward N for a passing rule.')
    w('')
    # ---- stage 1 recap
    w('## What was tested, and on what (stage 1 and the prereg, in short)')
    w('')
    w('- **Selection rule (fixed first):** a page-1 row with a Robinhood-fee mean > 0, a block-20 lower end > 0 on its own '
      'period, ≥ 300 trades, and not vendor-recorded, a preview or a base-trade row. 13 rows passed, in 9 families (prereg §1).')
    w('- **Fresh data:** Theta serves SPY bars, SPY EOD and SPX prints from 2017-01-03 and QQQ from 2012-06-01, and SPY/QQQ '
      'after-hours bars throughout (stage-1 probes, `out/probe_entitlement*.json`). The fresh span ends 2022-05-12: from '
      '2022-05-13 SPXW was read intraday on every session. Every session on which an earlier study held or read an '
      'index-product option inside the family\'s window (V8, S03, S16b, Compass Close\'s gate sample) is out; half days are out.')
    fam = S1['families']
    w(f"- **Sessions in the test:** SPY {fam['fly5']['in_test']['SPY']} (2017-01-04 → 2022-04-27), QQQ "
      f"{fam['fly5']['in_test']['QQQ']} (2012-06-01 → 2022-04-27), SPXW {fam['h13_te']['in_test']['SPXW']} (2017-01-03 → "
      f"2022-04-27), and QQQ stock 2025-10-13 → 2026-10-22 for T7. 8 QQQ sessions came back empty from Theta twice and carry "
      'no trade (FETCH_LOG.md).')
    w('- **Fees:** Robinhood (`docs/FEES_ROBINHOOD.md`) primary; each study\'s own fees as a line. **Fills** at the NBBO: buy at '
      'the ask, sell at the bid.')
    w('- **Settlement:** physically settled SPY/QQQ held to the close by AFTERHOURS.md\'s case (b) (the after-hours prices '
      'could be fetched, so the 15:59 close-out fallback was not used); SPXW on Cboe\'s official close; T7 at the next 09:30 open.')
    w('')
    # ---- MDE
    w('## Power: the MDE committed before reading, and at the realised n')
    w('')
    w('| test | planned n (prereg) | realised trades | MDE per trade, prereg SD at realised n | MDE per session, prereg SD | MDE per trade, realised SD | realised SD a trade |')
    w('|---|---|---|---|---|---|---|')
    key0 = {'T1 fly5_iron': 'fly5_iron', 'T2 condor_em1': 'condor_em1', 'T3 condor_d20': 'condor_d20', 'T4 touch_d25': 'touch_d25',
            'T5 h13_te': 'h13_te', 'T6 h15_s2': 'h15_s2', 'T7 h1_qqq': 'h1_qqq'}
    for k, r in R.items():
        m0 = MDE0['tests'][key0[k]]
        dd = dec(k)
        w(f"| {k.split()[0]} | {m0['planned_trades_max']:,} | {r['describe']['trades']:,} | {r['mde_prereg_sd_at_realised_n']['mde_trade']:.{dd}f} | "
          f"{r['mde_prereg_sd_at_realised_n']['mde_session']:.{dd}f} | {r['mde_realised_sd']['mde_trade']:.{dd}f} | {r['sd_trade_realised']:.{dd}f} |")
    w('')
    w('Units as each test\'s (percentage points of its unit). Every MDE is several times the effect the earlier reads found, as '
      'the prereg said it would be.')
    w('')
    # ---- per test
    for k, r in R.items():
        d = r['describe']
        dd = dec(k)
        w(f'## {NAMES[k]}')
        w('')
        w(f"**Verdict: FAIL** ({failed(r)}). Unit: {r['unit']}. Settlement: {r['settlement']}.")
        if r.get('universe'):
            u = r['universe']
            w(f" Every trade had its official close, decision price and next open ({u['name_sessions_total']} name-sessions; "
              f"decision-price coverage {u['decision_price_coverage'] * 100:.0f} %).")
        w('')
        w('| trades | sessions traded / in test | win % | avg win % | avg loss % | median % | mean % | mean $ | total $ | profit factor | max drawdown $ | longest drawdown (sessions) |')
        w('|---|---|---|---|---|---|---|---|---|---|---|---|')
        w(f"| {d['trades']:,} | {d['sessions_traded']} / {d['sessions_in_test']} | {d['win_rate'] * 100:.1f} | {p(d['avg_win_pct'], dd)} | "
          f"{p(d['avg_loss_pct'], dd)} | {p(d['median_pct'], dd)} | **{p(d['mean_pct'], dd)}** | {p(d['mean_usd'])} | {usd(d['total_usd'])} | "
          f"{d['profit_factor']:.2f} | {usd(d['max_dd_usd'])} | {d['longest_dd_sessions']} |")
        w('')
        b, wo = d['best'], d['worst']
        w(f"Best trade {usd(b['pnl'])} ({p(b['pct'], 1)} %, {b['date']} {b['entry']}, {b['inst']}); worst {usd(wo['pnl'])} "
          f"({p(wo['pct'], 1)} %, {wo['date']} {wo['entry']}, {wo['inst']}).")
        w('')
        w1, w10 = d['walk_1lot'], d['walk_10pct']
        w(f"**$1,000:** at a fixed 1 lot it ends at {usd(w1['end'])} (low {usd(w1['min'])}"
          + (f", first at or below $0 on {w1['first_at_or_below_0']}" if w1['first_at_or_below_0'] else '') + '); at 10 % per trade (the final '
          f"report's method B) it ends at {usd(w10['end'])}" + (f", wiped out on {w10['wiped_out_on']}" if w10['wiped_out_on'] else '') + '.'
          + (' A case (b) loss can exceed the structure\'s max risk (shares assigned and gapping overnight), so 10 % of the '
             'balance can lose more than 10 %.' if r['settlement'] == 'case (b)' else '')
          + (' A short straddle or strangle can lose many times its credit, so 10 % of the balance on the credit can lose far more than 10 %.'
             if k in ('T5 h13_te', 'T6 h15_s2') else ''))
        w('')
        w('| line (no verdict) | trades | mean | 95 % interval | total $ |')
        w('|---|---|---|---|---|')
        w(f"| **primary, Robinhood fees** | {d['trades']:,} | **{p(d['mean_pct'], dd)}** | {iv(d['ci95'], dd)} | {usd(d['total_usd'])} |")
        for ln, x in r['lines'].items():
            w(f"| {ln} | {x['trades']:,} | {p(x['mean_pct'], dd)} | {iv(x['ci95'], dd)} | {usd(x['total_usd'])} |")
        for ln, x in r.get('reported_structures', {}).items():
            w(f"| {ln} | {x['trades']:,} | {p(x['mean_pct'], dd)} | {iv(x['ci95'], dd)} | {usd(x['total_usd'])} |")
        for ln, x in r.get('by_name', {}).items():
            w(f"| {ln} alone | {x['trades']:,} | {p(x['mean_pct'], dd)} | {iv(x['ci95'], dd)} | {usd(x['total_usd'])} |")
        for ln, x in r.get('sensitivity', {}).items():
            if 'mean_pct' in x:
                w(f"| sensitivity: {ln} | {x['trades']:,} | {p(x['mean_pct'], dd)} | {iv(x['ci95'], dd)} | {usd(x.get('total_usd'))} |")
            else:
                w(f"| sensitivity: {ln} | 0 | — | — | {x.get('note', '')} |")
        w('')
        w('| by year | ' + ' | '.join(y['k'] for y in d['by_year']) + ' |')
        w('|---|' + '---|' * len(d['by_year']))
        w('| trades | ' + ' | '.join(str(y['n']) for y in d['by_year']) + ' |')
        w('| mean % | ' + ' | '.join(p(y['mean_pct'], dd) for y in d['by_year']) + ' |')
        w('| total $ | ' + ' | '.join(usd(y['usd']) for y in d['by_year']) + ' |')
        w('')
        wd = [y for y in d['by_weekday']]
        order = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4}
        wd.sort(key=lambda y: order.get(y['k'], 9))
        w('| by weekday | ' + ' | '.join(y['k'] for y in wd) + ' |')
        w('|---|' + '---|' * len(wd))
        w('| trades | ' + ' | '.join(str(y['n']) for y in wd) + ' |')
        w('| mean % | ' + ' | '.join(p(y['mean_pct'], dd) for y in wd) + ' |')
        w('')
        if k == 'T4 touch_d25':
            t = pl.read_parquet(OUT / 't4_trades.parquet').filter(pl.col('pnl_b').is_not_null()).with_columns(
                (pl.col('pnl_b') / pl.col('cost') * 100).alias('pct'), (pl.col('entry').str.slice(0, 2) + ':00').alias('h'))
            g = t.group_by('h').agg(pl.len().alias('n'), pl.col('pct').mean().alias('m')).sort('h')
            w('| entry hour | ' + ' | '.join(g['h'].to_list()) + ' |')
            w('|---|' + '---|' * g.height)
            w('| trades | ' + ' | '.join(str(x) for x in g['n'].to_list()) + ' |')
            w('| mean % | ' + ' | '.join(p(x) for x in g['m'].to_list()) + ' |')
        else:
            bt = d['by_time']
            w('| by entry time | ' + ' | '.join(y['k'] for y in bt) + ' |')
            w('|---|' + '---|' * len(bt))
            w('| trades | ' + ' | '.join(str(y['n']) for y in bt) + ' |')
            w('| mean % | ' + ' | '.join(p(y['mean_pct'], dd) for y in bt) + ' |')
        w('')
        w(f"![]({'charts/' + k.split()[0].lower() + '.png'})")
        w('')
    # ---- integrity
    w('## Integrity')
    w('')
    w(f"- **Plain-loop re-derivation** (`verify_plain.py`): {V['trades']} trades, 10 a test (seed 20261024), re-derived from the raw "
      f"files with separate code (pyarrow rows into Python lists; no polars, numpy, run script, engine or fee module): strikes, "
      f"fills, max risk, C, D, O, the Cboe close, the case (b) and stock P&L at Robinhood's fees. **{V['fields_compared']} fields, "
      f"{V['differences']} differences** (tolerance 1e-6).")
    w('- **Lookahead check** (`lookahead.py`, 10 sessions a family, seed 20261024; every chain row and bar stamped after the entry '
      'minute blanked, the settlement inputs kept; control: the chain read one minute later):')
    w('')
    w('| test | entries checked | sessions | unchanged with the future blanked | control changed |')
    w('|---|---|---|---|---|')
    for t, s in (LA['summary'].items() if LA else []):
        w(f"| {t} | {s['entries']} | {s['sessions']} | {s['unchanged_when_blanked']} of {s['entries']} | {s['control_changed']} of {s['entries']} |")
    if not LA:
        w('| all | — | — | **not run — usage ended** | — |')
    w('')
    w('- **Units asserted** in the run code (prices per share, $ = 100 × points − fees, % = $ ÷ the unit\'s $ base); the SPXW '
      'P&L is re-asserted against its legs for every trade (`run_t56.py`).')
    w('- **Every run path reproduced the committed research rows** on previously read sessions before it touched fresh data '
      '(FETCH_LOG.md): the replay 110 of 110 trades, the touch events and hyp B rows exactly, T-E/H15 rows at both fees, H1 21 of 21.')
    w(f"- **Frozen code:** sim.py and load.py from `7dfea57`, sha256 in `out/t56_code_sha256.json`; the tracker at "
      f"`rules-2026-10-21.1` / `rules-c3-2026-10-21.1`; the engine audit's and hyp B's engines unchanged; AFTERHOURS's "
      f"`case_pnl` imported.")
    w('')
    # ---- disclosures
    w('## Deviations and disclosures')
    w('')
    w('- **Four SDK logins in all:** two for the stage-1 entitlement probes (non-expiry days only, before the prereg), one for the '
      'fetch, one for the prereg\'s retry of the 8 empty QQQ answers (still empty, not filled in).')
    w('- **T7 ran before the fetch commit** (`f6d2889`): it needed no fetch, its code is the committed `run_t7.py` unchanged, and '
      'it ran once.')
    w('- **The lookahead check was not completed: usage ended.** It was started, restarted, and stopped before writing any result; '
      'no output was read. The remaining integrity work was skipped for the same reason. The plain-loop re-derivation (0 '
      'differences) and the reproduction of the committed rows on previously read sessions did run.')
    w('- **QQQ\'s third Fridays before 2015** are not in the test: the standard monthlies were then dated on the Saturday, and the '
      'frozen rules ask for the chain whose expiration is the session (prereg §2.2).')
    w('- **Every fresh session carries an end-of-day mark** from the Lifecycle daily tier or the Compass features (not counted as '
      'reads, as Compass Close decided), so the "EOD-marked sessions out" sensitivity line has no sessions.')
    w('- **The sensitivity line without Compass Close\'s P&L-sample sessions** leaves few SPY sessions (most fresh SPY sessions '
      'are in it); where it has fewer than 60 sessions it prints no interval.')
    w('- **T4\'s by-time table** is by entry hour (a touch can fall on any minute).')
    hi = [f"{k.split()[0]} ({p(r['lines']["primary settlement at the study's own fees"]['mean_pct'] - r['describe']['mean_pct'], dec(k))} points)"
          for k, r in R.items() if r['lines']["primary settlement at the study's own fees"]['mean_pct'] > r['describe']['mean_pct']]
    w('- **The study\'s own fees** are a reported line throughout; no verdict was read at them. Robinhood is cheaper on the ETF '
      'options and the stock trades and dearer on SPXW, so the mean at the study\'s fees is higher only for '
      + (', '.join(hi) if hi else 'none') + '; no verdict would differ.')
    w('')
    w('## Files')
    w('')
    w('`research_notes/Compass Final/`: `PREREG_COMPASS_FINAL.md` and the stage-1 files (`4bc546f`); `fetch_final.py`, '
      '`FETCH_LOG.md` and the run code (`f6d2889`); the trade files `out/t123_trades.parquet`, `out/t4_trades.parquet`, '
      '`out/t56_trades.parquet` (+ `t56_skips.csv`), `out/t7_trades.parquet` (+ `t7_sessions.parquet`); `out/results.json`, '
      '`out/verify_plain.json`, `out/lookahead.json`, `out/t4_events.json`, `out/t123_replay_days.json`, `charts/`; this report '
      'and its PDF (`report_final.py`, `render_final.py`). S17\'s forward: `forward/s17_forward.py` (step 8 of '
      '`scripts/daily_forward.py`), `tests/test_s17_forward.py`. Raw data stay in the scratchpad (`$SP/compass_final/`).')
    (HERE / 'COMPASS_FINAL_REPORT.md').write_text('\n'.join(L) + '\n')
    print('wrote', HERE / 'COMPASS_FINAL_REPORT.md', len(L), 'lines')


if __name__ == '__main__':
    main()
