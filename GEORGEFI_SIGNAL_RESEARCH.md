# GEORGEFI_SIGNAL_RESEARCH

Signal observations, reconstructed rules, candidate explanations, contradictions and confidence levels. All numbers come from the files in `evidence/` and can be regenerated with the scripts in `evidence/scripts/`.

Vocabulary: **Observed** = seen in a response; **Calculated** = computed by us from observed data; **Inferred** = our explanation; **Unknown** = not determinable from available evidence. "GeorgeFi says" = the operator's own published description (`/how`, `/guide`, `/docs/api`, `/mcp`), which is a claim, not an observation.

---

## 1. Datasets used

| Id | Content | Size | File |
|---|---|---|---|
| D1 | Epoch-2 closed-trade ledger (documented `GET /api/trades`) | 489 trades, 2026-03-02 → 2026-10-08, every field incl. the confluence ledger | `evidence/public_api/trades_all.json.gz` |
| D2 | Public signal tape, 8 sessions (`/api/public/todays-signals?date=`) | 972 alerts | `evidence/public_api/todays_signals_history/`, parsed: `evidence/analysis/public_tape_signals.csv` |
| D3 | Recap alerts with entry/peak/exit (SSR payloads) | 147 alerts, 9 sessions | `evidence/analysis/recap_alerts.csv` |
| D4 | Live decision snapshots (`/api/analysis`) | 20 decisions × 3 snapshots at writing (collector keeps running) | `evidence/public_api/analysis.json`, `evidence/analysis_snapshots/` |
| M1 | UW 1-minute contract bars for every D1 contract/day | 506 files | `evidence/validation/uw_bars.tar.gz` |
| M2 | UW 1-minute bars for every D2 contract/session | 643 files | `evidence/validation/uw_tape_bars.tar.gz` |
| M3 | Massive 1-minute bars (cross-check, partial because of the 5/min limit) | see `fetch_log.txt` | `evidence/validation/massive_bars_partial.tar.gz` |

---

## 2. Signal taxonomy (Observed)

### 2.1 Decision objects (`/api/analysis`, 20 tickers)
Per ticker: `direction` (BULLISH/BEARISH), `action` ∈ {WATCHING, WATCHING (Pending Entry), WAITING FOR TRIGGER, DO NOTHING, BUY_CALLS/BUY_PUTS, BLOCKED: <reason>}, `confidence` 0–100, `setupGrade` A+/A/A-/B+/B/B-, `contract` ("0DTE $7800 P" / "1DTE $100 P" / "SELECTION_FAILED"), `premium`, `optionSymbol` (OCC), `confluenceSignals[]`, `reason`, `watchLevels`, `gexProfile`, `ictProfile`, `crowd_mood`, `rsi`, `sparkline[20]`, `volumeAnalysis` ("NORMAL: VIX 15.2 - Standard market conditions"), `isChopDay`, `shouldWaitForPM`, `chopState`.

Block reasons seen: `Chop Day Inside Or`, `Too Many Penalties`, `Sweep Buy High 56`, `0dte Chase+Climax`, `Unanimous Structure Be…`, `Ob Bull Mid 49`.

### 2.2 Public tape subsystems (D2, 972 rows over 6 trading sessions)
`sus-strike` 498 · `hold-advisor` 232 · `momentum-ignition` 91 · `index-read` 35 · `relative-burst` 23 · `moc-wick` 19 · `block-sniper` 17 · `big-print` 13 · `feed-headline` 13 · `accumulation-sniper` 11 · `script-flip` 6 · `power-hour` 5 · `anchor-book` 5 · `trade-now` 3 · `chop-day` 1 (+ `opening-range`, `volume-crescendo`, `5m-wick`, `press-terminal` on 10/13).
Kinds: STEALTH LIGHT/BUILDING/HEAVY, BURST STRONG/EXTREME, KILLER STRONG/EXTREME/MODERATE, SUSTAINED · WATCH, BANG · WATCH, DIVERGENCE STRONG, HEARTBEAT · WATCH, FULL SIZE, SMALL SIZE OR SKIP, FLIP, RETRACTION INVALIDATED, WICK PRINTED/CONFIRMED, MOC GAME PLAN, FAST-MONEY FOLLOW, PRICE TEST, POSITIONING SHIFT, ROLLED, EXIT SUSPECTED, and hold-advisor states HOLDING STRONG / TRIM / LOCK MOST / EXHAUSTING / GET OUT / EXPIRED HOLD.
Direction field: `sus-strike` LONG 235 / SHORT 192 / blank 71; `momentum-ignition` and `relative-burst` always blank (size, not direction — matching the guide's "SURGE shows where size is, never which way"); `index-read` mostly blank with FULL SIZE / FLIP carrying a side.

### 2.3 Recap families (D3)
`full_size` 77, `moc_wick` 35, `surge` 23, `buy_and_forget` 9, `apex_unwind` 3. Postures: FULL SIZE 60, SURGE 23, HALF SIZE 22, WATCH 19, LOTTO 10, SIZE UP 5, BUY & FORGET 4, PLAN 2, BUY NOW 1, STAND ASIDE 1. Exit kinds: GET OUT 50, STOPPED 12, LOCK MOST 6, EXIT 3, none 76.

### 2.4 Trade ledger (D1)
Books: all 489 in `v2.0.0-ict` "ICT Main". 429 in the 0DTE account, 60 in the Swing account; 451 SCALP / 38 SWING by trade type. Contracts: 0DTE 429, 1DTE 13, 4–13 DTE for swings. Tickers: ^SPX 145, QQQ 104, SPY 70, IWM 34, ^RUT 23, META 16, ^NDX 16, GLD 15, TSLA 9, GOOGL 8, ROKU 7, 16 others ≤ 6 each. Size 1 contract in 349/489. Entry premium medians: ^SPX $6.55, ^RUT $5.50, ^NDX $9.98, QQQ $1.55, SPY $2.01, IWM $2.09. Strike moneyness at entry (Calculated): ^SPX median +0.11 % OTM (22 % ITM), QQQ −0.05 % (62 % ITM), SPY −0.15 % (72 % ITM), IWM −0.51 % (89 % ITM), ^RUT −0.01 %, ^NDX +1.12 % OTM (0 % ITM) — i.e. ATM for indices, slightly ITM for ETFs, OTM for NDX.

---

## 3. Reconstructed decision pipeline (Observed structure, Inferred semantics)

The `confluenceSignals` ledger on each trade is an ordered list of ~60–100 tags of the form `FAMILY:VALUE[:MODIFIER]`, many carrying explicit point deltas (`+15`, `-20`). The order and the cap tags reveal an additive pipeline:

1. **Context tags** (no points): `PREMARKET:BULLISH|BEARISH`, `PM:STRONG_GAP`, `REGIME:NORMAL|EXPANSION|EXTREME_EXPANSION`, `VOL:NORMAL|DELTA_BUYING|DELTA_SELLING|DELTA_BALANCED`, `KILLZONE:NY_OPEN|NY_AM_SILVER_BULLET|LONDON_CLOSE|NY_CLOSE`, `MACRO_TIME:10:00`, `EM:WITHIN_1SD|NEAR_1SD_BOUNDARY|EXHAUSTED(204%)`, `EXPECTED_MOVE:0.4%`, `VIX:ELEVATED_24.3`, `CORR:LOCKSTEP|NORMAL|DIVERGENCE|CHAOS`, `DAY_TYPE_GATE:CPI|VIX_SETTLE|OPEX_*`.
2. **Structure reads**: `STRUCT:BULLISH:CONFIRMS|CONFLICTS`, `BOS:UP|DOWN`, `CHoCH:UP|DOWN`, `OB_BULL:24` / `OB_BEAR:24` (strength), `BREAKER_BULL:29`, `BREAKER:MULTI_CONFLUENCE|RESPECTING|VERY_NEAR|FRESH`, `OTE:ALL_OBS_INVALID|GAP_STRUCTURE_UP`, `LIQ_BUY:95` / `LIQ_SELL:95`, `SWEEP_BUY:n` / `SWEEP_SELL:n`, `MTF:DAILY_ALIGNED|WEEKLY_CONFLICT|…`, `WP:<weekly profile>:CONFIRMS|CONFLICTS`, `VWAP:ALIGNED|CONFLICT:<dir>`, `ICT:FVG|SWEEP|DISPLACEMENT`, `JUDAS:BEARISH|BULLISH|DIRECTION_FLIP`, `AMD:EXTENDED_ACCUMULATION|CHOPPY|TIGHT_RANGE|MANIPULATION_INCOMPLETE`.
3. **Scored bonuses/penalties** (points explicit): `ENTRY_MODEL:SWEEP+15|DISPLACEMENT+10|FVG+5`, `SWEEP_ALIGNED:+25(PDH)`, `MULTI_SWEEP:+35(5x:…)`, `TRIPLE_CONF:+55(PDL+BULLISH+NEGATIVE_GAMMA)`, `LEVEL_PROXIMITY:+15(GEX_SUPPORT@0.01%)`, `SMT:ALIGNED:+15|CONFLICT:-20`, `GAMEPLAN:ALIGNED:+10`, `GEX:NEGATIVE_GAMMA+10(explosive)|PIN_PROXIMITY-15`, `VIX_GEX:GAMMA_CONFLICT-5|DOUBLE_EXPLOSIVE+15`, `INST:MULTI_TICKER_CONFIRMATION+20(EXTREME)`, `IMB:1D_BULLISH_ACTIVE:+25|CAP_HIT:-15`, `PDA_CI:DISCOUNT:-20`, `TREND:CHASING_CONTINUATION-10`, `SWEEP_CONFLICT:-30(ORL)`, `PENALTY:BULLISH_BREAKER:-10`, `BONUS:BEARISH_BREAKER:+10`, `DARK_POOL:ALIGNED+15|CONFLICT-20`, `DXY:ALIGNED:+20`, `LUNAR:FULL:+5`, `GENOME:CODON:AAA(TREND):+15`, `PHYSICS:RICCI_SHOCK+5`, `SESSION_ADJ:+20|+15|+10|-10|-30`, `CONSENSUS_BONUS:+10…+45`, `MACRO_TIME_BOOST:10:30:+5`, `CHASE_PENALTY:0DTE(-1.6%_in_126min,-35)`.
4. **Caps and floors**: `BONUS_CAP:55->20` (total bonus capped at 20), `SWEEP_FLOOR:51->65` (sweep setups floored at 65, matching GeorgeFi's "confidence floors at 60/70"), `CONFIDENCE_CAP:100->82:CRITICAL_CONFLICT_CLUSTER`, `GRADE_CAPPED:A+→A:STRUCTURAL_CONFLICTS`, `CRITICAL_CONFLICT_CLUSTER:2|3|4`, `CASH_SETTLED_CAP_TIER:5.0%`, `WIN_AFTER_LOSS_REDUCTION:0.5x:4→2`, `DIRECTION_LOSS_STREAK:2`, `DAILY_LOSS_PENALTY`.
5. **Gates / blocks / bypasses**: `CHOP_DAY_BLOCK:INSIDE_OR_WAIT_FOR_PM`, `LUNCH_BLOCK:12:00-1:15PM`, `PM_DEAD_ZONE:14:00-14:50`, `ENHANCED_CHOP_BLOCK:CONFIRMED_63`, `SNIPER_GATE:ALLOW:BULLISH(3/4)|BLOCK:WEAK(1/4<3)`, `FLOOR_BLOCKED:CONFLICTS`, `SWEEP_BLOCKED:PREMARKET_LEVEL(PMH)`, and matching `*_BYPASS` tags (`INST_BLOCK_OVERRIDE:LUNCH_CHOP_BLOCK`, `GATE_TRUST_BYPASS:…`, `REALITY:CLIMAX_BYPASS`, `OB_WEAK_BYPASSED:QUALITY_SETUP`).
6. **Sizing**: `CONFLUENCE_SIZE:MULTI_SWEEP_3PLUS:1.20x`, `HELIX_SIZE:FRAGILE_CAP`, `CONVICTION_TIER:WARM:1_classes|HOT:2_classes`, `CONVICTION_AXES:S+35,F-15,R-25,T+15,I+0,G+25` (six axes: structure, flow, regime?, timing, institutional, gamma — names inferred from initials).
7. **Grade**: `A_SETUP`, `APLUS_SETUP`, `A-_SETUP`, `B+_SETUP` (final), after caps.

Confidence (Observed): 0–100, median 72 on recorded trades; `confidencePreCap` equals `confidence` on every record (so the stored value is post-cap and the pre-cap copy is not populated). Confidence is **0 on all 204 trades before 2026-05-04** (not recorded then).

Inferred reading: the engine computes a base directional score from structure, adds capped bonuses, applies conflict caps, then floors sweep setups; the grade is a banding of the final score adjusted by conflict count. The exact band edges are **unknown** (grade is not a pure function of recorded confidence: A+ trades have confidence 82–100 and so do A trades).

Era note (Calculated, `evidence/analysis/trades_eras.txt`): tag families `GENOME`, `PHYSICS`, `HELIX_*`, `riskBudget`, `quoteQuality`, `dayTypeGateVerdict` appear from May 2026; `SNIPER` exit management appears 2026-04-06; mean tags per trade rises from 68 (March) to 100 (September). The ledger documents at least four distinct engine generations inside one "strategy version".

---

## 4. Candidate rules, evidence, counter-evidence, confidence

### R1 "George does the opposite of the crowd" (GeorgeFi's headline claim)
- **Hypothesis**: direction is chosen against a crowd-sentiment measure.
- **Observation**: `crowd_mood` is a deterministic RSI(1-min?) band — BEARISH when RSI ≤ 44.4, NEUTRAL 48.7–54.5, BULLISH ≥ 56.2 on 60/60 decision observations (D4). Direction equals `crowd_mood` in 13/20 decisions, is opposite in 2/20, and the rest have NEUTRAL crowd (`evidence/analysis_snapshots`). Trade records carry no crowd field at all; `discomfort_score` is 0 on every trade and equals confidence on live decisions.
- **Counter-evidence to the claim**: direction tags such as `STRUCT:BULLISH:CONFIRMS`, `WP:…:CONFIRMS`, `TREND:CHASING_CONTINUATION-10` show the engine rewards agreement with structure/weekly trend and penalises chasing; nothing in the ledger inverts a sentiment input.
- **Alternative explanation**: "inversion" is marketing framing for an ICT-style sweep/reclaim fade (buying after stops are taken the other way), which only *looks* contrarian.
- **Confidence**: High that the mechanism is not a literal sentiment inversion; the observed decisions mostly follow the RSI label.
- **To distinguish**: more D4 snapshots (collector running) to see whether direction ever flips against a strong crowd label; member-page observation of "discomfort scoring".

### R2 Scan cadence and timing
- **Observed**: index/ETF decisions regenerate together each minute; entry seconds are uniformly distributed (0–59) and entry minutes are not clustered on 5-minute boundaries (minute mod 5 counts 122/124/91/72/80) → the engine evaluates on a ~1-minute loop and fires immediately, not on 5-minute closes.
- **Confidence**: High (Calculated from 489 entry timestamps).

### R3 Level-sweep entry model (GeorgeFi says: sweep of PDH/PDL/PWH/PWL/ORH/ORL + reversal, priority setups)
- **Observed**: `ENTRY_MODEL:SWEEP+15` on 407/489, `SWEEP_ALIGNED:+25(<level>)` on 438/489, `MULTI_SWEEP:+n(kx:…)` on 379, `SWEEP_REVERSAL_DETECTED` 77, `TRIPLE_CONFIRM:SWEEP+DIRECTION+GEX` 83. `watchLevels.sweepsToday[]` carries `sweptAt` timestamps.
- **Calculated**: trades carrying `SWEEP_ALIGNED` averaged +5.9 % of premium vs −4.7 % without (n=438 vs 51, bootstrap p=0.006) — the only pre-registered claim that survived, but with a tiny "without" group concentrated in one era.
- **Counter-evidence**: random-time entry baseline (T4) shows the actual entries' MFE sits at the 50th percentile of random entries on the same contract and day → the timing does not capture more upside than chance.
- **Confidence**: High that sweeps are the dominant entry trigger; Low that it adds measurable edge.

### R4 Gates: chop day, lunch, PM dead zone, power hour (GeorgeFi says: time-of-day bonuses/penalties, chop detection)
- **Observed**: `SESSION_ADJ:+20` (260 trades) through `-30`; `LUNCH_BLOCK:12:00-1:15PM`, `PM_DEAD_ZONE:14:00-14:50(25% WR)`, `CHOP_DAY_BLOCK`, `EARLY_MARKET_GRACE:THRESHOLD_100`, `POWER_HOUR_PREFER_SPX`; 118/489 trades flagged `isChopDay` and still taken (via `CHOP_DAY_SWEEP_BYPASS` / `INST_BLOCK_OVERRIDE`).
- **Calculated**: entries 10:00–12:00 ET: n=249, WR 56.6 %, +$7,186; 09:30–10:00: n=39, WR 41 %, −$968; 15:00–16:00: n=37, WR 38 %, −$427; chop-day entries WR 55.9 % vs 50.4 % non-chop (no penalty visible in outcomes).
- **Counter-evidence**: `SESSION_ADJ:+20` trades did *not* outperform (+3.5 % vs +6.3 %, p=0.40).
- **Confidence**: High that the gates exist; Medium that the morning window is where the record was made; Low that the bonus points are calibrated.

### R5 GEX regime usage (GeorgeFi says: negative gamma = explosive, pin proximity penalty, GEX magnet lottos, accelerator flips)
- **Observed**: `gexProfile` per decision (totalGEX e.g. $8.45 B for ^SPX, gammaFlip 7808.9, maxGEXStrike 7800, pinRisk 95, acceleratorScore), tags `GEX:NEGATIVE_GAMMA+10(explosive)` (112), `GEX:PIN_PROXIMITY-15` (127), `VIX_GEX:*` (156), `SPX_GEX:GEX_MAGNET|ACCELERATOR_FLIP`, `GEX_BARRIER:7400($6.2B)_SIZE:70%`, exits `GEX EXIT: Accelerator reversed against BEARISH (was 0, now 43)` (23 trades, all winners, +17 % avg) and `GEX REGIME SHIFT: NEG→POS while losing` (11, all losers).
- **Calculated**: by `entryEnvironment.gexRegime` (May+ only): AT_PIN n=138 WR 58 % +$4,019; NEGATIVE_GAMMA n=47 WR 62 % +$868; POSITIVE_GAMMA n=86 WR 44 % −$2,629. `GEX:NEGATIVE_GAMMA+10` tag itself: no outcome difference (p=0.81). Note `gexRegimeAtEntry` is the literal string `NEUTRAL` on all 489 records (unpopulated legacy field).
- **Alternative explanation**: AT_PIN outperformance may reflect ^SPX concentration (145 trades, the most profitable ticker) rather than regime.
- **Confidence**: High that dealer-exposure estimates feed both entry scoring and an exit rule; Medium that regime labels correlate with outcomes; Unknown whether they are causal.

### R6 Flow / "sus strike" detection (GeorgeFi says: $500K+ in 60 s, sweep clusters, stealth accumulation over 15 min, counter-trend divergence)
- **Observed**: public tape kinds and MCP trigger names; ledger tags `SUS_FLOW_AGGRESSOR:93/66/202(bull=70,bear=89,face=0,flip=66)`, `INST:SURGE_PERSIST+10(EXTREME,DIR_ONLY)`, `INST_EVENT_DETECTED:MULTI_TICKER_CONFIRMATION` (180), `DELTA_FLOW:BEARISH:60:NEG_GAMMA`, `isSusStrikeAutoFire` (0 of 489 true), `isWhaleFollow` 2.
- **Calculated (T6, 6 sessions)**: `sus-strike` alerts' contracts: +60 min mean −0.9 %, median 0.0 %, 36 % positive (n=421); LONG-tagged +0.5 %, SHORT-tagged −2.2 %; STEALTH LIGHT median 0.0 % because many far-dated contracts barely trade. `momentum-ignition` contracts: +60 min −10.3 % (n=91), MFE median +14 % but MAE median −24 %. `relative-burst`: +60 min −10 %, to close −13 % (n=23). `block-sniper STRONG`: to close −10.5 % (n=17) with MFE median +67 % and MAE −48 % — large two-way moves, no net direction.
- **Interpretation**: consistent with GeorgeFi's own guide ("SURGE shows where size is, never which way"). As stand-alone directional signals these alerts have no positive expectancy in the observed week; the guide's instruction to use them for context only is supported.
- **Confidence**: Medium (one week of data).

### R7 Hold advisor / exit management (GeorgeFi says: T1 +25 % sell half, T2 +45 %, breakeven lock +6 %, VIX trails 8/11/14 %, hard kill, auto-close 15:58)
- **Observed exit reasons (D1)**: `STOP LOSS (-12%)` 25, `STOP LOSS (0%)` 12, `WIDENED STOP LOSS (-18/-22%)`, `STOP LOSS (-20/-25%)`, `HARD KILL (-25|-28% floor)` 16, `🎯 SNIPER: T1 PROFIT LOCK (+31…+60%)` 43, `🎯 SNIPER: EMERGENCY_STOP (-24…-50%)` 62, `🎯 SNIPER: TRAILING STOP (HWM +16%, trail at +8%)`, `TRAILING PROFIT (+8…+24% locked, exited at …)` 40, `ICT: Take profit at MAJOR liquidity pool` / `Market Structure Shift` / `Structure change (BOS) against position` 36+19, `GEX EXIT` 23, `GEX REGIME SHIFT … while losing` 11, `THETA BURN: 17min hold, LOSING` 9, `STALE TRAIL STOP`, `TREND VIOLATION`, `SHADOW STOP: Chart invalidated`, `FAST MOVE GUARD`, swing `PREMIUM STOP (-16…-27%)`, `SWING PROFIT_TARGET PARTIAL EXIT (25%)`, plus hand-written reasons (`Die TSLA DIE`, `Profit is Profit Mate`, `SHABBOTAGE`) → **some exits were manual** (Observed).
- **Calculated**: median scalp hold 5.5 min (p25 3.3, p75 9.9); stop-loss exits −13.7 % avg, sniper emergency −32 % avg, sniper T1 +40 % avg. 88 scalps reached +25 % HWM; 67 of those closed ≥ +15 %, only 5 closed negative (the trailing logic rarely gives back a +25 % gain). 161 scalps never exceeded +5 % HWM and averaged −15.3 %.
- **Published tiers vs record**: published T1 +25 % / T2 +45 % are not what the sniper exits show (T1 locks cluster +31…+60 %, emergency stops −30 %), and the published −32 % sweep stop corresponds to the `HARD KILL -28%`/`EMERGENCY -30%` family. The published 15:58 auto-close is consistent: only 2 scalps exited after 15:50.
- **Published limits vs record** (Calculated): 79 of 216 same-ticker re-entries happened < 30 min apart (41 within 5 min) despite the stated 30-min cooldown; up to 8 trades per ticker per day (stated max 5); 10 entries occurred after the day was already ≤ −$300 (stated daily stop); max 15 trades/day (stated ≤ 10). The published rules are at best the current-era rules.
- **Confidence**: High that the exit engine is the main driver of the recorded result (see §6 T3); Medium on the specific thresholds (they changed by era).

### R8 Contract selection
- **Observed**: `contract` strings with DTE label and strike; `quoteQuality` with `fillProfile` INDEX_CASH / SINGLE_NAME, `maxSpreadPct` 0.25/0.30, `maxAgeMs` 2000, `isExecutable`, `WEBSOCKET_QUOTE_TOO_OLD` (quotes older than 2 s were still used, flagged `stale:true`); `SELECTION_FAILED` contracts on live decisions.
- **Calculated**: ATM for indices, slightly ITM for ETFs (see §2.4); delta targets published by account size (0.20–0.70) could not be verified because `entryDelta` is 0 on every record.
- **Confidence**: High on moneyness pattern; Unknown on the delta rule.

### R9 Sizing
- **Observed**: `size` 1 on 71 %; up to 25 contracts on GEX lottos (`isGEXLotto` 10 trades, avg +91 % but 40 % WR); `riskBudget.stopLossPercent` 0.2, `maxLossPercent` ≈ 1.6 % of buying power; `WIN_AFTER_LOSS_REDUCTION:0.5x`; `CONFLUENCE_SIZE:1.20x/1.44x`.
- **Confidence**: High that sizing is rule-based and small; the published "institutional flips size up to 70 % of buying power" was not observed in Epoch 2.

### R10 Swings
- **Observed**: 38 swing-type trades, avg hold 1.1 days (published: up to 14), `SWING PREMIUM STOP (-16…-27%)`, `SWING PROFIT_TARGET PARTIAL EXIT (25%)` at +26…+29 %, `swingStopLabel`/`swingStopPrice` fields (underlying-level stops), 65.8 % WR, +$856 total. n is too small for inference.

---

## 5. Decision stability across refreshes (T7, preliminary)

Three snapshots (14:16, 14:47, 14:52 UTC) over 6 core tickers: `direction` changed on 4/37 ticker-pairs, `action` 19/37, `confidence` 20/37, `setupGrade` 18/37, `contract` 18/37, `gexRegime` 1/37, `crowd_mood` 0/37. Example: ^SPX went BEARISH/100/A/"BLOCKED: Chop Day" → BEARISH/61/B-/WATCHING → BEARISH/66/B/WATCHING within 36 minutes; QQQ flipped BULLISH→BEARISH. This matches GeorgeFi's own MCP description that the raw lane "churns by design" and that a separate committed read exists (not public). Confidence and grade are therefore **not stable state**; any consumer must timestamp them.

---

## 6. Validation results (Calculated; independent UW minute bars)

Full output: `evidence/analysis/validation_T1-T4.txt`, `validation_T5_gates.txt`, `validation_T6_tape.txt`. 486 of 489 trades had bars (3 contracts had no UW bar file).

**T1 Fill realism.** 58.6 % of recorded entry premiums lie inside the traded low–high of the entry minute (70.3 % for exits); median position inside the bar 0.50; 51 % of entries are below the bar's trade-weighted average. Reading: fills are at NBBO mid rather than at traded prices; 41 % of entries occurred in minutes where no trade printed at that price. Not systematically optimistic relative to trades, but not proven executable either.

**T2 Cost-adjusted replay** (481 trades with both bars, operator's own timestamps and sizes):

| Fill model | Total P&L | Win rate | Expectancy / trade | Profit factor |
|---|---|---|---|---|
| As recorded | +$3,506 | 52.0 % | +$7.3 (95 % CI −$12.9 … +$28.0) | 1.13 |
| Bar VWAP both sides | +$2,867 | 53.0 % | +$6.0 | 1.13 |
| Adverse (buy bar high, sell bar low) | −$27,233 | 34.3 % | −$56.6 | 0.32 |
| Adverse + spread (8 %/12 %) + fees | −$56,143 | 17.3 % | −$116.7 (CI −$139 … −$97) | 0.09 |

The recorded expectancy is not distinguishable from zero; with any realistic bid/ask cost the strategy loses. Monthly split: every month is negative under the cost model; June 2026 is negative even as recorded (−$3,497).

**T3 Exit alternatives** (443 same-day scalps, % of premium): recorded exits +4.5 % expectancy (PF 1.50); hold to 15:55 −15.8 %; ±25 % bracket +1.2 %; 30-min time stop −2.6 %; published tier ladder +2.2 % (WR 67.7 %, tiny wins). The operator's actual exits beat every mechanical rule → the record is produced by exit management (and possibly discretionary exits, see R7).

**T4 Entry information content**: median MFE +63.9 %, median MAE −81.8 % (0DTE contracts move violently both ways); 75 % of entries reached +25 % at some point, 87 % reached −25 %. Against a random-entry-time baseline on the same contract/day, actual entries' MFE percentile median = 50, mean = 51 → **no timing edge detectable**.

**T5 Gate validity**: 144 tag families tested; 30 clear BH q<0.10 but almost all are era markers (e.g. `GENOME`, `CONVICTION_AXES`, `IMB`, `DAY_TYPE_GATE` only exist from May; `VIX`, `VIX_GEX` only in high-VIX months), so they encode *when* a trade happened. Pre-registered claims: grade A+ vs A +5.0 pts (p=0.18); A vs A-/B+ −0.5 (p=0.93); `SESSION_ADJ:+20` −2.8 (p=0.40); chop-day −1.0 (p=0.74); `GEX:NEGATIVE_GAMMA` −0.8 (p=0.81); `SWEEP_ALIGNED` +10.6 (p=0.006); `TRIPLE_CONFIRM` +6.7 (p=0.08); confidence ≥85 vs <85 −2.9 (p=0.46). Out of sample (Jul–Oct) grade order inverts (A- best at +22 %, n=22). **Grades and confidence do not carry validated information.**

**T6 Public tape**: see R6. Aggregate: `loud=true` alerts' contracts −11.6 % at +60 min (n=80); every 0DTE alert contract to 15:55: mean +0.1 %, median −5.7 %, 35 % positive (n=296).

**Cross-check UW vs Massive bars**: for the 85 contracts fetched from both providers before the Massive rate limit stalled the cross-check, 28,674 overlapping minutes have a median absolute close difference of 0.0 % (p90 0.0 %) and a median volume ratio of 1.0, so the UW-based results above would not change on Massive data.

---

## 7. What is confirmed, calculated, inferred, unknown (summary)

- **Confirmed**: server-side 1-minute decision loop; ~100-tag additive ledger with caps/floors/gates; ICT level vocabulary; UW/Massive-style inputs; sus-strike/ignition/burst/hold-advisor subsystems; exit-reason families; RSI-band `crowd_mood`; published rule set differs from recorded behaviour on cooldown, daily stop, trades/day.
- **Calculated**: Epoch-2 record ≈ zero expectancy before costs, negative after; exits (not entries) explain the positive record; no entry-timing edge vs random; no OOS grade/confidence separation; tape alerts carry no stand-alone direction.
- **Inferred**: inversion is framing for sweep-reclaim fades; grade = banding of post-cap score with conflict-count adjustment; AT_PIN outperformance is ticker-confounded.
- **Unknown**: exact scoring constants and band edges; committed-read lane; member-cockpit inputs; detector thresholds for sus strikes; which exits were manual.
