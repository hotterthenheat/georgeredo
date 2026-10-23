# PREREG — Compass EMA (the owner's three EMA / ORB models), v0

Committed ALONE with `../HOLDOUT_LEDGER.md`, before any signal, trade, R or P&L is computed. Research only; read-only on
files already on disk (no fetch). Items the owner's spec left open are pinned here and marked **[v0]**.

## 1. Instruments, data, clock

- **Primary verdict: SPXW 0DTE**, signals on **SPY** 1-min bars (`theta/data/underlying/SPY`). **Secondary (labelled):
  QQQ 0DTE**, signals on QQQ bars. Chains `theta/data_full/chains/{SPXW,QQQ}/<date>.parquet` (1-min NBBO).
- New York clock; a 1-min bar stamped t (0 = 09:30) completes at minute t + 1; only completed bars are used. Regular session
  only (no pre-market rows exist on disk).
- 5m and 15m bars clock-aligned from 09:30 (5m bar j = stamps 5j..5j+4, completes at minute 5j+5): O first present, H max,
  L min, C last present, V sum; a bucket with no 1-min bar is missing **[v0]**.
- SPXW strikes: the contract is picked by delta on the SPXW chain's own parity forward, which is the SPX/SPY mapping at
  entry; the ratio SPX print stamped at the entry minute ÷ SPY's entry close is recorded **[v0]**.

## 2. Indicators (calls; puts mirrored)

- EMAs (alpha 2/(n+1), seeded with the first close **[v0]**) on 5m closes (9, 21, 50) and 15m closes (50, 200), run across
  sessions on the concatenated regular-session bars of the readable sessions (half days' bars included **[v0]**).
- 15m bias: the last 15m bar completed at the confirmation bar's completion: close > EMA50(15m).
- 5m alignment: EMA9 > EMA21 > EMA50 at the confirmation bar.
- Swings **[v0]**: 5m bar t is a swing high if H[t] > H[t−1], H[t−2] and H[t] ≥ H[t+1], H[t+2] (lows mirrored); confirmed
  when bar t+2 has completed; searched on the concatenated series across sessions. Structure HH/HL: the last two confirmed
  swing highs rising AND the last two confirmed swing lows rising (strict).
- VWAP: from 09:30 on 1-min typical price (H+L+C)/3 × volume; the confirmation bar's 5m close > VWAP at its end.
- RSI: Wilder RSI(14) on 5m closes across sessions (first value = simple means of 14 changes) > 50.
- RVOL: the bar's volume ÷ the mean volume of the same 5m slot over the prior 20 full readable sessions (half days out of
  the base **[v0]**) > 1.0.
- Chop skip: among today's last 12 5m bars ending at the confirmation bar, ≥ 4 crossings, a crossing = consecutive bars
  whose (close − VWAP) signs are nonzero and differ **[v0]**.
- Extended skip: |confirmation close − EMA21| > 1.0 × ATR(14) (Wilder, 5m bars, true range across sessions **[v0]**).
- Room: levels strictly beyond — or at — the entry price in the trade direction among PDH, PDL (prior session's high/low),
  the session high and low so far (every 1-min bar completed at entry, the confirmation bar included **[v0]**), and the
  09:30–09:59 range high/low (counted once complete, from 10:00 **[v0]**); the nearest one's distance must be ≥ 1R; no
  level in the direction → room passes **[v0]**.
- Event skip: no entry minute in 13:45–14:30 (inclusive) on scheduled FOMC statement days
  (`../Edge search/H7_H8_H9/data/fomc_statements_2012_2026.json`, `scheduled`, all 127 dates).
- Limits, per model/variant row and per name, each row run on its own **[v0]**: entry minutes 09:40–15:30; one open trade
  (a new entry minute must be later than the previous trade's last exit minute); stop for the day after 2 losing trades
  (losing = the trade's underlying result in R < 0, the same in both sequences **[v0]**); at most 4 trades a session.

## 3. Models

**Model 1, EMA pullback and reclaim.** Pullback bar = a 5m bar with L ≤ EMA9. At bar c: p = the latest pullback bar in
c−3..c−1 **[v0]**; the pullback began at s, the first bar of the run of consecutive pullback bars ending at p; no 5m close
< EMA21 in s..c **[v0]**. Confirmation: c closes bullish (C > O) and > EMA9, and every shared definition holds at c. Side:
the bias's (calls on a bullish bias, puts on a bearish one). One entry per pullback start s **[v0]**. Entry: the ask of the
quote stamped c's completion minute. Stop level = min L of s..p; R = entry close − stop (R ≤ 0 → no setup, counted).

**Model 2, 5-min ORB.** OR = the 09:30–09:34 5m bar. The first 5m close beyond either end among bars completing
09:40–11:00 is the session's one candidate **[v0]** (above → call, below → put); traded only if its close is on the same side
of VWAP and its RVOL ≥ 1.5, with the event skip and the limits; nothing else. Stop level = the OR's opposite end.

**Model 3.** Model 1 plus, at c: the last completed 15m close beyond EMA200(15m) in the trade direction; 15m structure
HH/HL (the swing rule on 15m bars); the 09:30–09:59 range ≥ 0.76 × the 9:31 straddle (C_mid + P_mid at the strike with
|C_mid − P_mid| smallest, chain row 1); entries only from 10:00. SPXW: the SPY range × (SPX print stamped 09:31 ÷ SPY's
09:30 close) **[v0]**. On holdout A (no 0DTE chains) the straddle is proxied, stated now: 0.798 × S × (VIX print stamped
09:31 / 100) × √(389 / (252 × 390)), S = the 09:30 close of the signal name **[v0]**; on exploration the proxy's agreement
with the straddle gate is reported (descriptive).

## 4. Contract and exits (all models)

- 0DTE; |delta| 0.40–0.60, nearest 0.50 (ties: lower spread, lower strike); Black-76 on the chain's parity forward at the
  entry row (the strike with both sides standing and |C_mid − P_mid| smallest; F = K + C_mid − P_mid), discount 1, T =
  minutes to 16:00 ÷ 525,600, IV from the mid; ask > bid > 0 and spread ≤ 10% of mid. None → no trade (counted; it does
  not count toward the limits).
- 3 contracts, sold at the bid of the quote stamped at the trigger minute (missing → the last bid in the 10 minutes
  before; none → $0, no fee). Triggers on the underlying, checked in time order; within a minute the targets first:
  - contract 1 at 1R, contract 2 at 2R: a 1-min high (call) / low (put) touching entry ± 1R / 2R **[v0]**;
  - stop (all open contracts): a 5m close beyond the stop level;
  - contract 3 (the runner) from entry **[v0]**: a 5m close back through EMA9 (call: close < EMA9);
  - flat at 15:58 (row 388).
- Fees per contract each way (PREREG_PICKER.md §4): SPXW $1.18748 under $1, $1.27748 at or above; QQQ $0.68748.
- Result in R = Σ over the 3 contracts of side × (exit underlying − entry) ÷ (3R); a target leg counts exactly its level,
  every other leg the triggering bar's close **[v0]**. Options % = net $ ÷ (3 × ask × 100).

## 5. Variants (exploration only) — 13 rows a name **[v0]**

M1, M2, M3 base; RSI 55/45 (M1, M3); RVOL ≥ 1.5 (M1, M3; M2 already uses it); runner trailed on EMA21 (all three);
X3: every contract still open, if entered before 14:00, out at the 14:00 bid (row 270) (all three).

## 6. Sequences **[v0]**

- **Direction sequence**: every signal is a trade (no contract step) — used for the gate, the finalists' mean R and
  holdout A.
- **Options sequence**: the contract step applies (no contract → no trade) — options P&L and holdout B. Its mean R is
  reported beside.

## 7. Splits (committed here)

- **Exploration**: 2022-05-13 → 2026-10-09 minus the 28 held-out months; QQQ entries from 2022-11-11. Full sessions with a
  chain file (half days out). A guard raises on opening any file dated ≤ 2022-05-12 or in a held-out month. The indicator
  series start 2022-05-13 (QQQ's too); the first 25 readable sessions are warm-up and every held-out gap is followed by 10
  re-warm sessions (indicators carry across the gap; no entries; counted) **[v0]**; a session whose prior trading session is
  held out is a re-warm session anyway. Sessions after 2026-10-09 are not read.
- **Holdout A (direction)**: SPY (and QQQ) bars 2017-06-01 → 2022-05-12, full sessions; warm-up bars 2017-01-03 →
  2017-05-31 opened at that read only **[v0]**. **Disclosure**: the Compass scanner's signal check (PREREG_COMPASS_SCANNER.md,
  142fcf4; its report 9e3888e) read SPY/QQQ/IWM bars 2017-07-05 → 2022-11-18 (its non-held-out Pick months) for an
  RSI / VWAP / RVOL / structure rule — a rule of this family, on most of this span. Earlier studies read it too (ledger).
- **Holdout B (options)**: the 28 months 2017-06, 2017-09, 2017-10, 2018-01, 2019-07, 2019-08, 2020-06, 2020-08, 2020-11,
  2020-12, 2021-01, 2021-03, 2021-05, 2021-11, 2022-04, 2022-12, 2023-05, 2023-11, 2024-05, 2024-06, 2024-07, 2024-08,
  2024-11, 2025-08, 2025-11, 2026-03, 2026-04, 2026-08. With chains: 13 (2022-12 on), 273 files each for SPXW and QQQ
  (counted from file names), less 4 half days = **269 full sessions each**. At the B read the bars are continuous (no gap).
- QQQ is **not a finalist path**; its holdouts are not read in this study **[v0]**.

## 8. Gate

On exploration, SPXW primary, direction sequence: mean R per trade of M1, M2, M3 (base). If all three ≤ 0: report and stop
before any options P&L.

## 9. Exploration report

Per row, SPXW and QQQ apart: trades and no-trade reasons (first failing check, in the order of section 2/3); mean R
(both sequences); options mean % and $ per trade after costs with the 20-session moving-block interval (audit_lib,
2,000 draws, sessions with zeros); win rate (net > 0), average winner and loser, profit factor, max drawdown ($, trade
order), exit-reason shares; by year, entry hour, calls vs puts, trend vs range days. Trend day **[v0]**: |close − open| ≥
0.5 × (high − low) on the signal name's session (09:30 open, 15:59 close); a trade is with the trend if its side =
sign(close − open). Descriptive (uses the whole day).

## 10. Finalists

At most 3 of the 13 SPXW rows; each needs exploration options mean % > 0, direction mean R > 0 and projected B ≥ 80
(trades per exploration session × 269). More than 3 → highest exploration options mean % per trade. k = the number.
None → nothing is read.

## 11. Holdout (read once, finalists only, SPXW)

- A: mean R per trade > 0 with the 20-session block interval at 1 − 0.05/k (two-sided percentile) clear of zero.
- B: options mean % > 0, interval at 1 − 0.05/k clear of zero, ≥ 80 trades, above the 97.5th percentile of 500 random-side
  draws (seed 20261023; each trade's side a fair coin; the same entry minute, contract rule on that side, exits mirrored,
  stop at the same distance; a flip with no contract left out of that draw).
- Pass = A and B. Also the interval at 1 − 0.05/N (N = the ledger's running count for that holdout, descriptive) and the
  share of profit from the 5 best days. The ledger is updated after the read.

## 12. Integrity

≥ 30 trades and 20 no-trade sessions re-derived from the raw files by separate plain-loop code (0 differences); 10
sessions rebuilt with the entry day's files cut at the entry minute (1-min bars stamped < m, quotes ≤ m), plus a control
cut one minute earlier; sha256 of the scripts in the report.
