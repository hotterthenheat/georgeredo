# Compass features: the forward test

The rule: `FORWARD_RULE.md` (committed alone before any forward datum existed). Written by `forward_features.py` (compass-features-forward-2026-10-22.1) from `forward_sessions.csv`. Forward set: 0DTE base trades on SPY, QQQ and SPXW, full sessions from 2026-10-22. Points of the debit per trade after fees; Δ = per-trade mean with − without, pooled over sessions; interval: 20-session moving-block bootstrap (audit_lib, 2,000 draws, seed 20261022), none under 60 sessions.

Sessions counted: **2** (2026-10-22 → 2026-10-23).

| model | counted / N | mean with | mean without | Δ | 95% | verdict |
|---|---|---|---|---|---|---|
| V1 | 2 / 23,960 | -53.86 | -53.86 | +0.00 | — | **no verdict (interim figures only)** |
| X3 | 2 / 369 | -29.47 | -55.15 | +25.68 | — | **no verdict (interim figures only)** |
| VN1 | 2 / 587 | -67.30 | -64.36 | -2.94 | — | **no verdict (interim figures only)** |
| BV1b | 2 / 481 | -49.47 | -53.86 | +4.39 | — | **no verdict (interim figures only)** |
| BX3e | 2 / 265 | -27.16 | -47.72 | +20.56 | — | **no verdict (interim figures only)** |
| BC3 | 2 / 341 | -32.38 | -53.86 | +21.48 | — | **no verdict (interim figures only)** |

No verdict is read before a model reaches its N; interim figures are logged for the record only, with no early stop. At N the verdict uses exactly the first N counted sessions and is never revised. V1's N (23,960 sessions) is out of reach on this forward set (FORWARD_RULE.md section 4). The six models are read separately, without a multiple-test correction.

## At Robinhood fees (descriptive)

The same sessions, trades and arms, each trade re-priced at Robinhood's fees (the research's default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`, `robinhood-2026-10-24.1`). The study's modelled fee ($0.68748 a contract a side; SPXW $1.18748 / $1.27748) is added back and Robinhood's charged: $0.0403 a contract to buy, and $0.0603 to sell a one-lot ETF option; SPXW $1.0403 / $1.1303 a side. **The pass rule and each model's N stay on the pre-registered fees (FORWARD_RULE.md, frozen)**, and the verdict column above is the only verdict. This table is descriptive.

Sessions re-priced: **2** (2026-10-22 → 2026-10-23).

| model | sessions | mean with, Robinhood (pre-registered) | mean without, Robinhood (pre-registered) | Δ, Robinhood (pre-registered) |
|---|---|---|---|---|
| V1 | 2 | -52.70 (-53.86) | -52.70 (-53.86) | +0.00 (+0.00) |
| X3 | 2 | -28.50 (-29.47) | -54.23 (-55.15) | +25.73 (+25.68) |
| VN1 | 2 | -67.01 (-67.30) | -63.33 (-64.36) | -3.68 (-2.94) |
| BV1b | 2 | -48.55 (-49.47) | -52.70 (-53.86) | +4.15 (+4.39) |
| BX3e | 2 | -25.71 (-27.16) | -46.34 (-47.72) | +20.63 (+20.56) |
| BC3 | 2 | -31.15 (-32.38) | -52.70 (-53.86) | +21.55 (+21.48) |
