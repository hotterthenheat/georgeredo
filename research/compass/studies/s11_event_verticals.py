"""Study S11 (amendments A4, A5.2) on the per-event option EOD chains pulled by s11_pull_event_chains.py:
  breakout20 / beat_top_tercile: short vertical (short leg nearest 0.30 delta, long leg nearest 0.15 delta, same side as
    the fade) sold at the event session's close, bought back at the close 21 sessions later or when the daily mark reaches
    2x the credit; calls for upward breakouts and beats, puts for downward breakouts.
  pre_earnings: long the nearest-0.50-delta call / the ATM straddle / a 0.30-0.15 debit call vertical at the close 10
    sessions before the event session, sold at the close of the session before the event session; ATM implied vol at
    entry and exit recorded.
Each event has a matched control date (same symbol and year, away from reports) with the same structures.
Legs at the end-of-day NBBO (short: bid in / ask out; long: ask in / bid out), $0.70 per contract per side per leg,
adverse one-tick scenario. Usage: python3 s11_event_verticals.py"""
import datetime as dt, glob, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import greeks as g, stats, calendar as cal
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
HERE = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(SP, 'theta', 'fetch_cache')
OUT = os.path.join(HERE, '..', 'results', 'v1', 's11_event_verticals'); os.makedirs(OUT, exist_ok=True)
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
FEE = 0.70; R = 0.04
ev = pl.read_parquet(os.path.join(CACHE, 's11_events.parquet'))
log('events', ev.group_by('group').len().sort('group').to_dicts())
# daily closes for spot (the lake)
from engine import daily_screen as ds
lake = ds.load_lake(f'{SP}/lake/stock_eod', [2023, 2024, 2025, 2026]).select(['symbol', 'date', 'close'])
spot_of = {(r['symbol'], r['date']): r['close'] for r in lake.filter(pl.col('symbol').is_in(ev['symbol'].unique().to_list())).iter_rows(named=True)}

def load_chain(sym, d, exp):
    p = os.path.join(CACHE, 'eod_exp', sym, f'{d}__{exp}.parquet')
    if not os.path.exists(p) or os.path.getsize(p) == 0: return None
    df = pl.read_parquet(p)
    if df.height == 0: return None
    dcol = next((c for c in ('created', 'timestamp', 'date', 'last_trade') if c in df.columns), None)
    if dcol is None: return None
    df = df.with_columns(pl.col(dcol).cast(pl.Datetime('ms'), strict=False).dt.date().alias('d') if df.schema[dcol] != pl.Date else pl.col(dcol).alias('d'))
    df = df.with_columns(pl.col('strike').cast(pl.Float64), pl.col('right').cast(pl.Utf8).str.to_uppercase().str.slice(0, 1))
    return df.select(['d', 'strike', 'right', 'bid', 'ask'] + [c for c in ('volume', 'open_interest') if c in df.columns])

def snap(chain, d):
    s = chain.filter(pl.col('d') == d)
    return s if s.height else None

def annotate(s, spot, T):
    K = s['strike'].to_numpy(); bid = s['bid'].to_numpy().astype(float); ask = s['ask'].to_numpy().astype(float); right = s['right'].to_numpy().astype(str)
    mid = (bid + ask) / 2
    iv = g.implied_vol(mid, spot, K, max(T, 1e-4), right, R, 0.0)
    delta = np.abs(g.delta(spot, K, max(T, 1e-4), np.where(np.isnan(iv), 0.3, iv), right, R, 0.0))
    return s.with_columns(pl.Series('mid', mid), pl.Series('iv', iv), pl.Series('delta_abs', np.where(np.isnan(iv), np.nan, delta)))

def nearest(s, right, target, lo, hi, beyond=None):
    c = s.filter((pl.col('right') == right) & pl.col('delta_abs').is_between(lo, hi) & (pl.col('ask') > 0) & (pl.col('ask') >= pl.col('bid')))
    if beyond is not None: c = c.filter((pl.col('strike') > beyond) if right == 'C' else (pl.col('strike') < beyond))
    if c.height == 0: return None
    return c.with_columns((pl.col('delta_abs') - target).abs().alias('_d')).sort('_d').row(0, named=True)

def quote(chain, d, strike, right):
    r = chain.filter((pl.col('d') == d) & (pl.col('strike') == strike) & (pl.col('right') == right))
    return None if r.height == 0 else r.row(0, named=True)

def T_years(d, exp): return max((exp - d).days, 1) / 365.25

rows = []; t0 = time.time(); missing = 0
for i, e in enumerate(ev.iter_rows(named=True)):
    sym, d, exp, grp = e['symbol'], e['date'], e['expiration'], e['group']
    base = {'symbol': sym, 'event_date': e['event_date'], 'date': d, 'expiration': exp, 'group': grp, 'year': e['year'], 'direction': e['direction']}
    chain = load_chain(sym, d, exp)
    if chain is None: missing += 1; rows.append({**base, 'status': 'no_chain'}); continue
    dates = sorted(chain['d'].unique().to_list())
    kind = grp.replace('_control', '')
    if kind in ('breakout20', 'beat_top_tercile'):
        entry_d = d; spot = spot_of.get((sym, entry_d))
        if spot is None or entry_d not in dates: rows.append({**base, 'status': 'no_entry'}); continue
        s = annotate(snap(chain, entry_d), spot, T_years(entry_d, exp))
        right = 'C' if e['direction'] > 0 else 'P'  # fade: sell calls into upward breakouts / beats, puts into downward breakouts
        sh = nearest(s, right, 0.30, 0.20, 0.40); lg = nearest(s, right, 0.15, 0.05, 0.25, beyond=sh['strike']) if sh else None
        if lg is not None and abs(lg['strike'] - sh['strike']) > 0.10 * spot: lg = None  # A6: width cap 10 % of spot
        if not sh or not lg or sh['bid'] <= 0: rows.append({**base, 'status': 'no_legs'}); continue
        width = abs(lg['strike'] - sh['strike'])
        later = [x for x in dates if x > entry_d]
        exit_target = entry_d
        for _ in range(21): exit_target = cal.next_session(exit_target)
        for adverse in (0.0, 0.01):
            credit = (sh['bid'] - adverse) - (lg['ask'] + adverse)
            if credit <= 0: rows.append({**base, 'structure': 'short_vertical', 'adverse_tick': adverse, 'status': 'no_credit'}); continue
            for xs in ('stop2x', 'time_only', 'cap_half_width'):
                exit_d, reason, cost, worst = None, None, None, 0.0
                for x in later:
                    qs, ql = quote(chain, x, sh['strike'], right), quote(chain, x, lg['strike'], right)
                    if qs is None or ql is None or qs['ask'] <= 0: continue
                    ctc = (qs['ask'] + adverse) - (max(ql['bid'], 0.0) - adverse); worst = max(worst, ctc - credit)
                    if xs == 'stop2x' and ctc >= 2 * credit: exit_d, reason, cost = x, 'stop', ctc; break
                    if xs == 'cap_half_width' and ctc >= credit + 0.5 * width: exit_d, reason, cost = x, 'cap', ctc; break
                    if x >= exit_target: exit_d, reason, cost = x, 'time', ctc; break
                    exit_d, reason, cost = x, 'last_mark', ctc
                if exit_d is None: rows.append({**base, 'structure': f'short_vertical_{xs}', 'adverse_tick': adverse, 'status': 'no_exit'}); continue
                rows.append({**base, 'structure': f'short_vertical_{xs}', 'adverse_tick': adverse, 'status': 'filled', 'entry_date': entry_d, 'exit_date': exit_d, 'exit_reason': reason, 'short_strike': sh['strike'], 'short_delta': sh['delta_abs'], 'long_strike': lg['strike'], 'long_delta': lg['delta_abs'], 'width': width,
                             'credit': credit, 'exit_cost': cost, 'pnl': (credit - cost) * 100 - 4 * FEE, 'mae': worst * 100, 'hold_sessions': sum(1 for x in dates if entry_d < x <= exit_d)})
    else:  # pre_earnings: entry 10 sessions before the event session, exit the session before it
        ref = e['event_date'] if kind == 'pre_earnings' else d  # controls: hold the same 10-session window ending the day before d
        exit_d = cal.prev_session(ref, 1); entry_d = exit_d
        for _ in range(10): entry_d = cal.prev_session(entry_d, 1)
        spot0 = spot_of.get((sym, entry_d)); spot1 = spot_of.get((sym, exit_d))
        if spot0 is None or spot1 is None or entry_d not in dates or exit_d not in dates: rows.append({**base, 'status': 'no_window'}); continue
        s0 = annotate(snap(chain, entry_d), spot0, T_years(entry_d, exp)); s1 = annotate(snap(chain, exit_d), spot1, T_years(exit_d, exp))
        call = nearest(s0, 'C', 0.50, 0.40, 0.60); put = nearest(s0, 'P', 0.50, 0.40, 0.60)
        c30 = nearest(s0, 'C', 0.30, 0.20, 0.40); c15 = nearest(s0, 'C', 0.15, 0.05, 0.25, beyond=c30['strike']) if c30 else None
        atm0 = s0.with_columns((pl.col('strike') - spot0).abs().alias('_k')).sort('_k').filter(pl.col('iv').is_not_null())
        atm1 = s1.with_columns((pl.col('strike') - spot1).abs().alias('_k')).sort('_k').filter(pl.col('iv').is_not_null())
        iv0 = float(atm0['iv'][0]) if atm0.height else None; iv1 = float(atm1['iv'][0]) if atm1.height else None
        for adverse in (0.0, 0.01):
            def long_pnl(leg):
                q1 = quote(chain, exit_d, leg['strike'], leg['right'])
                if q1 is None: return None
                return ((max(q1['bid'], 0.0) - adverse) - (leg['ask'] + adverse)) * 100 - 2 * FEE, leg['ask'], q1['bid']
            if call and call['ask'] > 0:
                r = long_pnl(call)
                if r: rows.append({**base, 'structure': 'long_call_0.50', 'adverse_tick': adverse, 'status': 'filled', 'entry_date': entry_d, 'exit_date': exit_d, 'pnl': r[0], 'debit': call['ask'], 'exit_bid': r[2], 'iv_entry': iv0, 'iv_exit': iv1, 'underlying_ret_bp': (spot1 / spot0 - 1) * 1e4})
            if call and put and call['ask'] > 0 and put['ask'] > 0:
                rc, rp = long_pnl(call), long_pnl(put)
                if rc and rp: rows.append({**base, 'structure': 'long_straddle_atm', 'adverse_tick': adverse, 'status': 'filled', 'entry_date': entry_d, 'exit_date': exit_d, 'pnl': rc[0] + rp[0], 'debit': call['ask'] + put['ask'], 'iv_entry': iv0, 'iv_exit': iv1, 'underlying_ret_bp': (spot1 / spot0 - 1) * 1e4})
            if c30 and c15 and c30['ask'] > 0:
                q30, q15 = quote(chain, exit_d, c30['strike'], 'C'), quote(chain, exit_d, c15['strike'], 'C')
                if q30 and q15:
                    debit = (c30['ask'] + adverse) - (c15['bid'] - adverse); value = (max(q30['bid'], 0.0) - adverse) - (q15['ask'] + adverse)
                    rows.append({**base, 'structure': 'debit_call_vertical_0.30_0.15', 'adverse_tick': adverse, 'status': 'filled', 'entry_date': entry_d, 'exit_date': exit_d, 'pnl': (value - debit) * 100 - 4 * FEE, 'debit': debit, 'iv_entry': iv0, 'iv_exit': iv1, 'underlying_ret_bp': (spot1 / spot0 - 1) * 1e4})
    if i % 500 == 0: log(f'{i}/{ev.height} rows {len(rows)} missing chains {missing} ({time.time() - t0:.0f}s)')
df = pl.DataFrame(rows, infer_schema_length=None); df.write_parquet(os.path.join(OUT, 'trades.parquet'))
log(f'rows {df.height}, missing chains {missing}')
fl = df.filter(pl.col('status') == 'filled').with_columns(pl.col('event_date').alias('session')); out = []
for grp in ('breakout20', 'beat_top_tercile', 'pre_earnings'):
    for structure in fl.filter(pl.col('group') == grp)['structure'].unique().to_list():
        for adverse in (0.0, 0.01):
            a = fl.filter((pl.col('group') == grp) & (pl.col('structure') == structure) & (pl.col('adverse_tick') == adverse))
            c = fl.filter((pl.col('group') == grp + '_control') & (pl.col('structure') == structure) & (pl.col('adverse_tick') == adverse))
            if a.height < 20: continue
            sa = stats.summary(a, day_col='event_date'); sc = stats.summary(c, day_col='event_date') if c.height >= 30 else {}
            pr = a.join(c.select(['symbol', 'event_date', 'pnl']).rename({'pnl': 'cpnl'}), on=['symbol', 'event_date'], how='inner')
            dm, dlo, dhi = stats.cluster_bootstrap_ci((pr['pnl'] - pr['cpnl']).to_numpy(), pr['event_date'].cast(pl.Utf8).to_numpy()) if pr.height >= 30 else (None, None, None)
            by = {str(y['year']): round(y['mean'], 1) for y in stats.by_group(a, ['year']).to_dicts()}
            rec = {'group': grp, 'structure': structure, 'adverse_tick': adverse, 'n': sa['n'], 'days': sa['days'], 'mean': sa['mean'], 'ci_lo': sa['ci_lo'], 'ci_hi': sa['ci_hi'], 'win_rate': sa['win_rate'], 'profit_factor': sa['profit_factor'], 'max_drawdown': sa['max_drawdown'],
                   'control_n': sc.get('n'), 'control_mean': sc.get('mean'), 'control_lo': sc.get('ci_lo'), 'control_hi': sc.get('ci_hi'), 'minus_control': dm, 'minus_control_lo': dlo, 'minus_control_hi': dhi, 'by_year': by,
                   'premium_mean': float(a['credit'].mean() * 100) if 'credit' in a.columns and a['credit'].drop_nulls().len() else (float(a['debit'].mean() * 100) if 'debit' in a.columns and a['debit'].drop_nulls().len() else None)}
            if 'iv_entry' in a.columns and a['iv_entry'].drop_nulls().len():
                rec['iv_change_mean'] = float((a['iv_exit'] - a['iv_entry']).drop_nulls().mean()); rec['underlying_ret_bp_mean'] = float(a['underlying_ret_bp'].drop_nulls().mean())
                if c.height and 'iv_entry' in c.columns: rec['control_iv_change_mean'] = float((c['iv_exit'] - c['iv_entry']).drop_nulls().mean())
            out.append(rec)
            log(f"{grp:17s} {structure:30s} adv {adverse}: n {sa['n']:4d} mean {sa['mean']:+8.2f} [{sa['ci_lo']:+8.2f}, {sa['ci_hi']:+8.2f}] win {sa['win_rate'] * 100:.0f}% PF {sa['profit_factor']:.2f} | control {sc.get('mean', float('nan')):+8.2f} | minus control {dm if dm is None else round(dm, 2)} [{dlo if dlo is None else round(dlo, 2)}, {dhi if dhi is None else round(dhi, 2)}] | by year {by}" + (f" | IV {rec['iv_change_mean']:+.3f} vs control {rec.get('control_iv_change_mean', float('nan')):+.3f}" if 'iv_change_mean' in rec else ''))
json.dump(out, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)
log(f'S11 DONE ({time.time() - t0:.0f}s)')
