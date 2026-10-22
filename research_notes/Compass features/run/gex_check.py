"""
gex_check.py — the GEX check of prereg section 7, on the exploration set only (SPY, IWM, SPX; QQQ is held out), before any
GEX feature is tested.

Name-sessions: exploration sessions in the spot-exposures span (2023-12-08 → 2026-10-21, held-out months out); IWM from
2024-04-19. One counts when it has a 09:45 GEX row (gamma_per_one_percent_move_oi of the last row whose minute ended by
09:45:00, sign as UW gives it; exactly 0 left out), a 09:45 0DTE implied move (the at-the-money straddle mid of the chain
row stamped 09:45, prereg 2.2; SPX: the SPXW same-day chain) and an official close (SPX: the Cboe file; the ETFs: Theta's
stock EOD close, else UW's daily bar). Realized move = |official close − P| ÷ IM, P = the close of the bar stamped 09:44
(SPX: its 09:45 print). Δ_GEX = mean realized move on negative-GEX name-sessions − mean on positive (pooled), its block-20
interval with the same draws for both groups. Gate: Δ_GEX > 0 and the interval's lower end > 0.

  python3 -I gex_check.py   → out/gex_check.json
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402
import stats as ST  # noqa: E402
import tiers as TI  # noqa: E402

NAMES = ('SPY', 'IWM', 'SPXW')
START = {'SPY': '2023-12-08', 'IWM': '2024-04-19', 'SPXW': '2023-12-08'}
M = C.mi('09:45')


def im_at(name: str, d: str):
    p = C.chain_0dte_path(name, d)
    if p is None:
        return None
    ch = pl.read_parquet(p, columns=['timestamp', 'strike', 'right', 'bid', 'ask']).with_columns(C.mcol().alias('m')).filter(pl.col('m') == M)
    ch = ch.with_columns(pl.col('bid').fill_null(float('nan')), pl.col('ask').fill_null(float('nan')))
    K = np.unique(ch['strike'].to_numpy())
    cb, ca, pb, pa = (np.full(K.size, np.nan) for _ in range(4))
    ki = np.searchsorted(K, ch['strike'].to_numpy())
    isc = ch['right'].to_numpy() == 'CALL'
    b, a = ch['bid'].to_numpy().astype(float), ch['ask'].to_numpy().astype(float)
    cb[ki[isc]], ca[ki[isc]] = b[isc], a[isc]
    pb[ki[~isc]], pa[ki[~isc]] = b[~isc], a[~isc]
    return C.forward_im(K, cb, ca, pb, pa)


def main():
    C.set_split('expl')
    t0 = time.time()
    tt = TI.table(NAMES)
    rows, skipped = [], {}
    for nm in NAMES:
        U = pl.read_parquet(C.WORK / 'uw' / 'expl' / f'{nm}.parquet').filter(pl.col('m') == M)
        g = {d: v for d, v in U.select('day', 'G').iter_rows()}
        off = C.official_spx() if nm == 'SPXW' else {k: v[0] for k, v in C.official_etf(nm).items()}
        for d in C.sessions():
            if d < START[nm] or d > C.LAST_DAY or C.held_month(d):
                continue
            G = g.get(d)
            if G is None:
                skipped[f'{nm}: no 09:45 GEX row'] = skipped.get(f'{nm}: no 09:45 GEX row', 0) + 1
                continue
            if G == 0:
                skipped[f'{nm}: GEX exactly 0'] = skipped.get(f'{nm}: GEX exactly 0', 0) + 1
                continue
            fim = im_at(nm, d)
            if fim is None:
                skipped[f'{nm}: no 09:45 implied move'] = skipped.get(f'{nm}: no 09:45 implied move', 0) + 1
                continue
            close = off.get(d)
            if close is None:
                skipped[f'{nm}: no official close'] = skipped.get(f'{nm}: no official close', 0) + 1
                continue
            P = C.price_at_entry(nm, d, M)
            if not np.isfinite(P):
                skipped[f'{nm}: no price at 09:45'] = skipped.get(f'{nm}: no price at 09:45', 0) + 1
                continue
            IM = fim[2]
            rows.append(dict(name=nm, day=d, G=G, IM=IM, P=P, close=close, rm=abs(close - P) / IM, neg=G < 0,
                             tier=tt.get((nm, d[:7]), 'U')))
        print(nm, len(rows), f'{time.time() - t0:.0f}s', flush=True)
    df = pl.DataFrame(rows)
    sess = sorted(set(df['day'].to_list()))
    allsess = [d for d in C.sessions() if sess[0] <= d <= sess[-1] and not C.held_month(d)]
    neg, pos = df.filter(pl.col('neg')), df.filter(~pl.col('neg'))
    res = dict(prereg=C.PREREG_COMMIT, name_sessions=df.height, negative=neg.height, positive=pos.height, skipped=skipped,
               pooled=ST.delta(neg, pos, allsess, col='rm'))
    res['by_name'] = {nm: ST.delta(neg.filter(pl.col('name') == nm), pos.filter(pl.col('name') == nm), allsess, col='rm')
                      for nm in NAMES}
    res['by_tier'] = {t: ST.delta(neg.filter(pl.col('tier') == t), pos.filter(pl.col('tier') == t), allsess, col='rm')
                      for t in ('1', '2', '3', 'U') if df.filter(pl.col('tier') == t).height}
    res['gate'] = ST.passes(res['pooled'])
    C.write_parquet(df, C.WORK / 'expl' / 'gex_check_rows.parquet')
    C.jdump(res, C.OUT / 'gex_check.json')
    p = res['pooled']
    print('GEX check', df.height, 'name-sessions; Δ', p.get('delta'), p.get('ci'), 'gate', res['gate'], flush=True)


if __name__ == '__main__':
    main()
