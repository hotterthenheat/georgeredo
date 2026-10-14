"""Run one setup family over a symbol list and a date range: signals -> expiration -> contract -> NBBO simulation, with
the one-position rule, matched random-entry baselines and versioned outputs (04_protocol.md §5-§7, §11).

Outputs in out_dir: config.json, trades.parquet (one row per signal: filled trades carry pnl, unfilled carry the reason),
baseline_{seed}.parquet, summary.json. Every row keeps the signal's feature snapshot so ablations and regime tables can be
built without re-running.
"""
from __future__ import annotations
import datetime as dt
import hashlib, json, os, time
import numpy as np
import polars as pl
from . import calendar as cal, contracts, signals, sim, stats

FAMILIES = {
    'quick_scalps': dict(category='0dte', signal={'entry_start_minute': 15, 'entry_end_minute': 320}, exits={'max_hold_min': 60, 'session_cutoff_minute': 380},
                         symbols_rule='index_products', warmup_sessions=30),
}

def _cfg_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:12]

def _snapshot_at(chain: pl.DataFrame, ts: dt.datetime) -> pl.DataFrame:
    return chain.filter(pl.col('timestamp') == ts).select(['strike', 'right', 'bid', 'ask', 'bid_size', 'ask_size'])

def _quotes_for(chain: pl.DataFrame, strike: float, right: str) -> pl.DataFrame:
    return chain.filter((pl.col('strike') == strike) & (pl.col('right') == right)).select(['timestamp', 'bid', 'ask']).sort('timestamp')

FEATURE_COLS = ['rsi', 'ema_fast', 'ema_lead', 'ema_mid', 'ema_slow', 'ema_long', 'vwap', 'vwap_sigma', 'cum_vol', 'relvol', 'atr',
                'close_5m', 'ema_mid_5m', 'struct_5m', 'swing_hi_5m', 'swing_lo_5m', 'close_15m', 'ema_mid_15m', 'ema_slow_15m', 'ema_long_15m',
                'close_d', 'ema_mid_d', 'ema_slow_d', 'ema_long_d', 'f_confirm_5m', 'f_align_15m', 'f_daily', 'f_relvol', 'f_structure']

def trade_one(store, root: str, chain: pl.DataFrame, e: dict, last_trading_day: dt.date, feat: pl.DataFrame, select_params: dict, exit_params: dict,
              oi: pl.DataFrame | None = None, ohlc: pl.DataFrame | None = None) -> dict:
    base = {k: e.get(k) for k in ['session', 'close_ts', 'minute', 'direction', 'spot', 'invalidation_level'] + FEATURE_COLS}
    base.update({'symbol': root, 'expiration': last_trading_day})
    snap = _snapshot_at(chain, e['close_ts'])
    if snap.height == 0: return {**base, 'status': 'no_chain_snapshot'}
    if oi is not None and oi.height: snap = snap.join(oi.select(['strike', 'right', 'open_interest']), on=['strike', 'right'], how='left')
    if ohlc is not None and ohlc.height:
        cum = ohlc.filter(pl.col('timestamp') <= e['close_ts']).group_by(['strike', 'right']).agg(pl.col('volume').sum().alias('cum_volume'))
        snap = snap.join(cum, on=['strike', 'right'], how='left').with_columns(pl.col('cum_volume').fill_null(0))
    t = contracts.years_to_expiry(e['close_ts'], last_trading_day)
    row, diag = contracts.select(snap, float(e['spot']), t, int(e['direction']), select_params)
    base.update({f'diag_{k}': v for k, v in diag.items()})
    if row is None: return {**base, 'status': 'no_eligible_contract'}
    base.update({'strike': row['strike'], 'right': row['right'], 'delta': row['delta_abs'], 'iv': row['iv'], 'spread_pct': row['spread_pct'], 'bid0': row['bid'], 'ask0': row['ask'], 'ask_size0': row.get('ask_size')})
    quotes = _quotes_for(chain, row['strike'], row['right'])
    tr = sim.simulate(e, {**row, 'last_trading_day': last_trading_day}, quotes, feat, exit_params)
    if tr is None: return {**base, 'status': 'no_quotes'}
    if tr['status'] != 'filled': return {**base, 'status': tr['status'], 'reason': tr.get('reason')}
    return {**base, **{k: v for k, v in tr.items() if k != 'status'}, 'status': 'filled'}

def run_family(store, family: str, symbols: list[str], start: dt.date, end: dt.date, out_dir: str, signal_params: dict | None = None,
               select_params: dict | None = None, exit_params: dict | None = None, one_position: bool = True, baseline_seeds=(11, 12, 13, 14, 15),
               baseline_window_min: int = 45, log=print) -> dict:
    fam = FAMILIES[family]
    sp = {**signals.BASELINE, **fam['signal'], **(signal_params or {})}
    cp = {**contracts.SELECT, **(select_params or {})}
    xp = {**sim.EXITS, **fam['exits'], **(exit_params or {})}
    cfg = {'family': family, 'symbols': symbols, 'start': str(start), 'end': str(end), 'signal': sp, 'select': cp, 'exits': xp, 'one_position': one_position,
           'baseline_seeds': list(baseline_seeds), 'baseline_window_min': baseline_window_min, 'engine_version': '0.1.0'}
    os.makedirs(out_dir, exist_ok=True)
    json.dump(cfg, open(os.path.join(out_dir, 'config.json'), 'w'), indent=1, default=str)
    rows, base_rows = [], {s: [] for s in baseline_seeds}
    t0 = time.time()
    for sym in symbols:
        warm = cal.prev_session(start, fam['warmup_sessions'])
        df1 = store.bars(sym, warm, end)
        if df1.height == 0: log(f'{sym}: no bars'); continue
        feat = signals.features(df1, sp)
        ev = signals.baseline_events(feat, sp).filter(pl.col('session') >= start)
        log(f'{sym}: bars {df1.height} events {ev.height}')
        exps = store.expirations(sym)
        open_until = None; n_tr = 0; n_days = 0
        for d, day in ev.group_by('session', maintain_order=True):
            d = d[0] if isinstance(d, tuple) else d
            n_days += 1
            if n_days % 100 == 0: log(f'{sym}: {d} days {n_days} filled {n_tr} ({time.time() - t0:.0f}s)')
            exp = contracts.pick_expiration(exps, d, fam['category'], sym)
            if exp is None:
                for e in day.iter_rows(named=True): rows.append({**{k: e.get(k) for k in ['session', 'close_ts', 'minute', 'direction', 'spot']}, 'symbol': sym, 'status': 'no_expiration_in_category'})
                continue
            ltd = cal.last_trading_day(exp, cal.is_spx_am_settled(sym, exp))
            chain = store.chain_minutes(sym, d, exp)
            if chain is None:
                for e in day.iter_rows(named=True): rows.append({**{k: e.get(k) for k in ['session', 'close_ts', 'minute', 'direction', 'spot']}, 'symbol': sym, 'expiration': exp, 'status': 'no_chain_data'})
                continue
            fday = feat.filter(pl.col('session') == d)
            oi = store.open_interest(sym, d, exp) if (cp.get('min_oi') is not None) else None
            ohlc = store.chain_ohlc(sym, d, exp) if (cp.get('min_volume') is not None) else None
            for e in day.sort('close_ts').iter_rows(named=True):
                if one_position and open_until is not None and e['close_ts'] < open_until:
                    rows.append({**{k: e.get(k) for k in ['session', 'close_ts', 'minute', 'direction', 'spot']}, 'symbol': sym, 'expiration': exp, 'status': 'in_position'}); continue
                r = trade_one(store, sym, chain, e, ltd, fday, cp, xp, oi, ohlc)
                rows.append(r)
                if r['status'] == 'filled':
                    n_tr += 1
                    if one_position: open_until = r['exit_ts']
                    # matched random baselines: same symbol, date, direction, contract rule and exits; random decision minute within ±window
                    for seed in baseline_seeds:
                        rng = np.random.default_rng(seed * 1_000_003 + int(hashlib.sha256(f'{sym}|{d}|{int(e["minute"])}'.encode()).hexdigest()[:8], 16))
                        lo = max(sp['entry_start_minute'], int(e['minute']) - baseline_window_min); hi = min(sp['entry_end_minute'], int(e['minute']) + baseline_window_min)
                        m = int(rng.integers(lo, hi + 1))
                        fr = fday.filter(pl.col('minute') == m)
                        if fr.height == 0: continue
                        fe = fr.row(0, named=True)
                        be = {**fe, 'direction': e['direction'], 'spot': fe['close'], 'invalidation_level': fe['swing_lo_5m'] if e['direction'] > 0 else fe['swing_hi_5m']}
                        br = trade_one(store, sym, chain, be, ltd, fday, cp, xp, oi, ohlc)
                        base_rows[seed].append({**br, 'matched_minute': int(e['minute']), 'seed': seed})
        log(f'{sym}: filled {n_tr} ({time.time() - t0:.0f}s)')
    trades = pl.DataFrame(rows, infer_schema_length=None) if rows else pl.DataFrame()
    trades.write_parquet(os.path.join(out_dir, 'trades.parquet'))
    for seed, br in base_rows.items():
        if br: pl.DataFrame(br, infer_schema_length=None).write_parquet(os.path.join(out_dir, f'baseline_{seed}.parquet'))
    summ = summarize(out_dir)
    json.dump(summ, open(os.path.join(out_dir, 'summary.json'), 'w'), indent=1, default=str)
    return summ

def summarize(out_dir: str) -> dict:
    trades = pl.read_parquet(os.path.join(out_dir, 'trades.parquet'))
    out = {'signals': int(trades.height), 'status_counts': {k: int(v) for k, v in trades.group_by('status').len().iter_rows()} if trades.height else {}}
    filled = trades.filter(pl.col('status') == 'filled') if trades.height else trades
    out['filled'] = filled.height
    if filled.height == 0: return out
    filled = filled.with_columns(pl.col('session').dt.year().alias('year'))
    out['all'] = stats.summary(filled)
    out['by_year'] = stats.by_group(filled, ['year']).to_dicts()
    out['by_symbol'] = stats.by_group(filled, ['symbol']).to_dicts()
    out['by_direction'] = stats.by_group(filled, ['direction']).to_dicts()
    out['by_exit'] = {k: int(v) for k, v in filled.group_by('exit_reason').len().iter_rows()}
    bases = []
    for f in sorted(os.listdir(out_dir)):
        if f.startswith('baseline_') and f.endswith('.parquet'):
            b = pl.read_parquet(os.path.join(out_dir, f)); bf = b.filter(pl.col('status') == 'filled')
            if bf.height: bases.append({'seed': int(f.split('_')[1].split('.')[0]), **{k: v for k, v in stats.summary(bf).items() if k in ('n', 'mean', 'ci_lo', 'ci_hi', 'win_rate', 'profit_factor', 'net_total')}})
    out['baselines'] = bases
    if bases:
        pooled = pl.concat([pl.read_parquet(os.path.join(out_dir, f)).filter(pl.col('status') == 'filled') for f in sorted(os.listdir(out_dir)) if f.startswith('baseline_')], how='diagonal_relaxed')
        out['baseline_pooled'] = {k: v for k, v in stats.summary(pooled).items() if k in ('n', 'mean', 'ci_lo', 'ci_hi', 'win_rate', 'profit_factor')}
        # paired by (symbol, session, matched minute): strategy trade minus the mean of its baseline draws
        key = ['symbol', 'session', 'minute']
        bm = pooled.group_by(['symbol', 'session', 'matched_minute']).agg(pl.col('pnl').mean().alias('pnl_base')).rename({'matched_minute': 'minute'})
        pairs = filled.join(bm, on=key, how='inner')
        if pairs.height:
            m, lo, hi = stats.cluster_bootstrap_ci((pairs['pnl'] - pairs['pnl_base']).to_numpy(), pairs['session'].cast(pl.Utf8).to_numpy())
            out['strategy_minus_baseline'] = {'n_pairs': pairs.height, 'mean': m, 'ci_lo': lo, 'ci_hi': hi, 'round_trip_cost_mean': float((filled['commission'] + (filled['ask0'] - filled['bid0']) * 100).mean())}
    return out
