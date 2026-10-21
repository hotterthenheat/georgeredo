"""Every liquidity-sweep event of the definition grid, its features at the entry minute, and the trades it would have
made with real 0DTE quotes. One row an (episode, k, confirm); session by session, two worker processes.

Grid (sweeplib): levels OR (09:30-09:59 high/low, from 10:01), PD (prior session high/low), PW (prior ISO week high/low),
SH (the session high/low so far, standing >= 10 bars); side hi/lo; X in {0,2,5,10,20} bps beyond the level; the close
back inside within k in {1,3,5} one-minute bars or on the 5-minute bar; confirm 0 (entry at the return bar's close) or
1 (the next bar closes in the fade direction; entry at its close). Entries 09:35-15:58, 30 minutes between episodes.

Trades, each bought at the ask on the entry minute and sold at the bid: fade (PUT on a high-side sweep, CALL on a
low-side), the nearest OTM strike ('fo') and the 0.30-0.45 |delta| pick ('fd'); continuation, nearest OTM ('co');
module 9 entries on the fade's nearest-OTM: OTE retrace ('ote') and order block ('ob'), filled within 30 bars.
Exits: 50% trailing stop ('trail'), +25% target / -32% stop else hold ('tgt'), hold to 15:58 ('hold').
Displacement-only bars (no sweep within 3 bars) are rows with level 'DISP', traded as continuation ('co') and fade ('fo').

  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I build_events.py SPY            # -> out/events_SPY.parquet, out/spread_SPY.parquet
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I build_events.py SPY 2024-06-03 # one session, printed
"""
import datetime as dt, os, sys, time
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S

EXITS = ('trail', 'tgt', 'hold')
FADE_WINDOWS = ((25, 65), (65, 150), (360, 390)); CHASE_WINDOWS = ((0, 25), (255, 360))
def window_of(m):
    t = m + 570
    if 595 <= t < 635: return 'fade1'
    if 635 <= t < 720: return 'fade2'
    if 930 <= t <= 960: return 'fade3'
    if 570 <= t < 595: return 'chase1'
    if 825 <= t < 930: return 'chase2'
    return 'noon'

def trade_cols(prefix, strikes, bid, ask, m, S_m, S_close, right, pick, rec):
    """fill the pick's trade columns into rec; pick is a strike index or -1"""
    for ex in EXITS:
        for f in ('m', 'px', 'net', 'ret'): rec[f'{prefix}_{ex}_{f}'] = np.nan
    rec[f'{prefix}_K'] = np.nan; rec[f'{prefix}_ask'] = np.nan; rec[f'{prefix}_bid'] = np.nan; rec[f'{prefix}_spr'] = np.nan
    if pick < 0: return
    K = strikes[pick]; a0 = ask[right, pick, m]; b0 = bid[right, pick, m]
    rec[f'{prefix}_K'] = K; rec[f'{prefix}_ask'] = a0; rec[f'{prefix}_bid'] = b0; rec[f'{prefix}_spr'] = (a0 - b0) / (0.5 * (a0 + b0))
    ex = S.exits(bid[right, pick], m, a0, S_close, K, right)
    for name, (xm, xp, net, ret) in ex.items():
        rec[f'{prefix}_{name}_m'] = xm; rec[f'{prefix}_{name}_px'] = xp; rec[f'{prefix}_{name}_net'] = net; rec[f'{prefix}_{name}_ret'] = ret

def session(root, d, days, volmat, volidx):
    u = S.BAR_SOURCE[root]
    arr, close_m, half = S.read_bars(u, d)
    if arr is None or half: return None, None
    o, h, l, c, v = arr['open'], arr['high'], arr['low'], arr['close'], arr['volume']
    spot = S.read_prints('SPX', d) if root == 'SPXW' else S.ffill(c)
    vix = S.read_prints('VIX', d)
    S_close = float(spot[close_m])
    row = days.get(d)
    if row is None: return None, None
    strikes, bid, ask = S.chain_arrays(root, d, close_m)
    if len(strikes) == 0: return None, None
    # the ATM straddle a minute (strike nearest spot with both sides quoted)
    mids = 0.5 * (bid + ask)
    # relative volume: the 20 sessions before this one, same minutes
    i = volidx.get(d); vol_ref = volmat[max(0, i - 20):i] if i is not None and i >= 10 else None
    # levels
    orh, orl = (np.nanmax(h[1:31]), np.nanmin(l[1:31])) if not np.isnan(h[1:31]).all() else (np.nan, np.nan)
    lev = {'OR': (orh, orl, 31), 'PD': (row['pdh'], row['pdl'], S.ENTRY_LO), 'PW': (row['pwh'], row['pwl'], S.ENTRY_LO)}
    runhi = np.maximum.accumulate(np.nan_to_num(h, nan=-np.inf)); runlo = np.minimum.accumulate(np.nan_to_num(l, nan=np.inf))

    def features(r, side, e, L, H, rec):
        rec['window'] = window_of(r); rec['m'] = r
        rec['depth_bps'] = (H - L) / L * 1e4 if side == 'hi' else (L - H) / L * 1e4
        rec['bars_out'] = r - e + 1
        rec['or_pos'] = (c[r] - orl) / (orh - orl) if (r > 30 and orh > orl) else np.nan
        rec['vix'] = vix[r]
        rec['day_move_atr'] = (c[r] - row['prev_close']) / row['atr14'] if row['atr14'] and row['atr14'] > 0 else np.nan
        rec['range_r_bps'] = (h[r] - l[r]) / c[r] * 1e4
        if vol_ref is not None:
            cur = np.nansum(v[r - 4:r + 1]); ref = np.nanmedian(vol_ref[:, r - 4:r + 1].sum(axis=1))
            rec['rel_vol'] = cur / ref if ref > 0 else np.nan
        else: rec['rel_vol'] = np.nan
        Sm = spot[r]
        j = int(np.nanargmin(np.abs(strikes - Sm))) if len(strikes) else -1
        st = np.nan
        for jj in sorted(range(max(0, j - 2), min(len(strikes), j + 3)), key=lambda q: abs(strikes[q] - Sm)):
            if not np.isnan(mids[0, jj, r]) and not np.isnan(mids[1, jj, r]): st = mids[0, jj, r] + mids[1, jj, r]; break
        rec['straddle'] = st; rec['straddle_rel'] = st / Sm if st == st else np.nan
        rec['fvg'] = S.fvg_present(h, l, r, side)
        rec['ob'] = 1 if S.order_block(o, h, l, c, r, side) is not None else 0
        rec['pd_near'] = int(min(abs(L - row['pdh']), abs(L - row['pdl'])) / L <= 0.002) if row['pdh'] else 0
        s = -1.0 if side == 'hi' else 1.0
        for hz in (5, 15, 30, 60):
            t = min(r + hz, close_m); rec[f'fwd_{hz}'] = s * (c[t] - c[r]) / c[r] * 1e4
        rec['fwd_close'] = s * (c[close_m] - c[r]) / c[r] * 1e4
        rec['fwd_max30'] = s * ((np.nanmax(h[r + 1:min(r + 31, close_m + 1)]) if side == 'lo' else np.nanmin(l[r + 1:min(r + 31, close_m + 1)])) - c[r]) / c[r] * 1e4 if r + 1 <= close_m else np.nan

    def trades(r, side, rec, geometry=True, e=None, H=None):
        Sm = float(spot[r]); fade_right = 1 if side == 'hi' else 0; cont_right = 1 - fade_right
        rec['spot'] = Sm
        pf = S.pick_contracts(strikes, bid, ask, r, Sm, fade_right)
        rec['fo_delta'] = pf['otm_delta']; rec['fo_iv'] = pf['otm_iv']; rec['fd_delta'] = pf['dlt_delta']; rec['fd_iv'] = pf['dlt_iv']
        trade_cols('fo', strikes, bid, ask, r, Sm, S_close, fade_right, pf['otm'], rec)
        trade_cols('fd', strikes, bid, ask, r, Sm, S_close, fade_right, pf['dlt'], rec)
        pc = S.pick_contracts(strikes, bid, ask, r, Sm, cont_right)
        trade_cols('co', strikes, bid, ask, r, Sm, S_close, cont_right, pc['otm'], rec)
        rec['fo_dist_str'] = abs(rec['fo_K'] - Sm) / rec['straddle'] if rec.get('straddle', np.nan) == rec.get('straddle', np.nan) and pf['otm'] >= 0 else np.nan
        rec['ote_m'] = np.nan; rec['ob_m'] = np.nan
        for g in ('ote', 'ob'): trade_cols(g, strikes, bid, ask, r, Sm, S_close, fade_right, -1, rec)
        if geometry and H is not None:
            t1 = S.ote_fill(h, l, c, r, H, side, close_m)
            t2 = S.ob_fill(h, l, r, S.order_block(o, h, l, c, r, side), H, side, close_m)
            for g, t in (('ote', t1), ('ob', t2)):
                if t is None: continue
                rec[f'{g}_m'] = t; St = float(spot[t])
                pg = S.pick_contracts(strikes, bid, ask, t, St, fade_right)
                trade_cols(g, strikes, bid, ask, t, St, S_close, fade_right, pg['otm'], rec)

    rows = []
    base = dict(product=root, session=d)
    for level in S.LEVELS:
        for side in ('hi', 'lo'):
            for X in S.X_GRID:
                # 1-minute episodes
                if level == 'SH':
                    eps = S.episodes_session_extreme(h, l, c, side, X, S.ENTRY_LO, close_m)
                else:
                    Lh, Ll, first = lev[level]; L0 = Lh if side == 'hi' else Ll
                    if L0 is None or not np.isfinite(L0): eps = []
                    else: eps = [(e, L0) for e in S.episodes_static(h, l, c, L0, side, X, first, close_m)]
                for e, L in eps:
                    for k in (1, 3, 5):
                        r = S.return_bar(c, e, L, side, k, close_m)
                        if r is None: continue
                        H = np.nanmax(h[e:r + 1]) if side == 'hi' else np.nanmin(l[e:r + 1])
                        for confirm in (0, 1):
                            m_in = r if confirm == 0 else r + 1
                            if confirm and not (m_in <= close_m and ((side == 'hi' and c[r + 1] < c[r]) or (side == 'lo' and c[r + 1] > c[r]))): continue
                            if m_in < S.ENTRY_LO or m_in > S.ENTRY_HI or np.isnan(spot[m_in]): continue
                            rec = dict(base, level=level, side=side, X=X, k=str(k), confirm=confirm, e=e, r=r, entry_m=m_in, L=float(L), H=float(H))
                            features(r, side, e, L, H, rec)
                            trades(m_in, side, rec, geometry=(confirm == 0), e=e, H=H)
                            rows.append(rec)
                # 5-minute bars
                if level == 'SH':
                    def level_fn(M, side=side):
                        L = runhi[M - 5] if side == 'hi' else runlo[M - 5]
                        if not np.isfinite(L) or M - 5 - S.SH_AGE < 1: return None
                        stale = (runhi[M - 5 - S.SH_AGE] == L) if side == 'hi' else (runlo[M - 5 - S.SH_AGE] == L)
                        return L if stale else None
                    first = S.ENTRY_LO
                else:
                    Lh, Ll, first = lev[level]; L0 = Lh if side == 'hi' else Ll
                    if L0 is None or not np.isfinite(L0): continue
                    def level_fn(M, L0=L0): return L0
                for M, L, H in S.five_min_episodes(h, l, c, level_fn, side, X, first, close_m):
                    for confirm in (0, 1):
                        m_in = M if confirm == 0 else M + 5
                        if confirm and not (m_in <= close_m and ((side == 'hi' and c[M + 5] < c[M]) or (side == 'lo' and c[M + 5] > c[M]))): continue
                        if m_in < S.ENTRY_LO or m_in > S.ENTRY_HI or np.isnan(spot[m_in]): continue
                        rec = dict(base, level=level, side=side, X=X, k='5m', confirm=confirm, e=M - 4, r=M, entry_m=m_in, L=float(L), H=float(H))
                        features(M, side, M - 4, L, H, rec)
                        trades(m_in, side, rec, geometry=(confirm == 0), e=M - 4, H=H)
                        rows.append(rec)
    # displacement-only bars: no sweep (any level, X = 0, k <= 5) returning within 3 bars
    sweep_bars = set()
    for rec in rows:
        if rec['X'] == 0 and rec['k'] in ('1', '3', '5'): sweep_bars.update(range(rec['r'] - 3, rec['r'] + 4))
    last = -10**6
    for m, dr in S.displacement_bars(o, h, l, c, close_m):
        if m < S.ENTRY_LO or m > S.ENTRY_HI or m in sweep_bars or m - last < S.COOLDOWN or np.isnan(spot[m]): continue
        last = m
        side = 'lo' if dr > 0 else 'hi'       # a 'lo'-side row's fade is a CALL ... here the displacement is UP, so its continuation ('co') is the CALL
        rec = dict(base, level='DISP', side=side, X=0, k='1', confirm=0, e=m, r=m, entry_m=m, L=float(o[m]), H=float(c[m]))
        features(m, side, m, o[m], c[m], rec)
        rec['depth_bps'] = abs(c[m] - o[m]) / o[m] * 1e4
        trades(m, side, rec, geometry=False)
        rows.append(rec)
    ev = pl.DataFrame(rows, infer_schema_length=None) if rows else None
    # the spread rule by minute: nearest OTM call and put, (ask - bid) / mid <= 5%
    sp_rows = []
    for m in range(S.ENTRY_LO, min(S.ENTRY_HI, close_m) + 1):
        Sm = spot[m]
        if np.isnan(Sm): continue
        for right in (0, 1):
            p = S.pick_contracts(strikes, bid, ask, m, Sm, right, want_delta=False)
            j = p['otm']
            if j < 0: sp_rows.append(dict(product=root, session=d, m=m, right=right, spr=np.nan, mid=np.nan)); continue
            a0 = ask[right, j, m]; b0 = bid[right, j, m]
            sp_rows.append(dict(product=root, session=d, m=m, right=right, spr=(a0 - b0) / (0.5 * (a0 + b0)), mid=0.5 * (a0 + b0)))
    return ev, pl.DataFrame(sp_rows)

def load_days(root):
    u = S.BAR_SOURCE[root]
    T = S.load_day_table(u)
    days = {r['session']: r for r in T.select('session', 'pdh', 'pdl', 'pwh', 'pwl', 'prev_close', 'atr14').to_dicts()}
    volmat = np.array(T['volume'].to_list(), dtype=float)
    volidx = {s: i for i, s in enumerate(T['session'].to_list())}
    return days, volmat, volidx

_G = {}
def _init(root):
    _G['days'], _G['volmat'], _G['volidx'] = load_days(root); _G['root'] = root
def _work(d):
    try:
        return session(_G['root'], d, _G['days'], _G['volmat'], _G['volidx'])
    except Exception as ex:
        print('FAILED', _G['root'], d, repr(ex), flush=True); return None, None

def run_product(root, workers=2, limit=None):
    sess = S.sessions_of(root)
    if limit: sess = sess[:limit]
    import multiprocessing as mp
    t0 = time.time(); evs = []; sps = []
    with mp.get_context('spawn').Pool(workers, initializer=_init, initargs=(root,)) as pool:
        for i, (ev, sp) in enumerate(pool.imap(_work, sess, chunksize=4)):
            if ev is not None: evs.append(ev)
            if sp is not None: sps.append(sp)
            if (i + 1) % 100 == 0: print(root, i + 1, 'of', len(sess), f'{time.time() - t0:.0f}s', flush=True)
    E = pl.concat(evs, how='diagonal_relaxed'); P = pl.concat(sps, how='vertical_relaxed')
    E.write_parquet(os.path.join(S.OUT, f'events_{root}.parquet'), compression='zstd'); P.write_parquet(os.path.join(S.OUT, f'spread_{root}.parquet'), compression='zstd')
    print(root, 'sessions', len(sess), 'event rows', E.height, 'spread rows', P.height, f'{time.time() - t0:.0f}s', flush=True)

if __name__ == '__main__':
    root = sys.argv[1]
    if len(sys.argv) == 3:
        pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_rows(30)
        days, volmat, volidx = load_days(root)
        t0 = time.time(); ev, sp = session(root, dt.date.fromisoformat(sys.argv[2]), days, volmat, volidx); print(f'{time.time() - t0:.2f}s')
        print(ev.height, 'rows'); print(ev.group_by('level', 'k').agg(pl.len()).sort('level', 'k'))
        print(ev.filter((pl.col('X') == 0) & (pl.col('k') == '1') & (pl.col('confirm') == 0)).select('level', 'side', 'e', 'r', 'entry_m', 'L', 'H', 'depth_bps', 'spot', 'fo_K', 'fo_ask', 'fo_bid', 'fo_delta', 'fd_K', 'fd_delta', 'fo_trail_m', 'fo_trail_px', 'fo_trail_ret', 'fo_hold_ret', 'co_hold_ret', 'ote_m', 'ob_m', 'fvg', 'rel_vol', 'straddle', 'fwd_30', 'window'))
        print(sp.group_by('right').agg((pl.col('spr') <= 0.05).mean(), pl.col('mid').median()))
    else:
        run_product(root, workers=int(os.environ.get('WORKERS', '2')), limit=int(os.environ['LIMIT']) if 'LIMIT' in os.environ else None)
