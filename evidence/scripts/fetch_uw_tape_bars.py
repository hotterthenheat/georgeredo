# After the trade-contract fetch finishes, fetch UW 1-minute bars for every (contract, session) pair on the public signal tape.
import json, os, time, csv, urllib.request, datetime, concurrent.futures, threading
SP=os.environ['SP']; KEY=os.environ['UW_API_TOKEN']
log_path=SP+'/evidence/validation/uw_fetch_log.txt'
while True:
    if os.path.exists(log_path) and 'FINISHED' in open(log_path).read(): break
    time.sleep(10)
out=SP+'/evidence/validation/uw_tape_bars'; os.makedirs(out, exist_ok=True); lock=threading.Lock(); log=open(SP+'/evidence/validation/uw_tape_fetch_log.txt','a')
pairs=set()
for r in csv.DictReader(open(SP+'/evidence/analysis/public_tape_signals.csv')):
    if r['occ'] and r['subsystem'] in ('index-read','trade-now','moc-wick','block-sniper','sus-strike','momentum-ignition','relative-burst','big-print','accumulation-sniper','power-hour','anchor-book','hold-advisor'):
        pairs.add((r['occ'][2:], r['session']))
pairs=sorted(pairs)
def get(url):
    req=urllib.request.Request(url, headers={'Authorization':'Bearer '+KEY,'Accept':'application/json'})
    for i in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429,502,503,504): time.sleep(5*(i+1)); continue
            return e.code, None
        except Exception: time.sleep(3)
    return 0, None
def work(p):
    cid,day=p; f=f'{out}/{cid}_{day}.json'
    if os.path.exists(f): return 'skip'
    code,res=get(f'https://api.unusualwhales.com/api/option-contract/{cid}/intraday?date={day}')
    if code==200 and res is not None: json.dump({'contract':cid,'date':day,'data':res.get('data',[])}, open(f,'w')); return 'ok'
    with lock: log.write(f'{cid} {day} code={code}\n'); log.flush()
    return 'fail'
c={'ok':0,'fail':0,'skip':0}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
    for i,r in enumerate(ex.map(work, pairs)):
        c[r]+=1
        if i%100==0:
            with lock: log.write(f'progress {c} of {len(pairs)} {datetime.datetime.utcnow().isoformat()}\n'); log.flush()
        time.sleep(0.05)
log.write(f'FINISHED {c}\n'); log.close(); print('FINISHED', c)
