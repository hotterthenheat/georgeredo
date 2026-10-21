"""Step 6: the tables for the notes, read off out/cells_oos.csv, out/cells_diff_oos.csv and the spread rows.
Prints: the pick fit / OOS by cut; the 14 fit-eligible cells OOS; the signal lift by name and entry OOS; the grid read
whole OOS (how many cells positive / CI clear, by cut); the pick's structure at 15:00 / 15:45 and under tp50 / stop2x;
the pick's OOS year by year, its tail day, and its sensitivity to the SPXW settlement proxy (settle +- 1, 2 points);
SPY's best fit cells OOS. Writes out/tables_oos.txt (this print) and out/pick_oos_rows.csv."""
import sys, numpy as np, polars as pl
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass phase 2/hyp_a_closing_pin")
from common import *
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(420); pl.Config.set_fmt_str_lengths(140); pl.Config.set_float_precision(2)
K = ["sym", "side", "rule", "wing", "t", "mgmt"]
c = pl.read_csv(f"{OUT}/cells_oos.csv"); d = pl.read_csv(f"{OUT}/cells_diff_oos.csv")
e = pl.read_csv(f"{OUT}/eligible_fit.csv")
PICK = {"sym": "SPXW", "side": "CALL", "rule": "m1.00", "wing": 25.0, "t": 930, "mgmt": "hold"}
def sel(df, **kw):
    for k, v in kw.items(): df = df.filter(pl.col(k) == v)
    return df
COLS = ["period", "cut", "n", "mean_usd", "ci_lo", "ci_hi", "mean_pct_risk", "pct_ci_lo", "pct_ci_hi", "win_rate", "avg_win", "avg_loss", "full_loss_share", "p5", "p1", "worst", "worst_date", "profit_factor", "max_dd", "longest_losing_streak", "wo_best5", "total", "total_wo_worst", "credit_mean", "max_risk_mean", "by_year"]
print("=== THE PICK, fit and OOS, by cut ===")
p = sel(c, **PICK).sort(["period", "cut"]); print(p.select(COLS))
print("=== THE PICK, the signal lift (Q12 - Q345), fit and OOS ===")
print(sel(d, **PICK).select("period", "n_q12", "n_q345", "mean_usd_q12", "mean_usd_q345", "diff_usd", "diff_usd_ci_lo", "diff_usd_ci_hi", "mean_pct_q12", "mean_pct_q345", "diff_pct", "diff_pct_ci_lo", "diff_pct_ci_hi", "mean_pct_all", "q12_minus_all_pct", "win_q12", "win_q345"))
print("=== THE 14 FIT-ELIGIBLE CELLS (Q12), fit beside OOS ===")
f = e.select(K + ["n", "mean_usd", "mean_pct_risk", "pct_ci_lo", "diff_pct"]).rename({"n": "n_fit", "mean_usd": "usd_fit", "mean_pct_risk": "pct_fit", "pct_ci_lo": "pct_ci_lo_fit", "diff_pct": "lift_fit"})
o = c.filter((pl.col("period") == "oos") & (pl.col("cut") == "Q12")).select(K + ["n", "mean_usd", "ci_lo", "ci_hi", "mean_pct_risk", "pct_ci_lo", "pct_ci_hi", "win_rate", "full_loss_share", "profit_factor", "wo_best5", "worst", "worst_date", "total", "total_wo_worst", "by_year"])
lo = d.filter(pl.col("period") == "oos").select(K + ["diff_pct", "diff_pct_ci_lo", "diff_pct_ci_hi", "mean_pct_q345", "mean_pct_all"]).rename({"diff_pct": "lift_oos", "diff_pct_ci_lo": "lift_lo", "diff_pct_ci_hi": "lift_hi"})
print(f.join(o, on=K, how="left").join(lo, on=K, how="left"))
print("=== THE SIGNAL LIFT BY NAME AND ENTRY, OOS (every cell with both cuts) ===")
for per in ["fit", "oos"]:
    x = d.filter(pl.col("period") == per)
    print(per, x.group_by(["sym", "t"]).agg(pl.len().alias("cells"), pl.col("diff_pct").mean().alias("lift_mean"), (pl.col("diff_pct") > 0).mean().alias("share_pos"), (pl.col("diff_pct_ci_lo") > 0).mean().alias("share_ci_clear"),
                                            pl.col("mean_pct_q12").mean(), pl.col("mean_pct_q345").mean(), pl.col("mean_pct_all").mean(), pl.col("full_loss_q12").mean(), pl.col("full_loss_q345").mean()).sort(["sym", "t"]))
print("=== THE GRID READ WHOLE, OOS: cells positive and CI clear, by name, cut and management ===")
x = c.filter(pl.col("period") == "oos")
print(x.group_by(["sym", "cut", "mgmt"]).agg(pl.len().alias("cells"), (pl.col("mean_pct_risk") > 0).mean().alias("share_pos"), (pl.col("pct_ci_lo") > 0).mean().alias("share_ci_clear"), (pl.col("pct_ci_hi") < 0).mean().alias("share_ci_neg"), pl.col("mean_pct_risk").mean().alias("pct_mean"), pl.col("mean_pct_risk").median().alias("pct_median")).sort(["sym", "cut", "mgmt"]))
print(x.group_by(["sym", "cut", "t"]).agg(pl.len().alias("cells"), (pl.col("mean_pct_risk") > 0).mean().alias("share_pos"), (pl.col("pct_ci_lo") > 0).mean().alias("share_ci_clear"), pl.col("mean_pct_risk").mean().alias("pct_mean")).sort(["sym", "cut", "t"]))
print("=== OOS: the best cells by lower CI (Q12 and all), both names - read once, not a pick ===")
for cut in ["Q12", "all"]:
    print(cut, x.filter(pl.col("cut") == cut).sort("pct_ci_lo", descending=True).select(K + ["n", "mean_usd", "mean_pct_risk", "pct_ci_lo", "pct_ci_hi", "win_rate", "profit_factor", "wo_best5", "worst", "by_year"]).head(8))
print("=== THE PICK'S STRUCTURE at 15:00 / 15:30 / 15:45 and under each management, OOS, every cut ===")
print(c.filter((pl.col("period") == "oos") & (pl.col("sym") == "SPXW") & (pl.col("side") == "CALL") & (pl.col("rule") == "m1.00") & (pl.col("wing") == 25.0)).sort(["t", "mgmt", "cut"]).select(["t", "mgmt", "cut", "n", "mean_usd", "ci_lo", "ci_hi", "mean_pct_risk", "pct_ci_lo", "pct_ci_hi", "win_rate", "full_loss_share", "profit_factor", "wo_best5", "worst", "worst_date", "total", "total_wo_worst", "by_year"]))
print("=== THE PICK'S FAMILY (SPXW, 15:30, hold, 25-pt wing), every side and rule, OOS, every cut ===")
print(c.filter((pl.col("period") == "oos") & (pl.col("sym") == "SPXW") & (pl.col("t") == 930) & (pl.col("mgmt") == "hold") & (pl.col("wing") == 25.0)).sort(["side", "rule", "cut"]).select(["side", "rule", "cut", "n", "mean_usd", "ci_lo", "ci_hi", "mean_pct_risk", "pct_ci_lo", "pct_ci_hi", "win_rate", "full_loss_share", "profit_factor", "wo_best5", "worst", "total", "total_wo_worst", "by_year"]))
print("=== SPY: the pick's analogue (m1.00, widest wing 5, 15:30, hold) and SPY's best fit Q12 cells, OOS ===")
print(c.filter((pl.col("sym") == "SPY") & (pl.col("rule") == "m1.00") & (pl.col("wing") == 5.0) & (pl.col("t") == 930) & (pl.col("mgmt") == "hold")).sort(["side", "period", "cut"]).select(["side", "period", "cut", "n", "mean_usd", "ci_lo", "ci_hi", "mean_pct_risk", "pct_ci_lo", "pct_ci_hi", "win_rate", "full_loss_share", "profit_factor", "wo_best5", "worst", "credit_mean", "by_year"]))
fs = c.filter((pl.col("sym") == "SPY") & (pl.col("period") == "fit") & (pl.col("cut") == "Q12") & pl.col("t").is_in([900, 930])).sort("pct_ci_lo", descending=True).head(6).select(K)
print(fs.join(c.filter(pl.col("cut") == "Q12"), on=K, how="left").sort(K + ["period"]).select(K + ["period", "n", "mean_usd", "ci_lo", "ci_hi", "mean_pct_risk", "pct_ci_lo", "pct_ci_hi", "win_rate", "profit_factor", "wo_best5", "credit_mean"]))
# the pick's rows: tail day, equity, settlement sensitivity
rows = pl.read_parquet(f"{OUT}/spread_rows_SPXW.parquet")
sc = pl.read_parquet(f"{OUT}/moc_scores.parquet").select("sym", "date", "t", "moc_mag"); cuts = pl.read_csv(f"{OUT}/moc_quintile_cuts.csv").select("sym", "t", "q40")
r = sel(rows, **PICK).join(sc, on=["sym", "date", "t"]).join(cuts, on=["sym", "t"]).filter(pl.col("moc_mag") < pl.col("q40")).sort("date")
r.write_csv(f"{OUT}/pick_rows.csv")
for per in ["fit", "oos"]:
    g = r.filter(pl.col("period") == per); pnl = g["pnl"].to_numpy()
    print(f"=== THE PICK {per}: n {pnl.size} total {pnl.sum():+.0f}; worst 3 sessions:", [(x[0], round(x[1], 1), x[2], x[3], round(x[4], 2)) for x in g.sort("pnl").head(3).select("date", "pnl", "Ks", "settle", "credit").iter_rows()])
    print(f"    total without worst 1 / 3 sessions: {pnl.sum() - pnl.min():+.0f} / {pnl.sum() - np.sort(pnl)[:3].sum():+.0f}; sessions settling above the short strike: {int((g['settle'] > g['Ks']).sum())}; above the long strike: {int((g['settle'] >= g['Kl']).sum())}")
    print("    distance short strike - spot (pts): mean %.1f p10 %.1f p90 %.1f; credit mean %.2f; settle - spot mean %.2f sd %.2f max %.2f" % ((g["Ks"] - g["spot"]).mean(), (g["Ks"] - g["spot"]).quantile(0.1), (g["Ks"] - g["spot"]).quantile(0.9), g["credit"].mean(), (g["settle"] - g["spot"]).mean(), (g["settle"] - g["spot"]).std(), (g["settle"] - g["spot"]).max()))
    for shift in [-2, -1, 1, 2]:
        s = g["settle"].to_numpy() + shift; Ks = g["Ks"].to_numpy(); Kl = g["Kl"].to_numpy(); cr = g["credit"].to_numpy()
        val = np.clip(s - Ks, 0, None) - np.clip(s - Kl, 0, None); p2 = (cr - val) * 100 - 2 * FEE
        print(f"    settle shifted {shift:+d} pts: mean {p2.mean():+.1f} (was {pnl.mean():+.1f})")
    # every session shifted by the SPY-implied level instead of the print
    chk = pl.read_csv(f"{OUT}/settle_check.csv").select("date", "implied_1600")
    gg = g.join(chk, on="date", how="inner"); s = gg["implied_1600"].to_numpy(); Ks = gg["Ks"].to_numpy(); Kl = gg["Kl"].to_numpy(); cr = gg["credit"].to_numpy()
    val = np.clip(s - Ks, 0, None) - np.clip(s - Kl, 0, None); p2 = (cr - val) * 100 - 2 * FEE
    print(f"    settled at the SPY-implied 16:00 level instead (n {gg.height}): mean {p2.mean():+.1f} (was {gg['pnl'].mean():+.1f})")
    cum = np.cumsum(pnl); print("    equity by quarter-ends:", [(g['date'][i], round(cum[i])) for i in range(len(pnl)) if i % max(len(pnl) // 8, 1) == 0 or i == len(pnl) - 1])
