# T-C methodology: 13:00 SPXW short straddle at measured NBBO (pre-registered, plan §5)

Pre-registration: `COMPASS_RESEARCH_PLAN.md` §5 T-C ("same design as T-A on SPXW ... pass criteria as T-A with 1.5 % half-spread"). The sample is the session list of the SPY straddle study (`research/short_vol_session/csv/t1_straddles.csv`, 2025-06-02..2026-10-09) minus early-close sessions (ThetaData calendar). No parameter was chosen after seeing results.

## Data (ThetaData PRO, cached as gzip CSV keyed by request; one login session per key)

* SPX 1-minute index values for each session (`index_history_price(symbol='SPX', interval='1m', date=d)`); the row at `HH:MM` is the value at `HH:MM:00`.
* SPXW strike list for the same-day expiration (`option_list_strikes(symbol='SPXW', expiration=d)`).
* 1-minute NBBO for the call and the put at the chosen strike, full session (`option_history_quote(symbol='SPXW', expiration=d, interval='1m', date=d, strike, right)`); the row at `HH:MM` is the NBBO at `HH:MM:00` (the 09:30 row carries zeros before the first quote). A strike that does not exist raises `NoDataFoundError`; the fetch log records every request.
* SPX official close for cash settlement from `index_history_eod` (SPXW is PM-settled to the official 16:00 SPX close, which differs slightly from the 16:00:00 tick; the analysis records which source was used per session).

## Trade definition

* Entry 13:00:00: ATM strike = SPX(13:00) rounded to the nearest 5 points, verified against the strike list (fallback: nearest existing strike, flagged). Sell one call and one put at the NBBO **bid** of the 13:00 row. Sessions where either leg has a zero bid or ask at 13:00 are skipped and listed.
* Exit: buy both legs back at the NBBO **ask** of the 15:55 row (main); variants at the 15:59 row and the 16:00 last quote; and hold to cash settlement (credit − |SPX close − K|, no exit spread, entry fees only).
* Fees $1.00 per contract per side ($4 per closed straddle, $2 for a settled one). Mid-to-mid P&L (no fees) reported for reference only.
* 2.0× credit stop: from the minute after entry to 15:54 the straddle is marked at the sum of the leg mids; the first minute at which the mark ≥ 2.0 × the executable credit triggers a buy-back at the **next** minute's asks; otherwise the 15:55 exit.
* Event exclusion: FOMC statement days, CPI and Employment Situation (NFP) release days from `event_days.csv` (sources: federalreserve.gov FOMC calendar; bls.gov 2025 and 2026 release schedules, cross-checked against the CPI archive, which confirms there was no October 2025 CPI release and that the September 2025 CPI was published 2025-10-24). The 2025-08-22 FOMC notation vote is not a meeting day and is not excluded.
* Random-time baseline: five draws of one entry minute per session, uniform on 09:35–14:30 (the window used by the SPY study's baseline), generated once from `numpy.random.default_rng(11)` and committed in `random_baseline_minutes.csv` before any quotes were fetched; ATM strike at that minute, same bid-entry / 15:55 ask-exit rules and fees. The 13:00 lane is compared to the per-date mean of the five draws with a date-paired bootstrap.
* Realized half-spread per leg = (ask − bid)/2 at the entry and exit rows, in points and as a share of the leg mid; straddle-level half-spread = sum of the leg half-spreads as a share of the straddle mid. Round-trip cost = (entry + exit straddle half-spreads) × 100 + $4.

## Statistics and gate

n, total, mean, 95 % interval by date-clustered bootstrap (5,000 draws, seed 7; one straddle per date for the main lane, five per date for the pooled baseline), win rate, profit factor, maximum drawdown of the cumulative P&L, five worst days, by month. Gate (plan §1 with the 1.5 % SPX-class half-spread): C1 executable lower bound > 0 over ≥ 150 straddle-days spanning ≥ 3 months; C2 realized entry half-spread ≤ 1.5 % of the credit; C3 the lane beats the random-entry baseline by more than one round-trip cost; C4 the edge survives executable (bid/ask) fills rather than mid.

## Reproduce

```
export TD_CACHE=$SP/theta/cache/index_tests CAL_FILE=$TD_CACHE/calendar_2017_2026.csv TC_OUT=$SP/theta/tc
set -a; . $SP/secrets/research.env; set +a        # THETADATA_KEY (never printed)
python3 -I ../code/fetch_all.py                     # fetches T-C sessions first, then the T-B monthly series
OUT_DIR=. python3 -I analyze_tc.py
```
Outputs: `tc_straddles.csv` (one row per session, every quote used), `tc_random_baseline.csv`, `tc_summary.csv`, `tc_paired_vs_random.csv`, `tc_spreads.csv`, `tc_by_month.csv`, `tc_gate.csv`, `tc_skipped.csv`, `RESULTS.md` (generated).

## Run notes (2026-10-13)

* 339 sessions; every session had an existing 5-point strike at the rounded 13:00 SPX level and a two-sided NBBO on both legs at 13:00; 2,034 contract-day quote files fetched (13:00 strike plus five baseline strikes per session, de-duplicated where strikes coincide). The committed baseline minutes are in `random_baseline_minutes.csv` (copied from `$SP/theta/tc/`).
* Settlement close from ThetaData EOD on 338 sessions (checked: SPX 2025-06-02 = 5935.94), the 16:00:00 tick on 2026-06-09 (EOD row missing).
* ThetaData permits one login per key; the pull ran in a single process shared with T-B and re-authenticated 48 times when other logins on the shared key invalidated the session; no request failed.
* Quote-row convention verified against the 1-second series: the 1-minute row stamped `HH:MM` is the state at `HH:MM:00`; the 09:30 option row carries zeros before the first quote.
