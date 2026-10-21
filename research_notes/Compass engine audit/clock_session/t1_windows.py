"""Test 1: do the spec's session-window biases (chase / fade / pin / neutral, reversal-prone) hold?

Data: 1-minute underlying bars for SPY and IWM 2017-01-03 -> 2026-10-09 and QQQ 2012-06-01 -> 2026-10-09 (the vendor's
SPY/IWM files before 2017 are empty); every session with a full 09:30-15:59 bar set; half days dropped.
Per window and session we measure, on the bars stamped inside the window [lo, hi):
  cont   : first-third continuation. m1 = close at the end of the window's first third minus the close just before
           the window; m2 = close at the window's end minus close at the end of the first third. cont = 1 when
           sign(m1) == sign(m2) (both non-zero). Null = 0.5.
  ac5    : lag-1 autocorrelation of non-overlapping 5-minute log returns inside the window (pooled by period).
  eff    : efficiency ratio |net move| / sum|1-minute moves| (pin -> low).
  revprev: 1 when the window's net move has the opposite sign of the previous window's net move. Null = 0.5.
  brk    : opening-range breakouts (first 1-minute close beyond ORH/ORL, t >= 600) that START in the window:
           share whose 15:58 close is still beyond the level in the breakout direction, and the mean move from
           the breakout close to 15:58 in the breakout direction (bp).
Labels are decided on 2022-2024 and read on 2025-2026; 2012-2021 is shown as context.
Decision rule (fixed before reading): chase if cont's 95% day-bootstrap interval lies above 0.5 AND ac5 > 0;
fade if the interval lies below 0.5 AND ac5 < 0; otherwise neutral. "pin" is judged by eff being below the
session's median window eff with its interval; "reversal-prone" by revprev's interval above 0.5.
"""
import sys, json, numpy as np
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass engine audit/clock_session")
from common import *

WINDOWS = [("opening_drive", 570, 595, "chase", 1.0, False), ("morning_reversal", 595, 635, "fade", 1.1, True),
           ("mid_morning", 635, 720, "pin", 1.25, False), ("lunch", 720, 795, "neutral", 1.5, False),
           ("pre_power", 795, 825, "neutral", 1.75, True), ("dealer_hour", 825, 900, "chase", 2.4, False),
           ("power_hour", 900, 930, "chase", 3.0, False), ("settlement", 930, 960, "pin", 3.5, True)]

def session_rows(sym, date, bars):
    c, h, l, v = bars["close"], bars["high"], bars["low"], bars["volume"]
    o = bars["open"]
    rows = []; prev_net = None
    orh, orl = np.nanmax(h[0:30]), np.nanmin(l[0:30])  # bars stamped 570..599
    # first breakout at t >= 600 (bar close beyond the range)
    brk_t = brk_dir = None; brk_level = None
    for i in range(30, 389):  # t=600..958
        if c[i] > orh: brk_t, brk_dir, brk_level = i + 570, 1, orh; break
        if c[i] < orl: brk_t, brk_dir, brk_level = i + 570, -1, orl; break
    c958 = c[958 - 570]
    for name, lo, hi, bias, mult, rev in WINDOWS:
        i0, i1 = lo - 570, hi - 570
        base = o[i0] if i0 == 0 else c[i0 - 1]
        third = i0 + max(1, (i1 - i0) // 3)
        m1 = c[third - 1] - base; m2 = c[i1 - 1] - c[third - 1]
        cont = np.nan if (m1 == 0 or m2 == 0 or np.isnan(m1) or np.isnan(m2)) else float(np.sign(m1) == np.sign(m2))
        seg = c[i0 - 1 if i0 > 0 else 0:i1]
        net = c[i1 - 1] - base
        eff = abs(net) / max(np.nansum(np.abs(np.diff(seg))), 1e-9)
        revprev = np.nan if prev_net is None or prev_net == 0 or net == 0 else float(np.sign(net) != np.sign(prev_net))
        prev_net = net
        # 5-minute log returns, non-overlapping, inside the window
        k = (i1 - i0) // 5
        r5 = np.array([np.log(c[i0 + 5 * j + 4] / (c[i0 + 5 * j - 1] if i0 + 5 * j > 0 else o[0])) for j in range(k)])
        brk_hold = brk_move = np.nan
        if brk_t is not None and lo <= brk_t < hi and lo >= 600:
            brk_hold = float((c958 - brk_level) * brk_dir > 0)
            brk_move = (c958 - c[brk_t - 570]) * brk_dir / c[brk_t - 570] * 1e4
        rows.append({"sym": sym, "date": date, "period": period(date), "window": name, "bias": bias, "rev": rev,
                     "cont": cont, "eff": float(eff), "revprev": revprev, "net_bp": float(net / base * 1e4),
                     "r5": r5.tolist(), "brk_hold": brk_hold, "brk_move": brk_move})
    return rows

def main():
    allrows = []
    for sym in ["SPY", "QQQ", "IWM"]:
        n = 0
        for date in sessions("underlying", sym):
            bars = load_bars(sym, date)
            if bars is None or is_half_day(bars) or np.isnan(bars["close"][:390]).any(): continue  # 16:00 bar may be null; 2012-2016 SPY/IWM files are empty
            allrows += session_rows(sym, date, bars); n += 1
        print(sym, "sessions", n, flush=True)
    df = pl.DataFrame(allrows)
    df.write_parquet(f"{OUT}/t1_window_rows.parquet")
    # summaries
    out = []
    for sym in ["SPY", "QQQ", "IWM", "ALL"]:
        d = df if sym == "ALL" else df.filter(pl.col("sym") == sym)
        for per in ["ctx", "fit", "oos"]:
            dp = d.filter(pl.col("period") == per)
            if dp.height == 0: continue
            # median window eff per period for the pin test
            for name, lo, hi, bias, mult, rev in WINDOWS:
                w = dp.filter(pl.col("window") == name)
                days = w["date"].to_numpy()
                def stat(col):
                    v = w[col].to_numpy().astype(float); m = np.isfinite(v)
                    lo_, hi_ = boot_ci(v[m], days[m]); return float(v[m].mean()) if m.any() else np.nan, lo_, hi_, int(m.sum())
                cont = stat("cont"); eff = stat("eff"); rp = stat("revprev"); bh = stat("brk_hold"); bm = stat("brk_move")
                # pooled ac5
                r = [np.asarray(x) for x in w["r5"].to_list()]
                pairs = np.concatenate([np.stack([x[:-1], x[1:]], 1) for x in r if len(x) >= 2]) if any(len(x) >= 2 for x in r) else np.zeros((0, 2))
                ac5 = float(np.corrcoef(pairs[:, 0], pairs[:, 1])[0, 1]) if pairs.shape[0] > 10 else np.nan
                # ac5 bootstrap by day
                if pairs.shape[0] > 10:
                    pd_ = np.concatenate([[w["date"][i]] * (len(x) - 1) for i, x in enumerate(r) if len(x) >= 2])
                    ud, inv = np.unique(pd_, return_inverse=True); rng = np.random.default_rng(3); acs = []
                    byday = [np.where(inv == k)[0] for k in range(ud.size)]
                    for _ in range(500):
                        pick = rng.integers(0, ud.size, ud.size); idx = np.concatenate([byday[k] for k in pick])
                        acs.append(np.corrcoef(pairs[idx, 0], pairs[idx, 1])[0, 1])
                    ac_lo, ac_hi = float(np.percentile(acs, 2.5)), float(np.percentile(acs, 97.5))
                else: ac_lo = ac_hi = np.nan
                out.append({"sym": sym, "period": per, "window": name, "spec_bias": bias, "spec_rev": rev, "n": cont[3],
                            "cont": cont[0], "cont_lo": cont[1], "cont_hi": cont[2], "ac5": ac5, "ac5_lo": ac_lo, "ac5_hi": ac_hi,
                            "eff": eff[0], "eff_lo": eff[1], "eff_hi": eff[2], "revprev": rp[0], "revprev_lo": rp[1], "revprev_hi": rp[2],
                            "brk_n": bh[3], "brk_hold": bh[0], "brk_hold_lo": bh[1], "brk_hold_hi": bh[2], "brk_move_bp": bm[0], "brk_move_lo": bm[1], "brk_move_hi": bm[2]})
    s = pl.DataFrame(out)
    # labels: decided on fit, read on oos
    def label(row, eff_med):
        if row["cont_lo"] > 0.5 and row["ac5"] > 0: return "chase"
        if row["cont_hi"] < 0.5 and row["ac5"] < 0: return "fade"
        return "neutral"
    labs = []
    for r in s.iter_rows(named=True):
        per_med = s.filter((pl.col("sym") == r["sym"]) & (pl.col("period") == r["period"]))["eff"].median()
        labs.append({"sym": r["sym"], "period": r["period"], "window": r["window"], "label": label(r, per_med),
                     "pin_like": bool(r["eff_hi"] < per_med), "reversal_prone": bool(r["revprev_lo"] > 0.5)})
    s = s.join(pl.DataFrame(labs), on=["sym", "period", "window"])
    s.write_csv(f"{OUT}/t1_window_summary.csv")
    with pl.Config(tbl_rows=200, tbl_cols=30, tbl_width_chars=250, fmt_str_lengths=20, float_precision=3):
        print(s.select("sym", "period", "window", "spec_bias", "label", "n", "cont", "cont_lo", "cont_hi", "ac5", "ac5_lo", "ac5_hi", "eff", "pin_like", "revprev", "revprev_lo", "revprev_hi", "spec_rev", "reversal_prone", "brk_n", "brk_hold", "brk_move_bp", "brk_move_lo", "brk_move_hi"))

if __name__ == "__main__":
    main()
