"""Shared pieces for the Compass Modules 5/6 audit. Pure numpy; no network.
Conventions: tau in years; r, q continuous; sigma decimal. Greeks per one share of underlying,
per 1.00 of vol (vega, vanna, vomma) and per year (theta, charm) unless a function says otherwise."""
import numpy as np, datetime as dt, glob, os
from scipy.special import ndtr

SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
HERE = os.path.dirname(os.path.abspath(__file__))
LAKE = '/home/user/georgeredo/data_lake'
R_HOUSE = 0.0415   # the house's measured UW convention
Q_SPY = 0.013      # SPY trailing dividend yield, approximate (spec: 1.2–1.5%)

def npdf(x): return np.exp(-0.5*x*x)/np.sqrt(2*np.pi)

def bs(S, K, tau, sigma, r=0.0, q=0.0, call=True):
    """Price and greeks. Arrays broadcast. Returns dict."""
    S=np.asarray(S,float); K=np.asarray(K,float); tau=np.asarray(tau,float); sigma=np.asarray(sigma,float)
    call=np.asarray(call,bool)
    tau=np.maximum(tau,1e-12); sigma=np.maximum(sigma,1e-12)
    sq=np.sqrt(tau)
    d1=(np.log(S/K)+(r-q+0.5*sigma**2)*tau)/(sigma*sq); d2=d1-sigma*sq
    eq=np.exp(-q*tau); er=np.exp(-r*tau)
    Nd1=ndtr(d1); Nd2=ndtr(d2); nd1=npdf(d1)
    price=np.where(call, S*eq*Nd1-K*er*Nd2, K*er*ndtr(-d2)-S*eq*ndtr(-d1))
    delta=np.where(call, eq*Nd1, eq*(Nd1-1))
    gamma=eq*nd1/(S*sigma*sq)
    vega=S*eq*nd1*sq                      # per 1.00 vol
    theta=np.where(call,
        -S*eq*nd1*sigma/(2*sq) - r*K*er*Nd2 + q*S*eq*Nd1,
        -S*eq*nd1*sigma/(2*sq) + r*K*er*ndtr(-d2) - q*S*eq*ndtr(-d1))   # per year
    rho=np.where(call, K*tau*er*Nd2, -K*tau*er*ndtr(-d2))              # per 1.00 rate
    vanna=-eq*nd1*d2/sigma                                               # dDelta/dSigma per 1.00 vol
    vomma=vega*d1*d2/sigma
    # charm: dDelta/dt (per year, derivative w.r.t. calendar time t = -d/dtau)
    charm_c = q*eq*Nd1 - eq*nd1*(2*(r-q)*tau - d2*sigma*sq)/(2*tau*sigma*sq)
    charm_p = -q*eq*ndtr(-d1) - eq*nd1*(2*(r-q)*tau - d2*sigma*sq)/(2*tau*sigma*sq)
    charm=np.where(call,charm_c,charm_p)
    return dict(price=price,delta=delta,gamma=gamma,vega=vega,theta=theta,rho=rho,vanna=vanna,vomma=vomma,charm=charm,d1=d1,d2=d2)

def iv_bisect(target, S, K, tau, r=0.0, q=0.0, call=True, lo=0.01, hi=3.0, iters=60):
    """Spec's bisection on [lo,hi], `iters` iterations, vectorised. NaN where the target is outside the
    bracket's price range (mid <= floor or above the hi-vol price)."""
    target=np.asarray(target,float)
    shape=np.broadcast(target,S,K,tau).shape
    lo=np.full(shape,lo,float); hi=np.full(shape,hi,float)
    plo=bs(S,K,tau,lo,r,q,call)['price']; phi=bs(S,K,tau,hi,r,q,call)['price']
    ok=(target>plo)&(target<phi)
    for _ in range(iters):
        mid=0.5*(lo+hi); pm=bs(S,K,tau,mid,r,q,call)['price']
        up=pm<target; lo=np.where(up,mid,lo); hi=np.where(up,hi,mid)
    out=0.5*(lo+hi); out=np.where(ok,out,np.nan); return out

def uw_tau_days(date, expiry):
    """UW's clock for a later expiry: whole calendar days / 365."""
    return (expiry-date).days/365.0

def parse_osi(sym):
    # SPY231215P00400000
    root=sym[:-15]; d=sym[-15:-9]; cp=sym[-9]; k=int(sym[-8:])/1000.0
    return root, dt.date(2000+int(d[:2]),int(d[2:4]),int(d[4:6])), cp, k

def spy_closes():
    """SPY daily close/open/high/low from the ThetaData stock_eod lake (2012→2026). Cached CSV."""
    import polars as pl
    cache=os.path.join(HERE,'_spy_eod.csv')
    if os.path.exists(cache):
        return {r[0]:tuple(map(float,r[1:])) for r in (l.strip().split(',') for l in open(cache)) if r[0]!='date'}
    rows=[]
    for f in sorted(glob.glob(LAKE+'/thetadata/stock_eod/year=*/part-*.parquet')):
        d=pl.scan_parquet(f).filter(pl.col('symbol')=='SPY').select(['created','open','high','low','close']).collect()
        if len(d): rows+= [(str(c)[:10],o,h,l,cl) for c,o,h,l,cl in d.iter_rows()]
    rows.sort()
    with open(cache,'w') as fh:
        fh.write('date,open,high,low,close\n')
        for r in rows: fh.write(','.join(map(str,r))+'\n')
    return {r[0]:tuple(r[1:]) for r in rows}

def nw_tstat(x, lags=5):
    """Newey-West t-stat of the mean of a series x."""
    x=np.asarray(x,float); x=x[~np.isnan(x)]; n=len(x)
    if n<10: return np.nan, np.nan, n
    m=x.mean(); e=x-m; s=np.sum(e*e)
    for L in range(1,lags+1):
        w=1-L/(lags+1); s+=2*w*np.sum(e[L:]*e[:-L])
    se=np.sqrt(s)/n
    return m, m/se if se>0 else np.nan, n
