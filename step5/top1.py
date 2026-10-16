"""Step 5e: trade only the top 1% (and stricter). Every trade model A ranks in its top 1%, the first such trade each day
(one a day), and the top 0.5% and 0.1%, each with three ways out, broken down trade by trade.

The cut points come from before the period they are used in, as in model.py and exits.py:
- 2025-2026: the main model A (fitted on 2022-01 to 2024-06), cut at its scores' percentiles on 2024-07 to 2024-12.
- 2022-2024: scored out of fold (exits.py: each block of sessions by a model fitted on the other two), cut at that
  score's own percentiles.
"First each day" takes the earliest minute a pick appears (the higher score if two appear in the same minute), so it
needs nothing from later in the day.

Ways out: the 50% trailing stop (step 4), hold to 30 minutes before the close (the way out exits.py picked for the top 1%
on 2022-2024), and hold to the close. Fees as before. One contract a trade; $ figures are per contract.

Writes step5/out/top1_summary.csv, top1_by_product.csv, top1_by_month.csv, top1_daily.csv
  python3 -I step5/top1.py
"""
import os, random, sys
import numpy as np
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import step5.model as M                       # noqa: E402
from step5.exits import exit_price, KEY       # noqa: E402

OUT = os.path.join(HERE, 'out')
TOPS = [('Top 1%', 0.99), ('Top 0.5%', 0.995), ('Top 0.1%', 0.999)]
EXITS = [('50% trailing stop', None), ('Hold to 30 min before close', 'c30'), ('Hold to the close', 'close')]

def with_exit(X, name):
    if name == '50% trailing stop':
        hit = pl.col('trail50_minute').is_not_null()
        price, sold = pl.when(hit).then(pl.col('trail50_bid')).otherwise(pl.col('settle')), hit | (pl.col('settle') > 0)
    elif name == 'Hold to 30 min before close':
        price, sold = exit_price(None, None, None, 'c30', None)
    else:
        price, sold = pl.col('settle'), pl.col('settle') > 0
    net = (price - pl.col('entry_ask')) * 100 - M.FEE - pl.when(sold).then(M.FEE).otherwise(0.0)
    return X.with_columns(net.alias('net'), (net / pl.col('cost')).alias('r'))

def summary(X):
    day = X.group_by('session').agg(pl.col('r').sum().alias('s'), pl.len().alias('n'), pl.col('net').sum().alias('usd')).sort('session')
    random.seed(20261016); s, n = day['s'].to_list(), day['n'].to_list(); bs = []
    for _ in range(2000):
        idx = [random.randrange(len(s)) for _ in s]
        bs.append(sum(s[i] for i in idx) / sum(n[i] for i in idx))
    bs.sort()
    top = day.sort('s', descending=True).head(5)
    wins, losses = X.filter(pl.col('net') > 0), X.filter(pl.col('net') <= 0)
    o = dict(trades=X.height, days=day.height, trades_per_day=X.height / day.height, win_rate=wins.height / X.height,
             avg_pct=X['r'].mean(), median_pct=X['r'].median(), avg_win_pct=wins['r'].mean(), avg_loss_pct=losses['r'].mean(),
             best_pct=X['r'].max(), worst_pct=X['r'].min(), avg_usd=X['net'].mean(), best_usd=X['net'].max(), worst_usd=X['net'].min(),
             total_usd=X['net'].sum(), days_up=int((day['usd'] > 0).sum()), best_day_usd=day['usd'].max(), worst_day_usd=day['usd'].min(),
             ci_low=bs[50], ci_high=bs[1949],
             without_best_5_days=(X['r'].sum() - top['s'].sum()) / (X.height - top['n'].sum()) if X.height > top['n'].sum() else None)
    for y in range(2022, 2027):
        Y = X.filter(pl.col('session').dt.year() == y)
        o[f'avg_pct_{y}'] = Y['r'].mean() if Y.height else None
        o[f'trades_{y}'] = Y.height
    return o

if __name__ == '__main__':
    T = M.load()
    P = pl.read_parquet(os.path.join(OUT, 'exit_paths.parquet'))
    P = P.join(T.select(KEY + ['entry_ask', 'cost', 'settle', 'close_minute', 'reach3', 'trail50_minute', 'trail50_bid']), on=KEY, how='left')
    if P['entry_ask'].null_count(): raise SystemExit('picks without a trade row')
    disc_n = T.filter(pl.col('part') != 'check').height
    vcut = {lab: T.filter(pl.col('part') == 'valid').join(pl.read_parquet(os.path.join(OUT, 'scores.parquet')).select(KEY + ['score_a']), on=KEY)['score_a'].quantile(q, 'linear')
            for lab, q in TOPS}
    # 2022-2024's top 0.5% and 0.1%: the k-th highest out-of-fold score over every 2022-2024 trade (the top 10% were kept,
    # which holds them all); its top 1% is exits.py's
    dsc = P.filter(pl.col('period') == 'disc')['score'].sort(descending=True)
    dcut = {lab: dsc[int(round(disc_n * (1 - q))) - 1] for lab, q in TOPS}
    P = P.with_columns(*[pl.when(pl.col('period') == 'disc').then(pl.col('score') >= dcut[lab]).otherwise(pl.col('score') >= vcut[lab]).alias('_' + lab) for lab, _ in TOPS])
    if (P.filter(pl.col('period') == 'check')['_Top 1%'] != P.filter(pl.col('period') == 'check')['Top 1%']).any():
        raise SystemExit('the 2025-2026 top 1% differs from model.py')
    P = P.with_columns(pl.col('Top 1%').alias('_Top 1%'))   # 2022-2024's top 1% exactly as exits.py cut it
    rows, prod, month, daily = [], [], [], []
    for lab, _ in TOPS:
        S = P.filter(pl.col('_' + lab))
        first = S.sort('session', 'entry_minute', 'score', descending=[False, False, True]).group_by('period', 'session', maintain_order=True).first()
        for how, X0 in (('Every pick', S), ('First pick each day', first)):
            for ex, _ in EXITS:
                X = with_exit(X0, ex)
                for period in ('disc', 'check'):
                    Z = X.filter(pl.col('period') == period)
                    if Z.height == 0: continue
                    o = dict(picks=lab, how=how, exit=ex, period=period); o.update(summary(Z)); rows.append(o)
                    if period == 'check':
                        g = Z.group_by('root').agg(pl.len().alias('trades'), (pl.col('net') > 0).mean().alias('win_rate'), pl.col('r').mean().alias('avg_pct'),
                                                   pl.col('r').max().alias('best_pct'), pl.col('r').min().alias('worst_pct'), pl.col('net').sum().alias('total_usd'))
                        prod.append(g.with_columns(pl.lit(lab).alias('picks'), pl.lit(how).alias('how'), pl.lit(ex).alias('exit')))
                        m = Z.group_by(pl.col('session').dt.strftime('%Y-%m').alias('month')).agg(pl.len().alias('trades'), (pl.col('net') > 0).mean().alias('win_rate'),
                                                                                                pl.col('r').mean().alias('avg_pct'), pl.col('net').sum().alias('total_usd'))
                        month.append(m.with_columns(pl.lit(lab).alias('picks'), pl.lit(how).alias('how'), pl.lit(ex).alias('exit')))
                        d = Z.group_by('session').agg(pl.len().alias('trades'), pl.col('net').sum().alias('usd'), pl.col('r').mean().alias('avg_pct')).sort('session')
                        daily.append(d.with_columns(pl.col('usd').cum_sum().alias('cum_usd'), pl.lit(lab).alias('picks'), pl.lit(how).alias('how'), pl.lit(ex).alias('exit')))
    r6 = lambda d: d.with_columns([pl.col(c).round(6) for c, t in d.schema.items() if t == pl.Float64])
    R = pl.DataFrame(rows, infer_schema_length=None).with_columns(pl.concat_str(['picks', 'how', 'exit', 'period'], separator=' | ').alias('id'))
    r6(R).write_csv(os.path.join(OUT, 'top1_summary.csv'))
    r6(pl.concat(prod).with_columns(pl.concat_str(['picks', 'how', 'exit', 'root'], separator=' | ').alias('id')).sort('id')).write_csv(os.path.join(OUT, 'top1_by_product.csv'))
    r6(pl.concat(month).with_columns(pl.concat_str(['picks', 'how', 'exit', 'month'], separator=' | ').alias('id')).sort('id')).write_csv(os.path.join(OUT, 'top1_by_month.csv'))
    r6(pl.concat(daily).with_columns(pl.concat_str(['picks', 'how', 'exit', pl.col('session').cast(pl.Utf8)], separator=' | ').alias('id'))).write_csv(os.path.join(OUT, 'top1_daily.csv'))
    pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_rows(60)
    print('cuts 2025-2026', vcut, 'cuts 2022-2024', dcut)
    print(R.select('picks', 'how', 'exit', 'period', 'trades', 'days', 'win_rate', 'avg_pct', 'median_pct', 'avg_win_pct', 'avg_loss_pct', 'best_pct', 'worst_pct',
                   'total_usd', 'days_up', 'ci_low', 'ci_high', 'without_best_5_days', 'avg_pct_2025', 'avg_pct_2026'))
