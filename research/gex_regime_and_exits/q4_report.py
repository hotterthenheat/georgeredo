"""Q4/Q5 report: per-configuration expectancy (mid/spread/adverse/spread+$0.01 floor), day-block and trade-level bootstrap CIs, PF, max DD,
IS/OOS split, exit-reason mix, White reality-check p-value for the best configuration, strategy-minus-random comparison, breakdowns."""
import collections, json
from common import *
NB = 2000
def load(name):
    z = np.load(OUT + f'/q4_grid_{name}.npz', allow_pickle=True); return {k: z[k] for k in z.files}
S = load('strategy'); Rn = load('random')
RNAME = ['', 'STOP', 'BREAKEVEN', 'TRAIL', 'T1', 'T2', 'TIME_STOP', 'CLOSE']
def analyse(Z, sel, label, seed=7):
    rng = np.random.default_rng(seed)
    cfg = Z['cfg']; C = len(cfg); U = Z['usd_spread'][:, sel].astype(float); N = U.shape[1]
    dates = Z['date'][sel]; ud, inv = np.unique(dates, return_inverse=True); D = len(ud)
    onehot = np.zeros((N, D)); onehot[np.arange(N), inv] = 1; cnt = onehot.sum(0)
    def day_boot(Umat, mask=None):
        m = np.ones(N, bool) if mask is None else mask
        Sd = Umat[:, m] @ onehot[m]; cd = onehot[m].sum(0)
        pick = rng.integers(0, D, size=(NB, D))
        return (Sd[:, pick].sum(2) / np.maximum(cd[pick].sum(1), 1)[None, :])  # C x NB
    B = day_boot(U); obs = U.mean(1)
    lo, hi = np.percentile(B, 2.5, axis=1), np.percentile(B, 97.5, axis=1)
    # trade-level bootstrap (as report.py)
    idx = rng.integers(0, N, size=(1000, N)); Bt = U[:, idx].mean(2); tlo, thi = np.percentile(Bt, 2.5, axis=1), np.percentile(Bt, 97.5, axis=1)
    # White reality check across configurations: max_c mean_c vs bootstrap max_c (mean*_c - mean_c)
    centred = B - obs[:, None]; rc_stat = obs.max(); rc_p = float((centred.max(0) >= rc_stat).mean())
    order = np.argsort(Z['entry_t'][sel]); cs = np.cumsum(U[:, order], axis=1); peak = np.maximum.accumulate(np.concatenate([np.zeros((C, 1)), cs], 1), axis=1)[:, 1:]; mdd = (cs - peak).min(1)
    pos = np.where(U > 0, U, 0).sum(1); neg = np.where(U < 0, U, 0).sum(1); pf = pos / np.maximum(-neg, 1e-9)
    ismask = dates < SPLIT; oos = ~ismask
    Bo = day_boot(U, oos); olo, ohi = np.percentile(Bo, 2.5, axis=1), np.percentile(Bo, 97.5, axis=1)
    hold = Z['exit_min'][:, sel] - Z['entry_min'][sel][None, :]
    rows = []
    for i in range(C):
        last = Z['last'][i, sel]; first = Z['first'][i, sel]; mix = collections.Counter(RNAME[x] for x in last)
        rows.append(dict(group=label, cfg=cfg[i], n=N, n_days=D, exp_mid=Z['usd_mid'][i, sel].mean(), exp_spread=obs[i], ci_lo_day=lo[i], ci_hi_day=hi[i], ci_lo_trade=tlo[i], ci_hi_trade=thi[i],
                         exp_adverse=Z['usd_adverse'][i, sel].mean(), exp_spread_floor=Z['usd_spread_floor'][i, sel].mean(), ret_spread_pct=100 * Z['ret_spread'][i, sel].mean(), ret_mid_pct=100 * Z['ret_mid'][i, sel].mean(),
                         wr=100 * (U[i] > 0).mean(), pf=pf[i], maxdd=mdd[i], total=U[i].sum(), is_n=int(ismask.sum()), is_exp=U[i, ismask].mean(), oos_n=int(oos.sum()), oos_exp=U[i, oos].mean(), oos_lo=olo[i], oos_hi=ohi[i],
                         hold_mean=float(np.nanmean(hold[i])), hold_median=float(np.nanmedian(hold[i])), t1_share=100 * (first == 4).mean(),
                         **{f'mix_{k}': 100 * mix.get(k, 0) / N for k in ('STOP', 'BREAKEVEN', 'TRAIL', 'T2', 'TIME_STOP', 'CLOSE')}))
    return rows, dict(group=label, n=N, n_days=D, best_cfg=cfg[int(obs.argmax())], best_exp=float(rc_stat), best_ci_lo_day=float(lo[obs.argmax()]), best_ci_hi_day=float(hi[obs.argmax()]), reality_check_p=rc_p,
                      n_cfg_lower_ci_above_zero_day=int((lo > 0).sum()), n_cfg_lower_ci_above_zero_trade=int((tlo > 0).sum()), n_cfg_exp_above_zero=int((obs > 0).sum()),
                      n_cfg_mid_exp_above_zero=int((Z['usd_mid'][:, sel].mean(1) > 0).sum()), best_is_cfg=cfg[int(U[:, ismask].mean(1).argmax())], best_is_cfg_oos_exp=float(U[int(U[:, ismask].mean(1).argmax()), oos].mean()),
                      best_is_cfg_oos_lo=float(olo[int(U[:, ismask].mean(1).argmax())]), best_is_cfg_oos_hi=float(ohi[int(U[:, ismask].mean(1).argmax())]), worst_cfg=cfg[int(obs.argmin())], worst_exp=float(obs.min()))
all_rows = []; heads = []
groups = [('strategy_sweep', S, S['variant'] == 'sweep|ict+gex|all|none|ladder'), ('strategy_continuation', S, S['variant'] == 'continuation|ict+gex|all|none|ladder'), ('strategy_pooled', S, np.ones(len(S['date']), bool)), ('random', Rn, np.ones(len(Rn['date']), bool))]
for label, Z, sel in groups:
    rows, head = analyse(Z, sel, label); all_rows += rows; heads.append(head); print('HEAD', json.dumps(head, default=float), flush=True)
write_csv(OUT + '/q4_grid_summary.csv', all_rows); write_csv(OUT + '/q4_group_heads.csv', heads)
# strategy-pooled minus random per configuration (joint day-block bootstrap on shared dates)
rng = np.random.default_rng(3); cfg = S['cfg']; C = len(cfg)
def daysums(Z):
    U = Z['usd_spread'].astype(float); ud, inv = np.unique(Z['date'], return_inverse=True); oh = np.zeros((U.shape[1], len(ud))); oh[np.arange(U.shape[1]), inv] = 1
    return ud, U @ oh, oh.sum(0)
udS, SS, cS = daysums(S); udR, SR, cR = daysums(Rn); ud = np.array(sorted(set(udS) | set(udR)))
def align(ud_src, Smat, cvec):
    out = np.zeros((C, len(ud))); cnt = np.zeros(len(ud)); pos = {d: i for i, d in enumerate(ud)}
    for j, d in enumerate(ud_src): out[:, pos[d]] = Smat[:, j]; cnt[pos[d]] = cvec[j]
    return out, cnt
SSa, cSa = align(udS, SS, cS); SRa, cRa = align(udR, SR, cR)
pick = rng.integers(0, len(ud), size=(NB, len(ud)))
dS = SSa[:, pick].sum(2) / np.maximum(cSa[pick].sum(1), 1); dR = SRa[:, pick].sum(2) / np.maximum(cRa[pick].sum(1), 1); diff = dS - dR
obs_diff = S['usd_spread'].mean(1) - Rn['usd_spread'].mean(1)
drows = [dict(cfg=cfg[i], strategy_exp=S['usd_spread'][i].mean(), random_exp=Rn['usd_spread'][i].mean(), diff=obs_diff[i], diff_lo=np.percentile(diff[i], 2.5), diff_hi=np.percentile(diff[i], 97.5),
              strategy_mid=S['usd_mid'][i].mean(), random_mid=Rn['usd_mid'][i].mean()) for i in range(C)]
write_csv(OUT + '/q4_strategy_minus_random.csv', drows)
print('strategy-minus-random: n cfg with diff CI above zero', sum(1 for r in drows if r['diff_lo'] > 0), 'below zero', sum(1 for r in drows if r['diff_hi'] < 0), 'of', C)
# breakdowns for the original config and the best spread config on the pooled strategy set, plus random
orig = 'stop-25|be6|guard35@15|partialon|ts30'; io = list(cfg).index(orig)
pooled = [r for r in all_rows if r['group'] == 'strategy_pooled']; ib = int(np.argmax([r['exp_spread'] for r in pooled]))
print('ORIGINAL pooled', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in pooled[io].items()})
print('BEST pooled', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in pooled[ib].items()})
def breakdown(Z, i, label):
    out = []
    for key, vals in (('ticker', Z['ticker']), ('regime', Z['regime']), ('hour', np.array([t[11:13] for t in Z['entry_t']])), ('direction', Z['direction']), ('variant', Z['variant'])):
        for v in sorted(set(vals)):
            m = vals == v; u = Z['usd_spread'][i, m].astype(float)
            if m.sum() < 20: continue
            lo, hi = boot_mean_ci(u, Z['date'][m], 1000)
            out.append(dict(set=label, cfg=cfg[i], by=key, value=v, n=int(m.sum()), exp_spread=u.mean(), lo=lo, hi=hi, exp_mid=Z['usd_mid'][i, m].mean(), wr=100 * (u > 0).mean(), cost_per_trade=(Z['usd_mid'][i, m] - Z['usd_spread'][i, m]).mean()))
    return out
br = breakdown(S, io, 'strategy') + breakdown(S, ib, 'strategy') + breakdown(Rn, io, 'random') + breakdown(Rn, ib, 'random')
write_csv(OUT + '/q4_breakdowns.csv', br)
for r in br: print('BR', {k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
# cost hurdle: mean round-trip cost (mid - spread) per contract by ticker, and in % of premium, for the original config
for Z, lab in ((S, 'strategy'), (Rn, 'random')):
    for tk in TICKERS:
        m = Z['ticker'] == tk; c = (Z['usd_mid'][io, m] - Z['usd_spread'][io, m]); cf = (Z['usd_mid'][io, m] - Z['usd_spread_floor'][io, m])
        print(f'COST {lab} {tk} n={m.sum()} mean entry ${Z["entry_px"][m].mean():.2f} median ${np.median(Z["entry_px"][m]):.2f} | round-trip cost spread model ${c.mean():.2f} ({100*c.mean()/ (100*Z["entry_px"][m].mean()):.1f}% of premium) | with $0.01 floor ${cf.mean():.2f}')
# marginal effects: average spread expectancy by each grid dimension (pooled strategy / random)
import re
for label in ('strategy_pooled', 'random'):
    rows = [r for r in all_rows if r['group'] == label]
    for dim in ('stop', 'be', 'guard', 'partial', 'ts'):
        g = collections.defaultdict(list)
        for r in rows:
            part = [p for p in r['cfg'].split('|') if p.startswith(dim)][0]; g[part].append(r['exp_spread'])
        print('MARGINAL', label, dim, {k: round(float(np.mean(v)), 2) for k, v in sorted(g.items())})
top = sorted(pooled, key=lambda r: -r['exp_spread'])[:12]
for r in top: print('TOP', r['cfg'], 'n', r['n'], 'spread %.2f [%.2f, %.2f] mid %.2f adv %.2f floor %.2f wr %.1f pf %.2f dd %.0f IS %.2f OOS %.2f [%.2f, %.2f] hold %.1f mix STOP %.0f BE %.0f TRAIL %.0f T2 %.0f TS %.0f CLOSE %.0f' % (r['exp_spread'], r['ci_lo_day'], r['ci_hi_day'], r['exp_mid'], r['exp_adverse'], r['exp_spread_floor'], r['wr'], r['pf'], r['maxdd'], r['is_exp'], r['oos_exp'], r['oos_lo'], r['oos_hi'], r['hold_mean'], r['mix_STOP'], r['mix_BREAKEVEN'], r['mix_TRAIL'], r['mix_T2'], r['mix_TIME_STOP'], r['mix_CLOSE']))
rtop = sorted([r for r in all_rows if r['group'] == 'random'], key=lambda r: -r['exp_spread'])[:6]
for r in rtop: print('RTOP', r['cfg'], 'n', r['n'], 'spread %.2f [%.2f, %.2f] mid %.2f adv %.2f wr %.1f pf %.2f IS %.2f OOS %.2f [%.2f, %.2f] hold %.1f mix STOP %.0f BE %.0f TRAIL %.0f T2 %.0f TS %.0f CLOSE %.0f' % (r['exp_spread'], r['ci_lo_day'], r['ci_hi_day'], r['exp_mid'], r['exp_adverse'], r['wr'], r['pf'], r['is_exp'], r['oos_exp'], r['oos_lo'], r['oos_hi'], r['hold_mean'], r['mix_STOP'], r['mix_BREAKEVEN'], r['mix_TRAIL'], r['mix_T2'], r['mix_TIME_STOP'], r['mix_CLOSE']))
for label in ('strategy_sweep', 'strategy_continuation'):
    rows = sorted([r for r in all_rows if r['group'] == label], key=lambda r: -r['exp_spread'])
    print(label, 'ORIG', {k: round(float(v), 2) for k, v in rows[[r['cfg'] for r in rows].index(orig)].items() if isinstance(v, (float, np.floating))})
    for r in rows[:3]: print(label, 'TOP', r['cfg'], 'spread %.2f [%.2f, %.2f] mid %.2f IS %.2f OOS %.2f [%.2f, %.2f]' % (r['exp_spread'], r['ci_lo_day'], r['ci_hi_day'], r['exp_mid'], r['is_exp'], r['oos_exp'], r['oos_lo'], r['oos_hi']))
