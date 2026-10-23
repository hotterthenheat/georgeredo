"""
signal_check.py — prereg section 6 (the owner's step 3a): the Compass scanner's direction on the underlying, before any
option. For every evaluated minute (09:31-15:30) of SPY, QQQ and IWM on the signal layer's sessions: the score, the
direction, and the signed forward return of the underlying over h = 5, 15, 30, 60 minutes (the close of the bar stamped
m - 1 + h against the close of the signal bar, stamped m - 1), in bp, and in units of the session's 09:30 implied move
where a 0DTE chain exists. A v0 signal is a minute with score >= 80. The baseline is every evaluated minute without a v0
signal, matched to the signals by name and minute of day.

python signal_check.py build pick|check   -> WORK/signal_<split>.npz   (per session x cell sums)
python signal_check.py stats pick|check   -> out/signal_check_<split>.json
"""
from __future__ import annotations

import json
import sys
from multiprocessing import get_context
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scanner_lib as S  # noqa: E402

H = (5, 15, 30, 60)
NM = S.EVAL_LAST                       # 360 evaluated minutes: m = 1..360, cell index m - 1
NAMES = S.PRIMARY


def session_rows(args):
    """one (name, day): per evaluated minute: valid, score, bull, onset, fwd bp per h, fwd IM units per h"""
    name, d = args
    st = S.scan(name, d)
    out = dict(valid=np.zeros(NM, bool), score=np.full(NM, np.nan), bull=np.zeros(NM, bool), onset=np.zeros(NM, bool),
               bp=np.full((NM, len(H)), np.nan), im=np.full((NM, len(H)), np.nan), has_im=False)
    if st is None:
        return name, d, out
    c = S.day_bars(name, d)[3]
    IM = None
    if d >= '2022-11-11' and S.chain_path(name, d) is not None:
        fi = S.forward_im(name, d, S.IM_MINUTE)
        IM = fi[2] if fi else None
    out['has_im'] = IM is not None
    prev = None
    for m in range(S.EVAL_FIRST, S.EVAL_LAST + 1):
        s = m - 1
        if not st['valid'][s] or not np.isfinite(c[s]):
            continue
        j = m - 1
        sc = st['score'][s]
        out['valid'][j] = True
        out['score'][j] = sc
        out['bull'][j] = st['bull'][s]
        out['onset'][j] = sc >= 80 and (prev is None or prev < 80)
        prev = sc
        sign = 1.0 if st['bull'][s] else -1.0
        for hi, h in enumerate(H):
            f = s + h
            if f <= S.NBAR - 1 and np.isfinite(c[f]):
                out['bp'][j, hi] = sign * (c[f] / c[s] - 1.0) * 1e4
                if IM:
                    out['im'][j, hi] = sign * (c[f] - c[s]) / IM
    return name, d, out


def build(split: str):
    sp = S.split_sessions('signal')[split]
    assert not any(S.held_month(d) for d in sp)
    jobs = [(n, d) for d in sp for n in NAMES]
    with get_context("spawn").Pool(4) as pool:
        res = pool.map(session_rows, jobs, chunksize=8)
    nd, nn = len(sp), len(NAMES)
    di = {d: i for i, d in enumerate(sp)}
    arr = {k: np.zeros((nd, nn, NM) + sh, dt) for k, sh, dt in (('valid', (), bool), ('score', (), float), ('bull', (), bool),
                                                                 ('onset', (), bool), ('bp', (len(H),), float),
                                                                 ('im', (len(H),), float))}
    arr['score'][:] = np.nan
    arr['bp'][:] = np.nan
    arr['im'][:] = np.nan
    for name, d, o in res:
        i, n = di[d], NAMES.index(name)
        for k in ('valid', 'score', 'bull', 'onset', 'bp', 'im'):
            arr[k][i, n] = o[k]
    S.WORK.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(S.WORK / f'signal_{split}.npz', days=np.array(sp), **arr)
    print('built', split, nd, 'sessions', int(arr['valid'].sum()), 'evaluated minutes', int((arr['score'] >= 80).sum()), 'signals')


def matched(sig, val, W, names_mask=None):
    """sig: (days, names, minutes) bool signal mask; val: (days, names, minutes) values (NaN = undefined).
    -> dict of point estimates and block-20 intervals: the signals' mean, the baseline's mean, and the matched excess
    (each signal minus the mean of the non-signal minutes of its own name and minute of day)"""
    ok = np.isfinite(val)
    if names_mask is not None:
        ok = ok & names_mask[None, :, None]
    s_m = sig & ok
    b_m = (~sig) & ok
    nd = val.shape[0]
    v0 = np.where(ok, val, 0.0)
    Ss = (v0 * s_m).reshape(nd, -1)
    Ns = s_m.reshape(nd, -1).astype(float)
    Sb = (v0 * b_m).reshape(nd, -1)
    Nb = b_m.reshape(nd, -1).astype(float)

    def est(w):
        ss, ns, sb, nb = w @ Ss, w @ Ns, w @ Sb, w @ Nb
        with np.errstate(invalid='ignore', divide='ignore'):
            bc = np.where(nb > 0, sb / nb, np.nan)
            keep = np.isfinite(bc) & (ns > 0)
            exc = np.where(keep, ss - bc * ns, 0.0).sum(-1) / np.where(keep, ns, 0.0).sum(-1)
            sm = ss.sum(-1) / ns.sum(-1)
            bm = sb.sum(-1) / nb.sum(-1)
        return exc, sm, bm

    one = np.ones((1, nd))
    e0, s0, b0 = (float(x[0]) for x in est(one))
    eb, sbt, bbt = est(W)
    return dict(n_signals=int(Ns.sum()), n_baseline=int(Nb.sum()), sessions=nd,
                signal_mean=s0, signal_ci=S.pct(sbt), baseline_mean=b0, baseline_ci=S.pct(bbt),
                excess=e0, excess_ci=S.pct(eb))


def stats(split: str):
    z = np.load(S.WORK / f'signal_{split}.npz')
    days = [str(x) for x in z['days']]
    valid, score, onset, bull = z['valid'], z['score'], z['onset'], z['bull']
    nd = len(days)
    W = S.boot_W(nd, 20)
    sig = valid & (score >= 80)
    out = {'split': split, 'sessions': nd, 'first': days[0], 'last': days[-1], 'block': 20, 'draws': int(W.shape[0]),
           'evaluated_minutes': int(valid.sum()), 'signals': int(sig.sum()), 'onsets': int(onset.sum()),
           'signals_bull': int((sig & bull).sum()), 'signals_bear': int((sig & ~bull).sum()),
           'grade_A': int((valid & (score >= 80) & (score < 90)).sum()), 'grade_Aplus': int((valid & (score >= 90)).sum())}
    for hi, h in enumerate(H):
        val = z['bp'][..., hi]
        key = f'h{h}'
        out[key] = {'pooled': matched(sig, val, W)}
        for n, name in enumerate(NAMES):
            mask = np.zeros(len(NAMES), bool)
            mask[n] = True
            out[key][name] = matched(sig, val, W, mask)
        out[key]['onsets_only'] = matched(onset, val, W)          # descriptive: onset minutes against every other minute
        out[key]['grade_A'] = matched(sig & (score < 90), val, W)
        out[key]['grade_Aplus'] = matched(sig & (score >= 90), val, W)
        out[key]['bull_only'] = matched(sig & bull, val, W)
        out[key]['bear_only'] = matched(sig & ~bull, val, W)
        # by year: point estimates only
        yrs = sorted({d[:4] for d in days})
        out[key]['by_year'] = {}
        for y in yrs:
            idx = np.array([d[:4] == y for d in days])
            r = matched(sig[idx], val[idx], np.ones((1, int(idx.sum()))))
            out[key]['by_year'][y] = dict(n=r['n_signals'], signal=r['signal_mean'], baseline=r['baseline_mean'], excess=r['excess'])
        imv = z['im'][..., hi]
        if np.isfinite(imv).any():
            out[key]['im_units_pooled'] = matched(sig, imv, W)
    # the gate (prereg 6.3)
    g = {}
    for h in (15, 30):
        p = out[f'h{h}']['pooled']
        g[f'h{h}'] = dict(excess=p['excess'], excess_lo=p['excess_ci'][0], signal=p['signal_mean'],
                          passes=bool(p['excess'] > 0 and p['excess_ci'][0] > 0 and p['signal_mean'] > 0))
    out['gate'] = g
    out['gate_passes'] = bool(any(v['passes'] for v in g.values()))
    S.OUT.mkdir(exist_ok=True)
    (S.OUT / f'signal_check_{split}.json').write_text(json.dumps(out, indent=1))
    print(json.dumps({k: out[k] for k in ('split', 'sessions', 'signals', 'gate', 'gate_passes')}, indent=1))


if __name__ == '__main__':
    cmd, split = sys.argv[1], sys.argv[2]
    assert split in ('pick', 'check')
    build(split) if cmd == 'build' else stats(split)
