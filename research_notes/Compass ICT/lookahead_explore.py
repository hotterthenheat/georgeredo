"""
lookahead_explore.py — prereg section 5's look-ahead check at the exploration's scale: 10 sessions' trades (one drawn per
row, seeded, then v0 again to ten; distinct sessions) rebuilt with every file cut at the entry minute (bars stamped < m,
prints and quotes stamped <= m, ict.Day's `cut`) and every entry-time figure compared with the full-file run; a control
cuts one minute earlier, where the setup must not be reproduced. Reuses lookahead.py's comparison.
"""
from __future__ import annotations

import random
from pathlib import Path

import polars as pl

import explore as X  # noqa: F401  (guard + the HTF history start, as the exploration ran)
import lookahead as LA

HERE = Path(__file__).resolve().parent


def main():
    T = pl.read_csv(HERE / 'out' / 'explore_trades.csv')
    rnd = random.Random(20261023)
    picks, seen = [], set()
    order = list(X.ict.VARIANTS) + ['v0'] * 10
    for row in order:
        if len(picks) >= 10:
            break
        R = [r for r in T.filter(pl.col('row') == row).iter_rows(named=True) if r['day'] not in seen]
        if not R:
            continue
        r = rnd.choice(R)
        picks.append((row, r['day'], r['m']))
        seen.add(r['day'])
    n_val = n_diff = c_diff = 0
    L = []
    for row, d, m in picks:
        P = X.ict.VARIANTS[row]
        full = LA.find(d, P, m, None)
        cut = LA.find(d, P, m, m)
        a = LA.key(full)
        dif = sum(x != y for x, y in zip(a, LA.key(cut))) if cut else len(a)
        ctl = LA.find(d, P, m, m - 1)
        cd = sum(x != y for x, y in zip(a, LA.key(ctl))) if ctl else len(a)
        n_val += len(a)
        n_diff += dif
        c_diff += cd
        L.append(f'{row} {d} entry {LA.ict_m(m)}: cut at the entry minute -> {dif} of {len(a)} differ; control cut a minute '
                 f'earlier -> {cd} of {len(a)} differ ({"setup gone" if ctl is None else "setup changed"})')
        X.ict.chain.cache_clear()
    L.append(f'TOTAL: {len(picks)} sessions, {n_diff} differences in {n_val} values at the entry cut; control {c_diff} of {n_val} differ')
    print('\n'.join(L))
    (HERE / 'out' / 'lookahead_explore.txt').write_text('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
