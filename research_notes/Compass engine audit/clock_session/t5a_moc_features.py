"""Test 5, pass 1: the MOC inputs available on disk, per session and per 5-minute checkpoint 15:05..15:50.

For t in {905, 910, ..., 950}, from the bars stamped 900..t-1 (all closed by t):
  vol_late    : underlying volume summed (SPXW: SPY's volume stands in - the index has none)
  range_late  : (highest high - lowest low) / close(899)              (SPX prints: max - min of the prints 900..t)
  move_late   : (close(t-1) - close(899)) / close(899)                 (SPX: print(t) - print(900))
  sweep       : per-contract premium = volume x close x 100 from the OHLC files (contracts within +-2% of the 09:31
                price), side = bought when the bar's close is above the NBBO mid at the bar's end (chain row stamped
                t_bar+1), sold when below, dropped when equal (step 5's rule). call_buy, call_sell, put_buy, put_sell
                summed over the bars 900..t-1. sweep_imb = (call_buy - put_buy) / (call_buy + put_buy), 0 if none.
  pre-15:00 session high / low (bars 570..899), close(t-1), and the targets: the move from close(t-1) to the close
  (the 16:00 bar when printed, else the 15:59 bar; SPX: the 16:00 print) and to the 15:58 close.
Writes out/t5_features.parquet. Normalization and tests are in t5b_moc_test.py.
"""
import sys, numpy as np
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass engine audit/clock_session")
from common import *

CHECKS = list(range(905, 951, 5))

def sweeps(sym, date):
    """Per minute 900..949: call_buy, call_sell, put_buy, put_sell premium ($)."""
    p = f"{RAW}/data/ohlc/{sym}/{date}.parquet"
    if not os.path.exists(p): return None
    o = (pl.scan_parquet(p).with_columns(tod().alias("t")).filter((pl.col("t") >= 900) & (pl.col("t") <= 949) & (pl.col("volume") > 0))
         .select("t", "strike", "right", "close", "volume").collect())
    if o.height == 0: return pl.DataFrame({"t": [], "cb": [], "cs": [], "pb": [], "ps": []})
    q = (pl.scan_parquet(f"{RAW}/data_full/chains/{sym}/{date}.parquet").with_columns(tod().alias("t"))
         .filter((pl.col("t") >= 901) & (pl.col("t") <= 950)).select((pl.col("t") - 1).alias("t"), "strike", "right", "mid").collect())
    j = o.join(q, on=["t", "strike", "right"], how="inner").with_columns((pl.col("volume") * pl.col("close") * 100).alias("prem"))
    j = j.with_columns(pl.when(pl.col("close") > pl.col("mid")).then(1).when(pl.col("close") < pl.col("mid")).then(-1).otherwise(0).alias("side"))
    return (j.group_by("t").agg(
        pl.col("prem").filter((pl.col("right") == "CALL") & (pl.col("side") == 1)).sum().alias("cb"),
        pl.col("prem").filter((pl.col("right") == "CALL") & (pl.col("side") == -1)).sum().alias("cs"),
        pl.col("prem").filter((pl.col("right") == "PUT") & (pl.col("side") == 1)).sum().alias("pb"),
        pl.col("prem").filter((pl.col("right") == "PUT") & (pl.col("side") == -1)).sum().alias("ps")).sort("t"))

def run(sym):
    usym = "SPX" if sym == "SPXW" else sym
    rows = []
    for date in sessions("chains", sym):
        bars = load_bars(usym, date)
        if bars is None or is_half_day(bars): continue
        vbars = load_bars("SPY", date) if sym == "SPXW" else bars
        if vbars is None: continue
        c, h, l, v = bars["close"], bars["high"], bars["low"], vbars["volume"]
        spx = sym == "SPXW"
        base = c[900 - 570] if spx else c[899 - 570]
        if not np.isfinite(base): continue
        pre_hi, pre_lo = np.nanmax(h[0:330]), np.nanmin(l[0:330])  # bars 570..899
        final = c[960 - 570] if np.isfinite(c[960 - 570]) else c[959 - 570]
        c958 = c[958 - 570]
        sw = sweeps(sym, date)
        if sw is None: continue
        swt = {int(r[0]): r[1:] for r in sw.iter_rows()}
        cb = cs = pb = ps = 0.0
        last_t = 900
        for t in CHECKS:
            for tt in range(last_t, t):
                if tt in swt: cb += swt[tt][0]; cs += swt[tt][1]; pb += swt[tt][2]; ps += swt[tt][3]
            last_t = t
            i0, i1 = 900 - 570, t - 570  # bars 900..t-1 -> indices i0..i1-1
            if spx:
                seg = c[i0:i1 + 1]; ct = c[i1]; hi, lo = np.nanmax(seg), np.nanmin(seg)
            else:
                ct = c[i1 - 1]; hi, lo = np.nanmax(h[i0:i1]), np.nanmin(l[i0:i1])
            vol = np.nansum(v[i0:i1])
            if not np.isfinite(ct): continue
            rows.append({"sym": sym, "date": date, "period": period(date), "t": t, "base": base, "close_t": ct, "pre_hi": pre_hi, "pre_lo": pre_lo,
                         "vol_late": vol, "range_late": (hi - lo) / base, "move_late": (ct - base) / base,
                         "call_buy": cb, "call_sell": cs, "put_buy": pb, "put_sell": ps,
                         "sweep_imb": (cb - pb) / (cb + pb) if (cb + pb) > 0 else 0.0,
                         "fwd_close_bp": (final - ct) / ct * 1e4, "fwd_958_bp": (c958 - ct) / ct * 1e4})
    print(sym, len(rows), flush=True)
    return pl.DataFrame(rows)

if __name__ == "__main__":
    df = pl.concat([run(s) for s in ["SPY", "QQQ", "IWM", "SPXW"]])
    df.write_parquet(f"{OUT}/t5_features.parquet"); print(df.shape)
