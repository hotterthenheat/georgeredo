"""run_t4.py — Compass Final T4: hyp B's pre-registered touch pick (SPY 2-wide 25-delta credit spread at the boundary touch,
hold, no filter, mult 1.0), run ONCE (PREREG_COMPASS_FINAL.md 5, 6).

    POLARS_MAX_THREADS=2 python3 -I run_t4.py events   # the engine audit's scans and touches of the fresh sessions
    POLARS_MAX_THREADS=2 python3 -I run_t4.py trades   # hyp B engine.run('SPY') on them, the pick's rows, the settlement

EVENTS: `Compass engine audit/move_atr_flow/engine.py`'s own `session()` (imported unchanged; RAW = the fresh root, its
OUT never written) on every T4 session; only its scans and touches tables are kept (as its `run()` writes them: session
as text). TRADES: `Compass phase 2/hyp_b_boundary_theta/engine.py`'s own `run('SPY')` (RAW = the fresh root; its AUDIT
pointed at the tables above plus the audit's committed daily_SPY.parquet; its OUT at this study's folder), then
`analyze.py`'s de-duplication (one row a touch minute) and the pick's cell. SETTLEMENT as T1-T3 (run_t123.py): the legs
through AFTERHOURS.md's case_pnl; Robinhood's fees on the two opening legs and on the shares a case leaves.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import lib_final as LF  # noqa: E402
import run_t123 as R123  # noqa: E402

ROOT = R123.ROOT
AUD = ROOT / 't4_audit_tables'
HBO = ROOT / 't4_hypb_out'
MAF = REPO / 'research_notes' / 'Compass engine audit' / 'move_atr_flow'
HYPB = REPO / 'research_notes' / 'Compass phase 2' / 'hyp_b_boundary_theta'


def load(name: str, path: Path):
    os.environ['RAW'] = str(ROOT)
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def sessions() -> list[str]:
    import csv
    return [r['session'] for r in csv.DictReader(open(HERE / 'sessions_touch_d25.csv')) if r['excluded_by'] == '' and r['root'] == 'SPY']


def events() -> None:
    R123.assemble()
    ME = load('maf_engine', MAF / 'engine.py')
    ME.OUT = str(AUD)                                      # never its own out/
    AUD.mkdir(parents=True, exist_ok=True)
    import datetime as dt
    sc, to, skipped = [], [], []
    for d in sessions():
        try:
            r = ME.session('SPY', dt.date.fromisoformat(d))
        except Exception as ex:  # noqa: BLE001
            skipped.append((d, repr(ex)[:160]))
            continue
        if r is None:
            skipped.append((d, 'half day or no spot'))
            continue
        if r[0] is not None and r[0].height:
            sc.append(r[0].with_columns(pl.col('session').cast(pl.Utf8)))
        if r[1] is not None and r[1].height:
            to.append(r[1].with_columns(pl.col('session').cast(pl.Utf8)))
    pl.concat(sc, how='diagonal_relaxed').write_parquet(AUD / 'scans_SPY.parquet', compression='zstd')
    pl.concat(to, how='diagonal_relaxed').write_parquet(AUD / 'touches_SPY.parquet', compression='zstd')
    shutil.copyfile(MAF / 'out' / 'daily_SPY.parquet', AUD / 'daily_SPY.parquet')
    (HERE / 'out').mkdir(exist_ok=True)
    (HERE / 'out' / 't4_events.json').write_text(json.dumps({'sessions': len(sessions()), 'with_scans': len(sc), 'skipped': skipped}, indent=1))
    print(len(sc), 'sessions with scans;', len(skipped), 'skipped', skipped[:5])


def trades() -> None:
    import audit_lib as AL
    import afterhours as AH
    import fees_robinhood as FR
    HB = load('hypb_engine', HYPB / 'engine.py')
    HB.AUDIT = str(AUD)
    HB.OUT = str(HBO)
    HBO.mkdir(parents=True, exist_ok=True)
    os.environ['OUTNAME'] = 'trades'
    HB.run('SPY')
    X = pl.read_parquet(HBO / 'trades_SPY.parquet')
    T = X.filter(pl.col('test') == 'touch')
    # analyze.py's de-duplication, then the pick's cell (out/prereg.txt): SPY, width 2, rule d25, mult 1.0, all, hold
    T1 = T.sort('session', 'touch_side', 'e', 'mult', 'rule', 'width', 'm_scan').unique(subset=['session', 'touch_side', 'e', 'mult', 'rule', 'width'], keep='first')
    P = T1.filter((pl.col('rule') == 'd25') & (pl.col('width') == 2.0) & ((pl.col('mult') - 1.0).abs() < 1e-9)).sort('session', 'e', 'touch_side')
    cl = R123.closes()
    cal, _ = R123.calendar()
    nxt = {cal[i]: cal[i + 1] for i in range(len(cal) - 1)}
    rows = []
    for r in P.iter_rows(named=True):
        day = r['session']
        R = 'C' if r['structure'] == 'call' else 'P'
        legs = [(R, float(r['short_k']), 'short', 1), (R, float(r['long_k']), 'long', 1)]
        C = cl.get('SPY', day)[0]
        d, dbar = R123.decision_price('SPY', day)
        n = nxt.get(day)
        o = R123.open_0930('SPY', n) if n else None
        rh = FR.option_fee('SPY', float(r['short_bid']), 1, 'sell') + FR.option_fee('SPY', float(r['long_ask']), 1, 'buy')
        m = int(r['e']) + 570
        out = {'candidate': 'touch_d25', 'structure': r['structure'], 'name': 'SPY', 'date': day, 'entry': f'{m // 60:02d}:{m % 60:02d}',
               'inst': f"SPY {r['structure']} spread", 'legs': json.dumps(legs), 'credit': float(r['credit']), 'max_risk': float(r['max_risk']) / 100,
               'cost': float(r['max_risk']), 'official': C, 'decision_px': d, 'decision_bar': dbar, 'next_session': n, 'next_open_0930': o,
               'fee_open_rh': rh, 'm_scan': int(r['m_scan']), 'pnl_study_own': float(r['pnl_hold']), 'settle_study_own': float(r['settle'])}
        for cs in ('0', 'a', 'b', 'c'):
            res = AH.case_pnl(legs, float(r['credit']), C, d, o, cs, 0.0) if C is not None else None
            if res is None:
                out[f'gross_{cs}'] = out[f'pnl_{cs}'] = out[f'pnl_{cs}_old'] = out[f'shares_{cs}'] = None
                continue
            g = res[0] + AL.CONTRACTS * AL.FEE
            out[f'gross_{cs}'] = g
            out[f'shares_{cs}'] = res[2]
            out[f'pnl_{cs}'] = g - rh - R123.stock_rh(res[2], o)
            out[f'pnl_{cs}_old'] = g - 2 * 0.65                 # hyp B's $0.65 a leg to open, two legs
        rows.append(out)
    D = pl.DataFrame(rows, infer_schema_length=None)
    D.write_parquet(HERE / 'out' / 't4_trades.parquet')
    print(D.height, 'touch-pick trades;', 'no D', D.filter(pl.col('decision_px').is_null())['date'].n_unique(), 'no C', D.filter(pl.col('official').is_null())['date'].n_unique())


if __name__ == '__main__':
    {'events': events, 'trades': trades}[sys.argv[1]]()
