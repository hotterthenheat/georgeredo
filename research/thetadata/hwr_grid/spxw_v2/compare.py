#!/usr/bin/env python3
"""Side-by-side: round-2 study (../spxw, +-2 % band chains, SPX 16:00 print) vs v2 (complete chains, Cboe close).
Outputs (results/): cmp_te.csv, cmp_selection.csv, cmp_multiplicity.csv, cmp_random_baseline.csv, cmp_days.csv (per-day
P&L of the compared rules in both studies), cmp_decomposition.csv (v1 -> v2 change split into the chain change and the settlement
change), carry_gate.csv (COMPASS section 10 items that are computable from the data; forward validation is not yet available)."""
import os, sys, json
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim  # noqa: E402
import analyze as A  # noqa: E402
import stress as ST  # noqa: E402
from stats import Boot, basic  # noqa: E402

RES = A.RES
V1RES = os.path.join(HERE, '..', 'spxw', 'results')
V1OUT = sim.L.SP + '/hwr_grid/spxw'


def te_cmp():
    v1 = pd.read_csv(os.path.join(V1RES, 'te_results.csv')); v2 = pd.read_csv(os.path.join(RES, 'te_results.csv'))
    items = [('lane (v1: 16:00 print; v2: Cboe close)', ': 13:00 ATM straddle', ': 13:00 ATM straddle'),
             ('lane, Cboe/official close in both', ': sensitivity, official SPX close', ': 13:00 ATM straddle'),
             ('lane, 16:00 print in both', ': 13:00 ATM straddle', ': sensitivity, settlement at the SPX print stamped 16:00'),
             ('adverse fill (one tick worse per leg)', ': sensitivity, adverse fill', ': sensitivity, adverse fill'),
             ('event days kept', ': reference, event days kept', ': reference, event days kept'),
             ('buy back at 15:55 ask (E0)', ': reference, buy back at the 15:55', ': reference, buy back at the 15:55'),
             ('E1', ': reference, E1', ': reference, E1'),
             ('lane minus random (per-date mean of 5 draws)', ': lane minus per-date mean', ': lane minus per-date mean')]
    rows = []
    for w in ('T-E window', 'holdout'):
        for name, p1, p2 in items:
            a = v1[v1['label'].str.startswith(w + p1)]; b = v2[v2['label'].str.startswith(w + p2)]
            r = dict(window=w, item=name)
            for tag, x in (('v1', a), ('v2', b)):
                if len(x):
                    x = x.iloc[0]
                    for c in ('n', 'mean', 'ci_lo', 'ci_hi', 'win_rate', 'pf', 'max_dd', 'worst5', 'verdict', 'note'):
                        if c in x.index: r[f'{tag}_{c}'] = x[c]
            rows.append(r)
        for tag, x in (('v1', v1), ('v2', v2)):
            rr = x[x['label'].str.startswith(w + ': random-entry baseline')]
            rows.append(dict(window=w, item=f'random draws R1..R5 means ({tag})', **{f'{tag}_mean': ' / '.join(f'{m:.1f}' for m in rr['mean']), f'{tag}_n': ' / '.join(str(int(n)) for n in rr['n'])}))
        m2 = v2[v2['label'].str.startswith(w + ': matched days: lane')]
        if len(m2): rows.append(dict(window=w, item='v2 matched days', v2_n=m2.iloc[0]['n'], v2_mean=m2.iloc[0]['mean'], v2_note=m2.iloc[0]['note']))
    pd.DataFrame(rows).to_csv(os.path.join(RES, 'cmp_te.csv'), index=False, float_format='%.6g')


def sel_cmp():
    s1 = pd.read_csv(os.path.join(V1RES, 'selected_test.csv')); s2 = pd.read_csv(os.path.join(RES, 'selected_test.csv'))
    g1 = pd.read_csv(os.path.join(V1RES, 'gate.csv')); g2 = pd.read_csv(os.path.join(RES, 'gate.csv'))
    cols = ['cid', 'train_n', 'train_mean', 'train_ci_lo', 'train_ci_hi', 'train_win_rate', 'test_n', 'test_mean', 'test_ci_lo', 'test_ci_hi',
            'test_win_rate', 'test_pf', 'test_max_dd', 'test_worst_day', 'test_worst5', 'test_mean_rt_cost', 'test_mean_adverse', 'test_coverage']
    rows = []
    for study, S, G, labs in (('v1 (band, 16:00 print)', s1, g1, ['S1', 'S2']), ('v2 (complete, Cboe close)', s2, g2, ['S1', 'S2', 'orig_S1', 'orig_S2', 'TE_rule'])):
        for lab in labs:
            x = S[S['selection'] == lab]
            if not len(x): continue
            x = x.iloc[0]; g = G[G['selection'] == lab]
            r = dict(study=study, selection={'S1': 'S1 (selected on this study\'s TRAIN)', 'S2': 'S2 (selected on this study\'s TRAIN)', 'orig_S1': 'round-2 S1 definition',
                                            'orig_S2': 'round-2 S2 definition', 'TE_rule': "T-E's rule as a grid cell (F4)"}[lab],
                     **{c: x[c] for c in cols if c in x.index})
            if len(g):
                g = g.iloc[0]
                for c in ('lane_minus_random', 'C1_lb_gt0', 'C2_n150_3m', 'C2_beats_random_by_rt', 'C3_adverse_mean_gt0', 'WR70', 'PASS_all', 'test_ci_lo_bonf2', 'CARRY_stat_items'):
                    if c in g.index: r[c] = g[c]
            rows.append(r)
    pd.DataFrame(rows).to_csv(os.path.join(RES, 'cmp_selection.csv'), index=False, float_format='%.6g')


def mult_cmp():
    rows = []
    for study, d in (('v1', V1RES), ('v2', RES)):
        for m in json.load(open(os.path.join(d, 'multiplicity.json'))):
            rows.append(dict(study=study, period=m['period'], observed_lb_gt0=m['observed_lb_gt0'], chance_mean=m['chance_mean'], chance_p95=m['chance_p95'],
                             chance_p99=m['chance_p99'], p_chance_ge_observed=m['p_chance_ge_observed'], observed_max_t=m['observed_max_t'], argmax_t=m['argmax_t'],
                             fixed_se_reality_check_p=m['fixed_se_reality_check_p'], fixed_se_romano_wolf_rejections=m['fixed_se_romano_wolf_rejections'],
                             within_draw_se_reality_check_p=m['within_draw_se_reality_check_p'], within_draw_se_romano_wolf_rejections=m['within_draw_se_romano_wolf_rejections'],
                             fixed_se_rejected=' '.join(m['fixed_se_romano_wolf_rejected'][:20])))
    pd.DataFrame(rows).to_csv(os.path.join(RES, 'cmp_multiplicity.csv'), index=False, float_format='%.6g')


def rb_cmp():
    b1 = pd.read_csv(os.path.join(V1RES, 'selected_random_baseline.csv')); b2 = pd.read_csv(os.path.join(RES, 'selected_random_baseline.csv'))
    b1.insert(0, 'study', 'v1'); b2.insert(0, 'study', 'v2')
    pd.concat([b1, b2]).to_csv(os.path.join(RES, 'cmp_random_baseline.csv'), index=False, float_format='%.6g')


def days_and_decomp():
    sel = json.load(open(os.path.join(RES, 'selection_train.json'))); osel = json.load(open(A.ORIG_SEL))
    rules = [('orig_S2', osel['S2']['cid']), ('orig_S1', osel['S1']['cid']), ('TE_rule', A.TE_RULE)]
    for lab, key in (('reselected_S1', 'S1'), ('reselected_S2', 'S2')):
        if sel[key] and sel[key]['cid'] not in [c for _, c in rules]: rules.append((lab, sel[key]['cid']))
    boot = Boot(); days = []; dec = []
    for lab, cid in rules:
        cfg = ST.parse(cid)
        t2 = ST.config_trades(cfg)
        t1 = ST.config_trades(cfg, out=V1OUT)
        # v2 P&L re-valued at the 16:00 print (settlement source change only), for rows settled at expiry
        s2 = t2['settle'].values; s16 = t2['settle_1600'].values
        delta = np.zeros(len(t2))
        settled = (t2['how'].values == 'settle')
        for k, sign, f in (('kc', -1, ST.intr_c), ('kp', -1, ST.intr_p), ('kcw', +1, ST.intr_c), ('kpw', +1, ST.intr_p)):
            K = t2[k].values; ok = np.isfinite(K)
            delta += np.where(ok & settled, sign * (f(np.nan_to_num(K), s16) - f(np.nan_to_num(K), s2)) * 100, 0.0)
        t2['pnl_1600'] = t2['pnl'].values + delta
        m = t2[['date', 'period', 'pnl', 'pnl_1600', 'spot', 'credit', 'kc', 'kp', 'settle', 'settle_1600']].merge(
            t1[['date', 'pnl', 'credit', 'kc', 'kp']].rename(columns={'pnl': 'pnl_v1', 'credit': 'credit_v1', 'kc': 'kc_v1', 'kp': 'kp_v1'}), on='date', how='outer')
        m['period'] = np.where(m['date'] <= A.PER['TRAIN'][1], 'TRAIN', 'TEST')
        m['status'] = np.where(m['pnl'].notna() & m['pnl_v1'].notna(), 'both', np.where(m['pnl'].notna(), 'v2 only (band-skipped in v1)', 'v1 only'))
        m['same_strikes'] = (m['kc'] == m['kc_v1']) & (m['kp'] == m['kp_v1'])
        m.insert(0, 'cid', cid); m.insert(0, 'label', lab); days.append(m)
        for per in ('TRAIN', 'TEST'):
            g = m[m['period'] == per].sort_values('date')
            both = g[g['status'] == 'both']; add = g[g['status'] != 'both']
            def st(x):
                x = x[np.isfinite(x)]
                if len(x) < 2: return (len(x), float(np.nan if not len(x) else x.mean()), np.nan, np.nan, np.nan)
                lo, hi, _ = boot.ci(x); b = basic(x); return (b['n'], b['mean'], lo, hi, b['win_rate'])
            for nm, x in (('v1 as published (band, 16:00 print)', g['pnl_v1'].values), ('v2 chain, 16:00 print (chain change only)', g['pnl_1600'].values),
                          ('v2 chain, Cboe close (both changes)', g['pnl'].values),
                          ('days in both: v1', both['pnl_v1'].values), ('days in both: v2 16:00 print', both['pnl_1600'].values), ('days in both: v2 Cboe close', both['pnl'].values),
                          ('v2-only days (band-skipped in v1): v2 Cboe close', g.loc[g['status'] == 'v2 only (band-skipped in v1)', 'pnl'].values)):
                n, mu, lo, hi, wr = st(np.asarray(x, float))
                dec.append(dict(label=lab, cid=cid, period=per, series=nm, n=n, mean=mu, ci_lo=lo, ci_hi=hi, win_rate=wr,
                                total=float(np.nansum(np.asarray(x, float)))))
            dec.append(dict(label=lab, cid=cid, period=per, series='days in both with different strikes/credit', n=int((~both['same_strikes']).sum()),
                            mean=np.nan, ci_lo=np.nan, ci_hi=np.nan, win_rate=np.nan, total=np.nan))
            a2 = add[add['status'] == 'v2 only (band-skipped in v1)'].sort_values('pnl'); a1 = add[add['status'] == 'v1 only']
            dec.append(dict(label=lab, cid=cid, period=per, series='v2-only days list, worst first (date:v2 P&L)', n=len(a2), mean=np.nan, ci_lo=np.nan, ci_hi=np.nan, win_rate=np.nan,
                            total=float(a2['pnl'].sum()), detail=' '.join(f'{d}:{p:.0f}' for d, p in zip(a2['date'], a2['pnl']))))
            dec.append(dict(label=lab, cid=cid, period=per, series='v1-only days list (date:v1 P&L)', n=len(a1), mean=np.nan, ci_lo=np.nan, ci_hi=np.nan, win_rate=np.nan,
                            total=float(a1['pnl_v1'].sum()), detail=' '.join(f'{d}:{p:.0f}' for d, p in zip(a1['date'], a1['pnl_v1']))))
    pd.concat(days).to_csv(os.path.join(RES, 'cmp_days.csv'), index=False, float_format='%.6g')
    pd.DataFrame(dec).to_csv(os.path.join(RES, 'cmp_decomposition.csv'), index=False, float_format='%.6g')


def random_explain():
    """Why lane - random changed between v1 and v2: the random draws per day in each study, on the same days."""
    osel = json.load(open(A.ORIG_SEL)); sel = json.load(open(os.path.join(RES, 'selection_train.json')))
    rules = [('orig_S2', osel['S2']['cid']), ('TE_rule', A.TE_RULE)]
    if sel['S2']['cid'] != osel['S2']['cid']: rules.append(('reselected_S2', sel['S2']['cid']))
    rows = []; perday = []
    for lab, cid in rules:
        cfg = ST.parse(cid)
        lane = {}; R = {}
        for tag, out in (('v1', V1OUT), ('v2', None)):
            lane[tag] = ST.config_trades(cfg, out=out).set_index('date')['pnl']
            dr = []
            for d in range(1, 6):
                c = dict(cfg, entry=f'R{d}')   # same cell/TP/stop/exit/filter as the lane (F2 -> 14:05 on FOMC days, as in analyze.baseline)
                t = ST.config_trades(c, out=out).set_index('date')['pnl'].rename(f'R{d}')
                dr.append(t)
            R[tag] = pd.concat(dr, axis=1)
        for per in ('TRAIN', 'TEST'):
            inp = lambda s: s[(s.index >= A.PER[per][0]) & (s.index <= A.PER[per][1])]
            l1, l2, r1, r2 = inp(lane['v1']), inp(lane['v2']), inp(R['v1']), inp(R['v2'])
            m1 = l1.index.intersection(r1.dropna(how='all').index)   # v1 matched days
            full1 = r1.loc[m1].notna().sum(axis=1)
            short = m1[full1.values < 5]
            def add(name, n, mean, note=''):
                rows.append(dict(label=lab, cid=cid, period=per, item=name, n=n, mean=mean, note=note))
            add('v1 lane on v1 matched days', len(m1), l1.loc[m1].mean())
            add('v1 random per-date mean on v1 matched days', len(m1), r1.loc[m1].mean(axis=1).mean())
            add('v1 random pooled (all draw-trades)', int(r1.notna().sum().sum()), float(np.nanmean(r1.values)))
            off = r1.drop(index=m1, errors='ignore')
            add('v1 random draw-trades on days the v1 lane did not trade', int(off.notna().sum().sum()), float(np.nanmean(off.values)) if off.notna().any().any() else np.nan,
                ' '.join(f'{d}:{v:.0f}' for d, v in off.mean(axis=1).dropna().sort_values().items()))
            add('v1 matched days with < 5 random draws', len(short), np.nan, ' '.join(short))
            add('v1 random draw-trades missing on matched days', int((5 - full1).sum()), np.nan)
            add('v2 random per-date mean on the same v1 matched days', len(m1), r2.reindex(m1).mean(axis=1).mean())
            add('v2 lane on the same v1 matched days', len(m1), l2.reindex(m1).mean())
            m2 = l2.index.intersection(r2.dropna(how='all').index)
            add('v2 lane on v2 matched days', len(m2), l2.loc[m2].mean())
            add('v2 random per-date mean on v2 matched days', len(m2), r2.loc[m2].mean(axis=1).mean())
            add('v2 random pooled', int(r2.notna().sum().sum()), float(np.nanmean(r2.values)))
            extra = l2.index.difference(m1)
            add('v2 lane on days absent from v1 matched set', len(extra), l2.loc[extra].mean() if len(extra) else np.nan,
                ' '.join(f'{d}:{v:.0f}' for d, v in l2.loc[extra].sort_values().items()))
            add('v2 random per-date mean on those days', len(extra), r2.reindex(extra).mean(axis=1).mean() if len(extra) else np.nan,
                ' '.join(f'{d}:{v:.0f}' for d, v in r2.reindex(extra).mean(axis=1).sort_values().items()))
            # influence of single days on v2 lane - random (per-date mean of five draws)
            diff = (l2.loc[m2] - r2.loc[m2].mean(axis=1)).sort_index()
            boot = Boot(); lo, hi, _ = boot.ci(diff.values)
            add('v2 lane minus random (all matched days)', len(diff), diff.mean(), f'CI [{lo:.2f}, {hi:.2f}]')
            top = diff.abs().sort_values(ascending=False).index[:5]
            add('v2 five most influential days (date: lane - random)', 5, np.nan, ' '.join(f'{d}:{diff.loc[d]:.0f}' for d in top))
            for k_ in (1, 3):
                keep = diff.drop(diff.abs().sort_values(ascending=False).index[:k_])
                lo, hi, _ = boot.ci(keep.values)
                add(f'v2 lane minus random without the {k_} most influential day(s)', len(keep), keep.mean(), f'CI [{lo:.2f}, {hi:.2f}]')
            if '2025-04-09' in diff.index:
                keep = diff.drop('2025-04-09'); lo, hi, _ = boot.ci(keep.values)
                add('v2 lane minus random without 2025-04-09', len(keep), keep.mean(), f'CI [{lo:.2f}, {hi:.2f}]')
            # the v1 short days: v1 survivors vs v2 all five draws
            if len(short):
                add('v1 short days: v1 per-date mean of surviving draws', len(short), r1.loc[short].mean(axis=1).mean())
                add('v1 short days: v2 per-date mean of all five draws', len(short), r2.reindex(short).mean(axis=1).mean())
                for d in short:
                    perday.append(dict(label=lab, period=per, date=d, v1_draws=int(full1.loc[d]), v1_random_mean=r1.loc[d].mean(), v2_random_mean=r2.loc[d].mean() if d in r2.index else np.nan,
                                       v1_lane=l1.get(d, np.nan), v2_lane=l2.get(d, np.nan), v2_draws=' '.join(f'{v:.0f}' for v in r2.loc[d].values) if d in r2.index else ''))
    pd.DataFrame(rows).to_csv(os.path.join(RES, 'cmp_random_explain.csv'), index=False, float_format='%.6g')
    pd.DataFrame(perday).to_csv(os.path.join(RES, 'cmp_random_shortdays.csv'), index=False, float_format='%.6g')


def robustness():
    """Descriptive robustness of the TEST/TRAIN results of the compared rules on complete data: by calendar year, without the
    k best days, without April 2025, and the share of the total earned by the best days."""
    osel = json.load(open(A.ORIG_SEL)); sel = json.load(open(os.path.join(RES, 'selection_train.json')))
    rules = [('orig_S2', osel['S2']['cid']), ('S1 (orig = reselected)', sel['S1']['cid']), ('TE_rule', A.TE_RULE)]
    if sel['S2']['cid'] != osel['S2']['cid']: rules.insert(1, ('reselected_S2', sel['S2']['cid']))
    boot = Boot(); rows = []
    for lab, cid in rules:
        T = ST.config_trades(ST.parse(cid))
        for per in ('TRAIN', 'TEST'):
            g = T[T['period'] == per].sort_values('date'); x = g['pnl'].values; d = g['date'].values
            def add(item, v, note=''):
                v = np.asarray(v, float); lo, hi, _ = boot.ci(v); b = basic(v)
                rows.append(dict(label=lab, cid=cid, period=per, item=item, n=b['n'], mean=b['mean'], ci_lo=lo, ci_hi=hi, win_rate=b['win_rate'], total=b['total'], note=note))
            add('all days', x)
            for y in sorted(set(s[:4] for s in d)):
                add(f'year {y}', x[np.array([s[:4] == y for s in d])])
            order = np.argsort(-x)
            for k in (1, 3, 5, 10):
                add(f'without the {k} best day(s)', np.delete(x, order[:k]), ' '.join(f'{d[i]}:{x[i]:.0f}' for i in order[:k]))
            apr = np.array([s.startswith('2025-04') for s in d])
            if apr.any(): add('without April 2025', x[~apr], f'{int(apr.sum())} days, sum {x[apr].sum():.0f}')
            add('top-10 days share of total (in note)', x, f'{x[order[:10]].sum() / x.sum():.3f}' if x.sum() != 0 else '')
    pd.DataFrame(rows).to_csv(os.path.join(RES, 'cmp_robustness.csv'), index=False, float_format='%.6g')


def carry_gate():
    """COMPASS section 10 gate items, computed where data allows (judgement items are stated, not computed)."""
    G = pd.read_csv(os.path.join(RES, 'gate.csv')); S = pd.read_csv(os.path.join(RES, 'selected_test.csv'))
    I = pd.read_csv(os.path.join(RES, 'integrity_legs.csv.gz')); integ = json.load(open(os.path.join(RES, 'integrity_summary.json')))
    caps = pd.read_csv(os.path.join(RES, 'capital_returns.csv')); mrg = pd.read_csv(os.path.join(RES, 'margin_summary.csv'))
    dd = pd.read_csv(os.path.join(RES, 'drawdown_bootstrap.csv'))
    sel = json.load(open(os.path.join(RES, 'selection_train.json')))
    labmap = {'orig_S2': 'orig_S2', 'TE_rule': 'TE_rule', 'S2': 'reselected_S2'}
    rows = []
    for glab in ('orig_S2', 'S2', 'TE_rule'):
        g = G[G['selection'] == glab]
        if not len(g): continue
        g = g.iloc[0]; cfg = ST.parse(g['cid']); slab = labmap[glab]
        if glab == 'S2' and not (caps['label'] == 'reselected_S2').any(): slab = 'orig_S2'   # re-selected S2 identical to the round-2 S2
        k = float(cfg['cell'][1:]); ents = [cfg['entry']]
        ii = I[(I['entry'].isin(ents)) & (I['k'] == k)]
        st = 'status_winged' if cfg['cell'][0] == 'W' else 'status_naked'
        not_ok = ii[ii[st] != 'ok']
        test_ii = ii[ii['date'] >= A.PER['TEST'][0]]; test_not_ok = test_ii[test_ii[st] != 'ok']
        test_fallback = [d for d in integ.get('sessions_band_fallback', []) if d >= A.PER['TEST'][0]]
        c15 = caps[(caps['label'] == slab) & (caps['capital_rule'] == 'cap15') & (caps['period'] == 'TEST')]
        c10 = caps[(caps['label'] == slab) & (caps['capital_rule'] == 'cap10') & (caps['period'] == 'TEST')]
        mm = mrg[(mrg['label'] == slab) & (mrg['period'] == 'TEST')]
        d15 = dd[(dd['label'] == slab) & (dd['capital_rule'] == 'cap15') & (dd['source'] == 'ALL') & (dd['block'] == 20) & (dd['horizon_sessions'] == 252)]
        rows.append(dict(
            selection=glab, cid=g['cid'],
            data_integrity=(f"TEST: {len(test_not_ok)} of {len(test_ii)} sessions with a needed strike/quote missing at {cfg['entry']} (k={k}), complete chains on all TEST sessions: {not test_fallback}; "
                            f"whole sample: {len(not_ok)} of {len(ii)} missing ({' '.join(sorted(not_ok['date']))}); complete chains for {integ['sessions_with_full_chain']}/{integ['sessions_expected']} regular sessions "
                            f"(band fallback: {' '.join(integ.get('sessions_band_fallback', []))}); SHA-256 per file in integrity_sessions.csv.gz"),
            data_integrity_pass_TEST=bool(len(test_not_ok) == 0 and not test_fallback),
            data_integrity_pass_all_sessions=bool(len(not_ok) == 0 and integ['sessions_with_full_chain'] == integ['sessions_expected']),
            execution_realism='bid/ask at the entry-minute NBBO, $1/contract/side, settlement at the Cboe close (no 16:00 proxy); 1-lot, no queue/size model',
            stat_test_n=g['test_n'], stat_test_mean=g['test_mean'], stat_test_ci_lo=g['test_ci_lo'], stat_test_ci_lo_bonf2=g['test_ci_lo_bonf2'],
            stat_adverse_mean=g['test_mean_adverse'], stat_months=g['test_months'],
            statistical_validity_pass=bool(g['test_ci_lo_bonf2'] > 0 and g['C2_n150_3m'] and g['C3_adverse_mean_gt0']),
            tail_cap15_median=float(c15['capital_median'].iloc[0]) if len(c15) else np.nan, tail_cap10_median=float(c10['capital_median'].iloc[0]) if len(c10) else np.nan,
            tail_ann_return_cap15_pct=float(c15['ann_return_on_median_capital_pct'].iloc[0]) if len(c15) else np.nan,
            tail_ann_return_cap10_pct=float(c10['ann_return_on_median_capital_pct'].iloc[0]) if len(c10) else np.nan,
            regt_median=float(mm['regt_median'].iloc[0]) if len(mm) else np.nan, pm_approx_median=float(mm['pm_approx_median'].iloc[0]) if len(mm) else np.nan,
            p_dd_gt10_1y_cap15=float(d15['p_dd_gt10'].iloc[0]) if len(d15) else np.nan, p_end_below_start_1y_cap15=float(d15['p_end_below_start'].iloc[0]) if len(d15) else np.nan,
            forward_validation='not yet: 0 of >= 150 sessions and 0 of >= 7 months of forward paper trading',
            classification='carry (no timing claim; random-entry item not applied)',
            promotable=False))
    pd.DataFrame(rows).to_csv(os.path.join(RES, 'carry_gate.csv'), index=False, float_format='%.6g')


if __name__ == '__main__':
    stage = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if stage in ('all', 'tables'):
        te_cmp(); sel_cmp(); mult_cmp(); rb_cmp(); days_and_decomp(); random_explain(); robustness()
    if stage in ('all', 'gate'):
        carry_gate()
    print('compare done', stage)
