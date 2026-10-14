#!/usr/bin/env python3
"""Data diagnostics over the simulated trades: ATM fallbacks (13:00-style ATM strike outside the stored band), forward-filled exit
rows, settlement fallbacks, legs left to settle under E1, exit reasons.  Writes results/diagnostics.csv."""
import os, sys, glob
import numpy as np, pandas as pd, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim  # noqa: E402
OUT = os.environ.get('HWR_OUT', sim.L.SP + '/hwr_grid/spxw'); RES = os.environ.get('RES_DIR', os.path.join(HERE, 'results'))
fs = sorted(glob.glob(OUT + '/trades/*.parquet'))
q = pl.concat([pl.read_parquet(f, columns=['date', 'entry', 'cell', 'tp', 'stop', 'exit', 'spot', 'kc', 'kp', 'how', 'legs_left', 'ffill_exit', 'settle_flag', 'wing_bid0', 'em'])
               .filter(pl.col('entry').is_in(sim.ENTRIES)) for f in fs])
q = q.with_columns(pl.when(pl.col('date') <= '2024-12-31').then(pl.lit('TRAIN')).otherwise(pl.lit('TEST')).alias('period'))
rows = []
a = q.filter((pl.col('cell') == 'N0.0') & (pl.col('tp') == 0) & (pl.col('stop') == 0) & (pl.col('exit') == 'E2'))
a = a.with_columns((pl.col('kc') != (pl.col('spot') / 5).round(0) * 5).alias('atm_fb'))
for (p, e), g in a.group_by(['period', 'entry']):
    rows.append(dict(metric='ATM strike outside band (nearest stored strike used)', period=p, entry=e, value=int(g['atm_fb'].sum()), of=g.height,
                     detail=' '.join(sorted(g.filter(pl.col('atm_fb'))['date'].to_list())[:20])))
    rows.append(dict(metric='EM median (points)', period=p, entry=e, value=float(g['em'].median()), of=g.height, detail=''))
    rows.append(dict(metric='settlement fallback (no 16:00 print)', period=p, entry=e, value=int((g['settle_flag'] != 'ok').sum()), of=g.height, detail=''))
b = q.filter(pl.col('exit') == 'E1')
for (p, c), g in b.group_by(['period', 'cell']):
    t = g.filter(pl.col('how') == 'time')
    rows.append(dict(metric='E1 time exits: mean legs left to settle', period=p, entry=c, value=float(t['legs_left'].mean()) if t.height else np.nan, of=t.height, detail=''))
    rows.append(dict(metric='exit rows forward-filled (share of trades)', period=p, entry=c, value=float((g['ffill_exit'] > 0).mean()), of=g.height, detail=''))
D = pd.DataFrame(rows).sort_values(['metric', 'period', 'entry']); D.to_csv(os.path.join(RES, 'diagnostics.csv'), index=False)
print(D.to_string())
