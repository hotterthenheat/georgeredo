"""Summarises the data-integrity check (etf_v2).  Reads $HWR_WORK/integrity_*.parquet (engine.py), skips_*.parquet, manifest_*.parquet
(integrity.py), the original run's skips in C.ORIG_WORK, and the band-data manifests in <scratchpad>/hwr_grid_v2_bandcheck (integrity.py
run with HWR_CHAIN_ROOT pointing at the original band dataset).  Writes
  results/integrity_summary.csv    status counts per ticker x period x entry set x structure-k
                                   (entry sets: 'fixed' = 10:00/11:00/13:00/14:05; 'random' = the seed-11..15 drawn minutes;
                                    'all_minutes' = every minute 10:00..14:30)
  results/integrity_missing.csv    every fixed or random entry x structure-k still skipped for a data reason (strike or quote missing)
  results/integrity_recovered.csv  entries the original run skipped (by reason) and what they are on the full chains
  results/integrity_reach.csv      how far the listed strikes reach beyond spot, in units of the entry-time expected move
  results/data_manifest.csv        one row per full-chain file: sha256, rows, strikes, range, band-file comparison
  results/integrity.json           headline counts"""
import os, sys, json, glob
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

DATA_REASONS = ['out_of_band', 'out_of_band_spot', 'no_quote', 'no_spot', 'no_em']
MARKET_REASONS = ['zero_bid', 'no_credit']
SKS = [C.sk_name(s, k) for s, k in C.SK]
BANDCHECK = os.path.join(C.SP, 'hwr_grid_v2_bandcheck')


def main():
    out = {}; summ = []; missing = []; recov = []; reach = []
    rnd = C.random_minutes()
    for tk in C.TICKERS:
        for per in ('TRAIN', 'TEST'):
            fp = os.path.join(C.WORK, f'integrity_{tk}_{per}.parquet')
            if not os.path.exists(fp): continue
            I = pl.read_parquet(fp)
            L = I.unpivot(index=['date', 'T'], on=[f'st_{k}' for k in SKS], variable_name='sk', value_name='status').with_columns(pl.col('sk').str.slice(3))
            fixed = L.filter(pl.col('T').is_in(list(C.ENTRIES)))
            rk = pl.DataFrame([(d, C.mstr(m), f'r{s}') for (s, t, d), m in rnd.items() if t == tk], schema=['date', 'T', 'entry'], orient='row')
            rand = L.join(rk, on=['date', 'T'], how='inner')
            for name, X in (('fixed', fixed), ('random', rand), ('all_minutes', L)):
                g = X.group_by(['sk', 'status']).len().pivot(on='status', index='sk', values='len').fill_null(0)
                for r in g.iter_rows(named=True):
                    n = sum(v for k, v in r.items() if k != 'sk')
                    summ.append(dict(ticker=tk, period=per, entries=name, sk=r['sk'], slots=n, **{k: r.get(k, 0) for k in ['ok'] + DATA_REASONS + MARKET_REASONS}))
            fx = fixed.with_columns(pl.col('T').alias('entry'))
            for X in (fx, rand):
                m = X.filter(pl.col('status').is_in(DATA_REASONS))
                for r in m.iter_rows(named=True): missing.append(dict(ticker=tk, period=per, date=r['date'], entry=r['entry'], T=r['T'], sk=r['sk'], reason=r['status']))
            # reach of the listed strikes, in EM units, at the fixed entries and over all minutes
            for name, X in (('fixed', I.filter(pl.col('T').is_in(list(C.ENTRIES)))), ('all_minutes', I)):
                ru = X['reach_up'].drop_nans().drop_nulls().to_numpy(); rd = X['reach_dn'].drop_nans().drop_nulls().to_numpy()
                reach.append(dict(ticker=tk, period=per, entries=name, n=len(ru), reach_up_min=round(float(ru.min()), 2), reach_up_p01=round(float(np.percentile(ru, 1)), 2),
                                  reach_up_median=round(float(np.median(ru)), 2), reach_dn_min=round(float(rd.min()), 2), reach_dn_p01=round(float(np.percentile(rd, 1)), 2),
                                  reach_dn_median=round(float(np.median(rd)), 2), slots_reach_below_2p5EM=int(((ru < 2.5) | (rd < 2.5)).sum()),
                                  strikes_median=int(X['n_strikes'].median())))
            # entries skipped in the ORIGINAL run, by reason, and their status now
            op = os.path.join(C.ORIG_WORK, f'skips_{tk}_{per}.parquet')
            if os.path.exists(op):
                O = pl.read_parquet(op)
                N = pl.read_parquet(os.path.join(C.WORK, f'skips_{tk}_{per}.parquet')).select(['date', 'entry', 'sk', pl.col('reason').alias('now')])
                J = O.join(N, on=['date', 'entry', 'sk'], how='left').with_columns(pl.col('now').fill_null('traded'),
                                                                                    kind=pl.when(pl.col('entry').str.starts_with('r')).then(pl.lit('random')).otherwise(pl.lit('fixed')))
                for (kind, reason, now), g in J.group_by(['kind', 'reason', 'now']):
                    recov.append(dict(ticker=tk, period=per, entries=kind, orig_reason=reason, now=now, n=g.height, sessions=g['date'].n_unique()))
                # sessions with at least one band-skipped fixed entry (the extreme-move days)
                bs = J.filter((pl.col('kind') == 'fixed') & pl.col('reason').is_in(['out_of_band', 'out_of_band_spot']))
                out[f'{tk}_{per}_orig_band_skips_fixed'] = bs.height
                out[f'{tk}_{per}_orig_band_skips_fixed_now_traded'] = bs.filter(pl.col('now') == 'traded').height
                out[f'{tk}_{per}_orig_spot_outside_band_fixed'] = bs.filter(pl.col('reason') == 'out_of_band_spot').height
                out[f'{tk}_{per}_orig_spot_outside_band_fixed_now_traded'] = bs.filter((pl.col('reason') == 'out_of_band_spot') & (pl.col('now') == 'traded')).height
                out[f'{tk}_{per}_orig_spot_outside_band_fixed_sessions'] = bs.filter(pl.col('reason') == 'out_of_band_spot')['date'].n_unique()
            D = pl.read_parquet(os.path.join(C.WORK, f'days_{tk}_{per}.parquet'))
            out[f'{tk}_{per}_days'] = {s: int(c) for s, c in D.group_by('status').len().rows()}
    S = pl.DataFrame(summ).sort(['ticker', 'period', 'entries', 'sk'])
    S.write_csv(os.path.join(C.OUT, 'integrity_summary.csv'))
    cols = ['ticker', 'period', 'date', 'entry', 'T', 'sk', 'reason']
    MS = pl.DataFrame(missing).select(cols).sort(['ticker', 'date', 'T', 'sk']) if missing else pl.DataFrame(schema={c: pl.Utf8 for c in cols})
    MS.write_csv(os.path.join(C.OUT, 'integrity_missing.csv'))
    pl.DataFrame(recov).sort(['ticker', 'period', 'entries', 'orig_reason', 'now']).write_csv(os.path.join(C.OUT, 'integrity_recovered.csv'))
    pl.DataFrame(reach).write_csv(os.path.join(C.OUT, 'integrity_reach.csv'))
    # file manifest (full chains) with the band comparison; band-data range coverage from the bandcheck manifests
    mans = [pl.read_parquet(f) for f in sorted(glob.glob(os.path.join(C.WORK, 'manifest_*.parquet')))]
    if mans:
        M = pl.concat(mans, how='diagonal_relaxed').sort(['tk', 'date'])
        M.write_csv(os.path.join(C.OUT, 'data_manifest.csv'))
        for tk, g in M.group_by('tk'):
            tk = tk[0]; gg = g.filter(pl.col('full_file'))
            out[f'{tk}_manifest'] = dict(sessions=g.height, full_files=gg.height, nodata=int(g['full_nodata'].sum()), early_close=int(g['early_close'].sum()),
                                         strikes_median=int(gg['strikes'].median()), strikes_min=int(gg['strikes'].min()),
                                         covers_day_range=int(gg['covers_day_range'].sum()), covers_2x_day_range=int(gg['covers_2x_day_range'].sum()),
                                         band_subset_all=bool(gg.filter(pl.col('band_file'))['band_subset'].all()),
                                         overlap_rows=int(gg['overlap_rows'].sum()), overlap_quote_diff_rows=int(gg['overlap_quote_diff_rows'].sum()),
                                         band_rows_missing_in_full=int(gg['band_rows_missing_in_full'].sum()),
                                         sessions_with_quote_diffs=int((gg['overlap_quote_diff_rows'] > 0).sum()))
            bp = os.path.join(BANDCHECK, f'manifest_{tk}.parquet')
            if os.path.exists(bp):
                Bm = pl.read_parquet(bp).filter(pl.col('full_file'))
                out[f'{tk}_band_data_covers_day_range'] = f"{int(Bm['covers_day_range'].sum())} of {Bm.height}"
    out['missing_fixed_or_random_entries'] = len(missing)
    out['missing_by_reason'] = {r: sum(1 for m in missing if m['reason'] == r) for r in DATA_REASONS}
    json.dump(out, open(os.path.join(C.OUT, 'integrity.json'), 'w'), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str)[:4000])


if __name__ == '__main__':
    main()
