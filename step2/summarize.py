"""Step 2c: summaries of step2/out/entries_*.parquet. How often a same-day contract bought at a fixed time reaches +100%,
and what "sell at +100%, otherwise hold to the close" did, by the contract's kind.

Every trade is one contract bought at the ask at the entry minute. Figures per contract are x100 (dollars). Two views
of the average:
- avg_usd: dollars per contract, one contract a trade.
- avg_pct: the average return on the premium paid, as if the same dollars went into every trade.
Fees: FEE dollars a contract a side (a typical retail commission; a broker's own may differ), on the buy, and on the
sale when there is one (sold at +100%, at the -50% stop, or worth something at the close). A contract that expires
worthless pays no second fee.
Break-even rate: the share of trades that must reach +100% for tp100 to break even (before fees), given what the
others lost on average in that group: L / (1 + L), L the average loss of the non-doubled trades as a share of premium.

Discovery and check: groups are judged on 2022-2024 (discovery) and then read on 2025-2026 (check) without change.

Writes step2/out/: headline.csv, near.csv, overview.csv, by_distance.csv, by_price.csv, by_year.csv, by_weekday.csv, discovery_check.csv,
recent_entries.csv
  python3 -I step2/summarize.py
"""
import os, sys
import polars as pl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from step2.double import load   # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
FEE = 0.65
CHECK_FROM = pl.date(2025, 1, 1)

def clock(col):
    t = pl.col(col).cast(pl.Int32) + 570
    h, m = t // 60, t % 60
    h12 = pl.when(h > 12).then(h - 12).otherwise(h)
    return pl.format('{}:{} {}', h12.cast(pl.Utf8), m.cast(pl.Utf8).str.zfill(2), pl.when(h >= 12).then(pl.lit('pm')).otherwise(pl.lit('am')))

T = pl.concat([load(p) for p in ('SPY', 'QQQ', 'IWM', 'SPXW')], how='vertical_relaxed')
hit = pl.col('double_minute').is_not_null()
T = T.with_columns(
    hit.alias('doubled'),
    clock('entry_minute').alias('entry_time'),
    pl.col('session').dt.year().alias('year'),
    pl.col('session').dt.strftime('%a').alias('weekday'), pl.col('session').dt.weekday().alias('weekday_order'),
    (pl.col('tp100') / pl.col('entry_ask')).alias('tp100_ret'),
    (pl.col('hold') / pl.col('entry_ask')).alias('hold_ret'),
    (pl.col('tp100_sl50') / pl.col('entry_ask')).alias('sl_ret'),
    # fees: the buy, and the sale when there is one
    (pl.col('tp100') * 100 - FEE - pl.when(hit | (pl.col('settle') > 0)).then(FEE).otherwise(0)).alias('tp100_net_usd'),
    (pl.col('tp100_sl50') * 100 - FEE - pl.when((pl.col('tp100_sl50_exit') != 'close') | (pl.col('settle') > 0)).then(FEE).otherwise(0)).alias('sl_net_usd'),
    (pl.col('hold') * 100 - FEE - pl.when(pl.col('settle') > 0).then(FEE).otherwise(0)).alias('hold_net_usd'),
)
T = T.with_columns((pl.col('tp100_net_usd') / (pl.col('entry_ask') * 100)).alias('tp100_net_ret'),
                   (pl.col('sl_net_usd') / (pl.col('entry_ask') * 100)).alias('sl_net_ret'),
                   (pl.col('hold_net_usd') / (pl.col('entry_ask') * 100)).alias('hold_net_ret'))

# distance from the underlying at the entry minute (out of the money positive), and the price paid
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
T = T.with_columns(*band('otm_entry_pct', DIST, 'distance'), (pl.col('entry_ask') * 100).alias('entry_usd'))
T = T.with_columns(*band('entry_usd', PRICE, 'price'))

def stats(keys, df=None):
    df = T if df is None else df
    nh = ~pl.col('doubled')
    g = df.group_by(keys).agg(
        pl.len().alias('trades'), pl.col('session').n_unique().alias('sessions'),
        pl.col('entry_usd').median().alias('entry_usd_median'),
        pl.col('doubled').mean().alias('doubled_rate'),
        (pl.col('max_multiple') >= 3).fill_null(False).mean().alias('reached_3x'),
        (pl.col('max_multiple') >= 5).fill_null(False).mean().alias('reached_5x'),
        (pl.col('max_multiple') >= 10).fill_null(False).mean().alias('reached_10x'),
        (pl.col('double_minute') - pl.col('entry_minute')).median().alias('minutes_to_double_median'),
        # sell at +100%, otherwise hold to the close
        (pl.col('tp100') > 0).mean().alias('win_rate'),
        (pl.col('tp100') * 100).filter(pl.col('tp100') > 0).mean().alias('avg_win_usd'),
        (pl.col('tp100') * 100).filter(pl.col('tp100') < 0).mean().alias('avg_loss_usd'),
        (pl.col('tp100') * 100).max().alias('biggest_win_usd'),
        (pl.col('tp100') * 100).min().alias('biggest_loss_usd'),
        (pl.col('tp100') * 100).mean().alias('avg_usd'),
        pl.col('tp100_ret').mean().alias('avg_pct'),
        pl.col('tp100_net_usd').mean().alias('avg_net_usd'),
        pl.col('tp100_net_ret').mean().alias('avg_net_pct'),
        (-pl.col('tp100_ret').filter(nh).mean()).alias('loss_if_not_doubled'),
        # for comparison: hold to the close, and +100% with a -50% stop
        (pl.col('hold') > 0).mean().alias('hold_win_rate'), pl.col('hold_ret').mean().alias('hold_avg_pct'), pl.col('hold_net_ret').mean().alias('hold_avg_net_pct'),
        (pl.col('tp100_sl50') > 0).mean().alias('sl_win_rate'), pl.col('sl_ret').mean().alias('sl_avg_pct'), pl.col('sl_net_ret').mean().alias('sl_avg_net_pct'),
    )
    L = pl.col('loss_if_not_doubled')
    return g.with_columns(pl.when(L > 0).then(L / (1 + L)).otherwise(0.0).alias('break_even_rate'))

ENTRY = ['entry_minute', 'entry_time']
r4 = lambda d: d.with_columns([pl.col(c).round(4) for c, t in d.schema.items() if t == pl.Float64])
def write(d, name, idkeys):
    d = r4(d).with_columns(pl.concat_str([pl.col(c).cast(pl.Utf8) for c in idkeys], separator=' | ').alias('id'))
    d.write_csv(os.path.join(OUT, name)); return d

O = write(stats(['product', 'right'] + ENTRY).sort('product', 'right', 'entry_minute'), 'overview.csv', ['product', 'right', 'entry_minute'])
D = write(stats(['product', 'right'] + ENTRY + ['distance', 'distance_order']).sort('product', 'right', 'entry_minute', 'distance_order'), 'by_distance.csv',
          ['product', 'right', 'entry_minute', 'distance'])
P = write(stats(['product', 'right'] + ENTRY + ['price', 'price_order']).sort('product', 'right', 'entry_minute', 'price_order'), 'by_price.csv',
          ['product', 'right', 'entry_minute', 'price'])
near = T.filter(pl.col('otm_entry_pct').abs() <= 0.5)
N = write(stats(['product', 'right'] + ENTRY, near).sort('product', 'right', 'entry_minute'), 'near.csv', ['product', 'right', 'entry_minute'])
Y = write(stats(['product', 'right', 'year'] + ENTRY, near).sort('product', 'right', 'entry_minute', 'year'), 'by_year.csv', ['product', 'right', 'entry_minute', 'year'])
W = write(stats(['product', 'right', 'weekday', 'weekday_order'], near).sort('product', 'right', 'weekday_order'), 'by_weekday.csv', ['product', 'right', 'weekday'])

# discovery (2022-2024) and check (2025-2026): every product x right x entry x distance group, judged on discovery
keys = ['product', 'right'] + ENTRY + ['distance', 'distance_order']
a = stats(keys, T.filter(pl.col('session') < CHECK_FROM)).select(keys + ['trades', 'sessions', 'doubled_rate', 'break_even_rate', 'avg_pct', 'avg_net_pct'])
b = stats(keys, T.filter(pl.col('session') >= CHECK_FROM)).select(keys + ['trades', 'sessions', 'doubled_rate', 'break_even_rate', 'avg_pct', 'avg_net_pct'])
DC = a.join(b, on=keys, how='full', coalesce=True, suffix='_check').rename({c: c + '_discovery' for c in ('trades', 'sessions', 'doubled_rate', 'break_even_rate', 'avg_pct', 'avg_net_pct')})
DC = write(DC.sort('product', 'right', 'entry_minute', 'distance_order'), 'discovery_check.csv', ['product', 'right', 'entry_minute', 'distance'])

# the headline counts
pos = DC.filter((pl.col('trades_discovery') >= 200) & (pl.col('avg_net_pct_discovery') > 0))
H = pl.DataFrame({
    'trades': [T.height], 'contracts': [T.select('product', 'session', 'strike', 'right').unique().height], 'sessions': [T.select('product', 'session').unique().height],
    'first': [str(T['session'].min())], 'last': [str(T['session'].max())],
    'distance_groups': [D.height], 'distance_groups_positive': [D.filter(pl.col('avg_pct') > 0).height], 'distance_groups_positive_net': [D.filter(pl.col('avg_net_pct') > 0).height],
    'price_groups': [P.height], 'price_groups_positive': [P.filter(pl.col('avg_pct') > 0).height], 'price_groups_positive_net': [P.filter(pl.col('avg_net_pct') > 0).height],
    'tp100_beats_hold': [D.filter(pl.col('avg_pct') > pl.col('hold_avg_pct')).height],
    'discovery_groups': [DC.filter(pl.col('trades_discovery') >= 200).height], 'discovery_positive_net': [pos.height],
    'check_positive_net': [pos.filter(pl.col('avg_net_pct_check') > 0).height],
    'near_doubled_min': [N['doubled_rate'].min()], 'near_doubled_max': [N['doubled_rate'].max()],
    'near_break_even_min': [N['break_even_rate'].min()], 'near_break_even_max': [N['break_even_rate'].max()],
    'near_trades': [near.height], 'near_doubled': [near['doubled'].mean()], 'near_loss_if_not_doubled': [-near.filter(~pl.col('doubled'))['tp100_ret'].mean()],
    'near_avg_net_pct': [near['tp100_net_ret'].mean()], 'fee': [FEE]})
H = r4(H).with_columns(pl.lit('all').alias('id')); H.write_csv(os.path.join(OUT, 'headline.csv'))

# contract by contract: the last 10 sessions of each product, strikes within 1% of the underlying at the entry
last = T.group_by('product').agg(pl.col('session').unique().sort().tail(10).alias('s')).explode('s')
R = T.join(last, left_on=['product', 'session'], right_on=['product', 's']).filter(pl.col('otm_entry_pct').abs() <= 1.0)
R = R.select('product', 'session', 'entry_time', 'entry_minute', 'strike', 'right', 'otm_entry_pct', 'spot_entry', 'entry_bid', 'entry_ask', 'max_bid', 'max_bid_minute',
             'max_multiple', 'double_minute', 'settle', 'tp100', 'hold', 'tp100_net_usd')
R = R.with_columns(pl.col('session').cast(pl.Utf8), clock('max_bid_minute').alias('max_bid_time'), clock('double_minute').alias('double_time'),
                   (pl.col('tp100') * 100).alias('tp100_usd'), (pl.col('hold') * 100).alias('hold_usd'),
                   pl.when(pl.col('double_minute').is_not_null()).then(pl.lit('Sold at +100%')).when(pl.col('settle') > 0).then(pl.lit('Held, in the money'))
                     .otherwise(pl.lit('Held, worthless')).alias('outcome'))
R = R.with_columns(pl.concat_str([pl.col('product'), pl.col('session'), pl.col('entry_minute').cast(pl.Utf8), pl.col('right'), pl.col('strike').cast(pl.Utf8)], separator=' | ').alias('id'))
R = r4(R.sort('product', 'session', 'entry_minute', 'right', 'strike'))
R.write_csv(os.path.join(OUT, 'recent_entries.csv'))

pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(260); pl.Config.set_tbl_rows(80)
print('trades', T.height)
print(O.select('product', 'right', 'entry_time', 'trades', 'doubled_rate', 'break_even_rate', 'win_rate', 'avg_win_usd', 'avg_loss_usd', 'avg_pct', 'avg_net_pct', 'hold_avg_pct', 'sl_avg_net_pct'))
print(H.transpose(include_header=True))
print(N.select('product', 'right', 'entry_time', 'trades', 'doubled_rate', 'break_even_rate', 'avg_net_pct', 'sl_avg_net_pct', 'hold_avg_pct'))
print('groups (product x right x entry x distance):', DC.height, ' with 200+ discovery trades:', DC.filter(pl.col('trades_discovery') >= 200).height,
      ' positive after fees in discovery:', pos.height, ' of those positive after fees in check:', pos.filter(pl.col('avg_net_pct_check') > 0).height)
print(pos.select('product', 'right', 'entry_time', 'distance', 'trades_discovery', 'avg_net_pct_discovery', 'trades_check', 'avg_net_pct_check'))
print('recent rows', R.height, os.path.getsize(os.path.join(OUT, 'recent_entries.csv')))
