"""Build the per-scan-minute table for one product: features known at the minute, the three targets, and every
structure's trades under every exit. Session by session, two worker processes; streams nothing larger than one
session's chain. Output: out/minutes_<ROOT>.parquet (rebuildable from the raw files by this script).
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I build.py SPY              # whole product
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I build.py SPY 2024-06-03   # one session, printed
"""
import datetime as dt, os, sys, time
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L

_G = {}
def _init(root):
    _G['days'], _G['volmat'], _G['volidx'] = L.load_days(root); _G['root'] = root; _G['vs'] = L.vix_sessions()
def _work(d):
    try:
        vp = L.vix_prev_close(d, _G['vs'])
        return L.session_rows(_G['root'], d, _G['days'], _G['volmat'], _G['volidx'], vp)
    except Exception as ex:
        print('FAILED', _G['root'], d, repr(ex), flush=True); return None

def run_product(root, workers=1, limit=None, step=1):
    """single process by default (the four cores are shared); STEP=2 takes every second session, stated in the notes"""
    sess = L.sessions_of(root)[::step]
    if limit: sess = sess[:limit]
    t0 = time.time(); frames = []; n_ok = 0
    if workers == 1:
        _init(root); it = map(_work, sess)
    else:
        import multiprocessing as mp
        pool = mp.get_context('spawn').Pool(workers, initializer=_init, initargs=(root,)); it = pool.imap(_work, sess, chunksize=4)
    for i, rows in enumerate(it):
        if rows: frames.append(pl.DataFrame(rows, infer_schema_length=None)); n_ok += 1
        if (i + 1) % 100 == 0: print(root, i + 1, 'of', len(sess), f'{time.time() - t0:.0f}s', flush=True)
    if workers != 1: pool.close(); pool.join()
    E = pl.concat(frames, how='diagonal_relaxed')
    E = E.with_columns([pl.col(c).fill_nan(None) for c, t in E.schema.items() if t == pl.Float64])
    E.write_parquet(os.path.join(L.OUT, f'minutes_{root}.parquet'), compression='zstd')
    print(root, 'sessions taken (every', step, 'th)', len(sess), 'kept', n_ok, 'rows', E.height, 'cols', E.width, f'{time.time() - t0:.0f}s', flush=True)

if __name__ == '__main__':
    root = sys.argv[1]
    if len(sys.argv) == 3:
        _init(root)
        t0 = time.time(); rows = _work(dt.date.fromisoformat(sys.argv[2])); print(f'{time.time() - t0:.2f}s', len(rows), 'rows')
        df = pl.DataFrame(rows, infer_schema_length=None)
        pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_rows(80)
        print(df.select('m', 'spot', 'ret5', 'rng30', 'range_pos', 'day_move_atr', 'rv_session', 'vix', 'vix_chg_prev', 'rel_vol', 'straddle', 'straddle_rel', 'implied30', 'mv30_bps', 't1', 't2', 't3'))
        print(df.select('m', 'atm_K', 'str_debit', 'str_h30_net', 'str_h60_net', 'str_trail_m', 'str_trail_net', 'str_settle_net', 'str_ri_m', 'str_ri_net', 'sg10_K', 'sg10_dc', 'sg10_debit', 'sg10_settle_net', 'sg20_K', 'sg20_debit', 'dir_right', 'dir_K', 'dir_debit', 'dir_h30_net', 'dir_trail_net'))
        print([c for c in df.columns if c.startswith('oddir') or 'e0955' in c or 'e1030' in c])
        print(df.filter(pl.col('m') == 5).select([c for c in df.columns if c.startswith('oddir') or 'e0955' in c or 'e1030' in c]))
    else:
        run_product(root, workers=int(os.environ.get('WORKERS', '1')), limit=int(os.environ['LIMIT']) if 'LIMIT' in os.environ else None, step=int(os.environ.get('STEP', '1')))
