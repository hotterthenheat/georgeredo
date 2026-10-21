"""Where the short spread's result comes from: the same trades priced at the MID with no fees against their NBBO fills with
fees, on a random sample of sessions (the chain is re-read for the legs' other side). Writes out/friction.csv.
    python3 -I friction.py [sessions_per_product=80]
Columns a (product, period, test, structure, rule, width): N, credit at the fill, credit at the mid, the spread cost
(mid - fill, $ a spread x100), fees, hold P&L at the fill with fees (engine's), hold P&L at the mid with no fees, and the
share of the hold P&L's gap that is the bid-ask against the fees.
"""
import os, random, sys, numpy as np, polars as pl
RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
NS = int(sys.argv[1]) if len(sys.argv) > 1 else 80
random.seed(11)

def minute_of(col):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

rows = []
for root in ('SPXW', 'SPY'):
    X = pl.read_parquet(os.path.join(OUT, f'trades_{root}.parquet')).filter(pl.col('structure') != 'condor')
    for period, lo, hi in (('fit 2022-2024', '2022-01-01', '2024-12-31'), ('oos 2025-2026', '2025-01-01', '2026-12-31')):
        sess = sorted(set(X.filter((pl.col('session') >= lo) & (pl.col('session') <= hi))['session'].to_list()))
        pick = sorted(random.sample(sess, min(NS, len(sess))))
        parts = []
        for d in pick:
            c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask']).with_columns(minute_of('timestamp').alias('e')).drop('timestamp')
            c = c.with_columns(pl.when(pl.col('right') == 'CALL').then(pl.lit('call')).otherwise(pl.lit('put')).alias('structure'))
            t = X.filter(pl.col('session') == d)
            t = t.join(c.select('structure', pl.col('strike').alias('short_k'), 'e', pl.col('ask').alias('short_ask')), on=['structure', 'short_k', 'e'], how='left') \
                 .join(c.select('structure', pl.col('strike').alias('long_k'), 'e', pl.col('bid').alias('long_bid')), on=['structure', 'long_k', 'e'], how='left')
            parts.append(t)
        T = pl.concat(parts).with_columns((((pl.col('short_bid') + pl.col('short_ask')) / 2) - ((pl.col('long_ask') + pl.col('long_bid')) / 2)).alias('credit_mid'))
        T = T.with_columns(((pl.col('credit_mid') - pl.col('settle_val')) * 100).alias('pnl_hold_mid_nofee'), ((pl.col('credit_mid') - pl.col('credit')) * 100).alias('spread_cost'))
        for (test, structure, rule, width), g in T.group_by('test', 'structure', 'rule', 'width'):
            rows.append(dict(product=root, period=period, sessions=len(pick), test=test, structure=structure, rule=rule, width=width, N=g.height,
                             credit_fill=float(g['credit'].mean()), credit_mid=float(g['credit_mid'].mean()), spread_cost_usd=float(g['spread_cost'].mean()), fees_usd=1.30,
                             pnl_hold_fill_fees=float(g['pnl_hold'].mean()), pnl_hold_mid_nofee=float(g['pnl_hold_mid_nofee'].mean()),
                             pnl_hold_mid_pct_risk=float((g['pnl_hold_mid_nofee'] / g['max_risk']).mean() * 100), pnl_hold_fill_pct_risk=float((g['pnl_hold'] / g['max_risk']).mean() * 100)))
F = pl.DataFrame(rows).sort('product', 'period', 'test', 'structure', 'rule', 'width')
F.write_csv(os.path.join(OUT, 'friction.csv'))
pl.Config.set_tbl_rows(300); pl.Config.set_tbl_width_chars(250); pl.Config.set_float_precision(2)
print(F)
