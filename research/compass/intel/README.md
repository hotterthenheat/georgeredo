# Market-intelligence brief (2026-10-15)

The owner's brief, "Slayer Terminal — Complete Options Intelligence, Market Research, Fair Value, and Trade Optimization Engine", asks for every ticker, expiration, strike and option type to be studied, and for an edge only where the evidence survives costs and out-of-sample validation.

**How this folder answers it.** Most of the brief had already been run by earlier work in this repository, so this pass does three things:
1. audits what exists against the brief;
2. runs the two pre-registered tests the earlier work had not;
3. states what Compass should and should not use.

| File | Contents |
|---|---|
| `01_audit_and_gaps.md` | The brief section by section against the work; today's verified data facts; the data we do not have; what the full scope would cost |
| `02_volatility_pricing.md` | V1 (option pricing across the universe) and V2 (the earnings volatility cycle): design, data checks, results |
| `03_compass_plan.md` | What Compass should use, what it should not, and what to build next |

**The brief's 16 deliverables:**

| # | Deliverable | Where |
|---|---|---|
| 1 | Data coverage and quality audit | `01_audit_and_gaps.md`; `../lifecycle/01_data_inventory.md` |
| 2 | Inventory of underlyings and contracts | `../lifecycle/01_data_inventory.md` §1–2; `../results/v1/v1_vol_pricing/plan.parquet` (the point-in-time universe, 34 months) |
| 3 | Ticker behaviour profiles | `../lifecycle/12_per_ticker_playbook.md` (SPY, QQQ, IWM, SPX); `../05_results.md` S06, S07 |
| 4 | Cross-ticker relationships | Not run in this pass (`01_audit_and_gaps.md` §4) |
| 5 | Fair-value framework | `02_volatility_pricing.md` (options); underlyings need data we lack |
| 6 | Expiration, strike, volatility and liquidity analysis | `02_volatility_pricing.md`; lifecycle 05, 06, 12 |
| 7 | False breakouts and anomalies | `../05_results.md` S06, S07; lifecycle 04 |
| 8 | Entries, scaling, stops, partials, exits | lifecycle 04, 05, 08, 12 |
| 9 | Cost-adjusted backtests | every study; `02_volatility_pricing.md` |
| 10 | Point-in-time trade replays | `02_volatility_pricing.md` (V1 and V2 trades with contract, quotes and settlement); lifecycle archives |
| 11 | Strategy ranking with out-of-sample evidence | `../lifecycle/09_setup_strategy_matrix.md`; `02_volatility_pricing.md` |
| 12 | New patterns, including failures | `02_volatility_pricing.md`; `../lifecycle/10_failed_hypotheses.md` |
| 13 | Data gaps | `01_audit_and_gaps.md` §3 |
| 14 | Storage and infrastructure plan | `01_audit_and_gaps.md` §5; `../lifecycle/01_data_inventory.md` §3 |
| 15 | Compass implementation plan | `03_compass_plan.md` |
| 16 | Reproducible code and results | `../studies/v1_vol_pricing.py`, `../studies/v2_earnings_vol.py`, `../results/v1/`, `../04_protocol.md` A8–A9 |
