# DATA_PROVIDER_AUDIT

Audit of the two market-data accounts available to Slayer Terminal research: **Unusual Whales** (UW) and **Massive** (formerly Polygon.io; `api.massive.com` and `api.polygon.io` serve byte-identical OpenAPI specs). Every entitlement claim below was tested with the supplied keys on 2026-10-13; the sampled responses (first 4 KB, no credentials) are in `evidence/provider_tests/*.sample.json`, the full endpoint catalogs in `evidence/provider_docs/uw_paths_catalog.txt` (226 operations) and `evidence/provider_docs/massive_paths_catalog.txt` (147 operations).

Keys are held only in a chmod-600 env file outside the repository and were never written to any evidence file.

---

## 1. Entitlement matrix (tested)

### 1.1 Massive / Polygon

| Endpoint | Purpose | Result | Notes |
|---|---|---|---|
| `GET /v3/reference/tickers` | ticker reference | **200** | |
| `GET /v3/reference/options/contracts?underlying_ticker=SPY&as_of=…` | contract reference (strike, expiry, exercise style, cfi) | **200** | fields: `cfi, contract_type, exercise_style, expiration_date, primary_exchange, shares_per_contract, strike_price, ticker, underlying_ticker` |
| `GET /v2/aggs/ticker/O:SPXW261012P07800000/range/1/minute/…` | **option 1-minute bars** (o,h,l,c,v,vw,n,t) | **200** | verified for 2026-10-12 and a March 2026 contract (`O:SPY260313P00674000` on 2026-03-04) |
| `GET /v1/open-close/O:…/{date}` | option daily OHLC incl. pre/after-hours marks | **200** | |
| `GET /v2/aggs/ticker/SPY/range/1/minute/…` | stock minute bars | **200** | 2024-10-14 works, 2024-01-02 refused ("plan doesn't include this data timeframe") → **≈2-year lookback** |
| `GET /v2/aggs/ticker/SPY/range/1/day/…` | stock daily bars | 200 for 2025+, **403** for Jan 2024 | same window |
| `GET /v3/trades/{stock or option}` | tick trades | **403 NOT_AUTHORIZED** | |
| `GET /v3/quotes/{stock or option}` | tick quotes / NBBO history | **403** | |
| `GET /v2/last/nbbo/SPY`, `/v2/last/trade/…` | last quote / trade | **403** | |
| `GET /v3/snapshot/options/{underlying}` and `/{contract}` | option snapshot with Greeks, IV, OI | **403** | |
| `GET /v2/snapshot/locale/us/markets/stocks/tickers/SPY` | stock snapshot | **403** | |
| `GET /v2/aggs/ticker/I:SPX/range/…`, `/v3/snapshot/indices` | **index data** | **403** | no indices entitlement |
| Rate limit | | **5 requests/minute observed** (HTTP 429 after bursts; no `Retry-After`/ratelimit headers; `x-item-count`, `x-request-id`, `x-polygon-cluster-name` present) | plan the research fetcher at ≤5/min |
| Websocket `wss://socket.massive.com` | real-time trades/quotes/aggs | **not tested** (would need a long-running client; snapshot/trade entitlements being 403 suggests the plan is aggregates-only) | |

Conclusion: the Massive plan is an **aggregates-only options + stocks** plan with ~2 years of history, no tick data, no Greeks, no index values, and a hard 5/min rate limit. It is sufficient to replay option-contract minute bars (entries, exits, maximum favourable/adverse excursion) but not to measure spreads or Greeks.

### 1.2 Unusual Whales

| Endpoint | Purpose | Result | Granularity / history | Notes |
|---|---|---|---|---|
| `GET /api/stock/{t}/info`, `/quote`, `/stock-state` | reference, live quote, session OHLC | 200 | | |
| `GET /api/stock/{t}/ohlc/{1m}` | underlying 1-minute OHLC incl. pre/post (`market_time: po`) | 200 | 1 m; `date` + `limit` paging | works for ETFs; the earlier "works for `SPX`" observation is **superseded**: the 2026-10-13 live re-audit (§6) returns 422 `cboe_index_access_missing` for SPX/NDX/RUT |
| `GET /api/stock/{t}/greek-exposure` (+`/strike`, `/expiry`, `/strike-expiry`) | **dealer GEX / delta / charm / vanna by strike (EOD snapshot per date)** | 200 for `SPY`, `SPX`, `SPXW` | daily; 890 strikes for SPX | sign convention: `call_gex` ≥ 0, `put_gex` ≤ 0 (dealer long calls / short puts assumption); values are *estimates from OI*, not observed dealer inventory |
| `GET /api/stock/{t}/spot-exposures` | gamma/vanna/charm per 1 % move, **1-minute** series (`_oi`, `_vol`, `_dir` variants) | 200 | 1 m; 516 rows/day | the closest analogue to a live "GEX regime" input |
| `GET /api/stock/{t}/spot-exposures/strike`, `/expiry-strike` | per-strike exposures (OI/vol/ask/bid decomposition) | 200 | | |
| `GET /api/stock/{t}/gex-levels` | computed `gamma_flip`, `call_wall`, `put_wall`, `gamma_magnet`, `nearby_flips`, `source: vol` | 200 | daily | SPY 2026-10-12: flip 781.86, call wall 780, put wall 778, magnet 778 |
| `GET /api/option-trades?ticker_symbol=…` / `option_contracts[]=…` | **tick-level option trades** with NBBO at execution, side tags (`bid_side`, `ask_side`, `mid`), IV, delta, OI, volume, exchange | 200 | **latest trading day only** (`historical_data_not_supported` for past dates) | historical ticks only via `full-tape` |
| `GET /api/option-trades/full-tape/{date}` | **full-market daily option trade file** | 302 → signed GCS zip, **1.51 GB** for 2026-10-12 | daily archives | entitled on this key (docs list it as a $250/mo add-on) |
| `GET /api/option-contract/{id}/intraday?date=` | **1-minute contract bars with `iv_high/iv_low` and ask/bid/mid-side premium & volume** | 200 | 1 m; 390 rows per RTH day; historical dates work | the preferred source for replaying GeorgeFi contracts (no rate limit observed) |
| `GET /api/option-contract/{id}/historic`, `/flow`, `/volume-profile` | contract history, contract flow, strike volume profile | not tested individually (same scope) | | |
| `GET /api/option-trades/flow-alerts` | UW's own flow alerts (rule names, sweeps, floor, multi-leg, premium sides, IV start/end) | 200 | | |
| `GET /api/stock/{t}/flow-recent`, `/flow-per-strike`, `/flow-per-strike-intraday` | per-strike **intraday flow** (call/put premium & volume by ask/bid side, per minute) | 200 | 1 m; 2,484 rows/day for SPY | matches the inputs a "sus-strike per-strike anomaly" detector would need |
| `GET /api/stock/{t}/net-prem-ticks` | net call/put premium & volume ticks | 200 | 1 m; 405 rows | |
| `GET /api/market/market-tide`, `/{sector}/sector-tide`, `/{t}/etf-tide` | market-wide net premium tide | 200 | 5 m | |
| `GET /api/darkpool/{t}`, `/darkpool/recent`, `/{t}/price-levels` | dark-pool prints with NBBO | 200 | tick | |
| `GET /api/stock/{t}/volatility/*` (realized, term-structure, stats, VRP, anomaly, character, option-sentiment) | IV/RV context | 200 (realized tested) | daily | |
| `GET /api/stock/{t}/option-chains?limit=` | chain id list | 200 | | returns **all** chains regardless of `limit` (276 KB) |
| `GET /api/stock/{t}/max-pain`, `/oi-change`, `/oi-per-strike`, `/oi-per-expiry` | OI analytics | in scope (not individually tested) | daily | |
| `GET /api/screener/*`, `/api/option-activity/unusual`, `/api/options-pulse/*` | screeners | in scope | | |
| Websocket channels (docs `/docs/websocket`) | `option_trades`, `gex`, `gex_strike`, `gex_strike_expiry`, `flow-alerts`, `price`, `news`, `custom_alerts`, `lit_trades`, `market_tide`, `darkpool` | documented; **not tested** | | |
| Rate limit | header `x-uw-req-per-minute-remaining: 1000000` on every response (no throttling seen across ~40 calls) | | | |

Conclusion: UW is the **primary** source for everything options-flow and dealer-positioning related, including historical 1-minute contract bars with side-of-trade attribution. Its gaps: tick history only via 1.5 GB daily files, and no Greeks per contract on historical bars (IV only).

**Cross-provider consistency check**: 85 contracts were fetched from both providers; across 28,674 overlapping minutes the median absolute difference in close price is 0.0 % (p90 0.0 %) and the median Massive/UW volume ratio is 1.0 (`evidence/scripts` cross-check in the repo commit). The two providers are interchangeable for 1-minute option OHLCV; UW adds IV range and side-of-trade premium, Massive adds nothing beyond a second rate-limited copy.

---

## 2. Required field → provider map

| Research need | Chosen source | Endpoint | Granularity | History | Timestamps | Limitations |
|---|---|---|---|---|---|---|
| Option contract price path around a GeorgeFi entry/exit | UW (primary), Massive (cross-check) | `option-contract/{id}/intraday`, `v2/aggs/ticker/O:…/range/1/minute` | 1 m | UW: historical OK; Massive: ≥ Mar 2026 verified, ~2 y plan window | UW `start_time` ISO UTC; Massive `t` epoch ms (bar open) | neither gives NBBO history → spread must be estimated (see §4) |
| Underlying price / levels (PDH, PDL, ORB, VWAP) | UW `stock/{t}/ohlc/1m` (ETFs; SPX **not** available on this entitlement, see §6); Massive stock aggs for ETFs | 1 m | UW unknown depth (tested 2026-10-12); Massive ~2 y | | Massive has **no index bars**; use UW for `^SPX/^NDX/^RUT` or ETF proxies (SPY≈SPX/10, document basis drift) |
| Dealer GEX regime, gamma flip, walls | UW `greek-exposure/strike`, `gex-levels`, `spot-exposures` | daily snapshot + 1 m spot series | daily back-fill available (`date=`) | `date` field | estimates based on OI and a dealer-position assumption; not observable dealer inventory |
| Per-strike flow anomalies ("sus-strike") | UW `flow-per-strike-intraday`, `option-trades` (live), `full-tape` (history) | 1 m / tick | live day + daily archives | `executed_at` ISO UTC µs | historical ticks require downloading daily zips |
| Implied volatility, IV rank, RV | UW `volatility/*`, contract `intraday.iv_high/low` | daily / 1 m | | | no per-contract Greeks history |
| Open interest | UW `oi-per-strike`, `option-trades.open_interest`; Massive contracts reference has none | daily | | | OI is T-1 clearing data |
| Dark pool prints | UW `darkpool/{t}` | tick | | | |
| Market breadth / tide | UW `market-tide`, `net-prem-ticks` | 5 m / 1 m | | | |
| Volume vs 20-day baseline (GeorgeFi "volume-status") | Massive stock aggs or UW ohlc | 1 m / daily | | | |
| VIX level | UW `volatility/vix-term-structure`; Massive indices **not entitled** | daily | | | intraday VIX needs another source |
| Fill realism (bid/ask at entry) | UW `option-trades` live-day NBBO fields; for history, infer from `premium_ask_side` vs `premium_bid_side` in contract intraday bars | tick / 1 m | | | approximation only |

Substitution rules used in this research (documented differences):

- **Index levels**: Massive cannot supply `I:SPX`, and UW `stock/SPX/ohlc/1m` answers 422 on this key (§6; the earlier statement that it is used is superseded). The per-minute `price` field of UW `stock/SPX/spot-exposures` is the only index price series this key can retrieve. Where SPY is used as a proxy, remember SPY ≈ SPX/10 minus dividend/basis drift (GeorgeFi's own glossary makes the same approximation).
- **Dealer positioning**: all "dealer" numbers are model estimates (UW assumes dealers are long calls / short puts from OI). Nothing in either API observes dealer inventory or hedging intent.
- **Spread/slippage**: no historical NBBO on either plan; validation uses conservative fills (buy at bar high or at mid + half of a typical spread observed in GeorgeFi's own `quoteQuality` records: median `spreadPct` 6–13 %, `maxSpreadPct` policy 25–30 %).

---

## 2b. GeorgeFi's own provider usage, as observed on the member surface

- `/api/flow-proxy` (the member Options Flow Scanner) forwards the user's filters (`min_premium`, `order`, `limit`, `min_ask_perc`, `is_otm`, `vol_greater_oi`, `max_dte`, …) and returns records with `days_of_oi_increases`, `days_of_vol_greater_than_oi`, `ask_side_perc_7_day`, `bid_side_perc_7_day`, `chain_prev_close`, `vol_pctile_15d`, `total_ask_changes`, `roc`, `floor_volume`, `multileg_volume`, `prev_oi`, `iv_change` — the field set of Unusual Whales' `GET /api/screener/option-contracts` ("Hottest Chains"), whose parameters (`is_otm`, `min_premium`, `min_volume_oi_ratio`, `max_dte`, …) match the proxied query. **Observed pass-through of UW's screener.**
- `/api/indices/*/gex` and `/api/gex/by-expiry` report `source: "websocket"` with `sourceOldestTimestamp`, and SSE `gex` events carry `dataSource`/`dataAgeMs`: a server-side websocket cache of per-strike gamma/vanna/charm, consistent with UW's `gex_strike_expiry` websocket channel (the only allowed host offering per-strike Greeks streams). [inferred provider; observed mechanism]
- `/api/indices/*/dark-pool` uses `methodology: "NBBO_TAGGED"` on SPY as a proxy, consistent with UW `darkpool/{ticker}` fields (`nbbo_bid`, `nbbo_ask`, `market_center`).
- Option symbols everywhere are Massive/Polygon OCC strings (`O:SPXW…`), mark prices come from an NBBO source (`pricingSource: "nbbo"`, `CACHED_NBBO`), and the trades' `quoteQuality.source` is `websocket` with `maxAgeMs 2000`: consistent with Massive's options quotes websocket feeding fills.
- `/api/market-data/bars?ticker=^SPX&timeframe=1M` serves index minute bars that this research's Massive plan cannot access; GeorgeFi therefore holds an indices entitlement or sources index bars elsewhere (UW `stock/SPX/ohlc/1m` is one candidate).

## 3. Costs and usage constraints

- **Massive**: 5 req/min on this key. A full replay of 489 contracts needs ~100 min single-threaded; the fetcher (`evidence/scripts/fetch_bars_mt.py`) backs off on 429. Upgrading to a plan with trades/quotes/snapshots/indices would be needed for tick-level spread analysis and index bars.
- **Unusual Whales**: effectively unthrottled on this key (`1000000`/min advertised); the full-tape archive is ~1.5 GB per trading day (budget ~30 GB per month of history if downloaded).
- Neither provider was asked for anything outside its documented API; no scraping.

---

## 4. Timestamp conventions

| Source | Field | Convention |
|---|---|---|
| GeorgeFi | `entryTime`, `exitTime`, `generatedAt` | ISO-8601 UTC, ms, sometimes space-separated; `timestamp` root = epoch ms |
| UW | `executed_at`, `start_time`, `time` | ISO-8601 UTC with µs; `date` fields are ET trading dates; `market-tide.timestamp` carries `-04:00` offset |
| Massive | `t` | epoch **ms** of bar start (UTC); `from/to` path dates are ET calendar dates |

ET conversion in all scripts uses UTC-4 (EDT) for the observed period (March–October 2026).

---

## 5. Documentation sources

- UW OpenAPI YAML: `https://api.unusualwhales.com/api/openapi` (1.25 MB, fetched 2026-10-13); websocket docs `https://api.unusualwhales.com/docs/websocket`.
- Massive OpenAPI JSON: `https://api.massive.com/openapi` (1.17 MB); same document at `api.polygon.io/openapi`.
- Both catalogs are flattened in `evidence/provider_docs/`.

## 6. Live re-audit on 2026-10-13 (later the same day; added, nothing above rewritten except the three superseded notes)

Full call table (109 calls) and evidence: `research/georgefi_full_history/provider_audit_2026-10-13.md` and `research/georgefi_full_history/provider_checks/`. What changed or was new:

- **Index 1-minute bars are not available on UW** (`stock/SPX|NDX|RUT|SPXW/ohlc/1m` → 422 `cboe_index_access_missing`), consistent with `BACKTEST_RESULTS.md` and contradicting §1.2/§2 above; Massive `I:SPX` stays 403. 184 of the 489 Epoch 2 main-book trades are index contracts whose *underlying* path therefore cannot be replayed; their *contract* bars can (SPXW/NDXP/RUTW roots).
- **UW concurrency cap is 3 in-flight requests** (429 `concurrent_limit_exceeded`); per-minute quota unchanged.
- **History floors**: UW historical option endpoints 403 before 2023-11-13 (730 trading days); UW contract 1-minute bars are empty for every date ≤ 2025-03-03 and present from 2025-04-01; UW stock 1-minute bars reach back to 2022-09-28. Massive 1-minute stock bars refuse 2024-06-03 (plan timeframe); trades/quotes remain 403.
- **Index option roots**: SPXW/NDXP/RUTW work on UW and Massive; plain SPX/NDX/RUT weekly roots are rejected; the 3rd-Friday `SPX…` root returns 0 bars where its `SPXW…` twin returns bars.
- **Works better than documented**: `gex-levels` and `spot-exposures` work for the SPX index (per-minute `price` included) and for old dates (no 90-day limit); `stock/{t}/option-contracts?date=` returns the historical chain with OI, NBBO and Greeks (undocumented); `net-prem-ticks` and `flow-per-strike-intraday` work for SPX; `flow-alerts` ignores `date` but honours `newer_than`/`older_than`; ticker-level `greek-exposure` series starts 2025-10-14 regardless of `date`.

