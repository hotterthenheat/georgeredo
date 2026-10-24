"""run_t7.py — Compass Final T7: Compass H1 (the overnight reversal of the late-day move) on QQQ's unread span, run ONCE
(PREREG_COMPASS_FINAL.md 5, 6). No fetch: the stored QQQ bars, Theta's EOD and H1's dividend table.

    POLARS_MAX_THREADS=2 python3 -I run_t7.py

`research_notes/Compass H1/run_h1.py` is imported and its `build()` run unchanged, with four constants set (section 5):
NAMES = ('QQQ',), FIRST = {'QQQ': '2025-10-13'}, LAST = '2026-10-22', and the span's two half days (2025-11-28, 2025-12-24,
from the dataset calendar) added to HALF_DAYS. Robinhood's stock fees replace H1's $0.01 a share (a fee-only auction cost):
a long buys at C (CAT) and sells at O (SEC fee, TAF, CAT); a short sells at C (SEC fee, TAF, CAT) and buys at O (CAT).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts'))


def main() -> None:
    import fees_robinhood as FR
    spec = importlib.util.spec_from_file_location('run_h1', REPO / 'research_notes' / 'Compass H1' / 'run_h1.py')
    H = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(H)
    H.NAMES = ('QQQ',)
    H.FIRST = {'QQQ': '2025-10-13'}
    H.LAST = '2026-10-22'
    H.HALF_DAYS = frozenset(set(H.HALF_DAYS) | {'2025-11-28', '2025-12-24'})
    t = H.build()
    t.write_parquet(HERE / 'out' / 't7_sessions.parquet')
    x = t.filter((pl.col('excluded') == '') & (pl.col('side') != 0))
    rows = []
    for r in x.iter_rows(named=True):
        C, O, side = r['C'], r['O'], r['side']
        if side == 1:
            fee = FR.stock_fee(C, 100, 'buy') + FR.stock_fee(O, 100, 'sell')
        else:
            fee = FR.stock_fee(C, 100, 'sell') + FR.stock_fee(O, 100, 'buy')
        net = r['gross'] + r['dividend'] - r['borrow'] - fee
        rows.append({'date': r['day'], 'entry': '16:00', 'inst': 'QQQ long' if side == 1 else 'QQQ short', 'side': side, 'C': C, 'P15': r['P15'],
                     'O': O, 'next': r['next'], 'gross': r['gross'], 'dividend': r['dividend'], 'borrow': r['borrow'], 'fee_rh': fee,
                     'cost': C * 100, 'pnl': net, 'pnl_old': r['net_1x'], 'flagged': r['flagged']})
    pl.DataFrame(rows).write_parquet(HERE / 'out' / 't7_trades.parquet')
    ex = t.filter(pl.col('excluded') != '')
    print(len(rows), 'trades;', t.filter(pl.col('side') == 0).height, 'flat;', ex.height, 'excluded', ex['excluded'].value_counts().to_dicts())


if __name__ == '__main__':
    main()
