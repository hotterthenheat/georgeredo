"""Step 5c: does the volume traded in each contract, minute by minute, tell the runners from the duds where the quotes
could not?

Volume: ThetaData's one-minute option bars (open, high, low, close, volume, trade count) for every same-day contract with a strike within 2% of the underlying's 9:31 price, $RAW/data/ohlc/<PRODUCT>/<date>.parquet. A bar
stamped at minute j covers j to j+1, so a trade bought at minute m may only use bars stamped m-1 or earlier.

For each turn-up or range-break trade of step5/features.py whose contract has bars that day:
- vol_1, vol_5, vol_15, vol_day: the contract's volume in the last 1, 5, 15 bars and since the open;
- burst5: vol_5 against the contract's own average 5 minutes so far today (vol_day / m x 5);
- trades_5 and size_5: its trade count in the last 5 bars and the average trade's size;
- buy_share5: the share of its last-5-bar volume in bars whose last trade (the bar's close) was above the bar's middle
  quote (the mean of the mids at the bar's start and end): a rough sign of buyers paying up. The bars' own volume-weighted
  price cannot be used: the vendor's vwap field is the session's running average, rounded to the cent, so a minute's own
  average cannot be taken back out of it (checked: re-derived, it fell inside the bar's low-high range on 16% of bars);
- side_share5 and side_share_day: the share of all call and put volume in the 2% band in the last 5 bars (and since the
  open) that was on the contract's own side (calls for a call); side_burst5: its side's last-5-bar volume against its
  side's own average 5 minutes so far; share_of_side5: the contract's part of its side's last-5-bar volume.

The test, fixed before scoring: on the trades that have volume, model.py's two models (same settings, same split: train
2022-01 to 2024-06, early stop on 2024-07 to 2024-12, score 2025-01 onward once) are fitted twice, with model.py's
features alone and with these added. If volume carries what the quotes miss, the second should rank 2025-2026 better and
its top buckets should make more.

Writes step5/out/volume_features_<PRODUCT>.parquet, volume_headline.csv, volume_buckets.csv, volume_stress.csv,
volume_importance.csv
  python3 -I step5/volume.py features     # build the volume features (needs the bars)
  python3 -I step5/volume.py test         # the with/without comparison
"""
import datetime as dt, os, sys
import numpy as np
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from step1.breakdown import RAW   # noqa: E402

OUT = os.path.join(HERE, 'out')
VOL = ['vol_1', 'vol_5', 'vol_15', 'vol_day', 'burst5', 'trades_5', 'size_5', 'buy_share5', 'side_share5', 'side_share_day', 'side_burst5', 'share_of_side5']

def minute_of(col):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

def session(root, d, T):
    """T: this session's trades (strike, right, entry_minute, tag). The volume features of each, or nulls."""
    f = os.path.join(RAW, 'data', 'ohlc', root, f'{d}.parquet')
    if not os.path.exists(f): return None
    close_m = int(T['close_minute'][0])
    b = pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'volume', 'count', 'close']).with_columns(minute_of('timestamp').alias('j')) \
        .filter((pl.col('j') >= 0) & (pl.col('j') < close_m)).drop('timestamp')
    if b.height == 0: return None
    # the middle quote at each bar's start and end, from the same raw quotes as steps 1-4
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask']) \
        .with_columns(minute_of('timestamp').alias('m'))
    two = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0)
    mids = c.filter(two).select('strike', 'right', 'm', ((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
    b = b.join(mids.rename({'m': 'j', 'mid': 'mid0'}), on=['strike', 'right', 'j'], how='left') \
         .join(mids.with_columns((pl.col('m') - 1).alias('j')).drop('m').rename({'mid': 'mid1'}), on=['strike', 'right', 'j'], how='left')
    b = b.with_columns(((pl.col('mid0') + pl.col('mid1')) / 2).alias('mid_bar'))
    b = b.with_columns(pl.when((pl.col('volume') > 0) & pl.col('mid_bar').is_not_null() & (pl.col('close') > pl.col('mid_bar') + 1e-9))
                       .then(pl.col('volume')).otherwise(0).alias('vbuy'),
                       pl.when((pl.col('volume') > 0) & pl.col('mid_bar').is_not_null()).then(pl.col('volume')).otherwise(0).alias('vjudged'))
    # running sums a contract: the value after bar j is known from minute j+1
    k = ['strike', 'right']
    full = b.select(k).unique().join(pl.DataFrame({'j': pl.int_range(0, close_m, eager=True).cast(pl.Int32)}), how='cross')
    b = full.join(b, on=k + ['j'], how='left').with_columns(pl.col('volume', 'count', 'vbuy', 'vjudged').fill_null(0)).sort(k + ['j'])
    b = b.with_columns(*[pl.col(x).cum_sum().over(k).alias('c_' + x) for x in ('volume', 'count', 'vbuy', 'vjudged')])
    # the side's totals a bar
    side = b.group_by('right', 'j').agg(pl.col('volume').sum().alias('sv')).sort('right', 'j').with_columns(pl.col('sv').cum_sum().over('right').alias('c_sv'))
    both = side.group_by('j').agg(pl.col('sv').sum().alias('bv')).sort('j').with_columns(pl.col('bv').cum_sum().alias('c_bv'))

    def at(frame, keys, cols, lag, name):
        """the running sums as of bar m-lag (all bars <= m-lag), joined on the trade"""
        return frame.select(keys + ['j'] + cols).rename({c: f'{c}@{name}' for c in cols}).with_columns((pl.col('j') + lag).alias('m')).drop('j')

    e = T.select('session', 'tag', 'strike', 'right', 'entry_minute').rename({'entry_minute': 'm'})
    has = b.select(k).unique().with_columns(pl.lit(1, pl.Int8).alias('has_vol'))
    e = e.join(has, on=k, how='left').with_columns(pl.col('has_vol').fill_null(0))
    cc = ['c_volume', 'c_count', 'c_vbuy', 'c_vjudged']
    for lag, name in ((1, 'now'), (2, 'l1'), (6, 'l5'), (16, 'l15')):
        e = e.join(at(b, k, cc, lag, name), on=k + ['m'], how='left')
        e = e.join(at(side, ['right'], ['c_sv'], lag, name), on=['right', 'm'], how='left')
        e = e.join(at(both, [], ['c_bv'], lag, name), on=['m'], how='left')
    z = lambda c: pl.col(c).fill_null(0)
    e = e.with_columns(
        z('c_volume@now').alias('vol_day'),
        (z('c_volume@now') - z('c_volume@l1')).alias('vol_1'),
        (z('c_volume@now') - z('c_volume@l5')).alias('vol_5'),
        (z('c_volume@now') - z('c_volume@l15')).alias('vol_15'),
        (z('c_count@now') - z('c_count@l5')).alias('trades_5'),
        ((z('c_vbuy@now') - z('c_vbuy@l5')) / (z('c_vjudged@now') - z('c_vjudged@l5'))).alias('buy_share5'),
        (z('c_sv@now') - z('c_sv@l5')).alias('_sv5'), z('c_sv@now').alias('_svd'),
        (z('c_bv@now') - z('c_bv@l5')).alias('_bv5'), z('c_bv@now').alias('_bvd'))
    e = e.with_columns(
        (pl.col('vol_5') / (pl.col('vol_day') / pl.col('m') * 5)).alias('burst5'),
        (pl.col('vol_5') / pl.col('trades_5')).alias('size_5'),
        (pl.col('_sv5') / pl.col('_bv5')).alias('side_share5'), (pl.col('_svd') / pl.col('_bvd')).alias('side_share_day'),
        (pl.col('_sv5') / (pl.col('_svd') / pl.col('m') * 5)).alias('side_burst5'),
        (pl.col('vol_5') / pl.col('_sv5')).alias('share_of_side5'))
    e = e.with_columns([pl.when(pl.col('has_vol') == 1).then(pl.col(c)).otherwise(None).alias(c) for c in VOL])
    return e.rename({'m': 'entry_minute'}).select('session', 'tag', 'strike', 'right', 'entry_minute', 'has_vol', *VOL)

def build(root):
    F = pl.read_parquet(os.path.join(OUT, f'features_{root}.parquet'), columns=['session', 'tag', 'strike', 'right', 'entry_minute', 'close_minute'])
    parts = {d: x for (d,), x in F.group_by('session')}
    import multiprocessing as mp
    with mp.get_context('spawn').Pool(4) as pool:
        out = pool.starmap(session, [(root, d, parts[d]) for d in sorted(parts)], chunksize=8)
    V = pl.concat([o for o in out if o is not None], how='vertical_relaxed').sort('session', 'tag', 'entry_minute', 'right', 'strike')
    V.write_parquet(os.path.join(OUT, f'volume_features_{root}.parquet'), compression='zstd', compression_level=19)
    print(root, 'sessions with bars', sum(o is not None for o in out), 'of', len(parts), 'trades', V.height, 'with volume', int(V['has_vol'].sum()), flush=True)

def test():
    import lightgbm as lgb
    import step5.model as M
    T = M.load()
    V = pl.concat([pl.read_parquet(os.path.join(OUT, f'volume_features_{r}.parquet')).with_columns(pl.lit(r).alias('root'))
                   for r in M.PRODUCTS if os.path.exists(os.path.join(OUT, f'volume_features_{r}.parquet'))])
    key = ['root', 'session', 'tag', 'strike', 'right', 'entry_minute']
    if V.select(key).is_duplicated().any(): raise SystemExit('a trade has two volume rows')
    n = T.height
    T = T.join(V, on=key, how='inner').filter(pl.col('has_vol') == 1)
    if T.select(key).is_duplicated().any() or T.height > n: raise SystemExit('the join matched a trade twice')
    T = T.with_columns(pl.max_horizontal(pl.col('max_bid').fill_null(0.0), pl.col('settle')).alias('_pp'))
    T = T.with_columns((((pl.col('_pp') - pl.col('entry_ask')) * 100 - M.FEE - pl.when(pl.col('_pp') > 0).then(M.FEE).otherwise(0.0)) / pl.col('cost')).alias('r_perfect'),
                       pl.col('r_trail50').clip(-1.0, 4.0).alias('y_b')).drop('_pp')
    print(T.group_by('part', 'root').agg(pl.len(), pl.col('session').min().alias('first'), pl.col('session').max().alias('last')).sort('part', 'root'), flush=True)
    base = list(M.FEATURES)
    heads, rows, srows, imps = [], [], [], []
    for label, feats in (('quotes only', base), ('quotes + volume', base + VOL)):
        M.FEATURES = feats
        for name, target, obj, s in (('A: reaches 3x', 'reach3', 'binary', 'sa'), ('B: trail50 result', 'y_b', 'regression', 'sb')):
            mdl = M.fit(T, target, obj)
            T = T.with_columns(pl.Series(s, mdl.predict(M.matrix(T), num_iteration=mdl.best_iteration)))
            for part in ('valid', 'check'):
                P = T.filter(pl.col('part') == part)
                heads.append(dict(features=label, model=name, part=part, trades=P.height, rounds=mdl.best_iteration,
                                  auc_reach3=M.auc(P['reach3'].to_numpy(), P[s].to_numpy()),
                                  corr_trail50=float(np.corrcoef(P[s].to_numpy(), P['r_trail50'].to_numpy())[0, 1])))
            cuts = {lab: (T.filter(pl.col('part') == 'valid')[s].quantile(q, 'linear') if q > 0 else -np.inf) for lab, q in M.TOPS}
            C = T.filter(pl.col('part') == 'check')
            for lab, _ in M.TOPS:
                rows.append(M.bucket_rows(C.filter(pl.col(s) >= cuts[lab]), lab).with_columns(pl.lit(label).alias('features'), pl.lit(name).alias('model'),
                                                                                             pl.lit(float(cuts[lab])).alias('cut')))
            if True:   # both models' top buckets
                for lab, _ in M.TOPS[3:]:
                    for x in M.EXITS:
                        o = dict(features=label, model=name, bucket=lab, exit=x); o.update(M.stress(C.filter(pl.col(s) >= cuts[lab]), x)); srows.append(o)
            g = mdl.feature_importance('gain')
            imps.append(pl.DataFrame({'feature': feats, 'share': g / g.sum()}).with_columns(pl.lit(label).alias('features'), pl.lit(name).alias('model')))
    r6 = lambda d: d.with_columns([pl.col(c).round(6) for c, t in d.schema.items() if t == pl.Float64])
    H = pl.DataFrame(heads).with_columns(pl.concat_str(['features', 'model', 'part'], separator=' | ').alias('id')); r6(H).write_csv(os.path.join(OUT, 'volume_headline.csv'))
    B = pl.concat(rows, how='diagonal_relaxed').with_columns(pl.concat_str(['features', 'model', 'bucket'], separator=' | ').alias('id'))
    r6(B).write_csv(os.path.join(OUT, 'volume_buckets.csv'))
    S = pl.DataFrame(srows, infer_schema_length=None).with_columns(pl.concat_str(['features', 'model', 'bucket', 'exit'], separator=' | ').alias('id'))
    r6(S).write_csv(os.path.join(OUT, 'volume_stress.csv'))
    I = pl.concat(imps).sort('features', 'model', 'share', descending=[False, False, True]).with_columns(pl.concat_str(['features', 'model', 'feature'], separator=' | ').alias('id'))
    r6(I).write_csv(os.path.join(OUT, 'volume_importance.csv'))
    pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_rows(60)
    print(H); print(B.select('features', 'model', 'bucket', 'trades', 'reached_3x', 'avg_pct_hold', 'avg_pct_trail30', 'avg_pct_trail50', 'win_rate_trail50'))
    print(S.select('features', 'bucket', 'exit', 'trades', 'days', 'avg_pct', 'ci_low', 'ci_high', 'without_best_5_days', 'avg_pct_2025', 'avg_pct_2026'))
    print(I.filter(pl.col('features') == 'quotes + volume').group_by('model').head(12))

if __name__ == '__main__':
    if sys.argv[1] == 'features':
        for r in (sys.argv[2].split(',') if len(sys.argv) > 2 else ['SPY', 'QQQ', 'IWM', 'SPXW']): build(r)
    elif sys.argv[1] == 'one':
        pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(260)
        d = dt.date.fromisoformat(sys.argv[3])
        F = pl.read_parquet(os.path.join(OUT, f'features_{sys.argv[2]}.parquet')).filter(pl.col('session') == d)
        print(session(sys.argv[2], d, F).filter(pl.col('has_vol') == 1).sort('vol_5', descending=True).head(8))
    else:
        test()
