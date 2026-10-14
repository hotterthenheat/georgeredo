#!/usr/bin/env python3
"""Work item 3 -- tail stress, margin and capital for the round-2 S2 definition, the re-selected S2 (if different) and T-E's rule,
on the complete-chain v2 trades (Cboe settlement).  Descriptive; nothing here feeds back into selection.

(a) Shock P&L per trade: settlement P&L if SPX settled at spot_entry x (1 + x), x in SHOCKS, strikes and credit as actually traded
    (long wings included if any), entry fees only (legs settle, no exit fee).  A stop or take-profit in the configuration is ignored
    (gap assumption: the move happens without an executable exit).
(b) Worst historical entry-to-close moves of SPX, 13:00 -> close and 14:05 -> close, 2017-06-01 -> 2026-10-09 (regular sessions;
    early closes excluded), close = official close (ThetaData EOD close, identical to Cboe's on 1,105/1,105 SPXW sessions; Cboe
    file for 2026-06-09 where the EOD row is missing) and, for reference, the SPX print stamped 16:00.
(c) Reg-T (Cboe strategy-based) initial margin per lot, from each leg's entry quote:
      short call or put on a broad-based index: proceeds + max(15 % x index x 100 - OTM amount x 100, 10 % x index x 100 [calls] /
      10 % x strike x 100 [puts]);  short put + short call: the greater side's requirement + the other side's proceeds;
      a spread (winged) side: the strike width x 100 (long wing fully paid).  `regt_simple` uses 10 % x index for both minimums.
    Portfolio margin (approximation): the largest expiration-value loss of the position over SPX moves from -8 % to +6 % of the entry
    level in 0.1 % steps (the TIMS broad-based index range), net of the credit; brokers' house minimums are not included.
(d) Capital per lot such that the 10 % and 15 % shock losses stay within 25 % of capital: cap10 = max(loss(-10 %), loss(+10 %)) / 0.25,
    cap15 = max(loss(-15 %), loss(+15 %)) / 0.25 (the down-only figures are also kept), computed per trade at that day's SPX level;
    annualised return on that capital from the complete-data TEST mean; drawdown probability and length by a circular moving-block
    bootstrap (block 20 sessions; also 5 and 60) of the complete-data daily return series r_t = P&L_t / capital_t (0 on sessions
    without a trade), 3,000 paths, seed 7.
Outputs (results/): stress_trades.csv.gz, stress_summary.csv, worst_moves.csv, margin_summary.csv, capital_returns.csv,
drawdown_bootstrap.csv, stress_meta.json.
"""
import os, sys, glob, json
import numpy as np, pandas as pd, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim  # noqa: E402
import analyze as A  # noqa: E402

RES = A.RES
SHOCKS = [-0.15, -0.10, -0.0842, -0.05, 0.05, 0.0842, 0.10, 0.15]
PM_GRID = np.round(np.arange(-0.08, 0.06 + 1e-9, 0.001), 4)
BUDGET = 0.25
BLOCKS = [20, 5, 60]; NPATH = 3000; SEED = 7
EOD_GLOB = os.path.join(sim.L.SP, 'theta', 'cache', 'index_tests', 'index_history_eod__*symbol=SPX.csv.gz')


def parse(cid):
    cell, e, tp, st, ex, F, var = cid.split('|')
    return dict(cid=cid, cell=cell, entry=e, tp=int(tp[2:]) / 100, stop=float(st[2:]), exit=ex, filter=F, variant=var)


def config_trades(cfg, out=None):
    """Trade rows of one configuration (filter applied), with strikes and credits, on the v2 trade files (or `out`)."""
    ents = [cfg['entry']] + (['14:05'] if cfg['filter'] == 'F2' and cfg['entry'] != '14:05' else [])
    fs = sorted(glob.glob((out or A.OUT) + '/trades/*.parquet'))
    q = pl.concat([pl.read_parquet(f).filter((pl.col('cell') == cfg['cell']) & pl.col('entry').is_in(ents) & ((pl.col('tp') - cfg['tp']).abs() < 1e-9)
                                              & ((pl.col('stop') - cfg['stop']).abs() < 1e-9) & (pl.col('exit') == cfg['exit'])) for f in fs])
    T = A.topd(q)
    if cfg['variant'] == 'P': T = T[T['wing_bid0'] == 0]
    dates = sorted(sim.regular_sessions()); fl, _ = A.flags(dates); fl = fl.set_index('date')
    T = T.join(fl, on='date')
    F = cfg['filter']
    if F == 'F2' and cfg['entry'] != '14:05':
        T = T[(T['fomc'] & (T['entry'] == '14:05')) | (~T['fomc'] & (T['entry'] == cfg['entry']))]
    else:
        T = T[T['entry'] == cfg['entry']]
        if F == 'F1': T = T[~T['fomc']]
        elif F == 'F3': T = T[~(T['fomc'] | T['month_end'])]
        elif F == 'F4': T = T[~(T['fomc'] | T['cpi'] | T['nfp'])]
    T = T.sort_values('date').reset_index(drop=True)
    T['period'] = np.where(T['date'] <= A.PER['TRAIN'][1], 'TRAIN', 'TEST')
    return T


def leg_quotes(T):
    """Entry bid/ask of every leg (from the complete chain at the entry minute)."""
    out = []
    for r in T.itertuples(index=False):
        hh, mm = int(r.entry_hm[:2]), int(r.entry_hm[3:])
        c = pl.scan_parquet(sim.chain_path(r.date)).filter(
            (pl.col('timestamp').dt.hour() == hh) & (pl.col('timestamp').dt.minute() == mm)).collect()
        q = {(row['strike'], row['right']): (row['bid'], row['ask']) for row in c.select(['strike', 'right', 'bid', 'ask']).to_dicts()}
        rec = dict(date=r.date)
        for nm, k, rt in (('sc', r.kc, 'CALL'), ('sp', r.kp, 'PUT'), ('wc', r.kcw, 'CALL'), ('wp', r.kpw, 'PUT')):
            b, a = q.get((k, rt), (np.nan, np.nan)) if np.isfinite(k) else (np.nan, np.nan)
            rec[f'{nm}_bid'] = b; rec[f'{nm}_ask'] = a
        out.append(rec)
    return pd.DataFrame(out)


def intr_c(K, S): return np.maximum(S - K, 0.0)
def intr_p(K, S): return np.maximum(K - S, 0.0)


def settle_pnl(T, S):
    """Settlement P&L ($/lot) of each trade if SPX settles at S (array)."""
    v = T['credit'].values - intr_c(T['kc'].values, S) - intr_p(T['kp'].values, S)
    w = np.isfinite(T['kcw'].values)
    v = v + np.where(w, intr_c(np.nan_to_num(T['kcw'].values), S) + intr_p(np.nan_to_num(T['kpw'].values), S), 0.0)
    return v * 100 - T['n_legs'].values * sim.FEE


def margins(T, Q):
    I = T['spot'].values; m = Q.set_index('date').loc[T['date']].reset_index()
    pc = m['sc_bid'].values; pp = m['sp_bid'].values
    otm_c = np.maximum(T['kc'].values - I, 0); otm_p = np.maximum(I - T['kp'].values, 0)
    winged = np.isfinite(T['kcw'].values)
    req = {}
    for tag, put_min in (('regt', T['kp'].values), ('regt_simple', I)):
        rc = pc * 100 + np.maximum(0.15 * I * 100 - otm_c * 100, 0.10 * I * 100)
        rp = pp * 100 + np.maximum(0.15 * I * 100 - otm_p * 100, 0.10 * put_min * 100)
        naked = np.maximum(rc, rp) + np.where(rc >= rp, pp, pc) * 100
        width = np.where(winged, np.maximum(np.nan_to_num(T['kcw'].values) - T['kc'].values, T['kp'].values - np.nan_to_num(T['kpw'].values)) * 100, np.nan)
        req[tag] = np.where(winged, width, naked)
    # portfolio-margin approximation: worst expiration-value loss over -8 % .. +6 %
    S = I[:, None] * (1 + PM_GRID[None, :])
    v = T['credit'].values[:, None] - intr_c(T['kc'].values[:, None], S) - intr_p(T['kp'].values[:, None], S)
    v = v + np.where(winged[:, None], intr_c(np.nan_to_num(T['kcw'].values)[:, None], S) + intr_p(np.nan_to_num(T['kpw'].values)[:, None], S), 0.0)
    req['pm_approx'] = np.maximum(-(v.min(axis=1)) * 100, 0.0)
    req['pm_worst_move'] = PM_GRID[v.argmin(axis=1)]
    return req


def worst_moves():
    eod = {}
    for f in sorted(glob.glob(EOD_GLOB)):
        e = pd.read_csv(f)
        for lt, c in zip(e['last_trade'].astype(str), e['close']): eod[lt[:10]] = float(c)
    for d, c in sim.CBOE.items(): eod.setdefault(d, c)
    early = {r['date'] for r in __import__('csv').DictReader(open(sim.L.CALENDAR)) if r['type'] == 'early_close'}
    rows = []
    for d in sim.L.trading_sessions('2017-06-01', '2026-10-09'):
        if d in early: continue
        try: s = pl.read_parquet(sim.L.path('index', 'SPX', d))
        except FileNotFoundError: continue
        hm = s['timestamp'].dt.strftime('%H:%M').to_list(); p = s['price'].to_list(); m = dict(zip(hm, p))
        rows.append(dict(date=d, p1300=m.get('13:00'), p1405=m.get('14:05'), p1600=m.get('16:00'), close=eod.get(d)))
    D = pd.DataFrame(rows)
    out = []
    for ent in ('13:00', '14:05'):
        col = 'p' + ent.replace(':', '')
        for cl in ('close', 'p1600'):
            mv = (D[cl] / D[col] - 1) * 100
            g = D.assign(move=mv).dropna(subset=['move'])
            for direction, asc in (('down', True), ('up', False)):
                top = g.sort_values('move', ascending=asc).head(10)
                for rank, r in enumerate(top.itertuples(index=False), start=1):
                    out.append(dict(entry=ent, close_source='official close' if cl == 'close' else '16:00 print', direction=direction, rank=rank,
                                    date=r.date, spx_entry=getattr(r, col), spx_close=getattr(r, cl), move_pct=round(r.move, 3)))
    meta = dict(sessions=int(len(D)), first=D['date'].min(), last=D['date'].max(),
                missing_close=int(D['close'].isna().sum()), missing_1300=int(D['p1300'].isna().sum()), missing_1405=int(D['p1405'].isna().sum()))
    return pd.DataFrame(out), meta


def day_path(d='2025-04-09'):
    """SPX minute path of one session with the committed random-entry minutes of that day (results/spx_{d}_path.csv)."""
    s = pl.read_parquet(sim.L.path('index', 'SPX', d)).with_columns(pl.col('timestamp').dt.strftime('%H:%M').alias('hm'))
    s = s.with_columns((pl.col('price') / pl.col('price').shift(1) - 1).alias('ret_1m'))
    rnd = {m: f'R{k}' for (dd, k), m in sim.random_minutes().items() if dd == d}
    out = A.topd(s.select(['hm', 'price', 'ret_1m']))
    out['label'] = out['hm'].map(lambda m: ', '.join(x for x in [rnd.get(m, ''), 'fixed entry' if m in sim.ENTRIES else ''] if x))
    out['cboe_close'] = sim.CBOE[d]
    out.to_csv(os.path.join(RES, f'spx_{d}_path.csv'), index=False, float_format='%.6g')


def block_boot(r, L, n_paths, horizon, seed):
    """Circular moving-block bootstrap paths of length `horizon` from series r."""
    rng = np.random.default_rng(seed); n = len(r); nb = int(np.ceil(horizon / L))
    starts = rng.integers(0, n, (n_paths, nb))
    idx = (starts[:, :, None] + np.arange(L)[None, None, :]) % n
    return r[idx.reshape(n_paths, -1)[:, :horizon]]


def dd_stats(R):
    """R: (paths, T) daily returns on capital.  Compounded equity; max drawdown and longest under-water spell (sessions)."""
    W = np.cumprod(1 + R, axis=1); W = np.concatenate([np.ones((R.shape[0], 1)), W], axis=1)
    W = np.where(np.minimum.accumulate(W > 0, axis=1), W, 0.0)
    peak = np.maximum.accumulate(W, axis=1); dd = W / peak - 1
    maxdd = dd.min(axis=1)
    under = dd < -1e-12
    # longest run of consecutive under-water sessions
    longest = np.zeros(R.shape[0], int)
    run = np.zeros(R.shape[0], int)
    for t in range(under.shape[1]):
        run = np.where(under[:, t], run + 1, 0); longest = np.maximum(longest, run)
    return maxdd, longest, W[:, -1]


def main():
    sel = json.load(open(os.path.join(RES, 'selection_train.json')))
    osel = json.load(open(A.ORIG_SEL))
    configs = [('orig_S2', osel['S2']['cid']), ('TE_rule', A.TE_RULE)]
    if sel['S2'] and sel['S2']['cid'] != osel['S2']['cid']: configs.insert(1, ('reselected_S2', sel['S2']['cid']))
    meta = dict(configs=configs, shocks=SHOCKS, budget=BUDGET, blocks=BLOCKS, paths=NPATH, seed=SEED,
                margin_rule_sources=[
                    'Cboe Rule 10.3(c)(5), as described in SEC Release 34-97019 / 88 FR 14416 (2023-03-08): "a margin deposit for short cash-settled index options in an amount equal to 100% of the current market value of the option plus 15% (if overlying a broad-based index) ... of the amount equal to the index value multiplied by the index multiplier minus the amount, if any, by which the option is out-of-the-money. The minimum margin required for such an option is 100% of the option current market value plus 10% of the index value multiplied by the index multiplier for a call or 10% of the exercise price multiplied by the index multiplier for a put."',
                    'Cboe "Strategy-based Margin" page (cboe.com/markets/us/options/margin/strategy-based-margin), Short Put and Short Call, initial requirement: "short put or short call requirement, whichever is greater, plus the option proceeds of the other side."'])
    allT, summ, mrg, caps, boots = [], [], [], [], []
    ses_all = sim.regular_sessions()
    for lab, cid in configs:
        cfg = parse(cid); T = config_trades(cfg); Q = leg_quotes(T)
        T['label'] = lab; T['cid'] = cid
        for x in SHOCKS: T[f'shock_{x:+.4f}'] = settle_pnl(T, T['spot'].values * (1 + x))
        T['pnl_check'] = settle_pnl(T, T['settle'].values)   # equals pnl for no-TP/no-stop E2 configurations
        mg = margins(T, Q)
        for k, v in mg.items(): T[k] = v
        T = T.join(Q.set_index('date'), on='date')
        T['loss10'] = -np.minimum(T['shock_-0.1000'], T['shock_+0.1000']); T['loss15'] = -np.minimum(T['shock_-0.1500'], T['shock_+0.1500'])
        T['cap10'] = T['loss10'] / BUDGET; T['cap15'] = T['loss15'] / BUDGET
        T['cap10_down'] = -T['shock_-0.1000'] / BUDGET; T['cap15_down'] = -T['shock_-0.1500'] / BUDGET
        T['notional'] = T['spot'] * 100
        allT.append(T)
        for per, g in (('TRAIN', T[T['period'] == 'TRAIN']), ('TEST', T[T['period'] == 'TEST']), ('ALL', T)):
            s = dict(label=lab, cid=cid, period=per, n=len(g), spot_median=g['spot'].median(), credit_median_pts=g['credit'].median(),
                     actual_worst=g['pnl'].min(), actual_worst_date=g.loc[g['pnl'].idxmin(), 'date'], actual_mean=g['pnl'].mean(),
                     pnl_check_maxabs=float((g['pnl_check'] - g['pnl']).abs().max()))
            for x in SHOCKS:
                c = g[f'shock_{x:+.4f}']
                s[f'shock{x:+.2%}_median'] = c.median(); s[f'shock{x:+.2%}_worst'] = c.min()
                s[f'shock{x:+.2%}_median_pct_notional'] = (c / g['notional']).median() * 100
            last = g.iloc[-1]
            s['last_date'] = last['date']; s['last_spot'] = last['spot']
            for x in SHOCKS: s[f'shock{x:+.2%}_last'] = last[f'shock_{x:+.4f}']
            summ.append(s)
            mrg.append(dict(label=lab, cid=cid, period=per, n=len(g), regt_median=g['regt'].median(), regt_min=g['regt'].min(), regt_max=g['regt'].max(),
                            regt_simple_median=g['regt_simple'].median(), regt_pct_notional_median=(g['regt'] / g['notional']).median() * 100,
                            pm_approx_median=g['pm_approx'].median(), pm_approx_min=g['pm_approx'].min(), pm_approx_max=g['pm_approx'].max(),
                            pm_pct_notional_median=(g['pm_approx'] / g['notional']).median() * 100,
                            pm_worst_move_share_down=float((g['pm_worst_move'] < 0).mean()),
                            cap10_median=g['cap10'].median(), cap15_median=g['cap15'].median(), cap10_down_median=g['cap10_down'].median(), cap15_down_median=g['cap15_down'].median(),
                            cap10_last=g['cap10'].iloc[-1], cap15_last=g['cap15'].iloc[-1], regt_last=g['regt'].iloc[-1], pm_last=g['pm_approx'].iloc[-1]))
        # capital, annualised return and block-bootstrap drawdowns (complete-data daily series)
        n_ses = {p_: len([d for d in ses_all if A.PER[p_][0] <= d <= A.PER[p_][1]]) for p_ in ('TRAIN', 'TEST')}; n_ses['ALL'] = len(ses_all)
        for capcol in ('cap10', 'cap15'):
            for per in ('TEST', 'ALL'):
                g = T if per == 'ALL' else T[T['period'] == per]
                tpy = len(g) * 252 / n_ses[per]
                ratio = g['pnl'] / g[capcol]
                caps.append(dict(label=lab, cid=cid, capital_rule=capcol, period=per, n=len(g), sessions=n_ses[per], trades_per_year=tpy,
                                 mean_pnl=g['pnl'].mean(), capital_median=g[capcol].median(), capital_last=g[capcol].iloc[-1],
                                 ann_return_on_median_capital_pct=g['pnl'].mean() * tpy / g[capcol].median() * 100,
                                 ann_return_mean_ratio_pct=ratio.mean() * tpy * 100,
                                 worst_day_pct_of_capital=float((g['pnl'] / g[capcol]).min() * 100), worst_day_date=g.loc[ratio.idxmin(), 'date'],
                                 regt_over_capital_median=float((g['regt'] / g[capcol]).median())))
                pses = [d for d in ses_all if (per == 'ALL' or (A.PER[per][0] <= d <= A.PER[per][1]))]
                rr = pd.Series(0.0, index=pses); rr.loc[g['date'].values] = ratio.values; r = rr.values
                hist_dd, hist_long, hist_end = dd_stats(r[None, :])
                for L in BLOCKS:
                    for horizon in (252, len(r)):
                        R = block_boot(r, L, NPATH, horizon, SEED)
                        dd, lg, end = dd_stats(R)
                        boots.append(dict(label=lab, cid=cid, capital_rule=capcol, source=per, block=L, horizon_sessions=horizon, paths=NPATH, seed=SEED,
                                          hist_maxdd=float(hist_dd[0]), hist_longest_underwater=int(hist_long[0]), hist_end=float(hist_end[0]),
                                          median_maxdd=float(np.median(dd)), p95_maxdd=float(np.percentile(dd, 5)),
                                          p_dd_gt10=float((dd < -0.10).mean()), p_dd_gt20=float((dd < -0.20).mean()), p_dd_gt30=float((dd < -0.30).mean()),
                                          p_dd_gt50=float((dd < -0.50).mean()), median_longest_underwater=float(np.median(lg)),
                                          p95_longest_underwater=float(np.percentile(lg, 95)), p_end_below_start=float((end < 1).mean()),
                                          median_end=float(np.median(end))))
    pd.concat(allT).to_csv(os.path.join(RES, 'stress_trades.csv.gz'), index=False, float_format='%.6g')
    pd.DataFrame(summ).to_csv(os.path.join(RES, 'stress_summary.csv'), index=False, float_format='%.6g')
    pd.DataFrame(mrg).to_csv(os.path.join(RES, 'margin_summary.csv'), index=False, float_format='%.6g')
    pd.DataFrame(caps).to_csv(os.path.join(RES, 'capital_returns.csv'), index=False, float_format='%.6g')
    pd.DataFrame(boots).to_csv(os.path.join(RES, 'drawdown_bootstrap.csv'), index=False, float_format='%.6g')
    W, wm = worst_moves(); W.to_csv(os.path.join(RES, 'worst_moves.csv'), index=False)
    day_path('2025-04-09')
    meta['worst_moves_series'] = wm
    json.dump(meta, open(os.path.join(RES, 'stress_meta.json'), 'w'), indent=1, default=str)
    pd.set_option('display.width', 250)
    print(pd.DataFrame(mrg).round(1).to_string()); print(pd.DataFrame(caps).round(2).to_string())
    print(W[W['rank'] <= 3].to_string())


if __name__ == '__main__':
    main()
