"""
Tests for the edge-search H5 and H6 forward tests (research_notes/Edge search/H5_H6/edge_forward.py and step 8 of
scripts/daily_forward.py), against PREREG_H5.md and PREREG_H6.md (e114e30).

Run:  python3 -I tests/test_edge_forward.py            (plain: runs every test_* below)
      python3 -I -m pytest tests/test_edge_forward.py -q

What they prove: the N, starts, fees and sizes in the code are the pre-registrations' and power_h5_h6.py reproduces both N
from the committed inputs; H5's package on a hand-built session (synthetic quotes, no historical day) equals the row
worked out by hand to the cent, a missing exit quote is valued by the stated rule and flagged, a SPY bid of 0 is a
no-trade session, a missing file fails loudly and writes nothing, nothing is computed before 2026-10-23; the append is
idempotent; H6's calendar (entry and exit sessions), expiration, strikes, fills, fees and P&L on a fake end-of-day
source, each answer asked once and kept as answered, its failures loud; the months counted in order; no verdict before N,
the verdict at exactly N on the first N, written once; the terminal path asks /option/history/eod on 127.0.0.1 with no
key; the daily job runs step 8 after the tracker, once, and a step-8 failure keeps the tracker's append.

H7 and H9 (research_notes/Edge search/H7_H8_H9/forward_h7_h9.py, against FORWARD_RULE_H7.md fcc1f4d and PREREG_H9.md
edca472): the N, costs, starts and seed in the code are the rules' and power_h7_forward.py reproduces N; the forward rule
was committed alone; the FOMC calendar lookup (the macro calendar against the committed list, a disagreement loud, the
calendar's and the holidays' ends loud); golden rows from made-up quotes (H7 at the 13:58 close, H9 at the next 09:30 open,
1× and 2×); a missing 13:58 bar excludes the meeting, any other missing input fails loudly and writes nothing, an official
close not from UW is refused; dividends paid by ex-date, never assumed past the table's complete_through or without an
amount; idempotent append; no verdict before N, the verdict at exactly N on the first N, written once; the checkpoint every
8 trades labelled no verdict; the daily job asks a half day's close and bars for H9 (terminal) and says so on the SDK.
"""
from __future__ import annotations

import datetime as dt
import gzip
import http.server
import json
import math
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EDGE = REPO / 'research_notes' / 'Edge search' / 'H5_H6'
sys.path.insert(0, str(EDGE))
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'tests'))

import polars as pl  # noqa: E402

import edge_forward as EF  # noqa: E402
import paper_tracker as T  # noqa: E402

SKIPPED = []
DAY = '2026-10-26'          # a full session after the start; every quote below is made up for the test


def skip(why: str):
    SKIPPED.append(why)
    print(f'SKIP  {why}')


# ---- the rules ----------------------------------------------------------------------------------------------------------------------------

def test_the_rules_in_the_code_are_the_preregs():
    p5 = (EDGE / 'PREREG_H5.md').read_text()
    p6 = (EDGE / 'PREREG_H6.md').read_text()
    assert EF.N_RULE == {'H5': 1326, 'H6': 449}
    assert '**N = 1,326 counted sessions**' in p5 and '**N = 449 counted months — 898 spreads' in p6
    assert EF.H5_START == '2026-10-23' and 'from Friday 2026-10-23' in p5
    assert EF.first_full_session(EF.H6_START_MONTH) == '2026-11-02' and '(Monday 2026-11-02)' in p6
    assert (EF.FEE_ETF, EF.FEE_SPXW_LT1, EF.FEE_SPXW_GE1) == (0.68748, 1.18748, 1.27748)
    assert '**$0.68748**' in p5 and '**$1.18748**' in p5 and '**$1.27748**' in p5 and '4 × **$0.68748**' in p6
    assert (EF.H5_SPY_N, EF.H5_SPXW_N, EF.H5_ENTRY_J, EF.H5_EXIT_J) == (10, 1, 360, 388)
    assert (EF.H6_SHORT_D, EF.H6_LONG_D, EF.H6_DTE_MIN, EF.H6_DTE_MAX, EF.H6_EXIT_BEFORE) == (0.30, 0.15, 30, 45, 21)
    assert EF.BLOCK == {'H5': 20, 'H6': 3}
    # the pre-registrations were committed together, alone, in the commit the code names
    try:
        names = subprocess.run(['git', '-C', str(REPO), 'show', '--name-only', '--format=', EF.PREREG_COMMIT],
                               capture_output=True, text=True, check=True).stdout.splitlines()
    except Exception as e:  # noqa: BLE001
        skip(f'prereg commit: git cannot show {EF.PREREG_COMMIT} here ({type(e).__name__})')
        return
    names = [x for x in names if x.strip()]
    assert sorted(names) == ['research_notes/Edge search/H5_H6/PREREG_H5.md', 'research_notes/Edge search/H5_H6/PREREG_H6.md'], names


def test_the_power_script_reproduces_both_N():
    import power_h5_h6 as PW
    h5 = PW.h5()
    assert h5['N'] == EF.N_RULE['H5'] and abs(h5['sigma_bps'] - 12.997) < 1e-3
    assert h5['periods']['selection']['mapped_mid_bps'] < 0 and h5['periods']['development']['mapped_mid_bps'] < 0
    try:
        h6 = PW.h6()
    except Exception as e:  # noqa: BLE001
        skip(f'power H6: S17\'s committed cycles are not readable here ({type(e).__name__})')
        return
    assert h6['N_months'] == EF.N_RULE['H6'] and h6['N_spreads'] == 898 and h6['cycles_common'] == 166
    js = json.loads((EDGE / 'power_h5_h6.json').read_text())
    assert js['H5']['N'] == EF.N_RULE['H5'] and js['H6']['N_months'] == EF.N_RULE['H6']


# ---- H5 -----------------------------------------------------------------------------------------------------------------------------------

NY = 'America/New_York'


def _ts(day: str, hhmm: str) -> dt.datetime:
    return dt.datetime.fromisoformat(f'{day}T{hhmm}:00')


def _chain_file(path: Path, day: str, quotes: dict):
    """quotes: {(hhmm, strike, 'CALL'|'PUT'): (bid, ask)} → the stored chain layout"""
    rows = [(_ts(day, m), k, r, b, a, 50, 60) for (m, k, r), (b, a) in sorted(quotes.items())]
    df = pl.DataFrame(rows, schema={'timestamp': pl.Datetime('ms'), 'strike': pl.Float64, 'right': pl.Utf8, 'bid': pl.Float64,
                                    'ask': pl.Float64, 'bid_size': pl.Int32, 'ask_size': pl.Int32}, orient='row')
    df = df.with_columns(pl.col('timestamp').dt.replace_time_zone(NY), ((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)


def h5_layout(root: Path, day: str = DAY, drop: tuple = (), spy_put_bid_30: float = 0.88):
    spy = {}
    for k in (699.0, 700.0, 701.0):
        spy[('15:30', k, 'CALL')] = {699.0: (2.00, 2.02), 700.0: (1.20, 1.21), 701.0: (0.60, 0.61)}[k]
        spy[('15:30', k, 'PUT')] = {699.0: (0.40, 0.41), 700.0: (spy_put_bid_30, 0.89), 701.0: (1.30, 1.32)}[k]
        spy[('15:58', k, 'CALL')] = {699.0: (1.30, 1.32), 700.0: (0.40, 0.41), 701.0: (0.02, 0.03)}[k]
        spy[('15:58', k, 'PUT')] = {699.0: (0.01, 0.02), 700.0: (0.05, 0.06), 701.0: (0.60, 0.62)}[k]
    for key in drop:
        spy.pop(key, None)
    spx = {}
    for k in (7015.0, 7020.0, 7025.0):
        spx[('15:30', k, 'CALL')] = {7015.0: (15.00, 15.20), 7020.0: (11.90, 12.10), 7025.0: (9.10, 9.30)}[k]
        spx[('15:30', k, 'PUT')] = {7015.0: (9.00, 9.20), 7020.0: (11.40, 11.60), 7025.0: (14.20, 14.40)}[k]
        spx[('15:58', k, 'CALL')] = {7015.0: (8.80, 9.00), 7020.0: (4.00, 4.20), 7025.0: (0.70, 0.80)}[k]
        spx[('15:58', k, 'PUT')] = {7015.0: (0.05, 0.10), 7020.0: (0.30, 0.40), 7025.0: (1.70, 1.90)}[k]
    if 'SPXW' not in drop:
        _chain_file(root / f'data_full/chains/SPXW/{day}.parquet', day, spx)
    _chain_file(root / f'data_full/chains/SPY/{day}.parquet', day, spy)
    bars = pl.DataFrame([(_ts(day, m), c, c, c, c, 1000, 10, c) for m, c in (('15:29', 700.30), ('15:57', 701.00))],
                        schema={'timestamp': pl.Datetime('ms'), 'open': pl.Float64, 'high': pl.Float64, 'low': pl.Float64, 'close': pl.Float64,
                                'volume': pl.Int64, 'count': pl.Int64, 'vwap': pl.Float64}, orient='row').with_columns(pl.col('timestamp').dt.replace_time_zone(NY))
    (root / 'data/underlying/SPY').mkdir(parents=True, exist_ok=True)
    bars.write_parquet(root / f'data/underlying/SPY/{day}.parquet')
    pr = pl.DataFrame([(_ts(day, m), p) for m, p in (('15:30', 7020.40), ('15:58', 7030.00))],
                      schema={'timestamp': pl.Datetime('ms'), 'price': pl.Float64}, orient='row').with_columns(pl.col('timestamp').dt.replace_time_zone(NY))
    (root / 'data/index/SPX').mkdir(parents=True, exist_ok=True)
    pr.write_parquet(root / f'data/index/SPX/{day}.parquet')


def test_h5_golden_row_worked_by_hand():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        h5_layout(root)
        r = EF.h5_session(DAY, root)
        # 15:30: SPY spot 700.30 (the 15:29 bar) → 700; SPX 7020.40 → 7020. Sell 10 × (1.20 + 0.88), buy 1 × (12.10 + 11.60);
        # 15:58: buy back 10 × (0.41 + 0.06), sell 1 × (4.00 + 0.30). Gross 100 × (10 × 1.61 − 19.40) = −330.00.
        # Fees: 40 × 0.68748 = 27.4992; SPXW 12.10, 11.60, 4.00 at 1.27748 and 0.30 at 1.18748 = 5.01992. P&L −362.51912.
        assert (r['k_spy'], r['k_spxw'], r['traded'], r['N']) == (700.0, 7020.0, 1, 1), r
        assert (r['spy_spot'], r['spx_spot']) == (700.30, 7020.40)
        assert abs(r['gross'] - (-330.0)) < 1e-9 and abs(r['fees'] - 32.51912) < 1e-9 and abs(r['pnl'] - (-362.51912)) < 1e-9, r
        assert r['S'] == r['pnl'] and r['exit_flags'] == ''
        # at the mids, for reading: 100 × (10 × (1.205 + 0.885 − 0.405 − 0.055) − (12.00 + 11.50 − 4.10 − 0.35)) = −275.00
        assert abs(r['pnl_mid'] - (-275.0)) < 1e-9
        assert (r['spy_c_bid'], r['spy_p_bid'], r['spxw_c_ask'], r['spxw_p_ask']) == (1.20, 0.88, 12.10, 11.60)
        assert (r['spy_c_ask_x'], r['spy_p_ask_x'], r['spxw_c_bid_x'], r['spxw_p_bid_x']) == (0.41, 0.06, 4.00, 0.30)


def test_h5_missing_exit_quote_is_valued_by_the_rule_and_flagged():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        h5_layout(root, drop=(('15:58', 700.0, 'PUT'),))
        r = EF.h5_session(DAY, root)
        # the SPY 700 put to buy back: intrinsic on the 15:57 bar (701.00) is 0, plus its 15:30 spread 0.01 → 0.01
        assert abs(r['gross'] - 100.0 * (10 * (1.20 + 0.88 - 0.41 - 0.01) - 19.40)) < 1e-9, r
        assert 'SPY put: no 15:58 ask' in r['exit_flags'] and r['pnl_mid'] is None and r['spy_p_ask_x'] is None


def test_h5_a_spy_bid_of_zero_is_a_no_trade_session():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        h5_layout(root, spy_put_bid_30=0.0)
        r = EF.h5_session(DAY, root)
        assert r['traded'] == 0 and r['N'] == 0 and r['S'] == 0.0 and 'bid of 0' in r['reason'] and r['pnl'] is None


def official_none(nm, d):
    return None


def test_h5_missing_data_fails_loudly_writes_nothing_and_nothing_before_the_start():
    with tempfile.TemporaryDirectory() as d:
        root, out = Path(d) / 'pq', Path(d) / 'fwd'
        h5_layout(root, drop=('SPXW',))
        res = EF.run([DAY], root, official_none, folder=out)
        assert res['h5_added'] == [] and len(res['failures']) == 1 and res['failures'][0].startswith(f'{DAY} h5-inputs:'), res
        assert 'SPXW' in res['failures'][0] and not (out / 'h5_sessions.csv').exists()
        assert 'no verdict' in (out / 'EDGE_FORWARD_REPORT.md').read_text()
        h5_layout(root, day='2026-10-22')                     # a whole session before the forward start: never computed
        res = EF.run(['2026-10-22'], root, official_none, folder=out)
        assert res == {'h5_added': [], 'h6_entries': [], 'h6_trades': [], 'failures': [], 'calls': 0} and not (out / 'h5_sessions.csv').exists()


def test_h5_the_append_is_idempotent():
    with tempfile.TemporaryDirectory() as d:
        root, out = Path(d) / 'pq', Path(d) / 'fwd'
        h5_layout(root)
        res = EF.run([DAY], root, official_none, folder=out)
        assert res['h5_added'] == [DAY] and not res['failures']
        f = out / 'h5_sessions.csv'
        txt, mt = f.read_text(), f.stat().st_mtime_ns
        res = EF.run([DAY], root, official_none, folder=out)
        assert res['h5_added'] == [] and f.read_text() == txt and f.stat().st_mtime_ns == mt
        rows = EF.read_rows(f)
        assert len(rows) == 1 and abs(float(rows[0]['pnl']) - (-362.51912)) < 1e-9
        assert '| 1 / 1,326 | 1 |' in (out / 'EDGE_FORWARD_REPORT.md').read_text()
        with open(f, 'a') as g:                               # a hand-made duplicate is refused on the next append
            g.write(txt.splitlines()[1] + '\n')
        try:
            EF.append_rows(f, EF.H5_COLS, [dict(rows[0], day='2026-10-27')], ('day',))
            raise AssertionError('a duplicated key went unnoticed')
        except RuntimeError as e:
            assert 'twice' in str(e)


# ---- the verdicts --------------------------------------------------------------------------------------------------------------------------

def test_no_verdict_before_N_and_the_verdict_at_exactly_N_written_once():
    S = [100.0 + (i % 7) for i in range(80)]
    N = [1] * 80
    e = EF.evaluate(S, N, 'H5')
    assert e['counted'] == 80 < e['N'] and e['verdict'] == 'no verdict' and e['delta'] > 0 and e['ci'] is not None
    assert EF.evaluate(S[:59], N[:59], 'H5', n_rule=200)['ci'] is None                 # under 60 sessions: no interval
    good = EF.evaluate(S + [-1e9], N + [1], 'H5', n_rule=80)                            # session 81 must not move it
    assert good['verdict'] == 'PASS' and good['ci'][0] > 0 and good == EF.evaluate(S + [-1e9], N + [1], 'H5', n_rule=80)
    assert EF.evaluate([-x for x in S], N, 'H5', n_rule=80)['verdict'] == 'FAIL'
    import numpy as np
    x = np.random.default_rng(7).normal(0.0, 1000.0, 80)
    noisy = list(x - x.mean() + 1.0)
    e = EF.evaluate(noisy, N, 'H5', n_rule=80)
    assert e['delta'] > 0 and e['ci'][0] < 0 < e['ci'][1] and e['verdict'] == 'FAIL'    # mean > 0, interval across zero
    m = EF.evaluate([10.0, 12.0, 0.0] * 5, [2, 2, 0] * 5, 'H6', n_rule=12)
    assert m['verdict'] == 'PASS' and m['trades'] == 16 and abs(m['delta'] - 5.5) < 1e-12   # Σ S ÷ Σ N over the first 12 months
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'v.json'
        first = EF.record_verdict(p, good, '2027-02-11')
        later = EF.record_verdict(p, EF.evaluate([-x for x in S], N, 'H5', n_rule=80), '2027-02-11')
        assert first['verdict'] == later['verdict'] == 'PASS' and json.loads(p.read_text())['H5']['through'] == '2027-02-11'


# ---- H6 -----------------------------------------------------------------------------------------------------------------------------------

def test_h6_the_calendar():
    assert EF.first_full_session('2026-11') == '2026-11-02' and EF.first_full_session('2027-01') == '2027-01-04'
    assert EF.is_entry_day('2026-11-02') and not EF.is_entry_day('2026-11-03') and not EF.is_entry_day('2026-10-01')
    assert EF.exit_day_for('2026-12-11') == '2026-11-20'
    assert EF.exit_day_for('2026-12-18') == '2026-11-30'          # 11-27 is a half day, then the weekend


def _put(S, K, v):
    """a European put at r = q = 0 with total volatility v = σ√τ"""
    d1 = (math.log(S / K) + 0.5 * v * v) / v
    return K * T._ncdf(-(d1 - v)) - S * T._ncdf(-d1)


SPOT = 700.0


def eod_rows(sym: str, day: str, expiries: dict, bump: dict | None = None, fmt: str = 'terminal') -> list[dict]:
    """made-up end-of-day rows: expiries {E: total vol}; puts and calls 600..800 every 5; bump {(E, K, right): (bid, ask)}"""
    rows = []
    for e, v in expiries.items():
        for k in range(600, 805, 5):
            p = _put(SPOT, k, v)
            for right, px in (('PUT', p), ('CALL', p + SPOT - k)):
                b, a = max(0.0, round(px - 0.02, 2)), round(px + 0.02, 2)
                if bump and (e, k, right[0]) in bump:
                    b, a = bump[(e, k, right[0])]
                if fmt == 'terminal':
                    rows.append({'symbol': sym, 'expiration': e, 'strike': float(k), 'right': right, 'created': f'{day}T17:15:00.000',
                                 'bid': b, 'ask': a, 'bid_size': 10, 'ask_size': 10})
                else:
                    rows.append({'symbol': sym, 'expiration': dt.date.fromisoformat(e), 'strike': float(k), 'right': right[0],
                                 'date': dt.date.fromisoformat(day), 'bid': b, 'ask': a})
    return rows


ENTRY, EXIT, E = '2026-11-02', '2026-11-20', '2026-12-11'
EXPS = {'2026-11-20': 0.2 * math.sqrt(18 / 365), '2026-12-04': 0.2 * math.sqrt(32 / 365), E: 0.2 * math.sqrt(39 / 365),
        '2026-12-18': 0.2 * math.sqrt(46 / 365)}


def test_h6_entry_picks_the_expiration_strikes_and_fills_of_the_rule():
    df, probs = EF.shape_eod(eod_rows('SPY', ENTRY, EXPS), ENTRY, 'SPY', None)
    assert not probs and df.height == 4 * 41 * 2
    r = EF.h6_entry('SPY', ENTRY, df, SPOT)
    assert r['status'] == 'open' and r['expiry'] == E and r['dte'] == 39 and r['exit_day'] == EXIT, r   # 46 days is out, 39 the latest in 30–45
    ch = EF.chain_of(df, 'SPY', E)
    assert (r['k_short'], r['k_long']) == (T.nearest_delta(ch, SPOT, 'put', 0.30)[0], T.nearest_delta(ch, SPOT, 'put', 0.15)[0])
    assert r['k_long'] < r['k_short'] < SPOT and abs(r['d_short'] - 0.30) < 0.03 and abs(r['d_long'] - 0.15) < 0.03
    qs, ql = ch.puts[r['k_short']], ch.puts[r['k_long']]
    assert (r['short_bid'], r['long_ask']) == (qs.bid, ql.ask) and abs(r['credit'] - (qs.bid - ql.ask)) < 1e-12
    # the SDK's shape (dates as dates, rights C/P) reads the same
    df2, probs2 = EF.shape_eod(eod_rows('SPY', ENTRY, EXPS, fmt='sdk'), ENTRY, 'SPY', None)
    assert not probs2 and EF.h6_entry('SPY', ENTRY, df2, SPOT)['k_short'] == r['k_short']
    # no expiration 30–45 days out → a final no-trade row
    df3, _ = EF.shape_eod(eod_rows('SPY', ENTRY, {'2026-11-20': 0.05, '2026-12-18': 0.09}), ENTRY, 'SPY', None)
    n = EF.h6_entry('SPY', ENTRY, df3, SPOT)
    assert n['status'] == 'no-trade' and '30–45' in n['reason']
    # an answer of another date or root is refused
    assert EF.shape_eod(eod_rows('SPY', '2026-10-30', EXPS), ENTRY, 'SPY', None)[1]
    assert EF.shape_eod(eod_rows('QQQ', ENTRY, EXPS), ENTRY, 'SPY', None)[1]


def test_h6_exit_golden_and_the_missing_quote_rule():
    df, _ = EF.shape_eod(eod_rows('SPY', ENTRY, EXPS), ENTRY, 'SPY', None)
    en = {k: ('' if v is None else str(v)) for k, v in EF.h6_entry('SPY', ENTRY, df, SPOT).items()}   # as read back from the CSV
    ks, kl = float(en['k_short']), float(en['k_long'])
    xr = eod_rows('SPY', EXIT, {E: 0.2 * math.sqrt(21 / 365)}, bump={(E, int(ks), 'P'): (1.48, 1.50), (E, int(kl), 'P'): (0.55, 0.57)})
    dfx, probs = EF.shape_eod(xr, EXIT, 'SPY', E)
    assert not probs
    t = EF.h6_exit(en, EXIT, dfx, 705.0)
    credit = float(en['credit'])
    # buy back the short at its ask 1.50, sell the long at its bid 0.55: 100 × (credit − 0.95) − 4 × 0.68748
    assert abs(t['debit'] - 0.95) < 1e-12 and abs(t['pnl'] - (100 * (credit - 0.95) - 2.74992)) < 1e-9 and t['exit_flags'] == ''
    assert abs(t['risk'] - 100 * (ks - kl - credit)) < 1e-9 and t['short_below_intrinsic'] == 0
    gone = dfx.filter(~((pl.col('strike') == ks) & (pl.col('right') == 'P')))
    t2 = EF.h6_exit(en, EXIT, gone, 705.0)          # no short-put quote: intrinsic (0 at 705) + its entry spread
    assert abs(t2['debit'] - ((float(en['short_ask']) - float(en['short_bid'])) - 0.55)) < 1e-12 and 'short put' in t2['exit_flags']


def test_h6_runs_through_a_month_asks_once_and_keeps_the_answers():
    calls = []

    def fetch(sym, day, exp):
        calls.append((sym, day, exp))
        if exp is None:
            return eod_rows(sym, day, EXPS)
        return eod_rows(sym, day, {exp: 0.2 * math.sqrt(21 / 365)})
    closes = {('SPY', ENTRY): SPOT, ('QQQ', ENTRY): SPOT, ('SPY', EXIT): 702.0, ('QQQ', EXIT): 690.0}
    with tempfile.TemporaryDirectory() as d:
        root, out, store = Path(d) / 'pq', Path(d) / 'fwd', Path(d) / 'store'
        days = ['2026-10-30', ENTRY, '2026-11-03', EXIT, '2026-11-23']
        res = EF.run(days, root, lambda nm, dd: closes.get((nm, dd)), fetch, store=store, folder=out, only=('H6',))
        assert not res['failures'] and res['h6_entries'] == ['2026-11/SPY', '2026-11/QQQ'] and res['h6_trades'] == ['2026-11/SPY', '2026-11/QQQ'], res
        assert res['calls'] == 4 and calls == [('SPY', ENTRY, None), ('QQQ', ENTRY, None), ('SPY', EXIT, E), ('QQQ', EXIT, E)]
        assert sorted(p.name for p in store.rglob('*.ndjson.gz')) == [f'{ENTRY}__ALL.ndjson.gz'] * 2 + [f'{EXIT}__{E}.ndjson.gz'] * 2
        with gzip.open(store / 'SPY' / f'{ENTRY}__ALL.ndjson.gz', 'rt') as g:
            assert [json.loads(x) for x in g] == eod_rows('SPY', ENTRY, EXPS)                       # kept as answered
        trs = EF.read_rows(out / 'h6_trades.csv')
        ms = EF.h6_months(EF.read_rows(out / 'h6_entries.csv'), trs)
        assert len(ms) == 1 and ms[0]['N'] == 2 and abs(ms[0]['S'] - sum(float(t['pnl']) for t in trs)) < 1e-9
        assert '| 1 / 449 | 2 |' in (out / 'EDGE_FORWARD_REPORT.md').read_text()
        before = {p.name: p.read_text() for p in out.glob('*.csv')}
        again = EF.run(days, root, lambda nm, dd: closes.get((nm, dd)), fetch, store=store, folder=out, only=('H6',))
        assert again['calls'] == 0 and again['h6_entries'] == again['h6_trades'] == [] and len(calls) == 4
        assert {p.name: p.read_text() for p in out.glob('*.csv')} == before


def test_h6_failures_are_loud_and_write_nothing():
    with tempfile.TemporaryDirectory() as d:
        root, out, store = Path(d) / 'pq', Path(d) / 'fwd', Path(d) / 'store'

        def refuse(sym, day, exp):
            raise EF.EdgeFetchError('472 NO_DATA')
        res = EF.run([ENTRY], root, lambda nm, dd: SPOT, refuse, store=store, folder=out, only=('H6',))
        assert res['failures'] == [f'{ENTRY} h6-entry: SPY end-of-day options (every expiration): 472 NO_DATA'], res
        assert not (out / 'h6_entries.csv').exists() and not list(store.rglob('*.gz'))
        res = EF.run([ENTRY], root, official_none, lambda s, dd, e: eod_rows(s, dd, EXPS), store=store, folder=out, only=('H6',))
        assert res['failures'][0].startswith(f'{ENTRY} h6-official-close') and not (out / 'h6_entries.csv').exists()
        res = EF.run([ENTRY], root, lambda nm, dd: SPOT, lambda s, dd, e: eod_rows(s, '2026-10-30', EXPS), store=store, folder=out, only=('H6',))
        assert 'refused' in res['failures'][0] and not list(store.rglob('*.gz'))                      # a wrong-date answer is never kept
        res = EF.run([ENTRY], root, lambda nm, dd: SPOT, None, store=store, folder=out, only=('H6',))
        assert 'no source was given' in res['failures'][0]


def test_h6_months_are_counted_in_order_and_only_when_final():
    ents = [{'month': '2026-11', 'name': 'SPY', 'status': 'open'}, {'month': '2026-11', 'name': 'QQQ', 'status': 'no-trade'},
            {'month': '2026-12', 'name': 'SPY', 'status': 'open'}, {'month': '2026-12', 'name': 'QQQ', 'status': 'open'},
            {'month': '2027-01', 'name': 'SPY', 'status': 'no-trade'}, {'month': '2027-01', 'name': 'QQQ', 'status': 'no-trade'}]
    trs = [{'month': '2026-11', 'name': 'SPY', 'pnl': '40.0'}, {'month': '2026-12', 'name': 'SPY', 'pnl': '-10.0'}]
    ms = EF.h6_months(ents, trs)
    assert [(m['month'], m['S'], m['N']) for m in ms] == [('2026-11', 40.0, 1)]      # December's QQQ is still open: it and after wait
    ms = EF.h6_months(ents, trs + [{'month': '2026-12', 'name': 'QQQ', 'pnl': '5.0'}])
    assert [(m['month'], m['S'], m['N']) for m in ms] == [('2026-11', 40.0, 1), ('2026-12', -5.0, 2), ('2027-01', 0.0, 0)]


# ---- the terminal path and the daily job ----------------------------------------------------------------------------------------------------

class _EodTerminal:
    """a stand-in Theta Terminal on 127.0.0.1 answering /v3/terminal/mdds/status and /v3/option/history/eod"""

    def __init__(self, rows):
        self.queries, self.headers = [], []
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                import urllib.parse as up
                u = up.urlparse(self.path)
                outer.queries.append((u.path, dict(up.parse_qsl(u.query))))
                outer.headers.append(dict(self.headers))
                if u.path == '/v3/terminal/mdds/status':
                    body = b'CONNECTED'
                elif u.path == '/v3/option/history/eod':
                    body = ('\n'.join(json.dumps(r) for r in rows) + '\n').encode()
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.base = f'http://127.0.0.1:{self.server.server_address[1]}/v3'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


def test_the_terminal_path_asks_the_eod_route_on_127_0_0_1_with_no_key():
    import daily_forward as DF
    import paper_backtest as B
    term = _EodTerminal(eod_rows('SPY', ENTRY, EXPS))
    try:
        f = DF.terminal_eod(B.ThetaFetch(term.base, waits=(0, 0)))
        rows = f('SPY', ENTRY, None)
        assert rows == eod_rows('SPY', ENTRY, EXPS)
        f('SPY', EXIT, E)
        paths = [p for p, _ in term.queries]
        assert paths == ['/v3/terminal/mdds/status', '/v3/option/history/eod', '/v3/option/history/eod']    # the status once
        q1, q2 = term.queries[1][1], term.queries[2][1]
        assert q1 == {'symbol': 'SPY', 'expiration': '*', 'start_date': '20261102', 'end_date': '20261102', 'format': 'ndjson'}
        assert q2['expiration'] == '20261211' and q2['start_date'] == '20261120'
        assert not any('authorization' in {k.lower() for k in h} for h in term.headers)
    finally:
        term.close()


def test_the_daily_job_runs_step_8_after_the_tracker_once_and_keeps_its_append_on_a_failure():
    try:
        import test_paper_tracker as TP
    except Exception as e:  # noqa: BLE001
        skip(f'daily job wiring: the paper tracker tests do not import here ({type(e).__name__})')
        return
    import daily_forward as DF
    term = TP._FakeThetaTerminal()
    try:
        with tempfile.TemporaryDirectory() as d:
            job, log, lines, uw, closes = TP.job_pieces(d)
            job.edge, job.edge_folder, job.h7h9_folder = True, Path(d) / 'edge', Path(d) / 'h7h9'
            asked = []
            res = DF.run_job(job, now=TP.JOB_NOW, log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes,
                             edge_fetch=lambda *a: asked.append(a) or [])
            # 2026-10-22 is the tracker's session but before H5's start and no H6 entry: step 8 runs, adds nothing, asks nothing
            assert res['rc'] == 0 and res['appended'] == [TP.JOB_DAY] and res['edge_added'] == {'h5_added': [], 'h6_entries': [], 'h6_trades': []}, (res, lines.lines[-5:])
            assert not asked and res['edge_calls'] == 0 and '| 0 / 1,326 |' in (job.edge_folder / 'EDGE_FORWARD_REPORT.md').read_text()
            # H7 / H9 run too: 2026-10-22 is before their series, so nothing is added and the report says no verdict
            assert res['edge_h7h9_added'] == {'h7': [], 'h9': []}, res
            assert '| H7 | SPY | 0 / 366 |' in (job.h7h9_folder / 'H7_H9_FORWARD_REPORT.md').read_text()
            again = DF.run_job(job, now=TP.JOB_NOW + dt.timedelta(hours=1), log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes,
                               edge_fetch=lambda *a: asked.append(a) or [])
            assert again['rc'] == 0 and again['edge_added']['h5_added'] == [] and not asked
        with tempfile.TemporaryDirectory() as d:
            job, log, lines, uw, closes = TP.job_pieces(d)
            job.edge, job.edge_folder, job.h7h9_folder = True, Path(d) / 'edge', Path(d) / 'h7h9'
            job.edge_folder.mkdir()
            (job.edge_folder / 'h5_sessions.csv').write_text('not,this,file\n1,2,3\n')
            res = DF.run_job(job, now=TP.JOB_NOW, log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes)
            assert res['rc'] == 1 and res['appended'] == [TP.JOB_DAY], res                     # the tracker's append is kept
            assert any(re.search(r'DAILY-FORWARD FAIL - edge', l) for l in lines.lines), lines.lines[-5:]
    finally:
        term.close()


# ---- H7 and H9 (research_notes/Edge search/H7_H8_H9/forward_h7_h9.py) ---------------------------------------------------------------------

H7DIR = REPO / 'research_notes' / 'Edge search' / 'H7_H8_H9'
sys.path.insert(0, str(H7DIR))
import forward_h7_h9 as FH  # noqa: E402


def test_h7_h9_the_rules_in_the_code_are_the_forward_rule_and_the_prereg():
    fr = (H7DIR / 'FORWARD_RULE_H7.md').read_text()
    p9 = (H7DIR / 'PREREG_H9.md').read_text()
    assert FH.N_RULE == {('H7', 'SPY'): 366, ('H7', 'QQQ'): 483, ('H9', 'SPY'): 7940, ('H9', 'QQQ'): 7940}
    assert '| SPY | 77 | 19.01 | 64.90 | 9.50 | **366** |' in fr and '| QQQ | 108 | 21.05 | 82.49 | 10.52 | **483** |' in fr
    assert '**N = 7,940 sessions for both names**' in p9 or 'N = 7,940 sessions for both names' in p9
    assert FH.H7_COST == {'1x': 1.50, '2x': 3.00} and FH.H9_COST == {'1x': 2.00, '2x': 4.00} and FH.H7_EXIT_J == 268
    assert (FH.BLOCK, FH.BOOT_N, FH.SEED, FH.H7_CHECKPOINT) == (20, 2000, 20261023, 8)
    assert FH.H7_START == '2026-10-28' and FH.SERIES_START == '2026-10-23'
    pw = json.loads((H7DIR / 'power_h7_forward.json').read_text())
    assert {nm: pw['names'][nm]['N'] for nm in ('SPY', 'QQQ')} == {'SPY': 366, 'QQQ': 483}
    try:
        names = subprocess.run(['git', '-C', str(REPO), 'show', '--name-only', '--format=', 'fcc1f4d'], capture_output=True, text=True,
                               check=True).stdout.split('\n')
    except Exception as e:  # noqa: BLE001
        skip(f'forward rule commit: git cannot show fcc1f4d here ({type(e).__name__})')
        return
    assert sorted(x for x in names if x.strip()) == sorted(f'research_notes/Edge search/H7_H8_H9/{f}' for f in
                                                           ('FORWARD_RULE_H7.md', 'power_h7_forward.json', 'power_h7_forward.py'))


def test_h7_the_power_script_reproduces_N():
    import importlib.util
    import numpy as np
    spec = importlib.util.spec_from_file_location('power_h7_forward', H7DIR / 'power_h7_forward.py')
    PW = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(PW)
    t = pl.read_csv(PW.TRADES).filter(pl.col('net_1x').is_not_null())
    for nm, n in (('SPY', 366), ('QQQ', 483)):
        u = t.filter(pl.col('name') == nm).sort('A')
        x = (u['net_1x'] / (100.0 * u['C_prev']) * 1e4).to_numpy()
        assert PW.n0(float(x.std(ddof=1)), 0.5 * float(x.mean())) == n
        a = np.array(u['A'].to_list(), dtype='datetime64[D]')
        assert PW.power(x, 0.5 * float(x.mean()), np.busday_count(a[:-1], a[1:]), n) >= 0.80


def test_h7_the_fomc_calendar_lookup():
    cal, end = FH.fomc_calendar()
    assert [r['date'] for r in cal[:4]] == ['2026-10-28', '2026-12-09', '2027-01-27', '2027-03-17'] and end == '2027-12-31'
    assert all(r['time_et'] == '14:00' for r in cal) and len(cal) == 10
    assert FH.meeting_end('October 27-28 - 2026') == '2026-10-28' and FH.meeting_end('June 8-9* - 2027') == '2027-06-09'
    assert FH.meeting_end('April 30-May 1 - 2024') == '2024-05-01' and FH.meeting_end('nothing') is None
    with tempfile.TemporaryDirectory() as d:                 # a calendar missing a meeting the committed list has: loud
        rows = [r for r in json.loads(FH.MACRO.read_text()) if r['date'] != '2027-06-09']
        f = Path(d) / 'macro.json'
        f.write_text(json.dumps(rows))
        try:
            FH.fomc_calendar(macro=f)
            raise AssertionError('a missing statement went unnoticed')
        except FH.EdgeDataError as e:
            assert '2027-06-09' in e.why and 'disagree' in e.why
    assert FH.prev_session('2026-10-28') == '2026-10-27' and FH.next_session('2026-11-25') == '2026-11-27'
    assert FH.half_days_due(['2026-11-30']) == ['2026-11-27'] and FH.half_days_due(['2026-10-22']) == []
    try:
        FH.sessions('2027-12-30', '2028-01-04')
        raise AssertionError('a session past the holidays list went unnoticed')
    except FH.EdgeDataError as e:
        assert 'HOLIDAYS' in e.why


def _bars(root: Path, name: str, day: str, quotes: dict):
    """quotes {hhmm: (open, close)} → the layout's 1-minute file"""
    rows = [(_ts(day, m), o, max(o, c), min(o, c), c, 1000, 10, c) for m, (o, c) in sorted(quotes.items())]
    df = pl.DataFrame(rows, schema={'timestamp': pl.Datetime('ms'), 'open': pl.Float64, 'high': pl.Float64, 'low': pl.Float64, 'close': pl.Float64,
                                    'volume': pl.Int64, 'count': pl.Int64, 'vwap': pl.Float64}, orient='row').with_columns(pl.col('timestamp').dt.replace_time_zone(NY))
    (root / f'data/underlying/{name}').mkdir(parents=True, exist_ok=True)
    df.write_parquet(root / f'data/underlying/{name}/{day}.parquet')


def _divs(d, through: str = '2026-12-11', ex: dict | None = None) -> Path:
    f = Path(d) / f'divs_{through}_{len(json.dumps(ex or {}))}.json'
    f.write_text(json.dumps({nm: {'complete_through': through, 'ex': (ex or {}).get(nm, {})} for nm in ('SPY', 'QQQ')}))
    return f


CLOSES = {('SPY', '2026-10-23'): 760.00, ('QQQ', '2026-10-23'): 700.00, ('SPY', '2026-10-26'): 761.50, ('QQQ', '2026-10-26'): 702.25,
          ('SPY', '2026-10-27'): 762.00, ('QQQ', '2026-10-27'): 703.00, ('SPY', '2026-10-28'): 766.00, ('QQQ', '2026-10-28'): 701.00}


def official_uw(nm, d):
    c = CLOSES.get((nm, d))
    return (c, 'uw_1d') if c is not None else (None, None)


def h7_layout(root: Path, drop_1358: bool = False):
    for nm, (o930, x) in (('SPY', (763.10, 764.55)), ('QQQ', (702.40, 701.95))):
        for day, q in (('2026-10-26', {'09:30': (760.80, 761.0)}), ('2026-10-27', {'09:30': (761.90, 762.0)}),
                       ('2026-10-28', {'09:30': (o930, o930 + 0.1), **({} if drop_1358 else {'13:58': (x - 0.05, x)}), '15:59': (x, x)})):
            _bars(root, nm, day, q)


def test_h7_golden_trade_from_made_up_quotes_and_the_exclusion_rule():
    with tempfile.TemporaryDirectory() as d:
        root, out = Path(d) / 'pq', Path(d) / 'fwd'
        h7_layout(root)
        days = ['2026-10-23', '2026-10-26', '2026-10-27', '2026-10-28']
        res = FH.run(days, root, official_uw, folder=out, divs_path=_divs(d), only=('H7',))
        assert not res['failures'] and res['h7_added'] == ['SPY/2026-10-28', 'QQQ/2026-10-28'], res
        rows = {r['name']: r for r in EF.read_rows(out / 'h7_trades.csv')}
        # SPY: buy 100 at the 2026-10-27 close 762.00, sell at the 13:58 close 764.55: 100 × 2.55 − 1.50 = 253.50 (2× 252.00)
        s = rows['SPY']
        assert (s['prev'], s['status'], float(s['C_prev']), float(s['X']), s['C_prev_src']) == ('2026-10-27', 'trade', 762.0, 764.55, 'uw_1d')
        assert abs(float(s['net_1x']) - 253.50) < 1e-9 and abs(float(s['net_2x']) - 252.0) < 1e-9 and float(s['dividend']) == 0.0
        assert abs(float(s['night']) - 110.0) < 1e-9 and abs(float(s['day']) - 145.0) < 1e-9
        # QQQ: 100 × (701.95 − 703.00) − 1.50 = −106.50
        assert abs(float(rows['QQQ']['net_1x']) - (-106.50)) < 1e-9
        rep = (out / 'H7_H9_FORWARD_REPORT.md').read_text()
        assert '| H7 | SPY | 1 / 366 | +253.50 | +252.00 | — | no verdict |' in rep, rep
    with tempfile.TemporaryDirectory() as d:                 # the file is there but no priced 13:58 bar: excluded and listed
        root, out = Path(d) / 'pq', Path(d) / 'fwd'
        h7_layout(root, drop_1358=True)
        res = FH.run(['2026-10-27', '2026-10-28'], root, official_uw, folder=out, divs_path=_divs(d), only=('H7',))
        r = EF.read_rows(out / 'h7_trades.csv')
        assert not res['failures'] and {x['status'] for x in r} == {'excluded'} and all(x['excluded'] == 'no priced 13:58 bar' for x in r)
        assert 'no priced 13:58 bar' in (out / 'H7_H9_FORWARD_REPORT.md').read_text() and FH.evaluate('H7', 'SPY', r)['counted'] == 0


def test_h7_waits_before_the_statement_and_fails_loudly_on_a_missing_input():
    with tempfile.TemporaryDirectory() as d:
        root, out = Path(d) / 'pq', Path(d) / 'fwd'
        h7_layout(root)
        res = FH.run(['2026-10-23', '2026-10-27'], root, official_uw, folder=out, divs_path=_divs(d), only=('H7',))
        assert res == {'h7_added': [], 'h9_added': [], 'failures': [], 'warnings': []} and not (out / 'h7_trades.csv').exists()
        res = FH.run(['2026-10-28'], root, lambda nm, dd: (None, None), folder=out, divs_path=_divs(d), only=('H7',))
        assert [f.split(':')[0] for f in res['failures']] == ['2026-10-27 h7-official-close'] * 2 and not (out / 'h7_trades.csv').exists()
        res = FH.run(['2026-10-28'], root, lambda nm, dd: (762.0, 'theta_eod'), folder=out, divs_path=_divs(d), only=('H7',))
        assert 'not UW' in res['failures'][0] and not (out / 'h7_trades.csv').exists()          # another source is never taken
        (root / 'data/underlying/SPY/2026-10-28.parquet').unlink()
        res = FH.run(['2026-10-28'], root, official_uw, folder=out, divs_path=_divs(d), only=('H7',))
        assert res['failures'] == ['2026-10-28 h7-bars: SPY 1-minute bars of 2026-10-28 are not in the layout'] and res['h7_added'] == ['QQQ/2026-10-28']


def test_h7_h9_dividends_are_paid_by_ex_date_and_never_assumed():
    with tempfile.TemporaryDirectory() as d:
        root, out = Path(d) / 'pq', Path(d) / 'fwd'
        h7_layout(root)
        f = _divs(d, ex={'SPY': {'2026-10-28': {'amount': 1.90, 'source': 'made up'}}})
        FH.run(['2026-10-28'], root, official_uw, folder=out, divs_path=f, only=('H7',))
        s = {r['name']: r for r in EF.read_rows(out / 'h7_trades.csv')}['SPY']
        assert abs(float(s['net_1x']) - (253.50 + 190.0)) < 1e-9 and float(s['div']) == 1.90
    with tempfile.TemporaryDirectory() as d:                 # the table not complete through A: loud, nothing written
        root, out = Path(d) / 'pq', Path(d) / 'fwd'
        h7_layout(root)
        res = FH.run(['2026-10-28'], root, official_uw, folder=out, divs_path=_divs(d, through='2026-10-27'), only=('H7',))
        assert len(res['failures']) == 2 and all('h7-dividend' in x and 'may be' in x for x in res['failures']), res
        assert not (out / 'h7_trades.csv').exists() and len(res['warnings']) == 2
        res = FH.run(['2026-10-28'], root, official_uw, folder=out,
                     divs_path=_divs(d, ex={'QQQ': {'2026-10-28': {'amount': None, 'source': 'announced'}}}), only=('H7',))
        assert res['h7_added'] == ['SPY/2026-10-28'] and 'no amount yet' in res['failures'][0]
    with tempfile.TemporaryDirectory() as d:                 # H9: the dividend whose ex-date is the next session is paid
        root, out = Path(d) / 'pq', Path(d) / 'fwd'
        h9_layout(root)
        f = _divs(d, ex={'QQQ': {'2026-10-26': {'amount': 0.75, 'source': 'made up'}}})
        FH.run(['2026-10-23', '2026-10-26'], root, official_uw, folder=out, divs_path=f, only=('H9',))
        q = {r['name']: r for r in EF.read_rows(out / 'h9_sessions.csv')}['QQQ']
        assert abs(float(q['net_1x']) - (100 * (699.10 - 700.00) + 75.0 - 2.0)) < 1e-9
    divs = {'SPY': {'complete_through': '2026-12-11', 'ex': {'2026-10-26': {'amount': 2.0}}}, 'QQQ': {'complete_through': '2026-12-11', 'ex': {}}}
    assert FH.dividend(divs, 'SPY', '2026-10-26', 's') == 2.0 and FH.dividend(divs, 'QQQ', '2026-10-26', 's') == 0.0
    real = FH.load_divs()
    assert real['SPY']['complete_through'] == real['QQQ']['complete_through'] == '2026-12-11'


def h9_layout(root: Path):
    for nm, o in (('SPY', 761.20), ('QQQ', 699.10)):
        _bars(root, nm, '2026-10-26', {'09:30': (o, o + 0.2), '09:31': (o + 0.2, o)})
        _bars(root, nm, '2026-10-27', {'09:30': (o + 1.0, o + 1.1)})


def test_h9_golden_rows_idempotent_append_and_loud_failures():
    with tempfile.TemporaryDirectory() as d:
        root, out = Path(d) / 'pq', Path(d) / 'fwd'
        h9_layout(root)
        res = FH.run(['2026-10-23', '2026-10-26'], root, official_uw, folder=out, divs_path=_divs(d), only=('H9',))
        # one night each: the 2026-10-23 close → the 2026-10-26 09:30 open; 10-26's night waits for 10-27
        assert not res['failures'] and res['h9_added'] == ['SPY/2026-10-23', 'QQQ/2026-10-23'], res
        rows = {r['name']: r for r in EF.read_rows(out / 'h9_sessions.csv')}
        assert abs(float(rows['SPY']['net_1x']) - (100 * (761.20 - 760.00) - 2.0)) < 1e-9          # +118.00
        assert abs(float(rows['QQQ']['net_1x']) - (100 * (699.10 - 700.00) - 2.0)) < 1e-9          # −92.00
        assert abs(float(rows['QQQ']['net_2x']) - (-94.0)) < 1e-9 and rows['SPY']['next'] == '2026-10-26'
        f = out / 'h9_sessions.csv'
        txt = f.read_text()
        again = FH.run(['2026-10-23', '2026-10-26'], root, official_uw, folder=out, divs_path=_divs(d), only=('H9',))
        assert again['h9_added'] == [] and f.read_text() == txt
        res = FH.run(['2026-10-23', '2026-10-26', '2026-10-27'], root, official_uw, folder=out, divs_path=_divs(d), only=('H9',))
        assert res['h9_added'] == ['SPY/2026-10-26', 'QQQ/2026-10-26'] and len(EF.read_rows(f)) == 4
        rep = (out / 'H7_H9_FORWARD_REPORT.md').read_text()
        assert '| H9 | SPY | 2 / 7,940 | +93.00 | +91.00 | — | no verdict |' in rep and 'no verdict' in rep, rep
    with tempfile.TemporaryDirectory() as d:                 # an unpriced 09:30 bar: loud, nothing written, never substituted
        root, out = Path(d) / 'pq', Path(d) / 'fwd'
        for nm in ('SPY', 'QQQ'):
            _bars(root, nm, '2026-10-26', {'09:31': (760.0, 760.1)})
        res = FH.run(['2026-10-23', '2026-10-26'], root, official_uw, folder=out, divs_path=_divs(d), only=('H9',))
        assert res['failures'] == ['2026-10-23 h9-bars: SPY has no priced 09:30 bar on 2026-10-26',
                                   '2026-10-23 h9-bars: QQQ has no priced 09:30 bar on 2026-10-26'] and not (out / 'h9_sessions.csv').exists()


def test_h7_h9_no_verdict_before_N_and_the_verdict_at_exactly_N_written_once():
    cal, _ = FH.fomc_calendar()
    keep = dict(FH.N_RULE)
    try:
        FH.N_RULE[('H7', 'SPY')] = 10
        good = [{'name': 'SPY', 'A': r['date'], 'status': 'trade', 'net_1x': str(40.0 + i), 'net_2x': str(38.5 + i)} for i, r in enumerate(cal)]
        e9 = FH.evaluate('H7', 'SPY', good[:9])
        assert e9['verdict'] == 'no verdict' and e9['counted'] == 9 and e9['ci'] is None
        e10 = FH.evaluate('H7', 'SPY', good)
        assert e10['verdict'] == 'CONFIRMED' and e10['ci'][0] > 0 and abs(e10['mean_1x'] - 44.5) < 1e-12 and e10['through'] == '2027-12-08'
        bad = [dict(r, net_1x=str(-float(r['net_1x']))) for r in good]
        assert FH.evaluate('H7', 'SPY', bad)['verdict'] == 'NOT CONFIRMED'
        FH.N_RULE[('H9', 'QQQ')] = 80
        h9 = [{'name': 'QQQ', 'day': f'd{i:03d}', 'net_1x': str(5.0 + i % 3), 'net_2x': str(3.0 + i % 3)} for i in range(80)]
        ev = FH.evaluate('H9', 'QQQ', h9 + [{'name': 'QQQ', 'day': 'd999', 'net_1x': '-1e9', 'net_2x': '-1e9'}])   # past N: no effect
        assert ev['verdict'] == 'PASS' and ev['counted'] == 81 and ev['trades'] == 80 and ev['through'] == 'd079'
        assert FH.evaluate('H9', 'QQQ', h9[:79])['verdict'] == 'no verdict'
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'v.json'
            first = FH.record_verdict(p, e10)
            later = FH.record_verdict(p, FH.evaluate('H7', 'SPY', bad))
            assert first['verdict'] == later['verdict'] == 'CONFIRMED' and json.loads(p.read_text())['H7 SPY']['through'] == '2027-12-08'
        cps = FH.checkpoints(good, 'SPY')
        assert [c['k'] for c in cps] == [8] and cps[0]['ci'] is None and cps[0]['through'] == '2027-09-15'
    finally:
        FH.N_RULE.clear()
        FH.N_RULE.update(keep)
    with tempfile.TemporaryDirectory() as d:                 # the report labels a checkpoint "no verdict"
        out = Path(d)
        rows = [{c: '' for c in FH.H7_COLS} | {'name': 'SPY', 'A': r['date'], 'status': 'trade', 'net_1x': '10.0', 'net_2x': '8.5'} for r in cal[:8]]
        EF.append_rows(out / 'h7_trades.csv', FH.H7_COLS, rows, ('name', 'A'))
        rep = FH.write_report(FH.default_paths(out))
        assert 'SPY after 8 trades (through 2027-09-15): mean +10.00' in rep and 'checkpoint — no verdict' in rep, rep
        assert '| H7 | SPY | 8 / 366 | +10.00 | +8.50 | — | no verdict |' in rep and not (out / 'verdicts.json').exists()


def logging_quiet():
    import logging
    lg = logging.getLogger('edge_forward_test_quiet')
    lg.handlers[:] = [logging.NullHandler()]
    lg.propagate = False
    return lg


def test_the_daily_job_collects_a_half_days_close_and_bars_for_h9():
    import daily_forward as DF
    import paper_backtest as B
    import paper_audit as PA
    calls = {'fetch': [], 'uw': []}
    orig = (B.complete_sessions, B.fetch_theta, DF.ensure_official)

    def fake_fetch(a, b, root, **kw):
        calls['fetch'].append((a, sorted(kw['only'])))
        return {'rc': 0, 'failed': [], 'incomplete': [], 'exists': [], 'not_asked': []}

    def fake_official(day, closes, odir, uw, log, names=('SPY', 'QQQ')):
        calls['uw'].append((day, uw is not None))
        return closes, [], 2
    try:
        B.complete_sessions = lambda *a, **k: (['2026-11-30'], {})
        B.fetch_theta = fake_fetch
        DF.ensure_official = fake_official
        with tempfile.TemporaryDirectory() as d:
            job = DF.Job(Path(d) / 'pq', Path(d) / 'replay', Path(d) / 'cum.md', official_dir=Path(d) / 'oc', h7h9_folder=Path(d) / 'h7h9')
            closes = PA.OfficialCloses(uw_dirs=(Path(d) / 'oc',), uw_lake_glob=None, theta_glob=None, live_root=None)
            out = DF.run_h7h9(job, logging_quiet(), closes, uw_client=object())
            assert calls['uw'] == [('2026-11-27', True)] and calls['fetch'] == [('2026-11-27', [('under', 'QQQ'), ('under', 'SPY')])]
            # nothing else is on disk: the first H9 night (2026-10-23) fails loudly on its official close and writes nothing
            assert out['uw_calls'] == 2 and out['failures'] and out['failures'][0].startswith('2026-10-27 h7-official-close'), out
            assert any(f.startswith('2026-10-23 h9-official-close') for f in out['failures']) and not (Path(d) / 'h7h9' / 'h9_sessions.csv').exists()
            job.source = 'sdk'
            out = DF.run_h7h9(job, logging_quiet(), closes, uw_client=object())
            assert len(calls['fetch']) == 1 and any('--source sdk fetches none' in n for n in out['half_day_notes'])
    finally:
        B.complete_sessions, B.fetch_theta, DF.ensure_official = orig


if __name__ == '__main__':
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print(f'ok    {name}')
            except Exception as e:  # noqa: BLE001
                failed += 1
                import traceback
                print(f'FAIL  {name}: {type(e).__name__}: {e}')
                traceback.print_exc()
    print(('\nall passed' if not failed else f'\n{failed} failed') + (f' ({len(SKIPPED)} skipped)' if SKIPPED else ''))
    sys.exit(1 if failed else 0)
