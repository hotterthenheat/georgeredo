"""TEST stage of the pre-registered grid (called by `python3 analyze.py test`), etf_v2 full-chain re-run.
Copied from ../etf/analyze_test.py.  Additions (the pre-registered statistics are computed exactly as before):
  * the ORIGINAL TRAIN selections (../etf/results/selection_train.json, band data) are evaluated on the complete TEST data, tagged
    S1-orig / S2-orig, next to the full-chain TRAIN re-selections S1 / S2 (and the original post-hoc PH-*-E1 rule, labelled post-hoc);
  * random baseline on matched days: lane and baseline restricted to the same (ticker, date) pairs, with the counts and P&L of
    baseline trades on days the lane did not trade (the one-sidedness the developer review found);
  * Bonferroni lower bound over the 8 pre-registered selections (S1/S2 x 4 scopes) and the Romano-Wolf status of each selection;
  * comparison with the original band-data trades of the same configuration: trades common to both (max |P&L difference|) and
    trades that exist only on the complete data (count, mean, worst).  Requires results/selection_train.json written by the
TRAIN stage before any TEST trade file existed.  Writes results/grid.csv.gz, results/selected_test.csv, results/baselines.csv,
results/marginal_effects.csv, results/wr_vs_expectancy.csv, results/coverage.csv, results/grid_test_summary.json and RESULTS.md."""
import os, sys, json, gzip, hashlib, math
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import analyze as A

DIMS = ['sk', 'entry', 'tp', 'st', 'ex', 'filt']


def spearman(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3: return float('nan')
    ra = np.argsort(np.argsort(a[m])); rb = np.argsort(np.argsort(b[m]))
    return float(np.corrcoef(ra, rb)[0, 1])


def baseline(T, sk, tp, st, ex, filt, seed):
    """Random-entry trades for one config and seed (filters applied the same way as for the lane)."""
    q = (pl.col('sk') == sk) & (pl.col('tp') == tp) & (pl.col('st') == st) & (pl.col('ex') == ex)
    is_f = pl.col('date').is_in(list(A.FOMC)); is_me = pl.col('date').is_in(list(A.ME))
    R = T.filter(q & (pl.col('entry') == f'r{seed}'))
    if filt == 'F1': R = R.filter(~is_f)
    elif filt == 'F3': R = R.filter(~(is_f | is_me))
    elif filt == 'F2': R = pl.concat([R.filter(~is_f), T.filter(q & (pl.col('entry') == '14:05') & is_f).with_columns(pl.lit(f'r{seed}').alias('entry'))])
    return R


def lane_trades(Lf, cfg): return Lf.filter(pl.col('cfg') == cfg)


N_PREREG = 8                                                   # S1/S2 x 4 scopes


def boot_lo_q(v, clusters, q, B=5000, seed=7):
    """Lower percentile q (in %) of the same day-clustered bootstrap as C.boot_ci (identical draws)."""
    v = np.asarray(v, float)
    if len(v) < 5: return float('nan')
    rng = np.random.default_rng(seed)
    keys = {}; cl = np.array([keys.setdefault(c, len(keys)) for c in clusters]); Jn = len(keys)
    S = np.bincount(cl, weights=v, minlength=Jn); N = np.bincount(cl, minlength=Jn).astype(float)
    idx = rng.integers(0, Jn, (B, Jn)); means = S[idx].sum(1) / N[idx].sum(1)
    return float(np.percentile(means, q))


def orig_lane(scope, PER, cfg):
    """The same configuration's trades in the ORIGINAL band-data run (../etf per-trade files in C.ORIG_WORK)."""
    parts = []
    for tk in A.SCOPES[scope]:
        fp = os.path.join(C.ORIG_WORK, f'trades_{tk}_{PER}.parquet')
        if not os.path.exists(fp): return None
        parts.append(pl.read_parquet(fp).select(A.KEEP))
    T = pl.concat(parts)
    sk, e, tp, st, ex, f = cfg.split('|')
    T = T.filter((pl.col('sk') == sk) & (pl.col('tp') == int(tp[2:])) & (pl.col('st') == int(st[2:])) & (pl.col('ex') == ex))
    fixed = T.filter(pl.col('entry').is_in(list(C.ENTRIES)))
    return A.apply_filters(fixed).filter(pl.col('cfg') == cfg)


def summarize(df, label):
    if df.height == 0: return dict(label=label, n=0)
    df = df.sort(['date', 'tk']); v = df['pnl'].to_numpy(); lo, hi = C.boot_ci(v, df['date'].to_list())
    w = v[v > 0]; l = v[v < 0]
    return dict(label=label, n=len(v), wr=round(100 * (v > 0).mean(), 1), mean=round(float(v.mean()), 2), lo=round(lo, 2), hi=round(hi, 2),
                pf=round(float(w.sum() / -l.sum()), 2) if len(l) else float('inf'), mdd=round(C.maxdd(v), 0), months=df['date'].str.slice(0, 7).n_unique(),
                cost=round(float(df['cost'].mean()), 2))


def marginal(agg, factor, ref, alts, note=''):
    out = []
    a = agg.with_columns(struct=pl.col('sk').str.slice(0, 1), kk=pl.col('sk').str.slice(1))
    if factor == 'struct': dims = ['kk', 'entry', 'tp', 'st', 'ex', 'filt']
    elif factor == 'kk': dims = ['struct', 'entry', 'tp', 'st', 'ex', 'filt']
    else: dims = [d for d in DIMS if d != factor]
    if factor == 'filt': a = a.filter(pl.col('entry') != '14:05')
    if factor not in ('ex',): a = a.filter(~pl.col('diag'))
    if factor == 'kk': a = a.filter(pl.col('struct') == 'S')
    base = a.filter(pl.col(factor).cast(pl.Utf8) == str(ref)).select(dims + ['wr', 'mean', 'lo', 'n'])
    for alt in alts:
        b = a.filter(pl.col(factor).cast(pl.Utf8) == str(alt)).select(dims + ['wr', 'mean', 'lo', 'n'])
        j = base.join(b, on=dims, suffix='_alt').filter((pl.col('n') >= 30) & (pl.col('n_alt') >= 30))
        if j.height == 0: continue
        dw = (j['wr_alt'] - j['wr']).to_numpy(); dm = (j['mean_alt'] - j['mean']).to_numpy(); dl = (j['lo_alt'] - j['lo']).to_numpy()
        out.append(dict(factor=factor, ref=str(ref), alt=str(alt), pairs=j.height, d_wr_median=round(float(np.median(dw)), 2), d_wr_mean=round(float(dw.mean()), 2),
                        share_wr_up=round(100 * float((dw > 0).mean()), 1), d_mean_median=round(float(np.median(dm)), 2), d_mean_mean=round(float(dm.mean()), 2),
                        share_mean_up=round(100 * float((dm > 0).mean()), 1), d_lo_median=round(float(np.nanmedian(dl)), 2), note=note))
    return out


def main(PER='TEST', OUTD=None):
    OUTD = OUTD or C.OUT
    sel_path = os.path.join(C.OUT, 'selection_train.json')        # full-chain TRAIN re-selection (this folder)
    sel_raw = open(sel_path).read(); sel = json.loads(sel_raw)
    sel_sha = hashlib.sha256(sel_raw.encode()).hexdigest()
    train = pl.read_csv(os.path.join(C.OUT, 'grid_train.csv.gz'))
    summary = {'selection_sha256': sel_sha, 'scopes': {}}
    grids = []; sel_rows = []; base_rows = []; marg_rows = []; wr_rows = []; per_year = []
    for scope in A.SCOPES:
        if scope not in sel['scopes']: print('no selection for', scope); continue
        agg, bm, (T, days, Lf) = A.grid_period(scope, PER, seeds=(7, 8))
        if agg is None: print('no TEST data for', scope); continue
        tr = train.filter(pl.col('scope') == scope).select(['cfg'] + [c for c in agg.columns if c not in ('cfg', 'scope', 'period') + tuple(DIMS) + ('dup', 'diag')])
        tr = tr.rename({c: 'train_' + c for c in tr.columns if c != 'cfg'})
        te = agg.rename({c: 'test_' + c for c in agg.columns if c not in ['cfg', 'scope'] + DIMS + ['dup', 'diag']}).drop('test_period')
        G = te.join(tr, on='cfg', how='left')
        grids.append(G)
        # -------- full-grid TEST distribution, chance count, reality check
        cfgs, point, mats, nn = bm
        idx = {c: i for i, c in enumerate(cfgs)}
        dist = agg.filter(~pl.col('diag') & ~pl.col('dup'))
        ci = np.array([idx[c] for c in dist['cfg'].to_list()])
        lo = dist['lo'].to_numpy(); se = dist['se'].to_numpy(); n = dist['n'].to_numpy(); mu = point[ci]
        D8 = mats[8][:, ci] - mu[None, :]
        thr = mu - lo
        with np.errstate(invalid='ignore'):
            cnt = np.nansum(D8 > thr[None, :], axis=1)
        tr70 = train.filter((pl.col('scope') == scope) & (pl.col('wr') >= 70))['cfg'].to_list()
        m70 = np.isin(dist['cfg'].to_numpy(), tr70)
        with np.errstate(invalid='ignore'):
            cnt70 = np.nansum((D8 > thr[None, :])[:, m70], axis=1)
        valid = (n >= 30) & (se > 0) & np.isfinite(se)
        t = np.where(valid, mu / np.where(valid, se, 1), -np.inf)
        Z = D8[:, valid] / se[valid][None, :]
        maxZ = np.nanmax(Z, axis=1)
        p_rc = float((maxZ >= t[valid].max()).mean())
        # Romano-Wolf step-down
        active = np.ones(valid.sum(), bool); tv = t[valid]; rejected = np.zeros(valid.sum(), bool)
        while True:
            crit = np.quantile(np.nanmax(Z[:, active], axis=1), 0.95) if active.any() else np.inf
            new = active & (tv > crit)
            if not new.any(): break
            rejected |= new; active &= ~new
        best = dist['cfg'].to_numpy()[valid][int(np.argmax(tv))]
        obj = dist.filter((pl.col('lo') > 0) & (pl.col('wr') >= 70))
        summary['scopes'][scope] = dict(
            distinct_configs=int(dist.height), test_days=len(days), lb_pos=int((lo > 0).sum()), lb_pos_and_wr70=int(obj.height),
            chance_lb_pos_mean=round(float(cnt.mean()), 1), chance_lb_pos_p95=float(np.percentile(cnt, 95)),
            train_wr70_configs=int(m70.sum()), lb_pos_among_train_wr70=int(((lo > 0) & m70).sum()),
            chance_among_train_wr70_mean=round(float(cnt70.mean()), 1), chance_among_train_wr70_p95=float(np.percentile(cnt70, 95)),
            wr70=int((dist['wr'].to_numpy() >= 70).sum()),
            rc_configs=int(valid.sum()), rc_best_cfg=str(best), rc_best_t=round(float(tv.max()), 3), rc_p=round(p_rc, 4),
            rc_crit95=round(float(np.quantile(maxZ, 0.95)), 3), romano_wolf_rejections=int(rejected.sum()),
            rw_rejected=[str(x) for x in dist['cfg'].to_numpy()[valid][rejected]],
            test_lb_quantiles={q: round(float(np.nanpercentile(lo, q)), 2) for q in (5, 25, 50, 75, 95, 100)},
            spearman_train_test_mean=round(spearman(G.filter(~pl.col('diag') & ~pl.col('dup'))['train_mean'], G.filter(~pl.col('diag') & ~pl.col('dup'))['test_mean']), 3),
            spearman_wr_mean_train=round(spearman(G.filter(~pl.col('diag') & ~pl.col('dup'))['train_wr'], G.filter(~pl.col('diag') & ~pl.col('dup'))['train_mean']), 3),
            spearman_wr_mean_test=round(spearman(dist['wr'], dist['mean']), 3),
            objective_test_configs=obj.sort('lo', descending=True).select(['cfg', 'n', 'wr', 'mean', 'lo']).head(30).rows())
        del D8, Z
        # -------- selections on TEST, baselines, gate
        Ttest = T
        # pre-registered selections S1/S2, plus POST-HOC (not pre-registered) TRAIN-only selections restricted to the E1 exit,
        # added after the TEST results showed that E2's advantage is mostly the unpriced after-hours exercise risk (diagnostics.py)
        trs = train.filter((pl.col('scope') == scope) & ~pl.col('diag') & (pl.col('n') >= 100) & pl.col('lo').is_not_nan() & (pl.col('ex') == 'E1'))
        trs = trs.sort(['lo', 'mean', 'cfg'], descending=[True, True, False])
        keep = ['cfg', 'n', 'wr', 'mean', 'lo', 'hi', 'pf', 'mdd', 'months', 'credit', 'cost']
        ph1 = {k: trs.row(0, named=True)[k] for k in keep}
        t70 = trs.filter(pl.col('wr') >= 70)
        ph2 = {k: t70.row(0, named=True)[k] for k in keep} if t70.height else None
        osel = json.load(open(os.path.join(C.ORIG, 'results', 'selection_train.json')))['scopes'].get(scope, {})
        trg = train.filter(pl.col('scope') == scope)
        rw_set = set(summary['scopes'][scope]['rw_rejected'])
        for tag, s in (('S1', sel['scopes'][scope]['S1']), ('S2', sel['scopes'][scope]['S2']), ('S1-orig', osel.get('S1')), ('S2-orig', osel.get('S2')),
                       ('PH-S1-E1', ph1), ('PH-S2-E1', ph2)):
            if not s: continue
            cfg = s['cfg']; sk, e, tp, st, ex, f = cfg.split('|'); tp = int(tp[2:]); st = int(st[2:])
            r = agg.filter(pl.col('cfg') == cfg).row(0, named=True)
            tf = trg.filter(pl.col('cfg') == cfg).row(0, named=True)            # TRAIN metrics on the complete (full-chain) TRAIN data
            lane = lane_trades(Lf, cfg).sort(['date', 'tk'])
            bs = [baseline(Ttest, sk, tp, st, ex, f, sd) for sd in C.RAND_SEEDS]
            bmeans = [float(b['pnl'].mean()) if b.height else float('nan') for b in bs]
            ball = pl.concat(bs)
            bavg = ball.group_by(['tk', 'date']).agg(pl.col('pnl').mean().alias('b'), pl.len().alias('nb'))
            pair = lane.join(bavg, on=['tk', 'date'], how='inner').with_columns((pl.col('pnl') - pl.col('b')).alias('d')).sort(['date', 'tk'])
            dlo, dhi = C.boot_ci(pair['d'].to_numpy(), pair['date'].to_list())
            base_only = ball.join(lane.select(['tk', 'date']), on=['tk', 'date'], how='anti')
            lane_only = lane.join(bavg.select(['tk', 'date']), on=['tk', 'date'], how='anti')
            bmean = float(np.nanmean(bmeans)); diff = r['mean'] - bmean
            pdiff = float(pair['d'].mean()) if pair.height else float('nan')
            lo_bonf = boot_lo_q(lane['pnl'].to_numpy(), lane['date'].to_list(), 100 * 0.05 / N_PREREG / 2)
            gate = dict(lb_pos=bool(r['lo'] > 0), n150=bool(r['n'] >= 150), months3=bool(r['months'] >= 3), beats_random=bool(diff > r['cost']))
            # comparison with the original band-data run of the same configuration
            O = orig_lane(scope, PER, cfg)
            if O is not None:
                common = lane.join(O.select(['tk', 'date', 'pnl']), on=['tk', 'date'], how='inner', suffix='_orig')
                new_only = lane.join(O.select(['tk', 'date']), on=['tk', 'date'], how='anti').sort('pnl')
                gone = O.join(lane.select(['tk', 'date']), on=['tk', 'date'], how='anti')
                cmp = dict(orig_n=O.height, orig_mean=round(float(O['pnl'].mean()), 2), common_n=common.height,
                           common_max_abs_diff=round(float((common['pnl'] - common['pnl_orig']).abs().max()), 4) if common.height else float('nan'),
                           new_only_n=new_only.height, new_only_sum=round(float(new_only['pnl'].sum()), 2),
                           new_only_mean=round(float(new_only['pnl'].mean()), 2) if new_only.height else float('nan'),
                           new_only_worst='; '.join(f"{a} {b} {c:.0f}" for a, b, c in new_only.select(['tk', 'date', 'pnl']).head(5).rows()),
                           orig_only_n=gone.height)
            else:
                cmp = {}
            row = dict(scope=scope, selection=tag, cfg=cfg, desc=A.fmt_cfg(cfg),
                       sel_train_n=s['n'], sel_train_wr=s['wr'], sel_train_mean=s['mean'], sel_train_lo=s['lo'], sel_train_hi=s['hi'],
                       train_n=tf['n'], train_wr=tf['wr'], train_mean=tf['mean'], train_lo=tf['lo'], train_hi=tf['hi'],
                       test_n=r['n'], test_wr=r['wr'], test_mean=r['mean'], test_lo=r['lo'], test_hi=r['hi'], test_lo_bonf8=round(lo_bonf, 2),
                       rw_rejected_test=cfg in rw_set, test_pf=r['pf'], test_mdd=r['mdd'],
                       test_worst5=r['worst5'], test_worst_trade=r['worst_trade'], test_months=r['months'], test_credit=r['credit'], test_cost=r['cost'],
                       base_mean=round(bmean, 2), base_seed_means='; '.join(f'{x:.2f}' for x in bmeans), base_n=ball.height,
                       lane_minus_base=round(diff, 2), paired_diff=round(pdiff, 2) if pair.height else float('nan'),
                       paired_lo=round(dlo, 2), paired_hi=round(dhi, 2), paired_n=pair.height,
                       matched_lane_mean=round(float(pair['pnl'].mean()), 2), matched_base_mean=round(float(pair['b'].mean()), 2),
                       base_only_trades=base_only.height, base_only_days=base_only.select(['tk', 'date']).unique().height,
                       base_only_mean=round(float(base_only['pnl'].mean()), 2) if base_only.height else float('nan'),
                       lane_only_trades=lane_only.height,
                       gate_lb_pos=gate['lb_pos'], gate_n150=gate['n150'], gate_months3=gate['months3'], gate_beats_random=gate['beats_random'],
                       gate_pass=all(gate.values()), gate_beats_random_matched=bool(pdiff > r['cost']), objective_wr70=bool(r['wr'] >= 70), **cmp)
            sel_rows.append(row)
            for b, sd in zip(bs, C.RAND_SEEDS):
                base_rows.append(dict(scope=scope, selection=tag, cfg=cfg, seed=sd, **{k: v for k, v in summarize(b, f'r{sd}').items() if k != 'label'}))
            for y in sorted(set(d[:4] for d in days)):
                per_year.append(dict(scope=scope, selection=tag, cfg=cfg, period=PER, year=y, **{k: v for k, v in summarize(lane.filter(pl.col('date').str.starts_with(y)), y).items() if k != 'label'}))
        # -------- marginal effects (TEST here; TRAIN from grid_train)
        for per, tab in (('TRAIN', train.filter(pl.col('scope') == scope)), ('TEST', agg)):
            ms = []
            ms += marginal(tab, 'tp', 0, [25, 50]); ms += marginal(tab, 'st', 0, [1, 2]); ms += marginal(tab, 'st', 2, [1])
            ms += marginal(tab, 'ex', 'E1', ['E2', 'E0'], 'E0 = diagnostic buy-back-all at 15:55'); ms += marginal(tab, 'ex', 'E0', ['E1'], 'leave-cheap-legs effect')
            ms += marginal(tab, 'filt', 'F0', ['F1', 'F2', 'F3'], 'entries other than 14:05')
            ms += marginal(tab, 'struct', 'S', ['I'], 'iron condor vs strangle at the same k')
            ms += marginal(tab, 'kk', '0', ['0.5', '1', '1.5'], 'strangle k vs straddle')
            ms += marginal(tab, 'entry', '13:00', ['10:00', '11:00', '14:05'])
            for m in ms: marg_rows.append(dict(scope=scope, period=per, **m))
        # -------- win rate vs expectancy
        GG = G.filter(~pl.col('diag') & ~pl.col('dup'))
        bins = [(0, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 101)]
        for a_, b_ in bins:
            x = GG.filter((pl.col('train_wr') >= a_) & (pl.col('train_wr') < b_))
            if x.height == 0: continue
            wr_rows.append(dict(scope=scope, train_wr_bin=f'{a_}-{min(b_, 100)}', configs=x.height, train_mean_median=round(x['train_mean'].median(), 2),
                                train_lb_pos=int((x['train_lo'] > 0).sum()), test_wr_median=round(x['test_wr'].median(), 1),
                                test_mean_median=round(x['test_mean'].median(), 2), test_lb_pos=int((x['test_lo'] > 0).sum()),
                                test_mean_pos_share=round(100 * float((x['test_mean'] > 0).mean()), 1)))
        print(scope, json.dumps({k: v for k, v in summary['scopes'][scope].items() if k not in ('objective_test_configs', 'rw_rejected')}), flush=True)
    G = pl.concat(grids, how='diagonal_relaxed')
    G.write_csv(os.path.join(OUTD, 'grid.csv')); os.system(f"gzip -f {os.path.join(OUTD, 'grid.csv')}")
    pl.DataFrame(sel_rows).write_csv(os.path.join(OUTD, 'selected_test.csv'))
    pl.DataFrame(base_rows).write_csv(os.path.join(OUTD, 'baselines.csv'))
    pl.DataFrame(per_year).write_csv(os.path.join(OUTD, 'selected_by_year.csv'))
    pl.DataFrame(marg_rows).write_csv(os.path.join(OUTD, 'marginal_effects.csv'))
    pl.DataFrame(wr_rows).write_csv(os.path.join(OUTD, 'wr_vs_expectancy.csv'))
    json.dump(summary, open(os.path.join(OUTD, 'grid_test_summary.json'), 'w'), indent=1, default=str)
    coverage(OUTD)


def coverage(OUTD):
    rows = []
    for tk in C.TICKERS:
        for per in ('TRAIN', 'TEST'):
            if not A.have(tk, per): continue
            days = A.days_ok(tk, per)
            tr = pl.read_parquet(os.path.join(C.WORK, f'trades_{tk}_{per}.parquet')).filter(
                pl.col('entry').is_in(list(C.ENTRIES)) & (pl.col('tp') == 0) & (pl.col('st') == 0) & (pl.col('ex') == 'E1'))
            sk = pl.read_parquet(os.path.join(C.WORK, f'skips_{tk}_{per}.parquet')).filter(pl.col('entry').is_in(list(C.ENTRIES)))
            for (e, s), g in tr.group_by(['entry', 'sk']):
                ss = sk.filter((pl.col('entry') == e) & (pl.col('sk') == s))
                reasons = {r: int(c) for r, c in ss.group_by('reason').len().rows()}
                rows.append(dict(ticker=tk, period=per, entry=e, sk=s, sessions=len(days), trades=g.height, coverage=round(100 * g.height / len(days), 1),
                                 dprox_median=round(float(g['dprox'].median()), 3), credit_median=round(float(g['credit'].median()), 2),
                                 **{f'skip_{k}': v for k, v in reasons.items()}))
    pl.DataFrame(rows, infer_schema_length=None).sort(['ticker', 'period', 'sk', 'entry']).write_csv(os.path.join(OUTD, 'coverage.csv'))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'dryrun':   # exercise the code on TRAIN only (no TEST file is read)
        d = os.path.join(C.WORK, 'dryrun'); os.makedirs(d, exist_ok=True); main('TRAIN', d)
    else: main()
