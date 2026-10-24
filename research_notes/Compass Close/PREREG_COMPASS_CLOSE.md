# PREREG — Compass Close (buy the 15:55 SPXW 0DTE ATM straddle, hold to cash settlement)

Committed ALONE with `../HOLDOUT_LEDGER.md` (its new row) and the two session lists beside this file
(`sessions_new.csv`, `sessions_dropped_jan_may_2017.csv`), BEFORE any fetch and before any ratio, return or P&L of this
study is computed on any span. The spec is the owner's, implemented as written; every point the spec left open is pinned
here and marked **[pin]**. The owner's open decisions, resolved as defaults by the owner's instruction, are marked
**[decision]**. Step 0 (no fetch, no new P&L) is the scratchpad note `compass_close/STEP0.md`; its one figure on outcomes
(the 0.79 ratio, 2022–26, PREVIOUSLY READ) is quoted in section 3.

## 0. The owner's open decisions, resolved as defaults

1. **[decision] The Lifecycle daily tier's closing-price marks do NOT count as reads.** They are end-of-day marks of
   SPY/QQQ/IWM options, not the 15:45–16:00 SPXW quotes this study trades. The overlapping sessions are named and the
   gate figures are also reported with them excluded, as a sensitivity line (no verdict). Two overlap definitions,
   **[pin]**, from the daily tier's own position files (`lifecycle/runs/{dgrid,dbest,dholdout}/{SPY,QQQ,IWM}/
   positions.parquet`, positions with no skip reason):
   - **entry overlap**: a session on which the daily tier opened a position at that session's closing NBBO;
   - **expiry overlap**: a session on which a daily-tier position's expiration fell (its last close / settlement read).
   Counted from those files before this prereg (dates only, no outcome): of the 470 new sessions, **469** are entry
   overlaps (all but 2022-05-11) and **446** are expiry overlaps (24 are not). So "Lifecycle excluded" leaves 1 session
   (entry) or 24 (expiry); both lines are printed with their n and carry no weight.
2. **[decision] Holdout A (2017-06-01 → 2022-05-12) is read again by this study.** The ledger row is added in this
   commit, before anything is computed (running count before it: holdout A ≥ 133 rules, holdout B ≥ 15,966). The new
   data also cover 15 of holdout B's 28 months (2017-06, 2017-09, 2017-10, 2018-01, 2019-07, 2019-08, 2020-06, 2020-08,
   2020-11, 2020-12, 2021-01, 2021-03, 2021-05, 2021-11, 2022-04), so the row counts in B too.
3. **[decision] The 63 Jan–May 2017 sessions** of step 0's 533 have no SPX 1-min print on disk; they are **dropped**
   and listed in `sessions_dropped_jan_may_2017.csv`. SPX is not fetched for them, and their chains are not fetched.

## 1. Definitions (every value known at the decision minute)

- Times are New York. A bar stamped t is the minute ending at t; on the files this means: an SPX print stamped t is the
  index value at t, and a chain row stamped t is the NBBO at t (the repo's convention, e.g.
  `../Compass engine audit/clock_session.md`).
- **t\*** = 15:55. Half days are excluded and listed (section 3).
- **S(t)** = the SPX 1-min print stamped t (`theta/data/index/SPX/<D>.parquet`). No print at t → the session is
  dropped and counted (reason `no-spx-print`) **[pin]**.
- **K** = the listed SPXW strike nearest S(t\*); a tie goes to the lower strike. **[pin]** "Listed" = a strike for which
  the session's same-day SPXW chain has at least one row for the call AND one for the put among the rows stamped
  15:45–16:00 (a zero quote still counts as listed; the quote rule judges the quote). K is chosen from all listed
  strikes, never only from well-quoted ones.
- **C, P** = the same-day PM-settled SPXW call and put at K (root SPXW, expiration = the session's date).
- **bid, ask** = the NBBO of each leg in the row stamped t\*; **mid** = (bid + ask)/2 (computed, not read from the
  file's mid column). No row stamped t\* for a leg → the leg fails the quote rule (reason `no-quote-row`) **[pin]**.
- **STR_ask** = ask_C + ask_P; **STR_mid** = mid_C + mid_P (SPX points, $ per share of premium).
- **SET** = the official SPX close from Cboe's SPX daily file (`data/official_closes/cboe_SPX_History_2026-10-23.csv`),
  never the 16:00 print. Every session with |SET − S(16:00)| > 0.5 is flagged and kept. No Cboe close → dropped
  (reason `no-set`) **[pin]**.
- **f** = $1.28 per contract per side.
- **Quote rule** (each leg): bid > 0, ask > bid, and (ask − bid) ≤ 0.5·mid. Also reported: how many sessions have both
  legs passing a 10%-of-mid rule (bid > 0, ask > bid, (ask − bid) ≤ 0.10·mid).
- Units **[pin]**: quotes and SET in SPX points; ×100 → $ per contract; f in $ per contract per side. Every boundary
  asserts its unit (premium per share in (0, 200) points; f = 1.28; a P&L in $ equals 100 × points − fees).

## 2. The rule (primary, frozen) and the reported books

**Primary.** One trade a session at 15:55: buy 1 C and 1 P at K at their asks in the 15:55 quote. Either leg failing the
quote rule → no trade (counted, with the reason). Hold to cash settlement.
- entry = 100·STR_ask + 2f; payout = 100·|SET − K| − 2f; **P&L = payout − entry**; **return = P&L / entry**;
  win = P&L > 0.

**Reported books (no verdict)** — each with its own quote rule on the legs it buys **[pin]**:
- (a) **call only**: entry 100·ask_C + f, payout 100·max(SET − K, 0) − f.
- (b) **put only**: entry 100·ask_P + f, payout 100·max(K − SET, 0) − f.
- (c) **the side of the day's move**: the call if S(15:55) > S(09:31), else the put (equal → the put, as written);
  no S(09:31) print → no trade for (c) **[pin]**.
- (d) **the narrower leg**: the leg with the smaller (ask − bid)/mid at 15:55; a tie → the call **[pin]**. The chosen
  leg alone must pass the quote rule **[pin]**.
- **Entry at 15:50** and **entry at 15:58**: the whole primary rule re-run at that minute (S, K and both quotes at t).
- **Entry at the ask of the 15:56 quote**: K from S(15:55) as in the primary; both legs bought at the asks of the row
  stamped 15:56 (one minute's delay); the quote rule applied to the 15:56 row **[pin]**.
- **No exit fee**: payout = 100·|SET − K| (entry unchanged).
- **One-strike-OTM strangle**: the call at the next listed strike above K and the put at the next listed strike below K,
  both at their 15:55 asks, held to settlement; entry 100·(ask_C' + ask_P') + 2f, payout 100·(max(SET − K⁺, 0) +
  max(K⁻ − SET, 0)) − 2f.
- **FOMC, CPI and NFP days** separately (the primary on those sessions). FOMC = the scheduled statement dates in
  `../Edge search/H7_H8_H9/data/fomc_statements_2012_2026.json` (`scheduled`). CPI and NFP = BLS release dates: for
  2017-06 → 2021-12 the dates in the appendix (BLS archive pages, read 2026-10-24); from 2022-01 the repo's
  `data/macro_events_2022_2027.json` (the appendix's 2022 dates agree with it).
- **Robinhood's fee schedule** (`docs/FEES_ROBINHOOD.md`, committed in 6501f13 — present, so the line is reported): the
  primary's fills with Robinhood's SPXW fees in place of f: each bought leg pays $1.0403 when its ask is under $1.00 and
  $1.1303 at $1.00 and up (non-Gold); cash settlement $0. The PRIMARY stays at f = $1.28 each side, as the owner wrote.

## 3. Data and splits (committed here before anything is computed)

- **New data**: the 855 sessions 2017-01-03 → 2022-05-12 with a same-day SPXW expiry (Theta's SPXW expiration list),
  minus the 312 already read (V8, S03, S16b), minus the 11 half days (2017-07-03, 2017-11-24, 2018-07-03, 2018-11-23,
  2018-12-24, 2019-07-03, 2019-11-29, 2019-12-24, 2020-11-27, 2020-12-24, 2021-11-26), minus the 63 Jan–May 2017
  sessions: **470 sessions**, 2017-06-02 → 2022-05-12, listed in `sessions_new.csv` (step 0's lists: sha256
  `831442776bb17aa5…` remaining_sessions.csv, `3a3dfd0150515855…` sessions_2017-01-03_2022-05-12.csv). The list is
  confirmed against Theta's expiration list at fetch time; a session Theta no longer lists, or whose chain is not
  same-day PM SPXW, is dropped and named.
- **Gate sample: ODD calendar months — 236 sessions** (Mon 71, Tue 14, Wed 81, Fri 70; 2017 25, 2018 53, 2019 50,
  2020 46, 2021 44, 2022 18). **P&L sample: EVEN calendar months — 234 sessions** (Mon 75, Tue 3, Wed 80, Thu 3,
  Fri 73). No session is used twice.
- **No month-end session is in the new data**: every 2017-06 → 2022-04 SPXW month-end was read by V8 (or is a half day),
  and the five Jan–May 2017 month-ends are dropped. The G2 end-of-month row is therefore empty (section 4).
- **Previously read: 2022-05-13 → 2026-10-09**, on disk (`theta/data_full/chains/SPXW/<D>.parquet`, the same-day full
  chains; SPX prints `theta/data/index/SPX`), every full session with a same-day SPXW chain file (half days out).
  Every figure of sections 4 and 5 that runs is also reported there, labelled **PREVIOUSLY READ**; no pass or fail is
  judged there. Step 0 already read a cousin figure on it: mean |SET − K| / mean STR_ask = 0.815 (2022-05-13 →
  2026-10-09, at 15:58, 1,097 sessions; at the mid 0.870). If the gate fails, the previously-read report holds the gate's
  figures and the primary's P&L summary only (no books) **[pin]**.
- **Forward: 2026-10-12 on**, via the daily job, only if section 5 passes.
- **Ledger**: one HOLDOUT_LEDGER row (this commit).

## 4. Gate (gate sample only; run once; nothing else runs if it fails)

Sessions: the gate sample's sessions on which the primary takes a trade (both 15:55 legs pass the quote rule) **[pin]**,
in calendar order; the no-trade sessions are counted with their reasons.

- **G1, pricing (no fees).** **R_ask = mean(|SET − K|) / mean(STR_ask)**, a ratio of means. Also reported: R_mid
  (= mean|SET − K| / mean STR_mid), the mean of per-session ratios |SET − K|/STR_ask, their median, and the share of
  sessions with |SET − K| > STR_ask.
  - Interval **[pin]**: audit_lib's moving-block draws (`../Compass phase 3/backtest_audit/audit_lib.py`
    `block_draws(n, 20)`: 20-session overlapping blocks, 2,000 draws, house seed 20261022 + 7919·20), each draw's
    session weights W (`weights_from`), the ratio recomputed as (W·|SET − K|) / (W·STR_ask), and the 2.5th and 97.5th
    percentiles (`pct_ci`). "The lower bound" = the 2.5th percentile.
  - **Pass G1: R_ask ≥ 1.05 AND the lower bound > 1.00.**
- **G2, stability.** R_ask > 1.00 in at least **4 of the 6 years** 2017–2022 (2017 = its odd months from June, 2022 =
  Jan, Mar, May to the 12th), AND R_ask > 1.00 **in each expiry weekday separately**: Mon, Wed, Fri, with end-of-month as
  its own row. **[pin]** The rows are exclusive (a month-end session sits in the EOM row only); Tue/Thu sessions that are
  not month-ends (holiday shifts, the 2022 Tuesday dailies) are in G1 and the years, printed as an "other" row, not
  judged. **[pin]** A row with no session in the gate sample is not a condition (it cannot be above or below 1); the
  EOM row is empty here (section 3), so G2's weekday part is judged on Mon, Wed and Fri. The inclusive weekday table is
  printed beside.
- **Control (descriptive)**: the same R_ask (and its interval) for the one-strike-OTM strangle: mean(max(SET − K⁺, 0) +
  max(K⁻ − SET, 0)) / mean(ask_C(K⁺) + ask_P(K⁻)), on the gate sessions where both strangle legs pass the quote rule.
  **[pin]** Read as "general" if the control's R_ask > 1.00, "ATM-only (possibly a pin or microstructure effect)" if
  the straddle's R_ask > 1.00 and the control's is not; reported whatever the gate's outcome.
- Also printed (no verdict): the Lifecycle-excluded sensitivity lines (section 0), the 10%-of-mid count, the SET-flag
  count.
- **If G1 or G2 fails:** GATE_REPORT.md is written and committed, and the rule work stops — no P&L on the new data, no
  books, no tuning, no forward. The final write-up says the study is closed.

## 5. P&L test (P&L sample; read once; only if the gate passes)

- **Before reading** (committed alone, after the gate): the MDE at 80% power, α = 0.05 one-sided,
  MDE = (z₀.₉₅ + z₀.₈₀) · SD / √n = 2.4865 · SD / √n, SD = the gate sample's per-trade return SD (sample SD, ddof 1),
  n = the P&L sample's trade count (counted from the 15:55 quotes alone, no SET read). If the MDE is above +8% per
  trade, a non-significant positive result counts as a FAIL.
- **Pass, all of:**
  1. mean return per trade after costs > 0;
  2. the 20-session block 95% lower bound > 0 (audit_lib `session_stats(S, N)`, S = the session's return, N = 1 for a
     traded session, 0 otherwise, calendar order; `ci_trade_b20`'s 2.5th percentile);
  3. the top-5 sessions' share of total profit ≤ 100% (Σ of the 5 largest session P&Ls in $ ÷ total P&L in $);
  4. ≥ 300 trades.
- **Stated before anything is computed:** the P&L sample holds **234 sessions**, so it can hold at most 234 trades.
  Condition 4 (≥ 300 trades) cannot be met on it. The owner's condition is kept as written; so if the gate passes, the
  P&L test is still run and reported in full, and it FAILS on condition 4 whatever the returns.
- **Also reported:** the deflated Sharpe ratio at N = 1 and N = 16,000 **[pin]** (Bailey & López de Prado 2014, on
  per-trade returns: SR = mean/sd (ddof 1), T trades, skew γ₃, kurtosis γ₄ (not excess); SR₀ = 0 at N = 1, else
  SR₀ = √V·((1 − γ)Φ⁻¹(1 − 1/N) + γΦ⁻¹(1 − 1/(N·e))), γ = 0.5772, V = 1/(T − 1); DSR = Φ((SR − SR₀)·√(T − 1) /
  √(1 − γ₃·SR + (γ₄ − 1)/4·SR²))); win rate, average win and loss, median, biggest win and loss (date and K), profit
  factor (Σ wins / |Σ losses|), max drawdown ($, on the cumulative per-trade P&L from 0 in calendar order) and the
  longest drawdown (sessions from a peak to the next new high, or to the end); by year and by weekday; every reported
  book of section 2, labelled.

## 6. Forward (only if section 5 passes)

The primary rule added to the daily job as paper, SET from Cboe's file, else UW's daily bar (flagged); the forward N for
80% power committed before the first forward session. (Given section 5's condition 4, this section will not run.)

## 7. Integrity

- Re-derive ≥ 50 sessions (K, both 15:55 quotes, SET, P&L) from the raw files with separate plain-loop code (no
  polars, no shared helper); 0 differences required. **[pin]** 60 sessions, seeded (20261024) from the sessions the
  report uses (gate sample; and the P&L sample if it runs; and 10 previously-read sessions).
- Lookahead check on 10 sessions: every input stamped after 15:55 blanked (chain rows and SPX prints), SET kept;
  nothing in the primary may change. Control: read the 15:56 quote instead; K or the entry should change.
- Costs in $ per contract; units asserted at every boundary (section 1).

## 8. Files

`research_notes/Compass Close/`: this prereg, then the fetch (raw data under the scratchpad's
`theta/data_full/chains_close/SPXW/<D>.parquet`, never committed), GATE_REPORT.md, PNL_REPORT.md only if the gate
passes, then COMPASS_CLOSE_FINAL.md and .pdf. Stop rule: if the gate or the P&L test fails, the study is closed.

**Fetch [pin]** (the owner's "do em all"): one ThetaData SDK login (the daily job's `--source sdk` path), never
00:00–01:45 or 19:40–20:30 New York; at most 3 requests in flight; one request a session,
`option_history_quote('SPXW', expiration=D, date=D, interval='1m', strike='*', right='both', start_time=15:45,
end_time=16:00)`; kept: the strikes from 4 listed steps below the lowest to 4 above the highest of S(15:45) … S(16:00)
(which holds ATM ± 3 around the 15:45 print, K, K ± 1 at every entry minute), plus a per-session list of every listed
strike (for K) and the answer's roots and expirations; an empty or denied answer logged and retried, never filled in.

## Appendix: BLS release dates used for CPI and NFP, 2017-06 → 2021-12

Read 2026-10-24 from the BLS release archives (https://www.bls.gov/bls/news-release/cpi.htm and
https://www.bls.gov/bls/news-release/empsit.htm; each date from the archive file name, cpi_MMDDYYYY / empsit_MMDDYYYY).

CPI: 2017-06-14, 2017-07-14, 2017-08-11, 2017-09-14, 2017-10-13, 2017-11-15, 2017-12-13, 2018-01-12, 2018-02-14,
2018-03-13, 2018-04-11, 2018-05-10, 2018-06-12, 2018-07-12, 2018-08-10, 2018-09-13, 2018-10-11, 2018-11-14, 2018-12-12,
2019-01-11, 2019-02-13, 2019-03-12, 2019-04-10, 2019-05-10, 2019-06-12, 2019-07-11, 2019-08-13, 2019-09-12, 2019-10-10,
2019-11-13, 2019-12-11, 2020-01-14, 2020-02-13, 2020-03-11, 2020-04-10, 2020-05-12, 2020-06-10, 2020-07-14, 2020-08-12,
2020-09-11, 2020-10-13, 2020-11-12, 2020-12-10, 2021-01-13, 2021-02-10, 2021-03-10, 2021-04-13, 2021-05-12, 2021-06-10,
2021-07-13, 2021-08-11, 2021-09-14, 2021-10-13, 2021-11-10, 2021-12-10.

NFP (Employment Situation): 2017-06-02, 2017-07-07, 2017-08-04, 2017-09-01, 2017-10-06, 2017-11-03, 2017-12-08,
2018-01-05, 2018-02-02, 2018-03-09, 2018-04-06, 2018-05-04, 2018-06-01, 2018-07-06, 2018-08-03, 2018-09-07, 2018-10-05,
2018-11-02, 2018-12-07, 2019-01-04, 2019-02-01, 2019-03-08, 2019-04-05, 2019-05-03, 2019-06-07, 2019-07-05, 2019-08-02,
2019-09-06, 2019-10-04, 2019-11-01, 2019-12-06, 2020-01-10, 2020-02-07, 2020-03-06, 2020-04-03, 2020-05-08, 2020-06-05,
2020-07-02, 2020-08-07, 2020-09-04, 2020-10-02, 2020-11-06, 2020-12-04, 2021-01-08, 2021-02-05, 2021-03-05, 2021-04-02,
2021-05-07, 2021-06-04, 2021-07-02, 2021-08-06, 2021-09-03, 2021-10-08, 2021-11-05, 2021-12-03.
