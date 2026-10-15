"""Which expirations each name actually listed, read from Unusual Whales' history (2023-11-15 on).

Why: single names are not Friday-only. In October 2026 the exchange's end-of-day file lists Monday and Wednesday
expirations on AAPL, AMD, AMZN, AVGO, GOOGL, INTC, META, MSFT, MU, NVDA and TSLA, and other weekdays on several ETFs.
A same-day (0DTE) or weekly study must use the dates each name listed, not a weekday rule.

How: for a name and a date D, ask the historical chain for expiry D on date D (page 0). The date was a listed expiry
for that name when any returned contract's OCC symbol carries expiry D. SPY (daily expirations throughout) is the
control: a weekday where SPY returns nothing is a market holiday or a failed call, never a "not listed".

  python3 -I expiry_calendar.py sample   # one week a month, Mon-Thu, every name
  python3 -I expiry_calendar.py full     # every week, for each (name, weekday) the sample found listed, plus SPY
  python3 -I expiry_calendar.py report   # first and last listed date per (name, weekday), gaps, holidays
"""
import datetime as dt, json, os, re, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import polars as pl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'results', 'expiry_calendar')
FLOOR, TOP = dt.date(2023, 11, 15), dt.date(2026, 10, 14)
SINGLE = ['AAPL', 'AMD', 'AMZN', 'AVGO', 'GOOGL', 'INTC', 'META', 'MSFT', 'MU', 'NVDA', 'TSLA']
ETF = ['GLD', 'IBIT', 'SMH', 'XLF', 'TLT', 'SLV', 'XLE', 'TQQQ', 'EEM', 'GDX', 'IEF', 'LQD', 'SOXL', 'UNG', 'USO']
CONTROL = 'SPY'
SYM = re.compile(r'^([A-Z.]+?)(\d{6})([CP])(\d{8})$')

def probe(t, d):
    url = f'https://api.unusualwhales.com/api/stock/{t}/option-contracts?date={d}&expiry={d}&page=0'
    req = urllib.request.Request(url, headers={'Authorization': f"Bearer {os.environ['UW_API_TOKEN']}", 'Accept': 'application/json'})
    last = 'rate-limited or server error on every attempt'
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: rows = json.loads(r.read()).get('data', [])
            break
        except urllib.error.HTTPError as ex:
            if ex.code == 429 or ex.code >= 500: last = f'http {ex.code}'; time.sleep(2 * (attempt + 1)); continue
            msg = ex.read()[:160].decode('utf-8', 'replace').replace(os.environ['UW_API_TOKEN'], '***')
            return dict(name=t, date=d, err=f'http {ex.code} {msg}', rows=0, match=0, quoted=0)
        except Exception as ex:
            time.sleep(2 * (attempt + 1)); last = str(ex)[:120]
    else:
        return dict(name=t, date=d, err=f'failed {last}', rows=0, match=0, quoted=0)
    want = d.replace('-', '')[2:]
    match = [r for r in rows if (m := SYM.match(r.get('option_symbol') or '')) and m.group(2) == want]
    quoted = sum(1 for r in match if _f(r.get('nbbo_ask')) > 0)
    return dict(name=t, date=d, err='', rows=len(rows), match=len(match), quoted=quoted)

def _f(x):
    try: return float(x)
    except (TypeError, ValueError): return 0.0

def weekdays(sample):
    d, out = FLOOR, []
    while d <= TOP:
        if d.weekday() <= 3 and (not sample or d.day <= 7 + d.weekday() and _first_full_week(d)): out.append(d)
        d += dt.timedelta(days=1)
    return out

def _first_full_week(d):
    monday = d - dt.timedelta(days=d.weekday())
    return monday.month == d.month and monday.day <= 7

def run(jobs, path):
    done = set()
    if os.path.exists(path):
        old = pl.read_parquet(path); done = {(a, b) for a, b in old.filter(pl.col('err') == '').select('name', 'date').iter_rows()}
    else: old = None
    jobs = [j for j in jobs if j not in done]
    print(f'{len(jobs)} calls to make ({len(done)} already done)', flush=True)
    out, t0 = [], time.time()
    with ThreadPoolExecutor(3) as ex:
        for i, r in enumerate(ex.map(lambda j: probe(*j), jobs)):
            out.append(r)
            if (i + 1) % 250 == 0: print(f'{i + 1}/{len(jobs)} {time.time() - t0:.0f}s', flush=True)
    new = pl.DataFrame(out, schema=dict(name=pl.Utf8, date=pl.Utf8, err=pl.Utf8, rows=pl.Int64, match=pl.Int64, quoted=pl.Int64)) if out else None
    parts = [x for x in (old.filter(pl.col('err') == '') if old is not None else None, new) if x is not None]
    df = pl.concat(parts).unique(['name', 'date'], keep='last').sort('name', 'date')
    os.makedirs(OUT, exist_ok=True); df.write_parquet(path)
    errs = df.filter(pl.col('err') != '')
    print(f'wrote {path}: {df.height} rows, {errs.height} errors', flush=True)
    if errs.height: print(errs.head(10))

def with_wd(df):
    return df.with_columns(pl.col('date').str.strptime(pl.Date, '%Y-%m-%d').dt.weekday().alias('wd'))

def main():
    cmd = sys.argv[1]
    if cmd == 'sample':
        jobs = [(t, d.isoformat()) for t in [CONTROL] + SINGLE + ETF for d in weekdays(True)]
        run(jobs, os.path.join(OUT, 'sample.parquet'))
    elif cmd == 'full':
        s = with_wd(pl.read_parquet(os.path.join(OUT, 'sample.parquet')))
        hol = set(s.filter((pl.col('name') == CONTROL) & (pl.col('match') == 0))['date'])
        s = s.filter(~pl.col('date').is_in(list(hol)))
        # from the last sample date that was NOT listed before the first listed one (FLOOR when the first sample is
        # already listed), every date of that weekday to TOP: pins the start to the week and lists every date since
        start = {}
        for (t, wd), g in s.filter(pl.col('name') != CONTROL).group_by(['name', 'wd']):
            g = g.sort('date'); lis = g.filter(pl.col('match') > 0)
            if lis.height == 0: continue
            before = g.filter((pl.col('date') < lis['date'][0]) & (pl.col('match') == 0))
            start[(t, wd)] = dt.date.fromisoformat(before['date'][-1]) if before.height else FLOOR
        days = weekdays(False)
        jobs = [(CONTROL, d.isoformat()) for d in days]
        jobs += [(t, d.isoformat()) for t in SINGLE + ETF for d in days if (t, d.weekday() + 1) in start and d >= start[(t, d.weekday() + 1)]]
        print(f'(name, weekday) pairs listed somewhere in the sample: {len(start)}; SPY empty on sample days: {sorted(hol)}')
        run(jobs, os.path.join(OUT, 'full.parquet'))
    elif cmd == 'report':
        report()
    elif cmd == 'v2impact':
        v2impact()
    elif cmd == 'compare':
        compare()

def report():
    s = with_wd(pl.read_parquet(os.path.join(OUT, 'sample.parquet')))
    f = with_wd(pl.read_parquet(os.path.join(OUT, 'full.parquet')))
    days = f.filter(pl.col('name') == CONTROL)
    hol = set(days.filter(pl.col('match') == 0)['date'])
    print('SPY empty (holidays or failed calls):', sorted(hol))
    f = f.filter(~pl.col('date').is_in(list(hol)))
    wdn = {1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu'}
    rows = []
    for (t, wd), g in f.filter(pl.col('name') != CONTROL).group_by(['name', 'wd']):
        g = g.sort('date'); listed = g.filter(pl.col('match') > 0)
        if listed.height == 0: continue
        first, last = listed['date'][0], listed['date'][-1]
        unlisted_before = g.filter((pl.col('date') < first) & (pl.col('match') == 0))
        span = g.filter((pl.col('date') >= first) & (pl.col('date') <= last))
        if unlisted_before.height == 0:
            first = f'on or before {first}'   # listed on the first date probed: the program predates the window
        missing = span.filter(pl.col('match') == 0)['date'].to_list()
        rows.append(dict(name=t, weekday=wdn[wd], first=first, last=last, listed=listed.height,
                         missing_inside=len(missing), missing_dates=','.join(missing[:12])))
    rep = pl.DataFrame(rows).sort('name', 'weekday')
    # (name, weekday) the sample never saw listed
    seen = {(r['name'], r['weekday']) for r in rows}
    never = [(t, wdn[wd]) for t in SINGLE + ETF for wd in (1, 2, 3, 4) if (t, wdn[wd]) not in seen]
    rep.write_csv(os.path.join(OUT, 'listed_weekdays.csv'))
    pl.Config.set_tbl_rows(200); pl.Config.set_fmt_str_lengths(120)
    print(rep)
    print('never listed in the monthly sample:', never)

def compare():
    """The Unusual Whales sample against ThetaData's list of expirations (expiry_calendar_theta.py), date by date."""
    s = pl.read_parquet(os.path.join(OUT, 'sample.parquet'))
    hol = set(s.filter((pl.col('name') == CONTROL) & (pl.col('match') == 0))['date'])
    th = pl.read_parquet(os.path.join(OUT, 'theta_expirations.parquet')).select('name', pl.col('expiration').cast(pl.Utf8).alias('date'))
    th = th.with_columns(pl.lit(True).alias('theta_listed'))
    x = s.filter(~pl.col('date').is_in(list(hol)) & (pl.col('err') == '')).join(th, on=['name', 'date'], how='left')
    x = x.with_columns(pl.col('theta_listed').fill_null(False), (pl.col('match') > 0).alias('uw_listed'))
    x = with_wd(x)
    agree = x.filter(pl.col('uw_listed') == pl.col('theta_listed'))
    print(f'sampled (name, date) pairs on trading days: {x.height}; agree {agree.height}; holidays left out {sorted(hol)}')
    print('by weekday:', x.group_by('wd').agg(pl.len().alias('n'), (pl.col('uw_listed') == pl.col('theta_listed')).sum().alias('agree'),
                                               pl.col('uw_listed').sum().alias('uw'), pl.col('theta_listed').sum().alias('theta')).sort('wd').to_dicts())
    dis = x.filter(pl.col('uw_listed') != pl.col('theta_listed'))
    pl.Config.set_tbl_rows(100); print(dis.select('name', 'date', 'wd', 'uw_listed', 'theta_listed', 'rows', 'match', 'quoted'))
    dis.write_csv(os.path.join(OUT, 'uw_vs_theta_disagreements.csv'))

def v2impact():
    """V2 (amendment A9) took the first FRIDAY expiration on or after the report session. Count the reports where a
    listed Monday-Thursday expiration (this calendar) fell on or after the event session and before that Friday."""
    f = with_wd(pl.read_parquet(os.path.join(OUT, 'full.parquet')))
    hol = set(f.filter((pl.col('name') == CONTROL) & (pl.col('match') == 0))['date'])
    lis = f.filter((pl.col('name') != CONTROL) & (pl.col('match') > 0) & ~pl.col('date').is_in(list(hol)))
    by = {}
    for t, d in lis.select('name', 'date').iter_rows(): by.setdefault(t, []).append(dt.date.fromisoformat(d))
    T = pl.read_parquet(os.path.join(HERE, '..', 'results', 'v1', 'v2_earnings_vol', 'trades.parquet'))
    rows = []
    for r in T.iter_rows(named=True):
        if r['symbol'] not in by or r['E'] is None: continue
        ev, E = r['event'], r['E']
        E = E if isinstance(E, dt.date) else dt.date.fromisoformat(str(E))
        earlier = [d for d in by[r['symbol']] if ev <= d < E]
        if earlier:
            rows.append(dict(symbol=r['symbol'], event=ev, split=r['split'], friday_E=E, nearest_listed=min(earlier),
                             a_status=r['a_status'], b_status=r['b_status'], a_r=r['a_r'], b_r=r['b_r']))
    out = pl.DataFrame(rows) if rows else pl.DataFrame()
    print(f'V2 trades on names with Monday-Thursday listings: {T.filter(pl.col("symbol").is_in(list(by))).height} of {T.height}')
    print(f'... where a listed Monday-Thursday expiry came before the Friday V2 used: {out.height}')
    if out.height:
        pl.Config.set_tbl_rows(200); print(out.sort('event'))
        out.write_csv(os.path.join(OUT, 'v2_affected.csv'))

if __name__ == '__main__':
    main()
