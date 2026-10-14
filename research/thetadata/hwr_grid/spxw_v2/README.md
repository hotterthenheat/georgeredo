# SPXW short-premium study, v2: complete chains, official settlement, tail stress and margin

Re-run of the round-2 SPXW study (`../spxw/`, pre-registration `../spxw/PREREGISTRATION.md`) in answer to the developer review
of `reports/High win rate 0DTE lanes.md` (adopted as `COMPASS_RESEARCH_PLAN.md` §10).  The original folder is not modified.
Generated numbers: `RESULTS.md` (written by `report.py` from `results/`).  Narrative note:
`research_notes/High win rate 0DTE lanes/empirical_spxw_full_chain_rerun.md`.

## Protocol (written before the v2 runs; SHA-256 in `protocol_sha256.txt`)

The pre-registered design is used unchanged: the same T-E rule, window and holdout; the same 2,880-configuration grid
(2,736 distinct); the same TRAIN (2022-05-13 → 2024-12-31) / TEST (2025-01-02 → 2026-10-09) split; the same selection rules
S1/S2 on TRAIN; the same seeds (bootstrap 7, joint null 8, random-entry minutes 11–15 — `random_minutes.csv` is a byte-identical
copy, SHA-256 `51cf9006…`); the same fills (sell at the NBBO bid, buy at the ask, at the row stamped at the minute), fees
($1.00 per contract per side, no fee on legs left to settle), take-profit/stop/exit rules, event filters and gate code.

Exactly two inputs change:

1. **Complete chains.** Option quotes are read from `$SP/theta/data_full/chains/SPXW/{date}.parquet` (every listed same-day
   strike, no ±2 % band; same schema).  Strike selection ("nearest listed strike outward") therefore never hits a storage limit.
2. **Official settlement.** Every settlement valuation (E2 hold-to-settlement, legs left to settle under E1, wings left at
   bid 0) uses the Cboe SPX close from `research/thetadata/settlement_audit/settlement_reconciliation.csv` (`cboe_close`; present
   for all 1,106 sessions including 2026-06-09) instead of the SPX print stamped 16:00.  The 16:00 print is kept as the
   column `settle_1600` and reported only as a sensitivity.

Reported in addition (descriptive; none of it changes a selection or a pass rule):
* a data-integrity check of the complete chains for every regular session, every fixed entry, every committed random-entry
  minute and every minute 10:00–14:30 (`integrity.py`);
* the round-2 S1 and S2 definitions and T-E's rule evaluated on the complete data next to the S1/S2 re-selected on complete
  TRAIN data; the random-entry comparison on matched days and pooled; a Bonferroni(2) lower bound for the two TRAIN selections
  (`analyze.py`, `te.py`);
* side-by-side tables against the round-2 results and a decomposition of every difference into band-skipped days and the
  settlement source (`compare.py`);
* tail stress (settlement P&L under SPX moves of −15, −10, −8.42, −5, +5, +8.42, +10, +15 % from the entry level), the worst
  historical 13:00→close and 14:05→close SPX moves 2017-06-01 → 2026-10-09, Reg-T and approximate portfolio margin, capital
  per lot so that the ±10 % and ±15 % shock losses are ≤ 25 % of capital, the annualised return on that capital from the TEST
  mean, and drawdown probability/length by a circular block bootstrap (block 20 sessions, also 5 and 60; seed 7) of the
  complete-data daily P&L (`stress.py`), for the round-2 S2 definition, the re-selected S2 (if different) and T-E's rule;
* the COMPASS §10 carry-lane gate items (`compare.py gate`).

**Amendment 1 (recorded before any v2 statistic was computed; time in `protocol_sha256.txt`).**  The complete-chain fetch
delivered 1,105 of 1,106 SPXW sessions; the request for **2024-06-21** stayed in flight for more than 30 minutes while the fetch
job moved on to other symbols, and this study may not log in to re-request it.  For that one session the simulator reads the
round-2 band file instead (`sim.chain_path`, flag `chain_src = band_fallback` on every trade and skip row).  Inside the band the
two files are row-for-row identical on every other session (`integrity_sessions.csv.gz`), so trades whose legs lie inside the
band are exactly what the complete chain would give; legs outside the band are skipped as `out_of_band` and are counted and
listed as still missing in the data-integrity results.  If the complete file arrives later, delete
`$SP/hwr_grid/spxw_v2/{trades,skips}/2024-06-21.parquet` and re-run the pipeline (`HWR_BAND_FALLBACK=0` disables the fallback).

Margin rule text used (stress.py): Cboe Rule 10.3(c)(5) as described in SEC Release 34-97019, 88 FR 14416 (2023-03-08):
"a margin deposit for short cash-settled index options in an amount equal to 100% of the current market value of the option
plus 15% (if overlying a broad-based index) … of the amount equal to the index value multiplied by the index multiplier minus
the amount, if any, by which the option is out-of-the-money.  The minimum margin required for such an option is 100% of the
option current market value plus 10% of the index value multiplied by the index multiplier for a call or 10% of the exercise
price multiplied by the index multiplier for a put."  Short put + short call (Cboe "Strategy-based Margin" page, initial
requirement): "short put or short call requirement, whichever is greater, plus the option proceeds of the other side."
The option value used is the entry proceeds (bid).  `regt_simple` applies 10 % of the index to both minimums (the formula in
the review request).  Portfolio margin is approximated as the largest expiration-value loss over SPX moves −8 % … +6 % (0.1 %
steps), net of credit, without broker house minimums — an approximation, not a TIMS calculation.

## Files

| File | Role |
|---|---|
| `sim.py` | the round-2 simulator with the two input changes (diff against `../spxw/sim.py` is limited to the chain loader and the settlement value) |
| `run_grid.py` | simulates every regular session → `$SP/hwr_grid/spxw_v2/trades/{date}.parquet`, `skips/{date}.parquet` (not in git) |
| `integrity.py` | work item 1: strike/quote availability for every needed leg; SHA-256 of every complete-chain file; band ⊆ complete check |
| `te.py` | T-C reproduction and T-E (window, holdout, sensitivities incl. the 16:00-print rule, random baseline matched/pooled, T-E.4 margin/sizing) |
| `analyze.py` | `train`: TRAIN metrics + `selection_train.json` (no TEST date loaded); `test`: TEST metrics, selections (re-selected and round-2 definitions, T-E rule), baselines, gate, multiplicity, effects, coverage, sizing |
| `stress.py` | work item 3: shocks, worst historical moves, Reg-T/PM margin, capital per lot, annualised return, block-bootstrap drawdowns |
| `compare.py` | v1 vs v2 tables, per-day decomposition, carry-gate items |
| `diag.py` | diagnostics (ATM fallbacks, settlement source, forward-filled exits, legs left to settle) |
| `report.py` | writes `RESULTS.md` |
| `stats.py`, `random_minutes.csv` | unchanged copies |

## Reproduce

```bash
SP=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad
cd /home/user/georgeredo/research/thetadata/hwr_grid/spxw_v2
python3 integrity.py                       # work item 1 (2 workers)
python3 run_grid.py                        # all 1,097 regular sessions (2 workers, resumable)
cp $SP/hwr_grid/spxw_v2/run_status.json results/
python3 analyze.py train                   # TRAIN metrics + selection_train.json (hash recorded before the TEST stage)
python3 analyze.py test
python3 te.py
python3 stress.py
python3 diag.py
python3 compare.py                         # side-by-side + carry gate
python3 report.py                          # RESULTS.md
```
No network access and no ThetaData login are needed.

## Outcome (appended after the runs, 2026-10-14; numbers from `results/`, details in `RESULTS.md`)

* **Amendment 1 resolved (03:11 UTC).**  The complete 2024-06-21 file arrived at 03:03 UTC; its band-fallback trade/skip files
  were deleted and the whole pipeline re-run.  No TEST-period figure changed; the S1/S2 selections are unchanged; TRAIN,
  T-E-window-baseline and whole-sample figures moved slightly (every changed cell, before → after: `results/resolution_changes.csv`,
  `resolution_diff.py`; summary in `RESULTS.md` §0).  The earlier (fallback) figures are kept in this list as "was".
* **Data integrity.** Complete chains for all 1,097 regular sessions (was 1,096, with 2024-06-21 on the band file).  No needed
  short or wing strike lies beyond the listed range at any fixed or committed random entry.  Residual gaps are vendor quote gaps
  on 2022-06-02 and 2024-06-21 (32 entry × k cases; was 42) and two no-credit wing cases on 2024-08-05.  The complete 2024-06-21
  file is itself partial: 127 of 333 strikes have one side only, and 7,429 of its band-file rows are absent from it.  All other
  37,307,656 band-file rows are present with identical bid/ask (was 37,315,085 of 37,315,085 before the file was replaced).  The
  complete chain supplies 531 naked and 1,739 winged fixed-entry trades the round-2 band could not hold (was 528 / 1,734).
* **T-C** reproduces exactly on 339/339 sessions.  **T-E still FAILS**: +$26.94 [−136.73, +170.75], n = 663; the holdout no
  longer "confirms" (+$138.97 [−19.69, +288.50]; round 2: +$152.93 [+1.91, +294.08]).
* **Grid.**  S1 is unchanged (`N0.0|14:05|tp0|st1|E2|F3`), TRAIN +$164.59 [+92.72, +236.58] (was +$165.25 [+93.38, +237.01]), TEST +$122.78 [−2.99, +246.45].  S2 re-selected on complete TRAIN data is
  `N1.0|14:05|tp0|st2|E2|F3`, TEST +$52.54 [−22.24, +122.49].  The round-2 S2 definition (`N0.5|14:05|tp0|st0|E2|F3`) on complete
  data: TEST n = 407 (100 % coverage), +$151.17 [+42.15, +251.73], win 70.8 %, Bonferroni(2) bound +$26.23; TRAIN n = 606,
  +$123.98 [+49.62, +192.92] (was n = 605, +$123.64 [+51.13, +194.44]).  TEST lower bounds > 0: 61 of 2,736 vs 39.8 expected by
  chance (95th percentile 196); TRAIN 227 (was 225) vs 54.3.
* **Random entry.**  Round-2 S2 lane − random is now +$22.60 [−147.61, +261.12] (round 2: −$92.82); the change is entirely the ten
  band-skipped days, above all 2025-04-09 (all five random minutes fell 10:15–12:39, before SPX jumped 2.6 % between 13:19 and
  13:20; their mean was −$32,554, while the 14:05 lane, entered at SPX 5,380.10, made +$2,778); without that day −$64.37 [−168.56, +45.84].  No timing skill is shown; the lane is carry.
* **Tail.**  A 10 % (15 %) SPX move from the 14:05 level costs a median $65,226 ($98,941) per lot on TEST; Reg-T ≈ $100,608 and
  approximate PM ≈ $51,928 per lot; capital so that ±10 % (±15 %) costs ≤ 25 %: median $261,570 ($396,198) per lot, i.e. 13.4 %
  (8.9 %) a year on the TEST mean.  The worst 14:05→close SPX move 2017-06-01 → 2026-10-09 is +5.28 % (2020-03-13); the worst
  13:00→close is +8.49 % (2025-04-09).
* **COMPASS §10 (carry lane):** not promotable — forward validation (T-G, ≥ 150 sessions and ≥ 7 months) has not started.  The
  round-2 S2 definition meets the data-integrity (TEST), modelled execution, statistical and stated tail-capital items; the
  re-selected S2 and T-E's rule fail the statistical item.
