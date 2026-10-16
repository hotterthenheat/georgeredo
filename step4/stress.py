"""Step 4d: every rule from step4/out/survivors.csv that made at least +5% a trade in both 2022-2024 and 2025-2026 on at
least 1,000 trades in each, stress-tested, with its mirror (the same rule on the other side) beside it:
- the average result per trade, every year on its own,
- a 95% range for the average from resampling whole days (2,000 draws, days with replacement),
- the average once the best 5 and the best 20 days are left out, and the share of the total made on the best 5 days,
- how many days the rule traded and how many of them made money.
Writes step4/out/stress.csv.
  python3 -I step4/stress.py
"""
import os, random
import polars as pl

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
FEE = 0.65
DIST = [(-1e9, -1.0, 'ITM more than 1%'), (-1.0, -0.5, 'ITM 0.5–1%'), (-0.5, -0.25, 'ITM 0.25–0.5%'), (-0.25, 0.0, 'ITM 0–0.25%'),
        (0.0, 0.25, 'OTM 0–0.25%'), (0.25, 0.5, 'OTM 0.25–0.5%'), (0.5, 1.0, 'OTM 0.5–1%'), (1.0, 2.0, 'OTM 1–2%'), (2.0, 1e9, 'OTM more than 2%')]
PRICE = [(0, 10, 'Under $10'), (10, 25, '$10–25'), (25, 50, '$25–50'), (50, 100, '$50–100'), (100, 200, '$100–200'), (200, 500, '$200–500'),
         (500, 1000, '$500–1,000'), (1000, 1e12, 'Over $1,000')]
ROOT = {'SPX': 'SPXW', 'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM'}

def band(col, edges, name):
    b = pl.lit(None, pl.Utf8)
    for lo, hi, lab in edges:
        b = pl.when((pl.col(col) > lo) & (pl.col(col) <= hi)).then(pl.lit(lab)).otherwise(b)
    return b.alias(name)

def trades(product):
    T = pl.read_parquet(os.path.join(OUT, f'trades_{ROOT[product]}.parquet'))
    sgn = pl.when(pl.col('right') == 'CALL').then(1.0).otherwise(-1.0)
    T = T.with_columns(
        pl.when(pl.col('right') == 'CALL').then((pl.col('spot_close') - pl.col('strike')).clip(0)).otherwise((pl.col('strike') - pl.col('spot_close')).clip(0)).alias('settle'),
        (sgn * (pl.col('strike') - pl.col('spot_entry')) / pl.col('spot_entry') * 100).alias('otm'), (pl.col('entry_ask') * 100).alias('cost'))
    return T.with_columns(band('otm', DIST, 'distance'), band('cost', PRICE, 'price'))

def result(T, x):
    if x == 'hold':
        price, sold = pl.col('settle'), pl.col('settle') > 0
    else:
        hit = pl.col(x + '_minute').is_not_null()
        price = pl.when(hit).then(pl.col(x + '_bid')).otherwise(pl.col('settle')); sold = hit | (pl.col('settle') > 0)
    net = (price - pl.col('entry_ask')) * 100 - FEE - pl.when(sold).then(FEE).otherwise(0.0)
    return T.with_columns(net.alias('net'), (net / pl.col('cost')).alias('r'))

def stress(X):
    day = X.group_by('session').agg(pl.col('r').sum().alias('s'), pl.len().alias('n')).sort('session')
    random.seed(20261016); s = day['s'].to_list(); n = day['n'].to_list(); bs = []
    for _ in range(2000):
        idx = [random.randrange(len(s)) for _ in s]
        bs.append(sum(s[i] for i in idx) / sum(n[i] for i in idx))
    bs.sort()
    top = day.sort('s', descending=True)
    def without(k):
        t = top.head(k); return (X['r'].sum() - t['s'].sum()) / (X.height - t['n'].sum())
    total = X['r'].sum()
    o = dict(trades=X.height, days=day.height, days_up=int((day['s'] > 0).sum()), win_rate=(X['net'] > 0).mean(), avg_pct=X['r'].mean(),
             ci_low=bs[50], ci_high=bs[1949], without_best_5_days=without(5), without_best_20_days=without(20),
             best_5_days_share=(top.head(5)['s'].sum() / total) if total > 0 else None)
    for y in range(2022, 2027):
        Y = X.filter(pl.col('session').dt.year() == y)
        o[f'avg_pct_{y}'] = Y['r'].mean() if Y.height else None; o[f'trades_{y}'] = Y.height
    return o

S = pl.read_csv(os.path.join(OUT, 'survivors.csv'))
C = S.filter((pl.col('trades_disc') >= 1000) & (pl.col('trades_check') >= 1000) & (pl.col('avg_pct_disc') >= 0.05) & (pl.col('avg_pct_check') >= 0.05))
rows, cache = [], {}
for c in C.iter_rows(named=True):
    if c['product'] not in cache: cache[c['product']] = trades(c['product'])
    T = cache[c['product']]
    for side, right in (('rule', c['right']), ('mirror', 'PUT' if c['right'] == 'CALL' else 'CALL')):
        f = (pl.col('tag') == c['tag']) & (pl.col('right') == right) & (pl.col(c['cut']) == (c['distance'] if c['cut'] == 'distance' else c['price']))
        X = result(T.filter(f), c['exit'])
        o = dict(rule=c['id'], side=side, product=c['product'], tag=c['tag'], right=right, cut=c['cut'], band=c['distance'] if c['cut'] == 'distance' else c['price'], exit=c['exit'])
        o.update(stress(X)); rows.append(o)
R = pl.DataFrame(rows, infer_schema_length=None)
R = R.with_columns([pl.col(c).round(6) for c, t in R.schema.items() if t == pl.Float64]).with_columns(
    pl.concat_str([pl.col('rule'), pl.col('side')], separator=' | ').alias('id'))
R.write_csv(os.path.join(OUT, 'stress.csv'))
pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(280); pl.Config.set_tbl_rows(40)
print(R.select('product', 'tag', 'right', 'band', 'exit', 'side', 'trades', 'days', 'days_up', 'win_rate', 'avg_pct', 'ci_low', 'ci_high',
               'without_best_5_days', 'without_best_20_days', 'best_5_days_share', 'avg_pct_2022', 'avg_pct_2023', 'avg_pct_2024', 'avg_pct_2025', 'avg_pct_2026'))
