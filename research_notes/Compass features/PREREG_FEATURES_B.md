# Compass features, Phase B: the improvement round's candidates, registered before their holdout read

Written 2026-10-22 and committed ALONE, after Phase A (commit `2a49049`, `FEATURES_REPORT.md`) and before any candidate below is
computed on a held-out ticker or month. Phase A's verdicts are final and are not rewritten here.

## 1. Why there is a Phase B

Phase A (pre-registration `PREREG_FEATURES.md`, `a2e14e4`) passed three features on the holdout — V1 (spread veto), VN1 (venue)
and X3 (sell a 0DTE long option at 14:00) — and none in the direction, expiry/strike or strike-distance families (the GEX family
was dropped by its gate). Every pass makes a losing base set lose less; none makes it profitable. The owner asked, if the
results are bad, not to stop until the model improves, under the standing rules: conclusions are not changed to produce a
positive result, not everything is optimized until it looks profitable, and a negative finding is a valid result.

## 2. What was allowed and what was done (exploration set only)

- Data: the EXPLORATION set of Phase A only (no held-out ticker AVGO, MU, QQQ; no held-out month), the same base trades, the same
  fees, the same statistic (prereg section 6: Δ = mean per trade with − without, after costs; 20-session moving-block bootstrap,
  audit_lib, 2,000 draws, seed 20261022; no interval under 60 sessions).
- Allowed: thresholds; combinations of features that each showed a positive exploration Δ in Phase A (V1 +2.46, VN1 +1.69,
  X3 +5.75, D2 +0.52, D5 +2.93, D6 +1.13); different features from the same pre-registered sources (including a source read the
  other way); conditioning by tier, expiry bucket or settlement type.
- Walk-forward inside exploration: PICK = exploration sessions to 2024-06-30; CHECK = exploration sessions from 2024-07-01.
- Selection rule, written in `run/phase_b.py` before any variant was computed: a variant is eligible when its PICK Δ > 0 with the
  PICK interval's lower end > 0 AND its CHECK Δ > 0 with the CHECK interval's lower end > 0; among the eligible at most one per
  family (veto, exit, direction, combination), the one with the highest PICK lower end; at most 3 in all (by the CHECK lower end
  if four families had one). Nothing was selected on the whole-exploration figures.
- **Variants tried: 33** — every one is in the ledger below (and `out/phase_b_trials.csv`), whatever it showed. Eligible:
  11 (BV1a, BV1b, BV1c, BV1d, BX3a, BX3b, BX3e, BC1, BC2, BC3, BC4). **No direction variant was eligible.**

## 3. The candidates (at most 3) — exact definitions

| id | family | definition | PICK Δ [95%] | CHECK Δ [95%] | whole exploration Δ [95%] |
|---|---|---|---|---|---|
| BX3e | exit | X3 (14:00) on the physically settled names only | +7.57 [+3.15, +12.22] | +7.39 [+1.96, +12.32] | +7.49 [+3.88, +10.94] |
| BC3 | combination | V1 veto + X3 exit + D6 direction, against all base trades | +6.97 [+4.93, +9.97] | +4.73 [+1.78, +7.62] | +5.95 [+4.05, +8.05] |
| BV1b | veto | V1 spread veto at 3% | +7.68 [+5.27, +10.61] | +3.05 [+1.29, +5.89] | +5.39 [+3.60, +7.52] |

Exact definitions, on Phase A's base trades (prereg sections 2.1–2.7, unchanged), every return after fees:

- **BV1b — spread veto at 3%.** Defined set: every base trade (every name, every bucket). With: the trades whose entry quote has
  (ask − bid) ÷ mid ≤ 0.03; without: all of them. (Phase A's V1 was the same at 10%.)
- **BX3e — the 14:00 exit on the physically settled names.** Defined set: the 0DTE base trades of SPY, QQQ, IWM and the eleven
  single names entered before 14:00 (09:45 … 13:45). With: sold at the bid of the 14:00 chain row (the last standing bid within
  the 10 minutes before, after the entry; $0 with no fee if none); without: the fixed exit (the 15:58 bid). SPXW is not in it.
  (Phase A's X3 was the same on every name, SPXW included.)
- **BC3 — a model: V1 veto + X3 exit + D6 direction, against all base trades.** Start from every base trade (every name, every
  bucket). Drop a trade whose entry spread (ask − bid) ÷ mid > 10% (V1). Then drop a 0DTE trade entered from 10:15 whose side is
  against the opening range (D6: price at entry — the close of the bar stamped m − 1, the SPX print at m for SPXW — above the
  09:30–09:59 high keeps calls only, below the low keeps puts only; inside, or before 10:15, or a multi-day trade: both sides
  kept). Then a remaining 0DTE trade entered before 14:00 takes the 14:00 exit of X3 (SPXW included, with its exit fee); every
  other trade keeps its fixed exit. With: the model's trades at the model's returns; without: ALL base trades at their fixed
  returns. Δ = mean(with) − mean(without).

## 4. The holdout test and the pass rule

- Each candidate is computed ONCE on Phase A's holdout set (the held-out tickers AVGO, MU, QQQ over all months, and the
  exploration tickers over the 43 held-out months; the same corrected holdout table Phase A's verdicts used), unchanged.
- **Pass (the owner's rule): the holdout Δ against the base trades > 0 with its 20-session block 95% interval clear of zero
  (lower end > 0).** Reported with the per-tier and per-settlement rows (descriptive) and the holdout's two parts.
- No tuning after the read; pass or fail is reported as it comes out. If no candidate passes, that is the result.

## 5. What is NOT virgin — disclosure

Phase A already read the holdout for V1, VN1 and X3 (all three passed there; Δ +2.61, +1.18, +7.78 points). Every candidate is
built from those reads' components: BV1b is V1 at another threshold, BX3e is X3 on a subset of the same trades, BC3 contains V1
and X3 (and D6, which Phase A screened but did not send to the holdout). The holdout trades of BV1b and BX3e are subsets or
re-thresholds of trades whose V1 / X3 outcome on the holdout is already known, so a pass here is far weaker evidence than a
fresh holdout: it mostly tells whether the restriction or threshold holds up, not whether the effect exists. The holdout months
and tickers are the same; no new holdout exists. 33 variants were tried for 3 candidates; under the null, with 33 one-sided
tries at 2.5% on PICK and the CHECK filter, chance eligibility is not negligible — the walk-forward is the only guard.

## 6. The trials ledger (all 33 variants, exploration only; Δ and intervals in percentage points of the debit)

| id | family | definition | whole exploration Δ [95%] | PICK Δ [95%] | CHECK Δ [95%] | trades with / without (whole) |
|---|---|---|---|---|---|---|
| BV1a | veto | V1 spread veto at 5% | 4.3131 [2.9673, 5.9068] | 6.1545 [4.2338, 8.2178] | 2.2928 [0.982, 4.2242] | 401175 / 651232 |
| BV1b | veto | V1 spread veto at 3% | 5.3944 [3.6044, 7.5242] | 7.6834 [5.2718, 10.6069] | 3.0477 [1.2916, 5.8914] | 265416 / 651232 |
| BV1c | veto | V1 spread veto at 20% | 1.1112 [0.6852, 1.6024] | 1.7454 [1.0049, 2.5533] | 0.3304 [0.1294, 0.5738] | 611041 / 651232 |
| BV1d | veto | V1 at 10%, 0DTE only | 2.9098 [1.446, 4.429] | 4.866 [2.2092, 7.0871] | 0.8101 [0.0424, 1.7267] | 297027 / 376177 |
| BV1e | veto | V1 at 10%, 1-60 DTE only | 1.1098 [0.5657, 1.608] | 0.5598 [-0.0481, 1.0669] | 1.8866 [0.997, 2.9868] | 241441 / 275055 |
| BV3a | veto | V3 volume veto at 1,000 | -2.0039 [-3.4817, -0.3302] | -0.8355 [-3.3701, 1.9374] | -2.369 [-4.1035, -0.5695] | 315437 / 520282 |
| BV3b | veto | V3 volume veto at 10 | -0.0867 [-0.294, 0.0931] | 0.0132 [-0.3436, 0.319] | -0.0926 [-0.3297, 0.0478] | 491267 / 520282 |
| BV2a | veto | V2 open-interest veto at 100 | -0.0389 [-0.6832, 0.5993] | 0.629 [-0.3022, 1.6418] | -0.1887 [-0.9865, 0.4506] | 161954 / 174213 |
| BV2b | veto | V2 open-interest veto at 5,000 | -4.5013 [-8.6505, -0.5966] | -7.9479 [-22.5931, -1.0973] | -4.0954 [-8.6849, -0.3457] | 47079 / 174213 |
| BV6a | veto | V6 IV-rank veto at 0.5 | -0.5911 [-1.9536, 0.8679] | 0.0205 [-1.4866, 1.7027] | -0.9663 [-2.7847, 1.2927] | 368458 / 449028 |
| BV6b | veto | V6 low-IV veto: IV rank < 0.2 | 2.4824 [0.5973, 4.6748] | 3.8459 [0.6873, 5.8376] | 2.0698 [-0.4112, 4.9711] | 258957 / 449028 |
| BX3a | exit | 0DTE time exit at 12:00 (entries before) | 8.189 [4.3879, 12.0448] | 4.964 [0.1897, 9.5658] | 11.8602 [6.1671, 17.7487] | 176254 / 176254 |
| BX3b | exit | 0DTE time exit at 13:00 (entries before) | 8.4825 [4.3184, 12.5662] | 6.0873 [1.3592, 11.2195] | 11.2191 [4.9601, 17.2079] | 236396 / 236396 |
| BX3c | exit | 0DTE time exit at 15:00 (entries before) | 2.4398 [-0.645, 5.4745] | 2.81 [-0.27, 6.8974] | 2.0122 [-2.7586, 6.9284] | 338495 / 338495 |
| BX3d | exit | X3 (14:00) on SPXW only | -0.1719 [-7.3179, 5.8824] | -6.2177 [-16.84, 3.5217] | 4.7561 [-3.1051, 12.9859] | 66067 / 66067 |
| BX3e | exit | X3 (14:00) on the physically settled names only | 7.4893 [3.878, 10.9432] | 7.5661 [3.1504, 12.2235] | 7.3917 [1.9594, 12.3183] | 225023 / 225023 |
| BX1a | exit | 0DTE target at 0.25 IM | 3.9577 [0.1088, 7.7803] | 1.2881 [-2.376, 5.9807] | 7.0239 [1.2854, 13.308] | 375438 / 375438 |
| BX1b | exit | 0DTE target at 0.5 IM | 1.2572 [-2.5532, 4.887] | -1.7669 [-5.2885, 2.7561] | 4.7307 [-1.029, 10.5875] | 375438 / 375438 |
| BD6a | direction | D6 read the other way (fade the opening-range break) | -1.1338 [-8.0855, 4.8354] | -7.7332 [-17.7733, -1.5724] | 5.757 [-3.8103, 14.3106] | 98905 / 197857 |
| BD6b | direction | D6 on 0DTE entries from 13:15 | -3.074 [-10.0048, 4.544] | 2.3435 [-3.9765, 12.8705] | -9.1393 [-18.8526, 2.0407] | 46491 / 92966 |
| BD6c | direction | D6 on SPXW only | -1.6707 [-10.4148, 8.0733] | 6.8691 [-3.8239, 23.6647] | -8.3867 [-19.5079, 2.2304] | 29183 / 58382 |
| BD7a | direction | D7 read the other way | 1.4703 [-3.0989, 5.3816] | 0.9501 [-5.9959, 6.6368] | 1.9989 [-2.8367, 7.8225] | 165346 / 330543 |
| BD7b | direction | D7 on 1-60 DTE only | -0.3806 [-4.6993, 3.9448] | 0.6533 [-4.2713, 6.6825] | -1.357 [-8.0372, 4.4426] | 68954 / 138065 |
| BD3a | direction | D3 (NOPE) read the other way | 4.3468 [0.2652, 9.4354] |  [, ] | 4.3468 [0.2652, 9.4354] | 38727 / 77399 |
| BD4a | direction | D4 (tide) read the other way | 3.3433 [-4.1802, 10.114] | 19.8339 [-3.0843, 41.8466] | -0.0292 [-6.7167, 7.6025] | 88639 / 177245 |
| BD1a | direction | D1 (net premium) read the other way | 0.401 [-2.7221, 4.2894] | -1.1048 [-3.9545, 8.2003] | 0.7102 [-3.0325, 5.164] | 88681 / 177245 |
| BD2a | direction | D2 (sweeps) with |value| ≥ $1M | -1.2103 [-6.484, 4.952] | -0.9662 [-17.3172, 11.9515] | -1.2555 [-8.0796, 4.2413] | 36454 / 72903 |
| BD2b | direction | D2 (sweeps) on 0DTE only | -0.1263 [-4.8675, 4.3351] | -1.1849 [-14.6323, 9.6714] | -0.0113 [-5.2998, 4.566] | 50703 / 101453 |
| BD26 | direction | D2 and D6 agree (0DTE from 10:15) | -6.808 [-16.7626, 5.0116] | -42.1085 [-89.0136, -18.979] | -3.9266 [-14.7926, 7.3594] | 15662 / 31336 |
| BC1 | combination | V1 veto + X3 exit, against all base trades | 5.0336 [3.292, 6.9932] | 5.6546 [3.4911, 8.402] | 4.209 [1.5736, 6.8758] | 538468 / 651232 |
| BC2 | combination | V1 veto + VN1 venue + X3 exit, against all base trades | 5.1931 [3.4111, 7.1033] | 5.8775 [3.8103, 8.5888] | 4.3763 [1.7319, 6.987] | 466824 / 651232 |
| BC3 | combination | V1 veto + X3 exit + D6 direction, against all base trades | 5.9467 [4.0543, 8.0531] | 6.9716 [4.9253, 9.9701] | 4.7313 [1.7792, 7.6206] | 458261 / 651232 |
| BC4 | combination | V1 veto + X3 exit, 0DTE entries before 14:00 only | 8.0268 [4.2721, 11.7417] | 8.5439 [4.0583, 13.7811] | 7.5388 [1.4918, 13.1067] | 239970 / 291090 |
