# BACKTEST_RESULTS

Independent backtest of the GeorgeFi-style 0DTE strategy as reconstructed from `GEORGEFI_SIGNAL_RESEARCH.md`, run on 2026-10-13. Code: `backtest/`. Outputs: `backtest/results/v1/` (`report.txt` has every variant; `summary.json` is machine-readable; `trades.csv.gz` has all 192,900 simulated trades; `baseline.csv.gz` the random-entry baseline; `georgefi_match.txt` the coincidence test).

Everything here is **Calculated** by us from Unusual Whales 1-minute data. Nothing comes from GeorgeFi's own P&L.

---

## 1. What was tested

**Universe and period.** SPY, QQQ, IWM 0DTE options (daily expiries), 345 sessions from 2025-06-02 to 2026-10-09. In-sample = sessions before 2026-03-02 (the start of GeorgeFi's Epoch 2); out-of-sample = 2026-03-02 → 2026-10-09. ^SPX was excluded because SPX index minute bars require a CBOE-approved Unusual Whales entitlement that this account does not have (option bars for SPXW contracts are available, the underlying is not).

**Data.** Underlying 1-minute RTH and pre-market bars (`stock/{t}/ohlc/1m`), prior-day dealer levels (`gex-levels`: gamma flip, call wall, put wall, magnet, dated T-1 to avoid look-ahead), 1-day implied-volatility context, and 1-minute contract bars (`option-contract/{id}/intraday`) for 9,299 contract-days (4,279 strategy, 5,020 baseline). All raw responses are cached outside the repo; the fetch scripts are in `backtest/`.

**Entry rules (two modes, two level sets).**
- Levels: PDH/PDL (prior session), PWH/PWL (prior five sessions), PMH/PML (same-day pre-market), ORH/ORL (first 15 minutes, usable from 09:45), and optionally CALL_WALL/PUT_WALL from the prior-day GEX levels.
- `sweep` (GeorgeFi's "sweep and reversal"): within the last 3 one-minute bars the price pierced a level (high above a resistance level or low below a support level), at most one bar closed beyond it, the preceding ~10 bars were mostly on the inside, and the current close is back inside by at least max(0.25·ATR₁₄, 0.02 %). Direction = against the sweep (sweep of a high → puts, sweep of a low → calls).
- `continuation`: first clean close beyond a level after being on the other side, direction = with the break.
- One signal per level and direction per 10 minutes; 30-minute cooldown per ticker; one open position per ticker; at most 5 entries per ticker-day.
- Contract: nearest-strike 0DTE call (bullish) or put (bearish); entry at the volume-weighted price of the first option bar after the signal minute (skipped if no bar prints within 3 minutes or premium < $0.05).

**Gates.** `none`; `posgamma_fade` (take sweep reversals only when spot is above the prior-day gamma flip, continuation only below it, i.e. the "dealers dampen / dealers amplify" rule); `avoid_pin` (no entries within 0.1 % of the gamma magnet).

**Session windows.** `all` 09:35–15:30; `morning` 10:00–12:00 (GeorgeFi's "Silver Bullet" window); `no_lunch` 09:35–12:00 and 13:15–15:00.

**Exit engines** (on 1-minute option bars, stop checked on the bar low before targets on the bar high):
- `ladder`: initial stop −25 % (GeorgeFi's sweep-entry stop), T1 +25 % sells half, T2 +45 % sells the rest, breakeven lock once the high-water mark reaches +6 %, guardian trail (floor = 65 % of the high-water mark once it reaches +15 %), time stop after 30 minutes if not positive, hard close at 15:55 ET.
- `trail`: same protective logic without the profit targets.
- `bracket`: +25 % / −25 %, close 15:55.
- `hold`: close 15:55 only.

**Cost models** (per contract): `mid` = fills at bar VWAP, no costs; `spread` = half-spread of 1 % (SPY, QQQ) or 2 % (IWM) of premium on each side plus $0.70 fees per side; `adverse` = buy at the entry bar's high, sell at a bid-side proxy (price minus two half-spreads) plus fees. Reported dollars are for one contract; median entry premium was $1.01, so $1 ≈ 1 % of premium.

**Baseline.** For every ticker-day, the same number of entries as the reference variant (`sweep|ict+gex|all|none|ladder`) at uniformly random minutes in the 09:35–15:30 window with a random direction, same contract choice, same `ladder` engine and the same cost models (9,896 trades).

**Metrics.** n, total, win rate, expectancy per trade with a 1,000-resample bootstrap 95 % interval, profit factor, maximum drawdown of the cumulative one-contract P&L, in-sample and out-of-sample expectancy.

---

## 2. Headline results

| Variant (mode \| levels \| window \| gate \| engine) | n | Win rate | Expectancy, spread model [95 % CI] | mid | adverse | IS | OOS [95 % CI] |
|---|---|---|---|---|---|---|---|
| Best of 144: `sweep \| ict+gex \| morning \| posgamma_fade \| trail` | 834 | 36.3 % | **−$2.41** [−4.10, −0.47] | +$2.0 | −$10.6 | −$2.9 | −$1.8 [−4.5, +0.9] |
| GeorgeFi-like reference: `sweep \| ict+gex \| all \| none \| ladder` | 2,979 | 36.5 % | −$3.44 [−4.23, −2.70] | +$1.1 | −$10.4 | −$3.8 | −$3.0 [−4.3, −1.8] |
| Same entries, `trail` engine | 2,979 | 36.5 % | −$3.06 [−3.94, −2.17] | +$1.1 | −$10.4 | −$3.4 | −$2.7 [−4.1, −1.3] |
| Same entries, `bracket` ±25 % | 2,670 | — | −$5.21 [−6.44, −4.01] | −$1.5 ret | — | −$5.8 | −$4.6 |
| Same entries, `hold` to 15:55 | 941 | 31.1 % | −$18.06 [−31.7, −4.8] | −$13.5 | −$26.9 | −$18.0 | −$18.2 |
| `continuation \| ict+gex \| all \| none \| trail` | 2,235 | 37.1 % | −$3.07 [−4.30, −1.76] | +$1.2 | −$12.8 | −$3.6 | −$2.5 |
| **Random-time baseline**, `ladder` engine | 5,665 | 37.1 % | **−$3.20** [−3.70, −2.70] | +$0.6 | −$9.3 | — | — |

- **0 of 144 variants** have positive expectancy after spread and fees; **0** have an out-of-sample lower confidence bound above zero.
- 62 of 144 are marginally positive at mid (no costs), by +$0.4 to +$2.0 per trade, i.e. 0.1–1 % of premium, which is smaller than one round trip of a 1 % half-spread plus fees (≈ $3.40 on a $1 contract).
- The best sweep variant beats the random-entry baseline by about $0.8 per trade; its confidence interval contains the baseline. The entry rule carries no measurable timing information, which matches the earlier finding on GeorgeFi's own ledger (MFE percentile ≈ 50 against random entries).
- Exit engine is the only dimension with a large, consistent effect: mean expectancy across variants is `trail` −$3.2, `ladder` −$4.0, `bracket` −$6.1, `hold` −$14.8 (spread model). Holding 0DTE ATM contracts to the close loses 11 % of premium on average before costs. This ordering is the same one GeorgeFi's record shows (its exits beat every mechanical alternative; see Signal Research §6 T3).
- Mode, level set, window and GEX gate change expectancy by less than $1 per trade; `posgamma_fade` is the least bad gate (−$6.6 mean across engines vs −$6.9 for none), but the difference is within noise.
- Both directions lose: in the reference variant, calls −$4 (n=1,540), puts −$3 (n=1,439). All three tickers lose. All ten levels lose; PWH sweeps are the worst (−$6, 26 % win rate).
- Month by month, the reference variant is negative in 15 of 17 months (mid: slightly positive in 2026-03 and 2026-07).

Exit mix of the reference variant explains the shape: breakeven stops 1,120 (−$4 each), trail exits 979 (+$13), stops 744 (−$30), T2 113 (+$36), time stops 23 (−$20). Median hold 3 minutes (p75 5): the +6 % breakeven arm triggers within minutes on 0DTE contracts and the position is then stopped at zero on the next dip. 73 % of entries reached +25 % at some point before 15:55, which is why loose exits look tempting and why every fixed exit still loses: the contracts swing ±25 % constantly regardless of the entry.

---

## 3. Does the reconstruction match GeorgeFi?

`backtest/results/v1/georgefi_match.txt`, using GeorgeFi's 188 SPY/QQQ/IWM scalps from the public ledger:

| Test | Result |
|---|---|
| A same-direction `sweep` signal within ±5 min of a GeorgeFi entry | 14/188 (7.4 %) with ICT levels, 16/188 (8.5 %) with ICT+GEX levels |
| Any signal within ±5 min | 16–18 % |
| `continuation` signal within ±5 min, same direction | 5 % |
| Our sweep signals during GeorgeFi's period that have a same-direction GeorgeFi entry within ±5 min | 19 of 2,944 (0.6 %) |
| Direction agreement when both fire within ±30 min | 124 agree vs 143 disagree (46 %) |

GeorgeFi's live entries are therefore **not** reproduced by the published "sweep of PDH/PDL/PWH/PWL/ORH/ORL and reverse" description at any reasonable tolerance, and when both systems fire near each other they disagree on direction about as often as they agree. Its real trigger either uses inputs we did not model (per-strike flow bursts, dealer accelerator changes, the five-contributor vote) or different level definitions. Either way the published rule set is not "the strategy".

---

## 4. Robustness checks performed

- Look-ahead: GEX levels are the prior session's; ORB levels are used only after 09:45; entries use the *next* option bar after the signal minute; exits use bar lows for stops before bar highs for targets.
- Costs: three models reported side by side; the `spread` model (1–2 % half-spread) is optimistic for IWM and for premiums under $0.50.
- Sample: 834–2,979 trades per variant; 345 sessions; two market regimes (2025 H2 low-VIX grind, 2026 spring/summer).
- Multiplicity: 144 variants were tried; the best one is reported next to the baseline and the full table so the selection effect is visible. No parameter was tuned on the out-of-sample window.
- Reproducibility: fixed random seed; cached raw data; one command per stage (see `backtest/README.md`).

---

## 5. What was not tested (and why)

- ^SPX / ^NDX / ^RUT cash index contracts (no index bars on this UW entitlement).
- Flow-burst ("sus strike") gating: requires per-strike intraday flow for every ticker-day (1.2 MB each) or the full-tape archives; feasible but ~500 MB per ticker-year.
- VIX-scaled trails (UW does not serve VIX on this entitlement; a 1-day IV percentile proxy is cached but was not used as a gate).
- Position sizing and portfolio effects; results are per-contract, equal-weighted.
- Any discretionary overlay (GeorgeFi's record contains hand-written exits).

---

## 6. Conclusion

The reconstructed strategy has **no positive expectancy** on SPY/QQQ/IWM 0DTE contracts after realistic costs, in or out of sample, and is indistinguishable from random entries managed by the same exit engine. The exit engine (breakeven lock plus trailing give-back, fast time stop, no holding into the close) is the only component with demonstrable value, and its value is in *losing less*, not in making money. This agrees with the operator's own published research (`/research`: "no independent SPX 0DTE edge found") and with our audit of their 489-trade ledger.
