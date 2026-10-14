"""Study S15 (amendment A5): 0DTE short ATM straddle at 10:00 on SPY/QQQ, bought back at 15:50, priced leg by leg at the
NBBO (sell at the bid, buy back at the ask), $0.70 per contract per side per leg; unconditional vs conditioned on the
straddle-implied move relative to the trailing 20-session realized 10:00 -> 15:50 move (rich >= 1.25x, cheap <= 0.8x),
with and without the FOMC/CPI/NFP and month-end skip (H17). Usage: python3 s15_vrp_short_straddle.py"""
import datetime as dt, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import store, run, stats, regime
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'results', 'v1', 's15_vrp_short_straddle'); os.makedirs(OUT, exist_ok=True)
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
st = store.CacheStore(f'{SP}/theta/data/underlying', f'{SP}/theta/data_full/chains', f'{SP}/theta/data/index', f'{SP}/universe/expirations.jsonl')
ev = regime.event_days(); t0 = time.time(); rows = []
T_ENTRY = dt.time(10, 0); T_EXIT = dt.time(15, 50)
for sym in ('SPY', 'QQQ'):
    sessions = [s for s in st.chain_sessions(sym) if s >= dt.date(2022, 11, 11)]
    df1 = st.bars(sym, dt.date(2022, 11, 1), dt.date(2026, 10, 9))
    for i, sess in enumerate(sessions):
        day = df1.filter(pl.col('session') == sess)
        if day.height < 385: continue
        spot0 = day.filter(pl.col('minute') == 29)['close']; spot1 = day.filter(pl.col('minute') == 379)['close']
        if spot0.is_empty() or spot1.is_empty(): continue
        spot0 = float(spot0[0]); spot1 = float(spot1[0])
        chain = st.chain_minutes(sym, sess, sess)
        if chain is None: continue
        s_in = run._snapshot_at(chain, dt.datetime.combine(sess, T_ENTRY)); s_out = run._snapshot_at(chain, dt.datetime.combine(sess, T_EXIT))
        if s_in.height == 0 or s_out.height == 0: continue
        strikes = s_in['strike'].unique().to_numpy(); K = float(strikes[np.argmin(np.abs(strikes - spot0))])
        def leg(snap, right):
            r = snap.filter((pl.col('strike') == K) & (pl.col('right') == right))
            return None if r.height == 0 else r.row(0, named=True)
        ci, pi, co, po = leg(s_in, 'CALL'), leg(s_in, 'PUT'), leg(s_out, 'CALL'), leg(s_out, 'PUT')
        if not all((ci, pi, co, po)) or min(ci['bid'], pi['bid']) <= 0 or min(co['ask'], po['ask']) <= 0: continue
        credit = ci['bid'] + pi['bid']; cost = co['ask'] + po['ask']
        rows.append({'symbol': sym, 'session': sess, 'strike': K, 'spot0': spot0, 'spot1': spot1, 'credit': credit, 'cost': cost, 'mid_in': (ci['bid'] + ci['ask'] + pi['bid'] + pi['ask']) / 2,
                     'implied_move': credit / spot0, 'realized_move': abs(spot1 / spot0 - 1), 'pnl': (credit - cost) * 100 - 4 * 0.70, 'pnl_adverse': (credit - 0.02 - (cost + 0.02)) * 100 - 4 * 0.70,
                     'event': ','.join(sorted(ev.get(sess, set()))) or None, 'month_end': regime.is_month_end(sess)})
        if i % 300 == 0: log(f'{sym} {sess} {i}/{len(sessions)} ({time.time() - t0:.0f}s)')
df = pl.DataFrame(rows).sort(['symbol', 'session'])
df = df.with_columns(pl.col('realized_move').shift(1).rolling_mean(20).over('symbol').alias('realized_trailing20')).with_columns((pl.col('implied_move') / pl.col('realized_trailing20')).alias('vrp_ratio'), pl.col('session').dt.year().alias('year'))
df.write_parquet(os.path.join(OUT, 'trades.parquet'))
log(f'straddles {df.height} ({time.time() - t0:.0f}s)')
out = []
def cell(name, sub, col='pnl'):
    if sub.height < 50: return
    s = stats.summary(sub, pnl_col=col)
    by = {str(y['year']): round(y['mean'], 2) for y in stats.by_group(sub, ['year']).to_dicts()} if col == 'pnl' else {}
    r = {'cell': name, 'pnl_col': col, 'n': s['n'], 'mean': s['mean'], 'ci_lo': s['ci_lo'], 'ci_hi': s['ci_hi'], 'win_rate': s['win_rate'], 'profit_factor': s['profit_factor'], 'max_drawdown': s['max_drawdown'], 'net_total': s['net_total'], 'credit_mean': float(sub['credit'].mean() * 100), 'worst_5': s['worst_5_trades'], 'by_year': by}
    out.append(r); log(f"{name:55s} n {s['n']:4d} mean {s['mean']:+7.2f} [{s['ci_lo']:+7.2f}, {s['ci_hi']:+7.2f}] win {s['win_rate'] * 100:.0f}% PF {s['profit_factor']:.2f} DD {s['max_drawdown']:.0f} by year {by}")
for sym in ('SPY', 'QQQ', 'ALL'):
    d = df if sym == 'ALL' else df.filter(pl.col('symbol') == sym)
    skip = d.filter(pl.col('event').is_null() & ~pl.col('month_end'))
    for tag, dd in (('all days', d), ('skip FOMC/CPI/NFP/month-end', skip)):
        cell(f'{sym} unconditional, {tag}', dd)
        cell(f'{sym} rich (implied >= 1.25x trailing realized), {tag}', dd.filter(pl.col('vrp_ratio') >= 1.25))
        cell(f'{sym} cheap (implied <= 0.8x trailing realized), {tag}', dd.filter(pl.col('vrp_ratio') <= 0.8))
        cell(f'{sym} middle, {tag}', dd.filter(pl.col('vrp_ratio').is_between(0.8, 1.25, closed='none')))
    cell(f'{sym} unconditional, all days, adverse one tick per leg', d, 'pnl_adverse')
    cell(f'{sym} rich, skip events, adverse one tick per leg', skip.filter(pl.col('vrp_ratio') >= 1.25), 'pnl_adverse')
# rich minus cheap difference (unpaired, bootstrap over days)
rng = np.random.default_rng(7); a = df.filter(pl.col('vrp_ratio') >= 1.25)['pnl'].to_numpy(); b = df.filter(pl.col('vrp_ratio') <= 0.8)['pnl'].to_numpy()
if a.size > 30 and b.size > 30:
    diffs = [rng.choice(a, a.size).mean() - rng.choice(b, b.size).mean() for _ in range(3000)]
    out.append({'cell': 'ALL rich minus cheap (unpaired bootstrap)', 'mean': float(a.mean() - b.mean()), 'ci_lo': float(np.percentile(diffs, 2.5)), 'ci_hi': float(np.percentile(diffs, 97.5)), 'n': int(a.size + b.size)})
    log(f"rich minus cheap: {a.mean() - b.mean():+.2f} [{np.percentile(diffs, 2.5):+.2f}, {np.percentile(diffs, 97.5):+.2f}]")
json.dump(out, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)
log(f'S15 DONE ({time.time() - t0:.0f}s)')
