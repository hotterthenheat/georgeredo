"""Q4: flips, walls, pin and king on the 68 UW SPY snapshots (one expiry per snapshot, two expiries per date, 34 dates).
GEX_strike with the spec's sign (calls +, puts -, gamma x OI x 100). Method A (linear zero crossing between neighbouring
strikes, nearest to spot, discard beyond 3%) vs Method B (net GEX re-priced on a 0.05% spot grid to +-4%, each contract's
UW vol held fixed, r=0 q=0 as UW's greeks stand, tau = days/365). Distance tiers in bps vs the strike spacing. Walls = max
positive / max negative GEX_strike; KING = max gross |call GEX|+|put GEX| strike; PIN = max open-interest strike (my
definitions, stated). Next-session touch test on the 34 dates' underlying 1-minute bars (small N)."""
import sys, os, gzip, json, glob, datetime as dt, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
out=open(os.path.join(C.HERE,'q4_results.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n')
spy=C.spy_closes(); dates_all=sorted(spy)
files=sorted(glob.glob(C.SP+'/uw_chains/SPY/*.json.gz'))
def methodA(Ks,G,S):
    best=None
    for i in range(len(Ks)-1):
        if G[i]*G[i+1]<0:
            F=Ks[i]+(Ks[i+1]-Ks[i])*G[i]/(G[i]-G[i+1])
            if best is None or abs(F-S)<abs(best-S): best=F
    return best
def methodB(S,K,call,iv,oi,tau,pct=0.04,step=0.0005):
    grid=S*(1+np.arange(-pct,pct+1e-9,step)); net=np.zeros_like(grid)
    for j,Sg in enumerate(grid):
        g=C.bs(Sg,K,tau,iv,0,0,call)['gamma']; net[j]=np.sum(np.where(call,1,-1)*g*oi*100)
    best=None
    for j in range(len(grid)-1):
        if net[j]*net[j+1]<0:
            F=grid[j]+(grid[j+1]-grid[j])*net[j]/(net[j]-net[j+1])
            if best is None or abs(F-S)<abs(best-S): best=F
    return best, net[len(grid)//2]
recs=[]
for f in files:
    b=os.path.basename(f)[:-8]; d0=b[:10]; ex=dt.date.fromisoformat(b[11:]); S=spy[d0][3]; dte=(ex-dt.date.fromisoformat(d0)).days; tau=dte/365
    rows=json.load(gzip.open(f))
    K=np.array([C.parse_osi(r['option_symbol'])[3] for r in rows]); call=np.array([C.parse_osi(r['option_symbol'])[2]=='C' for r in rows])
    iv=np.array([float(r['implied_volatility'] or 'nan') for r in rows]); gm=np.array([r['gamma'] if r['gamma'] is not None else np.nan for r in rows],float)
    oi=np.array([r['open_interest'] or 0 for r in rows],float)
    ok=np.isfinite(gm)&np.isfinite(iv)&(oi>0)
    if ok.sum()<10: print('skip (no usable greeks)',b,ok.sum()); continue
    K,call,iv,gm,oi=K[ok],call[ok],iv[ok],gm[ok],oi[ok]
    gex=np.where(call,1,-1)*gm*oi*100   # spec units: gamma x shares; x S^2/100 for $ per 1%
    Ks=np.unique(K); G=np.array([gex[K==k].sum() for k in Ks]); Gc=np.array([gex[(K==k)&call].sum() for k in Ks]); Gp=np.array([gex[(K==k)&~call].sum() for k in Ks]); OI=np.array([oi[K==k].sum() for k in Ks])
    FA=methodA(Ks,G,S); FB,net0=methodB(S,K,call,iv,oi,tau)
    cw=Ks[np.argmax(G)] if G.max()>0 else np.nan; pw=Ks[np.argmin(G)] if G.min()<0 else np.nan
    king=Ks[np.argmax(np.abs(Gc)+np.abs(Gp))]; pin=Ks[np.argmax(OI)]
    # nearest-spot strikes: spacing
    near=Ks[np.abs(Ks/S-1)<0.02]; spacing=np.median(np.diff(near)) if len(near)>2 else np.nan
    # next session bars
    i=dates_all.index(d0); nd=dates_all[i+1] if i+1<len(dates_all) else None
    nxt=None
    uf=C.SP+'/theta/data/underlying/SPY/'+(nd or 'x')+'.parquet'
    if nd and os.path.exists(uf):
        bb=pl.read_parquet(uf).filter(pl.col('close')>0); nxt=dict(hi=bb['high'].max(),lo=bb['low'].min(),op=bb['open'][0],cl=bb['close'][-1])
    recs.append(dict(date=d0,dte=dte,S=S,net=G.sum(),net_1pct=G.sum()*S*S/100,FA=FA,FB=FB,cw=cw,pw=pw,king=king,pin=pin,spacing=spacing,n_strikes=len(Ks),
                     Gc_cw=G.max(),Gp_pw=G.min(),nxt=nxt,Ks=Ks,G=G))
P('snapshots',len(recs),'dates',len(set(r['date'] for r in recs)))
R=recs
fa=np.array([r['FA'] if r['FA'] is not None else np.nan for r in R]); fb=np.array([r['FB'] if r['FB'] is not None else np.nan for r in R]); S=np.array([r['S'] for r in R])
P('\n=== Flip: Method A vs Method B ===')
P(f'Method A found a crossing: {np.isfinite(fa).sum()}/{len(R)}; within 3% of spot: {(np.abs(fa/S-1)<=0.03).sum()}; Method B found a zero on the +-4% grid: {np.isfinite(fb).sum()}/{len(R)}')
both=np.isfinite(fa)&np.isfinite(fb)
d=(fb-fa)[both]; bp=d/S[both]*1e4
P(f'both exist: {both.sum()}; |B-A| median ${np.median(np.abs(d)):.2f} ({np.median(np.abs(bp)):.0f} bp), p90 ${np.percentile(np.abs(d),90):.2f} ({np.percentile(np.abs(bp),90):.0f} bp); share |B-A| > 1 strike spacing: {np.mean(np.abs(d)>np.array([r["spacing"] for r in R])[both]):.2f}; share > 0.5%: {np.mean(np.abs(bp)>50):.2f}')
P(f'|F_A - S| in bps: median {np.nanmedian(np.abs(fa/S-1))*1e4:.0f}, p25 {np.nanpercentile(np.abs(fa/S-1),25)*1e4:.0f}, p75 {np.nanpercentile(np.abs(fa/S-1),75)*1e4:.0f}; same-sign of (F_A-S) and (F_B-S): {np.mean(np.sign(fa[both]-S[both])==np.sign(fb[both]-S[both])):.2f}')
sp=np.array([r['spacing'] for r in R]); P(f'strike spacing near spot: ${np.nanmedian(sp):.2f} = {np.nanmedian(sp/S)*1e4:.0f} bp of spot (range {np.nanmin(sp/S)*1e4:.0f}-{np.nanmax(sp/S)*1e4:.0f} bp); 1 bp of SPY = ${np.median(S)/1e4:.3f}')
tiers=[1,5,12,25]; dist=np.abs(fa/S-1)*1e4; dist=dist[np.isfinite(dist)]
P('Distance tiers of |F_A - S| (bps): '+', '.join(f'<= {t}: {np.mean(dist<=t):.2f}' for t in tiers)+f', > 25: {np.mean(dist>25):.2f}  (n={len(dist)})')
P('   a snapshot is end-of-day; intraday the flip moves with spot, so the tier a trader sees is the distance at the moment. 1 and 5 bp are 1/20 and 1/4 of one $1 strike step here.')
P('\n=== Walls, king, pin: 25-DTE vs 60-DTE expiry on the same date (both are "Macro" by the spec; how much the wall depends on the expiry picked) ===')
byd={}
for r in R: byd.setdefault(r['date'],[]).append(r)
same_cw=same_pw=same_king=same_pin=n=0; dcw=[];dpw=[]
for d0,rs in byd.items():
    if len(rs)!=2: continue
    a,b=sorted(rs,key=lambda r:r['dte']); n+=1
    same_cw+=a['cw']==b['cw']; same_pw+=a['pw']==b['pw']; same_king+=a['king']==b['king']; same_pin+=a['pin']==b['pin']; dcw.append(abs(a['cw']-b['cw'])); dpw.append(abs(a['pw']-b['pw']))
P(f'dates with both expiries: {n}; same call wall {same_cw}/{n}, same put wall {same_pw}/{n}, same king {same_king}/{n}, same pin {same_pin}/{n}; median |call wall diff| ${np.median(dcw):.0f}, |put wall diff| ${np.median(dpw):.0f}')
P(f'net GEX_book sign (spec sign, single expiry): positive in {np.mean([r["net"]>0 for r in R]):.2f} of snapshots; king == call wall in {np.mean([r["king"]==r["cw"] for r in R]):.2f}, king == put wall in {np.mean([r["king"]==r["pw"] for r in R]):.2f}, pin == king in {np.mean([r["pin"]==r["king"] for r in R]):.2f}')
P('   distances from spot (bps): call wall median %+.0f, put wall %+.0f, king %+.0f, pin %+.0f'%tuple(np.median([(r[k]/r['S']-1)*1e4 for r in R if np.isfinite(r[k])]) for k in ['cw','pw','king','pin']))
P('\n=== Next-session touch test (34 dates; the walls of the 25-DTE snapshot and of the 60-DTE snapshot counted separately; small N) ===')
P('A wall is "touched" if the next session\'s range reaches it; the control is the strike at the same distance on the OTHER side of spot (mirror) and the walls shifted by +-1 strike.')
def touched(level,nx): return (nx['lo']<=level<=nx['hi'])
for key,name in [('cw','call wall'),('pw','put wall'),('king','king'),('pin','pin')]:
    t=[];m=[];s1=[]
    for r in R:
        if r['nxt'] is None or not np.isfinite(r[key]): continue
        lv=r[key]; S0=r['S']; mirror=2*S0-lv
        t.append(touched(lv,r['nxt'])); m.append(touched(mirror,r['nxt'])); s1.append(np.mean([touched(lv+r['spacing'],r['nxt']),touched(lv-r['spacing'],r['nxt'])]))
    P(f'{name:9s}: n={len(t)} touched next session {np.mean(t):.2f} | mirror strike {np.mean(m):.2f} | +-1 strike {np.mean(s1):.2f} | median |level-S| {np.median([abs(r[key]-r["S"]) for r in R if r["nxt"] is not None and np.isfinite(r[key])]):.1f} $')
# "held": touched and closed back on the approach side
h=[]
for r in R:
    if r['nxt'] is None: continue
    for key in ['cw','pw']:
        lv=r[key]; nx=r['nxt']
        if not np.isfinite(lv) or not touched(lv,nx): continue
        above=r['S']<lv
        h.append((nx['cl']<lv) if above else (nx['cl']>lv))
P(f'of walls touched next session, closed back on the approach side ("held"): {np.mean(h):.2f} (n={len(h)}); a random level touched inside the day\'s range closes on the approach side by chance roughly half the time')
with open(os.path.join(C.HERE,'q4_snapshots.csv'),'w') as fh:
    fh.write('date,dte,spot,net_gex,net_gex_1pct_usd,flipA,flipB,call_wall,put_wall,king,pin,strike_spacing,n_strikes\n')
    for r in R: fh.write(','.join(str(r[k]) for k in ['date','dte','S','net','net_1pct','FA','FB','cw','pw','king','pin','spacing','n_strikes'])+'\n')
out.close()
