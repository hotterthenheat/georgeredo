"""Q3: dealer-sign tests. UW daily greek-exposure (book-level gamma/delta/charm/vanna, UW's sign: calls +, puts -,
= the spec's 'raw OI sum') on date D against the NEXT session's open-to-close return (all tickers, cross-section) and,
for SPY/QQQ/IWM, the next session's first-hour and last-hour drift from 1-minute bars. 'Negated' (customer-hedged dealer
sign) is the same test with the sign flipped, so one quintile/sign test answers both. Also the regime claim: does the
sign/size of GEX_book predict a smaller realized range and negative 5-minute autocorrelation the next session?
One year of data: 2025-10-15 -> 2026-10-13; first half (to 2026-04-14) is the discovery half, second half the check."""
import sys, os, glob, numpy as np, polars as pl, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
out=open(os.path.join(C.HERE,'q3_results.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n')
L=C.LAKE+'/unusualwhales/'
g=pl.scan_parquet(L+'greek-exposure.part0*.parquet').collect()
for c in ['call_gamma','put_gamma','call_delta','put_delta','call_charm','put_charm','call_vanna','put_vanna']:
    g=g.with_columns(pl.col(c).cast(pl.Float64,strict=False))
g=g.with_columns([(pl.col('call_gamma')+pl.col('put_gamma')).alias('GEX'),(pl.col('call_delta')+pl.col('put_delta')).alias('DEX'),
                  (pl.col('call_vanna')+pl.col('put_vanna')).alias('VEX'),(pl.col('call_charm')+pl.col('put_charm')).alias('CEX'),
                  (pl.col('call_gamma').abs()+pl.col('put_gamma').abs()).alias('GROSS')]).select(['ticker','date','GEX','DEX','VEX','CEX','GROSS'])
o=pl.scan_parquet(L+'ohlc__1d.part0*.parquet').filter(pl.col('market_time')=='r').select(['ticker','date','open','close','high','low','volume']).collect()
for c in ['open','close','high','low','volume']: o=o.with_columns(pl.col(c).cast(pl.Float64,strict=False))
o=o.sort(['ticker','date']).with_columns([
    (pl.col('close')/pl.col('open')-1).shift(-1).over('ticker').alias('r_oc_next'),
    ((pl.col('high')-pl.col('low'))/pl.col('close')).shift(-1).over('ticker').alias('range_next'),
    pl.col('date').shift(-1).over('ticker').alias('date_next'),
    (pl.col('close')*pl.col('volume')).alias('dv')])
o=o.with_columns((pl.col('range_next')/((pl.col('high')-pl.col('low'))/pl.col('close')).rolling_mean(window_size=20,min_samples=10).over('ticker')).alias('range_rel_next'))
e=pl.read_parquet(L+'earnings.parquet').select(['ticker','report_date']).drop_nulls().unique()
e=e.with_columns(pl.col('report_date').str.to_date()).rename({'report_date':'rd'})
df=g.join(o,on=['ticker','date'],how='inner').drop_nulls(['r_oc_next','GEX','DEX','VEX','CEX'])
# drop ticker-days whose next session is within one calendar day of a report
df=df.with_columns(pl.col('date_next').str.to_date().alias('dn'))
near=df.select(['ticker','dn']).join(e,on='ticker',how='inner').filter((pl.col('dn')-pl.col('rd')).dt.total_days().abs()<=1).select(['ticker','dn']).unique().with_columns(pl.lit(True).alias('earn'))
df=df.join(near,on=['ticker','dn'],how='left').filter(pl.col('earn').is_null()).drop('earn')
df=df.filter((pl.col('close')>5)&(pl.col('dv')>5e6)&(pl.col('GROSS')>0)&(pl.col('r_oc_next').abs()<0.5))
# scale within ticker by the trailing 20-session median |X| (known at D)
df=df.sort(['ticker','date'])
for c in ['GEX','DEX','VEX','CEX']:
    df=df.with_columns((pl.col(c)/pl.col(c).abs().rolling_median(window_size=20,min_samples=10).shift(1).over('ticker')).alias(c+'_z'))
dates=sorted(df['date'].unique().to_list()); mid=dates[len(dates)//2]
P('cross-section rows',len(df),'tickers',df['ticker'].n_unique(),'sessions',len(dates),'first',dates[0],'last',dates[-1],'split at',mid)
P('(filters: close>$5, dollar volume>$5M, UW book non-empty, |next return|<50%, next session not within a day of an earnings report)')
def half(d): return 'H1' if d<mid else 'H2'
P('\n=== Cross-section: next-session open-to-close return by SIGN of the prior session book (daily equal-weight means, NW t-stat lag 5) ===')
P('metric | half | n_days | mean(X>0) bp | mean(X<0) bp | diff bp | NW t | share days X>0')
for c in ['GEX','DEX','VEX','CEX']:
    for h in ['H1','H2','ALL']:
        sub=df.filter(pl.col('date')<mid) if h=='H1' else (df.filter(pl.col('date')>=mid) if h=='H2' else df)
        daily=sub.group_by('date').agg([pl.col('r_oc_next').filter(pl.col(c)>0).mean().alias('pos'),pl.col('r_oc_next').filter(pl.col(c)<0).mean().alias('neg'),(pl.col(c)>0).mean().alias('sh')]).sort('date').drop_nulls()
        d=(daily['pos']-daily['neg']).to_numpy()*1e4; m,t,n=C.nw_tstat(d)
        P(f'{c:4s} | {h:3s} | {n:4d} | {daily["pos"].mean()*1e4:+7.2f} | {daily["neg"].mean()*1e4:+7.2f} | {m:+7.2f} | {t:+5.2f} | {daily["sh"].mean():.2f}')
P('\n=== Cross-section: quintiles of X scaled by the name\'s trailing-20-session median |X| (Q5 most positive); Q5-Q1 next-session o-c return ===')
P('metric | half | n_days | Q1 bp | Q3 bp | Q5 bp | Q5-Q1 bp | NW t')
for c in ['GEX','DEX','VEX','CEX']:
    z=c+'_z'
    for h in ['H1','H2','ALL']:
        sub=df.filter(pl.col('date')<mid) if h=='H1' else (df.filter(pl.col('date')>=mid) if h=='H2' else df)
        sub=sub.drop_nulls([z]).with_columns(((pl.col(z).rank('ordinal').over('date')-1)*5//pl.col(z).count().over('date')).alias('q'))
        daily=sub.group_by(['date','q']).agg(pl.col('r_oc_next').mean()).pivot(on='q',index='date',values='r_oc_next').sort('date').drop_nulls()
        if len(daily)<10: continue
        d=(daily['4']-daily['0']).to_numpy()*1e4; m,t,n=C.nw_tstat(d)
        P(f'{c:4s} | {h:3s} | {n:4d} | {daily["0"].mean()*1e4:+6.2f} | {daily["2"].mean()*1e4:+6.2f} | {daily["4"].mean()*1e4:+6.2f} | {m:+7.2f} | {t:+5.2f}')
P('\n=== Regime claim, cross-section: next-session realized range (H-L)/C by GEX sign and by GEX_z quintile ===')
for h in ['H1','H2','ALL']:
    sub=df.filter(pl.col('date')<mid) if h=='H1' else (df.filter(pl.col('date')>=mid) if h=='H2' else df)
    daily=sub.group_by('date').agg([pl.col('range_next').filter(pl.col('GEX')>0).mean().alias('pos'),pl.col('range_next').filter(pl.col('GEX')<0).mean().alias('neg')]).sort('date').drop_nulls()
    d=(daily['pos']-daily['neg']).to_numpy()*1e4; m,t,n=C.nw_tstat(d)
    sub2=sub.drop_nulls(['GEX_z']).with_columns(((pl.col('GEX_z').rank('ordinal').over('date')-1)*5//pl.col('GEX_z').count().over('date')).alias('q'))
    dq=sub2.group_by(['date','q']).agg(pl.col('range_next').mean()).pivot(on='q',index='date',values='range_next').sort('date').drop_nulls()
    d2=(dq['4']-dq['0']).to_numpy()*1e4; m2,t2,n2=C.nw_tstat(d2)
    dr=sub2.drop_nulls(['range_rel_next']).group_by(['date','q']).agg(pl.col('range_rel_next').mean()).pivot(on='q',index='date',values='range_rel_next').sort('date').drop_nulls()
    d3=(dr['4']-dr['0']).to_numpy(); m3,t3,n3=C.nw_tstat(d3)
    P(f'{h}: range next | GEX>0 {daily["pos"].mean()*1e4:.0f} bp vs GEX<0 {daily["neg"].mean()*1e4:.0f} bp, diff {m:+.0f} bp NW t {t:+.2f} (n_days {n}) | Q5-Q1 of GEX_z: {m2:+.0f} bp, NW t {t2:+.2f} | Q5-Q1 of GEX_z on range RELATIVE to the name\'s trailing-20 mean range: {m3:+.3f} (Q1 {dr["0"].mean():.3f}, Q5 {dr["4"].mean():.3f}), NW t {t3:+.2f}')
P('   NOTE: the sign split is confounded by name type (a name whose book is net-negative is usually a put-heavy, higher-vol name), so the quintile-of-z line is the one to read.')

# ---------- Time series for the three ETFs ----------
P('\n=== Time series, SPY / QQQ / IWM: next-session drifts (bp) on the prior session\'s book; n ~ 250 sessions each, one year ===')
T=C.SP+'/theta/data/underlying/'
def intraday(sym,d):
    f=T+sym+'/'+d+'.parquet'
    if not os.path.exists(f): return None
    b=pl.read_parquet(f).sort('timestamp').filter((pl.col('close')>0)&(pl.col('open')>0))
    if len(b)<300: return None   # half day or gaps
    m=(b['timestamp'].dt.hour().cast(pl.Int64)*60+b['timestamp'].dt.minute().cast(pl.Int64)-570).to_numpy(); c=b['close'].to_numpy(); op=b['open'].to_numpy()
    def at(mm):   # price at minute boundary mm = close of bar stamped mm-1
        i=np.searchsorted(m,mm-1); return c[min(i,len(c)-1)]
    if not np.all(np.isfinite(c)) or not np.isfinite(op[0]): return None
    o0=op[0]; p1030=at(60); p1500=at(330); p1600=at(390); 
    # 5-minute returns lag-1 autocorrelation
    idx=np.searchsorted(m,np.arange(0,391,5)); idx=np.clip(idx-1,0,len(c)-1); p5=c[idx]; r5=np.diff(np.log(p5))
    ac=np.corrcoef(r5[:-1],r5[1:])[0,1] if len(r5)>10 else np.nan
    return dict(r_fh=p1030/o0-1, r_lh=p1600/p1500-1, r_oc=p1600/o0-1, ac5=ac, rv=np.sqrt(np.sum(np.diff(np.log(c))**2)), rng=(c.max()-c.min())/o0)
for sym in ['SPY','QQQ','IWM']:
    gs=g.filter(pl.col('ticker')==sym).sort('date')
    recs=[]
    ds=gs['date'].to_list()
    for i,d in enumerate(ds[:-1]):
        nd=ds[i+1]; x=intraday(sym,nd)
        if x is None: continue
        recs.append(dict(date=d,**{k:gs[k][i] for k in ['GEX','DEX','VEX','CEX']},**x))
    R=pl.DataFrame(recs).sort('date')
    for c in ['GEX','DEX','VEX','CEX']:
        R=R.with_columns((pl.col(c)/pl.col(c).abs().rolling_median(window_size=20,min_samples=10).shift(1)).alias(c+'_z'))
    P(f'\n{sym}: sessions with a next-session full day of bars: {len(R)}; share of sessions GEX_book>0: {(R["GEX"]>0).mean():.2f}, DEX>0: {(R["DEX"]>0).mean():.2f}, VEX>0: {(R["VEX"]>0).mean():.2f}, CEX>0: {(R["CEX"]>0).mean():.2f}')
    P('metric | half | n | corr(z, r_fh) | corr(z, r_lh) | corr(z, r_oc) | mean r_oc X>0 bp | X<0 bp | NW t(diff) | hit rate sign(X)=sign(r_oc)')
    for c in ['GEX','DEX','VEX','CEX']:
        for h in ['H1','H2','ALL']:
            S=R.filter(pl.col('date')<mid) if h=='H1' else (R.filter(pl.col('date')>=mid) if h=='H2' else R)
            S=S.drop_nulls([c+'_z'])
            z=S[c+'_z'].to_numpy(); x=S[c].to_numpy()
            cf=[np.corrcoef(z,S[k].to_numpy())[0,1] for k in ['r_fh','r_lh','r_oc']]
            roc=S['r_oc'].to_numpy(); pos=roc[x>0]; neg=roc[x<0]
            # NW t of the difference via a regression-free approximation: t of sign-coded series
            sgn=np.sign(x); m_,t_,n_=C.nw_tstat(sgn*roc)   # mean of sign*return = (pos-neg) weighted
            hit=np.mean(np.sign(roc)==sgn)
            P(f'{c:4s} | {h:3s} | {len(S):3d} | {cf[0]:+.3f} | {cf[1]:+.3f} | {cf[2]:+.3f} | {pos.mean()*1e4 if len(pos) else np.nan:+6.1f} | {neg.mean()*1e4 if len(neg) else np.nan:+6.1f} | {t_:+.2f} | {hit:.2f}')
    P(f'{sym} regime: next-session realized vol, range and 5-min autocorrelation by GEX_book sign and by GEX_z tercile')
    for h in ['H1','H2','ALL']:
        S=R.filter(pl.col('date')<mid) if h=='H1' else (R.filter(pl.col('date')>=mid) if h=='H2' else R)
        S=S.drop_nulls(['GEX_z']); z=S['GEX_z'].to_numpy(); x=S['GEX'].to_numpy()
        q=np.quantile(z,[1/3,2/3]); lo=z<=q[0]; hi=z>=q[1]
        for name,a,b in [('sign',x>0,x<0),('tercile',hi,lo)]:
            P(f'   {h} {name}: n+ {a.sum()} n- {b.sum()} | rv {S["rv"].to_numpy()[a].mean()*1e4:.0f} vs {S["rv"].to_numpy()[b].mean()*1e4:.0f} bp | range {S["rng"].to_numpy()[a].mean()*1e4:.0f} vs {S["rng"].to_numpy()[b].mean()*1e4:.0f} bp | ac5 {np.nanmean(S["ac5"].to_numpy()[a]):+.3f} vs {np.nanmean(S["ac5"].to_numpy()[b]):+.3f} | first-hour->rest-of-day corr {np.corrcoef(S["r_fh"].to_numpy()[a],(S["r_oc"].to_numpy()[a]-S["r_fh"].to_numpy()[a]))[0,1]:+.2f} vs {np.corrcoef(S["r_fh"].to_numpy()[b],(S["r_oc"].to_numpy()[b]-S["r_fh"].to_numpy()[b]))[0,1]:+.2f}')
    R.write_csv(os.path.join(C.HERE,f'q3_{sym}_series.csv'))
out.close()
