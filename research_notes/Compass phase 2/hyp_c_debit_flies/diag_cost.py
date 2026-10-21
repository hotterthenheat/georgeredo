"""Diagnostic (friction, not a selection): what a structure costs to open and close at once.
For each structure the ROUND TRIP = (debit paid at e) - (bid-side mark at the first quoted minute after e), as a share of
the debit; the naked contract's is (ask - bid at e+1) / ask on the same entries. Also the share of the debit that is
bid-ask at entry itself: (ask_long - bid_long) + (ask_short - bid_short) over the debit. Both periods pooled (no choice is
made on it). Writes out/diag_cost.csv.
"""
import os, sys, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
rows = []
T = pl.read_parquet(os.path.join(OUT, 'spreads_trades.parquet')).filter(pl.col('exit') == 'hold')
for root in PRODUCTS:
    S = pl.read_parquet(os.path.join(OUT, f'spreads_{root}.parquet')).filter(pl.col('ok'))
    L = pl.read_parquet(os.path.join(OUT, f'legs_{root}.parquet'))
    lkey = {(s, sd, float(k)): i for i, (s, sd, k) in enumerate(zip(L['session'], L['side'], L['strike']))}
    LB = np.round(np.array(L['bid'].to_list(), dtype=np.float64), 4); LA = np.round(np.array(L['ask'].to_list(), dtype=np.float64), 4)
    naked = pl.read_parquet(os.path.join(AUDIT_EXITS, 'out', f'paths_{root}.parquet'), columns=['session', 'universe', 'side', 'entry_m', 'entry_ask', 'bid', 'ask']).filter(pl.col('entry_m') > 0)
    nk = {(s, u, sd, int(e)): (a, np.round(np.array(b, float), 4), np.round(np.array(k, float), 4)) for s, u, sd, e, a, b, k in zip(naked['session'], naked['universe'], naked['side'], naked['entry_m'], naked['entry_ask'], naked['bid'], naked['ask'])}
    for r in S.iter_rows(named=True):
        iL = lkey[(r['session'], r['side'], float(r['k_long']))]; iS = lkey[(r['session'], r['side'], float(r['k_short']))]
        e = int(r['entry_m']); mark = LB[iL] - LA[iS]
        after = [m for m in range(e + 1, min(e + 6, 391)) if not np.isnan(mark[m])]
        if not after: continue
        m1 = after[0]
        key = (r['session'], r['universe'], r['side'], e)
        if key not in nk: continue
        a0, nb, na = nk[key]
        nafter = [m for m in range(e + 1, min(e + 6, 391)) if not np.isnan(nb[m])]
        if not nafter: continue
        rows.append(dict(product=root, universe=r['universe'], cell=r['cell'], debit=r['debit'], width=r['width'],
                         spread_rt=(r['debit'] - mark[m1]) / r['debit'], spread_ba_share=((r['ask_long'] - r['bid_long']) + (r['ask_short'] - r['bid_short'])) / r['debit'],
                         naked_rt=(a0 - nb[nafter[0]]) / a0, naked_ba_share=(a0 - nk[key][1][e]) / a0 if not np.isnan(nk[key][1][e]) else np.nan,
                         fee_share_spread=2 * 2 * FEE / (r['debit'] * 100), fee_share_naked=2 * FEE / (a0 * 100)))
D = pl.DataFrame(rows)
out = D.group_by('universe', 'product', 'cell').agg(pl.len().alias('n'), pl.col('debit').median().alias('med_debit'), pl.col('width').mean().alias('mean_width'),
        pl.col('spread_rt').median().alias('spread_roundtrip_med'), pl.col('spread_rt').mean().alias('spread_roundtrip_mean'), pl.col('spread_ba_share').median().alias('spread_ba_at_entry_med'),
        pl.col('naked_rt').median().alias('naked_roundtrip_med'), pl.col('naked_rt').mean().alias('naked_roundtrip_mean'),
        pl.col('fee_share_spread').median().alias('fees_rt_share_spread_med'), pl.col('fee_share_naked').median().alias('fees_rt_share_naked_med')).sort('universe', 'product', 'cell')
out.write_csv(os.path.join(OUT, 'diag_cost.csv'))
with pl.Config(tbl_rows=100, tbl_cols=20, tbl_width_chars=250, float_precision=3): print(out)
