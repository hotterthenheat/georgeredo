# Step 1: every same-day (0DTE) option contract, broken down

**What it covers:** SPY, QQQ, IWM and SPX (root SPXW), every contract of each session's same-day expiry.
- Coverage starts when each product began listing an expiry every day: SPX on 2022-05-13, SPY and QQQ on 2022-11-11, IWM on 2024-04-19.
- It runs to 2026-10-09.
- Total: 3,687 sessions and 1,176,935 contracts.

**Source:** raw ThetaData one-minute NBBO for every strike, plus the underlying's one-minute prices. The raw files are kept outside the repository.

**Checks:**
- `inventory.py`: every trading session has its chain.
- `verify.py`: 400 random contracts (40 of them on half days) were re-derived from the raw quotes with separate code. Every figure matched.

## Files

| File | What it is |
|---|---|
| `inventory.py` → `out/inventory.parquet` | Which sessions, strikes and minutes the raw data holds |
| `breakdown.py` → `out/contracts_<PRODUCT>.parquet` | One row per contract per session. The definitions are in the script's header |
| `verify.py` | The independent re-derivation check |
| `summarize.py` → `out/*.csv` | The summaries behind the page: by distance from the money, timing of highs and lows, the last 20 sessions contract by contract |

## Columns of `contracts_<PRODUCT>.parquet`

All prices are per share. Multiply by 100 for one contract. Minutes count from 9:30 am New York (minute 0).

**Identity**
- `product`, `session`, `strike`, `right`.

**Quotes**
- `open_*`: the first two-sided quote from 9:31 am.
- `close_*`: the last quote at the close (4:00 pm, or 1:00 pm on a half day).
- `high` and `low`: of the mid price, with `high_minute` and `low_minute`.
- `best_bid` and `best_ask`: the highest bid and the lowest ask of the day, with their minutes.
- `spread_median`: the median spread as a share of the mid. `spread_median_usd`: the same in dollars.
- `quoted_minutes` and `zero_bid_minutes`.

**Underlying**
- `spot_open`, `spot_close`, `spot_high`, `spot_low`.
- `close_minute` and `half_day`.

**Outcome**
- `settle`: what the contract was worth at the close.
- `expired_itm`: whether that was more than zero.
- `strike_vs_open` and `otm_at_open`: where the strike stood against the price at the open.

**Trades**
- `buy_open_hold`: paid the opening ask, held to the close.
- `sell_open_hold`: received the opening bid, held to the close.
- `run_up` and `draw_down`: the best and worst bid after the open, against the opening ask.
- `best_long` and `best_short`: the best trade the day allowed in hindsight, with `*_exit_minute` and `*_exit`.

No fees are taken off. The bid/ask is in every figure that buys or sells.
