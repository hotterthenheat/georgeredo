# Compass EMA ladder — pre-registration

Written 2026-10-23 and committed alone, before any option chart, signal, trade or P&L of this rule is computed. Before this
file was written only these were read: the definitions and the code of the scanner study (PREREG_COMPASS_SCANNER.md
`142fcf4`, `scanner_lib.py`), `audit_lib.py`'s bootstrap, PREREG_FEATURES.md's SD1 / D1 definitions and its fetch README,
the Edge-search ledger, the file schemas (one file of each kind, SPY 2025-01-06: the chain, the 1-minute bars, UW
`spot-exposures`, UW `net-prem-ticks` — the first three rows of each were printed while reading the schema; no value was
paired with any later price) and the data coverage (which files exist per name and date, file names only). No option price
was read against an outcome. The owner's change of contract (section 3, "best R/R") arrived before this file was committed
and is part of it.

The code is written after this commit; its sha256 is listed in the report, and any later change to it is a deviation.

**The owner's idea, verbatim**: "if you look at the 1 min options chart and it breaks the ema it's gonna go to the 5m and
if it breaks that then the 15 and so on so fourth" … "try the 9 and maybe gex will work with this one or call and put
premiums will work". The owner's contract change, verbatim: "don't just buy at the money, they're gonna be expensive, just
buy the best r/r contracts".

**A preview before the study (the owner's request, 2026-10-23: "test 1 month data first so i can see the results fast").**
After this commit, all 13 versions are run on ONE month, 2025-03 (21 full sessions; a Pick month, not one of the 28
held-out months), with V1 (EMA 9, L1) labelled as the preview's base, and committed as PREVIEW_2025-03.md, no verdict. Those
21 sessions stay in Pick: the BASE choice (section 6) is then made by an author who has seen one month of Pick. Stated
here so it is not hidden; nothing in this file changes after the preview.

---

## 1. Data, universe, sessions

| item | source | span |
|---|---|---|
| option quotes | ThetaData 1-minute NBBO chains, `$SP/theta/data_full/chains/{SPY,QQQ,IWM}/<D>.parquet` (columns timestamp, strike, right, bid, ask) — same-day expiry contracts | SPY, QQQ 2022-11-11 → 2026-10-21; IWM 2024-04-19 → 2026-10-21 (the 2026-10-22 files are not used) |
| underlying | ThetaData 1-minute bars `$SP/theta/data/underlying/{SPY,QQQ,IWM}/<D>.parquet` | as above |
| GEX (V7, V9) | UW `spot-exposures`, `$SP/features_data/uw/spot_exposures/<NAME>/<D>.parquet`, field `gamma_per_one_percent_move_oi` (SD1's field), sign as UW gives it | files from 2023-12-08 |
| premium (V8, V9) | UW `net-prem-ticks`, `$SP/features_data/uw/net_prem_ticks/<NAME>/<D>.parquet`, fields `net_call_premium`, `net_put_premium`, `tape_time` (PREREG_FEATURES D1) | files from 2023-11-21 |

- `$SP` = `/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad`. No vendor fetch of any kind.
- **Universe**: SPY, QQQ, IWM, 0DTE only (the contracts expiring the session's own date). The verdict is POOLED across the
  three names; per-name lines are descriptive.
- **Sessions**: full NYSE sessions only (`scanner_lib.full_sessions`: half days out — the 15:58 flat and the 09:45–15:30
  window assume a 16:00 close). A name trades on a session only when its chain file and bar file exist.
- **Clock**: New York. Minute m = 0 is 09:30. A 1-minute underlying bar stamped t covers t to t+1, so at minute m the last
  completed bar is the one stamped m − 1. A chain row stamped m is the NBBO at minute m (the house convention of every
  earlier study; the stored 09:30 rows are unquoted).

## 2. The option charts (the signal is read on the ATM contract's own chart)

- **Valid mid**: a row with bid > 0 and ask ≥ bid gives mid = (bid + ask)/2. A row with bid ≤ 0, ask < bid (crossed),
  a null field, or no row at all → the mid is missing and the chart CARRIES FORWARD the last valid mid of that contract
  from earlier today; before the contract's first valid mid of the day it has no chart.
- **1-minute candle**: the candle stamped t covers t to t+1 and completes at minute t+1; its close is the (carried) mid of
  the row stamped t+1. So the closes are indexed by their completion minute c = 1 … 389 (rows 09:31 … 15:59).
- **Higher timeframes** (clock-aligned): the 5-minute candle j covers [09:30 + 5j, 09:35 + 5j), completes at c = 5(j+1)
  and closes at the 1-minute close of minute c (the mid of its last minute). 15-minute: c = 15(j+1). 30-minute
  (c = 30(j+1)) is defined but no frozen version uses it (no L4). A higher candle exists once its completion close exists.
- **EMA(n)**, n = 9 or 20, α = 2/(n+1), per timeframe: seeded at that timeframe's first available close of the day
  (EMA₁ = close₁), then EMA_k = α·close_k + (1 − α)·EMA_{k−1}. Only completed candles enter; at minute m a timeframe's
  "last completed candle" is the latest with completion c ≤ m. Nothing after m is read.
- **Above** (state): the last completed candle's close > its EMA (strict).
- **Break** of a timeframe at minute m: a candle of that timeframe COMPLETES at m with close > EMA, and the previous
  completed candle of that timeframe had close ≤ its EMA. The first candle of a day cannot break (no previous candle).
  A put signal is the PUT chart breaking ABOVE its EMA (a rising put premium); a call signal the CALL chart breaking above.
- **Which charts are watched**: at minute m, S(m) = the close of today's latest bar stamped ≤ m − 1 (normally m − 1; none →
  the minute is not evaluated). The ATM strike K(m) = the strike, among the strikes present in today's chain file, nearest
  S(m) (ties → the lower strike). The watched charts at m are the call and the put at K(m), each built from 09:31 for that
  strike (so a strike that becomes ATM later in the day is read on its own full-day history; its state at m is exactly
  what it would have been had it been watched all day). A strike change between minutes is not itself a break: a break
  needs that chart's own candle completing at m to cross.

## 3. Entries — the ladder, and the execution contract ("best R/R")

**Ladder versions** (evaluated on each side's chart at K(m), at minute m):
- **L1**: a 1-minute break at m.
- **L2**: 1-minute above AND 5-minute above, with a break at m on the 1-minute or the 5-minute (a 1-minute break while the
  last completed 5-minute candle is above its EMA, or a 5-minute break while the 1-minute is above). Exactly: A1 ∧ A5 ∧
  (B1 ∨ B5).
- **L3**: A1 ∧ A5 ∧ A15 ∧ (B1 ∨ B5 ∨ B15).
- **Entry window**: m from 09:45 to 15:30 inclusive. One open position per name (call or put). If the call side and the
  put side both qualify at the same m → no trade, counted ("both sides"). A break is "fresh" only at the minute its candle
  completes, so every entry needs a break at its own minute; after an exit at minute x the next entry needs a break at a
  minute m > x.

**The execution contract (the owner's change)** — the signal is read on the ATM chart, but the contract BOUGHT is the
"best R/R" same-day contract on the signal's side (calls for a call signal, puts for a put signal), chosen at m from the
chain row stamped m:
- Candidates: every same-day contract of that right with **ask > bid > 0** at row m, **spread% = (ask − bid)/mid ≤ 12%**,
  and **0.15 ≤ |delta| ≤ 0.50** (inclusive).
- **Delta and IV**: Black-Scholes, S = S(m), the strike, T = (16:00 − m) in calendar minutes ÷ 525,600, r = 0.045, q = 0;
  the IV solved by bisection on [0.0001, 10] from the row-m mid (`scanner_lib.bs_delta`'s method); a mid with no vol
  (at or below the discounted intrinsic or at or above the bound) → fails the delta filter.
- **M** = the remaining implied move = the ATM straddle mid at m = the call chart's close + the put chart's close at K(m)
  at completion m (section 2: the row-m mids, carried forward if a row is invalid). No value on either → no trade, counted.
- **R/R** = (BS(S(m) + M for a call / S(m) − M for a put, K, T, IV) − ask) ÷ ask, the BS value at the moved price with the
  SAME IV and the SAME clock T.
- **Pick**: the largest R/R; ties → the smaller spread%, then the strike nearer S(m) (smaller |K − S(m)|), then the lower
  strike. No contract passes → no trade, counted ("no R/R contract").
- **Fill**: bought at the ASK of that contract's row stamped m.

## 4. Exits

- **Signal exit**: a completed candle of the entry's TOP timeframe (L1: 1-minute, L2: 5-minute, L3: 15-minute) closes
  BELOW its EMA (strict), read on the SIGNAL chart — the ATM contract at entry, (K(m_entry), side), fixed for the trade
  (not the moving ATM) — the first such candle completing at a minute c > m_entry. Sold at the BID of the EXECUTION
  contract's row stamped c.
- **15:58**: if still open, sold at the bid of the execution contract's row stamped 15:58 (a top-timeframe trigger at
  c = 15:58 is the same price). First trigger wins.
- **The exit bid**: the row's bid if the row exists with a non-null bid; otherwise the last non-null bid in the 10 minutes
  before; none → 0 (`scanner_lib.exit_quote`). **Bid 0 → exit value 0, and no exit fee** (nothing is sold).
- **Costs**: $0.68748 a contract each way ($0.65 + ORF $0.01248 + OCC $0.025; PREREG_PICKER.md). One contract.
  Return r = ((exit bid − entry ask) × 100 − fee_in − fee_out) ÷ (entry ask × 100); $ = the numerator.
- **Mid-to-mid, no fee** (signal against cost, descriptive): entry mid at row m, exit mid at the exit row (valid-mid rule of
  section 2, the 10-minute fallback, else 0), r_mid = (exit mid − entry mid) ÷ entry mid.

## 5. The versions (13, all listed; each judged as stated in section 6; every unlisted part unchanged)

| id | version |
|---|---|
| V1 | EMA 9, L1 |
| V2 | EMA 9, L2 |
| V3 | EMA 9, L3 |
| V4 | EMA 20, L1 |
| V5 | EMA 20, L2 |
| V6 | EMA 20, L3 |
| V7 | BASE + GEX filter: trade only when G < 0, G = `gamma_per_one_percent_move_oi` of the latest UW `spot-exposures` row of the name with `time` ≤ m:00 and `start_time` ≤ m − 1 minute (its minute completed by m), today's rows only, sign as UW gives it; G ≥ 0 or no row → no trade, counted ("GEX") |
| V8 | BASE + premium filter: P(m) = Σ (`net_call_premium` − `net_put_premium`) over today's `net-prem-ticks` rows with `tape_time` from 09:30 to m − 1 minute (minutes completed by m; PREREG_FEATURES D1's "last complete minute before entry"). A call only if P > 0, a put only if P < 0; P = 0 or no file → no trade, counted ("premium") |
| V9 | BASE + both filters (V7 and V8) |
| V10 | BASE + the 14:00 exit (X3): entries only at m ≤ 13:59; a position still open at 14:00 is sold at the bid of its row stamped 14:00 |
| V11 | BASE + spread 10%: the execution candidates' spread% ≤ 10% (in the filters, as the scanner's E1) |
| V12 | BASE + spread 3%: spread% ≤ 3% in the filters |
| V13 | BASE executed in the ATM contract: the contract bought is the signal chart's own contract (K(m), side), at the ask of its row stamped m, which needs ask > bid > 0 (else no trade, counted "ATM no quote"); no spread or delta filter; exits as BASE |

The filters of V7–V9 are applied after the side is determined (the "both sides" rule first) and before the contract pick.
The filter's no-trade does not change the position state (no entry was made).

## 6. Splits, selection, eligibility, finalists, the final read

- **Holdout** = the scanner's 28 held-out months, reused exactly (PREREG_COMPASS_SCANNER.md §3, drawn by its seeded code,
  asserted on import by `scanner_lib`): 2017-06, 2017-09, 2017-10, 2018-01, 2019-07, 2019-08, 2020-06, 2020-08, 2020-11,
  2020-12, 2021-01, 2021-03, 2021-05, 2021-11, 2022-04, 2022-12, 2023-05, 2023-11, 2024-05, 2024-06, 2024-07, 2024-08,
  2024-11, 2025-08, 2025-11, 2026-03, 2026-04, 2026-08. Of the option span these are 269 full sessions (2022-12-01 →
  2026-08-31). **A guard is implemented first**: every reader of a chain, bar or UW file raises if the date is in a
  held-out month, until the one holdout read switches it off.
- **Main span** (V1–V6, V10–V13): non-held full sessions 2022-11-11 → 2026-10-21 (710): **Pick = the first 60%** (n_pick =
  ⌊0.6 n + 0.5⌋) = 426 sessions, 2022-11-11 → 2025-04-02; **Check = the last 40%** = 284 sessions, 2025-04-03 → 2026-10-21.
  (The same dates as the scanner's option layer.) IWM trades only from 2024-04-19 (133 Pick sessions, 284 Check).
- **Filter span** (V7–V9, and BASE re-run on it for their comparison): non-held full sessions 2023-12-08 → 2026-10-21
  (507; the GEX files begin 2023-12-08 — the owner's 2023-11-21 start would add only 2023-12-01 … 12-07, five sessions
  without a GEX file, so all three filters and their base share the GEX span; 2023-11 is held out anyway): **Pick** 304
  sessions 2023-12-08 → 2025-07-31, **Check** 203 sessions 2025-09-02 → 2026-10-21; its holdout 206 sessions.
- **BASE** = the one of V1, V2, V3 (the 9-EMA ladders) with the largest Pick mean % per trade after costs (pooled names,
  main span). Ties → the lower ladder (L1 before L2 before L3).
- **Statistics**: per session s in date order (sessions of the split; a session with no trade counts as zero, every name
  together): S_s = Σ r, N_s = trades, D_s = Σ $. Mean % per trade = Σ S ÷ Σ N; mean $ per trade = Σ D ÷ Σ N. Interval:
  `audit_lib.block_draws(n, 20)` (moving block, 20-session blocks, 2,000 draws, seed 20261022 + 7919 × 20), `weights_from`,
  ratio (W·S)/(W·N) per draw, percentile interval (95%: 2.5 / 97.5; at 1 − α: α/2, 1 − α/2). A gain over a base uses the
  same draws for both arms: Δ_b = (W·S₁)/(W·N₁) − (W·S₀)/(W·N₀). Also reported: win rate (r > 0), average win, average loss,
  exit-reason shares (signal exit / 15:58 / 14:00), trades per session, by hour of entry, per name, the mid-to-mid no-fee
  mean, worst day, max drawdown of the cumulative $, the no-trade counts by reason, and for the R/R contract the
  distribution of |delta|, premium (ask) and R/R at entry.
- **Eligible**:
  - V1–V6 (judged against zero, not a base): the Pick mean % after costs with its 95% block-20 interval's lower end > 0,
    AND the Check mean % > 0.
  - V7–V13 (judged against BASE on the same sessions; V7–V9 on the filter span): the gain over BASE on Pick with its 95%
    interval's lower end > 0, AND on Check both the gain's mean > 0 and the version's own mean % after costs > 0 (the
    stricter reading of "positive mean on Check").
- **Finalists**: at most 3 eligible versions, the largest Check mean % per trade first.
- **The final read, once, on the holdout** (only if at least one version is eligible): k = the number of finalists. Each
  finalist is read on the holdout sessions of its own span (main span: 269 sessions; filter span: 206), pooled names, and
  PASSES iff its mean % per trade after costs > 0, its 20-session block interval at level 1 − 0.05/k (percentiles 2.5/k and
  100 − 2.5/k) has lower end > 0, and it has ≥ 100 holdout trades. Per-name rows descriptive. No tuning after the read.
  **If no version is eligible there is NO holdout read**: that is reported and the study stops with the holdout unopened.
- One row per rule read on the holdout is appended to `research_notes/Edge search/LEDGER.md`; none if there is no read.

## 7. Integrity

- A separate plain-loop verifier (no numpy vectorisation, no shared code with the study's library) re-derives from the raw
  Parquet files at least 30 trades (charts, EMAs, the break, K(m), the R/R pick, entry ask, exit row, exit bid, return) and
  at least 20 evaluated no-trade minutes (why no entry); 0 differences required.
- Deterministic: no random draw except the seeded bootstrap.
- Commits: this file alone; then the preview (PREVIEW_2025-03.md); then, on the owner's go, the code and
  EMA_LADDER_REPORT.md.

## 8. Prior reads — which months and names earlier studies opened

**No month and no name of this study is unread for other rules.** The full month-by-month and name-by-name table is
PREREG_COMPASS_SCANNER.md §12. For this study's span: SPY and QQQ 0DTE chains every month 2022-11 → 2026-10 (IWM 2024-04 →),
the held-out months included, were read by Steps 1–5, S01/S02 (the Quick Scalps 0DTE long calls/puts), S10/S12b, the
lifecycle Tier I study, V5, phase E/F, the picker, the Compass features study and the engine audits; the after-hours study
2025-10 →; the forward tracker 2026-10-12 → 21. The scanner study read selection data only (its gate failed before any option
P&L) on the non-held 2023-12 → 2026-10 sessions. Of the inputs of V7–V9: the features study's GEX check (Δ_GEX −0.0604
implied moves [−0.1327, +0.0354]) dropped SD1 untested, and its D1 (net premium since 09:30, as a direction feature) failed
its screen (−0.40 [−4.29, +2.73]). A related family on the UNDERLYING was read before: S06's "5-min EMA cross" trigger
(signed forward returns, SPY/QQQ/IWM bars 2017-06 → 2026-10-09). No study here has read an EMA break on an option's own
mid chart. The 28-month holdout is unopened for THIS rule only.
