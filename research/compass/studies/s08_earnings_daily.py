"""Study S08 (04_protocol.md amendment A3): the Earnings/Events family at daily resolution on the stock EOD lake with the
Unusual Whales earnings calendar. Usage: python3 s08_earnings_daily.py [out_name] [lake_root] [first_year] [last_year]"""
import datetime as dt, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import daily_screen as ds, stats
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
name = sys.argv[1] if len(sys.argv) > 1 else 's08_earnings_daily'
root = sys.argv[2] if len(sys.argv) > 2 else f'{SP}/lake/stock_eod'
y0 = int(sys.argv[3]) if len(sys.argv) > 3 else 2023
y1 = int(sys.argv[4]) if len(sys.argv) > 4 else 2026
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'v1', name); os.makedirs(OUT, exist_ok=True)
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
t0 = time.time()
df = ds.load_lake(root, list(range(y0, y1 + 1))); elig = ds.universe(df); f = ds.features(df).with_columns(pl.col('date').dt.year().alias('year'))
f = f.join(elig, on=['symbol', 'year'], how='semi').filter(pl.col('i') >= 200)
b = ds.benchmark(f, elig); f = f.join(b, on='date', how='left')
# next-session open after each row, and the following session's forward returns (for the drift entry)
f = f.with_columns([pl.col('date').shift(-1).over('symbol').alias('next_date'), pl.col('open').shift(-1).over('symbol').alias('next_open')])
log(f'eligible rows {f.height:,} ({time.time() - t0:.0f}s)')
e = pl.read_parquet(os.path.join(ROOT, 'data_lake', 'unusualwhales', 'earnings.parquet'))
e = e.filter(pl.col('report_type') == 'quarterly').with_columns([pl.col('report_date').str.to_date(strict=False).alias('rd'), pl.col('reported_eps').cast(pl.Float64, strict=False), pl.col('estimated_eps').cast(pl.Float64, strict=False), pl.col('surprise').cast(pl.Float64, strict=False)])
e = e.filter(pl.col('rd').is_not_null() & pl.col('reported_eps').is_not_null() & pl.col('estimated_eps').is_not_null() & pl.col('report_time').is_in(['premarket', 'postmarket']))
e = e.filter((pl.col('rd').dt.year() >= y0 + 1) & (pl.col('rd').dt.year() <= y1)).rename({'ticker': 'symbol'}).unique(['symbol', 'rd'])
# event session: the report date (premarket) or the next session after the report date (postmarket). Map through the
# symbol's own trading dates so holidays and gaps are honoured.
dates = f.select(['symbol', 'date', 'next_date']).rename({'date': 'rd'})
e = e.join(dates, on=['symbol', 'rd'], how='inner').with_columns(pl.when(pl.col('report_time') == 'premarket').then(pl.col('rd')).otherwise(pl.col('next_date')).alias('date'))
ev = e.select(['symbol', 'date', 'rd', 'report_time', 'reported_eps', 'estimated_eps', 'surprise']).join(f, on=['symbol', 'date'], how='inner')
ev = ev.with_columns([
    (pl.col('reported_eps') - pl.col('estimated_eps')).alias('surp'),
    ((pl.col('reported_eps') - pl.col('estimated_eps')) / pl.col('estimated_eps').abs().clip(lower_bound=0.01)).alias('surp_pct'),
    (pl.col('open') / pl.col('prev_close') - 1).alias('event_gap'), pl.col('ret').alias('event_day_ret'),
])
log(f'events {ev.height:,} symbols {ev["symbol"].n_unique():,} dates {ev["date"].n_unique():,}  premarket {int((ev["report_time"] == "premarket").sum()):,}')
# forward returns from the event open (gap entry) are r1..r21 on the event row (entry = that session's open: use the event
# row's own open, not next_open) -> recompute: close[t+h-1]/open[t] - 1 on the event row's horizon convention
# ds.features defines r_h = close[t+h]/open[t+1] - 1, i.e. entry at the next open. For the gap entry we need entry at
# the event row's open: shift the definition by one row -> use the previous row's r_h (entry = this open, exit = close h-1
# sessions after this one) -> simpler: compute directly.
F = f.select(['symbol', 'date', 'open', 'close'] + [f'r{h}' for h in ds.HORIZONS] + [f'b{h}' for h in ds.HORIZONS])
for h in ds.HORIZONS:
    F = F.with_columns((pl.col('close').shift(-(h - 1)).over('symbol') / pl.col('open') - 1).alias(f'g{h}'))
ev = ev.join(F.select(['symbol', 'date'] + [f'g{h}' for h in ds.HORIZONS]), on=['symbol', 'date'], how='left')
H = list(ds.HORIZONS)
def cell(sub: pl.DataFrame, direction: np.ndarray, entry: str) -> dict:
    days = sub['date'].cast(pl.Utf8).to_numpy(); rec = {'n': int(sub.height), 'days': int(np.unique(days).size), 'symbols': int(sub['symbol'].n_unique()), 'calls_share': float((direction > 0).mean())}
    rec['pre_ret_bp'] = float(np.nanmean(sub['event_day_ret'].to_numpy() * direction) * 1e4); rec['entry_gap_bp'] = float(np.nanmean(sub['event_gap'].to_numpy() * direction) * 1e4)
    for h in H:
        r = (sub[f'g{h}'] if entry == 'gap' else sub[f'r{h}']).to_numpy() * direction * 1e4; bm = sub[f'b{h}'].to_numpy() * direction * 1e4
        ok = np.isfinite(r) & np.isfinite(bm)
        m, lo, hi = stats.cluster_bootstrap_ci(r[ok], days[ok], n_boot=1000); rec.update({f'abs_{h}d_bp': m, f'abs_{h}d_lo': lo, f'abs_{h}d_hi': hi})
        m, lo, hi = stats.cluster_bootstrap_ci(r[ok] - bm[ok], days[ok], n_boot=1000); rec.update({f'adj_{h}d_bp': m, f'adj_{h}d_lo': lo, f'adj_{h}d_hi': hi})
        if h == 10: rec['hit_10d'] = float((r[ok] > 0).mean())
    r10 = (sub['g10'] if entry == 'gap' else sub['r10']).to_numpy() * direction * 1e4; b10 = sub['b10'].to_numpy() * direction * 1e4; yrs = sub['year'].to_numpy()
    rec['by_year_adj_10d'] = {int(y): round(float(np.nanmean((r10 - b10)[yrs == y])), 1) for y in np.unique(yrs)}
    rec['by_side_adj_10d'] = {'calls': round(float(np.nanmean((r10 - b10)[direction > 0])), 1), 'puts': round(float(np.nanmean((r10 - b10)[direction < 0])), 1)}
    return rec
ev = ev.with_columns(pl.col('surp_pct').rank().over('year').alias('rk'), pl.len().over('year').alias('ny')).with_columns((pl.col('rk') * 3 / pl.col('ny')).ceil().clip(1, 3).cast(pl.Int8).alias('tercile'))
rows = []
for entry in ('gap', 'drift'):
    specs = [('surprise_sign', 'all', pl.col('surp') != 0), ('surprise_sign', 'top_tercile_beats', pl.col('tercile') == 3), ('surprise_sign', 'bottom_tercile_misses', pl.col('tercile') == 1),
             ('surprise_sign', 'premarket', pl.col('report_time') == 'premarket'), ('surprise_sign', 'postmarket', pl.col('report_time') == 'postmarket'),
             ('event_day_move', 'all', pl.col('event_day_ret') != 0), ('event_day_move', 'big_move_2sigma', pl.col('event_day_ret').abs() >= 2 * pl.col('sigma60')),
             ('event_day_move', 'agrees_with_surprise', (pl.col('event_day_ret') * pl.col('surp')) > 0), ('event_day_move', 'against_surprise', (pl.col('event_day_ret') * pl.col('surp')) < 0)]
    for trig, filt, cond in specs:
        sub = ev.filter(cond)
        if trig == 'event_day_move' and entry == 'gap': continue  # the event-day move is not known at the event open
        d = np.sign(sub['surp'].to_numpy()) if trig == 'surprise_sign' else np.sign(sub['event_day_ret'].to_numpy())
        keep = d != 0; sub = sub.filter(pl.Series(keep)); d = d[keep].astype(int)
        if sub.height < 100: rows.append({'trigger': f'{trig}@{entry}', 'filters': filt, 'n': int(sub.height)}); continue
        rec = {'trigger': f'{trig}@{entry}', 'filters': filt, **cell(sub, d, entry)}; rows.append(rec)
        log(f"{rec['trigger']:26s} {filt:22s} n {rec['n']:6d} abs10 {rec['abs_10d_bp']:+6.1f} [{rec['abs_10d_lo']:+6.1f},{rec['abs_10d_hi']:+6.1f}] adj10 {rec['adj_10d_bp']:+6.1f} [{rec['adj_10d_lo']:+6.1f},{rec['adj_10d_hi']:+6.1f}]")
ev.select(['symbol', 'date', 'rd', 'report_time', 'reported_eps', 'estimated_eps', 'surp', 'surp_pct', 'tercile', 'event_gap', 'event_day_ret', 'year'] + [f'g{h}' for h in H] + [f'r{h}' for h in H] + [f'b{h}' for h in H]).write_parquet(os.path.join(OUT, 'events.parquet'))
md = ds.report(rows, OUT, f'{name}: earnings reports, direction = surprise sign (or the event-day move), entry at the event open (gap) or the next open (drift), {y0 + 1} → {y1}')
print(md); log(f'S08 DONE ({time.time() - t0:.0f}s)')
