"""Build one row per SPX trading day (2017-06-01..2026-10-09) from the ThetaData gzip cache: morning/afternoon realized
ranges and variances, VIX levels, prior-day and 5-day vol, overnight gap, calendar flags. Reads only local files."""
import os, glob, re, datetime as dt
import numpy as np, pandas as pd
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
CACHE = os.path.join(SP, 'theta', 'cache', 'index_tests')
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)

def load_monthly(pattern):
    fs = sorted(glob.glob(os.path.join(CACHE, pattern)))
    parts = []
    for f in fs:
        df = pd.read_csv(f, compression='gzip')
        if len(df): parts.append(df)
    df = pd.concat(parts, ignore_index=True)
    return df, len(fs)

spx, nspx = load_monthly('index_history_price__end_date=*__interval=1m__start_date=*__symbol=SPX.csv.gz')
vix, nvix = load_monthly('index_history_price__end_date=*__interval=1m__start_date=*__symbol=VIX.csv.gz')
eod, neod = load_monthly('index_history_eod__end_date=*__start_date=*__symbol=SPX.csv.gz')
spy_eod, nspy = load_monthly('stock_history_eod__end_date=*__start_date=*__symbol=SPY.csv.gz')
print('files spx1m', nspx, 'vix1m', nvix, 'spx eod', neod, 'spy eod', nspy, 'rows', len(spx), len(vix), len(eod), len(spy_eod))
for df in (spx, vix):
    df['date'] = df['timestamp'].str.slice(0, 10); df['hhmm'] = df['timestamp'].str.slice(11, 16)
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
cal = pd.read_csv(os.path.join(CACHE, 'calendar_2017_2026.csv'))
early = set(cal.loc[cal['type'] == 'early_close', 'date']); full_close = set(cal.loc[cal['type'] == 'full_close', 'date'])

def px(g, hhmm):
    s = g.loc[g['hhmm'] == hhmm, 'price']
    return float(s.iloc[0]) if len(s) and pd.notna(s.iloc[0]) else np.nan

def rv(p):
    r = np.diff(np.log(p.dropna().values)); return float(np.sqrt(np.sum(r * r))) if len(r) > 1 else np.nan

rows = []
for d, g in spx.groupby('date', sort=True):
    g = g.sort_values('hhmm'); v = g['price']
    nvalid = int(v.notna().sum())
    m_1030 = g['hhmm'] <= '10:30'; m_1300 = g['hhmm'] <= '13:00'; m_pm = g['hhmm'] >= '13:00'
    p_open = px(g, '09:31') if pd.notna(px(g, '09:31')) else (float(v.dropna().iloc[0]) if nvalid else np.nan)
    p1030, p1300, p1600 = px(g, '10:30'), px(g, '13:00'), px(g, '16:00')
    if np.isnan(p1600) and nvalid: p1600 = float(v.dropna().iloc[-1])
    am1 = v[m_1030]; am = v[m_1300]; pm = v[m_pm]; allv = v
    rows.append(dict(date=d, n_valid=nvalid, early_close=int(d in early),
        p_open=p_open, p_1030=p1030, p_1300=p1300, p_close=p1600,
        hi_am=am.max(), lo_am=am.min(), hi_pm=pm.max(), lo_pm=pm.min(), hi_day=allv.max(), lo_day=allv.min(),
        range_0930_1030=(am1.max() - am1.min()) / p_open, range_0930_1300=(am.max() - am.min()) / p_open,
        rv_0930_1030=rv(am1), rv_0930_1300=rv(am), rv_1300_1600=rv(pm),
        range_pm=(pm.max() - pm.min()) / p1300, absmove_pm=abs(p1600 / p1300 - 1.0), move_pm=p1600 / p1300 - 1.0,
        range_day=(allv.max() - allv.min()) / p_open, absmove_am=abs(p1300 / p_open - 1.0), move_am=p1300 / p_open - 1.0))
D = pd.DataFrame(rows)
# VIX at 09:31 (fallback 09:30), 10:30, 13:00, last print
vrows = []
for d, g in vix.groupby('date', sort=True):
    g = g.sort_values('hhmm'); v = g['price']
    v0931 = px(g, '09:31'); v0930 = px(g, '09:30')
    vrows.append(dict(date=d, vix_0931=v0931 if pd.notna(v0931) else v0930, vix_1030=px(g, '10:30'), vix_1300=px(g, '13:00'),
                      vix_last=float(v.dropna().iloc[-1]) if v.notna().any() else np.nan, vix_n=int(v.notna().sum()),
                      vix_hi_am=v[g['hhmm'] <= '13:00'].max(), vix_lo_am=v[g['hhmm'] <= '13:00'].min()))
V = pd.DataFrame(vrows)
D = D.merge(V, on='date', how='left')
D['vix_chg_open_1300'] = D['vix_1300'] / D['vix_0931'] - 1.0
D['vix_chg_open_1030'] = D['vix_1030'] / D['vix_0931'] - 1.0
# EOD: prior-day range, 5-day RV, close-to-close, gap
eod['date'] = eod['last_trade'].str.slice(0, 10); eod = eod.sort_values('date').drop_duplicates('date')
E = eod[['date', 'open', 'high', 'low', 'close']].rename(columns={c: 'eod_' + c for c in ('open', 'high', 'low', 'close')})
E['eod_range'] = (E['eod_high'] - E['eod_low']) / E['eod_close']
E['ret_cc'] = np.log(E['eod_close'] / E['eod_close'].shift(1))
E['rv5'] = E['ret_cc'].rolling(5).std() * np.sqrt(252)
E['rv20'] = E['ret_cc'].rolling(20).std() * np.sqrt(252)
E['prev_close'] = E['eod_close'].shift(1); E['prev_range'] = E['eod_range'].shift(1); E['prev_rv5'] = E['rv5'].shift(1); E['prev_rv20'] = E['rv20'].shift(1)
E['prev_ret_cc'] = E['ret_cc'].shift(1)
E['prev_range_mean20'] = E['eod_range'].rolling(20).mean().shift(1)
D = D.merge(E[['date', 'eod_open', 'eod_high', 'eod_low', 'eod_close', 'prev_close', 'prev_range', 'prev_rv5', 'prev_rv20', 'prev_ret_cc', 'prev_range_mean20']], on='date', how='left')
D['gap'] = D['p_open'] / D['prev_close'] - 1.0; D['absgap'] = D['gap'].abs()
# SPY EOD close for gamma sign (prior day)
spy_eod['date'] = spy_eod['last_trade'].str.slice(0, 10) if 'last_trade' in spy_eod else spy_eod['created'].str.slice(0, 10)
S = spy_eod.sort_values('date').drop_duplicates('date')[['date', 'close']].rename(columns={'close': 'spy_close'})
D = D.merge(S, on='date', how='left'); D['spy_prev_close'] = D['spy_close'].shift(1)
# calendar flags
D['dt'] = pd.to_datetime(D['date']); D['dow'] = D['dt'].dt.dayofweek; D['year'] = D['dt'].dt.year; D['month'] = D['dt'].dt.month
D['month_end'] = (D['dt'].dt.to_period('M') != D['dt'].shift(-1).dt.to_period('M')).astype(int); D.loc[D.index[-1], 'month_end'] = 0
D['month_start'] = (D['dt'].dt.to_period('M') != D['dt'].shift(1).dt.to_period('M')).astype(int)
bd_prev = np.busday_count(D['dt'].shift(1).dt.date.values[1:].astype('datetime64[D]'), D['dt'].dt.date.values[1:].astype('datetime64[D]'))
bd_next = np.busday_count(D['dt'].dt.date.values[:-1].astype('datetime64[D]'), D['dt'].shift(-1).dt.date.values[:-1].astype('datetime64[D]'))
D['post_holiday'] = 0; D.loc[D.index[1:], 'post_holiday'] = (bd_prev > 1).astype(int)
D['pre_holiday'] = 0; D.loc[D.index[:-1], 'pre_holiday'] = (bd_next > 1).astype(int)
D['holiday_adj'] = ((D['post_holiday'] + D['pre_holiday']) > 0).astype(int)
# monthly opex: third Friday, or the preceding trading day if the third Friday is closed
tdays = set(D['date']); opex = set()
for y in range(2017, 2027):
    for m in range(1, 13):
        first = dt.date(y, m, 1); fri3 = first + dt.timedelta(days=(4 - first.weekday()) % 7 + 14)
        d = fri3
        while d.isoformat() not in tdays and d > first: d -= dt.timedelta(days=1)
        if d.isoformat() in tdays: opex.add(d.isoformat())
D['opex'] = D['date'].isin(opex).astype(int); D['quad_opex'] = (D['opex'].astype(bool) & D['month'].isin([3, 6, 9, 12])).astype(int)
# rolling VIX percentile (prior 60 trading days of 13:00 VIX, strictly before today)
D['vix1300_p80_60d'] = D['vix_1300'].shift(1).rolling(60).quantile(0.8)
D['vix0931_p80_60d'] = D['vix_0931'].shift(1).rolling(60).quantile(0.8)
D['vix_last_p80_60d'] = D['vix_last'].shift(1).rolling(60).quantile(0.8)
D['vix_last_prev'] = D['vix_last'].shift(1)
# trailing baselines for the targets (strictly prior days, excluding early closes)
ok = (D['early_close'] == 0)
for tgt in ('range_pm', 'absmove_pm', 'range_day'):
    s = np.log(D[tgt].where(ok))
    D[f'base20_log_{tgt}'] = s.shift(1).rolling(20, min_periods=10).mean()
D = D.drop(columns=['dt'])
D.to_csv(os.path.join(OUT, 'daily.csv'), index=False, float_format='%.8g')
print('days', len(D), D['date'].min(), D['date'].max(), 'early', int(D['early_close'].sum()), 'opex', int(D['opex'].sum()),
      'holiday_adj', int(D['holiday_adj'].sum()), 'month_end', int(D['month_end'].sum()))
print('missing p_1300', int(D['p_1300'].isna().sum()), 'missing p_close', int(D['p_close'].isna().sum()), 'n_valid<350', int((D['n_valid'] < 350).sum()),
      'vix_1300 missing', int(D['vix_1300'].isna().sum()), 'vix_0931 missing', int(D['vix_0931'].isna().sum()), 'prev_close missing', int(D['prev_close'].isna().sum()))
print(D[['range_pm', 'absmove_pm', 'range_0930_1300', 'range_day', 'vix_1300', 'absgap', 'prev_range', 'prev_rv5']].describe().T.to_string())
print(D[D['n_valid'] < 350][['date', 'n_valid', 'early_close']].head(30).to_string())
