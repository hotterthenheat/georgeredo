"""write_report.py — SPXW_REPORT.md from out/build.json, out/results.json, out/verify_50.json and the trades (run_spxw.py report)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
NAMES = {'iron_fly': '(A) SPXW iron fly ±5×ratio (fly5 iron analogue), 15:00 + 15:30',
         'condor_d20': '(B) SPXW 20-delta iron condor, wings 2×ratio (condor_d20 analogue), 13:00–15:00'}
SHORT = {'iron_fly': '(A) iron fly', 'condor_d20': '(B) condor'}
PER = ('development', 'selection', 'forward')
VAR = (('legs', 'legs at NBBO'), ('pkg', 'package NBBO, $0.05 against us'), ('pkg5', 'package +$0.05'), ('pkg10', 'package +$0.10'),
       ('mid', 'mid (reference)'))


def f(x, fmt='{:+.2f}'):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return '—'
    return fmt.format(x)


def ci(t, fmt='{:+.2f}'):
    if not t or any(v is None or (isinstance(v, float) and not math.isfinite(v)) for v in t):
        return '—'
    return f'[{fmt.format(t[0])}, {fmt.format(t[1])}]'


def table(head, rows):
    out = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    out += ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]
    return '\n'.join(out)


def write(meta: dict, res: dict, tr: pl.DataFrame) -> None:
    ver = json.loads((OUT / 'verify_50.json').read_text()) if (OUT / 'verify_50.json').exists() else None
    prose = json.loads((HERE / 'prose.json').read_text()) if (HERE / 'prose.json').exists() else {}
    C, Vd, X = res['cells'], res['verdict'], res['extrinsic']
    per_dates = {'development': '2022-05-13 → 2024-12-31', 'selection': '2025-01-02 → 2026-10-09', 'forward': '2026-10-12 → 2026-10-21'}
    L = []
    L.append('# SPXW pre-registered test: the fly5 iron and condor_d20 analogues, and the late-day extrinsic against the realized move')
    L.append('')
    L.append(f"**Pre-registration: `PREREG_SPXW.md`, commit `{meta['prereg']}`** (pushed to `claude/lucid-heisenberg-bpyq7k` at "
             f"2026-10-22 02:22 UTC, before any SPXW structure was priced against an outcome). Every rule below is that file's; nothing "
             f"was changed after the run. Built {meta['built_utc']} by `run_spxw.py` in this folder ({meta['seconds']} s, three worker processes), "
             f"from the stored minute Parquet (`PAPER_PARQUET_ROOT`), Cboe's SPX history (`data/official_closes/cboe_SPX_History_2026-10-22.csv`) "
             f"and, for SPY and QQQ, the official closes AUDIT.md used (Theta EOD, else UW's daily bar). Nothing was fetched for the run; "
             f"the fee documents were read on 2026-10-22 (section 3).")
    L.append('')
    L.append('## Summary')
    L.append('')
    for an in ('iron_fly', 'condor_d20'):
        v = Vd[an]
        val = v['values']
        L.append(f"- **{NAMES[an]}: {v['verdict']}.** Selection mean session sum at the package fill {f(val['sel_mean'])} "
                 f"{ci(val['sel_ci_b20'])} (20-session block); at +$0.05 {f(val['sel_pkg5_mean'])}; development {f(val['dev_mean'])}. "
                 + '; '.join(f"{k} — {'yes' if ok else 'NO'}" for k, ok in v['conditions'].items()) + '.')
    for s in prose.get('summary', []):
        L.append(f'- {s}')
    L.append('')

    # 1. data
    L.append('## 1. Sessions, settlement and the code')
    L.append('')
    ex = meta['excluded']
    L.append(f"Full NYSE sessions 2022-05-13 → 2026-10-21 (audit_lib's calendar, half days out): {meta['expected_sessions']}; with an SPXW "
             f"chain, SPX prints, SPY bars and an official SPX close: **{meta['sessions']}**; left out: {len(ex)}"
             + (' — ' + ', '.join(f"{e['day']} ({', '.join(e['missing'])})" for e in ex) if ex else '') + '. '
             + (f"SPXW chain files on dates that are not full sessions (half days), not used: {', '.join(meta['chain_files_not_full_sessions'])}." if meta['chain_files_not_full_sessions'] else ''))
    L.append('')
    L.append('Sessions by period: ' + ', '.join(f"{p} {res['periods'][p]} ({per_dates[p]})" for p in PER) + '.')
    L.append('')
    ck = meta['spx_close_check']
    rows = [['Cboe SPX history, fetched 2026-10-22 (the primary)', f"{ck['cboe_new_rows']} rows, {ck['cboe_new_first']} → {ck['cboe_new_last']}", '', '', '']]
    for nm, lab in (('cboe_2026-10-14', 'Cboe SPX history, fetched 2026-10-14 (scratchpad/spx/cboe_spx.csv)'), ('fred_sp500', 'FRED SP500 (S&P DJI), scratchpad/spx/fred_sp500.csv')):
        c = ck.get(nm)
        if isinstance(c, dict):
            rows.append([lab, f"overlap {c['overlap']} days, {c['overlap_first']} → {c['overlap_last']}", c['overlap_in_range'],
                         f"{c['disagree_gt_0.005']} ({c['disagree_in_range']} in range)", f"{c['max_abs_diff_in_range']:.4f}"])
        else:
            rows.append([lab, str(c), '', '', ''])
    L.append(table(['source', 'span', 'overlap days in 2022-05-13 → 2026-10-21', 'disagreements > $0.005', 'largest |diff| in range'], rows))
    L.append('')
    for nm in ('cboe_2026-10-14', 'fred_sp500'):
        c = ck.get(nm)
        if isinstance(c, dict) and c['disagreements_in_range']:
            L.append(f"Disagreements with {nm} in range: " + ', '.join(f"{d['day']} {d['cboe_new']:.2f} vs {d[nm]:.2f}" for d in c['disagreements_in_range']) + '.')
            L.append('')
    for s in prose.get('settlement', []):
        L.append(s)
        L.append('')
    # official vs print
    trd = tr.filter(pl.col('tradable'))
    sd = trd.select('day', 'official', 'print16').unique().with_columns((pl.col('official') - pl.col('print16')).alias('d'))
    sd = sd.filter(pl.col('d').is_not_null())
    a = sd['d'].abs()
    w = sd.sort(pl.col('d').abs(), descending=True).head(1).to_dicts()[0]
    L.append(f"**Official close vs the last SPX print at or before 16:00** (the research's proxy), on the {sd.height} sessions with a trade: "
             f"equal within $0.005 on {int((a <= 0.005).sum())}; |difference| mean {a.mean():.2f}, median {a.median():.2f}, p95 {a.quantile(0.95):.2f}, "
             f"max {a.max():.2f} ({w['day']}: official {w['official']:.2f}, print {w['print16']:.2f}); over 1 point on {int((a > 1).sum())}, over 5 on {int((a > 5).sum())}.")
    L.append('')
    code = meta['code']
    L.append('**The code imported** (read, never written), with the SHA-256 of the working-tree file the run loaded and whether every '
             'function or class used is identical to the committed HEAD version (other agents edit `scripts/` concurrently):')
    L.append('')
    for rel, c in code.items():
        same = c.get('used_code_equal_to_HEAD', {})
        L.append(f"- `{rel}` `{c['sha256_working_tree']}` — HEAD `{c.get('head', '?')[:10]}`; used code equal to HEAD: "
                 f"{sum(same.values())} of {len(same)}" + ('' if all(same.values()) else f" (differs: {', '.join(k for k, v in same.items() if not v)})"))
    L.append('')

    # 2. structures
    L.append('## 2. The structures and the 50-structure check')
    L.append('')
    rows = []
    for an in ('iron_fly', 'condor_d20'):
        for p in PER:
            c = C[f'{an}|{p}']
            rs = sorted(c['reasons'].items(), key=lambda kv: -kv[1])[:4]
            rows.append([SHORT[an], p, c['rows'], c['tradable'], '; '.join(f'{k} ({v})' for k, v in rs) or '—',
                         ', '.join(f'{k}: {v}' for k, v in sorted(c.get('width_counts', {}).items(), key=lambda kv: -kv[1])),
                         f(c.get('ratio_med'), '{:.4f}'), f(c.get('credit_legs_mean'), '{:.2f}'), f(c.get('credit_pkg_mean'), '{:.2f}'),
                         f(abs(c['round_loss_mean']) if c.get('round_loss_mean') is not None else None, '{:.3f}'), f(c.get('fees_open_mean'), '${:.2f}')])
    L.append(table(['analogue', 'period', 'entries', 'tradable', 'untradable: the reasons (count of reason parts)', 'wing width (points): trades',
                    'median ratio', 'mean credit, legs', 'mean credit, package', 'mean lost to the $0.05 rounding', 'mean opening fees'], rows))
    L.append('')
    if ver:
        L.append(f"**Verification** (`verify_50.py`, separate plain-loop code reading the raw Parquet (polars as the file reader only) and the Cboe CSV with the csv "
                 f"module, its own Black-Scholes bisection; no import of the tracker, the replay, audit_lib or run_spxw): {ver['n']} entries "
                 f"(25 a structure, seed 20261022; {ver['tradable']} tradable) — spot, ratio, K0, wings, the 20-delta shorts, the tradable rule, "
                 f"the legs' credit, the package credit, the opening fees, the package P&L on the official close and the 15:58 package exit. "
                 f"Differences: " + ', '.join(f'{k} {v}' for k, v in ver['differences'].items()) + f"; entries with any difference: {ver['any']}.")
        L.append('')

    # 3. fees
    L.append('## 3. Fees, as fixed in the pre-registration')
    L.append('')
    L.append(table(['item', 'a contract', 'source (read 2026-10-22)'], [
        ['commission', '$0.65', "the owner's stated assumption"],
        ['Cboe customer transaction fee, SPX (incl SPXW), premium < $1.00 / ≥ $1.00', '$0.36 / $0.45',
         'Cboe Exchange Fees Schedule, October 1, 2026, Rate Table – Underlying Symbol List A, fee codes CS / CT (https://cdn.cboe.com/resources/membership/Cboe_FeeSchedule.pdf; '
         'the fee-code page https://www.cboe.com/us/options/membership/fee_schedule/cboe/, shown effective October 8, 2026)'],
        ['SPXW Execution Surcharge (electronic; customers included)', '$0.14', 'the same schedule; SEC Release 34-93955 ($0.13 → $0.14 from 2022-01-02)'],
        ['Index License Surcharge', '$0 for a customer', 'the same schedule ($0.10 for F J L M B N U, not C)'],
        ['Options Regulatory Fee', '$0.01248', 'the same schedule, Regulatory Fees, "per contract side"'],
        ['OCC clearing fee', '$0.025', 'OCC Schedule of Fees, SR-OCC-2025-002 / SEC Release 34-102437 (from 2025-02-14; $0.02 before); SR-OCC-2025-019 / 34-104274 (December 2025 holiday only)'],
        ['total', '$1.18748 (< $1.00) / $1.27748 (≥ $1.00)', 'on every contract at the open and at the 15:58 close; nothing at cash settlement'],
    ]))
    L.append('')
    L.append('A broker may add (exercise or settlement fees, its own pass-through of FINRA TAF and SEC Section 31 on sales) or absorb some of '
             'these (exchange, ORF and OCC fees are often bundled); the figures are a stated assumption, not a broker\'s bill. Complex orders '
             'carry no separate customer rate in the schedule; each leg pays per contract. The ETF reports charged $0.65 a contract only.')
    L.append('')

    # 4. session-level inference, primary fill
    L.append('## 4. Session-level inference by period (package NBBO rounded against us to $0.05, fees in, official close)')
    L.append('')
    L.append("A session's P&L is the sum of the analogue's trades that day (0 on a session in the universe with no tradable entry); the session "
             "mean's percentile intervals from the iid session bootstrap and the moving-block bootstrap over sessions in calendar order (blocks "
             "of 5 and 20, 2,000 draws, seed 20261022 — audit_lib.session_stats unchanged); the per-trade mean's block-20 interval; effective N "
             "from the session autocorrelations and from Var_iid ÷ Var_block-20. Periods are never pooled.")
    L.append('')
    rows = []
    for an in ('iron_fly', 'condor_d20'):
        for p in PER:
            c = C[f'{an}|{p}']
            s, r = c['pkg_off'], c['risk_pkg']
            rows.append([SHORT[an], p, per_dates[p], s.get('trades', 0), f"{s.get('sessions_traded', 0)} / {s.get('sessions', 0)}", f(s.get('mean_trade')),
                         f(r.get('mean_pct_risk'), '{:.2f}%'), f(r.get('mean_risk'), '${:.0f}'), f(s.get('mean_session')), ci(s.get('ci_session_b1')),
                         ci(s.get('ci_session_b5')), ci(s.get('ci_session_b20')), ci(s.get('ci_trade_b20')),
                         ' '.join(f'{x:+.2f}' for x in s.get('acf', [])) or '—',
                         f"{f(s.get('n_eff_acf'), '{:.0f}')} / {f(s.get('n_eff_block20'), '{:.0f}')}", f(r.get('total'), '{:+,.0f}')])
    L.append(table(['analogue', 'period', 'sessions', 'trades', 'sessions traded / run', 'mean $ a trade', 'mean % of max risk', 'mean max risk',
                    'mean $ a session', 'session CI (iid)', 'block-5 CI', 'block-20 CI', 'mean $ a trade, block-20 CI', 'session acf lag 1..5',
                    'effective N (acf / block-20)', 'total $'], rows))
    L.append('')

    # 5. fills and settlement
    L.append('## 5. Fills and settlement')
    L.append('')
    L.append('Mean $ a session (block-20 interval), held to the official close; the last column the same package fill settled on the last SPX print at or before 16:00 (labelled secondary).')
    L.append('')
    rows = []
    for an in ('iron_fly', 'condor_d20'):
        for p in PER:
            c = C[f'{an}|{p}']
            row = [SHORT[an], p]
            for v, _ in VAR:
                s = c[f'{v}_off']
                row.append(f"{f(s.get('mean_session'))} {ci(s.get('ci_session_b20'))}")
            s = c['pkg_p16']
            row.append(f"{f(s.get('mean_session'))} {ci(s.get('ci_session_b20'))}")
            sdf = c.get('settle_diff', {})
            row.append(f"{sdf.get('sessions_differing_gt_0.005', '—')} / {sdf.get('trades_pnl_changed', '—')}")
            rows.append(row)
    L.append(table(['analogue', 'period'] + [lab for _, lab in VAR] + ['package, ≤ 16:00 print (secondary)', 'sessions where the two closes differ / trades whose P&L changes'], rows))
    L.append('')
    L.append('Mean $ a trade by fill (official close): ' + '; '.join(
        f"{SHORT[an]} {p}: " + ', '.join(f"{v} {f(C[f'{an}|{p}'][f'risk_{v}'].get('mean_trade'))}" for v, _ in VAR)
        for an in ('iron_fly', 'condor_d20') for p in PER) + '.')
    L.append('')
    for s in prose.get('fills', []):
        L.append(s)
        L.append('')

    # 6. risk
    L.append('## 6. Risk (package NBBO, official close, one lot)')
    L.append('')
    L.append('Max risk: the wider wing × 100 − the package credit × 100 (fees not in the denominator). Drawdown, worst session, streak and the percentiles on the session sums in calendar order.')
    L.append('')
    rows = []
    for an in ('iron_fly', 'condor_d20'):
        for p in PER:
            r = C[f'{an}|{p}']['risk_pkg']
            if not r.get('trades'):
                rows.append([SHORT[an], p] + ['—'] * 10)
                continue
            rows.append([SHORT[an], p, f(r['mean_trade']), f(r['mean_pct_risk'], '{:.2f}%'), f(r['win'] * 100, '{:.1f}%'), f(r['pf'], '{:.2f}'),
                         f(r['dd'], '{:,.0f}'), f"{r['worst_day']} ({r['worst']:+,.0f})", r['streak'], f(r['full_loss'] * 100, '{:.1f}%'),
                         f(r['p1'], '{:+,.0f}'), f(r['p5'], '{:+,.0f}')])
    L.append(table(['analogue', 'period', 'mean $ a trade', 'mean % of max risk', 'win (trades)', 'profit factor', 'max drawdown $ (sessions)',
                    'worst session', 'longest losing streak (sessions)', 'full-loss share (≤ −95 % of max risk)', 'p1 session $', 'p5 session $'], rows))
    L.append('')

    # 7. 15:58
    L.append('## 7. The 15:58 exit, alongside')
    L.append('')
    L.append("Every trade closed at the rows stamped 15:58: legs — a short bought back at its ask, a long sold at its bid, a long with no bid left "
             "to expire (no fee, intrinsic on the official close); package — Σ short asks − Σ long bids rounded UP to $0.05, every leg closed, the "
             "+$0.05 / +$0.10 stress on BOTH the entry and the exit; mid — every leg at its mid both ways. Fees on every contract closed. A trade with "
             "a leg unquoted at 15:58 has no exit value (counted). Mean $ a session, block-20 interval.")
    L.append('')
    rows = []
    for an in ('iron_fly', 'condor_d20'):
        for p in PER:
            c = C[f'{an}|{p}']
            row = [SHORT[an], p, f(c['pkg_off'].get('mean_session'))]
            for v, _ in VAR:
                s = c[f'x_{v}']
                row.append(f"{f(s.get('mean_session'))} {ci(s.get('ci_session_b20'))}")
            row += [c.get('x_unavailable', '—'), c.get('x_abandoned_trades', '—'), f(c.get('fees_close_pkg_mean'), '${:.2f}')]
            rows.append(row)
    L.append(table(['analogue', 'period', 'hold, package (section 4)'] + [f'15:58 exit, {lab}' for _, lab in VAR] +
                   ['trades with no 15:58 value', 'trades with a long abandoned (legs)', 'mean closing fees (package)'], rows))
    L.append('')

    # 8. verdict
    L.append('## 8. The pass/fail rule, applied mechanically')
    L.append('')
    rows = []
    for an in ('iron_fly', 'condor_d20'):
        v = Vd[an]
        rows.append([NAMES[an]] + [('yes' if ok else '**no**') for ok in v['conditions'].values()] + [f"**{v['verdict']}**"])
    L.append(table(['analogue'] + list(Vd['iron_fly']['conditions'].keys()) + ['verdict'], rows))
    L.append('')
    L.append('The rule (PREREG_SPXW.md section 7): PASS only if, in the selection period, at the package-NBBO fill with the cited fees and the '
             'official-close settlement, the mean session sum is > 0 with its 20-session block-bootstrap 95 % interval excluding zero, AND the mean '
             'stays > 0 at +$0.05 package stress, AND the development-period mean is > 0. The forward period is reported, never used to pass. A PASS '
             'means "continue paper testing on SPXW", never production; a FAIL is not to be rescued by another width, minute, fill or filter read on '
             'these periods. The ETF results are not evidence for SPXW.')
    L.append('')
    for s in prose.get('verdict', []):
        L.append(s)
        L.append('')

    # 9. extrinsic
    L.append('## 9. ATM extrinsic against the realized move to settlement')
    L.append('')
    L.append("At 15:00, 15:30 and 15:58, every full session: K = the strike nearest spot with both sides quoted (the tracker's `Chain.nearest`); "
             "extrinsic = call mid + put mid − |spot − K|, in bps of spot; realized = |official close − spot| in bps of spot (SPY and QQQ: Theta EOD, "
             "else UW's daily bar, as AUDIT.md; SPX: Cboe). Spot: SPY and QQQ the close of the bar stamped m − 1, SPX the print stamped m. SPY and QQQ "
             "chains start 2022-11-11, so their development period is 2022-11-11 → 2024-12-31; the gaps use the sessions all three names share. "
             "Ratio = mean extrinsic ÷ mean realized; diff = mean (extrinsic − realized); intervals: 20-session moving-block bootstrap, 2,000 draws, "
             "the same draws for numerator and denominator (none under 60 sessions).")
    L.append('')
    miss = X.get('missing', [])
    if miss:
        L.append('Rows without a value: ' + ', '.join(f'{a} {b}: {c}' for a, b, c in miss) + '. Rows with no official close: '
                 + (', '.join(f'{a}: {b}' for a, b in X.get('no_close', [])) or 'none') + '. ATM strikes off the $0.50 grid (adjusted series): '
                 + (', '.join(f'{a}: {b}' for a, b in X.get('adjusted_strike_rows', [])) or 'none') + '.')
        L.append('')
    rows = []
    for p in PER:
        for m in ('15:00', '15:30', '15:58'):
            for nm in ('SPY', 'QQQ', 'SPXW'):
                c = X['cells'].get(f'{p}|{m}|{nm}')
                if not c:
                    continue
                rows.append([p, m, nm, c['n'], c['first'], f(c['ext'], '{:.2f}'), f(c['real'], '{:.2f}'), f(c['ratio'], '{:.3f}'),
                             ci(c.get('ratio_ci'), '{:.3f}'), f(c['diff'], '{:+.2f}'), ci(c.get('diff_ci')), f(c['ext_med'], '{:.2f}'),
                             f(c['real_med'], '{:.2f}'), f(c['atm_dist_bps'], '{:.2f}')])
    L.append(table(['period', 'minute', 'name', 'sessions', 'first', 'mean extrinsic bps', 'mean realized bps', 'ratio', 'ratio block-20 CI',
                    'mean ext − real bps', 'block-20 CI', 'median extrinsic bps', 'median realized bps', 'mean |K − spot| bps'], rows))
    L.append('')
    L.append('**The gaps, on the sessions all three share** (ETF − SPXW; a positive ratio gap = the ETF priced richer relative to its own realized move):')
    L.append('')
    rows = []
    for p in PER:
        for m in ('15:00', '15:30', '15:58'):
            g = X['gaps'].get(f'{p}|{m}')
            if not g:
                continue
            for etf in ('SPY', 'QQQ'):
                rows.append([p, m, etf, g['n'], f(g[f'{etf}_ratio'], '{:.3f}'), f(g['SPXW_ratio'], '{:.3f}'), f(g[f'{etf}_minus_SPXW_ratio'], '{:+.3f}'),
                             ci(g.get(f'{etf}_minus_SPXW_ratio_ci'), '{:+.3f}'), f(g[f'{etf}_minus_SPXW_diff'], '{:+.2f}'),
                             ci(g.get(f'{etf}_minus_SPXW_diff_ci')), f(g[f'{etf}_minus_SPXW_ext'], '{:+.2f}'), ci(g.get(f'{etf}_minus_SPXW_ext_ci')),
                             f(g[f'{etf}_minus_SPXW_real'], '{:+.2f}')])
    L.append(table(['period', 'minute', 'ETF', 'common sessions', 'ETF ratio', 'SPXW ratio', 'ratio gap', 'block-20 CI', 'gap in (ext − real) bps',
                    'block-20 CI', 'gap in extrinsic bps', 'block-20 CI', 'gap in realized bps'], rows))
    L.append('')
    for s in prose.get('extrinsic', []):
        L.append(s)
        L.append('')

    # 10. files
    L.append('## 10. Files and commands')
    L.append('')
    L.append('```')
    L.append('cd "research_notes/Compass phase 3/spxw_prereg"')
    L.append('export PAPER_PARQUET_ROOT=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
    L.append('# the structures, every fill, both settlements, the 15:58 exits and the extrinsic rows → out/trades.parquet, out/extrinsic_raw.parquet, out/build.json')
    L.append('POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 nice -n 10 python3 -I run_spxw.py build --workers 3')
    L.append('# 50 structures re-derived by separate code → out/verify_50.json')
    L.append('python3 -I verify_50.py')
    L.append('# the statistics, the verdicts and the extrinsic study → out/results.json, out/extrinsic.parquet, SPXW_REPORT.md')
    L.append('POLARS_MAX_THREADS=1 python3 -I run_spxw.py report')
    L.append('```')
    L.append('')
    L.append('`PREREG_SPXW.md` (the pre-registration, commit ' + meta['prereg'][:10] + '), `run_spxw.py` (build, statistics), `verify_50.py`, '
             '`write_report.py` (this file\'s tables), `prose.json` (the report\'s written paragraphs, added after the numbers were read); '
             '`out/`: trades.parquet (one row an entry: legs, quotes, every P&L), extrinsic_raw.parquet / extrinsic.parquet, build.json '
             '(sessions, exclusions, the SPX close cross-check, the code hashes), results.json, verify_50.json. `scripts/` and `tests/` were not '
             'edited. No vendor was called; no key or secret was read or written.')
    (HERE / 'SPXW_REPORT.md').write_text('\n'.join(L) + '\n')
