"""Hypothesis C: the pre-registered butterfly picks (preregistration.md) on SPY + QQQ pooled, fit and OOS, with the
moc_mag cut and a fill stress. P1 = 15:00 iron +-2, P2 = 15:00 long call fly +-2, P3 = 15:00 long call fly +-5; the
15:30 twins and the put form are printed beside them as the grid. Fill stress: every leg filled $0.01 (and $0.02) worse
than the NBBO used (4 legs: $4 / $8 a structure); 'mid' = every leg at its mid (the upper bound, not executable).
Writes out/picks.csv, out/picks_fillstress.csv.
"""
import os, sys, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_flies import load, boot_diff

PICKS = [('P1', '1500', 'iron', 'w2'), ('P2', '1500', 'call', 'w2'), ('P3', '1500', 'call', 'w5'),
         ('grid', '1500', 'put', 'w2'), ('grid', '1530', 'iron', 'w2'), ('grid', '1530', 'call', 'w2'), ('grid', '1530', 'call', 'w5'), ('grid', '1500', 'iron', 'w5'), ('grid', '1530', 'iron', 'w5'), ('grid', '1500', 'put', 'w5'), ('grid', '1500', 'call', 'w1'), ('grid', '1500', 'iron', 'wstraddle')]

def main():
    F = load().filter(pl.col('product').is_in(['SPY', 'QQQ']))
    rows = []; srows = []
    for tag, t, kind, wing in PICKS:
        d0 = F.filter((pl.col('t') == t) & (pl.col('kind') == kind) & (pl.col('wing') == wing))
        for per in ['fit', 'oos']:
            d = d0.filter(pl.col('period') == per)
            for prod in ['SPY+QQQ', 'SPY', 'QQQ']:
                g = d if prod == 'SPY+QQQ' else d.filter(pl.col('product') == prod)
                if g.height == 0: continue
                s = cell_stats(g['pnl'].to_numpy(), g['pct'].to_numpy(), g['session'].to_numpy())
                a = g.filter(pl.col('mag') == 'Q12'); b = g.filter(pl.col('mag') == 'Q345')
                if a.height and b.height:
                    lo, hi = boot_diff(a['pct'].to_numpy(), a['session'].to_numpy(), b['pct'].to_numpy(), b['session'].to_numpy())
                    s.update(nQ12=a.height, nQ345=b.height, Q12_pct=float(a['pct'].mean()), Q345_pct=float(b['pct'].mean()), diff_pct=float(a['pct'].mean() - b['pct'].mean()), diff_lo=lo, diff_hi=hi,
                             Q12_usd=float(a['pnl'].mean()), Q345_usd=float(b['pnl'].mean()), Q12_win=float((a['pnl'] > 0).mean()), Q345_win=float((b['pnl'] > 0).mean()))
                s.update(pick=tag, t=t, kind=kind, wing=wing, product=prod, period=per, mean_risk=float(g['risk'].mean()), mean_max_gain=float(g['max_gain'].mean()))
                rows.append(s)
                # fill stress
                for name, adj in (('nbbo', 0.0), ('worse_1c', 0.01), ('worse_2c', 0.02)):
                    pnl = g['pnl'].to_numpy() - adj * 4 * 100
                    risk = g['risk'].to_numpy() + adj * 4
                    ss = cell_stats(pnl, pnl / (risk * 100), g['session'].to_numpy())
                    srows.append(dict(pick=tag, t=t, kind=kind, wing=wing, product=prod, period=per, fill=name, n=ss['n'], mean_usd=ss['mean_usd'], mean_pct=ss['mean_pct'], ci_lo_pct=ss['ci_lo_pct'], ci_hi_pct=ss['ci_hi_pct'], win_rate=ss['win_rate'], wo_best5_usd=ss['wo_best5_usd'], profit_factor=ss['profit_factor'], by_year=ss['by_year']))
    out = pl.DataFrame(rows, infer_schema_length=None); out.write_csv(os.path.join(OUT, 'picks.csv'))
    st = pl.DataFrame(srows, infer_schema_length=None); st.write_csv(os.path.join(OUT, 'picks_fillstress.csv'))
    for r in out.iter_rows(named=True):
        q = f" | Q12={r['Q12_pct']*100:+5.1f}%(n{r['nQ12']},win{r['Q12_win']:.2f}) Q345={r['Q345_pct']*100:+5.1f}%(n{r['nQ345']},win{r['Q345_win']:.2f}) diff={r['diff_pct']*100:+5.1f} [{r['diff_lo']*100:+5.1f},{r['diff_hi']*100:+5.1f}]" if r.get('nQ12') else ''
        print(f"{r['pick']:4} {r['t']} {r['kind']:4} {r['wing']:9} {r['product']:7} {r['period']:3} risk={r['mean_risk']:.2f} maxG=${r['mean_max_gain']:.0f} | {fmt(r)}{q}")
    print('---- fill stress ----')
    for r in st.iter_rows(named=True):
        print(f"{r['pick']:4} {r['t']} {r['kind']:4} {r['wing']:9} {r['product']:7} {r['period']:3} {r['fill']:8} n={r['n']:4d} mean=${r['mean_usd']:+6.2f} ({r['mean_pct']*100:+5.1f}% [{r['ci_lo_pct']*100:+5.1f},{r['ci_hi_pct']*100:+5.1f}]) win={r['win_rate']:.2f} wo5=${r['wo_best5_usd']:+5.2f} PF={r['profit_factor']:.2f} | {r['by_year']}")

if __name__ == '__main__':
    main()
