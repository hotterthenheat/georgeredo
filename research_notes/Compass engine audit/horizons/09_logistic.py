"""No invented weights: logistic regression of the forward-return outcome on the booleans, fitted 2022-2024, scored
2025-2026 against the strict AND gate at the same selectivity (the top-probability name-days, as many as the gate took)."""
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
pd.set_option('display.width',250)
p=pd.read_pickle('panel.pkl'); p=p[p['year']>=2022].dropna(subset=['fwd10','fwd5','fwd20']).copy()
for c in ['B1','B2','B3','B1_daily','B2_ema','B3_12','B3_range']: p[c]=p[c].astype(int)
p['rvol_c']=np.log(p['rvol'].clip(0.1,10)).fillna(0); p['ote']=p['up_r_close'].fillna(-1); p['rsi_c']=(p['rsi14'].fillna(50)-50)/20
tr=p[p['year']<=2024]; ch=p[p['year']>=2025]
for H in [5,10,20]:
    y=f'fwd{H}'
    for feats,name in [(['B1','B2','B3'],'3 booleans'),(['B1','B2','B3','B1_daily','B2_ema','B3_12','B3_range'],'7 booleans'),(['B1','B2','B3','rvol_c','ote','rsi_c'],'booleans + continuous')]:
        m=LogisticRegression(C=1.0,max_iter=1000).fit(tr[feats].values,(tr[y]>0).astype(int))
        coef=dict(zip(feats,m.coef_[0].round(3)))
        gate_tr=tr['B1'].astype(bool)&tr['B2'].astype(bool)&tr['B3'].astype(bool); gate_ch=ch['B1'].astype(bool)&ch['B2'].astype(bool)&ch['B3'].astype(bool)
        pr=m.predict_proba(ch[feats].values)[:,1]; k=int(gate_ch.sum()); top=np.argsort(-pr)[:k]
        prt=m.predict_proba(tr[feats].values)[:,1]; kt=int(gate_tr.sum()); topt=np.argsort(-prt)[:kt]
        print(f'H={H} {name}: coef={coef} | train: gate N={kt} mean={tr.loc[gate_tr,y].mean():.4f} hit={(tr.loc[gate_tr,y]>0).mean():.3f}; logit-top{kt} mean={tr[y].values[topt].mean():.4f} hit={(tr[y].values[topt]>0).mean():.3f}'
              f' | CHECK: gate N={k} mean={ch.loc[gate_ch,y].mean():.4f} hit={(ch.loc[gate_ch,y]>0).mean():.3f}; logit-top{k} mean={ch[y].values[top].mean():.4f} hit={(ch[y].values[top]>0).mean():.3f}; all-days mean={ch[y].mean():.4f} hit={(ch[y]>0).mean():.3f}')
# AUC-type check: does any boolean or the logit rank name-days at all, out of sample?
from sklearn.metrics import roc_auc_score
for H in [5,10,20]:
    y=(ch[f'fwd{H}']>0).astype(int)
    m=LogisticRegression(max_iter=1000).fit(tr[['B1','B2','B3']].values,(tr[f'fwd{H}']>0).astype(int))
    print(f'H={H} out-of-sample AUC: logit(3 bools)={roc_auc_score(y,m.predict_proba(ch[["B1","B2","B3"]].values)[:,1]):.3f} B1={roc_auc_score(y,ch["B1"]):.3f} B2={roc_auc_score(y,ch["B2"]):.3f} B3={roc_auc_score(y,ch["B3"]):.3f} gate={roc_auc_score(y,(ch.B1&ch.B2&ch.B3)):.3f}')
