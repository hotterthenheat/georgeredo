# Normalized GeorgeFi trade history: coverage

Source raw dir: `pull_20261013T185223Z`; rows: 1149

| epoch | book | trades | first entry (ET) | last entry (ET) | 0DTE acct | SWING acct | options | shares | sum reported P&L | missing reported P&L | data-error exits | P&L mismatches (>$1) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | v2.0.0-ict | 546 | 2026-01-20 | 2026-02-27 | 373 | 173 | 496 | 50 | 43,248.26 | 0 | 18 | 16 |
| 2 | singles_today_v1 | 48 | 2026-10-05 | 2026-10-13 | 29 | 19 | 48 | 0 | -843.00 | 0 | 0 | 2 |
| 2 | spx_plan_v1 | 11 | 2026-10-05 | 2026-10-13 | 11 | 0 | 11 | 0 | 3,015.00 | 0 | 1 | 0 |
| 2 | trade_now_v1 | 55 | 2026-07-09 | 2026-10-13 | 55 | 0 | 55 | 0 | -9,902.50 | 0 | 0 | 1 |
| 2 | v2.0.0-ict | 489 | 2026-03-02 | 2026-10-08 | 429 | 60 | 489 | 0 | 3,973.80 | 0 | 5 | 2 |

## Monthly counts (all books)

| month (ET) | trades | sum reported P&L |
|---|---|---|
| 2026-01 | 279 | 15,289.37 |
| 2026-02 | 267 | 27,958.89 |
| 2026-03 | 124 | 1,446.00 |
| 2026-04 | 80 | -169.00 |
| 2026-05 | 69 | 1,745.00 |
| 2026-06 | 45 | -3,497.20 |
| 2026-07 | 69 | -7,372.00 |
| 2026-08 | 84 | -1,787.50 |
| 2026-09 | 53 | 2,875.00 |
| 2026-10 | 79 | 3,003.00 |

## Contract identification

Rows with an OCC symbol: 1099; without (share trades or missing): 50.
OCC roots: SPXW 267, QQQ 167, SPY 159, IWM 99, AMZN 39, RKLB 34, RUTW 31, GOOGL 21, GLD 19, NVDA 18, META 17, CRML 16, SLV 16, NDXP 16, INTC 14, TSLA 13, AAPL 12, CRCL 12, HOOD 11, DIS 10, IBIT 10, COIN 8, CRM 8, MSFT 7, ROKU 7, AVGO 6, ZM 6, ASTS 5, BABA 5, UCO 5, GOOG 4, SPX 4, MU 4, USO 3, USAR 2, RDDT 2, AMD 2, BOIL 2, SPCX 2, SMH 2, BAC 2, OKLO 1, CVNA 1, LYV 1, DRI 1, ZS 1, WMT 1, NBIS 1, TQQQ 1, MSTR 1, UBER 1, SMCI 1, ORCL 1

Rows flagged is_0dte (expiration == entry date ET): 894; options not 0DTE: 205.

## Field coverage

See `field_coverage.csv` (fill rate per epoch and book for the fields the analysis uses). Fields absent in Epoch 1: entrySource, gexRegime, gexDirectionalBias, markPremium, quoteQuality, riskBudget, entryDelta, entryIV, exitLog, holdAdvisor, exit_log, ledger, decisionLedger, marketContext, market_context.
