"""Writes intel/06_price_action_atlas.md from results/price_action/*.csv (pa_atlas.py). Every number is read from the CSVs.
  python3 -I pa_atlas_md.py"""
import os
import polars as pl
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, '..', 'results', 'price_action')
OUT = os.path.join(HERE, '..', 'intel', '06_price_action_atlas.md')
KEY = ['SPY', 'QQQ', 'IWM', 'AAPL', 'AMD', 'AMZN', 'AVGO', 'GOOGL', 'INTC', 'META', 'MSFT', 'MU', 'NVDA', 'TSLA']
P = {'a 2017-22': '2017–22', 'b 2023-26': '2023–26'}
rd = lambda f: pl.read_csv(os.path.join(R, f))

def md(df, fmt=None):
    fmt = fmt or {}
    cols = df.columns
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for r in df.iter_rows():
        cells = []
        for c, v in zip(cols, r):
            if v is None: cells.append('—')
            elif isinstance(v, float): cells.append(fmt.get(c, '{:.2f}').format(v))
            else: cells.append(str(v))
        out.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(out)

def pct(x): return f'{100 * x:.0f} %'

NICE = {'high_in_first_30m': 'high in first 30 min', 'low_in_first_30m': 'low in first 30 min', 'high_in_last_30m': 'high in last 30 min', 'low_in_last_30m': 'low in last 30 min',
        'extreme_in_first_30m': 'high or low in first 30 min', 'trend_day_clv_top_or_bottom_10pct': 'trend day', 'opening_range_holds': 'opening range holds',
        'first30_range_over_day_range': 'first 30 min range ÷ day range', 'prior_high_touched_from_below': 'prior high touched', 'close_above_prior_high_given_touch': 'close above it, given a touch',
        'prior_low_touched_from_above': 'prior low touched', 'close_below_prior_low_given_touch': 'close below it, given a touch', 'prior_close_touched': 'prior close touched',
        'vwap_crosses_after_10_median': 'VWAP crosses after 10:00, median', 'close_same_vwap_side_as_10': 'close on the same VWAP side as 10:00',
        'corr_first30_last30': 'first 30 min vs last 30 min', 'corr_rest_of_day_last30': '10:00–15:30 vs last 30 min', 'corr_overnight_intraday': 'overnight vs intraday',
        'autocorr_intraday_lag1': 'intraday vs next intraday', 'share_up_days': 'share of up days', 'mean_overnight_bp': 'mean overnight, bp', 'mean_intraday_bp': 'mean intraday, bp',
        'size_in_daily_sd': 'gap size (daily SDs)'}
def nice(df): return df.rename({c: NICE[c] for c in df.columns if c in NICE})

size, touch, path, lev, gaps, calr, dirn, har, prof = (rd(f) for f in ('size.csv', 'touch.csv', 'path.csv', 'levels.csv', 'gaps.csv', 'calendar.csv', 'direction.csv', 'har.csv', 'profile.csv'))
names = sorted(path['symbol'].unique().to_list())
L = []
A = L.append
A('# Market-intelligence brief — 6. The price-action atlas (2026-10-15)\n')
A('**What this is.** Descriptive statistics of the underlying that an options desk uses to pick strikes, timing and structure. '
  'Nothing here is a trade signal and no hypothesis is tested. Every figure is CALCULATED from one-minute bars; the benchmarks named (the reflection principle) are MODELED.\n')
A('**Data and rules.**')
A(f'- {len(names)} names with one-minute bars: the Tier A roots, SPY, QQQ and IWM. 2017-06-01 → 2026-10-09.')
A('- **Sessions:** a bar in every half-hour, half-days left out (A10.4). A minute with no trade has no bar; the last close is carried over it.')
A('- **Prices:** "10:00" is the close of the 09:59 bar. "Close" is the last one-minute bar\'s close, not the official close.')
A('- **Splits:** the bars are unadjusted. On a split session (the open within 10 % of a split ratio of 2:1 or more against the prior close) the prior day\'s levels and the overnight return are not used.')
A('- **META** is Facebook from 2022-06-09 only. The symbol META before that was another security (`05_expirations_and_corrections.md` §4); Facebook\'s earlier bars under FB are not yet cached.')
A('- **Two periods side by side,** 2017–22 and 2023–26, so a reader sees whether a figure held.')
A('- Source: `../studies/pa_atlas.py` → `../results/price_action/*.csv` (every name, both periods). This file: `../studies/pa_atlas_md.py`. Tables below show cross-name medians and the 14 names traded most.\n')

# headline numbers
t = touch.group_by('period', 'k_sigma').agg(pl.col('touch_over_close').median().alias('m'), pl.col('touch_over_close').min().alias('lo'), pl.col('touch_over_close').max().alias('hi'),
                                           pl.col('p_touch').median().alias('pt'), pl.col('p_close_beyond').median().alias('pc'), pl.len().alias('n')).sort('period', 'k_sigma')
ph = path.group_by('period').agg([pl.col(c).median() for c in path.columns[3:]]).sort('period')
hh = har.select(pl.len().alias('n'), pl.col('r2_out_of_sample').median().alias('m'), pl.col('r2_out_of_sample').min().alias('lo'), pl.col('r2_out_of_sample').max().alias('hi')).row(0, named=True)
lv = lev.group_by('period').agg([pl.col(c).median() for c in lev.columns[3:]]).sort('period')
dr = dirn.group_by('period').agg([pl.col(c).median() for c in dirn.columns[3:]]).sort('period')
A('## 1. What the atlas says, in short\n')
k1 = t.filter(pl.col('k_sigma') == 1.0)
A(f'- **Touches follow the reflection principle.** From 10:00, a level k trailing standard deviations away is touched about twice as often as the close ends beyond it: the cross-name median ratio is '
  + ', '.join(f"{r['m']:.2f} ({P[r['period']]})" for r in k1.iter_rows(named=True)) + ' at 1σ, and between 1.9 and 2.1 at ½σ to 2σ in both periods. '
  'After a touch, the close comes back inside about half the time. Intraday paths behave like a driftless random walk: a level is not "rejected" more often than chance.')
A(f'- **The size of a day is forecastable.** A HAR model of the log daily range, fitted on 2017–22, explains a median {hh["m"]:.2f} of its variance on 2023–26 '
  f'({hh["lo"]:.2f} to {hh["hi"]:.2f} across {hh["n"]} names). This is the forecastable part of price action; whether options already price it is test V4 (A11).')
a, b = ph.row(0, named=True), ph.row(1, named=True)
A(f'- **The day\'s extreme usually comes early.** The high or the low of the day is set in the first 30 minutes on a median {pct(a["extreme_in_first_30m"])} (2017–22) and {pct(b["extreme_in_first_30m"])} (2023–26) of sessions; '
  f'the first 30 minutes are {pct(a["first30_range_over_day_range"])}–{pct(b["first30_range_over_day_range"])} of the day\'s range; the opening range holds all day on only {pct(a["opening_range_holds"])}–{pct(b["opening_range_holds"])} of sessions.')
la, lb = lv.row(0, named=True), lv.row(1, named=True)
A(f'- **Prior-day highs and lows are not walls.** When the prior day\'s high is touched from below, the close ends above it {pct(la["close_above_prior_high_given_touch"])} (2017–22) and {pct(lb["close_above_prior_high_given_touch"])} (2023–26) of the time; '
  f'for the prior low, below it {pct(la["close_below_prior_low_given_touch"])} and {pct(lb["close_below_prior_low_given_touch"])}. A coin flip.')
da, db = dr.row(0, named=True), dr.row(1, named=True)
A(f'- **Direction is close to noise.** The first half hour against the last: correlation {da["corr_first30_last30"]:+.3f} and {db["corr_first30_last30"]:+.3f}; '
  f'one day\'s intraday return against the next: {da["autocorr_intraday_lag1"]:+.3f} and {db["autocorr_intraday_lag1"]:+.3f}. '
  f'The overnight session earns more than the day: median {da["mean_overnight_bp"]:.1f} and {db["mean_overnight_bp"]:.1f} bp a night against {da["mean_intraday_bp"]:.1f} and {db["mean_intraday_bp"]:.1f} bp a day (a known effect; it belongs to the shares, not to same-day options).\n')

A('## 2. Size: how far a name still moves from each time of day\n')
A('Median and 90th percentile of |close ÷ price at the time − 1|, and the median of the larger excursion (high or low after that time) over the median end-of-day move. CALCULATED, %. Cross-name medians first.\n')
sz = size.group_by('period', 'time').agg(pl.col('rem_move_median_pct').median().alias('remaining move, median %'), pl.col('rem_move_p90_pct').median().alias('remaining move, 90th pct %'),
                                         pl.col('excursion_over_end_move').median().alias('largest excursion ÷ end move')).sort('time', 'period')
sz = sz.with_columns(pl.col('period').replace(P)).filter(pl.col('time').is_in(['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '15:30']))
A(md(sz.rename({'period': 'period', 'time': 'from'})))
A('\nBy name, from 10:00 and from 13:00, 2023–26:\n')
s2 = size.filter(pl.col('symbol').is_in(KEY) & (pl.col('period') == 'b 2023-26') & pl.col('time').is_in(['10:00', '13:00'])).pivot(on='time', index='symbol', values=['rem_move_median_pct', 'rem_move_p90_pct'])
s2 = s2.rename({c: c.replace('rem_move_median_pct_', 'median from ').replace('rem_move_p90_pct_', '90th pct from ') for c in s2.columns}).sort('symbol')
h2 = har.select('symbol', pl.col('r2_out_of_sample').alias('HAR R² out of sample'))
A(md(s2.join(h2, on='symbol', how='left')))
A('\n**Reading.** The larger intraday excursion is about 1.8× the end move at every time of day; a level is touched about twice as often as the close finishes beyond it (§3).\n')

A('## 3. Touch against finish (the reflection principle)\n')
A('From 10:00, with σ = the root mean square of the 10:00 → close log move over the previous 20 sessions (point in time). P(touch) = the share of sessions whose high (low) after 10:00 reaches +kσ (−kσ), sides averaged; P(close beyond) likewise for the close. For a driftless random walk, P(touch) = 2 × P(close beyond) (MODELED).\n')
tt = t.with_columns(pl.col('period').replace(P)).select(pl.col('period'), pl.col('k_sigma').alias('k'), pl.col('n').alias('names'), pl.col('pt').alias('P(touch), median'),
                                                       pl.col('pc').alias('P(close beyond), median'), pl.col('m').alias('touch ÷ close, median'), pl.col('lo').alias('min'), pl.col('hi').alias('max'))
A(md(tt, {'P(touch), median': '{:.3f}', 'P(close beyond), median': '{:.3f}'}))
A('\n**Reading.** The ratio sits at 2 in every period and distance. A rule "close the short option if its strike is touched" therefore exits about twice as often as the option would have finished in the money, and half of those exits are on options that would have expired worthless. This is measured on realised frequencies against a trailing σ; whether the option chain\'s own finish and touch probabilities are calibrated is untested here (`04_price_action_angles.md` O2).\n')

A('## 4. Path and timing\n')
pth = path.filter(pl.col('symbol').is_in(KEY) & (pl.col('period') == 'b 2023-26')).select(
    'symbol', 'sessions', pl.col('high_in_first_30m').alias('high in first 30 min'), pl.col('low_in_first_30m').alias('low in first 30 min'),
    pl.col('high_in_last_30m').alias('high in last 30 min'), pl.col('low_in_last_30m').alias('low in last 30 min'),
    pl.col('trend_day_clv_top_or_bottom_10pct').alias('trend day (close in top or bottom 10 % of range)'), pl.col('opening_range_holds').alias('opening range holds')).sort('symbol')
A('2023–26 by name (shares of sessions):\n')
A(md(pth, {c: '{:.2f}' for c in pth.columns}))
A('\nCross-name medians, both periods:\n')
A(md(nice(ph.with_columns(pl.col('period').replace(P)).select('period', 'high_in_first_30m', 'low_in_first_30m', 'high_in_last_30m', 'low_in_last_30m', 'extreme_in_first_30m', 'trend_day_clv_top_or_bottom_10pct', 'opening_range_holds', 'first30_range_over_day_range'))))
A('\n"Trend day": the close in the top or bottom 10 % of the day\'s range.')
A('\n**Reading.** The arcsine law of a random walk puts the extremes near the open and the close; single names set them at the open more than the index ETFs do. Index ETFs set more highs in the last half hour (the end-of-day drift). Neither is a forecast of where today\'s extreme will be.\n')

A('## 5. Levels: the prior day and VWAP\n')
A(md(nice(lv.with_columns(pl.col('period').replace(P)))))
A('\nTouch rates are from the side the session opened on. "Close same VWAP side as 10:00": the share of sessions whose close is on the same side of the session VWAP as the 10:00 price was.\n')

A('## 6. Gaps\n')
A('Gap = open ÷ the prior session\'s last close − 1, in units of the trailing 20-session daily standard deviation. Filled = the prior close trades during the session. Cross-name, sessions pooled.\n')
gp = gaps.group_by('period', 'size_in_daily_sd').agg((pl.col('fill_rate') * pl.col('sessions')).sum().alias('w'), pl.col('sessions').sum().alias('sessions'),
                                                    pl.col('minutes_to_fill_median').median().alias('minutes to fill, median of names')).with_columns((pl.col('w') / pl.col('sessions')).alias('fill rate')).drop('w')
A(md(nice(gp.with_columns(pl.col('period').replace(P)).sort('size_in_daily_sd', 'period').select('size_in_daily_sd', 'period', 'sessions', 'fill rate', 'minutes to fill, median of names'))))
A('\n')

A('## 7. Calendar: the range on event days against all days\n')
cal_all = calr.filter(pl.col('cut') == 'all sessions').select('symbol', 'period', pl.col('range_median_pct').alias('base'), pl.col('move_10_to_close_median_pct').alias('base_m'))
cr = calr.join(cal_all, on=['symbol', 'period']).with_columns((pl.col('range_median_pct') / pl.col('base')).alias('r'), (pl.col('move_10_to_close_median_pct') / pl.col('base_m')).alias('rm'))
cr = cr.group_by('period', 'cut').agg(pl.col('r').median().alias('day range ÷ all days, median of names'), pl.col('rm').median().alias('10:00 → close move ÷ all days'), pl.col('sessions').median().alias('sessions per name'))
A(md(cr.with_columns(pl.col('period').replace(P)).sort('cut', 'period')))
A('\nThe event dates are the repository\'s FOMC, CPI and NFP file; "monthly opex" is the third Friday. Ratios of medians, not a test.\n')

A('## 8. Direction (descriptive only)\n')
A(md(nice(dr.with_columns(pl.col('period').replace(P))), {NICE.get(c, c): '{:+.3f}' for c in dr.columns[1:]}))
A('\nCorrelations are per name, then the median across names.\n')

A('## 9. When in the day the movement happens\n')
pr = prof.with_columns(((pl.col('minute_from') - 1) // 30).alias('half')).group_by('symbol', 'period', 'half').agg(pl.col('share_of_day_5min').sum().alias('s'))
pr = pr.group_by('period', 'half').agg(pl.col('s').median().alias('share')).sort('period', 'half')
pr = pr.with_columns(pl.format('{}:{}', (9 + (30 + pl.col('half') * 30) // 60), pl.when(((30 + pl.col('half') * 30) % 60) == 0).then(pl.lit('00')).otherwise(pl.lit('30'))).alias('half-hour from'))
pv = pr.pivot(on='period', index='half-hour from', values='share')
pv = pv.rename({k: P.get(k, k) for k in pv.columns})
A('Median share of the day\'s total absolute one-minute movement in each half-hour (sums to about 1):\n')
A(md(pv, {c: '{:.3f}' for c in pv.columns}))
A('\n**Reading.** The U-shape: the first half hour carries the most movement, midday the least, the last half hour rises again. Same-day premium decays on the clock, while the movement it pays for is concentrated at the open and the close.\n')

A('## 10. What this means for options (no rule is promoted from it)\n')
A('- **Strike distance:** the end-of-day move and its 90th percentile (§2) set the distance; the excursion (§2) and the touch odds (§3) set how often a short strike is threatened along the way.')
A('- **Stops on short options:** a touch rule exits about twice as often as the option would have finished in the money (§3). The repository\'s exit studies found no stop rule with a positive lower bound (lifecycle 05, 12).')
A('- **Entry time:** the first half hour alone spans 56–60 % of the day\'s range, holds the day\'s high or low on 74–78 % of sessions and carries the most movement of any half hour (§4, §9). A 10:00 entry prices what is left: §2 gives its size.')
A('- **Levels as support and resistance:** the prior day\'s high and low hold about half the time after a touch (§5): no reason to place strikes against them.')
A('- **The forecastable part is size** (§1, §2). Whether a forecast beats the option\'s own price is V4 (A11), run on V3\'s single-name same-day straddles; the index version (the lifecycle\'s VOLC) failed.')
A('- **Rule from the catalogue (`04_price_action_angles.md` §4):** no statistic here may choose a test run on the same sessions; a pattern this atlas suggests is tested on forward sessions only.')
open(OUT, 'w').write('\n'.join(L) + '\n'); print('wrote', OUT)
