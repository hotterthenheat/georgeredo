"""Compass Modules 3/4 audit, step 1: build the two 0DTE entry universes and store every trade's minute path.

Universe A (sweep fade): between bars stamped 10:00 and 11:59 NY (t = 600..719; a bar stamped t closes at t+1), the first
1-minute bar whose high is >= 2 bps above the 09:30-09:59 range high (bars stamped 09:30..09:59) and whose close is back
below that high -> buy the nearest out-of-the-money same-day PUT at the ask quoted at the bar's close (quote minute = bar
minute + 1). Mirror for the range low -> CALL. First such event a session per side.
Universe B (random minute): one random quote minute per session in [10:00, 15:00] (seed 20261016), CALL or PUT at random,
nearest OTM, bought at the ask.
Products SPY, QQQ, IWM (own 1-minute bars), SPXW (SPX index prints for the spot and strike choice; SPY bars x the SPX/SPY
ratio at 10:00 as the stated proxy for SPX bar highs/lows and the morning range).

Minute m = 0 is 09:30; close_m = 390 (210 on a half day, found from SPY's bars). Quote at minute m is paired with the bar
stamped m-1 (the bar that closes at m). Spot at quote minute m = close of bar stamped m-1 (ETF) or the SPX print at m.
A quote counts when bid and ask are present, ask >= bid >= 0 and ask > 0.
Paths are stored as fixed 391-long arrays indexed by quote minute (NaN where no quote), from the entry minute to the close.
settle = intrinsic at the closing spot.

  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I extract.py [PRODUCT ...]
writes out/paths_<PRODUCT>.parquet
"""
import os, sys, json, time
import numpy as np, polars as pl

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
UNDERLYING = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
SEED = 20261016
NMIN = 391
A_FIRST, A_LAST = 30, 149       # bars stamped 10:00..11:59
B_FIRST, B_LAST = 30, 330       # quote minutes 10:00..15:00
BUFFER_BPS = 2.0

def mcol(col='timestamp'):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

def bars(u, d):
    """ETF bars by bar minute (stamp), with open/high/low/close; SPX: prints by minute as close (no high/low)."""
    if u == 'SPX':
        p = pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).with_columns(mcol().alias('m'))
        return p.filter(pl.col('price').is_not_null()).select('m', pl.col('price').alias('close'))
    p = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', u, f'{d}.parquet'), columns=['timestamp', 'open', 'high', 'low', 'close'])
    return p.with_columns(mcol().alias('m')).filter(pl.col('close').is_not_null()).select('m', 'open', 'high', 'low', 'close').sort('m')

def to_arr(df, key, val, n=NMIN):
    a = np.full(n, np.nan); k = df[key].to_numpy(); v = df[val].to_numpy().astype(float)
    ok = (k >= 0) & (k < n); a[k[ok]] = v[ok]; return a

def session(root, d, rng):
    u = UNDERLYING[root]
    spy = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet'), columns=['timestamp', 'close']).filter(pl.col('close').is_not_null())
    if spy.height == 0: return []
    half = spy['timestamp'].max().hour < 15
    close_m = 210 if half else 390
    # bar arrays indexed by bar stamp minute
    if u == 'SPX':
        sp = bars('SPX', d)
        if sp.height < 100: return []
        spot = to_arr(sp, 'm', 'close')                      # spot at quote minute m = print at m
        spyb = bars('SPY', d)
        spy_close_q = np.full(NMIN, np.nan); spy_close_q[1:] = to_arr(spyb, 'm', 'close')[:-1]   # SPY close at quote minute
        # ratio at 10:00 (quote minute 30): SPX print / SPY close
        r_ok = ~np.isnan(spot[25:35]) & ~np.isnan(spy_close_q[25:35])
        if r_ok.sum() == 0: return []
        ratio = np.nanmedian(spot[25:35][r_ok] / spy_close_q[25:35][r_ok])
        bhigh = to_arr(spyb, 'm', 'high') * ratio; blow = to_arr(spyb, 'm', 'low') * ratio; bclose = to_arr(spyb, 'm', 'close') * ratio
        proxy = True
    else:
        b = bars(u, d)
        if b.height < 100: return []
        bhigh = to_arr(b, 'm', 'high'); blow = to_arr(b, 'm', 'low'); bclose = to_arr(b, 'm', 'close')
        spot = np.full(NMIN, np.nan); spot[1:] = bclose[:-1]  # spot at quote minute m = close of bar stamped m-1
        proxy = False
    # morning range: bars stamped 0..29 (09:30..09:59)
    rh = np.nanmax(bhigh[0:30]) if np.any(~np.isnan(bhigh[0:30])) else np.nan
    rl = np.nanmin(blow[0:30]) if np.any(~np.isnan(blow[0:30])) else np.nan
    vix = pl.read_parquet(os.path.join(RAW, 'data', 'index', 'VIX', f'{d}.parquet')).with_columns(mcol().alias('m'))
    vixa = to_arr(vix.filter(pl.col('price').is_not_null()), 'm', 'price')
    # chain
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'))
    c = c.with_columns(mcol().alias('m'))
    ok = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0) & (pl.col('ask') > 0)
    c = c.filter((pl.col('m') >= 1) & (pl.col('m') <= close_m) & ok)
    if c.height == 0: return []
    entries = []
    # Universe A
    if not (np.isnan(rh) or np.isnan(rl)):
        for side, lvl in (('PUT', rh), ('CALL', rl)):
            for bm in range(A_FIRST, A_LAST + 1):
                if np.isnan(bhigh[bm]) or np.isnan(bclose[bm]): continue
                if side == 'PUT' and bhigh[bm] >= lvl * (1 + BUFFER_BPS / 1e4) and bclose[bm] < lvl:
                    entries.append(('A', side, bm + 1, lvl)); break
                if side == 'CALL' and blow[bm] <= lvl * (1 - BUFFER_BPS / 1e4) and bclose[bm] > lvl:
                    entries.append(('A', side, bm + 1, lvl)); break
    # Universe B
    em = int(rng.integers(B_FIRST, B_LAST + 1)); side = 'CALL' if rng.integers(0, 2) == 1 else 'PUT'
    entries.append(('B', side, em, np.nan))
    rows = []
    for uni, side, em, lvl in entries:
        if em > close_m - 2 or np.isnan(spot[em]): continue
        s = spot[em]
        q = c.filter((pl.col('m') == em) & (pl.col('right') == side))
        q = q.filter(pl.col('strike') < s) if side == 'PUT' else q.filter(pl.col('strike') > s)
        if q.height == 0: continue
        k = float(q['strike'].max() if side == 'PUT' else q['strike'].min())
        path = c.filter((pl.col('strike') == k) & (pl.col('right') == side)).sort('m')
        if path.height < 2: continue
        bid = to_arr(path, 'm', 'bid'); ask = to_arr(path, 'm', 'ask'); bs = to_arr(path, 'm', 'bid_size'); asz = to_arr(path, 'm', 'ask_size')
        if np.isnan(ask[em]) or ask[em] <= 0: continue
        sc = spot[close_m] if not np.isnan(spot[close_m]) else spot[~np.isnan(spot)][-1]
        settle = max(sc - k, 0.0) if side == 'CALL' else max(k - sc, 0.0)
        rows.append(dict(product=root, session=d, universe=uni, side=side, strike=k, entry_m=em, level=lvl, spot_entry=s, entry_ask=float(ask[em]),
                         entry_bid=float(bid[em]), entry_bid_size=float(bs[em]), entry_ask_size=float(asz[em]), vix=float(vixa[em]) if not np.isnan(vixa[em]) else float(np.nanmax(vixa[max(0, em-5):em+1])) if np.any(~np.isnan(vixa[max(0, em-5):em+1])) else np.nan,
                         close_m=close_m, half_day=half, spot_close=float(sc), settle=settle, spx_proxy=proxy, range_high=rh, range_low=rl,
                         quotes_after=int(np.sum(~np.isnan(bid[em+1:close_m+1]))),
                         bid=bid.astype(np.float32).tolist(), ask=ask.astype(np.float32).tolist(), bid_size=bs.astype(np.float32).tolist(), ask_size=asz.astype(np.float32).tolist(),
                         spot=spot.astype(np.float32).tolist(), bar_high=bhigh.astype(np.float32).tolist(), bar_low=blow.astype(np.float32).tolist()))
    return rows

if __name__ == '__main__':
    prods = sys.argv[1:] or ['SPY', 'QQQ', 'IWM', 'SPXW']
    for root in prods:
        rng = np.random.default_rng(SEED + sum(ord(ch) for ch in root))   # one stream per product, fixed seed
        days = sorted(f[:-8] for f in os.listdir(os.path.join(RAW, 'data_full', 'chains', root)) if f.endswith('.parquet'))
        if os.environ.get('LIMIT'): days = days[:int(os.environ['LIMIT'])]
        t0 = time.time(); rows = []; miss = 0
        for i, d in enumerate(days):
            try:
                rows += session(root, d, rng)
            except FileNotFoundError as e:
                miss += 1
            if i % 100 == 0: print(root, i, len(days), len(rows), f'{time.time()-t0:.0f}s', flush=True)
        df = pl.DataFrame(rows, infer_schema_length=None)
        df.write_parquet(os.path.join(OUT, f'paths_{root}.parquet'), compression='zstd')
        print(root, 'sessions', len(days), 'missing files', miss, 'trades', df.height, df.group_by('universe', 'side').len().sort('universe', 'side').rows(), f'{time.time()-t0:.0f}s', flush=True)
