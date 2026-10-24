"""probe_entitlement.py — Compass Final, stage 1: what Theta serves for the fresh span (entitlement and coverage).

One ThetaData SDK login (the daily job's --source sdk path; the key loaded in-process from the scratchpad's
secrets/research.env, never printed or logged), requests one at a time. Every probe is on a NON-EXPIRY session
(2012-06-05, 2014-03-04, 2019-03-05 are Tuesdays with no SPY, QQQ or SPXW expiry, checked against Theta's expiration
lists at 7dfea57), so no probe reads a session any Compass Final family could trade. It prints, for each probe, whether
data came back, how many rows, and the first and last timestamps. Prices are not printed. Never between 00:00-01:45 or
19:40-20:30 New York.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
NY = ZoneInfo('America/New_York')
OUT = Path(__file__).resolve().parent / 'out' / 'probe_entitlement.json'


def load_key() -> None:
    if os.environ.get('THETADATA_KEY'):
        return
    for line in (SP / 'secrets' / 'research.env').read_text().splitlines():
        line = line.strip()
        if line.startswith('THETADATA_KEY='):
            os.environ['THETADATA_KEY'] = line.split('=', 1)[1].strip().strip('"').strip("'")


def red(s) -> str:
    s = str(s)
    k = os.environ.get('THETADATA_KEY') or ''
    if len(k) >= 4:
        s = s.replace(k, '[key]')
    return re.sub(r'td1_prod_[A-Za-z0-9_-]+', '[key]', s)


def allowed_now() -> bool:
    t = dt.datetime.now(NY).time()
    return not (dt.time(0, 0) <= t < dt.time(1, 45) or dt.time(19, 40) <= t < dt.time(20, 30))


def summary(df) -> dict:
    if df is None:
        return {'rows': 0}
    out = {'rows': df.height, 'columns': df.columns}
    for c in ('timestamp', 'created', 'last_trade', 'date'):
        if c in df.columns:
            v = df[c].drop_nulls()
            if len(v):
                out['first_' + c] = str(v.min())
                out['last_' + c] = str(v.max())
    for c in ('close', 'price', 'bid'):
        if c in df.columns:
            col = df[c]
            try:
                out['finite_' + c] = int(col.is_not_null().sum() - (col.is_nan().sum() if col.dtype.is_float() else 0))
            except Exception:  # noqa: BLE001
                pass
    if 'timestamp' in df.columns:
        ts = df['timestamp']
        try:
            hm = ts.dt.convert_time_zone('America/New_York').dt.strftime('%H:%M') if ts.dtype.time_zone else ts.dt.strftime('%H:%M')
            after = df.filter(hm >= '16:01')
            out['rows_after_1600'] = after.height
            if 'close' in after.columns:
                c = after['close']
                out['finite_close_after_1600'] = int(c.is_not_null().sum() - c.is_nan().sum())
            if 'volume' in after.columns:
                out['volume_after_1600'] = int(after['volume'].sum())
        except Exception as e:  # noqa: BLE001
            out['ts_note'] = red(e)[:120]
    return out


def main() -> None:
    if not allowed_now():
        raise SystemExit('outside the allowed hours')
    load_key()
    logging.getLogger('thetadata').setLevel(logging.ERROR)
    from thetadata import ThetaClient
    from thetadata.errors import NoDataFoundError
    c = ThetaClient(api_key=os.environ['THETADATA_KEY'], dataframe_type='polars')
    D = dt.date.fromisoformat
    probes = [
        ('SPY bars nqb 2014-03-04 09:30-17:31', lambda: c.stock_history_ohlc('SPY', interval='1m', date=D('2014-03-04'), start_time='09:30:00', end_time='17:31:00', venue='nqb')),
        ('SPY bars utp_cta 2014-03-04 09:30-17:31', lambda: c.stock_history_ohlc('SPY', interval='1m', date=D('2014-03-04'), start_time='09:30:00', end_time='17:31:00', venue='utp_cta')),
        ('SPY bars utp_cta 2012-06-05 09:30-17:31', lambda: c.stock_history_ohlc('SPY', interval='1m', date=D('2012-06-05'), start_time='09:30:00', end_time='17:31:00', venue='utp_cta')),
        ('SPY bars nqb 2019-03-05 09:30-17:31', lambda: c.stock_history_ohlc('SPY', interval='1m', date=D('2019-03-05'), start_time='09:30:00', end_time='17:31:00', venue='nqb')),
        ('SPY bars utp_cta 2019-03-05 09:30-17:31', lambda: c.stock_history_ohlc('SPY', interval='1m', date=D('2019-03-05'), start_time='09:30:00', end_time='17:31:00', venue='utp_cta')),
        ('QQQ bars nqb 2014-03-04 09:30-17:31', lambda: c.stock_history_ohlc('QQQ', interval='1m', date=D('2014-03-04'), start_time='09:30:00', end_time='17:31:00', venue='nqb')),
        ('SPY EOD 2014-03-03..2014-03-06', lambda: c.stock_history_eod('SPY', start_date=D('2014-03-03'), end_date=D('2014-03-06'))),
        ('QQQ EOD 2014-03-03..2014-03-06', lambda: c.stock_history_eod('QQQ', start_date=D('2014-03-03'), end_date=D('2014-03-06'))),
        ('SPX index price 2014-03-04 13:00-13:05', lambda: c.index_history_price('SPX', date=D('2014-03-04'), interval='1m', start_time='13:00:00', end_time='13:05:00')),
        ('SPX index price 2012-06-05 13:00-13:05', lambda: c.index_history_price('SPX', date=D('2012-06-05'), interval='1m', start_time='13:00:00', end_time='13:05:00')),
        ('SPY option quotes exp 2014-03-07 on 2014-03-04 15:00-15:02', lambda: c.option_history_quote(symbol='SPY', expiration=D('2014-03-07'), date=D('2014-03-04'), interval='1m', strike='*', right='both', start_time='15:00:00', end_time='15:02:00')),
        ('SPY option quotes exp 2012-06-08 on 2012-06-05 15:00-15:02', lambda: c.option_history_quote(symbol='SPY', expiration=D('2012-06-08'), date=D('2012-06-05'), interval='1m', strike='*', right='both', start_time='15:00:00', end_time='15:02:00')),
        ('QQQ option quotes exp 2014-03-07 on 2014-03-04 15:00-15:02', lambda: c.option_history_quote(symbol='QQQ', expiration=D('2014-03-07'), date=D('2014-03-04'), interval='1m', strike='*', right='both', start_time='15:00:00', end_time='15:02:00')),
        ('SPXW option quotes exp 2014-03-07 on 2014-03-04 13:00-13:01', lambda: c.option_history_quote(symbol='SPXW', expiration=D('2014-03-07'), date=D('2014-03-04'), interval='1m', strike='*', right='both', start_time='13:00:00', end_time='13:01:00')),
        ('SPXW option quotes exp 2012-06-08 on 2012-06-05 13:00-13:01', lambda: c.option_history_quote(symbol='SPXW', expiration=D('2012-06-08'), date=D('2012-06-05'), interval='1m', strike='*', right='both', start_time='13:00:00', end_time='13:01:00')),
    ]
    res = []
    for name, fn in probes:
        if not allowed_now():
            res.append({'probe': name, 'status': 'stopped: outside the allowed hours'})
            break
        t0 = dt.datetime.now(NY)
        try:
            df = fn()
            r = {'probe': name, 'status': 'ok', **summary(df)}
        except NoDataFoundError as e:
            r = {'probe': name, 'status': 'no data', 'error': red(e)[:200]}
        except Exception as e:  # noqa: BLE001
            r = {'probe': name, 'status': type(e).__name__, 'error': red(e)[:300]}
        r['at'] = t0.isoformat(timespec='seconds')
        res.append(r)
        print(red(json.dumps(r, default=str)), flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(red(json.dumps(res, indent=1, default=str)))


if __name__ == '__main__':
    sys.exit(main())
