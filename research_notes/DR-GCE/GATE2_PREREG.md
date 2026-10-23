# DR-GCE — Gate 2 (direction against volatility), pre-registered

Written and committed ALONE, before any opposite-side contract, touch or difference is computed. Gate 1 (GATE_PREREG.md
01d5c8e, Amendment 1 041baba, GATE_REPORT.md b20eb9c) passed on Mode 1 alone: 98 signals touched +18% within 4 minutes
32.7% [23.3, 40.2] against a random baseline of 16.0% [9.2, 22.4]. Gate 2 asks whether that lift is the signal's
DIRECTION or only the volatility after the impulse: on the same minutes, the opposite side. Every open choice is pinned
**[v0]**. Exploration span only (504 sessions 2023-12-01 → 2026-10-09); the guard (guard.py) wraps every read; no
holdout file is opened; nothing is fetched. The committed scripts are used by import and never edited.

## 1. The pairs

- **The signals [v0]**: the 98 rows of `out/signals.csv` (b20eb9c) — the Mode 1 signals Gate 1 traded. The 32
  overlap-skipped and 4 no-contract signals stay out, as in Gate 1. Mode 2 has 0 signals; nothing is changed to make it
  fire.
- **The opposite trade**: at each signal row, the same session, signal bar (`sbar`), book bar (`bbar` = `sbar`) and
  entry row (`sbar` + 1), the side turned over (a put for a call signal, a call for a put signal). Everything else as
  Gate 1 (GATE_PREREG §7), by dr_gce.py's own functions: SPXW 0DTE in the opposite direction, both sides standing,
  |Δ| ∈ [0.40, 0.54], (Ask − Bid) ÷ Ask ≤ 0.035, the highest C_K with δS = 3 σ̂1m · S at the signal bar (ties: the
  strike nearest F, then the lower strike); entry at that row's ask.
- **No overlap rule on the opposite [v0]**: each opposite trade is paired to its signal and stands whatever the other
  opposite trades do.

## 2. The stop and the touch

- **Primary stop [v0]**: by the OPPOSITE contract's own G_max, computed the same way (dr_gce `struct_move` with the
  opposite side, Mode 1): ΔS_struct = the distance from S (the book bar's print) to the nearest of {M_γ, the opposite
  side's opposing wall — for a put the strike below S with the most negative GEX_K, for a call the strike above S with
  the largest positive GEX_K} lying strictly beyond S in the opposite trade's direction, else the band's edge (2.5%);
  G_max = (|Δ| · ΔS + ½ Γ · ΔS²) ÷ EntryAsk; the stop −24% (bid ≤ 0.76 × EntryAsk) when G_max ≥ 0.85, else −18%.
- **Sensitivity [v0, labelled, not judged]**: the opposite trade with the SIGNAL side's stop fraction (the signal row's
  `stop`), everything else the same.
- **Touch**: as Gate 1 — the bid reaches ≥ 1.18 × EntryAsk on one of the 4 chain rows after the entry row; a stop on the
  same row as the touch or earlier is a FAIL (stop-first); a row with no bid counts as neither (dr_gce `outcome`).

## 3. No opposite contract [v0]

- A signal minute at which no opposite contract passes the rules (no forward, no standing quote, or none within the Δ and
  spread rules) is COUNTED (by reason) and its pair is EXCLUDED from the paired difference. The signal-side touch rate is
  shown on all 98 and on the paired set.

## 4. The report

- Per signal: date, signal bar, side, signal-side touch, opposite-side touch, signal-side stop-first, opposite-side
  stop-first, the opposite contract (strike, ask, G_max, stop), and the sensitivity outcome (`out/gate2_pairs.csv`).
- Touch and stop-first rates: signal side, opposite side (primary and sensitivity).
- **The random baseline's stop-first rate**: Gate 1 did not record it (its table kept the touch only). It is recomputed
  by rebuilding Gate 1's baseline table with the outcome kept (dr_gce `base_session`'s cells, `trade`'s `how`) and
  replaying Gate 1's draw sequence exactly (seed 20261023, 500 draws, the same redraw rule). The replay must reproduce
  Gate 1's baseline touch mean (0.15995918…) to the last digit; otherwise the mismatch is reported and no baseline
  stop-first rate is claimed. Shown: the mean over the 500 draws of (stops ÷ draws) and the 2.5–97.5% spread of the draw
  means.
- **The paired difference** D = Σ (signal touch − opposite touch) ÷ the number of pairs. Interval: the 20-session
  moving-block bootstrap of `research_notes/Compass phase 3/backtest_audit/audit_lib.py` (`block_draws`, `weights_from`,
  `pct_ci`; 2,000 draws, its default seed), over every exploration session in calendar order (zero-pair sessions
  included), each draw's D = Σ_w d ÷ max(Σ_w pairs, 1), 2.5–97.5%. **Pooled** (504 sessions) and **per year** (the
  year's own sessions in order, the same method; an interval only when the year holds ≥ 60 sessions, three blocks — 2023
  is December alone and is shown without one). Also shown: the discordant counts (signal touch only, opposite touch only).
- The sensitivity line's D and interval, labelled.

## 5. Pass / fail

- **PASS** if the pooled paired difference's lower bound (primary stop) is strictly > 0. Nothing else is judged.
- **FAIL**: stop. GATE2_REPORT.md says that Mode 1's lift is volatility after the impulse, not direction, and that there
  is no full backtest. Nothing further is run.
- PASS opens the full Mode 1 backtest, which is pre-registered and committed alone (BACKTEST_PREREG.md) before it runs.

## 6. Integrity

- A plain-loop re-derivation of ≥ 20 pairs: verify_plain.py's plain code (no numpy in its logic, no function shared with
  dr_gce.py — imported, not edited) rebuilds each chosen opposite trade (contract, ask, stop, touch, outcome, last row
  watched) and the signal trade; a plain loop rebuilds the sensitivity outcome. **0 differences required** (strike and
  ask within 1e-9, the rest exact).
- sha256 of every script recorded in the report.
