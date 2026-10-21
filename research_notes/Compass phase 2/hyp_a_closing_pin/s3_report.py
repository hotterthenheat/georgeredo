"""Step 3: the cells. `python3 s3_report.py fit` reads 2022-2024 alone and prints the pre-registered pick;
`python3 s3_report.py oos` reads everything (run only after the pick is written into the notes).

Cell = (sym, structure side [CALL | PUT | IC], rule, wing, entry t, mgmt, cut [Q12 | Q345 | all], period).
Cut: moc_mag at the entry checkpoint against the FIT-period 40% cut per name and checkpoint (out/moc_quintile_cuts.csv):
Q12 = below it, Q345 = at or above it; 'all' = every scored session (the same structure sold every session). Sessions
without a score (the first 20 of a name, or a session with fewer than 15 of the 20 prior) are in no cut.
Per cell: N, mean $ a spread, mean % of max risk (per trade pnl / (width x 100 - credit x 100)), win rate, average win and
loss, the share of full losses (pnl <= -95% of max risk), p5 / p1 / worst and its session, the profit factor, the max
drawdown and the longest losing streak of the 1-lot sequence in date order, the session-bootstrap 95% CI of the mean $
and of the mean %, the mean without the best 5 sessions, by year, the total and the total without the worst session.
The paired difference Q12 - Q345 and Q12 - all with a bootstrap CI goes to out/cells_diff_<stage>.csv.

THE PRE-REGISTERED PICK (the rule, written before any cell was read; fit cells only; entries 15:00 and 15:30 only,
15:45 is a check; cut Q12 only - the hypothesis is the signal's):
  eligible: N >= 150; the fit CI of the mean % of max risk excludes zero from above; mean without the best 5 sessions
  > 0; every fit calendar year with >= 30 trades has a profit factor > 1; the fit difference Q12 - Q345 in % of max
  risk > 0 (the signal must add over the unconditional sale).
  pick: among the eligible, the highest LOWER BOUND of the fit CI of the mean % of max risk; one pick a name, SPXW primary.
"""
import sys, json, numpy as np, polars as pl
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass phase 2/hyp_a_closing_pin")
from common import *

def cell_stats(d):
    """d: polars frame of one cell sorted by date. Returns a dict."""
    pnl = d["pnl"].to_numpy(); risk = d["max_risk"].to_numpy(); dates = d["date"].to_numpy()
    pct = pnl / risk * 100
    n = pnl.size
    if n == 0: return None
    wins = pnl > 0; losses = pnl < 0
    cum = np.cumsum(pnl); peak = np.maximum.accumulate(cum); dd = float((peak - cum).max())
    streak = best = 0
    for x in pnl:
        streak = streak + 1 if x < 0 else 0; best = max(best, streak)
    lo, hi = boot_ci(pnl, dates); plo, phi = boot_ci(pct, dates)
    order = np.argsort(pnl); best5 = set(order[-5:].tolist())
    keep = np.array([i not in best5 for i in range(n)])
    by = {}
    for y in sorted(set(x[:4] for x in dates)):
        m = np.array([x.startswith(y) for x in dates]); by[y] = (int(m.sum()), float(pnl[m].mean()), float(pnl[m].sum()), float(pnl[m][pnl[m] > 0].sum() / max(-pnl[m][pnl[m] < 0].sum(), 1e-9)))
    iw = int(np.argmin(pnl))
    return {"n": n, "sessions": int(np.unique(dates).size), "mean_usd": float(pnl.mean()), "ci_lo": lo, "ci_hi": hi,
            "mean_pct_risk": float(pct.mean()), "pct_ci_lo": plo, "pct_ci_hi": phi,
            "win_rate": float(wins.mean()), "avg_win": float(pnl[wins].mean()) if wins.any() else 0.0, "avg_loss": float(pnl[losses].mean()) if losses.any() else 0.0,
            "full_loss_share": float((pnl <= -0.95 * risk).mean()), "p5": float(np.percentile(pnl, 5)), "p1": float(np.percentile(pnl, 1)),
            "worst": float(pnl.min()), "worst_date": str(dates[iw]), "profit_factor": float(pnl[wins].sum() / max(-pnl[losses].sum(), 1e-9)),
            "max_dd": dd, "longest_losing_streak": best, "wo_best5": float(pnl[keep].mean()) if keep.any() else np.nan,
            "total": float(pnl.sum()), "total_wo_worst": float(pnl.sum() - pnl.min()), "credit_mean": float(d["credit"].mean()), "max_risk_mean": float(risk.mean()),
            "by_year": " ".join(f"{y}:{v[1]:+.1f}(n{v[0]},pf{v[3]:.2f})" for y, v in by.items())}

def diff_ci(a, da, b, db, n=2000, seed=11):
    rng = np.random.default_rng(seed)
    ua, ia = np.unique(da, return_inverse=True); ub, ib = np.unique(db, return_inverse=True)
    sa = np.bincount(ia, weights=a, minlength=ua.size); ca = np.bincount(ia, minlength=ua.size)
    sb = np.bincount(ib, weights=b, minlength=ub.size); cb = np.bincount(ib, minlength=ub.size)
    out = np.empty(n)
    for k in range(n):
        pa = rng.integers(0, ua.size, ua.size); pb = rng.integers(0, ub.size, ub.size)
        out[k] = sa[pa].sum() / max(ca[pa].sum(), 1) - sb[pb].sum() / max(cb[pb].sum(), 1)
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))

def load(stage):
    rows = pl.concat([pl.read_parquet(f"{OUT}/spread_rows_{s}.parquet") for s in ["SPXW", "SPY"]])
    sc = pl.read_parquet(f"{OUT}/moc_scores.parquet").select("sym", "date", "t", "moc_mag", "fwd_close_bp")
    cuts = pl.read_csv(f"{OUT}/moc_quintile_cuts.csv").select("sym", "t", "q40")
    rows = rows.join(sc, on=["sym", "date", "t"], how="left").join(cuts, on=["sym", "t"], how="left")
    rows = rows.filter(pl.col("moc_mag").is_not_null())
    rows = rows.with_columns(pl.when(pl.col("moc_mag") < pl.col("q40")).then(pl.lit("Q12")).otherwise(pl.lit("Q345")).alias("cut"))
    if stage == "fit": rows = rows.filter(pl.col("period") == "fit")
    return rows

def main(stage):
    rows = load(stage)
    keys = ["sym", "side", "rule", "wing", "t", "mgmt"]
    cells = []; diffs = []
    for key, g in rows.group_by(keys + ["period"], maintain_order=True):
        g = g.sort("date"); base = dict(zip(keys + ["period"], key))
        parts = {}
        for cut in ["Q12", "Q345", "all"]:
            d = g if cut == "all" else g.filter(pl.col("cut") == cut)
            s = cell_stats(d)
            if s is None: continue
            parts[cut] = d; cells.append({**base, "cut": cut, **s})
        if "Q12" in parts and "Q345" in parts:
            a, b = parts["Q12"], parts["Q345"]
            pa, pb = a["pnl"].to_numpy(), b["pnl"].to_numpy(); ra, rb = pa / a["max_risk"].to_numpy() * 100, pb / b["max_risk"].to_numpy() * 100
            da, db = a["date"].to_numpy(), b["date"].to_numpy()
            lo, hi = diff_ci(pa, da, pb, db); plo, phi = diff_ci(ra, da, rb, db)
            al = parts["all"]; pal = al["pnl"].to_numpy(); ral = pal / al["max_risk"].to_numpy() * 100
            diffs.append({**base, "n_q12": pa.size, "n_q345": pb.size, "mean_usd_q12": float(pa.mean()), "mean_usd_q345": float(pb.mean()), "diff_usd": float(pa.mean() - pb.mean()),
                          "diff_usd_ci_lo": lo, "diff_usd_ci_hi": hi, "mean_pct_q12": float(ra.mean()), "mean_pct_q345": float(rb.mean()), "diff_pct": float(ra.mean() - rb.mean()),
                          "diff_pct_ci_lo": plo, "diff_pct_ci_hi": phi, "mean_pct_all": float(ral.mean()), "q12_minus_all_pct": float(ra.mean() - ral.mean()),
                          "win_q12": float((pa > 0).mean()), "win_q345": float((pb > 0).mean()), "full_loss_q12": float((pa <= -0.95 * a["max_risk"].to_numpy()).mean()), "full_loss_q345": float((pb <= -0.95 * b["max_risk"].to_numpy()).mean())})
    cells = pl.DataFrame(cells).sort(keys + ["period", "cut"]); diffs = pl.DataFrame(diffs).sort(keys + ["period"])
    cells.write_csv(f"{OUT}/cells_{stage}.csv"); diffs.write_csv(f"{OUT}/cells_diff_{stage}.csv")
    print("cells", cells.height, "diff rows", diffs.height)
    if stage == "fit":
        pick(cells, diffs)

def pick(cells, diffs):
    f = cells.filter((pl.col("period") == "fit") & (pl.col("cut") == "Q12") & pl.col("t").is_in([900, 930]) & (pl.col("n") >= 150)
                     & (pl.col("pct_ci_lo") > 0) & (pl.col("wo_best5") > 0))
    keys = ["sym", "side", "rule", "wing", "t", "mgmt"]
    f = f.join(diffs.filter(pl.col("period") == "fit").select(keys + ["diff_pct", "diff_pct_ci_lo", "diff_pct_ci_hi", "mean_pct_q345", "mean_pct_all"]), on=keys, how="inner").filter(pl.col("diff_pct") > 0)
    def years_ok(s):
        for part in s.split():
            n = int(part.split("(n")[1].split(",")[0]); pf = float(part.split("pf")[1].rstrip(")"))
            if n >= 30 and pf <= 1: return False
        return True
    f = f.filter(pl.col("by_year").map_elements(years_ok, return_dtype=pl.Boolean)).sort("pct_ci_lo", descending=True)
    cols = keys + ["n", "mean_usd", "ci_lo", "ci_hi", "mean_pct_risk", "pct_ci_lo", "pct_ci_hi", "win_rate", "full_loss_share", "profit_factor", "wo_best5", "diff_pct", "diff_pct_ci_lo", "mean_pct_q345", "mean_pct_all", "by_year"]
    with pl.Config(tbl_rows=40, tbl_cols=30, tbl_width_chars=400, float_precision=2):
        print("ELIGIBLE (fit, Q12), best first:"); print(f.select(cols).head(40))
    picks = {}
    for sym in ["SPXW", "SPY"]:
        g = f.filter(pl.col("sym") == sym)
        if g.height: picks[sym] = {k: g[k][0] for k in keys}
    json.dump({"picks": picks, "n_eligible": f.height, "rule": "see s3_report.py docstring"}, open(f"{OUT}/pick.json", "w"), indent=1, default=str)
    print("PICKS:", json.dumps(picks, default=str))
    f.select(cols).write_csv(f"{OUT}/eligible_fit.csv")

if __name__ == "__main__":
    main(sys.argv[1])
