"""The touch's contribution over unconditional short premium, pooled over every scan. Reads out/trades_<P>.parquet.
Writes out/paired.csv.  python3 -I paired.py
For each touch row (mult 1.0, one row a scan x side x t, the audit's event) the SAME-SESSION PAIR is the scheduled sell at
the touch's own scan minute of the same side, rule and width (the 'at' rule pairs with 'em1', the band's own edge, since
"the first strike at or beyond the touch price" at the scan is the band edge). Columns a (product, period, width, rule,
management): touch rows paired, the touch mean $, the pair's mean $, the paired difference with a session-bootstrap 95%
range, and the UNCONDITIONAL baseline: the same structure sold at every full session's scan minutes (every session, the
touch's scans), its mean $ and % of max risk. The same-session pair is a LOOK-AHEAD comparison (a scan-time sell in a
session that then reached the band on that side was run through by construction), so the touch's contribution is read
against the TIME-OF-DAY-MATCHED unconditional sell: each touch at minute t is matched to the scheduled sells of the same
side, rule and width at the scan minute nearest t in EVERY session of the period (`tod_mean`, `tod_pct_risk`, the touches'
own mix of sides and times), and `touch_minus_tod_pct` is the touch cell's mean % of max risk less that. Dollars a spread,
fees in, as engine.py.
"""
import os, numpy as np, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
MGMT = {'hold': 'pnl_hold', 'tp50': 'pnl_tp', 'stop2x': 'pnl_stop', 'tp50+stop2x': 'pnl_both'}
period_col = pl.when(pl.col('session') <= '2024-12-31').then(pl.lit('fit 2022-2024')).otherwise(pl.lit('oos 2025-2026')).alias('period')

def boot(df, col, n=2000, seed=0):
    g = df.group_by('session').agg(pl.col(col).sum().alias('s'), pl.len().alias('k'))
    s = g['s'].to_numpy(); k = g['k'].to_numpy(); D = len(s)
    if D < 10: return (np.nan, np.nan)
    rng = np.random.default_rng(seed); idx = rng.integers(0, D, (n, D))
    means = s[idx].sum(1) / k[idx].sum(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))

SCANS = np.array([5, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360, 380])
rows = []
for P in ('SPXW', 'SPY'):
    X = pl.read_parquet(os.path.join(OUT, f'trades_{P}.parquet')).with_columns(period_col)
    T = X.filter((pl.col('test') == 'touch') & (pl.col('mult') == 1.0)).with_columns(pl.when(pl.col('touch_side') == 'up').then(pl.lit('call')).otherwise(pl.lit('put')).alias('structure'),
                                                                                   pl.when(pl.col('rule') == 'at').then(pl.lit('em1')).otherwise(pl.col('rule')).alias('brule'))
    S = X.filter((pl.col('test') == 'sched') & (pl.col('structure') != 'condor'))
    for (period, width, rule), g in T.group_by('period', 'width', 'rule'):
        brule = g['brule'][0]
        b = S.filter((pl.col('period') == period) & (pl.col('width') == width) & (pl.col('rule') == brule))
        pr = g.select('session', 'structure', 'm_scan', 'e', *[pl.col(c).alias(f't_{c}') for c in MGMT.values()]) \
              .join(b.select('session', 'structure', 'm_scan', *[pl.col(c).alias(f'b_{c}') for c in MGMT.values()]), on=['session', 'structure', 'm_scan'], how='inner')
        near = g.with_columns(pl.Series('m_near', SCANS[np.abs(g['e'].to_numpy()[:, None] - SCANS[None, :]).argmin(1)]))
        mix = near.group_by('structure', 'm_near').len().rename({'m_near': 'm_scan', 'len': 'w'})
        for mg, col in MGMT.items():
            d = pr.with_columns((pl.col(f't_{col}') - pl.col(f'b_{col}')).alias('d'))
            lo, hi = boot(d, 'd')
            base = b.filter(pl.col('m_scan').is_in(g['m_scan'].unique().to_list()))
            tod = b.group_by('structure', 'm_scan').agg(pl.col(col).mean().alias('mu'), (pl.col(col) / pl.col('max_risk')).mean().alias('mp'), pl.len().alias('n')).join(mix, on=['structure', 'm_scan'], how='inner')
            tod_mean = float((tod['mu'] * tod['w']).sum() / tod['w'].sum()); tod_pct = float((tod['mp'] * tod['w']).sum() / tod['w'].sum() * 100)
            rows.append(dict(product=P, period=period, width=width, rule=rule, pair_rule=brule, management=mg, paired_N=d.height, paired_sessions=d['session'].n_unique(),
                             touch_mean=float(d[f't_{col}'].mean()), pair_mean=float(d[f'b_{col}'].mean()), paired_diff=float(d['d'].mean()), diff_ci_lo=lo, diff_ci_hi=hi,
                             uncond_N=base.height, uncond_sessions=base['session'].n_unique(), uncond_mean=float(base[col].mean()), uncond_pct_risk=float((base[col] / base['max_risk']).mean() * 100),
                             touch_pct_risk=float((g[col] / g['max_risk']).mean() * 100), tod_N=int(tod['n'].sum()), tod_mean=tod_mean, tod_pct_risk=tod_pct, touch_minus_tod_pct=float((g[col] / g['max_risk']).mean() * 100) - tod_pct))
R = pl.DataFrame(rows).sort('product', 'period', 'width', 'rule', 'management')
R.write_csv(os.path.join(OUT, 'paired.csv'))
pl.Config.set_tbl_rows(400); pl.Config.set_tbl_width_chars(260); pl.Config.set_float_precision(2)
print(R.filter(pl.col('management') == 'hold').select('product', 'period', 'width', 'rule', 'paired_N', 'touch_mean', 'touch_pct_risk', 'uncond_pct_risk', 'tod_N', 'tod_mean', 'tod_pct_risk', 'touch_minus_tod_pct'))
