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

## At Robinhood fees (descriptive)

The same sessions, trades and arms, each trade re-priced at Robinhood's fees (the research's default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`, `robinhood-2026-10-24.1`). The study's modelled fee ($0.68748 a contract a side; SPXW $1.18748 / $1.27748) is added back and Robinhood's charged: $0.0403 a contract to buy, and $0.0603 to sell a one-lot ETF option; SPXW $1.0403 / $1.1303 a side. **The pass rule and each model's N stay on the pre-registered fees (FORWARD_RULE.md, frozen)**, and the verdict column above is the only verdict. This table is descriptive.

Sessions re-priced: **1** (2026-10-22 → 2026-10-22).

| model | sessions | mean with, Robinhood (pre-registered) | mean without, Robinhood (pre-registered) | Δ, Robinhood (pre-registered) |
|---|---|---|---|---|
| V1 | 1 | -50.65 (-51.73) | -50.65 (-51.73) | +0.00 (+0.00) |
| X3 | 1 | -13.83 (-14.78) | -50.41 (-51.27) | +36.58 (+36.49) |
| VN1 | 1 | -70.39 (-70.69) | -64.86 (-65.87) | -5.53 (-4.82) |
| BV1b | 1 | -46.57 (-47.45) | -50.65 (-51.73) | +4.08 (+4.28) |
| BX3e | 1 | -8.26 (-9.68) | -36.89 (-38.17) | +28.63 (+28.49) |
| BC3 | 1 | -6.82 (-7.94) | -50.65 (-51.73) | +43.83 (+43.79) |
