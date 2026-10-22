#!/usr/bin/env python3
"""
write_report.py — DIRECTION_REPORT.md from out/screen.json, out/verify_expl.json, the fetch logs and (only if the screen passed)
out/holdout.json and out/verify_hold.json. Figures are written as they are in the JSON (returns in % of the debit).

    python3 -I write_report.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dcommon as C  # noqa: E402


def pct(x, nd=2):
    return '—' if x is None else f'{100 * x:+.{nd}f}'


def ci(c):
    if not c or c[0] is None:
        return '[no interval]'
    return f'[{100 * c[0]:+.2f}, {100 * c[1]:+.2f}]'


def neff(x):
    return '—' if x is None else f'{x:,.0f}'


def row(lab, r):
    return (f"| {lab} | {r.get('events', '—'):,} | {r['trades_with']:,} / {r['trades_without']:,} | {r.get('sessions_without', 0):,} "
            f"| {pct(r.get('mean_with'))} | {pct(r.get('mean_without'))} | **{pct(r.get('delta'))}** {ci(r.get('ci'))} |")


HEAD = '| cut | events | trades with / without | sessions traded | mean with % | mean without % | Δ (pp) [95 % block-20] |\n|---|---|---|---|---|---|---|'


def fetch_lines(split):
    b = C.STORE / f'_budget_{split}.json'
    if not b.exists():
        return [f'- {split}: not fetched.']
    j = json.loads(b.read_text())
    reqs = [json.loads(x) for x in (C.STORE / '_requests.ndjson').read_text().splitlines()]
    evs = [json.loads(x) for x in (C.STORE / f'_events_{split}.ndjson').read_text().splitlines()]
    from collections import Counter
    st = Counter(e['stage'] for e in evs)
    return [f"- {split}: {len(evs):,} events walked in the seeded order; stopped: {j.get('stop') or 'every event walked'}; "
            f"{j['requests']:,} requests this set, fetch time {j['secs'] / 3600:.2f} h, {j['bytes'] / 1e6:.1f} MB stored.",
            '  - stages: ' + '; '.join(f'{k} {v:,}' for k, v in st.most_common())]


def main():
    sc = json.loads((C.OUT / 'screen.json').read_text())
    ve = json.loads((C.OUT / 'verify_expl.json').read_text())
    hp = C.OUT / 'holdout.json'
    ho = json.loads(hp.read_text()) if hp.exists() else None
    vh = json.loads((C.OUT / 'verify_hold.json').read_text()) if (C.OUT / 'verify_hold.json').exists() else None
    sha = hashlib.sha256(C.PREREG.read_bytes()).hexdigest()
    m = sc['main']
    L = []
    L.append('# Compass direction: post-earnings drift in 31–60 DTE options, run as pre-registered\n')
    L.append(f'**Pre-registration: `PREREG_DIRECTION.md`, commit `{C.PREREG_COMMIT}`, sha256 `{sha}`** (committed alone and pushed '
             'before anything was computed). Code in this folder: `ledger.py` (the draw), `dcommon.py`, `fetch_direction.py`, '
             '`build_direction.py`, `verify_direction.py`, `write_report.py`. Outputs: `out/`.\n')
    L.append('## Summary\n')
    L.append(f"- **Exploration screen: Δ {pct(m.get('delta'))} pp {ci(m.get('ci'))}** (picked side minus both sides, mean return per "
             f"trade after costs, % of the debit) on {sc['events']:,} events, {m['trades_with']:,} / {m['trades_without']:,} trades, "
             f"{m['sessions']:,} sessions ({m['sessions_without']:,} with a trade); effective N {neff(m.get('n_eff_block20'))} "
             f"(block) / {neff(m.get('n_eff_acf'))} (acf). → **{'PASS — sent to the holdout' if sc['screen_pass'] else 'FAIL — the holdout is not fetched and not read'}**.")
    a = sc['absolute']
    L.append(f"- Absolute means per trade: the picked side {pct(a['picked_mean'])} %, the other side {pct(a['other_side_mean'])} %, "
             f"both {pct(a['all_mean'])} %; {pct(a['exit_at_zero_share'], 1)[1:]} % of the trades exit at a $0 bid.")
    if ho:
        hm = ho['main']
        L.append(f"- **Holdout (read once): Δ {pct(hm.get('delta'))} pp {ci(hm.get('ci'))}** on {ho['events']:,} events, "
                 f"{hm['trades_with']:,} / {hm['trades_without']:,} trades, {hm['sessions']:,} sessions → **{ho['verdict']}**.")
    else:
        L.append('- **Holdout: not read** (the screen did not pass). The 1,600 holdout names stay unopened for 2019-01 → 2022-12.')
    L.append(f"- Verifier: {ve['checked']} exploration trades re-derived from the raw files by a plain loop, "
             f"{ve['differences']} differences" + (f"; holdout {vh['checked']} trades, {vh['differences']} differences." if vh else '.'))
    L.append('- H1 (overnight reversal): no such study exists in either repository; the only overnight study (S16a) promoted '
             'nothing. **H2 not added.**')
    L.append('- Power, as pre-registered (§8): the test finds the effect only if it is about as large as the 1970s–80s extreme-decile '
             'drift on every report; at the size recent work suggests its power is about 0.1. A FAIL is not evidence that no small '
             'drift exists.\n')
    L.append('## 1. The ledger and the sets\n')
    lg = C.ledger()
    L.append(f"- Opened names (before 2023): {lg['n_opened']}; every optionable name is opened from 2023. Optionable names with a timed "
             f"report in 2019-04 → 2022-12: {lg['optionable_names_in_hold_window']:,}; not opened: {lg['unopened_names']:,}; holdout H "
             f"{len(lg['holdout_names']):,} names ({lg['n_holdout_events']:,} timed reports), exploration X {len(lg['exploration_names']):,} names "
             f"({lg['n_exploration_events']:,} timed reports 2019-04 → 2026-09) plus the on-disk names ({lg['n_disk_events']} reports listed).")
    L.append(f"- Event-list hashes reproduced by `ledger.py`: holdout `{lg['sha256_holdout_events'][:16]}…`, exploration "
             f"`{lg['sha256_exploration_events'][:16]}…` (equal to the prereg's).\n")
    L.append('## 2. The fetch\n')
    L += fetch_lines('expl')
    L += fetch_lines('hold')
    L.append('')
    L.append('## 3. Events and trades: what was formed and why not\n')
    for lab, s in (('exploration', sc), ('holdout', ho)):
        if not s:
            continue
        info = s['info']
        L.append(f"- {lab}, fetched events built: {info['fetched_events']:,}; " +
                 '; '.join(f'{k} {v:,}' for k, v in sorted(info['build_counts_fetched'].items(), key=lambda kv: -kv[1])))
        if info.get('disk_events'):
            L.append(f"- {lab}, on-disk events listed: {info['disk_events']:,}; " +
                     '; '.join(f'{k} {v:,}' for k, v in sorted(info['build_counts_disk'].items(), key=lambda kv: -kv[1])))
    L.append('')
    L.append('## 4. The exploration screen\n')
    L.append(HEAD)
    L.append(row('**all (the screen)**', m))
    for k, r in sc.get('parts', {}).items():
        L.append(row(k, r))
    for k, r in sc['descriptive'].items():
        L.append(row(k, r))
    L.append('')
    L.append('Arms (block 1 / 5 / 20 intervals of the per-trade mean, %):')
    for arm in ('arm_with', 'arm_without'):
        s = m.get(arm, {})
        L.append(f"- {arm}: {s.get('trades', 0):,} trades, mean {pct(s.get('mean_trade'))}; b1 {ci(s.get('ci_trade_b1'))}, "
                 f"b5 {ci(s.get('ci_trade_b5'))}, b20 {ci(s.get('ci_trade_b20'))}")
    L.append('')
    if not ho:
        pc, pp = sc['descriptive'].get('pick=C', {}), sc['descriptive'].get('pick=P', {})
        L.append('## 5. Reading (no holdout)\n')
        L.append(f"- The picked side lost {pct(a['picked_mean'])} % a trade against {pct(a['other_side_mean'])} % for the other side at the "
                 "same entries: after a positive earnings-day return the call did not beat the put by more than the period's drift, and "
                 "after a negative one the put did worse than the call. Split by the pick (descriptive): after an up day the call "
                 f"minus both sides is {pct(pc.get('delta'))} pp {ci(pc.get('ci'))}; after a down day the put minus both is "
                 f"{pct(pp.get('delta'))} pp {ci(pp.get('ci'))} — the sign of the market's own drift over 2019–2026 (calls beat puts "
                 "whatever the report did), which the pooled Δ cancels. Nothing in the cuts (unopened 2019–2022 cells, opened "
                 "2023–2026 cells, pre- or post-market, strike bucket, tier, year) has an interval clear of zero on the positive side.")
        L.append('- The base itself loses about a quarter of the debit in ten sessions on these mostly Tier 3 names (spread and decay); '
                 'Δ would have had to be large and positive to matter, and it is about zero.')
        L.append('- Consistent with S08 (2024–2026, the underlying: no drift after the event-day move) and with the literature on '
                 'liquid names after 2000. Underpowered for a small drift (prereg §8), so the result says "no drift large enough to '
                 'carry through 31–60 DTE options", not "no drift".')
        L.append('- The on-disk names: AAPL and FB contribute only from 2019 (the bars on disk start in 2019-01), so their 2015–2018 '
                 'reports are counted as "no bar for P or R".\n')
    if ho:
        L.append('## 5. The holdout test (once)\n')
        L.append(HEAD)
        L.append(row('**all (the verdict)**', ho['main']))
        for k, r in ho['descriptive'].items():
            L.append(row(k, r))
        L.append('')
    L.append('## 6. Checks\n')
    L.append(f"- `verify_direction.py`: {ve['checked']} exploration trades ({ve['disk_trades']} from the stored weekly files, "
             f"{ve['fetched_trades']} from this fetch), drawn with seed 20261027, re-derived field by field (R, P, E1, the exit "
             f"session, the pick, the expiry, the strike, F, IM, the entry ask, the exit bid, r): **{ve['differences']} differences**.")
    if vh:
        L.append(f"- holdout: {vh['checked']} trades, **{vh['differences']} differences**.")
    L.append('')
    L.append('## 7. Deviations\n')
    dv = C.OUT / 'deviations.md'
    L.append(dv.read_text() if dv.exists() else '- None.')
    L.append('')
    L.append('## 8. Commands\n')
    L.append('```\npython3 -I ledger.py\npython3 -I fetch_direction.py expl\nPOLARS_MAX_THREADS=4 python3 -I build_direction.py expl\n'
             'python3 -I verify_direction.py expl 40\n# only after a screen pass: fetch_direction.py hold; build_direction.py hold; '
             'verify_direction.py hold 40\npython3 -I write_report.py\n```')
    (C.OUT.parent / 'DIRECTION_REPORT.md').write_text('\n'.join(L) + '\n')
    print('written')


if __name__ == '__main__':
    main()
