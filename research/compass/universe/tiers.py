"""Point-in-time liquidity tiers per calendar year (04_protocol.md §3): rank the roots optionable in year Y by the median
daily dollar volume of the underlying over year Y-1 (ThetaData stock EOD in the data lake), using only data from Y-1.
Tier A = top 100, B = 101-500, C = 501-1000, plus the index/ETF group. Writes data_lake/universe/tiers.parquet and
tiers_summary.json. Years whose Y-1 bars are not yet in the lake are skipped and listed."""
import datetime as dt, glob, gzip, json, os, sys
import polars as pl
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
LAKE = os.path.join(ROOT, 'data_lake', 'thetadata', 'stock_eod')
UNI = os.path.join(ROOT, 'data_lake', 'universe')
INDEX_GROUP = ['SPY', 'QQQ', 'IWM', 'DIA', 'SPXW', 'RUTW', 'SPX', 'RUT']

def load_year(y: int) -> pl.DataFrame:
    files = sorted(glob.glob(os.path.join(LAKE, f'year={y}', 'part-*.parquet')))
    if not files: return pl.DataFrame()
    frames = [pl.read_parquet(f, columns=['symbol', 'created', 'close', 'volume']) for f in files]
    df = pl.concat([f for f in frames if f.height], how='vertical_relaxed')
    return df.with_columns([pl.col('created').dt.date().alias('date'), (pl.col('close') * pl.col('volume')).alias('dollar_volume')])

def expirations():
    out = {}
    with gzip.open(os.path.join(UNI, 'expirations.jsonl.gz'), 'rt') as fh:
        for line in fh:
            r = json.loads(line)
            if r.get('n'): out[r['root']] = (dt.date.fromisoformat(r['first']), dt.date.fromisoformat(r['last']))
    return out

def main():
    exp = expirations()
    rows, summary = [], {}
    years = sorted({int(os.path.basename(p).split('=')[1]) for p in glob.glob(os.path.join(LAKE, 'year=*'))})
    for y in years:
        prev = load_year(y - 1)
        if prev.height == 0: summary[str(y)] = 'skipped: year %d bars not in the lake' % (y - 1); continue
        if prev['date'].n_unique() < 200: summary[str(y)] = 'skipped: year %d incomplete (%d sessions)' % (y - 1, prev['date'].n_unique()); continue
        agg = prev.group_by('symbol').agg([pl.col('dollar_volume').median().alias('med_dollar_vol'), pl.col('date').n_unique().alias('sessions')])
        y0, y1 = dt.date(y, 1, 1), dt.date(y, 12, 31)
        # optionable in year Y: a listed expiration on or after Jan 1 of Y and the root's first expiration before the end of Y
        opt = {r for r, (f, l) in exp.items() if f <= y1 and l >= y0}
        agg = agg.filter(pl.col('symbol').is_in(list(opt)) & (pl.col('sessions') >= 100)).sort('med_dollar_vol', descending=True).with_row_index('rank', offset=1)
        agg = agg.with_columns(pl.when(pl.col('rank') <= 100).then(pl.lit('A')).when(pl.col('rank') <= 500).then(pl.lit('B')).when(pl.col('rank') <= 1000).then(pl.lit('C')).otherwise(pl.lit('D')).alias('tier'))
        agg = agg.with_columns(pl.lit(y).alias('year'))
        rows.append(agg)
        summary[str(y)] = {'optionable_roots_with_bars': agg.height, 'tier_A_min_med_dollar_vol': float(agg.filter(pl.col('tier') == 'A')['med_dollar_vol'].min()),
                           'tier_B_min': float(agg.filter(pl.col('tier') == 'B')['med_dollar_vol'].min()) if agg.filter(pl.col('tier') == 'B').height else None,
                           'tier_C_min': float(agg.filter(pl.col('tier') == 'C')['med_dollar_vol'].min()) if agg.filter(pl.col('tier') == 'C').height else None,
                           'top_10': agg.head(10)['symbol'].to_list(), 'index_group_present': [s for s in INDEX_GROUP if s in set(agg['symbol'].to_list())]}
    if rows:
        out = pl.concat(rows)
        out.write_parquet(os.path.join(UNI, 'tiers.parquet'))
    json.dump(summary, open(os.path.join(UNI, 'tiers_summary.json'), 'w'), indent=1)
    print(json.dumps(summary, indent=1))

if __name__ == '__main__': main()
