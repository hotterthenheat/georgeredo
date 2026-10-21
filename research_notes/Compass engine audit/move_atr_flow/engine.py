"""Compass audit, modules 7/8/11: one pass over each 0DTE session that writes four tables a product.

Conventions (step1): minute m = 0 is 09:30; an ETF 1-minute bar stamped t closes at t+1, so the spot at minute m is the
close of the bar stamped m-1; an SPX print stamped m is the price at m. Quotes stamped m are the NBBO at m, read from
09:31. The close is minute 390. Half days (close 13:00) are skipped. Fees $0.65 a contract each way, none on a worthless
expiry. Prices per share; x100 a contract.

Tables (out/<table>_<PRODUCT>.parquet):
  scans   : at each scan minute (09:35, 10:00, 10:30 ... 15:30, 15:50): spot, ATM straddle mid, the remaining day's
            high/low/close (minute closes, and ETF bar highs/lows), the king proxy (the strike with the most same-day
            contract volume so far, calls+puts, bars stamped before the scan) and its distance.
  touches : for each scan x multiplier (1.0, 1.2533) x side: the first minute the spot reaches spot +/- M, the spot
            15/30/60 minutes later and at the close, the day's range position at the touch, and the fade trade: the
            nearest OTM 0DTE put (upper touch) or call (lower touch) bought at the ask at the touch minute, sold at the
            bid on a 50% trailing stop, else at 15:58 (and the hold-to-15:58 variant).
  flow    : every minute m (bars stamped <= m-1 only): buy-side and sell-side premium (volume x close x 100) of calls
            and of puts over the last 1, 5, 15 bars, a bar's side judged by its close against the mean of the mid at its
            start and end (as step5/volume.py), and the spot at m, m+5, m+15, m+30 (clamped to the close).
  sweeps  : (ETF products) each 1-minute bar whose high exceeds the running session high by >= 2 bps (or low below the
            running low) and closes back inside; the fade and the breakout trade entered at the next minute's quotes.
  python3 -I engine.py SPY [first_date] [last_date]
"""
import datetime as dt, os, sys, time
import numpy as np, polars as pl

RAW = os.environ.get('RAW', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad/theta')
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
UNDERLYING = {'SPY': 'SPY', 'QQQ': 'QQQ', 'IWM': 'IWM', 'SPXW': 'SPX'}
SCANS = [5, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360, 380]
MULTS = [1.0, 1.2533]
FEE = 0.65; HOLD_END = 388; CLOSE_M = 390; TRAIL = 0.5; SWEEP_BPS = 2e-4

def minute_of(col):
    return (pl.col(col).dt.hour().cast(pl.Int32) * 60 + pl.col(col).dt.minute().cast(pl.Int32)) - 570

def spot_series(u, d):
    if u == 'SPX':
        p = pl.read_parquet(os.path.join(RAW, 'data', 'index', 'SPX', f'{d}.parquet')).rename({'price': 'px'}).with_columns(minute_of('timestamp').alias('m'))
        bars = None
    else:
        b = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', u, f'{d}.parquet'), columns=['timestamp', 'open', 'high', 'low', 'close']).with_columns(minute_of('timestamp').alias('j'))
        bars = b.filter(pl.col('close').is_not_null() & (pl.col('j') >= 0) & (pl.col('j') < CLOSE_M)).select('j', 'open', 'high', 'low', 'close').sort('j')
        p = b.select(pl.col('close').alias('px'), (pl.col('j') + 1).alias('m'))
    p = p.filter(pl.col('px').is_not_null() & (pl.col('m') >= 0) & (pl.col('m') <= CLOSE_M)).select('m', 'px').sort('m')
    return p, bars

def trades(q, E, hold_end=HOLD_END):
    """E: id, e (entry minute), strike, right. Buy at the ask at e; sell at the bid on the first minute after e where the
    bid is under TRAIL x the highest bid since e, else at the last quote at or before hold_end. Also the hold variant."""
    if E.height == 0: return None
    k = ['strike', 'right']
    j = E.join(q.filter(pl.col('m') <= hold_end), on=k, how='inner').filter(pl.col('m') >= pl.col('e')).sort('id', 'm')
    j = j.with_columns(pl.col('bid').cum_max().over('id').alias('peak'),
                       (pl.col('m') == pl.col('e')).alias('is_e'))
    ent = j.filter(pl.col('is_e')).select('id', pl.col('ask').alias('entry_ask'), pl.col('bid').alias('entry_bid'))
    j = j.join(ent, on='id', how='inner').filter(pl.col('entry_ask') > 0)
    j = j.with_columns(((pl.col('m') > pl.col('e')) & (pl.col('peak') > 0) & (pl.col('bid') < TRAIL * pl.col('peak'))).alias('stop'))
    g = j.group_by('id').agg(
        pl.col('entry_ask').first(), pl.col('entry_bid').first(),
        pl.col('m').filter(pl.col('stop')).first().alias('stop_m'), pl.col('bid').filter(pl.col('stop')).first().alias('stop_bid'),
        pl.col('m').last().alias('last_m'), pl.col('bid').last().alias('last_bid'), pl.col('bid').max().alias('max_bid'),
        pl.col('m').get(pl.col('bid').arg_max()).alias('max_bid_m'))
    g = g.with_columns(pl.col('stop_m').is_not_null().alias('stopped'),
                       pl.coalesce('stop_m', 'last_m').alias('exit_m'), pl.coalesce('stop_bid', 'last_bid').alias('exit_bid'))
    pnl = lambda xb: (xb - pl.col('entry_ask')) * 100 - FEE - pl.when(xb > 0).then(FEE).otherwise(0.0)
    g = g.with_columns(pnl(pl.col('exit_bid')).alias('pnl_trail'), pnl(pl.col('last_bid')).alias('pnl_hold'))
    g = g.with_columns((pl.col('pnl_trail') / (pl.col('entry_ask') * 100)).alias('ret_trail'), (pl.col('pnl_hold') / (pl.col('entry_ask') * 100)).alias('ret_hold'))
    return g

def nearest_otm(q, when, side_right):
    """when: id, t, px. The nearest OTM strike of side_right quoted at t: the highest put strike under px / lowest call strike over px."""
    qq = q.filter(pl.col('right') == side_right).select('strike', 'm', 'ask').rename({'m': 't'})
    j = when.join(qq, on='t', how='inner').filter(pl.col('ask') > 0)
    j = j.filter((pl.col('strike') < pl.col('px')) if side_right == 'PUT' else (pl.col('strike') > pl.col('px')))
    agg = pl.col('strike').max() if side_right == 'PUT' else pl.col('strike').min()
    return j.group_by('id').agg(agg.alias('strike')).with_columns(pl.lit(side_right).alias('right'))

def session(root, d):
    u = UNDERLYING[root]
    spy = pl.read_parquet(os.path.join(RAW, 'data', 'underlying', 'SPY', f'{d}.parquet'), columns=['timestamp', 'close']).filter(pl.col('close').is_not_null())
    if spy['timestamp'].max().hour < 15: return None   # half day: skipped
    sp, bars = spot_series(u, d)
    if sp.height < 300: return None
    px = dict(zip(sp['m'].to_list(), sp['px'].to_list()))
    close_px = px[max(px)]
    c = pl.read_parquet(os.path.join(RAW, 'data_full', 'chains', root, f'{d}.parquet'), columns=['timestamp', 'strike', 'right', 'bid', 'ask']).with_columns(minute_of('timestamp').alias('m')).drop('timestamp')
    two = pl.col('bid').is_not_null() & pl.col('ask').is_not_null() & (pl.col('ask') >= pl.col('bid')) & (pl.col('bid') >= 0)
    q = c.filter(two & (pl.col('m') >= 1) & (pl.col('m') <= CLOSE_M)).with_columns(((pl.col('bid') + pl.col('ask')) / 2).alias('mid'))
    # ---- contract bars (the +/-2% band): premium by side a bar, and volume by strike
    f = os.path.join(RAW, 'data', 'ohlc', root, f'{d}.parquet')
    b = pl.read_parquet(f, columns=['timestamp', 'strike', 'right', 'close', 'volume']).with_columns(minute_of('timestamp').alias('j')).drop('timestamp') if os.path.exists(f) else None
    flow = None; kings = None
    if b is not None and b.height:
        b = b.filter((pl.col('j') >= 0) & (pl.col('j') < CLOSE_M) & (pl.col('volume') > 0))
        mids = q.select('strike', 'right', 'm', 'mid')
        b = b.join(mids.rename({'m': 'j', 'mid': 'mid0'}), on=['strike', 'right', 'j'], how='left') \
             .join(mids.with_columns((pl.col('m') - 1).alias('j')).drop('m').rename({'mid': 'mid1'}), on=['strike', 'right', 'j'], how='left')
        b = b.with_columns(((pl.col('mid0') + pl.col('mid1')) / 2).alias('mid_bar'), (pl.col('volume') * pl.col('close') * 100).alias('prem'))
        b = b.with_columns(pl.when(pl.col('mid_bar').is_null()).then(0).when(pl.col('close') > pl.col('mid_bar') + 1e-9).then(1).when(pl.col('close') < pl.col('mid_bar') - 1e-9).then(-1).otherwise(0).alias('side'))
        per = b.group_by('j').agg(
            pl.col('prem').filter((pl.col('right') == 'CALL') & (pl.col('side') == 1)).sum().alias('cb'),
            pl.col('prem').filter((pl.col('right') == 'CALL') & (pl.col('side') == -1)).sum().alias('cs'),
            pl.col('prem').filter((pl.col('right') == 'PUT') & (pl.col('side') == 1)).sum().alias('pb'),
            pl.col('prem').filter((pl.col('right') == 'PUT') & (pl.col('side') == -1)).sum().alias('ps'),
            pl.col('prem').filter(pl.col('right') == 'CALL').sum().alias('ct'), pl.col('prem').filter(pl.col('right') == 'PUT').sum().alias('pt'),
            pl.col('volume').sum().alias('vol'))
        full = pl.DataFrame({'j': pl.int_range(0, CLOSE_M, eager=True).cast(pl.Int32)}).join(per, on='j', how='left').fill_null(0).sort('j')
        cols = ['cb', 'cs', 'pb', 'ps', 'ct', 'pt', 'vol']
        full = full.with_columns([pl.col(x).rolling_sum(w, min_samples=1).alias(f'{x}_{w}') for x in cols for w in (1, 5, 15)])
        # known at minute m = sums of bars stamped <= m-1
        flow = full.with_columns((pl.col('j') + 1).alias('m')).drop(cols + ['j'])
        spx = pl.DataFrame({'m': list(px.keys()), 'px': list(px.values())}).with_columns(pl.col('m').cast(pl.Int32))
        flow = flow.join(spx, on='m', how='inner')
        for k_ in (5, 15, 30):
            flow = flow.join(spx.with_columns((pl.col('m') - k_).alias('m')).rename({'px': f'px_f{k_}'}), on='m', how='left')
        flow = flow.with_columns([pl.col(f'px_f{k_}').fill_null(close_px) for k_ in (5, 15, 30)]).with_columns(pl.lit(d).alias('session'))
        # king proxy: cumulative strike volume (calls + puts) from bars stamped <= scan-1
        sv = b.group_by('strike', 'j').agg(pl.col('volume').sum().alias('v')).sort('j')
        rows = []
        for s in SCANS:
            t = sv.filter(pl.col('j') <= s - 1).group_by('strike').agg(pl.col('v').sum()).sort('v', 'strike', descending=[True, False])
            if t.height: rows.append(dict(m_scan=s, king=float(t['strike'][0]), king_vol=int(t['v'][0]), king2=float(t['strike'][1]) if t.height > 1 else None, tot_vol=int(t['v'].sum())))
        kings = pl.DataFrame(rows) if rows else None
    # ---- scans: the ATM straddle and the remaining day
    srows = []
    for s in SCANS:
        if s not in px: continue
        spot = px[s]
        at = q.filter(pl.col('m') == s).filter(pl.col('ask') > 0)
        cl = at.filter(pl.col('right') == 'CALL').select('strike', pl.col('mid').alias('cm'), pl.col('bid').alias('cbid'), pl.col('ask').alias('cask'))
        pt = at.filter(pl.col('right') == 'PUT').select('strike', pl.col('mid').alias('pm'), pl.col('bid').alias('pbid'), pl.col('ask').alias('pask'))
        both = cl.join(pt, on='strike', how='inner').with_columns((pl.col('strike') - spot).abs().alias('dist')).sort('dist', 'strike')
        if both.height == 0: continue
        r = both.row(0, named=True)
        rem = sp.filter(pl.col('m') > s)
        if rem.height == 0: continue
        o = dict(session=d, m_scan=s, spot=spot, atm=r['strike'], call_mid=r['cm'], put_mid=r['pm'], straddle=r['cm'] + r['pm'], straddle_ask=r['cask'] + r['pask'], straddle_bid=r['cbid'] + r['pbid'],
                 rem_high=float(rem['px'].max()), rem_low=float(rem['px'].min()), close=close_px, prior=None)
        if bars is not None:
            rb = bars.filter(pl.col('j') >= s)
            o['rem_high_bar'] = float(rb['high'].max()); o['rem_low_bar'] = float(rb['low'].min())
            dy = bars.filter(pl.col('j') < s)
            o['day_high'] = float(dy['high'].max()) if dy.height else spot; o['day_low'] = float(dy['low'].min()) if dy.height else spot
        else:
            o['rem_high_bar'] = None; o['rem_low_bar'] = None
            dy = sp.filter(pl.col('m') <= s); o['day_high'] = float(dy['px'].max()); o['day_low'] = float(dy['px'].min())
        srows.append(o)
    scans = pl.DataFrame(srows, infer_schema_length=None)
    if kings is not None: scans = scans.join(kings, on='m_scan', how='left')
    # ---- touches of spot +/- mult x straddle after each scan
    trows = []
    ms = sp['m'].to_numpy(); pxs = sp['px'].to_numpy()
    for o in srows:
        s = o['m_scan']; spot = o['spot']
        after = ms > s
        for mult in MULTS:
            M = mult * o['straddle']
            for side, hit in (('up', pxs >= spot + M), ('down', pxs <= spot - M)):
                idx = np.flatnonzero(after & hit)
                if len(idx) == 0: continue
                i = idx[0]; t = int(ms[i]); pt_ = float(pxs[i])
                def at_(k):
                    mm = min(t + k, CLOSE_M)
                    return px.get(mm, close_px)
                dh = max(float(pxs[(ms <= t)].max()), pt_); dl = min(float(pxs[(ms <= t)].min()), pt_)
                trows.append(dict(session=d, m_scan=s, mult=mult, side=side, spot_scan=spot, M=M, t=t, px_t=pt_, px_15=at_(15), px_30=at_(30), px_60=at_(60), close=close_px,
                                  range_pos=(pt_ - dl) / (dh - dl) if dh > dl else 0.5, day_high_t=dh, day_low_t=dl))
    touches = pl.DataFrame(trows, infer_schema_length=None) if trows else None
    if touches is not None:
        touches = touches.with_row_index('id')
        tradable = touches.filter(pl.col('t') <= HOLD_END - 2)
        ks = []
        for side, rt in (('up', 'PUT'), ('down', 'CALL')):
            w = tradable.filter(pl.col('side') == side).select('id', 't', pl.col('px_t').alias('px'))
            if w.height: ks.append(nearest_otm(q, w, rt))
        if ks:
            E = pl.concat(ks).join(tradable.select('id', pl.col('t').alias('e')), on='id')
            T = trades(q, E)
            if T is not None:
                touches = touches.join(E.select('id', 'strike', 'right'), on='id', how='left').join(T, on='id', how='left')
        touches = touches.drop('id')
    # ---- sweeps (ETF bars): bar high >= running high x (1 + 2 bps) and close <= running high (and the mirror)
    sweeps = None
    if bars is not None:
        bb = bars.with_columns(pl.col('high').cum_max().shift(1).alias('run_high'), pl.col('low').cum_min().shift(1).alias('run_low'))
        bb = bb.filter((pl.col('j') >= 15) & (pl.col('j') <= HOLD_END - 4))
        up = bb.filter((pl.col('high') >= pl.col('run_high') * (1 + SWEEP_BPS)) & (pl.col('close') <= pl.col('run_high'))).select('j', pl.col('run_high').alias('level'), pl.col('high').alias('ext'), 'close').with_columns(pl.lit('up').alias('side'))
        dn = bb.filter((pl.col('low') <= pl.col('run_low') * (1 - SWEEP_BPS)) & (pl.col('close') >= pl.col('run_low'))).select('j', pl.col('run_low').alias('level'), pl.col('low').alias('ext'), 'close').with_columns(pl.lit('down').alias('side'))
        sw = pl.concat([up, dn]).sort('j', 'side')
        if sw.height:
            sw = sw.with_columns((pl.col('j') + 1).alias('t')).with_row_index('id')   # the bar closes at t = j+1: entry at the quotes stamped t
            sw = sw.with_columns(pl.col('t').map_elements(lambda t: px.get(int(t)), return_dtype=pl.Float64).alias('px_t'))
            for k_ in (15, 30):
                sw = sw.with_columns(pl.col('t').map_elements(lambda t, k_=k_: px.get(min(int(t) + k_, CLOSE_M), close_px), return_dtype=pl.Float64).alias(f'px_{k_}'))
            sw = sw.with_columns(pl.lit(close_px).alias('close_px'), pl.lit(d).alias('session'))
            outs = []
            for kind, up_right, dn_right in (('fade', 'PUT', 'CALL'), ('break', 'CALL', 'PUT')):
                ks = []
                for side, rt in (('up', up_right), ('down', dn_right)):
                    w = sw.filter(pl.col('side') == side).select('id', 't', pl.col('px_t').alias('px'))
                    if w.height: ks.append(nearest_otm(q, w, rt))
                if not ks: continue
                E = pl.concat(ks).join(sw.select('id', pl.col('t').alias('e')), on='id')
                T = trades(q, E)
                if T is None: continue
                outs.append(E.select('id', 'strike', 'right').join(T, on='id').rename({c: f'{kind}_{c}' for c in ['strike', 'right', 'entry_ask', 'entry_bid', 'stopped', 'exit_m', 'exit_bid', 'max_bid', 'max_bid_m', 'pnl_trail', 'pnl_hold', 'ret_trail', 'ret_hold']}).select(['id'] + [f'{kind}_{c}' for c in ['strike', 'right', 'entry_ask', 'entry_bid', 'stopped', 'exit_m', 'exit_bid', 'max_bid', 'max_bid_m', 'pnl_trail', 'pnl_hold', 'ret_trail', 'ret_hold']]))
            for o in outs: sw = sw.join(o, on='id', how='left')
            sweeps = sw.drop('id')
    return scans, touches, flow, sweeps

def run(root, first=None, last=None):
    files = sorted(x[:-8] for x in os.listdir(os.path.join(RAW, 'data_full', 'chains', root)))
    if first: files = [x for x in files if x >= first]
    if last: files = [x for x in files if x <= last]
    acc = {'scans': [], 'touches': [], 'flow': [], 'sweeps': []}
    t0 = time.time(); n = 0; skipped = []
    for d in files:
        try:
            r = session(root, dt.date.fromisoformat(d))
        except Exception as ex:
            skipped.append((d, repr(ex)[:120])); continue
        if r is None: skipped.append((d, 'half day or no spot')); continue
        for name, tab in zip(acc, r):
            if tab is not None and tab.height: acc[name].append(tab.with_columns(pl.col('session').cast(pl.Utf8)))
        n += 1
        if n % 100 == 0: print(root, d, n, f'{time.time() - t0:.0f}s', flush=True)
    for name, parts in acc.items():
        if parts:
            T = pl.concat(parts, how='diagonal_relaxed')
            T.write_parquet(os.path.join(OUT, f'{name}_{root}.parquet'), compression='zstd')
            print(root, name, T.height, flush=True)
    print(root, 'sessions', n, 'skipped', len(skipped), f'{time.time() - t0:.0f}s')
    with open(os.path.join(OUT, f'skipped_{root}.txt'), 'w') as fh:
        for d, why in skipped: fh.write(f'{d}\t{why}\n')

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, sys.argv[3] if len(sys.argv) > 3 else None)
