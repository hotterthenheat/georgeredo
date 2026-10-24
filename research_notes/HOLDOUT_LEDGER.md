# HOLDOUT LEDGER — every rule read on the two holdouts of the Compass ICT / Compass EMA studies

- **Holdout A** = index-product direction data (SPY, QQQ, IWM 1-min/daily bars, SPX prints, or their options) on any session
  2017-06-01 → 2022-05-12.
- **Holdout B** = index-product data (SPY, QQQ, IWM, SPX/SPXW bars or options) in any of the 28 months 2017-06, 2017-09,
  2017-10, 2018-01, 2019-07, 2019-08, 2020-06, 2020-08, 2020-11, 2020-12, 2021-01, 2021-03, 2021-05, 2021-11, 2022-04,
  2022-12, 2023-05, 2023-11, 2024-05, 2024-06, 2024-07, 2024-08, 2024-11, 2025-08, 2025-11, 2026-03, 2026-04, 2026-08.
- Unit: a rule (an entry/exit specification read against an outcome), as each study counts them, names not multiplied.
  "≥" = the notes give a family without a count; the count used is the smallest the notes support. Sources: the commits,
  `research/compass/registry.jsonl` at `75c29c9^`, and PREREG_COMPASS_SCANNER.md §12.
- Single-name reads (V3, V4, S06-TierA, Compass features' singles, H3, Compass direction) are listed at the foot, not counted.

| study (commit) | data and span | rules read | A | B |
|---|---|---|---|---|
| S04 (`b037899`) | SPY/QQQ/IWM bars 2017-06-01 → 2026-10-09 | Quick Scalps signal, forward returns (+ ablations, not counted) | 1 | 1 |
| S06 (`4aba507`) | same | 7 triggers × 4 filter sets | 28 | 28 |
| S12 (`be991de`) | bars 2017-06 → 2026-10-09 | first-half-hour momentum, 3 windows | 3 | 3 |
| S12b (`be991de`) | 0DTE 2022-11-11 → 2026-10-09 | 2 option expressions | 0 | 2 |
| S16a | bars 2017-06 → 2026-10-09 | 108 cells ÷ 3 names | 36 | 36 |
| S03, S16b (`3c8d6cb`) | weekly chains, sample 2017-06 → 2026-10-09 | Quick Scalps weekly; prior-day fade 2 cells × 2 exits | 5 | 5 |
| H10 (registry) | SPY bars 2017 → 2026-10-09 | last-30-minute momentum | 1 | 1 |
| H17 (registry) | SPX 2017 → 2026 | 4 day filters | 4 | 4 |
| S17 | SPY/QQQ monthly chains 2012-06 → 2026-10 | 5 structures | 5 | 5 |
| Lifecycle daily tier (`50de62a`) | SPY/QQQ/IWM option EOD 2012-06 → 2026-10 | ≥ 19 walk-forward finalists | ≥ 19 | ≥ 19 |
| V6 / atlas (`0d706b6`, `1660366`) | 43 names incl. SPY/QQQ/IWM bars 2017-06 → 2026-10 | PDH/PDL, round numbers | 2 | 2 |
| V8 (registry) | SPXW 2017-06 → 2022-04, SPY 2017-06 → 2022-10 month-ends | month-end 13:00 straddle | 1 | 1 |
| Compass H1 (`4a02144`) | SPY 2017-01 → 2025-10-10, QQQ 2012-06 → | overnight reversal | 1 | 1 |
| Edge H4 (`dfa575d`) | SPY/QQQ 2012/2017 → 2026-10-22 (exploration context + test) | intraday momentum | 1 | 1 |
| Edge H7, H8 (`6c94bb8`) | SPY 2017 → 2026-09, QQQ 2012/2013 → | pre-FOMC drift; turn of month | 2 | 2 |
| Compass features (`a2e14e4`, `2a49049`, `e5dd8c6`) | ETFs 2012-06 →; SPXW/SPY/QQQ 0DTE 2022 → 2026-10-21; its own 43-month holdout read (twice) | 23 features screened | 23 | 23 |
| Compass scanner signal check (`142fcf4`, `9e3888e`) | SPY/QQQ/IWM bars, Pick 2017-07-05 → 2022-11-18 (its non-held-out months; the 28 never opened) | the scanner score (RSI/VWAP/RVOL/structure family) | 1 | 0 |
| S01, S02 (`5e90201`, `6bf5934`) | SPY/QQQ/IWM 0DTE 2022-11-11 → 2026-10-09 | Quick Scalps + 41 variants | 0 | 42 |
| S09, S10 (`7167541`, `3c8d6cb`) | SPXW 0DTE 2022-05 →; SPY/QQQ/IWM | QS on SPXW; QS fade (≥ 2 cells) | 0 | ≥ 3 |
| S15 (registry) | SPY/QQQ 0DTE 2022-11-11 → 2026-10-09 | 10:00 straddle, 3 conditions | 0 | 3 |
| H9, H11, H13, H15, H16 (registry) | SPY/QQQ/SPXW 0DTE 2022-05 / 2025-06 → 2026-10 | straddles/strangles; grids of 1,890 + 2,736 configs | 0 | ≥ 4,630 |
| Steps 1–5 (`2185eb9` → `491a0c7`) | every 0DTE contract 2022-05-13 → 2026-10-09 | buy/sell-and-hold, times, exits, turn-ups, volume (≥ 1 a step) | 0 | ≥ 5 |
| Lifecycle Tier I (`425c7f4`) | 0DTE SPY/QQQ/IWM/SPXW 2022-05 → 2026-10-09 | 12 setups × 8 structures × 116 policies | 0 | 11,136 |
| V5, V7 (registry) | same-day chains 2022-05/11 → | calibration; event afternoons | 0 | 2 |
| Engine audit, phase 2 (4), phase 3 (E, F), backtest audit, SPXW analogues (`2820bb4`) | 0DTE 2022 → 2026-10-09 | ≥ 1 each | 0 | ≥ 9 |
| Picker (`c502122`, `1e10053`) | SPY/QQQ/IWM/SPXW 0DTE 2022 → 2026-10-21 | opening-range fade + improved | 0 | 2 |
| EMA system v1 preview | bars of 60 sessions before each week (2025-11, 2026-04 bars as warm-up only, no outcome) | — | 0 | 0 |
| Compass EMA ladder (previews 2025-02/03) | not held out; holdout not read | — | 0 | 0 |
| Step 6 (`30babaa`, `44b5547`) | 0DTE 2022-05-13 → 2026-10-09, the 28 months never opened | 18 rules | 0 | 0 |
| Compass ICT (`9d6c37e`, `0943030`) | exploration only; holdouts never opened | — | 0 | 0 |
| Compass EMA (this study, prereg) | not yet read | — | 0 | 0 |
| Compass Close (`research_notes/Compass Close/PREREG_COMPASS_CLOSE.md`, row added with the prereg, before any fetch or computation) | SPXW same-day PM chains 15:45–16:00, SPX prints, Cboe SPX closes: 470 new sessions 2017-06-02 → 2022-05-12 (gate = odd months 236, P&L = even months 234; 15 of B's 28 months inside); previously read 2022-05-13 → 2026-10-09 reported, not judged | 1 judged rule (15:55 ATM straddle to settlement) + 8 reported entry/exit books (call, put, move side, narrower leg, 15:50, 15:58, 15:56 ask, one-strike-OTM strangle); fee and event-day lines not counted | 9 | 9 |
| Compass Final (`research_notes/Compass Final/PREREG_COMPASS_FINAL.md`, row added with the prereg, before any fetch or computation) | SPY same-day chains 09:30–16:00, 266 sessions 2017-01-04 → 2022-04-27; QQQ same-day chains 15:00–16:00, 339 sessions 2012-06-01 → 2022-04-27; SPXW same-day chains at 13:00 and 14:05, 297 sessions 2017-01-03 → 2022-04-27; SPY/QQQ post-market bars to 17:30 on those sessions; QQQ stock 2025-10-13 → 2026-10-22 (H1, 257 sessions); every session read earlier for an index-product option (V8, S03, S16b, Compass Close's gate sample) excluded | 9 entry rules (fly5 iron judged, its call and put flies reported; condor_em1; condor_d20; the hyp B touch pick; T-E; H15 S2; H1 QQQ) + 4 settlement lines (0, a, c, 15:58 or the study's convention) on each of the 6 physically settled cells | 32 | 33 |

**Running count with Compass Final's row (2026-10-24): holdout A ≥ 174 rules; holdout B ≥ 16,008 rules.**

**Running count with Compass Close's row (2026-10-24): holdout A ≥ 142 rules (≥ 133 before it); holdout B ≥ 15,975 rules (≥ 15,966 before it); Compass EMA's prereg has read nothing.**

**Running count before Compass EMA's read: holdout A ≥ 133 rules; holdout B ≥ 15,966 rules** (11,136 of them Lifecycle
Tier I and ≥ 4,630 the short-premium grids, all in B's 13 option-era months; the 15 pre-2022-05 months carry the A-span
studies' 133 less the scanner's 1 = 132).

Single names, not counted: V3 / V4 (11 singles' same-day chains 2017-06 → 2026-10), S06-TierA (34 names' bars 2017-06 →),
Compass features' singles (2017-06 →, AVGO/MU holdout read), H3 (earnings condors 2019-04 → 2022-12), Compass direction
(X names 2019-04 →; its holdout names never opened).
