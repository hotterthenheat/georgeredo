"""run_t123.py — Compass Final T1 (fly5 iron), T2 (condor_em1), T3 (condor_d20): run ONCE (PREREG_COMPASS_FINAL.md 5, 6).

    POLARS_MAX_THREADS=2 python3 -I run_t123.py replay     # the frozen tracker over the fresh sessions (rows only)
    POLARS_MAX_THREADS=2 python3 -I run_t123.py settle     # the trades, the settlement cases, the fees -> out/t123_trades.parquet

THE REPLAY is scripts/paper_tracker.py's own (`paper_backtest.replay`), on $SP/compass_final (the fetched same-day chains;
the stored SPY/QQQ bars and VIX prints through symlinks). The ONE substitution: the replay's calendar, which reads SPY's
files (empty before 2017), is given the NYSE sessions of stage1 (QQQ's stored files with >= 30 closes) through
ParquetSource.days / is_session / is_half; nothing in paper_tracker is touched. Official closes: paper_audit.OfficialCloses
over Theta's EOD stores only (H1's 2012-2018 file, the 2019 lake, data_lake 2020-), no UW (none exists before 2022).

THE SETTLEMENT (section 4): each tradable trade's legs (audit_lib.legs_of on the capture row) through AFTERHOURS.md's own
`case_pnl` (backtest_audit/afterhours.py, imported, fee_ex 0): C = the official close, D = the close of the last
post-market bar ending at or before 17:30 (a bar stamped t ends at t + 1: stamps 16:00..17:29), O = the next session's
09:30 bar open. Fees: case_pnl subtracts the tracker's $2.60; gross = that + 2.60; Robinhood = gross - the opening legs'
fees (shorts sold at the bid, longs bought at the ask) - the stock fees on the shares a case leaves, closed at O.
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
sys.path.insert(0, str(HERE))
import lib_final as LF  # noqa: E402

SP = LF.SP
ROOT = Path(os.environ.get('CF_ROOT', str(LF.ROOT)))            # CF_ROOT/CF_START/CF_END: the dry run on previously read days only
REPLAY = ROOT / 'replay_official'
OUTNAME = os.environ.get('CF_OUT', 't123_trades.parquet')
KEYS = ('fly5', 'condor_em1', 'condor_d20')
START, END = os.environ.get('CF_START', '2012-06-01'), os.environ.get('CF_END', '2022-05-12')


def calendar() -> tuple[list[str], set]:
    import stage1_sessions as S1
    if os.environ.get('CF_END'):                     # the dry run: the same rule, past 2022-05-12
        S1.END = dt.date.fromisoformat(os.environ['CF_END']) + dt.timedelta(days=10)
    sess, half = S1.calendar()
    return [d.isoformat() for d in sess], {d.isoformat() for d in half}


def assemble() -> None:
    """the fresh root: fetched chains are already there; the stored bars and VIX by symlink; Theta's EOD stores in one folder"""
    for sym in ('SPY', 'QQQ'):
        p = ROOT / 'data' / 'underlying' / sym
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.symlink_to(SP / 'theta' / 'data' / 'underlying' / sym)
    v = ROOT / 'data' / 'index' / 'VIX'
    if not v.exists():
        v.parent.mkdir(parents=True, exist_ok=True)
        v.symlink_to(SP / 'theta' / 'data' / 'index' / 'VIX')
    e = ROOT / 'eod'
    e.mkdir(exist_ok=True)
    srcs = ([REPO / 'research_notes' / 'Compass H1' / 'data' / 'stock_eod_2012_2018.parquet']
            + sorted(Path(x) for x in glob.glob(str(SP / 'lake' / 'stock_eod' / 'year=2019' / '*.parquet')))
            + sorted(Path(x) for x in glob.glob(str(REPO / 'data_lake' / 'thetadata' / 'stock_eod' / 'year=*' / '*.parquet'))))
    for i, s in enumerate(srcs):
        link = e / f'{i:04d}_{s.parent.name}_{s.name}'
        if not link.exists():
            link.symlink_to(s)


def closes():
    import paper_audit as P
    return P.OfficialCloses(names=('SPY', 'QQQ'), uw_dirs=(), uw_lake_glob=None, theta_glob=str(ROOT / 'eod' / '*.parquet'), live_root=None)


def replay() -> None:
    import paper_backtest as B
    assemble()
    cal, half = calendar()
    calset = set(cal)

    class Src(B.ParquetSource):
        def days(self, sym: str = 'SPY') -> list[str]:
            return cal

        def is_session(self, day: str) -> bool:
            return day in calset

        def is_half(self, day: str) -> bool:
            return day in half
    B.ParquetSource = Src                         # the replay builds its ParquetSource by this name
    res = B.replay(START, END, KEYS, ROOT, REPLAY, live_root=None, settle_on='official', closes=closes())
    days = json.loads(B.days_file(REPLAY, START, END).read_text()) if B.days_file(REPLAY, START, END).exists() else {}
    days = days.get('days', days) if isinstance(days, dict) else {}
    n = {}
    for v in days.values():
        st = v.get('status') if isinstance(v, dict) else str(v)
        n[st] = n.get(st, 0) + 1
    print(res, n)
    if not os.environ.get('CF_END'):
        (HERE / 'out').mkdir(exist_ok=True)
        (HERE / 'out' / 't123_replay_days.json').write_text(json.dumps({'replay': res, 'status_counts': n}, indent=1))


# ---- the settlement cases --------------------------------------------------------------------------------------------------------------

def decision_price(sym: str, day: str):
    """the close of the last post-market bar ENDING at or before 17:30 (stamps 16:00..17:29); None if none"""
    f = ROOT / 'data' / 'afterhours' / sym / f'{day}.parquet'
    if not f.exists():
        return None, 'no after-hours file'
    b = pl.read_parquet(f).filter(pl.col('close').is_not_null())
    hm = b['timestamp'].dt.strftime('%H:%M')
    b = b.filter((hm >= '16:00') & (hm <= '17:29')).sort('timestamp')
    if b.height == 0:
        return None, 'no post-market bar with a trade 16:00-17:30'
    return float(b['close'][-1]), b['timestamp'][-1].strftime('%H:%M')


def open_0930(sym: str, day: str):
    f = SP / 'theta' / 'data' / 'underlying' / sym / f'{day}.parquet'
    if not f.exists():
        return None
    b = pl.read_parquet(f).filter(pl.col('timestamp').dt.strftime('%H:%M') == '09:30')
    if b.height == 0 or b['open'][0] is None:
        return None
    v = float(b['open'][0])
    return v if v == v else None


def rh_open(name: str, legs: list, cap: dict) -> float:
    import fees_robinhood as FR
    f = 0.0
    for i in range(1, 5):
        if not cap.get(f'l{i}_symbol'):
            continue
        q = float(cap[f'l{i}_qty'])
        if cap[f'l{i}_side'] == 'short':
            f += FR.option_fee(name, float(cap[f'l{i}_bid']), q, 'sell')
        else:
            f += FR.option_fee(name, float(cap[f'l{i}_ask']), q, 'buy')
    return f


def stock_rh(shares: float, px) -> float:
    import fees_robinhood as FR
    if not shares or px is None:
        return 0.0
    return FR.stock_fee(px, abs(shares), 'sell' if shares > 0 else 'buy')


def settle() -> None:
    import audit_lib as AL
    import afterhours as AH
    import fees_robinhood as FR
    cal, _ = calendar()
    nxt = {cal[i]: cal[i + 1] for i in range(len(cal) - 1)}
    df = AL.load_rows(REPLAY, keys=KEYS)
    caps = df.filter((pl.col('row_kind') == 'capture') & (pl.col('tradable') == 'true'))
    on = ['candidate', '_name', '_day', 'minute', 'structure']
    sett = df.filter(pl.col('row_kind') == 'settle').select(on + ['settle_source', 'close_official_f', 'pnl_nbbo_f', 'pnl_1558_nbbo_f',
                                                                  'legs_closed_f', 'fees_close_f', 'close_1m_r_f'])
    c58 = df.filter(pl.col('row_kind') == 'close1558')
    keep58 = [c for c in c58.columns if c.endswith('_1558') and c[:2] in ('l1', 'l2', 'l3', 'l4')]
    c58 = c58.select(on + keep58).unique(subset=on, keep='first') if c58.height else None
    caps = caps.drop([c for c in sett.columns if c not in on and c in caps.columns])     # capture rows carry these columns empty
    t = caps.join(sett, on=on, how='left')
    if c58 is not None:
        t = t.drop([c for c in c58.columns if c not in on and c in t.columns]).join(c58, on=on, how='left')
    D, O = {}, {}
    rows = []
    for r in t.iter_rows(named=True):
        nm, day = r['_name'], r['_day']
        if (nm, day) not in D:
            D[(nm, day)] = decision_price(nm, day)
            n = nxt.get(day)
            O[(nm, day)] = (open_0930(nm, n) if n else None, n)
        legs = AL.legs_of(r)
        entry = float(r['price_nbbo']) if r['package'] == 'credit' else -float(r['price_nbbo'])
        C = r['close_official_f']
        d, dbar = D[(nm, day)]
        o, nday = O[(nm, day)]
        out = {'candidate': r['candidate'], 'structure': r['structure'], 'name': nm, 'date': day, 'entry': r['minute'],
               'inst': f"{nm} {r['structure']}", 'legs': json.dumps(legs), 'package': r['package'], 'price_nbbo': float(r['price_nbbo']),
               'max_risk': float(r['max_risk']), 'cost': float(r['max_risk']) * 100, 'official': C, 'settle_source': r['settle_source'],
               'close_1559': r['close_1m_r_f'], 'decision_px': d, 'decision_bar': dbar, 'next_session': nday, 'next_open_0930': o,
               'pnl_replay_official_old': r['pnl_nbbo_f']}
        rh = rh_open(nm, legs, r)
        out['fee_open_rh'] = rh
        for cs in ('0', 'a', 'b', 'c'):
            res = AH.case_pnl(legs, entry, C, d, o, cs, 0.0) if C is not None else None
            if res is None:
                out[f'gross_{cs}'] = out[f'pnl_{cs}'] = out[f'pnl_{cs}_old'] = out[f'shares_{cs}'] = None
                continue
            g = res[0] + AL.CONTRACTS * AL.FEE
            out[f'gross_{cs}'] = g
            out[f'shares_{cs}'] = res[2]
            out[f'pnl_{cs}'] = g - rh - stock_rh(res[2], o)
            out[f'pnl_{cs}_old'] = g - AL.CONTRACTS * AL.FEE
        # the tracker's own 15:58 exit (study fees: $0.65 x 4 at the open, $0.65 a contract closed) and at Robinhood's
        p58 = r.get('pnl_1558_nbbo_f')
        if p58 is not None and r.get('fees_close_f') is not None:
            close_rh = 0.0
            for i in range(1, 5):
                if not r.get(f'l{i}_symbol'):
                    continue
                q = float(r[f'l{i}_qty'])
                b, a = r.get(f'l{i}_bid_1558'), r.get(f'l{i}_ask_1558')
                if r[f'l{i}_side'] == 'long':
                    if b is not None and float(b) > 0:
                        close_rh += FR.option_fee(nm, float(b), q, 'sell')
                elif a is not None:
                    close_rh += FR.option_fee(nm, float(a), q, 'buy')
            out['pnl_1558_old'] = p58
            out['pnl_1558'] = p58 + AL.CONTRACTS * AL.FEE + r['fees_close_f'] - rh - close_rh
        else:
            out['pnl_1558_old'] = out['pnl_1558'] = None
        rows.append(out)
    T = pl.DataFrame(rows, infer_schema_length=None)
    T.write_parquet(HERE / 'out' / OUTNAME if OUTNAME.startswith('t123') else Path(OUTNAME))
    print(T.group_by('candidate', 'structure').agg(pl.len()).sort('candidate'))
    print('no D', T.filter(pl.col('decision_px').is_null()).select('name', 'date').unique().height, 'no O',
          T.filter(pl.col('next_open_0930').is_null()).select('name', 'date').unique().height, 'no C',
          T.filter(pl.col('official').is_null()).select('name', 'date').unique().height)


if __name__ == '__main__':
    {'replay': replay, 'settle': settle}[sys.argv[1]]()
