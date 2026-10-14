# Compass research engine

Python (polars, numpy, scipy), no vendor terminal; data through the ThetaData gRPC client or the on-disk caches. Implements `../04_protocol.md`.

| Module | What it does |
|---|---|
| `calendar.py` | NYSE sessions 2012–2027, 13:00 closes, expiry categories (brief's six), AM settlement (SPX monthlies) — verified against SPY daily bars and minute-bar half days |
| `indicators.py` | EMA (seeded at first close), Wilder RSI (null seed window), session VWAP on typical price, Wilder ATR, same-minute relative volume, confirmed-pivot structure — the app's conventions, no look-ahead |
| `bars.py` | 1-minute bar loading, resampling to 5/15/30/60-minute and daily bars with closed-bar semantics, as-of alignment of higher-timeframe values |
| `greeks.py` | Black-Scholes with continuous yield (delta/vega conventions of `3abida/src/core/greeks.ts`), vectorised implied vol from the NBBO mid |
| `signals.py` | feature frame on all timeframes; the baseline rule (RSI cross + lead EMA, 5m confirmation, 15m alignment, relative volume, structure) with every component switchable for ablations |
| `contracts.py` | expiration choice per category; point-in-time contract selection (delta band from mid-implied vol, OI, intraday volume, relative spread, ask floor) with rejection diagnostics |
| `sim.py` | long single-leg simulation on minute NBBO: entry at the ask after the decision bar, exits (expiry, session cutoff, invalidation, VWAP loss, stop, targets, EMA target, time) at the bid, fees, MAE/MFE |
| `stats.py` | day-clustered bootstrap CIs, summary metrics, grouped tables, paired differences |
| `store.py` | `CacheStore` over the Parquet caches (minute bars, full-strike 0DTE chains, index minutes, expirations) |
| `run.py` | a family over symbols and dates: one-position rule, matched random baselines (5 seeds), versioned outputs and summaries |
| `tests/` | `python3 -m pytest engine/tests` — 15 tests incl. an end-to-end smoke test on cached SPY data |

Studies live in `../studies/` and write to `../results/vN/<study>/` (`config.json`, `trades.parquet`, `baseline_<seed>.parquet`, `summary.json`).

Conventions: timestamps are New York wall time; a bar stamped t closes at t+1 minute; a decision at a bar's close fills at the NBBO at that boundary or the next valid one; time to expiry is calendar time to the last trading day's close; fees $0.70 per contract per side; size 1 contract with fractional partial exits.
