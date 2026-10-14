"""SPXW same-day short-premium simulator at measured NBBO (PREREGISTRATION.md, Part G and T-E).

One session -> one frame of trade rows: every entry label (10:00, 11:00, 13:00, 14:05 and the five random-entry draws R1..R5)
x 8 structure-k cells x 3 take-profits x 3 stops x 3 exits (E0 diagnostic, E1, E2), plus skip rows.  Winged cells are computed
with zero-bid wings allowed and flagged (`wing_bid0`); the pre-registered (literal) rule drops the flagged rows (analysis step).
All money in $ per 1-lot (multiplier 100).  No look-ahead: spot and quotes are the rows stamped at the entry minute; management
uses rows stamped after entry; settlement uses the SPX price stamped 16:00.
"""
import os, sys, csv
import numpy as np, polars as pl

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'research', 'thetadata', 'dataset'))
import load as L  # noqa: E402

FEE = 1.00            # $ per contract per side
LEAVE = 0.10          # E1: legs with ask <= $0.10 are left to settle
ENTRIES = ['10:00', '11:00', '13:00', '14:05']
KS = [0.0, 0.5, 1.0, 1.5]
TPS = [0.0, 0.25, 0.5]   # 0 = none
STOPS = [0.0, 1.0, 2.0]  # 0 = none; s = credit-loss multiple
NMIN = 391               # 09:30 .. 16:00
I1554, I1555, I1600 = 384, 385, 390
EPS = 1e-9
EVENTS_CSV = os.path.join(REPO, 'research', 'thetadata', 'vol_filters', 'events.csv')
RANDOM_CSV = os.path.join(HERE, 'random_minutes.csv')


def hm2i(hm):
    return int(hm[:2]) * 60 + int(hm[3:5]) - 570


def i2hm(i):
    m = i + 570
    return f'{m // 60:02d}:{m % 60:02d}'


def regular_sessions(start='2022-05-13', end='2026-10-09'):
    early = {r['date'] for r in csv.DictReader(open(L.CALENDAR)) if r['type'] == 'early_close'}
    return [d for d in L.trading_sessions(start, end) if d not in early]


def write_random_minutes():
    """Seeds 11-15: one entry minute per regular session (sorted), uniform on 10:00-14:30 inclusive."""
    ses = regular_sessions()
    rows = []
    for draw, seed in enumerate(range(11, 16), start=1):
        rng = np.random.default_rng(seed)
        mins = rng.integers(600, 871, size=len(ses))  # minutes after midnight: 600 = 10:00, 870 = 14:30
        rows += [dict(date=d, draw=draw, seed=seed, minute=f'{m // 60:02d}:{m % 60:02d}') for d, m in zip(ses, mins)]
    with open(RANDOM_CSV, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['date', 'draw', 'seed', 'minute']); w.writeheader(); w.writerows(rows)


def random_minutes():
    out = {}
    for r in csv.DictReader(open(RANDOM_CSV)):
        out[(r['date'], int(r['draw']))] = r['minute']
    return out


class Session:
    """Minute x strike arrays for one SPXW session (call = 0, put = 1)."""

    def __init__(self, date):
        self.date = date
        c = L.chain('SPXW', date)
        c = c.with_columns(((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32)) - 570).alias('i'))
        c = c.filter((pl.col('i') >= 0) & (pl.col('i') < NMIN))
        self.K = np.array(sorted(c['strike'].unique().to_list()), float)
        kidx = {k: j for j, k in enumerate(self.K)}
        nK = len(self.K)
        bid = np.full((2, NMIN, nK), np.nan); ask = np.full((2, NMIN, nK), np.nan)
        r = (c['right'] == 'PUT').cast(pl.Int8).to_numpy()
        ii = c['i'].to_numpy(); jj = np.array([kidx[k] for k in c['strike'].to_list()])
        b = c['bid'].to_numpy().astype(float); a = c['ask'].to_numpy().astype(float)  # nulls -> nan
        bid[r, ii, jj] = b; ask[r, ii, jj] = a
        usable = np.isfinite(bid) & np.isfinite(ask) & (ask > 0) & (ask >= bid)
        self.usable = usable
        self.bid_raw = np.where(usable, bid, np.nan); self.ask_raw = np.where(usable, ask, np.nan)
        # forward fill along minutes (last usable row of the leg)
        idx = np.where(usable, np.arange(NMIN)[None, :, None], -1)
        idx = np.maximum.accumulate(idx, axis=1)
        safe = np.where(idx < 0, 0, idx)
        g = lambda arr: np.where(idx >= 0, np.take_along_axis(arr, safe, axis=1), np.nan)
        self.bid = g(self.bid_raw); self.ask = g(self.ask_raw)
        self.ffilled = (~usable) & (idx >= 0)
        s = L.index('SPX', date)
        s = s.with_columns(((pl.col('timestamp').dt.hour().cast(pl.Int32) * 60 + pl.col('timestamp').dt.minute().cast(pl.Int32)) - 570).alias('i'))
        spx = np.full(NMIN, np.nan)
        for i_, p_ in zip(s['i'].to_list(), s['price'].to_list()):
            if 0 <= i_ < NMIN and p_ is not None: spx[i_] = p_
        self.spx = spx
        self.settle_flag = 'ok'
        self.S = spx[I1600]
        if not np.isfinite(self.S):
            self.S = spx[I1600 - 1]; self.settle_flag = 'fallback_1559'

    def atm(self, ti, spot):
        both = self.usable[0, ti, :] & self.usable[1, ti, :]
        if not both.any(): return None
        k0 = round(spot / 5) * 5
        hit = np.where((self.K == k0) & both)[0]
        if len(hit): return int(hit[0])
        cand = np.where(both)[0]
        d = np.abs(self.K[cand] - spot)
        best = cand[d == d.min()]
        return int(best.min())  # ties -> lower strike


def _outward(K, target, side):
    """side +1: smallest stored strike >= target; side -1: largest stored strike <= target. None if beyond band."""
    if side > 0:
        j = np.searchsorted(K, target - EPS, side='left')
        return int(j) if j < len(K) else None
    j = np.searchsorted(K, target + EPS, side='right') - 1
    return int(j) if j >= 0 else None


def build(sess, ti, winged, k):
    """Legs for one entry: list of (right, strike_idx, sign) with sign -1 short / +1 long, plus info; or a skip reason."""
    spot = sess.spx[ti]
    if not np.isfinite(spot): return 'no_spot', None
    j0 = sess.atm(ti, spot)
    if j0 is None: return 'no_quote', None
    em = (sess.bid_raw[0, ti, j0] + sess.ask_raw[0, ti, j0]) / 2 + (sess.bid_raw[1, ti, j0] + sess.ask_raw[1, ti, j0]) / 2
    info = dict(spot=spot, em=em, k0=sess.K[j0])
    if k == 0:
        jc = jp = j0
    else:
        jc = _outward(sess.K, spot + k * em, +1); jp = _outward(sess.K, spot - k * em, -1)
        if jc is None or jp is None: return 'out_of_band', info
    legs = [(0, jc, -1), (1, jp, -1)]
    if winged:
        jcw = _outward(sess.K, spot + (k + 1.0) * em, +1); jpw = _outward(sess.K, spot - (k + 1.0) * em, -1)
        if jcw is not None and jcw <= jc: jcw = jc + 1 if jc + 1 < len(sess.K) else None
        if jpw is not None and jpw >= jp: jpw = jp - 1 if jp - 1 >= 0 else None
        if jcw is None or jpw is None: return 'out_of_band', info
        legs += [(0, jcw, +1), (1, jpw, +1)]
    for (r, j, sg) in legs:
        if not sess.usable[r, ti, j]: return 'no_quote', info
    for (r, j, sg) in legs:
        if sg < 0 and sess.bid_raw[r, ti, j] <= 0: return 'zero_bid', info
    wing_bid0 = int(any(sg > 0 and sess.bid_raw[r, ti, j] <= 0 for (r, j, sg) in legs))
    credit = sum(sess.bid_raw[r, ti, j] for (r, j, sg) in legs if sg < 0) - sum(sess.ask_raw[r, ti, j] for (r, j, sg) in legs if sg > 0)
    credit = round(credit, 4)
    if credit <= EPS: return 'no_credit', info
    info.update(credit=credit, wing_bid0=wing_bid0, legs=legs)
    return None, info


def intrinsic(r, K, S):
    return max(S - K, 0.0) if r == 0 else max(K - S, 0.0)


def simulate(sess, ti, winged, k):
    """All 3 TP x 3 stop x 3 exit outcomes of one entry.  Returns (skip_reason, info, rows)."""
    reason, info = build(sess, ti, winged, k)
    if reason: return reason, info, []
    legs = info['legs']; C = info['credit']; S = sess.S; K = sess.K
    nl = len(legs)
    shorts = [(r, j) for (r, j, sg) in legs if sg < 0]; longs = [(r, j) for (r, j, sg) in legs if sg > 0]
    entry_hs = sum((sess.ask_raw[r, ti, j] - sess.bid_raw[r, ti, j]) / 2 for (r, j, sg) in legs) * 100
    # close cost X(m) for m in ti+1..15:55 (forward-filled rows)
    X = np.zeros(NMIN)
    for (r, j) in shorts: X = X + sess.ask[r, :, j]
    for (r, j) in longs: X = X - sess.bid[r, :, j]
    X = np.round(X, 4)
    w0, w1 = ti + 1, I1554  # check window
    win = np.arange(w0, w1 + 1)  # empty if entry is after 15:53
    Xw = X[win]
    width = None
    if winged:
        (rc, jc), (rp, jp) = shorts[0], shorts[1]
        (rcw, jcw), (rpw, jpw) = longs[0], longs[1]
        width = max(K[jcw] - K[jc], K[jp] - K[jpw])
    base = dict(spot=info['spot'], em=info['em'], credit=C, settle=S, n_legs=nl, wing_bid0=info['wing_bid0'],
                kc=K[shorts[0][1]], kp=K[shorts[1][1]], kcw=K[longs[0][1]] if longs else np.nan, kpw=K[longs[1][1]] if longs else np.nan,
                entry_hs=round(entry_hs, 2),
                max_loss_struct=round((width - C) * 100 + nl * FEE, 2) if winged else np.nan,
                ffill_exit=0)

    def close_at(m):
        """Trade every leg at row m (shorts at ask, longs at bid if > 0); long legs with bid 0 are left to settle."""
        pts = 0.0; traded = 0; hs = 0.0; ff = 0
        for (r, j) in shorts:
            pts -= sess.ask[r, m, j]; traded += 1; hs += (sess.ask[r, m, j] - sess.bid[r, m, j]) / 2; ff += int(sess.ffilled[r, m, j])
        for (r, j) in longs:
            b = sess.bid[r, m, j]
            if np.isfinite(b) and b > 0:
                pts += b; traded += 1; hs += (sess.ask[r, m, j] - b) / 2; ff += int(sess.ffilled[r, m, j])
            else:
                pts += intrinsic(r, K[j], S)
        return pts, traded, hs, ff

    def exit_time(rule):
        pts = 0.0; traded = 0; hs = 0.0; left = 0; ff = 0
        m = I1555
        for (r, j) in shorts:
            a = sess.ask[r, m, j]
            buy = np.isfinite(a) and (a > LEAVE + EPS if rule == 'E1' else True) and rule != 'E2'
            if buy:
                pts -= a; traded += 1; hs += (a - sess.bid[r, m, j]) / 2; ff += int(sess.ffilled[r, m, j])
            else:
                pts -= intrinsic(r, K[j], S); left += 1
        for (r, j) in longs:
            a = sess.ask[r, m, j]; b = sess.bid[r, m, j]
            sell = rule != 'E2' and np.isfinite(b) and b > 0 and (a > LEAVE + EPS if rule == 'E1' else True)
            if sell:
                pts += b; traded += 1; hs += (a - b) / 2; ff += int(sess.ffilled[r, m, j])
            else:
                pts += intrinsic(r, K[j], S); left += 1
        return pts, traded, hs, left, ff

    # triggers
    rows = []
    tp_first = {}
    for p in TPS:
        if p == 0: tp_first[p] = None; continue
        hit = np.where(Xw <= (1 - p) * C + EPS)[0]
        tp_first[p] = int(win[hit[0]]) if len(hit) else None
    st_first = {}
    for s in STOPS:
        if s == 0: st_first[s] = None; continue
        hit = np.where(Xw >= (1 + s) * C - EPS)[0]
        st_first[s] = int(win[hit[0]]) if len(hit) else None
    time_exits = {e: exit_time(e) for e in ('E0', 'E1', 'E2')}
    for p in TPS:
        for s in STOPS:
            mt, ms = tp_first[p], st_first[s]
            how = None
            if mt is not None and (ms is None or mt <= ms): how, m = 'tp', mt
            elif ms is not None: how, m = 'stop', ms + 1
            if how:
                pts, traded, hs, ff = close_at(m)
                for e in ('E0', 'E1', 'E2'):
                    fees = (nl + traded) * FEE
                    pnl = (C + pts) * 100 - fees
                    rows.append(dict(base, tp=p, stop=s, exit=e, how=how, exit_hm=i2hm(m), pnl=round(pnl, 2),
                                     pnl_adv=round(pnl - 5.0 * (nl + traded), 2), legs_left=len(longs) - (traded - len(shorts)),
                                     rt_cost=round(entry_hs + hs * 100 + fees, 2), ffill_exit=ff))
            else:
                for e in ('E0', 'E1', 'E2'):
                    pts, traded, hs, left, ff = time_exits[e]
                    fees = (nl + traded) * FEE
                    pnl = (C + pts) * 100 - fees
                    rows.append(dict(base, tp=p, stop=s, exit=e, how='settle' if e == 'E2' else 'time', exit_hm='16:00' if e == 'E2' else '15:55',
                                     pnl=round(pnl, 2), pnl_adv=round(pnl - 5.0 * (nl + traded), 2), legs_left=left,
                                     rt_cost=round(entry_hs + hs * 100 + fees, 2), ffill_exit=ff))
    return None, info, rows


def run_session(date, rand=None):
    """All trade and skip rows for one session.  rand: {draw: 'HH:MM'} random-entry minutes."""
    sess = Session(date)
    labels = [(e, e) for e in ENTRIES] + ([(f'R{d}', m) for d, m in sorted(rand.items())] if rand else [])
    out = []; skips = []
    for lab, hm in labels:
        ti = hm2i(hm)
        for winged in (0, 1):
            for k in KS:
                reason, info, rows = simulate(sess, ti, winged, k)
                cell = ('W' if winged else 'N') + f'{k:.1f}'
                if reason:
                    skips.append(dict(date=date, entry=lab, entry_hm=hm, cell=cell, reason=reason))
                    continue
                for r in rows:
                    r.update(date=date, entry=lab, entry_hm=hm, cell=cell, settle_flag=sess.settle_flag)
                out += rows
    return out, skips
