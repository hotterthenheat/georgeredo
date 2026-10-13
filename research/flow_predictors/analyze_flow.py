"""Test 1: Spearman IC / quintile spreads / hit rates for F1,F2,F2u,F3 vs forward 15/30/60-minute log returns, per ticker; by GEX regime and time of day."""
import pandas as pd, numpy as np, time
from common import *
from stats import cell, pooled_ic, quintiles
df = pd.read_csv(os.path.join(OUT, 'panel_flow.csv.gz'))
df = df.sort_values(['ticker', 'date', 'minute']).reset_index(drop=True)
# trailing 15-minute return (diagnostic: how much of each feature is just the recent move)
ls = np.log(df.spot.values); back = np.full(len(df), np.nan)
same = (df.ticker.values[15:] == df.ticker.values[:-15]) & (df.date.values[15:] == df.date.values[:-15]) & (df.minute.values[15:] - df.minute.values[:-15] == 15)
back[15:][same] = (ls[15:] - ls[:-15])[same]; df['r_back15'] = back
FEATS = ['F1', 'F2', 'F2u', 'F3']; H = (15, 30, 60); t0 = time.time()
main = []; cond = []
for tk in TICKERS:
    d = df[df.ticker == tk]
    for ft in FEATS:
        rb = pooled_ic(d[ft].values, d['r_back15'].values, d.date.values, B=500)
        for h in H:
            r = cell(d[ft].values, d[f'r{h}'].values, d.date.values, B=2000)
            main.append(dict(test='flow', ticker=tk, feature=ft, horizon=h, ic_vs_trailing15=rb['ic'], **r))
            for cname, col, vals in (('regime', 'regime', ('POS', 'NEG')), ('tod', 'tod', ('09:45-10:30', '10:30-12:00', '12:00-14:00', '14:00-15:30'))):
                for v in vals:
                    s = d[d[col] == v]
                    rr = pooled_ic(s[ft].values, s[f'r{h}'].values, s.date.values, B=1000); qq = quintiles(s[ft].values, s[f'r{h}'].values, s.date.values, B=1000); qq.pop('qmeans')
                    cond.append(dict(ticker=tk, feature=ft, horizon=h, condition=cname, value=v, **rr, **qq))
    print(tk, round(time.time() - t0), 's', flush=True)
pd.DataFrame(main).to_csv(os.path.join(OUT, 'flow_ic_main.csv'), index=False, float_format='%.5g')
pd.DataFrame(cond).to_csv(os.path.join(OUT, 'flow_ic_conditional.csv'), index=False, float_format='%.5g')
m = pd.DataFrame(main)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(m[['ticker', 'feature', 'horizon', 'n', 'days', 'ic', 'lo', 'hi', 'p', 'dic_mean', 'dic_t', 'ic_vs_trailing15', 'q1_bps', 'q5_bps', 'spread', 'sp_lo', 'sp_hi', 'hr_top', 'hr_bot', 'sign_agree']].to_string())
