"""
write_report.py — FEATURES_REPORT.md from out/screen_expl.json, out/gex_check.json, out/holdout.json, out/verify_*.json, the
build counts and out/deviations.json. Formatting only: no number is computed here that the run scripts did not write
(the per-cell percentages are the scripts' fractions × 100).

  python3 -I write_report.py
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402

OUT = C.OUT


def pct(x, nd=2):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return '—'
    return f'{x * 100:+.{nd}f}'


def ci(t, nd=2):
    if not t or any(v is None or (isinstance(v, float) and not math.isfinite(v)) for v in t):
        return '—'
    return f'[{t[0] * 100:+.{nd}f}, {t[1] * 100:+.{nd}f}]'


def num(x, fmt='{:,.0f}'):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return '—'
    return fmt.format(x)


def load(p):
    return json.loads(p.read_text()) if p.exists() else None


def counts_table(split):
    rows = []
    for kind in ('0dte', 'eod'):
        for p in sorted((C.WORK / split / kind).glob('*.counts.json')):
            j = json.loads(p.read_text())
            rows.append((kind, j['name'], j.get('trades', 0), j.get('counts', {}), len(j.get('itm_zero', []))))
    return rows


def feature_row(f, h):
    p = f.get('pooled') or {}
    span = f.get('span') or {}
    if f.get('status'):
        expl = f['status']
    else:
        expl = f"{pct(p.get('delta'))} {ci(p.get('ci'))}"
    hold = '—'
    verdict = 'not sent'
    if f.get('status', '').startswith('dropped'):
        verdict = 'dropped by the GEX check'
    elif f.get('status', '').startswith('not tested'):
        verdict = 'not tested — no data'
    elif f.get('pass'):
        if h and f['id'] in h:
            hp = h[f['id']].get('pooled') or {}
            hold = f"{pct(hp.get('delta'))} {ci(hp.get('ci'))} (n_eff {num(hp.get('n_eff_block20'))})"
            verdict = '**PASS**' if h[f['id']].get('pass') else '**FAIL**'
        else:
            verdict = 'sent to the holdout (not yet read)'
    else:
        verdict = 'FAIL (screen)'
    return (f"| {f['id']} | {f['family']} | {span.get('first', '—')} → {span.get('last', '—')} | {num(span.get('sessions'))} | "
            f"{num(p.get('trades_with'))} / {num(p.get('trades_without'))} | {expl} | {num(p.get('n_eff_block20'))} | {hold} | {verdict} |")


def sub_rows(res: dict, label: str) -> list[str]:
    out = []
    for k, v in (res or {}).items():
        out.append(f"| {label} {k} | {num(v.get('trades_with'))} / {num(v.get('trades_without'))} | {pct(v.get('mean_with'))} | "
                   f"{pct(v.get('mean_without'))} | {pct(v.get('delta'))} | {ci(v.get('ci'))} |")
    return out


def main():
    scr = load(OUT / 'screen_expl.json')
    gx = load(OUT / 'gex_check.json')
    ho = load(OUT / 'holdout.json')
    dev = load(OUT / 'deviations.json') or {}
    H = {f['id']: f for f in ho['features']} if ho else None
    sha = hashlib.sha256(C.PREREG.read_bytes()).hexdigest()
    R = []
    p = R.append
    p('# Compass features: the pre-registered study, run as written\n')
    p(f'**Pre-registration: `PREREG_FEATURES.md`, commit `{C.PREREG_COMMIT}`, sha256 `{sha}`** (committed alone before any result '
      'was computed). Code: `run/` in this folder (`fcommon.py` the shared definitions; `daily.py`, `build_0dte.py`, `build_eod.py`, '
      '`tiers.py`, `uw_features.py` the inputs and base trades; `gex_check.py`; `screen.py` the comparisons; `x2.py`; '
      '`verify_features.py` the plain-loop re-derivation; this file by `write_report.py`). Files read only; no vendor call by the '
      'study. Returns are per trade after fees, as a share of the debit (prereg 2.6), shown in percentage points; Δ = mean with − '
      'mean without; intervals are the 20-session moving-block bootstrap (audit_lib, 2,000 draws, seed 20261022), percentile 95%, '
      'none under 60 sessions.\n')
    feats = scr['features']
    screened = len(feats)
    tested = [f for f in feats if not f.get('status')]
    passed = [f for f in feats if f.get('pass')]
    hpass = [k for k, v in (H or {}).items() if v.get('pass')]
    p('## Summary\n')
    g = gx['pooled'] if gx else {}
    p(f"- **The GEX check (section 7): Δ_GEX = {num(g.get('delta'), '{:+.4f}')} implied moves "
      f"{('[' + ', '.join(num(x, '{:+.4f}') for x in g.get('ci', [])) + ']') if g.get('ci') else '—'} on "
      f"{num(gx['name_sessions'] if gx else None)} name-sessions → the GEX features are "
      f"{'TESTED' if gx and gx['gate'] else 'DROPPED UNTESTED (SD1, SD2, X2)'}.**")
    p(f'- **Screened: {screened}** (the conservative count of section 6, the GEX features included whether tested or not); '
      f'computed on the exploration set: {len(tested)}; **passed the exploration screen: {len(passed)}** '
      f"({', '.join(f['id'] for f in passed) or 'none'}); **passed the holdout: {len(hpass)}** ({', '.join(hpass) or 'none'}).")
    if H:
        for k, v in H.items():
            hp = v['pooled']
            p(f"- {k} on the holdout: Δ {pct(hp.get('delta'))} {ci(hp.get('ci'))}, {num(hp.get('trades_with'))} / "
              f"{num(hp.get('trades_without'))} trades, {num(hp.get('sessions'))} sessions → **{'PASS' if v.get('pass') else 'FAIL'}**.")
    if H:
        p('- What the passes mean: each one makes a losing base set lose less; none makes it profitable. On the holdout, mean per '
          'trade with → without: ' + '; '.join(f"{k} {pct(v['pooled'].get('mean_with'))} → {pct(v['pooled'].get('mean_without'))}"
                                                for k, v in H.items()) + '. The three that pass are costs and timing (skip wide '
          'spreads, take the cheaper venue, sell a same-day long option at 14:00 instead of holding it to 15:58 or settlement); no '
          'direction, strike-placement or expiry-choice feature passed the screen, and the GEX family did not pass its gate.')
    h1 = load(OUT / 'holdout_run1_duplicated_rows.json')
    if h1:
        p('- **Disclosure: the holdout was read twice.** The first read ran on a table in which a join had duplicated base trades '
          '(777,571 rows for 580,274 trades; section 6); after the fix (no feature, threshold or rule changed) it was run once more '
          'and that second read carries the verdicts above. The first read, for the record: '
          + '; '.join(f"{f['id']} Δ {pct(f['pooled'].get('delta'))} {ci(f['pooled'].get('ci'))} → {'pass' if f.get('pass') else 'fail'}"
                      for f in h1['features']) + '. VN1 failed on the duplicated table and passes on the corrected one; weigh it accordingly.')
    p(f"- Expected false passes at the screen under the null: {screened} × 0.025 = {screened * 0.025:.2f}; both stages ≈ "
      f"{screened * 0.025 ** 2:.3f} (section 6).")
    p('')
    # ---- base set
    p('## 1. The base set (descriptive; no verdict)\n')
    b = scr['base']
    p(f"Exploration sessions {b['sessions']['first']} → {b['sessions']['last']} ({num(b['sessions']['n'])} in the span, held-out months out). "
      'Mean return per trade after fees with its block-20 interval:\n')
    p('| slice | sessions traded | trades | mean per trade | 20-session block 95% |')
    p('|---|---|---|---|---|')
    for k, v in b.items():
        if k == 'sessions':
            continue
        p(f"| {k} | {num(v.get('sessions_traded'))} | {num(v.get('trades'))} | {pct(v.get('mean_trade'))} | {ci(v.get('ci_trade_b20'))} |")
    p('\nTrades formed and not formed, by name (exploration split):\n')
    p('| kind | name | formed | not formed (reason: count) | sold at $0 in the money |')
    p('|---|---|---|---|---|')
    for kind, nm, n, cnt, itm in counts_table('expl'):
        p(f"| {kind} | {nm} | {num(n)} | {'; '.join(f'{k}: {v:,}' for k, v in sorted(cnt.items())) or '—'} | {itm} |")
    p('')
    # ---- GEX check
    p('## 2. The GEX check (prereg section 7)\n')
    if gx:
        p(f"Name-sessions: {gx['name_sessions']:,} (negative GEX {gx['negative']:,}, positive {gx['positive']:,}); left out: "
          + ('; '.join(f'{k} {v}' for k, v in sorted(gx['skipped'].items())) or 'none') + '. Realized move = |official close − P| ÷ IM.\n')
        p('| rows | name-sessions neg / pos | mean neg | mean pos | Δ_GEX | 20-session block 95% | sessions | n_eff (block) | n_eff (acf) |')
        p('|---|---|---|---|---|---|---|---|---|')

        def gl(lbl, v):
            c = v.get('ci') or []
            return (f"| {lbl} | {num(v.get('trades_with'))} / {num(v.get('trades_without'))} | {num(v.get('mean_with'), '{:.4f}')} | "
                    f"{num(v.get('mean_without'), '{:.4f}')} | {num(v.get('delta'), '{:+.4f}')} | "
                    f"{('[' + ', '.join(num(x, '{:+.4f}') for x in c) + ']') if c else '—'} | {num(v.get('sessions'))} | "
                    f"{num(v.get('n_eff_block20'))} | {num(v.get('n_eff_acf'))} |")
        p(gl('**pooled (the gate)**', gx['pooled']))
        for k, v in gx['by_name'].items():
            p(gl(f'name {k}', v))
        for k, v in gx['by_tier'].items():
            p(gl(f'tier {k}', v))
        p(f"\n**Gate: {'PASSED — SD1, SD2 and X2 are tested' if gx['gate'] else 'FAILED — SD1, SD2 and X2 are dropped untested (prereg section 7)'}.** "
          'The per-name and per-tier rows do not change the gate.\n')
    # ---- features
    p('## 3. The features, in the prereg\'s order\n')
    p('| id | family | span | sessions | trades with / without | exploration Δ [95%] | n_eff (block) | holdout Δ [95%] | verdict |')
    p('|---|---|---|---|---|---|---|---|---|')
    for f in feats:
        p(feature_row(f, H))
    p('\nPer feature: the decision, the source, the arms, and the rows per tier, settlement type and expiry bucket (descriptive).\n')
    for f in feats:
        p(f"### {f['id']} — {f['decision']}\n")
        p(f"Family: {f['family']}. Source: {f['source']}.")
        if f.get('status'):
            p(f"**{f['status']}.**\n")
            continue
        s = f['span']
        pp = f['pooled']
        p(f"Span {s['first']} → {s['last']}, {s['sessions']:,} sessions; names {', '.join(s['names'])}; buckets {', '.join(s['buckets'])}. "
          f"With: {pp['trades_with']:,} trades on {pp['sessions_with']:,} sessions, mean {pct(pp.get('mean_with'))}; without: "
          f"{pp['trades_without']:,} trades on {pp['sessions_without']:,} sessions, mean {pct(pp.get('mean_without'))}. "
          f"**Δ {pct(pp.get('delta'))} {ci(pp.get('ci'))}**, n_eff {num(pp.get('n_eff_block20'))} (block ratio) / "
          f"{num(pp.get('n_eff_acf'))} (acf). Screen: **{'PASS → holdout' if f.get('pass') else 'FAIL'}**.")
        if H and f['id'] in H:
            hh = H[f['id']]
            hp = hh['pooled']
            p(f"\nHoldout (once): {hp['trades_with']:,} / {hp['trades_without']:,} trades, {hp['sessions']:,} sessions "
              f"({hp['first']} → {hp['last']}), Δ {pct(hp.get('delta'))} {ci(hp.get('ci'))}, n_eff {num(hp.get('n_eff_block20'))} / "
              f"{num(hp.get('n_eff_acf'))} → **{'PASS' if hh.get('pass') else 'FAIL'}**.")
            for k, v in hh.get('parts', {}).items():
                p(f"- holdout part, {k} (descriptive): Δ {pct(v.get('delta'))} {ci(v.get('ci'))}, {v['trades_with']:,} / {v['trades_without']:,} trades.")
        p('\n| slice | trades with / without | mean with | mean without | Δ | 95% |')
        p('|---|---|---|---|---|---|')
        R.extend(sub_rows(f.get('by_tier'), 'tier'))
        R.extend(sub_rows(f.get('by_settle'), 'settlement'))
        R.extend(sub_rows(f.get('by_bucket'), 'bucket'))
        if H and f['id'] in H:
            R.extend(sub_rows(H[f['id']].get('by_tier'), 'holdout tier'))
            R.extend(sub_rows(H[f['id']].get('by_settle'), 'holdout settlement'))
        p('')
    # ---- counts
    p('## 4. Counts\n')
    p(f"- Screened: {screened}. Dropped by the GEX check: {sum(1 for f in feats if f.get('status', '').startswith('dropped'))}. "
      f"Not tested for want of data: {sum(1 for f in feats if f.get('status', '').startswith('not tested'))}. Computed on the exploration "
      f"set: {len(tested)}. Passed the screen: {len(passed)}. Passed the holdout: {len(hpass)}.")
    p('')
    # ---- verification
    p('## 5. Verification\n')
    for sp in ('expl', 'hold'):
        v = load(OUT / f'verify_{sp}.json')
        if v:
            p(f"- `verify_features.py {sp}` (plain loops, imports nothing of this study or audit_lib): {v['base_trades']} base trades and "
              f"{v['feature_decisions']} feature values and decisions re-derived from the raw files; **{v['differences']} differences**.")
    p('')
    # ---- deviations
    p('## 6. Deviations, known departures and readings of the prereg\n')
    for sec in ('deviations', 'departures', 'readings'):
        if dev.get(sec):
            p({'deviations': '**Deviations (forced by the data or made after a number was read)**',
               'departures': '**Known departures the prereg lists (section 8)**',
               'readings': '**Readings of the prereg where its text left a choice (made before any result was read)**'}[sec] + '\n')
            for x in dev[sec]:
                p(f'- {x}')
            p('')
    (C.FOLDER / 'FEATURES_REPORT.md').write_text('\n'.join(R) + '\n')
    print('written', len(R), 'lines')


if __name__ == '__main__':
    main()
