"""Q3b: the regime claim with a volatility control. A book that is unusually positive relative to its own history is also a
calm-market book (gamma is larger when vols are low), so 'high GEX -> smaller next-day range' may be 'calm -> calm'.
Here: next-session realized vol regressed on log trailing-20-session realized vol (HAR-style control) and GEX_z, with
Newey-West (lag 5) t-stats; and the next-session rv relative to the trailing mean by GEX_z tercile. Reads q3_<sym>_series.csv."""
import sys, os, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
out=open(os.path.join(C.HERE,'q3b_results.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n')
def ols_nw(y,X,lags=5):
    X=np.column_stack([np.ones(len(y)),X]); b=np.linalg.lstsq(X,y,rcond=None)[0]; e=y-X@b; n,k=X.shape
    S=(X*e[:,None]).T@(X*e[:,None])
    for L in range(1,lags+1):
        w=1-L/(lags+1); G=(X[L:]*e[L:,None]).T@(X[:-L]*e[:-L,None]); S+=w*(G+G.T)
    XtXi=np.linalg.inv(X.T@X); V=XtXi@S@XtXi; return b, b/np.sqrt(np.diag(V))
for sym in ['SPY','QQQ','IWM']:
    R=pl.read_csv(os.path.join(C.HERE,f'q3_{sym}_series.csv')).sort('date')
    rv=R['rv'].to_numpy(); z=R['GEX_z'].to_numpy(); ac=R['ac5'].to_numpy(); rng=R['rng'].to_numpy(); d=R['date'].to_list()
    trail=np.array([np.mean(rv[max(0,i-20):i]) if i>=10 else np.nan for i in range(len(rv))])   # rv of sessions up to the signal day
    # UW's 30-day implied vol on the signal day (volatility__realized.implied_volatility) as a second control
    ivt=pl.scan_parquet(C.LAKE+'/unusualwhales/volatility__realized.parquet').filter(pl.col('ticker')==sym).select(['date','implied_volatility']).collect()
    ivm={a:float(b) for a,b in ivt.iter_rows() if b is not None}
    iv=np.array([ivm.get(x,np.nan) for x in d])
    ok=np.isfinite(z)&np.isfinite(trail)&np.isfinite(rv)&np.isfinite(iv)&(iv>0)
    mid=d[len(d)//2]
    P(f'\n{sym}: n={ok.sum()} (split {mid})')
    for h,sel in [('H1',np.array([x<mid for x in d])&ok),('H2',np.array([x>=mid for x in d])&ok),('ALL',ok)]:
        y=np.log(rv[sel]); X=np.column_stack([np.log(trail[sel]),z[sel]])
        b,t=ols_nw(y,X); X3=np.column_stack([np.log(trail[sel]),np.log(iv[sel]),z[sel]]); b3,t3=ols_nw(y,X3)
        ya=ac[sel]; ba,ta=ols_nw(ya,X)
        rel=rv[sel]/trail[sel]; q=np.quantile(z[sel],[1/3,2/3]); lo=z[sel]<=q[0]; hi=z[sel]>=q[1]
        P(f'  {h}: log rv_next ~ log trail_rv + GEX_z: b(trail) {b[1]:+.3f} (t {t[1]:+.2f}), b(GEX_z) {b[2]:+.4f} (t {t[2]:+.2f}) [n={sel.sum()}] | rv_next/trail: top GEX_z tercile {np.mean(rel[hi]):.3f} vs bottom {np.mean(rel[lo]):.3f} | ac5 ~ trail + GEX_z: b(GEX_z) {ba[2]:+.4f} (t {ta[2]:+.2f}) | with UW 30d IV added: b(IV) {b3[2]:+.3f} (t {t3[2]:+.2f}), b(GEX_z) {b3[3]:+.4f} (t {t3[3]:+.2f})')
P('\nReading: b(GEX_z) is the change in log next-session realized vol per unit of GEX_z after the trailing-vol control; negative with |t|>2 in both halves would support "positive gamma dampens".')
out.close()
