import json, sys, collections, statistics, re, datetime
d=json.load(open(sys.argv[1])); ts=d['trades']; C=collections.Counter
def cat(r):
    r=(r or '').upper()
    for k,p in [('SNIPER','SNIPER'),('STOP/KILL','STOP LOSS|HARD KILL|SHADOW STOP|PREMIUM STOP'),('TRAIL','TRAILING'),('GEX','GEX'),('ICT_STRUCT','ICT'),('TP','PROFIT|TP|TIER'),('THETA','THETA'),('TREND','TREND'),('DIVERG','DIVERGENCE')]:
        if re.search(p,r): return k
    return 'OTHER'
months=sorted(set(t['entryTime'][:7] for t in ts))
print('--- per-month era table: n | conf==0 % | sniper-exit % | entrySource=STANDARD % | riskBudget present % | quoteQuality present % | physicsVerdict present % | dayTypeGate present % | genome tag % | helix tag % | avg confluence count | wr | pnl')
for m in months:
    v=[t for t in ts if t['entryTime'][:7]==m]; n=len(v)
    f=lambda fn: round(100*sum(1 for t in v if fn(t))/n)
    print(f"{m} n={n:3d} | conf0={f(lambda t:(t.get('confidence') or 0)==0):3d}% | sniper={f(lambda t:'SNIPER' in (t.get('exitReason') or '')):3d}% | std={f(lambda t:t.get('entrySource')=='STANDARD'):3d}% | risk={f(lambda t:bool(t.get('riskBudget'))):3d}% | quote={f(lambda t:bool(t.get('quoteQuality'))):3d}% | phys={f(lambda t:bool(t.get('physicsVerdictEntry'))):3d}% | daygate={f(lambda t:bool(t.get('dayTypeGateVerdict'))):3d}% | genome={f(lambda t:any(s.startswith('GENOME') for s in t.get('confluenceSignals') or [])):3d}% | helix={f(lambda t:any(s.startswith('HELIX') for s in t.get('confluenceSignals') or [])):3d}% | nconf={statistics.mean(len(t.get('confluenceSignals') or []) for t in v):5.1f} | wr={100*sum(1 for t in v if (t.get('pnl') or 0)>0)/n:4.0f}% | pnl={sum(t.get('pnl') or 0 for t in v):8.1f}")
print('--- exit category mix by month')
for m in months:
    v=[t for t in ts if t['entryTime'][:7]==m]; print(m, C(cat(t.get('exitReason')) for t in v).most_common())
sn=[t for t in ts if 'SNIPER' in (t.get('exitReason') or '')]
print('--- sniper-exit date range:', min(t['entryTime'] for t in sn)[:10], '->', max(t['entryTime'] for t in sn)[:10])
z=[t for t in ts if (t.get('confidence') or 0)==0]; print('--- conf==0 date range:', min(t['entryTime'] for t in z)[:10], '->', max(t['entryTime'] for t in z)[:10], ' months:', C(t['entryTime'][:7] for t in z).most_common())
# strike selection: moneyness at entry: parse contract strike vs entryPrice
mon=[]
for t in ts:
    m=re.search(r'\$([\d.]+)\s*([CP])', t.get('contract') or ''); 
    if m and t.get('entryPrice'):
        k=float(m.group(1)); s=float(t['entryPrice']); side=m.group(2)
        otm=(k-s)/s*100 if side=='C' else (s-k)/s*100
        mon.append((t['ticker'], round(otm,2), t.get('contract')[:4], t['tradeType']))
print('--- moneyness (% OTM, negative=ITM) 0DTE scalps:', 'n', len([x for x in mon if x[3]=='SCALP']))
for tk in ['^SPX','QQQ','SPY','IWM','^RUT','^NDX']:
    v=[x[1] for x in mon if x[0]==tk and x[3]=='SCALP']
    if v: print(f'   {tk}: n={len(v)} med={statistics.median(v):.2f}% q25={statistics.quantiles(v,n=4)[0]:.2f} q75={statistics.quantiles(v,n=4)[2]:.2f} ITM%={100*sum(1 for x in v if x<0)/len(v):.0f}%')
print('--- DTE labels:', C((t.get('contract') or '')[:4] for t in ts).most_common(8))
# premium distribution by ticker
for tk in ['^SPX','QQQ','SPY','IWM','^RUT','^NDX']:
    v=[t['entryPremium'] for t in ts if t['ticker']==tk and t['tradeType']=='SCALP']
    if v: print(f'   entryPremium {tk}: med={statistics.median(v):.2f} q25={statistics.quantiles(v,n=4)[0]:.2f} q75={statistics.quantiles(v,n=4)[2]:.2f}')
# highWaterMark vs final pnl: how much giveback
hw=[(t.get('highWaterMark') or 0, t.get('pnlPercent') or 0) for t in ts if t['tradeType']=='SCALP']
print('--- scalps: HWM>=25% count', sum(1 for h,p in hw if h>=0.25), 'of which closed >=+15%:', sum(1 for h,p in hw if h>=0.25 and p>=0.15), 'closed negative:', sum(1 for h,p in hw if h>=0.25 and p<0))
print('--- scalps: HWM<5% count', sum(1 for h,p in hw if h<0.05), 'avg pnl%', round(100*statistics.mean([p for h,p in hw if h<0.05]),1))
# win rate vs number of confluence signals / confidence (post-cap)
for lo,hi in [(0,20),(20,40),(40,60),(60,80),(80,120)]:
    v=[t for t in ts if lo<=len(t.get('confluenceSignals') or [])<hi]
    if v: print(f'--- confluence count {lo}-{hi}: n={len(v)} wr={100*sum(1 for t in v if (t.get("pnl") or 0)>0)/len(v):.0f}% avg pnl%={100*statistics.mean([t.get("pnlPercent") or 0 for t in v]):.1f}')
