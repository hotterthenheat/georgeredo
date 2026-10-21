"""More history for N: the same gates over every year on disk (SPY/QQQ/IWM from 2012-06, the names from 2020-01;
IBIT from 2024-01). 'pre' = before 2022 (no part of train or check). Fixed holds, gross, long side."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
from engine import *
pd.set_option('display.width',250); pd.set_option('display.max_rows',500)
bars=load_bars(); U=sorted(bars); F={s:features(bars[s]) for s in U}
for s in U:
    f=F[s]; c=bars[s]['close']; up=(c>c.shift(1))
    f['GATE']=f['B1']&f['B2']&f['B3']; f['SEQ5_12']=f['B1']&f['B2'].rolling(5).max().astype(bool)&f['B3_12']&up; f['SEQ3']=f['B1']&f['B2'].rolling(3).max().astype(bool)&f['B3']&up
    f['B1B2']=f['B1']&f['B2']; f['ALL']=True
def split_of(y): return 'train' if 2022<=y<=2024 else ('check' if y>=2025 else 'pre')
rows=[]
for H in [5,10,20]:
    for col in ['ALL','B1','B2','B3','B1B2','GATE','SEQ3','SEQ5_12']:
        parts=[]
        for s in U:
            f=F[s]; idx=np.where(f[col].fillna(False).values&(f['year'].values>=2013))[0]; r=fixed_hold(bars[s],idx,1,H)
            if len(r)==0: continue
            r['symbol']=s; r['year']=f.index.year.values[r['t'].values]; parts.append(r)
        r=pd.concat(parts); r=r[np.isfinite(r['ret'])]; r['split']=r['year'].map(split_of)
        for sp in ['pre','train','check','all']:
            q=r if sp=='all' else r[r['split']==sp]; x=q['ret'].values
            if len(x)<3: rows.append(dict(cond=col,H=H,split=sp,N=len(x))); continue
            rows.append(dict(cond=col,H=H,split=sp,N=len(x),hit=(x>0).mean(),mean=x.mean(),med=np.median(x),t=x.mean()/x.std(ddof=1)*np.sqrt(len(x)),mean_wo5=np.sort(x)[:-5].mean() if len(x)>5 else np.nan,etf_share=q['symbol'].isin(['SPY','QQQ','IWM']).mean()))
t=pd.DataFrame(rows); t.to_csv('all_years_fixed_hold.csv',index=False); print(t.round(4).to_string())
