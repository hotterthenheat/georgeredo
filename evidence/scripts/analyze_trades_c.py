import json, sys, collections, statistics, re, datetime
d=json.load(open(sys.argv[1])); ts=d['trades']
C=collections.Counter
def P(s):
    try: return datetime.datetime.fromisoformat(s.replace('Z','+00:00').replace(' ','T'))
    except: return None
ET=datetime.timezone(datetime.timedelta(hours=-4))
# 1. Sniper subsystem
sn=[t for t in ts if 'SNIPER' in (t.get('exitReason') or '').upper()]
print('--- SNIPER-exit trades:', len(sn), 'tickers', C(t['ticker'] for t in sn).most_common(6))
print('    spx_sniper_window:', C(str(t.get('spx_sniper_window')) for t in sn).most_common(6))
print('    spx_sniper_grade:', C(str(t.get('spx_sniper_grade')) for t in sn).most_common(8))
print('    spx_sniper_sub_mode:', C(str(t.get('spx_sniper_sub_mode')) for t in sn).most_common(8))
print('    spx_sniper_paper_mode:', C(str(t.get('spx_sniper_paper_mode')) for t in sn).most_common(4))
print('    spx_sniper_trail_stop_pct:', C(str(t.get('spx_sniper_trail_stop_pct')) for t in sn).most_common(6))
print('    spx_sniper_conviction:', C(str(t.get('spx_sniper_conviction')) for t in sn).most_common(8))
print('    confidence:', C(t.get('confidence') for t in sn).most_common(8))
print('    targets_json sample:', [t.get('spx_sniper_targets_json') for t in sn[:3]])
print('    sniperSnapshot sample:', json.dumps(sn[0].get('sniperSnapshot'))[:900])
print('    size:', C(t.get('size') for t in sn).most_common(6), 'entryPremium med', statistics.median([t['entryPremium'] for t in sn]))
# T1 lock pct and emergency pct distributions
t1=[float(m.group(1)) for t in sn for m in [re.search(r'T1 PROFIT LOCK \(\+(\d+)%', t['exitReason'])] if m]
em=[float(m.group(1)) for t in sn for m in [re.search(r'EMERGENCY_STOP \((-?[\d.]+)%', t['exitReason'])] if m]
print('    T1 lock pct: n',len(t1),'min',min(t1) if t1 else None,'med',statistics.median(t1) if t1 else None,'max',max(t1) if t1 else None)
print('    emergency pct: n',len(em),'min',min(em) if em else None,'med',statistics.median(em) if em else None,'max',max(em) if em else None)
# 2. stop loss numeric levels for non-sniper
sl=[(t['ticker'],float(m.group(1)),t.get('volumeAnalysis','')[:40], t.get('setupGrade')) for t in ts for m in [re.search(r'STOP LOSS \((-?\d+)%\)', t['exitReason'] or '')] if m]
print('--- STOP LOSS levels:', C(x[1] for x in sl).most_common(12))
vixsl=collections.defaultdict(list)
for tk,lv,va,g in sl:
    m=re.search(r'VIX ([\d.]+)', va); 
    if m: vixsl['VIX<15' if float(m.group(1))<15 else 'VIX15-20' if float(m.group(1))<20 else 'VIX20-30' if float(m.group(1))<30 else 'VIX30+'].append(lv)
print('    by VIX bucket (level counts):', {k:C(v).most_common(4) for k,v in vixsl.items()})
hk=[float(m.group(1)) for t in ts for m in [re.search(r'HARD KILL \((-?[\d.]+)% exceeded (-?[\d.]+)% floor', t['exitReason'] or '')] if m]
print('--- HARD KILL floors:', C(float(m.group(2)) for t in ts for m in [re.search(r'HARD KILL \((-?[\d.]+)% exceeded (-?[\d.]+)% floor', t['exitReason'] or '')] if m).most_common())
tp=[(float(m.group(1)),float(m.group(2))) for t in ts for m in [re.search(r'TRAILING PROFIT \(\+(\d+)% locked, exited at \+?(-?\d+)%', t['exitReason'] or '')] if m]
print('--- TRAILING PROFIT locked levels:', C(x[0] for x in tp).most_common(10))
# 3. entry timing: minute-of-cycle
secs=C(); mins=C(); 
for t in ts:
    e=P(t['entryTime']); 
    if e: secs[e.second//10*10]+=1; mins[e.minute%5]+=1
print('--- entry second bucket:', sorted(secs.items()), ' minute mod 5:', sorted(mins.items()))
# 4. cooldown + trades/day + daily loss stop
byday=collections.defaultdict(list)
for t in ts:
    e=P(t['entryTime']); 
    if e: byday[e.astimezone(ET).date()].append((e,t))
tpd=[len(v) for v in byday.values()]; print('--- trades/day: max',max(tpd),'dist',sorted(C(tpd).items()))
gaps=[]; same_dir=[]
for day,v in byday.items():
    v.sort(key=lambda x:x[0]); last={}
    for e,t in v:
        k=t['ticker']
        if k in last: gaps.append((e-last[k][0]).total_seconds()/60)
        last[k]=(e,t)
print('--- same-ticker re-entry gap minutes: n',len(gaps),'min',round(min(gaps),1) if gaps else None,'p10',round(statistics.quantiles(gaps,n=10)[0],1) if len(gaps)>10 else None,'med',round(statistics.median(gaps),1) if gaps else None)
print('    gaps < 30 min:', sum(1 for g in gaps if g<30), ' <5min:', sum(1 for g in gaps if g<5))
# per-ticker-per-day count, same-direction count
ptd=C(); sd=C()
for day,v in byday.items():
    for e,t in v: ptd[(day,t['ticker'])]+=1; sd[(day,t['ticker'],'C' if 'CALL' in t['action'] else 'P')]+=1
print('--- max trades per ticker per day:', max(ptd.values()), 'dist', sorted(C(ptd.values()).items()))
print('--- max same-direction per ticker per day:', max(sd.values()), 'dist', sorted(C(sd.values()).items()))
# daily loss stop: after cumulative day pnl <= -300 any more entries?
viol=0; tot=0
for day,v in byday.items():
    v.sort(key=lambda x:x[0]); cum=0
    for e,t in v:
        if cum<=-300: viol+=1
        tot+=1; cum+=t.get('pnl') or 0
print('--- entries after day P&L <= -$300 (approx, uses realized pnl of earlier entries):', viol, 'of', tot)
# 5. size vs grade / vix
print('--- size by grade:', {g:C(t['size'] for t in ts if t['setupGrade']==g).most_common(4) for g in ['A+','A','A-','B+']})
# 6. exit time of day for scalps: auto-close at 15:58?
late=[P(t['exitTime']).astimezone(ET).strftime('%H:%M') for t in ts if t['tradeType']=='SCALP' and P(t['exitTime']) and P(t['exitTime']).astimezone(ET).hour>=15 and P(t['exitTime']).astimezone(ET).minute>=50]
print('--- scalp exits after 15:50 ET:', C(late).most_common(8))
# 7. premium/underlying move relation: pnlPercent vs underlying? no exitPrice. skip
# 8. confidence==0 trades
z=[t for t in ts if (t.get('confidence') or 0)==0]; print('--- confidence==0 trades:', len(z), 'exit cats', C((t['exitReason'] or '')[:18] for t in z).most_common(5), 'entrySource', C(t.get('entrySource') for t in z).most_common(3), 'tickers', C(t['ticker'] for t in z).most_common(5))
# 9. action vs direction naming by era
print('--- action naming by month:', {m:C(t['action'] for t in ts if t['entryTime'][:7]==m).most_common(4) for m in sorted(set(t['entryTime'][:7] for t in ts))})
# 10. rationale samples for sniper and for ICT
for t in sn[:2]: print('--- sniper rationale:', (t.get('rationale') or '')[:600].replace('\n',' '))
ict=[t for t in ts if t.get('entrySource')=='STANDARD'][:2]
for t in ict: print('--- STANDARD rationale:', (t.get('rationale') or '')[:700].replace('\n',' '))
print('--- directionAuditPath sample:', json.dumps(ict[0].get('directionAuditPath'))[:1200] if ict else None)
print('--- riskBudget sample:', json.dumps(ict[0].get('riskBudget'))[:500] if ict else None)
print('--- pnlAttribution sample:', json.dumps(ict[0].get('pnlAttribution'))[:500] if ict else None)
