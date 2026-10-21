"""Option-level EV: a MODEL, not a backtest. Multi-day option price paths are not on disk (only 0DTE chains and five
October-2026 EOD files). Each gate entry's underlying path (daily closes, plus the entry open) is re-priced with
Black-Scholes at constant vol: the name's UW implied vol on the entry date where the UW iv-rank__1y table has it
(2025-10-14 -> 2026-10-13), else the name's median UW IV over that year (a stated constant). r = 4%, q = 0.
Contract: a call at the band's middle delta (weekly 0.425, swing 0.475, LEAPS 0.70), DTE 7 / 14 / 30 / 180 calendar
days at entry, strike solved from the delta. Fills: buy at mid x (1 + s/2), sell at mid x (1 - s/2), s = 3% (ETF),
8% (single name) of mid — the October-2026 EOD files say what s really is (07_contract_picker.py); fees $0.65 a
contract each way. Exits on the option: premium stop -20% (A+) / -17% (A), scale-outs, trail lock, RSI(14) exit,
the underlying level stop, time. One contract cannot be scaled: 25%/50% partials need 4 contracts (2 for 50%).
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd, polars as pl, json, math
from scipy.stats import norm
from engine import load_bars, features
pd.set_option('display.width',250); pd.set_option('display.max_columns',40); pd.set_option('display.max_rows',400)
R=0.04; FEE=0.65
ETF={'SPY','QQQ','IWM','TLT','HYG','EWZ','IBIT'}
bars=load_bars(); U=sorted(bars); F={s:features(bars[s]) for s in U}
iv=pl.read_parquet('/home/user/georgeredo/data_lake/unusualwhales/iv-rank__1y.parquet').filter(pl.col('ticker').is_in(U)).select(['ticker','date',pl.col('volatility').cast(pl.Float64)]).with_columns(pl.col('date').str.to_date())
ivp={ (r['ticker'],r['date']):r['volatility'] for r in iv.iter_rows(named=True)}
ivmed=iv.group_by('ticker').agg(pl.col('volatility').median()); IVMED={r['ticker']:r['volatility'] for r in ivmed.iter_rows(named=True)}
def vol_of(sym,date):
    v=ivp.get((sym,pd.Timestamp(date).date())); return v if v else IVMED[sym]
def bs(S,K,T,v,cp=1):
    if T<=1e-9: return max(cp*(S-K),0.0)
    d1=(math.log(S/K)+(R+v*v/2)*T)/(v*math.sqrt(T)); d2=d1-v*math.sqrt(T)
    return cp*(S*norm.cdf(cp*d1)-K*math.exp(-R*T)*norm.cdf(cp*d2))
def strike_for_delta(S,T,v,delta):
    # call delta N(d1)=delta -> K
    d1=norm.ppf(delta); return S*math.exp(-(d1*v*math.sqrt(T)-(R+v*v/2)*T))
def run(entries,H,dte,delta,spread,label,stop_pct=None,scale=None,trail=None,rsi_exit=False,level_stop=True,ncontracts=1,cp=1):
    """entries: DataFrame with symbol,t (signal index). cp=1 call (long), -1 put (short side)."""
    out=[]
    for sym,g in entries.groupby('symbol'):
        df=bars[sym]; f=F[sym]; o,h,l,c=df['open'].values,df['high'].values,df['low'].values,df['close'].values; rs=f['rsi14'].values
        sw=f['stop_wk'].values if cp==1 else f['stop_wk_s'].values; n=len(c); s=spread
        for t in g['t'].values:
            if t+H+1>=n: continue
            S0=o[t+1]; v=vol_of(sym,df.index[t]); T0=dte/365
            K=strike_for_delta(S0,T0,v,delta if cp==1 else 1-delta)
            if cp==-1: K=strike_for_delta(S0,T0,v,1-delta)   # put with |delta| = delta: N(d1)=1-delta
            mid0=bs(S0,K,T0,v,cp); 
            if mid0<0.05: continue
            px_in=mid0*(1+s/2)+FEE/100; stopU=sw[t]
            qty=ncontracts; rem=qty; pnl=0.0; peak=mid0; why='time'; locked=None; day=H
            for k in range(1,H+1):
                i=t+k; T=max(T0-k/365*(7/5),1e-6)   # calendar decay: 7 calendar days per 5 sessions
                # intraday level stop on the underlying -> option at the close of that day (daily data: fill at the day's close mid)
                m_close=bs(c[i],K,T,v,cp)
                m_sell=lambda m: m*(1-s/2)-FEE/100
                exit_all=False
                if level_stop and ((l[i]<=stopU) if cp==1 else (h[i]>=stopU)):
                    mS=bs(stopU,K,T,v,cp); pnl+=rem*(m_sell(mS)-px_in); rem=0; why='level'; day=k; break
                if stop_pct is not None and m_close<=mid0*(1-stop_pct):
                    pnl+=rem*(m_sell(m_close)-px_in); rem=0; why='prem_stop'; day=k; break
                if locked is not None and m_close<=locked:
                    pnl+=rem*(m_sell(m_close)-px_in); rem=0; why='trail'; day=k; break
                if scale:
                    for lvl,frac in scale:
                        if m_close>=mid0*(1+lvl) and rem>0:
                            q=int(round(qty*frac))
                            if q>0 and q<=rem and (sym,t,lvl) not in done:
                                pnl+=q*(m_sell(m_close)-px_in); rem-=q; done.add((sym,t,lvl))
                if trail is not None and m_close>=mid0*(1+trail[0]):
                    locked=max(locked or 0, mid0*(1+trail[0]-trail[1]))
                if rsi_exit and k>=2 and ((rs[i]<rs[i-1] and rs[i-1]>70) if cp==1 else (rs[i]>rs[i-1] and rs[i-1]<30)):
                    pnl+=rem*(m_sell(m_close)-px_in); rem=0; why='rsi'; day=k; break
                if rem==0: why='scaled_out'; day=k; break
            if rem>0:
                i=t+H; T=max(T0-H/365*(7/5),1e-6); m=bs(c[i],K,T,v,cp); pnl+=rem*(m_sell(m)-px_in)
            out.append(dict(symbol=sym,t=t,date=df.index[t],year=df.index[t].year,ret=pnl/(qty*px_in),pnl_usd=pnl*100,prem=mid0,K=K,S0=S0,iv=v,why=why,day=day))
    r=pd.DataFrame(out); r['label']=label; return r
done=set()
def summ(r):
    rows=[]
    for sp,yrs in [('train',(2022,2024)),('check',(2025,2026))]:
        q=r[(r['year']>=yrs[0])&(r['year']<=yrs[1])]
        if len(q)==0: continue
        x=q['ret'].values
        dd=q.groupby('date')['ret'].sum().sort_values(); wo5d=q.loc[~q['date'].isin(dd.index[-5:]),'ret'].mean() if len(dd)>5 else np.nan
        rows.append(dict(split=sp,N=len(x),hit=(x>0).mean(),mean=x.mean(),med=np.median(x),mean_wo5=np.sort(x)[:-5].mean() if len(x)>5 else np.nan,mean_wo5days=wo5d,t=x.mean()/x.std(ddof=1)*np.sqrt(len(x)) if len(x)>2 else np.nan,why=q['why'].value_counts().to_dict()))
    return rows
res=[]
# the hold never outlives the contract: sessions x 7/5 <= DTE - 1 calendar day
for horizon,H,dte,delta,efile in [('weekly_7dte',4,7,0.425,'entries_SEQ5_12_long_H5.pkl'),('weekly_10dte',5,10,0.425,'entries_SEQ5_12_long_H5.pkl'),('swing_14dte',8,14,0.475,'entries_SEQ5_12_long_H20.pkl'),('swing_21dte',12,21,0.475,'entries_SEQ5_12_long_H20.pkl'),('swing_30dte',20,30,0.475,'entries_SEQ5_12_long_H20.pkl'),('leaps_180dte',63,180,0.70,'entries_SEQ5_12_long_H63.pkl'),('GATEweekly_7dte',4,7,0.425,'entries_gate_long_H5.pkl'),('GATEswing_21dte',12,21,0.475,'entries_gate_long_H20.pkl')]:
    e=pd.read_pickle(efile); e=e[e['year']>=2022]
    e['spread']=e['symbol'].map(lambda s:0.03 if s in ETF else 0.08)
    configs={'hold_only':dict(level_stop=False),'level_stop':dict(),'level+prem20':dict(stop_pct=0.20),'level+prem17':dict(stop_pct=0.17),'prem20_only':dict(level_stop=False,stop_pct=0.20),
             'level+prem20+scale4':dict(stop_pct=0.20,scale=[(0.27,0.25),(0.50,0.50)],ncontracts=4),'level+prem20+scale2':dict(stop_pct=0.20,scale=[(0.50,0.50)],ncontracts=2),
             'level+prem20+trail':dict(stop_pct=0.20,trail=(0.26,0.04)),'level+prem20+rsi':dict(stop_pct=0.20,rsi_exit=True),'all_rules_4c':dict(stop_pct=0.20,scale=[(0.27,0.25),(0.50,0.50)],ncontracts=4,trail=(0.26,0.04),rsi_exit=True)}
    if horizon.startswith('GATE'): configs={'level_stop':dict(),'level+prem20':dict(stop_pct=0.20)}
    if horizon.startswith('leaps'): configs={'hold_only':dict(level_stop=False),'prem25_only':dict(level_stop=False,stop_pct=0.25),'prem25+scale3':dict(level_stop=False,stop_pct=0.25,scale=[(0.50,0.33),(1.00,0.33)],ncontracts=3)}
    for cname,kw in configs.items():
        done=set()
        parts=[]
        for sp,g in e.groupby('spread'):
            parts.append(run(g,H,dte,delta,sp,f'{horizon}/{cname}',**kw))
        r=pd.concat(parts); 
        for row in summ(r): row.update(horizon=horizon,config=cname,H=H,dte=dte,delta=delta); res.append(row)
        for row in summ(r): print(horizon,cname,row['split'],'N',row['N'],'hit %.3f mean %.4f med %.4f wo5 %.4f wo5days %.4f t %.2f'%(row['hit'],row['mean'],row['med'],row['mean_wo5'],row['mean_wo5days'],row['t']),row['why'],flush=True)
        if cname in ('level_stop','hold_only'): r.to_pickle(f'optmodel_{horizon}_{cname}.pkl')
pd.DataFrame(res).to_csv('option_model_results.csv',index=False)
# the random/unconditional baseline on the option model: ALL days, swing 14 DTE, level stop + prem20
e=pd.read_pickle('entries_all_long_H10.pkl'); e=e[e['year']>=2022].sample(frac=0.15,random_state=3)
e['spread']=e['symbol'].map(lambda s:0.03 if s in ETF else 0.08)
parts=[run(g,12,21,0.475,sp,'ALL/level+prem20',stop_pct=0.20) for sp,g in e.groupby('spread')]
r=pd.concat(parts); r.to_pickle('optmodel_ALL_swing21_level_prem20.pkl'); print('BASELINE all days (15% sample), swing 21DTE/12 sessions level+prem20:',[{k:(round(v,4) if isinstance(v,float) else v) for k,v in row.items() if k!='why'} for row in summ(r)])
# premium-stop mapping: the underlying move that takes a 0.475-delta call to -20% / -17%, by DTE, at the same day (no decay) and after 3 sessions
for dte in [7,14,30]:
    for v in [0.15,0.25,0.45]:
        S0=100; T0=dte/365; K=strike_for_delta(S0,T0,v,0.475); p0=bs(S0,K,T0,v)
        def move_for(loss,days):
            T=max(T0-days/365*7/5,1e-6); lo,hi=0.0,0.5
            for _ in range(60):
                m=(lo+hi)/2
                if bs(S0*(1-m),K,T,v)<=p0*(1-loss): hi=m
                else: lo=m
            return hi
        print(f'DTE {dte} IV {v}: premium {p0/S0*100:.2f}% of spot; -20% at day0 = {move_for(0.20,0)*100:.2f}% down, after 3 sessions {move_for(0.20,3)*100:.2f}%; -17%: day0 {move_for(0.17,0)*100:.2f}%, 3 sessions {move_for(0.17,3)*100:.2f}%; 3 sessions of pure decay = {(1-bs(S0,K,max(T0-3/365*7/5,1e-6),v)/p0)*100:.1f}%')
