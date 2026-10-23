#!/usr/bin/env python3
"""
write_report.py — writes H3_REPORT.md from out/ (PREREG_H3.md §9). Reads only the outputs of build_h3.py, verify_h3.py and the
fetch's request log; computes nothing new.

    PYTHONDONTWRITEBYTECODE=1 python3 -I -B write_report.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h3common as H  # noqa: E402


def f(x, fmt='{:+,.2f}'):
    return '—' if x is None else fmt.format(x)


def ci(t, fmt='{:+,.2f}'):
    return '—' if not t else f'[{fmt.format(t[0])}, {fmt.format(t[1])}]'


def req_summary(split):
    n = secs = byt = 0
    st = {}
    p = H.STORE / '_requests.ndjson'
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if r.get('split', 'expl') != split:
                continue
            n += 1
            secs += r['secs']
            byt += r.get('bytes', 0)
            st[r['status']] = st.get(r['status'], 0) + 1
    return n, secs, byt, st


def main():
    sha = hashlib.sha256(H.PREREG.read_bytes()).hexdigest()
    S = json.loads((H.OUT / 'screen_expl.json').read_text())
    V = json.loads((H.OUT / 'verify_expl.json').read_text())
    T = json.loads((H.OUT / 'test_hold.json').read_text()) if (H.OUT / 'test_hold.json').exists() else None
    VH = json.loads((H.OUT / 'verify_hold.json').read_text()) if (H.OUT / 'verify_hold.json').exists() else None
    extra = (H.OUT / 'notes.md').read_text() if (H.OUT / 'notes.md').exists() else ''
    m, d = S['pnl'], S['describe']
    w = []
    w.append('# H3 — earnings implied-volatility crush, a short iron condor across the report: the run\n')
    w.append(f'**Pre-registration: `PREREG_H3.md`, commit `{H.PREREG_COMMIT}`, sha256 `{sha}`** (committed alone and pushed '
             'before anything was computed). Code in this folder: `h3common.py`, `fetch_h3.py`, `build_h3.py`, `verify_h3.py`, `attribution_h3.py` (exploratory, after the screen), '
             '`write_report.py`; outputs in `out/`.\n')
    w.append('## Summary\n')
    verdict = 'PASS' if S['screen_pass'] else 'FAIL'
    w.append(f'- **Exploration screen (1,601 X names, events with P and R in 2019-04-01 → 2022-12-30): mean {f(m.get("mean"))} $ a '
             f'condor after costs, block-20 95 % {ci(m.get("ci95_b20"))}**, {m["trades"]:,} trades exiting on {m["sessions_traded"]:,} of '
             f'{m["sessions"]:,} sessions → **{verdict}**.')
    q = S['pct_risk']
    w.append(f'- As % of max risk: mean {f(100 * q["mean"], "{:+.2f}")} % [{100 * q["ci95_b20"][0]:+.2f}, {100 * q["ci95_b20"][1]:+.2f}]; '
             f'win rate {100 * d["win_rate"]:.1f} %; median {f(d["median"])} $; worst {f(d["worst"])} $; p1 {f(d["p1"])} $, '
             f'p5 {f(d["p5"])} $; mean credit ${d["mean_credit"]:,.2f}, mean max risk ${d["mean_max_risk"]:,.2f}.')
    if T is None:
        w.append('- **Holdout: not fetched and not read** (the screen did not pass). The 1,600 H names stay unopened for '
                 '2019-01 → 2022-12.')
    else:
        tm = T['pnl']
        w.append(f'- **Holdout (1,600 H names, read once): mean {f(tm.get("mean"))} $ {ci(tm.get("ci95_b20"))}**, {tm["trades"]:,} '
                 f'trades → **{"PASS" if T["holdout_pass"] else "FAIL"}**; Bonferroni m = 2 {ci(tm.get("ci_bonf_m2"))} '
                 f'(EDGE: {T["edge_bonferroni_m2"]}), m = 7 {ci(tm.get("ci_bonf_m7"))} (EDGE: {T["edge_bonferroni_m7"]}).')
    w.append(f'- Verifier: {V["checked"]} exploration trades re-derived from the raw files by a plain loop, {V["fields"]:,} fields, '
             f'**{V["differences"]} differences**.' + (f' Holdout: {VH["checked"]} trades, {VH["differences"]} differences.' if VH else ''))
    w.append('- Ledger: H3 is the 2nd hypothesis tested in `LEDGER.md` (5 earlier programme failures before it). '
             + ('No pass, so no Bonferroni question arises.' if T is None or not T['holdout_pass'] else
                'Bonferroni status above.'))
    w.append('')
    w.append('## 1. The fetch\n')
    for split, B in (('expl', S['budget']), ('hold', T['budget'] if T else None)):
        if B is None:
            w.append(f'- {split}: not fetched.')
            continue
        n, secs, byt, st = req_summary(split)
        w.append(f'- {split}: {n:,} requests ({", ".join(f"{k} {v:,}" for k, v in sorted(st.items()))}), fetch time {secs / 3600:.2f} h, '
                 f'{byt / 1e6:.1f} MB stored, {sum(json.loads(x).get('rows', 0) for x in (H.STORE / '_requests.ndjson').read_text().splitlines() if json.loads(x).get('split', 'expl') == split):,} rows; stop: {B.get("stop") or "none — every event and tier walked"}.')
    w.append('')
    for name, R in (('exploration', S), ('holdout', T)):
        if R is None:
            continue
        w.append(f'## 2{"a" if name == "exploration" else "b"}. Events at each stage ({name})\n')
        w.append('| stage | events |\n|---|---|')
        for k, v in sorted(R['stages'].items(), key=lambda kv: -kv[1]):
            w.append(f'| {k} | {v:,} |')
        w.append('')
        w.append('Formed trades by how the exit was valued: ' + ', '.join(f'{k} {v:,}' for k, v in R['build'].items()) +
                 f'; exit file with no rows {R["describe"]["exit_file_empty"]:,}; fallback legs {R["describe"]["fallback_legs"]:,} '
                 f'on {R["describe"]["fallback_trades"]:,} trades; iron-fly-shaped {R["describe"]["fly_shaped"]:,}.\n')
    w.append('## 3. The exploration screen\n')
    ss = m.get('session_stats', {})
    w.append(f'- Mean $ a condor {f(m.get("mean"))}; block-20 95 % {ci(m.get("ci95_b20"))}; block 1 {ci(ss.get("ci_trade_b1"))}, '
             f'block 5 {ci(ss.get("ci_trade_b5"))}; effective N (block) {ss.get("n_eff_block20", float("nan")):,.0f}, (acf) '
             f'{ss.get("n_eff_acf", float("nan")):,.0f} of {m["sessions"]:,} sessions.')
    w.append(f'- Bonferroni-level intervals of the same draws (descriptive here): m = 2 {ci(m.get("ci_bonf_m2"))}, m = 7 {ci(m.get("ci_bonf_m7"))}.')
    w.append(f'- Context (descriptive): median credit {d["median_credit_im"]:.3f} IM; median exit cost {d["median_exit_im"]:.3f} IM; '
             f'median realized move |close(R)/close(P) − 1| {d["median_move_im"]:.3f} IM; moves beyond the short strikes (> 0.5 IM) '
             f'{100 * d["share_move_beyond_short"]:.1f} %.\n')
    w.append('| cut | trades | mean $ | block-20 95 % | mean % of max risk | win rate |\n|---|---|---|---|---|---|')
    for k, c in S['cuts'].items():
        w.append(f'| {k} | {c["trades"]:,} | {f(c["mean"])} | {ci(c["ci95_b20"])} | '
                 f'{"—" if c["pct_risk_mean"] is None else f"{100 * c["pct_risk_mean"]:+.2f} %"} | {100 * c["win_rate"]:.1f} % |')
    w.append('')
    if T is not None:
        w.append('## 4. The holdout test\n')
        tm, td = T['pnl'], T['describe']
        w.append(f'- Mean {f(tm.get("mean"))} {ci(tm.get("ci95_b20"))}; % of max risk {100 * T["pct_risk"]["mean"]:+.2f} %; '
                 f'win rate {100 * td["win_rate"]:.1f} %; worst {f(td["worst"])}; p1 {f(td["p1"])}; p5 {f(td["p5"])}.\n')
        w.append('| cut | trades | mean $ | block-20 95 % | mean % of max risk | win rate |\n|---|---|---|---|---|---|')
        for k, c in T['cuts'].items():
            w.append(f'| {k} | {c["trades"]:,} | {f(c["mean"])} | {ci(c["ci95_b20"])} | '
                     f'{"—" if c["pct_risk_mean"] is None else f"{100 * c["pct_risk_mean"]:+.2f} %"} | {100 * c["win_rate"]:.1f} % |')
        w.append('')
    w.append(extra)
    w.append('## Commands\n')
    w.append('```\nPYTHONDONTWRITEBYTECODE=1 python3 -I -B fetch_h3.py expl     # through $SPN/h3/run_fetch.sh (restarts after the '
             'ThetaData quiet windows)\nPYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=4 python3 -I -B build_h3.py expl\n'
             'PYTHONDONTWRITEBYTECODE=1 python3 -I -B verify_h3.py expl 50\n# only after a screen pass: fetch_h3.py hold; '
             'build_h3.py hold; verify_h3.py hold 50\nPYTHONDONTWRITEBYTECODE=1 python3 -I -B write_report.py\n```\n')
    (H.HERE / 'H3_REPORT.md').write_text('\n'.join(w))
    print('written')


if __name__ == '__main__':
    main()
