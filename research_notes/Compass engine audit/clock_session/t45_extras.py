"""Small tables quoted in the notes that the main scripts do not print: test 4 by moneyness and the share of nearest-ITM
contracts that end worthless; test 5's |move| by moc_mag quintile; the book's sign frequencies (test 3)."""
import sys, numpy as np
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass engine audit/clock_session")
from common import *
d = pl.read_parquet(f"{OUT}/t4_rows.parquet")
n = d.filter(pl.col("nearest"))
print(n.group_by(["sym", "period"]).agg(pl.len(), (pl.col("intr_close") == 0).mean().alias("ends_otm"), ((pl.col("intr_close") - pl.col("bid958")) < 0).mean().alias("bid_above_intr")).sort(["sym", "period"]))
d = d.with_columns(pl.when(pl.col("moneyness") < 0.001).then(pl.lit("a<0.1%")).when(pl.col("moneyness") < 0.002).then(pl.lit("b0.1-0.2%")).when(pl.col("moneyness") < 0.005).then(pl.lit("c0.2-0.5%")).otherwise(pl.lit("d0.5-1%")).alias("mb"))
t = d.group_by(["sym", "mb"]).agg(pl.len(), pl.col("ride_edge").mean().round(1).alias("mean"), pl.col("ride_edge").median().round(1).alias("median"), (pl.col("ride_edge") < 0).mean().round(2).alias("loses")).sort(["sym", "mb"])
t.write_csv(f"{OUT}/t4_by_moneyness.csv"); print(t)
s = pl.read_parquet(f"{OUT}/t5_scores.parquet").filter((pl.col("t") == 950) & pl.col("moc_mag").is_not_null() & pl.col("fwd_close_bp").is_not_null())
rows = []
for per in ["fit", "oos"]:
    x = s.filter(pl.col("period") == per); q = np.quantile(x["moc_mag"].to_numpy(), [0.2, 0.4, 0.6, 0.8])
    x = x.with_columns(pl.col("moc_mag").map_elements(lambda v: int(np.searchsorted(q, v)), return_dtype=pl.Int64).alias("q5"))
    tt = x.group_by("q5").agg(pl.len(), pl.col("fwd_close_bp").abs().mean().round(1).alias("abs_fwd_bp"), pl.col("fwd_close_bp").abs().median().round(1).alias("abs_fwd_med"), pl.col("fwd_close_bp").mean().round(1).alias("fwd_bp")).sort("q5")
    print(per, tt)
    rows += [{"period": per, "quintile": r[0], "n": r[1], "abs_fwd_bp_mean": r[2], "abs_fwd_bp_median": r[3], "fwd_bp_mean": r[4]} for r in tt.iter_rows()]
pl.DataFrame(rows).write_csv(f"{OUT}/t5_mag_quintiles.csv")
b = pl.read_csv(f"{OUT}/t3_book.csv")
print(b.group_by("ticker").agg(pl.len(), (pl.col("gex_net") > 0).mean().round(2).alias("share_gex_pos"), (pl.col("charm_net") > 0).mean().round(2).alias("share_charm_pos"), (pl.col("charm_pressure") > 2.4).mean().round(2).alias("share_cp_gt_2.4"), pl.col("charm_pressure").median().round(2).alias("cp_median")).sort("ticker"))
