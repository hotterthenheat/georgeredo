#!/usr/bin/env python3
"""
paper_tracker.py — the forward paper confirmation tracker for the two Compass Phase 2 candidates: an isolated logger
that records, every session, each candidate's structure at its minutes from Unusual Whales' quotes, and after the
close its settlement and paper P&L — so the confirmation samples the two reports asked for accumulate on their own.
It touches no UI and no discretionary signal; it writes Parquet and nothing else.

THE TWO CANDIDATES (the rules reproduced from the reports; the strikes are picked exactly as their engines pick them):

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
              NBBO. Threshold: 250 settled sessions a name.

EVERY CAPTURE LOGS the four legs' NBBO at the minute (the route carries no quote sizes — those columns stay null,
README), the NBBO package price, the mid package price, the stresses, spot (UW's stock-state `close`) and the
straddle. THE SETTLEMENT PASS (16:20 New York) logs, a name: UW's ohlc/1m last regular bar's close (the 15:59 bar),
the bar stamped 16:00, the stock-state `close` at that minute and its `prev_close`, and the official close when UW's
daily bar (`/ohlc/1d`, the `r` row dated D) carries it; the settlement used is the official close when present, else
the last regular bar; each leg at intrinsic, $0.65 a leg at the open and nothing at expiry (a worthless leg pays
nothing; an in-the-money leg settles at intrinsic with no fee assumed — the reports' convention); and the "$0.25
settlement check" = |ohlc/1m 15:59 close − official close| <= 0.25, flagged a session.

QUOTES: GET /api/stock/{name}/option-contracts?expiry=D (one page of 500 holds a same-day chain — SPY's 302 contracts
on 2026-10-21 — paged until a short page, cap 5), nbbo_bid / nbbo_ask a contract; the strike, right and expiry read
off option_symbol (OCC). SPOT: GET /api/stock/{name}/stock-state. One chain and one state a name a minute.

BUDGET a session: 9 name-minutes × 2 = 18 capture calls, and 3 a name (ohlc/1m, stock-state, ohlc/1d) × 2 names = 6
at the settle — 24, the default `--budget`. Under `--budget 22` the settle pass leaves the daily bar out and the
official close is read later off the next session's first stock-state `prev_close` (equal to the daily bar's `r`
close — checked live 2026-10-21, 773.09 both); the brief's 20 cannot hold the two settlement calls a name on top of
the 18 captures, so it is not the default. The count is kept in <root>/_budget/<day>.json across runs.

STORAGE: append-only Parquet under data_recorder/paper/<candidate>/<name>/<YYYY-MM-DD>.parquet with the recorder's
stamps and dedupe (eod_recorder.Store): a capture row a structure a minute, a settle row a structure a minute a
settlement source; a second capture of the same minute is skipped before any call (its marker), and a row already held
is never written twice. Every value is a string, the recorder's convention.

MODES: --log --when HH:MM (one capture, for a scheduler), --daemon (sleeps to each capture minute and to 16:20, Mon–Fri,
the recorder's holidays, half days skipped as the reports skipped them), --settle [--day D] (the after-close pass,
re-runnable: the official close is added once the daily bar carries it), --status, --dry-run (the fixture chain, no
network), --smoke (one live capture under <root>/smoke/, labelled smoke, never a session).

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

VERSION = 'paper-tracker-2026-10-21.1'
RULES_VERSION = 'rules-2026-10-21.1'     # the strike and fill rules below; a change here is a new version
NY, UTC = R.NY, R.UTC
FEE = 0.65                               # a leg, at the open; nothing at expiry
LEGS = 4
MIN_CREDIT = 0.05                        # a vertical's credit (hyp_b MIN_CREDIT)
MIN_RISK = 0.05                          # a fly's max risk (hyp_c MIN_DEBIT)
STRESSES = (0.01, 0.02)                  # a leg worse than the NBBO (hyp_c picks_fillstress)
SETTLE_TIME = '16:20'
SETTLE_CHECK_TOL = 0.25
CHAIN_PAGE = 500
CHAIN_MAX_PAGES = 5
DEFAULT_BUDGET = 24


@dataclass(frozen=True)
class Candidate:
    key: str
    names: tuple
    minutes: tuple
    wing: float
    structures: tuple
    thresholds: tuple                   # settled sessions wanted (per name for fly5, pooled for condor_em1)
    per_name: bool
    note: str


CANDIDATES: dict[str, Candidate] = {
    'condor_em1': Candidate('condor_em1', ('SPY',), ('11:30', '12:00', '12:30', '13:00', '13:30'), 2.0, ('condor',),
                            (60, 120), False, 'hyp_b: SPY 2-wide iron condor, shorts the first strike outside spot ± the ATM straddle'),
    'fly5': Candidate('fly5', ('SPY', 'QQQ'), ('15:00', '15:30'), 5.0, ('iron', 'call', 'put'), (250,), True,
                      'hyp_c: ±5 iron butterfly and the long call and put ±5 butterflies at the strike nearest spot'),
}

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
)
DEDUPE = ('row_kind', 'minute', 'structure', 'settle_source')


def endpoint_for(cand: Candidate) -> R.Endpoint:
    """The recorder's Endpoint shape names the folder (<root>/<candidate>/<NAME>/<day>.parquet) and the dedupe."""
    return R.Endpoint(cand.key, 'eod', '', DEDUPE, COLUMNS, note=cand.note)


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
    and bid >= 0 (hyp_b `two`, hyp_c `slice_minute`)."""

    def __init__(self, rows: list, expiry: str):
        self.expiry = expiry
        self.calls: dict[float, Quote] = {}
        self.puts: dict[float, Quote] = {}
        self.rows = 0
        for r in rows:
            p = parse_symbol(r.get('option_symbol'))
            if not p or p[1] != expiry:
                continue
            self.rows += 1
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


def condor_em1(chain: Chain, spot: float, wing: float = 2.0) -> Structure:
    """hyp_b `em1`: shorts the first strike outside spot ± the ATM straddle, longs `wing` beyond; each spread's credit
    (short bid − long ask) >= MIN_CREDIT, the short's bid > 0 and the long's ask > 0 (hyp_b leg_paths)"""
    st = chain.straddle(spot)
    if st is None:
        return Structure('condor', 'credit', [], None, None, wing, False, 'no strike with both sides quoted')
    k0, m = st
    ksc, ksp = chain.first_beyond(spot + m, 'call'), chain.first_beyond(spot - m, 'put')
    legs, why = [], []
    for right, ks, kl in (('C', ksc, None if ksc is None else ksc + wing), ('P', ksp, None if ksp is None else ksp - wing)):
        side = 'call' if right == 'C' else 'put'
        if ks is None:
            why.append(f'no {side} strike beyond the band')
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
    return Structure('condor', 'credit', legs if len(legs) == 4 else [], k0, m, wing, ok, '; '.join(why),
                     {'short_call': ksc, 'short_put': ksp})


def flies5(chain: Chain, spot: float, wing: float = 5.0) -> list[Structure]:
    """hyp_c build_flies: K0 the strike nearest spot with both sides quoted; iron (sell the K0 straddle at the bid, buy
    the K0−W put and K0+W call at the ask; risk W − credit), long call fly and long put fly (buy the wings at the ask,
    sell two K0 at the bid; risk = the debit); the short legs' bids > 0; max risk >= MIN_RISK"""
    k0 = chain.nearest(spot)
    out = []
    if k0 is None:
        return [Structure(s, 'credit' if s == 'iron' else 'debit', [], None, None, wing, False, 'no strike with both sides quoted')
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
    s = Structure('iron', 'credit', legs if len(legs) == 4 else [], k0, strad, wing, not why, '; '.join(why))
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
        s = Structure(name, 'debit', legs if len(legs) == 3 else [], k0, strad, wing, not why, '; '.join(why))
        if s.tradable and (s.max_risk() is None or s.max_risk() < MIN_RISK - 1e-9):
            s.tradable, s.reason = False, f'max risk {s.max_risk():.2f} under {MIN_RISK}'
        out.append(s)
    return out


def build(cand: Candidate, chain: Chain, spot: float) -> list[Structure]:
    if cand.key == 'condor_em1':
        return [condor_em1(chain, spot, cand.wing)]
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
                pages: int) -> dict:
    has = bool(s.legs)
    r = {'row_kind': 'capture', 'candidate': cand.key, 'structure': s.structure, 'minute': minute,
         'rules_version': RULES_VERSION, 'tracker_version': VERSION, 'captured_at': R.iso_z(now), 'spot': fmt(spot),
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


def settle_row(cap: dict, s: Structure, source: str, px: float, closes: dict, now: dt.datetime) -> dict:
    """The settle row for one capture row at one settlement source"""
    r = {k: cap.get(k) for k in ('candidate', 'structure', 'minute', 'rules_version', 'tracker_version', 'wing', 'package',
                                 'k0', 'straddle', 'spot', 'price_nbbo', 'price_mid', 'price_1c', 'price_2c', 'max_risk',
                                 'tradable', 'reason')}
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


def fetch_closes(client, name: str, day: str, with_official: bool = True) -> tuple[dict, list]:
    """The settlement figures a name: the ohlc/1m last regular bar and the 16:00 bar, the stock-state close and its
    prev_close, the daily bar's official close (when it is there). (closes, errors)"""
    closes: dict = {}
    errors = []
    ans = client.get(f'/api/stock/{name}/ohlc/1m', {'date': day, 'limit': 1000})
    if ans.ok:
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


# ---- the fake client (the dry run and the tests: no network) -----------------------------------------------------------------------

DEFAULT_CHAIN_FIXTURE = R.REPO / 'tests' / 'fixtures' / 'paper_chain_SPY.json'


class FakePaperClient:
    """Serves the fixture chain (its option_symbols re-dated to the day asked, its root to the name asked), a
    stock-state at `spot`, an ohlc/1m day whose 15:59 bar closes at `close_r` and 16:00 bar at `close_1600`, and a
    daily bar whose `r` row closes at `close_official` (None: the daily bar has not caught up yet — the row is left
    out). The same limiter as the real client; `fail_plan` stages a status per path prefix."""

    def __init__(self, limiter, log, clock, scrub, fixture: Path = DEFAULT_CHAIN_FIXTURE, spot: float = 773.40,
                 prev_close: float = 770.72, close_r: float = 777.13, close_1600: float = 777.39,
                 close_official: float | None = 777.20, close_state: float | None = None, fail_plan: dict | None = None):
        self.limiter, self.log, self.clock, self.scrub = limiter, log, clock, scrub
        self.fixture = json.loads(Path(fixture).read_text(encoding='utf-8'))
        self.spot, self.prev_close, self.close_r, self.close_1600 = spot, prev_close, close_r, close_1600
        self.close_official, self.close_state = close_official, close_state
        self.fail_plan = dict(fail_plan or {})
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
            self.log.info('GET %s%s -> %s (fake)', path, '?' + R.query_of(params) if params else '', staged or 200)
            if staged:
                return R.Answer(staged, [], 1, error=f'{staged}: staged')
            body = self._serve(path, params)
        finally:
            self.limiter.release()
        return R.Answer(200, R.rows_of(body), 1, body=body)

    def _serve(self, path: str, params: dict):
        parts = path.split('/')
        name = parts[3] if len(parts) > 3 else 'SPY'
        if path.endswith('/option-contracts'):
            day = str(params.get('expiry') or R.ny_day_of(self.clock.utcnow()))
            page, limit = int(params.get('page', 0)), int(params.get('limit', 500))
            ymd = day[2:4] + day[5:7] + day[8:]
            rows = []
            for r in self.fixture['rows']:
                p = parse_symbol(r['option_symbol'])
                r = dict(r, option_symbol=f'{name}{ymd}{p[2]}{int(round(p[3] * 1000)):08d}')
                rows.append(r)
            return {'data': rows[page * limit:(page + 1) * limit]}
        if path.endswith('/stock-state'):
            now = self.clock.utcnow()
            close = self.close_state if self.close_state is not None else self.spot
            return {'data': {'close': f'{close:.2f}', 'prev_close': f'{self.prev_close:.2f}', 'market_time': 'regular',
                             'tape_time': R.iso_z(now), 'open': f'{self.spot:.2f}', 'high': f'{self.spot + 1:.2f}',
                             'low': f'{self.spot - 1:.2f}', 'volume': 1, 'total_volume': 1}}
        if path.endswith('/ohlc/1m'):
            day = str(params.get('date'))
            t1559, t1600 = R.ny_at(day, '15:59'), R.ny_at(day, '16:00')
            return {'data': [
                {'start_time': R.iso_z(t1600), 'end_time': R.iso_z(t1600 + dt.timedelta(minutes=1)), 'market_time': 'po',
                 'open': '1', 'high': '1', 'low': '1', 'close': f'{self.close_1600:.2f}', 'volume': 1, 'total_volume': 1},
                {'start_time': R.iso_z(t1559), 'end_time': R.iso_z(t1600), 'market_time': 'r', 'open': '1', 'high': '1',
                 'low': '1', 'close': f'{self.close_r:.2f}', 'volume': 1, 'total_volume': 1},
                {'start_time': R.iso_z(t1559 - dt.timedelta(minutes=1)), 'end_time': R.iso_z(t1559), 'market_time': 'r',
                 'open': '1', 'high': '1', 'low': '1', 'close': f'{self.close_r + 0.3:.2f}', 'volume': 1, 'total_volume': 1},
            ]}
        if path.endswith('/ohlc/1d'):
            day = str(params.get('date'))
            rows = [{'date': day, 'market_time': 'pr', 'open': '1', 'high': '1', 'low': '1', 'close': '1', 'volume': 1, 'total_volume': 1}]
            if self.close_official is not None:
                rows.append({'date': day, 'market_time': 'r', 'open': '1', 'high': '1', 'low': '1', 'close': f'{self.close_official:.2f}',
                             'volume': 1, 'total_volume': 1})
            return {'data': rows}
        return {'data': []}


# ---- the tracker ---------------------------------------------------------------------------------------------------------------------------

def is_tracked_day(day: str) -> bool:
    """Mon–Fri, not a holiday, not a half day (the reports skipped half days; a 13:00 close has no 13:30 or 15:00)"""
    return R.is_trading_day(day) and not R.is_half_day(day)


def minutes_of(day: str) -> list[str]:
    return sorted({m for c in CANDIDATES.values() for m in c.minutes})


def events_for(day: str) -> list[tuple[str, str, dt.datetime]]:
    """(label, kind, when): a 'capture' each distinct minute, then the 'settle'"""
    if not is_tracked_day(day):
        return []
    out = [(m, 'capture', R.ny_at(day, m)) for m in minutes_of(day)]
    out.append((SETTLE_TIME, 'settle', R.ny_at(day, SETTLE_TIME)))
    return out


def next_event(now: dt.datetime) -> tuple[str, str, str, dt.datetime]:
    d = dt.date.fromisoformat(R.ny_day_of(now))
    for _ in range(31):
        day = d.isoformat()
        for label, kind, when in events_for(day):
            if when > now:
                return day, label, kind, when
        d += dt.timedelta(days=1)
    raise RuntimeError('no tracked day in the next month — extend HOLIDAYS?')


class Tracker:
    def __init__(self, client, store: R.Store, limiter: R.RateLimiter, log, clock: R.Clock, scrub: R.Scrub,
                 label: str | None = None):
        self.client, self.store, self.limiter, self.log, self.clock, self.scrub = client, store, limiter, log, clock, scrub
        self.label = label                 # 'smoke' marks a row that is not a session
        self._budget_day = ''

    def _budget_for(self, day: str) -> None:
        if day != self._budget_day:
            self.limiter.reset_spent(self.store.budget_spent(day), self.store.budget_saver(day))
            self._budget_day = day

    # -- a capture at one minute --
    def capture(self, day: str, minute: str, when: dt.datetime | None = None, force: bool = False) -> dict:
        self._budget_for(day)
        when = when or R.ny_at(day, minute)
        scan = self.label or minute
        todo = [(c, n) for c in CANDIDATES.values() if minute in c.minutes for n in c.names]
        summary = {'day': day, 'minute': minute, 'jobs': len(todo), 'skipped': 0, 'rows': 0, 'calls': 0, 'failed': 0, 'tradable': 0}
        if not todo:
            self.log.warning('%s is not a capture minute of any candidate (%s)', minute, ' '.join(minutes_of(day)))
            return summary
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
                    summary['calls'] += chains[name][1] or 1
                if name not in states:
                    states[name] = fetch_state(self.client, name)
                    summary['calls'] += 1
            except R.BudgetExhausted as e:
                self.log.error('STOP: %s — the capture at %s ends here', e, minute)
                summary['failed'] += 1
                break
            rows, pages, cerr = chains[name]
            state, serr = states[name]
            spot = fnum(state.get('close')) if state else None
            if cerr or serr or spot is None or not rows:
                err = self.scrub(cerr or serr or ('no spot' if spot is None else 'empty chain'))
                self.store.set_marker(R.Marker(cand.key, name, day, scan, 'partial', fetched_at=R.iso_z(now), note=err, version=VERSION))
                self.store.record_failure(day, {'at': R.iso_z(now), 'candidate': cand.key, 'name': name, 'minute': minute, 'error': err})
                self.log.error('%s %s %s %s: %s', cand.key, name, day, minute, err)
                summary['failed'] += 1
                continue
            chain = Chain(rows, day)
            out = []
            for s in build(cand, chain, spot):
                out.append(capture_row(cand, s, minute, now, spot, state, chain, pages))
                summary['tradable'] += int(s.tradable)
                self.log.info('%s %s %s %s: %s K0 %s straddle %s legs %s %s %s%s', cand.key, name, day, minute, s.structure,
                              fmt(s.k0), fmt(s.straddle), ' '.join(f'{l.side[0]}{l.right}{l.strike:g}@{l.bid}/{l.ask}' for l in s.legs),
                              s.package, fmt(s.price()) if s.legs else '—', '' if s.tradable else f' NOT TRADABLE: {s.reason}')
            stamps = {'_day': day, '_scan': scan, '_scan_at': R.iso_z(when), '_fetched_at': R.iso_z(now), '_name': name}
            added, total = self.store.append(ep, name, day, out, stamps)
            summary['rows'] += added
            self.store.set_marker(R.Marker(cand.key, name, day, scan, 'done', rows_fetched=len(out), rows_added=added, pages=pages,
                                           calls=pages + 1, fetched_at=R.iso_z(now), version=VERSION))
        self.log.info('capture %s %s done: %d jobs, %d skipped, %d rows added, %d calls, %d failed, %d tradable; budget spent %d of %d',
                      day, minute, summary['jobs'], summary['skipped'], summary['rows'], summary['calls'], summary['failed'],
                      summary['tradable'], self.limiter.spent, self.limiter.budget)
        return summary

    # -- the settlement pass --
    def settle(self, day: str, with_official: bool | None = None, force: bool = False) -> dict:
        """The after-close pass: re-runnable — a name settled on the official close is skipped before any call; one
        settled on the 15:59 bar alone is asked again (the daily bar may carry the official close now)"""
        self._budget_for(day)
        now = self.clock.utcnow()
        summary = {'day': day, 'names': 0, 'skipped': 0, 'rows': 0, 'calls': 0, 'failed': 0, 'official': 0}
        names = sorted({n for c in CANDIDATES.values() for n in c.names})
        if with_official is None:
            with_official = self.limiter.remaining >= 3 * len(names)   # --budget 20: the daily bar waits for prev_close
        for name in names:
            caps = []
            settled_official = True
            for cand in CANDIDATES.values():
                if name not in cand.names:
                    continue
                df = self.store.read(cand.key, name, day)
                if df is None:
                    continue
                caps += [(cand, r) for r in df.filter(pl.col('row_kind') == 'capture').to_dicts()]
                m = self.store.marker(cand.key, name, day, 'settle-official')
                settled_official = settled_official and bool(m and m.status == 'done')
            if not caps:
                continue
            if settled_official and not force:
                self.log.info('skip settle %s %s — settled on the official close', name, day)
                summary['skipped'] += 1
                continue
            summary['names'] += 1
            try:
                closes, errors = fetch_closes(self.client, name, day, with_official)
            except R.BudgetExhausted as e:
                self.log.error('STOP: %s — the settle pass for %s ends here', e, day)
                summary['failed'] += 1
                break
            summary['calls'] += 2 + int(with_official)
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
                by_cand.setdefault(cand.key, []).append(settle_row(cap, s, source, px, closes, now))
            for key, rows in by_cand.items():
                cand = CANDIDATES[key]
                stamps = {'_day': day, '_scan': 'settle' if not self.label else f'{self.label}-settle',
                          '_scan_at': R.iso_z(R.ny_at(day, SETTLE_TIME)), '_fetched_at': R.iso_z(now), '_name': name}
                added, total = self.store.append(endpoint_for(cand), name, day, rows, stamps)
                summary['rows'] += added
                self.store.set_marker(R.Marker(cand.key, name, day, f'settle-{source}', 'done', rows_fetched=len(rows), rows_added=added,
                                               calls=2 + int(with_official), fetched_at=R.iso_z(now), version=VERSION))
        self.log.info('settle %s done: %d names, %d rows added, %d calls, %d failed, %d official; budget spent %d of %d', day,
                      summary['names'], summary['rows'], summary['calls'], summary['failed'], summary['official'],
                      self.limiter.spent, self.limiter.budget)
        return summary

    def _official_from_later_state(self, name: str, day: str) -> float | None:
        """The first capture after `day` carries stock-state's prev_close = the official close of the session before"""
        d = dt.date.fromisoformat(day)
        for _ in range(10):
            d += dt.timedelta(days=1)
            if not is_tracked_day(d.isoformat()):
                continue
            for cand in CANDIDATES.values():
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
        self.log.info('paper tracker up (%s, %s): captures %s, settle %s New York, Mon–Fri less holidays and half days; budget %d a session',
                      VERSION, RULES_VERSION, ' '.join(minutes_of('')), SETTLE_TIME, self.limiter.budget)
        now = self.clock.utcnow()
        today = R.ny_day_of(now)
        if is_tracked_day(today) and now >= R.ny_at(today, SETTLE_TIME):
            self.log.info('started after the settle time — running the settle pass for %s', today)
            self.settle(today)
        while not stop.is_set():
            day, label, kind, when = next_event(self.clock.utcnow())
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


def status(store: R.Store) -> dict:
    """Per candidate and name: sessions captured, settled (the best source a capture), mean P&L at the NBBO fill and
    the mid (and the stresses), the settlement check, the sessions still wanted"""
    out: dict = {}
    for cand in CANDIDATES.values():
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
                    chk = st.unique(subset=['_day']).filter(pl.col('check_025').is_not_null())
                    entry['check_n'] = chk.height
                    entry['check_pass'] = chk.filter(pl.col('check_025') == 'true').height
                    for s in cand.structures:
                        sub = st.filter((pl.col('structure') == s) & (pl.col('tradable') == 'true'))
                        if sub.height:
                            entry['structures'][s] = {
                                'n': sub.height, 'sessions': sub['_day'].n_unique(),
                                'mean_nbbo': sub['pnl_nbbo'].cast(pl.Float64).mean(), 'mean_mid': sub['pnl_mid'].cast(pl.Float64).mean(),
                                'mean_1c': sub['pnl_1c'].cast(pl.Float64).mean(), 'mean_2c': sub['pnl_2c'].cast(pl.Float64).mean(),
                                'win': sub.filter(pl.col('pnl_nbbo').cast(pl.Float64) > 0).height / sub.height,
                                'mean_risk': sub['max_risk'].cast(pl.Float64).mean()}
            out[(cand.key, name)] = entry
    return out


def print_status(store: R.Store) -> None:
    st = status(store)
    print(f'paper tracker — {store.root}  ({VERSION}, {RULES_VERSION})')
    for cand in CANDIDATES.values():
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
    else:
        client = R.UwClient(token or '', limiter, log, clock, scrub)
    return Tracker(client, store, limiter, log, clock, scrub, label='smoke' if args.smoke else None), store, log, clock


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--log', action='store_true', help='one capture at --when (for a scheduler)')
    mode.add_argument('--daemon', action='store_true', help='sleep to each capture minute and to 16:20, Mon–Fri, for ever')
    mode.add_argument('--settle', action='store_true', help='the after-close pass for --day (today); re-runnable')
    mode.add_argument('--status', action='store_true', help='sessions logged, running P&L, the settlement check, what remains')
    p.add_argument('--when', help='the capture minute for --log, HH:MM New York (11:30 12:00 12:30 13:00 13:30 15:00 15:30)')
    p.add_argument('--day', help='the New York day, YYYY-MM-DD (today by default)')
    p.add_argument('--dry-run', action='store_true', help='no network: the fixture chain, a fake clock, under <root>/dryrun')
    p.add_argument('--smoke', action='store_true', help='a live capture under <root>/smoke/, labelled smoke — never a session')
    p.add_argument('--force', action='store_true', help='capture again what a marker says is done (the dedupe still holds)')
    p.add_argument('--official', action='store_true', help='--settle: ask the daily bar even under a tight budget')
    p.add_argument('--data', default=os.environ.get('PAPER_DATA') or str(R.REPO / 'data_recorder' / 'paper'),
                   help='the data root (PAPER_DATA, else data_recorder/paper in the repo)')
    p.add_argument('--budget', type=int, default=int(os.environ.get('PAPER_BUDGET') or DEFAULT_BUDGET),
                   help=f'calls a session (PAPER_BUDGET, {DEFAULT_BUDGET}: 18 captures + 6 at the settle)')
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
    else:
        tracker.daemon()
        return 0
    print(json.dumps(s))
    return 1 if s.get('failed') else 0


if __name__ == '__main__':
    sys.exit(main())
