# Step 2: can a same-day (0DTE) contract make +100%?

**The question:** take every same-day contract on SPY, QQQ, IWM and SPX and buy it at the ask at a fixed time. Sell it the first minute its bid reaches twice the price paid. If it never does, hold it to the close. How often does it double, and does the rule make money?

**Short answer:** many contracts double, but too few to pay for the rest.
- Near the money, 29.1% of trades reached +100%. The ones that did not lost 65.3% of the price on average.
- Every group of contracts lost money, before fees and after. That covers 648 groups by product, call or put, time bought and distance from the price, and 576 groups by price paid.

**What was tested:** 10,547,433 trades: 1,176,935 contracts over 3,687 sessions, each bought at up to nine times of day. The sessions run from 2022-05-13 to 2026-10-09.

## How it was tested

**Buying**
- At the ask at 9:31 am, 10:00, 10:30, 11:00, 12:00, 1:00 pm, 2:00, 3:00 and 3:30 (New York).
- Every contract with a bid and an ask at that minute is bought. No contract is chosen; the results are grouped afterwards.

**Selling at +100%**
- The sale happens the first minute the bid reaches twice the price paid, at exactly twice.
- A resting sell order at that price would have filled by then: the bid cannot climb to a resting offer's price without trading with it.

**Otherwise**
- The contract is held to the close (4:00 pm, or 1:00 pm on a half day) and is worth its value against the underlying's closing price, as in step 1.

**Two other ways out, for comparison**
- Hold to the close with no target.
- Sell at +100% or at the first bid of half the price or less, whichever comes first.

**Fees**
- $0.65 a contract on the buy, and again on the sale.
- No second fee when a contract expires worthless.

**Break-even ("needed") rate**
- The share of trades that must double for a group to break even before fees, given what the others lost on average: L / (1 + L).
- A loss of 90% needs 47%.

**Out-of-sample check**
- Every group was measured on 2022–2024 and then read on 2025–2026 without change.

## Findings

All figures are from `out/*.csv`.

**1. Doubling is common near the money, but never common enough.**
- Within 0.5% of the price:

  | Product, call or put, time bought | Reached +100% | Needed to break even |
  |---|---|---|
  | Lowest | 13.8% | 35.3% |
  | Highest | 40.9% | 44.7% |

- Example: SPY calls 0–0.25% out of the money, bought at 9:31 am, cost $107 typically.
  - 39.6% doubled, with a median of 100 minutes from buying to the double.
  - 45.9% needed to double.
  - Average result: −11.7% of the price before fees, −12.7% after.
- The share that doubles falls as the day goes on, and the gap to break-even widens:

  | Time bought | Gap to break-even |
  |---|---|
  | By 11:00 am | 3.4–12.0 points |
  | From 2:00 pm | 11.1–22.2 points |

**2. Cheap contracts double less often, not more.**
- Contracts priced under $10 reached +100% 0.2–3.6% of the time, depending on product and time.
- Their average result after fees was −109% to −162% of the price: most expire worthless, and the fee is a large share of so small a price.

**3. No group made money.**
- None of the 648 distance groups made money with the +100% rule, before or after fees. None of the 576 price groups did either.
- Selling at +100% beat holding to the close in only 177 of the 648 distance groups: the cap cuts off the rare days that pay several times over.

**4. The −50% stop lost less, but still lost.**
- In near-the-money groups it lost less after fees than the plain +100% rule in 212 of 216 groups.
- It was still negative in all of them.

**5. Holding to the close was positive in 7 of the 648 groups (six SPX, one QQQ).**
- Each of the seven turns negative once its three best days are left out.
- These are a few large-move days, not a repeatable pattern.

**6. Nothing held up out of sample.**
- Of 541 groups with at least 200 trades in 2022–2024, 13 made money after fees there.
- All 13 were in-the-money contracts, at +0.01% to +0.77% of the price.
- None of the 13 made money in 2025–2026.

**What it would take**
- A rule that buys only when a near-the-money contract is more likely to double.
- In the morning, that means 3 to 12 percentage points above the rates here, without lowering what the winners make.
- That is a question about conditions known when buying (the move so far, the gap, the day's range, time of day). This step does not test any; step 3 would.

## Files

| File | What it is |
|---|---|
| `double.py` → `out/entries_<PRODUCT>.parquet` | One row per contract per entry time. The stored columns are quotes and minutes; `load()` adds the distance, multiple, settle and the three results. The definitions are in the script's header |
| `verify.py` | Re-derives random trades from the raw quotes with separate code. 600 trades (40 on half days, 40 that doubled) matched in every figure |
| `summarize.py` → `out/*.csv` | `headline`, `near` (within 0.5%, by time), `overview`, `by_distance`, `by_price`, `by_year`, `by_weekday`, `discovery_check`, `recent_entries` (the last 10 sessions, contract by contract) |

**Page:** "0DTE +100% test", built from these CSVs.
