"""Tail stress of the TRAIN-selected configurations (etf_v2; post-hoc, not pre-registered, used for the COMPASS §10 tail-survival gate).
A. Historical entry-to-close moves of SPY, QQQ, IWM from the 1-minute underlying series 2017-06-01 .. 2026-10-09 (all full sessions;
   early closes excluded): move = close of the 15:59 bar / close of the bar stamped T-1 - 1, for T = 10:00, 11:00, 13:00, 14:05, and the
   largest absolute move over every entry minute 10:00..14:30.  -> results/stress_hist_moves.csv (worst 10 down / up per ticker x entry),
   results/stress_hist_summary.csv (worst down / up and dates per ticker x entry).
B. For every selection in results/selected_test.csv, each TEST trade is re-valued as if the underlying settled at spot_entry x (1 + x)
   for x in +-5 %, +-8.42 %, +-10 %, +-15 % and at the worst historical down / up move of that ticker and entry time (A): P&L per 1-lot =
   credit - 100 x intrinsic(shorts) + 100 x intrinsic(longs) - $0.70 x legs (opening fees; legs expire, no closing fee).  This is the
   UNPROTECTED loss (no stop fill assumed: gaps, halts and after-hours moves cannot be stopped; COMPASS §10 measures entry to settlement).
   The 'stop at trigger' column is the optimistic alternative for configurations with a stop (loss = stop multiple x credit + fees).
   Capital per lot so that the stress loss is <= 8 % of capital (the §9 H15 budget) = loss / 0.08.
   Margin estimates per lot at entry (formula-based, NOT broker-verified): Reg-T naked short = credit + max over the two short legs of
   max(p x S - OTM amount, 10 % x S (call) or 10 % x K (put)), p = 20 % (equity-option rate) and 15 % (broad-based-index rate); iron condor
   = widest wing width x 100.  Portfolio-margin-style scenario loss at expiry intrinsic at -8 %/+6 % and at +-15 % from entry spot.
   -> results/stress_selected.csv
C. Realized P&L of each selection on the TEST days with the largest underlying moves (2025-04-03 .. 04-10 and the ticker's 5 largest
   absolute entry-to-close moves in TEST) -> results/stress_extreme_days.csv"""
import os, sys
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import analyze as A

SCEN = [-0.15, -0.10, -0.0842, -0.05, 0.05, 0.0842, 0.10, 0.15]
BUDGET = 0.08
EVENT_DAYS = ['2025-04-03', '2025-04-04', '2025-04-07', '2025-04-08', '2025-04-09', '2025-04-10']


def hist_moves():
    early = C.early_closes()
    sess = [d for d in C.L.trading_sessions('2017-06-01', C.LAST) if d not in early]
    rows = []
    for tk in C.TICKERS:
        for j, d in enumerate(sess):
            try: u = C.L.underlying(tk, d)
            except FileNotFoundError: continue
            u = u.with_columns(((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32)) - C.M0).alias('mi'))
            close = np.full(C.NM, np.nan)
            uu = u.filter((pl.col('mi') >= 0) & (pl.col('mi') < C.NM) & pl.col('close').is_not_null())
            close[uu['mi'].to_numpy()] = uu['close'].to_numpy().astype(float)
            Sset = C.last_close_before(close, C.SETTLE_BAR - C.M0 + 1)
            rec = dict(tk=tk, date=d, settle=Sset)
            for lab, m in C.ENTRIES.items():
                S = C.last_close_before(close, m - C.M0); rec[lab] = Sset / S - 1 if S == S and S > 0 else np.nan
            mv = []
            for m in range(C.RAND_LO, C.RAND_HI + 1):
                S = C.last_close_before(close, m - C.M0); mv.append(Sset / S - 1 if S == S and S > 0 else np.nan)
            mv = np.array(mv)
            rec['any_min'] = float(np.nanmin(mv)); rec['any_max'] = float(np.nanmax(mv))
            rows.append(rec)
        print('hist', tk, len(rows), flush=True)
    return pl.DataFrame(rows)


def leg_value(S, K, right): return np.maximum(S - K, 0.0) if right == 'C' else np.maximum(K - S, 0.0)


def settle_pnl(tr, Snew):
    """P&L per 1-lot if every leg expires at Snew (array per trade)."""
    v = tr['credit'].to_numpy() - 100 * (leg_value(Snew, tr['k_sc'].to_numpy(), 'C') + leg_value(Snew, tr['k_sp'].to_numpy(), 'P'))
    four = np.isfinite(tr['k_lc'].to_numpy())
    lc = np.where(four, tr['k_lc'].to_numpy(), np.inf); lp = np.where(four, tr['k_lp'].to_numpy(), -np.inf)
    v = v + 100 * (np.where(four, leg_value(Snew, lc, 'C'), 0) + np.where(four, leg_value(Snew, lp, 'P'), 0))
    return v - C.FEE * np.where(four, 4, 2)


def main():
    hp = os.path.join(C.WORK, 'hist_moves.parquet')
    if os.path.exists(hp): H = pl.read_parquet(hp)
    else:
        H = hist_moves(); H.write_parquet(hp)
    if len(sys.argv) > 1 and sys.argv[1] == 'hist': return
    # ---- A: worst moves
    rows = []; summ = []
    for tk in C.TICKERS:
        h = H.filter(pl.col('tk') == tk)
        for lab in list(C.ENTRIES) + ['any']:
            if lab == 'any':
                dn = h.sort('any_min').head(10).select(['date', pl.col('any_min').alias('move')])
                up = h.sort('any_max', descending=True).head(10).select(['date', pl.col('any_max').alias('move')])
            else:
                dn = h.drop_nans(lab).sort(lab).head(10).select(['date', pl.col(lab).alias('move')])
                up = h.drop_nans(lab).sort(lab, descending=True).head(10).select(['date', pl.col(lab).alias('move')])
            for side, X in (('down', dn), ('up', up)):
                for i, r in enumerate(X.iter_rows(named=True)):
                    rows.append(dict(ticker=tk, entry=lab, side=side, rank=i + 1, date=r['date'], move_pct=round(100 * r['move'], 3)))
            summ.append(dict(ticker=tk, entry=lab, sessions=h.height, first=h['date'].min(), last=h['date'].max(),
                             worst_down_pct=round(100 * dn['move'][0], 3), worst_down_date=dn['date'][0],
                             worst_up_pct=round(100 * up['move'][0], 3), worst_up_date=up['date'][0],
                             move_20250409_pct=(round(100 * h.filter(pl.col('date') == '2025-04-09')[lab if lab != 'any' else 'any_max'][0], 3)
                                                if h.filter(pl.col('date') == '2025-04-09').height else None)))
    pl.DataFrame(rows).write_csv(os.path.join(C.OUT, 'stress_hist_moves.csv'))
    HS = pl.DataFrame(summ); HS.write_csv(os.path.join(C.OUT, 'stress_hist_summary.csv'))
    worst = {(r['ticker'], r['entry']): (r['worst_down_pct'] / 100, r['worst_up_pct'] / 100, r['worst_down_date'], r['worst_up_date']) for r in HS.iter_rows(named=True)}
    # ---- B: stress of the selections
    S = pl.read_csv(os.path.join(C.OUT, 'selected_test.csv'))
    out = []; ext = []
    cache = {}
    for sel in S.iter_rows(named=True):
        scope, cfg = sel['scope'], sel['cfg']
        if scope not in cache:
            T = pl.concat([pl.read_parquet(os.path.join(C.WORK, f'trades_{tk}_TEST.parquet')).select(A.KEEP + ['spot', 'k_sc', 'k_sp', 'k_lc', 'k_lp'])
                           for tk in A.SCOPES[scope]])
            cache[scope] = A.apply_filters(T.filter(pl.col('entry').is_in(list(C.ENTRIES))))
        tr = cache[scope].filter(pl.col('cfg') == cfg).sort(['date', 'tk'])
        sk, e, tp, st, ex, f = cfg.split('|'); stop = int(st[2:])
        spot = tr['spot'].to_numpy(); credit = tr['credit'].to_numpy(); four = np.isfinite(tr['k_lc'].to_numpy())
        rec = dict(scope=scope, selection=sel['selection'], cfg=cfg, n=tr.height, spot_median=round(float(np.median(spot)), 2),
                   credit_median=round(float(np.median(credit)), 2), realized_worst_trade=round(float(tr['pnl'].min()), 2),
                   realized_worst_date=tr.sort('pnl')['date'][0])
        for x in SCEN:
            p = settle_pnl(tr, spot * (1 + x))
            rec[f'pnl_{100 * x:+.2f}_median'] = round(float(np.median(p)), 2); rec[f'pnl_{100 * x:+.2f}_worst'] = round(float(p.min()), 2)
        # entry time of the trade (F2 trades on FOMC days are entered at 14:05) -> historical worst for the ticker and that entry
        hd = np.array([worst[(t, '14:05' if (f == 'F2' and d in A.FOMC) else e)][0] for t, d in zip(tr['tk'].to_list(), tr['date'].to_list())])
        hu = np.array([worst[(t, '14:05' if (f == 'F2' and d in A.FOMC) else e)][1] for t, d in zip(tr['tk'].to_list(), tr['date'].to_list())])
        pd_ = settle_pnl(tr, spot * (1 + hd)); pu = settle_pnl(tr, spot * (1 + hu))
        rec.update(hist_down_pct='; '.join(sorted({f"{t} {100 * worst[(t, e)][0]:+.2f} % ({worst[(t, e)][2]})" for t in A.SCOPES[scope]})),
                   hist_up_pct='; '.join(sorted({f"{t} {100 * worst[(t, e)][1]:+.2f} % ({worst[(t, e)][3]})" for t in A.SCOPES[scope]})),
                   pnl_hist_down_median=round(float(np.median(pd_)), 2), pnl_hist_down_worst=round(float(pd_.min()), 2),
                   pnl_hist_up_median=round(float(np.median(pu)), 2), pnl_hist_up_worst=round(float(pu.min()), 2))
        p15 = np.minimum(settle_pnl(tr, spot * 1.15), settle_pnl(tr, spot * 0.85))
        p10 = np.minimum(settle_pnl(tr, spot * 1.10), settle_pnl(tr, spot * 0.90))
        ph = np.minimum(pd_, pu)
        rec.update(capital_8pct_budget_10pct_median=round(float(-np.median(p10) / BUDGET), 0), capital_8pct_budget_15pct_median=round(float(-np.median(p15) / BUDGET), 0),
                   capital_8pct_budget_15pct_worst=round(float(-p15.min() / BUDGET), 0), capital_8pct_budget_hist_median=round(float(-np.median(ph) / BUDGET), 0),
                   stop_trigger_loss_median=(round(float(-stop * np.median(credit) - C.FEE * (4 if four.any() else 2) * 2), 2) if stop else None))
        # margin estimates
        kc = tr['k_sc'].to_numpy(); kp = tr['k_sp'].to_numpy()
        for pr in (0.20, 0.15):
            xc = np.maximum(pr * spot - np.maximum(kc - spot, 0), 0.10 * spot); xp = np.maximum(pr * spot - np.maximum(spot - kp, 0), 0.10 * kp)
            regt = credit + 100 * np.maximum(xc, xp)
            if four.any():
                wid = 100 * np.maximum(tr['k_lc'].to_numpy() - kc, kp - tr['k_lp'].to_numpy()); regt = np.where(four, wid, regt)
            rec[f'regt_{int(pr * 100)}pct_median'] = round(float(np.median(regt)), 0)
        rec['pm_scen_-8_+6_median'] = round(float(-np.median(np.minimum(settle_pnl(tr, spot * 0.92), settle_pnl(tr, spot * 1.06)))), 0)
        rec['pm_scen_15_median'] = round(float(-np.median(p15)), 0)
        out.append(rec)
        # ---- C: realized on extreme days
        h = H.filter(pl.col('tk').is_in(list(A.SCOPES[scope])) & (pl.col('date') >= C.TEST[0]) & (pl.col('date') <= C.TEST[1]))
        big = h.drop_nans(e).drop_nulls(e).with_columns(pl.col(e).abs().alias('am')).sort('am', descending=True).head(5)['date'].to_list()
        for d in sorted(set(EVENT_DAYS) | set(big)):
            x = tr.filter(pl.col('date') == d)
            mv = h.filter(pl.col('date') == d)
            ext.append(dict(scope=scope, selection=sel['selection'], cfg=cfg, date=d, traded=x.height, pnl=round(float(x['pnl'].sum()), 2) if x.height else None,
                            exit=';'.join(x['reason'].to_list()), move_from_entry_pct='; '.join(f"{t} {100 * v:+.2f}" for t, v in zip(mv['tk'].to_list(), mv[e].to_list()))))
    pl.DataFrame(out).write_csv(os.path.join(C.OUT, 'stress_selected.csv'))
    pl.DataFrame(ext).write_csv(os.path.join(C.OUT, 'stress_extreme_days.csv'))
    print(pl.DataFrame(out).select(['scope', 'selection', 'cfg', 'n', 'pnl_-15.00_median', 'pnl_+15.00_median', 'pnl_hist_down_worst', 'pnl_hist_up_worst']))


if __name__ == '__main__':
    main()
