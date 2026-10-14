"""Signal screen on the underlying (04_protocol.md §13; the owner's 'use the underlying history to identify candidate
effects'): for an entry trigger, the signed underlying return after the decision bar at several horizons, against
random minutes matched by symbol, date and direction. A trigger earns an option test only when its day-clustered lower
bound beats the random control by more than the cost hurdle (about 3 bp over 30-60 minutes on SPY-class names).

Triggers (each in both directions, decision at the close of the 1-minute bar, entry window applied):
  rsi_cross       the owner's lead: RSI(14) crosses 55 up / 45 down with the close beyond EMA 9
  vwap_reclaim    1-minute close crosses the session VWAP (up for calls, down for puts)
  ema_cross_5m    EMA 9 crosses EMA 20 on completed 5-minute bars
  breakout_5m     a 5-minute close through the prior session's high/low or the 20-bar range (first break only)
  retest_5m       after a breakout, price returns to the broken level within 12 five-minute bars and closes beyond it again
  trend_pullback  15-minute EMA 20 > 50 > 200 (or reversed), a touch of the EMA 9/20 band within the last three 15-minute
                  bars, and a 5-minute close back beyond EMA 20 (5m)
  bounce          displacement z <= -2 (>= +2) over 60 bars, a touch of a support (resistance) level within 5 bars, and a
                  reversal 1-minute bar
Filters (switchable, measured as ablations): confirm_5m, align_15m, relvol, structure — the baseline's.
"""
from __future__ import annotations
import datetime as dt
import json, os
import numpy as np
import polars as pl
from . import bars, indicators as ind, signals, stats

HORIZONS = (5, 15, 30, 60)
TRIGGERS = ('rsi_cross', 'vwap_reclaim', 'ema_cross_5m', 'breakout_5m', 'retest_5m', 'trend_pullback', 'bounce')

def _same_session_prev(feat: pl.DataFrame) -> np.ndarray:
    s = feat['session'].cast(pl.Int32).to_numpy(); return np.concatenate(([False], s[1:] == s[:-1]))

def _tf(feat_or_df1: pl.DataFrame, minutes: int) -> pl.DataFrame:
    return bars.resample(feat_or_df1, minutes)

def trigger_direction(feat: pl.DataFrame, trigger: str, df1: pl.DataFrame, p: dict) -> np.ndarray:
    """+1/-1/0 per 1-minute bar."""
    n = feat.height; close = feat['close'].to_numpy(); same = _same_session_prev(feat)
    prev_close = np.roll(close, 1)
    if trigger == 'rsi_cross':
        rsi = feat['rsi'].to_numpy(); prev = np.roll(rsi, 1)
        up = (prev <= p['rsi_up']) & (rsi > p['rsi_up']) & same & (close > feat['ema_lead'].to_numpy())
        dn = (prev >= p['rsi_down']) & (rsi < p['rsi_down']) & same & (close < feat['ema_lead'].to_numpy())
        return np.where(up, 1, np.where(dn, -1, 0))
    if trigger == 'vwap_reclaim':
        v = feat['vwap'].to_numpy(); pv = np.roll(v, 1)
        up = (prev_close <= pv) & (close > v) & same; dn = (prev_close >= pv) & (close < v) & same
        return np.where(up, 1, np.where(dn, -1, 0))
    if trigger == 'ema_cross_5m':
        d5 = _tf(df1, 5); a = bars.with_session_arrays(d5)
        e9 = ind.ema(a['close'], p['ema_lead']); e20 = ind.ema(a['close'], p['ema_mid'])
        x_up = np.concatenate(([False], (e9[1:] > e20[1:]) & (e9[:-1] <= e20[:-1]))); x_dn = np.concatenate(([False], (e9[1:] < e20[1:]) & (e9[:-1] >= e20[:-1])))
        t = d5.select(['close_ts']).with_columns([pl.Series('xu', x_up), pl.Series('xd', x_dn)])
        j = feat.select(['close_ts']).join(t, on='close_ts', how='left')  # exact: fires on the 1m bar that closes the 5m bar
        return np.where(j['xu'].fill_null(False).to_numpy(), 1, np.where(j['xd'].fill_null(False).to_numpy(), -1, 0))
    if trigger in ('breakout_5m', 'retest_5m'):
        d5 = _tf(df1, 5); a = bars.with_session_arrays(d5)
        hi = pl.Series(a['high']).shift(1).rolling_max(p.get('range_bars_5m', 20)).to_numpy(); lo = pl.Series(a['low']).shift(1).rolling_min(p.get('range_bars_5m', 20)).to_numpy()
        lv = signals._daily_levels(df1)
        d5 = d5.join(lv, on='session', how='left')
        ph = d5['prev_high'].to_numpy(); plo = d5['prev_low'].to_numpy()
        lvl_up = np.fmax(hi, ph); lvl_dn = np.fmin(lo, plo)
        c5 = a['close']; pc5 = np.roll(c5, 1); s5 = a['session']; same5 = np.concatenate(([False], s5[1:] == s5[:-1]))
        with np.errstate(invalid='ignore'):
            b_up = (c5 > lvl_up) & (pc5 <= np.roll(lvl_up, 1)) & same5; b_dn = (c5 < lvl_dn) & (pc5 >= np.roll(lvl_dn, 1)) & same5
        if trigger == 'breakout_5m':
            t = d5.select(['close_ts']).with_columns([pl.Series('u', b_up), pl.Series('d', b_dn)])
        else:
            # retest within 12 bars: the low comes back to the broken level (within 0.05%) and the close is beyond it
            K = 12; r_up = np.zeros(c5.size, bool); r_dn = np.zeros(c5.size, bool)
            for i in np.flatnonzero(b_up):
                L = lvl_up[i]
                for k in range(i + 1, min(i + 1 + K, c5.size)):
                    if s5[k] != s5[i]: break
                    if a['low'][k] <= L * 1.0005 and c5[k] > L: r_up[k] = True; break
            for i in np.flatnonzero(b_dn):
                L = lvl_dn[i]
                for k in range(i + 1, min(i + 1 + K, c5.size)):
                    if s5[k] != s5[i]: break
                    if a['high'][k] >= L * 0.9995 and c5[k] < L: r_dn[k] = True; break
            t = d5.select(['close_ts']).with_columns([pl.Series('u', r_up), pl.Series('d', r_dn)])
        j = feat.select(['close_ts']).join(t, on='close_ts', how='left')
        return np.where(j['u'].fill_null(False).to_numpy(), 1, np.where(j['d'].fill_null(False).to_numpy(), -1, 0))
    if trigger == 'trend_pullback':
        d15 = _tf(df1, 15); a = bars.with_session_arrays(d15)
        e9 = ind.ema(a['close'], p['ema_lead']); e20 = ind.ema(a['close'], p['ema_mid']); e50 = ind.ema(a['close'], p['ema_slow']); e200 = ind.ema(a['close'], p['ema_long'])
        su = (e20 > e50) & (e50 > e200); sd = (e20 < e50) & (e50 < e200)
        tu = (a['low'] <= np.maximum(e9, e20)); td = (a['high'] >= np.minimum(e9, e20))
        def recent(x, N=3):
            out = x.copy()
            for k in range(1, N): out[k:] |= x[:-k]
            return out
        t15 = d15.select(['close_ts']).with_columns([pl.Series('su', su), pl.Series('sd', sd), pl.Series('pu', recent(tu)), pl.Series('pd', recent(td))])
        f = bars.align_closed(feat.select(['close_ts', 'close_5m', 'ema_mid_5m']), t15, ['su', 'sd', 'pu', 'pd'], '')
        c5 = f['close_5m'].to_numpy(); e205 = f['ema_mid_5m'].to_numpy(); pc = np.roll(c5, 1); pe = np.roll(e205, 1)
        with np.errstate(invalid='ignore'):
            up = f['su'].fill_null(False).to_numpy() & f['pu'].fill_null(False).to_numpy() & (c5 > e205) & (pc <= pe) & same
            dn = f['sd'].fill_null(False).to_numpy() & f['pd'].fill_null(False).to_numpy() & (c5 < e205) & (pc >= pe) & same
        return np.where(up, 1, np.where(dn, -1, 0))
    if trigger == 'bounce':
        W = p.get('z_window', 60); s = pl.Series(close); mu = s.rolling_mean(W).to_numpy(); sd = s.rolling_std(W).to_numpy()
        with np.errstate(invalid='ignore', divide='ignore'): z = (close - mu) / sd
        lv = signals._daily_levels(df1); f = feat.select(['session', 'low', 'high', 'open', 'vwap', 'vwap_sigma']).join(lv, on='session', how='left')
        low5 = pl.Series(feat['low'].to_numpy()).rolling_min(5).to_numpy(); high5 = pl.Series(feat['high'].to_numpy()).rolling_max(5).to_numpy()
        vlo = (f['vwap'] - 2 * f['vwap_sigma']).to_numpy(); vhi = (f['vwap'] + 2 * f['vwap_sigma']).to_numpy()
        with np.errstate(invalid='ignore'):
            touch_sup = (low5 <= f['prev_low'].to_numpy()) | (low5 <= f['low_20d'].to_numpy()) | (low5 <= vlo)
            touch_res = (high5 >= f['prev_high'].to_numpy()) | (high5 >= f['high_20d'].to_numpy()) | (high5 >= vhi)
            rev_up = (close > feat['open'].to_numpy()) & (close > prev_close); rev_dn = (close < feat['open'].to_numpy()) & (close < prev_close)
            up = (z <= -p.get('z_threshold', 2.0)) & touch_sup & rev_up & same; dn = (z >= p.get('z_threshold', 2.0)) & touch_res & rev_dn & same
        return np.where(up, 1, np.where(dn, -1, 0))
    raise ValueError(trigger)

def filter_mask(feat: pl.DataFrame, direction: np.ndarray, use: dict, p: dict) -> np.ndarray:
    close = feat['close'].to_numpy(); ok = np.ones(feat.height, bool)
    if use.get('confirm_5m'):
        c5 = feat['close_5m'].to_numpy(); e = feat['ema_mid_5m'].to_numpy(); v = feat['vwap'].to_numpy()
        with np.errstate(invalid='ignore'): ok &= np.where(direction > 0, (c5 > e) & (close > v), (c5 < e) & (close < v))
    if use.get('align_15m'):
        a = feat['ema_mid_15m'].to_numpy(); b = feat['ema_slow_15m'].to_numpy(); c = feat['close_15m'].to_numpy()
        with np.errstate(invalid='ignore'): ok &= np.where(direction > 0, (a > b) & (c > a), (a < b) & (c < a))
    if use.get('relvol'):
        with np.errstate(invalid='ignore'): ok &= feat['relvol'].to_numpy() >= p['relvol_min']
    if use.get('structure'):
        st = feat['struct_5m'].to_numpy(); ok &= np.where(direction > 0, st == 1, st == -1)
    return ok

def forward_returns(feat: pl.DataFrame, idx: np.ndarray, direction: np.ndarray) -> dict:
    close = feat['close'].to_numpy(); sess = feat['session'].cast(pl.Int32).to_numpy(); n = close.size
    out = {}
    for h in HORIZONS:
        j = np.minimum(idx + h, n - 1); same = sess[j] == sess[idx]
        out[f'fwd_{h}m_bp'] = np.where(same, (close[j] / close[idx] - 1) * 1e4 * direction, np.nan)
    for h in (15, 30):
        j = np.maximum(idx - h, 0); same = sess[j] == sess[idx]
        out[f'pre_{h}m_bp'] = np.where(same, (close[idx] / close[j] - 1) * 1e4 * direction, np.nan)
    last = {}
    for i in range(n - 1, -1, -1): last.setdefault(sess[i], i)
    jc = np.array([last[s] for s in sess[idx]]) if idx.size else np.zeros(0, int)
    out['fwd_close_bp'] = (close[jc] / close[idx] - 1) * 1e4 * direction if idx.size else np.zeros(0)
    return out

FILTER_SETS = {'raw': {}, 'baseline_filters': {'confirm_5m': True, 'align_15m': True, 'relvol': True, 'structure': True}, 'confirm_5m': {'confirm_5m': True}, 'align_15m': {'align_15m': True}}

def screen_symbol(symbol: str, df1: pl.DataFrame, triggers=TRIGGERS, filter_sets=FILTER_SETS, params: dict | None = None, seeds=(11, 12, 13, 14, 15), entry=(15, 320)) -> list[dict]:
    p = {**signals.BASELINE, **(params or {})}
    feat = signals.features(df1, p)
    minute = feat['minute'].to_numpy(); sess_i = feat['session'].cast(pl.Int32).to_numpy(); days_all = feat['session'].cast(pl.Utf8).to_numpy()
    window = (minute >= entry[0]) & (minute <= entry[1])
    by_sess = {}
    for i in np.flatnonzero(window): by_sess.setdefault(sess_i[i], []).append(i)
    rows = []
    for trig in triggers:
        d0 = trigger_direction(feat, trig, df1, p)
        for fname, use in filter_sets.items():
            direction = np.where(window & filter_mask(feat, d0, use, p), d0, 0)
            idx = np.flatnonzero(direction != 0)
            if idx.size < 50: rows.append({'symbol': symbol, 'trigger': trig, 'filters': fname, 'n': int(idx.size)}); continue
            dirn = direction[idx]; days = days_all[idx]
            fr = forward_returns(feat, idx, dirn)
            rec = {'symbol': symbol, 'trigger': trig, 'filters': fname, 'n': int(idx.size), 'days': int(np.unique(days).size), 'calls_share': float((dirn > 0).mean())}
            for k, v in fr.items():
                ok = np.isfinite(v); m, lo, hi = stats.cluster_bootstrap_ci(v[ok], days[ok], n_boot=1000); rec[k] = m; rec[k + '_lo'] = lo; rec[k + '_hi'] = hi
            rec['hit_30m'] = float((fr['fwd_30m_bp'][np.isfinite(fr['fwd_30m_bp'])] > 0).mean())
            # matched random minutes, same session and direction; paired difference at 30 and 60 min
            diffs30 = []; diffs60 = []; rand30 = []
            for seed in seeds:
                rng = np.random.default_rng(seed)
                ridx = np.array([by_sess[s][rng.integers(0, len(by_sess[s]))] for s in sess_i[idx]])
                rr = forward_returns(feat, ridx, dirn)
                diffs30.append(fr['fwd_30m_bp'] - rr['fwd_30m_bp']); diffs60.append(fr['fwd_60m_bp'] - rr['fwd_60m_bp']); rand30.append(np.nanmean(rr['fwd_30m_bp']))
            d30 = np.nanmean(np.vstack(diffs30), axis=0); d60 = np.nanmean(np.vstack(diffs60), axis=0)
            ok = np.isfinite(d30); m, lo, hi = stats.cluster_bootstrap_ci(d30[ok], days[ok], n_boot=1000); rec.update({'vs_random_30m_bp': m, 'vs_random_30m_lo': lo, 'vs_random_30m_hi': hi, 'random_30m_bp': float(np.mean(rand30))})
            ok = np.isfinite(d60); m, lo, hi = stats.cluster_bootstrap_ci(d60[ok], days[ok], n_boot=1000); rec.update({'vs_random_60m_bp': m, 'vs_random_60m_lo': lo, 'vs_random_60m_hi': hi})
            # by year (30-minute, vs random)
            years = np.array([int(x[:4]) for x in days]); rec['by_year_vs_random_30m'] = {int(y): round(float(np.nanmean(d30[years == y])), 2) for y in np.unique(years)}
            rows.append(rec)
    return rows

def run(symbols: list[str], loader, out_dir: str, log=print, **kw) -> pl.DataFrame:
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for sym in symbols:
        df1 = loader(sym)
        if df1 is None or df1.height < 390 * 60: log(f'{sym}: insufficient bars'); continue
        r = screen_symbol(sym, df1, **kw); rows += r
        log(f'{sym}: {len(r)} rows; raw rsi_cross vs random 30m = {next((x.get("vs_random_30m_bp") for x in r if x["trigger"] == "rsi_cross" and x["filters"] == "raw"), None)}')
        json.dump(rows, open(os.path.join(out_dir, 'rows.json'), 'w'), indent=1, default=str)
    tab = pl.DataFrame([{k: v for k, v in r.items() if k != 'by_year_vs_random_30m'} for r in rows], infer_schema_length=None)
    tab.write_csv(os.path.join(out_dir, 'table.csv'))
    return tab
