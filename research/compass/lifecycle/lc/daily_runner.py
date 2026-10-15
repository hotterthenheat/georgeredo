"""Tier D runner: daily setups x expiration buckets x structures x daily policies on DailyChains (lifecycle protocol
§1, §4, §5 at daily resolution). The position engine is lc.position with sessions as its time axis.

Buckets (calendar days from the decision session to the last trading day; the listed expiration nearest the target):
  W  Weekly 1-7 (target 5)    S  Swing 8-45 (target 30)    P  Position 46-90 (target 60)
  L  Long-Dated 91-269 (target 180)    X  LEAPS-tagged Long-Dated, 270 or more (target 365)
An expiration is usable at a session only if the chain carries a two-sided quote for it that session (point in time).

Daily policies carry a cut rule: 'expiry' (hold to settlement), 'ltd1' (close at the session before the last trading
day), 'dte21' (close at the first session 21 or fewer calendar days out; 'ltd1' if already inside), 'pre'/'post'
(earnings: the close before the first session that trades on the report, or that session's close)."""
from __future__ import annotations
import datetime as dt, json, os, sys, time, zlib
from functools import lru_cache
import numpy as np
import polars as pl
from . import daily as dy, daily_events as de, structures as stc, position as ps, policies as pol, paths, bs
from .runner import AGG, _agg_block, _flush_daily, _write_daily
sys.path.insert(0, os.path.dirname(paths.HERE))
from engine import calendar as cal  # noqa: E402

BUCKETS = {'W': (1, 7, 5), 'S': (8, 45, 30), 'P': (46, 90, 60), 'L': (91, 269, 180), 'X': (270, 1200, 365)}
DEV_END, VAL_END = dt.date(2021, 12, 31), dt.date(2023, 12, 31)
HOLDOUT_START = dt.date(2024, 1, 1)
SEEDS = (0, 1, 2, 3, 4)

def daily_policies():
    P = lambda **kw: ps.params(CUTOFF=-1, QUOTE_WAIT=0, **kw)
    out = [
        ('D0_expiry', 'M0', 'expiry', P()), ('D0_ltd1', 'M0', 'ltd1', P()), ('D0_dte21', 'M0', 'dte21', P()),
        ('D1_t5', 'M1', 'ltd1', P(TIME_EXIT=5)), ('D1_t10', 'M1', 'ltd1', P(TIME_EXIT=10)), ('D1_t20', 'M1', 'dte21', P(TIME_EXIT=20)),
        ('D2_s50_t50', 'M2', 'dte21', P(STOP=0.5, TARGET=0.5)), ('D2_s50_t100', 'M2', 'dte21', P(STOP=0.5, TARGET=1.0)),
        ('D2_s35_t35', 'M2', 'dte21', P(STOP=0.35, TARGET=0.35)), ('D2_s50_t50_exp', 'M2', 'ltd1', P(STOP=0.5, TARGET=0.5)),
        ('D3_p50at50_trail25', 'M3', 'dte21', P(STOP=0.5, P1_FRAC=0.5, P1_AT=0.5, TRAIL_ARM=0.5, TRAIL_GIVE=0.25)),
        ('D4_arm50_give25', 'M4', 'dte21', P(STOP=0.5, TRAIL_ARM=0.5, TRAIL_GIVE=0.25)),
        ('D5_thesis', 'M5', 'dte21', P(THESIS=1)),
        ('D6_add1atr', 'M6', 'dte21', P(ADD_K=1.0, ADD_MAX=1, STOP=0.5, TARGET=1.0)),
        ('D7_dd40', 'M7', 'dte21', P(DD_AT=0.4, DD_MAX=1)),
        ('D9_rsi_exit', 'M9', 'dte21', P(WARN_MASK=1, WARN_ACTION=2)),
        ('D12_both_t50', 'M12', 'ltd1', P(TARGET=0.5)), ('D12_leg_k05_trail25', 'M12', 'ltd1', P(LEG_K=0.5, LEG_TRAIL=0.25)),
        ('D13_expiry', 'M13', 'expiry', P()), ('D13_tp50', 'M13', 'expiry', P(CREDIT_TP=0.5)), ('D13_tp50_s2', 'M13', 'expiry', P(CREDIT_TP=0.5, CREDIT_STOP=2.0)),
        ('D13_s2', 'M13', 'expiry', P(CREDIT_STOP=2.0)), ('D13_tp50_dte21', 'M13', 'dte21', P(CREDIT_TP=0.5)),
        ('E_pre', 'EV', 'pre', P()), ('E_post', 'EV', 'post', P()),
    ]
    return out

FAMILY_FOR = {'debit': {'M0', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M9'}, 'straddle': {'M0', 'M1', 'M2', 'M12', 'EV'}, 'credit': {'M0', 'M1', 'M5', 'M13'}}

def structures_for(setup: str, direction: int):
    if setup in ('D_ALLV', 'D_VOLC', 'D_FOMC', 'D_ALLF', 'D_EARN', 'D_EARNC'): return ('STR', 'STG')
    if setup in ('D_ALLP', 'D_VOLR'): return ('CPS', 'CSP')
    return stc.DIRECTIONAL_LONG[1 if direction > 0 else -1]

def t_years(ch, m):
    close = dt.datetime.combine(ch.meta['ltd'], cal.close_time(ch.meta['ltd']))
    at = dt.datetime.combine(ch.sessions[m], cal.close_time(ch.sessions[m]))
    return max((close - at).total_seconds(), 3600.0) / (365.25 * 86400.0)

def atm_iv_series(ch) -> np.ndarray:
    """ATM IV per session (the strike nearest spot; mean of the call's and put's mid IVs where quoted), vectorised."""
    T = ch.n_min
    calls = {k: i for i, k in enumerate(ch.strike) if ch.is_call[i]}; puts = {k: i for i, k in enumerate(ch.strike) if not ch.is_call[i]}
    ks = np.array(sorted(set(calls) & set(puts)))
    if ks.size == 0: return np.full(T, np.nan)
    K = ks[np.abs(ks[None, :] - ch.spot[:, None]).argmin(axis=1)]
    ci = np.array([calls[k] for k in K]); pi = np.array([puts[k] for k in K]); mm = np.arange(T)
    t = np.array([t_years(ch, m) for m in range(T)])
    def mid(i):
        b, a = ch.bid[i, mm], ch.ask[i, mm]
        return np.where(np.isfinite(b) & np.isfinite(a) & (a > 0) & (a >= b), (a + b) / 2, np.nan)
    vc = bs.implied_vol(mid(ci), ch.spot.astype(float), K.astype(float), t, np.ones(T)); vp = bs.implied_vol(mid(pi), ch.spot.astype(float), K.astype(float), t, -np.ones(T))
    with np.errstate(invalid='ignore'):
        return np.where(np.isfinite(vc) & np.isfinite(vp), (vc + vp) / 2, np.where(np.isfinite(vc), vc, vp))

class Chains:
    def __init__(self, root, maxsize=64):
        self.root = root; self.cache = {}; self.order = []; self.maxsize = maxsize
        self.exps = dy.expirations(root)
        self.listed = dy.listed_ranges(root)
        self.ds = dy.daily_series(root).sort('session')
    def get(self, e):
        if e in self.cache: return self.cache[e]
        ch = dy.load(self.root, e, am_settled=False)
        if ch is not None:
            m = self.ds.filter(pl.col('session').is_in(ch.sessions)).sort('session')
            adj = m['adj'].to_numpy()
            ch.meta['ema'] = m['ema20'].to_numpy() * adj; ch.meta['rsi'] = m['rsi14'].to_numpy(); ch.meta['atr'] = m['atr14'].to_numpy() * adj
            ch.meta['ativ'] = atm_iv_series(ch); ch.meta['ix'] = {s: i for i, s in enumerate(ch.sessions)}
            if len(m) != ch.n_min: ch = None
        self.cache[e] = ch; self.order.append(e)
        if len(self.order) > self.maxsize:
            old = self.order.pop(0); self.cache.pop(old, None)
        return ch
    def pick(self, d: dt.date, bucket: str):
        lo, hi, tgt = BUCKETS[bucket]
        best = None
        for e in self.exps:
            first, last = self.listed.get(e, (None, None))
            if first is None or not (first <= d <= last): continue      # not listed (or no longer quoted) on d
            dte = (cal.last_trading_day(e, False) - d).days
            if lo <= dte <= hi and (best is None or abs(dte - tgt) < abs(best[1] - tgt)): best = (e, dte)
        return best

def cut_index(ch, m, rule, ev_session=None):
    T = ch.n_min
    if rule == 'expiry': return -1
    if rule == 'ltd1': return max(T - 2, m + 1)
    if rule == 'dte21':
        for k in range(m + 1, T):
            if (ch.meta['ltd'] - ch.sessions[k]).days <= 21: return k
        return max(T - 2, m + 1)
    if rule in ('pre', 'post') and ev_session is not None:
        ix = ch.meta['ix']
        if ev_session not in ix: return None
        k = ix[ev_session] - 1 if rule == 'pre' else ix[ev_session]
        return k if k > m else None
    return None

ROWS_POLICIES = ('D0_expiry', 'D0_ltd1', 'D0_dte21', 'D1_t10', 'D2_s50_t50', 'D13_expiry', 'D13_tp50', 'D13_tp50_s2', 'E_pre', 'E_post')

def run_root(root: str, stage: str = 'dgrid', mode: str = 'daily', include_holdout: bool = False, buckets=('W', 'S', 'P', 'L', 'X'),
             setups: tuple | None = None, start: dt.date | None = None, end: dt.date | None = None, with_controls: bool = True, log=print,
             policy_names: tuple | None = None):
    out_dir = f'{paths.WORK}/runs/{stage}/{root}'; os.makedirs(out_dir, exist_ok=True)
    pols = daily_policies()
    if policy_names: pols = [p for p in pols if p[0] in policy_names]
    names = [p[0] for p in pols]
    PM = np.vstack([p[3] for p in pols])
    t0 = time.time()
    dy.repartition(root)
    ev = de.directional(root)
    if root in ('SPY', 'QQQ', 'IWM'): ev = pl.concat([ev, de.fomc(root)], how='diagonal_relaxed')
    else:
        e = de.earnings(root)
        if e.height: ev = pl.concat([ev, e], how='diagonal_relaxed')
    if setups: ev = ev.filter(pl.col('setup').is_in(list(setups)))
    if not include_holdout: ev = ev.filter(pl.col('session') < HOLDOUT_START)
    if start: ev = ev.filter(pl.col('session') >= start)
    if end: ev = ev.filter(pl.col('session') <= end)
    if 'event_session' not in ev.columns: ev = ev.with_columns(pl.lit(None, dtype=pl.Date).alias('event_session'))
    items = [{**r, 'ctrl': -1, 'event_i': i} for i, r in enumerate(ev.iter_rows(named=True))]
    if with_controls:
        und = dy.underlying_daily(root); ss = [s for s in und['session'].to_list() if s < HOLDOUT_START or include_holdout]
        for it in list(items):
            if it['setup'] not in ('D_TP', 'D_BO', 'D_BOF', 'D_BN', 'D_BNF'): continue
            for sd in SEEDS:
                rng = np.random.default_rng(zlib.crc32(f'{root}|{it["session"]}|{it["event_i"]}|{sd}'.encode()))
                d = ss[int(rng.integers(200, len(ss)))]
                items.append({**it, 'session': d, 'ctrl': sd, 'inv': np.nan})
    items.sort(key=lambda x: x['session'])
    chains = Chains(root)
    daily = {}; chunks = ([], [], [], [], [], []); pos_rows = []; out_blocks = []; out_keys = []
    pid = 0; nruns = 0; n_incomplete = 0
    for n_it, it in enumerate(items):
        d = it['session']
        for b in buckets:
            pk = chains.pick(d, b)
            if pk is None: continue
            e, dte = pk
            ch = chains.get(e)
            if ch is None or d not in ch.meta['ix']: continue
            if ch.sessions[-1] < ch.meta['ltd']:
                # the data ends before this expiration's last trading day (an entry near the end of the pull): its path is
                # incomplete, so it is left out rather than settled early at intrinsic value
                n_incomplete += 1; continue
            m = ch.meta['ix'][d]
            if m >= ch.n_min - 1: continue
            tg = t_years(ch, m)
            for code in structures_for(it['setup'], it['direction']):
                legs, ratio, info = stc.build(ch, m, tg, code, it['direction'])
                key = dict(pos_id=pid, session=d, setup=it['setup'], ctrl=it['ctrl'], bucket=b, expiration=e, dte=dte, structure=code, direction=int(it['direction']))
                if legs is None: pos_rows.append({**key, 'skip': info['skip']}); pid += 1; continue
                nleg = info['nleg']
                h = ps.hindsight(ch.bid, ch.ask, legs, ratio, nleg, m, ch.n_min - 1, 0.0)
                pos_rows.append({**key, 'skip': None, 'k1': info['strikes'][0], 'd1': info['deltas'][0], 'iv1': info['ivs'][0], 'rel_spread': info['rel_spread'],
                                 'spot': float(ch.spot[m]), 'cost0': h[0], 'mfe_liq': h[1] - h[0], 't_mfe': h[2] - m, 'mae_liq': h[3] - h[0], 't_mae': h[4] - m, 'src': 'eod'})
                kind = pol.kind_of(code)
                fams = FAMILY_FOR[kind]
                sel = [i for i, p in enumerate(pols) if p[1] in fams and (p[1] != 'EV' or it['setup'] in ('D_EARN', 'D_EARNC'))]
                res = np.zeros((len(sel), ps.NO))
                for j, i in enumerate(sel):
                    q = PM[i].copy()
                    ci = cut_index(ch, m, pols[i][2], it.get('event_session'))
                    if ci is None and pols[i][2] in ('pre', 'post'): continue
                    q[ps.P['CUTOFF']] = ci if ci is not None else -1
                    res[j] = ps.simulate(ch.bid, ch.ask, ch.strike, ch.is_call, ch.spot, ch.meta['ema'], ch.meta['rsi'], ch.meta['atr'], ch.meta['ativ'], ch.n_min,
                                         legs, ratio, nleg, m, int(it['direction']), float(it['inv']) if it['inv'] is not None else np.nan, np.nan,
                                         ch.next_open, False, info['short_strike'], q)
                pidx = np.array(sel, np.int64)
                if mode == 'rows':
                    out_blocks.append(res.astype(np.float32)); out_keys.append(np.column_stack([np.full(pidx.size, pid), pidx]))
                else:
                    k = (d, f'{it["setup"]}|{b}', code, 0 if it['ctrl'] < 0 else 1)
                    acc = daily.get(k)
                    if acc is None: acc = daily[k] = np.zeros((len(PM), len(AGG)))
                    acc[pidx] += _agg_block(res)
                nruns += pidx.size; pid += 1
        if mode == 'daily' and n_it % 200 == 0: _flush_daily(daily, chunks)
        if n_it % 1000 == 0: log(f'{root} {stage}: {n_it}/{len(items)} events, {pid} positions, {nruns} runs, {time.time() - t0:.0f}s')
    pl.DataFrame(pos_rows, infer_schema_length=None).write_parquet(f'{out_dir}/positions.parquet', compression='zstd')
    if mode == 'daily':
        _flush_daily(daily, chunks)
        if chunks[0]: _write_daily(out_dir, chunks)
    else:
        from .runner import _write_rows
        _write_rows(out_dir, out_keys, out_blocks)
    meta = {'root': root, 'stage': stage, 'mode': mode, 'positions': pid, 'runs': nruns, 'policies': names, 'buckets': list(buckets),
            'events': len(items), 'incomplete_paths_left_out': n_incomplete, 'seconds': round(time.time() - t0, 1), 'holdout_included': include_holdout}
    json.dump(meta, open(f'{out_dir}/run.json', 'w'), indent=1, default=str)
    log(f'{root} {stage}: done {meta}')
    return meta
