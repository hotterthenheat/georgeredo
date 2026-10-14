"""Study S10 (04_protocol.md amendment A4): short premium on index 0DTE, fading the owner's Quick Scalps signal. At each
S01 signal minute (and at the S01 matched random minutes, 5 seeds) sell the contract the rule would have bought (single)
or that contract against the nearest-0.20-delta further-OTM contract (vertical); exits per EXIT_SETS.
Usage: python3 s10_short_premium_0dte.py [out_name]"""
import datetime as dt, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import store, contracts, run, short_sim, stats, calendar as cal
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
HERE = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1] if len(sys.argv) > 1 else 's10_short_premium_0dte'
OUT = os.path.join(HERE, '..', 'results', 'v1', name); os.makedirs(OUT, exist_ok=True)
S01 = os.path.join(HERE, '..', 'results', 'v1', 's01_quick_scalps_0dte_baseline')
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
EXIT_SETS = {'cutoff_stop2': dict(stop_mult=2.0, max_hold_min=None), 'hold60_stop2': dict(stop_mult=2.0, max_hold_min=60), 'cutoff_nostop': dict(stop_mult=None, max_hold_min=None)}
STRUCTURES = ('single', 'vertical')
st = store.CacheStore(f'{SP}/theta/data/underlying', f'{SP}/theta/data_full/chains', f'{SP}/theta/data/index', f'{SP}/universe/expirations.jsonl')
sig = pl.read_parquet(os.path.join(S01, 'trades.parquet')).filter(pl.col('status') == 'filled').select(['symbol', 'session', 'close_ts', 'direction', 'spot', 'strike', 'right', 'delta']).with_columns(pl.lit(0, dtype=pl.Int64).alias('seed'))
rnd = pl.concat([pl.read_parquet(os.path.join(S01, f'baseline_{s}.parquet')).filter(pl.col('status') == 'filled').select(['symbol', 'session', 'close_ts', 'direction', 'spot', 'strike', 'right', 'delta', 'seed']).with_columns(pl.col('seed').cast(pl.Int64)) for s in (11, 12, 13, 14, 15)])
ev = pl.concat([sig, rnd]).sort(['symbol', 'session', 'close_ts'])
log(f'signal minutes {sig.height}, random minutes {rnd.height} (5 seeds)')
rows = []; t0 = time.time(); n_sess = 0
for (sym, sess), day in ev.group_by(['symbol', 'session'], maintain_order=True):
    sess = sess if isinstance(sess, dt.date) else dt.date.fromisoformat(str(sess))
    chain = st.chain_minutes(sym, sess, sess)
    if chain is None: continue
    n_sess += 1
    cache_q = {}
    def quotes(strike, right):
        k = (strike, right)
        if k not in cache_q: cache_q[k] = run._quotes_for(chain, strike, right)
        return cache_q[k]
    for e in day.iter_rows(named=True):
        snap = run._snapshot_at(chain, e['close_ts'])
        if snap.height == 0: continue
        t = contracts.years_to_expiry(e['close_ts'], sess)
        snap = contracts.annotate(snap, float(e['spot']), t)
        short_row = snap.filter((pl.col('strike') == e['strike']) & (pl.col('right') == e['right']))
        if short_row.height == 0: continue
        short_row = short_row.row(0, named=True)
        long_row = short_sim.pick_long_leg(snap, short_row, int(e['direction']))
        sq = quotes(e['strike'], e['right']); lq = quotes(long_row['strike'], long_row['right']) if long_row else None
        for structure in STRUCTURES:
            if structure == 'vertical' and lq is None:
                rows.append({**e, 'structure': structure, 'exit_set': None, 'status': 'no_long_leg'}); continue
            for xs, xp in EXIT_SETS.items():
                for adverse in (0.0, 0.01):
                    r = short_sim.simulate(e, sq, lq if structure == 'vertical' else None, {**xp, 'tick_adverse': adverse})
                    rows.append({**e, 'structure': structure, 'exit_set': xs, 'adverse_tick': adverse, 'long_strike': long_row['strike'] if long_row else None, 'long_delta': long_row['delta_abs'] if long_row else None, **r})
    if n_sess % 100 == 0: log(f'{sym} {sess} sessions {n_sess} rows {len(rows)} ({time.time() - t0:.0f}s)')
df = pl.DataFrame(rows, infer_schema_length=None)
df.write_parquet(os.path.join(OUT, 'trades.parquet'))
log(f'done {n_sess} sessions, {df.height} rows ({time.time() - t0:.0f}s)')
# summary per cell: signal vs random (pooled over seeds), paired difference on the signal's own day clusters
f = df.filter(pl.col('status') == 'filled')
out = []
for structure in STRUCTURES:
    for xs in EXIT_SETS:
        for adverse in (0.0, 0.01):
            c = f.filter((pl.col('structure') == structure) & (pl.col('exit_set') == xs) & (pl.col('adverse_tick') == adverse))
            s = c.filter(pl.col('seed') == 0); r = c.filter(pl.col('seed') > 0)
            if s.height < 50: continue
            ss = stats.summary(s); rs = stats.summary(r) if r.height else {}
            # paired: per signal, strategy pnl minus the mean random pnl on the same symbol/session (seeds pooled)
            rm = r.group_by(['symbol', 'session']).agg(pl.col('pnl').mean().alias('rpnl'))
            pr = s.join(rm, on=['symbol', 'session'], how='inner')
            dm, dlo, dhi = stats.cluster_bootstrap_ci((pr['pnl'] - pr['rpnl']).to_numpy(), pr['session'].cast(pl.Utf8).to_numpy()) if pr.height else (None, None, None)
            by_year = {str(y['year']): round(y['mean'], 2) for y in stats.by_group(s.with_columns(pl.col('session').dt.year().alias('year')), ['year']).to_dicts()}
            exits = s.group_by('exit_reason').len().to_dicts()
            out.append({'structure': structure, 'exit_set': xs, 'adverse_tick': adverse, 'n': ss['n'], 'days': ss['days'], 'mean': ss['mean'], 'ci_lo': ss['ci_lo'], 'ci_hi': ss['ci_hi'], 'win_rate': ss['win_rate'], 'profit_factor': ss['profit_factor'], 'max_drawdown': ss['max_drawdown'], 'net_total': ss['net_total'],
                        'credit_mean': float(s['credit'].mean() * 100), 'mae_mean': ss.get('mae_mean'), 'mae_p95': ss.get('mae_p95'), 'worst_5': ss.get('worst_5_trades'),
                        'random_n': rs.get('n'), 'random_mean': rs.get('mean'), 'random_ci_lo': rs.get('ci_lo'), 'random_ci_hi': rs.get('ci_hi'), 'minus_random': dm, 'minus_random_lo': dlo, 'minus_random_hi': dhi,
                        'by_year': by_year, 'exits': {x['exit_reason']: x['len'] for x in exits}})
            log(f"{structure:8s} {xs:13s} adverse {adverse}: n {ss['n']} mean {ss['mean']:+.2f} [{ss['ci_lo']:+.2f}, {ss['ci_hi']:+.2f}] win {ss['win_rate']*100:.0f}% PF {ss['profit_factor']:.2f} DD {ss['max_drawdown']:.0f} | random {rs.get('mean', float('nan')):+.2f} | minus random {dm if dm is None else round(dm, 2)} [{dlo if dlo is None else round(dlo, 2)}, {dhi if dhi is None else round(dhi, 2)}] | by year {by_year}")
json.dump(out, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)
json.dump({'exit_sets': EXIT_SETS, 'structures': STRUCTURES, 'source_signals': 'results/v1/s01_quick_scalps_0dte_baseline (filled signals and matched random minutes, seeds 11-15)', 'fees_per_contract_per_side_per_leg': 0.70, 'long_leg': 'same right, further OTM, |delta| nearest 0.20 within [0.08, 0.32]'}, open(os.path.join(OUT, 'config.json'), 'w'), indent=1)
log('S10 DONE')
