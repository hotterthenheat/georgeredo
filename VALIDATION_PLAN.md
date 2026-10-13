# VALIDATION_PLAN

A reproducible plan for testing whether GeorgeFi's observable signals have value, using only data we can obtain independently. Results obtained so far are in `GEORGEFI_SIGNAL_RESEARCH.md` §6; this file is the design.

---

## 1. Datasets

| Dataset | Source | Rows | What it gives | Known biases |
|---|---|---|---|---|
| **D1 Epoch-2 trade ledger** | `GET /api/trades` (documented public endpoint), saved as `evidence/public_api/trades_all.json.gz` | 489 closed trades, 2026-03-02 → 2026-10-08 | entry/exit timestamps to the ms, OCC contract, entry/exit premium, size, confluence ledger, exit reason, high-water mark, P&L | **Survivorship-free within the epoch** (all closed trades are listed), but Epoch 1 (546 trades, +540 %) is not exported trade-by-trade and the operator chose the epoch boundaries. Entry/exit premiums are the operator's own simulated fills ("paper-traded at live prices"). |
| **D2 Public signal tape** | `GET /api/public/todays-signals?date=` for the 8 sessions the UI exposes | 972 alerts, 2026-10-06 → 10-13 | every subsystem's alert with minute timestamp, contract string, direction, loud flag, paper-book state | Only the last ~8 sessions are retrievable; alerts are heads-ups more than orders; 142 rows have no parsable contract |
| **D3 Recap alerts** | SSR payloads of `/recaps/<date>` | 147 alerts across 9 sessions (102 actionable) | entry price at alert, one-minute-high peak, exit call, source record ids | Curated by the operator ("a selection of the day's alerts"); peaks are highs, not fills |
| **D4 Live decision snapshots** | `GET /api/analysis` polled every 5 min | 20 decisions per snapshot | how direction/confidence/grade/levels evolve within a session | 1 session so far |
| **M1 Contract minute bars** | UW `option-contract/{id}/intraday` | one file per trade/day | OHLC, volume, IV range, ask/bid-side premium | no NBBO history |
| **M2 Underlying bars** | UW `stock/{t}/ohlc/1m` | per session | levels (PDH/PDL/ORB/VWAP), realized moves | index bars only via UW |
| **M3 Dealer exposure** | UW `greek-exposure/strike`, `spot-exposures`, `gex-levels` | per session | regime, flip, walls | model estimates |
| **M4 Flow** | UW `flow-per-strike-intraday`, `option-trades` (live), full-tape archives (history) | per session | per-strike premium bursts to re-detect "sus strikes" | tick history needs 1.5 GB/day downloads |

---

## 2. Questions and tests

### T1 Fill realism (D1 × M1)
For each trade, locate the 1-minute bar containing `entryTime` and `exitTime`. Measure whether the recorded premium lies inside `[low, high]` of that bar (or the next bar if the timestamp falls in the last seconds), and the position of the fill within the bar range. Report the share of entries that would have been fillable at or below the recorded price with a limit order, and the median distance between recorded premium and the bar's VWAP. A high share of "better than bar VWAP" fills is a flag for optimistic simulation.

### T2 Outcome replay with explicit cost assumptions (D1 × M1)
Recompute every trade's P&L under four fill models, all using the operator's exit timestamp and size:
1. *As recorded* (baseline).
2. *Bar-VWAP*: buy at entry-bar VWAP, sell at exit-bar VWAP.
3. *Adverse*: buy at entry-bar high, sell at exit-bar low.
4. *Adverse + spread*: model 3 plus a half-spread penalty on each side (spread proxy = 8 % of premium for SPX/NDX/RUT cash contracts, 12 % for ETFs/singles, from GeorgeFi's own `quoteQuality` records), plus $0.65/contract commission and $0.05 exchange fees.
Report total P&L, win rate, expectancy per trade, profit factor, max drawdown (daily close-to-close) for each model, with bootstrap 95 % intervals over trades.

### T3 Exit-rule value (D1 × M1)
Replace the operator's exits with mechanical alternatives applied to the same entries and bars:
- hold to 15:55 ET (0DTE) / to the recorded exit day close (swings);
- fixed bracket +25 % / −25 %;
- the published tier ladder (T1 +25 % sell half, T2 +45 %, breakeven lock at +6 % HWM, trail 8/11/14 % by VIX bucket);
- time stop at 30 minutes.
Compare against the recorded exits. This isolates how much of the result is entry selection vs exit management.

### T4 Entry-signal information content (D1 × M1 × M2)
For each entry compute maximum favourable excursion (MFE) and maximum adverse excursion (MAE) of the contract until 15:55 ET, and the underlying's signed move over 5/15/30/60 minutes in the trade's direction. Baselines:
- *Random-time baseline*: for each trade, sample 20 random entry minutes on the same day and contract (or nearest strike) and compute the same MFE/MAE; report the trade's percentile.
- *Opposite-side baseline*: the same contract strike on the other side (call↔put) at the same minute.
A real directional edge shows as MFE percentiles above 50 and the underlying's forward move significantly positive after costs.

### T5 Gate and grade validity (D1)
Treat each confluence tag family as a feature. For families with ≥30 occurrences, compare win rate and expectancy with vs without the tag (Fisher exact / bootstrap). Test the explicit claims: grade monotonicity (A+ > A > A- > B+), `SESSION_ADJ` time-of-day bonuses, `CHOP_DAY` penalty, `GEX:NEGATIVE_GAMMA+10` boost, `SWEEP_ALIGNED` bonus, `TRIPLE_CONFIRM`. Correct for multiple comparisons (Benjamini–Hochberg) and report effect sizes with intervals, not just p-values.

### T6 Public-tape signal value (D2 × M1 × M2)
For each `index-read` FULL SIZE / HALF SIZE, `trade-now`, `moc-wick CONFIRMED`, `block-sniper STRONG`, `sus-strike BURST/KILLER` alert with a parsable contract: compute contract return from the alert minute's bar close to (a) +15 min, (b) +60 min, (c) 15:55, and the hold-advisor exit when one exists. Compare `sus-strike` bought-at-ask vs sold-at-bid directions (the guide claims SOLD = mirror side). Use D3 peak values only as a cross-check, never as a return estimate.

### T7 Refresh stability (D4)
Across the 5-minute snapshots, measure how often `direction`, `action`, `confidence`, `setupGrade` and `contract` change per ticker, and whether flips cluster at level sweeps (`sweepsToday`) or at time-bucket boundaries (10:00, 12:00, 13:15, 15:00 ET). This tests the "committed read vs raw lane" distinction GeorgeFi itself describes.

### T8 Replicating the inputs (M3 × M4 × D1)
Re-derive, for each D1 entry minute: ORB high/low, PDH/PDL, VWAP, UW gamma flip / walls, 20-minute per-strike premium burst z-score. Check whether the recorded tags (`SWEEP_ALIGNED:+25(PDH)`, `GEX:NEGATIVE_GAMMA`, `SUS_FLOW_AGGRESSOR`) are consistent with the independently computed values. Agreement rate per tag family tells us which parts of the gate ledger can be reproduced from public data.

---

## 3. Bias controls

- **Look-ahead**: only bars with `t < entryTime` feed any entry-side feature; exits use bars at/after the exit timestamp. GEX snapshots used for a session are the **prior** day's EOD snapshot unless the 1-minute `spot-exposures` series is used.
- **Survivorship**: D1 is the complete closed set of one epoch; Epoch 1 is excluded entirely rather than cherry-picked. The recap set D3 is used only for cross-checks because it is curated.
- **In-sample / out-of-sample**: D1 is split by calendar month. Rules are proposed on March–June (318 trades) and evaluated on July–October (171 trades). Any rule tuned on the public tape (D2, October) is evaluated on later sessions collected after this report.
- **Multiple comparisons**: ~200 tag families exist; report family-wise corrected results and pre-register the eight claims in T5.
- **Regime**: report results split by `entryEnvironment.gexRegime`, `timeBucket`, VIX bucket and weekday so that one month (e.g. June's −$3,497) is visible.
- **Cost realism**: never report results without model 4 of T2 alongside model 1.
- **Sample size**: the current ledger supports conclusions about the aggregate (n=489) and about the big tickers (^SPX 145, QQQ 104, SPY 70) but not about single names (n ≤ 16). Anything with n < 30 is reported as "insufficient".

---

## 4. Metrics

Per test: n, win rate, average win, average loss, expectancy ($ and % of premium), profit factor, maximum drawdown (daily), Sharpe on daily P&L (annualised with √252, only as a comparative figure), bootstrap 95 % CI (10,000 resamples) on expectancy, and the fraction of P&L contributed by the top 5 trades (concentration).

---

## 5. Data required that we do not yet have

- NBBO history for option contracts (UW full-tape archives, or ThetaData — `DATA_PROVIDER_AUDIT.md` §7) to replace the spread proxy with measured spreads.
- The member-only pages (dealer-flow, GEX, hold, weeklies) to capture the *inputs* at alert time rather than only the outputs.
- Longer public-tape history: the UI keeps 8 sessions; a daily collector started on 2026-10-13 (`evidence/scripts/poll_analysis.sh`) should run every session.
- Epoch-1 trade ledger (only aggregates are published).

---

## 6. Reproduction

```
# 1. secrets in env (never in files): UW_API_TOKEN
# 2. public datasets
python3 -I evidence/scripts/profile_trades.py evidence/public_api/trades_all.json       # after gunzip
python3 -I evidence/scripts/analyze_trades_a.py …  analyze_trades_b.py … analyze_trades_c.py … analyze_trades_d.py …
# 3. market data
SP=<scratch> python3 -I evidence/scripts/fetch_uw_bars.py        # UW contract minute bars
# 4. validation
SP=<scratch> python3 -I evidence/scripts/validate_trades.py      # T1–T4 (see SIGNAL_RESEARCH §6 for output)
```
