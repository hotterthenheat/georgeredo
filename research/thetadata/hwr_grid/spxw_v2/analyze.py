#!/usr/bin/env python3
"""Grid analysis (../spxw/PREREGISTRATION.md G.6-G.10) -- v2 on complete chains with Cboe settlement.
v2 additions (reporting only; the pre-registered metrics, selection rule and gate are unchanged): the round-2 S1/S2 definitions
(../spxw/results/selection_train.json) and T-E's rule are evaluated on the complete data next to the re-selected S1/S2; the
random-baseline output adds the matched-day lane and random means and the unmatched-day counts; a Bonferroni(2) lower bound
(1.25th percentile) is reported for the two TRAIN selections.
  python3 analyze.py train   -> TRAIN metrics of every configuration and selection_train.json (no TEST date is loaded)
  python3 analyze.py test    -> TEST metrics, selected-configuration results, random baselines, gate, multiplicity,
                                factor effects, coverage, trade-off table, sizing  (requires selection_train.json)
Env: HWR_OUT (per-session trade files, default <scratchpad>/hwr_grid/spxw), RES_DIR (default ./results)."""
import os, sys, json, glob, hashlib, datetime as dt
import numpy as np, pandas as pd, polars as pl
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import sim  # noqa: E402
from stats import Boot, basic, max_dd, kelly_capital, path_stats  # noqa: E402

OUT = os.environ.get('HWR_OUT', sim.L.SP + '/hwr_grid/spxw_v2')
ORIG_SEL = os.path.join(HERE, '..', 'spxw', 'results', 'selection_train.json')
TE_RULE = 'N0.0|13:00|tp0|st0|E2|F4|P'
RES = os.environ.get('RES_DIR', os.path.join(HERE, 'results')); os.makedirs(RES, exist_ok=True)
PER = {'TRAIN': ('2022-05-13', '2024-12-31'), 'TEST': ('2025-01-02', '2026-10-09')}
if os.environ.get('HWR_DEV'):   # code test on early TRAIN dates only (never used for results)
    PER = {'TRAIN': ('2022-05-13', '2022-12-31'), 'TEST': ('2023-01-01', '2023-06-30')}
CELLS = [f'{s}{k:.1f}' for s in 'NW' for k in sim.KS]
FIXED = sim.ENTRIES; RANDS = [f'R{d}' for d in range(1, 6)]
EXITS = ['E0', 'E1', 'E2']; FILTERS = ['F0', 'F1', 'F2', 'F3', 'F4']
FNAME = {'F0': 'none', 'F1': 'skip FOMC', 'F2': 'FOMC days at 14:05', 'F3': 'skip FOMC + month-end', 'F4': 'skip FOMC/CPI/NFP'}
CELLNAME = {'N0.0': 'short straddle', 'N0.5': 'short strangle k=0.5', 'N1.0': 'short strangle k=1.0', 'N1.5': 'short strangle k=1.5',
            'W0.0': 'iron butterfly (wings 1.0 EM)', 'W0.5': 'iron condor k=0.5', 'W1.0': 'iron condor k=1.0', 'W1.5': 'iron condor k=1.5'}
COLS = ['date', 'entry', 'cell', 'tp', 'stop', 'exit', 'pnl', 'pnl_adv', 'rt_cost', 'credit', 'wing_bid0', 'how', 'max_loss_struct']


def topd(df):
    return pd.DataFrame({c: df[c].to_numpy() for c in df.columns})


def load(stage):
    files = sorted(glob.glob(OUT + '/trades/*.parquet'))
    hi = PER['TRAIN'][1] if stage == 'train' else '9999'
    files = [f for f in files if os.path.basename(f)[:10] <= hi]
    T = topd(pl.concat([pl.read_parquet(f, columns=COLS) for f in files]))
    sk = topd(pl.concat([pl.read_parquet(f) for f in sorted(glob.glob(OUT + '/skips/*.parquet')) if os.path.basename(f)[:10] <= hi], how='diagonal'))   # v2: skip files may carry chain_src
    return T, sk[sk['reason'] != 'none']


def flags(dates):
    ev = pd.read_csv(sim.EVENTS_CSV)
    allses = sim.regular_sessions('2022-05-01', '2026-10-31')
    fullcal = sim.L.trading_sessions('2022-05-01', '2026-10-31')   # month-end from the full NYSE calendar (early closes are sessions)
    me = {d for i, d in enumerate(fullcal[:-1]) if d[:7] != fullcal[i + 1][:7]}
    f = pd.DataFrame({'date': dates})
    for e in ('FOMC', 'CPI', 'NFP'): f[e.lower()] = f['date'].isin(set(ev.loc[ev['event'] == e, 'date'])).values
    f['month_end'] = f['date'].isin(me).values & (f['date'] != '2026-10-09')
    return f, allses


class Grid:
    def __init__(self, T, dates):
        self.dates = np.array(dates); self.di = {d: i for i, d in enumerate(dates)}; nd = len(dates)
        self.keys = {}
        T = T.copy(); T['tp'] = T['tp'].round(2); T['stop'] = T['stop'].round(1)
        T['key'] = T['cell'] + '|' + T['entry'] + '|' + T['tp'].astype(str) + '|' + T['stop'].astype(str) + '|' + T['exit']
        ukeys = sorted(T['key'].unique()); kid = {k: i for i, k in enumerate(ukeys)}; self.kid = kid
        shape = (len(ukeys), nd)
        self.A = {c: np.full(shape, np.nan) for c in ('pnl', 'pnl_adv', 'rt_cost', 'credit', 'max_loss_struct')}
        self.W0 = np.zeros(shape, bool)
        r = T['key'].map(kid).values; c = T['date'].map(self.di).values
        for col in self.A: self.A[col][r, c] = T[col].values
        self.W0[r, c] = T['wing_bid0'].values.astype(bool)

    def vec(self, cell, entry, tp, stop, ex, col, variant):
        k = f'{cell}|{entry}|{round(tp, 2)}|{round(stop, 1)}|{ex}'
        if k not in self.kid: return np.full(len(self.dates), np.nan)
        x = self.A[col][self.kid[k]].copy()
        if variant == 'P': x[self.W0[self.kid[k]]] = np.nan
        return x

    def config(self, cell, entry, tp, stop, ex, F, variant, fl, col='pnl'):
        x = self.vec(cell, entry, tp, stop, ex, col, variant)
        fomc = fl['fomc'].values
        if F == 'F1': x[fomc] = np.nan
        elif F == 'F2' and entry != '14:05':
            alt = self.vec(cell, '14:05', tp, stop, ex, col, variant); x[fomc] = alt[fomc]
        elif F == 'F3': x[fomc | fl['month_end'].values] = np.nan
        elif F == 'F4': x[fomc | fl['cpi'].values | fl['nfp'].values] = np.nan
        return x


def enumerate_configs():
    rows = []
    for cell in CELLS:
        for variant in (('P', 'W') if cell[0] == 'W' else ('P',)):
            for e in FIXED:
                for tp in sim.TPS:
                    for st in sim.STOPS:
                        for ex in EXITS:
                            for F in FILTERS:
                                cid = f'{cell}|{e}|tp{int(tp*100)}|st{int(st)}|{ex}|{F}|{variant}'
                                dup = (F == 'F2' and e == '14:05')
                                rows.append(dict(cid=cid, cell=cell, structure=CELLNAME[cell], entry=e, tp=tp, stop=st, exit=ex, filter=F,
                                                 variant=variant, duplicate_of_F0=dup,
                                                 grid=(ex in ('E1', 'E2') and variant == 'P'), distinct=(ex in ('E1', 'E2') and variant == 'P' and not dup)))
    return pd.DataFrame(rows)


def eligible_sessions(F, fl, mask):
    m = mask.copy()
    if F == 'F1': m &= ~fl['fomc'].values
    elif F == 'F3': m &= ~(fl['fomc'].values | fl['month_end'].values)
    elif F == 'F4': m &= ~(fl['fomc'].values | fl['cpi'].values | fl['nfp'].values)
    return int(m.sum())


def period_metrics(G, cfg, fl, period, boot):
    lo, hi = PER[period]; pm = (G.dates >= lo) & (G.dates <= hi)
    recs = []; series = {}
    for r in cfg.itertuples(index=False):
        x = G.config(r.cell, r.entry, r.tp, r.stop, r.exit, r.filter, r.variant, fl)[pm]
        ok = np.isfinite(x); series[r.cid] = (x, ok)
    order = sorted(series, key=lambda c: series[c][1].sum())   # process by n so index matrices are reused
    out = {}
    d_p = G.dates[pm]
    for cid in order:
        x, ok = series[cid]; xv = x[ok]; dv = d_p[ok]
        b = basic(xv)
        lo_, hi_, se = boot.ci(xv)
        o = dict(b, ci_lo=lo_, ci_hi=hi_, se_boot=se)
        if len(xv):
            w = np.argsort(xv)[:5]; o['worst5'] = ' | '.join(f'{dv[i]} {xv[i]:.0f}' for i in w)
            o['worst_day'] = float(xv.min()); o['best_day'] = float(xv.max())
            o['first'] = dv[0]; o['last'] = dv[-1]
            o['months'] = round((dt.date.fromisoformat(dv[-1]) - dt.date.fromisoformat(dv[0])).days / 30.44, 1)
        out[cid] = o
    # secondary columns (cheap)
    for r in cfg.itertuples(index=False):
        x, ok = series[r.cid]; o = out[r.cid]
        o['eligible_sessions'] = eligible_sessions(r.filter, fl[pm].reset_index(drop=True), np.ones(pm.sum(), bool))
        o['coverage'] = o['n'] / o['eligible_sessions'] if o['eligible_sessions'] else np.nan
        for col, nm in (('credit', 'mean_credit'), ('rt_cost', 'mean_rt_cost'), ('pnl_adv', 'mean_adverse')):
            v = G.config(r.cell, r.entry, r.tp, r.stop, r.exit, r.filter, r.variant, fl, col)[pm]
            o[nm] = float(np.nanmean(v)) if np.isfinite(v).any() else np.nan
    df = pd.DataFrame.from_dict(out, orient='index'); df.index.name = 'cid'
    return df.add_prefix(period.lower() + '_').reset_index()


def selection(train, cfg):
    t = cfg.merge(train, on='cid')
    el = t[t['distinct'] & (t['train_n'] >= 150)].copy()
    el = el.sort_values(['train_ci_lo', 'train_mean', 'cid'], ascending=[False, False, True])
    s1 = el.iloc[0]
    e70 = el[el['train_win_rate'] >= 0.70]
    s2 = e70.iloc[0] if len(e70) else None
    top = el.head(10)
    pick = lambda r: None if r is None else {k: (v.item() if hasattr(v, 'item') else v) for k, v in r[['cid', 'structure', 'entry', 'tp', 'stop', 'exit', 'filter', 'train_n', 'train_mean', 'train_ci_lo', 'train_ci_hi', 'train_win_rate', 'train_pf', 'train_max_dd']].items()}
    return dict(written_utc=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                rule='eligible: distinct grid configurations (E1/E2, literal zero-bid rule, F2@14:05 duplicates dropped) with TRAIN n >= 150; S1 = max TRAIN lower bound; S2 = max TRAIN lower bound with TRAIN win rate >= 0.70; ties: TRAIN mean, then id',
                n_eligible=int(len(el)), n_eligible_wr70=int(len(e70)), S1=pick(s1), S2=pick(s2), top10=[pick(r) for _, r in top.iterrows()])


def stage_train():
    T, sk = load('train')
    dates = sorted(T['date'].unique()); fl, _ = flags(dates)
    G = Grid(T, dates); cfg = enumerate_configs()
    boot = Boot()
    tr = period_metrics(G, cfg, fl, 'TRAIN', boot)
    tr.to_csv(os.path.join(RES, 'train_metrics.csv.gz'), index=False, float_format='%.6g')
    sel = selection(tr, cfg)
    h = hashlib.sha256(open(os.path.join(RES, 'train_metrics.csv.gz'), 'rb').read()).hexdigest()
    sel['train_metrics_sha256'] = h; sel['train_sessions'] = len(dates); sel['train_last_date'] = dates[-1]
    json.dump(sel, open(os.path.join(RES, 'selection_train.json'), 'w'), indent=1, default=str)
    print(json.dumps(sel, indent=1, default=str)[:3000])


# ------------------------------------------------------------------------------------------------------------------ TEST stage
def joint_multiplicity(G, cfg, fl, met, period, seed=8, n_draws=5000):
    """Chance count of lower bounds > 0 under the global null and studentised max-t reality check / Romano-Wolf."""
    lo, hi = PER[period]; pm = (G.dates >= lo) & (G.dates <= hi); D = int(pm.sum())
    c = cfg[cfg['distinct']].merge(met, on='cid')
    X = np.column_stack([G.config(r.cell, r.entry, r.tp, r.stop, r.exit, r.filter, r.variant, fl)[pm] for r in c.itertuples(index=False)])
    Tm = np.isfinite(X); X0 = np.where(Tm, X, 0.0)
    p = period.lower()
    mean = c[f'{p}_mean'].values; half = mean - c[f'{p}_ci_lo'].values; se = c[f'{p}_se_boot'].values; n = c[f'{p}_n'].values
    rng = np.random.default_rng(seed); idx = rng.integers(0, D, (n_draws, D))
    cnt = np.zeros((n_draws, D));
    for b in range(n_draws): cnt[b] = np.bincount(idx[b], minlength=D)
    S1 = cnt @ X0; N = cnt @ Tm.astype(float); S2 = cnt @ (X0 ** 2)
    with np.errstate(invalid='ignore', divide='ignore'):
        mstar = S1 / N; var = (S2 / N - mstar ** 2) * N / (N - 1); sestar = np.sqrt(var / N)
        d = mstar - mean[None, :]
        chance = ((d > half[None, :]) & np.isfinite(half)[None, :]).sum(axis=1)
        tstar = d / sestar
    use = (n >= 30) & np.isfinite(se) & (se > 0)
    t_obs = np.where(use, mean / se, np.nan)
    obs_max = np.nanmax(t_obs)
    obs_lb = int((c[f'{p}_ci_lo'] > 0).sum())
    res = dict(period=period, configs=int(len(c)), configs_in_max_stat=int(use.sum()), draws=n_draws, seed=seed,
               observed_lb_gt0=obs_lb, chance_mean=float(chance.mean()), chance_p95=float(np.percentile(chance, 95)),
               chance_p99=float(np.percentile(chance, 99)), p_chance_ge_observed=float((chance >= obs_lb).mean()),
               observed_max_t=float(obs_max), argmax_t=c['cid'].values[np.nanargmax(t_obs)],
               se_ratio_boot_vs_analytic_median=float(np.nanmedian(se / (c[f'{p}_sd'].values / np.sqrt(n)))))
    # (a) primary (Amendment 1): t*_c = (mean*_c - mean_c) / se_c with se_c the configuration's seed-7 bootstrap s.e.;
    # (b) within-draw studentisation (se* from each draw), reported for completeness
    for tag, tst in (('fixed_se', d / se[None, :]), ('within_draw_se', tstar)):
        tmax = np.nanmax(np.where(use[None, :], tst, -np.inf), axis=1)
        rejected = np.zeros(len(c), bool); active = use.copy(); crit = []
        while True:
            tm = np.nanmax(np.where(active[None, :], tst, -np.inf), axis=1); cv = float(np.percentile(tm, 95)); crit.append(cv)
            new = active & (t_obs > cv)
            if not new.any(): break
            rejected |= new; active &= ~new
        res[f'{tag}_reality_check_p'] = float((tmax >= obs_max).mean()); res[f'{tag}_max_t_p95'] = float(np.percentile(tmax, 95))
        res[f'{tag}_romano_wolf_rejections'] = int(rejected.sum()); res[f'{tag}_rw_critical_values'] = crit
        res[f'{tag}_romano_wolf_rejected'] = list(c['cid'].values[rejected][:50])
    return res


def baseline(G, r, fl, period, boot):
    """Lane minus the per-date mean of the five random-entry draws (same structure, k, TP, stop, exit, filter)."""
    lo, hi = PER[period]; pm = (G.dates >= lo) & (G.dates <= hi)
    lane = G.config(r['cell'], r['entry'], r['tp'], r['stop'], r['exit'], r['filter'], r['variant'], fl)[pm]
    draws = []
    for R in RANDS:
        x = G.vec(r['cell'], R, r['tp'], r['stop'], r['exit'], 'pnl', r['variant'])
        fomc = fl['fomc'].values
        F = r['filter']
        if F == 'F1': x[fomc] = np.nan
        elif F == 'F2':
            alt = G.vec(r['cell'], '14:05', r['tp'], r['stop'], r['exit'], 'pnl', r['variant']); x[fomc] = alt[fomc]
        elif F == 'F3': x[fomc | fl['month_end'].values] = np.nan
        elif F == 'F4': x[fomc | fl['cpi'].values | fl['nfp'].values] = np.nan
        draws.append(x[pm])
    Dm = np.vstack(draws)
    out = []
    for i, R in enumerate(RANDS):
        v = Dm[i][np.isfinite(Dm[i])]; b = basic(v); l, h, _ = boot.ci(v)
        out.append(dict(label=f'random draw {R} (seed {10 + i + 1})', n=b['n'], mean=b['mean'], ci_lo=l, ci_hi=h, win_rate=b['win_rate'], pf=b['pf'], max_dd=b['max_dd']))
    with np.errstate(all='ignore'):
        bm = np.nanmean(Dm, axis=0)
    ok = np.isfinite(lane) & np.isfinite(bm)
    diff = lane[ok] - bm[ok]; l, h, _ = boot.ci(diff)
    pooled = Dm[np.isfinite(Dm)]
    out.append(dict(label='five draws pooled (trade-level)', n=int(len(pooled)), mean=float(pooled.mean()), ci_lo=np.nan, ci_hi=np.nan,
                    win_rate=float((pooled > 0).mean()), pf=np.nan, max_dd=np.nan))
    # v2: matched-day decomposition
    lm = lane[ok]; l1, h1, _ = boot.ci(lm); b1 = bm[ok]; l2, h2, _ = boot.ci(b1)
    out.append(dict(label='matched days: lane', n=int(ok.sum()), mean=float(lm.mean()), ci_lo=l1, ci_hi=h1, win_rate=float((lm > 0).mean()), pf=np.nan, max_dd=max_dd(lm)))
    out.append(dict(label='matched days: per-date mean of the five draws', n=int(ok.sum()), mean=float(b1.mean()), ci_lo=l2, ci_hi=h2, win_rate=np.nan, pf=np.nan, max_dd=max_dd(b1)))
    out.append(dict(label='lane days with no random trade', n=int((np.isfinite(lane) & ~np.isfinite(bm)).sum()), mean=float(np.nanmean(np.where(np.isfinite(bm), np.nan, lane))) if (np.isfinite(lane) & ~np.isfinite(bm)).any() else np.nan,
                    ci_lo=np.nan, ci_hi=np.nan, win_rate=np.nan, pf=np.nan, max_dd=np.nan))
    rnl = np.isfinite(bm) & ~np.isfinite(lane)
    out.append(dict(label='random days with no lane trade (per-date mean)', n=int(rnl.sum()), mean=float(bm[rnl].mean()) if rnl.any() else np.nan,
                    ci_lo=np.nan, ci_hi=np.nan, win_rate=np.nan, pf=np.nan, max_dd=np.nan))
    nd = np.isfinite(Dm).sum(axis=0)[ok]
    out.append(dict(label='matched days: draws present per day (mean / min)', n=int(ok.sum()), mean=float(nd.mean()), ci_lo=float(nd.min()), ci_hi=np.nan,
                    win_rate=np.nan, pf=np.nan, max_dd=np.nan))
    out.append(dict(label='lane minus per-date mean of the five draws', n=int(ok.sum()), mean=float(diff.mean()), ci_lo=l, ci_hi=h,
                    win_rate=np.nan, pf=np.nan, max_dd=np.nan))
    return out, float(diff.mean())


def matched_effects(cfg, met):
    """Average paired change of mean and win rate when one rule changes and everything else is held fixed."""
    m = cfg[(cfg['variant'] == 'P')].merge(met, on='cid')
    m = m[~m['duplicate_of_F0']]
    dims = {'exit': ['E0', 'E1', 'E2'], 'tp': [0.0, 0.25, 0.5], 'stop': [0.0, 1.0, 2.0], 'filter': FILTERS, 'entry': FIXED}
    rows = []
    for dim, levels in dims.items():
        other = [c for c in ('cell', 'entry', 'tp', 'stop', 'exit', 'filter') if c != dim]
        if dim != 'exit': mm = m[m['exit'] != 'E0']
        else: mm = m
        base = levels[0]
        for lev in levels[1:]:
            a = mm[mm[dim] == base].set_index(other); b = mm[mm[dim] == lev].set_index(other)
            j = a.join(b, lsuffix='_a', rsuffix='_b', how='inner')
            for p in ('train', 'test'):
                dm = j[f'{p}_mean_b'] - j[f'{p}_mean_a']; dw = j[f'{p}_win_rate_b'] - j[f'{p}_win_rate_a']
                dl = j[f'{p}_ci_lo_b'] - j[f'{p}_ci_lo_a']
                rows.append(dict(dimension=dim, change=f'{base} -> {lev}', period=p.upper(), pairs=len(j), mean_delta_mean=dm.mean(), median_delta_mean=dm.median(),
                                 share_mean_up=(dm > 0).mean(), mean_delta_winrate=dw.mean(), share_winrate_up=(dw > 0).mean(), mean_delta_lb=dl.mean()))
        extra = {'exit': [('E1', 'E2')], 'filter': [('F1', 'F2'), ('F1', 'F3'), ('F1', 'F4')], 'tp': [(0.25, 0.5)], 'stop': [(1.0, 2.0)]}.get(dim, [])
        if extra:
            for x, y in extra:
                a = mm[mm[dim] == x].set_index(other); b = mm[mm[dim] == y].set_index(other)
                j = a.join(b, lsuffix='_a', rsuffix='_b', how='inner')
                for p in ('train', 'test'):
                    dm = j[f'{p}_mean_b'] - j[f'{p}_mean_a']; dw = j[f'{p}_win_rate_b'] - j[f'{p}_win_rate_a']; dl = j[f'{p}_ci_lo_b'] - j[f'{p}_ci_lo_a']
                    rows.append(dict(dimension=dim, change=f'{x} -> {y}', period=p.upper(), pairs=len(j), mean_delta_mean=dm.mean(), median_delta_mean=dm.median(),
                                     share_mean_up=(dm > 0).mean(), mean_delta_winrate=dw.mean(), share_winrate_up=(dw > 0).mean(), mean_delta_lb=dl.mean()))
    # winged vs naked at the same k
    a = m[(m['cell'].str[0] == 'N') & (m['exit'] != 'E0')].copy(); b = m[(m['cell'].str[0] == 'W') & (m['exit'] != 'E0')].copy()
    a['k'] = a['cell'].str[1:]; b['k'] = b['cell'].str[1:]
    key = ['k', 'entry', 'tp', 'stop', 'exit', 'filter']
    j = a.set_index(key).join(b.set_index(key), lsuffix='_a', rsuffix='_b', how='inner')
    for p in ('train', 'test'):
        dm = j[f'{p}_mean_b'] - j[f'{p}_mean_a']; dw = j[f'{p}_win_rate_b'] - j[f'{p}_win_rate_a']; dl = j[f'{p}_ci_lo_b'] - j[f'{p}_ci_lo_a']
        rows.append(dict(dimension='structure', change='naked -> winged (same k)', period=p.upper(), pairs=len(j), mean_delta_mean=dm.mean(), median_delta_mean=dm.median(),
                         share_mean_up=(dm > 0).mean(), mean_delta_winrate=dw.mean(), share_winrate_up=(dw > 0).mean(), mean_delta_lb=dl.mean()))
    return pd.DataFrame(rows)


def tradeoff(cfg, met):
    m = cfg[cfg['distinct']].merge(met, on='cid'); rows = []
    bins = [0, .5, .6, .7, .8, .9, 1.0001]; labs = ['<50%', '50-60%', '60-70%', '70-80%', '80-90%', '>=90%']
    for p in ('train', 'test'):
        mm = m[m[f'{p}_n'] >= 30].copy(); mm['wr_bin'] = pd.cut(mm[f'{p}_win_rate'], bins, labels=labs, right=False)
        for fam, sub in (('all', mm), ('naked', mm[mm['cell'].str[0] == 'N']), ('winged', mm[mm['cell'].str[0] == 'W'])):
            for lab, g in sub.groupby('wr_bin', observed=False):
                if not len(g): continue
                rows.append(dict(period=p.upper(), family=fam, win_rate_bin=lab, configs=len(g), median_mean=g[f'{p}_mean'].median(),
                                 mean_mean=g[f'{p}_mean'].mean(), share_mean_gt0=(g[f'{p}_mean'] > 0).mean(), lb_gt0=int((g[f'{p}_ci_lo'] > 0).sum()),
                                 median_pf=g[f'{p}_pf'].median(), median_worst_day=g[f'{p}_worst_day'].median(), median_credit=g[f'{p}_mean_credit'].median(),
                                 median_mean_over_credit=(g[f'{p}_mean'] / (100 * g[f'{p}_mean_credit'])).median()))
    return pd.DataFrame(rows)


def coverage(G, cfg, fl, sk, T):
    rows = []
    for p, (lo, hi) in PER.items():
        pm = (G.dates >= lo) & (G.dates <= hi); nses = int(pm.sum())
        for cell in CELLS:
            for e in FIXED:
                x = G.vec(cell, e, 0.0, 0.0, 'E2', 'pnl', 'W')[pm]; xp = G.vec(cell, e, 0.0, 0.0, 'E2', 'pnl', 'P')[pm]
                s = sk[(sk['cell'] == cell) & (sk['entry'] == e) & (sk['date'] >= lo) & (sk['date'] <= hi)]['reason'].value_counts().to_dict()
                rows.append(dict(period=p, cell=cell, structure=CELLNAME[cell], entry=e, sessions=nses, trades_literal=int(np.isfinite(xp).sum()),
                                 trades_wing0_allowed=int(np.isfinite(x).sum()), coverage_literal=float(np.isfinite(xp).sum() / nses),
                                 skip_out_of_band=s.get('out_of_band', 0), skip_zero_bid_short=s.get('zero_bid', 0),
                                 skip_zero_bid_wing=int(np.isfinite(x).sum() - np.isfinite(xp).sum()), skip_no_quote=s.get('no_quote', 0),
                                 skip_no_credit=s.get('no_credit', 0), skip_no_spot=s.get('no_spot', 0)))
    return pd.DataFrame(rows)


def stage_test():
    sel = json.load(open(os.path.join(RES, 'selection_train.json')))
    T, sk = load('test')
    dates = sorted(T['date'].unique()); fl, _ = flags(dates)
    G = Grid(T, dates); cfg = enumerate_configs(); boot = Boot()
    tr = pd.read_csv(os.path.join(RES, 'train_metrics.csv.gz'))
    assert hashlib.sha256(open(os.path.join(RES, 'train_metrics.csv.gz'), 'rb').read()).hexdigest() == sel['train_metrics_sha256']
    te = period_metrics(G, cfg, fl, 'TEST', boot)
    met = tr.merge(te, on='cid')
    full = cfg.merge(met, on='cid')
    full.to_csv(os.path.join(RES, 'grid_configs.csv.gz'), index=False, float_format='%.6g')
    # selected configurations (v2: plus the round-2 S1/S2 definitions and T-E's rule, evaluated on the complete data)
    osel = json.load(open(ORIG_SEL))
    picks = [('S1', sel['S1']), ('S2', sel['S2']), ('orig_S1', osel['S1']), ('orig_S2', osel['S2']), ('TE_rule', {'cid': TE_RULE})] + \
            [(f'top{i + 1}', r) for i, r in enumerate(sel['top10'])]
    srows, brows, gate = [], [], []
    for lab, s in picks:
        if s is None: continue
        r = full[full['cid'] == s['cid']].iloc[0]
        srows.append(dict(selection=lab, **{k: r[k] for k in full.columns if k in ('cid', 'structure', 'entry', 'tp', 'stop', 'exit', 'filter') or k.startswith('train_') or k.startswith('test_')}))
        if lab in ('S1', 'S2', 'orig_S1', 'orig_S2', 'TE_rule'):
            for p in ('TRAIN', 'TEST'):
                b, dmean = baseline(G, r, fl, p, boot)
                for x in b: brows.append(dict(selection=lab, cid=r['cid'], period=p, **x))
                if p == 'TEST':
                    g = dict(selection=lab, cid=r['cid'], test_n=r['test_n'], test_mean=r['test_mean'], test_ci_lo=r['test_ci_lo'], test_ci_hi=r['test_ci_hi'],
                             test_win_rate=r['test_win_rate'], test_months=r['test_months'], test_mean_rt_cost=r['test_mean_rt_cost'], lane_minus_random=dmean,
                             test_mean_adverse=r['test_mean_adverse'])
                    g['C1_lb_gt0'] = bool(r['test_ci_lo'] > 0); g['C2_n150_3m'] = bool(r['test_n'] >= 150 and r['test_months'] >= 3)
                    g['C2_beats_random_by_rt'] = bool(dmean > r['test_mean_rt_cost']); g['C3_adverse_mean_gt0'] = bool(r['test_mean_adverse'] > 0)
                    g['WR70'] = bool(r['test_win_rate'] >= 0.70)
                    g['PASS_all'] = all(g[k] for k in ('C1_lb_gt0', 'C2_n150_3m', 'C2_beats_random_by_rt', 'C3_adverse_mean_gt0'))
                    g['PASS_all_and_WR70'] = g['PASS_all'] and g['WR70']
                    # v2: carry-lane statistical items (COMPASS section 10: no random-entry item) and a Bonferroni(2) bound
                    xx = G.config(r['cell'], r['entry'], r['tp'], r['stop'], r['exit'], r['filter'], r['variant'], fl)
                    pte_ = (G.dates >= PER['TEST'][0]) & (G.dates <= PER['TEST'][1]); xv = xx[pte_][np.isfinite(xx[pte_])]
                    mb = xv[boot.idx(len(xv))].mean(axis=1)
                    g['test_ci_lo_bonf2'] = float(np.percentile(mb, 1.25))
                    g['CARRY_stat_items'] = bool(g['C1_lb_gt0'] and g['C2_n150_3m'] and g['C3_adverse_mean_gt0'])
                    gate.append(g)
    pd.DataFrame(srows).to_csv(os.path.join(RES, 'selected_test.csv'), index=False, float_format='%.6g')
    pd.DataFrame(brows).to_csv(os.path.join(RES, 'selected_random_baseline.csv'), index=False, float_format='%.6g')
    pd.DataFrame(gate).to_csv(os.path.join(RES, 'gate.csv'), index=False, float_format='%.6g')
    # multiplicity
    mult = [joint_multiplicity(G, cfg, fl, met, p) for p in ('TRAIN', 'TEST')]
    json.dump(mult, open(os.path.join(RES, 'multiplicity.json'), 'w'), indent=1, default=str)
    # effects, trade-off, coverage
    matched_effects(cfg, met).to_csv(os.path.join(RES, 'rule_effects.csv'), index=False, float_format='%.6g')
    tradeoff(cfg, met).to_csv(os.path.join(RES, 'winrate_expectancy_tradeoff.csv'), index=False, float_format='%.6g')
    coverage(G, cfg, fl, sk, T).to_csv(os.path.join(RES, 'coverage.csv'), index=False, float_format='%.6g')
    # TEST WR>=70 & LB>0 (all distinct, descriptive) and sizing for TEST LB > 0
    d = full[full['distinct']]
    d[(d['test_win_rate'] >= 0.70) & (d['test_ci_lo'] > 0)].sort_values('test_ci_lo', ascending=False).to_csv(os.path.join(RES, 'test_wr70_lbpos.csv'), index=False, float_format='%.6g')
    pos = d[d['test_ci_lo'] > 0]
    sz = []
    ptr = (G.dates >= PER['TRAIN'][0]) & (G.dates <= PER['TRAIN'][1]); pte = (G.dates >= PER['TEST'][0]) & (G.dates <= PER['TEST'][1])
    for r in pos.itertuples(index=False):
        x = G.config(r.cell, r.entry, r.tp, r.stop, r.exit, r.filter, r.variant, fl)
        xtr = x[ptr][np.isfinite(x[ptr])]; xte = x[pte][np.isfinite(x[pte])]
        if len(xtr) == 0: continue
        ml = G.config(r.cell, r.entry, r.tp, r.stop, r.exit, r.filter, r.variant, fl, 'max_loss_struct')[ptr]
        loss = float(np.nanmax(ml)) if r.cell[0] == 'W' else float(-xtr.min())
        base = dict(cid=r.cid, structure=r.structure, test_n=r.test_n, test_mean=r.test_mean, test_ci_lo=r.test_ci_lo, test_win_rate=r.test_win_rate)
        for lab, C in (('kelly_train', kelly_capital(xtr)), ('kelly_test', kelly_capital(xte))):
            if C is None: sz.append(dict(base, rule=f'quarter-{lab}', full_kelly_capital=np.nan)); continue
            sz.append(dict(base, rule=f'quarter-{lab}', full_kelly_capital=round(C, 0), **path_stats(xte, 4 * C)))
        sz.append(dict(base, rule='max-loss 8% (TRAIN worst loss / structural max)', loss_basis=loss, **path_stats(xte, loss / 0.08)))
    pd.DataFrame(sz).to_csv(os.path.join(RES, 'sizing_test_lbpos.csv'), index=False, float_format='%.6g')
    print('done; distinct configs', int(cfg['distinct'].sum()), 'TEST LB>0', len(pos))


if __name__ == '__main__':
    {'train': stage_train, 'test': stage_test}[sys.argv[1]]()
