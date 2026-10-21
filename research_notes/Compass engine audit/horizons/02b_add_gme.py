# SPCX (SpaceX) listed in 2026 and has no 2022-2024 history: substitute the 21st name by option volume, GME.
import polars as pl, glob, json
REPO='/home/user/georgeredo'
parts=[]
for f in sorted(glob.glob(f'{REPO}/data_lake/thetadata/stock_eod/year=*/*.parquet')):
    d=pl.scan_parquet(f).select(['symbol','last_trade','open','high','low','close','volume']).filter(pl.col('symbol')=='GME').collect()
    if d.height: parts.append(d)
g=pl.concat(parts).with_columns(pl.col('last_trade').dt.date().alias('date')).drop('last_trade').with_columns(pl.lit(0,dtype=pl.Int64).alias('nbars'))
b=pl.read_parquet('bars.parquet')
g=g.select(b.columns).sort('date').unique(['symbol','date'],keep='first')
b=pl.concat([b.filter(pl.col('symbol')!='SPCX'),g]).sort(['symbol','date'])
b.write_parquet('bars.parquet')
t=json.load(open('top20.json')); t['top20_used']=[x for x in t['top20'] if x!='SPCX']+['GME']; t['note']='SPCX (SpaceX, listed 2026) replaced by GME, the 21st name by option volume'
json.dump(t,open('top20.json','w'),indent=1)
print(b.group_by('symbol').agg(pl.col('date').min().alias('mn'),pl.col('date').max().alias('mx'),pl.len()).sort('symbol'))
