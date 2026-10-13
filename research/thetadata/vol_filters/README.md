# vol_filters: which intraday volatility / regime variables predict the SPX afternoon range?

Empirical study on locally cached ThetaData (SPX and VIX 1-minute index prints, SPX EOD, SPY EOD) from 2017-06-01 to 2026-10-09.
Question: which of (a) 09:30-10:30 and 09:30-13:00 realized range/variance, (b) VIX level at 09:31 / 13:00 and its change,
(c) prior-day range and 5-day realized vol, (d) FOMC/CPI/NFP/opex days, (e) day of week, month-end, holiday-adjacent days,
(f) overnight gap, (g) prior-day Unusual Whales gamma sign (2024-05-13+ only) predict the 13:00-16:00 absolute move and range,
and how skip rules built from them change a stylized short-premium payoff. Fit on 2017-2022, test on 2023-2026 (split fixed in advance).
Results note: `research_notes/High win rate 0DTE lanes/empirical_vol_filters_spx.md`.

## Data (local only; no ThetaData login, no network for market data)
* `$SP/theta/cache/index_tests/index_history_price__*__interval=1m__symbol=SPX.csv.gz` (monthly; `timestamp,price`; 09:30 print is empty, first print 09:31),
  same for VIX; `index_history_eod__*__symbol=SPX.csv.gz`; `stock_history_eod__*__symbol=SPY.csv.gz`; `calendar_2017_2026.csv` (full/early closes).
* Event days: `events.csv` (300 rows). FOMC decision days = last day of each scheduled meeting from federalreserve.gov
  (`fomccalendars.htm` for 2021-2027 and `fomchistorical2017..2020.htm`; parsed into `fomc_dates.csv`), plus the two unscheduled 2020 actions
  mapped to the session they hit (2020-03-03 statement at 10:00 ET; 2020-03-15 Sunday decision -> 2020-03-16).
  CPI and Employment Situation (NFP) release days for 2017-06..2025-05 from the BLS news-release archives
  (`bls.gov/bls/news-release/cpi.htm`, `.../empsit.htm`; the archive file names carry the release date), saved in
  `bls_cpi_release_dates.csv` and `bls_nfp_release_dates.csv`. Cross-checks: every CPI date is an ALFRED CPIAUCSL vintage date
  (`alfred_cpiaucsl_vintages.csv`; the 8 extra vintages are the annual seasonal-factor revisions and the Dec-2016 CPI), and every NFP date equals
  the BLS reference-week rule (third Friday after the week containing the 12th, Thursday when that Friday is July 3/4, next Friday when it is Jan 1-3).
  From 2025-06-01 the existing `research/thetadata/straddle_nbbo/event_days.csv` is used verbatim (it carries the 2025-26 shutdown delays).
* Opex = third Friday of each month (previous trading day if closed); quarterly opex = Mar/Jun/Sep/Dec.
* UW `stock/SPY/gex-levels` read only from the existing `$SP/bt/cache` files (no API calls); `neg_gamma_prev` = prior-day SPY close < prior-day gamma_flip, 2024-05-13 onward.

## Code
* `build_daily.py` -> `out/daily.csv`: one row per trading day (2,353 days). Ranges are (max-min)/reference price of 1-minute prints; RV = sqrt(sum of squared
  1-minute log returns). Afternoon = 13:00-16:00 prints; morning = 09:31-13:00; full day = 09:31-16:00. Gap = 09:31 print / prior EOD close - 1.
  Trailing baselines (20-day mean of the log target, strictly prior days) and the 60-day 80th percentile of VIX (strictly prior days) are computed here.
* `analyze.py` -> `out/*.csv` and `out/analyze.log`. Sample = trading days that are not early closes (2,333: 1,395 train, 938 test).
  1. Spearman IC of each predictor with |13:00->16:00 move|, 13:00-16:00 range, their ratio to the morning range, and the full-day range
     (`ic_spearman.csv`), with moving-block bootstrap CIs (block 20 days, 1000 resamples).
  2. OLS on log targets fit on train, R^2 on test vs. two benchmarks: train-mean constant and the trailing 20-day mean (`oos_r2.csv`, block-bootstrap CIs, 2000 resamples).
  3. Ratio of mean afternoon |move| / range on flagged days vs. clean days (`event_ratios.csv`; event flags compared against days with no FOMC/CPI/NFP/opex), bootstrap CIs.
  4. Stylized short-premium payoff: at 13:00 sell a straddle whose premium is k x (09:30-13:00 range); P&L per traded day = k - |pm move| / morning range
     (units of the morning range) and, in index %, k x range - |move|. k_fair = train mean of the ratio (so the trade-all payoff has zero mean in-sample), plus k = 1, 0.75, 0.5.
     Skip rules (`rules_single.csv`): events, VIX level (rolling 60-day 80th pct; train 80th pct), VIX change since the open (+10 %, +5 %, -10 %), morning range quantiles,
     morning range vs. prior-day range, morning efficiency, gap / prior-day range / 5-day RV train-80th-pct, day of week, month-end, holiday-adjacent.
     Mean outcome per trading day counts skipped days as 0. Rules are ranked on train (k_fair) and reported on test with paired block-bootstrap CIs of the
     difference vs. trade-all. All 465 OR-pairs in `rules_pairs_all.csv`; the top-15 train pairs with test CIs in `rules_pairs_top.csv`; `by_year.csv`; `quintiles.csv`.
* `robustness.py` -> `out/rules_alt_scale.csv`, `out/robustness.log`: log-log elasticity of the afternoon on the morning range, every rule re-run under an alternative
  scale (trailing 20-day geometric mean of the afternoon range), Wednesday ex-FOMC, half-size instead of skip, and k-robustness of the key rules.
* `posthoc.py` -> `out/posthoc.log`: checks run after the train-selected results were seen (FOMC-or-month-end pair on both scales, FOMC-day statistics); flagged as post-hoc in the note.
* Seeds: numpy default_rng(20251013). Run: `SP=<scratchpad> python3 build_daily.py && python3 analyze.py && python3 robustness.py && python3 posthoc.py`.

## Caveats
* The "morning-implied scale" is the realized 09:30-13:00 range, not an option-implied move (no implied data in this cache); the stylized payoff is a selection test, not a P&L forecast.
* SPX 1-minute prints are index values, not OHLC, so intra-minute extremes are missed (consistent across all series).
* Days with early closes (20) are excluded; 2 days lack a prior close (first day, holiday boundary) and 4 days lack a 09:31 VIX print.
