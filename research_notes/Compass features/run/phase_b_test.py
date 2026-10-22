"""
phase_b_test.py — the once-only holdout test of Phase B's candidates (PREREG_FEATURES_B.md, commit b6737c7): each candidate
exactly as phase_b.py defines it, on Phase A's corrected holdout table ($SP/features_work/hold/trades_with_inputs.parquet).
Pass: holdout Δ > 0 with the 20-session block 95% interval's lower end > 0. Refuses to run twice.

  python3 -I phase_b_test.py   → out/phase_b_holdout.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402
import stats as ST  # noqa: E402
import screen as SC  # noqa: E402
import phase_b as PB  # noqa: E402

CANDIDATES = ('BV1b', 'BX3e', 'BC3')


def main():
    C.set_split('hold')
    dest = C.OUT / 'phase_b_holdout.json'
    if dest.exists():
        raise SystemExit('the Phase B holdout was already read')
    sel = json.loads((C.OUT / 'phase_b_selection.json').read_text())
    assert sorted(sel['chosen']) == sorted(CANDIDATES)
    T = pl.read_parquet(C.WORK / 'hold' / 'trades_with_inputs.parquet')
    assert T['tid'].n_unique() == T.height
    sess_all = SC.split_sessions('hold')
    V = {vid: (fam, desc, fn) for vid, fam, desc, fn in PB.variants(T)}
    out = dict(prereg='b6737c7', candidates=[])
    for vid in CANDIDATES:
        fam, desc, fn = V[vid]
        w, wo = fn()
        a, b = wo['day'].min(), wo['day'].max()
        sess = [d for d in sess_all if a <= d <= b]
        res = dict(id=vid, family=fam, definition=desc, span=dict(first=a, last=b, sessions=len(sess)), pooled=ST.delta(w, wo, sess))
        res['by_tier'] = {t: ST.delta(w.filter(pl.col('tier') == t), wo.filter(pl.col('tier') == t), sess, full=False)
                          for t in ('1', '2', '3', 'U') if wo.filter(pl.col('tier') == t).height}
        res['by_settle'] = {t: ST.delta(w.filter(pl.col('settle') == t), wo.filter(pl.col('settle') == t), sess, full=False)
                            for t in ('physical', 'cash') if wo.filter(pl.col('settle') == t).height}
        res['parts'] = {}
        for lab, cond in (('held-out tickers, all months', pl.col('name').is_in(list(C.HELD_T))),
                          ('exploration tickers, held-out months', ~pl.col('name').is_in(list(C.HELD_T)))):
            bb = wo.filter(cond)
            if bb.height:
                x, y = bb['day'].min(), bb['day'].max()
                res['parts'][lab] = ST.delta(w.filter(cond), bb, [d for d in sess_all if x <= d <= y], full=False)
        res['pass'] = ST.passes(res['pooled'])
        out['candidates'].append(res)
        p = res['pooled']
        print(vid, p['trades_with'], p['trades_without'], p['delta'], p['ci'], res['pass'], flush=True)
    C.jdump(out, dest)


if __name__ == '__main__':
    main()
