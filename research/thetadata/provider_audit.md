# ThetaData entitlement audit (live, 2026-10-13)

Key supplied by the user in chat (stored only in the session's chmod-600 env file; rotate it after this research). Access path: the official `thetadata` Python client 1.0.14 (PyPI), which authenticates over HTTPS and streams data over gRPC/TLS; no local Theta Terminal is needed (running the downloaded Terminal jar was blocked by the session's execution policy, so it was not used). Probe scripts: `code/probe.py`, `code/tier_probe.py`; sanitized results in `provider_checks/` (`_summary.json`, `_tier_probe.json`).

## Tier: PRO for options, stocks and indices (verified against the published tier boundaries)

| Boundary (Subscriptions page, fetched 2026-10-13) | Test | Result |
|---|---|---|
| Options: VALUE 1-min from 2020-01-01; STANDARD tick from 2016-01-01; PRO tick from 2012-06-01 | 1-min quotes 2014-06-02; tick `trade_quote` 2013-06-07 | both OK (PRO) |
| Stocks: VALUE 1-min from 2021-01-01; STANDARD 1-min from 2016-01-01; PRO tick from 2012-06-01 | 1-min OHLC 2014-06-02; tick trades 2026-03-02 | both OK (PRO) |
| Indices: VALUE 1-min from 2023-01-01; STANDARD from 2022-01-01; PRO from 2017-01-01 | SPX 1-min 2017-06-01, 2019-06-03, 2021-06-01; SPX 1-second today | all OK (PRO) |
| Concurrency: VALUE 2, STANDARD 4, PRO 8 | 8 simultaneous option requests | 8/8 OK |
| NDX (and other Nasdaq GIDS symbols) | 1-min price and EOD | refused: "Requesting data for NASDAQ GIDs symbols without proper permissions" — a separate Nasdaq add-on, not included in PRO on this account |

## What works (first probe)

| Check | Result |
|---|---|
| Index 1-minute prices SPX, VIX, RUT | 391 rows per session; SPX verified on 2026-03-02, 2024-06-03, 2023-01-03, 2022-01-03 and back to 2017 |
| Stock 1-minute OHLC and NBBO, SPY | OK (2026-03-02, 2021-01-04, 2018-06-01, 2014-06-02) |
| Option NBBO 1-minute, 1-second; trades with prevailing NBBO (tick) | OK; strike passed as the plain number string (e.g. `'682'`); SPXW works via `symbol='SPXW'` (plain `SPX` root returns no data for weeklies) |
| Option NBBO depth | 1-minute quotes for SPY on 2025-06-02, 2022-01-03, 2020-06-01, 2018-06-01, 2014-06-02 |
| `option_at_time_quote` with `expiration='0DTE'` | rejected; the expiration must be a date |
| Interval `'0'` | rejected; use `trade_quote` for tick data or `'1s'` |

Schemas: option quotes `symbol, expiration, strike, right, timestamp (ET, tz-aware), bid_size, bid_exchange, bid, bid_condition, ask_size, ask_exchange, ask, ask_condition`; option OHLC adds `open, high, low, close, volume, count, vwap`; `trade_quote` adds `trade_timestamp, quote_timestamp, sequence, condition, size, exchange, price` plus the NBBO fields; index price `timestamp, price`; stock OHLC `timestamp, open, high, low, close, volume, count, vwap`; stock quote `timestamp, bid*, ask*`. The 09:30:00 row of 1-minute series is a NaN placeholder.

## What this unblocks (vs `DATA_PROVIDER_AUDIT.md` §6)
SPX/VIX/RUT minute (and second) prices back to 2017, previously 422 on Unusual Whales; measured option NBBO for every contract-minute and every print, previously modelled as 1–2 % half-spreads; stock tick data. Only NDX remains unavailable (Nasdaq add-on).
