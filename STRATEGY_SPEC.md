# STRATEGY_SPEC

"The strat": the GeorgeFi trading logic as reconstructed from evidence, written as an executable rule set, together with the verdict of the independent backtest and the configuration that Slayer Terminal should run **on paper** if it wants to track this family of ideas. Nothing in this file is a recommendation to trade live.

Sources: `GEORGEFI_SIGNAL_RESEARCH.md` (rules and evidence), `BACKTEST_RESULTS.md` (numbers), `backtest/` (code).

---

## 1. Reconstructed GeorgeFi logic (what the evidence supports)

### 1.1 Cadence and universe
- One evaluation per minute during RTH for ^SPX, ^NDX, ^RUT, SPY, QQQ, IWM; single names on a slower loop; Mon/Wed/Fri single-name 0DTE board.
- Entries fire immediately on evaluation (entry seconds are uniform, not on 5-minute boundaries).

### 1.2 Pre-session context (computed once)
- Levels: PDH, PDL, PDC, PWH, PWL, PMH, PML, ORH/ORL after 09:45, dealer levels from the prior day's option book (gamma flip, call wall, put wall, magnet/pin, σ rungs from VIX close), expected-move bands from the ATM straddle, dark-pool price levels (SPY proxy for SPX).
- Regime labels: GEX regime (POSITIVE / NEGATIVE / AT_PIN / FAR_FROM_PIN), VIX bucket (NORMAL / ELEVATED …), day type (CPI, OPEX week, VIX settle), weekly profile (TUESDAY_LOW_BULLISH …), pre-market bias.

### 1.3 Per-minute scoring (ICT Main book)
- Structure reads: BOS/CHoCH on 1-min and 5-min, order blocks and breakers with strength 0–100, liquidity pools, OTE/gap structure, VWAP side, displacement.
- Sweep detection at the levels above; `SWEEP_ALIGNED +25`, `MULTI_SWEEP +20…+35`, `TRIPLE_CONF +45…+55` when sweep + direction + GEX regime agree; `SWEEP_CONFLICT −30` when a sweep opposes the read.
- Session adjustment `SESSION_ADJ +20/+15/+10/−10/−30` by time bucket; kill-zone tags; lunch block 12:00–13:15; PM dead zone 14:00–14:50; early-market grace before 09:35.
- Flow and dealer inputs: `GEX:NEGATIVE_GAMMA +10`, `GEX:PIN_PROXIMITY −15`, `VIX_GEX` conflicts, institutional multi-ticker confirmation `+20`, delta-flow bias, dark-pool alignment, NOPE, market tide, SMT ±15/−20, correlation state.
- Exotic families (`GENOME`, `PHYSICS`, `HELIX`, `LUNAR`) add small ± points.
- Caps: total bonus capped at 20; confidence capped (e.g. 100→82) by critical-conflict clusters; sweep setups floored at 65; grade banded A+/A/A-/B+/B/B- and then capped one notch per structural conflict.
- Blocks: chop day inside the opening range (wait for PM), lunch block, PM dead zone, vol-climax, chase (>1.5 % move in the last hour), direction-loss streak, daily-loss penalty; institutional events can bypass most blocks.

### 1.4 Committed read (index lane)
- Five contributors (price vs VWAP/displacement, dealer regime, GEX position, flow bias, ICT structure) each cast a signed vote; conviction 0–100; tiers WATCH → SMALL SIZE → HALF SIZE → FULL SIZE; direction flips are gated and capped per day.

### 1.5 Contract and sizing
- 0DTE, ATM for indices, slightly ITM for ETFs (|Δ| ≈ 0.45–0.55), premium bands per ticker; 1–3 contracts; lotto plays 3–25 cheap OTM contracts; size multipliers for multi-sweep confluence (1.2×, 1.44×) and halving after a loss.

### 1.6 Exits (the part that matters)
- Initial stop −12 % (standard) to −25/−28 % (sweep/hard kill); emergency −30 % in the sniper lane.
- Breakeven lock after +6 % high-water mark; guardian ratchet after +15 % (never give back more than ~35 % of the peak); trail 8/11/14 % by VIX bucket.
- Profit: T1 lock at +25 % (observed +31…+60 % in the sniper lane) selling half, T2 at +45 %, runner trails; swing tiers +25 % partials.
- Structural exits: opposite BOS/CHoCH, liquidity-pool hit, GEX accelerator reversal, regime shift while losing, theta-burn time stop (10–18 minutes when losing), stale trail.
- Hard close 15:55–15:58 ET for all 0DTE; cash-settled ITM index contracts may ride to settlement.
- Limits as published (30-minute cooldown, ≤ 5 trades per ticker, daily stop $300/5 %) are not consistently enforced in the record.

Confidence in this reconstruction: high on structure and vocabulary (it is read directly from 489 ledgers and live payloads), low on the exact weights, and the backtest below shows that the published entry description does not reproduce the live entries (7–9 % coincidence).

---

## 2. What was backtested and what it showed

The testable core of §1 — level sweep (or break) → ATM 0DTE contract → GeorgeFi-style exit engine, with GEX and session gates — was run in 144 variants on SPY/QQQ/IWM over 345 sessions (`BACKTEST_RESULTS.md`).

| Finding | Number |
|---|---|
| Variants with positive expectancy after spread + fees | 0 / 144 |
| Best variant expectancy (spread model) | −$2.4 per contract-trade [−4.1, −0.5] on a ~$1.00 premium |
| Random-entry baseline with the same exit engine | −$3.2 [−3.7, −2.7] |
| Exit engine effect (mean across variants) | trail −$3.2 > ladder −$4.0 > bracket −$6.1 > hold −$14.8 |
| Coincidence with GeorgeFi's own entries (±5 min, same side) | 7–9 % |

Verdict: **no edge in the entries; measurable but insufficient value in the exits; the published description is not GeorgeFi's live trigger.**

---

## 3. The strategy specification for Slayer Terminal (paper only)

Because nothing is promotable, Slayer should implement this as a *measured paper lane*, not a trading system. The configuration below is the best-of-test variant, labelled as such; its purpose is to keep a live, cost-realistic record so that any future edge (new inputs, better entries) is measured against it.

```yaml
lane: level_sweep_fade_0dte          # best-of-144 by spread-model expectancy; expectancy still negative
universe: [SPY, QQQ, IWM]            # add ^SPX/^NDX/^RUT when index minute bars are licensed
session_window: "10:00-12:00 ET"     # 'morning'; no entries 12:00-13:15 or after 15:30 in any variant
levels:
  prior_session: [PDH, PDL]
  prior_week:    [PWH, PWL]          # five prior sessions
  premarket:     [PMH, PML]
  opening_range: [ORH, ORL]          # first 15 min, usable from 09:45
  dealer:        [CALL_WALL, PUT_WALL]   # prior-day UW gex-levels; FLIP and MAGNET used for gates only
entry:
  mode: sweep_reversal
  lookback_bars: 3
  max_closes_beyond_level: 1
  prior_side_requirement: ">=60% of the preceding 10 closes on the inside"
  reclaim: "close back inside by max(0.25*ATR14_1m, 0.02%)"
  direction: against the sweep (sweep of a high -> puts, sweep of a low -> calls)
  gate: posgamma_fade               # only when spot > prior-day gamma flip (dealers dampen); use continuation below the flip
  dedupe: one signal per level+direction per 10 min
  cooldown_per_ticker_min: 30
  max_entries_per_ticker_day: 5
  one_open_position_per_ticker: true
contract:
  expiry: 0DTE
  strike: nearest to spot
  side: call if bullish else put
  entry_price: VWAP of the first option bar after the signal minute; skip if none within 3 min or premium < 0.05
exit_engine: trail                  # best engine in test
  initial_stop_pct: -25
  breakeven_arm_pct: +6
  guardian_arm_pct: +15
  guardian_giveback: 0.35           # floor = 65% of high-water mark
  time_stop_min: 30                 # if not positive
  hard_close: "15:55 ET"
costs_reported: [mid, spread(1-2% half-spread + 0.70/side), adverse]
sizing: 1 contract (equal weight); never scale a paper lane
promotion_rule: lower 95% CI of spread-model expectancy > 0 over >= 150 trades spanning >= 3 months, and >= the random baseline by > 1 round-trip cost
status: NOT PROMOTABLE (2026-10-13 run: -2.4 [-4.1, -0.5] vs baseline -3.2)
```

Alternative lanes to keep alongside it, each a separate paper book with the same cost models and the random baseline computed automatically (`SLAYER_INDEPENDENT_IMPLEMENTATION_SPEC.md` §4–§6):
- `continuation` entries below the flip (tested: −$2.5 to −$3.1; same verdict).
- Dealer-magnet fades near walls (untested because walls alone produced the same losses in the sweep lane).
- Flow-burst watch (sus-strike analogue): display only; the public-tape test showed no stand-alone direction.
- Close-flush (MOC wick) lane: untested here; GeorgeFi's own recaps show large two-way moves without a measured net.

---

## 4. What would have to be true for this family to work

1. An input that times entries better than random. The member capture shows which inputs GeorgeFi has (per-strike bursts with 2-minute windows and baseline multiples, dealer accelerator changes, five-contributor votes). None of them has been shown to work; T8 of the validation plan (join those inputs with UW bars for several weeks) is the test.
2. Lower costs or larger premiums. On $1 contracts a 1 % half-spread plus fees is ≈ 3.4 % per round trip; the best mid-model expectancy is 0.5–1 %. Index contracts (SPXW at $5–10 premium, cash-settled) halve the proportional cost, which is where GeorgeFi's record is concentrated (^SPX 145 of 489 trades, +$5,234), but they could not be tested without index bars.
3. An exit engine that captures more of the frequent +25 % excursions without being stopped at breakeven first. 73 % of entries reached +25 %; the trail engine converts few of them because the breakeven lock fires on the way. A tuned engine (later breakeven arm, partial at +25 %, wider initial stop) should be tested on the same entries before any new entry logic.

---

## 5. Do-not-do list derived from the evidence

- Do not hold ATM 0DTE contracts to the close (−11 % of premium on average before costs).
- Do not treat a single additive confidence score or a letter grade as information; neither separated outcomes in GeorgeFi's record.
- Do not use "crowd inversion" as a mechanism; `crowd_mood` is an RSI band and the product trades with it, not against it.
- Do not report one-minute highs, recap peaks or 30-day scorecards as performance; report cost-adjusted closed trades with intervals.
- Do not go live on this lane.
