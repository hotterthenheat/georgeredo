# Compass Research Update — 2026-10-14

## Progress
- Underlying EOD pulled for SPY (Oct 2026).
- ATM strikes aligned to daily close.
- Aligned straddle mids and percentage-of-spot computed (results/spy_atm_aligned.csv).

## Sample observations (aligned to close)
Straddle mids vary significantly day to day (e.g., $0.70 on 10-01 vs $6.42 on 10-02). High-volume near-ATM spreads remain tight ($0.01–$0.04). Percentage of spot ranges from ~0.05% to ~0.83% in this short window.

## Status vs prior research
Consistent with existing Compass findings: premiums and costs are measurable; no new rule has yet been shown to clear the promotion bar in COMPASS_RESEARCH_PLAN.md.

## Next
Rule-based tests (short premium and defined-risk) with bid/ask fills, chronological splits, and baseline comparisons on the liquid 0DTE universe.
