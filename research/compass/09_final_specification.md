# Final parameter specification — Compass (DRAFT, pending S02 walk-forward, S03 weekly expirations, S06 on Tier A)

The brief asked for the exact recommended parameters, entry and exit logic, contract rules, expiration- and setup-specific settings and the ranking formula, with after-cost, out-of-sample, year-by-year, regime and baseline results, and the failed configurations — and, if no configuration meets the standard, to say so. This document is the answer as the evidence stands; the sections marked *pending* are filled when the three running studies finish. Every number is in `registry.jsonl` and `05_results.md`; the machine-readable form is `config/compass_config.v1.json`.

## 1. Verdict

**No Compass configuration tested meets the promotion gates (`GATE-v2`: positive day-clustered lower bound out of sample over at least three test years, ≥ 150 trades per three months, beats its matched random baseline, robust to adverse fills).** The owner's baseline loses before costs on every index product with same-day expirations; its entry rule and every other entry trigger in the catalogue carry no forward move on the underlying; at daily resolution across the liquid single-name universe the continuation setups predict the opposite sign and there is no post-earnings drift to buy. The recommended parameter set is therefore **none**; the recommended production state is **no-trade** (`status: no_validated_configuration`), with the engine, the configuration contract and the port specification delivered so that any future configuration is measured the same way before it is shown.

## 2. The owner's baseline, as specified and as measured

| Parameter (brief §4) | Implemented as | Evidence |
|---|---|---|
| RSI 14 crossing 55 / 45 on 1-minute closes, close beyond EMA 9 (lead) | `engine/signals.py::baseline_events` | S01, S04, S09 |
| EMA 5 / 9 / 20 / 50 / 200 on 1m, 5m, 15m, 30m, 1h, daily; "EMA 15" = the 15-minute timeframe (audit §8) | `engine/signals.py::features` (`bars.align_closed`, no look-ahead) | — |
| 1m lead → 5m confirmation (close beyond EMA 20 and VWAP) → 15m alignment (EMA 20 vs 50, price on the right side) | same | S04 ablations |
| Session VWAP; relative volume ≥ 1.0 vs the same minute of the prior 20 sessions; HH/HL (LL/LH) on 5-minute pivots | same | S04 ablations |
| Contract: delta 0.30–0.60 (nearest 0.45) from the NBBO-mid implied vol; spread < 12 % of mid; OI > 250; intraday volume > 100; ask ≥ $0.05 | `engine/contracts.py::select` (OI/volume filters where the chain carries them) | S01, S09 |
| Exits: swing-level invalidation, VWAP loss, −25 % stop, +25 % on half, +50 % on the rest, next 15-minute EMA level, 60-minute hold, 15:50 cutoff | `engine/sim.py` | S01, S02 |
| Fills ask in / bid out at the 1-minute NBBO; $0.70 per contract per side | `engine/sim.py` | C1 |
| Ranking = expected net profit ÷ expected worst drawdown | `engine/walkforward.py` objective `ep_ewd` | S02 (pending) |

Measured (Quick Scalps, same-day expirations, the only category whose chains were complete at this version):

| study | instruments | window | trades | mean $/contract [95 % CI] | win | PF | vs matched random | years negative |
|---|---|---|---|---|---|---|---|---|
| S01 | SPY, QQQ, IWM | 2022-11 → 2026-10 | 2,886 | **−4.19 [−5.68, −2.81]** | 34.3 % | 0.73 | −2.03 [−3.18, −0.90] | 4 of 4 |
| S09 | SPXW | 2022-05 → 2026-10 | 1,229 | **−46.18 [−63.19, −30.02]** | 33.8 % | 0.70 | −24.09 [−39.45, −9.28] | 4 of 5 (2024 −15.8 [−42.5, +10.0]) |

Regime: worst in the top VIX tercile (S01: −7.18 [−10.04, −4.42]) and in the 13:30–14:29 entry hour (−7.02); no event-day pattern. Direction: puts worse than calls on every product. Exit mix: the −25 % stop ends about half of all trades.

## 3. Why no exit, contract or expiration setting can rescue it

S04 and S06 measure the entry on the underlying alone, 2017 → 2026, about 450,000 trigger events on three index ETFs: the baseline rule's minutes are followed by −0.7 to −1.6 bp over 30 minutes while random minutes on the same days and sides collect +4.6 to +7.7 bp; the RSI cross alone carries 0.0 bp at every horizon; every other catalogue trigger (VWAP reclaim, 5-minute EMA cross, breakout, retest, trend pullback, bounce) sits within ±1 bp of zero at 30 and 60 minutes; the filter stack makes each trigger later, not better. A long option on an entry whose underlying expectation is ≤ 0 loses its spread and theta whatever the exit rule — the cost hurdle in underlying terms is about +3 bp over 30–60 minutes on SPY-class names (protocol A1). No cell cleared it.

## 4. Families and categories tested

| family | category | instruments | window | result | status |
|---|---|---|---|---|---|
| Quick Scalps | 0DTE | SPY, QQQ, IWM, SPXW | 2022 → 2026 | S01, S09 above | **rejected** |
| Quick Scalps | 0DTE, 41 single-factor variants | SPY, QQQ, IWM | 2022 → 2026 | S02: no variant positive or better than random; walk-forward OOS -3.81 [-5.23, -2.35] | **rejected** |
| Quick Scalps (owner rule, weekly expirations 1–7 days, OI/volume filters) | Weekly | SPY, QQQ, IWM | 2017 → 2026 (stratified sample of sessions) | S03: +$1.27 [−3.69, +6.25] = random | **rejected (zero, not negative)** |
| Trend Plays, Breakouts, Bounces (intraday triggers) | — (underlying screen) | SPY, QQQ, IWM | 2017 → 2026 | S06: nothing promoted | **not promoted** |
| Trend Plays, Breakouts, Bounces, Earnings/Events (intraday) | — | Tier A single names | 2017 → 2026 | S06 on Tier A | *pending (bars pulling)* |
| Breakouts, Trend Plays, Bounces (daily triggers) | Weekly / Swing / Position (underlying screen) | ~1,100–1,500 liquid names per year | 2024 → 2026 | S07: nothing promoted; breakouts −81 bp and pullbacks −97 bp adjusted at 21 sessions | **not promoted** |
| Earnings/Events (daily) | Weekly / Swing / Position (underlying screen) | same, 10,439 reports | 2024 → 2026 | S08: nothing promoted; beats underperform after the gap | **not promoted** |
| Cheap Options | any | — | — | not run: no entry with a positive underlying expectation exists to attach it to (protocol §13) | **not run** |
| Long-Dated, LEAPS | 91–364, ≥ 365 days | — | — | no family in the catalogue has an entry whose horizon justifies them; nothing to test until one does | **not run** |

## 5. Failed configurations

1. The owner's baseline on SPY/QQQ/IWM 0DTE (S01) and on SPXW 0DTE (S09) — §2.
2. Every single-factor variant of the baseline (S02): 41 variants, none with a positive lower bound or better than its random control; walk-forward out of sample −$3.81 [−5.23, −2.35] (lower-bound objective) and −$2.49 [−7.32, +2.46] (expected profit ÷ worst drawdown) — `results/v1/s02_walkforward/REPORT.md`.
3. The baseline entry rule and its ablations on the underlying (S04); the seven intraday triggers × four filter sets on index ETFs (S06).
4. Five daily triggers × two filter sets on the single-name universe (S07); nine earnings cells × two entries (S08).

## 6. Exploratory leads (not recommendations)

Two daily-resolution effects have the wrong sign for the catalogue but a consistent one: fading 20-day breakouts in liquid single names (+81 bp [+33, +133] absolute at 21 sessions, S07) and selling the beat after earnings (−86 bp [−136, −39] adjusted at 21 sessions for top-tercile beats, S08). Neither clears a long option's theta and spread (port spec §5); each is of the size a short-premium or spread structure could carry. They are recorded as hypotheses for the owner's decision on scope; if opened, they go through the protocol as new pre-registered studies with chains.

## 7. The best defensible result

Do not ship a Compass recommendation. Ship the measurement: the engine (`engine/`, 30 tests), the configuration contract (`config/compass_config.schema.json`, `v1.json` with every family disabled and the rejection list), the port specification (`08_port_spec_3abida.md`) and this record. The app's board should show the measured state and the no-trade gate until a configuration passes the gates. This is the result the evidence supports; a positive number could only have been produced by changing the question, which the protocol forbids.

## 8. What would change the verdict

A cell in S02's walk-forward with a positive out-of-sample lower bound in every test year; a weekly-expiration cell in S03 with a positive lower bound and a positive paired difference against random; or a single-name intraday trigger in S06 (Tier A) with an absolute lower bound ≥ +3 bp at 30–60 minutes *and* a positive paired difference. Each would then need the adverse-fill scenarios and three-month trade counts before the config's status could move to `research_candidate`.

*Pending sections are completed and this header removed when S02, S03 and S06-Tier A are recorded.*
