#!/usr/bin/env python3
"""
check_integrity.py — the replay's reproducibility and bookkeeping, read from its rows (never written):

  integrity(root)            sessions expected (the NYSE calendar written out in audit_lib) vs replayed (the replay's
                             _replay/days_*.json), every excluded day and why; rows by kind; no (candidate, name, day,
                             minute, structure, row kind, settle source) twice; every capture has exactly one settle row,
                             every fly5 capture exactly one 15:58 row; no settle or 15:58 row without its capture; the
                             macro stamps on the rows against data/macro_events_2022_2027.json.
  determinism(a, b, csv_a, csv_b)
                             two replay roots compared file by file on their rows' SORTED contents (a SHA-256 of the
                             rows written as CSV after sorting on every column), and the two report CSVs byte for byte.

    python3 -I check_integrity.py --root data_recorder/paper_backtest [--rerun-root DIR --csv A --rerun-csv B]
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from collections import Counter
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_lib as A  # noqa: E402


def read_days(root: Path) -> dict:
    out: dict = {}
    d = Path(root) / '_replay'
    for f in sorted(d.glob('days_*.json'), key=lambda x: x.stat().st_mtime) if d.is_dir() else []:
        out.update(json.loads(f.read_text(encoding='utf-8')))
    return out


def integrity(root: Path, start: str = A.HIST_START, end: str = A.HIST_END) -> dict:
    root = Path(root)
    df = A.load_rows(root, start=start, end=end)
    days = {d: v for d, v in read_days(root).items() if start <= d <= end}
    exp = A.expected_sessions(start, end)
    replayed = sorted(d for d, v in days.items() if v['status'] == 'replayed')
    res: dict = {'range': [start, end], 'weekdays': len(A.weekdays(start, end)), 'expected_full_sessions': len(exp),
                 'replayed_sessions': len(replayed), 'status_counts': dict(Counter(v['status'] for v in days.values())),
                 'expected_not_replayed': sorted(set(exp) - set(replayed)), 'replayed_not_expected': sorted(set(replayed) - set(exp)),
                 'excluded': {d: v['status'] + (f" ({v.get('note')})" if v.get('note') else '') for d, v in sorted(days.items()) if v['status'] != 'replayed'},
                 'days_with_missing_files': {d: v['missing'] for d, v in days.items() if v.get('missing')},
                 'calendar_holidays_in_range': sorted(d for d in A.NYSE_HOLIDAYS if start <= d <= end and dt_weekday(d) < 5),
                 'calendar_half_days_in_range': sorted(d for d in A.NYSE_HALF_DAYS if start <= d <= end)}
    # Theta's EOD dates as a second calendar
    try:
        eod = A.theta_eod(('SPY',))
        eod_days = set(eod.filter((pl.col('day') >= start) & (pl.col('day') <= end))['day'].to_list())
        full = eod_days - set(A.NYSE_HALF_DAYS)
        res['theta_eod_sessions'] = len(eod_days)
        res['theta_eod_full_sessions'] = len(full)
        res['theta_eod_vs_calendar'] = {'eod_not_calendar': sorted(full - set(exp)), 'calendar_not_eod': sorted(set(exp) - full)}
    except Exception as e:  # noqa: BLE001
        res['theta_eod_error'] = f'{type(e).__name__}: {e}'
    if df.height == 0:
        res['rows'] = 0
        return res
    res['rows'] = df.height
    res['files'] = int(df['_file'].n_unique())
    res['rows_by_kind'] = {f'{a}/{b}': c for (a, b), c in Counter(zip(df['candidate'].to_list(), df['row_kind'].to_list())).items()}
    key = ['candidate', '_name', '_day', 'minute', 'structure', 'row_kind', 'settle_source']
    dup = df.group_by(key).len().filter(pl.col('len') > 1)
    res['duplicate_keys'] = dup.height
    res['duplicate_examples'] = dup.head(5).to_dicts()
    k5 = ['candidate', '_name', '_day', 'minute', 'structure']
    caps = df.filter(pl.col('row_kind') == 'capture')
    sett = df.filter(pl.col('row_kind') == 'settle')
    clos = df.filter(pl.col('row_kind') == 'close1558')
    res['settle_sources'] = dict(Counter(sett['settle_source'].to_list()))
    res['close_official_from'] = dict(Counter(sett['close_official_from'].to_list())) if 'close_official_from' in sett.columns else {}
    sc = sett.group_by(k5).len()
    j = caps.select(k5 + ['tradable']).join(sc, on=k5, how='left').with_columns(pl.col('len').fill_null(0))
    res['captures'] = caps.height
    res['captures_tradable'] = int((caps['tradable'] == 'true').sum())
    res['captures_with_settle_count'] = dict(Counter(j['len'].to_list()))
    res['tradable_captures_settle_count'] = dict(Counter(j.filter(pl.col('tradable') == 'true')['len'].to_list()))
    res['captures_without_legs'] = int(caps['l1_symbol'].is_null().sum())
    res['captures_without_legs_tradable'] = int((caps['l1_symbol'].is_null() & (caps['tradable'] == 'true')).sum())
    res['settle_without_capture'] = sett.select(k5).join(caps.select(k5), on=k5, how='anti').height
    res['settle_tradable_rows'] = int((sett['tradable'] == 'true').sum())
    f5 = caps.filter(pl.col('candidate') == 'fly5')
    cc = clos.group_by(k5).len()
    jf = f5.select(k5).join(cc, on=k5, how='left').with_columns(pl.col('len').fill_null(0))
    res['fly5_captures_with_1558_count'] = dict(Counter(jf['len'].to_list()))
    jt = f5.filter(pl.col('tradable') == 'true').select(k5).join(cc, on=k5, how='left').with_columns(pl.col('len').fill_null(0))
    res['fly5_tradable_with_1558_count'] = dict(Counter(jt['len'].to_list()))
    res['close1558_without_capture'] = clos.select(k5).join(caps.select(k5), on=k5, how='anti').height
    res['close1558_with_value'] = int(clos['pnl_1558_nbbo_f'].is_not_null().sum()) if 'pnl_1558_nbbo_f' in clos.columns else 0
    res['close1558_reasons'] = dict(Counter(x for x in clos['close_reason'].to_list() if x)) if 'close_reason' in clos.columns else {}
    # sessions and minutes per candidate
    per: dict = {}
    for k in A.KEYS:
        c = caps.filter(pl.col('candidate') == k)
        want = len(A.MINUTES[k]) * len(A.STRUCTS[k])
        g = c.group_by('_name', '_day').len()
        short = g.filter(pl.col('len') != want)
        ds = set(c['_day'].to_list())
        per[k] = {'sessions_with_captures': len(ds), 'captures': c.height,
                  'name_sessions_short_of_minutes': short.height, 'expected_without_capture': sorted(set(exp) - ds)[:20],
                  'settled_trades': int(sett.filter((pl.col('candidate') == k) & (pl.col('tradable') == 'true')).height),
                  'sessions_with_settled_trade': int(sett.filter((pl.col('candidate') == k) & (pl.col('tradable') == 'true'))['_day'].n_unique())}
    res['per_candidate'] = per
    # the macro stamps against the file
    md = A.macro_days()
    st = caps.select('_day', 'is_macro_event_day', 'macro_events').unique()
    bad = [r for r in st.to_dicts() if (r['is_macro_event_day'] == 'true') != (r['_day'] in md)]
    res['macro_stamp_disagreements'] = len(bad)
    res['macro_stamp_examples'] = bad[:5]
    return res


def dt_weekday(d: str) -> int:
    import datetime as dt
    return dt.date.fromisoformat(d).weekday()


def rows_digest(f: Path) -> tuple[str, int, list]:
    d = pl.read_parquet(f)
    cols = sorted(d.columns)
    d = d.select(cols).sort(cols, nulls_last=True)
    buf = io.BytesIO()
    d.write_csv(buf)
    return hashlib.sha256(buf.getvalue()).hexdigest(), d.height, cols


def determinism(a: Path, b: Path, csv_a: Path | None = None, csv_b: Path | None = None) -> dict:
    a, b = Path(a), Path(b)
    fa = {str(p.relative_to(a)): p for p in A.row_files(a)}
    fb = {str(p.relative_to(b)): p for p in A.row_files(b)}
    res = {'files_a': len(fa), 'files_b': len(fb), 'only_a': sorted(set(fa) - set(fb))[:20], 'only_b': sorted(set(fb) - set(fa))[:20],
           'n_only_a': len(set(fa) - set(fb)), 'n_only_b': len(set(fb) - set(fa))}
    same = diff = 0
    examples = []
    diff_cols: Counter = Counter()
    for k in sorted(set(fa) & set(fb)):
        ha, na, ca = rows_digest(fa[k])
        hb, nb, cb = rows_digest(fb[k])
        if ha == hb:
            same += 1
            continue
        diff += 1
        da, db = pl.read_parquet(fa[k]), pl.read_parquet(fb[k])
        if ca != cb or na != nb:
            examples.append({'file': k, 'rows': [na, nb], 'cols_only_a': sorted(set(ca) - set(cb)), 'cols_only_b': sorted(set(cb) - set(ca))})
            continue
        kk = ['row_kind', 'minute', 'structure', 'settle_source']
        da, db = da.sort(kk, nulls_last=True), db.sort(kk, nulls_last=True)
        cols = [c for c in ca if not da[c].cast(pl.Utf8).fill_null('∅').equals(db[c].cast(pl.Utf8).fill_null('∅'))]
        diff_cols.update(cols)
        if len(examples) < 10:
            examples.append({'file': k, 'columns_differ': cols})
    res.update({'files_same': same, 'files_differ': diff, 'differ_examples': examples, 'differing_columns': dict(diff_cols)})
    if csv_a and csv_b:
        ba, bb = Path(csv_a).read_bytes(), Path(csv_b).read_bytes()
        res['csv'] = {'a': str(csv_a), 'b': str(csv_b), 'sha_a': hashlib.sha256(ba).hexdigest(), 'sha_b': hashlib.sha256(bb).hexdigest(),
                      'identical': ba == bb, 'bytes': [len(ba), len(bb)]}
        if ba != bb:
            la, lb = ba.decode().splitlines(), bb.decode().splitlines()
            nd = [i for i in range(min(len(la), len(lb))) if la[i] != lb[i]]
            res['csv']['lines'] = [len(la), len(lb)]
            res['csv']['lines_differ'] = len(nd)
            res['csv']['first_diffs'] = [(i, la[i][:160], lb[i][:160]) for i in nd[:5]]
    return res


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--root', default=str(A.REPO / 'data_recorder' / 'paper_backtest'))
    p.add_argument('--start', default=A.HIST_START)
    p.add_argument('--end', default=A.HIST_END)
    p.add_argument('--rerun-root')
    p.add_argument('--csv')
    p.add_argument('--rerun-csv')
    p.add_argument('--out', default=str(A.OUT))
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    res = integrity(Path(a.root), a.start, a.end)
    (out / 'integrity.json').write_text(json.dumps(res, indent=1, default=str), encoding='utf-8')
    print(json.dumps({k: v for k, v in res.items() if k not in ('excluded',)}, indent=1, default=str)[:6000])
    if a.rerun_root:
        det = determinism(Path(a.root), Path(a.rerun_root), a.csv, a.rerun_csv)
        det['root_a'], det['root_b'] = str(a.root), str(a.rerun_root)
        (out / 'determinism.json').write_text(json.dumps(det, indent=1, default=str), encoding='utf-8')
        print(json.dumps(det, indent=1, default=str)[:4000])
    return 0


if __name__ == '__main__':
    sys.exit(main())
