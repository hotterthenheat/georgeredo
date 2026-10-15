# Lifecycle research — 1. Data inventory and quality report (2026-10-15)

This is the first deliverable of the lifecycle brief. It was written **before** any large-scale processing.

Sources:
- the vendor's measured floors (`../02_coverage_matrix.md`, 2026-10-14);
- three new probes run today against the owner's ThetaData key: `audit/probe3.py`, `probe3b.py` and `probe_throughput.py`, outputs `audit/probe3.json` and `audit/probe_throughput.json`;
- a walk over every cache on this machine: `audit/local_inventory.py`, output `audit/local_inventory.json`.

Every figure below is something a request or a file returned. Nothing is taken from the vendors' documentation.

## 1. What the vendors actually serve (verified)

### ThetaData (PRO for stocks, options and indices; one login per key; 8 concurrent requests)

| Field | Granularity | Verified from | Verified today |
|---|---|---|---|
| Option NBBO quotes | tick, 1-second, 1-minute | 2012-06-04 (1-minute, full chains) | **Tick**: one SPY contract on 2024-06-04 returned 824,760 quotes (80 MB in memory, 24 s). **1-second**: 23,401 rows for the same contract. **1-minute**: one full weekly SPY chain-day returned 89,148 contract-minutes in 8 s. |
| Option trades and trade-with-quote | every print, with the NBBO at the print | 2012-06-04 | One full SPY chain-day: 37,785 prints. |
| Option 1-minute OHLCV | per contract-minute that traded | 2012-06-04 | AAPL, AMD and CRWD chain-days returned 21–51 k rows each. |
| Option EOD | OHLC, volume, count and closing NBBO per contract-day | 2012-06-04 | One SPY session across every expiration is about 6,000 contracts. |
| Open interest | per contract-day; the prior settlement's count, reported for that date | 2012-06-04 | The vendor throttles this endpoint to about 0.1 requests a second (measured during S03). |
| Vendor Greeks and IV | 1-minute and EOD | — | **Floor pinned between 2016-06 and 2017-06**: none on 2015-06-03 or 2016-06-03; present 2017-06-05, 2018 and 2019. Not used: the engine solves IV and Greeks from the NBBO mid with stated r and q (`../engine/greeks.py`), so 2012–2016 is treated the same as later years. |
| Interest-rate history | daily | — | **Not entitled before 2024-01-01** ("FREE subscription" on the rate product). The research uses a stated constant r, or the rate implied by put-call parity on the chain itself. No subscription is assumed. |
| Stock and ETF 1-minute OHLCV | 1-minute | **2017 for SPY, QQQ and IWM** | **Correction (found during the Tier D pull):** for 2012-06 → 2016-12 the vendor returns 391 rows a session with every price NaN (all 1,154 SPY sessions pulled). The earlier "2012-06-04 verified" counted rows, not values. For index ETFs before 2017, Tier D uses the close implied by put-call parity on the option chain itself, flagged per session (`src = parity`). Measured against real closes on SPY 2017-06 → 12 with the period's rate: median +0.6 bp, 10th–90th percentile −10.9 to +9.9 bp. |
| Index 1-minute (SPX, VIX; RUT from 2018-12) | 1-minute | 2017-01-03 | Already in use. NDX is refused before 2026-05 (add-on). |
| Expirations per root | full history | 2012 | TWTR lists 480 expirations, FB 539, META 330, BBBY 541. |

### Unusual Whales (on disk)

| Dataset | Range | Notes |
|---|---|---|
| Earnings calendar | 1996 → 2026-12 | 384 k rows, 5,805 tickers |
| Dealer greek-exposure (daily, by ticker) | **2025-10-15 → 2026-10-13** | about 3,000 tickers |
| IV rank, realized vol, variance risk premium | 2025-10-14 → 2026-10-13 | |
| Daily bars | 2025-10-13 → 2026-10-13 | |

Option-history endpoints (flow, chains, exposures by date) reach back to 2023-11-13 but have not been pulled. Contract minute bars start 2025-04-01. The intraday dealer book the terminal records lives on the owner's machine, not here.

### Survivorship (verified today)

Contracts on names that later disappeared are served:

- **TWTR**, taken private 2022-10-27: full 1-minute chains on 2022-10-20 (53,958 rows) and 2022-10-27 (35,972 rows); stock EOD through 2022-10-28.
- **FB → META**, renamed 2022-06-09: chains under FB on 2022-05-02 and under META on 2022-06-10. A rename changes the root, so a point-in-time universe must map roots by date.
- **BBBY**, bankrupt 2023: full chain on 2023-04-20.

Expired-worthless contracts are in every chain-day the caches hold: the full-strike 0DTE files include every strike to the close.

### Retrieval

Every option request is incremental: one (root, expiration or `*`, session or range) per call.
- The bulk "flat files" (every contract, one file a day) start at 2026-10-06 on this account, so no history can be bulk-downloaded.
- Option EOD across every expiration of a root: 1.6–5 s a session alone, **1.85 sessions a second with four in parallel**. A five-session request takes 6.5 s.

## 2. What is already on this machine

All caches are under `$SP/theta`, the session's old scratchpad. Session counts are sessions with a file.

| Dataset | Roots | Range | Sessions | Size | Use |
|---|---|---|---|---|---|
| **0DTE full chains**: 1-minute NBBO, every strike, same-day expiration | SPY, QQQ | 2022-11-11 → 2026-10-09 | 980 each, **complete** | 0.61 / 0.58 GB | intraday lifecycles, 0DTE bucket |
| | SPXW | 2022-05-13 → 2026-10-09 | 1,106, complete | 0.90 GB | |
| | IWM | 2024-04-19 → 2026-10-09 | 621, complete | 0.20 GB | |
| Weekly chains: 1-minute NBBO, every strike, the nearest Friday 1–7 days out | SPY | 2017-06-01 → 2026-10-09 | 468, a **stratified sample** (S03), not consecutive | 0.33 GB | intraday, Weekly bucket |
| | QQQ, IWM | 2017-06-01 → 2026-10-07 | 294 each, sample | 0.20 / 0.13 GB | |
| Weekly 1-minute OHLCV (traded volume) | same three | same | same | 0.14 GB | volume filters |
| Open interest | SPY weeklies | 2017-06 → 2023-06 | 1,525 | 5 MB | |
| Monthly option EOD | SPY, QQQ | 2012-06-15 → 2026-08-21 | 167 cycles each | 7 MB | Position bucket on index ETFs (S17) |
| Single-name event option EOD | 520 roots | 2024-01-02 → 2026-09-01 | 1,312 event windows | 40 MB | Earnings & Events and Breakouts (S11) |
| Single-name and ETF 1-minute OHLCV | 40 Tier A roots | 2017-06-01 → 2026-10-09 | 88,709 root-sessions | 0.96 GB | setup signals on single names |
| SPY / QQQ / IWM 1-minute OHLCV | 3 | 2017-06-01 → 2026-10-09 | 2,353–2,442 | 80 MB | setup signals on index ETFs |
| SPX, VIX 1-minute | 2 | 2017-06-01 → 2026-10-09 | 2,353 / 2,386 | 15 MB | SPXW signals, regime |
| Stock EOD, every symbol | ~13 k a year | 2023 → 2026 (repository data lake) | — | 0.49 GB | universe, daily signals |

### Quote quality (12 random files per root)

| Store | Median two-sided share | Crossed quotes | Locked quotes | Zero-bid share | Median relative spread, contracts priced $0.20–$5 |
|---|---|---|---|---|---|
| 0DTE SPY | 99.7 % | 0 | 39 | 41 % | 1.7 % |
| 0DTE QQQ | 99.7 % | 1 | 35 | 40 % | 2.4 % |
| 0DTE IWM | 99.7 % | 0 | 5 | 45 % | 3.1 % |
| 0DTE SPXW | 100 % | 0 | 0 | 36 % | 7.3 % |
| Weekly SPY | 100 % | 0 | 2,078 | 23 % | 1.3 % |
| Weekly QQQ | 100 % | 0 | 1,443 | 25 % | 1.7 % |
| Weekly IWM | 99.7 % | 0 | 905 | 25 % | 2.4 % |

- **Zero bids** are far-out-of-the-money strikes; a zero bid is a real quote (the contract can only be sold for nothing).
- **The missing 0.3 %** is the 09:30 row, which has no quote yet. Entries therefore start at 09:31 or later.
- **Locked quotes** in the weekly files are mostly deep in-the-money strikes. They are kept: the engine fills at the bid or the ask, never at a locked mid.

## 3. Compute and storage on this machine

| Resource | Available |
|---|---|
| Disk | **18 GB free** of a fixed per-session allowance (4 GB already holds the caches) |
| CPU | 4 cores |
| Memory | 15 GB |
| Vendor concurrency | 8 requests (PRO); the fetchers use 4 |

### What a complete archive would need (not provisioned)

**The whole U.S. option tape at 1-minute NBBO:**
- Measured density: about 6 bytes a contract-minute after compression (SPY 0DTE: 263 contracts × 391 minutes in 0.6 MB).
- At about 1.5 million listed series × 391 minutes, that is 3–4 GB a session, roughly **10–12 TB for 2012–2026**.
- Requests: about 60 k (root, expiration) requests a session, over 200 million in all. At the plan's 8 concurrent requests and 3 s each, that is **years of wall time**.
- Ticks or 1-second data are 20–40 times larger again.

**Conclusion: no complete archive will be built here.** It needs object storage at 10+ TB, a vendor arrangement for bulk history (the account's flat files start 2026-10-06), and several machines. That is infrastructure to decide on, not to provision unasked.

### What this machine can hold (the plan)

**Tier I — intraday, 1-minute NBBO**
- The complete 0DTE chains above (2.3 GB, on disk).
- The weekly sample (0.7 GB, on disk).
- Covers the 0DTE and Weekly buckets on index products: Quick Scalps and every intraday setup on SPY, QQQ, IWM and SPX.
- The derived lifecycle archive keeps contracts with |delta| in 0.03–0.97 on a five-minute entry grid. Estimate about 0.2 GB per root.

**Tier D — daily lifecycles, option EOD with the closing NBBO**
- Every expiration of SPY, QQQ and IWM from 2012-06, and of the 40 Tier A single names from 2017-06.
- Estimate about 45 roots × 3,500 sessions ÷ ~3 sessions a second, so **about 15 hours of pulling**, and **2–4 GB** in weekly files.
- Covers the Swing, Position and Long-Dated buckets, LEAPS, single names, cash-secured puts with assignment, and multi-week credit and debit spreads.
- Decisions are made once a session at the closing NBBO. Intraday excursions in this tier come from the option's own traded high and low, labelled as such.

**Tier E — single-name intraday on demand**
- 1-minute NBBO pulled per event window for a single-name intraday hypothesis that earns it.
- About 1–10 s and 0.3–2 MB per (root, expiration, session).

## 4. What can and cannot be researched with this data

| Brief item | Possible here | Limit |
|---|---|---|
| 0DTE lifecycles (index products) | **Yes, complete**: SPY and QQQ 2022-11 →, SPXW 2022-05 →, IWM 2024-04 → | Daily expirations did not exist earlier. |
| Weekly lifecycles (index products) | Intraday on a 294–468 session sample. Daily from 2012 once Tier D lands. | Multi-day intraday paths for weeklies need consecutive sessions, which the sample does not have. |
| Swing / Position / Long-Dated / LEAPS | Daily, once Tier D lands | Decisions at the close only. Intraday stops are not modelled in this tier. |
| Single names | Daily for 40 Tier A names (2017 →) and the 520 event roots (2024 →). Intraday on demand. | |
| Greeks, IV, skew, term structure | Solved from the NBBO, every year | r stated, or implied by parity (no rate entitlement before 2024). |
| Open interest | Per contract-day | Reported for the prior settlement. Throttled endpoint, so pulled only where a rule uses it. |
| Earnings | Calendar 1996 → | |
| Fed announcements and other macro events | Dates are public record (the Federal Reserve's own calendar) | The calendar is compiled from the Fed's site and kept with its source. Nothing is invented. |
| Unusual options activity | Option trades are available from 2012 on ThetaData (prints with the NBBO), so activity can be computed from the tape. | Requires per-chain trade pulls. UW's flow history (2023-11 →) has not been pulled. |
| Dealer gamma | UW's daily estimate 2025-10 → 2026-10 is on disk. The house estimate from OI and Greeks is possible for any year with OI. | A naive-sign estimate, not observed positioning. |
| Dark-pool prints | **Not on disk.** UW serves them from 2023-11. | Out of scope until pulled; reported as untested. |
| Tick-level fills | Available, but 80 MB a contract-day | Fills use 1-minute NBBO. Tick data is used only to audit a sample of fills. |

## 5. What is reused

The engine in `../engine/` (33 tests passing today) supplies:
- the NYSE calendar, half days and AM settlement;
- the expiry categories (the brief's buckets);
- Black–Scholes Greeks and IV from the mid;
- minute-bar loading and resampling with closed-bar semantics;
- the baseline signal and the trend, breakout and bounce families (`signals.py`), plus the seven triggers (`screen.py`);
- day-clustered bootstrap and paired differences (`stats.py`);
- walk-forward selection (`walkforward.py`);
- the short-premium simulator (`short_sim.py`);
- the resumable, idempotent ThetaData fetcher with one-login guard (`data/theta_fetch.py`).

The lifecycle work adds the contract archive, the position engine (multi-leg, every management action), the policy grid and the A/B/C result separation in `lifecycle/lc/`, on top of these.
