# Port specification — what Slayer Terminal (`3abida`) should take from this research (2026-10-14, interim)

Scope: the changes to `3abida` that follow from `01_implementation_audit.md` and the results in `05_results.md` and `registry.jsonl`. This document is updated when S02 (grid walk-forward), S03 (weekly expirations) and S06 on the Tier A universe finish; until then its conclusions rest on S01, S04, S06 (index ETFs), S07 and S08.

## 1. The position today

No Compass configuration tested so far meets the promotion gates (`registry.jsonl` `GATE-v2`; `04_protocol.md` §10). The owner's baseline on index 0DTE products loses before costs (S01); its entry rule carries no forward information on the underlying (S04); none of the catalogue's intraday triggers do on index ETFs over nine years (S06); at daily resolution across ~1,100–1,500 liquid single names the breakout and pullback triggers are followed by *under*performance and earnings beats are sold after the gap (S07, S08). The app's Compass path is a hash-seeded placeholder (`src/data/compass.ts`) whose scores, directions, targets and tags are random. The honest port therefore has two parts: (a) replace the placeholder with an engine whose outputs are either measured or absent, and (b) ship **no recommendation** until a configuration passes the gates.

## 2. Keep (the product contract)

| Keep | Where | Note |
|---|---|---|
| Sleeves, kinds, structures, option types, eligibility gate | `src/types/compass.ts` | Unchanged as the vocabulary. |
| Expiry categories | `src/types/compass.ts` `EXPIRY_CATS`, `src/data/expiryClass.ts`, `core/calendar.ts` | Replace the three DTE tables (`EXPIRY_CATS`, `sleeveForDte`, `horizonForDte`) with one table using the brief's six categories, computed from the *last trading day* and calendar days: 0DTE = 0; Weekly 1–7; Swing 8–30; Position 31–90; Long-Dated 91–364; LEAPS ≥ 365. The research engine's `engine/calendar.py::expiry_category` is the reference, including AM-settled SPX monthlies and early closes. |
| Indicator library | `src/data/indicators.ts` | The research engine (`engine/indicators.py`) matches its conventions: EMA seeded at the first close, Wilder RSI with a null seed window, session-anchored VWAP on typical price. A ported signal reproduces to the bar. |
| Black-Scholes and Greeks | `src/core/greeks.ts` | `engine/greeks.py` uses the same model (continuous yield, delta = e^{−qT} N(d1)); implied vol by bisection on the NBBO mid with r = 0.04, q = 0 stated. |
| Unusual Whales and ThetaData clients | `src/data/feed/uw.ts`, `src/data/feed/theta.ts` | Keep. The ThetaData client needs the quote path (§4). |
| Point-in-time field store, replay desk, partner method spec | `server/fieldStore.ts`, `src/data/review/*`, `docs/compass-backtest-spec.md` | Keep; the spec's rulings (fills never at midpoint, candidates frozen before scoring, journal every candidate, no-trade gate, purged walk-forward) are the ones the research engine enforces. |

## 3. Replace

| Replace | With | Reason |
|---|---|---|
| `src/data/compass.ts` (hash-seeded advisory model) | A thin client of the research engine's outputs: for each (symbol, session, minute) the engine's *measured* candidate rows (`trades.parquet` schema: signal time, direction, family, contract, delta, spread, fills, exits) and, in live mode, the same rules evaluated on live bars and the live chain | The current outputs are random numbers presented as analysis (`01_implementation_audit.md` §7.3). |
| `src/data/compassStandIn.ts` (kinds/structures/tags by hash) | Kinds from the engine's family that fired (`quick_scalps`, `trend_plays`, `breakouts`, `bounces`, `earnings`), structure = single long call/put until a multi-leg family is validated | Same. |
| `src/core/contractScore.ts` (random IV rank, 3 % fixed spread pricer) | `engine/contracts.py::select` logic: expiration by category; strikes with delta in [0.30, 0.60] from the mid-implied vol, nearest 0.45; spread < 12 % of mid; ask ≥ $0.05; OI > 250 and intraday volume > 100 where the chain carries them; rejection reasons returned, not hidden | The app's pricer is not Black-Scholes and its spread is invented. |
| `core/simulator.ts` as the board's market state | Live bars (ThetaData 1-minute OHLCV) and the live chain NBBO | No evidence can come from simulated prices. |

## 4. Add

1. **An NBBO path in the ThetaData client.** Contract minutes are currently folded from trades (VWAP); fills must be priced at the ask (buy) and bid (sell) of the 1-minute NBBO, exactly as `engine/sim.py` does. Without it the app cannot show a cost-correct P&L for any candidate.
2. **The configuration file as the only source of parameters.** `research/compass/config/compass_config.schema.json`; the app loads a versioned config (`compass_config.vN.json`) and refuses to score when `status != "validated"`. The current config `v0.baseline` is `baseline_unvalidated`; the final config this research delivers carries `status: "no_validated_configuration"` unless a pending study passes the gates, with the rejected configurations and their numbers listed in it.
3. **A no-trade gate on the board.** When no family has a validated configuration, the Compass board shows the measured state ("no validated setup; last evaluation 〈study〉, 〈mean〉 [〈CI〉]") rather than a ranked list. This is the partner spec's mandatory gate, applied at the product level.
4. **Journal every candidate** (`server/fieldStore.ts` discipline, two rows a minute shown/final) for the Compass path, so that the live rule's forward performance accumulates as evidence with the same statistics the research uses (day-clustered intervals, matched random baseline).
5. **Ranking** = expected net profit ÷ expected worst drawdown, computed from the engine's measured distribution per (family, category, symbol class) on the validated window; never from a pricer. Until a configuration is validated the ranking has no inputs and is not displayed.

## 5. What not to port

- Nothing from `compass.ts`, `compassStandIn.ts`, `contractScore.ts` or the simulator (audit §9.5).
- The GeorgeFi-derived rules in `georgeredo` (`SLAYER_INDEPENDENT_IMPLEMENTATION_SPEC.md`, `STRATEGY_SPEC.md`): kept distinct from Compass by the owner's rule; their results (`03_reconciliation.md`) are negative after costs at the gate's standard.
- The two exploratory leads in S07/S08 (fade 20-day breakouts in single names at 21 sessions; sell the beat) — they are of a size that only a short-premium or spread structure could carry, outside the long-option scope until the owner decides; if opened, they go through the protocol as new pre-registered hypotheses.

## 6. Acceptance for a future validated configuration

A configuration is portable when, in `registry.jsonl`, it has: a positive day-clustered lower bound out of sample over at least three test years; ≥ 150 trades over any three months; a positive paired difference against its matched random baseline; robustness to the adverse-fill scenarios; and the same sign in every walk-forward fold. The config file then carries `status: "validated"`, the study id, the config hash and the result directory, and `compass.ts` is permitted to score.
