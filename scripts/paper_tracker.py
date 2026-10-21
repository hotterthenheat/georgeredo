#!/usr/bin/env python3
"""
paper_tracker.py — the forward paper confirmation tracker for the Compass candidates: an isolated logger that records,
every session, each candidate's structure at its minutes from Unusual Whales' quotes, and after the close its
settlement and paper P&L — so the confirmation samples the reports asked for accumulate on their own. It touches no UI
and no discretionary signal; it writes Parquet and nothing else.

THE CANDIDATES (the rules reproduced from the reports; the strikes are picked exactly as their engines pick them):

  condor_em1  research_notes/Compass phase 2/hyp_b_boundary_theta.md "The rule, conditional on X": SPY, same-day
              expiry, at 11:30, 12:00, 12:30, 13:00 and 13:30 New York, every VIX. The ATM straddle M = call mid + put
              mid at the strike nearest spot with both sides quoted (a tie: the lower strike); short call = the first
              listed strike >= spot + M; short put = the first listed strike <= spot − M; wings 2 points (long call =
              short call + 2, long put = short put − 2). NBBO fill: the shorts at their bid, the longs at their ask;
              each spread's credit must be >= $0.05 (the condor's >= $0.10) or the row is logged `tradable=false`.
              Thresholds: 60 settled sessions (the report's X) and 120 (its re-read).
  fly5        research_notes/Compass phase 2/hyp_c_debit_flies.md section 6: SPY and QQQ, same-day expiry, at 15:00
              and 15:30 New York. K0 = the strike nearest spot with a call and a put quoted (a tie: the lower strike);
              wings ±5. Three structures a capture: the iron butterfly (sell the K0 call and put at the bid, buy the
              K0−5 put and the K0+5 call at the ask; max risk 5 − credit), the long call fly (buy K0−5 and K0+5 calls
              at the ask, sell two K0 calls at the bid; max risk = the debit) and the long put fly. A structure's max
              risk must be >= $0.05 and its short legs' bids > 0. Stress fills: every leg $0.01 and $0.02 worse than the
              NBBO. Threshold: 250 settled sessions a name. AT 15:58 every fly5 structure logged that day is read again
              off one chain a name (`close1558` rows): the four legs' NBBO, the package's liquidation value at the NBBO
              (sell what was bought at the bid, buy back what was sold at the ask) and at the mid, and the 15:58 exit
              P&L ($0.65 a contract to close; a long leg with no bid is left to expire, no fee) beside the 16:00
              intrinsic settlement — an in-the-money ETF option at the close is exercised or assigned in shares, which
              a cash account cannot carry (README).
  condor_d20  CANDIDATE 3, research_notes/Compass phase 3/hyp_e_short_premium_lift.md section 8, "needs X (1)": SPY,
              same-day expiry, at 13:00, 13:30, 14:00, 14:30 and 15:00 New York, every session, held to the close: the
              2-wide iron condor whose short call and short put are the OTM strikes whose Black-Scholes |delta| is
              nearest 0.20 — Hypothesis B's `nearest_delta` exactly (engine.py): r = q = 0, the vol implied by each
              option's own mid (total variance σ√τ by a 60-step bisection on [1e-5, 5]; only σ√τ enters delta, so τ to
              16:00 cancels), the candidates OTM (a call K > spot, a put K < spot) with mid > 0, ask > 0 and the mid
              under the no-arbitrage bound (a call's < spot, a put's < K); a tie in |delta − 0.20| goes to the FARTHER
              out-of-the-money strike (the code's np.lexsort order; its comment says "nearer-the-money" — the code is
              what produced the research, so the code is reproduced); longs 2 points beyond; fills and the tradable
              rule as condor_em1. Every capture row carries the live t2 decile of the FROZEN SPY volatility model
              (scripts/models/, vol_model.py) — the full model and the no-VIX model, each its own column, and the
              pre-registered primary (README) — a column, never a filter. Threshold: 150 settled sessions.
  fly_spxw    (ON by default since the owner's final patch, 2026-10-21 — 3–5 calls a session; --no-spxw turns it off) SPXW, the cash-settled equivalent of fly5: at
              15:00 and 15:30 the iron, call and put flies at ±5 and ±25 around K0 = the listed SPXW strike nearest SPX,
              off SPX's same-day chain (/option-contracts?expiry=D under SPX, the SPXW root alone). UW Basic has no SPX
              price (stock-state answers 422 for an index), so SPX is read off the same chain by put-call parity (r = q
              = 0, same day): the median of K + call mid − put mid over the three strikes where |call mid − put mid| is
              smallest — no extra call. Settled at 16:20 on `price` of SPX's /spot-exposures/strike (one call; UW's own
              SPX figure, a proxy for the official 16:00 SET, labelled so).

EVERY CAPTURE LOGS the four legs' NBBO at the minute (the route carries no quote sizes — those columns stay null,
README), the NBBO package price, the mid package price, the stresses, spot (UW's stock-state `close`) and the
straddle. THE SETTLEMENT PASS (16:20 New York) logs, a name: UW's ohlc/1m last regular bar's close (the 15:59 bar),
the bar stamped 16:00, the stock-state `close` at that minute and its `prev_close`, and the official close when UW's
daily bar (`/ohlc/1d`, the `r` row dated D) carries it; the settlement used is the official close when present, else
the last regular bar; each leg at intrinsic, $0.65 a leg at the open and nothing at expiry (a worthless leg pays
nothing; an in-the-money leg settles at intrinsic with no fee assumed — the reports' convention); and the "$0.25
settlement check" = |ohlc/1m 15:59 close − official close| <= 0.25, flagged a session. SPY's whole-day ohlc/1m answer
read there is also kept in the minute-bar cache the volatility model reads (no extra call).

THE MACRO STAMPS (macro_calendar.py): every row carries is_macro_event_day, macro_events (the day's kinds joined by
'+'), minutes_to_macro_release and minutes_since_last_release at its capture minute; a settle or 15:58 row carries its
capture's (the trade's entry minute). All null, one WARN line, when data/macro_events_2022_2027.json is not on disk.

QUOTES: GET /api/stock/{name}/option-contracts?expiry=D (one page of 500 holds a same-day chain — SPY's 302 contracts
on 2026-10-21 — paged until a short page, cap 5), nbbo_bid / nbbo_ask a contract; the strike, right and expiry read
off option_symbol (OCC). SPOT: GET /api/stock/{name}/stock-state. One chain and one state a name a minute.

THE MODEL'S INPUTS (candidate 3, UW alone but VIX): SPY's minute bars of the day (/api/stock/SPY/ohlc/1m?date=D, one
call a capture minute; asked once more after 20 s if the bar closing at the minute is not out yet), the 20 sessions
before from the minute-bar cache <root>/_cache/bars/SPY/<day>.json (filled by the settle pass, by the recorder's own
ohlc_1m files when they are there, else backfilled once with one call a day), the ATM straddle off the capture's chain,
and VIX: UW first (/api/stock/VIX/stock-state — 422 "not available for index ticker VIX" on UW Basic, measured
2026-10-21; asked at most once a session), then the owner's Theta Terminal on 127.0.0.1:25503 (/v3/index/history/price,
the day's VIX minutes; the key stays in the terminal), else none — the no-VIX model's decile stands then.

BUDGET a session (README "The budget"): captures 22 chain/state calls (11 name-minutes: SPY at nine, QQQ at two) + 5
minute-bar calls + 1 VIX probe + 2 at 15:58 + 6 at the settle = 36 with the cache warm; the first day with a cold
cache adds the 20-session backfill (56); a bar asked twice adds up to 5; fly_spxw (on by default) adds 3–5. The default
`--budget` is 90.

STORAGE: append-only Parquet under data_recorder/paper/<candidate>/<name>/<YYYY-MM-DD>.parquet with the recorder's
stamps and dedupe (eod_recorder.Store): a capture row a structure a minute, a close1558 row a fly5 structure a minute,
a settle row a structure a minute a settlement source; a second capture of the same minute is skipped before any call
(its marker), and a row already held is never written twice. Every value is a string, the recorder's convention.

MODES: --log --when HH:MM (one capture, or 15:58's close quotes, for a scheduler), --daemon (sleeps to each capture
minute, to 15:58 and to 16:20, Mon–Fri, the recorder's holidays, half days skipped as the reports skipped them),
--settle [--day D] (the after-close pass, re-runnable: the official close is added once the daily bar carries it),
--backfill (warms the minute-bar cache: at most 20 calls, once), --status, --dry-run (the fixture chain, no network),
--smoke (one live capture under <root>/smoke/, labelled smoke, never a session), --spxw (adds fly_spxw).

The token: UW_API_TOKEN in the environment alone — the recorder's client, limiter and scrubber (never logged).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eod_recorder as R  # noqa: E402  — the client, limiter, scrubber, store, calendar and clock
import macro_calendar as MC  # noqa: E402  — the macro-release stamps
import vol_model as V  # noqa: E402  — the frozen t2 model and its live inputs

VERSION = 'paper-tracker-2026-10-21.2'   # .2: candidate 3 (condor_d20 + the frozen t2 model), 15:58 close quotes, macro stamps, --spxw
RULES_VERSION = 'rules-2026-10-21.1'     # condor_em1 and fly5: the strike and fill rules below; a change here is a new version
C3_RULES_VERSION = 'rules-c3-2026-10-21.1'      # condor_d20: Hypothesis B's 20-delta rule, 2 wide, hold
SPXW_RULES_VERSION = 'rules-spxw-2026-10-21.1'  # fly_spxw: parity-implied SPX, ±5 and ±25
NY, UTC = R.NY, R.UTC
FEE = 0.65                               # a contract, at the open; nothing at expiry; at 15:58 a contract closed
LEGS = 4
MIN_CREDIT = 0.05                        # a vertical's credit (hyp_b MIN_CREDIT)
MIN_RISK = 0.05                          # a fly's max risk (hyp_c MIN_DEBIT)
STRESSES = (0.01, 0.02)                  # a leg worse than the NBBO (hyp_c picks_fillstress)
SETTLE_TIME = '16:20'
CLOSE_TIME = '15:58'                     # the fly5 close quotes
SETTLE_CHECK_TOL = 0.25
CHAIN_PAGE = 500
CHAIN_MAX_PAGES = 5
DEFAULT_BUDGET = 90                      # README "The budget": 36 warm, 56 the cold first day, + up to 5 bars asked twice, + 3–5 for fly_spxw (on by default)
DELTA_TARGET = 0.20
BAR_WAIT_S = 20.0                        # the bar closing at the capture minute not out yet: ask once more after this
PRIOR_SESSIONS = 20                      # hyp_d rel_vol: the 20 sessions before (ATR14 needs 15 of them)
MODEL_NAME = 'SPY'


@dataclass(frozen=True)
class Candidate:
    key: str
    names: tuple
    minutes: tuple
    wing: float
    structures: tuple
    thresholds: tuple                   # settled sessions wanted (per name for fly5, pooled for the others)
    per_name: bool
    note: str
    rules: str = RULES_VERSION
    optional: bool = False              # on only when asked (--spxw)


CANDIDATES: dict[str, Candidate] = {
    'condor_em1': Candidate('condor_em1', ('SPY',), ('11:30', '12:00', '12:30', '13:00', '13:30'), 2.0, ('condor',),
                            (60, 120), False, 'hyp_b: SPY 2-wide iron condor, shorts the first strike outside spot ± the ATM straddle'),
    'fly5': Candidate('fly5', ('SPY', 'QQQ'), ('15:00', '15:30'), 5.0, ('iron', 'call', 'put'), (250,), True,
                      'hyp_c: ±5 iron butterfly and the long call and put ±5 butterflies at the strike nearest spot'),
    'condor_d20': Candidate('condor_d20', ('SPY',), ('13:00', '13:30', '14:00', '14:30', '15:00'), 2.0, ('condor',), (150,), False,
                            'hyp_e: SPY 2-wide 20-delta iron condor, held, with the live t2 decile (D1 → condor, 13:00–15:00)',
                            rules=C3_RULES_VERSION),
    'fly_spxw': Candidate('fly_spxw', ('SPX',), ('15:00', '15:30'), 5.0, ('iron5', 'call5', 'put5', 'iron25', 'call25', 'put25'),
                          (250,), True, 'SPXW ±5 and ±25 iron, call and put flies at the strike nearest parity-implied SPX (cash-settled)',
                          rules=SPXW_RULES_VERSION, optional=True),
}
DEFAULT_KEYS = ('condor_em1', 'fly5', 'condor_d20')


def active_candidates(spxw: bool = True, keys: tuple | None = None) -> tuple:
    ks = keys or (DEFAULT_KEYS + (('fly_spxw',) if spxw else ()))
    return tuple(CANDIDATES[k] for k in ks)


# ---- the Parquet shape (the recorder's Store writes it: STAMPS first, these, any extra) -------------------------------------------

COLUMNS = (
    'row_kind', 'candidate', 'structure', 'minute', 'rules_version', 'tracker_version',
    # a capture
    'captured_at', 'spot', 'spot_tape_time', 'spot_market_time', 'prev_close', 'chain_rows', 'chain_pages', 'chain_expiry',
    'k0', 'straddle', 'k0_call_bid', 'k0_call_ask', 'k0_put_bid', 'k0_put_ask', 'wing',
    'l1_symbol', 'l1_side', 'l1_qty', 'l1_bid', 'l1_ask', 'l1_bid_size', 'l1_ask_size',
    'l2_symbol', 'l2_side', 'l2_qty', 'l2_bid', 'l2_ask', 'l2_bid_size', 'l2_ask_size',
    'l3_symbol', 'l3_side', 'l3_qty', 'l3_bid', 'l3_ask', 'l3_bid_size', 'l3_ask_size',
    'l4_symbol', 'l4_side', 'l4_qty', 'l4_bid', 'l4_ask', 'l4_bid_size', 'l4_ask_size',
    'package', 'price_nbbo', 'price_mid', 'price_1c', 'price_2c', 'max_risk', 'tradable', 'reason',
    # a settlement
    'settle_source', 'settle_px', 'close_1m_r', 'close_1m_r_bar', 'close_1m_1600', 'close_state', 'state_market_time',
    'prev_close_state', 'close_official', 'close_official_from', 'check_025', 'settled_at',
    'l1_settle', 'l2_settle', 'l3_settle', 'l4_settle', 'payoff', 'pnl_nbbo', 'pnl_mid', 'pnl_1c', 'pnl_2c',
) + MC.FIELDS
CLOSE_COLUMNS = (
    'close_at', 'close_chain_rows',
    'l1_bid_1558', 'l1_ask_1558', 'l2_bid_1558', 'l2_ask_1558', 'l3_bid_1558', 'l3_ask_1558', 'l4_bid_1558', 'l4_ask_1558',
    'liq_nbbo', 'liq_mid', 'legs_closed', 'fees_close', 'pnl_1558_nbbo', 'pnl_1558_mid', 'close_reason',
)
C3_FEATURES = tuple(f'f_{f}' for f in ('m', 'ret1', 'ret5', 'ret15', 'ret30', 'aret1', 'aret5', 'aret15', 'aret30', 'rng1', 'rng5',
                                        'rng15', 'rng30', 'range_pos', 'or_pos', 'day_move_atr', 'day_range_atr', 'rv_session', 'vix',
                                        'vix_chg_open', 'vix_chg30', 'vix_chg_prev', 'straddle_rel', 'implied30', 'rel_vol'))
C3_COLUMNS = (
    'delta_target', 'short_call_k', 'short_put_k', 'short_call_delta', 'short_put_delta',
    't2_score_full', 't2_decile_full', 't2_score_novix', 't2_decile_novix', 't2_decile_primary', 't2_primary_model',
    't2_model_full_sha', 't2_model_novix_sha', 'vix_source', 'vix_note', 'model_spot', 'model_atm_k', 'model_straddle',
    't2_bar_last', 't2_bar_complete', 't2_bar_asks', 't2_prior_sessions', 't2_atr_sessions', 't2_relvol_sessions', 't2_note',
) + C3_FEATURES
SPXW_COLUMNS = ('spot_source', 'parity_strikes')
C3_CARRY = ('delta_target', 'short_call_k', 'short_put_k', 'short_call_delta', 'short_put_delta', 't2_score_full', 't2_decile_full',
            't2_score_novix', 't2_decile_novix', 't2_decile_primary', 't2_primary_model', 'vix_source')
DEDUPE = ('row_kind', 'minute', 'structure', 'settle_source')


def columns_for(cand: Candidate) -> tuple:
    extra = {'fly5': CLOSE_COLUMNS, 'condor_d20': C3_COLUMNS, 'fly_spxw': SPXW_COLUMNS}.get(cand.key, ())
    return COLUMNS + extra


def endpoint_for(cand: Candidate) -> R.Endpoint:
    """The recorder's Endpoint shape names the folder (<root>/<candidate>/<NAME>/<day>.parquet) and the dedupe."""
    return R.Endpoint(cand.key, 'eod', '', DEDUPE, columns_for(cand), note=cand.note)


# ---- the chain ----------------------------------------------------------------------------------------------------------------------

def parse_symbol(sym: str) -> tuple[str, str, str, float] | None:
    """An OCC option_symbol → (root, expiry YYYY-MM-DD, 'C'|'P', strike); None when it is not one"""
    if not isinstance(sym, str) or len(sym) < 16:
        return None
    body = sym[-15:]
    root = sym[:-15]
    ymd, right, k = body[:6], body[6], body[7:]
    if right not in 'CP' or not ymd.isdigit() or not k.isdigit() or not root:
        return None
    return root, f'20{ymd[:2]}-{ymd[2:4]}-{ymd[4:]}', right, int(k) / 1000.0


def fnum(v) -> float | None:
    if v is None or v == '':
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


@dataclass
class Quote:
    symbol: str
    bid: float
    ask: float
    bid_size: object = None
    ask_size: object = None

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


class Chain:
    """A same-day chain at one minute: the quoted strikes a right. A quote stands when both sides are there, ask >= bid
    and bid >= 0 (hyp_b `two`, hyp_c `slice_minute`). `root`: keep one OCC root (SPX's chain carries SPX and SPXW)."""

    def __init__(self, rows: list, expiry: str, root: str | None = None):
        self.expiry = expiry
        self.calls: dict[float, Quote] = {}
        self.puts: dict[float, Quote] = {}
        self.listed: set = set()
        self.rows = 0
        for r in rows:
            p = parse_symbol(r.get('option_symbol'))
            if not p or p[1] != expiry or (root is not None and p[0] != root):
                continue
            self.rows += 1
            self.listed.add(p[3])
            b, a = fnum(r.get('nbbo_bid')), fnum(r.get('nbbo_ask'))
            if b is None or a is None or a < b or b < 0:
                continue
            q = Quote(r['option_symbol'], b, a, r.get('nbbo_bid_size'), r.get('nbbo_ask_size'))
            (self.calls if p[2] == 'C' else self.puts)[p[3]] = q
        self.strikes = sorted(set(self.calls) | set(self.puts))

    def both_quoted(self) -> list[float]:
        """Strikes with a call and a put quoted, both asks > 0 (hyp_b straddle_at; hyp_c `both` with the bids > 0 checked
        by the structure)"""
        return [k for k in self.strikes if k in self.calls and k in self.puts and self.calls[k].ask > 0 and self.puts[k].ask > 0]

    def nearest(self, spot: float) -> float | None:
        """The strike nearest spot among both_quoted(); a tie goes to the lower strike (np.lexsort / np.argmin)"""
        ks = self.both_quoted()
        if not ks:
            return None
        return min(ks, key=lambda k: (abs(k - spot), k))

    def straddle(self, spot: float) -> tuple[float, float] | None:
        k = self.nearest(spot)
        if k is None:
            return None
        return k, self.calls[k].mid + self.puts[k].mid

    def first_beyond(self, level: float, side: str) -> float | None:
        """The first listed strike >= level ('call') or <= level ('put') — hyp_b first_beyond, its 1e-9 tolerance"""
        if side == 'call':
            for k in self.strikes:
                if k >= level - 1e-9:
                    return k
            return None
        for k in reversed(self.strikes):
            if k <= level + 1e-9:
                return k
        return None

    def quote(self, right: str, k: float) -> Quote | None:
        return (self.calls if right == 'C' else self.puts).get(k)

    def model_quotes(self) -> dict:
        """{strike: ((bid, ask) | None, (bid, ask) | None)} for vol_model.atm_straddle — every listed strike"""
        def q(x):
            return (x.bid, x.ask) if x is not None else None
        return {k: (q(self.calls.get(k)), q(self.puts.get(k))) for k in sorted(self.listed | set(self.strikes))}

    def parity_spot(self, n: int = 3) -> tuple[float | None, str]:
        """The underlying by put-call parity at r = q = 0 (same day): the median of K + call mid − put mid over the `n`
        strikes, both sides quoted with bids > 0, where |call mid − put mid| is smallest. (spot, the strikes used)"""
        ks = [k for k in self.both_quoted() if self.calls[k].bid > 0 and self.puts[k].bid > 0]
        if not ks:
            return None, ''
        ks = sorted(ks, key=lambda k: (abs(self.calls[k].mid - self.puts[k].mid), k))[:n]
        fs = sorted(k + self.calls[k].mid - self.puts[k].mid for k in ks)
        mid = len(fs) // 2
        spot = fs[mid] if len(fs) % 2 else 0.5 * (fs[mid - 1] + fs[mid])
        return spot, ' '.join(f'{k:g}' for k in sorted(ks))


# ---- Hypothesis B's delta rule (engine.py bsm_total_var / deltas / nearest_delta) ------------------------------------------------

def _ncdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bsm_abs_delta(S: float, K: float, price: float, is_call: bool) -> float:
    """hyp_b bsm_total_var: v = σ√τ from a European price, r = q = 0, by 60 bisections on [1e-5, 5] (a put through
    parity, C = P + S − K); → |delta| (a call N(d1), a put 1 − N(d1))"""
    lo, hi = 1e-5, 5.0
    lnm = math.log(S / K)
    target = price if is_call else price + S - K
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        d1 = (lnm + 0.5 * mid * mid) / mid
        d2 = d1 - mid
        if S * _ncdf(d1) - K * _ncdf(d2) > target:
            hi = mid
        else:
            lo = mid
    v = 0.5 * (lo + hi)
    d1 = (lnm + 0.5 * v * v) / v
    return _ncdf(d1) if is_call else 1.0 - _ncdf(d1)


def otm_deltas(chain: Chain, S: float, side: str) -> dict:
    """hyp_b Session.deltas: |delta| by strike for the OTM calls (K > S) or puts (K < S) whose mid is > 0 with the ask
    > 0, a call's mid < S and a put's mid < K (no time value otherwise), from each option's own mid"""
    out = {}
    book = chain.calls if side == 'call' else chain.puts
    for k, q in book.items():
        mid = (q.bid + q.ask) / 2
        if side == 'call' and not (k > S and mid > 0 and q.ask > 0 and mid < S):
            continue
        if side == 'put' and not (k < S and mid > 0 and q.ask > 0 and mid < k):
            continue
        out[k] = bsm_abs_delta(S, k, mid, side == 'call')
    return out


def nearest_delta(chain: Chain, S: float, side: str, target: float = DELTA_TARGET) -> tuple[float | None, float | None]:
    """hyp_b nearest_delta: the OTM strike whose |delta| is nearest `target`; a tie goes as np.lexsort((-ks | ks, gap))
    puts it — the larger strike for a call, the smaller for a put (the farther out of the money). → (K, |delta|)"""
    dl = otm_deltas(chain, S, side)
    if not dl:
        return None, None
    k = min(dl, key=lambda k: (abs(dl[k] - target), -k if side == 'call' else k))
    return k, dl[k]


# ---- the structures -------------------------------------------------------------------------------------------------------------------

@dataclass
class Leg:
    symbol: str
    right: str
    strike: float
    side: str            # 'short' | 'long'
    qty: int
    bid: float
    ask: float
    bid_size: object = None
    ask_size: object = None

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2

    def fill(self, worse: float = 0.0) -> float:
        """The NBBO fill a leg: a short at its bid, a long at its ask; `worse` moves it against us"""
        return (self.bid - worse) if self.side == 'short' else (self.ask + worse)

    def signed(self, price: float) -> float:
        """Cash in (+) or out (−) for one unit of this leg at `price`"""
        return (price if self.side == 'short' else -price) * self.qty


@dataclass
class Structure:
    structure: str
    package: str              # 'credit' | 'debit'
    legs: list
    k0: float | None
    straddle: float | None
    wing: float
    tradable: bool
    reason: str = ''
    extra: dict = field(default_factory=dict)

    def price(self, worse: float = 0.0, mid: bool = False) -> float | None:
        """The package price, positive: a credit received or a debit paid"""
        if not self.legs:
            return None
        cash = sum(l.signed(l.mid if mid else l.fill(worse)) for l in self.legs)
        return cash if self.package == 'credit' else -cash

    def entry_cash(self, mid: bool = False) -> float | None:
        """Cash at the open, a unit: + a credit, − a debit"""
        p = self.price(mid=mid)
        return None if p is None else (p if self.package == 'credit' else -p)

    def max_risk(self) -> float | None:
        p = self.price()
        if p is None:
            return None
        return (self.wing - p) if self.package == 'credit' else p

    def payoff(self, settle: float) -> float:
        """At expiry, a point: + what the longs pay, − what the shorts cost (intrinsic)"""
        return sum(l.signed(-intrinsic(settle, l.strike, l.right)) for l in self.legs)

    def pnl(self, settle: float, worse: float = 0.0, mid: bool = False) -> float:
        """Dollars a structure: (credit + payoff) or (payoff − debit), × 100, less the opening fees"""
        p = self.price(worse, mid)
        pay = self.payoff(settle)
        core = (p + pay) if self.package == 'credit' else (pay - p)
        return core * 100 - LEGS * FEE


def intrinsic(settle: float, k: float, right: str) -> float:
    return max(settle - k, 0.0) if right == 'C' else max(k - settle, 0.0)


def _leg(q: Quote, right: str, k: float, side: str, qty: int = 1) -> Leg:
    return Leg(q.symbol, right, k, side, qty, q.bid, q.ask, q.bid_size, q.ask_size)


def _condor(chain: Chain, ksc: float | None, ksp: float | None, wing: float, k0, m, extra: dict, none_why: str) -> Structure:
    """A 2-wide iron condor on the short strikes given: longs `wing` beyond; each spread's credit (short bid − long ask)
    >= MIN_CREDIT, the short's bid > 0 and the long's ask > 0 (hyp_b leg_paths / vertical)"""
    legs, why = [], []
    for right, ks, kl in (('C', ksc, None if ksc is None else ksc + wing), ('P', ksp, None if ksp is None else ksp - wing)):
        side = 'call' if right == 'C' else 'put'
        if ks is None:
            why.append(f'no {side} strike {none_why}')
            continue
        qs, ql = chain.quote(right, ks), (chain.quote(right, kl) if kl is not None else None)
        if qs is None or qs.bid <= 0:
            why.append(f'short {side} {ks:g} not quoted (bid > 0)')
        if ql is None or ql.ask <= 0:
            why.append(f'long {side} {kl:g} not quoted (ask > 0)')
        if qs is not None and ql is not None:
            legs += [_leg(qs, right, ks, 'short'), _leg(ql, right, kl, 'long')]
            if qs.bid > 0 and ql.ask > 0 and qs.bid - ql.ask < MIN_CREDIT - 1e-9:
                why.append(f'{side} spread credit {qs.bid - ql.ask:.2f} under {MIN_CREDIT}')
    ok = len(legs) == 4 and not why
    return Structure('condor', 'credit', legs if len(legs) == 4 else [], k0, m, wing, ok, '; '.join(why), extra)


def condor_em1(chain: Chain, spot: float, wing: float = 2.0) -> Structure:
    """hyp_b `em1`: shorts the first strike outside spot ± the ATM straddle, longs `wing` beyond"""
    st = chain.straddle(spot)
    if st is None:
        return Structure('condor', 'credit', [], None, None, wing, False, 'no strike with both sides quoted')
    k0, m = st
    ksc, ksp = chain.first_beyond(spot + m, 'call'), chain.first_beyond(spot - m, 'put')
    return _condor(chain, ksc, ksp, wing, k0, m, {'short_call': ksc, 'short_put': ksp}, 'beyond the band')


def condor_d20(chain: Chain, spot: float, wing: float = 2.0, target: float = DELTA_TARGET) -> Structure:
    """Candidate 3 (hyp_e's forward test): the shorts at hyp_b's `d20` strikes (nearest_delta), longs `wing` beyond.
    k0 and the straddle columns are the ATM straddle as condor_em1 reads it (for the record; not used by the rule)."""
    st = chain.straddle(spot)
    k0, m = st if st is not None else (None, None)
    kc, dc = nearest_delta(chain, spot, 'call', target)
    kp, dp = nearest_delta(chain, spot, 'put', target)
    extra = {'delta_target': target, 'short_call_k': kc, 'short_put_k': kp, 'short_call_delta': dc, 'short_put_delta': dp}
    return _condor(chain, kc, kp, wing, k0, m, extra, 'with a delta (no OTM quote with time value)')


def flies5(chain: Chain, spot: float, wing: float = 5.0, suffix: str = '') -> list[Structure]:
    """hyp_c build_flies: K0 the strike nearest spot with both sides quoted; iron (sell the K0 straddle at the bid, buy
    the K0−W put and K0+W call at the ask; risk W − credit), long call fly and long put fly (buy the wings at the ask,
    sell two K0 at the bid; risk = the debit); the short legs' bids > 0; max risk >= MIN_RISK. `suffix` names the
    structures of another width ('iron25')."""
    k0 = chain.nearest(spot)
    out = []
    if k0 is None:
        return [Structure(s + suffix, 'credit' if s == 'iron' else 'debit', [], None, None, wing, False, 'no strike with both sides quoted')
                for s in ('iron', 'call', 'put')]
    strad = chain.calls[k0].mid + chain.puts[k0].mid
    lo, hi = k0 - wing, k0 + wing
    c0, p0, clo, chi, plo, phi = (chain.quote('C', k0), chain.quote('P', k0), chain.quote('C', lo), chain.quote('C', hi),
                                  chain.quote('P', lo), chain.quote('P', hi))
    # the iron fly
    why = []
    if plo is None:
        why.append(f'put {lo:g} not quoted')
    if chi is None:
        why.append(f'call {hi:g} not quoted')
    if c0.bid <= 0 or p0.bid <= 0:
        why.append(f'a K0 bid is 0')
    legs = [_leg(c0, 'C', k0, 'short'), _leg(p0, 'P', k0, 'short')] + ([_leg(plo, 'P', lo, 'long')] if plo else []) + ([_leg(chi, 'C', hi, 'long')] if chi else [])
    s = Structure('iron' + suffix, 'credit', legs if len(legs) == 4 else [], k0, strad, wing, not why, '; '.join(why))
    if s.tradable and (s.max_risk() is None or s.max_risk() < MIN_RISK - 1e-9):
        s.tradable, s.reason = False, f'max risk {s.max_risk():.2f} under {MIN_RISK}'
    out.append(s)
    # the long call and put flies
    for name, right, qlo, q0, qhi in (('call', 'C', clo, c0, chi), ('put', 'P', plo, p0, phi)):
        why = []
        if qlo is None:
            why.append(f'{name} {lo:g} not quoted')
        if qhi is None:
            why.append(f'{name} {hi:g} not quoted')
        if q0.bid <= 0:
            why.append(f'{name} K0 bid is 0')
        legs = ([_leg(qlo, right, lo, 'long')] if qlo else []) + [_leg(q0, right, k0, 'short', 2)] + ([_leg(qhi, right, hi, 'long')] if qhi else [])
        s = Structure(name + suffix, 'debit', legs if len(legs) == 3 else [], k0, strad, wing, not why, '; '.join(why))
        if s.tradable and (s.max_risk() is None or s.max_risk() < MIN_RISK - 1e-9):
            s.tradable, s.reason = False, f'max risk {s.max_risk():.2f} under {MIN_RISK}'
        out.append(s)
    return out


def build(cand: Candidate, chain: Chain, spot: float) -> list[Structure]:
    if cand.key == 'condor_em1':
        return [condor_em1(chain, spot, cand.wing)]
    if cand.key == 'condor_d20':
        return [condor_d20(chain, spot, cand.wing)]
    if cand.key == 'fly_spxw':
        return flies5(chain, spot, 5.0, '5') + flies5(chain, spot, 25.0, '25')
    return flies5(chain, spot, cand.wing)


# ---- rows -------------------------------------------------------------------------------------------------------------------------

def fmt(x) -> str | None:
    if x is None:
        return None
    if isinstance(x, bool):
        return 'true' if x else 'false'
    if isinstance(x, float):
        return f'{x:.4f}'.rstrip('0').rstrip('.') if math.isfinite(x) else None
    return str(x)


def fmt6(x) -> str | None:
    """A model figure: six significant places (scores and features need more than the prices' four decimals)"""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return None
    return f'{float(x):.6g}'


def leg_columns(s: Structure) -> dict:
    """The legs in a fixed order: the condor short call, long call, short put, long put; a fly its legs lo, K0, hi
    (the K0 leg with qty 2 — the call and put flies have three legs; the iron four: short call, short put, long put,
    long call)"""
    out = {}
    legs = list(s.legs)
    for i in range(4):
        l = legs[i] if i < len(legs) else None
        out.update({f'l{i + 1}_symbol': l.symbol if l else None, f'l{i + 1}_side': l.side if l else None,
                    f'l{i + 1}_qty': l.qty if l else None, f'l{i + 1}_bid': fmt(l.bid) if l else None,
                    f'l{i + 1}_ask': fmt(l.ask) if l else None, f'l{i + 1}_bid_size': fmt(l.bid_size) if l else None,
                    f'l{i + 1}_ask_size': fmt(l.ask_size) if l else None})
    return out


def capture_row(cand: Candidate, s: Structure, minute: str, now: dt.datetime, spot: float, state: dict, chain: Chain,
                pages: int, macro: dict | None = None, extra: dict | None = None) -> dict:
    has = bool(s.legs)
    r = {'row_kind': 'capture', 'candidate': cand.key, 'structure': s.structure, 'minute': minute,
         'rules_version': cand.rules, 'tracker_version': VERSION, 'captured_at': R.iso_z(now), 'spot': fmt(spot),
         'spot_tape_time': state.get('tape_time'), 'spot_market_time': state.get('market_time'),
         'prev_close': fmt(fnum(state.get('prev_close'))), 'chain_rows': chain.rows, 'chain_pages': pages,
         'chain_expiry': chain.expiry, 'k0': fmt(s.k0), 'straddle': fmt(s.straddle), 'wing': fmt(s.wing),
         'k0_call_bid': fmt(chain.calls[s.k0].bid) if s.k0 in chain.calls else None,
         'k0_call_ask': fmt(chain.calls[s.k0].ask) if s.k0 in chain.calls else None,
         'k0_put_bid': fmt(chain.puts[s.k0].bid) if s.k0 in chain.puts else None,
         'k0_put_ask': fmt(chain.puts[s.k0].ask) if s.k0 in chain.puts else None,
         'package': s.package, 'price_nbbo': fmt(s.price()) if has else None, 'price_mid': fmt(s.price(mid=True)) if has else None,
         'price_1c': fmt(s.price(STRESSES[0])) if has else None, 'price_2c': fmt(s.price(STRESSES[1])) if has else None,
         'max_risk': fmt(s.max_risk()) if has else None, 'tradable': fmt(s.tradable), 'reason': s.reason or None,
         'settle_source': None}
    r.update(leg_columns(s))
    r.update(macro or {k: None for k in MC.FIELDS})
    if cand.key == 'condor_d20':
        x = s.extra
        r.update({'delta_target': fmt(x.get('delta_target')), 'short_call_k': fmt(x.get('short_call_k')), 'short_put_k': fmt(x.get('short_put_k')),
                  'short_call_delta': fmt6(x.get('short_call_delta')), 'short_put_delta': fmt6(x.get('short_put_delta'))})
    r.update(extra or {})
    return r


def structure_from_row(row: dict) -> Structure | None:
    """A capture row read back → the Structure it logged (the P&L is figured from the row, never from memory)"""
    legs = []
    for i in range(1, 5):
        sym = row.get(f'l{i}_symbol')
        if not sym:
            continue
        p = parse_symbol(sym)
        if not p:
            return None
        legs.append(Leg(sym, p[2], p[3], row[f'l{i}_side'], int(row[f'l{i}_qty']), float(row[f'l{i}_bid']), float(row[f'l{i}_ask'])))
    if not legs:
        return None
    return Structure(row['structure'], row['package'], legs, fnum(row.get('k0')), fnum(row.get('straddle')),
                     float(row['wing']), row.get('tradable') == 'true', row.get('reason') or '')


def settle_row(cap: dict, s: Structure, source: str, px: float, closes: dict, now: dt.datetime, close: dict | None = None) -> dict:
    """The settle row for one capture row at one settlement source (and the 15:58 exit beside it, when it was read)"""
    r = {k: cap.get(k) for k in ('candidate', 'structure', 'minute', 'rules_version', 'tracker_version', 'wing', 'package',
                                 'k0', 'straddle', 'spot', 'price_nbbo', 'price_mid', 'price_1c', 'price_2c', 'max_risk',
                                 'tradable', 'reason') + MC.FIELDS + C3_CARRY + SPXW_COLUMNS}
    r.update({'row_kind': 'settle', 'settle_source': source, 'settle_px': fmt(px), 'settled_at': R.iso_z(now)})
    for k in ('close_1m_r', 'close_1m_r_bar', 'close_1m_1600', 'close_state', 'state_market_time', 'prev_close_state', 'close_official'):
        r[k] = fmt(closes.get(k))
    r['close_official_from'] = closes.get('close_official_from') or ('daily bar' if closes.get('close_official') is not None else None)
    a, b = closes.get('close_1m_r'), closes.get('close_official')
    r['check_025'] = fmt(abs(a - b) <= SETTLE_CHECK_TOL) if a is not None and b is not None else None
    for i, l in enumerate(s.legs):
        r[f'l{i + 1}_symbol'] = l.symbol
        r[f'l{i + 1}_settle'] = fmt(intrinsic(px, l.strike, l.right))
    r.update({'payoff': fmt(s.payoff(px)), 'pnl_nbbo': fmt(s.pnl(px)), 'pnl_mid': fmt(s.pnl(px, mid=True)),
              'pnl_1c': fmt(s.pnl(px, STRESSES[0])), 'pnl_2c': fmt(s.pnl(px, STRESSES[1]))})
    if close:
        for k in ('close_at', 'liq_nbbo', 'liq_mid', 'legs_closed', 'fees_close', 'pnl_1558_nbbo', 'pnl_1558_mid', 'close_reason'):
            r[k] = close.get(k)
    return {k: v for k, v in r.items() if v is not None or k in COLUMNS}


def liquidation(s: Structure, chain: Chain) -> dict:
    """The package closed at 15:58 off `chain`: each leg's NBBO; sell a long at its bid, buy back a short at its ask
    (`liq_nbbo`, cash a unit: + received), and at the mid (`liq_mid`); $0.65 a contract closed. A long leg with no bid
    (bid 0) cannot be sold — it is left to expire (0 in both values, no fee). A leg missing from the chain → no value."""
    out = {'legs': [], 'liq_nbbo': None, 'liq_mid': None, 'legs_closed': 0, 'fees_close': None, 'reason': ''}
    nbbo = mid = 0.0
    closed = 0
    missing = []
    for l in s.legs:
        q = chain.quote(l.right, l.strike)
        out['legs'].append(q)
        if q is None:
            missing.append(f'{l.side} {l.right}{l.strike:g} not quoted at {CLOSE_TIME}')
            continue
        if l.side == 'long':
            if q.bid <= 0:
                continue                                   # abandoned: worthless at the bid, no fee
            nbbo += l.qty * q.bid
            mid += l.qty * q.mid
        else:
            nbbo -= l.qty * q.ask
            mid -= l.qty * q.mid
        closed += l.qty
    if missing:
        out['reason'] = '; '.join(missing)
        return out
    out.update({'liq_nbbo': nbbo, 'liq_mid': mid, 'legs_closed': closed, 'fees_close': closed * FEE})
    return out


def close_row(cap: dict, s: Structure, chain: Chain, now: dt.datetime) -> dict:
    """A fly5 structure read again at 15:58: the legs' NBBO, the liquidation value, the 15:58 exit P&L — (entry cash +
    liquidation cash) × 100 − $2.60 to open − $0.65 a contract closed; at the NBBO both ways, and at the mid both ways"""
    liq = liquidation(s, chain)
    r = {k: cap.get(k) for k in ('candidate', 'structure', 'minute', 'rules_version', 'wing', 'package', 'k0', 'spot',
                                 'price_nbbo', 'price_mid', 'max_risk', 'tradable', 'reason') + MC.FIELDS}
    r.update({'row_kind': 'close1558', 'tracker_version': VERSION, 'settle_source': None, 'close_at': R.iso_z(now),
              'close_chain_rows': chain.rows, 'liq_nbbo': None, 'liq_mid': None, 'legs_closed': None, 'fees_close': None,
              'pnl_1558_nbbo': None, 'pnl_1558_mid': None})
    for i, (l, q) in enumerate(zip(s.legs, liq['legs'])):
        r.update({f'l{i + 1}_symbol': l.symbol, f'l{i + 1}_side': l.side, f'l{i + 1}_qty': l.qty,
                  f'l{i + 1}_bid_1558': fmt(q.bid) if q else None, f'l{i + 1}_ask_1558': fmt(q.ask) if q else None})
    if liq['liq_nbbo'] is not None:
        e_n, e_m = s.entry_cash(), s.entry_cash(mid=True)
        r.update({'liq_nbbo': fmt(liq['liq_nbbo']), 'liq_mid': fmt(liq['liq_mid']), 'legs_closed': liq['legs_closed'],
                  'fees_close': fmt(liq['fees_close']),
                  'pnl_1558_nbbo': fmt((e_n + liq['liq_nbbo']) * 100 - LEGS * FEE - liq['fees_close']),
                  'pnl_1558_mid': fmt((e_m + liq['liq_mid']) * 100 - LEGS * FEE - liq['fees_close'])})
    r['close_reason'] = liq['reason'] or None
    return r


# ---- the vendor calls -------------------------------------------------------------------------------------------------------------------

def fetch_chain(client, name: str, day: str) -> tuple[list, int, str | None]:
    """The same-day chain: /option-contracts?expiry=D, 500 a page, until a page is short. (rows, pages, error)"""
    rows, pages = [], 0
    for page in range(CHAIN_MAX_PAGES):
        ans = client.get(f'/api/stock/{name}/option-contracts', {'expiry': day, 'limit': CHAIN_PAGE, 'page': page})
        if not ans.ok:
            return rows, pages, ans.error
        pages += 1
        rows.extend(ans.rows)
        if len(ans.rows) < CHAIN_PAGE:
            return rows, pages, None
    return rows, pages, f'page cap {CHAIN_MAX_PAGES} reached'


def fetch_state(client, name: str) -> tuple[dict | None, str | None]:
    ans = client.get(f'/api/stock/{name}/stock-state')
    if not ans.ok:
        return None, ans.error
    body = ans.body.get('data') if isinstance(ans.body, dict) else None
    return (body if isinstance(body, dict) else None), (None if isinstance(body, dict) else 'stock-state carried no data')


def fetch_closes(client, name: str, day: str, with_official: bool = True, keep: dict | None = None) -> tuple[dict, list]:
    """The settlement figures a name: the ohlc/1m last regular bar and the 16:00 bar, the stock-state close and its
    prev_close, the daily bar's official close (when it is there). (closes, errors). `keep['rows']` gets the ohlc/1m
    answer (the minute-bar cache keeps SPY's day)."""
    closes: dict = {}
    errors = []
    ans = client.get(f'/api/stock/{name}/ohlc/1m', {'date': day, 'limit': 1000})
    if ans.ok:
        if keep is not None:
            keep['rows'] = ans.rows
        reg = [r for r in ans.rows if r.get('market_time') == 'r' and fnum(r.get('close')) is not None]
        reg.sort(key=lambda r: str(r.get('start_time')))
        if reg:
            closes['close_1m_r'] = fnum(reg[-1]['close'])
            closes['close_1m_r_bar'] = reg[-1].get('start_time')
        at16 = R.iso_z(R.ny_at(day, '16:00'))
        for r in ans.rows:
            t = R.parse_ts(r.get('start_time'))
            if t is not None and R.iso_z(t) == at16 and fnum(r.get('close')) is not None:
                closes['close_1m_1600'] = fnum(r['close'])
        if not reg:
            errors.append('ohlc/1m: no regular bar')
    else:
        errors.append(f'ohlc/1m: {ans.error}')
    state, err = fetch_state(client, name)
    if state:
        closes['close_state'] = fnum(state.get('close'))
        closes['state_market_time'] = state.get('market_time')
        closes['prev_close_state'] = fnum(state.get('prev_close'))
    else:
        errors.append(f'stock-state: {err}')
    if with_official:
        ans = client.get(f'/api/stock/{name}/ohlc/1d', {'date': day, 'limit': 6})
        if ans.ok:
            for r in ans.rows:
                if str(r.get('date')) == day and r.get('market_time') == 'r' and fnum(r.get('close')) is not None:
                    closes['close_official'] = fnum(r['close'])
        else:
            errors.append(f'ohlc/1d: {ans.error}')
    return closes, errors


def fetch_spx_price(client) -> tuple[float | None, str | None, str | None]:
    """SPX's price as UW figures it: `price` (and `time`) on /api/stock/SPX/spot-exposures/strike, page 0 — UW Basic
    has no index price route (stock-state 422). (price, its time, error)"""
    ans = client.get('/api/stock/SPX/spot-exposures/strike', {'limit': CHAIN_PAGE, 'page': 0})
    if not ans.ok:
        return None, None, ans.error
    for r in ans.rows:
        px = fnum(r.get('price'))
        if px is not None:
            return px, r.get('time'), None
    return None, None, 'spot-exposures carried no price'


# ---- the minute-bar cache (the model's sessions before) ------------------------------------------------------------------------------

class BarCache:
    """SPY's regular-session minute bars a session, as vol_model reads them: <root>/_cache/bars/<NAME>/<day>.json.
    A day is kept only whole (a day before today, or today after 16:00 New York) and is never asked again. Filled by the
    settle pass (its ohlc/1m answer), by the recorder's own ohlc_1m Parquet when there (no call), else one GET a day."""

    def __init__(self, root: Path, recorder_root: Path | None = None):
        self.dir = Path(root) / '_cache' / 'bars'
        self.recorder_root = Path(recorder_root) if recorder_root else None

    def file(self, name: str, day: str) -> Path:
        return self.dir / name / f'{day}.json'

    def get(self, name: str, day: str) -> dict | None:
        f = self.file(name, day)
        if not f.exists():
            return None
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
            bars = {k: [V.NAN if x is None else float(x) for x in d[k]] for k in 'ohlcv'}
            bars['n'], bars['last_m'] = d['n'], d['last_m']
            return bars
        except Exception:
            return None

    def put(self, name: str, day: str, bars: dict, source: str) -> None:
        f = self.file(name, day)
        f.parent.mkdir(parents=True, exist_ok=True)
        d = {'day': day, 'name': name, 'source': source, 'n': bars['n'], 'last_m': bars['last_m'],
             'kept_at': R.iso_z(dt.datetime.now(UTC))}
        d.update({k: [None if V.isnan(x) else x for x in bars[k]] for k in 'ohlcv'})
        tmp = f.with_name(f.name + '.tmp')
        tmp.write_text(json.dumps(d, separators=(',', ':')), encoding='utf-8')
        os.replace(tmp, f)

    def from_recorder(self, name: str, day: str) -> dict | None:
        """The recorder's ohlc_1m/<NAME>/<day>.parquet (its 16:15 EOD pass: the whole day) → bars, no call"""
        if self.recorder_root is None:
            return None
        f = self.recorder_root / 'ohlc_1m' / name / f'{day}.parquet'
        if not f.exists():
            return None
        try:
            rows = pl.read_parquet(f).select('start_time', 'open', 'high', 'low', 'close', 'volume', 'market_time').to_dicts()
        except Exception:
            return None
        bars = V.bars_from_uw(rows, day)
        return bars if bars['n'] >= 30 else None


def previous_sessions(day: str, n: int = PRIOR_SESSIONS) -> list[str]:
    """The `n` trading days before `day` (the recorder's calendar: weekdays less the holidays; half days count — the
    audit's day table holds them), oldest first"""
    out = []
    d = dt.date.fromisoformat(day)
    while len(out) < n:
        d -= dt.timedelta(days=1)
        if R.is_trading_day(d.isoformat()):
            out.insert(0, d.isoformat())
    return out


# ---- the fake client (the dry run and the tests: no network) -----------------------------------------------------------------------

DEFAULT_CHAIN_FIXTURE = R.REPO / 'tests' / 'fixtures' / 'paper_chain_SPY.json'
SPXW_SCALE = 5.0                          # the fake SPXW chain: the SPY fixture's strikes and prices × 5


def fake_bar(day: str, m: int, base: float) -> tuple:
    """A made-up regular bar closing at minute m: (open, high, low, close, volume) — deterministic by day"""
    s = sum(ord(c) for c in day) % 17
    c = base + 0.9 * math.sin((m + s) / 23.0) + 0.3 * math.sin(m / 5.0)
    o = base + 0.9 * math.sin((m - 1 + s) / 23.0) + 0.3 * math.sin((m - 1) / 5.0)
    return o, max(o, c) + 0.05, min(o, c) - 0.05, c, 150_000 + (m * 7919 + s * 101) % 90_000


class FakePaperClient:
    """Serves the fixture chain (its option_symbols re-dated to the day asked, its root to the name asked; SPX's as an
    SPXW chain at five times the strikes and prices), a stock-state at `spot` (VIX and SPX answer 422 as UW Basic does,
    unless `vix_uw` is a number), an ohlc/1m day of made-up regular bars whose 15:59 bar closes at `close_r` and 16:00
    bar at `close_1600` (`bars_until` HH:MM cuts the regular bars as a live answer before the close), a daily bar whose
    `r` row closes at `close_official` (None: not caught up — left out), and SPX's book at `spx_price`. The same limiter
    as the real client; `fail_plan` stages a status per path prefix."""

    def __init__(self, limiter, log, clock, scrub, fixture: Path = DEFAULT_CHAIN_FIXTURE, spot: float = 773.40,
                 prev_close: float = 770.72, close_r: float = 777.13, close_1600: float = 777.39,
                 close_official: float | None = 777.20, close_state: float | None = None, fail_plan: dict | None = None,
                 vix_uw: float | None = None, bars_until: str | None = None, spx_price: float | None = 3887.0,
                 chain_override: dict | None = None):
        self.limiter, self.log, self.clock, self.scrub = limiter, log, clock, scrub
        self.fixture = json.loads(Path(fixture).read_text(encoding='utf-8'))
        self.spot, self.prev_close, self.close_r, self.close_1600 = spot, prev_close, close_r, close_1600
        self.close_official, self.close_state = close_official, close_state
        self.fail_plan = dict(fail_plan or {})
        self.vix_uw, self.bars_until, self.spx_price = vix_uw, bars_until, spx_price
        self.chain_override = dict(chain_override or {})   # {(name, 'HH:MM' or None): rows} — a chain for a minute
        self.minute: str | None = None                     # the tracker's capture minute, set by the tests
        self.requests: list = []
        self.calls = 0
        self._lock = threading.Lock()

    def get(self, path: str, params: dict | None = None) -> R.Answer:
        params = {k: v for k, v in (params or {}).items() if v is not None}
        self.limiter.acquire()
        try:
            with self._lock:
                self.requests.append((path, dict(params)))
                self.calls += 1
                staged = None
                for prefix, plan in self.fail_plan.items():
                    if path.startswith(prefix) and plan:
                        staged = plan.pop(0)
                        break
            if staged is None and path.endswith('/stock-state') and path.split('/')[3] in ('VIX', 'SPX') and not (
                    path.split('/')[3] == 'VIX' and self.vix_uw is not None):
                staged = 422
            self.log.info('GET %s%s -> %s (fake)', path, '?' + R.query_of(params) if params else '', staged or 200)
            if staged:
                msg = 'Stock state data is not available for index ticker' if staged == 422 else 'staged'
                return R.Answer(staged, [], 1, error=f'{staged}: {msg}')
            body = self._serve(path, params)
        finally:
            self.limiter.release()
        return R.Answer(200, R.rows_of(body), 1, body=body)

    def _chain_rows(self, name: str, day: str) -> list:
        ymd = day[2:4] + day[5:7] + day[8:]
        rows = []
        src = self.chain_override.get((name, self.minute)) or self.chain_override.get((name, None)) or self.fixture['rows']
        for r in src:
            p = parse_symbol(r['option_symbol'])
            if name == 'SPX':
                k = p[3] * SPXW_SCALE
                rr = dict(r, option_symbol=f'SPXW{ymd}{p[2]}{int(round(k * 1000)):08d}')
                for f in ('nbbo_bid', 'nbbo_ask'):
                    if rr.get(f) not in (None, ''):
                        rr[f] = f'{float(rr[f]) * SPXW_SCALE:.2f}'
                rows.append(rr)
                # an AM-settled SPX contract of the same date (a third Friday): the SPXW root alone must be kept
                rows.append(dict(rr, option_symbol=f'SPX{ymd}{p[2]}{int(round(k * 1000)):08d}', nbbo_bid='0.05', nbbo_ask='99'))
            else:
                rows.append(dict(r, option_symbol=f'{name}{ymd}{p[2]}{int(round(p[3] * 1000)):08d}'))
        return rows

    def _serve(self, path: str, params: dict):
        parts = path.split('/')
        name = parts[3] if len(parts) > 3 else 'SPY'
        if path.endswith('/option-contracts'):
            day = str(params.get('expiry') or R.ny_day_of(self.clock.utcnow()))
            page, limit = int(params.get('page', 0)), int(params.get('limit', 500))
            rows = self._chain_rows(name, day)
            return {'data': rows[page * limit:(page + 1) * limit]}
        if path.endswith('/stock-state'):
            now = self.clock.utcnow()
            if name == 'VIX':
                return {'data': {'close': f'{self.vix_uw:.2f}', 'prev_close': '15.00', 'market_time': 'regular', 'tape_time': R.iso_z(now)}}
            close = self.close_state if self.close_state is not None else self.spot
            return {'data': {'close': f'{close:.2f}', 'prev_close': f'{self.prev_close:.2f}', 'market_time': 'regular',
                             'tape_time': R.iso_z(now), 'open': f'{self.spot:.2f}', 'high': f'{self.spot + 1:.2f}',
                             'low': f'{self.spot - 1:.2f}', 'volume': 1, 'total_volume': 1}}
        if path.endswith('/ohlc/1m'):
            day = str(params.get('date'))
            t1559, t1600 = R.ny_at(day, '15:59'), R.ny_at(day, '16:00')
            cut = None if self.bars_until is None else R.ny_at(day, self.bars_until)
            rows = [{'start_time': R.iso_z(t1600), 'end_time': R.iso_z(t1600 + dt.timedelta(minutes=1)), 'market_time': 'po',
                     'open': '1', 'high': '1', 'low': '1', 'close': f'{self.close_1600:.2f}', 'volume': 1, 'total_volume': 1}]
            for m in range(1, 391):
                t = R.ny_at(day, '09:30') + dt.timedelta(minutes=m - 1)
                if cut is not None and t >= cut:
                    continue
                o, h, l, c, v = fake_bar(day, m, self.spot)
                if m == 390:
                    c = self.close_r
                elif m == 389:
                    c = self.close_r + 0.3
                rows.append({'start_time': R.iso_z(t), 'end_time': R.iso_z(t + dt.timedelta(minutes=1)), 'market_time': 'r',
                             'open': f'{o:.4f}', 'high': f'{max(h, c):.4f}', 'low': f'{min(l, c):.4f}', 'close': f'{c:.4f}',
                             'volume': int(v), 'total_volume': int(v)})
            rows.reverse()                                   # UW answers newest first
            return {'data': rows}
        if path.endswith('/ohlc/1d'):
            day = str(params.get('date'))
            rows = [{'date': day, 'market_time': 'pr', 'open': '1', 'high': '1', 'low': '1', 'close': '1', 'volume': 1, 'total_volume': 1}]
            if self.close_official is not None:
                rows.append({'date': day, 'market_time': 'r', 'open': '1', 'high': '1', 'low': '1', 'close': f'{self.close_official:.2f}',
                             'volume': 1, 'total_volume': 1})
            return {'data': rows}
        if path.endswith('/spot-exposures/strike'):
            if self.spx_price is None:
                return {'data': []}
            return {'data': [{'ticker': name, 'price': f'{self.spx_price:.2f}', 'time': R.iso_z(self.clock.utcnow()), 'strike': '3800'}]}
        return {'data': []}


class FakeTheta:
    """The Theta Terminal for the tests: VIX minutes for a day (`vix(day, m)`), or unreachable (`up=False`)"""

    def __init__(self, up: bool = True, base: float = 16.0):
        self.up, self.base = up, base
        self.error = None
        self.calls = 0

    def prints(self, symbol: str, day: str):
        self.calls += 1
        if not self.up:
            self.error = 'URLError: [Errno 111] Connection refused'
            return None
        s = (sum(ord(c) for c in day) % 7) / 10
        return [(m, round(self.base + s + 0.002 * m, 2)) for m in range(0, 391)]


# ---- the tracker ---------------------------------------------------------------------------------------------------------------------------

def is_tracked_day(day: str) -> bool:
    """Mon–Fri, not a holiday, not a half day (the reports skipped half days; a 13:00 close has no 13:30 or 15:00)"""
    return R.is_trading_day(day) and not R.is_half_day(day)


def minutes_of(day: str, cands: tuple | None = None) -> list[str]:
    return sorted({m for c in (cands or active_candidates()) for m in c.minutes})


def events_for(day: str, cands: tuple | None = None) -> list[tuple[str, str, dt.datetime]]:
    """(label, kind, when): a 'capture' each distinct minute, 15:58's 'close' (when fly5 runs), then the 'settle'"""
    cands = cands or active_candidates()
    if not is_tracked_day(day):
        return []
    out = [(m, 'capture', R.ny_at(day, m)) for m in minutes_of(day, cands)]
    if any(c.key == 'fly5' for c in cands):
        out.append((CLOSE_TIME, 'close', R.ny_at(day, CLOSE_TIME)))
    out.append((SETTLE_TIME, 'settle', R.ny_at(day, SETTLE_TIME)))
    return sorted(out, key=lambda e: e[2])


def next_event(now: dt.datetime, cands: tuple | None = None) -> tuple[str, str, str, dt.datetime]:
    d = dt.date.fromisoformat(R.ny_day_of(now))
    for _ in range(31):
        day = d.isoformat()
        for label, kind, when in events_for(day, cands):
            if when > now:
                return day, label, kind, when
        d += dt.timedelta(days=1)
    raise RuntimeError('no tracked day in the next month — extend HOLIDAYS?')


class Tracker:
    def __init__(self, client, store: R.Store, limiter: R.RateLimiter, log, clock: R.Clock, scrub: R.Scrub,
                 label: str | None = None, cands: tuple | None = None, theta=None, models_dir: Path = V.MODELS_DIR,
                 recorder_root: Path | None = None, bar_wait_s: float = BAR_WAIT_S, vix_uw: bool = True,
                 macro_path: Path | None = None):
        self.client, self.store, self.limiter, self.log, self.clock, self.scrub = client, store, limiter, log, clock, scrub
        self.label = label                 # 'smoke' marks a row that is not a session
        self.cands = tuple(cands) if cands else active_candidates()
        self.theta = theta if theta is not None else V.ThetaIndex()
        self.models_dir = Path(models_dir)
        self.bars = BarCache(store.root, recorder_root)
        self.bar_wait_s = bar_wait_s
        self.vix_uw = vix_uw
        self.macro_path = macro_path
        self._models = None
        self._budget_day = ''

    def _budget_for(self, day: str) -> None:
        if day != self._budget_day:
            self.limiter.reset_spent(self.store.budget_spent(day), self.store.budget_saver(day))
            self._budget_day = day

    def cand(self, key: str) -> Candidate | None:
        return next((c for c in self.cands if c.key == key), None)

    def macro(self, day: str, at: dt.datetime | None) -> dict:
        return MC.calendar(self.log, self.macro_path).stamps(day, at)

    # -- the frozen models (loaded once; a changed file is refused by its hash) --
    def models(self):
        if self._models is None:
            try:
                self._models = (V.FrozenModel.load(V.FULL, self.models_dir), V.FrozenModel.load(V.NOVIX, self.models_dir))
                self.log.info('frozen t2 models loaded: %s %s, %s %s', V.FULL, self._models[0].sha[:12], V.NOVIX, self._models[1].sha[:12])
            except Exception as e:  # noqa: BLE001
                self.log.error('the frozen t2 models did not load (%s) — candidate 3 is logged without its decile', e)
                self._models = (None, f'{type(e).__name__}: {e}')
        return self._models

    # -- a capture at one minute --
    def capture(self, day: str, minute: str, when: dt.datetime | None = None, force: bool = False) -> dict:
        if minute == CLOSE_TIME:
            return self.close_quotes(day, when, force)
        self._budget_for(day)
        spent0 = self.limiter.spent
        when = when or R.ny_at(day, minute)
        scan = self.label or minute
        todo = [(c, n) for c in self.cands if minute in c.minutes for n in c.names]
        summary = {'day': day, 'minute': minute, 'jobs': len(todo), 'skipped': 0, 'rows': 0, 'calls': 0, 'failed': 0, 'tradable': 0}
        if not todo:
            self.log.warning('%s is not a capture minute of any candidate (%s)', minute, ' '.join(minutes_of(day, self.cands)))
            return summary
        macro = self.macro(day, when)
        chains: dict[str, tuple] = {}
        states: dict[str, tuple] = {}
        for cand, name in todo:
            ep = endpoint_for(cand)
            had = self.store.marker(cand.key, name, day, scan)
            if had and had.status == 'done' and not force:
                self.log.info('skip %s %s %s %s — captured %s', cand.key, name, day, minute, had.fetched_at)
                summary['skipped'] += 1
                continue
            now = self.clock.utcnow()
            try:
                if name not in chains:
                    chains[name] = fetch_chain(self.client, name, day)
                if name not in states:
                    # UW Basic has no index price (stock-state 422): SPX's is read off its chain by parity
                    states[name] = ({}, None) if name == 'SPX' else fetch_state(self.client, name)
            except R.BudgetExhausted as e:
                self.log.error('STOP: %s — the capture at %s ends here', e, minute)
                summary['failed'] += 1
                break
            rows, pages, cerr = chains[name]
            state, serr = states[name]
            chain = Chain(rows, day, root='SPXW' if name == 'SPX' else None)
            extra: dict = {}
            if name == 'SPX':
                spot, used = chain.parity_spot()
                extra = {'spot_source': 'parity: median of K + call mid − put mid at the 3 strikes nearest C = P', 'parity_strikes': used}
            else:
                spot = fnum(state.get('close')) if state else None
            if cerr or serr or spot is None or not rows:
                err = self.scrub(cerr or serr or ('no spot' if spot is None else 'empty chain'))
                self.store.set_marker(R.Marker(cand.key, name, day, scan, 'partial', fetched_at=R.iso_z(now), note=err, version=VERSION))
                self.store.record_failure(day, {'at': R.iso_z(now), 'candidate': cand.key, 'name': name, 'minute': minute, 'error': err})
                self.log.error('%s %s %s %s: %s', cand.key, name, day, minute, err)
                summary['failed'] += 1
                continue
            if cand.key == 'condor_d20':
                extra.update(self.model_inputs(day, minute, chain))
            out = []
            for s in build(cand, chain, spot):
                out.append(capture_row(cand, s, minute, now, spot, state or {}, chain, pages, macro, extra))
                summary['tradable'] += int(s.tradable)
                self.log.info('%s %s %s %s: %s K0 %s straddle %s legs %s %s %s%s%s', cand.key, name, day, minute, s.structure,
                              fmt(s.k0), fmt(s.straddle), ' '.join(f'{l.side[0]}{l.right}{l.strike:g}@{l.bid}/{l.ask}' for l in s.legs),
                              s.package, fmt(s.price()) if s.legs else '—', '' if s.tradable else f' NOT TRADABLE: {s.reason}',
                              f" · t2 decile {extra.get('t2_decile_primary')} ({extra.get('t2_primary_model')})" if cand.key == 'condor_d20' else '')
            stamps = {'_day': day, '_scan': scan, '_scan_at': R.iso_z(when), '_fetched_at': R.iso_z(now), '_name': name}
            added, total = self.store.append(ep, name, day, out, stamps)
            summary['rows'] += added
            self.store.set_marker(R.Marker(cand.key, name, day, scan, 'done', rows_fetched=len(out), rows_added=added, pages=pages,
                                           calls=pages + 1, fetched_at=R.iso_z(now), version=VERSION))
        summary['calls'] = self.limiter.spent - spent0
        self.log.info('capture %s %s done: %d jobs, %d skipped, %d rows added, %d calls, %d failed, %d tradable; budget spent %d of %d',
                      day, minute, summary['jobs'], summary['skipped'], summary['rows'], summary['calls'], summary['failed'],
                      summary['tradable'], self.limiter.spent, self.limiter.budget)
        return summary

    # -- candidate 3: the frozen model at the capture minute --
    def model_inputs(self, day: str, minute: str, chain: Chain) -> dict:
        """The t2 features at the minute (vol_model.features_at) and both frozen models' score and decile; the primary
        decile is the full model's when all four VIX features are there, else the no-VIX model's (README, pre-registered).
        Never raises: what cannot be read is null and said in t2_note."""
        h, mm_ = minute.split(':')
        m = int(h) * 60 + int(mm_) - 570
        out: dict = {}
        notes = []
        full, novix = self.models()
        if full is None:
            return {'t2_note': f'models not loaded: {novix}'}
        out.update({'t2_model_full_sha': full.sha[:16], 't2_model_novix_sha': novix.sha[:16]})
        try:
            bars, asks = self._today_bars(day, m)
            prior, got = self._prior(day)
            vix, vix_prev, src, vnote = self._vix(day, m)
        except R.BudgetExhausted as e:
            return dict(out, t2_note=f'budget: {e}')
        if bars is None:
            return dict(out, t2_note='ohlc/1m for the day did not answer', t2_bar_asks=asks)
        table = V.day_table_inputs(prior)
        spot_bar = V.ffill(bars['c'])[m]
        k_atm, st = V.atm_straddle(chain.model_quotes(), spot_bar)
        f = V.features_at(m, bars, table, vix, vix_prev, st)
        ps, dsf = full.score(f)
        pn, dsn = novix.score(f)
        has_vix = all(not V.isnan(f[k]) for k in V.VIX_FEATS)
        complete = not V.isnan(bars['c'][m])
        if not complete:
            notes.append(f'the bar closing at {minute} was not out after {asks} asks — the last close carried')
        if table['missing']:
            notes.append(f"{table['missing']} of {PRIOR_SESSIONS} sessions before not in the cache")
        if V.isnan(f['straddle_rel']):
            notes.append('no ATM straddle on the chain')
        out.update({
            't2_score_full': fmt6(ps), 't2_decile_full': str(dsf), 't2_score_novix': fmt6(pn), 't2_decile_novix': str(dsn),
            't2_decile_primary': str(dsf if has_vix else dsn), 't2_primary_model': V.FULL if has_vix else V.NOVIX,
            'vix_source': src, 'vix_note': vnote, 'model_spot': fmt6(spot_bar), 'model_atm_k': fmt(k_atm), 'model_straddle': fmt6(st),
            't2_bar_last': None if bars['last_m'] is None else f"{(570 + bars['last_m'] - 1) // 60:02d}:{(570 + bars['last_m'] - 1) % 60:02d}",
            't2_bar_complete': fmt(complete), 't2_bar_asks': asks, 't2_prior_sessions': got,
            't2_atr_sessions': table['atr_n'], 't2_relvol_sessions': len(table['vol_ref']), 't2_note': '; '.join(notes) or None})
        out.update({f'f_{k}': fmt6(f[k]) for k in full.features})
        return out

    def _today_bars(self, day: str, m: int) -> tuple[dict | None, int]:
        """Today's regular bars closing at or before m (UW /ohlc/1m?date=D); asked once more after bar_wait_s when the bar
        closing at m (stamped m − 1) is not in the answer yet. (bars, asks)"""
        asks = 0
        bars = None
        for attempt in range(2):
            ans = self.client.get(f'/api/stock/{MODEL_NAME}/ohlc/1m', {'date': day, 'limit': 1000})
            asks += 1
            if not ans.ok:
                self.log.error('t2 bars %s %s: %s', day, m, self.scrub(ans.error))
                return None, asks
            bars = V.bars_from_uw(ans.rows, day, before_m=m)
            if not V.isnan(bars['c'][m]) or attempt == 1 or self.bar_wait_s <= 0:
                break
            self.log.info('t2 bars %s: the bar closing at minute %d is not out — asking again in %.0f s', day, m, self.bar_wait_s)
            self.clock.sleep(self.bar_wait_s)
        return bars, asks

    def _prior(self, day: str) -> tuple[list, int]:
        """The PRIOR_SESSIONS sessions before `day` as day summaries (None where not to be had): the cache, the
        recorder's file, else one UW call a day (kept). (summaries oldest first, sessions present)"""
        out = []
        for d in previous_sessions(day):
            bars = self.bars.get(MODEL_NAME, d)
            if bars is None:
                bars = self.bars.from_recorder(MODEL_NAME, d)
                if bars is not None:
                    self.bars.put(MODEL_NAME, d, bars, 'recorder ohlc_1m')
            if bars is None:
                ans = self.client.get(f'/api/stock/{MODEL_NAME}/ohlc/1m', {'date': d, 'limit': 1000})
                if ans.ok:
                    bars = V.bars_from_uw(ans.rows, d)
                    if bars['n'] >= 30:
                        self.bars.put(MODEL_NAME, d, bars, 'uw ohlc/1m (backfill)')
                        self.log.info('t2 cache: %s %s backfilled (%d regular bars)', MODEL_NAME, d, bars['n'])
                    else:
                        self.log.warning('t2 cache: %s %s answered %d regular bars — not kept', MODEL_NAME, d, bars['n'])
                        bars = None
                else:
                    self.log.error('t2 cache: %s %s: %s', MODEL_NAME, d, self.scrub(ans.error))
            out.append(V.day_summary(bars) if bars is not None else None)
        return out, sum(1 for x in out if x is not None)

    def backfill(self, day: str) -> dict:
        """--backfill: the sessions before `day` into the cache (at most PRIOR_SESSIONS calls, none for a day kept)"""
        self._budget_for(day)
        spent0 = self.limiter.spent
        try:
            prior, got = self._prior(day)
        except R.BudgetExhausted as e:
            self.log.error('STOP: %s — the backfill ends here', e)
            return {'day': day, 'present': None, 'calls': self.limiter.spent - spent0, 'failed': 1}
        return {'day': day, 'present': got, 'of': PRIOR_SESSIONS, 'calls': self.limiter.spent - spent0, 'failed': 0}

    def _vix_file(self, day: str) -> Path:
        return self.store.root / '_cache' / 'vix' / f'{day}.json'

    def _vix_state(self, day: str) -> dict:
        f = self._vix_file(day)
        try:
            return json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            return {}

    def _vix_save(self, day: str, st: dict) -> None:
        f = self._vix_file(day)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(st, separators=(',', ':')), encoding='utf-8')

    def _vix(self, day: str, m: int) -> tuple[list | None, float | None, str, str | None]:
        """VIX at the minute: UW (stock-state; asked at most once a session while it answers 422 for an index) → the
        Theta Terminal (the day's VIX minutes and the session before's last print) → none. (array, prev, source, note)"""
        st = self._vix_state(day)
        notes = []
        if self.vix_uw and st.get('uw') != 'unavailable':
            ans = self.client.get('/api/stock/VIX/stock-state')
            body = ans.body.get('data') if ans.ok and isinstance(ans.body, dict) else None
            px = fnum(body.get('close')) if isinstance(body, dict) else None
            if px is not None:
                reads = st.get('uw_reads', {})
                reads[str(m)] = px
                st.update({'uw': 'ok', 'uw_reads': reads, 'uw_prev': fnum(body.get('prev_close'))})
                self._vix_save(day, st)
                arr = V.vix_array([(int(k), v) for k, v in reads.items()])
                return arr, st.get('uw_prev'), 'uw', 'UW stock-state: no 09:31 print, vix_chg_open is null'
            st['uw'] = 'unavailable'
            st['uw_error'] = self.scrub((ans.error or 'no close')[:160])
            self._vix_save(day, st)
            notes.append(f"UW: {st['uw_error'][:60]}")
        elif st.get('uw') == 'unavailable':
            notes.append('UW: not available for an index (once a session)')
        if self.theta is not None:
            prints = self.theta.prints('VIX', day)
            if prints:
                prev = st.get('theta_prev')
                if prev is None:
                    pd_ = previous_sessions(day, 1)[0]
                    pp = self.theta.prints('VIX', pd_)
                    prev = max(pp, key=lambda x: x[0])[1] if pp else None
                    if prev is not None:
                        st['theta_prev'] = prev
                        self._vix_save(day, st)
                arr = V.vix_array([(mm, px) for mm, px in prints if mm <= m])
                if prev is None:
                    notes.append('Theta: no VIX print for the session before')
                return arr, prev, 'theta', '; '.join(notes) or None
            notes.append(f'Theta: {getattr(self.theta, "error", None) or "no answer"}')
        msg = '; '.join(notes)
        if not st.get('warned_none'):
            self.log.warning('VIX: no source answered (%s) — the no-VIX decile is the primary', msg)
            st['warned_none'] = True
            self._vix_save(day, st)
        return None, None, 'none', msg or None

    # -- 15:58: the fly5 structures read again off one chain a name --
    def close_quotes(self, day: str, when: dt.datetime | None = None, force: bool = False) -> dict:
        self._budget_for(day)
        spent0 = self.limiter.spent
        summary = {'day': day, 'minute': CLOSE_TIME, 'jobs': 0, 'skipped': 0, 'rows': 0, 'calls': 0, 'failed': 0, 'tradable': 0}
        cand = self.cand('fly5')
        if cand is None:
            return summary
        scan = (self.label + '-' if self.label else '') + 'close1558'
        for name in cand.names:
            df = self.store.read(cand.key, name, day)
            caps = [] if df is None else df.filter((pl.col('row_kind') == 'capture') & pl.col('l1_symbol').is_not_null()).to_dicts()
            if self.label:
                caps = [c for c in caps if c.get('_scan') == self.label]
            if not caps:
                continue
            summary['jobs'] += 1
            had = self.store.marker(cand.key, name, day, scan)
            if had and had.status == 'done' and not force:
                summary['skipped'] += 1
                continue
            now = self.clock.utcnow()
            try:
                rows, pages, err = fetch_chain(self.client, name, day)
            except R.BudgetExhausted as e:
                self.log.error('STOP: %s — the 15:58 read ends here', e)
                summary['failed'] += 1
                break
            if err or not rows:
                err = self.scrub(err or 'empty chain')
                self.store.set_marker(R.Marker(cand.key, name, day, scan, 'partial', fetched_at=R.iso_z(now), note=err, version=VERSION))
                self.store.record_failure(day, {'at': R.iso_z(now), 'candidate': cand.key, 'name': name, 'minute': CLOSE_TIME, 'error': err})
                summary['failed'] += 1
                continue
            chain = Chain(rows, day)
            out = []
            for cap in caps:
                s = structure_from_row(cap)
                if s is None:
                    continue
                r = close_row(cap, s, chain, now)
                out.append(r)
                self.log.info('15:58 %s %s %s %s: liquidation %s (mid %s) → P&L %s (mid %s)%s', name, day, cap['minute'], s.structure,
                              r.get('liq_nbbo'), r.get('liq_mid'), r.get('pnl_1558_nbbo'), r.get('pnl_1558_mid'),
                              f" — {r['close_reason']}" if r.get('close_reason') else '')
            stamps = {'_day': day, '_scan': scan, '_scan_at': R.iso_z(when or R.ny_at(day, CLOSE_TIME)), '_fetched_at': R.iso_z(now), '_name': name}
            added, _ = self.store.append(endpoint_for(cand), name, day, out, stamps)
            summary['rows'] += added
            self.store.set_marker(R.Marker(cand.key, name, day, scan, 'done', rows_fetched=len(out), rows_added=added, pages=pages,
                                           calls=pages, fetched_at=R.iso_z(now), version=VERSION))
        summary['calls'] = self.limiter.spent - spent0
        self.log.info('15:58 %s done: %d names, %d rows added, %d calls, %d failed', day, summary['jobs'], summary['rows'], summary['calls'], summary['failed'])
        return summary

    # -- the settlement pass --
    def settle(self, day: str, with_official: bool | None = None, force: bool = False) -> dict:
        """The after-close pass: re-runnable — a name settled on the official close is skipped before any call; one
        settled on the 15:59 bar alone is asked again (the daily bar may carry the official close now)"""
        self._budget_for(day)
        spent0 = self.limiter.spent
        now = self.clock.utcnow()
        summary = {'day': day, 'names': 0, 'skipped': 0, 'rows': 0, 'calls': 0, 'failed': 0, 'official': 0}
        names = sorted({n for c in self.cands for n in c.names if n != 'SPX'})
        if with_official is None:
            with_official = self.limiter.remaining >= 3 * len(names)   # --budget 22 (no new candidate): the daily bar waits for prev_close
        for name in names:
            caps = []
            settled_official = True
            closes_1558: dict = {}
            for cand in self.cands:
                if name not in cand.names:
                    continue
                df = self.store.read(cand.key, name, day)
                if df is None:
                    continue
                caps += [(cand, r) for r in df.filter(pl.col('row_kind') == 'capture').to_dicts()]
                if 'pnl_1558_nbbo' in df.columns:
                    for r in df.filter(pl.col('row_kind') == 'close1558').to_dicts():
                        closes_1558[(cand.key, r['minute'], r['structure'])] = r
                m = self.store.marker(cand.key, name, day, 'settle-official')
                settled_official = settled_official and bool(m and m.status == 'done')
            if not caps:
                continue
            if settled_official and not force:
                self.log.info('skip settle %s %s — settled on the official close', name, day)
                summary['skipped'] += 1
                continue
            summary['names'] += 1
            keep: dict = {}
            try:
                closes, errors = fetch_closes(self.client, name, day, with_official, keep=keep)
            except R.BudgetExhausted as e:
                self.log.error('STOP: %s — the settle pass for %s ends here', e, day)
                summary['failed'] += 1
                break
            if name == MODEL_NAME and keep.get('rows') and now >= R.ny_at(day, '16:00'):
                bars = V.bars_from_uw(keep['rows'], day)
                if bars['n'] >= 30 and self.bars.get(MODEL_NAME, day) is None:
                    self.bars.put(MODEL_NAME, day, bars, 'uw ohlc/1m (settle pass)')
            for e in errors:
                self.log.error('settle %s %s: %s', name, day, self.scrub(e))
                self.store.record_failure(day, {'at': R.iso_z(now), 'name': name, 'settle': True, 'error': self.scrub(e)})
            if closes.get('close_official') is None:
                # a prev_close read after the session, on a later day's capture, is the official close too
                closes['close_official'] = self._official_from_later_state(name, day)
                if closes['close_official'] is not None:
                    closes['close_official_from'] = 'next session prev_close'
            source = px = None
            if closes.get('close_official') is not None:
                source, px = 'official', closes['close_official']
            elif closes.get('close_1m_r') is not None:
                source, px = 'ohlc_1m_r', closes['close_1m_r']
            if source is None:
                self.log.error('settle %s %s: no settlement price', name, day)
                summary['failed'] += 1
                continue
            summary['official'] += int(source == 'official')
            self.log.info('settle %s %s: %s %s (15:59 bar %s · 16:00 bar %s · state %s %s · prev_close %s · official %s · check %s)', name, day,
                          source, fmt(px), fmt(closes.get('close_1m_r')), fmt(closes.get('close_1m_1600')), fmt(closes.get('close_state')),
                          closes.get('state_market_time'), fmt(closes.get('prev_close_state')), fmt(closes.get('close_official')),
                          'pass' if (closes.get('close_1m_r') is not None and closes.get('close_official') is not None
                                     and abs(closes['close_1m_r'] - closes['close_official']) <= SETTLE_CHECK_TOL)
                          else ('FAIL' if closes.get('close_official') is not None and closes.get('close_1m_r') is not None else '—'))
            by_cand: dict[str, list] = {}
            for cand, cap in caps:
                s = structure_from_row(cap)
                if s is None:
                    continue
                cl = closes_1558.get((cand.key, cap['minute'], cap['structure']))
                by_cand.setdefault(cand.key, []).append(settle_row(cap, s, source, px, closes, now, cl))
            calls = 2 + int(with_official)
            for key, rows in by_cand.items():
                cand = CANDIDATES[key]
                stamps = {'_day': day, '_scan': 'settle' if not self.label else f'{self.label}-settle',
                          '_scan_at': R.iso_z(R.ny_at(day, SETTLE_TIME)), '_fetched_at': R.iso_z(now), '_name': name}
                added, total = self.store.append(endpoint_for(cand), name, day, rows, stamps)
                summary['rows'] += added
                self.store.set_marker(R.Marker(cand.key, name, day, f'settle-{source}', 'done', rows_fetched=len(rows), rows_added=added,
                                               calls=calls, fetched_at=R.iso_z(now), version=VERSION))
        if self.cand('fly_spxw') is not None:
            self._settle_spx(day, now, force, summary)
        summary['calls'] = self.limiter.spent - spent0
        self.log.info('settle %s done: %d names, %d rows added, %d calls, %d failed, %d official; budget spent %d of %d', day,
                      summary['names'], summary['rows'], summary['calls'], summary['failed'], summary['official'],
                      self.limiter.spent, self.limiter.budget)
        return summary

    def _settle_spx(self, day: str, now: dt.datetime, force: bool, summary: dict) -> None:
        """fly_spxw: settled on UW's SPX `price` off /spot-exposures/strike (one call), a proxy for the official SET"""
        cand = self.cand('fly_spxw')
        df = self.store.read(cand.key, 'SPX', day)
        if df is None:
            return
        caps = df.filter(pl.col('row_kind') == 'capture').to_dicts()
        m = self.store.marker(cand.key, 'SPX', day, 'settle-spx_book_price')
        if not caps or (m and m.status == 'done' and not force):
            summary['skipped'] += int(bool(caps))
            return
        summary['names'] += 1
        try:
            px, at, err = fetch_spx_price(self.client)
        except R.BudgetExhausted as e:
            self.log.error('STOP: %s — the SPXW settle ends here', e)
            summary['failed'] += 1
            return
        if px is None:
            self.log.error('settle SPX %s: %s', day, self.scrub(err))
            self.store.record_failure(day, {'at': R.iso_z(now), 'name': 'SPX', 'settle': True, 'error': self.scrub(err)})
            summary['failed'] += 1
            return
        rows = []
        for cap in caps:
            s = structure_from_row(cap)
            if s is not None:
                rows.append(settle_row(cap, s, 'spx_book_price', px, {'close_state': px, 'state_market_time': at}, now))
        stamps = {'_day': day, '_scan': 'settle' if not self.label else f'{self.label}-settle',
                  '_scan_at': R.iso_z(R.ny_at(day, SETTLE_TIME)), '_fetched_at': R.iso_z(now), '_name': 'SPX'}
        added, _ = self.store.append(endpoint_for(cand), 'SPX', day, rows, stamps)
        summary['rows'] += added
        self.store.set_marker(R.Marker(cand.key, 'SPX', day, 'settle-spx_book_price', 'done', rows_fetched=len(rows), rows_added=added,
                                       calls=1, fetched_at=R.iso_z(now), version=VERSION))
        self.log.info('settle SPX %s: UW book price %s at %s (a proxy for the 16:00 SET)', day, fmt(px), at)

    def _official_from_later_state(self, name: str, day: str) -> float | None:
        """The first capture after `day` carries stock-state's prev_close = the official close of the session before"""
        d = dt.date.fromisoformat(day)
        for _ in range(10):
            d += dt.timedelta(days=1)
            if not is_tracked_day(d.isoformat()):
                continue
            for cand in self.cands:
                if name not in cand.names:
                    continue
                df = self.store.read(cand.key, name, d.isoformat())
                if df is None:
                    continue
                caps = df.filter((pl.col('row_kind') == 'capture') & pl.col('prev_close').is_not_null())
                if caps.height:
                    return fnum(caps.sort('captured_at')['prev_close'][0])
            return None
        return None

    # -- the daemon --
    def daemon(self, stop: threading.Event | None = None) -> None:
        stop = stop or threading.Event()
        self.log.info('paper tracker up (%s, %s): %s; captures %s, close quotes %s, settle %s New York, Mon–Fri less holidays and half days; '
                      'budget %d a session', VERSION, RULES_VERSION, ' '.join(c.key for c in self.cands), ' '.join(minutes_of('', self.cands)),
                      CLOSE_TIME, SETTLE_TIME, self.limiter.budget)
        now = self.clock.utcnow()
        today = R.ny_day_of(now)
        if is_tracked_day(today) and now >= R.ny_at(today, SETTLE_TIME):
            self.log.info('started after the settle time — running the settle pass for %s', today)
            self.settle(today)
        while not stop.is_set():
            day, label, kind, when = next_event(self.clock.utcnow(), self.cands)
            wait = (when - self.clock.utcnow()).total_seconds()
            self.log.info('next: %s %s on %s at %s (in %.0f min)', kind, label, day, R.iso_z(when), wait / 60)
            while wait > 0 and not stop.is_set():
                self.clock.sleep(min(wait, 30.0))
                wait = (when - self.clock.utcnow()).total_seconds()
            if stop.is_set():
                break
            try:
                if kind == 'capture':
                    self.capture(day, label, when)
                elif kind == 'close':
                    self.close_quotes(day, when)
                else:
                    self.settle(day)
            except Exception as e:  # noqa: BLE001
                self.log.error('the %s failed: %s', kind, self.scrub(f'{type(e).__name__}: {e}'))
            self.clock.sleep(1.0)


# ---- status -------------------------------------------------------------------------------------------------------------------------------------

def read_all(store: R.Store, cand: Candidate, name: str) -> pl.DataFrame | None:
    d = store.root / cand.key / name
    files = sorted(d.glob('*.parquet')) if d.is_dir() else []
    if not files:
        return None
    frames = [pl.read_parquet(f) for f in files]
    return pl.concat(frames, how='diagonal_relaxed')


def _means(sub: pl.DataFrame) -> dict:
    out = {'n': sub.height, 'sessions': sub['_day'].n_unique(),
           'mean_nbbo': sub['pnl_nbbo'].cast(pl.Float64).mean(), 'mean_mid': sub['pnl_mid'].cast(pl.Float64).mean(),
           'mean_1c': sub['pnl_1c'].cast(pl.Float64).mean(), 'mean_2c': sub['pnl_2c'].cast(pl.Float64).mean(),
           'win': sub.filter(pl.col('pnl_nbbo').cast(pl.Float64) > 0).height / sub.height,
           'mean_risk': sub['max_risk'].cast(pl.Float64).mean()}
    if 'pnl_1558_nbbo' in sub.columns:
        c = sub.filter(pl.col('pnl_1558_nbbo').is_not_null())
        out['n_1558'] = c.height
        out['mean_1558_nbbo'] = c['pnl_1558_nbbo'].cast(pl.Float64).mean() if c.height else None
        out['mean_1558_mid'] = c['pnl_1558_mid'].cast(pl.Float64).mean() if c.height else None
    return out


def status(store: R.Store, cands: tuple | None = None) -> dict:
    """Per candidate and name: sessions captured, settled (the best source a capture), mean P&L at the NBBO fill and
    the mid (and the stresses; fly5's 15:58 exit beside), the settlement check, the sessions still wanted; candidate 3
    also by its primary t2 decile (D1 against every session — the forward test reads the time-matched lift itself)"""
    out: dict = {}
    cands = cands or tuple(c for c in CANDIDATES.values() if not c.optional or (store.root / c.key).is_dir())
    for cand in cands:
        for name in cand.names:
            df = read_all(store, cand, name)
            entry = {'captured': 0, 'tradable_sessions': 0, 'settled': 0, 'official': 0, 'check_pass': 0, 'check_n': 0, 'structures': {}}
            if df is not None:
                caps = df.filter(pl.col('row_kind') == 'capture')
                entry['captured'] = caps['_day'].n_unique()
                entry['tradable_sessions'] = caps.filter(pl.col('tradable') == 'true')['_day'].n_unique()
                st = df.filter(pl.col('row_kind') == 'settle')
                if st.height:
                    # the best source a (day, minute, structure): official over the 15:59 bar
                    st = st.with_columns(pl.when(pl.col('settle_source') == 'official').then(0).otherwise(1).alias('_rank'))
                    st = st.sort(['_day', 'minute', 'structure', '_rank']).unique(subset=['_day', 'minute', 'structure'], keep='first', maintain_order=True)
                    entry['settled'] = st['_day'].n_unique()
                    entry['official'] = st.filter(pl.col('settle_source') == 'official')['_day'].n_unique()
                    if 'check_025' in st.columns:
                        chk = st.unique(subset=['_day']).filter(pl.col('check_025').is_not_null())
                        entry['check_n'] = chk.height
                        entry['check_pass'] = chk.filter(pl.col('check_025') == 'true').height
                    for s in cand.structures:
                        sub = st.filter((pl.col('structure') == s) & (pl.col('tradable') == 'true'))
                        if sub.height:
                            entry['structures'][s] = _means(sub)
                            if cand.key == 'condor_d20' and 't2_decile_primary' in sub.columns:
                                d1 = sub.filter(pl.col('t2_decile_primary') == '1')
                                entry['structures'][s]['d1'] = _means(d1) if d1.height else None
            out[(cand.key, name)] = entry
    return out


def print_status(store: R.Store) -> None:
    st = status(store)
    print(f'paper tracker — {store.root}  ({VERSION}, {RULES_VERSION}, {C3_RULES_VERSION})')
    for cand in [CANDIDATES[k] for k in dict.fromkeys(k for k, _ in st)]:
        print(f'\n{cand.key}: {cand.note}')
        print(f'  minutes {", ".join(cand.minutes)} New York; wings ±{cand.wing:g}; thresholds {", ".join(str(t) for t in cand.thresholds)} settled sessions'
              f'{" a name" if cand.per_name else ""}')
        pooled_settled = 0
        for name in cand.names:
            e = st[(cand.key, name)]
            pooled_settled = max(pooled_settled, e['settled']) if cand.per_name else e['settled']
            print(f'  {name}: {e["captured"]} sessions captured ({e["tradable_sessions"]} with a tradable structure), {e["settled"]} settled '
                  f'({e["official"]} on the official close); $0.25 settlement check {e["check_pass"]} of {e["check_n"]} pass')
            for s, v in e['structures'].items():
                print(f'    {s:<7} n {v["n"]:>4} in {v["sessions"]:>3} sessions  mean $ a structure: NBBO {v["mean_nbbo"]:+.2f}  mid {v["mean_mid"]:+.2f}  '
                      f'1c {v["mean_1c"]:+.2f}  2c {v["mean_2c"]:+.2f}  win {v["win"]:.0%}  mean max risk ${v["mean_risk"] * 100:.0f}')
                if v.get('n_1558'):
                    print(f'            15:58 exit (n {v["n_1558"]}): NBBO {v["mean_1558_nbbo"]:+.2f}  mid {v["mean_1558_mid"]:+.2f}')
                if 'd1' in v:
                    d1 = v['d1']
                    print('            primary t2 decile 1: ' + (f'n {d1["n"]} in {d1["sessions"]} sessions, NBBO {d1["mean_nbbo"]:+.2f}, mid {d1["mean_mid"]:+.2f}'
                                                              if d1 else 'none yet') + ' (the lift is read time-matched, README)')
            if cand.per_name:
                for t in cand.thresholds:
                    print(f'    to {t}: {max(0, t - e["settled"])} sessions remain')
        if not cand.per_name:
            for t in cand.thresholds:
                print(f'  to {t}: {max(0, t - pooled_settled)} sessions remain')
    bdir = store.root / '_budget'
    for f in sorted(bdir.glob('*.json'))[-5:] if bdir.is_dir() else []:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
            print(f'budget {d["day"]}: {d["spent"]} calls')
        except Exception:
            pass


# ---- the command line ------------------------------------------------------------------------------------------------------------------------

def build_pieces(args, token: str | None, stream=sys.stderr):
    scrub = R.Scrub(token)
    root = Path(args.data)
    if args.dry_run:
        root = root / 'dryrun'
    if args.smoke:
        root = root / 'smoke'
    store = R.Store(root)
    log = R.make_logger(scrub, root / '_logs', stream=stream, name='paper_tracker')
    clock = R.FakeClock() if args.dry_run else R.Clock()
    limiter = R.RateLimiter(max_in_flight=1, per_minute=30, daily_budget=args.budget, clock=clock)
    if args.dry_run:
        client = FakePaperClient(limiter, log, clock, scrub, fixture=Path(args.fixture))
        theta = FakeTheta()
    else:
        client = R.UwClient(token or '', limiter, log, clock, scrub)
        theta = V.ThetaIndex(os.environ.get('THETA_BASE') or V.THETA_BASE)
    rec_root = Path(os.environ.get('RECORDER_DATA') or (R.REPO / 'data_recorder'))
    tr = Tracker(client, store, limiter, log, clock, scrub, label='smoke' if args.smoke else None,
                 cands=active_candidates(args.spxw), theta=theta, recorder_root=None if args.dry_run else rec_root,
                 bar_wait_s=0 if args.dry_run else BAR_WAIT_S)
    return tr, store, log, clock


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--log', action='store_true', help='one capture at --when (for a scheduler); --when 15:58 reads the fly5 close quotes')
    mode.add_argument('--daemon', action='store_true', help='sleep to each capture minute, 15:58 and 16:20, Mon–Fri, for ever')
    mode.add_argument('--settle', action='store_true', help='the after-close pass for --day (today); re-runnable')
    mode.add_argument('--backfill', action='store_true', help='warm the minute-bar cache for --day: the 20 sessions before (one call a day not kept)')
    mode.add_argument('--status', action='store_true', help='sessions logged, running P&L, the settlement check, what remains')
    p.add_argument('--when', help='the minute for --log, HH:MM New York (11:30 12:00 12:30 13:00 13:30 14:00 14:30 15:00 15:30 15:58)')
    p.add_argument('--day', help='the New York day, YYYY-MM-DD (today by default)')
    p.add_argument('--dry-run', action='store_true', help='no network: the fixture chain, a fake clock, under <root>/dryrun')
    p.add_argument('--smoke', action='store_true', help='a live capture under <root>/smoke/, labelled smoke — never a session')
    p.add_argument('--force', action='store_true', help='capture again what a marker says is done (the dedupe still holds)')
    p.add_argument('--official', action='store_true', help='--settle: ask the daily bar even under a tight budget')
    p.add_argument('--spxw', action=argparse.BooleanOptionalAction, default=(os.environ.get('PAPER_SPXW', '1') not in ('0', 'false', 'no')),
                   help='fly_spxw (SPXW ±5 and ±25 flies at 15:00 and 15:30; 3–5 calls a session more) — ON by default since the owner\'s final patch; --no-spxw or PAPER_SPXW=0 turns it off')
    p.add_argument('--data', default=os.environ.get('PAPER_DATA') or str(R.REPO / 'data_recorder' / 'paper'),
                   help='the data root (PAPER_DATA, else data_recorder/paper in the repo)')
    p.add_argument('--budget', type=int, default=int(os.environ.get('PAPER_BUDGET') or DEFAULT_BUDGET),
                   help=f'calls a session (PAPER_BUDGET, {DEFAULT_BUDGET}: 36 warm, 56 the cold first day — README "The budget")')
    p.add_argument('--fixture', default=str(DEFAULT_CHAIN_FIXTURE), help='the fake chain (--dry-run)')
    args = p.parse_args(argv)

    token = os.environ.get('UW_API_TOKEN')
    if args.status:
        print_status(R.Store(Path(args.data)))
        return 0
    if not args.dry_run and not token:
        print('UW_API_TOKEN is not set — set it in the environment (never in a file in the repo)', file=sys.stderr)
        return 2
    tracker, store, log, clock = build_pieces(args, token)
    now = clock.utcnow()
    day = args.day or R.ny_day_of(now)
    if args.log:
        if not args.when:
            print('--log needs --when HH:MM', file=sys.stderr)
            return 2
        if not args.smoke and not args.dry_run and not is_tracked_day(day):
            print(f'{day} is not a tracked session (weekend, holiday or half day) — nothing logged', file=sys.stderr)
            return 0
        s = tracker.capture(day, args.when, force=args.force)
    elif args.settle:
        s = tracker.settle(day, with_official=True if args.official else None, force=args.force)
    elif args.backfill:
        s = tracker.backfill(day)
    else:
        tracker.daemon()
        return 0
    print(json.dumps(s))
    return 1 if s.get('failed') else 0


if __name__ == '__main__':
    sys.exit(main())
