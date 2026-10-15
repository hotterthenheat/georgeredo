# Compass full-history research — results (running document)

Every number below is produced by `engine/` from the protocol in `04_protocol.md`, recorded in `registry.jsonl`, and reproducible from the study script named in each section (`studies/sNN_*.py`) and the data manifests. Negative results are results. Nothing here is a recommendation until it passes the gates (`registry.jsonl` `GATE-v2`, protocol §10).

## S01 — the owner's baseline, Quick Scalps on index ETFs with same-day expirations (REJECTED)

**What was run.** The configuration exactly as specified (protocol §4; `config/compass_config.v0.baseline.json`): 1-minute RSI 14 crossing 55 (calls) / 45 (puts) with the close on the right side of EMA 9; 5-minute close beyond EMA 20 and the session VWAP; 15-minute EMA 20 vs EMA 50 alignment with price on the right side of EMA 20; relative volume ≥ 1.0 against the same minute of the prior 20 sessions; higher-high/higher-low (or lower-low/lower-high) structure on 5-minute pivots; entries 09:45 → 14:50; one open position per symbol. Contract: the same-day expiration, delta 0.30–0.60 from the mid-implied vol (nearest 0.45), spread < 12 % of mid, ask ≥ $0.05 (open interest and intraday volume filters not available in the 0DTE cache — applied from S03 on). Exits in priority: session cutoff 15:50, 5-minute close through the signal's swing level, 1-minute close through VWAP, −25 % premium stop, +25 % on half, +50 % on the rest, the next 15-minute EMA level, 60-minute hold. Fills: ask in, bid out, from the 1-minute NBBO; $0.70 per contract per side.

**Data.** SPY and QQQ 2022-11-11 → 2026-10-09 (980 sessions each), IWM 2024-04-19 → 2026-10-09 (621 sessions): the complete history of daily expirations on these ETFs, full-strike chains (`research/thetadata/dataset/MANIFEST_full_chains.md`), underlying minute bars from 2017 for warm-up. 6,882 signals; 2,886 filled trades on 614 trading days; 3,100 signals skipped while a position was open; 428 on sessions without chain data; 360 without a same-day expiration; 108 without an eligible contract.

**Result** (`results/v1/s01_quick_scalps_0dte_baseline/REPORT.md`, registry `S01`):

| | trades | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD | net |
|---|---|---|---|---|---|---|---|
| Strategy | 2,886 | **−4.19** | [−5.68, −2.81] | 34.3 % | 0.73 | −$12,320 | −$12,081 |
| Matched random entry (5 seeds, same days/direction/contract rule/exits) | 14,218 | −2.18 | [−3.23, −1.15] | 37.2 % | 0.84 | | |
| Strategy − baseline, paired | 2,885 | **−2.03** | [−3.18, −0.90] | | | | |

Negative in every year (2023 −4.87 [−6.88, −2.85]; 2024 −3.22 [−5.75, −0.76]; 2025 −4.39 [−7.25, −1.78]; 2026 −4.65 [−8.52, −1.06]), for every symbol (SPY −4.99, QQQ −3.80, IWM −3.46) and for both sides (calls −2.26 [−3.86, −0.65]; puts −5.89 [−8.23, −3.67]). The round-trip cost is $2.79 per contract and the gross mean is −$2.79: **the entries lose before costs.** Exit mix: the −25 % stop ends 52 % of trades (−$22 each), the +50 % target 26 % (+$39), the VWAP-loss rule 15 % (−$22), the 60-minute time exit 5 % (+$14), the swing-level invalidation 1 % (−$11). Worst in the top VIX tercile (−7.18 [−10.04, −4.42]) and in the 13:30–14:29 entry hour (−7.02); no event-day pattern (FOMC/CPI/NFP cells overlap zero with small n).

**Reading.** The owner's rule, on the liquid index ETFs where it is cheapest to trade, selects minutes that are worse than random by about $2 per contract after a 60-minute, stop-managed hold. The loss is not a cost artefact and not a single-year artefact. Under protocol §13 the next diagnostics are (a) whether the signal predicts the underlying at all and how much of the move it chases (S04, on 2017 → 2026 minute bars), (b) which components of the rule hurt or help (S02 single-factor grid, in progress), (c) whether longer expirations change the picture (S03, weekly expirations with OI/volume filters, 2017 → 2026). Until one of these produces a positive, out-of-sample, baseline-beating cell, Quick Scalps is **rejected** as a Compass signal family on index 0DTE products.

## Pending


## S04 — does the baseline signal predict the underlying at all? (NO)

`studies/s04_signal_underlying_validity.py`, SPY/QQQ/IWM 1-minute bars 2017-06-01 → 2026-10-09 (2,353 sessions; 5,000–5,400 baseline signals per symbol), no options. Signed return = direction × underlying return in basis points; random controls = minutes drawn uniformly in the entry window on the same symbol and date with the same direction (5 seeds); day-clustered 95 % CIs. Table: `results/v1/s04_signal_underlying_validity/table.csv`.

| | prior 30 min | next 5 min | next 15 min | next 30 min [95 % CI] | next 60 min | to close | 30-min hit rate |
|---|---|---|---|---|---|---|---|
| SPY baseline (n 5,375) | +9.6 | −0.5 | −0.8 | **−1.3 [−2.4, −0.2]** | −1.2 | +0.2 | 50 % |
| SPY random minutes, same days/direction | +5.3 … +6.0 | +0.8 … +1.1 | +2.5 … +2.8 | **+4.6 … +5.3** | +8.4 … +9.2 | +19 … +20 | 60–62 % |
| QQQ baseline (n 5,040) | +12.0 | −0.8 | −0.7 | **−0.7 [−1.9, +0.5]** | +0.2 | +1.7 | 51 % |
| QQQ random | +7.7 … +8.5 | +1.1 … +1.4 | +3.3 … +4.0 | **+6.1 … +7.7** | +11.8 … +12.5 | +26 … +28 | 60–63 % |
| IWM baseline (n 5,398) | +13.6 | −0.5 | −0.7 | **−1.6 [−3.0, −0.2]** | −2.9 | −4.7 | 51 % |
| IWM random | +7.2 … +8.6 | +0.9 … +1.5 | +2.4 … +3.8 | **+5.2 … +6.8** | +10.4 … +12.2 | +20 … +22 | 59–61 % |
| RSI cross alone, no filters (n ≈ 73,000 per symbol) | +6.5 … +9.5 | 0.0 | 0.0 | **−0.03 … −0.10 [−0.3, +0.2]** | ≈ 0 | +0.6 | 50 % |

Ablations (next 30 min, SPY / QQQ / IWM): no structure +0.06 / +0.13 / −0.49; no relative volume −0.37 / −0.15 / −0.78; no 15-minute alignment −0.67 / −0.43 / −1.43; no 5-minute confirmation −1.38 / −0.83 / −1.39; with the daily trend −1.19 / −0.17 / −1.82. None is positive with a positive lower bound.

**Reading.** The rule fires after the move: the prior 30 minutes carry +10 to +14 bp in the signal's direction, and what follows is flat to slightly negative. Random minutes on the same days and sides collect the day's drift (+5 to +8 bp over 30 minutes) that the signal's minutes miss; the signal is therefore about 6–8 bp *worse* than chance at 30 minutes, which is the −$2 per contract measured in S01 once an option, its spread and theta are attached. The RSI-cross trigger itself carries zero information at every horizon; the filters only shrink the sample. This closes the question for the baseline as specified: **no exit rule, delta band, spread filter or expiration can make a long option profitable on an entry whose underlying expectation is negative.** The cost hurdle in underlying terms is about 2–3 bp per round trip on SPY (a $2.80 round trip on a ~$1, 0.45-delta contract) plus theta over the hold, so a Compass entry trigger must show a day-clustered lower bound of at least +3 bp over 30–60 minutes against the matched random control before any option test is worth running. That screen (S06) is the next step, run across the liquid universe on 2017 → 2026 minute bars.

## S06 — do any entry triggers predict the underlying on the index ETFs? (NO)

`studies/s06_signal_screen.py` → `results/v1/s06_signal_screen_index/REPORT.md` (84 rows), registry `S06`. SPY/QQQ/IWM 1-minute bars 2017-06-01 → 2026-10-09, decisions at the close of the 1-minute bar in the 09:45–14:50 window, seven triggers in both directions, each raw and under the baseline's filter stack (and the 5-minute confirmation and 15-minute alignment alone): the owner's RSI lead; a 1-minute VWAP reclaim; a 5-minute EMA 9/20 cross; a 5-minute close through the prior day's high/low or the 20-bar range (Breakouts); the retest of that level within 12 bars (Breakouts, retest variant); a 15-minute EMA 20 > 50 > 200 stack with a pullback to the EMA 9/20 band and a 5-minute close back through EMA 20 (Trend Plays); and a displacement of ≥ 2σ over 60 bars into a support/resistance level (prior-day extreme, 20-day extreme or VWAP ± 2σ) with a reversal bar (Bounces). Signed return = direction × underlying return in basis points; matched random = minutes drawn uniformly in the entry window on the same symbol, date and direction (5 seeds); day-clustered 95 % CIs.

| trigger (raw, no filters) | n per symbol | prior 30 min | +30 min absolute (SPY / QQQ / IWM) | +60 min absolute | vs matched random, 60 min |
|---|---|---|---|---|---|
| rsi_cross (owner's lead) | 72–73k | +6.5 … +9.5 | −0.0 / −0.1 / −0.0 | +0.1 / +0.1 / −0.1 | −1.2 / −1.5 / −1.6 |
| vwap_reclaim | 27–29k | +3.1 … +4.7 | +0.0 / +0.2 / +0.1 | +0.1 / +0.3 / +0.1 | −0.2 / −0.0 / −0.2 |
| ema_cross_5m | 5.4–5.6k | +18 … +27 | +0.1 / +0.1 / −0.0 | +0.4 / +0.0 / +0.3 | −1.1 / −2.0 / −1.4 |
| breakout_5m | 5.3–5.6k | +25 … +38 | −0.1 / +0.1 / −0.6 | −0.4 / +0.3 / −2.0 | −8.7 / −10.8 / −12.5 |
| retest_5m | 4.4–4.8k | +21 … +30 | −0.4 / −0.5 / −0.2 | −0.7 / −0.0 / −1.3 | −8.6 / −10.6 / −12.4 |
| trend_pullback | 5.6–5.7k | +5 … +7 | +0.1 / +0.7 / −0.2 | +0.6 / +1.1 / −0.4 | −0.5 / +0.0 / −1.0 |
| bounce | 8.8–11k | **−28 … −44** | −0.3 / −0.5 / +0.6 | −0.7 / −0.9 / +0.2 | **+7.1 / +9.6 / +10.7** |
| any trigger + the baseline filter stack | 0–5.4k | | −0.8 … −3.3 (every cell ≤ 0 except n ≤ 112) | −0.3 … −6.5 | −2.7 … −21.0 |

Every absolute 30- and 60-minute CI for a raw trigger includes zero and none has a lower bound above +0.1 bp (the only positive lower bounds are QQQ VWAP reclaim +0.1 and QQQ trend pullback +0.0, both economically nil). The widest effects in the table are the *pre-signal* columns: breakouts and retests fire after +25 to +38 bp of movement, EMA crosses after +18 to +27 bp, bounces after −28 to −44 bp. What follows is flat. Year-by-year (REPORT.md, second table) shows the same picture in each of the ten years: no trigger has a run of positive years.

**Why the bounce is not promoted.** Against the matched random control the bounce is the only trigger with a strongly positive difference (+6 to +11 bp at 60 min, lower bound ≥ +5 bp, positive in all ten years for the raw form). But its absolute forward return is zero. The difference comes from the control: random minutes on the same day *in the same direction* as a counter-trend signal collect the day's drift against that direction (the control's 30-minute return is −4 to −6 bp), so the comparison rewards the bounce for having picked the days on which the drift was adverse. A long option pays its spread and theta on the absolute move, not on the move relative to a control; a trigger whose absolute expectation is zero loses the full cost. The promotion rule is therefore stated with two parts — an absolute day-clustered lower bound ≥ +3 bp at 30 or 60 minutes **and** a positive paired lower bound against the matched random control — and `s06_report.py` applies both. The second part alone was the hurdle stated in the S04 reading; the first part was added after this screen exposed the control artefact. This tightening cannot manufacture a positive: it only removes a false one.

**Reading.** On the three index ETFs, over nine years and about 450,000 trigger events, none of the Compass setup-family triggers — the owner's RSI lead, VWAP reclaims, EMA crosses, breakouts, retests, trend pullbacks or bounces — carries a forward move after its decision bar. Every one fires after the move it is designed to catch. The baseline filter stack (5-minute confirmation, 15-minute alignment, relative volume, structure) makes each trigger *later*, not better: it lowers every row against random. This is consistent with S01 and S04 and with the well-documented absence of short-horizon intraday momentum in liquid index products. The screen now moves to the Tier A single-name universe (S05 bars), where cross-sectional dispersion and event-driven moves give an intraday trigger a chance that index ETFs do not; S03 (weekly expirations) still runs because its purpose — whether a longer-dated contract changes the *cost* side — is independent of this finding, but with the entries measured here its expectation is already known to be non-positive.

## S07 — daily triggers across the optionable universe, 2024 → 2026 (NOTHING PROMOTED; breakouts and pullbacks are followed by *under*performance)

`studies/s07_daily_screen.py` → `results/v1/s07_daily_screen/REPORT.md`, registry `S07`, pre-registered as protocol amendment A2. Universe per calendar year = every optionable root whose prior-calendar-year median daily dollar volume was ≥ $50 M with ≥ 200 bars and a median price ≥ $5 (1,119 symbols in 2024, 1,210 in 2025, 1,510 in 2026; 10.5 M daily rows read from the stock EOD lake, 2023 used only for the universe and warm-up). Triggers at the daily close in both directions; entry at the next session's open; signed return to the close 1, 5, 10 and 21 sessions later, absolute and adjusted for the same-date mean of the eligible universe in the trigger's direction; CIs clustered by event date.

| trigger | n | signal-day move | +5 sessions abs [CI] | +10 abs | +21 abs [CI] | +21 adjusted [CI] | adjusted 10-session by year 2024 / 2025 / 2026 |
|---|---|---|---|---|---|---|---|
| gap continuation (gap ≥ 2 ATR, close beyond the open) | 2,588 | +2,000 bp | +10 [−33, +60] | −29 | −35 [−120, +51] | +8 [−50, +69] | +75 / −76 / −38 |
| 20-day breakout (close through the prior 20-day high/low) | 112,938 | +328 | **−31 [−54, −9]** | **−40 [−73, −10]** | **−81 [−133, −33]** | **−47 [−81, −14]** | −19 / −18 / −21 |
| 5-day reversal (5-day return ≤ −2σ√5, up close) | 7,823 | +148 | +14 [−35, +58] | +10 | +53 [−16, +121] | +33 [−16, +80] | +1 / +46 / −69 |
| trend pullback (close > EMA 50 > EMA 200, EMA 20 touch, cross back) | 45,185 | +270 | **−22 [−42, −3]** | **−33 [−67, −3]** | **−69 [−113, −24]** | **−97 [−141, −55]** | −55 / −26 / −53 |
| event shock (relative volume ≥ 3, |return| ≥ 2σ; earnings proxy) | 5,024 | +1,257 | −27 [−77, +20] | −12 | −16 [−142, +107] | +37 [−50, +138] | +63 / −60 / +58 |

The relative-volume ≥ 1.5 variants (REPORT.md) change nothing in sign and widen the intervals.

**Reading.** Across about 1,100–1,500 liquid single names per year, the two continuation setups of the Compass catalogue that fire most often — Breakouts and Trend Plays at daily resolution — are followed by *underperformance* over the next one to four weeks, with intervals that exclude zero and the same sign in each of the three years. Gap continuation, 5-day reversal and the volume/return-shock proxy for earnings days carry nothing that survives clustering by date (their year-by-year signs flip). No trigger reaches the pre-registered hurdle; nothing earns an option test with chains.

*Exploratory, not pre-registered.* The inverse of the breakout trigger — fading a 20-day breakout — would clear the absolute part of the hurdle only at 21 sessions (+81 bp [+33, +133]) and the adjusted part at 5 and 21. In option terms that does not help a long option: a 0.5-delta position captures roughly 40 bp of spot from that move, against roughly 110 bp of theta over 21 sessions on a 60-DTE single-name contract (premium ≈ 5–6 % of spot at 35 % IV) and about 40 bp of spread (measured C1 half-spreads of 3.5–4.1 % of premium). The effect is of the size that only a short-premium or spread structure could carry, and it is one exploratory cell out of sixty (ten rows × three horizons × two signs), so it is recorded here as a lead for a decision on scope, not as a result.

**Where this leaves the catalogue.** Intraday (S04, S06) and daily (S07) triggers in the Compass setup families carry no forward move in their own direction on index ETFs or on the liquid single-name universe over the histories available (2017 → 2026 intraday; 2024 → 2026 daily), and the two most frequent continuation triggers predict the opposite sign at daily resolution. The remaining in-scope tests are the ones that measure the *cost* side rather than the entry (S02 exits/contract grid, S03 weekly expirations) and the intraday screen on the single-name universe (S06 on Tier A bars, pending the pull). Unless one of those produces a positive out-of-sample cell, the honest deliverable is that no long-option configuration in the Compass catalogue meets the gates.

## S08 — the Earnings/Events family at daily resolution, 2024 → 2026 (NOTHING PROMOTED; beats are sold after the gap)

`studies/s08_earnings_daily.py` → `results/v1/s08_earnings_daily/REPORT.md`, registry `S08`, pre-registered as amendment A3. The Unusual Whales earnings calendar (`data_lake/unusualwhales/earnings.parquet`: report dates 1996 → 2026 with reported and estimated EPS, surprise and pre/post-market time — the coverage matrix's "~1 year" was the pull window, now corrected) joined to the S07 universe: 10,439 quarterly reports on 1,186 symbols over 594 event dates (5,745 pre-market). Event session = the report date for pre-market reports, the next session for post-market ones. Two entries: at the event session's open ("gap", what a scanner can take once the report is out) and at the following open ("drift", after the event-day move is known). Direction = the sign of the EPS surprise; also direction = the sign of the event-day move. Same adjustments and CIs as S07.

| cell | n | calls | event-day move | +10 sessions absolute [CI] | +21 absolute | +10 adjusted [CI] | +21 adjusted [CI] |
|---|---|---|---|---|---|---|---|
| surprise sign, gap entry, all | 9,957 | 77 % | +131 bp | +30 [+8, +54] | +68 [+35, +99] | **−17 [−35, +3]** | **−31 [−59, −2]** |
| … top-tercile beats | 3,482 | 100 % | +209 | +79 [+26, +131] | +132 [+66, +196] | −12 [−51, +29] | −49 [−103, +1] |
| … bottom-tercile misses (puts) | 2,996 | 23 % | +180 | −26 [−73, +18] | −39 [−97, +21] | +20 [−22, +59] | +56 [+3, +108] |
| … pre-market reports | 5,491 | 78 % | +142 | +47 [+19, +73] | +78 [+42, +116] | −2 [−24, +22] | −27 [−57, +3] |
| … post-market reports | 4,466 | 76 % | +118 | +10 [−24, +43] | +57 [+10, +104] | **−36 [−64, −9]** | −36 [−79, +7] |
| surprise sign, drift entry (next open), all | 9,957 | 77 % | +131 | +23 [+1, +44] | +55 [+23, +85] | **−25 [−39, −9]** | **−44 [−70, −17]** |
| … top-tercile beats | 3,482 | 100 % | +209 | +63 [+6, +115] | +96 [+26, +156] | −28 [−60, +3] | **−86 [−136, −39]** |
| event-day move sign, drift entry, all | 10,426 | 50 % | +583 | −8 [−29, +11] | −10 [−33, +12] | −5 [−23, +13] | −12 [−35, +8] |
| … move ≥ 2σ | 5,150 | 51 % | +950 | −14 [−37, +8] | −12 [−44, +19] | −8 [−28, +12] | −14 [−46, +16] |
| … move against the surprise | 4,318 | 19 % | +524 | −36 [−71, +1] | −72 [−115, −32] | +21 [−6, +49] | +39 [−1, +73] |

**Reading.** Three of four reports beat the estimate, so "direction = surprise sign" is mostly long, and its positive absolute returns are the 2024–2026 market drift: against the same-date universe the surprise direction *underperforms*, at both entries, in each year (adjusted 10-session: −29 / −16 / −7 bp for the gap entry; −11 / −27 / −35 for the drift entry), and worst for the strongest beats held three weeks (−86 bp [−136, −39]). Post-market reports are worse than pre-market. The event-day move itself predicts nothing at 1–21 sessions (−5 bp adjusted at 10, CI straddling zero), and a move that disagrees with the surprise reverses only weakly (+19 [+2, +36] at 5 sessions adjusted, absolute negative). There is no post-earnings drift to buy in this universe and window; what there is runs the other way ("sell the beat"), is small, and sits with the S07 breakout fade in the short-premium/spread scope the owner has not opened. Nothing earns an option test.

## S09 — the owner's baseline on SPXW same-day expirations, 2022-05-13 → 2026-10-09 (REJECTED)

`studies/s09_spxw_0dte_baseline.py` → `results/v1/s09_spxw_0dte_baseline/REPORT.md`, registry `S09`. The same rule as S01 on the index product with the lowest relative cost (SPXW half-spread 0.9 % of mid, C1; a 0.45-delta same-day contract is ≈ $10–30, so the $1.40 of fees is ≈ 0.1 % of premium). The signal is computed on the SPX index value per minute (open and close; an index series has no intrabar range, so high/low = max/min of the two) with SPY's minute volume as the relative-volume and VWAP weight proxy (`engine.store.IndexProxyStore`, tested); spot, strikes and deltas are the index's own; fills at the SPXW 1-minute NBBO (1,106 sessions, full strikes, every session covered).

| | trades | days | mean $/contract | 95 % CI | win | PF | max DD | by year (mean) |
|---|---|---|---|---|---|---|---|---|
| Strategy | 1,229 | 481 | **−46.18** | [−63.19, −30.02] | 33.8 % | 0.70 | −$57,412 | 2022 −91.6; 2023 −29.2; 2024 −15.8 [−42.5, +10.0]; 2025 −58.9; 2026 −59.3 |
| Matched random (5 seeds) | 6,139 | | −22.15 | [−32.52, −11.03] | 37.6 % | 0.83 | | |
| Strategy − random, paired | 1,229 | | **−24.09** | [−39.45, −9.28] | | | | round-trip cost $18.79 |

Puts −68.28 [−94.68, −42.13], calls −20.89 [−40.39, −1.64]. Exits: the −25 % stop ends 648 trades (−$222 each), the +50 % target 322 (+$386), the VWAP-loss rule 188, the 60-minute time exit 41 (+$108), the swing-level invalidation 30 (−$81).

**Reading.** Per contract the numbers are about ten times SPY's (SPX notional), and as a fraction of premium they are the same: the rule loses roughly the same share on SPXW as on SPY, QQQ and IWM, and it loses it *relative to random entries on the same days* by a margin larger than the whole round-trip cost. Moving the owner's 0DTE scalps to the cheapest index product does not change the sign, because the entry has no directional information (S04, S06). Quick Scalps is rejected on SPXW as on the ETFs.

## S13 / S14 — pre-earnings run-up (PROMOTED AT THE UNDERLYING LEVEL); cross-sectional momentum and reversal (nothing promoted)

`studies/s13_s14_daily_batch.py` → `results/v1/s13_s14_daily_batch/REPORT.md`, registry `S13`, `S14`, amendment A5. S07 universe, 2024 → 2026.

**S13.** Long the stock from the close N sessions before a quarterly report, out at the close of the session before the event session (the report is never held through):

| N sessions before | n | abs (bp) [CI] | universe-adjusted [CI] | adjusted by year 2024 / 2025 / 2026 | A2 hurdle |
|---|---|---|---|---|---|
| 3 | 10,471 | +33 [+9, +53] | +15 [+7, +25] | +35 / +1 / +13 | adjusted only |
| 5 | 10,465 | +53 [+22, +82] | +23 [+10, +35] | +36 / +5 / +30 | adjusted only |
| **10** | 10,445 | **+97 [+62, +133]** | **+20 [+4, +36]** | +23 / +10 / +28 | **both parts** |

This is the documented earnings-announcement premium. It is the first cell in this research to clear the underlying hurdle, and it should be read exactly: three-quarters of the absolute 10-session return is the 2024–2026 market drift (an unconditional long over the same dates earned ≈ +77 bp); the part specific to the pre-earnings window is +20 bp [+4, +36], consistent in sign across the three years. For a long option a 10-session hold costs theta that a 97-bp move alone does not cover (port spec §5 arithmetic); what makes the window different from any other 10 sessions is the rise in implied volatility into the report, which a long call or straddle sold at the pre-event close collects. That is the pre-registered option test (A5.2), run on per-event chains with S11.

**S14.** Month-end deciles held 21 sessions have only 20–34 rebalance dates in the window; every interval is hundreds of bp wide. The 1-month reversal long leg is +398 bp absolute [+59, +737] but +247 [−38, +598] against the universe with year signs that flip; 12-1 momentum is indistinguishable from the universe; shorting the 12-1 bottom decile would have lost −576 bp [−1,120, −140] (small caps rallied). Nothing promoted; revisit when the 2012–2022 daily years land.

## S15 — 0DTE short ATM straddle at 10:00, conditioned on the volatility risk premium (NOTHING PROMOTED; the condition has the wrong sign)

`studies/s15_vrp_short_straddle.py` → `results/v1/s15_vrp_short_straddle/`, registry `S15`, amendment A5. SPY and QQQ, every session 2022-11-11 → 2026-10-09 (1,941 straddles): sell the at-the-money call and put at 10:00 at the bid, buy both back at 15:50 at the ask, $0.70 per contract per side per leg. Condition = the straddle's implied move (credit ÷ spot) relative to the trailing 20-session realized 10:00 → 15:50 move.

| cell (SPY + QQQ) | n | mean $/straddle [95 % CI] | win | PF | max DD | by year |
|---|---|---|---|---|---|---|
| unconditional, all days | 1,941 | **−15.46 [−32.68, +0.29]** | 58 % | 0.83 | −$35,674 | −28 / −17 / +1 / −33 / −10 |
| … one adverse tick per leg | 1,941 | −19.46 [−36.68, −3.71] | 57 % | 0.79 | −$42,830 | |
| … skip FOMC / CPI / NFP / month-end | 1,619 | −11.78 [−29.64, +4.68] | 58 % | 0.86 | −$23,805 | 0 / −18 / +3 / −26 / −7 |
| implied ≥ 1.25 × trailing realized ("rich") | 586 | **−41.10 [−86.33, −2.39]** | 55 % | 0.69 | −$25,789 | −66 / −20 / −31 / −107 / +2 |
| implied ≤ 0.8 × trailing realized ("cheap") | 304 | −11.83 [−43.11, +17.35] | 60 % | 0.85 | −$5,630 | −142 / −10 / +5 / +10 / −50 |
| middle | 1,011 | −1.60 [−19.69, +15.23] | 60 % | 0.98 | −$7,940 | −19 / −18 / +29 / −8 / −1 |

Rich minus cheap: −$29 [−69, +9]. **Reading.** A 58 % win rate and a losing expectancy, as H16 said it would be. The conditioning hypothesis — sell when implied is rich relative to recent realized — is wrong in sign: a rich implied move is the market correctly anticipating a large realized move (event days, vol clustering), and those are the days the straddle loses most. The nearest-to-flat cell (middle, −$1.60 ± 18) is not a lane. Together with H9/H11/H13 this closes unconditional and VRP-timed short ATM 0DTE straddles on these products at the measured round trip.

## S10 — short premium on index 0DTE, fading the owner's signal (NOTHING PROMOTED; breakeven at best)

`studies/s10_short_premium_0dte.py` → `results/v1/s10_short_premium_0dte/`, registry `S10`, amendment A4. At each of the 2,886 S01 signal minutes, sell the contract the rule would have bought (single) or sell it against the nearest-0.20-delta contract further out (vertical); legs at the NBBO, $0.70 per contract per side per leg; controls = the same structures at the 14,218 matched random minutes.

| structure | exit | n | mean $/contract [95 % CI] | win | PF | max DD | random-minute shorts | strategy − random [CI] | by year 2022 … 2026 |
|---|---|---|---|---|---|---|---|---|---|
| single | 15:50 cutoff, stop 2 × credit | 2,886 | **+0.52 [−6.11, +7.47]** | 55 % | 1.01 | −$9,276 | −5.71 | +6.44 [+4.36, +8.51] | +3.0 / +2.4 / +1.5 / +2.7 / **−5.0** |
| single | same, one adverse tick | 2,886 | −1.34 [−7.83, +5.48] | 54 % | 0.97 | −$9,791 | −7.47 | +6.35 [+4.27, +8.46] | |
| single | 60-min hold, stop 2 × | 2,886 | −2.59 [−6.06, +1.11] | 55 % | 0.90 | −$9,518 | −8.84 | +6.33 [+4.73, +7.93] | all negative |
| single | cutoff, no stop | 2,886 | −2.80 [−16.40, +9.78] | 65 % | 0.94 | −$18,468 | −9.42 | +6.78 [+5.20, +8.33] | +19 / −1 / −1 / −1 / −11 |
| vertical | cutoff, stop 2 × | 1,530 | −2.92 [−10.00, +4.60] | 53 % | 0.91 | −$8,143 | −8.05 | +5.17 [+3.08, +7.25] | −2 / −0 / +1 / −3 / −9 |
| vertical | 60-min hold | 1,530 | −5.17 [−8.97, −1.29] | 50 % | 0.74 | −$7,992 | −10.72 | +5.58 [+3.99, +7.27] | all negative |

**Reading.** The mirror of S01 holds exactly as the arithmetic predicts: the owner's signal marks a minute at which selling the option is about $6 better than selling at a random minute — and selling at a random minute loses $6–9 after the round trip, so the fade is breakeven (+$0.52 ± 7) and goes negative with one adverse tick. Defined-risk verticals pay two spreads and are worse; holding without a stop adds a −$18,000 drawdown for no mean. There is no sellable premium at these minutes either; the signal's information is real but smaller than the cost of trading it in either direction. 2026 is negative in every cell.

## S12 — intraday momentum (NOTHING PROMOTED; a QQQ-only rest-of-day effect that does not survive the batch adjustment)

`studies/s12_intraday_momentum.py` → `results/v1/s12_intraday_momentum/`, registry `S12`, amendment A5. Direction = the sign of the 09:30 → 10:00 return; signed returns in bp, CIs clustered by date, 2017-06 → 2026-10.

| cell | SPY all days | QQQ all days | IWM all days | SPY ≥ 0.3 % | QQQ ≥ 0.3 % | IWM ≥ 0.3 % |
|---|---|---|---|---|---|---|
| 10:00 → 15:00 | +2.2 [−0.6, +4.8] | **+4.3 [+0.8, +7.8]** | +2.6 [−1.2, +6.4] | +1.8 [−6.3, +10.2] | **+9.0 [+2.8, +15.3]** (hit 56 %) | +1.3 [−4.6, +7.2] |
| 15:00 → 15:50 | −0.2 [−1.4, +1.1] | +0.9 [−0.5, +2.3] | +1.5 [+0.0, +2.9] | +0.1 [−3.3, +3.4] | +0.7 [−1.7, +3.0] | +2.0 [−0.2, +4.3] |
| 15:30 → 16:00 | −0.8 [−2.2, +0.5] | −0.5 [−2.0, +1.0] | +0.1 [−1.3, +1.4] | −1.8 [−6.0, +2.4] | −1.2 [−4.0, +1.7] | +0.0 [−2.2, +2.2] |

The last-half-hour momentum of the literature (first half hour → last half hour) is absent on all three ETFs over nine years. The first half hour does predict the rest of the day on QQQ — by year {'2017': 10.8, '2018': 15.0, '2019': 10.4, '2020': 4.1, '2021': 10.9, '2022': 13.8, '2023': 7.6, '2024': 3.0, '2025': 10.6, '2026': 3.0} on the large-move days — but not on SPY or IWM, and the QQQ cell's Bonferroni-adjusted lower bound across the 163 primary cells of the A5 batch is -2.5 bp. The 15:00 option expression (long the baseline-rule 0DTE contract in the first-half-hour direction, exit 15:50, all three ETFs): −$4.36 per contract [−8.48, +0.21] all days, +$0.79 [−7.41, +10.40] on large-move days; against the same contract in a random direction +$1.11 [−2.51, +4.92] and +$3.90 [−2.78, +11.17]. The 10:00 expressions (long to 15:00; short opposite-side vertical to 15:50) are S12b.

## S16a — overnight gaps and the prior day's move as open-time signals (NOTHING PROMOTED)

`studies/s16a_overnight_gaps_underlying.py` → `results/v1/s16a_overnight_gaps_underlying/rows.json`, registry `S16a`. 108 cells (3 ETFs × 2 signals × 3 filters × continuation/fade × 3 horizons), 2017-06 → 2026-10. Gap continuation and gap fade are indistinguishable from zero everywhere. Fading the prior session's close-to-close move has 6 cells with a positive 95 % lower bound against 2.7 expected by chance; the largest, QQQ on |gap| ≥ 0.5 % days held to the next close, is +17.8 bp [+4.7, +30.2] (hit 52 %, negative only in 2017); the rest are +5 to +12 bp with one to five negative years. A one-day reversal of that size is below a weekly option's round trip (≈ 25–40 bp of spot for a 0.45-delta 1–7 DTE contract once the C1 half-spread and a day of theta are paid) and does not survive the batch adjustment. The weekly-option expression (S16b) runs on the S03 chains for the record.

### S13 robustness (registry `S13-R`): the run-up is a tail, Q2-concentrated mean

Cuts of the 10-session cell (adjusted bp): liquidity $50–200 M +19 [−0, +39], $200 M–1 B +18 [−10, +46], ≥ $1 B (the names with tradeable chains, n 459) +45 [−29, +117]; pre-market +13 [−6, +31], post-market +29 [−1, +57]; calendar Q1 +26 [−4, +54], **Q2 +64 [+30, +100]**, Q3 −14 [−45, +15], Q4 −7 [−43, +32]; 2024 +23 [−6, +50], 2025 +10 [−13, +30], 2026 +28 [−12, +60]. Concentration: without the top 1 % of events the adjusted mean is **−7 bp**; the median event is +8 bp; 50.8 % of events and 55.8 % of symbols are positive. The pre-registered cell stands as a candidate at the underlying level, but what it describes is a small number of large pre-earnings run-ups in April–June reports, not a broad drift — the option expression (S11, A5.2) is run as pre-registered, with the implied-volatility change recorded so that a result can be attributed.

## S03 — the owner's rule on weekly expirations, SPY/QQQ/IWM 2017 → 2026 (NOTHING PROMOTED; zero, not negative)

`studies/s03_weekly_index_etfs.py` → `results/v1/s03_weekly_index_etfs_baseline/REPORT.md`, registry `S03`. Same signal as S01; contract = the nearest-Friday weekly expiration (1–7 days), delta 0.30–0.60 nearest 0.45, spread < 12 %, open interest > 250 where cached (SPY 2017-06 → ≈ 2023-05), intraday volume > 100 from the option OHLC; holds up to three sessions with a 30 % stop. Chains were pulled for a year-stratified sample of sessions (SPY 468, QQQ 294, IWM 294) because the vendor throttled the pull; signals on the other sessions are excluded, not counted.

| | trades | days | mean $/contract [CI] | win | PF | max DD | by symbol | by direction |
|---|---|---|---|---|---|---|---|---|
| Strategy | 818 | 376 | **+1.27 [−3.69, +6.25]** | 38 % | 1.06 | −$1,214 | SPY +2.8, QQQ −2.1, IWM +2.1 | puts +3.1, calls −0.9 |
| Matched random | 4,089 | | +1.25 [−3.05, +5.71] | | | | | |
| Strategy − random | 818 | | **+0.02 [−2.11, +2.15]** | | | | | |

By year: −3.3 / +2.3 / −7.0 / +2.3 / −4.6 / −2.8 / +1.8 / +7.9 / +26.1 [−4.2, +57.6] / −6.7 (2017 → 2026). **Reading.** With a weekly contract the owner's rule is not negative, it is nothing: the same as random entries to the cent, with a sign that flips year to year. The 0DTE loss in S01/S09 was the same-day contract's theta and spread on an entry with no information; a longer contract removes the theta and leaves the nothing. 144 of the 818 trades closed at the last cached quote because the following session's chain was outside the sample (`data_end`), which truncates holds and slightly understates the costs of the full rule.

## S16b — fading the prior day's move with a weekly contract (NOTHING PROMOTED)

`studies/s16b_prior_day_fade_weekly.py` → `results/v1/s16b_prior_day_fade_weekly/summary.json`, registry `S16b`. The option expression of the S16a effect: at the 09:31 close buy the baseline-rule weekly contract against the prior session's close-to-close direction, exit at the next session's 15:50 or at −50 %. All days: −$9.91 per contract [−19.31, −0.26] (time exit), −$7.50 [−16.57, +1.67] with the stop — the same as a random direction (−$9.80). On |gap| ≥ 0.5 % days: +$1.83 [−16.40, +21.02] and +$2.73 [−14.80, +21.19], about +$12 [−7, +31] better than random: the +18 bp underlying reversal buys back the option's round trip and nothing more; year signs alternate (2022 +31, 2023 −4, 2024 −10, 2025 +1).

## S10 re-run — verticals with both sides filled (NOTHING PROMOTED)

After the protective-leg fix (`06_implementation_record.md`, 18:40) the vertical cells of S10 are re-measured on 2,857 fills: −$5.65 per contract [−10.09, −1.10] at the 15:50 cutoff with a 2 × credit stop, −$6.01 [−8.32, −3.66] at 60 minutes, −$11.49 [−19.69, −3.88] with no stop; +$4.0 to +$4.9 better than random-minute verticals, which lose −$10 to −$16. Negative in every year and exit set. The single-contract rows of S10 are unchanged (+$0.52 [−6.11, +7.47], breakeven).

## S02 — the single-factor grid around the baseline, 41 variants, with walk-forward selection (NOTHING PROMOTED)

`studies/s02_quick_scalps_grid.py` + `studies/s02_walkforward.py` → `results/v1/s02_walkforward/REPORT.md` (full table), registry `S02`. Every variant of protocol §8 — RSI 7/9/21, lead EMA 3/5/8/13, mid EMA 21/34, slow EMA 100/200, relative volume off/1.25/1.5/2.0, no 15-minute alignment, daily trend on, no structure, no 5-minute confirmation, RSI 60/40 and 50/50; delta bands 0.20–0.40 / 0.30–0.50 / 0.40–0.60, spread 5/8/10/15 %, tightest-spread pick; stops 20/30/40 %, no VWAP loss, no invalidation, no EMA target, no partial, +100 % target, +50/+100, holds 30/120 min, invalidation-only — on SPY/QQQ/IWM same-day expirations 2022-11 → 2026-10, each with its own matched random control.

**No variant has a positive full-sample lower bound, and none beats its matched random control.** The best lower bound is `delta20_40` at -3.76 per contract [-4.60, -2.94], -1.18 against random; the range across the grid is about −$2.7 to −$4.6 per contract, every cell negative in 2023, 2024, 2025 and 2026.

Walk-forward (train on all prior years with a 5-session embargo and ≥ 150 training trades, select the best variant, test on the next year):

| objective | 2024 (selected → OOS) | 2025 | 2026 | pooled OOS n | pooled OOS mean [CI] | win | PF |
|---|---|---|---|---|---|---|---|
| lower bound | delta20_40 → -2.97 | no_15m → -3.21 | no_15m → -5.19 | 3200 | **-3.81 [-5.23, -2.35]** | 34.8 % | 0.74 |
| mean | invalidation_only → -4.58 | no_15m → -3.21 | daily_trend → -6.07 | 2206 | **-3.94 [-6.11, -1.80]** | 37.3 % | 0.77 |
| expected profit ÷ expected worst drawdown (the brief's ranking) | invalidation_only → -4.58 | invalidation_only → -6.32 | invalidation_only → +4.94 | 1499 | **-2.49 [-7.32, +2.46]** | 39.8 % | 0.91 |

**Reading.** The grid is the answer to "can any parameter fix it": no. The ranking objective of the brief (expected profit ÷ expected worst drawdown) selects the invalidation-only exit set every year and produces the least-bad out-of-sample record, −$2.49 [−7.32, +2.46], with one positive fold (2026, +$4.94 [−6.11, +16.27] on 432 trades) whose interval includes zero. The sign is set by the entry (S04, S06); exits and contract rules move the mean by a dollar or two and the drawdown by thousands, never the sign.

## S12b — 10:00 option expressions of the first-half-hour direction (NOTHING PROMOTED)

`studies/s12b_first_half_hour_expressions.py` → `results/v1/s12b_first_half_hour_expressions/`, registry `S12b`, amendment A5.1 (re-run with both vertical sides filled). SPY/QQQ/IWM 0DTE, 2022-11 → 2026-10; controls = the same structures in a random direction (5 seeds).

| structure | cell | n | mean $/contract [CI] | win | PF | random direction | strategy − random [CI] | by symbol |
|---|---|---|---|---|---|---|---|---|
| long 0.45-delta, 10:00 → 15:00 | all days | 2,499 | −4.87 [−14.18, +4.87] | 33 % | 0.92 | −11.99 | +6.94 [−2.00, +15.65] | SPY −3.8, QQQ −6.0, IWM −4.8 |
| long | \|first 30 m\| ≥ 0.3 % | 936 | −6.25 [−23.84, +14.87] | 33 % | 0.91 | −15.01 | +8.48 [−6.98, +25.70] | SPY −9.4, QQQ −2.4, IWM −9.7 |
| short opposite-side vertical (0.30/0.15), 10:00 → 15:50, stop 2 × | all days | 2,455 | **−2.56 [−4.72, −0.33]** | 54 % | 0.87 | −5.15 | +2.48 [+0.25, +4.73] | SPY −2.3, QQQ −2.1, IWM −3.8 |
| short vertical | \|first 30 m\| ≥ 0.3 % | 909 | −1.48 [−5.61, +2.63] | 54 % | 0.93 | −6.87 | **+5.26 [+1.02, +9.52]** | SPY +1.1, QQQ −1.0, IWM −4.0 |
| short vertical, one adverse tick | all / large-open | 2,455 / 909 | −6.76 [−8.85, −4.67] / −5.94 [−9.82, −2.01] | 48 % | 0.68 / 0.74 | | +2.26 / +4.69 | |

**Reading.** The first-half-hour direction is worth $2.5–5 per contract relative to a coin flip — the S12 rest-of-day effect, priced through an option — and both structures lose more than that to spread and theta: the long loses the day's theta, the short vertical loses the two spreads plus the stop-outs on the days the direction is wrong. Nothing clears zero; the only positive symbol cell (SPY short vertical on large-open days, +$1.08) is inside the noise. The A5 batch is now complete except for the single-name intraday screen (S06 on Tier A, bars pulling) and the S11 event verticals.

## S11 (preliminary) — single-name short verticals into breakouts and beats; pre-earnings longs (NOTHING PROMOTED; 12 % of the chains)

`studies/s11_event_verticals.py` → `results/v1/s11_event_verticals/`, registry `S11-prelim`, amendments A4, A5.2, A6. The vendor throttled the per-event option-EOD pull to ~0.17 requests/s, so 876 of the 7,166 event and control chains arrived in the first window (a hash-ordered, therefore uniform, 12 % sample); the remainder is queued. The pre-registered 2 × credit stop proved defective on end-of-day marks for single-name spreads (A6), so three exit sets are reported.

| cell | n | mean $/spread [CI] | win | control (random dates) | event − control [CI] | by year |
|---|---|---|---|---|---|---|
| breakout fade, short 0.30/0.15 vertical, 21-session hold | 173 | **−193 [−285, −111]** | 40 % | −187 | +87 [−66, +244] | 2024 −72, 2025 −219, 2026 −333 |
| … cap at credit + ½ width | 173 | −184 [−254, −120] | 36 % | −192 | +55 [−64, +168] | |
| … 2 × credit stop (A4 design) | 173 | −169 [−205, −133] | 16 % | −159 | +22 [−34, +75] | |
| beats, short call vertical | 10 | (n too small) | | | | |
| pre-earnings long call / straddle / debit vertical, 10 sessions | 18–20 | (n too small; debit vertical −327 [−594, −122]) | | | | |

**Reading so far.** Selling a 0.30-delta call spread on these names and holding three weeks lost about $190 per spread in 2024–2026 whether or not the name had just broken out: the loss belongs to the period (single names rallied) and to the structure, not to the trigger, and the random-date control says so. The breakout-minus-control difference is positive but inside a ±$150 interval. The beat and pre-earnings cells cannot be read at n ≤ 20. Nothing is promoted; the study re-runs when the pull completes.

## S06 on Tier A — the intraday triggers on 34 single names and ETFs, 2017 → 2026 (NOTHING PROMOTED)

`studies/s06_signal_screen.py` → `results/v1/s06_signal_screen_tierA/REPORT.md`, registry `S06-TierA`. The same seven triggers and four filter sets as S06, on the Tier A names whose 1-minute bars were pulled in full (AAPL, ADBE, AMD, AMZN, AVGO, COIN, COST, CRM, DIA, GOOG, GOOGL, HYG, IVV, JPM, LLY, LQD, META, MSFT, MSTR, MU, NFLX, NVDA, SMCI, SMH, SOXL, TLT, TQQQ, TSLA, TSM, UNH, V, VOO, XLF, XOM), 8,257,109 trigger events. Promotion needs ≥ 100 trading days and ≥ 500 events per cell, an absolute day-clustered lower bound ≥ +3 bp at 30 or 60 minutes, and a positive paired lower bound against random minutes (A1). A first pass was invalid — NaN prices on no-trade minutes poisoned the recursive indicators (`06_implementation_record.md` 22:50) — and is archived in `results/v1/superseded/`.

**808 well-sampled cells; none clears the absolute hurdle; none clears both parts.** Medians across the 34 names, by trigger (raw): RSI cross −0.2 bp at 30 minutes, VWAP reclaim −0.1, 5-minute EMA cross −0.1, breakout +0.1, retest −0.0, trend pullback −0.2, bounce −0.4. Breakouts and retests fire after +37 to +50 bp of movement in the prior 30 minutes and trail random minutes in the same direction by −8 to −15 bp at 60 minutes; bounces fire after −57 to −66 bp and "beat" random by +7 to +13 bp — the control artefact of A1, with absolute returns of zero. 60 cells beat their random control against 40 expected by chance; the best absolute cell (AMD breakout with 15-minute alignment, +4.7 bp [+2.0, +6.9] after a +93 bp run-up) is −24 bp against random, negative in all ten years.

**Reading.** The single-name universe adds nothing the index ETFs did not show: the catalogue's triggers fire after the move on every product and carry no forward information. This closes the intraday entry question for the Compass setup families on the data available.

## S17 — index put-writing (the volatility risk premium), SPY and QQQ monthly, 2012-06 → 2026-10 (PASSES A7 for four cells, as a carry lane)

`studies/s17_put_write.py` → `results/v1/s17_put_write/REPORT.md`, registry `S17`, amendment A7 (pre-registered before any data). 167 monthly cycles per symbol: on each monthly expiration's last trading day, sell the next monthly at the closing **bid**, hold to its last trading day, settle at intrinsic against the 16:00 close (2017 →) or put-call parity (2012–17; parity error vs the close: median 6.9 bp, mean −0.9 bp). $0.70 per contract per leg both ways; interest on collateral not credited.

| cell | win | avg win / avg loss (% of credit) | mean $/contract/month [95 % CI] | premium kept, % of credit [CI] | one adverse tick | sub-periods positive | ann. return / vol / max DD | alpha per cycle vs underlying [CI] (beta) | worst cycle |
|---|---|---|---|---|---|---|---|---|---|
| QQQ ATM put | 80 % | +96 / −210 | **+199 [+58, +326]** | +36 % [+10, +58] | +198 [+58, +330] | 5 / 5 | +8.0 % / 11.1 % / −23.7 % | −0.09 % [−0.44, +0.36] (0.49) | Mar-2020 −$5,457 |
| QQQ 0.30-delta put | 86 % | +97 / −298 | **+151 [+46, +241]** | +41 % [+8, +67] | +150 [+42, +241] | 5 / 5 | +5.8 % / 8.8 % / −22.5 % | −0.05 % [−0.45, +0.44] (0.34) | Mar-2020 −$5,031 |
| QQQ 0.15-delta put | 93 % | +98 / −650 | **+89 [+20, +139]** | +51 % [+1, +85] | +88 [+16, +138] | 4 / 5 | +3.4 % / 6.1 % / −19.6 % | −0.01 % [−0.46, +0.39] (0.19) | Mar-2020 −$4,191 |
| SPY ATM put | 83 % | +94 / −259 | **+200 [+17, +347]** | +34 % [+2, +59] | +199 [+16, +346] | 5 / 5 | +6.4 % / 10.9 % / −29.6 % | −0.09 % [−0.44, +0.39] (0.56) | Mar-2020 −$9,871 |
| SPY 0.30-delta put | 86 % | +99 / −342 | +132 [−17, +243] | +37 % [−9, +69] | | 4 / 5 | | | |
| SPY 0.15-delta put | 95 % | +98 / −961 | +76 [−50, +149] | +43 % [−35, +88] | | 4 / 5 | | | |
| 0.30/0.15 put spreads | 84–86 % | | SPY +51 [−11, +107]; QQQ +56 [−1, +105] | | | | | | |
| 0.30-delta covered call, option leg | | | SPY -66 [-157, +17]; QQQ -78 [-186, +15] | SPY −32 %, QQQ −47 % | | | | | |
| buy-and-hold (price) | | | | | | | SPY +13.6 % / Sharpe 0.88 / −31.4 %; QQQ +18.9 % / 1.03 / −32.1 % | | |

**Reading.** This is the first configuration in the research that passes its pre-registered gate: selling at-the-money and 0.30-delta puts on QQQ, and at-the-money puts on SPY, every month for 14 years, at the real closing bid with fees, kept +34 % to +41 % of the premium net (+51 % for the 0.15-delta QQQ put), won 80–93 % of months, was positive in every three-year block and did not depend on fill quality. The puts were overpriced against what they paid out — the variance risk premium, measured directly. What it is not: (1) not alpha against the index — the regression intercept is zero, the strategy is about half the index's exposure (beta 0.5), and over this bull-market window it earned less per unit of risk than holding the index (interest on the cash collateral, ≈ 1.6 %/yr on average, is not credited and would narrow but not close that gap); (2) not robust to a ten-cell multiplicity correction (Bonferroni lower bounds −$11 to −$72), i.e. about two standard errors per cell; (3) not safe — the losses are crash losses, one month (March 2020) cost 16–21 months of average profit. The calls sold against the stock were not overpriced: the option leg of the covered call averaged −$66 (SPY) and −$78 (QQQ) per contract, intervals including zero, so the covered call's positive total is the stock's return. Put spreads did not clear their bound: the protective leg costs most of the premium.

**Status:** research_candidate carry lane under Premium Selling (cash-secured puts), sized as an index-exposure decision rather than a trading signal. It is not a Compass setup in the sense of the brief (no entry signal, one trade a month).

## V1 / V2 — option pricing across the optionable universe and the earnings volatility cycle, 2023-11 → 2026-09 (REJECTED)

`studies/v1_vol_pricing.py`, `studies/v2_earnings_vol.py` → `results/v1/v1_vol_pricing/`, `results/v1/v2_earnings_vol/`; amendments A8–A8.3c, A9; full write-up `intel/02_volatility_pricing.md`. Unusual Whales closing chains (equal to ThetaData's closing NBBO on 638/638 contracts), ThetaData raw closes, corporate actions read from the options market itself.

- **V1:** 44,447 ATM monthly straddles over 34 months. Shorting every one at the bid lost −13.2 % of premium a month in development + validation [−22.3, −5.2] and −23.6 % in the hold-out. Sorting on IV ÷ RV21 ranks forward volatility correctly (the richest quintile realised 2.3 vol points under implied) but selling it still lost, and it improved on shorting everything by +2.7 % [−2.4, +8.7] (dev + val) and −0.03 % (hold-out). Skew: no edge. Term slope (30,481 name-cycles): long-short −22.2 % (dev + val), −16.5 % (hold-out), no improvement over shorting everything.
- **V2:** 11,802 reports. Selling the straddle across the report lost −26.1 % (dev + val) and −34.2 % (hold-out); buying it into the report lost −20.9 % and −29.3 %. Reports moved 0.59 of the implied move (median), but the premium sellers earn at the mid (+6.9 % on same-day settlements) is smaller than half the straddle's spread (12.9 % median), and in the tightest-spread names it is negative even at the mid.
- **Reading:** single-name option prices are not mispriced in a way that can be traded after the bid/ask, monthly or around earnings, on this window. The volatility premium that pays is the index one (S17).

## V5 — are same-day index chains priced to what follows? (A12; NO TEST REJECTS, nothing promoted)

`studies/v5_chain_calibration.py` → `results/v1/v5_chain_calibration/` (`tests.csv`, `curve.csv`, `band_all_roots_devval.csv`), registry `V5`.

**Design.**
- Every one-strike vertical out of the money on each side, at 10:00 and 13:00: 112,993 verticals on 3,688 same-day chain-days.
  - SPXW from 2022-05, SPY and QQQ from 2022-11, IWM from 2024-04.
  - Each leg two-sided, relative spread ≤ 20 %.
- Price per unit width at the mid against the realised payoff per unit width at the 16:00 settlement.
- Distance is measured in implied moves (the ATM straddle).
- Sessions weigh equally; intervals resample sessions.
- Development + validation runs 2022 → 2025-09. Primary: SPXW, |distance| 0.5–1.5. Holm at α 0.01 across four tests.

| SPXW, 0.5–1.5 implied moves, dev+val | price | realised | edge at mid [95 %] | Holm p | seller after bid/ask [95 %] | buyer after bid/ask [95 %] |
|---|---|---|---|---|---|---|
| 10:00 puts (836 sessions) | 0.207 | 0.196 | −0.008 [−0.032, +0.017] | 1.0 | −0.039 [−0.064, −0.016] | −0.055 [−0.077, −0.030] |
| 10:00 calls (835) | 0.215 | 0.219 | +0.007 [−0.016, +0.031] | 1.0 | −0.047 [−0.072, −0.023] | −0.032 [−0.056, −0.009] |
| 13:00 puts (841) | 0.202 | 0.174 | −0.025 [−0.047, −0.002] | 0.14 | −0.001 [−0.025, +0.021] | −0.051 [−0.073, −0.028] |
| 13:00 calls (841) | 0.214 | 0.209 | −0.002 [−0.024, +0.022] | 1.0 | −0.022 [−0.046, +0.002] | −0.026 [−0.049, −0.001] |

Units are fractions of the vertical's width (0.01 = 1 % of width).

**Reading.**
- **SPXW's same-day chain is priced within about ±3 % of width of what followed** at 0.5–1.5 implied moves. No test rejects at the registered α.
- **After the bid/ask, neither side earns.** The seller of 13:00 out-of-the-money put verticals comes closest, at break-even.
- **At 10:00 sharp the quotes are wider**, because economic releases land at 10:00:00 (on 2025-03-14 the SPX spreads went from 0.2–0.4 to 1.5–2 points in that minute). That cost belongs to the entry time chosen.
- **Touches against the chain's own price come out at 0.88–1.08 × twice the price** (`curve.csv`). The reflection principle holds against the option's price as well as against realised frequencies (`intel/06_price_action_atlas.md` §3).

**Outside the tested family (descriptive; the forward hold-out decides).**
- On SPY, QQQ and IWM, 13:00 out-of-the-money puts realised less than their price: −0.034, −0.044 and −0.065 of width, each interval below zero.
- Sellers of 13:00 one-strike verticals came out near break-even or slightly positive after the bid/ask. Only IWM's lower bounds touch or clear zero: puts +0.038 [0.000, +0.074], calls +0.049 [+0.004, +0.090], on 257 and 189 sessions from 2024-04 only.
- It agrees with the ETF grid's 13:00 strangle (positive only in its TEST window) and with H15's open 14:05 SPXW strangle lane.
- Of 16 descriptive cells, chance alone would put a lower bound above zero in about 0.4. Two clear here, both IWM at 13:00, correlated with each other and on 189–257 sessions. It is recorded for a forward-only registration, never promoted on these sessions.
