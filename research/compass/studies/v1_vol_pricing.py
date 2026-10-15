"""Study V1 (amendment A8): ATM straddles across the optionable universe, sorted on IV/RV21 (S1), the term slope (S2)
and the skew (S3). Unusual Whales closing chains (their NBBO = ThetaData's closing NBBO, checked 638/638) and ThetaData
stock end-of-day closes.

  python3 v1_vol_pricing.py plan            calendar and point-in-time universe -> results/v1/v1_vol_pricing/plan.parquet
  python3 v1_vol_pricing.py fetch [E|E2]    pull the E_k chains (E) or the E_(k+1) chains of names with an E_k straddle (E2)
  python3 v1_vol_pricing.py build           straddles, signals, outcomes -> name_cycles.parquet
  python3 v1_vol_pricing.py analyze [--holdout]

Every chain is cached as gzipped JSON under $SP/uw_chains/<T>/<D>_<E>.json.gz and never fetched twice; the fetch ledger
(ledger.jsonl) records every request's outcome so coverage can be counted. The Unusual Whales token is read from the
environment and never printed."""
import datetime as dt, glob, gzip, json, os, sys, time, threading, urllib.request, urllib.error, re
from concurrent.futures import ThreadPoolExecutor
import numpy as np, polars as pl

SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
OUT = os.path.join(HERE, '..', 'results', 'v1', 'v1_vol_pricing'); os.makedirs(OUT, exist_ok=True)
CACHE = os.path.join(SP, 'uw_chains'); LEDGER = os.path.join(OUT, 'ledger.jsonl')
STOCK = os.path.join(ROOT, 'data_lake', 'thetadata', 'stock_eod')
UW_FLOOR = dt.date(2023, 11, 15)
FEE = 0.70
DEV_END, VAL_END = dt.date(2024, 12, 31), dt.date(2025, 12, 31)

def stock_eod() -> pl.DataFrame:
    fs = sorted(glob.glob(f'{STOCK}/year=*/*.parquet'))
    d = pl.concat([pl.read_parquet(f, columns=['created', 'open', 'close', 'volume', 'symbol']) for f in fs])
    d = d.with_columns(pl.col('created').dt.date().alias('date')).drop('created')
    return d.filter(pl.col('close').is_finite() & (pl.col('close') > 0)).unique(['symbol', 'date']).sort(['symbol', 'date'])

def calendar(sessions: list[dt.date]) -> list[tuple[dt.date, dt.date, dt.date]]:
    """(D_k, E_k, E_(k+1)) for the standard monthly expirations: the third Friday, or the session before it when the
    Friday is a holiday."""
    ss = set(sessions)
    def monthly(y, m):
        d = dt.date(y, m, 1); d += dt.timedelta(days=(4 - d.weekday()) % 7 + 14)
        while d not in ss: d -= dt.timedelta(days=1)
        return d
    exps = []
    y, m = 2023, 11
    while (y, m) <= (2026, 10):
        if monthly(y, m) <= max(sessions): exps.append(monthly(y, m))
        m += 1
        if m == 13: y, m = y + 1, 1
    out = []
    for a, b, c in zip(exps, exps[1:], exps[2:] + [None]):
        d = min(s for s in sessions if s > a)
        if d >= UW_FLOOR: out.append((d, b, c))
    return out

def plan():
    st = stock_eod()
    sessions = sorted(st.filter(pl.col('symbol') == 'SPY')['date'].to_list())
    cal = calendar(sessions)
    cal = [c for c in cal if c[1] <= dt.date(2026, 9, 30)]
    st = st.with_columns((pl.col('close') * pl.col('volume')).alias('dv'))
    rows = []
    for d, e, e2 in cal:
        w = [s for s in sessions if s <= d][-20:]
        u = st.filter(pl.col('date').is_in(w)).group_by('symbol').agg(pl.col('dv').median().alias('dv_med'), pl.len().alias('nd'),
                                                                   pl.col('close').filter(pl.col('date') == d).first().alias('close_d'))
        u = u.filter((pl.col('nd') >= 15) & (pl.col('dv_med') >= 50e6) & (pl.col('close_d') >= 10))
        rows.append(u.with_columns(pl.lit(d).alias('D'), pl.lit(e).alias('E'), pl.lit(e2).alias('E2')))
    P = pl.concat(rows)
    P = P.filter(~pl.col('symbol').str.contains(r'[^A-Z.]'))      # tickers with characters UW does not route (warrants, units)
    P.write_parquet(f'{OUT}/plan.parquet')
    print(P.group_by('D').agg(pl.len()).sort('D'))
    print('cycles', P['D'].n_unique(), 'name-cycles', P.height)

# ---------------------------------------------------------------- fetch
_lock = threading.Lock()
def _path(t, d, e): return os.path.join(CACHE, t, f'{d}_{e}.json.gz')
PAGE = 500          # the endpoint returns at most 500 contracts a page; `page=` continues (QQQ 2024-03-15: 500 + 62)

def _page(t, d, e, page):
    url = f'https://api.unusualwhales.com/api/stock/{t}/option-contracts?date={d}&expiry={e}&page={page}'
    req = urllib.request.Request(url, headers={'Authorization': f"Bearer {os.environ['UW_API_TOKEN']}", 'Accept': 'application/json'})
    last = 'rate-limited or server error on every attempt'
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read()).get('data', []), None
        except urllib.error.HTTPError as ex:
            if ex.code == 429 or ex.code >= 500: last = f'http {ex.code}'; time.sleep(2 * (attempt + 1)); continue
            msg = ex.read()[:200].decode('utf-8', 'replace').replace(os.environ['UW_API_TOKEN'], '***')
            return None, f'http {ex.code} {msg}'
        except Exception as ex:
            time.sleep(2 * (attempt + 1)); last = str(ex)[:120]
    return None, f'failed {last}'

def _write(p, data):
    os.makedirs(os.path.dirname(p), exist_ok=True); tmp = p + '.tmp'
    with gzip.open(tmp, 'wt') as f: json.dump(data, f)
    os.replace(tmp, p)

def _get(t, d, e):
    p = _path(t, d, e)
    if os.path.exists(p): return 'cached'
    data = []
    for page in range(20):
        rows, err = _page(t, d, e, page)
        if err: return err
        data += rows
        if len(rows) < PAGE: break
    _write(p, data)
    return f'ok {len(data)}'

def complete_pages():
    """re-fetch the later pages of any cached chain that stopped at exactly a full page (written before paging)"""
    fixed = 0
    for p in glob.glob(os.path.join(CACHE, '*', '*.json.gz')):
        with gzip.open(p, 'rt') as f: data = json.load(f)
        if len(data) == 0 or len(data) % PAGE: continue
        t = os.path.basename(os.path.dirname(p)); d, e = os.path.basename(p)[:-8].split('_')
        page = len(data) // PAGE; extra = []
        while True:
            rows, err = _page(t, d, e, page)
            if err: print('page error', t, d, e, err); break
            extra += rows; page += 1
            if len(rows) < PAGE: break
        seen = {r['option_symbol'] for r in data}
        data += [r for r in extra if r['option_symbol'] not in seen]
        _write(p, data); fixed += 1
    print('chains completed', fixed)

def fetch(which='E'):
    P = pl.read_parquet(f'{OUT}/plan.parquet')
    if which == 'E': jobs = [(r['symbol'], r['D'], r['E']) for r in P.iter_rows(named=True)]
    else:
        nc = pl.read_parquet(f'{OUT}/name_cycles.parquet')
        jobs = [(r['symbol'], r['D'], r['E2']) for r in nc.iter_rows(named=True) if r['E2'] is not None]
    todo = [j for j in jobs if not os.path.exists(_path(*j))]
    print(f'{which}: {len(jobs)} jobs, {len(jobs) - len(todo)} cached, {len(todo)} to fetch', flush=True)
    t0 = time.time(); n = 0
    def one(j):
        nonlocal n
        res = _get(*j)
        with _lock:
            n += 1
            with open(LEDGER, 'a') as f: f.write(json.dumps({'t': j[0], 'D': str(j[1]), 'E': str(j[2]), 'which': which, 'res': res, 'utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}) + '\n')
            if n % 500 == 0: print(f'{n}/{len(todo)} {time.time() - t0:.0f}s', flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex: list(ex.map(one, todo))
    print(f'done {n} in {time.time() - t0:.0f}s', flush=True)

# ---------------------------------------------------------------- corporate actions (A8.2)
OHLC = os.path.join(SP, 'uw_ohlc3y')
def _ohlc_get(t):
    p = os.path.join(OHLC, f'{t}.json.gz')
    if os.path.exists(p): return 'cached'
    url = f'https://api.unusualwhales.com/api/stock/{t}/ohlc/1d?timeframe=3Y'
    req = urllib.request.Request(url, headers={'Authorization': f"Bearer {os.environ['UW_API_TOKEN']}", 'Accept': 'application/json'})
    last = 'rate-limited or server error on every attempt'
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: data = json.loads(r.read()).get('data', [])
            rows = [{'date': x['date'], 'close': x['close']} for x in data if x.get('market_time') == 'r']
            os.makedirs(OHLC, exist_ok=True); tmp = p + '.tmp'
            with gzip.open(tmp, 'wt') as f: json.dump(rows, f)
            os.replace(tmp, p); return f'ok {len(rows)}'
        except urllib.error.HTTPError as ex:
            if ex.code == 429 or ex.code >= 500: last = f'http {ex.code}'; time.sleep(2 * (attempt + 1)); continue
            return f'http {ex.code}'
        except Exception as ex: last = str(ex)[:120]; time.sleep(2 * (attempt + 1))
    return f'failed {last}'

def fetch_ohlc(tickers):
    todo = [t for t in sorted(set(tickers)) if not os.path.exists(os.path.join(OHLC, f'{t}.json.gz'))]
    print(f'ohlc: {len(todo)} tickers to fetch', flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex: res = list(ex.map(_ohlc_get, todo))
    with open(os.path.join(OUT, 'ohlc_ledger.jsonl'), 'a') as f:
        for t, r in zip(todo, res): f.write(json.dumps({'t': t, 'res': r}) + '\n')

def corp_days(symbol: str, raw: pl.DataFrame):
    """sessions where the raw close-to-close ratio and Unusual Whales' adjusted ratio differ by 25 % or more; None when
    Unusual Whales has no bars for the ticker"""
    p = os.path.join(OHLC, f'{symbol}.json.gz')
    if not os.path.exists(p): return None
    with gzip.open(p, 'rt') as f: rows = json.load(f)
    if not rows: return None
    adj = pl.DataFrame(rows).with_columns(pl.col('date').str.to_date(), pl.col('close').cast(pl.Float64, strict=False)).filter(pl.col('close').is_finite() & (pl.col('close') > 0))
    j = raw.select(['date', 'close']).join(adj.rename({'close': 'adj'}), on='date', how='inner').sort('date')
    if j.height < 20: return None
    j = j.with_columns((pl.col('close') / pl.col('close').shift(1)).log().alias('lr'), (pl.col('adj') / pl.col('adj').shift(1)).log().alias('la'))
    return set(j.filter((pl.col('lr') - pl.col('la')).abs() >= np.log(1.25))['date'].to_list())

JUMP_LO, JUMP_HI = 1 / 1.4, 1.4

def jumps_in(raw, lo, hi):
    """(date, previous session, ratio) for raw close-to-close ratios >= 1.4 or <= 1/1.4 in [lo, hi]"""
    r = raw.with_columns(pl.col('date').shift(1).alias('prev')).filter(pl.col('date').is_between(lo, hi) & pl.col('ratio').is_finite() & ((pl.col('ratio') >= JUMP_HI) | (pl.col('ratio') <= JUMP_LO)))
    return [(a, b, c) for a, b, c in zip(r['date'].to_list(), r['prev'].to_list(), r['ratio'].to_list()) if b is not None]

def _quoted(t, d, e):
    """contracts with a finite, positive ask at the close"""
    c = chain(t, d, e)
    if c is None or c.height == 0: return set()
    c = c.filter(pl.col('ask').is_finite() & (pl.col('ask') > 0))
    return set(zip(c['strike'].to_list(), c['right'].to_list()))

def jump_verdict(t, jd, prev, e):
    """A8.3a: share of the prior session's quoted contracts still quoted on the jump session, same expiration. After a
    split the old series stay listed without quotes (SMCI 2024-10-01: bid and ask empty) and new strikes are listed"""
    a, b = _quoted(t, prev, e), _quoted(t, jd, e)
    if not a: return 'ambiguous', float('nan')
    share = len(a & b) / len(a)
    return ('genuine' if share >= 0.8 else 'corporate action' if share <= 0.3 else 'ambiguous'), share

def jump_jobs(pairs):
    """chain requests the A8.3 checks need, for (symbol, jump date, previous session, expiration)"""
    return sorted({(t, d, e) for t, jd, prev, e in pairs for d in (jd, prev)})

def corp_hit(symbol, raw, lo, hi, e=None, use_chains=False):
    """(hit, how): A8.3 when its chains are cached (use_chains), else A8.1's standard ratios (interim)"""
    if use_chains and e is not None:
        vs = [(jd, *jump_verdict(symbol, jd, prev, e), r) for jd, prev, r in jumps_in(raw, lo, hi)]
        bad = [v for v in vs if v[1] != 'genuine']
        if bad: return f'{bad[0][1]} {bad[0][0]} (ratio {bad[0][3]:.3f}, strikes kept {bad[0][2]:.2f})', 'A8.3'
        return None, 'A8.3'
    win = raw.filter(pl.col('date').is_between(lo, hi))
    hit = [x for x in win['ratio'].to_list() if x is not None and np.isfinite(x) and any(abs(x / f - 1) <= 0.015 for f in SPLIT_FACTORS)]
    return (f'split-like ratio {hit[0]:.4f}' if hit else None), 'A8.1 fallback'

# ---------------------------------------------------------------- build
SYM = re.compile(r'^([A-Z.]+?)(\d{6})([CP])(\d{8})$')
SPLIT_FACTORS = [1/2, 1/3, 2/3, 1/4, 1/5, 1/10, 1/20, 1/50, 2, 3, 4, 5, 8, 10, 15, 20, 25, 30, 40, 50]
TICK = lambda p: 0.01 if p < 3 else 0.05

def chain(t, d, e) -> pl.DataFrame | None:
    p = _path(t, d, e)
    if not os.path.exists(p): return None
    with gzip.open(p, 'rt') as f: rows = json.load(f)
    out = []
    for r in rows:
        m = SYM.match(r.get('option_symbol') or '')
        if not m: continue
        if dt.datetime.strptime(m.group(2), '%y%m%d').date() != e: continue      # only the requested expiration
        def f_(k):
            v = r.get(k)
            try: return float(v)
            except (TypeError, ValueError): return float('nan')
        out.append({'root': m.group(1), 'right': m.group(3), 'strike': int(m.group(4)) / 1000, 'bid': f_('nbbo_bid'), 'ask': f_('nbbo_ask'),
                    'iv': f_('implied_volatility'), 'delta': f_('delta'), 'oi': f_('open_interest'), 'vol': f_('volume')})
    return pl.DataFrame(out) if out else pl.DataFrame()

def straddle(c: pl.DataFrame, spot: float):
    two = c.filter(pl.col('bid').is_finite() & pl.col('ask').is_finite() & (pl.col('bid') > 0) & (pl.col('ask') >= pl.col('bid')))   # NaN > 0 is true in polars
    cc = two.filter(pl.col('right') == 'C').select(['strike', pl.col('bid').alias('cb'), pl.col('ask').alias('ca'), pl.col('iv').alias('civ'), pl.col('oi').alias('coi'), pl.col('vol').alias('cvol')])
    pp = two.filter(pl.col('right') == 'P').select(['strike', pl.col('bid').alias('pb'), pl.col('ask').alias('pa'), pl.col('iv').alias('piv'), pl.col('oi').alias('poi'), pl.col('vol').alias('pvol')])
    j = cc.join(pp, on='strike', how='inner')
    if j.height == 0: return None
    j = j.with_columns((pl.col('strike') - spot).abs().alias('dist')).sort(['dist', 'strike'])
    r = j.row(0, named=True)
    if r['dist'] > 0.05 * spot: return None
    return r

def skew(c: pl.DataFrame):
    two = c.filter(pl.col('bid').is_finite() & pl.col('ask').is_finite() & (pl.col('bid') > 0) & (pl.col('ask') >= pl.col('bid')) & pl.col('iv').is_finite() & (pl.col('iv') > 0) & pl.col('delta').is_finite())
    p = two.filter(pl.col('right') == 'P').with_columns((pl.col('delta') + 0.25).abs().alias('x')).sort('x')
    k = two.filter(pl.col('right') == 'C').with_columns((pl.col('delta') - 0.25).abs().alias('x')).sort('x')
    if p.height == 0 or k.height == 0 or p['x'][0] > 0.10 or k['x'][0] > 0.10: return float('nan')
    return float(p['iv'][0] - k['iv'][0])

def build():
    P = pl.read_parquet(f'{OUT}/plan.parquet')
    pilot = os.environ.get('V1_PILOT_D')                     # a one-cycle end-to-end check before the full build
    if pilot: P = P.filter(pl.col('D') == dt.date.fromisoformat(pilot))
    tag = '_pilot' if pilot else ''
    st = stock_eod().filter(pl.col('symbol').is_in(P['symbol'].unique().to_list()))
    st = st.with_columns((pl.col('close') / pl.col('close').shift(1).over('symbol')).alias('ratio'))
    by = {s: g.sort('date') for s, g in st.group_by('symbol', maintain_order=False)}
    by = {k[0] if isinstance(k, tuple) else k: v for k, v in by.items()}
    earn = pl.read_parquet(os.path.join(ROOT, 'data_lake', 'unusualwhales', 'earnings.parquet'), columns=['ticker', 'report_date'])
    earn = earn.with_columns(pl.col('report_date').str.to_date(strict=False)).drop_nulls()
    edates = {k[0]: sorted(set(v['report_date'].to_list())) for k, v in earn.group_by('ticker')}
    info = pl.read_parquet(os.path.join(ROOT, 'data_lake', 'unusualwhales', 'info.parquet'), columns=['symbol', 'issue_type', 'sector'])
    rows, excl = [], []
    for r in P.iter_rows(named=True):
        t, d, e, e2 = r['symbol'], r['D'], r['E'], r['E2']
        g = by.get(t)
        base = {'symbol': t, 'D': d, 'E': e, 'E2': e2}
        if g is None: excl.append({**base, 'reason': 'no stock rows'}); continue
        c = chain(t, d, e)
        if c is None: excl.append({**base, 'reason': 'chain not fetched'}); continue
        if c.height == 0: excl.append({**base, 'reason': 'empty chain'}); continue
        dates = g['date'].to_list(); i = dates.index(d) if d in dates else None
        if i is None: excl.append({**base, 'reason': 'no close on D'}); continue
        spot = float(g['close'][i])
        s = straddle(c, spot)
        if s is None: excl.append({**base, 'reason': 'no two-sided ATM straddle within 5%'}); continue
        hit, how = corp_hit(t, g, dates[max(0, i - 30)], e, e=e, use_chains=os.environ.get('V1_A83') == '1')
        if hit: excl.append({**base, 'reason': hit, 'rule': how}); continue
        if e not in dates: excl.append({**base, 'reason': 'no close on E (delisted, acquired or halted)', 'last_close_date': dates[-1] if dates[-1] < e else None}); continue
        j = dates.index(e); s_e = float(g['close'][j])
        if i < 21: excl.append({**base, 'reason': 'under 21 returns before D'}); continue
        lr = np.diff(np.log(g['close'][i - 21:i + 1].to_numpy()))
        rv21 = float(np.std(lr, ddof=1) * np.sqrt(252))
        lf = np.diff(np.log(g['close'][i:j + 1].to_numpy()))
        rv_fwd = float(np.std(lf, ddof=1) * np.sqrt(252)) if lf.size > 2 else float('nan')
        k = s['strike']; mid = (s['cb'] + s['ca'] + s['pb'] + s['pa']) / 2
        payoff = abs(s_e - k); fee = 2 * FEE / 100
        tick = TICK(s['ca']) + TICK(s['pa'])
        iv = np.nanmean([s['civ'], s['piv']]) if np.isfinite(s['civ']) or np.isfinite(s['piv']) else float('nan')
        er = any(d < x <= e for x in edates.get(t, ()))
        rows.append({**base, 'spot_D': spot, 'spot_E': s_e, 'K': k, 'cb': s['cb'], 'ca': s['ca'], 'pb': s['pb'], 'pa': s['pa'], 'mid': mid,
                     'rel_spread': (s['ca'] + s['pa'] - s['cb'] - s['pb']) / mid, 'atm_oi': s['coi'] + s['poi'], 'atm_vol': s['cvol'] + s['pvol'],
                     'iv': float(iv), 'rv21': rv21, 'rv_fwd': rv_fwd, 'skew': skew(c), 'earnings_in': er,
                     'dte': (e - d).days, 'payoff': payoff, 'ca_rule': how,
                     'short_pnl': (s['cb'] + s['pb'] - payoff - fee) * 100, 'long_pnl': (payoff - s['ca'] - s['pa'] - fee) * 100,
                     'short_pnl_adv': (s['cb'] + s['pb'] - tick - payoff - fee) * 100, 'long_pnl_adv': (payoff - s['ca'] - s['pa'] - tick - fee) * 100})
    N = pl.DataFrame(rows).join(info, on='symbol', how='left')
    N = N.with_columns((pl.col('short_pnl') / (pl.col('mid') * 100)).alias('r_short'), (pl.col('long_pnl') / (pl.col('mid') * 100)).alias('r_long'),
                       (pl.col('short_pnl_adv') / (pl.col('mid') * 100)).alias('r_short_adv'), (pl.col('long_pnl_adv') / (pl.col('mid') * 100)).alias('r_long_adv'),
                       (pl.col('iv') / pl.col('rv21')).alias('s1'),
                       pl.when(pl.col('D') <= DEV_END).then(pl.lit('dev')).when(pl.col('D') <= VAL_END).then(pl.lit('val')).otherwise(pl.lit('holdout')).alias('split'))
    N.write_parquet(f'{OUT}/name_cycles{tag}.parquet')
    X = pl.DataFrame(excl); X.write_parquet(f'{OUT}/exclusions{tag}.parquet')
    print('name-cycles', N.height, 'excluded', X.height); print(X.group_by(pl.col('reason').str.slice(0, 40)).agg(pl.len()).sort('len', descending=True))
    print(N.group_by('split').agg(pl.len(), pl.col('D').n_unique().alias('cycles')).sort('split'))

def add_term():
    N = pl.read_parquet(f'{OUT}/name_cycles.parquet')
    iv2 = []
    for r in N.iter_rows(named=True):
        v = float('nan')
        if r['E2'] is not None:
            c = chain(r['symbol'], r['D'], r['E2'])
            if c is not None and c.height:
                s = straddle(c, r['spot_D'])
                if s is not None and s['strike'] == r['K']: v = float(np.nanmean([s['civ'], s['piv']]))
                elif s is not None: v = float('nan')      # term slope only at the same strike, so the skew does not leak into it
        iv2.append(v)
    N = N.with_columns(pl.Series('iv2', iv2)).with_columns((pl.col('iv2') - pl.col('iv')).alias('s2'))
    N.write_parquet(f'{OUT}/name_cycles.parquet')
    print('S2 available', N.filter(pl.col('s2').is_finite()).height, 'of', N.height)

# ---------------------------------------------------------------- analyze
RNG = np.random.default_rng(8)
def boot(x: np.ndarray, B=10000):
    x = x[np.isfinite(x)]
    if x.size < 3: return float('nan'), float('nan'), float('nan'), float('nan')
    b = RNG.choice(x, size=(B, x.size), replace=True).mean(1)
    p = 2 * min((b <= 0).mean(), (b >= 0).mean())
    return float(x.mean()), float(np.quantile(b, 0.025)), float(np.quantile(b, 0.975)), float(max(p, 1 / B))

def per_cycle(N, sig, hi_is_expensive=True, q=5):
    """per cycle: short the expensive quintile at the bid, long the cheap one at the ask; and the expensive short minus
    shorting every name"""
    out = []
    for d, g in N.filter(pl.col(sig).is_finite()).group_by('D'):
        if g.height < 5 * q: continue
        g = g.with_columns(((pl.col(sig).rank('ordinal') - 1) * q // g.height).alias('qq'))
        exp_q, chp_q = (q - 1, 0) if hi_is_expensive else (0, q - 1)
        e = g.filter(pl.col('qq') == exp_q); c = g.filter(pl.col('qq') == chp_q)
        out.append({'D': d[0] if isinstance(d, tuple) else d, 'split': g['split'][0], 'n': g.height,
                    'ls': e['r_short'].mean() + c['r_long'].mean(), 'ls_adv': e['r_short_adv'].mean() + c['r_long_adv'].mean(),
                    'short_exp': e['r_short'].mean(), 'long_cheap': c['r_long'].mean(), 'short_all': g['r_short'].mean(),
                    'exp_minus_all': e['r_short'].mean() - g['r_short'].mean(),
                    'fvrp_exp': (e['iv'] - e['rv_fwd']).mean(), 'fvrp_cheap': (c['iv'] - c['rv_fwd']).mean()})
    return pl.DataFrame(out).sort('D')

def analyze(holdout=False):
    N = pl.read_parquet(f'{OUT}/name_cycles.parquet')
    if not holdout: N = N.filter(pl.col('split') != 'holdout')
    splits = ['dev', 'val', 'devval'] + (['holdout'] if holdout else [])
    def sel(df, sp): return df if sp == 'devval' else df.filter(pl.col('split') == sp)
    lines = []
    # T0: shorting every ATM straddle
    c0 = N.group_by(['D', 'split']).agg(pl.col('r_short').mean(), pl.col('r_short_adv').mean(), pl.len().alias('n')).sort('D')
    for sp in splits:
        s = sel(c0, sp) if sp != 'devval' else c0.filter(pl.col('split') != 'holdout')
        m, lo, hi, p = boot(s['r_short'].to_numpy())
        lines.append({'test': 'T0 short every ATM straddle', 'split': sp, 'cycles': s.height, 'name_cycles': int(s['n'].sum()), 'mean': m, 'lo': lo, 'hi': hi, 'p': p})
    for lab, f in (('stocks', pl.col('issue_type') != 'ETF'), ('ETFs', pl.col('issue_type') == 'ETF'), ('earnings in window', pl.col('earnings_in')), ('no earnings in window', ~pl.col('earnings_in'))):
        c = N.filter(f).group_by(['D', 'split']).agg(pl.col('r_short').mean(), pl.len().alias('n'))
        s = c.filter(pl.col('split') != 'holdout')
        m, lo, hi, p = boot(s['r_short'].to_numpy())
        lines.append({'test': f'T0 short every ATM straddle, {lab}', 'split': 'devval', 'cycles': s.height, 'name_cycles': int(s['n'].sum()), 'mean': m, 'lo': lo, 'hi': hi, 'p': p})
    # T1..T3
    pcs = {}
    for name, sig, hi_exp in (('T1 S1 IV/RV21', 's1', True), ('T2 S2 term slope', 's2', False), ('T3 S3 skew, high = expensive', 's3x', True), ('T3 S3 skew, low = expensive', 's3x', False)):
        if sig == 's3x': N2 = N.with_columns(pl.col('skew').alias('s3x'))
        else: N2 = N
        if sig not in N2.columns: continue
        pc = per_cycle(N2, sig, hi_exp); pcs[name] = pc
        if pc.height == 0: continue
        for sp in splits:
            s = pc if sp == 'devval' else pc.filter(pl.col('split') == sp)
            if sp == 'devval': s = s.filter(pl.col('split') != 'holdout')
            for col in ('ls', 'ls_adv', 'exp_minus_all', 'short_exp', 'long_cheap'):
                m, lo, hi, p = boot(s[col].to_numpy())
                lines.append({'test': f'{name} :: {col}', 'split': sp, 'cycles': s.height, 'name_cycles': int(s['n'].sum()), 'mean': m, 'lo': lo, 'hi': hi, 'p': p})
    R = pl.DataFrame(lines)
    R.write_csv(f'{OUT}/results{"_holdout" if holdout else ""}.csv')
    for k, v in pcs.items(): v.write_csv(f'{OUT}/per_cycle_{k.split()[0]}_{k.split()[1]}{"_low" if "low" in k else ""}{"_holdout" if holdout else ""}.csv')
    # signal-level: forward VRP and short return by S1 quintile, development + validation
    q = N.filter(pl.col('s1').is_finite()).with_columns(((pl.col('s1').rank('ordinal').over('D') - 1) * 5 // pl.len().over('D')).alias('q1'))
    q.group_by('q1').agg(pl.len(), pl.col('s1').median(), pl.col('iv').median(), pl.col('rv21').median(), pl.col('rv_fwd').median(),
                         (pl.col('iv') - pl.col('rv_fwd')).mean().alias('fwd_vrp'), pl.col('r_short').mean(), pl.col('r_short').median().alias('r_short_med'),
                         (pl.col('r_short') < -1).mean().alias('lost_over_premium'), pl.col('rel_spread').median()).sort('q1').write_csv(f'{OUT}/s1_quintiles{"_holdout" if holdout else ""}.csv')
    pl.Config.set_tbl_rows(100); pl.Config.set_tbl_width_chars(220); pl.Config.set_float_precision(4)
    print(R)

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'analyze': analyze('--holdout' in sys.argv)
    if cmd == 'plan': plan()
    elif cmd == 'fetch': fetch(sys.argv[2] if len(sys.argv) > 2 else 'E')
    elif cmd == 'build': build()
    elif cmd == 'term': add_term()
    elif cmd == 'jumps':                                    # A8.3: pull the chains the jump checks need
        P = pl.read_parquet(f'{OUT}/plan.parquet')
        st = stock_eod().filter(pl.col('symbol').is_in(P['symbol'].unique().to_list())).sort(['symbol', 'date'])
        st = st.with_columns((pl.col('close') / pl.col('close').shift(1).over('symbol')).alias('ratio'))
        by = {k[0]: g for k, g in st.group_by('symbol')}
        ss = sorted(st.filter(pl.col('symbol') == 'SPY')['date'].to_list()); ix = {d: i for i, d in enumerate(ss)}
        pairs = [(r['symbol'], jd, prev, r['E']) for r in P.iter_rows(named=True) if r['symbol'] in by
                 for jd, prev, _ in jumps_in(by[r['symbol']], ss[max(0, ix[r['D']] - 30)], r['E'])]
        jobs = [j for j in jump_jobs(pairs) if not os.path.exists(_path(*j))]
        print(f'A8.3: {len(pairs)} (cycle, jump) pairs, {len(jobs)} chains to fetch', flush=True)
        with ThreadPoolExecutor(max_workers=3) as ex: list(ex.map(lambda j: _get(*j), jobs))
        print('jump chains done', flush=True)
    elif cmd == 'complete': complete_pages()
    elif cmd == 'ohlc':
        tk = set(pl.read_parquet(f'{OUT}/plan.parquet')['symbol'].to_list())
        ev = os.path.join(HERE, '..', 'results', 'v1', 'v2_earnings_vol', 'events.parquet')
        if os.path.exists(ev): tk |= set(pl.read_parquet(ev)['symbol'].to_list())
        fetch_ohlc(tk)
