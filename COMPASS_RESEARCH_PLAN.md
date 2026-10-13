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
| Provider entitlements (live, 2026-10-13) | UW: contract bars from 2025-04-01, stock bars from 2022-09-28, concurrency 3, index bars 422; Massive: aggregates only, no index, no ticks | `research/georgefi_full_history/provider_audit_2026-10-13.md` |

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
| H9 | 13:00 short ATM straddle, SPY/QQQ, close 15:55 | **Open, candidate paper lane** | +$16.7 mid [5.4, 27.7]; +$8.4 after spread [−3.2, 19.5]; two tail days exceed 16 months of income | Pre-registered test T-A below; prerequisite NBBO capture |
| H10 | Gamma-conditioned last-half-hour momentum, in shares/futures | **Open, candidate (not options)** | peer-reviewed effect only on negative-gamma days; our option test underpowered (1,016 ticker-days) | Pre-registered test T-B on SPY shares back to 2022-09-28 |
| H11 | SPXW contracts (larger premium, lower proportional cost) for short premium | **Open, data-gated** | index bars unavailable (422); SPXW contract bars and the spot-exposures `price` series are available | Test T-C using contract bars plus the per-minute `price` field as the index proxy |
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
- Rotate the Unusual Whales and Massive keys and change the GeorgeFi password that were shared in chat.
- Whether to create a `main` branch and open a pull request; all work is on `claude/lucid-heisenberg-bpyq7k` in dedicated directories because this session is pinned to that branch.
