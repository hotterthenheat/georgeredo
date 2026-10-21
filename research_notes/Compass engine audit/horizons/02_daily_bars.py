# Build the daily-bar panel: SPY/QQQ/IWM from the 1-minute regular-session files (2012-06 -> 2026-10-09),
# the 20 names from data_lake/thetadata/stock_eod parts (2020 -> 2026-10-13). Output: bars.parquet
import polars as pl, glob, json, sys, os
S='/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta/data/underlying'
REPO='/home/user/georgeredo'
top=json.load(open('top20.json'))['top20']
out=[]
import polars as pl
for sym in ['SPY','QQQ','IWM']:
    rows=[]
    for f in sorted(glob.glob(f'{S}/{sym}/*.parquet')):
        d=pl.read_parquet(f,columns=['timestamp','open','high','low','close','volume'])
        d=d.filter((pl.col('timestamp').dt.time()>=pl.time(9,30))&(pl.col('timestamp').dt.time()<=pl.time(16,0))).filter(pl.col('close').is_not_nan()&pl.col('open').is_not_nan()&(pl.col('close')>0))
        if d.height<100: continue
        rows.append({'symbol':sym,'date':os.path.basename(f)[:10],'open':d['open'][0],'high':d['high'].max(),'low':d['low'].min(),'close':d['close'][-1],'volume':int(d['volume'].sum()),'nbars':d.height})
    out.append(pl.DataFrame(rows).with_columns(pl.col('nbars').cast(pl.Int64),pl.col('volume').cast(pl.Int64)))
    print(sym,len(rows),file=sys.stderr)
etf=pl.concat(out).with_columns(pl.col('date').str.to_date())
parts=[]
for f in sorted(glob.glob(f'{REPO}/data_lake/thetadata/stock_eod/year=*/*.parquet')):
    d=pl.scan_parquet(f).select(['symbol','last_trade','open','high','low','close','volume']).filter(pl.col('symbol').is_in(top)).collect()
    if d.height: parts.append(d)
nm=pl.concat(parts).with_columns(pl.col('last_trade').dt.date().alias('date')).drop('last_trade').with_columns(pl.lit(0,dtype=pl.Int64).alias('nbars'))
nm=nm.select(etf.columns).sort(['symbol','date']).unique(['symbol','date'],keep='first')
bars=pl.concat([etf,nm]).sort(['symbol','date'])
bars.write_parquet('bars.parquet')
print(bars.group_by('symbol').agg(pl.col('date').min(),pl.col('date').max(),pl.len()).sort('symbol'))
