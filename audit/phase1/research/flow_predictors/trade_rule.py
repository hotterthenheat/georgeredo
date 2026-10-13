"""Test 5: the nominally most promising flow feature as a trading rule on ATM 0DTE options.
Rule (default SPY, F1, 15-minute net premium): every 5 minutes 09:45-15:00, if F1 >= 80th pct of the trailing-20-session F1 distribution buy the ATM 0DTE call;
if F1 <= 20th pct buy the ATM put. Entry = VWAP of the first option bar after the signal minute. Exits: `trail` engine from backtest/exits.py (stop -25 %)
and, as the horizon-matched variant, a fixed 30-minute hold (VWAP of the bar 30 minutes later). Costs: backtest/costs.py 'spread' (1 % half-spread SPY/QQQ,
2 % IWM, $0.70/side). Max 2 trades per day, 30-minute cooldown, no overlapping positions. Baseline: random minutes matched per day, random side, same exits/costs."""
import sys, json, random, datetime, collections, concurrent.futures, time, subprocess
import pandas as pd, numpy as np
from common import *
import exits, costs
from stats import mean_ci
TK = sys.argv[1] if len(sys.argv) > 1 else 'SPY'; FEAT = sys.argv[2] if len(sys.argv) > 2 else 'F1'
df = pd.read_csv(os.path.join(OUT, 'panel_flow.csv.gz')); df = df[df.ticker == TK].sort_values(['date', 'minute'])
days = sorted(df.date.unique()); by_day = {d: g for d, g in df.groupby('date')}
sigs = []
for i, d in enumerate(days):
    if i < 20: continue
    hist = np.concatenate([by_day[days[j]][FEAT].values for j in range(i - 20, i)]); lo, hi = np.quantile(hist, [0.2, 0.8])
    g = by_day[d]; last = -999; n = 0
    for m, x, spot in zip(g.minute.values, g[FEAT].values, g.spot.values):
        if m % 5 or m > 330 or m - last < 30 or n >= 2: continue
        side = 'C' if x >= hi else 'P' if x <= lo else None
        if side is None: continue
        sigs.append(dict(date=d, minute=int(m), side=side, spot=float(spot), x=float(x))); last = m; n += 1
print('signals', len(sigs), collections.Counter(s['side'] for s in sigs), flush=True)
random.seed(42); base = []
for d, n in collections.Counter(s['date'] for s in sigs).items():
    g = by_day[d]; ms = g.minute.values; sp = g.spot.values
    for _ in range(n):
        k = random.randrange(len(ms));
        if ms[k] > 330: continue
        base.append(dict(date=d, minute=int(ms[k]), side=random.choice('CP'), spot=float(sp[k]), x=np.nan))
def cid_of(s): return data.contract_id(TK, datetime.date.fromisoformat(s['date']), s['side'], round(s['spot']))
needs = sorted({(cid_of(s), s['date']) for s in sigs + base}); print('contract-days', len(needs), flush=True)
def fetch(j): return len(data.option_bars(*j))
t0 = time.time(); i = 0
while i < len(needs):
    busy = subprocess.run(['pgrep', '-f', 'prefetch_'], capture_output=True).stdout.strip() != b''
    w = 1 if busy else 5; batch = needs[i:i + 50]
    with concurrent.futures.ThreadPoolExecutor(max_workers=w) as ex: list(ex.map(fetch, batch))
    i += len(batch)
    if (i // 50) % 4 == 0: print('bars', i, '/', len(needs), 'workers', w, data.STATS, round(time.time() - t0), 's', flush=True)
def run(sig_list, label):
    out = []
    for s in sig_list:
        bars = data.option_bars(cid_of(s), s['date']); st = datetime.datetime(*map(int, s['date'].split('-')), 9 + (s['minute'] + 30) // 60, (s['minute'] + 30) % 60, tzinfo=ET)
        eidx = next((k for k, b in enumerate(bars) if b['t'] > st), None)
        if eidx is None or (bars[eidx]['t'] - st).total_seconds() > 180: continue
        eb = bars[eidx]; px = eb['vw'] or eb['o']
        if not px or px < 0.05: continue
        rec = dict(set=label, date=s['date'], minute=s['minute'], side=s['side'], contract=cid_of(s), entry_px=px, prem_pct_spot=px / s['spot'])
        for eng in ('trail', 'hold30'):
            if eng == 'trail': legs = exits.simulate(bars, eidx, px, 'trail', {'stop': -0.25})
            else:
                xt = eb['t'] + datetime.timedelta(minutes=30); xb = next((b for b in bars[eidx + 1:] if b['t'] >= xt), None) or (bars[-1] if len(bars) > eidx + 1 else None)
                legs = [(1.0, (xb['vw'] or xb['c']), xb['t'], 'HOLD30')] if xb else []
            if not legs: continue
            for model in ('mid', 'spread'):
                r = costs.settle(TK, eb, px, legs, model); rec[f'{eng}_{model}_ret'] = r['ret']; rec[f'{eng}_{model}_usd'] = r['dollars']
            rec[f'{eng}_reason'] = '+'.join(l[3] for l in legs); rec[f'{eng}_hold_min'] = (max(l[2] for l in legs) - eb['t']).total_seconds() / 60
        out.append(rec)
    return out
tr = pd.DataFrame(run(sigs, 'rule') + run(base, 'baseline')); tr.to_csv(os.path.join(OUT, f'trade_rule_{TK}_{FEAT}.csv'), index=False, float_format='%.5g')
summ = []
for label, g in tr.groupby('set'):
    for eng in ('trail', 'hold30'):
        for model in ('mid', 'spread'):
            col = f'{eng}_{model}_ret'; g2 = g.dropna(subset=[col]); mc = mean_ci(g2[col].values, g2.date.values)
            summ.append(dict(set=label, exit=eng, cost=model, n=mc['n'], mean_ret=mc['mean'], lo=mc['lo'], hi=mc['hi'], p=mc['p'], win=float((g2[col] > 0).mean()), mean_usd=float(g2[f'{eng}_{model}_usd'].mean()), median_hold=float(g2[f'{eng}_hold_min'].median()), prem_pct_spot=float(g2.prem_pct_spot.median())))
    for side, gs in g.groupby('side'):
        mc = mean_ci(gs['trail_spread_ret'].dropna().values, gs.dropna(subset=['trail_spread_ret']).date.values)
        summ.append(dict(set=label + '_' + side, exit='trail', cost='spread', n=mc['n'], mean_ret=mc['mean'], lo=mc['lo'], hi=mc['hi'], p=mc['p'], win=float((gs.trail_spread_ret > 0).mean()), mean_usd=float(gs.trail_spread_usd.mean()), median_hold=float(gs.trail_hold_min.median()), prem_pct_spot=float(gs.prem_pct_spot.median())))
sm = pd.DataFrame(summ); sm.to_csv(os.path.join(OUT, f'trade_rule_{TK}_{FEAT}_summary.csv'), index=False, float_format='%.5g')
pd.set_option('display.width', 250); print(sm.to_string()); print(data.STATS)
