"""Q2: the spec's exclusions as causal claims, each read on 2022-24 and 2025-26 with fees in.
 (a) displacement-only entries (a 1-minute bar with range >= 2x the trailing 14-bar mean range, closing in its direction,
     no sweep within 3 bars) traded as continuation ('co') and as a fade ('fo'), against sweep entries;
 (b) ORH/ORL-only sweeps against those whose level lies within 0.2% of the prior day's high or low;
 (c) QQQ against SPY, IWM and SPXW fades;
 (d) the direction rule: fade against continuation by the spec's minute windows;
 (e) the gamma split: UW's daily net dealer gamma sign (call_gamma + put_gamma, the row dated the session), the year it covers.
Base definition: X=0, k=1, confirm=0 (the reference) and the merged trigger (any level, one entry a minute and side).
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I exclusions.py
"""
import os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S
from common_analysis import load_events, summarise, fmt

def stress_line(df, col, label):
    st = S.stress(df, col)
    print(f'   {label}: ' + ', '.join(f'{a}={b:.3g}' if isinstance(b, float) else f'{a}={b}' for a, b in st.items()))

if __name__ == '__main__':
    E = load_events()
    base = E.filter((pl.col('X') == 0) & (pl.col('k') == '1') & (pl.col('confirm') == 0))
    sweeps = base.filter(pl.col('level') != 'DISP').unique(['product', 'session', 'entry_m', 'side'])
    disp = base.filter(pl.col('level') == 'DISP')
    cols = ['events', 'sessions', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'tgt_pct', 'hold_usd', 'hold_pct', 'fwd30', 'fwd30_pos', 'fwdclose']
    print('== (a) displacement-only bars: continuation (co) and fade (fo), by period; sweeps (fade, fo) beside')
    for trade in ('co', 'fo'):
        print(f'-- displacement, {trade}'); print(fmt(summarise(disp, trade=trade, by=['period']).select(['period'] + cols)))
        print(fmt(summarise(disp, trade=trade, by=['product', 'period']).select(['product', 'period'] + cols)))
        for per in ('2022-24', '2025-26'): stress_line(disp.filter(pl.col('period') == per), f'{trade}_trail_net', f'disp {trade} trail {per}')
    print('-- sweeps, fo'); print(fmt(summarise(sweeps, trade='fo', by=['period']).select(['period'] + cols)))
    print('-- displacement by window (co = continuation)'); print(fmt(summarise(disp, trade='co', by=['window', 'period']).select(['window', 'period'] + cols)))
    summarise(disp, trade='co', by=['product', 'window', 'period']).write_csv(os.path.join(S.OUT, 'disp_co.csv'))
    summarise(disp, trade='fo', by=['product', 'window', 'period']).write_csv(os.path.join(S.OUT, 'disp_fo.csv'))

    print('\n== (b) OR sweeps: level within 0.2% of PDH/PDL (pd_near=1) against not, by period (X=0, k=1 and 3, confirm 0)')
    orr = E.filter((pl.col('level') == 'OR') & (pl.col('X') == 0) & pl.col('k').is_in(['1', '3']) & (pl.col('confirm') == 0))
    print(fmt(summarise(orr, trade='fo', by=['k', 'pd_near', 'period']).select(['k', 'pd_near', 'period'] + cols)))
    print(fmt(summarise(orr.filter(pl.col('k') == '1'), trade='fo', by=['product', 'pd_near', 'period']).select(['product', 'pd_near', 'period'] + cols)))
    for per in ('2022-24', '2025-26'):
        for near in (0, 1): stress_line(orr.filter((pl.col('k') == '1') & (pl.col('period') == per) & (pl.col('pd_near') == near)), 'fo_trail_net', f'OR k=1 pd_near={near} trail {per}')
    summarise(orr, trade='fo', by=['product', 'k', 'pd_near', 'period']).write_csv(os.path.join(S.OUT, 'or_pdnear.csv'))

    print('\n== (c) QQQ against the rest: merged fades by product and period, three exits')
    print(fmt(summarise(sweeps, trade='fo', by=['product', 'period']).select(['product', 'period'] + cols)))
    for p in ('SPY', 'QQQ', 'IWM', 'SPXW'):
        for per in ('2022-24', '2025-26'):
            stress_line(sweeps.filter((pl.col('product') == p) & (pl.col('period') == per)), 'fo_trail_net', f'{p} trail {per}')
    # QQQ with the delta pick too
    print(fmt(summarise(sweeps, trade='fd', by=['product', 'period']).select(['product', 'period', 'events', 'filled', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'hold_usd'])))

    print('\n== (d) direction by window: fade (fo) against continuation (co), merged sweeps, by period')
    d1 = summarise(sweeps, trade='fo', by=['window', 'period']).select(['window', 'period', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'hold_usd', 'fwd30', 'fwd30_pos', 'fwdclose']).rename({c: f'fade_{c}' for c in ['trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'hold_usd']})
    d2 = summarise(sweeps, trade='co', by=['window', 'period']).select(['window', 'period', 'trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'hold_usd']).rename({c: f'cont_{c}' for c in ['trail_usd', 'trail_pct', 'trail_win', 'tgt_usd', 'hold_usd']})
    D = d1.join(d2, on=['window', 'period']).sort('window', 'period'); print(fmt(D)); D.write_csv(os.path.join(S.OUT, 'direction_by_window.csv'))
    print('-- by side and window (fade fo)'); print(fmt(summarise(sweeps, trade='fo', by=['side', 'window', 'period']).select(['side', 'window', 'period', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'hold_usd', 'fwd30', 'fwdclose'])))

    print('\n== (e) gamma sign split (UW daily net dealer gamma, 2025-10-15 -> 2026-10-09; the row dated the session)')
    g = pl.concat([pl.read_parquet(f'/home/user/georgeredo/data_lake/unusualwhales/greek-exposure.part0{i}.parquet') for i in (1, 2)])
    g = g.filter(pl.col('ticker').is_in(['SPY', 'QQQ', 'IWM', 'SPX'])).with_columns(
        pl.col('date').str.to_date().alias('session'), (pl.col('call_gamma').cast(pl.Float64) + pl.col('put_gamma').cast(pl.Float64)).alias('net_gamma'),
        pl.when(pl.col('ticker') == 'SPX').then(pl.lit('SPXW')).otherwise(pl.col('ticker')).alias('product'))
    g = g.with_columns(pl.when(pl.col('net_gamma') > 0).then(pl.lit('positive')).otherwise(pl.lit('negative')).alias('gamma_sign')).select('product', 'session', 'gamma_sign', 'net_gamma')
    sg = sweeps.join(g, on=['product', 'session'], how='inner')
    print('covered events', sg.height, 'sessions', sg['session'].n_unique(), sg['session'].min(), '->', sg['session'].max())
    print(fmt(g.group_by('product', 'gamma_sign').agg(pl.len()).sort('product', 'gamma_sign')))
    print(fmt(summarise(sg, trade='fo', by=['gamma_sign']).select(['gamma_sign'] + cols)))
    print(fmt(summarise(sg, trade='co', by=['gamma_sign']).select(['gamma_sign', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'hold_usd']).rename({'trail_usd': 'cont_trail_usd', 'trail_pct': 'cont_trail_pct', 'trail_win': 'cont_trail_win', 'hold_usd': 'cont_hold_usd'})))
    print(fmt(summarise(sg, trade='fo', by=['gamma_sign', 'window']).select(['gamma_sign', 'window', 'events', 'trail_usd', 'trail_pct', 'trail_win', 'hold_usd', 'fwd30', 'fwdclose'])))
    for sgn in ('positive', 'negative'): stress_line(sg.filter(pl.col('gamma_sign') == sgn), 'fo_trail_net', f'gamma {sgn} fade trail')
    summarise(sg, trade='fo', by=['product', 'gamma_sign', 'window']).write_csv(os.path.join(S.OUT, 'gamma_split.csv'))
