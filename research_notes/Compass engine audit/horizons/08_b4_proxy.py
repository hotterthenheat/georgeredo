"""B4 (macro dealer book) is untestable before 2025-10-15 (no OI-by-strike history). Proxy where UW's daily
greek-exposure exists (2025-10-15 -> 2026-10-13): the book's net gamma sign (call_gamma + put_gamma, UW's sign) on
the signal date against the gate's and all-days' forward returns. This is the book SIGN, not the walls."""
import numpy as np, pandas as pd, polars as pl
pd.set_option('display.width',250)
p=pd.read_pickle('panel.pkl'); p=p[p['year']>=2025].copy()
g=pl.concat([pl.read_parquet(f'/home/user/georgeredo/data_lake/unusualwhales/greek-exposure.part0{i}.parquet') for i in (1,2)]).filter(pl.col('ticker').is_in(sorted(p['symbol'].unique())))
g=g.select(['ticker',pl.col('date').str.to_date(),(pl.col('call_gamma').cast(pl.Float64)+pl.col('put_gamma').cast(pl.Float64)).alias('net_gamma')])
gd=pd.DataFrame({c:g[c].to_list() for c in g.columns}); gd['date']=pd.to_datetime(gd['date']); gd=gd.rename(columns={'ticker':'symbol'})
m=p.merge(gd,on=['symbol','date'],how='inner'); m['pos_gamma']=m['net_gamma']>0
print('name-days with a book:',len(m),m['date'].min().date(),m['date'].max().date(),'positive-gamma share',m['pos_gamma'].mean().round(3))
gate=m['B1'].astype(bool)&m['B2'].astype(bool)&m['B3'].astype(bool); seq=m['SEQ5_12'].fillna(False).astype(bool) if 'SEQ5_12' in m else gate
for H in [5,10,20]:
    y=f'fwd{H}'
    for lab,q in [('ALL days',m),('GATE',m[gate]),('SEQ5_12',m[seq])]:
        for pg in [True,False]:
            x=q.loc[q['pos_gamma']==pg,y].dropna()
            print(f'H={H} {lab} pos_gamma={pg}: N={len(x)} mean={x.mean():.4f} hit={(x>0).mean():.3f}')
