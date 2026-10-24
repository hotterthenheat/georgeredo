#!/usr/bin/env python3
"""tests for research_notes/Compass Final/forward/s17_forward.py: the roll calendar, one entry and its close-out, fees,
idempotency, and a failure that writes nothing. Temporary folders only."""
import datetime as dt
import sys
import tempfile
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass Final' / 'forward'))
import s17_forward as S  # noqa: E402


def bars(root: Path, sym: str, day: str, close: float) -> None:
    f = root / 'data' / 'underlying' / sym / f'{day}.parquet'
    f.parent.mkdir(parents=True, exist_ok=True)
    ts = [dt.datetime.fromisoformat(f'{day}T15:58:00'), dt.datetime.fromisoformat(f'{day}T15:59:00')]
    pl.DataFrame({'timestamp': ts, 'close': [close - 1.0, close]}).with_columns(pl.col('timestamp').dt.replace_time_zone('America/New_York')).write_parquet(f)


def fetch_factory(calls: list):
    def fetch(sym, day, expiry):
        calls.append((sym, day, expiry))
        rows = []
        for k in (95.0, 99.0, 100.0, 101.0):
            for r in ('C', 'P'):
                rows.append({'symbol': sym, 'expiration': expiry, 'strike': k, 'right': r, 'bid': 1.0 + (k - 95) / 10, 'ask': 1.1 + (k - 95) / 10, 'date': day})
        return rows
    return fetch


def test_roll_calendar():
    assert S.monthly_expiry(2026, 11) == '2026-11-20'
    assert S.monthly_expiry(2026, 12) == '2026-12-18'
    assert S.is_roll('2026-11-20') and not S.is_roll('2026-11-19') and not S.is_roll('2026-10-16')


def test_entry_close_and_idempotent():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        for sym in S.NAMES:
            bars(t, sym, '2026-11-20', 100.5)
            bars(t, sym, '2026-12-18', 98.0)
        calls = []
        r = S.run(['2026-11-19', '2026-11-20'], t, eod_fetch=fetch_factory(calls), store=t / 'store', folder=t / 'out')
        assert not r['failures'] and len(r['s17_entries']) == 2 and len(calls) == 2, r
        e = S.EF.read_rows(t / 'out' / 's17_entries.csv')
        assert all(float(x['atm_k']) == 100.0 and x['expiry'] == '2026-12-18' for x in e), e
        r = S.run(['2026-11-20', '2026-12-18'], t, eod_fetch=fetch_factory(calls), store=t / 'store', folder=t / 'out')
        tr = [x for x in S.EF.read_rows(t / 'out' / 's17_trades.csv') if x['structure'] == 'atm_put']
        assert len(tr) == 2, tr
        x = tr[0]
        bid = 1.5
        fee = S.FR.option_fee(x['name'], bid, 1, 'sell')
        assert abs(float(x['pnl_rh']) - ((bid - 2.0) * 100 - fee)) < 1e-9 and abs(float(x['pnl_s17']) - ((bid - 2.0) * 100 - 1.40)) < 1e-9
        n_e, n_t = len(S.EF.read_rows(t / 'out' / 's17_entries.csv')), len(S.EF.read_rows(t / 'out' / 's17_trades.csv'))
        S.run(['2026-11-20', '2026-12-18'], t, eod_fetch=fetch_factory(calls), store=t / 'store', folder=t / 'out')
        assert n_e == len(S.EF.read_rows(t / 'out' / 's17_entries.csv')) and n_t == len(S.EF.read_rows(t / 'out' / 's17_trades.csv'))


def test_missing_bars_fail_and_write_nothing():
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        r = S.run(['2026-11-20'], t, eod_fetch=fetch_factory([]), store=t / 'store', folder=t / 'out')
        assert r['failures'] and not S.EF.read_rows(t / 'out' / 's17_entries.csv')


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok   ', name)
    print('\nall passed')
