# Lifecycle research — 12. Per-ticker playbook

**Asked for:** for every options ticker we hold, the highs and lows, where to buy, where to sell, where to add, where to stop, and anything else that matters.

**What this is:** the lifecycle archive cut by ticker, written by `scripts/per_ticker_playbook.py` and `scripts/playbook_md.py`.
- **Same-day (0DTE) options:** SPY, QQQ, IWM and SPX, 2022-11 to 2025-09. IWM's same-day chains in our pull begin 2024-04.
- **One week to over a year:** SPY, QQQ and IWM 2013–2023, and FB 2017–2022.
- **Periods:** development, then validation. The hold-outs are not read, because this report chooses nothing.
- **Entries:** the 12 Compass setups' entries. Earlier reports showed they do no better than random entries (`04_entry_research.md` §1.0, `06_daily_tier.md`), so these numbers describe the instruments more than the setups.

**Two kinds of number:**
- **Hindsight (T1, T2, T7):** where the high and low were, how far a position ran. Nobody can trade the best point; these describe the ride.
- **Executable (T3–T6, T8):** one fixed rule applied to every trade, after the spread and fees, development then validation.

## The short answers

1. **Highs and lows.** Half of SPY and SPX sessions set the day's high or low in the first 30 minutes (QQQ 62 %, IWM 67 %); 22–30 % set the high after 3:00. The median day ranges 0.90 % on SPY, 1.25 % on QQQ and 1.41 % on IWM. Days closed 53–61 % of the way up their range, the period's rise.
2. **Where to buy.** No setup or entry minute picked better trades than a random minute. The data does say what entry costs:
   - spreads are narrowest at the open and about double by 3:00 (SPY Steady 0.8 % → 1.8 %, Big Payoff 3.2 % → 8.0 %);
   - Steady calls bought in the first 30 minutes and held to 3:30 lost the most on SPY, QQQ and IWM (SPY −17 % against −6 % from 12–1), and put sales sold then did worst on every ticker. These are averages without intervals.
3. **Where to sell.** About half of every same-day option is up 50 % at some point (47–55 %, every structure, every ticker). But 60–75 % of Steady options and spreads, and 85–92 % of Big Payoff options, are also down 50 % at some point, and the high comes first in 56–85 %.
   - No target, stop, time exit or trail had a 95 % lower bound above zero: 81 rules per ticker and structure, either period, any ticker.
   - Tight exits lose about the round-trip cost (SPY Steady call out after 15 minutes: −$3.0 / −$3.0 a contract).
   - Calls held to the 4:00 settlement were the best rule on most tickers (SPY Steady call +$8.2 / +$16), but every interval spans zero, and it is the period's rise, not the rule.
4. **Where to stop.** Stops make losses smaller, not the average better. On puts the quickest exit lost least: SPY Steady put out after 15 minutes −$3.6 / −$4.0, against −$21 / −$42 held to 3:30.
5. **Where to add.** Every add lost money on the added contract, on every ticker, in both periods:
   - SPY adding once the trade moves your way: −$8.8 / −$11;
   - doubling down at −25 %: −$6.1 / −$6.6;
   - scaling in by thirds: −$6.1 / −$9.8.
6. **Selling puts** gives the only same-day rows with a positive average:
   - a cash-secured put held to 4:00 (SPY +$21 / +$13, QQQ +$22 / +$28), or held with a stop at 2–3× the credit;
   - taking 25–50 % of the credit early turned every one of them negative;
   - every validation interval spans zero, and selling at a random minute earned the same (`07_validation.md` §4.1);
   - win rates of 85–93 % are not an edge, and one bad day can take months of credits.
7. **One week to a year out.**
   - Steady calls held to expiry made money on SPY and QQQ in both periods from Swing out (SPY LEAPS +$1,179 / +$3,660 a contract), but not on IWM in 2022–2023.
   - Steady puts held to expiry lost on every index fund in development, and in validation everywhere but the Weekly bucket. From Swing out, getting out after 5 sessions lost far less than holding.
   - Buying the same structure on random days earned the same (`06_daily_tier.md` §3–§7).

## 1. Where the day's high and low form (underlying, regular sessions, early closes left out)

{T1}

Half-hour detail: `results/playbook/day_shape_by_half_hour.csv`.

## 2. After a same-day entry: how high, how low, how soon (hindsight)

Typical price is per share (a contract is 100 shares; SPX contracts are 10× SPY's size). "Ever +50 %" means the position could have been sold at +50 % at some minute before 3:30. "Held to 3:30" is the average value at 3:30 against the price paid, before fees.

{T2}

Entries at a random later minute are in `results/playbook/after_entry.csv`. They enter later in the day, so they have less time for both highs and lows; compare them by hour (§5), not in this table.

## 3. Where to sell and where to stop: same-day rules, executable

Dollars a contract after the spread and fees, development (2022-11 → 2024) / validation (2025-01 → 2025-09). Every one of the 81 rules per row is in `results/playbook/exits.csv` with its 95 % interval.

{T3}

**Reading it:**
- **Tight exits:** 15 minutes, or a 20 % stop and 20 % target. They cost about one round trip and leave little else; that is the spread and fees, not a rule working.
- **Holding longer** spreads the outcomes wider without lifting the average.
- **The 4:00 settlement** is positive for calls on most tickers because the market rose; no interval excludes zero.
- **SPX dollars** are about 10× SPY's, and its validation figures swing with a few large days.

## 4. Where to add: executable

Dollars a trade earned by the added contracts alone (the first contract's result beside them), pooled over the six debit structures.

{T4}

## 5. Selling same-day puts: executable

{T5}

**Reading it:**
- **Holding to the settlement** collects the most premium, and its development interval is above zero on SPY, QQQ and IWM.
- **Stops at 2–3× the credit** keep most of it.
- **Taking 25–50 % of the credit early** gives up the winners' remaining premium while keeping the full losers: negative on every ticker.
- **No validation interval excludes zero.** On the hold-out, the same put sold at a random later minute earned within noise of the setups (`07_validation.md` §4.1).

## 6. When in the day to buy: spread and time decay

Spread is the median as a share of the price. "Held to 3:30" is the average result of an entry at a random minute in that hour, held to 3:30, before fees.

{T6}

Averages without intervals, so descriptive only. Steady calls bought 9:30–10:00 and held to 3:30 lost the most on SPY, QQQ and IWM (SPX's tied with 2–3). Put sales sold 9:30–10:00 did worst on every ticker. For Steady puts and Big Payoff calls the hour made no consistent difference.

## 7. One week to over a year out (daily tier)

After entry (hindsight; held to expiry is the average result against the price paid):

{T7}

Exits (dollars a contract; FB's validation is 2022's first half, so most of its cells have under 30 trades and show "—"):

{T8}

## 8. What else matters (what the question did not name)

- **The cost of the trade.** Spread and fees are about $3–4 a round trip on a SPY Steady contract, which is the whole loss of the tight exits. Big Payoff spreads are 3–8 % of the price each way.
- **Time decay.** Held to 3:30, the average same-day position lost 4–38 % of its price (T2), whichever way the view was.
- **The hindsight trap.** "Half of them go +50 %" is true and not tradeable: the same half often dips −50 % first or after, and nothing in these tests told which.
- **Direction.** 2013–2025 mostly rose, so calls, call spreads and put sales look good and puts look bad. That is the market, not a rule, and it reverses in a falling market (IWM's 2022–2023 rows, FB's 2022).
- **Size.** As portfolios (`08_portfolio.md`):
  - one cash-secured put at a time earned about 1 % a year on $100,000;
  - the put-spread portfolio at $1,000 risk a trade lost 9.6 % on the hold-out.
- **The same bet twice.** SPY, QQQ and SPX move together on most days. Three positions on one day are mostly one position.
- **Tail days.** Put sales win 85–93 % of the time and give back months of credits on a single day.
- **Event days** (Fed, CPI, earnings for single names) are not separated here. The Fed-day test is in `06_daily_tier.md` §6.

## Files

- `results/playbook/day_shape.csv`, `day_shape_by_half_hour.csv`: §1.
- `results/playbook/after_entry.csv`: §2, setup entries and random later minutes.
- `results/playbook/exits.csv`: §3–§5, all 81 same-day rules (adds' per-lot results included), with 95 % day-clustered intervals.
- `results/playbook/exits_random.csv`: the seven rules re-run on random later-minute entries.
- `results/playbook/entry_hour.csv`: §6.
- `results/playbook/daily_after.csv`, `daily_exits.csv`: §7.
