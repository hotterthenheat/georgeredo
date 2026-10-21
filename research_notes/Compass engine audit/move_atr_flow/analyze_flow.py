"""Module 11: the flow proxy. Reads out/flow_<P>.parquet and out/sweeps_<P>.parquet.
imb_w   = cb_w - pb_w  (buy-side call premium minus buy-side put premium over the last w bars: the sweep_call_prem - sweep_put_prem proxy)
share_w = imb_w / (cb_w + pb_w)
net_w   = (cb_w - cs_w) - (pb_w - ps_w)  (bullish net premium, both sides judged)
Forward underlying returns r5/r15/r30 from the minute m (bars <= m-1 known). Minutes 16 <= m <= 390-k.
Tests: sign agreement; quintiles of share_w within product x period; a per-session slope of r_k on share_w (standardized
within the session) and its t-stat across sessions (Fama-MacBeth by session); the sweep entry's EV with and without
"trade-side premium > other side" over w bars. Writes out/flow_lead.csv, out/flow_quintiles.csv, out/flow_sweep.csv
"""
import os, sys, numpy as np, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
PRODUCTS = sys.argv[1].split(',') if len(sys.argv) > 1 else [p for p in ('SPY', 'QQQ', 'IWM', 'SPXW') if os.path.exists(os.path.join(OUT, f'flow_{p}.parquet'))]
period_col = pl.when(pl.col('session') <= '2024-12-31').then(pl.lit('pick 2022-2024')).otherwise(pl.lit('read 2025-2026')).alias('period')

def boot_days(df, col, n=2000, seed=0):
    g = df.group_by('session').agg(pl.col(col).sum().alias('s'), pl.len().alias('k')); s = g['s'].to_numpy(); k = g['k'].to_numpy(); D = len(s)
    if D < 10: return (np.nan, np.nan)
    idx = np.random.default_rng(seed).integers(0, D, (n, D)); means = s[idx].sum(1) / k[idx].sum(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))

def stress(df, col):
    o = dict(trades=df.height, days=df['session'].n_unique(), mean=float(df[col].mean()), win=float((df[col] > 0).mean()))
    o['ci_lo'], o['ci_hi'] = boot_days(df, col)
    g = df.group_by('session').agg(pl.col(col).sum().alias('s')).sort('s', descending=True)
    rest = df.filter(~pl.col('session').is_in(set(g['session'][:5].to_list()))); o['wo_best5'] = float(rest[col].mean()) if rest.height else np.nan
    for y in ('2022', '2023', '2024', '2025', '2026'):
        yy = df.filter(pl.col('session').str.starts_with(y)); o[f'mean_{y}'] = float(yy[col].mean()) if yy.height else np.nan
    return o

lead, quint, swp = [], [], []
for P in PRODUCTS:
    F = pl.read_parquet(os.path.join(OUT, f'flow_{P}.parquet')).with_columns(period_col)
    F = F.sort('session', 'm').with_columns(*[(pl.col(f'px_f{k}') / pl.col('px') - 1).alias(f'r{k}') for k in (5, 15, 30)],
                                           (pl.col('px') / pl.col('px').shift(5).over('session') - 1).alias('rb5'))
    for w in (1, 5, 15):
        F = F.with_columns((pl.col(f'cb_{w}') - pl.col(f'pb_{w}')).alias(f'imb_{w}'), ((pl.col(f'cb_{w}') - pl.col(f'pb_{w}')) / (pl.col(f'cb_{w}') + pl.col(f'pb_{w}'))).alias(f'share_{w}'),
                           ((pl.col(f'cb_{w}') - pl.col(f'cs_{w}')) - (pl.col(f'pb_{w}') - pl.col(f'ps_{w}'))).alias(f'net_{w}'))
    for (period,), G in F.group_by('period'):
        for w in (1, 5, 15):
            for sig in (f'share_{w}', f'net_{w}'):
                for k in (5, 15, 30):
                    g = G.filter((pl.col('m') >= 16) & (pl.col('m') <= 390 - k) & pl.col(sig).is_finite() & (pl.col(sig) != 0) & (pl.col(f'r{k}') != 0))
                    # standardize the signal within the session, slope of r on z, t across sessions
                    z = g.with_columns(((pl.col(sig) - pl.col(sig).mean().over('session')) / pl.col(sig).std().over('session')).alias('z'),
                                       ((pl.col('rb5') - pl.col('rb5').mean().over('session')) / pl.col('rb5').std().over('session')).alias('zb'),
                                       (pl.col(f'r{k}') - pl.col(f'r{k}').mean().over('session')).alias('rd')).filter(pl.col('z').is_finite() & pl.col('zb').is_finite())
                    # a per-session slope of r on z alone, and on z with the underlying's own last-5-minute return as a control
                    # (the proxy's side is the bar's close against the mean mid, which rises with the underlying inside the bar)
                    per = z.group_by('session').agg(((pl.col('z') * pl.col('rd')).sum() / (pl.col('z') ** 2).sum()).alias('slope'),
                                                    (pl.col('z') * pl.col('z')).sum().alias('szz'), (pl.col('zb') * pl.col('zb')).sum().alias('sbb'), (pl.col('z') * pl.col('zb')).sum().alias('szb'),
                                                    (pl.col('z') * pl.col('rd')).sum().alias('szr'), (pl.col('zb') * pl.col('rd')).sum().alias('sbr'), pl.len().alias('n')).filter(pl.col('n') >= 50)
                    det = per['szz'] * per['sbb'] - per['szb'] ** 2
                    partial = ((per['sbb'] * per['szr'] - per['szb'] * per['sbr']) / det).to_numpy() * 1e4
                    partial = partial[np.isfinite(partial)]
                    sl = per['slope'].to_numpy() * 1e4
                    lead.append(dict(product=P, period=period, window=w, signal=sig, horizon=k, obs=g.height, sessions=per.height,
                                     sign_agree=float((np.sign(g[sig].to_numpy()) == np.sign(g[f'r{k}'].to_numpy())).mean()),
                                     corr=float(np.corrcoef(g[sig].to_numpy(), g[f'r{k}'].to_numpy())[0, 1]),
                                     slope_bps_per_sd=float(sl.mean()), t_by_session=float(sl.mean() / (sl.std(ddof=1) / np.sqrt(len(sl)))) if len(sl) > 2 else np.nan,
                                     partial_slope_bps_per_sd=float(partial.mean()), t_partial=float(partial.mean() / (partial.std(ddof=1) / np.sqrt(len(partial)))) if len(partial) > 2 else np.nan))
                    if sig.startswith('share') and k in (5, 30):
                        q = g.with_columns(((pl.col(sig).rank('ordinal') - 1) * 5 // pl.len()).alias('q'))
                        for (qq,), b in q.group_by('q'):
                            quint.append(dict(product=P, period=period, window=w, signal=sig, horizon=k, quintile=int(qq) + 1, obs=b.height, mean_r_bps=1e4 * float(b[f'r{k}'].mean()), hit_up=float((b[f'r{k}'] > 0).mean())))
    # ---- the sweep entry with the premium condition
    fs = os.path.join(OUT, f'sweeps_{P}.parquet')
    if os.path.exists(fs):
        S = pl.read_parquet(fs).with_columns(period_col).join(F.select('session', pl.col('m').alias('t'), 'cb_1', 'pb_1', 'cb_5', 'pb_5', 'cb_15', 'pb_15'), on=['session', 't'], how='left')
        for (period,), G in S.group_by('period'):
            for kind in ('fade', 'break'):
                g = G.filter(pl.col(f'{kind}_entry_ask').is_not_null())
                base = dict(product=P, period=period, kind=kind, condition='none', window=0); base.update(stress(g, f'{kind}_pnl_trail')); swp.append(base)
                for w in (1, 5, 15):
                    # the trade's side: fade buys a put at an up sweep (puts are the trade side), a call at a down sweep; break the reverse
                    put_side = (pl.col('side') == 'up') if kind == 'fade' else (pl.col('side') == 'down')
                    cond = pl.when(put_side).then(pl.col(f'pb_{w}') > pl.col(f'cb_{w}')).otherwise(pl.col(f'cb_{w}') > pl.col(f'pb_{w}'))
                    for lab, mask in (('trade side > other', cond), ('trade side <= other', ~cond)):
                        b = g.filter(mask.fill_null(False))
                        if b.height: o = dict(product=P, period=period, kind=kind, condition=lab, window=w); o.update(stress(b, f'{kind}_pnl_trail')); swp.append(o)
    print(P, 'done', flush=True)

pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_rows(400)
L = pl.DataFrame(lead, infer_schema_length=None).sort('product', 'period', 'signal', 'window', 'horizon'); L.write_csv(os.path.join(OUT, 'flow_lead.csv')); print(L)
Q = pl.DataFrame(quint, infer_schema_length=None).sort('product', 'period', 'window', 'horizon', 'quintile'); Q.write_csv(os.path.join(OUT, 'flow_quintiles.csv')); print(Q)
if swp: W = pl.DataFrame(swp, infer_schema_length=None).sort('product', 'period', 'kind', 'window', 'condition'); W.write_csv(os.path.join(OUT, 'flow_sweep.csv')); print(W)
