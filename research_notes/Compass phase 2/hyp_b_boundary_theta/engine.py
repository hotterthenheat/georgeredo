"""Compass Phase 2, Hypothesis B: short defined-risk 0DTE credit spreads at the straddle boundary and in the midday window.
One pass over each full session of a product; writes out/trades_<PRODUCT>.parquet (rebuildable from the raw chains and
the audit's event tables) and out/log_<PRODUCT>.txt.

    nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I engine.py SPXW [first_date] [last_date]

EVENTS ARE THE AUDIT'S, READ FROM ITS TABLES (never rebuilt here, never edited):
  AUDIT/out/scans_<P>.parquet  : at each scan minute s in SCANS the spot and the ATM straddle mid (M = straddle).
  AUDIT/out/touches_<P>.parquet: for each scan x multiplier (1.0, 1.2533) x side the FIRST minute t > s at which the spot
                                 reaches spot_scan +/- M ("upper_1" = up side, "lower_1" = down side), and px_t.
  AUDIT/out/daily_<SYM>.parquet: prior_close and Wilder atr14; move_atr = (px_event - prior_close) / atr14 lagged one session
                                 (analyze_atr.py's definition; this test uses |move_atr|).
Conventions, the audit's: minute m = 0 is 09:30; an ETF bar stamped t closes at t+1, so the spot at m is the close of the bar
stamped m-1; an SPX print stamped m is the price at m; a chain row stamped m is the NBBO at m; the close is minute 390;
half days are skipped (the touch/scan tables hold none).

STRUCTURES. Vertical credit spreads: at an UP touch a call spread (short K_s, long K_s + width); at a DOWN touch a put spread
(short K_s, long K_s - width); iron condor = both. Widths: SPXW 5 and 10 points, SPY 1 and 2.
Short-strike rules (the rows' `rule`):
  touch   : 'at'      the first listed strike at or beyond the touch price (>= px_t for a call, <= px_t for a put)
            'half'    the first strike at or beyond px_t +/- 0.5 x the REMAINING ATM straddle at t (the mid straddle of the
                      strike nearest px_t with both sides quoted at t)
            'd15','d20','d25'  the OTM strike whose BSM |delta| is nearest 0.15 / 0.20 / 0.25 (r = q = 0, the vol implied by
                      the option's mid at the entry minute, tau = minutes to 16:00; only sigma*sqrt(tau) enters delta)
  scheduled (every full session at every scan minute, the baselines and the midday test):
            'd10','d15','d20','d25'  as above
            'em1'     the first strike outside spot +/- 1.0 x the ATM straddle at the scan (the band's own edge)
            'em1p'    the first strike outside spot +/- 1.2533 x the straddle
            'half'    the first strike outside spot +/- 0.5 x the straddle
FILLS: a short leg sold at its bid, a long leg bought at its ask, at the entry minute's NBBO; credit >= $0.05 a spread or no
trade; $0.65 a leg each way; a closing trade pays the fee on every leg closed; at expiry a worthless leg pays nothing and an
ITM leg settles at intrinsic with no fee assumed: SPXW cash-settled on the LAST SPX PRINT AT OR BEFORE 16:00 as a proxy for
the official SET (the official settlement is not on disk); SPY on the close of the bar stamped 16:00 (the closing auction
print; the last bar's close when there is none), no assignment fee assumed.
MANAGEMENT (every row carries all four): hold to settlement; buy back at <= 50% of the credit (tp); stop at >= 2x the credit
(stop); both (the earlier). Exits are checked at the NBBO of every minute from e+1 to 389 (cost to close = the short's ask
minus the long's bid; a minute where either side is unquoted cannot exit). An iron condor is managed as one position
(its total credit).
"""
import datetime as dt, math, os, sys, time
import numpy as np, polars as pl

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
AUDIT = '/home/user/georgeredo/research_notes/Compass engine audit/move_atr_flow/out'
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
UNDERLYING = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
DAILY = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
WIDTHS = {'SPXW': [5.0, 10.0], 'SPY': [1.0, 2.0], 'QQQ': [1.0, 2.0], 'IWM': [1.0, 2.0]}
SCANS = [5, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360, 380]
FEE = 0.65; CLOSE_M = 390; LAST_EXIT = 389; LAST_ENTRY = 388; MIN_CREDIT = 0.05; TP = 0.5; STOP = 2.0
SQRT_HALF_PI = 1.2533141
TOUCH_RULES = ['at', 'half', 'd15', 'd20', 'd25']
SCHED_RULES = ['d10', 'd15', 'd20', 'd25', 'em1', 'em1p', 'half']
DELTA_OF = {'d10': 0.10, 'd15': 0.15, 'd20': 0.20, 'd25': 0.25}

def minute_of(col):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

_erf = np.vectorize(math.erf, otypes=[np.float64])

def _ncdf(x):
    """the standard normal cdf, vectorised through math.erf (no scipy needed)"""
    return 0.5 * (1.0 + _erf(x / np.sqrt(2.0)))

def bsm_total_var(S, K, price, is_call):
    """Solve v = sigma*sqrt(tau) from a European price with r = q = 0 by bisection (vectorised); returns v and |delta|."""
    S = np.asarray(S, float); K = np.asarray(K, float); price = np.asarray(price, float)
    lo = np.full(K.shape, 1e-5); hi = np.full(K.shape, 5.0)
    lnm = np.log(S / K)
    def call_px(v):
        d1 = (lnm + 0.5 * v * v) / v; d2 = d1 - v
        return S * _ncdf(d1) - K * _ncdf(d2)
    target = price if is_call else price + S - K       # put-call parity at r = q = 0: C = P + S - K
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        above = call_px(mid) > target
        hi = np.where(above, mid, hi); lo = np.where(above, lo, mid)
    v = 0.5 * (lo + hi)
    d1 = (lnm + 0.5 * v * v) / v
    delta = _ncdf(d1) if is_call else 1.0 - _ncdf(d1)
    return v, delta

class Session:
    def __init__(self, root, d):
        self.root = root; self.d = d; u = UNDERLYING[root]
        spy = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet'), columns=['timestamp', 'close']).filter(pl.col('close').is_not_null())
        if spy['timestamp'].max().hour < 15: raise ValueError('half day')
        if u == 'SPX':
            p = pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).rename({'price': 'px'}).with_columns(minute_of('timestamp').alias('m'))
            p = p.filter(pl.col('px').is_not_null() & (pl.col('m') >= 0) & (pl.col('m') <= CLOSE_M)).sort('m')
            self.settle = float(p['px'][-1])            # the last SPX print at or before 16:00: the SET proxy
            self.settle_note = 'last SPX print <= 16:00'
        else:
            b = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', u, f'{d}.parquet'), columns=['timestamp', 'close']).with_columns(minute_of('timestamp').alias('j'))
            b = b.filter(pl.col('close').is_not_null() & (pl.col('j') >= 0) & (pl.col('j') <= CLOSE_M)).sort('j')
            self.settle = float(b['close'][-1])          # the bar stamped 16:00 (closing auction) when present
            self.settle_note = 'close of the last bar <= 16:00'
            p = b.filter(pl.col('j') < CLOSE_M).select(pl.col('close').alias('px'), (pl.col('j') + 1).alias('m'))
        if p.height < 300: raise ValueError('no spot')
        self.px = dict(zip(p['m'].to_list(), p['px'].to_list()))
        # ---- the chain as arrays [strike index, minute]
        c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask']).with_columns(minute_of('timestamp').alias('m'))
        two = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0)
        q = c.filter(two & (pl.col('m') >= 1) & (pl.col('m') <= CLOSE_M))
        self.strikes = np.array(sorted(q['strike'].unique().to_list()), float)
        nK = len(self.strikes); self.B = {}; self.A = {}
        for r in ('CALL', 'PUT'):
            sub = q.filter(pl.col('right') == r)
            B = np.full((nK, CLOSE_M + 1), np.nan); A = np.full((nK, CLOSE_M + 1), np.nan)
            si = np.searchsorted(self.strikes, sub['strike'].to_numpy()); mi = sub['m'].to_numpy()
            B[si, mi] = sub['bid'].to_numpy(); A[si, mi] = sub['ask'].to_numpy()
            self.B[r] = B; self.A[r] = A
        self.kidx = {float(k): i for i, k in enumerate(self.strikes)}
        self._delta_cache = {}
        # ---- VIX at each minute (the last print at or before m)
        self.vix = None
        fv = os.path.join(RAW, 'data', 'index', 'VIX', f'{d}.parquet')
        if os.path.exists(fv):
            v = pl.read_parquet(fv).with_columns(minute_of('timestamp').alias('m')).filter(pl.col('price').is_not_null()).sort('m')
            self.vix = (v['m'].to_numpy(), v['price'].to_numpy())

    def vix_at(self, m):
        if self.vix is None: return None
        ms, ps = self.vix; i = np.searchsorted(ms, m, side='right') - 1
        return float(ps[i]) if i >= 0 else None

    def straddle_at(self, m, S):
        """The ATM straddle mid at minute m: the strike nearest S with both sides quoted (ask > 0), as the audit's scans."""
        cb, ca, pb, pa = self.B['CALL'][:, m], self.A['CALL'][:, m], self.B['PUT'][:, m], self.A['PUT'][:, m]
        ok = np.isfinite(cb) & np.isfinite(pb) & (ca > 0) & (pa > 0)
        if not ok.any(): return None
        i = np.flatnonzero(ok); j = i[np.lexsort((self.strikes[i], np.abs(self.strikes[i] - S)))[0]]
        return float((cb[j] + ca[j]) / 2 + (pb[j] + pa[j]) / 2)

    def deltas(self, m, S):
        """|delta| by strike for OTM calls (K > S) and puts (K < S) at minute m, from each option's mid."""
        if m in self._delta_cache: return self._delta_cache[m]
        out = {}
        for r in ('CALL', 'PUT'):
            b, a = self.B[r][:, m], self.A[r][:, m]
            mid = (b + a) / 2
            otm = (self.strikes > S) if r == 'CALL' else (self.strikes < S)
            ok = otm & np.isfinite(mid) & (mid > 0) & (a > 0)
            if r == 'CALL': ok &= mid < S
            else: ok &= mid < self.strikes
            idx = np.flatnonzero(ok); dl = {}
            if len(idx):
                v, de = bsm_total_var(S, self.strikes[idx], mid[idx], r == 'CALL')
                for i, dd in zip(idx, de): dl[float(self.strikes[i])] = float(dd)
            out[r] = dl
        self._delta_cache[m] = out
        return out

    def first_beyond(self, level, side):
        """the first listed strike >= level (side 'call') or <= level (side 'put')"""
        if side == 'call':
            i = np.searchsorted(self.strikes, level - 1e-9, side='left')
            return float(self.strikes[i]) if i < len(self.strikes) else None
        i = np.searchsorted(self.strikes, level + 1e-9, side='right') - 1
        return float(self.strikes[i]) if i >= 0 else None

    def nearest_delta(self, m, S, side, target):
        dl = self.deltas(m, S)['CALL' if side == 'call' else 'PUT']
        if not dl: return None
        ks = np.array(list(dl.keys())); ds = np.array(list(dl.values()))
        j = np.lexsort((-ks if side == 'call' else ks, np.abs(ds - target)))[0]   # ties: the nearer-the-money strike
        return float(ks[j])

    def short_delta(self, m, S, side, K):
        return self.deltas(m, S)['CALL' if side == 'call' else 'PUT'].get(K)

    def leg_paths(self, side, Ks, Kl, e):
        """credit at e and the cost-to-close path (minutes e+1..LAST_EXIT) of a vertical: short Ks, long Kl."""
        r = 'CALL' if side == 'call' else 'PUT'
        if Ks not in self.kidx or Kl not in self.kidx: return None
        s, l = self.kidx[Ks], self.kidx[Kl]
        bs, al = self.B[r][s, e], self.A[r][l, e]
        if not (np.isfinite(bs) and np.isfinite(al)) or bs <= 0 or al <= 0: return None
        credit = bs - al
        self._other = (float(self.A[r][s, e]), float(self.B[r][l, e]))   # the legs' other sides, for the mid-price decomposition
        cost = self.A[r][s, e + 1:LAST_EXIT + 1] - self.B[r][l, e + 1:LAST_EXIT + 1]
        return credit, cost, float(bs), float(al)

    def intrinsic(self, side, K):
        return max(0.0, self.settle - K) if side == 'call' else max(0.0, K - self.settle)

def manage(credit, cost, e, settle_val, n_legs):
    """P&L in $ a spread under the four managements. cost: the cost-to-close path from e+1; NaN = cannot exit that minute."""
    fee_in = FEE * n_legs; fee_out = FEE * n_legs
    tp_hit = np.flatnonzero(np.isfinite(cost) & (cost <= TP * credit)); st_hit = np.flatnonzero(np.isfinite(cost) & (cost >= STOP * credit))
    tp_m = int(e + 1 + tp_hit[0]) if len(tp_hit) else None; st_m = int(e + 1 + st_hit[0]) if len(st_hit) else None
    hold = (credit - settle_val) * 100 - fee_in
    def at(mm): return (credit - cost[mm - e - 1]) * 100 - fee_in - fee_out
    o = dict(pnl_hold=hold, tp_m=tp_m, stop_m=st_m)
    o['pnl_tp'] = at(tp_m) if tp_m else hold
    o['pnl_stop'] = at(st_m) if st_m else hold
    if tp_m and st_m: both = min(tp_m, st_m)
    else: both = tp_m or st_m
    o['pnl_both'] = at(both) if both else hold
    o['exit_both_m'] = both
    return o

def vertical(ss, side, Ks, width, e, S, extra):
    Kl = Ks + width if side == 'call' else Ks - width
    lp = ss.leg_paths(side, Ks, Kl, e)
    if lp is None: return None
    credit, cost, bs, al = lp
    if credit < MIN_CREDIT: return None
    settle_val = ss.intrinsic(side, Ks) - ss.intrinsic(side, Kl)
    o = dict(session=str(ss.d), structure=side, width=width, e=e, spot_e=S, short_k=Ks, long_k=Kl, short_bid=bs, long_ask=al, short_ask=ss._other[0], long_bid=ss._other[1], credit=credit,
             max_risk=(width - credit) * 100, settle=ss.settle, settle_val=settle_val, short_delta=ss.short_delta(e, S, side, Ks), **extra)
    o.update(manage(credit, cost, e, settle_val, 2))
    o['full_loss_hold'] = settle_val >= width - 1e-9
    return o, (credit, cost, settle_val)

def condor(ss, cp, pp, width, e, S, extra):
    """cp, pp: the (credit, cost, settle_val) tuples of the call and put spreads; managed as one position."""
    credit = cp[0] + pp[0]; cost = cp[1] + pp[1]; sv = cp[2] + pp[2]
    o = dict(session=str(ss.d), structure='condor', width=width, e=e, spot_e=S, credit=credit, max_risk=(width - credit) * 100, settle=ss.settle, settle_val=sv, **extra)
    o.update(manage(credit, cost, e, sv, 4))
    o['full_loss_hold'] = sv >= width - 1e-9
    return o

def run(root, first=None, last=None):
    T = pl.read_parquet(os.path.join(AUDIT, f'touches_{root}.parquet')).select('session', 'm_scan', 'mult', 'side', 'spot_scan', 'M', 't', 'px_t')
    Sc = pl.read_parquet(os.path.join(AUDIT, f'scans_{root}.parquet')).select('session', 'm_scan', 'spot', 'straddle')
    D = pl.read_parquet(os.path.join(AUDIT, f'daily_{DAILY[root]}.parquet')).select('date', 'prior_close', pl.col('atr14').shift(1).alias('atr_prev'))
    daily = {r['date']: (r['prior_close'], r['atr_prev']) for r in D.iter_rows(named=True)}
    sessions = sorted(set(Sc['session'].to_list()))
    if first: sessions = [x for x in sessions if x >= first]
    if last: sessions = [x for x in sessions if x <= last]
    widths = WIDTHS[root]
    parts = []; t0 = time.time(); n = 0; skipped = []; counts = dict(touch_rows=0, touch_taken=0, sched_rows=0, sched_taken=0)
    for d in sessions:
        try:
            ss = Session(root, dt.date.fromisoformat(d))
        except Exception as ex:
            skipped.append((d, repr(ex)[:120])); continue
        pc, atr = daily.get(d, (None, None))
        rows = []
        # ---- touches: the audit's events
        for ev in T.filter(pl.col('session') == d).iter_rows(named=True):
            t = int(ev['t'])
            if t > LAST_ENTRY or t not in ss.px: continue
            S = ss.px[t]; side = 'call' if ev['side'] == 'up' else 'put'
            strad_t = ss.straddle_at(t, S)
            base = dict(test='touch', m_scan=int(ev['m_scan']), mult=float(ev['mult']), touch_side=ev['side'], spot_scan=ev['spot_scan'], M=ev['M'], px_t=ev['px_t'],
                        straddle_e=strad_t, vix_e=ss.vix_at(t), move_atr=((ev['px_t'] - pc) / atr if (pc is not None and atr is not None and atr > 0) else None))
            for rule in TOUCH_RULES:
                if rule == 'at': Ks = ss.first_beyond(ev['px_t'], side)
                elif rule == 'half': Ks = ss.first_beyond(ev['px_t'] + (0.5 * strad_t if side == 'call' else -0.5 * strad_t), side) if strad_t else None
                else: Ks = ss.nearest_delta(t, S, side, DELTA_OF[rule])
                if Ks is None: continue
                for w in widths:
                    counts['touch_rows'] += 1
                    r = vertical(ss, side, Ks, w, t, S, dict(base, rule=rule))
                    if r: rows.append(r[0]); counts['touch_taken'] += 1
        # ---- scheduled sells at every scan minute: the baselines and the midday test
        for sc in Sc.filter(pl.col('session') == d).iter_rows(named=True):
            s = int(sc['m_scan'])
            if s > LAST_ENTRY or s not in ss.px: continue
            S = ss.px[s]; strad = sc['straddle']
            base = dict(test='sched', m_scan=s, mult=None, touch_side=None, spot_scan=sc['spot'], M=strad, px_t=None, straddle_e=strad, vix_e=ss.vix_at(s),
                        move_atr=((S - pc) / atr if (pc is not None and atr is not None and atr > 0) else None))
            for rule in SCHED_RULES:
                for w in widths:
                    legs = {}
                    for side in ('call', 'put'):
                        sg = 1 if side == 'call' else -1
                        if rule in DELTA_OF: Ks = ss.nearest_delta(s, S, side, DELTA_OF[rule])
                        elif rule == 'em1': Ks = ss.first_beyond(S + sg * strad, side)
                        elif rule == 'em1p': Ks = ss.first_beyond(S + sg * SQRT_HALF_PI * strad, side)
                        else: Ks = ss.first_beyond(S + sg * 0.5 * strad, side)
                        if Ks is None: continue
                        counts['sched_rows'] += 1
                        r = vertical(ss, side, Ks, w, s, S, dict(base, rule=rule))
                        if r: rows.append(r[0]); legs[side] = r[1]; counts['sched_taken'] += 1
                    if 'call' in legs and 'put' in legs:
                        rows.append(condor(ss, legs['call'], legs['put'], w, s, S, dict(base, rule=rule, short_k=None, long_k=None, short_bid=None, long_ask=None, short_ask=None, long_bid=None, short_delta=None)))
        if rows: parts.append(pl.DataFrame(rows, infer_schema_length=None))
        n += 1
        if n % 100 == 0: print(root, d, n, f'{time.time() - t0:.0f}s', len(rows), flush=True)
    if parts:
        X = pl.concat(parts, how='diagonal_relaxed')
        X.write_parquet(os.path.join(OUT, f"{os.environ.get('OUTNAME', 'trades')}_{root}.parquet"), compression='zstd')
        print(root, 'rows', X.height, flush=True)
    msg = f'{root} sessions {n} skipped {len(skipped)} {time.time() - t0:.0f}s {counts} settle={ss.settle_note} fees={FEE}/leg/way min_credit={MIN_CREDIT} tp={TP} stop={STOP}'
    print(msg)
    with open(os.path.join(OUT, f'log_{root}.txt'), 'w') as fh:
        fh.write(msg + '\n')
        for d, why in skipped: fh.write(f'{d}\t{why}\n')

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, sys.argv[3] if len(sys.argv) > 3 else None)
