"""Q4b: the three books (0DTE / Near <=14 calendar days / Macro = all) on real full chains with open interest:
ThetaData bulk EOD files (every listed contract's closing NBBO and OI) for SPY, QQQ, IWM on 2026-10-06..10-12 (5 sessions,
all that exist on disk). Vols are inverted from the closing mid (bisection, r=0 q=0 to match UW's greek convention, and
r=4.15% q=0 as the house prices), tau = whole calendar days/365 (UW's clock; a contract expiring the same day is dead at the
close, so the "0DTE book" seen at the close is the NEXT session's expiry, stated). Walls, flip (Method A), king, pin per book;
the Macro book's net against UW's book-level greek-exposure for the same date (units: gamma x OI x 100)."""
import sys, os, glob, datetime as dt, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
out=open(os.path.join(C.HERE,'q4b_results.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n')
F=C.SP+'/lake/flat/'
days=sorted(os.path.basename(f)[:-8] for f in glob.glob(F+'option_eod/*.parquet'))
uw=pl.scan_parquet(C.LAKE+'/unusualwhales/greek-exposure.part0*.parquet').filter(pl.col('ticker').is_in(['SPY','QQQ','IWM'])).collect()
uw=uw.with_columns([pl.col('call_gamma').cast(pl.Float64),pl.col('put_gamma').cast(pl.Float64)])
# next-session dates from the SPY eod calendar
cal=sorted(C.spy_closes())
def methodA(Ks,G,S):
    best=None
    for i in range(len(Ks)-1):
        if G[i]*G[i+1]<0:
            Fp=Ks[i]+(Ks[i+1]-Ks[i])*G[i]/(G[i]-G[i+1])
            if best is None or abs(Fp-S)<abs(best-S): best=Fp
    return best
rows_out=[]
for d in days:
    eod=pl.scan_parquet(F+f'option_eod/{d}.parquet').filter(pl.col('root').is_in(['SPY','QQQ','IWM'])).select(['root','expiration','strike','right','bid','ask']).collect()
    oi=pl.scan_parquet(F+f'option_oi/{d}.parquet').filter(pl.col('root').is_in(['SPY','QQQ','IWM'])).select(['root','expiration','strike','right','open_interest']).collect()
    st=pl.read_parquet(F+f'stock_eod/{d}.parquet').filter(pl.col('root').is_in(['SPY','QQQ','IWM'])).select(['root','close'])
    j=eod.join(oi,on=['root','expiration','strike','right'],how='inner').join(st,on='root')
    j=j.with_columns([pl.col('strike').cast(pl.Float64),pl.col('bid').cast(pl.Float64),pl.col('ask').cast(pl.Float64),pl.col('close').cast(pl.Float64)])
    d0=dt.date.fromisoformat(d); nxt=cal[cal.index(d)+1] if d in cal and cal.index(d)+1<len(cal) else None
    for sym in ['SPY','QQQ','IWM']:
        x=j.filter((pl.col('root')==sym)&(pl.col('open_interest')>0)&(pl.col('bid')>0)&(pl.col('ask')>0))
        S=float(x['close'][0]); K=x['strike'].to_numpy(); call=(x['right']=='C').to_numpy(); mid=0.5*(x['bid']+x['ask']).to_numpy(); OI=x['open_interest'].to_numpy().astype(float)
        exp=np.array([dt.date(int(str(e)[:4]),int(str(e)[4:6]),int(str(e)[6:8])) for e in x['expiration'].to_list()])
        dte=np.array([(e-d0).days for e in exp]); keep=(dte>=1)&(np.abs(K/S-1)<0.25)
        K,call,mid,OI,dte,exp=K[keep],call[keep],mid[keep],OI[keep],dte[keep],exp[keep]; tau=dte/365
        res={}
        for conv,(r,q) in [('r0',(0,0)),('r415',(C.R_HOUSE,0))]:
            iv=C.iv_bisect(mid,S,K,tau,r,q,call); ok=np.isfinite(iv)
            g=np.where(ok,C.bs(S,K,tau,np.where(ok,iv,0.2),r,q,call)['gamma'],0.0)
            res[conv]=(np.where(call,1,-1)*g*OI*100, ok)
        gex,ok=res['r0']; gex415,_=res['r415']
        u=uw.filter((pl.col('ticker')==sym)&(pl.col('date')==d))
        unet=float(u['call_gamma'][0]+u['put_gamma'][0]) if len(u) else np.nan; ucall=float(u['call_gamma'][0]) if len(u) else np.nan; uput=float(u['put_gamma'][0]) if len(u) else np.nan
        P(f'\n{sym} {d}  S={S:.2f}  contracts with OI and a quote within 25% of spot: {len(K)} ({ok.mean():.3f} solvable at r=0); next session {nxt}')
        gross=np.abs(gex).sum(); ugross=abs(ucall)+abs(uput)
        P(f'   net/gross: mine {gex.sum()/gross:+.3f}, UW {unet/ugross:+.3f}; sign agrees: {np.sign(gex.sum())==np.sign(unet)}')
        P(f'   Macro net GEX (gamma x OI x 100): mine r=0 {gex.sum():,.0f} (calls {gex[call].sum():,.0f}, puts {gex[~call].sum():,.0f}) | mine r=4.15% {gex415.sum():,.0f} | UW greek-exposure {unet:,.0f} (calls {ucall:,.0f}, puts {uput:,.0f}) | $ per 1%: mine {gex.sum()*S*S/100/1e6:,.0f}M, UW {unet*S*S/100/1e6:,.0f}M')
        books={'0DTE(next session)':exp==dt.date.fromisoformat(nxt) if nxt else np.zeros(len(K),bool),'Near<=14d':dte<=14,'Macro':np.ones(len(K),bool)}
        for bn,sel in books.items():
            if sel.sum()<10: P(f'   {bn:18s}: no contracts'); continue
            Ks=np.unique(K[sel]); G=np.array([gex[sel&(K==k)].sum() for k in Ks]); Gc=np.array([gex[sel&(K==k)&call].sum() for k in Ks]); Gp=np.array([gex[sel&(K==k)&~call].sum() for k in Ks]); O=np.array([OI[sel&(K==k)].sum() for k in Ks])
            flip=methodA(Ks,G,S); cw=Ks[np.argmax(G)]; pw=Ks[np.argmin(G)]; king=Ks[np.argmax(np.abs(Gc)+np.abs(Gp))]; pin=Ks[np.argmax(O)]
            share_agree=np.sum(np.abs(G)[np.sign(G)==np.sign(G.sum())])/np.sum(np.abs(G))
            P(f'   {bn:18s}: n={sel.sum():5d} net {G.sum():>14,.0f} (${G.sum()*S*S/100/1e6:,.0f}M/1%) | flip A {flip if flip is None else round(flip,2)} ({"-" if flip is None else f"{(flip/S-1)*1e4:+.0f} bp"}) | call wall {cw:.0f} ({(cw/S-1)*1e4:+.0f} bp) put wall {pw:.0f} ({(pw/S-1)*1e4:+.0f} bp) | king {king:.0f} pin {pin:.0f} | strike-agreement share {share_agree:.2f}')
            rows_out.append((sym,d,bn,sel.sum(),G.sum(),flip,cw,pw,king,pin,S,share_agree))
with open(os.path.join(C.HERE,'q4b_books.csv'),'w') as fh:
    fh.write('sym,date,book,n,net_gex,flipA,call_wall,put_wall,king,pin,spot,strike_agreement_share\n')
    for r in rows_out: fh.write(','.join(str(v) for v in r)+'\n')
# summary: how often the three books' walls agree
import collections
agree=collections.Counter(); tot=0
byk={}
for r in rows_out: byk.setdefault((r[0],r[1]),{})[r[2]]=r
for k,v in byk.items():
    if len(v)<3: continue
    tot+=1; a,b,c=v['0DTE(next session)'],v['Near<=14d'],v['Macro']
    agree['cw 0DTE=Macro']+=a[6]==c[6]; agree['pw 0DTE=Macro']+=a[7]==c[7]; agree['cw Near=Macro']+=b[6]==c[6]; agree['pw Near=Macro']+=b[7]==c[7]; agree['king 0DTE=Macro']+=a[8]==c[8]
    agree['flip sign 0DTE=Macro']+= (a[5] is not None and c[5] is not None and np.sign(a[5]-a[10])==np.sign(c[5]-c[10]))
P(f'\nAcross {tot} name-days: '+', '.join(f'{k} {v}/{tot}' for k,v in agree.items()))
out.close()
