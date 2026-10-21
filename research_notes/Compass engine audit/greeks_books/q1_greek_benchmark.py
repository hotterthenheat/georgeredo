"""Q1: benchmark the Black-Scholes engine (Module 5) against the 68 UW SPY option-contract snapshots on disk.
Two stages: (A) given UW's own implied_volatility, which (r, q, tau, theta-divisor) convention reproduces UW's
delta/gamma/theta/vega/rho; (B) inverting the NBBO mid under r=0,q=0 vs r=4.15% (q=0 and q=1.3%) against UW's IV,
and the 'ITM calls > 3% from spot fall apart under r=0' claim. Spot = ThetaData SPY close on the snapshot date."""
import sys, os, gzip, json, glob, datetime as dt, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
out=open(os.path.join(C.HERE,'q1_results.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n')
spy=C.spy_closes()
files=sorted(glob.glob(C.SP+'/uw_chains/SPY/*.json.gz'))
rows=[]
for f in files:
    b=os.path.basename(f)[:-8]; d0=dt.date.fromisoformat(b[:10]); ex=dt.date.fromisoformat(b[11:])
    if b[:10] not in spy: P('no spot for',b); continue
    S=spy[b[:10]][3]
    for r in json.load(gzip.open(f)):
        root,exp2,cp,k=C.parse_osi(r['option_symbol'])
        bid=float(r['nbbo_bid'] or 'nan'); ask=float(r['nbbo_ask'] or 'nan'); iv=float(r['implied_volatility'] or 'nan')
        rows.append((b[:10],(ex-d0).days,S,k,cp=='C',bid,ask,iv,r['delta'],r['gamma'],r['theta'],r['vega'],r['rho'],r['open_interest'] or 0))
A=np.array(rows,dtype=object)
date=A[:,0].astype(str); dte=A[:,1].astype(float); S=A[:,2].astype(float); K=A[:,3].astype(float); call=A[:,4].astype(bool)
bid=A[:,5].astype(float); ask=A[:,6].astype(float); ivu=A[:,7].astype(float)
du=A[:,8].astype(float); gu=A[:,9].astype(float); tu=A[:,10].astype(float); vu=A[:,11].astype(float); ru=A[:,12].astype(float); oi=A[:,13].astype(float)
mid=0.5*(bid+ask); tau=dte/365.0
mny=K/S-1
P('N contracts',len(A),'snapshots',len(files),'dates',len(set(date)),'DTE values',sorted(set(dte.astype(int))))
P('DTE distribution: 15-30d:',int(((dte>=15)&(dte<=30)).sum()),' 31-90d:',int(((dte>=31)&(dte<=90)).sum()),' (no <=7, 8-14 or >90 DTE snapshots exist on disk)')
good=np.isfinite(ivu)&(ivu>0)&np.isfinite(du)
P('contracts with a UW IV and delta:',int(good.sum()))
def bucket(m):
    return np.select([m<-0.03,m<-0.01,m<=0.01,m<=0.03],['K<S-3%','S-3..-1%','ATM +-1%','S+1..3%'],'K>S+3%')
bk=bucket(mny); order=['K<S-3%','S-3..-1%','ATM +-1%','S+1..3%','K>S+3%']
dteb=np.where(dte<=30,'15-30d','31-90d')

# ---------- Stage A: greeks from UW's own IV under conventions ----------
P('\n=== Stage A: greeks from UW implied_volatility; which convention reproduces UW delta/gamma/theta/vega/rho ===')
def stageA(r,q,tau_,label,sel=good):
    g=C.bs(S[sel],K[sel],tau_[sel],ivu[sel],r,q,call[sel])
    e_d=g['delta']-du[sel]; e_g=g['gamma']-gu[sel]; e_v=g['vega']/100-vu[sel]
    rel_g=e_g/np.abs(gu[sel]); 
    th365=g['theta']/365-tu[sel]; th252=g['theta']/252-tu[sel]
    rho100=g['rho']/100-ru[sel]
    P(f'{label:38s} delta: med|err| {np.nanmedian(np.abs(e_d)):.4f} p90 {np.nanpercentile(np.abs(e_d),90):.4f} mean err {np.nanmean(e_d):+.4f}'
      f' | gamma med rel err {np.nanmedian(rel_g):+.3f} | vega/100 med|err| {np.nanmedian(np.abs(e_v)):.4f}'
      f' | theta/365 med|err| {np.nanmedian(np.abs(th365)):.4f} theta/252 {np.nanmedian(np.abs(th252)):.4f} | rho/100 med|err| {np.nanmedian(np.abs(rho100)):.4f}')
    return e_d
tau_cal=tau; tau_trd=np.round(dte*252/365)/252
for (r,q) in [(0,0),(C.R_HOUSE,0),(C.R_HOUSE,C.Q_SPY),(0.05,0),(0.0525,0)]:
    stageA(r,q,tau_cal,f'r={r:.4f} q={q:.3f} tau=days/365')
stageA(C.R_HOUSE,0,tau_trd,'r=0.0415 q=0 tau=trading days/252')
stageA(C.R_HOUSE,0,(dte+0.0)/365+ (0/365),'r=0.0415 q=0 tau=days/365 (same)')
# best r per snapshot (grid), q=0 and q=Q_SPY, by minimising delta RMSE over calls+puts
P('\nBest-fit r by snapshot (grid 0..8% step 0.25%, delta RMSE, q=0 | q=1.3%):')
grid=np.arange(0,0.0801,0.0025); best=[]
for b in sorted(set(zip(date,dte.astype(int)))):
    sel=good&(date==b[0])&(dte==b[1])
    res=[]
    for q in (0,C.Q_SPY):
        rm=[np.sqrt(np.mean((C.bs(S[sel],K[sel],tau[sel],ivu[sel],r,q,call[sel])['delta']-du[sel])**2)) for r in grid]
        res.append((grid[int(np.argmin(rm))],min(rm)))
    best.append((b[0],b[1],res[0][0],res[0][1],res[1][0],res[1][1]))
best=np.array(best,dtype=object)
P('  median best r (q=0): %.4f  IQR %.4f..%.4f ; median best r (q=1.3%%): %.4f ; median delta RMSE at best (q=0) %.5f'%(
   np.median(best[:,2].astype(float)),np.percentile(best[:,2].astype(float),25),np.percentile(best[:,2].astype(float),75),np.median(best[:,4].astype(float)),np.median(best[:,3].astype(float))))
for row in best[::6]: P('  ',row[0],'DTE',row[1],'best r q=0: %.4f (rmse %.5f) | q=1.3%%: %.4f (rmse %.5f)'%(row[2],row[3],row[4],row[5]))
with open(os.path.join(C.HERE,'q1_best_r_by_snapshot.csv'),'w') as fh:
    fh.write('date,dte,best_r_q0,delta_rmse_q0,best_r_q013,delta_rmse_q013\n')
    for row in best: fh.write(','.join(map(str,row))+'\n')
# put-call checks at the same strike
P('\nSame-strike put/call checks (UW greeks):')
key={}
for i in range(len(A)):
    if good[i]: key.setdefault((date[i],dte[i],K[i]),{})['C' if call[i] else 'P']=i
dd=[];gr=[];ivd=[];mm=[]
for k,v in key.items():
    if 'C' in v and 'P' in v:
        c,p=v['C'],v['P']; dd.append(du[c]-du[p]); gr.append(gu[p]/gu[c] if gu[c]>0 else np.nan); ivd.append(ivu[p]-ivu[c]); mm.append(mny[c])
dd=np.array(dd);gr=np.array(gr);ivd=np.array(ivd);mm=np.array(mm)
P(f'  pairs {len(dd)} | delta_call - delta_put: median {np.median(dd):.4f} (e^-q*tau would be {np.exp(-C.Q_SPY*np.median(tau)):.4f} at q=1.3%, 1.0000 at q=0)')
for lo,hi in [(-0.05,-0.02),(-0.02,0.02),(0.02,0.05)]:
    s=(mm>lo)&(mm<=hi)
    P(f'  K/S-1 in ({lo:+.2f},{hi:+.2f}]: n {s.sum()}  put gamma / call gamma median {np.nanmedian(gr[s]):.3f}  IV_put-IV_call median {np.nanmedian(ivd[s]):+.4f}')

# ---------- Stage B: invert the NBBO mid ----------
P('\n=== Stage B: implied vol by bisection [0.01,3.00] x60 on the NBBO mid, tau=days/365 ===')
has=np.isfinite(mid)&(bid>0)&(ask>0)
intr=np.where(call,np.maximum(S-K,0),np.maximum(K-S,0))
conv={'r=0,q=0':(0,0),'r=4.15%,q=0':(C.R_HOUSE,0),'r=4.15%,q=1.3%':(C.R_HOUSE,C.Q_SPY)}
ivs={}
for name,(r,q) in conv.items():
    ivs[name]=C.iv_bisect(mid,S,K,tau,r,q,call)
skip=(mid-intr)<=0.01
P('spec skip rule (mid - intrinsic <= 0.01): skipped share of quoted contracts %.3f (n=%d of %d)'%(skip[has].mean(),skip[has].sum(),has.sum()))
P('\nBy right x moneyness x DTE: n | share unsolvable under each convention | median |IV - IV_uw| (vol pts) for solvable | median |delta(IV) - delta_uw|')
for cp,cpn in [(True,'CALL'),(False,'PUT')]:
    for db in ['15-30d','31-90d']:
        for b in order:
            s=has&(call==cp)&(bk==b)&(dteb==db)&good
            if s.sum()<20: continue
            line=f'{cpn} {db} {b:10s} n={s.sum():5d}'
            for name,(r,q) in conv.items():
                v=ivs[name][s]; ok=np.isfinite(v)
                dlt=C.bs(S[s][ok],K[s][ok],tau[s][ok],v[ok],r,q,call[s][ok])['delta']
                line+=f' | {name}: unsolv {1-ok.mean():.3f} ivErr {np.median(np.abs(v[ok]-ivu[s][ok]))*100:5.2f} dErr {np.median(np.abs(dlt-du[s][ok])):.4f}'
            P(line)
P('\n--- The claim: ITM calls more than 3% from spot (K < 0.97 S) ---')
s=has&call&(mny<-0.03)&good
for name,(r,q) in conv.items():
    v=ivs[name][s]; ok=np.isfinite(v)
    floor=np.where(call[s], S[s]*np.exp(-q*tau[s])-K[s]*np.exp(-r*tau[s]), K[s]*np.exp(-r*tau[s])-S[s]*np.exp(-q*tau[s]))
    below=(mid[s]<=floor)
    dlt=C.bs(S[s][ok],K[s][ok],tau[s][ok],v[ok],r,q,call[s][ok])['delta']
    de=dlt-du[s][ok]
    P(f'{name:16s} n={s.sum()}  mid<=floor (no vol): {below.mean():.3f}  unsolvable by bisection: {1-ok.mean():.3f}  '
      f'IV err: med {np.median(np.abs(v[ok]-ivu[s][ok]))*100:.2f} vol pts, p90 {np.percentile(np.abs(v[ok]-ivu[s][ok]),90)*100:.2f}  '
      f'delta err: med {np.median(np.abs(de)):.4f} p90 {np.percentile(np.abs(de),90):.4f}  within 0.5% rel delta: {np.mean(np.abs(de)/np.abs(du[s][ok])<0.005):.3f}')
# same for ITM puts > 3% (K > 1.03 S): the r term pushes the other way
P('--- Mirror: ITM puts more than 3% from spot (K > 1.03 S) ---')
s=has&(~call)&(mny>0.03)&good
for name,(r,q) in conv.items():
    v=ivs[name][s]; ok=np.isfinite(v)
    floor=K[s]*np.exp(-r*tau[s])-S[s]*np.exp(-q*tau[s]); below=(mid[s]<=floor)
    dlt=C.bs(S[s][ok],K[s][ok],tau[s][ok],v[ok],r,q,call[s][ok])['delta']; de=dlt-du[s][ok]
    P(f'{name:16s} n={s.sum()}  mid<=floor: {below.mean():.3f}  unsolvable: {1-ok.mean():.3f}  IV err med {np.median(np.abs(v[ok]-ivu[s][ok]))*100:.2f} p90 {np.percentile(np.abs(v[ok]-ivu[s][ok]),90)*100:.2f}  delta err med {np.median(np.abs(de)):.4f} p90 {np.percentile(np.abs(de),90):.4f}')
# OI-weighted gamma error contribution of ITM calls (does it matter for GEX?)
P('\n--- Does the ITM-call distortion matter for a book? share of OI and of |gamma x OI| in K<0.97S calls ---')
s=has&good
w=np.abs(gu*oi)
for b in order:
    t=s&(bk==b)
    P(f'  {b:10s} share of OI {oi[t].sum()/oi[s].sum():.3f}  share of |gamma*OI| {w[t].sum()/w[s].sum():.3f}  (calls only: OI {oi[t&call].sum()/oi[s].sum():.3f}, |gamma*OI| {w[t&call].sum()/w[s].sum():.3f})')
out.close()
