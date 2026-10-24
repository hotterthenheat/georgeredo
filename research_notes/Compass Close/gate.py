"""gate.py — Compass Close's gate, run once (PREREG_COMPASS_CLOSE.md section 4) on the GATE sample (odd months), and the
same figures on the PREVIOUSLY READ span (no verdict there). Never reads a P&L-sample (even-month) session.

    python3 -I gate.py      → out/gate.json, out/gate_sessions.csv, out/prev_sessions.csv (GATE_REPORT.md is written from gate.json)
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
from collections import Counter
from pathlib import Path

os.environ.setdefault('POLARS_MAX_THREADS', '1')
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as A  # noqa: E402
import close_lib as L  # noqa: E402

OUT = HERE / 'out'


def ratio_ci(num: np.ndarray, den: np.ndarray) -> tuple[float, float, float]:
    """ratio of means with the pinned 20-session moving-block interval (audit_lib draws, 2,000, house seed)"""
    n = num.size
    r = float(num.mean() / den.mean())
    if n < 60:
        return r, float('nan'), float('nan')
    W = A.weights_from(A.block_draws(n, 20), n)
    lo, hi = A.pct_ci((W @ num) / (W @ den))
    return r, lo, hi


def lifecycle_sets() -> tuple[set, set]:
    ent, ex = set(), set()
    for n in ('SPY', 'QQQ', 'IWM'):
        for run in ('dgrid', 'dbest', 'dholdout'):
            p = pl.read_parquet(L.SP / 'lifecycle' / 'runs' / run / n / 'positions.parquet',
                                columns=['session', 'expiration', 'skip']).filter(pl.col('skip').is_null())
            ent |= {d.isoformat() for d in p['session'].to_list()}
            ex |= {d.isoformat() for d in p['expiration'].to_list()}
    return ent, ex


def figures(rows: list[dict]) -> dict:
    """every gate figure on a list of session rows (calendar order)"""
    bk = [L.books(r) for r in rows]
    why = Counter(b['primary'].get('why') for b in bk if not b['primary']['trade'])
    tr = [(r, b['primary']) for r, b in zip(rows, bk) if b['primary']['trade']]
    mv = np.array([p['move'] for _, p in tr])
    sa = np.array([p['str_ask'] for _, p in tr])
    sm = np.array([p['str_mid'] for _, p in tr])
    out = {'sessions': len(rows), 'trades': len(tr), 'no_trade': dict(why)}
    if not tr:
        return out
    r, lo, hi = ratio_ci(mv, sa)
    rm, lom, him = ratio_ci(mv, sm)
    per = mv / sa
    out.update(R_ask=r, R_ask_ci=[lo, hi], R_mid=rm, R_mid_ci=[lom, him], mean_ratio=float(per.mean()),
               median_ratio=float(np.median(per)), share_move_gt_str=float((mv > sa).mean()),
               mean_move=float(mv.mean()), mean_str_ask=float(sa.mean()), mean_str_mid=float(sm.mean()),
               ok10=int(sum(p['ok10'] for _, p in tr)),
               set_flag=[r['day'] for r in rows if r['SET'] is not None and r['S1600'] is not None and abs(r['SET'] - r['S1600']) > 0.5])
    by = {}
    for key, f in (('year', lambda r: str(r['year'])), ('row', lambda r: r['g2'] if r['g2'] in ('Mon', 'Wed', 'Fri', 'EOM') else 'other'),
                   ('weekday_incl', lambda r: L.dt.date.fromisoformat(r['day']).strftime('%a'))):
        g = {}
        for (rw, p) in tr:
            g.setdefault(f(rw), []).append(p)
        by[key] = {k: {'n': len(v), 'R_ask': float(np.mean([p['move'] for p in v]) / np.mean([p['str_ask'] for p in v]))}
                   for k, v in sorted(g.items())}
    out['by'] = by
    st = [(rw, b['strangle']) for rw, b in zip(rows, bk)]
    sv = [p for _, p in st if p['trade']]
    if sv:
        c, clo, chi = ratio_ci(np.array([p['move'] for p in sv]), np.array([p['str_ask'] for p in sv]))
        out['control'] = {'n': len(sv), 'R_ask': c, 'ci': [clo, chi], 'mean_intrinsic': float(np.mean([p['move'] for p in sv])),
                          'mean_prem_ask': float(np.mean([p['str_ask'] for p in sv])),
                          'no_trade': dict(Counter(p.get('why') for _, p in st if not p['trade']))}
    out['_tr'] = tr
    return out


def verdict(g: dict) -> dict:
    g1 = g['R_ask'] >= 1.05 and g['R_ask_ci'][0] > 1.00
    years = {y: v['R_ask'] > 1.00 for y, v in g['by']['year'].items()}
    rows = {k: g['by']['row'][k]['R_ask'] > 1.00 for k in ('Mon', 'Wed', 'Fri', 'EOM') if k in g['by']['row']}
    g2y = sum(years.values()) >= 4
    g2w = all(rows.values())
    ctrl = g.get('control', {}).get('R_ask', float('nan'))
    reading = 'general' if ctrl > 1.00 else ('ATM-only (possibly a pin or microstructure effect)' if g['R_ask'] > 1.00 else
                                            'neither: the straddle is not cheap either')
    return {'G1': g1, 'G2_years': g2y, 'years_above_1': int(sum(years.values())), 'G2_weekdays': g2w,
            'rows_judged': rows, 'EOM_in_sample': 'EOM' in g['by']['row'], 'G2': g2y and g2w, 'PASS': g1 and g2y and g2w,
            'control_reading': reading}


def pnl_summary(rows: list[dict]) -> dict:
    """the primary's P&L, previously read only (descriptive)"""
    bk = [L.books(r)['primary'] for r in rows]
    S = np.array([b['ret'] if b['trade'] else 0.0 for b in bk])
    N = np.array([1 if b['trade'] else 0 for b in bk])
    D = np.array([b['pnl'] for b in bk if b['trade']])
    st = A.session_stats(S, N, blocks=(1, 20))
    return {'trades': int(N.sum()), 'mean_ret': st.get('mean_trade'), 'ci_b20': st.get('ci_trade_b20'),
            'total_usd': float(D.sum()), 'mean_usd': float(D.mean()), 'win_rate': float((D > 0).mean()),
            'median_usd': float(np.median(D))}


def table(rows: list[dict], tr: list) -> pl.DataFrame:
    return pl.DataFrame([{'day': rw['day'], 'g2': rw['g2'], 'S1555': rw['15:55']['S'], 'K': p['K'], 'str_ask': p['str_ask'],
                          'str_mid': p['str_mid'], 'SET': rw['SET'], 'move': p['move'], 'pnl_usd': p['pnl'], 'ret': p['ret']}
                         for rw, p in tr])


def main() -> int:
    OUT.mkdir(exist_ok=True)
    gate_days = [s['session'] for s in L.new_sessions() if s['sample'] == 'gate']
    assert len(gate_days) == 236
    assert all(int(d[5:7]) % 2 == 1 for d in gate_days)
    rows = [L.session_row(d, 'new') for d in gate_days]
    g = figures(rows)
    v = verdict(g)
    ent, ex = lifecycle_sets()
    sens = {}
    for name, S in (('entry', ent), ('expiry', ex)):
        keep = [r for r in rows if r['day'] not in S]
        f = figures(keep)
        sens[name] = {'overlap': sum(r['day'] in S for r in rows), 'sessions_left': len(keep), 'trades': f['trades'],
                      'R_ask': f.get('R_ask'), 'not_overlapping': [r['day'] for r in keep]}
    table(rows, g.pop('_tr')).write_csv(OUT / 'gate_sessions.csv')
    pdays = L.prev_sessions()
    prow = [L.session_row(d, 'prev') for d in pdays]
    pg = figures(prow)
    table(prow, pg.pop('_tr')).write_csv(OUT / 'prev_sessions.csv')
    pv = verdict(pg)
    res = {'gate': g, 'verdict': v, 'lifecycle_sensitivity': sens,
           'previously_read': {'span': [pdays[0], pdays[-1]], 'figures': pg, 'would_be': pv, 'primary_pnl': pnl_summary(prow)}}
    (OUT / 'gate.json').write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps({'R_ask': g['R_ask'], 'ci': g['R_ask_ci'], 'R_mid': g['R_mid'], 'verdict': v,
                      'prev_R_ask': pg['R_ask'], 'prev_ci': pg['R_ask_ci']}, indent=1, default=str))
    return 0


if __name__ == '__main__':
    sys.exit(main())
