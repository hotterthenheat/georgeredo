"""Study S17 (amendment A7): monthly put-writing and covered calls on SPY/QQQ, 2012-06 -> 2026-10, from the end-of-day
NBBO of each standard monthly expiration (s17_pull_monthly_chains.py). Usage: python3 s17_put_write.py"""
import datetime as dt, glob, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import greeks as g
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
HERE = os.path.dirname(os.path.abspath(__file__)); CACHE = os.path.join(SP, 'theta', 'fetch_cache', 'eod_monthly')
OUT = os.path.join(HERE, '..', 'results', 'v1', 's17_put_write'); os.makedirs(OUT, exist_ok=True)
FEE = 0.70; R = 0.02  # stated constant for implied vol / delta only (no rate series wired); P&L does not depend on it
rng = np.random.default_rng(7)

def day_frame(df, d):
    s = df.filter(pl.col('d') == d)
    c = s.filter(pl.col('right') == 'C').select(['strike', pl.col('bid').alias('cb'), pl.col('ask').alias('ca')])
    p = s.filter(pl.col('right') == 'P').select(['strike', pl.col('bid').alias('pb'), pl.col('ask').alias('pa')])
    return s, c.join(p, on='strike', how='inner')

def parity_spot(cp):
    """underlying from put-call parity at the strike where |C - P| is smallest (two-sided quotes only)"""
    q = cp.filter((pl.col('ca') > 0) & (pl.col('pa') > 0) & (pl.col('ca') >= pl.col('cb')) & (pl.col('pa') >= pl.col('pb')))
    if q.height == 0: return None
    q = q.with_columns(((pl.col('cb') + pl.col('ca')) / 2 - (pl.col('pb') + pl.col('pa')) / 2).alias('cmp')).with_columns((pl.col('strike') + pl.col('cmp')).alias('s'), pl.col('cmp').abs().alias('a')).sort('a')
    return float(q['s'][:3].median())

def cached_close(root, d):
    p = f'{SP}/theta/data/underlying/{root}/{d}.parquet'
    if not os.path.exists(p): return None
    b = pl.read_parquet(p).with_columns(pl.col('close').cast(pl.Float64, strict=False))
    b = b.filter(pl.col('close').is_not_null() & pl.col('close').is_not_nan())
    return float(b['close'][-1]) if b.height else None

def run_root(root):
    rows = []
    for f in sorted(glob.glob(f'{CACHE}/{root}/*.parquet')):
        if os.path.getsize(f) == 0: continue
        df = pl.read_parquet(f)
        if df.height == 0: continue
        df = df.with_columns(pl.col('created').dt.date().alias('d'), pl.col('right').cast(pl.Utf8).str.slice(0, 1), pl.col('strike').cast(pl.Float64))
        days = sorted(df['d'].unique().to_list()); entry, exitd = days[0], days[-1]
        exp = dt.date.fromisoformat(os.path.basename(f)[12:22])
        s0, cp0 = day_frame(df, entry); _, cp1 = day_frame(df, exitd)
        S0p, S1p = parity_spot(cp0), parity_spot(cp1)
        S0c, S1c = cached_close(root, entry), cached_close(root, exitd)
        S0 = S0c if S0c is not None else S0p; S1 = S1c if S1c is not None else S1p  # OCC references the 16:00 close
        if S0 is None or S1 is None: continue
        T = max((exp - entry).days, 1) / 365.25
        a = s0.filter((pl.col('bid') > 0) & (pl.col('ask') >= pl.col('bid')))
        K = a['strike'].to_numpy(); mid = ((a['bid'] + a['ask']) / 2).to_numpy(); rt = a['right'].to_numpy()
        iv = g.implied_vol(mid, S0, K, T, np.where(rt == 'C', 'CALL', 'PUT'), R, 0.0)
        de = np.abs(g.delta(S0, K, T, np.where(np.isnan(iv), 0.3, iv), np.where(rt == 'C', 'CALL', 'PUT'), R, 0.0))
        a = a.with_columns(pl.Series('delta', np.where(np.isnan(iv), np.nan, de)), pl.Series('iv', iv))
        puts = a.filter(pl.col('right') == 'P'); calls = a.filter(pl.col('right') == 'C')
        def near(fr, target): 
            x = fr.filter(pl.col('delta').is_not_nan()).with_columns((pl.col('delta') - target).abs().alias('_d')).sort('_d')
            return None if x.height == 0 else x.row(0, named=True)
        atm = puts.filter(pl.col('strike') <= S0).sort('strike', descending=True)
        legs = {'atm_put': atm.row(0, named=True) if atm.height else None, 'put_30d': near(puts, 0.30), 'put_15d': near(puts, 0.15), 'call_30d': near(calls, 0.30)}
        base = {'root': root, 'entry': entry, 'exit': exitd, 'expiration': exp, 'S0': S0, 'S1': S1, 'S1_parity': S1p, 'S1_source': 'close' if S1c is not None else 'parity', 'und_ret': S1 / S0 - 1, 'year': entry.year}
        for adv in (0.0, 0.01):
            for name in ('atm_put', 'put_30d', 'put_15d'):
                L = legs[name]
                if not L: continue
                credit = L['bid'] - adv; payoff = max(L['strike'] - S1, 0.0); pnl = (credit - payoff) * 100 - 2 * FEE
                rows.append({**base, 'structure': name, 'adverse': adv, 'strike': L['strike'], 'delta': L['delta'], 'iv': L['iv'], 'credit': credit, 'payoff': payoff, 'pnl': pnl, 'ret': pnl / (L['strike'] * 100), 'capital': L['strike'] * 100})
            sh, lg = legs['put_30d'], legs['put_15d']
            if sh and lg and lg['strike'] < sh['strike']:
                credit = (sh['bid'] - adv) - (lg['ask'] + adv); w = sh['strike'] - lg['strike']
                payoff = max(sh['strike'] - S1, 0.0) - max(lg['strike'] - S1, 0.0); pnl = (credit - payoff) * 100 - 4 * FEE
                rows.append({**base, 'structure': 'put_spread_30_15', 'adverse': adv, 'strike': sh['strike'], 'delta': sh['delta'], 'iv': sh['iv'], 'credit': credit, 'payoff': payoff, 'pnl': pnl, 'ret': pnl / (w * 100), 'capital': w * 100})
            c = legs['call_30d']
            if c:
                credit = c['bid'] - adv; payoff = max(S1 - c['strike'], 0.0); pnl_opt = (credit - payoff) * 100 - 2 * FEE
                pnl = pnl_opt + (S1 - S0) * 100
                rows.append({**base, 'structure': 'covered_call_30d', 'adverse': adv, 'strike': c['strike'], 'delta': c['delta'], 'iv': c['iv'], 'credit': credit, 'payoff': payoff, 'pnl': pnl, 'ret': pnl / (S0 * 100), 'capital': S0 * 100, 'option_pnl': pnl_opt})
    return rows

def boot(x, n=5000):
    x = np.asarray(x, float); idx = rng.integers(0, x.size, (n, x.size)); m = x[idx].mean(1)
    return float(x.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))

def ols_alpha(y, x, n=5000):
    y = np.asarray(y, float); x = np.asarray(x, float)
    def fit(yy, xx):
        X = np.column_stack([np.ones_like(xx), xx]); b = np.linalg.lstsq(X, yy, rcond=None)[0]; return b
    b = fit(y, x); idx = rng.integers(0, y.size, (n, y.size)); bs = np.array([fit(y[i], x[i]) for i in idx])
    return float(b[0]), float(np.percentile(bs[:, 0], 2.5)), float(np.percentile(bs[:, 0], 97.5)), float(b[1])

def curve(r):
    eq = np.cumprod(1 + np.asarray(r)); peak = np.maximum.accumulate(eq); return eq, float((eq / peak - 1).min())

rows = []
for root in ('SPY', 'QQQ'): rows += run_root(root)
df = pl.DataFrame(rows).sort(['root', 'structure', 'adverse', 'entry']); df.write_parquet(os.path.join(OUT, 'cycles.parquet'))
out = []; L = ['# S17 — monthly put-writing and covered calls on SPY and QQQ, 2012-06 → 2026-10 (amendment A7)', '',
 'Sell the next standard monthly at the closing bid on the roll date, hold to its last trading day, settle at intrinsic (underlying from put-call parity at the expiration-day close); $0.70/contract/leg both ways; no interest credited on collateral; buy-and-hold is price return (dividends excluded on both sides). CIs: bootstrap over cycles (5,000).', '',
 '| root | structure | fills | cycles | win | avg win % of credit | avg loss % of credit | mean $/contract [95 % CI] | mean edge (credit − payoff) % of credit | return/cycle | ann. return | ann. vol | Sharpe (no rf) | max DD | worst cycle | alpha/cycle vs underlying [CI] | beta | buy-and-hold ann. / Sharpe / max DD | sub-periods positive (of 5) |', '|' + '---|' * 19]
SUBS = [(2012, 2014), (2015, 2017), (2018, 2020), (2021, 2023), (2024, 2026)]
for (root, st, adv), g_ in df.group_by(['root', 'structure', 'adverse'], maintain_order=True):
    g_ = g_.sort('entry'); r = g_['ret'].to_numpy(); u = g_['und_ret'].to_numpy(); pnl = g_['pnl'].to_numpy(); cr = g_['credit'].to_numpy() * 100
    m, lo, hi = boot(pnl); edge = (g_['credit'] - g_['payoff']).to_numpy() * 100
    em, elo, ehi = boot(edge / np.maximum(cr, 1e-9) * 100)
    win = pnl > 0; aw = float(np.mean(pnl[win] / np.maximum(cr[win], 1e-9))) * 100 if win.any() else float('nan'); al = float(np.mean(pnl[~win] / np.maximum(cr[~win], 1e-9))) * 100 if (~win).any() else float('nan')
    eq, mdd = curve(r); yrs = (g_['exit'].max() - g_['entry'].min()).days / 365.25; ann = float(eq[-1] ** (1 / yrs) - 1); vol = float(np.std(r) * np.sqrt(12)); sh = float(np.mean(r) * 12 / vol) if vol > 0 else float('nan')
    ueq, umdd = curve(u); uann = float(ueq[-1] ** (1 / yrs) - 1); usharpe = float(np.mean(u) * 12 / (np.std(u) * np.sqrt(12)))
    al_, alo, ahi, beta = ols_alpha(r, u)
    subs = [float(g_.filter(pl.col('year').is_between(a_, b_))['pnl'].mean() or 0) for a_, b_ in SUBS]
    rec = {'root': root, 'structure': st, 'adverse': adv, 'n': g_.height, 'win_rate': float(win.mean()), 'avg_win_pct_credit': aw, 'avg_loss_pct_credit': al, 'mean_pnl': m, 'pnl_lo': lo, 'pnl_hi': hi, 'edge_pct_credit': em, 'edge_lo': elo, 'edge_hi': ehi, 'ret_per_cycle': float(np.mean(r)), 'ann_return': ann, 'ann_vol': vol, 'sharpe': sh, 'max_dd': mdd, 'worst_cycle': float(r.min()), 'alpha_per_cycle': al_, 'alpha_lo': alo, 'alpha_hi': ahi, 'beta': beta, 'bh_ann': uann, 'bh_sharpe': usharpe, 'bh_max_dd': umdd, 'subperiod_mean_pnl': subs, 'by_year_mean_pnl': {str(y['year']): round(y['pnl'], 1) for y in g_.group_by('year').agg(pl.col('pnl').mean()).sort('year').to_dicts()}}
    out.append(rec)
    if adv == 0.0:
        L.append(f"| {root} | {st} | {g_.height} | {g_.height} | {win.mean() * 100:.0f} % | {aw:+.0f} % | {al:+.0f} % | **{m:+.1f} [{lo:+.1f}, {hi:+.1f}]** | {em:+.1f} % [{elo:+.1f}, {ehi:+.1f}] | {np.mean(r) * 100:+.2f} % | {ann * 100:+.1f} % | {vol * 100:.1f} % | {sh:.2f} | {mdd * 100:.1f} % | {r.min() * 100:.1f} % | {al_ * 100:+.2f} % [{alo * 100:+.2f}, {ahi * 100:+.2f}] | {beta:.2f} | {uann * 100:+.1f} % / {usharpe:.2f} / {umdd * 100:.1f} % | {sum(1 for x in subs if x > 0)} |")
L += ['', '### One adverse tick per leg', '', '| root | structure | mean $/contract [CI] | alpha/cycle [CI] |', '|---|---|---|---|']
for o in out:
    if o['adverse'] > 0: L.append(f"| {o['root']} | {o['structure']} | {o['mean_pnl']:+.1f} [{o['pnl_lo']:+.1f}, {o['pnl_hi']:+.1f}] | {o['alpha_per_cycle'] * 100:+.2f} % [{o['alpha_lo'] * 100:+.2f}, {o['alpha_hi'] * 100:+.2f}] |")
L += ['', '### Mean $ per contract by year (no adverse tick)', '']
for o in out:
    if o['adverse'] == 0: L.append(f"- {o['root']} {o['structure']}: {o['by_year_mean_pnl']}")
open(os.path.join(OUT, 'REPORT.md'), 'w').write('\n'.join(L) + '\n'); json.dump(out, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)
# parity-spot measurement error where both exist (2017-06 ->)
c = df.filter((pl.col('structure') == 'atm_put') & (pl.col('adverse') == 0) & (pl.col('S1_source') == 'close') & pl.col('S1_parity').is_not_null())
err = ((c['S1_parity'] / c['S1'] - 1) * 1e4).to_numpy()
print('\n'.join(L)); print(f'parity vs 16:00 close at expiry: n {err.size}, mean {np.mean(err):+.1f} bp, median abs {np.median(np.abs(err)):.1f} bp, p95 abs {np.percentile(np.abs(err), 95):.1f} bp; cycles settled on parity: {df.filter((pl.col("structure") == "atm_put") & (pl.col("adverse") == 0) & (pl.col("S1_source") == "parity")).height}')
