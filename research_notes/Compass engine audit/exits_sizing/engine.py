"""Compass Modules 3/4 audit: the exit engine, replayed on the stored minute paths (extract.py).

Conventions. Minute m = 0 is 09:30. A trade is bought at the ask at its entry minute e; every exit is judged on the
BID at each minute m > e (one-minute NBBO: intra-minute ticks are not observed). A stop, trail, time stop or hard flat
sells at that minute's bid (so a bid that gaps through a stop sells at the gapped bid). A target sells at the target
price exactly (a resting limit order; the bid at that minute is at or above it). Hard flat at 15:58 (m = 388; 208 on a
half day) at the bid; if no bid is quoted there, the last bid quoted before it; a contract whose exit bid is 0 is held
to settlement. Fees: $0.65 a contract each way; none on a contract held to settlement.
Partial exits: legs of whole contracts, each leg with its own target (or none: trailed/held); every leg shares the
stops. Per-contract $ and % figures are weighted by contracts.
"""
import os, numpy as np, polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
FEE = 0.65
NMIN = 391
PRODUCTS = ['SPY', 'QQQ', 'IWM', 'SPXW']
SPLIT = '2025-01-01'
VIX_TIERS = [(15.0, 0.06), (20.0, 0.08), (30.0, 0.11), (np.inf, 0.14)]

class Paths:
    pass

def load(products=PRODUCTS, universe=None):
    frames = []
    for p in products:
        f = os.path.join(OUT, f'paths_{p}.parquet')
        if os.path.exists(f): frames.append(pl.read_parquet(f))
    df = pl.concat(frames, how='vertical_relaxed')
    if universe: df = df.filter(pl.col('universe') == universe)
    df = df.filter(pl.col('quotes_after') >= 5).sort('product', 'session', 'universe', 'entry_m')
    P = Paths()
    P.df = df.drop('bid', 'ask', 'bid_size', 'ask_size', 'spot', 'bar_high', 'bar_low')
    arr = lambda c: np.array(df[c].to_list(), dtype=np.float64)
    P.B, P.A, P.BS, P.AS, P.S, P.BH, P.BL = (arr(c) for c in ('bid', 'ask', 'bid_size', 'ask_size', 'spot', 'bar_high', 'bar_low'))
    P.B = np.round(P.B, 4); P.A = np.round(P.A, 4)      # stored as float32 (quotes are in cents): 1.05 read back as 1.04999995 and missed a 1.05 threshold
    P.n = df.height
    P.e = df['entry_m'].to_numpy().astype(int); P.ask0 = df['entry_ask'].to_numpy(); P.close_m = df['close_m'].to_numpy().astype(int)
    P.settle = df['settle'].to_numpy(); P.put = (df['side'] == 'PUT').to_numpy(); P.level = df['level'].to_numpy(); P.spot0 = df['spot_entry'].to_numpy()
    P.vix = df['vix'].to_numpy(); P.uni = df['universe'].to_numpy(); P.session = df['session'].to_numpy(); P.product = df['product'].to_numpy()
    P.hf = np.where(P.close_m == 390, 388, 208)
    M = np.arange(NMIN)[None, :]
    P.after = (M > P.e[:, None]) & (M <= P.close_m[:, None])        # minutes a sale can happen
    P.M = M
    # the bid path with NaN outside the window; the running peak of the bid since entry (through each minute)
    B = np.where(P.after, P.B, np.nan)
    P.Bw = B
    P.peak = np.fmax.accumulate(np.where(np.isnan(B), -np.inf, B), axis=1)
    P.peak[~np.isfinite(P.peak)] = np.nan
    P.peak_prior = np.concatenate([np.full((P.n, 1), np.nan), P.peak[:, :-1]], axis=1)   # the peak through m-1
    P.is_check = (df['session'] >= SPLIT).to_numpy()
    P.year = df['session'].str.slice(0, 4).to_numpy()
    return P

def first_true(mask):
    """index of the first True per row, -1 where none"""
    any_ = mask.any(axis=1); idx = mask.argmax(axis=1); idx[~any_] = -1; return idx

def structural_minute(P, buffer_bps=0.0, b_bps=None):
    """first quote minute at which the underlying has traded back through the level (+ buffer), judged on bar high/low.
    Universe A: the swept level; universe B: entry spot moved b_bps against the trade. The bar stamped m' closes at m'+1."""
    lvl = P.level.copy()
    if b_bps is not None:
        lvl = np.where(P.uni == 'B', np.where(P.put, P.spot0 * (1 + b_bps / 1e4), P.spot0 * (1 - b_bps / 1e4)), lvl)
    up = lvl * (1 + buffer_bps / 1e4); dn = lvl * (1 - buffer_bps / 1e4)
    bar_ok = (P.M >= P.e[:, None]) & (P.M + 1 <= P.close_m[:, None])     # bars that close after entry
    hit = np.where(P.put[:, None], P.BH >= up[:, None], P.BL <= dn[:, None]) & bar_ok & ~np.isnan(lvl)[:, None]
    i = first_true(hit)
    return np.where(i >= 0, i + 1, -1)

def trail_frac(P, trail):
    if trail == 'vix':
        t = np.full(P.n, np.nan)
        for hi, f in VIX_TIERS[::-1]: t[P.vix < hi] = f
        t[np.isnan(P.vix)] = 0.11
        return t
    return np.full(P.n, float(trail))

def simulate(P, prem_stop=0.68, struct_buffer=None, b_bps=None, be_lock=None, trail=None, trail_act=0.06, time_stop=None, time_prog=0.06,
             time_prog_spot_bps=None, targets=((1, None),), hard_flat=True, target_fill='limit'):
    """Returns dict with per-contract pnl ($), pct (of debit), exit_m per leg, reason per leg, contracts."""
    n = P.n; ask0 = P.ask0[:, None]; B = P.Bw
    cand = []   # (minute index array, price array, reason)
    if prem_stop is not None:
        i = first_true(B <= prem_stop * ask0 + 1e-9); cand.append((i, 'prem_stop'))
    if struct_buffer is not None:
        i = structural_minute(P, struct_buffer, b_bps); cand.append((i, 'struct'))
    if be_lock is not None:
        lock_m = first_true(P.peak >= (1 + be_lock) * ask0 - 1e-9)
        m_after = P.M > lock_m[:, None]
        i = first_true((B <= ask0 + 1e-9) & m_after & (lock_m >= 0)[:, None]); cand.append((i, 'be_lock'))
    if trail is not None:
        t = trail_frac(P, trail)[:, None]
        active = P.peak_prior >= (1 + trail_act) * ask0 - 1e-9 if trail_act is not None else ~np.isnan(P.peak_prior)
        i = first_true((B <= (1 - t) * P.peak_prior + 1e-9) & active); cand.append((i, 'trail'))
    if time_stop is not None:
        tm = P.e + time_stop
        ok = tm <= P.close_m
        prog = P.peak[np.arange(n), np.minimum(tm, NMIN - 1)] >= (1 + time_prog) * P.ask0 - 1e-9
        if time_prog_spot_bps is not None:   # 'structural progress': the underlying moved in the trade's favour by this much at any minute by e+T
            S = np.where((P.M > P.e[:, None]) & (P.M <= tm[:, None]), P.S, np.nan)
            fav = np.where(P.put[:, None], S <= (P.spot0 * (1 - time_prog_spot_bps / 1e4))[:, None], S >= (P.spot0 * (1 + time_prog_spot_bps / 1e4))[:, None])
            prog = prog | fav.any(axis=1)
        i = np.where(ok & ~prog, tm, -1); cand.append((i, 'time'))
    if hard_flat:
        cand.append((P.hf.copy(), 'flat'))
    # common exit: the earliest candidate
    common_m = np.full(n, NMIN + 5); common_r = np.full(n, 'settle', dtype=object)
    for i, r in cand:
        better = (i >= 0) & (i < common_m)
        common_m[better] = i[better]; common_r[better] = r
    rows = np.arange(n)
    def bid_at(m):
        """the bid at minute m, or the last quoted bid before it inside the window"""
        mm = np.minimum(m, NMIN - 1)
        b = B[rows, mm]
        miss = np.isnan(b)
        if miss.any():
            Bf = B.copy()
            # forward-fill within row
            idx = np.where(~np.isnan(Bf), np.arange(NMIN)[None, :], 0); idx = np.maximum.accumulate(idx, axis=1)
            Bf = Bf[rows[:, None], idx]; b2 = Bf[rows, mm]
            b = np.where(miss, b2, b)
        return b
    total_c = sum(c for c, _ in targets)
    pnl = np.zeros(n); legs = []
    for c, tgt in targets:
        if tgt is None:
            m = common_m; r = common_r.copy()
        else:
            ti = first_true(B >= tgt * ask0 - 1e-9)
            hit = (ti >= 0) & (ti <= common_m)
            m = np.where(hit, ti, common_m); r = np.where(hit, 'target', common_r)
        sold = m < NMIN
        px = np.where(sold, bid_at(np.where(sold, m, 0)), np.nan)
        if tgt is not None:
            px = np.where(r == 'target', tgt * P.ask0 if target_fill == 'limit' else px, px)
        px = np.where(np.isnan(px), 0.0, px)
        sold = sold & (px > 0)
        exit_px = np.where(sold, px, P.settle)
        leg_pnl = (exit_px - P.ask0) * 100 - FEE - np.where(sold, FEE, 0.0)
        r = np.where(sold, r, 'settle')
        pnl += c * leg_pnl
        legs.append(dict(contracts=c, exit_m=np.where(sold, m, P.close_m), reason=r, price=exit_px, pnl=leg_pnl))
    pnl /= total_c
    return dict(pnl=pnl, pct=pnl / (P.ask0 * 100), legs=legs, common_m=common_m, common_r=common_r)

def stats(P, res, mask=None):
    mask = np.ones(P.n, bool) if mask is None else mask
    pct = res['pct'][mask]; pnl = res['pnl'][mask]
    if len(pct) == 0: return dict(n=0)
    win = pnl > 0
    return dict(n=int(len(pct)), ev_pct=float(pct.mean()), ev_usd=float(pnl.mean()), win_rate=float(win.mean()),
                avg_win_pct=float(pct[win].mean()) if win.any() else np.nan, avg_loss_pct=float(pct[~win].mean()) if (~win).any() else np.nan,
                total_usd=float(pnl.sum()), median_pct=float(np.median(pct)))

def stress(P, res, mask, seed=7, nboot=1000):
    """bootstrap by session, without the best 5 sessions, by year; on the masked trades"""
    pct = res['pct'][mask]; sess = P.session[mask]; yr = P.year[mask]
    if len(pct) == 0: return {}
    days = np.unique(sess); by_day = {d: pct[sess == d] for d in days}
    day_sum = np.array([by_day[d].sum() for d in days]); day_n = np.array([len(by_day[d]) for d in days])
    rng = np.random.default_rng(seed); means = []
    for _ in range(nboot):
        k = rng.integers(0, len(days), len(days)); means.append(day_sum[k].sum() / day_n[k].sum())
    lo, hi = np.percentile(means, [2.5, 97.5])
    top5 = np.argsort(day_sum)[-5:]; keep = np.ones(len(days), bool); keep[top5] = False
    wo5 = day_sum[keep].sum() / day_n[keep].sum() if day_n[keep].sum() else np.nan
    out = dict(boot_lo=float(lo), boot_hi=float(hi), without_best5=float(wo5), days=int(len(days)), days_up=int((day_sum > 0).sum()),
               best5_share=float(day_sum[top5].sum() / pct.sum()) if pct.sum() != 0 else np.nan)
    for y in sorted(set(yr)): out[f'y{y}'] = float(pct[yr == y].mean())
    return out

def row(name, P, res, extra=None):
    d = dict(rule=name)
    for lab, mk in (('disc', ~P.is_check), ('check', P.is_check)):
        s = stats(P, res, mk); d.update({f'{k}_{lab}': v for k, v in s.items()})
    if extra: d.update(extra)
    return d
