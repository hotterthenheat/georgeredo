"""Step 5d: for the trades the runner model (model A) ranks highest, which way out keeps the most of their runs?

The picks: model A's top 10%, 5% and 1%. On 2025-2026 they are model.py's buckets (the main model, its cut points from
2024-07 to 2024-12). On 2022-2024 a model's own training trades cannot be used (it has seen how they ended), so those
trades are scored out of fold: the period is cut into three blocks of sessions, and each block is scored by model A's
settings fitted on the other two (120 rounds, model A's early-stopped count), the cut points being that score's own
percentiles. Every pick is followed from the minute after buying to the close in the raw quotes, as in step 3:
- a target: sell the first minute the bid reaches +25%, +50%, +100%, +150%, +200%, +300%, +500% or +1,000%, at exactly
  that price; or none;
- a stop: sell at the bid the first minute it falls to -30%, -50% or -70%; or none;
- a time exit: the close (hold), 30 minutes before the close, or 30, 60 or 120 minutes after buying, at the last bid by
  then;
whichever comes first: 9 x 4 x 5 = 180 ways out, and step 4's four trailing stops. Fees as before.

The way out for each bucket is picked on 2022-2024 (the best average) and read, unchanged, on 2025-2026, with step 4's
stress test. Every way out's result in both periods is written too.

Writes step5/out/exit_paths.parquet, exits_grid.csv, exits_best.csv, exits_stress.csv
  python3 -I step5/exits.py
"""
import itertools, os, sys
import numpy as np
import polars as pl
import lightgbm as lgb

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from step1.breakdown import RAW   # noqa: E402
import step5.model as M           # noqa: E402

OUT = os.path.join(HERE, 'out')
EPS = 1e-9
A_ROUNDS = 120
BUCKETS = [('Top 10%', 0.9), ('Top 5%', 0.95), ('Top 1%', 0.99)]
TARGETS = [('none', None, None), ('+25%', 't125', 1.25), ('+50%', 't150', 1.5), ('+100%', 't200', 2.0), ('+150%', 't250', 2.5), ('+200%', 't300', 3.0),
           ('+300%', 't400', 4.0), ('+500%', 't600', 6.0), ('+1,000%', 't1100', 11.0)]
STOPS = [('none', None, None), ('-30%', 's70', 0.7), ('-50%', 's50', 0.5), ('-70%', 's30', 0.3)]
TIMES = [('close', None, None), ('30 min before close', 'c30', None), ('30 min after buying', 'h30', 30), ('60 min after buying', 'h60', 60),
         ('120 min after buying', 'h120', 120)]
KEY = ['session', 'root', 'tag', 'strike', 'right', 'entry_minute']

def minute_of(col):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

def paths(root, d, E):
    close_m = int(E['close_minute'][0])
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    c = c.with_columns(minute_of('timestamp').alias('m'))
    two = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0)
    q = c.filter((pl.col('m') >= 1) & (pl.col('m') <= close_m) & two).select('strike', 'right', 'm', 'bid')
    k = ['strike', 'right', 'entry_minute']
    e = E.select(k + ['entry_ask']).unique()
    j = e.join(q, on=['strike', 'right']).filter(pl.col('m') > pl.col('entry_minute')).sort(k + ['m'])
    aggs = [pl.len().alias('quotes_after_p'), pl.col('bid').max().alias('max_bid_p')]
    aggs += [pl.col('m').filter(pl.col('bid') >= x * pl.col('entry_ask') - EPS).first().alias(n) for _, n, x in TARGETS if n]
    for _, n, x in STOPS:
        if not n: continue
        down = pl.col('bid') <= x * pl.col('entry_ask') + EPS
        aggs += [pl.col('m').filter(down).first().alias(n), pl.col('bid').filter(down).first().alias(n + '_bid')]
    aggs.append(pl.col('bid').filter(pl.col('m') <= close_m - 30).last().alias('c30_bid'))
    aggs += [pl.col('bid').filter(pl.col('m') <= pl.col('entry_minute') + h).last().alias(f'h{h}_bid') for h in (30, 60, 120)]
    a = j.group_by(k, maintain_order=True).agg(aggs)
    r = E.join(a, on=k, how='left').with_columns(pl.col('quotes_after_p').fill_null(0))
    return r.with_columns(pl.when(pl.col('entry_minute') < close_m - 30).then(pl.col('c30_bid')).otherwise(None).alias('c30_bid'),
                          *[pl.when(pl.col('entry_minute') + h <= close_m).then(pl.col(f'h{h}_bid')).otherwise(None).alias(f'h{h}_bid') for h in (30, 60, 120)])

def exit_price(tcol, tk, scol, xcol, xh):
    tmin = pl.col(tcol) if tcol else pl.lit(None, pl.Int32)
    smin = pl.col(scol) if scol else pl.lit(None, pl.Int32)
    first = pl.min_horizontal(tmin, smin)    # a target is above the price paid and a stop below: never the same minute
    if xcol == 'c30':
        xm = pl.when(pl.col('entry_minute') < pl.col('close_minute') - 30).then(pl.col('close_minute') - 30)
    elif xcol:
        xm = pl.when(pl.col('entry_minute') + xh <= pl.col('close_minute')).then(pl.col('entry_minute') + xh)
    else:
        xm = pl.lit(None, pl.Int32)
    xbid = pl.col(xcol + '_bid') if xcol else pl.lit(None, pl.Float64)
    by_first = first.is_not_null() & (xm.is_null() | (first <= xm))
    tgt = (tmin.is_not_null() & (tmin == first)) if tcol else pl.lit(False)
    price = (pl.when(by_first & tgt).then(pl.col('entry_ask') * (tk or 0))
             .when(by_first).then(pl.col(scol + '_bid') if scol else pl.lit(None, pl.Float64))
             .when(xm.is_not_null() & xbid.is_not_null()).then(xbid)
             .otherwise(pl.col('settle')))
    sold = by_first | (xm.is_not_null() & xbid.is_not_null()) | (pl.col('settle') > 0)
    return price, sold

def rules():
    out = [(f'{tn} · {sn} · {xn}', exit_price(tc, tk, sc, xc, xh)) for (tn, tc, tk), (sn, sc, _), (xn, xc, xh) in itertools.product(TARGETS, STOPS, TIMES)]
    for x in ('trail20', 'trail30', 'trail40', 'trail50'):
        hit = pl.col(x + '_minute').is_not_null()
        out.append((f'{x[5:]}% trailing stop', (pl.when(hit).then(pl.col(x + '_bid')).otherwise(pl.col('settle')), hit | (pl.col('settle') > 0))))
    return out

if __name__ == '__main__':
    T = M.load()
    T = T.with_columns(pl.max_horizontal(pl.col('max_bid').fill_null(0.0), pl.col('settle')).alias('_pp'))
    T = T.with_columns((((pl.col('_pp') - pl.col('entry_ask')) * 100 - M.FEE - pl.when(pl.col('_pp') > 0).then(M.FEE).otherwise(0.0)) / pl.col('cost')).alias('r_perfect')).drop('_pp')
    S = pl.read_parquet(os.path.join(OUT, 'scores.parquet'))
    T = T.join(S.select(KEY + ['score_a']), on=KEY, how='left')
    # out-of-fold scores for 2022-2024: three blocks of sessions
    disc = T.filter(pl.col('part') != 'check')
    days = sorted(disc['session'].unique().to_list()); edges = [days[0], days[len(days) // 3], days[2 * len(days) // 3]]
    disc = disc.with_columns(pl.when(pl.col('session') >= edges[2]).then(2).when(pl.col('session') >= edges[1]).then(1).otherwise(0).alias('block'))
    oof = []
    for b in range(3):
        tr, te = disc.filter(pl.col('block') != b), disc.filter(pl.col('block') == b)
        dtr = lgb.Dataset(M.matrix(tr), label=tr['reach3'].to_numpy(), feature_name=M.FEATURES, categorical_feature=M.CATEGORICAL)
        mdl = lgb.train(dict(M.PARAMS, objective='binary'), dtr, A_ROUNDS)
        oof.append(te.select(KEY).with_columns(pl.Series('score', mdl.predict(M.matrix(te)))))
        print('block', b, te['session'].min(), te['session'].max(), 'auc', round(M.auc(te['reach3'].to_numpy(), oof[-1]['score'].to_numpy()), 4), flush=True)
    oof = pl.concat(oof)
    disc = disc.join(oof, on=KEY)
    chk = T.filter(pl.col('part') == 'check').with_columns(pl.col('score_a').alias('score'))
    vcut = {lab: T.filter(pl.col('part') == 'valid')['score_a'].quantile(q, 'linear') for lab, q in BUCKETS}
    dcut = {lab: disc['score'].quantile(q, 'linear') for lab, q in BUCKETS}
    P = pl.concat([disc.filter(pl.col('score') >= dcut['Top 10%']).with_columns(pl.lit('disc').alias('period')).drop('block'),
                   chk.filter(pl.col('score') >= vcut['Top 10%']).with_columns(pl.lit('check').alias('period'))], how='diagonal_relaxed')
    P = P.with_columns(*[pl.when(pl.col('period') == 'disc').then(pl.col('score') >= dcut[lab]).otherwise(pl.col('score') >= vcut[lab]).alias(lab) for lab, _ in BUCKETS])
    print('picks', P.group_by('period').len().rows(), flush=True)
    # follow every pick in the raw quotes
    import multiprocessing as mp
    jobs = [(root, d, x.select('strike', 'right', 'entry_minute', 'entry_ask', 'close_minute').unique()) for (root, d), x in P.group_by('root', 'session')]
    with mp.get_context('spawn').Pool(4) as pool:
        out = pool.starmap(paths, jobs, chunksize=8)
    W = pl.concat([o.with_columns(pl.lit(r).alias('root'), pl.lit(d).alias('session')) for (r, d, _), o in zip(jobs, out)], how='vertical_relaxed')
    P = P.join(W.drop('entry_ask', 'close_minute'), on=['root', 'session', 'strike', 'right', 'entry_minute'], how='left')
    # the paths and step 4 must agree on what came after each buy
    bad = P.filter(((pl.col('max_bid_p') - pl.col('max_bid')).abs() > EPS).fill_null(False) | (pl.col('max_bid_p').is_null() != pl.col('max_bid').is_null())
                   | (pl.col('quotes_after_p') != pl.col('quotes_after')))
    if bad.height: raise SystemExit(f'{bad.height} picks whose path differs from step 4')
    P.select(KEY + ['period', 'score'] + [b for b, _ in BUCKETS] + [c for c in W.columns if c not in ('root', 'session', 'strike', 'right', 'entry_minute', 'entry_ask', 'close_minute')]) \
     .write_parquet(os.path.join(OUT, 'exit_paths.parquet'), compression='zstd', compression_level=19)
    # every way out, every bucket, both periods
    rows = []
    for name, (price, sold) in rules():
        net = (price - pl.col('entry_ask')) * 100 - M.FEE - pl.when(sold).then(M.FEE).otherwise(0.0)
        X = P.with_columns(net.alias('net')).with_columns((pl.col('net') / pl.col('cost')).alias('r'))
        for lab, _ in BUCKETS:
            g = X.filter(pl.col(lab)).group_by('period').agg(pl.len().alias('trades'), (pl.col('net') > 0).mean().alias('win_rate'), pl.col('r').mean().alias('avg_pct'),
                                                            pl.col('r').filter(pl.col('net') > 0).mean().alias('avg_win_pct'), pl.col('r').filter(pl.col('net') <= 0).mean().alias('avg_loss_pct'))
            rows.append(g.with_columns(pl.lit(lab).alias('bucket'), pl.lit(name).alias('exit')))
    G = pl.concat(rows).pivot(on='period', index=['bucket', 'exit'], values=['trades', 'win_rate', 'avg_pct', 'avg_win_pct', 'avg_loss_pct'])
    G = G.with_columns(pl.concat_str(['bucket', 'exit'], separator=' | ').alias('id'))
    r6 = lambda d: d.with_columns([pl.col(c).round(6) for c, t in d.schema.items() if t == pl.Float64])
    r6(G.sort('bucket', 'avg_pct_disc', descending=[False, True])).write_csv(os.path.join(OUT, 'exits_grid.csv'))
    best, srows = [], []
    for lab, _ in BUCKETS:
        Gb = G.filter(pl.col('bucket') == lab)
        b = Gb.sort('avg_pct_disc', descending=True).row(0, named=True)
        hold = Gb.filter(pl.col('exit') == 'none · none · close').row(0, named=True)
        best.append(dict(bucket=lab, exit=b['exit'], trades_disc=b['trades_disc'], avg_pct_disc=b['avg_pct_disc'], trades_check=b['trades_check'],
                         avg_pct_check=b['avg_pct_check'], win_rate_check=b['win_rate_check'], avg_win_pct_check=b['avg_win_pct_check'],
                         avg_loss_pct_check=b['avg_loss_pct_check'], hold_avg_pct_check=hold['avg_pct_check'],
                         exits_positive_disc=int((Gb['avg_pct_disc'] > 0).sum()), exits_positive_both=int(((Gb['avg_pct_disc'] > 0) & (Gb['avg_pct_check'] > 0)).sum()),
                         exits=Gb.height, best_check_exit=Gb.sort('avg_pct_check', descending=True)['exit'][0], best_check_avg_pct=Gb['avg_pct_check'].max()))
        price, sold = dict(rules())[b['exit']]
        net = (price - pl.col('entry_ask')) * 100 - M.FEE - pl.when(sold).then(M.FEE).otherwise(0.0)
        C = P.filter(pl.col(lab) & (pl.col('period') == 'check')).with_columns(net.alias('net_x')).with_columns((pl.col('net_x') / pl.col('cost')).alias('r_x'))
        o = dict(bucket=lab, exit=b['exit']); o.update(M.stress(C, 'x')); srows.append(o)
    Bt = pl.DataFrame(best).with_columns(pl.col('bucket').alias('id')); r6(Bt).write_csv(os.path.join(OUT, 'exits_best.csv'))
    St = pl.DataFrame(srows, infer_schema_length=None).with_columns(pl.col('bucket').alias('id')); r6(St).write_csv(os.path.join(OUT, 'exits_stress.csv'))
    pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_rows(40)
    print(Bt); print(St)
    for lab, _ in BUCKETS:
        print(G.filter(pl.col('bucket') == lab).sort('avg_pct_disc', descending=True).head(8).select('exit', 'trades_disc', 'avg_pct_disc', 'trades_check', 'avg_pct_check', 'win_rate_check'))
