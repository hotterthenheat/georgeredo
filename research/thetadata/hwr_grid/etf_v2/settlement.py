"""Settlement realism of hold-to-expiry (E2) on the complete data (etf_v2; repeats the original POST-HOC diagnostic B of
../etf/diagnostics.py, not pre-registered).  SPY, QQQ and IWM options are American and physically settled, trade until 16:15 ET and
can be exercised on after-hours moves; the pre-registered valuation (intrinsic against the 16:00 close = close of the 15:59 bar) is
kept for every reported grid number and is OPTIMISTIC for E2.  Only SPY can be re-valued: the inputs are the per-date SPY EOD close and
17:15 quote mid stored in ../etf/results/diag_settlement_spy.csv (eod_close, ah_mid), read here unchanged.
Re-valuations of legs that expired (reason EXPIRE): (1) as run; (2) at the EOD close; (3) auto-exercise only (legs ITM at the EOD close
are exercised and the shares closed at the 17:15 mid); (4) rational after-hours exercise (each leg worth its intrinsic value at the
17:15 mid); (5) pessimistic (short legs owe max(intrinsic at the close, intrinsic at the 17:15 mid), long legs at the close).
Configurations: every TRAIN-selected configuration with an E2 exit in results/selected_test.csv (SPY trades of the SPY and SPY+QQQ
scopes), plus the five configurations of the original diagnostic.  Writes results/settlement_spy.csv."""
import os, sys
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import analyze as A


def intr(right, K, S): return max(S - K, 0.0) if right == 'C' else max(K - S, 0.0)


def main():
    E = pl.read_csv(os.path.join(C.ORIG, 'results', 'diag_settlement_spy.csv'))
    eod = {r['date']: (r['eod_close'], r['ah_mid']) for r in E.iter_rows(named=True)}
    S = pl.read_csv(os.path.join(C.OUT, 'selected_test.csv'))
    cfgs = {}
    for r in S.filter(pl.col('scope').is_in(['SPY', 'SPY+QQQ'])).iter_rows(named=True):
        if '|E2|' in r['cfg']: cfgs.setdefault(r['cfg'], []).append(f"{r['scope']} {r['selection']}")
    for c in ['S0|14:05|tp0|st1|E2|F3', 'S0.5|14:05|tp0|st2|E2|F3', 'S0|14:05|tp0|st2|E2|F3', 'S0|14:05|tp0|st0|E2|F0', 'S1|14:05|tp0|st0|E2|F0']:
        cfgs.setdefault(c, []).append('original diagnostic set')
    rows = []
    for per in ('TRAIN', 'TEST'):
        T = pl.read_parquet(os.path.join(C.WORK, f'trades_SPY_{per}.parquet')).select(
            A.KEEP + ['k_sc', 'k_sp', 'k_lc', 'k_lp', 'settle'])
        fixed = T.filter(pl.col('entry').is_in(list(C.ENTRIES)) & (pl.col('ex') == 'E2'))
        Lf = A.apply_filters(fixed)
        for cfg, used in cfgs.items():
            q = Lf.filter(pl.col('cfg') == cfg).sort('date')
            n_all = q.height
            q = q.filter(pl.col('date').is_in([d for d, v in eod.items() if v[1] is not None and v[1] == v[1] and v[0] is not None]))
            p = {i: [] for i in range(5)}; ds = []
            for r in q.iter_rows(named=True):
                ds.append(r['date']); base = r['pnl']; p[0].append(base)
                if r['reason'] != 'EXPIRE':
                    for i in range(1, 5): p[i].append(base)
                    continue
                Sc, Sah = eod[r['date']]; S0 = r['settle']
                legs = [('C', r['k_sc'], -1), ('P', r['k_sp'], -1)]
                if r['k_lc'] is not None and r['k_lc'] == r['k_lc']: legs += [('C', r['k_lc'], +1), ('P', r['k_lp'], +1)]
                d1 = d2 = d3 = d4 = 0.0
                for rt, K, sg in legs:
                    v0 = intr(rt, K, S0); v1 = intr(rt, K, Sc)
                    itm = (Sc > K) if rt == 'C' else (Sc < K)
                    v3 = ((Sah - K) if rt == 'C' else (K - Sah)) if itm else 0.0
                    v4 = intr(rt, K, Sah)
                    v2 = max(v1, v4) if sg < 0 else v1
                    d1 += sg * (v1 - v0); d2 += sg * (v2 - v0); d3 += sg * (v3 - v0); d4 += sg * (v4 - v0)
                p[1].append(base + 100 * d1); p[2].append(base + 100 * d3); p[3].append(base + 100 * d4); p[4].append(base + 100 * d2)
            rec = dict(cfg=cfg, used_by='; '.join(used), period=per, n_trades=n_all, n_with_ah=len(ds))
            for i, lab in enumerate(['as_run_1600', 'eod_close', 'auto_exercise_ah', 'rational_ah', 'pessimistic_ah']):
                v = np.array(p[i]); lo, hi = C.boot_ci(v, ds)
                rec[f'{lab}_mean'] = round(float(v.mean()), 2); rec[f'{lab}_lo'] = round(lo, 2); rec[f'{lab}_hi'] = round(hi, 2)
            rows.append(rec)
            print(rec, flush=True)
    pl.DataFrame(rows).write_csv(os.path.join(C.OUT, 'settlement_spy.csv'))


if __name__ == '__main__':
    main()
