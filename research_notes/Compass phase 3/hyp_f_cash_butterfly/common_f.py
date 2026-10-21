"""Compass Phase 3, Hypothesis F: shared constants. Everything structural (chain reading, the session frame, the
intrinsic settlement, the session bootstrap and the cell statistics) is IMPORTED from Hypothesis C's common.py,
unchanged, so this test is the same arithmetic as C with a fill model added.

C's conventions (kept): minute m = 0 is 09:30; a bar stamped t closes at t+1; a chain row stamped t is the quote at t;
spot at quote minute m = the close of the ETF bar stamped m-1; half days dropped. A long leg is bought at the ask, a
short leg sold at the bid (the NBBO case, k = 0); $0.65 a leg each way; a leg expiring worthless pays no closing fee;
a leg in the money at expiry settles at intrinsic on the 16:00 close (the bar stamped 15:59) with no assignment or
exercise fee assumed. Minimum debit (max risk) $0.05, judged on the NBBO structure so that the sample is the same
at every k. One lot. Fit 2022-11 -> 2024-12, OOS 2025-01 -> 2026-10-09.

The fill model (F's addition): for a long call / long put fly
    debit_k = D_nbbo - k * (D_nbbo - D_mid) + 4 * stress        k in {0, 0.25, 0.5}, stress in {0, 0.01, 0.02} $ a leg
    D_nbbo = ask(K0-W) + ask(K0+W) - 2 bid(K0);  D_mid = mid(K0-W) + mid(K0+W) - 2 mid(K0)
    pnl = (payoff - debit_k) * 100 - 4 * 0.65;   pct = pnl / (max(debit_k, 0.05) * 100)   (the floor is counted)
for the iron fly (sell the K0 straddle at the bid, buy the K0-W put and the K0+W call at the ask)
    credit_k = C_nbbo + k * (C_mid - C_nbbo) - 4 * stress;  risk_k = W - credit_k
    pnl = (credit_k + payoff) * 100 - 4 * 0.65;  pct = pnl / (risk_k * 100)
k > 0 is an ASSUMPTION about how a complex order fills against the package book, not an observation; the NBBO legs are
observed. 'gross' = the mid-to-mid result with no fees, (payoff - D_mid) * 100; friction = gross - pnl(k = 0, stress 0).
"""
import os, sys
C_DIR = '/home/user/georgeredo/research_notes/Compass phase 2/hyp_c_debit_flies'
sys.path.insert(0, C_DIR)
from common import (RAW, FEE, MIN_DEBIT, SPLIT, FLY_TIMES, NMIN, read_chain, session_frame, intrinsic, boot_ci, cell_stats, fmt,
                    period_of, mcol, to_arr)   # noqa: F401  (C's helpers, unchanged)
C_OUT = os.path.join(C_DIR, 'out')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out'); LOGS = os.path.join(HERE, 'logs')
PRODUCTS = ['SPY', 'QQQ']
W = 5.0
KS = [0.0, 0.25, 0.5]
STRESSES = [0.0, 0.01, 0.02]
FORMS = ['call', 'put', 'iron']
OOS_END = '2026-10-09'
