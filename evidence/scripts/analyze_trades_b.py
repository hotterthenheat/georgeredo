import json, sys, collections, re
d=json.load(open(sys.argv[1])); ts=d['trades']
C=collections.Counter; fam=C(); ex={}
for t in ts:
    for s in (t.get('confluenceSignals') or []):
        p=s.split(':')[0]; fam[p]+=1
        ex.setdefault(p,C())[s[:90]]+=1
print('--- confluence families (count, distinct variants, top examples)')
for p,n in fam.most_common(200):
    v=ex[p]; print(f'{p:28} n={n:5d} variants={len(v):4d} | ' + ' || '.join(f'{k}({c})' for k,c in v.most_common(4)))
# per-trade: parse the CONVICTION_AXES, CONFIDENCE_CAP, BONUS_CAP, GRADE_CAPPED, SWEEP_FLOOR, SESSION_ADJ
print('--- numeric-tag parsing examples')
for tag in ['CONVICTION_AXES','CONFIDENCE_CAP','BONUS_CAP','GRADE_CAPPED','SWEEP_FLOOR','SESSION_ADJ','CONSENSUS_BONUS','ENTRY_TIMING','HELIX_SIZE','CONFLUENCE_SIZE','CONVICTION_TIER','PENALTY','A_SETUP','APLUS_SETUP','EXPANSION','ENTRY_MODEL','KILLZONE','REGIME','VIX','EM','PHYSICS','GENOME','TIDE','CORR','IMB','INST','SNIPER_GATE','PDA_CI','DIR_CONFIRM','CRITICAL_CONFLICT_CLUSTER','INST_BLOCK_OVERRIDE','GEX','DELTA_FLOW','SPX_VELOCITY','VWAP','AMD','PM','PREMARKET','WP','MTF','OTE','BREAKER','EPIGENETIC_TRAIT','HELIX_PHI','HELIX_CONDG','HELIX_METRIC','ICT','RS','BONUS','MULTI_SWEEP','SWEEP_ALIGNED','LEVEL_PROXIMITY','CHOP_DAY','CHOP_LIGHT','VOL','CONFIRM','EXPECTED_MOVE','OB_WEAK_BYPASSED','MULTI_SWEEP_INST_PRIORITY','SWEEP_CONFLICT','GAMEPLAN','CONFLICT','STRUCT','BOS','CHoCH','ENTRY','LIQ_BUY','LIQ_SELL','SWEEP_BUY','SWEEP_SELL','OB_BULL','OB_BEAR','BREAKER_BULL','BREAKER_BEAR','BREAKER_GATE','MTF_ALIGNED']:
    v=ex.get(tag); 
    if v: print(f'  {tag}: ' + ' | '.join(k for k,_ in v.most_common(8)))
# rationale text samples
print('--- rationale samples')
for t in ts[:6]: print('  ', (t.get('rationale') or '')[:400].replace('\n',' '))
print('--- pnlAttribution sample:', json.dumps(ts[0].get('pnlAttribution'))[:600])
print('--- safetyLayersFired:', C(json.dumps(t.get('safetyLayersFired'))[:80] for t in ts).most_common(8))
print('--- directionAuditPath sample:', json.dumps(ts[0].get('directionAuditPath'))[:800])
print('--- convictionAxes sample:', json.dumps(ts[0].get('convictionAxes'))[:400])
print('--- criticalConflictBuckets:', C(json.dumps(t.get('criticalConflictBuckets'))[:60] for t in ts).most_common(6))
print('--- riskBudget sample:', json.dumps(ts[0].get('riskBudget'))[:400])
print('--- watchLevels sample:', json.dumps(ts[0].get('watchLevels'))[:600])
print('--- gexProfile sample:', json.dumps(ts[0].get('gexProfile'))[:400])
print('--- chartContext sample:', json.dumps(ts[0].get('chartContext'))[:300])
print('--- ictContext keys:', list((ts[0].get('ictContext') or {}).keys()))
print('--- sniperSnapshot sample:', json.dumps(ts[0].get('sniperSnapshot'))[:300])
print('--- stopLossLevel/takeProfit/trailing fields:', C((t.get('stopLossLevel'), t.get('take_profit'), t.get('trailing_stop')) for t in ts).most_common(5))
print('--- swing fields sample:', [(t['ticker'], t.get('swingEntryPrice'), t.get('swingStopPrice'), t.get('swingStopLabel'), t.get('target_price'), t.get('max_hold_sessions')) for t in ts if t['tradeType']=='SWING'][:6])
