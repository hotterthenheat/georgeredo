"""Code validation (etf_v2): the copied engine, run with HWR_CHAIN_ROOT pointing at the ORIGINAL band dataset, must reproduce the original
study's per-trade, skip and selection files exactly.  Compares <scratchpad>/hwr_grid_v2_bandcheck (band re-run with this folder's code)
with <scratchpad>/hwr_grid (the original run) and the band re-run's selection with ../etf/results/selection_train.json.
Writes results/validation_band_reproduction.json."""
import os, sys, json
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

BAND = os.path.join(C.SP, 'hwr_grid_v2_bandcheck')


def main():
    out = {}
    for tk in C.TICKERS:
        for per in ('TRAIN', 'TEST'):
            a = os.path.join(C.ORIG_WORK, f'trades_{tk}_{per}.parquet'); b = os.path.join(BAND, f'trades_{tk}_{per}.parquet')
            if not (os.path.exists(a) and os.path.exists(b)): out[f'{tk}_{per}'] = 'missing'; continue
            A_ = pl.read_parquet(a); B_ = pl.read_parquet(b)
            sa = pl.read_parquet(os.path.join(C.ORIG_WORK, f'skips_{tk}_{per}.parquet')); sb = pl.read_parquet(os.path.join(BAND, f'skips_{tk}_{per}.parquet'))
            out[f'{tk}_{per}'] = dict(rows_orig=A_.height, rows_v2_band=B_.height, trades_identical=bool(A_.equals(B_)), skips_identical=bool(sa.equals(sb)))
    so = json.load(open(os.path.join(C.ORIG, 'results', 'selection_train.json')))['scopes']
    sbp = os.path.join(BAND, 'results_test', 'selection_train.json')
    if os.path.exists(sbp):
        sb = json.load(open(sbp))['scopes']
        out['selections_identical'] = {sc: bool(so[sc]['S1']['cfg'] == sb[sc]['S1']['cfg'] and (so[sc]['S2'] or {}).get('cfg') == (sb[sc]['S2'] or {}).get('cfg')
                                                and abs(so[sc]['S1']['lo'] - sb[sc]['S1']['lo']) < 1e-9) for sc in so if sc in sb}
    st_o = os.path.join(C.ORIG, 'results', 'selected_test.csv'); st_b = os.path.join(BAND, 'results_test', 'selected_test.csv')
    if os.path.exists(st_b):
        o = pl.read_csv(st_o).select(['scope', 'selection', 'cfg', 'test_n', 'test_mean', 'test_lo', 'lane_minus_base'])
        b = pl.read_csv(st_b).select(['scope', 'selection', 'cfg', 'test_n', 'test_mean', 'test_lo', 'lane_minus_base'])
        j = o.join(b, on=['scope', 'selection', 'cfg'], how='inner', suffix='_v2')
        out['selected_test_rows_compared'] = j.height
        out['selected_test_max_abs_diff'] = {c: float((j[c] - j[c + '_v2']).abs().max()) for c in ('test_n', 'test_mean', 'test_lo', 'lane_minus_base')}
    json.dump(out, open(os.path.join(C.OUT, 'validation_band_reproduction.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
