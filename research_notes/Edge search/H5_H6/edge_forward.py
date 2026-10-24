"""
edge_forward.py — the forward tests of the edge-search queue's H5 and H6 (PREREG_H5.md, PREREG_H6.md, committed alone in
e114e30 before any forward session of either was computed), run by step 8 of scripts/daily_forward.py on every complete
forward session. Nothing here is a historical read: H5 starts at 2026-10-23, H6's first entry is November 2026's first
full session.

H5 (every full session from 2026-10-23): at 15:30 sell 10 SPY same-day at-the-money straddles at the bids and buy 1 SPXW
same-day at-the-money straddle at the asks (each strike by paper_tracker Chain.nearest on its own spot: SPY the 15:29
bar's close, SPX the 15:30 print), close all four legs at 15:58 (SPY at the asks, SPXW at the bids); fees $0.68748 a SPY
contract each way, $1.18748 / $1.27748 an SPXW contract by the leg's fill. Read from the daily job's own layout (the
same-day chains, SPY's bars, SPX's prints) — nothing is fetched for H5.

H6 (each month's first full session from November 2026): SPY and QQQ each sell the put nearest |Δ| 0.30 and buy the put
nearest 0.15 (paper_tracker.nearest_delta, bsm_abs_delta at r = q = 0 on the end-of-day mids and the official close) on
the latest expiration 30–45 days out, short at the bid, long at the ask; bought back on the end-of-day report of the
first full session on or after expiration − 21 days (short at the ask, long at the bid); 4 × $0.68748. The job fetches
no end-of-day option chains, so H6 asks its source for them (`eod_fetch(sym, day, expiration | None)`: every expiration
on an entry session, the one expiration on an exit session — at most four calls a month), keeps each answer as answered
(<store>/<SYM>/<D>__<ALL|E>.ndjson.gz) and never asks for one twice.

Idempotent: a session, an entry or a closed spread already written is never recomputed or written again (one row a key,
append-only CSVs). Loud: a missing file, minute, spot, official close or answer raises EdgeDataError — that session,
entry or exit writes nothing and the step reports `<day> <step>: <why>`; nothing is substituted. The verdicts: none
before N (H5 1,326 counted sessions; H6 449 counted months); at N, on the first N only, mean > 0 with the block
bootstrap's 95 % lower end > 0 ⇒ PASS, else FAIL — written once to verdicts.json and never revised.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
for _p in (REPO / 'scripts', REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import paper_backtest as B  # noqa: E402
import paper_tracker as T  # noqa: E402
import audit_lib as AL  # noqa: E402
import fees_robinhood as FR  # noqa: E402  (the default cost model from 2026-10-24 — beside the frozen tests, never in them)

VERSION = 'edge-forward-2026-10-23.1'
PREREG_COMMIT = 'e114e30'

# ---- the rules (PREREG_H5.md, PREREG_H6.md) ---------------------------------------------------------------------------------------------
H5_START = '2026-10-23'
H6_START_MONTH = '2026-11'
N_RULE = {'H5': 1326, 'H6': 449}          # H5 counted sessions; H6 counted months (898 spreads)
BLOCK = {'H5': 20, 'H6': 3}
NO_CI_UNDER = {'H5': 60, 'H6': 12}
FEE_ETF = 0.68748
FEE_SPXW_LT1, FEE_SPXW_GE1 = 1.18748, 1.27748
H5_ENTRY_J, H5_EXIT_J = B.MINUTE_OF('15:30'), B.MINUTE_OF('15:58')      # 360, 388
H5_SPY_N, H5_SPXW_N = 10, 1
H6_NAMES = ('SPY', 'QQQ')
H6_SHORT_D, H6_LONG_D = 0.30, 0.15
H6_DTE_MIN, H6_DTE_MAX = 30, 45
H6_EXIT_BEFORE = 21

FWD = HERE / 'forward'
H5_CSV = FWD / 'h5_sessions.csv'
H6_ENTRIES = FWD / 'h6_entries.csv'
H6_TRADES = FWD / 'h6_trades.csv'
REPORT_PATH = FWD / 'EDGE_FORWARD_REPORT.md'
VERDICTS_PATH = FWD / 'verdicts.json'
EOD_STORE = 'edge_forward/eod'            # under the job's Parquet root

H5_COLS = ('day', 'traded', 'reason', 'S', 'N', 'pnl', 'gross', 'fees', 'pnl_mid', 'spy_spot', 'spx_spot', 'k_spy', 'k_spxw',
           'spy_c_bid', 'spy_c_ask', 'spy_p_bid', 'spy_p_ask', 'spxw_c_bid', 'spxw_c_ask', 'spxw_p_bid', 'spxw_p_ask',
           'spy_c_bid_x', 'spy_c_ask_x', 'spy_p_bid_x', 'spy_p_ask_x', 'spxw_c_bid_x', 'spxw_c_ask_x', 'spxw_p_bid_x', 'spxw_p_ask_x',
           'spy_c_size', 'spy_p_size', 'spxw_c_size', 'spxw_p_size', 'exit_flags', 'version', 'written_at')
H6_ENTRY_COLS = ('month', 'name', 'entry_day', 'status', 'reason', 'spot', 'expiry', 'dte', 'k_short', 'k_long', 'd_short', 'd_long',
                 'short_bid', 'short_ask', 'long_bid', 'long_ask', 'credit', 'width', 'exit_day', 'version', 'written_at')
H6_TRADE_COLS = ('month', 'name', 'entry_day', 'exit_day', 'expiry', 'k_short', 'k_long', 'credit', 'short_bid_x', 'short_ask_x',
                 'long_bid_x', 'long_ask_x', 'debit', 'exit_flags', 'gross', 'fees', 'pnl', 'risk', 'spot_exit',
                 'short_below_intrinsic', 'version', 'written_at')


class EdgeDataError(Exception):
    def __init__(self, day: str, step: str, why: str):
        super().__init__(f'{day} {step}: {why}')
        self.day, self.step, self.why = day, step, why


class EdgeFetchError(Exception):
    """the source could not answer (raised by an eod_fetch); becomes an EdgeDataError of the session asking"""


def now_z() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def spxw_fee(price: float) -> float:
    return FEE_SPXW_LT1 if price < 1.0 else FEE_SPXW_GE1


# ---- the append-only files ---------------------------------------------------------------------------------------------------------------

def read_rows(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def append_rows(path: Path, cols: tuple, rows: list[dict], key: tuple) -> list[tuple]:
    """append the rows whose key is not in the file yet; a file whose header is not `cols`, or that holds a key twice, is
    refused (never rewritten). → the keys added"""
    have = read_rows(path)
    if have and tuple(have[0].keys()) != tuple(cols):
        raise RuntimeError(f'{path}: its header is not this version\'s ({list(have[0].keys())[:4]}…)')
    seen = [tuple(r[k] for k in key) for r in have]
    if len(seen) != len(set(seen)):
        raise RuntimeError(f'{path}: a key written twice')
    seen = set(seen)
    new = []
    for r in rows:
        k = tuple(str(r[c]) for c in key)
        if k in seen:
            continue
        seen.add(k)
        new.append(r)
    if not new:
        return []
    exists = Path(path).exists()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if not exists:
            w.writeheader()
        for r in new:
            w.writerow({c: _cell(r.get(c)) for c in cols})
    return [tuple(str(r[c]) for c in key) for r in new]


def _cell(v):
    if v is None:
        return ''
    if isinstance(v, float):
        return repr(v)
    return v


def _f(v) -> float | None:
    return None if v in (None, '') else float(v)


# ---- H5 ----------------------------------------------------------------------------------------------------------------------------------

def _chain(src: B.ParquetSource, name: str, day: str, j: int, step: str) -> T.Chain:
    rows = B.chain_rows(src, name, day, j)
    root = B.CHAIN_ROOT.get(name, name)
    if not rows:
        raise EdgeDataError(day, step, f'no {root} chain rows stamped minute {j} ({"file missing" if rows is None else "the minute is empty"})')
    return T.Chain(rows, day, root=root)


def h5_session(day: str, layout: Path) -> dict:
    """the H5 row of one full session from the job's layout (PREREG_H5.md section 2); EdgeDataError when an input is missing"""
    if not T.is_tracked_day(day):
        raise EdgeDataError(day, 'h5-calendar', 'not a full session')
    src = B.ParquetSource(Path(layout), keep=2)
    need = [src.chain_file('SPY', day), src.chain_file('SPXW', day), src.under_file('SPY', day), src.index_file('SPX', day)]
    miss = [str(f.relative_to(Path(layout))) for f in need if not f.exists() or src.refused(f, day)]
    if miss:
        raise EdgeDataError(day, 'h5-inputs', f'not in the layout: {", ".join(miss)}')
    bars = src.bars('SPY', day) or {'j': [], 'c': []}
    bc = dict(zip(bars['j'], bars['c']))
    pr = dict(src.prints('SPX', day) or [])
    s_y, s_x = bc.get(H5_ENTRY_J - 1), pr.get(H5_ENTRY_J)
    if s_y is None or s_x is None:
        raise EdgeDataError(day, 'h5-spot', ('no SPY bar close stamped 15:29' if s_y is None else 'no SPX print stamped 15:30'))
    y30 = _chain(src, 'SPY', day, H5_ENTRY_J, 'h5-chain')
    x30 = _chain(src, 'SPX', day, H5_ENTRY_J, 'h5-chain')
    y58 = _chain(src, 'SPY', day, H5_EXIT_J, 'h5-chain')
    x58 = _chain(src, 'SPX', day, H5_EXIT_J, 'h5-chain')
    row = {c: None for c in H5_COLS}
    row.update(day=day, spy_spot=float(s_y), spx_spot=float(s_x), version=VERSION, written_at=now_z(), traded=0, S=0.0, N=0)
    k_y, k_x = y30.nearest(s_y), x30.nearest(s_x)
    row.update(k_spy=k_y, k_spxw=k_x)
    if k_y is None or k_x is None:
        row['reason'] = 'no SPY strike with both sides quoted at 15:30' if k_y is None else 'no SPXW strike with both sides quoted at 15:30'
        return row
    yc, yp, xc, xp = y30.calls[k_y], y30.puts[k_y], x30.calls[k_x], x30.puts[k_x]
    row.update(spy_c_bid=yc.bid, spy_c_ask=yc.ask, spy_p_bid=yp.bid, spy_p_ask=yp.ask, spxw_c_bid=xc.bid, spxw_c_ask=xc.ask,
               spxw_p_bid=xp.bid, spxw_p_ask=xp.ask, spy_c_size=_sz(yc.bid_size), spy_p_size=_sz(yp.bid_size),
               spxw_c_size=_sz(xc.ask_size), spxw_p_size=_sz(xp.ask_size))
    if yc.bid <= 0 or yp.bid <= 0:
        row['reason'] = 'a SPY bid of 0 at 15:30 (nothing to sell)'
        return row
    flags = []
    s_y58 = s_x58 = None

    def exit_spot(which):
        nonlocal s_y58, s_x58
        if which == 'SPY':
            s_y58 = bc.get(H5_EXIT_J - 1)
            if s_y58 is None:
                raise EdgeDataError(day, 'h5-spot', 'a SPY exit quote is missing and no SPY bar close stamped 15:57 values it')
            return s_y58
        s_x58 = pr.get(H5_EXIT_J)
        if s_x58 is None:
            raise EdgeDataError(day, 'h5-spot', 'an SPXW exit quote is missing and no SPX print stamped 15:58 values it')
        return s_x58

    def buy_back(ch, k, right, entry_q, label):        # a short leg: its 15:58 ask, else intrinsic + its entry spread
        q = ch.quote(right, k)
        if q is not None and q.ask > 0:
            return q.ask, q
        flags.append(f'{label}: no 15:58 ask, valued at intrinsic + entry spread')
        return T.intrinsic(exit_spot('SPY'), k, right) + (entry_q.ask - entry_q.bid), q

    def sell_out(ch, k, right, entry_q, label):        # a long leg: its 15:58 bid, else max(0, intrinsic − its entry spread)
        q = ch.quote(right, k)
        if q is not None:
            return q.bid, q
        flags.append(f'{label}: no 15:58 quote, valued at intrinsic − entry spread')
        return max(0.0, T.intrinsic(exit_spot('SPX'), k, right) - (entry_q.ask - entry_q.bid)), q

    a_yc, q_yc = buy_back(y58, k_y, 'C', yc, 'SPY call')
    a_yp, q_yp = buy_back(y58, k_y, 'P', yp, 'SPY put')
    b_xc, q_xc = sell_out(x58, k_x, 'C', xc, 'SPXW call')
    b_xp, q_xp = sell_out(x58, k_x, 'P', xp, 'SPXW put')
    for nm, q in (('spy_c', q_yc), ('spy_p', q_yp), ('spxw_c', q_xc), ('spxw_p', q_xp)):
        if q is not None:
            row[f'{nm}_bid_x'], row[f'{nm}_ask_x'] = q.bid, q.ask
    gross = 100.0 * (H5_SPY_N * (yc.bid + yp.bid - a_yc - a_yp) - H5_SPXW_N * (xc.ask + xp.ask - b_xc - b_xp))
    fees = 2 * 2 * H5_SPY_N * FEE_ETF + H5_SPXW_N * (spxw_fee(xc.ask) + spxw_fee(xp.ask) + spxw_fee(b_xc) + spxw_fee(b_xp))
    pnl = gross - fees
    mid = None
    if None not in (q_yc, q_yp, q_xc, q_xp):
        mid = 100.0 * (H5_SPY_N * (yc.mid + yp.mid - q_yc.mid - q_yp.mid) - H5_SPXW_N * (xc.mid + xp.mid - q_xc.mid - q_xp.mid))
    row.update(traded=1, reason='', S=pnl, N=1, pnl=pnl, gross=gross, fees=fees, pnl_mid=mid, exit_flags='; '.join(flags))
    return row


def _sz(v):
    try:
        return None if v is None else int(v)
    except (TypeError, ValueError):
        return None


# ---- H6: the calendar --------------------------------------------------------------------------------------------------------------------

def first_full_session(month: str) -> str:
    """the first full NYSE session of 'YYYY-MM' (the recorder's calendar, half days skipped)"""
    d = dt.date.fromisoformat(month + '-01')
    while not T.is_tracked_day(d.isoformat()):
        d += dt.timedelta(days=1)
    return d.isoformat()


def is_entry_day(day: str) -> bool:
    return day[:7] >= H6_START_MONTH and day == first_full_session(day[:7])


def exit_day_for(expiry: str) -> str:
    """the first full session on or after expiry − 21 calendar days"""
    d = dt.date.fromisoformat(expiry) - dt.timedelta(days=H6_EXIT_BEFORE)
    while not T.is_tracked_day(d.isoformat()):
        d += dt.timedelta(days=1)
    return d.isoformat()


# ---- H6: the end-of-day answers ----------------------------------------------------------------------------------------------------------

def _iso(v) -> str | None:
    if v is None:
        return None
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()[:10]
    s = str(v).strip()
    if len(s) >= 8 and s[:8].isdigit():
        return f'{s[:4]}-{s[4:6]}-{s[6:8]}'
    return s[:10] if len(s) >= 10 and s[4] == '-' else None


def shape_eod(rows: list[dict], day: str, sym: str, expiry: str | None) -> tuple[pl.DataFrame, list]:
    """an end-of-day answer (the terminal's NDJSON rows or the SDK's rows alike) → expiration, strike, right C/P, bid, ask —
    a 0/0 quote is no quote (null); nothing filled in. The problems: a field missing, a row of another date, root or
    expiration than asked, a right neither call nor put, a number that does not parse."""
    probs = []
    if not rows:
        return pl.DataFrame(schema={'expiration': pl.Utf8, 'strike': pl.Float64, 'right': pl.Utf8, 'bid': pl.Float64, 'ask': pl.Float64}), ['no rows']
    miss = [k for k in ('expiration', 'strike', 'right', 'bid', 'ask') if any(k not in r for r in rows)]
    if miss:
        probs.append(f'fields missing: {", ".join(miss)}')
        return pl.DataFrame(), probs
    dfield = next((k for k in ('date', 'created', 'last_trade', 'timestamp') if k in rows[0]), None)
    out = {'expiration': [], 'strike': [], 'right': [], 'bid': [], 'ask': []}
    bad = other_day = other_root = 0
    for r in rows:
        if dfield is not None and _iso(r.get(dfield)) not in (None, day):
            other_day += 1
        if r.get('symbol') is not None and str(r['symbol']).upper() != sym:
            other_root += 1
        x = str(r['right']).strip().upper()
        right = 'C' if x in ('C', 'CALL') else 'P' if x in ('P', 'PUT') else None
        try:
            k, b, a = float(r['strike']), float(r['bid']), float(r['ask'])
        except (TypeError, ValueError):
            bad += 1
            continue
        if right is None or not all(math.isfinite(v) for v in (k, b, a)):
            bad += 1
            continue
        if b == 0 and a == 0:
            b = a = None
        out['expiration'].append(_iso(r['expiration']))
        out['strike'].append(k)
        out['right'].append(right)
        out['bid'].append(b)
        out['ask'].append(a)
    if bad:
        probs.append(f'{bad} rows with a right, strike or price that does not parse')
    if other_day:
        probs.append(f'{other_day} rows of a date other than {day}')
    if other_root:
        probs.append(f'{other_root} rows of a root other than {sym}')
    df = pl.DataFrame(out, schema={'expiration': pl.Utf8, 'strike': pl.Float64, 'right': pl.Utf8, 'bid': pl.Float64, 'ask': pl.Float64})
    if df['expiration'].null_count():
        probs.append('an expiration that does not parse')
    if expiry is not None and set(df['expiration'].drop_nulls().unique().to_list()) - {expiry}:
        probs.append(f'expirations other than {expiry}')
    if df.filter(pl.col('expiration') < day).height:
        probs.append(f'expirations before {day}')
    if df.height != df.select('expiration', 'strike', 'right').n_unique():
        probs.append('a contract twice')
    return df, probs


def eod_file(store: Path, sym: str, day: str, expiry: str | None) -> Path:
    return Path(store) / sym / f'{day}__{"ALL" if expiry is None else expiry}.ndjson.gz'


def get_eod(store: Path, sym: str, day: str, expiry: str | None, eod_fetch, counter: dict, step: str) -> pl.DataFrame:
    """the answer kept on disk, else asked ONCE (eod_fetch) and kept as answered — only when it shapes without a problem"""
    f = eod_file(store, sym, day, expiry)
    if f.exists():
        with gzip.open(f, 'rt', encoding='utf-8') as g:
            rows = [json.loads(line) for line in g if line.strip()]
    else:
        if eod_fetch is None:
            raise EdgeDataError(day, step, f'{sym} end-of-day options ({"every expiration" if expiry is None else expiry}) are not on disk and no source was given')
        try:
            counter['calls'] = counter.get('calls', 0) + 1
            rows = list(eod_fetch(sym, day, expiry))
        except EdgeFetchError as e:
            raise EdgeDataError(day, step, f'{sym} end-of-day options ({"every expiration" if expiry is None else expiry}): {e}') from None
        rows = [{k: (v.isoformat() if isinstance(v, (dt.date, dt.datetime)) else v) for k, v in r.items()} for r in rows]
    df, probs = shape_eod(rows, day, sym, expiry)
    if probs:
        raise EdgeDataError(day, step, f'{sym} end-of-day answer refused: {"; ".join(probs)}')
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        tmp = f.with_name(f.name + '.part')
        with gzip.GzipFile(tmp, 'wb', mtime=0) as g:
            g.write(''.join(json.dumps(r, separators=(',', ':'), default=str) + '\n' for r in rows).encode('utf-8'))
        os.replace(tmp, f)
    return df


def chain_of(df: pl.DataFrame, sym: str, expiry: str) -> T.Chain:
    s = df.filter(pl.col('expiration') == expiry)
    rows = [{'option_symbol': B.occ(sym, expiry, r, k), 'nbbo_bid': b, 'nbbo_ask': a}
            for k, r, b, a in zip(s['strike'], s['right'], s['bid'], s['ask'])]
    return T.Chain(rows, expiry, root=sym)


# ---- H6: entry and exit ------------------------------------------------------------------------------------------------------------------

def h6_entry(name: str, day: str, df: pl.DataFrame, spot: float) -> dict:
    """the entry row of one name on its month's first full session (PREREG_H6.md section 2)"""
    row = {c: None for c in H6_ENTRY_COLS}
    row.update(month=day[:7], name=name, entry_day=day, spot=float(spot), version=VERSION, written_at=now_z(), status='no-trade')
    d0 = dt.date.fromisoformat(day)
    exps = sorted(e for e in set(df['expiration'].to_list()) if H6_DTE_MIN <= (dt.date.fromisoformat(e) - d0).days <= H6_DTE_MAX)
    if not exps:
        row['reason'] = f'no listed expiration {H6_DTE_MIN}–{H6_DTE_MAX} days out'
        return row
    e = exps[-1]
    row.update(expiry=e, dte=(dt.date.fromisoformat(e) - d0).days, exit_day=exit_day_for(e))
    ch = chain_of(df, name, e)
    ks, ds = T.nearest_delta(ch, spot, 'put', H6_SHORT_D)
    kl, dl = T.nearest_delta(ch, spot, 'put', H6_LONG_D)
    row.update(k_short=ks, k_long=kl, d_short=ds, d_long=dl)
    if ks is None or kl is None:
        row['reason'] = 'no out-of-the-money put with a delta'
        return row
    qs, ql = ch.puts[ks], ch.puts[kl]
    row.update(short_bid=qs.bid, short_ask=qs.ask, long_bid=ql.bid, long_ask=ql.ask, width=ks - kl)
    if kl >= ks:
        row['reason'] = f'the 0.15 put ({kl:g}) is not below the 0.30 put ({ks:g})'
        return row
    credit = qs.bid - ql.ask
    row['credit'] = credit
    if qs.bid <= 0 or credit <= 0:
        row['reason'] = 'no credit (short bid 0 or the long ask at or above it)'
        return row
    row.update(status='open', reason='')
    return row


def h6_exit(entry: dict, day: str, df: pl.DataFrame, spot: float) -> dict:
    """the closed spread on its exit session (PREREG_H6.md section 2)"""
    name, e = entry['name'], entry['expiry']
    ks, kl, credit = float(entry['k_short']), float(entry['k_long']), float(entry['credit'])
    ch = chain_of(df, name, e)
    flags = []
    qs, ql = ch.quote('P', ks), ch.quote('P', kl)
    if qs is not None and qs.ask > 0:
        a_s = qs.ask
    else:
        a_s = T.intrinsic(spot, ks, 'P') + (float(entry['short_ask']) - float(entry['short_bid']))
        flags.append('short put: no exit ask, valued at intrinsic + entry spread')
    if ql is not None:
        b_l = ql.bid
    else:
        b_l = max(0.0, T.intrinsic(spot, kl, 'P') - (float(entry['long_ask']) - float(entry['long_bid'])))
        flags.append('long put: no exit quote, valued at intrinsic − entry spread')
    debit = a_s - b_l
    gross = 100.0 * (credit - debit)
    fees = 4 * FEE_ETF
    row = {c: None for c in H6_TRADE_COLS}
    row.update(month=entry['month'], name=name, entry_day=entry['entry_day'], exit_day=day, expiry=e, k_short=ks, k_long=kl, credit=credit,
               short_bid_x=None if qs is None else qs.bid, short_ask_x=None if qs is None else qs.ask,
               long_bid_x=None if ql is None else ql.bid, long_ask_x=None if ql is None else ql.ask, debit=debit,
               exit_flags='; '.join(flags), gross=gross, fees=fees, pnl=gross - fees, risk=100.0 * (ks - kl - credit), spot_exit=float(spot),
               short_below_intrinsic=int(qs is not None and qs.bid < T.intrinsic(spot, ks, 'P') - 1e-9),
               version=VERSION, written_at=now_z())
    return row


# ---- the statistic and the verdicts ------------------------------------------------------------------------------------------------------

def evaluate(S: list, N: list, test: str, n_rule: int | None = None) -> dict:
    """Δ = Σ S ÷ Σ N on the first n_rule units once they exist (else on all, labelled no verdict); the moving-block
    bootstrap's 95 % percentile interval (audit_lib.block_draws, its fixed seed); PASS / FAIL only at n_rule"""
    n_rule = N_RULE[test] if n_rule is None else n_rule
    n = len(S)
    k = min(n, n_rule)
    s, m = np.asarray(S[:k], float), np.asarray(N[:k], float)
    out = dict(test=test, N=n_rule, counted=n, verdict='no verdict', delta=None, ci=None, trades=int(m.sum()))
    if k and m.sum() > 0:
        out['delta'] = float(s.sum() / m.sum())
        if k >= NO_CI_UNDER[test]:
            idx = AL.block_draws(k, BLOCK[test])
            with np.errstate(divide='ignore', invalid='ignore'):
                out['ci'] = list(AL.pct_ci(s[idx].sum(1) / m[idx].sum(1)))
    if n >= n_rule:
        ok = out['delta'] is not None and out['delta'] > 0 and out['ci'] is not None and math.isfinite(out['ci'][0]) and out['ci'][0] > 0
        out['verdict'] = 'PASS' if ok else 'FAIL'
    return out


def h5_series(rows: list[dict]) -> tuple[list, list, list]:
    rs = sorted(rows, key=lambda r: r['day'])
    return [r['day'] for r in rs], [float(r['S']) for r in rs], [int(r['N']) for r in rs]


def h6_months(entries: list[dict], trades: list[dict]) -> list[dict]:
    """the counted months: the calendar-order prefix of months whose both names are final (a closed spread or a no-trade
    entry). → [{'month', 'S', 'N', 'by_name': {name: pnl}}]"""
    tr = {(t['month'], t['name']): t for t in trades}
    months = sorted({e['month'] for e in entries})
    out = []
    for mo in months:
        es = {e['name']: e for e in entries if e['month'] == mo}
        if set(es) != set(H6_NAMES):
            break
        rec = {'month': mo, 'S': 0.0, 'N': 0, 'by_name': {}}
        final = True
        for nm in H6_NAMES:
            e = es[nm]
            if e['status'] == 'no-trade':
                continue
            t = tr.get((mo, nm))
            if t is None:
                final = False
                break
            rec['S'] += float(t['pnl'])
            rec['N'] += 1
            rec['by_name'][nm] = float(t['pnl'])
        if not final:
            break
        out.append(rec)
    return out


def record_verdict(path: Path, ev: dict, through: str) -> dict:
    """written once: a verdict already there is returned unchanged, never revised"""
    have = json.loads(Path(path).read_text()) if Path(path).exists() else {}
    if ev['test'] in have:
        return have[ev['test']]
    if ev['verdict'] == 'no verdict':
        return ev
    have[ev['test']] = {**ev, 'through': through, 'written_at': now_z(), 'version': VERSION, 'prereg': PREREG_COMMIT}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(path).with_suffix('.part')
    tmp.write_text(json.dumps(have, indent=1))
    tmp.replace(path)
    return have[ev['test']]


def money(x):
    return '—' if x is None else f'{x:+,.2f}'


def _fl(x):
    return None if x in ('', None) else float(x)


def h5_rh_fees(row: dict) -> float:
    """Robinhood's fees on one traded H5 package (docs/FEES_ROBINHOOD.md), on the row's own fills: 10 SPY calls and puts sold
    at the 15:30 bids and bought back at the 15:58 asks (the entry ask where the exit ask was not quoted), the SPXW call and
    put bought at the asks and sold at the 15:58 bids (an unquoted bid taken at the $1.00 tier; a $0 bid not sold)"""
    n = H5_SPY_N
    f = FR.option_fee('SPY', _fl(row['spy_c_bid']), n, 'sell') + FR.option_fee('SPY', _fl(row['spy_p_bid']), n, 'sell')
    for leg in ('spy_c', 'spy_p'):
        a = _fl(row[f'{leg}_ask_x'])
        f += FR.option_fee('SPY', a if a is not None else _fl(row[f'{leg}_ask']), n, 'buy')
    for leg in ('spxw_c', 'spxw_p'):
        f += FR.option_fee('SPXW', _fl(row[f'{leg}_ask']), H5_SPXW_N, 'buy')
        b = _fl(row[f'{leg}_bid_x'])
        b = 1.0 if b is None else b
        if b > 0:
            f += FR.option_fee('SPXW', b, H5_SPXW_N, 'sell')
    return f


def h6_rh_fees(trade: dict, entry: dict | None) -> float:
    """Robinhood on one H6 spread: the short put sold at its entry bid and bought back at its exit ask, the long bought at its
    entry ask and sold at its exit bid (a $0 bid not sold)"""
    nm = trade['name']
    sb = _fl((entry or {}).get('short_bid')) or 0.0
    la = _fl((entry or {}).get('long_ask')) or 0.0
    sa, lb = _fl(trade['short_ask_x']) or 0.0, _fl(trade['long_bid_x']) or 0.0
    return (FR.option_fee(nm, sb, 1, 'sell') + FR.option_fee(nm, la, 1, 'buy') + FR.option_fee(nm, sa, 1, 'buy')
            + (FR.option_fee(nm, lb, 1, 'sell') if lb > 0 else 0.0))


def rh_lines(h5: list, ents: list, trs: list) -> list:
    """the forward rows at Robinhood's fees, beside the pre-registered ones — descriptive; N and the pass rules stay frozen"""
    t5 = [x for x in h5 if x['traded'] == '1']
    pre5 = [float(x['pnl']) for x in t5]
    rh5 = [float(x['pnl']) + float(x['fees']) - h5_rh_fees(x) for x in t5]
    em = {(x['month'], x['name']): x for x in ents}
    pre6 = [float(t['pnl']) for t in trs]
    rh6 = [float(t['pnl']) + float(t['fees']) - h6_rh_fees(t, em.get((t['month'], t['name']))) for t in trs]
    avg = lambda v: (sum(v) / len(v)) if v else None   # noqa: E731
    return ['## At Robinhood fees (descriptive)', '',
            'The same forward trades on the same fills, re-priced at Robinhood\'s fees (the research\'s default cost model from '
            f'2026-10-24, `docs/FEES_ROBINHOOD.md`, `{FR.VERSION}`): the study\'s $0.68748 a SPY/QQQ contract a side and SPXW\'s '
            '$1.18748 / $1.27748 added back; Robinhood\'s $0.0403 a contract a side (plus TAF and SEC on an ETF sale) and SPXW '
            '$1.0403 / $1.1303 charged. **The pass rules and N stay on the pre-registered fees (PREREG_H5.md, PREREG_H6.md, '
            'frozen); the verdict column above is the only verdict.**', '',
            '| test | trades | mean $ a trade at Robinhood fees | pre-registered fees |', '|---|---|---|---|',
            f'| H5 | {len(t5):,} | {money(avg(rh5))} | {money(avg(pre5))} |',
            f'| H6 | {len(trs):,} | {money(avg(rh6))} | {money(avg(pre6))} |', '']


def write_report(paths: dict) -> str:
    h5 = read_rows(paths['h5'])
    ents, trs = read_rows(paths['h6_entries']), read_rows(paths['h6_trades'])
    days, S, N = h5_series(h5)
    e5 = evaluate(S, N, 'H5')
    if e5['verdict'] != 'no verdict':                 # the verdict on the first N, written once; the count shown is today's
        e5 = {**record_verdict(paths['verdicts'], e5, days[N_RULE['H5'] - 1]), 'counted': e5['counted']}
    ms = h6_months(ents, trs)
    e6 = evaluate([m['S'] for m in ms], [m['N'] for m in ms], 'H6')
    if e6['verdict'] != 'no verdict':
        e6 = {**record_verdict(paths['verdicts'], e6, ms[N_RULE['H6'] - 1]['month']), 'counted': e6['counted']}

    def ci(e):
        return '—' if not e.get('ci') else f'[{money(e["ci"][0])}, {money(e["ci"][1])}]'

    def lab(e):
        return f'**{e["verdict"]}**' if e['verdict'] != 'no verdict' else '**no verdict** (interim figures only)'
    per_name = {}
    for nm in H6_NAMES:
        v = [float(t['pnl']) for t in trs if t['name'] == nm]
        per_name[nm] = (len(v), (sum(v) / len(v)) if v else None)
    open_ = [e for e in ents if e['status'] == 'open' and (e['month'], e['name']) not in {(t['month'], t['name']) for t in trs}]
    traded5 = [r for r in h5 if r['traded'] == '1']
    mids = [float(r['pnl_mid']) for r in traded5 if r['pnl_mid'] not in ('', None)]
    L = ['# Edge search H5 and H6: the forward tests', '',
         f'The rules: `PREREG_H5.md` and `PREREG_H6.md` (commit `{PREREG_COMMIT}`, committed alone before any forward session of '
         f'either). Written by `edge_forward.py` ({VERSION}) from the append-only files in this folder. Dollars a trade after '
         'every spread and fee. **No verdict before N**; at N the verdict uses exactly the first N and is written once '
         '(`verdicts.json`).', '',
         '| test | counted / N | trades | mean $ a trade | 95 % block interval | verdict |', '|---|---|---|---|---|---|',
         f'| H5 SPY − SPXW straddle package, 15:30 → 15:58 (sessions; block 20) | {e5["counted"]:,} / {e5["N"]:,} | {e5["trades"]:,} | '
         f'{money(e5["delta"])} | {ci(e5)} | {lab(e5)} |',
         f'| H6 SPY + QQQ 0.30/0.15 put spreads, monthly (months; block 3) | {e6["counted"]:,} / {e6["N"]:,} | {e6["trades"]:,} | '
         f'{money(e6["delta"])} | {ci(e6)} | {lab(e6)} |', '',
         f'H5: sessions {days[0] + " → " + days[-1] if days else "none yet"} (forward from {H5_START}); traded {len(traded5)}; '
         f'the mean at the mids, for reading only: {money(sum(mids) / len(mids) if mids else None)}. The mapped prior was negative '
         '(PREREG_H5.md section 1).',
         f'H6: entries {len(ents)} (from {first_full_session(H6_START_MONTH)}), closed {len(trs)}, open {len(open_)}; by name, '
         'for reading only: ' + ', '.join(f'{nm} {c} closed, mean {money(m)}' for nm, (c, m) in per_name.items()) + '. '
         'N = 449 months (898 spreads, about 37 years): no verdict is reachable in any useful time (PREREG_H6.md section 6).', '',
         'No interval is printed under 60 sessions (H5) or 12 months (H6). The two tests are read separately; the ledger counts '
         'each as a hypothesis.', ''] + rh_lines(h5, ents, trs)
    txt = '\n'.join(L)
    p = Path(paths['report'])
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix('.part')
    tmp.write_text(txt)
    tmp.replace(p)
    return txt


# ---- one run -----------------------------------------------------------------------------------------------------------------------------

def default_paths(folder: Path | None = None) -> dict:
    f = Path(folder) if folder else FWD
    return {'h5': f / H5_CSV.name, 'h6_entries': f / H6_ENTRIES.name, 'h6_trades': f / H6_TRADES.name,
            'report': f / REPORT_PATH.name, 'verdicts': f / VERDICTS_PATH.name}


def run(days: list[str], layout: Path, official, eod_fetch=None, store: Path | None = None, folder: Path | None = None, log=None,
        only: tuple = ('H5', 'H6')) -> dict:
    """every complete forward session given (oldest first): H5's row where missing; H6's entries on a month's first full
    session and its exits on their exit sessions. `official(name, day)` → the official close or None. H5 stops at its
    first failing session, H6 at its first failing entry or exit; each failure is said (`<day> <step>: <why>`), nothing is
    written for it. → {'h5_added', 'h6_entries', 'h6_trades', 'failures', 'calls'}"""
    paths = default_paths(folder)
    store = Path(store) if store else Path(layout) / EOD_STORE
    res = {'h5_added': [], 'h6_entries': [], 'h6_trades': [], 'failures': [], 'calls': 0}
    counter = {'calls': 0}
    todo = sorted(set(days))
    have5 = {r['day'] for r in read_rows(paths['h5'])}
    for d in [x for x in todo if 'H5' in only and x >= H5_START and x not in have5]:
        try:
            row = h5_session(d, layout)
            res['h5_added'] += [k[0] for k in append_rows(paths['h5'], H5_COLS, [row], ('day',))]
            if log:
                log.info('edge H5 %s: %s', d, f'package {row["pnl"]:+.2f} after costs' if row['traded'] else f'no trade ({row["reason"]})')
        except EdgeDataError as e:
            res['failures'].append(f'{e.day} {e.step}: {e.why}')
            break
    try:
        for d in [x for x in todo if 'H6' in only and x[:7] >= H6_START_MONTH]:
            if is_entry_day(d):
                have = {(e['month'], e['name']) for e in read_rows(paths['h6_entries'])}
                for nm in H6_NAMES:
                    if (d[:7], nm) in have:
                        continue
                    spot = official(nm, d)
                    if spot is None:
                        raise EdgeDataError(d, 'h6-official-close', f'no official close for {nm} on disk')
                    df = get_eod(store, nm, d, None, eod_fetch, counter, 'h6-entry')
                    row = h6_entry(nm, d, df, spot)
                    res['h6_entries'] += ['/'.join(k) for k in append_rows(paths['h6_entries'], H6_ENTRY_COLS, [row], ('month', 'name'))]
                    if log:
                        log.info('edge H6 entry %s %s: %s', d, nm, f'{row["k_short"]:g}/{row["k_long"]:g} {row["expiry"]} credit {row["credit"]:.2f}'
                                 if row['status'] == 'open' else f'no trade ({row["reason"]})')
            closed = {(t['month'], t['name']) for t in read_rows(paths['h6_trades'])}
            for e in read_rows(paths['h6_entries']):
                if e['status'] != 'open' or e['exit_day'] != d or (e['month'], e['name']) in closed:
                    continue
                spot = official(e['name'], d)
                if spot is None:
                    raise EdgeDataError(d, 'h6-official-close', f'no official close for {e["name"]} on disk')
                df = get_eod(store, e['name'], d, e['expiry'], eod_fetch, counter, 'h6-exit')
                row = h6_exit(e, d, df, spot)
                res['h6_trades'] += ['/'.join(k) for k in append_rows(paths['h6_trades'], H6_TRADE_COLS, [row], ('month', 'name'))]
                if log:
                    log.info('edge H6 exit %s %s: %+.2f after costs', d, e['name'], row['pnl'])
    except EdgeDataError as e:
        res['failures'].append(f'{e.day} {e.step}: {e.why}')
    res['calls'] = counter['calls']
    write_report(paths)
    return res
