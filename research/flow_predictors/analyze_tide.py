"""Test 2: market-wide net premium (market-tide, 5-minute, cumulative) level and 30-minute change vs SPY forward 30/60-minute returns."""
import pandas as pd, numpy as np
from common import *
from stats import cell, pooled_ic, quintiles
df = pd.read_csv(os.path.join(OUT, 'panel_tide.csv.gz'))
rows = []; cond = []
for align in ('tradable', 'contemp'):
    d = df[df['align'] == align]
    for ft in ('T_level', 'T_chg30'):
        for h in (30, 60):
            r = cell(d[ft].values, d[f'r{h}'].values, d.date.values, B=2000)
            rows.append(dict(test='tide', ticker='SPY', feature=ft, horizon=h, align=align, **r))
            if align == 'tradable':
                for cname, vals in (('regime', ('POS', 'NEG')), ('tod', ('09:45-10:30', '10:30-12:00', '12:00-14:00', '14:00-15:30'))):
                    for v in vals:
                        s = d[d[cname] == v]
                        rr = pooled_ic(s[ft].values, s[f'r{h}'].values, s.date.values, B=1000); qq = quintiles(s[ft].values, s[f'r{h}'].values, s.date.values, B=1000); qq.pop('qmeans')
                        cond.append(dict(ticker='SPY', feature=ft, horizon=h, condition=cname, value=v, **rr, **qq))
pd.DataFrame(rows).to_csv(os.path.join(OUT, 'tide_ic_main.csv'), index=False, float_format='%.5g')
pd.DataFrame(cond).to_csv(os.path.join(OUT, 'tide_ic_conditional.csv'), index=False, float_format='%.5g')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(pd.DataFrame(rows)[['feature', 'horizon', 'align', 'n', 'days', 'ic', 'lo', 'hi', 'p', 'dic_mean', 'dic_t', 'q1_bps', 'q5_bps', 'spread', 'sp_lo', 'sp_hi', 'hr_top', 'hr_bot']].to_string())
print(pd.DataFrame(cond)[['feature', 'horizon', 'condition', 'value', 'n', 'ic', 'lo', 'hi', 'p', 'spread', 'sp_lo', 'sp_hi']].to_string())
