# Compass core specification v2 — locked

Status: LOCKED, 2026-10-21. Written from `reports/Compass engine audit.md` and the six notes under
`research_notes/Compass engine audit/` (clock_session, sweep_trigger, exits_sizing, greeks_books, move_atr_flow,
horizons), executing the owner's Phase 2 directive item by item. Nothing in this document is a grade, a score, a win
probability or an expected value: every number is the audit's measurement of a loss, a frequency or a distance, and
every detector below is a drawn object or a boolean tag with no claim attached. Where the owner gave no number the
text says **owner sets** and no number is invented. The owner's Phase 3 directive (2026-10-21, items 1.1 and 2)
resolved 5.5 on the live check and set the defaults in 3.5, 4.2, 6.3, 12.3 and 12.6 — each "configurable via
environment/settings, default …", the default the owner's; what is still owner-set is listed at the end.

Tags: **KEEP** (the rule as the owner wrote it), **CHANGED** (the owner's rule with the stated change), **DROPPED**
(out of the engine; may stay on screen as telemetry where said), **PENDING** (cannot be settled on the data on disk —
what settles it is in the blockers at the end). Count, by the heading of each numbered rule (0.1–16.2): 25 KEEP,
17 CHANGED, 9 DROPPED, 1 PENDING (12.2); 3.6 is KEEP or DROP at the owner's word, and 2.2's tags are its sub-rules'
(two KEEP, one DROPPED, one PENDING, one owner-set).

Conventions throughout (the audit's): minute t is New York's hour × 60 + minute; a 1-minute bar stamped t closes at
t + 1; a chain NBBO row stamped t is the quote at t; a contract is bought at the ask and sold at the bid, $0.65 a
contract each way, no fee on a worthless expiry; "fit" is 2022–2024, "check" is 2025-01-01 → 2026-10-09/13; N is
fit / check. Horizons: 0DTE (same-day), Weekly (4–7 DTE), Swing (8–28 DTE), LEAPS (90–365+ DTE). Every rule names the
horizons it binds; the matrix at the end lists them all.

---

## 0. Quote loading — one rule before any module reads a price

**0.1 Four-decimal rounding on load — CHANGED (directive item 1).**
Evidence: exits_sizing `verify.py` — paths stored as float32 read a bid of 1.05 back as 1.04999995 and missed a 1.05
threshold; after rounding on load, 80 of 80 re-derived exit paths agreed with the engine (sweep `verify.py`: 240 of 240
events, one stated difference).
Rule (every horizon, every price field: bid, ask, mid, last, strike, spot, settle, the straddle, the expected move):

```python
def load_price(x) -> float:
    """Every float32 or vendor-string price, at the moment it enters the engine. Nothing downstream re-rounds."""
    return round(float(x), 4)

EPS = 1e-9            # every threshold test after loading: bid <= level + EPS, bid >= level - EPS (the engine's own)
```

A threshold itself (0.68 × entryAsk, 1.25 × entryAsk, 0.90 × peak) is computed from the rounded entry ask and
compared with EPS; it is never rounded to the tick, because a resting limit is placed at the tick by the broker, not by
the engine (owner sets the tick rounding of resting orders at the order layer, outside this spec).

---

## Module 1 — Session clock and settlement

**1.1 The nine session windows — CHANGED (directive item 2): directionally neutral boolean flags.**
Evidence: clock_session §1 — every window reads neutral on 2022–2024 by the rule fixed before reading (N 2,218
window-sessions a window, SPY+QQQ+IWM 1-minute bars; context 2012/2017–2021 N 4,777); the only check-period label is
the power hour's chase (continuation 0.562 [0.524, 0.598]) at 0.490 in fit and 0.486 in context; no "reversal-prone"
window reverses the one before (revprev 0.48–0.51, CIs through 0.5).
Rule (0DTE; the flags are also the clock for every other horizon's EOD rules):

```python
WINDOWS = {                       # [start, end) in New York minutes; nothing else is attached to a window
    'pre_market':        (0,   570),
    'opening_drive':     (570, 595),
    'morning_reversal':  (595, 635),
    'mid_morning':       (635, 720),
    'lunch':             (720, 795),
    'pre_power':         (795, 825),
    'dealer_hour':       (825, 900),
    'power_hour':        (900, 930),
    'settlement':        (930, 960),
}                                 # t >= 960 is 'after_hours', a tenth flag with the same status
def window_flags(t):  return {name: (a <= t < b) for name, (a, b) in WINDOWS.items()}
```

No chase / fade / pin label, no "reversal-prone", no charm multiplier (1.0 → 3.5 dropped), no lunch block ("block
new long 0DTE scalps unless fading to the gross pin in positive gamma" — untestable for want of strike-level OI, and
dropped with the rest). The window names stay the owner's; each is a flag the UI and the logs may show. The one
measured property — the opening drive trends more than a random walk (efficiency 1.137 fit / 1.133 check) while its
first third does not predict its remainder (0.508 / 0.499) — is a note on the display, not an entry.

**1.2 charm_pressure and the GEX regime — DROPPED from every gate and every size; display telemetry only (directive item 2).**
Evidence: clock_session §3 — trend trades at 15:00 won 23% above the spec's "> 2.4×" charm_pressure threshold against
26% below (N 1,887 / 1,759); every power-hour long-premium trade −18 to −24% of premium in fit with CIs clear of zero,
trend −19.5% [−31.5, −6.9] in check; the fade/pin cells under GEX < 0 (N 95–236 a cell, one book year) have CIs through
zero and are negative without their best five days.
Rule: `charm_pressure` (|charm| ÷ its trailing-20 median, × the clock) and `sign(GEX_book)` are written to the
telemetry sink and shown on the panel; no function that returns an entry, an exit or a contract count takes either as
an argument (module 16's Helix isolation check covers them under the same test). A note on the display: in UW's sign,
net gamma is positive on 74% of SPX sessions but 32% of SPY's, 36% of QQQ's and 7% of IWM's — a sign off this feed is
not a stable regime label.

**1.3 The 10:00 inside-opening-range check — DROPPED (directive item 2).**
Evidence: clock_session §2 — the 10:00 spot is the 09:59 close, one of the thirty bars that define the range, so the
check is true on 99.6–99.8% of ETF sessions (SPXW 91–93%); the only way-in whose CI excludes zero is the sweep-and-return
fade held to the close, and it is negative (−12.3% of premium [−23.5, −0.7], N 1,644 / 1,537).
Rule: the check is removed. An opening-range breakout is a boolean event flag `or_breakout(t)` = the first 1-minute
close beyond the 09:30–09:59 high or low, valid from bar 31, no direction attached, no EV claim.

**1.4 The 15:58 flat — KEEP on SPY, QQQ and IWM, with one exception; SPXW `may_ride` boolean (directive item 2).**
Evidence: clock_session §4 — riding the nearest in-the-money contract to settlement loses $7.4 [−8.8, −6.1] fit and
$14.8 [−17.1, −12.6] check a contract on SPY (N 1,060 / 882), $10.0 / $21.5 on QQQ, $1–2 on IWM, negative in every year;
by moneyness, intrinsic 0.2–0.5% of spot rides +$1 to +$4 and 0.5–1% +$7 to +$14 on the ETFs (riding wins 60–65%);
SPXW nearest ITM +$16.3 [+5.0, +27.5] mean, median −$42, 5th percentile −$390, and "delta-aligned" separates nothing
(+$14.9 [−14.1, +43.3] against +$17.6 [−11.1, +48.8]).
Rule (0DTE):

```python
FLAT_MINUTE = 958                       # 15:58 New York; 12:58 on a half day
ITM_EXEMPT_SHARE = 0.002                # the owner's 0.2% of spot

def settlement_action(name, right, K, S_958, bid_958, may_ride):
    intrinsic = max(S_958 - K, 0.0) if right == 'C' else max(K - S_958, 0.0)
    if name in ('SPY', 'QQQ', 'IWM'):
        if intrinsic / S_958 > ITM_EXEMPT_SHARE:
            return 'HOLD_TO_SETTLEMENT'   # exempt from the forced sale at the 15:58 bid
        return 'SELL_AT_BID_958'
    if name == 'SPXW':
        return 'HOLD_TO_SETTLEMENT' if may_ride else 'SELL_AT_BID_958'   # a boolean, never "should ride"
```

`may_ride` is a boolean the owner sets (per desk or per session); it carries no delta condition and no claim. The
exemption was measured to 1% of spot; a contract deeper than that was not in the sample and the exemption stands on
the owner's word there. A held contract is valued at its intrinsic at the close; exercise and assignment handling is
the broker's, outside this spec. Caveat kept from the audit: SPXW's settlement is approximated by the 16:00 print
(about $0.50 of precision; the official series is not on disk).

---

## Module 2 — The trigger: sweep, exclusions, picker, outcomes

**2.1 The sweep detector — KEEP as a boolean gate and a drawn object; no EV claim, no weight (directive item 3).**
Evidence: sweep_trigger §1 — across 160 definitions and 225,390 event rows the underlying's forward return in the fade
direction is +0.1 to −1.8 bps at 30 minutes in both periods; the reference trigger's fade loses SPY −6.1% / −8.0% of
premium, QQQ −12.6 / −11.5%, IWM −18.6 / −13.7%, SPXW −4.5 / −5.1% (win 0.18–0.20); the definition picked on fit
(+$27.2, N 621) read −$56.4 on N 565 in check.
Rule — the detector, exactly as tested (sweep_trigger §7); 0DTE on SPY, QQQ, IWM, SPXW (SPXW detected on SPY's bars,
a stated proxy):

```python
# bars: 1-minute OHLC indexed by the minute the bar CLOSES (m = 1 closes at 09:31; m = 390 at 16:00).
# Levels L: ORH/ORL = max high / min low of bars 1..30 (valid from m = 31); PDH/PDL = the prior session's regular-hours
# high/low; PWH/PWL = the prior ISO week's; SH/SL = the running session high/low over bars 1..e-1, counted only once it
# has not moved for SH_AGE = 10 bars.  Parameters: X bps beyond the level (0 in the reference), k bars allowed for the
# close back inside (1 in the reference).
SH_AGE = 10

def sweep_high(bars, L, e, X=0, k=1):
    """High-side sweep whose excursion bar is e. Returns the return bar r (the tag's minute) or None."""
    thr = L * (1 + X / 1e4)
    if not (bars.high[e] >= thr and bars.close[e - 1] < L and bars.high[e - 1] < thr):   # beyond the line, from inside
        return None
    for r in range(e, e + k):                                                             # close back inside within k bars
        if bars.close[r] < L:
            return r
    return None
# sweep_low mirrors it: low[e] <= L(1 - X/1e4), close[e-1] > L, low[e-1] > thr, close[r] > L.
# depth_bps = (max high over e..r - L) / L * 1e4.  Episodes of one (level, side, X) are at least 30 minutes apart.
# The confirmation bar (close[r+1] < close[r], entry at r+1) is NOT used: its apparent lift was a selection effect
# (the close entry one bar earlier on the same episodes made +$16.1 / +$35.5).
```

The tag written for each sweep: `{level_name, L, side, e, r, depth_bps, X, k}`. `side` names the swept side; the side
label the owner's spec attached ("fade: PUT after a high-side sweep, CALL after a low-side one") is kept only as the
name of the side the structural stop refers to (module 3.2) — it is not a trade instruction.

**2.2 The exclusions — boolean tags, no direction, no EV claim.**
Evidence: sweep_trigger §2 — displacement-only continuation −10.2 / −10.8% of premium against the sweeps' −8.1 / −9.4%
(N 9,023 / 8,146 bars); ORH sweeps within 0.2% of PDH/PDL lose less (−4.6% against −7.5% and −10.3%) but stay negative
and their OOS +$70 rests on five SPXW days; the direction-by-window rule fails in every window; by UW's net gamma sign
the fade is −9.6% on positive days against −9.3% on negative (N 3,774 events, 245 sessions).
Rules:
- `displacement_only` (a displacement bar with no sweep) — KEEP as a tag.
- `orh_at_pd` (an ORH/ORL sweep whose level lies within 0.2% of PDH/PDL) — KEEP as a tag; the one ordering that was
  stable, still a loss.
- Direction by window (chase in the chase windows, fade in the fade windows) — DROPPED (fails in every window; the
  underlying within ±3.4 bps in every cell).
- "Positive gamma between walls" as a trade condition — PENDING (untestable: no strike-level OI history before
  2026-10); drawn as context when the strike book exists, never a gate.
- Product blocks ("block QQQ", "approve IWM") — owner sets the product list; the only ordering the data supports is
  SPXW ≈ SPY > QQQ > IWM, an ordering of losses (IWM, which the spec approves, is the worst product).

**2.3 SWEEP_FLOOR, BONUS_CAP, CONFIDENCE_CAP — DROPPED; the fitted score — not deployed (directive item 3).**
Evidence: sweep_trigger §4 — a logistic regression on the spec's features (N 7,989 fit / 6,928 check) has AUC 0.563 fit
and 0.528 check for "the fade nets > 0", a boosted model 0.773 → 0.513; the top decile by the fit threshold makes +$64
on 465 check trades, 95% [−44, 217], −$39 without the best five days, SPXW +$718 on 44 trades and QQQ −$83.
Rule: the three constants are deleted (module 16 proves it); the grade ≥ 90 / 80–89 thresholds, the "A" / "A+" names
and "triple confirmation upgrades an A setup" go with them. No 0–100 replaces them. What a setup shows is its boolean
tags, each documented on screen as not positive EV for long premium on 2022–2026.

**2.4 The picker's hard execution guards — KEEP (directive item 3), with one explicit outcome added.**
Evidence: sweep_trigger §5 — 0.1–0.2% of sweeps had no clean candidate; spread/mid ≤ 5% rejects 30–44% of IWM picks at
sweep minutes and most picks after 15:30 everywhere (SPY's pass share 0.999 at 09:30 → 0.478 at 15:30; IWM 0.945 →
0.042), and the rejected candidates lose more of their premium (SPY −28.5 / −24.7% against −4.1 / −7.2%); the
0.30–0.45 delta pick is unavailable 36–78% of the time after 15:30 (59% on IWM 13:45–15:30).
Rule (every horizon; the delta bands of the longer horizons are module 13's):

```python
SPREAD_MAX = 0.05

def eligible(c):                                    # c: one contract's quote at the entry minute, loaded by 0.1
    if not (c.ask > 0 and c.bid > 0 and c.bid <= c.ask):  return False      # quote hygiene
    mid = (c.ask + c.bid) / 2
    return (c.ask - c.bid) / mid <= SPREAD_MAX + EPS

def pick(chain, S, side, mode):
    """mode 'otm': the nearest strike at or beyond S on the trade's side; mode 'delta': |delta| in [0.30, 0.45]
    (0DTE; module 13's bands for Weekly / Swing / LEAPS). Returns a contract or an explicit outcome."""
    cands = [c for c in chain if on_side(c, S, side) and eligible(c)]
    if not cands:                      return Outcome('NO_TRADE', 'no eligible contract')
    if mode == 'otm':                  return min(cands, key=lambda c: abs(c.strike - S))
    band = [c for c in cands if 0.30 <= abs(c.delta) <= 0.45]
    return min(band, key=lambda c: abs(abs(c.delta) - 0.375)) if band else Outcome('NO_TRADE', 'no eligible contract')

def gate_inputs_complete(inputs):   # the owner's "missing score blocks the trade", kept as the guard it is
    return all(v is not None and v == v for v in inputs.values())        # a NaN anywhere → NO_TRADE('missing input')
```

"No eligible contract → no trade" and "missing input → no trade" are outcomes the log records by name, not silent
skips. Entry, when a lane places one, is at the ask stamped r (the quote at the return bar's close).

---

## Module 3 — 0DTE exits, scale-out and sizing

The state machine below is the engine the audit replayed (exits_sizing `engine.py`), with the owner's changes. It
binds 0DTE; the Weekly / Swing / LEAPS exits are module 12.

**3.1 The −32% premium backstop — KEEP (directive item 4).**
Evidence: exits_sizing test 1 — inside the stack the backstop is the exit on 0.7% (A, sweep fades, N 3,433) to 6.3% (B,
random minutes, N 3,672) of trades and its level changes nothing (−15, −20, −25, −32, −50% give −4.5% on A to the second
decimal); stand-alone it is the best premium level OOS (A −2.6%, B −0.6%); −15% fires within three minutes of entry
on 25.5% of trades against 2.4% at −32%; every level realises 3–5 points past nominal (the first bid at or below it is
already through). The ledger's −15.2% (0.886 / 5.83) is the average realised loss over losing trades, not a stop.
Rule: `PREM_STOP = 0.68` — sell all legs at the first minute's bid ≤ 0.68 × entryAsk + EPS. Never widened, never
tightened.

**3.2 The structural stop at the swept level — KEEP, buffer 0–2 bp (directive item 4).**
Evidence: exits_sizing test 1 — fires on 95.8% of sweep fades at +0 bp (realised −9.4%), 93.7% at +2 bp (−14.7%),
90.1% at +5 bp (−22.4%, worse in fit and no better in check); paired against none inside the stack ±0.6%.
Rule: `STRUCT_BUFFER_BPS` ∈ [0, 2] (owner sets within the band). After a high-side sweep (the fade side is PUT) the stop
is the underlying trading above `L × (1 + STRUCT_BUFFER_BPS / 1e4)` on a bar's high; after a low-side sweep (CALL) below
`L × (1 − STRUCT_BUFFER_BPS / 1e4)` on a bar's low; sell all legs at that minute's bid. For an entry with no swept level
(not a sweep lane) the structural stop is absent and the backstop stands alone.

**3.3 The breakeven lock — CHANGED: activation +0%, only while a T1 target is on (directive item 4).**
Evidence: exits_sizing test 2 — with T1 on, +6% beats no lock by +2.0% [+0.7, +3.3] (A) and +1.0% [+0.07, +1.9] (B) of
debit OOS; +12% loses to +6% by −1.2% [−1.9, −0.4]; +0% beats +6% by +1.0% [+0.1, +1.8] on A (+0.6% without the best
five days) and +0.3% [−0.2, +0.9] on B; without a target the lock's sign flips between periods (+4.1% then −2.0%). The
choke (64% of lock exits would have reached +25%) is flat from +0% to +12% (62.5–63.4%) — not a bid-ask-bounce artefact.
Rule: `LOCK_ACT = 1.00`. Armed at the first minute whose bid ≥ entryAsk − EPS; from the NEXT minute on, sell all
remaining legs at the first bid ≤ entryAsk + EPS. The lock exists only while a T1 target is on the position (3.5); it
stays in force for the trailed remainder after T1 fills (that is how the evidence was produced). It is a smaller loss,
not a profit.

**3.4 The trail — CHANGED: a flat 10% from the peak once +6% (directive item 4).**
Evidence: exits_sizing test 3 — the VIX-tiered 6/8/11/14% trail against a flat 10% is paired −0.05% [−0.7, +0.7] fit and
+0.3% [−0.2, +0.9] check on A, −0.1 / +0.1% on B; within each VIX tier the tier's own rate never beats the best flat
rate in both periods; the whole spec stack against "−32% stop plus a flat 10% trail from +6%" is −2.3% [−3.8, −0.9] on
B OOS. A simplification; no EV claim (a trail against none flips sign between periods: +3.2% then −1.7%).
Rule: `TRAIL_ACT = 1.06`, `TRAIL = 0.10`. `peak_prior(m)` is the highest bid from entry through minute m − 1. The trail
is active at minute m once `peak_prior(m) ≥ 1.06 × entryAsk − EPS`; it sells the trailed legs at the first active
minute whose bid ≤ `0.90 × peak_prior(m) + EPS`.

**3.5 Targets and the scale-out — CHANGED: where size ≥ 2, one contract at T1 +25% and the remainder trailed; no T2 (directive item 4).**
Evidence: exits_sizing test 5 — T1 +25% all-out needs a 60.8–62.8% win rate against its −37% realised loss and gets
46.8–49.4%, so it loses 8–10% of debit and is worse than no target OOS (B −7.7% [−14.2, −2.0]); T2 at +45–50% needs
43–46% and gets 34–37%; a scale-out that keeps a trailed leg beats the one-contract T1 exit by +0.6–0.7% (A) and
+0.7–1.0% (B), CIs clear of zero; 1@+25 + 1@+50 with no trailed leg is as bad as all-out; two, three or four contracts
are immaterial (−5.4 to −5.6%); bid_size ≥ 1 at every target exit minute.
Rule: `T1 = 1.25`. With `size ≥ 2`: one contract rests at `1.25 × entryAsk` (a limit; fills at the first minute whose
bid ≥ T1 − EPS, and a target minute equal to a common-exit minute goes to the target), the other `size − 1` are
trailed (3.4), with the lock (3.3) on. T2 is gone. With `size = 1` (configurable via environment/settings, default
`ONE_LOT_SHAPE = 't1_lock'` — the owner's Phase 3 choice): the one contract exits 100% at T1 (+25%) with the +0%
breakeven lock (3.3) active — shape (a) of the two tested; shape (b), no target, no lock, the trail alone, stays
selectable. The loss is stated, not hidden: the stack as written with one contract sold at T1 +25% lost −4.3% /
−4.5% of debit on the sweep universe (exits_sizing `t0_spec_stack_A`, "spec 1c", 2022–24 / 2025–26); test 5's T1
all-out with the lock read −8.5% OOS on A and −8.3% on B, and shape (b) −2.6% / −0.6% OOS (the best single exit in
check and the worst in fit, its +234% average win a handful of days). Neither is positive; the default is the owner's
choice, the loss the audit's measurement. A one-lot Swing position (DTE ≥ 8) is 12.6's rule.

**3.6 The 5-minute time stop — KEEP or DROP, owner sets.**
Evidence: exits_sizing test 4 — fires on 47% of trades and sells them at −13% where holding would have averaged −12 to
−13%; 10, 15, 30 and 60 minutes the same within noise; paired 5 min against none −1.3% [−6.4, +3.3] then +1.3%
[−2.1, +4.4] (A).
Rule: `TIME_STOP = None` or an integer of minutes (owner sets; 5 is as good as any). If set: at minute `e + TIME_STOP`,
if the peak bid through that minute < `1.06 × entryAsk`, sell all legs at that minute's bid.

**3.7 The hard flat — KEEP.** Module 1.4's rule: `HARD_FLAT = 958` (12:58 on a half day); every leg still open sells at
that minute's bid unless 1.4 exempts it.

**3.8 The stack as one state machine (code-ready pseudocode).**

```python
PREM_STOP, LOCK_ACT, TRAIL_ACT, TRAIL, T1, HARD_FLAT = 0.68, 1.00, 1.06, 0.10, 1.25, 958
ONE_LOT_SHAPE = 't1_lock'      # configurable via environment/settings; default the owner's (Phase 3); 'trail_only' selectable
# owner sets: STRUCT_BUFFER_BPS in [0, 2]; TIME_STOP (None or minutes)

def run_stack(entry_m, entryAsk, size, bids, bars, swept):       # bids[m] = the bid at minute m, loaded by 0.1
    a0 = entryAsk
    if size >= 2:                                   # one contract at T1 +25%; the rest trailed 10% from the peak once +6%; the lock on
        legs = [('target', 1), ('trail', size - 1)]
    elif ONE_LOT_SHAPE == 't1_lock':                # size == 1, the default: 100% out at T1 +25%, the +0% lock active
        legs = [('target', 1)]
    else:                                           # size == 1, 'trail_only': no target, no lock, the trail alone
        legs = [('trail', 1)]
    t1_on = any(kind == 'target' for kind, _ in legs)
    peak = None; peak_prior = None; lock_armed_at = None
    for m in range(entry_m + 1, HARD_FLAT + 1):
        b = bids[m]
        peak_prior = peak
        peak = b if peak is None else max(peak, b)
        # ---- common exits: all remaining legs; the earliest wins, ties in this order ----
        reason = None
        if b <= PREM_STOP * a0 + EPS:                                               reason = 'prem_stop'
        elif swept and through_level(bars[m], swept, STRUCT_BUFFER_BPS):            reason = 'struct'
        elif t1_on and lock_armed_at is not None and m > lock_armed_at and b <= a0 + EPS:   reason = 'be_lock'
        elif any(k == 'trail' for k, _ in legs) and peak_prior is not None \
             and peak_prior >= TRAIL_ACT * a0 - EPS and b <= (1 - TRAIL) * peak_prior + EPS:  reason = 'trail'
        elif TIME_STOP is not None and m == entry_m + TIME_STOP and peak < TRAIL_ACT * a0 - EPS:  reason = 'time'
        elif m == HARD_FLAT:                                                        reason = 'flat'
        # ---- the target leg fills first on its own minute (a tie goes to the target) ----
        if t1_on and b >= T1 * a0 - EPS:
            fill('target', T1 * a0, m); legs = [l for l in legs if l[0] != 'target']; t1_on = False
            # the lock stays in force for the trailed remainder (as tested)
        if reason is not None:
            for kind, n in legs: fill(kind, b, m, reason)          # all remaining legs at this minute's bid
            return
        if t1_on and lock_armed_at is None and b >= LOCK_ACT * a0 - EPS:
            lock_armed_at = m                                       # arms this minute; may exit from the next
    # legs still open past HARD_FLAT are the 1.4 exemptions: settle at intrinsic
```

Notes the owner should read: in the replay the lock armed on the peak INCLUDING the current minute and exited only at
a later minute; the trail compared the current bid with the peak THROUGH THE PREVIOUS minute; a stop sells at the bid
of the minute it first triggers (a bid that gaps through the level sells at the gapped bid); a target fills at its
price. Intra-minute ticks were not observed — a tick-watching engine fires earlier within the minute than this replay.

**3.9 Sizing — CHANGED: by the dollar risk budget; the count cap (< 5) DROPPED.**
Evidence: exits_sizing test 6 — the displayed NBBO covers 2 contracts on 95–96% of trades at entry and exit, 3 on
92–94%, 5 on 89–92%, 10 on 80–85% (SPXW thinnest); per-contract EV by quoted size is non-monotonic; "≥ 5 contracts had
negative EV" is a losing engine on its largest tickets, not a size effect.
Rule (named inputs, owner sets the budget):

```python
RISK_PER_TRADE_USD = owner_sets          # the dollars the backstop may lose on one position, nominal
size = floor(RISK_PER_TRADE_USD / (entryAsk * 100 * (1 - PREM_STOP)))     # the backstop's nominal loss a contract
# the realised loss on a backstop exit ran 3-5 points past nominal (p10 -40%): the budget is nominal, not a bound
# owner sets whether size is also capped at the displayed ask_size at the entry minute (a hygiene rule, no EV claim)
```

No size is ever read off a ledger's size-EV correlation without the one-contract counterfactual.

---

## Module 4 — Risk governor

**4.1 The rolling 30-trade profit-factor breaker (PF < 1.05 → paper) — DROPPED (directive item 4).**
Evidence: exits_sizing test 7 — live-only EV worse than no breaker in 7 of 8 product × universe cells in 2025–2026 (A
SPY −3.7% all against −8.2% live-only; IWM −7.6 against −16.3%); the trades it skips win as often as the ones it takes
(22–36% against 25–37%); on 2,000 simulated streams of 200 trades shaped like the stack's outcomes and shifted to a
true +5% of debit it trips in 49% (A) to 85% (B) of runs, median first trip at trade 71–99; on a fat-tailed exit shape
(13% wins, +240% average win) ~100% at +10% and 95–98% at +20%.

**4.2 A hard daily dollar drawdown cap — CHANGED (the replacement), parameters as named inputs with the owner's defaults (Phase 3 item 2).**
Rule (every horizon; one cap for the account; each input configurable via environment/settings, the default the
owner's):

```python
DAILY_DD_CAP_PCT   = 0.03                   # default 3.0% of start-of-day account equity: the day's loss at which no new entry is placed
PAPER_DD_CAP_USD   = 500                    # default $500 flat in paper mode, in place of the percentage
DD_BASIS           = 'start_of_day_equity'  # the cap is read against the account's equity at 09:30 New York
DD_SCOPE           = 'account'              # one cap for the whole account, every lane and name together
DD_RESET           = 'next_session_open_NY' # the day is New York's; the count starts at zero at 09:30
RE_ENTRY           = 'none_that_session'    # a hard cap: once breached, no new entry until the next session
DD_MARK            = owner_sets             # 'realised' or 'realised_plus_open_at_bid' (open legs marked at the current bid) — unnamed by Phase 3

def dd_cap_usd(equity_sod_usd, paper):
    return PAPER_DD_CAP_USD if paper else DAILY_DD_CAP_PCT * equity_sod_usd

def governor(day_pnl_usd, equity_sod_usd, paper):
    if day_pnl_usd <= -dd_cap_usd(equity_sod_usd, paper):  return 'HALT_NEW_ENTRIES'   # until the next session; open positions keep their exit stack
    return 'OPEN'
```

The cap halts entries, never exits: module 3 keeps running on what is open. The default is set; the audit's noise
table (`exits_sizing/out/t7_breaker_noise_{A,B}.csv`, the method in `run_tests.py`) is still recomputed for the actual
lane's win-rate shape with the cap in place of the breaker before the lane runs on it, and the UI states that a
30-trade window had the trip rates above.

---

## Module 5 — The Black-Scholes / implied-vol engine

**5.1 The pricer and the inversion — KEEP.**
Evidence: greeks_books KQ1/KQ2 — delta, theta, charm, vanna and rho agree with finite differences to 1e-7 and put-call
parity to 1e-12; 60 bisections on [0.01, 3.00] never bound on these chains; the skip rule mid − intrinsic ≤ 0.01
removes 4.7% of near-money rows in the first half hour and 32.5% in the last (980 SPY sessions, 8.6 M
contract-minutes), costing ≤ 0.6% of near-money gamma before 15:30 and 2.8% after; 0.005 changes nothing, 0.02 skips
47% of near-money rows in the last half hour; r = q = 0 on 0DTE is immaterial (rτ ≤ 0.011% of K).
Rule: European Black-Scholes; IV by bisection on [0.01, 3.00] × 60; skip a row where `mid − intrinsic ≤ 0.01`; on
0DTE r = q = 0. τ is one clock for the inversion and the repricing: a vol is only right on the τ it was inverted with
(the house's rule, CLAUDE.md `UW_VOL_CONVENTION`).

**5.2 r and q — CHANGED: forward parity, r − q := ln(F/S)/τ from the ATM put-call pair; SOFR r for discounting only (directive item 5).**
Evidence: greeks_books KQ1 — same-strike call and put vols from the mids agree to −0.17 vol points (median; 48%
positive) under r = 4.15%, q = 0 and are +4.04 points apart under r = 0 in 100% of 67 snapshots; the forward-implied
r − q from the ATM pairs is 4.07% median (3.6–4.7% by year); UW's own greeks are reproduced from UW's IV only at r = 0,
q = 0 (best-fit r 0.0000, IQR 0–0, 68 snapshots, 17,332 rows with greeks).
Rule (every horizon with DTE ≥ 1; one r − q per expiry being priced):

```python
def forward_carry(S, K_atm, C_mid, P_mid, r_sofr, tau):
    """r - q read off the chain itself: C - P = S e^{-q tau} - K e^{-r tau}  =>  F = K + (C - P) e^{r tau}."""
    F = K_atm + (C_mid - P_mid) * exp(r_sofr * tau)        # K_atm: the listed strike nearest S; mids at one instant
    return log(F / S) / tau                                 # enters d1 and d2; q is never needed on its own

def bs_price(right, S, K, sigma, tau, r_sofr, r_minus_q):
    F  = S * exp(r_minus_q * tau)
    d1 = (log(S / K) + (r_minus_q + 0.5 * sigma**2) * tau) / (sigma * sqrt(tau));  d2 = d1 - sigma * sqrt(tau)
    df = exp(-r_sofr * tau)                                 # SOFR: the discount factor, nothing else
    return df * (F * N(d1) - K * N(d2)) if right == 'C' else df * (K * N(-d2) - F * N(-d1))
# the floor under the skip rule in 5.1 is the forward-consistent one: df * max(F - K, 0) for a call, df * max(K - F, 0) for a put
```

**5.3 The benchmark — CHANGED: put-call parity on the chain, never UW's greeks (directive item 5).**
Evidence: as 5.2 (UW's engine is r = 0, q = 0, τ = calendar days/365; at r = 4.15% the delta error against UW is 0.0106,
p90 0.043 — a convention difference, not an error in the pricer).
Rule: the engine's self-test is `|IV_call − IV_put|` at the same strike and instant on the chain's mids, read per
expiry; the audit's reading of a correct r − q is a median gap under one vol point with a random sign. ThetaData greeks
are the second benchmark when the terminal is free (blocker). UW's greeks are never a benchmark; the 1.15–1.25
put/call gamma asymmetry the house saw is the arithmetic of inverting at r = 0 when the forward carries 4%.

**5.4 The ITM sentence — CHANGED (wording).**
Evidence: greeks_books KQ1 — ITM calls more than 3% in (N 2,879) have 0.0% of mids at or below intrinsic under r = 0 and
5.7% under r = 4.15%, q = 0; deep ITM puts (N 848) have 32.0% at or below K − S under r = 0 and 0% under r = 4.15%.
Rule: the spec reads — "Under r = 0 a deep in-the-money put is often quoted below K − S (32% at the close on SPY
monthlies), so no vol solves; the forward-consistent floor restores one. In-the-money calls are unaffected under r = 0
and more often unsolvable under r > 0 with q = 0 (5.7%)."

**5.5 trailField and UW's live vols — KEEP: no rate patch (directive item 5, resolved by Phase 3 item 1.1).**
Evidence: the live check ran on 2026-10-21 at 20:36 UTC (`research_notes/Compass engine audit/greeks_books/
q1c_live_uw_check.py`, results in `q1c_results.txt` beside it): SPY `stock-state` 773.21; `option-contracts` for
2026-11-20 (30 DTE), 195 usable contracts within 10% of spot. UW's own `implied_volatility` field is parity-consistent
at the market's carry: same-strike IV_call − IV_put median +0.13 vol points (n 51), where an r = 0 inversion of the mids
gives +3.32 and an r = 4.15%, q = 0 inversion +0.04; the ATM put-call forward is 776.00 against spot 773.21, r − q =
+4.38%. So the live IVs stand on about 4% carry, the house's `UW_VOL_CONVENTION` (r = 0.0415, q = 0, measured
2026-10-13 on 8,096 `/option-trades` prints) is confirmed for the live chain, and trailField's repricing is right. UW's
printed GREEKS are another matter: on the 68 historical snapshots and on the live chain the delta best-fits r = 0 (live
rmse 0.028 at r = 0 against 0.040 at r = 4.15%) — UW's greek fields and its IV field do not share a convention. The
house never reads the greek fields (it reprices from the IV), so nothing depends on them.
Rule: price UW's IV under `UW_VOL_CONVENTION`; never consume UW's printed delta, gamma or theta for pricing; the
benchmark is put-call parity (5.3). trailField is unchanged. The house's own forward pricer keeps 5.2's
r − q := ln(F/S)/τ as it stands.

---

## Module 6 — Dealer exposure books, the flip, the walls and the confidence

**6.1 The GEX arithmetic — KEEP; the regime a descriptive label; "never direction" confirmed.**
Evidence: greeks_books KQ3/KQ4 — the house's sum stands within ±0.05 of UW's book-level net/gross on 12 of 15 name-days,
the sign agreeing on 12 of 15 with every disagreement at |net/gross| < 0.07; on 836,160 ticker-days the next
open-to-close return by exposure quintile is GEX +0.0 bp (t 0.01) / +2.0 (t 0.62) by half; on SPY/QQQ/IWM the hit rate
of sign(X) against sign(o-c) is 0.43–0.59; with UW's 30-day IV added the GEX term on next-session realised vol is +0.011
(t +0.55) / −0.063 (t −3.17) on SPY.
Rule: the house's sum, sign and units (OI × greek × price², the house's sign) stand. The regime (sign of GEX_book) is a
label on the panel with no weight (1.2). Call versus put is never picked from the regime sign.

**6.2 DEX / VEX / CEX drift rules (raw against negated) — DROPPED from the engine; a watch list for a second year.**
Evidence: greeks_books KQ3 — no convention predicts next-hour or next-day drift; CEX Q5 − Q1 +6.5 (t 1.38) / +7.4
(t 1.74) by half, +7.0 (t 2.20) over the year — 7 bp a day gross, below any options round trip, on six months of
confirmation.
Rule: recorded daily, nothing into the engine.

**6.3 The flip — KEEP Method A; Method B under its own name or dropped (owner sets); tiers in units of the day's ATM straddle M (directive item 5; the tiers the owner's, Phase 3 item 2).**
Evidence: greeks_books KQ4 — Method A found in 67 of 67 snapshots (66 within 3%), |F_A − S| median 33 bp; Method B has a
zero in 56 of 67 and where both exist |B − A| median $11.37 (188 bp), p90 $22.88, more than one strike step apart in
95% of cases, the same side of spot 57%; the 1 / 5 / 12 / 25 bp tiers are 1/20, 1/4, 2/3 and 1.4 of SPY's $1 strike
step (18 bp).
Rule (every book, every horizon):

```python
def flip_A(profile):        # profile: [(strike, net GEX at the strike)] sorted; the house's core/walls.ts pickFlip
    """The linear zero crossing of the per-strike profile nearest spot, to the cent; a gap where none."""
    for (a, va), (b, vb) in pairs(profile):
        if va == 0: return a
        if va * vb < 0: return a + (b - a) * abs(va) / (abs(va) + abs(vb))
    return None
# Method B (the spot at which the whole book's gamma re-priced on a 0.05% grid is zero, sticky-strike vols) is a
# different object: shown as "book zero (B)" or not shown — never called "the flip". Owner sets which.

# The flip's distance from spot in units of the day's 1.0 x ATM straddle M (module 7.1), never bps; configurable via
# environment/settings, the defaults the owner's (Phase 3). A tier is a label on the panel with no claim attached.
FLIP_TIERS_M = [(0.05, 'breached'), (0.15, 'critical'), (0.35, 'warn'), (0.75, 'watch')]   # upper bound inclusive; beyond 0.75 M 'safe'

def flip_tier(spot, F_A, M):
    """tier(|spot - F_A| / M): <= 0.05 M breached; <= 0.15 M critical; <= 0.35 M warn; <= 0.75 M watch; > 0.75 M safe."""
    d = abs(spot - F_A) / M
    for bound, name in FLIP_TIERS_M:
        if d <= bound + EPS: return name
    return 'safe'
```

**6.4 The walls, the king, the pin and the three books — KEEP the definitions and the slicing; every level labelled by its book.**
Evidence: greeks_books KQ4 — the 25- and 60-DTE expiries on one date give the same call wall on 8 of 33 dates, the
same put wall on 4; the 0DTE book's call wall never matched the Macro book's on 15 name-days, the Near book's did on 9;
on 34 dates the next session reached a monthly wall no more often than its mirror strike (call wall 3% against 10%,
put wall 4% against 4%, king 10 / 10%).
Rule: three books — `0DTE` (today's expiry), `Near` (≤ 14 calendar days), `Macro` (the rest, to the owner's horizon);
the call wall, put wall, king and pin computed per book by the owner's definitions (unchanged; the house's `pickWalls`),
and printed with the book's name beside them ("0DTE call wall 784 · Macro call wall 785" are different claims). A
wall's reach is a claim nothing here makes; the terminal's own track record (data/feed/trackRecord.ts) is the
instrument for intraday 0DTE walls, with its "insufficient data" rule.

**6.5 The sign gate → the confidence — CHANGED (directive item 5).**
Evidence: greeks_books KQ5 — on SPY 40% of the year's sessions had |conf| < 0.10 and 64% of the 56 day-to-day sign flips
happened there (QQQ 60%, IWM 71%); conf is 0.95–0.96 correlated with the house's tanh-of-p85 display scale; the two
engines on one open interest disagree only at |net/gross| < 0.07.
Rule (one conf per book; no EV claim — nothing shows the sign carries drift):

```python
def conf(book):             # book: the per-strike call and put GEX of one book (0DTE, Near or Macro), the house's sign
    net   = sum(book.gex_call) + sum(book.gex_put)
    gross = sum(abs(x) for x in book.gex_call) + sum(abs(x) for x in book.gex_put)
    return net / gross if gross > 0 else 0.0                          # in [-1, 1]

def conf_agree(conf_uw, conf_house):                                  # where both engines give the book
    return min(abs(conf_uw), abs(conf_house)) * (1.0 if sign(conf_uw) == sign(conf_house) else 0.0)

DEAD_ZONE = 0.10            # |conf| < 0.10 is neutral: the band in which two engines on one OI disagree, not a tuned constant
```

Downstream multiplies by `conf` (or by |conf| with the sign carried separately) wherever the spec tested
`sign(GEX_UW) == sign(GEX_house)`; a book in the dead zone contributes 0, never a veto. The house's tanh display scale
may stay as the display.

**6.6 Units — KEEP ÷365 and VEX/100; the unit printed on every figure.**
Evidence: greeks_books KQ6 — 365.25 against 252 is a factor 1.450, against the house's 365 0.07%; UW's book-level charm
and vanna could not be reproduced from the chains (ratios 0.01–6).
Rule: CEX per calendar day = CEX_year / 365; VEX per vol point = VEX / 100; UW's charm (a year's) divided by 365 where
read (the house already does); every printed figure carries its unit.

---

## Module 7 — Expected-move bands and the king scanner

**7.1 The band — CHANGED: M = straddle, labelled "~63% open containment" (directive item 6).**
Evidence: move_atr_flow Q1 — on 3,654 sessions × 14 scans the 68.3% quantile of |close − spot| / straddle at 09:35 is
1.09–1.19 and 0.70–0.95 in the last 90 minutes (ETFs); 1.0 × holds 59–65% of closes, 1.2533 × 70–75% (more than its
nominal 68.3%); RMS 1.15–1.29.
Rule (0DTE; the Swing engine's 1 × EM target in module 12 uses the same M on its own expiry):

```python
M       = straddle_mid(expiry, strike_nearest_spot)     # the ATM call mid + put mid at the scan, loaded by 0.1
upper_1 = S + M;  lower_1 = S - M
LABEL   = "~63% open containment"                       # never "1 SD", never 1.2533 x
# if a 1-SD band is ever wanted: 1.10-1.15 x M at the open tapering to 0.9 x after 14:00 (the measured quantile),
# never 1.2533 x; owner sets whether such a band is drawn at all
```

SPXW's late-day containment (58–60% of sessions beyond ±1.0 × at 15:50) is PENDING — the 16:00 print against a 15:50
straddle — and is not used until the print is checked against the official settlement.

**7.2 The boundary fade — DROPPED (directive item 6).**
Evidence: move_atr_flow Q1 — at the first touch of spot ± M the close is back inside 0.46–0.52 of the time at both
multipliers (upper touches 0.42–0.43 on SPY/QQQ/SPXW); the nearest-OTM fade loses −11 to −29% a trade in every product,
period and multiplier (SPY M = straddle −$5.27 [−7.66, −2.35] fit on 4,076 trades, −$9.14 [−15.6, −3.3] check on 3,408),
every year negative, the best fit scan of each product × multiplier negative in check in all eight cases.
Rule: no trigger at upper_1 / lower_1. The band is a ruler.

**7.3 The king's reachability gate — KEEP |dist_em| ≤ 1.0 with distance-band odds; the king's extra reach DROPPED (directive item 6).**
Evidence: move_atr_flow Q2 — a level within 1 M is reached 63–67% of the time, at 1–2 M 14–21%, and the mirror strike
at the same distance is reached at the same rates (SPY ≤ 1 M: 0.671 against 0.680 fit, 0.666 against 0.673 check;
41,000 scan rows, the king proxied by the strike with the most same-day volume — gross gamma by strike not on disk).
Rule:

```python
dist_em  = abs(K_target - S) / M
reachable = dist_em <= 1.0
REACH_ODDS = {'<=0.5 M': '65-87%', '0.5-1 M': '41-45%', '1-1.5 M': '18-26%'}     # shown beside the target, by band
```

The odds are the distance's, shown as measured; the king carries no reach of its own. The true king (gross gamma by
strike, per minute) needs the recorded strike book (PENDING, blockers).

---

## Module 8 — ATR exhaustion and the swing entry preference

**8.1 |move_atr| > 1.5 — CHANGED: a hard block on counter-trend session-extreme fades regardless of gamma sign (directive item 6).**
Evidence: move_atr_flow Q3 — after a sweep of the session extreme on a day already extended more than 1.5 ATR14 in that
direction, the close is back inside the extreme 0.439 / 0.301 of the time on SPY (41 fit / 83 check sweeps) and 0.413 /
0.310 on QQQ (75 / 84) against 0.47–0.53 otherwise, the underlying running a further 8–35 bps to the close against the
fade; IWM does not show it (0.600 / 0.556); the gamma cells hold 5–47 events with inconsistent signs, and UW's net gamma
is negative on 64–68% of days. A ledger finding, not a causal rule; the fade it blocks loses in every bucket anyway.
Rule (0DTE):

```python
atr14    = wilder_rma(true_range_daily, 14)[t - 1]            # known at the event: lagged one session
move_atr = (S_t - prior_close) / atr14
def block_counter_trend_fade(sweep, S_t, prior_close):
    if sweep.level_name not in ('SH', 'SL'):  return False     # the session extreme only
    counter = (sweep.side == 'hi' and S_t > prior_close) or (sweep.side == 'lo' and S_t < prior_close)
    return counter and abs(move_atr) > 1.5                      # whatever the gamma sign
```

**8.2 "Prefer pullback over range_position > 0.95" (Swing / LEAPS) — DROPPED as a rule; an entry-price preference with no return claim.**
Evidence: move_atr_flow Q3 — on the ETFs' daily bars 2012/2017–2024 pullback and near-mean entries beat chase entries
on 20-day returns with ranges that include zero (SPY pullback +74 bps [−79, +142], N 69); 2025–2026 reversed it (SPY
chase_20 +162 bps [+142, +292], N 83); the 3,320–3,891-name cross-section shows no pullback premium (t −1.0) and a weak
5-day reversal after 20-day-high closes (−24 bps, t −2.2).
Rule: `range_position` is shown; nothing is gated or sized on it.

---

## Module 9 — FVG, order block, OTE: drawn objects and boolean tags

**9.1 The three constructs — KEEP as drawn objects with sweeplib's definitions; no entry condition, no upgrade, no claim (directive item 3).**
Evidence: sweep_trigger §3 — on 16,980 (k = 1) and 25,028 (k = 3) episodes the OTE fills 55–63% of the time at −8.9 /
−10.4% of premium against the sweep close's −7.9 / −9.4%; the order block fills 59–68% at −8.1 / −10.1% and is present
on 99.7% of sweeps (not a condition); an FVG is present on 4.5% and marks events whose underlying continues against the
fade more (−1.0 / −5.7 bps against −0.4), win 0.199 / 0.185 against 0.193 / 0.193.
Rule — the definitions as tested (`sweep_trigger/sweeplib.py`), drawn on the chart and written as tags
`{fvg_present, order_block, ote_fill_minute, ob_fill_minute}`:

```python
GEOM_WAIT = 30                                   # bars allowed after r

def fvg_present(h, l, r, side):
    """A three-candle gap in the fade direction with its window ending at r-1 or r (known at r):
    bearish (side 'hi'): low[t-2] > high[t]; bullish (side 'lo'): high[t-2] < low[t]."""
    for t in (r - 1, r):
        if t - 2 < 1: continue
        if side == 'hi' and l[t - 2] > h[t]: return True
        if side == 'lo' and h[t - 2] < l[t]: return True
    return False

def order_block(o, h, l, c, r, side):
    """The last opposite-colour candle in [r-5, r-1]; zone = its body; a doji (body under one tick) takes its full
    range; a zero range is no block. Returns (zlo, zhi) or None."""
    for t in range(r - 1, max(r - 6, 0), -1):
        up = c[t] > o[t]
        if (side == 'hi' and up) or (side == 'lo' and not up):
            body = abs(c[t] - o[t])
            if body >= 0.01: return (min(o[t], c[t]), max(o[t], c[t]))
            if h[t] - l[t] >= 0.01: return (l[t], h[t])
            return None
    return None

def ote_fill(h, l, c, r, H, side, close_m, wait=GEOM_WAIT):
    """After the return bar r the impulse runs from the sweep extreme H to the running extreme of the displacement;
    the fill is the first bar whose range reaches the 0.62-0.705 zone of that leg measured back toward H (the near
    edge 0.62 is the test, 0.705 the zone's far edge). Doji guard: the leg must be >= 1 bp of price; a bar through H
    voids the setup. Returns the fill minute or None."""
    for t in range(r + 1, min(r + wait, close_m) + 1):
        if side == 'hi':
            leg_lo = min(l[r:t]); leg = H - leg_lo
            if leg < 1e-4 * H: continue
            if h[t] > H: return None
            if h[t] >= leg_lo + 0.62 * leg: return t
        else:
            leg_hi = max(h[r:t]); leg = leg_hi - H
            if leg < 1e-4 * H: continue
            if l[t] < H: return None
            if l[t] <= leg_hi - 0.62 * leg: return t
    return None

def ob_fill(h, l, r, zone, H, side, close_m, wait=GEOM_WAIT):
    """The first bar after r whose range returns into the order block; voided by a bar through H."""
    if zone is None: return None
    zlo, zhi = zone
    for t in range(r + 1, min(r + wait, close_m) + 1):
        if side == 'hi':
            if h[t] > H: return None
            if h[t] >= zlo: return t
        else:
            if l[t] < H: return None
            if l[t] <= zhi: return t
    return None
```

"Triple confirmation upgrades an A setup" is rejected; the triple-confirmed subset has the same win rate and a worse
underlying path. Other ICT variants (full-range blocks, "unmitigated" gaps) were not tested and are not drawn.

---

## Module 10 — The MOC engine

**10.1 The normalization — KEEP, locked, deterministic (directive item 6).**
Evidence: clock_session §5 — 36,630 session-checkpoints (SPY/QQQ 970 sessions each, IWM 615, SPXW 1,106); every term a
function of bars and quotes closed by t and of the 20 prior sessions, reproducible to the bit.
Rule (0DTE; checkpoints t ∈ {905, 910, …, 950}; for a name, an input x and a checkpoint t, mean₂₀ and sd₂₀ are the mean
and standard deviation of x at that same minute over the 20 sessions strictly before the day, at least 15 present,
else no score that day):

```
x_vol   = ln(1 + volume_{15:00→t})               x_range = ln(1e-6 + (high − low)_{15:00→t} / close_{14:59})
x_move  = (close_{t−1} − close_{14:59}) / close_{14:59}
x_sweep = (call_bought − put_bought) / (call_bought + put_bought)_{15:00→t}
z_i     = clip((x_i − mean₂₀(x_i, t)) / sd₂₀(x_i, t), −4, +4)        σ(z) = 1 / (1 + e^{−z})        u_i = 2σ(z_i) − 1
moc_score (signed, every weight 1.00) = u_move + u_sweep + sign(x_move) · (u_vol + u_range)          ∈ (−4, 4)
moc_mag   (magnitude)                 = [σ(z_vol) + σ(z_range) + σ(z_|move|) + σ(z_|sweep|)] / 4     ∈ (0, 1)
```

|move| and |sweep| are z-scored against their own 20-session minute norms. The closing-cross imbalance (NYSE/Nasdaq
messages from 15:50) enters as the fifth unit-weight term the day a feed exists (PENDING). The sweep proxy on disk
(premium bought when the bar's close is above the NBBO mid) stands in for a per-print side until a tape exists.

**10.2 moc_mag as a closing-volatility gauge — KEEP, exposed (directive item 6).**
Evidence: clock_session §5 — Spearman ρ of moc_mag with |15:49 → close move| +0.213 fit and +0.157 check (N 1,836 /
1,767 at t = 950), +0.14 to +0.25 on every name in both periods, the top quintile moving 17–18 bp against 9–10 bp in the
bottom.
Rule: `moc_mag` is shown as "expect a move" with its quintile; it may enter sizing as an owner-set input
(`MOC_MAG_SIZE_RULE = owner_sets`); it sets no direction.

**10.3 moc_score as a direction, and the power-hour long-premium buy rule — DROPPED (directive item 6).**
Evidence: clock_session §5 — the signed score's ρ with the move is +0.069 fit and −0.010 check, sign hit 48.7% (47.1%
when |score| > 1); the power-hour buy rule with real 0DTE quotes loses 19–26% of premium a trade in check with or
without its gates (full rule −19.1% [−38, +1] held, N 427; the gates move the pooled mean by +$0.7 to +$1.5).
Rule: `moc_score` is written to telemetry; no rule reads its sign. The short-premium use of the gauge (selling the
close's optionality when moc_mag is low) was not tested and is a new hypothesis for the owner's go-ahead, not a rule.

---

## Module 11 — Flow, dark pool, rotation

**11.1 Sweep premium balance, dark-pool signature, whale ≥ $100k, RVOL rotation — DROPPED as gates; telemetry only; PENDING a recorded year.**
Evidence: move_atr_flow Q4/Q6 — no OPRA tape, sweep flag, trade condition or dark-pool print is on disk; the testable
proxy (per-contract minute premium, bought when the close is above the mid) leads the next 5/15/30-minute move with the
opposite sign (SPY −0.29 bps per SD at 5 minutes, t −7.9; −1.04 at 30, t −9.5 fit; −0.26 / −0.93, t −6.5 / −7.2 check)
by a fraction of one spread; "trade-side premium > other side" made the sweep fade worse in fit (SPY −$30.1 [−42.0,
−19.8] on 53 trades) and holds on 3–4% of sweeps.
Rule: the four are recorded fields, drawn where the UI draws them, read by no decision. The prerequisite is a daily
recorder after 16:15 ET, append-only, per name on the Compass universe: every flow alert ≥ $25,000 (so the $100k
threshold itself can be tested), every dark-pool print with its NBBO, the day's `net-prem-ticks`, the day's minute
bars, the stock screener at each scan time, and the per-minute king from the strike book — picked on the first recorded
year, read on the second.

---

## Module 12 — The Weekly / Swing / LEAPS engine: the booleans and the exits

**12.1 B1, B2, B3 — KEEP as a strict boolean gate that describes a setup; no weights, no return claim.**
Evidence: horizons §1–2 — on 23 names (16,721 / 10,131 name-days) B1 fires on 41%, B2 on 5%, B3 on 10%; their same-day
AND fired 14 times in 2022–2024 and 6 in 2025–2026 (N = 20); no boolean ranks forward returns out of sample (AUC
0.49–0.51); the sequenced reading SEQ5_12 (N 105 / 71) with the spec's swing exits returned −1.95% / −1.72% a trade on
the underlying against +0.99% / +1.15% for count-matched random entries (below 200 of 200 and 199 of 200 draws); a
logistic on the booleans has OOS AUC 0.507–0.508 and the wrong sign on B2.
Rule (daily bars, everything known at the close of day t; an entry, if a lane places one, is the next session's open):

```python
B1 = close > EMA21 and close > EMA50 and lastCompletedWeekClose > EMA10w       # the week that ended before t's week
# B2: the impulse on closes over the last 30 sessions — hi = the highest close, lo = the lowest close before it inside
# the window; counts only if hi is >= 2 sessions old and (hi - lo) >= 2 * ATR14
B2 = low <= hi - 0.62 * (hi - lo) and close >= hi - 0.705 * (hi - lo)          # the day's low reaches 0.62, the close holds 0.705
B3 = volume >= 1.5 * mean(volume[t-20:t])                                      # 1.2x in the sequenced reading
B4 = None                                                                      # PENDING: off, labelled (12.2)
setup = B1 and B2 and B3 and (B4 if B4 is not None else True)
# the sequenced reading, declared not tuned: an OTE touch (B2) within the last 5 sessions, B1 today, 1.2x volume today,
# an up close — SEQ5_12; shown as the "within 5 sessions" variant of the same description
# the short side mirrors it (below the EMAs and the weekly; a rally into 0.62-0.705 of a down-impulse; S3 = B3)
```

The gate files a setup; it places no trade on its own and carries no return claim on the card (the Compass rule: a
why-text is a read, never an instruction). N > 500 is not reachable with these booleans on this universe; nothing is
loosened to reach it.

**12.2 B4, the dealer-book gate (a wall within one expected move, the stop beyond it) — PENDING.**
Evidence: horizons §5 — no open interest by strike before 2025-10-15; the one-year sign proxy carried nothing (38
positive-gamma entries, 6 negative; unconditionally negative-gamma days returned slightly more, +2.54% against +1.83% at
20 sessions).
Rule: run with B4 off and say so on the card; it comes in when a year of the strike-level book exists (blockers).

**12.3 The level stop — CHANGED: strictly at the structural level, capped at a maximum underlying distance (the caps the owner's, Phase 3 item 2); never "2.4–4.6%, median 3.45%".**
Evidence: horizons §2 — after an entry 62–70% down an impulse the prior-week low sits a median 8.25% below entry (q25
−12.1%, 10th percentile −17.7%) against a 1 × EM target a median +10.3% away at a 35–40% hit rate; "median 3.45%" is a
fact about 35 vendor trades, and a fixed 3.45% stop is hit on 74–78% of trades. So the cap below binds often: a median
of 8.25% is beyond both caps, and the stop sits at the cap rather than the level on more than half of the entries.
Rule (Weekly, Swing, LEAPS; configurable via environment/settings, the defaults the owner's):

```python
LEVEL_STOP_CAP = {'single_name': 0.060, 'SPY': 0.035, 'QQQ': 0.035, 'IWM': 0.035}   # maximum underlying distance from entry

def level_stop(entry, level, name, side):
    """The stop sits strictly at the structural level — the Near book's put wall (a long) or call wall (a short), or the
    prior-week low / high — unless the level is farther than the cap, in which case it sits at the cap."""
    cap  = LEVEL_STOP_CAP.get(name, LEVEL_STOP_CAP['single_name'])
    dist = min(abs(entry - level) / entry, cap)
    return entry * (1 - dist) if side == 'long' else entry * (1 + dist)
```

The prior-week low and the prior-day low are shown as the levels they are. Neither version is positive.

**12.4 The premium backstop — CHANGED (directive item 4): none below 21 DTE, or widened to the tenor.**
Evidence: horizons §3, exits_sizing test 8 — by Black-Scholes at IV 20% a −20% premium stop on a 7-DTE ATM option is a
0.47% adverse move at entry, 0.20% after one trading day and is tripped by time decay alone by the third day; at
14 DTE 0.67 / 0.48 / 0.08%; three sessions of pure decay take 42% off a 7-DTE premium and 19–20% off a 14-DTE one; in
the model 84–87 of 105 train swing trades left on the premium stop and 7–9 on the level (hold-only −0.3% against −17.4%
with the stop at 21 DTE in train).
Rule:

```python
def premium_backstop(dte, mode):              # mode: owner sets 'none_below_21' or 'widened'
    if mode == 'none_below_21':
        return None if dte < 21 else 0.80     # the level stop alone under 21 DTE; the owner's -20% may stand from 21 DTE
    if mode == 'widened':
        if dte <= 7:   return 0.55            # >= 45% at 7 DTE
        if dte <= 14:  return 0.75            # >= 25% at 14 DTE
        return owner_sets                      # 15-20 DTE and the A/A+ split (-20%/-17%, a 0.07% difference in the underlying at 7 DTE): the owner's
```

LEAPS: the −25% stop stands as the owner wrote it (a 4.3% move at 365 DTE; the audit: +1.7% train / −13.2% check
against hold +15.0% / −4.4%, no EV either way) — KEEP, no claim.

**12.5 The 3-day stall (8–13 DTE) — KEEP as a loss limiter.**
Evidence: horizons §2 — −1.95% → −1.37% train, −1.72% → −0.74% check; 46 / 31 trades out at −3.0% / −3.7% on day 3,
losers and winners alike.

**12.6 Scale-outs, trail lock, RSI(14) exit — KEEP sizing-conditional; the lock and RSI owner sets.**
Evidence: horizons §4 — scale-outs raise the hit rate (11% → 18–28%) without changing the sign; the ladder needs four
contracts (two run the 50% tier only, one has no ladder); the trail lock and the RSI exit stay within ±2 points of
the plain stop.
Rule: the 25% / 50% ladder exists at `size ≥ 4`; at `size = 2` the 50% tier only; at `size = 1` none — a one-lot
Swing position (DTE ≥ 8) runs the owner's trail lock plus 12.3's underlying level stop (Phase 3 item 2; configurable via
environment/settings, default on): the lock arms once the mark reaches `TRAIL_LOCK_ARM` ∈ [1.21, 1.31] × the entry
premium and the exit then rests `TRAIL_LOCK_OUT` ∈ [0.03, 0.05] of the entry under that level (the owner's "+21–31%,
exiting 3–5 points under"; the audit modelled +26% / 4 points: −16.4% / −11.9% at 21 DTE, no evidence either way).
At `size ≥ 2` `TRAIL_LOCK` and `RSI_EXIT` are owner-set booleans with no evidence either way.

**12.7 LEAPS — KEEP the 0.60–0.80 Δ band, the 33/33 ladder and the roll below 60 DTE as written.**
Evidence: horizons §3/§6 — the roll at 90 against 60 DTE is within ±0.3% of spot a cycle (decay 90 → 60 DTE 0.81 =
6.6% of the entry premium; one roll ≈ one spread plus two fees, 3.7–4.4% of a ~$63 mid); the hold +15.0% train rests on
five trades (+0.9% without them, median −8.7%) and is −4.4% check.
Rule: unchanged; the entry gate adds nothing over buying the name, and the card says no more than that.

---

## Module 13 — The contract picker for Weekly / Swing / LEAPS

**13.1 The delta bands — KEEP.**
Evidence: horizons §6 — on five bulk days the bands are liquid on the ETFs (median spread/mid 1.0–1.2% at the weekly
and swing bands) and expensive on single names (5.1–5.3% median, 90th percentile 18–21%); LEAPS at 0.60–0.80 Δ cost
3.7–4.4% to cross.
Rule: Weekly 4–7 DTE at 0.35–0.50 |Δ|; Swing 8–28 DTE at 0.40–0.55; LEAPS 90–365+ DTE at 0.60–0.80; quote hygiene
(2.4) on every pick. The 5% spread/mid guard is a 0DTE figure: at the swing band a single name's median is 5.1–5.3%
and 8.5% at 8–14 DTE, so `SPREAD_MAX_MULTI_DTE = owner_sets` (the ETFs pass 5% at every band; a single name would be
rejected about half the time).

**13.2 The OI ≥ 500 floor — CHANGED: "the nearest expiry with a qualifying contract" (directive item 4).**
Evidence: horizons §6 — OI ≥ 500 leaves a qualifying 0.40–0.55 Δ call in about half of the 8–28 DTE expiries (SPY 59%,
QQQ 34%, AMD 17%, MU 12%, HYG 17%) because daily-listed expiries carry little open interest.
Rule:

```python
def pick_expiry(listings, band, oi_floor=500):
    """Walk the listed expiries inside the horizon's DTE window from the nearest out; the first with a contract in the
    delta band, OI >= oi_floor and clean quotes is the pick; none → Outcome('NO_TRADE', 'no eligible contract')."""
```

**13.3 Tenor preference on single names — CHANGED (directive item 4): prefer 15–28 DTE over 8–14.**
Evidence: horizons §6 — single names at 0.35–0.50 Δ: 8–14 DTE median spread 8.5% (q75 20.7%), 15–28 DTE 4.4% (q75 8.2%).
Rule: for a non-ETF name the Swing walk in 13.2 starts at 15 DTE and falls back to 8–14 only when nothing qualifies
from 15 to 28; for SPY, QQQ, IWM the walk starts at 8.

---

## Module 14 — The earnings gate

**14.1 No Weekly / Swing hold across a report — KEEP as a pure variance / risk block, never EV (directive item 6).**
Evidence: horizons §7 — earnings sessions move the names 2.4–5.5 × a normal session (medians 2.5% AAPL to 12.1% PLTR
against 0.9–3.0%; 1,515 reports 1996 → 2026 on 16 names); the swing entries that crossed a report did not do worse on
the underlying (+0.91% against −3.04% train, N 29 / 76; +1.97% against −2.85% check); the gate removes about a quarter
of the entries; the option-side cost (IV crush, 20% spreads before announcements) is in the literature and not
priceable here.
Rule: a Weekly or Swing entry whose maximum hold (sessions × 7/5 ≤ DTE − 1) crosses a report date on UW's calendar
(date and pre/post-market time) is `NO_TRADE('earnings in the hold')`. LEAPS: `LEAPS_EARNINGS_GATE = owner_sets`
(almost every 63-session hold crosses one). The card words it as what it is — a block on announcement variance — and
never as an expectation.

---

## Module 15 — Cents normalization

**15.1 One price unit at the vendor boundary — KEEP as the rule; the static check is `docs/compass-static-checks/check_cents.py`.**
Evidence: horizons §10 — UW returns prices as numeric strings in dollars (`num()` reads them), ThetaData's bulk files
carry `strike`, `bid`, `ask` as strings in dollars, the house's book is dollars to the cent; UW's OCC option symbols
carry the strike × 1000 (the one place a `/ 1000` belongs).
Rule:
- Exactly one boundary module converts vendor fields to the engine's unit: dollars a share for a premium (the contract
  is × 100 in P&L only), dollars for a strike, a spot and a level; 0.1's `load_price` runs there.
- A schema test asserts unit and scale for every engine input at the boundary: spot, strike, bid, ask, mid, premium,
  target, stop, the expected move (a strike "808.0" is dollars, never 808000 mils; a premium "0.56" is dollars a share).
- A round trip of one known contract — SPY 20261030 808 C at bid 0.55 / ask 0.56 on 2026-10-09 (the bulk file) — through
  the picker, the backstop, the lock, T1, the trail and the P&L, each figure checked to the cent (the harness in
  check_cents.py: entry $56.00 a contract; backstop 0.3808; T1 0.70; lock 0.56; a +25% exit $12.70 net; a backstop exit
  at 0.38 −$19.30 net; fees $1.30 a round trip).
- Any `/100`, `*100`, `/1000`, `*1000` or `Math.round(x*100)` on a price outside that boundary is a finding; percent
  arithmetic (`* 100` into a `…Pct` figure) is not a price unit and is listed apart by the check.

---

## Module 16 — Dead-code quarantine and Helix isolation

**16.1 Dead-code quarantine — KEEP as the rule; the check is `check_dead_code.py`.**
Rule: every removed cap and floor is listed by name — `SWEEP_FLOOR`, `BONUS_CAP`, `CONFIDENCE_CAP` (2.3), the old
premium caps and floors on a contract's price, the delta floors and ceilings the 0.35–0.50 / 0.40–0.55 / 0.60–0.80 bands
replace, any old OI floor value, the min/max-DTE constants the 4–7 / 8–28 / 90–365+ windows replace, and any `weight`,
`score`, `confluence` or `grade` constant still imported (those words are banned on screen by `npm run words:check`) —
and nothing resolves them: a grep for the names and their literal values, `tsc` with the exports deleted where a
tsconfig exists, and the engine's output on a fixed replay day byte-identical before and after except where a removed
cap used to bind, each difference listed.

**16.2 Helix isolation (telemetry only) — KEEP as the rule; the check is `check_helix_isolation.py`.**
Rule: Helix's fields (and any "Physics" / "Nerve" telemetry the spec says has no weights, and module 1.2's
`charm_pressure`, `sign(GEX_book)`, module 10's `moc_score`, module 11's flow fields) are written by the engine and read
by the UI and the logs, never by a decision: (a) the gate's booleans, the picker, the stops, the scale-outs and the
sizing are pure functions of market inputs and config with no telemetry argument; (b) nothing under the decision
modules imports the telemetry module (an import-graph walk); (c) decisions on a fixed replay day are identical with the
telemetry fields null; (d) the telemetry writes to its own sink, never to the alert store, the paper engine's orders or
the Journal's trade records.

---

## The horizons — which rule binds where

| Rule | 0DTE | Weekly 4–7 | Swing 8–28 | LEAPS 90–365+ |
|---|---|---|---|---|
| 0.1 four-decimal load, EPS | yes | yes | yes | yes |
| 1.1 window flags | yes | the EOD clock only | the EOD clock only | the EOD clock only |
| 1.2 charm / regime telemetry | display | display | display | display |
| 1.4 15:58 flat, exemption, may_ride | yes | no (exempt) | no | no |
| 2.1–2.2 sweep and exclusion tags | yes | drawn | drawn | drawn |
| 2.4 quote hygiene, no-eligible-contract | yes (5%) | yes (owner's cap) | yes (owner's cap) | yes (owner's cap) |
| 3.1–3.8 the 0DTE stack | yes | no | no | no |
| 3.9 risk-budget sizing | yes | yes | yes | yes |
| 4.2 daily dollar drawdown cap | yes | yes | yes | yes |
| 5.1–5.4 pricer, forward parity, parity benchmark | r = q = 0 | yes | yes | yes |
| 6.3–6.5 flip A, books, conf | 0DTE book | Near book | Near / Macro | Macro |
| 7.1 M = straddle, 7.3 reachability | yes | the 1 × EM target (12) | the 1 × EM target | — |
| 8.1 ATR block | yes | no | no | no |
| 9.1 geometry drawn | yes | drawn | drawn | drawn |
| 10 MOC gauge | yes | no | no | no |
| 11 flow telemetry | display | display | display | display |
| 12.1–12.2 B1–B4 | no | yes | yes | yes |
| 12.3 level stop at the level, capped 6.0% / 3.5% | no | yes | yes | yes (the owner's weekly-close rule) |
| 12.4 premium backstop | no (3.1 instead) | none, or ≥ 45% at 7 DTE | none < 21 DTE, or ≥ 25% at 14 | −25% as written |
| 12.5 3-day stall | no | no | 8–13 DTE | no |
| 12.6 ladder, trail lock, RSI | no | size ≥ 4 | size ≥ 4; one lot: the trail lock + level stop | 33/33 |
| 12.7 roll < 60 DTE | no | no | no | yes |
| 13.1–13.3 bands, nearest qualifying expiry, 15–28 preference | no | 0.35–0.50 | 0.40–0.55; 15–28 first on names | 0.60–0.80 |
| 14.1 earnings gate | no | yes | yes | owner sets |
| 15–16 checks | yes | yes | yes | yes |

---

## Blockers — what is PENDING and what data clears it

1. **UW's live vol convention (5.5) — CLEARED 2026-10-21.** The GET of `stock/SPY/option-contracts?expiry=2026-11-20`
   plus `stock-state` ran through the audit's `q1c` script: the live IV field stands on ~4% carry (parity gap +0.13 vol
   points), trailField's r = 4.15% repricing is right and is not patched; UW's printed greeks fit r = 0 and are read by
   nothing.
2. **The ThetaData greek benchmark (5.3) and the multi-day option paths (12.4–12.7, 13).** A ThetaData pull outside the
   owner's terminal hours (it is in use 13:00–21:00 UTC): greeks at 7 / 14 / 30 / 180 DTE and the daily option NBBO
   history of the universe. Clears: a backtest, not a Black-Scholes model, of every Weekly / Swing / LEAPS exit.
3. **Strike-level open interest and gamma history (2.2 "between walls", 6.4 walls, 7.3 the true king, 12.2 B4).**
   `spot-exposures/strike?date=` per name per day (≈ 250 calls a name a year on a 3-concurrency plan) or the
   terminal's recorder once it covers a year (it began October 2026, six names). Clears: the wall and king tests, B4.
4. **A second year of book-level greeks (1.2, 6.1–6.2, 6.5).** UW's `greek-exposure` covers one year (250 rows a
   name). Clears: a train/check reading of the regime, the DEX/VEX/CEX watch list, the charm × GEX cell.
5. **The flow tape (11).** No OPRA tape, sweep flag, trade condition or dark-pool print on disk; the daily recorder in
   11.1. Clears: the sweep premium balance, the $100k whale filter, the dark-pool signature, RVOL rotation — after a
   recorded year.
6. **The closing-cross imbalance feed (10.1).** NYSE/Nasdaq imbalance messages from 15:50. Clears: the fifth term.
7. **The official SPXW settlement series (1.4, 7.1).** Clears: the last ~$0.50 of the SPXW ride figures and the
   late-day containment at 15:50.
8. **SPX bar highs and lows (2.1 on SPXW, 3.2).** SPX has one print a minute; SPXW's sweeps and structural stops are
   detected on SPY's bars. Clears: SPXW's own levels.
9. **Pre-market and after-hours bars (1.1).** Not in the data (one bar at 16:00). Clears: the two windows' flags as
   measured rather than assumed.
10. **A Compass trade log and the lane's own win-rate shape (3.5 one-lot shape, 4.2).** Clears: the noise table the
    cap's default (3.0% / $500) is read against, whether the one-lot default stands on the lane's own outcomes, and
    whether a soft gate (6.5) changes realised P&L.
11. **Intra-minute ticks (3.8).** Only one-minute NBBO exists on disk; a tick-watching engine fires earlier within the
    minute. Clears: the realised-overshoot figures as bounds.

## What this specification does not do

It does not pick a direction anywhere; it does not promise a profit from any rule above (every exit rule here is a
smaller loss on a losing universe, measured); it does not invent a number the owner did not give (each is marked
"owner sets"; Phase 3's defaults are the owner's, named as such); it does not patch trailField (the GET in 5.5
confirmed its convention); and it does not reach N > 500 on the swing gate by loosening it.

## Still owner-set

What Phase 3 did not name stays as it was, each with its own section: 0.1 the tick rounding of resting orders (at
the order layer); 1.4 `may_ride` for SPXW; 2.2 the product list; 3.2 `STRUCT_BUFFER_BPS` within [0, 2]; 3.6
`TIME_STOP` (None or minutes); 3.9 `RISK_PER_TRADE_USD` and whether size is capped at the displayed ask_size; 4.2
`DD_MARK` (whether open legs at the bid count toward the day's loss) and whether a lane gets a cap of its own beside the
account's; 6.3 whether Method B is shown as "book zero (B)" or not at all; 6.4 the Macro book's horizon; 7.1 whether a
1-SD band is drawn at all; 10.2 `MOC_MAG_SIZE_RULE`; 12.4 the premium-backstop mode (`none_below_21` or `widened`)
and its 15–20 DTE level; 12.6 the point inside the trail lock's band (+21–31%, 3–5 under) for a one-lot swing, and
`TRAIL_LOCK` / `RSI_EXIT` at `size ≥ 2`; 13.1 `SPREAD_MAX_MULTI_DTE`; 14.1 `LEAPS_EARNINGS_GATE`.
