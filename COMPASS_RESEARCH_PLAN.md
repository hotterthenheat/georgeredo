# Compass research plan (version 1, 2026-10-13)

No Compass research plan existed in this repository, so this is the initial plan, written from the verified findings of the 2026-10-13 reproduction audit (`audit/phase1/`) and the full-history investigation (`research/georgefi_full_history/`). It supersedes nothing; it tells Compass which hypotheses are closed, which are open, and what any lane must pass before promotion. Earlier deliverables are preserved unchanged; corrections live in dated errata sections.

## 1. Rules that apply to every lane

**Promotion criteria (all required).**
1. Expectancy under the *spread* cost model (half-spread 1 % SPY/QQQ, 1.5 % SPX-class, 2 % IWM/single names, plus $0.70 per side) has a lower 95 % bootstrap bound above zero, with the bootstrap clustered by trading day.
2. The same holds out of sample on a window fixed before the test (no re-tuning on it), with at least 150 trades spanning at least 3 months, and the lane beats its random-entry baseline by more than one round-trip cost; the baseline must be drawn at least five times from a committed list of contract-days, never from a cache listing.
3. Fills are validated against captured NBBO, not bar VWAP or mid; a lane whose edge disappears under the *adverse* fill model is not promotable.
4. A look-ahead audit is on file (levels from the prior session, entries on the next bar, regime inputs stamped as-of) and every input used at decision time is retrievable historically on our entitlements.
5. The run is reproducible from committed artifacts: fixed seeds, sorted iteration, result directories versioned (`results/v1`, `v2`, …), raw data hashed.

**Never promote on**: mid-price-only profit, confidence intervals that include zero, reported (operator) P&L, in-sample results alone, fewer than 150 trades, or any result that cannot be reproduced from the repository plus a documented data pull.

**Preservation rules.** Raw exports are immutable and indexed with SHA-256 (`research/georgefi_full_history/raw/*/_index.jsonl`); normalized tables are derived in separate folders; prior findings are never rewritten (errata sections only); every reproduction audit is kept (`audit/`); heavy caches stay out of git but their fetch scripts are committed.

**Separation rule.** GeorgeFi's history is evidence about GeorgeFi's record, not about Compass hypotheses. A GeorgeFi number may motivate a hypothesis; it never counts toward promoting one.

## 2. What is verified (the evidence base)

| Item | Status after audit | Where |
|---|---|---|
| GeorgeFi-style backtest, 144 variants | Reproduced byte-for-byte from the warm cache; live API matched the cache 30/30 | `audit/phase1/backtest_reproduction.md` |
| Validation tests T1–T7 | T1–T4, T6 exact; T5 point estimates exact, CIs made deterministic (v2 file); T7 recomputed, two wording errata | `audit/phase1/validation_reproduction.md`, `GEORGEFI_SIGNAL_RESEARCH.md` errata |
| Short-vol/session and flow-predictor studies | Reproduced byte-for-byte | `audit/phase1/research_reproduction.md` |
| GEX-regime/exit-grid study | Reproduced exactly given the committed random control set; the control draw itself was cache-dependent (see report errata) | same, follow-up section |
| GeorgeFi history on the account | 1,149 ledger trades (Epoch 1: 546, 2026-01-20→02-27; Epoch 2: 489 main + 114 side-book, 2026-03-02→10-13) + 84 SPX paper trades; two retrieval routes agree id-for-id; sums reconcile to the epoch totals | `research/georgefi_full_history/HISTORY_EXTENT.md` |
| Independent bars for that history | 1,229 of 1,233 rows have entry-day UW contract bars (missing: 4 plain-SPX-root rows) | `research/georgefi_full_history/results/RESULTS.md` §0 |
| Provider entitlements (live, 2026-10-13) | UW: contract bars from 2025-04-01, stock bars from 2022-09-28, concurrency 3, index bars 422 | `research/georgefi_full_history/provider_audit_2026-10-13.md` |

## 3. GeorgeFi's record, as it stands after independent pricing (closed questions)

- **Epoch 1 (+$43,248, 78.8 % win rate, "+540 % ROI") is not an independently supported result.** On the 452 trades with a print in both the entry and exit minute, reported +$36,729 becomes +$21,567 at bar VWAP, +$7,914 after spread and fees (+$17.5 per trade, 95 % CI [−3.6, 36.9]) and −$24,279 under adverse fills. Only 45.4 % of Epoch 1 entry premiums lie inside the traded range of their minute; 382 of 546 rows are same-contract-same-minute repeats that carry 95 % of the P&L; the single largest trade (+$4,020) is priced below the range its SPXW twin printed. (`RESULTS.md` §B, §D)
- **Epoch 2 (main book +$3,974) is indistinguishable from zero and negative after costs** (+$8.1 per trade [−11.1, 29.1] reported; −$3,098 at VWAP; −$14,913 with spread on 501 covered trades), consistent with the earlier T1–T4 finding.
- **Entry timing carries no robust information in either epoch.** From the reported entry minute with the paper-lane trail engine, Epoch 1 is +$5.8 per contract after spread [−5.7, 16.3] and Epoch 2 +$2.3 [−10.5, 14.9]; the MFE percentile against time-matched random minutes is 53 [cluster CI 47.5, 59.2] in Epoch 1 and 48 in Epoch 2. (`RESULTS.md` §C)
- **The reconstructed strategy description does not produce the live entries** (7–9 % coincidence) and, when backtested, 0 of 144 variants are positive after costs (`BACKTEST_RESULTS.md`).
- **The SPX paper book** (84 trades) is −$3,632 reported and −$6,217 after spread at the operator's own times.

Consequence for Compass: no lane may be justified by GeorgeFi's performance, and no "copy GeorgeFi's signals" lane is admissible.

## 4. Hypothesis register

| # | Hypothesis / lane | Verdict | Deciding evidence | Compass action |
|---|---|---|---|---|
| H1 | Level-sweep reversal / continuation into ATM 0DTE (GeorgeFi family) | **Closed, rejected** | 0/144 variants positive after costs; best −$2.4 vs random −$3.2 | Keep as a measured paper book only; no promotion path |
| H2 | Flow-following entries (net premium, net delta, market tide, dark-pool imbalance) | **Closed, rejected** | 0/62 cells survive correction; ICs ≤ 0.02 forward vs 0.5–0.67 trailing | Display-only; never an entry trigger |
| H3 | Per-strike burst ("sus strike") entries | **Closed, rejected** | burst contracts −6 to −8 % net vs −4 to −6 % random | Display-only |
| H4 | Dealer gamma regime as a direction filter | **Closed, rejected** | POS−NEG slope +0.03 [−0.12, +0.19]; sign flips IS→OOS | Not a filter |
| H5 | Intraday gamma as a volatility gauge (size/stop width) | **Open, tool not lane** | IC −0.21 vs absolute 30-min move; partial −0.17 | Build as a risk input; validate that it improves a lane's drawdown before relying on it |
| H6 | Wall / magnet pin fades | **Closed, rejected** | indistinguishable from distance-matched random levels | None |
| H7 | Exit-engine improvements alone | **Closed, not promotable** | 0/576 positive after costs on strategy entries and on both random draws; gross ceiling ≈ 1.5 % of premium vs 3–6 % cost | Keep trail engine as the default risk layer; stop searching exits for alpha |
| H8 | Session plays in options (ORB, gap fill, half-hour seasonality, 15:00 momentum) | **Closed, rejected** | every option expression negative; underlying effects null | None |
| H9 | 13:00 short ATM straddle, SPY/QQQ, close 15:55 | **Closed, rejected at measured NBBO (§8)** | +$16.7 mid [5.4, 27.7]; +$8.4 after spread [−3.2, 19.5]; two tail days exceed 16 months of income | Pre-registered test T-A below; prerequisite NBBO capture |
| H10 | Gamma-conditioned last-half-hour momentum, in shares/futures | **Closed, rejected (§8)** | peer-reviewed effect only on negative-gamma days; our option test underpowered (1,016 ticker-days) | Pre-registered test T-B on SPY shares back to 2022-09-28 |
| H11 | SPXW contracts (larger premium, lower proportional cost) for short premium | **Closed on the pre-registered design; one post-hoc variant to pre-register (§8)** | index bars unavailable (422); SPXW contract bars and the spot-exposures `price` series are available | Test T-C using contract bars plus the per-minute `price` field as the index proxy |
| H12 | GeorgeFi's committed-read inputs (five-contributor vote, bursts, accelerator) time entries | **Open, blocked** | needs weeks of member-surface collection; subscription lapses 2026-10-14 | Only if the user renews the subscription; otherwise closed by default |

## 5. Pre-registered next tests (in order)

- **T-A, short straddle paper lane.** Entry 13:00 ET, SPY and QQQ, ATM, close 15:55, no intraday stop (2.0× credit stop as a variant), skip FOMC/CPI/NFP days, 1 lot. Pass: spread-model lower bound > 0 over ≥ 150 straddle-days and ≥ 3 months, and the realized half-spread from NBBO capture ≤ 1.5 % of credit. Data: UW `option_trades` websocket NBBO capture for the two ATM contracts each afternoon (start now; a 3-request concurrency cap applies to REST, not the socket).
- **T-B, underlying momentum.** SPY shares, 2022-09-28 → today (UW 1-min bars), last-30-minute return signed by the 09:30–15:30 return, conditioned on prior-day gamma sign (`gex-levels`, dated T−1). Pass: net Sharpe > 1.0 on negative-gamma days with ≥ 300 days, zero effect on positive-gamma days, costs 0.2 bp per side.
- **T-C, SPXW short premium.** Same design as T-A on SPXW using contract bars and the `spot-exposures` price series; pass criteria as T-A with 1.5 % half-spread.
- **T-D, spread calibration.** Use the undocumented `stock/{t}/option-contracts?date=` daily chain (bid/ask included) to replace the assumed half-spreads with observed daily NBBO widths for every contract-day in the backtests; re-run `backtest/` and the straddle study with the calibrated costs before any promotion decision.

## 6. Infrastructure prerequisites

1. NBBO capture service (websocket) with its own hashed raw store.
2. Random baselines drawn from a committed contract-day list, five draws, reported with their spread.
3. Day-clustered bootstrap in every report; cluster by date and by contract-minute where repeats exist.
4. A `results/vN` convention and a reproduction run before any status change in this register.

## 7. Items that require the user's decision

- Renew or let lapse the GeorgeFi subscription (needed only for H12).
- Rotate the Unusual Whales and ThetaData keys and change the GeorgeFi password that were shared in chat.
- Whether to create a `main` branch and open a pull request; all work is on `claude/lucid-heisenberg-bpyq7k` in dedicated directories because this session is pinned to that branch.

## 8. Update, 2026-10-13 evening: results with measured quotes (ThetaData PRO)

The user supplied a ThetaData key (PRO on options, stocks and indices; `research/thetadata/provider_audit.md`). It removed the two data blockers named in §6 and §7 (executable spreads, index minute prices), so the three pre-registered tests were run at measured NBBO. Every number below is day-clustered; details and code in `research/thetadata/`.

| Test | Pre-registered gate | Result at measured NBBO | Verdict |
|---|---|---|---|
| T-A 13:00 short ATM straddle, SPY+QQQ (n = 678, 17 months) | lower 95 % bound > 0; round-trip cost ≤ 1.5 % of credit; beats random by > 1 round trip | +$8.60 per straddle [−6.07, 22.45]; realized round trip 3.9 % of credit (entry half-spread 0.6 %, but buying back near-worthless legs at 15:55 costs 5–6 % of leg value); vs random +$13.10 [−2.42, 29.14] against a $12.93 cost; IWM −$9.50 [−18.69, −0.44]; every other entry time negative | **FAIL**; the modelled-spread result (+$8.36) was optimistic by about $5 per straddle |
| T-B gamma-conditioned last-30-minute momentum, SPY shares (598 gamma-known days 2024-05-14 → 2026-10-09; 2,332 days unconditional 2017 →) | net Sharpe > 1.0 on negative-gamma days (≥ 300), ≈ 0 on positive | negative-gamma days −3.07 bp/day [−5.73, −0.52], Sharpe −2.15 (SPY-proxy); slope of last-30 on rest-of-day −1.4 ×100 [−7.6, 4.8] vs the published +6.6; the two gamma proxies agree on the regime only 52 % of days; unconditional 2017–2026 Sharpe 0.14 cost-free | **FAIL** (wrong sign) |
| T-C 13:00 SPXW short straddle, close 15:55 (339 sessions) | as T-A with 1.5 % half-spread, $1/contract/side | +$72.4 per day [−75.8, 214.2], PF 1.16, max drawdown −$21,180, worst day −$8,499; entry half-spread 0.87 % of credit (passes); vs random +$40.6 [−73.4, 164.2] against a $68.9 cost | **FAIL** on the pre-registered design |

Post-hoc observation, not a result: holding the SPXW straddle to the 16:00 cash settlement instead of buying it back (no exit spread) gives +$156.8 per day [+5.8, +305.0] over all 339 sessions, but [−18.5, +288.6] once FOMC/CPI/NFP days are excluded, and it was not pre-registered. It is logged as hypothesis **H13** below and may only be promoted through a new pre-registered test on data not used here.

**GeorgeFi's record at the NBBO (`research/georgefi_full_history/results/RESULTS_NBBO.md`).** With quotes at the reported second (99 % coverage): 58 % of Epoch 1 trades were filled better than the market offered on at least one side; repricing at ask-in/bid-out cuts the covered Epoch 1 record from $39,297 to $12,039 (+$22 per trade, day-clustered CI [−11, 66]) and Epoch 2 from −$3,294 to −$24,988; among the 382 same-minute repeats, 27 % are priced below the lowest bid of their minute. Realized half-spreads: SPY/QQQ 0.5 % of mid, SPXW 0.9 %, IWM 0.7–0.9 %, RUTW 4.5 %, NDXP 7.5 %, single names 3.5–4 %. The §3 verdicts stand and are now based on measured, not modelled, costs.

**Register changes.** H9, H10 closed (rejected). H11 closed on its pre-registered form. New:

| # | Hypothesis | Status | Pre-registered test |
|---|---|---|---|
| H13 | SPXW 13:00 short ATM straddle held to PM settlement, event days excluded | Open, candidate | **T-E**: window 2022-01-03 → 2025-05-29 (ThetaData, never used here), same entry rule, FOMC/CPI/NFP exclusion fixed in advance, settlement at the 16:00 SPX print, $1/contract/side, margin and tail sizing stated before the run; pass = lower 95 % day-clustered bound > 0 with ≥ 500 days, and the 2025-06 → 2026-10 window then treated as the holdout, not re-used for selection |
| H14 | Exit-side spread engineering for short premium (leave near-worthless legs to expire, or buy back only when the ask ≤ $0.05) | Open, mechanical | **T-F**: re-run T-A with the rule fixed in advance on the same 339 sessions; pass criteria as T-A; this addresses the 3.9 % round trip directly and is cheap |

**Infrastructure notes from this round.** ThetaData enforces one live login per key (a second process invalidates the first; run one fetch process per key). Cost assumptions in `backtest/costs.py` should be replaced by measured half-spreads per root (0.5 % SPY/QQQ, 0.9 % SPXW, 4.5 % RUTW, 7.5 % NDXP, 3.5–4 % single names) before any further option backtest; the T-D calibration step in §5 is therefore done by measurement rather than by the daily chain.

## 9. Update, 2026-10-14: round 2 on the full ThetaData chain dataset

Question asked: can a lane reach a 70 %+ win rate without negative expectancy? Evidence: three literature notes, an SPX intraday-volatility filter study (2017–2026), and two pre-registered grids on the complete same-day chain dataset (`research/thetadata/dataset/`: SPY/QQQ 980 sessions from 2022-11-11, SPXW 1,106 from 2022-05-13, IWM 621 from 2024-04-19; 1-minute NBBO; 80.2 million rows). Report: `reports/High win rate 0DTE lanes.md`; notes in `research_notes/High win rate 0DTE lanes/`; code and pre-registrations in `research/thetadata/hwr_grid/{etf,spxw}/` and `research/thetadata/vol_filters/`.

**Verdicts**

| Item | Result (TEST = 2025-01-02 → 2026-10-09 unless noted; day-clustered 95 % CIs; bid/ask fills) | Verdict |
|---|---|---|
| T-E / H13: 13:00 SPXW ATM straddle held to settlement, FOMC/CPI/NFP excluded, 2022-05-13 → 2025-05-29 | +$26.37 per day [−138.17, +169.77], win 61.5 %, PF 1.05, max drawdown −$41.4k, worst day 2025-04-09 −$33.7k; holdout +$152.93 [+1.91, +294.08] but it is the window H13 was found in and the lane trails random entry in both windows | **FAIL; H13 closed** |
| ETF grid (SPY/QQQ/IWM, 1,890 distinct configs per scope) | median config wins 71–73 % with negative mean; no TRAIN-selected config meets both ≥ 70 % TEST win rate and the full gate; SPY k = 0.5 strangle held to expiry wins 76.3 % with +$20.69 [+12.19, +29.03] but fails the random-baseline item; hold-to-expiry gains on SPY/QQQ are mostly the after-hours exercise premium (SPY S1 re-valued at 17:15: +$23.59 rational, +$2.58 [−10.03, +15.13] pessimistic) | **FAIL** |
| SPXW grid (2,736 distinct configs) | S2 (14:05 strangle at ±0.5 × expected move, hold to settlement, skip FOMC and month-end) TEST win 71.5 %, +$162.0 [+63.2, +258.4], n = 397, but lane − random entry −$92.8 [−184.5, +1.1]; the ±2 % storage band skipped the worst days for 13:00 entries | **FAIL** (premium is generic, timing adds nothing) |
| H14 exit-side rule (leave legs with ask ≤ $0.05 ETF / ≤ $0.10 SPXW to expire) | +$0.3 (ETF) and +$2.7 (SPXW) per trade in TRAIN and TEST | **Adopt as an execution rule; not a lane** |
| Take-profits (25 %/50 %) | win rate +5 to +17 points, mean −$5.6 to −$45 per trade | **Reject as an expectancy tool** (they buy win rate with expectancy) |
| Stops (1×/2× credit) | win rate −4 to −13 points; mean flat in TRAIN, negative in TEST | **Risk tool only** |
| Filters | skip FOMC and skip month-end are the only rules positive under both yardsticks (SPX study) and in both grid periods; VIX, morning-range, CPI/NFP/opex and weekday skips hurt out of sample | **Keep FOMC + month-end skip as the default filter** |
| Sizing | configs with positive TEST bounds need about $73–89k of capital per SPXW lot at quarter-Kelly or an 8 % max-loss budget; the TEST window lacks the band-skipped tail days, so this is optimistic | **Size by max-loss budget, never by win rate** |

**What "70 %+ win rate" means on this evidence.** A 70 %+ win rate is a property of the payoff shape and of take-profit rules, not of skill: the median configuration already wins 71–73 % while losing money. The only configurations with positive cost-realistic bounds are naked short premium held to settlement/expiry entered in the afternoon, they win 59–76 %, they carry single-day losses of $30k+ per SPXW lot (2025-04-09), and none of them beats a random entry time by more than one round trip. The data therefore supports a *volatility-risk-premium harvesting* lane with strict tail sizing, not a high-win-rate signal.

**Register changes.** H13 closed (rejected). H14 adopted as an execution rule. New candidate:

| # | Hypothesis | Status | Test |
|---|---|---|---|
| H15 | Afternoon (14:05) SPXW short strangle at ±0.5 × the 14:05 expected move, held to cash settlement, skip FOMC and month-end days, sized at ≤ 8 % max-loss budget with a stress move ≥ 8.5 % of SPX | Open; all historical data has now been used for selection | **T-G: forward paper only** from 2026-10-14, ≥ 150 sessions and ≥ 6 months, NBBO fills logged live, gate as §1 including the random-time baseline computed on the same days; no further historical re-selection allowed |

**Data notes.** The chain dataset stores strikes within ±2 % of the 09:31 price; trades whose strikes fell outside that band were skipped and counted, which removes some of the largest-move days (documented in both grid notes). Option OHLC was only partially fetched (about 3 minutes per session; resumable with `research/thetadata/dataset/fetch.py ohlc`); no test depends on it.

**Decision needed from the user (raised by round 2).** The §1 gate requires every lane to beat its random-entry baseline by more than one round trip. A premium-harvesting ("carry") lane makes no timing claim, so a version defined as "sell at any minute 10:00–14:30" cannot pass that item in principle, and S2 failed it (lane − random −$92.8). Either (a) keep the gate as written, which means no premium-harvesting lane can ever be promoted, or (b) add a carry-lane variant of the gate that drops the timing item but requires the forward T-G record, the max-loss sizing above, and a stress test on large-move days re-pulled with a wider strike band. Until the user decides, H15 stays a forward paper lane only.

