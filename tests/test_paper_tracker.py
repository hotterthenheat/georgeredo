"""
Tests for scripts/paper_tracker.py — the fixture chain, a fake clock, no network.

Run:  python3 -I tests/test_paper_tracker.py            (plain: runs every test_* below)
      python3 -I -m pytest tests/test_paper_tracker.py -q  (where pytest is installed)

What they prove: the two strike rules land on the hand-set strikes of tests/fixtures/paper_chain_SPY.json and the
package prices are the hand-worked ones; the P&L arithmetic on a known settlement (every leg at intrinsic, $0.65 a
leg at the open, nothing at expiry, the mid and the $0.01 / $0.02 stresses); a second capture of the same minute makes
no call and adds no row, a settle twice adds nothing, and the official close arriving later adds its rows once; a
session's calls fit the budget; the token never appears in a log line, a marker, a failure record or a Parquet cell;
every column is a string with the recorder's stamps first; the schedule skips weekends, holidays and half days.
"""
from __future__ import annotations

import datetime as dt
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import polars as pl  # noqa: E402

import eod_recorder as R  # noqa: E402
import paper_tracker as T  # noqa: E402

TOKEN = 'TEST-TOKEN-0123456789abcdef-NEVER-SHOWN'
DAY = '2026-10-20'          # a Tuesday; the fixture's spot 773.40
ALL_MINUTES = ['11:30', '12:00', '12:30', '13:00', '13:30', '15:00', '15:30']


def harness(root: Path, budget=24, **fake):
    scrub = R.Scrub(TOKEN)
    log = R.make_logger(scrub, None, stream=None, name='paper_tracker_test')
    lines = R.ListHandler(scrub)
    log.addHandler(lines)
    clock = R.FakeClock(dt.datetime(2026, 10, 20, 15, 30, tzinfo=R.UTC))
    limiter = R.RateLimiter(max_in_flight=1, per_minute=100, daily_budget=budget, clock=clock)
    client = T.FakePaperClient(limiter, log, clock, scrub, **fake)
    store = R.Store(root)
    tr = T.Tracker(client, store, limiter, log, clock, scrub)
    return tr, client, store, lines, clock, limiter


def fixture_chain() -> T.Chain:
    import json
    rows = json.loads(T.DEFAULT_CHAIN_FIXTURE.read_text())['rows']
    return T.Chain(rows, '2026-10-20')


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol


# ---- the strike rules, by hand ---------------------------------------------------------------------------------------------------

def test_condor_em1_strike_rule_on_the_fixture():
    """Spot 773.40. The strike nearest spot with both sides quoted is 773 (0.40 away; 774 is 0.60). Its call is
    1.20/1.30 and its put 0.80/0.90, so the ATM straddle M = 1.25 + 0.85 = 2.10. Spot + M = 775.50 → the first listed
    strike at or above it is 776; spot − M = 771.30 → the first at or below is 771. Wings 2: longs 778 and 769."""
    ch = fixture_chain()
    assert ch.rows == 62 and ch.strikes[0] == 760 and ch.strikes[-1] == 790
    assert ch.nearest(773.40) == 773 and close(ch.straddle(773.40)[1], 2.10)
    assert ch.first_beyond(775.50, 'call') == 776 and ch.first_beyond(771.30, 'put') == 771
    assert ch.first_beyond(775.0, 'call') == 775 and ch.first_beyond(771.0, 'put') == 771    # at or beyond, as hyp_b
    s = T.condor_em1(ch, 773.40, 2.0)
    assert s.tradable and s.structure == 'condor' and s.package == 'credit' and s.k0 == 773 and close(s.straddle, 2.10)
    assert [(l.side, l.right, l.strike) for l in s.legs] == [('short', 'C', 776), ('long', 'C', 778), ('short', 'P', 771), ('long', 'P', 769)]
    # NBBO fill: shorts at the bid, longs at the ask: (0.20 − 0.07) + (0.25 − 0.08) = 0.30; mid: (0.22 − 0.06) + (0.265 − 0.07) = 0.355
    assert close(s.price(), 0.30) and close(s.price(mid=True), 0.355)
    assert close(s.price(0.01), 0.26) and close(s.price(0.02), 0.22)         # four legs a cent worse each
    assert close(s.max_risk(), 1.70)                                          # 2 − 0.30, $170 a condor
    # a tie goes to the lower strike; a spot right between 773 and 774
    assert ch.nearest(773.5) == 773
    # a straddle too narrow for a $0.05 spread is logged, not tradable
    thin = T.Chain([r for r in __import__('json').loads(T.DEFAULT_CHAIN_FIXTURE.read_text())['rows']], '2026-10-20')
    thin.calls[776] = T.Quote('SPY261020C00776000', 0.08, 0.09)             # 0.08 − 0.07 = 0.01 < 0.05
    s2 = T.condor_em1(thin, 773.40, 2.0)
    assert not s2.tradable and 'call spread credit 0.01 under 0.05' in s2.reason and len(s2.legs) == 4


def test_fly5_strike_rule_on_the_fixture():
    """K0 = 773 (the strike nearest 773.40 with both sides quoted), wings ±5 → 768 and 778.
    Iron: sell the 773 call (bid 1.20) and put (bid 0.80), buy the 768 put (ask 0.05) and the 778 call (ask 0.07):
    credit 1.88, max risk 5 − 1.88 = 3.12. Call fly: buy 768 (ask 5.60) and 778 (ask 0.07) calls, sell two 773 calls
    (bid 1.20): debit 3.27. Put fly: 768 put ask 0.05 + 778 put ask 4.85 − 2 × 0.80 = 3.30."""
    ch = fixture_chain()
    iron, call, put = T.flies5(ch, 773.40, 5.0)
    assert iron.structure == 'iron' and iron.package == 'credit' and iron.k0 == 773 and close(iron.straddle, 2.10)
    assert [(l.side, l.right, l.strike, l.qty) for l in iron.legs] == [('short', 'C', 773, 1), ('short', 'P', 773, 1), ('long', 'P', 768, 1), ('long', 'C', 778, 1)]
    assert close(iron.price(), 1.88) and close(iron.max_risk(), 3.12) and close(iron.price(mid=True), 1.995)
    assert close(iron.price(0.01), 1.84) and close(iron.price(0.02), 1.80)
    assert call.package == 'debit' and [(l.side, l.strike, l.qty) for l in call.legs] == [('long', 768, 1), ('short', 773, 2), ('long', 778, 1)]
    assert close(call.price(), 3.27) and close(call.max_risk(), 3.27) and close(call.price(mid=True), 3.11)
    assert close(call.price(0.01), 3.31)                                       # 2 × 0.01 on the longs + 2 × 0.01 on the two shorts
    assert put.package == 'debit' and close(put.price(), 3.30) and close(put.price(mid=True), 3.12)
    assert iron.tradable and call.tradable and put.tradable
    # a wing not listed: the structure is logged without legs and with its reason
    narrow = T.Chain([r for r in __import__('json').loads(T.DEFAULT_CHAIN_FIXTURE.read_text())['rows']
                      if T.parse_symbol(r['option_symbol'])[3] != 778], '2026-10-20')
    i2, c2, p2 = T.flies5(narrow, 773.40, 5.0)
    assert not i2.tradable and 'call 778 not quoted' in i2.reason and i2.legs == []
    assert not c2.tradable and p2.tradable is False and 'put 778 not quoted' in p2.reason


def test_symbol_parsing():
    assert T.parse_symbol('SPY261021C00775000') == ('SPY', '2026-10-21', 'C', 775.0)
    assert T.parse_symbol('SPXW261021P07760000') == ('SPXW', '2026-10-21', 'P', 7760.0)
    assert T.parse_symbol('QQQ261121P00612500') == ('QQQ', '2026-11-21', 'P', 612.5)
    assert T.parse_symbol('nonsense') is None and T.parse_symbol(None) is None
    ch = fixture_chain()
    assert T.Chain([{'option_symbol': 'SPY261022C00775000', 'nbbo_bid': '1', 'nbbo_ask': '2'}], '2026-10-20').rows == 0   # another expiry: out
    assert T.Chain([{'option_symbol': 'SPY261020C00775000', 'nbbo_bid': '2', 'nbbo_ask': '1'}], '2026-10-20').strikes == []  # crossed: no quote
    assert 775 in ch.calls


# ---- the P&L arithmetic on a known settlement ---------------------------------------------------------------------------------------------

def test_pnl_arithmetic_on_a_known_settlement():
    """Settlement 777.20 (the fixture's official close). Condor: the short 776 call is 1.20 in the money, every other
    leg worthless → payoff −1.20; P&L = (0.30 − 1.20) × 100 − 4 × 0.65 = −92.60 at the NBBO, (0.355 − 1.20) × 100 − 2.60
    = −87.10 at the mid. At 773.00 every leg expires worthless: +27.40 / +32.90. Iron fly: the 773 call 4.20 in →
    (1.88 − 4.20) × 100 − 2.60 = −234.60. Call fly: 9.20 − 2 × 4.20 + 0 = 0.80 → (0.80 − 3.27) × 100 − 2.60 = −249.60;
    put fly: the 778 put 0.80 in → (0.80 − 3.30) × 100 − 2.60 = −252.60."""
    ch = fixture_chain()
    c = T.condor_em1(ch, 773.40, 2.0)
    assert close(c.payoff(777.20), -1.20) and close(c.pnl(777.20), -92.60) and close(c.pnl(777.20, mid=True), -87.10)
    assert close(c.pnl(777.20, 0.01), -96.60) and close(c.pnl(777.20, 0.02), -100.60)
    assert close(c.payoff(773.00), 0.0) and close(c.pnl(773.00), 27.40) and close(c.pnl(773.00, mid=True), 32.90)
    assert close(c.pnl(779.00), (0.30 - 2.00) * 100 - 2.60)                   # the full width: −$172.60, the max loss
    iron, call, put = T.flies5(ch, 773.40, 5.0)
    assert close(iron.payoff(777.20), -4.20) and close(iron.pnl(777.20), -234.60) and close(iron.pnl(777.20, mid=True), -223.10)
    assert close(iron.pnl(773.00), 1.88 * 100 - 2.60)                        # the close on K0: the whole credit
    assert close(call.payoff(777.20), 0.80) and close(call.pnl(777.20), -249.60) and close(call.pnl(777.20, 0.01), -253.60)
    assert close(put.payoff(777.20), 0.80) and close(put.pnl(777.20), -252.60) and close(put.pnl(777.20, 0.02), -260.60)
    assert close(call.pnl(773.00), (5.00 - 3.27) * 100 - 2.60)               # the close on K0: the wing less the debit
    assert T.intrinsic(777.20, 776, 'C') == 1.20 - 0.0 or close(T.intrinsic(777.20, 776, 'C'), 1.20)
    assert T.intrinsic(777.20, 778, 'P') == 0.8 or close(T.intrinsic(777.20, 778, 'P'), 0.80)


# ---- the store: idempotent, stamped, strings, the budget ----------------------------------------------------------------------------

def test_a_session_end_to_end_is_idempotent_and_fits_the_budget():
    with tempfile.TemporaryDirectory() as d:
        tr, client, store, lines, clock, limiter = harness(Path(d))
        for m in ALL_MINUTES:
            s = tr.capture(DAY, m)
            assert s['failed'] == 0 and s['skipped'] == 0, (m, s)
        assert client.calls == 18                                                # 9 name-minutes × (chain + state)
        # the same minute again: no call, no row
        calls = client.calls
        s = tr.capture(DAY, '12:00')
        assert s['skipped'] == 1 and s['calls'] == 0 and s['rows'] == 0 and client.calls == calls
        condor = store.read('condor_em1', 'SPY', DAY)
        assert condor.height == 5 and condor['_key'].n_unique() == 5 and condor['minute'].to_list() == ALL_MINUTES[:5]
        assert condor.columns[:len(R.STAMPS)] == R.STAMPS and all(t == pl.Utf8 for t in condor.schema.values())
        assert all(c in condor.columns for c in T.COLUMNS)
        assert condor['_scan'].to_list() == ALL_MINUTES[:5] and condor['_scan_at'][0] == '2026-10-20T15:30:00Z'    # 11:30 EDT
        assert condor['spot'][0] == '773.4' and condor['straddle'][0] == '2.1' and condor['price_nbbo'][0] == '0.3'
        assert condor['l1_bid_size'].null_count() == 5                            # the route carries no sizes
        fly = store.read('fly5', 'QQQ', DAY)
        assert fly.height == 6 and sorted(fly['structure'].unique().to_list()) == ['call', 'iron', 'put']
        assert fly['l1_symbol'][0].startswith('QQQ261020')
        # the settle: 3 calls a name, the official close carried → 'official' rows, the check passes (|777.13 − 777.20| ≤ 0.25)
        s = tr.settle(DAY)
        assert s['failed'] == 0 and s['calls'] == 6 and s['official'] == 2 and s['rows'] == 5 + 6 + 6
        assert client.calls == 24 and limiter.spent == 24 == T.DEFAULT_BUDGET
        st = store.read('condor_em1', 'SPY', DAY).filter(pl.col('row_kind') == 'settle')
        assert st.height == 5 and st['settle_source'].unique().to_list() == ['official'] and st['settle_px'].unique().to_list() == ['777.2']
        assert st['pnl_nbbo'].unique().to_list() == ['-92.6'] and st['pnl_mid'].unique().to_list() == ['-87.1']
        assert st['close_1m_r'][0] == '777.13' and st['close_1m_1600'][0] == '777.39' and st['close_official'][0] == '777.2'
        assert st['check_025'].unique().to_list() == ['true'] and st['close_official_from'][0] == 'daily bar'
        assert st['l1_settle'][0] == '1.2' and st['l2_settle'][0] == '0' and st['payoff'][0] == '-1.2'
        # settle again: skipped before any call; nothing added
        s2 = tr.settle(DAY)
        assert s2['skipped'] == 2 and s2['calls'] == 0 and s2['rows'] == 0 and client.calls == 24
        assert store.read('condor_em1', 'SPY', DAY).height == 10
        # the status
        stt = T.status(store)
        e = stt[('condor_em1', 'SPY')]
        assert e['captured'] == 1 and e['settled'] == 1 and e['official'] == 1 and e['check_pass'] == 1 and e['check_n'] == 1
        assert close(e['structures']['condor']['mean_nbbo'], -92.60) and close(e['structures']['condor']['mean_mid'], -87.10)
        q = stt[('fly5', 'QQQ')]['structures']
        assert close(q['iron']['mean_nbbo'], -234.60) and close(q['call']['mean_1c'], -253.60) and close(q['put']['mean_2c'], -260.60)
        # the budget file keeps the count across runs
        assert store.budget_spent(DAY) == 24
        # a 25th call is refused: the budget is the hard stop
        try:
            limiter.acquire()
            assert False
        except R.BudgetExhausted:
            pass


def test_the_official_close_arrives_later_and_is_added_once():
    """At 16:20 the daily bar may not carry the day yet: the settle writes 'ohlc_1m_r' rows; a later --settle, the bar
    now there, adds the 'official' rows once and keeps the first ones; the status reads the official ones."""
    with tempfile.TemporaryDirectory() as d:
        tr, client, store, lines, clock, limiter = harness(Path(d), budget=40, close_official=None)
        tr.capture(DAY, '11:30')
        s = tr.settle(DAY)
        assert s['official'] == 0 and s['rows'] == 1
        st = store.read('condor_em1', 'SPY', DAY).filter(pl.col('row_kind') == 'settle')
        assert st['settle_source'].to_list() == ['ohlc_1m_r'] and st['settle_px'][0] == '777.13' and st['check_025'][0] is None
        assert st['pnl_nbbo'][0] == '-85.6'                                      # (0.30 − 1.13) × 100 − 2.60
        s2 = tr.settle(DAY)                                                      # still no daily bar: the same row, not twice
        assert s2['rows'] == 0 and s2['skipped'] == 0
        client.close_official = 777.20
        s3 = tr.settle(DAY)
        assert s3['official'] == 1 and s3['rows'] == 1
        st = store.read('condor_em1', 'SPY', DAY).filter(pl.col('row_kind') == 'settle')
        assert sorted(st['settle_source'].to_list()) == ['official', 'ohlc_1m_r'] and st.filter(pl.col('settle_source') == 'official')['pnl_nbbo'][0] == '-92.6'
        e = T.status(store)[('condor_em1', 'SPY')]
        assert e['settled'] == 1 and e['official'] == 1 and close(e['structures']['condor']['mean_nbbo'], -92.60)
        assert tr.settle(DAY)['skipped'] == 1


def test_a_tight_budget_takes_the_official_close_from_the_next_session():
    """--budget 22: the settle pass asks ohlc/1m and the state alone (4 calls, no daily bar); the official close is
    the next session's first stock-state prev_close, read off that day's capture rows. (20 cannot hold the four.)"""
    with tempfile.TemporaryDirectory() as d:
        tr, client, store, lines, clock, limiter = harness(Path(d), budget=22)
        for m in ALL_MINUTES:
            tr.capture(DAY, m)
        s = tr.settle(DAY)
        assert s['calls'] == 4 and s['official'] == 0 and s['failed'] == 0 and limiter.spent == 22
        assert not any(p.endswith('/ohlc/1d') for p, _ in client.requests)
        # the next session's captures carry prev_close 777.20 (the fake's) — SPY's at 11:30, QQQ's first at 15:00 —
        # and a later settle of DAY (its budget file reset, as a new day's would be) finds them
        client.prev_close = 777.20
        tr.capture('2026-10-21', '11:30')
        tr.capture('2026-10-21', '15:00')
        store.budget_saver(DAY)(0)
        tr._budget_day = ''
        s2 = tr.settle(DAY, with_official=False, force=True)
        assert s2['official'] == 2 and s2['failed'] == 0 and s2['calls'] == 4
        st = store.read('condor_em1', 'SPY', DAY).filter(pl.col('settle_source') == 'official')
        assert st.height == 5 and st['close_official_from'][0] == 'next session prev_close' and st['pnl_nbbo'][0] == '-92.6'


def test_a_failed_chain_call_is_recorded_and_the_minute_is_asked_again():
    with tempfile.TemporaryDirectory() as d:
        plan = {'/api/stock/SPY/option-contracts': [404]}
        tr, client, store, lines, clock, limiter = harness(Path(d), fail_plan=plan)
        s = tr.capture(DAY, '11:30')
        assert s['failed'] == 1 and store.read('condor_em1', 'SPY', DAY) is None
        m = store.marker('condor_em1', 'SPY', DAY, '11:30')
        assert m.status == 'partial' and m.note.startswith('404')
        assert '"candidate":"condor_em1"' in (Path(d) / '_failures' / f'{DAY}.jsonl').read_text()
        s2 = tr.capture(DAY, '11:30')                                             # a partial is not skipped
        assert s2['failed'] == 0 and s2['rows'] == 1 and store.marker('condor_em1', 'SPY', DAY, '11:30').status == 'done'


# ---- the token --------------------------------------------------------------------------------------------------------------------------------

def test_the_token_never_appears_anywhere():
    with tempfile.TemporaryDirectory() as d:
        leak = RuntimeError(f'reset while sending Authorization: Bearer {TOKEN} to host?token={TOKEN}')
        plan = {'/api/stock/SPY/stock-state': [500] * 5}
        tr, client, store, lines, clock, limiter = harness(Path(d), fail_plan=plan)
        tr.log.error('a staged message: %s', tr.scrub(str(leak)))
        s = tr.capture(DAY, '11:30')
        assert s['failed'] == 1
        assert lines.lines and all(TOKEN not in l for l in lines.lines) and any('[token]' in l for l in lines.lines)
        tr.capture(DAY, '15:00')
        tr.settle(DAY)
        for f in Path(d).rglob('*'):
            if f.is_file() and f.suffix in ('.json', '.jsonl', '.log'):
                assert TOKEN not in f.read_text(encoding='utf-8'), f
            if f.is_file() and f.suffix == '.parquet':
                df = pl.read_parquet(f)
                for c in df.columns:
                    assert not df[c].str.contains(TOKEN, literal=True).fill_null(False).any(), (f, c)
        src = (Path(__file__).resolve().parents[1] / 'scripts' / 'paper_tracker.py').read_text()
        assert 'UW_API_TOKEN' in src and "os.environ.get('UW_API_TOKEN')" in src and 'Bearer' not in src   # the header is the recorder's


# ---- the schedule ---------------------------------------------------------------------------------------------------------------------------

def test_schedule_skips_weekends_holidays_and_half_days():
    assert T.minutes_of(DAY) == ALL_MINUTES
    ev = T.events_for(DAY)
    assert [e[0] for e in ev] == ALL_MINUTES + ['16:20'] and [e[1] for e in ev] == ['capture'] * 7 + ['settle']
    assert R.iso_z(ev[0][2]) == '2026-10-20T15:30:00Z' and R.iso_z(ev[-1][2]) == '2026-10-20T20:20:00Z'
    assert T.events_for('2026-10-24') == [] and T.events_for('2026-11-26') == [] and T.events_for('2026-11-27') == []   # Sat, Thanksgiving, the half day
    assert T.is_tracked_day('2026-12-24') is False and T.is_tracked_day('2026-12-28') is True
    day, label, kind, when = T.next_event(R.parse_ts('2026-10-23T21:00:00Z'))                 # Friday evening → Monday 11:30
    assert (day, label, kind) == ('2026-10-26', '11:30', 'capture')
    assert T.next_event(R.parse_ts('2026-10-20T17:31:00Z'))[1] == '15:00'                    # 13:31 New York → 15:00
    assert T.next_event(R.parse_ts('2026-10-20T19:31:00Z'))[2] == 'settle'
    assert T.next_event(R.parse_ts('2026-10-20T20:21:00Z'))[0] == '2026-10-21'
    for c in T.CANDIDATES.values():
        for m in c.minutes:
            assert m in ALL_MINUTES
    assert T.CANDIDATES['condor_em1'].thresholds == (60, 120) and T.CANDIDATES['fly5'].thresholds == (250,)
    assert T.CANDIDATES['condor_em1'].names == ('SPY',) and T.CANDIDATES['fly5'].names == ('SPY', 'QQQ')


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
