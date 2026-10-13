"""Q1: dealer-gamma regime (spot at 10:00 vs PRIOR-day gamma_flip) vs intraday continuation/mean reversion, range and 1-min reversal rate."""
import collections
from common import *
recs = []; skipped = collections.Counter()
for tk in TICKERS:
    for d in DAYS:
        rth, pre = data.underlying_bars(tk, d)
        if len(rth) < 300: skipped['short_day'] += 1; continue
        gex = data.gex_levels(tk, prior_day(d)); flip = gex.get('gamma_flip')
        o = rth[0]['o'] if hhmm(rth[0]['t']) == 570 else None
        spot10 = px_at(rth, 600); p13 = px_at(rth, 780); p1555 = px_at(rth, 955); p1525 = px_at(rth, 925); p1455 = px_at(rth, 895)
        if flip is None: skipped['no_flip'] += 1; continue
        if None in (o, spot10, p13, p1555, p1525, p1455): skipped['missing_bar'] += 1; continue
        closes = np.array([b['c'] for b in rth]); r1 = np.diff(closes) / closes[:-1]
        a, b = r1[:-1], r1[1:]; nz = (a != 0) & (b != 0)
        rev = float(np.mean(np.sign(a[nz]) != np.sign(b[nz]))) if nz.sum() > 20 else float('nan')
        ac1 = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else float('nan')
        recs.append(dict(ticker=tk, date=d, regime='POS' if spot10 > flip else 'NEG', dist_pct=(spot10 - flip) / spot10 * 100, flip=flip, spot10=spot10,
                         r_am=p13 / o - 1, r_pm=p1555 / p13 - 1, r_prev30=p1525 / p1455 - 1, r_last30=p1555 / p1525 - 1,
                         range_pct=(max(x['h'] for x in rth) - min(x['l'] for x in rth)) / o * 100, rev_frac=rev, ac1=ac1, rv_pct=float(r1.std() * np.sqrt(len(r1)) * 100), n_bars=len(rth)))
print('ticker-days', len(recs), 'skipped', dict(skipped))
write_csv(OUT + '/q1_daily.csv', recs)
R = {k: np.array([r[k] for r in recs]) for k in recs[0]}
# terciles of signed distance within ticker, and of |distance| within ticker
R['dist_terc'] = np.empty(len(recs), object); R['absdist_terc'] = np.empty(len(recs), object)
for tk in TICKERS:
    m = R['ticker'] == tk
    for key, src, labels in (('dist_terc', R['dist_pct'][m], ('T1_mostNEG', 'T2_mid', 'T3_mostPOS')), ('absdist_terc', np.abs(R['dist_pct'])[m], ('A1_near', 'A2_mid', 'A3_far'))):
        q = np.quantile(src, [1 / 3, 2 / 3]); R[key][m] = np.array(labels)[np.searchsorted(q, src, side='right')]
rows = []
def block(name, sel):
    g = R['date'][sel]; out = dict(group=name, n=int(sel.sum()))
    for lab, x, y in (('pm_on_am', R['r_am'][sel], R['r_pm'][sel]), ('last30_on_prev30', R['r_prev30'][sel], R['r_last30'][sel])):
        if sel.sum() < 10: continue
        s = ols_slope(x, y); lo, hi = boot_slope_ci(x, y, g, 1000)
        agree = (np.sign(x) == np.sign(y)) & (x != 0); nzs = x != 0
        ar = agree[nzs].mean(); alo, ahi = boot_mean_ci(agree[nzs].astype(float), g[nzs], 1000)
        follow = y * np.sign(x); flo, fhi = boot_mean_ci(follow * 1e4, g, 1000)  # bp earned by following the prior move
        out.update({f'{lab}_slope': s, f'{lab}_slope_lo': lo, f'{lab}_slope_hi': hi, f'{lab}_signagree': ar, f'{lab}_signagree_lo': alo, f'{lab}_signagree_hi': ahi,
                    f'{lab}_follow_bp': follow.mean() * 1e4, f'{lab}_follow_bp_lo': flo, f'{lab}_follow_bp_hi': fhi, f'{lab}_corr': float(np.corrcoef(x, y)[0, 1])})
    for lab in ('range_pct', 'rev_frac', 'ac1', 'rv_pct'):
        v = R[lab][sel]; ok = ~np.isnan(v); lo, hi = boot_mean_ci(v[ok], g[ok], 1000)
        out.update({f'{lab}_mean': float(v[ok].mean()), f'{lab}_lo': lo, f'{lab}_hi': hi})
    rows.append(out); return out
allm = np.ones(len(recs), bool)
block('ALL|all', allm)
for reg in ('POS', 'NEG'): block(f'ALL|{reg}', R['regime'] == reg)
for t in ('T1_mostNEG', 'T2_mid', 'T3_mostPOS'): block(f'ALL|{t}', R['dist_terc'] == t)
for t in ('A1_near', 'A2_mid', 'A3_far'): block(f'ALL|{t}', R['absdist_terc'] == t)
for tk in TICKERS:
    block(f'{tk}|all', R['ticker'] == tk)
    for reg in ('POS', 'NEG'): block(f'{tk}|{reg}', (R['ticker'] == tk) & (R['regime'] == reg))
    for t in ('T1_mostNEG', 'T2_mid', 'T3_mostPOS'): block(f'{tk}|{t}', (R['ticker'] == tk) & (R['dist_terc'] == t))
# IS/OOS halves of the regime split (robustness)
for per, sel in (('IS', R['date'] < SPLIT), ('OOS', R['date'] >= SPLIT)):
    for reg in ('POS', 'NEG'): block(f'ALL_{per}|{reg}', sel & (R['regime'] == reg))
write_csv(OUT + '/q1_summary.csv', rows)
# POS-NEG differences with daily-block bootstrap (pooled and per ticker)
diffs = []
def diff_block(name, selP, selN):
    rng = np.random.default_rng(11); dates = np.unique(R['date']); out = dict(group=name, nPOS=int(selP.sum()), nNEG=int(selN.sum()))
    stats = {}
    def calc(idx):
        P = selP[idx]; Nn = selN[idx]; res = {}
        for lab, xk, yk in (('pm_on_am', 'r_am', 'r_pm'), ('last30_on_prev30', 'r_prev30', 'r_last30')):
            x, y = R[xk][idx], R[yk][idx]
            res[f'{lab}_slope_diff'] = ols_slope(x[P], y[P]) - ols_slope(x[Nn], y[Nn])
            res[f'{lab}_follow_bp_diff'] = (y[P] * np.sign(x[P])).mean() * 1e4 - (y[Nn] * np.sign(x[Nn])).mean() * 1e4
        for lab in ('range_pct', 'rev_frac', 'ac1'):
            v = R[lab][idx]; res[f'{lab}_diff'] = np.nanmean(v[P]) - np.nanmean(v[Nn])
        return res
    base = calc(np.arange(len(recs))); members = {d: np.where(R['date'] == d)[0] for d in dates}; boots = collections.defaultdict(list)
    for _ in range(1000):
        idx = np.concatenate([members[d] for d in rng.choice(dates, len(dates))])
        if selP[idx].sum() < 5 or selN[idx].sum() < 5: continue
        for k, v in calc(idx).items(): boots[k].append(v)
    for k, v in base.items():
        out[k] = v; out[k + '_lo'] = float(np.nanpercentile(boots[k], 2.5)); out[k + '_hi'] = float(np.nanpercentile(boots[k], 97.5))
    diffs.append(out)
diff_block('ALL', R['regime'] == 'POS', R['regime'] == 'NEG')
for tk in TICKERS: diff_block(tk, (R['ticker'] == tk) & (R['regime'] == 'POS'), (R['ticker'] == tk) & (R['regime'] == 'NEG'))
diff_block('ALL_terc_T3_vs_T1', R['dist_terc'] == 'T3_mostPOS', R['dist_terc'] == 'T1_mostNEG')
write_csv(OUT + '/q1_pos_minus_neg.csv', diffs)
print('regime counts', collections.Counter(zip(R['ticker'], R['regime'])))
print('dist_pct quantiles by ticker', {tk: np.round(np.quantile(R['dist_pct'][R['ticker'] == tk], [0.1, 0.5, 0.9]), 2).tolist() for tk in TICKERS})
for r in rows:
    print(r['group'], 'n', r['n'], '| pm_on_am slope %.3f [%.3f,%.3f] agree %.3f follow_bp %.1f [%.1f,%.1f] | last30 slope %.3f [%.3f,%.3f] agree %.3f follow_bp %.1f [%.1f,%.1f] | range %.3f rev %.4f ac1 %.4f' % tuple(r.get(k, float('nan')) for k in ('pm_on_am_slope', 'pm_on_am_slope_lo', 'pm_on_am_slope_hi', 'pm_on_am_signagree', 'pm_on_am_follow_bp', 'pm_on_am_follow_bp_lo', 'pm_on_am_follow_bp_hi', 'last30_on_prev30_slope', 'last30_on_prev30_slope_lo', 'last30_on_prev30_slope_hi', 'last30_on_prev30_signagree', 'last30_on_prev30_follow_bp', 'last30_on_prev30_follow_bp_lo', 'last30_on_prev30_follow_bp_hi', 'range_pct_mean', 'rev_frac_mean', 'ac1_mean')))
for r in diffs: print('DIFF', r)
