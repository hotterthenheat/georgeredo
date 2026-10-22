"""
write_reports.py — AUDIT.md and cumulative_through_<date>.md from run_audit.py's state (called by run_audit.main).
Every figure printed here is computed in run_audit.py / audit_lib.py; nothing is typed in by hand but the prose.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from pathlib import Path

import numpy as np

import audit_lib as A

f, ci = A.f, A.ci
STRUCT_NAME = {('condor_em1', 'condor'): 'condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30)',
               ('condor_d20', 'condor'): 'condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00)',
               ('fly5', 'iron'): 'fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30)', ('fly5', 'call'): 'fly5 long call ±5',
               ('fly5', 'put'): 'fly5 long put ±5'}


def pc(x, d=1):
    return '—' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{100 * x:.{d}f}%'


def money(x, d=0):
    return '—' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{x:+,.{d}f}'


def tab(head, rows):
    return ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]


def period_label(key, p):
    for c, lab, a, b in A.PERIODS[key]:
        if c == p:
            return c, lab, a, b
    return p, '', '', ''


def ret_rows(state, periods_wanted):
    rows = []
    for r in state['risk']:
        if r['period'] not in periods_wanted:
            continue
        v = r['pnl_nbbo']
        if not v.get('trades'):
            rows.append([STRUCT_NAME[(r['key'], r['structure'])], r['period'], f"{r['from']} → {r['to']}", 0, v.get('sessions', 0)] + ['—'] * 11)
            continue
        rows.append([STRUCT_NAME[(r['key'], r['structure'])], r['period'], f"{r['from']} → {r['to']}", v['trades'], f"{v['sessions_traded']} / {v['sessions']}",
                     f(v['mean_trade']), pc(v['mean_pct'], 2), f"${v['mean_risk']:.0f}", f(v['mean_session']), ci(v.get('ci_session_b1')),
                     ci(v.get('ci_session_b5')), ci(v.get('ci_session_b20')), ci(v.get('ci_trade_b20')),
                     ' '.join((f'{x:+.2f}' if math.isfinite(x) else '—') for x in v['acf']), f"{v['n_eff_acf']:.0f} / {v['n_eff_block20']:.0f}" if math.isfinite(v.get('n_eff_block20', float('nan'))) else f"{v['n_eff_acf']:.0f} / —",
                     money(v['total'])])
    return tab(['candidate · structure', 'period', 'sessions', 'trades', 'sessions traded / run', 'mean $ a trade', 'mean % of max risk', 'mean max risk',
                'mean $ a session', 'session CI (iid sessions)', 'block-5 CI', 'block-20 CI', 'mean $ a trade, block-20 CI', 'session P&L acf lag 1..5',
                'effective N (acf / block-20)', 'total $'], rows)


def risk_rows(state, periods_wanted):
    rows = []
    for r in state['risk']:
        if r['period'] not in periods_wanted:
            continue
        v = r['pnl_nbbo']
        if not v.get('trades'):
            continue
        ws = v['worst_session']
        rows.append([STRUCT_NAME[(r['key'], r['structure'])], r['period'], f(v['mean_trade']), pc(v['mean_pct'], 2), pc(v['win']),
                     f(v['pf'], '{:.2f}'), f"{v['dd']:,.0f}", f"{ws[0]} ({money(ws[1])})", v['streak'], pc(v['full_loss']), money(v['p1']), money(v['p5'])])
    return tab(['candidate · structure', 'period', 'mean $ a trade', 'mean % of max risk', 'win (trades)', 'profit factor', 'max drawdown $ (one lot, sessions)',
                'worst session', 'longest losing streak (sessions)', 'full-loss share (≤ −95 % of max risk)', 'p1 session $', 'p5 session $'], rows)


def cost_rows(state, periods_wanted):
    rows = []
    for r in state['risk']:
        if r['period'] not in periods_wanted:
            continue
        v = r['pnl_nbbo']
        if not v.get('trades'):
            continue
        g = lambda c: r[c].get('mean_trade', float('nan'))  # noqa: E731
        be = v['mean_trade'] / A.CONTRACTS
        rows.append([STRUCT_NAME[(r['key'], r['structure'])], r['period'], f(g('pnl_nbbo')), f(g('pnl_1c')), f(g('pnl_2c')), f(g('pnl_mid')),
                     f"{r['width_mean']:.2f} / {r['width_median']:.2f}", f"{r['slip_mean']:.2f}", '+1.00',
                     f"{be:+.2f}¢" if math.isfinite(be) else '—', f(g('pnl_1558')), f(g('pnl_1558_1c')), f(g('pnl_1558_2c')), f(g('pnl_1558_mid')),
                     ci(r['pnl_1c'].get('ci_session_b20')), ci(r['pnl_2c'].get('ci_session_b20'))])
    return tab(['candidate · structure', 'period', 'NBBO legs (as modeled)', '+$0.01 a contract at the open', '+$0.02 a contract at the open', 'every leg at its mid',
                'package NBBO width $ (mean / median)', 'NBBO→mid slip $', 'each $0.01 of package improvement', 'break-even: worse fill a contract',
                '15:58 exit, NBBO', '15:58 exit, +$0.01 open and close', '15:58 exit, +$0.02 open and close', '15:58 exit at mids',
                '+1c: session-mean block-20 CI', '+2c: session-mean block-20 CI'], rows)


def lift_rows(state, settle='official', periods=('i-a', 'i-b', 'ii')):
    rows = []
    for r in state['lifts']:
        if r['period'] not in periods or r['settle'].split()[0] != settle.split()[0] or not r.get('d1_trades'):
            continue
        rows.append([r['period'], r['events'], r['sessions'], f"{r['d1_trades']} / {r['d1_sessions']}", f(r['d1_mean']), f(r['all_mean']), f(r['rest_mean']),
                     f(r['time_usd']), ci(r.get('time_usd_ci_b1')), ci(r.get('time_usd_ci_b20')), pc(r['time_pct'], 2), ci(tuple(100 * x for x in r['time_pct_ci_b20'])),
                     f(r['sess_usd']), r['sessions_both'], ci(r.get('sess_usd_ci_b1')), ci(r.get('sess_usd_ci_b20'))])
    return tab(['period', 'sessions kept', 'n', 'D1 trades / sessions', 'D1 mean $', 'all trades mean $ (same minutes)', 'D2–D10 mean $', 'time-matched lift $',
                'iid-session CI', 'block-20 CI', 'lift % of risk', 'block-20 CI (pp)', 'session-matched lift $', 'sessions with D1 and non-D1', 'iid-session CI', 'block-20 CI'], rows)


def write_all(state):
    out = Path(state.get('report_dir') or A.HERE)
    (Path(state.get('out_dir') or A.OUT) / 'state.json').write_text(json.dumps({k: v for k, v in state.items() if k not in ('H', 'F', 'sdf')}, indent=1, default=str), encoding='utf-8')
    audit(state, out / 'AUDIT.md')
    cumulative(state, out / f"cumulative_through_{state['through']}.md")


# ---- AUDIT.md -----------------------------------------------------------------------------------------------------------------------------

def audit(s, path: Path):
    I, D, E = s['integ'], s['det'], s['ent']
    L = []
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    L += [f'# Audit of the paper tracker\'s historical replay, 2022-11-11 → 2026-10-09', '',
          f'Written {now} by `run_audit.py` in this folder ({s["seconds"]:.0f} s). It reads the replay\'s rows (`{rel(s["root"])}`, '
          f'`source = backtest-parquet`), the stored minute Parquet (`PAPER_PARQUET_ROOT`), Theta\'s EOD daily bars '
          '(`data_lake/thetadata/stock_eod`), UW\'s daily bars (`data_lake/unusualwhales/ohlc__1d.part0*.parquet`, the `r` rows) and '
          '`data/macro_events_2022_2027.json`. Nothing is fetched and the replay\'s code and rows are not touched. The corrected '
          f'cumulative report is `cumulative_through_{s["through"]}.md`; the tables behind both are in `out/`.', '']
    # ---- summary
    rec = {(r['key'], r['structure']): r for r in s['rec_h']}
    L += ['## Summary', '']
    L += [f'- **Deterministic, no double counting.** A fresh replay into an empty root reproduced the committed report CSV byte for byte '
          f'(SHA-256 `{D["csv"]["sha_a"][:16]}…`) and all {D["files_same"]} of {D["files_a"]} row files with identical sorted contents. '
          f'{I["replayed_sessions"]} sessions replayed = the {I["expected_full_sessions"]} full NYSE sessions expected; no key twice; every tradable '
          f'capture has exactly one settle row. 100 trades re-derived from the raw chain by separate code: {E["diffs"]["any"]} differences.' if D and E else '- (determinism or entry check not run)',
          f'- **The settlement was the 15:59 bar, not the official close.** Re-settled on the official close (Theta EOD; equal to UW\'s daily close on '
          f'every one of the {s["ss_h"]["SPY"]["both_theta_uw"] + s["ss_h"]["QQQ"]["both_theta_uw"]} name-sessions where both exist), '
          f'{sum(r["changed"] for r in s["rec_h"])} of {sum(r["trades"] for r in s["rec_h"])} trades change; condor_em1 totals '
          f'{money(rec[("condor_em1", "condor")]["total_1559"])} → {money(rec[("condor_em1", "condor")]["total_official"])}, condor_d20 '
          f'{money(rec[("condor_d20", "condor")]["total_1559"])} → {money(rec[("condor_d20", "condor")]["total_official"])}, fly5 iron '
          f'{money(rec[("fly5", "iron")]["total_1559"])} → {money(rec[("fly5", "iron")]["total_official"])}. The largest gap is SPY on 2025-04-09: '
          f'official 548.62 against a 15:59 bar of 543.37.',
          '- **Per period, on the official close** (mean $ a trade, 20-session block-bootstrap interval): ' + per_period_line(s) + '.',
          '- **The report\'s intervals** are percentile bootstraps over iid SESSIONS (2,000 draws, seed 20261016, the trade-weighted mean); they '
          'keep a session\'s trades together but assume no dependence between sessions, pool every period, and treat fly5\'s three structures (one '
          'trade seen three ways) as three results. Re-derived here to the last digit, then replaced by session-sum and moving-block intervals per period.',
          '- **No untouched forward period exists on the stored data for any candidate.** Every historical session lies in a period the candidate '
          'was developed or chosen on (section 5). The forward period starts 2026-10-12 and is empty until the fetch.',
          '- **D1 is a session filter, not a minute filter, and its pooled lift mixes in-sample rows.** The replay\'s +$9.06 pools the model\'s own '
          'training sessions (scored in-sample). Out of the model\'s training (2025+) the time-matched lift is positive and clear of zero under a '
          '20-session block bootstrap, but the same-session comparison (D1 minutes against the same day\'s other minutes) is inside the noise and '
          'the lift falls by about 30 % without scheduled-event sessions — and the candidate was set after that span was read (section 6).',
          '- **Hold-to-expiration is not operationally clean.** A condor finishes with a short leg in the money on about a quarter of trades and an '
          'ETF fly on essentially every trade, leaving 100 shares (≈ $44–64K a lot) per fly against $370–410 of modeled risk; the 15:58 close-out that '
          'avoids it turns every candidate\'s mean negative under the tracker\'s exit rule, and closing only the legs near the money gives back most '
          'or all of the hold\'s mean (section 8).', '']
    # ---- 1
    L += ['## 1. Reproducibility and integrity', '']
    if D:
        L += ['**The re-run.** The command (four shared cores, the other agent\'s fetch work running beside it):', '', '```',
              'PAPER_PARQUET_ROOT=<the stored Parquet> POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 nice -n 10 \\',
              '  python3 -I scripts/paper_tracker.py --backtest --start 2022-11-11 --end 2026-10-09 \\',
              '  --candidates condor_em1,fly5,condor_d20 --backtest-data <a fresh empty dir> --out <dir>', '```', '',
              f'It took {D.get("wall_seconds", 0):.0f} s from a cold root (no marker, no bar or VIX cache). The scripts as they were when it started '
              '(the other agent edits the fetch code; Python had loaded these before any edit):', '']
        L += [f'- `{x}`' for x in D.get('script_sha256_at_run', []) if x]
        L += ['']
        L += tab(['check', 'result'], [
            ['report CSV, byte for byte (committed vs re-run)', f"{'identical' if D['csv']['identical'] else 'DIFFERENT'} — {D['csv']['bytes'][0]} bytes, SHA-256 `{D['csv']['sha_a']}`"],
            ['row files (candidate/name/day)', f"{D['files_a']} committed, {D['files_b']} re-run, {D['n_only_a']} / {D['n_only_b']} only on one side"],
            ['row files with identical sorted contents (every column)', f"{D['files_same']} of {D['files_a']}; {D['files_differ']} differ"]])
        L += ['', 'Why it is deterministic: the replay reads files only; the clock is set to each event\'s minute, so every timestamp column '
              '(`captured_at`, `_fetched_at`, `settled_at`) is the replayed minute, not the wall clock; there is no random draw in the replay; '
              'the bootstrap draws in the report are seeded (numpy `default_rng(20261016)`). The committed root was written by several runs (its '
              '`_replay/days_*.json`: 2022-11-11 → 2024-10-31, 2024-11-01 → 2026-10-09, 2025-01-02 → 2026-10-09, 2026-10-05 → 09 and the whole '
              'span, each skipping minutes already marked) — and still equals the one cold run, so the markers neither dropped nor repeated a minute.', '']
    st = I['status_counts']
    L += ['**Sessions.**', '']
    L += tab(['count', 'value'], [
        ['weekdays 2022-11-11 → 2026-10-09', I['weekdays']],
        ['NYSE holidays on weekdays (the calendar written out in audit_lib.py)', len(I['calendar_holidays_in_range'])],
        ['NYSE half days (skipped, as the research skipped them)', len(I['calendar_half_days_in_range'])],
        ['full sessions expected', I['expected_full_sessions']],
        ['Theta EOD sessions for SPY in the span / less the half days', f"{I.get('theta_eod_sessions')} / {I.get('theta_eod_full_sessions')} (calendar mismatches: {I.get('theta_eod_vs_calendar')})"],
        ['replayed (the replay\'s `_replay/days_*.json`)', st.get('replayed')],
        ['skipped as holiday / half day by the replay', f"{st.get('holiday')} / {st.get('half day')} — the same dates as the calendar"],
        ['expected but not replayed / replayed but not expected', f"{len(I['expected_not_replayed'])} / {len(I['replayed_not_expected'])}"],
        ['days with a candidate\'s file missing', len(I['days_with_missing_files'])]])
    L += ['', 'Excluded days, every one, with the reason: holidays ' + ', '.join(d for d, v in I['excluded'].items() if v.startswith('holiday')) +
          '; half days ' + ', '.join(d for d, v in I['excluded'].items() if v.startswith('half')) + '.', '']
    per = I['per_candidate']
    L += ['**Rows and trades.**', '']
    L += tab(['check', 'result'], [
        ['rows read (capture, close1558, settle)', f"{I['rows']} in {I['files']} files: " + ', '.join(f'{k} {v}' for k, v in sorted(I['rows_by_kind'].items()))],
        ['a key twice (candidate, name, day, minute, structure, row kind, settle source)', I['duplicate_keys']],
        ['captures / tradable', f"{I['captures']} / {I['captures_tradable']}"],
        ['tradable captures by number of settle rows', I['tradable_captures_settle_count']],
        ['captures with no settle row (all untradable, no legs to settle)', f"{I['captures_with_settle_count'].get('0', I['captures_with_settle_count'].get(0, 0))} (legless captures {I['captures_without_legs']}, of them tradable {I['captures_without_legs_tradable']})"],
        ['settle rows without a capture', I['settle_without_capture']],
        ['settle sources', I['settle_sources']],
        ['fly5 tradable captures by number of 15:58 rows', I['fly5_tradable_with_1558_count']],
        ['15:58 rows with a value / without (a leg unquoted at 15:58)', f"{I['close1558_with_value']} / {sum(I['close1558_reasons'].values())}"],
        ['macro stamps on the rows against the events file', f"{I['macro_stamp_disagreements']} disagreements"]] +
        [[f'{k}: sessions with captures, name-sessions short of minutes, settled trades, sessions with a settled trade',
          f"{v['sessions_with_captures']}, {v['name_sessions_short_of_minutes']}, {v['settled_trades']}, {v['sessions_with_settled_trade']}"] for k, v in per.items()])
    odd = sum(r.get('odd_strikes', 0) for r in s['expi'])
    L += ['', f'One data note found on the way: {odd} fly5 trades (22 a structure, QQQ, 14 sessions from 2023-12-27 to 2024-09-30) use strikes '
          'ending in .78 (390.78 … 489.78) — adjusted series after a distribution, which the stored chain lists under the plain QQQ root, so the '
          '"strike nearest spot" rule can pick one. Their deliverable is not verified here; live, UW writes an adjusted series under its own OCC '
          'root (QQQ1 …), which the tracker\'s `Chain` (root filter off for SPY and QQQ) would also accept. Kept in every figure; their mean is negative.', '']
    # ---- 2
    ss = s['ss_h']
    L += ['## 2. Settlement and entry reconciliation', '',
          'The replay settles SPY and QQQ on **the 15:59 bar\'s close** (`ParquetSource.last_regular_close`, labelled `close_official_from = replay: '
          'the 15:59 bar close`) — the research\'s convention. The options settle (and are auto-exercised) on **the official closing price**, the '
          'primary listing market\'s closing auction, which the live tracker reads from UW\'s daily bar. Here the official close is Theta\'s EOD '
          'daily bar (its 17:15 report), checked against UW\'s daily bar (`r` row) where both exist (2025-10-13 →).', '']
    L += tab(['', 'SPY', 'QQQ'], [
        ['sessions with a trade', ss['SPY']['sessions'], ss['QQQ']['sessions']],
        ['official close found (source)', f"{ss['SPY']['official']} ({ss['SPY']['src']})", f"{ss['QQQ']['official']} ({ss['QQQ']['src']})"],
        ['Theta EOD vs UW daily close: sessions with both / disagreeing by > $0.005', f"{ss['SPY']['both_theta_uw']} / {ss['SPY']['theta_uw_disagree']}", f"{ss['QQQ']['both_theta_uw']} / {ss['QQQ']['theta_uw_disagree']}"],
        ['official = 15:59 bar (within $0.005)', ss['SPY']['equal'], ss['QQQ']['equal']],
        ['|official − 15:59|: mean / median / p95 / max', f"{ss['SPY']['mean_abs']:.3f} / {ss['SPY']['median_abs']:.3f} / {ss['SPY']['p95_abs']:.3f} / {ss['SPY']['max_abs']:.2f} ({ss['SPY']['max_day']})",
         f"{ss['QQQ']['mean_abs']:.3f} / {ss['QQQ']['median_abs']:.3f} / {ss['QQQ']['p95_abs']:.3f} / {ss['QQQ']['max_abs']:.2f} ({ss['QQQ']['max_day']})"],
        ['sessions with |official − 15:59| > $0.05 / > $0.25', f"{ss['SPY']['over_5c']} / {ss['SPY']['over_25c']}", f"{ss['QQQ']['over_5c']} / {ss['QQQ']['over_25c']}"],
        ['sessions where the two straddle a traded leg\'s strike', ss['SPY']['sessions_crossing'], ss['QQQ']['sessions_crossing']]])
    L += ['', 'SPY on 2025-04-09: the 15:59 bar closed at 543.37 and the official close was 548.62 (+$5.25); SPX\'s prints stood at 5455 from 15:58 to '
          '16:00, so the jump was SPY\'s closing cross, not the market. Every session\'s two closes and the crossing flag are in '
          '`out/settlement_sessions.csv`.', '']
    rows = []
    for r in s['rec_h']:
        rows.append([STRUCT_NAME[(r['key'], r['structure'])], r['trades'], f"{r['changed']} ({r['better']} better, {r['worse']} worse)", f(r['mean_change_changed']),
                     f(r['max_abs_change']), f"{r['cross_trades']} / {r['itm_changes']}", money(r['total_1559']), money(r['total_official']),
                     f"{r['mean_1559']:+.2f} → {r['mean_official']:+.2f}", r['payoff_check_fail']])
    L += tab(['candidate · structure', 'trades', 'trades whose P&L changes', 'mean change of those $', 'largest |change| $', 'trades with a strike between the two closes / a leg\'s ITM state changed',
              'total, 15:59 bar', 'total, official close', 'mean $ a trade', 'replay payoff ≠ re-derived payoff at 15:59'], rows)
    L += ['', 'fly5\'s three structures share their strikes\' settlement, so their changed counts match; the change is the same intrinsic difference '
          'for every cost assumption (it moves the NBBO, mid, +1c and +2c P&L by the same dollars).', '']
    if E:
        L += [f'**Entry legs, re-derived.** `check_entries.py` drew {E["n"]} tradable trades (seed {E["seed"]}; {E["by_candidate"]}) and rebuilt each from '
              'the raw files with its own plain loops — no import of the tracker: spot = the close of the last bar stamped before the minute; the chain = '
              'the rows stamped at the minute; the strike rule written again (the 20-delta rule with its own Black-Scholes bisection); every leg\'s '
              'bid and ask; the OCC expiry = the session; the package price at the NBBO and at the mids; the max risk. Differences: ' +
              ', '.join(f'{k} {v}' for k, v in E['diffs'].items()) + '.', '']
    if s['exp_chk']:
        L += ['**The chain files\' expiry.** The stored chain files carry no expiry column (a file holds "the same-day contracts" by how it was '
              'fetched). Theta\'s flat end-of-day file lists every contract with its expiration for 2026-10-06 → 09; the contracts expiring that day '
              'are exactly the chain file\'s contracts on all ' + str(len(s['exp_chk'])) + ' name-days (' +
              '; '.join(f"{x['day']} {x['name']} {x['in_both']}/{x['chain_file_contracts']}" for x in s['exp_chk']) + '). Earlier dates have no '
              'such file on disk; the OCC symbols the replay writes carry the session as expiry by construction.', '']
    # ---- 3
    L += ['## 3. Execution: each leg at its NBBO, not a package fill', '',
          '**What is modeled.** At entry every leg trades alone at its own NBBO — a short at its bid, a long at its ask (`Leg.fill`); the package '
          'price is the sum. That is the WORST price at which the package could trade if every leg had to cross separately, and a real '
          'complex order does not trade that way: it rests or crosses as one package on the complex order book, at a net price in $0.01 steps for '
          'SPY and QQQ ($0.05 steps for SPX and SPXW packages — to be confirmed against Cboe\'s current rule before an SPXW run), and can fill inside the summed NBBO or not at all. The '
          'stored quotes carry no complex-order book and no fills, so neither the fill rate nor the price a package would have got can be '
          'measured from them; the table brackets it between the legs\' NBBO (as modeled), worse fills, and the mids.', '',
          '**When each cost applies (from `paper_tracker.py`).** Open: $0.65 a contract on every contract — four for every structure here (a '
          'condor 1+1+1+1, an iron fly 1+1+1+1, a call or put fly 1+2+1), $2.60 a structure (`LEGS × FEE`). Held to expiry: no fee; every leg at '
          'intrinsic on the settlement price. The $0.01 / $0.02 stresses (`pnl_1c`, `pnl_2c`) move EVERY CONTRACT at the open only — $4 / $8 a '
          'structure — and do not touch the settlement. The 15:58 exit (`close_row`): a long sold at its bid, a short bought back at its ask, $0.65 '
          'a contract closed; a long with no bid is left to expire with no fee; the replay applies no stress to the exit — the "+$0.01 open and '
          'close" columns here add it to every contract closed as well. Not modeled anywhere: exercise and assignment fees, the commission on the '
          'resulting stock trade, regulatory and clearing fees (ORF, OCC, SEC / FINRA TAF on sales), borrow on a short stock position, and margin '
          'interest. The mid column prices every leg at its mid with the same fees.', '']
    L += cost_rows(s, ('i', 'i-a', 'i-b', 'ii'))
    L += ['', 'A package filled $0.01 better than the summed NBBO adds $1.00 a structure (one cent × 100); the break-even column is how much worse '
          'than the NBBO every contract could fill (at the open, hold to expiry) before the period\'s mean is zero. The mid column is the most a '
          'package could get resting at the middle of every leg; whether it fills there is not in the data.', '']
    # ---- 4
    cc = s['ci_check']
    L += ['## 4. Inference', '', '**The method in the current report** (`paper_backtest.session_boot`, read in the code and re-derived here): a percentile '
          'bootstrap that resamples SESSIONS — the sessions holding at least one trade of the cell — with replacement, independently, 2,000 draws, '
          'numpy `default_rng(20261016)` (the same seed for every cell, so every interval uses the same index draws); the statistic is the '
          'trade-weighted mean of the drawn sessions\' trades (Σ P&L ÷ Σ trades); the interval is the 2.5th and 97.5th percentiles. The D1 lift '
          '(`lift_d1`) uses the same draws as session weights on Hypothesis E\'s time-matched formula; the 15:58 comparison bootstraps the paired '
          'difference the same way. Re-derived from the rows by `report_ci` in run_audit.py:', '']
    L += tab(['cell', 'report CSV', 'this audit'], [[f"{c['key']} {c['structure']}", ci(c['report']), ci(c['ours'])] for c in cc])
    L += ['', 'What it does right: a session\'s trades (its five minutes; fly5\'s two names and two minutes) stay together, so the trade-level '
          'independence a naive interval would assume is not assumed. What it does not do: (a) sessions are independent draws — no serial '
          'dependence between neighbouring sessions (volatility clusters); (b) one interval over every period, the in-sample and selection spans '
          'pooled; (c) fly5\'s iron, call and put flies are one trade seen three ways (same strikes, same settlement; their session P&Ls '
          'correlate as below) and are printed as three results; condor_em1 and condor_d20 share 13:00 and 13:30 on the same sessions; '
          '(d) the per-trade mean weighs a session by how many of its minutes were tradable.', '']
    for pname, cm in s['corr'].items():
        L += [f'Session P&L correlation, {pname} (official close, NBBO):', '']
        L += tab([''] + cm['labels'], [[lab] + [f'{x:+.2f}' for x in row] for lab, row in zip(cm['labels'], cm['corr'])])
        L += ['']
    L += ['**Session-level inference, by period** (official close, NBBO legs, fees in). A session\'s P&L is the sum of the candidate-structure\'s '
          'trades that day (zero on a session it ran and took no trade); the mean session P&L gets percentile intervals from the iid session '
          'bootstrap and from a moving-block bootstrap over sessions in calendar order (blocks of 5 and 20 sessions, 2,000 draws, seeded); the '
          'per-trade mean (Σ ÷ Σ) the block-20 interval. Effective N: n ÷ (1 + 2 Σ_{k≤5} (1 − k/n) ρ_k) from the session autocorrelations, and '
          'n × Var_iid ÷ Var_block-20 of the session mean. No interval here treats trades as independent.', '']
    L += ret_rows(s, ('i', 'i-a', 'i-b', 'ii', 'iii'))
    big = [f"{STRUCT_NAME[(r['key'], r['structure'])].split(' (')[0]} {r['period']} (max |ρ| {max(abs(x) for x in r['pnl_nbbo']['acf']):.2f})"
           for r in s['risk'] if r['pnl_nbbo'].get('trades') and max(abs(x) for x in r['pnl_nbbo']['acf']) > 0.10]
    L += ['', 'The session autocorrelations at lags 1–5 are within ±0.10 on every series' + (' except ' + ', '.join(big) if big else '') +
          ', and the block-5 and block-20 intervals are close to the iid-session ones: dependence between neighbouring sessions adds little width '
          'here. What changes the reading is the official-close settlement (section 2) and the period split (sections 5–6).', '']
    # ---- 5
    L += ['## 5. Periods: training, selection, untouched forward', '', 'Defined from the research notes, never pooled into one headline:', '']
    prow = []
    for k in A.KEYS:
        for c, lab, a, b in A.PERIODS[k]:
            prow.append([k, c, f"{a} → {b or 'the last fetched session'}", lab])
    L += tab(['candidate', 'period', 'sessions', 'what the span was used for'], prow)
    L += ['', 'Sources: condor_em1 — `research_notes/Compass phase 2/hyp_b_boundary_theta.md` ("The pre-registered picks": the midday pick was the '
          'VIX-mid cell, its all-VIX parent fourth by the fit lower bound; "The rule, conditional on X" drops the VIX cut after "the VIX cut that '
          'made it the pick did not help OOS"). fly5 — `hyp_c_debit_flies.md` (pre-registered 15:00 iron ±2, call ±2, call ±5; "a neighbouring '
          'cell I did not pick (the IRON ±5 …) … identified after the OOS read") and `Compass phase 3/hyp_f_cash_butterfly.md` ("the primary cell '
          'was named … after C\'s OOS was printed"). condor_d20 — `hyp_e_short_premium_lift.md` and `scripts/models/t2_spy_full.manifest.json` '
          '(fit = sessions before 2024-07-01, 405 sessions, in-sample AUC 0.81 against 0.61 out of fold; cuts = the score quantiles of 2024-07 → '
          '2024-12; frozen 2026-10-21T21:32Z, after the OOS read at 21:01Z); its section 4: "NOT PRE-REGISTRABLE … The OOS lift is read for the '
          'record only".', '',
          '**There is no untouched forward period on the stored data for any candidate.** Every session from 2022-11-11 to 2026-10-09 was either '
          'the development span or the span the candidate was chosen on. The first untouched sessions are 2026-10-12 onward; they are not in '
          'the stored files and wait for the fetch (`paper_tracker.py --fetch-theta` on the owner\'s machine, then `--backtest` over them). '
          f"Forward sessions expected through {s['through']}: {s['fwd']['n_expected']}; fetched: {len(s['fwd']['fetched'])}.", '']
    # ---- 6
    ev = s['ev_counts']
    L += ['## 6. D1 selection bias', '', 'condor_d20 carries the frozen t2 model\'s decile on every capture (`t2_decile_primary`: the full model where '
          'all four VIX features are there — every replayed row). Two comparisons, both on the official-close P&L, NBBO legs:', '',
          '- **time-matched** (Hypothesis E §8, the replay report\'s formula): Σ_m N_D1(m)·[mean(D1 at m) − mean(all trades at m)] ÷ Σ N_D1, m the five '
          'minutes — D1 against the unconditional strategy at the same times of day, over all sessions;',
          '- **session-matched**: Σ_s N_D1(s)·[mean(D1 trades in s) − mean(the other trades in s)] ÷ Σ N_D1(s), over the sessions holding both — D1 '
          'against the same session\'s other minutes (it removes which DAYS D1 picks; the minutes differ in time of day).', '',
          'Intervals: iid-session and 20-session moving-block bootstraps of the paired statistic (2,000 draws). Scheduled-event sessions: any '
          'FOMC decision, FOMC minutes, CPI or NFP date in `data/macro_events_2022_2027.json` (sessions in i-a / i-b / ii: ' +
          ', '.join(f"{k} {v['sessions']} ({v['event_sessions']} with an event, {v['fomc_decision']} FOMC decisions)" for k, v in ev.items() if v['sessions']) + ').', '']
    L += lift_rows(s, 'official')
    L += ['', 'Reconciliation with the replay report (15:59-bar settlement, pooled 2022-11-11 → 2026-10-09 — not a headline): ' +
          '; '.join(f"time-matched lift {f(r['time_usd'])} (report +9.06), session-matched {f(r['sess_usd'])}" for r in s['lifts'] if r['period'] == 'hist-pooled' and r['settle'].startswith('15:59')) + '.', '']
    L += d1_words(s)
    # ---- 7
    L += ['## 7. Risk comparability', '', 'Official close, NBBO legs, fees in, one lot. Max risk: a credit structure width × 100 − the credit; a debit '
          'structure the debit (fees not in the denominator). Drawdown, worst session, streaks and tails are on the SESSION sums in calendar order. '
          'Not ranked; the rows are not comparable by mean dollars alone — a fly risks about twice a condor\'s dollars, and fly5\'s three rows are one '
          'trade.', '']
    L += risk_rows(s, ('i', 'i-a', 'i-b', 'ii'))
    L += ['', 'Cost sensitivity for the same rows is the section 3 table (+$0.01 / +$0.02 a contract, the mids, $1.00 a structure for each cent of '
          'package improvement, the break-even, and the 15:58 exit).', '']
    # ---- 8
    L += expiry_words(s)
    # ---- 9
    L += ['## 9. Files and commands', '', '```', 'cd "research_notes/Compass phase 3/backtest_audit"',
          '# everything (integrity, the 100-trade entry check, settlement, execution, inference, D1, risk, expiry) → AUDIT.md + cumulative_through_<D>.md',
          'PAPER_PARQUET_ROOT=<the stored Parquet> POLARS_MAX_THREADS=1 nice -n 10 python3 -I run_audit.py --through 2026-10-21',
          '# the determinism check against a fresh replay root (adds out/determinism.json; run_audit reads it)',
          'PAPER_PARQUET_ROOT=<…> POLARS_MAX_THREADS=1 nice -n 10 python3 -I ../../../scripts/paper_tracker.py --backtest --start 2022-11-11 \\',
          '   --end 2026-10-09 --candidates condor_em1,fly5,condor_d20 --backtest-data <fresh dir> --out <dir>',
          'POLARS_MAX_THREADS=1 nice -n 10 python3 -I run_audit.py --rerun-root <fresh dir> --rerun-csv <dir>/backtest_2022-11-11_2026-10-09.csv',
          '# the pieces alone', 'python3 -I check_integrity.py [--rerun-root DIR --csv A --rerun-csv B]', 'python3 -I check_entries.py --parquet-root <…>', '```', '',
          '`audit_lib.py` (loaders, calendar, periods, bootstraps), `check_integrity.py`, `check_entries.py`, `run_audit.py`, `write_reports.py`; '
          '`out/`: integrity.json, determinism.json, entries.json, settlement_sessions.csv, risk_by_period.csv, d1_lift.csv, '
          'expiration_mechanics.csv, quotes_1558_cache.parquet (the 15:58 quotes read once from the chain files), state.json. '
          'No secret is read or written; no vendor is called.', '']
    path.write_text('\n'.join(L) + '\n', encoding='utf-8')


def per_period_line(s):
    out = []
    for r in s['risk']:
        v = r['pnl_nbbo']
        if not v.get('trades') or r['period'] == 'iii':
            continue
        lo, hi = v.get('ci_trade_b20', (float('nan'), float('nan')))
        tag = 'clear of zero' if lo > 0 else ('below zero' if hi < 0 else 'through zero')
        out.append(f"{r['key']}{'' if r['key'] != 'fly5' else ' ' + r['structure']} ({r['period']}) {v['mean_trade']:+.2f} [{lo:+.2f}, {hi:+.2f}] {tag}")
    return '; '.join(out)


def d1_words(s):
    g = {(r['period'], r['events']): r for r in s['lifts'] if r['settle'] == 'official'}
    a = g.get(('ii', 'all sessions'), {})
    b = g.get(('ii', 'without any scheduled-event session (FOMC decision, FOMC minutes, CPI, NFP)'), {})
    e = g.get(('ii', 'scheduled-event sessions only'), {})
    ia = g.get(('i-a', 'all sessions'), {})
    ib = g.get(('i-b', 'all sessions'), {})
    if not a:
        return []
    return ['**What the 2025+ lift is.** The frozen model was trained on sessions before 2024-07-01 and its cuts set on 2024-07 → 2024-12, so on '
            f'2025-01-02 → 2026-10-09 every decile is an out-of-training score. There the time-matched lift is {f(a["time_usd"])} a condor '
            f'({pc(a["time_pct"], 2)} of max risk), block-20 interval {ci(a["time_usd_ci_b20"])}: D1 minutes beat the unconditional condor at '
            'the same times of day, and the interval stays clear of zero when neighbouring sessions are resampled together.', '',
            '**What it is not.** (1) Not an untouched test: the candidate, its minutes and its D1 rule were written after this span had been '
            'read (hyp_e §4 labels it "not pre-registrable"; the model was frozen 31 minutes after the OOS read). (2) Not a minute-timing '
            f'effect: against the same session\'s other minutes D1 adds {f(a["sess_usd"])} [{", ".join(f"{x:+.2f}" for x in a["sess_usd_ci_b20"])}] — '
            'most of the time-matched lift is WHICH SESSIONS hold a D1 minute (D1 sessions were good for every minute\'s condor). (3) Not robust '
            f'to the event days: without scheduled-event sessions the time-matched lift is {f(b.get("time_usd"))} {ci(b.get("time_usd_ci_b20"))}, '
            f'on the {e.get("sessions", 0)} event sessions alone {f(e.get("time_usd"))} {ci(e.get("time_usd_ci_b20"))} — {e.get("d1_trades", 0)} '
            f'of the {a.get("d1_trades", 0)} D1 trades sit on event sessions; the opposite of the fit period\'s story in hyp_e (there the FOMC '
            'decision days destroyed the lift). (4) Not a confirmation of the training span: on the model\'s own training sessions (i-a) the decile is in-sample, so '
            f'its {f(ia.get("time_usd"))} lift says only that the model fits its training data; on the cut half (i-b) {f(ib.get("time_usd"))} '
            f'{ci(ib.get("time_usd_ci_b1"))} is inside the noise. The replay report\'s pooled +$9.06 [+5.41, +12.81] averages these three spans.', '',
            '**Do not read the D1 mean or win rate as evidence of predictive alpha.** D1\'s own mean ($' + f'{a.get("d1_mean", float("nan")):.2f}' +
            ' in 2025+) is the unconditional harvest plus the session selection; the only evidence that bears on the model is the lift against the '
            'matched unconditional strategy, and the forward pre-registered re-test hyp_e asked for (≥ 150 new sessions) has not started.', '']


def expiry_words(s):
    L = ['## 8. Expiration mechanics', '',
         'SPY and QQQ options are American-style and physically settled: an option in the money by $0.01 or more at the official close is '
         'exercised automatically by OCC\'s exercise-by-exception unless its holder says otherwise, and a holder may exercise or abandon until the '
         'cut-off after the close (about 5:30 pm New York) on after-hours prices — so a short leg near the money can be assigned or not on '
         'information the writer does not have until the next morning. Assignment of a short call delivers 100 shares a contract, of a short put '
         'takes 100 in. Measured on every trade held to the close, at the official close:', '']
    rows = []
    for r in s['expi']:
        rows.append([STRUCT_NAME[(r['key'], r['structure'])], r['period'], r['trades'], pc(r['any_itm']), pc(r['short_itm']), pc(r['long_itm']),
                     f"{pc(r['net_stock'])} ({pc(r['net_long'])} long, {pc(r['net_short'])} short)", pc(r['offset_pair']),
                     f"${r['net_stock_value_mean']:,.0f} / ${r['net_stock_value_max']:,.0f}", f"${r['max_risk_mean']:.0f}",
                     f"{pc(r['pin01'])} / {pc(r['pin25'])} / {pc(r['pin50'])}", pc(r['itm_changes'])])
    L += tab(['candidate · structure', 'period', 'trades', 'any leg ITM', 'a short leg ITM (assignment)', 'a long leg ITM (exercise)',
              'a stock position left after expiry (net ≠ 0)', 'ITM legs that offset (both sides of a vertical)', 'stock left: mean / max $ value',
              'mean modeled max risk', 'close within $0.01 / $0.25 / $0.50 of a short strike', 'a leg\'s ITM state differs 15:59 vs official'], rows)
    ah = s['ah']
    if ah:
        L += ['', 'After the close (2025-10-13 → 2026-10-09 only, where UW\'s post-market bar is on disk): the share of trades whose post-market '
              'range (16:00–20:00, so an upper bound for the window to the exercise cut-off) took a short strike across the money — the trades '
              'where the assignment was undecided at 16:00: ' + '; '.join(f"{STRUCT_NAME[(x['key'], x['structure'])]} {pc(x['short_strike_in_after_hours_range'])} of {x['trades']}" for x in ah) + '.']
    rows = []
    for r in s['expi']:
        rows.append([STRUCT_NAME[(r['key'], r['structure'])], r['period'], f(r['hold_mean']), f"{f(r['exit_mean'])} ({r['exit_n']})", f(r['exit_mid_mean']),
                     f"${r['exit_fees_mean']:.2f}", f"{f(r['part0.5_mean'])} ({pc(r['part0.5_resid'])})", f"{f(r['part1.0_mean'])} ({pc(r['part1.0_resid'])})"])
    L += ['', '**The early close.** The 15:58 exit is the tracker\'s own rule (`close_row`; logged by the replay for fly5 and priced here for the '
          'condors off the raw chain at 15:58 with the same rule — on fly5 it reproduces the replay\'s 15:58 P&L on ' + f"{s['ex_n'] - s['ex_diff']} of {s['ex_n']}" +
          ' trades with a value). It leaves no position overnight. A middle road a margin account could take (not the tracker\'s rule, shown for '
          'scale): close at 15:58 only the legs in the money or within $0.50 / $1.00 of the 15:58 spot, let the rest expire on the official close; '
          'the share in brackets is the trades where a leg left open still finished in the money (an assignment left to happen).', '']
    L += tab(['candidate · structure', 'period', 'hold to the official close', '15:58 exit, NBBO (trades)', '15:58 exit, mids', 'fees a structure with the exit',
              'close only legs within $0.50 (left ITM)', 'close only legs within $1.00 (left ITM)'], rows)
    sp = s['spxw']
    L += ['', '**What the hold-to-expiration payoff assumes, by account.**', '',
          '- **Cash account.** The iron condors and the iron fly sell credit spreads, which brokers generally allow only in a margin account '
          'with spread approval (some allow them in a cash or retirement account against cash equal to the width); no cash account can carry '
          'the short stock an assigned short call leaves. The long call and put flies are '
          'debit structures a cash account can open, but held to the close they finish with 100 shares long or short on nearly every trade '
          '(the table: 98–99 %), worth $44–64K a lot against a $375–410 debit — a cash account cannot pay for the long stock or hold the short. '
          'So for a cash account the hold-to-expiration P&L is not achievable; the achievable number is an exit before the close, and under the '
          'tracker\'s 15:58 rule every fly5 structure\'s mean turns negative (above).',
          '- **Margin account with spread approval.** It can carry an assignment overnight, but then the position is no longer the defined-risk '
          'structure: one side assigned and the other not (the "stock left" column — about one condor in five, nearly every fly) is a 100-share '
          'position exposed to the overnight gap, with the margin it needs; and near a short strike (the pin columns) the writer does not know at '
          '16:00 whether he will be assigned. A positive defined-risk payoff at intrinsic does not remove this; the modeled P&L also charges no '
          'exercise, assignment or stock commission.',
          '- **With an early close.** Closing before the close removes the delivery problem and costs the exit\'s bid-ask, the last minutes\' '
          'time value and the fees; on the tracker\'s full 15:58 exit every candidate\'s mean turns negative in every period, and at the mids '
          'it is still negative. Closing only the legs within $0.50 or $1.00 of the money gives back most or all of the hold\'s mean as well '
          '(the condors land near zero, the flies stay negative) and still leaves a few trades with a leg in the money. **On this data the '
          'hold-to-expiration P&L is the only one that is positive, and it is the one a cash account cannot achieve and a margin account can '
          'achieve only by carrying assignment and overnight stock risk the P&L does not price.**', '',
          '**SPXW is a different instrument and these results do not transfer.** SPXW options are cash-settled, European-style (no early '
          'exercise, no delivery) and PM-settled on the official SPX closing value; their quotes, widths and fees differ (index option fees '
          'and the $0.05 complex-order step), and Hypothesis B found SPXW condors negative or flat at the NBBO. On disk: same-day SPXW chains, 1-minute '
          f"NBBO, {sp.get('spxw_chain_files')} session files {sp.get('spxw_first')} → {sp.get('spxw_last')}; SPX 1-minute prints {sp.get('spx_print_files')} files "
          f"{sp.get('spx_first')} → {sp.get('spx_last')} (the research\'s settlement proxy: the last print at or before 16:00); the official SPX closing value only in "
          f"Theta's flat index_eod for {', '.join(sp.get('index_eod_flat_days', []))}. The replay\'s fly_spxw candidate has been run only as a one-week sanity "
          'run (2026-10-05 → 09, outside the repository). An SPXW alternative needs its own backtest on actual SPXW contracts and quotes, SPXW '
          'fees, a stated package-fill rule in $0.05 steps, and the official SPX closing value for every session (not on disk before 2026-10-06).', '']
    return L


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(A.REPO))
    except Exception:
        return str(p)


# ---- the cumulative report --------------------------------------------------------------------------------------------------------------

def cumulative(s, path: Path):
    fw = s['fwd']
    now = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    L = [f"# Paper tracker candidates — corrected cumulative report through {s['through']}", '',
         f'Written {now} by `run_audit.py` (this folder). The method and every check behind these tables are in `AUDIT.md`. Corrections against '
         '`backtest_replay/backtest_2022-11-11_2026-10-09.md`: settled on the official close (not the 15:59 bar); session-sum statistics with '
         'session and moving-block bootstrap intervals (never trade-level); the periods apart — (i) development / training, (ii) the span the '
         'candidate was selected on, (iii) the untouched forward sessions from 2026-10-12. **The periods are never pooled into one figure.** '
         'NBBO legs, $0.65 a contract at the open, held to the official close, one lot.', '']
    L += ['## (i) Development / training — historical, not evidence for the candidate', '']
    L += ret_rows(s, ('i', 'i-a', 'i-b'))
    L += ['', 'condor_d20\'s i-a are the frozen model\'s own training sessions (its deciles in-sample); i-b the half-year its cuts were set on.', '']
    L += risk_rows(s, ('i', 'i-a', 'i-b'))
    L += ['']
    L += cost_rows(s, ('i', 'i-a', 'i-b'))
    L += ['', '## (ii) Selection read — historical, the span each candidate was chosen on (not an out-of-sample confirmation)', '']
    L += ret_rows(s, ('ii',))
    L += ['']
    L += risk_rows(s, ('ii',))
    L += ['']
    L += cost_rows(s, ('ii',))
    L += ['', 'condor_d20, D1 against the unconditional condor (official close), by period:', '']
    L += lift_rows(s, 'official')
    L += ['', '## (iii) Untouched forward — 2026-10-12 → ' + s['through'], '']
    per = fw['per']
    nf = len(fw['fetched'])
    if 0 < nf < fw['n_expected']:
        L += [f"**Partly fetched: {nf} of {fw['n_expected']} expected sessions.** The rest are listed as missing below and wait for the fetch; "
              'the tables cover the replayed forward sessions alone. A forward session whose official close is not on disk yet (Theta EOD and '
              'UW\'s daily bars end where their last download ended) is settled on the 15:59 bar and listed in the last column below; '
              'regenerate once the closes are on disk.', '']
    if nf == 0:
        L += ['**Pending the fetch.** None of these sessions is in the stored Parquet yet; they are fetched on the owner\'s machine '
              '(`paper_tracker.py --fetch-theta --start 2026-10-12 --end ' + s['through'] + ' --parquet-root R`), replayed (`--backtest` over the '
              'same days into the replay root), and this report is regenerated by the one command in `AUDIT.md` §9. Nothing below is pooled with (i) or (ii).', '']
    L += tab(['sessions', 'count', 'dates'], [
        ['expected (NYSE full sessions)', fw['n_expected'], ', '.join(fw['expected'])],
        ['fetched (SPY and QQQ chains and bars on disk)', nf, ', '.join(fw['fetched']) or '—'],
        ['missing (not fetched)', len(fw['missing']), ', '.join(fw['missing']) or '—'],
        ['fetched without a VIX file (no-VIX decile primary)', len(fw['vix_missing']), ', '.join(fw['vix_missing']) or '—'],
        ['replayed', sum(1 for v in fw['status'].values() if v == 'replayed'), ', '.join(d for d, v in sorted(fw['status'].items()) if v == 'replayed') or '—'],
        ['excluded by the replay (holiday, half day, missing files)', len(fw['excluded']), ', '.join(f'{d} {v}' for d, v in sorted(fw['excluded'].items())) or '—']])
    L += ['']
    L += tab(['candidate', 'complete sessions (every minute captured)', 'settled sessions', 'valid trades (tradable, settled)', 'invalid (untradable captures)',
              'unmatched (a capture without its settle, or the reverse)', 'sessions settled without an official close on disk'],
             [[k, len(v['complete']), len(v['settled_sessions']), v['valid'], v['invalid'], v['unmatched'], ', '.join(v['official_missing']) or '—'] for k, v in per.items()])
    L += ['']
    if any(v['valid'] for v in per.values()):
        L += ret_rows(s, ('iii',))
        L += ['']
        L += risk_rows(s, ('iii',))
        L += ['']
        L += cost_rows(s, ('iii',))
        L += ['', 'condor_d20 D1 in the forward period (the pre-registered re-test needs ≥ 150 sessions):', '']
        lr = lift_rows(s, 'official', ('iii',))
        L += lr if len(lr) > 2 else ['No D1 trade in the forward sessions yet.']
    else:
        L += ['Forward P&L, risk and D1 tables: pending the fetch (they will hold the same columns as (i) and (ii), for the forward sessions alone).', '']
    path.write_text('\n'.join(L) + '\n', encoding='utf-8')
