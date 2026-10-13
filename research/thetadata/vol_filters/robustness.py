"""Supplementary checks: elasticity of the afternoon move on the morning range, the skip rules under an alternative scale
(trailing 20-day geometric mean of the afternoon range), Wednesday ex-FOMC, and half-size instead of skip. Local files only."""
import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
S = pd.read_csv(os.path.join(OUT, 'sample.csv')); D = pd.read_csv(os.path.join(OUT, 'daily.csv'))[['date', 'base20_log_range_pm', 'prev_range_mean20']]
S = S.merge(D, on='date', how='left'); S['train'] = S['train'].astype(bool)
rng = np.random.default_rng(20251013); B = 2000; L = 20
def block_idx(n):
    nb = int(np.ceil(n / L)); st = rng.integers(0, n - L + 1, size=(B, nb)); return (st[:, :, None] + np.arange(L)[None, None, :]).reshape(B, -1)[:, :n]
def ci(a): a = np.asarray(a, float); a = a[np.isfinite(a)]; return np.percentile(a, 2.5), np.percentile(a, 97.5)
tr = S[S['train']]; te = S[~S['train']]
print('=== elasticity: OLS slope of log(afternoon target) on log(09:30-13:00 range) ===')
for tgt in ('range_pm', 'absmove_pm'):
    for name, sub in (('train', tr), ('test', te)):
        x = np.log(sub['range_0930_1300'].values); y = np.log(sub[tgt].values + (1e-4 if tgt == 'absmove_pm' else 0)); idx = block_idx(len(x))
        b = np.polyfit(x, y, 1)[0]; bs = [np.polyfit(x[i], y[i], 1)[0] for i in idx[:1000]]
        print(f'{tgt:12s} {name:5s} slope {b:.3f} CI [{ci(bs)[0]:.3f}, {ci(bs)[1]:.3f}] n={len(x)}')
print('\n=== Wednesday ex-FOMC vs other non-event days (ratio of means) ===')
for name, sub in (('all', S), ('test', te)):
    clean = sub[(sub['fomc'] == 0) & (sub['cpi'] == 0) & (sub['nfp'] == 0) & (sub['opex'] == 0)]
    w = clean[clean['dow'] == 2]; o = clean[clean['dow'] != 2]
    for t in ('absmove_pm', 'range_pm', 'ratio'):
        ia = rng.integers(0, len(w), size=(B, len(w))); ib = rng.integers(0, len(o), size=(B, len(o)))
        r = w[t].mean() / o[t].mean(); bs = w[t].values[ia].mean(1) / o[t].values[ib].mean(1)
        print(f'{name:4s} {t:11s} wed_exFOMC/other {r:.3f} CI [{ci(bs)[0]:.3f}, {ci(bs)[1]:.3f}] n_wed={len(w)} n_other={len(o)}')
print('\n=== alternative scale: trailing 20-day geometric mean of the afternoon range (known at 13:00) ===')
S['scale_alt'] = np.exp(S['base20_log_range_pm']); S['ratio_alt'] = S['absmove_pm'] / S['scale_alt']
ok = S['ratio_alt'].notna(); tr = S[S['train'] & ok]; te = S[(~S['train']) & ok]
k_alt = float(tr['ratio_alt'].mean()); print(f'k_alt (train mean of |pm move| / scale_alt) = {k_alt:.4f}; test mean {te["ratio_alt"].mean():.4f}; train hit {(tr["ratio_alt"] < k_alt).mean():.3f} test hit {(te["ratio_alt"] < k_alt).mean():.3f}')
q = lambda c, p: float(tr[c].quantile(p))
RULES = {'skip_fomc': S['fomc'] == 1, 'skip_cpi': S['cpi'] == 1, 'skip_nfp': S['nfp'] == 1, 'skip_opex': S['opex'] == 1, 'skip_any_event': (S['fomc'] + S['cpi'] + S['nfp']) > 0,
         'skip_amrange_rel20_lt0.5': S['amrange_rel20'] < 0.5, 'skip_amrange_lo_p20': S['range_0930_1300'] < q('range_0930_1300', 0.2), 'skip_amrange_hi_p80': S['range_0930_1300'] > q('range_0930_1300', 0.8),
         'skip_vix_gt_60d_p80': S['vix_hi_60d'] == 1, 'skip_vix_rise_gt10pct': S['vix_chg_open_1300'] > 0.10, 'skip_vix_gt_train_p80': S['vix_1300'] > q('vix_1300', 0.8),
         'skip_wed': S['dow'] == 2, 'skip_mon': S['dow'] == 0, 'skip_month_end': S['month_end'] == 1, 'skip_gap_hi_p80': S['absgap'] > q('absgap', 0.8), 'skip_prevrange_hi_p80': S['prev_range'] > q('prev_range', 0.8),
         'skip_am_gt_prevday_range': S['range_0930_1300'] > S['prev_range'], 'skip_eff_am_hi_p80': S['eff_am'] > q('eff_am', 0.8)}
RULES['skip_fomc | skip_amrange_rel20_lt0.5'] = RULES['skip_fomc'] | RULES['skip_amrange_rel20_lt0.5']
rows = []
for name, sub in (('train', tr), ('test', te)):
    r = sub['ratio_alt'].values; idx = block_idx(len(r)); o_all = k_alt - r
    for rn, skip in RULES.items():
        m = ~skip.fillna(False).values[sub.index]; o = np.where(m, o_all, 0.0); d = o - o_all; lo, hi = ci(d[idx].mean(1))
        rows.append(dict(sample=name, rule=rn, share_traded=m.mean(), hit=(r[m] < k_alt).mean(), hit_delta=(r[m] < k_alt).mean() - (r < k_alt).mean(), delta_per_trading_day=d.mean(), ci_lo=lo, ci_hi=hi))
R = pd.DataFrame(rows); R.to_csv(os.path.join(OUT, 'rules_alt_scale.csv'), index=False, float_format='%.5g')
piv = R.pivot(index='rule', columns='sample', values=['share_traded', 'hit_delta', 'delta_per_trading_day', 'ci_lo', 'ci_hi'])
piv.columns = [f'{a}_{b}' for a, b in piv.columns]
print(piv[['share_traded_test', 'hit_delta_train', 'hit_delta_test', 'delta_per_trading_day_train', 'delta_per_trading_day_test', 'ci_lo_test', 'ci_hi_test']].sort_values('delta_per_trading_day_train', ascending=False).round(4).to_string())
print('\n=== half-size instead of skip (primary scale, k_fair): outcome x0.5 on flagged days; test ===')
RS = pd.read_csv(os.path.join(OUT, 'rules_single.csv')); k_fair = float(RS.loc[RS['k_name'] == 'k_fair_train', 'k'].iloc[0])
te2 = S[~S['train']]; r = te2['ratio'].values; idx = block_idx(len(r)); o_all = k_fair - r
for rn in ('skip_amrange_rel20_lt0.5', 'skip_fomc', 'skip_fomc | skip_amrange_rel20_lt0.5', 'skip_amrange_lo_p20', 'skip_wed'):
    f = RULES[rn].fillna(False).values[te2.index]
    for mult, lab in ((0.0, 'skip'), (0.5, 'half')):
        o = np.where(f, mult * o_all, o_all); d = o - o_all; lo, hi = ci(d[idx].mean(1))
        print(f'{rn:42s} {lab:4s} delta/trading day {d.mean():+.4f} CI [{lo:+.4f}, {hi:+.4f}]  mean/day {o.mean():+.4f}')
print('\n=== k robustness (test): delta per trading day for key rules at each k ===')
sub = RS[(RS['sample'] == 'test') & RS['rule'].isin(['skip_fomc', 'skip_any_event', 'skip_amrange_rel20_lt0.5', 'skip_amrange_lo_p20', 'skip_wed', 'skip_vix_gt_60d_p80', 'skip_vix_rise_gt10pct', 'skip_month_end', 'skip_cpi', 'skip_nfp', 'skip_opex'])]
print(sub.pivot(index='rule', columns='k_name', values='delta_per_trading_day').round(4).to_string())
print('\nhit rate (test) by k:'); print(sub.pivot(index='rule', columns='k_name', values='hit_rate').round(3).to_string())
print('\ntrade_all test:'); print(RS[(RS['sample'] == 'test') & (RS['rule'] == 'trade_all')][['k_name', 'k', 'hit_rate', 'mean_per_trading_day', 'mean_ci_lo', 'mean_ci_hi', 'mean_pct_per_trading_day']].round(4).to_string(index=False))
print('\n=== index-% deltas (premium k*range - |move|, % of SPX) per trading day, test, k_fair ===')
sub = RS[(RS['sample'] == 'test') & (RS['k_name'] == 'k_fair_train')].set_index('rule')
print(sub.loc[['skip_fomc', 'skip_any_event', 'skip_amrange_rel20_lt0.5', 'skip_amrange_lo_p20', 'skip_wed', 'skip_vix_gt_60d_p80', 'skip_vix_gt_train_p80', 'skip_vix_rise_gt10pct', 'skip_month_end', 'skip_cpi', 'skip_nfp', 'skip_opex', 'skip_amrange_hi_p80', 'skip_prevrange_hi_p80', 'skip_gap_hi_p80'], ['share_traded', 'hit_rate', 'hit_ci_lo', 'hit_ci_hi', 'delta_pct_per_trading_day', 'delta_pct_ci_lo', 'delta_pct_ci_hi', 'worst_traded']].round(4).to_string())
