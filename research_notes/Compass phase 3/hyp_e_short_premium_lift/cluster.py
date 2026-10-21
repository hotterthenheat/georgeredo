"""Where the signal's minutes fall: D1 / D1-2 rows by scan minute and by month, fit and OOS, on the trade rows of one cell;
and the monthly lift of two cells (the pick and the strongest OOS cell) - a clustering read for the stress tests.
python3 -I cluster.py  -> out/cluster.txt, out/signal_by_month.csv"""
import os, sys, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); L = []
S = pl.read_parquet(os.path.join(OUT, 'scores_SPY.parquet')).select(pl.col('session').cast(pl.Utf8), 'm', 'period', 'full_gbm_dec', 'full_gbm_score', 'dec_kind')
S = S.filter(pl.col('m').is_in(A.SCANS)).with_columns(pl.col('session').str.slice(0, 7).alias('month'))
L.append('t2 GBM decile share of SCAN minutes (this test\'s 12) by period: D1, D1-2, D10')
for per in ('fit', 'cut', 'oos'):
    g = S.filter(pl.col('period') == per); L.append(f"  {per}: rows {g.height}; D1 {(g['full_gbm_dec'] == 1).mean():.3f}; D1-2 {(g['full_gbm_dec'] <= 2).mean():.3f}; D10 {(g['full_gbm_dec'] == 10).mean():.3f}")
L.append('D1 share by scan minute (fit+cut / oos):')
for m in A.SCANS:
    a = S.filter((pl.col('m') == m) & (pl.col('period') != 'oos')); b = S.filter((pl.col('m') == m) & (pl.col('period') == 'oos'))
    L.append(f"  {A.hhmm(m)}: {(a['full_gbm_dec'] == 1).mean():.3f} / {(b['full_gbm_dec'] == 1).mean():.3f}   D1-2 {(a['full_gbm_dec'] <= 2).mean():.3f} / {(b['full_gbm_dec'] <= 2).mean():.3f}")
rows = []
for per in ('fit', 'cut', 'oos'):
    g = S.filter(pl.col('period') == per).group_by('month').agg(pl.len().alias('rows'), (pl.col('full_gbm_dec') == 1).sum().alias('d1'), (pl.col('full_gbm_dec') <= 2).sum().alias('d12'), pl.col('session').n_unique().alias('sessions')).sort('month')
    for r in g.iter_rows(named=True): rows.append(dict(period=per, **r, d1_share=r['d1'] / r['rows'], d12_share=r['d12'] / r['rows']))
M = pl.DataFrame(rows); M.write_csv(os.path.join(OUT, 'signal_by_month.csv'))
L.append('D1 share of scan minutes by month: ' + ', '.join(f"{r['month']} {r['d1_share']:.2f}" for r in M.iter_rows(named=True)))
# monthly lift of two cells
for mode in ('fit', 'oos'):
    X = A.load(mode)
    for st, ru, w, sig in (('put', 'd15', 2.0, 'D1-2'), ('condor', 'd25', 1.0, 'D1'), ('condor', 'd20', 2.0, 'D1'), ('condor', 'd25', 2.0, 'D1-2')):
        dlo, dhi = A.SIGNALS[sig]
        g = X.filter((pl.col('structure') == st) & (pl.col('rule') == ru) & (pl.col('width') == w)).with_columns(pl.col('session').str.slice(0, 7).alias('month'))
        tod = g.group_by('m_scan').agg(pl.col('pnl_hold').mean().alias('mu'))
        sg = g.filter((pl.col('dec') >= dlo) & (pl.col('dec') <= dhi)).join(tod, on='m_scan').with_columns((pl.col('pnl_hold') - pl.col('mu')).alias('d'))
        bm = sg.group_by('month').agg(pl.len().alias('n'), pl.col('d').mean().alias('lift'), pl.col('d').sum().alias('lift_total'), pl.col('pnl_hold').mean().alias('mean'), pl.col('session').n_unique().alias('sessions')).sort('month')
        L.append(f"\n{mode} {sig} {st} {ru} w{w:.0f} hold: N {sg.height}, lift ${sg['d'].mean():+.2f}; the all-rows mean by month vs the signal's, and the lift's total by month (months with the 5 largest totals marked):")
        top = set(bm.sort('lift_total', descending=True).head(5)['month'].to_list())
        allm = g.group_by('month').agg(pl.col('pnl_hold').mean().alias('all_mean'), pl.len().alias('n_all')).sort('month')
        bm = bm.join(allm, on='month')
        L.append('  ' + ' | '.join(f"{r['month']}{'*' if r['month'] in top else ''} n{r['n']} all {r['all_mean']:+.1f} sig {r['mean']:+.1f} lift {r['lift']:+.1f} tot {r['lift_total']:+.0f}" for r in bm.iter_rows(named=True)))
        L.append(f"  lift without the 5 months with the largest totals: ${bm.filter(~pl.col('month').is_in(top))['lift_total'].sum() / max(bm.filter(~pl.col('month').is_in(top))['n'].sum(), 1):+.2f} on {bm.filter(~pl.col('month').is_in(top))['n'].sum()} rows; months with a positive lift: {(bm['lift'] > 0).sum()} of {bm.height}")
        # the signal's sessions: how many of the period's sessions carry a signal row, and the losses avoided
        L.append(f"  sessions with a signal row: {sg['session'].n_unique()} of {g['session'].n_unique()}; the signal rows' full-loss share {(sg['pnl_hold'] <= -0.95 * sg['max_risk']).mean():.3f} vs all rows {(g['pnl_hold'] <= -0.95 * g['max_risk']).mean():.3f}; mean credit signal {sg['credit'].mean():.3f} vs all {g['credit'].mean():.3f}")
txt = '\n'.join(L); open(os.path.join(OUT, 'cluster.txt'), 'w').write(txt + '\n'); print(txt)
