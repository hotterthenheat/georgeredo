#!/usr/bin/env python3
"""
parity_t2_spy.py — does the tracker's live feature code (scripts/vol_model.py) reproduce Hypothesis E's model inputs?

Part 1 (the port): every feature rebuilt by vol_model.features_at from the SAME Theta Data inputs Hypothesis D/E read
(the minute bars, the VIX prints and the chain on disk, RAW) for N sessions, against out/minutes_SPY_all.parquet.
Part 2 (UW's bars): the session's own bars from Unusual Whales (/api/stock/SPY/ohlc/1m?date=D, two GETs on 2026-10-21,
saved as data_recorder/parity/uw_<D>.json — git-ignored, vendor data stays out of the repo; PARITY_UW_DIR moves it) in
place of Theta's — everything else as in part 1 (the sessions before, from Theta:
rebuilding 20 sessions before each from UW would take 20 calls a session) — against the same rows; the max difference
per feature and whether the decile (both frozen models) agrees, at every scan minute 09:35 .. 15:30.
  nice -n 10 env POLARS_MAX_THREADS=1 python3 -I scripts/models/parity/parity_t2_spy.py [N_PORT_SESSIONS]
"""
import datetime as dt, json, math, os, sys
import numpy as np, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, 'scripts'))
import vol_model as V  # noqa: E402
RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
MIN = os.path.join(REPO, 'research_notes', 'Compass phase 3', 'hyp_e_short_premium_lift', 'out', 'minutes_SPY_all.parquet')
FEATS = list(V.FrozenModel.load(V.FULL).features)
UW_DIR = os.environ.get('PARITY_UW_DIR') or os.path.join(REPO, 'data_recorder', 'parity')


def theta_bars(day):
    p = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{day}.parquet'))
    p = p.with_columns((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32) - 570 + 1).alias('m'))
    p = p.filter(pl.col('close').is_not_null() & (pl.col('m') >= 1) & (pl.col('m') <= 390))
    arr = {k: [V.NAN] * 391 for k in 'ohlcv'}
    for r in p.iter_rows(named=True):
        for k, col in zip('ohlcv', ('open', 'high', 'low', 'close', 'volume')):
            arr[k][r['m']] = float(r[col]) if r[col] is not None else V.NAN
    arr['n'] = p.height
    arr['last_m'] = int(p['m'].max()) if p.height else None
    return arr


def theta_vix(day):
    f = os.path.join(RAW, 'data', 'index', 'VIX', f'{day}.parquet')
    if not os.path.exists(f):
        return None, None
    p = pl.read_parquet(f).with_columns((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32) - 570).alias('m'))
    p = p.filter(pl.col('price').is_not_null() & (pl.col('m') >= 0) & (pl.col('m') <= 390))
    return V.vix_array([(int(m), float(x)) for m, x in zip(p['m'], p['price'])]), p


def theta_quotes(day, m):
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', 'SPY', f'{day}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    c = c.with_columns((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32) - 570).alias('m'))
    c = c.filter((pl.col('m') >= 1) & (pl.col('m') <= 390) & pl.col('bid').is_not_null() & pl.col('ask').is_not_null()
                 & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0) & (pl.col('ask') > 0))
    allk = set(float(k) for k in c['strike'].unique())
    q = {k: [None, None] for k in allk}
    for r in c.filter(pl.col('m') == m).iter_rows(named=True):
        q[float(r['strike'])][0 if r['right'] == 'CALL' else 1] = (round(r['bid'], 4), round(r['ask'], 4))
    # a strike quoted at some minute but not at m stays in the list with no sides (chain_arrays' strike list)
    return {k: tuple(v) for k, v in q.items()}


def sessions():
    return sorted(f[:10] for f in os.listdir(os.path.join(RAW, 'data', 'underlying', 'SPY')) if f.endswith('.parquet'))


_SUM = {}


def summary(day):
    if day not in _SUM:
        _SUM[day] = V.day_summary(theta_bars(day))
    return _SUM[day]


def table_for(day, all_days):
    i = all_days.index(day)
    prior = []                                       # the day table holds only sessions with >= 30 bars (a holiday's file drops out)
    j = i - 1
    while j >= 0 and len(prior) < 20:
        s = summary(all_days[j])
        if s is not None:
            prior.insert(0, s)
        j -= 1
    return V.day_table_inputs(prior)


def vix_prev_close(day, vdays):
    i = vdays.index(day) if day in vdays else None
    if not i:
        return None
    a, _ = theta_vix(vdays[i - 1])
    v = [x for x in a if not math.isnan(x)]
    return v[-1] if v else None


def rebuild(day, bars, all_days, vdays, ref, with_straddle_from_chain=False):
    table = table_for(day, all_days)
    vix, _ = theta_vix(day)
    vp = vix_prev_close(day, vdays)
    out = []
    for r in ref.filter(pl.col('session') == dt.date.fromisoformat(day)).iter_rows(named=True):
        m = r['m']
        st = r['straddle'] if r['straddle'] is not None else V.NAN
        if with_straddle_from_chain:
            Sm = V.ffill(bars['c'])[m]
            k, st = V.atm_straddle(theta_quotes(day, m), Sm)
        f = V.features_at(m, bars, table, vix, vp, st)
        out.append((r, f))
    return out


def compare(pairs, models):
    diffs = {k: 0.0 for k in FEATS}
    worst = {}
    agree = {mm.name: 0 for mm in models}
    n = 0
    for r, f in pairs:
        n += 1
        for k in FEATS:
            a, b = r[k], f[k]
            a = V.NAN if a is None else float(a)
            if math.isnan(a) and math.isnan(b):
                continue
            d = abs(a - b) if not (math.isnan(a) or math.isnan(b)) else math.inf
            if d > diffs[k]:
                diffs[k] = d
                worst[k] = (str(r['session']), r['m'], a, b)
        for mm in models:
            ra = {k: (V.NAN if r[k] is None else float(r[k])) for k in mm.features}
            if mm.score(ra)[1] == mm.score(f)[1]:
                agree[mm.name] += 1
    return n, diffs, worst, agree


def main():
    nport = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    ref = pl.read_parquet(MIN)
    all_days = sessions()
    vdays = sorted(f[:10] for f in os.listdir(os.path.join(RAW, 'data', 'index', 'VIX')) if f.endswith('.parquet'))
    models = [V.FrozenModel.load(V.FULL), V.FrozenModel.load(V.NOVIX)]
    have = sorted(str(d) for d in ref['session'].unique())
    rng = np.random.default_rng(7)
    port_days = sorted(rng.choice(have[25:], size=nport, replace=False).tolist()) + ['2026-10-08', '2026-10-09']
    lines = ['# parity_t2_spy.py — ' + dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), '']
    lines.append(f'## Part 1: the port — Theta inputs through vol_model.features_at, {len(port_days)} sessions ({", ".join(port_days)}), every scan minute; the straddle from the Theta chain through vol_model.atm_straddle')
    pairs = []
    for d in port_days:
        pairs += rebuild(d, theta_bars(d), all_days, vdays, ref, with_straddle_from_chain=True)
    n, diffs, worst, agree = compare(pairs, models)
    lines.append(f'rows {n}; decile agreement: ' + ', '.join(f'{k} {v}/{n}' for k, v in agree.items()))
    lines.append('max |difference| by feature: ' + ', '.join(f'{k} {diffs[k]:.3g}' for k in FEATS))
    for d in ('2026-10-09', '2026-10-08'):
        f = os.path.join(UW_DIR, f'uw_{d}.json')
        body = json.load(open(f))['body']
        rows = body['data'] if isinstance(body, dict) else body
        ub, tb = V.bars_from_uw(rows, d), theta_bars(d)
        lines += ['', f'## Part 2: {d} — UW\'s bars for the session (ohlc/1m, {ub["n"]} regular bars) against Theta\'s ({tb["n"]})']
        bd = {}
        for k in 'ohlcv':
            ds = [abs(ub[k][m] - tb[k][m]) for m in range(1, 391) if not (math.isnan(ub[k][m]) or math.isnan(tb[k][m]))]
            bd[k] = max(ds) if ds else float('nan')
        vr = [ub['v'][m] / tb['v'][m] for m in range(1, 391) if not (math.isnan(ub['v'][m]) or math.isnan(tb['v'][m])) and tb['v'][m] > 0]
        nmis = sum(1 for m in range(1, 391) if math.isnan(ub['c'][m]) != math.isnan(tb['c'][m]))
        cl = sum(1 for m in range(1, 391) if not (math.isnan(ub['c'][m]) or math.isnan(tb['c'][m])) and abs(ub['c'][m] - tb['c'][m]) > 0.005)
        lines.append(f'bars: max |diff| open {bd["o"]:.4g} high {bd["h"]:.4g} low {bd["l"]:.4g} close {bd["c"]:.4g} volume {bd["v"]:.6g}; '
                     f'closes differing by more than half a cent {cl} of 390; minutes present in one and not the other {nmis}; '
                     f'UW/Theta volume ratio a minute: median {np.median(vr):.4f}, min {min(vr):.4f}, max {max(vr):.4f}')
        pairs = rebuild(d, ub, all_days, vdays, ref)
        n, diffs, worst, agree = compare(pairs, models)
        lines.append(f'scan minutes {n}; decile agreement: ' + ', '.join(f'{k} {v}/{n}' for k, v in agree.items()))
        lines.append('max |difference| by feature (UW bars vs the parquet): ' + ', '.join(f'{k} {diffs[k]:.3g}' for k in FEATS))
        for k in FEATS:
            if diffs[k] > 1e-9:
                lines.append(f'  {k}: worst at m={worst[k][1]} parquet {worst[k][2]:.6g} vs UW {worst[k][3]:.6g}')
        dis = []
        for r, fx in pairs:
            for mm in models:
                ra = {k: (V.NAN if r[k] is None else float(r[k])) for k in mm.features}
                a, b = mm.score(ra), mm.score(fx)
                if a[1] != b[1]:
                    dis.append(f'{mm.name} m={r["m"]} decile {a[1]} -> {b[1]} (score {a[0]:.4f} -> {b[0]:.4f})')
        lines.append('decile disagreements: ' + ('; '.join(dis) if dis else 'none'))
        d1 = [(r['m'], mm.score({k: (V.NAN if r[k] is None else float(r[k])) for k in mm.features})[1], mm.score(fx)[1]) for r, fx in pairs for mm in models[:1] if r['m'] in (210, 240, 270, 300, 330)]
        lines.append('candidate 3 minutes (13:00 .. 15:00), full model decile parquet -> UW: ' + ', '.join(f'm{m} {a}->{b}' for m, a, b in d1))
    text = '\n'.join(lines) + '\n'
    open(os.path.join(HERE, 'parity_result.txt'), 'w').write(text)
    print(text)


if __name__ == '__main__':
    main()
