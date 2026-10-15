# Compass Research Update — 2026-10-14 (continued)

## Data collected this session
- SPY short-dated EOD (max_dte=1, early Oct 2026): 4,176 rows → 460 liquid contracts after tighter filter.
- QQQ short-dated EOD: 3,962 rows → 545 liquid.
- Refined ATM straddle samples for SPY, QQQ, IWM (see results/).

## Sample ATM straddle mids (executable mid, not fills)
SPY (refined):
- 2026-10-02 @ 765: ~$5.09
- 2026-10-06 @ 776: ~$3.23
- 2026-10-08 @ 774: ~$4.57

QQQ:
- 2026-10-02 @ 742: $6.92
- 2026-10-08 @ 753: $6.22

IWM:
- 2026-10-02 @ 280: $3.24
- 2026-10-08 @ 277: $2.19

Spreads on high-volume near-ATM contracts are frequently $0.01–$0.04.

## Alignment with prior research
These samples are consistent with the existing Compass research in the repo: short-dated ATM premiums are measurable, liquidity is high on the majors, and proportional costs matter. No new rule-based expectancy has been computed yet that passes the promotion criteria in COMPASS_RESEARCH_PLAN.md.

## Next in progress
- Underlying price alignment for true ATM selection.
- First defined-risk and naked short-premium rule tests with bid/ask fills.
- Chronological splits and baseline comparisons.
- Expansion to additional liquid short-dated names.

All artifacts remain under research/compass_2026_10_14/.
