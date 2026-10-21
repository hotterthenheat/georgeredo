"""The volatility forecast. For each target - t1: |30-minute move| >= 10 bps; t2: the realized |30-minute move| exceeds the
straddle-implied 30-minute move (straddle/spot * sqrt(30 / minutes left), a stated approximation); t3: the realized move
to the close exceeds the straddle/spot - a gradient-boosted model (LightGBM, one thread, fixed settings, never tuned) and
a logistic regression are fitted on the fit period (sessions before 2024-07-01) with the features known at the scan
minute; decile cuts are set on the cut slice (2024-07 -> 2024-12); 2025-2026 is scored once. A baseline that knows only
the time of day and the straddle (m, straddle_rel, product) is fitted the same way, and the lift of the full model's
top decile over the baseline's is reported. Honest fit-period scores are out-of-fold (5 contiguous session blocks).
Outputs: out/scores.parquet (one row a scan minute: scores and decile membership per target and model),
out/model_auc.csv, out/decile_rates.csv, out/lift.csv, out/feature_importance.csv.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I model.py
"""
import os, sys, time
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score

PROD_CODE = {p: i for i, p in enumerate(L.PRODUCTS)}
GBM = dict(objective='binary', num_leaves=15, learning_rate=0.05, n_estimators=400, min_child_samples=200, subsample=0.8, subsample_freq=1,
           colsample_bytree=0.8, reg_lambda=1.0, num_threads=1, verbose=-1, random_state=1)
NFOLD = 5

def load():
    cols = ['product', 'session', 'm', 'straddle_rel', 'mv30_bps', 'mvclose_bps', 't1', 't2', 't3'] + [f for f in L.FEATURES if f not in ('m', 'straddle_rel')]
    frames = [pl.read_parquet(os.path.join(L.OUT, f'minutes_{p}.parquet'), columns=cols) for p in L.PRODUCTS]
    return L.with_period(pl.concat(frames, how='diagonal_relaxed')).sort('session', 'product', 'm')

def design(df, feats, with_product=True):
    X = df.select(feats).to_numpy().astype(float)
    cols = list(feats)
    if with_product:
        pc = df['product'].to_numpy()
        X = np.column_stack([X, np.array([PROD_CODE[p] for p in pc], float)]); cols.append('product')
    return X, cols

def fit_gbm(X, y, cols):
    cat = [cols.index('product')] if 'product' in cols else []
    mdl = lgb.LGBMClassifier(**GBM); mdl.fit(X, y, categorical_feature=cat); return mdl

def fit_lr(X, y, cols):
    # one-hot the product, fill NaN with the training median
    pi = cols.index('product'); P = X[:, pi].astype(int); Xn = np.delete(X, pi, axis=1)
    med = np.nanmedian(Xn, axis=0); Xn = np.where(np.isnan(Xn), med, Xn)
    Xd = np.column_stack([Xn] + [(P == k).astype(float) for k in range(1, len(L.PRODUCTS))])
    mdl = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=3000)); mdl.fit(Xd, y)
    return (mdl, med, pi)

def pred_lr(model, X):
    mdl, med, pi = model; P = X[:, pi].astype(int); Xn = np.delete(X, pi, axis=1); Xn = np.where(np.isnan(Xn), med, Xn)
    Xd = np.column_stack([Xn] + [(P == k).astype(float) for k in range(1, len(L.PRODUCTS))])
    return mdl.predict_proba(Xd)[:, 1]

def decile_of(score, cuts):
    return np.clip(np.searchsorted(cuts, score, side='right'), 0, 9) + 1   # cuts: the 9 inner quantiles -> 1..10

def auc(y, p):
    return float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else np.nan

if __name__ == '__main__':
    t0 = time.time()
    D = load()
    print('rows', D.height, D.group_by('period').len().sort('period').to_dicts(), flush=True)
    feats_full = [f for f in L.FEATURES]; feats_base = list(L.BASE_FEATURES)
    auc_rows = []; dec_rows = []; lift_rows = []; imp_rows = []
    out = D.select('product', 'session', 'm', 'period')
    for tgt in L.TARGETS:
        Dt = D.filter(pl.col(tgt).is_not_null())
        y = Dt[tgt].to_numpy().astype(int); per = Dt['period'].to_numpy(); sess = Dt['session'].to_numpy(); mm = Dt['m'].to_numpy()
        fit = per == 'fit'; cut = per == 'cut'; oos = per == 'oos'
        print(f'\n==== target {tgt}: n fit {fit.sum()} cut {cut.sum()} oos {oos.sum()}; base rate fit {y[fit].mean():.3f} cut {y[cut].mean():.3f} oos {y[oos].mean():.3f}', flush=True)
        scores = {}
        for name, feats in (('full', feats_full), ('base', feats_base)):
            X, cols = design(Dt, feats)
            for kind in (('gbm', 'lr') if name == 'full' else ('gbm',)):
                key = f'{name}_{kind}'
                fitter = fit_gbm if kind == 'gbm' else fit_lr
                mdl = fitter(X[fit], y[fit], cols)
                p = mdl.predict_proba(X)[:, 1] if kind == 'gbm' else pred_lr(mdl, X)
                # out-of-fold on the fit period: 5 contiguous session blocks
                us = np.unique(sess[fit]); blocks = np.array_split(us, NFOLD); oof = np.full(len(y), np.nan)
                for b in blocks:
                    te = fit & np.isin(sess, b); tr = fit & ~te
                    m_ = fitter(X[tr], y[tr], cols)
                    oof[te] = m_.predict_proba(X[te])[:, 1] if kind == 'gbm' else pred_lr(m_, X[te])
                scores[key] = (p, oof)
                a = dict(target=tgt, model=key, auc_fit_insample=auc(y[fit], p[fit]), auc_fit_oof=auc(y[fit], oof[fit]), auc_cut=auc(y[cut], p[cut]), auc_oos=auc(y[oos], p[oos]))
                auc_rows.append(a); print('  ', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in a.items()}, flush=True)
                if kind == 'gbm' and name == 'full':
                    for c, g in zip(cols, mdl.booster_.feature_importance('gain')): imp_rows.append(dict(target=tgt, feature=c, gain=float(g)))
                if kind == 'lr':
                    coef = mdl[0].named_steps['logisticregression'].coef_[0]; names = [c for c in cols if c != 'product'] + [f'product={q}' for q in L.PRODUCTS[1:]]
                    order = np.argsort(-np.abs(coef)); print('   standardised coefficients:', ', '.join(f'{names[i]} {coef[i]:+.3f}' for i in order[:12]), flush=True)
                # decile cuts on the cut slice (registered); OOF deciles within the fit period
                cuts = np.quantile(p[cut], np.linspace(0.1, 0.9, 9)); dec = decile_of(p, cuts)
                cuts_oof = np.quantile(oof[fit], np.linspace(0.1, 0.9, 9)); dec_oof = np.where(fit, decile_of(np.nan_to_num(oof, nan=-1), cuts_oof), 0)
                col = pl.DataFrame({'product': Dt['product'], 'session': Dt['session'], 'm': Dt['m'], f'{tgt}_{key}_score': p, f'{tgt}_{key}_oof': oof,
                                    f'{tgt}_{key}_dec': dec.astype(np.int8), f'{tgt}_{key}_dec_oof': dec_oof.astype(np.int8)})
                out = out.join(col, on=['product', 'session', 'm'], how='left')
                for pname, mask, dcol in (('fit_oof', fit, dec_oof), ('cut', cut, dec), ('oos', oos, dec)):
                    for d in range(1, 11):
                        sel = mask & (dcol == d)
                        dec_rows.append(dict(target=tgt, model=key, period=pname, decile=d, n=int(sel.sum()), share=float(sel.sum() / max(mask.sum(), 1)),
                                             score_mean=float((oof if pname == 'fit_oof' else p)[sel].mean()) if sel.any() else np.nan, rate=float(y[sel].mean()) if sel.any() else np.nan,
                                             mv30_mean=float(Dt['mv30_bps'].to_numpy()[sel].mean()) if sel.any() else np.nan))
                scores[key + '_dec'] = (dec, dec_oof)
        # lift of the full model's D10 over the baseline's D10, and over the time-of-day-matched rate
        for pname, mask in (('fit_oof', fit), ('cut', cut), ('oos', oos)):
            dfull = scores['full_gbm_dec'][1 if pname == 'fit_oof' else 0]; dbase = scores['base_gbm_dec'][1 if pname == 'fit_oof' else 0]; dlr = scores['full_lr_dec'][1 if pname == 'fit_oof' else 0]
            s_full = mask & (dfull == 10); s_base = mask & (dbase == 10); s_lr = mask & (dlr == 10)
            # time-of-day matched: the rate over all rows of the period at the same product and m, averaged over the D10 rows
            key_pm = np.array([f'{a}|{b}' for a, b in zip(Dt['product'].to_numpy(), mm)])
            rate_pm = {}
            for k_ in np.unique(key_pm[mask]):
                sel = mask & (key_pm == k_); rate_pm[k_] = y[sel].mean()
            tod_rate = float(np.mean([rate_pm[k_] for k_ in key_pm[s_full]])) if s_full.any() else np.nan
            r = dict(target=tgt, period=pname, n_rows=int(mask.sum()), base_rate=float(y[mask].mean()), n_d10_full=int(s_full.sum()), rate_d10_full=float(y[s_full].mean()) if s_full.any() else np.nan,
                     rate_d10_lr=float(y[s_lr].mean()) if s_lr.any() else np.nan, rate_d10_base=float(y[s_base].mean()) if s_base.any() else np.nan,
                     rate_tod_matched=tod_rate, overlap_full_base=float((s_full & s_base).sum() / max(s_full.sum(), 1)),
                     rate_full_d10_not_in_base_d10=float(y[s_full & ~s_base].mean()) if (s_full & ~s_base).any() else np.nan,
                     rate_base_d10_not_in_full_d10=float(y[s_base & ~s_full].mean()) if (s_base & ~s_full).any() else np.nan,
                     mv30_d10_full=float(Dt['mv30_bps'].to_numpy()[s_full].mean()) if s_full.any() else np.nan, mv30_d10_base=float(Dt['mv30_bps'].to_numpy()[s_base].mean()) if s_base.any() else np.nan,
                     mv30_all=float(np.nanmean(Dt['mv30_bps'].to_numpy()[mask])))
            r['lift_full_over_base'] = r['rate_d10_full'] - r['rate_d10_base']; r['lift_full_over_tod'] = r['rate_d10_full'] - r['rate_tod_matched']
            # D10 by half hour of the day
            hh = (mm // 30)
            r['d10_share_by_halfhour'] = ' '.join(f'{int(h*30+570)//60:02d}{int(h*30+570)%60:02d}:{(s_full & (hh == h)).sum() / max(s_full.sum(),1):.2f}' for h in range(0, 12))
            lift_rows.append(r); print('   lift', pname, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k != 'd10_share_by_halfhour'}, flush=True); print('     D10 by half hour:', r['d10_share_by_halfhour'])
    out.write_parquet(os.path.join(L.OUT, 'scores.parquet'))
    pl.DataFrame(auc_rows).write_csv(os.path.join(L.OUT, 'model_auc.csv'))
    pl.DataFrame(dec_rows).write_csv(os.path.join(L.OUT, 'decile_rates.csv'))
    pl.DataFrame(lift_rows).write_csv(os.path.join(L.OUT, 'lift.csv'))
    pl.DataFrame(imp_rows).sort('target', 'gain', descending=[False, True]).write_csv(os.path.join(L.OUT, 'feature_importance.csv'))
    print(pl.DataFrame(imp_rows).sort('target', 'gain', descending=[False, True]).group_by('target', maintain_order=True).head(8))
    print(f'done {time.time() - t0:.0f}s')
