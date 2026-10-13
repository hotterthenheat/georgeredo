#!/usr/bin/env python3
"""T-C: 13:00 SPXW short straddle at measured NBBO (ThetaData 1-minute quotes), 2025-06-02..2026-10-09.
Env: TD_CACHE (ThetaData gzip-CSV cache), TC_OUT (fetch_log.csv + random_baseline_minutes.csv), OUT_DIR (results).
Fills: sell both legs at the NBBO bid of the entry minute; buy back at the NBBO ask of the exit minute; $1.00 per contract per side.
Settlement variant: credit minus |SPX official close - K| x 100, entry fees only (cash settlement, no exit trade)."""
import os, sys, glob, math, datetime as dt
import numpy as np, pandas as pd
TD = os.environ['TD_CACHE']; TC = os.environ['TC_OUT']; OUT = os.environ['OUT_DIR']; os.makedirs(OUT, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
FEE = 1.00; B = 5000; SEED = 7; STOP_MULT = 2.0; HS_GATE = 0.015
EVENTS = pd.read_csv(os.path.join(HERE, 'event_days.csv'))
EVENT_DATES = set(EVENTS['date'])
def minutes(a, b):
    out = []; m = a
    while m <= b: out.append(f'{m // 60:02d}:{m % 60:02d}'); m += 1
    return out
def hm2m(s): return int(s[:2]) * 60 + int(s[3:5])
def qfile(d, k, right):
    ks = str(int(k)) if float(k).is_integer() else str(k)
    return os.path.join(TD, f'option_history_quote__date={d}__expiration={d}__interval=1m__right={right}__strike={ks}__symbol=SPXW.csv.gz')
_qc = {}
def load_q(d, k, right):
    key = (d, k, right)
    if key in _qc: return _qc[key]
    f = qfile(d, k, right); q = None
    if os.path.exists(f):
        q = pd.read_csv(f)
        if q.empty: q = None
        else:
            q['hm'] = q['timestamp'].str.slice(11, 16); q = q.drop_duplicates('hm').set_index('hm')
            q['mid'] = (q['bid'] + q['ask']) / 2
    _qc[key] = q; return q
# SPX official close (settlement) from the monthly EOD files; fallback to the 16:00:00 minute price
eod = [pd.read_csv(f) for f in sorted(glob.glob(os.path.join(TD, 'index_history_eod__*symbol=SPX.csv.gz')))]
eod = pd.concat([e for e in eod if not e.empty], ignore_index=True) if eod else pd.DataFrame()
spx_close = {}
if len(eod):
    for _, r in eod.iterrows(): spx_close[str(r['last_trade'])[:10]] = float(r['close'])
def spx_1600(d):
    f = os.path.join(TD, f'index_history_price__date={d}__interval=1m__symbol=SPX.csv.gz')
    if not os.path.exists(f): return None
    s = pd.read_csv(f); s = s[s['timestamp'].str.slice(11, 16) == '16:00']
    return float(s['price'].iloc[0]) if len(s) else None
def straddle(d, k, entry_hm, exits=('15:55', '15:59', '16:00'), stop=True):
    c = load_q(d, k, 'call'); p = load_q(d, k, 'put')
    if c is None or p is None or entry_hm not in c.index or entry_hm not in p.index: return None
    ce, pe = c.loc[entry_hm], p.loc[entry_hm]
    if min(ce['bid'], pe['bid']) <= 0 or min(ce['ask'], pe['ask']) <= 0 or ce['ask'] < ce['bid'] or pe['ask'] < pe['bid']: return None
    r = dict(date=d, strike=k, entry=entry_hm, call_bid=ce['bid'], call_ask=ce['ask'], put_bid=pe['bid'], put_ask=pe['ask'],
             credit_exec=ce['bid'] + pe['bid'], credit_mid=ce['mid'] + pe['mid'])
    r['hs_entry_call'] = (ce['ask'] - ce['bid']) / 2; r['hs_entry_put'] = (pe['ask'] - pe['bid']) / 2
    r['hs_entry_call_pct'] = r['hs_entry_call'] / ce['mid']; r['hs_entry_put_pct'] = r['hs_entry_put'] / pe['mid']
    r['hs_entry_straddle'] = r['hs_entry_call'] + r['hs_entry_put']; r['hs_entry_straddle_pct'] = r['hs_entry_straddle'] / r['credit_mid']
    for x in exits:
        if x not in c.index or x not in p.index: r[f'pnl_exec_{x}'] = np.nan; continue
        cx, px = c.loc[x], p.loc[x]
        r[f'debit_exec_{x}'] = cx['ask'] + px['ask']; r[f'debit_mid_{x}'] = cx['mid'] + px['mid']
        r[f'pnl_exec_{x}'] = (r['credit_exec'] - r[f'debit_exec_{x}']) * 100 - 4 * FEE
        r[f'pnl_mid_{x}'] = (r['credit_mid'] - r[f'debit_mid_{x}']) * 100
        r[f'hs_exit_call_{x}'] = (cx['ask'] - cx['bid']) / 2; r[f'hs_exit_put_{x}'] = (px['ask'] - px['bid']) / 2
        r[f'hs_exit_call_pct_{x}'] = r[f'hs_exit_call_{x}'] / cx['mid'] if cx['mid'] > 0 else np.nan
        r[f'hs_exit_put_pct_{x}'] = r[f'hs_exit_put_{x}'] / px['mid'] if px['mid'] > 0 else np.nan
        r[f'hs_exit_straddle_{x}'] = r[f'hs_exit_call_{x}'] + r[f'hs_exit_put_{x}']
        r[f'hs_exit_straddle_pct_{x}'] = r[f'hs_exit_straddle_{x}'] / r[f'debit_mid_{x}'] if r[f'debit_mid_{x}'] > 0 else np.nan
    S = spx_close.get(d); src = 'eod'
    if S is None: S = spx_1600(d); src = '1600'
    r['spx_settle'] = S; r['settle_src'] = src
    r['pnl_settle'] = (r['credit_exec'] - abs(S - k)) * 100 - 2 * FEE if S is not None else np.nan
    r['pnl_settle_mid'] = (r['credit_mid'] - abs(S - k)) * 100 if S is not None else np.nan
    # 2.0x credit stop on straddle mids, checked each minute after entry up to 15:54; fill at the next minute's asks
    r['stop_hit'] = 0; r['exit_stop'] = '15:55'; r['pnl_exec_stop'] = r.get('pnl_exec_15:55', np.nan); r['peak_mid'] = r['credit_mid']
    if stop:
        for m in minutes(hm2m(entry_hm) + 1, hm2m('15:54')):
            if m in c.index and m in p.index:
                mark = c.loc[m, 'mid'] + p.loc[m, 'mid']; r['peak_mid'] = max(r['peak_mid'], mark)
                if mark >= STOP_MULT * r['credit_exec']:
                    nx = minutes(hm2m(m) + 1, hm2m(m) + 1)[0]
                    if nx in c.index and nx in p.index:
                        deb = c.loc[nx, 'ask'] + p.loc[nx, 'ask']
                        r['stop_hit'] = 1; r['exit_stop'] = nx; r['pnl_exec_stop'] = (r['credit_exec'] - deb) * 100 - 4 * FEE
                    break
    return r
# ---------- statistics ----------
def cluster_boot(x, cl, stat=np.mean, n=B, seed=SEED):
    x = np.asarray(x, float); cl = np.asarray(cl); ids = np.unique(cl); groups = [x[cl == i] for i in ids]
    rng = np.random.default_rng(seed); out = np.empty(n)
    for b in range(n):
        pick = rng.integers(0, len(ids), len(ids)); out[b] = stat(np.concatenate([groups[i] for i in pick]))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
def stats(df, col, label, cl='date'):
    d = df[['date', col]].dropna(); x = d[col].values.astype(float)
    if len(x) == 0: return dict(label=label, n=0)
    lo, hi = cluster_boot(x, d[cl].values)
    cum = np.cumsum(x); peak = np.maximum.accumulate(np.concatenate([[0.0], cum])); mdd = float((cum - peak[1:]).min()) if len(x) else 0.0
    gp = x[x > 0].sum(); gl = -x[x < 0].sum()
    worst = d.sort_values(col).head(5)
    return dict(label=label, n=int(len(x)), days=int(d['date'].nunique()), total=round(float(x.sum()), 2), mean=round(float(x.mean()), 2), sd=round(float(x.std(ddof=1)), 2) if len(x) > 1 else np.nan,
                ci_lo=round(lo, 2), ci_hi=round(hi, 2), win_rate=round(float((x > 0).mean()), 4), pf=round(float(gp / gl), 3) if gl > 0 else np.inf, max_dd=round(mdd, 2),
                worst5=' | '.join(f"{r['date']} {r[col]:.0f}" for _, r in worst.iterrows()))
def paired_diff(a, b, label):
    m = a.merge(b, on='date', suffixes=('_a', '_b')); x = (m['v_a'] - m['v_b']).values
    lo, hi = cluster_boot(x, m['date'].values)
    return dict(label=label, n=len(x), mean=round(float(x.mean()), 2), ci_lo=round(lo, 2), ci_hi=round(hi, 2))
# ---------- run ----------
log = pd.read_csv(os.path.join(TC, 'fetch_log.csv'))
rows = []; skipped = []
for _, r in log[log['draw'] == 0].sort_values('date').iterrows():
    s = straddle(r['date'], float(r['strike']), '13:00')
    if s is None: skipped.append(dict(date=r['date'], strike=r['strike'], reason='missing/zero NBBO at 13:00')); continue
    s['spx_1300'] = r['spx']; s['strike_fallback'] = int(r['fallback']); s['event'] = int(r['date'] in EVENT_DATES)
    s['event_type'] = '|'.join(EVENTS.loc[EVENTS['date'] == r['date'], 'type']) if s['event'] else ''
    rows.append(s)
S = pd.DataFrame(rows); S['month'] = S['date'].str.slice(0, 7)
for x in ('15:55', '15:59', '16:00'): S[f'pct_exec_{x}'] = S[f'pnl_exec_{x}'] / (S['credit_exec'] * 100)
S['pct_settle'] = S['pnl_settle'] / (S['credit_exec'] * 100)
S['round_trip_cost'] = (S['hs_entry_straddle'] + S['hs_exit_straddle_15:55']) * 100 + 4 * FEE
S.to_csv(os.path.join(OUT, 'tc_straddles.csv'), index=False)
pd.DataFrame(skipped).to_csv(os.path.join(OUT, 'tc_skipped.csv'), index=False)
# random-time baseline: five draws, entry at the committed random minute, exit 15:55
rb = []
for _, r in log[log['draw'] >= 1].sort_values(['draw', 'date']).iterrows():
    s = straddle(r['date'], float(r['strike']), str(r['entry']), exits=('15:55',), stop=False)
    if s is None: continue
    s['draw'] = int(r['draw']); rb.append(s)
RB = pd.DataFrame(rb); RB['pct_exec_15:55'] = RB['pnl_exec_15:55'] / (RB['credit_exec'] * 100)
RB.to_csv(os.path.join(OUT, 'tc_random_baseline.csv'), index=False)
# summaries
summ = []
NE = S[S['event'] == 0]
for name, df in (('all sessions', S), ('ex FOMC/CPI/NFP', NE)):
    summ.append(stats(df, 'pnl_exec_15:55', f'{name}: executable, sell bid 13:00 / buy ask 15:55, fees'))
    summ.append(stats(df, 'pnl_exec_15:59', f'{name}: executable, exit 15:59'))
    summ.append(stats(df, 'pnl_exec_16:00', f'{name}: executable, exit at the 16:00 last quote'))
    summ.append(stats(df, 'pnl_settle', f'{name}: hold to cash settlement (official SPX close), entry fees only'))
    summ.append(stats(df, 'pnl_exec_stop', f'{name}: executable with {STOP_MULT}x credit stop (mids, next-minute ask fill)'))
    summ.append(stats(df, 'pnl_mid_15:55', f'{name}: mid-to-mid 15:55, no fees (reference)'))
    summ.append(stats(df, 'pnl_settle_mid', f'{name}: mid credit to settlement, no fees (reference)'))
for k in sorted(RB['draw'].unique()):
    summ.append(stats(RB[RB['draw'] == k], 'pnl_exec_15:55', f'random-time baseline draw {k} (entry {RB[RB.draw==k].entry.min()}-{RB[RB.draw==k].entry.max()}), executable 15:55'))
summ.append(stats(RB, 'pnl_exec_15:55', 'random-time baseline, five draws pooled (date-clustered)'))
summ.append(stats(RB[RB['date'].isin(NE['date'])], 'pnl_exec_15:55', 'random-time baseline, five draws pooled, ex events'))
SUM = pd.DataFrame(summ); SUM.to_csv(os.path.join(OUT, 'tc_summary.csv'), index=False)
# paired 13:00 minus random (per-date mean of the five draws)
rb_mean = RB.groupby('date')['pnl_exec_15:55'].mean().reset_index().rename(columns={'pnl_exec_15:55': 'v'})
a = S[['date', 'pnl_exec_15:55']].rename(columns={'pnl_exec_15:55': 'v'})
PD = pd.DataFrame([paired_diff(a, rb_mean, '13:00 minus random-time (mean of 5 draws), executable $'),
                   paired_diff(a[a['date'].isin(NE['date'])], rb_mean, 'same, ex events')])
PD.to_csv(os.path.join(OUT, 'tc_paired_vs_random.csv'), index=False)
# spreads distribution
def dist(x):
    x = pd.Series(x).dropna(); return dict(n=len(x), mean=x.mean(), p10=x.quantile(.1), p25=x.quantile(.25), median=x.median(), p75=x.quantile(.75), p90=x.quantile(.9), max=x.max())
SP = []
for c, lab in (('hs_entry_call', 'entry 13:00 call half-spread $'), ('hs_entry_put', 'entry 13:00 put half-spread $'), ('hs_entry_call_pct', 'entry call half-spread % of mid'), ('hs_entry_put_pct', 'entry put half-spread % of mid'),
               ('hs_entry_straddle', 'entry straddle half-spread $ (sum of legs)'), ('hs_entry_straddle_pct', 'entry straddle half-spread % of straddle mid'),
               ('hs_exit_call_15:55', 'exit 15:55 call half-spread $'), ('hs_exit_put_15:55', 'exit 15:55 put half-spread $'), ('hs_exit_call_pct_15:55', 'exit 15:55 call half-spread % of mid'), ('hs_exit_put_pct_15:55', 'exit 15:55 put half-spread % of mid'),
               ('hs_exit_straddle_15:55', 'exit 15:55 straddle half-spread $'), ('hs_exit_straddle_pct_15:55', 'exit 15:55 straddle half-spread % of straddle mid'),
               ('hs_exit_straddle_pct_15:59', 'exit 15:59 straddle half-spread % of straddle mid'), ('hs_exit_straddle_pct_16:00', 'exit 16:00 straddle half-spread % of straddle mid'),
               ('round_trip_cost', 'round-trip cost $ (entry+exit 15:55 half-spreads x100 + $4 fees)'), ('credit_exec', 'credit at bid (points)'), ('credit_mid', 'credit at mid (points)')):
    SP.append(dict(metric=lab, **dist(S[c])))
SP = pd.DataFrame(SP); SP.to_csv(os.path.join(OUT, 'tc_spreads.csv'), index=False)
BM = S.groupby('month').agg(n=('date', 'count'), mean_exec=('pnl_exec_15:55', 'mean'), total_exec=('pnl_exec_15:55', 'sum'), win=('pnl_exec_15:55', lambda v: (v > 0).mean()), mean_settle=('pnl_settle', 'mean'), credit=('credit_exec', 'mean')).reset_index()
BM.to_csv(os.path.join(OUT, 'tc_by_month.csv'), index=False)
# gate
main = SUM.iloc[0]; hs_mean = S['hs_entry_straddle_pct'].mean(); hs_med = S['hs_entry_straddle_pct'].median()
months = (dt.date.fromisoformat(S['date'].max()) - dt.date.fromisoformat(S['date'].min())).days / 30.44
rt_cost = S['round_trip_cost'].mean(); diff = PD.iloc[0]
gate = [dict(criterion='C1 executable lower 95% bound > 0, n >= 150 straddle-days, span >= 3 months', value=f"lower={main['ci_lo']}, n={main['n']}, span={months:.1f} months", result='PASS' if (main['ci_lo'] > 0 and main['n'] >= 150 and months >= 3) else 'FAIL'),
        dict(criterion='C2 realized entry half-spread <= 1.5% of credit (straddle, % of mid)', value=f'mean={hs_mean:.4f}, median={hs_med:.4f}', result='PASS' if hs_mean <= HS_GATE else 'FAIL'),
        dict(criterion='C3 beats random-entry baseline by more than one round-trip cost', value=f"13:00 minus random = {diff['mean']} [{diff['ci_lo']}, {diff['ci_hi']}] vs mean round-trip cost {rt_cost:.2f}", result='PASS' if diff['mean'] > rt_cost else 'FAIL'),
        dict(criterion='C4 (plan §1.3) edge survives executable NBBO fills (same as C1 here: fills are at bid/ask, not mid)', value=f"exec mean={main['mean']} vs mid mean={SUM.iloc[5]['mean']}", result='PASS' if main['ci_lo'] > 0 else 'FAIL')]
G = pd.DataFrame(gate); G.to_csv(os.path.join(OUT, 'tc_gate.csv'), index=False)
# RESULTS.md (numbers only from this run)
def md(df, cols=None):
    df = df if cols is None else df[cols]
    return '| ' + ' | '.join(df.columns) + ' |\n|' + '---|' * len(df.columns) + '\n' + '\n'.join('| ' + ' | '.join('' if (isinstance(v, float) and math.isnan(v)) else (f'{v:.4g}' if isinstance(v, float) else str(v)) for v in r) + ' |' for r in df.itertuples(index=False))
L = []
L.append('# T-C results: 13:00 SPXW short straddle at measured NBBO\n')
L.append(f"Generated by `analyze_tc.py` on {dt.date.today().isoformat()}. Window {S['date'].min()} to {S['date'].max()}, {len(S)} sessions (early closes excluded; {len(skipped)} skipped for missing/zero NBBO), {int(S['event'].sum())} event days (FOMC/CPI/NFP, `event_days.csv`). Settlement source: {S['settle_src'].value_counts().to_dict()}. Strike fallback (nearest 5-point strike missing): {int(S['strike_fallback'].sum())} sessions. Stops hit: {int(S['stop_hit'].sum())}.\n")
L.append('## Gate (plan §1 with 1.5 % half-spread)\n'); L.append(md(G)); L.append('')
L.append('## P&L per 1-lot straddle ($), 95 % CI by date-clustered bootstrap (5,000 draws, seed 7)\n'); L.append(md(SUM, ['label', 'n', 'total', 'mean', 'ci_lo', 'ci_hi', 'win_rate', 'pf', 'max_dd', 'worst5'])); L.append('')
L.append('## 13:00 entry minus random-time baseline (paired by date)\n'); L.append(md(PD)); L.append('')
L.append('## Realized half-spreads (points per share unless marked %; 1 point = $100 per contract)\n'); L.append(md(SP)); L.append('')
L.append('## By month (executable 15:55 exit)\n'); L.append(md(BM)); L.append('')
L.append('## Percent-of-credit view\n')
L.append(f"Mean executable return on credit, 15:55 exit: {S['pct_exec_15:55'].mean():.4f} (median {S['pct_exec_15:55'].median():.4f}); settlement: {S['pct_settle'].mean():.4f}. Mean credit at bid {S['credit_exec'].mean():.2f} points, at mid {S['credit_mid'].mean():.2f}.\n")
open(os.path.join(OUT, 'RESULTS.md'), 'w').write('\n'.join(L))
print('\n'.join(L))
