"""Inventory of the on-disk caches the lifecycle research can read without a vendor call (2026-10-15).
Per dataset and root: files, bytes, first and last session, and for the option-minute stores a quality pass over a
sample of files (rows, contract count, share of minutes with a two-sided quote, crossed or locked quotes, median
relative spread near the money). Writes local_inventory.json."""
import os, sys, json, glob, random, re
import polars as pl
SP = sys.argv[1]
T = f'{SP}/theta'
sets = {
    '0dte_chains (1m NBBO, every strike, same-day expiration)': (f'{T}/data_full/chains', r'(\d{4}-\d{2}-\d{2})\.parquet'),
    'weekly_chains (1m NBBO, every strike, one expiration a day)': (f'{T}/fetch_cache/chains_exp', r'(\d{4}-\d{2}-\d{2})__(\d{4}-\d{2}-\d{2})\.parquet'),
    'weekly_ohlc (1m OHLCV per contract)': (f'{T}/fetch_cache/ohlc_exp', r'(\d{4}-\d{2}-\d{2})__(\d{4}-\d{2}-\d{2})\.parquet'),
    'open_interest (per contract-day)': (f'{T}/fetch_cache/oi', r'(\d{4}-\d{2}-\d{2})__(\d{4}-\d{2}-\d{2})\.parquet'),
    'monthly_eod (option EOD + closing NBBO, monthly cycles)': (f'{T}/fetch_cache/eod_monthly', r'(\d{4}-\d{2}-\d{2})__(\d{4}-\d{2}-\d{2})\.parquet'),
    'event_eod (option EOD + closing NBBO, single-name events)': (f'{T}/fetch_cache/eod_exp', r'(\d{4}-\d{2}-\d{2})__(\d{4}-\d{2}-\d{2})\.parquet'),
    'underlying_1m (stock/ETF 1m OHLCV)': (f'{T}/fetch_cache/underlying', r'(\d{4}-\d{2}-\d{2})\.parquet'),
    'index_underlying_1m (SPY/QQQ/IWM 1m OHLCV)': (f'{T}/data/underlying', r'(\d{4}-\d{2}-\d{2})'),
    'index_1m (SPX, VIX)': (f'{T}/data/index', r'(\d{4}-\d{2}-\d{2})'),
}
out = {}
for name, (root_dir, rx) in sets.items():
    roots = {}
    for r in sorted(os.listdir(root_dir)) if os.path.isdir(root_dir) else []:
        files = [f for f in glob.glob(f'{root_dir}/{r}/**/*', recursive=True) if os.path.isfile(f) and not f.endswith('.nodata')]
        dates = sorted(m.group(1) for f in files if (m := re.search(rx, os.path.basename(f))))
        if not files: continue
        roots[r] = {'files': len(files), 'bytes': sum(os.path.getsize(f) for f in files), 'first': dates[0] if dates else None, 'last': dates[-1] if dates else None, 'sessions': len(set(dates))}
    out[name] = {'dir': root_dir.replace(SP, '$SP'), 'roots': roots, 'total_bytes': sum(v['bytes'] for v in roots.values()), 'total_files': sum(v['files'] for v in roots.values())}
    print(name, len(roots), 'roots', round(out[name]['total_bytes'] / 1e9, 2), 'GB', flush=True)
# quality pass on the minute NBBO stores
random.seed(7)
def quality(files, k):
    agg = []
    for f in random.sample(files, min(k, len(files))):
        df = pl.read_parquet(f)
        if df.height == 0: continue
        two = df.filter(pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') > 0))
        crossed = two.filter(pl.col('bid') > pl.col('ask')).height
        locked = two.filter((pl.col('bid') == pl.col('ask')) & (pl.col('bid') > 0)).height
        zero_bid = two.filter(pl.col('bid') <= 0).height
        live = two.filter(pl.col('bid') > 0)
        rel = live.with_columns(((pl.col('ask') - pl.col('bid')) / ((pl.col('ask') + pl.col('bid')) / 2)).alias('rs'))
        # contracts priced 0.20-5.00 as a near-the-money proxy that needs no underlying
        ntm = rel.filter((pl.col('bid') + pl.col('ask')) / 2 >= 0.2).filter((pl.col('bid') + pl.col('ask')) / 2 <= 5.0)
        minutes = df['timestamp'].n_unique()
        agg.append({'file': os.path.basename(f), 'rows': df.height, 'contracts': df.select(['strike', 'right']).unique().height, 'minutes': minutes,
                    'two_sided_share': round(two.height / df.height, 4), 'crossed': crossed, 'locked': locked, 'zero_bid_share': round(zero_bid / max(two.height, 1), 4),
                    'median_rel_spread_ntm': round(float(ntm['rs'].median()), 4) if ntm.height else None})
    return agg
q = {}
for name in ['0dte_chains (1m NBBO, every strike, same-day expiration)', 'weekly_chains (1m NBBO, every strike, one expiration a day)']:
    root_dir = sets[name][0]
    for r in out[name]['roots']:
        files = [f for f in glob.glob(f'{root_dir}/{r}/*.parquet')]
        q[f'{name.split()[0]}/{r}'] = quality(files, 12)
        rows = q[f'{name.split()[0]}/{r}']
        print(name.split()[0], r, 'median two-sided', sorted(x['two_sided_share'] for x in rows)[len(rows)//2], 'crossed', sum(x['crossed'] for x in rows), flush=True)
out['quality_sample'] = q
json.dump(out, open('local_inventory.json', 'w'), indent=1)
