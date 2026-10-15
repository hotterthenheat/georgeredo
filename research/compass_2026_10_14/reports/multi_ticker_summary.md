# Multi-Ticker ATM Straddle Measurements — 2026-10-14

Executable mid measurements only. Not strategy results.

| Ticker | Days | Median Mid | Notes |
|--------|------|------------|-------|
| SPY    | 15   | $4.10     | 0.54% of spot (clean) |
| QQQ    | 5    | $5.51     | Higher vol |
| IWM    | 5    | $2.23     | Lower absolute |

All samples use high-volume strike proxy for ATM and positive bid filter.

These measurements support the cost calibration step required by the promotion criteria in COMPASS_RESEARCH_PLAN.md. They do not demonstrate an edge. Prior research closed most 0DTE lanes after realistic NBBO costs and random baselines.

Next steps remain: longer windows, entry-rule tests vs random baseline, management policies, and OOS validation.
