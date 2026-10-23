# H3 — earnings implied-volatility crush, a short iron condor across the report: the run

**Pre-registration: `PREREG_H3.md`, commit `001a136`, sha256 `7ea327e9e02680aba81fc9e386cbb1c5b19af696f7024e58cb9aaf2d75c15861`** (committed alone and pushed before anything was computed). Code in this folder: `h3common.py`, `fetch_h3.py`, `build_h3.py`, `verify_h3.py`, `attribution_h3.py` (exploratory, after the screen), `write_report.py`; outputs in `out/`.

## Summary

- **Exploration screen (1,601 X names, events with P and R in 2019-04-01 → 2022-12-30): mean -161.54 $ a condor after costs, block-20 95 % [-180.68, -142.46]**, 2,209 trades exiting on 554 of 940 sessions → **FAIL**.
- As % of max risk: mean -30.24 % [-32.32, -27.79]; win rate 30.3 %; median -44.81 $; worst -6,539.81 $; p1 -2,275.01 $, p5 -891.21 $; mean credit $239.94, mean max risk $560.72.
- **Holdout: not fetched and not read** (the screen did not pass). The 1,600 H names stay unopened for 2019-01 → 2022-12.
- Verifier: 50 exploration trades re-derived from the raw files by a plain loop, 1,150 fields, **0 differences**.
- Ledger: H3 is the 2nd hypothesis tested in `LEDGER.md` (5 earlier programme failures before it). No pass, so no Bonferroni question arises.

## 1. The fetch

- expl: 10,734 requests (empty 44, stored 10,690), fetch time 1.65 h, 67.5 MB stored, 5,244,878 rows; stop: none — every event and tier walked.
- hold: not fetched.

## 2a. Events at each stage (exploration)

| stage | events |
|---|---|
| outside the window | 23,678 |
| under the $50 M floor | 15,230 |
| no expiry after R within 14 days | 2,340 |
| formed | 2,209 |
| no bar for P | 1,806 |
| under 50 of 60 days of bars | 454 |
| untradable leg at entry | 345 |
| no credit | 146 |
| P or R is a half day | 48 |
| entry chain empty | 41 |
| no standing ATM pair | 23 |
| strike grid too coarse for the wings | 22 |
| bars and options disagree (parity > 5 %) | 2 |

Formed trades by how the exit was valued: quotes 2,208, split-sized move: booked at max loss 1; exit file with no rows 0; fallback legs 0 on 0 trades; iron-fly-shaped 162.

## 3. The exploration screen

- Mean $ a condor -161.54; block-20 95 % [-180.68, -142.46]; block 1 [-182.85, -141.09], block 5 [-182.05, -142.03]; effective N (block) 370, (acf) 411 of 940 sessions.
- Bonferroni-level intervals of the same draws (descriptive here): m = 2 [-182.74, -140.13], m = 7 [-185.58, -136.95].
- Context (descriptive): median credit 0.325 IM; median exit cost 0.433 IM; median realized move |close(R)/close(P) − 1| 0.631 IM; moves beyond the short strikes (> 0.5 IM) 58.6 %.

| cut | trades | mean $ | block-20 95 % | mean % of max risk | win rate |
|---|---|---|---|---|---|
| year=2019 | 403 | -99.06 | [-122.14, -70.54] | -28.00 % | 35.0 % |
| year=2020 | 504 | -166.49 | [-209.71, -125.07] | -32.37 % | 26.0 % |
| year=2021 | 649 | -192.07 | [-227.26, -154.82] | -32.72 % | 30.0 % |
| year=2022 | 653 | -165.94 | [-200.63, -133.42] | -27.50 % | 30.9 % |
| tier=2 | 7 | +0.64 | [-96.70, +99.02] | +3.83 % | 57.1 % |
| tier=3 | 2,200 | -162.18 | [-181.43, -142.92] | -30.37 % | 30.2 % |
| tier=U | 2 | -26.97 | [-54.81, +0.88] | -2.29 % | 50.0 % |
| report_time=postmarket | 987 | -172.91 | [-204.24, -141.00] | -28.44 % | 31.4 % |
| report_time=premarket | 1,222 | -152.35 | [-174.34, -133.11] | -31.69 % | 29.4 % |
| fly=False | 2,047 | -165.98 | [-186.61, -145.93] | -27.94 % | 31.6 % |
| fly=True | 162 | -105.44 | [-137.38, -73.17] | -59.26 % | 13.6 % |

## 5. Reading (no holdout)

- **The screen fails by a wide margin**: the condor lost about $162 a trade, 30 % of its maximum risk, with the interval far
  below zero in every year 2019–2022, for premarket and postmarket reports alike, and for the iron-fly-shaped trades too. Only
  7 trades fell in Tier 2 and none in Tier 1 (on the two sampled sessions per name-month); the set is the Tier 3 single names
  that clear a $50 M stock floor and list a weekly expiry, which is where V2a found the widest spreads.
- **Where the loss comes from (exploratory, `attribution_h3.py`, written after the screen was read; no verdict, no rule
  changed)**: on the 2,208 quote-valued trades, the same four legs valued at their mids at P and at R, no fees, lose
  **$20.17 a trade** (median −$20.75, 38.8 % positive): this structure does not collect the crush even before costs, because
  the median report moved 0.63 of the implied move and 58.6 % moved past the short strikes at 0.5 IM. The other
  **$141.36 a trade** is the spread crossed eight times and the fees ($5.50 at most). The entry credit at the bid/ask was a
  median 0.32 IM; the exit cost a median 0.43 IM.
- Consistent with V2a (2023-11 → 2026-09: the short straddle across the report lost a quarter to a third of its premium):
  single-name earnings options in this universe are not overpriced by enough to pay the round trip of spreads, and the
  defined-risk condor, with its shorts inside the typical realized move, gives up the mid-price gain the straddle had at the
  money. The FAIL says no premium large enough to pay eight spread crossings showed up; it does not say no earnings variance
  premium exists at the mid in other structures or more liquid names (which this set barely holds).

## 6. Checks

- `verify_h3.py`: 50 exploration trades (seed 20261028), every field (R, P, close(P), close(R), the expiry, K0, IM, F, the
  four strikes, the four entry quotes, the credit, W, the four exit prices, $) re-derived by plain Python loops from the raw
  parquet rows: **0 differences in 1,150 fields**. All 50 were quote-valued; the one split-booked trade (a split-sized
  close(R)/close(P) ratio, booked at max loss as the prereg says) is not among them.
- No exit fallback was needed: every formed trade had all four legs quoted at R (0 fallback legs, 0 empty exit files).
- The fetch walked every exploration event: no budget cut, so the exploration set is the whole of the 1,601 X names' timed
  reports with P and R in 2019-04-01 → 2022-12-30 (22,618 in the window; 46,344 in the list, the rest after 2022).

## 7. Deviations

- **No rule, threshold, window, structure or set was changed after a number was read.** The screen was computed once, after
  the fetch had walked every event, and it failed; the holdout was not fetched and not read.
- The first fetch run was started attached to the session and stopped after about a minute (117 events walked, 25 requests)
  so that it could run detached; it was restarted at once. Before the restart the budget's accounting was changed to sum the
  request log (so a stopped run loses no fetch time); no rule changed. Two logins in all, at 20:57 and 20:58 New York, both
  outside the quiet windows; the fetch ended at 22:38 New York.
- Before the fetch ended, the builder and the verifier were dry-run on the events walked so far, writing to a scratch folder
  that was deleted unread: only "the builder ran" and the verifier's count (40 checked, 0 differences) were seen — no mean,
  no P&L. The verifier's file reads were switched from pyarrow (not installed) to polars before that dry run.
- `attribution_h3.py` (the mid-price split above) is exploratory, written after the screen; it changes nothing.
- The prereg's estimate of about 5,000 events was the floor's pass rate; 2,209 trades formed — the 14-day expiry rule
  (2,340 events with no weekly after R) and missing stock bars at P (1,806) took more than expected. Not a rule change.
- The tier pass reused 980 tier files from the PEAD store (read only) and 41 P files; nothing was written there.

## Commands

```
PYTHONDONTWRITEBYTECODE=1 python3 -I -B fetch_h3.py expl     # through $SPN/h3/run_fetch.sh (restarts after the ThetaData quiet windows)
PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=4 python3 -I -B build_h3.py expl
PYTHONDONTWRITEBYTECODE=1 python3 -I -B verify_h3.py expl 50
# only after a screen pass: fetch_h3.py hold; build_h3.py hold; verify_h3.py hold 50
PYTHONDONTWRITEBYTECODE=1 python3 -I -B write_report.py
```
