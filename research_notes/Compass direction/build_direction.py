#!/usr/bin/env python3
"""
build_direction.py — the trades and the comparison of PREREG_DIRECTION.md (commit 38b11bf), from the stored files only.

    POLARS_MAX_THREADS=4 python3 -I build_direction.py expl     # the exploration screen  → out/screen.json, out/expl_trades.parquet
    POLARS_MAX_THREADS=4 python3 -I build_direction.py hold     # the single holdout test → out/holdout.json (refused before a pass)

Per event (§4): R, P, E1, the exit X; the earnings-day return g = close(R)/close(P) − 1 and its sign; the $50 M floor; the
split rule over P..X; E1's chain → the 31–60 expiry nearest 45 → K*, F, IM; the parity check |F/close(E1) − 1| ≤ 5 %; five
strike buckets a side at the closing ask; the closing bid 10 full sessions later (no bid → $0, no fee; no row → not formed);
fees $0.68748 a side. The comparison (§5): with = the picked side's trades, without = both sides' trades at the same events;
per entry session sums; Δ; the 20-session moving-block bootstrap of audit_lib (2,000 draws); effective N.
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dcommon as C  # noqa: E402

AL = C.AL


# ---- the trades --------------------------------------------------------------------------------------------------------------------

def bars_name(t: str, day: str) -> str:
    """the on-disk rule: UW files Facebook's reports under META; before 2022-06-09 its bars and chains are FB's"""
    return 'FB' if (t == 'META' and day <= '2022-06-08') else t


def build_event(ev: dict, bars: dict, disk: bool, lo: str, hi: str, cnt: Counter, tier_cache: dict) -> list[dict]:
    t = ev['ticker']
    d = C.event_dates(ev['report_date'], ev['report_time'])
    if d['status'] != 'ok':
        cnt[d['status']] += 1
        return []
    R, P, E1, X = d['R'], d['P'], d['E1'], d['X']
    if X is None or E1 < lo or X > hi:
        cnt['outside the set window'] += 1
        return []
    sym = bars_name(t, P) if disk else t
    if disk:
        root = C.disk_root(t, E1)
        a, b = C.DISK_SPAN[root]
        if not (a <= E1 and X <= b) or C.disk_root(t, X) != root:
            cnt['outside the stored option EOD span'] += 1
            return []
    B = bars.get(sym)
    if B is None or B.c(P) is None or B.c(R) is None:
        cnt['no bar for P or R'] += 1
        return []
    okl, med, _ = B.liquid(P)
    if not okl:
        cnt['under the $50 M floor' if med is not None else 'under 50 of 60 days of bars'] += 1
        return []
    g = B.c(R) / B.c(P) - 1.0
    if g == 0:
        cnt['g = 0: undefined'] += 1
        return []
    sp = B.split_between(P, X)
    if sp:
        cnt['a split-sized close-to-close move in P..X'] += 1
        return []
    ch = C.chain(t, E1, disk=disk) if disk else C.chain(t, E1)
    if ch is None:
        cnt['no entry chain'] += 1
        return []
    exp = C.choose_expiry(E1, ch['expiration'].unique().to_list())
    if exp is None:
        cnt['no listed 31-60 expiry'] += 1
        return []
    le = C.last_trading_day(exp)
    if le in C.HALF_DAYS:
        cnt['expiry on a half day'] += 1
        return []
    K, cb, ca, pb, pa = C.grid(ch.filter(pl.col('expiration') == exp))
    fim = C.forward_im(K, cb, ca, pb, pa)
    if fim is None:
        cnt['no standing ATM pair'] += 1
        return []
    Ks, F, IM = fim
    cE1 = B.c(E1) if not disk else (bars.get(bars_name(t, E1)).c(E1) if bars.get(bars_name(t, E1)) else None)
    if cE1 is None:
        cnt['no bar at E1'] += 1
        return []
    if abs(F / cE1 - 1) > C.PARITY_TOL:
        cnt['bars and options disagree (parity > 5 %)'] += 1
        return []
    xc = C.chain(t, X, exp, disk=disk) if disk else C.chain(t, X, exp)
    exitq = {}
    if xc is not None:
        for r in xc.select('strike', 'right', 'bid', 'ask').iter_rows():
            exitq[(round(r[0], 4), r[1])] = (r[2], r[3])
    # the tier of (name, month of E1)
    tk = (t, E1[:7])
    if tk not in tier_cache:
        td = C.tier_days(E1)
        rows = []
        if td:
            for day in td:
                x = C.chain(t, day, disk=disk) if disk else C.chain(t, day)
                if x is None:
                    rows = None
                    break
                rows.append(x)
        if rows:
            v, s_ = C.tier_measure(rows)
            tier_cache[tk] = (C.tier_of(v, s_), v, s_)
        else:
            tier_cache[tk] = ('U', None, None)
    tier, tv, ts = tier_cache[tk]
    side = 'C' if g > 0 else 'P'
    out = []
    for right, b_, a_ in (('C', cb, ca), ('P', pb, pa)):
        st = (b_ > 0) & (a_ > 0) & (a_ >= b_)
        xx = (K - F) / IM if right == 'C' else (F - K) / IM
        sel = C.select_buckets(K, st, xx)
        for bn in C.BUCKET_NAMES:
            if bn not in sel:
                cnt['trade: no standing quote in the bucket'] += 1
                continue
            i = sel[bn]
            ask, bid = float(a_[i]), float(b_[i])
            q = exitq.get((round(float(K[i]), 4), right))
            if q is None:
                cnt['trade: no EOD row at the exit'] += 1
                continue
            xb, xa = q
            px = float(xb) if (xb is not None and xb > 0 and xa is not None and xa > 0 and xa >= xb) else 0.0
            r_, pnl = C.ret(ask, px)
            out.append(dict(ticker=t, report_date=ev['report_date'], report_time=ev['report_time'], R=R, P=P, day=E1, exit_day=X,
                            g=g, pick=side, right=right, picked=(right == side), sb=bn, expiry=exp, strike=float(K[i]), x=float(xx[i]),
                            F=F, IM=IM, Kstar=Ks, S=cE1, bid=bid, ask=ask, spread=(ask - bid) / ((ask + bid) / 2), exit_px=px,
                            exit_zero=px <= 0, r=r_, pnl=pnl, tier=tier, tier_vol=tv, tier_spread=ts, disk=disk, liq=med))
    if out:
        cnt['events with trades'] += 1
    else:
        cnt['events with no trade'] += 1
    return out


def build(split: str) -> tuple[pl.DataFrame, dict]:
    store_ev = C.STORE / f'_events_{split}.ndjson'
    fetched = []
    stages = Counter()
    if store_ev.exists():
        for line in store_ev.read_text().splitlines():
            r = json.loads(line)
            stages[r['stage']] += 1
            if r['stage'] == 'fetched':
                fetched.append(dict(ticker=r['ticker'], report_date=r['report_date'], report_time=r['report_time']))
    evl = C.event_lists()
    disk_ev = evl['disk'] if split == 'expl' else []
    names = sorted({e['ticker'] for e in fetched} | {e['ticker'] for e in disk_ev} | ({'FB'} if disk_ev else set()))
    bars = {s: C.Bars(df) for s, df in C.load_bars(names).items()}
    lo, hi = (C.HOLD_FROM, '2022-12-30') if split == 'hold' else (C.EXPL_FROM, C.EXPL_LAST)
    cnt_f, cnt_d = Counter(), Counter()
    tier_cache = {}
    rows = []
    for e in fetched:
        rows += build_event(e, bars, False, lo, hi, cnt_f, tier_cache)
    for e in disk_ev:
        rows += build_event(e, bars, True, '2015-03-02', C.EXPL_LAST, cnt_d, tier_cache)
    df = pl.DataFrame(rows, infer_schema_length=None) if rows else pl.DataFrame()
    info = dict(fetch_stages=dict(stages), fetched_events=len(fetched), build_counts_fetched=dict(cnt_f),
                disk_events=len(disk_ev), build_counts_disk=dict(cnt_d))
    return df, info


# ---- the statistic (PREREG_FEATURES §6 / stats.py at e5dd8c6) ------------------------------------------------------------------------

_W = {}


def W(n, block):
    if (n, block) not in _W:
        _W[(n, block)] = AL.weights_from(AL.block_draws(n, block), n)
    return _W[(n, block)]


def per_session(df: pl.DataFrame, sessions: list[str]):
    idx = {d: i for i, d in enumerate(sessions)}
    S, N = np.zeros(len(sessions)), np.zeros(len(sessions))
    if df.height:
        for d, s, k in df.group_by('day').agg(pl.col('r').sum(), pl.len()).iter_rows():
            if d not in idx:
                raise RuntimeError(f'entry {d} outside the session list')
            S[idx[d]] += s
            N[idx[d]] += k
    return S, N


def clean(d):
    o = {}
    for k, v in d.items():
        if isinstance(v, tuple):
            o[k] = [None if not math.isfinite(x) else x for x in v]
        elif isinstance(v, float) and not math.isfinite(v):
            o[k] = None
        else:
            o[k] = v
    return o


def delta(w: pl.DataFrame, o: pl.DataFrame, sessions: list[str], full=True) -> dict:
    n = len(sessions)
    Sw, Nw = per_session(w, sessions)
    So, No = per_session(o, sessions)
    out = dict(sessions=n, first=sessions[0], last=sessions[-1], trades_with=int(Nw.sum()), trades_without=int(No.sum()),
               sessions_with=int((Nw > 0).sum()), sessions_without=int((No > 0).sum()),
               events=int(o.select('ticker', 'report_date').n_unique()) if o.height else 0)
    if Nw.sum() == 0 or No.sum() == 0:
        out.update(delta=None, ci=[None, None])
        return out
    mw, mo = Sw.sum() / Nw.sum(), So.sum() / No.sum()
    out.update(mean_with=float(mw), mean_without=float(mo), delta=float(mw - mo))
    if n < 60:
        out.update(ci=[None, None], note='under 60 sessions: no interval')
        return out

    def boot(block):
        Wb = W(n, block)
        with np.errstate(divide='ignore', invalid='ignore'):
            return (Wb @ Sw) / (Wb @ Nw) - (Wb @ So) / (Wb @ No)
    d20 = boot(20)
    out['ci'] = list(AL.pct_ci(d20))
    if full:
        d1 = boot(1)
        v1, v20 = np.nanvar(d1[np.isfinite(d1)]), np.nanvar(d20[np.isfinite(d20)])
        out['n_eff_block20'] = float(n * v1 / v20) if v20 > 0 else None
        ok = No > 0
        diff = Sw[ok] - (Nw[ok] / No[ok]) * So[ok]
        out['n_eff_acf'] = clean(AL.session_stats(diff, np.ones(diff.size), blocks=())).get('n_eff_acf')
        out['arm_with'] = clean(AL.session_stats(Sw, Nw))
        out['arm_without'] = clean(AL.session_stats(So, No))
    return out


def passes(res) -> bool:
    c = res.get('ci') or [None]
    return bool(res.get('delta') is not None and res['delta'] > 0 and c[0] is not None and c[0] > 0)


def arms(df: pl.DataFrame):
    return df.filter(pl.col('picked')), df


def analyse(df: pl.DataFrame, sessions: list[str]) -> dict:
    w, o = arms(df)
    res = dict(main=delta(w, o, sessions))
    res['pass'] = passes(res['main'])
    desc = {}
    for col in ('tier', 'sb', 'report_time'):
        for (k,), g in df.group_by([col]):
            ww, oo = arms(g)
            desc[f'{col}={k}'] = delta(ww, oo, sessions, full=False)
    desc['settlement=physical'] = delta(w, o, sessions, full=False)
    for side in ('C', 'P'):
        g = df.filter(pl.col('pick') == side)
        ww, oo = arms(g)
        desc[f'pick={side}'] = delta(ww, oo, sessions, full=False)
    for (y,), g in df.with_columns(pl.col('day').str.slice(0, 4).alias('year')).group_by(['year']):
        ww, oo = arms(g)
        desc[f'year={y}'] = delta(ww, oo, sessions, full=False)
    res['descriptive'] = dict(sorted(desc.items()))
    # the absolute mean per trade of each arm, and the picked vs the other side
    res['absolute'] = dict(picked_mean=float(w['r'].mean()) if w.height else None,
                           other_side_mean=float(df.filter(~pl.col('picked'))['r'].mean()) if df.height else None,
                           all_mean=float(df['r'].mean()) if df.height else None,
                           exit_at_zero_share=float(df['exit_zero'].mean()) if df.height else None)
    return res


def main(split: str):
    C.OUT.mkdir(parents=True, exist_ok=True)
    if split == 'hold':
        sc = json.loads((C.OUT / 'screen.json').read_text())
        if not sc.get('screen_pass'):
            raise SystemExit('the screen did not pass: the holdout is not read')
        if (C.OUT / 'holdout.json').exists():
            raise SystemExit('the holdout has been read once already (out/holdout.json)')
    df, info = build(split)
    if df.height == 0:
        C.jdump(dict(split=split, info=info, note='no trades'), C.OUT / ('screen.json' if split == 'expl' else 'holdout.json'))
        print('no trades', info)
        return
    C.WORK.mkdir(parents=True, exist_ok=True)
    df.write_parquet(C.WORK / f'{split}_trades.parquet', compression='zstd')
    if split == 'hold':
        sessions = C.sessions_in(C.HOLD_FROM, '2022-12-30')
    else:
        sessions = C.sessions_in(df['day'].min(), df['day'].max())
    res = analyse(df, sessions)
    out = dict(split=split, prereg=C.PREREG_COMMIT, info=info, trades=df.height,
               events=int(df.select('ticker', 'report_date').n_unique()), names=int(df['ticker'].n_unique()), **res)
    if split == 'expl':
        parts = {}
        for lab, g in (('X before 2023 (unopened cells)', df.filter(~pl.col('disk') & (pl.col('day') < '2023-01-01'))),
                       ('X from 2023 (opened cells)', df.filter(~pl.col('disk') & (pl.col('day') >= '2023-01-01'))),
                       ('on-disk names (opened)', df.filter(pl.col('disk')))):
            if g.height:
                ww, oo = arms(g)
                parts[lab] = delta(ww, oo, sessions, full=False)
        out['parts'] = parts
        out['screen_pass'] = res['pass']
        C.jdump(out, C.OUT / 'screen.json')
    else:
        out['verdict'] = 'PASS' if res['pass'] else 'FAIL'
        C.jdump(out, C.OUT / 'holdout.json')
    m = res['main']
    print(split, 'trades', df.height, 'events', out['events'], 'Δ', m.get('delta'), 'CI', m.get('ci'), 'pass', res['pass'])


if __name__ == '__main__':
    main(sys.argv[1])
