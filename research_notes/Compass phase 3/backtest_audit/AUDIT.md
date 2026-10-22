# Audit of the paper tracker's historical replay, 2022-11-11 → 2026-10-09

Written 2026-10-22 00:40 UTC by `run_audit.py` in this folder (93 s). It reads the replay's rows (`data_recorder/paper_backtest`, `source = backtest-parquet`), the stored minute Parquet (`PAPER_PARQUET_ROOT`), Theta's EOD daily bars (`data_lake/thetadata/stock_eod`), UW's daily bars (`data_lake/unusualwhales/ohlc__1d.part0*.parquet`, the `r` rows) and `data/macro_events_2022_2027.json`. Nothing is fetched and the replay's code and rows are not touched. The corrected cumulative report is `cumulative_through_2026-10-21.md`; the tables behind both are in `out/`.

## Summary

- **Deterministic, no double counting.** A fresh replay into an empty root reproduced the committed report CSV byte for byte (SHA-256 `5f40388affcb5efc…`) and all 3884 of 3884 row files with identical sorted contents. 971 sessions replayed = the 971 full NYSE sessions expected; no key twice; every tradable capture has exactly one settle row. 100 trades re-derived from the raw chain by separate code: 0 differences.
- **The settlement was the 15:59 bar, not the official close.** Re-settled on the official close (Theta EOD; equal to UW's daily close on every one of the 494 name-sessions where both exist), 12338 of 20469 trades change; condor_em1 totals +17,668 → +16,680, condor_d20 +26,797 → +25,424, fly5 iron +62,083 → +63,218. The largest gap is SPY on 2025-04-09: official 548.62 against a 15:59 bar of 543.37.
- **Per period, on the official close** (mean $ a trade, 20-session block-bootstrap interval): condor_em1 (i) +3.47 [-0.04, +6.68] through zero; condor_em1 (ii) +4.10 [-0.51, +8.15] through zero; fly5 iron (i) +16.59 [+12.41, +23.06] clear of zero; fly5 call (i) +9.60 [+5.29, +16.25] clear of zero; fly5 put (i) +7.43 [+3.01, +14.31] clear of zero; fly5 iron (ii) +16.20 [+10.26, +22.36] clear of zero; fly5 call (ii) +7.13 [+0.77, +13.53] clear of zero; fly5 put (ii) +5.58 [-1.04, +12.00] through zero; condor_d20 (i-a) +2.42 [-0.77, +4.99] through zero; condor_d20 (i-b) +8.71 [+3.68, +15.89] clear of zero; condor_d20 (ii) +7.67 [+3.87, +10.89] clear of zero.
- **The report's intervals** are percentile bootstraps over iid SESSIONS (2,000 draws, seed 20261016, the trade-weighted mean); they keep a session's trades together but assume no dependence between sessions, pool every period, and treat fly5's three structures (one trade seen three ways) as three results. Re-derived here to the last digit, then replaced by session-sum and moving-block intervals per period.
- **No untouched forward period exists on the stored data for any candidate.** Every historical session lies in a period the candidate was developed or chosen on (section 5). The forward period starts 2026-10-12 and is empty until the fetch.
- **D1 is a session filter, not a minute filter, and its pooled lift mixes in-sample rows.** The replay's +$9.06 pools the model's own training sessions (scored in-sample). Out of the model's training (2025+) the time-matched lift is positive and clear of zero under a 20-session block bootstrap, but the same-session comparison (D1 minutes against the same day's other minutes) is inside the noise and the lift falls by about 30 % without scheduled-event sessions — and the candidate was set after that span was read (section 6).
- **Hold-to-expiration is not operationally clean.** A condor finishes with a short leg in the money on about a quarter of trades and an ETF fly on essentially every trade, leaving 100 shares (≈ $44–64K a lot) per fly against $370–410 of modeled risk; the 15:58 close-out that avoids it turns every candidate's mean negative under the tracker's exit rule, and closing only the legs near the money gives back most or all of the hold's mean (section 8).

## 1. Reproducibility and integrity

**The re-run.** The command (four shared cores, the other agent's fetch work running beside it):

```
PAPER_PARQUET_ROOT=<the stored Parquet> POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 nice -n 10 \
  python3 -I scripts/paper_tracker.py --backtest --start 2022-11-11 --end 2026-10-09 \
  --candidates condor_em1,fly5,condor_d20 --backtest-data <a fresh empty dir> --out <dir>
```

It took 840 s from a cold root (no marker, no bar or VIX cache). The scripts as they were when it started (the other agent edits the fetch code; Python had loaded these before any edit):

- `03291ba2ff550c111eee1a6c75004770fa73d2948694e8aeefbfa0b4d73f43cc  scripts/paper_backtest.py`
- `8320e466e21a72d6b5367d083134197af79fbba6171318f7b78dae173c0e8585  scripts/paper_tracker.py`
- `4c064010d387a35206229876b48217de1330af3fc81a2c0136d729af6884de33  scripts/vol_model.py`
- `77640ef0525c727746d989a42442d738443673df64e3f1e6b9ffe7c7c02699de  scripts/eod_recorder.py`
- `05293b2a56458f9bc5a618b99604ec6d18d2431a437b23a90739ba4cc5b77917  scripts/macro_calendar.py`

| check | result |
|---|---|
| report CSV, byte for byte (committed vs re-run) | identical — 71296 bytes, SHA-256 `5f40388affcb5efc0fb4e52859f461bbe7fd14a3a2fa148360981594b88699da` |
| row files (candidate/name/day) | 3884 committed, 3884 re-run, 0 / 0 only on one side |
| row files with identical sorted contents (every column) | 3884 of 3884; 0 differ |

Why it is deterministic: the replay reads files only; the clock is set to each event's minute, so every timestamp column (`captured_at`, `_fetched_at`, `settled_at`) is the replayed minute, not the wall clock; there is no random draw in the replay; the bootstrap draws in the report are seeded (numpy `default_rng(20261016)`). The committed root was written by several runs (its `_replay/days_*.json`: 2022-11-11 → 2024-10-31, 2024-11-01 → 2026-10-09, 2025-01-02 → 2026-10-09, 2026-10-05 → 09 and the whole span, each skipping minutes already marked) — and still equals the one cold run, so the markers neither dropped nor repeated a minute.

**Sessions.**

| count | value |
|---|---|
| weekdays 2022-11-11 → 2026-10-09 | 1021 |
| NYSE holidays on weekdays (the calendar written out in audit_lib.py) | 41 |
| NYSE half days (skipped, as the research skipped them) | 9 |
| full sessions expected | 971 |
| Theta EOD sessions for SPY in the span / less the half days | 980 / 971 (calendar mismatches: {'eod_not_calendar': [], 'calendar_not_eod': []}) |
| replayed (the replay's `_replay/days_*.json`) | 971 |
| skipped as holiday / half day by the replay | 41 / 9 — the same dates as the calendar |
| expected but not replayed / replayed but not expected | 0 / 0 |
| days with a candidate's file missing | 0 |

Excluded days, every one, with the reason: holidays 2022-11-24, 2022-12-26, 2023-01-02, 2023-01-16, 2023-02-20, 2023-04-07, 2023-05-29, 2023-06-19, 2023-07-04, 2023-09-04, 2023-11-23, 2023-12-25, 2024-01-01, 2024-01-15, 2024-02-19, 2024-03-29, 2024-05-27, 2024-06-19, 2024-07-04, 2024-09-02, 2024-11-28, 2024-12-25, 2025-01-01, 2025-01-09, 2025-01-20, 2025-02-17, 2025-04-18, 2025-05-26, 2025-06-19, 2025-07-04, 2025-09-01, 2025-11-27, 2025-12-25, 2026-01-01, 2026-01-19, 2026-02-16, 2026-04-03, 2026-05-25, 2026-06-19, 2026-07-03, 2026-09-07; half days 2022-11-25, 2023-07-03, 2023-11-24, 2024-07-03, 2024-11-29, 2024-12-24, 2025-07-03, 2025-11-28, 2025-12-24.

**Rows and trades.**

| check | result |
|---|---|
| rows read (capture, close1558, settle) | 54065 in 3884 files: condor_d20/capture 4855, condor_d20/settle 4791, condor_em1/capture 4855, condor_em1/settle 4796, fly5/capture 11652, fly5/close1558 11558, fly5/settle 11558 |
| a key twice (candidate, name, day, minute, structure, row kind, settle source) | 0 |
| captures / tradable | 21362 / 20469 |
| tradable captures by number of settle rows | {1: 20469} |
| captures with no settle row (all untradable, no legs to settle) | 217 (legless captures 217, of them tradable 0) |
| settle rows without a capture | 0 |
| settle sources | {'official': 21145} |
| fly5 tradable captures by number of 15:58 rows | {1: 11558} |
| 15:58 rows with a value / without (a leg unquoted at 15:58) | 11545 / 13 |
| macro stamps on the rows against the events file | 0 disagreements |
| condor_em1: sessions with captures, name-sessions short of minutes, settled trades, sessions with a settled trade | 971, 0, 4426, 964 |
| fly5: sessions with captures, name-sessions short of minutes, settled trades, sessions with a settled trade | 971, 0, 11558, 971 |
| condor_d20: sessions with captures, name-sessions short of minutes, settled trades, sessions with a settled trade | 971, 0, 4485, 968 |

One data note found on the way: 66 fly5 trades (22 a structure, QQQ, 14 sessions from 2023-12-27 to 2024-09-30) use strikes ending in .78 (390.78 … 489.78) — adjusted series after a distribution, which the stored chain lists under the plain QQQ root, so the "strike nearest spot" rule can pick one. Their deliverable is not verified here; live, UW writes an adjusted series under its own OCC root (QQQ1 …), which the tracker's `Chain` (root filter off for SPY and QQQ) would also accept. Kept in every figure; their mean is negative.

## 2. Settlement and entry reconciliation

The replay settles SPY and QQQ on **the 15:59 bar's close** (`ParquetSource.last_regular_close`, labelled `close_official_from = replay: the 15:59 bar close`) — the research's convention. The options settle (and are auto-exercised) on **the official closing price**, the primary listing market's closing auction, which the live tracker reads from UW's daily bar. Here the official close is Theta's EOD daily bar (its 17:15 report), checked against UW's daily bar (`r` row) where both exist (2025-10-13 →).

|  | SPY | QQQ |
|---|---|---|
| sessions with a trade | 971 | 968 |
| official close found (source) | 971 ({'theta_eod': 971}) | 968 ({'theta_eod': 968}) |
| Theta EOD vs UW daily close: sessions with both / disagreeing by > $0.005 | 248 / 0 | 246 / 0 |
| official = 15:59 bar (within $0.005) | 76 | 77 |
| |official − 15:59|: mean / median / p95 / max | 0.054 / 0.040 / 0.130 / 5.25 (2025-04-09) | 0.055 / 0.040 / 0.160 / 0.98 (2024-05-31) |
| sessions with |official − 15:59| > $0.05 / > $0.25 | 355 / 11 | 355 / 17 |
| sessions where the two straddle a traded leg's strike | 42 | 23 |

SPY on 2025-04-09: the 15:59 bar closed at 543.37 and the official close was 548.62 (+$5.25); SPX's prints stood at 5455 from 15:58 to 16:00, so the jump was SPY's closing cross, not the market. Every session's two closes and the crossing flag are in `out/settlement_sessions.csv`.

| candidate · structure | trades | trades whose P&L changes | mean change of those $ | largest |change| $ | trades with a strike between the two closes / a leg's ITM state changed | total, 15:59 bar | total, official close | mean $ a trade | replay payoff ≠ re-derived payoff at 15:59 |
|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | 4426 | 810 (309 better, 501 worse) | -1.22 | +94.00 | 56 / 66 | +17,668 | +16,680 | +3.99 → +3.77 | 0 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | 3852 | 3520 (1855 better, 1665 worse) | +0.32 | +163.00 | 56 / 80 | +62,083 | +63,218 | +16.12 → +16.41 | 0 |
| fly5 long call ±5 | 3852 | 3520 (1855 better, 1665 worse) | +0.32 | +163.00 | 56 / 65 | +31,512 | +32,647 | +8.18 → +8.48 | 0 |
| fly5 long put ±5 | 3854 | 3522 (1855 better, 1667 worse) | +0.32 | +163.00 | 56 / 71 | +24,279 | +25,391 | +6.30 → +6.59 | 0 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | 4485 | 966 (388 better, 578 worse) | -1.42 | +200.00 | 65 / 76 | +26,797 | +25,424 | +5.97 → +5.67 | 0 |

fly5's three structures share their strikes' settlement, so their changed counts match; the change is the same intrinsic difference for every cost assumption (it moves the NBBO, mid, +1c and +2c P&L by the same dollars).

**Entry legs, re-derived.** `check_entries.py` drew 100 tradable trades (seed 20261022; {'condor_em1': 33, 'condor_d20': 33, 'fly5': 34}) and rebuilt each from the raw files with its own plain loops — no import of the tracker: spot = the close of the last bar stamped before the minute; the chain = the rows stamped at the minute; the strike rule written again (the 20-delta rule with its own Black-Scholes bisection); every leg's bid and ask; the OCC expiry = the session; the package price at the NBBO and at the mids; the max risk. Differences: spot 0, strikes 0, expiry 0, leg_quotes 0, price_nbbo 0, price_mid 0, max_risk 0, any 0.

**The chain files' expiry.** The stored chain files carry no expiry column (a file holds "the same-day contracts" by how it was fetched). Theta's flat end-of-day file lists every contract with its expiration for 2026-10-06 → 09; the contracts expiring that day are exactly the chain file's contracts on all 8 name-days (2026-10-06 SPY 350/350; 2026-10-06 QQQ 354/354; 2026-10-07 SPY 350/350; 2026-10-07 QQQ 354/354; 2026-10-08 SPY 350/350; 2026-10-08 QQQ 354/354; 2026-10-09 SPY 366/366; 2026-10-09 QQQ 412/412). Earlier dates have no such file on disk; the OCC symbols the replay writes carry the session as expiry by construction.

## 3. Execution: each leg at its NBBO, not a package fill

**What is modeled.** At entry every leg trades alone at its own NBBO — a short at its bid, a long at its ask (`Leg.fill`); the package price is the sum. That is the WORST price at which the package could trade if every leg had to cross separately, and a real complex order does not trade that way: it rests or crosses as one package on the complex order book, at a net price in $0.01 steps for SPY and QQQ ($0.05 steps for SPX and SPXW packages — to be confirmed against Cboe's current rule before an SPXW run), and can fill inside the summed NBBO or not at all. The stored quotes carry no complex-order book and no fills, so neither the fill rate nor the price a package would have got can be measured from them; the table brackets it between the legs' NBBO (as modeled), worse fills, and the mids.

**When each cost applies (from `paper_tracker.py`).** Open: $0.65 a contract on every contract — four for every structure here (a condor 1+1+1+1, an iron fly 1+1+1+1, a call or put fly 1+2+1), $2.60 a structure (`LEGS × FEE`). Held to expiry: no fee; every leg at intrinsic on the settlement price. The $0.01 / $0.02 stresses (`pnl_1c`, `pnl_2c`) move EVERY CONTRACT at the open only — $4 / $8 a structure — and do not touch the settlement. The 15:58 exit (`close_row`): a long sold at its bid, a short bought back at its ask, $0.65 a contract closed; a long with no bid is left to expire with no fee; the replay applies no stress to the exit — the "+$0.01 open and close" columns here add it to every contract closed as well. Not modeled anywhere: exercise and assignment fees, the commission on the resulting stock trade, regulatory and clearing fees (ORF, OCC, SEC / FINRA TAF on sales), borrow on a short stock position, and margin interest. The mid column prices every leg at its mid with the same fees.

| candidate · structure | period | NBBO legs (as modeled) | +$0.01 a contract at the open | +$0.02 a contract at the open | every leg at its mid | package NBBO width $ (mean / median) | NBBO→mid slip $ | each $0.01 of package improvement | break-even: worse fill a contract | 15:58 exit, NBBO | 15:58 exit, +$0.01 open and close | 15:58 exit, +$0.02 open and close | 15:58 exit at mids | +1c: session-mean block-20 CI | +2c: session-mean block-20 CI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | i | +3.47 | -0.53 | -4.53 | +5.48 | 4.01 / 4.00 | 2.01 | +1.00 | +0.87¢ | -4.83 | -11.26 | -17.70 | -0.83 | [-17.83, +12.05] | [-35.60, -5.82] |
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | ii | +4.10 | +0.10 | -3.90 | +6.16 | 4.12 / 4.00 | 2.06 | +1.00 | +1.03¢ | -7.52 | -14.62 | -21.71 | -2.81 | [-21.15, +19.61] | [-40.00, +0.69] |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | i | +16.59 | +12.59 | +8.59 | +19.04 | 4.89 / 5.00 | 2.45 | +1.00 | +4.15¢ | -7.81 | -14.03 | -20.25 | -1.65 | [+33.24, +75.26] | [+17.40, +59.59] |
| fly5 long call ±5 | i | +9.60 | +5.60 | +1.60 | +19.42 | 19.64 / 15.00 | 9.82 | +1.00 | +2.40¢ | -31.37 | -38.43 | -45.48 | -2.65 | [+5.10, +48.43] | [-10.73, +32.64] |
| fly5 long put ±5 | i | +7.43 | +3.43 | -0.57 | +19.45 | 24.04 / 18.00 | 12.02 | +1.00 | +1.86¢ | -36.63 | -43.79 | -50.95 | -1.81 | [-3.93, +40.72] | [-19.71, +24.81] |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | +16.20 | +12.20 | +8.20 | +18.62 | 4.85 / 4.00 | 2.42 | +1.00 | +4.05¢ | -13.77 | -20.72 | -27.67 | -6.53 | [+24.81, +73.13] | [+8.96, +57.19] |
| fly5 long call ±5 | ii | +7.13 | +3.13 | -0.87 | +18.78 | 23.29 / 17.00 | 11.65 | +1.00 | +1.78¢ | -35.98 | -43.25 | -50.52 | -7.59 | [-12.84, +37.95] | [-28.80, +21.99] |
| fly5 long put ±5 | ii | +5.58 | +1.58 | -2.42 | +19.44 | 27.72 / 20.00 | 13.86 | +1.00 | +1.39¢ | -39.19 | -46.87 | -54.55 | -6.15 | [-20.11, +31.84] | [-36.06, +15.95] |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-a | +2.42 | -1.58 | -5.58 | +4.47 | 4.10 / 4.00 | 2.05 | +1.00 | +0.60¢ | -5.66 | -12.13 | -18.61 | -1.61 | [-21.54, +4.39] | [-39.44, -13.60] |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-b | +8.71 | +4.71 | +0.71 | +10.76 | 4.09 / 4.00 | 2.05 | +1.00 | +2.18¢ | -6.62 | -13.32 | -20.01 | -2.22 | [-1.49, +56.03] | [-19.07, +37.07] |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | +7.67 | +3.67 | -0.33 | +9.77 | 4.20 / 4.00 | 2.10 | +1.00 | +1.92¢ | -5.54 | -12.79 | -20.05 | -1.03 | [-0.61, +32.71] | [-19.42, +13.79] |

A package filled $0.01 better than the summed NBBO adds $1.00 a structure (one cent × 100); the break-even column is how much worse than the NBBO every contract could fill (at the open, hold to expiry) before the period's mean is zero. The mid column is the most a package could get resting at the middle of every leg; whether it fills there is not in the data.

## 4. Inference

**The method in the current report** (`paper_backtest.session_boot`, read in the code and re-derived here): a percentile bootstrap that resamples SESSIONS — the sessions holding at least one trade of the cell — with replacement, independently, 2,000 draws, numpy `default_rng(20261016)` (the same seed for every cell, so every interval uses the same index draws); the statistic is the trade-weighted mean of the drawn sessions' trades (Σ P&L ÷ Σ trades); the interval is the 2.5th and 97.5th percentiles. The D1 lift (`lift_d1`) uses the same draws as session weights on Hypothesis E's time-matched formula; the 15:58 comparison bootstraps the paired difference the same way. Re-derived from the rows by `report_ci` in run_audit.py:

| cell | report CSV | this audit |
|---|---|---|
| condor_em1 condor | [+1.00, +6.86] | [+1.00, +6.86] |
| fly5 iron | [+11.58, +20.73] | [+11.58, +20.73] |
| fly5 call | [+3.55, +12.87] | [+3.55, +12.87] |
| fly5 put | [+1.63, +11.02] | [+1.63, +11.02] |
| condor_d20 condor | [+3.30, +8.47] | [+3.30, +8.47] |

What it does right: a session's trades (its five minutes; fly5's two names and two minutes) stay together, so the trade-level independence a naive interval would assume is not assumed. What it does not do: (a) sessions are independent draws — no serial dependence between neighbouring sessions (volatility clusters); (b) one interval over every period, the in-sample and selection spans pooled; (c) fly5's iron, call and put flies are one trade seen three ways (same strikes, same settlement; their session P&Ls correlate as below) and are printed as three results; condor_em1 and condor_d20 share 13:00 and 13:30 on the same sessions; (d) the per-trade mean weighs a session by how many of its minutes were tradable.

Session P&L correlation, 2022-11-11 → 2024-12-31 (official close, NBBO):

|  | condor_em1 condor | fly5 iron | fly5 call | fly5 put | condor_d20 condor |
|---|---|---|---|---|---|
| condor_em1 condor | +1.00 | +0.30 | +0.31 | +0.31 | +0.77 |
| fly5 iron | +0.30 | +1.00 | +1.00 | +0.99 | +0.59 |
| fly5 call | +0.31 | +1.00 | +1.00 | +0.99 | +0.59 |
| fly5 put | +0.31 | +0.99 | +0.99 | +1.00 | +0.59 |
| condor_d20 condor | +0.77 | +0.59 | +0.59 | +0.59 | +1.00 |

Session P&L correlation, 2025-01-02 → 2026-10-09 (official close, NBBO):

|  | condor_em1 condor | fly5 iron | fly5 call | fly5 put | condor_d20 condor |
|---|---|---|---|---|---|
| condor_em1 condor | +1.00 | +0.23 | +0.24 | +0.23 | +0.73 |
| fly5 iron | +0.23 | +1.00 | +0.99 | +0.99 | +0.56 |
| fly5 call | +0.24 | +0.99 | +1.00 | +0.99 | +0.56 |
| fly5 put | +0.23 | +0.99 | +0.99 | +1.00 | +0.55 |
| condor_d20 condor | +0.73 | +0.56 | +0.56 | +0.55 | +1.00 |

**Session-level inference, by period** (official close, NBBO legs, fees in). A session's P&L is the sum of the candidate-structure's trades that day (zero on a session it ran and took no trade); the mean session P&L gets percentile intervals from the iid session bootstrap and from a moving-block bootstrap over sessions in calendar order (blocks of 5 and 20 sessions, 2,000 draws, seeded); the per-trade mean (Σ ÷ Σ) the block-20 interval. Effective N: n ÷ (1 + 2 Σ_{k≤5} (1 − k/n) ρ_k) from the session autocorrelations, and n × Var_iid ÷ Var_block-20 of the session mean. No interval here treats trades as independent.

| candidate · structure | period | sessions | trades | sessions traded / run | mean $ a trade | mean % of max risk | mean max risk | mean $ a session | session CI (iid sessions) | block-5 CI | block-20 CI | mean $ a trade, block-20 CI | session P&L acf lag 1..5 | effective N (acf / block-20) | total $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | i | 2022-11-11 → 2024-12-31 | 2358 | 525 / 530 | +3.47 | 2.16% | $173 | +15.46 | [-0.73, +31.74] | [-2.26, +31.58] | [-0.16, +29.96] | [-0.04, +6.68] | +0.04 -0.01 -0.09 -0.08 +0.01 | 730 / 606 | +8,193 |
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | ii | 2025-01-02 → 2026-10-09 | 2068 | 439 / 441 | +4.10 | 2.46% | $167 | +19.25 | [-2.26, +38.82] | [-3.06, +38.70] | [-2.40, +38.40] | [-0.51, +8.15] | -0.02 -0.01 -0.01 +0.07 -0.03 | 440 / 464 | +8,487 |
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | iii | 2026-10-12 → 2026-10-21 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | i | 2022-11-11 → 2024-12-31 | 2095 | 530 / 530 | +16.59 | 4.74% | $399 | +65.58 | [+43.08, +87.28] | [+42.54, +89.37] | [+49.06, +91.11] | [+12.41, +23.06] | +0.01 -0.03 +0.01 -0.01 -0.02 | 580 / 629 | +34,755 |
| fly5 long call ±5 | i | 2022-11-11 → 2024-12-31 | 2095 | 530 / 530 | +9.60 | 2.96% | $406 | +37.95 | [+14.70, +59.95] | [+14.27, +61.80] | [+20.94, +64.30] | [+5.29, +16.25] | +0.02 -0.02 +0.01 -0.01 -0.02 | 549 / 596 | +20,116 |
| fly5 long put ±5 | i | 2022-11-11 → 2024-12-31 | 2097 | 530 / 530 | +7.43 | 2.43% | $408 | +29.42 | [+6.08, +51.25] | [+5.36, +53.67] | [+11.92, +56.63] | [+3.01, +14.31] | +0.01 -0.01 +0.01 +0.01 -0.01 | 515 / 542 | +15,591 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | 2025-01-02 → 2026-10-09 | 1757 | 441 / 441 | +16.20 | 5.42% | $366 | +64.54 | [+34.13, +92.37] | [+37.19, +92.60] | [+40.67, +89.07] | [+10.26, +22.36] | -0.02 -0.05 +0.01 -0.05 -0.06 | 663 / 663 | +28,463 |
| fly5 long call ±5 | ii | 2025-01-02 → 2026-10-09 | 1757 | 441 / 441 | +7.13 | 2.93% | $375 | +28.41 | [-3.04, +56.35] | [+0.40, +56.54] | [+3.06, +53.91] | [+0.77, +13.53] | -0.01 -0.05 +0.01 -0.05 -0.06 | 639 / 622 | +12,531 |
| fly5 long put ±5 | ii | 2025-01-02 → 2026-10-09 | 1757 | 441 / 441 | +5.58 | 2.53% | $377 | +22.22 | [-9.01, +49.80] | [-5.47, +50.67] | [-4.15, +47.72] | [-1.04, +12.00] | -0.02 -0.05 +0.02 -0.04 -0.06 | 630 / 607 | +9,800 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | iii | 2026-10-12 → 2026-10-21 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — |
| fly5 long call ±5 | iii | 2026-10-12 → 2026-10-21 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — |
| fly5 long put ±5 | iii | 2026-10-12 → 2026-10-21 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-a | 2022-11-11 → 2024-06-30 | 1823 | 403 / 405 | +2.42 | 1.53% | $171 | +10.88 | [-8.26, +29.12] | [-6.13, +27.35] | [-3.59, +22.52] | [-0.77, +4.99] | -0.03 -0.05 -0.08 -0.10 +0.06 | 658 / 857 | +4,407 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-b | 2024-07-01 → 2024-12-31 | 572 | 125 / 125 | +8.71 | 5.25% | $169 | +39.86 | [+4.36, +73.08] | [+2.07, +73.25] | [+16.68, +74.80] | [+3.68, +15.89] | +0.17 -0.10 -0.15 -0.12 -0.13 | 323 / 186 | +4,983 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | 2025-01-02 → 2026-10-09 | 2090 | 440 / 441 | +7.67 | 4.68% | $168 | +36.36 | [+18.25, +53.22] | [+17.68, +53.66] | [+18.42, +51.77] | [+3.87, +10.89] | +0.02 -0.01 +0.02 +0.04 -0.08 | 453 / 466 | +16,034 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | iii | 2026-10-12 → 2026-10-21 | 0 | 0 | — | — | — | — | — | — | — | — | — | — | — |

The session autocorrelations at lags 1–5 are within ±0.10 on every series except condor_d20 i-b (max |ρ| 0.17), and the block-5 and block-20 intervals are close to the iid-session ones: dependence between neighbouring sessions adds little width here. What changes the reading is the official-close settlement (section 2) and the period split (sections 5–6).

## 5. Periods: training, selection, untouched forward

Defined from the research notes, never pooled into one headline:

| candidate | period | sessions | what the span was used for |
|---|---|---|---|
| condor_em1 | i | 2022-11-11 → 2024-12-31 | development: hyp_b fit (the pre-registration picked the VIX-mid cell; this all-VIX parent ranked 4th) |
| condor_em1 | ii | 2025-01-02 → 2026-10-09 | selection read: hyp_b OOS, read once; the tracked all-VIX form was written after it |
| condor_em1 | iii | 2026-10-12 → the last fetched session | untouched forward |
| fly5 | i | 2022-11-11 → 2024-12-31 | development: hyp_c fit (C pre-registered 15:00 iron ±2, call ±2, call ±5 — not these cells) |
| fly5 | ii | 2025-01-02 → 2026-10-09 | selection read: hyp_c OOS — the iron ±5 found post hoc on it; the 15:30 call ±5 named after it (hyp_f) |
| fly5 | iii | 2026-10-12 → the last fetched session | untouched forward |
| condor_d20 | i-a | 2022-11-11 → 2024-06-30 | model training: the frozen t2 model was fit on these sessions — its deciles here are IN-SAMPLE |
| condor_d20 | i-b | 2024-07-01 → 2024-12-31 | decile cuts: the nine cuts are this half-year's score quantiles (still hyp_e's fit period) |
| condor_d20 | ii | 2025-01-02 → 2026-10-09 | selection read: hyp_e OOS — out of the model's training, read before the candidate was set |
| condor_d20 | iii | 2026-10-12 → the last fetched session | untouched forward |

Sources: condor_em1 — `research_notes/Compass phase 2/hyp_b_boundary_theta.md` ("The pre-registered picks": the midday pick was the VIX-mid cell, its all-VIX parent fourth by the fit lower bound; "The rule, conditional on X" drops the VIX cut after "the VIX cut that made it the pick did not help OOS"). fly5 — `hyp_c_debit_flies.md` (pre-registered 15:00 iron ±2, call ±2, call ±5; "a neighbouring cell I did not pick (the IRON ±5 …) … identified after the OOS read") and `Compass phase 3/hyp_f_cash_butterfly.md` ("the primary cell was named … after C's OOS was printed"). condor_d20 — `hyp_e_short_premium_lift.md` and `scripts/models/t2_spy_full.manifest.json` (fit = sessions before 2024-07-01, 405 sessions, in-sample AUC 0.81 against 0.61 out of fold; cuts = the score quantiles of 2024-07 → 2024-12; frozen 2026-10-21T21:32Z, after the OOS read at 21:01Z); its section 4: "NOT PRE-REGISTRABLE … The OOS lift is read for the record only".

**There is no untouched forward period on the stored data for any candidate.** Every session from 2022-11-11 to 2026-10-09 was either the development span or the span the candidate was chosen on. The first untouched sessions are 2026-10-12 onward; they are not in the stored files and wait for the fetch (`paper_tracker.py --fetch-theta` on the owner's machine, then `--backtest` over them). Forward sessions expected through 2026-10-21: 8; fetched: 0.

## 6. D1 selection bias

condor_d20 carries the frozen t2 model's decile on every capture (`t2_decile_primary`: the full model where all four VIX features are there — every replayed row). Two comparisons, both on the official-close P&L, NBBO legs:

- **time-matched** (Hypothesis E §8, the replay report's formula): Σ_m N_D1(m)·[mean(D1 at m) − mean(all trades at m)] ÷ Σ N_D1, m the five minutes — D1 against the unconditional strategy at the same times of day, over all sessions;
- **session-matched**: Σ_s N_D1(s)·[mean(D1 trades in s) − mean(the other trades in s)] ÷ Σ N_D1(s), over the sessions holding both — D1 against the same session's other minutes (it removes which DAYS D1 picks; the minutes differ in time of day).

Intervals: iid-session and 20-session moving-block bootstraps of the paired statistic (2,000 draws). Scheduled-event sessions: any FOMC decision, FOMC minutes, CPI or NFP date in `data/macro_events_2022_2027.json` (sessions in i-a / i-b / ii: i-a 405 (60 with an event, 13 FOMC decisions), i-b 125 (19 with an event, 4 FOMC decisions), ii 441 (68 with an event, 14 FOMC decisions)).

| period | sessions kept | n | D1 trades / sessions | D1 mean $ | all trades mean $ (same minutes) | D2–D10 mean $ | time-matched lift $ | iid-session CI | block-20 CI | lift % of risk | block-20 CI (pp) | session-matched lift $ | sessions with D1 and non-D1 | iid-session CI | block-20 CI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| i-a | all sessions | 405 | 459 / 226 | +12.05 | +2.42 | -0.83 | +9.16 | [+4.72, +13.65] | [+4.73, +13.86] | 5.27% | [+2.61, +8.19] | +6.22 | 205 | [+1.10, +11.64] | [+2.18, +11.47] |
| i-a | without any scheduled-event session (FOMC decision, FOMC minutes, CPI, NFP) | 345 | 383 / 196 | +11.66 | +1.75 | -1.53 | +9.00 | [+4.34, +13.83] | [+4.77, +13.78] | 5.07% | [+2.56, +7.95] | +4.89 | 177 | [+0.65, +9.80] | [+1.27, +9.00] |
| i-a | without FOMC decision days only | 392 | 425 / 213 | +13.08 | +3.02 | -0.19 | +9.20 | [+5.06, +13.68] | [+4.87, +14.08] | 5.21% | [+2.61, +8.20] | +4.39 | 192 | [+0.37, +8.92] | [+1.05, +8.34] |
| i-a | scheduled-event sessions only | 60 | 76 / 30 | +14.06 | +6.03 | +3.10 | +7.88 | [-6.09, +20.90] | [-6.66, +22.62] | 4.75% | [-4.60, +13.27] | +12.54 | 28 | [-5.18, +32.91] | [-7.96, +33.73] |
| i-b | all sessions | 125 | 68 / 34 | +14.47 | +8.71 | +7.93 | +5.88 | [-15.91, +22.78] | [-3.49, +26.24] | 4.51% | [-1.68, +17.84] | -0.01 | 33 | [-13.85, +9.63] | [-7.32, +12.27] |
| i-b | without any scheduled-event session (FOMC decision, FOMC minutes, CPI, NFP) | 106 | 50 / 28 | +15.84 | +9.36 | +8.62 | +6.80 | [-16.78, +21.84] | [-2.07, +23.04] | 5.00% | [-0.35, +15.13] | -3.19 | 27 | [-22.40, +9.58] | [-10.50, +15.54] |
| i-b | without FOMC decision days only | 121 | 54 / 30 | +16.70 | +9.16 | +8.34 | +7.60 | [-12.62, +22.30] | [+1.04, +23.43] | 5.40% | [+1.29, +15.15] | -2.05 | 29 | [-18.52, +10.25] | [-10.52, +14.39] |
| i-b | scheduled-event sessions only | 19 | 18 / 6 | +10.68 | +4.96 | +3.40 | +5.84 | [-52.34, +48.25] | — | 4.41% | — | +8.64 | 6 | [-0.45, +15.06] | — |
| ii | all sessions | 441 | 196 / 116 | +21.45 | +7.67 | +6.25 | +13.75 | [+7.32, +19.22] | [+5.82, +21.86] | 8.94% | [+3.89, +14.08] | +3.23 | 114 | [-2.73, +9.14] | [-4.18, +11.77] |
| ii | without any scheduled-event session (FOMC decision, FOMC minutes, CPI, NFP) | 373 | 141 / 90 | +16.42 | +6.72 | +5.87 | +9.80 | [+1.66, +16.87] | [+2.15, +18.73] | 5.98% | [+1.11, +11.58] | +0.55 | 89 | [-6.82, +7.65] | [-8.18, +9.81] |
| ii | without FOMC decision days only | 427 | 161 / 103 | +16.79 | +7.38 | +6.56 | +9.40 | [+2.14, +15.74] | [+1.26, +17.78] | 5.86% | [+0.91, +11.06] | +1.58 | 102 | [-5.16, +7.82] | [-6.43, +11.10] |
| ii | scheduled-event sessions only | 68 | 55 / 26 | +34.35 | +12.83 | +8.47 | +20.88 | [+11.93, +29.49] | [+10.05, +37.52] | 14.55% | [+7.23, +25.76] | +10.53 | 25 | [+2.63, +21.33] | [-0.81, +35.95] |

Reconciliation with the replay report (15:59-bar settlement, pooled 2022-11-11 → 2026-10-09 — not a headline): time-matched lift +9.06 (report +9.06), session-matched +4.45.

**What the 2025+ lift is.** The frozen model was trained on sessions before 2024-07-01 and its cuts set on 2024-07 → 2024-12, so on 2025-01-02 → 2026-10-09 every decile is an out-of-training score. There the time-matched lift is +13.75 a condor (8.94% of max risk), block-20 interval [+5.82, +21.86]: D1 minutes beat the unconditional condor at the same times of day, and the interval stays clear of zero when neighbouring sessions are resampled together.

**What it is not.** (1) Not an untouched test: the candidate, its minutes and its D1 rule were written after this span had been read (hyp_e §4 labels it "not pre-registrable"; the model was frozen 31 minutes after the OOS read). (2) Not a minute-timing effect: against the same session's other minutes D1 adds +3.23 [-4.18, +11.77] — most of the time-matched lift is WHICH SESSIONS hold a D1 minute (D1 sessions were good for every minute's condor). (3) Not robust to the event days: without scheduled-event sessions the time-matched lift is +9.80 [+2.15, +18.73], on the 68 event sessions alone +20.88 [+10.05, +37.52] — 55 of the 196 D1 trades sit on event sessions; the opposite of the fit period's story in hyp_e (there the FOMC decision days destroyed the lift). (4) Not a confirmation of the training span: on the model's own training sessions (i-a) the decile is in-sample, so its +9.16 lift says only that the model fits its training data; on the cut half (i-b) +5.88 [-15.91, +22.78] is inside the noise. The replay report's pooled +$9.06 [+5.41, +12.81] averages these three spans.

**Do not read the D1 mean or win rate as evidence of predictive alpha.** D1's own mean ($21.45 in 2025+) is the unconditional harvest plus the session selection; the only evidence that bears on the model is the lift against the matched unconditional strategy, and the forward pre-registered re-test hyp_e asked for (≥ 150 new sessions) has not started.

## 7. Risk comparability

Official close, NBBO legs, fees in, one lot. Max risk: a credit structure width × 100 − the credit; a debit structure the debit (fees not in the denominator). Drawdown, worst session, streaks and tails are on the SESSION sums in calendar order. Not ranked; the rows are not comparable by mean dollars alone — a fly risks about twice a condor's dollars, and fly5's three rows are one trade.

| candidate · structure | period | mean $ a trade | mean % of max risk | win (trades) | profit factor | max drawdown $ (one lot, sessions) | worst session | longest losing streak (sessions) | full-loss share (≤ −95 % of max risk) | p1 session $ | p5 session $ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | i | +3.47 | 2.16% | 80.2% | 1.22 | 2,849 | 2023-08-04 (-902) | 4 | 3.7% | -820 | -411 |
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | ii | +4.10 | 2.46% | 80.4% | 1.22 | 2,910 | 2025-01-31 (-888) | 4 | 7.0% | -791 | -522 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | i | +16.59 | 4.74% | 69.3% | 1.78 | 2,399 | 2024-05-31 (-1,392) | 6 | 0.9% | -1,004 | -382 |
| fly5 long call ±5 | i | +9.60 | 2.96% | 65.4% | 1.40 | 3,137 | 2024-05-31 (-1,448) | 7 | 0.9% | -1,037 | -446 |
| fly5 long put ±5 | i | +7.43 | 2.43% | 63.3% | 1.30 | 3,543 | 2024-05-31 (-1,432) | 7 | 0.9% | -1,043 | -410 |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | +16.20 | 5.42% | 63.5% | 1.55 | 2,902 | 2025-03-04 (-1,133) | 4 | 2.1% | -887 | -567 |
| fly5 long call ±5 | ii | +7.13 | 2.93% | 59.5% | 1.21 | 5,115 | 2025-03-04 (-1,168) | 4 | 2.1% | -901 | -613 |
| fly5 long put ±5 | ii | +5.58 | 2.53% | 58.6% | 1.16 | 5,553 | 2025-03-04 (-1,240) | 5 | 2.1% | -908 | -610 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-a | +2.42 | 1.53% | 76.9% | 1.14 | 1,769 | 2024-05-31 (-873) | 4 | 3.7% | -750 | -404 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-b | +8.71 | 5.25% | 83.9% | 1.62 | 1,618 | 2024-08-30 (-810) | 3 | 5.1% | -785 | -483 |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | +7.67 | 4.68% | 82.1% | 1.51 | 2,292 | 2026-09-30 (-843) | 4 | 4.7% | -760 | -390 |

Cost sensitivity for the same rows is the section 3 table (+$0.01 / +$0.02 a contract, the mids, $1.00 a structure for each cent of package improvement, the break-even, and the 15:58 exit).

## 8. Expiration mechanics

SPY and QQQ options are American-style and physically settled: an option in the money by $0.01 or more at the official close is exercised automatically by OCC's exercise-by-exception unless its holder says otherwise, and a holder may exercise or abandon until the cut-off after the close (about 5:30 pm New York) on after-hours prices — so a short leg near the money can be assigned or not on information the writer does not have until the next morning. Assignment of a short call delivers 100 shares a contract, of a short put takes 100 in. Measured on every trade held to the close, at the official close:

| candidate · structure | period | trades | any leg ITM | a short leg ITM (assignment) | a long leg ITM (exercise) | a stock position left after expiry (net ≠ 0) | ITM legs that offset (both sides of a vertical) | stock left: mean / max $ value | mean modeled max risk | close within $0.01 / $0.25 / $0.50 of a short strike | a leg's ITM state differs 15:59 vs official |
|---|---|---|---|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | i | 2358 | 23.2% | 23.2% | 3.5% | 19.8% (8.9% long, 10.8% short) | 3.5% | $46,733 / $60,433 | $173 | 1.0% / 10.3% / 22.5% | 1.4% |
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | ii | 2068 | 23.4% | 23.4% | 6.4% | 16.9% (8.3% long, 8.6% short) | 6.4% | $66,391 / $77,722 | $167 | 0.6% / 8.6% / 15.5% | 1.5% |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | i | 2095 | 99.7% | 99.7% | 0.7% | 98.9% (47.1% long, 51.9% short) | 0.7% | $43,706 / $60,781 | $399 | 1.4% / 23.5% / 42.4% | 2.1% |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | 1757 | 99.6% | 99.6% | 1.8% | 97.8% (47.0% long, 50.8% short) | 1.8% | $63,509 / $77,909 | $366 | 1.0% / 16.8% / 32.2% | 2.0% |
| fly5 long call ±5 | i | 2095 | 99.4% | 52.0% | 99.4% | 99.3% (47.4% long, 51.9% short) | 0.1% | $43,718 / $60,781 | $406 | 1.4% / 23.5% / 42.4% | 1.8% |
| fly5 long call ±5 | ii | 1757 | 99.0% | 51.6% | 99.0% | 98.2% (47.4% long, 50.8% short) | 0.8% | $63,532 / $77,909 | $375 | 1.0% / 16.8% / 32.2% | 1.5% |
| fly5 long put ±5 | i | 2097 | 99.9% | 47.6% | 99.9% | 99.3% (47.0% long, 52.3% short) | 0.6% | $43,722 / $60,781 | $408 | 1.4% / 23.6% / 42.4% | 1.7% |
| fly5 long put ±5 | ii | 1757 | 99.2% | 48.0% | 99.2% | 98.2% (47.0% long, 51.2% short) | 1.0% | $63,532 / $77,909 | $377 | 1.0% / 16.8% / 32.2% | 2.0% |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-a | 1823 | 29.3% | 29.3% | 3.3% | 26.0% (11.1% long, 14.9% short) | 3.3% | $44,437 / $54,710 | $171 | 1.0% / 15.2% / 32.3% | 1.1% |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-b | 572 | 21.5% | 21.5% | 4.9% | 16.6% (8.0% long, 8.6% short) | 4.9% | $57,238 / $60,766 | $169 | 1.6% / 12.9% / 24.8% | 1.6% |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | 2090 | 24.3% | 24.3% | 4.1% | 20.2% (9.5% long, 10.7% short) | 4.1% | $65,899 / $77,326 | $168 | 0.6% / 13.2% / 25.0% | 2.2% |

After the close (2025-10-13 → 2026-10-09 only, where UW's post-market bar is on disk): the share of trades whose post-market range (16:00–20:00, so an upper bound for the window to the exercise cut-off) took a short strike across the money — the trades where the assignment was undecided at 16:00: condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) 38.1% of 1183; fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) 56.6% of 987; fly5 long call ±5 56.4% of 987; fly5 long put ±5 56.0% of 987; condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) 51.7% of 1176.

**The early close.** The 15:58 exit is the tracker's own rule (`close_row`; logged by the replay for fly5 and priced here for the condors off the raw chain at 15:58 with the same rule — on fly5 it reproduces the replay's 15:58 P&L on 11545 of 11545 trades with a value). It leaves no position overnight. A middle road a margin account could take (not the tracker's rule, shown for scale): close at 15:58 only the legs in the money or within $0.50 / $1.00 of the 15:58 spot, let the rest expire on the official close; the share in brackets is the trades where a leg left open still finished in the money (an assignment left to happen).

| candidate · structure | period | hold to the official close | 15:58 exit, NBBO (trades) | 15:58 exit, mids | fees a structure with the exit | close only legs within $0.50 (left ITM) | close only legs within $1.00 (left ITM) |
|---|---|---|---|---|---|---|---|
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | i | +3.47 | -4.83 (2358) | -0.83 | $4.18 | -0.54 (0.6%) | -1.33 (0.0%) |
| condor_em1 (SPY 2-wide iron condor, straddle edge, 11:30–13:30) | ii | +4.10 | -7.52 (2062) | -2.81 | $4.61 | -2.66 (0.6%) | -3.47 (0.2%) |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | i | +16.59 | -7.81 (2095) | -1.65 | $4.04 | -4.08 (0.9%) | -6.81 (0.0%) |
| fly5 iron ±5 (SPY+QQQ, 15:00 and 15:30) | ii | +16.20 | -13.77 (1752) | -6.53 | $4.52 | -9.20 (1.9%) | -12.90 (0.3%) |
| fly5 long call ±5 | i | +9.60 | -31.37 (2095) | -2.65 | $4.59 | -27.48 (0.8%) | -30.32 (0.0%) |
| fly5 long call ±5 | ii | +7.13 | -35.98 (1754) | -7.59 | $4.72 | -30.05 (0.8%) | -33.65 (0.1%) |
| fly5 long put ±5 | i | +7.43 | -36.63 (2097) | -1.81 | $4.66 | -32.06 (0.1%) | -34.73 (0.0%) |
| fly5 long put ±5 | ii | +5.58 | -39.19 (1752) | -6.15 | $4.99 | -32.87 (1.1%) | -36.85 (0.2%) |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-a | +2.42 | -5.66 (1823) | -1.61 | $4.21 | -1.24 (0.6%) | -2.44 (0.0%) |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | i-b | +8.71 | -6.62 (572) | -2.22 | $4.35 | -0.93 (0.2%) | -2.70 (0.2%) |
| condor_d20 (SPY 2-wide 20-delta iron condor, 13:00–15:00) | ii | +7.67 | -5.54 (2084) | -1.03 | $4.72 | +0.35 (1.0%) | -1.23 (0.5%) |

**What the hold-to-expiration payoff assumes, by account.**

- **Cash account.** The iron condors and the iron fly sell credit spreads, which brokers generally allow only in a margin account with spread approval (some allow them in a cash or retirement account against cash equal to the width); no cash account can carry the short stock an assigned short call leaves. The long call and put flies are debit structures a cash account can open, but held to the close they finish with 100 shares long or short on nearly every trade (the table: 98–99 %), worth $44–64K a lot against a $375–410 debit — a cash account cannot pay for the long stock or hold the short. So for a cash account the hold-to-expiration P&L is not achievable; the achievable number is an exit before the close, and under the tracker's 15:58 rule every fly5 structure's mean turns negative (above).
- **Margin account with spread approval.** It can carry an assignment overnight, but then the position is no longer the defined-risk structure: one side assigned and the other not (the "stock left" column — about one condor in five, nearly every fly) is a 100-share position exposed to the overnight gap, with the margin it needs; and near a short strike (the pin columns) the writer does not know at 16:00 whether he will be assigned. A positive defined-risk payoff at intrinsic does not remove this; the modeled P&L also charges no exercise, assignment or stock commission.
- **With an early close.** Closing before the close removes the delivery problem and costs the exit's bid-ask, the last minutes' time value and the fees; on the tracker's full 15:58 exit every candidate's mean turns negative in every period, and at the mids it is still negative. Closing only the legs within $0.50 or $1.00 of the money gives back most or all of the hold's mean as well (the condors land near zero, the flies stay negative) and still leaves a few trades with a leg in the money. **On this data the hold-to-expiration P&L is the only one that is positive, and it is the one a cash account cannot achieve and a margin account can achieve only by carrying assignment and overnight stock risk the P&L does not price.**

**SPXW is a different instrument and these results do not transfer.** SPXW options are cash-settled, European-style (no early exercise, no delivery) and PM-settled on the official SPX closing value; their quotes, widths and fees differ (index option fees and the $0.05 complex-order step), and Hypothesis B found SPXW condors negative or flat at the NBBO. On disk: same-day SPXW chains, 1-minute NBBO, 1106 session files 2022-05-13 → 2026-10-09; SPX 1-minute prints 2353 files 2017-06-01 → 2026-10-09 (the research's settlement proxy: the last print at or before 16:00); the official SPX closing value only in Theta's flat index_eod for 2026-10-06, 2026-10-07, 2026-10-08, 2026-10-09, 2026-10-12. The replay's fly_spxw candidate has been run only as a one-week sanity run (2026-10-05 → 09, outside the repository). An SPXW alternative needs its own backtest on actual SPXW contracts and quotes, SPXW fees, a stated package-fill rule in $0.05 steps, and the official SPX closing value for every session (not on disk before 2026-10-06).

## 9. Files and commands

```
cd "research_notes/Compass phase 3/backtest_audit"
# everything (integrity, the 100-trade entry check, settlement, execution, inference, D1, risk, expiry) → AUDIT.md + cumulative_through_<D>.md
PAPER_PARQUET_ROOT=<the stored Parquet> POLARS_MAX_THREADS=1 nice -n 10 python3 -I run_audit.py --through 2026-10-21
# the determinism check against a fresh replay root (adds out/determinism.json; run_audit reads it)
PAPER_PARQUET_ROOT=<…> POLARS_MAX_THREADS=1 nice -n 10 python3 -I ../../../scripts/paper_tracker.py --backtest --start 2022-11-11 \
   --end 2026-10-09 --candidates condor_em1,fly5,condor_d20 --backtest-data <fresh dir> --out <dir>
POLARS_MAX_THREADS=1 nice -n 10 python3 -I run_audit.py --rerun-root <fresh dir> --rerun-csv <dir>/backtest_2022-11-11_2026-10-09.csv
# the pieces alone
python3 -I check_integrity.py [--rerun-root DIR --csv A --rerun-csv B]
python3 -I check_entries.py --parquet-root <…>
```

`audit_lib.py` (loaders, calendar, periods, bootstraps), `check_integrity.py`, `check_entries.py`, `run_audit.py`, `write_reports.py`; `out/`: integrity.json, determinism.json, entries.json, settlement_sessions.csv, risk_by_period.csv, d1_lift.csv, expiration_mechanics.csv, quotes_1558_cache.parquet (the 15:58 quotes read once from the chain files), state.json. No secret is read or written; no vendor is called.

