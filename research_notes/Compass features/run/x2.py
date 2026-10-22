"""
x2.py — the X2 exit (prereg 3.2, family 5; a GEX feature, run only when the GEX check passed): the call wall (the strike
with the largest call_gex) and the put wall (the most negative put_gex) of UW's greek-exposure/strike book of the session
before the entry session. A call takes the call wall as its level if it is above S_entry, a put the put wall if below;
otherwise the trade is not in the defined set. Exit mechanics as X1: 0DTE at the first bar stamped b ≥ m whose close reaches
the level, sold at the bid of row b + 1 (SPXW: the first SPX print p > m that reaches it, sold at row p), else the fixed
exit; multi-day at the first session after entry (to the fixed-exit session; 1–7 to the session before expiry) whose 15:59
close reaches it, sold at that session's EOD closing bid, else the fixed exit.

Reads $SP/features_work/<split>/trades_with_inputs.parquet; writes <split>/x2.parquet keyed by the trade's natural key.

  POLARS_MAX_THREADS=1 python3 -I x2.py expl
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402
import daily as D  # noqa: E402
import build_0dte as B0  # noqa: E402
import build_eod as BE  # noqa: E402

KEY = ['name', 'day', 'm', 'eb', 'strike', 'right', 'sb']


def main():
    split = sys.argv[1]
    C.set_split(split)
    T = pl.read_parquet(C.WORK / split / 'trades_with_inputs.parquet')
    T = T.filter(pl.col('name').is_in(list(C.INDEX)) & pl.col('S').is_not_null() & pl.col('S').is_finite())
    T = T.with_columns(pl.when(pl.col('right') == 'C').then(pl.col('cw')).otherwise(pl.col('pw')).alias('wall'))
    T = T.filter(pl.col('wall').is_not_null() & (((pl.col('right') == 'C') & (pl.col('wall') > pl.col('S')))
                                                 | ((pl.col('right') == 'P') & (pl.col('wall') < pl.col('S')))))
    out = []
    # 0DTE
    z = T.filter(pl.col('eb') == '0DTE')
    for (nm, d), g in z.group_by('name', 'day'):
        K, Bg, Ag = B0.grid(C.chain_0dte_path(nm, d))
        c = C.bars(nm, d)[2]
        for t in g.iter_rows(named=True):
            si = 0 if t['right'] == 'C' else 1
            i = int(np.where(np.abs(K - t['strike']) < 1e-6)[0][0])
            m, lvl = t['m'], t['wall']
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
                r2 = t['r']
            else:
                px, _ = B0.exit_bid(Bg[si, i], Ag[si, i], hit, m)
                r2, _ = C.ret(nm, t['ask'], px, C.fee(nm, px))
            out.append({**{k: t[k] for k in KEY}, 'x2_def': True, 'r_x2': r2, 'x2_hit': hit})
    # multi-day
    e = T.filter(pl.col('eb') != '0DTE')
    for (nm,), g in e.group_by('name'):
        rows = D.table(nm)['rows']
        req, todo = [], []
        for t in g.iter_rows(named=True):
            last = C.prev_session(t['expiry']) if t['eb'] == '1-7' else t['exit_day']
            checks = C.sessions_between(t['day'], last) if last and last > t['day'] else []
            hit = None
            for dd in checks:
                rr = rows.get(dd)
                v = rr['close1559'] if rr else None
                if v is None:
                    continue
                if (t['right'] == 'C' and v >= t['wall']) or (t['right'] == 'P' and v <= t['wall']):
                    hit = dd
                    break
            todo.append((t, hit))
            if hit:
                req.append((hit, t['listed'], t['strike'], t['right']))
        quote = {}
        if req:
            got = BE.eod_lookup(nm, pl.DataFrame(req, schema=['day', 'listed', 'strike', 'right'], orient='row').unique())
            quote = {(a, b, c_, d_): (x, y) for a, b, c_, d_, x, y in got.iter_rows()}
        for t, hit in todo:
            r2 = t['r']
            if hit:
                q = quote.get((hit, t['listed'], t['strike'], t['right']))
                if q is not None:
                    b_, a_ = q
                    px = float(b_) if (b_ is not None and b_ > 0 and a_ is not None and a_ > 0 and a_ >= b_) else 0.0
                    r2, _ = C.ret(nm, t['ask'], px, C.fee(nm, px))
            out.append({**{k: t[k] for k in KEY}, 'x2_def': True, 'r_x2': r2, 'x2_hit': None if hit is None else 1})
    df = pl.DataFrame(out, infer_schema_length=None).with_columns(pl.col('r_x2').cast(pl.Float64), pl.col('x2_hit').cast(pl.Int64))
    C.write_parquet(df, C.WORK / split / 'x2.parquet')
    print('x2', split, df.height, 'defined', int(df['x2_hit'].is_not_null().sum()), 'reached', flush=True)


if __name__ == '__main__':
    main()
