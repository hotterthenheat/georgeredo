"""Q2: the 0DTE skip rule (mid - intrinsic <= 0.01). On every SPY same-day chain on disk (ThetaData 1-minute NBBO,
2022-11 -> 2026-10): among contracts within +-1% of spot, the share skipped by minute of day under thresholds
0.005 / 0.01 / 0.02, by right and moneyness band, and the share of the band's (unweighted, OI is not in these files)
Black-Scholes gamma that the rule throws away. Spot = the underlying 1-minute bar's close stamped the same minute."""
import sys, os, glob, numpy as np, polars as pl, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
T=C.SP+'/theta'
files=sorted(glob.glob(T+'/data_full/chains/SPY/*.parquet'))
THR=[0.005,0.01,0.02]
MB=list(range(0,390,30))   # minute buckets, m=0 is 09:30
bands=['ITM>0.5%','ATM+-0.5%','OTM>0.5%']
# accumulators: [bucket][right][band] -> counts
import collections
cnt=collections.defaultdict(float); skp={t:collections.defaultdict(float) for t in THR}; unsolv=collections.defaultdict(float)
gam_tot=collections.defaultdict(float); gam_skp={t:collections.defaultdict(float) for t in THR}
ndates=0; years=collections.Counter()
for f in files:
    d=os.path.basename(f)[:-8]
    uf=T+'/data/underlying/SPY/'+d+'.parquet'
    if not os.path.exists(uf): continue
    ch=pl.read_parquet(f).filter(pl.col('bid').is_not_null()&pl.col('ask').is_not_null()&(pl.col('ask')>0))
    u=pl.read_parquet(uf).select(['timestamp','close']).rename({'close':'S'})
    j=ch.join(u,on='timestamp',how='inner')
    j=j.with_columns(((pl.col('strike')/pl.col('S')-1).alias('mny')))
    j=j.filter(pl.col('mny').abs()<=0.01)
    if len(j)==0: continue
    ndates+=1; years[d[:4]]+=1
    m=(j['timestamp'].dt.hour().cast(pl.Int64)*60+j['timestamp'].dt.minute().cast(pl.Int64)-570).to_numpy()
    K=j['strike'].to_numpy(); S=j['S'].to_numpy(); call=(j['right']=='CALL').to_numpy(); mid=j['mid'].to_numpy(); mny=j['mny'].to_numpy()
    intr=np.where(call,np.maximum(S-K,0),np.maximum(K-S,0)); ext=mid-intr
    tau=np.maximum((390-m),0.5)/(365*24*60)
    iv=C.iv_bisect(mid,S,K,tau,0,0,call); g=C.bs(S,K,tau,np.where(np.isfinite(iv),iv,0.2),0,0,call)['gamma']; g=np.where(np.isfinite(iv),g,0.0)
    band=np.select([(call&(mny<-0.005))|((~call)&(mny>0.005)), np.abs(mny)<=0.005],[0,1],2)
    b=np.minimum(m//30,12)
    for bi in range(13):
        for ri in (0,1):
            for ba in range(3):
                s=(b==bi)&(call==bool(ri))&(band==ba)
                if not s.any(): continue
                k=(bi,ri,ba); cnt[k]+=s.sum(); unsolv[k]+=(ext[s]<=0).sum(); gam_tot[k]+=g[s].sum()
                for t in THR: skp[t][k]+=(ext[s]<=t).sum(); gam_skp[t][k]+=g[s][ext[s]<=t].sum()
out=open(os.path.join(C.HERE,'q2_results.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n')
P('SPY same-day chains read:',ndates,'sessions',dict(sorted(years.items())),'| contracts within +-1% of spot, every minute')
P('\nShare of contracts within +-1% of spot SKIPPED by the rule mid-intrinsic<=thr, by 30-minute bucket (m=0 is 09:30):')
P('bucket   | n (k) | mid<=intr | thr .005 | thr .01 | thr .02 | gamma share lost @.005 | @.01 | @.02')
def row(keys,label):
    n=sum(cnt[k] for k in keys); 
    if n==0: return
    u=sum(unsolv[k] for k in keys)/n; s=[sum(skp[t][k] for k in keys)/n for t in THR]
    gt=sum(gam_tot[k] for k in keys); gs=[sum(gam_skp[t][k] for k in keys)/gt if gt>0 else np.nan for t in THR]
    P(f'{label:9s}| {n/1000:6.0f} |   {u:.3f}   |  {s[0]:.3f}   |  {s[1]:.3f}  |  {s[2]:.3f}  |        {gs[0]:.3f}         | {gs[1]:.3f} | {gs[2]:.3f}')
for bi in range(13):
    row([(bi,r,b) for r in (0,1) for b in range(3)], f'{bi*30:3d}-{bi*30+29:3d}')
P('\nBy right x moneyness band, whole session:')
for ri,rn in ((1,'CALL'),(0,'PUT')):
    for ba in range(3): row([(bi,ri,ba) for bi in range(13)], f'{rn} {bands[ba]}')
P('\nThe strikes a trade would use (ATM +-0.5%), by bucket:')
for bi in range(13): row([(bi,r,1) for r in (0,1)], f'{bi*30:3d}-{bi*30+29:3d}')
P('\nITM>0.5% band only, by bucket (where the rule bites):')
for bi in range(13): row([(bi,r,0) for r in (0,1)], f'{bi*30:3d}-{bi*30+29:3d}')
out.close()
