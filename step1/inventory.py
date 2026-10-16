"""Step 1a: what raw same-day (0DTE) option data exists for SPY, QQQ, IWM and SPX (root SPXW), session by session.

Reads only raw vendor files (ThetaData one-minute NBBO chains and one-minute prices, kept outside the repository in
the session scratchpad; RAW below). Writes step1/out/inventory.parquet (one row per product and session) and prints
the coverage and every gap.
  python3 -I step1/inventory.py
"""
import datetime as dt, os, sys
import polars as pl

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out'); os.makedirs(OUT, exist_ok=True)
PRODUCTS = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}     # option root -> underlying

def underlying_path(u, d):
    return os.path.join(RAW, 'data', 'index' if u == 'SPX' else 'underlying', u, f'{d}.parquet')

def sessions(u):
    """trading sessions: a price file with at least one price (the vendor also writes empty files for market holidays)"""
    d = os.path.join(RAW, 'data', 'index' if u == 'SPX' else 'underlying', u)
    col = 'price' if u == 'SPX' else 'close'
    out = []
    for f in sorted(os.listdir(d)):
        if f.endswith('.parquet') and pl.read_parquet(os.path.join(d, f), columns=[col])[col].drop_nulls().len() > 0: out.append(dt.date.fromisoformat(f[:10]))
    return out

rows = []
for root, u in PRODUCTS.items():
    cdir = os.path.join(RAW, 'data_full', 'chains', root)
    chain_days = sorted(dt.date.fromisoformat(f[:10]) for f in os.listdir(cdir) if f.endswith('.parquet'))
    first, last = chain_days[0], chain_days[-1]
    ss = sessions(u)
    for d in [s for s in ss if first <= s <= last] + [c for c in chain_days if c not in set(ss)]:
        r = dict(product=root, underlying=u, session=d, chain=False, underlying_prices=os.path.exists(underlying_path(u, d)))
        p = os.path.join(cdir, f'{d}.parquet')
        if os.path.exists(p):
            c = pl.read_parquet(p, columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
            two = c.filter(pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')))
            r.update(chain=True, rows=c.height, strikes=c['strike'].n_unique(), contracts=c.select('strike', 'right').unique().height,
                     contracts_quoted=two.select('strike', 'right').unique().height,
                     first_minute=str(c['timestamp'].min().time()), last_minute=str(c['timestamp'].max().time()), minutes=c['timestamp'].n_unique(),
                     kmin=float(c['strike'].min()), kmax=float(c['strike'].max()))
        rows.append(r)
I = pl.DataFrame(rows, infer_schema_length=None).sort('product', 'session')
I.write_parquet(os.path.join(OUT, 'inventory.parquet'))
pl.Config.set_tbl_cols(14); pl.Config.set_tbl_width_chars(220); pl.Config.set_tbl_rows(40)
print(I.group_by('product').agg(pl.col('session').min().alias('first'), pl.col('session').max().alias('last'), pl.len().alias('sessions_in_window'),
      pl.col('chain').sum().alias('with_chain'), (~pl.col('chain')).sum().alias('no_chain'), pl.col('underlying_prices').sum().alias('with_prices'),
      pl.col('contracts').sum().alias('contracts'), pl.col('contracts_quoted').sum().alias('contracts_quoted'), pl.col('strikes').median().alias('strikes_median'),
      pl.col('minutes').min().alias('min_minutes'), pl.col('minutes').max().alias('max_minutes')).sort('product'))
print('sessions in the window with no same-day chain:'); print(I.filter(~pl.col('chain')).select('product', 'session').group_by('product').agg(pl.col('session')))
print('chains whose minutes are not 391 (09:30-16:00):'); print(I.filter(pl.col('chain') & (pl.col('minutes') != 391)).select('product', 'session', 'minutes', 'first_minute', 'last_minute'))
print('chains without underlying prices:'); print(I.filter(pl.col('chain') & ~pl.col('underlying_prices')).select('product', 'session'))
