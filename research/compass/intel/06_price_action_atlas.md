# Market-intelligence brief — 6. The price-action atlas (2026-10-15)

**What this is.** Descriptive statistics of the underlying that an options desk uses to pick strikes, timing and structure. Nothing here is a trade signal and no hypothesis is tested. Every figure is CALCULATED from one-minute bars; the benchmarks named (the reflection principle) are MODELED.

**Data and rules.**
- 43 names with one-minute bars: the Tier A roots, SPY, QQQ and IWM. 2017-06-01 → 2026-10-09.
- **Sessions:** a bar in every half-hour, half-days left out (A10.4). A minute with no trade has no bar; the last close is carried over it.
- **Prices:** "10:00" is the close of the 09:59 bar. "Close" is the last one-minute bar's close, not the official close.
- **Splits:** the bars are unadjusted. On a split session (the open within 10 % of a split ratio of 2:1 or more against the prior close) the prior day's levels and the overnight return are not used.
- **META** is Facebook from 2022-06-09 only. The symbol META before that was another security (`05_expirations_and_corrections.md` §4); Facebook's earlier bars under FB are not yet cached.
- **Two periods side by side,** 2017–22 and 2023–26, so a reader sees whether a figure held.
- Source: `../studies/pa_atlas.py` → `../results/price_action/*.csv` (every name, both periods). This file: `../studies/pa_atlas_md.py`. Tables below show cross-name medians and the 14 names traded most.

## 1. What the atlas says, in short

- **Touches follow the reflection principle.** From 10:00, a level k trailing standard deviations away is touched about twice as often as the close ends beyond it: the cross-name median ratio is 2.00 (2017–22), 2.04 (2023–26) at 1σ, and between 1.9 and 2.1 at ½σ to 2σ in both periods. After a touch, the close comes back inside about half the time. Intraday paths behave like a driftless random walk: a level is not "rejected" more often than chance.
- **The size of a day is forecastable.** A HAR model of the log daily range, fitted on 2017–22, explains a median 0.21 of its variance on 2023–26 (0.07 to 0.43 across 43 names). This is the forecastable part of price action; whether options already price it is test V4 (A11).
- **The day's extreme usually comes early.** The high or the low of the day is set in the first 30 minutes on a median 74 % (2017–22) and 78 % (2023–26) of sessions; the first 30 minutes are 56 %–60 % of the day's range; the opening range holds all day on only 3 %–4 % of sessions.
- **Prior-day highs and lows are not walls.** When the prior day's high is touched from below, the close ends above it 52 % (2017–22) and 52 % (2023–26) of the time; for the prior low, below it 50 % and 49 %. A coin flip.
- **Direction is close to noise.** The first half hour against the last: correlation -0.022 and +0.009; one day's intraday return against the next: -0.070 and -0.061. The overnight session earns more than the day: median 4.9 and 6.8 bp a night against 1.1 and 4.4 bp a day (a known effect; it belongs to the shares, not to same-day options).

## 2. Size: how far a name still moves from each time of day

Median and 90th percentile of |close ÷ price at the time − 1|, and the median of the larger excursion (high or low after that time) over the median end-of-day move. CALCULATED, %. Cross-name medians first.

| period | from | remaining move, median % | remaining move, 90th pct % | largest excursion ÷ end move |
|---|---|---|---|---|
| 2017–22 | 10:00 | 0.66 | 2.10 | 1.77 |
| 2023–26 | 10:00 | 0.72 | 1.88 | 1.77 |
| 2017–22 | 11:00 | 0.56 | 1.72 | 1.79 |
| 2023–26 | 11:00 | 0.55 | 1.56 | 1.79 |
| 2017–22 | 12:00 | 0.46 | 1.40 | 1.79 |
| 2023–26 | 12:00 | 0.47 | 1.33 | 1.81 |
| 2017–22 | 13:00 | 0.38 | 1.28 | 1.81 |
| 2023–26 | 13:00 | 0.41 | 1.10 | 1.79 |
| 2017–22 | 14:00 | 0.34 | 1.11 | 1.78 |
| 2023–26 | 14:00 | 0.33 | 0.91 | 1.79 |
| 2017–22 | 15:00 | 0.26 | 0.85 | 1.77 |
| 2023–26 | 15:00 | 0.25 | 0.70 | 1.80 |
| 2017–22 | 15:30 | 0.20 | 0.67 | 1.77 |
| 2023–26 | 15:30 | 0.20 | 0.55 | 1.79 |

By name, from 10:00 and from 13:00, 2023–26:

| symbol | median from 10:00 | median from 13:00 | 90th pct from 10:00 | 90th pct from 13:00 | HAR R² out of sample |
|---|---|---|---|---|---|
| AAPL | 0.56 | 0.37 | 1.67 | 1.02 | 0.22 |
| AMD | 1.12 | 0.64 | 3.33 | 1.82 | 0.13 |
| AMZN | 0.74 | 0.41 | 1.92 | 1.14 | 0.17 |
| AVGO | 0.97 | 0.59 | 2.61 | 1.57 | 0.23 |
| GOOGL | 0.71 | 0.42 | 1.88 | 1.06 | 0.07 |
| INTC | 1.19 | 0.66 | 3.10 | 1.95 | 0.32 |
| IWM | 0.53 | 0.27 | 1.37 | 0.85 | 0.20 |
| META | 0.80 | 0.50 | 2.22 | 1.35 | 0.18 |
| MSFT | 0.54 | 0.35 | 1.62 | 0.91 | 0.21 |
| MU | 1.09 | 0.67 | 3.16 | 1.87 | 0.38 |
| NVDA | 1.01 | 0.56 | 2.98 | 1.76 | 0.25 |
| QQQ | 0.48 | 0.26 | 1.33 | 0.79 | 0.26 |
| SPY | 0.34 | 0.20 | 0.99 | 0.66 | 0.31 |
| TSLA | 1.32 | 0.75 | 3.55 | 2.06 | 0.19 |

**Reading.** The larger intraday excursion is about 1.8× the end move at every time of day; a level is touched about twice as often as the close finishes beyond it (§3).

## 3. Touch against finish (the reflection principle)

From 10:00, with σ = the root mean square of the 10:00 → close log move over the previous 20 sessions (point in time). P(touch) = the share of sessions whose high (low) after 10:00 reaches +kσ (−kσ), sides averaged; P(close beyond) likewise for the close. For a driftless random walk, P(touch) = 2 × P(close beyond) (MODELED).

| period | k | names | P(touch), median | P(close beyond), median | touch ÷ close, median | min | max |
|---|---|---|---|---|---|---|---|
| 2017–22 | 0.50 | 43 | 0.579 | 0.296 | 1.99 | 1.83 | 2.14 |
| 2017–22 | 1.00 | 43 | 0.297 | 0.149 | 2.00 | 1.80 | 2.17 |
| 2017–22 | 1.50 | 43 | 0.143 | 0.072 | 1.99 | 1.82 | 2.21 |
| 2017–22 | 2.00 | 43 | 0.070 | 0.036 | 1.99 | 1.76 | 2.55 |
| 2023–26 | 0.50 | 40 | 0.587 | 0.289 | 2.01 | 1.88 | 2.16 |
| 2023–26 | 1.00 | 40 | 0.301 | 0.148 | 2.04 | 1.91 | 2.21 |
| 2023–26 | 1.50 | 40 | 0.147 | 0.071 | 2.03 | 1.85 | 2.38 |
| 2023–26 | 2.00 | 40 | 0.071 | 0.034 | 2.05 | 1.74 | 2.78 |

**Reading.** The ratio sits at 2 in every period and distance. A rule "close the short option if its strike is touched" therefore exits about twice as often as the option would have finished in the money, and half of those exits are on options that would have expired worthless. This is measured on realised frequencies against a trailing σ; whether the option chain's own finish and touch probabilities are calibrated is untested here (`04_price_action_angles.md` O2).

## 4. Path and timing

2023–26 by name (shares of sessions):

| symbol | sessions | high in first 30 min | low in first 30 min | high in last 30 min | low in last 30 min | trend day (close in top or bottom 10 % of range) | opening range holds |
|---|---|---|---|---|---|---|---|
| AAPL | 938 | 0.39 | 0.45 | 0.16 | 0.12 | 0.20 | 0.05 |
| AMD | 938 | 0.43 | 0.42 | 0.12 | 0.11 | 0.22 | 0.05 |
| AMZN | 938 | 0.41 | 0.43 | 0.14 | 0.12 | 0.21 | 0.05 |
| AVGO | 938 | 0.42 | 0.43 | 0.14 | 0.13 | 0.23 | 0.06 |
| GOOGL | 938 | 0.42 | 0.46 | 0.16 | 0.12 | 0.21 | 0.06 |
| INTC | 938 | 0.42 | 0.44 | 0.11 | 0.13 | 0.25 | 0.04 |
| IWM | 938 | 0.37 | 0.34 | 0.14 | 0.14 | 0.24 | 0.01 |
| META | 938 | 0.43 | 0.41 | 0.13 | 0.13 | 0.24 | 0.05 |
| MSFT | 938 | 0.41 | 0.42 | 0.16 | 0.13 | 0.22 | 0.05 |
| MU | 938 | 0.42 | 0.43 | 0.13 | 0.11 | 0.22 | 0.06 |
| NVDA | 938 | 0.40 | 0.42 | 0.15 | 0.12 | 0.25 | 0.04 |
| QQQ | 938 | 0.29 | 0.34 | 0.17 | 0.14 | 0.25 | 0.01 |
| SPY | 938 | 0.23 | 0.29 | 0.21 | 0.14 | 0.24 | 0.00 |
| TSLA | 938 | 0.41 | 0.41 | 0.12 | 0.10 | 0.25 | 0.04 |

Cross-name medians, both periods:

| period | high in first 30 min | low in first 30 min | high in last 30 min | low in last 30 min | high or low in first 30 min | trend day | opening range holds | first 30 min range ÷ day range |
|---|---|---|---|---|---|---|---|---|
| 2017–22 | 0.38 | 0.39 | 0.16 | 0.14 | 0.74 | 0.27 | 0.03 | 0.56 |
| 2023–26 | 0.40 | 0.42 | 0.15 | 0.12 | 0.78 | 0.24 | 0.04 | 0.60 |

"Trend day": the close in the top or bottom 10 % of the day's range.

**Reading.** The arcsine law of a random walk puts the extremes near the open and the close; single names set them at the open more than the index ETFs do. Index ETFs set more highs in the last half hour (the end-of-day drift). Neither is a forecast of where today's extreme will be.

## 5. Levels: the prior day and VWAP

| period | prior high touched | close above it, given a touch | prior low touched | close below it, given a touch | prior close touched | VWAP crosses after 10:00, median | close on the same VWAP side as 10:00 |
|---|---|---|---|---|---|---|---|
| 2017–22 | 0.30 | 0.52 | 0.30 | 0.50 | 0.63 | 10.50 | 0.54 |
| 2023–26 | 0.32 | 0.52 | 0.30 | 0.49 | 0.63 | 10.00 | 0.53 |

Touch rates are from the side the session opened on. "Close same VWAP side as 10:00": the share of sessions whose close is on the same side of the session VWAP as the 10:00 price was.

## 6. Gaps

Gap = open ÷ the prior session's last close − 1, in units of the trailing 20-session daily standard deviation. Filled = the prior close trades during the session. Cross-name, sessions pooled.

| gap size (daily SDs) | period | sessions | fill rate | minutes to fill, median of names |
|---|---|---|---|---|
| 0-0.25 | 2017–22 | 21774 | 0.86 | 1.00 |
| 0-0.25 | 2023–26 | 14406 | 0.86 | 1.00 |
| 0.25-0.5 | 2017–22 | 15230 | 0.62 | 18.00 |
| 0.25-0.5 | 2023–26 | 9421 | 0.61 | 15.00 |
| 0.5-1 | 2017–22 | 12822 | 0.39 | 49.50 |
| 0.5-1 | 2023–26 | 8222 | 0.39 | 47.75 |
| 1-2 | 2017–22 | 4275 | 0.22 | 116.00 |
| 1-2 | 2023–26 | 2690 | 0.19 | 101.50 |
| 2+ | 2017–22 | 64 | 0.06 | 165.00 |
| 2+ | 2023–26 | 26 | 0.08 | 176.00 |


## 7. Calendar: the range on event days against all days

| period | cut | day range ÷ all days, median of names | 10:00 → close move ÷ all days | sessions per name |
|---|---|---|---|---|
| 2017–22 | CPI day | 1.01 | 0.94 | 66.00 |
| 2023–26 | CPI day | 1.04 | 0.93 | 44.00 |
| 2017–22 | FOMC day | 1.16 | 1.18 | 47.00 |
| 2023–26 | FOMC day | 1.12 | 1.29 | 30.00 |
| 2017–22 | NFP day | 1.01 | 1.04 | 66.00 |
| 2023–26 | NFP day | 1.12 | 1.11 | 42.00 |
| 2017–22 | all sessions | 1.00 | 1.00 | 1395.00 |
| 2023–26 | all sessions | 1.00 | 1.00 | 938.00 |
| 2017–22 | first session of month | 1.09 | 1.21 | 66.00 |
| 2023–26 | first session of month | 1.12 | 1.10 | 46.00 |
| 2017–22 | month end | 1.05 | 1.01 | 66.00 |
| 2023–26 | month end | 1.03 | 1.15 | 43.00 |
| 2017–22 | monthly opex (third Friday) | 0.97 | 0.95 | 65.00 |
| 2023–26 | monthly opex (third Friday) | 0.97 | 0.98 | 43.00 |
| 2017–22 | weekday Fri | 0.98 | 1.00 | 277.00 |
| 2023–26 | weekday Fri | 1.00 | 1.00 | 187.00 |
| 2017–22 | weekday Mon | 0.98 | 0.98 | 262.00 |
| 2023–26 | weekday Mon | 0.97 | 0.93 | 176.00 |
| 2017–22 | weekday Thu | 1.03 | 1.01 | 284.00 |
| 2023–26 | weekday Thu | 1.05 | 1.06 | 188.00 |
| 2017–22 | weekday Tue | 0.99 | 0.99 | 286.00 |
| 2023–26 | weekday Tue | 0.96 | 1.00 | 195.00 |
| 2017–22 | weekday Wed | 1.00 | 1.03 | 286.00 |
| 2023–26 | weekday Wed | 1.02 | 1.05 | 192.00 |

The event dates are the repository's FOMC, CPI and NFP file; "monthly opex" is the third Friday. Ratios of medians, not a test.

## 8. Direction (descriptive only)

| period | first 30 min vs last 30 min | 10:00–15:30 vs last 30 min | overnight vs intraday | intraday vs next intraday | share of up days | mean overnight, bp | mean intraday, bp |
|---|---|---|---|---|---|---|---|
| 2017–22 | -0.022 | +0.061 | +0.035 | -0.070 | +0.508 | +4.854 | +1.081 |
| 2023–26 | +0.009 | -0.006 | -0.060 | -0.061 | +0.516 | +6.822 | +4.448 |

Correlations are per name, then the median across names.

## 9. When in the day the movement happens

Median share of the day's total absolute one-minute movement in each half-hour (sums to about 1):

| half-hour from | 2017–22 | 2023–26 |
|---|---|---|
| 9:30 | 0.158 | 0.169 |
| 10:00 | 0.106 | 0.112 |
| 10:30 | 0.089 | 0.092 |
| 11:00 | 0.080 | 0.079 |
| 11:30 | 0.071 | 0.070 |
| 12:00 | 0.065 | 0.064 |
| 12:30 | 0.060 | 0.060 |
| 13:00 | 0.058 | 0.059 |
| 13:30 | 0.057 | 0.056 |
| 14:00 | 0.060 | 0.057 |
| 14:30 | 0.060 | 0.056 |
| 15:00 | 0.062 | 0.057 |
| 15:30 | 0.074 | 0.067 |

**Reading.** The U-shape: the first half hour carries the most movement, midday the least, the last half hour rises again. Same-day premium decays on the clock, while the movement it pays for is concentrated at the open and the close.

## 10. What this means for options (no rule is promoted from it)

- **Strike distance:** the end-of-day move and its 90th percentile (§2) set the distance; the excursion (§2) and the touch odds (§3) set how often a short strike is threatened along the way.
- **Stops on short options:** a touch rule exits about twice as often as the option would have finished in the money (§3). The repository's exit studies found no stop rule with a positive lower bound (lifecycle 05, 12).
- **Entry time:** the first half hour alone spans 56–60 % of the day's range, holds the day's high or low on 74–78 % of sessions and carries the most movement of any half hour (§4, §9). A 10:00 entry prices what is left: §2 gives its size.
- **Levels as support and resistance:** the prior day's high and low hold about half the time after a touch (§5): no reason to place strikes against them.
- **The forecastable part is size** (§1, §2). Whether a forecast beats the option's own price is V4 (A11), run on V3's single-name same-day straddles; the index version (the lifecycle's VOLC) failed.
- **Rule from the catalogue (`04_price_action_angles.md` §4):** no statistic here may choose a test run on the same sessions; a pattern this atlas suggests is tested on forward sessions only.
