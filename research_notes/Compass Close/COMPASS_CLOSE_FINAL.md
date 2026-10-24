# Compass Close — final write-up (2026-10-24)

**The study is closed. The gate failed, so the rule was never tested for profit on the new data.**

The idea: at 15:55 New York, buy the same-day SPXW call and put at the strike nearest the S&P 500 and hold both to the
4:00 pm cash settlement. That pays if the last five minutes, plus the settlement, move the index further than the two
options cost. The owner's gate asked one question before any P&L: is the move the straddle pays worth at least 1.05
times what the straddle costs at its asks, clearly above 1, every year and every expiry weekday?

## What we found, in plain English

1. **The straddle is expensive, not cheap.** On the 165 gate-sample trades (2017–2022, odd months), the straddle cost
   4.87 index points at its asks on average and paid back 3.31. The ratio is **0.68**, and the interval (0.63 to 0.79)
   is nowhere near 1. A buyer paid about $1.47 for every $1.00 the closing move delivered, before any fee.
2. **It is the same every year and every weekday.** The ratio is below 1 in all six years (the best, 2019, is 0.98) and
   on Mondays (0.73), Wednesdays (0.65) and Fridays (0.70). The gate needed four years of six; it got none.
3. **Going one strike further out is worse.** The one-strike-OTM strangle paid back 0.34 of its cost (59 sessions where
   both legs had usable quotes). So there is no cheapness to explain, at the money or away from it.
4. **The recent years, already read, agree.** On 2022-05-13 → 2026-10-09 (1,093 trades, PREVIOUSLY READ, not judged)
   the ratio is 0.86 (0.82 to 0.92), and the rule as written lost **12.8% a trade** (interval −16.7% to −8.4%), about
   $71 a trade and $77,318 in all, winning 37% of the time. The only row above 1 there is month-end (1.02 on 50
   sessions); the new data hold no month-end session, so it could not be tested and is not a finding.
5. **Quotes were wide before 2022.** 71 of the 236 gate sessions had a leg wider than half its mid, so no trade was
   taken; only 2 sessions had both legs inside 10% of mid. In 2022–2026 nearly every session traded.
6. **What did not run.** By the stop rule: the P&L test on the even-month sample, the MDE, the reported books (call
   only, put only, the move's side, the narrower leg, 15:50, 15:58, the 15:56 ask, no exit fee, the strangle, FOMC/CPI/NFP
   days, Robinhood's fees), the deflated Sharpe ratios and the forward test. The P&L test could not have passed anyway:
   the even months hold 234 sessions, fewer than the owner's 300-trade floor. This was stated in the prereg before
   anything was computed.

## How it was run

- **Prereg** committed alone before any fetch or figure (`PREREG_COMPASS_CLOSE.md`, 1ce2039), with the
  HOLDOUT_LEDGER row (holdout A read again: A ≥ 142 rules, B ≥ 15,975 with this study's 9).
- **The owner's open decisions, as defaults:** the Lifecycle daily tier's end-of-day marks are not reads (469 of the 470
  new sessions are its entry days and 446 its expiry days; with them excluded only 1 or 13 gate sessions remain, both
  printed, neither carrying weight); holdout A is read again; the 63 Jan–May 2017 sessions with no SPX minute print are
  dropped and listed.
- **Data:** 470 new sessions, 2017-06-02 → 2022-05-12 (every same-day PM SPXW session not read by V8, S03 or S16b, half
  days out). Gate = odd months (236), P&L = even months (234, never read). SET = Cboe's official SPX close; S = the SPX
  minute print; quotes = the 1-minute NBBO stamped 15:55.
- **Fetch** (c950d8a): 470 of 470 sessions from ThetaData's SDK, 15:45–16:00, every answer same-day PM SPXW, 0 empty or
  denied. Two logins rather than one: the first stopped on a script bug after one request (disclosed in `FETCH_LOG.md`).
- **Gate** (1857af3): run once.

## The tables

### Gate (G1 and G2), gate sample — judged

| figure | value | needed | result |
|---|---|---|---|
| R_ask = mean\|SET − K\| / mean STR_ask | **0.681** [0.629, 0.789] | ≥ 1.05 and lower bound > 1.00 | **FAIL** |
| R_mid | 0.758 [0.699, 0.882] | — | — |
| mean / median of per-session ratios | 0.698 / 0.638 | — | — |
| sessions where the move beat the straddle | 28.5% | — | — |
| years with R_ask > 1.00 | **0 of 6** (2017 0.505, 2018 0.709, 2019 0.978, 2020 0.647, 2021 0.733, 2022 0.506) | ≥ 4 | **FAIL** |
| Mon / Wed / Fri (end of month: no session) | 0.730 / 0.649 / 0.695 | each > 1.00 | **FAIL** |
| control: one-strike-OTM strangle | 0.339 (59 sessions) | descriptive | neither is cheap |
| trades / sessions | 165 / 236 (70 too wide, 1 zero bid) | — | — |
| both legs within 10% of mid | 2 sessions | reported | — |
| \|SET − S(16:00)\| > 0.5, flagged and kept | 38 sessions | reported | — |

Intervals: 20-session moving blocks, 2,000 draws, the house seed (audit_lib), the ratio recomputed on each draw.

### Previously read, 2022-05-13 → 2026-10-09 — not judged

| figure | value |
|---|---|
| trades / sessions | 1,093 / 1,097 |
| R_ask / R_mid | 0.865 [0.818, 0.920] / 0.913 [0.865, 0.969] |
| R_ask by year | 2022 0.879 · 2023 0.904 · 2024 0.861 · 2025 0.800 · 2026 0.919 |
| R_ask by expiry row | Mon 0.943 · Wed 0.861 · Fri 0.734 · month-end 1.024 (50) · Tue/Thu 0.872 |
| strangle control | 0.686 [0.579, 0.804] |
| primary rule, $1.28 a contract a side in and out | −12.8% a trade [−16.7%, −8.4%]; −$70.74 a trade; −$77,318 total; 37.0% won; median −$115.12 |

No cumulative chart: the P&L test did not run.

## Integrity

| check | result |
|---|---|
| plain-loop re-derivation (pyarrow and csv, no shared code): K, each leg's 15:55 bid and ask, STR_ask, STR_mid, SET, P&L | 60 sessions (50 gate, 10 previously read), 532 fields, **0 differences** |
| lookahead: inputs stamped after 15:55 blanked, SET kept | **10 of 10 unchanged** |
| lookahead control: the 15:56 quote read instead | entry or trade changed in **9 of 10** (the tenth has no trade either way) |
| units | asserted at every boundary (points per share, $1.28 a contract a side, P&L = 100 × points − fees) |
| fetch | 470 of 470 same-day PM SPXW, 16 stamps each, kept strikes bracket every 15:45–16:00 print |

## Files and commits

`research_notes/Compass Close/`: `PREREG_COMPASS_CLOSE.md` and `sessions_new.csv`, `sessions_dropped_jan_may_2017.csv`
(1ce2039); `fetch_close.py`, `FETCH_LOG.md`, `close_lib.py`, `gate.py` (c950d8a); `GATE_REPORT.md`, `verify_plain.py`,
`lookahead.py`, `out/` (1857af3); this write-up and its PDF, `render_final.py`. The raw quotes (5.8 MB) stay in the
scratchpad under `theta/data_full/chains_close/SPXW/`.

**Stop rule applied: the gate failed, the study is closed. No forward tracking.**
