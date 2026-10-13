# SLAYER_INDEPENDENT_IMPLEMENTATION_SPEC

An original specification for building, in Slayer Terminal, the capabilities that this research found to be (a) real in GeorgeFi's product, (b) reproducible from the data we are entitled to, and (c) worth having. It deliberately does **not** reproduce GeorgeFi's text, naming, scoring constants or alert copy. Where GeorgeFi's own numbers appear they are cited as *observations to test*, never as targets to copy.

Status legend: **Validated** = supported by our independent tests (see `GEORGEFI_SIGNAL_RESEARCH.md` §6); **Testable** = a concrete hypothesis with a defined test; **Infrastructure** = needed regardless of edge.

Nothing in this document is a trading strategy ready for live orders. The research found no statistically validated entry edge; the spec therefore builds the *measurement system first* and treats every signal lane as a hypothesis to be graded in a cost-realistic paper book.

---

## 1. Design goals

1. **Measurement before signals.** Every alert Slayer emits is stamped, paper-filled with explicit, conservative cost assumptions, and graded automatically. Slayer never reports a one-minute high as a result.
2. **Inputs are first-class.** Every alert carries the full input vector that produced it (levels, dealer-exposure estimates, flow burst statistics, session clock), so outcomes can be attributed to inputs later.
3. **Reproducibility.** All features are recomputable from stored raw data with a fixed clock; no feature may read data timestamped after its decision time.
4. **Honest vocabulary.** Dealer gamma is an *estimate*; flow side is *inferred from NBBO position*; "crowd mood" derived from an oscillator is labelled as such.

---

## 2. Data layer (Infrastructure)

| Component | Provider / endpoint | Cadence | Storage |
|---|---|---|---|
| Underlying 1-min bars for SPX, NDX, RUT, SPY, QQQ, IWM and the single-name universe | Unusual Whales `stock/{t}/ohlc/1m` (indices) and Massive stock aggregates (ETFs/singles) | pull each minute during RTH; daily backfill | `bars_underlying(ticker, ts_utc, o,h,l,c,v,src)` |
| Option contract 1-min bars with IV range and side-of-trade premium | UW `option-contract/{id}/intraday` (historical) and UW `option_trades` websocket channel (live) | live stream + EOD backfill | `bars_option(occ, ts_utc, o,h,l,c, vol_ask, vol_bid, vol_mid, prem_ask, prem_bid, iv_lo, iv_hi)` |
| Option NBBO at decision time | UW live `option-trades` fields `nbbo_bid/ask` (today) ; Massive quotes **not entitled** | live only | `quotes_option(occ, ts, bid, ask, bid_sz, ask_sz, src)` |
| Dealer exposure estimates | UW `greek-exposure/strike` (EOD), `spot-exposures` (1-min totals), `gex-levels` (flip, walls, magnet) | EOD + 1-min | `dealer_exposure(ticker, date, strike, call_gex, put_gex, charm, vanna)`; `dealer_levels(ticker, date, flip, call_wall, put_wall, magnet, source)` |
| Per-strike flow | UW `flow-per-strike-intraday` (1-min) ; `full-tape/{date}` zips for tick history | 1-min live; nightly archive | `flow_strike_min(ticker, ts, strike, side, prem_ask, prem_bid, vol_ask, vol_bid, trades)` |
| Dark pool prints | UW `darkpool/{t}` | live | optional lane input |
| Market tide / net premium | UW `market-tide`, `net-prem-ticks` | 5-min / 1-min | regime context |
| Volatility context | UW `volatility/realized`, `iv-rank`, VIX term structure | daily | sizing / trail inputs |
| Contract reference | Massive `v3/reference/options/contracts` | daily | strike/expiry/exercise style; OCC symbol builder |
| Session clock | computed | — | ET session state, holidays, early closes |

Budget rules: Massive ≤ 5 requests/min (observed plan limit); UW unthrottled but cache every response. All raw responses are stored verbatim with fetch time so features can be rebuilt.

---

## 3. Feature engine

All features are computed on bar close with timestamp `t` and may only read rows with `ts < t`.

### 3.1 Session levels (Testable)
Prior-day high/low/close, prior-week high/low, pre-market high/low, opening-range high/low (first 15 min, configurable), VWAP, expected-move bands (ATM straddle × 0.8 from the contract chain at 9:35), dealer levels (flip, walls, magnet). Each level is a row `(ticker, date, type, price, source)`.

### 3.2 Sweep detector (Testable)
A sweep of level L at bar `t`: `high_t > L` (or `low_t < L`) and `close_t` back inside by ≥ k × ATR₁ₘ within n bars (default k=0.25, n=3). Output: `(ticker, t, level_type, direction, depth_atr, reclaim_bars)`. GeorgeFi's ledger shows sweep tags on 438/489 trades; our test (T5) found a positive association only in the aggregate and it is confounded by era, so this is a hypothesis.

### 3.3 Structure (Testable)
Swing highs/lows on 1-min and 5-min (fractal n=3), break-of-structure and change-of-character flags, order-block candidates (last opposing candle before a displacement > 1.5 ATR). Store as labelled bars, not scores.

### 3.4 Dealer regime (Testable)
From UW exposures: `net_gex_total`, `flip`, `distance_to_flip_pct`, `nearest_wall`, `pin_distance_pct`. Regime label: `AMPLIFYING` if spot below flip and net GEX < 0, `DAMPENING` if above flip and net GEX > 0, `AT_PIN` if |pin_distance| < 0.1 %. GeorgeFi's record showed `AT_PIN` entries outperforming `POSITIVE_GAMMA` entries (observation, n=138 vs 86, era-confounded); test, don't assume.

### 3.5 Per-strike flow burst (Testable; the "sus strike" analogue)
For each (ticker, strike, side) keep a rolling 20-day same-time-of-day baseline of 1-min ask-side premium. Burst score = (prem_ask_1m − baseline_mean) / baseline_sd; sustained score over 15 min = mean z. Attribute aggressor from `prem_ask vs prem_bid` share (≥ 70 % ask = BOUGHT, ≥ 70 % bid = SOLD, else TWO-WAY). Emit `(ticker, t, occ, burst_z, sustained_z, aggressor, notional)`. Public-tape forward returns (T6) show these alerts are *not* directional on their own; store, display, but do not auto-trade.

### 3.6 Crowd oscillator (Validated as GeorgeFi's mechanism; untested as edge)
RSI(14, 1-min) → label `<45 BEARISH, 45–55 NEUTRAL, >55 BULLISH`. Reproduces GeorgeFi's `crowd_mood` exactly on 60/60 observed decisions. Keep as a transparency feature; our observations show GeorgeFi's own direction agrees with this label far more often than it opposes it, so "inversion" is not a mechanism to build.

### 3.7 Session clock
ET buckets: OPENING 09:30–10:00, MORNING 10:00–12:00, LUNCH 12:00–13:15, PM 13:15–15:00, POWER 15:00–15:45, CLOSE 15:45–16:00. GeorgeFi's record shows MORNING entries outperform and OPENING/POWER underperform (n=117 / 11 / 15, not significant after correction). Use as a reporting dimension.

---

## 4. Signal lanes (all Testable, all paper-only until graded)

Each lane produces `Signal{lane, ticker, occ, side, t, inputs{}, conviction∈[0,1], invalidation_price, invalidation_time}`.

- **L1 Level-reaction lane**: sweep of PDH/PDL/ORH/ORL/PWH/PWL + reclaim + structure shift in the reclaim direction. Contract: nearest 0DTE strike with |Δ|≈0.35–0.45 (from UW chain IV, Black-Scholes), premium in a per-ticker band.
- **L2 Dealer-magnet lane**: price within 0.3 % of a wall or magnet with regime DAMPENING → fade toward magnet; regime AMPLIFYING → continuation. Emits WATCH only until L1 confirms.
- **L3 Flow-burst lane**: burst_z ≥ 4 with aggressor BOUGHT → display-only alert with the contract and its forward-return history for that burst class.
- **L4 Close-flush lane**: after 15:40, a 1-min bar undercutting the session low (or exceeding the high) by ≥ 0.1 % and closing back inside; alert names the ATM contract and the wick extreme as invalidation.

Lanes never combine into a single additive "confidence" score. GeorgeFi's 60–100-tag additive ledger produced grades that did not separate outcomes out of sample (T5); Slayer keeps lanes separate and grades each lane's paper book independently.

---

## 5. Paper execution and exit engine (Infrastructure + Validated finding)

The one robust finding of the validation is that GeorgeFi's positive record comes from **fast, rule-based exits**, not from entry timing (T3: recorded exits +4.5 % of premium vs hold-to-close −15.8 %, bracket ±25 % +1.2 %, 30-min time stop −2.6 %; T4: entry MFE percentile vs random entry time = 50). Slayer therefore implements the exit engine as the core product and measures it:

- **Fill model** (mandatory, three variants reported side by side): `mid`, `bar_vwap`, `adverse` (buy bar high + half spread, sell bar low − half spread) + $0.65/contract commission + $0.05 fees. Spread proxy per instrument class until live NBBO is captured (8 % cash-settled index, 12 % ETF/single name, from GeorgeFi's own quote records); replace with measured NBBO from the UW live stream.
- **Exit rules** (parameterised, each a separate paper book so their value is measurable): initial stop as % of premium (test −12 %, −20 %, −25 %); breakeven lock after +6 % HWM; trailing giveback 8/11/14 % keyed to VIX buckets 15–20/20–30/30+; tiered take-profit (half at +25 %, rest at +45 %); structural exits on opposite BOS; dealer-regime flip exit; theta-time stop (n minutes losing); hard cash-settled close at 15:55.
- **Risk rules**: one open position per ticker, per-ticker re-entry cooldown (test 30 min), daily stop (test $300 or 5 %), max trades/day (test 8), sizing 1–3 contracts scaled by VIX bucket and account size. GeorgeFi's record violated its own published cooldown (79/216 re-entries < 30 min) and daily stop (10 entries after −$300), so these are measured, not assumed.

---

## 6. Grading and research harness (Infrastructure)

- Nightly job recomputes every open/closed paper trade under the three fill models and writes `trade_grades`.
- Per-lane scorecard: n, win rate, expectancy (% and $), profit factor, max drawdown, bootstrap 95 % CI, top-5-trade concentration, split IS/OOS by month, by regime, by time bucket. A lane is "promotable" only if the lower CI bound of expectancy under the `adverse` model is > 0 over ≥ 150 trades spanning ≥ 3 months.
- Feature-attribution report: for each lane, outcome vs each input quantile, with Benjamini–Hochberg control.
- Random-time baseline computed for every lane automatically (same contract, random minutes, same day).

---

## 7. User-facing surfaces in Slayer Terminal

1. **Tape**: chronological alert stream with lane, contract, side, invalidation and the live paper mark under the `adverse` model; filters by family/DTE/lane; 30-s refresh.
2. **Hold panel**: open paper positions with the active exit rule, distance to stop/trail, HWM, and the exit engine's current state.
3. **Levels & dealer panel**: today's levels, sweeps so far, UW dealer flip/walls/magnet with the estimate caveat shown inline.
4. **Flow panel**: burst table with aggressor attribution and the historical forward-return distribution for the burst class.
5. **Scorecards**: per-lane and per-exit-rule results with CIs; a "what you would have made at the bid/ask" toggle that is on by default.
6. **Research log**: every refused hypothesis stays visible (this mirrors a practice GeorgeFi publishes and it is worth keeping).

---

## 8. Build order

1. Data layer + storage + session clock (1–2 weeks).
2. Paper execution + exit engine + three fill models + scorecards (1–2 weeks). Backfill with the 489-trade GeorgeFi ledger as a regression fixture (expected outputs are in `evidence/analysis/validation_T1-T4.txt`).
3. Feature engine 3.1–3.4 and lanes L1/L2; run paper for ≥ 3 months.
4. Flow burst (3.5) and L3/L4 after the per-strike baseline has 20 days of history.
5. Promotion review against §6 criteria.

---

## 9. Explicit non-goals

- No additive multi-hundred-tag confidence score.
- No "inversion" marketing mechanism.
- No live order routing until a lane is promotable under the adverse fill model.
- No reliance on one-minute highs, curated recaps, or screenshots as performance evidence.
