# Exports made by the user from the GeorgeFi site

Files exported by the user from their own browser with GeorgeFi's built-in export buttons and uploaded to this session. Saved unmodified.

| File | Source page | Content | Rows | sha256 (first 16) |
|---|---|---|---|---|
| swings-analysis-2026-10-13.csv | /swings "Export CSV" | that day's swing scanner picks only (Type, Ticker, Strike, Premium, DTE, Confidence, Target1/2, Stop, Delta, Call/Put Wall) | 6 (5 SWING, 1 LOTTO) | a9d0e7a81ab886b2 |

The export button returns the current snapshot only; there is no history export on that page. Historical swing activity is in the trade ledger instead: `../normalized/trades.csv` rows with `account_type = SWING` (173 in Epoch 1, 79 in Epoch 2 across the main and Singles books), each with entry/exit times, premiums, grade and confluence tags.
