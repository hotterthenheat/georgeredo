"""Test 5, pass 2: the deterministic MOC normalization, its predictive power, and the power-hour rule's EV.

THE FORMULA (exact):
  For each name, each input x and each checkpoint minute t (905..950 step 5), the norm is the mean and standard deviation
  of x at the SAME minute t over the 20 sessions strictly before the day (at least 15 of them present, else no score).
    x_vol   = ln(1 + vol_late)            x_range = ln(1e-6 + range_late)
    x_move  = move_late                   x_sweep = sweep_imb
  z_i = clip((x_i - mean20_i) / sd20_i, -4, 4);  sigma(z) = 1 / (1 + exp(-z));  u_i = 2*sigma(z_i) - 1  in (-1, 1)
  SIGNED score (direction carried by the move and the sweep imbalance; the magnitude inputs amplify in the direction of
  the late move), every weight 1.00:
    moc_score = u_move + u_sweep + sign(move_late) * (u_vol + u_range)          range (-4, 4)
  MAGNITUDE score (the spec's "five magnitude_* inputs", four of which exist on disk; the closing-cross imbalance does
  not — a blocker): each magnitude is z-scored against its own 20-session minute norm, |move_late| and |sweep_imb| for
  the signed ones:
    moc_mag = ( sigma(z_vol) + sigma(z_range) + sigma(z_|move|) + sigma(z_|sweep|) ) / 4      range (0, 1)
POWER-HOUR RULE (900 <= t < 960): at the first checkpoint t where close_t > the pre-15:00 session high AND call premium
leads (sweep_imb > 0) AND moc_score > 0 -> buy the nearest OTM same-day call at the ask of the row stamped t; mirror for
puts (close_t < pre-15:00 low, sweep_imb < 0, moc_score < 0). Out at the 15:58 bid, or step 4's 50% trailing stop.
Variants: full rule; breakout + sweep (no score); breakout alone; breakout + moc_mag > 0.5.
"""
import sys, numpy as np
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass engine audit/clock_session")
from common import *

def sig(z): return 1 / (1 + np.exp(-z))

def normalize(df):
    df = df.sort(["sym", "t", "date"])
    df = df.with_columns(np.log1p(pl.col("vol_late")).alias("x_vol"), (pl.col("range_late") + 1e-6).log().alias("x_range"),
                         pl.col("move_late").alias("x_move"), pl.col("sweep_imb").alias("x_sweep"),
                         pl.col("move_late").abs().alias("x_amove"), pl.col("sweep_imb").abs().alias("x_asweep"))
    for c in ["x_vol", "x_range", "x_move", "x_sweep", "x_amove", "x_asweep"]:
        m = pl.col(c).shift(1).rolling_mean(window_size=20, min_samples=15).over(["sym", "t"])
        s = pl.col(c).shift(1).rolling_std(window_size=20, min_samples=15).over(["sym", "t"])
        df = df.with_columns(((pl.col(c) - m) / s).clip(-4, 4).alias("z" + c[1:]))
    u = lambda c: 2 * (1 / (1 + (-pl.col(c)).exp())) - 1
    df = df.with_columns((u("z_move") + u("z_sweep") + pl.col("move_late").sign() * (u("z_vol") + u("z_range"))).alias("moc_score"),
                         ((1 / (1 + (-pl.col("z_vol")).exp()) + 1 / (1 + (-pl.col("z_range")).exp()) + 1 / (1 + (-pl.col("z_amove")).exp()) + 1 / (1 + (-pl.col("z_asweep")).exp())) / 4).alias("moc_mag"))
    return df

def spearman(a, b):
    from scipy.stats import spearmanr
    r = spearmanr(a, b); return float(r.statistic), float(r.pvalue)

def predictive(df):
    lines = []
    d950 = df.filter((pl.col("t") == 950) & pl.col("moc_score").is_not_null() & pl.col("fwd_close_bp").is_not_null())
    for sym in ["SPY", "QQQ", "IWM", "SPXW", "ALL"]:
        for per in ["fit", "oos"]:
            d = d950.filter(pl.col("period") == per)
            if sym != "ALL": d = d.filter(pl.col("sym") == sym)
            if d.height < 30: continue
            y = d["fwd_close_bp"].to_numpy(); s = d["moc_score"].to_numpy(); mg = d["moc_mag"].to_numpy()
            row = {"sym": sym, "period": per, "n": d.height}
            row["rho_signed_vs_fwd"], row["p_signed"] = spearman(s, y)
            row["rho_mag_vs_absfwd"], row["p_mag"] = spearman(mg, np.abs(y))
            for c in ["z_move", "z_sweep", "z_vol", "z_range"]:
                row[f"rho_{c}"] = spearman(d[c].to_numpy(), y)[0]
            row["rho_zvol_vs_absfwd"] = spearman(d["z_vol"].to_numpy(), np.abs(y))[0]
            row["rho_zrange_vs_absfwd"] = spearman(d["z_range"].to_numpy(), np.abs(y))[0]
            nz = s != 0
            row["sign_hit_all"] = float((np.sign(s[nz]) == np.sign(y[nz])).mean())
            big = np.abs(s) > 1.0; row["n_abs_gt1"] = int(big.sum())
            row["sign_hit_abs_gt1"] = float((np.sign(s[big]) == np.sign(y[big])).mean()) if big.sum() > 10 else np.nan
            row["mean_fwd_bp_score_pos"] = float(y[s > 0].mean()); row["mean_fwd_bp_score_neg"] = float(y[s < 0].mean())
            q = np.quantile(s, [0.2, 0.8]); row["fwd_top20_bp"] = float(y[s >= q[1]].mean()); row["fwd_bot20_bp"] = float(y[s <= q[0]].mean())
            lo, hi = boot_ci(np.sign(s[nz]) * y[nz], d["date"].to_numpy()[nz]); row["signed_fwd_bp_mean"] = float((np.sign(s[nz]) * y[nz]).mean()); row["signed_fwd_ci_lo"], row["signed_fwd_ci_hi"] = lo, hi
            lines.append(row)
    return pl.DataFrame(lines)

def rule_trades(df):
    rows = []
    d = df.filter(pl.col("moc_score").is_not_null()).sort(["sym", "date", "t"])
    for (sym,), g in d.group_by(["sym"], maintain_order=True):
        usym = "SPX" if sym == "SPXW" else sym
        for (date,), s in g.group_by(["date"], maintain_order=True):
            fires = {}
            for r in s.iter_rows(named=True):
                up = r["close_t"] > r["pre_hi"]; dn = r["close_t"] < r["pre_lo"]
                if not (up or dn): continue
                right = "CALL" if up else "PUT"; sgn = 1 if up else -1
                conds = {"brk": True, "brk+sweep": (r["sweep_imb"] * sgn > 0), "full": (r["sweep_imb"] * sgn > 0) and (r["moc_score"] * sgn > 0),
                         "brk+mag>0.5": r["moc_mag"] > 0.5, "brk+score": (r["moc_score"] * sgn > 0)}
                for k, ok in conds.items():
                    if ok and k not in fires: fires[k] = (r["t"], right, r["close_t"], r["moc_score"], r["moc_mag"], r["sweep_imb"])
            if not fires: continue
            strikes = chain_strikes(sym, date)
            if strikes is None: continue
            need = {}
            for k, (t, right, px, sc, mg, sw) in fires.items():
                K = nearest_otm(strikes, px, right)
                if K is None: continue
                need.setdefault((right, K), []).append((k, t, px, sc, mg, sw))
            for (right, K), lst in need.items():
                q = quotes(sym, date, [K], right, 900, 958)
                bid = np.full(NBARS, np.nan); ask = np.full(NBARS, np.nan)
                idx = q["t"].to_numpy() - 570; bid[idx] = q["bid"].to_numpy(); ask[idx] = q["ask"].to_numpy()
                for k, t, px, sc, mg, sw in lst:
                    for ex, trail in (("hold958", None), ("trail50", 0.5)):
                        res = trade_path(bid, ask, t, 958, trail)
                        if res is None: continue
                        a0, b1, t_out, pnl = res
                        rows.append({"sym": sym, "date": date, "period": period(date), "variant": k, "t_in": t, "right": right, "strike": K, "spot": px,
                                     "moc_score": sc, "moc_mag": mg, "sweep_imb": sw, "exit": ex, "ask_in": a0, "bid_out": b1, "t_out": t_out, "pnl": pnl, "ret_pct": pnl / (a0 * 100) * 100})
    return pl.DataFrame(rows, infer_schema_length=None)

def main():
    df = normalize(pl.read_parquet(f"{OUT}/t5_features.parquet"))
    df.write_parquet(f"{OUT}/t5_scores.parquet")
    pred = predictive(df); pred.write_csv(f"{OUT}/t5_predictive.csv")
    with pl.Config(tbl_rows=100, tbl_cols=40, tbl_width_chars=300, float_precision=3): print(pred)
    tr = rule_trades(df); tr.write_parquet(f"{OUT}/t5_rule_rows.parquet")
    lines = []
    for sym in ["SPY", "QQQ", "IWM", "SPXW", "ALL"]:
        for var in ["brk", "brk+sweep", "brk+score", "brk+mag>0.5", "full"]:
            for ex in ["hold958", "trail50"]:
                for per in ["fit", "oos"]:
                    d = tr.filter((pl.col("variant") == var) & (pl.col("exit") == ex) & (pl.col("period") == per))
                    if sym != "ALL": d = d.filter(pl.col("sym") == sym)
                    if d.height == 0: continue
                    s = stress(d["pnl"].to_numpy(), d["date"].to_numpy()); sp = stress(d["ret_pct"].to_numpy(), d["date"].to_numpy())
                    lines.append({"sym": sym, "variant": var, "exit": ex, "period": per, "n": s["n"], "pnl_mean": s["mean"], "ci_lo": s["ci_lo"], "ci_hi": s["ci_hi"], "wo_best5": s["wo_best5"],
                                  "win_rate": s["win_rate"], "ret_pct_mean": sp["mean"], "ret_pct_ci_lo": sp["ci_lo"], "ret_pct_ci_hi": sp["ci_hi"], "ask_in_mean": float(d["ask_in"].mean()),
                                  "by_year": " ".join(f"{y}:{v[1]:+.0f}" for y, v in s["by_year"].items())})
    out = pl.DataFrame(lines); out.write_csv(f"{OUT}/t5_rule_summary.csv")
    for r in out.iter_rows(named=True):
        print(f"{r['sym']:4} {r['variant']:12} {r['exit']:7} {r['period']:3} n={r['n']:4} pnl=${r['pnl_mean']:+7.1f} ci=[{r['ci_lo']:+6.1f},{r['ci_hi']:+6.1f}] wo5={r['wo_best5']:+6.1f} win={r['win_rate']:.2f} ret%={r['ret_pct_mean']:+6.1f} [{r['ret_pct_ci_lo']:+5.1f},{r['ret_pct_ci_hi']:+5.1f}] ask={r['ask_in_mean']:5.2f} | {r['by_year']}")

if __name__ == "__main__":
    main()
