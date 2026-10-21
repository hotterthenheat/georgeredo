import polars as pl, json
pl.Config.set_tbl_rows(60); pl.Config.set_tbl_cols(20); pl.Config.set_fmt_str_lengths(40)
REPO='/home/user/georgeredo'
top=json.load(open('top20.json'))['top20']; U=top+['SPY','QQQ','IWM']
info=pl.read_parquet(f'{REPO}/data_lake/unusualwhales/info.parquet').filter(pl.col('ticker').is_in(U)).select(['ticker','full_name','issue_type','sector','has_options','next_earnings_date','avg30_volume'])
pass
e=pl.read_parquet(f'{REPO}/data_lake/unusualwhales/earnings.parquet')
print('earnings rows',e.height,'tickers',e['ticker'].n_unique())
print(e['report_type'].value_counts())
print(e.select(pl.col('report_date').min().alias('mn'),pl.col('report_date').max().alias('mx')))
eu=e.filter(pl.col('ticker').is_in(U))
print(eu.group_by('ticker').agg(pl.col('report_date').min().alias('mn'),pl.col('report_date').max().alias('mx'),pl.len(), pl.col('report_time').drop_nulls().len().alias('with_time')).sort('ticker'))
print(eu.filter(pl.col('ticker')=='AAPL').sort('report_date').select(['report_date','report_type','report_time','reported_eps','estimated_eps']))
# by year
print(e.with_columns(pl.col('report_date').str.slice(0,4).alias('y')).group_by('y').agg(pl.len(),pl.col('report_time').drop_nulls().len().alias('with_time'),pl.col('reported_eps').drop_nulls().len().alias('with_eps')).sort('y'))
iv=pl.read_parquet(f'{REPO}/data_lake/unusualwhales/iv-rank__1y.parquet').filter(pl.col('ticker').is_in(U))
print(iv.group_by('ticker').agg(pl.col('date').min().alias('mn'),pl.col('date').max().alias('mx'),pl.len(),pl.col('volatility').cast(pl.Float64).median().alias('med_iv')).sort('ticker'))
rv=pl.read_parquet(f'{REPO}/data_lake/unusualwhales/volatility__realized.parquet').filter(pl.col('ticker').is_in(U))
print(rv.group_by('ticker').agg(pl.col('date').min().alias('mn'),pl.col('date').max().alias('mx'),pl.len(),pl.col('implied_volatility').cast(pl.Float64).median().alias('med_iv'),pl.col('realized_volatility').cast(pl.Float64).median().alias('med_rv')).sort('ticker'))
