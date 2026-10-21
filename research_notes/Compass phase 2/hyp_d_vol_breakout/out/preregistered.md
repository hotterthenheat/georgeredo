# Pre-registered picks for Hypothesis D — written 2026-10-21 after reading cells_fit+cut_t2_{gbm,lr}.csv, BEFORE any 2025–2026 row was read

Signal: the t2 gradient-boosted model's top decile (D10 by the cuts set on 2024-07→12); the t2 logistic, and the t1 / t3
models' D10, are robustness reads only.
Primary cells (chosen from the hypothesis, not from the fit numbers): ATM straddle and 15-delta strangle bought at the
FIRST D10 minute of the session, exits hold-30 and 50% trail. Their fit+cut reads (pooled, % of debit): straddle h30
−2.7 % [−$48, −$14], trail −4.9 % (CI through zero, −$58 without the best 5 sessions); strangle h30 −9.9 % [−$28, −$6],
trail −9.7 % (CI through zero). Expectation: negative out of sample.
Best-on-fit cell (what a tuner would have picked; registered so its OOS fate is on record): 20-delta strangle, every D10
minute, 50% trail: +4.6 % of debit, +$21.7 [−$29, +$81], −$31 without the best 5 sessions, best 5 sessions = 238 % of
the total. Expectation: fails out of sample.
Opening drive pick: at 09:35, the side of the 09:30–09:35 move, nearest OTM, 50% trail, D10-only: +12.2 % of debit on
fit+cut, +$53 [−$26, +$145], −$23 without the best 5 sessions. Unconditional: +0.1 %. Expectation: noise.
Decision rule for "edge" (fixed now): OOS mean % of debit > 0 with the session-bootstrap 95 % CI of the mean $ clear of
zero, AND the mean without the best 5 sessions > 0, AND the paired time-of-day-matched lift's CI clear of zero.
