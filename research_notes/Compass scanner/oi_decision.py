"""
oi_decision.py — the owner's answer 3, from SELECTION data only: at every Compass scanner signal onset on 2023-11-21 ->
2026-10-21 (non-held-out months only), the 0DTE contract the rule picks with the OI >= 250 filter (v0) against
(a) the filter off, open interest still in the ranking, and (b) no open interest anywhere (the rule as it can run where
no daily OI exists). No exit, no P&L, no forward return is computed.

An onset is a minute with score >= 80 whose last evaluated minute before it had score < 80 (or none): the position-free
stand-in for v0's entries (v0 enters only at onsets; being in a position removes some of them).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from multiprocessing import get_context
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scanner_lib as S  # noqa: E402


def onsets(st, thr=80.0):
    out, prev = [], None
    for s in range(S.EVAL_FIRST - 1, S.EVAL_LAST):
        if not st['valid'][s]:
            continue
        sc = st['score'][s]
        if sc >= thr and (prev is None or prev < thr):
            out.append(s + 1)
        prev = sc
    return out


def one(args):
    name, d = args
    st = S.scan(name, d)
    if st is None:
        return []
    rows = []
    for m in onsets(st):
        s = m - 1
        bull = bool(st['bull'][s])
        E = float(st['C'][s])
        res = {}
        for mode in ('v0', 'nofilter', 'none'):
            c, why = S.pick_contract(name, d, m, bull, E, oi_mode=mode)
            res[mode] = (c['K'], c['r']) if c else None
            res[mode + '_why'] = why
        rows.append(dict(name=name, day=d, m=m, bull=bull, **res))
    return rows


if __name__ == '__main__':
    sp = S.split_sessions('option')
    days = [d for d in sp['pick'] + sp['check'] if '2023-11-21' <= d <= S.LAST_DAY]
    assert not any(S.held_month(d) for d in days)
    jobs = [(n, d) for n in S.PRIMARY for d in days if S.chain_path(n, d) is not None]
    with get_context("spawn").Pool(4) as pool:
        rows = [r for rs in pool.map(one, jobs, chunksize=4) for r in rs]
    out = {'sessions': len(days), 'first': days[0], 'last': days[-1], 'jobs': len(jobs), 'onsets': len(rows)}
    for grp, names in (('SPY+QQQ', ('SPY', 'QQQ')), ('SPY', ('SPY',)), ('QQQ', ('QQQ',)), ('IWM', ('IWM',)),
                       ('SPY+QQQ+IWM', S.PRIMARY)):
        R = [r for r in rows if r['name'] in names]
        g = {'onsets': len(R)}
        for alt in ('nofilter', 'none'):
            base = [r for r in R if r[alt] is not None or r['v0'] is not None]
            ch = [r for r in base if r[alt] != r['v0']]
            g[alt] = dict(picks=len(base), changed=len(ch), share=(len(ch) / len(base) if base else float('nan')),
                          v0_none_alt_pick=sum(1 for r in ch if r['v0'] is None),
                          both_pick_differ=sum(1 for r in ch if r['v0'] is not None and r[alt] is not None))
        g['v0_reasons'] = dict(Counter(r['v0_why'] for r in R))
        out[grp] = g
    S.OUT.mkdir(exist_ok=True)
    (S.OUT / 'oi_decision.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))
