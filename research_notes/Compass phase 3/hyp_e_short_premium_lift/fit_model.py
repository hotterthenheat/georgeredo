"""Compass Phase 3, Hypothesis E. Refit Hypothesis D's t2 volatility model on SPY's full-session scan minutes and score
every scan minute. Exactly model.py's recipe (its GBM settings, 5 contiguous-block out-of-fold scores on the fit period,
decile cuts on the cut slice) imported from Hypothesis D's model.py itself (read-only) - with two stated differences:
SPY alone (no product categorical; Hypothesis D pooled four products), and all 971 full sessions (it took every second).
  t2 = the realized |30-minute move| > implied30 (straddle/spot x sqrt(30 / minutes left)).
  fit = sessions before 2024-07-01, trained on the scan minutes Hypothesis D used (09:35..15:25); cut = 2024-07 -> 2024-12
  (the nine inner quantiles of the final score are the registered cuts); 15:30 (m = 360, added for this test) is scored
  but not trained on; OOS = 2025-01 -> 2026-10-09, scored here and READ only by the OOS pass.
The decile used by the lift test (`dec`): in the fit period the out-of-fold score cut at its own fit-period quantiles
(dec_kind 'oof'), in the cut and OOS periods the final model's score at the registered cuts ('reg') - as Hypothesis D's
fit+cut and oos reads. The OOS AUC and OOS decile rates are computed only by `fit_model.py oos` (after preregistered.md).
Outputs: out/scores_SPY.parquet (rebuildable), out/model_auc.csv, out/decile_rates.csv, out/feature_importance.csv,
out/hypd_spy_auc.csv (Hypothesis D's own pooled model read on its SPY rows, for the comparison).
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I fit_model.py        # fit + cut reads
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I fit_model.py oos    # the OOS AUC and decile rates
"""
import datetime as dt, os, sys, time
import numpy as np, polars as pl
HYP_D = '/home/user/georgeredo/research_notes/Compass phase 2/hyp_d_vol_breakout'
sys.path.insert(0, HYP_D)
import lib as L                      # noqa: E402  Hypothesis D's feature list and periods (read-only)
import model as HD                   # noqa: E402  Hypothesis D's GBM settings, folds, decile_of, auc (read-only; guarded by __main__)
from sklearn.linear_model import LogisticRegression   # noqa: E402
from sklearn.preprocessing import StandardScaler       # noqa: E402
from sklearn.pipeline import make_pipeline             # noqa: E402
import lightgbm as lgb                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
FEATS = list(L.FEATURES)             # no product column: SPY alone
TRAIN_SCANS = set(L.SCAN) if max(L.SCAN) <= 355 else set(range(5, 356, 5))   # Hypothesis D's 71 scan minutes

def fit_gbm(X, y):
    mdl = lgb.LGBMClassifier(**HD.GBM); mdl.fit(X, y); return mdl

def fit_lr(X, y):
    med = np.nanmedian(X, axis=0); Xn = np.where(np.isnan(X), med, X)
    mdl = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=3000)); mdl.fit(Xn, y); return (mdl, med)

def pred(model, X, kind):
    if kind == 'gbm': return model.predict_proba(X)[:, 1]
    mdl, med = model; return mdl.predict_proba(np.where(np.isnan(X), med, X))[:, 1]

def load():
    cols = list(dict.fromkeys(['session', 'm', 'spot', 'straddle', 'mv30_bps', 't2'] + FEATS))
    D = pl.read_parquet(os.path.join(OUT, 'minutes_SPY_all.parquet'), columns=cols)
    return L.with_period(D).sort('session', 'm')

if __name__ == '__main__':
    t0 = time.time()
    if len(sys.argv) > 1 and sys.argv[1] == 'oos':
        # ---- the OOS read of the model's quality: after the pre-registration only
        D = load().filter(pl.col('t2').is_not_null())
        Sc = pl.read_parquet(os.path.join(OUT, 'scores_SPY.parquet'))
        J = D.join(Sc, on=['session', 'm', 'period'], how='inner')
        rows = []; dec_rows = []
        for key in ('full_gbm', 'full_lr', 'base_gbm'):
            o = J.filter(pl.col('period') == 'oos')
            rows.append(dict(target='t2', model=key, period='oos', n=o.height, auc=HD.auc(o['t2'].to_numpy().astype(int), o[f'{key}_score'].to_numpy())))
            for d in range(1, 11):
                s = o.filter(pl.col(f'{key}_dec_reg') == d)
                dec_rows.append(dict(target='t2', model=key, period='oos', decile=d, n=s.height, share=s.height / max(o.height, 1), rate=float(s['t2'].mean()) if s.height else np.nan, mv30_mean=float(s['mv30_bps'].mean()) if s.height else np.nan))
        # Hypothesis D's own model on its SPY OOS rows
        HS = pl.read_parquet(os.path.join(HYP_D, 'out', 'scores.parquet')).filter(pl.col('product') == 'SPY')
        HM = pl.read_parquet(os.path.join(HYP_D, 'out', 'minutes_SPY.parquet'), columns=['session', 'm', 't2']).filter(pl.col('t2').is_not_null())
        HJ = HS.join(HM, on=['session', 'm'], how='inner').filter(pl.col('period') == 'oos')
        for key in ('full_gbm', 'full_lr', 'base_gbm'):
            rows.append(dict(target='t2', model=f'hypd_pooled_{key}_on_SPY', period='oos', n=HJ.height, auc=HD.auc(HJ['t2'].to_numpy().astype(int), HJ[f't2_{key}_score'].to_numpy())))
        R = pl.DataFrame(rows); R.write_csv(os.path.join(OUT, 'model_auc_oos.csv')); pl.DataFrame(dec_rows).write_csv(os.path.join(OUT, 'decile_rates_oos.csv'))
        pl.Config.set_tbl_rows(50); pl.Config.set_float_precision(4); print(R); print(pl.DataFrame(dec_rows).filter(pl.col('model') == 'full_gbm'))
        sys.exit(0)

    D = load()
    print('rows', D.height, 'sessions', D['session'].n_unique(), D.group_by('period').len().sort('period').to_dicts(), flush=True)
    Dt = D.filter(pl.col('t2').is_not_null())
    y = Dt['t2'].to_numpy().astype(int); per = Dt['period'].to_numpy(); sess = Dt['session'].to_numpy(); mm = Dt['m'].to_numpy()
    in_train_scan = np.isin(mm, list(TRAIN_SCANS))
    fit = (per == 'fit') & in_train_scan; cut = (per == 'cut') & in_train_scan; fit_all = per == 'fit'; cut_all = per == 'cut'; oos = per == 'oos'
    print(f't2: n fit {fit.sum()} (+{(fit_all & ~fit).sum()} at 15:30) cut {cut.sum()} oos {oos.sum()}; base rate fit {y[fit].mean():.3f} cut {y[cut].mean():.3f}', flush=True)
    X = Dt.select(FEATS).to_numpy().astype(float)
    Xb = Dt.select(list(L.BASE_FEATURES)).to_numpy().astype(float)
    out = Dt.select('session', 'm', 'period'); auc_rows = []; dec_rows = []; imp_rows = []
    for key, Xk, kind in (('full_gbm', X, 'gbm'), ('full_lr', X, 'lr'), ('base_gbm', Xb, 'gbm')):
        fitter = fit_gbm if kind == 'gbm' else fit_lr
        mdl = fitter(Xk[fit], y[fit]); p = pred(mdl, Xk, kind)
        us = np.unique(sess[fit]); blocks = np.array_split(us, HD.NFOLD); oof = np.full(len(y), np.nan)
        for b in blocks:
            te = fit_all & np.isin(sess, b); tr = fit & ~np.isin(sess, b)
            m_ = fitter(Xk[tr], y[tr]); oof[te] = pred(m_, Xk[te], kind)
        a = dict(target='t2', model=key, n_fit=int(fit.sum()), auc_fit_insample=HD.auc(y[fit], p[fit]), auc_fit_oof=HD.auc(y[fit], oof[fit]), auc_cut=HD.auc(y[cut], p[cut]), auc_fit_oof_incl1530=HD.auc(y[fit_all], oof[fit_all]), auc_cut_incl1530=HD.auc(y[cut_all], p[cut_all]))
        auc_rows.append(a); print('  ', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in a.items()}, flush=True)
        if key == 'full_gbm':
            for c, g in zip(FEATS, mdl.booster_.feature_importance('gain')): imp_rows.append(dict(feature=c, gain=float(g)))
        if kind == 'lr':
            coef = mdl[0].named_steps['logisticregression'].coef_[0]; order = np.argsort(-np.abs(coef))
            print('   standardised coefficients:', ', '.join(f'{FEATS[i]} {coef[i]:+.3f}' for i in order[:12]), flush=True)
        cuts = np.quantile(p[cut], np.linspace(0.1, 0.9, 9)); dec_reg = HD.decile_of(p, cuts)
        cuts_oof = np.quantile(oof[fit], np.linspace(0.1, 0.9, 9)); dec_oof = np.where(fit_all, HD.decile_of(np.nan_to_num(oof, nan=-1), cuts_oof), 0)
        dec = np.where(fit_all, dec_oof, dec_reg).astype(np.int8)
        out = out.with_columns(pl.Series(f'{key}_score', p), pl.Series(f'{key}_oof', oof), pl.Series(f'{key}_dec_reg', dec_reg.astype(np.int8)), pl.Series(f'{key}_dec_oof', dec_oof.astype(np.int8)), pl.Series(f'{key}_dec', dec))
        for pname, mask, dcol in (('fit_oof', fit_all, dec_oof), ('cut', cut_all, dec_reg)):
            for d in range(1, 11):
                sel = mask & (dcol == d)
                dec_rows.append(dict(target='t2', model=key, period=pname, decile=d, n=int(sel.sum()), share=float(sel.sum() / max(mask.sum(), 1)), rate=float(y[sel].mean()) if sel.any() else np.nan,
                                     mv30_mean=float(Dt['mv30_bps'].to_numpy()[sel].mean()) if sel.any() else np.nan))
        print('   cuts (registered, cut slice):', np.round(cuts, 4).tolist(), flush=True)
    out = out.with_columns(pl.when(pl.col('period') == 'fit').then(pl.lit('oof')).otherwise(pl.lit('reg')).alias('dec_kind'))
    out.write_parquet(os.path.join(OUT, 'scores_SPY.parquet'))
    pl.DataFrame(auc_rows).write_csv(os.path.join(OUT, 'model_auc.csv'))
    pl.DataFrame(dec_rows).write_csv(os.path.join(OUT, 'decile_rates.csv'))
    pl.DataFrame(imp_rows).sort('gain', descending=True).write_csv(os.path.join(OUT, 'feature_importance.csv'))
    # ---- Hypothesis D's own (pooled, every-2nd-session) model, read on its SPY rows alone: fit OOF and cut
    HS = pl.read_parquet(os.path.join(HYP_D, 'out', 'scores.parquet')).filter(pl.col('product') == 'SPY')
    HM = pl.read_parquet(os.path.join(HYP_D, 'out', 'minutes_SPY.parquet'), columns=['session', 'm', 't2']).filter(pl.col('t2').is_not_null())
    HJ = HS.join(HM, on=['session', 'm'], how='inner'); hrows = []
    for key in ('full_gbm', 'full_lr', 'base_gbm'):
        f = HJ.filter(pl.col('period') == 'fit'); c = HJ.filter(pl.col('period') == 'cut')
        hrows.append(dict(target='t2', model=f'hypd_pooled_{key}_on_SPY', n_fit=f.height, auc_fit_oof=HD.auc(f['t2'].to_numpy().astype(int), f[f't2_{key}_oof'].to_numpy()), auc_cut=HD.auc(c['t2'].to_numpy().astype(int), c[f't2_{key}_score'].to_numpy())))
        for pname, g, dc in (('fit_oof', f, f't2_{key}_dec_oof'), ('cut', c, f't2_{key}_dec')):
            for d in (1, 2, 10):
                s = g.filter(pl.col(dc) == d); hrows.append(dict(target='t2', model=f'hypd_pooled_{key}_on_SPY', period=pname, decile=d, n=s.height, rate=float(s['t2'].mean()) if s.height else np.nan))
    pl.DataFrame(hrows, infer_schema_length=None).write_csv(os.path.join(OUT, 'hypd_spy_auc.csv'))
    pl.Config.set_tbl_rows(60); pl.Config.set_float_precision(4); pl.Config.set_tbl_width_chars(200)
    print(pl.DataFrame(hrows, infer_schema_length=None))
    print(pl.DataFrame(dec_rows).filter(pl.col('model') == 'full_gbm').select('period', 'decile', 'n', 'share', 'rate', 'mv30_mean'))
    print(pl.DataFrame(imp_rows).sort('gain', descending=True).head(10))
    print(f'done {time.time() - t0:.0f}s')
