"""
Tests for scripts/eod_recorder.py — the dry-run path on the fixtures: no network, a fake clock.

Run:  python3 -I -m pytest tests/test_eod_recorder.py -q      (pytest installed)
      python3 -I tests/test_eod_recorder.py                   (plain: runs every test_* below)

What they prove: a second run adds no row and makes no call (the markers); a partial marker is fetched again without
a duplicate; the limiter paces 100 a minute, holds three in flight and stops at the daily budget; 429 waits the
Retry-After, 5xx backs off 2-4-8-16 and gives up after five, a 404 is recorded and passed over; the token never
appears in a log line, a marker, a failure record or an error; every Parquet column is a string and the stamps are
there; rows outside the day are dropped; the schedule skips weekends, holidays and knows a half day.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import polars as pl  # noqa: E402

import eod_recorder as R  # noqa: E402

TOKEN = 'TEST-TOKEN-0123456789abcdef-NEVER-SHOWN'
DAY = '2026-10-20'
NAMES = ['SPY', 'SPX', 'NVDA']


def harness(root: Path, fail_plan=None, names=NAMES, budget=20_000, per_minute=100):
    scrub = R.Scrub(TOKEN)
    log = R.make_logger(scrub, None, stream=None, name='eod_recorder_test')
    lines = R.ListHandler(scrub)
    log.addHandler(lines)
    clock = R.FakeClock(dt.datetime(2026, 10, 21, 20, 15, tzinfo=R.UTC))
    limiter = R.RateLimiter(max_in_flight=3, per_minute=per_minute, daily_budget=budget, clock=clock)
    client = R.FakeUwClient(limiter, log, clock, scrub, fail_plan=fail_plan)
    store = R.Store(root)
    rec = R.Recorder(client, store, limiter, log, clock, scrub, names=names)
    return rec, client, store, lines, clock, limiter


def rows_in(store: R.Store, ep: str, name: str) -> int:
    df = store.read(ep, name, DAY)
    return 0 if df is None else df.height


# ---- the dry-run path, twice -------------------------------------------------------------------------------------------

def test_two_runs_add_no_duplicate_and_the_markers_skip():
    with tempfile.TemporaryDirectory() as d:
        rec, client, store, lines, clock, limiter = harness(Path(d))
        first = rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'))
        assert first['failed'] == 0 and first['incomplete'] == 0 and first['budget_stopped'] is False
        counts = {(ep.key, n): rows_in(store, ep.key, n) for ep in R.EOD_ENDPOINTS for n in NAMES}
        calls_after_first = client.calls
        assert counts[('flow_alerts', 'SPY')] == 450          # the six rows before the day's start dropped
        assert counts[('flow_alerts', 'SPX')] == 450 + 40     # both roots, SPX and SPXW
        assert counts[('darkpool', 'SPY')] == 1300            # seven pages of 200 after the 422 fallback
        assert counts[('darkpool', 'SPX')] == 0               # an index: not asked
        assert counts[('ohlc_1m', 'SPX')] == 0
        assert counts[('chain', 'NVDA')] == 1234              # three pages
        assert counts[('net_prem_ticks', 'SPY')] == 390 and counts[('oi_strike', 'SPY')] == 491
        # a key per row, every key distinct
        for (ep, n), c in counts.items():
            if c:
                df = store.read(ep, n, DAY)
                assert df['_key'].n_unique() == df.height, (ep, n)
        second = rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'))
        assert second['skipped'] == second['jobs'] and second['added'] == 0 and second['calls'] == 0
        assert client.calls == calls_after_first
        assert {(ep.key, n): rows_in(store, ep.key, n) for ep in R.EOD_ENDPOINTS for n in NAMES} == counts
        # forced: fetched again, still no duplicate
        third = rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), force=True)
        assert third['skipped'] == 0 and third['added'] == 0 and third['rows'] == first['rows']
        assert {(ep.key, n): rows_in(store, ep.key, n) for ep in R.EOD_ENDPOINTS for n in NAMES} == counts


def test_scan_pass_stamps_the_scan_and_two_scans_coexist():
    with tempfile.TemporaryDirectory() as d:
        rec, client, store, lines, clock, limiter = harness(Path(d), names=['SPY', 'SPX'])
        rec.run_pass('scan', DAY, '09:35', R.ny_at(DAY, '09:35'))
        rec.run_pass('scan', DAY, '10:00', R.ny_at(DAY, '10:00'))
        rec.run_pass('scan', DAY, '10:00', R.ny_at(DAY, '10:00'))  # skipped by its marker
        spy = store.read('spot_strike', 'SPY', DAY)
        spx = store.read('spot_strike', 'SPX', DAY)
        assert spy.height == 491 * 2 and sorted(spy['_scan'].unique().to_list()) == ['09:35', '10:00']
        assert spx.height == 1100 * 2                        # three pages of 500 a scan
        assert spy.filter(pl.col('_scan') == '09:35')['strike'].n_unique() == 491
        assert store.marker('spot_strike', 'SPY', DAY, '10:00').status == 'done'


# ---- the markers ------------------------------------------------------------------------------------------------------------

def test_partial_marker_is_fetched_again_without_duplicates():
    with tempfile.TemporaryDirectory() as d:
        # the third darkpool page fails five times over (a 500 that never clears) → partial, the rows before it kept
        plan = {'/api/darkpool/SPY': [None, None, 500, 500, 500, 500, 500]}
        rec, client, store, lines, clock, limiter = harness(Path(d), fail_plan=plan, names=['SPY'])
        s = rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['darkpool'])
        m = store.marker('darkpool', 'SPY', DAY, 'eod')
        assert s['failed'] == 1 and m.status == 'partial' and 'gave up after 5 tries' in m.note
        held = rows_in(store, 'darkpool', 'SPY')
        assert 0 < held < 1300 and held % 200 == 0
        failures = (Path(d) / '_failures' / f'{DAY}.jsonl').read_text()
        assert '"endpoint":"darkpool"' in failures and TOKEN not in failures
        # the next run does not skip a partial, and the rows already held are not written twice
        s2 = rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['darkpool'])
        assert s2['skipped'] == 0 and rows_in(store, 'darkpool', 'SPY') == 1300
        assert store.marker('darkpool', 'SPY', DAY, 'eod').status == 'done'
        df = store.read('darkpool', 'SPY', DAY)
        assert df['_key'].n_unique() == 1300 and df['tracking_id'].n_unique() == 1300


def test_marker_file_shape():
    with tempfile.TemporaryDirectory() as d:
        rec, client, store, *_ = harness(Path(d), names=['SPY'])
        rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['oi_strike'])
        f = store.marker_file('oi_strike', 'SPY', DAY, 'eod')
        m = json.loads(f.read_text())
        assert m['status'] == 'done' and m['rows_fetched'] == 491 and m['rows_added'] == 491 and m['pages'] == 1
        assert m['version'] == R.VERSION and m['fetched_at'].endswith('Z')


# ---- the limiter ---------------------------------------------------------------------------------------------------------------

def test_limiter_paces_a_hundred_a_minute_on_a_fake_clock():
    clock = R.FakeClock()
    lim = R.RateLimiter(max_in_flight=3, per_minute=100, daily_budget=10_000, clock=clock)
    for _ in range(100):
        lim.acquire()
        lim.release()
    assert clock.now() == 0.0                      # the bucket starts full: a hundred at once
    lim.acquire()
    lim.release()
    assert abs(clock.now() - 0.6) < 1e-6           # the 101st waited one token's time: 60 s / 100
    for _ in range(99):
        lim.acquire()
        lim.release()
    assert abs(clock.now() - 60.0) < 1e-6          # two hundred calls take one minute
    # three threads, no spin: 300 calls in 120 fake seconds with a bounded number of sleeps
    clock2 = R.FakeClock()
    lim2 = R.RateLimiter(max_in_flight=3, per_minute=100, daily_budget=10_000, clock=clock2)

    def go():
        for _ in range(100):
            lim2.acquire()
            lim2.release()
    ts = [threading.Thread(target=go, daemon=True) for _ in range(3)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(10)
    assert not any(t.is_alive() for t in ts) and lim2.spent == 300
    assert abs(clock2.now() - 120.0) < 1e-6 and len(clock2.slept) < 1000


def test_limiter_holds_three_in_flight():
    clock = R.FakeClock()
    lim = R.RateLimiter(max_in_flight=3, per_minute=1000, daily_budget=100, clock=clock)
    lim.acquire(); lim.acquire(); lim.acquire()
    got = threading.Event()

    def fourth():
        lim.acquire()
        got.set()
    t = threading.Thread(target=fourth, daemon=True)
    t.start()
    assert not got.wait(0.6)                       # blocked while three are out
    lim.release()
    assert got.wait(2.0)                           # one came back, the fourth went
    assert lim.in_flight == 3


def test_limiter_daily_budget_stops_the_run_and_persists():
    clock = R.FakeClock()
    saved = []
    lim = R.RateLimiter(max_in_flight=3, per_minute=1000, daily_budget=5, clock=clock, spent=2, on_spend=saved.append)
    for _ in range(3):
        lim.acquire(); lim.release()
    assert saved == [3, 4, 5]
    try:
        lim.acquire()
        assert False, 'the sixth call should not go out'
    except R.BudgetExhausted as e:
        assert 'budget of 5' in str(e)
    # a pass stops cleanly, says so, and marks nothing done for what it could not ask
    with tempfile.TemporaryDirectory() as d:
        rec, client, store, lines, clock, limiter = harness(Path(d), names=['SPY', 'NVDA'], budget=4)
        s = rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['oi_strike', 'net_prem_ticks', 'chain'])
        assert s['budget_stopped'] is True and client.calls == 4
        assert any('STOP: the daily budget of 4 calls is spent' in l for l in lines.lines)
        done = sum(1 for ep in ('oi_strike', 'net_prem_ticks', 'chain') for n in ('SPY', 'NVDA')
                   if (m := store.marker(ep, n, DAY, 'eod')) and m.status == 'done')
        assert done <= 4
        assert json.loads(store.budget_file(DAY).read_text())['spent'] == 4


# ---- the retries ------------------------------------------------------------------------------------------------------------------

def test_429_waits_retry_after_5xx_backs_off_and_404_is_recorded():
    with tempfile.TemporaryDirectory() as d:
        plan = {'/api/stock/SPY/oi-per-strike': [429],                      # Retry-After 3 (the fake's), then 200
                '/api/stock/SPY/net-prem-ticks': [500, 503, 502],            # 2, 4, 8 s, then 200
                '/api/stock/SPY/ohlc/1m': [404]}                             # recorded, passed over, one call
        rec, client, store, lines, clock, limiter = harness(Path(d), fail_plan=plan, names=['SPY'])
        s = rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['oi_strike', 'net_prem_ticks', 'ohlc_1m'])
        assert sorted(x for x in clock.slept if x >= 1) == [2, 3, 4, 8]
        assert s['failed'] == 1
        assert store.marker('oi_strike', 'SPY', DAY, 'eod').status == 'done'
        assert store.marker('net_prem_ticks', 'SPY', DAY, 'eod').status == 'done'
        m = store.marker('ohlc_1m', 'SPY', DAY, 'eod')
        assert m.status == 'partial' and m.note.startswith('404')
        ohlc_calls = [p for p, _ in client.requests if p == '/api/stock/SPY/ohlc/1m']
        assert len(ohlc_calls) == 1
        assert any('waiting 3s (try 1 of 5)' in l for l in lines.lines)
        assert any('waiting 8s (try 3 of 5)' in l for l in lines.lines)
        assert any('-> 200' in l and 'try 4' in l for l in lines.lines)


def test_five_tries_then_give_up():
    with tempfile.TemporaryDirectory() as d:
        plan = {'/api/stock/SPY/oi-per-strike': [500] * 5}
        rec, client, store, lines, clock, limiter = harness(Path(d), fail_plan=plan, names=['SPY'])
        rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['oi_strike'])
        assert len([p for p, _ in client.requests if p.endswith('oi-per-strike')]) == 5
        assert sorted(x for x in clock.slept if x >= 1) == [2, 4, 8, 16]
        assert 'gave up after 5 tries' in store.marker('oi_strike', 'SPY', DAY, 'eod').note


# ---- the token -------------------------------------------------------------------------------------------------------------------------

def test_the_token_never_appears_anywhere():
    with tempfile.TemporaryDirectory() as d:
        leak = RuntimeError(f'connection reset while sending Authorization: Bearer {TOKEN} to host?token={TOKEN}')
        plan = {'/api/stock/SPY/oi-per-strike': [leak] * 5, '/api/stock/NVDA/net-prem-ticks': [leak]}
        rec, client, store, lines, clock, limiter = harness(Path(d), fail_plan=plan, names=['SPY', 'NVDA'])
        rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['oi_strike', 'net_prem_ticks'])
        assert lines.lines and any('network' in l for l in lines.lines)
        for l in lines.lines:
            assert TOKEN not in l, l
        assert any('[token]' in l for l in lines.lines)
        for f in Path(d).rglob('*'):
            if f.is_file() and f.suffix in ('.json', '.jsonl', '.log'):
                assert TOKEN not in f.read_text(encoding='utf-8'), f
        m = store.marker('oi_strike', 'SPY', DAY, 'eod')
        assert m.status == 'partial' and TOKEN not in m.note and '[token]' in m.note
    s = R.Scrub(TOKEN)
    assert s(f'Bearer {TOKEN}') == 'Bearer [token]'
    assert s(f'https://x/api?token={TOKEN}&a=1') == 'https://x/api?token=[token]&a=1'
    assert s('Bearer abcdefgh-ijkl-mnop') == 'Bearer [token]'   # a Bearer value never seen is scrubbed too
    assert s('nothing here') == 'nothing here'


def test_real_client_refuses_to_start_without_a_token():
    clock = R.FakeClock()
    try:
        R.UwClient('', R.RateLimiter(clock=clock), R.make_logger(R.Scrub(''), None, name='t2'), clock, R.Scrub(''))
        assert False
    except SystemExit as e:
        assert 'UW_API_TOKEN' in str(e)


# ---- the schema ----------------------------------------------------------------------------------------------------------------------

def test_parquet_schema_every_column_a_string_with_the_stamps_first():
    with tempfile.TemporaryDirectory() as d:
        rec, client, store, *_ = harness(Path(d), names=['SPY'])
        rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'))
        rec.run_pass('scan', DAY, '09:35', R.ny_at(DAY, '09:35'))
        for ep in R.ENDPOINTS.values():
            df = store.read(ep.key, 'SPY', DAY)
            assert df is not None and df.height > 0, ep.key
            assert df.columns[:len(R.STAMPS)] == R.STAMPS, ep.key
            assert all(t == pl.Utf8 for t in df.schema.values()), ep.key
            assert all(c in df.columns for c in ep.columns), ep.key
            assert df['_day'].unique().to_list() == [DAY] and df['_name'].unique().to_list() == ['SPY']
            assert df['_fetched_at'][0].endswith('Z') and df['_scan_at'][0].endswith('Z')
        fa = store.read('flow_alerts', 'SPY', DAY)
        assert fa['has_sweep'].unique().sort().to_list() == ['false', 'true']   # a bool as text
        assert fa['sector'].null_count() == fa.height                            # a null stays null
        assert fa['total_premium'].cast(pl.Float64).min() >= 25_000
        assert store.read('ohlc_1m', 'SPY', DAY)['market_time'].unique().sort().to_list() == ['po', 'pr', 'r']


def test_stringify_and_row_key():
    assert R.stringify(True) == 'true' and R.stringify(None) is None and R.stringify(12) == '12'
    assert R.stringify('0.2376321752265861027190332387') == '0.2376321752265861027190332387'
    assert R.stringify([1, 'a']) == '[1,"a"]' and R.stringify(-1.5461e-06) == '-1.5461e-06'
    ep = R.ENDPOINTS['darkpool']
    a = {'tracking_id': 1, 'executed_at': 't', 'price': '1', 'size': 2, 'volume': 5}
    b = dict(a, volume=9)
    assert R.row_key(ep, a) == R.row_key(ep, b)                 # the same print, a later volume: one row
    assert R.row_key(ep, a) != R.row_key(ep, dict(a, size=3))
    c = {'volume': 5}
    assert R.row_key(ep, c) != R.row_key(ep, {'volume': 6})      # no id at all: the whole row is the key


# ---- the day and the schedule ------------------------------------------------------------------------------------------------------

def test_day_bounds_and_timestamps():
    start, end = R.day_bounds('2026-10-20')
    assert R.iso_z(start) == '2026-10-20T04:00:00Z' and R.iso_z(end) == '2026-10-21T04:00:00Z'   # EDT
    s2, _ = R.day_bounds('2026-12-15')
    assert R.iso_z(s2) == '2026-12-15T05:00:00Z'                                                   # EST
    assert R.iso_z(R.parse_ts('2026-10-12T14:50:03.041370Z')) == '2026-10-12T14:50:03Z'
    assert R.iso_z(R.parse_ts(1791816594814)) == '2026-10-12T14:49:54Z'
    assert R.iso_z(R.parse_ts('1791816594814')) == '2026-10-12T14:49:54Z'
    assert R.parse_ts(None) is None and R.parse_ts('not a time') is None
    assert R.iso_z(R.ny_at('2026-10-20', '16:15')) == '2026-10-20T20:15:00Z'


def test_schedule_skips_weekends_and_holidays_and_knows_a_half_day():
    assert len(R.SCAN_TIMES) == 14 and R.SCAN_TIMES[0] == '09:35' and R.SCAN_TIMES[-1] == '15:50'
    ev = R.events_for('2026-10-20')                                  # a Tuesday
    assert [e[0] for e in ev] == R.SCAN_TIMES + ['eod'] and R.iso_z(ev[-1][2]) == '2026-10-20T20:15:00Z'
    assert R.events_for('2026-10-24') == [] and R.events_for('2026-11-26') == []   # Saturday, Thanksgiving
    half = R.events_for('2026-11-27')
    assert [e[0] for e in half] == R.HALF_DAY_SCAN_TIMES + ['eod'] and R.iso_z(half[-1][2]) == '2026-11-27T18:15:00Z'
    # from a Friday evening the next pass is Monday's 09:35
    now = R.parse_ts('2026-10-23T21:00:00Z')
    day, label, kind, when = R.next_event(now)
    assert (day, label, kind) == ('2026-10-26', '09:35', 'scan') and R.iso_z(when) == '2026-10-26T13:35:00Z'
    # mid-day: the next half hour
    day, label, kind, when = R.next_event(R.parse_ts('2026-10-20T15:01:00Z'))     # 11:01 New York
    assert (day, label, kind) == ('2026-10-20', '11:30', 'scan')
    # after 15:50 the EOD; after the EOD the next day
    assert R.next_event(R.parse_ts('2026-10-20T19:55:00Z'))[1] == 'eod'
    assert R.next_event(R.parse_ts('2026-10-20T20:16:00Z'))[0] == '2026-10-21'
    # --auto / cron: within four minutes of a scan, else the EOD once past 16:15, else nothing
    assert R.due_now(R.parse_ts('2026-10-20T13:37:00Z'))[1] == '09:35'
    assert R.due_now(R.parse_ts('2026-10-20T13:45:00Z')) is None
    assert R.due_now(R.parse_ts('2026-10-20T21:00:00Z'))[2] == 'eod'
    assert R.due_now(R.parse_ts('2026-10-24T21:00:00Z')) is None


def test_the_universe_and_the_names_file():
    assert R.DEFAULT_NAMES[:4] == ['SPX', 'SPY', 'QQQ', 'IWM'] and len(R.DEFAULT_NAMES) == 24
    assert len(set(R.DEFAULT_NAMES)) == 24 and 'GME' in R.DEFAULT_NAMES and 'SPCX' not in R.DEFAULT_NAMES
    assert R.alert_roots('SPX') == ['SPX', 'SPXW'] and R.alert_roots('SPY') == ['SPY']
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / 'names.txt'
        f.write_text('# mine\nspy\nQQQ  # the second\n\n')
        assert R.read_names(str(f)) == ['SPY', 'QQQ']


def test_budget_arithmetic_stays_under_twenty_thousand():
    """The README's arithmetic, checked: the worst day at every cap, 24 names, stays under the 20,000 budget."""
    names = 24
    scans = len(R.SCAN_TIMES) * names * R.ENDPOINTS['spot_strike'].max_pages            # every scan at its page cap
    indices = sum(1 for n in R.DEFAULT_NAMES if n in R.INDEX_NAMES)
    stocks = names - indices
    eod = (R.ENDPOINTS['flow_alerts'].max_pages * (names + indices)                      # a second root an index
           + R.ENDPOINTS['darkpool'].max_pages * stocks
           + 1 * names + 1 * stocks + 1 * names
           + R.ENDPOINTS['chain'].max_pages * stocks + R.ENDPOINTS['chain'].max_pages_index * indices)   # an index pages to 150 (.3)
    assert scans + eod < 20_000 and scans + eod == 11_751, (scans, eod)                  # the README's every-cap total
    # the expected day (what the fixtures and the live samples suggest), far smaller
    expected = len(R.SCAN_TIMES) * names + (2 * (names + indices) + 30 * stocks + names + stocks + names + 20 * names)
    assert expected < 2_500


def test_spx_book_of_824_strikes_pages_twice_and_index_alert_rows_carry_missing_periscope():
    """The smoke test of 2026-10-21: SPX's spot-exposures book is 824 strikes — page 0 answers 500 (strikes 200 →
    7660), page 1 the remaining 324 — so `page` is honoured and the walk stops on the short page (2 pages, done); and
    SPX's flow alerts (under SPX and SPXW) carry `missing_periscope`, a known column since .2, never an extra."""
    with tempfile.TemporaryDirectory() as d:
        scrub = R.Scrub(TOKEN)
        log = R.make_logger(scrub, None, stream=None, name='eod_recorder_test_spx')
        clock = R.FakeClock(dt.datetime(2026, 10, 21, 20, 15, tzinfo=R.UTC))
        limiter = R.RateLimiter(max_in_flight=3, per_minute=100, daily_budget=20_000, clock=clock)
        client = R.FakeUwClient(limiter, log, clock, scrub, counts={'spot_strike_index': 824})
        store = R.Store(Path(d))
        rec = R.Recorder(client, store, limiter, log, clock, scrub, names=['SPX'])
        s = rec.run_pass('scan', DAY, '10:00', R.ny_at(DAY, '10:00'))
        assert s['failed'] == 0 and s['incomplete'] == 0 and s['calls'] == 2
        m = store.marker('spot_strike', 'SPX', DAY, '10:00')
        assert m.status == 'done' and m.pages == 2 and m.rows_fetched == 824 and m.rows_added == 824
        pages = [(p, q.get('page')) for p, q in client.requests if p.endswith('spot-exposures/strike')]
        assert pages == [('/api/stock/SPX/spot-exposures/strike', 0), ('/api/stock/SPX/spot-exposures/strike', 1)]
        df = store.read('spot_strike', 'SPX', DAY)
        assert df.height == 824 and df['strike'].n_unique() == 824 and df['_key'].n_unique() == 824
        # the index's flow alerts: both roots, missing_periscope a known column filled 'true'
        assert 'missing_periscope' in R.FLOW_ALERT_COLUMNS
        rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['flow_alerts'])
        fa = store.read('flow_alerts', 'SPX', DAY)
        assert fa.height == 450 + 40 and sorted(fa['ticker'].unique().to_list()) == ['SPX', 'SPXW']
        assert fa['missing_periscope'].unique().to_list() == ['true']
        assert fa.columns.index('missing_periscope') < len(R.STAMPS) + len(R.FLOW_ALERT_COLUMNS)   # known, not an extra
        # a stock's rows leave it null, and an unknown column still lands as an extra after the known ones
        rec2 = R.Recorder(client, store, limiter, log, clock, scrub, names=['SPY'])
        rec2.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['flow_alerts'])
        spy = store.read('flow_alerts', 'SPY', DAY)
        assert spy['missing_periscope'].null_count() == spy.height


def test_eod_chain_walk_pages_until_a_short_page_under_the_cap():
    """The eod path asks page 0, 1, … and stops on the first page short of 500 (SPY live: page 19 held 125 rows, 20
    pages, the cap 40 untouched); the smoke path stops at one page and says so."""
    with tempfile.TemporaryDirectory() as d:
        rec, client, store, lines, clock, limiter = harness(Path(d), names=['SPY'])
        client.counts['chain'] = 9_625
        s = rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['chain'])
        pages = [q['page'] for p, q in client.requests if p.endswith('option-contracts')]
        assert pages == list(range(20)) and s['incomplete'] == 0
        m = store.marker('chain', 'SPY', DAY, 'eod')
        assert m.status == 'done' and m.pages == 20 and m.rows_fetched == 9_625 and R.ENDPOINTS['chain'].max_pages == 40
        rec.max_pages = 1
        got = rec.fetch(R.ENDPOINTS['chain'], 'SPY', DAY, clock.utcnow())
        assert got.pages == 1 and not got.complete and 'page cap 1' in got.note



# ---- since .3: the index chain's page cap, the macro stamps ----------------------------------------------------------------------------

def test_an_index_chain_takes_150_pages_and_a_stock_keeps_40():
    """2026-10-21's first real EOD pass stopped SPX's chain at the 40-page cap (20,000 rows; SPX and SPXW in one chain).
    An index name now pages to 150 (75,000 rows): a 25,000-contract SPX chain is 50 full pages and a short (empty) 51st
    — done; the same chain under a stock name still stops at 40 and is marked partial, so the next run asks it again."""
    with tempfile.TemporaryDirectory() as d:
        rec, client, store, lines, clock, limiter = harness(Path(d), names=['SPX', 'SPY'])
        client.counts['chain'] = 25_000
        s = rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['chain'])
        spx, spy = store.marker('chain', 'SPX', DAY, 'eod'), store.marker('chain', 'SPY', DAY, 'eod')
        assert spx.status == 'done' and spx.pages == 51 and spx.rows_fetched == 25_000 and rows_in(store, 'chain', 'SPX') == 25_000
        assert spy.status == 'partial' and spy.pages == 40 and 'page cap 40' in spy.note and s['incomplete'] == 1
        assert R.ENDPOINTS['chain'].max_pages_index == 150 and rec._pages(R.ENDPOINTS['chain'], 'NVDA') == 40
        # the partial is asked again by the next run; the done is skipped (the dedupe keeps the rows once)
        s2 = rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['chain'])
        assert s2['skipped'] == 1 and rows_in(store, 'chain', 'SPY') == 20_000 and rows_in(store, 'chain', 'SPX') == 25_000


def test_every_row_carries_the_macro_stamps():
    """The fixture calendar (tests/fixtures/macro_events_fixture.json via MACRO_EVENTS): 2026-10-20 holds an FOMC
    decision at 14:00 — a 10:00 scan row reads 240 minutes to it, an EOD row the day's flag and kinds with null minutes.
    The stamps are never part of a row's key: a run before the calendar existed and one after keep one row each."""
    import os
    import macro_calendar as MC
    fixture = Path(__file__).resolve().parent / 'fixtures' / 'macro_events_fixture.json'
    old = os.environ.get('MACRO_EVENTS')
    try:
        with tempfile.TemporaryDirectory() as d:
            os.environ['MACRO_EVENTS'] = str(Path(d) / 'not_yet.json')
            rec, client, store, lines, clock, limiter = harness(Path(d), names=['SPY'])
            rec.run_pass('scan', DAY, '10:00', R.ny_at(DAY, '10:00'))
            first = store.read('spot_strike', 'SPY', DAY)
            assert all(first[c].null_count() == first.height for c in MC.FIELDS)
            assert len([l for l in lines.lines if 'macro calendar' in l and 'WARN' in l]) == 1
            os.environ['MACRO_EVENTS'] = str(fixture)
            rec.run_pass('scan', DAY, '10:00', R.ny_at(DAY, '10:00'), force=True)
            again = store.read('spot_strike', 'SPY', DAY)
            assert again.height == first.height                                        # the key ignores the stamps
            rec.run_pass('scan', DAY, '10:30', R.ny_at(DAY, '10:30'))
            rec.run_pass('eod', DAY, 'eod', R.ny_at(DAY, '16:15'), only=['oi_strike', 'net_prem_ticks'])
            sc = store.read('spot_strike', 'SPY', DAY).filter(pl.col('_scan') == '10:30')
            assert sc['is_macro_event_day'].unique().to_list() == ['true'] and sc['macro_events'].unique().to_list() == ['FOMC_DECISION']
            assert sc['minutes_to_macro_release'].unique().to_list() == ['210'] and sc['minutes_since_last_release'].null_count() == sc.height
            eod = store.read('oi_strike', 'SPY', DAY)
            assert eod['is_macro_event_day'].unique().to_list() == ['true'] and eod['minutes_to_macro_release'].null_count() == eod.height
            assert eod.columns[:len(R.STAMPS)] == R.STAMPS and eod.columns[-4:] == list(MC.FIELDS)
            assert all(t == pl.Utf8 for t in eod.schema.values())
    finally:
        if old is None:
            os.environ.pop('MACRO_EVENTS', None)
        else:
            os.environ['MACRO_EVENTS'] = old

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
    print('\nall passed' if not failed else f'\n{failed} failed')
    sys.exit(1 if failed else 0)
