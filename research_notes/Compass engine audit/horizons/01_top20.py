# Pick the top-20 optionable single names (plus the three ETFs) by option contract volume
# summed over the five ThetaData bulk option_eod days 2026-10-06..10-12. Index roots are
# excluded by requiring the root to exist in stock_eod of the same day.
import polars as pl, glob, json
S='/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/lake/flat'
days=sorted(glob.glob(f'{S}/option_eod/*.parquet'))
tot=None
for f in days:
    d=(pl.scan_parquet(f).select(['root','volume']).group_by('root').agg(pl.col('volume').sum().alias('v')).collect())
    tot=d if tot is None else pl.concat([tot,d]).group_by('root').agg(pl.col('v').sum())
stocks=set(pl.scan_parquet(f'{S}/stock_eod/2026-10-09.parquet').select('root').collect()['root'].to_list())
tot=tot.filter(pl.col('root').is_in(list(stocks))).sort('v',descending=True)
print(tot.head(40))
etf={'SPY','QQQ','IWM'}
names=[r for r in tot['root'].to_list() if r not in etf][:20]
print('TOP20', names)
json.dump({'days':[f.split('/')[-1] for f in days],'top20':names,'table':tot.head(40).to_dicts()},open('top20.json','w'),indent=1)
