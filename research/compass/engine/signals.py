"""Feature frame and the baseline Compass signal (the owner's specification, research/compass/04_protocol.md §4).

features(df1, params) adds, to every 1-minute bar of one symbol:
  1m : rsi, ema_fast, ema_lead, ema_mid, ema_slow, ema_long, vwap, vwap_sigma, cum_vol, relvol, atr
  5m : close_5m, ema_mid_5m, struct_5m (+1 HH/HL, -1 LH/LL, 0), swing_hi_5m, swing_lo_5m
  15m: close_15m, ema_mid_15m, ema_slow_15m, ema_long_15m
  d  : ema_mid_d, ema_slow_d, ema_long_d, close_d (previous completed session)
Higher-timeframe values are those of the latest COMPLETED bar at the 1-minute bar's close (bars.align_closed), so no
look-ahead. NaN = not computable yet.

baseline_events(feat, params) returns the decision rows: an RSI cross of the lead threshold on the 1-minute bar with the
close on the right side of the lead EMA, the 5-minute confirmation (close above/below the mid EMA and the session VWAP),
the 15-minute alignment (mid EMA vs slow EMA and price vs mid EMA), relative volume at or above the floor, and the
5-minute structure in the signal's direction. Each flag is also returned so ablations can switch any one off.
"""
from __future__ import annotations
import numpy as np
import polars as pl
from . import bars, indicators as ind

BASELINE = dict(
    rsi_period=14, rsi_up=55.0, rsi_down=45.0,
    ema_fast=5, ema_lead=9, ema_mid=20, ema_slow=50, ema_long=200,
    relvol_lookback=20, relvol_min=1.0,
    pivot_left=3, pivot_right=3,
    atr_period=14,
    use_confirm_5m=True, use_align_15m=True, use_daily_trend=False, use_structure=True, use_relvol=True,
    entry_start_minute=15,   # 09:45
    entry_end_minute=300,    # 14:30 (families narrow this)
)

def _tf_frame(df_tf: pl.DataFrame, params: dict, which: str) -> pl.DataFrame:
    a = bars.with_session_arrays(df_tf)
    cols = {}
    if which == '5m':
        cols['close_5m'] = a['close']
        cols['ema_mid_5m'] = ind.ema(a['close'], params['ema_mid'])
        cols['struct_5m'] = ind.structure_state(a['high'], a['low'], params['pivot_left'], params['pivot_right'])
        hi, lo = ind.last_swing_levels(a['high'], a['low'], params['pivot_left'], params['pivot_right'])
        cols['swing_hi_5m'] = hi; cols['swing_lo_5m'] = lo
    elif which == '15m':
        cols['close_15m'] = a['close']
        cols['ema_mid_15m'] = ind.ema(a['close'], params['ema_mid'])
        cols['ema_slow_15m'] = ind.ema(a['close'], params['ema_slow'])
        cols['ema_long_15m'] = ind.ema(a['close'], params['ema_long'])
    elif which == 'd':
        cols['close_d'] = a['close']
        cols['ema_mid_d'] = ind.ema(a['close'], params['ema_mid'])
        cols['ema_slow_d'] = ind.ema(a['close'], params['ema_slow'])
        cols['ema_long_d'] = ind.ema(a['close'], params['ema_long'])
    return df_tf.select(['close_ts']).with_columns([pl.Series(k, v) for k, v in cols.items()])

def features(df1: pl.DataFrame, params: dict | None = None, daily: pl.DataFrame | None = None) -> pl.DataFrame:
    p = {**BASELINE, **(params or {})}
    a = bars.with_session_arrays(df1)
    close, high, low, vol = a['close'], a['high'], a['low'], a['volume']
    cum = ind.cumulative_session_volume(vol, a['session'])
    f = df1.with_columns([
        pl.Series('rsi', ind.rsi(close, p['rsi_period'])),
        pl.Series('ema_fast', ind.ema(close, p['ema_fast'])),
        pl.Series('ema_lead', ind.ema(close, p['ema_lead'])),
        pl.Series('ema_mid', ind.ema(close, p['ema_mid'])),
        pl.Series('ema_slow', ind.ema(close, p['ema_slow'])),
        pl.Series('ema_long', ind.ema(close, p['ema_long'])),
        pl.Series('vwap', ind.session_vwap(high, low, close, vol, a['session'])),
        pl.Series('vwap_sigma', ind.session_vwap_sigma(high, low, close, vol, a['session'])),
        pl.Series('cum_vol', cum),
        pl.Series('relvol', ind.relative_volume(cum, a['minute'], a['session'], p['relvol_lookback'])),
        pl.Series('atr', ind.atr(high, low, close, p['atr_period'])),
    ])
    df5 = bars.resample(df1, 5); df15 = bars.resample(df1, 15)
    f = bars.align_closed(f, _tf_frame(df5, p, '5m'), ['close_5m', 'ema_mid_5m', 'struct_5m', 'swing_hi_5m', 'swing_lo_5m'], '')
    f = bars.align_closed(f, _tf_frame(df15, p, '15m'), ['close_15m', 'ema_mid_15m', 'ema_slow_15m', 'ema_long_15m'], '')
    dd = daily if daily is not None else bars.daily_from_minutes(df1)
    f = bars.align_closed(f, _tf_frame(dd, p, 'd'), ['close_d', 'ema_mid_d', 'ema_slow_d', 'ema_long_d'], '')
    return f.sort('timestamp')

def baseline_events(feat: pl.DataFrame, params: dict | None = None) -> pl.DataFrame:
    """Decision rows with direction +1 (call) / -1 (put) and every component flag."""
    p = {**BASELINE, **(params or {})}
    rsi = feat['rsi'].to_numpy(); prev = np.roll(rsi, 1); prev[0] = np.nan
    same_session = (feat['session'].cast(pl.Int32).to_numpy() == np.roll(feat['session'].cast(pl.Int32).to_numpy(), 1))
    close = feat['close'].to_numpy()
    cross_up = (prev <= p['rsi_up']) & (rsi > p['rsi_up']) & same_session
    cross_dn = (prev >= p['rsi_down']) & (rsi < p['rsi_down']) & same_session
    lead_up = close > feat['ema_lead'].to_numpy(); lead_dn = close < feat['ema_lead'].to_numpy()
    c5_up = (feat['close_5m'].to_numpy() > feat['ema_mid_5m'].to_numpy()) & (close > feat['vwap'].to_numpy())
    c5_dn = (feat['close_5m'].to_numpy() < feat['ema_mid_5m'].to_numpy()) & (close < feat['vwap'].to_numpy())
    a15_up = (feat['ema_mid_15m'].to_numpy() > feat['ema_slow_15m'].to_numpy()) & (feat['close_15m'].to_numpy() > feat['ema_mid_15m'].to_numpy())
    a15_dn = (feat['ema_mid_15m'].to_numpy() < feat['ema_slow_15m'].to_numpy()) & (feat['close_15m'].to_numpy() < feat['ema_mid_15m'].to_numpy())
    d_up = (feat['ema_mid_d'].to_numpy() > feat['ema_slow_d'].to_numpy()); d_dn = (feat['ema_mid_d'].to_numpy() < feat['ema_slow_d'].to_numpy())
    rv = feat['relvol'].to_numpy(); rv_ok = rv >= p['relvol_min']
    st = feat['struct_5m'].to_numpy()
    minute = feat['minute'].to_numpy(); window = (minute >= p['entry_start_minute']) & (minute <= p['entry_end_minute'])
    def gate(flag, use): return flag if use else np.ones_like(flag, dtype=bool)
    up = cross_up & lead_up & window & gate(c5_up, p['use_confirm_5m']) & gate(a15_up, p['use_align_15m']) & gate(d_up, p['use_daily_trend']) & gate(rv_ok, p['use_relvol']) & gate(st == 1, p['use_structure'])
    dn = cross_dn & lead_dn & window & gate(c5_dn, p['use_confirm_5m']) & gate(a15_dn, p['use_align_15m']) & gate(d_dn, p['use_daily_trend']) & gate(rv_ok, p['use_relvol']) & gate(st == -1, p['use_structure'])
    direction = np.where(up, 1, np.where(dn, -1, 0))
    out = feat.with_columns([
        pl.Series('direction', direction), pl.Series('f_cross', cross_up | cross_dn), pl.Series('f_lead', lead_up | lead_dn),
        pl.Series('f_confirm_5m', np.where(direction > 0, c5_up, c5_dn)), pl.Series('f_align_15m', np.where(direction > 0, a15_up, a15_dn)),
        pl.Series('f_daily', np.where(direction > 0, d_up, d_dn)), pl.Series('f_relvol', rv_ok), pl.Series('f_structure', np.where(direction > 0, st == 1, st == -1)),
    ]).filter(pl.col('direction') != 0)
    return out.with_columns([
        pl.when(pl.col('direction') > 0).then(pl.col('swing_lo_5m')).otherwise(pl.col('swing_hi_5m')).alias('invalidation_level'),
        pl.col('close').alias('spot'),
    ])
