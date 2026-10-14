# Data coverage matrix — measured through the APIs (2026-10-14)

Every date below was discovered by a request against the owner's keys (scripts and raw outputs in `data_audit/`: `boundary_probe.py`, `boundary_probe2.py`, `thetadata_boundaries*.json`, `probe*.log`), not assumed. "Verified from" is the earliest date a request returned rows; "listed from" is what the provider's own date list reports; a floor marked "between A and B" was bracketed, not pinned. Unusual Whales floors come from the live audit of 2026-10-13 (`DATA_PROVIDER_AUDIT.md` §6). Last complete session for everything: **2026-10-13**.

## 1. ThetaData (PRO: stocks, options, indices; one login per key; 8 concurrent requests)

| Product | Field set | Verified from | Notes |
|---|---|---|---|
| Stock EOD (`stock_history_eod`) | OHLC, volume, count, closing NBBO, timestamps | **2012-06-01 for UTP-tape names** (AAPL: 146 rows in 2012, 252/yr after); **2017-01-03 for CTA-tape names** (SPY: no data 2012–2016, 251 rows 2017) | tape-dependent floor; ≤ 365 days per request; the report is stamped at its generation time (17:17–20:00 ET), use the date |
| Stock 1-minute OHLC (`stock_history_ohlc` 1m) | OHLCV, count, VWAP per minute, 09:30–16:00 (391 rows incl. a 16:00 null placeholder) | **2012-06-04 verified for SPY** (391 rows) and 2014-06-02; continuous SPY/QQQ/IWM cache 2017-06-01 → 2026-10-09 | bars exist for SPY before its EOD/tick floor; ≤ 1 month per request through the app's terminal, multi-day through the gRPC client |
| Stock quotes (tick) | NBBO | listed from 2012-06-01 (AAPL, MSFT), 2017-01-03 (SPY, IWM, GME) | `stock_list_dates(QUOTE)` |
| Stock 1-minute quotes (`stock_history_quote` 1m) | NBBO at minute | verified 2020-06-02 and 2024-06-03; **no data 2012–2018 for SPY** | floor between 2018-06 and 2020-06 for SPY; tick quotes listed earlier — not needed by Compass (fills are option NBBO) |
| Stock trades (tick) | every print | listed from 2012-06-01 (UTP) / 2017-01-03 (CTA); verified 2020-06-02 (369,510 SPY prints) and 2024-06-03; no data 2012–2018 on the probed days | as above |
| Index EOD (`index_history_eod`) | OHLC | **2017-01-03** (SPX, VIX; 2016 no data) | 251–253 rows/yr |
| Index 1-minute price | value per minute | **2017-01-03** (SPX, VIX; `index_list_dates`), **RUT 2018-12-01**, VIX1D 2023-04-24, DJI 2017-01-03 → 2018-12-31 only, **NDX 2026-05-08 →** (109 days) | NDX before 2026-05 refused (Nasdaq GIDS add-on) |
| Option expirations (`option_list_expirations`) | every expiration ever listed per root | full history (SPY 2,148, SPXW 2,279, AAPL 846, TSLA 805, GME 734, SPX 206) | the point-in-time universe source; a contract's own quote dates via `option_list_dates(QUOTE)` (the June-2013 SPY expiration quoted 2013-05-16 → 2013-06-14, 21 sessions) |
| Option 1-minute NBBO (`option_history_quote` 1m) | bid, ask, sizes, exchanges, conditions per contract-minute | **2012-06-04** (SPY: 99,314 contract-minutes for the 2012-06-16 expiration), 2013, 2014, 2020, 2024 verified | the fill source; whole-chain per expiration per day in one request (3–6 s); 1-second quotes also available |
| Option trades / trade-quote | every print with the NBBO at the print | **2012-06-04** (21,552 SPY prints) | fill audits |
| Option 1-minute OHLC | OHLCV per contract-minute with trades | **2012-06-04** | intraday volume filter |
| Option open interest | per contract per day | **2012-06-04** (10,752 SPY contracts) | prior-settlement OI; ≤ 365 days per request |
| Option EOD | OHLC, volume, closing NBBO per contract-day | **2012-06-04** (15,034 SPY contract-days in the first week) | daily option bars; one month per request is practical (a year-long request did not return in 20 minutes) |
| Option Greeks / IV (`option_history_greeks_*`, `greeks_eod`) | vendor-computed | **no data 2012–2014**, present 2020-06-04 and 2024 (floor between 2015 and 2020) | not used: the engine computes IV and Greeks from the NBBO mid with stated r, q (`engine/greeks.py`) |
| Interest rates (`interest_rate_history_eod`) | — | not yet probed | r is a stated constant (0.04) until wired |
| Bulk "flat files" (every contract, one day per request) | stock EOD, option EOD, OI, index EOD, quotes, trade-quotes | **2026-10-06 →** only ("first access date 20261006") | in the data lake for 2026-10-06 … 10-12 |

## 2. Unusual Whales (API; 3 concurrent requests; most per-ticker endpoints one day per request)

| Field | From | Notes |
|---|---|---|
| Daily bars (`ohlc/1d`) | ≥ 1 year window pulled (2025-10-13 → 2026-10-13) for 15,706 tickers | deeper history not pulled; ThetaData is the daily source |
| Stock 1-minute bars | 2022-09-28 | |
| Option history endpoints (flow, chains, OI, exposures by date) | **2023-11-13** (403 before) | ~730 trading days |
| Contract 1-minute bars | **2025-04-01** (empty ≤ 2025-03-03) | |
| Ticker-level `greek-exposure` series | 2025-10-14 regardless of date | pulled for 7,762 optionable tickers |
| `iv-rank` (1y), realized vol, variance risk premium | ~1 year | pulled |
| Earnings | ~1 year (5,805 tickers with rows) | the only earnings-date source on hand; limits the Earnings/Events family to 2025-10 → 2026-10 |
| Index 1-minute bars (SPX/NDX/RUT) | 422 (`cboe_index_access_missing`) | use ThetaData |
| Full company listings, optionable-tickers | 403 / 422 (tier) | universe built from sector lists + screener instead |

## 3. What the matrix means for each experiment

| Experiment input | Longest usable history | Constraint |
|---|---|---|
| Signals on the underlying (RSI/EMA/VWAP/relative volume/structure, multi-timeframe) | 2012-06 → for Nasdaq-tape names and for SPY/QQQ via 1-minute OHLC; 2017-01 → for CTA-tape daily/tick history | the tiered universe's minute bars are pulled per symbol-month; CTA-tape names before 2017 are verified per symbol before use |
| Option fills, spreads, delta, liquidity filters | 2012-06 → (NBBO, OHLC, OI) | 0DTE on SPY/QQQ only from 2022-11-11, SPXW from 2022-05-13, IWM from 2024-04-19 (daily expiries did not exist earlier); weekly expirations exist throughout |
| Index regime variables (SPX, VIX) | 2017-01 → | before 2017 use SPY/QQQ realized volatility as the regime proxy, stated as such |
| Point-in-time universe | 2012 → | expirations per root (all history) + daily bars (tape-dependent floor) |
| Earnings/events | 2025-10 → 2026-10 | one year only unless another calendar source is added |
| Flow / dealer-exposure features | 2023-11 → (daily), 2025-04 → (contract minutes) | evaluated on their own window against a matched baseline over the same dates |
| Vendor Greeks | 2020 → | not used |

## 4. Floors still to pin (recorded, not blocking)

- SPY 1-minute stock quotes/trades between 2018-06 and 2020-06 (not needed for fills).
- Vendor Greeks between 2015 and 2020 (not used).
- The 2016 option probe hit a Sunday (my error); 2014 and 2020 bracket it and both have full chains.
- Interest-rate history endpoint.
