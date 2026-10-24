"""run_t56.py — Compass Final T5 (T-E, H13: 13:00 SPXW ATM straddle to settlement, ex FOMC/CPI/NFP) and T6 (H15 round-2 S2:
14:05 SPXW strangle at +-0.5 EM, held, ex FOMC and month-end), run ONCE (PREREG_COMPASS_FINAL.md 5, 6).

    POLARS_MAX_THREADS=2 python3 -I run_t56.py

The simulator is research/thetadata/hwr_grid/spxw_v2/sim.py and its loader research/thetadata/dataset/load.py AS AT 7dfea57,
written out of git into $SP/compass_final/code_7dfea57/ (with the files they open at import: calendar_2017_2026.csv,
random_minutes.csv, vol_filters/events.csv, settlement_audit/settlement_reconciliation.csv) and imported unchanged; their
sha256 go to out/t56_code_sha256.json. Three inputs are pointed (section 5): HWR_CHAIN_ROOT = the fetched chains (the rows
stamped 13:00, 13:01, 14:05, 14:06; HWR_BAND_FALLBACK=0), THETA_DS_ROOT = a folder whose index/SPX holds the stored prints and
the fetched 2017-01 -> 05 ones, and sim.CBOE = the whole Cboe SPX file (the reconciliation CSV starts 2022). The cells read:
simulate(sess, 13:00, winged 0, k 0.0) and simulate(sess, 14:05, winged 0, k 0.5), the row tp 0, stop 0, exit E2.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'scripts'))
import lib_final as LF  # noqa: E402

ROOT = LF.ROOT
CODE = ROOT / 'code_7dfea57'
FILES = ['research/thetadata/hwr_grid/spxw_v2/sim.py', 'research/thetadata/hwr_grid/spxw_v2/random_minutes.csv',
         'research/thetadata/dataset/load.py', 'research/thetadata/dataset/calendar_2017_2026.csv',
         'research/thetadata/vol_filters/events.csv', 'research/thetadata/settlement_audit/settlement_reconciliation.csv']
FOMC_2017_JAN_MAY = ['2017-02-01', '2017-03-15', '2017-05-03']
CPI_2017_JAN_MAY = ['2017-01-18', '2017-02-15', '2017-03-15', '2017-04-14', '2017-05-12']
NFP_2017_JAN_MAY = ['2017-01-06', '2017-02-03', '2017-03-10', '2017-04-07', '2017-05-05']


def materialise() -> dict:
    sha = {}
    for f in FILES:
        b = subprocess.run(['git', '-C', str(REPO), 'show', f'7dfea57:{f}'], check=True, capture_output=True).stdout
        p = CODE / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b)
        sha[f] = hashlib.sha256(b).hexdigest()
    ds = ROOT / 'ds' / 'index' / 'SPX'
    ds.mkdir(parents=True, exist_ok=True)
    for src in (LF.SP / 'theta' / 'data' / 'index' / 'SPX', ROOT / 'data' / 'index' / 'SPX'):
        for x in src.glob('*.parquet'):
            if not (ds / x.name).exists():
                (ds / x.name).symlink_to(x)
    return sha


def cboe() -> dict:
    out = {}
    for r in csv.DictReader(open(REPO / 'data' / 'official_closes' / 'cboe_SPX_History_2026-10-23.csv')):
        m, d, y = r['DATE'].split('/')
        out[f'{y}-{m}-{d}'] = float(r['SPX'])
    return out


def main() -> None:
    sha = materialise()
    os.environ['HWR_CHAIN_ROOT'] = str(ROOT / 'data_full' / 'chains')
    os.environ['THETA_DS_ROOT'] = str(ROOT / 'ds')
    os.environ['HWR_BAND_FALLBACK'] = '0'
    sys.path.insert(0, str(CODE / 'research' / 'thetadata' / 'dataset'))
    spec = importlib.util.spec_from_file_location('sim_7dfea57', CODE / 'research/thetadata/hwr_grid/spxw_v2/sim.py')
    sim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sim)
    sim.CBOE = cboe()
    import fees_robinhood as FR
    ev = list(csv.DictReader(open(CODE / 'research/thetadata/vol_filters/events.csv')))
    E = {e: {r['date'] for r in ev if r['event'] == e} for e in ('FOMC', 'CPI', 'NFP')}
    E['FOMC'] |= set(FOMC_2017_JAN_MAY); E['CPI'] |= set(CPI_2017_JAN_MAY); E['NFP'] |= set(NFP_2017_JAN_MAY)
    cal = list(csv.DictReader(open(CODE / 'research/thetadata/dataset/calendar_2017_2026.csv')))
    closed = {r['date'] for r in cal if r['type'] == 'full_close'}
    d0 = dt.date(2017, 1, 2)
    allsess = [x for x in ((d0 + dt.timedelta(i)).isoformat() for i in range(3650)) if dt.date.fromisoformat(x).weekday() < 5 and x not in closed and x <= '2026-12-31']
    month_end = {max(d for d in allsess if d[:7] == m) for m in {d[:7] for d in allsess}}
    days = {fam: [r['session'] for r in csv.DictReader(open(HERE / f'sessions_{fam}.csv')) if r['excluded_by'] == '' and r['root'] == 'SPXW']
            for fam in ('h13_te', 'h15_s2')}
    cells = {'h13_te': ('13:00', 0.0, lambda d: d in E['FOMC'] or d in E['CPI'] or d in E['NFP']),
             'h15_s2': ('14:05', 0.5, lambda d: d in E['FOMC'] or d in month_end)}
    rows, skips = [], []
    for fam, (hm, k, skip_day) in cells.items():
        for d in days[fam]:
            if skip_day(d):
                skips.append({'test': fam, 'date': d, 'reason': 'event filter (F4)' if fam == 'h13_te' else 'event filter (F3)'})
                continue
            try:
                sess = sim.Session(d)
            except Exception as ex:  # noqa: BLE001
                skips.append({'test': fam, 'date': d, 'reason': f'session: {ex!r}'[:160]})
                continue
            ti = sim.hm2i(hm)
            reason, info, rr = sim.simulate(sess, ti, 0, k)
            if reason:
                skips.append({'test': fam, 'date': d, 'reason': reason})
                continue
            r = [x for x in rr if x['tp'] == 0.0 and x['stop'] == 0.0 and x['exit'] == 'E2']
            assert len(r) == 1, (fam, d, len(r))
            r = r[0]
            bids = [float(sess.bid_raw[rr_, ti, j]) for (rr_, j, sg) in info['legs'] if sg < 0]
            rh = sum(FR.option_fee('SPXW', b, 1, 'sell') for b in bids)
            old_fee = len(info['legs']) * sim.FEE
            assert abs(r['pnl'] - ((r['credit'] - (sim.intrinsic(0, r['kc'], r['settle']) + sim.intrinsic(1, r['kp'], r['settle']))) * 100 - old_fee)) < 1e-6
            rows.append({'test': fam, 'date': d, 'entry': hm, 'inst': 'SPXW straddle' if k == 0 else 'SPXW strangle', 'spot': info['spot'],
                         'em': info['em'], 'kc': r['kc'], 'kp': r['kp'], 'bid_c': bids[0], 'bid_p': bids[1], 'credit': r['credit'],
                         'cost': r['credit'] * 100, 'settle': r['settle'], 'settle_1600': r['settle_1600'], 'settle_flag': sess.settle_flag,
                         'fee_old': old_fee, 'fee_rh': rh, 'pnl_old': r['pnl'], 'pnl': r['pnl'] + old_fee - rh})
    pl.DataFrame(rows).write_parquet(HERE / 'out' / 't56_trades.parquet')
    pl.DataFrame(skips).write_csv(HERE / 'out' / 't56_skips.csv')
    (HERE / 'out' / 't56_code_sha256.json').write_text(json.dumps(sha, indent=1))
    t = pl.DataFrame(rows)
    print(t.group_by('test').len(), pl.DataFrame(skips).group_by('test', 'reason').len().sort('test'))


if __name__ == '__main__':
    main()
