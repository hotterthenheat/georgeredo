"""Long single-leg trade simulation on 1-minute NBBO (research/compass/04_protocol.md §4-§5).

Inputs per trade: the decision row (event), the chosen contract, the contract's minute quote series (timestamp = minute
boundary, bid, ask = last NBBO at that boundary), the underlying 1-minute feature frame for the hold window (close, vwap,
close_5m, swing levels, EMA levels), and the exit parameters. Fills: entry at the ask of the first quote at or after the
decision bar's close; exits at the bid of the quote at the minute boundary where the condition is observed. Size is 1.0
contract with fractional partial exits (P&L per contract is the size-weighted average).

Exit reasons, checked in this order each minute: expiry/settlement, session_cutoff, invalidation (5-minute close through
the signal's swing level), vwap_loss (1-minute close on the wrong side of the session VWAP), stop (bid <= entry x (1 -
stop_pct)), target_1/target_2 (bid >= entry x (1 + tp)), ema_target (underlying reaches the EMA target level), time
(hold limit). A dead quote (bid 0) defers the exit to the next valid quote.
"""
from __future__ import annotations
import datetime as dt
import numpy as np
import polars as pl

EXITS = dict(stop_pct=0.25, tp1_pct=0.25, tp1_frac=0.5, tp2_pct=0.50, max_hold_min=60, session_cutoff_minute=380,
             use_invalidation=True, use_vwap_loss=True, use_ema_target=True, commission=0.70, multiplier=100,
             settle_intrinsic=True)

def simulate(event: dict, contract: dict, quotes: pl.DataFrame, feat: pl.DataFrame, params: dict | None = None, spot_series: pl.DataFrame | None = None) -> dict | None:
    p = {**EXITS, **(params or {})}
    direction = int(event['direction'])
    decision_close = event['close_ts']
    q = quotes.filter(pl.col('timestamp') >= decision_close).sort('timestamp')
    if q.height == 0: return None
    # entry: first valid ask at/after the decision bar's close
    ent = q.filter((pl.col('ask') > 0) & (pl.col('bid') > 0) & (pl.col('ask') >= pl.col('bid')))
    if ent.height == 0: return {'status': 'no_fill', 'reason': 'no_valid_quote'}
    e = ent.row(0, named=True)
    entry_ts = e['timestamp']; entry_ask = float(e['ask'])
    if entry_ts > decision_close + dt.timedelta(minutes=5): return {'status': 'no_fill', 'reason': 'stale_quote'}
    # per-minute path after entry
    path = q.filter(pl.col('timestamp') > entry_ts)
    f = feat.filter(pl.col('close_ts') > entry_ts).select(['close_ts', 'close', 'vwap', 'close_5m', 'minute', 'session', 'ema_mid_15m', 'ema_slow_15m'])
    path = path.join(f, left_on='timestamp', right_on='close_ts', how='left').sort('timestamp')
    inval = event.get('invalidation_level'); inval = None if inval is None or (isinstance(inval, float) and np.isnan(inval)) else float(inval)
    # EMA target: the nearest 15m EMA level beyond spot in the trade's direction at decision time
    spot0 = float(event['spot']); levels = [event.get('ema_mid_15m'), event.get('ema_slow_15m')]
    levels = [float(x) for x in levels if x is not None and not (isinstance(x, float) and np.isnan(x))]
    ahead = [x for x in levels if (x > spot0 if direction > 0 else x < spot0)]
    ema_target = (min(ahead) if direction > 0 else max(ahead)) if ahead else None
    size = 1.0; realized = 0.0; legs = []
    min_bid = entry_ask; max_bid = entry_ask
    last_valid_bid = None
    expiry_ltd = contract.get('last_trading_day')
    for r in path.iter_rows(named=True):
        ts = r['timestamp']; bid = r['bid']; ask = r['ask']
        valid = bid is not None and bid > 0 and ask is not None and ask >= bid
        if valid:
            min_bid = min(min_bid, bid); max_bid = max(max_bid, bid); last_valid_bid = bid
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
        if reason is None: continue
        if not valid:
            continue  # dead quote: defer to the next valid quote
        if reason == 'target_1':
            frac = p['tp1_frac']; legs.append((ts, bid, frac, reason)); realized += frac * (bid - entry_ask); size -= frac; continue
        legs.append((ts, bid, size, reason)); realized += size * (bid - entry_ask); size = 0.0
        break
    if size > 0:
        # end of data without a trigger: close at the last valid bid (recorded as 'data_end')
        if last_valid_bid is None: return {'status': 'no_fill', 'reason': 'no_exit_quote'}
        legs.append((path['timestamp'][-1] if path.height else entry_ts, last_valid_bid, size, 'data_end')); realized += size * (last_valid_bid - entry_ask); size = 0.0
    comm = p['commission'] * (1 + sum(l[2] for l in legs))
    pnl = realized * p['multiplier'] - comm
    exit_ts = legs[-1][0]
    return {
        'status': 'filled', 'entry_ts': entry_ts, 'exit_ts': exit_ts, 'entry_ask': entry_ask, 'exit_bid': legs[-1][1],
        'exit_reason': legs[-1][3], 'partial': len(legs) > 1, 'pnl': pnl, 'gross': realized * p['multiplier'], 'commission': comm,
        'hold_min': (exit_ts - entry_ts).total_seconds() / 60.0, 'mae': (entry_ask - min_bid) * p['multiplier'], 'mfe': (max_bid - entry_ask) * p['multiplier'],
        'ret_pct': realized / entry_ask, 'ema_target': ema_target, 'invalidation_level': inval,
    }
