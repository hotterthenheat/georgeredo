# Compass features, Phase B: the improvement round, read once on the holdout

**Pre-registration: `PREREG_FEATURES_B.md`, commit `b6737c7`** (committed alone, after Phase A `2a49049` and before this read). Code: `run/b_exits.py` (the extra 0DTE exits, exploration only), `run/phase_b.py` (every variant, the walk-forward and the selection rule, written before the variants were computed), `run/phase_b_test.py` (this read). Phase A's verdicts stand as reported in `FEATURES_REPORT.md`.

## Result

- **BV1b** (V1 spread veto at 3%): holdout Δ +4.30 [+2.66, +5.85] points of the debit, mean per trade -6.73 with vs -11.03 for the base trades, 251,808 / 580,234 trades, 3,586 sessions, n_eff 3,071 → **PASS**.
- **BX3e** (X3 (14:00) on the physically settled names only): holdout Δ +7.67 [+4.23, +10.69] points of the debit, mean per trade -11.03 with vs -18.71 for the base trades, 203,289 / 203,289 trades, 2,340 sessions, n_eff 3,309 → **PASS**.
- **BC3** (V1 veto + X3 exit + D6 direction, against all base trades): holdout Δ +6.77 [+4.82, +8.19] points of the debit, mean per trade -4.26 with vs -11.03 for the base trades, 410,384 / 580,234 trades, 3,586 sessions, n_eff 4,128 → **PASS**.
- Variants tried on the exploration set: **33**; eligible by the walk-forward rule: 11; candidates: 3; passed the holdout: 3.
- **No direction variant survived the walk-forward** (none had PICK and CHECK intervals both above zero), so Phase B adds nothing on which side to buy. What passes is again cost and timing: a stricter spread veto, the 14:00 exit, and a model that stacks V1 + X3 + D6.
- **Every candidate still loses money per trade on the holdout** (the model BC3: −4.26% of the debit a trade against −11.03% for the base trades). The improvement is a smaller loss, not an edge.
- **This holdout is not virgin for these candidates.** Phase A read it for V1 and X3 (both passed); BV1b is V1 at 3% instead of 10%, BX3e is X3 without SPXW, BC3 contains V1 and X3 (D6 is the only component not read there before, and D6 alone failed the Phase A screen). A pass here mainly says that the re-threshold and the restriction hold up on trades whose V1/X3 outcome was already seen; it is much weaker evidence than Phase A's passes. 33 variants were tried for these 3.

## Per candidate (descriptive rows: the holdout's two parts, settlement type, tier)

| candidate | slice | Δ | 95% |
|---|---|---|---|
| BV1b | **pooled (verdict)** | +4.30 | [+2.66, +5.85] |
| BV1b | held-out tickers, all months | +4.40 | [+2.41, +6.32] |
| BV1b | exploration tickers, held-out months | +4.21 | [+1.91, +6.26] |
| BV1b | settlement physical | +4.50 | [+2.82, +6.08] |
| BV1b | settlement cash | +2.45 | [-1.03, +5.27] |
| BV1b | tier 1 | +2.11 | [+0.56, +3.26] |
| BV1b | tier 2 | +2.05 | [-2.54, +6.14] |
| BV1b | tier 3 | +8.81 | [+5.04, +12.47] |
| BV1b | tier U | +17.08 | [+7.87, +27.23] |
| BX3e | **pooled (verdict)** | +7.67 | [+4.23, +10.69] |
| BX3e | held-out tickers, all months | +7.91 | [+4.72, +10.97] |
| BX3e | exploration tickers, held-out months | +7.33 | [+0.78, +12.61] |
| BX3e | settlement physical | +7.67 | [+4.23, +10.69] |
| BX3e | tier 1 | +7.65 | [+3.16, +11.30] |
| BX3e | tier 2 | +1.32 | [-10.19, +10.29] |
| BX3e | tier 3 | +12.77 | [+7.29, +18.03] |
| BX3e | tier U | +7.47 | [+2.33, +13.42] |
| BC3 | **pooled (verdict)** | +6.77 | [+4.82, +8.19] |
| BC3 | held-out tickers, all months | +7.58 | [+6.00, +9.08] |
| BC3 | exploration tickers, held-out months | +5.92 | [+2.60, +8.17] |
| BC3 | settlement physical | +6.87 | [+5.11, +8.16] |
| BC3 | settlement cash | +5.73 | [-1.33, +10.13] |
| BC3 | tier 1 | +5.41 | [+2.31, +7.49] |
| BC3 | tier 2 | +1.55 | [-1.23, +2.99] |
| BC3 | tier 3 | +7.85 | [+5.88, +9.82] |
| BC3 | tier U | +15.93 | [+10.49, +21.52] |

## The walk-forward numbers the candidates were chosen on (exploration only)

| candidate | PICK (to 2024-06) Δ | CHECK (from 2024-07) Δ | whole exploration Δ |
|---|---|---|---|
| BX3e | +7.57 [+3.15, +12.22] | +7.39 [+1.96, +12.32] | +7.49 [+3.88, +10.94] |
| BC3 | +6.97 [+4.93, +9.97] | +4.73 [+1.78, +7.62] | +5.95 [+4.05, +8.05] |
| BV1b | +7.68 [+5.27, +10.61] | +3.05 [+1.29, +5.89] | +5.39 [+3.60, +7.52] |

The full ledger of the 33 variants is in `PREREG_FEATURES_B.md` section 6 and `out/phase_b_trials.csv`.

## What was not done

- No tuning after this read. No candidate was changed, added or dropped after it. No new holdout was drawn.
- The selected exit and veto rules reduce losses on long premium bought at the ask; whether any long-premium base set can be made profitable by these features was not shown, and on these data the answer is no.
