"""
phase_b.py — the improvement round (Phase B), on the EXPLORATION set only (never a held-out ticker or month).

Rules (set before any variant was computed, in the brief of 2026-10-22): Phase A's verdicts are final; a variant may change
a threshold, combine features that each showed a positive exploration difference in Phase A, use a different feature from a
pre-registered source, or condition on tier / expiry bucket / settlement type. EVERY variant computed is written to the
trials ledger (out/phase_b_trials.csv), whatever it shows.

Walk-forward inside exploration: PICK = exploration sessions to 2024-06-30, CHECK = exploration sessions from 2024-07-01.
For each variant: Δ (the prereg's statistic: mean per trade with − without, after costs) and its 20-session block interval on
PICK, on CHECK and on the whole exploration set.

Selection (fixed here, before the variants were computed): a variant is eligible when its PICK Δ > 0 with the PICK interval's
lower end > 0, AND its CHECK Δ > 0 with the CHECK interval's lower end > 0. Among the eligible, at most one per family
(veto, exit, direction, combination) — the one with the highest PICK lower end — and at most 3 in all (if four families have
one, the three with the highest CHECK lower end). Nothing is selected on the whole-exploration figures.

  python3 -I phase_b.py        → out/phase_b_trials.csv, out/phase_b_trials.json, out/phase_b_selection.json
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402
import stats as ST  # noqa: E402
import screen as SC  # noqa: E402

SPLIT_DAY = '2024-07-01'
ARM = SC.ARM_COLS


def veto(T, defined, vetoed):
    return SC.veto(T, defined, vetoed)


def direction(T, col, extra=None, invert=False, thr=None):
    d = pl.col(col).is_not_null() & (pl.col(col) != 0)
    if thr is not None:
        d = d & (pl.col(col).abs() >= thr)
    if extra is not None:
        d = d & extra
    pointed = (pl.col('right') == 'C') == (pl.col(col) > 0)
    return SC.choose(T, d, ~pointed if invert else pointed)


def exit_alt(T, col, extra=None):
    d = T.filter(pl.col(col).is_not_null() & (extra if extra is not None else pl.lit(True)))
    return SC.arms(d, d, col, 'r')


def combo(T, veto_expr=None, exit_col=None, dir_col=None, venue=False):
    """a model on top of the base trades: optional spread veto, optional VN1 venue pick, optional direction, optional time
    exit where it applies; compared with ALL base trades of the same scope (no other decision)"""
    base = T
    w = T
    if veto_expr is not None:
        w = w.filter(~veto_expr)
    if venue:
        vw, vwo = SC.f_VN1(w)
        drop = vwo.join(vw.select('tid'), on='tid', how='anti').select('tid')
        w = w.join(drop, on='tid', how='anti')
    if dir_col is not None:
        keep = (pl.col(dir_col).is_null()) | (pl.col(dir_col) == 0) | ((pl.col('right') == 'C') == (pl.col(dir_col) > 0))
        w = w.filter(keep)
    if exit_col is not None:
        w = w.with_columns(pl.when(pl.col(exit_col).is_not_null()).then(pl.col(exit_col)).otherwise(pl.col('r')).alias('r_model'))
    else:
        w = w.with_columns(pl.col('r').alias('r_model'))
    return SC.arms(w, base, 'r_model', 'r')


def variants(T):
    zero = pl.col('eb') == '0DTE'
    V = []
    add = lambda vid, fam, desc, fn: V.append((vid, fam, desc, fn))  # noqa: E731
    # veto thresholds and conditioning
    add('BV1a', 'veto', 'V1 spread veto at 5%', lambda: veto(T, pl.col('spread').is_not_null(), pl.col('spread') > 0.05))
    add('BV1b', 'veto', 'V1 spread veto at 3%', lambda: veto(T, pl.col('spread').is_not_null(), pl.col('spread') > 0.03))
    add('BV1c', 'veto', 'V1 spread veto at 20%', lambda: veto(T, pl.col('spread').is_not_null(), pl.col('spread') > 0.20))
    add('BV1d', 'veto', 'V1 at 10%, 0DTE only', lambda: veto(T, pl.col('spread').is_not_null() & zero, pl.col('spread') > 0.10))
    add('BV1e', 'veto', 'V1 at 10%, 1-60 DTE only', lambda: veto(T, pl.col('spread').is_not_null() & ~zero, pl.col('spread') > 0.10))
    add('BV3a', 'veto', 'V3 volume veto at 1,000', lambda: veto(T, pl.col('v3vol').is_not_null(), pl.col('v3vol') < 1000))
    add('BV3b', 'veto', 'V3 volume veto at 10', lambda: veto(T, pl.col('v3vol').is_not_null(), pl.col('v3vol') < 10))
    add('BV2a', 'veto', 'V2 open-interest veto at 100', lambda: veto(T, pl.col('oi').is_not_null(), pl.col('oi') < 100))
    add('BV2b', 'veto', 'V2 open-interest veto at 5,000', lambda: veto(T, pl.col('oi').is_not_null(), pl.col('oi') < 5000))
    add('BV6a', 'veto', 'V6 IV-rank veto at 0.5', lambda: veto(T, pl.col('ivr').is_not_null(), pl.col('ivr') >= 0.5))
    add('BV6b', 'veto', 'V6 low-IV veto: IV rank < 0.2', lambda: veto(T, pl.col('ivr').is_not_null(), pl.col('ivr') < 0.2))
    # exits
    add('BX3a', 'exit', '0DTE time exit at 12:00 (entries before)', lambda: exit_alt(T, 'r_t1200'))
    add('BX3b', 'exit', '0DTE time exit at 13:00 (entries before)', lambda: exit_alt(T, 'r_t1300'))
    add('BX3c', 'exit', '0DTE time exit at 15:00 (entries before)', lambda: exit_alt(T, 'r_t1500'))
    add('BX3d', 'exit', 'X3 (14:00) on SPXW only', lambda: exit_alt(T, 'r_x3', pl.col('name') == 'SPXW'))
    add('BX3e', 'exit', 'X3 (14:00) on the physically settled names only', lambda: exit_alt(T, 'r_x3', pl.col('name') != 'SPXW'))
    add('BX1a', 'exit', '0DTE target at 0.25 IM', lambda: exit_alt(T, 'r_im025'))
    add('BX1b', 'exit', '0DTE target at 0.5 IM', lambda: exit_alt(T, 'r_im050'))
    # direction: thresholds, conditioning, the same sources read the other way
    idx = pl.col('name').is_in(list(C.INDEX))
    add('BD6a', 'direction', 'D6 read the other way (fade the opening-range break)', lambda: direction(T, 'd6', zero & (pl.col('m') >= 45), True))
    add('BD6b', 'direction', 'D6 on 0DTE entries from 13:15', lambda: direction(T, 'd6', zero & (pl.col('m') >= C.mi('13:15'))))
    add('BD6c', 'direction', 'D6 on SPXW only', lambda: direction(T, 'd6', zero & (pl.col('m') >= 45) & (pl.col('name') == 'SPXW')))
    add('BD7a', 'direction', 'D7 read the other way', lambda: direction(T, 'd7', None, True))
    add('BD7b', 'direction', 'D7 on 1-60 DTE only', lambda: direction(T, 'd7', ~zero))
    add('BD3a', 'direction', 'D3 (NOPE) read the other way', lambda: direction(T, 'd3', idx, True))
    add('BD4a', 'direction', 'D4 (tide) read the other way', lambda: direction(T, 'd4', idx, True))
    add('BD1a', 'direction', 'D1 (net premium) read the other way', lambda: direction(T, 'd1', idx, True))
    add('BD2a', 'direction', 'D2 (sweeps) with |value| ≥ $1M', lambda: direction(T, 'd2', idx, False, 1e6))
    add('BD2b', 'direction', 'D2 (sweeps) on 0DTE only', lambda: direction(T, 'd2', idx & zero))
    add('BD26', 'direction', 'D2 and D6 agree (0DTE from 10:15)', lambda: SC.choose(
        T, idx & zero & (pl.col('m') >= 45) & pl.col('d2').is_not_null() & (pl.col('d2') != 0) & (pl.col('d6') != 0)
        & ((pl.col('d2') > 0) == (pl.col('d6') > 0)), (pl.col('right') == 'C') == (pl.col('d6') > 0)))
    # combinations of features with a positive Phase A exploration difference
    sp = pl.col('spread').is_not_null() & (pl.col('spread') > 0.10)
    add('BC1', 'combination', 'V1 veto + X3 exit, against all base trades', lambda: combo(T, sp, 'r_x3'))
    add('BC2', 'combination', 'V1 veto + VN1 venue + X3 exit, against all base trades', lambda: combo(T, sp, 'r_x3', venue=True))
    add('BC3', 'combination', 'V1 veto + X3 exit + D6 direction, against all base trades', lambda: combo(T, sp, 'r_x3', 'd6'))
    add('BC4', 'combination', 'V1 veto + X3 exit, 0DTE entries before 14:00 only', lambda: combo(T.filter(zero & (pl.col('m') < C.X3_M)), sp, 'r_x3'))
    return V


def periods(T):
    s = SC.split_sessions('expl')
    return {'pick': [d for d in s if d < SPLIT_DAY], 'check': [d for d in s if d >= SPLIT_DAY], 'all': s}


def measure(w, wo, sess_all, lab):
    if wo.height == 0:
        return dict(delta=None, ci=None)
    out = {}
    for k, ss in sess_all.items():
        a, b = (w.filter(pl.col('day').is_in(ss)), wo.filter(pl.col('day').is_in(ss)))
        if b.height == 0:
            out[k] = dict(delta=None, ci=None, trades_with=0, trades_without=0)
            continue
        x, y = b['day'].min(), b['day'].max()
        out[k] = ST.delta(a, b, [d for d in ss if x <= d <= y], full=False)
    return out


def main():
    C.set_split('expl')
    T = pl.read_parquet(C.WORK / 'expl' / 'trades_with_inputs.parquet')
    bx = pl.read_parquet(C.WORK / 'expl' / 'b_exits.parquet')
    T = T.join(bx, on=['name', 'day', 'm', 'eb', 'strike', 'right', 'sb'], how='left')
    P = periods(T)
    ledger = []
    for vid, fam, desc, fn in variants(T):
        w, wo = fn()
        res = measure(w, wo, P, vid)
        ledger.append(dict(id=vid, family=fam, definition=desc, **{k: res.get(k) for k in ('pick', 'check', 'all')}))
        a = res.get('all') or {}
        print(vid, fam, a.get('delta'), a.get('ci'), (res.get('pick') or {}).get('delta'), (res.get('check') or {}).get('delta'), flush=True)
    C.jdump(ledger, C.OUT / 'phase_b_trials.json')
    with open(C.OUT / 'phase_b_trials.csv', 'w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['id', 'family', 'definition', 'expl_delta_pct', 'expl_ci_lo', 'expl_ci_hi', 'pick_delta_pct', 'pick_ci_lo', 'pick_ci_hi',
                     'check_delta_pct', 'check_ci_lo', 'check_ci_hi', 'trades_with_all', 'trades_without_all'])
        for L in ledger:
            row = [L['id'], L['family'], L['definition']]
            for k in ('all', 'pick', 'check'):
                v = L.get(k) or {}
                c = v.get('ci') or (None, None)
                row += [None if v.get('delta') is None else round(v['delta'] * 100, 4)] + \
                       [None if (x is None or not math.isfinite(x)) else round(x * 100, 4) for x in c]
            a = L.get('all') or {}
            row += [a.get('trades_with'), a.get('trades_without')]
            wr.writerow(row)

    def lo(v):
        c = (v or {}).get('ci')
        return c[0] if c and c[0] is not None and math.isfinite(c[0]) else -math.inf

    elig = [L for L in ledger if ST.passes(L.get('pick') or {}) and ST.passes(L.get('check') or {})]
    best = {}
    for L in sorted(elig, key=lambda L: -lo(L['pick'])):
        best.setdefault(L['family'], L)
    chosen = sorted(best.values(), key=lambda L: -lo(L['check']))[:3]
    C.jdump(dict(rule=__doc__.split('Selection')[1].split('python3')[0].strip(), trials=len(ledger), eligible=[L['id'] for L in elig],
                 chosen=[L['id'] for L in chosen]), C.OUT / 'phase_b_selection.json')
    print('trials', len(ledger), 'eligible', [L['id'] for L in elig], 'chosen', [L['id'] for L in chosen])


if __name__ == '__main__':
    main()
