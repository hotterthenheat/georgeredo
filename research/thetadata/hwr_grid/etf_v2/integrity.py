"""Data-integrity check of the full-chain files (etf_v2; not part of the pre-registered grid, it decides whether the grid can be run
without amendment A1).  Usage: python3 integrity.py TICKER   -> $HWR_WORK/manifest_{TICKER}.parquet
For every session of the ticker in the study window (TRAIN start .. 2026-10-09, early closes included and flagged):
  * the full-chain file: sha256, rows, listed strikes, min/max strike, first/last timestamp, rows with a usable quote;
  * the original band file of the same session (research/thetadata/dataset root): strikes, and whether its strikes are a subset of the
    full chain; on the overlapping (strike, right, minute) rows the number of bid/ask differences (> $0.0001) between the two pulls;
  * the underlying 09:31 reference, the session's 09:30-16:00 low/high, and whether the full chain's strike range covers the
    session's full price range (low >= min strike and high <= max strike) and +-(1.0 x) the day's range beyond it.
The per-entry, per-structure check (does every strike the grid needs exist at every entry minute 10:00-14:30) is written by
engine.py (integrity_*.parquet) and summarised by integrity_summary.py."""
import os, sys, hashlib
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

BAND_ROOT = os.path.join(C.SP, 'theta', 'data')


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def main():
    tk = sys.argv[1]
    early = C.early_closes()
    cal = C.L.trading_sessions(C.FIRST[tk], C.LAST)
    rows = []
    for j, d in enumerate(cal):
        fp = C.L.path('chains', tk, d)
        bp = os.path.join(BAND_ROOT, 'chains', tk, d + '.parquet')
        rec = dict(tk=tk, date=d, early_close=d in early, full_file=os.path.exists(fp), band_file=os.path.exists(bp),
                   full_nodata=os.path.exists(fp.replace('.parquet', '.nodata')))
        if rec['full_file']:
            F = pl.read_parquet(fp)
            ks = np.array(sorted(F['strike'].unique().to_list()), float)
            usable = F.filter(pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') > 0) & (pl.col('ask') >= pl.col('bid')))
            rec.update(sha256=sha256(fp), rows=F.height, strikes=len(ks), kmin=float(ks.min()), kmax=float(ks.max()),
                       ts_min=str(F['timestamp'].min()), ts_max=str(F['timestamp'].max()), usable_rows=usable.height,
                       rights=','.join(sorted(F['right'].unique().to_list())))
            try:
                U = C.L.underlying(tk, d).filter(pl.col('close').is_not_null())
                lo, hi = float(U['low'].min()), float(U['high'].max())
                rec.update(day_low=lo, day_high=hi, covers_day_range=bool(ks.min() <= lo and hi <= ks.max()),
                           covers_2x_day_range=bool(ks.min() <= lo - (hi - lo) and hi + (hi - lo) <= ks.max()))
            except FileNotFoundError:
                rec.update(day_low=None, day_high=None, covers_day_range=None, covers_2x_day_range=None)
            if rec['band_file']:
                Bd = pl.read_parquet(bp)
                kb = set(Bd['strike'].unique().to_list())
                rec.update(band_strikes=len(kb), band_subset=bool(kb <= set(ks.tolist())), band_rows=Bd.height)
                J = Bd.select(['timestamp', 'strike', 'right', 'bid', 'ask']).join(
                    F.select(['timestamp', 'strike', 'right', 'bid', 'ask']), on=['timestamp', 'strike', 'right'], how='left', suffix='_f')
                miss = J.filter(pl.col('bid_f').is_null() & pl.col('ask_f').is_null() & (pl.col('bid').is_not_null() | pl.col('ask').is_not_null())).height
                diff = J.filter(((pl.col('bid') - pl.col('bid_f')).abs() > 1e-4) | ((pl.col('ask') - pl.col('ask_f')).abs() > 1e-4)
                                | (pl.col('bid').is_null() != pl.col('bid_f').is_null()) | (pl.col('ask').is_null() != pl.col('ask_f').is_null())).height
                rec.update(overlap_rows=J.height, overlap_quote_diff_rows=diff, band_rows_missing_in_full=miss)
        rows.append(rec)
        if j % 100 == 0: print(tk, d, flush=True)
    os.makedirs(C.WORK, exist_ok=True)
    pl.DataFrame(rows, infer_schema_length=None).write_parquet(os.path.join(C.WORK, f'manifest_{tk}.parquet'))
    print('done', tk, len(rows), flush=True)


if __name__ == '__main__':
    main()
