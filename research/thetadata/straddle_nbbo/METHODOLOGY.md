# Methodology: 0DTE short ATM straddle re-test on measured NBBO (ThetaData)

## Purpose
Re-price the candidate lane of `research/short_vol_session` (H9 / pre-registered test T-A in `COMPASS_RESEARCH_PLAN.md`) with measured bid/ask quotes
instead of the modelled half-spread (1 % SPY/QQQ, 2 % IWM of premium, floor $0.01, plus $0.70 per contract per side), and judge it against the §1 promotion gate.
Negative results are reported as found; nothing was tuned on the measured data.

## Like-for-like inputs (no re-selection)
* Sessions, tickers, entry times and ATM strikes are taken from `research/short_vol_session/csv/t1_straddles.csv` (variant `short_hold`): 339 sessions 2025-06-02 → 2026-10-09,
  SPY / QQQ / IWM, entry times 09:35, 10:00, 11:00, 13:00, 14:30, strike = the one the modelled study used (round(underlying) at the entry minute from Unusual Whales bars).
  That file holds 20 byte-identical duplicate rows (same date × ticker × time); they are de-duplicated here, so n = 339 per ticker × entry time (the modelled study's 341/339/341 become 339/339/339).
* The modelled study's own per-row numbers (`uw_pnl_mid`, `uw_pnl_spread`, `uw_pnl_adverse`, `uw_credit`) are carried along for a row-by-row comparison.

## Data
* ThetaData, PRO key, official `thetadata` 1.0.14 Python client (gRPC). `option_history_quote(symbol, expiration=date, interval='1m', date, strike, right='both', 09:30:00–16:00:00)`
  → 391 rows per right per contract-day (NBBO: bid, ask, bid_size, ask_size, exchange and condition codes). `stock_history_ohlc(symbol, '1m', date)` for the random-time baseline strike.
* Cache: one gzip CSV per (symbol, expiration, strike, right='both', date, interval) under the session scratchpad (`theta/cache/straddle/`), never refetched; `NoDataFoundError` recorded as a `.nodata` marker (none occurred).
* Fetch discipline: one login per process (every `ThetaClient()` is a new terminal session and invalidates the previous one), 2 worker threads sharing it, exponential back-off on
  gRPC RESOURCE_EXHAUSTED / UNAVAILABLE, re-login on UNAUTHENTICATED (other studies share the key). The key is read from the environment only; exception text is redacted before logging.

## What a 1-minute quote row represents (verified, `verify_interval.py` → `verify_interval.json`)
For four contract-minutes (SPY 2026-03-02 C682 13:00, SPY 2025-09-29 P663 13:00, QQQ 2026-05-27 C728 15:55, IWM 2025-09-29 P241 14:30) the 1-minute row stamped T is identical
(bid, ask, bid_size, ask_size) to the 1-second row stamped T, and differs from the last 1-second row of the minute [T, T+59 s] in 3 of 4 cases. In the QQQ case the row at T also differs
from the row at T−1 s, i.e. a quote update inside the second ending at T is already reflected. So **a 1-minute row stamped T is the NBBO in force at the minute boundary T:00 (the last
quote update at or before T), not an average and not the last quote of the following minute.** The 09:30:00 row is a placeholder (NaN / zero) because no quote has been posted yet.
For stock OHLC the 1-minute row stamped T is the bar covering [T, T+1 min) (open/high/low/close/volume match the 1-second rows 13:00:00–13:00:59 exactly), so the price "known at T"
is the close of the row stamped T−1.

## Fills and P&L (per 1-lot straddle, $)
* Entry at minute T: sell the call and the put at their **bid** in the row stamped T (`credit_bid`). Mid credit (`credit_mid`) = sum of (bid+ask)/2 at the same row. A straddle is skipped
  if either leg has no quote row at T or a zero bid (none were skipped at 13:00).
* Exit: buy both legs back at their **ask** in the row stamped 15:55 (primary), 15:59 or 16:00 (variants; the 16:00 row is the last quote of the session).
* Fees: $0.70 per contract per side, 4 sides = $2.80 per straddle round trip. `pnl_exec = (credit_bid − debit_ask) × 100 − 2.80`. `pnl_mid = (credit_mid − debit_mid) × 100` (no fees, the
  same convention as the modelled study's `mid`). `pnl_model_theta` applies the modelled cost rule to the ThetaData mids (isolates the cost-model error from the data-source difference).
* Stops (variants): combined quote mid ≥ 2.0× (or 1.5×) `credit_mid`, checked each minute from T+1 to 15:54, filled at the ask of the next minute (never later than 15:55).
* Realized half-spread per leg = (ask − bid)/2 at the fill row, in $ and as % of that leg's mid; straddle-level: entry-side (call+put half-spreads) / `credit_mid`, exit-side likewise
  (relative to the entry credit), round trip = their sum. These are what the modelled 1 %/2 % of premium stood in for.
* Missing minutes: ThetaData returns a row for every minute; rows with NaN, ask ≤ 0 or ask < bid are forward-filled from the last usable minute and flagged (`exit_raw` = 1 when the exit row was a real row).
* Event-day filter variant: FOMC decision days, CPI release days and Employment Situation (NFP) release days from `event_days.csv` (Federal Reserve FOMC calendar page; BLS news-release
  archives, release dates taken from the archive file names; the 2025 appropriations lapse shifted the Sep-2025 CPI to 2025-10-24 and the Sep-2025 jobs report to 2025-11-20 and cancelled the
  October 2025 releases). The 2025-08-22 FOMC notation vote is not treated as a decision day.

## Statistics
* Per ticker × entry time and pooled SPY+QQQ (the T-A lane) and SPY+QQQ+IWM (the modelled headline) at 13:00: n, total, mean, 95 % bootstrap CI of the mean over **date clusters**
  (5,000 draws, seed 7; the same bootstrap code as the modelled study), win rate, profit factor, maximum drawdown of the chronological cumulative P&L, worst 5 dates, and the per-straddle
  mid-vs-executable gap.
* Random-time baseline (seed 11): one straddle per ticker-date at a minute drawn uniformly from [09:31, 15:54], ATM strike = round(close of the ThetaData stock bar ending at that minute),
  same fills, close 15:55. Lane-minus-baseline is paired by ticker-date with a date-clustered bootstrap CI; "one round-trip cost" = the lane's mean mid-minus-executable gap.
* Gate (COMPASS §1, T-A): lower CI > 0 under executable fills; realized half-spread ≤ 1.5 % of credit (entry side; the round trip is also shown); n ≥ 150 and ≥ 3 months; beats the random
  baseline by more than one round-trip cost.

## Caveats
* The fill is the NBBO at the minute boundary; a real order arrives at some second inside the minute, when the quote can differ (the 1-second windows above show bid/ask ranges of several cents
  within a minute). No slippage beyond the NBBO is charged and no queue or latency effect is modelled; the fill is assumed at the full displayed size (median displayed bid size at 13:00 is tens of
  contracts per leg, so a 1-lot is covered, but larger size is not tested).
* Exit legs are often near-worthless at 15:55, where the quote is $0.01 wide and the ask is one tick above a bid of $0.00–$0.01; buying those back costs the full ask. Letting them expire is not modelled (pin risk).
* Single regime (16 months); two tail dates dominate the lane's income (see RESULTS.md); no margin, sizing or assignment modelling.
* ThetaData 1-minute NBBO is consolidated (OPRA) and the exchange code of the best quote is recorded; it was not cross-checked against a second quote source.

## Run record (2026-10-13)
* Fetch: 7 phases (13:00 first, then stock bars, random baseline, 09:35, 10:00, 11:00, 14:30), 4,682 contract-days / stock-days fetched + 3,454 cache hits (strikes repeat across entry times),
  0 errors, 0 no-data, 2 gRPC retries, 111 re-logins forced by other studies' logins on the shared key (every job completed). Wall time about 30 minutes at 2 concurrent requests.
* Coverage: 5,084 fixed-time straddles (339 sessions × 3 tickers × 5 entry times, minus one 09:35 IWM straddle with no quote row at the entry minute) and 1,017 random-time baseline straddles;
  the 15:55 exit row is a real quote row (not forward-filled) for 99.9 % of straddles.
* Outputs: `csv/straddles_nbbo.csv.gz` (one row per straddle, 59 columns: quotes and sizes at entry and exit, half-spreads, P&L under every variant, the modelled study's numbers for the same row),
  `csv/stats_lanes.csv`, `csv/half_spread_distribution.csv`, `RESULTS.md`, `verify_interval.json`.
* Reading the half-spread tables: a leg quoted 0.00 × 0.02 at the exit has mid $0.01 and half-spread $0.01, i.e. "100 % of mid"; the $ columns and the %-of-credit columns are the economically
  meaningful ones for the exit side.
* Reproduce: `set -a; . <env file with THETADATA_KEY>; set +a; python3 -I fetch.py 13:00 stock random 09:35 10:00 11:00 14:30` (fills the cache), then `python3 -I analyze.py` (no key needed).
