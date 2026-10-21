"""Compass horizons audit: the four-boolean swing gate on daily bars (long side; the short side mirrored).
Every rule is stated here in code. Entry at the next session's open after a signal close.
Prices: ThetaData closes, unadjusted; splits detected (close/prev close within 4% of 1/k, k in 2,3,4,5,10,20,50,
and the open the same) and back-adjusted; volume multiplied by k.
"""
import numpy as np, pandas as pd, polars as pl, json, sys
SPLIT_K=[2,3,4,5,10,20,50]

def load_bars():
    b=pl.read_parquet('bars.parquet').sort(['symbol','date'])
    b=b.filter((pl.col('open')>0)&(pl.col('close')>0)&(pl.col('high')>0)&(pl.col('low')>0)&(pl.col('volume')>0))
    b=b.filter(~((pl.col('symbol')=='IBIT')&(pl.col('date')<pl.date(2024,1,11))))   # IBIT listed 2024-01-11; earlier rows are a ghost symbol
    out={}
    for sym,g in b.group_by('symbol',maintain_order=True):
        sym=sym[0]
        df=pd.DataFrame({c:g[c].to_numpy() for c in ['date','open','high','low','close','volume']})
        df['date']=pd.to_datetime(df['date'])
        df=df.set_index('date')
        # split back-adjust
        r=df['close']/df['close'].shift(1); ro=df['open']/df['close'].shift(1)
        f=np.ones(len(df))
        for i in range(1,len(df)):
            for k in SPLIT_K:
                if abs(r.iloc[i]*k-1)<0.04 and abs(ro.iloc[i]*k-1)<0.06:
                    f[:i]/=k
        for c in ['open','high','low','close']: df[c]=df[c]*f
        df['volume']=df['volume']/f
        out[sym]=df
    return out

def rsi(close,n=14):
    d=close.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    au=up.ewm(alpha=1/n,adjust=False).mean(); ad=dn.ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+au/ad.replace(0,np.nan))

def features(df):
    """All features are known at the close of day t."""
    c,h,l,o,v=df['close'],df['high'],df['low'],df['open'],df['volume']
    f=pd.DataFrame(index=df.index)
    f['ema21']=c.ewm(span=21,adjust=False).mean(); f['ema50']=c.ewm(span=50,adjust=False).mean(); f['sma200']=c.rolling(200).mean()
    tr=pd.concat([h-l,(h-c.shift(1)).abs(),(l-c.shift(1)).abs()],axis=1).max(axis=1)
    f['atr14']=tr.ewm(alpha=1/14,adjust=False).mean(); f['tr']=tr
    f['vol20']=v.shift(1).rolling(20).mean(); f['rvol']=v/f['vol20']
    f['rsi14']=rsi(c)
    lr=np.log(c).diff(); f['sig20']=lr.rolling(20).std()
    # weekly: completed weeks (W-FRI). weekly_ok[t] uses the last week that ENDED before t's week.
    wk=c.resample('W-FRI').last().dropna(); wema=wk.ewm(span=10,adjust=False).mean()
    wok=(wk>wema); wok.index=wok.index+pd.Timedelta(days=1)   # valid from the Saturday after the week closed
    f['wk_ok']=wok.reindex(f.index,method='ffill').fillna(False).astype(bool)
    wbad=(wk<wema); wbad.index=wbad.index+pd.Timedelta(days=1)
    f['wk_bad']=wbad.reindex(f.index,method='ffill').fillna(False).astype(bool)
    # the partial-week alternative: this week's running close vs the ema seeded on completed weeks
    f['wk_ok_partial']=(c>wema.reindex(f.index,method='ffill')).fillna(False)
    # impulse (doji-safe: closes, not wicks). Up-impulse: the highest close of the last 30 sessions and the lowest
    # close before it within the window; size >= 2 ATR; the high at least 2 sessions old (a pullback exists).
    L=30; n=len(c); cv=c.values; lv=l.values; hv=h.values; atr=f['atr14'].values
    up_r_close=np.full(n,np.nan); up_r_low=np.full(n,np.nan); up_ok=np.zeros(n,bool); imp_lo=np.full(n,np.nan); imp_hi=np.full(n,np.nan)
    dn_r_close=np.full(n,np.nan); dn_r_high=np.full(n,np.nan); dn_ok=np.zeros(n,bool)
    for t in range(L,n):
        w=cv[t-L:t+1]
        ih=int(np.argmax(w)); 
        if ih>=1:
            lo=w[:ih].min(); hi=w[ih]
            if hi-lo>=2*atr[t] and ih<=L-2:
                up_ok[t]=True; up_r_close[t]=(hi-cv[t])/(hi-lo); up_r_low[t]=(hi-lv[t])/(hi-lo); imp_lo[t]=lo; imp_hi[t]=hi
        il=int(np.argmin(w))
        if il>=1:
            hi=w[:il].max(); lo=w[il]
            if hi-lo>=2*atr[t] and il<=L-2:
                dn_ok[t]=True; dn_r_close[t]=(cv[t]-lo)/(hi-lo); dn_r_high[t]=(hv[t]-lo)/(hi-lo)
    f['up_ok']=up_ok; f['up_r_close']=up_r_close; f['up_r_low']=up_r_low; f['imp_lo']=imp_lo; f['imp_hi']=imp_hi
    f['dn_ok']=dn_ok; f['dn_r_close']=dn_r_close; f['dn_r_high']=dn_r_high
    # ---- the booleans, long side ----
    f['B1']=(c>f['ema21'])&(c>f['ema50'])&f['wk_ok']                       # trend: daily above 21/50 EMA, last completed week above its 10-week EMA
    f['B1_daily']=(c>f['ema21'])&(c>f['ema50'])                            # alt: daily only
    f['B1_slope']=(c>f['ema21'])&(f['ema21']>f['ema50'])&f['wk_ok']         # alt: EMA stack
    f['B1_200']=(c>f['sma200'])&(c>f['ema21'])&f['wk_ok']                   # alt: 200-day
    f['B1_partial']=(c>f['ema21'])&(c>f['ema50'])&f['wk_ok_partial']        # alt: this week's running close
    f['B2']=up_ok&(up_r_low>=0.62)&(up_r_close<=0.705)                       # OTE: the day's low reached 0.62 of the impulse, the close not below 0.705
    f['B2_ema']=(l<=f['ema21'])&(c>=f['ema21'])&(c.shift(1)>f['ema21'])      # alt: a touch of the 21-EMA and a close back above it
    f['B2_wide']=up_ok&(up_r_low>=0.50)&(up_r_close<=0.786)                  # alt: 0.5-0.786
    f['B2_close']=up_ok&(up_r_close>=0.62)&(up_r_close<=0.705)               # alt: the close itself inside the zone
    f['B3']=f['rvol']>=1.5                                                  # relative volume >= 1.5x the 20-day mean
    f['B3_12']=f['rvol']>=1.2
    f['B3_range']=tr>=1.5*f['atr14'].shift(1)                               # alt: range expansion
    f['B3_any']=f['B3']|f['B3_range']
    # ---- mirrored, short side ----
    f['S1']=(c<f['ema21'])&(c<f['ema50'])&f['wk_bad']
    f['S2']=dn_ok&(dn_r_high>=0.62)&(dn_r_close<=0.705)
    f['S3']=f['B3']
    f['stop_wk']=l.rolling(5).min()           # prior-week low (5 sessions up to and including t)
    f['stop_day']=l                           # prior-day low
    f['stop_wk_s']=h.rolling(5).max(); f['stop_day_s']=h
    f['year']=f.index.year
    return f

def simulate(df,f,idx,side,H,stop_kind='wk',target_em=True,stall=False,rsi_exit=False,fixed_stop=None):
    """One trade per signal index t: entry = open[t+1]; stop/target on intraday touch (gap -> fill at the open);
    stop first when both touch on one day; exit at the close of session t+H otherwise. Returns signed return (long = +)."""
    o,h,l,c=df['open'].values,df['high'].values,df['low'].values,df['close'].values
    rs=f['rsi14'].values; sig=f['sig20'].values
    sw=f['stop_wk'].values if side>0 else f['stop_wk_s'].values
    sd=f['stop_day'].values if side>0 else f['stop_day_s'].values
    n=len(c); out=[]
    for t in idx:
        if t+1>=n or t+H>=n: continue
        e=o[t+1]
        if not np.isfinite(e) or e<=0: continue
        if fixed_stop is not None: stop=e*(1-side*fixed_stop)
        elif stop_kind=='wk': stop=sw[t]
        elif stop_kind=='day': stop=sd[t]
        else: stop=None
        em=sig[t]*np.sqrt(H) if np.isfinite(sig[t]) else np.nan
        tgt=e*(1+side*em) if target_em and np.isfinite(em) else None
        ex=None; why='time'; day=H
        for k in range(1,H+1):
            i=t+k
            hit_stop=stop is not None and ((l[i]<=stop) if side>0 else (h[i]>=stop))
            hit_tgt=tgt is not None and ((h[i]>=tgt) if side>0 else (l[i]<=tgt))
            if hit_stop:
                ex=min(o[i],stop) if side>0 else max(o[i],stop); why='stop'; day=k; break
            if hit_tgt:
                ex=max(o[i],tgt) if side>0 else min(o[i],tgt); why='target'; day=k; break
            if stall and k==3 and side*(c[i]-e)<=0 and i+1<n:
                ex=o[i+1]; why='stall'; day=k+1; break
            if rsi_exit and k>=2 and ((rs[i]<rs[i-1] and rs[i-1]>70) if side>0 else (rs[i]>rs[i-1] and rs[i-1]<30)) and i+1<n:
                ex=o[i+1]; why='rsi'; day=k+1; break
        if ex is None: ex=c[t+H]
        out.append((t,e,ex,side*(ex/e-1),why,day,(stop/e-1)*side if stop is not None else np.nan,em))
    return pd.DataFrame(out,columns=['t','entry','exit','ret','why','days','stop_dist','em'])

def fixed_hold(df,idx,side,H):
    o,c=df['open'].values,df['close'].values; n=len(c)
    t=np.array([i for i in idx if i+H<n and i+1<n],dtype=int)
    if len(t)==0: return pd.DataFrame(columns=['t','ret'])
    return pd.DataFrame({'t':t,'ret':side*(c[t+H]/o[t+1]-1)})
