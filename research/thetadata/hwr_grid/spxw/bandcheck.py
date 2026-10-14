#!/usr/bin/env python3
"""Post-hoc data-limitation check (not part of the pre-registered selection): the dataset stores only strikes within +-2 % of the
09:31 SPX price, so a strangle whose short strike lies beyond that band is skipped (`out_of_band`).  Those skips fall on
large-move days.  For every naked, no-TP, no-stop, hold-to-settlement (E2) configuration, this script adds back each skipped
day with an OPTIMISTIC P&L bound:  credit <= the ATM straddle credit at the bid at the same minute (a strangle always collects
less), short strikes = spot +- k*EM rounded outward to the 5-point grid, settlement at the SPX 16:00 print, $2 fees:
    P&L_bound = 100 * (straddle credit - intrinsic of the strangle at settlement) - 2  >=  true P&L.
Because the bound is >= the true P&L, the recomputed mean and percentile bounds are upper bounds on what the unrestricted strategy
would have shown.  Because a strangle's credit is often far below the straddle's, this strict bound is loose for k >= 1; a second,
still optimistic, estimate uses credit = (largest strangle/straddle credit ratio observed on traded days of that cell and entry,
2022-2026) x straddle credit.  Output: results/band_bias_check.csv."""
import os, sys, glob, math
import numpy as np, pandas as pd, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim  # noqa: E402
import analyze as A  # noqa: E402
from stats import Boot, basic  # noqa: E402

T, sk = A.load('test')
dates = sorted(T['date'].unique()); fl, _ = A.flags(dates); G = A.Grid(T, dates); cfg = A.enumerate_configs(); boot = Boot()
st = T[(T['cell'] == 'N0.0') & (T['tp'] == 0) & (T['stop'] == 0) & (T['exit'] == 'E2')]
fs = sorted(glob.glob(A.OUT + '/trades/*.parquet'))
info = A.topd(pl.concat([pl.read_parquet(f, columns=['date', 'entry', 'cell', 'tp', 'stop', 'exit', 'spot', 'em', 'credit', 'settle'])
                         .filter((pl.col('cell') == 'N0.0') & (pl.col('tp') == 0) & (pl.col('stop') == 0) & (pl.col('exit') == 'E2')) for f in fs]))
info = info.set_index(['date', 'entry'])
oob = sk[sk['reason'] == 'out_of_band']
cr = T[(T['tp'] == 0) & (T['stop'] == 0) & (T['exit'] == 'E2') & (T['cell'].str[0] == 'N')][['date', 'entry', 'cell', 'credit']]
cr = cr.merge(cr[cr['cell'] == 'N0.0'][['date', 'entry', 'credit']].rename(columns={'credit': 'straddle'}), on=['date', 'entry'])
RATIO = (cr['credit'] / cr['straddle']).groupby([cr['cell'], cr['entry']]).max().to_dict()
rows = []
sel = cfg[cfg['distinct'] & (cfg['cell'].str[0] == 'N') & (cfg['cell'] != 'N0.0') & (cfg['tp'] == 0) & (cfg['stop'] == 0) & (cfg['exit'] == 'E2')]
for r in sel.itertuples(index=False):
    k = float(r.cell[1:])
    x = G.config(r.cell, r.entry, r.tp, r.stop, r.exit, r.filter, r.variant, fl)
    # skipped out-of-band days in the configuration's day set
    ent = pd.Series(r.entry, index=dates)
    if r.filter == 'F2': ent[fl['fomc'].values] = '14:05'
    keep = np.ones(len(dates), bool)
    if r.filter == 'F1': keep &= ~fl['fomc'].values
    elif r.filter == 'F3': keep &= ~(fl['fomc'].values | fl['month_end'].values)
    elif r.filter == 'F4': keep &= ~(fl['fomc'].values | fl['cpi'].values | fl['nfp'].values)
    o = set(zip(oob.loc[oob['cell'] == r.cell, 'date'], oob.loc[oob['cell'] == r.cell, 'entry']))
    xb = x.copy(); xr = x.copy(); xz = x.copy(); added = []
    for i, d in enumerate(dates):
        if keep[i] and not np.isfinite(x[i]) and (d, ent.iloc[i]) in o and (d, ent.iloc[i]) in info.index:
            s = info.loc[(d, ent.iloc[i])]
            kc = math.ceil((s['spot'] + k * s['em']) / 5) * 5; kp = math.floor((s['spot'] - k * s['em']) / 5) * 5
            intr = max(s['settle'] - kc, 0) + max(kp - s['settle'], 0)
            xb[i] = 100 * (s['credit'] - intr) - 2.0; added.append((d, round(xb[i])))
            xr[i] = 100 * (RATIO[(r.cell, ent.iloc[i])] * s['credit'] - intr) - 2.0
            xz[i] = -100 * intr - 2.0   # pessimistic: zero credit
    for p, (lo, hi) in A.PER.items():
        pm = (np.array(dates) >= lo) & (np.array(dates) <= hi)
        a = x[pm][np.isfinite(x[pm])]; b = xb[pm][np.isfinite(xb[pm])]
        if len(a) < 2: continue
        la, ha, _ = boot.ci(a); lb, hb, _ = boot.ci(b); ba = basic(a); bb = basic(b)
        c_ = xr[pm][np.isfinite(xr[pm])]; lr, hr, _ = boot.ci(c_); br = basic(c_)
        z_ = xz[pm][np.isfinite(xz[pm])]; lz, hz, _ = boot.ci(z_); bz = basic(z_)
        ad = [t for t in added if lo <= t[0] <= hi]
        rows.append(dict(cid=r.cid, period=p, n=len(a), mean=ba['mean'], ci_lo=la, ci_hi=ha, win_rate=ba['win_rate'],
                         oob_days_added=len(ad), n_with_bound=len(b), mean_with_bound=bb['mean'], ci_lo_with_bound=lb, ci_hi_with_bound=hb,
                         win_rate_with_bound=bb['win_rate'], worst_added=min([v for _, v in ad], default=np.nan),
                         credit_ratio_max=RATIO.get((r.cell, r.entry)), mean_ratio_est=br['mean'], ci_lo_ratio_est=lr, ci_hi_ratio_est=hr, win_rate_ratio_est=br['win_rate'],
                         mean_zero_credit=bz['mean'], ci_lo_zero_credit=lz, ci_hi_zero_credit=hz,
                         added=' '.join(f'{d}:{v}' for d, v in sorted(ad, key=lambda t: t[1])[:8])))
D = pd.DataFrame(rows); D.to_csv(os.path.join(A.RES, 'band_bias_check.csv'), index=False, float_format='%.6g')
t = D[D['period'] == 'TEST']
print('TEST configs checked', len(t), '| LB>0 as is', int((t['ci_lo'] > 0).sum()), '| LB>0 with skipped days added at the strict optimistic bound', int((t['ci_lo_with_bound'] > 0).sum()), '| with the ratio estimate', int((t['ci_lo_ratio_est'] > 0).sum()))
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 90)
print(t.sort_values('ci_lo', ascending=False).head(25)[['cid', 'n', 'mean', 'ci_lo', 'win_rate', 'oob_days_added', 'mean_with_bound', 'ci_lo_with_bound', 'win_rate_with_bound', 'worst_added', 'credit_ratio_max', 'mean_ratio_est', 'ci_lo_ratio_est', 'ci_lo_zero_credit']].round(2).to_string())
print('with zero credit on the added days', int((t['ci_lo_zero_credit'] > 0).sum()))
print(D[D['cid'].isin(['N0.5|14:05|tp0|st0|E2|F3|P'])].T.to_string())
