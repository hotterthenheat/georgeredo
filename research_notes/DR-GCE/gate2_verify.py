"""
gate2_verify.py — GATE2_PREREG.md section 6: the plain-loop re-derivation of >= 20 pairs. The trades are rebuilt by
verify_plain.py's plain code (imported, not edited; it shares no function with dr_gce.py) and the sensitivity outcome by a
plain loop here; compared with out/gate2_pairs.csv. dr_gce is imported for the calendar only.

  python3 gate2_verify.py [MIN_PAIRS]
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_plain as V  # noqa: E402


def watch(X, m, k, r, ask, stop):
    for j in range(m + 1, min(m + 4, 390) + 1):
        q = X.Q.get((j, k, r))
        b = q[0] if q else None
        if b is None or b != b:
            continue
        if b <= stop * ask + 1e-9:
            return 0, 'stop', j
        if b >= 1.18 * ask - 1e-9:
            return 1, 'touch', j
    return 0, 'none', min(m + 4, 390)


def main():
    import dr_gce as D
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    rows = list(csv.DictReader(open(HERE / 'out' / 'gate2_pairs.csv')))
    by = {}
    for r in rows:
        by.setdefault(r['d'], []).append(r)
    days = sorted(by)
    pick, i = [], 0
    for d in days[::3] + days:
        if sum(len(by[x]) for x in pick) >= want:
            break
        if d not in pick:
            pick.append(d)
    diffs, npair = [], 0
    for d in sorted(pick):
        X = V.Sess(d, D.prev_tday(d))
        for r in by[d]:
            npair += 1
            s, side = int(r['sbar']), int(r['side'])
            a = V.trade(X, 1, s, s, side)
            if a is None or a['touch'] != int(r['sig_touch']) or a['how'] != r['sig_how'] or a['stop'] != float(r['sig_stopfrac']):
                diffs.append((d, s, 'signal', a))
            o = V.trade(X, 1, s, s, -side)
            if r['opp_ok'] != '1':
                if o is not None:
                    diffs.append((d, s, 'opp exists in plain', o))
                continue
            if o is None:
                diffs.append((d, s, 'opp missing in plain'))
                continue
            for f in ('touch', 'last'):
                if int(o[f]) != int(r[f'opp_{f}']):
                    diffs.append((d, s, f, o[f], r[f'opp_{f}']))
            if o['how'] != r['opp_how']:
                diffs.append((d, s, 'how', o['how'], r['opp_how']))
            for f, g in (('K', 'opp_K'), ('ask', 'opp_ask'), ('stop', 'opp_stopfrac')):
                if abs(float(o[f]) - float(r[g])) > 1e-9:
                    diffs.append((d, s, f, o[f], r[g]))
            t2, h2, l2 = watch(X, s + 1, o['K'], 0 if -side > 0 else 1, o['ask'], float(r['sig_stopfrac']))
            if (t2, h2, l2) != (int(r['sens_touch']), r['sens_how'], int(r['sens_last'])):
                diffs.append((d, s, 'sens', (t2, h2, l2)))
    print(f'gate2_verify: {len(pick)} sessions, {npair} pairs re-derived (signal, opposite, sensitivity), {len(diffs)} differences')
    for x in diffs[:20]:
        print('  ', x)


if __name__ == '__main__':
    main()
