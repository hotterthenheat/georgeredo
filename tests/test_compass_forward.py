"""
Tests for the Compass features forward test (research_notes/Compass features/forward/forward_features.py and step 7 of
scripts/daily_forward.py), against FORWARD_RULE.md.

Run:  python3 -I tests/test_compass_forward.py            (plain: runs every test_* below)
      python3 -I -m pytest tests/test_compass_forward.py -q

What they prove: the frozen code is the code committed in 2a49049 / e5dd8c6 (sha256, the same table as FORWARD_RULE.md)
and the N in the code are the rule's; the forward code rebuilds the committed holdout's rows for 2026-10-19, -20 and -21
(golden_sessions.json, cut from the Phase A holdout table) from the stored layout — trade by trade and model by model —
where the layout is on this machine (PAPER_PARQUET_ROOT, or the study's own data folder), and says SKIP otherwise; the
append is idempotent and never writes a partial session or a duplicate; no verdict before N; the verdict at exactly N on
the first N sessions; missing data fails loudly and writes nothing; the official SPX close is asked once and kept only
when it holds the day; the daily job's step 7 appends a fixture session once and is not run twice for it.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FWD = REPO / 'research_notes' / 'Compass features' / 'forward'
sys.path.insert(0, str(FWD))
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'tests'))

import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

import forward_features as FF  # noqa: E402

SP = Path(os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad'))
GOLDEN = json.loads((FWD / 'golden_sessions.json').read_text())
SKIPPED = []


def skip(why: str):
    SKIPPED.append(why)
    print(f'SKIP  {why}')


def layout_with(days) -> Path | None:
    for cand in (os.environ.get('PAPER_PARQUET_ROOT'), str(SP / 'theta')):
        if cand and all((Path(cand) / f'data_full/chains/{n}/{d}.parquet').exists() for d in days for n in FF.FORWARD_NAMES):
            return Path(cand)
    return None


def test_the_frozen_code_and_N_are_the_rules():
    FF.check_frozen()
    rule = (FWD.parent / 'FORWARD_RULE.md').read_text()
    for rel, h in FF.FROZEN.items():
        assert f'`{rel}` | `{h}`' in rule, rel
    pw = json.loads((FWD / 'power_n.json').read_text())
    for m in FF.MODELS:
        assert pw['models'][m]['A_forward_composition']['N'] == FF.N_RULE[m], m
        assert f'| {m} |' in rule and f'**{FF.N_RULE[m]:,}' in rule, m


def test_a_changed_frozen_file_is_refused():
    keep = dict(FF.FROZEN)
    try:
        FF.FROZEN['run/stats.py'] = '0' * 64
        try:
            FF.check_frozen()
            raise AssertionError('a changed file was not refused')
        except RuntimeError as e:
            assert 'run/stats.py' in str(e)
    finally:
        FF.FROZEN.clear()
        FF.FROZEN.update(keep)


def test_the_frozen_definitions_rebuild_the_committed_holdout_rows():
    days = sorted(GOLDEN['sessions'])
    lay = layout_with(days)
    if lay is None:
        skip('golden sessions: no layout with 2026-10-19..21 on this machine (set PAPER_PARQUET_ROOT)')
        return
    hold = SP / 'features_work' / 'hold' / 'trades_with_inputs.parquet'
    H = pl.read_parquet(hold) if hold.exists() else None
    with tempfile.TemporaryDirectory() as d:
        for day in days:
            T = FF.build_session(day, lay, Path(d) / 'work', REPO / 'data' / 'official_closes')
            g = GOLDEN['sessions'][day]
            assert {n: T.filter(pl.col('name') == n).height for n in FF.FORWARD_NAMES} == g['trades'], day
            for r in FF.session_rows(day, T):
                e = g['models'][r['model']]
                assert r['N_with'] == e['N_with'] and r['N_without'] == e['N_without'], (day, r['model'])
                assert abs(r['S_with'] - e['S_with']) < 1e-9 and abs(r['S_without'] - e['S_without']) < 1e-9, (day, r['model'])
            if H is not None:            # trade by trade against the holdout table itself
                h = H.filter((pl.col('day') == day) & (pl.col('eb') == '0DTE') & pl.col('name').is_in(list(FF.FORWARD_NAMES)))
                key, cols = ['name', 'm', 'right', 'sb'], ['strike', 'bid', 'ask', 'spread', 'r', 'r_x3', 'd6']
                j = T.select(key + cols).join(h.select(key + cols), on=key, how='full', suffix='_h')
                assert j.height == h.height == T.height
                for c in cols:
                    same = ((j[c] - j[c + '_h']).abs() <= 1e-12) | (j[c].is_null() & j[c + '_h'].is_null())
                    assert bool(same.all()), (day, c)


def fake_rows(days, model_effect: dict, rng_seed=1, noise=0.02, n=50):
    """per session and model: n trades without at mean −0.10, the 'with' arm at −0.10 + effect (noise per session)"""
    rng = np.random.default_rng(rng_seed)
    out = []
    for d in days:
        for m in FF.MODELS:
            mo = -0.10 + rng.normal(0, noise)
            mw = mo + model_effect.get(m, 0.0) + rng.normal(0, noise)
            out.append(dict(day=d, model=m, S_with=mw * n, N_with=n, S_without=mo * n, N_without=n, mean_with=mw, mean_without=mo,
                            d_session=mw - mo, version='test', written_at='x'))
    return out


def sessions(k, start='2027-01-04'):
    d0 = dt.date.fromisoformat(start)
    return [(d0 + dt.timedelta(days=i)).isoformat() for i in range(k)]


def test_the_append_is_idempotent_and_never_partial():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'f.csv'
        rows = fake_rows(sessions(2), {})
        assert FF.append_rows(rows, p) == sessions(2)
        txt = p.read_text()
        assert FF.append_rows(rows, p) == [] and p.read_text() == txt
        assert len(FF.read_csv(p)) == 12 and FF.days_in(p) == set(sessions(2))
        part = [r for r in fake_rows(sessions(1, '2027-02-01'), {}) if r['model'] != 'BC3']
        try:
            FF.append_rows(part, p)
            raise AssertionError('a partial session was appended')
        except RuntimeError:
            pass
        assert p.read_text() == txt
        with open(p, 'a') as f:                      # a hand-made duplicate is caught on the next read
            f.write(txt.splitlines()[1] + '\n')
        try:
            FF.days_in(p)
            raise AssertionError('a duplicate went unnoticed')
        except RuntimeError as e:
            assert 'duplicated' in str(e)


def test_no_verdict_before_N():
    rows = fake_rows(sessions(80), {m: 0.10 for m in FF.MODELS}, noise=0.001)
    for m in FF.MODELS:
        e = FF.evaluate(rows, m)
        assert e['counted'] == 80 < e['N'] and e['verdict'] == 'no verdict', e
        assert e['delta'] > 0 and e['ci'] is not None            # interim figures are computed, labelled no verdict
    e = FF.evaluate(rows[:6 * 30], 'X3', n_rule=100)
    assert e['ci'] is None and e['verdict'] == 'no verdict'      # under 60 sessions: no interval at all
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / 'f.csv'
        FF.append_rows(rows, p)
        txt = FF.write_report(Path(d) / 'r.md', p)
        assert txt.count('no verdict (interim figures only)') == 6 and 'CONFIRMED' not in txt


def test_the_verdict_at_exactly_N_on_the_first_N_sessions():
    days = sessions(61)
    good = fake_rows(days[:60], {'X3': 0.05, 'VN1': -0.05, 'BC3': 0.0}, noise=0.005)
    # session 61 is a disaster for X3: it must not move the verdict reached at N = 60
    bad = fake_rows(days[60:], {'X3': -50.0})
    rows = good + bad
    e = FF.evaluate(rows, 'X3', n_rule=60)
    assert e['verdict'] == 'CONFIRMED' and e['through'] == days[59] and e['ci'][0] > 0, e
    assert FF.evaluate(rows, 'VN1', n_rule=60)['verdict'] == 'NOT CONFIRMED'
    assert FF.evaluate(rows, 'BC3', n_rule=60)['verdict'] == 'NOT CONFIRMED'
    assert FF.evaluate(rows[:6 * 59], 'X3', n_rule=60)['verdict'] == 'no verdict'
    # the interval is the 20-session block bootstrap of audit_lib with its fixed seed: the same call twice, the same numbers
    assert FF.evaluate(rows, 'X3', n_rule=60)['ci'] == e['ci']


def tiny_layout(root: Path, day: str, drop: str | None = None):
    """the stored 2026-10-09 files of the paper tracker's reference copied under `day`"""
    ref = REPO / 'data' / 'theta_reference'
    for rel in ['data_full/chains/SPY/2026-10-09.parquet', 'data_full/chains/QQQ/2026-10-09.parquet', 'data_full/chains/SPXW/2026-10-09.parquet',
                'data/underlying/SPY/2026-10-09.parquet', 'data/underlying/QQQ/2026-10-09.parquet', 'data/index/SPX/2026-10-09.parquet']:
        if drop and drop in rel:
            continue
        src = ref / rel
        if not src.exists():
            return False
        dst = root / rel.replace('2026-10-09', day)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return True


def cboe_text(days_px: dict) -> str:
    lines = ['DATE,SPX'] + [f'{d[5:7]}/{d[8:10]}/{d[:4]},{v:.6f}' for d, v in sorted(days_px.items())]
    return '\n'.join(lines) + '\n'


def test_the_official_spx_close_is_asked_once_and_kept_only_when_it_holds_the_day():
    with tempfile.TemporaryDirectory() as d:
        od = Path(d)
        calls = []

        def early(url):
            calls.append(url)
            return cboe_text({'2026-10-21': 7757.17})

        assert FF.ensure_spx_close('2026-10-22', od, early, today='2026-10-22') == (None, 1) and not list(od.glob('*.csv'))

        def late(url):
            calls.append(url)
            return cboe_text({'2026-10-21': 7757.17, '2026-10-22': 7770.01})

        assert FF.ensure_spx_close('2026-10-22', od, late, today='2026-10-22') == (7770.01, 1)
        assert [f.name for f in od.glob('*.csv')] == ['cboe_SPX_History_2026-10-22.csv']
        assert FF.ensure_spx_close('2026-10-22', od, late) == (7770.01, 0) and len(calls) == 2
        try:
            FF.parse_cboe('date,close\n1/1/2026,1\n')
            raise AssertionError('a foreign file was read as Cboe\'s')
        except ValueError:
            pass


def test_missing_data_fails_loudly_and_writes_nothing():
    day = '2026-10-23'
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        if not tiny_layout(d / 'pq', day, drop='SPXW'):
            skip('missing-data test: data/theta_reference lacks the 2026-10-09 files')
            return
        od = d / 'oc'
        od.mkdir()
        (od / 'cboe_SPX_History_2026-10-23.csv').write_text(cboe_text({day: 6700.0}))
        csvp, rep = d / 'f.csv', d / 'r.md'
        r = FF.run([day], d / 'pq', d / 'work', od, csv_path=csvp, report_path=rep)
        assert r['added'] == [] and r['failure'].startswith(f'{day} inputs:') and 'SPXW' in r['failure'] and not csvp.exists()
        # every file there, no official SPX close and nothing may be asked → official-spx-close
        shutil.rmtree(d / 'pq')
        tiny_layout(d / 'pq', day)
        (od / 'cboe_SPX_History_2026-10-23.csv').unlink()
        r = FF.run([day], d / 'pq', d / 'work', od, csv_path=csvp, report_path=rep)
        assert r['failure'].startswith(f'{day} official-spx-close') and not csvp.exists()
        assert 'no verdict' in rep.read_text()


def test_a_fixture_session_runs_through_and_is_appended_once():
    day = '2026-10-23'
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        if not tiny_layout(d / 'pq', day):
            skip('fixture session: data/theta_reference lacks the 2026-10-09 files')
            return
        od = d / 'oc'
        asked = []
        fetch = lambda url: (asked.append(url), cboe_text({day: 6750.0}))[1]  # noqa: E731
        csvp, rep = d / 'f.csv', d / 'r.md'
        r = FF.run([day, '2026-10-21'], d / 'pq', d / 'work', od, csv_path=csvp, report_path=rep, fetch_text=fetch, today=day)
        assert r['failure'] is None and r['added'] == [day] and len(asked) == 1, r      # 2026-10-21 is before the forward start
        rows = FF.read_csv(csvp)
        assert len(rows) == 6 and {x['model'] for x in rows} == set(FF.MODELS) and all(x['N_without'] > 0 for x in rows if x['model'] != 'VN1')
        mt = csvp.stat().st_mtime_ns
        r2 = FF.run([day], d / 'pq', d / 'work', od, csv_path=csvp, report_path=rep, fetch_text=fetch)
        assert r2['added'] == [] and r2['pending'] == [] and csvp.stat().st_mtime_ns == mt and len(asked) == 1
        assert '| X3 | 1 / 369 |' in rep.read_text()


def test_the_daily_job_runs_step_7_after_the_tracker_and_once():
    try:
        import test_paper_tracker as TP
    except Exception as e:  # noqa: BLE001
        skip(f'daily job wiring: the paper tracker tests do not import here ({type(e).__name__})')
        return
    import daily_forward as DF
    term = TP._FakeThetaTerminal()
    try:
        with tempfile.TemporaryDirectory() as d:
            job, log, lines, uw, closes = TP.job_pieces(d)
            job.features, job.features_csv, job.features_report = True, Path(d) / 'f.csv', Path(d) / 'r.md'
            asked = []
            fetch = lambda url: (asked.append(url), cboe_text({TP.JOB_DAY: 6750.0}))[1]  # noqa: E731
            res = DF.run_job(job, now=TP.JOB_NOW, log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes, spx_fetch=fetch)
            assert res['rc'] == 0 and res['appended'] == [TP.JOB_DAY] and res['features_added'] == [TP.JOB_DAY], (res, lines.lines[-5:])
            assert len(FF.read_csv(job.features_csv)) == 6 and len(asked) == 1
            again = DF.run_job(job, now=TP.JOB_NOW + dt.timedelta(hours=1), log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes, spx_fetch=fetch)
            assert again['rc'] == 0 and again['features_added'] == [] and len(FF.read_csv(job.features_csv)) == 6 and len(asked) == 1
    finally:
        term.close()


def test_the_daily_job_says_a_features_failure_and_keeps_the_trackers_append():
    try:
        import test_paper_tracker as TP
    except Exception as e:  # noqa: BLE001
        skip(f'daily job failure: the paper tracker tests do not import here ({type(e).__name__})')
        return
    import daily_forward as DF
    term = TP._FakeThetaTerminal()
    try:
        with tempfile.TemporaryDirectory() as d:
            job, log, lines, uw, closes = TP.job_pieces(d)
            job.features, job.features_csv, job.features_report = True, Path(d) / 'f.csv', Path(d) / 'r.md'
            res = DF.run_job(job, now=TP.JOB_NOW, log=log, theta_fetcher=term.fetcher(), uw_client=uw, closes=closes,
                             spx_fetch=lambda url: cboe_text({'2026-10-21': 1.0}))
            assert res['rc'] == 1 and res['appended'] == [TP.JOB_DAY] and res['features_added'] == []
            assert any(re.search(r'DAILY-FORWARD FAIL 2026-10-22 features-official-spx-close', l) for l in lines.lines), lines.lines[-5:]
            assert not job.features_csv.exists()
    finally:
        term.close()


if __name__ == '__main__':
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print(f'ok    {name}')
            except Exception as e:  # noqa: BLE001
                failed += 1
                import traceback
                print(f'FAIL  {name}: {type(e).__name__}: {e}')
                traceback.print_exc()
    print(('\nall passed' if not failed else f'\n{failed} failed') + (f' ({len(SKIPPED)} skipped)' if SKIPPED else ''))
    sys.exit(1 if failed else 0)
