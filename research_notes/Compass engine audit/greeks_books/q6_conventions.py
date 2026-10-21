"""Q6: units. (a) What /365.25 vs /252 vs /365 does to a charm figure; VEX/100. (b) Empirical: the sum of Black-Scholes
charm x OI x 100 and vanna x OI x 100 over the ThetaData full SPY/QQQ/IWM chains (closing mids, r=0, tau=days/365,
per-YEAR charm, per-1.00-vol vanna) against UW's book-level call_charm/put_charm/call_vanna/put_vanna for the same date,
to find what unit UW's figures are in (the house says: charm is a year's)."""
import sys, os, glob, datetime as dt, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
out=open(os.path.join(C.HERE,'q6_results.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n')
P('(a) arithmetic: CEX_day = CEX_year/365.25 is 1.450x smaller than CEX_year/252 (252/365.25 = 0.690); /365 differs from /365.25 by 0.07%.')
P('    VEX per 1 vol point = VEX per 1.00 vol / 100 (vanna is dDelta/dSigma with sigma in decimals). Both are pure unit choices; nothing predictive turns on them.')
F=C.SP+'/lake/flat/'
uw=pl.scan_parquet(C.LAKE+'/unusualwhales/greek-exposure.part0*.parquet').filter(pl.col('ticker').is_in(['SPY','QQQ','IWM'])).collect()
for c in ['call_charm','put_charm','call_vanna','put_vanna','call_gamma','put_gamma','call_delta','put_delta']: uw=uw.with_columns(pl.col(c).cast(pl.Float64))
P('\n(b) chain sums vs UW book-level fields (same date; mine from closing mids, r=0, q=0, tau=whole days/365, contracts with OI, a two-sided quote, within 25% of spot, DTE>=1):')
P('sym date | charm: mine per YEAR calls / puts | UW call_charm / put_charm | ratio UW/mine | vanna: mine per 1.00 vol calls / puts | UW | ratio | delta: mine calls/puts | UW')
for d in sorted(os.path.basename(f)[:-8] for f in glob.glob(F+'option_eod/*.parquet')):
    eod=pl.scan_parquet(F+f'option_eod/{d}.parquet').filter(pl.col('root').is_in(['SPY','QQQ','IWM'])).select(['root','expiration','strike','right','bid','ask']).collect()
    oi=pl.scan_parquet(F+f'option_oi/{d}.parquet').filter(pl.col('root').is_in(['SPY','QQQ','IWM'])).select(['root','expiration','strike','right','open_interest']).collect()
    st=pl.read_parquet(F+f'stock_eod/{d}.parquet').filter(pl.col('root').is_in(['SPY','QQQ','IWM'])).select(['root','close'])
    j=eod.join(oi,on=['root','expiration','strike','right']).join(st,on='root').with_columns([pl.col('strike').cast(pl.Float64),pl.col('bid').cast(pl.Float64),pl.col('ask').cast(pl.Float64),pl.col('close').cast(pl.Float64)])
    d0=dt.date.fromisoformat(d)
    for sym in ['SPY','QQQ','IWM']:
        x=j.filter((pl.col('root')==sym)&(pl.col('open_interest')>0)&(pl.col('bid')>0)&(pl.col('ask')>0))
        S=float(x['close'][0]); K=x['strike'].to_numpy(); call=(x['right']=='C').to_numpy(); mid=0.5*(x['bid']+x['ask']).to_numpy(); OI=x['open_interest'].to_numpy().astype(float)
        dte=np.array([(dt.date(int(str(e)[:4]),int(str(e)[4:6]),int(str(e)[6:8]))-d0).days for e in x['expiration'].to_list()])
        keep=(dte>=1)&(np.abs(K/S-1)<0.25); K,call,mid,OI,dte=K[keep],call[keep],mid[keep],OI[keep],dte[keep]; tau=dte/365
        iv=C.iv_bisect(mid,S,K,tau,0,0,call); ok=np.isfinite(iv); g=C.bs(S,K,tau,np.where(ok,iv,0.2),0,0,call)
        w=OI*100*ok
        ch_c=np.sum((g['charm']*w)[call]); ch_p=np.sum((g['charm']*w)[~call]); va_c=np.sum((g['vanna']*w)[call]); va_p=np.sum((g['vanna']*w)[~call]); de_c=np.sum((g['delta']*w)[call]); de_p=np.sum((g['delta']*w)[~call])
        u=uw.filter((pl.col('ticker')==sym)&(pl.col('date')==d))
        if not len(u): continue
        P(f'{sym} {d} | {ch_c:,.0f} / {ch_p:,.0f} | {u["call_charm"][0]:,.0f} / {u["put_charm"][0]:,.0f} | {u["call_charm"][0]/ch_c:+.2f} / {u["put_charm"][0]/ch_p:+.2f} | {va_c:,.0f} / {va_p:,.0f} | {u["call_vanna"][0]:,.0f} / {u["put_vanna"][0]:,.0f} | {u["call_vanna"][0]/va_c:+.2f} / {u["put_vanna"][0]/va_p:+.2f} | {de_c:,.0f} / {de_p:,.0f} | {u["call_delta"][0]:,.0f} / {u["put_delta"][0]:,.0f}')
P('\nA ratio near +-1 means UW\'s charm is per year and its vanna per 1.00 vol in Black-Scholes units (sign tells UW\'s sign convention); near 1/365 would mean per day; near 1/100 per vol point.')
out.close()
