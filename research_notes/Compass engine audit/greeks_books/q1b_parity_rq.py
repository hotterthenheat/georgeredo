"""Q1b: what r and q does the SPY chain itself imply (put-call parity on NBBO mids), and which inversion convention
makes the same-strike call and put vols agree. No vendor greek is used as the benchmark here."""
import sys, os, gzip, json, glob, datetime as dt, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
out=open(os.path.join(C.HERE,'q1b_results.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n')
spy=C.spy_closes(); files=sorted(glob.glob(C.SP+'/uw_chains/SPY/*.json.gz'))
res=[]; gaps={k:[] for k in ['r=0,q=0','r=4.15%,q=0','r=4.15%,q=1.3%','r-q=forward,q=0']}
P('snapshot      DTE  S       implied r   implied q   n_pairs  | same-strike IV_call-IV_put median (vol pts) under: r=0,q=0 | r=4.15%,q=0 | r=4.15%,q=1.3% | r-q=fwd,q=0')
for f in files:
    b=os.path.basename(f)[:-8]; d0=dt.date.fromisoformat(b[:10]); ex=dt.date.fromisoformat(b[11:]); S=spy[b[:10]][3]; tau=(ex-d0).days/365
    rows={}
    for r in json.load(gzip.open(f)):
        _,_,cp,k=C.parse_osi(r['option_symbol']); bid=float(r['nbbo_bid'] or 'nan'); ask=float(r['nbbo_ask'] or 'nan')
        if not(bid>0 and ask>0): continue
        rows.setdefault(k,{})[cp]=0.5*(bid+ask)
    ks=np.array([k for k in rows if 'C' in rows[k] and 'P' in rows[k] and abs(k/S-1)<0.08]); 
    if len(ks)<8: continue
    cmp_=np.array([rows[k]['C']-rows[k]['P'] for k in ks])
    # C-P = S e^{-q tau} - K e^{-r tau}: least squares on K (weight the near-the-money)
    # the slope of C-P on K is ill-conditioned on closing NBBO mids (deep-ITM mids are wide); only the forward is
    # identifiable: F = K + (C-P) e^{r tau} near the money, so (r - q) = ln(F/S)/tau, and S is the 16:00 close while the
    # quotes stand at ~17:30 ET, so after-hours drift of 0.1-0.3% is the same size as (r-q)*tau -> report, do not trust.
    near=np.abs(ks/S-1)<0.015
    F=np.median(ks[near]+cmp_[near]*np.exp(C.R_HOUSE*tau)); r_imp=np.log(F/S)/tau; q_imp=np.nan
    line=f'{b[:10]}  {(ex-d0).days:3d}  {S:7.2f}  {r_imp:+.4f}    {q_imp:+.4f}    {len(ks):4d}    |'
    for name,(rr,qq) in [('r=0,q=0',(0,0)),('r=4.15%,q=0',(C.R_HOUSE,0)),('r=4.15%,q=1.3%',(C.R_HOUSE,C.Q_SPY)),('r-q=forward,q=0',(r_imp,0.0))]:
        ivc=C.iv_bisect(np.array([rows[k]['C'] for k in ks]),S,ks,tau,rr,qq,True); ivp=C.iv_bisect(np.array([rows[k]['P'] for k in ks]),S,ks,tau,rr,qq,False)
        g=(ivc-ivp); g=g[np.isfinite(g)]; gaps[name].append(np.median(g)*100); line+=f' {np.median(g)*100:+6.2f} |'
    res.append((b[:10],(ex-d0).days,S,r_imp,q_imp)); P(line)
res=np.array(res,dtype=object)
P('\nForward-implied (r-q) [unreliable, see comment]: median %.4f IQR %.4f..%.4f (n=%d snapshots)'%(
  np.median(res[:,3].astype(float)),np.percentile(res[:,3].astype(float),25),np.percentile(res[:,3].astype(float),75),len(res)))
for y in ['2023','2024','2025','2026']:
    s=np.array([d.startswith(y) for d in res[:,0]]); 
    if s.sum(): P(f'  {y}: forward-implied r-q median {np.median(res[s,3].astype(float)):.4f} (n={s.sum()})')
P('\nSame-strike signed IV_call - IV_put, median of snapshot medians (vol pts) and share of snapshots with the gap > 0: '+' | '.join(f'{k}: {np.median(v):+.2f} ({np.mean(np.array(v)>0):.2f})' for k,v in gaps.items()))
P('   median |gap|: '+' | '.join(f'{k}: {np.median(np.abs(v)):.2f}' for k,v in gaps.items()))
with open(os.path.join(C.HERE,'q1b_chain_implied_rq.csv'),'w') as fh:
    fh.write('date,dte,spot,implied_r,implied_q\n'); [fh.write(','.join(map(str,r))+'\n') for r in res]
out.close()
