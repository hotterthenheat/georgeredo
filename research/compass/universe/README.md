# Point-in-time optionable universe

Built so that no experiment uses today's ticker list as the historical universe (brief §4.1).

## Sources

| File | Content | Built by |
|---|---|---|
| `../../data_inventory/thetadata_option_roots.txt` | 15,817 option roots ThetaData lists, delisted and renamed roots included | `research/data_inventory/list_tickers.py` |
| `data_lake/universe/expirations.jsonl.gz` | every expiration ever listed per root (`first`, `last`, the full list); 2012-06-01 → 2099 (a few placeholder dates); 6,757 roots with a future expiration on 2026-10-14; first-expiration years: 4,195 roots already listed in 2012, 735 new in 2013, … 2,482 in 2022 (the daily-expiry and new-listing wave), 756 in 2026 | `list_expirations.py` (157 s, 0 errors, 2026-10-14 15:52 UTC) |
| `data_lake/thetadata/stock_eod/` | daily bars for every stock symbol, newest years first (2026, 2025, 2024, 2023 … as the job completes) | `research/data_inventory/bulk_fetch.py B` |
| `data_lake/universe/tiers.parquet`, `tiers_summary.json` | per calendar year Y: every root optionable in Y with ≥ 100 daily bars in Y−1, ranked by the median daily dollar volume of Y−1; Tier A = 1–100, B = 101–500, C = 501–1,000, D = rest | `tiers.py` |

## Rules

- **Optionable on date d**: the root has a listed expiration on or after d and its first expiration is on or before d (from `expirations.jsonl.gz`), and the underlying has a bar on d.
- **A contract exists on date d** only if it is in the chain ThetaData quoted on d (`option_history_quote` / `option_list_contracts`); the engine never reconstructs an earlier chain from a later one.
- **Tiers use year Y−1 only**, so membership for Y is known on Y's first session. A root that disappears mid-year keeps its tier until its last bar; a new listing enters the following year.
- Index products (SPY, QQQ, IWM, DIA, SPXW, RUTW) are a fixed group evaluated in every year they exist, on top of the tiers.

## Status (2026-10-14)

Tiers built for 2025 and 2026 (the daily bars for 2024 and 2025 are in the lake). 2026: 6,026 optionable roots with bars; Tier A floor $1.03 B median daily dollar volume, Tier B $240 M, Tier C $102 M; top of the list SPY, TSLA, NVDA, QQQ, AAPL, MSFT, PLTR, META, AMZN, IWM. Earlier years are produced automatically by re-running `tiers.py` as each year's daily bars land (the stock-tape floor means CTA-listed names have no daily bars before 2017; for 2013–2017 tiers the minute-bar-derived daily closes will be used for those names, to be added).
