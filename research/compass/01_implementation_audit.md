# Compass implementation audit — Slayer Terminal (`hotterthenheat/3abida`)

Audited 2026-10-14 from the repository's only reachable commit (`d2553cc`, branch `claude/trusting-planck-o77m11`, dated 2026-10-14 05:14 UTC; the clone is shallow, so no earlier history was readable). Every statement below was checked in the source; file paths are repository-relative. Purpose: establish what Compass actually computes today, which parts are sound enough to keep as contracts, and what the research has to build, before any parameter is "reproduced".

## 1. Where Compass lives

| Surface | Files | Lines |
|---|---|---|
| Board `/compass`, setup page `/compass/:id`, Tracker `/compass/tracker` | `src/pages/compass/{Board,SetupPage,CompassLayout}.tsx`, `src/pages/Tracker.tsx` | — |
| Components | `src/components/compass/*` (19 files) | 4,327 |
| Engine | `src/data/compass.ts` | 755 |
| Board filing (kinds, structures, tags, listings) | `src/data/compassStandIn.ts` | 509 |
| Contract weigher | `src/core/contractScore.ts` | 391 |
| Types and product definitions | `src/types/compass.ts` | 401 |
| Expiry categories and the 0DTE rule | `src/data/expiryClass.ts` | 124 |
| Specs | `docs/compass-backtest-spec.md` (partner math, Aug 2026), `docs/compass-setups-2026-10-11.md` (the board's filters), `docs/compass-redesign-port.md` | — |

The app is React 18 + Vite + TypeScript; `server/` is the dev proxy for the vendor keys plus the Terrain field recorder; `scripts/*-proof.ts` are the test suite (`npm test`).

## 2. Verdict in one paragraph

**The Compass engine is a placeholder, by its own header** (`src/data/compass.ts` lines 3–7: "Placeholder advisory model. Deterministic per contract so rows stay stable across ticks. Swap this whole file for the real quant engine / ThetaData feed later"). Direction, score, targets, invalidation, momentum and "why" text are produced by a hash-seeded random number generator; the board's market state comes from a simulator with hand-set prices; the kinds, structures and tags on the board are assigned by hash (`compassStandIn.ts` header: "THIS IS THE STAND-IN MAPPING, TO BE REPLACED BY THE ENGINE"). **None of the parameters in the research brief — RSI 14, EMA 5/9/20/50/200, 1m/5m/15m confirmation, VWAP, relative volume, HH/HL structure, OI > 250, volume > 100, spread < 12 %, delta 0.30–0.60, expected-profit/worst-drawdown ranking — exist in the Compass code or in either repository's documents.** They are the owner's specification and have never been implemented, so there is no existing behaviour to reproduce; the "baseline" has to be built from the specification and then measured. What the repository does contain and is sound: the product definitions (sleeves, kinds, expiry categories, eligibility gate), the calendar and 0DTE logic, a correct indicator library used by the charts, Black-Scholes with fixture tests, real Unusual Whales and ThetaData feed clients, a point-in-time recorder for the Terrain room, a manual replay desk, and a serious method spec for judging candidates.

## 3. What the engine computes today (`src/data/compass.ts`)

| Output on the board | How it is computed | Reads the market? |
|---|---|---|
| Direction (call or put) | `tickerLean()`: `mulberry(hash(ticker-scanner-group))() > 0.42` — a fixed coin per ticker × scanner, 58 % bullish | No |
| Score (ENTER ≥ 88, WATCH ≥ 72, else EXIT) | `96 × (0.4 + 0.6 × proximity) × (aligned ? 1 : 0.55) ± 4 noise`, proximity = 1 − \|strike − spot\| / (3 % of spot) | Spot only |
| Premium, bid, ask | `estimatePremium()`: intrinsic + spot·σ√t·0.4·exp(−m²/2), floor $0.05 (not Black-Scholes); spread fixed at max($0.02, 3 % of mid) | Spot, IV from the simulator |
| Live mid, high-water | mid × U(0.9, 1.1); high-water from RNG | No |
| Take-profit ladder | [30 %, 80 %, 150 %] × (0.8 + 0.3·moveBias); HIT/IN PROGRESS from an RNG "progress" draw | No |
| Invalidation price and reason | spot ∓ U(0.8 %, 2 %); reason = random pick of four strings ("Dealer buy-wall support", …) | No |
| Expected move % | moveBias × sleeve multiplier × U(24, 46) | No |
| Health, momentum, chain HOLD/REDUCE/SELL | linear in moneyness ± 6 noise | Spot only |
| Sparkline, change % | seeded random walk | No |
| "Why" chips and text | fixed copy per scanner × side (`WHY_LIBRARY`) | No |
| Candidates per name | 3 strike rungs on the lean's side, keep ≤ 2 with score ≥ floor (80–90 by scanner) | Spot only |
| Greeks | `core/greeks.ts` Black-Scholes on the simulator's IV | Simulator |

Real logic in the same file: the **eligibility gate** `ELIGIBLE_SCANNERS` (scanner × sleeve), the setup-id address scheme, the clock-aware expiry resolution (`core/calendar`), `sleeveForDte`.

**Market state fed to the engine.** `Board.tsx:295` builds the universe with `Simulator.universeQuotes(...)` (`src/core/simulator.ts`, "SIMULATION ENGINE — Options Physics, Greeks Math, & Live Ticker Feed"): hand-set base prices (SPY 500, QQQ 440, AAPL 190, NVDA 120, IWM 221.7) and a `SCAN_ROSTER` of about twenty names with hand-set price and IV; `src/data/universe.ts` is a typed large-cap list with "reference price the deterministic feeds oscillate around". The board therefore sweeps about 25 simulated names, never the market.

## 4. The board's filing (`src/data/compassStandIn.ts`)

Built to the owner's 2026-10-11 instruction "build this in compass UI NO MATH OR BACKEND THIS IS ALL UI". Kind (Trend vs Breakouts: `h % 2`), structure (`h % 12`: long leg, debit spread, credit put spread, cash-secured put), Volatility membership (`h % 3`), tags (`unusual`: `h % 7`; `penny`: `h % 3`), event flag (`h % 5` / `h % 6`) are all hash draws. Listed expiration dates are **real** when Unusual Whales is up (`src/data/feed/listings.ts`) and a schedule otherwise. The structure arithmetic (debit, width, breakevens) is plain and correct for the legs it is given, but the legs are priced by `estimatePremium`.

## 5. The contract weigher (`src/core/contractScore.ts`)

Real Black-Scholes (r = 4.5 %, time floored at half a day) and a six-factor composite with hand-set weights per horizon. Its inputs are not market data: `ivRank = hRange(ticker-day-ivr, 12, 92)` (random), `baseIv = 0.18 ± … + hRange(0, 0.25)` (random), skew `iv × (1 + 1.6·|moneyness|)` (assumed), OI from the simulator's chain, spread = f(OI) formula, flow from the simulated dark-pool posture, news from simulated sentiment, trend = `ema9 ≥ ema21` and RSI from the simulator's indicators. The file records that it was "DEMOTED FROM STATE AUTHORITY (2026-08-30)"; the state users see comes from `makeSetup`.

## 6. What is real and worth keeping

| Component | File | Assessment |
|---|---|---|
| Product definitions: sleeves, scanners/kinds, option types, structures, expiry categories, eligibility gate | `src/types/compass.ts` | Keep as the product contract. Expiry categories differ from the brief (see §8). |
| 0DTE rule and categories (last trading day, AM-settled SPX monthlies, half days, holidays) | `src/data/expiryClass.ts`, `core/calendar.ts` | Correct date logic; reuse verbatim in the backtester's calendar. |
| Indicator library: EMA (seeded at first close, warm-up = period), session-anchored VWAP on typical price, Wilder RSI (null through the seed window), MACD, Bollinger, SMA, VWAP σ, ATR | `src/data/indicators.ts` | Correct implementations, used by the charts and the Dossier's trend read (`stockOverview.ts`: rsi14, ema20, sma50, sma200, adx14). Not used by Compass. The research engine must match these conventions (EMA seeding in particular) so a ported signal reproduces. |
| Black-Scholes and Greeks | `src/core/greeks.ts`, `scripts/fixture-proof.ts` | Fixture-tested against the partner spec (7/7). |
| Unusual Whales client: flow alerts, option trades, net premium ticks, market tide, spot GEX by strike/expiry, Greek exposure, OI per strike, max pain, dark pool, earnings, chains, contract intraday/historic, OHLC 1m/5m/1d, flow per strike/expiry, stock screener | `src/data/feed/uw.ts` (1,412 lines) | Real, with provenance and failure words. History floors are the vendor's (documented in `georgeredo/DATA_PROVIDER_AUDIT.md` §6). |
| ThetaData client via the local Theta Terminal: stock 1-minute bars (≤ 1 month per call), stock EOD (≤ 1 year per call), contracts that quoted on a date, a contract's minutes folded from its own trades (VWAP per minute) | `src/data/feed/theta.ts`, `server/feed.ts` | Real. **No NBBO path**: contract minutes are trade-derived, so the app cannot yet price a fill at the bid or ask. The research engine uses ThetaData's quote endpoints directly (gRPC client in `georgeredo/research`). |
| Point-in-time field store for Terrain: two rows a minute (shown/final), append-only, rebuild-equality checks, scorecard | `server/fieldStore.ts`, `fieldRecorder.ts`, `fieldBackfill.ts`, `scorecard.ts` | Sound discipline; the "final must equal rebuild" rule is exactly what the Compass journal needs. Scope is dealer-gamma columns for the recorded names, not Compass. |
| Practice › Backtest replay desk: one clock, forward-only, ask/bid fills on the house tape, dead-quote refusal, $0.65/contract, TP/stop ladder, report | `src/data/review/engine.ts`, `docs/review-backtest-rules.md`, `src/data/feed/backtest.ts` | A manual trading replay, rules well specified. On **real days** a contract is priced at its own minute trade VWAP and fills at that price (no spread), untraded minutes refuse fills — optimistic versus an ask/bid fill. It runs no scanner, has no universe, no walk-forward; it is not a strategy backtester. |
| Partner method spec | `docs/compass-backtest-spec.md` | A judging pipeline, not a strategy (its own §0: "not a single entry rule, threshold, or coefficient"). Rulings worth inheriting as constraints: availability-timestamped features; candidates frozen before scoring; fills at mid ± κ·spread/2 (midpoint-only prohibited); Utility = EV − 1.0·ES95 in dollars; SetupScore as a historical percentile with N_eff ≥ 200 before any 0–100 is shown; a mandatory no-trade gate; purged and embargoed walk-forward; every scored candidate journaled, not only recommendations; invalidation = session close through the level ± max(0.1·ATR, tick), fixed at entry; dealer-sign prior −0.55/−0.53 ± 0.20 with a q = 0 stress. The spec's quick-scalp (H ∈ {5, 15, 30, 60, 120} min, first-passage target-before-stop) and rebounds (touch of a qualified level, target S + α·ATR, invalidation L − β·ATR) sleeves define two of the brief's setup families. Status: the "snapshot builder" it names as the next arc was never built (no code found). |

## 7. Defects and gaps (what the research must not inherit)

1. **No signal logic.** No RSI, EMA, VWAP, relative-volume, structure or multi-timeframe code is wired to Compass; the indicator library exists but only the charts call it.
2. **No market data behind the board.** Simulator prices and IVs; about 25 names; no chain, OI, volume or quotes from a vendor on the Compass path.
3. **Random outputs presented as analysis.** Direction, score, targets, invalidation reasons, momentum, tags, kinds and structures (§3–§4). Anything the board currently shows is not evidence about any strategy.
4. **A non-Black-Scholes pricer with a fixed 3 % spread** mints every premium, bid and ask (`estimatePremium`), and the structure figures are built on it.
5. **Three inconsistent DTE bucketings** in code: `EXPIRY_CATS` (0 / 1–7 / 8–45 / 46–90 / ≥ 91, LEAPS a tag past ~270), `sleeveForDte` (0 / ≤ 6 / ≤ 90 / else), `horizonForDte` (≤ 1 / ≤ 10 / ≤ 120 / else). The brief specifies a fourth (0 / 1–7 / 8–30 / 31–90 / 91–364 / ≥ 365).
6. **No NBBO in the app's option path**; the replay desk fills at trade VWAP.
7. **No candidate journal, no no-trade records, no walk-forward harness** — the spec's gaps #2 and #3 remain open.
8. **The Dossier's trend read** (`stockOverview.ts`) carries real indicator values from UW daily bars (rsi14, ema20, sma50, sma200); it is a display, not a signal, and uses different periods from the brief.

## 8. The brief's parameters against the repository

| Brief | In 3abida | In georgeredo |
|---|---|---|
| RSI 14 | Chart indicator label (`gex/indicatorItems.ts`), Dossier `rsi14` from UW daily bars, simulator RSI | GeorgeFi's `crowd_mood` label reproduced by RSI(14, 1-min) (`SLAYER_INDEPENDENT_IMPLEMENTATION_SPEC.md` §59) — GeorgeFi-derived, kept separate |
| EMA 5, 9, 20, 50, 200 | Chart EMA 9/21; Dossier EMA 20, SMA 50, SMA 200. No EMA 5. | None |
| **EMA 15** | **Not present anywhere** (no `ema15`, no "EMA 15" in code or docs) | **Not present** |
| 1m / 5m / 15m confirmation | None (charts offer timeframes; no confirmation logic) | None |
| VWAP positioning, relative volume, HH/HL structure | VWAP series exists (`indicators.ts`); no relative-volume or structure code | None |
| OI > 250, volume > 100, spread < 12 % | None | 12 % appears only as the GeorgeFi ETF spread *proxy* in the fill model |
| Delta 0.30–0.60 | Spec sheets: 0.25–0.55 (weekly), 0.35–0.65 (swing); `STEADY_DELTA = 0.5` splits Steady/Big Payoff | None |
| Expected profit / expected worst drawdown ranking | Named as the future Top Setups order (`compass-setups-2026-10-11.md` "Awaiting the engine"); not computed | §12 of the brief |

**EMA 15 resolution.** There is no EMA 15 indicator or EMA-15 target in either repository, so the inconsistency the brief refers to is between the brief's own list (which has no 15) and a reference elsewhere. Decision recorded for the baseline: the indicator set is RSI 14 and EMA 5/9/20/50/200 on each timeframe; "EMA 15" is treated as a reference to the **15-minute timeframe's EMAs** (the directional-alignment timeframe) unless the owner says otherwise; no additional EMA 15 series is computed, and every EMA target on the underlying uses one of the five listed periods. If a later document shows "EMA 15" was a sixth series, it is added to the parameter grid as a candidate, not to the baseline.

## 9. Consequences for the research plan

1. **Baseline = specification, not code.** The brief's configuration is implemented once, in the research engine, exactly as written, and its measured results are the "baseline reproduction". There is no existing output to match.
2. **The engine is built outside the app** (`georgeredo/research/compass/engine/`, Python, ThetaData gRPC client with NBBO), because the app's option path has no quotes and its universe is simulated. The deliverable back to `3abida` is a machine-readable configuration plus a port specification for replacing `src/data/compass.ts`, keeping `types/compass.ts`, `expiryClass.ts` and `core/calendar.ts` as the contract.
3. **Conventions are inherited from the app** so the port reproduces: EMA seeded at the first close, session-anchored VWAP on typical price, Wilder RSI with a null seed window, the 0DTE/last-trading-day rule, AM settlement, and the partner spec's fill rule (never midpoint), journal-every-candidate rule and no-trade gate.
4. **DTE categories**: the research uses the brief's six categories (0DTE, Weekly 1–7, Swing 8–30, Position 31–90, Long-Dated 91–364, LEAPS ≥ 365) and reports a mapping to the app's five; the port specification proposes unifying `EXPIRY_CATS`, `sleeveForDte` and `horizonForDte` on one table.
5. **Nothing from the simulator, the stand-in mapping or the board's current output is evidence** and none of it is carried into the registry.
