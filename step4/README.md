# Step 4: buying the turn and selling near the high

**The question:** you don't have to hold to the close. Can buying when a contract turns up off its low, and selling near its high with a trailing stop, find an edge in same-day contracts? Example: SPY's 762 put on 2026-10-16 went from $0.04 to $1.25.

**The test:** 12,149,834 trades on SPY, QQQ, IWM and SPX, 2022–2026. Every rule was picked on 2022–2024 and checked, unchanged, on 2025–2026.

**Ways in** (all bought at the ask):
- **Fixed times:** step 2's 10,547,433 trades.
- **Turn up:** the first minute (9:36 am to 15 minutes before the close) that a contract's ask reaches 1.5×, 2×, 3× or 5× its lowest ask so far that day.

  | Turn-up multiple | Trades |
  |---|---|
  | 1.5× | 308,876 |
  | 2× | 246,040 |
  | 3× | 132,828 |
  | 5× | 81,717 |

- **Range break:** every call when the underlying first trades above its 9:31–10:00 high, and every put when it first trades below its low. 832,940 trades.

**Ways out:**
- **Trailing stop:** sell at the bid once it falls 20%, 30%, 40% or 50% from the highest bid since buying. This is the realistic version of "sell at its high".
- **Hold** to the close.
- **Exact top:** the hindsight ceiling, shown for comparison only.

**Fees:** $0.65 a contract each way.

## Findings

**1. The exact top is worth about +86% to +138% a trade, but only hindsight knows it.** For contracts near the money (strike within 0.5% of the price), selling at each trade's exact top would have averaged:
- +86% to +109% at fixed times
- +107% to +138% on the turn up and the range break

No rule gets close to that.

**2. A trailing stop is better than holding, but still loses money.** SPY near the money at fixed times:

| Way out | Avg per trade |
|---|---|
| Hold | −19.7% |
| 20% trailing stop | −8.7% |
| 30% trailing stop | −9.0% |

- The stop sold at a median of 68% of the high (20% trailing stop) or 47% (50% trailing stop).
- A stop can't tell a pullback from the top. Today's 762 put spiked to $0.26 just after noon, fell back to about $0.12, then ran to $1.25. Every turn-up buy with a trailing stop sold before the run (in the morning chop or in that pullback), for between −33% and +100%.

**3. Buying on the turn up catches more runners, but not enough to pay.**
- SPX contracts bought on a turn up to 3× their low reached:
  - 2× the price paid 29.4% of the time
  - 5× 8.5% of the time
  - 10× 3.3% of the time
- Fixed-time buys reach those 3.5%, 0.9% and 0.4% of the time.
- Near the money, the turn-up and range-break rules end close to zero:

  | Rule (near the money, trailing stop) | All years | 2022–2024 | 2025–2026 |
  |---|---|---|---|
  | SPX, turn up 3×, 50% stop | +2.9% | +7.1% | −1.4% |
  | SPY, turn up 3×, 50% stop | +0.9% | +6.0% | −3.6% |
  | SPY, turn up 2×, 30% stop | −3.2% | | |

  The ones that looked positive turned negative in 2025–2026.

**4. Nothing held up.**
- Of 3,140 rules (way in × way out × product × call or put × distance or price), 459 made money on 2022–2024 and 126 also on 2025–2026.
- 11 of those made +5% or more a trade in both periods on 1,000+ trades each (`out/stress.csv`).
- All 11 fail the stress test. Each one's 95% range includes zero, and each turns negative without its best 5 days.
- The headline example: SPX puts 1–2% out of the money bought when SPX breaks below its morning range, held to the close.
  - +25% a trade.
  - It made money on only 28 of 774 days.
  - Its best 5 days made about four times its whole profit, so the other days together lost money.
  - Without those 5 days it averages −76% a trade, and 2026 so far is −86% a trade.

**What it means:**
- Cheap contracts that run 10–60× (like the 762 put) look the same as the ones that go to zero, both when they're bought and on the way up.
- Price and time alone, even buying on the turn and selling with a trailing stop, didn't separate them on 2025–2026.
- Finding them in advance needs information this data doesn't have: the flow into each contract, dealer positioning, or event times.

## Files

| File | What it is |
|---|---|
| `trail.py` → `out/trades_<PRODUCT>.parquet` | Every trade of every way in, with its trailing-stop exits (minute, bid, peak) and best bid |
| `verify.py` | Checks 600 trades of every kind against the raw quotes with separate code, including that each turn-up buy is the first minute its rule was met. No differences. Every fixed-time trade's price and best bid also equal step 2's |
| `summarize.py` → `out/*.csv` | `summary`, `by_distance`, `by_price`, `runs`, `survivors`, `headline` |
| `stress.py` → `out/stress.csv` | The 11 largest survivors and their mirrors: by year, a day-resampled range, without the best 5 and 20 days |

**Page:** "0DTE sell near the high".
