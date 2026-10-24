"""lookahead.py — Compass Final integrity, part 2 (PREREG section 11): on 10 sessions (seed 20261024) every input stamped after
an entry minute is blanked and the entry is rebuilt by the run's own code; nothing may change. Control: the chain read one
minute later; the entries should change. Settlement inputs (C, D, O, the Cboe close) are kept: they are read after the
close by design.

  T1-T3: the replay (paper_backtest.replay, the same calendar substitution as run_t123.py) on one session at a time, with
         that session's chain rows and bars stamped after the minute removed in memory (ParquetSource.chain / bars), one
         run per entry minute; the capture rows at that minute (tradable, the four leg symbols, the NBBO price, max risk)
         against the test's own run.
  T4:    for each touch-pick trade of the session, the session's bars and chain rows after the touch minute are replaced
         by those AT the touch minute (frozen: the engines refuse a session with fewer than 300 minutes, so the future is
         overwritten, not deleted); the audit's session() and hyp B's Session rebuild the touch and the spread.
  T5-T6: sim.Session with the chain rows after the entry minute and the SPX prints after it removed; the strikes and the
         credit against the run.

    POLARS_MAX_THREADS=2 python3 -I lookahead.py     -> out/lookahead.json
"""
from __future__ import annotations

import csv
import importlib.util
import json
import os
import random
import shutil
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import lib_final as LF  # noqa: E402
import run_t123 as R123  # noqa: E402

ROOT = LF.ROOT
WORK = Path('/tmp/claude-0/-home-user/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/cf_work/lookahead')
MIN = {'fly5': ('15:00', '15:30'), 'condor_em1': ('11:30', '12:00', '12:30', '13:00', '13:30'),
       'condor_d20': ('13:00', '13:30', '14:00', '14:30', '15:00')}


def j_of(h: str) -> int:
    return int(h[:2]) * 60 + int(h[3:]) - 570


def capture_key(df: pl.DataFrame, cand: str, nm: str, h: str) -> list:
    c = df.filter((pl.col('row_kind') == 'capture') & (pl.col('candidate') == cand) & (pl.col('_name') == nm) & (pl.col('minute') == h))
    return sorted((r['structure'], r['tradable'], r['l1_symbol'], r['l2_symbol'], r['l3_symbol'], r['l4_symbol'], r['price_nbbo'], r['max_risk'])
                  for r in c.iter_rows(named=True))


def replay_one(day: str, cand: str, h: str, mode: str) -> pl.DataFrame:
    """mode 'blank': the day's chain rows and bars after h removed; 'shift': the chain row stamped m+1 served at m"""
    import paper_backtest as B
    import paper_audit as P
    cal, half = R123.calendar()
    calset = set(cal)
    m = j_of(h)
    Base = B.ParquetSource

    class Src(Base):
        def days(self, sym='SPY'):
            return cal

        def is_session(self, d):
            return d in calset

        def is_half(self, d):
            return d in half

        def chain(self, root_sym, d):
            c = Base.chain(self, root_sym, d)
            if c is None or d != day:
                return c
            if mode == 'blank':
                return c.filter(pl.col('j') <= m)
            return c.with_columns((pl.col('j') - 1).alias('j'))

        def bars(self, sym, d):
            b = Base.bars(self, sym, d)
            if b is None or d != day or mode != 'blank':
                return b
            keep = [i for i, j in enumerate(b['j']) if j <= m]
            return {k: [v[i] for i in keep] for k, v in b.items()}
    out = WORK / f'replay_{mode}_{cand}_{day}_{h.replace(":", "")}'
    if out.exists():
        shutil.rmtree(out)
    B.ParquetSource = Src
    try:
        B.replay(day, day, (cand,), ROOT, out, live_root=None, settle_on='official', closes=R123.closes(), progress=None)
    finally:
        B.ParquetSource = Base
    import audit_lib as AL
    return AL.load_rows(out, keys=(cand,))


def t123(rng: random.Random) -> list:
    import audit_lib as AL
    base = AL.load_rows(R123.REPLAY, keys=tuple(MIN))
    spy = sorted({r['session'] for r in csv.DictReader(open(HERE / 'sessions_condor_em1.csv')) if r['excluded_by'] == ''})
    days = sorted(rng.sample(spy, 10))
    res = []
    for day in days:
        for cand, mins in MIN.items():
            for nm in (('SPY', 'QQQ') if cand == 'fly5' else ('SPY',)):
                for h in mins:
                    b = capture_key(base.filter(pl.col('_day') == day), cand, nm, h)
                    if not b:
                        continue
                    bl = capture_key(replay_one(day, cand, h, 'blank'), cand, nm, h)
                    sh = capture_key(replay_one(day, cand, h, 'shift'), cand, nm, h)
                    res.append({'test': cand, 'name': nm, 'day': day, 'minute': h, 'unchanged_when_blanked': bl == b, 'control_changed': sh != b})
    return res


def t4(rng: random.Random) -> list:
    os.environ['RAW'] = str(WORK / 't4root')
    ME = _load('maf_la', REPO / 'research_notes/Compass engine audit/move_atr_flow/engine.py')
    HB = _load('hb_la', REPO / 'research_notes/Compass phase 2/hyp_b_boundary_theta/engine.py')
    T = pl.read_parquet(HERE / 'out' / 't4_trades.parquet')
    days = sorted(rng.sample(sorted(set(T['date'].to_list())), 10))
    res = []
    import datetime as dt
    for day in days:
        for r in T.filter(pl.col('date') == day).iter_rows(named=True):
            t = j_of(r['entry'])
            for mode in ('blank', 'shift'):
                root = WORK / 't4root'
                if root.exists():
                    shutil.rmtree(root)
                (root / 'data' / 'underlying' / 'SPY').mkdir(parents=True)
                (root / 'data_full' / 'chains' / 'SPY').mkdir(parents=True)
                b = pl.read_parquet(LF.SP / 'theta' / 'data' / 'underlying' / 'SPY' / f'{day}.parquet')
                c = pl.read_parquet(ROOT / 'data_full' / 'chains' / 'SPY' / f'{day}.parquet')
                bj = b['timestamp'].dt.hour() * 60 + b['timestamp'].dt.minute() - 570
                cj = c['timestamp'].dt.hour() * 60 + c['timestamp'].dt.minute() - 570
                if mode == 'blank':
                    # freeze: every bar after the bar stamped t-1 (spot at t) repeats it; every chain row after t repeats t's
                    last = b.filter(bj == t - 1)
                    keepb = b.filter(bj <= t - 1)
                    fill = [last.with_columns(pl.col('timestamp') + pl.duration(minutes=k)) for k in range(1, int(bj.max()) - (t - 1) + 1)]
                    b2 = pl.concat([keepb] + fill)
                    ct = c.filter(cj == t)
                    c2 = pl.concat([c.filter(cj <= t)] + [ct.with_columns(pl.col('timestamp') + pl.duration(minutes=k)) for k in range(1, 391 - t)])
                else:
                    b2 = b
                    c2 = c.with_columns(pl.col('timestamp') - pl.duration(minutes=1))
                b2.write_parquet(root / 'data' / 'underlying' / 'SPY' / f'{day}.parquet')
                c2.write_parquet(root / 'data_full' / 'chains' / 'SPY' / f'{day}.parquet')
                out = ME.session('SPY', dt.date.fromisoformat(day))
                touches = out[1]
                ss = HB.Session('SPY', dt.date.fromisoformat(day))
                side = 'up' if r['structure'] == 'call' else 'down'
                tt = touches.filter((pl.col('m_scan') == r['m_scan']) & (pl.col('side') == side) & ((pl.col('mult') - 1.0).abs() < 1e-9)) if touches is not None else None
                got = None
                if tt is not None and tt.height and int(tt['t'][0]) == t and t in ss.px:
                    S = ss.px[t]
                    ks = ss.nearest_delta(t, S, r['structure'], 0.25)
                    v = HB.vertical(ss, r['structure'], ks, 2.0, t, S, {}) if ks is not None else None
                    got = (ks, round(v[0]['credit'], 6)) if v else (ks, None)
                want = (json.loads(r['legs'])[0][1], round(r['credit'], 6))
                if mode == 'blank':
                    rec = {'test': 'touch_d25', 'day': day, 'minute': r['entry'], 'unchanged_when_blanked': got == want}
                else:
                    rec['control_changed'] = got != want
                    res.append(rec)
    return res


def t56(rng: random.Random) -> list:
    import run_t56 as M
    os.environ['HWR_CHAIN_ROOT'] = str(ROOT / 'data_full' / 'chains')
    os.environ['THETA_DS_ROOT'] = str(ROOT / 'ds')
    os.environ['HWR_BAND_FALLBACK'] = '0'
    sys.path.insert(0, str(M.CODE / 'research' / 'thetadata' / 'dataset'))
    sim = _load('sim_la', M.CODE / 'research/thetadata/hwr_grid/spxw_v2/sim.py')
    sim.CBOE = M.cboe()
    T = pl.read_parquet(HERE / 'out' / 't56_trades.parquet')
    res = []
    for test, h, k in (('h13_te', '13:00', 0.0), ('h15_s2', '14:05', 0.5)):
        x = T.filter(pl.col('test') == test)
        for day in sorted(rng.sample(sorted(x['date'].to_list()), 5)):
            r = x.filter(pl.col('date') == day).row(0, named=True)
            full_chain, full_index = sim.chain_full, sim.L.index
            out = {}
            for mode in ('blank', 'shift'):
                ti = sim.hm2i(h)
                if mode == 'blank':
                    sim.chain_full = lambda d, f=full_chain: f(d).filter(pl.col('timestamp').dt.strftime('%H:%M') <= h)
                    sim.L.index = lambda s, d, f=full_index: f(s, d).filter(pl.col('timestamp').dt.strftime('%H:%M') <= h)
                else:
                    sim.chain_full = lambda d, f=full_chain: f(d).with_columns(pl.col('timestamp') - pl.duration(minutes=1))
                    sim.L.index = full_index
                try:
                    sess = sim.Session(day)
                    reason, info, rows = sim.simulate(sess, ti, 0, k)
                    got = None if reason else (float(rows[0]['kc']), float(rows[0]['kp']), float(rows[0]['credit']))
                finally:
                    sim.chain_full, sim.L.index = full_chain, full_index
                out[mode] = got
            want = (r['kc'], r['kp'], r['credit'])
            res.append({'test': test, 'day': day, 'minute': h, 'unchanged_when_blanked': out['blank'] == want, 'control_changed': out['shift'] != want})
    return res


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    rng = random.Random(20261024)
    rows = t123(rng) + t4(rng) + t56(rng)
    summ = {}
    for r in rows:
        s = summ.setdefault(r['test'], {'entries': 0, 'unchanged_when_blanked': 0, 'control_changed': 0, 'sessions': set()})
        s['entries'] += 1
        s['unchanged_when_blanked'] += int(r['unchanged_when_blanked'])
        s['control_changed'] += int(r['control_changed'])
        s['sessions'].add(r['day'])
    for s in summ.values():
        s['sessions'] = len(s['sessions'])
    (HERE / 'out' / 'lookahead.json').write_text(json.dumps({'summary': summ, 'rows': rows}, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
