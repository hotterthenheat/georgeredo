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
