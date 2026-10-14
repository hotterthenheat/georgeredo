"""POST-HOC diagnostics (not pre-registered, not used for selection; written after the TEST results were seen) that explain the
hold-to-expiry (E2) result and bound its realism.  Writes results/diagnostics.md and results/diag_*.csv.
A. Settlement price: the 16:00 close used by E2 (close of the 15:59 bar) vs ThetaData's SPY EOD close, and the after-hours move to
   the 17:15 quote (SPY only; EOD files from the index_tests cache).
B. E2 sensitivity for SPY: re-value legs that expired (reason EXPIRE) (i) at the EOD close, (ii) pessimistically against after-hours
   exercise: each short leg owes max(intrinsic at the close, intrinsic at the 17:15 mid).
C. Last-5-minute ATM straddle at 15:55: quoted mid and ask vs the realized |S(16:00) - K| (what E1 pays and E2 avoids).
D. E2 - E1 decomposition for the straddle entered at 14:05 (no TP, no stop, no filter): half-spread, extrinsic at 15:55, 15:55->16:00 move."""
import os, sys, glob, gzip
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

EOD_GLOB = os.path.join(C.SP, 'theta', 'cache', 'index_tests', 'stock_history_eod__end_date=*__start_date=*__symbol=SPY.csv.gz')


def spy_eod():
    fs = sorted(glob.glob(EOD_GLOB)); parts = []
    for f in fs:
        df = pl.read_csv(f, infer_schema_length=0)
        if df.height: parts.append(df)
    df = pl.concat(parts).with_columns(date=pl.col('created').str.slice(0, 10), close=pl.col('close').cast(pl.Float64),
                                       ah_mid=(pl.col('bid').cast(pl.Float64) + pl.col('ask').cast(pl.Float64)) / 2)
    return {r['date']: (r['close'], r['ah_mid']) for r in df.select(['date', 'close', 'ah_mid']).iter_rows(named=True)}


def boot(v, dates):
    v = np.asarray(v, float)
    lo, hi = C.boot_ci(v, list(dates)); return f'{v.mean():+.2f} [{lo:+.2f}, {hi:+.2f}]'


def intr(right, K, S): return max(S - K, 0.0) if right == 'C' else max(K - S, 0.0)


def main():
    out = ['# Post-hoc diagnostics of the hold-to-expiry (E2) result\n',
           'Not pre-registered and not used for any selection; computed after the TEST results were seen.  CIs: day-clustered, 5,000 draws, seed 7.\n']
    eod = spy_eod()
    # ---------------- A
    rows = []
    for per in ('TRAIN', 'TEST'):
        days = pl.read_parquet(os.path.join(C.WORK, f'days_SPY_{per}.parquet')).filter(pl.col('status') == 'ok')['date'].to_list()
        tr = pl.read_parquet(os.path.join(C.WORK, f'trades_SPY_{per}.parquet')).select(['date', 'settle']).unique('date')
        st = dict(tr.rows())
        for d in days:
            if d in eod and d in st and eod[d][0] is not None:
                rows.append(dict(period=per, date=d, settle_1559=st[d], eod_close=eod[d][0], ah_mid=eod[d][1]))
    A = pl.DataFrame(rows).with_columns(d_close=pl.col('eod_close') - pl.col('settle_1559'), ah_move=pl.col('ah_mid') - pl.col('eod_close'))
    A.write_csv(os.path.join(C.OUT, 'diag_settlement_spy.csv'))
    out.append('## A. Settlement price (SPY)\n')
    out.append('| period | days | mean (EOD close − 15:59-bar close) $ | median abs $ | p95 abs $ | max abs $ | median abs after-hours move to 17:15 mid $ | p95 abs | days with abs move > $0.50 | > $1.00 |')
    out.append('|---|---|---|---|---|---|---|---|---|---|')
    for per in ('TRAIN', 'TEST'):
        a = A.filter(pl.col('period') == per); x = a['d_close'].to_numpy(); y = a['ah_move'].drop_nulls().to_numpy()
        out.append(f'| {per} | {a.height} | {x.mean():+.4f} | {np.median(np.abs(x)):.3f} | {np.percentile(np.abs(x), 95):.3f} | {np.abs(x).max():.2f} | '
                   f'{np.median(np.abs(y)):.3f} | {np.percentile(np.abs(y), 95):.3f} | {(np.abs(y) > 0.5).sum()} | {(np.abs(y) > 1.0).sum()} |')
    # ---------------- B
    out.append('\n## B. E2 sensitivity (SPY): re-valuing expired legs\n')
    out.append('Columns: (1) as run, legs valued at the 15:59-bar close; (2) at the EOD close; (3) auto-exercise only (legs ITM at the EOD close are exercised, '
               'the delivered shares are closed at the 17:15 quote mid); (4) rational after-hours exercise (every leg is worth its intrinsic value at the 17:15 '
               'mid: holders exercise iff in the money after hours, shares closed there); (5) pessimistic: short legs owe max(intrinsic at the close, at the 17:15 mid).\n')
    out.append('| config | period | n | (1) as run | (2) EOD close | (3) auto-exercise, shares closed 17:15 | (4) rational after-hours exercise | (5) pessimistic |')
    out.append('|---|---|---|---|---|---|---|---|')
    cfgs = ['S0|14:05|tp0|st1|E2|F3', 'S0.5|14:05|tp0|st2|E2|F3', 'S0|14:05|tp0|st2|E2|F3', 'S0|14:05|tp0|st0|E2|F0', 'S1|14:05|tp0|st0|E2|F0']
    fomc = C.fomc_days(); me = C.month_ends()
    for per in ('TRAIN', 'TEST'):
        T = pl.read_parquet(os.path.join(C.WORK, f'trades_SPY_{per}.parquet')).filter(pl.col('entry').is_in(list(C.ENTRIES)))
        for cfg in cfgs:
            sk, e, tp, st, ex, f = cfg.split('|')
            q = T.filter((pl.col('sk') == sk) & (pl.col('tp') == int(tp[2:])) & (pl.col('st') == int(st[2:])) & (pl.col('ex') == ex))
            if f == 'F3': q = q.filter(pl.col('entry') == e).filter(~pl.col('date').is_in(list(fomc | me)))
            elif f == 'F0': q = q.filter(pl.col('entry') == e)
            q = q.filter(pl.col('date').is_in([d for d, v in eod.items() if v[1] is not None and v[1] == v[1]])).sort('date')
            p0 = []; p1 = []; p2 = []; p3 = []; p4 = []; ds = []
            for r in q.iter_rows(named=True):
                p = r['pnl']; p0.append(p); ds.append(r['date'])
                if r['reason'] != 'EXPIRE': p1.append(p); p2.append(p); p3.append(p); p4.append(p); continue
                Sc, Sah = eod[r['date']]; S0 = r['settle']
                legs = [('C', r['k_sc'], -1), ('P', r['k_sp'], -1)]
                if r['k_lc'] == r['k_lc'] and r['k_lc'] is not None: legs += [('C', r['k_lc'], +1), ('P', r['k_lp'], +1)]
                d1 = d2 = d3 = d4 = 0.0
                for rt, K, sg in legs:
                    v0 = intr(rt, K, S0); v1 = intr(rt, K, Sc)
                    itm = (Sc > K) if rt == 'C' else (Sc < K)
                    v3 = ((Sah - K) if rt == 'C' else (K - Sah)) if itm else 0.0
                    v4 = intr(rt, K, Sah)
                    v2 = max(v1, v4) if sg < 0 else v1
                    d1 += sg * (v1 - v0); d2 += sg * (v2 - v0); d3 += sg * (v3 - v0); d4 += sg * (v4 - v0)
                p1.append(p + 100 * d1); p2.append(p + 100 * d2); p3.append(p + 100 * d3); p4.append(p + 100 * d4)
            out.append(f'| {cfg} | {per} | {len(p0)} | {boot(p0, ds)} | {boot(p1, ds)} | {boot(p3, ds)} | {boot(p4, ds)} | {boot(p2, ds)} |')
    # ---------------- C and D
    out.append('\n## C. The last five minutes: ATM straddle quoted at 15:55 vs realized |S(16:00) − K|  ($ per straddle)\n')
    out.append('| ticker | period | days | mean mid $ | mean ask-sum $ | mean realized $ | mid − realized | ask − realized |')
    out.append('|---|---|---|---|---|---|---|---|')
    drows = []; crows = []
    for tk in ('SPY', 'QQQ', 'IWM'):
        for per in ('TRAIN', 'TEST'):
            fp = os.path.join(C.WORK, f'trades_{tk}_{per}.parquet')
            if not os.path.exists(fp): continue
            T = pl.read_parquet(fp).filter((pl.col('entry') == '14:05') & (pl.col('sk') == 'S0') & (pl.col('tp') == 0) & (pl.col('st') == 0))
            e1 = {r['date']: r for r in T.filter(pl.col('ex') == 'E1').iter_rows(named=True)}
            e2 = {r['date']: r['pnl'] for r in T.filter(pl.col('ex') == 'E2').iter_rows(named=True)}
            days = pl.read_parquet(os.path.join(C.WORK, f'days_{tk}_{per}.parquet')).filter(pl.col('status') == 'ok')['date'].to_list()
            for d in days:
                Aa = C.day_arrays(tk, d)
                if Aa is None: continue
                t = C.CLOSE_M - C.M0; ks = Aa['strikes']
                S55 = C.last_close_before(Aa['close'], t); Sset = C.last_close_before(Aa['close'], C.SETTLE_BAR - C.M0 + 1)
                okk = np.where(Aa['ok'][0, :, t] & Aa['ok'][1, :, t])[0]
                if len(okk) and ks.min() <= S55 <= ks.max():
                    i = int(okk[np.argmin(np.abs(ks[okk] - S55))]); K = ks[i]
                    mid = (Aa['bid'][0, i, t] + Aa['ask'][0, i, t] + Aa['bid'][1, i, t] + Aa['ask'][1, i, t]) / 2
                    ask = Aa['ask'][0, i, t] + Aa['ask'][1, i, t]
                    ah = eod.get(d, (None, None))[1] if tk == 'SPY' else None
                    crows.append(dict(ticker=tk, period=per, date=d, mid=100 * mid, ask=100 * ask, realized=100 * abs(Sset - K),
                                      realized_ah=(100 * abs(ah - K) if ah is not None and ah == ah else None)))
                if d in e1 and d in e2:
                    r = e1[d]; K = r['k_sc']
                    sp = hs = ext = mv = 0.0; nfee = 0
                    for ri, rt in ((0, 'C'), (1, 'P')):
                        i = int(np.where(np.isclose(ks, K))[0][0])
                        a = Aa['aff'][ri, i, t]; b = Aa['bff'][ri, i, t]
                        if a <= 0.05: continue          # E1 left this leg to expire: identical under E2
                        m = (a + b) / 2; v55 = intr(rt, K, S55); v60 = intr(rt, K, Sset)
                        hs += a - m; ext += m - v55; mv += v55 - v60; nfee += 1
                    drows.append(dict(ticker=tk, period=per, date=d, e2_minus_e1=e2[d] - r['pnl'], half_spread=100 * hs, extrinsic_1555=100 * ext,
                                      move_1555_1600=100 * mv, fees=C.FEE * nfee))
    Cc = pl.DataFrame(crows); Cc.write_csv(os.path.join(C.OUT, 'diag_last5min_straddle.csv'))
    for (tk, per), g in sorted(Cc.group_by(['ticker', 'period']), key=lambda x: (['SPY', 'QQQ', 'IWM'].index(x[0][0]), x[0][1] != 'TRAIN')):
        ds = g['date'].to_list()
        out.append(f"| {tk} | {per} | {g.height} | {g['mid'].mean():.2f} | {g['ask'].mean():.2f} | {g['realized'].mean():.2f} | "
                   f"{boot(g['mid'] - g['realized'], ds)} | {boot(g['ask'] - g['realized'], ds)} |")
        if tk == 'SPY':
            h = g.filter(pl.col('realized_ah').is_not_null())
            out.append(f"| SPY, realized at the 17:15 after-hours mid | {per} | {h.height} | {h['mid'].mean():.2f} | {h['ask'].mean():.2f} | {h['realized_ah'].mean():.2f} | "
                       f"{boot(h['mid'] - h['realized_ah'], h['date'].to_list())} | {boot(h['ask'] - h['realized_ah'], h['date'].to_list())} |")
    Dd = pl.DataFrame(drows); Dd.write_csv(os.path.join(C.OUT, 'diag_e2_minus_e1.csv'))
    out.append('\n## D. Why E2 beats E1: straddle entered at 14:05, no TP, no stop, no filter ($ per straddle, mean [95 % CI])\n')
    out.append('E2 − E1 = Σ over legs E1 bought back at 15:55 of (ask − mid) + (mid − intrinsic at the 15:54-bar close) + (intrinsic at 15:55 − intrinsic at 16:00) + fee.\n')
    out.append('| ticker | period | n | E2 − E1 | half-spread | extrinsic at 15:55 | 15:55→16:00 intrinsic change | fees |')
    out.append('|---|---|---|---|---|---|---|---|')
    for (tk, per), g in sorted(Dd.group_by(['ticker', 'period']), key=lambda x: (['SPY', 'QQQ', 'IWM'].index(x[0][0]), x[0][1] != 'TRAIN')):
        ds = g['date'].to_list()
        out.append(f"| {tk} | {per} | {g.height} | {boot(g['e2_minus_e1'], ds)} | {boot(g['half_spread'], ds)} | {boot(g['extrinsic_1555'], ds)} | "
                   f"{boot(g['move_1555_1600'], ds)} | {g['fees'].mean():.2f} |")
    open(os.path.join(C.OUT, 'diagnostics.md'), 'w').write('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
