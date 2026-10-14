#!/usr/bin/env python3
"""Simulate every session (PREREGISTRATION.md Part G): writes one trade file and one skip file per session.
Env: HWR_OUT (default <scratchpad>/hwr_grid/spxw), HWR_NWORK (default 2), HWR_START/HWR_END (session range).
Resumable: sessions whose output exists are skipped (delete the folder to recompute)."""
import os, sys, time, json
import polars as pl
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim  # noqa: E402

OUT = os.environ.get('HWR_OUT', sim.L.SP + '/hwr_grid/spxw')
os.makedirs(OUT + '/trades', exist_ok=True); os.makedirs(OUT + '/skips', exist_ok=True)
RAND = sim.random_minutes()


def work(d):
    ft, fs = f'{OUT}/trades/{d}.parquet', f'{OUT}/skips/{d}.parquet'
    if os.path.exists(ft) and os.path.exists(fs): return d, 'cached'
    try:
        rows, skips = sim.run_session(d, {k: RAND[(d, k)] for k in range(1, 6)})
    except FileNotFoundError as e:
        return d, f'missing: {e.filename}'
    pl.DataFrame(rows, infer_schema_length=None).write_parquet(ft + '.tmp', compression='zstd'); os.replace(ft + '.tmp', ft)
    pl.DataFrame(skips if skips else [dict(date=d, entry='', entry_hm='', cell='', reason='none')]).write_parquet(fs + '.tmp'); os.replace(fs + '.tmp', fs)
    return d, 'ok'


if __name__ == '__main__':
    ses = sim.regular_sessions(os.environ.get('HWR_START', '2022-05-13'), os.environ.get('HWR_END', '2026-10-09'))
    have = set(sim.L.sessions('chains', 'SPXW'))
    todo = [d for d in ses if d in have]
    missing = [d for d in ses if d not in have]
    t0 = time.time(); status = {}
    with Pool(int(os.environ.get('HWR_NWORK', '2'))) as p:
        for i, (d, st) in enumerate(p.imap(work, todo, chunksize=4)):
            status[d] = st
            if i % 100 == 0: print(i, d, st, round(time.time() - t0, 1), flush=True)
    json.dump(dict(sessions=len(ses), simulated=sum(v in ('ok', 'cached') for v in status.values()), missing_chain=missing,
                   errors={d: v for d, v in status.items() if v not in ('ok', 'cached')}, secs=round(time.time() - t0, 1)),
              open(OUT + '/run_status.json', 'w'), indent=1)
    print('done', len(todo), 'missing', len(missing), round(time.time() - t0, 1))
