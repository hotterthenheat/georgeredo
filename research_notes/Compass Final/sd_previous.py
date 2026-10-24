"""sd_previous.py — Compass Final, stage 1: per-trade and per-session SDs of the candidates on their PREVIOUSLY READ periods
at Robinhood fees (the final report registry loaders), and the case (b) SDs from AFTERHOURS.md period ii rows. Writes out/sd_previous.json.
Run from research_notes/FINAL REPORT/build:  python3 "../../Compass Final/sd_previous.py"  (then the case (b) block below)."""
import sys, json, math
sys.path.insert(0, '.')
import polars as pl
import registry as RG, base as B
want = ['6d','6e','20a','26a','26b','26c','32','7j-atm_put','7j-put_30d']
out = {}
for st in RG.STRATEGIES:
    if st.sid not in want or st.load is None: continue
    df = B.std(st.load())
    df = df.with_columns((pl.col('pnl') + pl.col('fee_old') - pl.col('fee_rh')).alias('pnl_rh')).with_columns((pl.col('pnl_rh') / pl.col('cost') * 100).alias('pct'))
    for (period, inst), g in df.group_by(['period', 'inst']):
        s = g.group_by('date').agg(pl.col('pct').mean().alias('m'), pl.len().alias('n'))
        out[f'{st.sid}|{period}|{inst}'] = dict(n=g.height, sessions=s.height, mean=g['pct'].mean(), sd_trade=g['pct'].std(), sd_session_mean=s['m'].std(), trades_per_session=g.height / s.height)
    if st.sid in ('26b', '26a', '26c', '20a', '6d', '6e', '32'):
        for period, g in df.group_by('period'):
            s = g.group_by('date').agg(pl.col('pct').mean().alias('m'))
            out[f'{st.sid}|{period[0]}|ALL'] = dict(n=g.height, sessions=s.height, mean=g['pct'].mean(), sd_trade=g['pct'].std(), sd_session_mean=s['m'].std(), trades_per_session=g.height/s.height)
OUTP = __import__('pathlib').Path(__file__).resolve().parent / 'out' / 'sd_prev_registry.json'; json.dump(out, open(OUTP, 'w'), indent=1)
for k, v in sorted(out.items()): print(k, {a: round(b, 3) for a, b in v.items()})

# case (b), period ii, from AFTERHOURS.md's committed rows; Robinhood fees in place of $0.65 x 4: 2 buys x $0.0403 + 2 sells x $0.0603
AH = __import__('pathlib').Path(__file__).resolve().parents[1] / 'Compass phase 3' / 'backtest_audit' / 'out' / 'afterhours_trades.csv'
d = pl.read_csv(AH, infer_schema_length=100000).filter(pl.col('period') == 'ii').drop_nulls('pnl_b')
w = pl.when(pl.col('candidate') == 'fly5').then(5.0).otherwise(2.0)
d = d.with_columns(((w - pl.col('price_nbbo')) * 100).alias('risk')).with_columns(((pl.col('pnl_b') + 2.60 - 0.2012) / pl.col('risk') * 100).alias('pct_b'), ((pl.col('pnl_0') + 2.60 - 0.2012) / pl.col('risk') * 100).alias('pct_0'))
cb = {}
for c, g in d.group_by('candidate'):
    s = g.group_by('day').agg(pl.col('pct_b').mean().alias('m'))
    cb[c[0]] = dict(n=g.height, sessions=s.height, mean_b=g['pct_b'].mean(), sd_b=g['pct_b'].std(), sd_sess_b=s['m'].std(), mean_0=g['pct_0'].mean(), sd_0=g['pct_0'].std())
json.dump({'prev': out, 'caseb': cb}, open(__import__('pathlib').Path(__file__).resolve().parent / 'out' / 'sd_previous.json', 'w'), indent=1)
