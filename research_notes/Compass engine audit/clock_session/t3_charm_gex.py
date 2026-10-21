"""Test 3: charm x dealer-book sign in the dealer hour / power hour (the owner's task (a)).

Trades (same-day contracts, nearest strictly out-of-the-money strike against the 15:00 spot, bought at the ask of the
chain row stamped 900, sold at the 15:58 bid; also step 4's 50% trailing stop on the bid; $0.65 each way, none on a
worthless expiry):
  trend : call if the 14:00 -> 15:00 move is up (close of bar 839 -> close of bar 899; SPX prints at 840 and 900),
          put if down.
  fade  : the opposite side.
  pin   : toward the pin proxy = the strike with the largest same-day contract volume (calls + puts) in the bars that
          closed by 15:00, from the per-contract OHLC files (contracts within +-2% of the 09:31 price). Call if the pin
          is above spot, put if below; skipped when the pin is the spot's strike. (Historical open interest by strike
          is not on disk, so the volume-heaviest strike stands in for the gross pin.)
Book (Unusual Whales greek-exposure, daily, book level, UW's sign: call gamma > 0, put gamma < 0): the row dated the
session before the trade. gex_sign = sign(call_gamma + put_gamma). charm_net = call_charm + put_charm.
charm_pressure = |charm_net| / median(|charm_net| over the 20 book rows before it) x 3.0 (the spec's 900-930 window
multiplier). The spec's "> 2.4x" is read as charm_pressure > 2.4. Book rows exist 2025-10-15 -> 2026-10-13 only, so
the book splits cover 2025-10-16 -> 2026-10-09 (one year, no train/check split possible); the trades themselves are
also reported for 2022-2026 without a book.
"""
import sys, numpy as np
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass engine audit/clock_session")
from common import *

def load_book():
    g = pl.concat([pl.read_parquet(f"{UW}/greek-exposure.part0{i}.parquet") for i in (1, 2)])
    g = g.filter(pl.col("ticker").is_in(["SPY", "QQQ", "IWM", "SPX"]))
    g = g.with_columns([pl.col(c).cast(pl.Float64) for c in ["call_gamma", "put_gamma", "call_charm", "put_charm", "call_delta", "put_delta"]])
    g = g.with_columns((pl.col("call_gamma") + pl.col("put_gamma")).alias("gex_net"), (pl.col("call_charm") + pl.col("put_charm")).alias("charm_net")).sort(["ticker", "date"])
    g = g.with_columns(pl.col("charm_net").abs().shift(1).rolling_median(window_size=20, min_samples=15).over("ticker").alias("charm_abs_med20"))
    return g.with_columns((pl.col("charm_net").abs() / pl.col("charm_abs_med20") * 3.0).alias("charm_pressure"))

def pin_strike(sym, date):
    p = f"{RAW}/data/ohlc/{sym}/{date}.parquet"
    if not os.path.exists(p): return None
    v = (pl.scan_parquet(p).with_columns(tod().alias("t")).filter(pl.col("t") <= 899)
         .group_by("strike").agg(pl.col("volume").sum().alias("v")).sort(["v", "strike"], descending=[True, False]).collect())
    return float(v["strike"][0]) if v.height and v["v"][0] > 0 else None

def run(sym, book):
    usym = "SPX" if sym == "SPXW" else sym
    bk = book.filter(pl.col("ticker") == usym).sort("date")
    bdates = bk["date"].to_list()
    rows = []
    for date in sessions("chains", sym):
        bars = load_bars(usym, date)
        if bars is None or is_half_day(bars): continue
        c = bars["close"]
        spot = c[899 - 570] if sym != "SPXW" else c[900 - 570]
        prev = c[839 - 570] if sym != "SPXW" else c[840 - 570]
        if not (np.isfinite(spot) and np.isfinite(prev)) or spot == prev: continue
        strikes = chain_strikes(sym, date)
        if strikes is None: continue
        pin = pin_strike(sym, date)
        up = spot > prev
        plans = [("trend", "CALL" if up else "PUT"), ("fade", "PUT" if up else "CALL")]
        if pin is not None and pin != spot: plans.append(("pin", "CALL" if pin > spot else "PUT"))
        # book of the session before
        i = np.searchsorted(np.array(bdates), date) - 1
        b = bk.row(i, named=True) if i >= 0 else None
        need = {}
        for name, right in plans:
            k = nearest_otm(strikes, spot, right)
            if k is None: continue
            need.setdefault(right, {})[k] = need.get(right, {}).get(k, []) + [name]
        for right, ks in need.items():
            q = quotes(sym, date, ks.keys(), right, 900, 958)
            for k, names in ks.items():
                qq = q.filter(pl.col("strike") == k)
                bid = np.full(NBARS, np.nan); ask = np.full(NBARS, np.nan)
                idx = qq["t"].to_numpy() - 570; bid[idx] = qq["bid"].to_numpy(); ask[idx] = qq["ask"].to_numpy()
                for name in names:
                    for exit_name, trail in (("hold958", None), ("trail50", 0.5)):
                        r = trade_path(bid, ask, 900, 958, trail)
                        if r is None: continue
                        a0, b1, t_out, pnl = r
                        rows.append({"sym": sym, "date": date, "period": period(date), "strategy": name, "right": right, "strike": k, "spot": spot,
                                     "move_840_900_bp": (spot - prev) / prev * 1e4, "pin": pin, "pin_dist_bp": (pin - spot) / spot * 1e4 if pin else np.nan,
                                     "exit": exit_name, "ask_in": a0, "bid_out": b1, "t_out": t_out, "pnl": pnl, "ret_pct": pnl / (a0 * 100) * 100,
                                     "book_date": b["date"] if b else None, "gex_net": b["gex_net"] if b else np.nan, "charm_net": b["charm_net"] if b else np.nan,
                                     "charm_pressure": b["charm_pressure"] if b else np.nan})
    return pl.DataFrame(rows, infer_schema_length=None)

def main():
    book = load_book(); book.write_csv(f"{OUT}/t3_book.csv")
    df = pl.concat([run(s, book) for s in ["SPY", "QQQ", "IWM", "SPXW"]]); df.write_parquet(f"{OUT}/t3_rows.parquet")
    lines = []
    def add(tag, sym, strat, ex, d):
        if d.height == 0: return
        s = stress(d["pnl"].to_numpy(), d["date"].to_numpy()); sp = stress(d["ret_pct"].to_numpy(), d["date"].to_numpy())
        lines.append({"split": tag, "sym": sym, "strategy": strat, "exit": ex, "n": s["n"], "pnl_mean": s["mean"], "ci_lo": s["ci_lo"], "ci_hi": s["ci_hi"],
                      "wo_best5": s["wo_best5"], "win_rate": s["win_rate"], "ret_pct_mean": sp["mean"], "ret_pct_ci_lo": sp["ci_lo"], "ret_pct_ci_hi": sp["ci_hi"],
                      "ask_in_mean": float(d["ask_in"].mean()), "by_year": " ".join(f"{y}:{v[1]:+.0f}" for y, v in s["by_year"].items())})
    for sym in ["SPY", "QQQ", "IWM", "SPXW", "ALL"]:
        for strat in ["trend", "fade", "pin"]:
            for ex in ["hold958", "trail50"]:
                base = df.filter((pl.col("strategy") == strat) & (pl.col("exit") == ex))
                if sym != "ALL": base = base.filter(pl.col("sym") == sym)
                for per in ["fit", "oos"]: add(f"period={per} (no book)", sym, strat, ex, base.filter(pl.col("period") == per))
                hb = base.filter(pl.col("gex_net").is_not_nan() & pl.col("gex_net").is_not_null())
                add("book-year all", sym, strat, ex, hb)
                add("book-year gex>0", sym, strat, ex, hb.filter(pl.col("gex_net") > 0)); add("book-year gex<0", sym, strat, ex, hb.filter(pl.col("gex_net") < 0))
                add("book-year charm_pressure>2.4", sym, strat, ex, hb.filter(pl.col("charm_pressure") > 2.4)); add("book-year charm_pressure<=2.4", sym, strat, ex, hb.filter(pl.col("charm_pressure") <= 2.4))
                add("book-year charm_net>0", sym, strat, ex, hb.filter(pl.col("charm_net") > 0)); add("book-year charm_net<0", sym, strat, ex, hb.filter(pl.col("charm_net") < 0))
                for g in ("gex>0", "gex<0"):
                    hg = hb.filter(pl.col("gex_net") > 0) if g == "gex>0" else hb.filter(pl.col("gex_net") < 0)
                    add(f"book-year {g} & charm_pressure>2.4", sym, strat, ex, hg.filter(pl.col("charm_pressure") > 2.4))
                    add(f"book-year {g} & charm_pressure<=2.4", sym, strat, ex, hg.filter(pl.col("charm_pressure") <= 2.4))
                # charm magnitude terciles within the book year (per sym)
                if sym != "ALL" and hb.height > 30:
                    q1, q2 = hb["charm_pressure"].quantile(1 / 3), hb["charm_pressure"].quantile(2 / 3)
                    add("book-year charm tercile low", sym, strat, ex, hb.filter(pl.col("charm_pressure") <= q1))
                    add("book-year charm tercile mid", sym, strat, ex, hb.filter((pl.col("charm_pressure") > q1) & (pl.col("charm_pressure") <= q2)))
                    add("book-year charm tercile high", sym, strat, ex, hb.filter(pl.col("charm_pressure") > q2))
    out = pl.DataFrame(lines); out.write_csv(f"{OUT}/t3_summary.csv")
    with pl.Config(tbl_rows=500, tbl_cols=30, tbl_width_chars=260, float_precision=1, fmt_str_lengths=50): print(out)

if __name__ == "__main__":
    main()
