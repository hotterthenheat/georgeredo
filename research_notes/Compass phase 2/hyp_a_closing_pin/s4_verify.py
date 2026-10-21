"""Step 4: 50 random spreads re-derived from the raw chain files with separate plain-loop code (no common.py, no
s2_spreads.py): the quotes read row by row into a dict, the IV by scipy's brentq, the delta by scipy's norm, the strike
rules, the credit, the management scan and the settlement all written again. Reports the count of differences in the
short strike, the long strike, the credit, the exit minute and the P&L (to the cent). Writes out/verify_50.csv."""
import os, sys, math, random, numpy as np, polars as pl
from scipy.optimize import brentq
from scipy.stats import norm
RAW = "/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta"
OUT = "/home/user/georgeredo/research_notes/Compass phase 2/hyp_a_closing_pin/out"
FEE = 0.65
WINGS = {"SPXW": [5.0, 10.0, 25.0], "SPY": [1.0, 2.0, 5.0]}

def minute(ts): return ts.hour * 60 + ts.minute

def read_chain(sym, date):
    q = {}
    for r in pl.read_parquet(f"{RAW}/data_full/chains/{sym}/{date}.parquet").iter_rows(named=True):
        t = minute(r["timestamp"])
        if t >= 900: q[(t, float(r["strike"]), r["right"])] = (None if r["bid"] is None else round(float(r["bid"]), 4), None if r["ask"] is None else round(float(r["ask"]), 4))
    return q

def underlying(sym, date):
    if sym == "SPXW":
        return {minute(r["timestamp"]): float(r["price"]) for r in pl.read_parquet(f"{RAW}/data/index/SPX/{date}.parquet").iter_rows(named=True) if r["price"] is not None}
    return {minute(r["timestamp"]): float(r["close"]) for r in pl.read_parquet(f"{RAW}/data/underlying/{sym}/{date}.parquet").iter_rows(named=True) if r["close"] is not None}

def bs(S, K, sig, T, right):
    d1 = (math.log(S / K) + 0.5 * sig * sig * T) / (sig * math.sqrt(T)); d2 = d1 - sig * math.sqrt(T)
    return S * norm.cdf(d1) - K * norm.cdf(d2) if right == "CALL" else K * norm.cdf(-d2) - S * norm.cdf(-d1)

def iv_delta(mid, S, K, T, right):
    intr = max(S - K, 0) if right == "CALL" else max(K - S, 0)
    if mid - intr <= 0.01: return None, None
    try: sig = brentq(lambda s: bs(S, K, s, T, right) - mid, 1e-4, 20.0, xtol=1e-10)
    except ValueError: return None, None
    d1 = (math.log(S / K) + 0.5 * sig * sig * T) / (sig * math.sqrt(T))
    return sig, (norm.cdf(d1) if right == "CALL" else norm.cdf(d1) - 1)

def rederive(sym, date, t, side, rule, wing, mgmt):
    q = read_chain(sym, date); u = underlying(sym, date)
    S = u[t] if sym == "SPXW" else u[t - 1]
    T = (960 - t) / (365.0 * 1440.0)
    if sym == "SPXW":
        settle = None
        for m in range(960, 950, -1):
            if m in u: settle = u[m]; break
    else: settle = u[960] if 960 in u else u[959]
    strikes = sorted(set(k for (tt, k, r) in q if tt == t))
    def pick(right):
        otm = [k for k in strikes if (k > S if right == "CALL" else k < S)]
        otm.sort(reverse=(right == "PUT"))
        if rule.startswith("d"):
            target = int(rule[1:]) / 100
            for k in otm:
                b, a = q.get((t, k, right), (None, None))
                if b is None or a is None or a <= 0: continue
                sig, d = iv_delta(0.5 * (b + a), S, k, T, right)
                if d is not None and abs(d) <= target: return k
            return None
        mult = float(rule[1:]); katm = min(strikes, key=lambda k: abs(k - S))
        bc, ac = q.get((t, katm, "CALL"), (None, None)); bp, ap = q.get((t, katm, "PUT"), (None, None))
        if None in (bc, ac, bp, ap): return None
        M = 0.5 * (bc + ac) + 0.5 * (bp + ap); bound = S + mult * M if right == "CALL" else S - mult * M
        for k in otm:
            if (k > bound if right == "CALL" else k < bound):
                b, a = q.get((t, k, right), (None, None))
                if b is not None and a is not None and a > 0: return k
        return None
    def vertical(right):
        Ks = pick(right)
        if Ks is None: return None
        Kl = Ks + wing if right == "CALL" else Ks - wing
        if (t, Kl, right) not in q: return None
        bs_, _ = q[(t, Ks, right)]; _, al = q[(t, Kl, right)]
        if bs_ is None or al is None: return None
        credit = round(bs_ - al, 4)
        if credit < 0.05: return None
        intr = lambda K, s: max(s - K, 0) if right == "CALL" else max(K - s, 0)
        if mgmt != "hold":
            for m in range(t + 1, 960):
                a_s = q.get((m, Ks, right), (None, None))[1]; b_l = q.get((m, Kl, right), (None, None))[0]
                if a_s is None: continue
                b_l = 0.0 if b_l is None else b_l
                cost = a_s - b_l
                if (mgmt == "tp50" and cost <= 0.5 * credit) or (mgmt == "stop2x" and cost >= 2 * credit):
                    if b_l > 0: return Ks, Kl, credit, m, (credit - cost) * 100 - 4 * FEE
                    return Ks, Kl, credit, m, (credit - a_s + intr(Kl, settle)) * 100 - 3 * FEE
        val = intr(Ks, settle) - intr(Kl, settle)
        return Ks, Kl, credit, 960, (credit - val) * 100 - 2 * FEE
    if side == "IC":
        c, p = vertical("CALL"), vertical("PUT")
        if c is None or p is None: return None
        return c[0], c[1], c[2] + p[2], max(c[3], p[3]), c[4] + p[4]
    return vertical(side)

if __name__ == "__main__":
    rows = pl.concat([pl.read_parquet(f"{OUT}/spread_rows_{s}.parquet") for s in ["SPXW", "SPY"]])
    random.seed(2026); idx = random.sample(range(rows.height), 50)
    out = []; ndiff = {"Ks": 0, "Kl": 0, "credit": 0, "exit_t": 0, "pnl": 0, "missing": 0}
    for i in idx:
        r = rows.row(i, named=True)
        got = rederive(r["sym"], r["date"], r["t"], r["side"], r["rule"], r["wing"], r["mgmt"])
        rec = {k: r[k] for k in ["sym", "date", "t", "side", "rule", "wing", "mgmt", "Ks", "Kl", "credit", "exit_t", "pnl"]}
        if got is None:
            ndiff["missing"] += 1; rec.update({"v_Ks": None, "v_Kl": None, "v_credit": None, "v_exit_t": None, "v_pnl": None, "same": False})
        else:
            Ks, Kl, credit, ex, pnl = got
            same = (Ks == r["Ks"]) and (Kl == r["Kl"]) and abs(credit - r["credit"]) < 1e-6 and ex == r["exit_t"] and abs(pnl - r["pnl"]) < 0.005
            ndiff["Ks"] += Ks != r["Ks"]; ndiff["Kl"] += Kl != r["Kl"]; ndiff["credit"] += abs(credit - r["credit"]) >= 1e-6
            ndiff["exit_t"] += ex != r["exit_t"]; ndiff["pnl"] += abs(pnl - r["pnl"]) >= 0.005
            rec.update({"v_Ks": Ks, "v_Kl": Kl, "v_credit": credit, "v_exit_t": ex, "v_pnl": pnl, "same": same})
        out.append(rec)
    o = pl.DataFrame(out); o.write_csv(f"{OUT}/verify_50.csv")
    print("50 spreads re-derived; identical:", int(o["same"].sum()), "differences:", ndiff)
    with pl.Config(tbl_rows=60, tbl_cols=20, tbl_width_chars=250): print(o.filter(~pl.col("same")))
