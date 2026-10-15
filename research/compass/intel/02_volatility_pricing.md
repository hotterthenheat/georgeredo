# Market-intelligence brief — 2. Option pricing across the universe (V1) and the earnings volatility cycle (V2)

**The question (brief §4, §6, §14):** are options mispriced in a way that can be traded after the real bid/ask? Which names, and when?

These are the two option-pricing families the earlier research had not run. Both were pre-registered before any chain was pulled: `../04_protocol.md` A8, A8.1–A8.3c (V1) and A9 (V2). Code: `../studies/v1_vol_pricing.py`, `../studies/v2_earnings_vol.py`. Results: `../results/v1/v1_vol_pricing/`, `../results/v1/v2_earnings_vol/`.

## Data, and the checks run before any result was read

- **Quotes (OBSERVED).** Unusual Whales historical closing chains: one request per (ticker, date, expiration), paged at 500 contracts. Their bid/ask equal ThetaData's official closing NBBO on 638 of 638 contracts checked.
- **Underlying closes (OBSERVED).** ThetaData end-of-day, raw (not split-adjusted). They equal Unusual Whales' regular-session closes within 0.05 % on 99.0 % of 20,244 (ticker, expiration date) pairs.
- **Vendor IV and Greeks (MODELED by the vendor).** Used only to rank names, never to price a fill.
- **Pull:** 48,967 entry chains, every one answered; 60 chains cut at 500 contracts were completed by paging; 2,336 more chains were pulled for the corporate-action checks.
- **Corporate actions.** The rule was corrected three times before any outcome existed, each time because a test on known cases failed:
  - A8.1 removed a rule that would also have dropped genuine crashes.
  - A8.2 assumed the vendor's history was split-adjusted; CELH showed it is not consistently adjusted.
  - A8.3a is the final rule: on any session with a raw move of 1.4× or more, check whether the prior session's quoted contracts are still quoted. It classified DXCM, SMCI (twice), NVDA and WMT correctly.
  - A8.3b–c check the close against the chain's put-call-parity price.
- **What was excluded (V1):**

| Reason | Name-cycles |
|---|---|
| No two-sided ATM straddle within 5 % of the close (mostly illiquid chains) | 3,229 |
| Empty chain for the expiration | 770 |
| Corporate action in the window (A8.3a) | 265 |
| Ambiguous jump (A8.3a); kept in the sensitivity run | 147 |
| No close on the expiration date (delisted or acquired) | 70 |
| Entry close more than 5 % from the chain-implied price | 18 |
| Fewer than 21 returns before entry | 17 |
| Close is a data error on a jump session (A8.3b) | 4 |

  Built: **44,447 name-cycles**:
  - 34 monthly cycles from 2023-11 to 2026-09;
  - 1,086–1,700 names a cycle;
  - development 14 cycles, validation 12, hold-out 8. A8's text miscounted these as 13/12/9; the date rule it states is what ran.

## V1 — selling (or buying) the at-the-money monthly straddle, and sorting names by how expensive their options are

**Setup.** Each month, on the first session after the monthly expiration:
- **the trade:** the at-the-money straddle on the next monthly, sold at the closing bid or bought at the closing ask, $0.70 a contract a leg, held to expiration and settled at intrinsic against the close.
- **the result:** P&L as a share of the straddle's mid at entry.
- **the interval:** 95 %, by resampling months.

### T0 — is single-name volatility overpriced at all, net of the bid/ask?

| Sample | Months | Straddles | Short straddle, mean per month | 95 % interval |
|---|---|---|---|---|
| Development (2023-11 → 2024-12) | 14 | 15,731 | −7.3 % | [−17.8, +0.5] |
| Validation (2025) | 12 | 16,232 | −20.0 % | [−35.8, −7.1] |
| Development + validation | 26 | 31,963 | **−13.2 %** | [−22.3, −5.2] |
| Hold-out (2026-01 → 08) | 8 | 12,484 | **−23.6 %** | [−30.5, −16.9] |
| … stocks and ADRs (dev + val) | 26 | 26,330 | −13.1 % | [−21.6, −5.7] |
| … ETFs | 26 | 5,474 | −13.5 % | [−27.9, −0.7] |
| … an earnings report inside the month | 26 | 7,652 | −14.8 % | [−21.4, −8.9] |
| … no report inside the month | 26 | 24,311 | −12.4 % | [−23.8, −3.0] |

**Reading T0:**
- **The typical straddle does fine.** It wins 51 % of the time, with a median of +3 % of premium.
- **The tail sinks the average.** 5 % of straddles lost 168 % of their premium or more, and 13 % lost more than the whole premium.
- **The spread is large.** The straddle's median bid/ask spread is 13 % of its mid, so selling at the bid gives up about 6 %.
- **Net:** single-name monthly straddles were not overpriced once that is paid. It held in every sample and was worst in the 2026 hold-out.
- **The contrast with index puts.** S17's index put-writing earned the volatility premium on SPY and QQQ; individual names do not carry it after costs. This matches the published finding that the volatility premium is mainly an index phenomenon.
- **Premium against spread (exploratory, not pre-registered).**
  - **At the mid, the straddles are fairly priced on average.** Selling at the mid and settling at expiration made −0.6 % [−10.0, +7.3] in development + validation and −6.8 % [−14.0, +0.5] in the hold-out.
  - **The loss is the spread.** Half the spread is 12 % of the mid on average (16 % in the hold-out).
  - **By liquidity third (straddle spread 5.4 % / 12.8 % / 42.5 %):** at the mid −4.8 % / −1.7 % / +4.5 %; at the bid −8.2 % / −9.9 % / −22.7 %.
  - **What looks rich is untradeable.** The only premium at the mid is in the least liquid third, where the spread is ten times larger.

### T1 — does sorting on implied ÷ realized volatility find the overpriced ones?

By quintile of IV ÷ RV21, development + validation:

| Quintile | IV ÷ RV21 (median) | IV (median) | Realized vol over the month (median) | Implied minus realized over the month (mean, vol points) | Short straddle (mean) | Lost more than the premium | Spread (median) |
|---|---|---|---|---|---|---|---|
| 1 (cheapest) | 0.69 | 29.9 % | 28.3 % | −0.14 | −12.4 % | 13.6 % | 11.8 % |
| 2 | 0.91 | 29.2 % | 28.0 % | −0.14 | −14.2 % | 14.3 % | 12.2 % |
| 3 | 1.04 | 28.6 % | 27.0 % | +0.36 | −12.5 % | 13.8 % | 12.6 % |
| 4 | 1.19 | 29.0 % | 27.0 % | +0.77 | −13.4 % | 13.1 % | 12.3 % |
| 5 (richest) | 1.53 | 33.7 % | 30.2 % | **+2.34** | −9.9 % | 12.1 % | 11.7 % |

| Executable test | Development | Validation | Dev + val | Hold-out |
|---|---|---|---|---|
| Long-short: sell quintile 5 at the bid, buy quintile 1 at the ask | −16.2 % [−25.0, −5.8] | −23.3 % [−36.9, −4.8] | −19.5 % [−27.8, −9.4] | −28.5 % [−37.8, −20.3] |
| … one tick worse on every leg | | | −21.4 % | −30.3 % |
| Sell quintile 5 only | | | −9.6 % [−15.6, −4.5] | −21.9 % [−26.5, −17.0] |
| Quintile 5 short minus shorting every name | +1.8 % [−4.4, +9.6] | +3.7 % [−3.8, +13.7] | +2.7 % [−2.4, +8.7] | **−0.03 %** [−2.9, +2.9] |

**Reading T1:**
- **The signal is real at the level of volatility.** Names whose implied volatility is richest relative to their recent realized volatility did see less movement than implied over the next month: 2.3 vol points, against none for the cheapest quintile. This is the published result (Goyal & Saretto).
- **It is too small to trade.** Selling the richest quintile still lost money in every sample.
- **It does not beat selling everything.** The improvement over shorting every name is inside zero in development and validation, and exactly zero in the hold-out.
- **Buying the cheapest quintile at the ask also lost** (−9.9 % [−20.1, +2.1]): the spread is paid on both sides.
- **Verdict:** no edge. T1 fails its promotion rule.

### T2 — term slope

- **The signal:** ATM IV at the next monthly minus ATM IV at the entry monthly. "Expensive" means the near month is priced above the next (low or inverted slope).
- **Coverage:** 30,481 of 44,447 name-cycles had a two-sided ATM quote with vendor IV in both expirations (A8.4).

| Executable test | Development | Validation | Dev + val | Hold-out (7 months with enough names) |
|---|---|---|---|---|
| Long-short: sell the lowest-slope quintile at the bid, buy the highest at the ask | −23.7 % [−32.0, −15.4] | −20.5 % [−26.9, −13.3] | −22.2 % [−27.6, −16.8] | −16.5 % [−28.7, −2.3] |
| … one tick worse | | | −24.0 % | −18.2 % |
| Sell the lowest-slope quintile only | | | −12.7 % [−21.5, −5.3] | −16.0 % [−25.2, −5.0] |
| Lowest-slope short minus shorting every name | −3.8 % [−7.9, +0.3] | +2.0 % [−2.7, +6.6] | −1.1 % [−4.4, +2.2] | +4.4 % [−3.5, +13.3] |

No edge: T2 fails its promotion rule.

### T3 — skew

The direction was chosen on development: high put-over-call skew = expensive, long-short −10.0 % against −22.9 % the other way.

| Sample | Long-short | Expensive quintile minus shorting every name |
|---|---|---|
| Validation | −20.2 % [−36.2, −5.0] | −0.4 % [−7.3, +6.0] |
| Development + validation | −14.7 % [−23.5, −6.6] | +0.1 % [−3.6, +3.6] |
| Hold-out | −24.1 % [−37.5, −11.1] | +2.4 % [−4.0, +8.2] |

No edge: T3 fails its promotion rule.

### Sensitivity

Keeping the 147 ambiguous jumps changes nothing material:
- shorting every straddle: −13.3 % (development + validation) and −23.6 % (hold-out);
- the T1 long-short: −19.5 % and −28.5 %.

### Representative trades (point-in-time replays)

All at the closing quotes of the entry session, settled at the expiration close; dollars per straddle for the short side.

| Name | Entry → expiration | Close at entry | Strike | Call bid/ask | Put bid/ask | Close at expiration | Short P&L | Note |
|---|---|---|---|---|---|---|---|---|
| SPY | 2024-06-24 → 07-19 | 542.74 | 543 | 7.58 / 7.61 | 5.48 / 5.52 | 548.99 | +$706 | a typical month on the index fund |
| MSFT | 2024-06-24 → 07-19 | 447.67 | 447.50 | 8.95 / 9.25 | 6.90 / 7.20 | 437.11 | +$545 | |
| TSLA | 2024-06-24 → 07-19 | 182.58 | 182.50 | 9.50 / 9.80 | 8.60 / 8.75 | 239.20 | −$3,861 | a +31 % month: −211 % of premium |
| NVDA | 2025-06-23 → 07-18 | 144.17 | 144 | 5.10 / 5.15 | 4.45 / 4.50 | 172.41 | −$1,887 | |
| META | 2025-06-23 → 07-18 | 698.53 | 697.50 | 21.35 / 21.90 | 18.25 / 18.50 | 704.28 | +$3,281 | |
| MSTR | 2024-02-20 → 03-15 | 704.98 | 705 | 63.55 / 69.70 | 60.65 / 63.85 | 1,782.36 | −$95,317 | the bitcoin rally: −740 % of premium |
| SNDK | 2025-08-18 → 09-19 | 45.52 | 45 | 2.80 / 3.00 | 2.10 / 2.30 | 102.21 | −$5,232 | the worst in the sample: −1,026 % |
| SATS | 2025-08-18 → 09-19 | 27.87 | 28 | 2.10 / 2.25 | 2.15 / 2.25 | 72.47 | −$4,023 | the spectrum sale |
| SMCI | 2024-05-20 → 06-21 | 903.94 | 905 | 74.10 / 75.30 | 71.30 / 72.70 | 905.26 | +$14,513 | the best: pinned at the strike |

The losers are single months on single names that moved 30–150 %. They are what the short side collects its premium against, and they decide the average.

## V2 — the earnings volatility cycle

**Setup.**
- **Events:** 11,836 quarterly reports (pre- or post-market), from 2023-11-27 to 2026-09-30.
- **Names:** 1,587, meeting the liquidity rule at five sessions before the report.
- **Expiration:** the first Friday expiration on or after the report session that was listed five sessions before. 5,236 expire within the report week; 1,107 on the report session itself, settled at its close.
- **Excluded:** 34 events (28 with no listed expiration within 35 days, 3 missing closes, 3 corporate actions).
- **Trades:**
  - **V2a:** sell the ATM straddle at the close before the report session and buy it back at the report session's close (or settle that day);
  - **V2b:** buy the ATM straddle five sessions earlier and sell the same strike at the close before the report.
- **Interval:** 95 %, by resampling event weeks.

| Trade | Development (2023-11 → 2024-12) | Validation (2025) | Dev + val | Hold-out (2026-01 → 09) |
|---|---|---|---|---|
| V2a: sell across the report, % of premium | −23.9 % [−26.4, −20.9] (3,558) | −27.9 % [−31.4, −23.7] (4,244) | **−26.1 %** [−28.5, −23.3] (7,802) | **−34.2 %** [−37.1, −29.8] (3,682) |
| … one tick worse | | | −27.8 % | −35.9 % |
| V2b: buy into the report | −12.7 % [−14.5, −10.1] (3,485) | −28.0 % [−30.6, −24.4] (4,100) | **−20.9 %** [−23.9, −17.6] (7,585) | **−29.3 %** [−32.5, −25.4] (3,543) |
| … one tick worse | | | −22.7 % | −31.0 % |

Both fail their promotion rule in every sample. Neither holds a positive interval in any cut:

| Cut (development + validation) | V2a | V2b |
|---|---|---|
| Pre-market reports | −28.0 % | −21.6 % |
| Post-market reports | −23.8 % | −20.1 % |
| Implied move, lowest third / middle / highest | −31.8 % / −28.5 % / −17.8 % | |
| Straddle spread, tightest third / middle / widest | −11.9 % / −20.7 % / −45.5 % | −6.7 % / −16.0 % / −40.1 % |

**Why the report looks overpriced and still loses (development + validation):**
- **Reports usually move less than implied.** The median report moved 0.59 of the implied move (interquartile 0.26–1.07), and only 28 % moved more.
- **At the midpoint, sellers do earn something.** On the 782 reports whose expiration was the report session (no buy-back), selling at the mid and settling at the close earned **+6.9 %** of premium on average: median +21.6 %, won 60 % of the time.
- **The spread takes all of it.** Selling at the bid instead turns that into **−4.5 %** after fees, because half the 12.9 % median spread is larger than the premium.
- **Where trading is cheap, the premium is gone.** In the tightest-spread third (5.5 %), the premium is negative even at the mid (−4.0 %).
- **Net:** the earnings "overpricing" sits in the names whose spreads are too wide to capture it.
- **V2b:** the run-up in implied volatility into the report does not pay for five days of time decay plus a round trip of spread.

This last comparison is exploratory, not pre-registered. It explains the result and changes no verdict.

## Verdicts (pre-registered rules)

| Test | Verdict |
|---|---|
| V1 T0, single-name monthly straddles overpriced net of costs | No: negative in every sample |
| V1 T1, IV ÷ RV sort | No edge. The signal ranks forward volatility correctly but does not make selling pay, and adds nothing in the hold-out |
| V1 T2, term slope | No edge: long-short −22 % (dev + val), −17 % (hold-out); no improvement over selling everything |
| V1 T3, skew | No edge |
| V2a, sell earnings straddles across the report | No: −26 % (dev + val), −34 % (hold-out) |
| V2b, buy earnings straddles into the report | No: −21 % (dev + val), −29 % (hold-out) |
