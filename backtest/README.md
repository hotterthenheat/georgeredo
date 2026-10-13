# Independent backtest of the reconstructed GeorgeFi-style 0DTE strategy

Pure-Python (stdlib + numpy for the report) backtest over Unusual Whales 1-minute data.

- `data.py` — UW REST client with a gzip disk cache (token from `UW_API_TOKEN` env only); underlying bars, GEX levels, IV context, option-contract bars; OCC id builder.
- `features.py` — session levels (PDH/PDL, PWH/PWL, PMH/PML, ORH/ORL, call/put walls, flip, magnet), cumulative VWAP, ATR(14), sweep-reversal and continuation detectors.
- `exits.py` — exit engines on option bars: `ladder` (stop −25 %, T1 +25 % half, T2 +45 %, breakeven lock after +6 %, guardian trail 35 % give-back after +15 %, 30-min time stop when flat/losing, 15:55 close), `trail` (same without targets), `bracket` (±25 %), `hold` (15:55 close).
- `costs.py` — fill models: `mid` (bar VWAP, no costs), `spread` (half-spread 1 % SPY/QQQ, 2 % IWM per side + $0.70 fees per side), `adverse` (buy bar high, sell at bid-side proxy + fees).
- `prefetch.py` — parallel prefetch of underlying bars, GEX levels and IV for a date range.
- `run.py START END TICKERS OUTDIR` — signals for 2 modes × 2 level sets, option-bar prefetch, 144 variants (3 windows × 3 gates × 2 modes × 2 level sets × 4 engines), random-time baseline with matched per-day counts.
- `report.py OUTDIR SPLIT` — per-variant metrics with bootstrap CIs, IS/OOS split, baselines, breakdowns; writes `summary.json`.
- `match_georgefi.py OUTDIR LEDGER` — coincidence of reconstructed signals with GeorgeFi's own SPY/QQQ/IWM entries.

Reproduce:
```
export UW_API_TOKEN=…            # never commit
export BT_CACHE=/path/to/cache
python3 -I prefetch.py 2025-06-02 2026-10-09 SPY,QQQ,IWM
python3 -I run.py 2025-06-02 2026-10-09 SPY,QQQ,IWM results/v1
python3 -I report.py results/v1 2026-03-02 > results/v1/report.txt
python3 -I match_georgefi.py results/v1 ../evidence/public_api/trades_all.json.gz
```
Results of the run performed on 2026-10-13 are in `results/v1/` (`report.txt`, `summary.json`, `georgefi_match.txt`, `trades.csv.gz`, `baseline.csv.gz`).
