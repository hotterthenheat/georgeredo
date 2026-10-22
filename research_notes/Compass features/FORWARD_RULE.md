# Compass features: the forward pass rule (committed before the first forward session's result exists)

History: written and committed alone on Thu 2026-10-22, during the first forward session (2026-10-22), after 12:30 New
York and before its close — later than the 09:30 aimed for, but before any forward datum exists: the session's chains,
bars and official close are fetched only after the close by the daily forward job (17:45 New York). Nothing in this
file was chosen after seeing a forward number. The exact commit time is the commit's own timestamp.

The owner (2026-10-22): "Add these to the daily forward job, frozen as committed: V1, X3, VN1, and Phase B's BV1b, BX3e
and BC3. Same base trades and costs as PREREG_FEATURES.md, forward sessions only (from 2026-10-22). Before the first
forward session, commit a forward pass rule: N sessions, Δ > 0 with the 20-session block interval clear of zero. Set N
from the holdout's session-level variance so that a true effect of the holdout's size clears zero with 80% power; report
N for each model. No verdict before N."

## 1. What is frozen

- **The model definitions**, exactly as committed: V1, X3, VN1 in `PREREG_FEATURES.md` (commit `a2e14e4`, sha256
  `840f7671b1f997c9610a3cda9bec0407fb341755eb8b88a3defa5d314cfc62cd`); BV1b, BX3e, BC3 in `PREREG_FEATURES_B.md` (commit
  `b6737c7`, sha256 `18846288f4f4f720e11a0c9e35d15a17b6f34df106d77a4bc7953d62cc7784f8`). The base trades (entries,
  strike buckets, forward and implied move, fixed exits, fees, the return) are `PREREG_FEATURES.md` section 2, unchanged.
- **The code**, by file sha256, as committed in `2a49049` (Phase A) and unchanged through `e5dd8c6` (Phase B):

  | file | sha256 |
  |---|---|
  | `run/fcommon.py` | `05af0be735bd2f6c82551913ca1de2df3cdc9d01cc49fa8b2e31601973b9e882` |
  | `run/build_0dte.py` | `e152b1bec413f03a78ff9b6116ae45b5a92585d558f28f60b196f135d25fbc47` |
  | `run/daily.py` | `d2cb253936b9928f3efe9b3e87d71fdb67ad0d360feb99a84d207b11f2ec6505` |
  | `run/screen.py` | `e6cf7ef0e6e3e144c38aaf608ebb4afad8e9f50808a04550ef164b9dde0376b4` |
  | `run/stats.py` | `4ad310430a2d27e88d2bbf4b491e433124bf1447d00fcbdaf179129558e97ea6` |
  | `run/phase_b.py` | `313efc2e7630f6820d54e108435adec1402b176cb34b903307a1baae33470fef` |
  | `run/b_exits.py` | `74556c8cb056179410d226bed6374c3dd0fa67e061675ca9b07915094badb665` |
  | `run/tiers.py` | `c6cad0c62353f42de3c029aaa1a45af26b5f125131b74dfa5c44aed1794818cd` |
  | `../Compass phase 3/backtest_audit/audit_lib.py` | `3fcbb80b54a31ae3baa0ed94cdd269be5040f2761351bac129866b88b7935936` |

  The forward job imports these files (or calls them on a forward date range) and checks their sha256 before every run;
  a mismatch stops the run. No feature definition, threshold, base trade, cost or exit is changed for the forward test.
- **The holdout inputs N was computed from** (read only, nothing new compared): the Phase A corrected holdout table
  `features_work/hold/trades_with_inputs.parquet` (sha256 `28a5cb40f08077b2e2c18189c8f509ed653e1bfda6cd7b81ba444a0073ce442c`),
  the table behind `out/holdout.json` (`2a49049`) and `out/phase_b_holdout.json` (`e5dd8c6`).

## 2. The forward set (which base trades the forward test trades)

**0DTE base trades on SPY, QQQ and SPXW**, every full forward session from **2026-10-22** (half days excluded, as in
the prereg): the 13 entry minutes, five strike buckets, calls and puts, the fixed exits (SPY/QQQ sold at the 15:58 bid;
SPXW held to settlement on the official SPX close), the prereg's fees. These are the names the daily forward job
already fetches every session (SPY/QQQ/SPXW same-day 1-minute chains, SPY/QQQ 1-minute bars, SPX prints, the official
closes), which carry every input the six models read: the entry quote's spread (V1, BV1b), the 14:00 row (X3, BX3e),
the SPY/SPXW pairs (VN1), the opening range from bars / SPX prints (D6 inside BC3).

**Out of the forward set, and therefore out of the N computation:** IWM and the 11 single names (no daily chain fetch
in the job; the singles' 0DTE trades exist only on their expiry days), and the 1–7, 8–30 and 31–60 DTE buckets (they
need a daily option-EOD fetch across names and hold 5–10 sessions or to expiry, so a session's trades would complete
weeks later). Adding any of them later is a new pre-registration, not a change to this one.

## 3. The statistic (the same as the report's)

Per model, as `stats.py` `delta` computes it (prereg section 6): for each session s in calendar order, S_s = Σ r and
N_s = the number of trades entered in s, for each arm (with the model's decision; without = the base trades the
decision acts on). **Δ = Σ S_with ÷ Σ N_with − Σ S_without ÷ Σ N_without** — the per-trade mean return after fees,
pooled over sessions (not a mean of per-session means). The interval: the 20-session moving-block bootstrap of
`audit_lib.block_draws(n, 20)` (2,000 draws, `audit_lib.SEED` = 20261022, the generator seeded 20261022 + 7919 × 20),
the same draw for both arms, the 95% percentile interval (`audit_lib.pct_ci`). Each forward session appends one row
per model (S_with, N_with, S_without, N_without and the session's own per-trade difference, for reading) to
`forward/forward_sessions.csv`.

## 4. N per model

Computed by `forward/power_n.py` (committed with this file; output `forward/power_n.json`) on the holdout restricted to
the forward set. **Composition A** (the one N is set from): the holdout sessions in held-out months on which all three
names are holdout — from 2023-02-01, 302 sessions — which is the forward composition (SPY + QQQ + SPXW every session).
Composition B (every holdout session of the restricted span, mostly QQQ alone, fewer trades a session) is reported as a
sensitivity only; for VN1 it is A padded with sessions that cannot trade.

- δ = the statistic above on the series (the holdout effect on the forward set).
- σ_LR (per session) = the larger of (i) the block-20 bootstrap SE of δ × √n and (ii) √(20 · var of 20-session block
  means of the linearised session contribution z_s = (S_with − m_with N_with) ÷ N̄_with − (S_without − m_without
  N_without) ÷ N̄_without).
- N0 = ⌈((1.96 + 0.8416) · σ_LR ÷ δ)²⌉, at least 60.
- Simulated power at N: 2,000 outer draws (moving blocks of 20 from the holdout series, cut to N, seed 20261023 + N),
  each judged by the rule's own interval; the share with Δ > 0 and the lower end > 0. If under 0.80, N is raised (steps
  of 5%, at least 5) until it is ≥ 0.80. N is never lowered below N0.

Points of the debit (percentage points of return per trade):

| model | holdout δ, pooled verdict (all names, all buckets) | δ on the forward set (A) | σ_LR (A) | N0 | power at N0 | **N** | power at N | B (sensitivity): δ, N |
|---|---|---|---|---|---|---|---|---|
| V1 | +2.61 | +0.06 | 3.28 | 23,960 | 0.37 | **23,960 (unreachable; see below)** | 0.37 | +0.13, 8,262 |
| X3 | +7.78 | +9.76 | 63.6 | 334 | 0.77 | **369** | 0.81 | +7.74, 893 |
| VN1 | +1.18 | +1.40 | 12.1 | 587 | 0.96 | **587** | 0.96 | +1.40, 1,575 |
| BV1b | +4.30 | +4.20 | 30.6 | 415 | 0.77 | **481** | 0.83 | +3.08, 1,181 |
| BX3e | +7.67 | +10.82 | 62.8 | 265 | 0.85 | **265** | 0.85 | +7.48, 819 |
| BC3 | +6.77 | +9.03 | 53.7 | 279 | 0.74 | **341** | 0.82 | +7.29, 704 |

At about 252 sessions a year: X3 ≈ 1.5 years, VN1 ≈ 2.3, BV1b ≈ 1.9, BX3e ≈ 1.1, BC3 ≈ 1.4. **V1 cannot be confirmed
on this forward set in any useful time**: on 0DTE SPY/QQQ/SPXW the 10% spread veto almost never acts (90,860 of 92,136
trades kept on the holdout), so its effect there is +0.06 points; N by the formula is 23,960 sessions and the
simulated power there is still 0.37 (the search was stopped at 20,000+). V1 is kept in the job and logged; its verdict
date is N = 23,960 as written, which in practice means no verdict.

**Why the floor is 60, not 40.** Two 20-session blocks (40) is the least a block bootstrap can resample at all, but
`stats.py` — the statistic this rule uses — prints no interval under 60 sessions, so the floor is the larger, 60. No
model's N is at the floor.

## 5. The rule

1. A forward session **counts** only when it is complete and verified: the job's fetch, verify and merge passed, every
   base trade of the forward set that the session forms has its exit (SPY/QQQ the 15:58 bid; SPXW the official SPX
   close), and the six models' rows are written. A session that fails is not counted and is not replaced by anything;
   the next complete session is the next count. Sessions are counted in calendar order from 2026-10-22.
2. **No verdict before N.** Interim figures may be printed in `forward/FORWARD_REPORT.md`, each labelled "no verdict";
   no early stop, no extension, no change of N, model, forward set or statistic once a forward row exists.
3. **At exactly N counted sessions**, per model, on those N sessions only: **Δ > 0 and the lower end of the 20-session
   block-bootstrap 95% interval (section 3, seed 20261022) > 0 ⇒ CONFIRMED; otherwise NOT CONFIRMED.** The verdict is
   written once and never revised; sessions after N are logged but do not change it.
4. The six models are read separately; no multiple-test correction is applied (each was already pre-registered and passed
   its holdout), and this is said beside every verdict. A CONFIRMED model still loses money per trade if its forward
   per-trade mean with the decision is negative; the report prints both arms' means beside Δ.
