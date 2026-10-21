"""The SPXW settlement proxy checked: the 16:00 SPX print against SPY's 16:00 close x (SPX / SPY at 15:59), every full
SPXW session with SPY bars (2022-11-11 on). Also the last-minute move (15:59 -> 16:00 print) and the share of sessions
where the proxy and the SPY-implied level differ by more than 1, 2 and 5 points. Writes out/settle_check.csv and prints
the distribution. The official SPXW settlement (the exchange's closing value from the constituents' closing auctions) is
not on disk; this bounds how far the proxy may sit from a level SPY's own close implies, not the official figure itself."""
import sys, numpy as np, polars as pl
sys.path.insert(0, "/home/user/georgeredo/research_notes/Compass phase 2/hyp_a_closing_pin")
from common import *
rows = []
for date in sessions("chains", "SPXW"):
    spx = load_bars("SPX", date); spy = load_bars("SPY", date)
    if spx is None or spy is None or is_half_day(spx) or is_half_day(spy): continue
    p = spx["close"]; c = spy["close"]
    p1559, p1600 = p[959 - 570], p[960 - 570]
    spy1559 = c[959 - 570]        # the bar stamped 15:59 closes at 16:00 -> SPY at 16:00
    spy1558 = c[958 - 570]        # the bar stamped 15:58 closes at 15:59 -> SPY at 15:59
    spy1600 = c[960 - 570] if np.isfinite(c[960 - 570]) else spy1559
    if not all(np.isfinite([p1559, p1600, spy1558, spy1559])): continue
    ratio = p1559 / spy1558
    rows.append({"date": date, "period": period(date), "spx_1559": p1559, "spx_1600": p1600, "spy_1600": spy1600, "ratio_1559": ratio,
                 "implied_1600": spy1600 * ratio, "diff_pts": p1600 - spy1600 * ratio, "last_min_move_pts": p1600 - p1559})
d = pl.DataFrame(rows); d.write_csv(f"{OUT}/settle_check.csv")
x = d["diff_pts"].to_numpy(); m = d["last_min_move_pts"].to_numpy()
print("sessions", d.height, d["date"].min(), d["date"].max())
print("16:00 print - SPY-implied (pts): mean %.3f median %.3f sd %.3f p5 %.2f p95 %.2f |diff|>1: %.1f%% >2: %.1f%% >5: %.1f%% max|diff| %.2f on %s" % (
    x.mean(), np.median(x), x.std(), np.percentile(x, 5), np.percentile(x, 95), (np.abs(x) > 1).mean() * 100, (np.abs(x) > 2).mean() * 100, (np.abs(x) > 5).mean() * 100, np.abs(x).max(), d["date"][int(np.argmax(np.abs(x)))]))
print("15:59 -> 16:00 print move (pts): mean %.3f median|.| %.3f sd %.3f p1 %.2f p99 %.2f |move|>5: %.1f%%" % (m.mean(), np.median(np.abs(m)), m.std(), np.percentile(m, 1), np.percentile(m, 99), (np.abs(m) > 5).mean() * 100))
for per in ["fit", "oos"]:
    y = d.filter(pl.col("period") == per)["diff_pts"].to_numpy()
    print(per, "n", y.size, "mean %.3f sd %.3f |diff|>2: %.1f%%" % (y.mean(), y.std(), (np.abs(y) > 2).mean() * 100))
