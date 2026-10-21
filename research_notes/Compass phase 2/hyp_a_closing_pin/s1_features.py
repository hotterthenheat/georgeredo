"""Step 1: moc_mag at the three entry checkpoints, SPXW and SPY.

The inputs are built by a copy of the audit's t5a_moc_features.py `run()` with the window generalized to (start, t):
  checkpoint 900 (15:00 entry): inputs over the bars 870..899 (14:30 -> 15:00) - at 15:00 the audit's "since 15:00"
      window is empty, so the half hour before stands in; base = the ETF's 14:29 bar close (closes 14:30) / the 14:30
      SPX print; sweeps over the bars 870..899 (sides from the chain rows 871..900).
  checkpoint 930 (15:30 entry): the audit's own definition, inputs over 900..929 (15:00 -> 15:30).
  checkpoint 945 (15:45 check): the audit's own, 900..944.
Every input: vol_late (underlying volume; SPY's stands in for SPXW), range_late, move_late, sweep_imb exactly as t5a.
The normalization is the audit's `normalize()` imported from t5b_moc_test.py (20 prior sessions' same-minute mean/sd,
at least 15, clipped z, logistic, unit weights) - not copied, not edited. The rows for 930 and 945 are checked equal to
the audit's out/t5_features.parquet. Writes out/moc_features.parquet, out/moc_scores.parquet, out/moc_quintile_cuts.csv
(fit-period 20/40/60/80% cuts per name and checkpoint; Q1-Q2 = moc_mag < the 40% cut).
"""
import sys, time, numpy as np, polars as pl
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass phase 2/hyp_a_closing_pin")
from common import *
sys.path.insert(0, AUDIT)
from t5b_moc_test import normalize   # the audit's normalization, imported as is

WINDOWS = [(870, 900), (900, 930), (900, 945)]

def sweeps(sym, date, start, end):
    """Per minute start..end-1: call_buy, call_sell, put_buy, put_sell premium ($). A copy of t5a's with the window free."""
    p = f"{RAW}/data/ohlc/{sym}/{date}.parquet"
    if not os.path.exists(p): return None
    o = (pl.scan_parquet(p).with_columns(tod().alias("t")).filter((pl.col("t") >= start) & (pl.col("t") <= end - 1) & (pl.col("volume") > 0))
         .select("t", "strike", "right", "close", "volume").collect())
    if o.height == 0: return pl.DataFrame({"t": [], "cb": [], "cs": [], "pb": [], "ps": []})
    q = (pl.scan_parquet(f"{RAW}/data_full/chains/{sym}/{date}.parquet").with_columns(tod().alias("t"))
         .filter((pl.col("t") >= start + 1) & (pl.col("t") <= end)).select((pl.col("t") - 1).alias("t"), "strike", "right", "mid").collect())
    j = o.join(q, on=["t", "strike", "right"], how="inner").with_columns((pl.col("volume") * pl.col("close") * 100).alias("prem"))
    j = j.with_columns(pl.when(pl.col("close") > pl.col("mid")).then(1).when(pl.col("close") < pl.col("mid")).then(-1).otherwise(0).alias("side"))
    return (j.group_by("t").agg(
        pl.col("prem").filter((pl.col("right") == "CALL") & (pl.col("side") == 1)).sum().alias("cb"),
        pl.col("prem").filter((pl.col("right") == "CALL") & (pl.col("side") == -1)).sum().alias("cs"),
        pl.col("prem").filter((pl.col("right") == "PUT") & (pl.col("side") == 1)).sum().alias("pb"),
        pl.col("prem").filter((pl.col("right") == "PUT") & (pl.col("side") == -1)).sum().alias("ps")).sort("t"))

def run(sym):
    usym = "SPX" if sym == "SPXW" else sym
    rows = []; t_start = time.time()
    for n, date in enumerate(sessions("chains", sym)):
        bars = load_bars(usym, date)
        if bars is None or is_half_day(bars): continue
        vbars = load_bars("SPY", date) if sym == "SPXW" else bars
        if vbars is None: continue
        c, h, l, v = bars["close"], bars["high"], bars["low"], vbars["volume"]
        spx = sym == "SPXW"
        final = c[960 - 570] if np.isfinite(c[960 - 570]) else c[959 - 570]
        for start, t in WINDOWS:
            base = c[start - 570] if spx else c[start - 1 - 570]
            if not np.isfinite(base): continue
            sw = sweeps(sym, date, start, t)
            if sw is None: continue
            cb = cs = pb = ps = 0.0
            for r in sw.iter_rows(): cb += r[1]; cs += r[2]; pb += r[3]; ps += r[4]
            i0, i1 = start - 570, t - 570
            if spx:
                seg = c[i0:i1 + 1]; ct = c[i1]; hi, lo = np.nanmax(seg), np.nanmin(seg)
            else:
                ct = c[i1 - 1]; hi, lo = np.nanmax(h[i0:i1]), np.nanmin(l[i0:i1])
            vol = np.nansum(v[i0:i1])
            if not np.isfinite(ct): continue
            rows.append({"sym": sym, "date": date, "period": period(date), "t": t, "w_start": start, "base": base, "close_t": ct,
                         "vol_late": vol, "range_late": (hi - lo) / base, "move_late": (ct - base) / base,
                         "call_buy": cb, "call_sell": cs, "put_buy": pb, "put_sell": ps,
                         "sweep_imb": (cb - pb) / (cb + pb) if (cb + pb) > 0 else 0.0,
                         "fwd_close_bp": (final - ct) / ct * 1e4})
        if n % 200 == 0: print(sym, n, date, f"{time.time() - t_start:.0f}s", flush=True)
    print(sym, "rows", len(rows), flush=True)
    return pl.DataFrame(rows)

if __name__ == "__main__":
    feats = pl.concat([run(s) for s in ["SPXW", "SPY"]])
    feats.write_parquet(f"{OUT}/moc_features.parquet")
    # check the 930 / 945 rows against the audit's own file
    a = pl.read_parquet(f"{AUDIT}/out/t5_features.parquet").filter(pl.col("sym").is_in(["SPXW", "SPY"]) & pl.col("t").is_in([930, 945]))
    j = feats.filter(pl.col("t").is_in([930, 945])).join(a, on=["sym", "date", "t"], how="inner", suffix="_a")
    diffs = {c: int((abs(j[c] - j[c + "_a"]) > 1e-9).sum()) for c in ["vol_late", "range_late", "move_late", "sweep_imb", "fwd_close_bp"]}
    print("rows compared with the audit's t5_features at 930/945:", j.height, "of", feats.filter(pl.col("t").is_in([930, 945])).height, "differences:", diffs)
    sc = normalize(feats)
    sc.write_parquet(f"{OUT}/moc_scores.parquet")
    cuts = []
    for sym in ["SPXW", "SPY"]:
        for t in [900, 930, 945]:
            x = sc.filter((pl.col("sym") == sym) & (pl.col("t") == t) & (pl.col("period") == "fit") & pl.col("moc_mag").is_not_null())["moc_mag"].to_numpy()
            q = np.quantile(x, [0.2, 0.4, 0.6, 0.8])
            n_oos = sc.filter((pl.col("sym") == sym) & (pl.col("t") == t) & (pl.col("period") == "oos") & pl.col("moc_mag").is_not_null())
            cuts.append({"sym": sym, "t": t, "n_fit": int(x.size), "q20": q[0], "q40": q[1], "q60": q[2], "q80": q[3],
                         "n_oos": n_oos.height, "oos_share_below_q40": float((n_oos["moc_mag"].to_numpy() < q[1]).mean())})
    cuts = pl.DataFrame(cuts); cuts.write_csv(f"{OUT}/moc_quintile_cuts.csv"); print(cuts)
    # the magnitude check at each checkpoint: Spearman of moc_mag with |move to the close|
    from scipy.stats import spearmanr
    out = []
    for sym in ["SPXW", "SPY"]:
        for t in [900, 930, 945]:
            for per in ["fit", "oos"]:
                d = sc.filter((pl.col("sym") == sym) & (pl.col("t") == t) & (pl.col("period") == per) & pl.col("moc_mag").is_not_null())
                r = spearmanr(d["moc_mag"].to_numpy(), np.abs(d["fwd_close_bp"].to_numpy()))
                out.append({"sym": sym, "t": t, "period": per, "n": d.height, "rho_mag_vs_absfwd": float(r.statistic), "p": float(r.pvalue),
                            "abs_fwd_bp_mean": float(np.abs(d["fwd_close_bp"].to_numpy()).mean())})
    out = pl.DataFrame(out); out.write_csv(f"{OUT}/moc_predictive_by_checkpoint.csv"); print(out)
