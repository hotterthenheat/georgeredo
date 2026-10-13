"""Shared helpers for the flow-predictor study. Reuses backtest/data.py (cached UW GET). Token only from env."""
import os, sys, json, datetime, zoneinfo
HERE = os.path.dirname(os.path.abspath(__file__))
BT = '/home/user/georgeredo/backtest'  # AUDIT COPY EDIT: original was os.path.abspath(os.path.join(HERE, '..', '..', 'backtest')), which does not resolve from audit/phase1/research/
sys.path.insert(0, BT)
import data  # noqa: E402
ET = zoneinfo.ZoneInfo('America/New_York')
OUT = HERE  # CSV outputs live next to the code
TICKERS = ['SPY', 'QQQ', 'IWM']
START, END = '2025-06-02', '2026-10-09'
DAYS_ALL = json.load(open(os.path.join(BT, 'trading_days.json')))
DAYS = [d for d in DAYS_ALL if START <= d <= END]

def prev_day(d):
    i = DAYS_ALL.index(d)
    return DAYS_ALL[i - 1] if i > 0 else None

def to_et(ts):
    """UTC/offset ISO string -> aware ET datetime."""
    return datetime.datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(ET)

def f(x):
    try: return float(x)
    except Exception: return float('nan')

def net_prem_ticks(ticker, date):
    return (data.get(f'stock/{ticker}/net-prem-ticks', {'date': date}) or {}).get('data') or []

def market_tide(date):
    return (data.get('market/market-tide', {'date': date}) or {}).get('data') or []

def darkpool_rth(ticker, date, max_pages=60):
    """All RTH dark-pool prints (09:30-16:00 ET) for one session, paged with older_than. Returns (rows, pages, truncated)."""
    newer = f'{date}T13:30:00Z'; older = f'{date}T20:00:00Z'
    # 13:30Z/20:00Z is correct for EDT; for EST sessions RTH is 14:30Z-21:00Z. Use a generous window and filter in ET afterwards.
    newer = f'{date}T13:00:00Z'; older = f'{date}T21:30:00Z'
    rows = []; seen = set(); pages = 0; truncated = False
    while pages < max_pages:
        d = data.get(f'darkpool/{ticker}', {'date': date, 'limit': 500, 'newer_than': newer, 'older_than': older})
        page = (d or {}).get('data') or []
        pages += 1
        # tracking_id is null on some dates (e.g. 2025-09..2025-12), so de-duplicate on a composite key
        def key(r): return r.get('tracking_id') or (r.get('executed_at'), r.get('price'), r.get('size'), r.get('market_center'), r.get('volume'))
        new = [r for r in page if key(r) not in seen]
        for r in new: seen.add(key(r)); rows.append(r)
        if len(page) < 500: break
        older = page[-1]['executed_at']
        if not new: break
    else:
        truncated = True
    out = []
    for r in rows:
        t = to_et(r['executed_at'])
        if t.strftime('%Y-%m-%d') != date: continue
        m = t.hour * 60 + t.minute
        if 9 * 60 + 30 <= m < 16 * 60: out.append(r)
    return out, pages, truncated
