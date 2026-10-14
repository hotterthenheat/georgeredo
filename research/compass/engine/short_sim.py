"""Short-premium simulation on 1-minute NBBO chains (04_protocol.md amendment A4): a short single contract or a short
vertical (short leg nearest the long rule's delta, long leg nearest a further-OTM delta), sold at the bid / bought at the
ask leg by leg, fees per contract per side per leg, exits at a session cutoff, a stop on the cost to close (multiple of
the credit) or a time limit. Marks are the cost to close at each minute (ask of the short leg minus bid of the long leg)."""
from __future__ import annotations
import datetime as dt
import numpy as np
import polars as pl
from . import contracts

EXITS = dict(stop_mult=2.0, max_hold_min=None, session_cutoff_minute=380, commission=0.70, tick_adverse=0.0)

def pick_long_leg(snap: pl.DataFrame, short_row: dict, direction: int, target_delta: float = 0.20, lo: float = 0.08, hi: float = 0.32) -> dict | None:
    """The protective leg: same right, further out of the money than the short strike, |delta| nearest target."""
    right = short_row['right']; K = float(short_row['strike'])
    c = snap.filter((pl.col('right') == right) & ((pl.col('strike') > K) if right == 'C' else (pl.col('strike') < K)))
    c = c.filter(pl.col('delta_abs').is_between(lo, hi) & (pl.col('bid') > 0) & (pl.col('ask') >= pl.col('bid')))
    if c.height == 0: return None
    return c.with_columns((pl.col('delta_abs') - target_delta).abs().alias('_d')).sort('_d').row(0, named=True)

def _path(quotes: pl.DataFrame, t0):
    q = quotes.filter(pl.col('timestamp') >= t0).sort('timestamp')
    ts = q['timestamp'].to_numpy().astype('datetime64[ms]')
    bid = q['bid'].cast(pl.Float64).fill_null(np.nan).to_numpy(); ask = q['ask'].cast(pl.Float64).fill_null(np.nan).to_numpy()
    return ts, bid, ask

def simulate(event: dict, short_q: pl.DataFrame, long_q: pl.DataFrame | None, params: dict | None = None) -> dict:
    p = {**EXITS, **(params or {})}; tick = p['tick_adverse']
    t0 = np.datetime64(event['close_ts'], 'ms')
    ts, sb, sa = _path(short_q, event['close_ts'])
    if ts.size == 0: return {'status': 'no_quotes'}
    if long_q is not None:
        lts, lb, la = _path(long_q, event['close_ts'])
        # align the long leg on the short leg's timestamps (exact minute match; missing -> nan)
        pos = np.searchsorted(lts, ts); pc = np.minimum(pos, max(lts.size - 1, 0)); m = (lts.size > 0) & (pos < lts.size) & (lts[pc] == ts) if lts.size else np.zeros(ts.size, bool)
        lb_al = np.where(m, lb[pc] if lts.size else np.nan, np.nan); la_al = np.where(m, la[pc] if lts.size else np.nan, np.nan)
    else:
        lb_al = np.zeros(ts.size); la_al = np.zeros(ts.size)
    # entry needs a bid to sell the short leg into (and an ask to buy the long leg); an exit needs an ask to buy the short
    # leg back (near expiry an OTM contract is bid 0 / ask 0.01: that is a real $0.01 buy-back, not a dead quote) and a
    # finite bid for the long leg (which may be 0: the leg is abandoned)
    fin = np.isfinite(sb) & np.isfinite(sa) & (sa >= sb) & np.isfinite(lb_al) & np.isfinite(la_al) & ((long_q is None) | (la_al >= lb_al))
    valid_entry = fin & (sb > 0) & ((long_q is None) | (la_al > 0))
    valid = fin & (sa > 0)
    vi = np.flatnonzero(valid_entry)
    if vi.size == 0: return {'status': 'no_fill', 'reason': 'no_valid_quote'}
    i0 = int(vi[0]); entry_ts = ts[i0]
    if entry_ts > t0 + np.timedelta64(5, 'm'): return {'status': 'no_fill', 'reason': 'stale_quote'}
    credit = (sb[i0] - tick) - ((la_al[i0] + tick) if long_q is not None else 0.0)
    if credit <= 0: return {'status': 'no_fill', 'reason': 'no_credit'}
    legs = 2 if long_q is not None else 1
    # cost to close at each later minute
    j = np.arange(i0 + 1, ts.size)
    if j.size == 0: return {'status': 'no_fill', 'reason': 'no_exit_quote'}
    ctc = (sa[j] + tick) - ((lb_al[j] - tick) if long_q is not None else 0.0)
    v = valid[j]
    minute = ((ts[j] - ts[j].astype('datetime64[D]')) / np.timedelta64(1, 'm')).astype(int) - 570  # minutes since 09:30
    held = (ts[j] - entry_ts) / np.timedelta64(1, 'm')
    cond_stop = v & (ctc >= p['stop_mult'] * credit) if p['stop_mult'] else np.zeros(j.size, bool)
    cond_cut = v & (minute >= p['session_cutoff_minute'])
    cond_time = v & (held >= p['max_hold_min']) if p['max_hold_min'] else np.zeros(j.size, bool)
    first = {}
    for k, c in (('stop', cond_stop), ('session_cutoff', cond_cut), ('time', cond_time)):
        idx = np.flatnonzero(c); first[k] = int(idx[0]) if idx.size else None
    cands = [(i, k) for k, i in first.items() if i is not None]
    if not cands:
        # no valid exit quote before the end of the path: close at the last valid quote
        vv = np.flatnonzero(v)
        if vv.size == 0: return {'status': 'no_fill', 'reason': 'no_exit_quote'}
        ix, reason = int(vv[-1]), 'last_quote'
    else:
        ix, reason = min(cands)
    exit_cost = float(ctc[ix]); fees = legs * 2 * p['commission']
    pnl = (credit - exit_cost) * 100.0 - fees
    mae = float(np.nanmax(np.where(v[:ix + 1], ctc[:ix + 1], np.nan)) - credit) * 100.0 if ix >= 0 else 0.0
    return {'status': 'filled', 'entry_ts': entry_ts.astype('datetime64[us]').astype(dt.datetime), 'exit_ts': ts[j][ix].astype('datetime64[us]').astype(dt.datetime),
            'credit': float(credit), 'exit_cost': exit_cost, 'exit_reason': reason, 'pnl': float(pnl), 'gross': float((credit - exit_cost) * 100.0), 'commission': float(fees),
            'hold_min': float(held[ix]), 'mae': mae, 'legs': legs, 'ret_pct_of_credit': float((credit - exit_cost) / credit)}
