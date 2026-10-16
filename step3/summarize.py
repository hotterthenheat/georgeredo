"""Step 3c: every one of step 2's 10.5 million trades broken down. How far each one ran (the % per trade), what the losing
trades looked like, which ways out of a trade lost least, and whether anything known when buying separated winners from
losers. Nothing is tuned on the whole sample: rules are picked on 2022-2024 (discovery) and read, unchanged, on
2025-2026 (check).

A trade is one contract bought at the ask (step 2). Its result is a share of the price paid ("%"), and in dollars for
one contract. Fees: FEE a contract on the buy, and on the sale when there is one (a target, a stop, a time exit, or worth
something at the close); none when it expires worthless.

Ways out (exits.csv), every combination of
- a target: sell the first minute the bid reaches +25%, +50%, +100%, +150%, +200%, +300%, +500% or +1,000%, at exactly
  that price; or no target,
- a stop: sell at the bid the first minute it falls to -30%, -50% or -70%; or no stop,
- a time exit: the close (hold), 30 minutes before the close, or 60 minutes after buying, at the last bid by then.
Whichever comes first. 9 x 4 x 3 = 108 ways out.

Writes step3/out/: reach.csv, reach_summary.csv, outcomes.csv, outcomes_near.csv, losers.csv, losers_near.csv, exits.csv,
exits_best.csv, exits_summary.csv, targets_near.csv, filters.csv, filters_best.csv, headline.csv
  python3 -I step3/summarize.py
"""
import itertools, os, sys
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, 'out')
FEE = 0.65
CHECK_FROM = pl.date(2025, 1, 1)
MIN_DISC = 300   # a way out or a condition is judged only on at least this many 2022-2024 trades
TARGETS = [('none', None, None), ('+25%', 't125', 1.25), ('+50%', 't150', 1.5), ('+100%', 't200', 2.0), ('+150%', 't250', 2.5), ('+200%', 't300', 3.0),
           ('+300%', 't400', 4.0), ('+500%', 't600', 6.0), ('+1,000%', 't1100', 11.0)]
STOPS = [('none', None), ('-30%', 's70'), ('-50%', 's50'), ('-70%', 's30')]
TIMES = [('close', None), ('30 min before close', 'c30'), ('60 min after buying', 'h60')]

def clock(col):
    t = pl.col(col).cast(pl.Int32) + 570
    h, m = t // 60, t % 60
    h12 = pl.when(h > 12).then(h - 12).otherwise(h)
    return pl.format('{}:{} {}', h12.cast(pl.Utf8), m.cast(pl.Utf8).str.zfill(2), pl.when(h >= 12).then(pl.lit('pm')).otherwise(pl.lit('am')))

def band(col, edges, name):
    b = pl.lit(None, pl.Utf8); o = pl.lit(None, pl.Int32)
    for i, (lo, hi, lab) in enumerate(edges):
        f = (pl.col(col) > lo) & (pl.col(col) <= hi)
        b = pl.when(f).then(pl.lit(lab)).otherwise(b); o = pl.when(f).then(pl.lit(i)).otherwise(o)
    return [b.alias(name), o.alias(name + '_order')]

def load(root):
    P = pl.read_parquet(os.path.join(OUT, f'paths_{root}.parquet'))
    F = pl.read_parquet(os.path.join(OUT, f'features_{root}.parquet')).select(
        'session', 'entry_minute', 'spot_entry', 'spot_open', 'spot_close', 'close_minute', 'high_so_far', 'low_so_far', 'vix_entry',
        'implied_move', 'gap', 'move', 'range_so_far', 'prior_range')
    O = pl.read_parquet(os.path.join(ROOT, 'step1', 'out', f'contracts_{root}.parquet'), columns=['session', 'strike', 'right', 'open_mid'])
    T = P.join(F, on=['session', 'entry_minute']).join(O, on=['session', 'strike', 'right'], how='left')
    return T.with_columns(pl.lit('SPX' if root == 'SPXW' else root).alias('product'))

DIST = [(-1e9, -1.0, 'ITM more than 1%'), (-1.0, -0.5, 'ITM 0.5–1%'), (-0.5, -0.25, 'ITM 0.25–0.5%'), (-0.25, 0.0, 'ITM 0–0.25%'),
        (0.0, 0.25, 'OTM 0–0.25%'), (0.25, 0.5, 'OTM 0.25–0.5%'), (0.5, 1.0, 'OTM 0.5–1%'), (1.0, 2.0, 'OTM 1–2%'), (2.0, 1e9, 'OTM more than 2%')]
NEARB = [(-0.5, 0.0, 'ITM 0–0.5%'), (0.0, 0.5, 'OTM 0–0.5%'), (0.5, 1.0, 'OTM 0.5–1%')]
OUTC = [(-1e9, -0.9999, 'Expired worthless (−100%)'), (-0.9999, -0.5, 'Lost 50–99%'), (-0.5, 0.0, 'Lost 0–50%'), (0.0, 1.0, 'Up 0–100%'),
        (1.0, 2.0, 'Up 100–200%'), (2.0, 1e12, 'Up 200% or more')]

def prep(root):
    """one product's trades with what was known when buying, where each stood, and how it ended if held"""
    T = load(root)
    sgn = pl.when(pl.col('right') == 'CALL').then(1.0).otherwise(-1.0)
    T = T.with_columns(
        pl.when(pl.col('right') == 'CALL').then((pl.col('spot_close') - pl.col('strike')).clip(0)).otherwise((pl.col('strike') - pl.col('spot_close')).clip(0)).alias('settle'),
        (sgn * (pl.col('strike') - pl.col('spot_entry')) / pl.col('spot_entry') * 100).alias('otm_entry_pct'),
        pl.when(pl.col('session') < CHECK_FROM).then(pl.lit('2022–2024')).otherwise(pl.lit('2025–2026')).alias('period'),
        clock('entry_minute').alias('entry_time'), (pl.col('entry_ask') * 100).alias('cost'),
        # what was known when buying, turned to the contract's side (positive = the underlying moved the contract's way)
        (sgn * pl.col('move') * 100).alias('move_dir'), (sgn * pl.col('gap') * 100).alias('gap_dir'),
        ((pl.col('entry_ask') - pl.col('entry_bid')) / ((pl.col('entry_ask') + pl.col('entry_bid')) / 2)).alias('spread'),
        (pl.col('range_so_far') / pl.col('implied_move')).alias('range_vs_implied'),
        (pl.col('implied_move') / pl.col('prior_range')).alias('implied_vs_prior'),
        pl.when(pl.col('high_so_far') > pl.col('low_so_far')).then(
            pl.when(pl.col('right') == 'CALL').then((pl.col('spot_entry') - pl.col('low_so_far')) / (pl.col('high_so_far') - pl.col('low_so_far')))
              .otherwise((pl.col('high_so_far') - pl.col('spot_entry')) / (pl.col('high_so_far') - pl.col('low_so_far')))).alias('range_position'),
        (((pl.col('entry_ask') + pl.col('entry_bid')) / 2) / pl.col('open_mid')).alias('since_open'),
        pl.col('session').dt.strftime('%a').alias('weekday'), pl.col('session').dt.weekday().alias('weekday_order'),
    )
    T = T.with_columns(*band('otm_entry_pct', DIST, 'distance'), *band('otm_entry_pct', NEARB, 'band'),
                       ((pl.col('settle') - pl.col('entry_ask')) / pl.col('entry_ask')).alias('hold_r'))
    return T.with_columns(*band('hold_r', OUTC, 'held'))

def exit_expr(tname, tcol, tk, scol, xcol):
    """price sold at (per share), and whether there was a sale before or at the close"""
    tmin = pl.col(tcol) if tcol else pl.lit(None, pl.Int32)
    smin = pl.col(scol) if scol else pl.lit(None, pl.Int32)
    first = pl.min_horizontal(tmin, smin)    # the earlier of target and stop (they never fall in the same minute)
    if xcol == 'c30':
        xm = pl.when(pl.col('entry_minute') < pl.col('close_minute') - 30).then(pl.col('close_minute') - 30)
    elif xcol == 'h60':
        xm = pl.when(pl.col('entry_minute') + 60 <= pl.col('close_minute')).then(pl.col('entry_minute') + 60)
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

def with_rule(df, tname, tcol, tk, sname, scol, xname, xcol):
    price, sold = exit_expr(tname, tcol, tk, scol, xcol)
    return df.with_columns(((price - pl.col('entry_ask')) * 100 - FEE - pl.when(sold).then(FEE).otherwise(0.0)).alias('net')).with_columns(
        (pl.col('net') / pl.col('cost')).alias('r'))

def stats(df, keys):
    return df.group_by(keys).agg(
        pl.len().alias('trades'),
        (pl.col('net') > 0).mean().alias('win_rate'),
        pl.col('r').filter(pl.col('net') > 0).mean().alias('avg_win_pct'),
        pl.col('r').filter(pl.col('net') <= 0).mean().alias('avg_loss_pct'),
        pl.col('r').mean().alias('avg_pct'),
        pl.col('net').filter(pl.col('net') > 0).mean().alias('avg_win_usd'),
        pl.col('net').filter(pl.col('net') <= 0).mean().alias('avg_loss_usd'),
        pl.col('net').mean().alias('avg_usd'))

r4 = lambda d: d.with_columns([pl.col(c).round(6) for c, t in d.schema.items() if t == pl.Float64])
def write(d, name, idkeys):
    """rounded in the file only: every count and pick below is made on the unrounded figures"""
    d = d.with_columns(pl.concat_str([pl.col(c).cast(pl.Utf8) for c in idkeys], separator=' | ').alias('id'))
    r4(d).write_csv(os.path.join(OUT, name)); return d

# 1. how far each trade ran: the share that reached each gain at some point after buying (the best bid against the price paid)
# 2. how each trade ended if held to the close, and what the losing ones did first
# Both one product at a time (the whole table does not fit in memory at once); parts 3 and 4 keep the trades within 1%.
REACH = [('+25%', 't125'), ('+50%', 't150'), ('+100%', 't200'), ('+150%', 't250'), ('+200%', 't300'), ('+300%', 't400'), ('+500%', 't600'), ('+1,000%', 't1100')]
keys = ['product', 'right', 'entry_minute', 'entry_time', 'distance', 'distance_order']
lose = pl.col('hold_r') < 0
KEEP = ['product', 'session', 'period', 'right', 'entry_minute', 'entry_time', 'band', 'band_order', 'otm_entry_pct', 'entry_bid', 'entry_ask', 'cost',
        'settle', 'close_minute'] + [c for _, c, _ in TARGETS if c] + [c for _, c in STOPS if c] + [c + '_bid' for _, c in STOPS if c] + \
       ['c30_bid', 'h60_bid', 'move_dir', 'gap_dir', 'vix_entry', 'spread', 'range_vs_implied', 'implied_vs_prior', 'range_position', 'since_open',
        'weekday', 'weekday_order']
A_parts, A2_parts, B_parts, L_parts, E_parts, TOTAL = [], [], [], [], [], 0
for root in ('SPY', 'QQQ', 'IWM', 'SPXW'):
    T = prep(root); TOTAL += T.height
    A_parts.append(T.group_by(keys).agg(pl.len().alias('trades'), (pl.col('cost')).median().alias('price_median'),
                                        *[pl.col(c).is_not_null().mean().alias('reach_' + c[1:]) for _, c in REACH],
                                        (pl.col('max_bid') <= pl.col('entry_bid')).fill_null(True).mean().alias('never_above_bid')))
    near = T.filter(pl.col('otm_entry_pct').abs() <= 0.5)
    A2_parts += [T.group_by('product').agg(pl.lit('All contracts').alias('which'), pl.len().alias('trades'), *[pl.col(c).is_not_null().mean().alias('reach_' + c[1:]) for _, c in REACH]),
                 near.group_by('product').agg(pl.lit('Within 0.5% of the price').alias('which'), pl.len().alias('trades'), *[pl.col(c).is_not_null().mean().alias('reach_' + c[1:]) for _, c in REACH])]
    B_parts.append(T.group_by('product', 'right', 'entry_minute', 'entry_time', 'distance', 'distance_order', 'held', 'held_order').agg(pl.len().alias('trades')))
    Lp = T.filter(lose).group_by(keys).agg(
        pl.len().alias('losing_trades'),
        (pl.col('settle') == 0).mean().alias('expired_worthless'),
        pl.col('t125').is_not_null().mean().alias('were_up_25'),
        pl.col('t150').is_not_null().mean().alias('were_up_50'),
        pl.col('t200').is_not_null().mean().alias('were_up_100'),
        (pl.col('max_bid') <= pl.col('entry_bid')).fill_null(True).mean().alias('never_above_bid'),
        (pl.col('s70') - pl.col('entry_minute')).median().alias('minutes_to_minus_30'),
        pl.col('hold_r').mean().alias('avg_loss_pct'))
    L_parts.append(Lp.join(T.group_by('product', 'right', 'entry_minute', 'distance').agg(pl.len().alias('trades'), lose.mean().alias('loss_rate')),
                           on=['product', 'right', 'entry_minute', 'distance']))
    E_parts.append(T.filter(pl.col('band').is_not_null()).select(KEEP))
    del T, near
A = write(pl.concat(A_parts).sort('product', 'right', 'entry_minute', 'distance_order'), 'reach.csv', ['product', 'right', 'entry_minute', 'distance'])
A2 = pl.concat(A2_parts, how='vertical_relaxed').sort('which', 'product')
B = pl.concat(B_parts)
B = B.with_columns((pl.col('trades') / pl.col('trades').sum().over('product', 'right', 'entry_minute', 'distance')).alias('share'))
B = write(B.sort('product', 'right', 'entry_minute', 'distance_order', 'held_order'), 'outcomes.csv', ['product', 'right', 'entry_minute', 'distance', 'held'])
L = write(pl.concat(L_parts).sort('product', 'right', 'entry_minute', 'distance_order'), 'losers.csv', ['product', 'right', 'entry_minute', 'distance'])

# 3. every way out, near the money (ITM 0-0.5%, OTM 0-0.5%, OTM 0.5-1%)
E = pl.concat(E_parts)
gk = ['product', 'right', 'entry_minute', 'entry_time', 'band', 'band_order']
rows = []
for (tn, tc, tk), (sn, sc), (xn, xc) in itertools.product(TARGETS, STOPS, TIMES):
    X = with_rule(E, tn, tc, tk, sn, sc, xn, xc)
    s_all = stats(X, gk)
    s_per = stats(X, gk + ['period']).pivot(on='period', index=gk, values=['trades', 'avg_pct', 'win_rate'])
    s = s_all.join(s_per, on=gk, how='left').with_columns(pl.lit(tn).alias('target'), pl.lit(sn).alias('stop'), pl.lit(xn).alias('time_exit'))
    rows.append(s)
EX = pl.concat(rows, how='diagonal_relaxed')
ren = {c: c.replace('2022–2024', 'disc').replace('2025–2026', 'check') for c in EX.columns}
EX = EX.rename(ren)
EX = EX.with_columns(pl.concat_str([pl.col('target'), pl.col('stop'), pl.col('time_exit')], separator=' · ').alias('rule'))
EX = write(EX.sort('product', 'right', 'entry_minute', 'band_order', 'rule'), 'exits.csv', ['product', 'right', 'entry_minute', 'band', 'rule'])
# for each group, the way out that did best on 2022-2024, and what it then did on 2025-2026
ok = EX.filter(pl.col('trades_disc') >= MIN_DISC)
BEST = ok.sort('avg_pct_disc', descending=True).group_by(gk, maintain_order=True).first()
HOLD = EX.filter(pl.col('rule') == 'none · none · close').select(gk + [pl.col('avg_pct_disc').alias('hold_disc'), pl.col('avg_pct_check').alias('hold_check')])
BEST = BEST.join(HOLD, on=gk, how='left').sort('product', 'right', 'entry_minute', 'band_order')
BEST = write(BEST.select(gk + ['rule', 'trades_disc', 'avg_pct_disc', 'win_rate_disc', 'trades_check', 'avg_pct_check', 'win_rate_check', 'hold_disc', 'hold_check']),
             'exits_best.csv', ['product', 'right', 'entry_minute', 'band'])
# the single best way out per product (all its groups pooled), picked on 2022-2024
SUMM = []
for (tn, tc, tk), (sn, sc), (xn, xc) in itertools.product(TARGETS, STOPS, TIMES):
    X = with_rule(E, tn, tc, tk, sn, sc, xn, xc)
    s = stats(X, ['product', 'period']).with_columns(pl.lit(f'{tn} · {sn} · {xn}').alias('rule'))
    SUMM.append(s)
SU = pl.concat(SUMM).pivot(on='period', index=['product', 'rule'], values=['trades', 'win_rate', 'avg_win_pct', 'avg_loss_pct', 'avg_pct'])
SU = SU.rename({c: c.replace('2022–2024', 'disc').replace('2025–2026', 'check') for c in SU.columns})
SU = write(SU.sort('product', 'avg_pct_disc', descending=[False, True]), 'exits_summary.csv', ['product', 'rule'])

# 4. what was known when buying: near the money (within 0.5%), every entry time, held to the close / sold at +100% / +100% or -50%
N = E.filter(pl.col('otm_entry_pct').abs() <= 0.5)
# 3b. near the money (within 0.5%), every entry time: each target, with no stop and with a -50% stop, otherwise held to the close
TT = []
for oi, (tn, tc, tk) in enumerate(TARGETS):
    for sn, sc in (('none', None), ('-50%', 's50')):
        X = with_rule(N, tn, tc, tk, sn, sc, 'close', None)
        s = stats(X, ['product']).join(stats(X, ['product', 'period']).pivot(on='period', index=['product'], values=['trades', 'win_rate', 'avg_pct']), on='product')
        TT.append(s.with_columns(pl.lit(tn).alias('target'), pl.lit(oi).alias('target_order'), pl.lit(sn).alias('stop')))
TT = pl.concat(TT, how='diagonal_relaxed')
TT = TT.rename({c: c.replace('2022–2024', 'disc').replace('2025–2026', 'check') for c in TT.columns})
TT = write(TT.sort('product', 'stop', 'target_order'), 'targets_near.csv', ['product', 'target', 'stop'])
# how trades within 0.5% ended if held, and what the losing ones did first, every entry time together
NEAR_D = ['ITM 0.25–0.5%', 'ITM 0–0.25%', 'OTM 0–0.25%', 'OTM 0.25–0.5%']
ON = B.filter(pl.col('distance').is_in(NEAR_D)).group_by('product', 'held', 'held_order').agg(pl.col('trades').sum())
ON = ON.with_columns((pl.col('trades') / pl.col('trades').sum().over('product')).alias('share'))
ON = write(ON.sort('product', 'held_order'), 'outcomes_near.csv', ['product', 'held'])
w = pl.col('losing_trades')
LN = L.filter(pl.col('distance').is_in(NEAR_D)).group_by('product').agg(
    w.sum().alias('losing_trades'), pl.col('trades').sum().alias('trades'),
    *[((pl.col(c) * w).sum() / w.sum()).alias(c) for c in ('expired_worthless', 'were_up_25', 'were_up_50', 'were_up_100', 'never_above_bid', 'avg_loss_pct')])
LN = write(LN.with_columns((pl.col('losing_trades') / pl.col('trades')).alias('loss_rate')).sort('product'), 'losers_near.csv', ['product'])

RULES = {'hold': ('none', None, None, 'none', None, 'close', None), 'tp100': ('+100%', 't200', 2.0, 'none', None, 'close', None),
         'tp100_sl50': ('+100%', 't200', 2.0, '-50%', 's50', 'close', None)}
FEAT = {
    'move_dir': ('Move since the open, the contract\'s way', [(-1e9, -0.5, 'Against, more than 0.5%'), (-0.5, -0.2, 'Against, 0.2–0.5%'), (-0.2, -0.05, 'Against, 0.05–0.2%'),
                 (-0.05, 0.05, 'Flat (within 0.05%)'), (0.05, 0.2, 'With, 0.05–0.2%'), (0.2, 0.5, 'With, 0.2–0.5%'), (0.5, 1e9, 'With, more than 0.5%')]),
    'gap_dir': ('Opening gap, the contract\'s way', [(-1e9, -0.5, 'Against, more than 0.5%'), (-0.5, -0.1, 'Against, 0.1–0.5%'), (-0.1, 0.1, 'Flat (within 0.1%)'),
                (0.1, 0.5, 'With, 0.1–0.5%'), (0.5, 1e9, 'With, more than 0.5%')]),
    'vix_entry': ('VIX when bought', [(0, 15, 'Under 15'), (15, 20, '15–20'), (20, 25, '20–25'), (25, 30, '25–30'), (30, 1e9, '30 or more')]),
    'spread': ('Bid/ask spread when bought', [(-1, 0.02, 'Under 2%'), (0.02, 0.05, '2–5%'), (0.05, 0.1, '5–10%'), (0.1, 0.2, '10–20%'), (0.2, 1e9, '20% or more')]),
    'range_vs_implied': ('Day\'s range so far against the move still priced', [(-1, 0.5, 'Under 0.5×'), (0.5, 1, '0.5–1×'), (1, 1.5, '1–1.5×'), (1.5, 2.5, '1.5–2.5×'), (2.5, 1e9, '2.5× or more')]),
    'implied_vs_prior': ('Move still priced against the session before\'s range', [(-1, 0.3, 'Under 0.3×'), (0.3, 0.5, '0.3–0.5×'), (0.5, 0.75, '0.5–0.75×'), (0.75, 1, '0.75–1×'), (1, 1e9, '1× or more')]),
    'range_position': ('Where the price stood in the day\'s range, the contract\'s way', [(-1, 0.2, 'Bottom fifth'), (0.2, 0.4, '2nd fifth'), (0.4, 0.6, 'Middle fifth'), (0.6, 0.8, '4th fifth'), (0.8, 1e9, 'Top fifth')]),
    'since_open': ('Contract\'s price against its own at 9:31', [(-1, 0.5, 'Under half'), (0.5, 0.8, '50–80%'), (0.8, 1.0, '80–100%'), (1.0, 1.5, '100–150%'), (1.5, 1e9, '150% or more')]),
}
# conditions that only exist once the session has run (no move, range or decay yet at 9:31) leave out the 9:31 entry
INTRADAY = {'move_dir', 'range_vs_implied', 'range_position', 'since_open'}
frows = []
for rk, (tn, tc, tk, sn, sc, xn, xc) in RULES.items():
    X = with_rule(N, tn, tc, tk, sn, sc, xn, xc)
    for f, (title, edges) in FEAT.items():
        Xf = X.with_columns(*band(f, edges, 'bucket')).filter(pl.col('bucket').is_not_null())
        if f in INTRADAY: Xf = Xf.filter(pl.col('entry_minute') > 1)
        for rights in ('both', 'CALL', 'PUT'):
            Xr = Xf if rights == 'both' else Xf.filter(pl.col('right') == rights)
            s = stats(Xr, ['product', 'bucket', 'bucket_order', 'period']).pivot(on='period', index=['product', 'bucket', 'bucket_order'], values=['trades', 'win_rate', 'avg_pct'])
            s = s.join(stats(Xr, ['product', 'bucket', 'bucket_order']).select('product', 'bucket', 'trades', 'win_rate', 'avg_pct', 'avg_usd'), on=['product', 'bucket'])
            frows.append(s.with_columns(pl.lit(rk).alias('rule'), pl.lit(f).alias('feature'), pl.lit(title).alias('feature_title'), pl.lit(rights).alias('rights')))
    # day of the week
    s = stats(X, ['product', 'weekday', 'weekday_order', 'period']).pivot(on='period', index=['product', 'weekday', 'weekday_order'], values=['trades', 'win_rate', 'avg_pct'])
    s = s.join(stats(X, ['product', 'weekday']).select('product', 'weekday', 'trades', 'win_rate', 'avg_pct', 'avg_usd'), on=['product', 'weekday'])
    frows.append(s.rename({'weekday': 'bucket', 'weekday_order': 'bucket_order'}).with_columns(pl.col('bucket_order').cast(pl.Int32), pl.lit(rk).alias('rule'),
                 pl.lit('weekday').alias('feature'), pl.lit('Day of the week').alias('feature_title'), pl.lit('both').alias('rights')))
FI = pl.concat(frows, how='diagonal_relaxed')
FI = FI.rename({c: c.replace('2022–2024', 'disc').replace('2025–2026', 'check') for c in FI.columns})
FI = write(FI.sort('rule', 'feature', 'rights', 'product', 'bucket_order'), 'filters.csv', ['rule', 'feature', 'rights', 'product', 'bucket'])
# the best condition per product and rule on 2022-2024 (at least MIN_DISC trades), and what it did on 2025-2026
FB = FI.filter(pl.col('trades_disc') >= MIN_DISC).sort('avg_pct_disc', descending=True).group_by(['rule', 'rights', 'product'], maintain_order=True).head(3)
FB = write(FB.select('rule', 'rights', 'product', 'feature_title', 'bucket', 'trades_disc', 'avg_pct_disc', 'win_rate_disc', 'trades_check', 'avg_pct_check', 'win_rate_check')
           .sort('rule', 'rights', 'product', 'avg_pct_disc', descending=[False, False, False, True]), 'filters_best.csv', ['rule', 'rights', 'product', 'feature_title', 'bucket'])

# headline counts
pos_ex = EX.filter((pl.col('trades_disc') >= MIN_DISC) & (pl.col('avg_pct_disc') > 0))
pos_fi = FI.filter((pl.col('trades_disc') >= MIN_DISC) & (pl.col('avg_pct_disc') > 0))
H = pl.DataFrame({
    'trades': [TOTAL], 'exit_cells': [EX.height], 'exit_cells_judged': [EX.filter(pl.col('trades_disc') >= MIN_DISC).height],
    'exit_cells_pos_disc': [pos_ex.height], 'exit_cells_pos_both': [pos_ex.filter(pl.col('avg_pct_check') > 0).height],
    'exit_groups': [BEST.height], 'exit_best_pos_check': [BEST.filter(pl.col('avg_pct_check') > 0).height],
    'filter_cells_judged': [FI.filter(pl.col('trades_disc') >= MIN_DISC).height], 'filter_cells_pos_disc': [pos_fi.height],
    'filter_cells_pos_both': [pos_fi.filter(pl.col('avg_pct_check') > 0).height],
    'fee': [FEE], 'min_disc': [MIN_DISC]})
H = r4(H).with_columns(pl.lit('all').alias('id')); H.write_csv(os.path.join(OUT, 'headline.csv'))
A2 = r4(A2).with_columns(pl.concat_str([pl.col('which'), pl.col('product')], separator=' | ').alias('id')); A2.write_csv(os.path.join(OUT, 'reach_summary.csv'))

pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(280); pl.Config.set_tbl_rows(60)
print(H.transpose(include_header=True)); print(A2)
print(SU.group_by('product', maintain_order=True).head(5).select('product', 'rule', 'trades_disc', 'avg_pct_disc', 'win_rate_disc', 'trades_check', 'avg_pct_check', 'win_rate_check'))
print(SU.filter(pl.col('rule').is_in(['none · none · close', '+100% · none · close'])).select('product', 'rule', 'avg_pct_disc', 'avg_pct_check'))
print(FB.filter(pl.col('rights') == 'both'))
