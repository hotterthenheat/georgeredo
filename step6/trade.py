"""Step 6d, Part 3: trading the visible-before conditions without holding to the close (PREREG section 5).

1. The rules, chosen on Pick alone, mechanically (5.1): a condition is one Part 2 bucket (never "not available") with
   >= 300 Pick trades; a rule is one condition or two on different features (AND). Rules with >= 300 Pick trades on >= 60
   Pick dates are ranked by Pick lift: family A for R40 in H60, family B for R500 in H1530. The top three of each, skipping
   a rule on the same feature set as one already taken; ties to more trades.
2. Each rule buys every population trade that meets it; three exits (a), (b), (c) as build.py computed them (fees in).
3. Reported per rule x exit x period (rules.csv, results.csv): trades, win rate, average and median r, average win and
   loss, total $, the best 5 days' share of the total, without the best 5 days, the 20-session moving-block bootstrap 95%
   interval of the average r (audit_lib.session_stats, every date of the period, zero where no trade), and the rule's
   place among 500 random draws matched on cell (buy time x moneyness bin) counts (seed 20261023).
4. Pass (Check): average r > 0, interval lower end > 0, average above the 97.5th percentile of the random draws.
  python3 -I step6/trade.py
"""
import os, sys
import numpy as np, polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, 'research_notes', 'Compass phase 3', 'backtest_audit'))
from step6.data import load, OUT, WORK, FEATURES   # noqa: E402
import audit_lib                                     # noqa: E402

MIN_COND, MIN_RULE, MIN_DATES, TOP = 300, 300, 60, 3
FAMILIES = {'A': 'R40_60', 'B': 'R500_1530'}
EXITS = {'a': '+40% / -30% / out at 60 min or 3:30', 'b': '50% trail armed at +40%, out at 3:30', 'c': 'half at +40%, trail the rest 50%, out at 3:30'}
DRAWS, SEED = 500, 20261023

def choose(T, memb):
    pick = (T['period'] == 'pick').to_numpy()
    conds = []
    for f in FEATURES:
        v = memb[f].to_numpy()
        for b in sorted(set(v[pick])):
            if b == 'not available': continue
            m = v == b
            if (m & pick).sum() >= MIN_COND: conds.append((f, b, m))
    X = np.stack([c[2][pick] for c in conds], 1).astype(np.float32)        # Pick trades x conditions
    dates = T['date'].to_numpy()[pick]
    chosen = {}
    for fam, cls in FAMILIES.items():
        y = T[cls].cast(pl.Float64).to_numpy()[pick]
        b = T.filter(pl.col('period') == 'pick').group_by('cell').agg(pl.col(cls).cast(pl.Float64).mean().alias('_b'))
        e = T.filter(pl.col('period') == 'pick').select('cell').join(b, on='cell', how='left')['_b'].to_numpy()
        N = X.T @ X; O = X.T @ (X * y[:, None]); E = X.T @ (X * e[:, None])
        feat = np.array([c[0] for c in conds])
        cand = []
        nC = len(conds)
        iu = np.triu_indices(nC)
        for i, j in zip(*iu):
            if i != j and feat[i] == feat[j]: continue
            if N[i, j] < MIN_RULE or E[i, j] <= 0: continue
            cand.append((O[i, j] / E[i, j], N[i, j], i, j))
        cand.sort(key=lambda t: (-t[0], -t[1]))
        taken, sets = [], set()
        for lift, n, i, j in cand:
            fs = frozenset({feat[i], feat[j]})
            if fs in sets: continue
            m = X[:, i].astype(bool) & X[:, j].astype(bool)
            if np.unique(dates[m]).size < MIN_DATES: continue
            sets.add(fs)
            taken.append({'family': fam, 'target': cls, 'rank': len(taken) + 1,
                          'rule': conds[i][0] + ' = ' + conds[i][1] + ('' if i == j else ' AND ' + conds[j][0] + ' = ' + conds[j][1]),
                          'pick_trades': int(n), 'pick_dates': int(np.unique(dates[m]).size), 'pick_obs': int(O[i, j]), 'pick_exp': float(E[i, j]),
                          'pick_lift': float(lift), 'mask': conds[i][2] & conds[j][2]})
            if len(taken) == TOP: break
        chosen[fam] = taken
    return chosen, len(conds)

def stats(G, r, net, dates_all):
    """r, net: per trade; G: the trades (date column)"""
    n = len(r)
    o = {'trades': n}
    if n == 0: return o
    win = r > 0
    o.update(win_rate=float(win.mean()), avg_r=float(r.mean()), median_r=float(np.median(r)),
             avg_win=float(r[win].mean()) if win.any() else np.nan, avg_loss=float(r[~win].mean()) if (~win).any() else np.nan,
             total_usd=float(net.sum()))
    d = G['date'].to_numpy()
    daily = pl.DataFrame({'d': d, 'net': net, 'r': r}).group_by('d').agg(pl.col('net').sum(), pl.col('r').sum().alias('S'), pl.len().alias('N'))
    best = daily.sort('net', descending=True).head(5)
    o['best5_share'] = float(best['net'].sum() / net.sum()) if net.sum() > 0 else np.nan   # only meaningful for a profit
    rest = daily.filter(~pl.col('d').is_in(best['d'].to_list()))
    o['avg_r_without_best5'] = float(rest['S'].sum() / rest['N'].sum()) if rest['N'].sum() else np.nan
    o['days'] = daily.height; o['days_up'] = int((daily['net'] > 0).sum())
    S = np.zeros(len(dates_all)); N = np.zeros(len(dates_all))
    idx = {x: i for i, x in enumerate(dates_all)}
    for row in daily.iter_rows(named=True):
        S[idx[row['d']]] = row['S']; N[idx[row['d']]] = row['N']
    s = audit_lib.session_stats(S, N, blocks=(20,))
    o['ci_lo'], o['ci_hi'] = s.get('ci_trade_b20', (np.nan, np.nan))
    return o

def random_means(P, cellcounts, rs, seed):
    """DRAWS cell-matched draws without replacement from P; the mean r of each exit for each draw"""
    rng = np.random.default_rng(seed)
    cells = P['cell'].to_numpy()
    sums = {k: np.zeros(DRAWS) for k in rs}; tot = 0
    for c, k in sorted(cellcounts.items()):
        pool = np.nonzero(cells == c)[0]
        if k > pool.size: raise SystemExit(f'cell {c}: {k} wanted, {pool.size} in the pool')
        for d in range(DRAWS):
            pick = rng.choice(pool, size=k, replace=False)
            for x in rs: sums[x][d] += rs[x][pick].sum()
        tot += k
    return {x: sums[x] / tot for x in rs}

def main():
    T = load()
    memb = pl.read_parquet(os.path.join(WORK, 'membership.parquet'))
    if memb.height != T.height or not (memb['strike'] == T['strike']).all() or not (memb['session'] == T['session']).all() or not (memb['product'] == T['product']).all():
        raise SystemExit('membership rows do not line up with the trades')
    chosen, ncond = choose(T, memb)
    print('conditions:', ncond)
    rules, res = [], []
    for fam, taken in chosen.items():
        for t in taken:
            mask = t.pop('mask')
            rules.append(t)
            for per in ('pick', 'check'):
                ps = (T['period'] == per).to_numpy()
                P = T.filter(pl.col('period') == per)
                dates_all = sorted(set(P['date'].to_list()))
                G = T.filter(pl.Series(mask & ps))
                cc = dict(G.group_by('cell').len().iter_rows())
                # the rule's lift for its own target and for the other family's, in this period (base: this period's cells)
                for tgt in sorted(set(FAMILIES.values())):
                    b = P.group_by('cell').agg(pl.col(tgt).cast(pl.Float64).mean().alias('_b'))
                    ex = G.select('cell').join(b, on='cell', how='left')['_b'].sum()
                    t[f'{per}_{tgt}_rate'] = float(G[tgt].mean()); t[f'{per}_{tgt}_lift'] = float(G[tgt].sum() / ex)
                rs = {x: P[f'r_{x}'].to_numpy() for x in EXITS}
                rnd = random_means(P, cc, rs, SEED + 1000 * (ord(fam) - 64) + 10 * t['rank'] + (0 if per == 'pick' else 1))
                for x, lab in EXITS.items():
                    r = G[f'r_{x}'].to_numpy(); net = G[f'net_{x}'].to_numpy()
                    o = {'family': fam, 'rank': t['rank'], 'rule': t['rule'], 'exit': x, 'exit_rule': lab, 'period': per}
                    o.update(stats(G, r, net, dates_all))
                    rm = rnd[x]
                    o.update(random_mean=float(rm.mean()), random_p2_5=float(np.percentile(rm, 2.5)), random_p97_5=float(np.percentile(rm, 97.5)),
                             rule_percentile=float((rm < o.get('avg_r', np.nan)).mean() * 100))
                    o['passes'] = bool(per == 'check' and o.get('avg_r', -1) > 0 and o.get('ci_lo', -1) > 0 and o['avg_r'] > o['random_p97_5'])
                    res.append(o)
    pl.DataFrame(rules).write_csv(os.path.join(OUT, 'rules.csv'))
    for t in rules: print(t['family'], t['rank'], t['rule'], t['pick_trades'], {k: round(v, 3) for k, v in t.items() if k.endswith('_lift')})
    R = pl.DataFrame(res)
    R.write_csv(os.path.join(OUT, 'results.csv'))
    # every population trade with each exit, for scale
    base = []
    for per in ('pick', 'check'):
        P = T.filter(pl.col('period') == per); dates_all = sorted(set(P['date'].to_list()))
        for x, lab in EXITS.items():
            o = {'family': 'all', 'rank': 0, 'rule': 'every population trade', 'exit': x, 'exit_rule': lab, 'period': per}
            o.update(stats(P, P[f'r_{x}'].to_numpy(), P[f'net_{x}'].to_numpy(), dates_all)); base.append(o)
    pl.DataFrame(base).write_csv(os.path.join(OUT, 'results_all.csv'))
    pl.Config.set_tbl_cols(30); pl.Config.set_tbl_width_chars(250); pl.Config.set_tbl_rows(60)
    print(R.select('family', 'rank', 'exit', 'period', 'trades', 'win_rate', 'avg_r', 'median_r', 'ci_lo', 'ci_hi', 'best5_share', 'random_mean', 'random_p97_5', 'rule_percentile', 'passes'))

if __name__ == '__main__':
    main()
