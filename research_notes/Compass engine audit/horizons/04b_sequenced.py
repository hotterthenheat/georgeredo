"""The same-day AND gate fired 20 times in 2022-2026 (14 train, 6 check): a pullback day that touches the OTE zone and
prints 1.5x volume in an uptrend is rare. The natural multi-day reading of the spec, declared BEFORE looking at
returns: the pullback (B2) happened within the last k sessions, and today is the confirmation day (B3 volume, an
up close). Four variants, all reported; nothing picked by its result."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, json
from engine import *
pd.set_option('display.width',250); pd.set_option('display.max_columns',40); pd.set_option('display.max_rows',500)
bars=load_bars(); U=sorted(bars); F={s:features(bars[s]) for s in U}
for s in U:
    f=F[s]; c=bars[s]['close']; up=(c>c.shift(1))
    f['B2_r3']=f['B2'].rolling(3).max().astype(bool); f['B2_r5']=f['B2'].rolling(5).max().astype(bool); f['B2ema_r3']=f['B2_ema'].rolling(3).max().astype(bool)
    f['SEQ3']=f['B1']&f['B2_r3']&f['B3']&up
    f['SEQ5']=f['B1']&f['B2_r5']&f['B3']&up
    f['SEQ3_12']=f['B1']&f['B2_r3']&f['B3_12']&up
    f['SEQE3']=f['B1']&f['B2ema_r3']&f['B3']&up
    f['SEQ5_12']=f['B1']&f['B2_r5']&f['B3_12']&up
    f['SEQ5_12_noup']=f['B1']&f['B2_r5']&f['B3_12']
    # the mirrored short
    dn=(c<c.shift(1)); f['S2_r5']=f['S2'].rolling(5).max().astype(bool); f['SSEQ5_12']=f['S1']&f['S2_r5']&f['B3_12']&dn
TRAIN=(2022,2024); CHECK=(2025,2026)
def split_of(y): return 'train' if TRAIN[0]<=y<=TRAIN[1] else ('check' if CHECK[0]<=y<=CHECK[1] else 'pre')
def collect(name,col,side=1,H=10,mode='fixed',**kw):
    rows=[]
    for s in U:
        f=F[s]; m=f[col].fillna(False).values&(f['year'].values>=2022); idx=np.where(m)[0]
        r=fixed_hold(bars[s],idx,side,H) if mode=='fixed' else simulate(bars[s],f,idx,side,H,**kw)
        if len(r)==0: continue
        r['symbol']=s; r['date']=f.index.values[r['t'].values]; r['year']=pd.DatetimeIndex(r['date']).year; rows.append(r)
    r=pd.concat(rows,ignore_index=True); r=r[np.isfinite(r['ret'])]; r['split']=r['year'].map(split_of); r['cond']=name; return r
def stats(r):
    x=r['ret'].values
    if len(x)<3: return dict(N=len(x))
    d=dict(N=len(x),hit=float((x>0).mean()),mean=float(x.mean()),med=float(np.median(x)),t=float(x.mean()/x.std(ddof=1)*np.sqrt(len(x))))
    g=r.groupby('date')['ret'].agg(['sum','count']); sums=g['sum'].values; cnt=g['count'].values; rng=np.random.default_rng(7); bs=[]
    for _ in range(500):
        j=rng.integers(0,len(sums),len(sums)); bs.append(sums[j].sum()/cnt[j].sum())
    d['ci_lo'],d['ci_hi']=float(np.percentile(bs,2.5)),float(np.percentile(bs,97.5))
    if len(x)>10:
        d['mean_wo5trades']=float(np.sort(x)[:-5].mean()); dd=r.groupby('date')['ret'].sum().sort_values(); d['mean_wo5days']=float(r.loc[~r['date'].isin(dd.index[-5:]),'ret'].mean())
    return d
def table(r,label):
    rows=[]
    for sp in ['train','check']:
        d=stats(r[r['split']==sp]); d.update(cond=label,split=sp); rows.append(d)
    for y in sorted(r['year'].unique()):
        d=stats(r[r['year']==y]); d.update(cond=label,split=str(y)); rows.append(d)
    return pd.DataFrame(rows)
cnt=pd.DataFrame([{**{'symbol':s},**{k:int(F[s].loc[F[s]['year']>=2022,k].sum()) for k in ['SEQ3','SEQ5','SEQ3_12','SEQE3','SEQ5_12','SEQ5_12_noup','SSEQ5_12']}} for s in U]); print(cnt.to_string()); print(cnt.sum(numeric_only=True)); cnt.to_csv('seq_gate_counts.csv',index=False)
out=[]
for H in [5,10,20,63]:
    for col in ['SEQ3','SEQ5','SEQ3_12','SEQE3','SEQ5_12','SEQ5_12_noup']:
        r=collect(col,col,1,H,'fixed'); t=table(r,col); t['H']=H; t['side']='long'; out.append(t); r.to_pickle(f'entries_{col}_long_H{H}.pkl')
    r=collect('SSEQ5_12','SSEQ5_12',-1,H,'fixed'); t=table(r,'SSEQ5_12'); t['H']=H; t['side']='short'; out.append(t)
fx=pd.concat(out,ignore_index=True); fx.to_csv('seq_fixed_hold_results.csv',index=False)
print('=== SEQUENCED GATES, FIXED HOLDS (gross, underlying) ==='); print(fx[fx['split'].isin(['train','check'])].round(4).to_string())
print('=== by year, SEQ5_12 ==='); print(fx[(fx['cond']=='SEQ5_12')&(~fx['split'].isin(['train','check']))].round(4).to_string())
# rule exits on each sequenced gate
variants={'weekly_H5_wkstop_emtgt':dict(H=5,stop_kind='wk',target_em=True),'weekly_H5_daystop_emtgt':dict(H=5,stop_kind='day',target_em=True),
 'swing_H20_wkstop_emtgt':dict(H=20,stop_kind='wk',target_em=True),'swing_H20_wkstop_emtgt_stall3':dict(H=20,stop_kind='wk',target_em=True,stall=True),
 'swing_H20_wkstop_emtgt_rsi':dict(H=20,stop_kind='wk',target_em=True,rsi_exit=True),'swing_H20_wkstop_notgt':dict(H=20,stop_kind='wk',target_em=False),
 'swing_H20_fixed345_emtgt':dict(H=20,fixed_stop=0.0345,target_em=True),'swing_H20_daystop_emtgt':dict(H=20,stop_kind='day',target_em=True),
 'swing_H20_nostop_notgt':dict(H=20,stop_kind=None,target_em=False),'leaps_H63_fixed8_notgt':dict(H=63,fixed_stop=0.08,target_em=False),'leaps_H63_nostop_notgt':dict(H=63,stop_kind=None,target_em=False)}
rows=[]; whys=[]
for col in ['SEQ5_12','SEQ3','SEQE3']:
    for vname,kw in variants.items():
        for cname in [col,'ALL']:
            if cname=='ALL':
                for s in U: F[s]['ALL']=True
            r=collect(cname,cname,1,mode='rules',**kw); t=table(r,cname); t['variant']=vname; t['gate']=col; rows.append(t)
            w=r.groupby(['split','why'])['ret'].agg(['count','mean']).reset_index(); w['variant']=vname; w['cond']=cname; w['gate']=col; whys.append(w)
            if cname==col and vname=='swing_H20_wkstop_emtgt': r.to_pickle(f'entries_{col}_rules_swing.pkl'); print(col,'stop distance (wk low) median',r['stop_dist'].median(),'q25/q75',r['stop_dist'].quantile([.25,.75]).values,'EM median',r['em'].median())
        if col!='SEQ5_12': break   # ALL baseline once
rl=pd.concat(rows,ignore_index=True); rl.to_csv('seq_rule_exit_results.csv',index=False); pd.concat(whys).to_csv('seq_rule_exit_why.csv',index=False)
print('=== RULE EXITS on the sequenced gates ==='); print(rl[rl['split'].isin(['train','check'])].round(4).to_string())
# random baseline matched by symbol-year count for SEQ5_12 swing rules
g=pd.read_pickle('entries_SEQ5_12_rules_swing.pkl'); rng=np.random.default_rng(1); cnt=g.groupby(['symbol','year']).size(); sim={'train':[],'check':[]}
for rep in range(200):
    rows=[]
    for (s,y),k in cnt.items():
        f=F[s]; cand=np.where(f['year'].values==y)[0]; cand=cand[cand<len(f)-21]; idx=np.sort(rng.choice(cand,size=min(k,len(cand)),replace=False))
        r=simulate(bars[s],f,idx,1,20,stop_kind='wk',target_em=True); r['split']=split_of(y); rows.append(r)
    r=pd.concat(rows)
    for sp in ['train','check']: sim[sp].append(r.loc[r['split']==sp,'ret'].mean())
for sp in ['train','check']:
    gm=g.loc[g['split']==sp,'ret'].mean(); sm=np.array(sim[sp]); print(f'RANDOM BASELINE (count-matched by symbol-year, swing rules) {sp}: gate mean {gm:.4f} random mean {sm.mean():.4f} sd {sm.std():.4f} p(random>=gate) {(sm>=gm).mean():.3f}')
# add the seq columns to the panel for the logistic regression
pan=pd.read_pickle('panel.pkl'); add=pd.concat([F[s][['B2_r5','B2_r3','SEQ5_12','SEQ3']].reset_index().rename(columns={'index':'date'}).assign(symbol=s) for s in U])
pan=pan.merge(add,on=['symbol','date'],how='left'); pan.to_pickle('panel.pkl'); print('done')
