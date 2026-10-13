# T1-T4: fill realism, cost-adjusted replay, exit-rule alternatives, MFE/MAE vs random-time baseline. Uses UW 1-minute contract bars.
import json, os, glob, datetime, statistics, random, collections, math
SP=os.environ['SP']; random.seed(7)
d=json.load(open(SP+'/evidence/public_api/trades_all.json')); ts=d['trades']
ET=datetime.timezone(datetime.timedelta(hours=-4))
def P(s): return datetime.datetime.fromisoformat(s.replace('Z','+00:00').replace(' ','T'))
def load(tid, day):
    f=f'{SP}/evidence/validation/uw_bars/{tid}_{day}.json'
    if not os.path.exists(f): return None
    rows=json.load(open(f))['data']
    bars=[]
    for r in rows:
        try: bars.append(dict(t=P(r['start_time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close']), avg=float(r['avg_price']) if r.get('avg_price') else None, v=int(r.get('volume_ask_side',0))+int(r.get('volume_bid_side',0))+int(r.get('volume_mid_side',0))+int(r.get('volume_no_side',0)), ask_p=r.get('premium_ask_side'), bid_p=r.get('premium_bid_side')))
        except Exception: pass
    bars.sort(key=lambda b:b['t']); return bars
def bar_at(bars, when):
    for b in bars:
        if b['t']<=when<b['t']+datetime.timedelta(minutes=1): return b
    return None
def next_bar(bars, when):
    for b in bars:
        if b['t']>when: return b
    return None
res=[]; missing=0; nobar=0
for t in ts:
    e=P(t['entryTime']); x=P(t['exitTime']) if t.get('exitTime') else None
    be=load(t['id'], t['entryTime'][:10]); bx=load(t['id'], (t.get('exitTime') or t['entryTime'])[:10]) if x else None
    if not be: missing+=1; continue
    eb=bar_at(be,e) or next_bar(be,e); xb=(bar_at(bx,x) or next_bar(bx,x)) if (bx and x) else None
    if not eb: nobar+=1; continue
    size=t.get('size') or 1; ep=t['entryPremium']; xp=t['exitPremium']
    # entry fill realism
    inside = eb['l']-1e-9 <= ep <= eb['h']+1e-9
    pos = (ep-eb['l'])/(eb['h']-eb['l']) if eb['h']>eb['l'] else 0.5
    # session bars after entry until 15:55 ET same day (0DTE) for MFE/MAE
    eod = e.astimezone(ET).replace(hour=15,minute=55,second=0,microsecond=0).astimezone(datetime.timezone.utc)
    after=[b for b in be if e< b['t']+datetime.timedelta(minutes=1) and b['t']<=eod]
    mfe = max([b['h'] for b in after], default=ep)/ep-1 if ep else None
    mae = min([b['l'] for b in after], default=ep)/ep-1 if ep else None
    close_1555 = after[-1]['c'] if after else None
    # alternatives (0DTE scalps only, same-day)
    alt={}
    if after and t['tradeType']=='SCALP' and (not x or x.date()==e.date()):
        alt['hold_to_1555']=close_1555/ep-1
        # bracket +25/-25
        br=None
        for b in after:
            if b['l']<=ep*0.75: br=-0.25; break
            if b['h']>=ep*1.25: br=0.25; break
        alt['bracket_25']=br if br is not None else alt['hold_to_1555']
        # 30-minute time stop
        tb=[b for b in after if b['t']<=e+datetime.timedelta(minutes=30)]
        alt['time_30m']=(tb[-1]['c']/ep-1) if tb else alt['hold_to_1555']
        # published ladder: T1 +25% sell half, T2 +45% sell rest; breakeven lock after +6% HWM; trail 8%
        hwm=0; half=False; done=None; pnl_frac=0
        for b in after:
            r_h=b['h']/ep-1; r_l=b['l']/ep-1; hwm=max(hwm,r_h)
            if not half and r_h>=0.25: half=True; pnl_frac+=0.5*0.25
            if half and r_h>=0.45: done=pnl_frac+0.5*0.45; break
            trail = (hwm-0.08) if hwm>=0.06 else -0.25
            if r_l<=trail: done=pnl_frac+(0.5 if half else 1.0)*max(trail,-0.25); break
        if done is None: done=pnl_frac+(0.5 if half else 1.0)*(after[-1]['c']/ep-1)
        alt['ladder']=done
    # fill models for recorded exits
    m={}
    if xb and x:
        m['recorded']=(xp-ep)*100*size
        vw_e=eb['avg'] or (eb['o']+eb['c'])/2; vw_x=xb['avg'] or (xb['o']+xb['c'])/2
        m['bar_vwap']=(vw_x-vw_e)*100*size
        m['adverse']=(xb['l']-eb['h'])*100*size
        sp=0.08 if t['ticker'] in ('^SPX','^NDX','^RUT') else 0.12
        m['adverse_spread_fees']=((xb['l']*(1-sp/2))-(eb['h']*(1+sp/2)))*100*size - 2*size*0.70
    res.append(dict(id=t['id'], ticker=t['ticker'], ttype=t['tradeType'], grade=t.get('setupGrade'), pnl=t.get('pnl') or 0, pnlpct=t.get('pnlPercent'), inside=inside, pos=pos, eb_vwap=eb['avg'], ep=ep, mfe=mfe, mae=mae, alt=alt, models=m, month=t['entryTime'][:7], dirn='C' if 'CALL' in t['action'] else 'P', exit_inside=(xb['l']-1e-9<=xp<=xb['h']+1e-9) if xb else None, hold=(x-e).total_seconds()/60 if x else None, after_n=len(after)))
print(f'trades={len(ts)} evaluated={len(res)} missing_bars={missing} no_bar_at_entry={nobar}')
R=res
print('--- T1 fill realism: entry premium inside entry-minute bar range:', f"{100*sum(1 for r in R if r['inside'])/len(R):.1f}%", '| exit inside exit bar:', f"{100*sum(1 for r in R if r['exit_inside'])/max(1,sum(1 for r in R if r['exit_inside'] is not None)):.1f}%")
print('    entry position within bar (0=low,1=high) median:', round(statistics.median(r['pos'] for r in R),2), ' entries below bar VWAP:', f"{100*sum(1 for r in R if r['eb_vwap'] and r['ep']<r['eb_vwap'])/max(1,sum(1 for r in R if r['eb_vwap'])):.1f}%")
def summ(vals):
    vals=[v for v in vals if v is not None]; 
    if not vals: return 'n/a'
    w=[v for v in vals if v>0]; l=[v for v in vals if v<0]
    pf=(sum(w)/abs(sum(l))) if l else float('inf')
    return f"n={len(vals)} total={sum(vals):9.1f} wr={100*len(w)/len(vals):5.1f}% avgW={statistics.mean(w) if w else 0:7.1f} avgL={statistics.mean(l) if l else 0:7.1f} exp={statistics.mean(vals):6.1f} PF={pf:4.2f}"
print('--- T2 fill models ($):')
for k in ['recorded','bar_vwap','adverse','adverse_spread_fees']:
    print(f'   {k:22}', summ([r['models'].get(k) for r in R if r['models']]))
# bootstrap CI on expectancy for recorded and adverse_spread_fees
for k in ['recorded','adverse_spread_fees']:
    v=[r['models'][k] for r in R if r['models']]; bs=[]
    for _ in range(3000): s=[random.choice(v) for _ in v]; bs.append(statistics.mean(s))
    bs.sort(); print(f'   {k} expectancy 95% CI: [{bs[int(0.025*len(bs))]:.1f}, {bs[int(0.975*len(bs))]:.1f}]')
print('--- T3 exit alternatives (0DTE scalps, % of premium, equal-weighted):')
S=[r for r in R if r['alt']]
print('   recorded exit          ', summ([r['pnlpct']*100 for r in S if r['pnlpct'] is not None]))
for k in ['hold_to_1555','bracket_25','time_30m','ladder']:
    print(f'   {k:22}', summ([r['alt'][k]*100 for r in S if k in r['alt']]))
print('--- T4 MFE/MAE (0DTE scalps):', 'median MFE', f"{100*statistics.median(r['mfe'] for r in S):.1f}%", 'median MAE', f"{100*statistics.median(r['mae'] for r in S):.1f}%", '| MFE>=+25%:', f"{100*sum(1 for r in S if r['mfe']>=0.25)/len(S):.0f}%", '| MAE<=-25%:', f"{100*sum(1 for r in S if r['mae']<=-0.25)/len(S):.0f}%")
# random-time baseline: same contract, random entry minutes on same day
pct=[]
for r in S:
    t=next(x for x in ts if x['id']==r['id']); bars=load(t['id'], t['entryTime'][:10]); e=P(t['entryTime'])
    eod=e.astimezone(ET).replace(hour=15,minute=55,second=0,microsecond=0).astimezone(datetime.timezone.utc)
    cands=[b for b in bars if b['t']<=eod-datetime.timedelta(minutes=5) and b['t'].astimezone(ET).hour*60+b['t'].astimezone(ET).minute>=9*60+35]
    if len(cands)<30: continue
    base=[]
    for _ in range(20):
        b=random.choice(cands); ep=b['c']; after=[z for z in bars if z['t']>b['t'] and z['t']<=eod]
        if ep and after: base.append(max(z['h'] for z in after)/ep-1)
    if base: pct.append(sum(1 for v in base if v<r['mfe'])/len(base))
print('   random-time MFE percentile of actual entries: n', len(pct), 'median', round(100*statistics.median(pct)), 'mean', round(100*statistics.mean(pct)), '(50 = no timing edge)')
# by month OOS split
print('--- by month (recorded vs adverse+spread+fees):')
for mth in sorted(set(r['month'] for r in R)):
    v=[r for r in R if r['month']==mth and r['models']]
    print(f'   {mth} n={len(v):3d} recorded={sum(r["models"]["recorded"] for r in v):8.1f} adverse_fees={sum(r["models"]["adverse_spread_fees"] for r in v):8.1f}')
json.dump(res, open(SP+'/evidence/validation/validation_results.json','w'), default=str)
