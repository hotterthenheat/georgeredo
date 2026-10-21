# Compass Modules 12–16: the Weekly / Swing / LEAPS engine, its contract picker, earnings gate, Helix isolation, cents normalization and dead-code quarantine

Scope: the multi-day part of the Compass spec (Modules 12–16, with the multi-day parts of Modules 2 and 3). Every number below comes from a script in `research_notes/Compass engine audit/horizons/` (named in each section); the literature is cited with URLs. Train = 2022–2024, check = 2025–2026-10-13, never touched for selection. Fees where options are priced: buy at the ask, sell at the bid, $0.65 a contract each way. Nothing in this note is a trade instruction.

**My reading of the truncated spec (stated so it can be corrected).** The swing engine is four boolean gates with no weights: B1 trend/structure alignment on the daily and weekly bars; B2 a pullback into a liquidity zone — the OTE retracement, 0.62–0.705 of the last impulse — rather than a chase; B3 a volume or flow confirmation (relative volume at or above a norm; flow has no history); B4 alignment with the macro dealer book (the target wall within one expected move, the stop beyond the put/call wall). Contract picker: Weekly 0.35–0.50 delta; Swing 0.40–0.55 delta with open interest ≥ 500; LEAPS 0.60–0.80 delta, rolled under 60 DTE. Exits: an underlying level stop (below the put wall / prior-day low / prior-week low, 2.4–4.6 % away, median 3.45 %), a premium backstop of −20 % (A+) / −17 % (A), scale-outs of 25 % at +25–29 % and 50 % at +50 %, a trail lock at +21–31 % exiting 3–5 points under it, an RSI(14) momentum exit, a 3-trading-day time stop on 8–13 DTE swings; LEAPS a −25 % premium stop or a weekly close beyond the macro wall / 200-DMA, scaled 33 % at +50 % and +100 %. Earnings gate: no swing across an earnings date. Helix: telemetry only. Cents normalization: one price unit. Dead-code quarantine: the old caps and floors removed. The vendor's ledger (N = 35 swing trades) is an outcome record, not a causal rule, and nothing here treats it as one.

**Data used.** Underlying daily bars: SPY, QQQ, IWM aggregated from the 1-minute regular-session files (2012-06-01 → 2026-10-09, `02_daily_bars.py`); the twenty names from `data_lake/thetadata/stock_eod` parts (2020-01-02 → 2026-10-13; SOFI from 2021-06-01, IBIT from its 2024-01-11 listing; the parts on disk start in 2020, so the names have no earlier history). Unadjusted closes with nine splits detected and back-adjusted (AAPL, TSLA ×2, AMZN, GOOGL, GME, AVGO, NVDA ×2, MSTR; `engine.py`). The top-20 names are the twenty largest non-ETF option roots by contract volume summed over the five ThetaData bulk option-EOD days 2026-10-06…10-12 (`01_top20.py`): NVDA, TSLA, AAPL, MU, INTC, AMZN, TLT, META, EWZ, PLTR, AMD, IBIT, MSFT, GOOGL, MSTR, HYG, AVGO, SOFI, ORCL, and GME in place of SPCX (SpaceX listed in 2026 and has no train history). Earnings: UW `earnings.parquet` (quarterly rows carry a report date and pre/post-market time from 1996). IV: UW `iv-rank__1y` (2025-10-14 → 2026-10-13). Dealer book: UW `greek-exposure` daily totals (2025-10-15 → 2026-10-13). Option chains: the five bulk option-EOD + OI days only — **multi-day option price paths are not on disk**, so every option figure below is a Black-Scholes model on the underlying's path, not a backtest.

---

## 1. The booleans, defined in code, and what each one does on its own

### Takeaway
Defined from daily bars (`engine.py features()`), the trend gate B1 fires on ~41 % of name-days, the OTE pullback B2 on ~5 %, the 1.5× volume gate B3 on ~10 %; **the strict same-day AND of the three fired 14 times in 2022–2024 and 6 times in 2025–2026 across 23 names** — N = 20, not 500. No single boolean has out-of-sample ranking power (AUC 0.49–0.51), and the OTE pullback alone is the only one that is negative in train.

### Definitions (all known at the close of day t; entry is the next session's open)
- **B1 (trend):** close > EMA21 and close > EMA50, and the last *completed* week's close > its 10-week EMA (the week that ended before t's week, so no look-ahead). Alternatives tested, not picked: daily-only (`B1_daily`), EMA stack `close > EMA21 > EMA50` (`B1_slope`), `close > SMA200 & > EMA21` (`B1_200`), the running partial week (`B1_partial`).
- **B2 (OTE pullback, doji-safe):** the impulse is taken on closes, not wicks — the highest close of the last 30 sessions and the lowest close before it inside the window; it counts only if the high is ≥ 2 sessions old (a pullback exists) and the impulse is ≥ 2 × ATR14. B2 is true when the day's **low** reaches 0.62 of the impulse and the **close** is not below 0.705 (`r_low ≥ 0.62 and r_close ≤ 0.705`). Alternatives: a touch of the 21-EMA with a close back above it (`B2_ema`), a wide zone 0.50–0.786 (`B2_wide`), the close itself inside the zone (`B2_close`).
- **B3 (volume):** today's volume ≥ 1.5 × the mean of the prior 20 sessions. Alternatives: 1.2× (`B3_12`), a range expansion `true range ≥ 1.5 × ATR14` (`B3_range`), either (`B3_any`).
- **B4 (dealer book):** untestable before 2025-10-15 (no OI-by-strike history); run with B4 off; a sign proxy is in §5.
- Short side mirrored (S1: below the EMAs and the weekly; S2: a rally into 0.62–0.705 of a down-impulse; S3 = B3).

### Cited Findings (computed; `04_run.py`, `fixed_hold_results.csv`, `gate_counts.csv`; forward return = close of session t+H over the open of t+1, gross, long side)
| Condition | N train / check | H=5 mean train / check | H=10 | H=20 |
|---|---|---|---|---|
| ALL name-days (the baseline) | 16,721 / 10,131 | +0.74 % / +0.57 % | +1.55 % / +1.26 % | +3.20 % / +2.62 % |
| B1 trend | 6,933 / 4,440 | +0.41 % / +0.55 % | +0.49 % / +1.40 % | +1.10 % / +2.76 % |
| B2 OTE pullback | 872 / 626 | **−0.41 % (t −1.6) / +0.11 %** | −0.09 % / +0.15 % | +0.55 % / +0.32 % |
| B3 volume ≥ 1.5× | 1,634 / 1,003 | +1.53 % / +0.55 % (without the best 5 trades: +0.36 % / +0.42 %) | +2.31 % / +1.24 % | +4.04 % / +2.41 % |
| B1 & B2 | 138 / 90 | +0.14 % / −0.29 % | −0.15 % / −0.27 % | +0.63 % / **−2.13 % (hit 37 %, t −1.9)** |
| B1 & B2 & B3 (the strict gate) | 14 / 6 | −0.92 % / −2.33 % | −0.37 % / −3.57 % | −1.20 % / −2.77 % (N 5) |
| B1 & B2_ema (EMA touch, no volume) | 551 / 391 | +0.83 % (t 3.1) / +0.93 % (t 2.7) | +0.36 % / +1.26 % | +1.40 % / +1.28 % |

- The trend gate B1 *underperforms* the unconditional baseline in every horizon in train (2022's bear year is in train; buying above the EMAs bought the rallies that failed) and roughly matches it in check.
- Every alternative of B1/B2/B3 inside the AND gate has N between 1 and 31 per split (`fixed_hold_results.csv` rows `B1_daily&B2&B3` … `B1&B2&B3_any`); none can be read.
- Out-of-sample AUC of each boolean for "forward return > 0" (`09_logistic.py`): B1 0.501/0.509/0.505, B2 0.494/0.489/0.489, B3 0.498/0.504/0.500 at H = 5/10/20; the strict gate 0.500.
- The pre-2022 history (`04c_all_years.py`, `all_years_fixed_hold.csv`; ETFs 2013–2021 and the names 2020–2021, N 13,460 name-days) gives the same picture: B2 +0.69 % at H10 vs ALL +1.76 %; the strict gate N = 9.

### Inferences
- A pullback day that touches the OTE zone **and** prints 1.5× volume inside an uptrend is, by construction, a distribution day; requiring both on one day leaves almost nothing, and what is left is slightly negative. The spec's booleans are not independent conditions; two of them fight.
- "Doji-safe" is honoured by taking the impulse on closes; using wicks (not reported) would only enlarge the impulse and move the zone lower, not change the sign of the result.

### Gaps
- Flow confirmation (B3's second leg) has no history on disk (UW flow is one day per request); B4 has no history (§5).

---

## 2. The backtest on daily bars: the gate with the spec's holds and exits, against random entries

### Takeaway
To reach a readable N the gate was read as a **sequence** (declared before any return was looked at: the OTE touch within the last 5 sessions, B1 today, 1.2× volume today and an up close — `SEQ5_12`, N = 105 train / 71 check; four other sequenced readings reported alongside). With the spec's swing exits (prior-week-low stop, 1 × expected-move target, 20 sessions) it returned **−1.95 % a trade in train and −1.72 % in check**, while count-matched random entries with the same exits returned +0.99 % and +1.15 %: the gate is worse than random in both periods (p(random ≥ gate) = 1.000 and 0.995). The weekly and LEAPS holds show the same: nothing the gate selects beats a day picked at random.

### Cited Findings (computed; `04b_sequenced.py`, `seq_fixed_hold_results.csv`, `seq_rule_exit_results.csv`, `seq_rule_exit_why.csv`, `seq_gate_counts.csv`)
Sequenced gates, fixed holds, gross, long:

| Gate (2022–2026 count) | N train / check | H5 | H10 | H20 | H63 |
|---|---|---|---|---|---|
| SEQ3 (OTE in last 3 d, 1.5× vol, up close) (53) | 32 / 21 | −0.71 % / −0.10 % | −2.48 % / +0.64 % | −1.42 % / −0.53 % | +1.30 % / +6.38 % |
| SEQ5 (last 5 d, 1.5× vol) (89) | 54 / 35 | −1.19 % / +0.70 % | −2.08 % / +1.91 % | −1.65 % / −1.53 % | +3.35 % / +6.49 % |
| SEQ3_12 (last 3 d, 1.2× vol) (109) | 68 / 41 | +0.48 % / −0.46 % | −1.93 % / +0.18 % | +0.04 % / −0.89 % | +7.06 % / +3.87 % |
| SEQE3 (EMA touch in last 3 d, 1.5× vol) (92) | 65 / 27 | +0.03 % / +0.08 % | +1.45 % / −0.17 % | +2.51 % / −1.99 % | +6.63 % / −3.98 % |
| **SEQ5_12** (last 5 d, 1.2× vol) (176) | 105 / 71 | −0.15 % / −0.26 % | −1.63 % / +1.02 % | −0.47 % / −1.08 % | +6.70 % (t 2.6) / +2.36 % |
| SEQ5_12 without the up-close (218) | 125 / 93 | +0.34 % / −0.22 % | −0.88 % / +0.39 % | +0.10 % / −1.34 % | +6.91 % / +2.47 % |
| ALL name-days | 16,721 / 10,131 | +0.74 % / +0.57 % | +1.55 % / +1.26 % | +3.20 % / +2.62 % | +7.12 % / +9.43 % |

- The one positive-looking cell, SEQ5_12 at H63 in train (+6.70 %, hit 58 %), is below the unconditional +7.12 %, drops to +3.16 % without its best five trades, and is +2.36 % with a 45 % hit rate in check (−4.63 % without its best five). By year at H20: 2022 −23.9 % (N 11), 2023 +1.76 % (42), 2024 +2.69 % (52), 2025 +0.33 % (37), 2026 −3.34 % (23).
- Bootstrap by entry date (500 resamples), SEQ5_12 H20: 95 % interval −3.6 % … +2.9 % train, −3.6 % … +1.6 % check — zero inside both.
- ETFs vs names inside SEQ5_12 at H20: SPY/QQQ/IWM N = 7 train (+2.0 %, hit 86 %) and 9 check (+1.7 %, hit 67 %); the names N = 98 (−0.65 %, hit 49 %) and 51 (−1.57 %, hit 33 %). Too few ETF entries to read, but the names are where the gate loses.
- Short side mirrored (SSEQ5_12, N 103 / 50 at H20): +1.68 % train, **−6.86 % check (t −2.4)**; at H63 −4.1 % / −17.2 %. Buying puts on a rally into a down-impulse's OTE lost heavily in 2025–2026.

Rule exits on SEQ5_12 (entry next open; stop and target on an intraday touch, a gap filled at the open, the stop first when both touch; otherwise out at the close of session H), gross on the underlying:

| Variant | SEQ5_12 train (N 105) | SEQ5_12 check (N 60–71) | ALL days, same rules, train / check |
|---|---|---|---|
| Weekly: H5, prior-week-low stop, 1×EM target | +0.81 % (hit 49 %) | −0.48 % (hit 51 %) | +0.25 % / +0.21 % |
| Weekly: H5, prior-day-low stop | −0.71 % | +0.09 % | +0.15 % / +0.14 % |
| **Swing: H20, prior-week-low stop, 1×EM target** | **−1.95 % (hit 40 %)** | **−1.72 % (hit 35 %)** | +0.56 % / +0.80 % |
| Swing + 3-day stall exit | −1.37 % | −0.74 % | +0.36 % / +0.66 % |
| Swing + RSI(14) turn exit | −2.10 % | −1.51 % | +0.40 % / +0.55 % |
| Swing, week-low stop, no target | −2.21 % | −1.60 % | +0.98 % / +1.34 % |
| Swing, fixed −3.45 % stop, 1×EM target | −1.42 % (hit 26 %) | −1.11 % (hit 22 %) | +0.50 % / +0.62 % |
| Swing, prior-day-low stop | −2.22 % (hit 16 %) | −0.41 % | +0.31 % / +0.40 % |
| Swing, no stop, no target (fixed 20) | −0.47 % | −1.08 % | +3.20 % / +2.62 % |
| LEAPS: H63, −8 % stop | +0.61 % | +0.23 % | +3.30 % / +4.18 % |
| LEAPS: H63, no stop | +6.70 % | +2.36 % | +7.12 % / +9.43 % |

- Where the swing trades ended (SEQ5_12, week-low stop, EM target): train 46 stops at −10.8 %, 27 targets at +13.8 %, 32 time exits at −2.5 %; check 18 stops at −10.3 %, 13 targets at +12.1 %, 29 time exits at −2.6 %. The stall rule turned 46 train / 31 check trades out at −3.0 % / −3.7 % on day 3 — it cut losers and winners alike.
- **The level stop is not where the spec says it is.** With entries 62–70 % down an impulse, the prior-week low sits a median 8.25 % below the entry (q25 −12.1 %, q75 −5.0 %, 10th percentile −17.7 %), not 2.4–4.6 %; the 1 × expected-move target (σ20 × √20) is a median +10.3 % away. The spec's "median 3.45 %" stop is a ledger fact from 35 vendor trades, and it is reachable only with a tighter stop (prior-day low: median closer, but hit rate 16 %) or a fixed 3.45 % (hit 22–26 %).
- Random baseline (`04b_sequenced.py`): 200 draws of the same number of entry days per symbol-year as SEQ5_12, same swing exits — mean +0.99 % (sd 0.78 %) in train and +1.15 % (sd 1.15 %) in check; the gate's −1.95 % / −1.72 % is below 200 of 200 and 199 of 200 draws.

### Inferences
- The gate does not pick good days; it picks days after a 62–70 % give-back inside an uptrend, which in 2022–2026 were on average worse than any other day for the next one to four weeks, and the spec's exit geometry (an 8 % stop against a 10 % target at a 35–40 % hit rate) loses even on days with no selection at all.
- N > 500 is **not reachable with the spec's booleans on this universe at daily resolution**: the strictest reading gives 20 entries, the loosest sequenced reading 218, over 23 names and 4.8 years. Reaching 500 would need either a wider universe (which the spec's "liquid names" rules out) or booleans so loose they no longer describe the setup.

### Gaps
- No intraday resolution for the entry (a pullback "into" a zone during the session and a same-day confirmation cannot be separated on daily bars); the sequenced reading is the closest daily equivalent and is declared, not tuned.
- The underlying results are gross; friction on the option leg is in §3.

---

## 3. Option-level EV: Black-Scholes on the gate's paths (a model, not a backtest)

### Takeaway
Repriced as the spec's calls, the sequenced gate loses at every horizon after spreads and fees: **weekly (7 DTE, 0.425 Δ) −13 % to −15 % a trade with the −20 % premium stop; swing (14–30 DTE, 0.475 Δ) −17 % to −26 % in train and −3 % to −17 % in check; LEAPS (180 DTE, 0.70 Δ) +15 % in train only because of five trades (+0.9 % without them) and −4 % in check.** The −20 %/−17 % premium stop fires before the level stop every time: at 7–14 DTE three sessions of pure decay already take 19–42 % off the premium.

### Method (`05_option_model.py`)
Each entry's daily closes (plus the entry open) are repriced with Black-Scholes at a constant vol: the name's UW implied vol on the entry date where the `iv-rank__1y` table has it (2025-10-14 → 2026-10-13), else the name's median UW IV over that year (a stated constant: SPY 0.144, QQQ 0.206, IWM 0.212, AAPL 0.254, NVDA 0.396, TSLA 0.456, AMD 0.576, MU 0.701, MSTR 0.715, INTC 0.661 …). r = 4 %, q = 0. Strike solved from the band's middle delta (weekly 0.425, swing 0.475, LEAPS 0.70). Fills: buy mid × (1 + s/2), sell mid × (1 − s/2), s = 3 % of mid for ETFs and 8 % for single names (the measured October-2026 spreads are in §6: 1.0–1.2 % ETF, 5.1–5.3 % single at the swing/weekly bands, 8.5 % at 8–14 DTE on single names — so 8 % is about right for singles and 3 % generous against the ETFs' real 1 %); $0.65 a contract each way. Exits on the option's modelled close: the underlying level stop (prior-week low, option sold at that spot), premium stop −20 %/−17 %, scale-outs at +27 % (25 %) and +50 % (50 %) with 4 contracts (2 contracts: 50 % at +50 %), trail lock at +26 % exiting 4 points under, RSI(14) turn, time. The hold never outlives the contract (sessions × 7/5 ≤ DTE − 1). Returns are on the premium paid.

### Cited Findings (computed; `option_model_results.csv`, `05.log`; SEQ5_12 entries, N 105 train / 71 (weekly) or 60 (swing) or 51 (LEAPS) check)
| Contract, hold | Exit | Train mean (hit) | Train without best 5 | Check mean (hit) | Check without best 5 |
|---|---|---|---|---|---|
| Weekly 7 DTE, 4 sessions | hold | +4.1 % (29 %) | −29.7 % | −15.0 % (23 %) | −43.1 % |
| Weekly 7 DTE | level + prem −20 % | −13.3 % (12 %); 87/105 stopped on premium | −38.6 % | −14.9 % (13 %); 56/71 | −41.9 % |
| Weekly 7 DTE | + 4-contract scale-out | −14.4 % | −37.5 % | −10.6 % (30 %) | −24.7 % |
| Weekly 10 DTE, 5 sessions | hold | −5.0 % (27 %) | −31.5 % | −10.5 % (32 %) | −35.6 % |
| Swing 14 DTE, 8 sessions | hold | −7.6 % (28 %) | −32.9 % | −23.5 % (25 %) | −48.4 % |
| Swing 14 DTE | level + prem −20 % | −18.6 % (11 %) | −38.2 % | −17.0 % (13 %) | −36.5 % |
| Swing 14 DTE | all rules, 4 contracts | −14.0 % (21 %) | −27.6 % | −15.0 % (28 %) | −24.7 % |
| Swing 21 DTE, 12 sessions | hold | −0.3 % (27 %) | −29.3 % | −25.3 % (22 %) | −56.3 % |
| Swing 21 DTE | level + prem −20 % | −17.4 % (11 %) | −36.5 % | −3.0 % (15 %) | −31.9 % |
| Swing 21 DTE | level + prem −17 % | −17.8 % | −36.9 % | −0.3 % | −29.0 % |
| Swing 21 DTE | + trail lock | −16.4 % | −33.3 % | −11.9 % | −33.5 % |
| Swing 21 DTE | + RSI exit | −16.7 % | −30.8 % | −9.4 % | −30.1 % |
| Swing 30 DTE, 20 sessions | level + prem −20 % | −26.4 % (t −4.5) | −37.6 % | −2.8 % | −34.1 % |
| LEAPS 180 DTE 0.70 Δ, 63 sessions | hold | +15.0 % (45 %, median −8.7 %) | +0.9 % (−0.2 % without best 5 days) | −4.4 % (29 %) | −29.3 % |
| LEAPS | prem −25 % | +1.7 % | −9.7 % | −13.2 % | −30.4 % |
| LEAPS | prem −25 % + 3-contract scale | −0.4 % | −6.9 % | −14.3 % | −26.6 % |
| ALL days (15 % sample, N 2,456 / 1,547), swing 21 DTE, level + prem −20 % | | +0.9 % (17 %) | −2.3 % | −3.1 % (17 %) | −5.7 % |
| Strict gate (N 14 / 5), swing 21 DTE, level + prem −20 % | | −51.2 % (0 %) | | −29.6 % (0 %) | |

- **Premium-stop geometry** (BSM, 0.475 Δ call, spot 100): at 7 DTE the premium is 0.76–2.21 % of spot (IV 15–45 %) and −20 % is a 0.34–1.00 % dip on day 0; after three sessions pure decay alone is 42 %, so the stop fires with no move. At 14 DTE −20 % is 0.48–1.39 % on day 0 and decay alone is 19–20 % in three sessions. At 30 DTE −20 % is 0.70–1.98 % on day 0 and 0.36–1.08 % after three sessions (decay 9 %). The level stop (median 8.25 % below entry, §2) is never reached first: in the model 84–87 of 105 train swing trades left on the premium stop and 7–9 on the level.
- The all-days option baseline with the same contract and exits is also negative-to-flat (+0.9 % / −3.1 %), i.e. the structure loses on random days too; the gate makes it worse by 15–20 points in train.

### Inferences
- A −20 % premium backstop on a 7–14 DTE call is a two-to-three-session time stop; it cannot coexist with a "hold to the target" plan at those tenors. If a premium backstop is kept it has to be sized to the tenor's decay (e.g. ≥ 45 % at 7 DTE, ≥ 25 % at 14 DTE) or dropped for the level stop alone, which the model says loses less at 21–30 DTE (hold-only −0.3 % vs −17 % in train at 21 DTE).
- The LEAPS mean in train is five trades (MU, MSTR, TSLA runs of 2023–2024); on a median basis a 0.70-delta LEAPS held 63 sessions lost 8.7 % in train and 29 % in check.
- Scale-outs raise the hit rate (11 % → 21–28 %) and lower the loss a little but do not change the sign; with one contract they do not exist, with two only the 50 % tier does.

### Gaps
- No option paths: the model holds vol constant (no IV crush after earnings, no vol-of-vol, no skew), prices the stop at the day's close rather than the touch, and uses one spread per class. A real test needs daily option NBBO history for the universe (ThetaData's per-contract EOD or minute history, not on disk; the owner's terminal is in use 13:00–21:00 UTC and was not called).

---

## 4. The scale-out ladder, trail lock and RSI(14) exit

### Takeaway
On the modelled option paths none of the three turns the swing positive; the 4-contract ladder is the least bad (−14 % to −16 % vs −17 % to −19 % with the plain premium stop in train), the trail lock and the RSI exit are within noise of it. **With one contract the 25 %/50 % partials are impossible (0.25 × 1 = 0), with two contracts only the 50 % tier at +50 % exists; four contracts is the smallest size the ladder as written can run.**

### Cited Findings (computed; `option_model_results.csv`, swing 21 DTE / 12 sessions, SEQ5_12, train / check)
- level + prem −20 %: −17.4 % / −3.0 % (hit 10.5 % / 15 %).
- + ladder, 4 contracts (25 % at +27 %, 50 % at +50 %): −16.2 % / −11.7 % (hit 18 % / 23 %).
- + ladder, 2 contracts (50 % at +50 %): −17.3 % / −8.5 %.
- + trail lock (+26 %, out 4 points under): −16.4 % / −11.9 %; 22 / 10 trades left on the trail.
- + RSI(14) exit (RSI turns down from above 70): −16.7 % / −9.4 %; 19 / 6 trades left on RSI.
- Everything together, 4 contracts: −14.4 % / −15.6 %.
- On the underlying (`seq_rule_exit_results.csv`): the RSI exit changed the swing's mean from −1.95 % to −2.10 % in train and −1.72 % to −1.51 % in check; it fired on 10–15 % of trades.

### Inferences
- The partials and the trail convert some of the few large winners into small ones; since the model's EV is carried by those few winners (mean ≫ median everywhere), the rules trade variance for a slightly lower mean. They are position-management conveniences, not edge.

### Gaps
- The "3–5 points below the lock" trail is in premium points; it was modelled as 4 % of the entry premium under the lock (a point on a $5 premium). A points-based trail on a $60 LEAPS behaves differently; not modelled.

---

## 5. The dealer-book gate (B4) and its one-year proxy

### Takeaway
B4 cannot be tested before 2025-10-15 (no open interest by strike on disk before UW's daily `greek-exposure` and the October-2026 bulk files), so every engine result above runs with B4 off. On the one year that has UW's daily book totals, the book's **sign** carried no information for the gate (N = 38 positive-gamma entries, 6 negative) and, unconditionally, negative-gamma days returned slightly more than positive ones — the opposite of a "trade with the book" rule.

### Cited Findings (computed; `08_b4_proxy.py`, 5,738 name-days 2025-10-15 → 2026-10-13, net gamma = UW call_gamma + put_gamma, positive on 75.8 % of name-days)
- All days: H5 +0.45 % (positive gamma, N 4,236) vs +0.70 % (negative, N 1,364); H10 +0.88 % vs +1.20 %; H20 +1.83 % vs +2.54 %.
- SEQ5_12 entries: H5 −0.05 % (N 38) vs +1.62 % (N 6); H20 −1.88 % (N 27, hit 30 %) vs +1.16 % (N 6). Too few to read.

### Inferences
- The proxy is the book's net sign, not the walls or the flip the spec names; a wall-within-one-expected-move test needs the strike-level book through time, which the terminal only began recording in October 2026 (CLAUDE.md, the recorder).

### Gaps
- Blocker: strike-level dealer book history before 2026-10 for the universe. The data needed is UW `spot-exposures/strike?date=` per name per day (≈ 250 calls a name a year on a 3-concurrency plan) or the terminal's own recorder files once they cover a year.

---

## 6. The contract picker: delta bands, the OI ≥ 500 floor, and what friction really is

### Takeaway
On the five October-2026 bulk days the spec's bands are liquid at the index ETFs (median spread 1.0–1.2 % of mid at the weekly and swing bands) and expensive on single names (5.1–5.3 % median, 8.5 % at 8–14 DTE, 90th percentile 18–21 %); **the OI ≥ 500 floor leaves a qualifying 0.40–0.55-delta call in only about half of the 8–28 DTE expiries** (SPY 66 %, QQQ 51 %, IWM 51 %, AAPL 58 %, NVDA 58 %, AMD 46 %, HYG 7 %), because the daily-listed expiries carry little open interest. LEAPS at 0.60–0.80 delta cost 3.7–4.4 % of mid to cross, and rolling at 90 rather than 60 DTE is a wash by Black-Scholes.

### Cited Findings (computed; `07_contract_picker.py`, calls only, closing NBBO, BSM implied vol and delta with r = 4 %; `picker_spread_by_band.csv`, `picker_oi500_by_name.csv`, `picker_expiry_coverage.csv`, `10_leaps_roll.py`)
- Weekly band, 4–7 DTE, 0.35–0.50 Δ: ETF n 185, median spread/mid 1.18 % (mean 2.1 %, 90th pct 3.9 %), median mid $2.93, OI ≥ 500 on 48 %; single names n 281, median 5.26 % (mean 7.3 %, 90th 17.6 %), mid $5.35, OI ≥ 500 on 38 %.
- Swing band, 8–28 DTE, 0.40–0.55 Δ: ETF n 730, median 1.00 % (90th 3.3 %), mid $5.52, OI ≥ 500 on 52 %; single n 1,323, median 5.13 % (mean 8.5 %, 90th 20.7 %), mid $10.60, OI ≥ 500 on 39 %. By tenor on single names at 0.35–0.50 Δ: 8–14 DTE median 8.5 % (q75 20.7 %), 15–28 DTE 4.4 % (q75 8.2 %), 29–60 DTE 5.0 %, 61–120 DTE 3.4 % (the monthlies, OI ≥ 500 on 94 %).
- LEAPS band, 90–400 DTE, 0.60–0.80 Δ: ETF n 3,315, median 4.36 % (90th 10.1 %), mid $62.75, OI ≥ 500 on 31 %; single n 4,540, median 3.71 % (90th 6.1 %), mid $65.16, OI ≥ 500 on 49 %.
- Share of 8–28 DTE contracts at 0.40–0.55 Δ with OI ≥ 500, per name (five days pooled): SPY 59 %, QQQ 34 %, IWM 34 %, AAPL 51 %, NVDA 51 %, TSLA 59 %, AMZN 54 %, META 26 %, MSFT 38 %, GOOGL 41 %, AMD 17 %, MU 12 %, INTC 33 %, AVGO 41 %, ORCL 33 %, PLTR 80 %, MSTR 69 %, SOFI 100 %, GME 65 %, IBIT 47 %, TLT 88 %, EWZ 77 %, HYG 17 %.
- LEAPS roll by BSM (0.70 Δ call bought at 365 DTE, spot unchanged): time value 1.76 at 90 DTE and 1.26 at 60 (IV 20 %, spot 100, entry premium 12.39); the decay from 90 to 60 DTE is 0.81 = 6.6 % of the entry premium (6.4 % at IV 40 %); daily theta 0.026 at 90 DTE vs 0.029 at 60 — a 12 % acceleration, not a cliff. One roll costs about one spread plus two fees: 3.7–4.4 % of a ~$63 LEAPS mid ≈ $2.4–2.8 a contract, i.e. ~0.5 of the normalised premium. Rolling at 90 avoids 0.81 of decay per cycle at a cost of ~0.5, but needs ~10 % more rolls a year: within ±0.3 % of spot a cycle, immaterial against the 0.70-delta exposure itself.

### Inferences
- The friction assumption "3 % ETF / 8 % single" used in §3 is conservative for the ETFs (real 1.0–1.2 %) and about right for single names at the swing band; at 8–14 DTE on single names it is too kind (8.5 % median).
- OI ≥ 500 is a reasonable floor for monthly and the main weekly expiries; applied to every daily-listed expiry it will reject most of them. The picker should fall back to the nearest expiry that has a qualifying contract rather than the nearest expiry alone.

### Gaps
- Five days of chains only (2026-10-06…10-12); the shares will move with the calendar (a monthly expiry in the window lifts the OI share). The spread by delta/DTE is a snapshot, not a history.

---

## 7. The earnings gate

### Takeaway
Earnings sessions move the names 2.4–5.5× a normal session (medians 2.5 % AAPL to 12.1 % PLTR against 0.9–3.0 %), so the gate is a variance rule; **on the underlying, the swing entries that crossed an earnings date did not do worse** (SEQ5_12 swing rules: +0.9 % vs −3.0 % in train, +2.0 % vs −2.9 % in check; fixed 20 sessions −0.2 % vs −0.6 % and −2.7 % vs −0.6 %), and the gate removes about a quarter of the entries. The option-side cost (IV crush, the wider spreads retail pays before announcements) is documented in the literature but not testable here.

### Cited Findings (computed; `06_earnings.py`, `earnings_moves.csv`; UW quarterly rows with a report date and pre/post-market time, 1,515 rows for the 16 reporting names, 1996-03-14 → 2026-11-18 — far more than one year; the move is the first session to trade on the report)
- Median |close-to-close| on earnings sessions vs other sessions, 2020-01 → 2026-10: AAPL 2.50 % vs 0.93 % (N 28 / 1,676), AMD 6.27 vs 1.90, AMZN 6.83 vs 1.21, AVGO 4.80 vs 1.36, GME 10.2 vs 2.36, GOOGL 4.96 vs 1.06, INTC 8.13 vs 1.46, META 8.25 vs 1.19, MSFT 3.07 vs 0.96, MSTR 4.56 vs 2.95, MU 4.83 vs 1.79, NVDA 4.01 vs 1.80, ORCL 6.67 vs 1.07, PLTR 12.1 vs 2.08, SOFI 6.57 vs 2.41, TSLA 6.65 vs 2.07. 90th percentiles 7.1 % (AAPL) to 29.8 % (GME). (META's *mean* earnings move is inflated by one anomalous bar in the vendor file; the medians are unaffected.) The ETFs have no earnings.
- SEQ5_12 swing with the spec's exits: crossing an earnings session N 29 train (+0.91 %, hit 41 %, sd 22 %) vs not crossing N 76 (−3.04 %, hit 39 %, sd 15 %); check 14 (+1.97 %) vs 46 (−2.85 %). Fixed 20-session hold: train −0.23 % vs −0.57 %; check −2.71 % vs −0.58 %. Weekly fixed 5: train −1.38 % (N 15) vs +0.06 % (90); check −0.51 % (4) vs −0.25 % (67). LEAPS fixed 63 (almost every 63-session hold crosses one): +9.2 % (83) vs −2.6 % (22) train; +4.3 % (35) vs −1.8 % (16) check.
- All name-days, fixed 10: train crossing +7.6 % (N 1,910; contaminated by the same META bar, sd 83 %) vs +0.76 %; check +1.30 % (N 1,119) vs +1.25 %.
- Literature: retail option buyers concentrate purchases before announcements and lose 5–9 % on average, 10–14 % around high-expected-volatility announcements, with spreads around 20 % of the option price ([de Silva, Smith & So, Review of Finance 2025, summary](https://quantpedia.com/how-retail-losses-money-in-option-trading/); [Stanford GSB listing](https://www.gsb.stanford.edu/faculty-research/publications/losing-optional-retail-option-trading-expected-announcement)). The stock side has an announcement *premium*: Frazzini and Lamont estimate it at over 7 % a year and tie it to small-investor buying ([NBER w13090](https://www.nber.org/papers/w13090)); Barber, De George, Lehavy and Trueman find it in 46 countries, significant in 9 of 20 with enough data, strongest where idiosyncratic volatility rises most around the announcement ([JFE 2013](https://ideas.repec.org/a/eee/jfinec/v108y2013i1p118-138.html)). Pre-earnings straddles earn positive returns on average because traders under-estimate announcement volatility after quiet periods ([Chung & Louis, J. Empirical Finance 2017](https://ideas.repec.org/a/eee/empfin/v40y2017icp220-235.html)); weekly straddle returns are higher when the historical move is large relative to the implied one ([Milian 2023](https://ideas.repec.org/a/gam/jjrfmx/v16y2023i5p270-d1145938.html)).

### Inferences
- For a long directional option, crossing earnings buys a big move at a high vol: the underlying's EV is not hurt (the announcement premium runs the other way), but the premium paid up front and the IV crush after are option-side costs this data cannot price. The gate is defensible as a *risk* rule (it caps the per-trade loss distribution) and should not be presented as an EV rule.

### Gaps
- Option paths across earnings (the pre-announcement IV and the crush) are not on disk; the vendor's N = 35 ledger cannot speak to it either.

---

## 8. Literature: what the published evidence says and what survives costs

### Takeaway
Momentum is a 3–12-month phenomenon; at 1–4 weeks the published sign is *reversal*, so a one-to-four-week long after a pullback is trading against the documented short-horizon effect and only with the intermediate trend. Abnormal volume does predict a higher next-month return, which is the only published support for B3, and it is a monthly effect. Buying out-of-the-money calls has negative expected returns that worsen with strike; delta 0.40–0.55 is the least-bad part of the curve. Nothing published supports the OTE zone as a level that behaves differently from any other.

### Cited Findings
- Momentum: strategies that buy past winners and sell past losers "generate significant positive returns over three- to twelve-month holding periods", with part of the first-year abnormal return dissipating over the next two years — [Jegadeesh & Titman 1993, J. Finance (abstract)](https://ideas.repec.org/a/bla/jfinan/v48y1993i1p65-91.html).
- Short-horizon reversal: one-week winners and losers show "sizeable return reversals over the subsequent week" that "persist after corrections for … bid-ask spreads and for plausible levels of transactions costs" — [Lehmann 1990, NBER w2533 (abstract)](https://www.nber.org/papers/w2533); Jegadeesh (1990) reports about 2 % a month from prior-month reversal over 1965–1989 (secondary summary, [Alpha Architect](https://alphaarchitect.com/quantitative-momentum-research-short-term-return-reversal/)); Lo and MacKinlay attribute much of it to delayed reaction to common factors (secondary, [PDR](https://pide.org.pk/research/momentum-effect-empirical-evidence-from-karachi-stock-exchange-2/)).
- Volume: "stocks experiencing unusually high (low) trading volume over a period of one day to a week tend to appreciate (depreciate) over the course of the following month … even stronger when the unusually high or low trading activity is not accompanied by extreme returns" — [Gervais, Kaniel & Mingelgrin, Wharton WP 001-99 (abstract)](https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2014/04/9901.pdf), published J. Finance 2001 ([author page](https://sites.duke.edu/sgervais/?p=64)). Volume also predicts the *persistence* of momentum: high-volume winners reverse faster — [Lee & Swaminathan 2000 (abstract)](https://academicnewsletter.sufe.edu.cn/info/361612).
- Costs: transaction costs reduce every anomaly's profitability and significance; strategies with one-sided monthly turnover under 50 % keep significant net spreads when designed to limit costs, and a buy/hold spread (stricter entry than exit) is the single most effective mitigation — [Novy-Marx & Velikov 2016, RFS (NBER w20721)](https://www.nber.org/papers/w20721). Short-term reversal is the anomaly most constrained by trading costs in live data (Frazzini, Israel & Moskowitz, cited in the same search; not fetched).
- Option returns by moneyness: out-of-the-money call returns decline with strike, with a turning point near the money (Bakshi, Madan & Panayotov, JFE 2010, via [CXO summary](https://www.cxoadvisory.com/?p=13232)); portfolios sorted on ex-ante skewness differ by 10–50 % a week in average option returns, lottery-like features concentrated in OTM options near expiration — [Boyer & Vorkink 2014, J. Finance](https://ideas.repec.org/a/bla/jfinan/v69y2014i4p1485-1527.html); equal-weighted delta-neutral straddles on individual names lost about 17 % a month 1996–2010 (Xing & Zhang, via [CXO](https://www.cxoadvisory.com/?p=22707)).
- Fibonacci/OTE: price bounces are more likely in Fibonacci zones, but "price behavior on Fibonacci and non-Fibonacci zones did not differ statistically" (Expert Systems with Applications 2021, [highlights](https://www.datalearner.com/academic/journal-papers/0957-4174/volumes-and-issues/391/paper-detail/17703)); a Fibonacci strategy beat buy-and-hold on energy stocks 2017–2020 in one study ([Gurrib et al., Financial Innovation 2022](https://jfin-swufe.springeropen.com/articles/10.1186/s40854-021-00311-8)); a student backtest on Vanguard ETFs found it unprofitable ([HKUST project](https://cse.hkust.edu.hk/~rossiter/independent_studies_projects/fibonacci_trading/fibonacci_trading.pdf)). No peer-reviewed support for 0.62–0.705 specifically.
- LEAPS vs stock replacement: only practitioner material found (a 0.80-delta target, "roll before the final 90 days", theta of a few cents a day on a deep ITM LEAPS — [tapeboard](https://tapeboard.com/blog/glossary-what-is-a-leap-option), [BIT](https://www.bit.com/knowledge-hub/leaps-call)); no independent backtest of the rolling cost exists in the results.

### Inferences
- What survives costs in the literature is intermediate momentum at low turnover and the earnings premium on the stock side; a one-to-four-week long call after a 62–70 % give-back is a high-turnover, negative-skew-premium trade sitting on top of the short-horizon reversal effect. The computed results in §1–3 are what that combination should look like.

### Gaps
- No full texts were read for Jegadeesh (1990), Bakshi–Madan–Panayotov or Xing–Zhang; their figures above are from abstracts or secondary summaries and are marked so.

---

## 9. No invented weights: the logistic regression against the strict gate

### Takeaway
A logistic regression of "forward return > 0" on the booleans, fitted 2022–2024, has out-of-sample AUC 0.507–0.508 (no better than a coin) and coefficients of the wrong sign on B2 (−0.29 at H5); it does not beat the AND gate out of sample because neither has anything to beat. **Recommendation: no weights — keep the strict boolean gate as the engine's form, but do not claim it selects for return.**

### Cited Findings (computed; `09_logistic.py`, train 2022–2024 N 16,721 name-days, check 2025–2026 N ≈ 10,000)
- Three booleans, H5: coefficients B1 +0.02, B2 −0.29, B3 −0.005; at the gate's own selectivity (top-5 by probability in check) the logit picks mean +2.0 % vs the gate's −5.2 % — five trades, noise. H10: B1 −0.06, B2 −0.21, B3 +0.02; H20: −0.03, −0.05, −0.03.
- Seven booleans (adding the alternatives) and booleans + continuous features (log relative volume, the retracement, RSI): coefficients all within ±0.3, the continuous model's top-k in check at H10 −0.46 % … +0.59 % depending on k — unstable.
- Out-of-sample AUC: logit 0.507 / 0.508 / 0.508 at H5/10/20; B1 0.501/0.509/0.505; B2 0.494/0.489/0.489; B3 0.498/0.504/0.500; the gate 0.500.

### Inferences
- With no boolean carrying information, any fitted weight is noise and would be an invented weight by another name. The guardrail is satisfied by keeping the gate strict; the honest statement is that the gate is a *description* of a setup, not a *predictor*.

---

## 10. Modules 15–16 and Helix: what the code review must check (no data test)

**Cents normalization (Module 15).** The review must find exactly one boundary where vendor prices enter and are converted to one unit, and nothing downstream that re-converts. UW returns prices as numeric strings in dollars (the data lake stores them as strings; `num()` reads them), ThetaData's bulk files carry `strike` as a string in dollars and `bid`/`ask` as strings, and the house's own book is in dollars to the cent (CLAUDE.md, `core/format.ts`). A schema test should assert, for every engine input (spot, strike, bid, ask, mid, premium, target, stop, the expected move), the unit and the scale at the boundary (a strike of "808.0" is dollars, never 808000 mils; a premium of "0.56" is dollars a share, the contract is ×100), and a round-trip test should feed one known contract (e.g. SPY 20261030 808 C at bid 0.55 / ask 0.56 on 2026-10-09 from the bulk file) through the picker, the stop, the scale-out tiers and the P&L and check each figure to the cent. Any `/100`, `*100`, `Math.round(x*100)` outside that boundary is a finding.

**Dead-code quarantine (Module 16).** The review must list by name every cap and floor removed and prove nothing reads them: the old premium caps and floors on a contract's price, the delta floors/ceilings that pre-date the 0.35–0.50 / 0.40–0.55 / 0.60–0.80 bands, the OI floor's old value if it differed from 500, any minimum-DTE or maximum-DTE constant that the 4–7 / 8–28 / 90–365+ windows replace, and any score, grade or weight constant left from a scored version of the gate (the spec says no weights; a leftover `weight`, `score`, `confluence` or `grade` constant that is still imported is a finding — those words are also banned on screen by `npm run words:check`). The test is static: the removed symbols must not resolve anywhere (`tsc` with the exports deleted, plus a grep for their names and their literal values), and the engine's output on a fixed replay day must be byte-identical before and after the quarantine except where a removed cap used to bind, with each such difference listed.

**Helix isolation (telemetry only).** Helix fields may be written by the engine and read by the UI and the logs, and must never be read by a decision. The review must enumerate the Helix fields and check (a) that the gate's four booleans, the picker, the stops, the scale-outs and the sizing are pure functions of the market inputs and the config with no Helix argument; (b) that the Helix module has no export consumed by the decision path (an import graph check: nothing under the engine's decision modules imports Helix); (c) that disabling Helix (its fields null) leaves the engine's decisions on a fixed replay day identical; and (d) that Helix writes to its own log/telemetry sink, never to the alert store, the paper engine's orders or the Journal's trade records. The same applies to any "Physics"/"Nerve" telemetry the spec says has no weights: isolated or boolean, never a score.

---

## Verdicts and replacement rules, module by module

| Rule | Spec | Test (data, N, split) | Numbers | Verdict |
|---|---|---|---|---|
| B1 trend | daily + weekly alignment | 23 names 2022–24 / 2025–26, N 6,933 / 4,440 | below the unconditional baseline in train (+0.49 % vs +1.55 % at H10), equal in check; AUC 0.50–0.51 | **Keep as a boolean, no weight; it is a filter of style, not of return.** Code: `close > EMA21 && close > EMA50 && lastCompletedWeekClose > EMA10w`. |
| B2 OTE pullback | 0.62–0.705 retracement | N 872 / 626 | −0.41 % (t −1.6) / +0.11 % at H5; AUC 0.49 | **Keep only as a description; it has no positive evidence at 1–20 sessions.** Code: impulse on closes over 30 sessions, ≥ 2 ATR, high ≥ 2 sessions old; `low ≤ hi − 0.62·(hi−lo) && close ≥ hi − 0.705·(hi−lo)`. If the engine needs entries, read it as "within the last 5 sessions" (SEQ5), which is declared here, not tuned. |
| B3 volume | rvol ≥ norm | N 1,634 / 1,003 | +1.53 % / +0.55 % at H5, +0.36 % / +0.42 % without the best 5 trades; literature supports a monthly high-volume premium | **Keep at 1.5× the 20-day mean (1.2× for the sequenced reading); say that its support is a one-month effect.** |
| B4 dealer book | wall within 1 EM, stop beyond the wall | untestable before 2025-10-15; sign proxy N 38 / 6 | negative-gamma days returned more unconditionally (H20 +2.54 % vs +1.83 %) | **Untestable; run the engine with B4 off and label it; blocker = strike-level book history.** |
| The AND gate | all four true | same-day N 14 / 6; sequenced N 105 / 71 | worse than count-matched random with the spec's exits (p 1.000 / 0.995) | **Strict gate, no weights, no return claim. N > 500 is not reachable with these booleans on this universe.** |
| Level stop | prior-day/week low, 2.4–4.6 %, median 3.45 % | SEQ5_12 swing N 105 / 60 | prior-week low is a median 8.25 % away after an OTE entry; a fixed 3.45 % stop is hit on 74–78 % of trades | **Change: state the stop as a distance, not a level, and size it to the entry's depth; neither version is positive.** |
| Premium backstop −20 % / −17 % | | BSM at 7 / 14 / 30 DTE | fires on decay alone within 3 sessions at ≤ 14 DTE; always before the level stop | **Change: ≥ 45 % at 7 DTE, ≥ 25 % at 14 DTE, or drop it below 21 DTE and keep the level stop only.** |
| 3-day stall (8–13 DTE) | out if not up after 3 sessions | N 105 / 60 | −1.95 % → −1.37 % train, −1.72 % → −0.74 % check; 46 / 31 trades out at −3 % | **Keep as a loss-limiter; it does not make the trade positive.** |
| Scale-outs 25 % / 50 % | | option model, 4 and 2 contracts | hit 11 % → 18–28 %, mean −17 % → −12 … −16 % | **Keep as sizing-conditional (needs ≥ 4 contracts; 2 contracts run the 50 % tier only; 1 contract has no ladder).** |
| Trail lock, RSI(14) exit | | option model | within ±2 points of the plain stop | **Keep or drop at the owner's taste; no evidence either way.** |
| LEAPS (0.60–0.80 Δ, roll < 60 DTE, −25 % stop, 33/33 scale) | | SEQ5_12 N 105 / 51; BSM roll model | hold +15 % train (five trades) / −4 % check; −25 % stop +1.7 % / −13 %; roll at 90 vs 60 within ±0.3 % of spot a cycle | **Keep the band and the roll rule as written (immaterial); the stop and the ladder do not add EV; the entry gate adds nothing over buying the name.** |
| Picker: Weekly 0.35–0.50, Swing 0.40–0.55 + OI ≥ 500, LEAPS 0.60–0.80 | | 5 bulk days, 23 names | ETF spreads 1.0–1.2 %, single 5.1–5.3 % (8.5 % at 8–14 DTE); OI ≥ 500 present in ~half of the 8–28 DTE expiries | **Keep the bands; change the OI rule to "nearest expiry with a qualifying contract", and prefer 15–28 DTE over 8–14 on single names (half the spread).** |
| Earnings gate | no swing across a report | 16 names, 1,515 reports; SEQ5_12 N 29 vs 76 / 14 vs 46 | earnings sessions 2.4–5.5× a normal move; crossing did not lower the underlying EV; removes ~25 % of entries | **Keep as a risk rule; never present it as EV.** |
| Helix, cents, dead code | | code review | — | §10 checklist. |

**The one sentence for the owner.** On 23 liquid names over 2022–2026, the four-boolean swing engine as specified fires 20 times, loses on the underlying and loses more as options at every tenor after spreads and fees, and does not beat a random day with the same exits; no fitted weight rescues it, so the honest build is the strict boolean gate labelled as a setup description with B4 marked untestable until a year of strike-level book history exists.
