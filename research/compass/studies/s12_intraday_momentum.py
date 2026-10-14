"""Study S12 (amendment A5): intraday momentum. Underlying: the 09:30 -> 10:00 return's sign predicting 10:00 -> 15:00,
15:00 -> 15:50 and 15:30 -> 16:00 on SPY/QQQ/IWM 2017-06 -> 2026-10 (all days; |first half hour| >= 0.3 %).
Option: at 15:00 buy the baseline-rule 0DTE contract in the first-half-hour direction, exit 15:50, vs the same contract in a
random direction (5 seeds), 2022-11 -> 2026-10. Usage: python3 s12_intraday_momentum.py"""
import datetime as dt, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import bars, store, contracts, run, sim, stats, calendar as cal
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'results', 'v1', 's12_intraday_momentum'); os.makedirs(OUT, exist_ok=True)
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
UND = f'{SP}/theta/data/underlying'
rows = []; t0 = time.time()
def px(df1, minute):  # close of the bar whose close_ts is 09:30 + minute
    return df1.filter(pl.col('minute') == minute - 1).select(['session', 'close']).rename({'close': f'c{minute}'})
for sym in ('SPY', 'QQQ', 'IWM'):
    df1 = bars.load_minutes(sym, UND, dt.date(2017, 6, 1), dt.date(2026, 10, 9))
    op = df1.filter(pl.col('minute') == 0).select(['session', 'open']).rename({'open': 'o0'})
    d = op
    for m in (30, 330, 360, 380, 390): d = d.join(px(df1, m), on='session', how='inner')
    d = d.with_columns([(pl.col('c30') / pl.col('o0') - 1).alias('r_first'), (pl.col('c330') / pl.col('c30') - 1).alias('r_rest'), (pl.col('c380') / pl.col('c330') - 1).alias('r_1500_1550'), (pl.col('c390') / pl.col('c360') - 1).alias('r_last30')])
    d = d.filter(pl.col('r_first') != 0).with_columns(pl.col('session').dt.year().alias('year'))
    for filt, cond in (('all days', pl.lit(True)), ('|first 30m| >= 0.3%', pl.col('r_first').abs() >= 0.003)):
        s = d.filter(cond); sign = np.sign(s['r_first'].to_numpy()); days = s['session'].cast(pl.Utf8).to_numpy()
        for cell, col in (('10:00->15:00', 'r_rest'), ('15:00->15:50', 'r_1500_1550'), ('15:30->16:00', 'r_last30')):
            r = s[col].to_numpy() * sign * 1e4; m, lo, hi = stats.cluster_bootstrap_ci(r, days, n_boot=2000)
            yrs = s['year'].to_numpy(); by = {int(y): round(float(r[yrs == y].mean()), 1) for y in np.unique(yrs)}
            rows.append({'part': 'underlying', 'symbol': sym, 'filters': filt, 'cell': cell, 'n': int(r.size), 'mean_bp': m, 'lo': lo, 'hi': hi, 'hit': float((r > 0).mean()), 'by_year': by, 'uncond_abs_bp': float(np.abs(s[col].to_numpy()).mean() * 1e4)})
            log(f'{sym} {filt:22s} {cell:13s} n {r.size:5d} {m:+6.1f} [{lo:+6.1f}, {hi:+6.1f}] hit {(r > 0).mean() * 100:.0f}% by year {by}')
# option expression: 15:00 entry in the first-half-hour direction, 0DTE, exit 15:50
st = store.CacheStore(UND, f'{SP}/theta/data_full/chains', f'{SP}/theta/data/index', f'{SP}/universe/expirations.jsonl')
XP = dict(stop_pct=10.0, tp1_frac=0.0, tp2_pct=100.0, use_vwap_loss=False, use_invalidation=False, use_ema_target=False, max_hold_min=60, session_cutoff_minute=380)
SEL = {'min_oi': None, 'min_volume': None}
trades = []
for sym in ('SPY', 'QQQ', 'IWM'):
    sessions = [s for s in st.chain_sessions(sym) if s >= dt.date(2022, 11, 11)]
    df1 = bars.load_minutes(sym, UND, dt.date(2022, 10, 1), dt.date(2026, 10, 9))
    from engine import signals
    feat = signals.features(df1)
    for i, sess in enumerate(sessions):
        day = feat.filter(pl.col('session') == sess)
        if day.height < 385: continue
        o0 = df1.filter((pl.col('session') == sess) & (pl.col('minute') == 0))['open']
        c30 = day.filter(pl.col('minute') == 29)['close']; e330 = day.filter(pl.col('minute') == 329)
        if o0.is_empty() or c30.is_empty() or e330.height == 0: continue
        r_first = float(c30[0] / o0[0] - 1)
        if r_first == 0: continue
        chain = st.chain_minutes(sym, sess, sess)
        if chain is None: continue
        e = e330.row(0, named=True); e['invalidation_level'] = float('nan'); e['target_price'] = float('nan')
        snap = run._snapshot_at(chain, e['close_ts'])
        if snap.height == 0: continue
        t = contracts.years_to_expiry(e['close_ts'], sess)
        rng = np.random.default_rng(int(sess.strftime('%Y%m%d')))
        for seed, direction in [(0, int(np.sign(r_first)))] + [(k, int(rng.choice([-1, 1]))) for k in (11, 12, 13, 14, 15)]:
            row, diag = contracts.select(snap, float(e['close']), t, direction, SEL)
            if row is None: trades.append({'symbol': sym, 'session': sess, 'seed': seed, 'direction': direction, 'r_first': r_first, 'status': 'no_eligible_contract'}); continue
            q = run._quotes_for(chain, row['strike'], row['right'])
            tr = sim.simulate({**e, 'direction': direction, 'spot': float(e['close'])}, {**row, 'last_trading_day': sess}, q, day, XP)
            if tr is None or tr['status'] != 'filled': trades.append({'symbol': sym, 'session': sess, 'seed': seed, 'direction': direction, 'r_first': r_first, 'status': (tr or {}).get('status', 'no_quotes')}); continue
            trades.append({'symbol': sym, 'session': sess, 'seed': seed, 'direction': direction, 'r_first': r_first, 'strike': row['strike'], 'right': row['right'], 'delta': row['delta_abs'], 'status': 'filled', **{k: tr[k] for k in ('entry_ask', 'exit_bid', 'exit_reason', 'pnl', 'gross', 'commission', 'hold_min')}})
        if i % 200 == 0: log(f'{sym} {sess} {i}/{len(sessions)} trades {len(trades)} ({time.time() - t0:.0f}s)')
tdf = pl.DataFrame(trades, infer_schema_length=None); tdf.write_parquet(os.path.join(OUT, 'trades.parquet'))
fl = tdf.filter(pl.col('status') == 'filled')
for filt, cond in (('all days', pl.lit(True)), ('|first 30m| >= 0.3%', pl.col('r_first').abs() >= 0.003)):
    s0 = fl.filter(cond & (pl.col('seed') == 0)); rr = fl.filter(cond & (pl.col('seed') > 0))
    if s0.height < 50: continue
    ss = stats.summary(s0); rs = stats.summary(rr)
    rm = rr.group_by(['symbol', 'session']).agg(pl.col('pnl').mean().alias('rpnl')); pr = s0.join(rm, on=['symbol', 'session'], how='inner')
    dm, dlo, dhi = stats.cluster_bootstrap_ci((pr['pnl'] - pr['rpnl']).to_numpy(), pr['session'].cast(pl.Utf8).to_numpy())
    by = {str(y['year']): round(y['mean'], 2) for y in stats.by_group(s0.with_columns(pl.col('session').dt.year().alias('year')), ['year']).to_dicts()}
    rows.append({'part': 'option_0dte_1500_1550', 'filters': filt, 'n': ss['n'], 'days': ss['days'], 'mean': ss['mean'], 'lo': ss['ci_lo'], 'hi': ss['ci_hi'], 'win_rate': ss['win_rate'], 'profit_factor': ss['profit_factor'], 'random_mean': rs['mean'], 'random_lo': rs['ci_lo'], 'random_hi': rs['ci_hi'], 'minus_random': dm, 'minus_random_lo': dlo, 'minus_random_hi': dhi, 'by_year': by})
    log(f"OPTION {filt:22s} n {ss['n']} mean {ss['mean']:+.2f} [{ss['ci_lo']:+.2f}, {ss['ci_hi']:+.2f}] win {ss['win_rate'] * 100:.0f}% PF {ss['profit_factor']:.2f} | random {rs['mean']:+.2f} [{rs['ci_lo']:+.2f}, {rs['ci_hi']:+.2f}] | minus random {dm:+.2f} [{dlo:+.2f}, {dhi:+.2f}] | by year {by}")
json.dump(rows, open(os.path.join(OUT, 'rows.json'), 'w'), indent=1, default=str)
log(f'S12 DONE ({time.time() - t0:.0f}s)')
