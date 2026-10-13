"""Build manifest.csv.gz (one row per file) and MANIFEST.md for the 0DTE dataset.  Reads every parquet under $THETA_DS_ROOT,
the builder's _jobs.jsonl / progress.json, and verify.json (written by verify.py) when present.  No network access.
Usage: python3 -I manifest.py"""
import os, sys, csv, gzip, json, hashlib, datetime as dt, collections
import polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import load as L
ROOT = L.ROOT
KINDS = [('chains', ['SPY', 'QQQ', 'SPXW', 'IWM']), ('ohlc', ['SPY', 'QQQ', 'SPXW', 'IWM']), ('underlying', ['SPY', 'QQQ', 'IWM']), ('index', ['SPX', 'VIX'])]
U_START, U_END = '2017-06-01', '2026-10-09'

def expected(kind, sym):
    if kind in ('chains', 'ohlc'): return L.trading_sessions(L.FIRST_DAILY[sym], U_END)
    return L.trading_sessions(U_START, U_END)

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()

def main():
    jobs = {}
    jl = os.path.join(ROOT, '_jobs.jsonl')
    if os.path.exists(jl):
        for line in open(jl):
            r = json.loads(line); k = ('chains' if r['kind'] == 'chain' else r['kind'], r['sym'], r['date'])
            if r['kind'] in ('chain', 'ohlc'): jobs[k] = r          # last record wins
    rows = []; summary = collections.OrderedDict(); missing = {}; nodata = {}; empty = {}; fallback = {}
    for kind, syms in KINDS:
        for sym in syms:
            exp = expected(kind, sym); have = set(L.sessions(kind, sym)); nd = set(L.nodata_sessions(kind, sym))
            s = dict(expected=len(exp), files=0, nodata=len(nd & set(exp)), missing=0, empty=0, rows=0, bytes=0, strikes_min=None, strikes_max=None, fallback_ref=0)
            miss = [d for d in exp if d not in have and d not in nd]
            missing[(kind, sym)] = miss; nodata[(kind, sym)] = sorted(nd & set(exp)); empty[(kind, sym)] = []; fallback[(kind, sym)] = []
            for d in sorted(have):
                p = L.path(kind, sym, d); df = pl.read_parquet(p); b = os.path.getsize(p)
                r = dict(data_type=kind, symbol=sym, date=d, rows=df.height, bytes=b, sha256=sha256(p), strikes=None, min_strike=None, max_strike=None,
                         ref_price=None, ref_time=None, ref_status=None, band_lo=None, band_hi=None, raw_rows=None, raw_strikes=None, in_calendar=int(d in set(exp)))
                if 'strike' in df.columns:
                    ks = df['strike'].unique(); r.update(strikes=len(ks), min_strike=(float(ks.min()) if len(ks) else None), max_strike=(float(ks.max()) if len(ks) else None))
                    j = jobs.get((kind, sym, d), {})
                    r.update(ref_price=j.get('ref_price'), ref_time=j.get('ref_time'), ref_status=j.get('ref_status'), band_lo=j.get('band_lo'), band_hi=j.get('band_hi'), raw_rows=j.get('raw_rows'), raw_strikes=j.get('raw_strikes'))
                    if j.get('ref_status') == 'fallback': s['fallback_ref'] += 1; fallback[(kind, sym)].append(d)
                    if r['strikes'] is not None:
                        s['strikes_min'] = r['strikes'] if s['strikes_min'] is None else min(s['strikes_min'], r['strikes'])
                        s['strikes_max'] = r['strikes'] if s['strikes_max'] is None else max(s['strikes_max'], r['strikes'])
                if df.height == 0: s['empty'] += 1; empty[(kind, sym)].append(d)
                s['files'] += 1; s['rows'] += df.height; s['bytes'] += b; rows.append(r)
            s['missing'] = len(miss); summary[(kind, sym)] = s
            print(kind, sym, json.dumps(s), flush=True)
    cols = ['data_type', 'symbol', 'date', 'rows', 'strikes', 'min_strike', 'max_strike', 'ref_price', 'ref_time', 'ref_status', 'band_lo', 'band_hi', 'raw_rows', 'raw_strikes', 'in_calendar', 'bytes', 'sha256']
    with gzip.open(os.path.join(HERE, 'manifest.csv.gz'), 'wt', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c: r.get(c) for c in cols})
    prog = json.load(open(os.path.join(ROOT, 'progress.json'))) if os.path.exists(os.path.join(ROOT, 'progress.json')) else {}
    ver = json.load(open(os.path.join(HERE, 'verify.json'))) if os.path.exists(os.path.join(HERE, 'verify.json')) else None
    tot_rows = sum(s['rows'] for s in summary.values()); tot_bytes = sum(s['bytes'] for s in summary.values())
    md = []
    md.append('# ThetaData 0DTE research dataset — manifest\n')
    md.append(f'Generated {dt.datetime.now().isoformat(timespec="seconds")} from `{ROOT}` (outside the repo). One row per file in `manifest.csv.gz` '
              f'(columns: {", ".join(cols)}). Loader: `load.py`; build/verify commands: `README.md`.\n')
    md.append('## Scope\n')
    md.append('| Symbol | First daily-expiry date (every weekday session has an expiration, from `option_list_expirations`) | Chain sessions to 2026-10-09 |\n|---|---|---|')
    for sym in ('SPY', 'QQQ', 'SPXW', 'IWM'): md.append(f'| {sym} | {L.FIRST_DAILY[sym]} | {len(expected("chains", sym))} |')
    md.append('\nChains/OHLC: same-day expiration, both rights, 1-minute, strikes within ±2.0 % of the 09:31 underlying print (ETFs: open of the 09:31 bar; SPXW: SPX index value at 09:31:00), 09:30–16:00 ET. '
              'Underlying (SPY, QQQ, IWM 1-minute OHLC) and index (SPX, VIX 1-minute price) cover every NYSE session 2017-06-01 → 2026-10-09 (SPX, VIX and SPY converted from the index_tests cache pulled 2026-10-13 with the same client; QQQ and IWM fetched here).\n')
    md.append('## Files per data type and symbol\n')
    md.append('| Data type | Symbol | Expected sessions | Files | No-data (API) | Missing (not fetched) | Empty files | Fallback ref | Strikes/file min–max | Rows | MB |\n|---|---|---|---|---|---|---|---|---|---|---|')
    for (kind, sym), s in summary.items():
        md.append(f"| {kind} | {sym} | {s['expected']} | {s['files']} | {s['nodata']} | {s['missing']} | {s['empty']} | {s['fallback_ref']} | {s['strikes_min']}–{s['strikes_max']} | {s['rows']:,} | {s['bytes']/1e6:,.1f} |")
    md.append(f'\n**Total: {len(rows):,} files, {tot_rows:,} rows, {tot_bytes/1e9:.2f} GB.**\n')
    md.append('## Sessions without data\n')
    for (kind, sym) in summary:
        parts = []
        if nodata[(kind, sym)]: parts.append(f"API no-data ({len(nodata[(kind, sym)])}): {', '.join(nodata[(kind, sym)][:40])}{' …' if len(nodata[(kind, sym)]) > 40 else ''}")
        if missing[(kind, sym)]: parts.append(f"not fetched ({len(missing[(kind, sym)])}): {', '.join(missing[(kind, sym)][:40])}{' …' if len(missing[(kind, sym)]) > 40 else ''}")
        if empty[(kind, sym)]: parts.append(f"empty ({len(empty[(kind, sym)])}): {', '.join(empty[(kind, sym)][:40])}")
        if fallback[(kind, sym)]: parts.append(f"fallback 09:31 reference ({len(fallback[(kind, sym)])}): {', '.join(fallback[(kind, sym)][:20])}")
        md.append(f"- {kind}/{sym}: " + ('; '.join(parts) if parts else 'complete'))
    if prog:
        md.append('\n## Build run\n')
        md.append(f"progress.json: done={prog.get('done')} pending={prog.get('pending')} elapsed={prog.get('elapsed_s')} s, login generations={prog.get('login_gen')}, final={prog.get('final')}; per job class ok/nodata/err/unauth: " + ', '.join(f"{k}: {v['ok']}/{v['nodata']}/{v['err']}/{v['unauth']}" for k, v in prog.get('stats', {}).items()))
    md.append('\n## Verification (verify.py)\n')
    if ver:
        md.append(f"Fresh 1-second NBBO pulls on {ver['date']} for {len(ver['checks'])} random session files; at every minute boundary present in both series the 1-minute row must equal the 1-second row (bid, ask, bid_size, ask_size).\n")
        md.append('| Symbol | Date | Strike | Right | 1-min rows | 1-sec rows | Minutes compared | Mismatches | Result |\n|---|---|---|---|---|---|---|---|---|')
        for c in ver['checks']:
            md.append(f"| {c['symbol']} | {c['date']} | {c['strike']} | {c['right']} | {c.get('rows_1m')} | {c.get('rows_1s')} | {c.get('compared')} | {c.get('mismatches')} | {c.get('result')} |")
        if ver.get('notes'): md.append('\n' + '\n'.join('- ' + n for n in ver['notes']))
    else:
        md.append('verify.json not found: verification not run.')
    open(os.path.join(HERE, 'MANIFEST.md'), 'w').write('\n'.join(md) + '\n')
    print('wrote', os.path.join(HERE, 'MANIFEST.md'), 'and manifest.csv.gz;', len(rows), 'files', tot_rows, 'rows', round(tot_bytes / 1e9, 3), 'GB')

if __name__ == '__main__':
    main()
