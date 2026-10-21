"""Hypothesis C: moc_mag at the two fly entry times, with the audit's normalization imported unchanged.

15:30 entry: the audit's own checkpoint t = 930 (inputs over 15:00 -> 15:30) read from clock_session/out/t5_features.parquet.
15:00 entry: the audit's features re-computed over 14:30 -> 15:00 (stated here because the audit's checkpoints start at
15:05): with the ETF bars stamped 870..899 (all closed by 15:00) and SPX prints 870..900,
  vol_late = volume summed over the bars 870..899 (SPXW: SPY's volume stands in, as in the audit)
  range_late = (highest high - lowest low) / close(869)        (SPX: max - min of the prints 870..900, / print(870))
  move_late = (close(899) - close(869)) / close(869)           (SPX: (print(900) - print(870)) / print(870))
  sweep_imb from the per-contract OHLC bars 870..899 against the chain mid at the bar's end (row stamped t+1), the
  audit's side rule (bought above the mid, sold below, dropped at it), premium = volume x close x 100.
Both are then normalized by t5b_moc_test.normalize() (imported, not copied): the 20-session same-minute mean/sd per name,
clipped z, logistic, moc_mag = mean of the four sigmoids. The t = 930 rows come out identical to the audit's t5_scores
(the rolling norm is per (sym, t)); this is checked and printed.
Quintile cuts: per name and t, the 20/40/60/80th percentiles of moc_mag over the FIT sessions (2022-2024) alone; a session's
quintile is read against them in both periods. Q12 = below the fit 40th percentile.
Writes out/moc_mag.parquet (sym, date, t, moc_mag, quintile, period).
"""
import os, sys, numpy as np, polars as pl
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass engine audit/clock_session")
import t5b_moc_test as t5b          # brings the audit's common.* into t5b's namespace; RAW, OUT (the audit's) below
from common import RAW, OUT as AUDIT_OUT, tod, sessions, load_bars, is_half_day, period
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
T0, T1 = 870, 900

def sweeps_1430(sym, date):
    p = f"{RAW}/data/ohlc/{sym}/{date}.parquet"
    if not os.path.exists(p): return None
    o = (pl.scan_parquet(p).with_columns(tod().alias("t")).filter((pl.col("t") >= T0) & (pl.col("t") <= T1 - 1) & (pl.col("volume") > 0))
         .select("t", "strike", "right", "close", "volume").collect())
    if o.height == 0: return dict(cb=0.0, cs=0.0, pb=0.0, ps=0.0)
    q = (pl.scan_parquet(f"{RAW}/data_full/chains/{sym}/{date}.parquet").with_columns(tod().alias("t"))
         .filter((pl.col("t") >= T0 + 1) & (pl.col("t") <= T1)).select((pl.col("t") - 1).alias("t"), "strike", "right", "mid").collect())
    j = o.join(q, on=["t", "strike", "right"], how="inner").with_columns((pl.col("volume") * pl.col("close") * 100).alias("prem"))
    j = j.with_columns(pl.when(pl.col("close") > pl.col("mid")).then(1).when(pl.col("close") < pl.col("mid")).then(-1).otherwise(0).alias("side"))
    f = lambda r, s: float(j.filter((pl.col("right") == r) & (pl.col("side") == s))["prem"].sum())
    return dict(cb=f("CALL", 1), cs=f("CALL", -1), pb=f("PUT", 1), ps=f("PUT", -1))

def features_1500(sym):
    usym = "SPX" if sym == "SPXW" else sym
    rows = []
    for date in sessions("chains", sym):
        bars = load_bars(usym, date)
        if bars is None or is_half_day(bars): continue
        vbars = load_bars("SPY", date) if sym == "SPXW" else bars
        if vbars is None: continue
        c, h, l, v = bars["close"], bars["high"], bars["low"], vbars["volume"]
        spx = sym == "SPXW"
        i0, i1 = T0 - 570, T1 - 570
        base = c[i0] if spx else c[i0 - 1]
        if not np.isfinite(base): continue
        if spx:
            seg = c[i0:i1 + 1]; ct = c[i1]; hi, lo = np.nanmax(seg), np.nanmin(seg)
        else:
            ct = c[i1 - 1]; hi, lo = np.nanmax(h[i0:i1]), np.nanmin(l[i0:i1])
        if not np.isfinite(ct): continue
        vol = np.nansum(v[i0:i1])
        sw = sweeps_1430(sym, date)
        if sw is None: continue
        cb, pb = sw["cb"], sw["pb"]
        final = c[960 - 570] if np.isfinite(c[960 - 570]) else c[959 - 570]
        rows.append({"sym": sym, "date": date, "period": period(date), "t": T1, "base": base, "close_t": ct, "pre_hi": np.nan, "pre_lo": np.nan,
                     "vol_late": vol, "range_late": (hi - lo) / base, "move_late": (ct - base) / base,
                     "call_buy": cb, "call_sell": sw["cs"], "put_buy": pb, "put_sell": sw["ps"],
                     "sweep_imb": (cb - pb) / (cb + pb) if (cb + pb) > 0 else 0.0,
                     "fwd_close_bp": (final - ct) / ct * 1e4, "fwd_958_bp": (c[958 - 570] - ct) / ct * 1e4})
    print(sym, len(rows), flush=True)
    return pl.DataFrame(rows)

def main():
    aud = pl.read_parquet(f"{AUDIT_OUT}/t5_features.parquet").filter(pl.col("t") == 930)
    f15 = pl.concat([features_1500(s) for s in ["SPY", "QQQ", "IWM", "SPXW"]])
    f15 = f15.select(aud.columns)
    allf = pl.concat([aud, f15.cast(aud.schema)])
    sc = t5b.normalize(allf)
    # check the t = 930 rows against the audit's own scores
    ref = pl.read_parquet(f"{AUDIT_OUT}/t5_scores.parquet").filter(pl.col("t") == 930).select("sym", "date", pl.col("moc_mag").alias("ref"))
    chk = sc.filter(pl.col("t") == 930).join(ref, on=["sym", "date"], how="inner")
    diff = (chk["moc_mag"] - chk["ref"]).abs().fill_nan(0.0)
    print("t=930 rows checked against the audit's t5_scores:", chk.height, "max |diff|", float(diff.max()), "null both", int((chk["moc_mag"].is_null() & chk["ref"].is_null()).sum()))
    out = []
    for (sym, t), g in sc.group_by(["sym", "t"]):
        g = g.filter(pl.col("moc_mag").is_not_null())
        fit = g.filter(pl.col("period") == "fit")["moc_mag"].to_numpy()
        cuts = np.quantile(fit, [0.2, 0.4, 0.6, 0.8]) if fit.size >= 50 else None
        mg = g["moc_mag"].to_numpy()
        quint = (np.searchsorted(cuts, mg, side="right") + 1) if cuts is not None else np.full(mg.size, -1)
        out.append(g.select("sym", "date", "t", "period", "moc_mag", "vol_late", "range_late", "move_late", "sweep_imb").with_columns(pl.Series("quintile", quint.astype(int))))
        print(sym, t, "fit n", fit.size, "cuts", None if cuts is None else np.round(cuts, 3), "n scored", mg.size, flush=True)
    res = pl.concat(out).sort("sym", "t", "date")
    res.write_parquet(f"{OUT}/moc_mag.parquet")
    print(res.group_by("sym", "t", "period").agg(pl.len(), pl.col("moc_mag").mean()).sort("sym", "t", "period"))

if __name__ == "__main__":
    main()
