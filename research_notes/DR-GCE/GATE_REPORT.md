# DR-GCE — gate report (section 7)

Run as pre-registered: GATE_PREREG.md 01d5c8e, Amendment 1 041baba (VolRatio's σ_ATM on the trading-minute clock),
both committed before any signal was computed. 504 full exploration sessions 2023-12-01 → 2026-10-09 (2023-11 is held
out, so the span starts in December); the 28 held-out months were never opened (the guard raises; selftest 5 of 5).
SPXW 0DTE, real NBBO only. VIX is on disk and was not read.

## Result

| | signals | touch rate [20-session block 95%] | baseline (500 draws) [2.5–97.5% of draw means] | gate |
|---|---|---|---|---|
| **Pooled** | **98** | **32.7% [23.3, 40.2]** | **16.0% [9.2, 22.4]** | **PASS** (23.3 > 22.4) |
| Mode 1 (Gamma Vacuum Squeeze) | 98 | 32.7% [23.3, 40.2] | 16.0% [9.2, 22.4] | pass |
| Mode 2 (Climax Pin Snapback) | 0 | — | — | no signal |

- **Against 83%: 32.7%, upper bound 40.2% — far below.**
- Per year (Mode 1 = pooled): 2023 1/1 · 2024 14/35 (40%) · 2025 11/36 (31%) · 2026 6/26 (23%).
- Outcomes: 32 touches, 20 stops first, 46 neither in 4 minutes. Stop −24% on 84 of 98 (G_max ≥ 0.85). 37 calls, 61
  puts. Not traded: 32 signals while the mode's previous trade was open, 4 with no eligible contract.
- Mode 2's funnel (trigger bars 10:00–14:45): 127 stretched ≥ 2.80 → 70 with S > Z_γ → 18 within 0.15% of a wall →
  **0 with VolRatio ≤ 1.18**. Mode 2 never fires on this span as pinned.
- The pass is narrow (0.9 points between the bounds) and rests on Mode 1 alone.

## Integrity

- Plain-loop re-derivation (verify_plain.py, math only, no shared code): 30 sessions with signals + 6 without, every bar
  rescanned, **40 signals re-derived with contract, stop and touch outcome: 0 differences**.
- Lookahead (lookahead.py): 3 sessions, 2,310 bar decisions rebuilt with every input after the decision minute blanked:
  **0 differ**; control (SPX read one minute ahead): 10 of 19 signal decisions differ.

## Scripts (sha256)

```
5c24fa29002ec2c589723930814bdd9e4fa201cbcf2cc21aff3a6a22775ffcb4  dr_gce.py
4772bd855952b10736d4404278a2c27c7cd625f0769c2b4b87719b9fd53fbd9b  guard.py
f5c03b7c0c7a5c9c0d7cd7bd619d637af2f502840ef5c8c1b141cbfe0c0eb14e  verify_plain.py
62c2d50a06b017387ba63557ed693af5b10cb03ee81115315d394d141d123c29  lookahead.py
438e71170350952b75d8afca339766c62342dba91871c8a2d165c0ccf75d2ecd  funnel_m2.py
```

Outputs: out/signals.csv, out/summary.json, out/*.log. Nothing beyond the gate was run.
