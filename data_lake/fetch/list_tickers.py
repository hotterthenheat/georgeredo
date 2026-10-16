"""List every ticker available on the user's ThetaData and Unusual Whales accounts and time one bulk (flat-file) day per type.
Keys are read from THETADATA_KEY / UW_API_TOKEN only (never printed). Usage: python3 -I list_tickers.py"""
import os, re, sys, json, time, datetime as dt
sys.path.insert(0, '/home/user/georgeredo/backtest')
OUT = os.path.dirname(os.path.abspath(__file__))
SP = '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s))
summary = {'generated_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}
def save(name, items, note):
    items = sorted({str(x).strip() for x in items if str(x).strip()})
    open(os.path.join(OUT, name), 'w').write('\n'.join(items) + '\n')
    summary[name] = dict(count=len(items), note=note); print(name, len(items), flush=True)
    return items
# ---------- ThetaData ----------
import logging; logging.getLogger('thetadata').setLevel(logging.ERROR)
from thetadata import ThetaClient
c = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='pandas')
st = save('thetadata_stocks.txt', c.stock_list_symbols()['symbol'], 'ThetaData stock_list_symbols')
op = save('thetadata_option_roots.txt', c.option_list_symbols()['symbol'], 'ThetaData option_list_symbols (option roots)')
ix = save('thetadata_indices.txt', c.index_list_symbols()['symbol'], 'ThetaData index_list_symbols (includes Nasdaq GIDS symbols the plan cannot read)')
D = dt.date(2026, 10, 9); flat = {}
for name, fn in (('stock_flat_file_eod', c.stock_flat_file_eod), ('option_flat_file_eod', c.option_flat_file_eod), ('option_flat_file_open_interest', c.option_flat_file_open_interest), ('index_flat_file_eod', c.index_flat_file_eod)):
    t0 = time.time()
    try:
        df = fn(date=D); p = f'{SP}/inventory/{name}_{D}.parquet'; df.to_parquet(p)
        flat[name] = dict(date=str(D), rows=len(df), cols=list(df.columns)[:12], secs=round(time.time() - t0, 1), parquet_bytes=os.path.getsize(p))
    except Exception as e:
        flat[name] = dict(date=str(D), error=red(f'{type(e).__name__}: {e}')[:300], secs=round(time.time() - t0, 1))
    print(name, flat[name] if 'error' in flat[name] else {k: v for k, v in flat[name].items() if k != 'cols'}, flush=True)
summary['thetadata_flat_file_probe'] = flat
# ---------- Unusual Whales ----------
os.environ.setdefault('BT_CACHE', SP + '/bt/cache')
import data as uw
uw_res = {}
r = uw.get('option-trades/optionable-tickers', {})
rows = (r or {}).get('data') if isinstance(r, dict) else r
uw_res['optionable-tickers'] = dict(status=('error ' + str(r.get('error'))) if isinstance(r, dict) and r.get('error') else 'ok', n=(len(rows) if isinstance(rows, list) else None), sample=(rows[:3] if isinstance(rows, list) else str(r)[:200]))
if isinstance(rows, list):
    save('unusualwhales_optionable_tickers.txt', [x if isinstance(x, str) else (x.get('ticker') or x.get('symbol') or '') for x in rows], 'UW /api/option-trades/optionable-tickers')
r = uw.get('companies/listings', {})
lst = (r or {}).get('data') if isinstance(r, dict) else r
uw_res['companies/listings'] = dict(status=('error ' + str(r.get('error'))) if isinstance(r, dict) and r.get('error') else 'ok', n=(len(lst) if isinstance(lst, list) else None), sample=(lst[:2] if isinstance(lst, list) else str(r)[:200]))
if isinstance(lst, list):
    save('unusualwhales_listings.txt', [x.get('ticker') or x.get('symbol') or '' for x in lst if isinstance(x, dict)], 'UW /api/companies/listings (active US-traded securities)')
summary['unusualwhales_probe'] = uw_res
print(json.dumps(uw_res, default=str)[:1500])
json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)
