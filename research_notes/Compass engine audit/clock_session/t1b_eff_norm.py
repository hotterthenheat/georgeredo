"""Test 1 addendum: the efficiency ratio against its random-walk null.
For a random walk of n one-minute steps, E|net| / E(sum|step|) ~ 1/sqrt(n), so eff * sqrt(n_bars) ~ 1 (1 = no drift
structure, < 1 = mean-reverting / pinned, > 1 = trending). Reads out/t1_window_rows.parquet."""
import sys, numpy as np
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass engine audit/clock_session")
from common import *
NB = {"opening_drive": 25, "morning_reversal": 40, "mid_morning": 85, "lunch": 75, "pre_power": 30, "dealer_hour": 75, "power_hour": 30, "settlement": 30}
df = pl.read_parquet(f"{OUT}/t1_window_rows.parquet")
rows = []
for sym in ["SPY", "QQQ", "IWM", "ALL"]:
    for per in ["ctx", "fit", "oos"]:
        for w, n in NB.items():
            d = df.filter((pl.col("window") == w) & (pl.col("period") == per))
            if sym != "ALL": d = d.filter(pl.col("sym") == sym)
            v = d["eff"].to_numpy() * np.sqrt(n); lo, hi = boot_ci(v, d["date"].to_numpy())
            rows.append({"sym": sym, "period": per, "window": w, "n": d.height, "eff_norm": float(v.mean()), "lo": lo, "hi": hi})
out = pl.DataFrame(rows); out.write_csv(f"{OUT}/t1b_eff_norm.csv")
for r in out.iter_rows(named=True): print(f"{r['sym']:4} {r['period']:3} {r['window']:16} n={r['n']:5} eff*sqrt(n)={r['eff_norm']:.3f} [{r['lo']:.3f},{r['hi']:.3f}]")
