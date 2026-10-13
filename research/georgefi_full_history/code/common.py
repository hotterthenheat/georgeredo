"""Shared loaders for the full-history reconstruction (ledger + paper book, UW bars via backtest/data.py)."""
import sys, os, csv, json, time, datetime, zoneinfo
sys.path.insert(0, '/home/user/georgeredo/backtest')
import data  # noqa: E402  (UW client; token from env only, gzip cache at BT_CACHE)

ROOT = '/home/user/georgeredo/research/georgefi_full_history'
NORM = ROOT + '/normalized'
RES = ROOT + '/results'
ET = zoneinfo.ZoneInfo('America/New_York')
UTC = datetime.timezone.utc
INDEX_ROOTS = {'SPXW', 'SPX', 'NDXP', 'NDX', 'RUTW', 'RUT'}


def trading_days():
    td = json.load(open('/home/user/georgeredo/backtest/trading_days.json'))
    # the file ends 2026-10-12; the ledger runs to 2026-10-13 (a Tuesday) -> extend in memory only
    last = datetime.date.fromisoformat(td[-1])
    d = last + datetime.timedelta(days=1)
    while d <= datetime.date(2026, 10, 13):
        if d.weekday() < 5: td.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return td


def parse_utc(s):
    s = s.strip().replace(' ', 'T').replace('Z', '+00:00')
    return datetime.datetime.fromisoformat(s)


def cid_from_occ(occ):
    return occ[2:] if occ.startswith('O:') else occ


def occ_root(occ):
    cid = cid_from_occ(occ)
    i = 0
    while i < len(cid) and not cid[i].isdigit(): i += 1
    return cid[:i]


def load_ledger():
    """Normalized ledger rows (1,149) with parsed fields added."""
    rows = list(csv.DictReader(open(NORM + '/trades.csv')))
    out = []
    for r in rows:
        d = dict(r)
        d['group'] = 'ledger'; d['size_implied'] = False
        d['epoch'] = r['epoch_number']
        d['entry_dt'] = parse_utc(r['entry_utc']).astimezone(ET)
        d['exit_dt'] = parse_utc(r['exit_utc']).astimezone(ET) if r['exit_utc'] else None
        d['entry_date'] = d['entry_dt'].strftime('%Y-%m-%d')
        d['exit_date'] = d['exit_dt'].strftime('%Y-%m-%d') if d['exit_dt'] else None
        d['cid'] = cid_from_occ(r['occ']) if r['occ'] else ''
        d['root'] = r['occ_root'] or r['ticker']
        d['size_n'] = float(r['size'] or 0)
        d['entry_px'] = float(r['entry_premium']) if r['entry_premium'] else None
        d['exit_px'] = float(r['exit_premium']) if r['exit_premium'] else None
        d['pnl'] = float(r['pnl_reported']) if r['pnl_reported'] else None
        d['is_option'] = r['side'] in ('CALL', 'PUT')
        d['is_shares'] = r['side'] == 'SHARES'
        d['dte0'] = r['is_0dte'] == 'True'
        d['data_err'] = r['data_error'] == 'True'
        d['mismatch'] = r['pnl_mismatch'] == 'True'
        d['month'] = d['entry_date'][:7]
        d['hold'] = float(r['hold_min']) if r['hold_min'] else None
        out.append(d)
    return out


def load_paper():
    """SPX paper book (spx_gex_engine), mapped onto the ledger schema; group='paper'."""
    f = NORM + '/paper_trades_spx.csv'
    if not os.path.exists(f): return []
    out = []
    for r in csv.DictReader(open(f)):
        if not r.get('exitTime'): continue
        occ = r['optionSymbol']
        e = parse_utc(r['entryTime']).astimezone(ET); x = parse_utc(r['exitTime']).astimezone(ET)
        cid = cid_from_occ(occ)
        exp = '20' + cid[len(occ_root(occ)):len(occ_root(occ)) + 6]
        exp = f'{exp[:4]}-{exp[4:6]}-{exp[6:8]}'
        d = dict(group='paper', epoch='paper', epoch_number='paper', book='spx_gex_engine_paper', trade_id=r['id'], ticker=r['ticker'],
                 account_type='0DTE', trade_type='PAPER', action=r['action'], side='CALL' if 'CALL' in r['action'] else 'PUT',
                 strike=r['strike'], occ=occ, occ_root=occ_root(occ), expiration=exp, entry_utc=r['entryTime'], exit_utc=r['exitTime'],
                 entry_et=e.isoformat(), exit_et=x.isoformat(), entry_date_et=e.strftime('%Y-%m-%d'),
                 hold_min=f'{(x - e).total_seconds() / 60:.2f}', is_0dte=str(exp == e.strftime('%Y-%m-%d')),
                 entry_premium=r['entryPremium'], exit_premium=r['exitPremium'], size=r['size'], initial_size=r['size'],
                 pnl_reported=r['pnl'], pnl_pct_reported=r['pnlPercent'], exit_reason=r['exitReason'], setup_grade=r['setupGrade'],
                 data_error=str('DATA ERROR' in r['exitReason'].upper() or 'INVALID' in r['exitReason'].upper()), pnl_mismatch='False',
                 pricing_source=r.get('pricingSource', ''))
        ep = float(r['entryPremium'] or 0); xp = float(r['exitPremium'] or 0); sz = float(r['size'] or 0); pnl = float(r['pnl'] or 0)
        # 17 paper rows are reported with size 0 (post-close size); imply the lot from pnl / ((exit - entry) x 100) when it is a whole number
        d['size_implied'] = False
        if sz == 0 and xp != ep:
            s_ = pnl / ((xp - ep) * 100)
            if abs(s_ - round(s_)) < 0.01 and round(s_) > 0: sz = float(round(s_)); d['size_implied'] = True; d['size'] = str(int(sz))
        d['pnl_recomputed'] = f'{(xp - ep) * 100 * sz:.2f}'
        d['pnl_mismatch'] = str(abs((xp - ep) * 100 * sz - pnl) > 1.0)  # remaining mismatches = partial exits (T1 PARTIAL) on 2-lot entries
        d['entry_dt'] = e; d['exit_dt'] = x; d['entry_date'] = e.strftime('%Y-%m-%d'); d['exit_date'] = x.strftime('%Y-%m-%d')
        d['cid'] = cid; d['root'] = occ_root(occ); d['size_n'] = sz; d['entry_px'] = ep; d['exit_px'] = xp; d['pnl'] = pnl
        d['is_option'] = True; d['is_shares'] = False; d['dte0'] = d['is_0dte'] == 'True'; d['data_err'] = d['data_error'] == 'True'
        d['mismatch'] = d['pnl_mismatch'] == 'True'; d['month'] = d['entry_date'][:7]; d['hold'] = (x - e).total_seconds() / 60
        out.append(d)
    return out


def load_all():
    return load_ledger() + load_paper()


def _get_retry(path, params):
    """data.get with one retry on a cache read failure (other agents write the same cache dir)."""
    for attempt in range(2):
        try:
            return data.get(path, params)
        except Exception as e:  # truncated gzip / partial JSON while another process writes the file
            if attempt == 0: time.sleep(1.5); continue
            return {'error': 'cache_read_fail:' + type(e).__name__}


def option_payload(cid, date):
    return _get_retry(f'option-contract/{cid}/intraday', {'date': date})


def underlying_payload(ticker, date):
    return _get_retry(f'stock/{ticker}/ohlc/1m', {'date': date, 'limit': 2000})


def option_bars(cid, date):
    """Same parsing as data.option_bars but from the retry-wrapped payload. Bars sorted by t (ET)."""
    d = option_payload(cid, date)
    if not isinstance(d, dict) or 'error' in d: return []
    rows = d.get('data') or []
    out = []
    for r in rows:
        try:
            out.append(dict(t=data.et(r['start_time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close']),
                            vw=float(r['avg_price']) if r.get('avg_price') else None,
                            vol=int(r.get('volume_ask_side') or 0) + int(r.get('volume_bid_side') or 0) + int(r.get('volume_mid_side') or 0) + int(r.get('volume_no_side') or 0),
                            ask_p=float(r.get('premium_ask_side') or 0), bid_p=float(r.get('premium_bid_side') or 0)))
        except Exception: continue
    out.sort(key=lambda b: b['t'])
    return out


def underlying_bars(ticker, date):
    """RTH 1-minute bars of the underlying (same filter as data.underlying_bars); vw=None, vol from 'volume'."""
    d = underlying_payload(ticker, date)
    if not isinstance(d, dict) or 'error' in d: return []
    out = []
    for r in d.get('data') or []:
        try:
            b = dict(t=data.et(r['start_time']), o=float(r['open']), h=float(r['high']), l=float(r['low']), c=float(r['close']), vw=None, vol=int(r.get('volume') or 0), ask_p=0.0, bid_p=0.0)
        except Exception: continue
        if b['t'].strftime('%Y-%m-%d') != date or r.get('market_time') != 'r': continue
        out.append(b)
    out.sort(key=lambda b: b['t'])
    return out


def bar_at(bars, when):
    """Bar whose minute contains `when` (ET-aware datetime), else None."""
    m = when.replace(second=0, microsecond=0)
    for b in bars:
        if b['t'] == m: return b
        if b['t'] > m: return None
    return None


def first_bar_after(bars, when):
    """(index, bar) of the first bar strictly after the minute containing `when`."""
    m = when.replace(second=0, microsecond=0)
    for i, b in enumerate(bars):
        if b['t'] > m: return i, b
    return None, None


def vwap(b):
    return b['vw'] if b.get('vw') else b['c']
