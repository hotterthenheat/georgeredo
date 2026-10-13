"""Test 3: dark-pool prints (90-session sample x 3 tickers). Per minute t (10:00-15:30) over the trailing 30 minutes (t-29..t):
  D1  = notional of prints with price >= NBBO mid / total notional        (buy-initiated share, literal definition; centred at 0.5)
  D1x = (notional price > mid  -  notional price < mid) / total notional   (strict; prints exactly at the mid are neutral)
  D2  = notional(price >= mid) - notional(price < mid)                      ($ net notional)
vs forward 30/60-minute log returns of the underlying. Prints are binned by executed_at (ET) minute; a print in minute t is treated as known at the close of t."""
import pandas as pd, numpy as np, json, time
from common import *
from stats import cell, pooled_ic, quintiles
S = json.load(open(os.path.join(OUT, 'samples.json')))['dp_sessions']
rows = []; t0 = time.time()
def tod(m): return '09:45-10:30' if m < 60 else '10:30-12:00' if m < 150 else '12:00-14:00' if m < 270 else '14:00-15:30'
for tk in TICKERS:
    for d in S:
        prints, pages, trunc = darkpool_rth(tk, d); rth, _ = data.underlying_bars(tk, d)
        if len(rth) < 380 or len(prints) < 100: continue
        c = np.full(390, np.nan)
        for b in rth:
            m = (b['t'].hour - 9) * 60 + b['t'].minute - 30
            if 0 <= m < 390: c[m] = b['c']
        A = np.zeros((390, 3))  # buy(>mid), sell(<mid), at-mid notional
        for r in prints:
            t = to_et(r['executed_at']); m = (t.hour - 9) * 60 + t.minute - 30
            px, bid, ask = f(r['price']), f(r['nbbo_bid']), f(r['nbbo_ask']); notional = f(r['premium'])
            if not (0 <= m < 390) or not np.isfinite(px * bid * ask * notional): continue
            mid = (bid + ask) / 2
            A[m, 0 if px > mid else 1 if px < mid else 2] += notional
        cs = np.vstack([np.zeros((1, 3)), np.cumsum(A, 0)])
        pdd = prev_day(d); flip = (data.gex_levels(tk, pdd) if pdd else {}).get('gamma_flip')
        for m in range(30, 361):
            w = cs[m + 1] - cs[m - 29]; tot = w.sum()
            if tot <= 0 or not np.isfinite(c[m]): continue
            rec = dict(ticker=tk, date=d, minute=m, spot=c[m], D1=(w[0] + w[2]) / tot, D1x=(w[0] - w[1]) / tot, D2=(w[0] + w[2]) - w[1], tot30=tot,
                       regime=('POS' if c[m] > flip else 'NEG') if flip else '', tod=tod(m))
            for h in (30, 60): rec[f'r{h}'] = np.log(c[m + h] / c[m]) if m + h < 390 and np.isfinite(c[m + h]) else np.nan
            rows.append(rec)
    print(tk, len(rows), round(time.time() - t0), 's', flush=True)
df = pd.DataFrame(rows); df.to_csv(os.path.join(OUT, 'panel_darkpool.csv.gz'), index=False, float_format='%.6g')
main = []; cond = []
for tk in TICKERS:
    d = df[df.ticker == tk]
    for ft in ('D1', 'D1x', 'D2'):
        x = d[ft].values - (0.5 if ft == 'D1' else 0.0)
        for h in (30, 60):
            main.append(dict(test='darkpool', ticker=tk, feature=ft, horizon=h, **cell(x, d[f'r{h}'].values, d.date.values, B=2000)))
            for cname, vals in (('regime', ('POS', 'NEG')), ('tod', ('09:45-10:30', '10:30-12:00', '12:00-14:00', '14:00-15:30'))):
                for v in vals:
                    s = d[d[cname] == v]; xs = s[ft].values - (0.5 if ft == 'D1' else 0.0)
                    rr = pooled_ic(xs, s[f'r{h}'].values, s.date.values, B=1000); qq = quintiles(xs, s[f'r{h}'].values, s.date.values, B=1000); qq.pop('qmeans')
                    cond.append(dict(ticker=tk, feature=ft, horizon=h, condition=cname, value=v, **rr, **qq))
pd.DataFrame(main).to_csv(os.path.join(OUT, 'dp_ic_main.csv'), index=False, float_format='%.5g')
pd.DataFrame(cond).to_csv(os.path.join(OUT, 'dp_ic_conditional.csv'), index=False, float_format='%.5g')
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
print(pd.DataFrame(main)[['ticker', 'feature', 'horizon', 'n', 'days', 'ic', 'lo', 'hi', 'p', 'q1_bps', 'q5_bps', 'spread', 'sp_lo', 'sp_hi', 'hr_top', 'hr_bot', 'sign_agree']].to_string())
cv = pd.read_csv(os.path.join(OUT, 'darkpool_coverage.csv')); cv['dp_share_of_volume'] = cv.dp_shares / cv.bar_volume; cv['at_mid_share'] = cv.at_mid / cv.prints
print(cv.groupby('ticker')[['prints', 'pages', 'dp_share_of_volume', 'at_mid_share']].describe().T.to_string())
print('truncated days', int(cv.truncated.sum()), 'no_nbbo prints', int(cv.no_nbbo.sum()), 'ticker-days', len(cv))
c2 = pd.DataFrame(cond); c2['z'] = c2.ic / c2.se; print(c2.reindex(c2.z.abs().sort_values(ascending=False).index)[['ticker', 'feature', 'horizon', 'condition', 'value', 'n', 'ic', 'lo', 'hi', 'p', 'spread']].head(8).to_string()); print('dp conditional cells', len(c2), 'nominal p<0.05', int((c2.p < 0.05).sum()))
