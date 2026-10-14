"""Daily-resolution trigger screen on the stock EOD lake (04_protocol.md amendment A2): for each trigger at the daily
close, the signed forward return from the next session's open at 1/5/10/21 sessions, absolute and adjusted for the
same-date universe mean, with CIs clustered by event date. Selects daily triggers for the Weekly / Swing / Position
expiration categories; produces no option result."""
from __future__ import annotations
import datetime as dt
import glob, json, os
import numpy as np
import polars as pl
from . import stats

HORIZONS = (1, 5, 10, 21)
TRIGGERS = ('gap_cont', 'breakout20', 'reversal5', 'trend_pullback', 'event_shock')
FILTER_SETS = {'raw': {}, 'relvol150': {'relvol_min': 1.5}}

def load_lake(root: str, years: list[int]) -> pl.DataFrame:
    fs = [f for y in years for f in sorted(glob.glob(os.path.join(root, f'year={y}', 'part-*.parquet')))]
    lf = pl.scan_parquet(fs).select(['symbol', 'created', 'open', 'high', 'low', 'close', 'volume'])
    df = lf.with_columns(pl.col('created').dt.date().alias('date')).drop('created').filter(pl.col('close') > 0).collect()
    return df.unique(['symbol', 'date']).sort(['symbol', 'date'])

def universe(df: pl.DataFrame, min_dollar_volume: float = 50e6, min_days: int = 200, min_price: float = 5.0) -> pl.DataFrame:
    """symbol, year -> eligible in `year` by the prior calendar year's median daily dollar volume (point in time)."""
    g = df.with_columns((pl.col('close') * pl.col('volume')).alias('dv'), pl.col('date').dt.year().alias('y'))
    a = g.group_by(['symbol', 'y']).agg(pl.col('dv').median().alias('mdv'), pl.len().alias('n'), pl.col('close').median().alias('mpx'))
    a = a.filter((pl.col('mdv') >= min_dollar_volume) & (pl.col('n') >= min_days) & (pl.col('mpx') >= min_price))
    return a.select(pl.col('symbol'), (pl.col('y') + 1).alias('year'), 'mdv')

def features(df: pl.DataFrame) -> pl.DataFrame:
    o = pl.col('open'); h = pl.col('high'); l = pl.col('low'); c = pl.col('close'); v = pl.col('volume'); S = 'symbol'
    pc = c.shift(1).over(S)
    tr = pl.max_horizontal(h - l, (h - pc).abs(), (l - pc).abs())
    f = df.with_columns([
        pc.alias('prev_close'), (c / pc - 1).alias('ret'), (o / pc - 1).alias('gap'), tr.alias('tr'),
        c.ewm_mean(span=20, adjust=False).over(S).alias('ema20'), c.ewm_mean(span=50, adjust=False).over(S).alias('ema50'), c.ewm_mean(span=200, adjust=False).over(S).alias('ema200'),
        h.shift(1).rolling_max(20).over(S).alias('hi20'), l.shift(1).rolling_min(20).over(S).alias('lo20'),
        (c / c.shift(5) - 1).over(S).alias('ret5'),
        (v / v.shift(1).rolling_mean(20)).over(S).alias('relvol'),
        pl.int_range(pl.len()).over(S).alias('i'), pl.len().over(S).alias('n_sym'),
    ])
    f = f.with_columns([
        (pl.col('tr').rolling_mean(20) / pl.col('prev_close')).over(S).alias('atr20_pct'),
        pl.col('ret').rolling_std(60).over(S).alias('sigma60'),
        pl.col('low').rolling_min(3).over(S).alias('low3'), pl.col('high').rolling_max(3).over(S).alias('high3'),
        pl.col('ema20').shift(1).over(S).alias('prev_ema20'),
    ])
    # forward: entry at the next open, exit at the close h sessions after the signal day
    f = f.with_columns(pl.col('open').shift(-1).over(S).alias('entry_open'))
    for hz in HORIZONS: f = f.with_columns((pl.col('close').shift(-hz).over(S) / pl.col('entry_open') - 1).alias(f'r{hz}'))
    return f

def trigger_direction(f: pl.DataFrame, trig: str) -> np.ndarray:
    c = f['close'].to_numpy(); o = f['open'].to_numpy(); pc = f['prev_close'].to_numpy(); ret = f['ret'].to_numpy(); gap = f['gap'].to_numpy()
    with np.errstate(invalid='ignore'):
        if trig == 'gap_cont':
            thr = 2 * f['atr20_pct'].to_numpy()
            up = (gap >= thr) & (c > o); dn = (gap <= -thr) & (c < o)
        elif trig == 'breakout20':
            up = c > f['hi20'].to_numpy(); dn = c < f['lo20'].to_numpy()
        elif trig == 'reversal5':
            s = 2 * f['sigma60'].to_numpy() * np.sqrt(5); r5 = f['ret5'].to_numpy()
            up = (r5 <= -s) & (c > pc); dn = (r5 >= s) & (c < pc)
        elif trig == 'trend_pullback':
            e20 = f['ema20'].to_numpy(); e50 = f['ema50'].to_numpy(); e200 = f['ema200'].to_numpy(); pe = f['prev_ema20'].to_numpy()
            up = (c > e50) & (e50 > e200) & (f['low3'].to_numpy() <= e20) & (c > e20) & (pc <= pe)
            dn = (c < e50) & (e50 < e200) & (f['high3'].to_numpy() >= e20) & (c < e20) & (pc >= pe)
        elif trig == 'event_shock':
            s = 2 * f['sigma60'].to_numpy(); rv = f['relvol'].to_numpy()
            up = (rv >= 3) & (ret >= s); dn = (rv >= 3) & (ret <= -s)
        else: raise ValueError(trig)
    return np.where(up, 1, np.where(dn, -1, 0)).astype(np.int8)

def benchmark(f: pl.DataFrame, elig: pl.DataFrame) -> pl.DataFrame:
    """same-date mean forward return (from the next open) over the eligible universe, per horizon"""
    u = f.join(elig, on=['symbol', 'year'], how='semi')
    return u.group_by('date').agg([pl.col(f'r{h}').mean().alias(f'b{h}') for h in HORIZONS] + [pl.len().alias('n_univ')])

def screen(f: pl.DataFrame, elig: pl.DataFrame, triggers=TRIGGERS, filter_sets=FILTER_SETS, min_events: int = 100, log=print) -> list[dict]:
    f = f.with_columns(pl.col('date').dt.year().alias('year'))
    f = f.join(elig, on=['symbol', 'year'], how='semi').filter(pl.col('i') >= 200)  # 200 bars of history for EMA 200 / sigma
    b = benchmark(f, elig)
    f = f.join(b, on='date', how='left')
    log(f'eligible rows {f.height:,} symbols {f["symbol"].n_unique():,} dates {f["date"].n_unique():,}')
    rows = []
    for trig in triggers:
        d0 = trigger_direction(f, trig)
        for fname, use in filter_sets.items():
            d = d0.copy()
            if use.get('relvol_min'):
                with np.errstate(invalid='ignore'): d = np.where(f['relvol'].to_numpy() >= use['relvol_min'], d, 0)
            idx = np.flatnonzero(d != 0)
            if idx.size < min_events: rows.append({'trigger': trig, 'filters': fname, 'n': int(idx.size)}); continue
            ev = f[idx].with_columns(pl.Series('direction', d[idx]))
            days = ev['date'].cast(pl.Utf8).to_numpy(); dirn = ev['direction'].to_numpy()
            rec = {'trigger': trig, 'filters': fname, 'n': int(idx.size), 'days': int(np.unique(days).size), 'symbols': int(ev['symbol'].n_unique()),
                   'calls_share': float((dirn > 0).mean()), 'pre_ret_bp': float(np.nanmean(ev['ret'].to_numpy() * dirn) * 1e4),
                   'entry_gap_bp': float(np.nanmean((ev['entry_open'].to_numpy() / ev['close'].to_numpy() - 1) * dirn) * 1e4)}
            for h in HORIZONS:
                r = ev[f'r{h}'].to_numpy() * dirn * 1e4; bm = ev[f'b{h}'].to_numpy() * dirn * 1e4
                ok = np.isfinite(r) & np.isfinite(bm)
                m, lo, hi = stats.cluster_bootstrap_ci(r[ok], days[ok], n_boot=1000); rec.update({f'abs_{h}d_bp': m, f'abs_{h}d_lo': lo, f'abs_{h}d_hi': hi})
                m, lo, hi = stats.cluster_bootstrap_ci(r[ok] - bm[ok], days[ok], n_boot=1000); rec.update({f'adj_{h}d_bp': m, f'adj_{h}d_lo': lo, f'adj_{h}d_hi': hi})
                if h == 10: rec['hit_10d'] = float((r[ok] > 0).mean())
            r10 = ev['r10'].to_numpy() * dirn * 1e4; b10 = ev['b10'].to_numpy() * dirn * 1e4
            yrs = ev['year'].to_numpy()
            rec['by_year_adj_10d'] = {int(y): round(float(np.nanmean((r10 - b10)[yrs == y])), 1) for y in np.unique(yrs)}
            rec['by_side_adj_10d'] = {'calls': round(float(np.nanmean((r10 - b10)[dirn > 0])), 1), 'puts': round(float(np.nanmean((r10 - b10)[dirn < 0])), 1)}
            rows.append(rec)
            log(f"{trig:15s} {fname:10s} n {idx.size:7d}  abs10 {rec['abs_10d_bp']:+6.1f} [{rec['abs_10d_lo']:+6.1f},{rec['abs_10d_hi']:+6.1f}]  adj10 {rec['adj_10d_bp']:+6.1f} [{rec['adj_10d_lo']:+6.1f},{rec['adj_10d_hi']:+6.1f}]")
    return rows

def report(rows: list[dict], out_dir: str, title: str, hurdle_bp: float = 30.0) -> str:
    f = lambda x, d=0: '' if x is None or x != x else f'{x:+.{d}f}'
    L = [f'# {title}', '', 'Signed return in bp from the next session\'s open to the close h sessions after the signal; adjusted = minus the same-date eligible-universe mean in the trigger\'s direction; CIs clustered by event date (1,000 draws).', '',
         '| trigger | filters | n | days | symbols | calls | signal-day move | overnight gap at entry | +1d abs | +5d abs [CI] | +10d abs [CI] | +21d abs [CI] | +5d adj [CI] | +10d adj [CI] | +21d adj [CI] | hit 10d | promoted |', '|' + '---|' * 17]
    prom = []
    for r in rows:
        if not r.get('days'): L.append(f"| {r['trigger']} | {r['filters']} | {r.get('n', 0)} |" + ' |' * 14); continue
        abs_ok = any(r[f'abs_{h}d_lo'] >= hurdle_bp for h in (5, 10, 21)); adj_ok = any(r[f'adj_{h}d_lo'] > 0 for h in (5, 10, 21))
        p = 'YES' if abs_ok and adj_ok else ('abs only' if abs_ok else ('adj only' if adj_ok else 'no'))
        if abs_ok and adj_ok: prom.append((r['trigger'], r['filters']))
        L.append(f"| {r['trigger']} | {r['filters']} | {r['n']} | {r['days']} | {r['symbols']} | {r['calls_share'] * 100:.0f} % | {f(r['pre_ret_bp'])} | {f(r['entry_gap_bp'])} | {f(r['abs_1d_bp'])} | "
                 + ' | '.join(f"{f(r[f'abs_{h}d_bp'])} [{f(r[f'abs_{h}d_lo'])}, {f(r[f'abs_{h}d_hi'])}]" for h in (5, 10, 21)) + ' | '
                 + ' | '.join(f"**{f(r[f'adj_{h}d_bp'])}** [{f(r[f'adj_{h}d_lo'])}, {f(r[f'adj_{h}d_hi'])}]" for h in (5, 10, 21)) + f" | {r['hit_10d'] * 100:.0f} % | {p} |")
    L += ['', f'Promotion rule (A2): absolute lower bound ≥ +{hurdle_bp:g} bp at 5, 10 or 21 sessions AND adjusted lower bound > 0. Promoted: {prom or "none"}.', '', '## Adjusted 10-session return by year and by side', '']
    years = sorted({y for r in rows for y in (r.get('by_year_adj_10d') or {})})
    L.append('| trigger | filters | ' + ' | '.join(str(y) for y in years) + ' | calls | puts |'); L.append('|---|---|' + '---|' * (len(years) + 2))
    for r in rows:
        if not r.get('days'): continue
        by = r['by_year_adj_10d']; sd = r['by_side_adj_10d']
        L.append(f"| {r['trigger']} | {r['filters']} | " + ' | '.join(f(by.get(y), 1) for y in years) + f" | {f(sd['calls'], 1)} | {f(sd['puts'], 1)} |")
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, 'REPORT.md'), 'w').write('\n'.join(L) + '\n')
    json.dump(rows, open(os.path.join(out_dir, 'rows.json'), 'w'), indent=1, default=str)
    json.dump({'hurdle_bp': hurdle_bp, 'promoted': prom, 'rows': len(rows)}, open(os.path.join(out_dir, 'summary.json'), 'w'), indent=1)
    return '\n'.join(L)
