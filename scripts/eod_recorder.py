#!/usr/bin/env python3
"""
eod_recorder.py — the Compass Phase 2 recorder: an append-only Unusual Whales recorder for the Compass universe
(SPX, SPY, QQQ, IWM and the twenty most liquid roots), one process, one schedule.

WHAT IT RECORDS (every row stamped with the New York day, the scan it belongs to, and the fetch time in UTC; every
vendor field kept as the string UW sent it; never a row deleted):

  pass   folder          UW route                                              a call asks
  eod    flow_alerts     GET /api/option-trades/flow-alerts                    one root, min_premium 25000, paged back by older_than
  eod    darkpool        GET /api/darkpool/{ticker}                            date=D, paged back by older_than (never an index)
  eod    net_prem_ticks  GET /api/stock/{ticker}/net-prem-ticks                date=D, one call
  eod    ohlc_1m         GET /api/stock/{ticker}/ohlc/1m                       date=D, limit 1000, one call (never an index: 422)
  eod    oi_strike       GET /api/stock/{ticker}/oi-per-strike                 date=D, one call — call_oi / put_oi by strike
  eod    chain           GET /api/stock/{ticker}/option-contracts              exclude_zero_oi_chains, 500 a page — OI a contract
  scan   spot_strike     GET /api/stock/{ticker}/spot-exposures/strike         the whole book by strike, 500 a page

THE SCHEDULE (New York): scans at 09:35, then every half hour from 10:00 to 15:30, and 15:50; the EOD pass at 16:15;
Monday to Friday, never on an exchange holiday (HOLIDAYS below); on a half day the scans end at 12:50 and the EOD
pass runs at 13:15.

THE LIMITER: at most 3 calls in flight (UW Basic answers three at once), a token bucket of 100 calls a minute, a daily
budget (20,000 by default) that ends the run with one clear line when it is spent. 429 and 5xx wait the Retry-After
or 2, 4, 8, 16 s and try five times; any other 4xx is recorded and passed over. Every call is logged with its status
and elapsed time; the token is never logged, and every message is scrubbed.

THE MACRO STAMPS (macro_calendar.py, data/macro_events_2022_2027.json or MACRO_EVENTS): every row carries
is_macro_event_day, macro_events (the day's kinds joined by '+'), minutes_to_macro_release and
minutes_since_last_release — a scan row at its scan time, an EOD row null; all null, with one WARN line, when the
calendar is not on disk. They are written after the vendor's columns and are never part of a row's key.

THE TOKEN comes from the environment alone (UW_API_TOKEN, sent as a Bearer header) — never from a file in the repo.
The data root is RECORDER_DATA, or data_recorder/ in the repo (git-ignored).

MODES: --eod, --scan, --daemon, --auto (the pass the clock calls for — for cron), --dry-run (no network: a fake client
on tests/fixtures), --smoke (one call an endpoint, one name — the owner's first run), --status.

Read scripts/eod_recorder.README.md for the schema, the budget arithmetic, the smoke procedure, what the smoke test of
2026-10-21 settled and what is still unsettled. The forward paper tracker (scripts/paper_tracker.py) imports this
module's client, limiter, scrubber and store.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import macro_calendar as MC  # noqa: E402  — the macro-release stamps (data/macro_events_2022_2027.json)

VERSION = 'eod-recorder-2026-10-21.3'   # .3: the chain's page cap 150 for an index (SPX hit 40 on 2026-10-21); the macro stamps
# .2: the smoke test of 2026-10-21 settled the endpoint notes (README "Settled")
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
NY = ZoneInfo('America/New_York')
UTC = dt.timezone.utc
BASE_URL = 'https://api.unusualwhales.com'
USER_AGENT = 'georgeredo-eod-recorder/' + VERSION
MIN_PREMIUM = 25_000
RETRIES = 5
BACKOFF_S = (2, 4, 8, 16, 32)
MAX_RETRY_AFTER_S = 120

# ---- the universe ----------------------------------------------------------------------------------------------------

CORE_NAMES = ['SPX', 'SPY', 'QQQ', 'IWM']
# research_notes/Compass engine audit/horizons/top20.json `top20_used` (by option volume, 2026-10-06..12; SPCX, listed
# 2026, replaced by GME, the 21st name). Overridable with --names FILE (one name a line, # comments).
TOP20 = ['NVDA', 'TSLA', 'AAPL', 'MU', 'INTC', 'AMZN', 'TLT', 'META', 'EWZ', 'PLTR',
         'AMD', 'IBIT', 'MSFT', 'GOOGL', 'MSTR', 'HYG', 'AVGO', 'SOFI', 'ORCL', 'GME']
DEFAULT_NAMES = CORE_NAMES + TOP20

# An index has no stock prints and no bars on UW Basic (darkpool: nothing; ohlc: 422 cboe_index_access_missing), and
# lists its PM dailies under a second root (3abida docs/data-feed-samples.md: SPX's own dates are the AM monthlies,
# SPXW's every session). Its book (/spot-exposures/strike) is asked under the index's own name — the smoke test of
# 2026-10-21 read SPX's whole book under SPX, 824 strikes over two pages — and its chain under SPX carries BOTH roots'
# contracts (SPXW261021… and SPX261… option_symbols in one answer). Flow alerts are filed under BOTH roots (SPX 174
# rows and SPXW 200 in the smoke), so both are asked; the dedupe on `id` makes a row filed twice harmless.
INDEX_NAMES = frozenset(['SPX', 'NDX', 'RUT', 'VIX'])
ALERT_ROOTS = {'SPX': ['SPX', 'SPXW'], 'NDX': ['NDX', 'NDXP'], 'RUT': ['RUT', 'RUTW'], 'VIX': ['VIX', 'VIXW']}

# ---- the calendar ----------------------------------------------------------------------------------------------------

SCAN_TIMES = ['09:35', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30',
              '15:00', '15:30', '15:50']
HALF_DAY_SCAN_TIMES = ['09:35', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '12:50']
EOD_TIME = '16:15'
HALF_DAY_EOD_TIME = '13:15'

# US equity market holidays (NYSE), the same list the terminal keeps (3abida src/core/calendar.ts). EXTEND IT EACH
# AUTUMN for the year after next; a day missing here is recorded like any weekday (the calls answer empty or the
# session before's rows, a waste of a few hundred calls, never a corruption).
HOLIDAYS = frozenset([
    # 2026
    '2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07',
    '2026-11-26', '2026-12-25',
    # 2027
    '2027-01-01', '2027-01-18', '2027-02-15', '2027-03-26', '2027-05-31', '2027-06-18', '2027-07-05', '2027-09-06',
    '2027-11-25', '2027-12-24',
])
# Early closes (13:00 New York): the day after Thanksgiving and Christmas Eve when it is a weekday.
HALF_DAYS = frozenset(['2026-11-27', '2026-12-24', '2027-11-26'])

# ---- the endpoints -----------------------------------------------------------------------------------------------------

STAMPS = ['_day', '_scan', '_scan_at', '_fetched_at', '_name', '_key']


@dataclass(frozen=True)
class Endpoint:
    key: str
    pass_: str                      # 'eod' | 'scan'
    path: str                       # with {t} for the name
    dedupe: tuple                   # the vendor's own id for a row; all null → the whole row
    columns: tuple                  # the vendor fields a live answer carried (docs/data-feed-samples.md, 2026-10-12)
    indices: bool = True            # asked for an index name
    page_limit: int | None = None   # `limit` asked a page (None: the route's own answer, one call)
    page_limit_fallback: int | None = None  # tried once when the vendor refuses the limit (422)
    max_pages: int = 1
    paging: str = 'none'            # 'none' | 'older_than' | 'page'
    max_pages_index: int | None = None  # the page cap for an index name (SPX's chain carries SPX and SPXW), else max_pages
    time_field: str = ''            # the row's time for the older_than cursor and the day's bounds
    note: str = ''


FLOW_ALERT_COLUMNS = (
    'id', 'rule_id', 'alert_rule', 'ticker', 'option_chain', 'type', 'strike', 'expiry', 'expiry_count',
    'created_at', 'start_time', 'end_time', 'total_premium', 'total_ask_side_prem', 'total_bid_side_prem',
    'total_size', 'trade_count', 'volume', 'open_interest', 'volume_oi_ratio', 'price', 'bid', 'ask', 'theo',
    'underlying_price', 'iv', 'iv_start', 'iv_end', 'delta', 'gamma', 'theta', 'vega', 'rho', 'has_sweep',
    'has_floor', 'has_singleleg', 'has_multileg', 'all_opening_trades', 'issue_type', 'sector', 'marketcap',
    'next_earnings_date', 'er_time',
    'missing_periscope',   # an index root's rows carry it (SPX and SPXW, 2026-10-21 smoke: "true"); a stock's do not
)
DARKPOOL_COLUMNS = (
    'tracking_id', 'ticker', 'executed_at', 'trf_executed_at', 'price', 'size', 'premium', 'volume', 'nbbo_bid',
    'nbbo_ask', 'nbbo_bid_quantity', 'nbbo_ask_quantity', 'market_center', 'canceled', 'sale_cond_codes',
    'ext_hour_sold_codes', 'trade_code', 'trade_settlement',
)
NET_PREM_COLUMNS = (
    'date', 'tape_time', 'call_volume', 'put_volume', 'call_volume_ask_side', 'call_volume_bid_side',
    'put_volume_ask_side', 'put_volume_bid_side', 'net_call_premium', 'net_put_premium', 'net_call_volume',
    'net_put_volume', 'net_delta',
)
OHLC_COLUMNS = ('start_time', 'end_time', 'open', 'high', 'low', 'close', 'volume', 'total_volume', 'market_time')
SPOT_STRIKE_COLUMNS = (
    'ticker', 'date', 'time', 'price', 'strike',
    'call_gamma_oi', 'put_gamma_oi', 'call_delta_oi', 'put_delta_oi', 'call_charm_oi', 'put_charm_oi',
    'call_vanna_oi', 'put_vanna_oi',
    'call_gamma_vol', 'put_gamma_vol', 'call_delta_vol', 'put_delta_vol', 'call_charm_vol', 'put_charm_vol',
    'call_vanna_vol', 'put_vanna_vol',
    'call_gamma_ask', 'put_gamma_ask', 'call_delta_ask', 'put_delta_ask', 'call_charm_ask', 'put_charm_ask',
    'call_vanna_ask', 'put_vanna_ask',
    'call_gamma_bid', 'put_gamma_bid', 'call_delta_bid', 'put_delta_bid', 'call_charm_bid', 'put_charm_bid',
    'call_vanna_bid', 'put_vanna_bid',
)
OI_STRIKE_COLUMNS = ('date', 'strike', 'call_oi', 'put_oi')
CHAIN_COLUMNS = (
    'option_symbol', 'open_interest', 'prev_oi', 'implied_volatility', 'delta', 'gamma', 'theta', 'vega', 'rho',
    'volume', 'ask_volume', 'bid_volume', 'mid_volume', 'no_side_volume', 'sweep_volume', 'multi_leg_volume',
    'floor_volume', 'stock_multi_leg_volume', 'last_price', 'avg_price', 'high_price', 'low_price', 'nbbo_ask',
    'nbbo_bid', 'total_premium', 'last_tape_time',
)

ENDPOINTS: dict[str, Endpoint] = {
    'flow_alerts': Endpoint(
        'flow_alerts', 'eod', '/api/option-trades/flow-alerts', ('id',), FLOW_ALERT_COLUMNS,
        page_limit=200, page_limit_fallback=100, max_pages=60, paging='older_than', time_field='created_at',
        note='the market route with ticker_symbol (the per-name route answers without id or the times); '
             'min_premium 25000; newer_than the day\'s start, older_than walked back on created_at. '
             'SETTLED 2026-10-21: limit=200 accepted (200 rows a page, SPY 19:43–20:14Z in one page, so a day is '
             'several pages; the 100 fallback stays for a refusal); newer_than and older_than are both honoured '
             '(the window [04:00Z, 13:00Z) of the day answered empty, not the session before\'s rows); an index '
             'is filed under both roots (SPX 174 + SPXW 200 rows); index rows carry missing_periscope.'),
    'darkpool': Endpoint(
        'darkpool', 'eod', '/api/darkpool/{t}', ('tracking_id', 'executed_at', 'price', 'size'), DARKPOOL_COLUMNS,
        indices=False, page_limit=500, page_limit_fallback=200, max_pages=250, paging='older_than',
        time_field='executed_at',
        note='date=D and older_than walked back on executed_at (the per-name route takes older_than since 2024-05-30; '
             '/darkpool/recent ignores it). SETTLED 2026-10-21: limit=500 accepted (a page of 500 held 490 distinct '
             'rows — ten exact duplicates, 446 tracking_ids: the key is tracking_id+executed_at+price+size); '
             'date=D does NOT bound the rows (older_than=04:00Z of D answered the session before\'s prints), so the '
             'day is bounded by the recorder\'s own filter and the walk stops at the day\'s start; a page spans ~35 '
             'minutes of SPY\'s session, so a day is 10–20 pages (the 200 fallback stays for a refusal).'),
    'net_prem_ticks': Endpoint(
        'net_prem_ticks', 'eod', '/api/stock/{t}/net-prem-ticks', ('tape_time',), NET_PREM_COLUMNS,
        note='date=D, one call, a tick a minute from pre-market (SPY 510 rows 07:30–16:14 ET on 2026-10-21). SETTLED '
             '2026-10-21: an index answers (SPX 428 rows from 09:30 ET, the same 13 fields).'),
    'ohlc_1m': Endpoint(
        'ohlc_1m', 'eod', '/api/stock/{t}/ohlc/1m', ('start_time',), OHLC_COLUMNS, indices=False, page_limit=1000,
        page_limit_fallback=None,
        note='date=D&limit=1000: the day\'s whole tape, pre-market to after hours, every row kept and stamped '
             '(2026-10-21 at 16:37 ET: 669 bars — 242 pr from 04:00, 390 r 09:30–15:59, 37 po; a whole day ~870, '
             'under the limit; market_time r is the regular session, the 15:59 bar the last of it). An index '
             'answers 422 (cboe_index_access_missing) and is not asked.'),
    'oi_strike': Endpoint(
        'oi_strike', 'eod', '/api/stock/{t}/oi-per-strike', ('date', 'strike'), OI_STRIKE_COLUMNS,
        note='date=D, one call: call_oi and put_oi by strike, every expiry together (491 rows for SPY, 548 for SPX '
             'on 2026-10-21 — an index answers). The count dated D is the positions at the close of the session '
             'BEFORE D (UW publishes it about 06:45 on D).'),
    'chain': Endpoint(
        'chain', 'eod', '/api/stock/{t}/option-contracts', ('option_symbol',), CHAIN_COLUMNS, page_limit=500,
        page_limit_fallback=None, max_pages=40, paging='page', max_pages_index=150,
        note='exclude_zero_oi_chains=true, 500 a page, `page` from 0, a page short of 500 the last — the eod walk '
             '(_walk_pages) stops on the first short page, cap 40 (SETTLED 2026-10-21: SPY page 19 answered 125 '
             'rows, 9,625 contracts in 20 pages; SPX answers, both roots\' contracts in one chain, SPXW261021… '
             'first). Heaviest volume first, so an expiry\'s contracts are spread over the pages. open_interest is '
             'the count published on D (the session before\'s close), prev_oi the one before it. No date '
             'parameter: the route answers the current day only. `expiry=YYYY-MM-DD` filters to one date (SPY '
             '2026-10-21: 302 rows in one page, zero-OI contracts included — the paper tracker reads it so). AN INDEX: '
             'SPX\'s chain holds both roots (SPX monthlies and SPXW) — the first real EOD pass (2026-10-21) stopped at '
             'the 40-page cap with 20,000 rows (12,226 SPXW, 7,774 SPX; the open interest at the cut down to 3 '
             'contracts), so an index takes max_pages_index = 150 (75,000 rows) and stops on its short page as ever.'),
    'spot_strike': Endpoint(
        'spot_strike', 'scan', '/api/stock/{t}/spot-exposures/strike', ('strike',), SPOT_STRIKE_COLUMNS,
        page_limit=500, page_limit_fallback=None, max_pages=10, paging='page',
        note='the whole book by strike, every expiry together, as UW figured it at `time` (491 rows for SPY in one '
             'answer). SETTLED 2026-10-21: `page` is honoured — SPX page 0 answered 500 rows (strikes 200 → 7660) '
             'and page 1 the remaining 324, so SPX\'s book is 824 strikes over two pages; the cap of 10 pages is '
             'generous on purpose (5,000 strikes).'),
}
EOD_ENDPOINTS = [e for e in ENDPOINTS.values() if e.pass_ == 'eod']
SCAN_ENDPOINTS = [e for e in ENDPOINTS.values() if e.pass_ == 'scan']


# ---- time ---------------------------------------------------------------------------------------------------------------

def iso_z(t: dt.datetime) -> str:
    """2026-10-21T20:15:03Z — a UTC instant, to the second"""
    return t.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_ts(v) -> dt.datetime | None:
    """An ISO string (Z, an offset, microseconds) or an epoch in milliseconds → an aware UTC datetime; else None"""
    if v is None or v == '':
        return None
    if isinstance(v, (int, float)) or (isinstance(v, str) and re.fullmatch(r'\d{12,14}', v)):
        return dt.datetime.fromtimestamp(int(v) / 1000, tz=UTC)
    if isinstance(v, str):
        s = v.strip()
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'
        try:
            t = dt.datetime.fromisoformat(s)
        except ValueError:
            return None
        if t.tzinfo is None:
            t = t.replace(tzinfo=UTC)
        return t.astimezone(UTC)
    return None


def ny_day_of(t: dt.datetime) -> str:
    return t.astimezone(NY).strftime('%Y-%m-%d')


def ny_at(day: str, hhmm: str) -> dt.datetime:
    """The New York wall time hh:mm on `day`, as a UTC instant"""
    h, m = hhmm.split(':')
    return dt.datetime.fromisoformat(day).replace(hour=int(h), minute=int(m), tzinfo=NY).astimezone(UTC)


def day_bounds(day: str) -> tuple[dt.datetime, dt.datetime]:
    """The New York day as [00:00 of D, 00:00 of D+1) in UTC"""
    start = ny_at(day, '00:00')
    nxt = (dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat()
    return start, ny_at(nxt, '00:00')


def is_trading_day(day: str) -> bool:
    return dt.date.fromisoformat(day).weekday() < 5 and day not in HOLIDAYS


def is_half_day(day: str) -> bool:
    return day in HALF_DAYS


def events_for(day: str) -> list[tuple[str, str, dt.datetime]]:
    """The passes of one day: (label, kind, when in UTC), scans then the EOD; empty when the market is shut"""
    if not is_trading_day(day):
        return []
    scans = HALF_DAY_SCAN_TIMES if is_half_day(day) else SCAN_TIMES
    eod = HALF_DAY_EOD_TIME if is_half_day(day) else EOD_TIME
    out = [(t, 'scan', ny_at(day, t)) for t in scans]
    out.append(('eod', 'eod', ny_at(day, eod)))
    return out


def next_event(now: dt.datetime) -> tuple[str, str, str, dt.datetime]:
    """The first pass strictly after `now`: (day, label, kind, when) — looking up to 30 days ahead"""
    d = dt.date.fromisoformat(ny_day_of(now))
    for _ in range(31):
        day = d.isoformat()
        for label, kind, when in events_for(day):
            if when > now:
                return day, label, kind, when
        d += dt.timedelta(days=1)
    raise RuntimeError('no trading day in the next month — extend HOLIDAYS?')


def due_now(now: dt.datetime, window_min: int = 4) -> tuple[str, str, str, dt.datetime] | None:
    """For --auto and cron: the pass the clock calls for — a scan within ±window of its time, the EOD once its time
    has passed (until midnight New York); None when nothing is due"""
    day = ny_day_of(now)
    events = events_for(day)
    if not events:
        return None
    for label, kind, when in events:
        if kind == 'scan' and abs((now - when).total_seconds()) <= window_min * 60:
            return day, label, kind, when
    label, kind, when = events[-1]
    if now >= when:
        return day, label, kind, when
    return None


# ---- the clock (real or fake, so the limiter and the retries are testable without wall time) -----------------------------

class Clock:
    def now(self) -> float:
        return time.monotonic()

    def utcnow(self) -> dt.datetime:
        return dt.datetime.now(UTC)

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)


class FakeClock(Clock):
    """Time that moves only when something sleeps — the dry run and the tests"""

    def __init__(self, start_utc: dt.datetime | None = None):
        self._t = 0.0
        self._start = start_utc or dt.datetime(2026, 10, 21, 20, 15, tzinfo=UTC)
        self.slept: list[float] = []
        self._lock = threading.Lock()

    def now(self) -> float:
        return self._t

    def utcnow(self) -> dt.datetime:
        return self._start + dt.timedelta(seconds=self._t)

    def sleep(self, seconds: float) -> None:
        with self._lock:
            self.slept.append(seconds)
            self._t += max(0.0, seconds)


# ---- the scrubber and the log ----------------------------------------------------------------------------------------------

class Scrub:
    """Every message passes through it: the token's value, a Bearer value, a token= query"""

    def __init__(self, token: str | None):
        self.token = token or ''

    def __call__(self, text) -> str:
        s = str(text)
        if len(self.token) >= 8:
            s = s.replace(self.token, '[token]')
        s = re.sub(r'(Bearer\s+)[A-Za-z0-9._-]{8,}', r'\1[token]', s)
        s = re.sub(r'([?&](?:token|api_key|apiKey)=)[^&\s"\']+', r'\1[token]', s, flags=re.IGNORECASE)
        return s


class ScrubFormatter(logging.Formatter):
    def __init__(self, scrub: Scrub):
        super().__init__('%(asctime)s %(levelname)s %(message)s', '%Y-%m-%dT%H:%M:%SZ')
        self.converter = time.gmtime
        self.scrub = scrub

    def format(self, record: logging.LogRecord) -> str:
        return self.scrub(super().format(record))


class ListHandler(logging.Handler):
    """Keeps the formatted lines — the tests read them"""

    def __init__(self, scrub: Scrub):
        super().__init__()
        self.lines: list[str] = []
        self.setFormatter(ScrubFormatter(scrub))

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(self.format(record))


def make_logger(scrub: Scrub, log_dir: Path | None, stream=None, name: str = 'eod_recorder') -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    log.propagate = False
    for h in list(log.handlers):
        log.removeHandler(h)
    if stream is not None:
        h = logging.StreamHandler(stream)
        h.setFormatter(ScrubFormatter(scrub))
        log.addHandler(h)
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / f'recorder-{dt.datetime.now(UTC):%Y-%m-%d}.log', encoding='utf-8')
        fh.setFormatter(ScrubFormatter(scrub))
        log.addHandler(fh)
    return log


# ---- the limiter --------------------------------------------------------------------------------------------------------------

class BudgetExhausted(RuntimeError):
    pass


class RateLimiter:
    """At most `max_in_flight` calls out at once, `per_minute` a minute (a token bucket that starts full), and a daily
    budget counted across restarts (`spent` loaded, `on_spend` saves). `acquire` blocks; `release` after the answer."""

    def __init__(self, max_in_flight: int = 3, per_minute: int = 100, daily_budget: int = 20_000,
                 clock: Clock | None = None, spent: int = 0, on_spend=None):
        self.max_in_flight = max(1, int(max_in_flight))
        self.capacity = float(max(1, per_minute))
        self.rate = self.capacity / 60.0
        self.budget = int(daily_budget)
        self.clock = clock or Clock()
        self.spent = int(spent)
        self.on_spend = on_spend
        self.cv = threading.Condition()
        self.in_flight = 0
        self.tokens = self.capacity
        self.last = self.clock.now()
        self.waited_s = 0.0

    def _refill(self) -> None:
        now = self.clock.now()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now

    def reset_spent(self, spent: int, on_spend=None) -> None:
        with self.cv:
            self.spent = int(spent)
            if on_spend is not None:
                self.on_spend = on_spend

    @property
    def remaining(self) -> int:
        return max(0, self.budget - self.spent)

    def acquire(self) -> None:
        while True:
            with self.cv:
                if self.spent >= self.budget:
                    raise BudgetExhausted(f'the daily budget of {self.budget} calls is spent')
                self._refill()
                if self.in_flight >= self.max_in_flight:
                    self.cv.wait(0.25)
                    continue
                if self.tokens >= 1.0 - 1e-9:
                    self.tokens = max(0.0, self.tokens - 1.0)
                    self.in_flight += 1
                    self.spent += 1
                    spent, on_spend = self.spent, self.on_spend
                    break
                wait = max(0.01, (1.0 - self.tokens) / self.rate)  # the floor: a float a hair under 1 spun for ever
            self.waited_s += wait
            self.clock.sleep(min(wait, 60.0))
        if on_spend is not None:
            try:
                on_spend(spent)
            except Exception:
                pass

    def release(self) -> None:
        with self.cv:
            self.in_flight = max(0, self.in_flight - 1)
            self.cv.notify()


# ---- the client ----------------------------------------------------------------------------------------------------------------

@dataclass
class Answer:
    status: int
    rows: list
    elapsed_ms: int
    error: str | None = None
    body: object = None
    attempts: int = 1

    @property
    def ok(self) -> bool:
        return self.status == 200 and self.error is None


def rows_of(body) -> list:
    if isinstance(body, list):
        return [r for r in body if isinstance(r, dict)]
    if isinstance(body, dict):
        d = body.get('data')
        if isinstance(d, list):
            return [r for r in d if isinstance(r, dict)]
        if isinstance(d, dict) and isinstance(d.get('chains'), list):
            return [r for r in d['chains'] if isinstance(r, dict)]
    return []


def query_of(params: dict | None) -> str:
    items = [(k, v) for k, v in (params or {}).items() if v is not None]
    return urllib.parse.urlencode(items, doseq=True) if items else ''


class UwClient:
    """GET a vendor path through the limiter, with the retries; the token in the header alone, never in a message"""

    def __init__(self, token: str, limiter: RateLimiter, log: logging.Logger, clock: Clock, scrub: Scrub,
                 timeout_s: float = 60.0, base: str = BASE_URL, opener=None):
        if not token:
            raise SystemExit('UW_API_TOKEN is not set — the recorder sends nothing without it')
        self._token = token
        self.limiter = limiter
        self.log = log
        self.clock = clock
        self.scrub = scrub
        self.timeout_s = timeout_s
        self.base = base
        self.opener = opener or urllib.request.build_opener()
        self.calls = 0

    def _once(self, url: str) -> tuple[int, bytes, str | None, str | None]:
        """status, body, retry_after, error — one try"""
        req = urllib.request.Request(url, headers={
            'Authorization': 'Bearer ' + self._token, 'Accept': 'application/json', 'User-Agent': USER_AGENT})
        try:
            with self.opener.open(req, timeout=self.timeout_s) as res:
                return int(res.status), res.read(), None, None
        except urllib.error.HTTPError as e:
            try:
                body = e.read()
            except Exception:
                body = b''
            return int(e.code), body, e.headers.get('Retry-After') if e.headers else None, None
        except Exception as e:  # URLError, TimeoutError, a reset — the network said no before the vendor could
            return 0, b'', None, self.scrub(f'{type(e).__name__}: {e}')

    def get(self, path: str, params: dict | None = None) -> Answer:
        q = query_of(params)
        url = self.base + path + ('?' + q if q else '')
        shown = path + ('?' + q if q else '')
        last: Answer | None = None
        for attempt in range(1, RETRIES + 1):
            self.limiter.acquire()
            t0 = self.clock.now()
            try:
                status, body, retry_after, err = self._once(url)
            finally:
                self.limiter.release()
            elapsed = int((self.clock.now() - t0) * 1000)
            self.calls += 1
            self.log.info('GET %s -> %s %dms%s', shown, status if status else 'network', elapsed,
                          f' try {attempt}' if attempt > 1 else '')
            if status == 200:
                try:
                    parsed = json.loads(body.decode('utf-8'))
                except Exception as e:
                    return Answer(200, [], elapsed, error=self.scrub(f'unreadable body: {type(e).__name__}'),
                                  attempts=attempt)
                return Answer(200, rows_of(parsed), elapsed, body=parsed, attempts=attempt)
            text = self.scrub(body.decode('utf-8', 'replace')[:300]) if body else (err or '')
            last = Answer(status, [], elapsed, error=f'{status or "network"}: {text}', attempts=attempt)
            if status == 429 or status >= 500 or status == 0:
                wait = BACKOFF_S[min(attempt - 1, len(BACKOFF_S) - 1)]
                if retry_after and re.fullmatch(r'\d+', retry_after.strip()):
                    wait = min(int(retry_after), MAX_RETRY_AFTER_S)
                if attempt < RETRIES:
                    self.log.warning('%s on %s — waiting %ss (try %d of %d)', status or 'network', shown, wait,
                                     attempt, RETRIES)
                    self.clock.sleep(wait)
                    continue
                last.error = f'gave up after {RETRIES} tries — last {last.error}'
                return last
            return last  # another 4xx: recorded, passed over
        return last  # unreachable


# ---- the fake client (the dry run and the tests: no network) ---------------------------------------------------------------------

DEFAULT_FIXTURES = REPO / 'tests' / 'fixtures' / 'uw_templates.json'


class FakeUwClient:
    """Serves the shapes a live answer carried (tests/fixtures/uw_templates.json, one template row an endpoint) with
    rows made up for the day asked: the same limiter, the same paging rules, a `fail_plan` to stage errors.
    It honours older_than and `limit` but deliberately IGNORES newer_than and date=D on the paged routes, so the
    recorder's own day filter is exercised; darkpool refuses limit > 200 (422) so the fallback is exercised."""

    def __init__(self, limiter: RateLimiter, log: logging.Logger, clock: Clock, scrub: Scrub,
                 fixtures: Path = DEFAULT_FIXTURES, counts: dict | None = None, fail_plan: dict | None = None):
        self.limiter, self.log, self.clock, self.scrub = limiter, log, clock, scrub
        self.templates = json.loads(Path(fixtures).read_text(encoding='utf-8'))
        self.counts = {'flow_alerts': 450, 'darkpool': 1300, 'chain': 1234, 'spot_strike': 491,
                       'spot_strike_index': 1100, 'ohlc_1m': 746, 'net_prem_ticks': 390, 'oi_strike': 491}
        if counts:
            self.counts.update(counts)
        self.fail_plan = dict(fail_plan or {})
        self.requests: list[tuple[str, dict]] = []
        self.calls = 0
        self._lock = threading.Lock()

    # -- staging --
    def _staged(self, path: str) -> int | Exception | None:
        for prefix, plan in self.fail_plan.items():
            if path.startswith(prefix) and plan:
                return plan.pop(0)
        return None

    def get(self, path: str, params: dict | None = None) -> Answer:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        shown = path + ('?' + query_of(params) if params else '')
        last = None
        for attempt in range(1, RETRIES + 1):
            self.limiter.acquire()
            t0 = self.clock.now()
            try:
                with self._lock:
                    self.requests.append((path, dict(params)))
                    self.calls += 1
                    staged = self._staged(path)
                if isinstance(staged, Exception):
                    status, rows, err, retry_after = 0, [], self.scrub(f'{type(staged).__name__}: {staged}'), None
                elif isinstance(staged, int):
                    status, rows, err, retry_after = staged, [], f'{staged}: staged', ('3' if staged == 429 else None)
                else:
                    status, rows, err, retry_after = self._serve(path, params)
            finally:
                self.limiter.release()
            elapsed = int((self.clock.now() - t0) * 1000)
            self.log.info('GET %s -> %s %dms%s (fake)', shown, status if status else 'network', elapsed,
                          f' try {attempt}' if attempt > 1 else '')
            if status == 200:
                return Answer(200, rows, elapsed, body={'data': rows}, attempts=attempt)
            last = Answer(status, [], elapsed, error=err, attempts=attempt)
            if status == 429 or status >= 500 or status == 0:
                wait = BACKOFF_S[min(attempt - 1, len(BACKOFF_S) - 1)]
                if retry_after:
                    wait = int(retry_after)
                if attempt < RETRIES:
                    self.log.warning('%s on %s — waiting %ss (try %d of %d)', status or 'network', shown, wait,
                                     attempt, RETRIES)
                    self.clock.sleep(wait)
                    continue
                last.error = f'gave up after {RETRIES} tries — last {last.error}'
                return last
            return last
        return last

    # -- the made-up day --
    def _serve(self, path: str, params: dict):
        m = re.fullmatch(r'/api/stock/([^/]+)/(.+)', path)
        if path == '/api/option-trades/flow-alerts':
            return self._flow_alerts(params)
        if path.startswith('/api/darkpool/'):
            return self._darkpool(path.rsplit('/', 1)[1], params)
        if m:
            name, route = m.group(1), m.group(2)
            if route == 'net-prem-ticks':
                return self._minutes('net_prem_ticks', name, params, 'tape_time', 390, 60)
            if route == 'ohlc/1m':
                if name in INDEX_NAMES:
                    return 422, [], '422: {"msg":"cboe_index_access_missing"}', None
                return self._minutes('ohlc_1m', name, params, 'start_time', self.counts['ohlc_1m'], 60, pre=240)
            if route == 'oi-per-strike':
                return 200, self._strikes('oi_strike', name, params, self.counts['oi_strike']), None, None
            if route == 'spot-exposures/strike':
                n = self.counts['spot_strike_index'] if name in INDEX_NAMES else self.counts['spot_strike']
                return self._paged_by_page('spot_strike', name, params, n)
            if route == 'option-contracts':
                return self._paged_by_page('chain', name, params, self.counts['chain'])
        return 404, [], '404: {"msg":"no such route in the fake"}', None

    def _day(self, params: dict) -> str:
        d = params.get('date') or params.get('_day')
        if d:
            return str(d)
        ot = parse_ts(params.get('older_than'))
        return ny_day_of(ot - dt.timedelta(seconds=1)) if ot else ny_day_of(self.clock.utcnow())

    def _flow_alerts(self, params: dict):
        root = str(params.get('ticker_symbol', 'SPY'))
        day = self._day(params)
        start, _ = day_bounds(day)
        n = self.counts['flow_alerts'] if root not in ('SPXW', 'NDXP', 'RUTW', 'VIXW') else 40
        tpl = self.templates['flow_alerts']
        rows = []
        for i in range(n + 6):  # six before the day's start — the recorder must drop them
            t = start + dt.timedelta(hours=9, minutes=31) + dt.timedelta(seconds=i * 52) if i < n \
                else start - dt.timedelta(hours=1, minutes=i - n)
            r = dict(tpl)
            r.update({'id': f'fa-{root}-{day}-{i}', 'ticker': root, 'created_at': t.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                      'start_time': int(t.timestamp() * 1000) - 1800, 'end_time': int(t.timestamp() * 1000),
                      'total_premium': str(25_000 + (i * 7919) % 400_000), 'strike': str(700 + i % 40),
                      'has_sweep': i % 3 == 0, 'has_floor': i % 11 == 0, 'type': 'put' if i % 2 else 'call'})
            if root in INDEX_NAMES or root in ('SPXW', 'NDXP', 'RUTW', 'VIXW'):
                r['missing_periscope'] = True     # as the live SPX and SPXW rows carried it (2026-10-21 smoke)
            rows.append(r)
        rows.sort(key=lambda r: r['created_at'], reverse=True)
        older = parse_ts(params.get('older_than'))
        if older:
            rows = [r for r in rows if parse_ts(r['created_at']) < older]
        limit = int(params.get('limit', 50))
        return 200, rows[:limit], None, None

    def _darkpool(self, name: str, params: dict):
        limit = int(params.get('limit', 100))
        if limit > 200:
            return 422, [], '422: {"msg":"limit must be smaller than 200"}', None
        day = self._day(params)
        start, _ = day_bounds(day)
        n = self.counts['darkpool']
        tpl = self.templates['darkpool']
        rows = []
        for i in range(n + 4):
            t = start + dt.timedelta(hours=9, minutes=30) + dt.timedelta(seconds=i * 18) if i < n \
                else start - dt.timedelta(minutes=5 + i - n)
            r = dict(tpl)
            r.update({'tracking_id': 71_000_000_000 + i * 97, 'ticker': name,
                      'executed_at': t.strftime('%Y-%m-%dT%H:%M:%SZ'), 'trf_executed_at': t.strftime('%Y-%m-%dT%H:%M:%SZ'),
                      'size': str(100 * (1 + i % 50)), 'price': f'{777 + (i % 90) / 100:.2f}',
                      'nbbo_bid': f'{777 + (i % 90) / 100 - 0.01:.2f}', 'nbbo_ask': f'{777 + (i % 90) / 100 + 0.01:.2f}'})
            rows.append(r)
        rows.sort(key=lambda r: r['executed_at'], reverse=True)
        older = parse_ts(params.get('older_than'))
        if older:
            rows = [r for r in rows if parse_ts(r['executed_at']) < older]
        return 200, rows[:limit], None, None

    def _minutes(self, ep: str, name: str, params: dict, tfield: str, n: int, step_s: int, pre: int = 0):
        day = self._day(params)
        start, _ = day_bounds(day)
        tpl = self.templates[ep]
        rows = []
        for i in range(n):
            t = start + dt.timedelta(hours=9, minutes=30) + dt.timedelta(seconds=(i - pre) * step_s)
            r = dict(tpl)
            r[tfield] = t.strftime('%Y-%m-%dT%H:%M:%S.%fZ') if ep == 'net_prem_ticks' else t.strftime('%Y-%m-%dT%H:%M:%SZ')
            if ep == 'ohlc_1m':
                r['end_time'] = (t + dt.timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
                r['market_time'] = 'pr' if i < pre else ('r' if i < pre + 390 else 'po')
            else:
                r['date'] = day
            rows.append(r)
        rows.sort(key=lambda r: r[tfield], reverse=True)
        return 200, rows, None, None

    def _strikes(self, ep: str, name: str, params: dict, n: int) -> list:
        day = self._day(params)
        tpl = self.templates[ep]
        step = 5 if name in INDEX_NAMES else 1
        base = 2000 if name in INDEX_NAMES else 50
        rows = []
        for i in range(n):
            r = dict(tpl)
            r.update({'strike': str(base + i * step), 'date': day})
            if ep == 'spot_strike':
                r.update({'ticker': name, 'time': iso_z(self.clock.utcnow()),
                          'price': '7800' if name in INDEX_NAMES else '778.05',
                          'call_gamma_oi': f'{(i * 131) % 9000 / 7:.2f}', 'put_gamma_oi': f'{-((i * 71) % 11000) / 5:.2f}'})
            elif ep == 'chain':
                exp = (dt.date.fromisoformat(day) + dt.timedelta(days=i % 45)).strftime('%y%m%d')
                r.update({'option_symbol': f'{name}{exp}{"P" if i % 2 else "C"}{int((base + i * step) * 1000):08d}',
                          'open_interest': (i * 37) % 9000 + 1, 'prev_oi': (i * 37) % 9000})
                r.pop('date', None)    # the live chain row carries neither (data-feed-samples.md)
                r.pop('strike', None)
            rows.append(r)
        return rows

    def _paged_by_page(self, ep: str, name: str, params: dict, n: int):
        limit = int(params.get('limit', 50))
        page = int(params.get('page', 0))
        rows = self._strikes(ep, name, params, n)
        return 200, rows[page * limit:(page + 1) * limit], None, None


# ---- the store: append-only Parquet, idempotent ----------------------------------------------------------------------------------

def stringify(v) -> str | None:
    """Every vendor value kept as text: the numeric strings as sent, a bool as true/false, a list or object as JSON"""
    if v is None:
        return None
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, (int, float)):
        return repr(v) if isinstance(v, float) else str(v)
    if isinstance(v, str):
        return v
    return json.dumps(v, separators=(',', ':'), sort_keys=True)


def row_key(ep: Endpoint, row: dict, scan: str | None = None) -> str:
    """The row's identity for the dedupe: the vendor's id fields; a row with none of them, its whole content. A scan
    endpoint's row belongs to its scan (the same strike stands in every snapshot), so the scan label leads the key."""
    vals = [stringify(row.get(k)) for k in ep.dedupe]
    if all(v is None for v in vals):
        vals = [json.dumps({k: stringify(v) for k, v in sorted(row.items())}, separators=(',', ':'))]
    if ep.pass_ == 'scan':
        vals = [scan or ''] + vals
    return hashlib.sha1('|'.join('' if v is None else v for v in vals).encode('utf-8')).hexdigest()[:24]


@dataclass
class Marker:
    endpoint: str
    name: str
    day: str
    scan: str
    status: str            # 'done' | 'partial'
    rows_fetched: int = 0
    rows_added: int = 0
    pages: int = 0
    calls: int = 0
    fetched_at: str = ''
    note: str = ''
    version: str = VERSION

    def as_dict(self) -> dict:
        return self.__dict__.copy()


class Store:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # -- files --
    def file(self, endpoint: str, name: str, day: str) -> Path:
        return self.root / endpoint / name / f'{day}.parquet'

    def read(self, endpoint: str, name: str, day: str) -> pl.DataFrame | None:
        f = self.file(endpoint, name, day)
        return pl.read_parquet(f) if f.exists() else None

    def append(self, ep: Endpoint, name: str, day: str, rows: list, stamps: dict, tags: dict | None = None) -> tuple[int, int]:
        """Adds the rows the file does not hold (by `_key`); never changes or drops a row. Returns (added, total).
        `tags`: columns written on every row of this append (the macro stamps), after the vendor's — never in the key."""
        tags = dict(tags or {})
        extras = sorted({k for r in rows for k in r.keys()} - set(ep.columns) - set(STAMPS) - set(tags))
        cols = STAMPS + list(ep.columns) + extras + [k for k in tags if k not in ep.columns]
        data = {c: [] for c in cols}
        for r in rows:
            key = row_key(ep, r, stamps.get('_scan'))
            for c in cols:
                if c == '_key':
                    data[c].append(key)
                elif c in STAMPS:
                    data[c].append(stamps.get(c))
                elif c in tags:
                    data[c].append(stringify(tags[c]))
                else:
                    data[c].append(stringify(r.get(c)))
        new = pl.DataFrame(data, schema={c: pl.Utf8 for c in cols})
        with self._lock:
            old = self.read(ep.key, name, day)
            if old is None:
                both = new
            else:
                for c in old.columns:
                    if old.schema[c] != pl.Utf8:
                        old = old.with_columns(pl.col(c).cast(pl.Utf8))
                both = pl.concat([old, new], how='diagonal_relaxed')
            both = both.unique(subset=['_key'], keep='first', maintain_order=True)
            total = both.height
            added = total - (old.height if old is not None else 0)
            if added > 0 or old is None:
                f = self.file(ep.key, name, day)
                f.parent.mkdir(parents=True, exist_ok=True)
                tmp = f.with_name(f.name + '.tmp')
                both.write_parquet(tmp, compression='zstd')
                os.replace(tmp, f)
        return added, total

    # -- markers: one per (endpoint, name, day, scan) --
    def marker_file(self, endpoint: str, name: str, day: str, scan: str) -> Path:
        return self.root / '_markers' / endpoint / name / day / f'{scan.replace(":", "")}.json'

    def marker(self, endpoint: str, name: str, day: str, scan: str) -> Marker | None:
        f = self.marker_file(endpoint, name, day, scan)
        if not f.exists():
            return None
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
            return Marker(**{k: d[k] for k in Marker.__dataclass_fields__ if k in d})
        except Exception:
            return None

    def set_marker(self, m: Marker) -> None:
        f = self.marker_file(m.endpoint, m.name, m.day, m.scan)
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + '.tmp')
        tmp.write_text(json.dumps(m.as_dict(), indent=1), encoding='utf-8')
        os.replace(tmp, f)

    # -- failures and the budget --
    def record_failure(self, day: str, entry: dict) -> None:
        d = self.root / '_failures'
        d.mkdir(parents=True, exist_ok=True)
        with self._lock:
            with open(d / f'{day}.jsonl', 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, separators=(',', ':')) + '\n')

    def budget_file(self, day: str) -> Path:
        return self.root / '_budget' / f'{day}.json'

    def budget_spent(self, day: str) -> int:
        f = self.budget_file(day)
        if not f.exists():
            return 0
        try:
            return int(json.loads(f.read_text(encoding='utf-8')).get('spent', 0))
        except Exception:
            return 0

    def budget_saver(self, day: str):
        f = self.budget_file(day)
        f.parent.mkdir(parents=True, exist_ok=True)

        def save(spent: int) -> None:
            tmp = f.with_name(f.name + '.tmp')
            tmp.write_text(json.dumps({'day': day, 'spent': spent, 'at': iso_z(dt.datetime.now(UTC))}),
                           encoding='utf-8')
            os.replace(tmp, f)
        return save

    # -- status --
    def status(self) -> list[dict]:
        out = []
        for ep in sorted(ENDPOINTS):
            d = self.root / ep
            if not d.is_dir():
                continue
            for name_dir in sorted(p for p in d.iterdir() if p.is_dir()):
                for f in sorted(name_dir.glob('*.parquet')):
                    day = f.stem
                    try:
                        rows = pl.scan_parquet(f).select(pl.len()).collect().item()
                    except Exception as e:
                        rows = f'unreadable ({type(e).__name__})'
                    mdir = self.root / '_markers' / ep / name_dir.name / day
                    marks = {}
                    if mdir.is_dir():
                        for mf in sorted(mdir.glob('*.json')):
                            try:
                                marks[mf.stem] = json.loads(mf.read_text(encoding='utf-8')).get('status', '?')
                            except Exception:
                                marks[mf.stem] = '?'
                    out.append({'endpoint': ep, 'name': name_dir.name, 'day': day, 'rows': rows,
                                'done': sum(1 for v in marks.values() if v == 'done'),
                                'partial': sum(1 for v in marks.values() if v == 'partial'),
                                'size_kb': round(f.stat().st_size / 1024, 1)})
        return out


# ---- the recorder -------------------------------------------------------------------------------------------------------------------

@dataclass
class Fetched:
    rows: list = field(default_factory=list)
    pages: int = 0
    calls: int = 0
    complete: bool = True
    note: str = ''
    error: str | None = None


def alert_roots(name: str) -> list[str]:
    return ALERT_ROOTS.get(name, [name])


class Recorder:
    def __init__(self, client, store: Store, limiter: RateLimiter, log: logging.Logger, clock: Clock, scrub: Scrub,
                 names: list[str] | None = None, min_premium: int = MIN_PREMIUM, max_pages: int | None = None):
        self.client, self.store, self.limiter, self.log, self.clock, self.scrub = client, store, limiter, log, clock, scrub
        self.names = list(names or DEFAULT_NAMES)
        self.min_premium = int(min_premium)
        self.max_pages = max_pages           # an override (the smoke test asks one page)
        self._limits: dict[str, int] = {}    # the `limit` a route accepted, after a fallback
        self._budget_day = ''

    # -- the budget follows the New York day --
    def _budget_for(self, day: str) -> None:
        if day != self._budget_day:
            self.limiter.reset_spent(self.store.budget_spent(day), self.store.budget_saver(day))
            self._budget_day = day

    # -- one call with the limit fallback --
    def _get(self, ep: Endpoint, path: str, params: dict) -> Answer:
        if ep.page_limit is not None:
            params = dict(params, limit=self._limits.get(ep.key, ep.page_limit))
        ans = self.client.get(path, params)
        if (ans.status == 422 and ep.page_limit_fallback is not None and 'limit' in params
                and params['limit'] != ep.page_limit_fallback and 'limit' in (ans.error or '').lower()):
            self.log.warning('%s refused limit=%s — asking %s from now on', ep.key, params['limit'], ep.page_limit_fallback)
            self._limits[ep.key] = ep.page_limit_fallback
            first = ans.attempts
            ans = self.client.get(path, dict(params, limit=ep.page_limit_fallback))
            ans.attempts += first
        return ans

    def _pages(self, ep: Endpoint, name: str | None = None) -> int:
        if self.max_pages is not None:
            return self.max_pages
        if name in INDEX_NAMES and ep.max_pages_index is not None:
            return ep.max_pages_index
        return ep.max_pages

    # -- the fetchers --
    def fetch(self, ep: Endpoint, name: str, day: str, now: dt.datetime) -> Fetched:
        if name in INDEX_NAMES and not ep.indices:
            return Fetched(complete=True, note='an index: not asked (no stock prints; bars are a CBOE grant)')
        if ep.key == 'flow_alerts':
            return self._fetch_flow_alerts(ep, name, day, now)
        if ep.paging == 'older_than':
            return self._walk_older_than(ep, ep.path.format(t=name), {'date': day}, name, day, now)
        if ep.paging == 'page':
            return self._walk_pages(ep, ep.path.format(t=name), {'exclude_zero_oi_chains': 'true'} if ep.key == 'chain' else {}, name)
        params = {'date': day}
        ans = self._get(ep, ep.path.format(t=name), params)
        if not ans.ok:
            return Fetched(calls=ans.attempts, complete=False, error=ans.error)
        return Fetched(rows=ans.rows, pages=1, calls=ans.attempts)

    def _fetch_flow_alerts(self, ep: Endpoint, name: str, day: str, now: dt.datetime) -> Fetched:
        out = Fetched()
        for root in alert_roots(name):
            part = self._walk_older_than(ep, ep.path, {'ticker_symbol': root, 'min_premium': self.min_premium}, name, day, now)
            out.rows.extend(part.rows)
            out.pages += part.pages
            out.calls += part.calls
            out.complete = out.complete and part.complete
            if part.note:
                out.note = (out.note + '; ' if out.note else '') + f'{root}: {part.note}'
            if part.error:
                out.error = (out.error + '; ' if out.error else '') + f'{root}: {part.error}'
        return out

    def _walk_older_than(self, ep: Endpoint, path: str, base: dict, name: str, day: str, now: dt.datetime) -> Fetched:
        """Newest first, each page's oldest time the next page's older_than, until the day's start is crossed"""
        start, end = day_bounds(day)
        cursor = min(now, end)
        out = Fetched()
        seen: set[str] = set()
        for page in range(self._pages(ep)):
            params = dict(base, newer_than=iso_z(start), older_than=iso_z(cursor))
            ans = self._get(ep, path, params)
            out.calls += ans.attempts
            if not ans.ok:
                out.complete = False
                out.error = ans.error
                return out
            out.pages += 1
            times = [(r, parse_ts(r.get(ep.time_field))) for r in ans.rows]
            for r, t in times:
                if t is not None and start <= t < end:
                    k = row_key(ep, r)
                    if k not in seen:
                        seen.add(k)
                        out.rows.append(r)
            limit = self._limits.get(ep.key, ep.page_limit) or 0
            if not ans.rows or (limit and len(ans.rows) < limit):
                return out
            oldest = min((t for _, t in times if t is not None), default=None)
            if oldest is None:
                out.note = f'no {ep.time_field} on the rows — paging stopped'
                out.complete = False
                return out
            if oldest < start:
                return out
            if oldest >= cursor:
                out.note = 'older_than did not move the cursor — paging stopped'
                out.complete = False
                return out
            cursor = oldest
        out.note = f'page cap {self._pages(ep)} reached — the day may be incomplete'
        out.complete = False
        return out

    def _walk_pages(self, ep: Endpoint, path: str, base: dict, name: str | None = None) -> Fetched:
        out = Fetched()
        cap = self._pages(ep, name)
        for page in range(cap):
            ans = self._get(ep, path, dict(base, page=page))
            out.calls += ans.attempts
            if not ans.ok:
                out.complete = False
                out.error = ans.error
                return out
            out.pages += 1
            out.rows.extend(ans.rows)
            limit = self._limits.get(ep.key, ep.page_limit) or 0
            if not ans.rows or (limit and len(ans.rows) < limit):
                return out
        out.note = f'page cap {cap} reached — the answer may be incomplete'
        out.complete = False
        return out

    # -- the macro stamps: the day's releases on every row; the minutes to / since a release at a scan's time --
    def macro_tags(self, ep: Endpoint, day: str, scan_at: dt.datetime | None) -> dict:
        """is_macro_event_day, macro_events, minutes_to_macro_release and minutes_since_last_release
        (macro_calendar.py): a scan row reads the minutes at its scan time, an EOD row null; all null (one WARN) when
        the calendar is not on disk"""
        return MC.calendar(self.log).stamps(day, scan_at if ep.pass_ == 'scan' else None)

    # -- one job: an endpoint for a name, recorded and marked --
    def job(self, ep: Endpoint, name: str, day: str, scan: str, scan_at: dt.datetime, force: bool = False) -> dict:
        had = self.store.marker(ep.key, name, day, scan)
        if had and had.status == 'done' and not force:
            self.log.info('skip %s %s %s %s — recorded %s (%d rows)', ep.key, name, day, scan, had.fetched_at, had.rows_fetched)
            return {'endpoint': ep.key, 'name': name, 'skipped': True, 'rows': had.rows_fetched, 'added': 0, 'calls': 0}
        now = self.clock.utcnow()
        try:
            got = self.fetch(ep, name, day, now)
        except BudgetExhausted:
            raise
        except Exception as e:
            got = Fetched(complete=False, error=self.scrub(f'{type(e).__name__}: {e}'))
        added = total = 0
        if got.rows:
            stamps = {'_day': day, '_scan': scan, '_scan_at': iso_z(scan_at), '_fetched_at': iso_z(now), '_name': name}
            added, total = self.store.append(ep, name, day, got.rows, stamps, tags=self.macro_tags(ep, day, scan_at))
        status = 'done' if got.complete else 'partial'
        m = Marker(ep.key, name, day, scan, status, rows_fetched=len(got.rows), rows_added=added, pages=got.pages,
                   calls=got.calls, fetched_at=iso_z(now), note=self.scrub(got.note or got.error or ''))
        self.store.set_marker(m)
        if got.error:
            self.store.record_failure(day, {'at': iso_z(now), 'endpoint': ep.key, 'name': name, 'scan': scan,
                                            'error': self.scrub(got.error)})
            self.log.error('%s %s %s %s: %s', ep.key, name, day, scan, self.scrub(got.error))
        self.log.info('%s %s %s %s: %d rows fetched, %d new (file holds %d), %d page(s), %d call(s)%s', ep.key, name,
                      day, scan, len(got.rows), added, total, got.pages, got.calls, f' — {got.note}' if got.note else '')
        return {'endpoint': ep.key, 'name': name, 'skipped': False, 'rows': len(got.rows), 'added': added,
                'calls': got.calls, 'complete': got.complete, 'error': got.error}

    # -- a pass --
    def run_pass(self, kind: str, day: str, scan: str | None = None, scan_at: dt.datetime | None = None,
                 only: list[str] | None = None, names: list[str] | None = None, force: bool = False) -> dict:
        self._budget_for(day)
        eps = SCAN_ENDPOINTS if kind == 'scan' else EOD_ENDPOINTS
        if only:
            eps = [e for e in eps if e.key in only]
        scan = scan or ('eod' if kind == 'eod' else ny_at_label(self.clock.utcnow()))
        scan_at = scan_at or self.clock.utcnow()
        jobs = [(ep, n) for ep in eps for n in (names or self.names)]
        self.log.info('%s pass for %s (%s): %d jobs, %d names, budget %d of %d left', kind, day, scan, len(jobs),
                      len(names or self.names), self.limiter.remaining, self.limiter.budget)
        results: list[dict] = []
        stopped = {'budget': False}

        def run(job):
            ep, n = job
            if stopped['budget']:
                return {'endpoint': ep.key, 'name': n, 'skipped': True, 'rows': 0, 'added': 0, 'calls': 0,
                        'error': 'budget'}
            try:
                return self.job(ep, n, day, scan, scan_at, force=force)
            except BudgetExhausted as e:
                stopped['budget'] = True
                self.log.error('STOP: %s — the %s pass for %s ends here; the markers say what was recorded', e, kind, day)
                return {'endpoint': ep.key, 'name': n, 'skipped': True, 'rows': 0, 'added': 0, 'calls': 0,
                        'error': 'budget'}

        with ThreadPoolExecutor(max_workers=self.limiter.max_in_flight) as ex:
            results = list(ex.map(run, jobs))
        summary = {
            'kind': kind, 'day': day, 'scan': scan, 'jobs': len(jobs),
            'skipped': sum(1 for r in results if r.get('skipped')),
            'rows': sum(r['rows'] for r in results), 'added': sum(r['added'] for r in results),
            'calls': sum(r['calls'] for r in results),
            'failed': sum(1 for r in results if r.get('error') and r.get('error') != 'budget'),
            'incomplete': sum(1 for r in results if not r.get('skipped') and not r.get('complete', True)),
            'budget_stopped': stopped['budget'], 'budget_spent': self.limiter.spent,
        }
        self.log.info('%s pass for %s (%s) done: %d jobs, %d skipped, %d rows fetched, %d new, %d calls, %d failed, '
                      '%d incomplete, budget spent %d', kind, day, scan, summary['jobs'], summary['skipped'],
                      summary['rows'], summary['added'], summary['calls'], summary['failed'], summary['incomplete'],
                      summary['budget_spent'])
        return summary

    # -- the daemon --
    def daemon(self, stop: threading.Event | None = None, catch_up: bool = True) -> None:
        stop = stop or threading.Event()
        self.log.info('daemon up (%s): %d names, scans %s, EOD %s New York, Mon–Fri less %d holidays', VERSION,
                      len(self.names), ' '.join(SCAN_TIMES), EOD_TIME, len(HOLIDAYS))
        if catch_up:
            due = due_now(self.clock.utcnow())
            if due and due[2] == 'eod':
                self.log.info('the EOD pass for %s is due and not yet recorded in full — running it now', due[0])
                self.run_pass('eod', due[0], 'eod', due[3])
        while not stop.is_set():
            day, label, kind, when = next_event(self.clock.utcnow())
            wait = (when - self.clock.utcnow()).total_seconds()
            self.log.info('next: %s pass %s on %s at %s (in %.0f min)', kind, label, day, iso_z(when), wait / 60)
            while wait > 0 and not stop.is_set():
                self.clock.sleep(min(wait, 30.0))
                wait = (when - self.clock.utcnow()).total_seconds()
            if stop.is_set():
                break
            try:
                self.run_pass(kind, day, label, when)
            except Exception as e:
                self.log.error('the %s pass failed: %s', kind, self.scrub(f'{type(e).__name__}: {e}'))
            self.clock.sleep(1.0)

    # -- the smoke test: one call an endpoint, one name --
    def smoke(self, name: str, day: str) -> list[dict]:
        self._budget_for(day)
        self.max_pages = 1
        now = self.clock.utcnow()
        report = []
        for ep in list(EOD_ENDPOINTS) + list(SCAN_ENDPOINTS):
            got = self.fetch(ep, name, day, now)
            cols = sorted({k for r in got.rows for k in r.keys()})
            missing = [c for c in ep.columns if c not in cols] if got.rows else []
            extra = [c for c in cols if c not in ep.columns]
            entry = {'endpoint': ep.key, 'route': ep.path.format(t=name), 'status': 'ok' if not got.error else 'FAILED',
                     'rows': len(got.rows), 'pages': got.pages, 'calls': got.calls, 'error': got.error, 'note': got.note,
                     'columns': cols, 'missing_known': missing, 'new_columns': extra}
            if got.rows:
                stamps = {'_day': day, '_scan': 'smoke', '_scan_at': iso_z(now), '_fetched_at': iso_z(now), '_name': name}
                self.store.append(ep, name, day, got.rows, stamps)
                entry['first_row'] = {k: stringify(v) for k, v in got.rows[0].items()}
            report.append(entry)
        return report


def ny_at_label(t: dt.datetime) -> str:
    return t.astimezone(NY).strftime('%H:%M')


# ---- the command line ---------------------------------------------------------------------------------------------------------------

def read_names(path: str | None) -> list[str]:
    if not path:
        return list(DEFAULT_NAMES)
    out = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        s = line.split('#', 1)[0].strip().upper()
        if s:
            out.append(s)
    if not out:
        raise SystemExit(f'{path} names nothing')
    return out


def print_status(store: Store) -> None:
    rows = store.status()
    if not rows:
        print(f'nothing recorded under {store.root}')
        return
    print(f'{"endpoint":<15} {"name":<6} {"day":<10} {"rows":>9} {"done":>5} {"partial":>7} {"KB":>8}')
    for r in rows:
        print(f'{r["endpoint"]:<15} {r["name"]:<6} {r["day"]:<10} {str(r["rows"]):>9} {r["done"]:>5} {r["partial"]:>7} {r["size_kb"]:>8}')
    by_ep: dict[str, int] = {}
    for r in rows:
        if isinstance(r['rows'], int):
            by_ep[r['endpoint']] = by_ep.get(r['endpoint'], 0) + r['rows']
    print('\ntotals: ' + ', '.join(f'{k} {v:,}' for k, v in sorted(by_ep.items())))
    for f in sorted((store.root / '_budget').glob('*.json')) if (store.root / '_budget').is_dir() else []:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
            print(f'budget {d["day"]}: {d["spent"]:,} calls')
        except Exception:
            pass


def build(args, token: str | None, stream=sys.stderr):
    """The pieces for a run: the scrub, the log, the store, the limiter, the client (real or fake), the recorder"""
    scrub = Scrub(token)
    root = Path(args.data)
    if args.dry_run:
        root = root / 'dryrun'
    if args.smoke:
        root = root / 'smoke'
    store = Store(root)
    log = make_logger(scrub, root / '_logs', stream=stream)
    clock = FakeClock() if args.dry_run else Clock()
    limiter = RateLimiter(max_in_flight=args.in_flight, per_minute=args.per_minute, daily_budget=args.budget, clock=clock)
    if args.dry_run:
        client = FakeUwClient(limiter, log, clock, scrub, fixtures=Path(args.fixtures))
    else:
        client = UwClient(token or '', limiter, log, clock, scrub)
    rec = Recorder(client, store, limiter, log, clock, scrub, names=read_names(args.names), min_premium=args.min_premium)
    return rec, store, log, clock


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--eod', action='store_true', help='the 16:15 pass for --day (today New York by default)')
    mode.add_argument('--scan', action='store_true', help='one spot-exposures/strike snapshot a name, stamped --scan-time')
    mode.add_argument('--daemon', action='store_true', help='sleep until each scan time and the EOD, Mon–Fri, for ever')
    mode.add_argument('--auto', action='store_true', help='the pass the clock calls for now, or nothing (for cron)')
    mode.add_argument('--smoke', action='store_true', help='ONE call an endpoint for --name; prints the rows and the schema')
    mode.add_argument('--status', action='store_true', help='what each endpoint/name/day holds')
    p.add_argument('--dry-run', action='store_true', help='no network: the fake client on tests/fixtures, a fake clock')
    p.add_argument('--day', help='the New York day, YYYY-MM-DD (today by default)')
    p.add_argument('--scan-time', help='the scan label for --scan, HH:MM New York (now by default)')
    p.add_argument('--name', default='SPY', help='the one name for --smoke (SPY)')
    p.add_argument('--names', help='a file of names, one a line, in place of the built-in universe')
    p.add_argument('--only', help='a comma list of endpoints to run (flow_alerts,darkpool,…)')
    p.add_argument('--force', action='store_true', help='fetch again what a marker says is done (the dedupe still holds)')
    p.add_argument('--data', default=os.environ.get('RECORDER_DATA') or str(REPO / 'data_recorder'),
                   help='the data root (RECORDER_DATA, else data_recorder/ in the repo)')
    p.add_argument('--budget', type=int, default=int(os.environ.get('RECORDER_BUDGET') or 20_000),
                   help='calls a day before the run stops (RECORDER_BUDGET, 20000)')
    p.add_argument('--per-minute', type=int, default=100, help='calls a minute (100)')
    p.add_argument('--in-flight', type=int, default=3, help='calls out at once (3 — UW Basic\'s own limit)')
    p.add_argument('--min-premium', type=int, default=MIN_PREMIUM, help='the flow alerts\' floor (25000)')
    p.add_argument('--fixtures', default=str(DEFAULT_FIXTURES), help='the fake client\'s templates (--dry-run)')
    args = p.parse_args(argv)

    token = os.environ.get('UW_API_TOKEN')
    if args.status:
        print_status(Store(Path(args.data)))
        return 0
    if not args.dry_run and not token:
        print('UW_API_TOKEN is not set — set it in the environment (never in a file in the repo)', file=sys.stderr)
        return 2
    rec, store, log, clock = build(args, token)
    now = clock.utcnow()
    day = args.day or ny_day_of(now)
    only = [s.strip() for s in args.only.split(',') if s.strip()] if args.only else None
    for o in only or []:
        if o not in ENDPOINTS:
            print(f'no endpoint {o!r}; the endpoints are {", ".join(ENDPOINTS)}', file=sys.stderr)
            return 2

    if args.smoke:
        print(f'smoke: one call an endpoint for {args.name} on {day} → {store.root}  (the token stays in the header)')
        report = rec.smoke(args.name.upper(), day)
        for e in report:
            print(f'\n{e["endpoint"]:<15} {e["route"]}  {e["status"]}  rows {e["rows"]}  pages {e["pages"]}  calls {e["calls"]}')
            if e['error']:
                print(f'  error: {e["error"]}')
            if e['note']:
                print(f'  note: {e["note"]}')
            if e['rows']:
                print(f'  columns ({len(e["columns"])}): {", ".join(e["columns"])}')
                if e['missing_known']:
                    print(f'  known columns the answer did NOT carry: {", ".join(e["missing_known"])}')
                if e['new_columns']:
                    print(f'  columns NOT in the known list (kept as extras): {", ".join(e["new_columns"])}')
                print(f'  first row: {json.dumps(e["first_row"], separators=(",", ":"))[:600]}')
        print(f'\ncalls made: {rec.client.calls}; budget spent today: {rec.limiter.spent}')
        return 0
    if args.eod:
        s = rec.run_pass('eod', day, 'eod', ny_at(day, HALF_DAY_EOD_TIME if is_half_day(day) else EOD_TIME), only=only, force=args.force)
    elif args.scan:
        label = args.scan_time or ny_at_label(now)
        s = rec.run_pass('scan', day, label, ny_at(day, label) if args.scan_time else now, only=only, force=args.force)
    elif args.auto:
        due = due_now(now)
        if not due:
            print(f'nothing is due at {now.astimezone(NY):%Y-%m-%d %H:%M} New York')
            return 0
        d, label, kind, when = due
        s = rec.run_pass(kind, d, label, when, only=only, force=args.force)
    else:
        rec.daemon()
        return 0
    print(json.dumps(s))
    return 1 if s.get('budget_stopped') else 0


if __name__ == '__main__':
    sys.exit(main())
