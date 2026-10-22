"""
b_exits.py — Phase B's extra exits on the 0DTE base trades (the same mechanics as X1 and X3, prereg 3.2 family 5, other
parameters): a time exit at 12:00, 13:00 and 15:00 (entries before that minute, sold at that row's bid with the 10-minute
fallback; SPXW with its exit fee), and the implied-move target at 0.25 and 0.5 IM (the first bar whose close reaches
S_entry ± k × IM, sold at the next row's bid, else the fixed exit). Keyed by the trade's natural key.

  POLARS_MAX_THREADS=1 python3 -I b_exits.py expl|hold
"""
from __future__ import annotations

import multiprocessing as mp
import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402
import build_0dte as B0  # noqa: E402

KEY = ['name', 'day', 'm', 'eb', 'strike', 'right', 'sb']
TIMES = {'t1200': C.mi('12:00'), 't1300': C.mi('13:00'), 't1500': C.mi('15:00')}
FRACS = {'im025': 0.25, 'im050': 0.50}


def one(args):
    nm, d, rows, split = args
    C.set_split(split)
    K, Bg, Ag = B0.grid(C.chain_0dte_path(nm, d))
    c = C.bars(nm, d)[2]
    out = []
    for t in rows:
        si = 0 if t['right'] == 'C' else 1
        i = int(np.where(np.abs(K - t['strike']) < 1e-6)[0][0])
        B, A = Bg[si, i], Ag[si, i]
        m = t['m']
        o = {k: t[k] for k in KEY}
        for lab, X in TIMES.items():
            if m < X:
                px, _ = B0.exit_bid(B, A, X, m)
                o['r_' + lab] = C.ret(nm, t['ask'], px, C.fee(nm, px))[0]
            else:
                o['r_' + lab] = None
        for lab, f in FRACS.items():
            S = t['S']
            if S is None or not np.isfinite(S):
                o['r_' + lab] = None
                continue
            lvl = S + f * t['IM'] if si == 0 else S - f * t['IM']
            hit = None
            if nm == 'SPXW':
                for pm in range(m + 1, C.FLAT + 1):
                    v = c[pm]
                    if np.isfinite(v) and ((si == 0 and v >= lvl) or (si == 1 and v <= lvl)):
                        hit = pm
                        break
            else:
                for bm in range(m, C.FLAT):
                    v = c[bm]
                    if np.isfinite(v) and ((si == 0 and v >= lvl) or (si == 1 and v <= lvl)):
                        hit = bm + 1
                        break
            if hit is None:
                o['r_' + lab] = t['r']
            else:
                px, _ = B0.exit_bid(B, A, hit, m)
                o['r_' + lab] = C.ret(nm, t['ask'], px, C.fee(nm, px))[0]
        out.append(o)
    return out


def main():
    split = sys.argv[1]
    C.set_split(split)
    T = pl.read_parquet(C.WORK / split / 'trades_with_inputs.parquet').filter(pl.col('eb') == '0DTE')
    jobs = [(nm, d, g.select(KEY + ['ask', 'S', 'IM', 'r']).to_dicts(), split) for (nm, d), g in T.group_by('name', 'day')]
    rows = []
    with mp.get_context('spawn').Pool(3) as pool:
        for r in pool.imap_unordered(one, jobs, chunksize=4):
            rows += r
    df = pl.DataFrame(rows, infer_schema_length=None).with_columns([pl.col(c).cast(pl.Float64) for c in
                                                                     ['r_' + k for k in list(TIMES) + list(FRACS)]])
    C.write_parquet(df, C.WORK / split / 'b_exits.parquet')
    print('b_exits', split, df.height, flush=True)


if __name__ == '__main__':
    main()
