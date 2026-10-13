"""Normalize the raw GeorgeFi trade exports (all epochs, all books) into one flat CSV plus coverage tables.
Usage: python3 -I normalize.py RAW_DIR OUT_DIR
Raw files are never modified. Every derived column is documented in OUT_DIR/README_normalized.md.
"""
import json, os, sys, csv, re, datetime, zoneinfo, collections, hashlib
RAW, OUT = sys.argv[1], sys.argv[2]; os.makedirs(OUT, exist_ok=True)
ET = zoneinfo.ZoneInfo('America/New_York')
epochs = {e['id']: e for e in json.load(open(f'{RAW}/epochs.json'))['epochs']}
SOURCES = [  # (file, epoch id, book label from the pull)
    ('trades_epoch_2714g69043m3csg.json', '2714g69043m3csg', 'v2.0.0-ict'),
    ('trades_book_v2.0.0-ict.json', 'aheqcv69vozw167', 'v2.0.0-ict'),
    ('trades_book_trade_now_v1.json', 'aheqcv69vozw167', 'trade_now_v1'),
    ('trades_book_singles_today_v1.json', 'aheqcv69vozw167', 'singles_today_v1'),
    ('trades_book_spx_plan_v1.json', 'aheqcv69vozw167', 'spx_plan_v1'),
]
def P(s):
    if not s: return None
    try: return datetime.datetime.fromisoformat(s.replace('Z', '+00:00').replace(' ', 'T'))
    except Exception: return None
OCC = re.compile(r'^O:([A-Z]+)(\d{6})([CP])(\d{8})$')
def side(action):
    a = (action or '').upper().replace('_', ' ')
    if 'CALL' in a: return 'CALL'
    if 'PUT' in a: return 'PUT'
    if 'SHARE' in a: return 'SHARES'
    return a or ''
KEY = ['epoch_number', 'epoch_id', 'book', 'trade_id', 'ticker', 'account_type', 'trade_type', 'action', 'side', 'strike', 'occ', 'occ_root', 'expiration', 'contract_text',
       'entry_utc', 'exit_utc', 'entry_et', 'exit_et', 'entry_date_et', 'hold_min', 'is_0dte', 'entry_premium', 'exit_premium', 'avg_entry_premium', 'size', 'initial_size',
       'pnl_reported', 'pnl_pct_reported', 'pnl_recomputed', 'pnl_mismatch', 'exit_reason', 'setup_grade', 'confidence', 'confidence_pre_cap', 'high_water_mark', 'entry_source',
       'gex_regime', 'n_confluence', 'data_error', 'source_file']
rows, seen = [], {}
cov = collections.defaultdict(lambda: collections.Counter()); n_by = collections.Counter()
WATCH = ['strike', 'optionSymbol', 'contract', 'expiration_date', 'entryTime', 'exitTime', 'entryPremium', 'exitPremium', 'avgEntryPremium', 'size', 'initial_size', 'pnl', 'pnlPercent',
         'exitReason', 'setupGrade', 'confidence', 'confidencePreCap', 'confluenceSignals', 'highWaterMark', 'entrySource', 'gexRegime', 'gexDirectionalBias', 'markPremium', 'quoteQuality',
         'riskBudget', 'entryDelta', 'entryIV', 'partial_pnl', 'scaleInExecuted', 'isChopDay', 'isGEXLotto', 'is_aplus_setup', 'exitLog', 'holdAdvisor', 'exit_log', 'ledger', 'decisionLedger', 'marketContext', 'market_context']
for fn, eid, book in SOURCES:
    d = json.load(open(f'{RAW}/{fn}'))
    for t in d['trades']:
        key = (eid, book, t['id'])
        if key in seen: continue
        seen[key] = 1; n_by[(eid, book)] += 1
        for k in WATCH:
            v = t.get(k)
            if v not in (None, '', [], {}): cov[(eid, book)][k] += 1
        e, x = P(t.get('entryTime')), P(t.get('exitTime'))
        occ = t.get('optionSymbol') or ''; m = OCC.match(occ)
        exp = (t.get('expiration_date') or '')[:10] or (('20' + m.group(2)[:2] + '-' + m.group(2)[2:4] + '-' + m.group(2)[4:]) if m else '')
        strike = t.get('strike')
        if (strike in (None, 0, '')) and m: strike = int(m.group(4)) / 1000
        sd = side(t.get('action'))
        sz = t.get('size') or 0; ep, xp = t.get('entryPremium'), t.get('exitPremium')
        mult = 1 if sd == 'SHARES' else 100
        recomputed = round((xp - ep) * mult * sz, 2) if isinstance(ep, (int, float)) and isinstance(xp, (int, float)) and sz else None
        pr = t.get('pnl')
        mism = (abs((pr or 0) - recomputed) > 1.0) if (recomputed is not None and pr is not None) else None
        edate = e.astimezone(ET).date().isoformat() if e else ''
        reason = t.get('exitReason') or ''
        rows.append(dict(epoch_number=epochs[eid]['epochNumber'], epoch_id=eid, book=book, trade_id=t['id'], ticker=t.get('ticker'), account_type=t.get('accountType'), trade_type=t.get('tradeType') or '',
            action=t.get('action'), side=sd, strike=strike, occ=occ, occ_root=m.group(1) if m else '', expiration=exp, contract_text=t.get('contract'),
            entry_utc=e.isoformat() if e else '', exit_utc=x.isoformat() if x else '', entry_et=e.astimezone(ET).isoformat() if e else '', exit_et=x.astimezone(ET).isoformat() if x else '',
            entry_date_et=edate, hold_min=round((x - e).total_seconds() / 60, 2) if e and x else '', is_0dte=(exp == edate) if exp and edate else '',
            entry_premium=ep, exit_premium=xp, avg_entry_premium=t.get('avgEntryPremium'), size=sz, initial_size=t.get('initial_size'), pnl_reported=pr, pnl_pct_reported=t.get('pnlPercent'),
            pnl_recomputed=recomputed, pnl_mismatch=mism, exit_reason=reason, setup_grade=t.get('setupGrade'), confidence=t.get('confidence'), confidence_pre_cap=t.get('confidencePreCap'),
            high_water_mark=t.get('highWaterMark'), entry_source=t.get('entrySource'), gex_regime=t.get('gexRegime'), n_confluence=len(t.get('confluenceSignals') or []),
            data_error=('DATA ERROR' in reason.upper() or 'INVALID' in reason.upper()), source_file=fn))
rows.sort(key=lambda r: (r['entry_utc'], r['trade_id']))
with open(f'{OUT}/trades.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=KEY); w.writeheader(); [w.writerow(r) for r in rows]
with open(f'{OUT}/field_coverage.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['epoch_id', 'epoch_number', 'book', 'n_trades'] + WATCH)
    for (eid, book), n in sorted(n_by.items()):
        w.writerow([eid, epochs[eid]['epochNumber'], book, n] + [f'{cov[(eid, book)][k] / n:.3f}' for k in WATCH])
# coverage report
by = collections.defaultdict(list)
for r in rows: by[(r['epoch_number'], r['book'])].append(r)
L = ['# Normalized GeorgeFi trade history: coverage', '', f'Source raw dir: `{os.path.basename(RAW)}`; rows: {len(rows)}', '',
     '| epoch | book | trades | first entry (ET) | last entry (ET) | 0DTE acct | SWING acct | options | shares | sum reported P&L | missing reported P&L | data-error exits | P&L mismatches (>$1) |', '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
for (en, book), rs in sorted(by.items()):
    L.append(f"| {en} | {book} | {len(rs)} | {rs[0]['entry_date_et']} | {rs[-1]['entry_date_et']} | {sum(1 for r in rs if r['account_type']=='0DTE')} | {sum(1 for r in rs if r['account_type']=='SWING')} | {sum(1 for r in rs if r['side'] in ('CALL','PUT'))} | {sum(1 for r in rs if r['side']=='SHARES')} | {sum((r['pnl_reported'] or 0) for r in rs):,.2f} | {sum(1 for r in rs if r['pnl_reported'] is None)} | {sum(1 for r in rs if r['data_error'])} | {sum(1 for r in rs if r['pnl_mismatch'])} |")
L += ['', '## Monthly counts (all books)', '', '| month (ET) | trades | sum reported P&L |', '|---|---|---|']
mo = collections.defaultdict(list)
for r in rows: mo[r['entry_date_et'][:7]].append(r)
for m, rs in sorted(mo.items()): L.append(f"| {m} | {len(rs)} | {sum((r['pnl_reported'] or 0) for r in rs):,.2f} |")
L += ['', '## Contract identification', '', f"Rows with an OCC symbol: {sum(1 for r in rows if r['occ'])}; without (share trades or missing): {sum(1 for r in rows if not r['occ'])}.",
      'OCC roots: ' + ', '.join(f'{k} {v}' for k, v in collections.Counter(r['occ_root'] for r in rows if r['occ']).most_common()), '',
      f"Rows flagged is_0dte (expiration == entry date ET): {sum(1 for r in rows if r['is_0dte'] is True)}; options not 0DTE: {sum(1 for r in rows if r['is_0dte'] is False)}.", '',
      '## Field coverage', '', 'See `field_coverage.csv` (fill rate per epoch and book for the fields the analysis uses). Fields absent in Epoch 1: ' + ', '.join(k for k in WATCH if all(cov[(eid, b)][k] == 0 for (eid, b) in n_by if epochs[eid]['epochNumber'] == 1)) + '.']
open(f'{OUT}/coverage_report.md', 'w').write('\n'.join(L) + '\n')
open(f'{OUT}/README_normalized.md', 'w').write('''# trades.csv columns
- epoch_number / epoch_id / book: from /api/epochs and the pull used (`source_file`).
- side: CALL / PUT / SHARES parsed from `action`. strike: reported `strike`, or parsed from the OCC symbol when 0/missing.
- occ: GeorgeFi `optionSymbol` (Massive/Polygon style, e.g. O:SPXW260227P06875000); occ_root: SPXW/NDXP/RUTW/SPY...; expiration: `expiration_date` or parsed from the OCC.
- entry_utc/exit_utc: `entryTime`/`exitTime` as given (UTC); *_et converted to America/New_York; hold_min = exit - entry.
- is_0dte: expiration equals the ET entry date.
- entry_premium/exit_premium/size/initial_size/pnl_reported/pnl_pct_reported: as reported by GeorgeFi (reported results, not independent).
- pnl_recomputed = (exit - entry) x 100 x size for options, x size for shares; pnl_mismatch = |reported - recomputed| > $1 (partials/scale-ins explain most).
- data_error: exit reason contains DATA ERROR / INVALID.
- n_confluence: number of confluence tags on the ledger; gex_regime/entry_source/confidence/high_water_mark: Epoch 2 only where present.
''')
print('rows', len(rows)); print(open(f'{OUT}/coverage_report.md').read())
