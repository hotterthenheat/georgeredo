"""How often does the reconstructed sweep signal coincide with GeorgeFi's own SPY/QQQ/IWM entries (±5 min, same direction)?"""
import json, sys, datetime, collections, zoneinfo, gzip
ET = zoneinfo.ZoneInfo('America/New_York')
OUT = sys.argv[1]; LEDGER = sys.argv[2]
sigs = json.load(open(OUT + '/signals.json'))
led = json.load(gzip.open(LEDGER, 'rt'))['trades'] if LEDGER.endswith('.gz') else json.load(open(LEDGER))['trades']
def P(s): return datetime.datetime.fromisoformat(s.replace('Z', '+00:00').replace(' ', 'T')).astimezone(ET)
S = collections.defaultdict(list)
for s in sigs: S[(s['ticker'], s['date'], s['mode'], s['levelset'])].append((datetime.datetime.fromisoformat(s['t']), s['direction'], s['level']))
led = [t for t in led if t['ticker'] in ('SPY', 'QQQ', 'IWM') and t['tradeType'] == 'SCALP']
print('GeorgeFi SPY/QQQ/IWM scalps in window:', len(led))
for mode in ('sweep', 'continuation'):
    for ls in ('ict', 'ict+gex'):
        hit = 0; hit_any_dir = 0; n = 0
        for t in led:
            e = P(t['entryTime']); d = e.strftime('%Y-%m-%d'); direction = 'BULLISH' if 'CALL' in t['action'] else 'BEARISH'
            cands = S.get((t['ticker'], d, mode, ls), [])
            near = [c for c in cands if abs((c[0] - e).total_seconds()) <= 300]
            n += 1
            if any(c[1] == direction for c in near): hit += 1
            if near: hit_any_dir += 1
        print(f'{mode:13} {ls:8}: same-direction signal within ±5 min of GeorgeFi entry: {hit}/{n} = {100*hit/n:.1f}% | any signal within ±5 min: {100*hit_any_dir/n:.1f}%')
# reverse: how many of our sweep signals (ict+gex) have a GeorgeFi entry within ±5 min same direction, in GeorgeFi's active period?
L = collections.defaultdict(list)
for t in led: L[(t['ticker'], P(t['entryTime']).strftime('%Y-%m-%d'))].append((P(t['entryTime']), 'BULLISH' if 'CALL' in t['action'] else 'BEARISH'))
dates = sorted(set(k[1] for k in L)); lo, hi = dates[0], dates[-1]
ours = [s for s in sigs if s['mode'] == 'sweep' and s['levelset'] == 'ict+gex' and lo <= s['date'] <= hi]
m = sum(1 for s in ours if any(abs((e - datetime.datetime.fromisoformat(s['t'])).total_seconds()) <= 300 and dr == s['direction'] for e, dr in L.get((s['ticker'], s['date']), [])))
print(f'our sweep signals in GeorgeFi period: {len(ours)}; with a same-direction GeorgeFi entry within ±5 min: {m} ({100*m/max(1,len(ours)):.1f}%)')
# direction agreement when both fire the same day within 30 min
agree = dis = 0
for s in ours:
    for e, dr in L.get((s['ticker'], s['date']), []):
        if abs((e - datetime.datetime.fromisoformat(s['t'])).total_seconds()) <= 1800:
            agree += (dr == s['direction']); dis += (dr != s['direction'])
print(f'direction agreement within ±30 min: agree={agree} disagree={dis}')
