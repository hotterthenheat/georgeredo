"""Executable P&L of the 0DTE short ATM straddle lane from MEASURED 1-minute NBBO (ThetaData), like-for-like with the
modelled-spread study research/short_vol_session (same sessions, tickers, entry times and ATM strikes).
Usage: python3 -I analyze.py            (reads the gzip-CSV cache written by fetch.py; no network, no key)
Writes: csv/straddles_nbbo.csv.gz (one row per entry time x ticker x date, plus the random-time baseline), csv/stats_*.csv,
        csv/half_spread_*.csv, RESULTS.md."""
import os, sys, csv, json, math, collections, datetime as dt
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import jobs as J
SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
CACHE = os.environ.get('THETA_CACHE', SP + '/theta/cache/straddle')
OUT = HERE + '/csv'; os.makedirs(OUT, exist_ok=True)
FEE = 0.70                                   # $ per contract per side; 4 sides per straddle round trip
HS_MODEL = {'SPY': 0.01, 'QQQ': 0.01, 'IWM': 0.02}   # the modelled half-spreads (fraction of premium), floor $0.01
CLOSE = 15 * 60 + 55
EXITS = {'1555': CLOSE, '1559': 15 * 60 + 59, '1600': 16 * 60}
EVENTS = {r['date']: r['event'] for r in csv.DictReader(open(HERE + '/event_days.csv'))}
def tmin(s): h, m = s.split(':'); return int(h) * 60 + int(m)
def mstr(m): return f'{m // 60:02d}:{m % 60:02d}'

# ---------------- quotes ----------------
_Q = {}
def load_quotes(tk, d, K):
    """{'CALL': df, 'PUT': df} indexed by ET minute 570..960 with bid, ask, bid_size, ask_size, mid, raw (True = quote row present at that minute).
    Minutes without a usable row (NaN, ask<=0, ask<bid) are forward-filled from the last usable minute and flagged raw=False."""
    key = (tk, d, int(K))
    if key in _Q: return _Q[key]
    f = os.path.join(CACHE, J.okey(tk, d, K) + '.csv.gz')
    if not os.path.exists(f): _Q[key] = None; return None
    df = pd.read_csv(f)
    if len(df) == 0: _Q[key] = None; return None
    ts = pd.to_datetime(df['timestamp'], utc=True).dt.tz_convert('America/New_York')
    df['m'] = ts.dt.hour * 60 + ts.dt.minute
    legs = {}
    for r in ('CALL', 'PUT'):
        x = df[df['right'] == r].drop_duplicates('m').set_index('m')[['bid', 'ask', 'bid_size', 'ask_size']].reindex(range(570, 961))
        valid = x['bid'].notna() & x['ask'].notna() & (x['ask'] > 0) & (x['ask'] >= x['bid']) & (x['bid'] >= 0)
        x.loc[~valid, ['bid', 'ask', 'bid_size', 'ask_size']] = np.nan
        x['raw'] = valid
        x[['bid', 'ask', 'bid_size', 'ask_size']] = x[['bid', 'ask', 'bid_size', 'ask_size']].ffill()
        x['mid'] = (x['bid'] + x['ask']) / 2
        legs[r] = x
    _Q[key] = legs; return legs

_S = {}
def load_stock(tk, d):
    k = (tk, d)
    if k in _S: return _S[k]
    f = os.path.join(CACHE, J.skey(tk, d) + '.csv.gz')
    _S[k] = pd.read_csv(f) if os.path.exists(f) else None
    return _S[k]

# ---------------- one straddle ----------------
def sim(tk, legs, T, exit_min=CLOSE, stop_mult=None):
    """Sell call+put at the BID at minute T, buy back at the ASK at exit_min (or at the minute after the stop trigger).
    Stop: combined quote MID >= stop_mult x entry mid-credit, checked each minute from T+1 to exit_min-1, filled at the next minute's ask.
    Returns a dict or (None, reason)."""
    C, P = legs['CALL'], legs['PUT']
    if T not in C.index or T not in P.index: return None, 'entry_minute_out_of_range'
    ec, ep = C.loc[T], P.loc[T]
    if not (ec['raw'] and ep['raw']): return None, 'no_quote_at_entry'
    if np.isnan(ec['bid']) or np.isnan(ep['bid']): return None, 'nan_entry'
    if ec['bid'] <= 0 or ep['bid'] <= 0: return None, 'zero_bid_at_entry'
    credit_bid = ec['bid'] + ep['bid']; credit_mid = ec['mid'] + ep['mid']
    hs_e = [(ec['ask'] - ec['bid']) / 2, (ep['ask'] - ep['bid']) / 2]
    exit_m, reason = exit_min, 'CLOSE'
    comb = (C['mid'] + P['mid'])
    path = comb.loc[T + 1: exit_min - 1]
    peak = float(max(credit_mid, path.max())) if len(path) else credit_mid
    trough = float(min(credit_mid, path.min())) if len(path) else credit_mid
    if stop_mult:
        hit = path[path >= stop_mult * credit_mid]
        if len(hit): exit_m = int(hit.index[0]) + 1; reason = 'STOP'
    xc, xp = C.loc[exit_m], P.loc[exit_m]
    if np.isnan(xc['ask']) or np.isnan(xp['ask']): return None, 'nan_exit'
    hs_x = [(xc['ask'] - xc['bid']) / 2, (xp['ask'] - xp['bid']) / 2]
    debit_ask = xc['ask'] + xp['ask']; debit_mid = xc['mid'] + xp['mid']
    fees = 4 * FEE
    pnl_exec = (credit_bid - debit_ask) * 100 - fees
    pnl_mid = (credit_mid - debit_mid) * 100
    h = HS_MODEL[tk]
    pnl_model = (sum(m - max(h * m, 0.01) for m in (ec['mid'], ep['mid'])) - sum(m + max(h * m, 0.01) for m in (xc['mid'], xp['mid']))) * 100 - fees
    return dict(entry_t=mstr(T), exit_t=mstr(exit_m), reason=reason,
                call_bid=ec['bid'], call_ask=ec['ask'], put_bid=ep['bid'], put_ask=ep['ask'], call_bid_size=ec['bid_size'], put_bid_size=ep['bid_size'],
                credit_bid=round(credit_bid, 4), credit_mid=round(credit_mid, 4), debit_ask=round(debit_ask, 4), debit_mid=round(debit_mid, 4),
                exit_call_bid=xc['bid'], exit_call_ask=xc['ask'], exit_put_bid=xp['bid'], exit_put_ask=xp['ask'], exit_raw=int(bool(xc['raw'] and xp['raw'])),
                hs_entry_call=hs_e[0], hs_entry_put=hs_e[1], hs_exit_call=hs_x[0], hs_exit_put=hs_x[1],
                hs_entry_call_pct=100 * hs_e[0] / ec['mid'] if ec['mid'] > 0 else np.nan, hs_entry_put_pct=100 * hs_e[1] / ep['mid'] if ep['mid'] > 0 else np.nan,
                hs_exit_call_pct=100 * hs_x[0] / xc['mid'] if xc['mid'] > 0 else np.nan, hs_exit_put_pct=100 * hs_x[1] / xp['mid'] if xp['mid'] > 0 else np.nan,
                hs_entry_pct_credit=100 * sum(hs_e) / credit_mid, hs_exit_pct_credit=100 * sum(hs_x) / credit_mid, hs_roundtrip_pct_credit=100 * (sum(hs_e) + sum(hs_x)) / credit_mid,
                peak_mid=round(peak, 4), trough_mid=round(trough, 4),
                pnl_exec=round(pnl_exec, 2), pnl_mid=round(pnl_mid, 2), pnl_model_theta=round(pnl_model, 2), gap=round(pnl_mid - pnl_exec, 2)), None

# ---------------- statistics (bootstrap copied from research/short_vol_session/common.py so CIs are comparable) ----------------
def boot_ci(v, clusters=None, B=5000, seed=7):
    v = np.asarray(v, float); n = len(v)
    if n < 5: return (float('nan'), float('nan'))
    rng = np.random.default_rng(seed)
    if clusters is None:
        means = np.empty(B); step = max(1, min(B, 20_000_000 // n))
        for s in range(0, B, step):
            idx = rng.integers(0, n, (min(step, B - s), n)); means[s:s + idx.shape[0]] = v[idx].mean(1)
    else:
        keys = {}; cl = np.array([keys.setdefault(c, len(keys)) for c in clusters]); Jn = len(keys)
        S = np.bincount(cl, weights=v, minlength=Jn); N = np.bincount(cl, minlength=Jn).astype(float)
        idx = rng.integers(0, Jn, (B, Jn)); means = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))
def maxdd(v):
    c = np.cumsum(v); peak = np.maximum.accumulate(np.concatenate([[0.0], c]))[1:]
    return float((c - peak).min()) if len(c) else 0.0
def summ(df, key='pnl_exec'):
    if len(df) == 0: return dict(n=0)
    df = df.sort_values(['date', 'ticker']); v = df[key].to_numpy(float); cl = df['date'].tolist()
    lo, hi = boot_ci(v, cl); w = v[v > 0]; l = v[v < 0]
    return dict(n=int(len(v)), total=round(float(v.sum()), 0), mean=round(float(v.mean()), 2), lo=round(lo, 2), hi=round(hi, 2), median=round(float(np.median(v)), 2),
                wr=round(100 * (v > 0).mean(), 1), pf=round(float(w.sum() / abs(l.sum())), 2) if len(l) and l.sum() != 0 else float('inf'), mdd=round(maxdd(v), 0),
                months=int(df['date'].str[:7].nunique()), dates=int(df['date'].nunique()))
def fmt(s):
    if not s or s.get('n', 0) == 0: return '| n=0 |||||||'
    return f"| {s['n']} | {s['total']:.0f} | {s['mean']:.2f} | [{s['lo']:.2f}, {s['hi']:.2f}] | {s['wr']}% | {s['pf']} | {s['mdd']:.0f} |"
HDR = '| lane | n | total $ | mean $ | 95% CI (date-cluster) | win | PF | maxDD $ |\n|---|---|---|---|---|---|---|---|\n'

# ---------------- build the per-straddle table ----------------
def build():
    t1 = J.load_t1(); rows = []; skipped = collections.Counter()
    for (t, tk, d), r in sorted(t1.items()):
        K = int(float(r['strike'])); legs = load_quotes(tk, d, K)
        base = dict(time=t, ticker=tk, date=d, month=d[:7], strike=K, event=EVENTS.get(d, ''), T=t,
                    uw_credit=float(r['credit']), uw_pnl_mid=float(r['pnl_mid']), uw_pnl_spread=float(r['pnl_spread']), uw_pnl_adverse=float(r['pnl_adverse']), uw_entry_t=r['entry_t'])
        if legs is None: skipped[(t, 'no_quote_file')] += 1; continue
        T = tmin(t)
        out, why = sim(tk, legs, T)
        if out is None: skipped[(t, why)] += 1; continue
        row = dict(base, **out)
        for name, xm in EXITS.items():
            if name == '1555': continue
            o, _ = sim(tk, legs, T, exit_min=xm)
            row[f'pnl_exec_{name}'] = o['pnl_exec'] if o else np.nan; row[f'pnl_mid_{name}'] = o['pnl_mid'] if o else np.nan
        for sm in (2.0, 1.5):
            o, _ = sim(tk, legs, T, stop_mult=sm)
            row[f'pnl_exec_stop{sm}'] = o['pnl_exec'] if o else np.nan; row[f'pnl_mid_stop{sm}'] = o['pnl_mid'] if o else np.nan
            row[f'reason_stop{sm}'] = o['reason'] if o else ''; row[f'exit_t_stop{sm}'] = o['exit_t'] if o else ''
        rows.append(row)
    # random-time baseline (seed 11): one straddle per ticker-date at a uniformly random RTH minute, ATM strike from the ThetaData stock bar ending at T
    rm = J.random_minutes()
    for (tk, d), T in sorted(rm.items()):
        s = load_stock(tk, d); K = J.random_strike(s, T) if s is not None else None
        if K is None: skipped[('random', 'no_stock_bars')] += 1; continue
        legs = load_quotes(tk, d, K)
        if legs is None: skipped[('random', 'no_quote_file')] += 1; continue
        out, why = sim(tk, legs, T)
        if out is None: skipped[('random', why)] += 1; continue
        rows.append(dict(time='random', ticker=tk, date=d, month=d[:7], strike=K, event=EVENTS.get(d, ''), T=mstr(T), **out))
    df = pd.DataFrame(rows)
    return df, skipped

def main():
    df, skipped = build()
    df.to_csv(OUT + '/straddles_nbbo.csv.gz', index=False, compression='gzip')
    fixed = df[df['time'] != 'random'].copy(); rnd = df[df['time'] == 'random'].copy()
    L = []; P = L.append
    P('# 0DTE short ATM straddle: executable P&L from measured NBBO (ThetaData 1-minute quotes)\n')
    P(f'Generated {dt.datetime.now().strftime("%Y-%m-%d %H:%M")} by analyze.py from the gzip cache (`fetch.py`). Sessions {J.START}..{J.END}: {fixed["date"].nunique()} dates, '
      f'{len(fixed)} fixed-time straddles + {len(rnd)} random-time baseline straddles. Fills: sell both legs at the BID at the entry minute, buy back at the ASK at 15:55; fees $0.70 x 4 sides. '
      f'All $ are per 1-lot straddle. CIs: 95 % bootstrap over date clusters (5,000 draws, seed 7). Skipped straddles: {dict(skipped) or "none"}.\n')
    P('Definitions: `exec` = bid/ask fills + fees; `mid` = quote mids, no fees (the reference used by the modelled study); `model@theta` = the modelled cost rule '
      '(half-spread max(1 % SPY/QQQ or 2 % IWM of premium, $0.01) per leg per side + fees) applied to the ThetaData mids; `uw_spread` = the modelled study\'s own number '
      '(Unusual Whales bar VWAP fills + the same cost rule) on the same date x ticker x entry time.\n')
    # ---- coverage ----
    P('## 0. Coverage\n')
    P('| entry time | straddles (SPY/QQQ/IWM) | dates | exit quote row present at 15:55 (not forward-filled) | median entry bid size (call / put) |\n|---|---|---|---|---|')
    for t in J.TIMES:
        x = fixed[fixed['time'] == t]
        if len(x) == 0: P(f'| {t} | not fetched | | | |'); continue
        P(f"| {t} | {len(x)} ({(x['ticker']=='SPY').sum()}/{(x['ticker']=='QQQ').sum()}/{(x['ticker']=='IWM').sum()}) | {x['date'].nunique()} | {100*x['exit_raw'].mean():.1f}% | {x['call_bid_size'].median():.0f} / {x['put_bid_size'].median():.0f} |")
    P(f"| random | {len(rnd)} | {rnd['date'].nunique() if len(rnd) else 0} | {100*rnd['exit_raw'].mean():.1f}% | {rnd['call_bid_size'].median() if len(rnd) else float('nan'):.0f} / {rnd['put_bid_size'].median() if len(rnd) else float('nan'):.0f} |")
    # ---- 1. headline: 13:00 ----
    P('\n## 1. The pre-registered lane: 13:00 entry, close 15:55, no stop\n')
    P(HDR.rstrip())
    stats = []
    groups = [('SPY', fixed.query("time=='13:00' and ticker=='SPY'")), ('QQQ', fixed.query("time=='13:00' and ticker=='QQQ'")), ('IWM', fixed.query("time=='13:00' and ticker=='IWM'")),
              ('SPY+QQQ (T-A lane)', fixed.query("time=='13:00' and ticker!='IWM'")), ('SPY+QQQ+IWM (modelled headline)', fixed.query("time=='13:00'"))]
    for name, g in groups:
        for key, label in (('pnl_exec', 'exec 15:55'), ('pnl_mid', 'mid 15:55'), ('pnl_model_theta', 'model@theta'), ('uw_pnl_spread', 'uw_spread (modelled study)'), ('uw_pnl_mid', 'uw_mid (modelled study)'),
                           ('pnl_exec_1559', 'exec 15:59'), ('pnl_exec_1600', 'exec 16:00 last quote'), ('pnl_exec_stop2.0', 'exec stop 2.0x'), ('pnl_exec_stop1.5', 'exec stop 1.5x')):
            s = summ(g, key); P(f'| 13:00 {name} / {label} ' + fmt(s)); stats.append(dict(group=name, time='13:00', variant=label, **s))
        ne = g[g['event'] == '']
        for key, label in (('pnl_exec', 'exec 15:55, no FOMC/CPI/NFP days'), ('pnl_exec_stop2.0', 'exec stop 2.0x, no event days')):
            s = summ(ne, key); P(f'| 13:00 {name} / {label} ' + fmt(s)); stats.append(dict(group=name, time='13:00', variant=label, **s))
    # gap
    P('\nMid-vs-executable gap per straddle (mid P&L minus exec P&L = realized half-spreads x 100 + $2.80 fees):\n')
    P('| lane | mean gap $ | median gap $ | mean modelled cost $ (uw_mid - uw_spread) | mean model@theta cost $ (mid - model@theta) |\n|---|---|---|---|---|')
    for name, g in groups:
        P(f"| 13:00 {name} | {g['gap'].mean():.2f} | {g['gap'].median():.2f} | {(g['uw_pnl_mid']-g['uw_pnl_spread']).mean():.2f} | {(g['pnl_mid']-g['pnl_model_theta']).mean():.2f} |")
    # data-source agreement
    g = fixed.query("time=='13:00'")
    P(f"\nData-source agreement at 13:00 (same contracts, same minutes): mean mid P&L ThetaData quotes {g['pnl_mid'].mean():.2f} vs Unusual Whales VWAP bars {g['uw_pnl_mid'].mean():.2f}; "
      f"correlation of per-straddle mid P&L {np.corrcoef(g['pnl_mid'], g['uw_pnl_mid'])[0,1]:.3f}; mean credit (mid) {g['credit_mid'].mean():.3f} vs UW VWAP credit {g['uw_credit'].mean():.3f}; "
      f"mean credit at the bid {g['credit_bid'].mean():.3f}.")
    # worst days
    P('\nWorst 5 dates (SPY+QQQ at 13:00, exec P&L summed over the two tickers):\n')
    sq = fixed.query("time=='13:00' and ticker!='IWM'").groupby('date')['pnl_exec'].sum().sort_values()
    P('| date | exec $ | event |\n|---|---|---|')
    for d, v in sq.head(5).items(): P(f'| {d} | {v:.0f} | {EVENTS.get(d, "")} |')
    P(f'\nBest 5 dates: ' + ', '.join(f'{d} {v:+.0f}' for d, v in sq.tail(5)[::-1].items()) + f'. Sum of the two best dates = {sq.tail(2).sum():.0f} vs total {sq.sum():.0f}.')
    # ---- 2. all entry times x tickers ----
    P('\n## 2. Every entry time x ticker (exec 15:55, no stop)\n')
    P(HDR.rstrip())
    for t in J.TIMES:
        for tk in J.TICKERS + ['SPY+QQQ', 'ALL']:
            g = fixed[(fixed['time'] == t) & ((fixed['ticker'] == tk) if tk in J.TICKERS else (fixed['ticker'] != 'IWM') if tk == 'SPY+QQQ' else True)]
            if len(g) == 0: continue
            s = summ(g, 'pnl_exec'); P(f'| {t} {tk} / exec ' + fmt(s)); stats.append(dict(group=tk, time=t, variant='exec 15:55', **s))
            sm = summ(g, 'pnl_mid'); su = summ(g, 'uw_pnl_spread'); stats.append(dict(group=tk, time=t, variant='mid 15:55', **sm)); stats.append(dict(group=tk, time=t, variant='uw_spread', **su))
    P('\nSame cells, mean $ only: exec / mid / model@theta / uw_spread / uw_mid / exec stop 2.0x / exec no-event-days:\n')
    P('| time | ticker | n | exec | mid | model@theta | uw_spread | uw_mid | exec stop2.0 | exec stop1.5 | exec no-events (n) |\n|---|---|---|---|---|---|---|---|---|---|---|')
    for t in J.TIMES:
        for tk in J.TICKERS + ['SPY+QQQ', 'ALL']:
            g = fixed[(fixed['time'] == t) & ((fixed['ticker'] == tk) if tk in J.TICKERS else (fixed['ticker'] != 'IWM') if tk == 'SPY+QQQ' else True)]
            if len(g) == 0: continue
            ne = g[g['event'] == '']
            P(f"| {t} | {tk} | {len(g)} | {g['pnl_exec'].mean():.2f} | {g['pnl_mid'].mean():.2f} | {g['pnl_model_theta'].mean():.2f} | {g['uw_pnl_spread'].mean():.2f} | {g['uw_pnl_mid'].mean():.2f} | {g['pnl_exec_stop2.0'].mean():.2f} | {g['pnl_exec_stop1.5'].mean():.2f} | {ne['pnl_exec'].mean():.2f} ({len(ne)}) |")
    pd.DataFrame(stats).to_csv(OUT + '/stats_lanes.csv', index=False)
    # ---- 3. half-spreads ----
    P('\n## 3. Realized half-spread (ask - bid)/2 per leg, from the quote at the fill minute\n')
    P('Per-leg half-spread as % of the leg mid at the same minute, compared with the modelled 1 % (SPY/QQQ) / 2 % (IWM). Entry = sell at the entry minute; exit = buy at 15:55.\n')
    def q(x): x = x.dropna(); return (f'{x.median():.3f} / {x.quantile(.75):.3f} / {x.quantile(.95):.3f}' if len(x) else 'n/a')
    def qd(x): x = x.dropna(); return (f'{x.median():.4f} / {x.quantile(.75):.4f} / {x.quantile(.95):.4f}' if len(x) else 'n/a')
    hs_rows = []
    def hs_block(title, keyfn, order):
        P(f'\n### {title}\n')
        P('| group | n | entry call % mid (p50/p75/p95) | entry put % mid | entry $ per leg (call; put) p50/p75/p95 | entry straddle half-spread % of credit (p50/p75/p95) | exit call % mid | exit put % mid | exit $ per leg (call; put) p50 | round-trip half-spread % of credit (p50/p75/p95) | mean |\n|---|---|---|---|---|---|---|---|---|---|---|')
        for k in order:
            g = fixed[keyfn(fixed) == k]
            if len(g) == 0: continue
            P(f"| {k} | {len(g)} | {q(g['hs_entry_call_pct'])} | {q(g['hs_entry_put_pct'])} | {qd(g['hs_entry_call'])}; {qd(g['hs_entry_put'])} | {q(g['hs_entry_pct_credit'])} | {q(g['hs_exit_call_pct'])} | {q(g['hs_exit_put_pct'])} | {g['hs_exit_call'].median():.4f}; {g['hs_exit_put'].median():.4f} | {q(g['hs_roundtrip_pct_credit'])} | {g['hs_roundtrip_pct_credit'].mean():.3f} |")
            hs_rows.append(dict(group=title, value=k, n=len(g), **{c + '_p50': g[c].median() for c in ('hs_entry_call_pct', 'hs_entry_put_pct', 'hs_entry_call', 'hs_entry_put', 'hs_entry_pct_credit', 'hs_exit_call_pct', 'hs_exit_put_pct', 'hs_exit_call', 'hs_exit_put', 'hs_roundtrip_pct_credit')},
                               **{c + '_p75': g[c].quantile(.75) for c in ('hs_entry_call_pct', 'hs_entry_put_pct', 'hs_entry_pct_credit', 'hs_roundtrip_pct_credit')},
                               **{c + '_p95': g[c].quantile(.95) for c in ('hs_entry_call_pct', 'hs_entry_put_pct', 'hs_entry_pct_credit', 'hs_roundtrip_pct_credit')},
                               **{c + '_mean': g[c].mean() for c in ('hs_entry_pct_credit', 'hs_exit_pct_credit', 'hs_roundtrip_pct_credit')}))
    hs_block('By ticker (all entry times)', lambda x: x['ticker'], J.TICKERS)
    hs_block('By ticker at 13:00', lambda x: np.where(x['time'] == '13:00', x['ticker'] + ' 13:00', ''), [tk + ' 13:00' for tk in J.TICKERS])
    hs_block('By entry time (all tickers)', lambda x: x['time'], J.TIMES)
    hs_block('By entry time, SPY+QQQ only', lambda x: np.where(x['ticker'] != 'IWM', x['time'] + ' SPY+QQQ', ''), [t + ' SPY+QQQ' for t in J.TIMES])
    hs_block('By year-month, 13:00 SPY+QQQ', lambda x: np.where((x['ticker'] != 'IWM') & (x['time'] == '13:00'), x['month'], ''), sorted(fixed['month'].unique()))
    hs_block('By year-month, 13:00 IWM', lambda x: np.where((x['ticker'] == 'IWM') & (x['time'] == '13:00'), x['month'], ''), sorted(fixed['month'].unique()))
    pd.DataFrame(hs_rows).to_csv(OUT + '/half_spread_distribution.csv', index=False)
    # ---- 4. random baseline ----
    P('\n## 4. Random-time baseline (seed 11): one straddle per ticker-date at a uniformly random minute in [09:31, 15:54], ATM at that minute, same fills, close 15:55\n')
    P(HDR.rstrip())
    rb = {}
    for tk in J.TICKERS + ['SPY+QQQ', 'ALL']:
        g = rnd[(rnd['ticker'] == tk) if tk in J.TICKERS else (rnd['ticker'] != 'IWM') if tk == 'SPY+QQQ' else np.ones(len(rnd), bool)]
        if len(g) == 0: continue
        s = summ(g, 'pnl_exec'); rb[tk] = s; P(f'| random {tk} / exec ' + fmt(s)); stats.append(dict(group=tk, time='random', variant='exec 15:55', **s))
        s2 = summ(g, 'pnl_mid'); P(f'| random {tk} / mid ' + fmt(s2))
    P('\n13:00 lane minus random baseline, paired by ticker-date (exec, $ per straddle), CI clustered by date; the "one round-trip cost" is the 13:00 lane\'s mean mid-minus-exec gap:\n')
    P('| lane | n pairs | 13:00 exec mean | random exec mean | difference | 95% CI | round-trip cost $ | difference > cost? |\n|---|---|---|---|---|---|---|---|')
    pd.DataFrame(stats).to_csv(OUT + '/stats_lanes.csv', index=False)
    gate_rb = {}
    for tk in J.TICKERS + ['SPY+QQQ', 'ALL']:
        a = fixed[(fixed['time'] == '13:00') & ((fixed['ticker'] == tk) if tk in J.TICKERS else (fixed['ticker'] != 'IWM') if tk == 'SPY+QQQ' else True)]
        b = rnd[(rnd['ticker'] == tk) if tk in J.TICKERS else (rnd['ticker'] != 'IWM') if tk == 'SPY+QQQ' else np.ones(len(rnd), bool)]
        m = a.merge(b[['ticker', 'date', 'pnl_exec']], on=['ticker', 'date'], suffixes=('', '_rnd'))
        if len(m) == 0: continue
        diff = (m['pnl_exec'] - m['pnl_exec_rnd']); lo, hi = boot_ci(diff.to_numpy(), m['date'].tolist()); cost = a['gap'].mean()
        gate_rb[tk] = dict(n=len(m), lane=m['pnl_exec'].mean(), rnd=m['pnl_exec_rnd'].mean(), diff=diff.mean(), lo=lo, hi=hi, cost=cost)
        P(f"| 13:00 {tk} | {len(m)} | {m['pnl_exec'].mean():.2f} | {m['pnl_exec_rnd'].mean():.2f} | {diff.mean():.2f} | [{lo:.2f}, {hi:.2f}] | {cost:.2f} | {'yes' if diff.mean() > cost else 'no'} |")
    P('\nNote: a uniformly random RTH minute holds on average about 3 hours vs 2 h 55 min for the 13:00 entry, and sells more premium in the morning; it is a time-unmatched control, as specified.')
    # ---- 5. gate ----
    P('\n## 5. COMPASS §1 promotion gate, 13:00 SPY+QQQ lane (exec fills)\n')
    g = fixed.query("time=='13:00' and ticker!='IWM'"); s = summ(g, 'pnl_exec'); sne = summ(g[g['event'] == ''], 'pnl_exec')
    hs_med = g['hs_entry_pct_credit'].median(); hs_mean = g['hs_entry_pct_credit'].mean(); rt_med = g['hs_roundtrip_pct_credit'].median(); rt_mean = g['hs_roundtrip_pct_credit'].mean()
    rbq = gate_rb.get('SPY+QQQ')
    P('| criterion | value | verdict |\n|---|---|---|')
    P(f"| lower 95 % CI > 0 under executable fills (all days) | mean {s['mean']:.2f}, CI [{s['lo']:.2f}, {s['hi']:.2f}] | {'PASS' if s['lo'] > 0 else 'FAIL'} |")
    P(f"| same, skipping FOMC/CPI/NFP days (T-A spec) | n={sne['n']}, mean {sne['mean']:.2f}, CI [{sne['lo']:.2f}, {sne['hi']:.2f}] | {'PASS' if sne['lo'] > 0 else 'FAIL'} |")
    P(f"| realized half-spread <= 1.5 % of credit (entry side, straddle) | median {hs_med:.2f} %, mean {hs_mean:.2f} % of mid credit; round trip median {rt_med:.2f} %, mean {rt_mean:.2f} % | {'PASS' if hs_med <= 1.5 else 'FAIL'} (median entry side); round trip {'PASS' if rt_med <= 1.5 else 'FAIL'} |")
    P(f"| n >= 150 straddle-days and >= 3 months | n={s['n']} straddles on {s['dates']} dates, {s['months']} months | {'PASS' if s['n'] >= 150 and s['months'] >= 3 else 'FAIL'} |")
    if rbq: P(f"| beats the random-time baseline by more than one round-trip cost | difference {rbq['diff']:.2f} [{rbq['lo']:.2f}, {rbq['hi']:.2f}] vs cost {rbq['cost']:.2f} | {'PASS' if rbq['diff'] > rbq['cost'] else 'FAIL'} |")
    else: P('| beats the random-time baseline by more than one round-trip cost | baseline not available | n/a |')
    g3 = fixed.query("time=='13:00'"); s3 = summ(g3, 'pnl_exec'); su = summ(g3, 'uw_pnl_spread')
    P(f"\nModelled vs measured, 13:00 all three tickers (the modelled headline): modelled +{su['mean']:.2f} [{su['lo']:.2f}, {su['hi']:.2f}] vs executable {s3['mean']:.2f} [{s3['lo']:.2f}, {s3['hi']:.2f}] on the same {s3['n']} straddles "
      f"-> the modelled spread was {'OPTIMISTIC' if su['mean'] > s3['mean'] else 'PESSIMISTIC'} by {su['mean'] - s3['mean']:.2f} $ per straddle. SPY+QQQ: modelled {summ(g, 'uw_pnl_spread')['mean']:.2f} vs executable {s['mean']:.2f}.")
    open(HERE + '/RESULTS.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))

if __name__ == '__main__':
    main()
