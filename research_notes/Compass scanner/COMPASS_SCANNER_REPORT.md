# Compass scanner — report

**Pre-registration: `PREREG_COMPASS_SCANNER.md`, commit `142fcf4` (committed alone and pushed before any forward return
or P&L was computed).** The code files carry the sha256 values printed in the prereg; none changed after that commit.

## Verdict

**The signal check fails its pre-registered gate on Pick, so the study STOPS before section 4 (prereg 6.3).** At
15 minutes the Compass scanner's signals moved −0.28 bp in their own direction, and the matched excess over non-signal
minutes was −0.30 bp [−0.56, −0.07]: clear of zero on the WRONG side. At 30 minutes the signal mean was −0.06 bp and the
excess −0.19 bp [−0.57, +0.21]. The gate needs, at 15 or at 30 minutes, an excess > 0 with its block-20 interval clear of
zero and a positive signal mean. Neither horizon comes close.

So none of the following were computed: the option P&L (3b), the component ablation (3c), the variants A–F and G1
(section 4), the holdout read (section 5), the singles' secondary universe beyond the OI selection count, and the fetch
estimate for the other three expirations (answer 8). No exit, no option price after entry and no P&L of the Compass
scanner was read at any point. No held-out month was read for an outcome. AMD and AVGO were never opened. Nothing was
fetched from any vendor.

- **Primary verdict (SPY, QQQ, IWM):** no rule was read on the holdout. The Compass scanner shows no positive forward
  return on Pick, so no exit or contract change can be tested (the owner's section 3a).
- **Singles' secondary verdict:** not run. The gate stopped the study first (prereg §10).
- **Early-span secondary (SPY/QQQ 2022-11 → 2023-11, no OI):** not run, for the same reason.
- **Rules that pass:** none, so there is no frozen parameter list beyond v0 as pre-registered. No LEDGER row was added,
  because no rule was read on the holdout (prereg §11).

## Decisions taken before any outcome (from the prereg)

- **0DTE only; primary universe SPY, QQQ, IWM.** The singles are a separate secondary universe ("no OI filter, expiry
  days only, 2022-11 →").
- **OI decision (answer 3, selection data only, `out/oi_decision.json`).** This counted onsets on 512 non-held-out
  sessions from 2023-12-01 to 2026-10-21: 18,287 SPY + QQQ onsets, of which 17,892 pick a contract on at least one side.
  - Turning the OI ≥ 250 filter off (OI still ranked) changed **59 picks (0.33%)**.
  - The rule as it must run without daily OI (no filter and no OI terms in the pick) changed **3,269 (18.27%)**.
  - The prereg's rule required both counts under 1%, so the decision went the other way:
    - the **primary span for SPY/QQQ starts 2023-11-21** (in practice 2023-12-01);
    - **2022-11-11 → 2023-11-20 is a labelled secondary**.
  - IWM, shown only: 1.25% / 7.73%.
- **The splits**:
  - **Holdout months** (seed 2026102301): 28 of the 113 months 2017-06 → 2026-10, for every layer.
  - **Held-out singles** (seed 2026102302): AMD and AVGO.
  - **Signal layer Pick / Check:** 1,055 / 704 sessions (2017-07-05 → 2022-11-18 / 2022-11-21 → 2026-10-21).
  - **Option layer Pick / Check:** 426 / 284 sessions (2022-11-11 → 2025-04-02 / 2025-04-03 → 2026-10-21). The primary
    Pick is 228 sessions from 2023-12-01.
- **Forward return**: the close of the bar stamped m − 1 + h against the signal bar's close (bar m − 1), signed by
  v0's direction, in bp. A **signal** is any evaluated minute with score ≥ 80. The **baseline** is every other
  evaluated minute, matched by name and minute of day. The interval is a 20-session moving-block bootstrap with all
  three names together, 2,000 draws (`audit_lib.block_draws`, seeded).
- **The implied move "at 09:30"** is read on the 09:31 row, because every stored 09:30 row is unquoted.

## The signal check (step 3a) — every table

The Pick table carries the verdict. Check is descriptive, as the prereg says.

### Pick — 1,055 sessions, 2017-07-05 → 2022-11-18

Evaluated minutes 1,120,527; v0 signals (score ≥ 80) 69,942 (36,362 bullish, 33,580 bearish; grade A 57,395, A+ 12,547); onsets 56,071.

| h (min) | row | signals | signal mean bp [95%] | baseline mean bp [95%] | matched excess bp [95%] |
|---|---|---|---|---|---|
| 5 | **pooled** | 69,941 | −0.25 [−0.38, −0.11] | −0.02 [−0.08, +0.04] | −0.23 [−0.37, −0.10] |
| 5 | SPY | 22,970 | −0.24 [−0.42, −0.05] | −0.03 [−0.08, +0.03] | −0.22 [−0.41, −0.02] |
| 5 | QQQ | 23,728 | −0.29 [−0.47, −0.11] | −0.02 [−0.08, +0.05] | −0.28 [−0.49, −0.10] |
| 5 | IWM | 23,243 | −0.21 [−0.43, −0.00] | −0.03 [−0.11, +0.07] | −0.18 [−0.39, +0.01] |
| 5 | grade A | 57,394 | −0.23 [−0.37, −0.10] | −0.03 [−0.08, +0.03] | −0.21 [−0.36, −0.07] |
| 5 | grade A+ | 12,547 | −0.31 [−0.59, +0.01] | −0.03 [−0.09, +0.03] | −0.28 [−0.55, +0.02] |
| 5 | bullish | 36,362 | −0.20 [−0.35, −0.07] | −0.03 [−0.09, +0.03] | −0.18 [−0.33, −0.05] |
| 5 | bearish | 33,579 | −0.30 [−0.52, −0.06] | −0.03 [−0.08, +0.03] | −0.27 [−0.50, −0.03] |
| 5 | onsets only | 56,070 | −0.25 [−0.38, −0.12] | −0.03 [−0.08, +0.04] | −0.23 [−0.37, −0.11] |
| 15 | **pooled** | 69,940 | −0.28 [−0.57, +0.02] | +0.02 [−0.12, +0.18] | −0.30 [−0.56, −0.07] |
| 15 | SPY | 22,970 | −0.31 [−0.61, +0.03] | −0.01 [−0.15, +0.14] | −0.29 [−0.57, +0.00] |
| 15 | QQQ | 23,728 | −0.30 [−0.70, +0.09] | +0.05 [−0.08, +0.21] | −0.38 [−0.76, −0.03] |
| 15 | IWM | 23,242 | −0.22 [−0.70, +0.23] | +0.01 [−0.22, +0.25] | −0.23 [−0.61, +0.13] |
| 15 | grade A | 57,393 | −0.29 [−0.59, +0.01] | +0.02 [−0.13, +0.18] | −0.31 [−0.55, −0.07] |
| 15 | grade A+ | 12,547 | −0.22 [−0.70, +0.27] | +0.00 [−0.14, +0.17] | −0.25 [−0.70, +0.18] |
| 15 | bullish | 36,362 | −0.10 [−0.43, +0.23] | +0.00 [−0.14, +0.17] | −0.11 [−0.44, +0.17] |
| 15 | bearish | 33,578 | −0.47 [−0.89, +0.02] | +0.01 [−0.13, +0.18] | −0.49 [−0.87, −0.07] |
| 15 | onsets only | 56,069 | −0.28 [−0.57, +0.02] | +0.01 [−0.13, +0.18] | −0.30 [−0.54, −0.07] |
| 30 | **pooled** | 69,942 | −0.06 [−0.54, +0.48] | +0.11 [−0.23, +0.44] | −0.19 [−0.57, +0.21] |
| 30 | SPY | 22,971 | −0.17 [−0.66, +0.38] | +0.07 [−0.22, +0.36] | −0.26 [−0.68, +0.21] |
| 30 | QQQ | 23,728 | +0.05 [−0.59, +0.71] | +0.27 [−0.04, +0.60] | −0.24 [−0.86, +0.34] |
| 30 | IWM | 23,243 | −0.06 [−0.71, +0.65] | −0.01 [−0.48, +0.44] | −0.05 [−0.62, +0.53] |
| 30 | grade A | 57,395 | −0.11 [−0.59, +0.40] | +0.11 [−0.23, +0.44] | −0.23 [−0.65, +0.20] |
| 30 | grade A+ | 12,547 | +0.19 [−0.71, +1.10] | +0.10 [−0.23, +0.42] | +0.04 [−0.74, +0.77] |
| 30 | bullish | 36,362 | +0.08 [−0.49, +0.62] | +0.10 [−0.23, +0.43] | −0.05 [−0.71, +0.52] |
| 30 | bearish | 33,580 | −0.21 [−1.01, +0.71] | +0.11 [−0.22, +0.43] | −0.32 [−1.00, +0.42] |
| 30 | onsets only | 56,071 | −0.05 [−0.49, +0.46] | +0.11 [−0.23, +0.43] | −0.17 [−0.53, +0.21] |
| 60 | **pooled** | 63,256 | −0.32 [−1.16, +0.63] | +0.05 [−0.48, +0.64] | −0.34 [−1.01, +0.35] |
| 60 | SPY | 20,626 | −0.58 [−1.49, +0.38] | +0.15 [−0.30, +0.66] | −0.71 [−1.50, +0.09] |
| 60 | QQQ | 21,490 | −0.28 [−1.32, +0.87] | +0.25 [−0.28, +0.84] | −0.51 [−1.31, +0.31] |
| 60 | IWM | 21,140 | −0.10 [−1.20, +1.11] | −0.26 [−0.97, +0.53] | +0.18 [−0.86, +1.18] |
| 60 | grade A | 52,007 | −0.27 [−1.06, +0.66] | +0.04 [−0.48, +0.63] | −0.28 [−0.91, +0.36] |
| 60 | grade A+ | 11,249 | −0.56 [−1.92, +0.81] | +0.03 [−0.49, +0.62] | −0.59 [−1.76, +0.60] |
| 60 | bullish | 32,684 | −0.17 [−1.37, +1.06] | +0.03 [−0.50, +0.62] | −0.19 [−1.40, +0.93] |
| 60 | bearish | 30,572 | −0.48 [−1.93, +1.08] | +0.04 [−0.47, +0.62] | −0.50 [−1.76, +0.77] |
| 60 | onsets only | 50,808 | −0.28 [−1.09, +0.66] | +0.04 [−0.49, +0.63] | −0.30 [−0.92, +0.36] |

Matched excess by year, bp (points; signals in brackets):

| h | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 |
|---|---|---|---|---|---|---|
| 5 | −0.11 (4,688) | −0.21 (15,778) | −0.19 (12,535) | −0.12 (11,531) | −0.12 (11,131) | −0.50 (14,278) |
| 15 | −0.14 (4,688) | −0.19 (15,778) | −0.31 (12,535) | −0.34 (11,530) | −0.22 (11,131) | −0.53 (14,278) |
| 30 | −0.36 (4,688) | −0.03 (15,778) | −0.40 (12,535) | +0.25 (11,532) | −0.28 (11,131) | −0.52 (14,278) |
| 60 | +0.11 (4,248) | −0.20 (14,283) | −0.25 (11,494) | −1.51 (10,401) | −0.23 (10,007) | −0.01 (12,823) |

### Check (descriptive) — 704 sessions, 2022-11-21 → 2026-10-21

Evaluated minutes 747,433; v0 signals (score ≥ 80) 48,528 (24,910 bullish, 23,618 bearish; grade A 39,527, A+ 9,001); onsets 38,530.

| h (min) | row | signals | signal mean bp [95%] | baseline mean bp [95%] | matched excess bp [95%] |
|---|---|---|---|---|---|
| 5 | **pooled** | 48,528 | −0.03 [−0.17, +0.08] | −0.01 [−0.06, +0.04] | −0.01 [−0.14, +0.10] |
| 5 | SPY | 15,957 | −0.05 [−0.18, +0.07] | +0.01 [−0.04, +0.06] | −0.06 [−0.18, +0.06] |
| 5 | QQQ | 16,272 | −0.07 [−0.25, +0.09] | +0.01 [−0.05, +0.06] | −0.06 [−0.25, +0.12] |
| 5 | IWM | 16,299 | +0.04 [−0.22, +0.23] | −0.05 [−0.13, +0.03] | +0.09 [−0.14, +0.26] |
| 5 | grade A | 39,527 | −0.01 [−0.14, +0.10] | −0.01 [−0.06, +0.04] | +0.01 [−0.11, +0.11] |
| 5 | grade A+ | 9,001 | −0.12 [−0.40, +0.14] | −0.01 [−0.06, +0.04] | −0.10 [−0.38, +0.17] |
| 5 | bullish | 24,910 | −0.07 [−0.26, +0.08] | −0.01 [−0.06, +0.04] | −0.05 [−0.27, +0.12] |
| 5 | bearish | 23,618 | +0.02 [−0.23, +0.24] | −0.01 [−0.06, +0.03] | +0.03 [−0.20, +0.25] |
| 5 | onsets only | 38,530 | −0.03 [−0.17, +0.07] | −0.01 [−0.06, +0.04] | −0.02 [−0.14, +0.08] |
| 15 | **pooled** | 48,527 | +0.07 [−0.24, +0.33] | +0.02 [−0.15, +0.16] | +0.07 [−0.21, +0.32] |
| 15 | SPY | 15,957 | +0.14 [−0.15, +0.44] | +0.07 [−0.07, +0.21] | +0.08 [−0.20, +0.37] |
| 15 | QQQ | 16,271 | +0.01 [−0.33, +0.31] | +0.05 [−0.14, +0.22] | −0.00 [−0.37, +0.35] |
| 15 | IWM | 16,299 | +0.05 [−0.53, +0.51] | −0.08 [−0.30, +0.14] | +0.14 [−0.37, +0.54] |
| 15 | grade A | 39,526 | +0.07 [−0.24, +0.33] | +0.02 [−0.14, +0.16] | +0.07 [−0.19, +0.31] |
| 15 | grade A+ | 9,001 | +0.06 [−0.45, +0.50] | +0.02 [−0.15, +0.17] | +0.06 [−0.44, +0.51] |
| 15 | bullish | 24,909 | +0.02 [−0.31, +0.24] | +0.02 [−0.15, +0.17] | +0.01 [−0.34, +0.27] |
| 15 | bearish | 23,618 | +0.12 [−0.39, +0.60] | +0.02 [−0.15, +0.16] | +0.13 [−0.33, +0.59] |
| 15 | onsets only | 38,529 | +0.01 [−0.27, +0.24] | +0.02 [−0.14, +0.17] | +0.01 [−0.23, +0.22] |
| 30 | **pooled** | 48,528 | +0.21 [−0.41, +0.86] | +0.02 [−0.26, +0.30] | +0.20 [−0.31, +0.75] |
| 30 | SPY | 15,957 | +0.35 [−0.27, +1.08] | +0.18 [−0.09, +0.47] | +0.17 [−0.33, +0.76] |
| 30 | QQQ | 16,272 | −0.08 [−0.72, +0.56] | +0.12 [−0.22, +0.45] | −0.17 [−0.76, +0.37] |
| 30 | IWM | 16,299 | +0.37 [−0.55, +1.21] | −0.24 [−0.57, +0.11] | +0.61 [−0.19, +1.40] |
| 30 | grade A | 39,527 | +0.18 [−0.35, +0.67] | +0.02 [−0.26, +0.30] | +0.17 [−0.23, +0.51] |
| 30 | grade A+ | 9,001 | +0.36 [−0.95, +1.95] | +0.03 [−0.26, +0.31] | +0.32 [−0.90, +1.86] |
| 30 | bullish | 24,910 | +0.33 [−0.51, +1.11] | +0.02 [−0.27, +0.31] | +0.31 [−0.52, +1.05] |
| 30 | bearish | 23,618 | +0.09 [−0.71, +0.91] | +0.03 [−0.25, +0.30] | +0.08 [−0.55, +0.77] |
| 30 | onsets only | 38,530 | +0.10 [−0.43, +0.59] | +0.03 [−0.26, +0.31] | +0.08 [−0.32, +0.44] |
| 60 | **pooled** | 44,040 | +0.73 [−0.29, +1.81] | +0.21 [−0.28, +0.75] | +0.53 [−0.28, +1.30] |
| 60 | SPY | 14,439 | +0.75 [−0.33, +1.93] | +0.48 [−0.03, +1.12] | +0.26 [−0.57, +1.04] |
| 60 | QQQ | 14,795 | +0.41 [−0.76, +1.69] | +0.38 [−0.27, +1.04] | +0.05 [−0.86, +0.96] |
| 60 | IWM | 14,806 | +1.04 [−0.27, +2.21] | −0.23 [−0.80, +0.39] | +1.27 [+0.10, +2.25] |
| 60 | grade A | 35,954 | +0.69 [−0.22, +1.56] | +0.22 [−0.28, +0.77] | +0.47 [−0.17, +1.04] |
| 60 | grade A+ | 8,086 | +0.95 [−0.98, +3.19] | +0.23 [−0.27, +0.79] | +0.69 [−1.06, +2.56] |
| 60 | bullish | 22,663 | +1.12 [−0.30, +2.53] | +0.21 [−0.29, +0.78] | +0.90 [−0.56, +2.12] |
| 60 | bearish | 21,377 | +0.33 [−1.10, +1.75] | +0.24 [−0.25, +0.79] | +0.10 [−1.07, +1.21] |
| 60 | onsets only | 34,971 | +0.62 [−0.28, +1.47] | +0.22 [−0.28, +0.77] | +0.40 [−0.26, +0.97] |

Matched excess by year, bp (points; signals in brackets):

| h | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| 5 | +1.90 (398) | −0.15 (14,469) | +0.07 (10,079) | +0.07 (14,256) | −0.06 (9,326) |
| 15 | +5.62 (398) | −0.23 (14,469) | −0.03 (10,079) | +0.37 (14,255) | −0.02 (9,326) |
| 30 | +7.66 (398) | −0.09 (14,469) | +0.10 (10,079) | +0.48 (14,256) | +0.07 (9,326) |
| 60 | +7.11 (335) | +0.81 (13,040) | +0.34 (9,192) | +0.23 (13,066) | +0.47 (8,407) |

**In implied-move units** (the move ÷ that session's 09:31 0DTE ATM straddle; only sessions with a chain):

| sample | h | signals | signal mean [95%] | baseline mean | matched excess [95%] |
|---|---|---|---|---|---|
| Pick (SPY/QQQ, 2022-11-11 → 18 only) | 5 / 15 / 30 / 60 | 241 / 241 / 241 / 211 | −0.020 / −0.033 / −0.023 / −0.017 | −0.005 / −0.011 / −0.004 / −0.003 | −0.018 [−0.029, +0.009] / −0.033 [−0.056, −0.005] / −0.030 [−0.079, −0.030] / −0.010 [−0.028, +0.051] |
| Check (SPY/QQQ 2022-11-21 →, IWM 2024-04-19 →) | 5 / 15 / 30 / 60 | 41,912 / 41,911 / 41,912 / 38,066 | +0.0007 / +0.0028 / +0.0040 / +0.0093 | +0.0005 / +0.0023 / +0.0033 / +0.0077 | +0.0004 [−0.0016, +0.0021] / +0.0010 [−0.0029, +0.0045] / +0.0012 [−0.0038, +0.0058] / +0.0021 [−0.0071, +0.0095] |

The Pick figures in IM units rest on 5 sessions, so their intervals are not meaningful. They are shown because the
prereg lists them.

### Reading the result (descriptive)

**Pick (2017-07 → 2022-11).** The signals are slightly worse than the minutes around them at every horizon.

| horizon | matched excess | interval |
|---|---|---|
| 5 min | −0.23 bp | [−0.37, −0.10] |
| 15 min | −0.30 bp | [−0.56, −0.07] |
| 30 min | −0.19 bp | not clear of zero |
| 60 min | −0.34 bp | not clear of zero |

- Every name is negative at 15 minutes, and so is every year from 2017 to 2022.
- A+ signals are no better than A. Bullish and bearish signals are both negative at 15 minutes.

**Check (2022-11 → 2026-10).** The signs turn slightly positive, but nothing pooled clears zero at any horizon: at 15
minutes the excess is +0.07 [−0.21, +0.32], and at 30 minutes +0.20 [−0.31, +0.75].

**The scale.** These effects are a fraction of a basis point. A 0DTE at-the-money contract's spread and fees are worth
several basis points of the underlying, so no exit or contract rule could turn them into an option edge.

**One sub-cell clears zero on Check**, out of 9 rows × 4 horizons × 2 splits: IWM's 60-minute excess, +1.27 bp
[+0.10, +2.25]. The gate does not read it and it is not a finding.

This agrees with the earlier S04 diagnostic on the owner's "Quick Scalps" baseline (same family, same names, 2017–2026):
no forward value in the signal's direction.

## Integrity (section 6)

- **Plain-loop re-derivation**: `verify_scanner.py`, a separate script with plain Python loops that imports nothing
  from `scanner_lib`, re-read the raw bar Parquet. On a seeded sample (seed 20261023) of **40 signal minutes and 30
  non-signal minutes** from the Pick arrays it rebuilt the window, RSI_1m, RSI_5m, VWAP, RVOL, the swings, trend, BOS,
  MSS, the stretch filter, the score, the direction and the four signed forward returns.
- **Result: 0 of 70 minutes differ** (score exact, direction exact, forward returns within 1e-6 bp). Output:
  `out/verify_signal_pick.json`.
- The trade and no-trade re-derivation (≥ 30 trades, ≥ 20 no-trades) does not apply, because no trade was formed. The
  prereg names the signal-minute check for this case.
- **Deterministic and seeded**: the holdout draw is asserted on every import, and the bootstrap is `audit_lib`'s.

## Deviations

- **After the prereg commit: none.** The code's sha256 equals the prereg's, and every computation followed it as
  written.
- **Disclosed in the prereg, before it was committed:**
  - a smoke test scored SPY on 2024-06-04 (a held-out month), score only;
  - one hung run of `oi_decision.py` was killed with no output.
- **The container restarted after the signal check.** The Pick and Check outputs, the verifier output and the prereg
  were already on disk and committed or pushed, and nothing was recomputed.

## Files

- `PREREG_COMPASS_SCANNER.md` (`142fcf4`)
- Code: `scanner_lib.py`, `oi_decision.py`, `signal_check.py`, `verify_scanner.py`
- Outputs:
  - `out/oi_decision.json`
  - `out/signal_check_pick.json`, `out/signal_check_check.json`
  - `out/verify_signal_pick.json`
- The per-minute arrays (`signal_pick.npz`, `signal_check.npz`, about 32 MB each) stay in the scratch folder
  `$SP/scanner_work/` and are not committed.
