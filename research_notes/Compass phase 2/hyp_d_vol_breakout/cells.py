"""The trade cells. Joins the per-minute trade table with the model's scores and reports every cell the brief names:
structure x exit x selection (D10 first-of-session, D10 every minute, D1 every minute, all minutes), per product and
pooled, with N, mean $ and % of debit, win rate, average win / loss, p5 / p1 / worst, the best 5 sessions' share, profit
factor, a session-bootstrap 95% CI, the mean without the best 5 sessions, by year, the time-of-day-matched paired lift of
D10 over all minutes, and whether the straddle at D10 minutes was priced richer than at the same minute on other sessions.
The opening drive (09:35) is its own table. The fit period's D10 is the out-of-fold decile; the cut and oos periods use
the registered cuts (set on the cut slice).
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I cells.py fit,cut t2 gbm     # before the OOS read
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I cells.py oos t2 gbm
Outputs: out/cells_<periods>_<target>_<model>.csv, out/cells_by_year_..., out/paired_lift_..., out/opening_drive_...,
out/straddle_rich_... ; the printed log goes to logs/.
"""
import os, sys, time
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib as L

def load(periods, target, model):
    key = f'{target}_full_{model}'
    sc = pl.read_parquet(os.path.join(L.OUT, 'scores.parquet'), columns=['product', 'session', 'm', 'period', f'{key}_dec', f'{key}_dec_oof'])
    sc = sc.with_columns(pl.when(pl.col('period') == 'fit').then(pl.col(f'{key}_dec_oof')).otherwise(pl.col(f'{key}_dec')).alias('dec')).select('product', 'session', 'm', 'period', 'dec')
    frames = []
    for p in L.PRODUCTS:
        f = os.path.join(L.OUT, f'minutes_{p}.parquet')
        if os.path.exists(f): frames.append(pl.read_parquet(f))
    M = L.with_period(pl.concat(frames, how='diagonal_relaxed'))
    M = M.join(sc.drop('period'), on=['product', 'session', 'm'], how='left').filter(pl.col('period').is_in(periods))
    return M

def by_year(df, net_col, ret_col):
    return df.group_by('year').agg(pl.len().alias('n'), pl.col(net_col).mean().alias('usd'), pl.col(ret_col).mean().alias('pct'), (pl.col(net_col) > 0).mean().alias('win')).sort('year')

def selections(M):
    """returns dict name -> frame of the rows selected"""
    d10 = M.filter(pl.col('dec') == 10)
    first = d10.sort('session', 'm').unique(['product', 'session'], keep='first', maintain_order=True)
    return {'d10_first': first, 'd10_every': d10, 'd1_every': M.filter(pl.col('dec') == 1), 'all_every': M}

if __name__ == '__main__':
    periods = sys.argv[1].split(','); target = sys.argv[2]; model = sys.argv[3]
    tag = f'{"+".join(periods)}_{target}_{model}'
    t0 = time.time(); M = load(periods, target, model)
    print('rows', M.height, 'sessions', M['session'].n_unique(), 'periods', periods, 'target', target, 'model', model, flush=True)
    # D10 share by period and product (the registered cuts may not give 10% out of sample)
    print(M.group_by('period', 'product').agg(pl.len().alias('n'), (pl.col('dec') == 10).mean().alias('d10_share'), (pl.col('dec') == 1).mean().alias('d1_share')).sort('period', 'product'))
    # straddle richness at D10: straddle_rel / the median straddle_rel of the same (product, m, period) over every session
    med = M.group_by('product', 'm', 'period').agg(pl.col('straddle_rel').median().alias('str_med'))
    R = M.join(med, on=['product', 'm', 'period']).with_columns((pl.col('straddle_rel') / pl.col('str_med')).alias('str_ratio'))
    rich = R.group_by('period', 'product', (pl.col('dec') == 10).alias('is_d10')).agg(pl.len().alias('n'), pl.col('str_ratio').mean().alias('ratio_mean'), pl.col('str_ratio').median().alias('ratio_median'), (pl.col('str_ratio') > 1).mean().alias('share_above_median'), pl.col('straddle_rel').mean().alias('straddle_rel_mean'), pl.col('implied30').mean().alias('implied30_mean'), pl.col('mv30_bps').mean().alias('mv30_mean')).sort('period', 'product', 'is_d10')
    print('\n== straddle/spot at D10 minutes against the same minute on other sessions'); print(rich)
    rich.write_csv(os.path.join(L.OUT, f'straddle_rich_{tag}.csv'))
    sels = selections(M)
    rows = []; yrows = []; prows = []
    structs = list(L.STRUCTS); exits = list(L.EXITS)
    for st in structs:
        for ex in exits:
            nc, rc = f'{st}_{ex}_net', f'{st}_{ex}_ret'
            if nc not in M.columns: continue
            for sname, sel in sels.items():
                for prod in ('ALL',) + L.PRODUCTS:
                    for per in (periods if len(periods) == 1 else periods + ['+'.join(periods)]):
                        sub = sel if prod == 'ALL' else sel.filter(pl.col('product') == prod)
                        sub = sub.filter(pl.col('period').is_in(per.split('+'))).filter(pl.col(nc).is_not_null())
                        if sub.height == 0: continue
                        stt = L.cell_stats(sub[nc].to_numpy(), sub[rc].to_numpy(), sub['session'].cast(pl.Utf8).to_numpy())
                        stt.update(structure=st, exit=ex, selection=sname, product=prod, period=per, debit_mean=float(sub[f'{st}_debit'].mean()))
                        rows.append(stt)
                        if prod == 'ALL' or True:
                            for yr in by_year(sub, nc, rc).to_dicts():
                                yrows.append(dict(structure=st, exit=ex, selection=sname, product=prod, period=per, **yr))
            # paired, time-of-day-matched lift of D10 over all minutes: baseline = the mean of every session's trade at the
            # same (product, m, period), the trade's own session left out
            base = M.filter(pl.col(nc).is_not_null()).group_by('product', 'm', 'period').agg(pl.col(nc).sum().alias('s'), pl.col(rc).sum().alias('sr'), pl.len().alias('k'))
            for sname in ('d10_first', 'd10_every', 'd1_every'):
                P = sels[sname].filter(pl.col(nc).is_not_null()).join(base, on=['product', 'm', 'period']).filter(pl.col('k') > 1)
                P = P.with_columns(((pl.col('s') - pl.col(nc)) / (pl.col('k') - 1)).alias('b_usd'), ((pl.col('sr') - pl.col(rc)) / (pl.col('k') - 1)).alias('b_pct'))
                P = P.with_columns((pl.col(nc) - pl.col('b_usd')).alias('d_usd'), (pl.col(rc) - pl.col('b_pct')).alias('d_pct'))
                for prod in ('ALL',) + L.PRODUCTS:
                    for per in (periods if len(periods) == 1 else periods + ['+'.join(periods)]):
                        sub = P if prod == 'ALL' else P.filter(pl.col('product') == prod)
                        sub = sub.filter(pl.col('period').is_in(per.split('+')))
                        if sub.height == 0: continue
                        s1 = L.cell_stats(sub['d_usd'].to_numpy(), sub['d_pct'].to_numpy(), sub['session'].cast(pl.Utf8).to_numpy())
                        prows.append(dict(structure=st, exit=ex, selection=sname, product=prod, period=per, n=s1['n'], lift_usd=s1['mean_usd'], lift_ci_lo=s1['ci_lo'], lift_ci_hi=s1['ci_hi'], lift_pct=s1['mean_pct'], lift_wo_best5=s1['wo_best5'],
                                          sel_usd=float(sub[nc].mean()), matched_usd=float(sub['b_usd'].mean()), sel_pct=float(sub[rc].mean()), matched_pct=float(sub['b_pct'].mean())))
    C = pl.DataFrame(rows); C.write_csv(os.path.join(L.OUT, f'cells_{tag}.csv'))
    pl.DataFrame(yrows).write_csv(os.path.join(L.OUT, f'cells_by_year_{tag}.csv'))
    PL = pl.DataFrame(prows); PL.write_csv(os.path.join(L.OUT, f'paired_lift_{tag}.csv'))
    pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_rows(400); pl.Config.set_float_precision(2)
    show = ['structure', 'exit', 'selection', 'period', 'n', 'sessions', 'debit_mean', 'mean_usd', 'mean_pct', 'ci_lo', 'ci_hi', 'wo_best5', 'win', 'avg_win', 'avg_loss', 'p5', 'p1', 'worst', 'best5_share', 'profit_factor', 'sessions_up']
    for per in (periods if len(periods) == 1 else periods + ['+'.join(periods)]):
        print(f'\n==== pooled cells, period {per} (dollars pool SPXW with the ETFs; % of debit is the cross-product yardstick)')
        print(C.filter((pl.col('product') == 'ALL') & (pl.col('period') == per)).select(show).sort('structure', 'exit', 'selection'))
    print('\n==== by product, D10 first-of-session and all minutes, hold 30 / trail / settle')
    print(C.filter((pl.col('product') != 'ALL') & pl.col('selection').is_in(['d10_first', 'all_every']) & pl.col('exit').is_in(['h30', 'trail', 'settle'])).select(['product'] + show).sort('product', 'structure', 'exit', 'selection', 'period'))
    print('\n==== paired, time-of-day-matched lift of D10 over all minutes (pooled)')
    print(PL.filter(pl.col('product') == 'ALL').sort('structure', 'exit', 'selection', 'period'))
    # the opening drive: 09:35, straddle and the side of the 09:30-09:35 move; unconditional and D10-only at 09:35
    O = M.filter(pl.col('m') == 5)
    orows = []
    for st in ('str', 'sg15', L.OD_STRUCT):
        for ex in ('e0955', 'e1030', 'trail', 'settle', 'ri'):
            nc, rc = f'{st}_{ex}_net', f'{st}_{ex}_ret'
            if nc not in O.columns: continue
            for sname, sub0 in (('unconditional', O), ('d10_at_0935', O.filter(pl.col('dec') == 10)), ('d1_at_0935', O.filter(pl.col('dec') == 1))):
                for prod in ('ALL',) + L.PRODUCTS:
                    for per in (periods if len(periods) == 1 else periods + ['+'.join(periods)]):
                        sub = sub0 if prod == 'ALL' else sub0.filter(pl.col('product') == prod)
                        sub = sub.filter(pl.col('period').is_in(per.split('+'))).filter(pl.col(nc).is_not_null())
                        if sub.height == 0: continue
                        stt = L.cell_stats(sub[nc].to_numpy(), sub[rc].to_numpy(), sub['session'].cast(pl.Utf8).to_numpy())
                        stt.update(structure=st, exit=ex, selection=sname, product=prod, period=per, debit_mean=float(sub[f'{st}_debit'].mean()))
                        yr = by_year(sub, nc, rc); stt['by_year_pct'] = ' '.join(f"{r['year']}:{r['pct']:+.1f}({r['n']})" for r in yr.to_dicts())
                        orows.append(stt)
    OD = pl.DataFrame(orows); OD.write_csv(os.path.join(L.OUT, f'opening_drive_{tag}.csv'))
    print('\n==== the opening drive at 09:35 (pooled and by product)')
    print(OD.select(['product'] + show + ['by_year_pct']).sort('product', 'structure', 'exit', 'selection', 'period'))
    print(f'done {time.time() - t0:.0f}s')
