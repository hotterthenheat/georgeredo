"""Empirical study: which intraday volatility / regime variables predict the SPX afternoon (13:00-16:00) absolute move and
range, and how skip rules built from them change a stylized short-premium payoff. Fit on 2017-2022, test on 2023-2026.
All CIs are moving-block bootstraps over trading days (block length 20). Reads only local files; seeds fixed."""
import os, sys, glob, gzip, json, re, itertools, datetime as dt
import numpy as np, pandas as pd
from scipy import stats
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
BT_CACHE = os.path.join(SP, 'bt', 'cache')
SEED = 20251013; B_RULES = 2000; B_IC = 1000; BLOCK = 20
TRAIN_END = '2022-12-31'; GEX_START = '2024-05-13'

D = pd.read_csv(os.path.join(OUT, 'daily.csv'))
ev = pd.read_csv(os.path.join(HERE, 'events.csv'))
for e in ('FOMC', 'CPI', 'NFP'):
    D[e.lower()] = D['date'].isin(set(ev.loc[ev['event'] == e, 'date'])).astype(int)
D['any_event'] = ((D['fomc'] + D['cpi'] + D['nfp']) > 0).astype(int)
D['any_event_opex'] = ((D['any_event'] + D['opex']) > 0).astype(int)
# UW SPY gex-levels from the local cache only (prior-day gamma flip vs prior-day SPY close)
gf = {}
for f in glob.glob(os.path.join(BT_CACHE, '*_stock_SPY_gex-levels_date-*.json.gz')):
    m = re.search(r'date-(\d{4}-\d{2}-\d{2})\.json\.gz$', f)
    try:
        with gzip.open(f, 'rt') as fh: d = (json.load(fh).get('data') or {})
        gf[m.group(1)] = float(d.get('gamma_flip')) if d.get('gamma_flip') is not None else np.nan
    except Exception: pass
G = pd.DataFrame({'date': list(gf.keys()), 'gamma_flip': list(gf.values())}).sort_values('date')
D = D.merge(G, on='date', how='left'); D['gamma_flip_prev'] = D['gamma_flip'].shift(1)
D['neg_gamma_prev'] = np.where(D['gamma_flip_prev'].notna() & D['spy_prev_close'].notna(), (D['spy_prev_close'] < D['gamma_flip_prev']).astype(float), np.nan)
D.loc[D['date'] < GEX_START, 'neg_gamma_prev'] = np.nan
print('gex cache dates', len(G), 'with gamma_flip', int(G['gamma_flip'].notna().sum()), 'neg_gamma_prev available days', int(D['neg_gamma_prev'].notna().sum()))

# ---------- sample ----------
S = D[D['early_close'] == 0].copy().reset_index(drop=True)
S['ratio'] = S['absmove_pm'] / S['range_0930_1300']; S['ratio_range'] = S['range_pm'] / S['range_0930_1300']
S['eff_am'] = S['absmove_am'] / S['range_0930_1300']
S['amrange_rel20'] = S['range_0930_1300'] / S['prev_range_mean20']
S['am_gt_prev'] = (S['range_0930_1300'] > S['prev_range']).astype(float)
S['vix_hi_60d'] = (S['vix_1300'] > S['vix1300_p80_60d']).astype(float)
S['vix_hi_60d_open'] = (S['vix_0931'] > S['vix0931_p80_60d']).astype(float)
S['y_pm_range'] = np.log(S['range_pm']); S['y_day_range'] = np.log(S['range_day']); S['y_pm_abs'] = np.log(S['absmove_pm'] + 1e-4)
S['train'] = S['date'] <= TRAIN_END; S['test'] = ~S['train']
print('sample days', len(S), 'train', int(S['train'].sum()), 'test', int(S['test'].sum()))
for c in ('range_0930_1030', 'rv_0930_1030', 'range_0930_1300', 'rv_0930_1300', 'vix_0931', 'vix_1300', 'prev_range', 'prev_rv5', 'prev_rv20', 'absgap'):
    S['log_' + c] = np.log(S[c].clip(lower=1e-6))
for k in range(5): S[f'dow{k}'] = (S['dow'] == k).astype(int)

PRED = [('log_range_0930_1030', '(a) log range 09:30-10:30'), ('log_rv_0930_1030', '(a) log RV 09:30-10:30'),
        ('log_range_0930_1300', '(a) log range 09:30-13:00'), ('log_rv_0930_1300', '(a) log RV 09:30-13:00'), ('eff_am', '(a) morning efficiency |move|/range'),
        ('log_vix_0931', '(b) log VIX 09:31'), ('log_vix_1300', '(b) log VIX 13:00'), ('vix_chg_open_1300', '(b) VIX change open->13:00'), ('vix_hi_60d', '(b) VIX13 > 60d p80'),
        ('log_prev_range', '(c) log prior-day range'), ('log_prev_rv5', '(c) log 5d RV'), ('log_prev_rv20', '(c) log 20d RV'),
        ('fomc', '(d) FOMC'), ('cpi', '(d) CPI'), ('nfp', '(d) NFP'), ('opex', '(d) monthly opex'), ('quad_opex', '(d) quarterly opex'), ('any_event', '(d) FOMC|CPI|NFP'),
        ('dow0', '(e) Monday'), ('dow1', '(e) Tuesday'), ('dow2', '(e) Wednesday'), ('dow3', '(e) Thursday'), ('dow4', '(e) Friday'),
        ('month_end', '(e) month-end'), ('holiday_adj', '(e) holiday-adjacent'), ('pre_holiday', '(e) pre-holiday'), ('post_holiday', '(e) post-holiday'),
        ('log_absgap', '(f) log |overnight gap|'), ('neg_gamma_prev', '(g) prior-day SPY close < UW gamma flip (2024-05-13+)')]
TGT = [('absmove_pm', '|13:00->16:00 move|'), ('range_pm', '13:00-16:00 range'), ('ratio', '|pm move| / morning range'), ('range_day', 'full-day range')]

rng = np.random.default_rng(SEED)
def block_idx(n, B, L=BLOCK):
    nb = int(np.ceil(n / L)); starts = rng.integers(0, n - L + 1, size=(B, nb))
    idx = (starts[:, :, None] + np.arange(L)[None, None, :]).reshape(B, -1)[:, :n]
    return idx
def ci(a, lo=2.5, hi=97.5): a = np.asarray(a, float); a = a[np.isfinite(a)]; return (np.percentile(a, lo), np.percentile(a, hi)) if len(a) else (np.nan, np.nan)

# ---------- 1. Spearman IC ----------
ic_rows = []
for sub_name, mask in (('all', np.ones(len(S), bool)), ('train', S['train'].values), ('test', S['test'].values)):
    sub = S[mask]
    for p, plab in PRED:
        for t, tlab in TGT:
            ok = sub[[p, t]].notna().all(axis=1).values; x = sub[p].values[ok]; y = sub[t].values[ok]; n = len(x)
            if n < 50 or np.nanstd(x) == 0: continue
            r = stats.spearmanr(x, y).correlation
            idx = block_idx(n, B_IC)
            RX = stats.rankdata(x[idx], axis=1); RY = stats.rankdata(y[idx], axis=1)
            RX = RX - RX.mean(1, keepdims=True); RY = RY - RY.mean(1, keepdims=True)
            den = np.sqrt((RX * RX).sum(1) * (RY * RY).sum(1)); bs = np.where(den > 0, (RX * RY).sum(1) / den, np.nan)
            lo, hi = ci(bs)
            ic_rows.append(dict(sample=sub_name, predictor=p, predictor_label=plab, target=t, target_label=tlab, n=n, spearman=r, ci_lo=lo, ci_hi=hi, mean_x1=(y[x == 1].mean() if set(np.unique(x)) <= {0, 1} else np.nan), mean_x0=(y[x == 0].mean() if set(np.unique(x)) <= {0, 1} else np.nan)))
IC = pd.DataFrame(ic_rows); IC.to_csv(os.path.join(OUT, 'ic_spearman.csv'), index=False, float_format='%.4f')
print('\n=== Spearman IC (all days, 13:00-16:00 |move| and range) ===')
print(IC[(IC['sample'] == 'all') & (IC['target'].isin(['absmove_pm', 'range_pm']))].pivot(index='predictor_label', columns='target', values='spearman').round(3).to_string())

# ---------- 2. OOS R2 of linear models on log ranges ----------
def ols_fit(X, y):
    Xa = np.column_stack([np.ones(len(X)), X]); beta, *_ = np.linalg.lstsq(Xa, y, rcond=None); return beta
def ols_pred(X, beta): return np.column_stack([np.ones(len(X)), X]) @ beta
GROUPS = {'morning_1030': ['log_range_0930_1030', 'log_rv_0930_1030'], 'morning_1300': ['log_range_0930_1300', 'log_rv_0930_1300', 'eff_am'],
          'vix': ['log_vix_0931', 'log_vix_1300', 'vix_chg_open_1300'], 'prior': ['log_prev_range', 'log_prev_rv5', 'log_prev_rv20'],
          'calendar': ['fomc', 'cpi', 'nfp', 'opex', 'dow0', 'dow1', 'dow2', 'dow3', 'month_end', 'holiday_adj'], 'gap': ['log_absgap']}
GROUPS['all_1300'] = GROUPS['morning_1030'] + GROUPS['morning_1300'] + GROUPS['vix'] + GROUPS['prior'] + GROUPS['calendar'] + GROUPS['gap']
GROUPS['all_1030'] = GROUPS['morning_1030'] + ['log_vix_0931'] + GROUPS['prior'] + GROUPS['calendar'] + GROUPS['gap']
GROUPS['all_open'] = ['log_vix_0931'] + GROUPS['prior'] + GROUPS['calendar'] + GROUPS['gap']
r2_rows = []
for tgt, base_col in (('y_pm_range', 'base20_log_range_pm'), ('y_day_range', 'base20_log_range_day'), ('y_pm_abs', 'base20_log_absmove_pm')):
    specs = [(p, [p]) for p, _ in PRED if p != 'neg_gamma_prev'] + list(GROUPS.items())
    for name, cols in specs:
        need = cols + [tgt, base_col]; ok = S[need].notna().all(axis=1)
        tr = S[ok & S['train']]; te = S[ok & S['test']]
        if len(tr) < 100 or len(te) < 100: continue
        beta = ols_fit(tr[cols].values, tr[tgt].values); pred = ols_pred(te[cols].values, beta); y = te[tgt].values
        e_m = (y - pred) ** 2; e_c = (y - tr[tgt].mean()) ** 2; e_b = (y - te[base_col].values) ** 2
        r2c = 1 - e_m.sum() / e_c.sum(); r2b = 1 - e_m.sum() / e_b.sum()
        idx = block_idx(len(te), B_RULES); bc = 1 - e_m[idx].sum(1) / e_c[idx].sum(1); bb = 1 - e_m[idx].sum(1) / e_b[idx].sum(1)
        tr_r2 = 1 - ((tr[tgt].values - ols_pred(tr[cols].values, beta)) ** 2).sum() / ((tr[tgt].values - tr[tgt].mean()) ** 2).sum()
        r2_rows.append(dict(target=tgt, model=name, k=len(cols), n_train=len(tr), n_test=len(te), r2_train=tr_r2, r2_oos_vs_trainmean=r2c, ci_lo_c=ci(bc)[0], ci_hi_c=ci(bc)[1],
                            r2_oos_vs_trailing20=r2b, ci_lo_b=ci(bb)[0], ci_hi_b=ci(bb)[1], r2_trailing20_vs_trainmean=1 - e_b.sum() / e_c.sum()))
R2 = pd.DataFrame(r2_rows); R2.to_csv(os.path.join(OUT, 'oos_r2.csv'), index=False, float_format='%.4f')
print('\n=== OOS R2 (test 2023-2026) vs train-mean benchmark; log afternoon range ===')
print(R2[R2['target'] == 'y_pm_range'].sort_values('r2_oos_vs_trainmean', ascending=False)[['model', 'k', 'r2_train', 'r2_oos_vs_trainmean', 'ci_lo_c', 'ci_hi_c', 'r2_oos_vs_trailing20', 'ci_lo_b', 'ci_hi_b']].round(3).to_string(index=False))

# ---------- 3. Event-day ratios ----------
ev_rows = []
for sub_name, mask in (('all', np.ones(len(S), bool)), ('train', S['train'].values), ('test', S['test'].values)):
    sub = S[mask]
    for flag in ('fomc', 'cpi', 'nfp', 'opex', 'quad_opex', 'any_event', 'month_end', 'holiday_adj', 'pre_holiday', 'post_holiday', 'dow0', 'dow1', 'dow2', 'dow3', 'dow4', 'vix_hi_60d', 'neg_gamma_prev', 'am_gt_prev'):
        ok = sub[flag].notna(); a = sub[ok & (sub[flag] == 1)]; b = sub[ok & (sub[flag] == 0)]
        if flag in ('fomc', 'cpi', 'nfp', 'opex', 'quad_opex'): b = sub[ok & (sub['any_event_opex'] == 0)]  # compare against clean days
        if len(a) < 5 or len(b) < 20: continue
        for t in ('absmove_pm', 'range_pm', 'ratio', 'range_0930_1300', 'range_day'):
            ra = a[t].values; rb = b[t].values
            ratio = ra.mean() / rb.mean(); med_ratio = np.median(ra) / np.median(rb)
            ia = rng.integers(0, len(ra), size=(B_RULES, len(ra))); ib = block_idx(len(rb), B_RULES)
            bs = ra[ia].mean(1) / rb[ib].mean(1); lo, hi = ci(bs)
            ev_rows.append(dict(sample=sub_name, flag=flag, target=t, n_flag=len(a), n_other=len(b), mean_flag=ra.mean(), mean_other=rb.mean(), ratio_mean=ratio, ci_lo=lo, ci_hi=hi, ratio_median=med_ratio))
EV = pd.DataFrame(ev_rows); EV.to_csv(os.path.join(OUT, 'event_ratios.csv'), index=False, float_format='%.5g')
print('\n=== Ratio of mean |pm move| and pm range, flag days / clean days (all days) ===')
print(EV[(EV['sample'] == 'all') & (EV['target'].isin(['absmove_pm', 'range_pm', 'ratio']))].pivot(index='flag', columns='target', values=['ratio_mean']).round(3).to_string())

# ---------- 4. Stylized short-premium payoff and skip rules ----------
tr = S[S['train']]; te = S[S['test']]
q = lambda col, p: float(tr[col].quantile(p))
k_fair = float(tr['ratio'].mean()); k_med = float(tr['ratio'].median())
print(f'\nratio |pm move|/morning range: train mean {k_fair:.4f} median {k_med:.4f}; test mean {te["ratio"].mean():.4f} median {te["ratio"].median():.4f}')
TH = dict(vix_abs=q('vix_1300', 0.8), amr_lo=q('range_0930_1300', 0.2), amr_hi=q('range_0930_1300', 0.8), gap_hi=q('absgap', 0.8), prev_hi=q('prev_range', 0.8), rv5_hi=q('prev_rv5', 0.8), eff_hi=q('eff_am', 0.8), rv1030_hi=q('rv_0930_1030', 0.8), amrel_lo=0.5)
print('train thresholds', {k: round(v, 5) for k, v in TH.items()})
RULES = {
    'skip_fomc': S['fomc'] == 1, 'skip_cpi': S['cpi'] == 1, 'skip_nfp': S['nfp'] == 1, 'skip_opex': S['opex'] == 1, 'skip_quad_opex': S['quad_opex'] == 1,
    'skip_any_event': S['any_event'] == 1, 'skip_any_event_or_opex': S['any_event_opex'] == 1,
    'skip_vix_gt_60d_p80': S['vix_hi_60d'] == 1, 'skip_vix_open_gt_60d_p80': S['vix_hi_60d_open'] == 1, 'skip_vix_gt_train_p80': S['vix_1300'] > TH['vix_abs'],
    'skip_vix_rise_gt10pct': S['vix_chg_open_1300'] > 0.10, 'skip_vix_rise_gt5pct': S['vix_chg_open_1300'] > 0.05, 'skip_vix_fall_gt10pct': S['vix_chg_open_1300'] < -0.10,
    'skip_amrange_lo_p20': S['range_0930_1300'] < TH['amr_lo'], 'skip_amrange_hi_p80': S['range_0930_1300'] > TH['amr_hi'], 'skip_amrange_rel20_lt0.5': S['amrange_rel20'] < TH['amrel_lo'],
    'skip_am_gt_prevday_range': S['am_gt_prev'] == 1, 'skip_eff_am_hi_p80': S['eff_am'] > TH['eff_hi'], 'skip_rv1030_hi_p80': S['rv_0930_1030'] > TH['rv1030_hi'],
    'skip_gap_hi_p80': S['absgap'] > TH['gap_hi'], 'skip_prevrange_hi_p80': S['prev_range'] > TH['prev_hi'], 'skip_rv5_hi_p80': S['prev_rv5'] > TH['rv5_hi'],
    'skip_mon': S['dow'] == 0, 'skip_tue': S['dow'] == 1, 'skip_wed': S['dow'] == 2, 'skip_thu': S['dow'] == 3, 'skip_fri': S['dow'] == 4,
    'skip_month_end': S['month_end'] == 1, 'skip_holiday_adj': S['holiday_adj'] == 1, 'skip_pre_holiday': S['pre_holiday'] == 1, 'skip_post_holiday': S['post_holiday'] == 1,
}
RULES = {k: v.fillna(False).values.astype(bool) for k, v in RULES.items()}
KS = {'k_fair_train': k_fair, 'k_1.0': 1.0, 'k_0.75': 0.75, 'k_0.5': 0.5}

def payoff_stats(mask_trade, sub_mask, k, idx=None):
    """Outcome per day = k - ratio (units of morning range) when traded, 0 when skipped. Returns dict + bootstrap of mean per trading day and of delta vs trade-all."""
    r = S['ratio'].values[sub_mask]; m = mask_trade[sub_mask]; o = np.where(m, k - r, 0.0); o_all = k - r
    # index-% version: premium k*scale minus |move|, in % of SPX
    scale = S['range_0930_1300'].values[sub_mask]; mv = S['absmove_pm'].values[sub_mask]; o_pct = np.where(m, k * scale - mv, 0.0) * 100; o_pct_all = (k * scale - mv) * 100
    n = len(r); nt = int(m.sum())
    d = dict(n_days=n, n_traded=nt, share_traded=nt / n, hit_rate=float((r[m] < k).mean()) if nt else np.nan, hit_rate_all=float((r < k).mean()),
             mean_per_traded_day=float(o[m].mean()) if nt else np.nan, mean_per_trading_day=float(o.mean()), mean_all_days=float(o_all.mean()),
             delta_per_trading_day=float(o.mean() - o_all.mean()), mean_pct_per_trading_day=float(o_pct.mean()), delta_pct_per_trading_day=float(o_pct.mean() - o_pct_all.mean()),
             hit_rate_delta=(float((r[m] < k).mean() - (r < k).mean()) if nt else np.nan), worst_traded=float(o[m].min()) if nt else np.nan)
    if idx is not None:
        dd = (o - o_all); bs = dd[idx].mean(1); d['delta_ci_lo'], d['delta_ci_hi'] = ci(bs)
        bm = o[idx].mean(1); d['mean_ci_lo'], d['mean_ci_hi'] = ci(bm)
        hb = []; mb = m[idx]; rb = r[idx]
        for i in range(min(500, idx.shape[0])):
            if mb[i].sum(): hb.append((rb[i][mb[i]] < k).mean())
        d['hit_ci_lo'], d['hit_ci_hi'] = ci(hb)
        dp = (o_pct - o_pct_all); d['delta_pct_ci_lo'], d['delta_pct_ci_hi'] = ci(dp[idx].mean(1))
    return d
TRm = S['train'].values; TEm = S['test'].values; idx_tr = block_idx(int(TRm.sum()), B_RULES); idx_te = block_idx(int(TEm.sum()), B_RULES)
rows = []
for kname, k in KS.items():
    for rname, skip in [('trade_all', np.zeros(len(S), bool))] + list(RULES.items()):
        for sname, sm, ix in (('train', TRm, idx_tr), ('test', TEm, idx_te)):
            d = payoff_stats(~skip, sm, k, ix); d.update(k_name=kname, k=k, rule=rname, sample=sname); rows.append(d)
RS = pd.DataFrame(rows); RS.to_csv(os.path.join(OUT, 'rules_single.csv'), index=False, float_format='%.5g')
# selection on train (k_fair): rank by delta per trading day
sel = RS[(RS['k_name'] == 'k_fair_train') & (RS['sample'] == 'train') & (RS['rule'] != 'trade_all')].sort_values('delta_per_trading_day', ascending=False)
print('\n=== Single rules ranked on TRAIN (k = fair), with TEST results ===')
tst = RS[(RS['k_name'] == 'k_fair_train') & (RS['sample'] == 'test')].set_index('rule')
tab = sel[['rule', 'share_traded', 'hit_rate', 'hit_rate_delta', 'delta_per_trading_day', 'delta_ci_lo', 'delta_ci_hi']].copy()
for c in ('share_traded', 'hit_rate', 'hit_rate_delta', 'delta_per_trading_day', 'delta_ci_lo', 'delta_ci_hi'): tab['test_' + c] = tst.loc[tab['rule'], c].values
print(tab.round(4).to_string(index=False))
# pairs (OR): skip if either rule fires
pair_rows = []; rnames = list(RULES.keys())
for a, b in itertools.combinations(rnames, 2):
    skip = RULES[a] | RULES[b]
    for kname, k in (('k_fair_train', k_fair), ('k_1.0', 1.0)):
        for sname, sm, ix in (('train', TRm, None), ('test', TEm, None)):
            d = payoff_stats(~skip, sm, k, None); d.update(k_name=kname, k=k, rule=a + ' | ' + b, rule_a=a, rule_b=b, sample=sname); pair_rows.append(d)
PR = pd.DataFrame(pair_rows)
top_pairs = PR[(PR['k_name'] == 'k_fair_train') & (PR['sample'] == 'train')].sort_values('delta_per_trading_day', ascending=False).head(15)
# bootstrap CIs for the top pairs on test
extra = []
for _, r in top_pairs.iterrows():
    skip = RULES[r['rule_a']] | RULES[r['rule_b']]
    for sname, sm, ix in (('train', TRm, idx_tr), ('test', TEm, idx_te)):
        d = payoff_stats(~skip, sm, k_fair, ix); d.update(k_name='k_fair_train', k=k_fair, rule=r['rule'], rule_a=r['rule_a'], rule_b=r['rule_b'], sample=sname); extra.append(d)
PX = pd.DataFrame(extra); PX.to_csv(os.path.join(OUT, 'rules_pairs_top.csv'), index=False, float_format='%.5g')
PR.to_csv(os.path.join(OUT, 'rules_pairs_all.csv'), index=False, float_format='%.5g')
print('\n=== Top-15 pairs on TRAIN (k = fair): train and test delta per trading day ===')
ptr = PX[PX['sample'] == 'train'].set_index('rule'); pte = PX[PX['sample'] == 'test'].set_index('rule')
pt = pd.DataFrame({'train_share': ptr['share_traded'], 'train_delta': ptr['delta_per_trading_day'], 'test_share': pte['share_traded'], 'test_hit': pte['hit_rate'], 'test_hit_delta': pte['hit_rate_delta'], 'test_delta': pte['delta_per_trading_day'], 'test_ci_lo': pte['delta_ci_lo'], 'test_ci_hi': pte['delta_ci_hi']})
print(pt.round(4).to_string())

# ---------- 5. By-year stability for selected rules ----------
best_single = sel.iloc[0]['rule']; best_pair = (top_pairs.iloc[0]['rule_a'], top_pairs.iloc[0]['rule_b'])
chosen = {'trade_all': np.zeros(len(S), bool), best_single: RULES[best_single], ' | '.join(best_pair): RULES[best_pair[0]] | RULES[best_pair[1]],
          'skip_any_event': RULES['skip_any_event'], 'skip_vix_gt_60d_p80': RULES['skip_vix_gt_60d_p80'], 'skip_vix_rise_gt10pct': RULES['skip_vix_rise_gt10pct'], 'skip_fomc': RULES['skip_fomc']}
yr_rows = []
for y in sorted(S['year'].unique()):
    ym = (S['year'] == y).values
    for rname, skip in chosen.items():
        d = payoff_stats(~skip, ym, k_fair, None); d.update(year=y, rule=rname, sample='train' if y <= 2022 else 'test'); yr_rows.append(d)
YR = pd.DataFrame(yr_rows); YR.to_csv(os.path.join(OUT, 'by_year.csv'), index=False, float_format='%.5g')
print('\n=== By year: delta per trading day vs trade-all (k = fair) ===')
print(YR.pivot(index='year', columns='rule', values='delta_per_trading_day').round(4).to_string())
print('\n=== By year: hit rate (k = fair) ===')
print(YR.pivot(index='year', columns='rule', values='hit_rate').round(3).to_string())
print('\n=== By year: share traded ===')
print(YR.pivot(index='year', columns='rule', values='share_traded').round(3).to_string())

# ---------- 6. Quintile tables (edges from train) on test ----------
qrows = []
for p in ('log_range_0930_1300', 'log_range_0930_1030', 'log_vix_1300', 'vix_chg_open_1300', 'log_prev_range', 'log_prev_rv5', 'log_absgap', 'eff_am', 'amrange_rel20'):
    edges = tr[p].quantile([0.2, 0.4, 0.6, 0.8]).values
    for sname, sub in (('train', tr), ('test', te)):
        qb = np.digitize(sub[p].values, edges)
        for qq in range(5):
            m = (qb == qq) & sub['ratio'].notna().values
            if m.sum() < 10: continue
            qrows.append(dict(predictor=p, sample=sname, quintile=qq + 1, n=int(m.sum()), mean_ratio=sub['ratio'].values[m].mean(), median_ratio=np.median(sub['ratio'].values[m]), hit_rate_kfair=float((sub['ratio'].values[m] < k_fair).mean()),
                              mean_absmove_pm_pct=sub['absmove_pm'].values[m].mean() * 100, mean_range_pm_pct=sub['range_pm'].values[m].mean() * 100, mean_outcome_kfair=float((k_fair - sub['ratio'].values[m]).mean())))
Q = pd.DataFrame(qrows); Q.to_csv(os.path.join(OUT, 'quintiles.csv'), index=False, float_format='%.4f')
print('\n=== Test-set mean ratio |pm move|/morning range by train-quintile of predictor ===')
print(Q[Q['sample'] == 'test'].pivot(index='predictor', columns='quintile', values='mean_ratio').round(3).to_string())
print('\n=== Test-set hit rate (k fair) by quintile ===')
print(Q[Q['sample'] == 'test'].pivot(index='predictor', columns='quintile', values='hit_rate_kfair').round(3).to_string())
# gamma sub-sample
g = S[S['neg_gamma_prev'].notna()]
if len(g) > 50:
    a = g[g['neg_gamma_prev'] == 1]; b = g[g['neg_gamma_prev'] == 0]
    print(f'\n=== UW prior-day gamma sign (>= {GEX_START}): n_neg {len(a)} n_pos {len(b)}; mean ratio neg {a["ratio"].mean():.4f} pos {b["ratio"].mean():.4f}; hit(kfair) neg {(a["ratio"] < k_fair).mean():.3f} pos {(b["ratio"] < k_fair).mean():.3f}; mean |pm move| neg {a["absmove_pm"].mean()*100:.3f}% pos {b["absmove_pm"].mean()*100:.3f}%')
S[['date', 'year', 'dow', 'train', 'p_open', 'p_1300', 'p_close', 'range_0930_1030', 'rv_0930_1030', 'range_0930_1300', 'rv_0930_1300', 'absmove_am', 'eff_am', 'range_pm', 'absmove_pm', 'move_pm', 'ratio', 'range_day', 'vix_0931', 'vix_1300', 'vix_chg_open_1300', 'vix_hi_60d', 'prev_range', 'prev_rv5', 'prev_rv20', 'absgap', 'amrange_rel20', 'fomc', 'cpi', 'nfp', 'opex', 'quad_opex', 'month_end', 'holiday_adj', 'pre_holiday', 'post_holiday', 'neg_gamma_prev']].to_csv(os.path.join(OUT, 'sample.csv'), index=False, float_format='%.6g')
print('\nDONE')
