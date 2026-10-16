"""Where the money goes on each tested trade: the same trade priced at the mid (no bid/ask paid) against its executable
result, and the difference split into the bid/ask paid at entry, at exit, and fees. Descriptive; no test is re-run and no
rule is changed. Also re-derives every V3 fill from the raw quotes as a check on the original build.
  python3 -I where_money_goes.py v3|v1|v8|lc0dte
"""
import datetime as dt, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import numpy as np, polars as pl
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
CACHE = os.path.join(SP, 'theta', 'fetch_cache')
OUT = os.path.join(HERE, '..', 'results', 'v1', 'where_money_goes'); os.makedirs(OUT, exist_ok=True)
FEE = 0.70

def v3():
    T = pl.read_parquet(os.path.join(HERE, '..', 'results', 'v1', 'v3_single_name_0dte', 'trades.parquet'))
    rows = []
    for r in T.iter_rows(named=True):
        d = r['session']; f = os.path.join(CACHE, 'chains_exp', r['root'], f'{d}__{d}.parquet')
        ch = pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'bid', 'ask']).with_columns(pl.col('timestamp').dt.replace_time_zone(None))
        q = {}
        for t in (dt.time(10, 0), dt.time(15, 50)):
            s = ch.filter((pl.col('timestamp') == dt.datetime.combine(d, t)) & (pl.col('strike') == r['K']))
            for k, rt, b, a in s.select('strike', 'right', 'bid', 'ask').iter_rows(): q[(t.hour, rt)] = (b, a)
        ci, pi = q.get((10, 'CALL')), q.get((10, 'PUT')); co, po = q.get((15, 'CALL')), q.get((15, 'PUT'))
        out = dict(symbol=r['symbol'], session=d, split=r['split'], event=r['event'], rel_spread=r['rel_spread'], mid_in=r['straddle_mid'])
        if r['a_status'] == 'ok' and None not in (ci, pi, co, po):
            mid_out = (co[0] + co[1] + po[0] + po[1]) / 2
            a_check = (ci[0] + pi[0] - co[1] - po[1]) * 100 - 4 * FEE
            out.update(mid_out=mid_out, a_pnl=r['a_pnl'], a_check=a_check,
                       short_at_mid=(r['straddle_mid'] - mid_out) * 100, long_at_mid=(mid_out - r['straddle_mid']) * 100,
                       spread_in=(r['straddle_mid'] - ci[0] - pi[0]) * 100, spread_out_short=(co[1] + po[1] - mid_out) * 100,
                       spread_out_long=(mid_out - co[0] - po[0]) * 100, spread_in_long=(ci[1] + pi[1] - r['straddle_mid']) * 100,
                       c_pnl=r['c_pnl'], c_check=(co[0] + po[0] - ci[1] - pi[1]) * 100 - 4 * FEE)
        if r['b_status'] == 'ok':
            out.update(b_pnl=r['b_pnl'], b_at_mid=(r['b_mid'] - r['b_intrinsic']) * 100, b_spread=(r['b_mid'] - r['b_bid']) * 100, b_mid=r['b_mid'])
        rows.append(out)
    D = pl.DataFrame(rows, infer_schema_length=None); D.write_parquet(os.path.join(OUT, 'v3_trades_at_mid.parquet'))
    ok = D.filter(pl.col('a_check').is_not_null())
    print('V3 fills re-derived from raw quotes:', ok.height, 'trades; max |a_pnl difference|', float((ok['a_pnl'] - ok['a_check']).abs().max()),
          'max |c_pnl difference|', float((ok['c_pnl'] - ok['c_check']).abs().max()))
    P = D.filter(~pl.col('event'))
    res = []
    for sp, f in (('Development + validation', pl.col('split') != 'holdout'), ('Hold-out', pl.col('split') == 'holdout')):
        g = P.filter(f & pl.col('a_check').is_not_null()); prem = g['mid_in'] * 100
        res.append(dict(test='V3a sell the same-day straddle', window=sp, trades=g.height,
                        at_mid=float((g['short_at_mid'] / prem).mean()), spread_entry=-float((g['spread_in'] / prem).mean()),
                        spread_exit=-float((g['spread_out_short'] / prem).mean()), fees=-float((4 * FEE / prem).mean()), net=float((g['a_pnl'] / prem).mean())))
        res.append(dict(test='V3c buy the same-day straddle', window=sp, trades=g.height,
                        at_mid=float((g['long_at_mid'] / prem).mean()), spread_entry=-float((g['spread_in_long'] / prem).mean()),
                        spread_exit=-float((g['spread_out_long'] / prem).mean()), fees=-float((4 * FEE / prem).mean()), net=float((g['c_pnl'] / prem).mean())))
        b = P.filter(f & pl.col('b_pnl').is_not_null()); bp = b['b_mid'] * 100
        res.append(dict(test='V3b sell the put one implied move below', window=sp, trades=b.height,
                        at_mid=float((b['b_at_mid'] / bp).mean()), spread_entry=-float((b['b_spread'] / bp).mean()), spread_exit=0.0,
                        fees=-float((FEE / bp).mean()), net=float((b['b_pnl'] / bp).mean())))
    R = pl.DataFrame(res); R.write_csv(os.path.join(OUT, 'v3.csv'))
    pl.Config.set_tbl_cols(12); pl.Config.set_tbl_width_chars(220); print(R)

def v1():
    """V1 T0: single-name monthly ATM straddles sold at the bid, held to expiry (settled at intrinsic, so no exit spread)"""
    T = pl.read_parquet(os.path.join(HERE, '..', 'results', 'v1', 'v1_vol_pricing', 'name_cycles.parquet')).filter(pl.col('r_short').is_finite())
    T = T.with_columns(((pl.col('mid') - pl.col('payoff')) / pl.col('mid')).alias('at_mid'),
                       (-(pl.col('mid') - pl.col('cb') - pl.col('pb')) / pl.col('mid')).alias('spread_entry'))
    rows = []
    for sp, f in (('Development + validation', pl.col('split').is_in(['dev', 'val'])), ('Hold-out', pl.col('split') == 'holdout')):
        g = T.filter(f)
        rows.append(dict(test='V1 T0 sell every monthly straddle (per name-month)', window=sp, trades=g.height, at_mid=float(g['at_mid'].mean()),
                         spread_entry=float(g['spread_entry'].mean()), spread_exit=0.0, fees=float((g['r_short'] - g['at_mid'] - g['spread_entry']).mean()), net=float(g['r_short'].mean())))
    R = pl.DataFrame(rows); R.write_csv(os.path.join(OUT, 'v1.csv')); print(R)

def v8():
    """V8: the month-end 13:00 straddle bought at the ask, held to settlement"""
    T = pl.read_parquet(os.path.join(HERE, '..', 'results', 'v1', 'v8_monthend', 'trades.parquet'))
    rows = []
    for root, g in T.group_by('root', maintain_order=True):
        at_mid = (g['pay'] - g['mid']) / g['mid']; spr = -(g['ask'] - g['mid']) / g['mid']
        rows.append(dict(test=f'V8 buy the month-end straddle, {root[0]}', window='Unread data', trades=g.height, at_mid=float(at_mid.mean()),
                         spread_entry=float(spr.mean()), spread_exit=0.0, fees=float((g['r'] - at_mid - spr).mean()), net=float(g['r'].mean())))
    R = pl.DataFrame(rows); R.write_csv(os.path.join(OUT, 'v8.csv')); print(R)

def lc0dte():
    """The 12 same-day setups (lifecycle stage 1), every trade held to expiry (M0_expiry: settled at intrinsic, no exit
    spread), development + validation, setups pooled: the trade at the entry mid against its executable result"""
    sys.path.insert(0, os.path.join(HERE, '..', 'lifecycle'))
    import json
    from lc import runner
    W = os.path.join(SP, 'lifecycle', 'runs', 'stage1'); fr = []
    for r in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        ix = json.load(open(f'{W}/{r}/run.json'))['policies'].index('M0_expiry')
        o = pl.scan_parquet(f'{W}/{r}/outcomes.parquet').filter(pl.col('policy') == ix).select('pos_id', 'filled', 'pnl', 'fees')
        p = pl.scan_parquet(f'{W}/{r}/positions.parquet').filter((pl.col('ctrl') == -1) & (pl.col('session') < runner.HOLDOUT_START)).select('pos_id', 'structure', 'mark0', 'cost0')
        fr.append(o.join(p, on='pos_id').filter(pl.col('filled') > 0).collect())
    D = pl.concat(fr).with_columns((pl.col('cost0') - pl.col('mark0')).alias('spread_in'))
    D = D.with_columns((pl.col('pnl') + pl.col('spread_in') + pl.col('fees')).alias('pnl_mid'))
    S = D.group_by('structure').agg(pl.len().alias('trades'), pl.col('pnl_mid').mean().alias('at_mid_usd'), (-pl.col('spread_in')).mean().alias('spread_usd'),
        (-pl.col('fees')).mean().alias('fees_usd'), pl.col('pnl').mean().alias('net_usd'), pl.col('mark0').abs().mean().alias('premium_usd'),
        (pl.col('pnl_mid').sum() / pl.col('mark0').abs().sum()).alias('at_mid_share'), (pl.col('pnl').sum() / pl.col('mark0').abs().sum()).alias('net_share')).sort('structure')
    S.write_csv(os.path.join(OUT, 'lifecycle_0dte_hold_to_expiry.csv')); print(S)

if __name__ == '__main__':
    {'v3': v3, 'v1': v1, 'v8': v8, 'lc0dte': lc0dte}[sys.argv[1]]()
