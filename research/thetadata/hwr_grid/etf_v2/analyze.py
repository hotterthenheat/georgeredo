"""Aggregation, selection and evaluation of the pre-registered grid (PREREGISTRATION_original.md §5-§8), etf_v2 full-chain re-run.
Copied from ../etf/analyze.py.  Changes: a scope is computed only when every ticker of the scope has trade files for the period (the
original silently pooled whatever existed); the TRAIN stage keeps scopes already present in results/selection_train.json unchanged
(asserting that a re-run reproduces them) and adds new scopes, recording the UTC time each scope was selected.
Usage:
  python3 analyze.py train   -> results/grid_train.csv.gz, results/selection_train.json   (reads only TRAIN trades)
  python3 analyze.py test    -> results/grid.csv.gz (TRAIN + TEST per configuration), results/*.csv, RESULTS.md
Per-trade inputs: $HWR_WORK/trades_{TICKER}_{PERIOD}.parquet from engine.py."""
import os, sys, json, glob, hashlib, datetime as dt
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C

B = 5000
FOMC = C.fomc_days(); ME = C.month_ends()
SCOPES = {'SPY': ('SPY',), 'QQQ': ('QQQ',), 'IWM': ('IWM',), 'SPY+QQQ': ('SPY', 'QQQ')}
KEEP = ['tk', 'date', 'entry', 'sk', 'tp', 'st', 'ex', 'pnl', 'cost', 'credit', 'dprox', 'reason', 'n_exp', 'itm_exp']


def have(tk, period): return os.path.exists(os.path.join(C.WORK, f'trades_{tk}_{period}.parquet'))


def load(tk, period):
    return pl.read_parquet(os.path.join(C.WORK, f'trades_{tk}_{period}.parquet')).select(KEEP)


def days_ok(tk, period):
    d = pl.read_parquet(os.path.join(C.WORK, f'days_{tk}_{period}.parquet'))
    return sorted(d.filter(pl.col('status') == 'ok')['date'].to_list())


def apply_filters(T, fixed=True):
    """Long frame with a `filt` column (F0-F3) and `cfg` id.  T holds one entry label per row; for the random baseline the label is
    the seed (r11..r15) and F2 substitutes the fixed 14:05 trade on FOMC days (passed in T as entry '14:05')."""
    is_f = pl.col('date').is_in(list(FOMC)); is_me = pl.col('date').is_in(list(ME))
    base = T.filter(pl.col('entry') != '14:05') if not fixed else T
    out = [base.with_columns(pl.lit('F0').alias('filt')),
           base.filter(~is_f).with_columns(pl.lit('F1').alias('filt')),
           base.filter(~(is_f | is_me)).with_columns(pl.lit('F3').alias('filt'))]
    labels = [e for e in base['entry'].unique().to_list()]
    t1405 = T.filter((pl.col('entry') == '14:05') & is_f)
    f2 = [base.filter(~is_f)] + [t1405.with_columns(pl.lit(e).alias('entry')) for e in labels]
    out.append(pl.concat(f2).with_columns(pl.lit('F2').alias('filt')))
    L = pl.concat(out)
    return L.with_columns(pl.concat_str([pl.col('sk'), pl.col('entry'), pl.lit('tp') + pl.col('tp').cast(pl.Utf8), pl.lit('st') + pl.col('st').cast(pl.Utf8),
                                         pl.col('ex'), pl.col('filt')], separator='|').alias('cfg'))


def boot_matrix(Lf, days, seeds=(7,)):
    """Day-clustered bootstrap of the per-trade mean for every cfg at once.  Returns cfg list, point means, {seed: (B, nC) means}."""
    cfgs = sorted(Lf['cfg'].unique().to_list()); ci = {c: i for i, c in enumerate(cfgs)}; di = {d: i for i, d in enumerate(days)}
    S = Lf.group_by(['cfg', 'date']).agg(p=pl.col('pnl').sum(), n=pl.len())
    S = S.filter(pl.col('date').is_in(days))
    r = np.array([di[d] for d in S['date'].to_list()]); c = np.array([ci[x] for x in S['cfg'].to_list()])
    P = np.zeros((len(days), len(cfgs))); N = np.zeros((len(days), len(cfgs)))
    np.add.at(P, (r, c), S['p'].to_numpy()); np.add.at(N, (r, c), S['n'].to_numpy().astype(float))
    point = P.sum(0) / np.where(N.sum(0) > 0, N.sum(0), np.nan)
    out = {}
    for s in seeds:
        W = C.boot_weights(len(days), B, s)
        with np.errstate(invalid='ignore', divide='ignore'):
            out[s] = (W @ P) / (W @ N)
        del W
    return cfgs, point, out, N.sum(0)


def metrics(Lf, days, seeds=(7,)):
    Lf = Lf.filter(pl.col('date').is_in(days))
    g = Lf.sort(['cfg', 'date', 'tk']).with_columns(pl.col('pnl').cum_sum().over('cfg').alias('cum'))
    g = g.with_columns(pl.max_horizontal(pl.col('cum').cum_max().over('cfg'), pl.lit(0.0)).alias('peak'))
    agg = g.group_by('cfg').agg(n=pl.len(), wr=(pl.col('pnl') > 0).mean() * 100, mean=pl.col('pnl').mean(), median=pl.col('pnl').median(),
                                total=pl.col('pnl').sum(), gw=pl.col('pnl').filter(pl.col('pnl') > 0).sum(),
                                gl=pl.col('pnl').filter(pl.col('pnl') < 0).sum(), mdd=(pl.col('cum') - pl.col('peak')).min(),
                                months=pl.col('date').str.slice(0, 7).n_unique(), dates=pl.col('date').n_unique(),
                                credit=pl.col('credit').mean(), cost=pl.col('cost').mean(), dprox=pl.col('dprox').median(),
                                worst_trade=pl.col('pnl').min(), itm_exp=(pl.col('itm_exp') > 0).mean() * 100)
    agg = agg.with_columns(pf=pl.when(pl.col('gl') < 0).then(pl.col('gw') / -pl.col('gl')).otherwise(float('inf')))
    ds = Lf.group_by(['cfg', 'date']).agg(p=pl.col('pnl').sum()).sort(['cfg', 'p']).group_by('cfg', maintain_order=True).head(5)
    w5 = ds.group_by('cfg').agg(worst5=pl.concat_str([pl.col('date'), pl.col('p').round(0).cast(pl.Int64).cast(pl.Utf8)], separator=' ').str.join('; '),
                                worst5_sum=pl.col('p').sum())
    agg = agg.join(w5, on='cfg', how='left')
    cfgs, point, bm, nn = boot_matrix(Lf, days, seeds)
    M = bm[seeds[0]]
    with np.errstate(invalid='ignore'):
        lo = np.nanpercentile(M, 2.5, axis=0); hi = np.nanpercentile(M, 97.5, axis=0); se = np.nanstd(M, axis=0)
    lo[nn < 5] = np.nan; hi[nn < 5] = np.nan
    bt = pl.DataFrame({'cfg': cfgs, 'lo': lo, 'hi': hi, 'se': se})
    agg = agg.join(bt, on='cfg', how='left')
    return agg, (cfgs, point, bm, nn)


def split_cfg(df):
    parts = pl.col('cfg').str.split('|')
    return df.with_columns(sk=parts.list.get(0), entry=parts.list.get(1), tp=parts.list.get(2).str.slice(2).cast(pl.Int64),
                           st=parts.list.get(3).str.slice(2).cast(pl.Int64), ex=parts.list.get(4), filt=parts.list.get(5)).with_columns(
        dup=((pl.col('filt') == 'F2') & (pl.col('entry') == '14:05')), diag=(pl.col('ex') == 'E0'))


def scope_frames(scope, period):
    tks = list(SCOPES[scope])
    if not all(have(t, period) for t in tks): return None, None
    T = pl.concat([load(t, period) for t in tks])
    days = sorted(set().union(*[set(days_ok(t, period)) for t in tks]))
    return T, days


def grid_period(scope, period, seeds=(7,)):
    T, days = scope_frames(scope, period)
    if T is None: return None, None, None
    fixed = T.filter(pl.col('entry').is_in(list(C.ENTRIES)))
    Lf = apply_filters(fixed)
    agg, bm = metrics(Lf, days, seeds)
    agg = split_cfg(agg).with_columns(pl.lit(scope).alias('scope'), pl.lit(period).alias('period'))
    return agg, bm, (T, days, Lf)


def fmt_cfg(c):
    sk, e, tp, st, ex, f = c.split('|')
    s = {'S': 'straddle' if sk == 'S0' else 'strangle', 'I': 'iron condor'}[sk[0]]
    fl = {'F0': 'no filter', 'F1': 'skip FOMC', 'F2': 'FOMC→14:05', 'F3': 'skip FOMC+month-end'}[f]
    return f'{s} k={sk[1:]} @{e}, TP {tp[2:]}%, stop {st[2:]}x, {ex}, {fl}'.replace('TP 0%', 'no TP').replace('stop 0x', 'no stop')


# ------------------------------------------------------------------ TRAIN stage
def stage_train():
    os.makedirs(C.OUT, exist_ok=True)
    sp = os.path.join(C.OUT, 'selection_train.json')
    old = json.load(open(sp)) if os.path.exists(sp) else None
    rows = []; sel = {'written_utc': dt.datetime.utcnow().isoformat(timespec='seconds'), 'rule': 'PREREGISTRATION_original.md §7 (unchanged)',
                      'data': 'full chains (data_full), TRAIN trades only', 'scopes': {}}
    for scope in SCOPES:
        agg, _, _ = grid_period(scope, 'TRAIN')
        if agg is None: print('no TRAIN data for', scope); continue
        rows.append(agg)
        G = agg.filter(~pl.col('diag') & (pl.col('n') >= 100) & pl.col('lo').is_not_nan())
        G = G.sort(['lo', 'mean', 'cfg'], descending=[True, True, False])
        s1 = G.row(0, named=True)
        G70 = G.filter(pl.col('wr') >= 70)
        s2 = G70.row(0, named=True) if G70.height else None
        keep = ['cfg', 'n', 'wr', 'mean', 'lo', 'hi', 'pf', 'mdd', 'months', 'credit', 'cost']
        sel['scopes'][scope] = dict(S1={k: s1[k] for k in keep}, S2=({k: s2[k] for k in keep} if s2 else None),
                                    eligible=G.height, eligible_wr70=G70.height,
                                    top10=[{k: r[k] for k in keep} for r in G.head(10).iter_rows(named=True)])
        if old and scope in old['scopes']:
            o = old['scopes'][scope]
            assert o['S1']['cfg'] == s1['cfg'] and (o['S2'] or {}).get('cfg') == (s2 or {}).get('cfg'), f'{scope}: re-run changed the selection'
            sel['scopes'][scope] = o
        else:
            sel['scopes'][scope]['selected_utc'] = dt.datetime.utcnow().isoformat(timespec='seconds')
        print(scope, 'S1', s1['cfg'], round(s1['lo'], 2), '| S2', s2['cfg'] if s2 else None, round(s2['lo'], 2) if s2 else None, flush=True)
    pl.concat(rows).write_csv(os.path.join(C.OUT, 'grid_train.csv'))
    os.system(f"gzip -f {os.path.join(C.OUT, 'grid_train.csv')}")
    js = json.dumps(sel, indent=1, default=float)
    open(sp, 'w').write(js)
    print('selection sha256', hashlib.sha256(js.encode()).hexdigest())


if __name__ == '__main__':
    if sys.argv[1] == 'train': stage_train()
    else:
        import analyze_test
        analyze_test.main()
