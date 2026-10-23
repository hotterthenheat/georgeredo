#!/usr/bin/env python3
"""
attribution_h3.py — EXPLORATORY, NOT PRE-REGISTERED, written after the screen was read; changes no verdict. Splits the
exploration trades' loss into the spread paid and the condor's value change at the mid: for each trade in out/trades_expl.csv
(the quote-valued ones), the same four legs valued at their mids at P and at R, no fees. Writes out/attribution_expl.json.

    PYTHONDONTWRITEBYTECODE=1 python3 -I -B attribution_h3.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import h3common as H  # noqa: E402


def main():
    tr = pl.read_csv(H.OUT / 'trades_expl.csv', infer_schema_length=None).filter(pl.col('how') == 'quotes')
    mid_pnl, spread_cost = [], []
    for t in tr.iter_rows(named=True):
        xp = H.quotes(H.read(H.find_all(t['ticker'], t['P'])).filter(pl.col('expiration') == t['expiry']))
        xr = H.quotes(H.read(H.path(t['ticker'], t['R'], t['expiry'])))
        legs = (('C', t['Kcs'], -1), ('P', t['Kps'], -1), ('C', t['Kcl'], 1), ('P', t['Kpl'], 1))
        m0 = sum(s * sum(xp[(r, round(k, 4))]) / 2 for r, k, s in legs)
        m1 = sum(s * sum(xr[(r, round(k, 4))]) / 2 for r, k, s in legs)
        mid_pnl.append(100 * (m1 - m0))          # long-structure value change; the short condor earns −(m1 − m0)
        spread_cost.append(t['pnl'] + 100 * (m1 - m0))
    a = -np.array(mid_pnl)
    res = dict(note='exploratory, after the screen; no verdict', trades=len(a), mean_at_mid_no_fees=float(a.mean()),
               median_at_mid=float(np.median(a)), win_rate_at_mid=float((a > 0).mean()),
               mean_spread_and_fees=float(np.mean(spread_cost)),
               mean_pnl_after_costs=float(tr['pnl'].mean()))
    H.jdump(res, H.OUT / 'attribution_expl.json')
    print(json.dumps(res))


if __name__ == '__main__':
    main()
