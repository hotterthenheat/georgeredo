# Compass EMA ladder — "take profits are the nearest EMAs", PREVIEW

**PREVIEW — one month each, no verdict.** Run on the owner's new rule ("take profits are the nearest EMAs") after the rule
was written down and committed alone (RULE_EMA_TARGETS.md, `aad56cf`). Nothing here is a test: no interval, no
eligibility, no holdout. One month is ~20 sessions, which is far too few to tell a small edge from noise.

- **2025-02** is the preview: 19 full sessions (2025-02-03 → 2025-02-28), not one of the scanner's 28 held-out months, and
  inside the main Pick split (both asserted in `targets.py`). Fresh for this rule.
- **2025-03** beside it for comparison (21 sessions) — already seen once under the ladder rule (PREVIEW_2025-03.md
  `cb79c23`), so it is not fresh.
- SPY, QQQ, IWM pooled, 0DTE, fees $0.68748 a contract each way. E1 buys the ATM contract (3% spread veto); E2 buys the
  best-R/R contract of PREREG_EMA_LADDER §3 with a 3% spread cap. Both have the same entries, target and exits (on the ATM
  chart); they differ only in the contract bought and its skips.
- Code: `ema_lib.py` unchanged (sha256 `e56328fe396893209cb5b6d6b5a0587936c1c59a371734324d7677cdb4a8ae64`, as
  committed in `cb79c23`); new: `targets.py` `71f5e6139b982fafa0cca75a4f787045b38cfbd36309b69e70c0e377708514c0`,
  `targets_stats.py` `e3ecdf189684e2e4ba392ab2278457fcf4384d9a503fd4e9782dd2f19cc7e922`, `verify_targets.py`
  `5b7c1bffd60c0c88e1a6e21db5629415373e6c221a82d428ff30de5c258bd9e2`. The trade lists (`out/targets_<month>.json`,
  1.2 and 1.5 MB) are not committed; the run is deterministic (about 45 s) and rebuilds them.

## The table (PREVIEW — one month each, no verdict)

Mean % = mean per-trade return after costs ((exit bid − entry ask) × 100 − fees) ÷ (entry ask × 100); win = return > 0;
avg win / avg loss = the mean returns of winning / losing trades; hold = exit minute − entry minute; mid-to-mid = the same
trades marked mid to mid, no fee; |delta| and premium = the bought contract's at entry. Per name: mean % (trades).

| version | month | sessions | trades | skips | mean % after costs | mean $ | win rate | avg win | avg loss | exits target / stop / 15:58 | median hold (min) | mid-to-mid no fee | median abs delta | median premium (ask) | SPY / QQQ / IWM mean % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 (ATM, 3% veto) | 2025-02 | 19 | 1761 | E1 spread > 3% 490; gap < spread 193; ATM no quote 2 | -2.75% | -2.49 | 30.8% | +15.1% | -10.7% | 27% / 73% / 0% | 2 | +0.45% | 0.50 | $0.97 | -2.43% (697) / -2.46% (713) / -3.95% (351) |
| E1 (ATM, 3% veto) | 2025-03 | 21 | 2179 | E1 spread > 3% 328; gap < spread 237 | -2.28% | -2.36 | 32.5% | +15.5% | -10.8% | 30% / 70% / 0% | 2 | +0.36% | 0.50 | $1.34 | -1.40% (811) / -1.57% (803) / -4.53% (565) |
| E2 (best R/R, 3% cap) | 2025-02 | 19 | 1544 | no R/R contract 747; gap < spread 201; ATM no quote 2 | -5.21% | -2.34 | 27.1% | +18.5% | -14.0% | 28% / 72% / 0% | 2 | +0.27% | 0.27 | $0.44 | -4.92% (637) / -5.28% (678) / -5.78% (229) |
| E2 (best R/R, 3% cap) | 2025-03 | 21 | 2044 | no R/R contract 494; gap < spread 241 | -4.76% | -2.29 | 29.4% | +18.5% | -14.5% | 30% / 70% / 0% | 2 | +0.46% | 0.21 | $0.47 | -4.38% (793) / -4.41% (792) / -6.01% (459) |

No trade in either month reached 15:58 (0 of 7,528). "Both sides" never occurred. Breaks of the 1-minute EMA with no
5/15/30-minute EMA above the close (not a signal, descriptive): E1 617 and 683, E2 636 and 705 (Feb, Mar).

By exit reason: target hits average +16.0% / +16.4% (E1 Feb / Mar, 99% of them winners after costs) and +17.6% / +17.8% (E2);
stops average −9.8% / −10.1% (E1) and −13.9% / −14.4% (E2). The target sits a median 15% above the ATM close at entry.

For comparison on 2025-03 only (the ladder preview, same month): V13 (L1 exits, ATM) −3.61% / −$2.91 a trade; V12 (L1 exits,
best R/R with a 3% cap) −5.91% / −$2.87. The nearest-EMA target with the 1-minute stop loses a little less per trade
(E1 −2.28% / −$2.36, E2 −4.76% / −$2.29) on similar trade counts.

## What the two months show (descriptive only)

- Both versions lose after costs in both months, by about $2.3–2.5 a trade: the mid-to-mid gain is +$0.10 to +$0.71 a
  trade, one spread paid (half in, half out) is $1.02–1.64 a trade, and the fees are $1.37 a round trip.
- Before costs the trades are slightly positive mid to mid (+0.3% to +0.5%), so the rule's moves on the option's mid are
  small and the bid/ask and fees decide the sign.
- About 3 in 10 trades reach the target; 7 in 10 are stopped, almost always within a couple of minutes (median hold 2
  minutes): the 1-minute EMA stop sits very close to the entry, so most trades end on the next candle or two.
- E2's best-R/R pick again leans to the low-delta end (median |delta| 0.21–0.27, premium about $0.45); the 3% cap removes
  most candidates (747 and 494 skipped for "no R/R contract"). E1 buys at |delta| ≈ 0.50 for about $1.00–1.35.
- IWM loses the most in every row (its spreads are wider as a share of premium).

**Integrity:** `verify_targets.py` (plain loops, no numpy, no `ema_lib` / `scanner_lib` code) re-derived 10 trades per month
(5 E1, 5 E2; 3 target and 2 stop exits each), replaying each trade's whole name-session from 09:45 off the raw Parquet rows:
the ATM strike, the carried-mid charts and EMA 9 on 1/5/15/30-minute candles, the break, the target, the cost check, the E1
veto or the E2 pick (its own Black-Scholes and bisection), entry ask, exit minute and reason, exit bid and $ — **20 trades,
0 differences**; and each replayed session's whole trade list (entry, exit, reason) equalled the engine's on 20 of 20.
