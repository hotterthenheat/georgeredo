# GeorgeFi reported fills vs the ThetaData 1-second NBBO: results

Generated 2026-10-13 16:04 ET by code/nbbo_analyze.py from the cache written by code/nbbo_fetch.py. This extends RESULTS.md section B (Unusual Whales 1-minute bar ranges) with the measured NBBO at the reported second. Labels: **Reported by GeorgeFi** = the operator's ledger premiums and P&L; **Executable at NBBO (ours)** = the same trades filled at the ask (entry) and the bid (exit) prevailing at the reported second, $0.70/contract/side. Bootstrap CIs: 1000 resamples, numpy seed 7; "day CI" resamples ET entry days (clusters), "CI" resamples trades. E1 = Epoch 1 main book; E2 = Epoch 2 (all four books); paper = SPX paper book. Shares rows are priced on the stock NBBO (no fees).

## Summary (every number is copied from the tables below)

**Coverage.** E1: 517/546 rows (94.7 %) have a valid NBBO at both the entry and the exit second; entry quotes 527, exit quotes 533. E2: 67/603 rows (11.1 %) have a valid NBBO at both the entry and the exit second; entry quotes 78, exit quotes 78. Paper: 1/84 rows (1.2 %) have a valid NBBO at both the entry and the exit second; entry quotes 1, exit quotes 1. Missing reasons are in the coverage table (plain-`SPX` root = no data on ThetaData; entries/exits outside 09:30–16:00 ET carry an empty quote; the 3 open rows have no exit).

**Fill classification (Reported by GeorgeFi vs the NBBO at the reported second).** E1 (527 entries / 533 exits): entry at/below bid 35.3 % (below bid 32.8 %, at bid 2.5 %), inside 9.3 %, at mid 21.6 %, at ask 4.4 %, above ask 29.4 %; exit at/above ask 39.0 % (at ask 11.1 %, above ask 28.0 %), below bid 15.8 %; median entry position in the spread 0.5, exit 0.6; either side better than the market 61.3 % of rows with both quotes. E2 (78 / 78): entry at/below bid 41.0 % (below bid 37.2 %, at bid 3.9 %), inside 10.3 %, at mid 21.8 %, at ask 0.0 %, above ask 26.9 %; exit at/above ask 24.4 % (at ask 10.3 %, above ask 14.1 %), below bid 33.3 %; median entry position in the spread 0.5, exit 0.146; either side better than the market 50.7 % of rows with both quotes. Paper (1 / 1): entry at/below bid 0.0 % (below bid 0.0 %, at bid 0.0 %), inside 100.0 %, at mid 0.0 %, at ask 0.0 %, above ask 0.0 %; exit at/above ask 0.0 % (at ask 0.0 %, above ask 0.0 %), below bid 0.0 %; median entry position in the spread 0.75, exit 0.5; either side better than the market 0.0 % of rows with both quotes.

**Executable repricing (ours).** E1: 517 rows: reported 39,948 (all 546 rows of the epoch: 43,248; RESULTS.md A: 43,248) → executable at NBBO 13,064 (25.3/trade, day CI [-8.7, 70.4], trade CI [3.7, 47.5]; win rate 64.8 % vs reported 79.5 %; PF 1.54 vs 3.36); 1-second-later variant 12,545 on 517 rows; NBBO mid without costs 32,920; reported − executable 52.0/trade, day CI [30.1, 67.4], of which reported − NBBO mid 13.6/trade [-1.1, 27.3] and spread + fees 19,855 in total. On the 439 rows shared with RESULTS.md §B: reported 37,285, bar-VWAP mid 21,745, modelled spread 8,484, executable NBBO 18,674 (§B published on its 452 rows: reported 36,729, mid 21,567, spread 7,914, adverse -24,279). E2: 67 rows: reported 2,242 (all 603 rows of the epoch: -3,757; RESULTS.md A: -3,757) → executable at NBBO -2,737 (-40.9/trade, day CI [-124.0, 30.1], trade CI [-116.4, 33.3]; win rate 50.7 % vs reported 59.7 %; PF 0.63 vs 1.38); 1-second-later variant -2,762 on 67 rows; NBBO mid without costs 1,155; reported − executable 74.3/trade, day CI [-2.1, 149.4], of which reported − NBBO mid 16.2/trade [-33.6, 85.2] and spread + fees 3,892 in total. On the 57 rows shared with RESULTS.md §B: reported 1,582, bar-VWAP mid -606, modelled spread -3,156, executable NBBO -1,561 (§B published on its 501 rows: reported 2,043, mid -3,098, spread -14,913, adverse -51,494). Paper: 1 rows: reported -100 (all 84 rows of the epoch: -3,632; RESULTS.md A: -3,632) → executable at NBBO -113 (-112.8/trade, day CI [-112.8, -112.8], trade CI [-112.8, -112.8]; win rate 0.0 % vs reported 0.0 %; PF 0.00 vs 0.00); 1-second-later variant -103 on 1 rows; NBBO mid without costs -95.0; reported − executable 12.8/trade, day CI [12.8, 12.8], of which reported − NBBO mid -5.0/trade [-5.0, -5.0] and spread + fees 17.8 in total. On the 1 rows shared with RESULTS.md §B: reported -100, bar-VWAP mid -100, modelled spread -106, executable NBBO -113 (§B published on its 84 rows: reported -3,632, mid -4,702, spread -6,217, adverse -13,597).

**Spreads.** E1: median realized half-spread at entry 0.8 % of mid (mean 3.1 %, $0.025), at exit 0.8 % (mean 3.7 %). E2: median realized half-spread at entry 0.6 % of mid (mean 2.4 %, $0.02), at exit 0.7 % (mean 3.1 %). Paper: median realized half-spread at entry 7.1 % of mid (mean 7.1 %, $0.05), at exit 11.1 % (mean 11.1 %). Per root and per assumption bucket below (RESULTS.md §B used 1 % SPY/QQQ, 2 % IWM, 1.5 % index roots, 2 % single names).

**Epoch 1 same-minute repeats.** 372 rows in 97 same-contract-same-minute clusters (361 with quotes in the minute): the NBBO changed within the entry minute for 100.0 % (median 21 distinct NBBOs per minute); the reported entry premium equals a bid, ask or mid of some second in that minute for 55.7 % of rows, lies within [min bid, max ask] of the minute for 64.0 %, and is below the minute's lowest bid for 27.7 % (reported P&L of those rows 9,713). Non-repeated E1 rows: matches 66.4 %, below lowest bid 8.4 %.

## 1. Coverage

Rows: 1233 (ledger 1,149 + paper 84); contract-days 761; ThetaData 1-second quote requests 1699 ({'ok': 611, 'error': 1084, 'nodata': 4}). Status per side: `ok` = valid NBBO row at the reported second (ask > 0, ask ≥ bid); `no_quote` = a row exists but bid/ask are 0 or empty (outside 09:30–16:00 ET); `nodata` = ThetaData has no quotes for the contract (plain-`SPX` root); `missing_second` = window returned but no row at that second; `no_exit` = open position.

| epoch | book | account | n | instrument | entry ok | exit ok | both ok | both ok (1 s later) | entry: no_quote / nodata / error / no_exit / not_fetched | exit: no_quote / nodata / error / no_exit / not_fetched | entry outside RTH | exit outside RTH | reported P&L (all rows) | reported P&L (both ok) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | ALL | ALL | 546 | 546 | 527 | 533 | 517 | 517 | 3 / 1 / 15 / 0 / 0 | 1 / 1 / 11 / 0 / 0 | 3 | 2 | 43,248 | 39,948 |
| E2 | ALL | ALL | 603 | 603 | 78 | 78 | 67 | 67 | 1 / 1 / 523 / 0 / 0 | 1 / 1 / 520 / 3 / 0 | 0 | 5 | -3,757 | 2,242 |
| paper | ALL | ALL | 84 | 84 | 1 | 1 | 1 | 1 | 0 / 0 / 83 / 0 / 0 | 0 / 0 / 83 / 0 / 0 | 0 | 0 | -3,632 | -100 |
| E1 | v2.0.0-ict | 0DTE | 373 | 373 | 358 | 367 | 354 | 354 | 3 / 1 / 11 / 0 / 0 | 1 / 1 / 4 / 0 / 0 | 3 | 2 | 37,026 | 33,338 |
| E1 | v2.0.0-ict | SWING | 173 | 173 | 169 | 166 | 163 | 163 | 0 / 0 / 4 / 0 / 0 | 0 / 0 / 7 / 0 / 0 | 0 | 0 | 6,222 | 6,610 |
| E2 | v2.0.0-ict | 0DTE | 429 | 429 | 58 | 57 | 48 | 48 | 1 / 1 / 369 / 0 / 0 | 1 / 1 / 370 / 0 / 0 | 0 | 0 | 3,221 | 1,330 |
| E2 | v2.0.0-ict | SWING | 60 | 60 | 20 | 21 | 19 | 19 | 0 / 0 / 40 / 0 / 0 | 0 / 0 / 39 / 0 / 0 | 0 | 2 | 752 | 912 |
| E2 | trade_now_v1 | 0DTE | 55 | 55 | 0 | 0 | 0 | 0 | 0 / 0 / 55 / 0 / 0 | 0 / 0 / 54 / 1 / 0 | 0 | 1 | -9,902 | 0.0 |
| E2 | singles_today_v1 | 0DTE | 29 | 29 | 0 | 0 | 0 | 0 | 0 / 0 / 29 / 0 / 0 | 0 / 0 / 29 / 0 / 0 | 0 | 2 | -1,132 | 0.0 |
| E2 | spx_plan_v1 | 0DTE | 11 | 11 | 0 | 0 | 0 | 0 | 0 / 0 / 11 / 0 / 0 | 0 / 0 / 11 / 0 / 0 | 0 | 0 | 3,015 | 0.0 |
| E2 | singles_today_v1 | SWING | 19 | 19 | 0 | 0 | 0 | 0 | 0 / 0 / 19 / 0 / 0 | 0 / 0 / 17 / 2 / 0 | 0 | 0 | 289 | 0.0 |
| paper | spx_gex_engine_paper | 0DTE | 84 | 84 | 1 | 1 | 1 | 1 | 0 / 0 / 83 / 0 / 0 | 0 / 0 / 83 / 0 / 0 | 0 | 0 | -3,632 | -100 |

### Coverage by OCC root (n ≥ 5)

| epoch | root | n | entry ok | exit ok | both ok | entry no_quote / nodata | exit no_quote / nodata |
|---|---|---|---|---|---|---|---|
| E1 | QQQ | 63 | 63 | 62 | 62 | 0 / 0 | 0 / 0 |
| E1 | IWM | 65 | 64 | 62 | 61 | 1 / 0 | 0 / 0 |
| E1 | COIN | 7 | 7 | 7 | 7 | 0 / 0 | 0 / 0 |
| E1 | ASTS | 5 | 5 | 5 | 5 | 0 / 0 | 0 / 0 |
| E1 | RKLB | 38 | 38 | 38 | 38 | 0 / 0 | 0 / 0 |
| E1 | CRM | 11 | 10 | 10 | 9 | 0 / 0 | 0 / 0 |
| E1 | SPXW | 59 | 59 | 59 | 59 | 0 / 0 | 0 / 0 |
| E1 | DIS | 11 | 11 | 11 | 11 | 0 / 0 | 0 / 0 |
| E1 | AAPL | 9 | 9 | 9 | 9 | 0 / 0 | 0 / 0 |
| E1 | SPY | 89 | 87 | 88 | 87 | 2 / 0 | 1 / 0 |
| E1 | RUTW | 8 | 8 | 8 | 8 | 0 / 0 | 0 / 0 |
| E1 | GOOG | 5 | 5 | 5 | 5 | 0 / 0 | 0 / 0 |
| E1 | GOOGL | 10 | 10 | 10 | 10 | 0 / 0 | 0 / 0 |
| E1 | AMZN | 32 | 32 | 29 | 29 | 0 / 0 | 0 / 0 |
| E1 | IBIT | 8 | 8 | 8 | 8 | 0 / 0 | 0 / 0 |
| E1 | INTC | 11 | 11 | 11 | 11 | 0 / 0 | 0 / 0 |
| E1 | HOOD | 9 | 8 | 9 | 8 | 0 / 0 | 0 / 0 |
| E1 | CRML | 18 | 7 | 18 | 7 | 0 / 0 | 0 / 0 |
| E1 | MSFT | 7 | 7 | 7 | 7 | 0 / 0 | 0 / 0 |
| E1 | SLV | 11 | 11 | 11 | 11 | 0 / 0 | 0 / 0 |
| E1 | BOIL | 9 | 9 | 9 | 9 | 0 / 0 | 0 / 0 |
| E1 | CRCL | 12 | 12 | 12 | 12 | 0 / 0 | 0 / 0 |
| E1 | NVDA | 18 | 18 | 18 | 18 | 0 / 0 | 0 / 0 |
| E2 | IWM | 34 | 20 | 19 | 18 | 0 / 0 | 0 / 0 |
| E2 | SPY | 70 | 18 | 16 | 14 | 0 / 0 | 0 / 0 |
| E2 | QQQ | 104 | 11 | 15 | 10 | 1 / 0 | 1 / 0 |
| E2 | SPXW | 208 | 9 | 7 | 7 | 0 / 0 | 0 / 0 |
| E2 | TSLA | 9 | 3 | 3 | 3 | 0 / 0 | 0 / 0 |
| E2 | AMZN | 9 | 2 | 2 | 2 | 0 / 0 | 0 / 0 |
| E2 | UCO | 5 | 1 | 2 | 1 | 0 / 0 | 0 / 0 |
| E2 | AVGO | 6 | 1 | 1 | 1 | 0 / 0 | 0 / 0 |
| E2 | AAPL | 5 | 2 | 1 | 1 | 0 / 0 | 0 / 0 |
| E2 | GLD | 19 | 2 | 1 | 1 | 0 / 0 | 0 / 0 |
| E2 | GOOGL | 13 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| E2 | SLV | 5 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| E2 | NDXP | 16 | 1 | 1 | 1 | 0 / 0 | 0 / 0 |
| E2 | RUTW | 23 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| E2 | ROKU | 7 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| E2 | ZM | 6 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| E2 | META | 17 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| paper | SPXW | 84 | 1 | 1 | 1 | 0 / 0 | 0 / 0 |

## 2. Fill classification: Reported by GeorgeFi vs the NBBO at the reported second

Classes of the reported premium p against the NBBO [bid, ask] at the reported second (q0 = last quote at or before HH:MM:SS): below bid (p < bid − $0.004), at bid (±$0.004), inside, at mid (±$0.01), at ask, above ask. Position = (p − bid)/(ask − bid). GeorgeFi is long: an entry at or below the bid, or an exit at or above the ask, is better than the market offered at that second. "1 s later" repeats the better-than-market share against the quote at HH:MM:SS+1 (the first snapshot that includes updates posted during the reported second).

| epoch | book | account | n entry | below bid | at bid | inside | at mid | at ask | above ask | entry ≤ bid | entry ≤ bid (1 s later) | median pos | n exit | below bid | at bid | inside | at mid | at ask | above ask | exit ≥ ask | exit ≥ ask (1 s later) | median pos | either side better (n both) | both within NBBO | reported P&L either better / both within |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | ALL | ALL | 527 | 32.8 % | 2.5 % | 9.3 % | 21.6 % | 4.4 % | 29.4 % | 35.3 % | 40.2 % | 0.5 | 533 | 15.8 % | 8.8 % | 18.6 % | 17.8 % | 11.1 % | 28.0 % | 39.0 % | 39.0 % | 0.6 | 61.3 % (517) | 23.8 % | 28,199 / 11,749 |
| E2 | ALL | ALL | 78 | 37.2 % | 3.9 % | 10.3 % | 21.8 % | 0.0 % | 26.9 % | 41.0 % | 43.6 % | 0.5 | 78 | 33.3 % | 12.8 % | 17.9 % | 11.5 % | 10.3 % | 14.1 % | 24.4 % | 28.2 % | 0.146 | 50.7 % (67) | 22.4 % | 5,104 / -2,862 |
| paper | ALL | ALL | 1 | 0.0 % | 0.0 % | 100.0 % | 0.0 % | 0.0 % | 0.0 % | 0.0 % | 0.0 % | 0.75 | 1 | 0.0 % | 0.0 % | 0.0 % | 100.0 % | 0.0 % | 0.0 % | 0.0 % | 0.0 % | 0.5 | 0.0 % (1) | 100.0 % | 0.0 / -100 |
| E1 | v2.0.0-ict | 0DTE | 358 | 27.9 % | 2.0 % | 5.9 % | 26.8 % | 4.5 % | 33.0 % | 29.9 % | 37.7 % | 0.5 | 367 | 16.6 % | 10.6 % | 14.4 % | 18.0 % | 13.9 % | 26.4 % | 40.3 % | 40.6 % | 0.6 | 58.2 % (354) | 23.4 % | 22,660 / 10,678 |
| E1 | v2.0.0-ict | SWING | 169 | 43.2 % | 3.5 % | 16.6 % | 10.7 % | 4.1 % | 21.9 % | 46.8 % | 45.6 % | 0.346 | 166 | 13.9 % | 4.8 % | 27.7 % | 17.5 % | 4.8 % | 31.3 % | 36.1 % | 35.5 % | 0.6 | 68.1 % (163) | 24.5 % | 5,538 / 1,071 |
| E2 | v2.0.0-ict | 0DTE | 58 | 39.7 % | 1.7 % | 6.9 % | 19.0 % | 0.0 % | 32.8 % | 41.4 % | 44.8 % | 0.5 | 57 | 36.8 % | 14.0 % | 12.3 % | 10.5 % | 12.3 % | 14.0 % | 26.3 % | 33.3 % | 0.0 | 50.0 % (48) | 14.6 % | 4,656 / -3,326 |
| E2 | v2.0.0-ict | SWING | 20 | 30.0 % | 10.0 % | 20.0 % | 30.0 % | 0.0 % | 10.0 % | 40.0 % | 40.0 % | 0.478 | 21 | 23.8 % | 9.5 % | 33.3 % | 14.3 % | 4.8 % | 14.3 % | 19.1 % | 14.3 % | 0.333 | 52.6 % (19) | 42.1 % | 448 / 464 |
| paper | spx_gex_engine_paper | 0DTE | 1 | 0.0 % | 0.0 % | 100.0 % | 0.0 % | 0.0 % | 0.0 % | 0.0 % | 0.0 % | 0.75 | 1 | 0.0 % | 0.0 % | 0.0 % | 100.0 % | 0.0 % | 0.0 % | 0.0 % | 0.0 % | 0.5 | 0.0 % (1) | 100.0 % | 0.0 / -100 |

### Fill classification by OCC root (n entry ≥ 10)

| epoch | root | n entry | entry ≤ bid | entry inside/mid | entry ≥ ask | median entry pos | n exit | exit ≤ bid | exit inside/mid | exit ≥ ask | median exit pos |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | QQQ | 63 | 36.5 % | 25.4 % | 38.1 % | 0.5 | 62 | 40.3 % | 19.4 % | 40.3 % | 0.437 |
| E1 | IWM | 64 | 14.1 % | 46.9 % | 39.1 % | 0.5 | 62 | 32.3 % | 29.0 % | 38.7 % | 0.472 |
| E1 | RKLB | 38 | 55.3 % | 23.7 % | 21.1 % | -0.409 | 38 | 10.5 % | 68.4 % | 21.1 % | 0.54 |
| E1 | CRM | 10 | 30.0 % | 60.0 % | 10.0 % | 0.346 | 10 | 10.0 % | 60.0 % | 30.0 % | 0.6 |
| E1 | SPXW | 59 | 28.8 % | 40.7 % | 30.5 % | 0.5 | 59 | 33.9 % | 18.6 % | 47.5 % | 0.56 |
| E1 | DIS | 11 | 9.1 % | 81.8 % | 9.1 % | 0.5 | 11 | 9.1 % | 81.8 % | 9.1 % | 0.667 |
| E1 | SPY | 87 | 17.2 % | 33.3 % | 49.4 % | 0.75 | 88 | 25.0 % | 28.4 % | 46.6 % | 0.75 |
| E1 | GOOGL | 10 | 70.0 % | 0.0 % | 30.0 % | -0.7 | 10 | 20.0 % | 40.0 % | 40.0 % | 0.548 |
| E1 | AMZN | 32 | 46.9 % | 31.2 % | 21.9 % | 0.4 | 29 | 6.9 % | 51.7 % | 41.4 % | 0.7 |
| E1 | INTC | 11 | 100.0 % | 0.0 % | 0.0 % | -1.75 | 11 | 18.2 % | 81.8 % | 0.0 % | 0.4 |
| E1 | SLV | 11 | 27.3 % | 0.0 % | 72.7 % | 1.722 | 11 | 0.0 % | 54.5 % | 45.5 % | 0.727 |
| E1 | CRCL | 12 | 100.0 % | 0.0 % | 0.0 % | -0.564 | 12 | 0.0 % | 8.3 % | 91.7 % | 1.556 |
| E1 | NVDA | 18 | 55.6 % | 0.0 % | 44.4 % | -2.0 | 18 | 27.8 % | 22.2 % | 50.0 % | 0.75 |
| E2 | IWM | 20 | 40.0 % | 40.0 % | 20.0 % | 0.458 | 19 | 57.9 % | 21.1 % | 21.1 % | 0.0 |
| E2 | SPY | 18 | 55.6 % | 27.8 % | 16.7 % | -0.667 | 16 | 43.8 % | 31.2 % | 25.0 % | 0.333 |
| E2 | QQQ | 11 | 18.2 % | 18.2 % | 63.6 % | 2.5 | 15 | 46.7 % | 13.3 % | 40.0 % | 0.5 |

Reported size vs displayed NBBO depth (option rows with both quotes): share of rows whose reported size exceeds the ask size at entry / the bid size at exit — E1 5.1 % / 4.2 % (n 472), E2 13.4 % / 0.0 % (n 67), paper 0.0 % / 0.0 % (n 1).

## 3. Executable repricing: Reported by GeorgeFi vs Executable at NBBO (ours)

Rows with a valid NBBO at both the entry and the exit second. Executable = buy at the ask of the entry second, sell at the bid of the exit second, reported size, $0.70/contract/side (shares: stock NBBO, no fees). "NBBO mid" = mid-to-mid, no costs (the NBBO analogue of §B's bar-VWAP `mid`). "1 s later" uses the quotes at HH:MM:SS+1. CIs: day = ET-entry-day cluster bootstrap; trade = plain bootstrap. The §B columns repeat RESULTS.md section B's bar-VWAP mid and modelled-spread P&L on the rows shared with that sample.

| epoch | book | account | n (days) | reported total | executable total | executable mean [day CI] [trade CI] | WR rep/exec | PF rep/exec | 1 s later: n / exec total | NBBO mid total | reported − exec mean [day CI] | reported − NBBO mid mean [day CI] | spread + fees total | §B rows: n / reported / bar mid / bar spread / exec NBBO | excl. data-error & mismatch: n / reported / exec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | ALL | ALL | 517 (28) | 39,948 | 13,064 | 25.3 [-8.7, 70.4] [3.7, 47.5] | 79.5 %/64.8 % | 3.36/1.54 | 517 / 12,545 | 32,920 | 52.0 [30.1, 67.4] | 13.6 [-1.1, 27.3] | 19,855 | 439 / 37,285 / 21,745 / 8,484 / 18,674 | 486 / 33,444 / 11,793 |
| E2 | ALL | ALL | 67 (17) | 2,242 | -2,737 | -40.9 [-124.0, 30.1] [-116.4, 33.3] | 59.7 %/50.7 % | 1.38/0.63 | 67 / -2,762 | 1,155 | 74.3 [-2.1, 149.4] | 16.2 [-33.6, 85.2] | 3,892 | 57 / 1,582 / -606 / -3,156 / -1,561 | 62 / 1,878 / -2,801 |
| paper | ALL | ALL | 1 (1) | -100 | -113 | -112.8 [-112.8, -112.8] [-112.8, -112.8] | 0.0 %/0.0 % | 0.00/0.00 | 1 / -103 | -95.0 | 12.8 [12.8, 12.8] | -5.0 [-5.0, -5.0] | 17.8 | 1 / -100 / -100 / -106 / -113 | 1 / -100 / -113 |
| E1 | v2.0.0-ict | ALL | 517 (28) | 39,948 | 13,064 | 25.3 [-8.7, 70.4] [3.7, 47.5] | 79.5 %/64.8 % | 3.36/1.54 | 517 / 12,545 | 32,920 | 52.0 [30.1, 67.4] | 13.6 [-1.1, 27.3] | 19,855 | 439 / 37,285 / 21,745 / 8,484 / 18,674 | 486 / 33,444 / 11,793 |
| E2 | v2.0.0-ict | ALL | 67 (17) | 2,242 | -2,737 | -40.9 [-124.0, 30.1] [-116.4, 33.3] | 59.7 %/50.7 % | 1.38/0.63 | 67 / -2,762 | 1,155 | 74.3 [-2.1, 149.4] | 16.2 [-33.6, 85.2] | 3,892 | 57 / 1,582 / -606 / -3,156 / -1,561 | 62 / 1,878 / -2,801 |
| paper | spx_gex_engine_paper | ALL | 1 (1) | -100 | -113 | -112.8 [-112.8, -112.8] [-112.8, -112.8] | 0.0 %/0.0 % | 0.00/0.00 | 1 / -103 | -95.0 | 12.8 [12.8, 12.8] | -5.0 [-5.0, -5.0] | 17.8 | 1 / -100 / -100 / -106 / -113 | 1 / -100 / -113 |
| E1 | v2.0.0-ict | 0DTE | 354 (25) | 33,338 | 14,667 | 41.4 [-9.9, 111.4] [12.9, 72.0] | 82.5 %/68.4 % | 3.72/1.81 | 354 / 13,867 | 26,088 | 52.7 [26.9, 75.8] | 20.5 [-0.6, 40.1] | 11,421 | 310 / 31,814 / 17,004 / 7,375 / 17,578 | 335 / 27,517 / 13,404 |
| E1 | v2.0.0-ict | SWING | 163 (10) | 6,610 | -1,603 | -9.8 [-29.2, 3.2] [-30.7, 10.0] | 73.0 %/57.1 % | 2.42/0.73 | 163 / -1,322 | 6,832 | 50.4 [13.8, 63.9] | -1.4 [-24.6, 4.9] | 8,435 | 129 / 5,471 / 4,741 / 1,108 / 1,097 | 151 / 5,927 / -1,611 |
| E2 | v2.0.0-ict | 0DTE | 48 (15) | 1,330 | -872 | -18.2 [-122.3, 59.3] [-116.7, 66.0] | 60.4 %/52.1 % | 1.27/0.80 | 48 / -884 | 337 | 45.9 [-24.4, 152.7] | 20.7 [-49.8, 119.5] | 1,209 | 47 / 1,257 / -769 / -2,768 / -879 | 44 / 1,467 / -581 |
| E2 | v2.0.0-ict | SWING | 19 (7) | 912 | -1,865 | -98.2 [-203.6, 101.0] [-245.7, 27.3] | 57.9 %/47.4 % | 1.96/0.39 | 19 / -1,878 | 818 | 146.1 [35.2, 207.0] | 4.9 [-19.7, 40.0] | 2,683 | 10 / 324 / 163 / -388 / -682 | 18 / 410 / -2,220 |
| paper | spx_gex_engine_paper | 0DTE | 1 (1) | -100 | -113 | -112.8 [-112.8, -112.8] [-112.8, -112.8] | 0.0 %/0.0 % | 0.00/0.00 | 1 / -103 | -95.0 | 12.8 [12.8, 12.8] | -5.0 [-5.0, -5.0] | 17.8 | 1 / -100 / -100 / -106 / -113 | 1 / -100 / -113 |

### Epoch totals side by side (same rows unless stated)

| epoch | rows | Reported by GeorgeFi (RESULTS.md A, all rows) | Reported on NBBO-covered rows | Executable at NBBO (ours) | Executable, 1 s later | NBBO mid, no costs | §B bar-VWAP mid (published, §B rows) | §B modelled spread (published, §B rows) | §B adverse (published, §B rows) |
|---|---|---|---|---|---|---|---|---|---|
| E1 | 517 | 43,248 (546 rows) | 39,948 | 13,064 | 12,545 (517 rows) | 32,920 | 21,567 (452 rows) | 7,914 | -24,279 |
| E2 | 67 | -3,757 (603 rows) | 2,242 | -2,737 | -2,762 (67 rows) | 1,155 | -3,098 (501 rows) | -14,913 | -51,494 |
| paper | 1 | -3,632 (84 rows) | -100 | -113 | -103 (1 rows) | -95.0 | -4,702 (84 rows) | -6,217 | -13,597 |

### Repricing by month

| epoch | month | n (days) | reported | executable | executable mean [day CI] | WR rep/exec | PF rep/exec | NBBO mid | 1 s later exec |
|---|---|---|---|---|---|---|---|---|---|
| E1 | 2026-01 | 263 (9) | 15,386 | -1,448 | -5.5 [-47.0, 32.0] | 79.8 %/56.6 % | 2.82/0.89 | 12,508 | -1,597 |
| E1 | 2026-02 | 254 (19) | 24,562 | 14,512 | 57.1 [6.0, 124.5] | 79.1 %/73.2 % | 3.91/2.28 | 20,412 | 14,143 |
| E2 | 2026-03 | 65 (16) | 1,792 | -3,292 | -50.6 [-146.0, 16.0] | 60.0 %/50.8 % | 1.31/0.55 | 474 | -3,257 |
| E2 | 2026-05 | 2 (1) | 450 | 555 | 277.6 [277.6, 277.6] | 50.0 %/50.0 % | 13.86/13.79 | 680 | 495 |
| paper | 2026-07 | 1 (1) | -100 | -113 | -112.8 [-112.8, -112.8] | 0.0 %/0.0 % | 0.00/0.00 | -95.0 | -103 |

### Repricing by OCC root (n ≥ 10)

| epoch | root | n | reported | executable | executable mean [day CI] | WR rep/exec | NBBO mid | reported − exec mean |
|---|---|---|---|---|---|---|---|---|
| E1 | QQQ | 62 | 4,524 | 2,451 | 39.5 [-2.2, 85.7] | 85.5 %/82.3 % | 3,324 | 33.4 |
| E1 | IWM | 61 | 3,279 | 2,485 | 40.7 [-10.2, 85.7] | 86.9 %/90.2 % | 3,126 | 13.0 |
| E1 | RKLB | 38 | 1,825 | -1,128 | -29.7 [-160.7, 10.4] | 89.5 %/47.4 % | 1,100 | 77.7 |
| E1 | SPXW | 59 | 20,715 | 11,688 | 198.1 [16.6, 532.5] | 84.8 %/79.7 % | 15,812 | 153.0 |
| E1 | DIS | 11 | 194 | -835 | -76.0 [-77.9, -67.2] | 63.6 %/0.0 % | 119 | 93.6 |
| E1 | SPY | 87 | 3,938 | 2,479 | 28.5 [-2.7, 59.1] | 75.9 %/72.4 % | 3,584 | 16.8 |
| E1 | GOOGL | 10 | -218 | -46.6 | -4.7 [-46.6, 25.4] | 70.0 %/50.0 % | 193 | -17.1 |
| E1 | AMZN | 29 | 1,425 | 443 | 15.3 [4.4, 22.6] | 89.7 %/65.5 % | 897 | 33.9 |
| E1 | INTC | 11 | 448 | 23.2 | 2.1 [2.1, 2.1] | 90.9 %/81.8 % | 182 | 38.6 |
| E1 | SLV | 11 | 724 | 369 | 33.5 [-33.4, 58.6] | 100.0 %/63.6 % | 770 | 32.3 |
| E1 | CRCL | 12 | 627 | -1,174 | -97.8 [-97.8, -97.8] | 91.7 %/0.0 % | -589 | 150.1 |
| E1 | NVDA | 18 | 652 | 291 | 16.2 [-10.2, 36.8] | 100.0 %/66.7 % | 385 | 20.0 |
| E2 | IWM | 18 | 532 | 76.6 | 4.3 [-52.3, 64.1] | 50.0 %/44.4 % | 272 | 25.3 |
| E2 | SPY | 14 | 950 | 485 | 34.7 [-48.5, 105.9] | 71.4 %/64.3 % | 654 | 33.2 |
| E2 | QQQ | 10 | -558 | -208 | -20.8 [-97.3, 48.2] | 60.0 %/60.0 % | -124 | -35.0 |

## 4. Realized half-spreads (ours) vs the assumptions in backtest/costs.py and RESULTS.md §B

Half-spread = (ask − bid)/2 at the reported second, in $ and as a share of the NBBO mid; "share above assumed" = rows whose realized half-spread (% of mid) exceeds the flat assumption used in §B (1 % SPY/QQQ, 2 % IWM, 1.5 % SPXW/NDXP/RUTW, 2 % single names).

| epoch | bucket | assumed | n entry | entry hs % median (mean) [p25, p75] | entry hs $ median | share above assumed | n exit | exit hs % median (mean) | exit hs $ median | share above assumed | median mid (entry) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | SPY/QQQ (assumed 1 %) | 1.0 % | 150 | 0.5 % (0.6 %) [0.4 %, 0.7 %] | 0.01 | 2.7 % | 150 | 0.5 % (0.6 %) | 0.01 | 0.7 % | 2.095 |
| E1 | IWM (assumed 2 %) | 2.0 % | 64 | 0.7 % (0.9 %) [0.5 %, 1.0 %] | 0.01 | 4.7 % | 62 | 0.8 % (1.0 %) | 0.015 | 3.2 % | 1.64 |
| E1 | single names (assumed 2 %) | 2.0 % | 199 | 3.5 % (5.9 %) [0.9 %, 8.3 %] | 0.05 | 62.8 % | 207 | 3.8 % (6.6 %) | 0.05 | 61.8 % | 1.845 |
| E1 | shares | n/a | 47 | 0.1 % (0.1 %) [0.0 %, 0.1 %] | 0.035 | n/a | 47 | 0.0 % (0.0 %) | 0.01 | n/a | 112.255 |
| E1 | index (assumed 1.5 %) | 1.5 % | 67 | 1.2 % (4.9 %) [0.7 %, 2.7 %] | 0.1 | 34.3 % | 67 | 1.1 % (6.5 %) | 0.1 | 34.3 % | 6.95 |
| E2 | IWM (assumed 2 %) | 2.0 % | 20 | 0.7 % (1.1 %) [0.5 %, 1.2 %] | 0.02 | 15.0 % | 19 | 1.0 % (1.2 %) | 0.02 | 10.5 % | 2.25 |
| E2 | SPY/QQQ (assumed 1 %) | 1.0 % | 29 | 0.5 % (0.5 %) [0.4 %, 0.6 %] | 0.01 | 0.0 % | 31 | 0.4 % (0.5 %) | 0.01 | 0.0 % | 2.6 |
| E2 | index (assumed 1.5 %) | 1.5 % | 10 | 0.6 % (1.2 %) [0.5 %, 0.9 %] | 0.125 | 10.0 % | 8 | 0.6 % (1.1 %) | 0.15 | 12.5 % | 15.525 |
| E2 | single names (assumed 2 %) | 2.0 % | 19 | 2.4 % (7.2 %) [1.4 %, 4.7 %] | 0.09 | 52.6 % | 20 | 2.3 % (9.6 %) | 0.065 | 55.0 % | 2.765 |
| paper | index (assumed 1.5 %) | 1.5 % | 1 | 7.1 % (7.1 %) [7.1 %, 7.1 %] | 0.05 | 100.0 % | 1 | 11.1 % (11.1 %) | 0.025 | 100.0 % | 0.7 |

### By OCC root (n entry ≥ 5)

| epoch | root | assumed | n entry | entry hs % median (mean) | entry hs $ median | share above assumed | n exit | exit hs % median (mean) | exit hs $ median | median mid |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | ALL | n/a | 527 | 0.8 % (3.1 %) | 0.025 | n/a | 533 | 0.8 % (3.7 %) | 0.025 | 2.08 |
| E2 | ALL | n/a | 78 | 0.6 % (2.4 %) | 0.02 | n/a | 78 | 0.7 % (3.1 %) | 0.025 | 2.685 |
| E1 | QQQ | 1.0 % | 63 | 0.5 % (0.7 %) | 0.01 | 12.7 % | 62 | 0.5 % (0.6 %) | 0.01 | 1.935 |
| E1 | IWM | 2.0 % | 64 | 0.7 % (0.9 %) | 0.01 | 4.7 % | 62 | 0.8 % (1.0 %) | 0.015 | 1.64 |
| E1 | COIN | 2.0 % | 7 | 4.3 % (5.0 %) | 0.04 | 85.7 % | 7 | 5.3 % (4.9 %) | 0.055 | 0.84 |
| E1 | ASTS | n/a | 5 | 0.2 % (1.8 %) | 0.225 | n/a | 5 | 0.1 % (1.7 %) | 0.165 | 109.16 |
| E1 | RKLB | 2.0 % | 38 | 5.9 % (8.6 %) | 0.11 | 89.5 % | 38 | 7.1 % (7.8 %) | 0.1 | 1.5 |
| E1 | CRM | n/a | 10 | 8.3 % (5.6 %) | 0.195 | n/a | 10 | 9.3 % (9.6 %) | 0.2025 | 2.355 |
| E1 | SPXW | 1.5 % | 59 | 0.9 % (4.9 %) | 0.05 | 32.2 % | 59 | 0.9 % (6.8 %) | 0.05 | 7.05 |
| E1 | DIS | 2.0 % | 11 | 7.5 % (7.7 %) | 0.08 | 90.9 % | 11 | 6.5 % (6.1 %) | 0.075 | 1.07 |
| E1 | AAPL | n/a | 9 | 0.9 % (0.7 %) | 0.05 | n/a | 9 | 0.8 % (0.7 %) | 0.05 | 5.7 |
| E1 | SPY | 1.0 % | 87 | 0.5 % (0.6 %) | 0.01 | 8.1 % | 88 | 0.5 % (0.6 %) | 0.015 | 2.485 |
| E1 | RUTW | 1.5 % | 8 | 4.6 % (4.8 %) | 0.125 | 100.0 % | 8 | 4.2 % (4.1 %) | 0.1375 | 2.875 |
| E1 | GOOG | n/a | 5 | 1.8 % (1.5 %) | 0.075 | n/a | 5 | 1.7 % (1.4 %) | 0.075 | 4.175 |
| E1 | GOOGL | n/a | 10 | 0.9 % (1.5 %) | 0.025 | n/a | 10 | 1.5 % (2.0 %) | 0.0225 | 2.993 |
| E1 | AMZN | 2.0 % | 32 | 0.8 % (0.9 %) | 0.02 | 0.0 % | 29 | 1.0 % (0.9 %) | 0.025 | 2.71 |
| E1 | IBIT | 2.0 % | 8 | 2.1 % (2.0 %) | 0.01 | 87.5 % | 8 | 1.8 % (1.7 %) | 0.01 | 0.603 |
| E1 | INTC | 2.0 % | 11 | 2.6 % (2.8 %) | 0.04 | 100.0 % | 11 | 2.1 % (2.2 %) | 0.035 | 1.51 |
| E1 | HOOD | 2.0 % | 8 | 4.1 % (4.5 %) | 0.055 | 100.0 % | 9 | 5.2 % (5.2 %) | 0.055 | 1.345 |
| E1 | CRML | 2.0 % | 7 | 14.3 % (20.6 %) | 0.075 | 71.4 % | 18 | 25.0 % (22.2 %) | 0.05 | 0.875 |
| E1 | MSFT | 2.0 % | 7 | 0.8 % (0.6 %) | 0.05 | 0.0 % | 7 | 0.8 % (0.6 %) | 0.05 | 6.35 |
| E1 | SLV | 2.0 % | 11 | 4.1 % (3.8 %) | 0.09 | 100.0 % | 11 | 2.8 % (2.9 %) | 0.065 | 2.2 |
| E1 | BOIL | n/a | 9 | 0.1 % (0.1 %) | 0.02 | n/a | 9 | 0.0 % (0.0 %) | 0.01 | 35.82 |
| E1 | CRCL | 2.0 % | 12 | 14.4 % (14.4 %) | 0.275 | 100.0 % | 12 | 13.8 % (14.0 %) | 0.2 | 1.905 |
| E1 | NVDA | 2.0 % | 18 | 0.9 % (0.9 %) | 0.01 | 0.0 % | 18 | 0.8 % (0.7 %) | 0.01 | 1.06 |
| E2 | IWM | 2.0 % | 20 | 0.7 % (1.1 %) | 0.02 | 15.0 % | 19 | 1.0 % (1.2 %) | 0.02 | 2.25 |
| E2 | SPY | 1.0 % | 18 | 0.4 % (0.5 %) | 0.0125 | 5.6 % | 16 | 0.4 % (0.5 %) | 0.015 | 2.82 |
| E2 | QQQ | 1.0 % | 11 | 0.6 % (0.5 %) | 0.01 | 0.0 % | 15 | 0.5 % (0.6 %) | 0.01 | 1.94 |
| E2 | SPXW | 1.5 % | 9 | 0.6 % (0.6 %) | 0.1 | 0.0 % | 7 | 0.5 % (0.6 %) | 0.15 | 15.55 |

## 5. Epoch 1 same-contract-same-minute repeats vs the NBBO within the minute

For every ledger option row, all 1-second NBBO rows of the reported entry minute (up to 60). "repeat" = the row shares contract and entry minute with at least one other ledger row (RESULTS.md: 382 such rows in Epoch 1). "matches any quote" = the reported entry premium equals the bid or ask (±$0.004) or the mid (±$0.01) of at least one second of that minute.

| epoch | rows | n | with minute quotes | clusters | reported P&L | NBBO changed in minute | median distinct NBBOs | matches bid | matches ask | matches mid | matches any quote | within [min bid, max ask] | below min bid | above max ask | below min mid | reported P&L of rows below min bid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | single | 124 | 119 | 124 | 2,058 | 97.5 % | 21 | 25.2 % | 26.9 % | 61.3 % | 66.4 % | 77.3 % | 8.4 % | 14.3 % | 13.5 % | 2,402 |
| E1 | repeat | 372 | 361 | 97 | 41,187 | 100.0 % | 21 | 16.9 % | 14.7 % | 52.1 % | 55.7 % | 64.0 % | 27.7 % | 8.3 % | 33.8 % | 9,713 |
| E2 | single | 551 | 71 | 551 | -9,882 | 98.6 % | 29 | 25.4 % | 26.8 % | 62.0 % | 67.6 % | 74.7 % | 14.1 % | 11.3 % | 16.9 % | 2,572 |
| E2 | repeat | 52 | 8 | 14 | 6,125 | 100.0 % | 27.0 | 0.0 % | 50.0 % | 75.0 % | 75.0 % | 75.0 % | 25.0 % | 0.0 % | 25.0 % | 471 |

## 6. Interpretation

On the 517 Epoch 1 rows with an NBBO at both reported seconds, GeorgeFi reports 39,948; filled at the NBBO ask and bid of those same seconds the rows are worth 13,064 (25.3/trade, day-cluster CI [-8.7, 70.4]). The gap, 26,884 or 67.3 % of the reported total on these rows, is the fill assumption: 7,028 (17.6 %) comes from reported premiums better than the NBBO mid and 19,855 from crossing the realized spread plus fees. 35.3 % of Epoch 1 entries are at or below the bid and 39.0 % of exits at or above the ask; 61.3 % of rows have at least one fill better than the market offered at that second, and those rows carry 28,199 of reported P&L against 11,749 for rows whose fills both lie within the NBBO. The 1-second-later variant gives 12,545 on 517 rows, so the result does not hinge on sub-second timestamp alignment.

Epoch 2 (67 rows): reported 2,242 → executable -2,737 (-40.9/trade, day CI [-124.0, 30.1]); 41.0 % of entries at or below the bid, 24.4 % of exits at or above the ask. Paper (1 rows): reported -100 → executable -113; 0.0 % / 0.0 %.

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
