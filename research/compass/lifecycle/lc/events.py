"""Setup events on an index product's 1-minute bars (lifecycle protocol §3). An event is a decision at the close of a
1-minute bar: (session, m = the instant's minute index, direction, setup, invalidation, target, spot).

QS, TP, BO, BN are the engine's families (engine/signals.py: the family trigger AND the S01 baseline rule). BOF, BNF,
LS, MSS, FVG are pattern triggers on their own (no RSI gate), defined here; every level they read is known at the
decision (prior session's high/low, the 09:30-10:00 range once 10:00 has passed, completed 5-minute bars, confirmed
swings). Events are kept inside the entry window (09:45 to 15:00 by default)."""
from __future__ import annotations
import datetime as dt, os, sys
import numpy as np
import polars as pl
from . import paths
sys.path.insert(0, os.path.dirname(paths.HERE))
from engine import bars, indicators as ind, signals  # noqa: E402

WINDOW = (15, 330)            # 09:45 .. 15:00 (minute index of the decision instant)
SWEEP_PCT = 0.0003

def _m_of(close_ts: pl.Series, session: pl.Series) -> np.ndarray:
    ct = close_ts.dt.replace_time_zone(None).cast(pl.Datetime('ms')).to_numpy().astype('datetime64[m]')
    op = np.array([np.datetime64(dt.datetime.combine(d, dt.time(9, 30)), 'm') for d in session.to_list()])
    return (ct - op).astype(int)

def _rows(df: pl.DataFrame, setup: str) -> pl.DataFrame:
    if df.height == 0:
        return pl.DataFrame(schema={'session': pl.Date, 'm': pl.Int64, 'direction': pl.Int64, 'setup': pl.Utf8, 'inv': pl.Float64, 'target': pl.Float64, 'spot': pl.Float64})
    m = _m_of(df['close_ts'], df['session'])
    out = pl.DataFrame({'session': df['session'], 'm': m, 'direction': df['direction'].cast(pl.Int64), 'setup': [setup] * df.height,
                        'inv': df['inv'].cast(pl.Float64) if 'inv' in df.columns else pl.Series([None] * df.height, dtype=pl.Float64),
                        'target': df['target'].cast(pl.Float64) if 'target' in df.columns else pl.Series([None] * df.height, dtype=pl.Float64),
                        'spot': df['close'].cast(pl.Float64)})
    return out.filter((pl.col('m') >= WINDOW[0]) & (pl.col('m') <= WINDOW[1]))

def engine_families(feat: pl.DataFrame, df1: pl.DataFrame) -> list[pl.DataFrame]:
    out = []
    p = {'entry_start_minute': 0, 'entry_end_minute': 390}
    qs = signals.family_events(feat, 'quick_scalps', p, df1)
    out.append(_rows(qs.with_columns(pl.lit(None, dtype=pl.Float64).alias('inv'), pl.lit(None, dtype=pl.Float64).alias('target')), 'QS'))
    for fam, code in [('trend_plays', 'TP'), ('breakouts', 'BO'), ('bounces', 'BN')]:
        e = signals.family_events(feat, fam, p, df1)
        if e.height == 0: out.append(_rows(e, code)); continue
        e = e.with_columns(pl.col('invalidation_level').alias('inv'), (pl.col('target_price') if 'target_price' in e.columns else pl.lit(None, dtype=pl.Float64)).alias('target'))
        out.append(_rows(e, code))
    return out

def _five(df1: pl.DataFrame) -> pl.DataFrame:
    d5 = bars.resample(df1, 5)
    a = bars.with_session_arrays(d5)
    return d5.with_columns(pl.Series('atr5', ind.atr(a['high'], a['low'], a['close'], 14)))

def pattern_events(df1: pl.DataFrame, feat: pl.DataFrame) -> list[pl.DataFrame]:
    """BOF, LS, MSS, FVG (BNF is built from BN in `failed_bounces`)."""
    d5 = _five(df1)
    lv = signals._daily_levels(df1)
    sess = df1['session'].to_numpy(); hi1 = df1['high'].to_numpy(); lo1 = df1['low'].to_numpy(); cl1 = df1['close'].to_numpy(); mi1 = df1['minute'].to_numpy()
    ct1 = df1['close_ts'].to_numpy()
    s5 = d5['session'].to_numpy(); o5 = d5['open'].to_numpy(); h5 = d5['high'].to_numpy(); l5 = d5['low'].to_numpy(); c5 = d5['close'].to_numpy()
    ct5 = d5['close_ts'].to_numpy(); m5 = d5['minute'].to_numpy(); atr5 = d5['atr5'].to_numpy()
    lvd = {np.datetime64(r['session'], 'D'): r for r in lv.iter_rows(named=True)}
    # swing levels (confirmed) on 5-minute bars, as the feature frame carries them at each 1m close
    sw = feat.select(['close_ts', 'swing_hi_5m', 'swing_lo_5m']).to_dict(as_series=False)
    swd = dict(zip(feat['close_ts'].cast(pl.Datetime('ms')).to_numpy().astype('datetime64[ms]').tolist(), zip(sw['swing_hi_5m'], sw['swing_lo_5m'])))
    rows = {'BOF': [], 'LS': [], 'MSS': [], 'FVG': []}
    sessions = np.unique(s5)
    # index ranges per session
    i5 = {s: np.where(s5 == s)[0] for s in sessions}
    i1 = {s: np.where(sess == s)[0] for s in sessions}
    for s in sessions:
        L = lvd.get(s)
        if L is None or L['prev_high'] is None: continue
        b5 = i5[s]; b1 = i1[s]
        if b5.size < 8 or b1.size < 60: continue
        # opening range 09:30-10:00 (known from the 10:00 instant)
        orh = hi1[b1[:30]].max(); orl = lo1[b1[:30]].min()
        # ---- BOF: first 5m close beyond the prior-session level or the 20-bar 5m range, then a 5m close back inside within 3 bars
        hh = pl.Series(h5).shift(1).rolling_max(20).to_numpy(); ll = pl.Series(l5).shift(1).rolling_min(20).to_numpy()
        for side in (+1, -1):
            for k, j in enumerate(b5):
                lvl = max(L['prev_high'], hh[j]) if side > 0 else min(L['prev_low'], ll[j])
                if not np.isfinite(lvl): continue
                broke = c5[j] > lvl if side > 0 else c5[j] < lvl
                if not broke: continue
                ext = h5[j] if side > 0 else l5[j]
                for jj in b5[k + 1:k + 4]:
                    ext = max(ext, h5[jj]) if side > 0 else min(ext, l5[jj])
                    back = c5[jj] < lvl if side > 0 else c5[jj] > lvl
                    if back:
                        rows['BOF'].append((s, ct5[jj], -side, ext, lvl, c5[jj])); break
                break                                          # first break per side per session only
        # ---- LS: a sweep of the prior-session high/low or the opening range (after 10:00), then a 5m close back inside
        levels = [(L['prev_high'], +1, 0), (L['prev_low'], -1, 0), (orh, +1, 30), (orl, -1, 30)]
        ls_events = []
        for lvl, side, start_m in levels:
            swept_at = -1; ext = np.nan
            for idx in b1:
                if mi1[idx] < max(start_m, 1): continue
                if side > 0 and hi1[idx] > lvl * (1 + SWEEP_PCT): swept_at = idx; ext = hi1[idx]; break
                if side < 0 and lo1[idx] < lvl * (1 - SWEEP_PCT): swept_at = idx; ext = lo1[idx]; break
            if swept_at < 0: continue
            sm = mi1[swept_at]
            cands = [j for j in b5 if m5[j] + 5 > sm][:4]        # the 5m bar holding the sweep and the next three
            for j in cands:
                # extend the extreme with the 1m bars up to this 5m close
                seg = b1[(mi1[b1] >= sm) & (mi1[b1] < m5[j] + 5)]
                ext = hi1[seg].max() if side > 0 else lo1[seg].min()
                back = c5[j] < lvl if side > 0 else c5[j] > lvl
                if back:
                    rows['LS'].append((s, ct5[j], -side, ext, lvl, c5[j])); ls_events.append((ct5[j], -side, ext)); break
        # ---- MSS: within 30 minutes after an LS, a 5m close beyond the most recent confirmed 5m swing in the LS direction
        for t_ls, d, ext in ls_events:
            for j in b5:
                if ct5[j] <= t_ls: continue
                if (ct5[j] - t_ls) > np.timedelta64(30, 'm'): break
                shl = swd.get(ct5[j].astype('datetime64[ms]').tolist())
                if shl is None: continue
                sh, slw = shl
                if d > 0 and sh is not None and np.isfinite(sh) and c5[j] > sh:
                    rows['MSS'].append((s, ct5[j], d, ext, sh, c5[j])); break
                if d < 0 and slw is not None and np.isfinite(slw) and c5[j] < slw:
                    rows['MSS'].append((s, ct5[j], d, ext, slw, c5[j])); break
        # ---- FVG: a displacement 5m bar leaving a three-bar gap; entry when a 1m bar trades back into the gap within 60 min
        for k in range(2, b5.size):
            j = b5[k]; jm = b5[k - 1]; j2 = b5[k - 2]
            if not np.isfinite(atr5[jm]) or (h5[jm] - l5[jm]) < 1.5 * atr5[jm]: continue
            if l5[j] > h5[j2] and c5[jm] > o5[jm]:   side, top, bot = +1, l5[j], h5[j2]
            elif h5[j] < l5[j2] and c5[jm] < o5[jm]: side, top, bot = -1, l5[j2], h5[j]   # bearish gap: (h5[j], l5[j2])
            else: continue
            t_end = ct5[j] + np.timedelta64(60, 'm')
            for idx in b1:
                if ct1[idx] <= ct5[j]: continue
                if ct1[idx] > t_end: break
                if side > 0 and lo1[idx] <= top:
                    if cl1[idx] > bot: rows['FVG'].append((s, ct1[idx], +1, bot, top, cl1[idx]))
                    break
                if side < 0 and hi1[idx] >= bot:
                    if cl1[idx] < top: rows['FVG'].append((s, ct1[idx], -1, top, bot, cl1[idx]))
                    break
    out = []
    for code, rr in rows.items():
        if not rr: out.append(_rows(pl.DataFrame(), code)); continue
        rr = [(x[0].astype('datetime64[D]').tolist(), x[1].astype('datetime64[ms]').tolist(), int(x[2]), float(x[3]), float(x[4]), float(x[5])) for x in rr]
        df = pl.DataFrame(rr, schema={'session': pl.Date, 'close_ts': pl.Datetime('ms'), 'direction': pl.Int64, 'inv': pl.Float64, 'level': pl.Float64, 'close': pl.Float64}, orient='row')
        df = df.with_columns(pl.lit(None, dtype=pl.Float64).alias('target'))
        out.append(_rows(df, code))
    return out

def failed_bounces(bn: pl.DataFrame, df1: pl.DataFrame) -> pl.DataFrame:
    """BNF: a BN event whose 5m close crosses its invalidation level within 6 five-minute bars -> the original move's
    direction (opposite of the bounce), invalidation the extreme reached since the bounce event."""
    if bn.height == 0: return bn.with_columns(pl.lit('BNF').alias('setup'))
    d5 = bars.resample(df1, 5)
    out = []
    by = {s: g for (s,), g in d5.group_by(['session'], maintain_order=True)}
    for r in bn.iter_rows(named=True):
        g = by.get(r['session'])
        if g is None or r['inv'] is None: continue
        mm = g['minute'].to_numpy() + 5                     # instant of each 5m close
        c = g['close'].to_numpy(); h = g['high'].to_numpy(); l = g['low'].to_numpy()
        after = np.where(mm > r['m'])[0][:6]
        ext = -np.inf if r['direction'] > 0 else np.inf
        for j in after:
            ext = max(ext, h[j]) if r['direction'] > 0 else min(ext, l[j])
            crossed = c[j] < r['inv'] if r['direction'] > 0 else c[j] > r['inv']
            if crossed:
                out.append((r['session'], int(mm[j]), -r['direction'], 'BNF', float(ext), None, float(c[j]))); break
    if not out: return pl.DataFrame(schema=bn.schema)
    df = pl.DataFrame(out, schema=['session', 'm', 'direction', 'setup', 'inv', 'target', 'spot'], orient='row')
    return df.with_columns(pl.col('m').cast(pl.Int64), pl.col('direction').cast(pl.Int64), pl.col('target').cast(pl.Float64)).filter((pl.col('m') >= WINDOW[0]) & (pl.col('m') <= WINDOW[1]))

PURE = {'TPp': 'trend_pullback', 'BOp': 'breakout_5m', 'BOr': 'retest_5m', 'BNp': 'bounce', 'VWR': 'vwap_reclaim'}

def pure_triggers(feat: pl.DataFrame, df1: pl.DataFrame) -> list[pl.DataFrame]:
    """The screen's triggers without the baseline RSI gate (engine/screen.py, S06): invalidation the last confirmed 5m
    swing against the trade (swing low for calls, swing high for puts)."""
    from engine import screen
    p = {**signals.BASELINE, **signals.FAMILY_DEFAULTS['bounces']}
    out = []
    for code, trig in PURE.items():
        d = screen.trigger_direction(feat, trig, df1, p)
        idx = np.flatnonzero(d != 0)
        f = feat[idx].with_columns(pl.Series('direction', d[idx]))
        f = f.with_columns(pl.when(pl.col('direction') > 0).then(pl.col('swing_lo_5m')).otherwise(pl.col('swing_hi_5m')).alias('inv'),
                           pl.lit(None, dtype=pl.Float64).alias('target'))
        out.append(_rows(f, code))
    return out

def all_events(store, root: str, start: dt.date, end: dt.date) -> pl.DataFrame:
    from .aux import feature_frame
    from engine import calendar as cal
    warm = cal.prev_session(start, 40)
    df1 = store.bars(root, warm, end)
    feat = feature_frame(store, root, start, end)
    parts = engine_families(feat, df1) + pattern_events(df1, feat) + pure_triggers(feat, df1)
    ev = pl.concat([p for p in parts if p.height], how='vertical_relaxed')
    bn = ev.filter(pl.col('setup') == 'BN')
    bnf = failed_bounces(bn, df1)
    if bnf.height: ev = pl.concat([ev, bnf.select(ev.columns)], how='vertical_relaxed')
    ev = ev.filter((pl.col('session') >= start) & (pl.col('session') <= end)).with_columns(pl.lit(root).alias('root'))
    return ev.sort(['session', 'm', 'setup'])
