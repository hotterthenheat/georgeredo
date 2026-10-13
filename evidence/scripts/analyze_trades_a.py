import json, sys, collections, statistics, re, datetime
d=json.load(open(sys.argv[1])); ts=d['trades']
def parse(t):
    try: return datetime.datetime.fromisoformat(t.replace('Z','+00:00').replace(' ','T'))
    except: return None
ET=datetime.timezone(datetime.timedelta(hours=-4))
rows=[]
for t in ts:
    e=parse(t.get('entryTime') or ''); x=parse(t.get('exitTime') or '')
    hold=(x-e).total_seconds()/60 if e and x else None
    et=e.astimezone(ET) if e else None
    rows.append(dict(ticker=t['ticker'], acct=t['accountType'], ttype=t['tradeType'], grade=t.get('setupGrade'), conf=t.get('confidence'), dirn='CALLS' if 'CALL' in (t.get('action') or '') else 'PUTS',
        entry=t.get('entryPremium'), exit=t.get('exitPremium'), pnl=t.get('pnl') or 0, pnlpct=t.get('pnlPercent'), size=t.get('size'), isize=t.get('initial_size'), hold=hold, hour=(et.hour+et.minute/60) if et else None, dow=et.weekday() if et else None,
        reason=t.get('exitReason') or '', delta=t.get('entryDelta'), iv=t.get('entryIV'), hwm=t.get('highWaterMark'), chop=t.get('isChopDay'), lotto=t.get('isGEXLotto'), aplus=t.get('is_aplus_setup'), scalein=t.get('scaleInExecuted'), partial=t.get('partial_pnl'), src=t.get('entrySource'), date=(et.date().isoformat() if et else None), env=t.get('entryEnvironment')))
def cat(reason):
    r=reason.upper()
    for k,pat in [('SNIPER_T1','SNIPER: T1'),('SNIPER_TRAIL','SNIPER: TRAILING'),('SNIPER_EMERGENCY','SNIPER: EMERGENCY'),('SNIPER_OTHER','SNIPER'),('STOP_LOSS','STOP LOSS'),('HARD_KILL','HARD KILL'),('TRAILING_PROFIT','TRAILING PROFIT'),('GEX_EXIT','GEX EXIT'),('SWING_TP','SWING PROFIT_TARGET'),('SWING_SL','SWING STOP'),('ICT_TP','ICT: TAKE PROFIT'),('TAKE_PROFIT','TAKING PROFIT'),('TP','^TP'),('AUTO_CLOSE','AUTO'),('EOD','END OF DAY'),('EXPIR','EXPIR'),('SETTLE','SETTLE'),('TURBO','TURBO'),('SHABBOTAGE','SHABBOTAGE'),('BREAKEVEN','BREAKEVEN'),('TIME','TIME'),('MANUAL','MANUAL'),('KILL','KILL')]:
        if re.search(pat, r): return k
    return 'OTHER:'+reason[:40]
C=collections.Counter
print('N', len(rows))
def grp(key, label, rowsx=rows):
    g=collections.defaultdict(list)
    for r in rowsx: g[key(r)].append(r)
    print(f'--- by {label}: n | winrate | avg pnl | sum pnl | avg pnl% | med hold min')
    for k,v in sorted(g.items(), key=lambda kv: -len(kv[1])):
        w=sum(1 for r in v if r['pnl']>0); pp=[r['pnlpct'] for r in v if isinstance(r['pnlpct'],(int,float))]; hh=[r['hold'] for r in v if r['hold'] is not None]
        print(f'   {str(k)[:48]:48} {len(v):4d} | {w/len(v)*100:5.1f}% | {statistics.mean([r["pnl"] for r in v]):8.1f} | {sum(r["pnl"] for r in v):9.1f} | {statistics.mean(pp)*100 if pp else float("nan"):6.1f}% | {statistics.median(hh) if hh else float("nan"):7.1f}')
grp(lambda r: cat(r['reason']), 'exit category')
grp(lambda r: r['grade'], 'grade')
grp(lambda r: r['acct']+'/'+r['ttype'], 'account/type')
grp(lambda r: r['dirn'], 'direction')
grp(lambda r: r['ticker'], 'ticker')
grp(lambda r: ('conf<50' if (r['conf'] or 0)<50 else 'conf50-69' if r['conf']<70 else 'conf70-84' if r['conf']<85 else 'conf85+'), 'confidence bucket')
grp(lambda r: (None if r['hour'] is None else '09:30-10:00' if r['hour']<10 else '10:00-12:00' if r['hour']<12 else '12:00-13:15' if r['hour']<13.25 else '13:15-15:00' if r['hour']<15 else '15:00-16:00'), 'entry time bucket (ET)')
grp(lambda r: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][r['dow']] if r['dow'] is not None else None, 'weekday')
grp(lambda r: 'chop' if r['chop'] else 'nochop', 'chop day flag')
grp(lambda r: 'lotto' if r['lotto'] else 'normal', 'GEX lotto flag')
grp(lambda r: 'scale-in' if r['scalein'] else 'no-scalein', 'scale-in executed')
grp(lambda r: (r['env'] or {}).get('gexRegime') if isinstance(r['env'],dict) else 'n/a', 'entryEnvironment.gexRegime')
grp(lambda r: (r['env'] or {}).get('timeBucket') if isinstance(r['env'],dict) else 'n/a', 'entryEnvironment.timeBucket')
grp(lambda r: (r['env'] or {}).get('volumeTier') if isinstance(r['env'],dict) else 'n/a', 'entryEnvironment.volumeTier')
grp(lambda r: r['date'][:7], 'month')
hold=[r['hold'] for r in rows if r['hold'] is not None and r['ttype']=='SCALP']
print('--- scalp hold minutes: n',len(hold),'min',round(min(hold),1),'p25',round(statistics.quantiles(hold,n=4)[0],1),'med',round(statistics.median(hold),1),'p75',round(statistics.quantiles(hold,n=4)[2],1),'max',round(max(hold),1))
pp=[r['pnlpct'] for r in rows if isinstance(r['pnlpct'],(int,float))]
print('--- pnl% quantiles:', [round(q*100,1) for q in statistics.quantiles(pp,n=10)])
dl=[r['delta'] for r in rows if isinstance(r['delta'],(int,float)) and r['delta']!=0]
print('--- entryDelta: n',len(dl),'med',round(statistics.median([abs(x) for x in dl]),3),'q',[round(abs(q),3) for q in statistics.quantiles([abs(x) for x in dl],n=4)])
iv=[r['iv'] for r in rows if isinstance(r['iv'],(int,float)) and r['iv']>0]; print('--- entryIV: n',len(iv),'med',round(statistics.median(iv),3))
# daily P&L
dd=collections.defaultdict(float)
for r in rows: dd[r['date']]+=r['pnl']
cum=0; peak=0; mdd=0; curve=[]
for k in sorted(dd): cum+=dd[k]; peak=max(peak,cum); mdd=min(mdd,cum-peak); curve.append((k,round(cum,1)))
print('--- trading days', len(dd), 'max drawdown $', round(mdd,1), 'final', round(cum,1))
print('--- equity curve sample:', curve[::10])
# exit reason raw examples per category
ex=collections.defaultdict(set)
for r in rows: 
    if len(ex[cat(r['reason'])])<4: ex[cat(r['reason'])].add(r['reason'][:110])
print('--- exit reason examples:')
for k,v in ex.items(): print('  ',k,'=>',list(v))
