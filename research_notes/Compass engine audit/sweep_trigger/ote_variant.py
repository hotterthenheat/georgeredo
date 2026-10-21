"""A stricter OTE on SPY (robustness): the impulse leg must be >= 5 bps of price and the fill is sought from the third
bar after the return bar, so the 'impulse' is a displacement, not the sweep bar's own range. Same events (X=0, k=1,
confirm=0, merged), nearest-OTM fade, three exits; compared with the close entry on the same episodes.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I ote_variant.py
"""
import datetime as dt, os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S
from common_analysis import load_events, fmt

MIN_LEG = 5e-4; START = 3

def ote_strict(h, l, c, r, H, side, close_m, wait=S.GEOM_WAIT):
    for t in range(r + 1, min(r + wait, close_m, S.ENTRY_HI) + 1):
        if side == 'hi':
            leg_lo = np.nanmin(l[r:t]); leg = H - leg_lo
            if h[t] > H: return None
            if t < r + START or leg < MIN_LEG * H: continue
            if h[t] >= leg_lo + 0.62 * leg: return t
        else:
            leg_hi = np.nanmax(h[r:t]); leg = leg_hi - H
            if l[t] < H: return None
            if t < r + START or leg < MIN_LEG * H: continue
            if l[t] <= leg_hi - 0.62 * leg: return t
    return None

def work(d, rows):
    arr, close_m, half = S.read_bars('SPY', d); h, l, c = arr['high'], arr['low'], arr['close']; spot = S.ffill(c)
    strikes, bid, ask = S.chain_arrays('SPY', d, close_m); S_close = float(spot[close_m]); out = []
    for row in rows:
        side = row['side']; r = row['r']; right = 1 if side == 'hi' else 0
        t = ote_strict(h, l, c, r, row['H'], side, close_m)
        rec = dict(product='SPY', session=d, entry_m=row['entry_m'], side=side, filled=t is not None, ote_m=t, net=None, ret=None, hold_net=None)
        if t is not None:
            p = S.pick_contracts(strikes, bid, ask, t, float(spot[t]), right, want_delta=False)
            if p['otm'] >= 0:
                K = strikes[p['otm']]; a0 = ask[right, p['otm'], t]
                ex = S.exits(bid[right, p['otm']], t, a0, S_close, K, right)
                rec['net'] = ex['trail'][2]; rec['ret'] = ex['trail'][3]; rec['hold_net'] = ex['hold'][2]
        out.append(rec)
    return pl.DataFrame(out)

if __name__ == '__main__':
    E = load_events(products=('SPY',)).filter((pl.col('level') != 'DISP') & (pl.col('X') == 0) & (pl.col('k') == '1') & (pl.col('confirm') == 0)).unique(['product', 'session', 'entry_m', 'side'])
    parts = {d[0]: g.to_dicts() for d, g in E.group_by('session')}
    import multiprocessing as mp
    with mp.get_context('spawn').Pool(2) as pool: frames = pool.starmap(work, [(d, parts[d]) for d in sorted(parts)], chunksize=8)
    R = pl.concat(frames).with_columns(pl.col('session').cast(pl.Date))
    J = E.select('session', 'entry_m', 'side', 'period', 'fo_trail_net', 'fo_trail_ret', 'fo_hold_net').join(R, on=['session', 'entry_m', 'side'])
    print(fmt(J.group_by('period').agg(pl.len().alias('episodes'), pl.col('filled').mean().alias('fill_rate'), (pl.col('ote_m') - pl.col('entry_m')).mean().alias('wait_mins'),
                                       pl.col('net').mean().alias('ote_trail_usd'), pl.col('ret').mean().alias('ote_trail_pct'), (pl.col('net') > 0).mean().alias('ote_win'), pl.col('hold_net').mean().alias('ote_hold_usd'),
                                       pl.col('fo_trail_net').filter(pl.col('filled')).mean().alias('close_same_eps_trail_usd'), pl.col('fo_trail_ret').filter(pl.col('filled')).mean().alias('close_same_eps_trail_pct')).sort('period')))
    for per in ('2022-24', '2025-26'):
        st = S.stress(J.filter(pl.col('period') == per), 'net'); print(f'   stress strict OTE {per} trail: ' + ', '.join(f'{a}={b:.3g}' if isinstance(b, float) else f'{a}={b}' for a, b in st.items()))
    J.write_parquet(os.path.join(S.OUT, 'ote_strict_SPY.parquet'))
