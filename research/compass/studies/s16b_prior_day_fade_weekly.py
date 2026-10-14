"""Study S16b (amendment A5, option part of S16): fade the prior session's close-to-close move with a WEEKLY contract on
SPY/QQQ/IWM using the S03 chains (nearest-Friday weekly, 1-minute NBBO): at the close of the 09:31 bar buy the
baseline-rule contract (0.30-0.60 delta, nearest 0.45) in the fade direction; exit at the next session's 15:50 (time) or
at -50 % of premium (stop variant); cells: all days, |gap| >= 0.5 %; controls = random direction (5 seeds).
Usage: python3 s16b_prior_day_fade_weekly.py"""
import datetime as dt, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import bars, store, contracts, run, sim, stats, signals, calendar as cal
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
HERE = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(SP, 'theta', 'fetch_cache')
OUT = os.path.join(HERE, '..', 'results', 'v1', 's16b_prior_day_fade_weekly'); os.makedirs(OUT, exist_ok=True)
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
UND = f'{SP}/theta/data/underlying'
choice = {}
for line in open(os.path.join(CACHE, 'weekly_choice.jsonl')):
    r = json.loads(line); choice[(r['root'], r['session'])] = dt.date.fromisoformat(r['expiration'])
def chain_for(root, sess, exp):
    p = os.path.join(CACHE, 'chains_exp', root, f'{sess}__{exp}.parquet')
    if not os.path.exists(p) or os.path.getsize(p) == 0: return None
    df = pl.read_parquet(p)
    if df.height == 0: return None
    return df.select(['timestamp', 'strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size']).with_columns(pl.col('timestamp').dt.replace_time_zone(None), pl.col('right').cast(pl.Utf8))
SEL = {'min_oi': None, 'min_volume': None}
XP = {'time_only': dict(stop_pct=10.0, tp1_frac=0.0, tp2_pct=100.0, use_vwap_loss=False, use_invalidation=False, use_ema_target=False, max_hold_min=769, session_cutoff_minute=390),
      'stop50': dict(stop_pct=0.50, tp1_frac=0.0, tp2_pct=100.0, use_vwap_loss=False, use_invalidation=False, use_ema_target=False, max_hold_min=769, session_cutoff_minute=390)}
trades = []; t0 = time.time()
for sym in ('SPY', 'QQQ', 'IWM'):
    df1 = bars.load_minutes(sym, UND, dt.date(2017, 5, 1), dt.date(2026, 10, 9)); feat = signals.features(df1)
    daily = df1.group_by('session').agg(pl.col('close').last().alias('close')).sort('session').with_columns([pl.col('close').shift(1).alias('pc'), pl.col('close').shift(2).alias('pc2')])
    prev_cc = {r['session']: (r['pc'] / r['pc2'] - 1) for r in daily.iter_rows(named=True) if r['pc'] is not None and r['pc2'] is not None}
    sessions = sorted({k[1] for k in choice if k[0] == sym})
    done = 0
    for s_str in sessions:
        sess = dt.date.fromisoformat(s_str); exp = choice[(sym, s_str)]
        if sess not in prev_cc or prev_cc[sess] == 0: continue
        chain = chain_for(sym, sess, exp)
        if chain is None: continue
        nxt = cal.next_session(sess)
        if nxt > exp: continue  # the contract must survive to the exit session
        chain2 = chain_for(sym, nxt, choice.get((sym, str(nxt)), exp)) if choice.get((sym, str(nxt))) == exp else None
        day = feat.filter(pl.col('session') == sess); e1 = day.filter(pl.col('minute') == 1)
        if e1.height == 0: continue
        e = e1.row(0, named=True); e['invalidation_level'] = float('nan'); e['target_price'] = float('nan')
        spot = float(e['close']); gap = float(df1.filter((pl.col('session') == sess) & (pl.col('minute') == 0))['open'][0] / daily.filter(pl.col('session') == sess)['pc'][0] - 1)
        snap = run._snapshot_at(chain, e['close_ts'])
        if snap.height == 0: continue
        ltd = cal.last_trading_day(exp, False); t = contracts.years_to_expiry(e['close_ts'], ltd)
        fwin = feat.filter(pl.col('session').is_in([sess, nxt]))
        rng = np.random.default_rng(int(sess.strftime('%Y%m%d')) + 16)
        for seed, direction in [(0, -int(np.sign(prev_cc[sess])))] + [(k, int(rng.choice([-1, 1]))) for k in (11, 12, 13, 14, 15)]:
            row, _ = contracts.select(snap, spot, t, direction, SEL)
            base = {'symbol': sym, 'session': sess, 'expiration': exp, 'seed': seed, 'direction': direction, 'prev_cc': prev_cc[sess], 'gap': gap, 'has_next_chain': chain2 is not None}
            if row is None: trades.append({**base, 'exit_set': None, 'status': 'no_eligible_contract'}); continue
            q = run._quotes_for(chain, row['strike'], row['right'])
            if chain2 is not None: q = pl.concat([q, run._quotes_for(chain2, row['strike'], row['right'])]).sort('timestamp')
            for xs, xp in XP.items():
                tr = sim.simulate({**e, 'direction': direction, 'spot': spot}, {**row, 'last_trading_day': ltd}, q, fwin, xp)
                if tr is None or tr['status'] != 'filled': trades.append({**base, 'exit_set': xs, 'status': (tr or {}).get('status', 'no_quotes')}); continue
                trades.append({**base, 'exit_set': xs, 'status': 'filled', 'strike': row['strike'], 'right': row['right'], 'delta': row['delta_abs'], **{k: tr[k] for k in ('entry_ask', 'exit_bid', 'exit_reason', 'pnl', 'gross', 'commission', 'hold_min')}})
        done += 1
        if done % 100 == 0: log(f'{sym} {sess} sessions {done} trades {len(trades)} ({time.time() - t0:.0f}s)')
    log(f'{sym}: {done} sessions with chains')
tdf = pl.DataFrame(trades, infer_schema_length=None); tdf.write_parquet(os.path.join(OUT, 'trades.parquet'))
fl = tdf.filter(pl.col('status') == 'filled'); rows = []
for xs in XP:
    for filt, cond in (('all days', pl.lit(True)), ('|gap| >= 0.5%', pl.col('gap').abs() >= 0.005)):
        for sym in ('ALL', 'SPY', 'QQQ', 'IWM'):
            c = fl.filter((pl.col('exit_set') == xs) & cond & ((pl.col('symbol') == sym) if sym != 'ALL' else pl.lit(True)))
            s0 = c.filter(pl.col('seed') == 0); rr = c.filter(pl.col('seed') > 0)
            if s0.height < 50: continue
            ss = stats.summary(s0); rs = stats.summary(rr)
            rm = rr.group_by(['symbol', 'session']).agg(pl.col('pnl').mean().alias('rpnl')); pr = s0.join(rm, on=['symbol', 'session'], how='inner')
            dm, dlo, dhi = stats.cluster_bootstrap_ci((pr['pnl'] - pr['rpnl']).to_numpy(), pr['session'].cast(pl.Utf8).to_numpy())
            by = {str(y['year']): round(y['mean'], 2) for y in stats.by_group(s0.with_columns(pl.col('session').dt.year().alias('year')), ['year']).to_dicts()}
            rows.append({'exit_set': xs, 'filters': filt, 'symbol': sym, 'n': ss['n'], 'days': ss['days'], 'mean': ss['mean'], 'ci_lo': ss['ci_lo'], 'ci_hi': ss['ci_hi'], 'win_rate': ss['win_rate'], 'profit_factor': ss['profit_factor'], 'max_drawdown': ss['max_drawdown'], 'premium_mean': float(s0['entry_ask'].mean() * 100), 'random_mean': rs['mean'], 'random_lo': rs['ci_lo'], 'random_hi': rs['ci_hi'], 'minus_random': dm, 'minus_random_lo': dlo, 'minus_random_hi': dhi, 'by_year': by, 'exits': s0.group_by('exit_reason').len().to_dicts()})
            log(f"{xs:9s} {filt:14s} {sym:3s} n {ss['n']:5d} mean {ss['mean']:+7.2f} [{ss['ci_lo']:+7.2f}, {ss['ci_hi']:+7.2f}] win {ss['win_rate'] * 100:.0f}% PF {ss['profit_factor']:.2f} | random {rs['mean']:+.2f} | minus random {dm:+.2f} [{dlo:+.2f}, {dhi:+.2f}] | by year {by}")
json.dump(rows, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)
log(f'S16b DONE ({time.time() - t0:.0f}s)')
