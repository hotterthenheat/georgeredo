# Compass features: the forward test

The rule: `FORWARD_RULE.md` (committed alone before any forward datum existed). Written by `forward_features.py` (compass-features-forward-2026-10-22.1) from `forward_sessions.csv`. Forward set: 0DTE base trades on SPY, QQQ and SPXW, full sessions from 2026-10-22. Points of the debit per trade after fees; Δ = per-trade mean with − without, pooled over sessions; interval: 20-session moving-block bootstrap (audit_lib, 2,000 draws, seed 20261022), none under 60 sessions.

Sessions counted: **1** (2026-10-22 → 2026-10-22).

| model | counted / N | mean with | mean without | Δ | 95% | verdict |
|---|---|---|---|---|---|---|
| V1 | 1 / 23,960 | -51.73 | -51.73 | +0.00 | — | **no verdict (interim figures only)** |
| X3 | 1 / 369 | -14.78 | -51.27 | +36.49 | — | **no verdict (interim figures only)** |
| VN1 | 1 / 587 | -70.69 | -65.87 | -4.82 | — | **no verdict (interim figures only)** |
| BV1b | 1 / 481 | -47.45 | -51.73 | +4.28 | — | **no verdict (interim figures only)** |
| BX3e | 1 / 265 | -9.68 | -38.17 | +28.49 | — | **no verdict (interim figures only)** |
| BC3 | 1 / 341 | -7.94 | -51.73 | +43.79 | — | **no verdict (interim figures only)** |

No verdict is read before a model reaches its N; interim figures are logged for the record only, with no early stop. At N the verdict uses exactly the first N counted sessions and is never revised. V1's N (23,960 sessions) is out of reach on this forward set (FORWARD_RULE.md section 4). The six models are read separately, without a multiple-test correction.
