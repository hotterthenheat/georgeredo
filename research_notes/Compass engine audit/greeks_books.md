# Compass Modules 5 and 6: the Black-Scholes / implied-vol engine and the dealer exposure books

Scripts, logs and every number below: `research_notes/Compass engine audit/greeks_books/` (`common.py` is the pricer; `q1*` the greek benchmark, `q2` the 0DTE skip rule, `q3*` the dealer-sign and regime tests, `q4*` flips/walls/books, `q5` the confidence multiplier, `q6` the unit conventions; each writes `q*_results.txt`). Run as `nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I <script>`. No credential appears in any file; the one UW token on disk answered **401 Unauthorized** to three GET calls on 2026-10-21 (`q1c_live_uw_check.py`), so no live UW data was used. **The ThetaData API was not called** (the owner's terminal is in use 13:00–21:00 UTC); the ThetaData benchmark the spec asks for is a blocker, and the files on disk (`lake/flat/option_eod`, 2026-10-06→10-12) carry closing NBBO and open interest but **no greeks**, so they served the book tests, not the greek benchmark.

Data used: (a) 68 UW `option-contracts` snapshots of SPY, 34 end-of-day dates 2023-11-20→2026-08-24, two expiries per date (24–32 and 52–60 calendar days; **no ≤7, 8–14 or >90 DTE snapshot exists on disk**), 26,307 contract rows, 17,332 with a UW IV and delta; (b) ThetaData SPY same-day chains at 1-minute NBBO, 980 sessions 2022-11-11→2026-10-09; (c) ThetaData 1-minute underlying bars SPY/QQQ/IWM; (d) UW daily book-level `greek-exposure` for 6,014 tickers 2025-10-15→2026-10-13 (one year) with UW daily OHLC; (e) ThetaData bulk EOD option files with OI, 5 sessions 2026-10-06→10-12, SPY/QQQ/IWM full chains.

Splits: the one-year UW book history is read as two halves (H1 to 2026-04-14/15, H2 after), the first as discovery and the second as check — six months each, which is thin, and said so wherever it matters.

## Key question 0: the audited rules and the verdicts at a glance

### Takeaway
Module 5's pricer is sound and the r,q adjustment is the market-consistent choice, but the spec's stated reason for it ("ITM calls > 3% fall apart under r = 0") is backwards and the benchmark the owner names (vendor greeks) will *disagree* with it, because Unusual Whales' own contract greeks stand on r = 0, q = 0. Module 6's arithmetic is standard; its dealer-sign readings (DEX/VEX/CEX → next-day drift) found nothing that holds in both halves; the regime claim is mostly implied volatility in disguise; Method A and Method B flips are different quantities that disagree by about 2% of spot on single-expiry books; the 1/5/12/25 bp tiers sit inside one strike step; the hard sign gate should give way to `net/gross` (no free weight), which is what the sign disagreement between two engines on the same open interest actually measures.

### Cited Findings
| Rule (spec) | Test | Verdict |
|---|---|---|
| IV by bisection on [0.01, 3.00], 60 iterations, on the NBBO mid | `q1`: 25,276 quoted contracts; under r=0 the inverted vol sits 0.13–0.95 vol points from UW's own IV by bucket — [q1_results.txt](greeks_books/q1_results.txt) | **Keep.** 60 bisections give 2⁻⁶⁰ of the bracket; the bracket [0.01, 3.00] never bound on these chains. |
| 0DTE: r = 0, q = 0 | Immaterial at τ ≤ 1 day: the rτ term is ≤ 0.011% of K | **Keep.** |
| DTE ≥ 1: r (SOFR) and q in d1 | `q1b`: same-strike call and put vols from the mids agree to −0.17 vol points under r=4.15%, q=0 (sign random, 48% positive) and are +4.04 points apart under r=0 in 100% of 67 snapshots — [q1b_results.txt](greeks_books/q1b_results.txt) | **Keep r, q — but write it as the forward: (r − q) ≈ 4% on SPY 2023–2026.** Expect the engine to disagree with UW's greeks by 1–5 vol points and 0.01–0.05 delta, because UW's are r = 0 (next row). |
| "Benchmark against vendor greeks; ITM calls > 3% converge within 0.5%" | `q1` Stage A: UW's delta/gamma/theta/vega/rho are reproduced from UW's own IV at **r = 0, q = 0, τ = calendar days/365, theta per calendar day**: median \|Δdelta\| 0.0015 (p90 0.0096), gamma relative error +0.1%, theta/365 0.0012, rho/100 0.0010; at r=4.15% the delta error is 0.0106 (p90 0.043) and the best-fit r per snapshot is 0.0000 (IQR 0–0) | **Change the benchmark.** UW's greeks cannot validate an r,q engine; they validate an r=0 engine. Use put-call parity on the chain (q1b) or ThetaData greeks when the terminal is free. |
| "r,q eliminates the intrinsic-floor distortion in ITM calls > 3%" | `q1`: ITM calls K < 0.97 S, n=2,879: under r=0 **0.0%** have mid ≤ intrinsic; under r=4.15%, q=0 **5.7%** do (the floor S − K e^{−rτ} is *higher*); under r=4.15%, q=1.3% 0.4%. The mirror — ITM puts K > 1.03 S, n=848 — is where r=0 fails: **32.0%** have mid ≤ K − S and no vol, 0% under r=4.15% | **Change the wording.** The distortion is in deep ITM *puts* under r=0 (carry makes a put worth less than K−S), not calls. |
| Skip a contract if mid − intrinsic ≤ 0.01 (0DTE) | `q2`: 980 SPY sessions, every minute, contracts within ±1% of spot: 4.7% skipped in the first half hour → 32.5% in the last; at the strikes a trade uses (±0.5%) 0.5% → 17.8%; gamma thrown away ≤ 0.6% of the band's until 15:30, 2.8% in the last half hour — [q2_results.txt](greeks_books/q2_results.txt) | **Keep 0.01.** 0.005 changes nothing (most skipped rows have mid ≤ intrinsic already); 0.02 skips 47% of near-money rows in the last half hour and 9% of its gamma. |
| GEX_call = +γ·OI·100, GEX_put = −γ·OI·100, GEX_1pct = GEX·S²/100 | `q4b`: my sum on ThetaData full chains vs UW's book-level figure, same day: net/gross within ±0.05 of UW's on 12 of 15 name-days; sign agrees 12/15, the 3 disagreements all at \|net/gross\| < 0.07 — [q4b_results.txt](greeks_books/q4b_results.txt) | **Keep the arithmetic; drop the belief that the sign is a fact.** |
| Regime = sign(GEX_book): mean-reversion vs continuation, never direction | `q3`/`q3b`: direction — hit rates 0.43–0.59, NW t of the sign split −1.7 to +2.2 with opposite signs in the two halves; volatility — GEX_z predicts lower next-session realized vol after a trailing-vol control (t −3.7/−4.2 SPY, −3.9/−1.8 QQQ, −3.5/−2.5 IWM) **but with UW's 30-day IV added the GEX term is +0.55/−3.17 (SPY), −0.39/+0.08 (QQQ), −1.47/−2.32 (IWM)** — [q3b_results.txt](greeks_books/q3b_results.txt) | **Keep "never direction" (confirmed). Demote the regime to a descriptive label**: most of it is "low implied vol → low realized vol". Not a causal rule, no weight. |
| DEX, VEX, CEX raw vs negated → next-hour / next-day drift | `q3`: cross-section 836,160 ticker-days, quintile Q5−Q1 next o-c return: GEX +1.1 bp (t 0.5), DEX +2.8 (0.7), VEX −2.9 (−0.8), CEX +7.0 (t 2.2; H1 +6.5 t 1.4, H2 +7.4 t 1.7); ETFs: every correlation < 0.23 and sign-flipping across halves — [q3_results.txt](greeks_books/q3_results.txt) | **Negative finding.** Neither sign convention predicts drift. CEX cross-sectional is the one same-sign-both-halves result and is 7 bp a day gross — not actionable; flag for a second year. |
| Flip Method A (linear zero crossing, nearest, discard > 3%) | `q4`: found in 67/67 snapshots, 66 within 3%; \|F_A − S\| median 33 bp (p25 11, p75 67) — [q4_results.txt](greeks_books/q4_results.txt) | **Keep A as "the strike-level zero crossing"** (it is the house's rule). |
| Flip Method B (re-price net GEX on a 0.05% spot grid) | `q4`: a zero on ±4% in 56/67; where both exist \|B − A\| median $11.37 (188 bp), p90 $22.88; 95% differ by more than one strike; same side of spot only 57% | **Change: never call both "the flip".** B is the spot at which the *book's* gamma is zero (a dynamic quantity); A is where the per-strike profile changes sign. Report both under their own names or drop B. |
| Distance tiers ≤1 / ≤5 / ≤12 / ≤25 bp | `q4`: SPY's $1 strike step is 18 bp (13–97 across the sample), 1 bp = $0.059; end-of-day \|F_A − S\| falls ≤1 bp 1%, ≤5 bp 15%, ≤12 bp 28%, ≤25 bp 42% | **Change.** "Breached" (≤1 bp) and "critical" (≤5 bp) are 1/20 and 1/4 of one strike step: noise at a 1-minute print. Use multiples of the strike step or of the day's 1σ move. |
| Walls = max positive / max negative GEX_strike; king, pin | `q4`: the 25-DTE and 60-DTE expiries on the same date give the same call wall 8/33 dates, the same put wall 4/33; `q4b`: 0DTE book's call wall never equals the Macro book's (0/15), the Near book's does 9/15 | **Keep the definitions; label every level by its book.** |
| Three books: 0DTE / Near ≤14 / Macro | `q4b` above | **Keep; the slicing matters** (the levels differ). |
| Replace the hard UW sign gate with a continuous multiplier | `q5`: conf = tanh(GEX/ref₈₅,₆₀) and conf₂ = net/gross; on SPY 40% of days have \|net/gross\| < 0.10 and 64% of the 56 day-to-day sign flips happen there — [q5_results.txt](greeks_books/q5_results.txt) | **Change to conf₂ = (ΣGEX_call + ΣGEX_put)/(Σ\|GEX_call\| + Σ\|GEX_put\|)**, exact formula below. Presented as a gate replacement, not an edge: nothing in this audit shows the sign carries EV. |
| CEX_day = CEX/365.25 (not 252); VEX_1vol = VEX/100 | `q6`: pure unit choices (365.25 vs 252 is a factor 1.450); the house's "charm is a year's, ÷365" differs from ÷365.25 by 0.07% | **Keep ÷365 (the house's) for a calendar day.** UW's charm/vanna book figures could *not* be reproduced from the chains (ratios 0.01–6), so their unit stands on UW's spec text alone. |

### Inferences
- The single most consequential finding for the house: on every one of 68 historical snapshots, UW's contract greeks are r = 0, q = 0. The house's measured "UW's vols invert under r = 4.15%, q = 0" (8,096 prints, a different endpoint — flow prints, not `option-contracts`) and this finding can both be true only if the two endpoints run different engines; the `trailField` model prices UW's chain-read vols at r = 4.15%, so if the chain endpoint is r = 0 like these snapshots, every put is priced 1–2 vol points too rich and every call too cheap relative to the vol's own clock. A live `option-contracts` pull would settle it (the token is dead; see Gaps).
- "Not from the regime sign" is the one spec rule this audit confirms outright (hit rates at coin-flip, signs reversing between halves).

### Gaps
- ThetaData v3 greeks (the spec's named benchmark) at 7/14/30/180 DTE: blocked — the API was not to be called and the bulk files on disk have no greeks. Needed: one `v3` greeks pull per DTE bucket on a day the terminal is free.
- ≤7, 8–14 and >90 DTE buckets of the greek benchmark: no snapshot on disk.
- A live UW `option-contracts` read to confirm the live endpoint is r = 0 like the history: the token on disk returns 401.

## Key question 1: the Greek benchmark (Module 5)

### Takeaway
Against the 68 UW snapshots, the engine reproduces UW's greeks only at r = 0, q = 0 — the vendor's convention — and against the market itself (put-call parity on the mids) the r,q engine is the right one: same-strike call and put vols agree within 0.2 vol points at r − q ≈ 4% and are 4 points apart at r = 0. The ITM-call claim in the spec is reversed; the r = 0 failure is in deep ITM puts.

### Cited Findings
- Stage A (greeks from UW's own IV, τ = calendar days/365): r=0, q=0 gives median \|Δdelta\| 0.0015, p90 0.0096, mean +0.0015; gamma median relative error +0.001; vega/100 median \|err\| 0.0024; theta/365 0.0012 (theta/252 0.0382); rho/100 0.0010. r=4.15%, q=0: delta 0.0106 / p90 0.0433 / mean +0.0170; gamma −3.5%; theta/365 0.0180. r=4.15%, q=1.3%: delta 0.0068 / p90 0.0316. τ = trading days/252 fits worse than days/365 (delta 0.0110 vs 0.0106). Best-fit r by snapshot (grid 0–8%, delta RMSE, q=0): median 0.0000, IQR 0.0000–0.0000; 2025-02-24 and 2025-11-24 fit 1.5–1.75% — [q1_results.txt](greeks_books/q1_results.txt), [q1_best_r_by_snapshot.csv](greeks_books/q1_best_r_by_snapshot.csv)
- UW's same-strike pairs (5,626): delta_call − delta_put median 0.9737 (e^{−qτ} would be 0.9989 at q=1.3%, 1.0000 at q=0); put gamma / call gamma 1.145 (K/S−1 in (−5%,−2%]), **1.245 (±2%)**, 1.058 (+2..+5%); IV_put − IV_call −0.041, −0.031, −0.033 — [q1_results.txt](greeks_books/q1_results.txt)
- Stage B (bisection on the NBBO mid, [0.01, 3.00] × 60): median \|IV − IV_UW\| under r=0 is 0.13–0.95 vol points in every right × moneyness × DTE bucket (calls K<S−3%: 0.95 at 15–30d, 0.59 at 31–90d; puts K>S+3%: 1.82, 0.95); under r=4.15%, q=0 it is 0.5–5.8 points (ITM calls 4.95/5.40, ITM puts 5.77/5.52) — [q1_results.txt](greeks_books/q1_results.txt)
- Parity (q1b, 67 snapshots, strikes within ±8%): signed median IV_call − IV_put per snapshot: r=0,q=0 **+4.04 points, positive in 100% of snapshots**; r=4.15%, q=0 **−0.17 (48% positive), median \|gap\| 0.84**; r=4.15%, q=1.3% +1.11 (85% positive); forward-implied (r − q) from the ATM pairs: median 0.0407, IQR 0.0315–0.0501, by year 2023 3.9%, 2024 4.7%, 2025 3.9%, 2026 3.6% — with the caveat that the spot is the 16:00 close and the quotes stand at ~17:30 ET — [q1b_results.txt](greeks_books/q1b_results.txt)
- ITM calls > 3% from spot (K < 0.97 S, n=2,879): r=0 → mid ≤ floor 0.000, IV err median 0.67 pts (p90 4.16), delta err median 0.0046 (p90 0.0124), within 0.5% relative delta of UW 46.9%; r=4.15%, q=0 → 5.7% unsolvable, delta err 0.0492 (p90 0.0756), within 0.5% 2.0%; r=4.15%, q=1.3% → 0.4% unsolvable, delta err 0.0276 — [q1_results.txt](greeks_books/q1_results.txt)
- ITM puts > 3% (K > 1.03 S, n=848): r=0 → **32.0% have mid ≤ K − S** (no solvable vol); r=4.15% → 0.0%, delta err 0.121 vs UW (UW's puts are r=0) — [q1_results.txt](greeks_books/q1_results.txt)
- Weight of the contested region: calls with K < 0.97 S carry 6.3% of OI and 6.7% of \|γ·OI\| across the snapshots (ITM-anything carries 72.9% of OI — the deep OTM-put side of the same strikes — but 40.6% of \|γ·OI\|) — [q1_results.txt](greeks_books/q1_results.txt)
- The spec's skip rule applied to these monthlies removes 6.2% of quoted contracts (1,566 of 25,276) — [q1_results.txt](greeks_books/q1_results.txt)
- Numerical checks of the pricer: delta, theta, charm (call and put), vanna, rho agree with finite differences to 1e-7; put-call parity to 1e-12 — [common.py](greeks_books/common.py) self-test in the transcript.

### Inferences
- UW's `option-contracts` engine: European Black-Scholes, r = 0, q = 0, τ = whole calendar days/365, theta per calendar day, rho per 1%. The 1.15–1.25 put/call gamma asymmetry the house saw is the arithmetic consequence: inverting at r = 0 when the forward carries ~4% pushes the call vol up ~2 points and the put vol down ~2 points at the same strike (rho × r ≈ $0.65 on a $450 ATM monthly against a vega of ~$47 per 1.00 vol → 1.4 points each way), and gamma ∝ 1/σ near the money.
- The spec's r,q engine is correct for pricing and for sizing a hedge, and *wrong as a way to match UW*. Compass should state which it wants: match-the-vendor (r=0) or match-the-market (r − q ≈ 4%). Since only r − q enters d1 and the chain itself gives the forward, the cleanest rule is: **r − q := ln(F/S)/τ from the ATM put-call pair of the expiry being priced, r := the SOFR print for the discount factor** — no SOFR series is needed for d1.
- Exact replacement for the "ITM calls" sentence: "Under r = 0 a deep in-the-money put (K > 1.03 S) is often quoted below K − S (32% of them at the close on SPY monthlies), so no vol solves; the forward-consistent floor K e^{−rτ} − S e^{−qτ} restores a vol. In-the-money calls are not affected under r = 0 and are *more* often unsolvable under r > 0 with q = 0 (5.7%)."

### Gaps
- ThetaData v3 greeks at 7/14/30/180 DTE: not obtainable now (API off-limits during 13:00–21:00 UTC; no greeks in the bulk files).
- Whether UW's *live* chain endpoint is r = 0 (as the 2023–2026 history is) or r = 4.15% (as the house measured on prints): the token answers 401. One GET of `stock/SPY/option-contracts?expiry=<~30 d>` plus `stock-state` and the `q1c` script would answer it in a minute.
- A SOFR series to replace the 4.15% constant: not on disk; the forward-implied r − q above is the data's own answer and is enough for d1.

## Key question 2: the 0DTE skip rule (mid − intrinsic ≤ 0.01)

### Takeaway
On every SPY same-day chain for four years the rule is benign until the last half hour: it removes contracts that have no solvable vol anyway (mid ≤ intrinsic), costs under 1% of near-money gamma before 15:30 and 2.8% in the last 30 minutes; 0.005 is indistinguishable from 0.01, 0.02 is materially worse.

### Cited Findings
- 980 sessions (2022: 34, 2023: 250, 2024: 252, 2025: 250, 2026: 194), contracts within ±1% of spot at every minute, 8.6 million contract-minutes: share skipped at thr 0.01 by 30-minute bucket from the open: 4.7%, 5.4%, 6.0%, 6.4%, 7.2%, 7.9%, 8.9%, 9.9%, 11.4%, 13.5%, 16.1%, 20.4%, **32.5%**; share with mid ≤ intrinsic (unsolvable under any threshold): 4.3% → 18.4% — [q2_results.txt](greeks_books/q2_results.txt)
- Threshold sensitivity, whole session by band: CALL ITM>0.5% skipped 25.8% / 27.0% / 29.5% at 0.005 / 0.01 / 0.02 (24.6% already mid ≤ intrinsic); CALL OTM>0.5% 13.0% / 13.0% / 33.8%; PUT OTM>0.5% 2.2% / 2.2% / 11.7% — [q2_results.txt](greeks_books/q2_results.txt)
- Strikes a trade would use (ATM ±0.5%): skipped 0.5% in the first half hour, 2.2% at 11:30–12:00, 6.1% at 14:30, 9.0% at 15:00–15:30, 17.8% at 15:30–16:00; gamma share lost 0.0% until 14:30, 0.3% at 15:30, 1.3% in the last half hour (6.0% at thr 0.02) — [q2_results.txt](greeks_books/q2_results.txt)
- Gamma is unweighted (open interest is not in the minute chains); τ is calendar time to 16:00, vol inverted at r = 0 — [q2_skip_rule.py](greeks_books/q2_skip_rule.py)

### Inferences
- Keep 0.01. The OTM calls skipped at 0.02 (33.8%) are the $0.01–0.02 lottery tickets whose gamma is nil; the near-money loss in the last half hour is the one place a 0DTE book is sensitive, and that is where the mid ≤ intrinsic share (which no threshold can fix) is already 18%.
- A better treatment than skipping in the last half hour: carry the contract's last solvable vol forward (sticky strike) rather than drop it — testable, not tested here.

### Gaps
- OI-weighted gamma loss (the number that matters for a 0DTE book) needs per-minute OI, which does not exist; the ThetaData daily OI files could weight the close-of-day cut only.

## Key question 3: dealer-sign tests (owner's task a) and the regime claim

### Takeaway
Neither the raw-OI sign nor its negation (customer-hedged dealer sign) of DEX, VEX or CEX predicts the next session's open-to-close, first-hour or last-hour drift in a way that holds in both halves of the year, cross-sectionally or on SPY/QQQ/IWM. The regime claim (positive GEX → quieter, mean-reverting session) looks strong until implied vol is controlled for, after which it survives only in SPY's second half and IWM.

### Cited Findings
- Cross-section: 836,160 ticker-days, 5,103 tickers, 249 sessions 2025-10-15→2026-10-12, filters close > $5, dollar volume > $5M, UW book non-empty, \|next return\| < 50%, no earnings within a day; GEX_book > 0 on 79% of ticker-days, CEX > 0 on 9% — [q3_results.txt](greeks_books/q3_results.txt)
- Sign split, daily equal-weight mean next o-c return (X>0 minus X<0), NW t lag 5: GEX −2.0 bp (t −0.91) H1 / +1.8 (t +0.74) H2; DEX −0.5 / −0.0; VEX −1.7 / −1.4; CEX +1.1 (t 0.25) / +3.1 (t 0.75) — [q3_results.txt](greeks_books/q3_results.txt)
- Quintiles of X scaled by the name's trailing-20-session median \|X\|, Q5−Q1: GEX +0.0 bp (t 0.01) / +2.0 (0.62); DEX +2.6 (0.41) / +3.0 (0.60); VEX −2.4 (−0.41) / −3.3 (−0.72); **CEX +6.5 (t 1.38) / +7.4 (t 1.74), full year +7.0 (t 2.20)** — [q3_results.txt](greeks_books/q3_results.txt)
- Realized range next session: raw GEX > 0 names 358 bp vs 314 bp (t +18) — a name-type confound (call-heavy books are calmer names); relative to the name's own trailing-20 mean range, Q5−Q1 of GEX_z is −0.013 (t −2.13) H1, +0.002 (t +0.41) H2, −0.005 (t −1.42) all — [q3_results.txt](greeks_books/q3_results.txt)
- ETF time series (next session from 1-minute bars; first hour 09:30→10:30, last hour 15:00→16:00; n 231–245): corr(GEX_z, first-hour return) SPY −0.19 H1 / +0.13 H2, QQQ −0.17 / +0.16; DEX QQQ −0.22 / +0.16; VEX QQQ +0.10 / −0.22 (last hour +0.05 / −0.27); hit rate sign(X) = sign(o-c) 0.43–0.59; IWM GEX sign split NW t −1.72 H1 and +2.16 H2 (opposite signs) — [q3_results.txt](greeks_books/q3_results.txt)
- Share of sessions with GEX_book > 0 on UW's book: SPY 0.30, QQQ 0.36, IWM 0.07; VEX > 0: 0.04, 0.19, 0.07; CEX > 0: 0.75, 0.64, 0.65 — [q3_results.txt](greeks_books/q3_results.txt)
- Regime, raw terciles of GEX_z (next-session realized vol, range, 5-minute lag-1 autocorrelation): SPY top vs bottom rv 59 vs 75 bp (H1), 47 vs 63 (H2); range 87 vs 124, 66 vs 101; ac5 −0.019 vs +0.060, −0.084 vs −0.027; QQQ rv 77 vs 102, 74 vs 102; ac5 −0.015 vs +0.031, −0.039 vs −0.039; IWM rv 94 vs 122, 82 vs 84 — [q3_results.txt](greeks_books/q3_results.txt)
- Regime with controls (log rv_next on log trailing-20 rv and GEX_z, NW t): b(GEX_z) SPY −0.084 (t −3.67) H1, −0.104 (t −4.18) H2; QQQ −0.096 (−3.87), −0.032 (−1.76); IWM −0.088 (−3.46), −0.084 (−2.45). **Adding UW's 30-day implied vol: b(IV) +1.4 to +2.1 (t 3.1–6.0) and b(GEX_z) SPY +0.011 (t +0.55) H1, −0.063 (t −3.17) H2; QQQ −0.010 (−0.39), +0.001 (+0.08); IWM −0.033 (−1.47), −0.043 (−2.32).** Autocorrelation on GEX_z after the trailing-vol control: SPY −0.022 (t −1.98) / −0.016 (−1.57), QQQ −0.031 (−2.45) / −0.005 (−0.69), IWM n.s. — [q3b_results.txt](greeks_books/q3b_results.txt)

### Inferences
- "Never pick call vs put from the regime sign": confirmed on 249 sessions × 3 ETFs and 836k ticker-days, i.e. a far larger sample than the spec's 22 sessions.
- Raw vs negated sign is moot: a sign that predicts nothing predicts nothing when flipped. The one survivor (CEX quintiles, +7 bp a day, t 2.2, same sign both halves) is below any options round-trip cost and rests on six months of confirmation; it goes on the watch list, not into the engine.
- The regime label is mostly "gamma is large when implied vol is low, and low implied vol forecasts low realized vol". After the IV control the dealer-hedging residual is SPY H2 and IWM only. Compass may show the regime as a description; it must not weight by it.

### Gaps
- One year only: a 6-month discovery / 6-month check is the most this data allows; the cross-sectional CEX line needs 2027's data before it is believed.
- No intraday book (the UW history is end-of-day), so the next-hour test is the next *session's* first and last hour on the prior close's book — the right test for a dealer-flow story at the open and the close, not a test of intraday updates.
- A true GEX history by strike per day for 6,000 names (to size the dealer flow in dollars against the name's liquidity, as Barbon–Buraschi do) does not exist on disk.

## Key question 4: flip, walls, king, pin, tiers and the three books

### Takeaway
Method A (the house's zero crossing) is always found; Method B is a different object and disagrees with A by a median $11 (188 bp) on single-expiry SPY books, on the same side of spot only 57% of the time; the 1 and 5 bp tiers are fractions of one strike step; the walls depend heavily on which expiry or book is summed (the 0DTE book's call wall never matched the Macro book's on 15 name-days), and on 34 dates the next session reached a wall no more often than a mirror strike.

### Cited Findings
- 67 usable snapshots (one had no usable greeks). Method A: a crossing in 67/67, 66 within 3%; Method B (0.05% grid, ±4%, sticky-strike vols, r=0): a zero in 56/67. Both exist in 56: \|B − A\| median $11.37 (188 bp), p90 $22.88 (351 bp); > 1 strike step in 95%, > 0.5% in 91%; same side of spot 57% — [q4_results.txt](greeks_books/q4_results.txt)
- \|F_A − S\| end of day: median 33 bp, p25 11, p75 67; tiers ≤1 bp 1%, ≤5 bp 15%, ≤12 bp 28%, ≤25 bp 42%, >25 bp 58%; the strike step near spot is $1.00 = 18 bp (13–97 bp across the sample); 1 bp of SPY = $0.059 — [q4_results.txt](greeks_books/q4_results.txt)
- Same date, 25-DTE vs 60-DTE expiry (33 dates): same call wall 8/33, same put wall 4/33, same king 6/33, same pin 3/33; median \|call wall difference\| $5, put wall $10. Net GEX (spec sign, one expiry) positive in 10% of snapshots; king = call wall 13%, king = put wall 39%; median distances: call wall +277 bp, put wall −367 bp, king −123 bp, pin −1,837 bp (the pin here is max-OI, dominated by far OTM puts) — [q4_results.txt](greeks_books/q4_results.txt)
- Next-session touch (67 snapshot-walls, 34 dates): call wall touched 3% vs mirror strike 10% vs ±1 strike 4%; put wall 4% vs 4% vs 3%; king 10% / 10% / 10%; "held" after a touch 4 of 5 — [q4_results.txt](greeks_books/q4_results.txt)
- Three books on real full chains (ThetaData EOD with OI, 5 sessions, SPY/QQQ/IWM, "0DTE" = the next session's expiry as seen at the close): 0DTE call wall = Macro call wall 0/15, put wall 2/15; Near (≤14 d) = Macro call wall 9/15, put wall 7/15; king 0DTE = Macro 6/15; flip on the same side of spot 9/15. SPY 2026-10-12: 0DTE net +$289M/1% (flip 778.44), Near +$1,570M (774.70), Macro +$19M (774.68); Macro call wall 785, put wall 755; 0DTE call wall 784, put wall 774 — [q4b_results.txt](greeks_books/q4b_results.txt)
- My Macro net vs UW's book-level for the same date, gamma × OI × 100: SPY 10-06 +1,083,922 vs +1,419,262; 10-07 +235,353 vs −594,231; 10-08 −970,599 vs −701,363; 10-09 +312,067 vs +235,100; 10-12 +3,119 vs +569,729; QQQ 10-09 −6,467 vs +130,802; IWM within 5–30% on all five days. As net/gross: 12 of 15 within ±0.05 of UW's; the 3 sign disagreements at \|net/gross\| = 0.030/−0.064, 0.050/−0.036, −0.001/+0.023 — [q4b_results.txt](greeks_books/q4b_results.txt)
- Strike-agreement share (the \|GEX_strike\| mass on the book's net side ÷ total): SPY Macro 0.50–0.62, Near 0.57–0.74, 0DTE 0.50–0.91; IWM Macro 0.87–0.91 — [q4b_results.txt](greeks_books/q4b_results.txt)

### Inferences
- A and B answer different questions. A: "between which two strikes does the per-strike profile change sign nearest spot" — a level. B: "at what spot would the whole book's gamma be zero if vols were sticky-strike" — a dynamic point that moves with the whole surface. Naming both "flip" and comparing them to 1/5/12 bp tiers is a category error; the house's rule (A to the cent) stands.
- The tiers should be in strike steps or in the day's 1σ budget: e.g. "inside one step", "1–3 steps", "beyond". A 1 bp tier on a $1-step SPY chain asks the print to sit within six cents of a level that itself moves by a strike when the next expiry is added.
- The book a level comes from must be printed next to it; a 0DTE wall at 784 and a Macro wall at 785 are different claims about different hedgers.
- The touch test is small-N and single-expiry (monthlies at 25–60 DTE, walls 3–4% away); it says nothing about intraday 0DTE walls near spot, which is where the terminal's own track record (data/feed/trackRecord.ts) is the right instrument.

### Gaps
- An intraday strike book (per-minute OI × gamma) for the 34 dates: not on disk; the terminal's recorder has it only from 2026-10.
- A proper wall test needs hundreds of sessions with full-chain OI by day; the lake has 5.

## Key question 5: the continuous agreement multiplier (owner's task b)

### Takeaway
Replace the hard sign gate with `conf = net/gross`, the signed share of the book's gross gamma that the net represents; it has no window and no free weight, it is 0.96 correlated with the trailing-p85 tanh version, and it is exactly the quantity on which two engines fed the same open interest disagree (every sign disagreement in q4b sat at \|net/gross\| < 0.07). On SPY, 40% of the year's sessions had \|net/gross\| < 0.10 and 64% of the 56 day-to-day sign flips happened there.

### Cited Findings
- conf₁ = tanh(GEX_book / ref), ref = p85 of \|GEX_book\| over the 60 sessions before the day: SPY \|conf₁\| < 0.2 on 23% of 230 sessions, 0.2–0.5 35%, 0.5–0.8 25%, ≥ 0.8 17%; median −0.26; day-to-day sign flips on 25% of sessions, 38% of them at \|conf₁\| < 0.2, 20% at \|conf₁\| ≥ 0.5. QQQ: 25% / 31% / 27% / 17%, flips 24% of sessions, 42% at \|conf₁\| < 0.2. IWM: 27% / 21% / 30% / 22%, flips 6% of sessions, 93% at \|conf₁\| < 0.2 — [q5_results.txt](greeks_books/q5_results.txt)
- conf₂ = (ΣGEX_call + ΣGEX_put)/(Σ\|GEX_call\| + Σ\|GEX_put\|): SPY \|conf₂\| < 0.05 on 20% of sessions, < 0.10 on 40%, < 0.20 on 70%, median −0.082; QQQ 24% / 39% / 72%, median −0.048; IWM 8% / 20% / 40%, median −0.265; corr(conf₁, conf₂) 0.95–0.96; of the sign flips 64% (SPY), 60% (QQQ), 71% (IWM) were at \|conf₂\| < 0.10 — [q5_results.txt](greeks_books/q5_results.txt)
- Last readings on disk (2026-10-13, the nearest to 2026-10-16): SPY GEX_book −249,588 against ref 2,358,990 → conf₁ −0.105, conf₂ −0.026; QQQ −1,228,219 / 1,250,393 → conf₁ −0.754; IWM −6,946,013 / 6,667,098 → conf₁ −0.779. SPY's preceding ten sessions ran −0.29, −0.51, +0.05, −0.24, +0.51, −0.23, −0.27, +0.09, +0.22, −0.11 — a sign flip every other day — [q5_results.txt](greeks_books/q5_results.txt), [q5_conf_series.csv](greeks_books/q5_conf_series.csv)
- The two engines on the same OI (q4b): sign agreement 12/15, every disagreement at \|net/gross\| < 0.07 — [q4b_results.txt](greeks_books/q4b_results.txt)

### Inferences
- Exact rule: **conf = (ΣGEX_call + ΣGEX_put) / (Σ\|GEX_call\| + Σ\|GEX_put\|)**, with ΣGEX over the book in question (0DTE, Near or Macro — one conf per book), in [−1, 1]. Any downstream use multiplies by conf (or by \|conf\| with the sign carried separately) instead of testing sign(GEX_UW) == sign(GEX_house). Where a vendor and the house both give a book, **conf_agree = min(\|conf_UW\|, \|conf_house\|) × [sign agrees]**, so a near-zero book from either source contributes near zero rather than a veto. A dead zone, if one is wanted, is \|conf\| < 0.10 (two engines on one OI disagree only there, q4b), not a tuned constant.
- conf₁ (tanh with the bead-scale reference) is the house's existing vocabulary and can stay as the display scale; conf₂ is the gate because it needs no history, so it works on a name's first day and on a 0DTE book that has no trailing 60 sessions.
- No EV claim: nothing in q3 shows the sign carries drift; the multiplier only stops the gate from deadlocking and from chattering on 25% of SPY's sessions.

### Gaps
- 2026-10-16 itself: not on disk (the lake ends 2026-10-13) and the API token is dead.
- Whether a soft gate changes Compass's realised P&L: untested here (no Compass trade log in scope); it is a gate-behaviour replacement.

## Key question 6: CEX/365.25 vs /252, VEX/100, and the house's charm convention

### Takeaway
These are unit choices with no predictive content: /365.25 and /252 differ by a factor 1.450, /365 and /365.25 by 0.07%; keep the house's ÷365 (a calendar day, matching UW's spec text "charm × OI × 365"). UW's book-level charm and vanna could not be reproduced from the chains (ratios 0.01–6), so their unit rests on UW's documentation, not on a measurement.

### Cited Findings
- 252/365.25 = 0.690, so CEX_day(252) = 1.450 × CEX_day(365.25); 365/365.25 = 0.99932 — [q6_results.txt](greeks_books/q6_results.txt)
- UW's `greek-exposure` fields are defined as "the sum of the [greek] values … multiplied by the open interest and the number of shares per contract" — no per-day or per-vol-point scaling stated — UW API documentation for `greek-exposure/strike` (the `Gex_Call_Gamma` … `Gex_Put_Vanna` schema descriptions), copy in the session scratchpad `uwdocs/greek-exposure-by-strike.full.md`
- Chain sums (ThetaData full chains, r=0, τ=days/365, per-year charm, per-1.00 vanna) vs UW's book fields, same day: delta sums match (SPY 10-06 calls 164.4M vs UW 185.3M, puts −89.7M vs −99.6M; QQQ 189.0M vs 213.0M); charm ratios UW/mine range +0.01 to +5.96 (SPY puts +0.33, +0.28, +0.30, +1.05, +1.76 across the five days); vanna puts +0.90 to +1.45, calls +0.11 to +1.11 — [q6_results.txt](greeks_books/q6_results.txt)

### Inferences
- Charm and vanna sums are dominated by the shortest-dated contracts (charm ∝ 1/τ), whose τ UW sets by its own clock (today's expiry on calendar time to its last trading instant; my close-of-day chains drop τ = 0 contracts and put tomorrow's at 1/365), so the book-level comparison cannot settle the unit. The delta sums (not τ-sensitive) do match within 10–15%, which is the share of contracts my filters drop (OI > 0, two-sided quote, within 25% of spot).
- Recommendation: CEX per calendar day = CEX_year/365; VEX per vol point = VEX/100; print the unit on every figure. The 365.25 in the spec is a cosmetic difference from the house's 365 and not worth two conventions.

### Gaps
- A per-contract UW charm/vanna (the `option-contracts` snapshots carry none) would settle UW's unit directly.

## Key question 7: the literature on dealer gamma, intraday returns and the sign-assumption problem

### Takeaway
Published work agrees that dealer gamma is a *modelled* quantity, that its sign is an assumption outside Cboe's own customer/market-maker data, and that where positioning is observed (SPX 0DTE) it is small and balanced; the two credible return effects — Baltussen et al.'s last-half-hour momentum and Barbon–Buraschi's momentum-under-negative-gamma — are regime-conditional and tied to illiquidity, not day-ahead direction.

### Cited Findings
- Cboe (every SPX trade seen as customer or market maker): 0DTE market-maker net gamma "ranging from $170mm to $670mm throughout the day", "0.04% to 0.17% of the daily S&P futures liquidity"; customer flow "remarkably balanced between buy vs. sell"; the 3:30 pm median +$173mm with a 25th–75th range −$1.1bn to +$2.4bn; on 2023-08-15 market makers were long ~$2bn gamma at 3 pm and ~−$500mm at 3:30 pm — [Cboe, Volatility Insights](https://www.cboe.com/insights/posts/volatility-insights-evaluating-the-market-impact-of-spx-0-dte-options); later "net market maker gamma hedging remains de minimis, … at best 0.2% of the SPX daily liquidity" — [Cboe, 0DTEs Decoded](https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact)
- Adams et al., "Do S&P500 Options Increase Market Volatility? Evidence from 0DTEs": higher market-maker net gamma predicts lower S&P 500 volatility over the next 10 minutes, fading after about an hour; stronger E-mini order-flow reversals and negative high-frequency momentum; market makers' net gamma positive through 0DTE expiration days; a 1 bp rise in hedging needs ≈ 4 bp lower realized vol — [Quantpedia summary](https://quantpedia.com/do-sp500-0dtes-options-increase-market-volatility/)
- Baltussen, Da, Lammers, Martens, "Hedging Demand and Market Intraday Momentum", JFE 142 (2021) 377–403: last-30-minute returns are predicted by the rest-of-day return across 60+ futures 1974–2020, attributed to gamma hedging by option market makers and leveraged-ETF rebalancing; reverts over the next days — [Erasmus repository](https://pure.eur.nl/en/publications/hedging-demand-and-market-intraday-momentum); [Alpha Architect summary](https://alphaarchitect.com/hot-topic-does-gamma-hedging-actually-affect-stock-prices/)
- Barbon & Buraschi, "Gamma Fragility" (St. Gallen WP, 2020): intraday momentum when dealers are net short gamma and reversal when net long, through delta-hedging feedback, conditional on illiquidity of the underlying and strongest in the least liquid names; flash crashes more likely on negative-gamma days — [author page](https://abarbon.com/papers/gamma-fragility); [St. Gallen repository](https://www.alexandria.unisg.ch/261487)
- Beckmeyer, Branger, Gayda, "Retail Traders Love 0DTE Options… But Should They?" (SSRN 4404704, 2023; Cboe SPX trade data 2021-01→2023-02): end users buy more 0DTE options than they sell, leaving market makers net short, whose hedging "has the potential to exacerbate intraday market swings"; retail losses average $358,000 a day since daily expirations — [Medium summary](https://medium.com/@y125789/retail-traders-love-0dte-options-paper-summary-6da4a7ff7d72); [CXO summary](https://cxoadvisory.com/individual-investing/retail-0dte-option-trader-performance) — contradicted on sign by Cboe's own positioning data above.
- Maurer, "Dealer Gamma Exposure and Overnight Gap Risk" (OptionMetrics, 2026): dealer gamma improves overnight-gap quantile forecasts only in low-VIX regimes (≈15% lower 0.99-quantile loss, Holm-corrected across 100 Clark–West tests), robust "to the sign convention"; the effect is strongest where conventional vol indicators are weakest — [OptionMetrics](https://optionmetrics.com/research/dealer-gamma-exposure-and-overnight-gap-risk-incremental-information-in-low-volatility-regimes/)
- The sign convention is an assumption: SpotGamma states dealer gamma is "estimated rather than directly observed"; a TradingView GEX script calls it "a common simplifying assumption, not measured positioning"; FlashAlpha's alternative signs each trade's aggressor by Lee–Ready against the NBBO — [SpotGamma](https://spotgamma.com/what-is-gex-gamma-exposure/); [SwiftEdge GEX script](https://kr.tradingview.com/script/wgAmu5Is-SwiftEdge-GEX/); [FlashAlpha](https://flashalpha.com/articles/flow-signed-gex-polarity-dealers-long-or-short-gamma)
- The GEX recipe the spec copies (OI × gamma × 100, calls positive, puts negative, scaled by the share price) is SqueezeMetrics' 2016/2017 white paper — [white paper PDF](https://slopeofhope.com/wp-content/uploads/2020/11/GEX-white_paper.pdf); [commentary](https://slopeofhope.com/?p=187436)
- Vanna/charm flows: no peer-reviewed test found; vendor pages (FlashAlpha, LuxAlgo, SpotGamma) describe the mechanism and anecdotes (an OptionMetrics quant's "nearly $1 billion of buying" from negative vanna on one day) — [OptionMetrics news](https://optionmetrics.com/news/vanna-and-the-big-put-unusual-suspects-in-a-market-mystery/); [LuxAlgo](https://www.luxalgo.com/library/concept/vanna-charm-flows.md)

### Inferences
- The literature's effects are short (10 minutes to an hour, or the last half hour) and conditional (illiquidity, low-VIX); the spec's day-ahead DEX/VEX/CEX drift rule has no published counterpart, and this audit found none in the data either.
- The sign-assumption problem has an observed answer only inside Cboe; outside it, any "dealer" book is customer-OI-with-a-convention, and the right response is a confidence (Key question 5), not a firmer convention.

### Gaps
- Full texts of Baltussen et al. (nd.edu PDF 503), Barbon–Buraschi (author site 502/503) and the Alpha Architect page (403) could not be fetched; their gamma-measure definitions and t-statistics are reported here only as the abstracts and summaries state them.
- Beckmeyer et al.'s realized-volatility result is not in any summary reached.
