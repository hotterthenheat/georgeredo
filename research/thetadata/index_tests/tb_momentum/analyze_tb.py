#!/usr/bin/env python3
"""T-B: gamma-conditioned last-half-hour momentum (Baltussen, Da, Lammers, Martens 2021 design) on SPX (index, cost-free) and SPY (tradable, 0.2 bp per side).
Env: TD_CACHE (ThetaData monthly gzip-CSV files), UW_GEX_CSV (daily gex-levels pull for SPY and SPX), CAL_FILE (ThetaData calendar), OUT_DIR.
Signal at 15:30 = sign(P(15:30)/P(open) - 1); position held 15:30 -> 16:00. Gamma regime for day T = sign(close(T-1) - gamma_flip(T-1)), gex-levels dated T-1."""
import os, glob, math, datetime as dt
import numpy as np, pandas as pd
TD = os.environ['TD_CACHE']; UW = os.environ['UW_GEX_CSV']; CAL = os.environ['CAL_FILE']; OUT = os.environ['OUT_DIR']; os.makedirs(OUT, exist_ok=True)
COST_BP = 0.2; B = 5000; SEED = 7
PRIOR = {'neg': 6.6, 'pos': 0.8}  # Baltussen et al. (2021), beta x 100 of the last-half-hour return on the rest-of-day return, by dealer-gamma sign
def load(pattern):
    fs = sorted(glob.glob(os.path.join(TD, pattern))); dfs = [pd.read_csv(f) for f in fs]; dfs = [d for d in dfs if not d.empty]
    df = pd.concat(dfs, ignore_index=True); df['date'] = df['timestamp'].str.slice(0, 10); df['hm'] = df['timestamp'].str.slice(11, 16); return df
spx = load('index_history_price__end_date=*__interval=1m__start_date=*__symbol=SPX.csv.gz')
vix = load('index_history_price__end_date=*__interval=1m__start_date=*__symbol=VIX.csv.gz')
spy = load('stock_history_ohlc__end_date=*__interval=1m__start_date=*__symbol=SPY.csv.gz')
def eod(pattern):
    fs = sorted(glob.glob(os.path.join(TD, pattern))); dfs = [pd.read_csv(f) for f in fs]; dfs = [d for d in dfs if not d.empty]
    df = pd.concat(dfs, ignore_index=True); df['date'] = df['last_trade'].astype(str).str.slice(0, 10); return df.drop_duplicates('date').set_index('date')
spx_eod = eod('index_history_eod__*symbol=SPX.csv.gz'); spy_eod = eod('stock_history_eod__*symbol=SPY.csv.gz')
cal = pd.read_csv(CAL); early = set(cal.loc[cal['type'] == 'early_close', 'date'])
# per-day table
def pick(df, hm, col):
    s = df[df['hm'] == hm][['date', col]].drop_duplicates('date').set_index('date')[col]; return s
spx_open = spx[spx['price'].notna() & (spx['hm'] <= '09:35')].sort_values('timestamp').drop_duplicates('date').set_index('date')
D = pd.DataFrame(index=sorted(spx['date'].unique()))
D['spx_open'] = spx_open['price']; D['spx_open_hm'] = spx_open['hm']
for hm in ('13:00', '15:30', '15:45', '16:00'): D[f'spx_{hm.replace(":", "")}'] = pick(spx, hm, 'price')
D['spx_rows'] = spx.groupby('date').size()
D['spx_close_off'] = spx_eod['close']
D['vix_1530'] = pick(vix, '15:30', 'price'); D['vix_prev_close'] = pick(vix, '16:00', 'price').shift(1)
D['spy_open'] = pick(spy, '09:30', 'open'); D['spy_c1529'] = pick(spy, '15:29', 'close'); D['spy_c1530'] = pick(spy, '15:30', 'close'); D['spy_c1544'] = pick(spy, '15:44', 'close'); D['spy_c1559'] = pick(spy, '15:59', 'close')
D['spy_close_off'] = spy_eod['close']; D['spy_open_off'] = spy_eod['open']
D['early_close'] = D.index.isin(early).astype(int)
D['year'] = D.index.str.slice(0, 4)
# gamma regime from gex-levels dated T-1
uw = pd.read_csv(UW); uw['gamma_flip'] = pd.to_numeric(uw['uw_gamma_flip'], errors='coerce')
avail = {}
for tk in ('SPY', 'SPX'):
    u = uw[uw['ticker'] == tk].set_index('date')
    ok = u[u['http'].astype(str).isin(['200', 'cache'])]; nn = ok[ok['gamma_flip'].notna()]
    avail[tk] = dict(first_http200=ok.index.min(), first_nonnull_flip=nn.index.min(), last=nn.index.max(), n_nonnull=int(len(nn)), n_http403=int((u['http'].astype(str) == '403').sum()),
                     n_null_after_first=int(((ok.index >= nn.index.min()) & ok['gamma_flip'].isna() & ok.index.isin(D.index[D['early_close'] == 0])).sum()))
    D[f'flip_{tk}_prev'] = u['gamma_flip'].reindex(D.index).shift(1)
    D[f'flip_{tk}_time_prev'] = u['uw_time'].reindex(D.index).shift(1)
D['spy_close_prev'] = D['spy_close_off'].shift(1); D['spx_close_prev'] = D['spx_close_off'].shift(1)
def regime(close_prev, flip):
    if pd.isna(flip) or pd.isna(close_prev): return 'unknown'
    return 'neg' if close_prev < flip else ('pos' if close_prev > flip else 'unknown')
D['regime_spy'] = [regime(c, f) for c, f in zip(D['spy_close_prev'], D['flip_SPY_prev'])]
D['regime_spx'] = [regime(c, f) for c, f in zip(D['spx_close_prev'], D['flip_SPX_prev'])]
# look-ahead stamp check: gex-levels 'time' (UTC) must be after the T-1 close (20:00Z EDT / 21:00Z EST)
def after_close(ts, d):
    if pd.isna(ts) or not isinstance(ts, str): return np.nan
    t = pd.Timestamp(ts); et = t.tz_convert('America/New_York'); return int(et.hour * 60 + et.minute >= 16 * 60)
D['flip_SPY_stamp_after_close'] = [after_close(t, d) for t, d in zip(D['flip_SPY_time_prev'], D.index)]
# returns (bp)
BP = 1e4
D['spx_rod'] = (D['spx_1530'] / D['spx_open'] - 1) * BP; D['spx_l30'] = (D['spx_1600'] / D['spx_1530'] - 1) * BP
D['spx_rod45'] = (D['spx_1545'] / D['spx_open'] - 1) * BP; D['spx_l15'] = (D['spx_1600'] / D['spx_1545'] - 1) * BP
D['spy_rod'] = (D['spy_c1529'] / D['spy_open'] - 1) * BP; D['spy_l30'] = (D['spy_close_off'] / D['spy_c1529'] - 1) * BP
D['spy_l30_1559'] = (D['spy_c1559'] / D['spy_c1529'] - 1) * BP; D['spy_l30_delayed'] = (D['spy_close_off'] / D['spy_c1530'] - 1) * BP
D['spy_rod45'] = (D['spy_c1544'] / D['spy_open'] - 1) * BP; D['spy_l15'] = (D['spy_close_off'] / D['spy_c1544'] - 1) * BP
sg = lambda s: np.sign(s)
D['strat_spx'] = sg(D['spx_rod']) * D['spx_l30']; D['strat_spx_45'] = sg(D['spx_rod45']) * D['spx_l15']
D['strat_spy_gross'] = sg(D['spy_rod']) * D['spy_l30']; D['strat_spy_net'] = D['strat_spy_gross'] - 2 * COST_BP * (D['spy_rod'] != 0)
D['strat_spy_net_1559'] = sg(D['spy_rod']) * D['spy_l30_1559'] - 2 * COST_BP * (D['spy_rod'] != 0)
D['strat_spy_net_delayed'] = sg(D['spy_rod']) * D['spy_l30_delayed'] - 2 * COST_BP * (D['spy_rod'] != 0)
D['strat_spy_net_45'] = sg(D['spy_rod45']) * D['spy_l15'] - 2 * COST_BP * (D['spy_rod45'] != 0)
D['strat_spy_spxsignal_net'] = sg(D['spx_rod']) * D['spy_l30'] - 2 * COST_BP * (D['spx_rod'] != 0)
req = ['spx_open', 'spx_1530', 'spx_1600', 'spy_open', 'spy_c1529', 'spy_close_off']
D['valid'] = ((D['early_close'] == 0) & D[req].notna().all(axis=1) & (D['spx_rows'] >= 380)).astype(int)
D.index.name = 'date'; D.to_csv(os.path.join(OUT, 'tb_daily.csv'))
V = D[D['valid'] == 1].copy()
# VIX splits (VIX level at 15:30 on day T, known at decision time)
vmed = V['vix_1530'].median()
V['vix_split_median'] = np.where(V['vix_1530'] >= vmed, f'VIX>={vmed:.1f}', f'VIX<{vmed:.1f}'); V['vix_split_20'] = np.where(V['vix_1530'] >= 20, 'VIX>=20', 'VIX<20')
# ---------- statistics ----------
def boot(x, stat, seed=SEED, n=B):
    x = np.asarray(x, float); rng = np.random.default_rng(seed); idx = rng.integers(0, len(x), (n, len(x))); v = np.array([stat(x[i]) for i in idx]); return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))
def sharpe(x): return float(x.mean() / x.std(ddof=1) * math.sqrt(252)) if len(x) > 2 and x.std(ddof=1) > 0 else np.nan
def block(df, col, label):
    x = df[col].dropna().values.astype(float); n = len(x)
    if n < 3: return dict(label=label, n=n)
    se = x.std(ddof=1) / math.sqrt(n); mlo, mhi = boot(x, np.mean); slo, shi = boot(x, sharpe)
    return dict(label=label, n=n, mean_bp=round(x.mean(), 3), t_stat=round(x.mean() / se, 2), sharpe=round(sharpe(x), 3), sharpe_ci=f'[{slo:.2f}, {shi:.2f}]', mean_ci=f'[{mlo:.2f}, {mhi:.2f}]',
                hit_rate=round(float((x > 0).mean()), 4), sd_bp=round(x.std(ddof=1), 2), first=df.index.min(), last=df.index.max())
def ols_beta(df, y, x, label):
    d = df[[y, x]].dropna(); n = len(d)
    if n < 10: return dict(label=label, n=n)
    X = np.column_stack([np.ones(n), d[x].values]); Y = d[y].values; b = np.linalg.lstsq(X, Y, rcond=None)[0]; e = Y - X @ b
    XtX = np.linalg.inv(X.T @ X); S = (X * (e ** 2)[:, None]).T @ X; V = XtX @ S @ XtX * n / (n - 2); se = math.sqrt(V[1, 1])
    rng = np.random.default_rng(SEED); bs = []
    for _ in range(B):
        i = rng.integers(0, n, n); Xi, Yi = X[i], Y[i]; bs.append(np.linalg.lstsq(Xi, Yi, rcond=None)[0][1])
    return dict(label=label, n=n, beta_x100=round(b[1] * 100, 2), se_x100=round(se * 100, 2), ci95_x100=f'[{(b[1] - 1.96 * se) * 100:.2f}, {(b[1] + 1.96 * se) * 100:.2f}]', boot_ci_x100=f'[{np.percentile(bs, 2.5) * 100:.2f}, {np.percentile(bs, 97.5) * 100:.2f}]', r2=round(1 - e.var() / Y.var(), 4))
STRATS = [('strat_spx', 'SPX index, 15:30->16:00, cost-free'), ('strat_spy_net', 'SPY shares, 15:30->official close, net 0.2 bp/side'), ('strat_spy_gross', 'SPY shares, gross'),
          ('strat_spy_net_1559', 'SPY, exit at the 15:59 bar close, net'), ('strat_spy_net_delayed', 'SPY, entry at the 15:30 bar close (1-min delay), net'), ('strat_spy_spxsignal_net', 'SPY traded on the SPX signal, net'),
          ('strat_spx_45', 'SPX index, 15:45->16:00'), ('strat_spy_net_45', 'SPY, 15:45->close, net')]
rows = []; reg = []; byyear = []
for proxy, rcol in (('SPY gex-levels', 'regime_spy'), ('SPX gex-levels', 'regime_spx')):
    for r in ('neg', 'pos', 'unknown', 'all'):
        sub = V if r == 'all' else V[V[rcol] == r]
        for col, lab in STRATS: rows.append(dict(proxy=proxy, regime=r, strategy=lab, **block(sub, col, lab)))
        reg.append(dict(proxy=proxy, regime=r, prior_baltussen_x100=PRIOR.get(r, ''), **ols_beta(sub, 'spx_l30', 'spx_rod', 'SPX: r_last30 on r_ROD')))
        reg.append(dict(proxy=proxy, regime=r, prior_baltussen_x100=PRIOR.get(r, ''), **ols_beta(sub, 'spy_l30', 'spy_rod', 'SPY: r_last30 on r_ROD')))
        for y, g in sub.groupby('year'):
            for col, lab in STRATS[:2]: byyear.append(dict(proxy=proxy, regime=r, year=y, strategy=lab, **block(g, col, lab)))
# gamma-available window only (so 'all' is comparable): days with a known SPY regime
W = V[V['regime_spy'] != 'unknown']
for col, lab in STRATS[:2]: rows.append(dict(proxy='SPY gex-levels', regime='neg+pos (known only)', strategy=lab, **block(W, col, lab)))
# VIX splits
for split in ('vix_split_median', 'vix_split_20'):
    for r in sorted(V[split].unique()):
        sub = V[V[split] == r]
        for col, lab in STRATS[:2]: rows.append(dict(proxy=split, regime=r, strategy=lab, **block(sub, col, lab)))
        reg.append(dict(proxy=split, regime=r, prior_baltussen_x100='', **ols_beta(sub, 'spx_l30', 'spx_rod', 'SPX: r_last30 on r_ROD')))
    # VIX split within the gamma window
    for r in sorted(V[split].unique()):
        sub = W[W[split] == r]
        for col, lab in STRATS[:2]: rows.append(dict(proxy=split + ' (gamma window)', regime=r, strategy=lab, **block(sub, col, lab)))
# unconditional by year (full sample)
for y, g in V.groupby('year'):
    for col, lab in STRATS[:2]: byyear.append(dict(proxy='none', regime='all', year=y, strategy=lab, **block(g, col, lab)))
SUM = pd.DataFrame(rows); REG = pd.DataFrame(reg); BY = pd.DataFrame(byyear)
SUM.to_csv(os.path.join(OUT, 'tb_summary.csv'), index=False); REG.to_csv(os.path.join(OUT, 'tb_regression.csv'), index=False); BY.to_csv(os.path.join(OUT, 'tb_by_year.csv'), index=False)
pd.DataFrame(avail).T.to_csv(os.path.join(OUT, 'tb_gex_availability.csv'))
# pass criterion
def crit(proxy):
    neg = SUM[(SUM['proxy'] == proxy) & (SUM['regime'] == 'neg') & (SUM['strategy'] == STRATS[1][1])].iloc[0]
    pos = SUM[(SUM['proxy'] == proxy) & (SUM['regime'] == 'pos') & (SUM['strategy'] == STRATS[1][1])].iloc[0]
    if not isinstance(pos.get('mean_ci'), str) or not isinstance(neg.get('sharpe_ci'), str):
        return dict(proxy=proxy, neg_n=neg.get('n'), pos_n=pos.get('n'), verdict='FAIL (insufficient regime data)')
    pos_lo, pos_hi = [float(v) for v in pos['mean_ci'].strip('[]').split(',')]
    ok_neg = (neg['sharpe'] > 1.0) and (neg['n'] >= 300); ok_pos = (pos_lo <= 0 <= pos_hi) and abs(pos['sharpe']) < 0.5
    return dict(proxy=proxy, neg_n=neg['n'], neg_sharpe=neg['sharpe'], neg_sharpe_ci=neg['sharpe_ci'], pos_n=pos['n'], pos_sharpe=pos['sharpe'], pos_mean_ci=pos['mean_ci'],
                neg_ok=f"Sharpe>1 and n>=300: {'yes' if ok_neg else 'no'}", pos_ok=f"mean CI covers 0 and |Sharpe|<0.5: {'yes' if ok_pos else 'no'}", verdict='PASS' if (ok_neg and ok_pos) else 'FAIL')
G = pd.DataFrame([crit('SPY gex-levels'), crit('SPX gex-levels')]); G.to_csv(os.path.join(OUT, 'tb_gate.csv'), index=False)
def md(df, cols=None):
    df = df if cols is None else df[cols]
    return '| ' + ' | '.join(df.columns) + ' |\n|' + '---|' * len(df.columns) + '\n' + '\n'.join('| ' + ' | '.join('' if (isinstance(v, float) and math.isnan(v)) else (f'{v:.4g}' if isinstance(v, float) else str(v)) for v in r) + ' |' for r in df.itertuples(index=False))
L = ['# T-B results: gamma-conditioned last-half-hour momentum\n',
     f"Generated by `analyze_tb.py` on {dt.date.today().isoformat()}. SPX minute prices {D.index.min()} to {D.index.max()}: {len(D)} sessions, {int(D['valid'].sum())} valid (early closes and incomplete days removed). Gamma regimes (SPY proxy): {V['regime_spy'].value_counts().to_dict()}; (SPX proxy): {V['regime_spx'].value_counts().to_dict()}. gex-levels stamp after the T-1 close: {int(V['flip_SPY_stamp_after_close'].sum())} of {int(V['flip_SPY_stamp_after_close'].notna().sum())} stamped days.\n",
     '## gex-levels availability (Unusual Whales)\n', md(pd.DataFrame(avail).T.reset_index().rename(columns={'index': 'ticker'})), '',
     '## Pass criterion (plan §5: net Sharpe > 1.0 on negative-gamma days with >= 300 days, ~0 on positive-gamma days; SPY net of 0.2 bp/side)\n', md(G), '',
     '## Per regime and pooled (bp per day; CIs = day bootstrap, 5,000 draws, seed 7; with one observation per day the day-clustered t equals the plain t)\n', md(SUM, ['proxy', 'regime', 'strategy', 'n', 'mean_bp', 'mean_ci', 't_stat', 'sharpe', 'sharpe_ci', 'hit_rate', 'first', 'last']), '',
     '## Regression slope of r_last30 on r_ROD (beta x 100; HC1 SE; Baltussen et al. 2021 priors: 6.6 negative gamma vs 0.8 positive)\n', md(REG), '',
     '## By year\n', md(BY, ['proxy', 'regime', 'year', 'strategy', 'n', 'mean_bp', 't_stat', 'sharpe', 'hit_rate']), '']
open(os.path.join(OUT, 'RESULTS.md'), 'w').write('\n'.join(L)); print('\n'.join(L[:12]))
