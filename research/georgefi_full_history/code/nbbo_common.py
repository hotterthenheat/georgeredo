"""Shared helpers for the ThetaData NBBO check of GeorgeFi's reported fills.

Rows come from common.py (ledger 1,149 + SPX paper 84). For every option/paper row with an OCC and every SHARES row the
1-second NBBO is requested for a window around the reported entry second and around the reported exit second:
    window = [start of the reported minute - 10 s, reported second + 91 s]
(the whole reported minute is covered so the same-minute repeat analysis can see every second of it). Windows of the same
contract-day are merged when they overlap or touch; one request per merged window, cached as gzip CSV + JSON status under
$SP/theta/cache/georgefi_nbbo/ keyed by the request; ok / no-data results are never refetched, transport errors are.

ThetaData semantics (openapiv3: "the quote for each interval represents the last quote prior to the interval's timestamp"):
the row stamped HH:MM:SS is the NBBO prevailing at that instant, i.e. the last quote update at or before HH:MM:SS.000.
For a reported time HH:MM:SS.mmm we therefore take q0 = row at HH:MM:SS (the last quote at or before the reported second)
and q1 = row at HH:MM:SS+1 (the first snapshot that includes quote updates posted during the reported second).

Key handling: THETADATA_KEY is read from the environment only; exception text is redacted (td1_prod_...) before logging.
"""
import os, sys, re, json, gzip, time, hashlib, datetime, threading, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
CACHE = os.path.join(SP, 'theta', 'cache', 'georgefi_nbbo')
os.makedirs(CACHE, exist_ok=True)
ET = C.ET
PRE_S, POST_S = 10, 91          # seconds before the reported minute start / after the reported second
MERGE_GAP_S = 1                 # merge windows that overlap or touch
FEES = 0.70                     # $/contract/side (backtest/costs.py)
RETRY_CODES = ('RESOURCE_EXHAUSTED', 'UNAVAILABLE', 'DEADLINE_EXCEEDED', 'UNKNOWN', 'INTERNAL', 'UNAUTHENTICATED')

_RED = re.compile(r'td1_prod_[A-Za-z0-9]+')
def red(s): return _RED.sub('REDACTED', str(s))


# ---------------------------------------------------------------- rows
def theta_spec(occ):
    """OCC like O:SPXW260227P06875000 -> (root, expiration date, strike string, right)."""
    cid = C.cid_from_occ(occ)
    m = re.match(r'^([A-Z]+)(\d{6})([CP])(\d{8})$', cid)
    if not m: return None
    root, ymd, cp, k = m.groups()
    exp = datetime.date(2000 + int(ymd[:2]), int(ymd[2:4]), int(ymd[4:6]))
    strike = int(k) / 1000.0
    ks = str(int(strike)) if strike == int(strike) else ('%.3f' % strike).rstrip('0')
    return root, exp, ks, ('call' if cp == 'C' else 'put')


def load_rows():
    """All rows with the fields the NBBO study needs. kind = 'opt' | 'stk' | None (no instrument)."""
    rows = C.load_all()
    for r in rows:
        r['label'] = f"E{r['epoch']}" if r['group'] == 'ledger' else 'paper'
        r['cluster'] = (r['cid'] or r['ticker']) + '|' + r['entry_dt'].strftime('%Y-%m-%d %H:%M')
        r['day'] = r['entry_date']
        if r['is_option'] and r['occ']:
            spec = theta_spec(r['occ'])
            if spec:
                r['kind'] = 'opt'; r['t_root'], r['t_exp'], r['t_strike'], r['t_right'] = spec
            else:
                r['kind'] = None; r['t_root'] = r['root']
        elif r['is_shares']:
            r['kind'] = 'stk'; r['t_root'] = r['ticker']; r['t_exp'] = None; r['t_strike'] = ''; r['t_right'] = ''
        else:
            r['kind'] = None; r['t_root'] = r['root']
    return rows


# ---------------------------------------------------------------- windows / requests
def floor_s(t): return t.replace(microsecond=0)

def window_for(t):
    """[start, end] second-aligned ET datetimes around reported time t."""
    s = floor_s(t)
    start = s.replace(second=0) - datetime.timedelta(seconds=PRE_S)
    end = s + datetime.timedelta(seconds=POST_S)
    day0 = s.replace(hour=0, minute=0, second=0)
    start = max(start, day0)
    end = min(end, day0.replace(hour=23, minute=59, second=59))
    return start, end


def contract_key(r, date):
    if r['kind'] == 'opt': return ('opt', r['t_root'], r['t_exp'].isoformat(), r['t_strike'], r['t_right'], date)
    if r['kind'] == 'stk': return ('stk', r['t_root'], '', '', '', date)
    return None


def build_requests(rows):
    """Merge per-contract-day windows; returns {ckey: [(start, end), ...]}."""
    wins = collections.defaultdict(list)
    for r in rows:
        if r['kind'] is None: continue
        for which, t in (('entry', r['entry_dt']), ('exit', r['exit_dt'])):
            if t is None: continue
            ck = contract_key(r, t.strftime('%Y-%m-%d'))
            wins[ck].append(window_for(t))
    merged = {}
    for ck, ws in wins.items():
        ws.sort()
        out = []
        for s, e in ws:
            if out and s <= out[-1][1] + datetime.timedelta(seconds=MERGE_GAP_S):
                out[-1][1] = max(out[-1][1], e)
            else:
                out.append([s, e])
        merged[ck] = [(s, e) for s, e in out]
    return merged


def req_id(ck, s, e):
    kind, root, exp, strike, right, date = ck
    raw = f"{kind}|{root}|{exp}|{strike}|{right}|{date}|{s.strftime('%H:%M:%S')}|{e.strftime('%H:%M:%S')}"
    return raw, hashlib.sha1(raw.encode()).hexdigest()[:20]


def cache_paths(h): return os.path.join(CACHE, h + '.csv.gz'), os.path.join(CACHE, h + '.json')


# ---------------------------------------------------------------- fetch
_lock = threading.Lock()
_client = {'c': None, 'gen': 0}

def make_client():
    import thetadata
    return thetadata.ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='pandas')


def get_client():
    """Shared client (one gRPC channel; thread-safe). Returns (client, generation)."""
    with _lock:
        if _client['c'] is None:
            _client['c'] = make_client(); _client['gen'] += 1
        return _client['c'], _client['gen']


def reset_client(gen):
    """Re-authenticate once per failed generation (an UNAUTHENTICATED 'Invalid session ID' happens when the shared key is
    used by another process; a fresh login fixes it)."""
    with _lock:
        if _client['gen'] == gen:
            _client['c'] = None
            try: _client['c'] = make_client(); _client['gen'] += 1
            except Exception: _client['c'] = None


def fetch_one(client, ck, s, e, max_tries=8):
    """Fetch one window, write the cache, return the status dict. Never raises on data errors.
    `client` None -> the shared client is used (and re-created on UNAUTHENTICATED); passing one keeps the old call signature."""
    import grpc
    from thetadata.errors import NoDataFoundError
    raw, h = req_id(ck, s, e)
    csv_p, js_p = cache_paths(h)
    if os.path.exists(js_p):
        st = json.load(open(js_p))
        if st.get('ok') or st.get('nodata'): return st      # transport errors are refetched
    kind, root, exp, strike, right, date = ck
    d = datetime.date.fromisoformat(date)
    stt, en = s.strftime('%H:%M:%S'), e.strftime('%H:%M:%S')
    status = dict(key=raw, hash=h, kind=kind, root=root, date=date, start=stt, end=en)
    t0 = time.time(); wait = 2.0
    for attempt in range(max_tries):
        cl, gen = (client, 0) if client is not None else get_client()
        try:
            if kind == 'opt':
                df = cl.option_history_quote(symbol=root, expiration=datetime.date.fromisoformat(exp), interval='1s', date=d,
                                             strike=strike, right=right, start_time=stt, end_time=en)
            else:
                df = cl.stock_history_quote(symbol=root, interval='1s', date=d, start_time=stt, end_time=en)
            cols = [c for c in ['timestamp', 'bid', 'ask', 'bid_size', 'ask_size', 'bid_exchange', 'ask_exchange', 'bid_condition', 'ask_condition'] if c in df.columns]
            out = df[cols].copy()
            out['timestamp'] = out['timestamp'].astype(str)
            with gzip.open(csv_p, 'wt') as fh: out.to_csv(fh, index=False)
            status.update(ok=True, rows=int(len(out)), ms=int((time.time() - t0) * 1000), attempts=attempt + 1,
                          first=str(out['timestamp'].iloc[0]) if len(out) else None, last=str(out['timestamp'].iloc[-1]) if len(out) else None)
            break
        except NoDataFoundError:
            status.update(ok=False, nodata=True, error='NoDataFoundError', ms=int((time.time() - t0) * 1000), attempts=attempt + 1); break
        except grpc.RpcError as ex:
            code = ex.code().name if hasattr(ex, 'code') else 'RpcError'
            msg = red(re.sub(r'\s+', ' ', str(ex)))[:300]
            if code in RETRY_CODES and attempt < max_tries - 1:
                if code == 'UNAUTHENTICATED' and client is None: reset_client(gen)
                time.sleep(wait); wait = min(wait * 2, 60); continue
            status.update(ok=False, nodata=False, error=f'{code}: {msg}', ms=int((time.time() - t0) * 1000), attempts=attempt + 1); break
        except Exception as ex:
            msg = red(re.sub(r'\s+', ' ', f'{type(ex).__name__}: {ex}'))[:300]
            if attempt < max_tries - 1 and ('timed out' in msg.lower() or 'connection' in msg.lower()):
                time.sleep(wait); wait = min(wait * 2, 60); continue
            status.update(ok=False, nodata=False, error=msg, ms=int((time.time() - t0) * 1000), attempts=attempt + 1); break
    with _lock:
        json.dump(status, open(js_p, 'w'))
    return status


# ---------------------------------------------------------------- read back
def load_window(ck, s, e):
    """Return (status, {second(ET datetime): (bid, ask, bid_size, ask_size)}) from the cache, or (None, {}) if not fetched."""
    import pandas as pd
    raw, h = req_id(ck, s, e)
    csv_p, js_p = cache_paths(h)
    if not os.path.exists(js_p): return None, {}
    st = json.load(open(js_p))
    if not st.get('ok'): return st, {}
    q = {}
    with gzip.open(csv_p, 'rt') as fh: df = pd.read_csv(fh)
    bs_col = df['bid_size'] if 'bid_size' in df.columns else [None] * len(df)
    as_col = df['ask_size'] if 'ask_size' in df.columns else [None] * len(df)
    for ts, b, a, bs, as_ in zip(df['timestamp'], df['bid'], df['ask'], bs_col, as_col):
        t = datetime.datetime.fromisoformat(str(ts))
        if t.tzinfo is None: t = t.replace(tzinfo=ET)
        q[t.astimezone(ET)] = (float(b), float(a), bs, as_)
    return st, q


class QuoteBook:
    """Holds every fetched window of every contract-day; quote lookups by second."""
    def __init__(self, merged):
        self.data = {}; self.status = {}
        for ck, ws in merged.items():
            for s, e in ws:
                st, q = load_window(ck, s, e)
                self.status[(ck, s, e)] = st
                self.data.setdefault(ck, {}).update(q)

    def status_for(self, ck, t):
        s_, e_ = window_for(t)
        for (c, s, e), st in self.status.items():
            if c == ck and s <= s_ and e >= e_: return st
        return None

    def at(self, ck, second):
        return self.data.get(ck, {}).get(second)

    def minute(self, ck, t):
        """All quotes in the reported minute of t: [(second, bid, ask)]."""
        m0 = floor_s(t).replace(second=0); m1 = m0 + datetime.timedelta(minutes=1)
        d = self.data.get(ck, {})
        return [(k, v[0], v[1]) for k, v in sorted(d.items()) if m0 <= k < m1]
