#!/usr/bin/env python3
"""
fetch_postmarket_1m.py — fetch UW 1-minute bars (they include the post-market `po` rows) for the name-sessions
afterhours.py lists without a decision price, and keep each answer as fetched under data/postmarket_1m/<T>/<D>.json.gz.

The owner's permission (2026-10-22, relayed): one call per missing name-session, ONE call at a time with a pause
between calls (the terminal recorder shares the token's three-at-once limit), backing off on 429. The token is read
from the environment (UW_API_TOKEN, sent as a Bearer header) and is never printed, logged or written; the cached file
is the response body alone. A name-session already cached is never asked again, so afterhours.py re-runs make no call.

    set -a; . <research.env>; set +a
    python3 -I fetch_postmarket_1m.py SPY:2026-10-12 QQQ:2026-10-12 …      # or --from-coverage (reads out/afterhours_coverage.csv)
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
CACHE = REPO / 'data' / 'postmarket_1m'
BASE = 'https://api.unusualwhales.com/api/stock/{t}/ohlc/1m?date={d}&limit=2000'
PAUSE = 2.0


def want_from_coverage() -> list[tuple[str, str]]:
    import csv
    rows = csv.DictReader(open(HERE / 'out' / 'afterhours_coverage.csv', encoding='utf-8'))
    return [(r['name'], r['day']) for r in rows if not r['decision_px']]


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('pairs', nargs='*', help='NAME:YYYY-MM-DD')
    p.add_argument('--from-coverage', action='store_true')
    a = p.parse_args(argv)
    want = want_from_coverage() if a.from_coverage else [tuple(x.split(':')) for x in a.pairs]
    tok = os.environ.get('UW_API_TOKEN')
    if not tok:
        sys.exit('UW_API_TOKEN is not set')
    ctx = ssl.create_default_context(cafile=os.environ.get('SSL_CERT_FILE') or ('/root/.ccr/ca-bundle.crt' if Path('/root/.ccr/ca-bundle.crt').exists() else None))
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx), urllib.request.ProxyHandler())
    failed = []
    for t, d in want:
        out = CACHE / t / f'{d}.json.gz'
        if out.exists():
            print(f'{t} {d}: cached')
            continue
        wait = 30.0
        for attempt in range(6):
            req = urllib.request.Request(BASE.format(t=t, d=d), headers={'Authorization': f'Bearer {tok}', 'Accept': 'application/json'})
            try:
                with opener.open(req, timeout=60) as r:
                    body = r.read()
                    status = r.status
            except urllib.error.HTTPError as e:
                body, status = e.read(), e.code
            except (urllib.error.URLError, TimeoutError) as e:
                body, status = str(e).encode(), -1
            if status == 429:
                print(f'{t} {d}: 429, waiting {wait:.0f} s')
                time.sleep(wait)
                wait = min(wait * 2, 600)
                continue
            break
        if status == 200:
            try:
                n = len(json.loads(body)['data'])
            except (ValueError, KeyError, TypeError):
                n = None
            if n:
                out.parent.mkdir(parents=True, exist_ok=True)
                tmp = out.with_suffix('.part')
                with gzip.GzipFile(tmp, 'wb', mtime=0) as g:
                    g.write(body)
                tmp.rename(out)
                print(f'{t} {d}: 200, {n} rows')
            else:
                failed.append((t, d, status, 'no rows'))
                print(f'{t} {d}: 200 with no rows')
        else:
            failed.append((t, d, status, body[:200].decode('utf-8', 'replace')))
            print(f'{t} {d}: status {status}')
        time.sleep(PAUSE)
    if failed:
        print('could not answer:', json.dumps(failed))
    return 0


if __name__ == '__main__':
    sys.exit(main())
