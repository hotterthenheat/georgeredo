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

| Ticker | Sessions | Median day range | Quiet day (25th pct) | Wild day (90th pct) | High set 9:30–10:00 | Low set 9:30–10:00 | First 30 min holds the high or low | High set after 3:00 | Low set after 3:00 | Close, share of the way up the range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SPY | 715 (2022-11 → 2025-09) | 0.90 % | 0.65 % | 1.75 % | 23 % | 27 % | 51 % | 30 % | 20 % | 61 % |
| QQQ | 715 (2022-11 → 2025-09) | 1.25 % | 0.94 % | 2.31 % | 29 % | 33 % | 62 % | 25 % | 19 % | 61 % |
| IWM | 359 (2024-04 → 2025-09) | 1.41 % | 1.10 % | 2.54 % | 36 % | 32 % | 67 % | 22 % | 14 % | 53 % |
| SPX | 841 (2022-05 → 2025-09) | 0.94 % | 0.65 % | 1.99 % | 24 % | 28 % | 51 % | 29 % | 22 % | 60 % |

Half-hour detail: `results/playbook/day_shape_by_half_hour.csv`.

## 2. After a same-day entry: how high, how low, how soon (hindsight)

Typical price is per share (a contract is 100 shares; SPX contracts are 10× SPY's size). "Ever +50 %" means the position could have been sold at +50 % at some minute before 3:30. "Held to 3:30" is the average value at 3:30 against the price paid, before fees.

| Ticker | Structure | Typical price | Spread | Ever +50 % | Ever +100 % | Minutes to the best (median) | Ever −50 % | Best came before worst | Held to 3:30, average | Green at 3:30 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SPY | Steady call | $1.21 | 1.0 % | 50 % | 27 % | 67 | 60 % | 60 % | −7 % | 38 % |
| SPY | Steady put | $1.28 | 1.0 % | 49 % | 29 % | 50 | 70 % | 67 % | −15 % | 30 % |
| SPY | Big Payoff call | $0.24 | 4.3 % | 49 % | 35 % | 30 | 85 % | 79 % | −21 % | 18 % |
| SPY | Big Payoff put | $0.30 | 3.4 % | 49 % | 34 % | 25 | 90 % | 84 % | −29 % | 15 % |
| SPY | Call debit spread | $0.71 | 3.0 % | 52 % | 27 % | 95 | 61 % | 56 % | −11 % | 41 % |
| SPY | Put debit spread | $0.67 | 2.5 % | 51 % | 30 % | 70 | 71 % | 64 % | −21 % | 33 % |
| QQQ | Steady call | $1.30 | 1.4 % | 50 % | 26 % | 64 | 61 % | 61 % | −10 % | 37 % |
| QQQ | Steady put | $1.38 | 1.4 % | 48 % | 29 % | 47 | 71 % | 69 % | −18 % | 29 % |
| QQQ | Big Payoff call | $0.27 | 4.1 % | 50 % | 34 % | 29 | 86 % | 81 % | −25 % | 18 % |
| QQQ | Big Payoff put | $0.33 | 3.4 % | 48 % | 34 % | 23 | 90 % | 85 % | −28 % | 14 % |
| QQQ | Call debit spread | $0.75 | 3.1 % | 52 % | 27 % | 91 | 62 % | 57 % | −16 % | 40 % |
| QQQ | Put debit spread | $0.71 | 2.7 % | 50 % | 29 % | 68 | 72 % | 65 % | −28 % | 31 % |
| IWM | Steady call | $0.89 | 2.7 % | 47 % | 25 % | 60 | 63 % | 61 % | −14 % | 36 % |
| IWM | Steady put | $0.91 | 2.8 % | 48 % | 29 % | 49 | 70 % | 69 % | −16 % | 30 % |
| IWM | Big Payoff call | $0.16 | 7.4 % | 47 % | 33 % | 23 | 90 % | 84 % | −38 % | 15 % |
| IWM | Big Payoff put | $0.18 | 6.5 % | 48 % | 35 % | 23 | 92 % | 84 % | −20 % | 14 % |
| IWM | Call debit spread | $0.41 | 5.1 % | 53 % | 32 % | 92 | 68 % | 58 % | −18 % | 38 % |
| IWM | Put debit spread | $0.38 | 4.7 % | 48 % | 31 % | 65 | 75 % | 67 % | −30 % | 30 % |
| SPX | Steady call | $10.40 | 1.8 % | 54 % | 33 % | 65 | 65 % | 61 % | −4 % | 38 % |
| SPX | Steady put | $11.10 | 1.8 % | 51 % | 33 % | 48 | 75 % | 69 % | −14 % | 29 % |
| SPX | Big Payoff call | $2.40 | 3.8 % | 52 % | 39 % | 33 | 88 % | 79 % | −14 % | 19 % |
| SPX | Big Payoff put | $2.90 | 3.6 % | 51 % | 37 % | 27 | 91 % | 84 % | −21 % | 14 % |
| SPX | Call debit spread | $5.95 | 3.5 % | 55 % | 31 % | 93 | 63 % | 56 % | −10 % | 42 % |
| SPX | Put debit spread | $5.80 | 3.4 % | 52 % | 33 % | 68 | 73 % | 63 % | −19 % | 34 % |

Entries at a random later minute are in `results/playbook/after_entry.csv`. They enter later in the day, so they have less time for both highs and lows; compare them by hour (§5), not in this table.

## 3. Where to sell and where to stop: same-day rules, executable

Dollars a contract after the spread and fees, development (2022-11 → 2024) / validation (2025-01 → 2025-09). Every one of the 81 rules per row is in `results/playbook/exits.csv` with its 95 % interval.

| Ticker | Structure | Hold to 3:30 | Hold to 4:00 | Out after 15 min | Out after 60 min | Stop −20 % / target +20 % | Stop −35 % / target +50 % | Target +50 %, no stop | Stop −50 %, no target | Trail: from +20 %, give back 25 % | Rules tested | Any with a lower bound above zero |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SPY | Steady call | −9.7 / −4.2 | +8.2 / +16 | −3.0 / −3.0 | −3.4 / −6.2 | −3.6 / −3.8 | −3.2 / −5.8 | −6.6 / −7.8 | −5.1 / −2.9 | −3.5 / −9.0 | 81 | none |
| SPY | Steady put | −21 / −42 | −44 / −31 | −3.6 / −4.0 | −6.4 / −13 | −4.1 / −4.2 | −7.2 / −8.6 | −13 / −23 | −16 / −25 | −4.7 / −8.2 | 81 | none |
| SPY | Big Payoff call | −6.0 / +2.4 | −0.5 / −2.0 | −2.7 / −3.0 | −3.3 / −4.9 | −2.6 / −3.1 | −2.9 / −3.8 | −4.9 / −5.9 | −3.1 / −1.0 | −2.9 / −3.5 | 81 | none |
| SPY | Big Payoff put | −11 / −13 | −19 / +0.7 | −2.7 / −3.1 | −4.0 / −7.3 | −2.9 / −3.0 | −3.4 / −3.5 | −6.3 / −9.4 | −6.3 / −8.6 | −3.1 / −4.1 | 81 | none |
| QQQ | Steady call | −10 / −23 | +11 / +11 | −3.8 / −2.7 | −4.4 / −7.0 | −4.3 / −4.7 | −2.9 / −8.7 | −6.9 / −8.4 | −5.2 / −22 | −2.7 / −12 | 81 | none |
| QQQ | Steady put | −27 / −37 | −48 / −11 | −4.6 / −3.4 | −7.9 / −10 | −4.6 / −4.5 | −9.6 / −7.5 | −18 / −16 | −19 / −28 | −7.5 / −5.4 | 81 | none |
| QQQ | Big Payoff call | −5.2 / −8.3 | +0.0 / +1.7 | −2.8 / −2.8 | −3.7 / −5.5 | −2.8 / −2.9 | −3.2 / −4.1 | −4.9 / −6.9 | −2.8 / −6.9 | −3.3 / −4.5 | 81 | none |
| QQQ | Big Payoff put | −11 / −11 | −19 / +11 | −3.0 / −2.4 | −4.2 / −5.4 | −2.9 / −3.2 | −3.7 / −4.3 | −7.4 / −7.4 | −7.4 / −8.1 | −3.6 / −3.6 | 81 | none |
| IWM | Steady call | −23 / −4.9 | +2.4 / +0.7 | −5.1 / −3.6 | −8.9 / −2.0 | −5.3 / −3.8 | −7.1 / −3.0 | −12 / −6.3 | −17 / −2.7 | −9.3 / −5.4 | 81 | none |
| IWM | Steady put | −6.6 / −27 | −27 / −17 | −4.0 / −5.6 | −2.8 / −8.2 | −5.1 / −6.3 | −6.7 / −8.4 | −11 / −18 | −3.8 / −14 | −3.6 / −7.1 | 81 | none |
| IWM | Big Payoff call | −12 / −2.2 | +0.6 / −2.7 | −2.8 / −2.5 | −4.8 / −1.4 | −2.8 / −2.7 | −2.8 / −2.9 | −5.6 / −3.6 | −7.4 / −1.1 | −3.7 / −3.2 | 81 | none |
| IWM | Big Payoff put | −3.0 / −7.3 | −11 / −0.3 | −2.5 / −3.0 | −1.6 / −3.3 | −2.8 / −3.0 | −2.9 / −3.8 | −5.0 / −5.5 | −3.0 / −4.3 | −2.6 / −3.3 | 81 | none |
| SPX | Steady call | −54 / +82 | +5.9 / +137 | −21 / −15 | −26 / −30 | −27 / −24 | −18 / −37 | −35 / −17 | −9.0 / +63 | −18 / −53 | 81 | none |
| SPX | Steady put | −175 / −260 | −145 / −256 | −32 / −32 | −69 / −76 | −33 / −24 | −64 / −38 | −124 / −176 | −131 / −111 | −39 / −39 | 81 | none |
| SPX | Big Payoff call | −40 / +59 | −19 / +79 | −14 / −13 | −21 / −28 | −13 / −15 | −16 / −22 | −30 / −30 | −14 / +18 | −19 / −23 | 81 | none |
| SPX | Big Payoff put | −81 / −73 | −69 / −125 | −16 / −20 | −32 / −42 | −17 / −15 | −23 / −21 | −46 / −63 | −46 / −40 | −21 / −29 | 81 | none |

**Reading it:**
- **Tight exits:** 15 minutes, or a 20 % stop and 20 % target. They cost about one round trip and leave little else; that is the spread and fees, not a rule working.
- **Holding longer** spreads the outcomes wider without lifting the average.
- **The 4:00 settlement** is positive for calls on most tickers because the market rose; no interval excludes zero.
- **SPX dollars** are about 10× SPY's, and its validation figures swing with a few large days.

## 4. Where to add: executable

Dollars a trade earned by the added contracts alone (the first contract's result beside them), pooled over the six debit structures.

| Ticker | First contract (no add) | Add once it moves your way | Double down at −25 % | Double down at −40 % | Scale in by thirds (the later two-thirds) |
| --- | --- | --- | --- | --- | --- |
| SPY | −12 / −16 | −8.8 / −11 | −6.1 / −6.6 | −4.4 / −5.7 | −6.1 / −9.8 |
| QQQ | −14 / −22 | −10 / −18 | −7.5 / −9.3 | −5.7 / −5.9 | −7.4 / −12 |
| IWM | −11 / −12 | −7.4 / −7.2 | −7.2 / −6.9 | −5.6 / −5.9 | −6.3 / −6.4 |
| SPX | −88 / −62 | −68 / −37 | −46 / −14 | −35 / −27 | −46 / −39 |

## 5. Selling same-day puts: executable

| Ticker | Structure | Hold to 4:00 | Take 25 % of the credit | Take 50 % | Take 50 %, or close if the strike is touched | Stop at 1.5× the credit | Stop at 2× | Stop at 3× | Win rate, hold to 4:00 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SPY | Cash-secured put | +21* / +13 | −2.2 / −6.2 | −1.2 / −6.4 | +0.4 / +0.3 | +3.3* / +3.0 | +5.4* / +5.4 | +6.7* / +8.8 | 89 % |
| SPY | Put credit spread | +8.2* / +2.3 | −4.7 / −6.8 | −4.6 / −6.9 | −3.2 / −3.7 | −3.7 / −4.3 | −2.4 / −3.6 | −1.9 / −2.5 | 93 % |
| QQQ | Cash-secured put | +22* / +28 | −1.6 / −1.1 | −1.2 / −4.4 | +1.8 / +0.8 | +4.0* / +4.4 | +5.8* / +4.9 | +6.9* / +9.8 | 89 % |
| QQQ | Put credit spread | +6.2* / +1.4 | −4.5 / −6.7 | −4.4 / −8.2 | −3.1 / −3.6 | −3.0 / −3.6 | −2.1 / −3.5 | −1.4 / −2.7 | 93 % |
| IWM | Cash-secured put | +15* / +2.4 | −0.9 / −2.9 | −4.6 / −4.4 | −2.9 / −1.6 | +0.0 / −0.8 | +1.9 / +0.6 | +3.0 / +0.8 | 85 % |
| IWM | Put credit spread | +8.3* / −2.1 | −5.1 / −6.0 | −6.0 / −6.6 | −5.1 / −4.8 | −4.7 / −4.3 | −4.0 / −4.0 | −3.8 / −3.0 | 89 % |
| SPX | Cash-secured put | +62 / +118 | −11 / −52 | −0.7 / −42 | +12 / +18 | +36* / +36 | +52* / +62 | +67* / +83 | 85 % |
| SPX | Put credit spread | +9.8 / +14 | −25 / −36 | −24 / −32 | −15 / −14 | −14 / −19 | −8.1 / −16 | −4.8 / −13 | 89 % |

**Reading it:**
- **Holding to the settlement** collects the most premium, and its development interval is above zero on SPY, QQQ and IWM.
- **Stops at 2–3× the credit** keep most of it.
- **Taking 25–50 % of the credit early** gives up the winners' remaining premium while keeping the full losers: negative on every ticker.
- **No validation interval excludes zero.** On the hold-out, the same put sold at a random later minute earned within noise of the setups (`07_validation.md` §4.1).

## 6. When in the day to buy: spread and time decay

Spread is the median as a share of the price. "Held to 3:30" is the average result of an entry at a random minute in that hour, held to 3:30, before fees.

| Ticker | Structure | Spread 9:30 | Spread 12:00 | Spread 3:00 | Held to 3:30 from 9:30–10 | from 10–11 | from 12–1 | from 2–3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| SPY | Steady call | 0.8 % | 1.1 % | 1.8 % | −17 % | −9 % | −6 % | −11 % |
| SPY | Steady put | 0.8 % | 1.1 % | 1.7 % | −14 % | −16 % | −14 % | −14 % |
| SPY | Big Payoff call | 3.2 % | 4.4 % | 8.0 % | −47 % | −18 % | −20 % | −30 % |
| SPY | Cash-secured put | 1.7 % | 2.3 % | 3.8 % | −1 % | +11 % | +3 % | +17 % |
| QQQ | Steady call | 1.1 % | 1.4 % | 2.2 % | −19 % | −5 % | −8 % | −17 % |
| QQQ | Steady put | 1.1 % | 1.4 % | 1.8 % | −28 % | −24 % | −17 % | −16 % |
| QQQ | Big Payoff call | 3.0 % | 4.3 % | 6.5 % | −33 % | −14 % | −19 % | −42 % |
| QQQ | Cash-secured put | 1.7 % | 2.4 % | 4.3 % | −32 % | +23 % | +3 % | +13 % |
| IWM | Steady call | 2.2 % | 3.0 % | 4.1 % | −32 % | −16 % | −17 % | −18 % |
| IWM | Steady put | 2.3 % | 2.9 % | 4.3 % | −19 % | −11 % | −14 % | −22 % |
| IWM | Big Payoff call | 5.4 % | 8.0 % | 8.0 % | −56 % | −39 % | −43 % | −46 % |
| IWM | Cash-secured put | 3.4 % | 4.9 % | 8.0 % | −23 % | −2 % | +2 % | −3 % |
| SPX | Steady call | 1.4 % | 1.8 % | 3.2 % | −11 % | −1 % | −4 % | −11 % |
| SPX | Steady put | 1.4 % | 1.8 % | 2.4 % | −10 % | −19 % | −11 % | −14 % |
| SPX | Big Payoff call | 3.4 % | 3.8 % | 6.1 % | −16 % | −3 % | −14 % | −26 % |
| SPX | Cash-secured put | 2.5 % | 3.1 % | 5.0 % | −8 % | +8 % | −1 % | +14 % |

Averages without intervals, so descriptive only. Steady calls bought 9:30–10:00 and held to 3:30 lost the most on SPY, QQQ and IWM (SPX's tied with 2–3). Put sales sold 9:30–10:00 did worst on every ticker. For Steady puts and Big Payoff calls the hour made no consistent difference.

## 7. One week to over a year out (daily tier)

After entry (hindsight; held to expiry is the average result against the price paid):

| Ticker | Expiry | Steady call: ever +50 % | ever −50 % | held to expiry, average | Steady put: ever +50 % | ever −50 % | held to expiry, average |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SPY | Weekly (1–7 days) | 42 % | 57 % | +7 % | 34 % | 71 % | −7 % |
| SPY | Swing (8–45) | 60 % | 62 % | +23 % | 42 % | 84 % | −30 % |
| SPY | Position (46–90) | 65 % | 61 % | +28 % | 41 % | 89 % | −41 % |
| SPY | Long-dated (91–269) | 78 % | 56 % | +53 % | 36 % | 88 % | −55 % |
| SPY | LEAPS (270+) | 80 % | 52 % | +101 % | 38 % | 86 % | −64 % |
| QQQ | Weekly (1–7 days) | 45 % | 54 % | +16 % | 35 % | 72 % | −7 % |
| QQQ | Swing (8–45) | 63 % | 60 % | +30 % | 43 % | 82 % | −31 % |
| QQQ | Position (46–90) | 69 % | 60 % | +40 % | 44 % | 85 % | −41 % |
| QQQ | Long-dated (91–269) | 81 % | 51 % | +93 % | 38 % | 89 % | −59 % |
| QQQ | LEAPS (270+) | 83 % | 51 % | +157 % | 33 % | 90 % | −69 % |
| IWM | Weekly (1–7 days) | 38 % | 62 % | −3 % | 37 % | 68 % | −8 % |
| IWM | Swing (8–45) | 54 % | 71 % | +1 % | 47 % | 78 % | −17 % |
| IWM | Position (46–90) | 57 % | 73 % | −0 % | 47 % | 81 % | −19 % |
| IWM | Long-dated (91–269) | 60 % | 76 % | +23 % | 44 % | 81 % | −30 % |
| IWM | LEAPS (270+) | 64 % | 76 % | +43 % | 45 % | 80 % | −43 % |
| FB | Weekly (1–7 days) | 40 % | 62 % | +18 % | 41 % | 65 % | +0 % |
| FB | Swing (8–45) | 56 % | 68 % | +10 % | 50 % | 77 % | −5 % |
| FB | Position (46–90) | 62 % | 68 % | +6 % | 49 % | 77 % | −5 % |
| FB | Long-dated (91–269) | 72 % | 73 % | +22 % | 47 % | 84 % | −21 % |
| FB | LEAPS (270+) | 93 % | 67 % | +102 % | 50 % | 96 % | −88 % |

Exits (dollars a contract; FB's validation is 2022's first half, so most of its cells have under 30 trades and show "—"):

| Ticker | Expiry | Steady call, hold to expiry | Steady call, out after 10 sessions | Steady put, hold to expiry | Steady put, out after 5 sessions | Cash-secured put, hold to expiry | Cash-secured put, take 50 % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SPY | Weekly (1–7 days) | +30* / −80 | +12 / −28 | −33 / −9.1 | −29 / −26 | +16 / −17 | +12 / +2.3 |
| SPY | Swing (8–45) | +118* / +24 | +52* / −68 | −233 / −225 | −70 / −57 | +97* / +53 | +63* / +56 |
| SPY | Position (46–90) | +195* / +58 | +52* / −76 | −418 / −534 | −72 / −63 | +180* / +188 | +152* / +97 |
| SPY | Long-dated (91–269) | +621* / +412 | +51* / −121 | −1,078 / −1,284 | −97 / −119 | +541* / +715* | +396* / +411* |
| SPY | LEAPS (270+) | +1,179* / +3,660* | +38* / −235 | −1,882 / −3,745 | −144 / −299 | +948* / +1,813* | +626* / +946* |
| QQQ | Weekly (1–7 days) | +22 / −59 | +12 / −24 | −21 / +26 | −35 / −13 | +14 / −23 | +14 / −13 |
| QQQ | Swing (8–45) | +111* / +85 | +52* / −19 | −185 / −38 | −52 / −4.7 | +92* / +101 | +64* / +26 |
| QQQ | Position (46–90) | +176* / +194 | +54* / −13 | −333 / −119 | −53 / −13 | +149* / +171 | +127* / +74 |
| QQQ | Long-dated (91–269) | +644* / +1,825* | +56* / −40 | −832 / −563 | −70 / −27 | +409* / +535* | +185* / +394* |
| QQQ | LEAPS (270+) | +1,384* / +5,156* | −1.6 / −75 | −1,176 / −3,104 | −170 / −111 | +458* / +1,466* | +233* / +654* |
| IWM | Weekly (1–7 days) | +8.1 / −44 | −1.7 / −19 | −23 / +1.8 | −22 / +3.9 | +10 / −12 | +9.5 / −15 |
| IWM | Swing (8–45) | +24 / −71 | +13 / −61 | −117 / −67 | −39 / −18 | +37 / −5.4 | +24 / +2.8 |
| IWM | Position (46–90) | +42 / −234 | +16 / −62 | −153 / −116 | −40 / −16 | +41 / +51 | +39 / +31 |
| IWM | Long-dated (91–269) | +259* / −675 | +13 / −77 | −355 / −430 | −56 / −40 | +220* / +534* | +156* / +323* |
| IWM | LEAPS (270+) | +427* / −552 | −38 / −159 | −653 / −1,347 | −154 / −190 | +332* / +996* | +233* / +525* |
| FB | Weekly (1–7 days) | +56 / — | +2.2 / — | −46 / +321 | −56 / +236 | +15 / −525 | +25 / −287 |
| FB | Swing (8–45) | +87 / — | −12 / — | −355 / +2,620* | −131 / +460 | +118 / −1,854 | +80 / −1,582 |
| FB | Position (46–90) | +19 / — | −2.0 / — | −312 / — | −131 / — | +38 / −2,271 | +15 / −2,197 |
| FB | Long-dated (91–269) | +326* / — | +12 / — | −519 / — | −146 / — | −96 / — | −103 / — |
| FB | LEAPS (270+) | +2,295* / — | −4.1 / — | −4,025 / — | −182 / — | +1,721* / — | +903* / — |

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
