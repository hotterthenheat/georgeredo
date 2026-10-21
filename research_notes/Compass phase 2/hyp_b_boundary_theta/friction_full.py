"""Where the short spread's result comes from, on EVERY vertical in out/trades_<P>.parquet (the engine's rows carry the
legs' other sides: short_ask, long_bid). Writes out/friction_full.csv.   python3 -I friction_full.py
A (product, period, test, structure, rule, width) cell: N, the credit at the NBBO fill, the credit at the legs' mids, the
bid-ask cost (mid credit - fill credit, $ a spread), fees ($1.30 a vertical, entry only, held to settlement), the hold P&L at
the fill with fees (the engine's), the hold P&L at the mid with no fees (the premium's own expectancy), both as % of max
risk, and the share of the mid's gross result the friction takes. The touch rows are one a touch minute (de-duplicated
as analyze.py does); the scheduled rows are every scan.
"""
import os, numpy as np, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
period_col = pl.when(pl.col('session') <= '2024-12-31').then(pl.lit('fit 2022-2024')).otherwise(pl.lit('oos 2025-2026')).alias('period')
rows = []
for P in ('SPXW', 'SPY'):
    X = pl.read_parquet(os.path.join(OUT, f'trades_{P}.parquet')).filter(pl.col('structure') != 'condor').with_columns(period_col)
    X = pl.concat([X.filter(pl.col('test') == 'sched'),
                   X.filter(pl.col('test') == 'touch').sort('session', 'touch_side', 'e', 'mult', 'rule', 'width', 'm_scan').unique(subset=['session', 'touch_side', 'e', 'mult', 'rule', 'width'], keep='first')])
    X = X.with_columns((((pl.col('short_bid') + pl.col('short_ask')) / 2) - ((pl.col('long_ask') + pl.col('long_bid')) / 2)).alias('credit_mid'))
    X = X.with_columns(((pl.col('credit_mid') - pl.col('settle_val')) * 100).alias('pnl_mid'), ((pl.col('credit_mid') - pl.col('credit')) * 100).alias('spread_cost'))
    for (period, test, mult, structure, rule, width), g in X.group_by('period', 'test', 'mult', 'structure', 'rule', 'width'):
        if test == 'touch' and mult != 1.0: continue
        gross = float(g['pnl_mid'].sum()); fric = float((g['spread_cost'] + 1.30).sum())
        rows.append(dict(product=P, period=period, test=test, structure=structure, rule=rule, width=width, N=g.height, sessions=g['session'].n_unique(),
                         credit_fill=float(g['credit'].mean()), credit_mid=float(g['credit_mid'].mean()), spread_cost_usd=float(g['spread_cost'].mean()), fees_usd=1.30,
                         pnl_hold_fill_fees=float(g['pnl_hold'].mean()), pnl_hold_mid_nofee=float(g['pnl_mid'].mean()),
                         pct_risk_fill=float((g['pnl_hold'] / g['max_risk']).mean() * 100), pct_risk_mid=float((g['pnl_mid'] / g['max_risk']).mean() * 100),
                         friction_pct_risk=float(((g['spread_cost'] + 1.30) / g['max_risk']).mean() * 100), win_rate_mid=float((g['pnl_mid'] > 0).mean())))
F = pl.DataFrame(rows).sort('product', 'period', 'test', 'structure', 'rule', 'width')
F.write_csv(os.path.join(OUT, 'friction_full.csv'))
pl.Config.set_tbl_rows(400); pl.Config.set_tbl_width_chars(260); pl.Config.set_float_precision(2)
print(F.select('product', 'period', 'test', 'structure', 'rule', 'width', 'N', 'credit_fill', 'credit_mid', 'spread_cost_usd', 'pnl_hold_fill_fees', 'pnl_hold_mid_nofee', 'pct_risk_fill', 'pct_risk_mid', 'friction_pct_risk'))
