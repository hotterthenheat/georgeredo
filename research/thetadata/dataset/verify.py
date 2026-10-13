"""Spot-check the dataset against fresh 1-second NBBO pulls: for N random chain files pick one in-band strike/right, pull the
1-second series for that contract and compare bid/ask/sizes at every minute boundary with the stored 1-minute rows.
Run ONLY when no other fetch process is using the key (one login per key).  Writes verify.json next to this file.
Usage: set -a; . "$SP/secrets/research.env"; set +a; python3 -I verify.py [N=5] [seed=7]"""
import os, re, sys, json, time, random, logging, datetime as dt
logging.getLogger('thetadata').setLevel(logging.ERROR)
import polars as pl
from thetadata import ThetaClient
from thetadata.errors import NoDataFoundError
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import load as L
def red(s): return re.sub(r'td1_prod_[A-Za-z0-9]+', 'REDACTED', str(s))
N = int(sys.argv[1]) if len(sys.argv) > 1 else 5
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 7

def main():
    rng = random.Random(SEED)
    pool = [(sym, d) for sym in ('SPY', 'QQQ', 'SPXW', 'IWM') for d in L.sessions('chains', sym)]
    picks = rng.sample(pool, N)
    c = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars')
    out = dict(date=dt.datetime.now().isoformat(timespec='seconds'), seed=SEED, checks=[], notes=[])
    for sym, d in picks:
        ch = L.chain(sym, d); ks = sorted(ch['strike'].unique().to_list())
        ref = L.ref_price(sym, d)[0]
        k = min(ks, key=lambda x: abs(x - ref)) if rng.random() < 0.5 else rng.choice(ks)
        right = rng.choice(['CALL', 'PUT'])
        one = ch.filter((pl.col('strike') == k) & (pl.col('right') == right)).sort('timestamp')
        rec = dict(symbol=sym, date=d, strike=k, right=right, rows_1m=one.height)
        D = dt.date.fromisoformat(d); ks_str = str(int(k)) if float(k).is_integer() else str(k)
        t0 = time.time()
        try:
            s1 = c.option_history_quote(symbol=sym, expiration=D, interval='1s', date=D, strike=ks_str, right=right.lower())
        except NoDataFoundError:
            rec.update(rows_1s=0, compared=0, mismatches=None, result='NO 1s DATA'); out['checks'].append(rec); print(json.dumps(rec), flush=True); continue
        except Exception as e:
            rec.update(result='ERROR ' + red(f'{type(e).__name__}: {e}')[:200]); out['checks'].append(rec); print(json.dumps(rec), flush=True); continue
        s1 = s1.with_columns(pl.col('timestamp').dt.convert_time_zone('America/New_York').dt.cast_time_unit('ms'))
        s1 = s1.with_columns([pl.col(x).fill_nan(None) for x in ('bid', 'ask')])
        bound = s1.filter(pl.col('timestamp').dt.second() == 0).select(['timestamp', 'bid', 'ask', 'bid_size', 'ask_size'])
        j = one.join(bound, on='timestamp', how='inner', suffix='_1s')
        def eq(a, b): return ((pl.col(a).is_null() & pl.col(b).is_null()) | ((pl.col(a) - pl.col(b)).abs() < 1e-9))
        j = j.with_columns((eq('bid', 'bid_1s') & eq('ask', 'ask_1s') & (pl.col('bid_size') == pl.col('bid_size_1s')) & (pl.col('ask_size') == pl.col('ask_size_1s'))).alias('match'))
        mism = j.filter(~pl.col('match'))
        rec.update(rows_1s=s1.height, compared=j.height, mismatches=mism.height, secs=round(time.time() - t0, 1),
                   result=('PASS' if j.height >= 300 and mism.height == 0 else 'FAIL'),
                   first_mismatches=[{kk: (str(v) if hasattr(v, 'isoformat') else v) for kk, v in r.items()} for r in mism.head(3).to_dicts()])
        out['checks'].append(rec); print(json.dumps(rec, default=str)[:600], flush=True)
    out['notes'].append('1-second rows at hh:mm:00 are compared with the stored 1-minute rows (same contract, same session); the 09:30:00 placeholder row is included when both series carry it.')
    json.dump(out, open(os.path.join(HERE, 'verify.json'), 'w'), indent=1, default=str)
    print('PASS' if all(ch.get('result') == 'PASS' for ch in out['checks']) else 'NOT ALL PASS')

if __name__ == '__main__':
    main()
