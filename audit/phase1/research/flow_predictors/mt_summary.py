"""Multiple-testing summary across the main (unconditioned) cells: flow (36), tide tradable (4), dark pool D1/D2 (12), bursts k=5 band 1 % (2 filters x 5 = 10)."""
import pandas as pd, numpy as np
from common import *
cells = []
fl = pd.read_csv(os.path.join(OUT, 'flow_ic_main.csv')); cells += [dict(test='flow', ticker=r.ticker, feature=r.feature, horizon=r.horizon, n=r.n, stat='IC', value=r.ic, lo=r.lo, hi=r.hi, p=r.p, spread_bps=r.spread, sp_lo=r.sp_lo, sp_hi=r.sp_hi, sp_p=r.sp_p) for r in fl.itertuples()]
td = pd.read_csv(os.path.join(OUT, 'tide_ic_main.csv')); td = td[td['align'] == 'tradable']; cells += [dict(test='tide', ticker='SPY', feature=r.feature, horizon=r.horizon, n=r.n, stat='IC', value=r.ic, lo=r.lo, hi=r.hi, p=r.p, spread_bps=r.spread, sp_lo=r.sp_lo, sp_hi=r.sp_hi, sp_p=r.sp_p) for r in td.itertuples()]
try:
    dp = pd.read_csv(os.path.join(OUT, 'dp_ic_main.csv')); dp = dp[dp.feature.isin(['D1', 'D2'])]; cells += [dict(test='darkpool', ticker=r.ticker, feature=r.feature, horizon=r.horizon, n=r.n, stat='IC', value=r.ic, lo=r.lo, hi=r.hi, p=r.p, spread_bps=r.spread, sp_lo=r.sp_lo, sp_hi=r.sp_hi, sp_p=r.sp_p) for r in dp.itertuples()]
except FileNotFoundError: print('no darkpool results yet')
try:
    bs = pd.read_csv(os.path.join(OUT, 'bursts_summary.csv')); bs = bs[(bs.k == 5) & (bs.band == 0.01) & (bs.set == 'burst')]
    for r in bs.itertuples():
        for col, lab in (('u15', 'underlying_15'), ('u30', 'underlying_30'), ('u60', 'underlying_60'), ('c15_net', 'contract_net_15'), ('c30_net', 'contract_net_30')):
            cells.append(dict(test='bursts_' + r.filter, ticker='ALL', feature=lab, horizon=int(lab.split('_')[-1]), n=getattr(r, col + '_n'), stat='mean_bps' if col[0] == 'u' else 'mean_ret', value=getattr(r, col + '_mean'), lo=getattr(r, col + '_lo'), hi=getattr(r, col + '_hi'), p=getattr(r, col + '_p'), spread_bps=np.nan, sp_lo=np.nan, sp_hi=np.nan, sp_p=np.nan))
except FileNotFoundError: print('no burst results yet')
df = pd.DataFrame(cells); N = len(df)
def bh(p):
    p = np.asarray(p, float); ok = np.isfinite(p); idx = np.argsort(p[ok]); m = ok.sum(); rej = np.zeros(len(p), bool)
    thr = 0.05 * (np.arange(1, m + 1) / m); passed = np.where(np.sort(p[ok]) <= thr)[0]
    if len(passed): rej[np.where(ok)[0][idx[:passed.max() + 1]]] = True
    return rej
df['bonf_ic'] = df.p < 0.05 / N; df['bh_ic'] = bh(df.p.values); df['bonf_spread'] = df.sp_p < 0.05 / N; df['bh_spread'] = bh(df.sp_p.values)
df.to_csv(os.path.join(OUT, 'mt_summary.csv'), index=False, float_format='%.5g')
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 200)
print('cells', N, 'bonferroni threshold', 0.05 / N, '| nominal p<0.05 (IC/mean):', int((df.p < 0.05).sum()), '| bonferroni survivors:', int(df.bonf_ic.sum()), '| BH survivors:', int(df.bh_ic.sum()),
      '| spread nominal:', int((df.sp_p < 0.05).sum()), 'bonf:', int(df.bonf_spread.sum()), 'BH:', int(df.bh_spread.sum()))
print(df.sort_values('p')[['test', 'ticker', 'feature', 'horizon', 'n', 'stat', 'value', 'lo', 'hi', 'p', 'spread_bps', 'sp_lo', 'sp_hi', 'sp_p']].head(12).to_string())
