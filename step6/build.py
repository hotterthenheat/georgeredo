"""Step 6a: the anatomy of the runners. Every population trade (step6/PREREG.md section 1), followed from the buy to the
peak of its bid in two windows, with what the underlying and the option did on the way, the three pre-registered exits,
and everything that was visible at the buy minute.

Trades are step 2's (step2/out/entries_<PRODUCT>.parquet) joined to step 3's session-and-minute table
(step3/out/features_<PRODUCT>.parquet: straddle_entry, prior_close, gap, prior_range). Same raw files, clock and prices as
steps 1-5: minute 0 = 9:30; an ETF bar stamped t closes at t+1; an SPX or VIX print is stamped when taken; a quote counts
when bid and ask are both there and ask >= bid >= 0.

Writes, per product, $WORK/trades_<PRODUCT>.parquet (WORK defaults to the data root's scratchpad, step6/). One row a trade:
- keys: product, root, session, period (pick/check), strike, right, entry_minute, entry_bid, entry_ask, x (moneyness in
  remaining moves, out of the money positive), xbin, cell.
- for each window w in (60, 1530): peak_w, peak_min_w, mult_w (peak / ask); the Part 1 measures to the peak (mv_pts_w,
  mv_pct_w, mv_em_w, mv_em0_w, burst1_w, burst5_w, iv_peak_w, the Shapley split dprice_w, dvol_w, dtime_w, dspread_w as $
  per share, the underlying events or_w, vwapx_w, flipx_w, newext_w, rev_w).
- the exits: r_a, net_a, xm_a, why_a; r_b, ...; r_c, ... (PREREG 5.2, fees included).
- the buy-minute features: step 5's raw columns (step5/features.py `session`, reused as is) and this step's day context
  (vwap, or_state, uw_gamma, flip, event, iv_entry, fwd_entry). Step 5's derived features are formed by `step5_derived`
  (the same expressions as step5/model.py `load`).
- the day (after the fact): day_hi, day_lo, day_open, day_close, vix_close.

  python3 -I step6/build.py                 # every product
  python3 -I step6/build.py SPY 2024-06-03  # one session, printed
"""
import datetime as dt, json, os, sys, warnings
import numpy as np, polars as pl
from scipy.special import ndtr

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
from step1.breakdown import RAW, UNDERLYING, spot_series   # noqa: E402
import step5.features as s5                                  # noqa: E402

warnings.filterwarnings('ignore', message='Sortedness of columns')
SP = os.path.dirname(RAW)
WORK = os.environ.get('WORK', os.path.join(SP, 'step6')); os.makedirs(WORK, exist_ok=True)
UWDIR = os.path.join(SP, 'features_data', 'uw')
UWT = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
HELD_OUT = {'2017-06', '2017-09', '2017-10', '2018-01', '2019-07', '2019-08', '2020-06', '2020-08', '2020-11', '2020-12', '2021-01',
            '2021-03', '2021-05', '2021-11', '2022-04', '2022-12', '2023-05', '2023-11', '2024-05', '2024-06', '2024-07', '2024-08',
            '2024-11', '2025-08', '2025-11', '2026-03', '2026-04', '2026-08'}
ENTRY_TIMES = [1, 30, 60, 90, 150, 210, 270, 330]
LAST, CLOSE = 360, 390          # 3:30 pm, 4:00 pm
END = dt.date(2026, 10, 9); CHECK_FROM = dt.date(2025, 1, 1)
XBINS = [(-1.0, -0.5), (-0.5, -0.2), (-0.2, 0.0), (0.0, 0.2), (0.2, 0.5), (0.5, 1.0000001)]
EPS = 1e-9
YEAR_MIN = 252 * 390
TGT, STOP, TRAIL = 1.40, 0.70, 0.50
MACRO = {}
for ev in json.load(open(os.path.join(ROOT, 'data', 'macro_events_2022_2027.json'))):
    if ev['event'] in ('FOMC_DECISION', 'CPI', 'NFP'):
        MACRO.setdefault(ev['date'], set()).add({'FOMC_DECISION': 'FOMC'}.get(ev['event'], ev['event']))

def held_out(d): return d.strftime('%Y-%m') in HELD_OUT

def fee(root, price):
    """per contract, one way (PREREG 5.2); price per share"""
    if root != 'SPXW': return np.full(np.shape(price), 0.65)
    return np.where(np.asarray(price) < 1.0, 1.18748, 1.27748)

# ---- Black-76 on the forward, undiscounted ---------------------------------------------------------------------------------------
def b76(F, K, s, t, call):
    s = np.maximum(s, 1e-12); t = np.maximum(t, 1e-12)
    v = s * np.sqrt(t); d1 = (np.log(F / K) + 0.5 * v * v) / v; d2 = d1 - v
    c = F * ndtr(d1) - K * ndtr(d2)
    return np.where(call, c, c - F + K)

def implied(price, F, K, t, call):
    """the vol that prices `price`; NaN when the price is outside (intrinsic, upper bound)"""
    intr = np.where(call, np.maximum(F - K, 0), np.maximum(K - F, 0)); up = np.where(call, F, K)
    ok = np.isfinite(price) & np.isfinite(F) & (price > intr + 1e-9) & (price < up)
    lo, hi = np.full(price.shape, np.log(1e-4)), np.full(price.shape, np.log(50.0))
    for _ in range(80):
        mid = 0.5 * (lo + hi); p = b76(F, K, np.exp(mid), t, call)
        big = p > price; hi = np.where(big, mid, hi); lo = np.where(big, lo, mid)
    return np.where(ok, np.exp(0.5 * (lo + hi)), np.nan)

def shapley(F0, F1, s0, s1, t0, t1, K, call):
    """the change B76(F1,s1,t1) - B76(F0,s0,t0) split into price, vol and time by the Shapley average over the 8 corners"""
    f = {}
    for a in (0, 1):
        for b in (0, 1):
            for c in (0, 1):
                f[a, b, c] = b76(F1 if a else F0, K, s1 if b else s0, t1 if c else t0, call)
    def phi(i):
        tot = 0.0
        for o1 in (0, 1):
            for o2 in (0, 1):
                w = 1 / 3 if o1 == o2 else 1 / 6
                idx0 = [o1, o2]; idx0.insert(i, 0); idx1 = [o1, o2]; idx1.insert(i, 1)
                tot = tot + w * (f[tuple(idx1)] - f[tuple(idx0)])
        return tot
    return phi(0), phi(1), phi(2)

# ---- per session -----------------------------------------------------------------------------------------------------------------
def minute_of(col): return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

def grid_np(m, v, n=CLOSE + 1):
    """minute 0..n-1 -> the last value at or before it (NaN before the first)"""
    g = np.full(n, np.nan); m = np.asarray(m, int); v = np.asarray(v, float)
    ok = (m >= 0) & (m < n) & np.isfinite(v); g[m[ok]] = v[ok]
    have = np.isfinite(g)
    idx = np.where(have, np.arange(n), -1); np.maximum.accumulate(idx, out=idx)
    return np.where(idx >= 0, g[np.maximum(idx, 0)], np.nan)

def uw_rows(kind, tk, d):
    p = os.path.join(UWDIR, kind, tk, f'{d}.parquet')
    return pl.read_parquet(p) if os.path.exists(p) else None

def day_context(root, d, prior_day):
    """underlying grid, VWAP grid, VIX grid, forward per minute, UW gamma rows, prior flip, for one session"""
    u = UNDERLYING[root]
    sp = spot_series(u, d).filter(pl.col('m') <= CLOSE)
    px = grid_np(sp['m'].to_numpy(), sp['px'].to_numpy())
    # VWAP: an ETF's own bars ((h + l + c) / 3 x volume), a bar stamped t counted from minute t+1 (when it has closed)
    etf = 'SPY' if u == 'SPX' else u
    b = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', etf, f'{d}.parquet')).with_columns(minute_of('timestamp').alias('m'))
    b = b.filter((pl.col('m') >= 0) & (pl.col('m') < CLOSE) & pl.col('volume').is_not_null() & pl.col('close').is_not_null())
    tp = ((b['high'] + b['low'] + b['close']) / 3).to_numpy(); vol = b['volume'].to_numpy().astype(float); mm = b['m'].to_numpy() + 1
    pv = np.zeros(CLOSE + 1); vv = np.zeros(CLOSE + 1)
    np.add.at(pv, mm, tp * vol); np.add.at(vv, mm, vol)
    cpv, cvv = np.cumsum(pv), np.cumsum(vv)
    vwap = np.where(cvv > 0, cpv / np.where(cvv > 0, cvv, 1), np.nan)
    if u == 'SPX':      # SPY's VWAP scaled by SPX / SPY at the minute
        spy = spot_series('SPY', d).filter(pl.col('m') <= CLOSE)
        spypx = grid_np(spy['m'].to_numpy(), spy['px'].to_numpy())
        vwap = vwap * px / spypx
    v = pl.read_parquet(os.path.join(RAW, 'data', 'index', 'VIX', f'{d}.parquet')).with_columns(minute_of('timestamp').alias('m')) \
        .filter(pl.col('price').is_not_null() & (pl.col('m') >= 1))
    vix = grid_np(v['m'].to_numpy(), v['price'].to_numpy())
    # UW: net OI gamma rows stamped at or before each minute; the prior session's gamma flip
    tk = UWT[root]; gam = np.full(CLOSE + 1, np.nan)
    se = uw_rows('spot_exposures', tk, d)
    if se is not None and se.height:
        ny = se.with_columns(pl.col('time').dt.convert_time_zone('America/New_York').alias('ny'))
        # the minute by which the row was known: its stamp rounded up to the minute
        ny = ny.with_columns(((pl.col('ny').dt.hour().cast(pl.Int32) * 60 + pl.col('ny').dt.minute().cast(pl.Int32) - 570)
                              + ((pl.col('ny').dt.second() > 0) | (pl.col('ny').dt.nanosecond() > 0)).cast(pl.Int32)).alias('m'))
        ny = ny.filter(pl.col('gamma_per_one_percent_move_oi').is_not_null()).sort('ny')
        mk = ny['m'].to_numpy(); gv = ny['gamma_per_one_percent_move_oi'].to_numpy()
        early = mk < 0
        if early.any(): gam[0] = gv[early][-1]
        late = (mk >= 0) & (mk <= CLOSE)
        g2 = np.full(CLOSE + 1, np.nan)
        for a, val in zip(mk[late], gv[late]): g2[a] = val           # sorted by time: the last row a minute wins
        g2[0] = gam[0] if np.isnan(g2[0]) else g2[0]
        gam = grid_np(np.nonzero(np.isfinite(g2))[0], g2[np.isfinite(g2)])
    flip = np.nan
    if prior_day is not None and not held_out(prior_day):
        gl = uw_rows('gex_levels', tk, prior_day)
        if gl is not None and gl.height and gl['gamma_flip'][0] is not None: flip = float(gl['gamma_flip'][0])
    return px, vwap, vix, gam, flip

def forwards(q, px):
    """per minute: the median of K + C_mid - P_mid over the three strikes nearest the price with both quoted (ask > 0)"""
    a = q.filter(pl.col('ask') > 0).with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
    p = a.filter(pl.col('right') == 'CALL').select('m', 'strike', pl.col('mid').alias('c')).join(
        a.filter(pl.col('right') == 'PUT').select('m', 'strike', pl.col('mid').alias('p')), on=['m', 'strike'])
    p = p.join(pl.DataFrame({'m': np.arange(CLOSE + 1, dtype=np.int32), 'px': px}), on='m').filter(pl.col('px').is_not_nan())
    p = p.with_columns((pl.col('strike') - pl.col('px')).abs().alias('dist')).sort('m', 'dist', 'strike')
    f = p.group_by('m', maintain_order=True).head(3).group_by('m').agg((pl.col('strike') + pl.col('c') - pl.col('p')).median().alias('F'))
    out = np.full(CLOSE + 1, np.nan); out[f['m'].to_numpy()] = f['F'].to_numpy()
    return out

def session(root, d, T, prior_day):
    """T: this session's population trades (step 2 + step 3 columns). Returns one row a trade."""
    # step 5's buy-minute features, by step 5's own code
    T5 = T.select('session', 'strike', 'right', 'entry_minute', 'entry_ask').with_columns(
        pl.lit('fixed').alias('tag'), pl.lit(CLOSE).alias('close_minute'), pl.lit(None, pl.Float64).alias('low_before'))
    F5 = s5.session(root, d, T5)[0].drop('tag', 'close_minute', 'low_before', 'session', 'entry_ask')
    T = T.join(F5, on=['strike', 'right', 'entry_minute'], how='left')
    if T['px'].null_count(): raise SystemExit(f'{root} {d}: step 5 features missing')
    if ((T['straddle'] - T['straddle_entry']).abs() > 1e-9).any(): raise SystemExit(f'{root} {d}: step 5 straddle differs from step 3')

    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
    c = c.with_columns(minute_of('timestamp').alias('m'))
    two = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0)
    q = c.filter((pl.col('m') >= 1) & (pl.col('m') <= CLOSE) & two).select('strike', 'right', 'm', 'bid', 'ask')
    px, vwap, vix, gam, flip = day_context(root, d, prior_day)
    fwd = forwards(q, px)

    # the population's contracts as dense minute arrays
    keys = T.select('strike', 'right').unique(maintain_order=True).with_row_index('ci')
    qq = q.join(keys, on=['strike', 'right'])
    nC = keys.height
    BID = np.full((nC, CLOSE + 1), np.nan); ASK = np.full((nC, CLOSE + 1), np.nan)
    ci, mm = qq['ci'].to_numpy(), qq['m'].to_numpy()
    BID[ci, mm] = qq['bid'].to_numpy(); ASK[ci, mm] = qq['ask'].to_numpy()
    T = T.join(keys, on=['strike', 'right'])
    n = T.height
    cidx = T['ci'].to_numpy(); e = T['entry_minute'].to_numpy(); ask0 = T['entry_ask'].to_numpy(); bid0 = T['entry_bid'].to_numpy()
    K = T['strike'].to_numpy(); call = (T['right'] == 'CALL').to_numpy(); dirn = np.where(call, 1.0, -1.0)
    B = BID[cidx]; A = ASK[cidx]; M = np.arange(CLOSE + 1)[None, :]
    if not np.allclose(B[np.arange(n), e], bid0) or not np.allclose(A[np.arange(n), e], ask0): raise SystemExit(f'{root} {d}: entry quote mismatch')
    # the lowest ask before the buy (ask > 0), as step 4/5's low_before
    Apos = np.where((A > 0) & (M < e[:, None]) & (M >= 1), A, np.inf)
    low_before = Apos.min(1); low_before[~np.isfinite(low_before)] = np.nan

    out = {'low_before': low_before}
    P = px[None, :].repeat(n, 0)
    hi_e = np.array([np.nanmax(px[1:k + 1]) for k in e]); lo_e = np.array([np.nanmin(px[1:k + 1]) for k in e])
    or_hi, or_lo = np.nanmax(px[1:31]), np.nanmin(px[1:31])
    # the first break of the opening range after 10:00, each way
    up_brk = np.nonzero((np.arange(CLOSE + 1) > 30) & (px > or_hi))[0]; dn_brk = np.nonzero((np.arange(CLOSE + 1) > 30) & (px < or_lo))[0]
    first_up = up_brk[0] if up_brk.size else 10 ** 6; first_dn = dn_brk[0] if dn_brk.size else 10 ** 6
    first_with = np.where(call, first_up, first_dn); first_against = np.where(call, first_dn, first_up)
    tau = lambda m: (CLOSE - m) / YEAR_MIN
    mid0 = (ask0 + bid0) / 2; F0 = fwd[e]; t0 = tau(e)
    iv0 = implied(mid0, F0, K, t0, call)
    out.update(fwd_entry=F0, iv_entry=iv0)
    strad = T['straddle_entry'].to_numpy(); strad0 = T['straddle_open'].to_numpy()

    for w in (60, 1530):
        hi_m = np.minimum(e + 60, LAST) if w == 60 else np.full(n, LAST)
        win = (M > e[:, None]) & (M <= hi_m[:, None])
        Bw = np.where(win, B, np.nan)
        has = np.isfinite(Bw).any(1)
        Bf = np.where(np.isfinite(Bw), Bw, -np.inf)
        pk = Bf.max(1); pm = Bf.argmax(1)
        pk = np.where(has, pk, np.nan); pm = np.where(has, pm, -1)
        out[f'peak_{w}'] = pk; out[f'peak_min_{w}'] = pm; out[f'mult_{w}'] = pk / ask0
        okp = has
        pmc = np.where(okp, pm, e)
        s_e, s_p = px[e], px[pmc]
        mv = dirn * (s_p - s_e)
        out[f'mv_pts_{w}'] = np.where(okp, mv, np.nan); out[f'mv_pct_{w}'] = np.where(okp, mv / s_e * 100, np.nan)
        out[f'mv_em_{w}'] = np.where(okp, mv / strad, np.nan); out[f'mv_em0_{w}'] = np.where(okp, mv / strad0, np.nan)
        # steady or burst: the largest 1- and 5-minute moves the contract's way between the buy and the peak, over the move
        d1 = np.full(n, np.nan); d5 = np.full(n, np.nan)
        for i in np.nonzero(okp & (mv > 0))[0]:
            seg = dirn[i] * px[e[i]:pmc[i] + 1]
            d1[i] = np.max(np.diff(seg))
            d5[i] = np.max(seg[5:] - seg[:-5]) if seg.size > 5 else seg[-1] - seg[0]
        out[f'burst1_{w}'] = d1 / mv; out[f'burst5_{w}'] = d5 / mv
        # the option's change split by repricing
        bidp, askp = B[np.arange(n), pmc], A[np.arange(n), pmc]
        midp = (bidp + askp) / 2; F1 = fwd[pmc]; t1 = tau(pmc)
        iv1 = implied(midp, F1, K, t1, call)
        dp, dv, dtm = shapley(F0, F1, iv0, iv1, t0, t1, K, call)
        good = okp & np.isfinite(iv0) & np.isfinite(iv1)
        out[f'iv_peak_{w}'] = np.where(okp, iv1, np.nan)
        out[f'dprice_{w}'] = np.where(good, dp, np.nan); out[f'dvol_{w}'] = np.where(good, dv, np.nan); out[f'dtime_{w}'] = np.where(good, dtm, np.nan)
        out[f'dspread_{w}'] = np.where(okp, (mid0 - ask0) + (bidp - midp), np.nan)
        out[f'dmid_{w}'] = np.where(okp, midp - mid0, np.nan)
        # what the underlying did between the buy and the peak
        orx = np.zeros(n, bool); newx = np.zeros(n, bool); rev = np.zeros(n, bool)
        for i in np.nonzero(okp)[0]:
            seg = px[e[i] + 1:pmc[i] + 1]
            if call[i]:
                newx[i] = np.nanmax(seg) > hi_e[i] + EPS
                rev[i] = pmc[i] - e[i] > 1 and np.nanmin(px[e[i] + 1:pmc[i]]) < lo_e[i] - EPS
            else:
                newx[i] = np.nanmin(seg) < lo_e[i] - EPS
                rev[i] = pmc[i] - e[i] > 1 and np.nanmax(px[e[i] + 1:pmc[i]]) > hi_e[i] + EPS
            orx[i] = e[i] < first_with[i] <= pmc[i]
        out[f'or_{w}'] = np.where(okp, orx, False); out[f'newext_{w}'] = newx; out[f'rev_{w}'] = rev
        out[f'vwapx_{w}'] = okp & (dirn * (s_e - vwap[e]) < 0) & (dirn * (s_p - vwap[pmc]) > 0)
        fx = okp & np.isfinite(flip) & (dirn * (s_e - flip) < 0) & (dirn * (s_p - flip) > 0)
        out[f'flipx_{w}'] = np.where(np.isfinite(flip), fx.astype(float), np.nan)
        out[f'spot_peak_{w}'] = np.where(okp, s_p, np.nan)

    # ---- the exits (PREREG 5.2) -------------------------------------------------------------------------------------------------
    fin = fee(root, ask0)
    def last_bid(upto):
        """the last bid at or before `upto` (from the buy minute on)"""
        msk = (M >= e[:, None]) & (M <= upto[:, None]) & np.isfinite(B)
        j = np.where(msk, M, -1).max(1)
        return B[np.arange(n), j], j
    def first(mask):
        any_ = mask.any(1); j = mask.argmax(1)
        return np.where(any_, j, -1)
    tgt = TGT * ask0
    # (a) +40% / -30% / out at 60 min or 3:30
    end_a = np.minimum(e + 60, LAST)
    win = (M > e[:, None]) & (M <= end_a[:, None])
    Bw = np.where(win, B, np.nan)
    jt = first(Bw >= tgt[:, None] - EPS); js = first(Bw <= STOP * ask0[:, None] + EPS)
    tb, tj = last_bid(end_a)
    t_first = (jt >= 0) & ((js < 0) | (jt < js)); s_first = (js >= 0) & ~t_first
    xp = np.where(t_first, tgt, np.where(s_first, B[np.arange(n), np.maximum(js, 0)], tb))
    xm = np.where(t_first, jt, np.where(s_first, js, tj))
    why = np.where(t_first, 'target', np.where(s_first, 'stop', 'time'))
    net = (xp - ask0) * 100 - fin - np.where(xp > 0, fee(root, xp), 0.0)
    out.update(net_a=net, r_a=net / (ask0 * 100), xm_a=xm, why_a=why, xp_a=xp)
    # (b) a 50% trail armed at +40%, out at 3:30
    win = (M > e[:, None]) & (M <= LAST)
    Bw = np.where(win, B, np.nan)
    ja = first(Bw >= tgt[:, None] - EPS)
    run = np.maximum.accumulate(np.where(np.isfinite(Bw), Bw, -np.inf), axis=1)
    trig = (M > ja[:, None]) & (ja[:, None] >= 0) & np.isfinite(Bw) & (Bw <= TRAIL * run + EPS)
    jr = first(trig)
    lb, lj = last_bid(np.full(n, LAST))
    xp_b = np.where(jr >= 0, B[np.arange(n), np.maximum(jr, 0)], lb)
    xm_b = np.where(jr >= 0, jr, lj)
    why_b = np.where(jr >= 0, 'trail', np.where(ja >= 0, 'time_armed', 'time'))
    net_b = (xp_b - ask0) * 100 - fin - np.where(xp_b > 0, fee(root, xp_b), 0.0)
    out.update(net_b=net_b, r_b=net_b / (ask0 * 100), xm_b=xm_b, why_b=why_b, xp_b=xp_b, arm_min=ja)
    # (c) one contract sold at +40%, the other trailed as (b); neither armed: both out at 3:30
    xp_c1 = np.where(ja >= 0, tgt, lb)
    net_c1 = (xp_c1 - ask0) * 100 - fin - np.where(xp_c1 > 0, fee(root, xp_c1), 0.0)
    net_c = net_c1 + net_b
    out.update(net_c=net_c, r_c=net_c / (2 * ask0 * 100))

    # ---- buy-minute context (PREREG section 4) -----------------------------------------------------------------------------------
    s_e = px[e]
    out['vwap'] = vwap[e]
    out['vwap_side'] = [None if not np.isfinite(vwap[k]) else ('with' if dirn[i] * (s_e[i] - vwap[k]) > 0 else 'against') for i, k in enumerate(e)]
    out['vwap_im'] = dirn * (s_e - vwap[e]) / strad
    out['or30_im'] = np.where(e >= 30, (or_hi - or_lo) / strad0, np.nan)
    st = []
    for i in range(n):
        if e[i] <= 30: st.append('forming'); continue
        w_ = first_with[i] <= e[i]; a_ = first_against[i] <= e[i]
        st.append('broke both' if w_ and a_ else 'broke with' if w_ else 'broke against' if a_ else 'inside')
    out['or_state'] = np.array(st)
    out['uw_gamma'] = gam[e]
    out['uw_regime'] = [None if not np.isfinite(g) else ('positive' if g > 0 else 'negative') for g in gam[e]]
    out['flip_prior'] = np.full(n, flip)
    out['flip_im'] = dirn * (s_e - flip) / strad
    ev = MACRO.get(d.isoformat(), set())
    out['event'] = np.full(n, 'FOMC' if 'FOMC' in ev else 'CPI' if 'CPI' in ev else 'NFP' if 'NFP' in ev else 'none')
    # the day (after the fact)
    out['day_open'] = np.full(n, px[1]); out['day_close'] = np.full(n, px[CLOSE])
    out['day_hi'] = np.full(n, np.nanmax(px[1:])); out['day_lo'] = np.full(n, np.nanmin(px[1:]))
    out['vix_close'] = np.full(n, vix[CLOSE]); out['hi_e'] = hi_e; out['lo_e'] = lo_e
    # the underlying every 15 minutes, for the case table
    out['px_path'] = [','.join(f'{px[m]:.2f}' for m in range(int(e[i]), LAST + 1, 15)) for i in range(n)]
    return T.drop('ci').with_columns([pl.Series(k, v) for k, v in out.items()])

# ---- the population ----------------------------------------------------------------------------------------------------------------
def population(root):
    E = pl.read_parquet(os.path.join(ROOT, 'step2', 'out', f'entries_{root}.parquet'),
                        columns=['session', 'strike', 'right', 'entry_minute', 'entry_bid', 'entry_ask', 'spot_entry', 'spot_close', 'half_day'])
    S3 = pl.read_parquet(os.path.join(ROOT, 'step3', 'out', f'features_{root}.parquet'),
                         columns=['session', 'entry_minute', 'straddle_entry', 'prior_close', 'gap', 'prior_range'])
    E = E.filter(~pl.col('half_day') & pl.col('entry_minute').is_in(ENTRY_TIMES) & (pl.col('session') <= END)
                 & ~pl.col('session').dt.strftime('%Y-%m').is_in(sorted(HELD_OUT)))
    E = E.join(S3, on=['session', 'entry_minute'], how='left')
    dirn = pl.when(pl.col('right') == 'CALL').then(1.0).otherwise(-1.0)
    E = E.with_columns((dirn * (pl.col('strike') - pl.col('spot_entry')) / pl.col('straddle_entry')).alias('x'),
                       ((pl.col('entry_ask') - pl.col('entry_bid')) / ((pl.col('entry_ask') + pl.col('entry_bid')) / 2)).alias('spread_mid'))
    E = E.filter((pl.col('x').abs() <= 1.0) & (pl.col('spread_mid') <= 0.10) & pl.col('straddle_entry').is_not_null())
    xb = pl.lit(None, pl.Int32)
    for i, (lo, hi) in enumerate(XBINS): xb = pl.when((pl.col('x') >= lo) & (pl.col('x') < hi)).then(pl.lit(i, pl.Int32)).otherwise(xb)
    E = E.with_columns(xb.alias('xbin'), pl.lit(root).alias('root'), pl.lit('SPX' if root == 'SPXW' else root).alias('product'),
                       pl.when(pl.col('session') < CHECK_FROM).then(pl.lit('pick')).otherwise(pl.lit('check')).alias('period'))
    E = E.with_columns((pl.col('entry_minute').cast(pl.Utf8) + '|' + pl.col('xbin').cast(pl.Utf8)).alias('cell'))
    # the session before in the product's own chain list: a held-out one gives no prior figures (PREREG section 1)
    days = sorted(dt.date.fromisoformat(f[:10]) for f in os.listdir(os.path.join(RAW, 'data_full', 'chains', root)) if f.endswith('.parquet'))
    prev = {b: a for a, b in zip(days[:-1], days[1:])}
    bad_prior = [d for d in set(E['session'].to_list()) if prev.get(d) is None or held_out(prev[d])]
    E = E.with_columns(*[pl.when(pl.col('session').is_in(bad_prior)).then(None).otherwise(pl.col(c)).alias(c) for c in ('prior_close', 'gap', 'prior_range')])
    return E.drop('half_day'), prev

def work(root, d, T, prior_day):
    return session(root, d, T, prior_day)

def run_product(root):
    E, prev = population(root)
    # the trading calendar for the prior session's UW flip: the session before in SPY's bar files
    cal = sorted(dt.date.fromisoformat(f[:10]) for f in os.listdir(os.path.join(RAW, 'data', 'underlying', 'SPY')) if f.endswith('.parquet'))
    cprev = {b: a for a, b in zip(cal[:-1], cal[1:])}
    parts = {d: x for (d,), x in E.group_by('session')}
    import multiprocessing as mp
    with mp.get_context('spawn').Pool(4) as pool:
        out = pool.starmap(work, [(root, d, parts[d], cprev.get(d)) for d in sorted(parts)], chunksize=4)
    R = pl.concat(out, how='vertical_relaxed').sort('session', 'entry_minute', 'right', 'strike')
    if R.height != E.height: raise SystemExit(f'{root}: {R.height} rows for {E.height} trades')
    R.write_parquet(os.path.join(WORK, f'trades_{root}.parquet'), compression='zstd', compression_level=10)
    print(root, 'sessions', len(parts), 'trades', R.height, flush=True)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        pl.Config.set_tbl_cols(80); pl.Config.set_tbl_width_chars(300)
        root, d = sys.argv[1], dt.date.fromisoformat(sys.argv[2])
        E, prev = population(root)
        cal = sorted(dt.date.fromisoformat(f[:10]) for f in os.listdir(os.path.join(RAW, 'data', 'underlying', 'SPY')) if f.endswith('.parquet'))
        cprev = {b: a for a, b in zip(cal[:-1], cal[1:])}
        x = session(root, d, E.filter(pl.col('session') == d), cprev.get(d))
        print(x.select('strike', 'right', 'entry_minute', 'entry_ask', 'x', 'peak_60', 'mult_60', 'mult_1530', 'mv_em_1530', 'dprice_1530', 'dvol_1530',
                       'dtime_1530', 'dspread_1530', 'dmid_1530', 'iv_entry', 'iv_peak_1530', 'r_a', 'why_a', 'r_b', 'why_b', 'r_c', 'or_state', 'uw_regime', 'flip_im', 'event'))
    else:
        for r in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['SPY', 'QQQ', 'IWM', 'SPXW']): run_product(r)
