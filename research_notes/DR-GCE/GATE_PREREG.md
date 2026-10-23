# DR-GCE — the falsification gate (section 7), pre-registered

Written and committed ALONE, before any signal, touch rate or outcome is computed. Every open choice is pinned here as
**[v0]**. Nothing beyond the gate is run: on a FAIL the work stops (no exit tuning, no variants, no full backtest).

## 1. The gate

- **Span**: exploration only, 2023-11-21 → 2026-10-09, the 28 held-out months excluded (2017-06 2017-09 2017-10 2018-01
  2019-07 2019-08 2020-06 2020-08 2020-11 2020-12 2021-01 2021-03 2021-05 2021-11 2022-04 2022-12 2023-05 2023-11
  2024-05 2024-06 2024-07 2024-08 2024-11 2025-08 2025-11 2026-03 2026-04 2026-08). **2023-11 is held out, so the span
  effectively starts 2023-12-01.** A guard wraps polars' readers and RAISES when a file named by a date in a held-out
  month, or outside the span, is opened (listing names is allowed). Sessions [v0]: full NYSE sessions (half days out:
  the Mode 1 afternoon window does not exist on them), 2023-12-01 → 2026-10-09, not held out — **504 sessions**, each
  with all four inputs on disk (counted from file names only).
- **Instrument**: SPXW 0DTE (the expiry-day chain `theta/data_full/chains/SPXW/<D>.parquet`: 1-min NBBO bid/ask/mid
  and sizes only — no IV, greeks or OI in it).
- **Entry**: the ask of the chain row in the minute immediately after the signal bar (section 2 timing).
- **Touch**: the bid reaches ≥ 1.18 × EntryAsk on one of the 4 chain rows after the entry row (minute quotes). The stop
  is −18% (bid ≤ 0.82 × EntryAsk) when G_max < 0.85 and −24% (bid ≤ 0.76 × EntryAsk) when G_max ≥ 0.85, read on the
  same rows; a stop on the same row as the touch or earlier is a FAIL. Neither in 4 rows = no touch.
- **Random baseline**: 500 draws. Each draw takes, for every real signal, its entry minute of day and its mode, a
  uniformly drawn exploration session and a direction (call/put 50/50), and applies the SAME contract rule (section 5)
  and the same stop rule (G_max from that session's book at that minute). A draw that finds no eligible contract or no
  standing quote is redrawn (session and direction), up to 50 tries [v0]. Seed 20261023.
- **Report**: signals per mode; touch rate with a 20-session moving-block bootstrap interval (audit_lib `block_draws`,
  2,000 draws, 2.5–97.5%, the touch rate as Σ touches ÷ Σ signals over every exploration session in calendar order,
  zero-signal sessions included); baseline touch rate and its interval = **the 2.5–97.5% spread of the 500 draw means
  [v0]**; per mode and per year; the touch rate against the 83% threshold.
- **Pass bar**: the signals' lower interval bound strictly above the baseline's upper bound. **Judged on the two modes
  pooled against the pooled baseline [v0]**; each mode is also shown against its own baseline (draws on that mode's
  minutes), information only.
- **Fail action**: stop. No exit tuning, no variants, no full backtest.

## 2. Data and timing [v0]

- **Bars**: bar stamp s = 0..389 is 09:30 + s. SPY's 1-min bar s is complete at minute s+1. The SPX index has one print
  a minute; the print stamped s+1 is taken as the close of bar s (the house reading, EMA system RULEBOOK_v0 §1).
- **S_t** = the SPX print (close of bar t). Returns, σ̂1m, Z_vel, distances, the GEX book and the walls are all in SPX
  points off S_t. **OHLC** (the reversal candle's body) is read on SPY's own bar (open/close); scaling does not change
  "inside the body", so no scale is applied there.
- **Volume** = SPY's 1-min bar volume. **VWAP** = SPY's session VWAP from 09:30, Σ((H+L+C)/3 · V) ÷ Σ V over bars 0..t
  (Theta's `vwap` field is not used: it is a running VWAP that includes pre-market), scaled to SPX by the bar's own
  ratio: VWAP_SPX,t = VWAP_SPY,t × S_t ÷ C_SPY,t.
- **Known at the signal**: everything a bar-t decision reads is known at minute t+1 — the SPX print stamped t+1, SPY's
  bar t, the chain row stamped t+1 (the NBBO at minute t+1), that morning's open interest. The entry row is the chain
  row stamped t+1 (the minute immediately after the signal bar t). *Ambiguity*: a row stamped m is the NBBO at minute
  m, so the entry ask is the quote at the instant the signal bar closes (zero latency); pinned as written, not varied.
- **Open interest** = UW's `oi_chain/SPX/<D>.parquet` field `open_interest` for session D: the count published the
  morning of D = **positions at D−1's close** (the prior close count; checked in PREREG_COMPASS_SCANNER: the chain dated
  D's `prev_oi` equals the chain dated D−1's). Matched by OCC symbol `SPXW<YYMMDD><C|P><strike×1000>` for the D expiry.
  A contract absent from the file has OI 0.
- **Rate / clock**: r = 0.045 (discounting only), T = (390 − m) ÷ 525,600 years at chain row m (calendar minutes to
  16:00), as the house's 0DTE readers.

## 3. Volatility (3.1) [v0]

- r_j = ln(S_j / S_{j−1}); σ̂1m = 1.4826 × median|r − median(r)| over the **last 60 one-minute returns**. *Ambiguity*:
  at 09:45 the session holds only 14 returns. Pinned: the 60 returns run back into the **previous trading day's last
  returns** (its prints; the overnight return between the sessions is left out) when that day is an exploration day
  (not held out); when it is held out (or absent) σ̂1m needs 60 in-session returns (from bar 60, 10:30). A window with
  fewer than 50 finite returns of its 60 leaves σ̂1m undefined (no signal at that bar).
- Z_vel,t = ln(S_t / S_{t−3}) ÷ (√3 · σ̂1m,t), S_{t−3} within the session (t ≥ 3).

## 4. Gamma (3.2) [v0]

- **Γ and IVs from real mids**: each 0DTE contract's IV is solved from its NBBO mid (both sides standing, ask ≥ bid > 0)
  by **Black-76 on the parity forward** F_m (scanner_lib `forward_im`: the strike K* with both sides standing and
  |C_mid − P_mid| smallest, F = K* + C_mid − P_mid), bisection on [1e-4, 10]; a mid outside the no-arbitrage bounds
  leaves the contract out (GEX 0). *Ambiguity logged*: greeks computed from real NBBO mids are **not synthetic quotes**
  (the "no synthetic BSM quotes" rule bans pricing a contract that has no real quote; it does not ban greeks inverted
  from a real quote); no trade is ever filled at a model price.
- Γ (per SPX point, spot) = e^{−rT} φ(d1) ÷ (F σ √T) × (F/S)²; Δ = e^{−rT} N(d1) × F/S for a call, e^{−rT}(N(d1) − 1)
  × F/S for a put.
- **GEX_K** (net per strike) = Σ over call and put at K of OI · 100 · Γ · S² · 0.01, + calls, − puts; strikes with
  |K − S_t| ≤ 2.5% of S_t; the 0DTE SPXW contracts only (the only chain on disk with real quotes; the AM-settled SPX
  monthly is not a 0DTE PM contract and is out).
- **Z_γ**: ΣGEX(x) recomputed over a spot grid x ∈ [0.975 S_t, 1.025 S_t] in 1-point steps, each contract's IV held at
  its solved value (sticky strike), F(x) = x · F/S, T unchanged, the strike set fixed at S_t's band. Z_γ = the linearly
  interpolated zero crossing **nearest S_t**. No crossing in the grid: the zero lies outside it, on the side the sign
  says (ΣGEX(S_t) < 0 → Z_γ above → negative regime; > 0 → positive).
- **Regime**: negative if S_t < Z_γ, positive if S_t > Z_γ (S_t = Z_γ: neither).
- **M_γ** = the strike of max |GEX_K| with |K − S_t| ≤ 1% of S_t (the "magnet").
- **Walls** ("strike wall", "opposing strike wall", "primary gamma wall"): **call wall CW** = the strike with the
  largest positive GEX_K in the ±2.5% band; **put wall PW** = the strike with the most negative GEX_K in the band
  (wherever the price stands; none when no strike has that sign). Mode 1's **opposing strike wall**: for a long call,
  the strike above S_t with the largest positive GEX_K (the call-side resistance above); for a long put, the strike
  below S_t with the most negative GEX_K (the put-side support below). None in the band → the band's edge (2.5% away).
  Mode 2's **primary gamma wall** = CW or PW (above).

## 5. Vol compression (3.3) [v0]

- σ_ATM = the mean of the call and put Black-76 IVs (from mids) at K* of the bar's chain row; VolRatio = σ_ATM ÷
  (σ̂1m · √(252 · 390)) ≤ 1.18, both modes, at the signal (Mode 2: at the trigger bar).

## 6. The modes [v0]

- **Mode 1 (Gamma Vacuum Squeeze)**, signal bar t with stamp in 09:45–11:45 (15..135) or 13:30–15:15 (240..345),
  inclusive: S_t < Z_γ; |Z_vel| ≥ 2.60; SPY V_t ≥ 1.8 × median(V over the prior 30 bars of the session — fewer when
  the session holds fewer, at least 15); distance |W − S_t| to the opposing strike wall ≥ 4.5 · √5 · σ̂1m · S_t; long
  call if Z_vel ≥ +2.60 and S_t > VWAP_t; long put if Z_vel ≤ −2.60 and S_t < VWAP_t; VolRatio ≤ 1.18.
- **Mode 2 (Climax Pin Snapback)**, trigger bar t with stamp in 10:00–14:45 (30..315), inclusive: S_t > Z_γ;
  |S_t − VWAP_t| ÷ (σ̂1m · S_t · √τ_vwap) ≥ 2.80 with **τ_vwap = t + 1, the minutes in the session VWAP** (*ambiguity*:
  the 1σ random-walk move over the minutes since the open, not τ/3); |S_t − W| ≤ 0.15% of S_t for W = CW or PW (the
  nearer when both); VolRatio ≤ 1.18. **High-side / low-side** is the stretch's side: S_t > VWAP_t (high side) → long
  put; S_t < VWAP_t (low side) → long call. **Reversal confirmation** on bar t+1 (the signal bar): SPY's close C_{t+1}
  strictly inside SPY bar t's body (min(O_t, C_t) < C_{t+1} < max(O_t, C_t)), and Z_vel,t+1 of the opposing sign
  (< 0 after a high-side stretch, > 0 after a low-side one; no magnitude threshold). Entry: the chain row stamped t+2.
- **One trade at a time per mode**: a mode's next signal is taken only when its entry row comes after the last row
  watched by that mode's previous trade (the touch, the stop, or the 4th row); the modes are independent. A signal with
  no eligible contract is counted as "no contract" and is not a trade (reported).

## 7. The contract (5) and G_max (6) [v0]

- At the entry row m: SPXW 0DTE in the trade direction (calls for a long call), both sides standing, |Δ| ∈ [0.40,
  0.54] (Δ from the row's mid, Black-76 on F_m), (Ask − Bid) ÷ Ask ≤ 0.035; pick the max C_K = (|Δ| · δS + ½ Γ · δS²)
  ÷ (|Θ_5min| + (Ask − Bid)), δS = 3 σ̂1m · S at the signal bar, Θ_5min = the Black-76 value at T minus the value at
  T − 5 minutes (same F and IV; intrinsic when T − 5 min ≤ 0); ties: the strike nearest F, then the lower strike.
- **G_max** = (|Δ| · ΔS_struct + ½ Γ · ΔS_struct²) ÷ EntryAsk, ΔS_struct = the distance from S to the nearest of {M_γ,
  the opposing wall} lying strictly beyond S in the trade direction (Mode 2's opposing wall: PW for a put, CW for a
  call; Mode 1's as in section 4), else the band's edge; the book read at the signal bar (Mode 2: the trigger bar t).
  Used ONLY to set the −18% / −24% stop.
- **VIX**: on disk (`theta/data/index/VIX`), **not read** — the gate does not need it (the trails come after TP3).
- **Missing quotes**: a row with no bid in the 4-row watch counts as neither touch nor stop (no carry forward).

## 8. Integrity

- A separate plain-loop script re-derives ≥ 20 signals (their conditions, contract and touch outcome) from the files:
  0 differences required.
- Lookahead: 3 sessions rebuilt with every input after the decision minute blanked; the signals must not change. A
  control that reads one minute ahead must change them.
- sha256 of every script recorded in the report.
