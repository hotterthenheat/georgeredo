"""Compass Phase 3, Hypothesis E. Rebuild SPY's scan-minute table for EVERY full session (Hypothesis D's build.py took every
second session) with Hypothesis D's own feature code, read-only: lib.session_rows from
../../Compass phase 2/hyp_d_vol_breakout/lib.py (which reuses the audit's sweeplib). Nothing there is edited: the scan
list is extended from this script (lib.SCAN is a module global that session_rows reads) so that 15:30 (m = 360), the last
of this test's scan times, gets its features and t2 target too; 09:35..15:25 every 5 minutes stay as Hypothesis D had them.
Writes out/minutes_SPY_all.parquet (rebuildable by this script, ~25 MB) and logs/build.log. Single process, one thread.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I build_minutes.py
"""
import os, sys, time
import numpy as np, polars as pl
HYP_D = '/home/user/georgeredo/research_notes/Compass phase 2/hyp_d_vol_breakout'
sys.path.insert(0, HYP_D)
import lib as L                                   # noqa: E402  (Hypothesis D's feature and pricing code, read-only)
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); LOGS = os.path.join(HERE, 'logs')
ROOT = 'SPY'
L.SCAN = list(range(5, 361, 5))                   # 09:35 .. 15:30 (72 scan minutes; Hypothesis D stopped at 15:25)

if __name__ == '__main__':
    days, volmat, volidx = L.load_days(ROOT); vs = L.vix_sessions()
    sess = L.sessions_of(ROOT)
    t0 = time.time(); frames = []; n_ok = 0; skipped = []
    for i, d in enumerate(sess):
        try:
            rows = L.session_rows(ROOT, d, days, volmat, volidx, L.vix_prev_close(d, vs))
        except Exception as ex:
            skipped.append((str(d), repr(ex)[:120])); rows = None
        if rows: frames.append(pl.DataFrame(rows, infer_schema_length=None)); n_ok += 1
        else: skipped.append((str(d), 'no rows (half day / short bars / no chain)'))
        if (i + 1) % 100 == 0: print(ROOT, i + 1, 'of', len(sess), f'{time.time() - t0:.0f}s', flush=True)
    E = pl.concat(frames, how='diagonal_relaxed')
    E = E.with_columns([pl.col(c).fill_nan(None) for c, t in E.schema.items() if t == pl.Float64])
    E.write_parquet(os.path.join(OUT, f'minutes_{ROOT}_all.parquet'), compression='zstd')
    msg = f'{ROOT} sessions on disk {len(sess)} kept {n_ok} skipped {len(skipped)} rows {E.height} cols {E.width} scan minutes {len(L.SCAN)} {time.time() - t0:.0f}s'
    print(msg, flush=True)
    with open(os.path.join(LOGS, 'build.log'), 'w') as fh:
        fh.write(msg + '\n')
        for d, why in skipped: fh.write(f'{d}\t{why}\n')
