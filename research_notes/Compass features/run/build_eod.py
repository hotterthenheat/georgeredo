"""
build_eod.py — everything the option EOD files give (prereg 2.3–2.7, 3.2): per name

  pass 1 (each weekly file alone): per trading day the total option volume, the closing spreads used by the tiers, every
  1–60 DTE expiry's forward / implied move / at-the-money IV, IV30, the next-session expiry's volumes (V3 for 0DTE
  entries) and the multi-day entries (1–7, 8–30, 31–60 DTE; five strike buckets; calls and puts);
  pass 2: the fixed exits (1–7: the expiry-day 15:58 bid, SPXW intrinsic on the official SPX close; 8–30: the 5th session
  after entry or the session before expiry; 31–60: the 10th session) and the X1 exit.

Outputs in $SP/features_work/: eod/<name>/days.parquet, expiries.parquet, nextvol.parquet, spreads.npz (split-free: inputs
only), and <split>/eod/<name>.parquet (the trades of that split) with its counts.

  POLARS_MAX_THREADS=1 python3 -I build_eod.py expl [names...]
"""
from __future__ import annotations

import math
import pickle
import sys
import time
from collections import Counter, defaultdict
import multiprocessing as mp
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402
import daily as D  # noqa: E402
import build_0dte as B0  # noqa: E402

MULTI = (('1-7', 1, 7, 4), ('8-30', 8, 30, 19), ('31-60', 31, 60, 45))
EOD_FIRST = {'SPY': '2012-06-01', 'QQQ': '2012-06-01', 'IWM': '2012-06-01'}     # singles: 2022-11-01; SPXW: its first file


def eod_dir(name: str) -> Path:
    C.guard_ticker(name)
    return C.THETA / 'fetch_cache' / 'eod_all' / name


def eod_files(name: str) -> list[Path]:
    fs = sorted(eod_dir(name).glob('*.parquet'))
    if name in C.SINGLES:
        fs = [f for f in fs if f.stem.split('__')[1] >= '2022-11-01']
    return fs


def first_day(name: str) -> str:
    if name in EOD_FIRST:
        return EOD_FIRST[name]
    if name in C.SINGLES:
        return '2022-11-01'
    fs = eod_files(name)
    return fs[0].stem.split('__')[0] if fs else '9999'


def load_week(f: Path) -> pl.DataFrame:
    x = pl.read_parquet(f, columns=['date', 'expiration', 'strike', 'right', 'volume', 'bid', 'ask'])
    return x.with_columns(pl.col('date').cast(pl.String), pl.col('expiration').cast(pl.String),
                          pl.col('bid').cast(pl.Float64).round(4), pl.col('ask').cast(pl.Float64).round(4),
                          pl.col('strike').cast(pl.Float64).round(4)).unique(['date', 'expiration', 'strike', 'right'], keep='first',
                                                                             maintain_order=True)


def atm_iv(name, K, cb, ca, pb, pa, F, Ks, T):
    """prereg 2.2: index names the IV at K* (call = put there by parity); single names the mean of the out-of-the-money
    call above F and put below F"""
    if name in C.SINGLES:
        cs = (cb > 0) & (ca > 0) & (ca >= cb) & (K > F)
        ps = (pb > 0) & (pa > 0) & (pa >= pb) & (K < F)
        if not cs.any() or not ps.any():
            return float('nan')
        ic = int(np.where(cs)[0][0])
        ip = int(np.where(ps)[0][-1])
        v = C.b76_iv(np.array([(cb[ic] + ca[ic]) / 2, (pb[ip] + pa[ip]) / 2]), F, np.array([K[ic], K[ip]]), T, np.array([True, False]))
        return float(np.mean(v)) if np.isfinite(v).all() else float('nan')
    i = int(np.where(K == Ks)[0][0])
    v = C.b76_iv(np.array([(cb[i] + ca[i]) / 2]), F, np.array([K[i]]), T, np.array([True]))
    return float(v[0])


def pass1_file(args):
    name, f, split_any = args
    C.set_split(split_any)
    x = load_week(f)
    full = set(C.sessions())
    out_days, out_exp, out_next, out_entries, spreads = [], [], [], [], {}
    for dd in sorted(x['date'].unique().to_list()):
        xd = x.filter(pl.col('date') == dd)
        out_days.append(dict(day=dd, total_vol=int(xd['volume'].sum() or 0), rows=xd.height))
        nxt = C.next_tday(dd)
        exps = sorted(xd['expiration'].unique().to_list())
        ltd = {e: C.last_trading_day(e) for e in exps}
        sp_list = []
        per_exp = {}
        for e in exps:
            le = ltd[e]
            if le is None:
                continue
            dte = C.cal_days(dd, le)
            xe = xd.filter(pl.col('expiration') == e)
            if le == nxt and dte >= 1 and e == nxt:
                # V3 for a 0DTE entry on the next session: the contract LISTED to expire that day (keyed by its listed date)
                for r in xe.select('strike', 'right', 'volume').iter_rows():
                    out_next.append((dd, e, r[0], r[1], int(r[2] or 0)))
            if dte < 1 or dte > 60:
                continue
            K = np.unique(xe['strike'].to_numpy())
            cb, ca, pb, pa = (np.full(K.size, np.nan) for _ in range(4))
            cv, pv = np.zeros(K.size, np.int64), np.zeros(K.size, np.int64)
            ki = np.searchsorted(K, xe['strike'].to_numpy())
            isc = xe['right'].to_numpy() == 'C'
            bid = xe['bid'].to_numpy().astype(float)
            ask = xe['ask'].to_numpy().astype(float)
            vol = xe['volume'].fill_null(0).to_numpy()
            cb[ki[isc]], ca[ki[isc]], cv[ki[isc]] = bid[isc], ask[isc], vol[isc]
            pb[ki[~isc]], pa[ki[~isc]], pv[ki[~isc]] = bid[~isc], ask[~isc], vol[~isc]
            fim = C.forward_im(K, cb, ca, pb, pa)
            T = C.years(dte * 1440)
            if fim is None:
                per_exp[le] = None
                out_exp.append(dict(day=dd, expiry=le, listed=e, dte=dte, Kstar=None, F=None, IM=None, atm_iv=None))
                continue
            Ks, F, IM, _, _ = fim
            aiv = atm_iv(name, K, cb, ca, pb, pa, F, Ks, T)
            out_exp.append(dict(day=dd, expiry=le, listed=e, dte=dte, Kstar=Ks, F=F, IM=IM, atm_iv=aiv if np.isfinite(aiv) else None))
            per_exp[le] = (K, cb, ca, pb, pa, cv, pv, F, IM, Ks, T, aiv, dte)
            for si, (b_, a_) in enumerate(((cb, ca), (pb, pa))):
                st = (b_ > 0) & (a_ > 0) & (a_ >= b_)
                xx = (K - F) / IM if si == 0 else (F - K) / IM
                ok = st & (np.abs(xx) <= 0.5 + 1e-12)
                sp_list += list(((a_ - b_) / ((a_ + b_) / 2))[ok])
        spreads[dd] = np.array(sp_list, np.float32)
        # the multi-day entries: full sessions only
        if dd not in full:
            continue
        for eb, lo, hi, centre in MULTI:
            cands = sorted({ltd[e] for e in exps if ltd[e] is not None and lo <= C.cal_days(dd, ltd[e]) <= hi},
                           key=lambda le: (abs(C.cal_days(dd, le) - centre), le))
            if not cands:
                out_entries.append(dict(day=dd, eb=eb, status='no listed expiry in the bucket'))
                continue
            le = cands[0]
            if le in C.HALF_DAYS:
                out_entries.append(dict(day=dd, eb=eb, expiry=le, status='expires on a half day'))
                continue
            pe = per_exp.get(le)
            if pe is None:
                out_entries.append(dict(day=dd, eb=eb, expiry=le, status='no standing ATM pair'))
                continue
            K, cb, ca, pb, pa, cv, pv, F, IM, Ks, T, aiv, dte = pe
            for si, right, b_, a_, v_ in ((0, 'C', cb, ca, cv), (1, 'P', pb, pa, pv)):
                st = (b_ > 0) & (a_ > 0) & (a_ >= b_)
                xx = (K - F) / IM if si == 0 else (F - K) / IM
                sel = C.select_buckets(K, st, xx)
                for bn in C.BUCKET_NAMES:
                    if bn not in sel:
                        out_entries.append(dict(day=dd, eb=eb, expiry=le, right=right, sb=bn, status='no standing quote in the bucket'))
                        continue
                    i = sel[bn]
                    bid, ask = float(b_[i]), float(a_[i])
                    mid = (bid + ask) / 2
                    iv = float(C.b76_iv(np.array([mid]), F, np.array([K[i]]), T, np.array([si == 0]))[0])
                    de = float(C.b76_delta(F, K[i], T, iv, si == 0)) if np.isfinite(iv) else None
                    out_entries.append(dict(day=dd, eb=eb, expiry=le, right=right, sb=bn, status='ok', strike=float(K[i]),
                                            x=float(xx[i]), bid=bid, ask=ask, mid=mid, spread=(ask - bid) / mid, F=F, IM=IM,
                                            Kstar=Ks, dte=dte, iv=iv if np.isfinite(iv) else None, delta=de,
                                            atm_iv=aiv if np.isfinite(aiv) else None, vol=int(v_[i])))
    return out_days, out_exp, out_next, out_entries, spreads


def inputs_dir(name: str) -> Path:
    return C.WORK / 'eod' / name


def run_pass1(name: str, split_any: str, procs: int = 3):
    t0 = time.time()
    fs = eod_files(name)
    days, exps, nxt, ents, spreads = [], [], [], [], {}
    seen = set()
    with mp.get_context("spawn").Pool(procs) as pool:
        for a, b, c, d, s in pool.imap(pass1_file, [(name, f, split_any) for f in fs], chunksize=2):
            # a trading day stored in two weekly files is taken once, from the first file (in file order)
            new = {x['day'] for x in a} - seen
            seen |= new
            days += [x for x in a if x['day'] in new]; exps += [x for x in b if x['day'] in new]
            nxt += [x for x in c if x[0] in new]; ents += [x for x in d if x['day'] in new]
            spreads.update({k: v for k, v in s.items() if k in new})
    od = inputs_dir(name)
    C.write_parquet(pl.DataFrame(days), od / 'days.parquet')
    C.write_parquet(pl.DataFrame(exps, infer_schema_length=None).with_columns(
        [pl.col(c).cast(pl.Float64) for c in ('Kstar', 'F', 'IM', 'atm_iv')]), od / 'expiries.parquet')
    C.write_parquet(pl.DataFrame(nxt, schema=['day', 'expiry', 'strike', 'right', 'volume'], orient='row'), od / 'nextvol.parquet')
    ed = pl.DataFrame(ents, infer_schema_length=None)
    C.write_parquet(ed.with_columns([pl.col(c).cast(pl.Float64) for c in ('strike', 'x', 'bid', 'ask', 'mid', 'spread', 'F', 'IM',
                                                                          'Kstar', 'iv', 'delta', 'atm_iv') if c in ed.columns]),
                    od / 'entries.parquet')
    with open(od / 'spreads.pkl', 'wb') as fh:
        pickle.dump(spreads, fh)
    print('pass1', name, len(fs), 'files', len(days), 'days', ed.height, 'entry rows', f'{time.time() - t0:.0f}s', flush=True)


# ---- pass 2: the exits ------------------------------------------------------------------------------------------------------------

def file_of_day(name: str) -> dict[str, Path]:
    out = {}
    for f in eod_files(name):
        a, b = f.stem.split('__')
        for d in C.trading_days():
            if a <= d <= b:
                out[d] = str(f)
    return out


def eod_lookup(name: str, req: pl.DataFrame) -> pl.DataFrame:
    """req: (day, listed, strike, right) → the EOD (bid, ask) of those rows"""
    fod = file_of_day(name)
    parts = []
    for f, g in req.with_columns(pl.col('day').replace_strict(fod, default=None).cast(pl.String).alias('_f')).group_by('_f'):
        if f[0] is None:
            continue
        x = load_week(Path(f[0])).rename({'date': 'day', 'expiration': 'listed'}).select('day', 'listed', 'strike', 'right', 'bid', 'ask')
        parts.append(g.drop('_f').join(x, on=['day', 'listed', 'strike', 'right'], how='inner'))
    return pl.concat(parts) if parts else pl.DataFrame(schema={'day': pl.String, 'listed': pl.String, 'strike': pl.Float64,
                                                                 'right': pl.String, 'bid': pl.Float64, 'ask': pl.Float64})


def chain_1558(name: str, E: str, wants: list[tuple[float, str]]):
    """the expiry-day chain's 15:58 bid of each (strike, right) with the 10-minute fallback; None when the chain is not on
    disk"""
    p = C.chain_0dte_path(name, E)
    if p is None:
        return None
    K, Bg, Ag = B0.grid(p)
    out = {}
    for k, right in wants:
        i = np.where(np.abs(K - k) < 1e-6)[0]
        if i.size == 0:
            out[(k, right)] = None
            continue
        si = 0 if right == 'C' else 1
        px, _ = B0.exit_bid(Bg[si, i[0]], Ag[si, i[0]], C.FLAT, C.FLAT - 11)
        out[(k, right)] = (px, '' if px > 0 else 'no bid: $0')
    return out


def run_pass2(name: str, split: str):
    t0 = time.time()
    C.set_split(split)
    od = inputs_dir(name)
    ents = pl.read_parquet(od / 'entries.parquet')
    expi = pl.read_parquet(od / 'expiries.parquet')
    listed_of = {(r['day'], r['expiry']): r['listed'] for r in expi.select('day', 'expiry', 'listed').iter_rows(named=True)}
    cnt = Counter()
    for r in ents.filter(pl.col('status') != 'ok').iter_rows(named=True):
        # a trade not formed has no exit: it is counted in the split of its entry session's month (and name)
        if r['day'] >= first_day(name) and (split == 'hold') == ((name in C.HELD_T) or C.held_month(r['day'])):
            cnt[f"{r['eb']}: {r['status']}"] += 1
    ok = ents.filter(pl.col('status') == 'ok')
    f0 = first_day(name)
    dt = D.table(name)
    rows_daily = dt['rows']
    trades = []
    for r in ok.iter_rows(named=True):
        d, E, eb = r['day'], r['expiry'], r['eb']
        if d < f0:
            continue
        if eb == '1-7':
            ex_day = E
            last_check = C.prev_session(E)
        elif eb == '8-30':
            a5 = C.nth_session_after(d, 5)
            pb = C.prev_session(E)
            ex_day = min(x for x in (a5, pb) if x is not None)
            last_check = ex_day
        else:
            ex_day = C.nth_session_after(d, 10)
            last_check = ex_day
        if ex_day is None or ex_day > C.LAST_DAY:
            cnt[f'{eb}: exit after the data ends'] += 1
            continue
        held = (name in C.HELD_T) or C.window_held(d, ex_day)
        if (split == 'expl') == held:
            continue
        sp = C.spans_split(name, d, ex_day)
        if sp:
            cnt[f'{eb}: spans the split of {sp}'] += 1
            continue
        t = dict(name=name, day=d, m=C.EOD_M, eb=eb, expiry=E, listed=listed_of[(d, E)], strike=r['strike'], right=r['right'],
                 sb=r['sb'], x=r['x'], bid=r['bid'], ask=r['ask'], mid=r['mid'], spread=r['spread'], F=r['F'], IM=r['IM'],
                 Kstar=r['Kstar'], dte=r['dte'], iv=r['iv'], delta=r['delta'], atm_iv=r['atm_iv'], vol=r['vol'], exit_day=ex_day,
                 last_check=last_check)
        S = C.price_at_entry(name, d, C.EOD_M)
        t['S'] = S
        trades.append(t)
    if not trades:
        df = pl.DataFrame()
        C.write_parquet(df, C.WORK / split / 'eod' / f'{name}.parquet')
        C.jdump(dict(name=name, split=split, trades=0, counts=dict(cnt)), C.WORK / split / 'eod' / f'{name}.counts.json')
        print('pass2', name, split, 0, dict(cnt), flush=True)
        return
    # the EOD bids needed: the fixed exit day (8-30, 31-60) and every X1 check day
    req = []
    for i, t in enumerate(trades):
        days = C.sessions_between(t['day'], t['last_check']) if t['last_check'] and t['last_check'] > t['day'] else []
        t['_checks'] = days
        for dd in set(days) | ({t['exit_day']} if t['eb'] != '1-7' else set()):
            req.append((dd, t['listed'], t['strike'], t['right']))
    req = pl.DataFrame(req, schema=['day', 'listed', 'strike', 'right'], orient='row').unique()
    got = eod_lookup(name, req)
    quote = {(a, b, c, d_): (e, f) for a, b, c, d_, e, f in got.iter_rows()}
    # the 1-7 expiry-day chains
    chains = {}
    if name != 'SPXW':
        need = defaultdict(set)
        for t in trades:
            if t['eb'] == '1-7':
                need[t['expiry']].add((t['strike'], t['right']))
        for E, w in need.items():
            chains[E] = chain_1558(name, E, sorted(w))
    spx = C.official_spx()
    out = []
    itm = []
    for t in trades:
        eb = t['eb']
        note = ''
        if eb == '1-7':
            if name == 'SPXW':
                o = spx.get(t['expiry'])
                if o is None:
                    cnt['1-7: no official SPX close at expiry'] += 1
                    continue
                px = max(o - t['strike'], 0.0) if t['right'] == 'C' else max(t['strike'] - o, 0.0)
                fee_out, note = 0.0, 'settled'
            else:
                ch = chains.get(t['expiry'])
                if ch is None:
                    cnt['1-7: no expiry-day chain on disk'] += 1
                    continue
                if ch.get((t['strike'], t['right'])) is None:
                    cnt['1-7: contract not in the expiry-day chain'] += 1
                    continue
                px, note = ch[(t['strike'], t['right'])]
                fee_out = C.fee(name, px)
                if px <= 0:
                    rr = rows_daily.get(t['expiry'])
                    s_ex = rr['close1559'] if rr else None
                    if s_ex is not None and ((t['right'] == 'C' and s_ex > t['strike']) or (t['right'] == 'P' and s_ex < t['strike'])):
                        note = 'no bid: $0 (IN THE MONEY)'
                        itm.append((name, t['day'], eb, t['expiry'], t['right'], t['strike']))
        else:
            q = quote.get((t['exit_day'], t['listed'], t['strike'], t['right']))
            if q is None:
                cnt[f'{eb}: no EOD row for the contract at the exit session'] += 1
                continue
            b_, a_ = q
            px = float(b_) if (b_ is not None and b_ > 0 and a_ is not None and a_ > 0 and a_ >= b_) else 0.0
            fee_out = C.fee(name, px)
            if px <= 0:
                note = 'no bid: $0'
        r_, pnl = C.ret(name, t['ask'], px, fee_out)
        t.update(exit_px=px, exit_fee=fee_out, exit_note=note, r=r_, pnl=pnl)
        # X1
        S = t['S']
        t['x1_def'] = bool(np.isfinite(S))
        t['r_x1'], t['pnl_x1'], t['x1_day'], t['x1_px'] = r_, pnl, None, None
        if t['x1_def']:
            lvl = S + t['IM'] if t['right'] == 'C' else S - t['IM']
            for dd in t['_checks']:
                rr = rows_daily.get(dd)
                v = rr['close1559'] if rr else None
                if v is None:
                    continue
                if (t['right'] == 'C' and v >= lvl) or (t['right'] == 'P' and v <= lvl):
                    q = quote.get((dd, t['listed'], t['strike'], t['right']))
                    if q is None:
                        t['x1_note'] = f'no EOD row at {dd}: fixed exit'
                        break
                    b_, a_ = q
                    p1 = float(b_) if (b_ is not None and b_ > 0 and a_ is not None and a_ > 0 and a_ >= b_) else 0.0
                    t['r_x1'], t['pnl_x1'] = C.ret(name, t['ask'], p1, C.fee(name, p1))
                    t['x1_day'], t['x1_px'] = dd, p1
                    break
        t.pop('_checks')
        out.append(t)
    df = pl.DataFrame(out, infer_schema_length=None)
    df = df.with_columns([pl.col(c).cast(pl.Float64) for c in ('strike', 'x', 'bid', 'ask', 'mid', 'spread', 'F', 'IM', 'Kstar', 'iv',
                                                                'delta', 'atm_iv', 'S', 'exit_px', 'exit_fee', 'r', 'pnl', 'r_x1',
                                                                'pnl_x1', 'x1_px') if c in df.columns])
    C.write_parquet(df, C.WORK / split / 'eod' / f'{name}.parquet')
    C.jdump(dict(name=name, split=split, trades=df.height, counts=dict(cnt), itm_zero=itm), C.WORK / split / 'eod' / f'{name}.counts.json')
    print('pass2', name, split, df.height, 'trades', dict(cnt), f'{time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    split = sys.argv[1]
    C.set_split(split)
    args = [a for a in sys.argv[2:] if not a.startswith('--')]
    names = args or [t for t in C.TICKERS if (t not in C.HELD_T) or split == 'hold']
    if split == 'expl':
        assert not set(names) & set(C.HELD_T)
    for nm in names:
        if '--pass2' not in sys.argv:
            run_pass1(nm, split)
        if '--pass1' not in sys.argv:
            run_pass2(nm, split)
