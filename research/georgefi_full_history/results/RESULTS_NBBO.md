# GeorgeFi reported fills vs the ThetaData 1-second NBBO: results

Generated 2026-10-13 16:24 ET by code/nbbo_analyze.py from the cache written by code/nbbo_fetch.py. This extends RESULTS.md section B (Unusual Whales 1-minute bar ranges) with the measured NBBO at the reported second. Labels: **Reported by GeorgeFi** = the operator's ledger premiums and P&L; **Executable at NBBO (ours)** = the same trades filled at the ask (entry) and the bid (exit) prevailing at the reported second, $0.70/contract/side. Bootstrap CIs: 1000 resamples, numpy seed 7; "day CI" resamples ET entry days (clusters), "CI" resamples trades. E1 = Epoch 1 main book; E2 = Epoch 2 (all four books); paper = SPX paper book. Shares rows are priced on the stock NBBO (no fees).

## Summary (every number is copied from the tables below)

**Coverage.** E1: 542/546 rows (99.3 %) have a valid NBBO at both the entry and the exit second; entry quotes 542, exit quotes 544. E2: 594/603 rows (98.5 %) have a valid NBBO at both the entry and the exit second; entry quotes 599, exit quotes 594. Paper: 84/84 rows (100.0 %) have a valid NBBO at both the entry and the exit second; entry quotes 84, exit quotes 84. Missing reasons are in the coverage table (plain-`SPX` root = no data on ThetaData; entries/exits outside 09:30–16:00 ET carry an empty quote; the 3 open rows have no exit).

**Fill classification (Reported by GeorgeFi vs the NBBO at the reported second).** E1 (492 entries / 494 exits): entry at/below bid 33.5 % (below bid 31.3 %, at bid 2.2 %), inside 11.8 %, at mid 23.2 %, at ask 4.5 %, above ask 27.0 %; exit at/above ask 37.2 % (at ask 12.2 %, above ask 25.1 %), below bid 14.4 %; median entry position in the spread 0.5, exit 0.6; either side better than the market 58.1 % of rows with both quotes. E2 (599 / 594): entry at/below bid 33.6 % (below bid 29.4 %, at bid 4.2 %), inside 11.7 %, at mid 17.4 %, at ask 10.2 %, above ask 27.2 %; exit at/above ask 22.6 % (at ask 7.6 %, above ask 15.0 %), below bid 28.3 %; median entry position in the spread 0.5, exit 0.1; either side better than the market 47.1 % of rows with both quotes. Paper (84 / 84): entry at/below bid 19.1 % (below bid 11.9 %, at bid 7.1 %), inside 4.8 %, at mid 28.6 %, at ask 25.0 %, above ask 22.6 %; exit at/above ask 30.9 % (at ask 7.1 %, above ask 23.8 %), below bid 25.0 %; median entry position in the spread 0.75, exit 0.5; either side better than the market 46.4 % of rows with both quotes.

**Executable repricing (ours).** E1: 542 rows: reported 39,297 (all 546 rows of the epoch: 43,248; RESULTS.md A: 43,248) → executable at NBBO 12,039 (22.2/trade, day CI [-11.2, 66.2], trade CI [2.3, 42.1]; win rate 63.1 % vs reported 79.0 %; PF 1.47 vs 3.18); 1-second-later variant 11,530 on 542 rows; NBBO mid without costs 32,568; reported − executable 50.3/trade, day CI [30.9, 65.0], of which reported − NBBO mid 12.4/trade [-0.5, 25.7] and spread + fees 20,529 in total. On the 452 rows shared with RESULTS.md §B: reported 36,729, bar-VWAP mid 21,567, modelled spread 7,914, executable NBBO 18,256 (§B published on its 452 rows: reported 36,729, mid 21,567, spread 7,914, adverse -24,279). E2: 594 rows: reported -3,294 (all 603 rows of the epoch: -3,757; RESULTS.md A: -3,757) → executable at NBBO -24,988 (-42.1/trade, day CI [-78.8, -9.6], trade CI [-74.4, -7.3]; win rate 45.1 % vs reported 48.8 %; PF 0.63 vs 0.94); 1-second-later variant -24,275 on 594 rows; NBBO mid without costs -6,626; reported − executable 36.5/trade, day CI [22.4, 52.4], of which reported − NBBO mid 5.6/trade [-6.0, 18.7] and spread + fees 18,362 in total. On the 500 rows shared with RESULTS.md §B: reported 2,274, bar-VWAP mid -3,095, modelled spread -14,897, executable NBBO -15,127 (§B published on its 501 rows: reported 2,043, mid -3,098, spread -14,913, adverse -51,494). Paper: 84 rows: reported -3,632 (all 84 rows of the epoch: -3,632; RESULTS.md A: -3,632) → executable at NBBO -6,209 (-73.9/trade, day CI [-115.2, -29.6], trade CI [-115.3, -33.6]; win rate 36.9 % vs reported 38.1 %; PF 0.40 vs 0.61); 1-second-later variant -6,214 on 84 rows; NBBO mid without costs -4,865; reported − executable 30.7/trade, day CI [18.4, 47.2], of which reported − NBBO mid 14.7/trade [2.4, 30.7] and spread + fees 1,344 in total. On the 84 rows shared with RESULTS.md §B: reported -3,632, bar-VWAP mid -4,702, modelled spread -6,217, executable NBBO -6,209 (§B published on its 84 rows: reported -3,632, mid -4,702, spread -6,217, adverse -13,597).

**Spreads.** E1: median realized half-spread at entry 0.9 % of mid (mean 4.3 %, $0.025), at exit 0.9 % (mean 4.0 %). E2: median realized half-spread at entry 1.0 % of mid (mean 2.3 %, $0.045), at exit 1.0 % (mean 3.2 %). Paper: median realized half-spread at entry 1.2 % of mid (mean 1.8 %, $0.05), at exit 1.3 % (mean 1.8 %). Per root and per assumption bucket below (RESULTS.md §B used 1 % SPY/QQQ, 2 % IWM, 1.5 % index roots, 2 % single names).

**Epoch 1 same-minute repeats.** 372 rows in 97 same-contract-same-minute clusters (372 with quotes in the minute): the NBBO changed within the entry minute for 100.0 % (median 21.0 distinct NBBOs per minute); the reported entry premium equals a bid, ask or mid of some second in that minute for 57.0 % of rows, lies within [min bid, max ask] of the minute for 65.0 %, and is below the minute's lowest bid for 26.9 % (reported P&L of those rows 9,713). Non-repeated E1 rows: matches 66.7 %, below lowest bid 8.3 %.

## 1. Coverage

Rows: 1233 (ledger 1,149 + paper 84); contract-days 761; ThetaData 1-second quote requests 1699 ({'ok': 1689, 'nodata': 10}). Status per side: `ok` = valid NBBO row at the reported second (ask > 0, ask ≥ bid); `no_quote` = a row exists but bid/ask are 0 or empty (outside 09:30–16:00 ET); `nodata` = ThetaData has no quotes for the contract (plain-`SPX` root); `missing_second` = window returned but no row at that second; `no_exit` = open position.

| epoch | book | account | n | instrument | entry ok | exit ok | both ok | both ok (1 s later) | entry: no_quote / nodata / error / no_exit / not_fetched | exit: no_quote / nodata / error / no_exit / not_fetched | entry outside RTH | exit outside RTH | reported P&L (all rows) | reported P&L (both ok) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | ALL | ALL | 546 | 546 | 542 | 544 | 542 | 542 | 3 / 1 / 0 / 0 / 0 | 1 / 1 / 0 / 0 / 0 | 3 | 2 | 43,248 | 39,297 |
| E2 | ALL | ALL | 603 | 603 | 599 | 594 | 594 | 594 | 1 / 3 / 0 / 0 / 0 | 1 / 5 / 0 / 3 / 0 | 0 | 5 | -3,757 | -3,294 |
| paper | ALL | ALL | 84 | 84 | 84 | 84 | 84 | 84 | 0 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 / 0 | 0 | 0 | -3,632 | -3,632 |
| E1 | v2.0.0-ict | 0DTE | 373 | 373 | 369 | 371 | 369 | 369 | 3 / 1 / 0 / 0 / 0 | 1 / 1 / 0 / 0 / 0 | 3 | 2 | 37,026 | 33,075 |
| E1 | v2.0.0-ict | SWING | 173 | 173 | 173 | 173 | 173 | 173 | 0 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 / 0 | 0 | 0 | 6,222 | 6,222 |
| E2 | v2.0.0-ict | 0DTE | 429 | 429 | 425 | 425 | 425 | 425 | 1 / 3 / 0 / 0 / 0 | 1 / 3 / 0 / 0 / 0 | 0 | 0 | 3,221 | 3,462 |
| E2 | v2.0.0-ict | SWING | 60 | 60 | 60 | 60 | 60 | 60 | 0 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 / 0 | 0 | 2 | 752 | 752 |
| E2 | trade_now_v1 | 0DTE | 55 | 55 | 55 | 54 | 54 | 54 | 0 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 1 / 0 | 0 | 1 | -9,902 | -9,902 |
| E2 | singles_today_v1 | 0DTE | 29 | 29 | 29 | 27 | 27 | 27 | 0 / 0 / 0 / 0 / 0 | 0 / 2 / 0 / 0 / 0 | 0 | 2 | -1,132 | -910 |
| E2 | spx_plan_v1 | 0DTE | 11 | 11 | 11 | 11 | 11 | 11 | 0 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 / 0 | 0 | 0 | 3,015 | 3,015 |
| E2 | singles_today_v1 | SWING | 19 | 19 | 19 | 17 | 17 | 17 | 0 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 2 / 0 | 0 | 0 | 289 | 289 |
| paper | spx_gex_engine_paper | 0DTE | 84 | 84 | 84 | 84 | 84 | 84 | 0 / 0 / 0 / 0 / 0 | 0 / 0 / 0 / 0 / 0 | 0 | 0 | -3,632 | -3,632 |

### Coverage by OCC root (n ≥ 5)

| epoch | root | n | entry ok | exit ok | both ok | entry no_quote / nodata | exit no_quote / nodata |
|---|---|---|---|---|---|---|---|
| E1 | QQQ | 63 | 63 | 63 | 63 | 0 / 0 | 0 / 0 |
| E1 | IWM | 65 | 64 | 65 | 64 | 1 / 0 | 0 / 0 |
| E1 | COIN | 7 | 7 | 7 | 7 | 0 / 0 | 0 / 0 |
| E1 | ASTS | 5 | 5 | 5 | 5 | 0 / 0 | 0 / 0 |
| E1 | RKLB | 38 | 38 | 38 | 38 | 0 / 0 | 0 / 0 |
| E1 | CRM | 11 | 11 | 11 | 11 | 0 / 0 | 0 / 0 |
| E1 | SPXW | 59 | 59 | 59 | 59 | 0 / 0 | 0 / 0 |
| E1 | DIS | 11 | 11 | 11 | 11 | 0 / 0 | 0 / 0 |
| E1 | AAPL | 9 | 9 | 9 | 9 | 0 / 0 | 0 / 0 |
| E1 | SPY | 89 | 87 | 88 | 87 | 2 / 0 | 1 / 0 |
| E1 | RUTW | 8 | 8 | 8 | 8 | 0 / 0 | 0 / 0 |
| E1 | GOOG | 5 | 5 | 5 | 5 | 0 / 0 | 0 / 0 |
| E1 | GOOGL | 10 | 10 | 10 | 10 | 0 / 0 | 0 / 0 |
| E1 | AMZN | 32 | 32 | 32 | 32 | 0 / 0 | 0 / 0 |
| E1 | IBIT | 8 | 8 | 8 | 8 | 0 / 0 | 0 / 0 |
| E1 | INTC | 11 | 11 | 11 | 11 | 0 / 0 | 0 / 0 |
| E1 | HOOD | 9 | 9 | 9 | 9 | 0 / 0 | 0 / 0 |
| E1 | CRML | 18 | 18 | 18 | 18 | 0 / 0 | 0 / 0 |
| E1 | MSFT | 7 | 7 | 7 | 7 | 0 / 0 | 0 / 0 |
| E1 | SLV | 11 | 11 | 11 | 11 | 0 / 0 | 0 / 0 |
| E1 | BOIL | 9 | 9 | 9 | 9 | 0 / 0 | 0 / 0 |
| E1 | CRCL | 12 | 12 | 12 | 12 | 0 / 0 | 0 / 0 |
| E1 | NVDA | 18 | 18 | 18 | 18 | 0 / 0 | 0 / 0 |
| E2 | IWM | 34 | 34 | 34 | 34 | 0 / 0 | 0 / 0 |
| E2 | SPY | 70 | 70 | 70 | 70 | 0 / 0 | 0 / 0 |
| E2 | QQQ | 104 | 103 | 103 | 103 | 1 / 0 | 1 / 0 |
| E2 | SPXW | 208 | 208 | 207 | 207 | 0 / 0 | 0 / 0 |
| E2 | TSLA | 9 | 9 | 9 | 9 | 0 / 0 | 0 / 0 |
| E2 | AMZN | 9 | 9 | 9 | 9 | 0 / 0 | 0 / 0 |
| E2 | UCO | 5 | 5 | 5 | 5 | 0 / 0 | 0 / 0 |
| E2 | AVGO | 6 | 6 | 5 | 5 | 0 / 0 | 0 / 1 |
| E2 | AAPL | 5 | 5 | 5 | 5 | 0 / 0 | 0 / 0 |
| E2 | GLD | 19 | 19 | 18 | 18 | 0 / 0 | 0 / 1 |
| E2 | GOOGL | 13 | 13 | 13 | 13 | 0 / 0 | 0 / 0 |
| E2 | SLV | 5 | 5 | 5 | 5 | 0 / 0 | 0 / 0 |
| E2 | NDXP | 16 | 16 | 16 | 16 | 0 / 0 | 0 / 0 |
| E2 | RUTW | 23 | 23 | 23 | 23 | 0 / 0 | 0 / 0 |
| E2 | ROKU | 7 | 7 | 7 | 7 | 0 / 0 | 0 / 0 |
| E2 | ZM | 6 | 6 | 6 | 6 | 0 / 0 | 0 / 0 |
| E2 | META | 17 | 17 | 17 | 17 | 0 / 0 | 0 / 0 |
| paper | SPXW | 84 | 84 | 84 | 84 | 0 / 0 | 0 / 0 |

## 2. Fill classification: Reported by GeorgeFi vs the NBBO at the reported second

Classes of the reported premium p against the NBBO [bid, ask] at the reported second (q0 = last quote at or before HH:MM:SS): below bid (p < bid − $0.004), at bid (±$0.004), inside, at mid (±$0.01), at ask, above ask. Position = (p − bid)/(ask − bid). GeorgeFi is long: an entry at or below the bid, or an exit at or above the ask, is better than the market offered at that second. "1 s later" repeats the better-than-market share against the quote at HH:MM:SS+1 (the first snapshot that includes updates posted during the reported second).

| epoch | book | account | n entry | below bid | at bid | inside | at mid | at ask | above ask | entry ≤ bid | entry ≤ bid (1 s later) | median pos | n exit | below bid | at bid | inside | at mid | at ask | above ask | exit ≥ ask | exit ≥ ask (1 s later) | median pos | either side better (n both) | both within NBBO | reported P&L: either side better / neither side better |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | ALL | ALL | 492 | 31.3 % | 2.2 % | 11.8 % | 23.2 % | 4.5 % | 27.0 % | 33.5 % | 38.4 % | 0.5 | 494 | 14.4 % | 9.5 % | 19.6 % | 19.2 % | 12.2 % | 25.1 % | 37.2 % | 37.5 % | 0.6 | 58.1 % (492) | 27.4 % | 27,253 / 12,040 |
| E2 | ALL | ALL | 599 | 29.4 % | 4.2 % | 11.7 % | 17.4 % | 10.2 % | 27.2 % | 33.6 % | 33.2 % | 0.5 | 594 | 28.3 % | 21.6 % | 11.1 % | 16.5 % | 7.6 % | 15.0 % | 22.6 % | 24.6 % | 0.1 | 47.1 % (594) | 28.8 % | 10,479 / -13,772 |
| paper | ALL | ALL | 84 | 11.9 % | 7.1 % | 4.8 % | 28.6 % | 25.0 % | 22.6 % | 19.1 % | 27.4 % | 0.75 | 84 | 25.0 % | 2.4 % | 8.3 % | 33.3 % | 7.1 % | 23.8 % | 30.9 % | 33.3 % | 0.5 | 46.4 % (84) | 35.7 % | 2,182 / -5,815 |
| E1 | v2.0.0-ict | 0DTE | 369 | 27.1 % | 1.9 % | 8.7 % | 26.0 % | 4.3 % | 32.0 % | 29.0 % | 36.6 % | 0.5 | 371 | 16.4 % | 10.8 % | 14.3 % | 17.8 % | 14.3 % | 26.4 % | 40.7 % | 41.0 % | 0.6 | 56.6 % (369) | 25.5 % | 22,302 / 10,772 |
| E1 | v2.0.0-ict | SWING | 123 | 43.9 % | 3.2 % | 21.1 % | 14.6 % | 4.9 % | 12.2 % | 47.1 % | 43.9 % | 0.346 | 123 | 8.1 % | 5.7 % | 35.8 % | 23.6 % | 5.7 % | 21.1 % | 26.8 % | 26.8 % | 0.579 | 62.6 % (123) | 33.3 % | 4,950 / 1,268 |
| E2 | v2.0.0-ict | 0DTE | 425 | 33.7 % | 4.0 % | 11.8 % | 15.8 % | 5.2 % | 29.6 % | 37.6 % | 36.7 % | 0.5 | 425 | 30.8 % | 16.2 % | 10.6 % | 17.2 % | 8.5 % | 16.7 % | 25.2 % | 28.5 % | 0.25 | 52.7 % (425) | 22.6 % | 11,959 / -8,496 |
| E2 | v2.0.0-ict | SWING | 60 | 15.0 % | 3.3 % | 23.3 % | 53.3 % | 0.0 % | 5.0 % | 18.3 % | 20.0 % | 0.5 | 60 | 21.7 % | 31.7 % | 21.7 % | 13.3 % | 3.3 % | 8.3 % | 11.7 % | 13.3 % | 0.0 | 26.7 % (60) | 60.0 % | 416 / 337 |
| E2 | trade_now_v1 | 0DTE | 55 | 34.5 % | 5.5 % | 1.8 % | 5.5 % | 14.5 % | 38.2 % | 40.0 % | 41.8 % | 1.0 | 54 | 22.2 % | 13.0 % | 7.4 % | 22.2 % | 11.1 % | 24.1 % | 35.2 % | 31.5 % | 0.5 | 59.3 % (54) | 13.0 % | -4,568 / -5,335 |
| E2 | singles_today_v1 | 0DTE | 29 | 6.9 % | 6.9 % | 10.3 % | 3.5 % | 44.8 % | 27.6 % | 13.8 % | 10.3 % | 1.0 | 27 | 22.2 % | 63.0 % | 3.7 % | 11.1 % | 0.0 % | 0.0 % | 0.0 % | 0.0 % | 0.0 | 11.1 % (27) | 51.8 % | -74.0 / -836 |
| E2 | spx_plan_v1 | 0DTE | 11 | 18.2 % | 9.1 % | 0.0 % | 0.0 % | 54.5 % | 18.2 % | 27.3 % | 27.3 % | 1.0 | 11 | 36.4 % | 54.5 % | 0.0 % | 0.0 % | 9.1 % | 0.0 % | 9.1 % | 0.0 % | 0.0 | 36.4 % (11) | 54.5 % | 2,690 / 325 |
| E2 | singles_today_v1 | SWING | 19 | 5.3 % | 0.0 % | 10.5 % | 5.3 % | 63.2 % | 15.8 % | 5.3 % | 10.5 % | 1.0 | 17 | 11.8 % | 58.8 % | 17.6 % | 11.8 % | 0.0 % | 0.0 % | 0.0 % | 0.0 % | 0.0 | 5.9 % (17) | 70.6 % | 56.0 / 233 |
| paper | spx_gex_engine_paper | 0DTE | 84 | 11.9 % | 7.1 % | 4.8 % | 28.6 % | 25.0 % | 22.6 % | 19.1 % | 27.4 % | 0.75 | 84 | 25.0 % | 2.4 % | 8.3 % | 33.3 % | 7.1 % | 23.8 % | 30.9 % | 33.3 % | 0.5 | 46.4 % (84) | 35.7 % | 2,182 / -5,815 |
| E1 | v2.0.0-ict | SHARES (stock NBBO) | 50 | 38.0 % | 4.0 % | 4.0 % | 2.0 % | 4.0 % | 48.0 % | 42.0 % | 46.0 % | 1.005 | 50 | 28.0 % | 2.0 % | 6.0 % | 2.0 % | 2.0 % | 60.0 % | 62.0 % | 60.0 % | 3.671 | 78.0 % (50) | 4.0 % | 72.4 / -68.7 |

### Fill classification by OCC root (n entry ≥ 10)

| epoch | root | n entry | entry ≤ bid | entry inside/mid | entry ≥ ask | median entry pos | n exit | exit ≤ bid | exit inside/mid | exit ≥ ask | median exit pos |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | QQQ | 63 | 36.5 % | 25.4 % | 38.1 % | 0.5 | 63 | 39.7 % | 19.1 % | 41.3 % | 0.444 |
| E1 | IWM | 64 | 14.1 % | 46.9 % | 39.1 % | 0.5 | 65 | 32.3 % | 27.7 % | 40.0 % | 0.5 |
| E1 | RKLB | 34 | 50.0 % | 26.5 % | 23.5 % | -0.163 | 34 | 8.8 % | 76.5 % | 14.7 % | 0.5 |
| E1 | SPXW | 59 | 28.8 % | 40.7 % | 30.5 % | 0.5 | 59 | 33.9 % | 18.6 % | 47.5 % | 0.56 |
| E1 | DIS | 10 | 0.0 % | 90.0 % | 10.0 % | 0.5 | 10 | 10.0 % | 90.0 % | 0.0 % | 0.646 |
| E1 | SPY | 87 | 17.2 % | 33.3 % | 49.4 % | 0.75 | 88 | 25.0 % | 28.4 % | 46.6 % | 0.75 |
| E1 | AMZN | 30 | 46.7 % | 33.3 % | 20.0 % | 0.4 | 30 | 6.7 % | 53.3 % | 40.0 % | 0.65 |
| E1 | INTC | 11 | 100.0 % | 0.0 % | 0.0 % | -1.75 | 11 | 18.2 % | 81.8 % | 0.0 % | 0.4 |
| E1 | CRML | 16 | 12.5 % | 81.2 % | 6.2 % | 0.333 | 16 | 12.5 % | 81.2 % | 6.2 % | 0.6 |
| E1 | SLV | 11 | 27.3 % | 0.0 % | 72.7 % | 1.722 | 11 | 0.0 % | 54.5 % | 45.5 % | 0.727 |
| E1 | CRCL | 12 | 100.0 % | 0.0 % | 0.0 % | -0.564 | 12 | 0.0 % | 8.3 % | 91.7 % | 1.556 |
| E1 | NVDA | 18 | 55.6 % | 0.0 % | 44.4 % | -2.0 | 18 | 27.8 % | 22.2 % | 50.0 % | 0.75 |
| E2 | IWM | 34 | 38.2 % | 50.0 % | 11.8 % | 0.5 | 34 | 55.9 % | 23.5 % | 20.6 % | 0.0 |
| E2 | SPY | 70 | 42.9 % | 22.9 % | 34.3 % | 0.292 | 70 | 41.4 % | 22.9 % | 35.7 % | 0.5 |
| E2 | QQQ | 103 | 37.9 % | 14.6 % | 47.6 % | 0.667 | 103 | 49.5 % | 19.4 % | 31.1 % | 0.25 |
| E2 | SPXW | 208 | 40.9 % | 16.3 % | 42.8 % | 0.5 | 207 | 52.7 % | 17.9 % | 29.5 % | 0.0 |
| E2 | GLD | 19 | 0.0 % | 73.7 % | 26.3 % | 0.525 | 18 | 33.3 % | 66.7 % | 0.0 % | 0.288 |
| E2 | GOOGL | 13 | 7.7 % | 53.8 % | 38.5 % | 0.714 | 13 | 38.5 % | 53.8 % | 7.7 % | 0.5 |
| E2 | NDXP | 16 | 6.2 % | 75.0 % | 18.8 % | 0.583 | 16 | 75.0 % | 25.0 % | 0.0 % | 0.0 |
| E2 | RUTW | 23 | 21.7 % | 60.9 % | 17.4 % | 0.562 | 23 | 47.8 % | 47.8 % | 4.3 % | 0.1 |
| E2 | META | 17 | 47.1 % | 41.2 % | 11.8 % | 0.143 | 17 | 11.8 % | 88.2 % | 0.0 % | 0.5 |
| paper | SPXW | 84 | 19.1 % | 33.3 % | 47.6 % | 0.75 | 84 | 27.4 % | 41.7 % | 30.9 % | 0.5 |

Reported size vs displayed NBBO depth (option rows with both quotes): share of rows whose reported size exceeds the ask size at entry / the bid size at exit — E1 4.9 % / 4.1 % (n 492), E2 2.7 % / 1.8 % (n 594), paper 1.2 % / 0.0 % (n 84).

## 3. Executable repricing: Reported by GeorgeFi vs Executable at NBBO (ours)

Rows with a valid NBBO at both the entry and the exit second. Executable = buy at the ask of the entry second, sell at the bid of the exit second, reported size, $0.70/contract/side (shares: stock NBBO, no fees). "NBBO mid" = mid-to-mid, no costs (the NBBO analogue of §B's bar-VWAP `mid`). "1 s later" uses the quotes at HH:MM:SS+1. CIs: day = ET-entry-day cluster bootstrap; trade = plain bootstrap. The §B columns repeat RESULTS.md section B's bar-VWAP mid and modelled-spread P&L on the rows shared with that sample.

| epoch | book | account | n (days) | reported total | executable total | executable mean [day CI] [trade CI] | WR rep/exec | PF rep/exec | 1 s later: n / exec total | NBBO mid total | reported − exec mean [day CI] | reported − NBBO mid mean [day CI] | spread + fees total | §B rows: n / reported / bar mid / bar spread / exec NBBO | excl. data-error & mismatch: n / reported / exec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | ALL | ALL | 542 (28) | 39,297 | 12,039 | 22.2 [-11.2, 66.2] [2.3, 42.1] | 79.0 %/63.1 % | 3.18/1.47 | 542 / 11,530 | 32,568 | 50.3 [30.9, 65.0] | 12.4 [-0.5, 25.7] | 20,529 | 452 / 36,729 / 21,567 / 7,914 / 18,256 | 510 / 32,793 / 10,775 |
| E2 | ALL | ALL | 594 (132) | -3,294 | -24,988 | -42.1 [-78.8, -9.6] [-74.4, -7.3] | 48.8 %/45.1 % | 0.94/0.63 | 594 / -24,275 | -6,626 | 36.5 [22.4, 52.4] | 5.6 [-6.0, 18.7] | 18,362 | 500 / 2,274 / -3,095 / -14,897 / -15,127 | 586 / -3,912 / -24,966 |
| paper | ALL | ALL | 84 (38) | -3,632 | -6,209 | -73.9 [-115.2, -29.6] [-115.3, -33.6] | 38.1 %/36.9 % | 0.61/0.40 | 84 / -6,214 | -4,865 | 30.7 [18.4, 47.2] | 14.7 [2.4, 30.7] | 1,344 | 84 / -3,632 / -4,702 / -6,217 / -6,209 | 73 / -6,320 / -7,519 |
| E1 | v2.0.0-ict | ALL | 542 (28) | 39,297 | 12,039 | 22.2 [-11.2, 66.2] [2.3, 42.1] | 79.0 %/63.1 % | 3.18/1.47 | 542 / 11,530 | 32,568 | 50.3 [30.9, 65.0] | 12.4 [-0.5, 25.7] | 20,529 | 452 / 36,729 / 21,567 / 7,914 / 18,256 | 510 / 32,793 / 10,775 |
| E2 | v2.0.0-ict | ALL | 485 (114) | 4,215 | -11,142 | -23.0 [-41.5, -6.8] [-39.5, -5.9] | 52.2 %/47.6 % | 1.15/0.66 | 485 / -10,985 | 2,802 | 31.7 [16.7, 47.4] | 2.9 [-10.3, 16.0] | 13,944 | 397 / 6,559 / 1,597 / -6,340 / -4,483 | 478 / 3,512 / -11,207 |
| E2 | trade_now_v1 | ALL | 54 (35) | -9,902 | -15,631 | -289.5 [-552.6, 24.5] [-594.3, 12.5] | 25.9 %/29.6 % | 0.64/0.48 | 54 / -15,171 | -11,945 | 106.1 [31.4, 181.2] | 37.8 [-27.8, 107.4] | 3,686 | 52 / -6,768 / -7,391 / -10,558 / -12,527 | 54 / -9,902 / -15,631 |
| E2 | singles_today_v1 | ALL | 44 (7) | -621 | -779 | -17.7 [-45.1, 7.0] [-37.6, 1.8] | 38.6 %/34.1 % | 0.54/0.47 | 44 / -798 | -248 | 3.6 [1.8, 4.7] | -8.5 [-11.5, -6.5] | 531 | 40 / -533 / -37.0 / -423 / -681 | 44 / -621 / -779 |
| E2 | spx_plan_v1 | ALL | 11 (7) | 3,015 | 2,564 | 233.1 [-400.2, 732.4] [-276.5, 685.0] | 54.5 %/54.5 % | 2.26/1.96 | 11 / 2,679 | 2,765 | 41.0 [-10.6, 114.2] | 22.7 [-27.1, 91.8] | 201 | 11 / 3,015 / 2,736 / 2,424 / 2,564 | 10 / 3,100 / 2,650 |
| paper | spx_gex_engine_paper | ALL | 84 (38) | -3,632 | -6,209 | -73.9 [-115.2, -29.6] [-115.3, -33.6] | 38.1 %/36.9 % | 0.61/0.40 | 84 / -6,214 | -4,865 | 30.7 [18.4, 47.2] | 14.7 [2.4, 30.7] | 1,344 | 84 / -3,632 / -4,702 / -6,217 / -6,209 | 73 / -6,320 / -7,519 |
| E1 | v2.0.0-ict | 0DTE | 369 (25) | 33,075 | 14,168 | 38.4 [-9.9, 107.8] [7.7, 65.4] | 82.9 %/66.4 % | 3.62/1.76 | 369 / 13,352 | 25,762 | 51.2 [26.7, 73.3] | 19.8 [-0.2, 39.2] | 11,595 | 314 / 31,473 / 16,632 / 6,949 / 17,178 | 350 / 27,254 / 12,904 |
| E1 | v2.0.0-ict | SWING | 173 (10) | 6,222 | -2,129 | -12.3 [-34.5, -2.5] [-34.9, 6.0] | 70.5 %/56.1 % | 2.15/0.69 | 173 / -1,822 | 6,805 | 48.3 [15.5, 59.0] | -3.4 [-22.0, 5.6] | 8,934 | 138 / 5,256 / 4,935 / 965 / 1,078 | 160 / 5,539 / -2,130 |
| E2 | v2.0.0-ict | 0DTE | 425 (113) | 3,462 | -8,930 | -21.0 [-38.4, -4.4] [-40.0, -3.0] | 51.5 %/46.6 % | 1.14/0.68 | 425 / -8,799 | 1,130 | 29.2 [15.2, 44.7] | 5.5 [-8.0, 20.9] | 10,060 | 382 / 6,483 / 1,659 / -5,661 / -3,478 | 419 / 3,260 / -8,639 |
| E2 | v2.0.0-ict | SWING | 60 (28) | 752 | -2,212 | -36.9 [-89.6, 22.4] [-89.2, 8.5] | 56.7 %/55.0 % | 1.31/0.52 | 60 / -2,186 | 1,672 | 49.4 [-1.8, 106.6] | -15.3 [-47.1, 3.7] | 3,884 | 15 / 76.5 / -62.0 / -680 / -1,005 | 59 / 252 / -2,567 |
| E2 | trade_now_v1 | 0DTE | 54 (35) | -9,902 | -15,631 | -289.5 [-552.6, 24.5] [-594.3, 12.5] | 25.9 %/29.6 % | 0.64/0.48 | 54 / -15,171 | -11,945 | 106.1 [31.4, 181.2] | 37.8 [-27.8, 107.4] | 3,686 | 52 / -6,768 / -7,391 / -10,558 / -12,527 | 54 / -9,902 / -15,631 |
| E2 | singles_today_v1 | 0DTE | 27 (6) | -910 | -1,001 | -37.1 [-61.5, -2.2] [-63.8, -12.4] | 22.2 %/18.5 % | 0.23/0.22 | 27 / -979 | -656 | 3.4 [0.6, 5.0] | -9.4 [-13.4, -6.4] | 345 | 24 / -816 / -430 / -634 / -900 | 27 / -910 / -1,001 |
| E2 | spx_plan_v1 | 0DTE | 11 (7) | 3,015 | 2,564 | 233.1 [-400.2, 732.4] [-276.5, 685.0] | 54.5 %/54.5 % | 2.26/1.96 | 11 / 2,679 | 2,765 | 41.0 [-10.6, 114.2] | 22.7 [-27.1, 91.8] | 201 | 11 / 3,015 / 2,736 / 2,424 / 2,564 | 10 / 3,100 / 2,650 |
| E2 | singles_today_v1 | SWING | 17 (4) | 289 | 222 | 13.1 [8.6, 19.5] [-8.2, 35.7] | 64.7 %/58.8 % | 2.89/2.24 | 17 / 181 | 408 | 3.9 [2.8, 5.7] | -7.0 [-9.4, -5.0] | 186 | 16 / 283 / 393 / 211 / 219 | 17 / 289 / 222 |
| paper | spx_gex_engine_paper | 0DTE | 84 (38) | -3,632 | -6,209 | -73.9 [-115.2, -29.6] [-115.3, -33.6] | 38.1 %/36.9 % | 0.61/0.40 | 84 / -6,214 | -4,865 | 30.7 [18.4, 47.2] | 14.7 [2.4, 30.7] | 1,344 | 84 / -3,632 / -4,702 / -6,217 / -6,209 | 73 / -6,320 / -7,519 |

### Epoch totals side by side (same rows unless stated)

| epoch | rows | Reported by GeorgeFi (RESULTS.md A, all rows) | Reported on NBBO-covered rows | Executable at NBBO (ours) | Executable, 1 s later | NBBO mid, no costs | §B bar-VWAP mid (published, §B rows) | §B modelled spread (published, §B rows) | §B adverse (published, §B rows) |
|---|---|---|---|---|---|---|---|---|---|
| E1 | 542 | 43,248 (546 rows) | 39,297 | 12,039 | 11,530 (542 rows) | 32,568 | 21,567 (452 rows) | 7,914 | -24,279 |
| E2 | 594 | -3,757 (603 rows) | -3,294 | -24,988 | -24,275 (594 rows) | -6,626 | -3,098 (501 rows) | -14,913 | -51,494 |
| paper | 84 | -3,632 (84 rows) | -3,632 | -6,209 | -6,214 (84 rows) | -4,865 | -4,702 (84 rows) | -6,217 | -13,597 |

### Repricing by month

| epoch | month | n (days) | reported | executable | executable mean [day CI] | WR rep/exec | PF rep/exec | NBBO mid | 1 s later exec |
|---|---|---|---|---|---|---|---|---|---|
| E1 | 2026-01 | 279 (9) | 15,289 | -1,529 | -5.5 [-43.4, 30.9] | 79.9 %/54.5 % | 2.71/0.88 | 12,810 | -1,657 |
| E1 | 2026-02 | 263 (19) | 24,008 | 13,567 | 51.6 [1.8, 121.6] | 78.0 %/72.2 % | 3.65/2.10 | 19,758 | 13,187 |
| E2 | 2026-03 | 122 (22) | 1,677 | -4,183 | -34.3 [-85.5, 3.1] | 51.6 %/45.9 % | 1.22/0.57 | 384 | -3,974 |
| E2 | 2026-04 | 78 (20) | -159 | -261 | -3.3 [-32.7, 24.6] | 46.2 %/42.3 % | 0.94/0.91 | 670 | -244 |
| E2 | 2026-05 | 69 (16) | 1,745 | -68.0 | -1.0 [-48.7, 32.9] | 49.3 %/47.8 % | 1.35/0.99 | 1,120 | -211 |
| E2 | 2026-06 | 45 (15) | -3,497 | -4,733 | -105.2 [-177.3, -56.6] | 37.8 %/35.6 % | 0.35/0.20 | -2,604 | -4,747 |
| E2 | 2026-07 | 69 (19) | -7,372 | -15,105 | -218.9 [-440.6, -69.5] | 53.6 %/50.7 % | 0.62/0.33 | -10,454 | -14,698 |
| E2 | 2026-08 | 84 (15) | -1,788 | -5,409 | -64.4 [-157.0, -5.1] | 53.6 %/48.8 % | 0.78/0.43 | -3,385 | -5,383 |
| E2 | 2026-09 | 53 (17) | 2,875 | 2,254 | 42.5 [-40.1, 194.0] | 52.8 %/50.9 % | 1.83/1.64 | 3,426 | 2,353 |
| E2 | 2026-10 | 74 (8) | 3,225 | 2,517 | 34.0 [-72.7, 182.6] | 40.5 %/36.5 % | 1.44/1.33 | 4,217 | 2,629 |
| paper | 2026-07 | 9 (5) | -130 | -213 | -23.7 [-144.8, 37.1] | 44.4 %/44.4 % | 0.76/0.65 | -95.0 | -123 |
| paper | 2026-08 | 42 (17) | -2,910 | -3,554 | -84.6 [-137.8, -20.9] | 42.9 %/42.9 % | 0.45/0.36 | -2,868 | -3,674 |
| paper | 2026-09 | 29 (13) | -1,178 | -2,532 | -87.3 [-156.9, -23.3] | 31.0 %/27.6 % | 0.64/0.30 | -2,072 | -2,547 |
| paper | 2026-10 | 4 (3) | 585 | 90.2 | 22.6 [-237.8, 598.6] | 25.0 %/25.0 % | 3.85/1.18 | 170 | 130 |

### Repricing by OCC root (n ≥ 10)

| epoch | root | n | reported | executable | executable mean [day CI] | WR rep/exec | NBBO mid | reported − exec mean |
|---|---|---|---|---|---|---|---|---|
| E1 | QQQ | 63 | 4,144 | 2,008 | 31.9 [-6.2, 71.4] | 84.1 %/81.0 % | 2,900 | 33.9 |
| E1 | IWM | 64 | 3,318 | 2,529 | 39.5 [-8.5, 84.3] | 87.5 %/90.6 % | 3,178 | 12.3 |
| E1 | RKLB | 38 | 1,825 | -1,128 | -29.7 [-160.7, 10.4] | 89.5 %/47.4 % | 1,100 | 77.7 |
| E1 | CRM | 11 | -280 | -1,839 | -167.2 [-260.9, -8.6] | 54.5 %/27.3 % | -382 | 141.8 |
| E1 | SPXW | 59 | 20,715 | 11,688 | 198.1 [16.6, 532.5] | 84.8 %/79.7 % | 15,812 | 153.0 |
| E1 | DIS | 11 | 194 | -835 | -76.0 [-77.9, -67.2] | 63.6 %/0.0 % | 119 | 93.6 |
| E1 | SPY | 87 | 3,938 | 2,479 | 28.5 [-2.7, 59.1] | 75.9 %/72.4 % | 3,584 | 16.8 |
| E1 | GOOGL | 10 | -218 | -46.6 | -4.7 [-46.6, 25.4] | 70.0 %/50.0 % | 193 | -17.1 |
| E1 | AMZN | 32 | 964 | 180 | 5.6 [-1.1, 17.4] | 84.4 %/65.6 % | 855 | 24.5 |
| E1 | INTC | 11 | 448 | 23.2 | 2.1 [2.1, 2.1] | 90.9 %/81.8 % | 182 | 38.6 |
| E1 | CRML | 18 | -152 | -1,221 | -67.8 [-343.2, 16.9] | 83.3 %/11.1 % | 32.8 | 59.4 |
| E1 | SLV | 11 | 724 | 369 | 33.5 [-33.4, 58.6] | 100.0 %/63.6 % | 770 | 32.3 |
| E1 | CRCL | 12 | 627 | -1,174 | -97.8 [-97.8, -97.8] | 91.7 %/0.0 % | -589 | 150.1 |
| E1 | NVDA | 18 | 652 | 291 | 16.2 [-10.2, 36.8] | 100.0 %/66.7 % | 385 | 20.0 |
| E2 | IWM | 34 | 823 | 246 | 7.2 [-35.3, 47.8] | 61.8 %/55.9 % | 577 | 17.0 |
| E2 | SPY | 70 | 682 | -133 | -1.9 [-19.9, 17.0] | 54.3 %/48.6 % | 275 | 11.6 |
| E2 | QQQ | 103 | -1,032 | -1,802 | -17.5 [-32.2, -4.0] | 49.5 %/45.6 % | -1,173 | 7.5 |
| E2 | SPXW | 207 | -1,644 | -13,904 | -67.2 [-166.3, 20.2] | 44.9 %/45.9 % | -6,955 | 59.2 |
| E2 | GLD | 18 | -313 | -1,051 | -58.4 [-93.8, -29.3] | 33.3 %/16.7 % | -186 | 41.0 |
| E2 | GOOGL | 13 | 11.0 | -202 | -15.6 [-39.8, 19.9] | 46.2 %/23.1 % | 49.5 | 16.4 |
| E2 | NDXP | 16 | -3,405 | -4,360 | -272.5 [-453.9, -96.2] | 18.8 %/18.8 % | -1,862 | 59.7 |
| E2 | RUTW | 23 | 1,122 | -187 | -8.1 [-63.5, 53.1] | 60.9 %/39.1 % | 1,315 | 56.9 |
| E2 | META | 17 | 1,342 | 243 | 14.3 [-102.9, 84.4] | 70.6 %/70.6 % | 742 | 64.6 |
| paper | SPXW | 84 | -3,632 | -6,209 | -73.9 [-115.2, -29.6] | 38.1 %/36.9 % | -4,865 | 30.7 |

## 4. Realized half-spreads (ours) vs the assumptions in backtest/costs.py and RESULTS.md §B

Half-spread = (ask − bid)/2 at the reported second, in $ and as a share of the NBBO mid; "share above assumed" = rows whose realized half-spread (% of mid) exceeds the flat assumption used in §B (1 % SPY/QQQ, 2 % IWM, 1.5 % SPXW/NDXP/RUTW, 2 % single names).

| epoch | bucket | assumed | n entry | entry hs % median (mean) [p25, p75] | entry hs $ median | share above assumed | n exit | exit hs % median (mean) | exit hs $ median | share above assumed | median mid (entry) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | SPY/QQQ (assumed 1 %) | 1.0 % | 150 | 0.5 % (0.6 %) [0.4 %, 0.7 %] | 0.01 | 2.7 % | 151 | 0.5 % (0.6 %) | 0.01 | 0.7 % | 2.095 |
| E1 | IWM (assumed 2 %) | 2.0 % | 64 | 0.7 % (0.9 %) [0.5 %, 1.0 %] | 0.01 | 4.7 % | 65 | 0.8 % (1.0 %) | 0.015 | 3.1 % | 1.64 |
| E1 | single names (assumed 2 %) | 2.0 % | 211 | 4.1 % (7.8 %) [1.0 %, 9.0 %] | 0.055 | 64.9 % | 211 | 3.5 % (6.5 %) | 0.05 | 60.7 % | 1.68 |
| E1 | shares | n/a | 50 | 0.1 % (0.1 %) [0.0 %, 0.1 %] | 0.0325 | n/a | 50 | 0.0 % (0.0 %) | 0.01 | n/a | 111.843 |
| E1 | index (assumed 1.5 %) | 1.5 % | 67 | 1.2 % (4.9 %) [0.7 %, 2.7 %] | 0.1 | 34.3 % | 67 | 1.1 % (6.5 %) | 0.1 | 34.3 % | 6.95 |
| E2 | IWM (assumed 2 %) | 2.0 % | 34 | 0.9 % (1.1 %) [0.6 %, 1.1 %] | 0.025 | 11.8 % | 34 | 1.0 % (1.1 %) | 0.03 | 8.8 % | 2.51 |
| E2 | SPY/QQQ (assumed 1 %) | 1.0 % | 173 | 0.5 % (0.6 %) [0.4 %, 0.7 %] | 0.01 | 0.6 % | 173 | 0.5 % (0.6 %) | 0.01 | 1.7 % | 1.65 |
| E2 | index (assumed 1.5 %) | 1.5 % | 247 | 1.0 % (2.5 %) [0.7 %, 2.4 %] | 0.05 | 25.9 % | 246 | 1.2 % (3.6 %) | 0.05 | 33.3 % | 6.55 |
| E2 | single names (assumed 2 %) | 2.0 % | 145 | 3.5 % (4.3 %) [1.9 %, 5.6 %] | 0.045 | 73.1 % | 141 | 4.1 % (6.1 %) | 0.05 | 80.1 % | 1.575 |
| paper | index (assumed 1.5 %) | 1.5 % | 84 | 1.2 % (1.8 %) [1.0 %, 2.1 %] | 0.05 | 27.4 % | 84 | 1.3 % (1.8 %) | 0.05 | 22.6 % | 3.375 |

### By OCC root (n entry ≥ 5)

| epoch | root | assumed | n entry | entry hs % median (mean) | entry hs $ median | share above assumed | n exit | exit hs % median (mean) | exit hs $ median | median mid |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | ALL | n/a | 492 | 0.9 % (4.3 %) | 0.025 | n/a | 494 | 0.9 % (4.0 %) | 0.03 | 1.96 |
| E2 | ALL | n/a | 599 | 1.0 % (2.3 %) | 0.045 | n/a | 594 | 1.0 % (3.2 %) | 0.04 | 2.58 |
| paper | ALL | 1.5 % | 84 | 1.2 % (1.8 %) | 0.05 | 39.3 % | 84 | 1.3 % (1.8 %) | 0.05 | 3.375 |
| E1 | QQQ | 1.0 % | 63 | 0.5 % (0.7 %) | 0.01 | 12.7 % | 63 | 0.5 % (0.6 %) | 0.01 | 1.935 |
| E1 | IWM | 2.0 % | 64 | 0.7 % (0.9 %) | 0.01 | 4.7 % | 65 | 0.8 % (1.0 %) | 0.015 | 1.64 |
| E1 | COIN | 2.0 % | 7 | 4.3 % (5.0 %) | 0.04 | 85.7 % | 7 | 5.3 % (4.9 %) | 0.055 | 0.84 |
| E1 | ASTS | n/a | 5 | 0.2 % (1.8 %) | 0.225 | n/a | 5 | 0.1 % (1.7 %) | 0.165 | 109.16 |
| E1 | RKLB | 2.0 % | 38 | 5.9 % (8.6 %) | 0.11 | 89.5 % | 38 | 7.1 % (7.8 %) | 0.1 | 1.5 |
| E1 | CRM | n/a | 11 | 8.3 % (5.6 %) | 0.195 | n/a | 11 | 7.0 % (8.8 %) | 0.13 | 2.355 |
| E1 | SPXW | 1.5 % | 59 | 0.9 % (4.9 %) | 0.05 | 32.2 % | 59 | 0.9 % (6.8 %) | 0.05 | 7.05 |
| E1 | DIS | 2.0 % | 11 | 7.5 % (7.7 %) | 0.08 | 90.9 % | 11 | 6.5 % (6.1 %) | 0.075 | 1.07 |
| E1 | AAPL | n/a | 9 | 0.9 % (0.7 %) | 0.05 | n/a | 9 | 0.8 % (0.7 %) | 0.05 | 5.7 |
| E1 | SPY | 1.0 % | 87 | 0.5 % (0.6 %) | 0.01 | 8.1 % | 88 | 0.5 % (0.6 %) | 0.015 | 2.485 |
| E1 | RUTW | 1.5 % | 8 | 4.6 % (4.8 %) | 0.125 | 100.0 % | 8 | 4.2 % (4.1 %) | 0.1375 | 2.875 |
| E1 | GOOG | n/a | 5 | 1.8 % (1.5 %) | 0.075 | n/a | 5 | 1.7 % (1.4 %) | 0.075 | 4.175 |
| E1 | GOOGL | n/a | 10 | 0.9 % (1.5 %) | 0.025 | n/a | 10 | 1.5 % (2.0 %) | 0.0225 | 2.993 |
| E1 | AMZN | 2.0 % | 32 | 0.8 % (0.9 %) | 0.02 | 0.0 % | 32 | 1.0 % (1.0 %) | 0.025 | 2.71 |
| E1 | IBIT | 2.0 % | 8 | 2.1 % (2.0 %) | 0.01 | 87.5 % | 8 | 1.8 % (1.7 %) | 0.01 | 0.603 |
| E1 | INTC | 2.0 % | 11 | 2.6 % (2.8 %) | 0.04 | 100.0 % | 11 | 2.1 % (2.2 %) | 0.035 | 1.51 |
| E1 | HOOD | 2.0 % | 9 | 4.1 % (4.0 %) | 0.055 | 88.9 % | 9 | 5.2 % (5.2 %) | 0.055 | 1.345 |
| E1 | CRML | 2.0 % | 18 | 42.9 % (34.2 %) | 0.075 | 88.9 % | 18 | 25.0 % (22.2 %) | 0.05 | 0.175 |
| E1 | MSFT | 2.0 % | 7 | 0.8 % (0.6 %) | 0.05 | 0.0 % | 7 | 0.8 % (0.6 %) | 0.05 | 6.35 |
| E1 | SLV | 2.0 % | 11 | 4.1 % (3.8 %) | 0.09 | 100.0 % | 11 | 2.8 % (2.9 %) | 0.065 | 2.2 |
| E1 | BOIL | n/a | 9 | 0.1 % (0.1 %) | 0.02 | n/a | 9 | 0.0 % (0.0 %) | 0.01 | 35.82 |
| E1 | CRCL | 2.0 % | 12 | 14.4 % (14.4 %) | 0.275 | 100.0 % | 12 | 13.8 % (14.0 %) | 0.2 | 1.905 |
| E1 | NVDA | 2.0 % | 18 | 0.9 % (0.9 %) | 0.01 | 0.0 % | 18 | 0.8 % (0.7 %) | 0.01 | 1.06 |
| E2 | IWM | 2.0 % | 34 | 0.9 % (1.1 %) | 0.025 | 11.8 % | 34 | 1.0 % (1.1 %) | 0.03 | 2.51 |
| E2 | SPY | 1.0 % | 70 | 0.4 % (0.5 %) | 0.01 | 5.7 % | 70 | 0.4 % (0.5 %) | 0.01 | 2.055 |
| E2 | QQQ | 1.0 % | 103 | 0.5 % (0.6 %) | 0.01 | 13.6 % | 103 | 0.6 % (0.7 %) | 0.01 | 1.505 |
| E2 | SPXW | 1.5 % | 208 | 0.9 % (1.8 %) | 0.05 | 19.2 % | 207 | 1.0 % (2.8 %) | 0.05 | 6.475 |
| E2 | TSLA | 2.0 % | 9 | 1.6 % (1.5 %) | 0.015 | 44.4 % | 9 | 0.9 % (1.1 %) | 0.015 | 1.785 |
| E2 | AMZN | 2.0 % | 9 | 1.7 % (2.0 %) | 0.025 | 44.4 % | 9 | 2.3 % (2.3 %) | 0.025 | 1.03 |
| E2 | UCO | 2.0 % | 5 | 4.2 % (5.1 %) | 0.15 | 80.0 % | 5 | 3.4 % (6.2 %) | 0.15 | 4.25 |
| E2 | AVGO | 2.0 % | 6 | 1.8 % (2.3 %) | 0.015 | 16.7 % | 5 | 2.7 % (2.9 %) | 0.015 | 0.978 |
| E2 | AAPL | 2.0 % | 5 | 1.3 % (1.3 %) | 0.015 | 0.0 % | 5 | 1.6 % (2.2 %) | 0.02 | 1.905 |
| E2 | GLD | 2.0 % | 19 | 5.6 % (6.1 %) | 0.085 | 94.7 % | 18 | 6.7 % (10.1 %) | 0.105 | 1.535 |
| E2 | GOOGL | 2.0 % | 13 | 3.2 % (3.4 %) | 0.035 | 61.5 % | 13 | 2.8 % (4.3 %) | 0.025 | 1.1 |
| E2 | SLV | 2.0 % | 5 | 2.0 % (2.5 %) | 0.015 | 60.0 % | 5 | 4.1 % (4.1 %) | 0.02 | 0.49 |
| E2 | NDXP | 1.5 % | 16 | 7.5 % (7.7 %) | 0.65 | 100.0 % | 16 | 8.4 % (10.0 %) | 0.725 | 9.975 |
| E2 | RUTW | 1.5 % | 23 | 4.3 % (5.2 %) | 0.25 | 100.0 % | 23 | 4.9 % (6.2 %) | 0.3 | 6.0 |
| E2 | ROKU | 2.0 % | 7 | 6.0 % (6.0 %) | 0.045 | 100.0 % | 7 | 5.8 % (17.1 %) | 0.06 | 0.755 |
| E2 | ZM | 2.0 % | 6 | 6.7 % (6.7 %) | 0.12 | 100.0 % | 6 | 4.1 % (4.7 %) | 0.09 | 1.78 |
| E2 | META | 2.0 % | 17 | 3.5 % (3.8 %) | 0.105 | 94.1 % | 17 | 4.2 % (4.2 %) | 0.15 | 2.575 |
| paper | SPXW | 1.5 % | 84 | 1.2 % (1.8 %) | 0.05 | 39.3 % | 84 | 1.3 % (1.8 %) | 0.05 | 3.375 |

## 5. Epoch 1 same-contract-same-minute repeats vs the NBBO within the minute

For every ledger option row, all 1-second NBBO rows of the reported entry minute (up to 60). "repeat" = the row shares contract and entry minute with at least one other ledger row: 382 Epoch 1 rows (RESULTS.md: 382), of which 372 are option rows (the rest are share rows, listed in F_nbbo_repeats.csv with kind = stk but not summarised here); Epoch 2 52 rows. "matches any quote" = the reported entry premium equals the bid or ask (±$0.004) or the mid (±$0.01) of at least one second of that minute. Option rows only in this table.

| epoch | rows | n | with minute quotes | clusters | reported P&L | NBBO changed in minute | median distinct NBBOs | matches bid | matches ask | matches mid | matches any quote | within [min bid, max ask] | below min bid | above max ask | below min mid | reported P&L of rows below min bid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | single | 124 | 120 | 124 | 2,058 | 96.7 % | 21.0 | 25.0 % | 26.7 % | 61.7 % | 66.7 % | 77.5 % | 8.3 % | 14.2 % | 13.3 % | 2,402 |
| E1 | repeat | 372 | 372 | 97 | 41,187 | 100.0 % | 21.0 | 16.4 % | 14.2 % | 53.5 % | 57.0 % | 65.0 % | 26.9 % | 8.1 % | 32.8 % | 9,713 |
| E2 | single | 551 | 548 | 551 | -9,882 | 97.8 % | 18.0 | 32.3 % | 39.1 % | 79.4 % | 85.6 % | 88.3 % | 6.8 % | 4.9 % | 7.7 % | 10,624 |
| E2 | repeat | 52 | 52 | 14 | 6,125 | 88.5 % | 12.0 | 9.6 % | 17.3 % | 42.3 % | 42.3 % | 63.5 % | 36.5 % | 0.0 % | 48.1 % | 3,371 |

## 6. Interpretation

On the 542 Epoch 1 rows with an NBBO at both reported seconds, GeorgeFi reports 39,297; filled at the NBBO ask and bid of those same seconds the rows are worth 12,039 (22.2/trade, day-cluster CI [-11.2, 66.2]). The gap, 27,259 or 69.4 % of the reported total on these rows, is the fill assumption: 6,730 (17.1 %) comes from reported premiums better than the NBBO mid and 20,529 from crossing the realized spread plus fees. 33.5 % of Epoch 1 entries are at or below the bid and 37.2 % of exits at or above the ask; 58.1 % of rows have at least one fill better than the market offered at that second, and those rows carry 27,253 of reported P&L against 12,040 for the rows with no fill better than the market (fills within the NBBO or worse than it); 27.4 % of rows have both fills within the NBBO. The 1-second-later variant gives 11,530 on 542 rows, so the result does not hinge on sub-second timestamp alignment.

Epoch 2 (594 rows): reported -3,294 → executable -24,988 (-42.1/trade, day CI [-78.8, -9.6]); 33.6 % of entries at or below the bid, 22.6 % of exits at or above the ask. Paper (84 rows): reported -3,632 → executable -6,209; 19.1 % / 30.9 %.

What this does and does not show: the NBBO is the best displayed quote with its displayed size; a marketable order can fill inside the spread (price improvement, hidden liquidity, auctions) and a resting limit order can fill at the bid, so a reported entry at the bid is not impossible — but a record in which a large share of entries sit at or below the bid and exits at or above the ask is better than the market offered at those seconds, and the executable repricing is the number a taker would have obtained. Rows filled at the reported size could also exceed the displayed NBBO size (the size-vs-depth line in section 2). Nothing here speaks to signal quality; see RESULTS.md section C for that.

## METHODOLOGY

- **Timestamps.** Ledger `entryTime`/`exitTime` are UTC with milliseconds; converted to America/New_York. The reported second is HH:MM:SS (milliseconds truncated).
- **Quotes.** ThetaData `option_history_quote` / `stock_history_quote`, `interval='1s'`, root = OCC root (SPXW, RUTW, NDXP, SPY, QQQ, IWM, single names), strike as the plain number string (`'612.5'` for half strikes), one request per merged window [reported minute start − 10 s, reported second + 91 s] per contract-day (windows that overlap or touch are merged); 1699 requests, 2 concurrent, every response cached as gzip CSV under `$SP/theta/cache/georgefi_nbbo/` (never refetched; transport errors were retried with a fresh login). Per the ThetaData API description, the row stamped T "represents the last quote prior to the interval's timestamp", i.e. the NBBO prevailing at T.000. q0 = row at the reported second (the last quote at or before HH:MM:SS); q1 = row at HH:MM:SS+1 (the first snapshot that includes updates posted during the reported second). The true quote at HH:MM:SS.mmm lies between the two; the tables use q0 and show q1 as the "1 s later" variant. NDXP option quotes are served (the Nasdaq GIDS restriction in provider_audit.md applies to the NDX index price only); the plain-`SPX` root returns no data (4 rows; the SPXW twin is not substituted here).
- **Valid quote.** ask > 0 and ask ≥ bid (bid may be 0). Rows outside 09:30–16:00 ET usually carry 0/empty quotes and are counted as `no_quote`; rows after 16:00 that carry a quote (ETF options trade to 16:15) are used as found and flagged `exit_rth = False` in F_nbbo_trades.csv.
- **Classification.** below bid / at bid (±$0.004) / inside / at mid (±$0.01) / at ask (±$0.004) / above ask; position = (p − bid)/(ask − bid). Within-NBBO = at bid, inside, at mid or at ask.
- **Executable P&L.** (bid at exit second − ask at entry second) × 100 × reported size − 2 × $0.70 × size for options; (bid − ask) × shares for stock rows, no fees. NBBO-mid P&L = (mid_exit − mid_entry) × 100 × size, no fees. Rows with a valid quote at both seconds only; partial exits / scale-ins are priced at the ledger's final size and premiums exactly as §B does (P&L-mismatch rows are flagged and the totals are repeated without them).
- **Statistics.** Win rate = share of P&L > 0; PF = gross wins / gross losses; bootstrap 1000 resamples, `numpy.random.default_rng(7)` fresh per statistic; day CI resamples ET entry days with replacement and recomputes the per-trade mean.
- **Spreads.** Half-spread (ask − bid)/2 and its share of the mid at the reported second; medians and means by OCC root, epoch and §B assumption bucket.
- **Repeats.** All 1-second NBBO rows of the reported entry minute; cluster = contract + entry minute as in RESULTS.md.
- **Limitations.** The NBBO carries no depth beyond the displayed size at the best price (fills larger than the displayed size would walk the book; the displayed sizes are in F_nbbo_trades.csv). Index-option (SPXW/RUTW/NDXP) quotes update many times per second; a 1-second snapshot can miss a quote that existed for part of the second, which is why both q0 and q1 are shown. Quote timestamps are the SIP's; the ledger's clock is GeorgeFi's. Pre-market entries (3 rows, 2026-02-10) and the 4 plain-`SPX` rows cannot be checked. Shares rows use the consolidated stock NBBO (SIP), 50 rows. Nothing was tuned; every row is in F_nbbo_trades.csv.
- **Commands.** `set -a; . "$SP/secrets/research.env"; set +a; SP="$SP" python3 -I nbbo_fetch.py` then `SP="$SP" python3 -I nbbo_analyze.py` from `research/georgefi_full_history/code/`.
