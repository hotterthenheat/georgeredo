"""The position engine: one multi-leg option position managed minute by minute under a policy, on one session's chain
(lifecycle protocol §2, §5). Compiled with numba; a pure-Python wrapper builds the inputs and names the outputs.

A STRUCTURE is up to four legs with integer ratios (+1 long, -1 short). A UNIT is one of each leg at its ratio. Every
price is per share; every dollar figure is per unit x 100.

  open cost (a buy of one unit)      sum over legs: ratio > 0 -> ask * ratio, ratio < 0 -> -bid * |ratio|, + slip per contract
  liquidation (a sale of one unit)   sum over legs: ratio > 0 -> bid * ratio, ratio < 0 -> -ask * |ratio|, - slip per contract
  mark                               sum of ratio * mid
A debit structure costs > 0 to open; a credit structure < 0 (the credit is -cost).

Policy decisions read the MARK (mid) by default (TRIGGER_ON = 0) or the liquidation value (1); fills are always at the
bid or ask. Units added after the entry are separate LOTS; an exit sells a fraction of the units held, pro rata across
lots, and is tagged with a REASON so every partial's and the runner's contribution is measured.

Order of evaluation each minute after the entry: expiry or cutoff, thesis, stop, short-premium rules, time exit,
targets and partials, trailing and runner exits, warnings, then the additions (scale-in tranches, adds, double-down).

Expiry, if a position reaches the last minute open: cash-settled legs pay intrinsic at the close value; physically
settled legs in the money by $0.01 or more at the close are exercised or assigned and the resulting shares are sold at
the next session's open (NEXT_OPEN; the close when unknown). Fees are charged on exercise and assignment.
"""
from __future__ import annotations
import numpy as np
from numba import njit

# ---- policy parameter layout ------------------------------------------------------------------------------------
P_NAMES = ['STOP', 'TARGET', 'TIME_EXIT', 'CUTOFF', 'P1_FRAC', 'P1_AT', 'P2_FRAC', 'P2_AT', 'TRAIL_ARM', 'TRAIL_GIVE',
           'RUNNER_STRUCT', 'THESIS', 'ADD_K', 'ADD_MAX', 'DD_AT', 'DD_MAX', 'SCALE', 'WARN_MASK', 'WARN_ACTION',
           'CREDIT_TP', 'CREDIT_STOP', 'STRIKE_TOUCH', 'LEG_K', 'LEG_TRAIL', 'TRIGGER_ON', 'SLIP', 'FEE', 'QUOTE_WAIT',
           'RUNNER_TIME', 'LAT']
P = {n: i for i, n in enumerate(P_NAMES)}
NP = len(P_NAMES)
DEFAULT = dict(STOP=-1.0, TARGET=-1.0, TIME_EXIT=-1.0, CUTOFF=380.0, P1_FRAC=0.0, P1_AT=-1.0, P2_FRAC=0.0, P2_AT=-1.0,
               TRAIL_ARM=-1.0, TRAIL_GIVE=0.25, RUNNER_STRUCT=0.0, THESIS=0.0, ADD_K=-1.0, ADD_MAX=0.0, DD_AT=-1.0,
               DD_MAX=0.0, SCALE=0.0, WARN_MASK=0.0, WARN_ACTION=0.0, CREDIT_TP=-1.0, CREDIT_STOP=-1.0,
               STRIKE_TOUCH=0.0, LEG_K=-1.0, LEG_TRAIL=-1.0, TRIGGER_ON=0.0, SLIP=0.0, FEE=0.70, QUOTE_WAIT=2.0,
               RUNNER_TIME=-1.0, LAT=0.0)

def params(**kw) -> np.ndarray:
    d = {**DEFAULT, **kw}
    bad = set(d) - set(P_NAMES)
    if bad: raise KeyError(bad)
    return np.array([float(d[n]) for n in P_NAMES])

# exit reasons
R_NAMES = ['partial1', 'partial2', 'runner', 'stop', 'target', 'time', 'cutoff', 'thesis', 'warning', 'leg', 'expiry',
           'credit_tp', 'credit_stop', 'strike_touch']
R = {n: i for i, n in enumerate(R_NAMES)}
NR = len(R_NAMES)
# lot tags
LOT_INITIAL, LOT_ADD, LOT_DD, LOT_SCALE = 0, 1, 2, 3
# output layout
O_NAMES = ['filled', 'entry_m', 'exit_m', 'pnl', 'fees', 'cost0', 'credit', 'capital_peak', 'units_peak',
           'pnl_lot_initial', 'pnl_lot_add', 'pnl_lot_dd', 'pnl_lot_scale', 'n_adds', 'n_dd', 'n_scale',
           'final_reason', 'hold_min', 'entry_spread', 'warned'] + [f'pnl_{r}' for r in R_NAMES]
O = {n: i for i, n in enumerate(O_NAMES)}
NO = len(O_NAMES)

MAXLOT = 8

@njit(cache=True)
def _leg_ok(bid, ask, c, m):
    b = bid[c, m]; a = ask[c, m]
    return (b == b) and (a == a) and a > 0.0 and a >= b

@njit(cache=True)
def _quotes_ok(bid, ask, legs, nleg, m):
    for i in range(nleg):
        if not _leg_ok(bid, ask, legs[i], m): return False
    return True

@njit(cache=True)
def _open_cost(bid, ask, legs, ratio, nleg, m, slip):
    s = 0.0
    for i in range(nleg):
        c = legs[i]; r = ratio[i]
        if r > 0: s += (ask[c, m] + slip) * r
        else: s += (bid[c, m] - slip) * r          # r < 0: receives the bid
    return s * 100.0

@njit(cache=True)
def _liq(bid, ask, legs, ratio, nleg, m, slip):
    s = 0.0
    for i in range(nleg):
        c = legs[i]; r = ratio[i]
        if r > 0: s += max(bid[c, m] - slip, 0.0) * r
        else: s += (ask[c, m] + slip) * r
    return s * 100.0

@njit(cache=True)
def _mark(bid, ask, legs, ratio, nleg, m):
    s = 0.0
    for i in range(nleg):
        c = legs[i]
        s += 0.5 * (bid[c, m] + ask[c, m]) * ratio[i]
    return s * 100.0

@njit(cache=True)
def _contracts(ratio, nleg):
    s = 0.0
    for i in range(nleg): s += abs(ratio[i])
    return s

@njit(cache=True)
def _settle_leg(strike, is_call, r, close, next_open, cash, fee):
    """Value per unit of one leg reaching expiry (x100), and the exercise/assignment fee per unit."""
    itm = (close - strike) if is_call else (strike - close)
    if itm < 0.01: return 0.0, 0.0
    if cash: v = itm
    else:
        px = next_open if next_open == next_open else close
        v = (px - strike) if is_call else (strike - px)
    return v * r * 100.0, fee * abs(r)

@njit(cache=True)
def simulate(bid, ask, strike, is_call, spot, ema5, rsi, atr5, ativ, n_min,
             legs, ratio, nleg, entry_m, direction, inv, entry_px_override, next_open, cash_settle, short_strike, p):
    out = np.zeros(NO)
    legs = legs.copy(); ratio = ratio.copy(); p = p.copy()
    slip = p[25]; fee = p[26]; wait = int(p[27]); cutoff = int(p[3]); lat = int(p[29])
    last = n_min - 1
    # ---- entry fill (market at entry_m, or a limit price passed in) -------------------------------------------------
    m0 = -1
    for k in range(wait + 1):
        mm = entry_m + k
        if mm > last - 1: break
        if _quotes_ok(bid, ask, legs, nleg, mm):
            m0 = mm; break
    if m0 < 0: return out
    nc = _contracts(ratio, nleg)
    cost_unit = _open_cost(bid, ask, legs, ratio, nleg, m0, slip)
    if entry_px_override == entry_px_override: cost_unit = entry_px_override * 100.0
    credit = cost_unit < 0.0
    first = 1.0 / 3.0 if p[16] == 1.0 else 1.0
    # lots
    lot_units = np.zeros(MAXLOT); lot_cost = np.zeros(MAXLOT); lot_tag = np.zeros(MAXLOT, np.int64); lot_real = np.zeros(MAXLOT)
    lot_units0 = np.zeros(MAXLOT)
    nlot = 1
    lot_units[0] = first; lot_units0[0] = first; lot_cost[0] = cost_unit * first + fee * nc * first; lot_tag[0] = LOT_INITIAL
    units = first
    basis = lot_cost[0]                      # cash paid for the open units (fees included), reduced pro rata on exits
    fees_total = fee * nc * first
    cap = max(cost_unit, 0.0) * first        # capital at risk; credit structures below
    width_risk = 0.0
    if credit:
        # risk per unit of a credit structure: the defined-risk width for a spread, the strike for a cash-secured put
        if nleg == 1: width_risk = strike[legs[0]] * 100.0
        else:
            w = 0.0
            for i in range(nleg):
                for j in range(nleg):
                    if ratio[i] < 0 and ratio[j] > 0 and is_call[legs[i]] == is_call[legs[j]]:
                        w = max(w, abs(strike[legs[i]] - strike[legs[j]]))
            width_risk = w * 100.0
        cap = width_risk * first
    cap_peak = cap; units_peak = units
    reason_pnl = np.zeros(NR)
    n_adds = 0; n_dd = 0; n_scale = 0
    spot0 = spot[m0]; atr0 = atr5[m0]; iv0 = ativ[m0]
    sp0 = 0.0
    leg_cost0 = np.zeros(4)
    for i in range(nleg):
        c = legs[i]; sp0 += (ask[c, m0] - bid[c, m0]) * abs(ratio[i])
        leg_cost0[i] = ((ask[c, m0] + slip) if ratio[i] > 0 else (bid[c, m0] - slip)) * ratio[i]
    p1_done = False; p2_done = False; thesis_reduced = False; warned = False
    peak = -1e18; trail_armed = False; runner = False
    final_reason = -1; exit_m = -1
    leg_units = np.ones(4) * units               # leg mode (straddle/strangle): units per leg
    leg_mode = p[22] >= 0.0 and nleg == 2
    leg_peak = np.zeros(4) - 1e18
    leg_closed = np.zeros(4, np.bool_)
    scale2_done = p[16] != 1.0; scale3_done = p[16] != 1.0
    sign = 1.0 if direction >= 0 else -1.0

    m = m0
    while True:
        m += 1
        if units <= 1e-12: break
        if m > last:
            break
        q = _quotes_ok(bid, ask, legs, nleg, m)
        # ---- expiry and cutoff -------------------------------------------------------------------------------------
        if m == last or (cutoff >= 0 and m >= cutoff):
            if cutoff >= 0 and m >= cutoff and m < last and q:
                x = _liq(bid, ask, legs, ratio, nleg, m, slip) - fee * nc
                pr = units * x
                reason_pnl[6] += pr - basis
                for l in range(nlot): lot_real[l] += lot_units[l] * x
                fees_total += fee * nc * units
                basis = 0.0; units = 0.0; final_reason = 6; exit_m = m
                break
            if m == last:
                v = 0.0; ef = 0.0
                for i in range(nleg):
                    c = legs[i]
                    uu = leg_units[i] if leg_mode else units
                    a, b = _settle_leg(strike[c], is_call[c], ratio[i], spot[last], next_open, cash_settle, fee)
                    v += a * uu; ef += b * uu
                pr = v - ef
                fees_total += ef
                reason_pnl[10] += pr - basis
                for l in range(nlot): lot_real[l] += (lot_units[l] / units) * pr if units > 0 else 0.0
                basis = 0.0; units = 0.0; final_reason = 10; exit_m = m
                break
            continue
        if not q: continue
        mk = _mark(bid, ask, legs, ratio, nleg, m) if p[24] == 0.0 else _liq(bid, ask, legs, ratio, nleg, m, slip)
        avg_cost = basis / units                         # per unit, fees included
        g = 0.0; cr = 0.0; buyback = 0.0
        # gain fraction on the debit, or for credits the buy-back as a multiple of the credit
        if not credit:
            g = (mk - avg_cost) / avg_cost if avg_cost > 0 else 0.0
        else:
            cr = -avg_cost                               # credit per unit, net of fees
            buyback = -mk                                # cost to close per unit
        exit_frac = 0.0; reason = -1
        s = spot[m]
        mover = (s - spot0) * sign                       # favourable underlying move
        # ---- thesis ------------------------------------------------------------------------------------------------
        th = int(p[11])
        if th > 0 and inv == inv:
            crossed = (s < inv) if sign > 0 else (s > inv)
            if th == 2 and m % 5 != 0: crossed = False
            if crossed:
                if th == 3:
                    if not thesis_reduced:
                        exit_frac = 0.5; reason = 7; thesis_reduced = True
                else:
                    exit_frac = 1.0; reason = 7
        # ---- stop (debit) --------------------------------------------------------------------------------------------
        if reason < 0 and not credit and p[0] > 0 and g <= -p[0]:
            exit_frac = 1.0; reason = 3
        # ---- short premium ---------------------------------------------------------------------------------------------
        if reason < 0 and credit:
            if p[20] > 0 and buyback >= p[20] * cr:
                exit_frac = 1.0; reason = 12
            elif p[21] > 0 and short_strike == short_strike and s <= short_strike:
                exit_frac = 1.0; reason = 13
            elif p[19] > 0 and buyback <= (1.0 - p[19]) * cr:
                exit_frac = 1.0; reason = 11
        # ---- time exit ----------------------------------------------------------------------------------------------
        if reason < 0 and p[2] > 0 and (m - m0) >= p[2] and not runner:
            exit_frac = 1.0; reason = 5
        if reason < 0 and runner and p[28] > 0 and (m - m0) >= p[28]:
            exit_frac = 1.0; reason = 2
        # ---- targets and partials (debit) ------------------------------------------------------------------------------
        if reason < 0 and not credit and not leg_mode:
            if p[4] > 0 and not p1_done and p[5] > 0 and g >= p[5]:
                exit_frac = p[4]; reason = 0; p1_done = True; runner = True
            elif p[6] > 0 and p1_done and not p2_done and p[7] > 0 and g >= p[7]:
                # second partial: a fraction of the ORIGINAL position, expressed against the units now held
                exit_frac = min(p[6] / max(1.0 - p[4], 1e-9), 1.0); reason = 1; p2_done = True
            elif p[1] > 0 and g >= p[1] and not runner:
                exit_frac = 1.0; reason = 4
        # ---- trailing and runner exits -----------------------------------------------------------------------------------
        if not credit and not leg_mode:
            if mk > peak: peak = mk
            if p[8] >= 0 and not trail_armed and g >= p[8]: trail_armed = True
            if reason < 0 and trail_armed and peak > 0 and mk <= peak * (1.0 - p[9]):
                exit_frac = 1.0; reason = 2
            if reason < 0 and runner and p[10] == 1.0 and m % 5 == 0 and ema5[m] == ema5[m]:
                if (s - ema5[m]) * sign < 0:
                    exit_frac = 1.0; reason = 2
        # ---- warnings --------------------------------------------------------------------------------------------------
        wm = int(p[17])
        if reason < 0 and wm > 0 and not warned:
            w = False
            if (wm & 1) and rsi[m] == rsi[m] and (rsi[m] - 50.0) * sign < 0: w = True
            if (wm & 2) and iv0 == iv0 and ativ[m] == ativ[m] and ativ[m] <= 0.9 * iv0: w = True
            if (wm & 4):
                spm = 0.0
                for i in range(nleg):
                    c = legs[i]; spm += (ask[c, m] - bid[c, m]) * abs(ratio[i])
                if sp0 > 0 and spm >= 2.0 * sp0: w = True
            if (wm & 8) and atr0 == atr0 and mover <= -atr0: w = True
            if w:
                warned = True
                if p[18] == 1.0: exit_frac = 0.5; reason = 8
                elif p[18] == 2.0: exit_frac = 1.0; reason = 8
        # ---- straddle / strangle legs ------------------------------------------------------------------------------------
        if leg_mode and reason < 0:
            em = cost_unit / 100.0                         # the entry debit per share: the expected move it prices
            if p[1] > 0:
                if (mk - avg_cost) / avg_cost >= p[1]: exit_frac = 1.0; reason = 4
            if reason < 0 and not (leg_closed[0] or leg_closed[1]) and abs(s - spot0) >= p[22] * em:
                # close the losing leg: the put when price rose, the call when it fell
                lose = -1
                for i in range(nleg):
                    c = legs[i]
                    if (s > spot0 and not is_call[c]) or (s < spot0 and is_call[c]): lose = i
                if lose >= 0:
                    c = legs[lose]
                    x = max(bid[c, m] - slip, 0.0) * ratio[lose] * 100.0 - fee * abs(ratio[lose])
                    pr = leg_units[lose] * x
                    tot = leg_cost0[0] + leg_cost0[1]
                    share = leg_cost0[lose] / tot if tot > 0 else 0.5   # the closed leg carries its entry share of the basis
                    reason_pnl[9] += pr - basis * share
                    for l in range(nlot): lot_real[l] += lot_units[l] / units * pr
                    fees_total += fee * abs(ratio[lose]) * leg_units[lose]
                    basis = basis * (1.0 - share)
                    leg_units[lose] = 0.0; leg_closed[lose] = True
                    # the remaining position is now one leg: continue with a one-leg view
                    keep = 1 - lose
                    legs[0] = legs[keep]; ratio[0] = ratio[keep]; leg_units[0] = leg_units[keep]; leg_cost0[0] = leg_cost0[keep]; nleg = 1; leg_mode = False
                    nc = _contracts(ratio, nleg)
                    peak = -1e18; trail_armed = p[23] > 0; p[9] = p[23] if p[23] > 0 else p[9]
                    runner = True
                    continue
        # ---- apply an exit -------------------------------------------------------------------------------------------------
        if reason >= 0 and exit_frac > 0:
            exit_frac = min(exit_frac, 1.0)
            mf = m + lat if (m + lat < last and _quotes_ok(bid, ask, legs, nleg, m + lat)) else m
            x = _liq(bid, ask, legs, ratio, nleg, mf, slip) - fee * nc
            sold = units * exit_frac
            pr = sold * x
            reason_pnl[reason] += pr - basis * exit_frac
            for l in range(nlot):
                lot_real[l] += lot_units[l] * exit_frac * x
                lot_units[l] *= (1.0 - exit_frac)
            fees_total += fee * nc * sold
            basis *= (1.0 - exit_frac); units -= sold
            if units <= 1e-9:
                units = 0.0; final_reason = reason; exit_m = m
                break
            continue
        # ---- additions -----------------------------------------------------------------------------------------------------
        add = 0.0; tag = -1
        if not scale2_done and (m - m0) >= 5:
            scale2_done = True
            ok = True
            if inv == inv: ok = not ((s < inv) if sign > 0 else (s > inv))
            if ok: add = 1.0 / 3.0; tag = LOT_SCALE
        if add == 0.0 and not scale3_done and m % 5 == 0 and m > m0:
            if (m - m0) > 30: scale3_done = True
            elif mover > 0:
                scale3_done = True; add = 1.0 / 3.0; tag = LOT_SCALE
        if add == 0.0 and p[12] > 0 and n_adds < int(p[13]) and atr0 == atr0 and atr0 > 0 and not credit:
            if mover >= p[12] * atr0 * (n_adds + 1) and g > 0:
                add = 1.0; tag = LOT_ADD
        if add == 0.0 and p[14] > 0 and n_dd < int(p[15]) and not credit and g <= -p[14]:
            ok = True
            if inv == inv: ok = not ((s < inv) if sign > 0 else (s > inv))
            if ok: add = units; tag = LOT_DD
        if add > 0 and nlot < MAXLOT:
            c1 = _open_cost(bid, ask, legs, ratio, nleg, m, slip)
            lot_units[nlot] = add; lot_units0[nlot] = add; lot_cost[nlot] = c1 * add + fee * nc * add; lot_tag[nlot] = tag
            basis += lot_cost[nlot]; units += add; fees_total += fee * nc * add
            nlot += 1
            if tag == LOT_ADD: n_adds += 1
            elif tag == LOT_DD: n_dd += 1
            else: n_scale += 1
            cap = basis if not credit else width_risk * units
            if cap > cap_peak: cap_peak = cap
            if units > units_peak: units_peak = units
            if not credit: leg_units[:] = units
    # ---- outputs ---------------------------------------------------------------------------------------------------------
    pnl = 0.0
    lp = np.zeros(4)
    for l in range(nlot):
        x = lot_real[l] - lot_cost[l]
        pnl += x
        lp[lot_tag[l]] += x
    out[0] = 1.0; out[1] = m0; out[2] = exit_m; out[3] = pnl; out[4] = fees_total; out[5] = cost_unit
    out[6] = 1.0 if credit else 0.0; out[7] = cap_peak; out[8] = units_peak
    out[9] = lp[0]; out[10] = lp[1]; out[11] = lp[2]; out[12] = lp[3]
    out[13] = n_adds; out[14] = n_dd; out[15] = n_scale; out[16] = final_reason; out[17] = exit_m - m0
    out[18] = sp0 * 100.0; out[19] = 1.0 if warned else 0.0
    for r in range(NR): out[20 + r] = reason_pnl[r]
    return out

def run_one(cd, aux: dict, legs, ratio, nleg: int, entry_m: int, direction: int, inv: float, pvec: np.ndarray,
            next_open: float = np.nan, cash: bool | None = None, short_strike: float = np.nan, override: float = np.nan) -> dict:
    """Python entry point: names the kernel's outputs."""
    if cash is None: cash = cd.root.startswith('SPX')
    o = simulate(cd.bid, cd.ask, cd.strike, cd.is_call, cd.spot, aux['ema5'], aux['rsi'], aux['atr5'], aux['ativ'], cd.n_min,
                 np.asarray(legs, np.int64), np.asarray(ratio, np.float64), int(nleg), int(entry_m), int(direction), float(inv),
                 float(override), float(next_open), bool(cash), float(short_strike), pvec)
    return dict(zip(O_NAMES, o.tolist()))

@njit(cache=True)
def run_policies(bid, ask, strike, is_call, spot, ema5, rsi, atr5, ativ, n_min, legs, ratio, nleg, entry_m, direction, inv,
                 override, next_open, cash, short_strike, PM, pidx):
    """One position under several policies (rows of PM selected by pidx): outputs [len(pidx), NO]."""
    out = np.zeros((pidx.size, NO))
    for k in range(pidx.size):
        out[k] = simulate(bid, ask, strike, is_call, spot, ema5, rsi, atr5, ativ, n_min, legs, ratio, nleg, entry_m,
                          direction, inv, override, next_open, cash, short_strike, PM[pidx[k]])
    return out

@njit(cache=True)
def hindsight(bid, ask, legs, ratio, nleg, m0, end_m, slip):
    """Result A for one structure bought (or sold) at the fill minute m0: the open cost, then over (m0, end_m] the best and
    worst liquidation value and their minutes, the best mark, and the liquidation value at end_m (NaN when unquoted).
    Retrospective: no rule could know these minutes in advance."""
    res = np.full(8, np.nan)
    if not _quotes_ok(bid, ask, legs, nleg, m0): return res
    c0 = _open_cost(bid, ask, legs, ratio, nleg, m0, slip)
    best = -1e18; worst = 1e18; tb = -1; tw = -1; bm = -1e18; last = np.nan
    for m in range(m0 + 1, end_m + 1):
        if not _quotes_ok(bid, ask, legs, nleg, m): continue
        v = _liq(bid, ask, legs, ratio, nleg, m, slip)
        if v > best: best = v; tb = m
        if v < worst: worst = v; tw = m
        mk = _mark(bid, ask, legs, ratio, nleg, m)
        if mk > bm: bm = mk
        if m == end_m: last = v
    res[0] = c0; res[1] = best; res[2] = tb; res[3] = worst; res[4] = tw; res[5] = bm; res[6] = last
    res[7] = _mark(bid, ask, legs, ratio, nleg, m0)
    return res
