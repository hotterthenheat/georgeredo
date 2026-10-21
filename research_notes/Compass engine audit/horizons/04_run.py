import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, json, sys, itertools
from engine import *
pd.set_option('display.width',250); pd.set_option('display.max_columns',40); pd.set_option('display.max_rows',500)
bars=load_bars(); U=sorted(bars)
F={s:features(bars[s]) for s in U}
TRAIN=(2022,2024); CHECK=(2025,2026)
HOLDS={'weekly':5,'swing':20,'leaps':63}

def split_of(y): return 'train' if TRAIN[0]<=y<=TRAIN[1] else ('check' if CHECK[0]<=y<=CHECK[1] else 'pre')

def collect(cond_name, cond_fn, side=1, H=10, mode='fixed', **kw):
    rows=[]
    for s in U:
        f=F[s]; df=bars[s]
        m=cond_fn(f).fillna(False).values & (f['year'].values>=2022)
        idx=np.where(m)[0]
        r=fixed_hold(df,idx,side,H) if mode=='fixed' else simulate(df,f,idx,side,H,**kw)
        if len(r)==0: continue
        r['symbol']=s; r['date']=f.index.values[r['t'].values]; r['year']=pd.DatetimeIndex(r['date']).year
        rows.append(r)
    r=pd.concat(rows,ignore_index=True); r['split']=r['year'].map(split_of); r['cond']=cond_name
    return r

def stats(r):
    if len(r)==0: return dict(N=0)
    x=r['ret'].values; 
    d=dict(N=len(x),hit=float((x>0).mean()),mean=float(x.mean()),med=float(np.median(x)),t=float(x.mean()/x.std(ddof=1)*np.sqrt(len(x))) if len(x)>2 and x.std()>0 else np.nan)
    # bootstrap by date (cluster): 500 resamples of entry dates
    g=r.groupby('date')['ret'].apply(lambda v:(v.sum(),len(v)))
    sums=np.array([a for a,b in g.values]); cnt=np.array([b for a,b in g.values]); rng=np.random.default_rng(7)
    bs=[]
    for _ in range(500):
        j=rng.integers(0,len(sums),len(sums)); bs.append(sums[j].sum()/cnt[j].sum())
    d['ci_lo'],d['ci_hi']=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
    if len(x)>10:
        d['mean_wo5trades']=float(np.sort(x)[:-5].mean())
        dd=r.groupby('date')['ret'].sum().sort_values(); keep=~r['date'].isin(dd.index[-5:])
        d['mean_wo5days']=float(r.loc[keep,'ret'].mean())
    return d

def table(r,label):
    rows=[]
    for sp in ['train','check']:
        q=r[r['split']==sp]; d=stats(q); d.update(cond=label,split=sp); rows.append(d)
    for y in sorted(r['year'].unique()):
        q=r[r['year']==y]; d=stats(q); d.update(cond=label,split=str(y)); rows.append(d)
    return pd.DataFrame(rows)

results={}
ALL=lambda f: pd.Series(True,index=f.index)
conds_long={'ALL':ALL,'B1':lambda f:f['B1'],'B2':lambda f:f['B2'],'B3':lambda f:f['B3'],
 'B1&B2':lambda f:f['B1']&f['B2'],'B1&B3':lambda f:f['B1']&f['B3'],'B2&B3':lambda f:f['B2']&f['B3'],
 'GATE(B1&B2&B3)':lambda f:f['B1']&f['B2']&f['B3'],
 'B1_daily&B2&B3':lambda f:f['B1_daily']&f['B2']&f['B3'],'B1_slope&B2&B3':lambda f:f['B1_slope']&f['B2']&f['B3'],'B1_200&B2&B3':lambda f:f['B1_200']&f['B2']&f['B3'],'B1_partial&B2&B3':lambda f:f['B1_partial']&f['B2']&f['B3'],
 'B1&B2_ema&B3':lambda f:f['B1']&f['B2_ema']&f['B3'],'B1&B2_wide&B3':lambda f:f['B1']&f['B2_wide']&f['B3'],'B1&B2_close&B3':lambda f:f['B1']&f['B2_close']&f['B3'],
 'B1&B2&B3_12':lambda f:f['B1']&f['B2']&f['B3_12'],'B1&B2&B3_range':lambda f:f['B1']&f['B2']&f['B3_range'],'B1&B2&B3_any':lambda f:f['B1']&f['B2']&f['B3_any'],
 'B1&B2_ema':lambda f:f['B1']&f['B2_ema'],'B1&B2_wide':lambda f:f['B1']&f['B2_wide'],
}
# 1) fixed holds, every condition, long side
out=[]
for H in [5,10,20,63]:
    for name,fn in conds_long.items():
        r=collect(name,fn,1,H,'fixed'); t=table(r,name); t['H']=H; t['side']='long'; out.append(t)
        if name=='GATE(B1&B2&B3)': r.to_pickle(f'entries_gate_long_H{H}.pkl')
        if name=='ALL' and H==10: r.to_pickle('entries_all_long_H10.pkl')
# short mirrored
for H in [5,10,20]:
    for name,fn in {'ALL':ALL,'S1':lambda f:f['S1'],'S2':lambda f:f['S2'],'S1&S2':lambda f:f['S1']&f['S2'],'GATE(S1&S2&S3)':lambda f:f['S1']&f['S2']&f['S3']}.items():
        r=collect(name,fn,-1,H,'fixed'); t=table(r,name); t['H']=H; t['side']='short'; out.append(t)
fixed=pd.concat(out,ignore_index=True); fixed.to_csv('fixed_hold_results.csv',index=False)
print('=== FIXED HOLDS (gross, underlying, entry next open, exit close of session t+H) ===')
print(fixed[fixed['split'].isin(['train','check'])].round(4).to_string())
# 2) the exit rules on the gate, long
out=[]
gate=conds_long['GATE(B1&B2&B3)']
variants={'weekly_H5_wkstop_emtgt':dict(H=5,stop_kind='wk',target_em=True),
 'weekly_H5_daystop_emtgt':dict(H=5,stop_kind='day',target_em=True),
 'weekly_H5_nostop_notgt':dict(H=5,stop_kind=None,target_em=False),
 'swing_H20_wkstop_emtgt':dict(H=20,stop_kind='wk',target_em=True),
 'swing_H20_wkstop_emtgt_stall3':dict(H=20,stop_kind='wk',target_em=True,stall=True),
 'swing_H20_wkstop_emtgt_rsi':dict(H=20,stop_kind='wk',target_em=True,rsi_exit=True),
 'swing_H20_wkstop_notgt':dict(H=20,stop_kind='wk',target_em=False),
 'swing_H20_fixed345_emtgt':dict(H=20,fixed_stop=0.0345,target_em=True),
 'swing_H20_daystop_emtgt':dict(H=20,stop_kind='day',target_em=True),
 'swing_H20_nostop_notgt':dict(H=20,stop_kind=None,target_em=False),
 'swing_H10_wkstop_emtgt':dict(H=10,stop_kind='wk',target_em=True),
 'leaps_H63_fixed8_notgt':dict(H=63,fixed_stop=0.08,target_em=False),
 'leaps_H63_nostop_notgt':dict(H=63,stop_kind=None,target_em=False),
 'leaps_H126_fixed8_notgt':dict(H=126,fixed_stop=0.08,target_em=False),
}
rows=[]; whys=[]
for vname,kw in variants.items():
    for cname,fn in [('GATE',gate),('ALL',ALL),('B1',lambda f:f['B1'])]:
        r=collect(cname,fn,1,mode='rules',**kw); t=table(r,cname); t['variant']=vname; rows.append(t)
        w=r.groupby(['split','why'])['ret'].agg(['count','mean']).reset_index(); w['variant']=vname; w['cond']=cname; whys.append(w)
        if cname=='GATE' and vname=='swing_H20_wkstop_emtgt': r.to_pickle('entries_gate_long_rules_swing.pkl'); print('stop distance (wk low) median', r['stop_dist'].median(), 'q25/q75', r['stop_dist'].quantile([.25,.75]).values, 'EM median',r['em'].median())
rules=pd.concat(rows,ignore_index=True); rules.to_csv('rule_exit_results.csv',index=False)
pd.concat(whys).to_csv('rule_exit_why.csv',index=False)
print('=== RULE EXITS (gross, underlying) ===')
print(rules[rules['split'].isin(['train','check'])].round(4).to_string())
# 3) random-entry baseline matched by count per symbol-year, same rules, swing variant
g=pd.read_pickle('entries_gate_long_rules_swing.pkl'); rng=np.random.default_rng(1)
cnt=g.groupby(['symbol','year']).size()
sim_means={'train':[],'check':[]}
for rep in range(200):
    rows=[]
    for (s,y),k in cnt.items():
        f=F[s]; cand=np.where((f['year'].values==y))[0]; cand=cand[cand<len(f)-21]
        idx=np.sort(rng.choice(cand,size=min(k,len(cand)),replace=False))
        r=simulate(bars[s],f,idx,1,20,stop_kind='wk',target_em=True); r['split']=split_of(y); rows.append(r)
    r=pd.concat(rows)
    for sp in ['train','check']: sim_means[sp].append(r.loc[r['split']==sp,'ret'].mean())
for sp in ['train','check']:
    gm=g.loc[g['split']==sp,'ret'].mean(); sm=np.array(sim_means[sp])
    print(f'RANDOM BASELINE swing rules {sp}: gate mean {gm:.4f}  random mean {sm.mean():.4f} sd {sm.std():.4f}  p(random>=gate) {(sm>=gm).mean():.3f}')
json.dump({k:[float(x) for x in v] for k,v in sim_means.items()},open('random_baseline_swing.json','w'))
# 4) gate firing counts
cnts=[]
for s in U:
    f=F[s]; q=f[f['year']>=2022]
    cnts.append(dict(symbol=s,days=len(q),B1=int(q['B1'].sum()),B2=int(q['B2'].sum()),B3=int(q['B3'].sum()),gate=int((q['B1']&q['B2']&q['B3']).sum()),B1B2=int((q['B1']&q['B2']).sum())))
cnts=pd.DataFrame(cnts); print(cnts.to_string()); cnts.to_csv('gate_counts.csv',index=False)
# panel for the logistic regression and B4
pan=[]
for s in U:
    f=F[s]; df=bars[s]; o,c=df['open'].values,df['close'].values; n=len(c)
    p=f[['B1','B2','B3','B1_daily','B2_ema','B3_12','B3_range','rvol','up_r_close','rsi14','sig20','year']].copy(); p['symbol']=s
    for H in [5,10,20]:
        r=np.full(n,np.nan); r[:n-H-1]=c[H+1:]/o[1:n-H]-1; p[f'fwd{H}']=r
    pan.append(p.reset_index().rename(columns={'index':'date'}))
pd.concat(pan).to_pickle('panel.pkl')
print('done')
