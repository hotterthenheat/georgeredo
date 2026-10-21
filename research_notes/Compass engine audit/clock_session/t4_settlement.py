"""Test 4: the 15:58 flat rule vs riding to settlement.

For every same-day contract in the money at t = 958 (spot = the close of the bar stamped 957, which closes at 15:58;
SPX = the 15:58 index print), compare selling at the 15:58 bid (the flat rule; $0.65 fee) with riding to settlement
= intrinsic at the closing spot (no fee assumed on exercise/cash settlement). Closing spot: the 16:00 bar close when
printed, else the 15:59 bar close (ETFs); the 16:00 index print for SPX. The SPXW official settlement is the SPX close
computed from constituents' closing prints, which the 16:00 print approximates.
ride_edge ($ per contract) = (intrinsic_close - bid_958) * 100 + 0.65.
Rows kept: 958 bid > 0 and intrinsic at 958 <= 1% of spot (what a 0DTE holder is plausibly long); also "nearest ITM".
delta_aligned = the 15:00 -> 15:58 move has the contract's direction.
"""
import sys, numpy as np
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass engine audit/clock_session")
from common import *

def run(sym):
    usym = "SPX" if sym == "SPXW" else sym
    rows = []
    for date in sessions("chains", sym):
        bars = load_bars(usym, date)
        if bars is None or is_half_day(bars): continue
        c = bars["close"]
        spot958 = c[957 - 570] if sym != "SPXW" else c[958 - 570]
        close = c[960 - 570] if np.isfinite(c[960 - 570]) else c[959 - 570]
        spot900 = c[899 - 570] if sym != "SPXW" else c[900 - 570]
        if not (np.isfinite(spot958) and np.isfinite(close) and np.isfinite(spot900)): continue
        p = f"{RAW}/data_full/chains/{sym}/{date}.parquet"
        q = (pl.scan_parquet(p).with_columns(tod().alias("t")).filter(pl.col("t") == 958)
             .select("strike", "right", "bid", "ask").collect())
        if q.height == 0: continue
        mv = np.sign(spot958 - spot900)
        for strike, right, bid, ask in q.iter_rows():
            sgn = 1 if right == "CALL" else -1
            intr958 = max(0.0, sgn * (spot958 - strike)); intr_close = max(0.0, sgn * (close - strike))
            if intr958 <= 0 or bid <= 0 or intr958 > 0.01 * spot958: continue
            rows.append({"sym": sym, "date": date, "period": period(date), "strike": strike, "right": right, "bid958": bid, "ask958": ask,
                         "intr958": intr958, "intr_close": intr_close, "moneyness": intr958 / spot958,
                         "ride_edge": (intr_close - bid) * 100 + FEE, "delta_aligned": bool(mv == sgn)})
    df = pl.DataFrame(rows)
    # nearest ITM per date/right
    df = df.with_columns((pl.col("intr958") == pl.col("intr958").min().over(["date", "right"])).alias("nearest"))
    return df

def main():
    frames = [run(s) for s in ["SPY", "QQQ", "IWM", "SPXW"]]
    df = pl.concat(frames); df.write_parquet(f"{OUT}/t4_rows.parquet")
    lines = []
    for sym in ["SPY", "QQQ", "IWM", "SPXW"]:
        for per in ["fit", "oos", "all"]:
            for sub in ["all_itm_1pct", "nearest_itm", "nearest_aligned", "nearest_not_aligned"]:
                d = df.filter(pl.col("sym") == sym)
                if per != "all": d = d.filter(pl.col("period") == per)
                if sub != "all_itm_1pct": d = d.filter(pl.col("nearest"))
                if sub == "nearest_aligned": d = d.filter(pl.col("delta_aligned"))
                if sub == "nearest_not_aligned": d = d.filter(~pl.col("delta_aligned"))
                if d.height == 0: continue
                v = d["ride_edge"].to_numpy(); pct = (d["intr_close"] - d["bid958"]).to_numpy() / d["bid958"].to_numpy() * 100
                s = stress(v, d["date"].to_numpy())
                lines.append({"sym": sym, "period": per, "subset": sub, "n": d.height, "sessions": d["date"].n_unique(),
                              "ride_edge_mean": s["mean"], "ci_lo": s["ci_lo"], "ci_hi": s["ci_hi"], "median": float(np.median(v)),
                              "p1": float(np.percentile(v, 1)), "p5": float(np.percentile(v, 5)), "p95": float(np.percentile(v, 95)), "p99": float(np.percentile(v, 99)),
                              "share_ride_loses": float((v < 0).mean()), "share_ride_loses_gt_bid10pct": float((pct < -10).mean()),
                              "pct_of_bid_mean": float(pct.mean()), "pct_of_bid_median": float(np.median(pct)),
                              "wo_best5_days": s["wo_best5"], "by_year": " ".join(f"{y}:{v_[1]:+.1f}" for y, v_ in s["by_year"].items())})
    out = pl.DataFrame(lines); out.write_csv(f"{OUT}/t4_summary.csv")
    with pl.Config(tbl_rows=100, tbl_cols=30, tbl_width_chars=260, float_precision=2, fmt_str_lengths=60): print(out)

if __name__ == "__main__":
    main()
