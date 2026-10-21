"""Q5: a continuous agreement-confidence multiplier in place of a hard GEX-sign gate.
conf = tanh(GEX_book / ref), ref = the 85th percentile of |GEX_book| over the trailing 60 sessions before the day (the
house's bead-scale mirror; no free weight). On UW's daily book-level greek-exposure for SPY/QQQ/IWM, 2025-10-15 -> 2026-10-13.
Also: how often the raw sign flips day to day (what a hard sign gate chatters on), and the share of days under |conf|<0.2."""
import sys, os, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
out=open(os.path.join(C.HERE,'q5_results.txt'),'w')
def P(*a):
    s=' '.join(str(x) for x in a); print(s); out.write(s+'\n')
uw=pl.scan_parquet(C.LAKE+'/unusualwhales/greek-exposure.part0*.parquet').filter(pl.col('ticker').is_in(['SPY','QQQ','IWM'])).collect()
uw=uw.with_columns([pl.col('call_gamma').cast(pl.Float64),pl.col('put_gamma').cast(pl.Float64)]).with_columns([(pl.col('call_gamma')+pl.col('put_gamma')).alias('GEX'),(pl.col('call_gamma').abs()+pl.col('put_gamma').abs()).alias('GROSS')]).sort(['ticker','date'])
P('conf = tanh(GEX_book / ref), ref = p85 of |GEX_book| over the 60 sessions before the day (first 20 sessions: as many as exist, min 20)')
allrows=[]
for sym in ['SPY','QQQ','IWM']:
    s=uw.filter(pl.col('ticker')==sym); g=s['GEX'].to_numpy(); d=s['date'].to_list(); gross=s['GROSS'].to_numpy(); ng=g/gross
    ref=np.full(len(g),np.nan); conf=np.full(len(g),np.nan)
    for i in range(len(g)):
        w=np.abs(g[max(0,i-60):i])
        if len(w)>=20: ref[i]=np.percentile(w,85); conf[i]=np.tanh(g[i]/ref[i])
    v=np.isfinite(conf); c=conf[v]; sg=np.sign(g)
    flips=np.mean(sg[1:]!=sg[:-1])
    P(f'\n{sym}: sessions {len(g)}, with a reference {v.sum()}; share GEX_book>0 {np.mean(g>0):.2f}; day-to-day sign flips {flips:.2f} of sessions')
    P(f'   conf distribution: |conf|<0.2 {np.mean(np.abs(c)<0.2):.2f}, 0.2-0.5 {np.mean((np.abs(c)>=0.2)&(np.abs(c)<0.5)):.2f}, 0.5-0.8 {np.mean((np.abs(c)>=0.5)&(np.abs(c)<0.8)):.2f}, >=0.8 {np.mean(np.abs(c)>=0.8):.2f}; median conf {np.median(c):+.2f}, p10 {np.percentile(c,10):+.2f}, p90 {np.percentile(c,90):+.2f}')
    # hard sign gate chatter vs soft gate: how many sign flips happen while |conf|<0.2 (where the hard gate would have deadlocked/chattered)
    fl=np.where((sg[1:]!=sg[:-1]))[0]+1; fl=[i for i in fl if v[i]]
    P(f'   of {len(fl)} sign flips with a reference, {np.mean([abs(conf[i])<0.2 for i in fl]) if fl else float("nan"):.2f} happened at |conf|<0.2 (a soft gate would have been near zero there), {np.mean([abs(conf[i])>=0.5 for i in fl]) if fl else float("nan"):.2f} at |conf|>=0.5')
    P(f'   alternative with no window at all, conf2 = net/gross = (call+put)/(|call|+|put|): |conf2|<0.05 {np.mean(np.abs(ng)<0.05):.2f}, <0.10 {np.mean(np.abs(ng)<0.10):.2f}, <0.20 {np.mean(np.abs(ng)<0.20):.2f}; median {np.nanmedian(ng):+.3f}; corr(conf, conf2) {np.corrcoef(conf[v&np.isfinite(ng)],ng[v&np.isfinite(ng)])[0,1]:.2f}; of the sign flips {np.mean([abs(ng[i])<0.10 for i in fl]) if fl else float("nan"):.2f} were at |conf2|<0.10')
    P('   last ten sessions (date, GEX_book in gamma x OI x 100, ref, conf, net/gross):')
    for i in range(len(g)-10,len(g)): P(f'      {d[i]}  {g[i]:>14,.0f}  {ref[i]:>14,.0f}  {conf[i]:+.3f}  {ng[i]:+.3f}')
    for i in range(len(g)): allrows.append((sym,d[i],g[i],ref[i],conf[i],ng[i]))
with open(os.path.join(C.HERE,'q5_conf_series.csv'),'w') as fh:
    fh.write('sym,date,gex_book,ref_p85_60,conf,net_over_gross\n'); [fh.write(','.join(str(x) for x in r)+'\n') for r in allrows]
P('\nThe data on disk ends 2026-10-13; 2026-10-16 is not in it and the UW API answered 401 on 2026-10-21, so the 10-16 reading cannot be computed here. The nearest is 2026-10-13 above.')
out.close()
