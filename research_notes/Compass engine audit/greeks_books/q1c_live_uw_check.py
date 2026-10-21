"""Q1c: two live UW GET calls (allowed: <=40, one at a time): SPY stock-state (spot) and the SPY option-contracts for one
~30-day expiry, to see whether the LIVE chain endpoint's greeks also stand on r=0, q=0 (the 68 historical snapshots do).
The token is read from the environment and never written anywhere."""
import os, sys, json, urllib.request, datetime as dt, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
tok=os.environ.get('UW_API_TOKEN'); assert tok, 'no token in env'
def get(path):
    req=urllib.request.Request('https://api.unusualwhales.com/api/'+path, headers={'Authorization':'Bearer '+tok,'Accept':'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
out=open(os.path.join(C.HERE,'q1c_results.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n')
st=get('stock/SPY/stock-state'); d=st.get('data',st); P('stock-state keys:',list(d.keys())[:12]); S=float(d.get('close') or d.get('price') or d.get('last'))
P('SPY spot (UW stock-state close):',S,'tape_time',d.get('tape_time'))
expiry='2026-11-20'
ch=get(f'stock/SPY/option-contracts?expiry={expiry}&limit=500'); rows=ch.get('data',ch); P('option-contracts rows:',len(rows), 'keys:',list(rows[0].keys()))
json.dump(rows, open(os.path.join(C.HERE,'q1c_live_chain_SPY_'+expiry+'.json'),'w'))
today=dt.date.today(); ex=dt.date.fromisoformat(expiry); tau=(ex-today).days/365; P('today',today,'expiry',expiry,'DTE',(ex-today).days)
K=np.array([C.parse_osi(r['option_symbol'])[3] for r in rows]); call=np.array([C.parse_osi(r['option_symbol'])[2]=='C' for r in rows])
iv=np.array([float(r['implied_volatility'] or 'nan') for r in rows]); du=np.array([float(r['delta']) if r['delta'] is not None else np.nan for r in rows])
gu=np.array([float(r['gamma']) if r['gamma'] is not None else np.nan for r in rows]); tu=np.array([float(r['theta']) if r['theta'] is not None else np.nan for r in rows])
bid=np.array([float(r['nbbo_bid'] or 'nan') for r in rows]); ask=np.array([float(r['nbbo_ask'] or 'nan') for r in rows]); mid=0.5*(bid+ask)
good=np.isfinite(iv)&(iv>0)&np.isfinite(du)&(np.abs(K/S-1)<0.1)
P('usable contracts within 10% of spot:',good.sum())
for r,q in [(0,0),(0.02,0),(C.R_HOUSE,0),(C.R_HOUSE,C.Q_SPY)]:
    g=C.bs(S,K[good],tau,iv[good],r,q,call[good]); e=g['delta']-du[good]
    P(f'  r={r:.4f} q={q:.3f}: delta med|err| {np.median(np.abs(e)):.4f} p90 {np.percentile(np.abs(e),90):.4f} mean {e.mean():+.4f} | gamma med rel err {np.median((g["gamma"]-gu[good])/gu[good]):+.3f} | theta/365 med|err| {np.median(np.abs(g["theta"]/365-tu[good])):.4f}')
grid=np.arange(0,0.0801,0.0025)
rm=[np.sqrt(np.mean((C.bs(S,K[good],tau,iv[good],r,0,call[good])['delta']-du[good])**2)) for r in grid]
P('  best-fit r (q=0) on the live chain: %.4f (delta rmse %.5f); at r=4.15%%: %.5f'%(grid[int(np.argmin(rm))],min(rm),rm[int(np.argmin(np.abs(grid-C.R_HOUSE)))]))
# parity gap of UW's own IVs and of mid-inverted IVs
pairs={}
for i in np.where(good)[0]: pairs.setdefault(K[i],{})['C' if call[i] else 'P']=i
gap_uw=[]; gap0=[]; gap415=[]
for k,v in pairs.items():
    if 'C' in v and 'P' in v and abs(k/S-1)<0.04:
        c,p=v['C'],v['P']; gap_uw.append(iv[c]-iv[p])
        if bid[c]>0 and bid[p]>0:
            a=C.iv_bisect(mid[c],S,k,tau,0,0,True)-C.iv_bisect(mid[p],S,k,tau,0,0,False); gap0.append(a)
            a=C.iv_bisect(mid[c],S,k,tau,C.R_HOUSE,0,True)-C.iv_bisect(mid[p],S,k,tau,C.R_HOUSE,0,False); gap415.append(a)
P(f'  same-strike IV_call-IV_put within 4% of spot: UW own IVs median {np.nanmedian(gap_uw)*100:+.2f} vol pts (n={len(gap_uw)}); mid-inverted r=0: {np.nanmedian(gap0)*100:+.2f}; r=4.15%,q=0: {np.nanmedian(gap415)*100:+.2f}')
near=np.abs(K/S-1)<0.015
F=[k+mid[v['C']]-mid[v['P']] for k,v in pairs.items() if 'C' in v and 'P' in v and abs(k/S-1)<0.015 and bid[v['C']]>0 and bid[v['P']]>0]
if F: P(f'  forward from ATM parity: {np.median(F):.2f} vs spot {S:.2f} -> implied r-q = {np.log(np.median(F)/S)/tau:+.4f} (spot and quotes at the same moment this time)')
out.close()
