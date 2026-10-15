# Multi-Ticker ATM Straddle Measurements — 2026-10-14

Executable mid measurements only. Not strategy results.

| Ticker | Days | Median Mid | Median % of Spot | Notes |
|--------|------|------------|------------------|-------|
| SPY    | 15   | $4.10     | 0.54%           | Clean sample |
| QQQ    | 15   | $5.93     | 0.80%           | Longer, outlier filtered |
| IWM    | 15   | $2.31     | 0.83%           | Longer |
| AAPL   | 3    | ~$4.50    | —               | Short sample |
| NVDA   | 3    | ~$6.70    | —               | Short sample |

All use high-volume strike proxy + positive bid filter.

These measurements support cost calibration required by the promotion criteria in COMPASS_RESEARCH_PLAN.md. They do not demonstrate an edge. Prior research closed most 0DTE lanes after realistic NBBO costs and random baselines.

Next: entry-rule tests vs random baseline, management policies, and OOS validation.
