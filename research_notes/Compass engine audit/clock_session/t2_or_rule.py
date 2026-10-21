"""Test 2: the 10:00 inside-opening-range rule, with real same-day quotes.

Opening range: ORH/ORL = highest high / lowest low of the bars stamped 570..599 (09:30-09:59; the 09:59 bar closes at
10:00). Spot at t = 600 is the close of the bar stamped 599. The session is "inside" when ORL < spot < ORH strictly.
On inside sessions, three ways in (every entry at the ask of the chain row stamped one minute after the signal bar,
since a bar stamped t closes at t+1; nearest strictly out-of-the-money same-day strike against the signal bar's close):
  (i)   first breakout: the first bar (t >= 600) that closes above ORH -> call, below ORL -> put.
  (ii)  sweep-and-return: the first bar whose high exceeds ORH but which closes at or below it -> put (fade the sweep);
        mirror at ORL -> call.
  (iii) post-sweep breakout: the first close beyond a boundary that was already swept-and-returned (the spec's
        "wait for a boundary sweep", then take the breakout).
Context: (iv) first breakout on sessions already outside the range at 10:00.
SPXW uses SPX index prints (one price a minute, so a "sweep" is a print beyond the boundary followed by a later print
back inside; entry one minute after the return print). Signals up to t = 940.
Two ways out: step 4's 50% trailing stop on the bid (sold at the bid the first minute it is at or below half of the
highest bid since entry), and hold to 15:58 (sold at the 15:58 bid; no fee if it is worthless).
Fees $0.65 a contract each way. fit = 2022-2024, oos = 2025-2026.
"""
import sys, numpy as np
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass engine audit/clock_session")
from common import *

T_LAST_ENTRY = 940

def signals(bars, spx):
    c, h, l = bars["close"], bars["high"], bars["low"]
    orh, orl = np.nanmax(h[0:30]), np.nanmin(l[0:30]); spot = c[29]
    inside = orl < spot < orh
    sig = {}
    swept = {1: None, -1: None}  # time the boundary was swept-and-returned
    for i in range(30, T_LAST_ENTRY - 570 + 1):
        t = i + 570
        if not np.isfinite(c[i]): continue
        if "brk" not in sig:
            if c[i] > orh: sig["brk"] = (t, "CALL", c[i], 1)
            elif c[i] < orl: sig["brk"] = (t, "PUT", c[i], -1)
        if spx:
            # a print beyond the boundary, then a later print back inside
            if swept[1] is None and "sw_hi_seen" not in sig and c[i] > orh: sig["sw_hi_seen"] = t
            if swept[1] is None and "sw_hi_seen" in sig and c[i] <= orh and t > sig["sw_hi_seen"]:
                swept[1] = t; sig.setdefault("sweep", (t, "PUT", c[i], -1))
            if swept[-1] is None and "sw_lo_seen" not in sig and c[i] < orl: sig["sw_lo_seen"] = t
            if swept[-1] is None and "sw_lo_seen" in sig and c[i] >= orl and t > sig["sw_lo_seen"]:
                swept[-1] = t; sig.setdefault("sweep", (t, "CALL", c[i], 1))
        else:
            if swept[1] is None and h[i] > orh and c[i] <= orh:
                swept[1] = t; sig.setdefault("sweep", (t, "PUT", c[i], -1))
            if swept[-1] is None and l[i] < orl and c[i] >= orl:
                swept[-1] = t; sig.setdefault("sweep", (t, "CALL", c[i], 1))
        if "post" not in sig:
            if swept[1] is not None and t > swept[1] and c[i] > orh: sig["post"] = (t, "CALL", c[i], 1)
            elif swept[-1] is not None and t > swept[-1] and c[i] < orl: sig["post"] = (t, "PUT", c[i], -1)
    return inside, orh, orl, spot, {k: v for k, v in sig.items() if k in ("brk", "sweep", "post")}

def run(sym):
    usym = "SPX" if sym == "SPXW" else sym
    rows = []
    for date in sessions("chains", sym):
        bars = load_bars(usym, date)
        if bars is None or is_half_day(bars): continue
        inside, orh, orl, spot, sig = signals(bars, sym == "SPXW")
        if not sig: continue
        strikes = chain_strikes(sym, date)
        if strikes is None: continue
        need = []
        for kind, (t, right, px, d) in sig.items():
            if not inside and kind != "brk": continue
            k = nearest_otm(strikes, px, right)
            if k is None: continue
            need.append((kind, t, right, k, px))
        for right in ("CALL", "PUT"):
            ks = {k for _, _, r, k, _ in need if r == right}
            if not ks: continue
            q = quotes(sym, date, ks, right, 600, 958)
            for kind, t, r, k, px in need:
                if r != right: continue
                qq = q.filter(pl.col("strike") == k)
                bid = np.full(NBARS, np.nan); ask = np.full(NBARS, np.nan)
                idx = qq["t"].to_numpy() - 570; bid[idx] = qq["bid"].to_numpy(); ask[idx] = qq["ask"].to_numpy()
                t_in = t + 1
                for exit_name, trail in (("trail50", 0.5), ("hold958", None)):
                    r_ = trade_path(bid, ask, t_in, 958, trail)
                    if r_ is None: continue
                    a0, b1, t_out, pnl = r_
                    rows.append({"sym": sym, "date": date, "period": period(date), "inside": inside, "kind": kind, "right": right,
                                 "t_signal": t, "t_in": t_in, "strike": k, "spot": px, "orh": orh, "orl": orl, "exit": exit_name,
                                 "ask_in": a0, "bid_out": b1, "t_out": t_out, "pnl": pnl, "ret_pct": pnl / (a0 * 100) * 100})
    return pl.DataFrame(rows)

def main():
    df = pl.concat([run(s) for s in ["SPY", "QQQ", "IWM", "SPXW"]]); df.write_parquet(f"{OUT}/t2_rows.parquet")
    lines = []
    for sym in ["SPY", "QQQ", "IWM", "SPXW", "ALL"]:
        for per in ["fit", "oos"]:
            for inside in (True, False):
                for kind in ("brk", "sweep", "post"):
                    for ex in ("trail50", "hold958"):
                        d = df.filter((pl.col("period") == per) & (pl.col("inside") == inside) & (pl.col("kind") == kind) & (pl.col("exit") == ex))
                        if sym != "ALL": d = d.filter(pl.col("sym") == sym)
                        if d.height == 0: continue
                        s = stress(d["pnl"].to_numpy(), d["date"].to_numpy()); sp = stress(d["ret_pct"].to_numpy(), d["date"].to_numpy())
                        lines.append({"sym": sym, "period": per, "inside_at_1000": inside, "kind": kind, "exit": ex, "n": s["n"],
                                      "pnl_mean": s["mean"], "ci_lo": s["ci_lo"], "ci_hi": s["ci_hi"], "wo_best5": s["wo_best5"], "win_rate": s["win_rate"],
                                      "ret_pct_mean": sp["mean"], "ret_pct_ci_lo": sp["ci_lo"], "ret_pct_ci_hi": sp["ci_hi"], "ret_pct_wo_best5": sp["wo_best5"],
                                      "ask_in_mean": float(d["ask_in"].mean()), "t_in_median": float(d["t_in"].median()),
                                      "by_year": " ".join(f"{y}:{v[1]:+.0f}" for y, v in s["by_year"].items())})
    out = pl.DataFrame(lines); out.write_csv(f"{OUT}/t2_summary.csv")
    with pl.Config(tbl_rows=200, tbl_cols=30, tbl_width_chars=260, float_precision=1, fmt_str_lengths=50): print(out)
    ins = df.filter(pl.col("exit") == "hold958").group_by(["sym", "period"]).agg(pl.col("date").n_unique().alias("sessions_with_signal"), pl.col("inside").mean().alias("inside_share"))
    print(ins.sort(["sym", "period"]))

if __name__ == "__main__":
    main()
