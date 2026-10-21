"""Hypothesis F: re-derive 50 random flies (from out/flies_fit.parquet and out/flies_oos.parquet together) from the RAW
chain and underlying files with plain row-by-row loops - no polars expressions, no shared helper beyond the file paths
and the constants - and count the differences against the stored rows and the fill model's P&L.

Checked per fly: spot at the entry minute, K0, each leg's bid / ask / bid_size / ask_size, the NBBO debit (or credit),
the mid debit (or credit), the settlement payoff, the P&L at k = 0, at k = 0.5 and at the $0.01-a-leg stress (the
latter two recomputed here from the plain-loop legs and compared with run.py's priced() on the stored row).
Tolerance 1e-6 on prices, exact on strikes and sizes.
  nice -n 10 env POLARS_MAX_THREADS=1 python3 -I verify.py      (SEED=... for another draw)
"""
import os, sys, random, json
import polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
FEE = 0.65; W = 5.0
SEED = int(os.environ.get('SEED', '20261021'))
random.seed(SEED)

def minute(ts): return ts.hour * 60 + ts.minute - 570

def chain_at(root, d, m):
    """{(strike, right): (bid, ask, bid_size, ask_size)} at minute m, with the validity rule, plain python."""
    out = {}
    for r in pl.read_parquet(f'{RAW}/data_full/chains/{root}/{d}.parquet').iter_rows(named=True):
        if minute(r['timestamp']) != m: continue
        b, a = r['bid'], r['ask']
        if b is None or a is None or a < b or b < 0 or a <= 0: continue
        out[(float(r['strike']), r['right'])] = (float(b), float(a), int(r['bid_size']), int(r['ask_size']))
    return out

def spot_and_close(root, d, m):
    """spot at quote minute m = close of the bar stamped m-1; settlement = close of the bar stamped 389 (15:59), else the last close."""
    closes = {}
    for r in pl.read_parquet(f'{RAW}/data/underlying/{root}/{d}.parquet').iter_rows(named=True):
        if r['close'] is None: continue
        closes[minute(r['timestamp'])] = float(r['close'])
    spot = closes.get(m - 1)
    sc = closes[389] if 389 in closes else closes[max(k for k in closes if k <= 389)]
    return spot, sc

def intr(S, K, right): return max(S - K, 0.0) if right == 'CALL' else max(K - S, 0.0)

def check(row):
    root, d, m, form, K0 = row['product'], row['session'], int(row['m']), row['form'], float(row['K0'])
    q = chain_at(root, d, m); S, sc = spot_and_close(root, d, m)
    diffs = []
    if S is None or abs(S - row['spot']) > 1e-6: diffs.append(f'spot {S} vs {row["spot"]}')
    if abs(sc - row['spot_close']) > 1e-6: diffs.append(f'close {sc} vs {row["spot_close"]}')
    both = sorted({k for (k, r) in q if (k, 'CALL') in q and (k, 'PUT') in q})
    k0 = min(both, key=lambda k: (abs(k - S), k))
    if k0 != K0: diffs.append(f'K0 {k0} vs {K0}')
    lo, hi = k0 - W, k0 + W
    if form == 'call':
        legs = [(lo, 'CALL', 1, True), (k0, 'CALL', 2, False), (hi, 'CALL', 1, True)]
        pay = intr(sc, lo, 'CALL') - 2 * intr(sc, k0, 'CALL') + intr(sc, hi, 'CALL')
    elif form == 'put':
        legs = [(lo, 'PUT', 1, True), (k0, 'PUT', 2, False), (hi, 'PUT', 1, True)]
        pay = intr(sc, lo, 'PUT') - 2 * intr(sc, k0, 'PUT') + intr(sc, hi, 'PUT')
    else:
        legs = [(lo, 'PUT', 1, True), (k0, 'CALL', 1, False), (k0, 'PUT', 1, False), (hi, 'CALL', 1, True)]
        pay = -intr(sc, k0, 'CALL') - intr(sc, k0, 'PUT') + intr(sc, lo, 'PUT') + intr(sc, hi, 'CALL')
    nbbo = 0.0; mid = 0.0
    for i, (K, right, lots, long) in enumerate(legs):
        if (K, right) not in q: diffs.append(f'leg {i} {K} {right} not quoted'); continue
        b, a, bs, as_ = q[(K, right)]
        for name, val in (('K', K), ('side', right), ('lots', lots), ('long', long), ('bid', b), ('ask', a), ('bid_size', bs), ('ask_size', as_)):
            have = row[f'l{i}_{name}']
            if isinstance(val, float) and abs(val - have) > 1e-6 or not isinstance(val, float) and val != have: diffs.append(f'leg {i} {name} {val} vs {have}')
        nbbo += lots * (a if long else -b); mid += lots * ((a + b) / 2 if long else -(a + b) / 2)
    if abs(pay - row['payoff']) > 1e-6: diffs.append(f'payoff {pay} vs {row["payoff"]}')
    if form == 'iron':
        credit, credit_mid = -nbbo, -mid
        if abs(credit - row['credit_nbbo']) > 1e-6: diffs.append(f'credit {credit} vs {row["credit_nbbo"]}')
        if abs(credit_mid - row['credit_mid']) > 1e-6: diffs.append(f'credit_mid {credit_mid} vs {row["credit_mid"]}')
        if abs((W - credit) - row['risk_nbbo']) > 1e-6: diffs.append(f'risk {W - credit} vs {row["risk_nbbo"]}')
        pnl0 = (credit + pay) * 100 - 4 * FEE
        pnl_k5 = (credit + 0.5 * (credit_mid - credit) + pay) * 100 - 4 * FEE
        pnl_s1 = (credit - 0.04 + pay) * 100 - 4 * FEE
    else:
        if abs(nbbo - row['debit_nbbo']) > 1e-6: diffs.append(f'debit {nbbo} vs {row["debit_nbbo"]}')
        if abs(mid - row['debit_mid']) > 1e-6: diffs.append(f'debit_mid {mid} vs {row["debit_mid"]}')
        if abs(nbbo - row['risk_nbbo']) > 1e-6: diffs.append(f'risk {nbbo} vs {row["risk_nbbo"]}')
        pnl0 = (pay - nbbo) * 100 - 4 * FEE
        pnl_k5 = (pay - (nbbo - 0.5 * (nbbo - mid))) * 100 - 4 * FEE
        pnl_s1 = (pay - (nbbo + 0.04)) * 100 - 4 * FEE
    if abs((nbbo - mid) - row['slip']) > 1e-6: diffs.append(f'slip {nbbo - mid} vs {row["slip"]}')
    if abs(pnl0 - row['pnl_nbbo']) > 1e-6: diffs.append(f'pnl0 {pnl0} vs {row["pnl_nbbo"]}')
    # the fill model as run.py prices it on the stored row
    sys.path.insert(0, HERE)
    from run import priced
    g = pl.DataFrame([row])
    p_k5 = float(priced(g, 0.5, 0.0)[0][0]); p_s1 = float(priced(g, 0.0, 0.01)[0][0])
    if abs(pnl_k5 - p_k5) > 1e-6: diffs.append(f'pnl k=0.5 {pnl_k5} vs run.py {p_k5}')
    if abs(pnl_s1 - p_s1) > 1e-6: diffs.append(f'pnl stress 1c {pnl_s1} vs run.py {p_s1}')
    return diffs

def main():
    F = pl.concat([pl.read_parquet(os.path.join(OUT, 'flies_fit.parquet')), pl.read_parquet(os.path.join(OUT, 'flies_oos.parquet'))], how='vertical_relaxed')
    idx = random.sample(range(F.height), 50)
    n_diff = 0; report = []
    for i in idx:
        row = F.row(i, named=True); d = check(row)
        n_diff += bool(d); report.append(dict(product=row['product'], session=row['session'], t=row['t'], form=row['form'], diffs=d))
        print(row['product'], row['session'], row['t'], row['form'], 'OK' if not d else d, flush=True)
    print('flies checked 50, with differences:', n_diff)
    with open(os.path.join(OUT, 'verify.json'), 'w') as f: json.dump(dict(seed=SEED, checked=50, differing=n_diff, rows=report), f, indent=1)

if __name__ == '__main__':
    main()
