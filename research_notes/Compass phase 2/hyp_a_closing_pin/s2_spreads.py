"""Step 2: every credit spread of the grid, sold at 15:00 / 15:30 / 15:45 on every full session, SPXW and SPY.

Per session and entry minute t (900, 930, 945):
  spot S     : SPX's print stamped t; SPY's bar stamped t-1 (closes at t).
  IV, delta  : BSM, r = q = 0, from the contract's NBBO mid at t; a contract with mid - intrinsic <= 0.01 has no IV
               (the same-day skip rule) and is never a short strike.
  short strike rules (OTM only, the call side K > S, the put side K < S):
    d10/d15/d20/d25 : the nearest-the-money OTM strike whose |delta| <= 0.10/0.15/0.20/0.25
    m1.00 / m1.25   : the first strike strictly outside S +- 1.00 x M / 1.25 x M, M = the ATM straddle's mid
                      (call mid + put mid at the strike nearest S) at t
  wings            : SPXW 5, 10, 25 points; SPY 1, 2, 5 points; the long strike must have a finite ask at t.
  fills            : short leg sold at its bid, long leg bought at its ask, both at the row stamped t;
                     credit = bid_short - ask_long, a vertical needs credit >= 0.05; $0.65 a leg to open.
  management (each its own variant, one lot a vertical):
    hold    : to settlement; the vertical is worth intrinsic(short) - intrinsic(long) at the settle; no closing fee.
    tp50    : from t+1 to 15:59, the first minute the cost to close (ask_short - bid_long) <= 0.5 x credit:
              buy the short back at its ask (+$0.65); sell the long at its bid (+$0.65) when that bid > 0, else keep it to
              settlement. Else held to settlement.
    stop2x  : the first minute the cost to close >= 2 x credit, closed the same way. Else held.
  iron condor      : the call and the put vertical of the same rule and wing on the same session, each passing the
                     credit floor, each managed on its own (side = IC; max risk = width x 100 - total credit x 100).
  settlement       : SPXW = the last SPX print at or before 16:00 (a proxy for the official settlement, see the notes);
                     SPY = the 16:00 bar's close (cash-settled at intrinsic, no assignment fee - an assumption).
Writes out/spread_rows.parquet (rebuildable from the raw files by this script; ~1M rows).
"""
import sys, time, numpy as np, polars as pl
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass phase 2/hyp_a_closing_pin")
from common import *

ENTRIES = [900, 930, 945]
DELTAS = {"d10": 0.10, "d15": 0.15, "d20": 0.20, "d25": 0.25}
MULTS = {"m1.00": 1.00, "m1.25": 1.25}
WINGS = {"SPXW": [5.0, 10.0, 25.0], "SPY": [1.0, 2.0, 5.0]}
MIN_CREDIT = 0.05

def intrinsic(K, right, S):
    return max(S - K, 0.0) if right == "CALL" else max(K - S, 0.0)

def manage(chain, Ks, Kl, right, t, credit, settle, mode):
    """Return (exit_t, exit_cost, pnl, long_kept). exit_t = 960 when settled."""
    bs, as_ = chain.bid[(Ks, right)], chain.ask[(Ks, right)]
    bl, al = chain.bid[(Kl, right)], chain.ask[(Kl, right)]
    settle_val = intrinsic(Ks, right, settle) - intrinsic(Kl, right, settle)
    if mode != "hold":
        i0 = t + 1 - T0; i1 = 959 - T0
        cost = as_[i0:i1 + 1] - np.nan_to_num(bl[i0:i1 + 1], nan=0.0)
        if mode == "tp50": hit = np.where(np.isfinite(cost) & (cost <= 0.5 * credit))[0]
        else: hit = np.where(np.isfinite(cost) & (cost >= 2.0 * credit))[0]
        if hit.size:
            i = hit[0] + i0; m = i + T0
            a_s = as_[i]; b_l = bl[i] if np.isfinite(bl[i]) else 0.0
            if b_l > 0:
                return m, a_s - b_l, (credit - (a_s - b_l)) * 100 - 4 * FEE, False
            # the long leg is kept to settlement (its bid is 0)
            long_settle = intrinsic(Kl, right, settle)
            return m, a_s, (credit - a_s + long_settle) * 100 - 3 * FEE, True
    return 960, settle_val, (credit - settle_val) * 100 - 2 * FEE, False

def session_rows(sym, date):
    usym = "SPX" if sym == "SPXW" else sym
    bars = load_bars(usym, date)
    if bars is None or is_half_day(bars): return []
    settle = settlement(sym, bars)
    if settle is None: return []
    chain = Chain(sym, date)
    rows = []
    for t in ENTRIES:
        S = spot_at(sym, bars, t)
        if S is None: continue
        T = years_to_close(t)
        # IV / delta of every OTM contract at t
        info = {}
        for right in ("CALL", "PUT"):
            for K in chain.strikes:
                if (right == "CALL" and K <= S) or (right == "PUT" and K >= S): continue
                b, a = chain.quote(K, right, t)
                if not (np.isfinite(b) and np.isfinite(a)) or a <= 0: continue
                mid = 0.5 * (b + a)
                iv = implied_vol(mid, S, K, T, right)
                info[(K, right)] = (b, a, mid, iv, bs_delta(S, K, iv, T, right) if iv else None)
        # the ATM straddle
        K_atm = float(chain.strikes[np.argmin(np.abs(chain.strikes - S))])
        bc, ac = chain.quote(K_atm, "CALL", t); bp, ap = chain.quote(K_atm, "PUT", t)
        M = 0.5 * (bc + ac) + 0.5 * (bp + ap) if all(np.isfinite([bc, ac, bp, ap])) else None
        for right in ("CALL", "PUT"):
            otm = sorted([K for (K, r) in info if r == right], reverse=(right == "PUT"))  # nearest the money first
            for rule in list(DELTAS) + list(MULTS):
                Ks = None
                if rule in DELTAS:
                    for K in otm:
                        d = info[(K, right)][4]
                        if d is not None and abs(d) <= DELTAS[rule]: Ks = K; break
                else:
                    if M is None: continue
                    bound = S + MULTS[rule] * M if right == "CALL" else S - MULTS[rule] * M
                    for K in otm:
                        if (right == "CALL" and K > bound) or (right == "PUT" and K < bound): Ks = K; break
                if Ks is None: continue
                b_s, a_s, mid_s, iv_s, d_s = info[(Ks, right)]
                for w in WINGS[sym]:
                    Kl = Ks + w if right == "CALL" else Ks - w
                    if (Kl, right) not in chain.ask: continue
                    b_l, a_l = chain.quote(Kl, right, t)
                    if not np.isfinite(a_l): continue
                    credit = round(b_s - a_l, 4)
                    if credit < MIN_CREDIT: continue
                    for mode in ("hold", "tp50", "stop2x"):
                        ex_t, ex_cost, pnl, kept = manage(chain, Ks, Kl, right, t, credit, settle, mode)
                        rows.append({"sym": sym, "date": date, "period": period(date), "t": t, "side": right, "rule": rule, "wing": w,
                                     "Ks": Ks, "Kl": Kl, "spot": S, "M": M, "bid_s": b_s, "ask_l": a_l, "credit": credit,
                                     "delta_s": abs(d_s) if d_s is not None else None, "iv_s": iv_s, "settle": settle,
                                     "mgmt": mode, "exit_t": ex_t, "exit_cost": ex_cost, "pnl": pnl, "long_kept": kept,
                                     "max_risk": (w - credit) * 100})
    # iron condors: pair the call and the put vertical of the same (t, rule, wing, mgmt)
    byk = {}
    for r in rows: byk.setdefault((r["t"], r["rule"], r["wing"], r["mgmt"]), {})[r["side"]] = r
    ics = []
    for (t, rule, w, mode), d in byk.items():
        if "CALL" in d and "PUT" in d:
            c, p = d["CALL"], d["PUT"]
            ics.append({"sym": sym, "date": date, "period": period(date), "t": t, "side": "IC", "rule": rule, "wing": w,
                        "Ks": c["Ks"], "Kl": c["Kl"], "spot": c["spot"], "M": c["M"], "bid_s": c["bid_s"] + p["bid_s"], "ask_l": c["ask_l"] + p["ask_l"],
                        "credit": c["credit"] + p["credit"], "delta_s": None, "iv_s": None, "settle": settle, "mgmt": mode,
                        "exit_t": max(c["exit_t"], p["exit_t"]), "exit_cost": c["exit_cost"] + p["exit_cost"], "pnl": c["pnl"] + p["pnl"],
                        "long_kept": c["long_kept"] or p["long_kept"], "max_risk": w * 100 - (c["credit"] + p["credit"]) * 100})
    return rows + ics

SCHEMA = {"sym": pl.Utf8, "date": pl.Utf8, "period": pl.Utf8, "t": pl.Int32, "side": pl.Utf8, "rule": pl.Utf8, "wing": pl.Float64,
          "Ks": pl.Float64, "Kl": pl.Float64, "spot": pl.Float64, "M": pl.Float64, "bid_s": pl.Float64, "ask_l": pl.Float64, "credit": pl.Float64,
          "delta_s": pl.Float64, "iv_s": pl.Float64, "settle": pl.Float64, "mgmt": pl.Utf8, "exit_t": pl.Int32, "exit_cost": pl.Float64,
          "pnl": pl.Float64, "long_kept": pl.Boolean, "max_risk": pl.Float64}

if __name__ == "__main__":
    syms = sys.argv[1:] or ["SPXW", "SPY"]
    for sym in syms:
        t0 = time.time(); parts = []; buf = []; n_sess = 0
        for n, date in enumerate(sessions("chains", sym)):
            r = session_rows(sym, date)
            if r: n_sess += 1; buf.extend(r)
            if len(buf) > 200000:
                parts.append(pl.DataFrame(buf, schema=SCHEMA)); buf = []
            if n % 100 == 0: print(sym, n, date, f"{time.time() - t0:.0f}s rows so far {sum(p.height for p in parts) + len(buf)}", flush=True)
        if buf: parts.append(pl.DataFrame(buf, schema=SCHEMA))
        df = pl.concat(parts); df.write_parquet(f"{OUT}/spread_rows_{sym}.parquet")
        print(sym, "sessions", n_sess, "rows", df.height, f"{time.time() - t0:.0f}s", flush=True)
