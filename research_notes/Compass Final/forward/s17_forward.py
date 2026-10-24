"""
s17_forward.py — Compass Final's forward test of S17 index put-writing (PREREG_COMPASS_FINAL.md section 9; the family has
no unread history: S17's single test read SPY and QQQ standard monthlies 2012-06 → 2026-10, all Theta serves). Run by
step 8 of scripts/daily_forward.py on every complete forward session, after H5/H6, with the same end-of-day fetch.

THE RULE, S17's own (research/compass/studies/s17_put_write.py at 7dfea57, A7 c81522a, results 5e7e1bd): on each standard
monthly expiration day (the roll: the third Friday, or the session before it when that Friday is a holiday) sell, for SPY
and QQQ, the NEXT standard monthly's at-the-money put — the highest put strike at or below S0 with bid > 0 and ask >= bid —
at its end-of-day bid; S0 = the session's last 1-minute close (the job's own bars; S17 used the stored 1-minute close).
Hold it to its last trading day (the next roll) and settle at intrinsic on that day's last 1-minute close (S17's S1).
Return = P&L ÷ (strike × 100), the cash set aside. FEES: Robinhood (docs/FEES_ROBINHOOD.md: the sale's $0.0403 a contract
+ TAF + SEC fee; $0 at expiration or assignment); S17's own $0.70 a contract a side beside it. Logged beside the ATM put
and never judged: the 0.30-delta put (S17's |delta| from greeks_7dfea57.py at R = 0.02, q = 0, τ = calendar days ÷ 365.25).

FIRST ROLL 2026-11-20 (the first roll after this file was committed). N = 147 closed ATM cycles, SPY and QQQ pooled
(80 % power, one-sided 5 %, on S17's mean +0.66 % and SD 3.21 % a cycle; out/mde_prereg.json). No verdict before N. At N,
on the first N closed cycles: mean > 0, the block-20 95 % lower end > 0 (audit_lib over the calendar sessions from the
first roll, a cycle booked on its entry session) and at most one calendar year with a mean ≤ 0 ⇒ PASS, else FAIL — written
once to s17_verdict.json and never revised.

Idempotent and loud as edge_forward.py: a row already written is never written again; a missing file, close or answer
raises EdgeDataError for that session, which writes nothing.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
for _p in (REPO / 'scripts', REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit', REPO / 'research_notes' / 'Edge search' / 'H5_H6', HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import eod_recorder as R  # noqa: E402
import edge_forward as EF  # noqa: E402
import audit_lib as AL  # noqa: E402
import fees_robinhood as FR  # noqa: E402

VERSION = 's17-forward-2026-10-24.1'
FIRST_ROLL = '2026-11-20'
N_RULE = 147
NAMES = ('SPY', 'QQQ')
FEE_S17 = 0.70
R_S17 = 0.02
ENTRIES = HERE / 's17_entries.csv'
TRADES = HERE / 's17_trades.csv'
REPORT = HERE / 'S17_FORWARD_REPORT.md'
VERDICT = HERE / 's17_verdict.json'
ENTRY_COLS = ('roll', 'name', 'status', 'reason', 'expiry', 's0', 'atm_k', 'atm_bid', 'atm_ask', 'd30_k', 'd30_bid', 'd30_delta', 'written_at')
TRADE_COLS = ('roll', 'name', 'structure', 'expiry', 'k', 'bid', 's1', 'payoff', 'capital', 'pnl_rh', 'pnl_s17', 'ret_rh', 'written_at')


def monthly_expiry(year: int, month: int) -> str:
    """the standard monthly's last trading day: the third Friday, or the trading day before it"""
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(4 - d.weekday()) % 7 + 14)
    while not R.is_trading_day(d.isoformat()):
        d -= dt.timedelta(days=1)
    return d.isoformat()


def next_monthly(day: str) -> str:
    d = dt.date.fromisoformat(day)
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return monthly_expiry(y, m)


def is_roll(day: str) -> bool:
    d = dt.date.fromisoformat(day)
    return day >= FIRST_ROLL and day == monthly_expiry(d.year, d.month)


def last_close(layout: Path, sym: str, day: str) -> float:
    f = Path(layout) / 'data' / 'underlying' / sym / f'{day}.parquet'
    if not f.exists():
        raise EF.EdgeDataError(day, 's17', f'{sym} 1-minute bars not on disk ({f.name})')
    b = pl.read_parquet(f, columns=['timestamp', 'close']).filter(pl.col('close').is_not_null() & pl.col('close').is_not_nan())
    if b.height == 0:
        raise EF.EdgeDataError(day, 's17', f'{sym} has no 1-minute close on {day}')
    return float(b.sort('timestamp')['close'][-1])


def entry_row(name: str, roll: str, df: pl.DataFrame, s0: float) -> dict:
    import greeks_7dfea57 as G
    exp = next_monthly(roll)
    row = {c: None for c in ENTRY_COLS}
    row.update(roll=roll, name=name, expiry=exp, s0=s0, written_at=EF.now_z())
    p = df.filter((pl.col('expiration') == exp) & (pl.col('right') == 'P') & (pl.col('bid') > 0) & (pl.col('ask') >= pl.col('bid')))
    atm = p.filter(pl.col('strike') <= s0).sort('strike', descending=True)
    if atm.height == 0:
        row.update(status='no entry', reason=f'no put at or below {s0:.2f} with bid > 0')
        return row
    a = atm.row(0, named=True)
    row.update(status='open', reason='', atm_k=a['strike'], atm_bid=a['bid'], atm_ask=a['ask'])
    T = max((dt.date.fromisoformat(exp) - dt.date.fromisoformat(roll)).days, 1) / 365.25
    mid = ((p['bid'] + p['ask']) / 2).to_numpy()
    iv = G.implied_vol(mid, s0, p['strike'].to_numpy(), T, np.array(['PUT'] * p.height), R_S17, 0.0)
    de = np.abs(G.delta(s0, p['strike'].to_numpy(), T, np.where(np.isnan(iv), 0.3, iv), np.array(['PUT'] * p.height), R_S17, 0.0))
    de = np.where(np.isnan(iv), np.nan, de)
    ok = ~np.isnan(de)
    if ok.any():
        i = int(np.nanargmin(np.where(ok, np.abs(de - 0.30), np.inf)))
        row.update(d30_k=float(p['strike'][i]), d30_bid=float(p['bid'][i]), d30_delta=float(de[i]))
    return row


def trade_rows(e: dict, roll: str, s1: float) -> list[dict]:
    out = []
    for structure, k, bid in (('atm_put', e['atm_k'], e['atm_bid']), ('put_30d', e.get('d30_k'), e.get('d30_bid'))):
        if k in (None, '') or bid in (None, ''):
            continue
        k, bid = float(k), float(bid)
        payoff = max(k - s1, 0.0)
        rh = FR.option_fee(e['name'], bid, 1, 'sell')
        pnl_rh = (bid - payoff) * 100 - rh
        out.append({'roll': e['roll'], 'name': e['name'], 'structure': structure, 'expiry': roll, 'k': k, 'bid': bid, 's1': s1, 'payoff': payoff,
                    'capital': k * 100, 'pnl_rh': pnl_rh, 'pnl_s17': (bid - payoff) * 100 - 2 * FEE_S17, 'ret_rh': pnl_rh / (k * 100),
                    'written_at': EF.now_z()})
    return out


def evaluate(trades: list[dict], sessions: list[str]) -> dict:
    x = sorted((t for t in trades if t['structure'] == 'atm_put'), key=lambda t: (t['roll'], t['name']))[:N_RULE]
    o = {'closed': len(x), 'n_rule': N_RULE}
    if not x:
        return o
    S = np.array([sum(float(t['ret_rh']) for t in x if t['roll'] == d) for d in sessions])
    N = np.array([sum(1 for t in x if t['roll'] == d) for d in sessions], float)
    st = AL.session_stats(S, N, blocks=(20,))
    o['mean_ret'] = st.get('mean_trade')
    o['ci_b20'] = st.get('ci_trade_b20')
    yrs = {}
    for t in x:
        yrs.setdefault(t['roll'][:4], []).append(float(t['ret_rh']))
    o['negative_years'] = sorted(y for y, v in yrs.items() if np.mean(v) <= 0)
    if len(x) >= N_RULE:
        lo = o['ci_b20'][0] if o.get('ci_b20') else float('nan')
        o['verdict'] = 'PASS' if (o['mean_ret'] > 0 and lo == lo and lo > 0 and len(o['negative_years']) <= 1) else 'FAIL'
    return o


def run(sessions: list[str], layout: Path, eod_fetch=None, store: Path | None = None, folder: Path | None = None, log=None) -> dict:
    global ENTRIES, TRADES, REPORT, VERDICT
    if folder is not None:
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        ENTRIES, TRADES, REPORT, VERDICT = folder / ENTRIES.name, folder / TRADES.name, folder / REPORT.name, folder / VERDICT.name
    store = Path(store) if store is not None else Path(layout) / EF.EOD_STORE
    counter, failures, added_e, added_t = {}, [], [], []
    have_e = {(r['roll'], r['name']): r for r in EF.read_rows(ENTRIES)}
    have_t = {(r['roll'], r['name'], r['structure']) for r in EF.read_rows(TRADES)}
    for day in sorted(sessions):
        if not is_roll(day):
            continue
        try:
            new_t, new_e = [], []
            for nm in NAMES:
                for (roll, name), e in list(have_e.items()):
                    if name == nm and e.get('status') == 'open' and e.get('expiry') == day and (roll, nm, 'atm_put') not in have_t:
                        new_t += trade_rows(e, day, last_close(layout, nm, day))
                if (day, nm) not in have_e:
                    exp = next_monthly(day)
                    df = EF.get_eod(store, nm, day, exp, eod_fetch, counter, 's17')
                    new_e.append(entry_row(nm, day, df, last_close(layout, nm, day)))
            if new_t:
                EF.append_rows(TRADES, TRADE_COLS, new_t, ('roll', 'name', 'structure'))
                added_t += [f"{t['roll']} {t['name']} {t['structure']}" for t in new_t]
                have_t |= {(t['roll'], t['name'], t['structure']) for t in new_t}
            if new_e:
                EF.append_rows(ENTRIES, ENTRY_COLS, new_e, ('roll', 'name'))
                added_e += [f"{e['roll']} {e['name']}" for e in new_e]
                have_e.update({(e['roll'], e['name']): e for e in new_e})
        except EF.EdgeDataError as x:
            failures.append(f'{day} s17: {x}')
    trades = EF.read_rows(TRADES)
    cal = [d for d in sorted(sessions) if d >= FIRST_ROLL]
    ev = evaluate(trades, cal)
    if ev.get('verdict') and not VERDICT.exists():
        VERDICT.write_text(json.dumps({'verdict': ev['verdict'], 'evaluated': ev, 'version': VERSION}, indent=1, default=str))
    write_report(ev, EF.read_rows(ENTRIES), trades)
    return {'s17_entries': added_e, 's17_trades': added_t, 'calls': counter.get('calls', 0), 'failures': failures, 'evaluated': ev}


def write_report(ev: dict, entries: list[dict], trades: list[dict]) -> None:
    L = ['# S17 forward — monthly ATM put-writing, SPY and QQQ (Compass Final, PREREG_COMPASS_FINAL.md section 9)', '',
         f'Rule as frozen (S17, 7dfea57): sell the next standard monthly ATM put at its end-of-day bid on each roll, hold to its last '
         f'trading day, settle at intrinsic on the last 1-minute close; Robinhood fees. First roll {FIRST_ROLL}. **No verdict before N = '
         f'{N_RULE} closed ATM cycles** (SPY and QQQ pooled).', '',
         f'- entries written: {len(entries)}; closed cycles (ATM): {sum(1 for t in trades if t["structure"] == "atm_put")} of {N_RULE}',
         f'- mean return a cycle so far (ATM, Robinhood): {ev.get("mean_ret") if ev.get("mean_ret") is None else f"{ev["mean_ret"] * 100:+.2f} %"} — read nothing into it before N',
         f'- verdict: {ev.get("verdict", "none (before N)")}', '']
    REPORT.write_text('\n'.join(L) + '\n')
