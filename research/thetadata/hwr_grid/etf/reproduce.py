"""Sanity check (PREREGISTRATION.md §9): recompute the published T-A lane of research/thetadata/straddle_nbbo/RESULTS.md
(13:00 SPY+QQQ ATM straddle, sell both legs at the BID at 13:00, buy both back at the ASK at 15:55, $0.70 per contract per side,
2025-06-02 -> 2026-10-09; published +$8.60 [-6.07, 22.45], n = 678) from the local dataset.
(a) strikes of the published study (csv/straddles_nbbo.csv.gz, time 13:00); (b) this study's ATM rule (stored strike nearest to the
close of the 12:59 bar).  Writes results/reproduction.csv and results/reproduction.md."""
import os, sys, gzip, csv
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

PRIOR = os.path.join(C.REPO, 'research', 'thetadata', 'straddle_nbbo', 'csv', 'straddles_nbbo.csv.gz')


def one(arr, K, T=780, X=C.CLOSE_M):
    ks = arr['strikes']; i = np.where(np.isclose(ks, K))[0]
    if len(i) == 0: return None, 'strike_not_stored'
    i = int(i[0]); t = T - C.M0; x = X - C.M0
    if not (arr['ok'][0, i, t] and arr['ok'][1, i, t]): return None, 'no_quote'
    cb, pb = arr['bid'][0, i, t], arr['bid'][1, i, t]
    if cb <= 0 or pb <= 0: return None, 'zero_bid'
    ca, pa = arr['aff'][0, i, x], arr['aff'][1, i, x]
    if not (np.isfinite(ca) and np.isfinite(pa)): return None, 'no_exit'
    return round((cb + pb - ca - pa) * 100 - 4 * C.FEE, 2), None


def main():
    os.makedirs(C.OUT, exist_ok=True)
    prior = [r for r in csv.DictReader(gzip.open(PRIOR, 'rt')) if r['time'] == '13:00' and r['ticker'] in ('SPY', 'QQQ')]
    rows = []; skipped = {}
    cache = {}
    for r in sorted(prior, key=lambda r: (r['date'], r['ticker'])):
        tk, d = r['ticker'], r['date']
        if (tk, d) not in cache: cache[(tk, d)] = C.day_arrays(tk, d)
        arr = cache[(tk, d)]
        if arr is None: skipped['no_file'] = skipped.get('no_file', 0) + 1; continue
        pa, why = one(arr, float(r['strike']))
        S = C.last_close_before(arr['close'], 780 - C.M0)
        k0 = float(arr['strikes'][np.argmin(np.abs(arr['strikes'] - S))])
        if arr['strikes'].min() <= S <= arr['strikes'].max(): pb, whyb = one(arr, k0)
        else: pb, whyb = None, 'out_of_band'      # PREREGISTRATION.md amendment A1
        rows.append(dict(date=d, ticker=tk, strike_prior=float(r['strike']), pnl_prior=float(r['pnl_exec']), pnl_a=pa, why_a=why or '',
                         strike_b=k0, pnl_b=pb, why_b=whyb or ''))
    with open(os.path.join(C.OUT, 'reproduction.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    out = ['# Reproduction of the published T-A lane (13:00 SPY+QQQ ATM straddle, NBBO, close 15:55)\n',
           'Published (research/thetadata/straddle_nbbo/RESULTS.md): n = 678, mean +$8.60, 95 % CI [-6.07, 22.45], win 64.7 %.\n',
           '| variant | n | mean $ | 95 % CI (date clusters, 5,000 draws, seed 7) | win | rows equal to the published P&L (±$0.01) |', '|---|---|---|---|---|---|']
    v = [(x['date'], x['pnl_prior']) for x in rows if x['pnl_a'] is not None]
    p = np.array([b for _, b in v]); lo, hi = C.boot_ci(p, [a for a, _ in v])
    pub_same = f'| published per-row P&L on the rows of (a) | {len(p)} | {p.mean():+.2f} | [{lo:.2f}, {hi:.2f}] | {100 * (p > 0).mean():.1f} % | {len(p)} |'
    for lab, col in (('published strikes, this dataset', 'pnl_a'), ('this study\'s ATM rule (nearest stored strike to the 12:59 close)', 'pnl_b'), ('published per-row P&L (check)', 'pnl_prior')):
        v = [(x['date'], x[col]) for x in rows if x[col] is not None]
        p = np.array([b for _, b in v]); lo, hi = C.boot_ci(p, [a for a, _ in v])
        eq = sum(1 for x in rows if x[col] is not None and abs(x[col] - x['pnl_prior']) <= 0.011)
        out.append(f'| {lab} | {len(p)} | {p.mean():+.2f} | [{lo:.2f}, {hi:.2f}] | {100 * (p > 0).mean():.1f} % | {eq} |')
    out.append(pub_same)
    nb = sum(1 for x in rows if x['strike_b'] != x['strike_prior'])
    out.append(f'\nStrike differences between the two ATM rules: {nb} of {len(rows)} rows.  Skips: '
               f'{ {k: sum(1 for x in rows if x["why_a"] == k) for k in set(x["why_a"] for x in rows) if k} or "none"} (a), '
               f'{ {k: sum(1 for x in rows if x["why_b"] == k) for k in set(x["why_b"] for x in rows) if k} or "none"} (b).')
    diffs = [abs(x['pnl_a'] - x['pnl_prior']) for x in rows if x['pnl_a'] is not None]
    out.append(f'Max |row difference| (a vs published): ${max(diffs):.2f}; rows differing by more than $0.01: {sum(1 for z in diffs if z > 0.011)}.')
    open(os.path.join(C.OUT, 'reproduction.md'), 'w').write('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
