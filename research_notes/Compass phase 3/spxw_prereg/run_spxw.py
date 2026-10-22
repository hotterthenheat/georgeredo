#!/usr/bin/env python3
"""
run_spxw.py — stage 2 of PREREG_SPXW.md (committed 2820bb4e061d865ddb2fcb640d1661b6c5105909 before any SPXW P&L was read).

Builds the two SPXW analogues (A: the fly5 iron → SPXW iron fly at 15:00 and 15:30, wings the listed strikes nearest
K0 ± 5 × SPX/SPY; B: condor_d20 → SPXW 20-delta iron condor at 13:00–15:00, wings 2 × SPX/SPY beyond the shorts) for every
full session 2022-05-13 → 2026-10-21, prices them at the legs' NBBO, the package NBBO rounded against us to $0.05, the
+$0.05 / +$0.10 package stresses and the mid, with the cited Cboe / ORF / OCC fees and $0.65 commission, settles them on the
official SPX close (Cboe's history; the last print at or before 16:00 beside it) and closes them again at 15:58; and measures
the ATM straddle's extrinsic at 15:00, 15:30 and 15:58 for SPY, QQQ and SPXW against the realized move to the official close.

The strike, delta and structure code is imported from scripts/paper_tracker.py (Chain, nearest_delta, Leg, Structure, _leg,
intrinsic) and the replay's adapter from scripts/paper_backtest.py (ParquetSource, chain_rows); the bootstraps, the calendar and
the ETF official closes from backtest_audit/audit_lib.py. Those files are read, never written. Outputs: out/ beside this file.

    PAPER_PARQUET_ROOT=<the stored Parquet> POLARS_MAX_THREADS=1 nice -n 10 python3 -I run_spxw.py build [--workers 3]
    python3 -I verify_50.py            # 50 structures re-derived from the raw files by separate code
    python3 -I run_spxw.py report      # → SPXW_REPORT.md and out/*.csv
No vendor is called; no key is read.
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import hashlib
import inspect
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
import multiprocessing as mp
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
AUDIT_DIR = REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(AUDIT_DIR))
import paper_tracker as T  # noqa: E402
import paper_backtest as B  # noqa: E402
import audit_lib as A  # noqa: E402

OUT = HERE / 'out'
PREREG_HASH = '2820bb4e061d865ddb2fcb640d1661b6c5105909'
START, END = '2022-05-13', '2026-10-21'
PERIODS = [('development', '2022-05-13', '2024-12-31'), ('selection', '2025-01-02', '2026-10-09'), ('forward', '2026-10-12', '2026-10-21')]
FLY_MIN = ('15:00', '15:30')
CON_MIN = ('13:00', '13:30', '14:00', '14:30', '15:00')
X_MIN = ('15:00', '15:30', '15:58')
EXIT = '15:58'
FLY_MULT, CON_MULT, DELTA = 5.0, 2.0, 0.20
STEP = 0.05                                   # Cboe: the net package price of an SPX/SPXW complex order is in $0.05 increments
# fees a contract (PREREG_SPXW.md section 4; the Cboe Fees Schedule of October 1, 2026; OCC's schedule since 2025-02-14)
COMMISSION, CBOE_LT1, CBOE_GE1, SPXW_EXEC, ORF, OCC = 0.65, 0.36, 0.45, 0.14, 0.01248, 0.025
CBOE_CSV = REPO / 'data' / 'official_closes' / 'cboe_SPX_History_2026-10-22.csv'
OLD = Path('/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/spx')
IMPORTED = {'scripts/paper_tracker.py': ('Chain', 'nearest_delta', 'otm_deltas', 'bsm_abs_delta', '_ncdf', 'Leg', 'Structure',
                                         '_leg', 'intrinsic', 'parse_symbol', 'fnum', 'Quote'),
            'scripts/paper_backtest.py': ('ParquetSource', 'chain_rows', 'occ', '_j')}


def jm(hhmm: str) -> int:
    return int(hhmm[:2]) * 60 + int(hhmm[3:5]) - 570


def fee(price: float) -> float:
    """one contract: commission + Cboe's customer SPX/SPXW fee by the leg's premium + the SPXW execution surcharge + ORF + OCC"""
    return COMMISSION + (CBOE_LT1 if price < 1.0 else CBOE_GE1) + SPXW_EXEC + ORF + OCC


def floor_step(x: float) -> float:
    return math.floor(x / STEP + 1e-6) * STEP


def ceil_step(x: float) -> float:
    return math.ceil(x / STEP - 1e-6) * STEP


def period_of(day: str) -> str | None:
    for p, a, b in PERIODS:
        if a <= day <= b:
            return p
    return None


# ---- the official closes ------------------------------------------------------------------------------------------------------------

def read_cboe(path: Path) -> dict:
    df = pl.read_csv(path, infer_schema_length=0)
    out = {}
    for d, v in zip(df['DATE'], df['SPX']):
        m, dd, y = d.split('/')
        out[f'{y}-{m}-{dd}'] = float(v)
    return out


def read_fred(path: Path) -> dict:
    df = pl.read_csv(path, infer_schema_length=0)
    return {d: float(v) for d, v in zip(df[df.columns[0]], df[df.columns[1]]) if v not in (None, '', '.')}


def spx_closes() -> tuple[dict, dict]:
    new = read_cboe(CBOE_CSV)
    check = {'cboe_new_rows': len(new), 'cboe_new_first': min(new), 'cboe_new_last': max(new)}
    for nm, path, reader in (('cboe_2026-10-14', OLD / 'cboe_spx.csv', read_cboe), ('fred_sp500', OLD / 'fred_sp500.csv', read_fred)):
        if not path.exists():
            check[nm] = 'not on disk'
            continue
        old = reader(path)
        both = sorted(set(old) & set(new))
        dis = [(d, new[d], old[d]) for d in both if abs(new[d] - old[d]) > 0.005]
        inr = [d for d in both if START <= d <= END]
        dis_r = [x for x in dis if START <= x[0] <= END]
        check[nm] = {'overlap': len(both), 'overlap_first': both[0] if both else None, 'overlap_last': both[-1] if both else None,
                     'overlap_in_range': len(inr), 'disagree_gt_0.005': len(dis), 'disagree_in_range': len(dis_r),
                     'max_abs_diff_in_range': max((abs(a - b) for _, a, b in dis_r), default=0.0),
                     'disagreements_in_range': [{'day': d, 'cboe_new': a, nm: b} for d, a, b in dis_r][:200],
                     'only_new_in_range': sorted(d for d in new if START <= d <= END and d not in old and d <= max(old))[:50]}
    return new, check


def etf_closes() -> tuple[dict, dict]:
    """AUDIT.md's official close for SPY and QQQ: Theta's EOD bar, else UW's daily bar (run_audit.official_closes)"""
    th = A.theta_eod(('SPY', 'QQQ'))
    uw = A.uw_daily(('SPY', 'QQQ'))
    j = th.join(uw, on=['symbol', 'day'], how='full', coalesce=True)
    off, src = {}, {}
    for r in j.to_dicts():
        k = (r['symbol'], r['day'])
        if r['close_theta'] is not None:
            off[k], src[k] = r['close_theta'], 'theta_eod'
        elif r['close_uw'] is not None:
            off[k], src[k] = r['close_uw'], 'uw_1d'
    return off, src


# ---- the code imported, checked against the committed version -----------------------------------------------------------------------

def code_check() -> dict:
    out = {}
    for rel, names in IMPORTED.items():
        p = REPO / rel
        out[rel] = {'sha256_working_tree': hashlib.sha256(p.read_bytes()).hexdigest()}
        try:
            head = subprocess.run(['git', '-C', str(REPO), 'show', f'HEAD:{rel}'], capture_output=True, text=True, check=True).stdout
            out[rel]['head'] = subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        except Exception as e:      # noqa: BLE001
            out[rel]['head_error'] = str(e)
            continue
        tree = ast.parse(head)
        lines = head.splitlines()
        seg = {n.name: '\n'.join(lines[min([n.lineno] + [d.lineno for d in n.decorator_list]) - 1:n.end_lineno])   # decorators included, as inspect gives them
               for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        mod = T if 'tracker' in rel else B
        same = {}
        for nm in names:
            obj = getattr(mod, nm)
            try:
                live = inspect.getsource(obj).rstrip()
            except (TypeError, OSError):
                live = None
            same[nm] = (live is not None and seg.get(nm, '').rstrip() == live)
        out[rel]['used_code_equal_to_HEAD'] = same
    return out


# ---- the structures -----------------------------------------------------------------------------------------------------------------

def wing_strike(listed: list, target: float, centre: float) -> float:
    """the listed strike nearest `target`; a tie goes to the strike farther from `centre` (the wider wing)"""
    return min(listed, key=lambda k: (abs(k - target), -abs(k - centre)))


def untradable(name: str, why: str, **extra) -> dict:
    return {'structure': name, 'tradable': False, 'reason': why, 'legs': [], **extra}


def iron_fly(chain: T.Chain, S: float, ratio: float) -> dict:
    k0 = chain.nearest(S)
    if k0 is None:
        return untradable('iron_fly', 'no strike with both sides quoted')
    listed = sorted(chain.listed)
    khi, klo = wing_strike(listed, k0 + FLY_MULT * ratio, k0), wing_strike(listed, k0 - FLY_MULT * ratio, k0)
    c0, p0 = chain.quote('C', k0), chain.quote('P', k0)
    chi, plo = chain.quote('C', khi), chain.quote('P', klo)
    why = []
    if not (khi > k0 > klo):
        why.append(f'wing strikes {klo:g}/{khi:g} not around K0 {k0:g}')
    if plo is None:
        why.append(f'put {klo:g} not quoted')
    if chi is None:
        why.append(f'call {khi:g} not quoted')
    if c0.bid <= 0 or p0.bid <= 0:
        why.append('a K0 bid is 0')
    width = max(khi - k0, k0 - klo)
    legs = [T._leg(c0, 'C', k0, 'short'), T._leg(p0, 'P', k0, 'short')] + ([T._leg(plo, 'P', klo, 'long')] if plo else []) + \
           ([T._leg(chi, 'C', khi, 'long')] if chi else [])
    s = T.Structure('iron_fly', 'credit', legs if len(legs) == 4 else [], k0, c0.mid + p0.mid, width, not why, '; '.join(why))
    if s.tradable and (s.max_risk() is None or s.max_risk() < 0.05 * ratio - 1e-9):
        s.tradable, s.reason = False, f'max risk {s.max_risk():.2f} under {0.05 * ratio:.4f} (0.05 x ratio)'
    return pack(s, {'k0': k0, 'k_hi': khi, 'k_lo': klo})


def condor20(chain: T.Chain, S: float, ratio: float) -> dict:
    kc, dc = T.nearest_delta(chain, S, 'call', DELTA)
    kp, dp = T.nearest_delta(chain, S, 'put', DELTA)
    listed = sorted(chain.listed)
    klc = wing_strike(listed, kc + CON_MULT * ratio, kc) if kc is not None else None
    klp = wing_strike(listed, kp - CON_MULT * ratio, kp) if kp is not None else None
    legs, why = [], []
    min_credit = 0.05 * ratio
    for right, ks, kl in (('C', kc, klc), ('P', kp, klp)):
        side = 'call' if right == 'C' else 'put'
        if ks is None:
            why.append(f'no {side} strike with a delta (no OTM quote with time value)')
            continue
        if (right == 'C' and not kl > ks) or (right == 'P' and not kl < ks):
            why.append(f'{side} wing {kl:g} not beyond the short {ks:g}')
            continue
        qs, ql = chain.quote(right, ks), chain.quote(right, kl)
        if qs is None or qs.bid <= 0:
            why.append(f'short {side} {ks:g} not quoted (bid > 0)')
        if ql is None or ql.ask <= 0:
            why.append(f'long {side} {kl:g} not quoted (ask > 0)')
        if qs is not None and ql is not None:
            legs += [T._leg(qs, right, ks, 'short'), T._leg(ql, right, kl, 'long')]
            if qs.bid > 0 and ql.ask > 0 and qs.bid - ql.ask < min_credit - 1e-9:
                why.append(f'{side} spread credit {qs.bid - ql.ask:.2f} under {min_credit:.4f} (0.05 x ratio)')
    ok = len(legs) == 4 and not why
    width = max((klc - kc) if (kc is not None and klc is not None) else 0.0, (kp - klp) if (kp is not None and klp is not None) else 0.0)
    st = chain.straddle(S)
    s = T.Structure('condor_d20', 'credit', legs if len(legs) == 4 else [], st[0] if st else None, st[1] if st else None, width, ok, '; '.join(why))
    return pack(s, {'k_sc': kc, 'k_sp': kp, 'd_sc': dc, 'd_sp': dp, 'k_lc': klc, 'k_lp': klp})


def pack(s: T.Structure, extra: dict) -> dict:
    d = {'structure': s.structure, 'tradable': bool(s.tradable), 'reason': s.reason, 'width': s.wing, 'straddle': s.straddle,
         'legs': [{'right': l.right, 'k': l.strike, 'side': l.side, 'qty': l.qty, 'bid': l.bid, 'ask': l.ask} for l in s.legs]}
    d.update(extra)
    if s.legs:
        d['credit_legs'] = s.price()
        d['credit_mid'] = s.price(mid=True)
    return d


# ---- one session --------------------------------------------------------------------------------------------------------------------

_SRC = None


def _src() -> B.ParquetSource:
    global _SRC
    if _SRC is None:
        _SRC = B.ParquetSource(Path(os.environ['PAPER_PARQUET_ROOT']), keep=2)
    return _SRC


def chain_at(name: str, day: str, m: int) -> T.Chain | None:
    rows = B.chain_rows(_src(), name, day, m)
    if rows is None:
        return None
    root = B.CHAIN_ROOT.get(name, name)
    return T.Chain(rows, day, root=root)


def do_day(day: str) -> dict:
    src = _src()
    pr = dict(src.prints('SPX', day) or [])
    spy = src.bars('SPY', day)
    spy_c = dict(zip(spy['j'], spy['c'])) if spy else {}
    print16 = None
    for j in sorted(pr):
        if j <= 390:
            print16 = pr[j]
    out = {'day': day, 'trades': [], 'x': [], 'print16': print16}
    cache = {}
    for hhmm in sorted(set(FLY_MIN) | set(CON_MIN)):
        m = jm(hhmm)
        S, sy = pr.get(m), spy_c.get(m - 1)
        ch = chain_at('SPX', day, m)
        cache[hhmm] = (ch, S)
        builds = (['iron_fly'] if hhmm in FLY_MIN else []) + (['condor_d20'] if hhmm in CON_MIN else [])
        for b in builds:
            base = {'day': day, 'minute': hhmm, 'analogue': b, 'spot': S, 'spy': sy, 'ratio': (S / sy) if (S and sy) else None}
            if ch is None:
                r = untradable(b, 'no chain file')
            elif S is None:
                r = untradable(b, 'no SPX print')
            elif sy is None:
                r = untradable(b, 'no SPY bar close (no ratio)')
            else:
                r = iron_fly(ch, S, S / sy) if b == 'iron_fly' else condor20(ch, S, S / sy)
            base.update(r)
            out['trades'].append(base)
    c58 = chain_at('SPX', day, jm(EXIT))
    for t in out['trades']:
        t['exit'] = [None if c58 is None or c58.quote(l['right'], l['k']) is None else
                     (c58.quote(l['right'], l['k']).bid, c58.quote(l['right'], l['k']).ask) for l in t['legs']]
    # the ATM extrinsic
    for name in ('SPY', 'QQQ', 'SPX'):
        bars = None if name == 'SPX' else src.bars(name, day)
        bc = dict(zip(bars['j'], bars['c'])) if bars else {}
        for hhmm in X_MIN:
            m = jm(hhmm)
            S = pr.get(m) if name == 'SPX' else bc.get(m - 1)
            ch = cache[hhmm][0] if (name == 'SPX' and hhmm in cache) else chain_at(name, day, m)
            rec = {'day': day, 'name': 'SPXW' if name == 'SPX' else name, 'minute': hhmm, 'spot': S}
            if ch is None or S is None:
                rec['why'] = 'no chain' if ch is None else 'no spot'
                out['x'].append(rec)
                continue
            k = ch.nearest(S)
            if k is None:
                rec['why'] = 'no strike with both sides quoted'
                out['x'].append(rec)
                continue
            cm, pm = ch.calls[k].mid, ch.puts[k].mid
            rec.update({'k': k, 'call_mid': cm, 'put_mid': pm, 'extrinsic': cm + pm - abs(S - k),
                        'call_w': ch.calls[k].ask - ch.calls[k].bid, 'put_w': ch.puts[k].ask - ch.puts[k].bid})
            out['x'].append(rec)
    return out


# ---- P&L -----------------------------------------------------------------------------------------------------------------------------

def payoff(legs: list, px: float) -> float:
    return sum((1 if l['side'] == 'long' else -1) * l['qty'] * T.intrinsic(px, l['k'], l['right']) for l in legs)


def pnl_rows(t: dict, official: float | None, p16: float | None) -> dict:
    """every fill variant, both settlements, the 15:58 exits; dollars one lot"""
    legs = t['legs']
    fill = [(l['bid'] if l['side'] == 'short' else l['ask']) for l in legs]
    f_open = sum(l['qty'] * fee(p) for l, p in zip(legs, fill))
    cl = t['credit_legs']
    pk = floor_step(cl)
    credits = {'legs': cl, 'pkg': pk, 'pkg5': pk - STEP, 'pkg10': pk - 2 * STEP, 'mid': t['credit_mid']}
    r = {'fees_open': f_open, 'credit_pkg': pk}
    for v, c in credits.items():
        r[f'risk_{v}'] = (t['width'] - c) * 100
        for sname, px in (('off', official), ('p16', p16)):
            r[f'pnl_{v}_{sname}'] = None if px is None else (c + payoff(legs, px)) * 100 - f_open
    # 15:58
    ex = t['exit']
    if any(q is None for q in ex):
        r['exit_reason'] = 'a leg not quoted at 15:58'
        return r
    # legs: the tracker's liquidation rule; an abandoned long (bid 0) settles at intrinsic on the official close, no fee
    cost, f_close, aband = 0.0, 0.0, []
    for l, (b, a) in zip(legs, ex):
        if l['side'] == 'long':
            if b <= 0:
                aband.append(l)
                continue
            cost -= l['qty'] * b
            f_close += l['qty'] * fee(b)
        else:
            cost += l['qty'] * a
            f_close += l['qty'] * fee(a)
    ab = payoff(aband, official) if (aband and official is not None) else 0.0
    r['x_legs'] = (cl - cost + ab) * 100 - f_open - f_close
    r['x_abandoned'] = len(aband)
    # package: Σ short asks − Σ long bids, rounded up to $0.05, every leg closed
    raw = sum(l['qty'] * (a if l['side'] == 'short' else -b) for l, (b, a) in zip(legs, ex))
    f_all = sum(l['qty'] * fee(a if l['side'] == 'short' else b) for l, (b, a) in zip(legs, ex))
    pc = ceil_step(raw)
    r['x_pkg'] = (pk - pc) * 100 - f_open - f_all
    r['x_pkg5'] = (pk - STEP - pc - STEP) * 100 - f_open - f_all
    r['x_pkg10'] = (pk - 2 * STEP - pc - 2 * STEP) * 100 - f_open - f_all
    mc = sum(l['qty'] * ((a + b) / 2) * (1 if l['side'] == 'short' else -1) for l, (b, a) in zip(legs, ex))
    r['x_mid'] = (t['credit_mid'] - mc) * 100 - f_open - f_all
    r['exit_cost_raw'], r['exit_cost_pkg'], r['fees_close_pkg'] = raw, pc, f_all
    return r


# ---- build -----------------------------------------------------------------------------------------------------------------------------

def build(workers: int) -> None:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    root = Path(os.environ['PAPER_PARQUET_ROOT'])
    closes, check = spx_closes()
    exp = A.expected_sessions(START, END)
    excluded, days = [], []
    for d in exp:
        miss = [w for w, f in (('SPXW chain', root / 'data_full/chains/SPXW' / f'{d}.parquet'), ('SPX prints', root / 'data/index/SPX' / f'{d}.parquet'),
                               ('SPY bars', root / 'data/underlying/SPY' / f'{d}.parquet')) if not f.exists()]
        if d not in closes:
            miss.append('official SPX close')
        if miss:
            excluded.append({'day': d, 'missing': miss})
        else:
            days.append(d)
    files = sorted(f.stem for f in (root / 'data_full/chains/SPXW').glob('*.parquet'))
    extra = [d for d in files if START <= d <= END and d not in exp]
    trades, xs, p16 = [], [], {}
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context('spawn')) as ex:   # spawn: polars' threads do not survive a fork
        for i, res in enumerate(ex.map(do_day, days, chunksize=4)):
            p16[res['day']] = res['print16']
            trades += res['trades']
            xs += res['x']
            if i % 100 == 0:
                print(f'{res["day"]} {i}/{len(days)} {time.time() - t0:.0f}s', flush=True)
    for t in trades:
        t.update(pnl_rows(t, closes.get(t['day']), p16.get(t['day'])) if t['tradable'] else {})
        t['period'] = period_of(t['day'])
        t['official'] = closes.get(t['day'])
        t['print16'] = p16.get(t['day'])
    rows = []
    for t in trades:
        r = {k: v for k, v in t.items() if k not in ('legs', 'exit')}
        r['legs_json'] = json.dumps(t['legs'])
        r['exit_json'] = json.dumps(t['exit'])
        rows.append(r)
    pl.DataFrame(rows, infer_schema_length=None).write_parquet(OUT / 'trades.parquet')
    pl.DataFrame(xs, infer_schema_length=None).write_parquet(OUT / 'extrinsic_raw.parquet')
    meta = {'prereg': PREREG_HASH, 'built_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), 'seconds': round(time.time() - t0),
            'expected_sessions': len(exp), 'sessions': len(days), 'excluded': excluded, 'chain_files_not_full_sessions': extra,
            'spx_close_check': check, 'code': code_check(), 'print16': p16, 'parquet_root': str(root)}
    (OUT / 'build.json').write_text(json.dumps(meta, indent=1, default=str))
    print(f'built {len(trades)} rows, {len(xs)} extrinsic rows, {len(days)} sessions in {time.time() - t0:.0f}s')


# ---- statistics --------------------------------------------------------------------------------------------------------------------------

def sess_sums(df: pl.DataFrame, col: str, days: list) -> tuple[np.ndarray, np.ndarray]:
    sub = df.filter(pl.col(col).is_not_null())
    g = sub.group_by('day').agg(pl.col(col).sum().alias('s'), pl.len().alias('n'))
    m = {d: (s, n) for d, s, n in g.iter_rows()}
    S = np.array([m.get(d, (0.0, 0))[0] for d in days], float)
    N = np.array([m.get(d, (0.0, 0))[1] for d in days], float)
    return S, N


def risk_facts(df: pl.DataFrame, col: str, risk: str, days: list) -> dict:
    sub = df.filter(pl.col(col).is_not_null())
    x = sub[col].to_numpy()
    rk = sub[risk].to_numpy()
    S, _ = sess_sums(df, col, days)
    out = {'trades': int(x.size)}
    if x.size == 0:
        return out
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    i = int(np.argmin(S)) if S.size else None
    out.update({'mean_trade': float(x.mean()), 'mean_pct_risk': float(np.mean(x / rk) * 100), 'mean_risk': float(rk.mean()),
                'win': float((x > 0).mean()), 'pf': float(pos / neg) if neg > 0 else float('inf'), 'dd': A.drawdown(S),
                'worst_day': days[i] if i is not None else None, 'worst': float(S[i]) if i is not None else None,
                'streak': A.losing_streak(S), 'full_loss': float((x <= -0.95 * rk).mean()),
                'p1': float(np.percentile(S, 1)), 'p5': float(np.percentile(S, 5)), 'total': float(x.sum())})
    return out


def stats_cell(df: pl.DataFrame, col: str, days: list) -> dict:
    S, N = sess_sums(df, col, days)
    return A.session_stats(S, N)


def ratio_boot(E: np.ndarray, Rz: np.ndarray, B_: int = A.BOOT_N, block: int = 20):
    n = E.size
    if n < 3 * block:
        return None
    idx = A.block_draws(n, block)
    return E[idx].mean(1) / Rz[idx].mean(1), (E[idx] - Rz[idx]).mean(1)


def report() -> None:
    meta = json.loads((OUT / 'build.json').read_text())
    tr = pl.read_parquet(OUT / 'trades.parquet')
    xr = pl.read_parquet(OUT / 'extrinsic_raw.parquet')
    sessions = sorted(set(meta['print16']))
    per = {p: [d for d in sessions if a <= d <= b] for p, a, b in PERIODS}
    V = ('legs', 'pkg', 'pkg5', 'pkg10', 'mid')
    res = {'periods': {p: len(v) for p, v in per.items()}, 'cells': {}, 'verdict': {}}
    for an in ('iron_fly', 'condor_d20'):
        for p, days in per.items():
            d = tr.filter((pl.col('analogue') == an) & (pl.col('period') == p))
            cell = {'rows': d.height, 'tradable': int(d['tradable'].sum()),
                    'reasons': {k: v for k, v in d.filter(~pl.col('tradable'))['reason'].str.split('; ').explode()
                                .str.replace_all(r'[-0-9.]+', '#').value_counts().iter_rows()} if d.filter(~pl.col('tradable')).height else {}}
            dt_ = d.filter(pl.col('tradable'))
            for v in V:
                for s in ('off', 'p16'):
                    cell[f'{v}_{s}'] = stats_cell(dt_, f'pnl_{v}_{s}', days)
                cell[f'risk_{v}'] = risk_facts(dt_, f'pnl_{v}_off', f'risk_{v}', days)
                cell[f'x_{v}'] = stats_cell(dt_, f'x_{v}', days)
            if dt_.height:
                cell['width_counts'] = {str(k): v for k, v in dt_['width'].value_counts().iter_rows()}
                cell['credit_legs_mean'] = float(dt_['credit_legs'].mean())
                cell['credit_pkg_mean'] = float(dt_['credit_pkg'].mean())
                cell['round_loss_mean'] = float((dt_['credit_legs'] - dt_['credit_pkg']).mean())
                cell['fees_open_mean'] = float(dt_['fees_open'].mean())
                cell['fees_close_pkg_mean'] = float(dt_['fees_close_pkg'].drop_nulls().mean()) if dt_['fees_close_pkg'].drop_nulls().len() else None
                cell['x_unavailable'] = int(dt_['x_pkg'].is_null().sum())
                cell['x_abandoned_trades'] = int((dt_['x_abandoned'].fill_null(0) > 0).sum())
                cell['ratio_med'] = float(dt_['ratio'].median())
                cell['settle_diff'] = {'sessions_differing_gt_0.005': int(d.filter(pl.col('tradable') & ((pl.col('official') - pl.col('print16')).abs() > 0.005))['day'].n_unique()),
                                       'trades_pnl_changed': int((dt_['pnl_pkg_off'] - dt_['pnl_pkg_p16']).abs().gt(0.005).sum())}
            res['cells'][f'{an}|{p}'] = cell
        sel, dev = res['cells'][f'{an}|selection'], res['cells'][f'{an}|development']
        c1m = sel['pkg_off'].get('mean_session', float('nan'))
        c1lo = sel['pkg_off'].get('ci_session_b20', (float('nan'),) * 2)[0]
        c2 = sel['pkg5_off'].get('mean_session', float('nan'))
        c3 = dev['pkg_off'].get('mean_session', float('nan'))
        cond = {'1: selection mean > 0': c1m > 0, '1: selection block-20 lower bound > 0': c1lo > 0,
                '2: selection mean at +$0.05 package stress > 0': c2 > 0, '3: development mean > 0': c3 > 0}
        res['verdict'][an] = {'conditions': cond, 'values': {'sel_mean': c1m, 'sel_ci_b20': sel['pkg_off'].get('ci_session_b20'),
                                                             'sel_pkg5_mean': c2, 'dev_mean': c3},
                              'verdict': 'PASS' if all(cond.values()) else 'FAIL'}
    # the extrinsic study
    off_etf, src_etf = etf_closes()
    spx = read_cboe(CBOE_CSV)
    x = xr.filter(pl.col('extrinsic').is_not_null())
    def realized(name, day, spot):
        c = spx.get(day) if name == 'SPXW' else off_etf.get((name, day))
        return None if c is None else abs(c - spot) / spot * 1e4
    x = x.with_columns(pl.struct('name', 'day', 'spot').map_elements(lambda s: realized(s['name'], s['day'], s['spot']), return_dtype=pl.Float64).alias('real_bps'),
                       (pl.col('extrinsic') / pl.col('spot') * 1e4).alias('ext_bps'),
                       (pl.col('k') % 0.5).gt(1e-6).alias('adjusted_strike'))
    x = x.with_columns(pl.col('day').map_elements(period_of, return_dtype=pl.String).alias('period'))
    x.write_parquet(OUT / 'extrinsic.parquet')
    xres = {'missing': [list(r) for r in xr.filter(pl.col('extrinsic').is_null()).group_by('name', 'why').len().sort('name').iter_rows()],
            'no_close': [list(r) for r in x.filter(pl.col('real_bps').is_null()).group_by('name').len().iter_rows()],
            'adjusted_strike_rows': [list(r) for r in x.filter(pl.col('adjusted_strike')).group_by('name').len().iter_rows()],
            'etf_close_sources': {}, 'cells': {}, 'gaps': {}}
    for p, a, b in PERIODS:
        for mnt in X_MIN:
            sub = x.filter((pl.col('period') == p) & (pl.col('minute') == mnt) & pl.col('real_bps').is_not_null())
            for nm in ('SPY', 'QQQ', 'SPXW'):
                s = sub.filter(pl.col('name') == nm).sort('day')
                if s.height == 0:
                    continue
                E, Rz = s['ext_bps'].to_numpy(), s['real_bps'].to_numpy()
                c = {'n': s.height, 'first': s['day'][0], 'ext': float(E.mean()), 'real': float(Rz.mean()), 'ratio': float(E.mean() / Rz.mean()),
                     'diff': float((E - Rz).mean()), 'ext_med': float(np.median(E)), 'real_med': float(np.median(Rz)),
                     'atm_dist_bps': float((s['k'] - s['spot']).abs().mean() / s['spot'].mean() * 1e4)}
                bt = ratio_boot(E, Rz)
                if bt:
                    c['ratio_ci'], c['diff_ci'] = A.pct_ci(bt[0]), A.pct_ci(bt[1])
                xres['cells'][f'{p}|{mnt}|{nm}'] = c
            # gaps on the common sessions
            w = sub.select('day', 'name', 'ext_bps', 'real_bps').pivot(on='name', index='day', values=['ext_bps', 'real_bps'])
            need = [f'{v}_{n}' for v in ('ext_bps', 'real_bps') for n in ('SPY', 'QQQ', 'SPXW')]
            if not all(c in w.columns for c in need):
                continue
            w = w.drop_nulls(need).sort('day')
            n = w.height
            if n == 0:
                continue
            g = {'n': n}
            idx = A.block_draws(n, 20) if n >= 60 else None
            for etf in ('SPY', 'QQQ'):
                Ee, Re, Es, Rs = (w[f'ext_bps_{etf}'].to_numpy(), w[f'real_bps_{etf}'].to_numpy(), w['ext_bps_SPXW'].to_numpy(), w['real_bps_SPXW'].to_numpy())
                g[f'{etf}_ratio'], g['SPXW_ratio'] = float(Ee.mean() / Re.mean()), float(Es.mean() / Rs.mean())
                g[f'{etf}_minus_SPXW_ratio'] = g[f'{etf}_ratio'] - g['SPXW_ratio']
                g[f'{etf}_minus_SPXW_diff'] = float((Ee - Re).mean() - (Es - Rs).mean())
                g[f'{etf}_minus_SPXW_ext'] = float(Ee.mean() - Es.mean())
                g[f'{etf}_minus_SPXW_real'] = float(Re.mean() - Rs.mean())
                if idx is not None:
                    rb = Ee[idx].mean(1) / Re[idx].mean(1) - Es[idx].mean(1) / Rs[idx].mean(1)
                    db = (Ee[idx] - Re[idx]).mean(1) - (Es[idx] - Rs[idx]).mean(1)
                    eb = Ee[idx].mean(1) - Es[idx].mean(1)
                    g[f'{etf}_minus_SPXW_ratio_ci'], g[f'{etf}_minus_SPXW_diff_ci'], g[f'{etf}_minus_SPXW_ext_ci'] = A.pct_ci(rb), A.pct_ci(db), A.pct_ci(eb)
            xres['gaps'][f'{p}|{mnt}'] = g
    res['extrinsic'] = xres
    (OUT / 'results.json').write_text(json.dumps(res, indent=1, default=str))
    import write_report
    write_report.write(meta, res, tr)
    print('report written')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('step', choices=('build', 'report'))
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    if a.step == 'build':
        build(a.workers)
    else:
        sys.path.insert(0, str(HERE))
        report()
    return 0


if __name__ == '__main__':
    sys.exit(main())
