"""Q4: the score. A logistic regression (and a gradient-boosted check) fitted on 2022-24 sweep events of the merged
trigger (any level, X=0, k=1, confirm=0, one entry a minute and side) with the features the spec names or implies,
scored once on 2025-26. Outcomes: (A) the fade trade's net result > 0 (nearest OTM, 50% trailing stop, fees in);
(B) the underlying moves >= 10 bps in the fade direction within 30 minutes (fwd_max30 >= 10).
Reports out-of-sample AUC, calibration by decile, the EV after fees of the top decile and top two deciles (the A+ / A
analogue) against the plain gate (every event), with the day-bootstrap stress test.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I score.py
"""
import os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S
from common_analysis import load_events, fmt
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

NUM = ['depth_bps', 'm', 'or_pos', 'rel_vol', 'vix', 'fo_dist_str', 'day_move_atr', 'fvg', 'ob', 'straddle_rel', 'range_r_bps', 'fo_spr', 'fo_ask', 'bars_out']
CAT = {'level': ['OR', 'PD', 'PW', 'SH'], 'window': ['fade1', 'fade2', 'fade3', 'chase1', 'chase2', 'noon'], 'product': ['SPY', 'QQQ', 'IWM', 'SPXW'], 'side': ['hi', 'lo']}

def design(df):
    X = df.select(NUM).to_numpy().astype(float)
    cols = list(NUM)
    for c, levels in CAT.items():
        v = df[c].to_numpy()
        for lv in levels[1:]:
            X = np.column_stack([X, (v == lv).astype(float)]); cols.append(f'{c}={lv}')
    # fill missing with the training median (set by caller) -> here NaN handled by caller
    return X, cols

def deciles(score, y, net, k=10):
    q = np.quantile(score, np.linspace(0, 1, k + 1)); q[0] -= 1e-9; q[-1] += 1e-9
    d = np.clip(np.searchsorted(q, score, side='right') - 1, 0, k - 1)
    rows = []
    for i in range(k):
        m = d == i
        rows.append(dict(decile=i + 1, n=int(m.sum()), score_mean=float(score[m].mean()), outcome_rate=float(y[m].mean()), net_usd=float(net[m].mean()), win=float((net[m] > 0).mean())))
    return pl.DataFrame(rows), d

if __name__ == '__main__':
    E = load_events().filter((pl.col('level') != 'DISP') & (pl.col('X') == 0) & (pl.col('k') == '1') & (pl.col('confirm') == 0))
    # the merged trigger: one entry a (product, session, minute, side); keep the level with the highest priority OR > PD > PW > SH for the level feature
    pri = {'OR': 0, 'PD': 1, 'PW': 2, 'SH': 3}
    E = E.with_columns(pl.col('level').replace_strict(pri).alias('_p')).sort('_p').unique(['product', 'session', 'entry_m', 'side'], keep='first').drop('_p')
    E = E.filter(pl.col('fo_ask').is_not_null())
    E = E.with_columns((pl.col('fo_trail_net') > 0).cast(pl.Int8).alias('yA'), (pl.col('fwd_max30') >= 10).cast(pl.Int8).alias('yB'))
    tr = E.filter(pl.col('period') == '2022-24'); te = E.filter(pl.col('period') == '2025-26')
    print('train', tr.height, 'test', te.height, 'base rates A', float(tr['yA'].mean()), float(te['yA'].mean()), 'B', float(tr['yB'].mean()), float(te['yB'].mean()))
    Xtr, cols = design(tr); Xte, _ = design(te)
    med = np.nanmedian(Xtr, axis=0); Xtr = np.where(np.isnan(Xtr), med, Xtr); Xte = np.where(np.isnan(Xte), med, Xte)
    out = []
    for yname, exitcol in (('yA', 'fo_trail_net'), ('yB', 'fo_trail_net')):
        ytr = tr[yname].to_numpy(); yte = te[yname].to_numpy(); net_te = te[exitcol].to_numpy(); net_tr = tr[exitcol].to_numpy()
        for model_name, model in (('logistic', make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000))),
                                  ('gbm', HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=200, random_state=1))):
            model.fit(Xtr, ytr)
            p_tr = model.predict_proba(Xtr)[:, 1]; p_te = model.predict_proba(Xte)[:, 1]
            auc_tr = roc_auc_score(ytr, p_tr); auc_te = roc_auc_score(yte, p_te)
            print(f'\n==== outcome {yname}, {model_name}: AUC train {auc_tr:.3f}  test {auc_te:.3f}')
            if model_name == 'logistic':
                coef = model.named_steps['logisticregression'].coef_[0]
                order = np.argsort(-np.abs(coef))
                print('   standardised coefficients:', ', '.join(f'{cols[i]} {coef[i]:+.3f}' for i in order[:14]))
            D, d = deciles(p_te, yte, net_te); print('-- calibration and EV by decile, 2025-26 (score 1 = lowest)'); print(fmt(D))
            D.with_columns(pl.lit(yname).alias('outcome'), pl.lit(model_name).alias('model')).write_csv(os.path.join(S.OUT, f'score_deciles_{yname}_{model_name}.csv'))
            # thresholds set on TRAIN: the top 10% and 20% of train scores
            for share in (0.10, 0.20):
                thr = np.quantile(p_tr, 1 - share)
                sel = te.with_columns(pl.Series('p', p_te)).filter(pl.col('p') >= thr)
                sel_tr = tr.with_columns(pl.Series('p', p_tr)).filter(pl.col('p') >= thr)
                st = S.stress(sel, exitcol); st_tr = S.stress(sel_tr, exitcol)
                print(f'   top {int(share*100)}% by train threshold {thr:.3f}: train n={st_tr["n"]} mean={st_tr["mean"]:.2f}$ | test n={st["n"]} mean={st["mean"]:.2f}$ win={float((sel[exitcol] > 0).mean()):.3f} '
                      f'95% [{st["lo95"]:.2f}, {st["hi95"]:.2f}] wo_best5={st["wo_best5"]:.2f} days_up={st["days_up"]}/{st["days"]}')
                for ex in ('tgt', 'hold'):
                    st2 = S.stress(sel, f'fo_{ex}_net'); print(f'      {ex}: test mean={st2["mean"]:.2f}$ 95% [{st2["lo95"]:.2f}, {st2["hi95"]:.2f}] wo_best5={st2["wo_best5"]:.2f}')
                by_year = sel.group_by('year').agg(pl.len().alias('n'), pl.col(exitcol).mean().alias('usd')).sort('year'); print('      by year:', by_year.to_dicts())
                by_prod = sel.group_by('product').agg(pl.len().alias('n'), pl.col(exitcol).mean().alias('usd'), (pl.col(exitcol) > 0).mean().alias('win')).sort('product'); print('      by product:', by_prod.to_dicts())
                out.append(dict(outcome=yname, model=model_name, share=share, thr=float(thr), auc_train=float(auc_tr), auc_test=float(auc_te), train_n=st_tr['n'], train_usd=st_tr['mean'], test_n=st['n'], test_usd=st['mean'], lo95=st['lo95'], hi95=st['hi95'], wo_best5=st['wo_best5'], days_up=st['days_up'], days=st['days']))
    gate = S.stress(te, 'fo_trail_net'); gate_tr = S.stress(tr, 'fo_trail_net')
    print(f'\n== the plain gate (every merged sweep, fade, trailing stop): train mean={gate_tr["mean"]:.2f}$ n={gate_tr["n"]} | test mean={gate["mean"]:.2f}$ n={gate["n"]} 95% [{gate["lo95"]:.2f}, {gate["hi95"]:.2f}] wo_best5={gate["wo_best5"]:.2f} days_up={gate["days_up"]}/{gate["days"]}')
    pl.DataFrame(out).write_csv(os.path.join(S.OUT, 'score_summary.csv'))
    # single-feature deciles on train for the notes: depth, rel_vol, dist in straddle units
    print('\n== single features, outcome A rate and trail $ by quintile (2022-24 / 2025-26)')
    for f in ('depth_bps', 'rel_vol', 'fo_dist_str', 'vix', 'day_move_atr', 'm'):
        for per, df in (('2022-24', tr), ('2025-26', te)):
            x = df[f].to_numpy().astype(float); ok = ~np.isnan(x)
            q = np.quantile(x[ok], [0, .2, .4, .6, .8, 1]); q[-1] += 1e-9
            b = np.clip(np.searchsorted(q, x, side='right') - 1, 0, 4)
            line = []
            for i in range(5):
                m = ok & (b == i); line.append(f'[{q[i]:.2g},{q[i+1]:.2g}) n={m.sum()} A={df["yA"].to_numpy()[m].mean():.3f} ${df["fo_trail_net"].to_numpy()[m].mean():.1f}')
            print(f'  {f} {per}: ' + ' | '.join(line))
