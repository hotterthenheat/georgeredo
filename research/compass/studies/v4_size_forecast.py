"""V4 (amendment A11): does a price-action forecast of the 10:00 -> 15:50 move beat the same-day straddle's implied move?

  python3 -I v4_size_forecast.py forecast            # per-name forecasts from one-minute bars -> forecasts.parquet
  python3 -I v4_size_forecast.py index               # SPY/QQQ/IWM same-day straddles, both sides (exploratory family)
  python3 -I v4_size_forecast.py analyze [--holdout] # V4s, V4l, V4e on V3's trades; the index family alongside
"""
import datetime as dt, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import numpy as np, polars as pl
from engine import bars as B, calendar as cal
import v3_single_name_0dte as v3

SP = v3.SP
OUT = os.path.join(HERE, '..', 'results', 'v1', 'v4_size_forecast'); os.makedirs(OUT, exist_ok=True)
SPLITS = [x for k in (2, 3, 4, 5, 8, 10, 15, 20, 25, 30, 40, 50) for x in (k, 1 / k)]
INDEX = {'SPY': dt.date(2022, 11, 11), 'QQQ': dt.date(2022, 11, 11), 'IWM': dt.date(2024, 4, 19)}
I_DEV, I_VAL = dt.date(2024, 6, 30), dt.date(2025, 6, 30)        # index family splits (exploratory)
log = v3.log

def bars_of(name):
    """one-minute bars for a name; META is FB before 2022-06-09 (A10.3); index ETFs from the research dataset"""
    if name in INDEX: return B.load_minutes(name, f'{SP}/theta/data/underlying', dt.date(2017, 6, 1), v3.END)
    parts = []
    for r, a, b in v3.roots(name):
        if os.path.isdir(os.path.join(v3.CACHE, 'underlying', r)): parts.append(B.load_minutes(r, os.path.join(v3.CACHE, 'underlying'), a, b))
    return pl.concat(parts, how='vertical_relaxed') if parts else None

def session_rows(name):
    df = bars_of(name)
    if df is None or df.height == 0: return None
    rows = []
    for (d,), g in df.group_by(['session'], maintain_order=True):
        if cal.is_early_close(d) or not v3.usable(g): continue                # A10.4
        mins = g['minute'].to_numpy(); cls = g['close'].to_numpy()
        def at(m):                                                         # the last bar's close at or before minute m
            k = np.searchsorted(mins, m, side='right') - 1
            return float(cls[k]) if k >= 0 else None
        o0 = float(g['open'][0]) if mins[0] <= 4 else None                 # the session's first bar opens by 09:34
        pts = [at(m) for m in range(29, 380, 5)]                           # 10:00, 10:05, ..., 15:50 (71 prices)
        opn = [o0] + [at(m) for m in range(4, 30, 5)]                      # 09:30 open, 09:35, ..., 10:00
        if o0 is None or any(p is None or not np.isfinite(p) for p in pts + opn): continue
        lr = np.diff(np.log(pts)); lo = np.diff(np.log(opn))
        rows.append(dict(name=name, session=d, rv=float(np.sum(lr ** 2)), rvo=float(np.sum(lo ** 2)), open=o0, last=float(g['close'][-1]),
                         p10=pts[0], p1550=pts[-1]))
    s = pl.DataFrame(rows).sort('session')
    prev_last = s['last'].shift(1).to_list(); ses = s['session'].to_list()
    g, flag = [], []
    for i, (o, d) in enumerate(zip(s['open'].to_list(), ses)):
        ok = i > 0 and cal.prev_session(d) == ses[i - 1]
        r = o / prev_last[i] if ok else np.nan
        g.append(np.log(r) if ok else np.nan)
        flag.append(bool(ok and any(abs(r / f - 1) <= 0.10 for f in SPLITS)))
    s = s.with_columns(pl.Series('g', g), pl.Series('split', flag))
    # A11: split sessions and the session after them leave fits and lags
    bad = s['split'].to_list(); bad = [b or (i > 0 and bad[i - 1]) for i, b in enumerate(bad)]
    return s.with_columns(pl.Series('skip', bad))

def features(s):
    rv = s['rv'].to_numpy(); skip = s['skip'].to_numpy(); out = []
    good = [i for i in range(len(rv)) if not skip[i] and rv[i] > 0]
    pos = {i: k for k, i in enumerate(good)}
    for i in good:
        k = pos[i]
        if k < 22: out.append(None); continue
        h = [rv[good[j]] for j in range(k - 22, k)]
        out.append((np.log(h[-1]), np.log(np.mean(h[-5:])), np.log(np.mean(h)), i))
    return good, out

def forecast():
    allrows = []
    for name in v3.NAMES + list(INDEX):
        s = session_rows(name)
        if s is None: log(name, 'no bars'); continue
        good, feats = features(s)
        rvo = s['rvo'].to_numpy(); g = s['g'].to_numpy(); rv = s['rv'].to_numpy(); ses = s['session'].to_list()
        recs = [(f[3], f[0], f[1], f[2]) for f in feats if f is not None]
        first = ses[0]
        for y in range(2019, 2027):
            cut = dt.date(y, 1, 1)
            if (cut - first).days < 730: continue
            fit = [r for r in recs if ses[r[0]] < cut and rvo[r[0]] > 0 and np.isfinite(g[r[0]])]
            if len(fit) < 250: continue
            c = float(np.median([g[r[0]] ** 2 for r in fit]))
            X = np.array([[1, r[1], r[2], r[3], np.log(rvo[r[0]]), np.log(g[r[0]] ** 2 + c)] for r in fit]); Y = np.array([np.log(rv[r[0]]) for r in fit])
            beta, *_ = np.linalg.lstsq(X, Y, rcond=None); s2 = float(np.mean((Y - X @ beta) ** 2))
            for r in recs:
                d = ses[r[0]]
                if d.year != y or rvo[r[0]] <= 0 or not np.isfinite(g[r[0]]): continue
                x = np.array([1, r[1], r[2], r[3], np.log(rvo[r[0]]), np.log(g[r[0]] ** 2 + c)])
                erv = float(np.exp(x @ beta + s2 / 2))
                allrows.append(dict(name=name, session=d, fit_year=y, fit_n=len(fit), rv=float(rv[r[0]]), erv=erv, m_hat=float(np.sqrt(2 / np.pi * erv)),
                                    realised_move=abs(s['p1550'][r[0]] / s['p10'][r[0]] - 1), b=json.dumps([round(float(v), 4) for v in beta])))
        log(name, 'forecasts', sum(1 for r in allrows if r['name'] == name))
    F = pl.DataFrame(allrows); F.write_parquet(os.path.join(OUT, 'forecasts.parquet'))
    # out-of-sample calibration of the forecast itself (no option data)
    F2 = F.with_columns((pl.col('rv').log() - pl.col('erv').log()).alias('e'))
    print(F2.group_by('name').agg(pl.len(), pl.corr(pl.col('rv').log(), pl.col('erv').log()).pow(2).alias('r2_ln_rv'),
                                  pl.col('e').mean().alias('mean_ln_err')).sort('name'))

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'forecast': forecast()
