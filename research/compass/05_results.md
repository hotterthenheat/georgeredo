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

- S02: single-factor grid and ablations around S01 (41 variants) with walk-forward selection by year (running).
- S03: baseline on Weekly-category expirations, SPY/QQQ/IWM 2017-06 → 2026-10, OI > 250 and intraday volume > 100 applied (chains being pulled).
- S06 on the Tier A single-name universe once its minute bars are cached (S05).

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
