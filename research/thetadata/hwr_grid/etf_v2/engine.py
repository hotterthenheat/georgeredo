"""Per-trade simulation of the pre-registered grid (PREREGISTRATION_original.md §3-§5) for one ticker and one period, etf_v2.
Copied from ../etf/engine.py; the trade logic is unchanged (amendment A1's spot-outside-the-stored-range rule is still in the code; on
full chains it should never fire, and integrity_*.parquet counts it).  Added: integrity_{TICKER}_{PERIOD}.parquet, one row per
session x minute 10:00..14:30 (every pre-registered entry and every random-baseline minute) with the entry-time skip status of each
structure-k under the same rules as the trade loop (data-integrity check), the listed strike range and its reach in EM units.
Usage: python3 engine.py TICKER PERIOD        (PERIOD = TRAIN | TEST)
Writes $HWR_WORK/trades_{TICKER}_{PERIOD}.parquet (one row per trade x TP x stop x exit; fixed entries 10:00/11:00/13:00/14:05 and
random-baseline entries r11..r15) and skips_{TICKER}_{PERIOD}.parquet (one row per skipped entry x structure-k with the reason).
Filters (F0-F3) are applied later, in analyze.py, from the fixed-entry rows."""
import os, sys, time, math
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

SQ = math.sqrt(math.pi / 2)


def Phi(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def legs_for(strikes, S, em, s, k, i0):
    """[(right, strike_index, sign)] with sign -1 short / +1 long, or (None, reason)."""
    nK = len(strikes)
    if k == 0:
        sc = sp = i0
    else:
        sc = int(np.searchsorted(strikes, S + k * em - 1e-9, 'left'))
        sp = int(np.searchsorted(strikes, S - k * em + 1e-9, 'right')) - 1
        if sc >= nK or sp < 0: return None, 'out_of_band'
    legs = [(0, sc, -1), (1, sp, -1)]
    if s == 'I':
        lc = int(np.searchsorted(strikes, S + (k + 1) * em - 1e-9, 'left'))
        lp = int(np.searchsorted(strikes, S - (k + 1) * em + 1e-9, 'right')) - 1
        if lc <= sc: lc = sc + 1
        if lp >= sp: lp = sp - 1
        if lc >= nK or lp < 0: return None, 'out_of_band'
        legs += [(0, lc, +1), (1, lp, +1)]
    return legs, None


def settle_value(strikes, legs, Sset):
    out = []
    for r, i, sg in legs:
        K = strikes[i]
        out.append(max(Sset - K, 0.0) if r == 0 else max(K - Sset, 0.0))
    return out


def close_out(A, legs, e, mode, intr):
    """Exit at row e.  mode: 'ALL' (TP/stop: close every leg; long with bid 0 expires), 'E1' (leave legs with ask <= 0.05 and
    zero-bid longs), 'E0' (close every short; long with bid 0 expires), 'E2' (everything expires).
    Returns (cash_per_share, n_closed, half_spread_sum, n_exp, itm_short_exp, ff_flag)."""
    cash = 0.0; ncl = 0; hs = 0.0; nexp = 0; itm = 0; ff = 0
    for (r, i, sg), iv in zip(legs, intr):
        if mode == 'E2':
            expire = True
        else:
            a = A['aff'][r, i, e]; b = A['bff'][r, i, e]
            if mode == 'E1': expire = (a <= 0.05) or (sg > 0 and b <= 0)
            else: expire = (sg > 0 and b <= 0)
        if expire:
            cash += -iv if sg < 0 else iv; nexp += 1
            if sg < 0 and iv > 0: itm += 1
        else:
            cash += -a if sg < 0 else b; ncl += 1; hs += (a - b) / 2
            if not A['ok'][r, i, e]: ff = 1
    return cash, ncl, hs, nexp, itm, ff


def entry_status(A, t):
    """Skip status of every structure-k at minute index t, by exactly the rules of run_day (no P&L).  Returns (S, em, i0, {sk: code})."""
    strikes = A['strikes']
    S = C.last_close_before(A['close'], t)
    if not np.isfinite(S): return S, np.nan, -1, {C.sk_name(s, k): 'no_spot' for s, k in C.SK}
    if not (strikes.min() <= S <= strikes.max()): return S, np.nan, -1, {C.sk_name(s, k): 'out_of_band_spot' for s, k in C.SK}
    ok_t = A['ok'][0, :, t] & A['ok'][1, :, t]
    cand = np.where(ok_t)[0]
    if len(cand) == 0: return S, np.nan, -1, {C.sk_name(s, k): 'no_quote' for s, k in C.SK}
    i0 = int(cand[np.argmin(np.abs(strikes[cand] - S))])
    em = float((A['bid'][0, i0, t] + A['ask'][0, i0, t]) / 2 + (A['bid'][1, i0, t] + A['ask'][1, i0, t]) / 2)
    if not (em > 0): return S, em, i0, {C.sk_name(s, k): 'no_em' for s, k in C.SK}
    out = {}
    for s, k in C.SK:
        legs, why = legs_for(strikes, S, em, s, k, i0)
        if legs is None: out[C.sk_name(s, k)] = why
        elif not all(A['ok'][r, i, t] for r, i, _ in legs): out[C.sk_name(s, k)] = 'no_quote'
        elif any(A['bid'][r, i, t] <= 0 for r, i, _ in legs): out[C.sk_name(s, k)] = 'zero_bid'
        elif sum(A['bid'][r, i, t] if sg < 0 else -A['ask'][r, i, t] for r, i, sg in legs) <= 1e-9: out[C.sk_name(s, k)] = 'no_credit'
        else: out[C.sk_name(s, k)] = 'ok'
    return S, em, i0, out


def integrity_day(d, A, out):
    strikes = A['strikes']; kmin, kmax = float(strikes.min()), float(strikes.max())
    for minute in range(C.RAND_LO, C.RAND_HI + 1):
        t = minute - C.M0
        S, em, i0, st = entry_status(A, t)
        rec = dict(date=d, T=C.mstr(minute), spot=S, em=em, n_strikes=len(strikes), kmin=kmin, kmax=kmax,
                   reach_up=(kmax - S) / em if em == em and em > 0 else np.nan, reach_dn=(S - kmin) / em if em == em and em > 0 else np.nan)
        rec.update({f'st_{k}': v for k, v in st.items()})
        out.append(rec)


def run_day(tk, d, A, entries, early, rows, skips):
    strikes = A['strikes']; t_mon = C.MON_LAST - C.M0; t_cls = C.CLOSE_M - C.M0
    Sset = C.last_close_before(A['close'], C.SETTLE_BAR - C.M0 + 1)
    for lab, minute, fixed in entries:
        t = minute - C.M0
        S = C.last_close_before(A['close'], t)
        ok_t = A['ok'][0, :, t] & A['ok'][1, :, t]
        def skip_all(reason):
            for s, k in C.SK: skips.append((d, lab, C.sk_name(s, k), reason))
        if not np.isfinite(S): skip_all('no_spot'); continue
        if not (strikes.min() <= S <= strikes.max()): skip_all('out_of_band_spot'); continue
        cand = np.where(ok_t)[0]
        if len(cand) == 0: skip_all('no_quote'); continue
        i0 = int(cand[np.argmin(np.abs(strikes[cand] - S))])
        em = float((A['bid'][0, i0, t] + A['ask'][0, i0, t]) / 2 + (A['bid'][1, i0, t] + A['ask'][1, i0, t]) / 2)
        if not (em > 0): skip_all('no_em'); continue
        sig = em * SQ
        for s, k in C.SK:
            name = C.sk_name(s, k)
            legs, why = legs_for(strikes, S, em, s, k, i0)
            if legs is None: skips.append((d, lab, name, why)); continue
            if not all(A['ok'][r, i, t] for r, i, _ in legs): skips.append((d, lab, name, 'no_quote')); continue
            if any(A['bid'][r, i, t] <= 0 for r, i, _ in legs): skips.append((d, lab, name, 'zero_bid')); continue
            Cr = sum(A['bid'][r, i, t] if sg < 0 else -A['ask'][r, i, t] for r, i, sg in legs)
            if Cr <= 1e-9: skips.append((d, lab, name, 'no_credit')); continue
            hs_e = sum((A['ask'][r, i, t] - A['bid'][r, i, t]) / 2 for r, i, _ in legs)
            dprox = float(np.mean([Phi(-abs(strikes[i] - S) / sig) for r, i, sg in legs if sg < 0]))
            intr = settle_value(strikes, legs, Sset)
            # cost-to-close path on rows t+1 .. 15:54
            X = np.zeros(t_mon - t)
            for r, i, sg in legs:
                X += (A['aff'][r, i, t + 1:t_mon + 1] if sg < 0 else -A['bff'][r, i, t + 1:t_mon + 1])
            def first(mask):
                w = np.flatnonzero(mask)
                return int(w[0]) + t + 1 if len(w) else None
            tp_m = {0: None}; st_m = {0: None}
            for p in (25, 50): tp_m[p] = first(X <= (1 - p / 100) * Cr + 1e-9)
            for m in (1, 2): st_m[m] = first(X >= (1 + m) * Cr - 1e-9)
            nlegs = len(legs)
            base = dict(entry=lab, T=C.mstr(minute), sk=name, credit=round(Cr * 100, 2), em=round(em, 4), spot=round(S, 4),
                        k_sc=strikes[legs[0][1]], k_sp=strikes[legs[1][1]],
                        k_lc=strikes[legs[2][1]] if nlegs == 4 else np.nan, k_lp=strikes[legs[3][1]] if nlegs == 4 else np.nan,
                        dprox=round(dprox, 4), settle=round(Sset, 4))
            term_cache = {}
            exits = ('E1', 'E2', 'E0') if fixed else ('E1', 'E2')
            for tp in C.TPS:
                for st in C.STOPS:
                    a, b = tp_m[tp], st_m[st]
                    trig = None
                    if a is not None and (b is None or a < b): trig = ('TP', a)
                    elif b is not None: trig = ('STOP', b + 1)
                    for ex in exits:
                        if trig is not None:
                            key = trig
                            if key not in term_cache: term_cache[key] = close_out(A, legs, trig[1], 'ALL', intr)
                            res = term_cache[key]; reason, em_ = trig[0], trig[1]
                        else:
                            key = ex
                            if key not in term_cache:
                                term_cache[key] = close_out(A, legs, t_cls, ex, intr)
                            res = term_cache[key]; reason = {'E1': 'CLOSE1555', 'E0': 'CLOSEALL1555', 'E2': 'EXPIRE'}[ex]
                            em_ = t_cls if ex != 'E2' else C.NM - 1
                        cash, ncl, hs_x, nexp, itm, ff = res
                        fees = C.FEE * (nlegs + ncl)
                        pnl = (Cr + cash) * 100 - fees
                        cost = (hs_e + hs_x) * 100 + fees
                        rows.append(dict(base, tp=tp, st=st, ex=ex, pnl=round(pnl, 2), cost=round(cost, 2), reason=reason,
                                         exit_t=C.mstr(em_ + C.M0), n_exp=nexp, itm_exp=itm, ff_exit=ff))


def main():
    tk, period = sys.argv[1], sys.argv[2]
    lo, hi = C.TRAIN if period == 'TRAIN' else C.TEST
    lo = max(lo, C.FIRST[tk])
    os.makedirs(C.WORK, exist_ok=True)
    early = C.early_closes(); rnd = C.random_minutes()
    cal = [d for d in C.L.trading_sessions(lo, hi)]
    have = set(C.L.sessions('chains', tk))
    rows = []; skips = []; t0 = time.time(); daylog = []; integ = []
    for j, d in enumerate(cal):
        if d in early: daylog.append((d, 'early_close')); continue
        if d not in have: daylog.append((d, 'no_chain_file')); continue
        A = C.day_arrays(tk, d)
        if A is None: daylog.append((d, 'no_underlying_file')); continue
        entries = [(lab, m, True) for lab, m in C.ENTRIES.items()] + [(f'r{s}', rnd[(s, tk, d)], False) for s in C.RAND_SEEDS]
        n0 = len(rows)
        run_day(tk, d, A, entries, early, rows, skips)
        integrity_day(d, A, integ)
        for r in rows[n0:]: r['date'] = d
        daylog.append((d, 'ok', len(A['strikes']), float(A['strikes'].min()), float(A['strikes'].max())))
        if j % 50 == 0: print(f'{tk} {period} {d} rows={len(rows)} {time.time() - t0:.0f}s', flush=True)
    df = pl.DataFrame(rows)
    df = df.with_columns(pl.lit(tk).alias('tk')).select(['tk', 'date'] + [c for c in df.columns if c not in ('tk', 'date')])
    df.write_parquet(os.path.join(C.WORK, f'trades_{tk}_{period}.parquet'))
    pl.DataFrame(skips, schema=['date', 'entry', 'sk', 'reason'], orient='row').with_columns(pl.lit(tk).alias('tk')).write_parquet(
        os.path.join(C.WORK, f'skips_{tk}_{period}.parquet'))
    daylog = [x if len(x) == 5 else (x[0], x[1], None, None, None) for x in daylog]
    pl.DataFrame(daylog, schema=['date', 'status', 'n_strikes', 'kmin', 'kmax'], orient='row').with_columns(pl.lit(tk).alias('tk')).write_parquet(
        os.path.join(C.WORK, f'days_{tk}_{period}.parquet'))
    pl.DataFrame(integ, infer_schema_length=None).with_columns(pl.lit(tk).alias('tk')).write_parquet(os.path.join(C.WORK, f'integrity_{tk}_{period}.parquet'))
    print(f'done {tk} {period}: {df.height} rows, {len(skips)} skips, {time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    main()
