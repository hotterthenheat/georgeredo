"""funnel_m2.py — why Mode 2 fired 0 times: the count of trigger bars passing each condition in turn (as pinned)."""
import math
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dr_gce as D  # noqa: E402


def one(d):
    day = D.Day(d)
    c = [0] * 6
    for t in range(30, 316):
        s, St, vw = day.sigma(t), day.S[t], day.vwap[t]
        if not (np.isfinite(s) and np.isfinite(St) and np.isfinite(vw)):
            continue
        c[0] += 1
        if abs(St - vw) / (s * St * math.sqrt(t + 1)) < 2.80:
            continue
        c[1] += 1
        bk = day.book(t)
        if bk is None or bk['regime'] != 1:
            continue
        c[2] += 1
        if not any(np.isfinite(w) and abs(St - w) <= 0.0015 * St for w in (bk['CW'], bk['PW'])):
            continue
        c[3] += 1
        if not D.vol_ratio(day, t, bk) <= 1.18:
            continue
        c[4] += 1
        if D.mode2_at(day, t + 1):
            c[5] += 1
    return c


if __name__ == '__main__':
    with mp.get_context('spawn').Pool(4) as p:
        cs = p.map(one, D.sessions())
    tot = np.sum(cs, axis=0)
    print('Mode 2 funnel (trigger bars 10:00-14:45, 504 sessions): sigma defined', tot[0], '| stretch >= 2.80', tot[1],
          '| S > Z_gamma', tot[2], '| within 0.15% of CW/PW', tot[3], '| VolRatio <= 1.18', tot[4], '| confirmed', tot[5])
