"""Test 4: per-strike ask-side premium bursts (flow-per-strike-intraday, 40-session sample x 3 tickers, both 'filter' values).
Burst = strike-side minute whose ask-side premium x >= k * max(trailing 20-minute median, FLOOR) and x >= MINABS (k in {5,10}); within 1 % (main) / 2 % of spot;
15-minute cooldown per strike-side. Direction: call burst -> long, put burst -> short.
(a) underlying forward 15/30/60-minute log return in the burst direction (bps); (b) the 0DTE contract at that strike/side: entry = VWAP of the next option bar,
exit = VWAP of the bar 15/30 minutes later, net of half-spread (1 % SPY/QQQ, 2 % IWM per side) and $0.70 fees per side.
Baseline: random minutes matched per ticker-day (same count), random side, ATM 0DTE contract. NOTE: the endpoint only returns the day's top-8 strikes by the
chosen filter (full-day totals -> selection on outcome), and aggregates all expiries; the 0DTE contract is used as the tradable proxy."""
import json, random, datetime, collections, concurrent.futures, time
import pandas as pd, numpy as np
from common import *
from stats import mean_ci
S = json.load(open(os.path.join(OUT, 'samples.json')))['fps_sessions']
FLOOR = {'SPY': 2000, 'QQQ': 2000, 'IWM': 1000}; MINABS = {'SPY': 20000, 'QQQ': 20000, 'IWM': 10000}; HS = {'SPY': 0.01, 'QQQ': 0.01, 'IWM': 0.02}; FEE = 0.70
random.seed(7); events = []; coverage = []
for filt in ('NetPremium', 'Volume'):
    for tk in TICKERS:
        for d in S:
            params = {'date': d} if filt == 'NetPremium' else {'date': d, 'filter': 'Volume'}
            rows = (data.get(f'stock/{tk}/flow-per-strike-intraday', params) or {}).get('data') or []
            rth, _ = data.underlying_bars(tk, d)
            if len(rth) < 380 or not rows: continue
            c = np.full(390, np.nan)
            for b in rth:
                m = (b['t'].hour - 9) * 60 + b['t'].minute - 30
                if 0 <= m < 390: c[m] = b['c']
            P = collections.defaultdict(lambda: np.zeros(390))
            for r in rows:
                t = to_et(r['timestamp']); m = (t.hour - 9) * 60 + t.minute - 30
                if not (0 <= m < 390): continue
                k = float(r['strike']); P[(k, 'C')][m] += f(r['call_premium_ask_side']); P[(k, 'P')][m] += f(r['put_premium_ask_side'])
            strikes = sorted({k for k, s in P}); near = [k for k in strikes if np.isfinite(c[200]) and abs(k / c[200] - 1) <= 0.01]
            coverage.append(dict(filter=filt, ticker=tk, date=d, strikes=len(strikes), strikes_within1pct_of_midday_spot=len(near), rows=len(rows)))
            nb = 0
            for (k, side), x in P.items():
                last = -99
                for m in range(20, 361):
                    if not np.isfinite(c[m]) or m - last < 15: continue
                    med = np.median(x[m - 20:m]); ref = max(med, FLOOR[tk])
                    if x[m] < 5 * ref or x[m] < MINABS[tk]: continue
                    band = abs(k / c[m] - 1)
                    if band > 0.02: continue
                    last = m; nb += band <= 0.01
                    ev = dict(set='burst', filter=filt, ticker=tk, date=d, strike=k, side=side, minute=m, spot=c[m], x=x[m], med=med, mult=x[m] / ref, band=band, dir=1 if side == 'C' else -1)
                    for h in (15, 30, 60): ev[f'u{h}'] = ev['dir'] * np.log(c[m + h] / c[m]) * 1e4 if m + h < 390 and np.isfinite(c[m + h]) else np.nan
                    events.append(ev)
            for _ in range(nb):  # matched random baseline (ATM strike, random side, random minute)
                m = random.randrange(20, 361)
                if not np.isfinite(c[m]): continue
                side = random.choice('CP'); ev = dict(set='baseline', filter=filt, ticker=tk, date=d, strike=float(round(c[m])), side=side, minute=m, spot=c[m], x=np.nan, med=np.nan, mult=np.nan, band=abs(round(c[m]) / c[m] - 1), dir=1 if side == 'C' else -1)
                for h in (15, 30, 60): ev[f'u{h}'] = ev['dir'] * np.log(c[m + h] / c[m]) * 1e4 if m + h < 390 and np.isfinite(c[m + h]) else np.nan
                events.append(ev)
print('events', collections.Counter((e['set'], e['filter']) for e in events), flush=True)
def cid_of(e): return data.contract_id(e['ticker'], datetime.date.fromisoformat(e['date']), e['side'], e['strike'])
needs = sorted({(cid_of(e), e['date']) for e in events}); print('contract-days', len(needs), flush=True); t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
    for i, n in enumerate(ex.map(lambda j: len(data.option_bars(*j)), needs)):
        if i % 200 == 0: print('bars', i, data.STATS, round(time.time() - t0), 's', flush=True)
for e in events:
    bars = data.option_bars(cid_of(e), e['date']); st = datetime.datetime(*map(int, e['date'].split('-')), 9 + (e['minute'] + 30) // 60, (e['minute'] + 30) % 60, tzinfo=ET)
    eidx = next((k for k, b in enumerate(bars) if b['t'] > st), None)
    e['has_bars'] = len(bars) > 0
    if eidx is None or (bars[eidx]['t'] - st).total_seconds() > 180: continue
    eb = bars[eidx]; px = eb['vw'] or eb['o']
    if not px or px < 0.05: continue
    e['entry_px'] = px; hs = HS[e['ticker']]
    for h in (15, 30):
        xb = next((b for b in bars[eidx + 1:] if b['t'] >= eb['t'] + datetime.timedelta(minutes=h)), None)
        if xb is None: continue
        xp = xb['vw'] or xb['c']; buy = px * (1 + hs); sell = xp * (1 - hs)
        e[f'c{h}_raw'] = xp / px - 1; e[f'c{h}_net'] = (sell - buy) / buy - 2 * FEE / (100 * buy)
ev = pd.DataFrame(events); ev.to_csv(os.path.join(OUT, 'bursts_events.csv'), index=False, float_format='%.5g')
pd.DataFrame(coverage).to_csv(os.path.join(OUT, 'bursts_coverage.csv'), index=False)
summ = []
for filt in ('NetPremium', 'Volume'):
    for k in (5, 10):
        for bandmax in (0.01, 0.02):
            for st_ in ('burst', 'baseline'):
                g = ev[(ev['filter'] == filt) & (ev.set == st_) & (ev.band <= bandmax)]
                if st_ == 'burst': g = g[g.mult >= k]
                rec = dict(filter=filt, k=k, band=bandmax, set=st_, n=len(g), tickers=dict(collections.Counter(g.ticker)), has_bars=float(g.has_bars.mean()) if len(g) else np.nan)
                for col in ('u15', 'u30', 'u60', 'c15_raw', 'c15_net', 'c30_raw', 'c30_net'):
                    if col not in g: continue
                    gg = g.dropna(subset=[col]); mc = mean_ci(gg[col].values, gg.date.values)
                    rec[f'{col}_mean'] = mc['mean']; rec[f'{col}_lo'] = mc['lo']; rec[f'{col}_hi'] = mc['hi']; rec[f'{col}_p'] = mc.get('p', np.nan); rec[f'{col}_n'] = mc['n']; rec[f'{col}_hit'] = float((gg[col] > 0).mean()) if len(gg) else np.nan
                summ.append(rec)
sm = pd.DataFrame(summ); sm.to_csv(os.path.join(OUT, 'bursts_summary.csv'), index=False, float_format='%.5g')
pd.set_option('display.width', 300); pd.set_option('display.max_columns', 40)
print(sm[['filter', 'k', 'band', 'set', 'n', 'u15_mean', 'u15_lo', 'u15_hi', 'u30_mean', 'u30_lo', 'u30_hi', 'u60_mean', 'u60_lo', 'u60_hi', 'u30_hit']].to_string())
print(sm[['filter', 'k', 'band', 'set', 'n', 'c15_net_n', 'c15_raw_mean', 'c15_net_mean', 'c15_net_lo', 'c15_net_hi', 'c15_net_hit', 'c30_raw_mean', 'c30_net_mean', 'c30_net_lo', 'c30_net_hi', 'c30_net_hit']].to_string())
cv = pd.DataFrame(coverage); print(cv.groupby(['filter', 'ticker'])[['strikes', 'strikes_within1pct_of_midday_spot']].mean().to_string())
