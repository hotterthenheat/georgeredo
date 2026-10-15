# Lifecycle research — 3. The contract lifecycle archive (deliverable 2)

## What it is

A queryable record of what an entry into any same-day index option could have done. It covers every contract with |delta| between 0.05 and 0.95, at every 5-minute instant from 09:35 to 15:45, on every complete 0DTE chain on this machine:

| Root | Sessions | Entry points |
|---|---|---|
| SPY | 980 (2022-11 → 2026-10) | 1.06 M development + validation; the hold-out year adds the rest |
| QQQ | 980 | 1.15 M |
| SPXW | 1,106 (2022-05 → 2026-10) | 2.31 M |
| IWM | 621 (2024-04 → 2026-10) | 0.29 M |

**Total: 7.05 million entry points in 281 MB of Parquet.** Partitioned by root and month in `$SP/lifecycle/archive/<root>/<YYYY-MM>.parquet`, with `jobs.jsonl` recording each month's status, rows, bytes and seconds.

**Build:** `python3 scripts/build_archive.py SPY,QQQ,IWM,SPXW` (code `lc/archive.py`). It is resumable by month and idempotent. A month marked ok is never rebuilt, and files are written atomically.

## Schema (one row per contract × entry instant)

| Group | Columns | Meaning |
|---|---|---|
| Identity | root, session, strike, right, m | m = minutes after 09:30 of the entry instant |
| Entry | bid0, ask0, mid0, rel_spread0, bid_size0, ask_size0 | the NBBO at the entry instant; an entry is executable at ask0 |
| Greeks at entry | spot0, iv0, delta0, gamma0, theta0, vega0, t_years | IV solved from mid0 with r = 4 %, q = 0; theta is the analytic calendar-day rate; vega per vol point |
| Executable exits | liq15, liq30, liq60, liq_cut | the bid 15, 30 and 60 minutes later and at 15:50 |
| Hindsight (Result A) | best_bid, t_best, worst_bid, t_worst | the highest and lowest bid in (entry, 15:50] and the minutes to each |
| Hindsight by horizon | best_bid15, best_bid30, best_bid60 | the highest bid within each horizon |
| Theoretical | best_mid, t_best_mid | the highest mid in (entry, 16:00]: not a fill |
| Expiry | settle | intrinsic value at the 16:00 underlying |
| Underlying | spot15, spot30, spot60, spot_cut, spot_max, spot_min | the path the option rode |

**Half days are left out.** Their grid ends at 13:00, so their horizons are not comparable.

**Checks** (`tests/`, and a manual comparison while the archive was built): `ask0`, `liq30`, `liq_cut`, `best_bid` and its minute, the 30-minute best bid and `spot30` were checked against the raw quote file for the SPY 530 call on 2024-06-04 entered at 10:30. All matched to the cent.

## Result A: the hindsight opportunity against what fixed exits got

Development and validation only (sessions before 2025-10-01). Retrospective: no rule could have known the best minute.

Each figure is a share of the premium paid at the ask:
- **best exit** is the highest bid before 15:50;
- **reached +50 %** is the share of entries whose bid ever touched +50 %;
- the three fixed-exit columns sell at the bid after 30 minutes, at 15:50, or hold to expiry.

| Side | Delta | Entries | Best exit, mean | Reached +50 % | Sold after 30 min | Sold at 15:50 | Held to expiry | Median rel. spread |
|---|---|---|---|---|---|---|---|---|
| Calls | 0.05–0.15 | 411,925 | +155 % | 41 % | −14.5 % | −21.7 % | −19.5 % | 8.7 % |
| Calls | 0.15–0.30 | 300,766 | +136 % | 51 % | −6.2 % | −15.2 % | −15.0 % | 3.6 % |
| Calls | 0.30–0.45 | 232,650 | +107 % | 53 % | −3.6 % | −11.0 % | −9.1 % | 2.2 % |
| Calls | 0.45–0.60 | 230,006 | +84 % | 52 % | −2.4 % | −8.4 % | −4.8 % | 1.5 % |
| Calls | 0.60–0.80 | 389,490 | +60 % | 45 % | −2.4 % | −6.6 % | −1.1 % | 1.7 % |
| Calls | 0.80–0.95 | 798,322 | +30 % | 21 % | −3.1 % | −6.6 % | −0.6 % | 2.1 % |
| Puts | 0.05–0.15 | 557,753 | +181 % | 41 % | −13.4 % | −23.6 % | −28.4 % | 7.4 % |
| Puts | 0.15–0.30 | 363,013 | +153 % | 48 % | −6.6 % | −18.9 % | −22.5 % | 3.3 % |
| Puts | 0.30–0.45 | 253,217 | +120 % | 50 % | −4.5 % | −16.5 % | −18.1 % | 2.1 % |
| Puts | 0.45–0.60 | 227,407 | +95 % | 50 % | −3.5 % | −14.3 % | −13.9 % | 1.5 % |
| Puts | 0.60–0.80 | 345,594 | +69 % | 45 % | −3.3 % | −12.1 % | −8.8 % | 1.8 % |
| Puts | 0.80–0.95 | 703,265 | +34 % | 25 % | −4.3 % | −10.3 % | −5.2 % | 2.6 % |

By time of entry (all deltas):

| Side | Entry window | Best exit, mean | Reached +50 % | Sold after 30 min | Sold at 15:50 | Median minutes to the best bid |
|---|---|---|---|---|---|---|
| Calls | 09:35–11:00 | +96 % | 43 % | −5.2 % | −8.1 % | 84 |
| Calls | 11:00–14:00 | +89 % | 40 % | −3.8 % | −9.2 % | 68 |
| Calls | 14:00–15:45 | +51 % | 28 % | −9.9 % | −19.3 % | 15 |
| Puts | 09:35–11:00 | +119 % | 45 % | −5.1 % | −15.6 % | 62 |
| Puts | 11:00–14:00 | +111 % | 41 % | −5.6 % | −14.5 % | 47 |
| Puts | 14:00–15:45 | +66 % | 29 % | −11.4 % | −19.7 % | 14 |

### What it says

- **Same-day options swing hard in both directions.** About half of all entries near the money touch +50 % at some minute, and the average hindsight best exit is several times the premium for out-of-the-money contracts.
- **None of that is capturable on average with a fixed exit.** Every executable column is negative:
  - the loss grows with time held and with distance out of the money;
  - puts lose more than calls over 2022–2025, a rising market;
  - entries after 14:00 lose most, because time decay is fastest and spreads widest relative to premium.
- **The gap between columns A and B is the problem the management research has to solve.** A rule must find the good exits in real time, and the random-entry comparisons in `05_management_research.md` show whether any rule does.
