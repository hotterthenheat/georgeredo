"""Hypothesis C, step 2: the debit verticals replayed under the audit's exits, paired against the naked contract.

Mark = the spread's bid-side value at minute m: long bid(m) - short ask(m) (what closing at market returns); NaN when
either leg has no quote that minute. Every exit is judged on the mark at each minute m > e and fills at that minute's
mark (a target fills at its price exactly, a resting limit - the audit's rule). Hard flat at 15:58 (m = 388) at the last
mark quoted at or before it. A sale whose mark is <= 0 is not made: the structure is held to settlement (closing a
spread for nothing or less is pointless; the audit held a 0-bid contract to settlement the same way). Fees: $0.65 a leg
each way, none on a leg at settlement. The naked contract is the audit's stored path replayed by THE SAME CODE (mark =
its bid, one leg), and checked against the audit's engine.simulate for the four rules it has.
Exits: hold (settlement); flat (15:58 only); trail50 (step 4's 50% trailing stop on the mark's running peak, from the
first minute after entry, + flat); t1_bs (+25% target on the debit, -32% backstop, + flat); t1_bs_lock0 (t1_bs + the
breakeven lock at +0%: once the mark has been at or above the debit, sell at the first later mark at or below it);
struct0 / struct2 (universe A only: the underlying trades back through the swept level + 0 / 2 bps on a bar's high/low,
sold at the next minute's mark, + flat).
  PERIOD=fit  prints the fit tables only (the pre-registration pass);  PERIOD=all prints fit and OOS.
Writes out/spreads_summary.csv, out/spreads_paired.csv, out/spreads_trades.parquet (every trade's result per cell x exit).
"""
import os, sys, json, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
sys.path.insert(0, AUDIT_EXITS)
import engine as audit_engine            # read-only use of the audit's loader and simulate (for the naked check)

PERIOD = os.environ.get('PERIOD', 'fit')
EXITS = ['hold', 'flat', 'trail50', 't1_bs', 't1_bs_lock0', 'struct0', 'struct2']
CELLS = ['d60_40', 'd70_30', 'd55_45', 'atm_otm1']

def first_true(mask):
    any_ = mask.any(axis=1); idx = mask.argmax(axis=1); idx[~any_] = -1; return idx

def ffill_rows(X):
    idx = np.where(~np.isnan(X), np.arange(X.shape[1])[None, :], 0); idx = np.maximum.accumulate(idx, axis=1)
    return X[np.arange(X.shape[0])[:, None], idx]

def simulate(mark, debit, settle, e, close_m, nlegs, rule, put=None, level=None, BH=None, BL=None):
    n, _ = mark.shape; M = np.arange(NMIN)[None, :]
    after = (M > e[:, None]) & (M <= close_m[:, None])
    Mw = np.where(after, mark, np.nan)
    peak = np.fmax.accumulate(np.where(np.isnan(Mw), -np.inf, Mw), axis=1); peak[~np.isfinite(peak)] = np.nan
    hf = np.where(close_m == 390, 388, 208)
    d = debit[:, None]
    cand = []
    if rule in ('flat', 'trail50', 't1_bs', 't1_bs_lock0', 'struct0', 'struct2'):
        cand.append((hf.copy(), 'flat'))
    if rule == 'trail50':
        cand.append((first_true((peak > 0) & (Mw <= 0.5 * peak + 1e-9)), 'trail'))
    if rule in ('t1_bs', 't1_bs_lock0'):
        cand.append((first_true(Mw <= 0.68 * d + 1e-9), 'stop'))
    if rule == 't1_bs_lock0':
        lock_m = first_true(peak >= d - 1e-9)
        cand.append((first_true((Mw <= d + 1e-9) & (M > lock_m[:, None]) & (lock_m >= 0)[:, None]), 'lock'))
    if rule in ('struct0', 'struct2'):
        buf = 0.0 if rule == 'struct0' else 2.0
        up = level * (1 + buf / 1e4); dn = level * (1 - buf / 1e4)
        bar_ok = (M >= e[:, None]) & (M + 1 <= close_m[:, None])
        hit = np.where(put[:, None], BH >= up[:, None], BL <= dn[:, None]) & bar_ok & ~np.isnan(level)[:, None]
        i = first_true(hit); cand.append((np.where(i >= 0, i + 1, -1), 'struct'))
    common_m = np.full(n, NMIN + 5); common_r = np.full(n, 'settle', dtype=object)
    for i, r in cand:
        better = (i >= 0) & (i < common_m); common_m[better] = i[better]; common_r[better] = r
    m = common_m.copy(); r = common_r.copy()
    if rule in ('t1_bs', 't1_bs_lock0'):
        ti = first_true(Mw >= 1.25 * d - 1e-9); hit = (ti >= 0) & (ti <= common_m)
        m = np.where(hit, ti, common_m); r = np.where(hit, 'target', common_r)
    sold = m < NMIN
    Mf = ffill_rows(Mw)
    px = np.where(sold, Mf[np.arange(n), np.minimum(m, NMIN - 1)], np.nan)
    px = np.where(r == 'target', 1.25 * debit, px)
    px = np.where(np.isnan(px), 0.0, px)
    sold = sold & (px > 0)
    exit_px = np.where(sold, px, settle); r = np.where(sold, r, 'settle'); m = np.where(sold, m, close_m)
    pnl = (exit_px - debit) * 100 - nlegs * FEE - np.where(sold, nlegs * FEE, 0.0)
    return dict(pnl=pnl, pct=pnl / (debit * 100), exit_m=m, reason=r, exit_px=exit_px)

def load_product(root):
    S = pl.read_parquet(os.path.join(OUT, f'spreads_{root}.parquet')).filter(pl.col('ok'))
    L = pl.read_parquet(os.path.join(OUT, f'legs_{root}.parquet'))
    P = audit_engine.load(products=[root])
    key = {(s, u, int(e), sd): i for i, (s, u, e, sd) in enumerate(zip(P.session, P.uni, P.e, P.df['side'].to_numpy()))}
    lkey = {(s, sd, float(k)): i for i, (s, sd, k) in enumerate(zip(L['session'], L['side'], L['strike']))}
    LB = np.round(np.array(L['bid'].to_list(), dtype=np.float64), 4); LA = np.round(np.array(L['ask'].to_list(), dtype=np.float64), 4)
    return S, P, key, lkey, LB, LA

def run_product(root):
    S, P, key, lkey, LB, LA = load_product(root)
    trades = []; summaries = []; paired = []
    # the naked contract under this code, and the audit engine's own figures for the rules it has
    nk_mark = P.B; nk_debit = P.ask0; nk_settle = P.settle; nk_e = P.e; nk_close = P.close_m
    half = nk_close == 210
    naked = {}
    for rule in EXITS:
        naked[rule] = simulate(nk_mark, nk_debit, nk_settle, nk_e, nk_close, 1, rule, P.put, P.level, P.BH, P.BL)
    checks = {}
    for rule, kw in (('hold', dict(prem_stop=None, hard_flat=False)), ('flat', dict(prem_stop=None, hard_flat=True)),
                     ('t1_bs', dict(prem_stop=0.68, targets=((1, 1.25),), hard_flat=True)), ('t1_bs_lock0', dict(prem_stop=0.68, targets=((1, 1.25),), be_lock=0.0, hard_flat=True)),
                     ('struct0', dict(prem_stop=None, struct_buffer=0.0, hard_flat=True)), ('struct2', dict(prem_stop=None, struct_buffer=2.0, hard_flat=True))):
        ref = audit_engine.simulate(P, **kw)
        checks[rule] = int(np.sum(np.abs(ref['pnl'] - naked[rule]['pnl']) > 1e-6))
    print(root, 'naked vs audit engine, trades differing by > 1e-6 $:', checks, 'of', P.n, flush=True)
    for cell in CELLS:
        C = S.filter(pl.col('cell') == cell)
        if C.height == 0: continue
        idx = np.array([key.get((s, u, int(e), sd), -1) for s, u, e, sd in zip(C['session'], C['universe'], C['entry_m'], C['side'])])
        keep = idx >= 0
        C = C.filter(pl.Series(keep)); idx = idx[keep]
        if C.height == 0: continue
        iL = np.array([lkey[(s, sd, float(k))] for s, sd, k in zip(C['session'], C['side'], C['k_long'])])
        iS = np.array([lkey[(s, sd, float(k))] for s, sd, k in zip(C['session'], C['side'], C['k_short'])])
        mark = LB[iL] - LA[iS]
        debit = C['debit'].to_numpy(); settle = C['settle'].to_numpy(); e = C['entry_m'].to_numpy().astype(int); close_m = C['close_m'].to_numpy().astype(int)
        uni = C['universe'].to_numpy(); sess = C['session'].to_numpy(); per = np.where(sess < SPLIT, 'fit', 'oos')
        for rule in EXITS:
            res = simulate(mark, debit, settle, e, close_m, 2, rule, P.put[idx], P.level[idx], P.BH[idx], P.BL[idx])
            nk = naked[rule]
            for i in range(C.height):
                trades.append(dict(product=root, session=sess[i], universe=uni[i], side=C['side'][i], entry_m=int(e[i]), cell=cell, exit=rule, period=per[i],
                                   debit=float(debit[i]), width=float(C['width'][i]), pnl=float(res['pnl'][i]), pct=float(res['pct'][i]), exit_m=int(res['exit_m'][i]), reason=str(res['reason'][i]),
                                   naked_ask=float(nk_debit[idx[i]]), naked_pnl=float(nk['pnl'][idx[i]]), naked_pct=float(nk['pct'][idx[i]]), naked_reason=str(nk['reason'][idx[i]])))
    T = pl.DataFrame(trades, infer_schema_length=None)
    return T

def summarize(T):
    rows = []; prow = []
    periods = ['fit'] if PERIOD == 'fit' else ['fit', 'oos']
    for uni in ['A', 'B']:
        for prod in PRODUCTS + ['ALL']:
            for cell in CELLS:
                for rule in EXITS:
                    if uni == 'B' and rule.startswith('struct'): continue
                    for per in periods:
                        d = T.filter((pl.col('universe') == uni) & (pl.col('cell') == cell) & (pl.col('exit') == rule) & (pl.col('period') == per))
                        if prod != 'ALL': d = d.filter(pl.col('product') == prod)
                        if d.height == 0: continue
                        s = cell_stats(d['pnl'].to_numpy(), d['pct'].to_numpy(), d['session'].to_numpy(), order=(d['session'] + d['entry_m'].cast(pl.Utf8).str.zfill(3)).to_numpy())
                        s.update(universe=uni, product=prod, cell=cell, exit=rule, period=per, mean_debit=float(d['debit'].mean()), mean_width=float(d['width'].mean()),
                                 share_settle=float((d['reason'] == 'settle').mean()), share_target=float((d['reason'] == 'target').mean()), share_stop=float((d['reason'] == 'stop').mean()))
                        rows.append(s)
                        # paired against the naked contract on the same entries
                        du = d['pnl'].to_numpy() - d['naked_pnl'].to_numpy(); dp = d['pct'].to_numpy() - d['naked_pct'].to_numpy()
                        lo, hi = boot_ci(du, d['session'].to_numpy()); plo, phi = boot_ci(dp, d['session'].to_numpy())
                        nk = cell_stats(d['naked_pnl'].to_numpy(), d['naked_pct'].to_numpy(), d['session'].to_numpy())
                        prow.append(dict(universe=uni, product=prod, cell=cell, exit=rule, period=per, n=d.height, spread_usd=float(d['pnl'].mean()), naked_usd=float(d['naked_pnl'].mean()),
                                         diff_usd=float(du.mean()), diff_usd_lo=lo, diff_usd_hi=hi, spread_pct=float(d['pct'].mean()), naked_pct=float(d['naked_pct'].mean()),
                                         diff_pct=float(dp.mean()), diff_pct_lo=plo, diff_pct_hi=phi, share_spread_better=float((du > 0).mean()),
                                         naked_win=nk['win_rate'], naked_ci_lo_pct=nk['ci_lo_pct'], naked_ci_hi_pct=nk['ci_hi_pct'], naked_wo5_pct=nk['wo_best5_pct'], naked_by_year=nk['by_year']))
    return pl.DataFrame(rows, infer_schema_length=None), pl.DataFrame(prow, infer_schema_length=None)

if __name__ == '__main__':
    T = pl.concat([run_product(p) for p in PRODUCTS], how='vertical_relaxed')
    T.write_parquet(os.path.join(OUT, 'spreads_trades.parquet'))
    summ, pair = summarize(T)
    tag = '' if PERIOD == 'fit' else '_all'
    summ.write_csv(os.path.join(OUT, f'spreads_summary{tag}.csv')); pair.write_csv(os.path.join(OUT, f'spreads_paired{tag}.csv'))
    for r in summ.iter_rows(named=True):
        print(f"{r['universe']} {r['product']:4} {r['cell']:8} {r['exit']:11} {r['period']:3} debit={r['mean_debit']:.2f} w={r['mean_width']:.2f} settle={r['share_settle']:.2f} | {fmt(r)}")
    print('---- paired, spread minus naked, same entries ----')
    for r in pair.iter_rows(named=True):
        print(f"{r['universe']} {r['product']:4} {r['cell']:8} {r['exit']:11} {r['period']:3} n={r['n']:5d} spread=${r['spread_usd']:+7.2f} ({r['spread_pct']*100:+6.2f}%) naked=${r['naked_usd']:+7.2f} ({r['naked_pct']*100:+6.2f}%) "
              f"diff=${r['diff_usd']:+6.2f} [{r['diff_usd_lo']:+6.2f},{r['diff_usd_hi']:+6.2f}] diff%={r['diff_pct']*100:+6.2f} [{r['diff_pct_lo']*100:+6.2f},{r['diff_pct_hi']*100:+6.2f}] spreadBetter={r['share_spread_better']:.2f}")
