"""targets.py — the "nearest EMA" take-profit rule (RULE_EMA_TARGETS.md), on the committed ema_lib (charts, EMA, ATM strike,
R/R pick, fills, fees). PREVIEW — one month each, no verdict. Reads files only; ema_lib's guard refuses a held-out month.

python targets.py  -> out/targets_<month>.json for 2025-02 and 2025-03, both versions
"""
import json
import sys
from pathlib import Path

import numpy as np
import ema_lib as E

HERE = Path(__file__).resolve().parent
S = E.S
N = 9
HTF = (5, 15, 30)


def ema_values(cm, n, tf):
    """V[m, k, r] = the tf-candle EMA(n) after the last completed candle with completion <= m (NaN before the first)"""
    a = 2.0 / (n + 1)
    nK = cm.shape[1]
    V = np.full((391, nK, 2), np.nan)
    ema = np.full((nK, 2), np.nan)
    comps = set(range(tf, E.NC, tf))
    for m in range(391):
        if m in comps:
            c = cm[m]
            fin = np.isfinite(c)
            seed = fin & ~np.isfinite(ema)
            ema = np.where(seed, c, np.where(fin, a * c + (1 - a) * ema, ema))
        V[m] = ema
    return V


def run_day(name, d, ver):
    """ver 'E1' (ATM, spread veto 3%) or 'E2' (best R/R, cap 3%); returns trades, skip counts, breaks with no EMA above"""
    dd = E.day_data(name, d)
    if dd is None:
        return [], {}, 0
    K, bid, ask, mid, cm, Sx, st = dd
    A1, B1, BL1 = st[N][1]
    HV = {tf: ema_values(cm, N, tf) for tf in HTF}
    trades, nt, noabove = [], {}, 0

    def skip(why):
        nt[why] = nt.get(why, 0) + 1

    m = E.E_FIRST
    while m <= E.E_LAST:
        s = Sx[m]
        if not np.isfinite(s):
            m += 1
            continue
        k = E.atm_index(K, s)
        q = []
        for r in (0, 1):
            if not B1[m, k, r]:
                continue
            c0 = cm[m, k, r]
            above = [HV[tf][m, k, r] for tf in HTF if np.isfinite(HV[tf][m, k, r]) and HV[tf][m, k, r] > c0]
            if not above:
                noabove += 1
                continue
            q.append((r, min(above)))
        if not q:
            m += 1
            continue
        if len(q) == 2:
            skip('both sides')
            m += 1
            continue
        r, T = q[0]
        b0, a0 = bid[m, k, r], ask[m, k, r]
        if not (np.isfinite(b0) and np.isfinite(a0) and a0 > b0 > 0):
            skip('ATM no quote')
            m += 1
            continue
        mid0 = 0.5 * (a0 + b0)
        if not (T - mid0 >= a0 - b0):
            skip('gap < spread')
            m += 1
            continue
        if ver == 'E1':
            sp = (a0 - b0) / mid0
            if sp > 0.03 + 1e-12:
                skip('E1 spread > 3%')
                m += 1
                continue
            ex = k
            _, de = E.iv_delta(np.array([mid0]), s, np.array([K[k]]), (390 - m) / 525600.0, r == 0)
            de = float(de[0])
        else:
            M = cm[m, k, 0] + cm[m, k, 1]
            if not np.isfinite(M):
                skip('no implied move')
                m += 1
                continue
            pk = E.pick_rr(K, bid, ask, m, r, s, M, 0.03)
            if pk is None:
                skip('no R/R contract')
                m += 1
                continue
            ex, de, _, sp = pk
        a_in = float(ask[m, ex, r])
        mid_in = 0.5 * (a_in + float(bid[m, ex, r]))
        x, why = E.FLAT, '15:58'
        for c in range(m + 1, E.FLAT + 1):
            if cm[c, k, r] >= T:
                x, why = c, 'target'
                break
            if BL1[c, k, r]:
                x, why = c, 'stop'
                break
        b_out = S.exit_quote(bid, x, ex, r)
        m_out = S.exit_quote(mid, x, ex, r)
        fee_out = E.FEE if b_out > 0 else 0.0
        usd = (b_out - a_in) * 100 - E.FEE - fee_out
        trades.append(dict(ver=ver, name=name, date=d, m=m, side='C' if r == 0 else 'P', k_sig=float(K[k]),
                           k_ex=float(K[ex]), T=float(T), close_in=float(cm[m, k, r]), delta=de, spread=float(sp),
                           ask=a_in, x=x, why=why, bid_out=b_out, usd=usd, ret=usd / (a_in * 100),
                           ret_mid=(m_out - mid_in) / mid_in if mid_in > 0 else float('nan')))
        m = x + 1
    return trades, nt, noabove


def month_days(mo):
    assert not S.held_month(mo + '-01'), f'{mo} is a held-out month'
    pick = S.split_sessions('option')['pick']
    days = [d for d in S.full_sessions(mo + '-01', mo + '-31')]
    assert days and all(d in pick for d in days), f'{mo} is not wholly inside Pick'
    return days


if __name__ == '__main__':
    (HERE / 'out').mkdir(exist_ok=True)
    for mo in (sys.argv[1:] or ['2025-02', '2025-03']):
        days = month_days(mo)
        R = {}
        for ver in ('E1', 'E2'):
            T, NT, NA = [], {}, 0
            for d in days:
                for nm in E.NAMES:
                    t, nt, na = run_day(nm, d, ver)
                    T += t
                    NA += na
                    for a, b in nt.items():
                        NT[a] = NT.get(a, 0) + b
            R[ver] = dict(trades=T, skips=NT, breaks_no_ema_above=NA)
            print(mo, ver, len(T), NT, NA, flush=True)
        json.dump({'month': mo, 'days': days, **R}, open(HERE / 'out' / f'targets_{mo}.json', 'w'))
