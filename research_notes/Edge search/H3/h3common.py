"""
h3common.py — the shared rules of H3 (PREREG_H3.md, commit 001a136): the event's dates (P, R), the liquidity floor, the stored
files, the expiry, the four strikes and the entry, the exit valuation and the $ of a trade. Reads files only; no vendor call.

The calendar, the bars, the tier measure and the fees come from research_notes/Compass direction/dcommon.py (read, not edited).
Run every script of this folder with PYTHONDONTWRITEBYTECODE=1 (python3 -I -B) so nothing is written into that folder.
"""
from __future__ import annotations

import bisect
import json
import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass direction'))
import dcommon as D  # noqa: E402

AL = D.AL
SPN = Path('/tmp/claude-0/-home-user/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
STORE = SPN / 'h3' / 'store'              # this study's fetch
PEAD_STORE = D.STORE                       # read only: the PEAD fetch's files (tier files, any P file it holds)
OUT = HERE / 'out'
PREREG = HERE / 'PREREG_H3.md'
PREREG_COMMIT = '001a136'

WIN_FROM, WIN_TO = '2019-04-01', '2022-12-30'
MAX_DTE = 14
PARITY_TOL = 0.05
FEE = D.FEE                                # 0.68748
SPLIT_RATIOS = (1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10, 1 / 20, 1 / 50, 2, 3, 4, 5, 10, 20, 50)


def event_lists() -> dict:
    return D.event_lists()


def ev_dates(report_date: str, report_time: str) -> dict:
    """R (the reaction session) and P (the trading day before R); status 'ok' or why the event is not formed"""
    td = D.tday_set()
    if report_time == 'premarket':
        R = report_date if report_date in td else D.next_tday(report_date)
    elif report_time == 'postmarket':
        R = D.next_tday(report_date)
    else:
        return dict(status='no report time')
    if R is None:
        return dict(status='after the calendar')
    P = D.prev_tday(R)
    if P is None:
        return dict(status='before the calendar', R=R)
    ses = set(D.sessions())
    if P not in ses or R not in ses:
        return dict(status='P or R is a half day', R=R, P=P)
    if P < WIN_FROM or R > WIN_TO:
        return dict(status='outside the window', R=R, P=P)
    return dict(status='ok', R=R, P=P)


def liquid_before(bars: D.Bars, P: str):
    """the $50 M floor on the 60 trading days ending at the session before P (at least 50 present)"""
    return bars.liquid(D.prev_tday(P))


# ---- the stored files ----------------------------------------------------------------------------------------------------------

def path(sym: str, day: str, what: str) -> Path:
    return STORE / sym / f'{day}__{what}.parquet'


def find_all(sym: str, day: str) -> Path | None:
    """a stored every-expiry file of the name on the day: this study's store, else the PEAD store (read only)"""
    for root in (STORE, PEAD_STORE):
        p = root / sym / f'{day}__ALL.parquet'
        if p.exists():
            return p
    return None


def read(p: Path) -> pl.DataFrame:
    return D.norm(pl.read_parquet(p))


# ---- the expiry and the entry (PREREG_H3 §3) ------------------------------------------------------------------------------------

def choose_expiry(P: str, R: str, expirations) -> str | None:
    """the earliest listed expiration whose last trading day is after R and whose date is at most 14 calendar days after P"""
    c = []
    for e in set(expirations):
        le = D.last_trading_day(e)
        if le is None or le <= R:
            continue
        if D.cal_days(P, e) > MAX_DTE:
            continue
        c.append(e)
    return min(c) if c else None


def stands(b, a) -> bool:
    return b is not None and a is not None and b > 0 and a > 0 and a >= b


def nearest(strikes: np.ndarray, target: float, far_side: str) -> float | None:
    """the listed strike nearest the target; ties: 'up' the higher, 'down' the lower"""
    if strikes.size == 0:
        return None
    d = np.abs(strikes - target)
    m = d.min()
    cand = strikes[np.abs(d - m) <= 1e-9]
    return float(cand.max() if far_side == 'up' else cand.min())


def quotes(x: pl.DataFrame) -> dict:
    """one expiry's rows → {(right, strike): (bid, ask)}"""
    return {(r, round(float(k), 4)): (float(b), float(a))
            for r, k, b, a in zip(x['right'].to_list(), x['strike'].to_list(), x['bid'].to_list(), x['ask'].to_list())}


def entry(xP: pl.DataFrame, closeP: float) -> dict:
    """P's rows of the chosen expiry and close(P) → the condor at entry, or status = why it is not formed. Entry-side only."""
    q = quotes(xP)
    calls = np.array(sorted({k for (r, k) in q if r == 'C'}), float)
    puts = np.array(sorted({k for (r, k) in q if r == 'P'}), float)
    both = np.array(sorted(set(calls.tolist()) & set(puts.tolist())), float)
    if both.size == 0:
        return dict(status='no standing ATM pair')
    K0 = nearest(both, closeP, 'down')
    cb, ca = q[('C', K0)]
    pb, pa = q[('P', K0)]
    if not (stands(cb, ca) and stands(pb, pa)):
        return dict(status='no standing ATM pair', K0=K0)
    cm, pm = (cb + ca) / 2, (pb + pa) / 2
    IM = cm + pm
    F = K0 + cm - pm
    if not IM > 0:
        return dict(status='no standing ATM pair', K0=K0)
    if abs(F / closeP - 1) > PARITY_TOL:
        return dict(status='bars and options disagree (parity > 5 %)', K0=K0, IM=IM, F=F)
    Kcs = nearest(calls, K0 + 0.5 * IM, 'up')
    Kcl = nearest(calls, K0 + 1.5 * IM, 'up')
    Kps = nearest(puts, K0 - 0.5 * IM, 'down')
    Kpl = nearest(puts, K0 - 1.5 * IM, 'down')
    out = dict(K0=K0, IM=IM, F=F, Kcs=Kcs, Kcl=Kcl, Kps=Kps, Kpl=Kpl)
    if not (Kcl > Kcs and Kpl < Kps):
        return dict(status='strike grid too coarse for the wings', **out)
    legs = {'cs': ('C', Kcs), 'cl': ('C', Kcl), 'ps': ('P', Kps), 'pl': ('P', Kpl)}
    bad = [n for n, k in legs.items() if not stands(*q[k])]
    if bad:
        return dict(status='untradable leg at entry', bad=bad, **out)
    for n, k in legs.items():
        out[n + '_bid'], out[n + '_ask'] = q[k]
    c = out['cs_bid'] + out['ps_bid'] - out['cl_ask'] - out['pl_ask']
    W = max(Kcl - Kcs, Kps - Kpl)
    out.update(credit=c, W=W, fly=bool(Kcs == Kps))
    if not c > 1e-12:
        return dict(status='no credit', **out)
    if c >= W - 1e-12:
        return dict(status='credit at or above the width', **out)
    out['status'] = 'formed'
    return out


# ---- the exit and the trade (PREREG_H3 §3) -------------------------------------------------------------------------------------

def intrinsic(right: str, K: float, s: float) -> float:
    return max(s - K, 0.0) if right == 'C' else max(K - s, 0.0)


def split_sized(closeP: float, closeR: float | None) -> bool:
    if closeR is None or not closeP:
        return False
    q = closeR / closeP
    return any(abs(q / r - 1) <= 0.10 for r in SPLIT_RATIOS)


def max_loss_dollars(e: dict) -> float:
    return -100.0 * (e['W'] - e['credit']) - 4 * FEE - 4 * FEE


def trade(e: dict, xR: pl.DataFrame | None, closeP: float, closeR: float | None) -> dict:
    """the entry (formed), R's rows of the expiry (None or empty when the file holds none) and the closes → the trade"""
    fees_in = 4 * FEE
    risk = 100.0 * (e['W'] - e['credit'])
    if split_sized(closeP, closeR):
        d = max_loss_dollars(e)
        return dict(pnl=d, pct_risk=d / risk, how='split-sized move: booked at max loss', fallbacks=0)
    q = quotes(xR) if xR is not None and xR.height else {}
    legs = {'cs': ('C', e['Kcs'], 'short'), 'ps': ('P', e['Kps'], 'short'), 'cl': ('C', e['Kcl'], 'long'), 'pl': ('P', e['Kpl'], 'long')}
    px, fb, fees_out = {}, 0, 0.0
    for n, (r, K, side) in legs.items():
        b, a = q.get((r, round(K, 4)), (None, None))
        espread = e[n + '_ask'] - e[n + '_bid']
        if side == 'short':
            if a is not None and a > 0 and a >= b:
                p = a
            else:
                if closeR is None:
                    d = max_loss_dollars(e)
                    return dict(pnl=d, pct_risk=d / risk, how='fallback with no bar at R: booked at max loss', fallbacks=1)
                p = intrinsic(r, K, closeR) + espread
                fb += 1
            fees_out += FEE if p > 0 else 0.0
        else:
            if b is not None and a is not None and b > 0 and a >= b:
                p = b
            elif b is not None and a is not None and b == 0 and a > 0:
                p = 0.0
            else:
                if closeR is None:
                    d = max_loss_dollars(e)
                    return dict(pnl=d, pct_risk=d / risk, how='fallback with no bar at R: booked at max loss', fallbacks=1)
                p = max(intrinsic(r, K, closeR) - espread, 0.0)
                fb += 1
            fees_out += FEE if p > 0 else 0.0
        px[n] = p
    xcost = px['cs'] + px['ps'] - px['cl'] - px['pl']
    d = 100.0 * (e['credit'] - xcost) - fees_in - fees_out
    return dict(pnl=d, pct_risk=d / risk, how='quotes' if fb == 0 else 'quotes with fallback', fallbacks=fb, exit_cost=xcost,
                **{'x_' + k: v for k, v in px.items()})


def jdump(obj, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.part')
    tmp.write_text(json.dumps(obj, indent=1, default=str))
    tmp.replace(p)
