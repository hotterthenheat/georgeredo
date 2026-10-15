"""Price-action atlas: descriptive statistics of the underlying that an options desk uses to choose strikes, timing and
structure. Nothing here is a trade signal and no hypothesis is tested: every figure is CALCULATED from one-minute bars,
and every one is shown for 2017-06 -> 2022-12 and 2023-01 -> 2026-10 side by side, so a reader sees whether it held.

Universe: every root with cached one-minute bars (40 Tier A roots, SPY, QQQ, IWM), 2017-06-01 -> 2026-10-09, regular
sessions with a bar in each of the 13 half-hours (A10.4), half-days left out. "Close" here is the last one-minute bar's close (15:59-16:00),
not the official close; "10:00" is the close of the 09:59 bar.

  python3 -I pa_atlas.py            # all roots -> results/price_action/
  python3 -I pa_atlas.py SPY,NVDA   # a subset
"""
import datetime as dt, glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import numpy as np, polars as pl
from engine import bars as B, calendar as cal, regime

SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
ROOTS = {**{s: f'{SP}/theta/fetch_cache/underlying' for s in os.listdir(f'{SP}/theta/fetch_cache/underlying') if s != 'FB'},
         **{s: f'{SP}/theta/data/underlying' for s in ('SPY', 'QQQ', 'IWM')}}
OUT = os.path.join(HERE, '..', 'results', 'price_action'); os.makedirs(OUT, exist_ok=True)
START, END, CUT = dt.date(2017, 6, 1), dt.date(2026, 10, 9), dt.date(2022, 12, 31)
HALF = list(range(30, 390, 30))          # 10:00 .. 15:30 as minute indices (bar closes at minute index - 1)
KS = (0.5, 1.0, 1.5, 2.0)
SPLITS = [x for k in (2, 3, 4, 5, 8, 10, 15, 20, 25, 30, 40, 50) for x in (k, 1 / k)]   # forward and reverse; no 3:2
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
EV = regime.event_days()

# The symbol META before 2022-06-09 is another security (an ETF that held the ticker first, 2021-06-30 -> 2022-01-28);
# Facebook is FB before that day (A10.3). FB's bars are used where they are cached.
SPLICE = {'META': [('FB', START, dt.date(2022, 6, 8)), ('META', dt.date(2022, 6, 9), END)]}

def load(sym):
    parts = []
    for r, a, b in SPLICE.get(sym, [(sym, START, END)]):
        root = f'{SP}/theta/fetch_cache/underlying' if r == 'FB' else ROOTS[sym]
        if os.path.isdir(os.path.join(root, r)): parts.append(B.load_minutes(r, root, a, b))
    return pl.concat(parts, how='vertical_relaxed') if parts else B.load_minutes(sym, ROOTS[sym], START, END)

def grid(sym):
    """sessions x 390 arrays of open, high, low, close, volume (NaN where a minute has no bar; closes carried forward)"""
    df = load(sym).select('session', 'minute', 'open', 'high', 'low', 'close', 'volume')
    df = df.filter((pl.col('minute') >= 0) & (pl.col('minute') < 390))
    # A10.4: a session is usable with at least one bar in each of its 13 half-hours (a minute with no trade has no bar;
    # a 385-bar floor dropped most sessions of high-priced names such as GOOGL before its split)
    n = df.group_by('session').agg((pl.col('minute') // 30).n_unique().alias('halves'))
    keep = [d for d, k in n.iter_rows() if k >= 13 and not cal.is_early_close(d)]
    df = df.filter(pl.col('session').is_in(keep)).sort('session', 'minute')
    S = sorted(keep); idx = {d: i for i, d in enumerate(S)}
    A = {c: np.full((len(S), 390), np.nan) for c in ('open', 'high', 'low', 'close', 'volume')}
    si = np.array([idx[d] for d in df['session'].to_list()]); mi = df['minute'].to_numpy()
    for c in A: A[c][si, mi] = df[c].to_numpy()
    c = A['close']
    for j in range(1, 390):                                   # carry the last close over a minute with no bar
        m = np.isnan(c[:, j]); c[m, j] = c[m, j - 1]
    for k in ('open', 'high', 'low'):
        m = np.isnan(A[k]); A[k][m] = c[m]
    A['volume'] = np.nan_to_num(A['volume'])
    return S, A

def period(d): return 'a 2017-22' if d <= CUT else 'b 2023-26'

def atlas(sym):
    S, A = grid(sym)
    if len(S) < 300: return None
    O, H, L, C, V = A['open'], A['high'], A['low'], A['close'], A['volume']
    op, cl = O[:, 0], C[:, -1]
    hi, lo = H.max(1), L.min(1)
    per = np.array([period(d) for d in S])
    prev_cl = np.r_[np.nan, cl[:-1]]; prev_hi = np.r_[np.nan, hi[:-1]]; prev_lo = np.r_[np.nan, lo[:-1]]
    consec = np.r_[False, np.array([cal.prev_session(S[i]) == S[i - 1] for i in range(1, len(S))])]
    prev_cl[~consec] = np.nan; prev_hi[~consec] = np.nan; prev_lo[~consec] = np.nan
    # the bars are unadjusted: a split shows as an overnight jump at a standard ratio. On a split session the prior day's
    # levels are unusable and its overnight return is not a return. Within 10 % of a ratio of 2:1 and beyond (A8.1's list
    # without 3:2, so a genuine one-third gap is never taken for a split; AAPL opened 2.3 % off its 4:1 ratio); every
    # detection is printed.
    ratio = op / prev_cl
    split = np.array([np.isfinite(x) and any(abs(x / f - 1) <= 0.10 for f in SPLITS) for x in ratio])
    for i in np.where(split)[0]: log(sym, 'split session', S[i], f'open/prior close {ratio[i]:.4f}')
    prev_cl[split] = np.nan; prev_hi[split] = np.nan; prev_lo[split] = np.nan
    rows = {k: [] for k in ('size', 'touch', 'path', 'levels', 'gaps', 'calendar', 'direction', 'har', 'profile')}
    p10 = C[:, 29]
    # ---- size: remaining move and excursions from each half hour to the close ----
    for m in HALF:
        p = C[:, m - 1]
        rem = np.abs(cl / p - 1)
        up = np.maximum(H[:, m:].max(1) / p - 1, 0); dn = np.maximum(1 - L[:, m:].min(1) / p, 0)
        for pr in np.unique(per):
            s = per == pr
            rows['size'].append(dict(symbol=sym, period=pr, time=f'{9 + (30 + m) // 60}:{(30 + m) % 60:02d}', sessions=int(s.sum()),
                                     rem_move_median_pct=100 * np.nanmedian(rem[s]), rem_move_p90_pct=100 * np.nanquantile(rem[s], 0.9),
                                     max_up_median_pct=100 * np.nanmedian(up[s]), max_down_median_pct=100 * np.nanmedian(dn[s]),
                                     excursion_over_end_move=np.nanmedian(np.maximum(up[s], dn[s])) / np.nanmedian(rem[s])))
    # ---- touch odds from 10:00 against the reflection principle ----
    r = np.log(cl / p10)
    sig = np.full(len(S), np.nan)
    for i in range(20, len(S)):                              # point in time: the 20 sessions before, never the day itself
        sig[i] = np.sqrt(np.nanmean(r[i - 20:i] ** 2))
    upx = np.log(H[:, 30:].max(1) / p10); dnx = np.log(L[:, 30:].min(1) / p10)
    for k in KS:
        for pr in np.unique(per):
            s = (per == pr) & np.isfinite(sig)
            tu = upx[s] >= k * sig[s]; td = dnx[s] <= -k * sig[s]; eu = r[s] >= k * sig[s]; ed = r[s] <= -k * sig[s]
            pt = (tu.mean() + td.mean()) / 2; pe = (eu.mean() + ed.mean()) / 2
            rows['touch'].append(dict(symbol=sym, period=pr, k_sigma=k, sessions=int(s.sum()), p_touch=pt, p_close_beyond=pe,
                                      touch_over_close=pt / pe if pe > 0 else np.nan,
                                      p_back_inside_given_touch=1 - ((tu & eu).mean() + (td & ed).mean()) / max(tu.mean() + td.mean(), 1e-12)))
    # ---- path and timing ----
    hmin = H.argmax(1); lmin = L.argmin(1)
    rng = hi - lo; clv = np.where(rng > 0, (cl - lo) / rng, np.nan)
    orh, orl = H[:, :30].max(1), L[:, :30].min(1)
    br_up = H[:, 30:].max(1) > orh; br_dn = L[:, 30:].min(1) < orl
    for pr in np.unique(per):
        s = per == pr
        rows['path'].append(dict(symbol=sym, period=pr, sessions=int(s.sum()),
                                 high_in_first_30m=np.mean(hmin[s] < 30), low_in_first_30m=np.mean(lmin[s] < 30),
                                 high_in_last_30m=np.mean(hmin[s] >= 360), low_in_last_30m=np.mean(lmin[s] >= 360),
                                 extreme_in_first_30m=np.mean((hmin[s] < 30) | (lmin[s] < 30)),
                                 trend_day_clv_top_or_bottom_10pct=np.nanmean((clv[s] >= 0.9) | (clv[s] <= 0.1)),
                                 clv_median=np.nanmedian(clv[s]),
                                 opening_range_broken_up=np.mean(br_up[s]), opening_range_broken_down=np.mean(br_dn[s]),
                                 opening_range_broken_both=np.mean(br_up[s] & br_dn[s]), opening_range_holds=np.mean(~br_up[s] & ~br_dn[s]),
                                 first30_range_over_day_range=np.nanmedian((orh[s] - orl[s]) / np.where(rng[s] > 0, rng[s], np.nan))))
    # ---- levels: prior day's high, low and close; VWAP ----
    tp = (H + L + C) / 3; cv = np.cumsum(V, 1); vwap = np.where(cv > 0, np.cumsum(tp * V, 1) / np.where(cv > 0, cv, 1), np.nan)
    side = np.sign(C[:, 29:] - vwap[:, 29:]); side[side == 0] = np.nan
    crosses = np.nansum(np.abs(np.diff(np.nan_to_num(side, nan=0), axis=1)) == 2, axis=1)
    same_side = np.sign(cl - vwap[:, -1]) == np.sign(p10 - vwap[:, 29])
    t_ph = (hi >= prev_hi) & (op < prev_hi); c_ph = cl > prev_hi
    t_pl = (lo <= prev_lo) & (op > prev_lo); c_pl = cl < prev_lo
    t_pc = (lo <= prev_cl) & (hi >= prev_cl)
    for pr in np.unique(per):
        s = (per == pr) & np.isfinite(prev_hi)
        rows['levels'].append(dict(symbol=sym, period=pr, sessions=int(s.sum()),
                                   prior_high_touched_from_below=np.mean(t_ph[s]), close_above_prior_high_given_touch=np.mean(c_ph[s & t_ph]) if (s & t_ph).any() else np.nan,
                                   prior_low_touched_from_above=np.mean(t_pl[s]), close_below_prior_low_given_touch=np.mean(c_pl[s & t_pl]) if (s & t_pl).any() else np.nan,
                                   prior_close_touched=np.mean(t_pc[s]),
                                   vwap_crosses_after_10_median=float(np.median(crosses[s])),
                                   close_same_vwap_side_as_10=np.nanmean(same_side[s])))
    # ---- gaps: size in units of the trailing daily move; fill = the prior close traded during the session ----
    gap = op / prev_cl - 1
    dret = np.log(cl / prev_cl)
    sd = np.full(len(S), np.nan)
    for i in range(21, len(S)): sd[i] = np.sqrt(np.nanmean(dret[i - 20:i] ** 2))
    z = gap / sd
    filled = np.where(gap > 0, lo <= prev_cl, hi >= prev_cl)
    fill_min = np.full(len(S), np.nan)
    for i in np.where(np.isfinite(gap) & (gap != 0))[0]:
        hit = (L[i] <= prev_cl[i]) if gap[i] > 0 else (H[i] >= prev_cl[i])
        if hit.any(): fill_min[i] = hit.argmax()
    for lo_z, hi_z, lab in ((0, 0.25, '0-0.25'), (0.25, 0.5, '0.25-0.5'), (0.5, 1, '0.5-1'), (1, 2, '1-2'), (2, 99, '2+')):
        for sgn, sl in ((1, 'up'), (-1, 'down')):
            for pr in np.unique(per):
                s = (per == pr) & np.isfinite(z) & (np.sign(gap) == sgn) & (np.abs(z) >= lo_z) & (np.abs(z) < hi_z)
                if s.sum() < 20: continue
                rows['gaps'].append(dict(symbol=sym, period=pr, gap=sl, size_in_daily_sd=lab, sessions=int(s.sum()), fill_rate=np.mean(filled[s]),
                                         minutes_to_fill_median=float(np.nanmedian(fill_min[s & filled])) if (s & filled).any() else np.nan,
                                         close_beyond_open_in_gap_direction=np.mean(np.sign(cl[s] - op[s]) == sgn)))
    # ---- calendar ----
    rngp = rng / op
    tags = {
        'weekday Mon': [d.weekday() == 0 for d in S], 'weekday Tue': [d.weekday() == 1 for d in S], 'weekday Wed': [d.weekday() == 2 for d in S],
        'weekday Thu': [d.weekday() == 3 for d in S], 'weekday Fri': [d.weekday() == 4 for d in S],
        'monthly opex (third Friday)': [d == cal.third_friday(d.year, d.month) for d in S],
        'FOMC day': ['FOMC' in EV.get(d, set()) for d in S], 'CPI day': ['CPI' in EV.get(d, set()) for d in S],
        'NFP day': ['NFP' in EV.get(d, set()) for d in S], 'month end': [regime.is_month_end(d) for d in S],
        'first session of month': [i > 0 and S[i - 1].month != d.month for i, d in enumerate(S)],
        'all sessions': [True] * len(S)}
    for lab, f in tags.items():
        f = np.array(f)
        for pr in np.unique(per):
            s = (per == pr) & f
            if s.sum() < 15: continue
            rows['calendar'].append(dict(symbol=sym, period=pr, cut=lab, sessions=int(s.sum()), range_median_pct=100 * np.nanmedian(rngp[s]),
                                         move_10_to_close_median_pct=100 * np.nanmedian(np.abs(cl[s] / p10[s] - 1)), gap_abs_median_pct=100 * np.nanmedian(np.abs(gap[s]))))
    # ---- direction (descriptive only) ----
    r_first = C[:, 29] / op - 1; r_last = cl / C[:, 359] - 1; r_rest = C[:, 359] / C[:, 29] - 1
    r_on = op / prev_cl - 1; r_id = cl / op - 1
    for pr in np.unique(per):
        s = per == pr; s2 = s & np.isfinite(r_on)
        cc = lambda a, b, m: float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 30 else np.nan
        rows['direction'].append(dict(symbol=sym, period=pr, sessions=int(s.sum()),
                                      corr_first30_last30=cc(r_first, r_last, s), corr_rest_of_day_last30=cc(r_rest, r_last, s),
                                      corr_overnight_intraday=cc(r_on, r_id, s2), autocorr_intraday_lag1=cc(r_id[1:], r_id[:-1], s[1:] & s[:-1]),
                                      share_up_days=float(np.mean(r_id[s] > 0)), mean_overnight_bp=1e4 * float(np.nanmean(r_on[s2])), mean_intraday_bp=1e4 * float(np.nanmean(r_id[s]))))
    # ---- how predictable the size is: HAR on the log daily range, fitted on 2017-22, scored on 2023-26 ----
    lr = np.log(np.where(rngp > 0, rngp, np.nan))
    X, y, pp = [], [], []
    for i in range(22, len(S)):
        x1, x5, x22 = lr[i - 1], np.nanmean(lr[i - 5:i]), np.nanmean(lr[i - 22:i])
        if np.isfinite([x1, x5, x22, lr[i]]).all(): X.append([1, x1, x5, x22]); y.append(lr[i]); pp.append(per[i])
    X, y, pp = np.array(X), np.array(y), np.array(pp)
    if len(y) > 300 and (pp == 'a 2017-22').sum() > 200:
        a = pp == 'a 2017-22'; b = ~a
        beta = np.linalg.lstsq(X[a], y[a], rcond=None)[0]
        r2 = lambda m: 1 - np.sum((y[m] - X[m] @ beta) ** 2) / np.sum((y[m] - y[m].mean()) ** 2)
        naive = 1 - np.sum((y[b] - X[b][:, 1]) ** 2) / np.sum((y[b] - y[b].mean()) ** 2)
        rows['har'].append(dict(symbol=sym, sessions_fit=int(a.sum()), sessions_scored=int(b.sum()), r2_in_sample=float(r2(a)), r2_out_of_sample=float(r2(b)),
                                r2_oos_yesterday_only=float(naive), b_1d=float(beta[1]), b_5d=float(beta[2]), b_22d=float(beta[3])))
    # ---- volatility by minute of day (share of the day's absolute movement) ----
    lr1 = np.abs(np.diff(np.log(C), axis=1)); tot = lr1.sum(1, keepdims=True)
    share = np.where(tot > 0, lr1 / tot, np.nan)
    for pr in np.unique(per):
        s = per == pr; prof = np.nanmean(share[s], 0)
        for j in range(0, 389, 5):
            rows['profile'].append(dict(symbol=sym, period=pr, minute_from=j + 1, time=f'{9 + (31 + j) // 60}:{(31 + j) % 60:02d}', share_of_day_5min=float(prof[j:j + 5].sum())))
    return rows

if __name__ == '__main__':
    syms = sys.argv[1].split(',') if len(sys.argv) > 1 else sorted(ROOTS)
    acc = {}
    for sym in syms:
        try: r = atlas(sym)
        except Exception as e: log(sym, 'failed', type(e).__name__, str(e)[:200]); continue
        if r is None: log(sym, 'too few sessions'); continue
        for k, v in r.items(): acc.setdefault(k, []).extend(v)
        log(sym, 'done', {k: len(v) for k, v in r.items()})
    for k, v in acc.items():
        if v: pl.DataFrame(v, infer_schema_length=None).write_csv(os.path.join(OUT, f'{k}.csv'), float_precision=5)
    log('wrote', OUT)
