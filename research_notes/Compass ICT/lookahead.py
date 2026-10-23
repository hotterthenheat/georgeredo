"""
lookahead.py — rebuilds 3 sessions' trades from the files cut at the entry minute (bars stamped < m, prints and quotes
stamped <= m) and compares every entry-time figure with the full-file run; a control cuts one minute earlier, where the
setup must no longer be reproduced.
"""
from __future__ import annotations

import numpy as np

import ict

FIELDS = ('t', 'side', 'ext', 'K', 'ask', 'delta', 'spread', 'entry_u', 'tp1', 'tp2')


def key(tr):
    return tuple(None if tr[f] is None else round(float(tr[f]), 9) for f in FIELDS) + \
        tuple(None if z is None else round(z, 9) for z in (tr['setup']['zone'] or (None, None)))


def find(d, P, m, cut):
    tr, *_ = ict.run_day(d, P, cut=cut)
    return next((t for t in tr if t['m'] == m), None)


def main():
    picks = []
    seen = set()
    for name in ('v0', 'A no HTF bias', 'A no killzones', 'A no sweep'):
        for d in ict.DAYS:
            tr, *_ = ict.run_day(d, ict.VARIANTS[name])
            if tr and d not in seen and len(picks) < 3:
                picks.append((name, d, tr[0]))
                seen.add(d)
    n_val = n_diff = c_diff = 0
    for name, d, full in picks:
        P = ict.VARIANTS[name]
        m = full['m']
        cut = find(d, P, m, m)
        a, b = key(full), (key(cut) if cut else None)
        dif = sum(x != y for x, y in zip(a, b)) if b else len(a)
        n_val += len(a)
        n_diff += dif
        ctl = find(d, P, m, m - 1)
        cd = sum(x != y for x, y in zip(a, key(ctl))) if ctl else len(a)
        c_diff += cd
        print(f'{name} {d} entry {ict_m(m)}: cut at the entry minute -> {dif} of {len(a)} differ; '
              f'control cut a minute earlier -> {cd} of {len(a)} differ ({"setup gone" if ctl is None else "setup changed"})')
    print(f'TOTAL: {n_diff} differences in {n_val} values at the entry cut; control {c_diff} of {n_val} differ')


def ict_m(m):
    h, mm = divmod(570 + m, 60)
    return f'{h:02d}:{mm:02d}'


if __name__ == '__main__':
    main()
