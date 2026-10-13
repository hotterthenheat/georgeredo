"""Q3: first touch (close within 0.1 %) of the PRIOR-day call_wall / put_wall / gamma_magnet: next 30/60-min returns, close-vs-level (pin),
compared with random pseudo-levels drawn at the same |distance from the open| distribution (5 controls per real level)."""
import collections, random
from common import *
TOL = 0.001; rng = random.Random(3)
days = []
for tk in TICKERS:
    for d in DAYS:
        rth, _ = data.underlying_bars(tk, d)
        if len(rth) < 300: continue
        gex = data.gex_levels(tk, prior_day(d)); o = rth[0]['o'] if hhmm(rth[0]['t']) == 570 else None; p1555 = px_at(rth, 955)
        if o is None or p1555 is None: continue
        days.append((tk, d, rth, gex, o, p1555))
absd = collections.defaultdict(list)
for tk, d, rth, gex, o, p1555 in days:
    for lvl in ('call_wall', 'put_wall', 'gamma_magnet'):
        L = gex.get(lvl)
        if L: absd[(tk, lvl)].append(abs(L - o) / o)
def evaluate(rth, L, o, p1555):
    mins = np.array([hhmm(b['t']) for b in rth]); c = np.array([b['c'] for b in rth])
    near = np.abs(c - L) / L <= TOL
    if not near.any(): return dict(touched=0)
    i = int(np.argmax(near)); tm = int(mins[i]); px = float(c[i])
    def fwd(k):
        j = np.searchsorted(mins, tm + k, side='right') - 1
        return float(c[j] / px - 1) if tm + k <= 955 and mins[j] >= tm + k - 2 else float('nan')
    appr = np.sign(L - o) if abs(L - o) / o > TOL else 0.0
    r30, r60 = fwd(30), fwd(60)
    return dict(touched=1, touch_min=tm, touch_px=px, approach=appr, r30=r30, r60=r60, through30=(appr * r30 if appr else float('nan')), through60=(appr * r60 if appr else float('nan')),
                close_rel=(p1555 - L) / L * 100, abs_close_rel=abs(p1555 - L) / L * 100, pin25=int(abs(p1555 - L) / L <= 0.0025), pin50=int(abs(p1555 - L) / L <= 0.005),
                mfe_through=float(appr * ((c[i:].max() if appr > 0 else c[i:].min()) / px - 1)) if appr else float('nan'))
events = []
for tk, d, rth, gex, o, p1555 in days:
    for lvl in ('call_wall', 'put_wall', 'gamma_magnet'):
        L = gex.get(lvl)
        if not L: continue
        e = dict(kind='real', ticker=tk, date=d, level=lvl, L=L, d0_pct=(L - o) / o * 100, uncond_pin25=int(abs(p1555 - L) / L <= 0.0025)); e.update(evaluate(rth, L, o, p1555)); events.append(e)
        for rep in range(5):
            dd = rng.choice(absd[(tk, lvl)]); s = rng.choice((-1, 1)); Lc = o * (1 + s * dd)
            e = dict(kind='control', ticker=tk, date=d, level=lvl, L=Lc, d0_pct=s * dd * 100, uncond_pin25=int(abs(p1555 - Lc) / Lc <= 0.0025)); e.update(evaluate(rth, Lc, o, p1555)); events.append(e)
write_csv(OUT + '/q3_events.csv', events, fields=['kind', 'ticker', 'date', 'level', 'L', 'd0_pct', 'uncond_pin25', 'touched', 'touch_min', 'touch_px', 'approach', 'r30', 'r60', 'through30', 'through60', 'close_rel', 'abs_close_rel', 'pin25', 'pin50', 'mfe_through'])
rows = []
def stat(name, ev):
    out = dict(group=name, n_days=len(ev), touch_rate=float(np.mean([e['touched'] for e in ev])) if ev else float('nan'))
    g = np.array([e['date'] for e in ev]); out['uncond_pin25'] = float(np.mean([e['uncond_pin25'] for e in ev])); out['uncond_pin25_lo'], out['uncond_pin25_hi'] = boot_mean_ci([e['uncond_pin25'] for e in ev], g, 800)
    t = [e for e in ev if e['touched']]; out['n_touched'] = len(t)
    if len(t) >= 10:
        gt = np.array([e['date'] for e in t]); out['touch_min_median'] = float(np.median([e['touch_min'] for e in t]))
        for k in ('r30', 'r60', 'through30', 'through60', 'abs_close_rel', 'close_rel', 'pin25', 'pin50', 'mfe_through'):
            v = np.array([e[k] for e in t], float); ok = ~np.isnan(v)
            if ok.sum() < 10: continue
            mult = 1e4 if k in ('r30', 'r60', 'through30', 'through60', 'mfe_through') else 1
            lo, hi = boot_mean_ci(v[ok] * mult, gt[ok], 800); out[f'{k}_n'] = int(ok.sum()); out[f'{k}_mean'] = float(v[ok].mean() * mult); out[f'{k}_lo'] = lo; out[f'{k}_hi'] = hi
            if k in ('through30', 'through60'): out[f'{k}_pos_rate'] = float((v[ok] > 0).mean())
            if k == 'abs_close_rel': out[f'{k}_median'] = float(np.median(v[ok]))
    rows.append(out); return out
for lvl in ('call_wall', 'put_wall', 'gamma_magnet'):
    for kind in ('real', 'control'):
        stat(f'ALL|{lvl}|{kind}', [e for e in events if e['level'] == lvl and e['kind'] == kind])
        for tk in TICKERS: stat(f'{tk}|{lvl}|{kind}', [e for e in events if e['level'] == lvl and e['kind'] == kind and e['ticker'] == tk])
    # split by approach direction (from below / from above) for the real levels
    for ap, nm in ((1.0, 'from_below'), (-1.0, 'from_above')):
        stat(f'ALL|{lvl}|real|{nm}', [e for e in events if e['level'] == lvl and e['kind'] == 'real' and e.get('approach') == ap])
        stat(f'ALL|{lvl}|control|{nm}', [e for e in events if e['level'] == lvl and e['kind'] == 'control' and e.get('approach') == ap])
write_csv(OUT + '/q3_summary.csv', rows)
# real - control differences with daily-block bootstrap
diffs = []
for lvl in ('call_wall', 'put_wall', 'gamma_magnet'):
    re_ = [e for e in events if e['level'] == lvl and e['kind'] == 'real' and e['touched']]; co = [e for e in events if e['level'] == lvl and e['kind'] == 'control' and e['touched']]
    d = dict(level=lvl, n_real=len(re_), n_control=len(co))
    rngb = np.random.default_rng(5); dates = sorted({e['date'] for e in re_} | {e['date'] for e in co})
    byd_r = collections.defaultdict(list); byd_c = collections.defaultdict(list)
    for e in re_: byd_r[e['date']].append(e)
    for e in co: byd_c[e['date']].append(e)
    for k in ('through30', 'through60', 'abs_close_rel', 'pin25', 'r30'):
        def m(ev): v = np.array([e[k] for e in ev], float); v = v[~np.isnan(v)]; return v.mean() * (1e4 if k in ('through30', 'through60', 'r30') else 1) if len(v) else np.nan
        base = m(re_) - m(co); bs = []
        for _ in range(600):
            pick = rngb.choice(dates, len(dates)); bs.append(m([e for dd in pick for e in byd_r.get(dd, [])]) - m([e for dd in pick for e in byd_c.get(dd, [])]))
        d[f'{k}_diff'] = float(base); d[f'{k}_diff_lo'] = float(np.nanpercentile(bs, 2.5)); d[f'{k}_diff_hi'] = float(np.nanpercentile(bs, 97.5))
    diffs.append(d)
write_csv(OUT + '/q3_real_minus_control.csv', diffs)
for r in rows: print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
for r in diffs: print('DIFF', {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
