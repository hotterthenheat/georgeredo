"""Earnings gate. UW's earnings table: quarterly rows carry report_date and report_time (premarket/postmarket) from
1996. The earnings-day move = the session that first trades on the report: the report date for premarket, the next
session for postmarket (unknown time -> next session). Distribution of |close/close - 1| on those sessions vs all
other sessions, by name; the swing gate's EV with and without entries whose 20-session hold crosses an earnings session."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, polars as pl
from engine import load_bars
pd.set_option('display.width',250); pd.set_option('display.max_columns',40); pd.set_option('display.max_rows',400)
bars=load_bars(); U=sorted(bars)
e=pl.read_parquet('/home/user/georgeredo/data_lake/unusualwhales/earnings.parquet').filter(pl.col('ticker').is_in(U)&(pl.col('report_type')=='quarterly')&pl.col('report_date').is_not_null()).select(['ticker','report_date','report_time']).unique()
e=e.with_columns(pl.col('report_date').str.to_date()).to_pandas() if False else pd.DataFrame({c:e[c].to_list() for c in e.columns})
e['report_date']=pd.to_datetime(e['report_date'])
print('earnings rows (quarterly, dated) for the universe:',len(e),'date range',e['report_date'].min().date(),e['report_date'].max().date())
print(e.groupby('ticker')['report_date'].agg(['min','max','count']))
# earnings sessions per name
ES={}
for sym in U:
    idx=bars[sym].index; q=e[e['ticker']==sym]; days=set()
    for d,tm in zip(q['report_date'],q['report_time']):
        pos=idx.searchsorted(d)
        if pos>=len(idx): continue
        if tm=='premarket' and idx[pos]==d: days.add(idx[pos])
        elif idx[pos]==d: 
            if pos+1<len(idx): days.add(idx[pos+1])
        else: days.add(idx[pos])   # the report date was not a session: the next session
    ES[sym]=days
rows=[]
for sym in U:
    df=bars[sym]; r=(df['close']/df['close'].shift(1)-1).abs(); r=r[r.index>=pd.Timestamp('2020-01-01')]
    m=r.index.isin(ES[sym])
    if m.sum()==0: rows.append(dict(symbol=sym,n_earn=0)); continue
    rows.append(dict(symbol=sym,n_earn=int(m.sum()),n_other=int((~m).sum()),med_abs_earn=r[m].median(),med_abs_other=r[~m].median(),mean_abs_earn=r[m].mean(),mean_abs_other=r[~m].mean(),p90_earn=r[m].quantile(.9),p90_other=r[~m].quantile(.9),ratio_mean=r[m].mean()/r[~m].mean()))
t=pd.DataFrame(rows); print(t.round(4).to_string()); t.to_csv('earnings_moves.csv',index=False)
# gate entries crossing an earnings session
for fn,H,lab in [('entries_gate_long_rules_swing.pkl',20,'GATE swing rules (wk stop, EM target)'),('entries_gate_long_H20.pkl',20,'GATE swing fixed 20'),('entries_gate_long_H5.pkl',5,'GATE weekly fixed 5'),('entries_SEQ5_12_rules_swing.pkl',20,'SEQ5_12 swing rules'),('entries_SEQ5_12_long_H20.pkl',20,'SEQ5_12 swing fixed 20'),('entries_SEQ5_12_long_H5.pkl',5,'SEQ5_12 weekly fixed 5'),('entries_SEQ5_12_long_H63.pkl',63,'SEQ5_12 leaps fixed 63'),('entries_all_long_H10.pkl',10,'ALL days fixed 10')]:
    if not os.path.exists(fn): continue
    g=pd.read_pickle(fn); g=g[g['year']>=2022].copy()
    cross=[]
    for sym,t in zip(g['symbol'],g['t']):
        idx=bars[sym].index; win=set(idx[t+1:t+1+H]); cross.append(len(win&ES[sym])>0)
    g['cross']=cross
    for sp in ['train','check']:
        q=g[g['split']==sp]
        for c in [True,False]:
            x=q.loc[q['cross']==c,'ret']
            print(f'{lab} {sp} crosses_earnings={c}: N={len(x)} hit={(x>0).mean():.3f} mean={x.mean():.4f} med={x.median():.4f} sd={x.std():.4f}')
    g.to_pickle(fn.replace('.pkl','_earn.pkl'))
