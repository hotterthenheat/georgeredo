# DR-GCE — Gate 2 report (direction against volatility)

Run as pre-registered: GATE2_PREREG.md (294d4f2), committed alone before any opposite-side figure was computed. The 98
Mode 1 signal rows of Gate 1 (b20eb9c), the opposite side at the same entry row under Gate 1's contract rules; 504
exploration sessions 2023-12-01 → 2026-10-09; the held-out months never opened (guard selftest 5 of 5); nothing fetched.

## Verdict: FAIL

**Mode 1's lift is volatility after the impulse, not direction. There is no full backtest** (BACKTEST_PREREG.md is not
written; nothing further is run).

| | n | touch +18% in 4 min | stop first |
|---|---|---|---|
| Signal side (all 98) | 98 | 32.7% (32) | 20.4% (20) |
| Signal side (paired) | 96 | 31.3% (30) | 20.8% (20) |
| Opposite side, own G_max stop (primary) | 96 | 20.8% (20) | 26.0% (25) |
| Opposite side, signal's stop fraction (sensitivity) | 96 | 20.8% (20) | 20.8% (20) |
| Random baseline (Gate 1's 500 draws, replayed) | 98 a draw | 16.0% [9.2, 22.4] | 14.1% [8.2, 20.9] |

**Paired difference (signal − opposite touch), 20-session block 95%:**

| | pairs | D | interval |
|---|---|---|---|
| **Pooled (primary)** | **96** | **+10.4 pt** | **[−4.4, +22.4]** — lower bound ≤ 0: **FAIL** |
| Pooled, sensitivity (signal's stop fraction) | 96 | +10.4 pt | [−4.4, +22.4] |
| 2023 (December only, 20 sessions) | 1 | +100 pt | none (< 60 sessions) |
| 2024 | 34 | +26.5 pt | [+12.1, +46.7] |
| 2025 | 35 | 0.0 pt | [−23.5, +21.4] |
| 2026 | 26 | 0.0 pt | [−35.0, +16.7] |

- No opposite contract: 2 of 98 (both "no contract" within the Δ and spread rules); those pairs are excluded.
- Discordant pairs: signal touch only 30, opposite touch only 20, both 0.
- The opposite side's own stop was −24% on 61 of 96 (G_max ≥ 0.85); it differed from the signal side's on 39 pairs and
  changed 5 outcomes (stop ↔ neither), no touch. The sensitivity line is the same D to the digit.
- The opposite side alone touches at 20.8%, above the random baseline's 16.0% mean (inside its [9.2, 22.4] spread): the post-impulse minutes are
  volatile in both directions. The direction's edge is +10 points pooled, carried by 2024; 2025 and 2026 show none.
- The baseline replay reproduced Gate 1's baseline touch mean exactly (0.1599591836734694), so its stop-first rate is
  Gate 1's own draws.

## Integrity

- Plain-loop re-derivation (gate2_verify.py, verify_plain.py's plain code imported, not edited; dr_gce for the calendar
  only): **all 98 pairs over 77 sessions — signal trade, opposite contract (strike, ask, stop, touch, outcome, last row)
  and the sensitivity outcome — 0 differences**. gate2.py also re-ran every signal trade through dr_gce: 98 of 98 match
  signals.csv.
- Committed scripts unchanged (their sha256 equal GATE_REPORT.md's).

## Scripts (sha256)

```
5c24fa29002ec2c589723930814bdd9e4fa201cbcf2cc21aff3a6a22775ffcb4  dr_gce.py
4772bd855952b10736d4404278a2c27c7cd625f0769c2b4b87719b9fd53fbd9b  guard.py
f5c03b7c0c7a5c9c0d7cd7bd619d637af2f502840ef5c8c1b141cbfe0c0eb14e  verify_plain.py
cfcf5273f9804d0ed08daf3941c0ddbdf2c0654bfca37a5f9321dc5ed31ba58b  gate2.py
bf9efb32a32fdb14d091a4033ff6dff4754e5e830d67d3a36f5fe26166ddec88  gate2_verify.py
```

Outputs: out/gate2_pairs.csv (per signal), out/gate2_summary.json, out/gate2_run.log, out/gate2_verify.log.
