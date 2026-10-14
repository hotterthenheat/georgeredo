# Ticker inventory (2026-10-14)

Every ticker available on the user's two data accounts, pulled live with `list_tickers.py` (ThetaData) and the Unusual Whales list scripts (sector lists, screener by issue type with market-cap bands). Keys are read from the session env file only.

| File | Count | Source |
|---|---|---|
| `thetadata_stocks.txt` | 26,855 | ThetaData `stock_list_symbols` (every US stock/ETF symbol ThetaData carries, including delisted) |
| `thetadata_option_roots.txt` | 15,817 | ThetaData `option_list_symbols` (option roots, incl. index roots like SPXW) |
| `thetadata_indices.txt` | 24,305 | ThetaData `index_list_symbols` (the PRO plan reads Cboe-family indices such as SPX, VIX, RUT; Nasdaq GIDS indices such as NDX need an add-on) |
| `unusualwhales_tickers.txt` | 15,757 | UW `stock/{sector}/tickers` for 11 sectors (13,549 companies), screener `issue_types[]=ETF` in 15 market-cap bands (2,154 ETFs, no band capped), ADR (1 not already listed) and Index (53); tab-separated with type and sector |
| `all_tickers.txt` | 35,180 | union of the above (excluding the index list), with flags: `thetadata_stock`, `thetadata_options`, `unusualwhales`, `uw_type`, `uw_sector` |

Not available on these tiers: UW `/api/companies/listings` (403, Advanced+ tier) and `/api/option-trades/optionable-tickers` (422, not included).

Overlaps: 10,520 symbols have both ThetaData stock data and options; 12,622 UW tickers are ThetaData stock symbols; 3,028 UW tickers are not ThetaData stock symbols (mostly OTC/foreign listings); 5,297 option roots are not stock symbols (index, adjusted and weekly roots).

## What "all data for all tickers" means in practice (measured 2026-10-14)

| Data, every ticker | Limit observed | Size estimate | Fetch time estimate |
|---|---|---|---|
| ThetaData bulk daily files (all stocks, all ~2.1 M option contracts, open interest, indices) | account access starts **2026-10-06** for bulk files ("first access date 20261006") | ~41 MB per day | ~1.5 min per day |
| Stock daily bars per ticker | 365 days per request | ~300 MB for 2022–2026; ~1–2 GB for 2012–2026 | hours |
| Option daily bars per root | AAPL: 72,344 rows, 21 s per month | ~100 GB for 2012–2026 | weeks |
| Stock 1-minute bars per ticker | AAPL: 32 s per month | ~300 GB for 2012–2026 | weeks |
| Option NBBO ticks | — | hundreds of TB | not feasible |

The container has about 27 GB of disk and is temporary, and a git repository should not carry more than a few hundred MB of data, so the full-history option and minute-level data for every ticker cannot be stored here; see `../thetadata/dataset/` for the 0DTE index/ETF datasets already built and `bulk_fetch.py` (next) for the all-ticker daily data.
