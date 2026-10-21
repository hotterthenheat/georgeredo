"""Recompute the underlying's forward returns from the ENTRY minute (build_events measured them from the return bar r,
which for confirm=1 rows and the geometry entries is before the entry). Overwrites fwd_5/15/30/60/close and fwd_max30
in out/events_<P>.parquet: fade-direction bps from c[entry_m] to c[entry_m + h] (capped at the close).
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I fix_fwd.py
"""
import os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S

def fix(root):
    f = os.path.join(S.OUT, f'events_{root}.parquet'); E = pl.read_parquet(f)
    u = S.BAR_SOURCE[root]; out = {k: np.full(E.height, np.nan) for k in ('fwd_5', 'fwd_15', 'fwd_30', 'fwd_60', 'fwd_close', 'fwd_max30')}
    for d, idx in E.with_row_index('i').group_by('session').agg(pl.col('i')).iter_rows():
        arr, close_m, half = S.read_bars(u, d); c, h, l = arr['close'], arr['high'], arr['low']
        sub = E[idx]
        for i, m, side in zip(idx, sub['entry_m'].to_list(), sub['side'].to_list()):
            s = -1.0 if side == 'hi' else 1.0
            for hz in (5, 15, 30, 60):
                t = min(m + hz, close_m); out[f'fwd_{hz}'][i] = s * (c[t] - c[m]) / c[m] * 1e4
            out['fwd_close'][i] = s * (c[close_m] - c[m]) / c[m] * 1e4
            if m + 1 <= close_m:
                ext = np.nanmax(h[m + 1:min(m + 31, close_m + 1)]) if side == 'lo' else np.nanmin(l[m + 1:min(m + 31, close_m + 1)])
                out['fwd_max30'][i] = s * (ext - c[m]) / c[m] * 1e4
    E = E.with_columns(*[pl.Series(k, v) for k, v in out.items()])
    E.write_parquet(f, compression='zstd'); print(root, E.height, 'rows fixed', flush=True)

if __name__ == '__main__':
    for r in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['SPY', 'QQQ', 'IWM', 'SPXW']): fix(r)
