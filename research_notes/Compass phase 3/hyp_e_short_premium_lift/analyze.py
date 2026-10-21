"""Compass Phase 3, Hypothesis E: unconditional vs regime-filtered SPY short 0DTE premium held to the close.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I analyze.py fit     # 2022-11-11 -> 2024-12-31 only
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I analyze.py oos     # 2025-01-02 -> 2026-10-09, read once
THE PERIOD IS FILTERED AT LOAD: the fit pass never collects a 2025-2026 trade row.

TRADES are Hypothesis B's scheduled sells, read-only (../../Compass phase 2/hyp_b_boundary_theta/out/trades_SPY.parquet,
engine.py): at each scan minute of every full SPY session a call vertical (short K, long K + width), a put vertical (short K,
long K - width) and the iron condor (both); short strike by rule - d10/d15/d20/d25 (the OTM strike whose BSM |delta| from
its own mid is nearest 0.10/0.15/0.20/0.25) or em1 (the first strike outside spot +/- 1.0 x the ATM straddle mid at the
scan); widths 1 and 2; each leg at its own NBBO (short at the bid, long at the ask); credit >= $0.05 a vertical or no
trade; $0.65 a leg each way, a closing trade fee on every leg closed, a leg expiring worthless pays nothing, an ITM leg
settles at intrinsic on the close of the bar stamped 16:00 (no assignment fee assumed); one lot. Managements: hold to
settlement (primary), buy back at <= 50% of the credit (tp50), stop at >= 2x the credit (stop2x). This test's cells: the
12 scan minutes 10:00, 10:30 .. 15:30 (m = 30 .. 360), the five rules above, both widths, the three structures.
SIGNAL: the t2 volatility model's decile at the scan minute (out/scores_SPY.parquet, fit_model.py): D1-D2 (the bottom
20%: the model says the straddle is least likely to be beaten by the next 30 minutes) and D1 alone, against the rest
(D3-D10) and against all sessions. Trade rows at a minute with no score (no straddle at the minute, or a session the
feature build dropped) stay in "all" and are in neither signal set; counted in the log.
THE LIFT of a cell (structure x rule x width x management x signal) = sum over scan minutes s of N_sig(s) x
[mean(net | signal at s) - mean(net | all sessions at s)] / sum N_sig(s): the signal's mean against the TIME-OF-DAY-
MATCHED unconditional mean, weighted by the signal's own mix of scan minutes. Its 95% CI is a PAIRED SESSION BOOTSTRAP:
2,000 draws of the period's sessions with replacement (seed 20261016; one draw matrix for every cell), both means
recomputed from the same drawn sessions. Also in $ per $100 of max risk (the cross-structure yardstick, the ranking's),
vs the rest, by year, by scan minute, and without the best 5 sessions (by their contribution to the lift).
THE UNCONDITIONAL BENCHMARK: the same structure at every full session's scan minute, per scan minute and pooled, with
the same session bootstrap; "significant" = the 95% CI of the mean $ lies above zero.
Per cell: N, sessions, mean $ a structure, % of max risk, median credit, win rate, average win / loss, full-loss share
(net <= -95% of max risk), p5 / p1 / worst, worst session, total, profit factor, max drawdown and longest losing streak
(the 1-lot sequence in session, entry order), CI, mean without the best 5 sessions, by year, friction (hold: the legs'
bid-ask crossed at entry plus fees as a share of the gross at the mids with no fees; a condor's mid credit is its two
verticals' at the same minute).
Outputs: out/<mode>_uncond_byscan.csv, out/<mode>_uncond_pooled.csv, out/<mode>_lift_cells.csv, out/<mode>_lift_byscan.csv,
out/<mode>_sig_byyear.csv, out/<mode>_summary.txt.
"""
import os, sys, time
import numpy as np, polars as pl

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
TRADES = '/home/user/georgeredo/research_notes/Compass phase 2/hyp_b_boundary_theta/out/trades_SPY.parquet'
SCANS = [30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330, 360]
RULES = ['d10', 'd15', 'd20', 'd25', 'em1']
WIDTHS = [1.0, 2.0]; STRUCTS = ['call', 'put', 'condor']
MGMT = {'hold': 'pnl_hold', 'tp50': 'pnl_tp', 'stop2x': 'pnl_stop'}
SIGNALS = {'D1-2': (1, 2), 'D1': (1, 1)}
NBOOT = 2000; SEED = 20261016
FEE = 0.65
FIT_LAST = '2024-12-31'

def hhmm(m): return f'{(570 + m) // 60:02d}:{(570 + m) % 60:02d}'

def load(mode):
    X = pl.scan_parquet(TRADES).filter((pl.col('test') == 'sched') & pl.col('m_scan').is_in(SCANS) & pl.col('rule').is_in(RULES) & pl.col('width').is_in(WIDTHS) & pl.col('structure').is_in(STRUCTS))
    X = X.filter(pl.col('session') <= FIT_LAST) if mode == 'fit' else X.filter(pl.col('session') > FIT_LAST)   # THE PERIOD, AT LOAD
    X = X.select('session', 'structure', 'rule', 'width', 'm_scan', 'e', 'credit', 'max_risk', 'settle_val', 'short_bid', 'long_ask', 'short_ask', 'long_bid', *MGMT.values()).collect()
    # the mid credit: a vertical's own legs; a condor's the sum of its two verticals at the same minute
    V = X.filter(pl.col('structure') != 'condor').with_columns(((pl.col('short_bid') + pl.col('short_ask')) / 2 - (pl.col('long_ask') + pl.col('long_bid')) / 2).alias('credit_mid'))
    C = X.filter(pl.col('structure') == 'condor').join(V.group_by('session', 'rule', 'width', 'm_scan').agg(pl.col('credit_mid').sum(), pl.len().alias('nv')).filter(pl.col('nv') == 2).drop('nv'),
                                                       on=['session', 'rule', 'width', 'm_scan'], how='left')
    X = pl.concat([V, C], how='diagonal_relaxed')
    X = X.with_columns(pl.when(pl.col('structure') == 'condor').then(4).otherwise(2).alias('legs'), pl.col('session').str.slice(0, 4).cast(pl.Int32).alias('year'))
    S = pl.read_parquet(os.path.join(OUT, 'scores_SPY.parquet')).select(pl.col('session').cast(pl.Utf8), pl.col('m').alias('m_scan'), pl.col('full_gbm_dec').alias('dec'), pl.col('full_lr_dec').alias('dec_lr'), 'dec_kind')
    X = X.join(S, on=['session', 'm_scan'], how='left')
    return X.sort('session', 'e', 'structure', 'rule', 'width')

# ------------------------------------------------------------------------------------------------ the bootstrap
class Boot:
    """one draw matrix for the period: W[b, j] = how many times session j is drawn in draw b"""
    def __init__(self, sessions):
        self.sessions = np.array(sorted(sessions)); self.D = len(self.sessions); self.idx = {s: i for i, s in enumerate(self.sessions)}
        rng = np.random.default_rng(SEED); draws = rng.integers(0, self.D, (NBOOT, self.D))
        self.W = np.zeros((NBOOT, self.D));
        for b in range(NBOOT): self.W[b] = np.bincount(draws[b], minlength=self.D)
    def mat(self, df, col):
        """(sum, count) matrices [session, scan] of `col` over df's rows"""
        g = df.group_by('session', 'm_scan').agg(pl.col(col).sum().alias('s'), pl.len().alias('n'))
        Sm = np.zeros((self.D, len(SCANS))); Nm = np.zeros((self.D, len(SCANS)))
        ji = np.array([self.idx[s] for s in g['session'].to_list()]); si = np.array([SCANS.index(m) for m in g['m_scan'].to_list()])
        Sm[ji, si] = g['s'].to_numpy(); Nm[ji, si] = g['n'].to_numpy()
        return Sm, Nm
    def ci_mean(self, Sm, Nm):
        s = self.W @ Sm.sum(1); n = self.W @ Nm.sum(1); m = np.where(n > 0, s / np.where(n > 0, n, 1), np.nan)
        return float(np.nanpercentile(m, 2.5)), float(np.nanpercentile(m, 97.5))
    def ci_lift(self, Ss, Ns, Sa, Na, per_scan=False):
        """paired: sum_s Ns(s) [Ss/Ns - Sa/Na](s) / sum_s Ns(s), per draw"""
        SS = self.W @ Ss; NS = self.W @ Ns; SA = self.W @ Sa; NA = self.W @ Na
        ma = np.where(NA > 0, SA / np.where(NA > 0, NA, 1), np.nan)
        d = SS - NS * ma                                   # sum over the signal's rows of (net - tod mean), per scan
        if per_scan:
            l = np.where(NS > 0, d / np.where(NS > 0, NS, 1), np.nan)
            return np.nanpercentile(l, 2.5, axis=0), np.nanpercentile(l, 97.5, axis=0)
        ok = NS > 0; num = np.where(ok, d, 0).sum(1); den = NS.sum(1)
        l = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
        return float(np.nanpercentile(l, 2.5)), float(np.nanpercentile(l, 97.5))

# ------------------------------------------------------------------------------------------------ cell statistics
def seq_stats(net):
    cum = np.cumsum(net); peak = np.maximum.accumulate(np.maximum(cum, 0)); dd = float((peak - cum).max()) if len(cum) else np.nan
    streak = best = 0
    for x in net:
        streak = streak + 1 if x < 0 else 0; best = max(best, streak)
    return dd, best

def stats(df, col, boot, years):
    """the per-cell report on df (already the cell's rows, sorted by session and entry)"""
    net = df[col].to_numpy(); mr = df['max_risk'].to_numpy(); ses = df['session'].to_numpy()
    n = len(net)
    if n == 0: return dict(N=0)
    g = df.group_by('session').agg(pl.col(col).sum().alias('s'), pl.len().alias('k')).sort('s', descending=True)
    sums = g['s'].to_numpy(); ks = g['k'].to_numpy(); tot = float(net.sum())
    wins = net[net > 0]; losses = net[net < 0]
    Sm, Nm = boot.mat(df, col); lo, hi = boot.ci_mean(Sm, Nm)
    pr = pl.DataFrame({'session': df['session'], 'm_scan': df['m_scan'], 'pr': net / mr * 100}); Sp, Np = boot.mat(pr, 'pr'); plo, phi = boot.ci_mean(Sp, Np)
    dd, streak = seq_stats(net)
    o = dict(N=n, sessions=int(g.height), mean_usd=float(net.mean()), mean_pct_risk=float((net / mr).mean() * 100), ci_lo=lo, ci_hi=hi, ci_lo_pct_risk=plo, ci_hi_pct_risk=phi,
             median_credit=float(df['credit'].median()), mean_max_risk=float(mr.mean()), win_rate=float((net > 0).mean()),
             avg_win=float(wins.mean()) if len(wins) else np.nan, avg_loss=float(losses.mean()) if len(losses) else np.nan,
             full_loss_share=float((net <= -0.95 * mr).mean()), p5=float(np.percentile(net, 5)), p1=float(np.percentile(net, 1)), worst=float(net.min()),
             worst_session=str(g['session'][-1]), worst_session_usd=float(sums[-1]), total_usd=tot,
             profit_factor=float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() < 0 else np.nan,
             max_drawdown=dd, longest_losing_streak=int(streak),
             wo_best5=float(sums[5:].sum() / max(ks[5:].sum(), 1)) if g.height > 5 else np.nan, best5_share_of_total=float(sums[:5].sum() / tot) if tot > 0 else np.nan)
    for yr in years:
        s = df.filter(pl.col('year') == yr); o[f'mean_{yr}'] = float(s[col].mean()) if s.height else np.nan; o[f'n_{yr}'] = s.height
    if col == 'pnl_hold':
        f = df.filter(pl.col('credit_mid').is_not_null())
        if f.height:
            gross = ((f['credit_mid'] - f['settle_val']) * 100).to_numpy(); spread_cost = ((f['credit_mid'] - f['credit']) * 100).to_numpy(); fees = f['legs'].to_numpy() * FEE
            o.update(credit_mid=float(f['credit_mid'].mean()), credit_fill=float(f['credit'].mean()), spread_cost_usd=float(spread_cost.mean()), fees_usd=float(fees.mean()), gross_mid_nofee_usd=float(gross.mean()),
                     friction_share_of_gross=float((spread_cost.mean() + fees.mean()) / gross.mean()) if gross.mean() > 0 else np.nan, n_friction=f.height)
    return o

# ------------------------------------------------------------------------------------------------ main
if __name__ == '__main__':
    mode = sys.argv[1]; assert mode in ('fit', 'oos')
    t0 = time.time(); X = load(mode)
    sessions = sorted(X['session'].unique().to_list()); years = sorted(X['year'].unique().to_list())
    boot = Boot(sessions)
    log = [f'{mode}: rows {X.height} sessions {len(sessions)} {sessions[0]} -> {sessions[-1]}; scored rows {X.filter(pl.col("dec").is_not_null()).height} ({X.filter(pl.col("dec").is_null())["session"].n_unique()} sessions with an unscored row); '
           f'decile kinds {X.group_by("dec_kind").len().sort("dec_kind").to_dicts()}; D1-2 rows {X.filter(pl.col("dec") <= 2).height} D1 {X.filter(pl.col("dec") == 1).height}; '
           f'fees {FEE}/leg/way, hold: no closing fee, ITM at intrinsic on the 16:00 bar; bootstrap {NBOOT} draws seed {SEED}']
    print(log[0], flush=True)
    # ---- 1. the unconditional benchmark, per scan minute and pooled
    unc = []; pooled = []
    for (st, ru, w), g in X.group_by('structure', 'rule', 'width'):
        for mg, col in MGMT.items():
            for s in SCANS:
                c = g.filter(pl.col('m_scan') == s)
                if c.height: unc.append(dict(period=mode, scan=hhmm(s), m_scan=s, structure=st, rule=ru, width=w, management=mg, **stats(c, col, boot, years)))
            pooled.append(dict(period=mode, structure=st, rule=ru, width=w, management=mg, **stats(g, col, boot, years)))
    U = pl.DataFrame(unc, infer_schema_length=None).with_columns((pl.col('ci_lo') > 0).alias('significant')).sort('management', 'structure', 'rule', 'width', 'm_scan')
    P = pl.DataFrame(pooled, infer_schema_length=None).with_columns((pl.col('ci_lo') > 0).alias('significant')).sort('management', 'structure', 'rule', 'width')
    U.write_csv(os.path.join(OUT, f'{mode}_uncond_byscan.csv')); P.write_csv(os.path.join(OUT, f'{mode}_uncond_pooled.csv'))
    print('unconditional done', f'{time.time() - t0:.0f}s', flush=True)
    # ---- 2. the lift cells
    cells = []; byscan = []; byyear = []
    for (st, ru, w), g in X.group_by('structure', 'rule', 'width'):
        scored = g.filter(pl.col('dec').is_not_null())
        for mg, col in MGMT.items():
            Sa, Na = boot.mat(g, col)                                         # all sessions at each scan (the benchmark)
            pr_all = g.with_columns((pl.col(col) / pl.col('max_risk') * 100).alias('pr')); Pa, _ = boot.mat(pr_all, 'pr')
            tod = np.where(Na.sum(0) > 0, Sa.sum(0) / np.maximum(Na.sum(0), 1), np.nan)        # tod mean $ per scan
            tod_pr = np.where(Na.sum(0) > 0, Pa.sum(0) / np.maximum(Na.sum(0), 1), np.nan)
            for sig, (dlo, dhi) in SIGNALS.items():
                sg = scored.filter((pl.col('dec') >= dlo) & (pl.col('dec') <= dhi)); rest = scored.filter(pl.col('dec') > dhi)
                if sg.height == 0: continue
                Ss, Ns = boot.mat(sg, col); Sr, Nr = boot.mat(rest, col)
                sgp = sg.with_columns((pl.col(col) / pl.col('max_risk') * 100).alias('pr')); Ps, _ = boot.mat(sgp, 'pr')
                ns = Ns.sum(0); w_ = ns / ns.sum()
                mean_sig_s = np.where(ns > 0, Ss.sum(0) / np.maximum(ns, 1), np.nan)
                lift = float(np.nansum(w_ * (mean_sig_s - tod)))
                lo, hi = boot.ci_lift(Ss, Ns, Sa, Na); plo, phi = boot.ci_lift(Ps, Ns, Pa, Na)
                lift_pr = float(np.nansum(w_ * (np.where(ns > 0, Ps.sum(0) / np.maximum(ns, 1), np.nan) - tod_pr)))
                nr = Nr.sum(0); mean_rest_s = np.where(nr > 0, Sr.sum(0) / np.maximum(nr, 1), np.nan)
                lift_rest = float(np.nansum(w_ * (mean_sig_s - np.where(np.isnan(mean_rest_s), mean_sig_s, mean_rest_s)))); rlo, rhi = boot.ci_lift(Ss, Ns, Sr, Nr)
                # without the best 5 sessions by their contribution to the lift
                contrib = (Ss - Ns * tod[None, :]).sum(1); order = np.argsort(-contrib); keep = np.ones(boot.D, bool); keep[order[:5]] = False
                lift_wo5 = float(contrib[keep].sum() / max(Ns[keep].sum(), 1))
                st_ = stats(sg, col, boot, years)
                row = dict(period=mode, structure=st, rule=ru, width=w, management=mg, signal=sig, **st_,
                           tod_mean_usd=float(np.nansum(w_ * tod)), tod_mean_pct_risk=float(np.nansum(w_ * tod_pr)), rest_mean_usd=float(np.nansum(w_ * np.where(np.isnan(mean_rest_s), 0, mean_rest_s))), rest_N=int(nr.sum()),
                           lift_usd=lift, lift_ci_lo=lo, lift_ci_hi=hi, lift_pct_risk=lift_pr, lift_ci_lo_pct_risk=plo, lift_ci_hi_pct_risk=phi, lift_wo_best5=lift_wo5,
                           lift_vs_rest_usd=lift_rest, lift_vs_rest_ci_lo=rlo, lift_vs_rest_ci_hi=rhi)
                for yr in years:
                    gy = g.filter(pl.col('year') == yr); sy = sg.filter(pl.col('year') == yr)
                    if sy.height:
                        ty = gy.group_by('m_scan').agg(pl.col(col).mean().alias('mu')); mp = dict(zip(ty['m_scan'].to_list(), ty['mu'].to_list()))
                        row[f'lift_{yr}'] = float((sy[col].to_numpy() - np.array([mp[m] for m in sy['m_scan'].to_list()])).mean()); row[f'lift_n_{yr}'] = sy.height
                    else: row[f'lift_{yr}'] = np.nan; row[f'lift_n_{yr}'] = 0
                cells.append(row)
                slo, shi = boot.ci_lift(Ss, Ns, Sa, Na, per_scan=True)
                for i, s in enumerate(SCANS):
                    if ns[i] > 0:
                        c = sg.filter(pl.col('m_scan') == s)
                        byscan.append(dict(period=mode, structure=st, rule=ru, width=w, management=mg, signal=sig, scan=hhmm(s), N=int(ns[i]), sessions=c['session'].n_unique(), mean_usd=float(mean_sig_s[i]), mean_pct_risk=float((c[col] / c['max_risk']).mean() * 100),
                                           win_rate=float((c[col] > 0).mean()), tod_N=int(Na.sum(0)[i]), tod_mean_usd=float(tod[i]), tod_mean_pct_risk=float(tod_pr[i]), lift_usd=float(mean_sig_s[i] - tod[i]), lift_ci_lo=float(slo[i]), lift_ci_hi=float(shi[i])))
    Cdf = pl.DataFrame(cells, infer_schema_length=None).sort('management', 'signal', 'structure', 'rule', 'width')
    Cdf.write_csv(os.path.join(OUT, f'{mode}_lift_cells.csv'))
    pl.DataFrame(byscan, infer_schema_length=None).sort('management', 'signal', 'structure', 'rule', 'width', 'scan').write_csv(os.path.join(OUT, f'{mode}_lift_byscan.csv'))
    print('lift done', f'{time.time() - t0:.0f}s', flush=True)
    # ---- 3. the summary
    pl.Config.set_tbl_rows(500); pl.Config.set_tbl_width_chars(300); pl.Config.set_float_precision(2); pl.Config.set_tbl_cols(40)
    lines = list(log)
    H = Cdf.filter(pl.col('management') == 'hold')
    lines.append('\n== LIFT CELLS, hold, ranked by the lower 95% bound of the lift in % of max risk (paired session bootstrap) ==')
    lines.append(str(H.select('signal', 'structure', 'rule', 'width', 'N', 'sessions', 'mean_usd', 'mean_pct_risk', 'tod_mean_usd', 'tod_mean_pct_risk', 'lift_usd', 'lift_ci_lo', 'lift_ci_hi', 'lift_pct_risk', 'lift_ci_lo_pct_risk', 'lift_ci_hi_pct_risk', 'lift_wo_best5', 'lift_vs_rest_usd', 'lift_vs_rest_ci_lo', 'wo_best5', 'win_rate', 'full_loss_share').sort('lift_ci_lo_pct_risk', descending=True)))
    for mg in ('tp50', 'stop2x'):
        M = Cdf.filter(pl.col('management') == mg)
        lines.append(f'\n== LIFT CELLS, {mg}, the ten best lower bounds ==')
        lines.append(str(M.select('signal', 'structure', 'rule', 'width', 'N', 'mean_usd', 'mean_pct_risk', 'tod_mean_pct_risk', 'lift_usd', 'lift_ci_lo', 'lift_ci_hi', 'lift_pct_risk', 'lift_ci_lo_pct_risk', 'lift_wo_best5').sort('lift_ci_lo_pct_risk', descending=True).head(10)))
    lines.append('\n== UNCONDITIONAL, pooled over the 12 scans, hold, ranked by the lower bound in % of max risk ==')
    lines.append(str(P.filter(pl.col('management') == 'hold').select('structure', 'rule', 'width', 'N', 'sessions', 'mean_usd', 'mean_pct_risk', 'ci_lo', 'ci_hi', 'ci_lo_pct_risk', 'win_rate', 'full_loss_share', 'wo_best5', 'profit_factor', 'max_drawdown', 'longest_losing_streak', 'friction_share_of_gross', 'significant').sort('ci_lo_pct_risk', descending=True)))
    lines.append('\n== UNCONDITIONAL by scan, hold: significant cells (CI of the mean $ above zero) per scan, and the strongest cell a scan ==')
    Uh = U.filter(pl.col('management') == 'hold')
    for s in SCANS:
        us = Uh.filter(pl.col('m_scan') == s).sort('ci_lo_pct_risk', descending=True); top = us.row(0, named=True)
        lines.append(f"{hhmm(s)}: {int(us['significant'].sum())} of {us.height} cells significant; strongest {top['structure']} {top['rule']} w{top['width']:.0f}: N {top['N']} mean ${top['mean_usd']:.2f} = {top['mean_pct_risk']:.2f}% of risk, CI $[{top['ci_lo']:.2f}, {top['ci_hi']:.2f}], win {top['win_rate']:.2f}, wo5 ${top['wo_best5']:.2f}")
    lines.append('\n== UNCONDITIONAL by scan, hold, every cell (mean % of max risk | CI lo $ ; * = significant) ==')
    for (st, ru, w), g in Uh.group_by('structure', 'rule', 'width', maintain_order=True):
        g = g.sort('m_scan'); lines.append(f'{st:6s} {ru:4s} w{w:.0f}: ' + '  '.join(f"{hhmm(r['m_scan'])} {r['mean_pct_risk']:+.2f}%{'*' if r['significant'] else ' '}" for r in g.iter_rows(named=True)))
    lines.append('\n== MANAGEMENT, pooled unconditional (mean % of max risk) ==')
    lines.append(str(P.pivot(on='management', index=['structure', 'rule', 'width'], values='mean_pct_risk').sort('structure', 'rule', 'width')))
    txt = '\n'.join(lines)
    with open(os.path.join(OUT, f'{mode}_summary.txt'), 'w') as fh: fh.write(txt + '\n')
    print(txt[:20000]); print(f'done {time.time() - t0:.0f}s')
