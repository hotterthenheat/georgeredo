# Compass lifecycle research

The lifecycle research program behind the Compass brief:
- every Compass setup and option structure;
- every contract's lifecycle;
- every entry and management decision.

It was tested on the vendor's historical NBBO, with realistic fills, and against random entries and a hold-out.

## Documents (read in this order)

| # | File | Deliverable |
|---|---|---|
| 1 | `01_data_inventory.md` | Data inventory and quality report |
| 2 | `02_protocol.md` | The pre-registered protocol and its amendments |
| 3 | `03_lifecycle_archive.md` | The contract-level lifecycle archive and Result A (hindsight) |
| 4 | `04_entry_research.md` | Entry rules, filters, and setup-versus-random comparisons |
| 5 | `05_management_research.md` | Holding, adding, doubling down, scaling, partials, runners, trails, warnings, short-premium rules |
| 6 | `06_daily_tier.md` | Swing / Position / Long-Dated / LEAPS buckets and single names (daily lifecycles) |
| 7 | `07_validation.md` | Walk-forward, finalists, the hold-out (opened once), the Fed and dealer-gamma tests |
| 8 | `08_portfolio.md` | Concurrent signals, capital, caps, re-entry and reversal rules |
| 9 | `09_setup_strategy_matrix.md` | Every setup × strategy cell: untested, insufficient, failed, or promising |
| 10 | `10_failed_hypotheses.md` | Every rule that failed, with its numbers |
| 11 | `11_conclusions.md` | Ranked conclusions |

## Code (`lc/`)

| Module | Role |
|---|---|
| `paths.py` | Where caches, work files and results live |
| `chainmat.py` | One session's 0DTE chain as dense [contract × minute] NBBO arrays, plus the underlying on the same grid |
| `aux.py` | The decision series a policy may read at each minute: RSI, EMA 20 (5m), ATR (5m), VWAP, ATM IV |
| `bs.py` | Black–Scholes, implied vol and analytic theta, compiled; checked against `../engine/greeks.py` |
| `structures.py` | Strike selection for LC/LP Steady and Big Payoff, debit spreads, credit put spread, cash-secured put, straddle, strangle |
| `position.py` | **The position engine** (numba): one multi-leg position managed minute by minute. It covers partials, runner, trail, adds, double-down, scale-in, warnings, thesis exits, credit take-profit and stops, straddle legs, and expiry with exercise and assignment. Lots and exit reasons are accounted separately. |
| `policies.py` | The pre-registered management grid (116 policies) |
| `events.py` | Intraday setups: the engine's families, failed breakouts and bounces, ICT sweeps, MSS and FVG, trigger-only variants |
| `vol.py` | Volatility (HAR forecast against implied) and Fed-day setups |
| `runner.py` | Events × structures × policies over sessions. Random-minute controls, entry rules (latency, confirmation, limits, chase guard), per-row or daily-sum outputs; the hold-out is excluded unless asked. |
| `archive.py` | The contract lifecycle archive builder |
| `analyze.py`, `reports.py` | Day-clustered bootstrap, paired tests, walk-forward selection, tables |
| `sequencer.py` | Time-ordered portfolio simulation: one position per root, risk and collateral caps, displayed-size limits, re-entry and reversal rules |
| `daily.py`, `daily_events.py`, `daily_runner.py` | Tier D: option EOD lifecycles, daily setups, expiration buckets, daily policies |
| `pull_tier_d.py` | Resumable vendor pull of option EOD for every expiration |

## Reproduce

```bash
cd research/compass/lifecycle
python3 -m pytest -q tests/                          # 19 tests: hand-checked trades, a real trade against raw quotes, the compiled pricer, the clean controls, the point-in-time picker
python3 scripts/build_events.py SPY,QQQ,IWM,SPXW     # setup events
python3 scripts/build_vol_events.py SPY,QQQ,IWM,SPXW # volatility and Fed-day events
python3 scripts/run_grid.py <ROOT> both              # the 116-policy grid (daily sums) and the stage-1 set (per row), dev + val only
python3 scripts/run_more.py <ROOT> entry|vol         # entry-rule variants; volatility setups
python3 scripts/build_archive.py SPY,QQQ,IWM,SPXW    # the lifecycle archive
python3 scripts/analyze_tier1.py                     # tables, walk-forward, finalists (no hold-out)
python3 scripts/holdout_tier1.py                     # opens the hold-out ONCE for the finalists (refuses a second run)
python3 scripts/holdout_verdicts.py                  # scores the six promotion rules
python3 scripts/run_controls.py SPY,QQQ,IWM,SPXW     # L-A2 clean controls (RND-after, FLIP); 'holdout' re-scores the finalists
python3 scripts/analyze_controls.py                  # setups against the clean controls, drift-neutral versions
python3 scripts/holdout_flo.py; python3 scripts/holdout_flo_stats.py   # H-FLO-1/2 (run once), p-values and within-root split
python3 scripts/holdout_la3.py                       # L-A3, run once (refuses a second run)
python3 scripts/holdout_r2_after.py                  # the finalists' R2 against RND-after (post hoc)
python3 scripts/run_portfolio.py <configs> devval|holdout
./scripts/run_tier_d.sh                              # Tier D pull (vendor key in the environment, one login)
python3 scripts/run_tier_d_research.py <ROOTS>       # Tier D runs
python3 scripts/analyze_tier_d_groups.py SPY,QQQ,IWM FB   # one bootstrap per group (index ETFs; single names)
python3 scripts/holdout_tier_d.py                    # L-A4: the daily tier's finalists and its hold-out, once
python3 scripts/build_matrix.py; python3 scripts/matrix_md.py   # the setup x strategy matrix (09), from the result files
```

**Data needed:** the 0DTE chains, underlying minutes and index minutes under `$SP/theta` (see `01_data_inventory.md`), and the vendor key for the Tier D pull. The key is read from `THETADATA_KEY` only and is never written anywhere.

**Large intermediates** (archive, runs, Tier D files) live under `$SP/lifecycle` and `$SP/theta/fetch_cache/eod_all`. They are not committed because they are regenerable. Results small enough to read are under `results/`.
