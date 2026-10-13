"""Load the two reference entry sets and all option bars they need (from cache); build and verify the matrices; also build the
random-entry control set (3,000 random ticker-day-minutes 09:35-15:30, random direction, ATM contract, where the cache holds the bars)."""
import gzip, csv, random, pickle, glob, re, os, collections, time
from common import *
import q4_engine as E
rows = [r for r in csv.DictReader(gzip.open(BT + '/results/v1/trades.csv.gz', 'rt')) if r['variant'] in ('sweep|ict+gex|all|none|ladder', 'continuation|ict+gex|all|none|ladder')]
print('reference trades', len(rows), flush=True)
t0 = time.time(); cache = {}
for cd in sorted({(r['contract'], r['date']) for r in rows}):
    cache[cd] = data.option_bars(*cd)
print('bars loaded', len(cache), round(time.time() - t0, 1), 's', flush=True)
assert E.verify(rows, cache), 'vectorised engine disagrees with exits.simulate'
# random-entry control set
avail = set()
for f in glob.glob(os.environ.get('BT_CACHE', BT + '/cache') + '/*option-contract_*_intraday_date-*'):
    m = re.search(r'option-contract_([A-Z]+\d{6}[CP]\d{8})_intraday_date-(\d{4}-\d{2}-\d{2})', f)
    if m: avail.add((m.group(1), m.group(2)))
print('cached contract-days', len(avail), flush=True)
rng = random.Random(2026); rand = []; tries = 0; day_bars = {}
days_ok = {t: [d for d in DAYS] for t in TICKERS}
while len(rand) < 3000 and tries < 200000:
    tries += 1
    tk = rng.choice(TICKERS); d = rng.choice(days_ok[tk])
    if (tk, d) not in day_bars: day_bars[(tk, d)] = data.underlying_bars(tk, d)[0]
    rth = day_bars[(tk, d)]
    if len(rth) < 300: continue
    i = rng.randrange(0, len(rth)); t = rth[i]['t']
    if not (9 * 60 + 35 <= hhmm(t) < 15 * 60 + 30): continue
    direction = rng.choice(['BULLISH', 'BEARISH']); strike = round(rth[i]['c'])
    cid = data.contract_id(tk, datetime.date.fromisoformat(d), 'C' if direction == 'BULLISH' else 'P', strike)
    if (cid, d) not in avail: continue
    if (cid, d) not in cache: cache[(cid, d)] = data.option_bars(cid, d)
    bars = cache[(cid, d)]
    eidx = next((k for k, b in enumerate(bars) if b['t'] > t), None)
    if eidx is None or (bars[eidx]['t'] - t).total_seconds() > 180: continue
    eb = bars[eidx]; entry_px = eb['vw'] or eb['o']
    if not entry_px or entry_px < 0.05: continue
    rand.append(dict(variant='RANDOM', ticker=tk, date=d, signal_t=t.isoformat(), entry_t=eb['t'].isoformat(), direction=direction, contract=cid, strike=strike, entry_px=round(entry_px, 3)))
print('random entries', len(rand), 'tries', tries, collections.Counter(r['ticker'] for r in rand), flush=True)
write_csv(OUT + '/q4_random_entries.csv', rand)
pickle.dump(dict(rows=rows, rand=rand, cache={k: v for k, v in cache.items()}), open(OUT + '/q4_bars.pkl', 'wb'))
print('saved', round(time.time() - t0, 1), 's')
