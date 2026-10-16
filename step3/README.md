# Step 3: every one of the 10.5 million trades, broken down

**The question:** step 2's trades are every same-day contract on SPY, QQQ, IWM and SPX, bought at the ask at nine times of day. For each one:
- How far did it run (the % per trade)?
- Where do the losses come from?
- Does any way out of a trade avoid them?
- Does anything known when buying separate winners from losers?

**The test:** 10,547,433 trades, followed minute by minute to:
- 8 profit targets
- 3 stops
- 3 time exits

Every rule and condition was picked on 2022–2024 (at least 300 trades) and then read, unchanged, on 2025–2026.

## Findings

All figures are after fees ($0.65 a contract each way) unless marked otherwise. "Near the money" means a strike within 0.5% of the price when bought.

**1. The % per trade: big moves happen often.** Share of near-the-money trades whose bid reached each gain at some point before the close:

| | +25% | +50% | +100% | +150% | +200% | +300% | +500% | +1,000% |
|---|---|---|---|---|---|---|---|---|
| SPX | 61.7% | 46.8% | 29.9% | 20.0% | 14.2% | 8.1% | 3.6% | 0.9% |
| SPY | 60.2% | 44.6% | 27.4% | 17.8% | 12.3% | 6.8% | 2.7% | 0.6% |
| QQQ | 62.1% | 46.4% | 28.5% | 18.5% | 12.6% | 6.5% | 2.4% | 0.4% |
| IWM | 62.1% | 47.5% | 29.9% | 19.3% | 13.3% | 6.7% | 2.3% | 0.3% |

These are what a perfect exit could have taken, not what any rule took.

**2. Held to the close, most near-the-money trades lose.**
- About 50% expire worthless, and about 70% end below what was paid.
- About 6–7% end up 200% or more.

**3. Losers often had the gain first.** Among SPX near-the-money trades that lost if held:
- 72% expired worthless.
- 48% had been up 25% or more first.
- 31% had been up 50% or more.
- 16% had been up 100% or more.

The other products are within two points of these figures (`out/losers_near.csv`).

**4. Stops cut the losses; targets raise the win rate but lower the average. Neither made money.** SPX near the money, every entry time (`out/targets_near.csv`):

| Way out | Win rate | Avg win | Avg loss | Avg per trade |
|---|---|---|---|---|
| Hold to the close | 30.2% | +168% | −85% | −8.5% |
| Sell at +25% | 63.6% | +24% | −87% | −16.3% |
| Sell at +100% | 41.2% | +82% | −85% | −15.8% |
| Sell at +150% | 36.4% | +105% | −85% | −15.4% |
| Stop at −50%, no target | 21.7% | +168% | −53% | −4.8% |

- A −50% stop cut the average loss from about −85% to about −53%.
- A small target raised the win rate to 64%, but it capped the wins and made the average worse.
- Every row is negative on SPY, QQQ and IWM too.

**5. The best ways out on 2022–2024 did not hold up.**
- Of 17,496 combinations (product, call or put, entry time, distance and way out), 796 made money on 2022–2024. Only 118 also made money on 2025–2026.
- Picking the best of the 108 ways out for each of the 162 groups on 2022–2024 left 9 groups positive on 2025–2026.

**6. The one family that held up rests on a few days.** The 118 survivors were mostly one family:
- 112 were SPX or SPY calls.
- All were bought by 11:00 am.
- 110 used a stop.

One of them, stress-tested: calls bought at 9:31 am, 0–0.5% out of the money, stopped at −50%, otherwise sold 30 minutes before the close (`out/stress.csv`):

| Product, side | Avg per trade | 95% range (days resampled) | Without best 5 days | By year |
|---|---|---|---|---|
| SPX calls | +9.3% | −1.6% to +22.5% | −0.7% | 2022 +7.9%, 2023 +8.2%, 2024 +8.0%, 2025 +0.0%, 2026 +22.3% |
| SPY calls | +3.7% | −7.0% to +15.9% | −5.4% | 2025 −7.3% |
| QQQ calls | +4.4% | −5.7% to +15.6% | −2.9% | 2025 −13.6% |
| IWM calls | −8.9% | | | |
| Puts, every product | −4.3% to −8.4% | | | |

- It made money on calls in a market that rose over the sample, and lost on puts.
- Its range includes zero, and leaving out its 5 best days (of 1,106) makes it negative.
- This is not an edge to trade.

**7. Nothing known when buying separated winners from losers.**
- Conditions tested: the move and the gap the contract's way, VIX, the spread, the day's range so far against the move still priced, where the price stood in the day's range, and the contract's own change since 9:31.
- Of 1,461 condition groups, 53 made money on 2022–2024 and 1 also on 2025–2026: SPX puts held to the close when the move still priced was 0.75–1× the session before's range. It made +8.9% and then +0.8%.
- With 1,461 tried, one survivor is about what chance gives.

## What it would take

- A −50% stop is the one change that consistently made the losses smaller. It was still not enough.
- The data say the money was there: about 30% of near-the-money contracts doubled at some point. No fixed rule, and no condition tested here, found those trades in advance.

The next things to test would need information this data does not hold:
- the flow into each contract (volume, sweeps, open interest),
- dealer positioning (gamma by strike),
- news and economic-release times.

## Files

| File | What it is |
|---|---|
| `paths.py` → `out/paths_<PRODUCT>.parquet`, `out/features_<PRODUCT>.parquet` | Each trade's first minute at every target and stop, its bids at the time exits, and what was known at the entry minute |
| `verify.py` | Checks two things: 600 trades and 160 entry minutes re-derived from the raw quotes with separate code, and every trade's +100% minute, −50% minute and bid, and best bid against step 2. No differences |
| `summarize.py` → `out/*.csv` | `reach`, `outcomes`, `losers`, `exits` (all 23,328 cells), `exits_best`, `exits_summary`, `targets_near`, `filters`, `filters_best`, `headline` |
| `stress.py` → `out/stress.csv` | The surviving rule, year by year, with a day-resampled range and without its best days |

**Page:** "0DTE wins and losses".
