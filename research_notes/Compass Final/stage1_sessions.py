"""stage1_sessions.py — Compass Final, stage 1: the fresh sessions of every family and what is excluded from them.

Files only (dates and timestamps of earlier studies' positions; no quote, price or P&L is read). Writes, beside this file:
  sessions_<family>.csv   every same-day-expiry session of the family's instrument(s) in its fresh span, with
                          `excluded_by` (empty = in the test), `half_day`, and the EOD-mark overlaps (sensitivity only)
  out/stage1_summary.json the counts the prereg quotes

THE RULES (PREREG_COMPASS_FINAL.md section 3):
- Fresh span: from the first session Theta serves the rule's inputs (QQQ bars, EOD and options 2012-06-01; SPY bars and
  EOD 2017-01-03; SPX 1-minute prints 2017-01-03 — stage 1 probes, out/probe_entitlement*.json) to 2022-05-12, the last
  session before 2022-05-13, from which SPXW same-day chains were read intraday on every session (steps 1-5, Tier I,
  H11/H13/H15, S09, Compass ICT ...).
- Same-day-expiry sessions: Theta's expiration lists (research/thetadata/dataset/expirations/expirations_<ROOT>.csv at
  7dfea57), a listed expiration that is a session.
- Sessions: QQQ's 1-minute bar files on disk with >= 30 closes are the NYSE sessions (2012-06-01 -> 2022-05-12); a
  half day = the last bar with a close stamped before 15:00 (the replay's rule); checked against the dataset calendar
  (calendar_2017_2026.csv) from 2017.
- Excluded as READ (the precedent of Compass Close step 0, union across the index products SPY/QQQ/IWM/SPX/SPXW): a
  session on which an earlier study held an index-product option position, or read an index-product option P&L, at
  any minute of the family's window [first entry minute, 16:00]:
    V8 (month-end 13:00 straddle to settlement): [13:00, 16:00] on its session;
    S03 (filled trades): [entry_ts, exit_ts];
    S16b (filled trades): [session 09:31, + hold_min minutes] (Compass Close's convention);
    Compass Close: its gate sample (`sample` = gate in its sessions_new.csv: the 15:45-16:00 quotes and the settlement
    read; its plain-loop and lookahead checks drew only from it): [15:45, 16:00].
- NOT counted as reads (Compass Close's decision 1, kept): end-of-day closing marks — the Lifecycle daily tier, the
  Compass features' ETF base trades before 2022-11 (entered and exited at minute 390) and S17's monthly cycles. Their
  overlaps are flagged per session for the sensitivity lines.
"""
from __future__ import annotations

import datetime as dt
import glob
import io
import json
import os
import subprocess
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SP = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
END = dt.date(2022, 5, 12)
START = {'SPY': dt.date(2017, 1, 3), 'QQQ': dt.date(2012, 6, 1), 'SPXW': dt.date(2017, 1, 3)}
FAMILIES = {      # family: (instrument roots, window start)
    'fly5': (('SPY', 'QQQ'), dt.time(15, 0)),
    'condor_em1': (('SPY',), dt.time(11, 30)),
    'condor_d20': (('SPY',), dt.time(13, 0)),
    'touch_d25': (('SPY',), dt.time(9, 35)),
    'h13_te': (('SPXW',), dt.time(13, 0)),
    'h15_s2': (('SPXW',), dt.time(14, 5)),
}
CLOSE = dt.time(16, 0)


def git_bytes(path: str, rev: str = '7dfea57') -> bytes:
    return subprocess.run(['git', '-C', str(REPO), 'show', f'{rev}:{path}'], check=True, capture_output=True).stdout


def git_frame(path: str) -> pl.DataFrame:
    b = git_bytes(path)
    return pl.read_parquet(io.BytesIO(b)) if path.endswith('.parquet') else pl.read_csv(io.BytesIO(b), infer_schema_length=0)


def calendar() -> tuple[list, set]:
    sess, half = [], set()
    for f in sorted(glob.glob(str(SP / 'theta' / 'data' / 'underlying' / 'QQQ' / '*.parquet'))):
        d = dt.date.fromisoformat(os.path.basename(f)[:10])
        if not (dt.date(2012, 6, 1) <= d <= END):
            continue
        b = pl.read_parquet(f, columns=['timestamp', 'close']).filter(pl.col('close').is_not_null() & pl.col('close').is_not_nan())
        if b.height < 30:
            continue
        sess.append(d)
        last = b['timestamp'].max()
        if last.hour * 60 + last.minute < 15 * 60:
            half.add(d)
    return sess, half


def expirations(root: str) -> set:
    e = git_frame(f'research/thetadata/dataset/expirations/expirations_{root}.csv')
    return {dt.date.fromisoformat(x) for x in e['expiration'].to_list()}


def reads() -> dict:
    """study -> list of (start datetime, end datetime) intervals of index-product option positions / reads"""
    out = {'V8': [], 'S03': [], 'S16b': [], 'CompassClose': []}
    v = git_frame('research/compass/results/v1/v8_monthend/trades.parquet')
    for s in v['session'].to_list():
        out['V8'].append((dt.datetime.combine(s, dt.time(13, 0)), dt.datetime.combine(s, CLOSE)))
    s3 = git_frame('research/compass/results/v1/s03_weekly_index_etfs_baseline/trades.parquet').filter(pl.col('status') == 'filled')
    for e, x in zip(s3['entry_ts'].to_list(), s3['exit_ts'].to_list()):
        out['S03'].append((e, x))
    b = git_frame('research/compass/results/v1/s16b_prior_day_fade_weekly/trades.parquet').filter(pl.col('status') == 'filled')
    for s, h in zip(b['session'].to_list(), b['hold_min'].to_list()):
        t0 = dt.datetime.combine(s, dt.time(9, 31))
        out['S16b'].append((t0, t0 + dt.timedelta(minutes=h)))
    cc = REPO / 'research_notes' / 'Compass Close'
    new = pl.read_csv(cc / 'sessions_new.csv', infer_schema_length=0)
    days = {dt.date.fromisoformat(x) for x, smp in zip(new['session'].to_list(), new['sample'].to_list()) if smp == 'gate'}
    # its plain-loop check drew 50 gate-sample sessions (+ 10 previously read, after 2022-05-12); its lookahead check 10
    # gate-sample sessions: both inside the gate sample, asserted here
    la = {dt.date.fromisoformat(r['day']) for r in json.loads((cc / 'out' / 'lookahead.json').read_text())['rows']}
    assert la <= days, 'a lookahead session outside the gate sample'
    for d in sorted(days):
        out['CompassClose'].append((dt.datetime.combine(d, dt.time(15, 45)), dt.datetime.combine(d, CLOSE)))
    return out


def hits(intervals: list, d: dt.date, t0: dt.time) -> bool:
    a, b = dt.datetime.combine(d, t0), dt.datetime.combine(d, CLOSE)
    return any(x <= b and y >= a for x, y in intervals if x.date() <= d <= y.date())


def eod_marks() -> dict:
    """session -> the EOD-mark studies with a position entered, held or expiring that session (sensitivity only)"""
    out: dict = {}

    def add(d, who):
        out.setdefault(d, set()).add(who)
    for p in ('expl', 'hold'):
        f = SP / 'features_work' / p / 'trades_with_inputs.parquet'
        if f.exists():
            t = pl.read_parquet(f, columns=['name', 'day', 'exit_day']).filter(pl.col('name').is_in(['SPY', 'QQQ', 'IWM']))
            t = t.with_columns(pl.col('day').cast(pl.Utf8).str.slice(0, 10), pl.col('exit_day').cast(pl.Utf8).str.slice(0, 10))
            for a, x in zip(t['day'].to_list(), t['exit_day'].to_list()):
                a = dt.date.fromisoformat(a) if a else None
                x = dt.date.fromisoformat(x) if x else None
                if a is None or a > END:
                    continue
                add(a, 'features_eod')
                if x is not None:
                    add(x, 'features_eod')
    for f in [g for run in ('dgrid', 'dbest', 'dholdout') for g in glob.glob(str(SP / 'lifecycle' / 'runs' / run / '*' / 'positions.parquet'))]:
        if Path(f).parent.name not in ('SPY', 'QQQ', 'IWM'):
            continue
        t = pl.read_parquet(f)
        cols = t.columns
        if 'skip' in cols:
            t = t.filter(pl.col('skip').is_null() | (pl.col('skip').cast(pl.Utf8) == ''))
        for c in [c for c in ('entry_date', 'date', 'session', 'expiration', 'exit_date') if c in cols]:
            for v in t[c].cast(pl.Utf8).to_list():
                if v:
                    try:
                        add(dt.date.fromisoformat(v[:10]), 'lifecycle_daily')
                    except ValueError:
                        pass
    s17 = git_frame('research/compass/results/v1/s17_put_write/cycles.parquet')
    for c in [c for c in s17.columns if c in ('entry', 'entry_date', 'expiry', 'expiration', 'exit', 'roll')]:
        for v in s17[c].cast(pl.Utf8).to_list():
            if v:
                try:
                    add(dt.date.fromisoformat(v[:10]), 's17_eod')
                except ValueError:
                    pass
    return out


def main() -> None:
    sess, half = calendar()
    S = set(sess)
    cal = git_frame('research/thetadata/dataset/calendar_2017_2026.csv')
    cal_half = {dt.date.fromisoformat(d) for d, t in zip(cal['date'].to_list(), cal['type'].to_list()) if t == 'early_close'}
    cal_full = {dt.date.fromisoformat(d) for d, t in zip(cal['date'].to_list(), cal['type'].to_list()) if t == 'full_close'}
    check = {'half_days_from_bars_2017+': sorted(str(d) for d in half if d.year >= 2017),
             'half_days_calendar_2017+': sorted(str(d) for d in cal_half if dt.date(2017, 1, 3) <= d <= END),
             'calendar_holidays_with_a_bar_file': sorted(str(d) for d in cal_full if d in S)}
    exps = {r: expirations(r) for r in ('SPY', 'QQQ', 'SPXW')}
    R = reads()
    E = eod_marks()
    summary = {'calendar_check': check, 'half_days_2012_2016': sorted(str(d) for d in half if d.year < 2017), 'families': {}}
    for fam, (roots, t0) in FAMILIES.items():
        rows = []
        for root in roots:
            for d in sess:
                if d < START[root] or d not in exps[root]:
                    continue
                by = [k for k, iv in R.items() if hits(iv, d, t0)]
                rows.append(dict(session=str(d), root=root, weekday=d.strftime('%a'), year=d.year, half_day=d in half,
                                 excluded_by='+'.join((['half_day'] if d in half else []) + by),
                                 eod_marks='+'.join(sorted(E.get(d, ()))),
                                 compass_close_pnl_sample=False))
        df = pl.DataFrame(rows).sort(['session', 'root'])
        # Compass Close's P&L sample (even months of its sessions_new.csv): fetched 15:45-16:00, never read for an outcome
        cc = pl.read_csv(REPO / 'research_notes' / 'Compass Close' / 'sessions_new.csv', infer_schema_length=0)
        even = {x for x, smp in zip(cc['session'].to_list(), cc['sample'].to_list()) if smp != 'gate'}
        df = df.with_columns(pl.col('session').is_in(sorted(even)).alias('compass_close_pnl_sample'))
        df.write_csv(HERE / f'sessions_{fam}.csv')
        keep = df.filter(pl.col('excluded_by') == '')
        summary['families'][fam] = {
            'roots': list(roots), 'window': f'{t0.strftime("%H:%M")}-16:00',
            'listed_sessions': {r: df.filter(pl.col('root') == r).height for r in roots},
            'half_days': {r: df.filter((pl.col('root') == r) & pl.col('half_day')).height for r in roots},
            'excluded_read': {k: df.filter(pl.col('excluded_by').str.contains(k)).height for k in R},
            'excluded_any': df.filter(pl.col('excluded_by') != '').height,
            'in_test': {r: keep.filter(pl.col('root') == r).height for r in roots},
            'in_test_by_year': {f'{r} {y}': keep.filter((pl.col('root') == r) & (pl.col('year') == y)).height
                                for r in roots for y in sorted(set(keep['year'].to_list()))},
            'in_test_by_weekday': {f'{r} {w}': keep.filter((pl.col('root') == r) & (pl.col('weekday') == w)).height
                                   for r in roots for w in ('Mon', 'Tue', 'Wed', 'Thu', 'Fri')},
            'in_test_with_eod_marks': keep.filter(pl.col('eod_marks') != '').height,
            'in_test_compass_close_pnl_sample': keep.filter(pl.col('compass_close_pnl_sample')).height,
            'first': keep['session'].min(), 'last': keep['session'].max(),
        }
    (HERE / 'out').mkdir(exist_ok=True)
    (HERE / 'out' / 'stage1_summary.json').write_text(json.dumps(summary, indent=1, default=str))
    print(json.dumps(summary, indent=1, default=str))


if __name__ == '__main__':
    main()
