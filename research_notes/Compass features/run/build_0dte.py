"""
build_0dte.py — the 0DTE base trades (prereg 2.3–2.6) with every value the screen needs that the chain and the bars give:
the entry (ask, bid, spread, x, IV, delta), the fixed exit (15:58 bid; SPXW: intrinsic on the official SPX close), the X1
and X3 exits (prereg 3.2, family 5), the D6 and D7 directions and the ES3 distance. One parquet per name and split in
$SP/features_work/<split>/0dte/<name>.parquet, plus the counts of trades not formed.

A split decides which name-days are opened: 'expl' = an exploration ticker on a session outside the held-out months;
'hold' = a held-out ticker (every session) or an exploration ticker on a held-out-month session.

  POLARS_MAX_THREADS=1 python3 -I build_0dte.py expl [names...]
"""
from __future__ import annotations

import math
import sys
import time
from collections import Counter
import multiprocessing as mp
from pathlib import Path

import numpy as np
import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402
import daily as D  # noqa: E402

SQ2PI = math.sqrt(2.0 / math.pi)
SPAN0 = {'SPY': '2022-11-11', 'QQQ': '2022-11-11', 'SPXW': '2022-05-13', 'IWM': '2024-04-19'}


def name_days(name: str, split: str) -> list[str]:
    """the full sessions on which a 0DTE base trade can be formed for this name and split"""
    days = []
    full = set(C.sessions())
    for d in C.chain_days(name):
        if d not in full or d > C.LAST_DAY:
            continue
        if name in SPAN0 and d < SPAN0[name]:
            continue
        if name in C.SINGLES and d < '2017-06-02':
            continue
        held = (name in C.HELD_T) or C.held_month(d)
        if (split == 'expl') != (not held):
            continue
        days.append(d)
    return days


def stands(b, a):
    return (b > 0) & (a > 0) & (a >= b)


def exit_bid(B, A, X, m0):
    """the bid of row X if it stands, else the last standing bid within the 10 minutes before X (after the entry), else 0"""
    for j in range(X, max(X - 10, m0 + 1) - 1, -1):
        if stands(B[j], A[j]):
            return float(B[j]), j
    return 0.0, X


def grid(p: Path):
    ch = pl.read_parquet(p, columns=['timestamp', 'strike', 'right', 'bid', 'ask']).with_columns(C.mcol().alias('m'))
    ch = ch.filter((pl.col('m') >= 0) & (pl.col('m') <= 390)).with_columns(pl.col('bid').fill_null(float('nan')),
                                                                             pl.col('ask').fill_null(float('nan')))
    K = np.unique(ch['strike'].to_numpy())
    ki = np.searchsorted(K, ch['strike'].to_numpy())
    side = (ch['right'].to_numpy() == 'PUT').astype(int)
    m = ch['m'].to_numpy()
    Bg = np.full((2, K.size, C.NMIN), np.nan)
    Ag = np.full((2, K.size, C.NMIN), np.nan)
    Bg[side, ki, m] = ch['bid'].to_numpy().astype(float)
    Ag[side, ki, m] = ch['ask'].to_numpy().astype(float)
    return K, Bg, Ag


def build_day(args):
    name, d, split = args
    C.set_split(split)
    cnt = Counter()
    rows = []
    p = C.chain_0dte_path(name, d)
    if p is None:
        cnt['day: no chain'] += 1
        return rows, cnt, []
    K, Bg, Ag = grid(p)
    b = C.bars(name, d)
    official = None
    if name == 'SPXW':
        official = C.official_spx().get(d)
        if official is None:
            cnt['day: no official SPX close (SPXW not formed)'] += 1
            return rows, cnt, []
    h = l = c = None
    if b is not None:
        h, l, c = b
    tab = D.table(name)['rows']
    r0 = tab.get(d)
    orh = r0['or_high'] if r0 else None
    orl = r0['or_low'] if r0 else None
    ph, plo = D.prior_hl(name, d)
    rv = D.rv20_through(name, C.prev_session(d))
    notes = []
    for m in C.ENTRY_M:
        fim = C.forward_im(K, Bg[0, :, m], Ag[0, :, m], Bg[1, :, m], Ag[1, :, m])
        if fim is None:
            cnt['entry: no standing ATM pair'] += 1
            continue
        Ks, F, IM, _, _ = fim
        S = C.price_at_entry(name, d, m)
        T = C.years(390 - m)
        d6 = 0
        if m >= C.mi('10:15') and orh is not None and np.isfinite(S):
            d6 = 1 if S > orh else (-1 if S < orl else 0)
        d7 = 0
        if np.isfinite(S) and np.isfinite(ph):
            d7 = 1 if S > ph else (-1 if S < plo else 0)
        rm = S * rv * math.sqrt((390 - m) / 390.0) * SQ2PI if (np.isfinite(S) and np.isfinite(rv)) else float('nan')
        xrm = rm / IM if np.isfinite(rm) else float('nan')
        for si, right in ((0, 'C'), (1, 'P')):
            Bm, Am = Bg[si, :, m], Ag[si, :, m]
            st = stands(Bm, Am)
            x = (K - F) / IM if si == 0 else (F - K) / IM
            sel = C.select_buckets(K, st, x)
            for bn in C.BUCKET_NAMES:
                if bn not in sel:
                    cnt['contract: no standing quote in the bucket'] += 1
                    continue
                i = sel[bn]
                k = float(K[i])
                bid, ask = float(Bm[i]), float(Am[i])
                mid = (bid + ask) / 2.0
                B, A = Bg[si, i], Ag[si, i]
                # the fixed exit
                if name == 'SPXW':
                    ex_px = max(official - k, 0.0) if si == 0 else max(k - official, 0.0)
                    ex_fee, ex_m, ex_note = 0.0, 390, 'settled'
                else:
                    ex_px, ex_m = exit_bid(B, A, C.FLAT, m)
                    ex_fee = C.fee(name, ex_px)
                    ex_note = '' if ex_px > 0 else 'no bid: $0'
                    if ex_px <= 0 and c is not None and np.isfinite(c[C.FLAT - 1]):
                        s_ex = c[C.FLAT - 1]
                        if (si == 0 and s_ex > k) or (si == 1 and s_ex < k):
                            ex_note = 'no bid: $0 (IN THE MONEY)'
                            notes.append((name, d, C.mtxt(m), right, k, 'fixed'))
                r, pnl = C.ret(name, ask, ex_px, ex_fee)
                row = dict(name=name, day=d, m=m, eb='0DTE', expiry=d, strike=k, right=right, sb=bn, x=float(x[i]),
                           bid=bid, ask=ask, mid=mid, spread=(ask - bid) / mid, F=F, IM=IM, Kstar=Ks, S=S,
                           exit_day=d, exit_m=ex_m, exit_px=ex_px, exit_fee=ex_fee, exit_note=ex_note, r=r, pnl=pnl,
                           d6=d6, d7=d7, xrm=xrm, rv20=rv)
                # X1: the implied move as a target
                lvl = S + IM if si == 0 else S - IM
                row['x1_def'] = bool(np.isfinite(S) and c is not None)
                hit = None
                if row['x1_def']:
                    if name == 'SPXW':
                        for pm in range(m + 1, C.FLAT + 1):
                            v = c[pm]
                            if np.isfinite(v) and ((si == 0 and v >= lvl) or (si == 1 and v <= lvl)):
                                hit = pm
                                break
                    else:
                        for bm in range(m, C.FLAT):
                            v = c[bm]
                            if np.isfinite(v) and ((si == 0 and v >= lvl) or (si == 1 and v <= lvl)):
                                hit = bm + 1
                                break
                if hit is not None:
                    px1, _ = exit_bid(B, A, hit, m)
                    f1 = C.fee(name, px1)
                    row['r_x1'], row['pnl_x1'] = C.ret(name, ask, px1, f1)
                    row['x1_m'], row['x1_px'] = hit, px1
                else:
                    row['r_x1'], row['pnl_x1'], row['x1_m'], row['x1_px'] = r, pnl, None, None
                # X3: entries before 14:00 sold at the 14:00 bid
                if m < C.X3_M:
                    px3, _ = exit_bid(B, A, C.X3_M, m)
                    row['r_x3'], row['pnl_x3'] = C.ret(name, ask, px3, C.fee(name, px3))
                    row['x3_px'] = px3
                else:
                    row['r_x3'] = row['pnl_x3'] = row['x3_px'] = None
                # the IV and delta (ES4), solved from the mid
                rows.append(row)
    if rows:
        k_ = np.array([r['strike'] for r in rows if True])
        F_ = np.array([r['F'] for r in rows])
        mid_ = np.array([r['mid'] for r in rows])
        T_ = np.array([C.years(390 - r['m']) for r in rows])
        ic = np.array([r['right'] == 'C' for r in rows])
        iv = C.b76_iv(mid_, F_, k_, T_, ic)
        de = C.b76_delta(F_, k_, T_, np.where(np.isfinite(iv), iv, 0.2), ic)
        for r, v, dl in zip(rows, iv, de):
            r['iv'] = float(v) if np.isfinite(v) else None
            r['delta'] = float(dl) if np.isfinite(v) else None
    if C.staged(p):
        cnt['day: chain read from the fetch staging'] += 1
    return rows, cnt, notes


SCHEMA_FLOAT = ('strike', 'x', 'bid', 'ask', 'mid', 'spread', 'F', 'IM', 'Kstar', 'S', 'exit_px', 'exit_fee', 'r', 'pnl', 'xrm',
                'rv20', 'r_x1', 'pnl_x1', 'x1_px', 'r_x3', 'pnl_x3', 'x3_px', 'iv', 'delta')


def frame(rows: list[dict]) -> pl.DataFrame:
    df = pl.DataFrame(rows, infer_schema_length=None)
    return df.with_columns([pl.col(c).cast(pl.Float64) for c in SCHEMA_FLOAT if c in df.columns])


def run(split: str, names: list[str], procs: int = 3):
    C.set_split(split)
    out_dir = C.WORK / split / '0dte'
    for name in names:
        t0 = time.time()
        days = name_days(name, split)
        cnt = Counter()
        rows, notes = [], []
        with mp.get_context("spawn").Pool(procs) as pool:
            for rr, cc, nn in pool.imap(build_day, [(name, d, split) for d in days], chunksize=4):
                rows += rr
                cnt.update(cc)
                notes += nn
        df = frame(rows) if rows else pl.DataFrame()
        C.write_parquet(df, out_dir / f'{name}.parquet')
        C.jdump(dict(name=name, split=split, days=len(days), first=days[0] if days else None, last=days[-1] if days else None,
                     trades=df.height, counts=dict(cnt), itm_zero=notes), out_dir / f'{name}.counts.json')
        print(split, name, len(days), 'days', df.height, 'trades', dict(cnt), f'{time.time() - t0:.0f}s', flush=True)


if __name__ == '__main__':
    split = sys.argv[1]
    names = sys.argv[2:] or [t for t in C.TICKERS if (t not in C.HELD_T) or split == 'hold']
    if split == 'expl':
        assert not set(names) & set(C.HELD_T)
    run(split, names)
