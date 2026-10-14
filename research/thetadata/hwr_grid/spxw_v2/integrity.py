#!/usr/bin/env python3
"""Work item 1 -- data integrity of the complete SPXW chains for the pre-registered grid.

For every regular session 2022-05-13 -> 2026-10-09 (TRAIN + TEST = T-E window + holdout) and every pre-registered entry minute
(10:00, 11:00, 13:00, 14:05 and the five committed random-entry minutes R1..R5), and every k in {0, 0.5, 1.0, 1.5}:
  * spot = SPX price stamped at the entry minute; ATM K0 = round(spot/5)*5 listed with usable call and put rows at that minute;
  * EM = ATM straddle mid; short call / put targets spot +- k*EM; wing targets spot +- (k+1)*EM;
  * the strike the simulator would trade ("nearest listed strike outward", sim._outward on the complete chain), its distance
    from the target, whether it has a usable quote row stamped at the entry minute, whether a short leg is bid 0,
    and whether that strike was stored in the original +-2 % band file (i.e. whether the round-2 study could have traded it);
  * the simulator's own verdict (sim.build) for the naked and winged structure.
Also, for EVERY minute 10:00..14:30 (the support of the random-entry baseline) and all 8 structure cells, sim.build's verdict
(counts; every non-ok case listed).
Per session: SHA-256 of the complete-chain file, rows, strikes, strike range, and a consistency check that every row of the
original band file is present in the complete file with identical bid/ask.
Outputs (results/): integrity_legs.csv.gz, integrity_minutes_nonok.csv, integrity_sessions.csv.gz, integrity_summary.json.
"""
import os, sys, json, hashlib, time
import numpy as np, pandas as pd, polars as pl
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim  # noqa: E402

RES = os.environ.get('RES_DIR', os.path.join(HERE, 'results')); os.makedirs(RES, exist_ok=True)
BAND_ROOT = sim.L.ROOT + '/chains'   # original +-2 % band dataset
RAND = sim.random_minutes()
ALLMIN = list(range(sim.hm2i('10:00'), sim.hm2i('14:30') + 1))


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


CACHE = os.environ.get('HWR_OUT', sim.L.SP + '/hwr_grid/spxw_v2') + '/integrity'


def one(d):
    """Cached per session (keyed by the chain file's SHA-256, so a re-fetched file is re-checked)."""
    import pickle
    fpath = sim.chain_path(d); h = sha(fpath)
    cp = os.path.join(CACHE, f'{d}.pkl')
    if os.path.exists(cp):
        res = pickle.load(open(cp, 'rb'))
        if res[0]['sha256'] == h: return res
    res = _one(d)
    os.makedirs(CACHE, exist_ok=True); pickle.dump(res, open(cp + '.tmp', 'wb')); os.replace(cp + '.tmp', cp)
    return res


def _one(d):
    fpath = sim.chain_path(d)
    sess = sim.Session(d)
    full = sim.chain_full(d)
    srow = dict(date=d, chain_src=sim.chain_source(d), sha256=sha(fpath), rows=full.height, strikes=int(full['strike'].n_unique()), kmin=float(full['strike'].min()),
                kmax=float(full['strike'].max()), settle_flag=sess.settle_flag, cboe_close=sess.S, spx_1600=sess.S1600)
    bpath = os.path.join(BAND_ROOT, 'SPXW', f'{d}.parquet')
    band_strikes = set()
    if os.path.exists(bpath):
        b = pl.read_parquet(bpath); band_strikes = set(b['strike'].unique().to_list())
        j = b.join(full.with_columns(pl.lit(1).alias('_hit')), on=['timestamp', 'strike', 'right'], how='left', suffix='_f')
        same = lambda a, c: (j[a] == j[c]).fill_null(False) | (j[a].is_null() & j[c].is_null())
        srow.update(band_rows=b.height, band_rows_in_full=int(j['_hit'].is_not_null().sum()),
                    band_rows_identical=int((j['_hit'].is_not_null() & same('bid', 'bid_f') & same('ask', 'ask_f')).sum()),
                    band_strikes=len(band_strikes), band_strikes_missing_in_full=len(band_strikes - set(full['strike'].unique().to_list())))
    else:
        srow.update(band_rows=0, band_rows_in_full=0, band_rows_identical=0, band_strikes=0, band_strikes_missing_in_full=0)
    K = sess.K
    legs = []
    labels = [(e, e) for e in sim.ENTRIES] + [(f'R{k}', RAND[(d, k)]) for k in range(1, 6)]
    for lab, hm in labels:
        ti = sim.hm2i(hm); spot = sess.spx[ti]
        base = dict(date=d, entry=lab, entry_hm=hm, spot=spot)
        if not np.isfinite(spot):
            for k in sim.KS: legs.append(dict(base, k=k, status_naked='no_spot', status_winged='no_spot'))
            continue
        k0 = round(spot / 5) * 5
        hit = np.where(K == k0)[0]
        k0_listed = bool(len(hit)); k0_usable = bool(len(hit) and sess.usable[0, ti, hit[0]] and sess.usable[1, ti, hit[0]])
        j0 = sess.atm(ti, spot)
        em = np.nan if j0 is None else (sess.bid_raw[0, ti, j0] + sess.ask_raw[0, ti, j0]) / 2 + (sess.bid_raw[1, ti, j0] + sess.ask_raw[1, ti, j0]) / 2
        for k in sim.KS:
            r = dict(base, k=k, k0=k0, k0_listed=k0_listed, k0_usable=k0_usable, atm_used=np.nan if j0 is None else K[j0], em=em,
                     k0_in_band=k0 in band_strikes)
            if j0 is not None:
                for nm, side, mult, right in (('sc', +1, k, 0), ('sp', -1, k, 1), ('wc', +1, k + 1.0, 0), ('wp', -1, k + 1.0, 1)):
                    tgt = spot + side * mult * em
                    if k == 0 and nm in ('sc', 'sp'):
                        j = j0
                    else:
                        j = sim._outward(K, tgt, side)
                    r[f'{nm}_target'] = round(tgt, 2)
                    if j is None:
                        r.update({f'{nm}_strike': np.nan, f'{nm}_listed': False, f'{nm}_gap': np.nan, f'{nm}_usable': False, f'{nm}_bid0': np.nan, f'{nm}_in_band': False})
                        continue
                    r.update({f'{nm}_strike': K[j], f'{nm}_listed': True, f'{nm}_gap': round(abs(K[j] - tgt), 2),
                              f'{nm}_usable': bool(sess.usable[right, ti, j]),
                              f'{nm}_bid0': bool(sess.usable[right, ti, j] and sess.bid_raw[right, ti, j] <= 0),
                              f'{nm}_in_band': K[j] in band_strikes})
            r['status_naked'] = sim.build(sess, ti, 0, k)[0] or 'ok'
            r['status_winged'] = sim.build(sess, ti, 1, k)[0] or 'ok'
            legs.append(r)
    nonok = []; counts = {}
    for ti in ALLMIN:
        for winged in (0, 1):
            for k in sim.KS:
                reason = sim.build(sess, ti, winged, k)[0] or 'ok'
                counts[reason] = counts.get(reason, 0) + 1
                if reason != 'ok':
                    nonok.append(dict(date=d, minute=sim.i2hm(ti), cell=('W' if winged else 'N') + f'{k:.1f}', reason=reason))
    srow.update({f'allmin_{k}': v for k, v in counts.items()})
    return srow, legs, nonok


if __name__ == '__main__':
    t0 = time.time()
    ses = sim.regular_sessions()
    have = {f[:10] for f in os.listdir(os.path.join(sim.CHAIN_ROOT, 'SPXW')) if f.endswith('.parquet')}
    fallback = [d for d in ses if d not in have and sim.BAND_FALLBACK and os.path.exists(sim.chain_path(d))]   # Amendment 1
    todo = [d for d in ses if d in have or d in fallback]; missing = [d for d in ses if d not in have]
    if os.environ.get('HWR_CACHE_ONLY'):   # warm the per-session cache only (used while the chain fetch is still running)
        with Pool(int(os.environ.get('HWR_NWORK', '2'))) as p:
            for i, _ in enumerate(p.imap(one, todo, chunksize=4)):
                if i % 200 == 0: print('cache', i, round(time.time() - t0, 1), flush=True)
        sys.exit(0)
    S, LG, NO = [], [], []
    with Pool(int(os.environ.get('HWR_NWORK', '2'))) as p:
        for i, (s, lg, no) in enumerate(p.imap(one, todo, chunksize=4)):
            S.append(s); LG += lg; NO += no
            if i % 200 == 0: print(i, s['date'], round(time.time() - t0, 1), flush=True)
    S = pd.DataFrame(S).sort_values('date'); LG = pd.DataFrame(LG).sort_values(['date', 'entry', 'k']); NO = pd.DataFrame(NO, columns=['date', 'minute', 'cell', 'reason'])
    S.to_csv(os.path.join(RES, 'integrity_sessions.csv.gz'), index=False)
    LG.to_csv(os.path.join(RES, 'integrity_legs.csv.gz'), index=False, float_format='%.6g')
    NO.to_csv(os.path.join(RES, 'integrity_minutes_nonok.csv'), index=False)
    # ---------------------------------------------------------------- summary
    per = lambda d: 'TRAIN' if d <= '2024-12-31' else 'TEST'
    LG['period'] = LG['date'].map(per); LG['kind'] = np.where(LG['entry'].str.startswith('R'), 'random', 'fixed')
    summ = dict(sessions_expected=len(ses), sessions_with_full_chain=len(todo) - len(fallback), sessions_missing_full_chain=missing,
                sessions_band_fallback=fallback,
                band_rows_total=int(S['band_rows'].sum()), band_rows_found_in_full=int(S['band_rows_in_full'].sum()),
                band_rows_identical_bid_ask=int(S['band_rows_identical'].sum()), band_strikes_missing_in_full=int(S['band_strikes_missing_in_full'].sum()),
                settle_flags=S['settle_flag'].value_counts().to_dict(),
                full_chain_strikes_median=float(S['strikes'].median()), full_chain_strikes_min=int(S['strikes'].min()), full_chain_strikes_max=int(S['strikes'].max()),
                full_chain_rows_total=int(S['rows'].sum()))
    tab = []
    for (kind, k), g in LG.groupby(['kind', 'k']):
        row = dict(kind=kind, k=k, entries=len(g), no_spot=int((g['status_naked'] == 'no_spot').sum()),
                   atm_k0_not_listed=int((~g['k0_listed'].astype(bool)).sum()), atm_k0_not_usable=int((~g['k0_usable'].astype(bool)).sum()),
                   atm_k0_outside_band_v1=int((~g['k0_in_band'].astype(bool)).sum()))
        for nm in ('sc', 'sp', 'wc', 'wp'):
            row[f'{nm}_beyond_listed'] = int((~g[f'{nm}_listed'].fillna(False).astype(bool)).sum())
            row[f'{nm}_not_usable'] = int((g[f'{nm}_listed'].fillna(False).astype(bool) & ~g[f'{nm}_usable'].fillna(False).astype(bool)).sum())
            row[f'{nm}_bid0'] = int(g[f'{nm}_bid0'].fillna(False).astype(bool).sum())
            row[f'{nm}_outside_band_v1'] = int((g[f'{nm}_listed'].fillna(False).astype(bool) & ~g[f'{nm}_in_band'].fillna(False).astype(bool)).sum())
            row[f'{nm}_gap_gt5'] = int((g[f'{nm}_gap'] > 5 + 1e-9).sum()); row[f'{nm}_gap_max'] = float(g[f'{nm}_gap'].max())
        for st in ('naked', 'winged'):
            vc = g[f'status_{st}'].value_counts().to_dict()
            row[f'{st}_ok'] = vc.get('ok', 0); row[f'{st}_not_ok'] = int(len(g) - vc.get('ok', 0))
            row[f'{st}_reasons'] = json.dumps({a: b for a, b in vc.items() if a != 'ok'})
        tab.append(row)
    pd.DataFrame(tab).to_csv(os.path.join(RES, 'integrity_by_k.csv'), index=False, float_format='%.6g')
    bad = LG[(LG['status_naked'] != 'ok') | (LG['status_winged'] != 'ok')]
    summ['fixed_and_random_entries_not_ok'] = int(len(bad))
    summ['fixed_and_random_not_ok_list'] = [f"{r.date} {r.entry}({r.entry_hm}) k={r.k} naked={r.status_naked} winged={r.status_winged}" for r in bad.itertuples()][:200]
    summ['allmin_counts'] = {c: int(S[c].sum()) for c in S.columns if c.startswith('allmin_')}
    summ['allmin_nonok_rows'] = int(len(NO)); summ['allmin_nonok_by_reason_cell'] = NO.groupby(['reason', 'cell']).size().to_dict() if len(NO) else {}
    summ['allmin_nonok_by_reason_cell'] = {f'{a}|{b}': int(v) for (a, b), v in summ['allmin_nonok_by_reason_cell'].items()}
    # what the band hid: fixed entries whose trade the v1 band could not hold but the complete chain can
    fx = LG[LG['kind'] == 'fixed']
    def v1_ok(r, winged):
        need = ['sc', 'sp'] + (['wc', 'wp'] if winged else [])
        return all(bool(r[f'{n}_in_band']) if pd.notna(r.get(f'{n}_in_band')) else False for n in need)
    fx = fx.assign(v1_naked_in_band=[v1_ok(r, 0) for _, r in fx.iterrows()], v1_winged_in_band=[v1_ok(r, 1) for _, r in fx.iterrows()])
    summ['fixed_entries_band_excluded_naked'] = int(((~fx['v1_naked_in_band']) & (fx['status_naked'] == 'ok')).sum())
    summ['fixed_entries_band_excluded_winged'] = int(((~fx['v1_winged_in_band']) & (fx['status_winged'] == 'ok')).sum())
    hid = fx[(~fx['v1_naked_in_band']) & (fx['status_naked'] == 'ok') & (fx['k'] == 0.5) & (fx['entry'].isin(['13:00', '14:05']))]
    summ['k05_13h_14h_band_excluded_dates'] = {e: sorted(g['date'].tolist()) for e, g in hid.groupby('entry')}
    summ['secs'] = round(time.time() - t0, 1)
    json.dump(summ, open(os.path.join(RES, 'integrity_summary.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: v for k, v in summ.items() if k not in ('fixed_and_random_not_ok_list',)}, indent=1, default=str)[:4000])
