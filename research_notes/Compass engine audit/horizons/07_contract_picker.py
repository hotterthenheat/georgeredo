"""Contract picker audit on the five ThetaData bulk option EOD days (2026-10-06..10-12): for the universe,
every contract's closing NBBO mid, BSM implied vol and delta (r = 4.0%, q = 0, ACT/365 calendar DTE to expiry),
spread/mid by delta band and DTE bucket, and the share of 8-28 DTE contracts at 0.40-0.55 delta with OI >= 500.
Calls only for the delta bands (the spec's long-call picker); the short side mirrors on puts.
"""
import polars as pl, numpy as np, json, glob, math
from scipy.stats import norm
from scipy.optimize import brentq
S='/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/lake/flat'
U=json.load(open('top20.json'))['top20_used']+['SPY','QQQ','IWM']
R=0.04
def bs_call(Sx,K,T,v): 
    if T<=0 or v<=0: return max(Sx-K,0.0)
    d1=(math.log(Sx/K)+(R+v*v/2)*T)/(v*math.sqrt(T)); d2=d1-v*math.sqrt(T)
    return Sx*norm.cdf(d1)-K*math.exp(-R*T)*norm.cdf(d2)
def iv_call(Sx,K,T,p):
    lo=max(Sx-K*math.exp(-R*T),0)
    if p<=lo+1e-6 or T<=0: return np.nan
    try: return brentq(lambda v: bs_call(Sx,K,T,v)-p,1e-3,5.0)
    except Exception: return np.nan
def delta_call(Sx,K,T,v):
    if not np.isfinite(v) or T<=0: return np.nan
    d1=(math.log(Sx/K)+(R+v*v/2)*T)/(v*math.sqrt(T)); return norm.cdf(d1)
rows=[]
for f in sorted(glob.glob(f'{S}/option_eod/*.parquet')):
    day=f.split('/')[-1][:10]; d=int(day.replace('-',''))
    st=pl.scan_parquet(f'{S}/stock_eod/{day}.parquet').filter(pl.col('root').is_in(U)).select(['root',pl.col('close').cast(pl.Float64).alias('S')]).collect()
    oi=pl.scan_parquet(f'{S}/option_oi/{day}.parquet').filter(pl.col('root').is_in(U)).select(['root','expiration',pl.col('strike').cast(pl.Float64),'right','open_interest']).collect()
    o=(pl.scan_parquet(f).filter(pl.col('root').is_in(U)&(pl.col('right')=='C')).select(['root','expiration','strike','right','bid','ask','volume']).collect()
       .with_columns(pl.col('bid').cast(pl.Float64),pl.col('ask').cast(pl.Float64),pl.col('strike').cast(pl.Float64)))
    o=o.join(oi,on=['root','expiration','strike','right'],how='left').join(st,on='root',how='left')
    o=o.with_columns(((pl.col('bid')+pl.col('ask'))/2).alias('mid'),(pl.col('ask')-pl.col('bid')).alias('spr'))
    exp=pl.col('expiration').cast(pl.Utf8).str.to_date('%Y%m%d'); today=pl.lit(day).str.to_date()
    o=o.with_columns((exp-today).dt.total_days().alias('dte')).filter((pl.col('dte')>=1)&(pl.col('bid')>0)&(pl.col('ask')>0)&(pl.col('S')>0)&(pl.col('mid')>0.02))
    o=o.filter((pl.col('strike')/pl.col('S')).is_between(0.5,1.6))   # a sane moneyness window
    Sv=o['S'].to_numpy(); Kv=o['strike'].to_numpy(); Tv=o['dte'].to_numpy()/365.0; Mv=o['mid'].to_numpy()
    iv=np.array([iv_call(s,k,t,m) for s,k,t,m in zip(Sv,Kv,Tv,Mv)]); dl=np.array([delta_call(s,k,t,v) for s,k,t,v in zip(Sv,Kv,Tv,iv)])
    o=o.with_columns(pl.Series('iv',iv),pl.Series('delta',dl),pl.lit(day).alias('day'))
    rows.append(o); print(day,o.height,flush=True)
a=pl.concat(rows).with_columns((pl.col('spr')/pl.col('mid')).alias('spr_mid'),(pl.col('spr')/pl.col('S')*100).alias('spr_bp_of_spot'))
a.write_parquet('contracts_calls_5days.parquet')
def dteb(c): return pl.when(c<=7).then(pl.lit('1-7')).when(c<=14).then(pl.lit('8-14')).when(c<=28).then(pl.lit('15-28')).when(c<=60).then(pl.lit('29-60')).when(c<=120).then(pl.lit('61-120')).when(c<=365).then(pl.lit('121-365')).otherwise(pl.lit('366+'))
def delb(c): return pl.when(c<0.2).then(pl.lit('<0.20')).when(c<0.35).then(pl.lit('0.20-0.35')).when(c<0.5).then(pl.lit('0.35-0.50')).when(c<0.6).then(pl.lit('0.50-0.60')).when(c<0.8).then(pl.lit('0.60-0.80')).otherwise(pl.lit('0.80+'))
a=a.with_columns(dteb(pl.col('dte')).alias('dteb'),delb(pl.col('delta')).alias('delb'),pl.when(pl.col('root').is_in(['SPY','QQQ','IWM','TLT','HYG','EWZ','IBIT'])).then(pl.lit('ETF')).otherwise(pl.lit('single')).alias('kind'))
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(20)
t1=a.filter(pl.col('delta').is_not_nan()).group_by(['kind','dteb','delb']).agg(pl.len().alias('n'),pl.col('spr_mid').median().alias('med_spr_mid'),pl.col('spr_mid').quantile(0.75).alias('q75_spr_mid'),pl.col('mid').median().alias('med_mid'),pl.col('open_interest').median().alias('med_oi'),(pl.col('open_interest')>=500).mean().alias('share_oi500')).sort(['kind','dteb','delb'])
print(t1); t1.write_csv('picker_spread_by_band.csv')
sw=a.filter((pl.col('dte')>=8)&(pl.col('dte')<=28))
t2=sw.group_by('root').agg(pl.len().alias('n_8_28'),((pl.col('delta')>=0.40)&(pl.col('delta')<=0.55)).sum().alias('n_delta_band'),((pl.col('delta')>=0.40)&(pl.col('delta')<=0.55)&(pl.col('open_interest')>=500)).sum().alias('n_band_oi500'),
   pl.col('spr_mid').filter((pl.col('delta')>=0.40)&(pl.col('delta')<=0.55)).median().alias('med_spr_mid_band'),pl.col('expiration').n_unique().alias('n_exp')).with_columns((pl.col('n_band_oi500')/pl.col('n_delta_band')).alias('share_oi500_in_band')).sort('root')
print(t2); t2.write_csv('picker_oi500_by_name.csv')
# per day per name: does at least one 0.40-0.55 call with OI>=500 exist in each 8-28 DTE expiry?
t3=sw.group_by(['root','day','expiration']).agg(((pl.col('delta')>=0.40)&(pl.col('delta')<=0.55)&(pl.col('open_interest')>=500)).any().alias('ok')).group_by('root').agg(pl.col('ok').mean().alias('share_expiries_with_pick'),pl.len().alias('name_day_expiries')).sort('root')
print(t3); t3.write_csv('picker_expiry_coverage.csv')
# weekly (4-7 DTE, 0.35-0.50) and LEAPS (>=90 DTE, 0.60-0.80) spreads
for lab,lo,hi,dlo,dhi in [('weekly 4-7 DTE 0.35-0.50',4,7,0.35,0.50),('swing 8-28 DTE 0.40-0.55',8,28,0.40,0.55),('leaps 90-400 DTE 0.60-0.80',90,400,0.60,0.80)]:
    q=a.filter((pl.col('dte')>=lo)&(pl.col('dte')<=hi)&(pl.col('delta')>=dlo)&(pl.col('delta')<=dhi))
    print(lab, q.group_by('kind').agg(pl.len().alias('n'),pl.col('spr_mid').median().alias('med_spr_mid'),pl.col('spr_mid').mean().alias('mean_spr_mid'),pl.col('spr_mid').quantile(0.9).alias('q90'),pl.col('mid').median().alias('med_mid'),(pl.col('open_interest')>=500).mean().alias('share_oi500')).sort('kind'))
