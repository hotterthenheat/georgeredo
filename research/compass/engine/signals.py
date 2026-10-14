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


# ---- setup families (04_protocol.md §4) ---------------------------------------------------------------------------------
FAMILY_DEFAULTS = {
    'quick_scalps': {},
    'trend_plays': {'pullback_bars_15m': 3},
    'breakouts': {'relvol_min': 1.5, 'range_bars_5m': 20},
    'bounces': {'z_window': 60, 'z_threshold': 2.0, 'alpha_atr': 1.5, 'beta_atr': 0.5, 'touch_bars': 5},
}

def _daily_levels(df1: pl.DataFrame) -> pl.DataFrame:
    """Per 1-minute bar: the PREVIOUS session's high/low and the 20-session high/low ending the previous session."""
    d = bars.daily_from_minutes(df1).sort('session')
    d = d.with_columns([pl.col('high').shift(1).alias('prev_high'), pl.col('low').shift(1).alias('prev_low'),
                        pl.col('high').shift(1).rolling_max(20).alias('high_20d'), pl.col('low').shift(1).rolling_min(20).alias('low_20d')])
    return d.select(['session', 'prev_high', 'prev_low', 'high_20d', 'low_20d'])

def family_events(feat: pl.DataFrame, family: str, params: dict | None = None, df1: pl.DataFrame | None = None) -> pl.DataFrame:
    """Decision rows for a setup family: the family's trigger AND the baseline rule (signal components switchable).
    Adds `family`, `trigger_level` (the level the trade is built on, when any), `target_price` (bounces) and the
    family's `invalidation_level`."""
    p = {**BASELINE, **FAMILY_DEFAULTS.get(family, {}), **(params or {})}
    if family == 'quick_scalps':
        return baseline_events(feat, p).with_columns(pl.lit(family).alias('family'))
    base = baseline_events(feat, p)
    if base.height == 0: return base.with_columns(pl.lit(family).alias('family'))
    f = feat
    if family == 'trend_plays':
        # 15m trend stack and a pullback that touched EMA 9 or EMA 20 (15m) within the last N completed 15m bars
        df15 = bars.resample(df1 if df1 is not None else feat, 15)
        a = bars.with_session_arrays(df15)
        e9 = ind.ema(a['close'], p['ema_lead']); e20 = ind.ema(a['close'], p['ema_mid']); e50 = ind.ema(a['close'], p['ema_slow']); e200 = ind.ema(a['close'], p['ema_long'])
        touch_up = (a['low'] <= np.maximum(e9, e20)) & (a['close'] > e20)  # dipped into the EMA band, closed above
        touch_dn = (a['high'] >= np.minimum(e9, e20)) & (a['close'] < e20)
        N = p['pullback_bars_15m']
        def recent(x):
            out = np.zeros_like(x, bool)
            for k in range(N): out[k:] |= x[:x.size - k] if k else x
            return out
        t15 = df15.select(['close_ts']).with_columns([pl.Series('stack_up', (e20 > e50) & (e50 > e200)), pl.Series('stack_dn', (e20 < e50) & (e50 < e200)),
                                                       pl.Series('pull_up', recent(touch_up)), pl.Series('pull_dn', recent(touch_dn))])
        base = bars.align_closed(base, t15, ['stack_up', 'stack_dn', 'pull_up', 'pull_dn'], '')
        ok = ((pl.col('direction') > 0) & pl.col('stack_up') & pl.col('pull_up')) | ((pl.col('direction') < 0) & pl.col('stack_dn') & pl.col('pull_dn'))
        out = base.filter(ok.fill_null(False)).with_columns(pl.when(pl.col('direction') > 0).then(pl.col('ema_slow_15m')).otherwise(pl.col('ema_slow_15m')).alias('invalidation_level'))
        return out.with_columns(pl.lit(family).alias('family'))
    if family == 'breakouts':
        df5 = bars.resample(df1 if df1 is not None else feat, 5)
        a = bars.with_session_arrays(df5)
        R = p['range_bars_5m']
        hi_prev = pl.Series(a['high']).shift(1).rolling_max(R).to_numpy(); lo_prev = pl.Series(a['low']).shift(1).rolling_min(R).to_numpy()
        t5 = df5.select(['close_ts']).with_columns([pl.Series('range_hi', hi_prev), pl.Series('range_lo', lo_prev), pl.Series('close5', a['close'])])
        lv = _daily_levels(df1 if df1 is not None else feat)
        b = bars.align_closed(base, t5, ['range_hi', 'range_lo', 'close5'], '').join(lv, on='session', how='left')
        up = (pl.col('direction') > 0) & ((pl.col('close5') > pl.col('prev_high')) | (pl.col('close5') > pl.col('range_hi')))
        dn = (pl.col('direction') < 0) & ((pl.col('close5') < pl.col('prev_low')) | (pl.col('close5') < pl.col('range_lo')))
        out = b.filter((up | dn).fill_null(False))
        out = out.with_columns([pl.when(pl.col('direction') > 0).then(pl.max_horizontal('prev_high', 'range_hi')).otherwise(pl.min_horizontal('prev_low', 'range_lo')).alias('trigger_level')])
        # invalidation: back inside the range (the broken level); target: range height projected
        out = out.with_columns([pl.col('trigger_level').alias('invalidation_level'),
                                pl.when(pl.col('direction') > 0).then(pl.col('trigger_level') + (pl.col('range_hi') - pl.col('range_lo'))).otherwise(pl.col('trigger_level') - (pl.col('range_hi') - pl.col('range_lo'))).alias('target_price')])
        return out.with_columns(pl.lit(family).alias('family'))
    if family == 'bounces':
        lv = _daily_levels(df1 if df1 is not None else feat)
        close = f['close'].to_numpy(); W = p['z_window']
        s = pl.Series(close); mu = s.rolling_mean(W).to_numpy(); sd = s.rolling_std(W).to_numpy()
        with np.errstate(invalid='ignore', divide='ignore'): z = (close - mu) / sd
        low5 = pl.Series(f['low'].to_numpy()).rolling_min(p['touch_bars']).to_numpy(); high5 = pl.Series(f['high'].to_numpy()).rolling_max(p['touch_bars']).to_numpy()
        ff = f.with_columns([pl.Series('z', z), pl.Series('low_touch', low5), pl.Series('high_touch', high5)]).join(lv, on='session', how='left')
        ff = ff.with_columns([(pl.col('vwap') - 2 * pl.col('vwap_sigma')).alias('vwap_lo'), (pl.col('vwap') + 2 * pl.col('vwap_sigma')).alias('vwap_hi')])
        # the level touched (calls: a support below; puts: a resistance above)
        sup = pl.max_horizontal(*[pl.when(pl.col('low_touch') <= pl.col(c)).then(pl.col(c)).otherwise(None) for c in ('prev_low', 'low_20d', 'vwap_lo')])
        res = pl.min_horizontal(*[pl.when(pl.col('high_touch') >= pl.col(c)).then(pl.col(c)).otherwise(None) for c in ('prev_high', 'high_20d', 'vwap_hi')])
        ff = ff.with_columns([sup.alias('support'), res.alias('resistance')])
        keep = ['close_ts', 'z', 'support', 'resistance', 'atr']
        b = base.join(ff.select(keep).rename({'atr': 'atr1'}), on='close_ts', how='left')
        up = (pl.col('direction') > 0) & (pl.col('z') <= -p['z_threshold']) & pl.col('support').is_not_null()
        dn = (pl.col('direction') < 0) & (pl.col('z') >= p['z_threshold']) & pl.col('resistance').is_not_null()
        out = b.filter((up | dn).fill_null(False))
        out = out.with_columns([pl.when(pl.col('direction') > 0).then(pl.col('support')).otherwise(pl.col('resistance')).alias('trigger_level')])
        out = out.with_columns([pl.when(pl.col('direction') > 0).then(pl.col('trigger_level') - p['beta_atr'] * pl.col('atr1')).otherwise(pl.col('trigger_level') + p['beta_atr'] * pl.col('atr1')).alias('invalidation_level'),
                                pl.when(pl.col('direction') > 0).then(pl.col('trigger_level') + p['alpha_atr'] * pl.col('atr1')).otherwise(pl.col('trigger_level') - p['alpha_atr'] * pl.col('atr1')).alias('target_price')])
        return out.with_columns(pl.lit(family).alias('family'))
    raise ValueError(family)
