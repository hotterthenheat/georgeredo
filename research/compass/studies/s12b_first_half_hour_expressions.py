"""Study S12b (amendment A5.1): 10:00 option expressions of the first-half-hour direction on SPY/QQQ/IWM 0DTE,
2022-11 -> 2026-10: (a) long the baseline-rule contract 10:00 -> 15:00; (b) short an opposite-side vertical (0.30/0.15
delta) 10:00 -> 15:50 with a 2x-credit stop; random-direction controls (5 seeds); adverse one-tick scenario.
Usage: python3 s12b_first_half_hour_expressions.py"""
import datetime as dt, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import bars, store, contracts, run, sim, short_sim, stats, signals
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'results', 'v1', 's12b_first_half_hour_expressions'); os.makedirs(OUT, exist_ok=True)
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
UND = f'{SP}/theta/data/underlying'
st = store.CacheStore(UND, f'{SP}/theta/data_full/chains', f'{SP}/theta/data/index', f'{SP}/universe/expirations.jsonl')
XP_LONG = dict(stop_pct=10.0, tp1_frac=0.0, tp2_pct=100.0, use_vwap_loss=False, use_invalidation=False, use_ema_target=False, max_hold_min=300, session_cutoff_minute=380)
SEL_LONG = {'min_oi': None, 'min_volume': None}
SEL_SHORT = {'min_oi': None, 'min_volume': None, 'delta_lo': 0.20, 'delta_hi': 0.40, 'delta_target': 0.30}
trades = []; t0 = time.time()
for sym in ('SPY', 'QQQ', 'IWM'):
    sessions = [s for s in st.chain_sessions(sym) if s >= dt.date(2022, 11, 11)]
    df1 = bars.load_minutes(sym, UND, dt.date(2022, 10, 1), dt.date(2026, 10, 9)); feat = signals.features(df1)
    for i, sess in enumerate(sessions):
        day = feat.filter(pl.col('session') == sess)
        if day.height < 385: continue
        o0 = df1.filter((pl.col('session') == sess) & (pl.col('minute') == 0))['open']; e30 = day.filter(pl.col('minute') == 29)
        if o0.is_empty() or e30.height == 0: continue
        e = e30.row(0, named=True); r_first = float(e['close'] / o0[0] - 1)
        if r_first == 0: continue
        chain = st.chain_minutes(sym, sess, sess)
        if chain is None: continue
        snap = run._snapshot_at(chain, e['close_ts'])
        if snap.height == 0: continue
        t = contracts.years_to_expiry(e['close_ts'], sess); spot = float(e['close'])
        snap_a = contracts.annotate(snap, spot, t)
        e['invalidation_level'] = float('nan'); e['target_price'] = float('nan')
        rng = np.random.default_rng(int(sess.strftime('%Y%m%d')) + 7)
        for seed, direction in [(0, int(np.sign(r_first)))] + [(k, int(rng.choice([-1, 1]))) for k in (11, 12, 13, 14, 15)]:
            base = {'symbol': sym, 'session': sess, 'seed': seed, 'direction': direction, 'r_first': r_first}
            # (a) long
            row, _ = contracts.select(snap, spot, t, direction, SEL_LONG)
            if row is None: trades.append({**base, 'structure': 'long', 'status': 'no_eligible_contract'})
            else:
                q = run._quotes_for(chain, row['strike'], row['right'])
                tr = sim.simulate({**e, 'direction': direction, 'spot': spot}, {**row, 'last_trading_day': sess}, q, day, XP_LONG)
                trades.append({**base, 'structure': 'long', 'strike': row['strike'], 'right': row['right'], 'delta': row['delta_abs'], **({'status': 'filled', **{k: tr[k] for k in ('entry_ask', 'exit_bid', 'exit_reason', 'pnl', 'gross', 'commission', 'hold_min')}} if tr and tr['status'] == 'filled' else {'status': (tr or {}).get('status', 'no_quotes')})})
            # (b) short opposite-side vertical
            srow, _ = contracts.select(snap, spot, t, -direction, SEL_SHORT)
            if srow is None: trades.append({**base, 'structure': 'short_vertical', 'status': 'no_eligible_contract'}); continue
            lrow = short_sim.pick_long_leg(snap_a, srow, -direction, target_delta=0.15, lo=0.05, hi=0.25)
            if lrow is None: trades.append({**base, 'structure': 'short_vertical', 'status': 'no_long_leg'}); continue
            sq = run._quotes_for(chain, srow['strike'], srow['right']); lq = run._quotes_for(chain, lrow['strike'], lrow['right'])
            for adverse in (0.0, 0.01):
                r = short_sim.simulate({**e, 'direction': direction}, sq, lq, dict(stop_mult=2.0, max_hold_min=None, session_cutoff_minute=380, tick_adverse=adverse))
                trades.append({**base, 'structure': 'short_vertical', 'adverse_tick': adverse, 'strike': srow['strike'], 'right': srow['right'], 'delta': srow['delta_abs'], 'long_strike': lrow['strike'], 'long_delta': lrow['delta_abs'], **r})
        if i % 200 == 0: log(f'{sym} {sess} {i}/{len(sessions)} trades {len(trades)} ({time.time() - t0:.0f}s)')
tdf = pl.DataFrame(trades, infer_schema_length=None); tdf.write_parquet(os.path.join(OUT, 'trades.parquet'))
fl = tdf.filter(pl.col('status') == 'filled'); rows = []
for structure in ('long', 'short_vertical'):
    for adverse in ((None,) if structure == 'long' else (0.0, 0.01)):
        for filt, cond in (('all days', pl.lit(True)), ('|first 30m| >= 0.3%', pl.col('r_first').abs() >= 0.003)):
            c = fl.filter((pl.col('structure') == structure) & cond)
            if adverse is not None: c = c.filter(pl.col('adverse_tick') == adverse)
            s0 = c.filter(pl.col('seed') == 0); rr = c.filter(pl.col('seed') > 0)
            if s0.height < 50: continue
            ss = stats.summary(s0); rs = stats.summary(rr)
            rm = rr.group_by(['symbol', 'session']).agg(pl.col('pnl').mean().alias('rpnl')); pr = s0.join(rm, on=['symbol', 'session'], how='inner')
            dm, dlo, dhi = stats.cluster_bootstrap_ci((pr['pnl'] - pr['rpnl']).to_numpy(), pr['session'].cast(pl.Utf8).to_numpy())
            by = {str(y['year']): round(y['mean'], 2) for y in stats.by_group(s0.with_columns(pl.col('session').dt.year().alias('year')), ['year']).to_dicts()}
            bysym = {y['symbol']: round(y['mean'], 2) for y in stats.by_group(s0, ['symbol']).to_dicts()}
            rows.append({'structure': structure, 'adverse_tick': adverse, 'filters': filt, 'n': ss['n'], 'days': ss['days'], 'mean': ss['mean'], 'ci_lo': ss['ci_lo'], 'ci_hi': ss['ci_hi'], 'win_rate': ss['win_rate'], 'profit_factor': ss['profit_factor'], 'max_drawdown': ss['max_drawdown'], 'net_total': ss['net_total'], 'random_mean': rs['mean'], 'random_lo': rs['ci_lo'], 'random_hi': rs['ci_hi'], 'minus_random': dm, 'minus_random_lo': dlo, 'minus_random_hi': dhi, 'by_year': by, 'by_symbol': bysym, 'exits': s0.group_by('exit_reason').len().to_dicts()})
            log(f"{structure:14s} adv {adverse} {filt:22s} n {ss['n']:5d} mean {ss['mean']:+7.2f} [{ss['ci_lo']:+7.2f}, {ss['ci_hi']:+7.2f}] win {ss['win_rate'] * 100:.0f}% PF {ss['profit_factor']:.2f} DD {ss['max_drawdown']:.0f} | random {rs['mean']:+.2f} [{rs['ci_lo']:+.2f}, {rs['ci_hi']:+.2f}] | minus random {dm:+.2f} [{dlo:+.2f}, {dhi:+.2f}] | by year {by} | by symbol {bysym}")
json.dump(rows, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)
log(f'S12b DONE ({time.time() - t0:.0f}s)')
