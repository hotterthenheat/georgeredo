# EMA system — RULEBOOK v0 (the preview's rules, written before any result)

Status: written and committed ALONE, before any signal, trade or P&L of this system is computed. The preview that follows
(PREVIEW_last_week.md) runs these rules exactly; anything changed after a result is seen is a new version (v1, …) and is
said so. This is **v0 of the owner's full EMA options strategy spec**: the spec leaves many choices open, and every choice
pinned below marked **[v0]** is a default to be tested later, not a finding.

Scope of the preview (the owner: "test just on last weeks data so i can see the results fast"): the five full sessions
**2026-10-12 → 2026-10-16** (Mon–Fri). Five sessions decide nothing: every number the preview prints is labelled
**PREVIEW — 5 sessions, no verdict**.

Files only, no vendor call, no key. Deterministic; every random draw seeded.

## 1. Instruments and data

| Name | Signals read on | Options traded | Volume |
|---|---|---|---|
| SPY, QQQ, IWM | the name's 1-minute bars (Theta, `theta/data/underlying/<T>/<D>.parquet`) | the name's 0DTE chain | the bar's volume |
| SPXW | SPX 1-minute index prints (`theta/data/index/SPX`) | the SPXW 0DTE chain | **none** |

- **0DTE only [v0, forced]**: only 0DTE 1-minute NBBO chains are on disk (`theta/data_full/chains/<T>/<D>.parquet`);
  non-0DTE 1-minute quotes are not, so no other expiry can be priced.
- **SPX bars [v0]**: the index has one print a minute and no OHLC or volume. The print stamped t is taken as the close of
  the 1-minute bar that ends at t (bar stamp t − 1 minute); that bar's open = high = low = close = the print. So for SPX
  every "high"/"low" below is the close.
- **SPX VWAP [v0]**: with no volume, SPX's "VWAP" is the session's time-weighted mean of its 1-minute closes (each bar
  weight 1), reset at 09:30. Labelled a stand-in.
- **SPX RVOL**: unavailable → the RVOL condition is **dropped for SPXW** (labelled in every SPXW row).
- Regular session 09:30–16:00 only. Bar stamps 0..389 = 09:30..15:59; "minute m" = 09:30 + m, the moment bar m − 1 has
  completed. A chain row stamped m is the NBBO at minute m.

## 2. Indicators (all on regular-session bars)

- **EMAs run continuously across sessions**: one series per timeframe through every regular-session bar, warmed up on the
  **60 trading days before 2026-10-12** on disk [v0]. EMA(n): α = 2/(n+1), seeded with the first close of the warm-up.
- **Candles [v0]**: 5-minute and 15-minute candles are clock-aligned buckets of the session's 1-minute bars (09:30–09:34,
  …; 09:30–09:44, …); a candle's close is the close of its last bar; a candle is **completed** once its last bar is.
  At minute m the last completed 5m candle is bucket ⌊m/5⌋ − 1 of the session, the last completed 15m candle ⌊m/15⌋ − 1
  (before the session's first, the previous session's last).
- **VWAP**: Σ(typical price × volume) ÷ Σ volume from 09:30, typical = (H + L + C)/3; resets each session (SPX: §1).
- **RSI(14), Wilder** on 1m closes (continuous, warmed up). **ROC(5)** = C[s] ÷ C[s−5] − 1 on 1m closes.
- **RVOL** = volume of bar s ÷ mean volume of the same bar stamp over the previous 10 sessions on disk that have it (at
  least 5, else undefined → condition fails) — SPY/QQQ/IWM only.
- **Swings (structure, reported only)**: bar i is a swing high if H[i] = max(H[i−2..i+2]), a swing low if L[i] =
  min(L[i−2..i+2]); **known only once bar i+2 has completed** (minute i+3).

## 3. The rule (decision at minute m, using only bars ≤ s = m − 1)

Two configs, run separately:

| | 5-minute alignment (last completed 5m candle) | pullback line (1m) |
|---|---|---|
| **Config A** | bull EMA5 > EMA15 > EMA20 > EMA50; bear reversed | EMA20(1m) |
| **Config B** | bull EMA9 > EMA21 > EMA50; bear reversed | EMA21(1m) |

All of these must hold for a **bull** trade (calls); **bear** (puts) is the mirror:

1. **15-minute bias**: the last completed 15m candle's close > its EMA50(15m). (EMA200(15m) is context only: reported, not
   required.)
2. **5-minute alignment** of the config (above).
3. **1-minute setup**: in the window W = the last 5 completed 1m bars (s−4..s), some bar t ∈ W has L[t] ≤ max(pullback
   line[t], VWAP[t]) (bear: H[t] ≥ min(…)), each line read at that bar; and **no** close in W is on the wrong side of the
   1m EMA50 at its bar (bull: no C[t] < EMA50[t]; bear: no C[t] > EMA50[t]) [v0 reading of "crossed against the trade"].
4. **Trigger**: C[s] > H[s−1] and C[s] > VWAP[s] (bear: C[s] < L[s−1] and C[s] < VWAP[s]).
5. **Confirmations**: RSI14[s] > 50 (bear < 50); ROC5[s] > 0 (bear < 0); RVOL[s] ≥ 1.5 (not SPXW).
6. **Time**: minute m in 09:45–15:30 (m = 15..360).

If bull and bear both held (impossible by 1–2) bull would win; stated for completeness.

**Structure** (last two confirmed swing highs and lows at m rising for bull / falling for bear) is computed and reported
beside each trade, **not required** in v0.

## 4. The contract and the entry

At minute m, on the chain row stamped m, 1 contract (10 in X4):
- 0DTE, the trade's side (calls bull, puts bear); ask > bid > 0;
- spread (ask − bid)/mid ≤ 12%;
- |delta| 0.30–0.60, Black-Scholes from the mid, r = 0.045, no dividend, T = minutes to 16:00 ÷ 525,600, spot = C[s];
- open interest ≥ 250 — the count **published the morning of the session** = the `open_interest` field of the UW chain
  dated the session (PREREG_FEATURES.md, V2: "the count published the morning of D = positions at D−1's close");
- previous-session volume ≥ 100 (ThetaData EOD of the session before, same contract);
- pick |delta| nearest 0.45; ties the tighter spread, then the lower strike.

No contract passes → **no trade**, counted with its reason (the first filter that empties the list, in the order above).
Filled at the **ask**.

## 5. Stop, R and the exits

- **Stop level**: bull the lowest low in W, bear the highest high in W. **R** = |C[s] − stop level| in underlying points
  (R = 0 → no trade, reason "zero R").
- **Stop**: a 1m close beyond the stop level (bull C < level; bear C > level) at any bar after entry.
- **Targets on 1m closes [v0]**: +kR is reached when a completed 1m bar's close is at or beyond C[s] ± kR.
- Exit variants (run separately, each its own trade sequence; the stop and the 15:58 flat are active in every variant;
  the first trigger wins):
  - **X1**: full exit at +1R. **X2**: full exit at +2R.
  - **X3 (runner)**: exit when a completed 5m candle (after entry) closes below its EMA9(5m) (bear: above).
  - **X4 (partial, 10 contracts)**: 2 at +1R, 3 at +2R, 5 on X3; the stop takes whatever is open (stop not moved).
- **The fill**: an exit triggered by the bar completing at minute e sells at the **bid of the chain row stamped e**;
  a missing bid takes the last bid in the 10 rows before, none → 0; bid 0 → 0. **15:58 flat**: anything open at
  minute 388 sells at row 388's bid.
- **Fees**: SPY/QQQ/IWM **$0.68748** a contract each way; SPXW **$1.18748** a contract each way when that side's premium
  < $1.00, **$1.27748** otherwise. Contract multiplier 100.

## 6. Risk

Max **5 entries** per name per session; **one position per name** (a new entry at minute ≥ the previous exit's minute + 1);
**5-minute cooldown** after a stop (next entry at minute ≥ stop exit minute + 5); no entry after 15:30. Names independent.

## 7. Baselines (same week, same contract rule, the X2 exit with the same stop definition, same risk rules unless said)

- **(a) simple crossover**: bull when the 1m EMA9 crosses above EMA21 at bar s (Config B) / EMA5 above EMA15 (Config A),
  bear on the cross below; no other filter. Stop = the extreme of the last 5 bars as in §5.
- **(b) alignment only**: 15m bias + the config's 5m alignment on the same side; enter on the first minute the joint state
  turns on (off at m − 1, on at m; the session's first eligible minute 09:45 counts as a turn-on when it is on).
- **(c) RANDOM**: 500 seeded trials (seed 20261023). Per trial, per name, the same number of entries as the full
  strategy's X2 trades for that config and name; each entry draws a session uniformly from the five, a minute from the
  full strategy's entry minutes (pooled over names, that config), a side Bernoulli at the full strategy's call share; X2
  exit, stop as in §5. Risk rules not applied (draws independent; overlap allowed). A draw with no contract is drawn
  again (up to 50 times). Reported: the mean and the 5–95% band over trials of net P&L per trade and in total.

## 8. What the preview reports

Per config × exit variant × instrument (and all): trades, no-trades by reason, win rate (net > 0), avg win / avg loss,
expectancy $ and % of premium after costs, gross vs net, profit factor, avg and median hold, MAE/MFE (option %, on the
bid marked each minute against the entry ask), long vs short, by hour of entry; the baselines; the **stock-only study**
(each full-strategy trade's underlying signed move entry → exit, in bp and in R); a costs breakdown; a plain-loop
re-derivation of at least 10 trades (target: 0 differences); unit tests (indicators on a toy series, no-lookahead,
the swing delay, the fees). Labels OBSERVED (read off the data), CALCULATED (arithmetic of observed), MODELED (Black-
Scholes delta). Every table: **PREVIEW — 5 sessions, no verdict**.
