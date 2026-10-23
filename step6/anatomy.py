"""Step 6b, Part 1: how the runners' moves happened, every class side by side (PREREG section 3). Descriptive only.

Writes step6/out/:
- classes.csv: how many trades fall in each class and band, by window, period and product.
- how.csv: for each window and class (the exclusive bands and the nested R40 / R100 / R500), every Part 1 measure; the
  column `when` says whether the measure was knowable at the buy or only after the fact.
- how_by_time.csv: the classes' rates by buy time and window.
- r500_cases.csv: the 30 largest peaks in H1530, with the underlying's path.
- runner_days.csv: how many days each class's trades come from, and the share on the busiest 5 and 20 days.
  python3 -I step6/anatomy.py
"""
import os, sys
import numpy as np, polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
from step6.data import load, OUT, BANDS, CLASSES, WINDOWS, TIMES   # noqa: E402

def q(x, p):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return float(np.percentile(x, p)) if x.size else float('nan')

def share(b):
    b = np.asarray(b, float); b = b[np.isfinite(b)]
    return float(b.mean()) if b.size else float('nan')

def measures(G, w):
    """one dict of measures for a group of trades G and window w"""
    a = G['entry_ask'].to_numpy(); n = G.height
    pk = G[f'peak_{w}'].to_numpy(); gain = pk - a
    o = {'trades': n}
    def add(name, when, med=None, lo=None, hi=None, val=None):
        o[name] = (when, med, lo, hi, val)
    mult = G[f'mult_{w}'].to_numpy()
    add('peak bid / ask paid', 'after', q(mult, 50), q(mult, 25), q(mult, 75))
    mins = (G[f'peak_min_{w}'] - G['entry_minute']).to_numpy().astype(float); mins[G[f'peak_min_{w}'].to_numpy() < 0] = np.nan
    add('minutes from buy to peak', 'after', q(mins, 50), q(mins, 25), q(mins, 75))
    for col, lab in (('mv_em', 'underlying move to peak, in remaining moves at the buy'), ('mv_em0', 'underlying move to peak, in 9:31 straddles'),
                     ('mv_pct', 'underlying move to peak, %'), ('mv_pts', 'underlying move to peak, points')):
        v = G[f'{col}_{w}'].to_numpy(); add(lab, 'after', q(v, 50), q(v, 25), q(v, 75))
    mv = G[f'mv_em_{w}'].to_numpy()
    add('share where the underlying moved the contract\'s way', 'after', val=share(mv > 0))
    b5 = G[f'burst5_{w}'].to_numpy(); b1 = G[f'burst1_{w}'].to_numpy()
    add('largest 1-minute stretch, share of the move', 'after', q(b1, 50), q(b1, 25), q(b1, 75))
    add('largest 5-minute stretch, share of the move', 'after', q(b5, 50), q(b5, 25), q(b5, 75))
    add('share "burst" (5-minute stretch >= 60% of the move)', 'after', val=share(np.where(np.isfinite(b5), b5 >= 0.6, np.nan)))
    # the split of the gain (bid at peak - ask paid), as % of the ask paid: mean and median
    dp, dv, dt_, ds = (G[f'{c}_{w}'].to_numpy() for c in ('dprice', 'dvol', 'dtime', 'dspread'))
    ok = np.isfinite(dp) & np.isfinite(dv) & np.isfinite(dt_) & np.isfinite(ds) & np.isfinite(gain)
    add('repricing split available (IV solved at both ends)', 'after', val=float(ok.mean()) if n else np.nan)
    tot = gain[ok].sum()
    for arr, lab in ((dp, 'price (delta+gamma)'), (dv, 'IV (vega)'), (dt_, 'time (theta)'), (ds, 'spread paid')):
        r = arr[ok] / a[ok] * 100
        add(f'gain from {lab}, % of ask', 'after', q(r, 50), q(r, 25), q(r, 75), float(r.mean()) if r.size else np.nan)
        add(f'gain from {lab}, share of total gain', 'after', val=float(arr[ok].sum() / tot) if r.size and tot != 0 else np.nan)
    iv0 = G['iv_entry'].to_numpy() * 100; iv1 = G[f'iv_peak_{w}'].to_numpy() * 100
    add('IV at the buy (%, trading-time)', 'buy', q(iv0, 50), q(iv0, 25), q(iv0, 75))
    add('IV at the peak (%)', 'after', q(iv1, 50), q(iv1, 25), q(iv1, 75))
    add('IV change buy to peak (points)', 'after', q(iv1 - iv0, 50), q(iv1 - iv0, 25), q(iv1 - iv0, 75))
    em = G['entry_minute'].to_numpy()
    for k, lab in TIMES.items(): add(f'bought at {lab}', 'buy', val=share(em == k))
    pm = G[f'peak_min_{w}'].to_numpy().astype(float); pm[pm < 0] = np.nan
    add('peak clock (minutes after 9:30)', 'after', q(pm, 50), q(pm, 25), q(pm, 75))
    for col, lab in (('or', 'broke the opening range its way, buy to peak'), ('vwapx', 'crossed VWAP its way, buy to peak'),
                     ('newext', 'made a new session high (calls) / low (puts), buy to peak'),
                     ('rev', 'made a new session low (calls) / high (puts) after the buy, then reversed')):
        add(lab, 'after', val=share(G[f'{col}_{w}'].to_numpy().astype(float)))
    fx = G[f'flipx_{w}'].to_numpy().astype(float)
    add('crossed the prior session\'s UW gamma flip its way (where covered)', 'after', val=share(fx))
    add('UW flip covered', 'buy', val=float(np.isfinite(fx).mean()) if n else np.nan)
    rng = (G['day_hi'] - G['day_lo']).to_numpy(); rim = rng / G['straddle_open'].to_numpy()
    add('day range / 9:31 straddle', 'after', q(rim, 50), q(rim, 25), q(rim, 75))
    trend = np.abs((G['day_close'] - G['day_open']).to_numpy()) >= 0.5 * rng
    add('trend day (|close - open| >= half the range)', 'after', val=share(trend))
    dclose = (G['dir'] * (G['day_close'] - G['day_open'])).to_numpy()
    add('the day closed the contract\'s way (vs its open)', 'after', val=share(dclose > 0))
    g = G['gap_abs'].to_numpy(); add('|gap| %', 'buy', q(g, 50), q(g, 25), q(g, 75))
    dg = G['dgap'].to_numpy(); add('gap the contract\'s way, %', 'buy', q(dg, 50), q(dg, 25), q(dg, 75))
    v = G['vix'].to_numpy(); add('VIX at the buy', 'buy', q(v, 50), q(v, 25), q(v, 75))
    vc = (G['vix_close'] / G['vix_open'] - 1).to_numpy() * 100; add('VIX change over the session, %', 'after', q(vc, 50), q(vc, 25), q(vc, 75))
    ev = G['event'].to_numpy()
    for k in ('FOMC', 'CPI', 'NFP'): add(f'{k} day', 'buy', val=share(ev == k))
    fomc = ev == 'FOMC'
    add('FOMC day and the peak after 2:00 pm (share of FOMC trades)', 'after', val=share(pm[fomc] > 270) if fomc.any() else np.nan)
    add('calls', 'buy', val=share(G['is_call'].to_numpy() == 1))
    for p in ('SPX', 'SPY', 'QQQ', 'IWM'): add(f'product {p}', 'buy', val=share(G['product'].to_numpy() == p))
    x = G['x'].to_numpy(); add('moneyness x (remaining moves, OTM +)', 'buy', q(x, 50), q(x, 25), q(x, 75))
    pr = G['entry_ask'].to_numpy() * 100; add('price paid, $ a contract', 'buy', q(pr, 50), q(pr, 25), q(pr, 75))
    return o

def main():
    T = load()
    rows = []
    for w in WINDOWS:
        for per in ('all', 'pick', 'check'):
            P = T if per == 'all' else T.filter(pl.col('period') == per)
            for prod in ('all', 'SPX', 'SPY', 'QQQ', 'IWM'):
                X = P if prod == 'all' else P.filter(pl.col('product') == prod)
                n = X.height
                r = {'window': w, 'period': per, 'product': prod, 'trades': n}
                for b in BANDS: r[b] = (X[f'band_{w}'] == b).sum() / n if n else np.nan
                for c in CLASSES: r[c] = X[f'{c}_{w}'].sum() / n if n else np.nan
                rows.append(r)
    pl.DataFrame(rows).write_csv(os.path.join(OUT, 'classes.csv'))

    # how.csv: exclusive bands and nested classes, all periods together and apart
    hw = []
    for w in WINDOWS:
        groups = [(b, pl.col(f'band_{w}') == b) for b in BANDS] + [(f'{c} (nested)', pl.col(f'{c}_{w}')) for c in CLASSES]
        for per in ('all', 'pick', 'check'):
            P = T if per == 'all' else T.filter(pl.col('period') == per)
            for name, cond in groups:
                G = P.filter(cond)
                m = measures(G, w)
                for k, v in m.items():
                    if k == 'trades':
                        hw.append({'window': w, 'period': per, 'group': name, 'measure': 'trades', 'when': '', 'median': float(v), 'p25': None, 'p75': None, 'value': float(v)})
                    else:
                        when, med, lo, hi, val = v
                        hw.append({'window': w, 'period': per, 'group': name, 'measure': k, 'when': {'after': 'after the fact', 'buy': 'knowable at the buy'}[when],
                                   'median': med, 'p25': lo, 'p75': hi, 'value': val})
    pl.DataFrame(hw, schema_overrides={'median': pl.Float64, 'p25': pl.Float64, 'p75': pl.Float64, 'value': pl.Float64}).write_csv(os.path.join(OUT, 'how.csv'))

    # rates by buy time
    bt = []
    for w in WINDOWS:
        for per in ('pick', 'check'):
            P = T.filter(pl.col('period') == per)
            for k, lab in TIMES.items():
                X = P.filter(pl.col('entry_minute') == k); n = X.height
                if not n: continue
                r = {'window': w, 'period': per, 'buy': lab, 'trades': n, 'DUD': X[f'DUD_{w}'].sum() / n}
                for c in CLASSES: r[c] = X[f'{c}_{w}'].sum() / n
                mins = (X[f'peak_min_{w}'] - X['entry_minute']).filter(X[f'R40_{w}'])
                r['R40 median minutes to peak'] = float(mins.median()) if mins.len() else None
                bt.append(r)
    pl.DataFrame(bt).write_csv(os.path.join(OUT, 'how_by_time.csv'))

    # the 30 largest +500% runs (H1530)
    C = T.filter(pl.col('R500_1530')).sort('mult_1530', descending=True).head(30)
    hm = lambda m: f'{(570 + m) // 60 % 12 or 12}:{(570 + m) % 60:02d} {"am" if 570 + m < 720 else "pm"}'
    cases = []
    for r in C.iter_rows(named=True):
        pm = r['peak_min_1530']
        path = [float(v) for v in r['px_path'].split(',')]
        steps = (pm - r['entry_minute']) // 15 + 1
        cases.append({'date': r['date'], 'product': r['product'], 'side': r['right'].lower(), 'strike': r['strike'], 'bought': hm(r['entry_minute']),
                      'ask paid': r['entry_ask'], 'peak bid': r['peak_1530'], 'peak at': hm(pm), 'multiple': round(r['mult_1530'], 1),
                      'minutes': pm - r['entry_minute'], 'moneyness x': round(r['x'], 2), 'underlying at buy': r['px'],
                      'underlying at peak': r['spot_peak_1530'], 'move in remaining moves': round(r['mv_em_1530'], 2),
                      'move %': round(r['mv_pct_1530'], 2), 'IV buy %': round(100 * r['iv_entry'], 1) if r['iv_entry'] == r['iv_entry'] else None,
                      'IV peak %': round(100 * r['iv_peak_1530'], 1) if r['iv_peak_1530'] == r['iv_peak_1530'] else None,
                      'price part %': round(100 * r['dprice_1530'] / r['entry_ask']) if r['dprice_1530'] == r['dprice_1530'] else None,
                      'IV part %': round(100 * r['dvol_1530'] / r['entry_ask']) if r['dvol_1530'] == r['dvol_1530'] else None,
                      'time part %': round(100 * r['dtime_1530'] / r['entry_ask']) if r['dtime_1530'] == r['dtime_1530'] else None,
                      'event': r['event'], 'burst5': round(r['burst5_1530'], 2) if r['burst5_1530'] == r['burst5_1530'] else None,
                      'underlying every 15 min from the buy': ' '.join(f'{v:.2f}' for v in path[:steps + 1])})
    pl.DataFrame(cases).write_csv(os.path.join(OUT, 'r500_cases.csv'))
    # how concentrated the runners are by day: each class's trades on its busiest days
    dd = []
    for c, w in (('R40', 60), ('R100', 60), ('R500', 60), ('R40', 1530), ('R100', 1530), ('R500', 1530)):
        X = T.filter(pl.col(f'{c}_{w}'))
        g = X.group_by('date').len().sort('len', descending=True)
        n = X.height; nd = T['date'].n_unique()
        dd.append({'class': c, 'window': w, 'trades': n, 'days_with_one': g.height, 'days_in_sample': nd,
                   'share_on_top5_days': g['len'].head(5).sum() / n, 'share_on_top20_days': g['len'].head(20).sum() / n,
                   'top_days': ' '.join(f"{d} ({k})" for d, k in g.head(8).iter_rows())})
    pl.DataFrame(dd).write_csv(os.path.join(OUT, 'runner_days.csv'))
    print('written classes.csv, how.csv, how_by_time.csv, r500_cases.csv, runner_days.csv;', T.height, 'trades')

if __name__ == '__main__':
    main()
