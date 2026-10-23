"""
lookahead.py — DR-GCE's lookahead rebuild (GATE_PREREG.md section 8). For 3 sessions, every bar t's decision (both
modes, and the contract picked on the entry row) is rebuilt with every input after minute t + 1 blanked (SPX prints, SPY
bars, chain rows); it must equal the full-file decision. The control reads SPX one minute ahead (the print stamped t + 2
taken as bar t's close) under the same cut; it must change decisions.
"""
from __future__ import annotations

import csv
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dr_gce as D  # noqa: E402

for nm in ('spx_closes', 'spy_bars', 'oi_arrays'):
    f = getattr(D, nm)
    if nm == 'oi_arrays':
        c = lru_cache(None)(lambda d, Kt, f=f: f(d, np.array(Kt)))
        setattr(D, nm, lambda d, K, c=c: tuple(a.copy() for a in c(d, tuple(K))))
    else:
        c = lru_cache(None)(f)
        setattr(D, nm, (lambda d, c=c: (c(d).copy() if isinstance(c(d), np.ndarray) else tuple(a.copy() for a in c(d)))))


def decisions(day: D.Day, t: int):
    out = []
    for mode, fn in ((1, D.mode1_at), (2, D.mode2_at)):
        side = fn(day, t)
        k = None
        if side:
            c, _ = D.pick(day, t + 1, side, day.sigma(t), float(day.S[t])) if np.isfinite(day.sigma(t)) else (None, None)
            k = None if c is None else (c['K'], c['ask'])
        out.append((side, k))
    return out


def main():
    rows = list(csv.DictReader(open(HERE / 'out' / 'signals.csv')))
    cnt = {}
    for r in rows:
        cnt[r['d']] = cnt.get(r['d'], 0) + 1
    days = sorted(cnt, key=lambda d: (-cnt[d], d))[:3]
    tot = dif = cdif = csig = sig = 0
    for d in sorted(days):
        full = D.Day(d)
        for t in range(0, D.NBAR - 5):
            a = decisions(full, t)
            b = decisions(D.Day(d, cut=t + 1), t)
            c = decisions(D.Day(d, cut=t + 1, peek=1), t)
            tot += 2
            sig += sum(1 for x in a if x[0])
            csig += sum(1 for x, y in zip(a, c) if x[0] or y[0])
            dif += sum(1 for x, y in zip(a, b) if x != y)
            cdif += sum(1 for x, y in zip(a, c) if x != y)
    print(f'lookahead: {len(days)} sessions ({", ".join(sorted(days))}), {tot} bar decisions, {sig} signals; '
          f'cut rebuild differs on {dif}; control (SPX read 1 minute ahead) differs on {cdif} of {csig} decisions '
          f'where either flags a signal')


if __name__ == '__main__':
    main()
