"""
run_picker.py — the picker's pre-registered test (PREREG_PICKER.md, commit c502122), run exactly as frozen.

Reads files only (the stored ThetaData minute Parquet, the official SPX closes, the flow recorder's one session, and the
GeorgeFi cards from git objects at 75c29c9^). No vendor call. Deterministic: no random draw but audit_lib's seeded
bootstraps. Writes out/ (trade CSVs, summary.json) and PICKER_REPORT.md beside this file.

  POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 nice -n 10 python3 -I run_picker.py
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / 'backtest_audit'))
import audit_lib as AL  # noqa: E402  (session_stats, block_draws, weights_from, pct_ci, expected_sessions, SEED, BOOT_N)

OUT = HERE / 'out'
RAW = Path(os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta'))
PREREG = HERE / 'PREREG_PICKER.md'
PREREG_COMMIT = 'c502122'
CARDS_REV = '75c29c9^'
NY = ZoneInfo('America/New_York')

EPS = 1e-9
NMIN = 391
FLAT = 388                    # 15:58
OR_BARS = range(0, 30)        # bars stamped 09:30..09:59
SCAN = range(30, 150)         # bars stamped 10:00..11:59
BUF = 2.0                     # bps
STOP, TGT, PROG, TSTOP = 0.68, 1.25, 1.06, 5
VIX_TIERS = [(15.0, 0.06), (20.0, 0.08), (30.0, 0.11), (math.inf, 0.14)]
FEE_ETF = 0.65 + 0.01248 + 0.025                 # $0.68748
FEE_SPXW_LO, FEE_SPXW_HI = 0.65 + 0.36 + 0.14 + 0.01248 + 0.025, 0.65 + 0.45 + 0.14 + 0.01248 + 0.025   # 1.18748 / 1.27748
SPAN = {'SPY': ('2022-11-11', '2026-10-21'), 'QQQ': ('2022-11-11', '2026-10-21'),
        'SPXW': ('2022-05-13', '2026-10-21'), 'IWM': ('2024-04-19', '2026-10-09')}
PRIMARY_NAMES = ('SPY', 'QQQ', 'IWM', 'SPXW')
IMPROVED_NAMES = ('SPXW', 'SPY', 'IWM')
NEVER_READ_FROM = '2026-10-14'
FLOW_DAY = '2026-10-21'


# ---- small helpers --------------------------------------------------------------------------------------------------------------------

def r4(x):
    return round(float(x), 4)


def fee(name: str, px: float) -> float:
    """per contract, one side; nothing on a $0 side"""
    if px <= 0:
        return 0.0
    if name == 'SPXW':
        return FEE_SPXW_LO if px < 1.0 - EPS else FEE_SPXW_HI
    return FEE_ETF


def tick(name: str, px: float) -> float:
    if name == 'SPXW':
        return 0.05 if px < 3.0 - EPS else 0.10
    return 0.01


def target_price(name: str, ask0: float) -> float:
    """1.25 × entryAsk rounded UP to the option's tick (a resting sell)"""
    raw = TGT * ask0
    t = tick(name, raw)
    return r4(math.ceil(round(raw / t, 9)) * t)


def mcol(c='timestamp'):
    return (pl.col(c).dt.hour().cast(pl.Int32) * 60 + pl.col(c).dt.minute().cast(pl.Int32)) - 570


def arr(df: pl.DataFrame, key: str, val: str) -> np.ndarray:
    a = np.full(NMIN, np.nan)
    if df.height:
        k = df[key].to_numpy(); v = df[val].to_numpy().astype(float)
        ok = (k >= 0) & (k < NMIN) & np.isfinite(v)
        a[k[ok]] = np.round(v[ok], 4)
    return a


# ---- the excluded dates: re-derived from the git objects, checked against the prereg ---------------------------------------------------

def git_bytes(path: str) -> bytes:
    return subprocess.run(['git', '-C', str(REPO), 'show', f'{CARDS_REV}:{path}'], check=True, capture_output=True).stdout


def ny_day(s) -> str:
    return dt.datetime.fromisoformat(str(s).replace('Z', '+00:00')).astimezone(NY).date().isoformat()


def load_cards():
    d1 = json.loads(gzip.decompress(git_bytes('evidence/public_api/trades_all.json.gz')))['trades']
    books = {b: json.loads(gzip.decompress(git_bytes(f'evidence/public_api/trades_book_{b}.json.gz')))['trades']
             for b in ('trade_now_v1', 'singles_today_v1', 'spx_plan_v1')}
    spx_paper = json.loads(git_bytes('evidence/auth_api/spx_paper-trades_days_30_ticker_SPX.json'))['trades']
    recap = list(csv.DictReader(io.StringIO(git_bytes('evidence/analysis/recap_alerts.csv').decode())))
    tape = list(csv.DictReader(io.StringIO(git_bytes('evidence/analysis/public_tape_signals.csv').decode())))
    snaps = subprocess.run(['git', '-C', str(REPO), 'ls-tree', '--name-only', CARDS_REV, 'evidence/analysis_snapshots/'],
                           check=True, capture_output=True, text=True).stdout.split()
    return d1, books, spx_paper, recap, tape, snaps


def excluded_dates(cards) -> list[str]:
    d1, books, spx_paper, recap, tape, snaps = cards
    u = set()
    for rows in [d1, *books.values(), spx_paper]:
        for r in rows:
            for k in ('entryTime', 'exitTime'):
                if r.get(k):
                    u.add(ny_day(r[k]))
    u |= {r['date'] for r in recap} | {r['session'] for r in tape}
    for f in snaps:
        m = re.search(r'_(\d{8})T', f)
        if m:
            u.add(f'{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}')
    return sorted(u)


def prereg_dates() -> list[str]:
    txt = PREREG.read_text()
    block = txt.split('The list:')[1].split('(2026-10-10 is a Saturday')[0]
    return sorted(re.findall(r'\d{4}-\d{2}-\d{2}', block))


# ---- per-session data -----------------------------------------------------------------------------------------------------------------

UNDER = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPY'}
_bar_files: dict[str, list[str]] = {}


def bar_days(u: str) -> list[str]:
    if u not in _bar_files:
        _bar_files[u] = sorted(f[:-8] for f in os.listdir(RAW / 'data' / 'underlying' / u) if f.endswith('.parquet'))
    return _bar_files[u]


def read_bars(u: str, d: str):
    p = pl.read_parquet(RAW / 'data' / 'underlying' / u / f'{d}.parquet', columns=['timestamp', 'high', 'low', 'close'])
    p = p.with_columns(mcol().alias('m')).filter(pl.col('close').is_not_null())
    return arr(p, 'm', 'high'), arr(p, 'm', 'low'), arr(p, 'm', 'close')


def read_index(sym: str, d: str) -> np.ndarray:
    p = pl.read_parquet(RAW / 'data' / 'index' / sym / f'{d}.parquet').with_columns(mcol().alias('m'))
    return arr(p.filter(pl.col('price').is_not_null()), 'm', 'price')


def prior_high(u: str, d: str) -> float:
    days = bar_days(u)
    i = days.index(d)
    if i == 0:
        return float('nan')
    h, _, _ = read_bars(u, days[i - 1])
    x = h[0:390]
    return float(np.nanmax(x)) if np.any(np.isfinite(x)) else float('nan')


class Session:
    """everything one name-session needs, loaded once"""

    def __init__(self, name: str, d: str):
        self.name, self.d = name, d
        u = UNDER[name]
        self.h, self.l, self.c = read_bars(u, d)
        self.ratio = float('nan')
        if name == 'SPXW':
            spx = read_index('SPX', d)
            self.spx = spx
            spy_q = np.full(NMIN, np.nan); spy_q[1:] = self.c[:-1]          # SPY close at quote minute m = bar m-1
            pairs = [spx[m] / spy_q[m] for m in range(21, 31) if np.isfinite(spx[m]) and np.isfinite(spy_q[m]) and spy_q[m] > 0]
            if pairs:
                self.ratio = float(np.median(pairs))
            self.bh, self.bl, self.bc = self.h * self.ratio, self.l * self.ratio, self.c * self.ratio
            self.spot = spx                                                  # spot at quote minute m = the SPX print at m
        else:
            self.bh, self.bl, self.bc = self.h, self.l, self.c
            self.spot = np.full(NMIN, np.nan); self.spot[1:] = self.c[:-1]
        vix = read_index('VIX', d)
        self.vix = vix
        ch = pl.read_parquet(RAW / 'data_full' / 'chains' / name / f'{d}.parquet',
                             columns=['timestamp', 'strike', 'right', 'bid', 'ask'])
        ok = (pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid'))
              & (pl.col('bid') >= 0) & (pl.col('ask') > 0))
        self.chain = ch.with_columns(mcol().alias('m')).filter((pl.col('m') >= 1) & (pl.col('m') <= 390) & ok)

    def or_levels(self):
        hh = self.bh[list(OR_BARS)]; ll = self.bl[list(OR_BARS)]
        rh = float(np.nanmax(hh)) if np.any(np.isfinite(hh)) else float('nan')
        rl = float(np.nanmin(ll)) if np.any(np.isfinite(ll)) else float('nan')
        return rh, rl

    def pick(self, e: int, side: str):
        """nearest OTM same-day strike on the side whose quote stands at e → (strike, bid[], ask[]) or a reason"""
        s = self.spot[e]
        if not np.isfinite(s):
            return 'no spot'
        q = self.chain.filter((pl.col('m') == e) & (pl.col('right') == side))
        q = q.filter(pl.col('strike') < s) if side == 'PUT' else q.filter(pl.col('strike') > s)
        if q.height == 0:
            return 'no eligible contract'
        k = float(q['strike'].max() if side == 'PUT' else q['strike'].min())
        path = self.chain.filter((pl.col('strike') == k) & (pl.col('right') == side))
        return k, arr(path, 'm', 'bid'), arr(path, 'm', 'ask')


# ---- triggers -------------------------------------------------------------------------------------------------------------------------

def or_triggers(S: Session):
    """the first bar stamped 10:00-11:59 per side: high >= ORH(1+2bp) & close < ORH → PUT; low <= ORL(1-2bp) & close > ORL → CALL"""
    rh, rl = S.or_levels()
    out = []
    if not (np.isfinite(rh) and np.isfinite(rl)):
        return out, 'no opening range'
    for side, L in (('PUT', rh), ('CALL', rl)):
        for bm in SCAN:
            hi, lo, cl = S.bh[bm], S.bl[bm], S.bc[bm]
            if not (np.isfinite(hi) and np.isfinite(cl)):
                continue
            if side == 'PUT' and hi >= L * (1 + BUF / 1e4) and cl < L:
                out.append((side, bm, L)); break
            if side == 'CALL' and lo <= L * (1 - BUF / 1e4) and cl > L:
                out.append((side, bm, L)); break
    return out, None


def pdh_trigger(S: Session, pdh: float):
    if not np.isfinite(pdh):
        return []
    for bm in SCAN:
        hi, cl = S.bh[bm], S.bc[bm]
        if not (np.isfinite(hi) and np.isfinite(cl)):
            continue
        if hi >= pdh * (1 + BUF / 1e4) and cl < pdh:
            return [('PUT', bm, pdh)]
    return []


# ---- exits ----------------------------------------------------------------------------------------------------------------------------

def last_bid(bid: np.ndarray, e: int, m: int) -> float:
    """the bid at m if it stands, else the last standing bid in (e, m), else 0"""
    for j in range(m, e, -1):
        if np.isfinite(bid[j]):
            return float(bid[j])
    return 0.0


def run_exit(kind: str, name: str, e: int, ask0: float, bid: np.ndarray, vix_t: float = 0.11,
             ride_itm=None):
    """kind: 'primary' | 'secondary' | 's2' | 'improved'. Returns (exit_m, price, reason, ride)"""
    T = target_price(name, ask0)
    stop = STOP * ask0
    peak = -math.inf                 # highest standing bid through the current minute
    lock_at = None
    for m in range(e + 1, FLAT + 1):
        b = bid[m]
        q = np.isfinite(b)
        peak_prior = peak
        if q:
            peak = max(peak, b)
        # 1. target (a resting limit) first
        if q and b >= T - EPS:
            return m, T, 'target', False
        if kind in ('primary', 'secondary', 's2') and q and b <= stop + EPS:
            return m, float(b), 'stop', False
        if kind == 'secondary':
            if q and lock_at is not None and m > lock_at and b <= ask0 + EPS:
                return m, float(b), 'lock', False
            if q and peak_prior >= PROG * ask0 - EPS and b <= (1 - vix_t) * peak_prior + EPS:
                return m, float(b), 'trail', False
            if lock_at is None and q and peak >= PROG * ask0 - EPS:
                lock_at = m
        if m == e + TSTOP:
            if kind == 'primary' and peak < PROG * ask0 - EPS:
                return m, last_bid(bid, e, m), 'time5', False
            if kind in ('s2', 'improved'):
                return m, last_bid(bid, e, m), 'time5', False
        if m == FLAT:
            if ride_itm is not None and ride_itm:
                return m, float('nan'), 'flat', True
            return m, last_bid(bid, e, m), 'flat', False
    raise RuntimeError('no exit')


def settle_spxw(k: float, side: str, official: float) -> float:
    return max(official - k, 0.0) if side == 'CALL' else max(k - official, 0.0)


# ---- the runs -------------------------------------------------------------------------------------------------------------------------

def official_spx() -> dict[str, float]:
    out = {}
    with open(REPO / 'data' / 'official_closes' / 'cboe_SPX_History_2026-10-22.csv') as f:
        for r in csv.DictReader(f):
            mm, dd, yy = r['DATE'].split('/')
            out[f'{yy}-{mm}-{dd}'] = float(r['SPX'])
    return out


def sessions_for(name: str, excl: set[str]):
    a, b = SPAN[name]
    keep, left = [], []
    for d in AL.expected_sessions(a, b):
        if d in excl:
            continue
        need = [RAW / 'data_full' / 'chains' / name / f'{d}.parquet', RAW / 'data' / 'underlying' / UNDER[name] / f'{d}.parquet',
                RAW / 'data' / 'index' / 'VIX' / f'{d}.parquet']
        if name == 'SPXW':
            need.append(RAW / 'data' / 'index' / 'SPX' / f'{d}.parquet')
        miss = [str(p.relative_to(RAW)) for p in need if not p.exists()]
        (left.append((d, 'missing ' + ', '.join(miss))) if miss else keep.append(d))
    return keep, left


def vix_tier(S: Session, e: int) -> float:
    v = S.vix[e]
    if not np.isfinite(v):
        w = S.vix[max(0, e - 5):e]
        v = float(np.nanmax(w)) if np.any(np.isfinite(w)) else float('nan')
    if not np.isfinite(v):
        return 0.11
    for hi, t in VIX_TIERS:
        if v < hi:
            return t
    return 0.14


def make_trade(run: str, kind: str, S: Session, side: str, bm: int, L: float, k, bid, ask, official, extra=None):
    name, d = S.name, S.d
    e = bm + 1
    ask0 = float(ask[e])
    vt = vix_tier(S, e)
    if kind == 'ride':
        # S3: the primary, except an SPXW position open at 15:58 and in the money on the 15:58 print rides to the official close
        s958 = S.spx[FLAT] if name == 'SPXW' else float('nan')
        itm = np.isfinite(s958) and ((side == 'CALL' and s958 > k) or (side == 'PUT' and s958 < k))
        m, px, reason, rode = run_exit('primary', name, e, ask0, bid, ride_itm=bool(itm))
    else:
        m, px, reason, rode = run_exit(kind, name, e, ask0, bid, vix_t=vt)
    note = ''
    fee_out = 0.0
    if rode:
        px = settle_spxw(k, side, official[d]); note = 'rode to the official close'
    elif px <= 0:
        if name == 'SPXW':
            px = settle_spxw(k, side, official[d]); note = 'no bid: cash-settled on the official close'
        else:
            px = 0.0
            spot_exit = S.spot[min(m, FLAT)]
            itm = np.isfinite(spot_exit) and ((side == 'CALL' and spot_exit > k) or (side == 'PUT' and spot_exit < k))
            note = 'no bid: $0' + (' (IN THE MONEY at the exit spot)' if itm else '')
    else:
        fee_out = fee(name, px)
    fee_in = fee(name, ask0)
    pnl = (px - ask0) * 100 - fee_in - fee_out
    row = dict(run=run, name=name, session=d, year=d[:4], side=side, level=r4(L), trigger_bar=bm, entry_m=e, strike=k,
               spot_entry=r4(S.spot[e]), ratio=r4(S.ratio) if name == 'SPXW' else None, entry_ask=ask0,
               entry_bid=float(bid[e]) if np.isfinite(bid[e]) else None, target=target_price(name, ask0), exit_m=m,
               exit_px=r4(px), reason=reason, note=note, fee_in=round(fee_in, 5), fee_out=round(fee_out, 5),
               pnl=round(pnl, 4), pct=round(pnl / (ask0 * 100) * 100, 4), vix_trail=vt)
    if extra:
        row.update(extra)
    return row


def run_all(excl: set[str]):
    official = official_spx()
    rows = {k: [] for k in ('primary', 'secondary', 's2', 's3', 'improved')}
    skipped = {k: [] for k in ('primary', 'improved')}
    sess = {}
    left_out = {}
    for name in PRIMARY_NAMES:
        keep, left = sessions_for(name, excl)
        sess[name] = keep; left_out[name] = left
        t0 = time.time()
        for i, d in enumerate(keep):
            if name == 'SPXW' and d not in official:
                left_out[name].append((d, 'no official SPX close')); continue
            S = Session(name, d)
            if name == 'SPXW' and not np.isfinite(S.ratio):
                skipped['primary'].append((name, d, '-', 'no ratio')); continue
            trig, why = or_triggers(S)
            if why:
                skipped['primary'].append((name, d, '-', why))
            for side, bm, L in trig:
                e = bm + 1
                if e > 390 - 2:
                    continue
                p = S.pick(e, side)
                if isinstance(p, str):
                    skipped['primary'].append((name, d, side, p)); continue
                k, bid, ask = p
                rows['primary'].append(make_trade('primary', 'primary', S, side, bm, L, k, bid, ask, official))
                rows['secondary'].append(make_trade('secondary', 'secondary', S, side, bm, L, k, bid, ask, official))
                rows['s2'].append(make_trade('s2', 's2', S, side, bm, L, k, bid, ask, official))
                if name == 'SPXW':
                    rows['s3'].append(make_trade('s3', 'ride', S, side, bm, L, k, bid, ask, official))
            if name in IMPROVED_NAMES:
                pdh = prior_high(UNDER[name], d) * (S.ratio if name == 'SPXW' else 1.0)
                for side, bm, L in pdh_trigger(S, pdh):
                    p = S.pick(bm + 1, side)
                    if isinstance(p, str):
                        skipped['improved'].append((name, d, side, p)); continue
                    k, bid, ask = p
                    rows['improved'].append(make_trade('improved', 'improved', S, side, bm, L, k, bid, ask, official))
            if i % 200 == 0:
                print(name, i, len(keep), len(rows['primary']), f'{time.time() - t0:.0f}s', flush=True)
    return rows, skipped, sess, left_out, official


# ---- statistics -----------------------------------------------------------------------------------------------------------------------

def stats_block(trades: list[dict], sessions: list[str]) -> dict:
    idx = {d: i for i, d in enumerate(sessions)}
    n = len(sessions)
    S_d, S_p, N = np.zeros(n), np.zeros(n), np.zeros(n)
    for t in trades:
        i = idx[t['session']]
        S_d[i] += t['pnl']; S_p[i] += t['pct']; N[i] += 1
    a = AL.session_stats(S_p, N, blocks=(20,))
    b = AL.session_stats(S_d, N, blocks=(20,))
    out = dict(sessions=n, trades=int(N.sum()), mean_pct=a.get('mean_trade'), ci_pct=a.get('ci_trade_b20'),
               mean_usd=b.get('mean_trade'), ci_usd=b.get('ci_trade_b20'))
    if trades:
        out['win'] = float(np.mean([t['pnl'] > 0 for t in trades]))
        rs = [t['reason'] for t in trades]
        out['exits'] = {r: rs.count(r) / len(rs) for r in sorted(set(rs))}
        out['median_ask'] = float(np.median([t['entry_ask'] for t in trades]))
    return out


def table(trades, sessions, names):
    res = {}
    for nm in names:
        ss = sessions[nm]
        tt = [t for t in trades if t['name'] == nm]
        res[nm] = {'ALL': stats_block(tt, ss)}
        for y in sorted({d[:4] for d in ss}):
            sy = [d for d in ss if d[:4] == y]
            res[nm][y] = stats_block([t for t in tt if t['year'] == y], sy)
        sn = [d for d in ss if d >= NEVER_READ_FROM]
        if sn:
            res[nm]['never-read 2026-10-14→21'] = stats_block([t for t in tt if t['session'] >= NEVER_READ_FROM], sn)
    return res


def verdict(st: dict) -> str:
    m, c = st.get('mean_pct'), st.get('ci_pct')
    if m is None or not c or any(not math.isfinite(v) for v in c):
        return 'FAIL (no interval)'
    return 'PASS' if (m > 0 and c[0] > 0) else 'FAIL'


# ---- the flow gate ---------------------------------------------------------------------------------------------------------------------

def flow_gate(trades: list[dict]) -> list[dict]:
    out = []
    for t in trades:
        if t['session'] != FLOW_DAY:
            continue
        sym = 'SPX' if t['name'] == 'SPXW' else t['name']
        f = REPO / 'data_recorder' / 'flow_alerts' / sym / f'{FLOW_DAY}.parquet'
        if not f.exists():
            continue
        fa = pl.read_parquet(f, columns=['created_at', 'type', 'has_sweep', 'total_ask_side_prem', 'option_chain'])
        fa = fa.with_columns(pl.col('created_at').str.to_datetime(time_zone='UTC').dt.convert_time_zone('America/New_York').alias('ts'))
        fa = fa.with_columns(mcol('ts').alias('mm'), pl.col('total_ask_side_prem').cast(pl.Float64).alias('ask_prem'))
        e = t['entry_m']
        w = fa.filter((pl.col('has_sweep') == 'true') & (pl.col('mm') >= e - 5) & (pl.col('mm') < e))
        mine = 'put' if t['side'] == 'PUT' else 'call'
        a = float(w.filter(pl.col('type') == mine)['ask_prem'].sum() or 0.0)
        b = float(w.filter(pl.col('type') != mine)['ask_prem'].sum() or 0.0)
        out.append(dict(t, gate_trade_side=a, gate_other_side=b, gate_alerts=w.height, gate=(a > b)))
    return out


# ---- the grade check -------------------------------------------------------------------------------------------------------------------

def grade_check(rows: list[dict], label: str) -> dict:
    recs = [r for r in rows if r.get('setupGrade') and r.get('pnlPercent') is not None and r.get('entryTime')]
    sess = sorted({ny_day(r['entryTime']) for r in recs})
    idx = {d: i for i, d in enumerate(sess)}
    n = len(sess)
    grades = [g for g in ('A+', 'A', 'A-', 'B+', 'B') if any(r['setupGrade'] == g for r in recs)]
    S, N = {}, {}
    out = {'label': label, 'cards': len(recs), 'sessions': n, 'grades': {}, 'diffs': {}}
    for g in grades:
        s, c = np.zeros(n), np.zeros(n)
        for r in recs:
            if r['setupGrade'] == g:
                i = idx[ny_day(r['entryTime'])]; s[i] += float(r['pnlPercent']) * 100; c[i] += 1
        S[g], N[g] = s, c
        ci = (float('nan'), float('nan'))
        if n >= 60:                       # the 20-session block interval; a draw holding none of this grade's cards is dropped
            Wg = AL.weights_from(AL.block_draws(n, 20), n)
            okg = (Wg @ c) > 0
            ci = AL.pct_ci(((Wg @ s) / np.maximum(Wg @ c, 1))[okg])
        gr = [r for r in recs if r['setupGrade'] == g]
        out['grades'][g] = dict(n=int(c.sum()), mean_pct=float(s.sum() / c.sum()), ci=ci,
                                win=float(np.mean([float(r.get('pnl') or 0) > 0 for r in gr])),
                                mean_usd=float(np.mean([float(r.get('pnl') or 0) for r in gr])))
    if n >= 60:
        W = AL.weights_from(AL.block_draws(n, 20), n)
        for a, b in (('A+', 'A'), ('A', 'B+'), ('A+', 'B+')):
            if a in S and b in S:
                da = (W @ S[a]) / np.maximum(W @ N[a], 1); db = (W @ S[b]) / np.maximum(W @ N[b], 1)
                ok = ((W @ N[a]) > 0) & ((W @ N[b]) > 0)
                pt = S[a].sum() / N[a].sum() - S[b].sum() / N[b].sum()
                out['diffs'][f'{a} − {b}'] = dict(diff=float(pt), ci=AL.pct_ci((da - db)[ok]))
    return out


# ---- the report ------------------------------------------------------------------------------------------------------------------------

def F(x, fmt='{:+.2f}'):
    return AL.f(x, fmt)


def C(t, fmt='{:+.2f}'):
    return AL.ci(t, fmt)


def exit_cols(kind):
    return {'primary': ('stop', 'target', 'time5', 'flat'), 's2': ('stop', 'target', 'time5', 'flat'),
            's3': ('stop', 'target', 'time5', 'flat'), 'secondary': ('stop', 'target', 'lock', 'trail', 'flat'),
            'improved': ('target', 'time5', 'flat')}[kind]


def md_table(res: dict, kind: str, verdicts: bool = False) -> str:
    ec = exit_cols(kind)
    head = ['name', 'span', 'sessions', 'trades', 'mean %/trade', '20-session block 95%', 'mean $/trade', '20-session block 95% ($)',
            'win rate'] + [f'exit {c}' for c in ec] + (['verdict'] if verdicts else [])
    lines = ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)]
    for nm, by in res.items():
        for span, st in by.items():
            ex = st.get('exits', {})
            cells = [nm, span, str(st['sessions']), str(st['trades']), F(st.get('mean_pct')) + '%' if st.get('mean_pct') is not None else '—',
                     C(st.get('ci_pct')), F(st.get('mean_usd')), C(st.get('ci_usd')),
                     F(st.get('win'), '{:.1%}') if st.get('win') is not None else '—'] + \
                    [F(ex.get(c, 0.0), '{:.1%}') if st['trades'] else '—' for c in ec]
            if verdicts:
                cells.append(f"**{verdict(st)}**" if span == 'ALL' else '')
            lines.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(lines)


def main():
    t_start = time.time()
    OUT.mkdir(exist_ok=True)
    cards = load_cards()
    excl = excluded_dates(cards)
    pre = prereg_dates()
    if excl != pre:
        raise SystemExit(f'excluded dates differ from the prereg: only derived {sorted(set(excl) - set(pre))}, only prereg {sorted(set(pre) - set(excl))}')
    excl_set = set(excl)
    rows, skipped, sess, left_out, official = run_all(excl_set)
    for k, v in rows.items():
        if v:
            pl.DataFrame(v, infer_schema_length=None).write_csv(OUT / f'trades_{k}.csv')
    res = {k: table(rows[k], sess, (PRIMARY_NAMES if k != 'improved' else IMPROVED_NAMES) if k != 's3' else ('SPXW',))
           for k in rows}
    verdicts = {nm: verdict(res['primary'][nm]['ALL']) for nm in PRIMARY_NAMES}
    overall = 'PASS' if all(v == 'PASS' for v in verdicts.values()) else 'FAIL'
    gated = flow_gate(rows['primary'])
    d1, books, spx_paper, *_ = cards
    grades = [grade_check(d1, 'D1 ICT Main ledger, all 489'),
              grade_check([r for r in d1 if (r.get('accountType') or r.get('account_type')) == '0DTE'], 'D1, 0DTE account'),
              grade_check(books['trade_now_v1'], 'Trade Now book'),
              grade_check(spx_paper, 'SPX paper trades')]
    in_card_span = {nm: [d for d in AL.expected_sessions(*SPAN[nm]) if d in excl_set] for nm in PRIMARY_NAMES}
    summary = dict(prereg=PREREG_COMMIT, excluded=len(excl), results=res, verdicts=verdicts, overall=overall,
                   skipped={k: v for k, v in skipped.items()}, left_out=left_out, sessions={k: len(v) for k, v in sess.items()},
                   excluded_sessions_in_span={k: len(v) for k, v in in_card_span.items()},
                   flow=gated, grades=grades, seconds=round(time.time() - t_start))
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=1, default=str))
    write_report(summary, rows, sess)
    print('done', overall, verdicts, f'{time.time() - t_start:.0f}s')


def write_report(sm, rows, sess):
    R = []
    p = R.append
    p('# The picker, tested out of sample: the 0DTE opening-range fade, as written\n')
    p(f'**Pre-registration: `PREREG_PICKER.md`, commit `{PREREG_COMMIT}`** (pushed before any P&L of this rule was computed). '
      f'Written by `run_picker.py` in this folder ({sm["seconds"]} s); `verify_picker.py` re-derives trades from the raw files. '
      'Files read only; no vendor call. Fees $0.68748 a contract each way on SPY/QQQ/IWM, $1.18748 / $1.27748 on SPXW (prereg §4); '
      '1 contract; entry at the ask, exits at the bid (a target at its resting limit). Intervals: 20-session moving-block bootstrap '
      '(audit_lib, 2,000 draws, seed 20261022), percentile 95%; none under 60 sessions.\n')
    v = sm['verdicts']
    p('## Summary\n')
    p(f'- **Verdict by the owner\'s rule (prereg §10, PRIMARY run, whole span, excluded dates out): '
      + '; '.join(f'{nm} {v[nm]}' for nm in PRIMARY_NAMES) + f'. As a whole: {sm["overall"]}.**')
    for nm in PRIMARY_NAMES:
        st = sm['results']['primary'][nm]['ALL']
        p(f'- {nm}: {st["trades"]} trades on {st["sessions"]} sessions, {F(st.get("mean_pct"))}% a trade {C(st.get("ci_pct"))}, '
          f'{F(st.get("mean_usd"))} $ a trade {C(st.get("ci_usd"))}, win rate {F(st.get("win"), "{:.1%}")}.')
    imp = sm['results']['improved']
    p('- IMPROVED (picked on the cards; labelled, separate): ' + '; '.join(
        f'{nm} {imp[nm]["ALL"]["trades"]} trades {F(imp[nm]["ALL"].get("mean_pct"))}% {C(imp[nm]["ALL"].get("ci_pct"))}' for nm in IMPROVED_NAMES)
      + ' — negative on every name, intervals below zero.')
    p('- Flow gate: the flow history on disk is one session (2026-10-21); the test runs without it. On that day no primary trade '
      'passed the gate (5 trades, 0 gated).')
    g0 = sm['grades'][0]
    p('- Grade check (descriptive, GeorgeFi\'s own recorded returns on D1): mean return A+ ' + F(g0['grades']['A+']['mean_pct'])
      + '%, A ' + F(g0['grades']['A']['mean_pct']) + '%, B+ ' + F(g0['grades']['B+']['mean_pct']) + '%; A+ − A '
      + F(g0['diffs']['A+ − A']['diff']) + ' ' + C(g0['diffs']['A+ − A']['ci']) + ', A − B+ ' + F(g0['diffs']['A − B+']['diff'])
      + ' ' + C(g0['diffs']['A − B+']['ci']) + ' (section 6).')
    p('- For scale: the engine audit\'s universe A (built the same way, a fuller exit stack, the same years) read −4.3% / −4.5% of '
      'the debit a trade (`exits_sizing.md` line 14) — the disclosure at the top of the prereg.')
    p(f'- Excluded: {sm["excluded"]} card dates (2026-03-02 → 2026-10-13); inside each name\'s span: '
      + ', '.join(f'{k} {n}' for k, n in sm['excluded_sessions_in_span'].items()) + ' full sessions.')
    p('')
    p('## 1. PRIMARY — the formal exits (stop 0.68 × ask, target 1.25 × ask, 5-minute stop if no +6%, flat 15:58)\n')
    p(md_table(sm['results']['primary'], 'primary', verdicts=True))
    p('\nThe never-read line (2026-10-14 → 21) is the only part of the stored data no study of this rule had read; it carries no verdict.\n')
    p('## 2. SECONDARY (labelled) — the narrative\'s breakeven lock at +6% and VIX trail, with the stop, target and flat\n')
    p(md_table(sm['results']['secondary'], 'secondary'))
    p('\n## 3. Sensitivities (labelled, no verdict)\n')
    p('**S2 — "5 minutes" as a hard exit:**\n')
    p(md_table(sm['results']['s2'], 's2'))
    p('\n**S3 — SPXW rides to the official close when in the money at 15:58:**\n')
    p(md_table(sm['results']['s3'], 's3'))
    p('\n## 4. IMPROVED (picked on the cards) — SPXW/SPY/IWM, PDH sweep → put, 10:00–12:00, sell at +25% or at 5 minutes; separate, never pooled\n')
    p(md_table(sm['results']['improved'], 'improved'))
    p('\nThe owner\'s rule applied to it, for reading only (labelled; the parameters were picked from the cards, the dates of which are excluded): '
      + '; '.join(f'{nm} {verdict(sm["results"]["improved"][nm]["ALL"])}' for nm in IMPROVED_NAMES) + '.\n')
    p('## 5. The flow gate\n')
    p(f'Flow history on disk covers one session ({FLOW_DAY}); the primary test above runs without the gate. On {FLOW_DAY}, '
      'the primary rule\'s trades with the gate (trade-side UW sweep ask-premium over the 5 minutes before entry > the other side):\n')
    if sm['flow']:
        p('| name | side | entry | strike | trade-side $ | other side $ | alerts | gate | P&L $ | % | exit |')
        p('|---|---|---|---|---|---|---|---|---|---|---|')
        for t in sm['flow']:
            p(f"| {t['name']} | {t['side']} | {minute_txt(t['entry_m'])} | {t['strike']} | {t['gate_trade_side']:,.0f} | {t['gate_other_side']:,.0f} | "
              f"{t['gate_alerts']} | {'pass' if t['gate'] else 'fail'} | {t['pnl']:+.2f} | {t['pct']:+.2f}% | {t['reason']} |")
        g = [t for t in sm['flow'] if t['gate']]
        p(f'\nGated: {len(g)} trade(s), ' + (f'mean {np.mean([t["pnl"] for t in g]):+.2f} $ ({np.mean([t["pct"] for t in g]):+.2f}%).' if g else 'none.')
          + ' Descriptive; one session.\n')
    else:
        p('No primary trade on that session.\n')
    p('## 6. The grade check (descriptive; the grade filters nothing)\n')
    for gc in sm['grades']:
        p(f"**{gc['label']}** — {gc['cards']} cards on {gc['sessions']} sessions. Return per trade = the card's `pnlPercent`.\n")
        p('| grade | n | mean %/trade | 20-session block 95% | win rate | mean $ |')
        p('|---|---|---|---|---|---|')
        for g, x in gc['grades'].items():
            p(f"| {g} | {x['n']} | {F(x['mean_pct'])}% | {C(x['ci'])} | {x['win']:.1%} | {x['mean_usd']:+.2f} |")
        for k, x in gc['diffs'].items():
            p(f"\n{k}: {F(x['diff'])} points {C(x['ci'])}")
        p('')
    vf = OUT / 'verify.txt'
    p('## 7. Verification, deviations, trades not taken\n')
    p('- `verify_picker.py` (separate plain-loop code, no import of this script or audit_lib): '
      + (vf.read_text().strip() if vf.exists() else 'not run yet') + '.')
    p('- Deviations from the prereg: (a) the grade check\'s per-grade intervals drop the bootstrap draws that hold no card of '
      'that grade (`audit_lib.session_stats` would count them as 0, pulling a sparse grade\'s interval to zero); the '
      'differences between grades use the same draws, dropping draws without both grades; (b) an SPXW session without an '
      'official SPX close would have been left out (needed for a no-bid or ride settlement) — none was. Nothing else.')
    for k, sk in sm['skipped'].items():
        from collections import Counter
        p(f"- {k}: " + (', '.join(f'{r} {n}' for r, n in Counter((s[0], s[3]) for s in sk).items()) if sk else 'none'))
    for nm, lo in sm['left_out'].items():
        p(f"- {nm} sessions left out: {len(lo)}" + (': ' + ', '.join(f'{d} ({w})' for d, w in lo[:20]) + (' …' if len(lo) > 20 else '') if lo else ''))
    zero = [t for k in ('primary', 'improved') for t in rows[k] if t['note']]
    p(f"- exits with a note (no bid / ride): {len(zero)}" + (': ' + '; '.join(f"{t['run']} {t['name']} {t['session']} {t['note']}" for t in zero[:15]) if zero else ''))
    p('\n## 8. IWM and RUT\n')
    p('Not fetched (prereg §11): IWM is on disk to 2026-10-09 and is tested there; its 8 missing sessions (2026-10-12 → 21) are 16 ThetaData '
      'requests, ≈ 2.6 MB. RUT/RUTW: nothing on disk; one expirations list call, then a chain and an index-price call a session — ≤ ≈ 1,960 '
      'requests and ≈ 0.2–0.8 GB over 2022-11-11 → 2026-10-21.\n')
    (HERE / 'PICKER_REPORT.md').write_text('\n'.join(R) + '\n')


def minute_txt(m: int) -> str:
    h, mm = divmod(570 + m, 60)
    return f'{h:02d}:{mm:02d}'


if __name__ == '__main__':
    main()
