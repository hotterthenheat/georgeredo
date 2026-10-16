# Step 5: can you tell the runners at the moment you buy them?

**The question:** we have every same-day contract's quotes, minute by minute, so we can see every low, every turn and every high. Can what was visible at the moment of the turn tell the contracts that went on to run (like SPY's 762 put on 2026-10-16, $0.02 to $1.25) from the ones that went to zero? And if so, does buying only those make money?

**The trades:** step 4's 1,602,401 turn-up and range-break buys. Turn-up means the first minute a contract's ask reached 1.5, 2, 3 or 5 times its low so far. Range-break means the first break of the 9:31–10:00 range.

| Product | Trades |
|---|---|
| SPY | 368,268 |
| QQQ | 390,588 |
| IWM | 172,490 |
| SPX | 671,055 |

**What was visible at the turn:** 42 measurements, all known by the end of the minute of buying and none from after it (`features.py`; `verify.py` re-derived 400 trades from the raw files with separate code, no differences). They cover:
- **The contract:** its price, spread and quoted sizes; how far it had fallen from its earlier high before its low; how long ago the low was; how fast it was rising over the last 1, 5 and 15 minutes.
- **The underlying:** its move over the last 1, 5, 15 and 30 minutes, since the open and since yesterday; where it stood in the day's range; whether it had just made a new high or low; how jumpy it was.
- **Volatility:** VIX and its change.
- **The options market:** the move the at-the-money straddle was still pricing, and the strike's distance from the price in units of that move.
- **The calendar:** time of day, time to the close, weekday.

**The test:** two models (gradient-boosted trees), both fixed before the 2025–2026 trades were scored, and those trades scored once (`model.py`):
- **Model A:** the chance that the bid reaches 3 times the price paid (+200%).
- **Model B:** the trade's result with step 4's 50% trailing stop.

| Period | Use | Trades |
|---|---|---|
| 2022-05 to 2024-06 | Train | 511,568 |
| 2024-07 to 2024-12 | Stop training, set the cut points | 204,550 |
| 2025-01 to 2026-10 | Check | 886,283 |

**Fees:** $0.65 a contract each way, none when a contract expires worthless.

## Findings (2025–2026, never seen while building)

**1. Yes, runners can be partly told apart at the moment you buy.**
- Model A ranked 2025–2026 almost as well as 2024 (AUC 0.88 in both).
- The top 1% reached 3× the price paid 26% of the time, against 6% for all turn-up buys.

| Model A's picks | Trades | Reached 3× | Avg if sold at the exact top | Avg with 50% trailing stop | Avg if held |
|---|---|---|---|---|---|
| All turn-up buys | 886,283 | 5.8% | +18% | −65% | −57% |
| Top 10% | 92,299 | 23.8% | +215% | −6.5% | −12.4% |
| Top 5% | 52,235 | 24.9% | +223% | −0.5% | −1.4% |
| Top 1% | 13,972 | 25.6% | +229% | +14.6% | +13.1% |

**2. What the runners looked like when they turned.** These held the same in both periods:
- **The strike was within about one remaining expected move of the price.** Between 0.4 moves in the money and 3 moves out, 22% of turns reached 3×. More than 6 moves out of the money, about 2% or less did.
- **The contract had already been crushed.** Contracts whose low was under a quarter of their earlier high reached 3× 14% of the time, against 0–5% for ones that had barely fallen.
- **It was rising steadily, not spiking.** Up 1.3–1.5× over the last 5 minutes, 15% reached 3×. Up 2× or more in 5 minutes, only 5–7% did, so chasing a spike is worse.
- **The spread was not wide.** Spreads of 25% of the ask or more reached 3× 2% of the time, and averaged −137% to −148% a trade once the spread and fees were paid.

**3. But even the best picks don't make money reliably.**
- About 75% of model A's top picks still never reach 3×.
- The ones that do are hard to sell near the top. The top 1% averaged +229% at the exact top but +14.6% with the trailing stop.
- That +14.6% fails the stress test:
  - Its 95% range runs from −18% to +60%.
  - Without its best 5 days it averages −20%.
  - It made +28% in 2025 and +1% in 2026.
  - The same bucket lost money on 2024's second half (−1.2%), so it would not have been chosen before 2025.
- Model B (built to predict the trailing-stop result directly) found nothing: its top picks averaged −0.5% to −1.7% a trade.

**4. No other way out rescues the picks** (`exits.py`).
- 184 ways out were tried on model A's picks: 9 targets × 4 stops × 5 time exits, plus the 4 trailing stops.
- Each was picked on 2022–2024, using trades scored by models that never saw them, then read on 2025–2026:

| Picks | Way out picked on 2022–2024 | 2022–2024 | 2025–2026 | 95% range | Without best 5 days | 2026 so far | Best 5 days vs whole profit |
|---|---|---|---|---|---|---|---|
| Top 10% | −70% stop, out 120 min after buying | +17.4% | +3.3% | −20% to +38% | −23% | +2.2% | 7.8× |
| Top 5% | Hold to 30 min before the close | +17.7% | +1.2% | −33% to +42% | −35% | −23.7% | 29× |
| Top 1% | Hold to 30 min before the close | +29.3% | +5.2% | −43% to +88% | −45% | −37.8% | 9.3× |

- None of the ways out picked uses a profit target. The money comes from a few huge runners, and any target cuts them short.

**5. Cheap contracts are mostly fees.**
- A $0.02 contract costs $2, and $1.30 in fees eats 65% of that before the price moves.
- Turn-up buys costing under $5 a contract averaged −166% a trade with the trailing stop, because the fees add to a price loss that is already near total.

**6. Trading only the top 1% (and stricter)** (`top1.py`). On 2025–2026, one contract a trade, with each of three ways out. "Every pick" takes every trade in the top group. "First pick each day" takes one trade a day: the earliest pick of the day, which needs nothing from later in the day.

| Picks | Way out | Trades | Win rate | Avg a trade | Avg win | Avg loss | Biggest win | Biggest loss | Total ($) | Days up |
|---|---|---|---|---|---|---|---|---|---|---|
| Top 1%, every pick | 50% trailing stop | 13,972 | 21% | +14.6% | +233% | −45% | +11,825% | −110% | +$698,574 | 68 of 295 |
| Top 1%, every pick | Hold to 30 min before close | 13,972 | 18% | +5.2% | +438% | −92% | +11,187% | −143% | +$507,772 | 71 of 295 |
| Top 1%, first pick each day | 50% trailing stop | 295 | 21% | −3.9% | +151% | −45% | +1,352% | −110% | −$6,900 | 62 of 295 |
| Top 1%, first pick each day | Hold to 30 min before close | 295 | 18% | −16.7% | +331% | −93% | +1,404% | −122% | −$8,694 | 53 of 295 |
| Top 0.1%, every pick | 50% trailing stop | 1,339 | 25% | +77.7% | +455% | −47% | +3,186% | −86% | +$521,677 | 18 of 76 |
| Top 0.1%, first pick each day | 50% trailing stop | 76 | 22% | −12.4% | +91% | −42% | +443% | −72% | −$2,471 | 17 of 76 |

- **Every top-1% pick made money in total, but almost all of it came on one day.** 2025-11-20 alone made $1,046,400 across 323 picks.
  - Without its best 5 days, the top 1% lost $620,114.
  - 20 of 22 months lost money. Only November 2025 and April 2026 were clearly up.
- **One trade a day, the version a person could actually follow, lost money on average** at every cut and with every way out.
  - In dollars, the top 0.1% held to 30 minutes before the close came out +$1,937 over 76 trades, and held to the close +$3,960.
  - Both rest on one or two trades: the biggest wins were $11,599 and $15,331.
- **The stricter the cut, the higher the average, and the fewer the days it rests on.**
  - The top 0.1% averaged +77.7% a trade, but made money on 18 of 76 days.
  - It made +160% a trade in 2025 and −16% in 2026.
  - Its 95% range runs from −31% to +271%.
  - On 2022–2024 (scored by models that never saw those trades) the same top 0.1% averaged +0.4%.

## What it means

- Price, quotes and timing do carry real information about which turns become runners, and it held up out of sample.
- It isn't enough to pay. Three in four of the best picks still fail, and the winners give back most of their run before any rule can sell.
- What profit there is comes from a handful of days.
- Like steps 2–4, this is a negative result. It was not tuned to look better.

## Still running: per-contract volume

The one input this test didn't have is the trading in each contract: whether buyers were paying up, and how much was trading against its own normal.
- ThetaData's one-minute bars with volume are downloading now, outside market hours.
- `volume.py` adds 12 volume measurements (the contract's volume burst, its trade sizes, whether its last trades were above the middle quote, and the call/put mix around it).
- It then refits both models with and without them on the same trades and split, so any gain is volume's alone.
- Results will be added here.

## Files

| File | What it is |
|---|---|
| `features.py` → `out/features_<PRODUCT>.parquet` | Every turn-up and range-break trade with what was visible at its entry minute (checks that its low before buying equals step 4's on every trade) |
| `verify.py` | Re-derives 400 trades' measurements from the raw files with separate code. No differences |
| `model.py` → `out/headline.csv`, `buckets.csv`, `stress.csv`, `importance.csv`, `feature_deciles.csv`, `scores.parquet` | The two models: their ranking power, every bucket by product and contract price, the stress tests, which measurements mattered, each strong measurement by tenth |
| `exits.py` → `out/exits_grid.csv`, `exits_best.csv`, `exits_stress.csv`, `exit_paths.parquet` | 184 ways out for model A's picks, picked on 2022–2024 and read on 2025–2026 (checks that every pick's path equals step 4's) |
| `top1.py` → `out/top1_summary.csv`, `top1_by_product.csv`, `top1_by_month.csv`, `top1_daily.csv` | Only the top 1%, 0.5% and 0.1%: every pick or the first each day, three ways out, trade by trade, by product, by month and day by day |
| `volume.py` | The volume test, run when the download finishes |
