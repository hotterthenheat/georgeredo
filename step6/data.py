"""Step 6: the shared reader. Loads build.py's trades, forms step 5's derived features (the same expressions as
step5/model.py `load`), this step's day-context features, and the runner classes (PREREG section 2).

  from step6.data import load, FEATURES, CLASSES
"""
import os
import numpy as np, polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
import sys
sys.path.insert(0, ROOT)
from step1.breakdown import RAW   # noqa: E402  (the raw files' location, as steps 1-5)
WORK = os.environ.get('WORK', os.path.join(os.path.dirname(RAW), 'step6'))
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
ROOTS = ['SPY', 'QQQ', 'IWM', 'SPXW']
PRODUCTS = {'SPY': 0, 'QQQ': 1, 'IWM': 2, 'SPXW': 3}
EPS = 1e-9
# class -> (multiple threshold, at least?) ; the pairs (class, window)
CLASSES = {'R40': 1.40, 'R100': 2.00, 'R500': 6.00}
WINDOWS = (60, 1530)
PAIRS = [(c, w) for w in WINDOWS for c in CLASSES]
PRIMARY = [('R40', 60), ('R100', 60), ('R500', 1530)]
BANDS = ['DUD', '+10–40%', '+40–100%', '+100–500%', '+500% and up']
TIMES = {1: '9:31', 30: '10:00', 60: '10:30', 90: '11:00', 150: '12:00', 210: '1:00 pm', 270: '2:00 pm', 330: '3:00 pm'}
XLAB = ['ITM 0.5–1 move', 'ITM 0.2–0.5', 'ITM 0–0.2', 'OTM 0–0.2', 'OTM 0.2–0.5', 'OTM 0.5–1 move']

# step 5's 42, less kind, half_day and to_close (PREREG section 4), then this step's day context
STEP5 = ['product', 'is_call', 'weekday', 'entry_minute', 'otm', 'otm_im', 'price', 'spread', 'bid_size', 'ask_size', 'size_imb', 'turn',
         'low_age', 'fall', 'open_vs_low', 'ask_vs_open', 'mom1', 'mom5', 'mom15', 'dret1', 'dret5', 'dret15', 'dret30', 'dmove', 'dgap', 'pos',
         'new_ext5', 'new_against5', 'range_pct', 'prior_range_pct', 'rv15_pct', 'vix', 'vix_chg', 'vix_chg15', 'implied_rest', 'implied_open',
         'iv_now', 'iv_ratio', 'range_im']
CONTEXT = ['gap_abs', 'or30_im', 'vwap_side', 'vwap_im', 'or_state', 'uw_regime', 'flip_im', 'event', 'iv_entry']
FEATURES = STEP5 + CONTEXT

def step5_derived(T):
    """step5/model.py load(): the same expressions, on this step's columns (close_minute is 390: full sessions only)"""
    dirn = pl.when(pl.col('right') == 'CALL').then(1.0).otherwise(-1.0)
    rng = pl.col('hi_so_far') - pl.col('lo_so_far')
    T = T.with_columns(dirn.alias('dir'), (pl.lit(390) - pl.col('entry_minute')).alias('to_close'))
    T = T.with_columns(
        pl.col('root').replace_strict(PRODUCTS).alias('product_code'),
        (pl.col('right') == 'CALL').cast(pl.Int8).alias('is_call'),
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
    T = T.with_columns((pl.col('iv_now') / (pl.col('implied_open') / (pl.lit(390) - 1) ** 0.5)).alias('iv_ratio'))
    return T

def load(columns=None):
    T = pl.concat([pl.read_parquet(os.path.join(WORK, f'trades_{r}.parquet')) for r in ROOTS], how='vertical_relaxed')
    T = step5_derived(T).with_columns((pl.col('gap') * 100).abs().alias('gap_abs'))
    for c, x in CLASSES.items():
        for w in WINDOWS:
            T = T.with_columns((pl.col(f'peak_{w}') >= x * pl.col('entry_ask') - EPS).fill_null(False).alias(f'{c}_{w}'))
    for w in WINDOWS:
        m = pl.col(f'mult_{w}')
        band = pl.when(m.is_null() | (m <= 1.10 + EPS)).then(pl.lit(BANDS[0])).when(m < 1.40 - EPS).then(pl.lit(BANDS[1])) \
            .when(m < 2.0 - EPS).then(pl.lit(BANDS[2])).when(m < 6.0 - EPS).then(pl.lit(BANDS[3])).otherwise(pl.lit(BANDS[4]))
        T = T.with_columns(band.alias(f'band_{w}'), (m.is_null() | (m <= 1.10 + EPS)).alias(f'DUD_{w}'))
    T = T.with_columns(pl.col('session').cast(pl.Utf8).alias('date'))
    return T if columns is None else T.select(columns)
