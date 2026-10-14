# ThetaData all-ticker data (2026-10-14)

Script: `../../research/data_inventory/bulk_fetch.py` (one login, resumable). Every file has rows, symbol count and SHA-256 in its folder's `manifest.json`.

## `flat/` — bulk daily files: every ticker in one file per day
Your account's bulk ("flat file") access starts on **2026-10-06** (earlier dates return "first access date 20261006"); the 2026-10-13 files were not yet published at download time.

| Folder | Per day | Contents |
|---|---|---|
| `option_eod/` | ~2.05 M contracts across ~6,290 option roots, ~29 MB | end-of-day OHLC, volume, count and closing NBBO for every listed option contract |
| `option_oi/` | ~2.03 M contracts, ~10.5 MB | open interest for every contract |
| `stock_eod/` | ~18,400 symbols, 0.6 MB | end-of-day OHLC, volume and closing NBBO for every stock/ETF |
| `index_eod/` | ~12,500 index symbols, 0.3 MB | end-of-day values for every index ThetaData publishes |

Sessions: 2026-10-06, 10-07, 10-08, 10-09, 10-12 (202 MB in total).

## `stock_eod/` — daily bars for every stock symbol (26,855 in `../../research/data_inventory/thetadata_stocks.txt`)
One request per symbol per calendar year (the API allows at most 365 days per request), 500 symbols per Parquet part, a `symbol` column added. Years run newest first (2026, 2025, …, 2022); about 45 % of symbols return no data in a given year (delisted or not yet listed). Parts are added to the repository as each year completes; see `manifest.json`.
