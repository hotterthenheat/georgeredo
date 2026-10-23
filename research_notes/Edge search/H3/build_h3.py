#!/usr/bin/env python3
"""
build_h3.py — builds H3's trades from the stored files and runs the pre-registered statistic (PREREG_H3.md §3–§5, commit
001a136). Once per set: the exploration screen, then (only after a pass, and after its fetch) the holdout test.

    PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=4 python3 -I -B build_h3.py expl
    PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=4 python3 -I -B build_h3.py hold    # refused before a screen pass

Writes out/trades_<set>.csv, out/screen_<set>.json (expl) or out/test_<set>.json (hold), out/stages_<set>.json.
"""
from __future__ import annotations

import collections
import json
import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h3common as H  # noqa: E402

D, AL = H.D, H.AL
BLOCK, B = 20, 2000
BONF = {'m2': 0.05 / 2, 'm7': 0.05 / 7}


def boot(sess: list[str], tr: pl.DataFrame, col: str, W20: np.ndarray) -> dict:
    ix = {s: i for i, s in enumerate(sess)}
    n = len(sess)
    S, N = np.zeros(n), np.zeros(n)
    for r, v in zip(tr['R'].to_list(), tr[col].to_list()):
        S[ix[r]] += v
        N[ix[r]] += 1
    out = dict(trades=int(N.sum()), sessions=n, sessions_traded=int((N > 0).sum()))
    if N.sum() == 0:
        return out
    out['mean'] = float(S.sum() / N.sum())
    mt = (W20 @ S) / np.maximum(W20 @ N, 1e-12)
    mt = np.where((W20 @ N) > 0, mt, np.nan)
    out['ci95_b20'] = AL.pct_ci(mt)
    fin = mt[np.isfinite(mt)]
    for k, a in BONF.items():
        out[f'ci_bonf_{k}'] = (float(np.percentile(fin, 100 * a / 2)), float(np.percentile(fin, 100 * (1 - a / 2))))
    if col == 'pnl':
        ss = AL.session_stats(S, N)
        out['session_stats'] = {k: v for k, v in ss.items() if k != 'acf'}
    return out


def main(split: str):
    if split == 'hold':
        sc = H.OUT / 'screen_expl.json'
        if not sc.exists() or not json.loads(sc.read_text()).get('screen_pass'):
            raise SystemExit('the holdout is built only after the exploration screen passed')
    done = [json.loads(x) for x in (H.STORE / f'_events_{split}.ndjson').read_text().splitlines()]
    budget = json.loads((H.STORE / f'_budget_{split}.json').read_text())
    stages = collections.Counter(r['stage'] for r in done)
    formed = [r for r in done if r['stage'] == 'formed']
    bars = {s: D.Bars(df) for s, df in D.load_bars(sorted({r['ticker'] for r in formed})).items()}

    rows, bstage = [], collections.Counter()
    for r in formed:
        sym, P, R, exp = r['ticker'], r['P'], r['R'], r['expiry']
        xp = H.read(H.find_all(sym, P)).filter(pl.col('expiration') == exp)
        cP, cR = bars[sym].c(P), bars[sym].c(R)
        e = H.entry(xp, cP)
        assert e['status'] == 'formed', (sym, P, e['status'])
        pr = H.path(sym, R, exp)
        if pr.exists():
            xr = H.read(pr)
        elif pr.with_name(pr.name + '.empty').exists():
            xr = None
        else:
            raise SystemExit(f'exit file missing for a formed event {sym} {R}')
        t = H.trade(e, xr, cP, cR)
        bstage[t['how']] += 1
        rows.append(dict(ticker=sym, report_date=r['report_date'], report_time=r['report_time'], P=P, R=R, expiry=exp,
                         closeP=cP, closeR=cR, K0=e['K0'], IM=e['IM'], F=e['F'], Kcs=e['Kcs'], Kcl=e['Kcl'], Kps=e['Kps'],
                         Kpl=e['Kpl'], cs_bid=e['cs_bid'], ps_bid=e['ps_bid'], cl_ask=e['cl_ask'], pl_ask=e['pl_ask'],
                         credit=e['credit'], W=e['W'], fly=e['fly'], exit_file='empty' if xr is None else 'stored',
                         exit_cost=t.get('exit_cost'), x_cs=t.get('x_cs'), x_ps=t.get('x_ps'), x_cl=t.get('x_cl'),
                         x_pl=t.get('x_pl'), fallbacks=t['fallbacks'], how=t['how'], pnl=t['pnl'], pct_risk=t['pct_risk']))
    tr = pl.DataFrame(rows, infer_schema_length=None).sort('R', 'ticker')

    # tiers: (name, month of P), on the 10th and 20th of the 20 full sessions before the month's first session
    tiers = {}
    for k in sorted({(t, p[:7]) for t, p in zip(tr['ticker'].to_list(), tr['P'].to_list())}):
        td = D.tier_days(k[1] + '-15')
        fs = [H.find_all(k[0], d) for d in td] if td else []
        if not fs or any(f is None for f in fs):
            tiers[k] = 'U'
            continue
        v, s = D.tier_measure([H.read(f) for f in fs])
        tiers[k] = D.tier_of(v, s)
    tr = tr.with_columns(pl.Series('tier', [tiers[(t, p[:7])] for t, p in zip(tr['ticker'].to_list(), tr['P'].to_list())]),
                         ((pl.col('closeR') / pl.col('closeP') - 1).abs() * pl.col('closeP') / pl.col('IM')).alias('move_im'),
                         (pl.col('credit') / pl.col('IM')).alias('credit_im'), (pl.col('exit_cost') / pl.col('IM')).alias('exit_im'),
                         pl.col('R').str.slice(0, 4).alias('year'))
    H.OUT.mkdir(parents=True, exist_ok=True)
    tr.write_csv(H.OUT / f'trades_{split}.csv')

    sess = D.sessions_in(H.WIN_FROM, H.WIN_TO)
    W20 = AL.weights_from(AL.block_draws(len(sess), BLOCK), len(sess))
    main_ = boot(sess, tr, 'pnl', W20)
    res = dict(prereg_commit=H.PREREG_COMMIT, split=split, budget=budget, stages=dict(stages), build=dict(bstage),
               pnl=main_, pct_risk=boot(sess, tr, 'pct_risk', W20))
    p = tr['pnl'].to_numpy()
    res['describe'] = dict(trades=int(p.size), win_rate=float((p > 0).mean()), worst=float(p.min()), best=float(p.max()),
                           p1=float(np.percentile(p, 1)), p5=float(np.percentile(p, 5)), median=float(np.median(p)),
                           p95=float(np.percentile(p, 95)), mean_credit=float(tr['credit'].mean()) * 100,
                           mean_max_risk=float(((tr['W'] - tr['credit']) * 100).mean()),
                           median_credit_im=float(tr['credit_im'].median()), median_exit_im=float(tr['exit_im'].drop_nulls().median()),
                           median_move_im=float(tr['move_im'].drop_nulls().median()),
                           share_move_beyond_short=float((tr['move_im'].drop_nulls() > 0.5).mean()),
                           fallback_trades=int((tr['fallbacks'] > 0).sum()), fallback_legs=int(tr['fallbacks'].sum()),
                           exit_file_empty=int((tr['exit_file'] == 'empty').sum()), fly_shaped=int(tr['fly'].sum()))
    cuts = {}
    for col in ('year', 'tier', 'report_time', 'fly'):
        for v in sorted(tr[col].unique().to_list()):
            sub = tr.filter(pl.col(col) == v)
            b = boot(sess, sub, 'pnl', W20)
            q = boot(sess, sub, 'pct_risk', W20)
            cuts[f'{col}={v}'] = dict(trades=b['trades'], mean=b.get('mean'), ci95_b20=b.get('ci95_b20'),
                                      pct_risk_mean=q.get('mean'), win_rate=float((sub['pnl'] > 0).mean()))
    res['cuts'] = cuts
    lo = main_.get('ci95_b20', (float('nan'),))[0]
    ok = main_.get('mean', float('nan')) > 0 and lo > 0 and main_['sessions'] >= 60
    if split == 'expl':
        res['screen_pass'] = bool(ok)
        H.jdump(res, H.OUT / 'screen_expl.json')
    else:
        res['holdout_pass'] = bool(ok)
        res['edge_bonferroni_m2'] = bool(ok and main_['ci_bonf_m2'][0] > 0)
        res['edge_bonferroni_m7'] = bool(ok and main_['ci_bonf_m7'][0] > 0)
        H.jdump(res, H.OUT / 'test_hold.json')
    print(json.dumps(dict(split=split, trades=main_['trades'], mean=main_.get('mean'), ci=main_.get('ci95_b20'),
                          passed=bool(ok)), default=str))


if __name__ == '__main__':
    main(sys.argv[1])
