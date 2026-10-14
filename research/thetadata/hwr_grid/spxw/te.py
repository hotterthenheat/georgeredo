#!/usr/bin/env python3
"""T-C reproduction (PREREGISTRATION.md G.11) and T-E (Part A): 13:00 SPXW ATM straddle held to settlement, ex FOMC/CPI/NFP,
T-E window 2022-05-13 -> 2025-05-29, holdout 2025-06-02 -> 2026-10-09.  Reads the per-session trade files written by run_grid.py.
Env: HWR_OUT (trade files), RES_DIR (results, default ./results)."""
import os, sys, glob, json, math
import numpy as np, pandas as pd, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim  # noqa: E402
from stats import cluster_boot_loop, Boot, basic, kelly_capital, path_stats  # noqa: E402

OUT = os.environ.get('HWR_OUT', sim.L.SP + '/hwr_grid/spxw')
RES = os.environ.get('RES_DIR', os.path.join(HERE, 'results')); os.makedirs(RES, exist_ok=True)
REPO = sim.REPO
TC_DIR = os.path.join(REPO, 'research', 'thetadata', 'index_tests', 'tc_spxw_straddle')
EOD_GLOB = os.path.join(sim.L.SP, 'theta', 'cache', 'index_tests', 'index_history_eod__*symbol=SPX.csv.gz')
TE_WIN = ('2022-05-13', '2025-05-29'); HOLD = ('2025-06-02', '2026-10-09')
STRESS = 0.0633; BUDGET = 0.08


def topd(df):
    return pd.DataFrame({c: df[c].to_numpy() for c in df.columns})


def straddles():
    fs = sorted(glob.glob(OUT + '/trades/*.parquet'))
    q = pl.concat([pl.read_parquet(f).filter((pl.col('cell') == 'N0.0') & (pl.col('tp') == 0) & (pl.col('stop') == 0)) for f in fs])
    return topd(q)


def official_close():
    out = {}
    for f in sorted(glob.glob(EOD_GLOB)):
        e = pd.read_csv(f)
        if e.empty: continue
        for _, r in e.iterrows(): out[str(r['last_trade'])[:10]] = float(r['close'])
    return out


def row(label, x, dates):
    b = basic(x); lo, hi = cluster_boot_loop(x, dates)
    order = np.argsort(x)[:5]
    return dict(label=label, n=b['n'], total=round(b['total'], 1), mean=round(b['mean'], 2), ci_lo=round(lo, 2), ci_hi=round(hi, 2),
                win_rate=round(b['win_rate'], 4), pf=round(b['pf'], 3), max_dd=round(b['max_dd'], 1),
                worst5=' | '.join(f'{dates[i]} {x[i]:.0f}' for i in order))


def main():
    ev = pd.read_csv(sim.EVENTS_CSV); evd = set(ev.loc[ev['event'].isin(['FOMC', 'CPI', 'NFP']), 'date'])
    S = straddles(); eod = official_close()
    lane = S[S['entry'] == '13:00'].copy()
    lane['event'] = lane['date'].isin(evd)
    lane['S_eod'] = lane['date'].map(eod)
    lane['eod_src'] = np.where(lane['S_eod'].notna(), 'eod', '1600')
    lane['S_eod'] = lane['S_eod'].fillna(lane['settle'])   # as T-C: 16:00 print where the EOD row is missing
    lane['atm_fallback'] = (lane['kc'] != (lane['spot'] / 5).round() * 5)   # 13:00 ATM strike outside the stored +-2 % band
    lane['pnl_settle_eod'] = (lane['credit'] - (lane['S_eod'] - lane['kc']).abs()) * 100 - 2.0
    out = {}
    # 0. bootstrap equivalence check (vectorised Boot vs the verbatim loop)
    x = lane.loc[lane['exit'] == 'E2', 'pnl'].values[:300]; d = lane.loc[lane['exit'] == 'E2', 'date'].values[:300]
    bl = cluster_boot_loop(x, d); bv = Boot().ci(x)[:2]
    out['boot_equivalence'] = dict(loop=bl, vectorised=bv, identical=bool(np.allclose(bl, bv)))
    # 1. T-C reproduction on 2025-06-02 .. 2026-10-09
    rows = []
    h = lane[(lane['date'] >= HOLD[0]) & (lane['date'] <= HOLD[1])]
    e0 = h[h['exit'] == 'E0'].sort_values('date'); e2 = h[h['exit'] == 'E2'].sort_values('date')
    rows.append(row('T-C repro: all sessions, sell bid 13:00 / buy ask 15:55, $1/side (published +72.43 [-75.8, 214.2], n=339)', e0['pnl'].values, e0['date'].values))
    rows.append(row('T-C repro: all sessions, hold to settlement, official close (published +156.8 [+5.76, +305.0])', e2['pnl_settle_eod'].values, e2['date'].values))
    rows.append(row('T-C repro: all sessions, hold to settlement, 16:00 SPX print', e2['pnl'].values, e2['date'].values))
    ne = e2[~e2['event']]
    rows.append(row('T-C repro: ex FOMC/CPI/NFP, hold to settlement, official close (published +139.7 [-18.45, +288.6], n=299)', ne['pnl_settle_eod'].values, ne['date'].values))
    rows.append(row('T-C repro: ex FOMC/CPI/NFP, hold to settlement, 16:00 SPX print', ne['pnl'].values, ne['date'].values))
    ne0 = e0[~e0['event']]
    rows.append(row('T-C repro: ex FOMC/CPI/NFP, sell bid / buy ask 15:55 (published +45.28 [-103.1, 182.5])', ne0['pnl'].values, ne0['date'].values))
    rep = pd.DataFrame(rows)
    # per-session comparison with the published T-C table
    tc = pd.read_csv(os.path.join(TC_DIR, 'tc_straddles.csv'))
    m = tc.merge(e0[['date', 'kc', 'credit', 'pnl']], on='date', how='outer', suffixes=('_tc', '_ds')).merge(
        e2[['date', 'pnl', 'pnl_settle_eod', 'settle', 'S_eod']].rename(columns={'pnl': 'pnl_settle_1600_ds', 'pnl_settle_eod': 'pnl_settle_eod_ds'}), on='date', how='left')
    cmp = dict(sessions_tc=int(tc['date'].nunique()), sessions_dataset=int(e0['date'].nunique()),
               in_both=int(m['strike'].notna().sum() - m['kc'].isna().sum()),
               strike_equal=int((m['strike'] == m['kc']).sum()), credit_equal=int((m['credit_exec'] - m['credit']).abs().lt(1e-6).sum()),
               pnl_1555_equal=int((m['pnl_exec_15:55'] - m['pnl']).abs().lt(0.01).sum()),
               pnl_settle_eod_equal=int((m['pnl_settle'] - m['pnl_settle_eod_ds']).abs().lt(0.01).sum()),
               max_abs_diff_pnl_1555=float((m['pnl_exec_15:55'] - m['pnl']).abs().max()),
               settle_1600_minus_official_bp_mean=float(((m['settle'] - m['S_eod']) / m['S_eod'] * 1e4).mean()),
               settle_1600_minus_official_bp_absmean=float(((m['settle'] - m['S_eod']).abs() / m['S_eod'] * 1e4).mean()),
               settle_1600_minus_official_pts_maxabs=float((m['settle'] - m['S_eod']).abs().max()))
    diffs = m[(m['pnl_exec_15:55'] - m['pnl']).abs().gt(0.01) | m['kc'].isna() | m['strike'].isna()]
    diffs[['date', 'strike', 'kc', 'credit_exec', 'credit', 'pnl_exec_15:55', 'pnl']].to_csv(os.path.join(RES, 'tc_repro_session_diffs.csv'), index=False)
    cmp['eod_missing_dates'] = sorted(set(e2.loc[e2['eod_src'] == '1600', 'date']))
    cmp['atm_fallback_dates_in_window'] = sorted(set(e2.loc[e2['atm_fallback'], 'date']))
    out['tc_session_compare'] = cmp
    cmp['note'] = 'sessions that differ are those where the 13:00 ATM strike lies outside the dataset band (+-2 % of the 09:31 SPX price) and the nearest stored strike is used'
    rep.to_csv(os.path.join(RES, 'tc_reproduction.csv'), index=False)
    if len(sys.argv) > 1 and sys.argv[1] == 'tc':   # sanity check only
        pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 120)
        print(rep[['label', 'n', 'mean', 'ci_lo', 'ci_hi', 'win_rate', 'pf', 'max_dd']].to_string()); print(json.dumps(cmp, indent=1))
        print(json.dumps(out['boot_equivalence'])); return
    # 2. T-E window and holdout
    te_rows = []; by_year = []
    E2 = lane[(lane['exit'] == 'E2') & (~lane['event'])].sort_values('date')
    allE2 = lane[lane['exit'] == 'E2']
    ses = sim.regular_sessions()
    for nm, (a, b) in (('T-E window', TE_WIN), ('holdout', HOLD)):
        w = E2[(E2['date'] >= a) & (E2['date'] <= b)]
        expected = [s for s in ses if a <= s <= b and s not in evd]
        missing = sorted(set(expected) - set(w['date']))
        r = row(f'{nm}: 13:00 ATM straddle, sell bid, hold to 16:00 SPX print, $2 fees, ex FOMC/CPI/NFP', w['pnl'].values, w['date'].values)
        r.update(window=f'{a} -> {b}', expected_sessions=len(expected), missing_or_skipped=len(missing),
                 missing_list=' '.join(missing[:30]), months=round((pd.Timestamp(w['date'].max()) - pd.Timestamp(w['date'].min())).days / 30.44, 1),
                 mean_credit_pts=round(w['credit'].mean(), 3), median_pnl=float(np.median(w['pnl'])), sd=round(w['pnl'].std(ddof=1), 1))
        r['verdict'] = ('PASS' if (r['ci_lo'] > 0 and r['n'] >= 500) else 'FAIL') if nm == 'T-E window' else ('confirms' if (r['ci_lo'] > 0 and r['n'] >= 150 and r['months'] >= 3) else 'does not confirm')
        te_rows.append(r)
        r2 = row(f'{nm}: sensitivity, official SPX close', w['pnl_settle_eod'].dropna().values, w.loc[w['pnl_settle_eod'].notna(), 'date'].values); te_rows.append(r2)
        r3 = row(f'{nm}: sensitivity, adverse fill (one $0.05 tick worse per leg)', w['pnl_adv'].values, w['date'].values); te_rows.append(r3)
        wf = w[~w['atm_fallback']]
        r4 = row(f'{nm}: sensitivity, excluding sessions whose 13:00 ATM strike was outside the stored band ({int(w["atm_fallback"].sum())}: {" ".join(sorted(w.loc[w["atm_fallback"], "date"]))})', wf['pnl'].values, wf['date'].values); te_rows.append(r4)
        wa = allE2[(allE2['date'] >= a) & (allE2['date'] <= b)].sort_values('date')
        te_rows.append(row(f'{nm}: reference, event days kept', wa['pnl'].values, wa['date'].values))
        ev_only = wa[wa['event']]
        if len(ev_only) > 1: te_rows.append(row(f'{nm}: reference, FOMC/CPI/NFP days only', ev_only['pnl'].values, ev_only['date'].values))
        we0 = lane[(lane['exit'] == 'E0') & (~lane['event']) & (lane['date'] >= a) & (lane['date'] <= b)].sort_values('date')
        te_rows.append(row(f'{nm}: reference, buy back at the 15:55 ask (T-C rule)', we0['pnl'].values, we0['date'].values))
        we1 = lane[(lane['exit'] == 'E1') & (~lane['event']) & (lane['date'] >= a) & (lane['date'] <= b)].sort_values('date')
        te_rows.append(row(f'{nm}: reference, E1 (15:55 buy-back except legs with ask <= $0.10)', we1['pnl'].values, we1['date'].values))
        # random-entry baseline (R1..R5: ATM straddle at the random minute, hold to settlement, same exclusion)
        R = S[(S['entry'].str.startswith('R')) & (S['exit'] == 'E2') & (~S['date'].isin(evd)) & (S['date'] >= a) & (S['date'] <= b)]
        for dname, g in R.groupby('entry'):
            g = g.sort_values('date'); te_rows.append(row(f'{nm}: random-entry baseline {dname} (seed {10 + int(dname[1])})', g['pnl'].values, g['date'].values))
        bm = R.groupby('date')['pnl'].mean()
        j = w.set_index('date')['pnl'].to_frame('lane').join(bm.rename('base'), how='inner').sort_index()
        dd = (j['lane'] - j['base']).values; lo, hi = cluster_boot_loop(dd, j.index.values)
        rt = w['rt_cost'].mean()
        te_rows.append(dict(label=f'{nm}: lane minus per-date mean of five random draws', n=len(dd), mean=round(dd.mean(), 2), ci_lo=round(lo, 2), ci_hi=round(hi, 2),
                            note=f'mean round-trip cost (entry half-spreads x100 + $2) = {rt:.2f}; beats random by > 1 round trip: {dd.mean() > rt}'))
        for y, g in w.groupby(w['date'].str[:4]):
            bb = basic(g['pnl'].values)
            by_year.append(dict(window=nm, year=y, n=bb['n'], mean=round(bb['mean'], 1), total=round(bb['total'], 0), win_rate=round(bb['win_rate'], 3),
                                worst=round(g['pnl'].min(), 0), mean_credit=round(g['credit'].mean(), 2)))
    TE = pd.DataFrame(te_rows); TE.to_csv(os.path.join(RES, 'te_results.csv'), index=False)
    pd.DataFrame(by_year).to_csv(os.path.join(RES, 'te_by_year.csv'), index=False)
    # 3. margin and sizing (pre-stated rules, T-E.4)
    w = E2[(E2['date'] >= TE_WIN[0]) & (E2['date'] <= TE_WIN[1])]; hd = E2[(E2['date'] >= HOLD[0]) & (E2['date'] <= HOLD[1])]
    sz = {}
    for nm, g in (('T-E window', w), ('holdout', hd)):
        regt = 0.15 * g['spot'] * 100 + g['credit'] * 100
        tail_loss = (STRESS * g['spot'] - g['credit']) * 100; tail_cap = tail_loss / BUDGET
        sz[nm] = dict(regT_margin_median=round(regt.median(), 0), regT_margin_range=[round(regt.min(), 0), round(regt.max(), 0)],
                      mean_return_on_regT_per_day_pct=round(float((g['pnl'] / regt).mean() * 100), 4),
                      stress_loss_median=round(tail_loss.median(), 0), tail_capital_median=round(tail_cap.median(), 0),
                      worst_day_loss=round(float(g['pnl'].min()), 0), worst_day_as_pct_of_tail_capital=round(float(-g['pnl'].min() / tail_cap.loc[g['pnl'].idxmin()] * 100), 2),
                      max_13_16_move_pct=round(float(((g['settle'] - g['spot']).abs() / g['spot']).max() * 100), 3))
    xw = w['pnl'].values; xh = hd['pnl'].values
    C = kelly_capital(xw)
    sz['kelly_from_TE_window'] = dict(full_kelly_capital=None if C is None else round(C, 0))
    if C is not None:
        for frac, mult in (('full', 1), ('half', 2), ('quarter', 4), ('tenth', 10)):
            sz[f'{frac}_kelly_TE_window_in_sample'] = path_stats(xw, mult * C)
            sz[f'{frac}_kelly_applied_to_holdout'] = path_stats(xh, mult * C)
    tc_med = sz['T-E window']['tail_capital_median']
    sz['tail_sizing_fixed_capital_TE_median'] = dict(TE_window=path_stats(xw, tc_med), holdout=path_stats(xh, tc_med))
    out['sizing'] = sz
    json.dump(out, open(os.path.join(RES, 'te_summary.json'), 'w'), indent=1, default=str)
    pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 120)
    print(rep[['label', 'n', 'mean', 'ci_lo', 'ci_hi', 'win_rate', 'pf', 'max_dd']].to_string())
    print(json.dumps(cmp, indent=1))
    print(TE[['label', 'n', 'mean', 'ci_lo', 'ci_hi', 'win_rate', 'pf', 'max_dd']].to_string())
    print(json.dumps(out['boot_equivalence']))


if __name__ == '__main__':
    main()
