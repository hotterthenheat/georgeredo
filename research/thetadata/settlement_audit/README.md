# SPXW settlement audit (2026-10-14)

PM-settled SPXW options settle to the S&P 500 closing value computed from the component stocks' closing prices (Cboe product specification). This audit reconciles the two settlement proxies used in the research against Cboe's published SPX daily closing values (`https://cdn.cboe.com/api/global/us_indices/daily_prices/SPX_History.csv`, downloaded 2026-10-14, sha256 prefix 54f30ada8afd088e) for every SPXW session 2022-05-13 → 2026-10-09.

| Proxy | Sessions | Within $0.01 of Cboe | Mean abs gap | Median abs gap | Max abs gap | Gaps > 1 pt | Gaps > 5 pt |
|---|---|---|---|---|---|---|---|
| ThetaData SPX end-of-day `close` | 1,105 (1 session has no ThetaData EOD row) | 1,105 | 0.00 | 0.00 | 0.00 | 0 | 0 |
| SPX minute print stamped 16:00 (used by the round-2 SPXW grid) | 1,106 | 27 | 0.63 pts | 0.45 pts | 18.32 pts (2026-06-26) | 194 | 2 |

Conclusion: the ThetaData EOD close is identical to Cboe's published close; the 16:00 minute print is a proxy that is usually within a point but not always. All hold-to-settlement results from 2026-10-14 onward use the Cboe close (`settlement_reconciliation.csv`, column `cboe_close`). Code: `reconcile.py` (`python3 -I reconcile.py`, needs the Cboe file and the local dataset).
