"""Build the ticker-minute panel (signed flow features from net-prem-ticks, forward returns, GEX regime, time-of-day) and the 5-minute market-tide panel.
Feature definitions (window = last 15 one-minute flow bars t-14..t, all known at the close of minute t):
  F1  = sum(net_call_premium - net_put_premium)                        [$, bullish > 0]
  F2  = [(call_ask - call_bid) - (put_ask - put_bid)] / (call_ask + call_bid + put_ask + put_bid)   [signed directional ask-minus-bid volume share]
  F2u = [(call_ask + put_ask) - (call_bid + put_bid)] / same denominator   [unsigned 'aggressor' share, not directional]
  F3  = sum(net_delta)  (= change of cumulative net delta over 15 minutes)
Forward returns r_h = ln(close[t+h] / close[t]) on the underlying's 1-minute RTH bars, h in {15,30,60}; t in 09:45..15:30 and t+h <= 15:59.
Regime: POS if close[t] > prior session's gamma_flip else NEG (prior session's gex-levels, no look-ahead).
Market tide: 5-minute rows stamped T hold the cumulative value through T+4:59 (verified against the 1-minute series), so row T is aligned to the
underlying bar closing at T+4:59 ('tradable'); the 'contemp' alignment (bar closing at T-0:01) is kept only as a non-tradable reference."""
import numpy as np, pandas as pd, time, csv
from common import *
SHORT_DAYS = {'2025-07-03', '2025-11-28', '2025-12-24'}
H = (15, 30, 60)
def tod(m):
    return '09:45-10:30' if m < 60 else '10:30-12:00' if m < 150 else '12:00-14:00' if m < 270 else '14:00-15:30'
rows = []; tide_rows = []; t0 = time.time(); skipped = []
for tk in TICKERS:
    for d in DAYS:
        if d in SHORT_DAYS: continue
        rth, _ = data.underlying_bars(tk, d); npt = net_prem_ticks(tk, d)
        if len(rth) < 380 or len(npt) < 300: skipped.append((tk, d, len(rth), len(npt))); continue
        c = np.full(390, np.nan)
        for b in rth:
            m = (b['t'].hour - 9) * 60 + b['t'].minute - 30
            if 0 <= m < 390: c[m] = b['c']
        A = np.zeros((390, 7)); have = np.zeros(390, bool)
        for r in npt:
            t = to_et(r['tape_time']); m = (t.hour - 9) * 60 + t.minute - 30
            if 0 <= m < 390:
                A[m] = [f(r['net_call_premium']), f(r['net_put_premium']), r.get('call_volume_ask_side') or 0, r.get('call_volume_bid_side') or 0,
                        r.get('put_volume_ask_side') or 0, r.get('put_volume_bid_side') or 0, f(r['net_delta'])]; have[m] = True
        A = np.nan_to_num(A); cs = np.vstack([np.zeros((1, 7)), np.cumsum(A, 0)]); hv = np.concatenate([[0], np.cumsum(have)])
        pdd = prev_day(d); gex = data.gex_levels(tk, pdd) if pdd else {}; flip = gex.get('gamma_flip')
        for m in range(15, 361):
            if hv[m + 1] - hv[m - 14] < 12 or not np.isfinite(c[m]): continue
            w = cs[m + 1] - cs[m - 14]
            den = w[2] + w[3] + w[4] + w[5]
            rec = dict(ticker=tk, date=d, minute=m, t_et=f'{9 + (m + 30) // 60:02d}:{(m + 30) % 60:02d}', spot=c[m], F1=w[0] - w[1],
                       F2=((w[2] - w[3]) - (w[4] - w[5])) / den if den > 0 else np.nan, F2u=((w[2] + w[4]) - (w[3] + w[5])) / den if den > 0 else np.nan, F3=w[6],
                       regime=('POS' if c[m] > flip else 'NEG') if flip else '', tod=tod(m))
            for h in H: rec[f'r{h}'] = np.log(c[m + h] / c[m]) if m + h < 390 and np.isfinite(c[m + h]) else np.nan
            rows.append(rec)
        if tk == 'SPY':
            V = {}
            for r in market_tide(d):
                t = to_et(r['timestamp']); m = (t.hour - 9) * 60 + t.minute - 30
                if 0 <= m < 390: V[m] = f(r['net_call_premium']) - f(r['net_put_premium'])
            for m in range(30, 390, 5):
                if m not in V or m - 30 not in V: continue
                for align, j in (('tradable', m + 4), ('contemp', m - 1)):
                    if j >= 390 or not np.isfinite(c[j]): continue
                    rec = dict(date=d, minute=m, t_et=f'{9 + (m + 30) // 60:02d}:{(m + 30) % 60:02d}', align=align, spot=c[j], T_level=V[m], T_chg30=V[m] - V[m - 30],
                               regime=('POS' if c[j] > flip else 'NEG') if flip else '', tod=tod(j))
                    for h in (30, 60): rec[f'r{h}'] = np.log(c[j + h] / c[j]) if j + h < 390 and np.isfinite(c[j + h]) else np.nan
                    tide_rows.append(rec)
    print(tk, 'rows', len(rows), round(time.time() - t0), 's', flush=True)
df = pd.DataFrame(rows); df.to_csv(os.path.join(OUT, 'panel_flow.csv.gz'), index=False, float_format='%.6g')
pd.DataFrame(tide_rows).to_csv(os.path.join(OUT, 'panel_tide.csv.gz'), index=False, float_format='%.6g')
print('skipped', skipped); print(df.groupby('ticker').size()); print(df[['F1', 'F2', 'F2u', 'F3', 'r15', 'r30', 'r60']].describe().T)
