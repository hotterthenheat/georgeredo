# Compass full-history research — results (running document)

Every number below is produced by `engine/` from the protocol in `04_protocol.md`, recorded in `registry.jsonl`, and reproducible from the study script named in each section (`studies/sNN_*.py`) and the data manifests. Negative results are results. Nothing here is a recommendation until it passes the gates (`registry.jsonl` `GATE-v2`, protocol §10).

## S01 — the owner's baseline, Quick Scalps on index ETFs with same-day expirations (REJECTED)

**What was run.** The configuration exactly as specified (protocol §4; `config/compass_config.v0.baseline.json`): 1-minute RSI 14 crossing 55 (calls) / 45 (puts) with the close on the right side of EMA 9; 5-minute close beyond EMA 20 and the session VWAP; 15-minute EMA 20 vs EMA 50 alignment with price on the right side of EMA 20; relative volume ≥ 1.0 against the same minute of the prior 20 sessions; higher-high/higher-low (or lower-low/lower-high) structure on 5-minute pivots; entries 09:45 → 14:50; one open position per symbol. Contract: the same-day expiration, delta 0.30–0.60 from the mid-implied vol (nearest 0.45), spread < 12 % of mid, ask ≥ $0.05 (open interest and intraday volume filters not available in the 0DTE cache — applied from S03 on). Exits in priority: session cutoff 15:50, 5-minute close through the signal's swing level, 1-minute close through VWAP, −25 % premium stop, +25 % on half, +50 % on the rest, the next 15-minute EMA level, 60-minute hold. Fills: ask in, bid out, from the 1-minute NBBO; $0.70 per contract per side.

**Data.** SPY and QQQ 2022-11-11 → 2026-10-09 (980 sessions each), IWM 2024-04-19 → 2026-10-09 (621 sessions): the complete history of daily expirations on these ETFs, full-strike chains (`research/thetadata/dataset/MANIFEST_full_chains.md`), underlying minute bars from 2017 for warm-up. 6,882 signals; 2,886 filled trades on 614 trading days; 3,100 signals skipped while a position was open; 428 on sessions without chain data; 360 without a same-day expiration; 108 without an eligible contract.

**Result** (`results/v1/s01_quick_scalps_0dte_baseline/REPORT.md`, registry `S01`):

| | trades | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD | net |
|---|---|---|---|---|---|---|---|
| Strategy | 2,886 | **−4.19** | [−5.68, −2.81] | 34.3 % | 0.73 | −$12,320 | −$12,081 |
| Matched random entry (5 seeds, same days/direction/contract rule/exits) | 14,218 | −2.18 | [−3.23, −1.15] | 37.2 % | 0.84 | | |
| Strategy − baseline, paired | 2,885 | **−2.03** | [−3.18, −0.90] | | | | |

Negative in every year (2023 −4.87 [−6.88, −2.85]; 2024 −3.22 [−5.75, −0.76]; 2025 −4.39 [−7.25, −1.78]; 2026 −4.65 [−8.52, −1.06]), for every symbol (SPY −4.99, QQQ −3.80, IWM −3.46) and for both sides (calls −2.26 [−3.86, −0.65]; puts −5.89 [−8.23, −3.67]). The round-trip cost is $2.79 per contract and the gross mean is −$2.79: **the entries lose before costs.** Exit mix: the −25 % stop ends 52 % of trades (−$22 each), the +50 % target 26 % (+$39), the VWAP-loss rule 15 % (−$22), the 60-minute time exit 5 % (+$14), the swing-level invalidation 1 % (−$11). Worst in the top VIX tercile (−7.18 [−10.04, −4.42]) and in the 13:30–14:29 entry hour (−7.02); no event-day pattern (FOMC/CPI/NFP cells overlap zero with small n).

**Reading.** The owner's rule, on the liquid index ETFs where it is cheapest to trade, selects minutes that are worse than random by about $2 per contract after a 60-minute, stop-managed hold. The loss is not a cost artefact and not a single-year artefact. Under protocol §13 the next diagnostics are (a) whether the signal predicts the underlying at all and how much of the move it chases (S04, on 2017 → 2026 minute bars), (b) which components of the rule hurt or help (S02 single-factor grid, in progress), (c) whether longer expirations change the picture (S03, weekly expirations with OI/volume filters, 2017 → 2026). Until one of these produces a positive, out-of-sample, baseline-beating cell, Quick Scalps is **rejected** as a Compass signal family on index 0DTE products.

## Pending

- S02: single-factor grid and ablations around S01 (42 variants) with walk-forward selection by year.
- S03: baseline on Weekly-category expirations, SPY/QQQ/IWM 2017-06 → 2026-10, OI > 250 and intraday volume > 100 applied.
- S04: signal validity on the underlying (forward and backward returns around signals vs random minutes), 2017-06 → 2026-10.
