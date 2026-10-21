# Hypothesis F — pre-registration (written from the 2022-11 → 2024-12 tables only; no 2025–2026 session has been read)

Written after `PERIOD=fit build.py` (out/flies_fit.parquet, sessions 2022-11-11 → 2024-12-31, SPY 1,048 / QQQ 1,049 +-5 fly
entries at the two times) and `PERIOD=fit run.py` (out/cells_fit.csv, out/kstar_fit.csv, out/fills_fit.csv,
out/magdiff_fit.csv). `PERIOD=oos build.py` is started only after this file is saved; the file timestamps in this folder
(and the shell stamp at the foot of this file) record the order.

## What the fit period shows (SPY + QQQ pooled, +-5, held to settlement, % of max risk, k = 0 = every leg at the NBBO)

| time | form | n | mean $ | mean % [95 % CI] | win | PF | wo5 % | SPY / QQQ % | 2022 / 2023 / 2024 % | $0.01-a-leg stress % [CI] |
|---|---|---|---|---|---|---|---|---|---|---|
| 15:30 | long call +-5 | 1,048 | +6.75 | +2.25 [+0.47, +3.90] | 0.645 | 1.29 | +1.56 | +1.56 / +2.93 | +2.1 / +2.7 / +1.8 | +1.25 [−0.50, +2.87] |
| 15:30 | long put +-5 | 1,049 | +5.30 | +1.87 [+0.09, +3.53] | 0.631 | 1.22 | +1.21 | +1.05 / +2.69 | +1.8 / +2.4 / +1.3 | +0.88 [−0.87, +2.52] |
| 15:30 | iron +-5 (comparison, needs spread approval) | 1,048 | +13.45 | +3.88 [+2.06, +5.56] | 0.683 | 1.65 | +3.19 | +3.21 / +4.55 | +3.6 / +3.9 / +3.9 | +2.85 [+1.06, +4.51] |
| 15:00 | long call +-5 | 1,047 | +11.25 | +3.36 [+1.39, +5.33] | 0.656 | 1.44 | +2.53 | +2.81 / +3.91 | +6.0 / +3.4 / +3.0 | +2.30 [+0.36, +4.26] |
| 15:00 | long put +-5 | 1,048 | +8.38 | +2.68 [+0.71, +4.64] | 0.631 | 1.31 | +1.85 | +1.66 / +3.69 | +6.0 / +2.9 / +2.0 | +1.63 [−0.30, +3.57] |
| 15:00 | iron +-5 (comparison) | 1,047 | +18.52 | +5.26 [+3.21, +7.31] | 0.691 | 1.81 | +4.42 | +4.84 / +5.69 | +7.7 / +4.8 / +5.4 | +4.17 [+2.15, +6.18] |

The fill model on fit: the package debit of a +-5 call or put fly sits $9.6–12.9 a fly above its mid (median $7.50–9.00),
so k = 0.25 adds about $2.4–3.2 a fly and k = 0.5 about $4.8–6.4; the iron's package is only $2.2–2.7 above its mid.
Friction (NBBO slip + $2.60 of fees) is 53–72 % of the mid-to-mid gross on the call / put forms, 21–27 % on the iron.
Every leg quoted >= 1 contract on 100 % of entries; >= the lots needed (2 on the short K0) on 96.5–98.7 %.
moc_mag Q12 − Q345 on fit, pooled: 15:30 call +0.8 [−2.2, +3.8], put +0.7 [−2.5, +3.8]; 15:00 call −0.1 [−3.5, +3.8].

## The pre-registered primary cell and the edge rule (fixed before any 2025–2026 figure is computed)

- PRIMARY (the owner's cell): 15:30, SPY + QQQ pooled, one lot, held to settlement, k = 0 (every leg at the NBBO):
  (a) the long call +-5 fly, (b) the long put +-5 fly, and (c) **the better of the two on fit = the long CALL +-5**
  (fit +2.25 % vs +1.87 %; the call is also the owner's quoted form). (c) is the one cell the verdict stands on.
- SECONDARY: the same at 15:00 (call and put). The iron +-5 is printed beside them for comparison only (it needs spread
  approval, so it is not cash-account-executable and is not a candidate here).
- EDGE RULE for the primary cell, read once on 2025-01-02 → 2026-10-09: "edge" only if ALL of
  (1) OOS mean > 0 with the session-bootstrap 95 % interval clear of zero at k = 0,
  (2) the same with every leg filled $0.01 worse than the NBBO (the $0.01-a-leg stress) — mean > 0 AND interval clear of zero,
  (3) OOS mean without the best five sessions > 0,
  (4) OOS mean > 0 on SPY alone and on QQQ alone.
  Fail on any one → "no edge established / needs more data". k = 0.25 and k = 0.5 and the $0.02 stress are read as the
  grid (sensitivity), never as a selection: k > 0 is an assumption about the complex-order book, not an observation.
- Expectation written now: the owner's +3.9 % [+1.4, +6.2] is C's own OOS figure for cell (c) at k = 0 (C's picks.csv,
  grid / 1530 / call / w5 / SPY+QQQ / oos, n 879) and this folder's build reproduces C's arithmetic exactly on fit, so
  the k = 0 OOS mean will come out at +3.9 %; the question this test answers is rule (2): C printed +2.7 % [+0.3, +5.1]
  at $0.01 a leg for that cell, which would pass (2) narrowly, and +1.6 % [−0.8, +3.9] at $0.02. The put form was never
  pooled by C. Whether (3) and (4) hold at k = 0 and under the stress is what is read next.
- moc_mag: Q12 vs Q345 is read on the primary cell at k = 0 as a diagnostic; no cut is proposed (fit contrasts are
  within +-1 point with intervals through zero).
- No further cell will be promoted after the OOS read. A rule, if (1)–(4) all hold, is the primary cell as stated, with
  the forward paper tracker measuring the realized package fill against the NBBO and the mid (the k that the complex
  book actually gives) — the sample the tracker needs is computed in the notes from the OOS mean and session SD.

Shell stamp at save: 2026-10-21 20:44:54 UTC — OOS build started after this line.
