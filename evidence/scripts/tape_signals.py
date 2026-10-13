import json, glob, os, re, csv, collections, datetime
SP=os.environ['SP']
rows=[]
def occ(ticker, strike, side, expiry):
    root={'^SPX':'SPXW','^NDX':'NDXP','^RUT':'RUTW','SPX':'SPXW','NDX':'NDXP','RUT':'RUTW'}.get(ticker, ticker.replace('^',''))
    return f"O:{root}{expiry.strftime('%y%m%d')}{side}{int(round(float(strike)*1000)):08d}"
for f in sorted(glob.glob(SP+'/evidence/public_api/todays_signals_history/*.json')):
    d=json.load(open(f)); day=os.path.basename(f)[:10]; dd=datetime.date.fromisoformat(day)
    for s in d.get('signals') or []:
        play=s.get('play') or ''; m=re.search(r'([A-Z^]+)\s+\$?([\d,]+(?:\.\d+)?)\s*([CP])\b(?:\s+(0DTE|1DTE|(\d{2})/(\d{2})))?', play.replace(',',''))
        sym=None; exp=None
        if m:
            tk=m.group(1); k=m.group(2); side=m.group(3); lab=m.group(4)
            if lab=='0DTE': exp=dd
            elif lab=='1DTE': exp=dd+datetime.timedelta(days=1)
            elif lab and m.group(5): 
                mo=int(m.group(5)); da=int(m.group(6)); yr=dd.year if (mo>=dd.month) else dd.year+1; exp=datetime.date(yr,mo,da)
            if exp: sym=occ(s.get('ticker') or tk, k, side, exp)
        rows.append(dict(session=day, at=s.get('at'), ticker=s.get('ticker'), subsystem=s.get('subsystem'), kind=s.get('kind'), title=(s.get('title') or '')[:160], play=play, direction=s.get('direction'), loud=s.get('loud'), family=s.get('family'), paper=json.dumps(s.get('paper')) if s.get('paper') else '', occ=sym or '', expiry=exp.isoformat() if exp else ''))
w=csv.DictWriter(open(SP+'/evidence/analysis/public_tape_signals.csv','w',newline=''), fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('rows', len(rows), 'with occ', sum(1 for r in rows if r['occ']))
C=collections.Counter
print('loud by subsystem:', C((r['subsystem'],r['loud']) for r in rows).most_common(20))
print('paper present:', sum(1 for r in rows if r['paper']), 'sample:', [r['paper'] for r in rows if r['paper']][:3])
print('direction by subsystem:', {k: dict(C(r['direction'] for r in rows if r['subsystem']==k)) for k in ['index-read','trade-now','moc-wick','block-sniper','sus-strike','momentum-ignition','relative-burst','hold-advisor']})
# hold-advisor sequences: group by contract
seq=collections.defaultdict(list)
for r in rows:
    if r['subsystem']=='hold-advisor': seq[(r['session'], r['play'])].append((r['at'][11:16], r['kind']))
print('hold-advisor threads:', len(seq)); 
for k,v in list(seq.items())[:8]: print('  ',k, v)
print('kinds for index-read:', C(r['kind'] for r in rows if r['subsystem']=='index-read').most_common(10))
print('kinds for trade-now/moc-wick/block-sniper:', C((r['subsystem'],r['kind']) for r in rows if r['subsystem'] in ('trade-now','moc-wick','block-sniper','anchor-book','power-hour','big-print')).most_common(30))
