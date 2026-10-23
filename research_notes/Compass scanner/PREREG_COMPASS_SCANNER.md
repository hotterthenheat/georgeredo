# Compass scanner — pre-registration

Written 2026-10-23 and committed alone, before any forward return of the underlying, any option exit or any P&L of the
Compass scanner is computed. Before this file was written exactly three things were computed: the holdout draw (section 3,
by the code printed there), the session calendar and the Pick / Check splits (dates only), and the owner's answer-3
open-interest decision (section 2.3), which used SELECTION data only — the scanner's score on 1-minute bars, the chain
quotes at the onset minute, the published open interest and the previous session's contract volume — and counted how
often the contract picked changes. No exit, no forward bar after a signal, no option price after entry was read for it.

The code lives in this folder and is committed with the results (this file is committed alone); its state at this
commit, by sha256 — `scanner_lib.py` (calendar, holdout, splits, the scanner, chains, the pick), `oi_decision.py` (section
2.3, output `out/oi_decision.json`), `signal_check.py` (section 6, written and not run) and `verify_scanner.py` (section
11, not run):
  - `scanner_lib.py` sha256 `29820045abf1e730359d76139b8c953eb2787742b3a0b84d2d3de7263ee35116`
  - `oi_decision.py` sha256 `48b43e9bca4ed8e2195daae05e0b31c8d22cf71ac74079d245f7714f4a9a9e89`
  - `signal_check.py` sha256 `d930b6b1fc33da7225c86b733568ac7ad7e99e646a5e07bcab9765ee6b9370ca`
  - `verify_scanner.py` sha256 `292cbb0b516f2ad345059890f3dbd40c7e05053efad209b2bf8bf12e947de15b`
  - `out/oi_decision.json` sha256 `30aec73ee7f457c1acb6e3e573e3e5c95597ac83b6a49247fd05842fdd0ba804`

Any later change to these files is listed as a deviation in the report.

**Deviations before this commit.** (i) A smoke test of the scanner computed the SCORE of SPY on 2024-06-04 (a held-out
month, which was drawn just before); no forward bar, chain or outcome of that day was read. (ii) A first run of
`oi_decision.py` hung in its process pool and was killed with no output; the run reported is the second, unchanged.

**What the author had read before writing this file** (disclosed because it bears on how virgin the data are). The
research registry of 2026-10-14/16 (`research/compass/registry.jsonl`, last at `75c29c9^`), whose headline results
include S01–S04, S06 and S09 on the owner's earlier "Quick Scalps" baseline — a rule of the same family as the Compass
scanner (RSI(14) crossing 55/45, VWAP side, relative volume, 5-minute structure, delta 0.30–0.60 nearest 0.45, spread
under 12%): its signal had no forward value on SPY/QQQ/IWM over 2017-06 → 2026-10-09 (S04: −1.27 bp at 30 minutes on
SPY, fired after a +10 to +14 bp move in the prior 30 minutes), and its 0DTE option trades lost (S01: −$4.19 a trade
[−5.68, −2.81]; S09 on SPXW −$46.18). PREREG_FEATURES.md (`a2e14e4`), its INVENTORY.md (`04ce685`), the Edge-search
ledger and queue, `audit_lib.py`, `fcommon.py`, the fee sections of PREREG_PICKER.md / PREREG_SPXW.md. No figure of the
Compass scanner itself was seen.

---

## 1. The rule, v0 (frozen) — the owner's section 1, word for word

```
============================================================
1. The rule, v0 (frozen)
============================================================
Clock: New York time. Bar stamped t covers t to t+1. At minute m the last completed bar is the one stamped m−1. Every indicator uses only bars completed by m.

Bars: regular-session 1-minute bars (09:30–15:59) from sessions within the last 3 calendar days, including today. Signals need ≥ 30 bars.

RSI(14), simple average (not Wilder):
  Δi = ci − c(i−1) over the last 14 changes
  G = mean(max(Δi, 0)), L = mean(max(−Δi, 0))
  RSI = 100 − 100 / (1 + G/L)
  Fewer than 15 closes → 50; G = L = 0 → 50; L = 0 → 100.
RSI_1m = RSI(14) of 1-minute closes. RSI_5m = RSI(14) of the closes of completed clock-aligned 5-minute bars (09:30–09:34, 09:35–09:39, …) over the same sessions.

VWAP: session-anchored from today's 09:30.
  Σ((H+L+C)/3 · V) / ΣV over today's completed bars.

RVOL = last bar's volume ÷ mean volume of the 20 bars before it (1.0 with fewer than 2 bars).

Swings: bar i is a swing high if its high = max(high of bars i−2 … i+2), a swing low if its low = min(low of bars i−2 … i+2). Ties count. A swing is known only once bar i+2 is complete.
  Last two swing highs h1 (older), h2; lows l1, l2:
  HH: h2 > h1 · LH: h2 < h1 · HL: l2 > l1 · LL: l2 < l1
  trend = uptrend if HH and HL; downtrend if LH and LL; else range
  BOS = last close > latest swing high OR last close < latest swing low
  MSS = (uptrend AND last close < latest swing low) OR (downtrend AND last close > latest swing high)

Direction: bullish if last close ≥ VWAP AND RSI_1m ≥ 50, otherwise bearish (mixed readings default to bearish).
  trend_aligned = (bullish and uptrend) or (bearish and downtrend)
  volume_expanding = last bar's volume > previous bar's volume

Stretch filter: score = 0 if ANY of these:
  |C − VWAP| / VWAP > 1.8%
  bullish and RSI_1m ≥ 82; bearish and RSI_1m ≤ 18
  each of the last 3 bars has |close − open| / (high − low) > 0.75
  |C − latest swing| / C > 2.5% (swing low if bullish, swing high if bearish)
(C = last close.)

Score (sum, cap 100):
  RSI_1m > 55 (bull) / < 45 (bear) ............. +15
  RSI_5m > 52 (bull) / < 48 (bear) ............. +15
  C > VWAP (bull) / C < VWAP (bear) ............ +15
  RVOL ≥ 1.5 → +15; ≥ 1.2 → +8
  volume_expanding ............................. +10
  trend_aligned ................................ +15
  BOS (either direction) ....................... +10
  MSS (either direction) ....................... +5
Grades: ≥ 90 A+, 80–89 A, 70–79 B, 60–69 C, else IGNORE. v0 trades score ≥ 80 only.

Entry:
- Score evaluated every minute 09:31–15:30.
- Enter at the ASK of the chain quote stamped m, the minute the signal bar completes.
- One contract. One open position per name at a time. After an exit, a new entry needs the score to drop below 80 on some bar first (a fresh crossing).

Contract (calls if bullish, puts if bearish), from the first 4 listed expirations, or 0DTE only per step 0:
- Filters, all must hold:
  - open interest ≥ 250 (that morning's published OI);
  - volume ≥ 100 (previous session's contract volume; point-in-time stand-in for intraday volume, stated as a deviation);
  - spread% = (ask − bid) / mid ≤ 12% at the entry quote;
  - 0.30 ≤ |delta| ≤ 0.60, Black-Scholes delta solved from the entry mid, r = 0.045, no dividend, T to the expiry's 16:00;
  - ask > bid > 0.
- Pick: the contract with the largest tuple, compared in order:
  1. liquidity = min(vol/100, 5) + min(OI/250, 5)
  2. OI
  3. volume
  4. delta_score = 1 − ||Δ| − 0.45| / 0.15
  5. (1 − spread%/0.12) + 1 / (1 + |DTE − 7|)
- No contract passes → no trade (counted).

Underlying targets: E = last close at entry.
  Bullish: T1 = E × 1.0025, T2 = E × 1.005, T3 = E × 1.01
  Bearish: T1 = E × 0.9975, T2 = E × 0.995, T3 = E × 0.99

Exit v0, checked on each completed bar after entry, first trigger wins, sold at the BID of the quote stamped when that bar completes:
  (a) target: bar high ≥ T1 (bull) / bar low ≤ T1 (bear)
  (b) invalidation: bar closes below VWAP or below the latest swing low (bull); above VWAP or above the latest swing high (bear)
  (c) 15:58: flat; nothing is held to the close.
  If the bid is 0, the exit value is 0.

Costs: $0.68748 per contract each way ($0.65 + ORF $0.01248 + OCC $0.025). Return per trade = (exit bid − entry ask) / entry ask, after fees, plus $ per trade.
```

---

## 2. Data decisions (the owner's step 0 and answers 1–8)

### 2.1 Universes and spans

| layer | universe | data | span |
|---|---|---|---|
| signal check (6) | **SPY, QQQ, IWM** | ThetaData 1-minute underlying bars, `$SP/theta/data/underlying/{SPY,QQQ,IWM}/` | 2017-06-01 → 2026-10-21 |
| option layer, PRIMARY (the verdict) | **SPY, QQQ, IWM**, 0DTE only (answer 1) | ThetaData 1-minute full NBBO chains `$SP/theta/data_full/chains/`; bars as above SPY/QQQ **2023-11-21** → 2026-10-21 (2.3); IWM 2024-04-19 → 2026-10-21 |
| option layer, SECONDARY "SPY/QQQ early span" (2.3) | SPY, QQQ, 0DTE, the rule without OI (2.3 (b)) | as above | 2022-11-11 → 2023-11-20; its own lines, never in the primary verdict |
| option layer, SECONDARY "singles" (answer 4) | AAPL, AMZN, GOOGL, INTC, META, MSFT, MU, NVDA, TSLA open; **AMD, AVGO held out** (section 3) | ThetaData expiry-day chains `$SP/theta/fetch_cache/chains_exp/<T>/<D>__<D>.parquet` (same-day files only), the 41-name bar cache `$SP/theta/fetch_cache/underlying/`, EOD volume `$SP/theta/fetch_cache/eod_all/<T>/` | expiry days only, 2022-11-11 → 2026-10-21 ("no OI filter, expiry days only, 2022-11 →"); its own verdict line, never in the primary verdict |
| variant G1 (answer 7) | SPY's signals traded in **SPXW** | `$SP/theta/data_full/chains/SPXW/`; official SPX close from `data/official_closes/cboe_SPX_History_2026-10-22.csv` | as SPY |

- The span ends 2026-10-21 (the owner's "2026-10-21"); the 2026-10-22 files on disk for SPY/QQQ/SPXW are not used.
- The 1–7 DTE sample is not used (answer 1). "From the first 4 listed expirations" is replaced by the expiry-day (0DTE)
  contracts alone; the fifth tuple element's 1/(1 + |DTE − 7|) is then 1/8 for every contract.
- META is FB in the stored bars and chains before 2022-06-09; the singles' span starts after it.
- No vendor fetch of any kind is made by this study (answer 8: a fetch is revisited only if the gate passes, and then
  only as a size/time/disk estimate reported to the owner, section 13).

### 2.2 Sessions and the calendar

- Trading days: SPY's option EOD dates before 2022 (as `fcommon.trading_days`), `audit_lib`'s NYSE calendar from 2022.
- **Evaluated sessions are full sessions** (half days out, the list of `fcommon.PRE2022_HALF` ∪ `audit_lib.NYSE_HALF_DAYS`):
  v0's 09:31–15:30 window and 15:58 flat cannot run on a 13:00 close. A half day's bars still serve as INPUT bars of the
  3-calendar-day window of a later session.
- **The bar window**: the trading days among the calendar days D−2, D−1, D (so a Monday's window is Monday alone, a
  Tuesday's is Monday and Tuesday, a Wednesday–Friday's is three sessions; a holiday in the window just drops out). The
  window's regular-session bars (stamps 09:30–15:59 with a non-null open, high, low and close; volume null → 0) are
  concatenated in time order into one sequence; every indicator except VWAP runs on that sequence across the session
  breaks. At minute m the sequence holds the prior window sessions' bars and today's bars stamped ≤ m − 1.
- A minute m is **evaluated** only if today's bar stamped m − 1 exists, the window holds ≥ 30 bars, and today's ΣV > 0
  (VWAP defined). A minute that is not evaluated has no score; it neither signals nor re-arms.
- Splits within the 3-day window (singles): none of the singles' split dates (NVDA 2024-06-10, AVGO 2024-07-15) falls in
  the window of an expiry-day session of the singles' span other than as "today"; prices are used unadjusted. (Checked by
  the code; a window that crosses a split is skipped and listed.)

### 2.3 Open interest before 2023-11-21 — the owner's answer 3, decided here from selection data only

Computed by `oi_decision.py` before this commit, on the option layer's non-held-out sessions 2023-11-21 → 2026-10-21
(held-out months never opened), names SPY, QQQ (decision) and IWM (shown): at every scanner **onset** (a minute with score ≥ 80
whose last evaluated minute before it had score < 80, or the session's first such minute — v0 can enter only at an onset;
the position rule only removes some), the contract the rule picks with v0's OI ≥ 250 filter against (a) the filter off,
OI still in the ranking (the owner's literal count), and (b) no OI anywhere — the filter off AND the OI terms out of the
pick (liquidity = min(vol/100, 5), the OI key dropped), i.e. the rule as it can run where no daily OI exists. "Changed" =
a different (strike, right), or a contract on one side and no trade on the other. Share = changed ÷ onsets where either
side picks a contract.

Non-held-out sessions read: 512, 2023-12-01 → 2026-10-21 (2023-11 is a held-out month); 1,441 name-sessions with a chain;
25,972 onsets. Output: `out/oi_decision.json`.

| names | onsets | either side picks | (a) filter off, OI ranked: changed | share | (b) no OI at all: changed | share |
|---|---|---|---|---|---|---|
| **SPY + QQQ (decides)** | 18,287 | 17,892 | 59 (54 v0 no-trade → a pick; 5 a different contract) | **0.33%** | 3,269 (54 + 3,215 a different contract) | **18.27%** |
| SPY | 8,987 | 8,789 | 9 | 0.10% | 1,490 | 16.95% |
| QQQ | 9,300 | 9,103 | 50 | 0.55% | 1,779 | 19.54% |
| IWM (shown only; its chains start 2024-04-19, inside the OI span) | 7,685 | 6,563 | 82 | 1.25% | 507 | 7.73% |

v0's own no-trade reasons at these onsets (SPY + QQQ): delta 322, volume 71, open interest 54, spread 2.

**Decision (the larger of (a) and (b) on SPY + QQQ decides; both must be under 1% to run the early span as the same
rule):** the filter alone changes 0.33% of picks, but the rule as it can actually run without daily OI changes 18.27% — **not
under 1%. So the PRIMARY span of SPY and QQQ starts 2023-11-21** (in practice 2023-12-01, the first non-held-out session;
IWM 2024-04-19), and **2022-11-11 → 2023-11-20 is a labelled SECONDARY span ("SPY/QQQ, no OI, 2022-11 → 2023-11")**, run
with the (b) rule (no OI filter, OI out of the pick), reported beside the primary figures and never in the primary
verdict, eligibility or finalist choice. The rule written for this decision (both counts under 1%) was in this file's
draft before `oi_decision.py` returned.

Consequences for the splits (section 3, unchanged dates): the PRIMARY option-layer Pick is 228 sessions (2023-12-01 →
2025-04-02), Check 284 (2025-04-03 → 2026-10-21), holdout 212 (the held-out months 2023-11-21 → 2026-08-31). The secondary
early span holds 198 Pick sessions (2022-11-11 → 2023-10-31) and 57 held-out sessions (2022-12, 2023-05, 2023-11-01 →
2023-11-20); it has no Check sessions.

### 2.4 Open interest file convention

"That morning's published OI" for session D = the `open_interest` field of UW's dated chain dated D,
`$SP/features_data/uw/oi_chain/{SPY,QQQ,IWM}/<D>.parquet` — exactly the features study's V2 convention (PREREG_FEATURES
§9, `uw_features.oi_for`): the chain dated D carries the count published the morning of D (positions at D−1's close).
Checked on the files (selection data, no outcome): the chain dated D's `prev_oi` equals the chain dated D−1's
`open_interest` on 6,717 of 6,717 joined SPY contracts (2024-06-04 against 2024-06-03). Nothing else in the dated chain
(its NBBO, IV, greeks, volume are D's end state) is read. The chains were fetched with `exclude_zero_oi_chains = true`, so
a contract with no row has OI 0 here and fails the filter.

### 2.5 Volume — the stated deviation

"volume ≥ 100 (previous session's contract volume)": the contract's `volume` in ThetaData's option EOD row dated P, P the
trading day before D (half days count as trading days), for the same expiry (D), strike and right
(`$SP/theta/fetch_cache/eod_all/<T>/` weekly files). No row → volume 0 (fails). If P's EOD file is not on disk the minute
is a no-trade "no previous-session volume file". **Deviation, as the owner states:** this is a point-in-time stand-in for
intraday volume; many same-day contracts are listed only days before expiry, so a contract that traded little the day
before fails even if it is active today.

### 2.6 Quotes, the delta and the contract

- The chain row stamped m is the NBBO at minute m (the stored files' stamps). A quote stands for the filters when
  ask > bid > 0 (strict, as the rule says); mid = (bid + ask) / 2 computed from the row.
- **Delta**: Black-Scholes with S = E (the close of the bar stamped m − 1, the last completed bar), the strike, T = (16:00
  − m) in calendar minutes ÷ 525,600, r = 0.045, q = 0; the vol solved by bisection on [0.0001, 10] from the mid; a mid at
  or below the discounted intrinsic or at or above the bound (no vol) → delta undefined → fails 0.30–0.60.
- **Ties in the pick tuple**: after the five elements, the strike nearest E, then the lower strike.
- **No contract passes** → a no-trade at that onset, with the first filter that left nothing (in the order quote, spread,
  delta, volume, OI), and the onset is consumed: the rule re-arms only after a minute with score < 80. A minute without a
  chain file or without any quote on that side is a no-trade with that reason.

### 2.7 Exits, fills and costs

- Entry at minute m at the ask of the row stamped m. The first completed bar after entry is the bar stamped m (it
  completes at m + 1). Bars b = m … 15:57 are checked in order; a trigger on bar b sells at the bid of the row stamped
  b + 1; no trigger → sold at the bid of the 15:58 row ((c)).
- (b) uses VWAP after bar b and the latest swing low (high) known once bar b completes (swings confirmed through bar b);
  with no swing known only the VWAP part applies. A bar of today missing from the file is skipped (no check on it).
- An exit row with no bid for the contract: the last bid in the 10 minutes before; none → 0. **Bid 0 → exit value 0, no
  exit fee** (nothing is sold). Mid-to-mid marks take the same rows' mids with the same fallback.
- Costs $0.68748 a contract each way (SPY, QQQ, IWM, singles); SPXW $1.18748 under $1.00, $1.27748 at $1.00 or more, no fee
  at cash settlement (PREREG_SPXW §4). Return r = ((exit − ask) × 100 − fee in − fee out) ÷ (ask × 100); $ = the numerator.
- One open position per name; entries at minutes 09:31–15:30 only. After an exit at row x the rule is disarmed and
  re-arms at the first evaluated minute ≥ x with score < 80; an entry needs an evaluated minute with score ≥ 80 after the
  re-arm (at session start the rule is armed).
- Grade of a trade = the score at its entry minute (A 80–89, A+ ≥ 90).

### 2.8 The implied move and the forward return (signal check)

- **Implied move** (PREREG_FEATURES 2.2): on the 0DTE chain of the same name, K* = the strike where both the call and the
  put stand (bid > 0, ask > 0, ask ≥ bid) and |C_mid − P_mid| is smallest (ties: the lower strike), F = K* + C_mid − P_mid,
  IM = C_mid + P_mid in dollars, unscaled. **"At 09:30" is read on the row stamped 09:31**: the stored rows stamped 09:30
  carry no quote (0 of 40 sampled files per name had a standing pair at 09:30); 09:31 is the first quoted row. A session
  with no standing pair at 09:31 has no IM-unit figures.
- **Forward return** of a minute m (signal bar = the bar stamped m − 1, close c(m−1)) over h ∈ {5, 15, 30, 60}: the close
  of today's bar stamped m − 1 + h against c(m−1), signed +1 bullish / −1 bearish (v0's direction at m), in bp =
  sign × (c(m−1+h) / c(m−1) − 1) × 10⁴; in IM units = sign × (c(m−1+h) − c(m−1)) ÷ IM. Undefined (the minute is left out at
  that horizon, signal and baseline alike) when m − 1 + h is past the 15:59 bar or that bar is missing.
- **A v0 signal** = an evaluated minute with score ≥ 80 (every such minute, whatever the position state). Onsets alone are
  reported beside it, descriptive.
- **The baseline** = every evaluated minute with score < 80 (stretch-zeroed minutes included), same names, the same
  minutes of day, each signed by its own v0 direction.

---

## 3. The splits (answer 5) — drawn once, before anything was computed

Drawn with numpy 2.5.3 by exactly this code (`scanner_lib.draw_holdout`, asserted on every import):

```python
import numpy as np
MONTHS = [f'{y}-{m:02d}' for y in range(2017, 2027) for m in range(1, 13) if '2017-06' <= f'{y}-{m:02d}' <= '2026-10']   # 113
SINGLES = ('AAPL', 'AMD', 'AMZN', 'AVGO', 'GOOGL', 'INTC', 'META', 'MSFT', 'MU', 'NVDA', 'TSLA')
k = int(np.floor(0.25 * len(MONTHS) + 0.5))                                                              # 28
held_m = sorted(np.random.default_rng(2026102301).choice(MONTHS, size=k, replace=False).tolist())
kt = int(np.floor(0.20 * len(SINGLES) + 0.5))                                                            # 2
held_t = sorted(np.random.default_rng(2026102302).choice(list(SINGLES), size=kt, replace=False).tolist())
```

**Held-out months (28 of the 113 calendar months 2017-06 → 2026-10), every layer and every name:** 2017-06, 2017-09,
2017-10, 2018-01, 2019-07, 2019-08, 2020-06, 2020-08, 2020-11, 2020-12, 2021-01, 2021-03, 2021-05, 2021-11, 2022-04,
2022-12, 2023-05, 2023-11, 2024-05, 2024-06, 2024-07, 2024-08, 2024-11, 2025-08, 2025-11, 2026-03, 2026-04, 2026-08.

**Held-out tickers (singles only, 2 of 11): AMD, AVGO.** Never opened (bars, chains, EOD) before the holdout read.

**Pick / Check**: the first 60% / last 40% (n_pick = ⌊0.6 n + 0.5⌋) of each layer's non-held-out full sessions, by date:

| layer | full sessions | held out | Pick | Check |
|---|---|---|---|---|
| signal check: underlying bars, 2017-06-01 → 2026-10-21 | 2,341 | 582 | 1,055: 2017-07-05 → 2022-11-18 | 704: 2022-11-21 → 2026-10-21 |
| option layer: 0DTE chains, 2022-11-11 → 2026-10-21 | 979 | 269 | 426: 2022-11-11 → 2025-04-02 | 284: 2025-04-03 → 2026-10-21 |

- One calendar per layer: every name of a layer uses the same Pick / Check dates (IWM's chains start 2024-04-19, so its
  option-layer Pick holds 2024-04-19 → 2025-04-02 only; a single name trades only on its expiry days inside them).
- **The holdout of the option layer** = its sessions in the held-out months (269), for every name; for the singles also
  the two held-out tickers in every month of the span. Read once, section 10.
- Held-out months are never read for an outcome or a selection before that read. A window INPUT of a non-held-out session
  (the bars of D−1, D−2) may fall in a held-out month; nothing of such a day is paired with an outcome. The signal check is
  never run on the holdout.

---

## 4. Ambiguities resolved here (each fixed before any result)

1. **Window**: the 3 calendar days D−2 … D, trading days among them (2.2); bars concatenated across session breaks for
   RSI_1m, RSI_5m, RVOL, swings, trend, BOS and MSS; VWAP today only. The overnight change counts as one of RSI_1m's 14
   changes when it falls in the last 14.
2. **RSI_5m**: a 5-minute bar's close is the close of the last present 1-minute bar in its clock bucket; a bucket with no
   bar is skipped; today's bucket j (09:30 + 5j … +4) counts once the bar stamped 09:34 + 5j is complete (whether or not
   that bar exists); all buckets of the earlier window sessions count.
3. **RVOL**: with 2 ≤ k < 22 bars, the mean of the bars before the last that exist (fewer than 20); a mean of 0 → 1.0.
4. **Swings**: bar i of the window sequence (2 ≤ i ≤ n − 3) is a swing high if H_i ≥ max(H_{i−2..i+2}) (ties count, so
   every bar of a flat top is a swing); a bar with fewer than two bars on either side in the sequence is never a swing; a
   swing at i is known at minute m once i + 2 ≤ (index of the bar stamped m − 1). "Latest" = the known swing with the
   largest index; h1/h2 (l1/l2) the last two known. With fewer than two known swings of a kind, the comparisons on it are
   false, so the trend is "range"; BOS/MSS and the stretch's swing test need the latest swing of the kind they name, and
   are false without one.
5. **Body ratio**: a bar with high = low has ratio 0 (not > 0.75); the three bars are the last three of the sequence (the
   prior session's last bars at 09:31–09:32 on a day with a window).
6. **Direction / mixed**: mixed = (C ≥ VWAP) ≠ (RSI_1m ≥ 50). v0: mixed → bearish. "C > VWAP (bull)" scores only if
   strictly above.
7. **Score cap and grades**: the eight components sum to 100 at most, so the cap never binds; grade as in section 1.
8. **Fresh crossing**: see 2.7; a no-trade consumes the onset (2.6).
9. **Exit timing**: 2.7; an exit at 15:58 by rule (c) and a trigger on the 15:57 bar both sell at the 15:58 bid.
10. **Same minutes baseline**: matched by name and minute of day (each signal against the mean of the non-signal minutes of
    its own name and minute, over the same split's sessions); 6.2.
11. **Tuple ties**: 2.6. **No IV solution**: fails delta (2.6). **No OI row**: OI 0 (2.4).
12. **Singles**: the rule without OI (2.3 (b) form); "expiry days only": a single name is evaluated only on dates with a
    same-day chain file (date = expiry); the bars of earlier sessions in its window are inputs.

---

## 5. Statistics used everywhere

- Per session s in date order (sessions of the split, concatenated across held-out gaps; a session with no trade counts as
  zero): S_s = Σ r over the trades entered in s (all names of the comparison together), N_s = number of trades, D_s = Σ $.
  Mean % per trade = Σ S ÷ Σ N; mean $ per trade = Σ D ÷ Σ N.
- **Interval**: the moving-block bootstrap over sessions, **20-session blocks**, all names resampled together (a session's
  whole row), **2,000 draws**, `audit_lib.block_draws(n, 20)` (seeded 20261022 + 7919 × 20) and `weights_from`; the
  percentile interval (95%: 2.5th and 97.5th; at level 1 − α: α/2 and 1 − α/2). A difference between two rules uses the
  SAME draws for both arms: Δ_b = (W·S₁)/(W·N₁) − (W·S₀)/(W·N₀).
- Worst day = the lowest session Σ $; max drawdown = the largest peak-to-trough of the cumulative Σ $ by session.

---

## 6. Step 3a — the signal check, and THE GATE

6.1 **Run** on the signal layer's Pick sessions (1,055) for SPY, QQQ, IWM; the same on Check (704) is reported,
descriptive. Never on the holdout.

6.2 **Statistics**, for each h ∈ {5, 15, 30, 60}, in bp (and in IM units where the session has a 0DTE chain and an IM —
on Pick only 2022-11-11 → 2022-11-18 for SPY/QQQ; descriptive):
- the signals' mean signed forward return, with its block-20 interval;
- the baseline's mean (all non-signal evaluated minutes), with its interval;
- **the matched excess**: Σ over signals of (r_i − b_cell(i)) ÷ number of signals, b_cell = the mean of the non-signal
  minutes of the signal's name and minute of day over the split's sessions; bootstrapped with the baseline means
  recomputed inside each draw (the same session weights for signals and baseline; a cell with no baseline minute in a
  draw drops its signals from that draw).
- the same per name, grade A / A+, bullish / bearish, by year (points), and for onsets alone (descriptive).

6.3 **THE GATE (the owner's STOP rule, made exact here)**: v0's direction "shows a positive forward return on Pick" iff,
**at h = 15 or at h = 30 minutes** (pooled SPY + QQQ + IWM, bp): the matched excess > 0 **and** its block-20 95% interval's
lower end > 0 **and** the signals' own mean signed forward return > 0. Otherwise the study reports the signal check and
**STOPS** before section 4 (no option P&L, no ablation, no variant, no holdout read, no fetch estimate): no exit or
contract change can create a direction edge.

---

## 7. Step 3b — option P&L of v0 on Pick and Check (only if the gate passes; exploration only)

Per name, per year, per grade (A / A+), per hour of entry (09, 10, …, 15): trades and no-trades (with the reason); mean %
and mean $ per trade with the block-20 interval (dates as the unit, all names resampled together); win rate, average
win and average loss; exit-reason shares ((a) target, (b) invalidation, (c) 15:58); worst day; max drawdown. Every trade
also marked mid-to-mid with no fees (entry mid at m, exit mid at the exit row), to separate the signal from the cost of
trading it. The singles (open tickers) are reported the same way as their own table.

The secondary early span (SPY/QQQ 2022-11-11 → 2023-10-31 Pick, no OI) and the singles get the same tables as their own
lines.

## 8. Step 3c — component ablation (descriptive only)

v0 with each of the eight score components removed, one at a time (its points set to 0; threshold 80 unchanged, so a
signal must reach 80 without it), on Pick and Check: trades, mean %, mean $, and the gain over v0 with the same draws.

---

## 9. Section 4 — refinement, Pick → Check only (the holdout stays closed). Every variant changes one thing; every other
part is v0.

| id | variant |
|---|---|
| A1 | threshold 70 (score ≥ 70 to signal; re-arm below 70) |
| A2 | threshold 90 |
| B1 | BOS/MSS scored only in the trade's direction: BOS +10 only if bullish and C > latest swing high, or bearish and C < latest swing low; MSS +5 only if bullish and (downtrend and C > latest swing high), or bearish and (uptrend and C < latest swing low) |
| B2 | mixed direction readings → no trade: a mixed minute (4.6) scores 0 (no signal; it re-arms) |
| C1 | entries 09:45–11:30 only (entry minute m in [09:45, 11:30]) |
| C2 | entries 10:00–15:00 only |
| C3 | no entries after 14:00 (m ≤ 14:00) |
| D1 | exit (a) at T2 instead of T1 |
| D2 | exit (a) at T3 instead of T1 |
| D3 | 15-minute time stop: also sold at the bid of the row stamped m + 15 if still open |
| D4 | 30-minute time stop (m + 30) |
| D5 | premium stop −30% with target +50%: (a) is replaced by — at each row stamped b + 1 (b ≥ m), bid ≤ 0.70 × entry ask → sell (stop), bid ≥ 1.50 × entry ask → sell (target); (b) and (c) unchanged, first trigger wins |
| D6 | 0DTE sold by the 14:00 bid: a position open at 14:00 is sold at the bid of the 14:00 row; no entry at or after 14:00 (it could not be held) |
| E1 | spread veto 10% (spread% ≤ 10% in the filters) |
| E2 | spread veto 3% |
| E3 | contract nearest \|delta\| 0.45 among those passing the filters, instead of the OI ranking (ties: v0's tuple) |
| G1 | (answer 7) SPY's signals traded in SPXW 0DTE: at each SPY entry, SPY's pick has distance x = (K − F)/IM (call) or (F − K)/IM (put) on SPY's chain at m (2.8's F and IM at minute m); the SPXW contract of the same right with ask > bid > 0 whose x on SPXW's chain at m is nearest (ties: the lower strike) is bought at its ask; exits are SPY's triggers sold at the SPXW bid of the same row; SPXW fees; **an SPXW entry after 14:00 (m > 14:00) is held to the official SPX close** (intrinsic, Cboe file, no exit fee), and while it is held SPY takes no new entry. QQQ and IWM unchanged. No SPXW quote standing at m → a no-trade "SPXW no quote" |
| F1–F5 | combinations, below |

**F (combinations), fixed now**: after A–E are judged, take the eligible A–E variants (G1 is not combined), keep the one
with the largest Pick gain per group (A, B, C, D, E; B1 and B2 count as one group), and order them by Pick gain, largest
first: v1, v2, … vk. The combinations, in this order and only those that exist: F1 = {v1, v2}, F2 = {v1, v2, v3}, F3 = {v1,
v2, v3, v4}, F4 = {v1, …, v5}, F5 = {v1, v3}. k ≤ 1 → no F. A combination applies each member's change together.

Total ≤ 2 + 2 + 3 + 6 + 3 + 1 + 5 = 22 (≤ 30). Every one tried is listed with its figures.

**Eligible**: the gain over v0 (Δ = mean % per trade of the variant − v0, all primary names pooled, the same draws) has
its Pick block-20 95% interval clear of zero (lower end > 0) **and** the gain's mean on Check > 0. **Finalists**: at most
3 eligible variants (A–F and G1), the largest Check mean % per trade first (equivalently the largest Check gain). No new
indicator, data source or parameter beyond this list.

---

## 10. Section 5 — the final read, once, on the holdout (only if the gate passed)

v0 plus the finalists, k = 1 + number of finalists, read together once on the option layer's held-out sessions of the
primary span (212 sessions, 2023-11-21 → 2026-08-31), primary names. The early span's 57 held-out sessions are read in the
same pass as their own secondary line (SPY/QQQ, no OI), never in the primary verdict. Each rule passes iff, on the holdout: **mean % per trade after costs > 0; its 20-session block interval at
level 1 − 0.05/k (percentiles 2.5/k and 100 − 2.5/k) clear of zero (lower end > 0); at least 100 holdout trades.**
Per-name rows descriptive. No tuning after this read; if nothing passes, that is the answer and no further variant is
tried.

**The singles' secondary verdict** (answer 4, never part of the primary verdict): the same rules (v0 and the finalists
that apply to single names — G1 does not), without OI, read once on the singles' holdout (AMD and AVGO in every month of
2022-11-11 → 2026-10-21, plus the other nine names in the held-out months) with the same pass rule and the same k. Its
Pick / Check figures (open tickers, non-held-out months) are reported as exploration.

If the gate fails the singles get the same treatment as the primary universe: the signal check is the primary universe's,
and nothing of the singles beyond what section 2.3 used is computed.

---

## 11. Section 6 — integrity

- ≥ 30 trades and ≥ 20 no-trade cases re-derived from the raw Parquet files by a separate plain-loop script (no numpy
  vectorization, no shared code with `scanner_lib`): the indicators at the entry minute, the score, the contract, the
  entry ask, the exit row, the exit bid and the return; differences listed. If the gate fails, ≥ 30 signal minutes and
  ≥ 20 non-signal minutes of the signal check are re-derived the same way (score, direction, forward returns).
- Deterministic; the bootstrap is `audit_lib`'s seeded code.
- Commits: this file alone; then the results (`COMPASS_SCANNER_REPORT.md`, with every table above and the frozen parameter
  list of any rule that passes). One LEDGER row per rule read on the holdout (`research_notes/Edge search/LEDGER.md`); none
  if the gate stops the study.

---

## 12. Prior reads — which months and names earlier studies opened

**Bottom line: no month and no name of this study is unread.** Every month of both layers, the 28 held-out months
included, has been read by earlier studies on the same names — and the closest of them (S01–S04, S06, S09) tested the
owner's earlier "Quick Scalps" baseline, a rule of the same family (RSI crossing 55/45, VWAP side, relative volume,
structure, 0DTE contracts at delta 0.30–0.60 nearest 0.45, spread under 12%). The random month holdout protects this
study only against its own Pick → Check tuning; it cannot undo what earlier studies saw.

**By study** (commits; the research registry entries were last at `75c29c9^`, `research/compass/registry.jsonl`):

| study (commit) | names | data and span | what it read |
|---|---|---|---|
| S04 (`b037899`) | SPY, QQQ, IWM | 1-min bars 2017-06-01 → 2026-10-09 | the Quick Scalps signal's signed forward return 5/15/30/60 min, against matched random minutes; component ablations |
| S06 (`4aba507`) | SPY, QQQ, IWM | 1-min bars 2017-06-01 → 2026-10-09 | seven intraday triggers (RSI cross, VWAP reclaim, 5-min EMA cross, breakout, retest, trend pullback, bounce) × four filter sets, signed forward returns |
| S06-TierA (`ad7ee20`) | AAPL, AMD, AMZN, AVGO, GOOGL, META, MSFT, MU, NVDA, TSLA (not INTC) and 24 others | 1-min bars 2017-06-01 → 2026-10-09 | the same triggers on single names (8.26 M events) |
| S12, S12b (`be991de`) | SPY, QQQ, IWM | bars 2017-06 → 2026-10-09; 0DTE 2022-11-11 → 2026-10-09 | first-half-hour momentum on the underlying; 0DTE expressions of it |
| H10 (registry) | SPY | bars 2017 → 2026-10-09 | last-30-minute momentum, gamma-conditioned |
| Compass H1 (`4a02144`), H4 (`dfa575d`) | SPY, QQQ | bars and official closes: H1 → 2025-10-10, H4 → 2026-10-22 | overnight reversal; first / last half-hour momentum |
| price-action atlas, V6 (`0d706b6`, `1660366`) | 43 names incl. SPY, QQQ, IWM and the 11 singles | 1-min bars 2017-06 → 2026-10 | price-action catalogue; prior-day high/low and round numbers against placebos |
| S01, S02 (`5e90201`, `6bf5934`) | SPY, QQQ, IWM | 0DTE chains 2022-11-11 → 2026-10-09 | **Quick Scalps 0DTE long calls/puts** (2,886 trades) and 41 single-factor variants with a walk-forward |
| S03 (`3c8d6cb`) | SPY, QQQ, IWM | weekly chains, a sample 2017-06 → 2026-10-09 | Quick Scalps with 1–7 DTE contracts, OI > 250 where cached |
| S09 (`7167541`), S10 (`3c8d6cb`) | SPXW; SPY, QQQ, IWM | 0DTE 2022-05 → 2026-10-09 | Quick Scalps on SPXW; fading the Quick Scalps signal with short premium |
| Steps 1–5 (`2185eb9` → `491a0c7`) | SPY, QQQ, IWM, SPXW | every same-day contract's minute quotes 2022-05-13 → 2026-10-09 | distance, time of day, exits, turn-up entries, per-contract volume; step 5 scored once on 2025–2026 |
| Lifecycle Tier I (`425c7f4`) | SPY, QQQ, IWM, SPXW | 0DTE 2022-05 → 2026-10-09 (hold-out 2025-10-01 → 2026-10-09) | 12 intraday setups × 8 structures × 116 policies |
| V5 (`f5b23f6`), V7 | SPY, QQQ, IWM, SPXW | same-day chains 2022-11 → | calibration by distance; event afternoons |
| Engine audit, phase 2, phase 3 E/F, backtest audit, after-hours | SPY, QQQ, IWM, SPXW | 0DTE 2022 → 2026-10-09 (after-hours 2025-10-13 → 2026-10-21) | the engine's trigger, opening range, straddle containment, credit structures, butterflies, the paper replay |
| Picker (`c502122`, `1e10053`) | SPY, QQQ, IWM, SPXW | 0DTE 2022 → 2026-10-21 | 0DTE long calls and puts on the opening-range fade |
| Compass features (`a2e14e4`, `2a49049`, `e5dd8c6`) | SPY, QQQ, IWM, SPXW; the 11 singles | 0DTE at 13 fixed minutes 2022-11-11 → 2026-10-21; singles' same-day chains 2017-06-02 → 2026-10-21 | long calls/puts by strike bucket and time; its holdout (AVGO, MU, QQQ; 43 months) read once, so every month and name of it is read |
| Forward tracker | SPY, QQQ | 0DTE 2026-10-12 → 21 | paper candidates |
| V3, V4 (`e4e4cea`) | the 11 singles | same-day chains and bars 2017-06 → 2026-10-09 (V4 from 2019-06) | single-name same-day straddles and put sales; a size forecast |

**By name**: SPY, QQQ, IWM bars — every month 2017-06 → 2026-10 (S04, S06, S12, atlas; SPY also H1, H4, H10; QQQ H1, H4).
SPY and QQQ 0DTE — every month 2022-11 → 2026-10 (IWM 2024-04 →; Steps 1–5, S01/S02, lifecycle, picker, features). SPXW
0DTE — every month 2022-05 → 2026-10. AAPL, AMZN, GOOGL, MSFT, NVDA, TSLA, AMD, INTC, MU, META same-day chains and bars,
and AVGO — every month 2017-06 → 2026-10 (V3, V4, features; S06-TierA bars for all but INTC). The two singles held out
here (AMD, AVGO) were read by V3, V4, features (AVGO in its holdout read) and S06-TierA.

**Month by month** (this study's role: "sig" = the signal layer, "opt" = the option layer; Pick → Check marks the month the
split falls in). * SPY (H10) or SPY and QQQ only (H1, H4). † S06-TierA: not INTC.

| month | this study | SPY/QQQ/IWM 1-min bars read by | SPY/QQQ/IWM 0DTE chains read by | single names (same-day chains, bars) read by | features study |
|---|---|---|---|---|---|
| 2017-06 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2017-07 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2017-08 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2017-09 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2017-10 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2017-11 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2017-12 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-01 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-02 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-03 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-04 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-05 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2018-06 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-07 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-08 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-09 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-10 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-11 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2018-12 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2019-01 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2019-02 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2019-03 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2019-04 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2019-05 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, Features, S06-A†, atlas/V6 | exploration |
| 2019-06 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2019-07 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2019-08 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2019-09 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2019-10 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2019-11 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2019-12 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-01 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2020-02 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-03 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-04 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-05 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-06 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-07 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-08 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-09 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-10 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-11 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2020-12 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2021-01 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2021-02 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2021-03 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2021-04 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2021-05 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2021-06 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2021-07 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2021-08 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2021-09 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2021-10 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2021-11 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2021-12 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2022-01 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2022-02 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2022-03 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2022-04 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2022-05 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2022-06 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2022-07 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2022-08 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2022-09 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2022-10 | sig Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | — (no daily expiry on disk) | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2022-11 | sig Pick→Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2022-12 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2023-01 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2023-02 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2023-03 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2023-04 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2023-05 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2023-06 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2023-07 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2023-08 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2023-09 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2023-10 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2023-11 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2023-12 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2024-01 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2024-02 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2024-03 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features; IWM none on disk | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2024-04 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2024-05 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2024-06 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2024-07 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2024-08 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2024-09 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2024-10 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2024-11 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2024-12 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2025-01 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2025-02 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2025-03 | sig Check · opt Pick | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2025-04 | sig Check · opt Pick→Check | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2025-05 | sig Check · opt Check | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2025-06 | sig Check · opt Check | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2025-07 | sig Check · opt Check | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2025-08 | **holdout** | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2025-09 | sig Check · opt Check | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2025-10 | sig Check · opt Check | S04, S06, S12, H10*, H1*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2025-11 | **holdout** | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2025-12 | sig Check · opt Check | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2026-01 | sig Check · opt Check | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2026-02 | sig Check · opt Check | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2026-03 | **holdout** | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2026-04 | **holdout** | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2026-05 | sig Check · opt Check | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2026-06 | sig Check · opt Check | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |
| 2026-07 | sig Check · opt Check | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2026-08 | **holdout** | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2026-09 | sig Check · opt Check | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH | V3, V4, Features, S06-A†, atlas/V6 | exploration |
| 2026-10 | sig Check · opt Check | S04, S06, S12, H10*, H4*, atlas/V6 | Steps 1–5, S01/S02, S10/S12b, LC Tier I, V5, PhE/F, Picker, Features, AfterH, Fwd | V3, V4, Features, S06-A†, atlas/V6 | holdout (read once) |

---

## 13. If the gate passes: the fetch estimate (answer 8), reported, not requested

The near-money band of the other 3 listed expirations (after the 0DTE) on SPY, QQQ, IWM, 2022-11 → 2026-10: requests,
size, time and disk, from the measured figures of INVENTORY.md §3 and the free disk (`df`, about 3.5 GB at the time of
writing); nothing is requested. Single-name OI only if the singles matter by then.
