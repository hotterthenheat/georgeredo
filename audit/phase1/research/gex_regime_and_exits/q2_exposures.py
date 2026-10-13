"""Q2: UW 1-minute spot exposures (SPY, 60 sessions): does the sign/size of net gamma (OI/vol/dir) or its 30-min change predict the next
30/60-minute signed and absolute return? ICs = Spearman rank correlations, pooled and as mean daily IC, with daily-block bootstrap CIs."""
import json, collections
from common import *
sessions = json.load(open(OUT + '/q2_sessions.json'))
FIELDS = ['gamma_per_one_percent_move_oi', 'gamma_per_one_percent_move_vol', 'gamma_per_one_percent_move_dir', 'charm_per_one_percent_move_oi', 'vanna_per_one_percent_move_oi']
obs = []; gaps = collections.Counter(); daily = []
for d in sessions:
    raw = data.get('stock/SPY/spot-exposures', {'date': d}).get('data') or []
    ex = {}
    for r in raw:
        t = data.et(r['start_time']); m = hhmm(t)
        if t.strftime('%Y-%m-%d') != d: gaps['other_date_row'] += 1; continue
        try: ex[m] = {f: float(r[f]) for f in FIELDS} | {'uw_price': float(r['price'])}
        except Exception: gaps['bad_row'] += 1
    rth, _ = data.underlying_bars('SPY', d); c = {hhmm(b['t']): b['c'] for b in rth}
    rth_min = [m for m in range(570, 960) if m in ex]; gaps['rth_minutes_missing'] += 390 - len(rth_min)
    gex_prev = data.gex_levels('SPY', prior_day(d)); flip = gex_prev.get('gamma_flip')
    g10 = ex.get(600, {}).get('gamma_per_one_percent_move_oi'); daily.append(dict(date=d, n_rth_rows=len(rth_min), g_oi_1000=g10, spot10=c.get(600), flip=flip, levels_regime=('POS' if (flip and c.get(600) and c[600] > flip) else 'NEG'), sign_g_oi_1000=(np.sign(g10) if g10 is not None else None),
                      g_oi_share_pos=float(np.mean([ex[m]['gamma_per_one_percent_move_oi'] > 0 for m in rth_min])) if rth_min else None))
    for m in range(570, 960):
        if m not in ex or m not in c: continue
        o = dict(date=d, minute=m)
        for f in FIELDS: o[f.replace('_per_one_percent_move', '')] = ex[m][f]
        prev = ex.get(m - 30) or ex.get(m - 31) or ex.get(m - 29)
        o['d30_gamma_oi'] = ex[m]['gamma_per_one_percent_move_oi'] - prev['gamma_per_one_percent_move_oi'] if prev else np.nan
        o['d30_gamma_vol'] = ex[m]['gamma_per_one_percent_move_vol'] - prev['gamma_per_one_percent_move_vol'] if prev else np.nan
        for k in (30, 60):
            o[f'r{k}'] = c[m + k] / c[m] - 1 if (m + k) in c else np.nan
            o[f'abs_r{k}'] = abs(o[f'r{k}'])
        o['r_prev30'] = c[m] / c[m - 30] - 1 if (m - 30) in c else np.nan
        obs.append(o)
write_csv(OUT + '/q2_minute_obs.csv', obs); write_csv(OUT + '/q2_daily.csv', daily)
print('sessions', len(sessions), 'minute obs', len(obs), 'gaps', dict(gaps))
print('regime agreement (sign of gamma_oi at 10:00 vs prior-day flip regime):', collections.Counter((x['levels_regime'], x['sign_g_oi_1000']) for x in daily))
A = {k: np.array([o[k] for o in obs], dtype=object if k == 'date' else float) for k in obs[0]}
rows = []
preds = ['gamma_oi', 'gamma_vol', 'gamma_dir', 'd30_gamma_oi', 'd30_gamma_vol', 'charm_oi', 'vanna_oi']
for subset, sel in (('all_minutes', np.ones(len(obs), bool)), ('nonoverlap_30', (A['minute'] % 30 == 0)), ('after_1030', A['minute'] >= 630)):
    for p in preds:
        for tgt in ('r30', 'r60', 'abs_r30', 'abs_r60'):
            ok = sel & ~np.isnan(A[p]) & ~np.isnan(A[tgt]) & (A[p] != 0)
            if ok.sum() < 50: continue
            x, y, g = A[p][ok], A[tgt][ok], A['date'][ok]
            ic = spearman(x, y); lo, hi = boot_stat_ci(spearman, [x, y], g, 500)
            # mean daily IC
            dics = [spearman(x[g == d], y[g == d]) for d in np.unique(g) if (g == d).sum() >= 20]; dics = np.array([v for v in dics if not np.isnan(v)])
            # sign split on the predictor
            pos = y[x > 0]; neg = y[x < 0]
            rows.append(dict(subset=subset, predictor=p, target=tgt, n=int(ok.sum()), n_days=len(np.unique(g)), ic_pooled=ic, ic_lo=lo, ic_hi=hi, daily_ic_mean=float(dics.mean()) if len(dics) else np.nan,
                             daily_ic_se=float(dics.std(ddof=1) / np.sqrt(len(dics))) if len(dics) > 1 else np.nan, daily_ic_t=float(dics.mean() / (dics.std(ddof=1) / np.sqrt(len(dics)))) if len(dics) > 1 else np.nan,
                             mean_tgt_pred_pos_bp=float(pos.mean() * 1e4) if len(pos) else np.nan, n_pos=len(pos), mean_tgt_pred_neg_bp=float(neg.mean() * 1e4) if len(neg) else np.nan, n_neg=len(neg)))
write_csv(OUT + '/q2_ic_summary.csv', rows)
for r in rows:
    if r['subset'] != 'after_1030': print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
# Baltussen-style with the intraday measure: continuation of the previous 30 min by sign of gamma_oi
for subset, sel in (('all_minutes', np.ones(len(obs), bool)), ('nonoverlap_30', (A['minute'] % 30 == 0))):
    for sgn, nm in ((1, 'gamma_oi>0'), (-1, 'gamma_oi<0')):
        ok = sel & ~np.isnan(A['r_prev30']) & ~np.isnan(A['r30']) & (np.sign(A['gamma_oi']) == sgn)
        if ok.sum() < 30: continue
        x, y, g = A['r_prev30'][ok], A['r30'][ok], A['date'][ok]
        s = ols_slope(x, y); lo, hi = boot_slope_ci(x, y, g, 500); fol = y * np.sign(x); flo, fhi = boot_mean_ci(fol * 1e4, g, 500)
        print('CONT', subset, nm, 'n', int(ok.sum()), 'days', len(np.unique(g)), 'slope next30~prev30 %.3f [%.3f, %.3f] follow_bp %.1f [%.1f, %.1f]' % (s, lo, hi, fol.mean() * 1e4, flo, fhi))
