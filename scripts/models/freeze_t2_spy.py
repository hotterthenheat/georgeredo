#!/usr/bin/env python3
"""
freeze_t2_spy.py — freeze Hypothesis E's SPY t2 volatility model for the forward paper test (paper_tracker.py candidate 3).

Refits EXACTLY as research_notes/Compass phase 3/hyp_e_short_premium_lift/fit_model.py does (read-only imports of
Hypothesis D's lib.py feature list and model.py GBM settings — LightGBM, num_threads=1, never tuned): SPY alone, the
t2 target (the realized |30-minute move| > implied30), fit = sessions before 2024-07-01 on Hypothesis D's 71 scan
minutes (09:35 .. 15:25), the decile cuts = the nine inner quantiles of the final model's score on the cut slice
2024-07-01 -> 2024-12-31 (the same 71 scan minutes). Two models:

  t2_spy_full   the 25 features of hyp_d lib.FEATURES, in that order — Hypothesis E's model (its AUCs and cuts are
                checked against hyp_e's out/model_auc.csv and out/scores_SPY.parquet below; a mismatch stops the run)
  t2_spy_novix  the same recipe WITHOUT the four VIX features (vix, vix_chg_open, vix_chg30, vix_chg_prev) — the
                fallback decile for a session whose VIX cannot be read live (UW Basic answers 422 for VIX)

Writes, under scripts/models/: <model>.txt (LightGBM's text model), <model>.cuts.json (the nine cuts), <model>.manifest.json
(the features in order, the training rows, the AUCs reproduced, the settings, the sha256 of the model text and of the
cuts), and tests/fixtures/t2_feature_rows.json (a few feature rows with LightGBM's own score and decile, for the tests).
The tracker LOADS these files (and checks the hashes); it never refits.

  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I scripts/models/freeze_t2_spy.py
"""
import datetime as dt, hashlib, json, os, sys
import numpy as np, polars as pl

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HYP_D = os.path.join(REPO, 'research_notes', 'Compass phase 2', 'hyp_d_vol_breakout')
HYP_E = os.path.join(REPO, 'research_notes', 'Compass phase 3', 'hyp_e_short_premium_lift')
sys.path.insert(0, HYP_D)
import lib as L                      # noqa: E402  Hypothesis D's feature list and periods (read-only)
import model as HD                   # noqa: E402  Hypothesis D's GBM settings, NFOLD, decile_of, auc (read-only)
import lightgbm as lgb               # noqa: E402

VIX_FEATS = ('vix', 'vix_chg_open', 'vix_chg30', 'vix_chg_prev')
MODELS = {'t2_spy_full': [f for f in L.FEATURES], 't2_spy_novix': [f for f in L.FEATURES if f not in VIX_FEATS]}
TRAIN_SCANS = set(L.SCAN) if max(L.SCAN) <= 355 else set(range(5, 356, 5))
HYP_E_CUTS = [0.187, 0.2351, 0.2705, 0.3001, 0.3303, 0.3604, 0.3983, 0.4452, 0.5135]   # hyp_e logs/fit_model.log, full_gbm, rounded to 4


def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    cols = list(dict.fromkeys(['session', 'm', 'spot', 'straddle', 'mv30_bps', 't2'] + list(L.FEATURES)))
    D = L.with_period(pl.read_parquet(os.path.join(HYP_E, 'out', 'minutes_SPY_all.parquet'), columns=cols)).sort('session', 'm')
    Dt = D.filter(pl.col('t2').is_not_null())
    y = Dt['t2'].to_numpy().astype(int); per = Dt['period'].to_numpy(); sess = Dt['session'].to_numpy(); mm = Dt['m'].to_numpy()
    in_train = np.isin(mm, list(TRAIN_SCANS))
    fit = (per == 'fit') & in_train; cut = (per == 'cut') & in_train; fit_all = per == 'fit'
    ref = pl.read_parquet(os.path.join(HYP_E, 'out', 'scores_SPY.parquet'))
    ref_auc = pl.read_csv(os.path.join(HYP_E, 'out', 'model_auc.csv')).filter(pl.col('model') == 'full_gbm').to_dicts()[0]
    fixture_rows = []
    for key, feats in MODELS.items():
        X = Dt.select(feats).to_numpy().astype(float)
        mdl = lgb.LGBMClassifier(**HD.GBM)
        mdl.fit(X[fit], y[fit])                         # exactly hyp_e fit_gbm (numpy in, no names)
        p = mdl.predict_proba(X)[:, 1]
        us = np.unique(sess[fit]); blocks = np.array_split(us, HD.NFOLD); oof = np.full(len(y), np.nan)
        for b in blocks:
            te = fit_all & np.isin(sess, b); tr = fit & ~np.isin(sess, b)
            m_ = lgb.LGBMClassifier(**HD.GBM); m_.fit(X[tr], y[tr]); oof[te] = m_.predict_proba(X[te])[:, 1]
        cuts = np.quantile(p[cut], np.linspace(0.1, 0.9, 9))
        aucs = dict(fit_insample=HD.auc(y[fit], p[fit]), fit_oof=HD.auc(y[fit], oof[fit]), cut=HD.auc(y[cut], p[cut]))
        check = {}
        if key == 't2_spy_full':
            J = Dt.select('session', 'm').with_columns(pl.Series('p', p)).join(ref.select('session', 'm', 'full_gbm_score'), on=['session', 'm'], how='inner')
            d = float((J['p'] - J['full_gbm_score']).abs().max())
            check = dict(rows_compared=J.height, max_abs_score_diff_vs_hyp_e=d,
                         auc_vs_hyp_e={k: (aucs[k], float(ref_auc[f'auc_{k}'])) for k in ('fit_insample', 'fit_oof', 'cut')},
                         cuts_vs_hyp_e_logged=max(abs(float(a) - b) for a, b in zip(cuts, HYP_E_CUTS)) < 5e-5)
            if d > 1e-12 or not check['cuts_vs_hyp_e_logged'] or any(abs(a - b) > 1e-9 for a, b in check['auc_vs_hyp_e'].values()):
                raise SystemExit(f'the refit does not reproduce Hypothesis E: {check}')
        booster = mdl.booster_
        txt = os.path.join(HERE, f'{key}.txt')
        booster.save_model(txt, num_iteration=-1)
        # the saved text, read back, scores the same rows identically
        back = lgb.Booster(model_file=txt).predict(X)
        assert float(np.max(np.abs(back - p))) < 1e-12, 'the saved model does not score as the fitted one'
        cuts_f = os.path.join(HERE, f'{key}.cuts.json')
        with open(cuts_f, 'w') as f:
            json.dump({'model': key, 'cuts': [float(c) for c in cuts], 'from': 'the nine inner quantiles (0.1 .. 0.9) of the final score on '
                       'the cut slice 2024-07-01 -> 2024-12-31, scan minutes 09:35 .. 15:25', 'decile_rule': 'clip(searchsorted(cuts, score, '
                       'side="right"), 0, 9) + 1 (hyp_d model.decile_of)', 'n_cut_rows': int(cut.sum())}, f, indent=1)
        man = dict(model=key, kind='LightGBM binary classifier, t2 target (P[|30-minute move| > implied30])', product='SPY',
                   features=feats, n_features=len(feats), training_rows=int(fit.sum()), training_sessions=int(len(us)),
                   fit_period='sessions before 2024-07-01 (2022-11-11 ->)', train_scan_minutes='m = 5 .. 355 step 5 (09:35 .. 15:25)',
                   cut_period='2024-07-01 -> 2024-12-31', auc=aucs, base_rate_fit=float(y[fit].mean()), gbm_settings=HD.GBM,
                   lightgbm_version=lgb.__version__, model_file=os.path.basename(txt), model_sha256=sha256(txt),
                   cuts_file=os.path.basename(cuts_f), cuts_sha256=sha256(cuts_f), cuts=[float(c) for c in cuts],
                   source='research_notes/Compass phase 3/hyp_e_short_premium_lift/out/minutes_SPY_all.parquet (Theta Data bars, '
                          'chains and VIX prints; hyp_d lib.session_rows features)',
                   recipe='scripts/models/freeze_t2_spy.py = hyp_e fit_model.py full_gbm (feature list varies by model)',
                   frozen_at=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), reproduction_check=check)
        with open(os.path.join(HERE, f'{key}.manifest.json'), 'w') as f:
            json.dump(man, f, indent=1, default=float)
        print(key, json.dumps({k: man[k] for k in ('n_features', 'training_rows', 'auc', 'model_sha256')}, default=float), check or '', flush=True)
        # fixture rows: a scan minute in each decile of the cut slice (and one with NaNs), LightGBM's own score
        dec = HD.decile_of(p, cuts)
        rng = np.random.default_rng(20261021)
        for d_ in range(1, 11):
            idx = np.flatnonzero(cut & (dec == d_))
            i = int(rng.choice(idx))
            fixture_rows.append(dict(model=key, session=str(sess[i]), m=int(mm[i]), features={f: (None if not np.isfinite(X[i, j]) else float(X[i, j])) for j, f in enumerate(feats)},
                                     score=float(p[i]), decile=int(dec[i])))
    with open(os.path.join(REPO, 'tests', 'fixtures', 't2_feature_rows.json'), 'w') as f:
        json.dump({'_about': 'feature rows from hyp_e minutes_SPY_all.parquet (cut slice), scored by LightGBM at freeze time '
                   '(scripts/models/freeze_t2_spy.py); the tracker\'s loader must give the same score and decile', 'rows': fixture_rows}, f, indent=1)


if __name__ == '__main__':
    main()
