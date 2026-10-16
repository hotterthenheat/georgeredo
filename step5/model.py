"""Step 5b: can what was visible at the moment of buying tell the runners from the duds?

Trades: step 4's turn-up and range-break buys (1,602,401), with step5/features.py's entry-minute features.

Every choice below was fixed before the 2025-2026 trades were scored, and they were scored once:
- What a model sees: only what features.py records at the entry minute (below, `FEATURES`), never anything after it.
- Model A (runners): the chance that the contract's bid reaches 3 times the price paid (+200%) before the close.
- Model B (money): the result of the trade sold with a 50% trailing stop (step 4's trail50, its best exit on the turn-up
  trades in 2022-2024), net of fees, as a share of the price paid, capped at +400% so a handful of 50x days do not
  decide the fit.
- Both are gradient-boosted trees (LightGBM) with the settings in `PARAMS`, trained on 2022-01 to 2024-06 and stopped
  early on 2024-07 to 2024-12. 2025-01 onward is never seen until the scoring.
- The score cut points (top 50%, 20%, 10%, 5%, 1%) are the scores' percentiles on 2024-07 to 2024-12, so a trader
  could have set them before 2025. Each 2025-2026 trade is then put in its bucket.
For each bucket, every way out is shown (hold, trailing stops), with fees as in step 4: $0.65 a contract each way, none
when a contract expires worthless, and split by product and by what one contract cost. The top 10%, 5% and 1% of both
models on 2025-2026 are stress-tested as in step 4 (by year, a day-resampled 95% range, without the best 5 and 20 days).
(The first run stopped in the last table, after the models were fitted and scored; the price split and model A's stress
rows were added to the reports and the script run again. The fit is deterministic: the rerun's models, scores and every
figure the first run wrote are identical.)

Writes step5/out/: headline.csv, buckets.csv, stress.csv, importance.csv, feature_deciles.csv, scores.parquet
  python3 -I step5/model.py
"""
import os, random
import numpy as np
import polars as pl
import lightgbm as lgb

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
FEE = 0.65
TRAIN_END, VALID_END = pl.date(2024, 7, 1), pl.date(2025, 1, 1)
EXITS = ['hold', 'trail20', 'trail30', 'trail40', 'trail50']
TOPS = [('All', 0.0), ('Top 50%', 0.5), ('Top 20%', 0.8), ('Top 10%', 0.9), ('Top 5%', 0.95), ('Top 1%', 0.99)]
PARAMS = dict(num_leaves=63, learning_rate=0.03, min_data_in_leaf=1000, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
              lambda_l2=10.0, seed=20261016, deterministic=True, force_row_wise=True, num_threads=4, verbose=-1)
ROUNDS, PATIENCE = 3000, 100
PRODUCTS = {'SPY': 0, 'QQQ': 1, 'IWM': 2, 'SPXW': 3}
TAGS = {'bounce1.5': 0, 'bounce2': 1, 'bounce3': 2, 'bounce5': 3, 'orb': 4}
PRICE_BANDS = {'Under $5': (0, 5), '$5–10': (5, 10), '$10–25': (10, 25), '$25–50': (25, 50), '$50–100': (50, 100), 'Over $100': (100, 1e12)}

def load():
    F = []
    for root in PRODUCTS:
        x = pl.read_parquet(os.path.join(OUT, f'features_{root}.parquet')).with_columns(pl.lit(root).alias('root'))
        F.append(x)
    T = pl.concat(F, how='vertical_relaxed')
    dirn = pl.when(pl.col('right') == 'CALL').then(1.0).otherwise(-1.0)
    rng = pl.col('hi_so_far') - pl.col('lo_so_far')
    T = T.with_columns(dirn.alias('dir'), (pl.col('close_minute') - pl.col('entry_minute')).alias('to_close'))
    T = T.with_columns(
        # what was visible at the entry minute
        pl.col('root').replace_strict(PRODUCTS).alias('product'), pl.col('tag').replace_strict(TAGS).alias('kind'),
        (pl.col('right') == 'CALL').cast(pl.Int8).alias('is_call'), pl.col('half_day').cast(pl.Int8),
        pl.col('session').dt.weekday().alias('weekday'),
        (pl.col('dir') * (pl.col('strike') - pl.col('px')) / pl.col('px') * 100).alias('otm'),
        pl.col('entry_ask').alias('price'), ((pl.col('entry_ask') - pl.col('entry_bid')) / pl.col('entry_ask')).alias('spread'),
        ((pl.col('bid_size') - pl.col('ask_size')) / (pl.col('bid_size') + pl.col('ask_size'))).alias('size_imb'),
        (pl.col('entry_ask') / pl.col('low_before')).alias('turn'), (pl.col('entry_minute') - pl.col('low_minute')).alias('low_age'),
        (pl.col('hi_before') / pl.col('low_before')).alias('fall'), (pl.col('open_ask') / pl.col('low_before')).alias('open_vs_low'),
        (pl.col('entry_ask') / pl.col('open_ask')).alias('ask_vs_open'),
        *[(pl.col('entry_ask') / pl.col(f'ask_{L}')).alias(f'mom{L}') for L in (1, 5, 15)],
        *[(pl.col('dir') * (pl.col('px') / pl.col(f'px_{L}') - 1) * 100).alias(f'dret{L}') for L in (1, 5, 15, 30)],
        (pl.col('dir') * (pl.col('px') / pl.col('spot_open') - 1) * 100).alias('dmove'),
        (pl.col('dir') * pl.col('gap') * 100).alias('dgap'),
        pl.when(pl.col('dir') > 0).then((pl.col('px') - pl.col('lo_so_far')) / rng).otherwise((pl.col('hi_so_far') - pl.col('px')) / rng).alias('pos'),
        pl.when(pl.col('dir') > 0).then(pl.col('hi_so_far') > pl.col('hi_5')).otherwise(pl.col('lo_so_far') < pl.col('lo_5')).cast(pl.Int8).alias('new_ext5'),
        pl.when(pl.col('dir') > 0).then(pl.col('lo_so_far') < pl.col('lo_5')).otherwise(pl.col('hi_so_far') > pl.col('hi_5')).cast(pl.Int8).alias('new_against5'),
        (rng / pl.col('spot_open') * 100).alias('range_pct'), (pl.col('prior_range') * 100).alias('prior_range_pct'),
        (pl.col('rv15') * 100).alias('rv15_pct'),
        (pl.col('vix') / pl.col('vix_open') - 1).alias('vix_chg'), (pl.col('vix') / pl.col('vix_15') - 1).alias('vix_chg15'),
        (pl.col('straddle') / pl.col('px') * 100).alias('implied_rest'),
        (pl.col('straddle_open') / pl.col('spot_open') * 100).alias('implied_open'))
    T = T.with_columns(
        (pl.col('implied_rest') / pl.col('to_close').sqrt()).alias('iv_now'),
        (pl.col('otm') / pl.col('implied_rest')).alias('otm_im'),
        (pl.col('range_pct') / pl.col('implied_open')).alias('range_im'))
    T = T.with_columns((pl.col('iv_now') / (pl.col('implied_open') / (pl.col('close_minute') - 1).sqrt())).alias('iv_ratio'))
    # what happened after, for scoring only
    settle = pl.when(pl.col('right') == 'CALL').then((pl.col('spot_close') - pl.col('strike')).clip(0)).otherwise((pl.col('strike') - pl.col('spot_close')).clip(0))
    band = pl.lit(None, pl.Utf8)
    for lab, (lo, hi) in PRICE_BANDS.items(): band = pl.when((pl.col('entry_ask') * 100 > lo) & (pl.col('entry_ask') * 100 <= hi)).then(pl.lit(lab)).otherwise(band)
    T = T.with_columns(settle.alias('settle'), (pl.col('entry_ask') * 100).alias('cost'), band.alias('price_band'),
                       (pl.col('max_bid') >= 3 * pl.col('entry_ask') - 1e-9).fill_null(False).cast(pl.Int8).alias('reach3'))
    cols = []
    for x in EXITS:
        if x == 'hold':
            price, sold = pl.col('settle'), pl.col('settle') > 0
        else:
            hit = pl.col(x + '_minute').is_not_null()
            price = pl.when(hit).then(pl.col(x + '_bid')).otherwise(pl.col('settle')); sold = hit | (pl.col('settle') > 0)
        net = (price - pl.col('entry_ask')) * 100 - FEE - pl.when(sold).then(FEE).otherwise(0.0)
        cols += [net.alias('net_' + x), (net / pl.col('cost')).alias('r_' + x)]
    T = T.with_columns(cols)
    return T.with_columns(pl.when(pl.col('session') < TRAIN_END).then(pl.lit('train')).when(pl.col('session') < VALID_END).then(pl.lit('valid'))
                          .otherwise(pl.lit('check')).alias('part'))

FEATURES = ['product', 'kind', 'is_call', 'half_day', 'weekday', 'entry_minute', 'to_close', 'otm', 'otm_im', 'price', 'spread', 'bid_size',
            'ask_size', 'size_imb', 'turn', 'low_age', 'fall', 'open_vs_low', 'ask_vs_open', 'mom1', 'mom5', 'mom15', 'dret1', 'dret5', 'dret15',
            'dret30', 'dmove', 'dgap', 'pos', 'new_ext5', 'new_against5', 'range_pct', 'prior_range_pct', 'rv15_pct', 'vix', 'vix_chg', 'vix_chg15',
            'implied_rest', 'implied_open', 'iv_now', 'iv_ratio', 'range_im']
CATEGORICAL = ['product', 'kind', 'weekday']

def matrix(T):
    X = T.select([pl.col(c).cast(pl.Float64).fill_nan(None) for c in FEATURES]).to_numpy().astype(np.float32)
    X[~np.isfinite(X)] = np.nan
    return X

def fit(T, target, objective):
    tr, va = T.filter(pl.col('part') == 'train'), T.filter(pl.col('part') == 'valid')
    dtr = lgb.Dataset(matrix(tr), label=tr[target].to_numpy(), feature_name=FEATURES, categorical_feature=CATEGORICAL, free_raw_data=False)
    dva = lgb.Dataset(matrix(va), label=va[target].to_numpy(), reference=dtr)
    p = dict(PARAMS, objective=objective, metric='auc' if objective == 'binary' else 'l2')
    return lgb.train(p, dtr, ROUNDS, valid_sets=[dva], callbacks=[lgb.early_stopping(PATIENCE, verbose=False)])

def auc(y, s):
    o = np.argsort(s, kind='mergesort'); r = np.empty(len(s)); r[o] = np.arange(1, len(s) + 1)
    # ties share their average rank
    _, inv, cnt = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=r); r = (sums / cnt)[inv]
    pos = y == 1; n1, n0 = pos.sum(), (~pos).sum()
    return (r[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)

def bucket_rows(X, label):
    a = [pl.len().alias('trades'), pl.col('session').n_unique().alias('days'), pl.col('reach3').mean().alias('reached_3x'),
         pl.col('r_perfect').mean().alias('avg_pct_exact_top')]
    for x in EXITS:
        a += [(pl.col('net_' + x) > 0).mean().alias(f'win_rate_{x}'), pl.col('r_' + x).mean().alias(f'avg_pct_{x}'),
              pl.col('r_' + x).filter(pl.col('net_' + x) > 0).mean().alias(f'avg_win_pct_{x}'),
              pl.col('r_' + x).filter(pl.col('net_' + x) <= 0).mean().alias(f'avg_loss_pct_{x}')]
    return X.select(a).with_columns(pl.lit(label).alias('bucket'))

def stress(X, x):
    r, net = 'r_' + x, 'net_' + x
    day = X.group_by('session').agg(pl.col(r).sum().alias('s'), pl.len().alias('n')).sort('session')
    random.seed(20261016); s = day['s'].to_list(); n = day['n'].to_list(); bs = []
    for _ in range(2000):
        idx = [random.randrange(len(s)) for _ in s]
        bs.append(sum(s[i] for i in idx) / sum(n[i] for i in idx))
    bs.sort()
    top = day.sort('s', descending=True)
    def without(k):
        t = top.head(k); return (X[r].sum() - t['s'].sum()) / (X.height - t['n'].sum()) if X.height > t['n'].sum() else None
    total = X[r].sum()
    o = dict(trades=X.height, days=day.height, days_up=int((day['s'] > 0).sum()), win_rate=(X[net] > 0).mean(), avg_pct=X[r].mean(),
             ci_low=bs[50], ci_high=bs[1949], without_best_5_days=without(5), without_best_20_days=without(20),
             best_5_days_share=(top.head(5)['s'].sum() / total) if total > 0 else None)
    for y in (2025, 2026):
        Y = X.filter(pl.col('session').dt.year() == y)
        o[f'avg_pct_{y}'] = Y[r].mean() if Y.height else None; o[f'trades_{y}'] = Y.height
    return o

if __name__ == '__main__':
    T = load()
    T = T.with_columns(pl.max_horizontal(pl.col('max_bid').fill_null(0.0), pl.col('settle')).alias('_pp'))
    T = T.with_columns((((pl.col('_pp') - pl.col('entry_ask')) * 100 - FEE - pl.when(pl.col('_pp') > 0).then(FEE).otherwise(0.0)) / pl.col('cost')).alias('r_perfect')).drop('_pp')
    T = T.with_columns(pl.col('r_trail50').clip(-1.0, 4.0).alias('y_b'))
    print(T.group_by('part').agg(pl.len(), pl.col('session').min().alias('first'), pl.col('session').max().alias('last'), pl.col('reach3').mean()).sort('part'), flush=True)
    A = fit(T, 'reach3', 'binary'); B = fit(T, 'y_b', 'regression')
    X = matrix(T)
    T = T.with_columns(pl.Series('score_a', A.predict(X, num_iteration=A.best_iteration)), pl.Series('score_b', B.predict(X, num_iteration=B.best_iteration)))
    del X
    heads, rows, srows = [], [], []
    for name, s in (('A: reaches 3x', 'score_a'), ('B: trail50 result', 'score_b')):
        mdl = A if s == 'score_a' else B
        for part in ('train', 'valid', 'check'):
            P = T.filter(pl.col('part') == part)
            heads.append(dict(model=name, part=part, trades=P.height, rounds=mdl.best_iteration,
                              auc_reach3=auc(P['reach3'].to_numpy(), P[s].to_numpy()),
                              corr_trail50=float(np.corrcoef(P[s].to_numpy(), P['r_trail50'].to_numpy())[0, 1])))
        cuts = {lab: (T.filter(pl.col('part') == 'valid')[s].quantile(q, 'linear') if q > 0 else -np.inf) for lab, q in TOPS}
        for part in ('valid', 'check'):
            P = T.filter(pl.col('part') == part)
            for lab, _ in TOPS:
                top = P.filter(pl.col(s) >= cuts[lab])
                for cut, val in [('All', 'All')] + [('product', p) for p in PRODUCTS] + [('price', b) for b in PRICE_BANDS]:
                    Q = top if cut == 'All' else top.filter(pl.col('root' if cut == 'product' else 'price_band') == val)
                    if Q.height == 0: continue
                    rows.append(bucket_rows(Q, lab).with_columns(pl.lit(name).alias('model'), pl.lit(part).alias('part'), pl.lit(val if cut != 'price' else 'All').alias('product'),
                                                                 pl.lit(val if cut == 'price' else 'All').alias('price'), pl.lit(float(cuts[lab])).alias('cut')))
        # the top buckets of both models on 2025-2026, stress-tested with every way out
        C = T.filter(pl.col('part') == 'check')
        for lab, _ in TOPS[3:]:
            for x in EXITS:
                o = dict(model=name, bucket=lab, exit=x); o.update(stress(C.filter(pl.col(s) >= cuts[lab]), x)); srows.append(o)
    r6 = lambda d: d.with_columns([pl.col(c).round(6) for c, t in d.schema.items() if t == pl.Float64])
    H = pl.DataFrame(heads); r6(H).write_csv(os.path.join(OUT, 'headline.csv'))
    Bk = pl.concat(rows, how='diagonal_relaxed').with_columns(pl.concat_str(['model', 'part', 'bucket', 'product', 'price'], separator=' | ').alias('id'))
    first = ['id', 'model', 'part', 'bucket', 'product', 'price', 'cut']
    r6(Bk.select(first + [c for c in Bk.columns if c not in first])).write_csv(os.path.join(OUT, 'buckets.csv'))
    S = pl.DataFrame(srows, infer_schema_length=None).with_columns(pl.concat_str(['model', 'bucket', 'exit'], separator=' | ').alias('id'))
    r6(S).write_csv(os.path.join(OUT, 'stress.csv'))
    imp = pl.DataFrame({'feature': FEATURES, 'gain_a': A.feature_importance('gain'), 'gain_b': B.feature_importance('gain')})
    imp = imp.with_columns((pl.col('gain_a') / pl.col('gain_a').sum()).alias('share_a'), (pl.col('gain_b') / pl.col('gain_b').sum()).alias('share_b')).sort('share_a', descending=True)
    r6(imp.with_columns(pl.col('feature').alias('id'))).write_csv(os.path.join(OUT, 'importance.csv'))
    # the strongest features one at a time: deciles cut on 2022-2024, read in each period
    D = []
    top = set(imp.head(8)['feature'].to_list()) | set(imp.sort('share_b', descending=True).head(8)['feature'].to_list())
    for f in sorted(top - set(CATEGORICAL)):
        disc = T.filter(pl.col('part') != 'check')[f].drop_nulls().drop_nans()
        qs = sorted(set(disc.quantile(q / 10, 'linear') for q in range(1, 10)))
        b = pl.lit(0)
        for i, q in enumerate(qs): b = pl.when(pl.col(f) > q).then(pl.lit(i + 1)).otherwise(b)
        Z = T.filter(pl.col(f).is_not_null() & pl.col(f).is_not_nan()).with_columns(b.alias('decile'), pl.when(pl.col('part') == 'check').then(pl.lit('check')).otherwise(pl.lit('disc')).alias('period'))
        g = Z.group_by('decile', 'period').agg(pl.len().alias('trades'), pl.col(f).min().cast(pl.Float64).alias('lo'), pl.col(f).max().cast(pl.Float64).alias('hi'), pl.col('reach3').mean().alias('reached_3x'),
                                              pl.col('r_trail50').mean().alias('avg_pct_trail50'), pl.col('r_hold').mean().alias('avg_pct_hold'))
        D.append(g.with_columns(pl.lit(f).alias('feature')))
    D = pl.concat(D).sort('feature', 'period', 'decile').with_columns(pl.concat_str([pl.col('feature'), pl.col('period'), pl.col('decile').cast(pl.Utf8)], separator=' | ').alias('id'))
    r6(D).write_csv(os.path.join(OUT, 'feature_deciles.csv'))
    T.select('session', 'root', 'tag', 'strike', 'right', 'entry_minute', 'part', 'score_a', 'score_b').write_parquet(os.path.join(OUT, 'scores.parquet'), compression='zstd', compression_level=19)
    pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_rows(60)
    print(H)
    print(Bk.filter((pl.col('product') == 'All') & (pl.col('price') == 'All')).select('model', 'part', 'bucket', 'trades', 'reached_3x', 'avg_pct_hold', 'avg_pct_trail30', 'avg_pct_trail50', 'win_rate_trail50', 'avg_pct_exact_top'))
    print(S.select('model', 'bucket', 'exit', 'trades', 'days', 'days_up', 'avg_pct', 'ci_low', 'ci_high', 'without_best_5_days', 'avg_pct_2025', 'avg_pct_2026'))
    print(imp.head(15))
