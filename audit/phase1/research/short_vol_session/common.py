"""Shared helpers for the short-vol / session-effects research.
Reuses backtest/data.py (Unusual Whales client + gzip cache), backtest/exits.py (trail engine) and backtest/costs.py (constants).
Conventions (look-ahead discipline):
  * a decision at minute T uses only bars whose start minute < T (i.e. the bar ending at T:00 is the last one seen);
  * entry fill = volume-weighted price (UW avg_price) of the first option bar with start minute in [T, T+3);
  * stops on combos are evaluated on the combined per-minute mark (vw, forward-filled) and filled on the NEXT bar's vw;
  * hard close: fill at the vw of the first option bar with start >= 15:55 (fallback: last traded price).
Cost models per contract per side: 'mid' = none; 'spread' = half-spread max(1 % (SPY/QQQ) or 2 % (IWM) of premium, $0.01) + $0.70;
  'adverse' = fill at the bar LOW when selling and the bar HIGH when buying, + $0.70.
"""
import os, sys, json, datetime, collections, concurrent.futures, csv, math
import numpy as np
BT = '/home/user/georgeredo/backtest'
sys.path.insert(0, BT)
import data, exits, costs
HERE = os.path.dirname(os.path.abspath(__file__))
CSV = HERE + '/csv'
DAYS = json.load(open(BT + '/trading_days.json'))
START, END = '2025-06-02', '2026-10-09'
TICKERS = ['SPY', 'QQQ', 'IWM']
SEL = [d for d in DAYS if START <= d <= END]
CLOSE_MIN = 15 * 60 + 55
HS = costs.HALF_SPREAD; FEE = costs.FEES
MODELS = ('mid', 'spread', 'adverse')

def hm(t): return t.hour * 60 + t.minute
def mstr(m): return f'{m // 60:02d}:{m % 60:02d}'
def weekday(d): return datetime.date.fromisoformat(d).strftime('%a')

_ub, _ob, _iv = {}, {}, {}
def ubars(tk, d):
    k = (tk, d)
    if k not in _ub: _ub[k] = data.underlying_bars(tk, d)
    return _ub[k]
def _safe_option_bars(c, d):
    """data.option_bars with retries: the cache directory is shared with other processes, so a file can be read while it is being written."""
    import time
    for i in range(4):
        try: return data.option_bars(c, d)
        except Exception as e:
            time.sleep(1 + i)
            if i >= 2:
                f = os.path.join(data.CACHE, data._key(f'option-contract/{c}/intraday', {'date': d}) + '.json.gz')
                try: os.remove(f); print('removed corrupt cache file', f[-80:], flush=True)
                except OSError: pass
    print('FAILED option bars', c, d, flush=True); return []
def obars(c, d):
    k = (c, d)
    if k not in _ob: _ob[k] = _safe_option_bars(c, d)
    return _ob[k]
def ivpct_prior(tk, d):
    """1-day IV percentile of the PRIOR session (known before today's open)."""
    pd = DAYS[DAYS.index(d) - 1]; k = (tk, pd)
    if k not in _iv: _iv[k] = data.iv_context(tk, pd).get('pct')
    return _iv[k]
def prefetch(needs, label='bars'):
    needs = sorted({n for n in needs if n not in _ob})
    print(label, 'contract-days to load:', len(needs), flush=True)
    def f(j): return j, _safe_option_bars(*j)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
        for n, (j, b) in enumerate(ex.map(f, needs)):
            _ob[j] = b
            if n % 1000 == 0: print(label, n, '/', len(needs), data.STATS, flush=True)
    print(label, 'done', data.STATS, flush=True)

def cid(tk, d, side, strike): return data.contract_id(tk, datetime.date.fromisoformat(d), side, strike)
def atm(px): return float(round(px))
def vw(b): return b['vw'] if b.get('vw') else b['c']

def px_before(rth, T):
    """Close of the last RTH bar with start minute < T."""
    last = None
    for b in rth:
        if hm(b['t']) < T: last = b
        else: break
    return last['c'] if last else None

def fill_bar(bars, T, max_wait=3):
    """First option bar with start minute in [T, T+max_wait); None if the contract did not trade in that window."""
    for b in bars:
        m = hm(b['t'])
        if m >= T: return b if m < T + max_wait else None
    return None

def fill_or_ffill(bars, T, max_wait=5):
    """Fill bar at T; if no trade within max_wait minutes, synthesise a bar at the last traded price before T (flag=1)."""
    b = fill_bar(bars, T, max_wait)
    if b is not None: return b, 0
    last = None
    for x in bars:
        if hm(x['t']) < T: last = x
        else: break
    if last is None: return None, 1
    p = vw(last); return dict(t=last['t'], o=p, h=p, l=p, c=p, vw=p, vol=0), 1

def close_fill(bars):
    return fill_or_ffill(bars, CLOSE_MIN, 5)

def slip(tk, p): return max(HS[tk] * p, 0.01)

# ---------------- combos (straddle / strangle) ----------------
def sim_combo(tk, d, T, legs, side='short', stop_mult=None):
    """legs = [(cid, strike, 'C'|'P')]. side='short': sell all legs at T, buy back at stop/close. 'long': the mirror.
    Stop (short): combined mark >= stop_mult*credit -> buy back next bar. Stop (long): combined mark <= stop_mult*debit.
    Returns dict with per-model $ P&L for one contract per leg, or None if a leg has no fill within 3 minutes of T."""
    bars = [obars(c, d) for c, _, _ in legs]
    ebs = [fill_bar(b, T) for b in bars]
    if any(e is None for e in ebs): return None
    e_px = [vw(e) for e in ebs]
    if any(p < 0.01 for p in e_px): return None
    credit = sum(e_px)
    maps = [{hm(b['t']): b for b in bb} for bb in bars]
    entry_min = max(hm(e['t']) for e in ebs)
    last = list(e_px); exit_min = None; reason = 'CLOSE'; peak = credit; trough = credit
    for m in range(entry_min + 1, CLOSE_MIN):
        for i, mp in enumerate(maps):
            if m in mp: last[i] = vw(mp[m])
        comb = sum(last); peak = max(peak, comb); trough = min(trough, comb)
        if stop_mult:
            if side == 'short' and comb >= stop_mult * credit: exit_min = m + 1; reason = 'STOP'; break
            if side == 'long' and comb <= stop_mult * credit: exit_min = m + 1; reason = 'STOP'; break
    if exit_min is None: exit_min = CLOSE_MIN
    xbs = []; ff = 0
    for b in bars:
        xb, fl = fill_or_ffill(b, exit_min, 5); ff += fl
        if xb is None: return None
        xbs.append(xb)
    x_px = [vw(x) for x in xbs]
    n = len(legs); fees = 2 * n * FEE
    if side == 'short':
        pnl = dict(mid=(sum(e_px) - sum(x_px)) * 100,
                   spread=(sum(p - slip(tk, p) for p in e_px) - sum(p + slip(tk, p) for p in x_px)) * 100 - fees,
                   adverse=(sum(max(e['l'], 0.01) for e in ebs) - sum(x['h'] for x in xbs)) * 100 - fees)
    else:
        pnl = dict(mid=(sum(x_px) - sum(e_px)) * 100,
                   spread=(sum(p - slip(tk, p) for p in x_px) - sum(p + slip(tk, p) for p in e_px)) * 100 - fees,
                   adverse=(sum(max(x['l'], 0.0) for x in xbs) - sum(e['h'] for e in ebs)) * 100 - fees)
    return dict(entry_t=mstr(entry_min), exit_t=mstr(min(exit_min, CLOSE_MIN)), reason=reason, credit=round(credit, 3), debit=round(sum(x_px), 3),
                peak_mark=round(peak, 3), trough_mark=round(trough, 3), leg_px='|'.join(f'{p:.2f}' for p in e_px), ffill=ff,
                pnl_mid=round(pnl['mid'], 2), pnl_spread=round(pnl['spread'], 2), pnl_adverse=round(pnl['adverse'], 2),
                pct_mid=round(pnl['mid'] / (credit * 100), 4), pct_spread=round(pnl['spread'] / (credit * 100), 4), pct_adverse=round(pnl['adverse'] / (credit * 100), 4))

# ---------------- single long option with the existing exit engines ----------------
def sim_long(tk, d, c, T, engine='trail', strict_after=False):
    """Buy one contract at the first bar with start >= T (or > T if strict_after), run backtest/exits.simulate(engine), settle 3 ways."""
    bars = obars(c, d)
    T0 = T + 1 if strict_after else T
    eb = fill_bar(bars, T0, 3)
    if eb is None: return None
    eidx = bars.index(eb); entry_px = vw(eb)
    if entry_px < 0.05: return None
    legs = exits.simulate(bars, eidx, entry_px, engine, {'stop': -0.25})
    if not legs: return None
    bym = {hm(b['t']): b for b in bars}
    mid = sum(f * p for f, p, t, r in legs)
    spr = sum(f * (p - slip(tk, p)) for f, p, t, r in legs)
    adv = sum(f * min(p, bym[hm(t)]['l']) for f, p, t, r in legs)
    buy_s = entry_px + slip(tk, entry_px); buy_a = eb['h']
    exit_t = max(l[2] for l in legs); reasons = '+'.join(l[3] for l in legs)
    mfe = max((b['h'] for b in bars[eidx + 1:] if hm(b['t']) < CLOSE_MIN), default=entry_px) / entry_px - 1
    return dict(entry_t=mstr(hm(eb['t'])), exit_t=mstr(hm(exit_t)), reason=reasons, entry_px=round(entry_px, 3), hold_min=int((exit_t - eb['t']).total_seconds() // 60), mfe=round(mfe, 4),
                pnl_mid=round((mid - entry_px) * 100, 2), pnl_spread=round((spr - buy_s) * 100 - 2 * FEE, 2), pnl_adverse=round((adv - buy_a) * 100 - 2 * FEE, 2),
                ret_mid=round(mid / entry_px - 1, 4), ret_spread=round((spr - buy_s) / buy_s, 4))

# ---------------- statistics ----------------
def boot_ci(v, clusters=None, B=5000, seed=7):
    v = np.asarray(v, float); n = len(v)
    if n < 5: return (float('nan'), float('nan'))
    rng = np.random.default_rng(seed)
    if clusters is None:
        means = np.empty(B); step = max(1, min(B, 20_000_000 // n))
        for s in range(0, B, step):
            idx = rng.integers(0, n, (min(step, B - s), n)); means[s:s + idx.shape[0]] = v[idx].mean(1)
    else:
        keys = {}; cl = np.array([keys.setdefault(c, len(keys)) for c in clusters]); J = len(keys)
        S = np.bincount(cl, weights=v, minlength=J); N = np.bincount(cl, minlength=J).astype(float)
        idx = rng.integers(0, J, (B, J)); means = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))

def maxdd(v):
    c = np.cumsum(v); peak = np.maximum.accumulate(np.concatenate([[0.0], c]))[1:]
    return float((c - peak).min()) if len(c) else 0.0

def summ(rows, key='pnl_spread', clusters='date', order='date'):
    """n, mean, cluster-bootstrap 95 % CI (clusters = date), win rate, profit factor, max drawdown (chronological)."""
    if not rows: return dict(n=0)
    rows = sorted(rows, key=lambda r: (r[order], r.get('entry_t', '')))
    v = np.array([float(r[key]) for r in rows]); cl = [r[clusters] for r in rows] if clusters else None
    lo, hi = boot_ci(v, cl); w = v[v > 0]; l = v[v < 0]
    return dict(n=int(len(v)), mean=round(float(v.mean()), 4), lo=round(lo, 4), hi=round(hi, 4), median=round(float(np.median(v)), 4), wr=round(100 * (v > 0).mean(), 1),
                pf=round(float(w.sum() / abs(l.sum())), 2) if len(l) and l.sum() != 0 else float('inf'), total=round(float(v.sum()), 0), mdd=round(maxdd(v), 0),
                sd=round(float(v.std(ddof=1)), 1) if len(v) > 1 else float('nan'), t=round(float(v.mean() / (v.std(ddof=1) / math.sqrt(len(v)))), 2) if len(v) > 1 and v.std() > 0 else float('nan'))

def iv_terciles(rows, key='ivpct'):
    vals = sorted(float(r[key]) for r in rows if r.get(key) not in (None, '', 'None'))
    if len(vals) < 9: return None
    return vals[len(vals) // 3], vals[2 * len(vals) // 3]

def iv_bucket(x, cuts):
    if x in (None, '', 'None') or cuts is None: return 'n/a'
    x = float(x); return 'IV_low' if x < cuts[0] else ('IV_mid' if x < cuts[1] else 'IV_high')

def breakdowns(rows, key='pnl_spread', cuts=None):
    """Per ticker / weekday / month / IV tercile: n, mean, CI, win rate."""
    out = []
    groups = [('ticker', lambda r: r['ticker']), ('weekday', lambda r: r['weekday']), ('month', lambda r: r['date'][:7]), ('iv', lambda r: iv_bucket(r.get('ivpct'), cuts))]
    for gname, fn in groups:
        g = collections.defaultdict(list)
        for r in rows: g[fn(r)].append(r)
        for k in sorted(g):
            s = summ(g[k], key); out.append(dict(group=gname, value=k, **s))
    return out

def write_csv(path, rows):
    if not rows: open(path, 'w').write(''); return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(rows)

def read_csv(path):
    return list(csv.DictReader(open(path)))

def fmt(s, pct=False):
    if not s or s.get('n', 0) == 0: return 'n=0'
    return f"n={s['n']} mean={s['mean']:.2f} CI=[{s['lo']:.2f},{s['hi']:.2f}] wr={s['wr']}% PF={s['pf']} mdd={s['mdd']:.0f} total={s['total']:.0f}"
