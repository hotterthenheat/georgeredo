"""Step 4c: what selling near the high (a trailing stop) and buying on the turn (bounce, opening-range break) did, for
every trade of step4/out/trades_*.parquet. Picked on 2022-2024, read unchanged on 2025-2026, as in step 3.

Ways out compared: hold (worth at the close), trail20/30/40/50 (sold at the bid once it fell that far from the highest bid
since buying), and perfect (sold at the highest bid after buying, or worth at the close if more): the hindsight top,
shown only as the ceiling, never judged as a rule. Fees: FEE a contract on the buy and on the sale (none when a
contract expires worthless). captured: the bid sold at as a share of the highest bid after buying, for trades a trailing
stop sold.

Writes step4/out/: by_distance.csv, by_price.csv, summary.csv, runs.csv, headline.csv
  python3 -I step4/summarize.py
"""
import os
import polars as pl

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
FEE = 0.65
CHECK_FROM = pl.date(2025, 1, 1)
MIN_DISC = 300
EXITS = ['hold', 'trail20', 'trail30', 'trail40', 'trail50', 'perfect']
TAGS = {'fixed': 'Fixed times (step 2\'s trades)', 'bounce1.5': 'Turn up: 1.5× its low', 'bounce2': 'Turn up: 2× its low', 'bounce3': 'Turn up: 3× its low',
        'bounce5': 'Turn up: 5× its low', 'orb': 'Underlying breaks its 9:31–10:00 range'}
DIST = [(-1e9, -1.0, 'ITM more than 1%'), (-1.0, -0.5, 'ITM 0.5–1%'), (-0.5, -0.25, 'ITM 0.25–0.5%'), (-0.25, 0.0, 'ITM 0–0.25%'),
        (0.0, 0.25, 'OTM 0–0.25%'), (0.25, 0.5, 'OTM 0.25–0.5%'), (0.5, 1.0, 'OTM 0.5–1%'), (1.0, 2.0, 'OTM 1–2%'), (2.0, 1e9, 'OTM more than 2%')]
PRICE = [(0, 10, 'Under $10'), (10, 25, '$10–25'), (25, 50, '$25–50'), (50, 100, '$50–100'), (100, 200, '$100–200'), (200, 500, '$200–500'),
         (500, 1000, '$500–1,000'), (1000, 1e12, 'Over $1,000')]

def band(col, edges, name):
    b = pl.lit(None, pl.Utf8); o = pl.lit(None, pl.Int32)
    for i, (lo, hi, lab) in enumerate(edges):
        f = (pl.col(col) > lo) & (pl.col(col) <= hi)
        b = pl.when(f).then(pl.lit(lab)).otherwise(b); o = pl.when(f).then(pl.lit(i)).otherwise(o)
    return [b.alias(name), o.alias(name + '_order')]

def prep(root):
    T = pl.read_parquet(os.path.join(OUT, f'trades_{root}.parquet'))
    sgn = pl.when(pl.col('right') == 'CALL').then(1.0).otherwise(-1.0)
    T = T.with_columns(
        pl.lit('SPX' if root == 'SPXW' else root).alias('product'),
        pl.when(pl.col('right') == 'CALL').then((pl.col('spot_close') - pl.col('strike')).clip(0)).otherwise((pl.col('strike') - pl.col('spot_close')).clip(0)).alias('settle'),
        (sgn * (pl.col('strike') - pl.col('spot_entry')) / pl.col('spot_entry') * 100).alias('otm'),
        (pl.col('entry_ask') * 100).alias('cost'),
        pl.when(pl.col('session') < CHECK_FROM).then(pl.lit('disc')).otherwise(pl.lit('check')).alias('period'))
    T = T.with_columns(*band('otm', DIST, 'distance'), *band('cost', PRICE, 'price'))
    # each way out: the price sold at, and whether there was a sale
    cols = []
    for x in EXITS:
        if x == 'hold':
            price, sold = pl.col('settle'), pl.col('settle') > 0
        elif x == 'perfect':
            price = pl.max_horizontal(pl.col('max_bid').fill_null(0.0), pl.col('settle')); sold = price > 0
        else:
            hit = pl.col(x + '_minute').is_not_null()
            price = pl.when(hit).then(pl.col(x + '_bid')).otherwise(pl.col('settle')); sold = hit | (pl.col('settle') > 0)
        net = (price - pl.col('entry_ask')) * 100 - FEE - pl.when(sold).then(FEE).otherwise(0.0)
        cols += [net.alias('net_' + x), (net / pl.col('cost')).alias('r_' + x)]
    T = T.with_columns(cols)
    return T.with_columns([(pl.col(x + '_bid') / pl.col('max_bid')).alias('cap_' + x) for x in EXITS if x.startswith('trail')])

def stats(T, keys):
    """one row per group and way out, all years and each period"""
    rows = []
    for x in EXITS:
        a = [pl.len().alias('trades'), (pl.col('net_' + x) > 0).mean().alias('win_rate'),
             pl.col('r_' + x).filter(pl.col('net_' + x) > 0).mean().alias('avg_win_pct'),
             pl.col('r_' + x).filter(pl.col('net_' + x) <= 0).mean().alias('avg_loss_pct'),
             pl.col('r_' + x).mean().alias('avg_pct'), pl.col('net_' + x).mean().alias('avg_usd')]
        if x.startswith('trail'):
            a.append(pl.col('cap_' + x).filter(pl.col(x + '_minute').is_not_null()).median().alias('captured_median'))
        s = T.group_by(keys).agg(a)
        p = T.group_by(keys + ['period']).agg(pl.len().alias('trades'), pl.col('r_' + x).mean().alias('avg_pct'), (pl.col('net_' + x) > 0).mean().alias('win_rate'))
        p = p.pivot(on='period', index=keys, values=['trades', 'avg_pct', 'win_rate'])
        rows.append(s.join(p, on=keys, how='left').with_columns(pl.lit(x).alias('exit')))
    return pl.concat(rows, how='diagonal_relaxed')

r6 = lambda d: d.with_columns([pl.col(c).round(6) for c, t in d.schema.items() if t == pl.Float64])
def write(d, name, idkeys):
    """rounded in the file only; counts below use the unrounded figures"""
    d = d.with_columns(pl.concat_str([pl.col(c).cast(pl.Utf8) for c in idkeys], separator=' | ').alias('id'))
    r6(d).write_csv(os.path.join(OUT, name)); return d

D, P, S, R, total, by_tag = [], [], [], [], 0, []
for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
    T = prep(root); total += T.height
    by_tag.append(T.group_by('tag').len())
    D.append(stats(T, ['product', 'tag', 'right', 'distance', 'distance_order']))
    P.append(stats(T, ['product', 'tag', 'right', 'price', 'price_order']))
    S.append(stats(T, ['product', 'tag']).with_columns(pl.lit('All').alias('which')))
    S.append(stats(T.filter(pl.col('otm').abs() <= 0.5), ['product', 'tag']).with_columns(pl.lit('Within 0.5%').alias('which')))
    # how far trades kept going after the buy: the best bid against the price paid
    R.append(T.group_by('product', 'tag').agg(pl.len().alias('trades'), *[(pl.col('max_bid') >= k * pl.col('entry_ask')).fill_null(False).mean().alias(f'ran_{k}x') for k in (1.25, 1.5, 2, 3, 5, 10)],
                                             (pl.col('max_bid') <= pl.col('entry_bid')).fill_null(True).mean().alias('never_above_bid')))
    del T
ren = lambda d: d.rename({c: c.replace('_disc', '_disc').replace('_check', '_check') for c in d.columns})
D = write(pl.concat(D, how='diagonal_relaxed').sort('product', 'tag', 'right', 'distance_order', 'exit'), 'by_distance.csv', ['product', 'tag', 'right', 'distance', 'exit'])
P = write(pl.concat(P, how='diagonal_relaxed').sort('product', 'tag', 'right', 'price_order', 'exit'), 'by_price.csv', ['product', 'tag', 'right', 'price', 'exit'])
S = write(pl.concat(S, how='diagonal_relaxed').with_columns(pl.col('tag').replace_strict(TAGS).alias('entry')).sort('which', 'product', 'tag', 'exit'), 'summary.csv', ['which', 'product', 'tag', 'exit'])
R = write(pl.concat(R).with_columns(pl.col('tag').replace_strict(TAGS).alias('entry')).sort('product', 'tag'), 'runs.csv', ['product', 'tag'])

rules = pl.concat([D.with_columns(pl.lit('distance').alias('cut')), P.with_columns(pl.lit('price').alias('cut'))], how='diagonal_relaxed').filter(pl.col('exit') != 'perfect')
judged = rules.filter(pl.col('trades_disc') >= MIN_DISC)
pos = judged.filter(pl.col('avg_pct_disc') > 0)
both = pos.filter(pl.col('avg_pct_check') > 0)
H = pl.DataFrame({'trades': [total], 'cells': [rules.height], 'cells_judged': [judged.height], 'cells_pos_disc': [pos.height], 'cells_pos_both': [both.height],
                  'fee': [FEE], 'min_disc': [MIN_DISC]}).with_columns(pl.lit('all').alias('id'))
H.write_csv(os.path.join(OUT, 'headline.csv'))
both = write(both.sort('avg_pct_disc', descending=True), 'survivors.csv', ['cut', 'product', 'tag', 'right', 'distance', 'price', 'exit'])

pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_rows(80)
print(pl.concat(by_tag).group_by('tag').agg(pl.col('len').sum()).sort('tag'))
print(H)
print(S.filter(pl.col('which') == 'Within 0.5%').select('product', 'tag', 'exit', 'trades', 'win_rate', 'avg_win_pct', 'avg_loss_pct', 'avg_pct', 'avg_pct_disc', 'avg_pct_check', 'captured_median'))
print(R)
print(both.select('cut', 'product', 'tag', 'right', 'distance', 'price', 'exit', 'trades_disc', 'avg_pct_disc', 'trades_check', 'avg_pct_check').head(60))
