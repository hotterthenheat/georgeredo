"""Cross-reference of GeorgeFi's ledger against independent data, two questions the earlier reports did not answer directly:
  (1) Direction: after his entries, does the underlying move his way? Signed underlying return at 5/15/30/60 min and over
      his own hold, vs time-matched random minutes on the same symbol and day (5 seeds); hit rates; by epoch and book.
  (2) Day selection: is the same trade (same contract rule, entry minute, direction and hold) worth more on the days he
      chose than on random other sessions? Executable P&L at the 1-minute NBBO (ask in / bid out, $0.70/contract/side) of
      the 0.30-0.60-delta nearest-0.45 same-day contract on his day vs on 5 random sessions within +/-30 sessions.
Index roots use the ETF proxy for the underlying (SPXW->SPY, NDXP->QQQ, RUTW->IWM) and their own 0DTE chains where cached
(SPXW); single names are excluded (no minute bars). Output: results/G_edge_crossref.{md,csv}."""
import datetime as dt, json, os, sys, time
sys.path.insert(0, '/home/user/georgeredo/research/compass')
import numpy as np, polars as pl
from engine import bars, store, contracts, run, sim, stats, calendar as cal
SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
R = '/home/user/georgeredo/research/georgefi_full_history'
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
PROXY = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPY', 'SPX': 'SPY', 'NDXP': 'QQQ', 'NDX': 'QQQ', 'RUTW': 'IWM', 'RUT': 'IWM'}
CHAIN_ROOT = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPXW', 'SPX': 'SPXW'}
t = pl.read_csv(f'{R}/normalized/trades.csv', infer_schema_length=5000, ignore_errors=True)
t = t.filter(pl.col('occ_root').is_in(list(PROXY)) & pl.col('side').is_in(['CALL', 'PUT']) & pl.col('entry_et').is_not_null() & pl.col('exit_et').is_not_null())
t = t.with_columns([pl.col('entry_et').str.slice(0, 19).str.to_datetime('%Y-%m-%dT%H:%M:%S').alias('entry_ts'), pl.col('exit_et').str.slice(0, 19).str.to_datetime('%Y-%m-%dT%H:%M:%S').alias('exit_ts'),
                    pl.when(pl.col('side') == 'CALL').then(1).otherwise(-1).alias('direction'), pl.col('occ_root').replace_strict(PROXY, default=None).alias('proxy')])
t = t.with_columns(pl.col('entry_ts').dt.date().alias('session'), ((pl.col('exit_ts') - pl.col('entry_ts')).dt.total_seconds() / 60).alias('hold'))
log('ledger rows on index/ETF roots', t.height, t.group_by(['epoch_number', 'account_type']).len().sort(['epoch_number', 'account_type']).to_dicts())
UND = f'{SP}/theta/data/underlying'
feat = {s: bars.load_minutes(s, UND, dt.date(2025, 12, 1), dt.date(2026, 10, 13)) for s in ('SPY', 'QQQ', 'IWM')}
rows = []; rng = np.random.default_rng(3)
H = (5, 15, 30, 60)
for e in t.iter_rows(named=True):
    f = feat[e['proxy']].filter(pl.col('session') == e['session'])
    if f.height < 300: continue
    ts = f['close_ts'].to_numpy().astype('datetime64[ms]'); close = f['close'].to_numpy()
    e_ts = np.datetime64(e['entry_ts'], 'ms'); x_ts = np.datetime64(e['exit_ts'], 'ms')
    i = int(np.searchsorted(ts, e_ts))  # first bar closing at/after the entry second (decision at that close: no look-ahead)
    if i >= ts.size - 1: continue
    j = int(np.searchsorted(ts, x_ts)); j = min(max(j, i + 1), ts.size - 1)
    d = e['direction']; rec = {'epoch': e['epoch_number'], 'book': e['book'], 'account_type': e['account_type'], 'root': e['occ_root'], 'proxy': e['proxy'], 'session': str(e['session']), 'minute': int(f['minute'][i]), 'direction': d, 'hold': e['hold'], 'pnl_reported': e['pnl_reported'], 'is_0dte': e['is_0dte']}
    for h in H:
        k = min(i + h, ts.size - 1); rec[f'r{h}'] = (close[k] / close[i] - 1) * 1e4 * d
    rec['r_hold'] = (close[j] / close[i] - 1) * 1e4 * d
    # time-matched random minutes: same day, uniformly in 09:45-15:30, 5 seeds
    cand = np.flatnonzero((f['minute'].to_numpy() >= 15) & (f['minute'].to_numpy() <= 360))
    for s in range(5):
        ri = int(rng.choice(cand))
        for h in H:
            k = min(ri + h, ts.size - 1); rec[f'rand{s}_r{h}'] = (close[k] / close[ri] - 1) * 1e4 * d
        kj = min(ri + max(j - i, 1), ts.size - 1); rec[f'rand{s}_r_hold'] = (close[kj] / close[ri] - 1) * 1e4 * d
    rows.append(rec)
df = pl.DataFrame(rows); log('direction rows', df.height)
out = []
def cell(name, sub):
    if sub.height < 30: return
    days = sub['session'].to_numpy(); r = {'cell': name, 'n': sub.height, 'days': int(np.unique(days).size)}
    for h in list(H) + ['hold']:
        col = f'r{h}' if h != 'hold' else 'r_hold'; v = sub[col].to_numpy(); m, lo, hi = stats.cluster_bootstrap_ci(v, days, n_boot=2000)
        rv = np.mean([sub[f'rand{s}_{col}'].to_numpy() for s in range(5)], axis=0); dm, dlo, dhi = stats.cluster_bootstrap_ci(v - rv, days, n_boot=2000)
        r[f'{h}_bp'] = m; r[f'{h}_lo'] = lo; r[f'{h}_hi'] = hi; r[f'{h}_hit'] = float((v > 0).mean()); r[f'{h}_vs_random'] = dm; r[f'{h}_vs_random_lo'] = dlo; r[f'{h}_vs_random_hi'] = dhi
    out.append(r); log(f"{name:34s} n {r['n']:4d} | 15m {r['15_bp']:+6.1f} [{r['15_lo']:+6.1f},{r['15_hi']:+6.1f}] hit {r['15_hit']*100:.0f}% | 30m {r['30_bp']:+6.1f} [{r['30_lo']:+6.1f},{r['30_hi']:+6.1f}] vs rand {r['30_vs_random']:+6.1f} [{r['30_vs_random_lo']:+6.1f},{r['30_vs_random_hi']:+6.1f}] | hold {r['hold_bp']:+6.1f} [{r['hold_lo']:+6.1f},{r['hold_hi']:+6.1f}] hit {r['hold_hit']*100:.0f}% vs rand {r['hold_vs_random']:+6.1f} [{r['hold_vs_random_lo']:+6.1f},{r['hold_vs_random_hi']:+6.1f}]")
cell('all index/ETF trades', df)
for ep in (1, 2): cell(f'epoch {ep}', df.filter(pl.col('epoch') == ep))
for ep in (1, 2):
    for acct in ('0DTE', 'SWING'): cell(f'epoch {ep} {acct}', df.filter((pl.col('epoch') == ep) & (pl.col('account_type') == acct)))
for bk in df['book'].unique().to_list(): cell(f'book {bk}', df.filter(pl.col('book') == bk))
for d in (1, -1): cell('calls' if d > 0 else 'puts', df.filter(pl.col('direction') == d))
for rt in ('SPY', 'QQQ', 'IWM', 'SPXW'): cell(f'root {rt}', df.filter(pl.col('root') == rt))
# (2) day selection on 0DTE trades with cached chains
st = store.CacheStore(UND, f'{SP}/theta/data_full/chains', f'{SP}/theta/data/index', f'{SP}/universe/expirations.jsonl')
XP = dict(stop_pct=10.0, tp1_frac=0.0, tp2_pct=100.0, use_vwap_loss=False, use_invalidation=False, use_ema_target=False, session_cutoff_minute=385)
from engine import signals
featfull = {}
def feats(sym):
    if sym not in featfull: featfull[sym] = signals.features(bars.load_minutes(sym, UND, dt.date(2025, 10, 1), dt.date(2026, 10, 13)))
    return featfull[sym]
sess_all = {sym: st.chain_sessions(sym) for sym in ('SPY', 'QQQ', 'IWM', 'SPXW')}
ds_rows = []; done = 0
d0 = t.filter(pl.col('is_0dte') & pl.col('occ_root').is_in(list(CHAIN_ROOT)))
for e in d0.iter_rows(named=True):
    root = CHAIN_ROOT[e['occ_root']]; proxy = e['proxy']; sess = e['session']; hold = max(int(round(e['hold'])), 1)
    fe = feats(proxy); day = fe.filter(pl.col('session') == sess)
    if day.height < 300: continue
    ts = day['close_ts'].to_numpy().astype('datetime64[ms]'); i = int(np.searchsorted(ts, np.datetime64(e['entry_ts'], 'ms')))
    if i >= day.height - 2: continue
    minute = int(day['minute'][i])
    def trade(session, spot_day):
        chain = st.chain_minutes(root, session, session)
        if chain is None: return None
        row_e = spot_day.filter(pl.col('minute') == minute)
        if row_e.height == 0: return None
        ev = row_e.row(0, named=True); ev['invalidation_level'] = float('nan'); ev['target_price'] = float('nan')
        snap = run._snapshot_at(chain, ev['close_ts'])
        if snap.height == 0: return None
        if root == 'SPXW':  # index chain priced off the index level: scale the ETF spot by the ATM strike ratio at that minute
            strikes = snap['strike'].unique().to_numpy(); spot = float(strikes[np.argmin(np.abs(strikes - np.median(strikes)))])
            mid = snap.filter((pl.col('right') == 'CALL') & (pl.col('bid') > 0)).with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('m'))
            # ATM = the call strike whose mid is closest to the put mid at the same strike
            puts = snap.filter((pl.col('right') == 'PUT') & (pl.col('bid') > 0)).with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mp')).select(['strike', 'mp'])
            j = mid.select(['strike', 'm']).join(puts, on='strike', how='inner').with_columns((pl.col('m') - pl.col('mp')).abs().alias('_d')).sort('_d')
            if j.height == 0: return None
            spot = float(j['strike'][0])
        else: spot = float(ev['close'])
        tt = contracts.years_to_expiry(ev['close_ts'], session)
        row, _ = contracts.select(snap, spot, tt, e['direction'], {'min_oi': None, 'min_volume': None})
        if row is None: return None
        q = run._quotes_for(chain, row['strike'], row['right'])
        tr = sim.simulate({**ev, 'direction': e['direction'], 'spot': spot}, {**row, 'last_trading_day': session}, q, spot_day, {**XP, 'max_hold_min': hold})
        return tr['pnl'] if tr and tr['status'] == 'filled' else None
    own = trade(sess, day)
    if own is None: continue
    pool = [s for s in sess_all[root] if s != sess and abs((s - sess).days) <= 45]
    if len(pool) < 5: continue
    picks = list(rng.choice(pool, size=5, replace=False)); vals = []
    for s in picks:
        v = trade(s, fe.filter(pl.col('session') == s)); 
        if v is not None: vals.append(v)
    if len(vals) < 3: continue
    ds_rows.append({'epoch': e['epoch_number'], 'book': e['book'], 'root': e['occ_root'], 'session': str(sess), 'minute': minute, 'direction': e['direction'], 'hold': hold, 'own_pnl': own, 'random_day_pnl': float(np.mean(vals)), 'n_random': len(vals), 'pnl_reported': e['pnl_reported']})
    done += 1
    if done % 100 == 0: log(f'day-selection {done}')
dd = pl.DataFrame(ds_rows); log('day-selection rows', dd.height)
ds_out = []
def dcell(name, sub):
    if sub.height < 30: return
    days = sub['session'].to_numpy(); own = sub['own_pnl'].to_numpy(); rd = sub['random_day_pnl'].to_numpy()
    m, lo, hi = stats.cluster_bootstrap_ci(own, days, n_boot=2000); rm, rlo, rhi = stats.cluster_bootstrap_ci(rd, days, n_boot=2000); dm, dlo, dhi = stats.cluster_bootstrap_ci(own - rd, days, n_boot=2000)
    ds_out.append({'cell': name, 'n': sub.height, 'days': int(np.unique(days).size), 'own_mean': m, 'own_lo': lo, 'own_hi': hi, 'random_day_mean': rm, 'random_day_lo': rlo, 'random_day_hi': rhi, 'diff': dm, 'diff_lo': dlo, 'diff_hi': dhi, 'own_win': float((own > 0).mean()), 'random_win': float((rd > 0).mean())})
    log(f"DAY {name:28s} n {sub.height:4d} own {m:+7.2f} [{lo:+7.2f},{hi:+7.2f}] win {(own > 0).mean()*100:.0f}% | random day {rm:+7.2f} [{rlo:+7.2f},{rhi:+7.2f}] | diff {dm:+7.2f} [{dlo:+7.2f},{dhi:+7.2f}]")
dcell('all 0DTE index/ETF', dd)
for ep in (1, 2): dcell(f'epoch {ep}', dd.filter(pl.col('epoch') == ep))
for rt in ('SPY', 'QQQ', 'IWM', 'SPXW'): dcell(f'root {rt}', dd.filter(pl.col('root') == rt))
for d in (1, -1): dcell('calls' if d > 0 else 'puts', dd.filter(pl.col('direction') == d))
df.write_csv(f'{R}/results/G_direction_rows.csv'); dd.write_csv(f'{R}/results/G_day_selection_rows.csv')
json.dump({'direction': out, 'day_selection': ds_out}, open(f'{R}/results/G_edge_crossref.json', 'w'), indent=1, default=str)
log('EDGE CROSSREF DONE')
