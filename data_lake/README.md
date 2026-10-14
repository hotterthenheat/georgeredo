# Data lake (all-ticker data committed to the repository)

Data pulled on 2026-10-14 for every ticker the user's accounts expose (ticker lists: `../research/data_inventory/`). Every file is Parquet (zstd), each under 40 MB, with row counts and SHA-256 in each folder's `manifest.json`. Read with `polars.read_parquet` or `pandas.read_parquet` (pyarrow).

## `unusualwhales/` — per-ticker histories (one request per ticker; scripts `../research/data_inventory/uw_bulk_fetch.py`, `build_uw_tables.py`)

| Table | Universe requested | Tickers with data | Rows | History |
|---|---|---|---|---|
| `ohlc__1d.part01–03` | all 15,757 UW tickers | 9,610 | 4.48 M | daily bars 2025-10-13 → 2026-10-13, split into pre-market / regular / after-hours rows (`market_time`) |
| `info` | all | 15,676 | 15,676 | snapshot: sector, issue type, market cap, has_options, beta … |
| `earnings` | all | 5,805 | 384 k | earnings reports and estimates |
| `greek-exposure.part01–02` | 7,762 optionable | 6,014 | 1.42 M | daily dealer gamma/delta/charm/vanna (OI-based estimates) 2025-10-15 → 2026-10-13 |
| `iv-rank__1y` | optionable | 6,365 | 1.46 M | daily IV and 1-year IV rank, one year (`timespan=1y`) |
| `iv-rank` | optionable | 6,006 | 29,962 | default request (last ~5 days); superseded by `iv-rank__1y` |
| `volatility__realized` | optionable | 6,276 | 1.42 M | daily implied vs realized volatility, one year |
| `volatility__variance-risk-premium` | optionable | 5,941 | 1.27 M | daily variance risk premium, ~one year |
| `max-pain` | optionable | 5,994 | 36,110 | current max pain for every listed expiration (snapshot, not history) |

Values are stored as strings exactly as the API returned them; `ticker` is added to every row. Tickers that returned no rows are mostly OTC/foreign listings or symbols without options; failed requests (404/422) are counted in `../research/data_inventory/summary.json`. UW endpoints that only return one day per request (flow, OI, spot exposures, chains, …) were not pulled for every ticker: that would be ~250 requests per ticker per year at UW's 3-request concurrency limit.

## `thetadata/` — see its README (bulk daily files for every stock/option/index, and daily stock bars for every symbol).

## Not in the repository (too large for git), kept with manifests and rebuild scripts
- 0DTE option chains at 1-minute NBBO for SPY/QQQ/IWM/SPXW (band 0.67 GB, full chains 2.4 GB): `../research/thetadata/dataset/MANIFEST*.md`.
- Any per-ticker option or minute-level history for all tickers (~100–300 GB+): see `../research/data_inventory/README.md` for the sizing.
