"""
gate2.py — DR-GCE Gate 2 (direction against volatility), exactly as GATE2_PREREG.md pins it. Reuses dr_gce.py by import
(never edited). Files only; deterministic.

  python3 gate2.py          # pairs, baseline stop-first replay, paired difference -> out/gate2_*
"""
from __future__ import annotations

import csv
import json
import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dr_gce as D  # noqa: E402  (imports guard first)

AL = D.AL
OUT = HERE / 'out'
GATE1_BASE_MEAN = 0.1599591836734694


def signals() -> list[dict]:
    rows = list(csv.DictReader(open(OUT / 'signals.csv')))
    for r in rows:
        for k in ('mode', 'sbar', 'bbar', 'entry_row', 'side', 'touch', 'last'):
            r[k] = int(r[k])
        for k in ('K', 'ask', 'stop', 'gmax'):
            r[k] = float(r[k])
    return rows


def pair_session(args):
    d, rows = args
    day = D.Day(d)
    out = []
    for s in rows:
        opp = -s['side']
        # the signal side again (a check against signals.csv)
        tr_s, _ = D.trade(day, 1, s['sbar'], s['bbar'], s['side'])
        tr_o, why = D.trade(day, 1, s['sbar'], s['bbar'], opp)
        rec = dict(d=d, sbar=s['sbar'], side=s['side'], sig_touch=s['touch'], sig_stop=int(s['how'] == 'stop'),
                   sig_how=s['how'], sig_stopfrac=s['stop'],
                   sig_check=int(tr_s is not None and tr_s['touch'] == s['touch'] and tr_s['how'] == s['how']
                                 and abs(tr_s['K'] - s['K']) < 1e-9 and abs(tr_s['ask'] - s['ask']) < 1e-9))
        if tr_o is None:
            rec.update(opp_ok=0, opp_why=why)
        else:
            # sensitivity: the signal side's stop fraction (outcome reads g >= 0.85 -> 0.76)
            c, _ = D.pick(day, s['sbar'] + 1, opp, day.sigma(s['sbar']), float(day.S[s['sbar']]))
            g_sens = 1.0 if s['stop'] == 0.76 else 0.0
            t2, h2, l2 = D.outcome(day, s['sbar'] + 1, c, g_sens)
            rec.update(opp_ok=1, opp_why='ok', opp_K=tr_o['K'], opp_ask=tr_o['ask'], opp_gmax=tr_o['gmax'],
                       opp_stopfrac=tr_o['stop'], opp_touch=tr_o['touch'], opp_stop=int(tr_o['how'] == 'stop'),
                       opp_how=tr_o['how'], opp_last=tr_o['last'],
                       sens_touch=t2, sens_stop=int(h2 == 'stop'), sens_how=h2, sens_last=l2)
        out.append(rec)
    return out


def base_session2(args):
    """dr_gce.base_session with the outcome (`how`) kept"""
    d, cells = args
    day = D.Day(d)
    res = {}
    for mode, m in cells:
        sbar = m - 1
        bbar = sbar if mode == 1 else sbar - 1
        for side in (1, -1):
            tr, _ = D.trade(day, mode, sbar, bbar, side)
            res[(mode, m, side)] = None if tr is None else (tr['touch'], tr['how'])
    return d, res


def boot(dv: np.ndarray, nv: np.ndarray):
    n = dv.size
    W = AL.weights_from(AL.block_draws(n, 20), n)
    return AL.pct_ci((W @ dv) / np.maximum(W @ nv, 1))


def main(procs: int = 4):
    print(D.G.selftest())
    sig = signals()
    days = D.sessions()
    by = {}
    for s in sig:
        by.setdefault(s['d'], []).append(s)
    with mp.get_context('spawn').Pool(procs) as p:
        pairs = [r for rs in p.map(pair_session, sorted(by.items())) for r in rs]
    keys = []
    for r in pairs:
        keys += [k for k in r if k not in keys]
    with open(OUT / 'gate2_pairs.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys, restval='')
        w.writeheader()
        w.writerows(pairs)
    # ---- baseline stop-first: rebuild Gate 1's table with the outcome, replay its draws
    cells = sorted({(s['mode'], s['entry_row']) for s in sig})
    with mp.get_context('spawn').Pool(procs) as p:
        tab = dict(p.map(base_session2, [(d, cells) for d in days]))
    rng = np.random.default_rng(D.SEED)
    tmeans, smeans = [], []
    for _ in range(D.TRIALS):
        hits, stops = [], []
        for s in sig:
            for _try in range(50):
                d = days[int(rng.integers(len(days)))]
                sd = 1 if rng.random() < 0.5 else -1
                v = tab[d].get((s['mode'], s['entry_row'], sd))
                if v is not None:
                    hits.append(v[0])
                    stops.append(int(v[1] == 'stop'))
                    break
        tmeans.append(np.mean(hits))
        smeans.append(np.mean(stops))
    tmeans, smeans = np.array(tmeans), np.array(smeans)
    base_mean = float(tmeans.mean())
    replay_ok = base_mean == GATE1_BASE_MEAN
    # ---- paired difference
    di = {d: i for i, d in enumerate(days)}
    P = [r for r in pairs if r['opp_ok']]

    def diff(sel, sens=False, dd=None):
        dd = dd or days
        idx = {d: i for i, d in enumerate(dd)}
        dv, nv = np.zeros(len(dd)), np.zeros(len(dd))
        for r in sel:
            if r['d'] in idx:
                dv[idx[r['d']]] += r['sig_touch'] - (r['sens_touch'] if sens else r['opp_touch'])
                nv[idx[r['d']]] += 1
        est = float(dv.sum() / nv.sum()) if nv.sum() else float('nan')
        ci = boot(dv, nv) if (nv.sum() and len(dd) >= 60) else (float('nan'), float('nan'))
        return dict(n=int(nv.sum()), D=est, ci=ci, sessions=len(dd))

    summ = dict(
        signals=len(sig), pairs=len(P), no_opposite={},
        sig_check_all=all(r['sig_check'] for r in pairs),
        sig_touch_all=sum(r['sig_touch'] for r in pairs) / len(pairs),
        sig_stop_all=sum(r['sig_stop'] for r in pairs) / len(pairs),
        sig_touch_paired=sum(r['sig_touch'] for r in P) / len(P),
        sig_stop_paired=sum(r['sig_stop'] for r in P) / len(P),
        opp_touch=sum(r['opp_touch'] for r in P) / len(P),
        opp_stop=sum(r['opp_stop'] for r in P) / len(P),
        opp_stop24=sum(r['opp_stopfrac'] == 0.76 for r in P),
        sens_touch=sum(r['sens_touch'] for r in P) / len(P),
        sens_stop=sum(r['sens_stop'] for r in P) / len(P),
        discordant=dict(sig_only=sum(r['sig_touch'] and not r['opp_touch'] for r in P),
                        opp_only=sum(r['opp_touch'] and not r['sig_touch'] for r in P),
                        both=sum(r['sig_touch'] and r['opp_touch'] for r in P)),
        baseline=dict(replay_touch_mean=base_mean, gate1_touch_mean=GATE1_BASE_MEAN, replay_exact=replay_ok,
                      stop_first_mean=float(smeans.mean()) if replay_ok else None,
                      stop_first_ci=AL.pct_ci(smeans) if replay_ok else None),
        pooled=diff(P), pooled_sens=diff(P, sens=True), years={}, years_sens={},
    )
    for r in pairs:
        if not r['opp_ok']:
            summ['no_opposite'][r['opp_why']] = summ['no_opposite'].get(r['opp_why'], 0) + 1
    for y in sorted({d[:4] for d in days}):
        dd = [d for d in days if d[:4] == y]
        summ['years'][y] = diff(P, dd=dd)
        summ['years_sens'][y] = diff(P, sens=True, dd=dd)
    summ['pass'] = bool(np.isfinite(summ['pooled']['ci'][0]) and summ['pooled']['ci'][0] > 0)
    (OUT / 'gate2_summary.json').write_text(json.dumps(summ, indent=1, default=float))
    print(json.dumps(summ, indent=1, default=float))


if __name__ == '__main__':
    main()
