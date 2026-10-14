"""Long single-leg trade simulation on 1-minute NBBO (research/compass/04_protocol.md §4-§5).

Inputs per trade: the decision row (event), the chosen contract, the contract's minute quote series (timestamp = minute
boundary, bid, ask = last NBBO at that boundary), the underlying 1-minute feature frame for the hold window (close, vwap,
close_5m, minute, session), and the exit parameters. Fills: entry at the ask of the first valid quote at or after the
decision bar's close; exits at the bid of the quote at the minute boundary where the condition is observed. Size is 1.0
contract with fractional partial exits (P&L per contract is the size-weighted average).

Exit reasons, checked in this priority each minute: expired, settlement (the last bar of the contract's last trading
day: intrinsic value on the underlying close, no spread), session_cutoff, invalidation (5-minute close through the
signal's swing level), vwap_loss (1-minute close on the wrong side of the session VWAP), stop (bid <= entry x (1 -
stop_pct)), target_1 / target_2 (bid >= entry x (1 + tp)), ema_target (underlying reaches the EMA target), time (hold
limit). A dead quote (no bid) defers the exit to the next valid quote; the conditions are re-evaluated there.

`simulate` is vectorised (numpy); `simulate_loop` is the reference minute-by-minute implementation kept for the
equivalence test (tests/test_sim_equivalence.py).
"""
from __future__ import annotations
import datetime as dt
import numpy as np
import polars as pl

EXITS = dict(stop_pct=0.25, tp1_pct=0.25, tp1_frac=0.5, tp2_pct=0.50, max_hold_min=60, session_cutoff_minute=380,
             use_invalidation=True, use_vwap_loss=True, use_ema_target=True, commission=0.70, multiplier=100,
             settle_intrinsic=True)

REASONS = ['expired', 'settlement', 'session_cutoff', 'invalidation', 'vwap_loss', 'stop', 'target_1', 'target_2', 'ema_target', 'time']

def _nan(x):
    return x is None or (isinstance(x, float) and np.isnan(x))

def _targets(event: dict, direction: int):
    spot0 = float(event['spot'])
    levels = [float(x) for x in (event.get('ema_mid_15m'), event.get('ema_slow_15m')) if not _nan(x)]
    ahead = [x for x in levels if (x > spot0 if direction > 0 else x < spot0)]
    ema_target = (min(ahead) if direction > 0 else max(ahead)) if ahead else None
    inval = event.get('invalidation_level'); inval = None if _nan(inval) else float(inval)
    return ema_target, inval

def simulate(event: dict, contract: dict, quotes: pl.DataFrame, feat: pl.DataFrame, params: dict | None = None, spot_series=None) -> dict | None:
    p = {**EXITS, **(params or {})}
    direction = int(event['direction']); decision_close = event['close_ts']
    q = quotes.filter(pl.col('timestamp') >= decision_close).sort('timestamp')
    if q.height == 0: return None
    ts = q['timestamp'].to_numpy().astype('datetime64[ms]')
    bid = q['bid'].cast(pl.Float64).fill_null(np.nan).to_numpy(); ask = q['ask'].cast(pl.Float64).fill_null(np.nan).to_numpy()
    valid = np.isfinite(bid) & np.isfinite(ask) & (bid > 0) & (ask >= bid)
    vi = np.flatnonzero(valid)
    if vi.size == 0: return {'status': 'no_fill', 'reason': 'no_valid_quote'}
    i0 = int(vi[0]); entry_ts = ts[i0]; entry_ask = float(ask[i0])
    if entry_ts > np.datetime64(decision_close, 'ms') + np.timedelta64(5, 'm'): return {'status': 'no_fill', 'reason': 'stale_quote'}
    tsp = ts[i0 + 1:]; bidp = bid[i0 + 1:]; askp = ask[i0 + 1:]; vp = valid[i0 + 1:]
    n = tsp.size
    if n == 0: return {'status': 'no_fill', 'reason': 'no_exit_quote'}
    # underlying features at each path minute (exact close_ts match)
    fts = feat['close_ts'].to_numpy().astype('datetime64[ms]')
    pos = np.searchsorted(fts, tsp); pos_c = np.minimum(pos, fts.size - 1)
    match = (pos < fts.size) & (fts[pos_c] == tsp)
    def col(name, dtype=float):
        v = feat[name].cast(pl.Float64).fill_null(np.nan).to_numpy() if dtype is float else feat[name].to_numpy()
        return np.where(match, v[pos_c], np.nan) if dtype is float else np.where(match, v[pos_c], -1)
    close = col('close'); vwap = col('vwap'); c5 = col('close_5m'); minute = col('minute', int)
    sess = feat['session'].to_numpy()[pos_c]
    path_date = tsp.astype('datetime64[D]')
    held = (tsp - entry_ts) / np.timedelta64(1, 'm')
    ema_target, inval = _targets(event, direction)
    ltd = contract.get('last_trading_day')
    cond = {}
    cond['expired'] = (path_date > np.datetime64(ltd, 'D')) if ltd is not None else np.zeros(n, bool)
    # settlement: the last bar of the last trading day (minute index equals the session's last minute: the next feat row is a new session or none)
    if ltd is not None and p['settle_intrinsic']:
        is_ltd = path_date == np.datetime64(ltd, 'D')
        last_of_session = np.zeros(n, bool)
        if is_ltd.any():
            # the greatest matched minute on that day
            mm = np.where(is_ltd & match, minute, -1)
            if mm.max() >= 0: last_of_session = is_ltd & match & (minute == mm.max())
        cond['settlement'] = last_of_session
    else: cond['settlement'] = np.zeros(n, bool)
    cutoff_ok = True if ltd is None or p['max_hold_min'] <= 390 else None
    if cutoff_ok is None: cond['session_cutoff'] = (minute >= p['session_cutoff_minute']) & (path_date == np.datetime64(ltd, 'D'))
    else: cond['session_cutoff'] = (minute >= 0) & (minute >= p['session_cutoff_minute'])
    zeros = np.zeros(n, bool)
    with np.errstate(invalid='ignore'):
        cond['invalidation'] = (match & ((c5 < inval) if direction > 0 else (c5 > inval))) if (p['use_invalidation'] and inval is not None) else zeros
        cond['vwap_loss'] = (match & ((close < vwap) if direction > 0 else (close > vwap))) if p['use_vwap_loss'] else zeros
        cond['stop'] = vp & (bidp <= entry_ask * (1 - p['stop_pct']))
        cond['target_1'] = (vp & (bidp >= entry_ask * (1 + p['tp1_pct']))) if p['tp1_frac'] > 0 else zeros
        cond['target_2'] = vp & (bidp >= entry_ask * (1 + p['tp2_pct']))
        cond['ema_target'] = (match & ((close >= ema_target) if direction > 0 else (close <= ema_target))) if (p['use_ema_target'] and ema_target is not None) else zeros
    cond['time'] = held >= p['max_hold_min']
    for k in cond: cond[k] = np.asarray(cond[k], bool)
    def first_trigger(start: int, skip_t1: bool):
        any_c = np.zeros(n, bool)
        for k in REASONS:
            if skip_t1 and k == 'target_1': continue
            any_c |= cond[k]
        fillable = any_c & (vp | cond['settlement'])
        fillable[:start] = False
        idx = np.flatnonzero(fillable)
        if idx.size == 0: return None, None
        i = int(idx[0])
        for k in REASONS:
            if skip_t1 and k == 'target_1': continue
            if cond[k][i]: return i, k
        return i, 'time'
    def settle_price(i):
        K = float(contract['strike']); S = close[i]
        if not np.isfinite(S): return None
        return max(S - K, 0.0) if direction > 0 else max(K - S, 0.0)
    legs = []; size = 1.0; realized = 0.0
    i1, r1 = first_trigger(0, skip_t1=False)
    end_i = None
    if i1 is not None and r1 == 'target_1':
        frac = p['tp1_frac']; legs.append((tsp[i1], float(bidp[i1]), frac, 'target_1')); realized += frac * (bidp[i1] - entry_ask); size -= frac
        i2, r2 = first_trigger(i1 + 1, skip_t1=True)
        if i2 is not None:
            px = settle_price(i2) if r2 == 'settlement' else float(bidp[i2])
            if px is not None:
                legs.append((tsp[i2], px, size, r2)); realized += size * (px - entry_ask); size = 0.0; end_i = i2
    elif i1 is not None:
        px = settle_price(i1) if r1 == 'settlement' else float(bidp[i1])
        if px is not None:
            legs.append((tsp[i1], px, size, r1)); realized += size * (px - entry_ask); size = 0.0; end_i = i1
    if size > 0:
        lv = np.flatnonzero(vp)
        if lv.size == 0: return {'status': 'no_fill', 'reason': 'no_exit_quote'}
        last_bid = float(bidp[lv[-1]])
        legs.append((tsp[-1], last_bid, size, 'data_end')); realized += size * (last_bid - entry_ask); size = 0.0; end_i = n - 1
    upto = vp.copy(); upto[end_i + 1:] = False
    bids_seen = bidp[upto]
    min_bid = min(entry_ask, float(bids_seen.min())) if bids_seen.size else entry_ask
    max_bid = max(entry_ask, float(bids_seen.max())) if bids_seen.size else entry_ask
    comm = p['commission'] * (1 + sum(l[2] for l in legs))
    pnl = realized * p['multiplier'] - comm
    exit_ts = legs[-1][0]
    to_py = lambda t: dt.datetime.fromtimestamp(int(np.datetime64(t, 'ms').astype(np.int64)) / 1000.0, dt.timezone.utc).replace(tzinfo=None)
    return {
        'status': 'filled', 'entry_ts': to_py(entry_ts), 'exit_ts': to_py(exit_ts), 'entry_ask': entry_ask, 'exit_bid': float(legs[-1][1]),
        'exit_reason': legs[-1][3], 'partial': len(legs) > 1, 'pnl': float(pnl), 'gross': float(realized * p['multiplier']), 'commission': float(comm),
        'hold_min': float((exit_ts - entry_ts) / np.timedelta64(1, 'm')), 'mae': float((entry_ask - min_bid) * p['multiplier']), 'mfe': float((max_bid - entry_ask) * p['multiplier']),
        'ret_pct': float(realized / entry_ask), 'ema_target': ema_target, 'invalidation_level': inval,
    }

def simulate_loop(event: dict, contract: dict, quotes: pl.DataFrame, feat: pl.DataFrame, params: dict | None = None, spot_series=None) -> dict | None:
    """Reference implementation (minute-by-minute); same semantics as simulate() except settlement, which it does not model."""
    p = {**EXITS, **(params or {})}
    direction = int(event['direction']); decision_close = event['close_ts']
    q = quotes.filter(pl.col('timestamp') >= decision_close).sort('timestamp')
    if q.height == 0: return None
    ent = q.filter((pl.col('ask') > 0) & (pl.col('bid') > 0) & (pl.col('ask') >= pl.col('bid')))
    if ent.height == 0: return {'status': 'no_fill', 'reason': 'no_valid_quote'}
    e = ent.row(0, named=True); entry_ts = e['timestamp']; entry_ask = float(e['ask'])
    if entry_ts > decision_close + dt.timedelta(minutes=5): return {'status': 'no_fill', 'reason': 'stale_quote'}
    path = q.filter(pl.col('timestamp') > entry_ts)
    f = feat.filter(pl.col('close_ts') > entry_ts).select(['close_ts', 'close', 'vwap', 'close_5m', 'minute', 'session'])
    path = path.join(f, left_on='timestamp', right_on='close_ts', how='left').sort('timestamp')
    ema_target, inval = _targets(event, direction)
    size = 1.0; realized = 0.0; legs = []; min_bid = entry_ask; max_bid = entry_ask; last_valid_bid = None
    expiry_ltd = contract.get('last_trading_day')
    for r in path.iter_rows(named=True):
        ts = r['timestamp']; bid = r['bid']; ask = r['ask']
        valid = bid is not None and ask is not None and bid > 0 and ask >= bid
        if valid: min_bid = min(min_bid, bid); max_bid = max(max_bid, bid); last_valid_bid = bid
        held = (ts - entry_ts).total_seconds() / 60.0
        minute = r['minute']; close = r['close']; vwap = r['vwap']; c5 = r['close_5m']
        reason = None
        if expiry_ltd is not None and ts.date() > expiry_ltd: reason = 'expired'
        elif minute is not None and minute >= p['session_cutoff_minute'] and (expiry_ltd is None or ts.date() == expiry_ltd or p['max_hold_min'] <= 390): reason = 'session_cutoff'
        elif p['use_invalidation'] and inval is not None and c5 is not None and ((direction > 0 and c5 < inval) or (direction < 0 and c5 > inval)): reason = 'invalidation'
        elif p['use_vwap_loss'] and close is not None and vwap is not None and ((direction > 0 and close < vwap) or (direction < 0 and close > vwap)): reason = 'vwap_loss'
        elif valid and bid <= entry_ask * (1 - p['stop_pct']): reason = 'stop'
        elif valid and size == 1.0 and p['tp1_frac'] > 0 and bid >= entry_ask * (1 + p['tp1_pct']): reason = 'target_1'
        elif valid and bid >= entry_ask * (1 + p['tp2_pct']): reason = 'target_2'
        elif p['use_ema_target'] and ema_target is not None and close is not None and ((direction > 0 and close >= ema_target) or (direction < 0 and close <= ema_target)): reason = 'ema_target'
        elif held >= p['max_hold_min']: reason = 'time'
        if reason is None or not valid: continue
        if reason == 'target_1':
            frac = p['tp1_frac']; legs.append((ts, bid, frac, reason)); realized += frac * (bid - entry_ask); size -= frac; continue
        legs.append((ts, bid, size, reason)); realized += size * (bid - entry_ask); size = 0.0
        break
    if size > 0:
        if last_valid_bid is None: return {'status': 'no_fill', 'reason': 'no_exit_quote'}
        legs.append((path['timestamp'][-1] if path.height else entry_ts, last_valid_bid, size, 'data_end')); realized += size * (last_valid_bid - entry_ask); size = 0.0
    comm = p['commission'] * (1 + sum(l[2] for l in legs)); pnl = realized * p['multiplier'] - comm; exit_ts = legs[-1][0]
    return {'status': 'filled', 'entry_ts': entry_ts, 'exit_ts': exit_ts, 'entry_ask': entry_ask, 'exit_bid': legs[-1][1], 'exit_reason': legs[-1][3], 'partial': len(legs) > 1,
            'pnl': pnl, 'gross': realized * p['multiplier'], 'commission': comm, 'hold_min': (exit_ts - entry_ts).total_seconds() / 60.0,
            'mae': (entry_ask - min_bid) * p['multiplier'], 'mfe': (max_bid - entry_ask) * p['multiplier'], 'ret_pct': realized / entry_ask, 'ema_target': ema_target, 'invalidation_level': inval}
