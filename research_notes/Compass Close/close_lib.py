"""close_lib.py — Compass Close's one session builder (PREREG_COMPASS_CLOSE.md sections 1-2), files only.

session_row(day, span) reads one session's same-day SPXW quotes (15:45-16:00), the SPX prints and Cboe's official close and
returns every input the primary rule and the books use, in SPX points; books(row) turns it into $ P&L per contract.
span 'new' reads the study's fetch (theta/data_full/chains_close/SPXW), 'prev' the stored full-day chains
(theta/data_full/chains/SPXW, PREVIOUSLY READ). Nothing here reads any input stamped after the minute it decides at,
except SET (and S(16:00) for the settlement-difference flag), and `cut` lets the lookahead check blank them.
"""
from __future__ import annotations

import calendar
import csv
import datetime as dt
import json
import math
from functools import lru_cache
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
NEW = SP / 'theta' / 'data_full' / 'chains_close' / 'SPXW'
PREV = SP / 'theta' / 'data_full' / 'chains' / 'SPXW'
SPX = SP / 'theta' / 'data' / 'index' / 'SPX'
CBOE = REPO / 'data' / 'official_closes' / 'cboe_SPX_History_2026-10-23.csv'
CAL = SP / 'theta' / 'cache' / 'index_tests' / 'calendar_2017_2026.csv'
FOMC = REPO / 'research_notes' / 'Edge search' / 'H7_H8_H9' / 'data' / 'fomc_statements_2012_2026.json'
MACRO = REPO / 'data' / 'macro_events_2022_2027.json'

F = 1.28                       # $ per contract per side (the owner's f)
MULT = 100                     # $ per SPX point per contract
T_STAR = '15:55'
PREV_FROM, PREV_TO = '2022-05-13', '2026-10-09'

# BLS release dates 2017-06 .. 2021-12 (the prereg's appendix); 2022 on from data/macro_events_2022_2027.json
CPI_BLS = """2017-06-14 2017-07-14 2017-08-11 2017-09-14 2017-10-13 2017-11-15 2017-12-13 2018-01-12 2018-02-14 2018-03-13
2018-04-11 2018-05-10 2018-06-12 2018-07-12 2018-08-10 2018-09-13 2018-10-11 2018-11-14 2018-12-12 2019-01-11 2019-02-13
2019-03-12 2019-04-10 2019-05-10 2019-06-12 2019-07-11 2019-08-13 2019-09-12 2019-10-10 2019-11-13 2019-12-11 2020-01-14
2020-02-13 2020-03-11 2020-04-10 2020-05-12 2020-06-10 2020-07-14 2020-08-12 2020-09-11 2020-10-13 2020-11-12 2020-12-10
2021-01-13 2021-02-10 2021-03-10 2021-04-13 2021-05-12 2021-06-10 2021-07-13 2021-08-11 2021-09-14 2021-10-13 2021-11-10
2021-12-10""".split()
NFP_BLS = """2017-06-02 2017-07-07 2017-08-04 2017-09-01 2017-10-06 2017-11-03 2017-12-08 2018-01-05 2018-02-02 2018-03-09
2018-04-06 2018-05-04 2018-06-01 2018-07-06 2018-08-03 2018-09-07 2018-10-05 2018-11-02 2018-12-07 2019-01-04 2019-02-01
2019-03-08 2019-04-05 2019-05-03 2019-06-07 2019-07-05 2019-08-02 2019-09-06 2019-10-04 2019-11-01 2019-12-06 2020-01-10
2020-02-07 2020-03-06 2020-04-03 2020-05-08 2020-06-05 2020-07-02 2020-08-07 2020-09-04 2020-10-02 2020-11-06 2020-12-04
2021-01-08 2021-02-05 2021-03-05 2021-04-02 2021-05-07 2021-06-04 2021-07-02 2021-08-06 2021-09-03 2021-10-08 2021-11-05
2021-12-03""".split()


# ---- calendars and events --------------------------------------------------------------------------------------------

@lru_cache(None)
def calendar_rows() -> dict:
    out = {}
    with open(CAL) as fh:
        for r in csv.DictReader(fh):
            out[r['date']] = r['type']
    return out


def half_day(day: str) -> bool:
    return calendar_rows().get(day) == 'early_close'


def is_session(day: str) -> bool:
    d = dt.date.fromisoformat(day)
    return d.weekday() < 5 and calendar_rows().get(day) != 'full_close'


def month_end(day: str) -> bool:
    """the last NYSE session of its calendar month"""
    d = dt.date.fromisoformat(day)
    last = calendar.monthrange(d.year, d.month)[1]
    for k in range(d.day + 1, last + 1):
        if is_session(dt.date(d.year, d.month, k).isoformat()):
            return False
    return True


@lru_cache(None)
def events() -> dict[str, set]:
    ev: dict[str, set] = {}
    f = json.loads(FOMC.read_text())
    for e in f['scheduled']:
        ev.setdefault(e['date'], set()).add('FOMC')
    for d in CPI_BLS:
        ev.setdefault(d, set()).add('CPI')
    for d in NFP_BLS:
        ev.setdefault(d, set()).add('NFP')
    for e in json.loads(MACRO.read_text()):
        if e['event'] in ('CPI', 'NFP') and e['date'] >= '2022-01-01':
            ev.setdefault(e['date'], set()).add(e['event'])
    return ev


@lru_cache(None)
def cboe() -> dict[str, float]:
    out = {}
    with open(CBOE) as fh:
        for r in csv.DictReader(fh):
            m, d, y = r['DATE'].split('/')
            out[f'{y}-{m}-{d}'] = float(r['SPX'])
    return out


def new_sessions() -> list[dict]:
    with open(HERE / 'sessions_new.csv') as fh:
        return list(csv.DictReader(fh))


def prev_sessions() -> list[str]:
    days = sorted(p.stem for p in PREV.glob('*.parquet'))
    return [d for d in days if PREV_FROM <= d <= PREV_TO and is_session(d) and not half_day(d)]


def g2_row(day: str) -> str:
    if month_end(day):
        return 'EOM'
    return dt.date.fromisoformat(day).strftime('%a')


# ---- one session ------------------------------------------------------------------------------------------------------

def _hm(df: pl.DataFrame) -> pl.Series:
    return df['timestamp'].dt.strftime('%H:%M')


def load_chain(day: str, span: str) -> pl.DataFrame:
    f = (NEW if span == 'new' else PREV) / f'{day}.parquet'
    x = pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    x = x.filter(_hm(x).is_between(pl.lit('15:45'), pl.lit('16:00')))
    x = x.with_columns(_hm(x).alias('hm'), pl.col('right').str.to_uppercase().str.slice(0, 1).alias('r'),
                       pl.col('bid').round(4), pl.col('ask').round(4))
    return x


def listed_strikes(day: str, span: str, chain: pl.DataFrame) -> list[float]:
    if span == 'new':
        m = json.loads((NEW / f'{day}.meta.json').read_text())
        return [float(k) for k in m['listed_strikes']]
    c = set(chain.filter(pl.col('r') == 'C')['strike'].to_list())
    p = set(chain.filter(pl.col('r') == 'P')['strike'].to_list())
    return sorted(c & p)


def load_spx(day: str) -> dict[str, float]:
    x = pl.read_parquet(SPX / f'{day}.parquet')
    return {h: float(v) for h, v in zip(_hm(x).to_list(), x['price'].to_list()) if v is not None and math.isfinite(v)}


def nearest(listed: list[float], s: float) -> float:
    """nearest listed strike; a tie goes to the lower strike"""
    return min(listed, key=lambda k: (abs(k - s), k))


def quote(chain_ix: dict, k: float, r: str, hm: str):
    return chain_ix.get((k, r, hm))


def leg_ok(q, frac: float = 0.5) -> tuple[bool, str]:
    if q is None:
        return False, 'no-quote-row'
    b, a = q
    if b is None or a is None or not (b > 0):
        return False, 'bid<=0'
    if not (a > b):
        return False, 'ask<=bid'
    if (a - b) > frac * (a + b) / 2:
        return False, 'wide'
    return True, ''


def session_row(day: str, span: str, cut: str | None = None, entry_quote_minute: str | None = None) -> dict:
    """every input of the rule and books. cut='15:55' blanks every chain row and SPX print stamped after 15:55 (SET kept)."""
    chain = load_chain(day, span)
    listed = listed_strikes(day, span, chain)
    spx = load_spx(day)
    if cut:
        chain = chain.filter(pl.col('hm') <= cut)
        spx = {h: v for h, v in spx.items() if h <= cut}
    ix = {(k, r, h): (b, a) for k, r, h, b, a in zip(chain['strike'].to_list(), chain['r'].to_list(),
                                                     chain['hm'].to_list(), chain['bid'].to_list(), chain['ask'].to_list())}
    row = {'day': day, 'span': span, 'SET': cboe().get(day), 'S1600': spx.get('16:00'), 'S0931': spx.get('09:31'),
           'ev': sorted(events().get(day, ())), 'g2': g2_row(day), 'year': int(day[:4]), 'n_listed': len(listed)}
    for t in ('15:50', '15:55', '15:58'):
        s = spx.get(t)
        e = {'S': s}
        if s is None or not listed:
            e['K'] = None
        else:
            k = nearest(listed, s)
            i = listed.index(k)
            e['K'] = k
            e['Kup'] = listed[i + 1] if i + 1 < len(listed) else None
            e['Kdn'] = listed[i - 1] if i > 0 else None
            qm = entry_quote_minute or t
            e['C'] = quote(ix, k, 'C', qm)
            e['P'] = quote(ix, k, 'P', qm)
            e['Cup'] = quote(ix, e['Kup'], 'C', qm) if e['Kup'] is not None else None
            e['Pdn'] = quote(ix, e['Kdn'], 'P', qm) if e['Kdn'] is not None else None
            if t == '15:55':                   # the 15:56-ask book: K from 15:55, the asks of the row stamped 15:56
                e['C56'] = quote(ix, k, 'C', '15:56')
                e['P56'] = quote(ix, k, 'P', '15:56')
        row[t] = e
    return row


# ---- the rule and the books ($ per contract, one contract a leg) -------------------------------------------------------

def mid(q):
    return (q[0] + q[1]) / 2


def rh_fee(ask: float) -> float:
    """Robinhood SPXW, one contract one side (docs/FEES_ROBINHOOD.md: $1.0403 under $1.00 of premium, $1.1303 at $1.00 up)"""
    return 1.0403 if ask < 1.00 else 1.1303


def assert_units(prem: float, f: float = F) -> None:
    assert 0 < prem < 200, f'premium {prem} is not in SPX points per share'
    assert f in (F, 0.0) or 1.0 < f < 1.2, f'fee {f} not $ per contract per side'


def straddle(e: dict, SET: float, cq='C', pq='P', exit_fee=True, fee=None) -> dict:
    """the primary's arithmetic on legs e[cq], e[pq] at strike e['K']"""
    C, P = e.get(cq), e.get(pq)
    okc, rc = leg_ok(C)
    okp, rp = leg_ok(P)
    if not (okc and okp):
        return {'trade': False, 'why': rc or rp}
    K = e['K']
    str_ask = C[1] + P[1]
    assert_units(str_ask)
    fe = (rh_fee(C[1]) + rh_fee(P[1])) if fee == 'rh' else 2 * F
    fx = 0.0 if (fee == 'rh' or not exit_fee) else 2 * F
    entry = MULT * str_ask + fe
    payout = MULT * abs(SET - K) - fx
    pnl = payout - entry
    assert abs(pnl - (MULT * (abs(SET - K) - str_ask) - fe - fx)) < 1e-6
    return {'trade': True, 'K': K, 'entry': entry, 'payout': payout, 'pnl': pnl, 'ret': pnl / entry,
            'move': abs(SET - K), 'str_ask': str_ask, 'str_mid': mid(C) + mid(P),
            'ok10': leg_ok(C, 0.10)[0] and leg_ok(P, 0.10)[0]}


def single(K: float, q, right: str, SET: float) -> dict:
    ok, why = leg_ok(q)
    if not ok:
        return {'trade': False, 'why': why}
    assert_units(q[1])
    entry = MULT * q[1] + F
    intr = max(SET - K, 0.0) if right == 'C' else max(K - SET, 0.0)
    payout = MULT * intr - F
    pnl = payout - entry
    return {'trade': True, 'K': K, 'entry': entry, 'payout': payout, 'pnl': pnl, 'ret': pnl / entry}


def strangle(e: dict, SET: float) -> dict:
    C, P = e.get('Cup'), e.get('Pdn')
    okc, rc = leg_ok(C)
    okp, rp = leg_ok(P)
    if e.get('Kup') is None or e.get('Kdn') is None or not (okc and okp):
        return {'trade': False, 'why': rc or rp or 'no-strike'}
    prem = C[1] + P[1]
    assert_units(prem)
    intr = max(SET - e['Kup'], 0.0) + max(e['Kdn'] - SET, 0.0)
    entry = MULT * prem + 2 * F
    payout = MULT * intr - 2 * F
    return {'trade': True, 'K': e['K'], 'Kup': e['Kup'], 'Kdn': e['Kdn'], 'entry': entry, 'payout': payout,
            'pnl': payout - entry, 'ret': (payout - entry) / entry, 'move': intr, 'str_ask': prem}


def books(row: dict) -> dict:
    """the primary and every reported book; a session with no SET or no S(15:55) has no trade anywhere"""
    SET = row['SET']
    e = row['15:55']
    out = {}
    if SET is None:
        return {'primary': {'trade': False, 'why': 'no-set'}}
    if e.get('K') is None:
        return {'primary': {'trade': False, 'why': 'no-spx-print'}}
    out['primary'] = straddle(e, SET)
    out['call'] = single(e['K'], e.get('C'), 'C', SET)
    out['put'] = single(e['K'], e.get('P'), 'P', SET)
    if row.get('S0931') is None:
        out['move_side'] = {'trade': False, 'why': 'no-0931'}
    else:
        side = 'C' if e['S'] > row['S0931'] else 'P'
        out['move_side'] = single(e['K'], e.get(side), side, SET) | {'side': side}
    C, P = e.get('C'), e.get('P')
    wc = (C[1] - C[0]) / mid(C) if C and C[0] is not None and C[1] is not None and mid(C) > 0 else math.inf
    wp = (P[1] - P[0]) / mid(P) if P and P[0] is not None and P[1] is not None and mid(P) > 0 else math.inf
    side = 'C' if wc <= wp else 'P'
    out['narrow'] = single(e['K'], e.get(side), side, SET) | {'side': side}
    for t, name in (('15:50', 'e1550'), ('15:58', 'e1558')):
        out[name] = straddle(row[t], SET) if row[t].get('K') is not None else {'trade': False, 'why': 'no-spx-print'}
    out['ask1556'] = straddle(e, SET, 'C56', 'P56')
    out['no_exit_fee'] = straddle(e, SET, exit_fee=False)
    out['strangle'] = strangle(e, SET)
    out['robinhood'] = straddle(e, SET, fee='rh')
    return out
