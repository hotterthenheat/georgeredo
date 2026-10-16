"""Step 3d: the one family of rules that made money in both 2022-2024 and 2025-2026, stress-tested.

The rule (exits.csv's best survivor, read off the whole family): buy the call (and, as a mirror, the put) 0-0.5% out of
the money at 9:31 am, sell at the bid if it falls to half the price paid, otherwise sell at the bid 30 minutes before the
close. Fees as in summarize.py. For each product and side:
- the average result per trade, every year on its own,
- a 95% range for the average by resampling whole days (2,000 draws, days with replacement),
- the average once the best 5 and the best 20 days are left out.
Writes step3/out/stress.csv.
  python3 -I step3/stress.py
"""
import os, random
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
FEE = 0.65

def load(root):
    P = pl.read_parquet(os.path.join(OUT, f'paths_{root}.parquet'))
    F = pl.read_parquet(os.path.join(OUT, f'features_{root}.parquet')).select('session', 'entry_minute', 'spot_entry', 'spot_close', 'close_minute')
    T = P.join(F, on=['session', 'entry_minute'])
    sgn = pl.when(pl.col('right') == 'CALL').then(1.0).otherwise(-1.0)
    return T.with_columns(
        pl.when(pl.col('right') == 'CALL').then((pl.col('spot_close') - pl.col('strike')).clip(0)).otherwise((pl.col('strike') - pl.col('spot_close')).clip(0)).alias('settle'),
        (sgn * (pl.col('strike') - pl.col('spot_entry')) / pl.col('spot_entry') * 100).alias('otm'))

def rule(T):
    xm = pl.when(pl.col('entry_minute') < pl.col('close_minute') - 30).then(pl.col('close_minute') - 30)
    by_stop = pl.col('s50').is_not_null() & (xm.is_null() | (pl.col('s50') <= xm))
    timed = xm.is_not_null() & pl.col('c30_bid').is_not_null()
    price = pl.when(by_stop).then(pl.col('s50_bid')).when(timed).then(pl.col('c30_bid')).otherwise(pl.col('settle'))
    sold = by_stop | timed | (pl.col('settle') > 0)
    T = T.with_columns(((price - pl.col('entry_ask')) * 100 - FEE - pl.when(sold).then(FEE).otherwise(0.0)).alias('net'))
    return T.with_columns((pl.col('net') / (pl.col('entry_ask') * 100)).alias('r'))

rows = []
for root in ('SPXW', 'SPY', 'QQQ', 'IWM'):
    S = rule(load(root).filter((pl.col('entry_minute') == 1) & (pl.col('otm') > 0) & (pl.col('otm') <= 0.5)))
    product = 'SPX' if root == 'SPXW' else root
    for right in ('CALL', 'PUT'):
        X = S.filter(pl.col('right') == right)
        day = X.group_by('session').agg(pl.col('r').sum().alias('s'), pl.len().alias('n')).sort('session')   # sorted: the same draws every run
        random.seed(20261016); s = day['s'].to_list(); n = day['n'].to_list(); bs = []
        for _ in range(2000):
            idx = [random.randrange(len(s)) for _ in s]
            bs.append(sum(s[i] for i in idx) / sum(n[i] for i in idx))
        bs.sort()
        top = day.sort('s', descending=True)
        def without(k):
            t = top.head(k); return (X['r'].sum() - t['s'].sum()) / (X.height - t['n'].sum())
        base = dict(product=product, right=right, trades=X.height, days=day.height, win_rate=(X['net'] > 0).mean(), avg_pct=X['r'].mean(),
                    ci_low=bs[50], ci_high=bs[1949], without_best_5_days=without(5), without_best_20_days=without(20))
        for y in sorted(X['session'].dt.year().unique().to_list()):
            Y = X.filter(pl.col('session').dt.year() == y)
            base[f'avg_pct_{y}'] = Y['r'].mean(); base[f'trades_{y}'] = Y.height
        rows.append(base)
R = pl.DataFrame(rows, infer_schema_length=None)
R = R.with_columns([pl.col(c).round(6) for c, t in R.schema.items() if t == pl.Float64]).with_columns(
    pl.concat_str([pl.col('product'), pl.col('right')], separator=' | ').alias('id'))
R.write_csv(os.path.join(OUT, 'stress.csv'))
pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(260)
print(R)
