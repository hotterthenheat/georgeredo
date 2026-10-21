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
Since .2 (candidate 3, 15:58, the macro stamps): the macro stamps on a fixture calendar (an FOMC day at 14:00 → 60
minutes at 13:00) and a missing calendar (null, one WARN); candidate 3's 20-delta strike rule on a chain priced at a
known total vol (the deltas checked against the closed form) and its tie-break; the frozen models load (hashes checked;
a changed file refused) and score fixture rows to LightGBM's own deciles; a candidate-3 capture with VIX from Theta,
and without any VIX (the no-VIX decile the primary); the 15:58 liquidation arithmetic on a known quote; a whole default
session's calls cold (56) and warm (36) under the default budget; --spxw's SPXW-only chain, parity spot and settle.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import polars as pl  # noqa: E402

import eod_recorder as R  # noqa: E402
import paper_tracker as T  # noqa: E402
import macro_calendar as MC  # noqa: E402
import vol_model as V  # noqa: E402

TOKEN = 'TEST-TOKEN-0123456789abcdef-NEVER-SHOWN'
DAY = '2026-10-20'          # a Tuesday; the fixture's spot 773.40; an FOMC decision at 14:00 in the fixture calendar
ALL_MINUTES = ['11:30', '12:00', '12:30', '13:00', '13:30', '15:00', '15:30']      # condor_em1 and fly5 (the legacy pair)
DEFAULT_MINUTES = ['11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30']
LEGACY = T.active_candidates(keys=('condor_em1', 'fly5'))
FIXTURES = Path(__file__).resolve().parent / 'fixtures'
MACRO_FIXTURE = FIXTURES / 'macro_events_fixture.json'


def harness(root: Path, budget=24, cands=LEGACY, theta=None, macro=MACRO_FIXTURE, start=None, **fake):
    scrub = R.Scrub(TOKEN)
    log = R.make_logger(scrub, None, stream=None, name='paper_tracker_test')
    lines = R.ListHandler(scrub)
    log.addHandler(lines)
    clock = R.FakeClock(start or dt.datetime(2026, 10, 20, 15, 30, tzinfo=R.UTC))
    limiter = R.RateLimiter(max_in_flight=1, per_minute=100, daily_budget=budget, clock=clock)
    client = T.FakePaperClient(limiter, log, clock, scrub, **fake)
    store = R.Store(root)
    tr = T.Tracker(client, store, limiter, log, clock, scrub, cands=cands, theta=theta if theta is not None else T.FakeTheta(),
                   bar_wait_s=0, macro_path=macro)
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
        assert client.calls == 24 and limiter.spent == 24                         # the legacy pair alone: 24, as before
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
        plan = {'/api/stock/SPY/stock-state': [500]}          # the fake does not retry: one 500, the 11:30 state
        tr, client, store, lines, clock, limiter = harness(Path(d), fail_plan=plan, budget=80, cands=T.active_candidates(spxw=True))
        tr.log.error('a staged message: %s', tr.scrub(str(leak)))
        s = tr.capture(DAY, '11:30')
        assert s['failed'] == 1
        assert lines.lines and all(TOKEN not in l for l in lines.lines) and any('[token]' in l for l in lines.lines)
        tr.capture(DAY, '13:00')                     # candidate 3: the bars, the VIX probe, the backfill into _cache
        tr.capture(DAY, '15:00')
        tr.capture(DAY, '15:58')
        tr.settle(DAY)
        assert list((Path(d) / '_cache').rglob('*.json')) and store.read('condor_d20', 'SPY', DAY) is not None
        for f in Path(d).rglob('*'):
            if f.is_file() and f.suffix in ('.json', '.jsonl', '.log'):
                assert TOKEN not in f.read_text(encoding='utf-8'), f
            if f.is_file() and f.suffix == '.parquet':
                df = pl.read_parquet(f)
                for c in df.columns:
                    assert not df[c].str.contains(TOKEN, literal=True).fill_null(False).any(), (f, c)
        src = (Path(__file__).resolve().parents[1] / 'scripts' / 'paper_tracker.py').read_text()
        assert 'UW_API_TOKEN' in src and "os.environ.get('UW_API_TOKEN')" in src and 'Bearer' not in src   # the header is the recorder's
        for mod in ('vol_model.py', 'macro_calendar.py'):
            src = (Path(__file__).resolve().parents[1] / 'scripts' / mod).read_text()
            assert 'UW_API_TOKEN' not in src and 'Bearer' not in src and 'THETADATA' not in src      # no key reaches them


# ---- the schedule ---------------------------------------------------------------------------------------------------------------------------

def test_schedule_skips_weekends_holidays_and_half_days():
    assert T.minutes_of(DAY, LEGACY) == ALL_MINUTES and T.minutes_of(DAY) == DEFAULT_MINUTES
    ev = T.events_for(DAY)
    assert [e[0] for e in ev] == DEFAULT_MINUTES + ['15:58', '16:20'] and [e[1] for e in ev] == ['capture'] * 9 + ['close', 'settle']
    assert [e[0] for e in T.events_for(DAY, T.active_candidates(spxw=True))] == DEFAULT_MINUTES + ['15:58', '16:20']
    assert R.iso_z(ev[0][2]) == '2026-10-20T15:30:00Z' and R.iso_z(ev[-1][2]) == '2026-10-20T20:20:00Z'
    assert T.events_for('2026-10-24') == [] and T.events_for('2026-11-26') == [] and T.events_for('2026-11-27') == []   # Sat, Thanksgiving, the half day
    assert T.is_tracked_day('2026-12-24') is False and T.is_tracked_day('2026-12-28') is True
    day, label, kind, when = T.next_event(R.parse_ts('2026-10-23T21:00:00Z'))                 # Friday evening → Monday 11:30
    assert (day, label, kind) == ('2026-10-26', '11:30', 'capture')
    assert T.next_event(R.parse_ts('2026-10-20T17:31:00Z'))[1] == '14:00'                    # 13:31 New York → 14:00 (candidate 3)
    assert T.next_event(R.parse_ts('2026-10-20T17:31:00Z'), LEGACY)[1] == '15:00'
    assert T.next_event(R.parse_ts('2026-10-20T19:31:00Z'))[1:3] == ('15:58', 'close')
    assert T.next_event(R.parse_ts('2026-10-20T19:59:00Z'))[2] == 'settle'
    assert T.next_event(R.parse_ts('2026-10-20T20:21:00Z'))[0] == '2026-10-21'
    for c in T.CANDIDATES.values():
        for m in c.minutes:
            assert m in DEFAULT_MINUTES
    assert T.CANDIDATES['condor_em1'].thresholds == (60, 120) and T.CANDIDATES['fly5'].thresholds == (250,)
    assert T.CANDIDATES['condor_d20'].thresholds == (150,) and T.CANDIDATES['condor_d20'].minutes == ('13:00', '13:30', '14:00', '14:30', '15:00')
    assert [c.key for c in T.active_candidates()] == ['condor_em1', 'fly5', 'condor_d20'] and T.CANDIDATES['fly_spxw'].optional
    assert T.CANDIDATES['condor_em1'].names == ('SPY',) and T.CANDIDATES['fly5'].names == ('SPY', 'QQQ')



# ---- the macro stamps -------------------------------------------------------------------------------------------------------------------

def ny(day, hhmm):
    return R.ny_at(day, hhmm)


def test_macro_stamps_on_a_fixture_calendar():
    """2026-10-20: FOMC decision at 14:00 → at 13:00 the next release is 60 minutes away and none has passed; at 15:00
    none is ahead (null) and the last was 60 minutes ago; an EOD stamp (no time) has the day's flag and kinds, no
    minutes. 2026-10-14: CPI 08:30 and the minutes at 14:00 → 'CPI+FOMC_MINUTES', at 13:00 60 to go, 270 since.
    A cancelled release (2026-10-21's) is left out; a day with none reads 'false' and ''."""
    cal = MC.MacroCalendar.load(MACRO_FIXTURE)
    assert cal.loaded and cal.events_on(DAY) == [('14:00', 'FOMC_DECISION')]
    assert cal.stamps(DAY, ny(DAY, '13:00')) == {'is_macro_event_day': 'true', 'macro_events': 'FOMC_DECISION',
                                                  'minutes_to_macro_release': '60', 'minutes_since_last_release': None}
    assert cal.minutes_to_macro_release(ny(DAY, '13:00')) == 60 and cal.minutes_to_macro_release(ny(DAY, '14:00')) == 0
    assert cal.stamps(DAY, ny(DAY, '15:00'))['minutes_to_macro_release'] is None and cal.stamps(DAY, ny(DAY, '15:00'))['minutes_since_last_release'] == '60'
    assert cal.stamps(DAY, None) == {'is_macro_event_day': 'true', 'macro_events': 'FOMC_DECISION', 'minutes_to_macro_release': None,
                                     'minutes_since_last_release': None}
    st = cal.stamps('2026-10-14', ny('2026-10-14', '13:00'))
    assert st['macro_events'] == 'CPI+FOMC_MINUTES' and st['minutes_to_macro_release'] == '60' and st['minutes_since_last_release'] == '270'
    assert cal.stamps('2026-10-21', ny('2026-10-21', '13:00')) == {'is_macro_event_day': 'false', 'macro_events': '',
                                                                    'minutes_to_macro_release': None, 'minutes_since_last_release': None}
    assert cal.minutes_to_macro_release(ny(DAY, '13:00') + dt.timedelta(seconds=30)) == 59.5      # seconds count, two decimals


def test_a_missing_calendar_is_null_and_warns_once():
    with tempfile.TemporaryDirectory() as d:
        gone = Path(d) / 'no_calendar_here.json'
        tr, client, store, lines, clock, limiter = harness(Path(d), budget=80, macro=gone)
        tr.capture(DAY, '11:30')
        tr.capture(DAY, '12:00')
        row = store.read('condor_em1', 'SPY', DAY).to_dicts()[0]
        assert all(row[k] is None for k in MC.FIELDS)
        warns = [l for l in lines.lines if 'macro calendar' in l]
        assert len(warns) == 1 and 'WARN' in warns[0] and 'null' in warns[0]
        bad = Path(d) / 'bad.json'
        bad.write_text('{not json')
        assert MC.MacroCalendar.load(bad).loaded is False and MC.MacroCalendar.load(bad).stamps(DAY, ny(DAY, '13:00'))['is_macro_event_day'] is None


# ---- candidate 3: Hypothesis B's 20-delta rule ----------------------------------------------------------------------------------------

def _bs_call(S, K, v):
    d1 = (math.log(S / K) + 0.5 * v * v) / v
    return S * T._ncdf(d1) - K * T._ncdf(d1 - v)


def priced_chain(S=500.0, v=0.01, day=DAY, half_spread=0.005):
    """Every strike 490..510 priced at the same total vol v = σ√τ (r = q = 0) — the mid exact, the NBBO ± half a cent"""
    rows = []
    ymd = day[2:4] + day[5:7] + day[8:]
    for K in range(490, 511):
        c = _bs_call(S, K, v)
        p = c - S + K
        for right, px in (('C', c), ('P', p)):
            rows.append({'option_symbol': f'SPY{ymd}{right}{K * 1000:08d}', 'nbbo_bid': f'{max(px - half_spread, 0):.6f}',
                         'nbbo_ask': f'{px + half_spread:.6f}'})
    return T.Chain(rows, day)


def test_candidate3_delta_rule_on_a_known_vol_chain():
    """S 500, every option priced at σ√τ = 0.01. By hand: a call's delta is N(d1), d1 = (ln(S/K) + v²/2) / v — K 504:
    d1 = (ln(500/504) + 0.00005) / 0.01 = −0.7918 → 0.2142; K 505: −0.9900 → 0.1611; so the 0.20 call is 504 (gap
    0.0142 against 0.0389). A put's |delta| is 1 − N(d1) — K 496: d1 = 0.8082 → 0.2095; K 495: 1.0100 → 0.1562; the
    0.20 put is 496. Longs 2 beyond: 506 and 494. The bisection recovers the closed form to 1e-6."""
    ch = priced_chain()
    dc, dp = T.otm_deltas(ch, 500.0, 'call'), T.otm_deltas(ch, 500.0, 'put')
    assert min(dc) == 501 and max(dp) == 499 and 500 not in dc and 500 not in dp           # strictly out of the money
    for K, d in dc.items():
        assert abs(d - T._ncdf((math.log(500 / K) + 0.5e-4) / 0.01)) < 1e-6, K
    for K, d in dp.items():
        assert abs(d - (1 - T._ncdf((math.log(500 / K) + 0.5e-4) / 0.01))) < 1e-6, K
    assert round(dc[504], 4) == 0.2142 and round(dc[505], 4) == 0.1611 and round(dp[496], 4) == 0.2095 and round(dp[495], 4) == 0.1562
    assert T.nearest_delta(ch, 500.0, 'call') == (504, dc[504]) and T.nearest_delta(ch, 500.0, 'put') == (496, dp[496])
    s = T.condor_d20(ch, 500.0, 2.0)
    assert s.tradable and [(l.side, l.right, l.strike) for l in s.legs] == [('short', 'C', 504), ('long', 'C', 506), ('short', 'P', 496), ('long', 'P', 494)]
    cred = (ch.calls[504].bid - ch.calls[506].ask) + (ch.puts[496].bid - ch.puts[494].ask)
    assert close(s.price(), cred) and close(s.max_risk(), 2 - cred)
    assert s.extra['short_call_k'] == 504 and abs(s.extra['short_call_delta'] - 0.2142) < 1e-4
    # the fixture chain: 776 (0.1604; 775 is 0.2616) and 771 (0.1827; 772 is 0.2838) — credit $0.30 as condor_em1's
    f = T.condor_d20(fixture_chain(), 773.40, 2.0)
    assert f.tradable and (f.extra['short_call_k'], f.extra['short_put_k']) == (776, 771) and close(f.price(), 0.30)


def test_candidate3_tie_goes_to_the_farther_strike_and_no_quote_is_logged():
    """hyp_b's np.lexsort((-ks | ks, gap)): equal gaps → the larger call strike, the smaller put strike (gaps exact in
    binary: target 0.25, deltas 0.375 and 0.125)"""
    ch = priced_chain()
    real = T.otm_deltas
    try:
        T.otm_deltas = lambda c, S, side: {776.0: 0.375, 777.0: 0.125} if side == 'call' else {770.0: 0.125, 771.0: 0.375}
        assert T.nearest_delta(ch, 500.0, 'call', 0.25) == (777.0, 0.125) and T.nearest_delta(ch, 500.0, 'put', 0.25) == (770.0, 0.125)
    finally:
        T.otm_deltas = real
    empty = T.condor_d20(T.Chain([], DAY), 500.0)
    assert not empty.tradable and empty.legs == [] and 'no call strike with a delta' in empty.reason


# ---- the frozen model ------------------------------------------------------------------------------------------------------------------

def test_the_frozen_models_load_and_score_fixture_rows_to_known_deciles():
    rows = json.loads((FIXTURES / 't2_feature_rows.json').read_text())['rows']
    for name in (V.FULL, V.NOVIX):
        m = V.FrozenModel.load(name)
        man = json.loads((V.MODELS_DIR / f'{name}.manifest.json').read_text())
        assert m.sha == man['model_sha256'] and len(m.features) == man['n_features'] and len(m.cuts) == 9
        assert man['training_rows'] == 28750 and man['gbm_settings']['num_threads'] == 1
        mine = [r for r in rows if r['model'] == name]
        assert sorted(r['decile'] for r in mine) == list(range(1, 11))
        for r in mine:
            p, d = m.score({k: (float('nan') if v is None else v) for k, v in r['features'].items()})
            assert abs(p - r['score']) < 1e-12 and d == r['decile'], (name, r['session'], r['m'])
    full = V.FrozenModel.load(V.FULL)
    assert full.features[-1] == 'rel_vol' and 'vix' in full.features and 'vix' not in V.FrozenModel.load(V.NOVIX).features
    assert full.decile(full.cuts[0] - 1e-9) == 1 and full.decile(full.cuts[0]) == 2 and full.decile(1.0) == 10   # side='right'
    assert full.manifest['auc']['fit_oof'] == 0.613138425834206                                                # Hypothesis E's 0.613
    with tempfile.TemporaryDirectory() as d:
        for f in V.MODELS_DIR.glob('t2_spy_full*'):
            shutil.copy(f, Path(d) / f.name)
        txt = Path(d) / 't2_spy_full.txt'
        txt.write_text(txt.read_text().replace('learning_rate: 0.05', 'learning_rate: 0.06', 1))
        try:
            V.FrozenModel.load(V.FULL, Path(d))
            assert False, 'a changed model must be refused'
        except ValueError as e:
            assert 'sha256' in str(e)


def test_candidate3_capture_logs_the_decile_and_the_vix_source():
    """13:00 on a cold cache: the chain and state (shared with condor_em1), the day's bars, the UW VIX probe (422 —
    remembered for the day), the 20-session backfill — 24 calls; at 13:30 only the bars are new (3 calls). Every row
    carries both deciles, the primary (the full model: Theta's VIX gives all four VIX features) and the features."""
    with tempfile.TemporaryDirectory() as d:
        theta = T.FakeTheta()
        tr, client, store, lines, clock, limiter = harness(Path(d), budget=80, cands=T.active_candidates(), theta=theta)
        s = tr.capture(DAY, '13:00')
        assert s['failed'] == 0 and s['calls'] == 2 + 1 + 1 + 20, s
        assert sum(1 for p, _ in client.requests if p == '/api/stock/VIX/stock-state') == 1
        assert len(list((Path(d) / '_cache' / 'bars' / 'SPY').glob('*.json'))) == 20
        row = store.read('condor_d20', 'SPY', DAY).to_dicts()[0]
        assert row['structure'] == 'condor' and row['rules_version'] == T.C3_RULES_VERSION and row['delta_target'] == '0.2'
        assert (row['short_call_k'], row['short_put_k']) == ('776', '771') and row['tradable'] == 'true'
        assert row['vix_source'] == 'theta' and row['t2_primary_model'] == V.FULL and row['t2_decile_primary'] == row['t2_decile_full']
        assert row['t2_decile_full'] in [str(i) for i in range(1, 11)] and row['t2_decile_novix'] in [str(i) for i in range(1, 11)]
        assert row['f_m'] == '210' and row['f_vix'] is not None and row['f_rel_vol'] is not None and row['f_day_move_atr'] is not None
        assert row['t2_bar_complete'] == 'true' and row['t2_bar_last'] == '12:59' and row['t2_prior_sessions'] == '20'
        assert row['t2_atr_sessions'] == '14' and row['t2_relvol_sessions'] == '20' and row['t2_model_full_sha'] == V.FrozenModel.load(V.FULL).sha[:16]
        assert row['minutes_to_macro_release'] == '60' and row['macro_events'] == 'FOMC_DECISION'
        # the decile is what the frozen model gives the logged features (scored again from the row)
        m = V.FrozenModel.load(V.FULL)
        p, dd = m.score({k: float(row[f'f_{k}']) if row[f'f_{k}'] is not None else float('nan') for k in m.features})
        assert abs(p - float(row['t2_score_full'])) < 1e-5 and str(dd) == row['t2_decile_full']
        s2 = tr.capture(DAY, '13:30')
        assert s2['calls'] == 3 and sum(1 for p, _ in client.requests if p == '/api/stock/VIX/stock-state') == 1
        # the same minute again: no call, no row
        before = client.calls
        assert tr.capture(DAY, '13:00')['calls'] == 0 and client.calls == before


def test_candidate3_without_any_vix_takes_the_no_vix_decile():
    with tempfile.TemporaryDirectory() as d:
        tr, client, store, lines, clock, limiter = harness(Path(d), budget=80, cands=T.active_candidates(keys=('condor_d20',)),
                                                           theta=T.FakeTheta(up=False))
        tr.capture(DAY, '14:00')
        tr.capture(DAY, '14:30')
        rows = store.read('condor_d20', 'SPY', DAY).to_dicts()
        assert all(r['vix_source'] == 'none' and r['t2_primary_model'] == V.NOVIX and r['t2_decile_primary'] == r['t2_decile_novix'] for r in rows)
        assert all(r['f_vix'] is None and r['t2_decile_full'] is not None for r in rows)
        assert len([l for l in lines.lines if 'VIX: no source answered' in l]) == 1                # one WARN a session
        assert 'Connection refused' in (rows[0]['vix_note'] or '')
        # a bar not yet out: asked again (bar_wait_s 0 in the tests), the last close carried and said so
        tr2, client2, store2, lines2, *_ = harness(Path(d) / 'b', budget=80, cands=T.active_candidates(keys=('condor_d20',)), bars_until='14:58')
        tr2.bar_wait_s = 0.001
        tr2.capture(DAY, '15:00')
        r = store2.read('condor_d20', 'SPY', DAY).to_dicts()[0]
        assert r['t2_bar_complete'] == 'false' and r['t2_bar_asks'] == '2' and r['t2_bar_last'] == '14:57' and 'not out' in r['t2_note']


# ---- 15:58: the fly5 close quotes ---------------------------------------------------------------------------------------------------------

def test_the_1558_liquidation_arithmetic_on_a_known_quote():
    """The fixture's iron fly (credit 1.88 at the NBBO, 1.995 at the mid; short C773 and P773, long P768 and C778),
    read at 15:58 on: C773 3.10/3.20, P773 0.00/0.02, P768 0.00/0.01, C778 0.05/0.07. Liquidation at the NBBO: buy back
    the C773 at 3.20 and the P773 at 0.02, sell the C778 at 0.05, the P768 has no bid (left, no fee) → −3.17; three
    contracts closed, $1.95. P&L = (1.88 − 3.17) × 100 − 2.60 − 1.95 = −133.55. At the mid: −3.15 + 0.06 − 0.01 = −3.10
    → (1.995 − 3.10) × 100 − 4.55 = −115.05. The call fly (debit 3.27: long C768 5.60, short 2 C773, long C778) with
    C768 at 8.00/8.20: 8.00 − 2 × 3.20 + 0.05 = 1.65 → (1.65 − 3.27) × 100 − 2.60 − 2.60 = −167.20."""
    iron, call, put = T.flies5(fixture_chain(), 773.40, 5.0)
    ymd = '261020'
    q = {('C', 773): (3.10, 3.20), ('P', 773): (0.00, 0.02), ('P', 768): (0.00, 0.01), ('C', 778): (0.05, 0.07), ('C', 768): (8.00, 8.20)}
    ch = T.Chain([{'option_symbol': f'SPY{ymd}{r}{k * 1000:08d}', 'nbbo_bid': str(b), 'nbbo_ask': str(a)} for (r, k), (b, a) in q.items()], DAY)
    liq = T.liquidation(iron, ch)
    assert close(liq['liq_nbbo'], -3.17) and close(liq['liq_mid'], -3.10) and liq['legs_closed'] == 3 and close(liq['fees_close'], 1.95)
    cap = T.capture_row(T.CANDIDATES['fly5'], iron, '15:30', R.parse_ts('2026-10-20T19:30:00Z'), 773.40, {}, fixture_chain(), 1)
    r = T.close_row(cap, iron, ch, R.parse_ts('2026-10-20T19:58:00Z'))
    assert r['row_kind'] == 'close1558' and r['pnl_1558_nbbo'] == '-133.55' and r['pnl_1558_mid'] == '-115.05' and r['close_reason'] is None
    assert r['l1_ask_1558'] == '3.2' and r['l3_bid_1558'] == '0' and r['legs_closed'] == 3
    rc = T.close_row(cap, call, ch, R.parse_ts('2026-10-20T19:58:00Z'))
    assert rc['liq_nbbo'] == '1.65' and rc['pnl_1558_nbbo'] == '-167.2'
    # a leg not quoted at 15:58: no value, said
    rp = T.close_row(cap, put, ch, R.parse_ts('2026-10-20T19:58:00Z'))
    assert rp['pnl_1558_nbbo'] is None and 'not quoted at 15:58' in rp['close_reason']


def test_a_default_session_cold_then_warm_fits_the_budget_and_the_settle_carries_1558():
    """The default candidates: day one on a cold cache is 56 calls (22 chain/state + 5 bars + 1 VIX probe + 20
    backfill + 2 at 15:58 + 6 at the settle), day two 36 (the cache holds day one from its settle, the 19 before from the
    backfill); both under the default budget of 80. The settle rows carry the 15:58 exit, the capture's macro stamps and
    candidate 3's deciles; a second settle and a second 15:58 make no call."""
    with tempfile.TemporaryDirectory() as d:
        tr, client, store, lines, clock, limiter = harness(Path(d), budget=T.DEFAULT_BUDGET, cands=T.active_candidates(),
                                                           start=dt.datetime(2026, 10, 20, 20, 25, tzinfo=R.UTC))
        assert T.DEFAULT_BUDGET == 80
        for m in DEFAULT_MINUTES:
            assert tr.capture(DAY, m)['failed'] == 0, m
        assert client.calls == 22 + 5 + 1 + 20
        s = tr.capture(DAY, '15:58')
        assert s['calls'] == 2 and s['rows'] == 12 and client.calls == 50
        assert tr.capture(DAY, '15:58')['calls'] == 0
        st = tr.settle(DAY)
        assert st['calls'] == 6 and st['failed'] == 0 and limiter.spent == 56 <= T.DEFAULT_BUDGET
        assert (Path(d) / '_cache' / 'bars' / 'SPY' / f'{DAY}.json').exists()            # the settle's ohlc/1m kept for tomorrow
        fly = store.read('fly5', 'SPY', DAY)
        cl = fly.filter(pl.col('row_kind') == 'close1558')
        assert cl.height == 6 and cl['pnl_1558_nbbo'].null_count() == 0
        se = fly.filter(pl.col('row_kind') == 'settle')
        assert se.height == 6 and se['pnl_1558_nbbo'].null_count() == 0
        assert se.sort(['minute', 'structure'])['pnl_1558_nbbo'].to_list() == cl.sort(['minute', 'structure'])['pnl_1558_nbbo'].to_list()
        assert se.sort(['minute', 'structure'])['pnl_1558_mid'].to_list() == cl.sort(['minute', 'structure'])['pnl_1558_mid'].to_list()
        c3 = store.read('condor_d20', 'SPY', DAY)
        cs = c3.filter(pl.col('row_kind') == 'settle')
        assert cs.height == 5 and cs['t2_decile_primary'].null_count() == 0 and cs['pnl_nbbo'].null_count() == 0
        cap = c3.filter(pl.col('row_kind') == 'capture').sort('minute')
        assert cs.sort('minute')['minutes_to_macro_release'].to_list() == cap['minutes_to_macro_release'].to_list() == ['60', '30', '0', None, None]
        assert cs.sort('minute')['t2_decile_primary'].to_list() == cap['t2_decile_primary'].to_list()
        assert tr.settle(DAY)['calls'] == 0
        # day two, warm
        day2 = '2026-10-21'
        before = client.calls
        for m in DEFAULT_MINUTES:
            tr.capture(day2, m)
        tr.capture(day2, '15:58')
        tr.settle(day2)
        assert client.calls - before == 36 and store.budget_spent(day2) == 36
        assert all(r['t2_prior_sessions'] == '20' for r in store.read('condor_d20', 'SPY', day2).filter(pl.col('row_kind') == 'capture').to_dicts())
        e = T.status(store)
        assert e[('condor_d20', 'SPY')]['settled'] == 2 and 'condor' in e[('condor_d20', 'SPY')]['structures']
        assert e[('fly5', 'SPY')]['structures']['iron']['n_1558'] == 4


def test_spxw_flies_read_the_spxw_root_and_settle_on_the_book_price():
    """--spxw: SPX's same-day chain holds an AM SPX contract a strike (the fake's, priced absurdly) — the SPXW root alone
    is read; spot by parity (the fake's SPXW chain is the SPY fixture × 5: 773.40 → K0 3865 ±5 / ±25); no stock-state
    for SPX; the settle asks /spot-exposures/strike once and settles on its `price`"""
    with tempfile.TemporaryDirectory() as d:
        tr, client, store, lines, clock, limiter = harness(Path(d), budget=80, cands=T.active_candidates(keys=('fly_spxw',)), spx_price=3887.0)
        s = tr.capture(DAY, '15:00')
        assert s['calls'] == 1 and s['failed'] == 0 and not any(p.endswith('/SPX/stock-state') for p, _ in client.requests)
        df = store.read('fly_spxw', 'SPX', DAY)
        assert sorted(df['structure'].to_list()) == ['call25', 'call5', 'iron25', 'iron5', 'put25', 'put5']
        legs = [x for c in ('l1_symbol', 'l2_symbol', 'l3_symbol', 'l4_symbol') for x in df[c].to_list() if x]
        assert legs and all(x.startswith('SPXW') for x in legs)
        r = df.filter(pl.col('structure') == 'iron5').to_dicts()[0]
        assert r['k0'] == '3865' and r['spot_source'].startswith('parity') and 3860 < float(r['spot']) < 3870
        assert r['l3_symbol'].endswith('P03860000') and r['l4_symbol'].endswith('C03870000')
        r25 = df.filter(pl.col('structure') == 'iron25').to_dicts()[0]
        assert r25['l3_symbol'].endswith('P03840000') and r25['l4_symbol'].endswith('C03890000')
        st = tr.settle(DAY)
        assert st['calls'] == 1 and st['rows'] == 6
        se = store.read('fly_spxw', 'SPX', DAY).filter(pl.col('row_kind') == 'settle')
        assert se['settle_source'].unique().to_list() == ['spx_book_price'] and se['settle_px'][0] == '3887'
        assert tr.settle(DAY)['calls'] == 0

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
