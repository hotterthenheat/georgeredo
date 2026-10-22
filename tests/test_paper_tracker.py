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
The historical replay (scripts/paper_backtest.py): the Parquet-to-Chain adapter on a fixture (hand-checked strikes and
fills), a replay of fixture Parquet producing its rows (apart, source=backtest-parquet) and its report, the replay root
refused where it meets the live root. --fetch-theta against a fake Theta Terminal answering the stored 2026-10-09 in v3's
shape (data/theta_reference): the files come back equal to the stored ones; 472 / no rows / a cut stream / 473 FAILED in
the manifest, never an empty session, and the replay refuses the day; retries, the fatal statuses, no pagination; Theta's
gap, an unfinished session, a calendar disagreement; the answer's shape checked and nothing filled in; --merge-parquet
never overwrites; --verify-parquet passes the stored day and fails each broken copy (docs/fetch-theta-audit.md).
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import shutil
import sys
import tempfile
import threading
import time
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
    assert [c.key for c in T.active_candidates()] == ['condor_em1', 'fly5', 'condor_d20', 'fly_spxw']   # fly_spxw on by default (the owner's final patch)
    assert [c.key for c in T.active_candidates(spxw=False)] == ['condor_em1', 'fly5', 'condor_d20'] and T.CANDIDATES['fly_spxw'].optional
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
    backfill); both under the default budget of 90 (fly_spxw, on by default, adds 3–5: its own test). The settle rows carry the 15:58 exit, the capture's macro stamps and
    candidate 3's deciles; a second settle and a second 15:58 make no call."""
    with tempfile.TemporaryDirectory() as d:
        tr, client, store, lines, clock, limiter = harness(Path(d), budget=T.DEFAULT_BUDGET, cands=T.active_candidates(spxw=False),
                                                           start=dt.datetime(2026, 10, 20, 20, 25, tzinfo=R.UTC))
        assert T.DEFAULT_BUDGET == 90
        for m in DEFAULT_MINUTES:
            assert tr.capture(DAY, m)['failed'] == 0, m
        assert client.calls == 22 + 5 + 1 + 20
        s = tr.capture(DAY, '15:58')
        # since .3 every candidate is read again at 15:58 off the same one chain a name: SPY (condor_em1 5, condor_d20 5,
        # fly5 6) and QQQ (fly5 6) — still two calls
        assert s['calls'] == 2 and s['rows'] == 22 and client.calls == 50
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


def test_spxw_is_on_by_default_and_fits_the_budget():
    """The owner's final patch: fly_spxw is on without a flag (--no-spxw / PAPER_SPXW=0 turn it off), and a whole cold
    first day with it stays under the default budget of 90."""
    import argparse as _ap
    assert 'fly_spxw' in [c.key for c in T.active_candidates()]
    with tempfile.TemporaryDirectory() as d:
        tr, client, store, lines, clock, limiter = harness(Path(d), budget=T.DEFAULT_BUDGET, cands=T.active_candidates(),
                                                           start=dt.datetime(2026, 10, 20, 20, 25, tzinfo=R.UTC), spx_price=3887.0)
        for m in DEFAULT_MINUTES:
            assert tr.capture(DAY, m)['failed'] == 0, m
        tr.capture(DAY, '15:58')
        st = tr.settle(DAY)
        assert st['failed'] == 0 and 56 < limiter.spent <= 61 <= T.DEFAULT_BUDGET, limiter.spent


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


# ---- the historical replay (scripts/paper_backtest.py: --backtest, the report, --fetch-theta) ------------------------------------------------

import paper_backtest as B  # noqa: E402

REPLAY_MINUTES = ('11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '15:58')


def _ny_ts(day, j):
    return dt.datetime.fromisoformat(day).replace(hour=9, minute=30, tzinfo=R.NY) + dt.timedelta(minutes=j)


def write_parquet_fixture(root: Path, days, chains=('SPY', 'QQQ'), spot=773.40, close_1559=777.20, nulls=True):
    """The research's layout on a tiny scale: the paper fixture chain as Theta's 1-minute NBBO (sizes 10 bid / 12 ask; the
    P768 ask size 0), at the replay's minutes; SPY/QQQ bars closing at `spot` until the 15:59 bar closes at `close_1559`
    (the 16:00 bar empty, as Theta's is); VIX prints. With `nulls`, the C790 row at 11:30 has no quote."""
    rows = json.loads(T.DEFAULT_CHAIN_FIXTURE.read_text())['rows']
    for day in days:
        for name in chains:
            rec = {'timestamp': [], 'strike': [], 'right': [], 'bid': [], 'ask': [], 'bid_size': [], 'ask_size': [], 'mid': []}
            for hhmm in REPLAY_MINUTES:
                j = int(hhmm[:2]) * 60 + int(hhmm[3:]) - 570
                for r in rows:
                    _, _, right, k = T.parse_symbol(r['option_symbol'])
                    b, a = float(r['nbbo_bid']), float(r['nbbo_ask'])
                    if nulls and hhmm == '11:30' and k == 790 and right == 'C':
                        b = a = None
                    rec['timestamp'].append(_ny_ts(day, j)); rec['strike'].append(float(k)); rec['right'].append('CALL' if right == 'C' else 'PUT')
                    rec['bid'].append(b); rec['ask'].append(a); rec['bid_size'].append(10)
                    rec['ask_size'].append(0 if (k == 768 and right == 'P') else 12)
                    rec['mid'].append(None if b is None else (a + b) / 2)
            df = pl.DataFrame(rec, schema={'timestamp': pl.Datetime('ms', 'America/New_York'), 'strike': pl.Float64, 'right': pl.Utf8, 'bid': pl.Float64,
                                           'ask': pl.Float64, 'bid_size': pl.Int32, 'ask_size': pl.Int32, 'mid': pl.Float64})
            f = root / 'data_full' / 'chains' / name / f'{day}.parquet'
            f.parent.mkdir(parents=True, exist_ok=True)
            df.write_parquet(f)
        for name in ('SPY', 'QQQ'):
            ts = [_ny_ts(day, j) for j in range(391)]
            c = [spot] * 389 + [close_1559, None]
            df = pl.DataFrame({'timestamp': ts, 'open': c, 'high': [None if x is None else x + 0.05 for x in c], 'low': [None if x is None else x - 0.05 for x in c],
                               'close': c, 'volume': [100_000] * 390 + [0], 'count': [100] * 390 + [0], 'vwap': [spot] * 391},
                              schema={'timestamp': pl.Datetime('ms', 'America/New_York'), 'open': pl.Float64, 'high': pl.Float64, 'low': pl.Float64,
                                      'close': pl.Float64, 'volume': pl.Int64, 'count': pl.Int64, 'vwap': pl.Float64})
            f = root / 'data' / 'underlying' / name / f'{day}.parquet'
            f.parent.mkdir(parents=True, exist_ok=True)
            df.write_parquet(f)
        f = root / 'data' / 'index' / 'VIX' / f'{day}.parquet'
        f.parent.mkdir(parents=True, exist_ok=True)
        pl.DataFrame({'timestamp': [_ny_ts(day, j) for j in range(391)], 'price': [None] + [16.0 + 0.002 * j for j in range(1, 391)]},
                     schema={'timestamp': pl.Datetime('ms', 'America/New_York'), 'price': pl.Float64}).write_parquet(f)


def test_the_parquet_to_chain_adapter_lands_on_the_hand_checked_strikes_and_fills():
    """The Parquet rows at 11:30 become UW rows (OCC symbols as UW writes them, nbbo_bid/ask, the sizes) and the LIVE
    Chain and strike rules read them: spot 773.40 → the straddle 2.10 at 773 → condor shorts 776 / 771, longs 778 / 769,
    credit $0.30 at the NBBO ($0.355 at the mid); K0 773 ±5 → iron credit 1.88, call fly 3.27, put fly 3.30. A row with
    no quote is listed but not quoted; the sizes ride into the legs."""
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / 'pq'
        write_parquet_fixture(root, ['2026-10-20'])
        src = B.ParquetSource(root)
        rows = B.chain_rows(src, 'SPY', '2026-10-20', 120)
        assert len(rows) == 62 and rows[0]['option_symbol'] == 'SPY261020C00760000'
        assert B.occ('SPXW', '2026-10-20', 'PUT', 5800.0) == 'SPXW261020P05800000' and B.occ('QQQ', '2026-11-21', 'CALL', 612.5) == 'QQQ261121C00612500'
        c790 = next(r for r in rows if r['option_symbol'] == 'SPY261020C00790000')
        assert c790['nbbo_bid'] is None and c790['nbbo_ask'] is None
        ch = T.Chain(rows, '2026-10-20')
        assert ch.rows == 62 and 790 in ch.listed and 790 not in ch.calls and 790 in ch.puts
        c = T.condor_em1(ch, 773.40, 2.0)
        assert [(l.side, l.right, l.strike) for l in c.legs] == [('short', 'C', 776), ('long', 'C', 778), ('short', 'P', 771), ('long', 'P', 769)]
        assert close(c.price(), 0.30) and close(c.price(mid=True), 0.355) and c.tradable
        assert [(l.bid_size, l.ask_size) for l in c.legs] == [(10, 12)] * 4
        iron, call, put = T.flies5(ch, 773.40, 5.0)
        assert close(iron.price(), 1.88) and close(call.price(), 3.27) and close(put.price(), 3.30)
        assert next(l for l in iron.legs if l.strike == 768).ask_size == 0
        # the replay client: spot at 11:30 = the close of the bar stamped 11:29; the chain served at the clock's minute
        tr, store, client, clock = B.make_tracker(src, Path(d) / 'replay', None, ('condor_em1',))
        clock.set(R.ny_at('2026-10-20', '11:30'))
        st = client.get('/api/stock/SPY/stock-state')
        assert st.ok and st.body['data']['close'] == 773.40 and st.body['data']['tape_time'] == R.iso_z(R.ny_at('2026-10-20', '11:30'))
        ans = client.get('/api/stock/SPY/option-contracts', {'expiry': '2026-10-20', 'limit': 500, 'page': 0})
        assert ans.ok and len(ans.rows) == 62
        bars = client.get('/api/stock/SPY/ohlc/1m', {'date': '2026-10-20'})
        assert len(bars.rows) == 120 and bars.rows[0]['start_time'] == R.iso_z(R.ny_at('2026-10-20', '11:29'))   # nothing past the clock
        assert client.get('/api/stock/SPY/ohlc/1d', {'date': '2026-10-20'}).rows == []                             # no close before 16:00
        clock.set(R.ny_at('2026-10-20', '16:20'))
        assert client.get('/api/stock/SPY/ohlc/1d', {'date': '2026-10-20'}).rows[0]['close'] == 777.20             # the 15:59 bar
        assert client.get('/api/stock/VIX/stock-state').status == 422


def test_a_replay_over_fixture_parquets_writes_its_rows_apart_and_reports():
    """--settle-on 1559 (the old convention, kept so the committed reports stay reproducible). Two whole sessions
    (2026-10-19, -20), a third missing QQQ's chain (-21), two after the files end: the live tracker runs at every minute;
    the rows carry source=backtest-parquet under the replay root; the settlement is the 15:59 bar (777.20) → the condor
    −$92.60 at the NBBO (−$87.10 mid, −$96.60 / −$100.60 stressed), the iron fly −$234.60; fly5 has its 15:58 exit;
    candidate 3 its deciles; the report and its CSV say all of it; a second replay writes nothing."""
    with tempfile.TemporaryDirectory() as d:
        pq, rroot, live, out = Path(d) / 'pq', Path(d) / 'replay', Path(d) / 'paper', Path(d) / 'out'
        write_parquet_fixture(pq, ['2026-10-19', '2026-10-20'])
        write_parquet_fixture(pq, ['2026-10-21'], chains=('SPY',))
        saved = (R.HOLIDAYS, R.HALF_DAYS)
        res = B.replay('2026-10-19', '2026-10-23', T.DEFAULT_KEYS, pq, rroot, live_root=live, progress=None, settle_on='1559')
        assert (R.HOLIDAYS, R.HALF_DAYS) == saved                                            # the calendar is put back
        assert res['replayed'] == 3 and not live.exists()
        days = B.read_days(rroot)
        assert days['2026-10-21']['missing'] == [{'candidate': 'fly5', 'name': 'QQQ', 'files': ['data_full/chains/QQQ/2026-10-21.parquet']}]
        assert days['2026-10-22']['status'] == 'not in files' and 'fetch' in days['2026-10-22']['note']
        df = B.read_rows(rroot, T.DEFAULT_KEYS, '2026-10-19', '2026-10-23')
        assert df['source'].unique().to_list() == [B.SOURCE]
        em = df.filter((pl.col('candidate') == 'condor_em1') & (pl.col('row_kind') == 'settle'))
        assert em.height == 15 and em['settle_source'].unique().to_list() == ['official'] and em['settle_px'].unique().to_list() == ['777.2']
        assert em['close_official_from'].unique().to_list() == [B.OFFICIAL_FROM]
        assert em['pnl_nbbo'].unique().to_list() == ['-92.6'] and em['pnl_mid'].unique().to_list() == ['-87.1']
        assert em['pnl_1c'].unique().to_list() == ['-96.6'] and em['pnl_2c'].unique().to_list() == ['-100.6']
        fl = df.filter((pl.col('candidate') == 'fly5') & (pl.col('row_kind') == 'settle'))
        assert fl.filter(pl.col('_name') == 'QQQ')['_day'].unique().sort().to_list() == ['2026-10-19', '2026-10-20']
        iron = fl.filter(pl.col('structure') == 'iron')
        assert iron['pnl_nbbo'].unique().to_list() == ['-234.6'] and iron['pnl_1558_nbbo'].null_count() == 0
        # the 15:58 exit off the 15:58 quotes (the same fixture quotes) is the live close_row's figure
        cap = df.filter((pl.col('candidate') == 'fly5') & (pl.col('row_kind') == 'capture') & (pl.col('structure') == 'iron')).to_dicts()[0]
        ch = T.Chain(B.chain_rows(B.ParquetSource(pq), 'SPY', cap['_day'], 388), cap['_day'])
        want = T.close_row(cap, T.structure_from_row(cap), ch, R.ny_at(cap['_day'], '15:58'))['pnl_1558_nbbo']
        assert iron['pnl_1558_nbbo'].unique().to_list() == [want]
        c3 = df.filter((pl.col('candidate') == 'condor_d20') & (pl.col('row_kind') == 'capture'))
        assert c3.height == 15 and c3['vix_source'].unique().to_list() == ['theta'] and c3['t2_decile_full'].null_count() == 0
        # the first day has no VIX file for the session before (vix_chg_prev null) → the no-VIX model is its primary
        prim = dict(c3.group_by('_day').agg(pl.col('t2_primary_model').unique().first()).iter_rows())
        assert prim == {'2026-10-19': V.NOVIX, '2026-10-20': V.FULL, '2026-10-21': V.FULL}
        rep = B.build_report(rroot, T.DEFAULT_KEYS, '2026-10-19', '2026-10-23', out, stream=None)     # the root's own convention: 1559
        md = Path(rep['md']).read_text()
        assert Path(rep['md']).name == 'backtest_2026-10-19_2026-10-23.md' and Path(rep['csv']).exists()
        assert 'Results by period' not in md and 'trades_csv' not in rep                               # the old report, unchanged
        assert '| condor | 3 | 15 | 100.0% | -92.60 |' in md and '15:59 bar' in md and 'fetch' in md
        assert 'fly5 QQQ: data_full/chains/QQQ/2026-10-21.parquet' in md
        assert '| iron | 3 | 10 | 100.0% | -234.60 |' in md
        # the fill facts by hand: the condor's legs quote 0.04 + 0.02 + 0.03 + 0.02 wide = $11, slip |0.30 − 0.355| = $5.50; the
        # iron fly's 0.10 + 0.10 + 0.01 + 0.02 = $23, slip |1.88 − 1.995| = $11.50, and its long P768 shows 0 contracts on its ask
        assert '| condor | 15 | 11.00 / 11.00 | 5.50 / 5.50 | 100.0% (of 15) |' in md
        assert '| iron | 10 | 23.00 / 23.00 | 11.50 / 11.50 | 0.0% (of 10) |' in md
        cells = {(c['candidate'], c['structure']): c for c in rep['cells']}
        assert cells[('condor_em1', 'condor')]['trades'] == 15 and close(cells[('condor_em1', 'condor')]['mean_nbbo'], -92.6)
        csv = pl.read_csv(rep['csv'])
        assert {'cell', 'fills', '1558', 'decile', 'lift'} <= set(csv['section'].to_list())
        # a second replay of the same days writes no row
        n = sum(f.stat().st_size for f in rroot.rglob('*.parquet'))
        B.replay('2026-10-19', '2026-10-21', T.DEFAULT_KEYS, pq, rroot, live_root=live, progress=None, settle_on='1559')
        assert sum(f.stat().st_size for f in rroot.rglob('*.parquet')) == n
        # the root is a 1559 root: an official-close run into it is refused (their settle rows would collide)
        try:
            B.replay('2026-10-19', '2026-10-19', T.DEFAULT_KEYS, pq, rroot, live_root=live, progress=None, settle_on='official')
            assert False, 'mixed conventions in one root'
        except ValueError as e:
            assert 'settle-on 1559' in str(e)


def test_the_replay_root_is_kept_apart_from_the_live_root():
    with tempfile.TemporaryDirectory() as d:
        live = Path(d) / 'paper'
        for bad in (live, live / 'backtest'):
            try:
                B.ReplayStore(bad, live_root=live)
                assert False, 'the live root was accepted'
            except ValueError as e:
                assert 'never writes there' in str(e)
        try:
            B.ReplayStore(Path(d), live_root=live)                      # a root holding the live one
            assert False
        except ValueError:
            pass
        st = B.ReplayStore(Path(d) / 'paper_backtest', live_root=live)
        st.append(T.endpoint_for(T.CANDIDATES['condor_em1']), 'SPY', '2026-10-20', [{'row_kind': 'capture', 'minute': '11:30', 'structure': 'condor'}],
                  {'_day': '2026-10-20', '_scan': '11:30', '_scan_at': 'x', '_fetched_at': 'x', '_name': 'SPY'})
        assert st.read('condor_em1', 'SPY', '2026-10-20')['source'].to_list() == [B.SOURCE]
        # the command line refuses it too, and --status still reads the live root alone
        rc = T.main(['--backtest', '--start', '2026-10-20', '--end', '2026-10-20', '--parquet-root', d, '--data', str(live), '--backtest-data', str(live)])
        assert rc == 2
        assert T.status(R.Store(live)) == {(c.key, n): {'captured': 0, 'tradable_sessions': 0, 'settled': 0, 'official': 0, 'check_pass': 0, 'check_n': 0, 'structures': {}}
                                           for c in T.CANDIDATES.values() if not c.optional for n in c.names}


# ---- --fetch-theta, --verify-parquet, --merge-parquet (docs/fetch-theta-audit.md) -----------------------------------------------------
#
# The fake terminal answers in v3's shape (NDJSON, a flat row a line; New York wall-clock stamps "2026-10-09T09:30:00.000";
# the quote rows' symbol/expiration/strike/right/timestamp/bid_size/bid_exchange/bid/bid_condition/ask_size/ask_exchange/
# ask/ask_condition; stock bars timestamp/open/high/low/close/volume/count/vwap with 0 prices on a no-trade minute; index
# timestamp/price with 0 before the first print; 472 for no data) and its CONTENT is the stored dataset itself — the
# SDK-built files of 2026-10-09 kept in data/theta_reference — turned back into what the terminal sends. So a fetch that
# reproduces those files exactly proves the conversion end to end.

REF = Path(__file__).resolve().parents[1] / 'data' / 'theta_reference'
REF_DAY = '2026-10-09'
AFTER = dt.datetime(2026, 10, 22, 15, 0, tzinfo=R.UTC)          # 11:00 New York, the day after the window: every session over
_V3: dict = {}


def v3_template(kind, sym):
    """the reference file as the v3 terminal writes it, one NDJSON line a row, the day as @DAY@"""
    if (kind, sym) in _V3:
        return _V3[(kind, sym)]
    df = pl.read_parquet(REF / B.rel_of(kind, sym, REF_DAY))
    t = [f'@DAY@T{x}.000' for x in df['timestamp'].dt.strftime('%H:%M:%S').to_list()]
    lines = []
    if kind == 'chain':
        for ts, k, r, b, a, bs, as_ in zip(t, df['strike'], df['right'], df['bid'], df['ask'], df['bid_size'], df['ask_size']):
            lines.append(json.dumps({'symbol': sym, 'expiration': '@DAY@', 'strike': k, 'right': r, 'timestamp': ts, 'bid_size': bs,
                                     'bid_exchange': 0 if b is None else 5, 'bid': 0.0 if b is None else b, 'bid_condition': 50,
                                     'ask_size': as_, 'ask_exchange': 0 if a is None else 5, 'ask': 0.0 if a is None else a, 'ask_condition': 50}))
    elif kind == 'under':
        for ts, o, h, l, c, v, n, w in zip(t, df['open'], df['high'], df['low'], df['close'], df['volume'], df['count'], df['vwap']):
            lines.append(json.dumps({'timestamp': ts, 'open': o or 0.0, 'high': h or 0.0, 'low': l or 0.0, 'close': c or 0.0, 'volume': v, 'count': n, 'vwap': w}))
    else:
        for ts, p in zip(t, df['price']):
            lines.append(json.dumps({'timestamp': ts, 'price': p or 0.0}))
    _V3[(kind, sym)] = '\n'.join(lines) + '\n'
    return _V3[(kind, sym)]


def v3_rows(kind, sym, day=REF_DAY):
    return [json.loads(x) for x in v3_template(kind, sym).replace('@DAY@', day).splitlines()]


class _FakeThetaTerminal:
    """A Theta Terminal v3 stand-in on 127.0.0.1. `script[(path, symbol)]` is a list of what the next requests get:
    ('status', code, text), ('cut',) a 200 whose last line is cut, ('header', name, value) the answer with a header,
    ('rows', [..]) those rows, ('empty',) a 200 with no rows. `mdds` is the status route's word; `cal` the calendar's type."""

    def __init__(self):
        import http.server
        self.paths, self.queries, self.headers = [], [], []
        self.in_flight = self.max_in_flight = 0
        self.lock = threading.Lock()
        self.script: dict = {}
        self.mdds = 'CONNECTED'
        self.cal: dict = {}
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                import urllib.parse as up
                u = up.urlparse(self.path)
                q = dict(up.parse_qsl(u.query))
                with outer.lock:
                    outer.paths.append(u.path); outer.queries.append(q); outer.headers.append(dict(self.headers))
                    outer.in_flight += 1
                    outer.max_in_flight = max(outer.max_in_flight, outer.in_flight)
                    act = None
                    todo = outer.script.get((u.path, q.get('symbol')))
                    if todo:
                        act = todo.pop(0)
                try:
                    time.sleep(0.02)
                    self.answer(u.path, q, act)
                finally:
                    with outer.lock:
                        outer.in_flight -= 1

            def send(self, code, body: bytes, headers=()):
                self.send_response(code)
                for k, v in headers:
                    self.send_header(k, v)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def answer(self, path, q, act):
                if path == '/v3/terminal/mdds/status':
                    return self.send(200, outer.mdds.encode())
                if path == '/v3/calendar/on_date':
                    return self.send(200, (json.dumps({'type': outer.cal.get(q['date'], 'open'), 'open': '09:30:00', 'close': '16:00:00'}) + '\n').encode())
                if act and act[0] == 'status':
                    return self.send(act[1], act[2].encode())
                if act and act[0] == 'empty':
                    return self.send(200, b'')
                day = f'{q["date"][:4]}-{q["date"][4:6]}-{q["date"][6:]}' if 'date' in q else f'{q["start_date"][:4]}-{q["start_date"][4:6]}-{q["start_date"][6:]}'
                kind = {'/v3/option/history/quote': 'chain', '/v3/stock/history/ohlc': 'under', '/v3/index/history/price': 'index'}.get(path)
                if kind is None:
                    return self.send(404, b'NO_IMPL')
                if act and act[0] == 'rows':
                    body = ('\n'.join(json.dumps(r) for r in act[1]) + '\n').encode()
                else:
                    body = v3_template(kind, q['symbol']).replace('@DAY@', day).encode()
                if act and act[0] == 'cut':
                    body = body[:len(body) // 2]
                return self.send(200, body, [act[1:]] if act and act[0] == 'header' else ())

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.base = f'http://127.0.0.1:{self.server.server_address[1]}/v3'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def fetcher(self, **kw):
        return B.ThetaFetch(self.base, waits=(0, 0, 0, 0), **kw)

    def data_queries(self):
        return [q for p, q in zip(self.paths, self.queries) if not p.startswith('/v3/terminal/') and not p.startswith('/v3/calendar/')]

    def close(self):
        self.server.shutdown()


def test_the_theta_fetch_reproduces_the_stored_day_exactly_and_places_it_safely():
    """--fetch-theta against a fake terminal answering the stored 2026-10-09 in v3's shape: 127.0.0.1 only ("localhost"
    refused), the terminal's status asked first, the calendar asked, format=ndjson on every data call, no key or
    Authorization header ever sent, at most 3 in flight, the stock bars on venue nqb (what the stored files were asked
    with); the seven files come back EQUAL to the stored ones (schema, keys, every value; the 09:30 no-quote rows null,
    the 16:00 no-trade bar's prices null, SPX's 09:30 null); every file's manifest says ok with its request and hash; a
    second run asks nothing; --force on a changed file keeps the old beside it; and the replay reads the fetched day as
    it reads the stored one."""
    for bad in ('http://localhost:25503/v3', 'https://127.0.0.1:25503/v3', 'http://0.0.0.0:25503/v3'):
        try:
            B.ThetaFetch(bad)
            assert False, f'{bad} accepted'
        except ValueError:
            pass
    term = _FakeThetaTerminal()
    try:
        with tempfile.TemporaryDirectory() as d:
            pq = Path(d) / 'pq'
            res = B.fetch_theta(REF_DAY, REF_DAY, pq, stream=None, fetcher=term.fetcher(), now=AFTER)
            assert res['rc'] == 0 and len(res['written']) == 7 and not res['failed'] and not res['incomplete'], res
            assert term.paths[0] == '/v3/terminal/mdds/status' and term.paths[1] == '/v3/calendar/on_date'
            assert res['calendar'][REF_DAY] == {'recorder': 'full', 'theta': 'open', 'error': None}
            dq = term.data_queries()
            assert len(dq) == 7 and all(q.get('format') == 'ndjson' for q in dq) and 1 <= term.max_in_flight <= 3
            assert not any(k.lower() in ('authorization', 'apikey', 'api_key', 'x-api-key') for h in term.headers for k in h)
            assert not any('key' in k.lower() for q in term.queries for k in q)
            under = [q for q in dq if 'venue' in q]
            assert len(under) == 2 and {q['venue'] for q in under} == {'nqb'} and all(q['start_date'] == q['end_date'] == '20261009' for q in under)
            ch = [q for q in dq if 'expiration' in q]
            assert {q['symbol'] for q in ch} == {'SPY', 'QQQ', 'SPXW'} and all(q['expiration'] == q['date'] == '20261009' and q['interval'] == '1m'
                                                                                  and q['start_time'] == '09:30:00' and q['end_time'] == '16:00:00' for q in ch)
            for kind, sym in [(j['kind'], j['sym']) for j in B.fetch_jobs(REF_DAY)]:
                rel = B.rel_of(kind, sym, REF_DAY)
                c = B.compare_frames(kind, pl.read_parquet(pq / rel), pl.read_parquet(REF / rel))
                assert c['equal'], (rel, c)
            m = B.read_manifest(pq, REF_DAY)
            assert m['session'] == 'full' and m['theta_calendar'] == 'open' and set(m['files']) == {B.rel_of(j['kind'], j['sym'], REF_DAY) for j in B.fetch_jobs(REF_DAY)}
            e = m['files']['data/underlying/SPY/2026-10-09.parquet']
            assert e['status'] == 'ok' and e['venue'] == 'nqb' and e['request']['http'] == 200 and len(e['sha256']) == 64 and e['placed'] == 'placed'
            assert B.verify_parquet(pq, REF_DAY, REF_DAY, prior=False, compare_root=REF, stream=None)['ok']
            # a second run: every file on disk, nothing asked but the status and the calendar
            n0 = len(term.data_queries())
            again = B.fetch_theta(REF_DAY, REF_DAY, pq, stream=None, fetcher=term.fetcher(), now=AFTER)
            assert again['rc'] == 0 and len(again['skipped']) == 7 and len(term.data_queries()) == n0
            # --force over a file that differs: the old one kept beside, the new placed; over an identical one: left as it was
            f = pq / 'data/index/VIX/2026-10-09.parquet'
            old = pl.read_parquet(f).with_columns(pl.col('price') + 1)
            old.write_parquet(f)
            forced = B.fetch_theta(REF_DAY, REF_DAY, pq, stream=None, fetcher=term.fetcher(), now=AFTER, force=True, only=B.parse_only('VIX-index,SPX-index'))
            assert forced['rc'] == 0 and forced['written'] == ['data/index/VIX/2026-10-09.parquet'] and forced['identical'] == ['data/index/SPX/2026-10-09.parquet']
            prev = list(f.parent.glob('2026-10-09.parquet.prev-*'))
            assert len(prev) == 1 and pl.read_parquet(prev[0]).equals(old) and B.compare_frames('index', pl.read_parquet(f), pl.read_parquet(REF / 'data/index/VIX/2026-10-09.parquet'))['equal']
            assert B.read_manifest(pq, REF_DAY)['files']['data/index/VIX/2026-10-09.parquet']['tries'] == 2
            # the replay reads the fetched day exactly as the stored one
            caps = []
            for root in (pq, REF):
                B.replay(REF_DAY, REF_DAY, ('condor_em1',), root, Path(d) / f'replay_{len(caps)}', progress=None)
                caps.append(B.read_rows(Path(d) / f'replay_{len(caps)}', ('condor_em1',), REF_DAY, REF_DAY).filter(pl.col('row_kind') == 'capture')
                            .select('minute', 'l1_symbol', 'l2_symbol', 'l3_symbol', 'l4_symbol', 'price_nbbo', 'price_mid', 'spot').sort('minute'))
            assert caps[0].height == 5 and caps[0].equals(caps[1])
    finally:
        term.close()


def test_a_session_without_data_is_failed_never_an_empty_session():
    """A 472 for a day the calendar calls a session, a 200 with no rows, a cut stream that never comes whole, a 473: each
    is FAILED in the day's manifest with its request, nothing is placed, the run exits 1; --verify-parquet fails the day;
    and the replay calls the day refused — never a holiday, never an empty session."""
    term = _FakeThetaTerminal()
    day = '2026-10-12'                                                     # Columbus Day: the equity and option markets open
    assert B.session_of(day) == {'kind': 'full', 'close_j': 390}
    term.script[('/v3/stock/history/ohlc', 'SPY')] = [('status', 472, 'No data for the specified timeframe')]
    term.script[('/v3/index/history/price', 'VIX')] = [('empty',)]
    term.script[('/v3/index/history/price', 'SPX')] = [('cut',)] * 5
    term.script[('/v3/stock/history/ohlc', 'QQQ')] = [('status', 473, 'Invalid params')]
    try:
        with tempfile.TemporaryDirectory() as d:
            pq = Path(d) / 'pq'
            res = B.fetch_theta(day, day, pq, stream=None, fetcher=term.fetcher(), now=AFTER, only=B.parse_only('SPY-underlying,QQQ-underlying,SPX-index,VIX-index'))
            assert res['rc'] == 1 and not res['written']
            why = {x['file']: x['error'] for x in res['failed']}
            assert '472 NO_DATA for a day the calendar calls a session' in why['data/underlying/SPY/2026-10-12.parquet']
            assert 'no rows' in why['data/index/VIX/2026-10-12.parquet'] and 'cut' in why['data/index/SPX/2026-10-12.parquet']
            assert '473' in why['data/underlying/QQQ/2026-10-12.parquet']
            m = B.read_manifest(pq, day)['files']
            assert m['data/index/SPX/2026-10-12.parquet']['request']['attempts'] == 5 and m['data/index/SPX/2026-10-12.parquet']['request']['statuses'] == [0] * 5
            assert m['data/underlying/QQQ/2026-10-12.parquet']['request']['attempts'] == 1                # 473 is not asked again
            assert all(e['status'] == 'FAILED' for e in m.values()) and not list((pq / 'data').rglob('*.parquet'))
            rep = B.verify_parquet(pq, day, day, prior=False, stream=None)
            assert not rep['ok'] and any('472' in f for f in rep['fails'])
            # the replay over a root holding the session after it: the day is refused, not a holiday
            write_parquet_fixture(pq, ['2026-10-13'])
            B.replay('2026-10-12', '2026-10-13', ('condor_em1',), pq, Path(d) / 'replay', progress=None)
            days = B.read_days(Path(d) / 'replay')
            assert days['2026-10-12']['status'] == 'refused' and '472' in days['2026-10-12']['refused']['data/underlying/SPY/2026-10-12.parquet']
            assert days['2026-10-13']['status'] == 'replayed'
    finally:
        term.close()


def test_theta_statuses_are_retried_stopped_or_failed_and_never_paged():
    """429 / 571 / a cut stream are asked again and then taken; 473 fails at once; a Next-Page header fails (v3 does not
    page); 478 (another terminal took the key's session) stops every call after it without asking; a refused connection
    stops the run; a terminal that is not CONNECTED means nothing is asked."""
    term = _FakeThetaTerminal()
    try:
        th = term.fetcher()
        p = {'symbol': 'VIX', 'date': '20261009', 'interval': '1m', 'start_time': '09:30:00', 'end_time': '16:00:00'}
        term.script[('/v3/index/history/price', 'VIX')] = [('status', 429, 'OS_LIMIT'), ('status', 571, 'SERVER_STARTING'), ('cut',)]
        a = th.get('/index/history/price', p)
        assert a.ok and a.attempts == 4 and a.statuses == [429, 571, 0, 200] and len(a.rows) == 391
        term.script[('/v3/index/history/price', 'VIX')] = [('header', 'Next-Page', 'http://127.0.0.1/v3/next?x=1')]
        a = th.get('/index/history/price', p)
        assert not a.ok and a.status == 477 and 'paginated' in a.error
        term.script[('/v3/index/history/price', 'VIX')] = [('header', 'Next-Page', 'null')]
        assert th.get('/index/history/price', p).ok                                    # "null" is no next page
        term.script[('/v3/index/history/price', 'VIX')] = [('status', 478, 'INVALID_SESSION_ID')]
        n = len(term.paths)
        a = th.get('/index/history/price', p)
        assert a.fatal and a.status == 478 and th.stopped and len(term.paths) == n + 1
        b = th.get('/index/history/price', p)
        assert b.status == 'stopped' and len(term.paths) == n + 1                    # never asked
        # a refused connection: the run stops
        import socket
        s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
        dead = B.ThetaFetch(f'http://127.0.0.1:{port}/v3', waits=(0,))
        assert dead.get('/index/history/price', p).status == -1 and dead.stopped
        # not CONNECTED: nothing asked beyond the status route
        term.mdds = 'DISCONNECTED'
        n = len(term.paths)
        with tempfile.TemporaryDirectory() as d:
            res = B.fetch_theta(REF_DAY, REF_DAY, Path(d), stream=None, fetcher=term.fetcher(), now=AFTER)
        assert res['rc'] == 1 and 'not CONNECTED' in res['aborted'] and len(term.paths) == n + 1
    finally:
        term.close()


def test_the_fetch_waits_out_thetas_gap_unfinished_sessions_and_calendar_disagreements():
    """Inside Theta's gap (00:00–01:45 New York) nothing is asked, not even the status; a session not yet over is not
    asked; a day the terminal's calendar calls something else than the recorder's is FAILED with no data call; a holiday
    is never asked."""
    term = _FakeThetaTerminal()
    try:
        with tempfile.TemporaryDirectory() as d:
            gap = dt.datetime(2026, 10, 22, 5, 30, tzinfo=R.UTC)                # 01:30 New York
            res = B.fetch_theta('2026-10-12', '2026-10-21', Path(d), stream=None, fetcher=term.fetcher(), now=gap)
            assert 'gap' in res['aborted'] and res['calls'] == 0 and not term.paths
            mid = dt.datetime(2026, 10, 21, 19, 0, tzinfo=R.UTC)                # 15:00 New York on the 21st
            res = B.fetch_theta('2026-10-21', '2026-10-21', Path(d), stream=None, fetcher=term.fetcher(), now=mid, only=B.parse_only('VIX-index'))
            assert res['rc'] == 1 and 'not over' in res['not_asked'][0]['error'] and not term.data_queries()
            term.cal['20261013'] = 'full_close'
            res = B.fetch_theta('2026-10-13', '2026-10-13', Path(d), stream=None, fetcher=term.fetcher(), now=AFTER, only=B.parse_only('VIX-index'))
            assert res['rc'] == 1 and 'calendars disagree' in res['failed'][0]['error'] and not term.data_queries()
            res = B.fetch_theta('2026-11-26', '2026-11-26', Path(d), stream=None, fetcher=term.fetcher(), now=dt.datetime(2026, 11, 27, 15, 0, tzinfo=R.UTC))
            assert res['holidays'] == ['2026-11-26'] and not term.data_queries() and B.read_manifest(Path(d), '2026-11-26')['session'] == 'holiday'
            assert [B.session_of(x)['kind'] for x in ('2026-10-12', '2026-11-11', '2026-11-27', '2026-10-17', '2025-12-25')] == ['full', 'full', 'half', 'weekend', 'unknown']
    finally:
        term.close()


def test_the_answer_shape_is_checked_and_nothing_is_filled_in():
    """frame_of / validate_frame on the real rows: a quote field under another name, a right that is neither call nor
    put, another expiry or root, a stamp that does not parse — each a problem (FAILED), never a value made up; 'call',
    'C', 'PUT' all read; the no-quote minute (0 / 0, sizes 0) null but a 0 bid with an ask kept; the no-trade bar's prices
    null, its session VWAP kept; an index 0 null; strikes in thousandths, a duplicate, a minute short of contracts, a
    day's volume a tenth of the norm — each INCOMPLETE."""
    rows = v3_rows('chain', 'SPY')
    df, probs = B.frame_of('chain', rows, REF_DAY, 'SPY')
    assert not probs and B.compare_frames('chain', df, pl.read_parquet(REF / 'data_full/chains/SPY/2026-10-09.parquet'))['equal']
    assert B.validate_frame('chain', 'SPY', REF_DAY, df)[0] == 'ok'
    renamed = [dict({k: v for k, v in r.items() if k not in ('bid', 'ask')}, bid_price=r['bid'], ask_price=r['ask']) for r in rows[:2000]]
    _, probs = B.frame_of('chain', renamed, REF_DAY, 'SPY')
    assert any('fields missing: bid in 2000 rows, ask in 2000 rows' in p for p in probs)
    r0 = dict(rows[1000])
    lower = [dict(r0, right='call'), dict(r0, right='C', strike=r0['strike'] + 1), dict(r0, right='PUT'), dict(r0, right='X', strike=1.0)]
    df2, probs = B.frame_of('chain', lower, REF_DAY, 'SPY')
    assert df2['right'].to_list().count('CALL') == 2 and df2['right'].to_list().count('PUT') == 1 and any('neither call nor put: 1' in p for p in probs)
    _, probs = B.frame_of('chain', [dict(r0, expiration='2026-10-16'), dict(r0, symbol='SPX')], REF_DAY, 'SPY')
    assert any('expirations other than the day' in p for p in probs) and any('roots other than SPY' in p for p in probs)
    _, probs = B.frame_of('chain', [dict(r0, timestamp='20261009 09:31')], REF_DAY, 'SPY')
    assert any('stamps that do not parse' in p for p in probs)
    q = B.frame_of('chain', [dict(r0, bid=0.0, ask=0.0, bid_size=0, ask_size=0), dict(r0, bid=0.0, ask=0.05, bid_size=0, ask_size=10, strike=1.0)], REF_DAY, 'SPY')[0]
    assert q.filter(pl.col('strike') == 1.0)['bid'].to_list() == [0.0] and q.filter(pl.col('strike') != 1.0)['bid'].to_list() == [None]
    b = B.frame_of('under', [{'timestamp': '2026-10-09T16:00:00.000', 'open': 0.0, 'high': 0.0, 'low': 0.0, 'close': 0.0, 'volume': 0, 'count': 0, 'vwap': 777.65}], REF_DAY)[0]
    assert b['close'].to_list() == [None] and b['vwap'].to_list() == [777.65]
    assert B.frame_of('index', [{'timestamp': '2026-10-09T09:30:00.000', 'price': 0.0}], REF_DAY)[0]['price'].to_list() == [None]
    # thousandths (the v2 unit), with and without a norm
    k = df.with_columns(pl.col('strike') * 1000)
    assert B.validate_frame('chain', 'SPY', REF_DAY, k)[0] == 'INCOMPLETE'
    st, _, probs = B.validate_frame('chain', 'SPY', REF_DAY, k, {'strike_mid': 700.0})
    assert st == 'INCOMPLETE' and any('strike units' in p for p in probs)
    st, ck, probs = B.validate_frame('chain', 'SPY', REF_DAY, pl.concat([df, df.head(3)]))
    assert st == 'INCOMPLETE' and ck['duplicates'] == 3
    short = df.filter(~((pl.col('timestamp').dt.hour() == 12) & (pl.col('timestamp').dt.minute() == 0) & (pl.col('strike') > 700)))
    assert any('hold under 99%' in p for p in B.validate_frame('chain', 'SPY', REF_DAY, short)[2])
    u = pl.read_parquet(REF / 'data/underlying/SPY/2026-10-09.parquet')
    assert B.validate_frame('under', 'SPY', REF_DAY, u, {'volume': u['volume'].sum() * 1.0})[0] == 'ok'
    st, _, probs = B.validate_frame('under', 'SPY', REF_DAY, u.with_columns(pl.col('volume') // 10), {'volume': u['volume'].sum() * 1.0})
    assert st == 'INCOMPLETE' and any('another venue' in p for p in probs)


def test_merge_checks_everything_first_and_never_overwrites():
    """--merge-parquet: a clean layout is copied whole with each file's manifest entry; a second merge (every target
    there, identical) copies nothing and exits 1 listing the overlap; a target that differs stops it too, and --force
    replaces it keeping the old one beside; a file its manifest calls INCOMPLETE, or one that fails validation, stops
    the whole merge before anything is copied; the source is never changed."""
    import shutil
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / 'src', Path(d) / 'dst'
        shutil.copytree(REF, src)
        before = {f: B.sha256_of(f) for f in src.rglob('*.parquet')}
        r = B.merge_parquet(src, dst, stream=None)
        assert r['rc'] == 0 and len(r['copied']) == 7 and not r['refused']
        assert B.read_manifest(dst, REF_DAY)['files']['data/index/VIX/2026-10-09.parquet']['status'] == 'ok'
        r = B.merge_parquet(src, dst, stream=None)
        assert r['rc'] == 1 and len(r['identical']) == 7 and not r['copied']
        f = dst / 'data/index/SPX/2026-10-09.parquet'
        pl.read_parquet(f).with_columns(pl.col('price') * 2).write_parquet(f)
        r = B.merge_parquet(src, dst, stream=None)
        assert r['rc'] == 1 and r['overlap'] == ['data/index/SPX/2026-10-09.parquet'] and not r['copied']
        r = B.merge_parquet(src, dst, force=True, stream=None)
        assert r['rc'] == 0 and r['copied'] == ['data/index/SPX/2026-10-09.parquet (replaced)'] and len(list(f.parent.glob('*.prev-*'))) == 1
        # a refusal anywhere: nothing copied
        dst2 = Path(d) / 'dst2'
        B.write_manifest(src, REF_DAY, {'data/index/VIX/2026-10-09.parquet': {'status': 'INCOMPLETE', 'problems': ['planted']}})
        g = src / 'data/underlying/QQQ/2026-10-09.parquet'
        pl.read_parquet(g).head(200).write_parquet(g)
        before[g] = B.sha256_of(g)
        r = B.merge_parquet(src, dst2, stream=None)
        assert r['rc'] == 1 and not r['copied'] and not dst2.exists()
        assert {x['file'] for x in r['refused']} == {'data/index/VIX/2026-10-09.parquet', 'data/underlying/QQQ/2026-10-09.parquet'}
        assert {f: B.sha256_of(f) for f in src.rglob('*.parquet')} == before


def test_verify_parquet_passes_the_stored_day_and_fails_every_broken_copy():
    """--verify-parquet on the stored 2026-10-09: PASS (the sessions-before check off — the folder holds one day), and
    compared to itself equal; with the sessions before asked, the 20 SPY sessions and VIX's are missing → FAIL; then
    each break on a copy fails alone: 30 minutes cut, a duplicated row, a session's file deleted, the bars padded empty
    (what Theta's stock route answers for a day it has no trades for), the manifest calling a file FAILED."""
    import shutil
    rep = B.verify_parquet(REF, REF_DAY, REF_DAY, prior=False, compare_root=REF, stream=None)
    assert rep['ok'] and all(r['compare']['equal'] for r in rep['rows'] if 'compare' in r)
    rep = B.verify_parquet(REF, REF_DAY, REF_DAY, stream=None)
    assert not rep['ok'] and any('prior SPY bars: 20 sessions' in f for f in rep['fails']) and any('prior VIX' in f for f in rep['fails'])
    breaks = {
        'data_full/chains/SPY/2026-10-09.parquet': lambda c: c.filter(~((c['timestamp'].dt.hour() == 13) & (c['timestamp'].dt.minute() < 30))),
        'data_full/chains/QQQ/2026-10-09.parquet': lambda c: pl.concat([c, c.tail(1)]),
        'data/underlying/QQQ/2026-10-09.parquet': lambda b: b.with_columns([pl.lit(None, pl.Float64).alias(x) for x in ('open', 'high', 'low', 'close')]),
        'data/index/VIX/2026-10-09.parquet': None,
    }
    for rel, fn in breaks.items():
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'r'
            shutil.copytree(REF, root)
            if fn is None:
                (root / rel).unlink()
            else:
                fn(pl.read_parquet(root / rel)).write_parquet(root / rel)
            rep = B.verify_parquet(root, REF_DAY, REF_DAY, prior=False, stream=None)
            assert not rep['ok'] and len(rep['fails']) == 1 and rep['fails'][0].startswith(rel), (rel, rep['fails'])
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / 'r'
        shutil.copytree(REF, root)
        B.write_manifest(root, REF_DAY, {'data/index/SPX/2026-10-09.parquet': {'status': 'FAILED', 'error': 'planted'}})
        rep = B.verify_parquet(root, REF_DAY, REF_DAY, prior=False, stream=None)
        assert not rep['ok'] and rep['fails'] == ['data/index/SPX/2026-10-09.parquet: the manifest: FAILED: planted']
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            assert T.main(['--verify-parquet', '--start', REF_DAY, '--end', REF_DAY, '--parquet-root', str(root), '--no-prior']) == 1
        assert 'verify-parquet: FAIL (1)' in buf.getvalue()


def test_the_replay_reads_a_refused_file_as_absent_and_a_missing_session_is_not_a_holiday():
    """A file its manifest calls INCOMPLETE is absent to the replay even though it is on disk (VIX here: candidate 3
    falls to the no-VIX decile and the day says so); from the recorder's calendar's first year a weekday session with no
    SPY file is 'missing files', never a holiday (before the calendar's years the files still say what a holiday is)."""
    with tempfile.TemporaryDirectory() as d:
        pq = Path(d) / 'pq'
        write_parquet_fixture(pq, ['2026-10-19', '2026-10-21'])
        B.write_manifest(pq, '2026-10-21', {'data/index/VIX/2026-10-21.parquet': {'status': 'INCOMPLETE', 'problems': ['planted']}})
        B.replay('2026-10-19', '2026-10-21', T.DEFAULT_KEYS, pq, Path(d) / 'replay', progress=None)
        days = B.read_days(Path(d) / 'replay')
        assert days['2026-10-20']['status'] == 'missing files'
        assert days['2026-10-21']['status'] == 'replayed' and 'no VIX file' in days['2026-10-21']['note']
        c3 = B.read_rows(Path(d) / 'replay', ('condor_d20',), '2026-10-21', '2026-10-21').filter(pl.col('row_kind') == 'capture')
        assert c3.height == 5 and c3['t2_primary_model'].unique().to_list() == [V.NOVIX]
        pq2 = Path(d) / 'pq2'
        write_parquet_fixture(pq2, ['2025-12-22', '2025-12-24'])
        B.replay('2025-12-22', '2025-12-24', ('condor_em1',), pq2, Path(d) / 'replay2', progress=None)
        assert B.read_days(Path(d) / 'replay2')['2025-12-23']['status'] == 'holiday'


# ---- the audit's corrections as the defaults (2026-10-22; scripts/paper_audit.py) -------------------------------------------------------

import paper_audit as PA  # noqa: E402
import daily_forward as DF  # noqa: E402

AUDIT_DIR = Path(__file__).resolve().parents[1] / 'research_notes' / 'Compass phase 3' / 'backtest_audit'


def _import_audit(name):
    """the audit's own modules, imported read-only (no bytecode written into its folder)"""
    sys.dont_write_bytecode = True
    if str(AUDIT_DIR) not in sys.path:
        sys.path.insert(0, str(AUDIT_DIR))
    import importlib
    return importlib.import_module(name)


def uw_close_file(d: Path, rows):
    """a UW daily-bar file as data/official_closes keeps them: (ticker, date, market_time, close[, low, high, open])"""
    d.mkdir(parents=True, exist_ok=True)
    recs = [{'ticker': t, 'date': day, 'market_time': mt, 'close': str(c), 'open': str(o if o is not None else c), 'high': str(h if h is not None else c),
             'low': str(lo if lo is not None else c), 'total_volume': '1', 'volume': '1'} for t, day, mt, c, lo, h, o in rows]
    pl.DataFrame(recs).write_parquet(d / 'uw_ohlc_1d_test.parquet')


def test_period_labels_at_the_boundaries():
    """AUDIT.md section 5, one function for the rows and the report: condor_d20 i-a to 2024-06-30, i-b from 2024-07-01 to
    2024-12-31, ii from 2025-01-02 to 2026-10-09, iii from 2026-10-12; condor_em1 and fly5 i / ii / iii; before the span
    'pre'; every row carries it (capture, 15:58 and settle)."""
    p = PA.period_of
    assert [p('condor_d20', d) for d in ('2022-11-10', '2022-11-11', '2024-06-28', '2024-07-01', '2024-12-31', '2025-01-02', '2026-10-09', '2026-10-12', '2027-03-01')] == \
        ['pre', 'i-a', 'i-a', 'i-b', 'i-b', 'ii', 'ii', 'iii', 'iii']
    for k in ('condor_em1', 'fly5'):
        assert [p(k, d) for d in ('2022-11-11', '2024-12-31', '2025-01-02', '2026-10-09', '2026-10-12')] == ['i', 'i', 'ii', 'ii', 'iii']
    assert p('fly_spxw', '2024-01-02') == 'hist' and p('fly_spxw', '2026-10-13') == 'iii' and p('fly5', None) is None
    audit = _import_audit('audit_lib')
    for k in audit.KEYS:                                       # the audit's own definitions, day for day
        for d in ('2022-11-11', '2024-06-30', '2024-07-01', '2024-12-31', '2025-01-02', '2026-10-09', '2026-10-12', '2026-10-21'):
            assert p(k, d) == audit.period_of(k, d), (k, d)
    with tempfile.TemporaryDirectory() as d:
        tr, client, store, *_ = harness(Path(d), budget=80, cands=T.active_candidates(spxw=False), start=dt.datetime(2026, 10, 20, 20, 25, tzinfo=R.UTC))
        for m in DEFAULT_MINUTES + ['15:58']:
            tr.capture(DAY, m)
        tr.settle(DAY)
        for k, nm in (('condor_em1', 'SPY'), ('fly5', 'QQQ'), ('condor_d20', 'SPY')):
            df = store.read(k, nm, DAY)
            assert set(df['row_kind'].unique().to_list()) == {'capture', 'close1558', 'settle'} and df['period'].unique().to_list() == ['iii'], k


def test_session_statistics_agree_with_the_audits():
    """paper_audit's ported block_draws / session_stats give audit_lib's numbers to the last digit (seeded draws)"""
    import numpy as np
    audit = _import_audit('audit_lib')
    rng = np.random.default_rng(7)
    for n in (5, 61, 150):
        S = rng.normal(5, 40, n) * (rng.random(n) > 0.1)
        N = (S != 0).astype(float) * rng.integers(1, 6, n)
        a, b = PA.session_stats(S, N), audit.session_stats(S, N)
        assert a.keys() == b.keys()
        for k in a:
            va, vb = a[k], b[k]
            if isinstance(va, (tuple, list)):
                assert all((x == y) or (x != x and y != y) for x, y in zip(va, vb)), (n, k)
            else:
                assert va == vb or (va != va and vb != vb), (n, k, va, vb)
    assert (PA.block_draws(30, 20) == audit.block_draws(30, 20)).all()


def test_official_closes_source_chain():
    """UW's daily bar first (its newest fetch), Theta's EOD where UW has none, nothing where neither; UW's post-market
    bar gives the range"""
    with tempfile.TemporaryDirectory() as d:
        uw = Path(d) / 'oc'
        uw_close_file(uw, [('SPY', '2026-10-19', 'r', 777.31, None, None, 776.0), ('SPY', '2026-10-19', 'po', 777.4, 776.9, 778.1, None)])
        eod = Path(d) / 'eod' / 'year=2026'
        eod.mkdir(parents=True)
        ts = lambda day: dt.datetime.fromisoformat(day).replace(hour=17, minute=15, tzinfo=R.NY)      # noqa: E731
        pl.DataFrame({'symbol': ['SPY', 'SPY', 'QQQ'], 'created': [ts('2026-10-19'), ts('2026-10-21'), ts('2026-10-21')], 'close': [999.0, 770.5, 700.25]},
                     schema={'symbol': pl.Utf8, 'created': pl.Datetime('ms', 'America/New_York'), 'close': pl.Float64}).write_parquet(eod / 'p.parquet')
        oc = PA.OfficialCloses(uw_dirs=(uw,), uw_lake_glob=None, theta_glob=str(Path(d) / 'eod' / 'year=*' / '*.parquet'), live_root=None)
        assert oc.get('SPY', '2026-10-19') == (777.31, 'uw_1d')                 # UW over Theta's 999
        assert oc.get('SPY', '2026-10-21') == (770.5, 'theta_eod') and oc.get('QQQ', '2026-10-21') == (700.25, 'theta_eod')
        assert oc.get('SPY', '2026-10-20') == (None, None)
        assert oc.post_market('SPY', '2026-10-19')[:2] == (776.9, 778.1) and oc.post_market('SPY', '2026-10-20')[0] is None
        assert oc.open_r('SPY', '2026-10-19') == 776.0


def test_the_replay_settles_on_the_official_close_by_default_and_flags_a_fallback():
    """The default replay (--settle-on official): 2026-10-19 has UW's official close 777.30 → every SPY/QQQ settle row
    'official' at 777.30 (the condor −$102.60: (0.30 − 1.30) × 100 − $2.60), labelled where it came from; 2026-10-20 has
    none on disk → the 15:59 bar (777.20), labelled `1559_bar`, `settle_fallback` true, the session flagged in the day
    file and in the report, and not whole for the cumulative report; every row carries its period; the 15:58 rows of
    every candidate (the condors too) with the stress on the exit; the report's period tables and trades CSV."""
    with tempfile.TemporaryDirectory() as d:
        pq, rroot, out, oc_dir = Path(d) / 'pq', Path(d) / 'replay', Path(d) / 'out', Path(d) / 'oc'
        write_parquet_fixture(pq, ['2026-10-19', '2026-10-20'])
        uw_close_file(oc_dir, [('SPY', '2026-10-19', 'r', 777.30, None, None, None), ('QQQ', '2026-10-19', 'r', 777.30, None, None, None),
                               ('SPY', '2026-10-19', 'po', 777.5, 775.5, 777.6, None)])
        oc = PA.OfficialCloses(uw_dirs=(oc_dir,), uw_lake_glob=None, theta_glob=None, live_root=None)
        B.replay('2026-10-19', '2026-10-20', T.DEFAULT_KEYS, pq, rroot, progress=None, closes=oc)
        assert B.root_mode(rroot) == 'official'
        df = B.read_rows(rroot, T.DEFAULT_KEYS, '2026-10-19', '2026-10-20')
        em = df.filter((pl.col('candidate') == 'condor_em1') & (pl.col('row_kind') == 'settle')).sort('_day')
        a, b = em.filter(pl.col('_day') == '2026-10-19'), em.filter(pl.col('_day') == '2026-10-20')
        assert a['settle_source'].unique().to_list() == ['official'] and a['settle_px'].unique().to_list() == ['777.3']
        assert a['close_official_from'][0] == 'replay: official close (uw_1d)' and a['pnl_nbbo'].unique().to_list() == ['-102.6']
        assert a['settle_fallback'].unique().to_list() == ['false'] and a['close_1m_r'][0] == '777.2'
        assert b['settle_source'].unique().to_list() == ['1559_bar'] and b['settle_px'].unique().to_list() == ['777.2']
        assert b['settle_fallback'].unique().to_list() == ['true'] and b['pnl_nbbo'].unique().to_list() == ['-92.6']
        # the flags at the settlement: the short 776 call in the money → 100 shares short left; the pin; the post-market cross
        assert a['stock_left'].unique().to_list() == ['-100'] and a['stock_left_side'][0] == 'short' and a['pin_dist'][0] == '1.3'
        assert a['pm_cross'][0] == 'true' and a['pm_source'][0].startswith('uw_1d po')                # 775.5 – 777.6 takes 776 across
        assert b['pm_cross'][0] is None and b['pm_source'][0].startswith('none')
        assert df['period'].null_count() == 0 and df['period'].unique().to_list() == ['iii']
        days = B.read_days(rroot)
        assert 'settle_fallback' not in days['2026-10-19'] and days['2026-10-20']['settle_fallback'] == ['condor_d20 SPY', 'condor_em1 SPY', 'fly5 QQQ', 'fly5 SPY']
        assert 'NO OFFICIAL CLOSE' in days['2026-10-20']['note']
        cl = df.filter(pl.col('row_kind') == 'close1558')
        assert sorted(cl['candidate'].unique().to_list()) == ['condor_d20', 'condor_em1', 'fly5'] and cl['pnl_1558_1c'].null_count() == 0
        comp, pend = B.complete_sessions(rroot, T.DEFAULT_KEYS, '2026-10-19', '2026-10-20')
        assert comp == ['2026-10-19'] and 'no official close' in pend['2026-10-20']
        rep = B.build_report(rroot, T.DEFAULT_KEYS, '2026-10-19', '2026-10-20', out, parquet_root=pq, stream=None, closes=oc, decision_prices={})
        md = Path(rep['md']).read_text()
        assert 'official-close settlement' in md and '## Results by period — never pooled' in md and '## Hold to expiry against the 15:58 exit' in md
        assert '**Flagged — settled on the 15:59 bar (`1559_bar`), no official close on disk:** 2026-10-20 QQQ, 2026-10-20 SPY' in md
        assert '| condor | iii | 2 | 10 | 2 / 2 | -97.60 |' in md                     # (5 × −102.60 + 5 × −92.60) / 10
        tc = pl.read_csv(rep['trades_csv'])
        assert tc.height == 10 + 3 * 4 * 2 + 10 and set(tc['period'].unique().to_list()) == {'iii'}
        csv = pl.read_csv(rep['csv'])
        assert {'settlement', 'period', 'exit1558', 'flags', 'afterhours', 'cell', '1558'} <= set(csv['section'].to_list())


def test_1558_rows_for_every_candidate_with_the_stress_on_the_exit():
    """The 15:58 exit with the stress on the open AND the exit, by hand on the fixture iron fly (credit 1.88; at 15:58
    C773 3.10/3.20, P773 0.00/0.02, P768 0.00/0.01 — no bid, abandoned —, C778 0.05/0.07): +1c: entry 1.84, the exit
    −3.21 − 0.03 + 0.04 = −3.20 → (1.84 − 3.20) × 100 − $2.60 − $1.95 = −140.55; +2c: 1.80, −3.22 − 0.04 + 0.03 = −3.23 →
    −147.55. And the same figures as the audit's own `exit_1558` (run_audit.py) on every structure and quote set."""
    iron, call, put = T.flies5(fixture_chain(), 773.40, 5.0)
    condor = T.condor_em1(fixture_chain(), 773.40, 2.0)
    q = {('C', 773): (3.10, 3.20), ('P', 773): (0.00, 0.02), ('P', 768): (0.00, 0.01), ('C', 778): (0.05, 0.07), ('C', 768): (8.00, 8.20),
         ('P', 778): (4.60, 4.75), ('C', 776): (1.20, 1.25), ('P', 771): (0.00, 0.01), ('P', 769): (0.0, 0.01)}
    ch = T.Chain([{'option_symbol': f'SPY261020{r}{k * 1000:08d}', 'nbbo_bid': str(b), 'nbbo_ask': str(a)} for (r, k), (b, a) in q.items()], DAY)
    cap = T.capture_row(T.CANDIDATES['fly5'], iron, '15:30', R.parse_ts('2026-10-20T19:30:00Z'), 773.40, {}, fixture_chain(), 1, day=DAY)
    r = T.close_row(dict(cap, _day=DAY), iron, ch, R.parse_ts('2026-10-20T19:58:00Z'))
    assert r['pnl_1558_nbbo'] == '-133.55' and r['pnl_1558_1c'] == '-140.55' and r['pnl_1558_2c'] == '-147.55' and r['period'] == 'iii'
    run_audit = _import_audit('run_audit')
    quotes = {k: v for k, v in q.items()}
    for s in (iron, call, put, condor):
        legs = [(l.right, l.strike, l.side, l.qty) for l in s.legs]
        cash = s.entry_cash()
        liq = T.liquidation(s, ch)
        mine = T.exit_pnl(s, liq)
        for tag, w in (('nbbo', 0.0), ('1c', 0.01), ('2c', 0.02)):
            nb, _, closed = run_audit.exit_1558(legs, cash, quotes, w)
            if nb is None:
                assert mine[f'pnl_1558_{tag}'] is None
                continue
            want = (cash - 4 * w + nb) * 100 - 4 * 0.65 - closed * 0.65            # run_audit.build_trades' formula
            assert abs(mine[f'pnl_1558_{tag}'] - want) < 1e-9, (s.structure, tag, mine, want)
    # in a session: a condor's 15:58 row, its settle row carrying the stressed exit
    with tempfile.TemporaryDirectory() as d:
        tr, client, store, *_ = harness(Path(d), budget=80, cands=T.active_candidates(keys=('condor_em1', 'condor_d20')))
        tr.capture(DAY, '13:00')
        s = tr.capture(DAY, '15:58')
        assert s['calls'] == 1 and s['rows'] == 2                        # one SPY chain for both condors
        tr.settle(DAY)
        se = store.read('condor_em1', 'SPY', DAY).filter(pl.col('row_kind') == 'settle').to_dicts()[0]
        cl = store.read('condor_em1', 'SPY', DAY).filter(pl.col('row_kind') == 'close1558').to_dicts()[0]
        assert se['pnl_1558_nbbo'] == cl['pnl_1558_nbbo'] and se['pnl_1558_2c'] == cl['pnl_1558_2c'] is not None
        assert float(se['pnl_1558_2c']) < float(se['pnl_1558_1c']) < float(se['pnl_1558_nbbo'])


def test_expiry_flags_on_a_fixture():
    """At 777.20: the condor's short 776 call is assigned (−100 shares), the iron fly's short 773 call (−100), the call
    fly's long 768 and two short 773 calls (+100 − 200 = −100), the put fly's long 778 put (−100); at 773.00 neither the
    condor nor the iron fly has a leg in the money (0; the iron fly's pin 0.00) but the call fly's long 768 call is
    (+100 — a long fly pinned at K0 still delivers stock) and the put fly's long 778 put (−100). Exercise-by-exception needs $0.01: at 776.01 the 776 call is assigned, at
    776.004 it is not. The pins are the nearest short strike within $0.25 / $0.50. The post-market cross: a range that
    takes a short strike across the money (775.5–777.6 around 776), not one wholly on one side (776.5–777.6), none
    without the bar."""
    ch = fixture_chain()
    c = T.condor_em1(ch, 773.40, 2.0)
    iron, call, put = T.flies5(ch, 773.40, 5.0)
    assert [PA.stock_left(x, 777.20) for x in (c, iron, call, put)] == [-100, -100, -100, -100]
    assert [PA.stock_left(x, 773.00) for x in (c, iron, call, put)] == [0, 0, 100, -100]
    assert PA.stock_left(c, 776.01) == -100 and PA.stock_left(c, 776.004) == 0
    f = PA.flags(c, 776.20)
    assert f['pin_025'] and f['pin_050'] and close(f['pin_dist'], 0.20) and f['stock_left_side'] == 'short'
    f = PA.flags(c, 776.40)
    assert not f['pin_025'] and f['pin_050']
    assert PA.flags(c, 777.20, 775.5, 777.6)['pm_cross'] is True and PA.flags(c, 777.20, 776.5, 777.6)['pm_cross'] is False
    assert PA.flags(c, 777.20)['pm_cross'] is None
    assert PA.flags(iron, 773.0)['pin_dist'] == 0.0 and PA.flags(iron, 773.0, cash_settled=True)['stock_left_side'] == 'cash-settled'
    row = T.settle_row(dict(T.capture_row(T.CANDIDATES['condor_em1'], c, '11:30', R.parse_ts('2026-10-20T15:30:00Z'), 773.4, {}, ch, 1, day=DAY), _day=DAY),
                       c, 'official', 777.20, {'close_official': 777.20, 'pm_low': 775.5, 'pm_high': 777.6, 'pm_source': 'test'}, R.parse_ts('2026-10-20T20:20:00Z'))
    assert (row['stock_left'], row['stock_left_side'], row['pin_025'], row['pin_050'], row['pm_cross'], row['settle_fallback'], row['period']) == \
        ('-100', 'short', 'false', 'false', 'true', 'false', 'iii')


def test_after_hours_cases_by_hand():
    """paper_audit.after_hours_pnl on the fixture condor (credit 0.30: short C776 / long C778, short P771 / long P769):
    official 777.20, the next open 778.00. (0) intrinsic: (0.30 − 1.20) × 100 − 2.60 = −92.60. (a) the short 776 call
    assigned at the close, the short stock bought back at the open: (0.30 + (776 − 778)) × 100 − 2.60 = −172.60.
    (b) decision 775.90: the call is out of the money then — not assigned, no long in the money at the close → +27.40;
    decision 776.50: assigned → −172.60. (c) both at the decision price 778.50: the long 778 call is exercised too —
    (0.30 + (776 − 778) + (778 − 778)) → −172.60; at 779.00 the same. With a fee of $1 a contract exercised: (a) −173.60.
    The iron fly (credit 1.88) at official 773.004 (nothing ≥ $0.01 in the money) is case 0's +185.40 in (a); at 772.99
    the short 773 put is assigned (+100 shares) and the open 770 marks it: (1.88 − 3.00) × 100 − 2.60 = −114.60. A
    missing open: (a) (b) (c) None; a missing decision price: (b) (c) None; cash-settled: every case is case 0."""
    ch = fixture_chain()
    c = T.condor_em1(ch, 773.40, 2.0)
    ah = PA.after_hours_pnl(c, c.entry_cash(), 777.20, 778.00, 775.90)
    assert close(ah['pnl_ah0'], -92.60) and close(ah['pnl_ah_a'], -172.60) and close(ah['pnl_ah_b'], 27.40) and close(ah['pnl_ah_c'], 27.40)
    ah = PA.after_hours_pnl(c, c.entry_cash(), 777.20, 778.00, 776.50)
    assert close(ah['pnl_ah_b'], -172.60) and close(ah['pnl_ah_c'], -172.60)
    ah = PA.after_hours_pnl(c, c.entry_cash(), 777.20, 778.00, 778.50)
    assert close(ah['pnl_ah_c'], -172.60) and close(ah['pnl_ah_b'], -172.60)
    assert close(PA.after_hours_pnl(c, c.entry_cash(), 777.20, 778.00, None, fee_per_exercise=1.0)['pnl_ah_a'], -173.60)
    iron = T.flies5(ch, 773.40, 5.0)[0]
    assert close(PA.after_hours_pnl(iron, iron.entry_cash(), 773.004, 770.0, None)['pnl_ah_a'], 185.40)
    assert close(PA.after_hours_pnl(iron, iron.entry_cash(), 772.99, 770.0, None)['pnl_ah_a'], -114.60)
    none = PA.after_hours_pnl(c, c.entry_cash(), 777.20, None, 776.0)
    assert close(none['pnl_ah0'], -92.60) and none['pnl_ah_a'] is None and none['pnl_ah_b'] is None and none['pnl_ah_c'] is None
    nod = PA.after_hours_pnl(c, c.entry_cash(), 777.20, 778.0, None)
    assert nod['pnl_ah_a'] is not None and nod['pnl_ah_b'] is None and nod['pnl_ah_c'] is None
    cash = PA.after_hours_pnl(c, c.entry_cash(), 777.20, 778.0, 776.5, cash_settled=True)
    assert all(close(cash[k], -92.60) for k in ('pnl_ah0', 'pnl_ah_a', 'pnl_ah_b', 'pnl_ah_c'))


def test_after_hours_cases_equal_the_studys_rows():
    """Reconciled with the after-hours study (research_notes/Compass phase 3/backtest_audit/out/afterhours_trades.csv,
    commit 633fbff): on period ii's overlap, rows of fly5 iron and condor_d20 where the cases differ — the study's own
    legs, NBBO entry, official close, decision price (its last UW post-market minute bar ≤ 17:30) and next 09:30 open
    fed to paper_audit.after_hours_pnl give its four P&Ls to the cent. And its decision prices for the forward sessions
    are what decision_prices_on_disk reads off data/postmarket_1m."""
    f = AUDIT_DIR / 'out' / 'afterhours_trades.csv'
    assert f.exists(), f
    d = pl.read_csv(f, infer_schema_length=None).filter(pl.col('period') == 'ii')
    picks = []
    for cand in ('fly5', 'condor_d20'):
        x = d.filter(pl.col('candidate') == cand)
        for cond in ((pl.col('pnl_a') - pl.col('pnl_0')).abs() > 0.005, (pl.col('pnl_b') - pl.col('pnl_a')).abs() > 0.005,
                     (pl.col('pnl_c') - pl.col('pnl_b')).abs() > 0.005, (pl.col('pnl_a') - pl.col('pnl_0')).abs() <= 0.005):
            picks += x.filter(cond).sort('day', 'name', 'minute').head(3).to_dicts()
    assert len(picks) == 24
    for r in picks:
        legs = [tuple(x) for x in json.loads(r['legs'])]
        entry = r['price_nbbo'] if r['package'] == 'credit' else -r['price_nbbo']
        ah = PA.after_hours_pnl(legs, entry, r['official'], r['next_open_0930'], r['decision_px'])
        for mine, theirs in (('pnl_ah0', 'pnl_0'), ('pnl_ah_a', 'pnl_a'), ('pnl_ah_b', 'pnl_b'), ('pnl_ah_c', 'pnl_c')):
            assert abs(round(ah[mine], 2) - round(r[theirs], 2)) < 0.005, (r['candidate'], r['day'], r['minute'], mine, ah[mine], r[theirs])
    dp = PA.decision_prices_on_disk()
    iii = pl.read_csv(f, infer_schema_length=None).filter(pl.col('period') == 'iii').select('name', 'day', 'decision_px').unique()
    assert iii.height == 16 and all(abs(dp[(n, dd)] - px) < 1e-9 for n, dd, px in iii.iter_rows())


def test_the_append_mode_leaves_the_history_untouched():
    """append_cumulative: a new file holds the historical sections given; the forward sessions of the root (whole ones
    alone) are appended; a second append with nothing new writes nothing; a session added to the root later is appended
    and the historical bytes are still the same; a session not whole (a 15:59 fallback) is pending, never appended; a
    listed session gone from the root stops it."""
    with tempfile.TemporaryDirectory() as d:
        pq, rroot, cum, oc_dir = Path(d) / 'pq', Path(d) / 'replay', Path(d) / 'cumulative.md', Path(d) / 'oc'
        days = ['2026-10-19', '2026-10-20', '2026-10-21']
        write_parquet_fixture(pq, days)
        uw_close_file(oc_dir, [(n, dd, 'r', 777.30, None, None, None) for n in ('SPY', 'QQQ') for dd in days[:2]])
        oc = PA.OfficialCloses(uw_dirs=(oc_dir,), uw_lake_glob=None, theta_glob=None, live_root=None)
        hist = Path(d) / 'hist.md'
        hist.write_text('# Historical replay 2022-11-11 → 2026-10-09\n\n| period | mean |\n|---|---|\n| i | +3.47 |\n', encoding='utf-8')
        B.replay(days[0], days[0], T.DEFAULT_KEYS, pq, rroot, progress=None, closes=oc)
        r1 = B.append_cumulative(rroot, cum, parquet_root=pq, closes=oc, decision_prices={}, historical_from=hist)
        assert r1['added'] == [days[0]] and r1['written']
        t1 = cum.read_text()
        h0 = t1[:t1.index(B.CUM_HIST_END) + len(B.CUM_HIST_END)]
        assert '## Historical replay 2022-11-11 → 2026-10-09' in h0 and '| i | +3.47 |' in h0
        assert '# Forward — period iii, 1 session, 2026-10-19 → 2026-10-19' in t1 and '| 2026-10-19 | condor_em1 condor' in t1
        st = cum.stat().st_mtime_ns
        assert B.append_cumulative(rroot, cum, parquet_root=pq, closes=oc, decision_prices={})['added'] == [] and cum.stat().st_mtime_ns == st
        B.replay(days[1], days[2], T.DEFAULT_KEYS, pq, rroot, progress=None, closes=oc)
        r2 = B.append_cumulative(rroot, cum, parquet_root=pq, closes=oc, decision_prices={})
        assert r2['added'] == [days[1]] and 'no official close' in r2['pending'][days[2]]
        t2 = cum.read_text()
        assert t2.startswith(h0) and '2 sessions, 2026-10-19 → 2026-10-20' in t2 and '| 2026-10-21 |' not in t2
        assert t2.count(B.CUM_HIST_BEGIN) == 1 and t2.count(B.CUM_FWD_BEGIN) == 1
        # the next session's open is now on disk for 2026-10-19: its after-hours (a) column fills on this regeneration
        tc = B.trade_table(B.read_rows(rroot, T.DEFAULT_KEYS, days[0], days[0]), oc, pq, {})[0]
        assert all(t['next_open'] == 773.40 and t['pnl_ah_a'] is not None for t in tc if t['candidate'] != 'fly_spxw')
        shutil.rmtree(rroot / 'condor_em1' / 'SPY')
        (rroot / 'condor_em1' / 'SPY').mkdir()
        try:
            B.append_cumulative(rroot, cum, parquet_root=pq, closes=oc, decision_prices={})
            assert False, 'a listed session gone from the root must stop the append'
        except ValueError as e:
            assert 'not whole' in str(e)
        assert cum.read_text() == t2


# ---- the daily job (scripts/daily_forward.py) -------------------------------------------------------------------------------------------

JOB_DAY = '2026-10-22'
JOB_NOW = dt.datetime(2026, 10, 22, 21, 45, tzinfo=R.UTC)        # 17:45 New York


def job_layout(root: Path, day: str = JOB_DAY):
    """a layout holding the 20 sessions before `day` that the replay and --verify-parquet read (the stored 2026-10-09
    bars and prints copied under their dates; the bars are read by minute)"""
    for d in T.previous_sessions(day, 20):
        for rel in ('data/underlying/SPY/2026-10-09.parquet', 'data/underlying/QQQ/2026-10-09.parquet', 'data/index/VIX/2026-10-09.parquet'):
            dst = root / rel.replace('2026-10-09', d)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REF / rel, dst)


def job_pieces(d: Path, **kw):
    pq, rroot, cum, oc_dir, pm = Path(d) / 'pq', Path(d) / 'replay', Path(d) / 'cumulative.md', Path(d) / 'oc', Path(d) / 'pm'
    job_layout(pq)
    job = DF.Job(pq, rroot, cum, official_dir=oc_dir, postmarket_dir=pm, day=kw.pop('day', JOB_DAY), **kw)
    scrub = R.Scrub(TOKEN)
    log = R.make_logger(scrub, None, stream=None, name='daily_forward_test')
    lines = R.ListHandler(scrub)
    log.addHandler(lines)
    clock = R.FakeClock(JOB_NOW)
    uw = T.FakePaperClient(R.RateLimiter(max_in_flight=1, per_minute=100, daily_budget=50, clock=clock), log, clock, scrub, close_official=777.50)
    closes = PA.OfficialCloses(uw_dirs=(oc_dir,), uw_lake_glob=None, theta_glob=None, live_root=None)
    return job, log, lines, uw, closes


def test_the_daily_job_fetches_verifies_merges_replays_and_appends_once():
    """--source terminal (no login): the fake Theta Terminal answers the day; staged, verified, merged; UW's daily bar
    asked once a name (2 calls) for the official close, kept as fetched; the session replayed on it and appended. A
    second run: nothing pending — no Theta call, no UW call, the cumulative report unchanged; `--day` again on an
    appended day: nothing either."""
    term = _FakeThetaTerminal()
    try:
        with tempfile.TemporaryDirectory() as d:
            job, log, lines, uw, closes = job_pieces(d)
            res = DF.run_job(job, now=JOB_NOW, log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes)
            assert res['rc'] == 0 and res['completed'] == [JOB_DAY] and res['appended'] == [JOB_DAY] and res['fetched'] == [JOB_DAY], (res, lines.lines)
            assert res['logins'] == 0 and sum(1 for p, _ in uw.requests if p.endswith('/ohlc/1d')) == 2
            assert all((job.parquet_root / B.rel_of(j['kind'], j['sym'], JOB_DAY)).exists() for j in B.fetch_jobs(JOB_DAY))
            assert not (job.staging / JOB_DAY).exists() and list(job.official_dir.glob('uw_ohlc_1d_2026-10-22_fetched*.parquet'))
            se = B.read_rows(job.replay_root, ('condor_em1',), JOB_DAY, JOB_DAY).filter(pl.col('row_kind') == 'settle')
            assert se.height and se['settle_source'].unique().to_list() == ['official'] and se['settle_px'].unique().to_list() == ['777.5']
            txt = job.cumulative.read_text()
            assert f'| {JOB_DAY} | condor_em1 condor' in txt and B._cum_parse(txt)[2] == [JOB_DAY]
            assert any('DAILY-FORWARD OK' in l for l in lines.lines) and all(TOKEN not in l for l in lines.lines)
            n_theta, n_uw, mt = len(term.paths), len(uw.requests), job.cumulative.stat().st_mtime_ns
            again = DF.run_job(DF.Job(job.parquet_root, job.replay_root, job.cumulative, official_dir=job.official_dir, postmarket_dir=job.postmarket_dir,
                                      start=JOB_DAY), now=JOB_NOW + dt.timedelta(hours=1), log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes)
            assert again['rc'] == 0 and again['pending'] == [] and len(term.paths) == n_theta and len(uw.requests) == n_uw
            assert job.cumulative.stat().st_mtime_ns == mt
            assert DF.run_job(job, now=JOB_NOW, log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes)['pending'] == []
            # a new machine: the report lists the day, this replay root does not hold it → rebuilt (no fetch: in the
            # layout; no UW call: the close is on disk), nothing appended twice
            shutil.rmtree(job.replay_root)
            reb = DF.run_job(job, now=JOB_NOW, log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes)
            assert reb['rc'] == 0 and reb['rebuild'] == [JOB_DAY] and reb['completed'] == [JOB_DAY] and reb['appended'] == [], reb
            assert len(term.paths) == n_theta, term.paths[n_theta:]
            assert len(uw.requests) == n_uw, uw.requests[n_uw:]
            assert B.complete_sessions(job.replay_root, T.DEFAULT_KEYS, JOB_DAY, JOB_DAY)[0] == [JOB_DAY]
            # the day before the ready time: not pending yet
            assert DF.pending_sessions([], R.ny_at('2026-10-23', '17:00'), start='2026-10-23') == []
            assert DF.pending_sessions([], JOB_NOW, start='2026-11-25') == [] and DF.pending_sessions([], R.ny_at('2026-11-30', '18:00'), start='2026-11-25') == \
                ['2026-11-25', '2026-11-30']                                                  # Thanksgiving and the half day skipped
    finally:
        term.close()


def test_the_daily_job_never_appends_a_partial_day():
    """A fetch that comes back short (a 472 on a file), a staged day that fails --verify-parquet, and an official close
    not published yet: each exits 1 with one DAILY-FORWARD FAIL line naming the day and the step; nothing is merged
    or appended (the cumulative report never written)."""
    term = _FakeThetaTerminal()
    try:
        with tempfile.TemporaryDirectory() as d:
            job, log, lines, uw, closes = job_pieces(d)
            term.script[('/v3/index/history/price', 'VIX')] = [('status', 472, 'No data')]
            res = DF.run_job(job, now=JOB_NOW, log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes)
            assert res['rc'] == 1 and res['completed'] == [] and not job.cumulative.exists()
            assert any(l.split(' ', 2)[2].startswith(f'DAILY-FORWARD FAIL {JOB_DAY} fetch:') for l in lines.lines), lines.lines
            assert not (job.parquet_root / 'data_full' / 'chains' / 'SPY' / f'{JOB_DAY}.parquet').exists()
        with tempfile.TemporaryDirectory() as d:
            job, log, lines, uw, closes = job_pieces(d)
            # a staged leftover the fetch keeps (it never re-asks a staged file): a chain with half an hour cut out
            stage = job.staging / JOB_DAY
            src = pl.read_parquet(REF / 'data_full/chains/SPY/2026-10-09.parquet')
            bad = src.with_columns(pl.col('timestamp') + pl.duration(days=13)).filter(~((pl.col('timestamp').dt.hour() == 13) & (pl.col('timestamp').dt.minute() < 30)))
            f = stage / B.rel_of('chain', 'SPY', JOB_DAY)
            f.parent.mkdir(parents=True)
            bad.write_parquet(f)
            res = DF.run_job(job, now=JOB_NOW, log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes)
            assert res['rc'] == 1 and not job.cumulative.exists()
            assert any(f'DAILY-FORWARD FAIL {JOB_DAY} verify-parquet:' in l for l in lines.lines), lines.lines
            assert not (job.parquet_root / 'data_full' / 'chains' / 'SPY' / f'{JOB_DAY}.parquet').exists()
        with tempfile.TemporaryDirectory() as d:
            job, log, lines, uw, closes = job_pieces(d)
            uw.close_official = None                                        # UW's daily bar does not carry the day yet
            res = DF.run_job(job, now=JOB_NOW, log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes)
            assert res['rc'] == 1 and not job.cumulative.exists() and 'official-close' in res['failure']
            assert any(f'DAILY-FORWARD FAIL {JOB_DAY} official-close: no official close for SPY, QQQ' in l for l in lines.lines)
            assert not (job.replay_root / 'condor_em1').exists()                  # never settled on the 15:59 bar
    finally:
        term.close()


class _FakeSdkClient:
    """the thetadata SDK's three calls, answering the stored 2026-10-09 re-dated to the day asked (polars frames as the
    SDK hands them: the chain without its mid, with symbol and expiration)"""

    def __init__(self):
        self.calls = []

    def _frame(self, kind, sym, D):
        df = pl.read_parquet(REF / B.rel_of(kind, sym, '2026-10-09'))
        shift = (D - dt.date(2026, 10, 9)).days
        df = df.with_columns(pl.col('timestamp') + pl.duration(days=shift))
        if kind == 'chain':
            df = df.drop('mid').with_columns(pl.lit(sym).alias('symbol'), pl.lit(D.isoformat()).alias('expiration'))
        return df

    def option_history_quote(self, symbol, expiration, interval, date, strike, right):
        self.calls.append(('chain', symbol, date))
        return self._frame('chain', symbol, date)

    def stock_history_ohlc(self, symbol, interval, date):
        self.calls.append(('under', symbol, date))
        return self._frame('under', symbol, date)

    def index_history_price(self, symbol, interval, date):
        self.calls.append(('index', symbol, date))
        return self._frame('index', symbol, date)


def test_the_sdk_source_logs_in_once_and_only_inside_the_owners_window():
    """--source sdk: refused (exit 2, no login) with THETA_SDK_WINDOW unset, outside the window, and between 00:00 and
    01:45 New York even inside a window that holds it; inside the window two sessions are fetched on ONE login, verified,
    merged, replayed and appended."""
    logins = []

    def factory():
        logins.append(1)
        return _FakeSdkClient()
    with tempfile.TemporaryDirectory() as d:
        job, log, lines, uw, closes = job_pieces(d, source='sdk', day=None, start=JOB_DAY)
        for win, now, why in ((None, JOB_NOW, 'not set'), ('18:00-19:00', JOB_NOW, 'outside'),
                              ('23:00-02:00', dt.datetime(2026, 10, 23, 4, 30, tzinfo=R.UTC), 'gap')):
            sdk = DF.SdkSource(factory=factory, log=log)
            env = os.environ.pop(DF.SDK_WINDOW_ENV, None)
            try:
                res = DF.run_job(job, now=now, log=log, sdk=sdk, uw_client=uw, closes=closes, window=win)
            finally:
                if env is not None:
                    os.environ[DF.SDK_WINDOW_ENV] = env
            assert res['rc'] == 2 and why in res['failure'] and not logins and not job.cumulative.exists(), (win, res)
        assert any('DAILY-FORWARD REFUSED' in l for l in lines.lines)
        assert DF.in_window(R.ny_at(JOB_DAY, '23:30').astimezone(R.NY), DF.parse_window('23:00-02:00'))
        sdk = DF.SdkSource(factory=factory, log=log)
        res = DF.run_job(job, now=dt.datetime(2026, 10, 23, 22, 0, tzinfo=R.UTC), log=log, sdk=sdk, uw_client=uw, closes=closes, window='17:00-23:00')
        assert res['rc'] == 0 and res['completed'] == ['2026-10-22', '2026-10-23'] and res['logins'] == 1 and len(logins) == 1, (res, lines.lines[-5:])
        assert B._cum_parse(job.cumulative.read_text())[2] == ['2026-10-22', '2026-10-23']


def test_the_next_open_skips_a_holidays_padded_file():
    """The next session's 09:30 open (the after-hours cases' stock mark) skips a padded holiday file in the layout (the
    stored data holds one for Thanksgiving 2025-11-27 — taking it left seven condors of 2025-11-26 without an open until
    the reconciliation with the after-hours study found it); no next session on disk → None"""
    with tempfile.TemporaryDirectory() as d:
        pq = Path(d) / 'pq'
        write_parquet_fixture(pq, ['2026-10-19', '2026-10-21'])
        pad = pl.read_parquet(pq / 'data/underlying/SPY/2026-10-19.parquet').head(5).with_columns(pl.col('timestamp') + pl.duration(days=1))
        pad.with_columns([pl.lit(None, pl.Float64).alias(c) for c in ('open', 'high', 'low', 'close')]).write_parquet(pq / 'data/underlying/SPY/2026-10-20.parquet')
        src = B.ParquetSource(pq)
        oc = PA.OfficialCloses.none()
        assert B.next_session_open(src, oc, 'SPY', '2026-10-19') == (773.40, '2026-10-21', "parquet: the 09:30 bar's open")
        assert B.next_session_open(src, oc, 'SPY', '2026-10-21')[0] is None


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
