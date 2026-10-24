# Compass Close — GATE REPORT: **FAIL**. The study is closed.

Run once, as pre-registered (`PREREG_COMPASS_CLOSE.md`, 1ce2039), on the gate sample (odd months of the 470 new
sessions, 2017-06-02 → 2022-05-12), with the code committed before the run (c950d8a: `close_lib.py`, `gate.py`).
Nothing of the P&L sample (even months) was read. Per the prereg, the rule work stops here: no P&L on the new data, no
books, no tuning, no forward. The figures on the span read before this study (2022-05-13 → 2026-10-09) are below,
labelled PREVIOUSLY READ, and are not judged.

## In plain words

At 15:55 the same-day SPXW at-the-money straddle cost, at its asks, about **1.47 times** the move it went on to pay
(4.87 SPX points of premium against a mean |SET − K| of 3.31). The owner's gate asked for the opposite: the move worth
at least 1.05 times the price, with the interval's lower end above 1. On the 2017–2022 gate sample the ratio is
**0.68 [0.63, 0.79]**. It is below 1 in every year and on every expiry weekday. The one-strike-OTM strangle is dearer
still (0.34). On the span read before (2022–2026) the ratio is 0.86 [0.82, 0.92] and buying the straddle at 15:55 lost
12.8% a trade after the $1.28 fees.

## G1 — pricing (no fees), gate sample

| | value |
|---|---|
| sessions in the gate sample | 236 |
| trades (both 15:55 legs pass the quote rule) | **165** |
| no trade | 71 (70 a leg wider than half its mid, 1 a zero bid) |
| both legs within 10% of mid | 2 of 236 sessions |
| mean \|SET − K\| / mean STR_ask = **R_ask** | **0.681** [0.629, 0.789] (20-session moving blocks, 2,000 draws, seed 20261022) |
| R_mid (at the mids) | 0.758 [0.699, 0.882] |
| mean of per-session ratios \|SET − K\| / STR_ask | 0.698 |
| median of per-session ratios | 0.638 |
| share of sessions with \|SET − K\| > STR_ask | 28.5% |
| mean \|SET − K\|, mean STR_ask, mean STR_mid (SPX points) | 3.31, 4.87, 4.37 |
| sessions with \|SET − S(16:00)\| > 0.5 (flagged, kept) | 38 of 236 |

**G1: FAIL** (needs R_ask ≥ 1.05 and the lower bound > 1.00; R_ask is 0.681 and the upper bound 0.789).

## G2 — stability, gate sample

| year | trades | R_ask | > 1.00 |
|---|---|---|---|
| 2017 (Jul, Sep, Nov) | 7 | 0.505 | no |
| 2018 | 28 | 0.709 | no |
| 2019 | 31 | 0.978 | no |
| 2020 | 40 | 0.647 | no |
| 2021 | 41 | 0.733 | no |
| 2022 (Jan, Mar, May 1–12) | 18 | 0.506 | no |

**0 of 6 years above 1.00** (needs 4).

| expiry row (exclusive) | trades | R_ask | > 1.00 |
|---|---|---|---|
| Mon | 45 | 0.730 | no |
| Wed | 51 | 0.649 | no |
| Fri | 58 | 0.695 | no |
| end of month | 0 | — (no month-end session in the new data; not a condition, as pinned) | — |
| other (Tue, not month-end; reported, not judged) | 11 | 0.507 | — |

The inclusive weekday table is the same (no month-end in the sample). **G2: FAIL** on both parts.

## Control — the one-strike-OTM strangle (descriptive)

| | value |
|---|---|
| sessions where both OTM legs pass the quote rule | 59 of 236 (90 a zero bid, 87 too wide) |
| mean intrinsic at SET / mean strangle ask = R_ask | **0.339** (no interval: fewer than 60 sessions, audit_lib's 3-block minimum) |
| mean intrinsic, mean ask (SPX points) | 1.09, 3.20 |

Reading as pinned: **neither** — the ATM straddle is not cheap, and the strangle one strike out is dearer still against
what it pays. There is no cheapness for a pin or microstructure story to explain.

## Sensitivity: the Lifecycle daily tier's sessions excluded (no verdict)

| overlap definition | gate sessions overlapping | left | trades left | R_ask |
|---|---|---|---|---|
| entry overlap (the daily tier opened a position at that close) | 235 | 1 (2022-05-11) | 1 | 0.02 |
| expiry overlap (a daily-tier position expired that day) | 223 | 13 | 5 | 0.49 |

Both lines are too small to carry weight. Neither moves toward the gate.

## PREVIOUSLY READ — 2022-05-13 → 2026-10-09 (the same figures, not judged)

1,097 full sessions with a same-day SPXW chain; 1,093 trades (4 too wide).

| | value |
|---|---|
| R_ask | 0.865 [0.818, 0.920] |
| R_mid | 0.913 [0.865, 0.969] |
| mean / median of per-session ratios | 0.883 / 0.743 |
| share with \|SET − K\| > STR_ask | 38.0% |
| mean \|SET − K\|, STR_ask, STR_mid (SPX points) | 4.20, 4.86, 4.60 |
| both legs within 10% of mid | 343 of 1,093 trades |
| \|SET − S(16:00)\| > 0.5 | 502 of 1,097 |
| by year (R_ask) | 2022 0.879 · 2023 0.904 · 2024 0.861 · 2025 0.800 · 2026 0.919 (none above 1) |
| by expiry row (R_ask, n) | Mon 0.943 (198) · Wed 0.861 (216) · Fri 0.734 (200) · **EOM 1.024 (50)** · other (Tue/Thu) 0.872 (429) |
| control strangle | 0.686 [0.579, 0.804], 940 sessions |
| **primary P&L** (f = $1.28 a side, entry and exit) | 1,093 trades, **−12.8% a trade [−16.7%, −8.4%]**, −$70.74 a trade, total −$77,318, won 37.0%, median −$115.12 |

Step 0's cousin figure (15:58, 0.815) and this one (15:55, 0.865) say the same thing: the late-day ATM straddle is
priced above the move it pays. Only the month-end row reaches 1.02, on 50 sessions, and the new data hold no month-end
session to test it; it is not a finding.

## Integrity

- **Plain-loop re-derivation** (`verify_plain.py`, pyarrow + csv, no polars, nothing shared with `close_lib.py`): 60
  sessions (50 gate, 10 previously read; seed 20261024), 43 with a trade and 17 without; K, each leg's 15:55 bid and
  ask, STR_ask, STR_mid, SET and P&L: **532 fields, 0 differences**.
- **Lookahead** (`lookahead.py`): 10 gate sessions with every chain row and SPX print stamped after 15:55 blanked (SET
  kept): **10 of 10 unchanged**. Control, the 15:56 quote read instead: the entry (or whether there is a trade) changed
  in **9 of 10** (the tenth has no trade at either minute; K is set at 15:55 in both).
- Units asserted at every boundary in `close_lib.py` (premium in SPX points within (0, 200); f = $1.28 a contract a
  side; P&L = 100 × points − fees, checked per trade).
- Fetch: 470 of 470 sessions answered, every answer same-day PM SPXW (`FETCH_LOG.md`).
- Code (sha256, first 16): close_lib.py 0ffff6016cca6cf8 · gate.py aec53b97958fed3d · fetch_close.py 6b424d5860eef415 ·
  verify_plain.py 9f11bacd0d613e41 · lookahead.py 6458d59fe8046728. Outputs: `out/gate.json`, `out/gate_sessions.csv`,
  `out/prev_sessions.csv`, `out/verify_plain.json`, `out/lookahead.json`.
- Disclosed: `out/gate_sessions.csv` carries each gate trade's $ arithmetic (P&L, return) because section 7's plain-loop
  check re-derives P&L; no P&L figure of the gate sample is summarized, reported or used.

## What did not run, by the stop rule

The P&L test (section 5; it could not have passed anyway — 234 sessions cannot reach the owner's 300 trades), the
MDE, the reported books on the new data, the deflated Sharpe ratios and the forward (section 6).
