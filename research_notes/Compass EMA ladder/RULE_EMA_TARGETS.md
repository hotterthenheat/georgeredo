# Compass EMA ladder — the "nearest EMA" take-profit rule (preview rule)

Written 2026-10-23 and committed alone, before any chart, signal, trade or P&L of THIS rule is computed. It is built on the
committed EMA ladder code (PREREG_EMA_LADDER.md `0dd8c5d`, `ema_lib.py` as committed in `cb79c23`); the committed files
are not changed — new code goes in new files. Everything not stated here is as in PREREG_EMA_LADDER.md.

**The owner's rule, verbatim**: "take profits are the nearest EMAs".

**PREVIEW — one month each, no verdict.** This is a quick look, not a study: no interval, no eligibility, no holdout.

## 1. Data, names, clock

- SPY, QQQ, IWM, 0DTE only, pooled with per-name lines; the same files as PREREG_EMA_LADDER §1 (ThetaData 1-minute NBBO
  chains and 1-minute underlying bars). No vendor fetch. Full sessions only (`scanner_lib.full_sessions`).
- Minute m = 0 is 09:30; a chain row stamped m is the NBBO at minute m; S(m) = the close of the latest bar stamped ≤ m − 1.
- The held-out months (the scanner's 28) are never read: `ema_lib.guard` raises on any of them.

## 2. Charts (exactly as `ema_lib` builds them)

- The ATM option's own chart: the CALL chart for a call, the PUT chart for a put, at K(m) = the chain strike nearest S(m)
  (ties → the lower strike; `ema_lib.atm_index`). Mid-based (bid > 0, ask ≥ bid), the last valid mid carried forward
  (`ema_lib.carried_mid`); the 1-minute close completing at c is the carried mid of row c (c = 1 … 389).
- Clock-aligned 5-, 15- and 30-minute candles: completion c = tf·(j+1), close = the 1-minute close of minute c
  (30-minute: c = 30, 60, …, 360).
- EMA 9 on each timeframe, α = 2/(n+1) = 0.2, seeded at that timeframe's first available close of the day, then
  EMA_k = α·close_k + (1 − α)·EMA_{k−1}; completed candles only. At minute m a timeframe's current EMA value is the value
  after its last completed candle (completion ≤ m); a timeframe with no completed candle yet has no value (e.g. the
  30-minute before 10:00).

## 3. Entry

At minute m, 09:45 ≤ m ≤ 15:30, for each side (call chart, put chart at K(m)) the side QUALIFIES when both hold:
1. **1-minute break**: the 1-minute candle completing at m closes above its 9 EMA (strict), and the previous completed
   1-minute close was ≤ its EMA (`ema_lib.ladder_states` B for the 1-minute, EMA 9).
2. **An EMA above**: at least one of the current 5-, 15-, 30-minute EMA values is above (strict) the chart's 1-minute
   close at m. **Target T** = the smallest such EMA value above that close (the nearest EMA above), fixed at entry.

Then, in this order (each skip counted by reason; a skip leaves the position state unchanged and the next minute is
evaluated):
- **Both sides** qualify at m → no trade ("both sides").
- **Cost check** (stated on the ATM chart, because the target is defined on the ATM chart; the same check for E1 and E2):
  the ATM contract of the side at row m needs ask > bid > 0 (else "ATM no quote"), and the trade is skipped unless
  **T − ATM mid(m) ≥ ATM ask(m) − ATM bid(m)** ("gap < spread"), with mid(m) = (bid + ask)/2 of row m.
- **Execution** (two versions, each run on its own, each with its own position state):
  - **E1** = the ATM contract itself (K(m), side), vetoed if its spread (ask − bid)/mid > 3% ("E1 spread > 3%").
  - **E2** = the best-R/R contract exactly as PREREG_EMA_LADDER §3 defines it (same right, ask > bid > 0,
    0.15 ≤ |delta| ≤ 0.50, M = the ATM straddle on the carried mids at m, R/R at the moved price with the same IV and clock,
    the same tie rules; `ema_lib.pick_rr`) with the spread cap **3%** inside its candidate filter. No M → "no implied move";
    no candidate → "no R/R contract".
- **Fill**: bought at the ASK of the execution contract's row stamped m. Fees $0.68748 a contract each way. One contract.

One position per name. After an exit at minute x the next entry needs a fresh 1-minute break completing at a minute m > x.

## 4. Exit — the first of, on the SIGNAL chart (the ATM contract at entry, (K(m_entry), side), fixed for the trade)

Checked on each completed 1-minute candle c = m_entry + 1, …, 15:58:
- **(a) take profit**: the chart's 1-minute close at c ≥ T.
- **(b) stop**: the chart's 1-minute close at c is below its 1-minute 9 EMA (strict).
- **(c) 15:58**: still open at c = 15:58 (388).
- If (a) and (b) both hold at the same c, it is counted as (a) (the listed order). A trigger at c = 15:58 is labelled by
  its trigger; the price is the same row.
- Sold at the BID of the EXECUTION contract's row stamped c. Bid missing → `scanner_lib.exit_quote` (the last non-null
  bid in the 10 minutes before; none → 0); bid 0 → value 0 and no exit fee.
- Return r = ((exit bid − entry ask) × 100 − fee_in − fee_out) ÷ (entry ask × 100); $ = the numerator.
  Mid-to-mid, no fee: the execution contract's entry mid at row m against its exit mid at row c (the same fallback).

## 5. Months

- **2025-02** (fresh for this rule): its full sessions; asserted not a held-out month and inside the main Pick split
  (2022-11-11 → 2025-04-02). It is the preview.
- **2025-03** beside it for comparison — already seen once under the ladder rule (PREVIEW_2025-03.md `cb79c23`).

## 6. What is reported (per version per month)

Trades; skips by reason; mean % and mean $ per trade after costs; win rate (r > 0); average win / average loss (% of
premium); exit-reason shares (target / stop / 15:58); median holding minutes (x − m); mid-to-mid no-fee mean; median
|delta| at entry (E1: the ATM contract's, by the same IV/delta method, descriptive) and median premium (ask); per name
(SPY / QQQ / IWM) mean %. Also, descriptively, the number of 1-minute breaks that had no EMA above (not a signal).

**Integrity**: a separate plain-loop script (no numpy arrays, no `ema_lib` / `scanner_lib` code; the raw Parquet rows
read and looped in Python) re-derives 10 trades per month — the ATM strike, the charts and EMAs, the break, T, the cost
check, the execution contract, entry ask, the exit minute and reason, the exit bid and $ — 0 differences required.

Label on every table: **PREVIEW — one month each, no verdict**.
