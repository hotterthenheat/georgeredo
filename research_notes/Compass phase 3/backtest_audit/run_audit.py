#!/usr/bin/env python3
"""
run_audit.py — the audit of the paper tracker's historical replay and the corrected cumulative report, from the
replay's rows (read, never written) and the files on disk. ONE COMMAND writes both reports:

    cd "research_notes/Compass phase 3/backtest_audit"
    PAPER_PARQUET_ROOT=<the stored Parquet> POLARS_MAX_THREADS=1 nice -n 10 python3 -I run_audit.py \
        [--root ../../../data_recorder/paper_backtest] [--through 2026-10-21] [--rerun-root DIR --rerun-csv FILE]

→ AUDIT.md, cumulative_through_<through>.md, out/*.json, out/*.csv. The historical periods (i)/(ii) and the forward
period (iii, sessions from 2026-10-12) are kept in separate tables; nothing is pooled across them into a headline. When
the parquet root and the replay root later hold 2026-10-12 → <through>, the same command fills the forward tables.

Corrections applied here (the replay's rows are left as they are): every trade re-settled on the OFFICIAL close (Theta's
EOD daily bar, cross-checked against UW's daily bar where both exist) in place of the 15:59 bar; inference on SESSION
sums by session and moving-block bootstraps; periods kept apart; the 15:58 close-out priced for the condors too (the
replay logs it for fly5 only) off the raw chain at 15:58 with the tracker's own exit rule.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_lib as A  # noqa: E402
import check_entries as CE  # noqa: E402
import check_integrity as CI  # noqa: E402

f, ci = A.f, A.ci
REPORT_DIR = A.REPO / 'research_notes' / 'Compass phase 3' / 'backtest_replay'
REPORT_CSV = REPORT_DIR / 'backtest_2022-11-11_2026-10-09.csv'
EVENTS = ('FOMC_DECISION', 'FOMC_MINUTES', 'CPI', 'NFP')


# ---- the trades ----------------------------------------------------------------------------------------------------------------------

def official_closes() -> tuple[dict, dict, pl.DataFrame]:
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
    return off, src, j


def liq_1558(parquet_root: Path | None, need: dict, cache_file: Path) -> dict:
    """{(name, day): {(right, strike): (bid, ask)}} at the rows stamped 15:58, for the legs asked (cached)"""
    cache: dict = {}
    if cache_file.exists():
        for r in pl.read_parquet(cache_file).to_dicts():
            cache.setdefault((r['name'], r['day']), {})[(r['right'], r['strike'])] = (r['bid'], r['ask'])
    todo = [(nm, d) for (nm, d) in need if not all(x in cache.get((nm, d), {}) for x in need[(nm, d)])]
    if todo and parquet_root is not None:
        for nm, d in todo:
            fpath = Path(parquet_root) / 'data_full' / 'chains' / nm / f'{d}.parquet'
            if not fpath.exists():
                continue
            c = (pl.scan_parquet(fpath).filter((pl.col('timestamp').dt.hour() == 15) & (pl.col('timestamp').dt.minute() == 58))
                 .select('strike', 'right', 'bid', 'ask').collect())
            got = cache.setdefault((nm, d), {})
            for k, r, b, a in c.iter_rows():
                key = ('C' if r.upper().startswith('C') else 'P', round(float(k), 3))
                if key in need[(nm, d)]:
                    got[key] = (b, a)
            for key in need[(nm, d)]:
                if key[0] != 'S':
                    got.setdefault(key, (None, None))
            fu = Path(parquet_root) / 'data' / 'underlying' / nm / f'{d}.parquet'
            if fu.exists():           # the spot known at 15:58: the close of the bar stamped 15:57
                u = (pl.scan_parquet(fu).filter((pl.col('timestamp').dt.hour() == 15) & (pl.col('timestamp').dt.minute() == 57)).select('close').collect())
                got[('S', 0.0)] = (u['close'][0] if u.height else None, None)
        rows = [{'name': nm, 'day': d, 'right': k[0], 'strike': k[1], 'bid': v[0], 'ask': v[1]} for (nm, d), m in cache.items() for k, v in m.items()]
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        pl.DataFrame(rows, schema={'name': pl.Utf8, 'day': pl.Utf8, 'right': pl.Utf8, 'strike': pl.Float64, 'bid': pl.Float64, 'ask': pl.Float64}).write_parquet(cache_file)
    return cache


def exit_1558(legs, entry_cash: float, quotes: dict, worse: float = 0.0) -> tuple[float | None, float | None, int]:
    """the tracker's 15:58 rule, written again: sell a long at its bid (a long with no bid is left to expire, no fee),
    buy a short back at its ask; $0.65 a contract closed; `worse` cents a contract against us at the exit too.
    → (P&L at the NBBO before the entry stress, at the mid, contracts closed); None when a leg has no quote"""
    nb = md = 0.0
    closed = 0
    for r, k, side, q in legs:
        b, a = quotes.get((r, k), (None, None))
        if b is None or a is None or a < b or b < 0:
            return None, None, 0
        if side == 'long':
            if b <= 0:
                continue
            nb += q * (b - worse)
            md += q * (b + a) / 2
        else:
            nb -= q * (a + worse)
            md -= q * (b + a) / 2
        closed += q
    return nb, md, closed


def exit_partial(legs, entry_cash: float, quotes: dict, spot58, settle: float, buf: float):
    """a margin account's middle road (not the tracker's rule): at 15:58 close only the legs in the money at the 15:58
    spot or within `buf` of it (the tracker's exit rule for those legs), leave the rest to expire and settle them at the
    official close. → (P&L, whether a leg left open finished in the money — an exercise or assignment left to happen)"""
    if spot58 is None:
        return None
    nb, closed, pay, resid = 0.0, 0, 0.0, False
    for r, k, side, q in legs:
        near = A.intrinsic(spot58, k, r) > 0 or abs(k - spot58) <= buf
        if not near:
            v = A.intrinsic(settle, k, r)
            pay += (1 if side == 'long' else -1) * q * v
            resid = resid or v >= 0.005
            continue
        b, a = quotes.get((r, k), (None, None))
        if b is None or a is None or a < b or b < 0:
            return None
        if side == 'long':
            if b <= 0:
                continue
            nb += q * b
        else:
            nb -= q * a
        closed += q
    return (entry_cash + nb + pay) * 100 - A.CONTRACTS * A.FEE - closed * A.FEE, resid


def build_trades(df: pl.DataFrame, parquet_root: Path | None, out: Path) -> tuple[list, dict]:
    off, off_src, closes = official_closes()
    md = A.macro_days()
    caps = df.filter(pl.col('row_kind') == 'capture')
    sett = df.filter(pl.col('row_kind') == 'settle')
    clo = df.filter(pl.col('row_kind') == 'close1558')
    k5 = ('candidate', '_name', '_day', 'minute', 'structure')
    S = {tuple(r[k] for k in k5): r for r in sett.to_dicts()}
    C = {tuple(r[k] for k in k5): r for r in clo.to_dicts()}
    tr = []
    need: dict = defaultdict(set)
    for c in caps.filter(pl.col('tradable') == 'true').to_dicts():
        key = tuple(c[k] for k in k5)
        s = S.get(key)
        legs = A.legs_of(c)
        t = {'key': c['candidate'], 'name': c['_name'], 'day': c['_day'], 'minute': c['minute'], 'structure': c['structure'],
             'period': A.period_of(c['candidate'], c['_day']), 'legs': legs, 'package': c['package'],
             'price_nbbo': c['price_nbbo_f'], 'price_mid': c['price_mid_f'], 'max_risk': c['max_risk_f'],
             'width': sum(q * (c[f'l{i}_ask_f'] - c[f'l{i}_bid_f']) for i, (_, _, _, q) in enumerate(legs, 1)),
             'd1': c.get('t2_decile_primary'), 'd1_novix': c.get('t2_decile_novix'),
             'events': sorted(md.get(c['_day'], set())), 'settled': s is not None}
        if s is None:
            tr.append(t)
            continue
        px = s['settle_px_f']
        o = off.get((c['_name'], c['_day']))
        t.update({'settle_1559': px, 'official': o, 'official_src': off_src.get((c['_name'], c['_day'])),
                  'pnl_nbbo_r': s['pnl_nbbo_f'], 'pnl_mid_r': s['pnl_mid_f'], 'pnl_1c_r': s['pnl_1c_f'], 'pnl_2c_r': s['pnl_2c_f'],
                  'payoff_r': s['payoff_f']})
        p59 = A.payoff(legs, px)
        t['payoff_check'] = abs(p59 - s['payoff_f']) < 1e-6
        use = o if o is not None else px
        delta = (A.payoff(legs, use) - p59) * 100
        t['delta_off'] = delta
        for x in ('nbbo', 'mid', '1c', '2c'):
            t[f'pnl_{x}'] = t[f'pnl_{x}_r'] + delta
        a, b = min(px, use), max(px, use)
        t['cross'] = any(a < k < b for _, k, _, _ in legs)
        t['strike_between_or_on'] = any(a <= k <= b for _, k, _, _ in legs) and a != b
        # expiration mechanics at the official close
        itm = [(r, k, side, q) for r, k, side, q in legs if A.intrinsic(use, k, r) >= 0.005]
        t['any_itm'] = bool(itm)
        t['short_itm'] = sum(q for r, k, side, q in itm if side == 'short')
        t['long_itm'] = sum(q for r, k, side, q in itm if side == 'long')
        sh = sum((100 * q) * ((1 if side == 'long' else -1) * (1 if r == 'C' else -1)) for r, k, side, q in itm)
        t['net_shares'] = sh
        t['assign_notional'] = sum(100 * q * k for r, k, side, q in itm if side == 'short')
        t['net_stock_value'] = abs(sh) * use
        shorts = [k for r, k, side, q in legs if side == 'short']
        t['pin_dist'] = min(abs(use - k) for k in shorts) if shorts else float('nan')
        t['itm_changes'] = any((A.intrinsic(px, k, r) >= 0.005) != (A.intrinsic(use, k, r) >= 0.005) for r, k, _, _ in legs)
        t['risk_usd'] = t['max_risk'] * 100
        cl = C.get(key)
        if cl is not None and cl.get('pnl_1558_nbbo_f') is not None:
            t['pnl_1558_r'] = cl['pnl_1558_nbbo_f']
            t['pnl_1558_mid_r'] = cl['pnl_1558_mid_f']
        need[(c['_name'], c['_day'])] |= {(r, k) for r, k, _, _ in legs} | {('S', 0.0)}
        tr.append(t)
    q = liq_1558(parquet_root, need, out / 'quotes_1558_cache.parquet')
    for t in tr:
        if not t.get('settled'):
            continue
        quotes = q.get((t['name'], t['day']))
        if not quotes:
            continue
        entry = t['price_nbbo'] if t['package'] == 'credit' else -t['price_nbbo']
        entry_mid = t['price_mid'] if t['package'] == 'credit' else -t['price_mid']
        for tag, worse in (('', 0.0), ('_1c', 0.01), ('_2c', 0.02)):
            nb, mdv, closed = exit_1558(t['legs'], entry, quotes, worse)
            if nb is None:
                break
            e = entry - (A.CONTRACTS * worse if worse else 0.0)        # the entry stress: every contract `worse` (as pnl_1c / pnl_2c)
            t[f'pnl_1558{tag}'] = (e + nb) * 100 - A.CONTRACTS * A.FEE - closed * A.FEE
            if not tag:
                t['pnl_1558_mid'] = (entry_mid + mdv) * 100 - A.CONTRACTS * A.FEE - closed * A.FEE
                t['closed_1558'] = closed
        s58 = quotes.get(('S', 0.0), (None, None))[0]
        use = t['official'] if t['official'] is not None else t['settle_1559']
        for buf in (0.5, 1.0):
            r_ = exit_partial(t['legs'], entry, quotes, s58, use, buf)
            if r_ is not None:
                t[f'pnl_part{buf}'], t[f'resid_itm{buf}'] = r_
    return tr, {'closes': closes, 'official': off, 'official_src': off_src}


# ---- sessions --------------------------------------------------------------------------------------------------------------------------

def replayed_days(root: Path) -> list[str]:
    return sorted(d for d, v in CI.read_days(root).items() if v['status'] == 'replayed')


def sessions_of(days_all: list, key: str, period: str) -> list[str]:
    return [d for d in days_all if A.period_of(key, d) == period]


def series(tr: list, days: list, col: str = 'pnl_nbbo', filt=None) -> tuple[np.ndarray, np.ndarray]:
    ix = {d: i for i, d in enumerate(days)}
    S, N = np.zeros(len(days)), np.zeros(len(days))
    for t in tr:
        if t['day'] in ix and t.get(col) is not None and (filt is None or filt(t)):
            S[ix[t['day']]] += t[col]
            N[ix[t['day']]] += 1
    return S, N


def risk_row(tr: list, days: list, col: str = 'pnl_nbbo') -> dict:
    xs = [t for t in tr if t['day'] in set(days) and t.get(col) is not None]
    if not xs:
        return {'trades': 0, 'sessions': len(days)}
    x = np.array([t[col] for t in xs])
    risk = np.array([t['risk_usd'] for t in xs])
    S, N = series(xs, days, col)
    st = A.session_stats(S, N)
    traded = S[N > 0]
    gw, gl = x[x > 0].sum(), -x[x < 0].sum()
    worst_i = int(np.argmin(np.where(N > 0, S, np.inf)))
    return dict(st, mean_pct=float(np.mean(x / risk)), mean_risk=float(risk.mean()), win=float((x > 0).mean()),
                pf=float(gw / gl) if gl > 0 else float('inf'), dd=A.drawdown(traded), worst_session=(days[worst_i], float(S[worst_i])),
                streak=A.losing_streak(traded), full_loss=float(np.mean(x <= -0.95 * risk)),
                p1=float(np.percentile(traded, 1)), p5=float(np.percentile(traded, 5)), total=float(x.sum()))


# ---- the D1 lift ---------------------------------------------------------------------------------------------------------------------

def lift_mats(tr: list, days: list, minutes: tuple, col: str = 'pnl_nbbo', pct: bool = False, dcol: str = 'd1'):
    ix = {d: i for i, d in enumerate(days)}
    n, M = len(days), len(minutes)
    S, N, S1, N1 = (np.zeros((n, M)) for _ in range(4))
    for t in tr:
        if t['day'] not in ix or t.get(col) is None or t['minute'] not in minutes or t.get(dcol) is None:
            continue
        v = t[col] / t['risk_usd'] if pct else t[col]
        i, m = ix[t['day']], minutes.index(t['minute'])
        S[i, m] += v
        N[i, m] += 1
        if str(t[dcol]) == '1':
            S1[i, m] += v
            N1[i, m] += 1
    return S, N, S1, N1


def lift_time(W, S, N, S1, N1):
    s, nn, s1, n1 = W @ S, W @ N, W @ S1, W @ N1          # (B, M)
    with np.errstate(invalid='ignore', divide='ignore'):
        good = (n1 > 0) & (nn > 0)
        term = np.where(good, n1 * (np.where(good, s1 / np.where(n1 > 0, n1, 1), 0) - np.where(good, s / np.where(nn > 0, nn, 1), 0)), 0)
        den = np.where(good, n1, 0).sum(1)
        return np.where(den > 0, term.sum(1) / np.where(den > 0, den, 1), np.nan)


def lift_session(W, S, N, S1, N1):
    """D1 trades against the same session's other trades: Σ_s N1(s)·[mean D1(s) − mean non-D1(s)] / Σ N1(s), over the
    sessions holding both"""
    s1, n1 = S1.sum(1), N1.sum(1)
    s0, n0 = S.sum(1) - s1, N.sum(1) - n1
    ok = (n1 > 0) & (n0 > 0)
    d = np.where(ok, s1 / np.where(n1 > 0, n1, 1) - s0 / np.where(n0 > 0, n0, 1), 0.0)
    num = W @ (np.where(ok, n1, 0) * d)
    den = W @ np.where(ok, n1, 0)
    return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan), int(ok.sum())


def d1_block(tr: list, days: list, minutes: tuple, col: str = 'pnl_nbbo', dcol: str = 'd1') -> dict:
    n = len(days)
    out = {'sessions': n}
    if n == 0:
        return out
    for unit, pct in (('usd', False), ('pct', True)):
        S, N, S1, N1 = lift_mats(tr, days, minutes, col, pct, dcol)
        one = np.ones((1, n))
        lt = float(lift_time(one, S, N, S1, N1)[0])
        ls, ns = lift_session(one, S, N, S1, N1)
        out[f'time_{unit}'] = lt
        out[f'sess_{unit}'] = float(ls[0])
        out['sessions_both'] = ns
        out['d1_trades'] = int(N1.sum())
        out['d1_sessions'] = int((N1.sum(1) > 0).sum())
        out['all_trades'] = int(N.sum())
        if unit == 'usd':
            out['d1_mean'] = float(S1.sum() / N1.sum()) if N1.sum() else float('nan')
            out['all_mean'] = float(S.sum() / N.sum()) if N.sum() else float('nan')
            out['rest_mean'] = float((S.sum() - S1.sum()) / (N.sum() - N1.sum())) if N.sum() > N1.sum() else float('nan')
        for b in (1, 5, 20):
            if n < 3 * b:
                out[f'time_{unit}_ci_b{b}'] = out[f'sess_{unit}_ci_b{b}'] = (float('nan'), float('nan'))
                continue
            W = A.weights_from(A.block_draws(n, b), n)
            out[f'time_{unit}_ci_b{b}'] = A.pct_ci(lift_time(W, S, N, S1, N1))
            out[f'sess_{unit}_ci_b{b}'] = A.pct_ci(lift_session(W, S, N, S1, N1)[0])
    return out


# ---- the replay report's CI, re-derived ---------------------------------------------------------------------------------------------

def report_ci(values: np.ndarray, days: np.ndarray, n: int = 2000, seed: int = 20261016) -> tuple[float, float]:
    """paper_backtest.session_boot, written again: the sessions holding a trade resampled with replacement (2,000 draws,
    numpy default_rng(20261016)), the statistic the trade-weighted mean of the drawn sessions' trades (Σ sums / Σ counts),
    the 2.5th and 97.5th percentiles"""
    ud, inv = np.unique(days, return_inverse=True)
    sums = np.bincount(inv, weights=values, minlength=ud.size)
    cnts = np.bincount(inv, minlength=ud.size).astype(float)
    rng = np.random.default_rng(seed)
    draw = rng.integers(0, ud.size, (n, ud.size))
    means = sums[draw].sum(1) / np.maximum(cnts[draw].sum(1), 1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# ---- the reports ---------------------------------------------------------------------------------------------------------------------

def md_table(head: list, rows: list) -> list:
    return ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows]


def pct(x, d=1):
    return '—' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{100 * x:.{d}f}%'


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--root', default=str(A.REPO / 'data_recorder' / 'paper_backtest'))
    p.add_argument('--parquet-root', default=os.environ.get('PAPER_PARQUET_ROOT'))
    p.add_argument('--through', default='2026-10-21')
    p.add_argument('--rerun-root')
    p.add_argument('--rerun-csv')
    p.add_argument('--skip-entries', action='store_true', help='reuse out/entries.json')
    p.add_argument('--out-dir', help='write the reports and out/ here instead of this folder (a trial run)')
    a = p.parse_args(argv)
    t0 = time.time()
    root = Path(a.root).resolve()
    pr = Path(a.parquet_root) if a.parquet_root else None
    out = Path(a.out_dir) / 'out' if a.out_dir else A.OUT
    report_dir = Path(a.out_dir) if a.out_dir else A.HERE
    out.mkdir(parents=True, exist_ok=True)
    df = A.load_rows(root, end=a.through)
    days_all = [d for d in replayed_days(root) if d <= a.through]
    hist_days = [d for d in days_all if d <= A.HIST_END]
    fwd_days = [d for d in days_all if d >= A.FORWARD_START]

    # 1. integrity, determinism, entries
    integ = CI.integrity(root, A.HIST_START, A.HIST_END)
    (out / 'integrity.json').write_text(json.dumps(integ, indent=1, default=str), encoding='utf-8')
    if a.rerun_root:
        det = CI.determinism(root, Path(a.rerun_root), REPORT_CSV, Path(a.rerun_csv) if a.rerun_csv else None)
        det.update({'root_a': str(root), 'root_b': str(a.rerun_root), 'at': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')})
        (out / 'determinism.json').write_text(json.dumps(det, indent=1, default=str), encoding='utf-8')
    det = json.loads((out / 'determinism.json').read_text()) if (out / 'determinism.json').exists() else None
    if a.skip_entries and (out / 'entries.json').exists():
        ent = json.loads((out / 'entries.json').read_text())
    elif pr is not None:
        ent = CE.check(root, pr)
        (out / 'entries.json').write_text(json.dumps(ent, indent=1, default=str), encoding='utf-8')
    else:
        ent = None

    # the trades
    tr, oc = build_trades(df, pr, out)
    TR = [t for t in tr if t.get('settled')]
    H = [t for t in TR if t['day'] <= A.HIST_END]
    F = [t for t in TR if t['day'] >= A.FORWARD_START]

    # 2. settlement
    closes = oc['closes']
    sess = {}
    for t in TR:
        sess.setdefault((t['name'], t['day']), t['settle_1559'])
    srows = []
    for (nm, d), c59 in sorted(sess.items()):
        r = closes.filter((pl.col('symbol') == nm) & (pl.col('day') == d))
        th = r['close_theta'][0] if r.height else None
        uw = r['close_uw'][0] if r.height else None
        srows.append({'name': nm, 'day': d, 'close_1559': c59, 'close_theta': th, 'close_uw': uw,
                      'official': oc['official'].get((nm, d)), 'src': oc['official_src'].get((nm, d))})
    sdf = pl.DataFrame(srows, infer_schema_length=None)
    sdf = sdf.with_columns((pl.col('official') - pl.col('close_1559')).alias('off_minus_1559'), (pl.col('close_theta') - pl.col('close_uw')).alias('theta_minus_uw'))
    xs = {(t['name'], t['day']) for t in TR if t['cross']}
    sdf = sdf.with_columns(pl.struct('name', 'day').map_elements(lambda r: (r['name'], r['day']) in xs, return_dtype=pl.Boolean).alias('a_leg_strike_crossed'))
    sdf.write_csv(out / 'settlement_sessions.csv')

    def settle_summary(rows):
        o = {}
        for nm in ('SPY', 'QQQ'):
            s = rows.filter(pl.col('name') == nm)
            dd = s['off_minus_1559'].drop_nulls().to_numpy()
            both = s.filter(pl.col('close_theta').is_not_null() & pl.col('close_uw').is_not_null())
            dis = both.filter((pl.col('theta_minus_uw').abs() > 0.005))
            o[nm] = {'sessions': s.height, 'official': int(s['official'].is_not_null().sum()), 'src': dict(Counter(s['src'].to_list())),
                     'both_theta_uw': both.height, 'theta_uw_disagree': dis.height,
                     'theta_uw_disagree_rows': dis.select('day', 'close_theta', 'close_uw').to_dicts(),
                     'mean_abs': float(np.mean(np.abs(dd))) if dd.size else float('nan'), 'median_abs': float(np.median(np.abs(dd))) if dd.size else float('nan'),
                     'p95_abs': float(np.percentile(np.abs(dd), 95)) if dd.size else float('nan'), 'max_abs': float(np.max(np.abs(dd))) if dd.size else float('nan'),
                     'max_day': s.sort(pl.col('off_minus_1559').abs(), descending=True, nulls_last=True)['day'][0] if dd.size else None,
                     'equal': int((np.abs(dd) < 0.005).sum()), 'over_5c': int((np.abs(dd) > 0.05).sum()), 'over_25c': int((np.abs(dd) > 0.25).sum()),
                     'sessions_crossing': int(s['a_leg_strike_crossed'].sum())}
        return o
    ss_h = settle_summary(sdf.filter(pl.col('day') <= A.HIST_END))

    def recon(trs):
        rows = []
        for k in A.KEYS:
            for s in A.STRUCTS[k]:
                x = [t for t in trs if t['key'] == k and t['structure'] == s]
                if not x:
                    continue
                dl = np.array([t['delta_off'] for t in x])
                ch = np.abs(dl) > 0.005
                rows.append({'key': k, 'structure': s, 'trades': len(x), 'changed': int(ch.sum()), 'better': int((dl > 0.005).sum()), 'worse': int((dl < -0.005).sum()),
                             'mean_change_changed': float(dl[ch].mean()) if ch.any() else 0.0, 'max_abs_change': float(np.abs(dl).max()),
                             'total_1559': float(sum(t['pnl_nbbo_r'] for t in x)), 'total_official': float(sum(t['pnl_nbbo'] for t in x)),
                             'mean_1559': float(np.mean([t['pnl_nbbo_r'] for t in x])), 'mean_official': float(np.mean([t['pnl_nbbo'] for t in x])),
                             'cross_trades': int(sum(t['cross'] for t in x)), 'itm_changes': int(sum(t['itm_changes'] for t in x)),
                             'no_official': int(sum(t['official'] is None for t in x)), 'payoff_check_fail': int(sum(not t['payoff_check'] for t in x))})
        return rows
    rec_h = recon(H)

    # the expiry check against Theta's flat option_eod (2026-10-06 → 09): the chain file's strikes = the same-day listing
    exp_chk = []
    if pr is not None:
        for d in ('2026-10-06', '2026-10-07', '2026-10-08', '2026-10-09'):
            fe = A.REPO / 'data_lake' / 'thetadata' / 'flat' / 'option_eod' / f'{d}.parquet'
            for nm in ('SPY', 'QQQ'):
                fc = pr / 'data_full' / 'chains' / nm / f'{d}.parquet'
                if not (fe.exists() and fc.exists()):
                    continue
                e = pl.scan_parquet(fe).filter((pl.col('root') == nm) & (pl.col('expiration') == int(d.replace('-', '')))).select('strike', 'right').collect()
                es = {(r[0].upper(), float(k)) for k, r in e.iter_rows()}
                c = pl.scan_parquet(fc).select('strike', 'right').unique().collect()
                cs = {(r[0].upper(), float(k)) for k, r in c.iter_rows()}
                exp_chk.append({'day': d, 'name': nm, 'eod_same_day_contracts': len(es), 'chain_file_contracts': len(cs), 'in_both': len(es & cs),
                                'only_chain_file': len(cs - es), 'only_eod': len(es - cs)})

    # 3/4/7. CI method check, risk, inference by period
    rep = pl.read_csv(REPORT_CSV, infer_schema_length=None) if REPORT_CSV.exists() else None
    ci_check = []
    for k in A.KEYS:
        for s in A.STRUCTS[k]:
            x = [t for t in H if t['key'] == k and t['structure'] == s]
            lo, hi = report_ci(np.array([t['pnl_nbbo_r'] for t in x]), np.array([t['day'] for t in x]))
            rr = rep.filter((pl.col('section') == 'cell') & (pl.col('candidate') == k) & (pl.col('structure') == s) & (pl.col('cut') == 'all')) if rep is not None else None
            ci_check.append({'key': k, 'structure': s, 'ours': (lo, hi), 'report': (float(rr['ci_lo_nbbo'][0]), float(rr['ci_hi_nbbo'][0])) if rr is not None and rr.height else None})

    risk = []
    for k in A.KEYS:
        for pcode, plabel, pa, pb in A.PERIODS[k]:
            days = sessions_of(days_all, k, pcode)
            for s in A.STRUCTS[k]:
                x = [t for t in TR if t['key'] == k and t['structure'] == s]
                row = {'key': k, 'structure': s, 'period': pcode, 'label': plabel, 'from': pa, 'to': pb or a.through}
                for col in ('pnl_nbbo', 'pnl_1c', 'pnl_2c', 'pnl_mid', 'pnl_nbbo_r', 'pnl_1558', 'pnl_1558_1c', 'pnl_1558_2c', 'pnl_1558_mid'):
                    row[col] = risk_row(x, days, col)
                xs_ = [t for t in x if t['day'] in set(days)]
                row['width_mean'] = float(np.mean([t['width'] for t in xs_]) * 100) if xs_ else float('nan')
                row['width_median'] = float(np.median([t['width'] for t in xs_]) * 100) if xs_ else float('nan')
                row['slip_mean'] = float(np.mean([abs(t['price_nbbo'] - t['price_mid']) for t in xs_]) * 100) if xs_ else float('nan')
                risk.append(row)
    flat = []
    for r in risk:
        for col in ('pnl_nbbo', 'pnl_1c', 'pnl_2c', 'pnl_mid', 'pnl_nbbo_r', 'pnl_1558', 'pnl_1558_1c', 'pnl_1558_2c', 'pnl_1558_mid'):
            v = r[col]
            flat.append({'candidate': r['key'], 'structure': r['structure'], 'period': r['period'], 'from': r['from'], 'to': r['to'], 'pnl': col,
                         **{kk: (json.dumps(vv) if isinstance(vv, (list, tuple)) else vv) for kk, vv in v.items()}})
    pl.DataFrame(flat, infer_schema_length=None).write_csv(out / 'risk_by_period.csv')

    # 6. D1
    d20 = [t for t in TR if t['key'] == 'condor_d20']
    evfilters = [('all sessions', lambda d: True), ('without any scheduled-event session (FOMC decision, FOMC minutes, CPI, NFP)', lambda d: not oc_ev(d)),
                 ('without FOMC decision days only', lambda d: 'FOMC_DECISION' not in oc_ev(d)), ('scheduled-event sessions only', lambda d: bool(oc_ev(d)))]
    macro = A.macro_days()

    def oc_ev(d):
        return {e for e in macro.get(d, set()) if e in EVENTS}
    lifts = []
    plist = [(pc, pl_) for pc, pl_, _, _ in A.PERIODS['condor_d20']] + [('hist-pooled', 'ALL 2022-11-11 → 2026-10-09 pooled — for reconciliation with the replay report only, not a headline')]
    for pcode, plabel in plist:
        base = [d for d in days_all if d <= A.HIST_END] if pcode == 'hist-pooled' else sessions_of(days_all, 'condor_d20', pcode)
        for evn, evf in evfilters:
            days = [d for d in base if evf(d)]
            for col in ('pnl_nbbo', 'pnl_nbbo_r'):
                if col == 'pnl_nbbo_r' and evn != 'all sessions':
                    continue
                r = d1_block(d20, days, A.MINUTES['condor_d20'], col)
                lifts.append({'period': pcode, 'label': plabel, 'events': evn, 'settle': 'official' if col == 'pnl_nbbo' else '15:59 bar (replay)', **r})
    pl.DataFrame([{k: (json.dumps(v) if isinstance(v, (list, tuple)) else v) for k, v in r.items()} for r in lifts], infer_schema_length=None).write_csv(out / 'd1_lift.csv')
    ev_counts = {pc: {'sessions': len(sessions_of(hist_days, 'condor_d20', pc)), 'event_sessions': sum(1 for d in sessions_of(hist_days, 'condor_d20', pc) if oc_ev(d)),
                      'fomc_decision': sum(1 for d in sessions_of(hist_days, 'condor_d20', pc) if 'FOMC_DECISION' in oc_ev(d))} for pc, _, _, _ in A.PERIODS['condor_d20']}

    # 8. expiration mechanics
    expi = []
    for k in A.KEYS:
        for s in A.STRUCTS[k]:
            for pcode, plabel, _, _ in A.PERIODS[k]:
                x = [t for t in TR if t['key'] == k and t['structure'] == s and t['period'] == pcode]
                if not x:
                    continue
                n = len(x)
                ns = [t for t in x if t['net_shares'] != 0]
                expi.append({'key': k, 'structure': s, 'period': pcode, 'trades': n,
                             'any_itm': sum(t['any_itm'] for t in x) / n, 'short_itm': sum(t['short_itm'] > 0 for t in x) / n,
                             'long_itm': sum(t['long_itm'] > 0 for t in x) / n,
                             'net_stock': len(ns) / n, 'net_long': sum(t['net_shares'] > 0 for t in x) / n, 'net_short': sum(t['net_shares'] < 0 for t in x) / n,
                             'offset_pair': sum(t['short_itm'] > 0 and t['net_shares'] == 0 for t in x) / n,
                             'net_stock_value_mean': float(np.mean([t['net_stock_value'] for t in ns])) if ns else 0.0,
                             'net_stock_value_max': float(np.max([t['net_stock_value'] for t in ns])) if ns else 0.0,
                             'assign_notional_mean_when': float(np.mean([t['assign_notional'] for t in x if t['short_itm']])) if any(t['short_itm'] for t in x) else 0.0,
                             'max_risk_mean': float(np.mean([t['risk_usd'] for t in x])),
                             'pin25': sum(t['pin_dist'] <= 0.25 for t in x) / n, 'pin50': sum(t['pin_dist'] <= 0.50 for t in x) / n,
                             'pin01': sum(t['pin_dist'] <= 0.01 for t in x) / n,
                             'itm_changes': sum(t['itm_changes'] for t in x) / n,
                             'hold_mean': float(np.mean([t['pnl_nbbo'] for t in x])),
                             'exit_n': sum(t.get('pnl_1558') is not None for t in x),
                             'exit_mean': float(np.mean([t['pnl_1558'] for t in x if t.get('pnl_1558') is not None])) if any(t.get('pnl_1558') is not None for t in x) else float('nan'),
                             'exit_mid_mean': float(np.mean([t['pnl_1558_mid'] for t in x if t.get('pnl_1558_mid') is not None])) if any(t.get('pnl_1558_mid') is not None for t in x) else float('nan'),
                             'exit_fees_mean': float(np.mean([A.FEE * (A.CONTRACTS + t['closed_1558']) for t in x if t.get('closed_1558') is not None])) if any(t.get('closed_1558') is not None for t in x) else float('nan'),
                             **{f'part{b}_mean': (float(np.mean([t[f'pnl_part{b}'] for t in x if t.get(f'pnl_part{b}') is not None])) if any(t.get(f'pnl_part{b}') is not None for t in x) else float('nan')) for b in (0.5, 1.0)},
                             **{f'part{b}_resid': (float(np.mean([t[f'resid_itm{b}'] for t in x if t.get(f'pnl_part{b}') is not None])) if any(t.get(f'pnl_part{b}') is not None for t in x) else float('nan')) for b in (0.5, 1.0)},
                             'odd_strikes': sum(any(abs(k * 2 - round(k * 2)) > 1e-6 for _, k, _, _ in t['legs']) for t in x)})
    pl.DataFrame(expi).write_csv(out / 'expiration_mechanics.csv')
    # our 15:58 exit against the replay's (fly5 only)
    ex_chk = [(t['pnl_1558'], t['pnl_1558_r']) for t in H if t['key'] == 'fly5' and t.get('pnl_1558') is not None and t.get('pnl_1558_r') is not None]
    ex_diff = int(sum(abs(x - y) > 0.005 for x, y in ex_chk))
    ex_missing = sum(1 for t in H if t['key'] == 'fly5' and (t.get('pnl_1558') is None) != (t.get('pnl_1558_r') is None))
    # the after-hours window (UW's post-market bar, 2025-10-13 onward): could it cross a short strike?
    po = pl.concat([pl.scan_parquet(fp).filter(pl.col('ticker').is_in(['SPY', 'QQQ']) & (pl.col('market_time') == 'po')).collect()
                    for fp in sorted((A.REPO / 'data_lake' / 'unusualwhales').glob('ohlc__1d.part0*.parquet'))])
    POR = {(r['ticker'], r['date']): (float(r['low']), float(r['high'])) for r in po.to_dicts()}
    ah = []
    for k in A.KEYS:
        for s in A.STRUCTS[k]:
            x = [t for t in H if t['key'] == k and t['structure'] == s and (t['name'], t['day']) in POR and t['official'] is not None]
            if not x:
                continue
            hit = 0
            for t in x:
                lo, hi = POR[(t['name'], t['day'])]
                lo, hi = min(lo, t['official']), max(hi, t['official'])
                if any(lo <= kk <= hi and (A.intrinsic(lo, kk, r) >= 0.005) != (A.intrinsic(hi, kk, r) >= 0.005) for r, kk, side, q in t['legs'] if side == 'short'):
                    hit += 1
            ah.append({'key': k, 'structure': s, 'trades': len(x), 'sessions': len({t['day'] for t in x}), 'short_strike_in_after_hours_range': hit / len(x)})

    # SPXW inventory
    spxw = {}
    if pr is not None:
        ch = sorted((pr / 'data_full' / 'chains' / 'SPXW').glob('*.parquet'))
        ix = sorted((pr / 'data' / 'index' / 'SPX').glob('*.parquet'))
        spxw = {'spxw_chain_files': len(ch), 'spxw_first': ch[0].stem if ch else None, 'spxw_last': ch[-1].stem if ch else None,
                'spx_print_files': len(ix), 'spx_first': ix[0].stem if ix else None, 'spx_last': ix[-1].stem if ix else None}
    flat_ix = sorted((A.REPO / 'data_lake' / 'thetadata' / 'flat' / 'index_eod').glob('*.parquet'))
    spxw['index_eod_flat_days'] = [x.stem for x in flat_ix]

    # session P&L correlation across the candidate-structures (shared sessions, overlapping minutes)
    corr = {}
    for pname, plo, phi in (('2022-11-11 → 2024-12-31', '2022-11-11', '2024-12-31'), ('2025-01-02 → 2026-10-09', '2025-01-02', A.HIST_END)):
        dd = [d for d in hist_days if plo <= d <= phi]
        labs, mat = [], []
        for k in A.KEYS:
            for st_ in A.STRUCTS[k]:
                S_, _ = series([t for t in H if t['key'] == k and t['structure'] == st_], dd)
                labs.append(f'{k} {st_}')
                mat.append(S_)
        corr[pname] = {'labels': labs, 'corr': np.corrcoef(np.array(mat)).round(3).tolist()}

    # forward bookkeeping
    fwd = forward_counts(root, pr, df, a.through, oc)

    state = dict(integ=integ, det=det, ent=ent, ss_h=ss_h, rec_h=rec_h, exp_chk=exp_chk, ci_check=ci_check, risk=risk, lifts=lifts, ev_counts=ev_counts,
                 expi=expi, corr=corr, ex_diff=ex_diff, ex_n=len(ex_chk), ex_missing=ex_missing, ah=ah, spxw=spxw, fwd=fwd, through=a.through, root=str(root),
                 pr=str(pr) if pr else None, seconds=time.time() - t0, H=H, F=F, sdf=sdf, out_dir=str(out), report_dir=str(report_dir))
    import write_reports as WR
    WR.write_all(state)
    print(f'audit written in {time.time() - t0:.0f} s')
    return 0


def forward_counts(root: Path, pr: Path | None, df: pl.DataFrame, through: str, oc: dict) -> dict:
    exp = A.expected_sessions(A.FORWARD_START, through) if through >= A.FORWARD_START else []
    days = {d: v for d, v in CI.read_days(root).items() if A.FORWARD_START <= d <= through}
    out = {'expected': exp, 'n_expected': len(exp)}

    def have(d):
        if pr is None:
            return False
        need = [pr / 'data_full' / 'chains' / s / f'{d}.parquet' for s in ('SPY', 'QQQ')] + [pr / 'data' / 'underlying' / s / f'{d}.parquet' for s in ('SPY', 'QQQ')]
        return all(x.exists() for x in need)
    fetched = [d for d in exp if have(d)]
    out['fetched'] = fetched
    out['missing'] = [d for d in exp if d not in fetched]
    out['vix_missing'] = [d for d in fetched if pr is not None and not (pr / 'data' / 'index' / 'VIX' / f'{d}.parquet').exists()]
    out['status'] = {d: v['status'] for d, v in days.items()}
    out['excluded'] = {d: v['status'] for d, v in days.items() if v['status'] != 'replayed'}
    f_ = df.filter(pl.col('_day') >= A.FORWARD_START) if df.height else df
    per = {}
    for k in A.KEYS:
        if f_.height == 0:
            per[k] = {'complete': [], 'settled_sessions': [], 'valid': 0, 'invalid': 0, 'unmatched': 0, 'official_missing': []}
            continue
        c = f_.filter((pl.col('candidate') == k) & (pl.col('row_kind') == 'capture'))
        s = f_.filter((pl.col('candidate') == k) & (pl.col('row_kind') == 'settle'))
        want = len(A.MINUTES[k]) * len(A.STRUCTS[k]) * len(A.NAMES[k])
        g = c.group_by('_day').len()
        complete = sorted(r['_day'] for r in g.to_dicts() if r['len'] == want)
        k5 = ['_name', '_day', 'minute', 'structure']
        withlegs = c.filter(pl.col('l1_symbol').is_not_null())
        unmatched = withlegs.select(k5).join(s.select(k5), on=k5, how='anti').height + s.select(k5).join(c.select(k5), on=k5, how='anti').height
        per[k] = {'complete': complete, 'settled_sessions': sorted(set(s['_day'].to_list())),
                  'valid': s.filter(pl.col('tradable') == 'true').height, 'invalid': c.filter(pl.col('tradable') != 'true').height, 'unmatched': unmatched,
                  'official_missing': sorted({d for d in s['_day'].to_list() for nm in A.NAMES[k] if (nm, d) not in oc['official']})}
    out['per'] = per
    return out


if __name__ == '__main__':
    sys.exit(main())
