# Multi-Ticker ATM Straddle Measurements — 2026-10-14

Executable mid measurements only. Not strategy results.

| Ticker | Days | Median Mid | Notes |
|--------|------|------------|-------|
| SPY    | 15   | $4.10     | 0.54% of spot (clean) |
| QQQ    | 16   | $5.85     | Longer window |
| IWM    | 15   | $2.31     | Longer window |
| AAPL   | 3    | ~$4.50    | Short-dated sample |
| NVDA   | 3    | ~$6.70    | Short-dated sample |

All use high-volume strike proxy + positive bid filter. Outliers flagged/filtered where obvious.

These measurements support the cost calibration step required by the promotion criteria in COMPASS_RESEARCH_PLAN.md. They do not demonstrate an edge. Prior research closed most 0DTE lanes after realistic NBBO costs and random baselines.

Next: entry-rule tests vs random baseline, management policies, longer windows, and OOS validation.
