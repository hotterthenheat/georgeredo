# Compass Phase 3, Hypothesis F: the cash-account 15:30 butterfly under realistic complex-order fills

The SPY and QQQ long call ±5 and long put ±5 butterflies (zero margin, cash-account compliant) at 15:30, and 15:00 as the
secondary, held to settlement, with the net package debit filled at the 4-leg NBBO (k = 0) and at 25 % and 50 % of the way
toward the mid (k = 0.25, 0.5), plus the $0.01 and $0.02-a-leg worse-fill stresses, and the iron ±5 beside them for
comparison. Everything runs on files already on disk; nothing was fetched. Every number is from a script in
`research_notes/Compass phase 3/hyp_f_cash_butterfly/` (`out/` the rows and tables, `logs/` the runs); Hypothesis C's
structure builder conventions and statistics are imported from its `common.py` unchanged (nothing in C's folder was edited).
Fit 2022-11-11 → 2024-12-31, OOS 2025-01-02 → 2026-10-09; the pre-registration (`out/preregistered.md`, shell-stamped
2026-10-21 20:44:54 UTC) was saved before `PERIOD=oos build.py` touched a 2025–2026 file (`out/flies_oos.parquet` is
stamped 20:45:27). Fees $0.65 a leg, four legs to open, none at expiry. One lot.

**The short answer.** The owner's "+3.9 % [+1.4 %, +6.2 %] OOS at full 4-leg NBBO" is exactly one cell of Hypothesis C's
record — `out/picks.csv` row `grid / 1530 / call / w5 / SPY+QQQ / oos` (n 879, +3.85 % [+1.38, +6.24]) — the long CALL ±5
fly at 15:30, SPY + QQQ pooled, in C's OOS, and this folder reproduces it to the second decimal. The put ±5 at 15:30 was
never pooled by C; pooled here it reads +3.66 % [+1.16, +6.06] OOS. Against the pre-registered edge rule the primary cell
(the call, the better of the two on fit) **passes all four conditions**: OOS mean +3.85 % with the interval clear of zero
at k = 0; +2.73 % [+0.29, +5.07] with every leg $0.01 worse (the lower bound stays at +0.14 to +0.33 over six bootstrap
seeds and 10,000 draws); +2.69 % without the best five sessions (+1.59 % under the stress); SPY +4.22 % and QQQ +3.48 %
(+3.12 / +2.33 under the stress). It dies at $0.02 a leg (+1.63 % [−0.76, +3.93]). Fill improvement helps linearly and
modestly: the package sits $10.27 a fly above its mid (median $9), so k = 0.25 adds $2.57 and k = 0.5 $5.13 a fly
(+4.56 % and +5.29 %); the break-even k* is −0.96, i.e. the mean survives fills $9.89 a fly ($0.025 a leg) WORSE than the
NBBO package. Friction (slip + $2.60 of fees) is 57 % of the mid-to-mid gross. The iron ±5 (spread approval) does the same
payoff for $8 less a fly: +5.96 % [+3.40, +8.41], and it survives the $0.02 stress. At 15:00 the cash forms do not pass
(call +2.15 % [−0.99, +5.20], QQQ +0.90 %). moc_mag Q1–Q2 vs the rest still adds nothing: the low-magnitude group is
WORSE at 15:30 OOS (−5.05 points [−9.81, −0.43]) after +0.77 [−2.19, +3.84] on fit — the sign flips, as C found.

**The caveat that decides the verdict.** The OOS read here is the same 2025–2026 data C read, and the primary cell was
named (by C's note and then by the owner) after C's OOS was printed. The pre-registration in this folder fixes the rule and
the fill model before any 2025–2026 figure was computed by THIS code, but it cannot make the cell's selection independent
of its OOS. What this test adds that C did not have: the put form pooled, the fill model (k and k*), the gross and the
friction share, the quoted sizes, the stress read on both names and without the best five, and the pre-registered
four-part rule applied to one named cell instead of a grid. So the verdict is **a conditionally justified rule, to be
confirmed by the forward paper tracker before any capital** — not "edge" on evidence independent of its selection.

## 1. Definitions (C's, kept exactly)

- **Data.** `RAW/data_full/chains/{SPY,QQQ}/<date>.parquet`: the 1-minute NBBO of every same-day contract (bid, ask,
  bid_size, ask_size, mid); `RAW/data/underlying/{SPY,QQQ}`: 1-minute bars. SPY and QQQ 980 session files each,
  2022-11-11 → 2026-10-09; half days dropped (fit SPY 6 / QQQ 6, OOS SPY 3 / QQQ 3 — `logs/build_*.json`). Minute m = 0 is
  09:30; a bar stamped t closes at t + 1; **a chain row stamped t is the quote at t**; spot at quote minute m = the close of
  the bar stamped m − 1. A quote is valid when bid and ask are present, ask ≥ bid, bid ≥ 0, ask > 0 (C's `read_chain`).
- **The centre.** C's exact rule: at the entry minute m (330 = 15:00, 360 = 15:30), **K0 = the strike nearest spot among the
  strikes that have BOTH a call and a put validly quoted at m** (a tie goes to the lower strike — numpy's argmin; it never
  arose in the 50 verified flies). "±5" = wings at K0 − 5 and K0 + 5, five dollars (five $1 strikes) from the centre.
- **The structures.** Long call fly: buy 1 K0−5 call, sell 2 K0 calls, buy 1 K0+5 call; long put fly the same in puts;
  iron fly: sell the K0 call and the K0 put, buy the K0−5 put and the K0+5 call. Every leg quoted at m, the short legs' bids
  > 0, max risk ≥ $0.05 (judged on the NBBO structure, so the sample is identical at every k; no row ever hit the $0.05
  floor, `n_floored` = 0 in every cell).
- **Fills.** NBBO (k = 0): a long leg at the ask, a short leg at the bid. D_nbbo = ask(K0−5) + ask(K0+5) − 2 bid(K0);
  D_mid = the same in mids. **The fill model:** debit_k = D_nbbo − k × (D_nbbo − D_mid) + 4 × stress, k ∈ {0, 0.25, 0.5},
  stress ∈ {$0, $0.01, $0.02} a leg. For the iron: credit_k = C_nbbo + k × (C_mid − C_nbbo) − 4 × stress, risk = 5 − credit.
  k > 0 is an **assumption** about how a complex order fills against the package book (a complex order fills as ONE
  package, never leg by leg; the NBBO legs are observed, the improvement is not — the forward paper tracker is what
  measures it). "slip" = D_nbbo − D_mid, what k = 1 would recover.
- **Settlement.** Held to the 16:00 close (the bar stamped 15:59); an in-the-money leg settles at intrinsic with no
  assignment or exercise fee (stated; see §7 — on the ETFs this is physical delivery, which a cash account must flatten),
  a leg out of the money expires with no closing fee. pnl = (payoff − debit_k) × 100 − 4 × $0.65; % = pnl / (debit_k × 100)
  = of max risk. gross = (payoff − D_mid) × 100 with no fees; friction = gross − pnl(k = 0).
- **Statistics** (C's `cell_stats`): "CI" = 2,000-draw bootstrap resampling SESSIONS (pooled SPY + QQQ resample a session
  with both names together); "wo5" = the mean without the best five sessions; max drawdown and the longest losing streak
  are those of the 1-lot chronological sequence; the "by name" figures inside a pooled cell are the same rows split.
- **moc_mag.** C's `out/moc_mag.parquet` read as is: at 15:30 the audit's own t = 930 score, at 15:00 C's 14:30 → 15:00
  re-computation through the audit's normalization; quintile cuts from the fit sessions per name and time; Q12 = below
  the fit 40th percentile. Q12 − Q345 with a session bootstrap in each group (C's `boot_diff`).
- **Break-even k\*.** The mean is linear in k (mean_k = mean_0 + k × 100 × mean slip), so k\* = −mean_0 / (100 × mean slip);
  "$/leg to zero" = mean_0 / 400 is the worse-fill per leg that takes the mean to zero.
- **Scripts.** `common_f.py` (imports C's helpers), `build.py` (PERIOD=fit | oos → `out/flies_fit.parquet`,
  `out/flies_oos.parquet` — rebuildable from RAW in ~15 s a product; the only parquets here), `run.py` (PERIOD=fit | all →
  `out/cells[_fit].csv`, `out/kstar[_fit].csv`, `out/fills[_fit].csv`, `out/magdiff[_fit].csv`), `tables.py`
  (→ `out/tables.md`, formatting only), `verify.py` (→ `out/verify.json`). Run as
  `nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I <script>`; the longest run is 35 s.
- **Verification.** `verify.py` re-derived 50 random flies (seed 20261021, drawn from both periods) from the raw chain and
  underlying files with plain row-by-row loops — spot, K0, every leg's bid / ask / bid_size / ask_size, the NBBO and mid
  package, the payoff, the P&L at k = 0, and the P&L at k = 0.5 and at the $0.01 stress against `run.py`'s own pricing of
  the stored row: **50 of 50 agree, 0 differences** (`out/verify.json`, `logs/verify.log`). On fit, every pooled k = 0 cell
  equals C's `picks.csv` / `flies_summary.csv` figure (15:30 call ±5 pooled +2.25 % [+0.47, +3.90] n 1,048; C printed
  +2.2 [+0.5, +3.9]).

## 2. What Hypothesis C actually printed vs the owner's quoted figure

C's record for the ±5 flies at 15:30, held to settlement, % of max risk [95 % CI], from `hyp_c_debit_flies/out/flies_summary_all.csv`
(by name) and `out/picks.csv` / `out/picks_fillstress.csv` (SPY + QQQ pooled; C pooled the 15:30 call and iron only):

| C's cell | fit n | fit % [CI] | OOS n | OOS % [CI] | OOS $0.01-a-leg | OOS $0.02 |
|---|---|---|---|---|---|---|
| SPY 15:30 call ±5 | 522 | +1.6 [−0.2, +3.3] | 440 | +4.2 [+1.9, +6.7] | +3.1 [+0.8, +5.6] | +2.0 [−0.2, +4.5] |
| QQQ 15:30 call ±5 | 526 | +2.9 [+1.0, +5.0] | 439 | +3.5 [+0.5, +6.5] | +2.3 [−0.6, +5.3] | +1.2 [−1.7, +4.2] |
| **SPY+QQQ 15:30 call ±5** (`picks.csv` grid / 1530 / call / w5) | 1,048 | +2.2 [+0.5, +3.9] | **879** | **+3.9 [+1.4, +6.2]** | +2.7 [+0.3, +5.1] | +1.6 [−0.8, +3.9] |
| SPY 15:30 put ±5 | 522 | +1.1 [−0.7, +2.8] | 440 | +4.2 [+1.8, +6.7] | not printed | not printed |
| QQQ 15:30 put ±5 | 527 | +2.7 [+0.8, +4.6] | 439 | +3.2 [+0.1, +6.2] | not printed | not printed |
| SPY+QQQ 15:30 put ±5 | — | not pooled by C | — | not pooled by C | — | — |
| SPY 15:30 iron ±5 | 522 | +3.2 [+1.4, +5.0] | 440 | +5.5 [+3.1, +8.1] | +4.4 | +3.3 |
| QQQ 15:30 iron ±5 | 526 | +4.6 [+2.6, +6.6] | 439 | +6.4 [+3.3, +9.5] | +5.2 | +4.0 |
| SPY+QQQ 15:30 iron ±5 (post hoc in C) | 1,048 | +3.9 [+2.1, +5.6] | 879 | +6.0 [+3.4, +8.4] | +4.8 [+2.3, +7.2] | +3.6 [+1.2, +6.0] |
| four-name ALL 15:30 call ±5 (SPXW's one-strike fly drags it) | 1,703 | −6.4 | 1,319 | −7.4 | | |

**Verdict on the quote: it matches.** The owner's "+3.9 % [+1.4 %, +6.2 %] OOS at full 4-leg NBBO" is C's
`picks.csv` row `pick = grid, t = 1530, kind = call, wing = w5, product = SPY+QQQ, period = oos`: n 879, mean_pct 0.038501,
CI [0.013759, 0.062403], win 0.622, PF 1.34, wo5 +2.7 %, 2025 +2.9 / 2026 +5.1; C's note quotes it in §6 as the cell "to test
the same way" for a cash account. It is the long CALL fly only (the put was not pooled), at 15:30, both names pooled, NBBO
fills, after fees. Note that C's pre-registered picks were the 15:00 cells (P1–P3), all of which failed; the 15:30 call ±5
was read as the grid, and its fit interval ([+0.5, +3.9]) was the weaker one. This folder's k = 0 OOS row reproduces the
cell exactly (+3.85 % [+1.38, +6.24], same n, same win, same PF, same worst session 2025-03-04).

## 3. The pre-registration, verbatim (`out/preregistered.md`)

```
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
```

## 4. The full tables (`out/tables.md`, rendered from `out/cells.csv`, `out/kstar.csv`, `out/fills.csv`, `out/magdiff.csv`)

### T1. The primary and secondary cells, every k and stress — SPY + QQQ pooled, OOS 2025-01-02 → 2026-10-09

| time | form | k | stress $/leg | n | mean $ | mean % [95 % CI] | win | avg W / L $ | p5 / p1 / worst $ | worst session | PF | MDD $ | streak | wo5 % | SPY / QQQ % | by year % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:30 | long call ±5 | 0.00 | 0.00 | 879 | +9.89 | +3.85 [+1.38, +6.24] | 0.622 | +63 / -77 | -160 / -266 / -335 | 2025-03-04 (-626) | 1.34 | -2519 | 8 | +2.69 | +4.22 / +3.48 | 25: +2.9 / 26: +5.1 |
| 15:30 | long call ±5 | 0.00 | 0.01 | 879 | +5.89 | +2.73 [+0.29, +5.07] | 0.604 | +60 / -77 | -164 / -270 / -339 | 2025-03-04 (-634) | 1.19 | -2727 | 8 | +1.59 | +3.12 / +2.33 | 25: +1.8 / 26: +3.9 |
| 15:30 | long call ±5 | 0.00 | 0.02 | 879 | +1.89 | +1.63 [-0.76, +3.93] | 0.581 | +59 / -77 | -168 / -274 / -343 | 2025-03-04 (-642) | 1.06 | -3330 | 9 | +0.53 | +2.04 / +1.21 | 25: +0.7 / 26: +2.8 |
| 15:30 | long call ±5 | 0.25 | 0.00 | 879 | +12.46 | +4.56 [+2.06, +6.98] | 0.629 | +64 / -75 | -156 / -262 / -331 | 2025-03-04 (-619) | 1.45 | -2386 | 8 | +3.39 | +4.73 / +4.39 | 25: +3.7 / 26: +5.7 |
| 15:30 | long call ±5 | 0.25 | 0.01 | 879 | +8.46 | +3.42 [+0.97, +5.80] | 0.617 | +62 / -77 | -160 / -266 / -335 | 2025-03-04 (-627) | 1.29 | -2594 | 8 | +2.29 | +3.62 / +3.22 | 25: +2.5 / 26: +4.6 |
| 15:30 | long call ±5 | 0.25 | 0.02 | 879 | +4.46 | +2.31 [-0.10, +4.64] | 0.592 | +60 / -76 | -164 / -270 / -339 | 2025-03-04 (-635) | 1.14 | -2802 | 8 | +1.20 | +2.53 / +2.08 | 25: +1.4 / 26: +3.4 |
| 15:30 | long call ±5 | 0.50 | 0.00 | 879 | +15.02 | +5.29 [+2.75, +7.73] | 0.638 | +66 / -75 | -155 / -257 / -328 | 2025-03-04 (-611) | 1.56 | -2253 | 8 | +4.12 | +5.25 / +5.32 | 25: +4.5 / 26: +6.4 |
| 15:30 | long call ±5 | 0.50 | 0.01 | 879 | +11.02 | +4.13 [+1.64, +6.52] | 0.623 | +63 / -76 | -159 / -261 / -332 | 2025-03-04 (-619) | 1.39 | -2461 | 8 | +2.99 | +4.13 / +4.13 | 25: +3.3 / 26: +5.2 |
| 15:30 | long call ±5 | 0.50 | 0.02 | 879 | +7.02 | +3.00 [+0.55, +5.34] | 0.610 | +61 / -77 | -163 / -265 / -336 | 2025-03-04 (-627) | 1.23 | -2669 | 8 | +1.89 | +3.03 / +2.97 | 25: +2.2 / 26: +4.1 |
| 15:30 | long put ±5 | 0.00 | 0.00 | 879 | +9.10 | +3.66 [+1.16, +6.06] | 0.617 | +62 / -77 | -161 / -268 / -347 | 2025-03-04 (-641) | 1.31 | -2528 | 8 | +2.49 | +4.16 / +3.16 | 25: +2.7 / 26: +4.8 |
| 15:30 | long put ±5 | 0.00 | 0.01 | 879 | +5.10 | +2.54 [+0.08, +4.90] | 0.590 | +61 / -75 | -165 / -272 / -351 | 2025-03-04 (-649) | 1.16 | -2743 | 8 | +1.40 | +3.06 / +2.01 | 25: +1.6 / 26: +3.7 |
| 15:30 | long put ±5 | 0.00 | 0.02 | 879 | +1.10 | +1.44 [-0.99, +3.77] | 0.578 | +58 / -77 | -169 / -276 / -355 | 2025-03-04 (-657) | 1.03 | -3467 | 8 | +0.33 | +1.99 / +0.90 | 25: +0.5 / 26: +2.6 |
| 15:30 | long put ±5 | 0.25 | 0.00 | 879 | +11.99 | +4.45 [+1.91, +6.86] | 0.631 | +64 / -76 | -159 / -264 / -333 | 2025-03-04 (-625) | 1.43 | -2379 | 8 | +3.27 | +4.72 / +4.18 | 25: +3.6 / 26: +5.6 |
| 15:30 | long put ±5 | 0.25 | 0.01 | 879 | +7.99 | +3.31 [+0.83, +5.69] | 0.611 | +62 / -76 | -163 / -268 / -337 | 2025-03-04 (-633) | 1.27 | -2587 | 8 | +2.17 | +3.61 / +3.01 | 25: +2.4 / 26: +4.4 |
| 15:30 | long put ±5 | 0.25 | 0.02 | 879 | +3.99 | +2.20 [-0.26, +4.53] | 0.589 | +60 / -76 | -167 / -272 / -341 | 2025-03-04 (-641) | 1.13 | -2795 | 8 | +1.09 | +2.52 / +1.88 | 25: +1.3 / 26: +3.3 |
| 15:30 | long put ±5 | 0.50 | 0.00 | 879 | +14.87 | +5.26 [+2.69, +7.69] | 0.644 | +65 / -76 | -157 / -261 / -321 | 2025-03-04 (-609) | 1.55 | -2229 | 8 | +4.08 | +5.28 / +5.23 | 25: +4.5 / 26: +6.3 |
| 15:30 | long put ±5 | 0.50 | 0.01 | 879 | +10.87 | +4.10 [+1.58, +6.50] | 0.622 | +63 / -75 | -161 / -265 / -325 | 2025-03-04 (-617) | 1.38 | -2437 | 8 | +2.95 | +4.16 / +4.04 | 25: +3.3 / 26: +5.1 |
| 15:30 | long put ±5 | 0.50 | 0.02 | 879 | +6.87 | +2.97 [+0.49, +5.32] | 0.605 | +61 / -76 | -165 / -269 / -329 | 2025-03-04 (-625) | 1.23 | -2645 | 8 | +1.85 | +3.06 / +2.88 | 25: +2.2 / 26: +4.0 |
| 15:30 | iron ±5 (spread approval) | 0.00 | 0.00 | 879 | +17.46 | +5.96 [+3.40, +8.41] | 0.652 | +67 / -75 | -154 / -250 / -323 | 2025-03-04 (-600) | 1.67 | -2145 | 8 | +4.80 | +5.54 / +6.38 | 25: +5.2 / 26: +6.9 |
| 15:30 | iron ±5 (spread approval) | 0.00 | 0.01 | 879 | +13.46 | +4.79 [+2.28, +7.19] | 0.635 | +65 / -75 | -158 / -254 / -327 | 2025-03-04 (-608) | 1.49 | -2330 | 8 | +3.66 | +4.41 / +5.16 | 25: +4.0 / 26: +5.7 |
| 15:30 | iron ±5 (spread approval) | 0.00 | 0.02 | 879 | +9.46 | +3.64 [+1.17, +6.00] | 0.621 | +62 / -77 | -162 / -258 / -331 | 2025-03-04 (-616) | 1.33 | -2538 | 8 | +2.54 | +3.31 / +3.98 | 25: +2.9 / 26: +4.6 |
| 15:30 | iron ±5 (spread approval) | 0.25 | 0.00 | 879 | +18.07 | +6.15 [+3.58, +8.61] | 0.655 | +67 / -75 | -153 / -249 / -322 | 2025-03-04 (-599) | 1.70 | -2123 | 8 | +4.98 | +5.71 / +6.59 | 25: +5.4 / 26: +7.1 |
| 15:30 | iron ±5 (spread approval) | 0.25 | 0.01 | 879 | +14.07 | +4.97 [+2.45, +7.40] | 0.638 | +65 / -75 | -157 / -253 / -326 | 2025-03-04 (-607) | 1.52 | -2294 | 8 | +3.84 | +4.58 / +5.37 | 25: +4.2 / 26: +5.9 |
| 15:30 | iron ±5 (spread approval) | 0.25 | 0.02 | 879 | +10.07 | +3.83 [+1.34, +6.20] | 0.627 | +62 / -77 | -161 / -257 / -330 | 2025-03-04 (-615) | 1.35 | -2502 | 8 | +2.72 | +3.47 / +4.18 | 25: +3.1 / 26: +4.8 |
| 15:30 | iron ±5 (spread approval) | 0.50 | 0.00 | 879 | +18.68 | +6.34 [+3.76, +8.81] | 0.659 | +67 / -75 | -152 / -248 / -321 | 2025-03-04 (-597) | 1.73 | -2101 | 8 | +5.17 | +5.89 / +6.80 | 25: +5.6 / 26: +7.3 |
| 15:30 | iron ±5 (spread approval) | 0.50 | 0.01 | 879 | +14.68 | +5.16 [+2.63, +7.59] | 0.639 | +65 / -75 | -156 / -252 / -325 | 2025-03-04 (-605) | 1.54 | -2258 | 8 | +4.02 | +4.75 / +5.58 | 25: +4.4 / 26: +6.1 |
| 15:30 | iron ±5 (spread approval) | 0.50 | 0.02 | 879 | +10.68 | +4.01 [+1.51, +6.39] | 0.628 | +62 / -77 | -160 / -256 / -329 | 2025-03-04 (-613) | 1.37 | -2466 | 8 | +2.90 | +3.63 / +4.38 | 25: +3.3 / 26: +4.9 |
| 15:00 | long call ±5 | 0.00 | 0.00 | 878 | +4.52 | +2.15 [-0.99, +5.20] | 0.585 | +73 / -92 | -197 / -315 / -471 | 2026-03-09 (-706) | 1.12 | -3295 | 8 | +0.99 | +3.40 / +0.90 | 25: +1.2 / 26: +3.4 |
| 15:00 | long call ±5 | 0.00 | 0.01 | 878 | +0.52 | +0.99 [-2.12, +3.99] | 0.572 | +70 / -93 | -201 / -319 / -475 | 2026-03-09 (-714) | 1.01 | -3752 | 9 | -0.15 | +2.25 / -0.28 | 25: +0.0 / 26: +2.2 |
| 15:00 | long call ±5 | 0.00 | 0.02 | 878 | -3.48 | -0.15 [-3.21, +2.80] | 0.560 | +68 / -94 | -205 / -323 / -479 | 2026-03-09 (-722) | 0.92 | -6222 | 9 | -1.26 | +1.12 / -1.42 | 25: -1.1 / 26: +1.1 |
| 15:00 | long call ±5 | 0.25 | 0.00 | 878 | +7.78 | +3.03 [-0.17, +6.14] | 0.593 | +74 / -90 | -193 / -312 / -451 | 2026-03-09 (-700) | 1.21 | -2962 | 8 | +1.86 | +3.98 / +2.08 | 25: +2.1 / 26: +4.3 |
| 15:00 | long call ±5 | 0.25 | 0.01 | 878 | +3.78 | +1.85 [-1.31, +4.89] | 0.582 | +72 / -91 | -197 / -316 / -455 | 2026-03-09 (-708) | 1.10 | -3282 | 9 | +0.70 | +2.81 / +0.88 | 25: +0.9 / 26: +3.1 |
| 15:00 | long call ±5 | 0.25 | 0.02 | 878 | -0.22 | +0.69 [-2.41, +3.69] | 0.567 | +70 / -92 | -201 / -320 / -459 | 2026-03-09 (-716) | 0.99 | -3863 | 9 | -0.43 | +1.67 / -0.29 | 25: -0.2 / 26: +1.9 |
| 15:00 | long call ±5 | 0.50 | 0.00 | 878 | +11.03 | +3.94 [+0.69, +7.10] | 0.607 | +75 / -89 | -190 / -309 / -432 | 2026-03-09 (-695) | 1.32 | -2629 | 8 | +2.78 | +4.57 / +3.31 | 25: +3.0 / 26: +5.1 |
| 15:00 | long call ±5 | 0.50 | 0.01 | 878 | +7.03 | +2.74 [-0.47, +5.84] | 0.595 | +73 / -90 | -194 / -313 / -436 | 2026-03-09 (-703) | 1.19 | -2949 | 8 | +1.60 | +3.39 / +2.08 | 25: +1.8 / 26: +3.9 |
| 15:00 | long call ±5 | 0.50 | 0.02 | 878 | +3.03 | +1.56 [-1.58, +4.62] | 0.579 | +71 / -90 | -198 / -317 / -440 | 2026-03-09 (-711) | 1.08 | -3269 | 9 | +0.45 | +2.24 / +0.88 | 25: +0.7 / 26: +2.7 |
| 15:00 | long put ±5 | 0.00 | 0.00 | 878 | +2.20 | +1.55 [-1.60, +4.68] | 0.568 | +73 / -91 | -196 / -315 / -366 | 2026-03-09 (-714) | 1.06 | -3605 | 8 | +0.39 | +2.90 / +0.19 | 25: +0.1 / 26: +3.4 |
| 15:00 | long put ±5 | 0.00 | 0.01 | 878 | -1.80 | +0.40 [-2.69, +3.48] | 0.557 | +70 / -93 | -200 / -319 / -370 | 2026-03-09 (-722) | 0.96 | -5539 | 9 | -0.74 | +1.76 / -0.97 | 25: -1.0 / 26: +2.2 |
| 15:00 | long put ±5 | 0.00 | 0.02 | 878 | -5.80 | -0.73 [-3.76, +2.30] | 0.543 | +68 / -94 | -204 / -323 / -374 | 2026-03-09 (-730) | 0.86 | -8337 | 9 | -1.83 | +0.64 / -2.10 | 25: -2.1 / 26: +1.0 |
| 15:00 | long put ±5 | 0.25 | 0.00 | 878 | +6.25 | +2.62 [-0.59, +5.79] | 0.581 | +75 / -88 | -190 / -313 / -361 | 2026-03-09 (-708) | 1.17 | -2846 | 8 | +1.45 | +3.64 / +1.60 | 25: +1.3 / 26: +4.3 |
| 15:00 | long put ±5 | 0.25 | 0.01 | 878 | +2.25 | +1.45 [-1.71, +4.54] | 0.564 | +73 / -89 | -194 / -317 / -365 | 2026-03-09 (-716) | 1.06 | -3374 | 9 | +0.30 | +2.48 / +0.41 | 25: +0.2 / 26: +3.1 |
| 15:00 | long put ±5 | 0.25 | 0.02 | 878 | -1.75 | +0.30 [-2.78, +3.34] | 0.551 | +70 / -90 | -198 / -321 / -369 | 2026-03-09 (-724) | 0.96 | -5327 | 9 | -0.82 | +1.35 / -0.76 | 25: -1.0 / 26: +1.9 |
| 15:00 | long put ±5 | 0.50 | 0.00 | 878 | +10.29 | +3.74 [+0.50, +6.95] | 0.599 | +76 / -87 | -186 / -310 / -357 | 2026-03-09 (-703) | 1.29 | -2409 | 8 | +2.57 | +4.41 / +3.08 | 25: +2.6 / 26: +5.2 |
| 15:00 | long put ±5 | 0.50 | 0.01 | 878 | +6.29 | +2.54 [-0.65, +5.69] | 0.584 | +74 / -88 | -190 / -314 / -361 | 2026-03-09 (-711) | 1.17 | -2729 | 8 | +1.39 | +3.23 / +1.85 | 25: +1.4 / 26: +4.0 |
| 15:00 | long put ±5 | 0.50 | 0.02 | 878 | +2.29 | +1.37 [-1.76, +4.46] | 0.568 | +72 / -89 | -194 / -318 / -365 | 2026-03-09 (-719) | 1.06 | -3178 | 9 | +0.25 | +2.08 / +0.65 | 25: +0.3 / 26: +2.8 |
| 15:00 | iron ±5 (spread approval) | 0.00 | 0.00 | 878 | +15.09 | +5.03 [+1.72, +8.24] | 0.623 | +77 / -87 | -185 / -302 / -350 | 2026-03-09 (-693) | 1.46 | -2190 | 8 | +3.85 | +5.03 / +5.03 | 25: +4.2 / 26: +6.1 |
| 15:00 | iron ±5 (spread approval) | 0.00 | 0.01 | 878 | +11.09 | +3.80 [+0.54, +6.96] | 0.607 | +75 / -88 | -189 / -306 / -354 | 2026-03-09 (-701) | 1.32 | -2489 | 8 | +2.65 | +3.84 / +3.76 | 25: +3.0 / 26: +4.9 |
| 15:00 | iron ±5 (spread approval) | 0.00 | 0.02 | 878 | +7.09 | +2.60 [-0.61, +5.70] | 0.590 | +73 / -88 | -193 / -310 / -358 | 2026-03-09 (-709) | 1.20 | -2809 | 9 | +1.48 | +2.68 / +2.52 | 25: +1.8 / 26: +3.7 |
| 15:00 | iron ±5 (spread approval) | 0.25 | 0.00 | 878 | +15.69 | +5.23 [+1.91, +8.45] | 0.625 | +77 / -87 | -184 / -301 / -349 | 2026-03-09 (-692) | 1.48 | -2135 | 8 | +4.07 | +5.21 / +5.25 | 25: +4.4 / 26: +6.3 |
| 15:00 | iron ±5 (spread approval) | 0.25 | 0.01 | 878 | +11.69 | +4.00 [+0.73, +7.16] | 0.609 | +75 / -87 | -188 / -305 / -353 | 2026-03-09 (-700) | 1.34 | -2422 | 8 | +2.86 | +4.02 / +3.97 | 25: +3.2 / 26: +5.0 |
| 15:00 | iron ±5 (spread approval) | 0.25 | 0.02 | 878 | +7.69 | +2.79 [-0.44, +5.91] | 0.591 | +74 / -87 | -192 / -309 / -357 | 2026-03-09 (-708) | 1.22 | -2742 | 9 | +1.68 | +2.85 / +2.73 | 25: +2.0 / 26: +3.8 |
| 15:00 | iron ±5 (spread approval) | 0.50 | 0.00 | 878 | +16.30 | +5.43 [+2.09, +8.65] | 0.626 | +78 / -87 | -184 / -301 / -348 | 2026-03-09 (-691) | 1.50 | -2080 | 8 | +4.26 | +5.39 / +5.47 | 25: +4.6 / 26: +6.5 |
| 15:00 | iron ±5 (spread approval) | 0.50 | 0.01 | 878 | +12.30 | +4.19 [+0.90, +7.36] | 0.612 | +76 / -87 | -188 / -305 / -352 | 2026-03-09 (-699) | 1.36 | -2355 | 8 | +3.05 | +4.19 / +4.18 | 25: +3.4 / 26: +5.2 |
| 15:00 | iron ±5 (spread approval) | 0.50 | 0.02 | 878 | +8.30 | +2.98 [-0.26, +6.12] | 0.593 | +74 / -87 | -192 / -309 / -356 | 2026-03-09 (-707) | 1.23 | -2675 | 9 | +1.86 | +3.02 / +2.94 | 25: +2.2 / 26: +4.0 |

### T2. The same cells on FIT 2022-11-11 → 2024-12-31 (SPY + QQQ pooled)

| time | form | k | stress | n | mean $ | mean % [95 % CI] | win | PF | MDD $ | streak | wo5 % | SPY / QQQ % | by year % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:30 | long call ±5 | 0.00 | 0.00 | 1,048 | +6.75 | +2.25 [+0.47, +3.90] | 0.645 | 1.29 | -2196 | 8 | +1.56 | +1.56 / +2.93 | 22: +2.1 / 23: +2.7 / 24: +1.8 |
| 15:30 | long call ±5 | 0.00 | 0.01 | 1,048 | +2.75 | +1.25 [-0.50, +2.87] | 0.615 | 1.11 | -2672 | 9 | +0.58 | +0.58 / +1.91 | 22: +1.1 / 23: +1.8 / 24: +0.8 |
| 15:30 | long call ±5 | 0.00 | 0.02 | 1,048 | -1.25 | +0.27 [-1.45, +1.88] | 0.594 | 0.95 | -3878 | 9 | -0.38 | -0.38 / +0.92 | 22: +0.1 / 23: +0.8 / 24: -0.2 |
| 15:30 | long call ±5 | 0.25 | 0.00 | 1,048 | +9.15 | +2.84 [+1.04, +4.50] | 0.663 | 1.41 | -1895 | 8 | +2.14 | +2.14 / +3.52 | 22: +2.6 / 23: +3.2 / 24: +2.5 |
| 15:30 | long call ±5 | 0.25 | 0.01 | 1,048 | +5.15 | +1.83 [+0.06, +3.46] | 0.631 | 1.22 | -2300 | 9 | +1.15 | +1.15 / +2.50 | 22: +1.6 / 23: +2.2 / 24: +1.5 |
| 15:30 | long call ±5 | 0.25 | 0.02 | 1,048 | +1.15 | +0.84 [-0.90, +2.45] | 0.604 | 1.05 | -3025 | 9 | +0.18 | +0.18 / +1.49 | 22: +0.7 / 23: +1.2 / 24: +0.4 |
| 15:30 | long call ±5 | 0.50 | 0.00 | 1,048 | +11.55 | +3.43 [+1.62, +5.11] | 0.677 | 1.53 | -1761 | 8 | +2.73 | +2.73 / +4.13 | 22: +3.2 / 23: +3.7 / 24: +3.2 |
| 15:30 | long call ±5 | 0.50 | 0.01 | 1,048 | +7.55 | +2.41 [+0.62, +4.06] | 0.649 | 1.33 | -1927 | 8 | +1.73 | +1.73 / +3.09 | 22: +2.2 / 23: +2.7 / 24: +2.2 |
| 15:30 | long call ±5 | 0.50 | 0.02 | 1,048 | +3.55 | +1.41 [-0.34, +3.03] | 0.622 | 1.15 | -2403 | 9 | +0.75 | +0.75 / +2.07 | 22: +1.2 / 23: +1.7 / 24: +1.1 |
| 15:30 | long put ±5 | 0.00 | 0.00 | 1,049 | +5.30 | +1.87 [+0.09, +3.53] | 0.631 | 1.22 | -2089 | 9 | +1.21 | +1.05 / +2.69 | 22: +1.8 / 23: +2.4 / 24: +1.3 |
| 15:30 | long put ±5 | 0.00 | 0.01 | 1,049 | +1.30 | +0.88 [-0.87, +2.52] | 0.605 | 1.05 | -3029 | 9 | +0.23 | +0.08 / +1.68 | 22: +0.9 / 23: +1.4 / 24: +0.3 |
| 15:30 | long put ±5 | 0.00 | 0.02 | 1,049 | -2.70 | -0.09 [-1.82, +1.52] | 0.577 | 0.90 | -4343 | 9 | -0.72 | -0.87 / +0.69 | 22: -0.1 / 23: +0.5 / 24: -0.7 |
| 15:30 | long put ±5 | 0.25 | 0.00 | 1,049 | +8.10 | +2.55 [+0.75, +4.22] | 0.649 | 1.36 | -1776 | 9 | +1.86 | +1.74 / +3.36 | 22: +2.5 / 23: +2.9 / 24: +2.2 |
| 15:30 | long put ±5 | 0.25 | 0.01 | 1,049 | +4.10 | +1.55 [-0.22, +3.20] | 0.626 | 1.17 | -2169 | 9 | +0.88 | +0.76 / +2.33 | 22: +1.5 / 23: +2.0 / 24: +1.1 |
| 15:30 | long put ±5 | 0.25 | 0.02 | 1,049 | +0.10 | +0.57 [-1.17, +2.18] | 0.600 | 1.00 | -3336 | 9 | -0.09 | -0.20 / +1.33 | 22: +0.5 / 23: +1.0 / 24: +0.1 |
| 15:30 | long put ±5 | 0.50 | 0.00 | 1,049 | +10.89 | +3.25 [+1.44, +4.93] | 0.669 | 1.50 | -1566 | 9 | +2.55 | +2.45 / +4.04 | 22: +3.1 / 23: +3.5 / 24: +3.0 |
| 15:30 | long put ±5 | 0.50 | 0.01 | 1,049 | +6.89 | +2.23 [+0.45, +3.88] | 0.640 | 1.30 | -1770 | 9 | +1.55 | +1.45 / +3.00 | 22: +2.1 / 23: +2.5 / 24: +2.0 |
| 15:30 | long put ±5 | 0.50 | 0.02 | 1,049 | +2.89 | +1.23 [-0.52, +2.85] | 0.617 | 1.12 | -2351 | 9 | +0.57 | +0.48 / +1.99 | 22: +1.1 / 23: +1.5 / 24: +1.0 |
| 15:30 | iron ±5 (spread approval) | 0.00 | 0.00 | 1,048 | +13.45 | +3.88 [+2.06, +5.56] | 0.683 | 1.65 | -1514 | 8 | +3.19 | +3.21 / +4.55 | 22: +3.6 / 23: +3.9 / 24: +3.9 |
| 15:30 | iron ±5 (spread approval) | 0.00 | 0.01 | 1,048 | +9.45 | +2.85 [+1.06, +4.51] | 0.666 | 1.43 | -1586 | 8 | +2.18 | +2.20 / +3.51 | 22: +2.5 / 23: +2.9 / 24: +2.9 |
| 15:30 | iron ±5 (spread approval) | 0.00 | 0.02 | 1,048 | +5.45 | +1.85 [+0.08, +3.48] | 0.631 | 1.23 | -1966 | 9 | +1.19 | +1.21 / +2.48 | 22: +1.5 / 23: +1.9 / 24: +1.8 |
| 15:30 | iron ±5 (spread approval) | 0.25 | 0.00 | 1,048 | +14.07 | +4.05 [+2.22, +5.73] | 0.686 | 1.68 | -1502 | 8 | +3.33 | +3.35 / +4.74 | 22: +3.7 / 23: +4.0 / 24: +4.1 |
| 15:30 | iron ±5 (spread approval) | 0.25 | 0.01 | 1,048 | +10.07 | +3.01 [+1.21, +4.67] | 0.668 | 1.46 | -1574 | 8 | +2.32 | +2.34 / +3.68 | 22: +2.7 / 23: +3.0 / 24: +3.0 |
| 15:30 | iron ±5 (spread approval) | 0.25 | 0.02 | 1,048 | +6.07 | +2.00 [+0.23, +3.64] | 0.635 | 1.26 | -1894 | 9 | +1.33 | +1.34 / +2.65 | 22: +1.7 / 23: +2.1 / 24: +2.0 |
| 15:30 | iron ±5 (spread approval) | 0.50 | 0.00 | 1,048 | +14.68 | +4.21 [+2.38, +5.90] | 0.689 | 1.72 | -1489 | 8 | +3.49 | +3.50 / +4.92 | 22: +3.9 / 23: +4.2 / 24: +4.3 |
| 15:30 | iron ±5 (spread approval) | 0.50 | 0.01 | 1,048 | +10.68 | +3.17 [+1.37, +4.84] | 0.668 | 1.49 | -1561 | 8 | +2.47 | +2.48 / +3.86 | 22: +2.9 / 23: +3.2 / 24: +3.2 |
| 15:30 | iron ±5 (spread approval) | 0.50 | 0.02 | 1,048 | +6.68 | +2.16 [+0.38, +3.80] | 0.638 | 1.29 | -1822 | 9 | +1.48 | +1.48 / +2.83 | 22: +1.9 / 23: +2.2 / 24: +2.1 |
| 15:00 | long call ±5 | 0.00 | 0.00 | 1,047 | +11.25 | +3.36 [+1.39, +5.33] | 0.656 | 1.44 | -1339 | 8 | +2.53 | +2.81 / +3.91 | 22: +6.0 / 23: +3.4 / 24: +3.0 |
| 15:00 | long call ±5 | 0.00 | 0.01 | 1,047 | +7.25 | +2.30 [+0.36, +4.26] | 0.636 | 1.27 | -1731 | 8 | +1.50 | +1.77 / +2.83 | 22: +4.8 / 23: +2.4 / 24: +1.9 |
| 15:00 | long call ±5 | 0.00 | 0.02 | 1,047 | +3.25 | +1.27 [-0.65, +3.19] | 0.607 | 1.11 | -2755 | 9 | +0.48 | +0.75 / +1.78 | 22: +3.7 / 23: +1.3 / 24: +0.9 |
| 15:00 | long call ±5 | 0.25 | 0.00 | 1,047 | +13.76 | +4.01 [+2.03, +6.00] | 0.670 | 1.56 | -1285 | 8 | +3.18 | +3.47 / +4.56 | 22: +6.7 / 23: +3.9 / 24: +3.8 |
| 15:00 | long call ±5 | 0.25 | 0.01 | 1,047 | +9.76 | +2.94 [+0.99, +4.89] | 0.654 | 1.38 | -1357 | 8 | +2.13 | +2.42 / +3.47 | 22: +5.5 / 23: +2.9 / 24: +2.7 |
| 15:00 | long call ±5 | 0.25 | 0.02 | 1,047 | +5.76 | +1.89 [-0.04, +3.82] | 0.625 | 1.21 | -2075 | 9 | +1.10 | +1.38 / +2.41 | 22: +4.4 / 23: +1.9 / 24: +1.6 |
| 15:00 | long call ±5 | 0.50 | 0.00 | 1,047 | +16.26 | +4.68 [+2.67, +6.70] | 0.680 | 1.69 | -1231 | 8 | +3.83 | +4.14 / +5.23 | 22: +7.3 / 23: +4.5 / 24: +4.5 |
| 15:00 | long call ±5 | 0.50 | 0.01 | 1,047 | +12.26 | +3.60 [+1.62, +5.57] | 0.662 | 1.49 | -1303 | 8 | +2.77 | +3.07 / +4.12 | 22: +6.2 / 23: +3.4 / 24: +3.4 |
| 15:00 | long call ±5 | 0.50 | 0.02 | 1,047 | +8.26 | +2.53 [+0.59, +4.47] | 0.644 | 1.31 | -1524 | 8 | +1.73 | +2.03 / +3.04 | 22: +5.0 / 23: +2.4 / 24: +2.3 |
| 15:00 | long put ±5 | 0.00 | 0.00 | 1,048 | +8.38 | +2.68 [+0.71, +4.64] | 0.631 | 1.31 | -2020 | 9 | +1.85 | +1.66 / +3.69 | 22: +6.0 / 23: +2.9 / 24: +2.0 |
| 15:00 | long put ±5 | 0.00 | 0.01 | 1,048 | +4.38 | +1.63 [-0.30, +3.57] | 0.615 | 1.16 | -3036 | 9 | +0.83 | +0.64 / +2.62 | 22: +4.8 / 23: +1.9 / 24: +0.9 |
| 15:00 | long put ±5 | 0.00 | 0.02 | 1,048 | +0.38 | +0.61 [-1.30, +2.51] | 0.586 | 1.01 | -4227 | 9 | -0.17 | -0.36 / +1.57 | 22: +3.7 / 23: +0.9 / 24: -0.1 |
| 15:00 | long put ±5 | 0.25 | 0.00 | 1,048 | +11.60 | +3.48 [+1.50, +5.48] | 0.647 | 1.46 | -1329 | 9 | +2.65 | +2.58 / +4.38 | 22: +6.6 / 23: +3.6 / 24: +3.0 |
| 15:00 | long put ±5 | 0.25 | 0.01 | 1,048 | +7.60 | +2.42 [+0.47, +4.38] | 0.629 | 1.28 | -2057 | 9 | +1.61 | +1.54 / +3.30 | 22: +5.5 / 23: +2.5 / 24: +1.9 |
| 15:00 | long put ±5 | 0.25 | 0.02 | 1,048 | +3.60 | +1.38 [-0.53, +3.30] | 0.601 | 1.13 | -3081 | 9 | +0.59 | +0.52 / +2.24 | 22: +4.4 / 23: +1.5 / 24: +0.8 |
| 15:00 | long put ±5 | 0.50 | 0.00 | 1,048 | +14.81 | +4.31 [+2.31, +6.33] | 0.673 | 1.62 | -1220 | 9 | +3.46 | +3.52 / +5.09 | 22: +7.3 / 23: +4.2 / 24: +4.0 |
| 15:00 | long put ±5 | 0.50 | 0.01 | 1,048 | +10.81 | +3.23 [+1.26, +5.21] | 0.647 | 1.43 | -1345 | 9 | +2.40 | +2.47 / +3.99 | 22: +6.2 / 23: +3.2 / 24: +2.9 |
| 15:00 | long put ±5 | 0.50 | 0.02 | 1,048 | +6.81 | +2.17 [+0.23, +4.12] | 0.627 | 1.25 | -2102 | 9 | +1.37 | +1.43 / +2.91 | 22: +5.0 / 23: +2.1 / 24: +1.8 |
| 15:00 | iron ±5 (spread approval) | 0.00 | 0.00 | 1,047 | +18.52 | +5.26 [+3.21, +7.31] | 0.691 | 1.81 | -1183 | 8 | +4.42 | +4.84 / +5.69 | 22: +7.7 / 23: +4.8 / 24: +5.4 |
| 15:00 | iron ±5 (spread approval) | 0.00 | 0.01 | 1,047 | +14.52 | +4.17 [+2.15, +6.18] | 0.671 | 1.60 | -1255 | 8 | +3.34 | +3.76 / +4.58 | 22: +6.5 / 23: +3.8 / 24: +4.3 |
| 15:00 | iron ±5 (spread approval) | 0.00 | 0.02 | 1,047 | +10.52 | +3.09 [+1.11, +5.08] | 0.653 | 1.41 | -1339 | 8 | +2.29 | +2.70 / +3.49 | 22: +5.4 / 23: +2.7 / 24: +3.1 |
| 15:00 | iron ±5 (spread approval) | 0.25 | 0.00 | 1,047 | +19.13 | +5.43 [+3.37, +7.48] | 0.694 | 1.85 | -1173 | 8 | +4.58 | +4.99 / +5.88 | 22: +7.9 / 23: +5.0 / 24: +5.6 |
| 15:00 | iron ±5 (spread approval) | 0.25 | 0.01 | 1,047 | +15.13 | +4.33 [+2.31, +6.36] | 0.676 | 1.63 | -1245 | 8 | +3.50 | +3.91 / +4.76 | 22: +6.8 / 23: +3.9 / 24: +4.4 |
| 15:00 | iron ±5 (spread approval) | 0.25 | 0.02 | 1,047 | +11.13 | +3.26 [+1.26, +5.25] | 0.657 | 1.44 | -1325 | 8 | +2.45 | +2.84 / +3.67 | 22: +5.6 / 23: +2.9 / 24: +3.3 |
| 15:00 | iron ±5 (spread approval) | 0.50 | 0.00 | 1,047 | +19.73 | +5.61 [+3.54, +7.66] | 0.698 | 1.88 | -1163 | 8 | +4.75 | +5.15 / +6.07 | 22: +8.2 / 23: +5.1 / 24: +5.7 |
| 15:00 | iron ±5 (spread approval) | 0.50 | 0.01 | 1,047 | +15.73 | +4.50 [+2.47, +6.53] | 0.678 | 1.67 | -1235 | 8 | +3.67 | +4.06 / +4.95 | 22: +7.0 / 23: +4.1 / 24: +4.6 |
| 15:00 | iron ±5 (spread approval) | 0.50 | 0.02 | 1,047 | +11.73 | +3.42 [+1.42, +5.43] | 0.659 | 1.47 | -1311 | 8 | +2.61 | +2.99 / +3.85 | 22: +5.8 / 23: +3.0 / 24: +3.5 |

### T3. By name, OOS, k = 0 and the stresses (and k = 0.25 / 0.5 at stress 0)

| time | name | form | k | stress | n | mean $ | mean % [95 % CI] | win | PF | MDD $ | streak | wo5 % | worst session | by year % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:30 | SPY | long call ±5 | 0.00 | 0.00 | 440 | +13.08 | +4.22 [+1.89, +6.71] | 0.643 | 1.53 | -1121 | 4 | +3.26 | 2025-05-22 (-293) | 25: +3.0 / 26: +5.8 |
| 15:30 | SPY | long call ±5 | 0.00 | 0.01 | 440 | +9.08 | +3.12 [+0.80, +5.58] | 0.623 | 1.35 | -1202 | 4 | +2.18 | 2025-05-22 (-297) | 25: +1.9 / 26: +4.7 |
| 15:30 | SPY | long call ±5 | 0.00 | 0.02 | 440 | +5.08 | +2.04 [-0.25, +4.47] | 0.600 | 1.18 | -1314 | 4 | +1.13 | 2025-05-22 (-301) | 25: +0.8 / 26: +3.7 |
| 15:30 | SPY | long call ±5 | 0.25 | 0.00 | 440 | +14.88 | +4.73 [+2.37, +7.23] | 0.645 | 1.62 | -1092 | 4 | +3.77 | 2025-05-22 (-291) | 25: +3.5 / 26: +6.3 |
| 15:30 | SPY | long call ±5 | 0.50 | 0.00 | 440 | +16.68 | +5.25 [+2.86, +7.79] | 0.659 | 1.71 | -1064 | 4 | +4.28 | 2025-05-22 (-290) | 25: +4.0 / 26: +6.8 |
| 15:30 | SPY | long put ±5 | 0.00 | 0.00 | 440 | +12.77 | +4.16 [+1.77, +6.70] | 0.636 | 1.51 | -1106 | 4 | +3.19 | 2025-03-04 (-295) | 25: +2.9 / 26: +5.7 |
| 15:30 | SPY | long put ±5 | 0.00 | 0.01 | 440 | +8.77 | +3.06 [+0.70, +5.55] | 0.607 | 1.33 | -1195 | 4 | +2.11 | 2025-03-04 (-299) | 25: +1.8 / 26: +4.6 |
| 15:30 | SPY | long put ±5 | 0.00 | 0.02 | 440 | +4.77 | +1.99 [-0.34, +4.44] | 0.598 | 1.17 | -1307 | 6 | +1.06 | 2025-03-04 (-303) | 25: +0.7 / 26: +3.6 |
| 15:30 | SPY | long put ±5 | 0.25 | 0.00 | 440 | +14.75 | +4.72 [+2.31, +7.29] | 0.643 | 1.61 | -1074 | 4 | +3.74 | 2025-03-04 (-292) | 25: +3.5 / 26: +6.3 |
| 15:30 | SPY | long put ±5 | 0.50 | 0.00 | 440 | +16.72 | +5.28 [+2.85, +7.88] | 0.659 | 1.71 | -1042 | 4 | +4.30 | 2025-03-04 (-290) | 25: +4.1 / 26: +6.8 |
| 15:30 | SPY | iron ±5 (spread approval) | 0.00 | 0.00 | 440 | +17.66 | +5.54 [+3.12, +8.14] | 0.661 | 1.76 | -1039 | 4 | +4.58 | 2025-05-22 (-289) | 25: +4.3 / 26: +7.2 |
| 15:30 | SPY | iron ±5 (spread approval) | 0.00 | 0.01 | 440 | +13.66 | +4.41 [+2.02, +6.96] | 0.639 | 1.56 | -1107 | 4 | +3.47 | 2025-05-22 (-293) | 25: +3.1 / 26: +6.0 |
| 15:30 | SPY | iron ±5 (spread approval) | 0.00 | 0.02 | 440 | +9.66 | +3.31 [+0.94, +5.82] | 0.627 | 1.37 | -1193 | 4 | +2.38 | 2025-05-22 (-297) | 25: +2.0 / 26: +4.9 |
| 15:30 | SPY | iron ±5 (spread approval) | 0.25 | 0.00 | 440 | +18.23 | +5.71 [+3.29, +8.33] | 0.664 | 1.79 | -1029 | 4 | +4.74 | 2025-05-22 (-288) | 25: +4.5 / 26: +7.3 |
| 15:30 | SPY | iron ±5 (spread approval) | 0.50 | 0.00 | 440 | +18.80 | +5.89 [+3.46, +8.51] | 0.666 | 1.83 | -1019 | 4 | +4.91 | 2025-05-22 (-287) | 25: +4.6 / 26: +7.5 |
| 15:30 | QQQ | long call ±5 | 0.00 | 0.00 | 439 | +6.69 | +3.48 [+0.49, +6.53] | 0.601 | 1.20 | -1654 | 6 | +2.15 | 2025-03-04 (-335) | 25: +2.8 / 26: +4.3 |
| 15:30 | QQQ | long call ±5 | 0.00 | 0.01 | 439 | +2.69 | +2.33 [-0.60, +5.33] | 0.585 | 1.08 | -2018 | 6 | +1.04 | 2025-03-04 (-339) | 25: +1.7 / 26: +3.1 |
| 15:30 | QQQ | long call ±5 | 0.00 | 0.02 | 439 | -1.31 | +1.21 [-1.67, +4.15] | 0.563 | 0.96 | -2382 | 7 | -0.05 | 2025-03-04 (-343) | 25: +0.6 / 26: +2.0 |
| 15:30 | QQQ | long call ±5 | 0.25 | 0.00 | 439 | +10.03 | +4.39 [+1.38, +7.46] | 0.613 | 1.31 | -1332 | 6 | +3.05 | 2026-05-18 (-331) | 25: +3.9 / 26: +5.1 |
| 15:30 | QQQ | long call ±5 | 0.50 | 0.00 | 439 | +13.37 | +5.32 [+2.26, +8.43] | 0.617 | 1.44 | -1242 | 6 | +3.97 | 2026-05-18 (-328) | 25: +4.9 / 26: +5.9 |
| 15:30 | QQQ | long put ±5 | 0.00 | 0.00 | 439 | +5.42 | +3.16 [+0.13, +6.17] | 0.597 | 1.16 | -1765 | 5 | +1.84 | 2025-03-04 (-347) | 25: +2.5 / 26: +3.9 |
| 15:30 | QQQ | long put ±5 | 0.00 | 0.01 | 439 | +1.42 | +2.01 [-0.95, +4.99] | 0.574 | 1.04 | -2129 | 5 | +0.73 | 2025-03-04 (-351) | 25: +1.4 / 26: +2.8 |
| 15:30 | QQQ | long put ±5 | 0.00 | 0.02 | 439 | -2.58 | +0.90 [-2.01, +3.83] | 0.558 | 0.93 | -2493 | 5 | -0.35 | 2025-03-04 (-355) | 25: +0.3 / 26: +1.7 |
| 15:30 | QQQ | long put ±5 | 0.25 | 0.00 | 439 | +9.22 | +4.18 [+1.12, +7.23] | 0.620 | 1.29 | -1337 | 5 | +2.86 | 2025-03-04 (-333) | 25: +3.7 / 26: +4.8 |
| 15:30 | QQQ | long put ±5 | 0.50 | 0.00 | 439 | +13.02 | +5.23 [+2.16, +8.33] | 0.629 | 1.43 | -1236 | 4 | +3.87 | 2026-05-18 (-321) | 25: +4.9 / 26: +5.7 |
| 15:30 | QQQ | iron ±5 (spread approval) | 0.00 | 0.00 | 439 | +17.26 | +6.38 [+3.29, +9.47] | 0.642 | 1.59 | -1138 | 5 | +5.08 | 2026-05-18 (-323) | 25: +6.1 / 26: +6.7 |
| 15:30 | QQQ | iron ±5 (spread approval) | 0.00 | 0.01 | 439 | +13.26 | +5.16 [+2.14, +8.19] | 0.631 | 1.44 | -1242 | 5 | +3.90 | 2026-05-18 (-327) | 25: +4.9 / 26: +5.5 |
| 15:30 | QQQ | iron ±5 (spread approval) | 0.00 | 0.02 | 439 | +9.26 | +3.98 [+1.02, +6.97] | 0.615 | 1.29 | -1346 | 5 | +2.75 | 2026-05-18 (-331) | 25: +3.8 / 26: +4.3 |
| 15:30 | QQQ | iron ±5 (spread approval) | 0.25 | 0.00 | 439 | +17.91 | +6.59 [+3.49, +9.70] | 0.647 | 1.62 | -1118 | 5 | +5.29 | 2026-05-18 (-322) | 25: +6.4 / 26: +6.9 |
| 15:30 | QQQ | iron ±5 (spread approval) | 0.50 | 0.00 | 439 | +18.56 | +6.80 [+3.70, +9.93] | 0.651 | 1.65 | -1099 | 4 | +5.44 | 2026-05-18 (-321) | 25: +6.6 / 26: +7.1 |
| 15:00 | SPY | long call ±5 | 0.00 | 0.00 | 440 | +10.53 | +3.40 [+0.28, +6.34] | 0.616 | 1.33 | -1260 | 5 | +2.19 | 2026-03-09 (-345) | 25: +2.1 / 26: +5.1 |
| 15:00 | SPY | long call ±5 | 0.00 | 0.01 | 440 | +6.53 | +2.25 [-0.83, +5.14] | 0.598 | 1.19 | -1420 | 5 | +1.07 | 2026-03-09 (-349) | 25: +0.9 / 26: +3.9 |
| 15:00 | SPY | long call ±5 | 0.00 | 0.02 | 440 | +2.53 | +1.12 [-1.91, +3.97] | 0.580 | 1.07 | -1664 | 5 | -0.02 | 2026-03-09 (-353) | 25: -0.2 / 26: +2.8 |
| 15:00 | SPY | long call ±5 | 0.25 | 0.00 | 440 | +12.62 | +3.98 [+0.82, +6.95] | 0.623 | 1.40 | -1144 | 5 | +2.76 | 2026-03-09 (-342) | 25: +2.7 / 26: +5.7 |
| 15:00 | SPY | long call ±5 | 0.50 | 0.00 | 440 | +14.70 | +4.57 [+1.41, +7.56] | 0.627 | 1.48 | -1029 | 5 | +3.34 | 2026-03-09 (-339) | 25: +3.2 / 26: +6.3 |
| 15:00 | SPY | long put ±5 | 0.00 | 0.00 | 440 | +8.44 | +2.90 [-0.22, +6.00] | 0.605 | 1.25 | -1554 | 6 | +1.68 | 2026-03-09 (-349) | 25: +1.3 / 26: +4.9 |
| 15:00 | SPY | long put ±5 | 0.00 | 0.01 | 440 | +4.44 | +1.76 [-1.31, +4.79] | 0.584 | 1.13 | -1825 | 6 | +0.57 | 2026-03-09 (-353) | 25: +0.2 / 26: +3.8 |
| 15:00 | SPY | long put ±5 | 0.00 | 0.02 | 440 | +0.44 | +0.64 [-2.37, +3.62] | 0.566 | 1.01 | -2417 | 6 | -0.51 | 2026-03-09 (-357) | 25: -0.9 / 26: +2.7 |
| 15:00 | SPY | long put ±5 | 0.25 | 0.00 | 440 | +11.18 | +3.64 [+0.53, +6.74] | 0.609 | 1.35 | -1235 | 6 | +2.41 | 2026-03-09 (-347) | 25: +2.1 / 26: +5.6 |
| 15:00 | SPY | long put ±5 | 0.50 | 0.00 | 440 | +13.91 | +4.41 [+1.25, +7.54] | 0.623 | 1.45 | -995 | 5 | +3.17 | 2026-03-09 (-346) | 25: +3.0 / 26: +6.3 |
| 15:00 | SPY | iron ±5 (spread approval) | 0.00 | 0.00 | 440 | +16.32 | +5.03 [+1.91, +8.04] | 0.636 | 1.55 | -954 | 5 | +3.80 | 2026-03-09 (-344) | 25: +3.6 / 26: +6.8 |
| 15:00 | SPY | iron ±5 (spread approval) | 0.00 | 0.01 | 440 | +12.32 | +3.84 [+0.76, +6.79] | 0.623 | 1.39 | -1105 | 5 | +2.64 | 2026-03-09 (-348) | 25: +2.5 / 26: +5.6 |
| 15:00 | SPY | iron ±5 (spread approval) | 0.00 | 0.02 | 440 | +8.32 | +2.68 [-0.36, +5.57] | 0.598 | 1.25 | -1265 | 5 | +1.51 | 2026-03-09 (-352) | 25: +1.3 / 26: +4.5 |
| 15:00 | SPY | iron ±5 (spread approval) | 0.25 | 0.00 | 440 | +16.89 | +5.21 [+2.07, +8.24] | 0.636 | 1.57 | -924 | 5 | +3.97 | 2026-03-09 (-343) | 25: +3.8 / 26: +7.0 |
| 15:00 | SPY | iron ±5 (spread approval) | 0.50 | 0.00 | 440 | +17.46 | +5.39 [+2.24, +8.44] | 0.639 | 1.60 | -894 | 5 | +4.14 | 2026-03-09 (-343) | 25: +4.0 / 26: +7.1 |
| 15:00 | QQQ | long call ±5 | 0.00 | 0.00 | 438 | -1.51 | +0.90 [-2.63, +4.56] | 0.555 | 0.97 | -2306 | 5 | -0.58 | 2026-05-12 (-471) | 25: +0.3 / 26: +1.7 |
| 15:00 | QQQ | long call ±5 | 0.00 | 0.01 | 438 | -5.51 | -0.28 [-3.75, +3.32] | 0.546 | 0.88 | -3750 | 5 | -1.71 | 2026-05-12 (-475) | 25: -0.9 / 26: +0.5 |
| 15:00 | QQQ | long call ±5 | 0.00 | 0.02 | 438 | -9.51 | -1.42 [-4.83, +2.11] | 0.541 | 0.80 | -5194 | 5 | -2.82 | 2026-05-12 (-479) | 25: -2.0 / 26: -0.7 |
| 15:00 | QQQ | long call ±5 | 0.25 | 0.00 | 438 | +2.92 | +2.08 [-1.46, +5.77] | 0.564 | 1.07 | -1898 | 5 | +0.59 | 2026-05-12 (-451) | 25: +1.5 / 26: +2.8 |
| 15:00 | QQQ | long call ±5 | 0.50 | 0.00 | 438 | +7.35 | +3.31 [-0.26, +7.06] | 0.587 | 1.19 | -1698 | 5 | +1.79 | 2026-05-12 (-432) | 25: +2.8 / 26: +4.0 |
| 15:00 | QQQ | long put ±5 | 0.00 | 0.00 | 438 | -4.07 | +0.19 [-3.23, +3.69] | 0.532 | 0.91 | -3463 | 7 | -1.29 | 2026-03-09 (-366) | 25: -1.1 / 26: +1.8 |
| 15:00 | QQQ | long put ±5 | 0.00 | 0.01 | 438 | -8.07 | -0.97 [-4.33, +2.47] | 0.530 | 0.83 | -4899 | 7 | -2.41 | 2026-03-09 (-370) | 25: -2.2 / 26: +0.6 |
| 15:00 | QQQ | long put ±5 | 0.00 | 0.02 | 438 | -12.07 | -2.10 [-5.43, +1.28] | 0.521 | 0.75 | -6335 | 7 | -3.50 | 2026-03-09 (-374) | 25: -3.3 / 26: -0.6 |
| 15:00 | QQQ | long put ±5 | 0.25 | 0.00 | 438 | +1.29 | +1.60 [-1.88, +5.15] | 0.553 | 1.03 | -1762 | 7 | +0.10 | 2026-03-09 (-361) | 25: +0.5 / 26: +2.9 |
| 15:00 | QQQ | long put ±5 | 0.50 | 0.00 | 438 | +6.66 | +3.08 [-0.47, +6.70] | 0.575 | 1.17 | -1577 | 5 | +1.56 | 2026-03-09 (-357) | 25: +2.2 / 26: +4.1 |
| 15:00 | QQQ | iron ±5 (spread approval) | 0.00 | 0.00 | 438 | +13.86 | +5.03 [+1.37, +8.69] | 0.610 | 1.38 | -1345 | 4 | +3.53 | 2026-03-09 (-350) | 25: +4.7 / 26: +5.4 |
| 15:00 | QQQ | iron ±5 (spread approval) | 0.00 | 0.01 | 438 | +9.86 | +3.76 [+0.18, +7.36] | 0.591 | 1.26 | -1461 | 5 | +2.30 | 2026-03-09 (-354) | 25: +3.5 / 26: +4.1 |
| 15:00 | QQQ | iron ±5 (spread approval) | 0.00 | 0.02 | 438 | +5.86 | +2.52 [-0.98, +6.06] | 0.582 | 1.15 | -1577 | 5 | +1.10 | 2026-03-09 (-358) | 25: +2.3 / 26: +2.9 |
| 15:00 | QQQ | iron ±5 (spread approval) | 0.25 | 0.00 | 438 | +14.49 | +5.25 [+1.58, +8.92] | 0.614 | 1.40 | -1323 | 4 | +3.73 | 2026-03-09 (-349) | 25: +5.0 / 26: +5.6 |
| 15:00 | QQQ | iron ±5 (spread approval) | 0.50 | 0.00 | 438 | +15.13 | +5.47 [+1.79, +9.15] | 0.614 | 1.43 | -1302 | 4 | +3.94 | 2026-03-09 (-348) | 25: +5.2 / 26: +5.8 |

### T4. Break-even fill improvement k*, the gross (mid-to-mid) result and friction

k* = −mean(k = 0) / (100 × mean slip): the k at which the OOS mean crosses zero; negative = the cell stays positive even at fills WORSE than the NBBO, by |k*| × the slip. "$/leg to zero" = mean(k = 0) / 400: the worse-fill per leg that takes the mean to zero. Gross = (payoff − mid package) × 100, no fees; friction = gross − net(k = 0) = NBBO slip + $2.60 of fees.

| time | name | form | period | n | mean $ at k = 0 | slip $ (NBBO − mid, a fly) | mean at k = 0.25 / 0.5 / 1 (mid) | k* | $/leg to zero | gross $ | friction $ | friction / gross |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 15:30 | QQQ | long call ±5 | fit | 526 | +8.36 | 9.59 (med 8.00) | +10.76 / +13.16 / +17.95 | -0.87 | +0.0209 | +20.55 | 12.19 | 0.59 |
| 15:30 | QQQ | long call ±5 | oos | 439 | +6.69 | 13.36 (med 11.50) | +10.03 / +13.37 / +20.04 | -0.50 | +0.0167 | +22.64 | 15.96 | 0.70 |
| 15:30 | QQQ | iron ±5 (spread approval) | fit | 526 | +14.99 | 2.69 (med 2.50) | +15.66 / +16.33 / +17.68 | -5.56 | +0.0375 | +20.28 | 5.29 | 0.26 |
| 15:30 | QQQ | iron ±5 (spread approval) | oos | 439 | +17.26 | 2.60 (med 2.50) | +17.91 / +18.56 / +19.85 | -6.64 | +0.0431 | +22.45 | 5.20 | 0.23 |
| 15:30 | QQQ | long put ±5 | fit | 527 | +7.60 | 10.68 (med 8.50) | +10.28 / +12.95 / +18.29 | -0.71 | +0.0190 | +20.89 | 13.28 | 0.64 |
| 15:30 | QQQ | long put ±5 | oos | 439 | +5.42 | 15.21 (med 13.50) | +9.22 / +13.02 / +20.63 | -0.36 | +0.0135 | +23.23 | 17.81 | 0.77 |
| 15:30 | SPY | long call ±5 | fit | 522 | +5.12 | 9.62 (med 7.75) | +7.53 / +9.93 / +14.74 | -0.53 | +0.0128 | +17.34 | 12.22 | 0.70 |
| 15:30 | SPY | long call ±5 | oos | 440 | +13.08 | 7.19 (med 6.00) | +14.88 / +16.68 / +20.28 | -1.82 | +0.0327 | +22.88 | 9.79 | 0.43 |
| 15:30 | SPY | iron ±5 (spread approval) | fit | 522 | +11.90 | 2.23 (med 2.00) | +12.46 / +13.02 / +14.14 | -5.33 | +0.0298 | +16.74 | 4.83 | 0.29 |
| 15:30 | SPY | iron ±5 (spread approval) | oos | 440 | +17.66 | 2.28 (med 2.00) | +18.23 / +18.80 / +19.94 | -7.74 | +0.0441 | +22.54 | 4.88 | 0.22 |
| 15:30 | SPY | long put ±5 | fit | 522 | +2.97 | 11.69 (med 9.00) | +5.90 / +8.82 / +14.66 | -0.25 | +0.0074 | +17.26 | 14.29 | 0.83 |
| 15:30 | SPY | long put ±5 | oos | 440 | +12.77 | 7.88 (med 7.00) | +14.75 / +16.72 / +20.66 | -1.62 | +0.0319 | +23.26 | 10.48 | 0.45 |
| 15:30 | SPY+QQQ | long call ±5 | fit | 1,048 | +6.75 | 9.61 (med 8.00) | +9.15 / +11.55 / +16.35 | -0.70 | +0.0169 | +18.95 | 12.21 | 0.64 |
| 15:30 | SPY+QQQ | long call ±5 | oos | 879 | +9.89 | 10.27 (med 9.00) | +12.46 / +15.02 / +20.16 | -0.96 | +0.0247 | +22.76 | 12.87 | 0.57 |
| 15:30 | SPY+QQQ | iron ±5 (spread approval) | fit | 1,048 | +13.45 | 2.46 (med 2.50) | +14.07 / +14.68 / +15.91 | -5.46 | +0.0336 | +18.51 | 5.06 | 0.27 |
| 15:30 | SPY+QQQ | iron ±5 (spread approval) | oos | 879 | +17.46 | 2.44 (med 2.50) | +18.07 / +18.68 / +19.90 | -7.15 | +0.0436 | +22.50 | 5.04 | 0.22 |
| 15:30 | SPY+QQQ | long put ±5 | fit | 1,049 | +5.30 | 11.18 (med 9.00) | +8.10 / +10.89 / +16.48 | -0.47 | +0.0133 | +19.08 | 13.78 | 0.72 |
| 15:30 | SPY+QQQ | long put ±5 | oos | 879 | +9.10 | 11.54 (med 10.00) | +11.99 / +14.87 / +20.64 | -0.79 | +0.0228 | +23.24 | 14.14 | 0.61 |
| 15:00 | QQQ | long call ±5 | fit | 523 | +13.17 | 9.61 (med 8.00) | +15.58 / +17.98 / +22.79 | -1.37 | +0.0329 | +25.39 | 12.21 | 0.48 |
| 15:00 | QQQ | long call ±5 | oos | 438 | -1.51 | 17.71 (med 13.00) | +2.92 / +7.35 / +16.21 | +0.09 | -0.0038 | +18.81 | 20.31 | 1.08 |
| 15:00 | QQQ | iron ±5 (spread approval) | fit | 523 | +19.74 | 2.63 (med 2.50) | +20.40 / +21.06 / +22.37 | -7.51 | +0.0494 | +24.97 | 5.23 | 0.21 |
| 15:00 | QQQ | iron ±5 (spread approval) | oos | 438 | +13.86 | 2.54 (med 2.50) | +14.49 / +15.13 / +16.40 | -5.46 | +0.0346 | +19.00 | 5.14 | 0.27 |
| 15:00 | QQQ | long put ±5 | fit | 524 | +12.42 | 10.34 (med 8.50) | +15.01 / +17.59 / +22.76 | -1.20 | +0.0311 | +25.36 | 12.94 | 0.51 |
| 15:00 | QQQ | long put ±5 | oos | 438 | -4.07 | 21.44 (med 15.00) | +1.29 / +6.66 / +17.38 | +0.19 | -0.0102 | +19.98 | 24.04 | 1.20 |
| 15:00 | SPY | long call ±5 | fit | 524 | +9.32 | 10.45 (med 7.50) | +11.94 / +14.55 / +19.77 | -0.89 | +0.0233 | +22.37 | 13.05 | 0.58 |
| 15:00 | SPY | long call ±5 | oos | 440 | +10.53 | 8.35 (med 5.50) | +12.62 / +14.70 / +18.88 | -1.26 | +0.0263 | +21.48 | 10.95 | 0.51 |
| 15:00 | SPY | iron ±5 (spread approval) | fit | 524 | +17.30 | 2.23 (med 2.00) | +17.86 / +18.42 / +19.53 | -7.77 | +0.0433 | +22.13 | 4.83 | 0.22 |
| 15:00 | SPY | iron ±5 (spread approval) | oos | 440 | +16.32 | 2.27 (med 2.00) | +16.89 / +17.46 / +18.59 | -7.19 | +0.0408 | +21.19 | 4.87 | 0.23 |
| 15:00 | SPY | long put ±5 | fit | 524 | +4.34 | 15.37 (med 9.50) | +8.19 / +12.03 / +19.72 | -0.28 | +0.0109 | +22.32 | 17.97 | 0.81 |
| 15:00 | SPY | long put ±5 | oos | 440 | +8.44 | 10.93 (med 6.50) | +11.18 / +13.91 / +19.38 | -0.77 | +0.0211 | +21.98 | 13.53 | 0.62 |
| 15:00 | SPY+QQQ | long call ±5 | fit | 1,047 | +11.25 | 10.03 (med 7.50) | +13.76 / +16.26 / +21.28 | -1.12 | +0.0281 | +23.88 | 12.63 | 0.53 |
| 15:00 | SPY+QQQ | long call ±5 | oos | 878 | +4.52 | 13.02 (med 8.50) | +7.78 / +11.03 / +17.55 | -0.35 | +0.0113 | +20.15 | 15.62 | 0.78 |
| 15:00 | SPY+QQQ | iron ±5 (spread approval) | fit | 1,047 | +18.52 | 2.43 (med 2.50) | +19.13 / +19.73 / +20.95 | -7.62 | +0.0463 | +23.55 | 5.03 | 0.21 |
| 15:00 | SPY+QQQ | iron ±5 (spread approval) | oos | 878 | +15.09 | 2.41 (med 2.00) | +15.69 / +16.30 / +17.50 | -6.27 | +0.0377 | +20.10 | 5.01 | 0.25 |
| 15:00 | SPY+QQQ | long put ±5 | fit | 1,048 | +8.38 | 12.86 (med 9.00) | +11.60 / +14.81 / +21.24 | -0.65 | +0.0210 | +23.84 | 15.46 | 0.65 |
| 15:00 | SPY+QQQ | long put ±5 | oos | 878 | +2.20 | 16.18 (med 10.00) | +6.25 / +10.29 / +18.38 | -0.14 | +0.0055 | +20.98 | 18.78 | 0.89 |

### T5. Quoted size on the legs at the entry minute (the side hit: ask size on a long leg, bid size on a short leg)

| time | name | form | period | n | min leg size: median / p10 | every leg ≥ 1 | every leg ≥ its lots (2 on the short K0 of a call/put fly) | every leg ≥ 10 | NBBO max risk $ |
|---|---|---|---|---|---|---|---|---|---|
| 15:30 | QQQ | long call ±5 | fit | 526 | 48 / 6 | 100.0 % | 98.1 % | 85.2 % | 4.14 |
| 15:30 | QQQ | long call ±5 | oos | 439 | 30 / 8 | 100.0 % | 98.4 % | 88.4 % | 3.80 |
| 15:30 | QQQ | iron ±5 (spread approval) | fit | 526 | 36 / 5 | 100.0 % | 100.0 % | 85.2 % | 4.08 |
| 15:30 | QQQ | iron ±5 (spread approval) | oos | 439 | 30 / 6 | 100.0 % | 100.0 % | 86.3 % | 3.70 |
| 15:30 | QQQ | long put ±5 | fit | 527 | 50 / 6 | 100.0 % | 97.3 % | 86.0 % | 4.15 |
| 15:30 | QQQ | long put ±5 | oos | 439 | 33 / 8 | 100.0 % | 97.5 % | 88.6 % | 3.82 |
| 15:30 | SPY | long call ±5 | fit | 522 | 100 / 8 | 100.0 % | 98.7 % | 89.3 % | 4.17 |
| 15:30 | SPY | long call ±5 | oos | 440 | 51 / 8 | 100.0 % | 99.5 % | 87.7 % | 3.89 |
| 15:30 | SPY | iron ±5 (spread approval) | fit | 522 | 72 / 10 | 100.0 % | 100.0 % | 90.4 % | 4.10 |
| 15:30 | SPY | iron ±5 (spread approval) | oos | 440 | 92 / 20 | 100.0 % | 100.0 % | 94.3 % | 3.84 |
| 15:30 | SPY | long put ±5 | fit | 522 | 102 / 10 | 100.0 % | 97.7 % | 91.0 % | 4.19 |
| 15:30 | SPY | long put ±5 | oos | 440 | 60 / 8 | 100.0 % | 98.9 % | 87.5 % | 3.89 |
| 15:30 | SPY+QQQ | long call ±5 | fit | 1,048 | 68 / 6 | 100.0 % | 98.4 % | 87.2 % | 4.15 |
| 15:30 | SPY+QQQ | long call ±5 | oos | 879 | 35 / 8 | 100.0 % | 99.0 % | 88.1 % | 3.85 |
| 15:30 | SPY+QQQ | iron ±5 (spread approval) | fit | 1,048 | 52 / 6 | 100.0 % | 100.0 % | 87.8 % | 4.09 |
| 15:30 | SPY+QQQ | iron ±5 (spread approval) | oos | 879 | 49 / 10 | 100.0 % | 100.0 % | 90.3 % | 3.77 |
| 15:30 | SPY+QQQ | long put ±5 | fit | 1,049 | 77 / 7 | 100.0 % | 97.5 % | 88.5 % | 4.17 |
| 15:30 | SPY+QQQ | long put ±5 | oos | 879 | 40 / 8 | 100.0 % | 98.2 % | 88.1 % | 3.85 |
| 15:00 | QQQ | long call ±5 | fit | 523 | 50 / 5 | 100.0 % | 96.7 % | 80.9 % | 3.93 |
| 15:00 | QQQ | long call ±5 | oos | 438 | 30 / 5 | 100.0 % | 97.7 % | 85.4 % | 3.62 |
| 15:00 | QQQ | iron ±5 (spread approval) | fit | 523 | 33 / 2 | 100.0 % | 100.0 % | 80.7 % | 3.87 |
| 15:00 | QQQ | iron ±5 (spread approval) | oos | 438 | 30 / 5 | 100.0 % | 100.0 % | 84.5 % | 3.46 |
| 15:00 | QQQ | long put ±5 | fit | 524 | 50 / 4 | 100.0 % | 95.4 % | 81.9 % | 3.94 |
| 15:00 | QQQ | long put ±5 | oos | 438 | 33 / 6 | 100.0 % | 98.6 % | 87.4 % | 3.64 |
| 15:00 | SPY | long call ±5 | fit | 524 | 92 / 5 | 100.0 % | 97.7 % | 86.1 % | 3.99 |
| 15:00 | SPY | long call ±5 | oos | 440 | 52 / 7 | 100.0 % | 99.3 % | 85.0 % | 3.69 |
| 15:00 | SPY | iron ±5 (spread approval) | fit | 524 | 89 / 5 | 100.0 % | 100.0 % | 88.5 % | 3.91 |
| 15:00 | SPY | iron ±5 (spread approval) | oos | 440 | 102 / 10 | 100.0 % | 100.0 % | 91.4 % | 3.63 |
| 15:00 | SPY | long put ±5 | fit | 524 | 100 / 3 | 100.0 % | 97.5 % | 86.6 % | 4.04 |
| 15:00 | SPY | long put ±5 | oos | 440 | 56 / 5 | 100.0 % | 99.1 % | 83.6 % | 3.71 |
| 15:00 | SPY+QQQ | long call ±5 | fit | 1,047 | 68 / 5 | 100.0 % | 97.2 % | 83.5 % | 3.96 |
| 15:00 | SPY+QQQ | long call ±5 | oos | 878 | 35 / 6 | 100.0 % | 98.5 % | 85.2 % | 3.66 |
| 15:00 | SPY+QQQ | iron ±5 (spread approval) | fit | 1,047 | 56 / 4 | 100.0 % | 100.0 % | 84.6 % | 3.89 |
| 15:00 | SPY+QQQ | iron ±5 (spread approval) | oos | 878 | 51 / 6 | 100.0 % | 100.0 % | 87.9 % | 3.55 |
| 15:00 | SPY+QQQ | long put ±5 | fit | 1,048 | 75 / 4 | 100.0 % | 96.5 % | 84.3 % | 3.99 |
| 15:00 | SPY+QQQ | long put ±5 | oos | 878 | 39 / 5 | 100.0 % | 98.9 % | 85.5 % | 3.68 |

### T6. moc_mag Q1–Q2 vs Q3–Q5 (C's definition and scores), k = 0, % of max risk; diff = Q12 − Q345 with a session bootstrap in each group

| time | name | form | period | n Q12 / Q345 | Q12 % (win) | Q345 % (win) | diff [95 % CI] |
|---|---|---|---|---|---|---|---|
| 15:30 | QQQ | long call ±5 | fit | 204 / 307 | +2.74 (0.68) | +3.25 (0.64) | -0.51 [-4.03, +2.92] |
| 15:30 | QQQ | long call ±5 | oos | 189 / 250 | +0.01 (0.59) | +6.10 (0.61) | -6.09 [-11.79, -0.55] |
| 15:30 | QQQ | iron ±5 (spread approval) | fit | 204 / 307 | +4.13 (0.70) | +5.03 (0.67) | -0.90 [-4.47, +2.55] |
| 15:30 | QQQ | iron ±5 (spread approval) | oos | 189 / 250 | +2.56 (0.63) | +9.26 (0.65) | -6.70 [-12.54, -1.09] |
| 15:30 | QQQ | long put ±5 | fit | 204 / 308 | +2.58 (0.68) | +2.98 (0.62) | -0.40 [-3.78, +3.10] |
| 15:30 | QQQ | long put ±5 | oos | 189 / 250 | -0.44 (0.58) | +5.87 (0.61) | -6.32 [-11.96, -0.80] |
| 15:30 | SPY | long call ±5 | fit | 201 / 307 | +2.76 (0.66) | +0.71 (0.62) | +2.05 [-0.98, +5.32] |
| 15:30 | SPY | long call ±5 | oos | 192 / 248 | +1.95 (0.66) | +5.98 (0.63) | -4.03 [-8.54, +0.21] |
| 15:30 | SPY | iron ±5 (spread approval) | fit | 201 / 307 | +4.25 (0.73) | +2.48 (0.66) | +1.76 [-1.36, +5.06] |
| 15:30 | SPY | iron ±5 (spread approval) | oos | 192 / 248 | +3.04 (0.66) | +7.48 (0.66) | -4.44 [-9.03, -0.12] |
| 15:30 | SPY | long put ±5 | fit | 201 / 307 | +2.10 (0.65) | +0.28 (0.60) | +1.83 [-1.24, +5.08] |
| 15:30 | SPY | long put ±5 | oos | 192 / 248 | +2.00 (0.65) | +5.83 (0.63) | -3.83 [-8.30, +0.42] |
| 15:30 | SPY+QQQ | long call ±5 | fit | 405 / 614 | +2.75 (0.67) | +1.98 (0.63) | +0.77 [-2.19, +3.84] |
| 15:30 | SPY+QQQ | long call ±5 | oos | 381 / 498 | +0.99 (0.62) | +6.04 (0.62) | -5.05 [-9.81, -0.43] |
| 15:30 | SPY+QQQ | iron ±5 (spread approval) | fit | 405 / 614 | +4.19 (0.71) | +3.76 (0.66) | +0.43 [-2.60, +3.60] |
| 15:30 | SPY+QQQ | iron ±5 (spread approval) | oos | 381 / 498 | +2.80 (0.65) | +8.38 (0.65) | -5.58 [-10.36, -0.76] |
| 15:30 | SPY+QQQ | long put ±5 | fit | 405 / 615 | +2.34 (0.66) | +1.63 (0.61) | +0.71 [-2.51, +3.75] |
| 15:30 | SPY+QQQ | long put ±5 | oos | 381 / 498 | +0.79 (0.61) | +5.85 (0.62) | -5.07 [-9.77, -0.39] |
| 15:00 | QQQ | long call ±5 | fit | 203 / 306 | +4.76 (0.68) | +3.43 (0.65) | +1.33 [-2.58, +5.33] |
| 15:00 | QQQ | long call ±5 | oos | 178 / 260 | +4.05 (0.58) | -1.26 (0.53) | +5.31 [-1.39, +11.87] |
| 15:00 | QQQ | iron ±5 (spread approval) | fit | 203 / 306 | +6.26 (0.69) | +5.40 (0.68) | +0.85 [-3.17, +4.96] |
| 15:00 | QQQ | iron ±5 (spread approval) | oos | 178 / 260 | +8.14 (0.65) | +2.90 (0.58) | +5.24 [-1.75, +12.01] |
| 15:00 | QQQ | long put ±5 | fit | 204 / 306 | +4.51 (0.68) | +3.25 (0.64) | +1.26 [-2.76, +5.23] |
| 15:00 | QQQ | long put ±5 | oos | 178 / 260 | +3.18 (0.56) | -1.86 (0.52) | +5.04 [-1.71, +11.52] |
| 15:00 | SPY | long call ±5 | fit | 201 / 308 | +1.92 (0.63) | +3.37 (0.66) | -1.45 [-5.31, +2.03] |
| 15:00 | SPY | long call ±5 | oos | 186 / 254 | +2.80 (0.61) | +3.84 (0.62) | -1.04 [-6.68, +4.65] |
| 15:00 | SPY | iron ±5 (spread approval) | fit | 201 / 308 | +3.71 (0.68) | +5.58 (0.70) | -1.87 [-5.72, +1.69] |
| 15:00 | SPY | iron ±5 (spread approval) | oos | 186 / 254 | +3.99 (0.63) | +5.80 (0.64) | -1.81 [-7.59, +4.02] |
| 15:00 | SPY | long put ±5 | fit | 201 / 308 | +0.44 (0.56) | +2.38 (0.62) | -1.94 [-5.82, +1.56] |
| 15:00 | SPY | long put ±5 | oos | 186 / 254 | +1.87 (0.60) | +3.66 (0.61) | -1.79 [-7.45, +4.06] |
| 15:00 | SPY+QQQ | long call ±5 | fit | 404 / 614 | +3.35 (0.65) | +3.40 (0.65) | -0.05 [-3.52, +3.77] |
| 15:00 | SPY+QQQ | long call ±5 | oos | 364 / 514 | +3.41 (0.60) | +1.26 (0.58) | +2.15 [-3.88, +7.86] |
| 15:00 | SPY+QQQ | iron ±5 (spread approval) | fit | 404 / 614 | +4.99 (0.68) | +5.49 (0.69) | -0.50 [-4.07, +3.32] |
| 15:00 | SPY+QQQ | iron ±5 (spread approval) | oos | 364 / 514 | +6.02 (0.64) | +4.33 (0.61) | +1.69 [-4.64, +7.57] |
| 15:00 | SPY+QQQ | long put ±5 | fit | 405 / 614 | +2.49 (0.62) | +2.82 (0.63) | -0.32 [-3.92, +3.38] |
| 15:00 | SPY+QQQ | long put ±5 | oos | 364 / 514 | +2.51 (0.58) | +0.87 (0.56) | +1.64 [-4.42, +7.37] |

## 5. Reading the tables

**The primary cell** (T1, 15:30, SPY + QQQ pooled, long call ±5; OOS n 879 flies on 441 sessions, 438 with both names):

| fill | mean $ | mean % [CI] | win | PF | MDD / streak | wo5 % | SPY / QQQ % | 2025 / 2026 % |
|---|---|---|---|---|---|---|---|---|
| k = 0, NBBO | +9.89 | **+3.85 [+1.38, +6.24]** | 0.622 | 1.34 | −2,519 / 8 | +2.69 | +4.22 / +3.48 | +2.9 / +5.1 |
| k = 0, $0.01 a leg worse | +5.89 | **+2.73 [+0.29, +5.07]** | 0.604 | 1.19 | −2,727 / 8 | +1.59 | +3.12 / +2.33 | +1.8 / +3.9 |
| k = 0, $0.02 a leg worse | +1.89 | +1.63 [−0.76, +3.93] | 0.581 | 1.06 | −3,330 / 9 | +0.53 | +2.04 / +1.21 | +0.7 / +2.8 |
| k = 0.25 | +12.46 | +4.56 [+2.06, +6.98] | 0.629 | 1.45 | −2,386 / 8 | +3.39 | +4.73 / +4.39 | +3.7 / +5.7 |
| k = 0.25, $0.01 | +8.46 | +3.42 [+0.97, +5.80] | 0.617 | 1.29 | −2,594 / 8 | +2.29 | +3.62 / +3.22 | +2.5 / +4.6 |
| k = 0.5 | +15.02 | +5.29 [+2.75, +7.73] | 0.638 | 1.56 | −2,253 / 8 | +4.12 | +5.25 / +5.32 | +4.5 / +6.4 |
| k = 0.5, $0.02 | +7.02 | +3.00 [+0.55, +5.34] | 0.610 | 1.23 | −2,669 / 8 | +1.89 | +3.03 / +2.97 | +2.2 / +4.1 |

Tails at k = 0: average win +$63, average loss −$77, p5 −$160, p1 −$266, worst fly −$335, worst session 2025-03-04 (−$626
over its two flies); the NBBO debit is $1.57–4.77 (p5 2.66, median 4.00, p95 4.48), so max risk is about $400 a fly and the
worst fly lost 84 % of it. The pre-registered rule on this cell: (1) k = 0 mean > 0, CI clear of zero — **yes**; (2) the
$0.01 stress mean > 0 with CI clear of zero — **yes, narrowly** (lower bound +0.29; +0.14 to +0.33 over seeds 1–7 and
+0.22 with 10,000 draws); (3) wo5 > 0 — **yes** (+2.69 %; +1.59 % under the stress); (4) both names > 0 — **yes** (SPY
+4.22 %, QQQ +3.48 %; +3.12 / +2.33 under the stress). All four hold. 2025 alone is +2.9 % (+1.8 % stressed) and 2026
+5.1 % (+3.9 %), so neither OOS year carries the other.

**The put form** (the same cell in puts): +3.66 % [+1.16, +6.06] at k = 0, +2.54 % [+0.08, +4.90] at $0.01 (just clear),
+1.44 % [−0.99, +3.77] at $0.02; SPY +4.16 / QQQ +3.16; wo5 +2.49 %. It pays $1.27 a fly more slip than the call
(package $11.54 above the mid vs $10.27) for the same settlement payoff, so it is the weaker of the two in both periods, as
pre-registered. Either cash form is executable; the call is the one the rule names.

**k and k\*** (T4). The NBBO package of the ±5 call fly sits $10.27 a fly above its mid OOS (median $9.00; p5 $4, p95 $20;
44 % of entries within $8, 72 % within $12). So k = 0.25 is worth $2.57 a fly and k = 0.5 $5.13 — about a quarter and a
half of the k = 0 mean. k\* = −0.96: the OOS mean reaches zero only when the package fills $9.89 a fly WORSE than the
NBBO, which is $0.0247 a leg; the $0.02-a-leg stress ($8 a fly) is close to that, which is why it fails there. On fit
k\* was −0.70 ($0.0169 a leg). By name OOS: SPY k\* −1.82 (its slip is only $7.19), QQQ −0.50 (slip $13.36, mean $6.69).
The iron's package is $2.44 above its mid, k\* −7.15: improvement is irrelevant to it, and it survives $0.0436 a leg.

**Gross and friction** (T4). Mid-to-mid, no fees, the 15:30 ±5 fly earned +$22.76 a fly OOS (call), +$23.24 (put),
+$22.50 (iron) — the three forms are the same payoff, so their gross agrees within $0.74. Friction at k = 0 is $12.87 on
the call (slip $10.27 + fees $2.60 = 57 % of gross), $14.14 on the put (61 %), $5.04 on the iron (22 %). The fees alone are
11 % of the gross; the four legs' bid-ask is the rest. At 15:00 OOS the pooled call's friction is 78 % of its gross and
QQQ's 108 % (its slip grew to $17.71 OOS from $9.61 on fit), which is the whole of why the 15:00 cash forms do not pass.

**Quoted size** (T5; the side hit: the ask on a long leg, the bid on a short). At 15:30 OOS every leg quoted ≥ 1 contract
on 100.0 % of entries, ≥ its lots (2 on the short K0) on 99.0 % (call) / 98.2 % (put), ≥ 10 on 88 %; the smallest leg's
displayed size is 35 contracts at the median (SPY 51, QQQ 30), p10 8. One lot is within displayed size on essentially
every entry; the displayed legs are not a package quote, and a complex order's fill against the complex book is what k
stands for — unobserved here. The sizes say a 1-lot package is not size-constrained; they do not say it fills at k = 0.

**15:00, the secondary** (T1, T3). The cash forms fail the rule at 15:00 OOS: call +2.15 % [−0.99, +5.20] (QQQ +0.90 %,
wo5 +0.99 %; $0.01 stress +0.99 % [−2.12, +3.99]), put +1.55 % [−1.60, +4.68] (QQQ +0.19 %). The fit figures were the
STRONGER ones at 15:00 (call +3.36 % [+1.39, +5.33]) — the usual shrinkage on a picked cell, as C's P3 showed. The iron
at 15:00 reads +5.03 % [+1.72, +8.24] OOS (QQQ +5.03, SPY +5.03), dying at $0.02 ([−0.61, +5.70]).

**The iron ±5 beside it** (T1, T3). Same payoff, $8 a fly cheaper: 15:30 OOS +$17.46, +5.96 % [+3.40, +8.41], win 0.652,
PF 1.67, wo5 +4.80 %, SPY +5.54 / QQQ +6.38, 2025 +5.2 / 2026 +6.9; at $0.01 +4.79 % [+2.28, +7.19]; at $0.02 +3.64 %
[+1.17, +6.00]; k changes it by under $1.3 a fly. **It needs spread approval** (a defined-risk credit combination, short
the ATM straddle), so it is not the cash-account form; it remains C's "candidate, not a rule" and nothing here promotes it.

**moc_mag** (T6). Q12 − Q345 on the primary cell: fit +0.77 points [−2.19, +3.84]; OOS **−5.05 [−9.81, −0.43]** (Q12 +0.99 %
on 381 flies, Q345 +6.04 % on 498); the put −5.07 [−9.77, −0.39], the iron −5.58 [−10.36, −0.76]; by name SPY −4.03 [−8.54,
+0.21], QQQ −6.09 [−11.79, −0.55]. At 15:00 the sign is the other way and through zero (+2.15 [−3.88, +7.86]). A cut whose
sign flips between periods and between times adds nothing; the quiet-close group is the one to AVOID at 15:30 OOS, which
is not a rule either (fit says the opposite). Confirmed: it still adds nothing. No cut.

## 6. Verdict and the rule

**Verdict: a conditionally justified rule — "needs the forward tracker", not "edge".** The pre-registered four-part rule
is met on the primary cell (15:30, SPY + QQQ pooled, long call ±5, k = 0): OOS +3.85 % [+1.38, +6.24], +2.73 % [+0.29,
+5.07] at $0.01 a leg, wo5 +2.69 %, SPY +4.22 % and QQQ +3.48 %, every OOS year positive, PF 1.34, the stress interval's
lower bound seed-stable at +0.14 to +0.33. What keeps it from "edge": (i) the 2025–2026 data that passes it is the data
C's OOS read and the owner's quote came from — the cell was chosen on it, so the pass is not independent evidence; (ii)
it dies at $0.02 a leg and its k\* is −0.96, i.e. the whole mean is one $9.89-a-fly fill away from zero, and k is an
assumption until measured; (iii) fit was weaker (+2.25 % [+0.47, +3.90], SPY +1.56 % with its interval through zero in C's
own table), so the OOS is the larger figure — the opposite of shrinkage, which on a cell picked after the OOS read is a
warning, not a comfort; (iv) friction is 57 % of the gross, and the fee line alone ($2.60 of a $9.89 mean) is 26 % of
what is kept.

**The exact rule, if the owner runs the confirmation** (code: this folder's `build.py` + `run.py`, unchanged):

- Names SPY and QQQ, one lot each, on every full session (no half day), entered at **15:30:00 ET** on the quote at that
  minute. **K0** = the strike nearest the 15:29 bar's close that has a call and a put quoted (a tie → the lower strike).
  **Buy 1 K0−5 call, sell 2 K0 calls, buy 1 K0+5 call as ONE complex order** with a net-debit limit at the NBBO package
  debit (ask + ask − 2 × bid) — the planning number is k = 0; the tracker records the realized package fill against the
  NBBO package and the mid package, which is the measured k. Skip the fly if the NBBO debit < $0.05 or the short K0 bid is
  0. No exit: held to the close, settled at intrinsic. Fees $0.65 a leg to open; none at expiry in the model.
- Pass criteria, fixed now, on sessions after 2026-10-09 (none in this data): the SPY + QQQ pooled mean > 0 with its
  session-bootstrap 95 % interval clear of zero **at the realized fills AND at those fills $0.01 a leg worse**, wo5 > 0,
  both names > 0, and the realized package fill no worse than the NBBO package on the median entry (k ≥ 0 measured).
  Fail on any one.
- **The sample the rule needs.** The session total of the two 1-lot flies has mean $19.71 and SD $168.2 a session OOS
  (the two names' same-session P&L correlate 0.785, so sessions, not flies, are the sample). A one-sided 5 % test with
  80 % power on that mean needs **451 sessions (about 1.8 trading years)** at the k = 0 figure, and **1,276 sessions
  (about 5 years)** at the $0.01-stress figure ($11.71 a session) — that is the honest size for a mean this small against
  this SD; with fewer sessions the tracker can only reject (a negative run) or measure the fill. The fill itself needs far
  less: the realized improvement over the NBBO package is one number a fly, and after 60 fills its mean is known to a
  standard error of its SD / 7.7 — the first quarter of the tracker answers whether k = 0 is the right planning number, and
  if the median fill lands at or inside the NBBO package the rule's figures stand as computed; if it lands outside, the
  $/leg-to-zero line (+$0.0247) says how much room there is.
- Until then: nothing in the Compass engine, no capital, no moc_mag cut.

## 7. Gaps and limits

- **The OOS is not independent of the selection** (§6, the deciding caveat). This folder cannot repair that; the tracker can.
- **k > 0 is unobserved.** A complex order fills as a package against the complex order book; the displayed leg sizes
  (T5) bound a leg-by-leg fill, not the package. The figures at k = 0.25 and 0.5 are sensitivities, never results.
- **One-minute NBBO at 15:30:00.** The fill is the quote at that instant with no queue; the $0.01 / $0.02 stresses stand in
  for queue position and for a package that fills outside the NBBO. SPY's slip was lower OOS than fit ($7.19 vs $9.62),
  QQQ's higher ($13.36 vs $9.59); the spread regime moves.
- **Settlement on an ETF is physical delivery, which a cash account must handle.** The model settles every leg at intrinsic
  on the 15:59 bar with no assignment or exercise fee (C's convention, stated). On SPY and QQQ a close between K0−5 and K0
  leaves the K0−5 call exercised (100 shares bought, about $60,000 of SPY a cash account must have the cash for), and a
  close between K0 and K0+5 adds the two short calls assigned (200 shares sold) — a net short 100 shares a cash account
  cannot hold; the real alternatives are closing the fly before 16:00 (a fifth bid-ask on
  four legs, untested here) or letting the broker exercise/assign and flattening at the next open (gap risk, untested).
  The same-close pin risk C noted applies. This is the largest gap between the modeled and the executable cash-account trade.
- **Fees** are the stated $0.65 a leg; exchange and regulatory fees on a complex order, and any assignment fee the
  broker charges, are not in it. At a $9.89 mean, every $1 of unmodeled fee a fly is 10 % of the result.
- **No upper debit cap, no event filter**: every full session is traded, Fed days and CPI days included (the worst
  session, 2025-03-04, was a large down day on both names). No cut was tested, by design.
- moc_mag at 15:00 is C's construction (14:30 → 15:00 inputs), not the audit's checkpoint; at 15:30 it is the audit's own.
