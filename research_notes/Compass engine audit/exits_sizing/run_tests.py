"""Compass Modules 3/4 audit: the computed tests 1-7 on both entry universes. Pick on 2022-2024 ('disc'), read on
2025-2026 ('check'). Writes out/t*.csv and prints the tables.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I run_tests.py
"""
import os, sys, json, itertools
import numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E

OUT = E.OUT
pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_rows(80); pl.Config.set_fmt_str_lengths(60)
def write(rows, name):
    df = pl.DataFrame(rows, infer_schema_length=None)
    df = df.with_columns([pl.col(c).round(5) for c, t in df.schema.items() if t == pl.Float64])
    df.write_csv(os.path.join(OUT, name)); return df

SPEC_T1 = ((1, 1.25),)                 # 1 contract: all out at T1
SPEC_2C = ((1, 1.25), (1, 1.50))       # 2 contracts: one at T1, one at T2
SPEC_3C = ((1, 1.25), (1, 1.50), (1, None))

def spec_kwargs(uni):
    return dict(prem_stop=0.68, struct_buffer=2.0 if uni == 'A' else 0.0, b_bps=None if uni == 'A' else 15.0, be_lock=0.06, trail='vix', trail_act=0.06,
                time_stop=5, time_prog=0.06, targets=SPEC_T1, hard_flat=True)

def by_reason(P, res, mask):
    r = res['legs'][0]['reason'][mask]; pct = res['pct'][mask]
    out = {}
    for k in np.unique(r):
        mk = r == k; out[k] = dict(share=float(mk.mean()), avg_pct=float(pct[mk].mean()), n=int(mk.sum()))
    return out

def main():
    summary = {}
    for uni in ('A', 'B'):
        P = E.load(universe=uni)
        print(f'\n==== Universe {uni}: {P.n} trades, {np.sum(~P.is_check)} disc / {np.sum(P.is_check)} check; '
              f'products {dict(zip(*np.unique(P.product, return_counts=True)))}; median entry ask {np.median(P.ask0):.2f}')
        summary[uni] = dict(n=int(P.n), n_disc=int(np.sum(~P.is_check)), n_check=int(np.sum(P.is_check)), median_ask=float(np.median(P.ask0)),
                            sessions=int(len(np.unique(P.session))))
        # ---------- descriptive: entry price, spread, the exact-top ceiling, hold to flat
        hold = E.simulate(P, prem_stop=None, targets=((1, None),))
        spread = (P.ask0 - P.df['entry_bid'].to_numpy()) / P.ask0
        print('entry spread/ask median', np.median(spread).round(3), 'mean', spread.mean().round(3))
        maxb = np.nanmax(P.Bw, axis=1); print('peak bid / ask: share >=1.06', np.mean(maxb >= 1.06 * P.ask0).round(3), '>=1.25', np.mean(maxb >= 1.25 * P.ask0).round(3),
              '>=1.5', np.mean(maxb >= 1.5 * P.ask0).round(3))
        summary[uni].update(spread_med=float(np.median(spread)), p_peak106=float(np.mean(maxb >= 1.06 * P.ask0)), p_peak125=float(np.mean(maxb >= 1.25 * P.ask0)),
                            p_peak150=float(np.mean(maxb >= 1.5 * P.ask0)))
        # ---------- the spec stack as written, 1/2/3 contracts, and the loss mix (task a)
        rows = []
        for name, tg in (('spec 1c (T1 all-out)', SPEC_T1), ('spec 2c (1@T1,1@T2)', SPEC_2C), ('spec 3c (1@T1,1@T2,1 trailed)', SPEC_3C)):
            kw = spec_kwargs(uni); kw['targets'] = tg
            res = E.simulate(P, **kw); r = E.row(name, P, res); r.update({f's_{k}': v for k, v in E.stress(P, res, P.is_check).items()})
            loss = res['pnl'] < 0
            r['avg_loss_all_pct'] = float(res['pct'][loss].mean()); r['loss_mix'] = json.dumps({k: (round(v['share'], 3), round(v['avg_pct'], 3)) for k, v in by_reason(P, res, loss).items()})
            r['exit_mix'] = json.dumps({k: (round(v['share'], 3), round(v['avg_pct'], 3)) for k, v in by_reason(P, res, np.ones(P.n, bool)).items()})
            rows.append(r)
        rows.append(E.row('hold to 15:58, no stops', P, hold))
        df = write(rows, f't0_spec_stack_{uni}.csv'); print(df.select('rule', 'n_disc', 'ev_pct_disc', 'win_rate_disc', 'n_check', 'ev_pct_check', 'win_rate_check', 'avg_loss_pct_check', 's_boot_lo', 's_boot_hi', 's_without_best5', 'exit_mix'))
        # ---------- Test 1: stops
        rows = []
        prem_levels = [None, 0.85, 0.80, 0.75, 0.68, 0.50]
        struct_levels = [None, 0.0, 2.0, 5.0] if uni == 'A' else [None, 10.0, 15.0, 20.0]
        for ps, st in itertools.product(prem_levels, struct_levels):
            kw = dict(prem_stop=ps, hard_flat=True)
            if st is not None: kw.update(struct_buffer=st if uni == 'A' else 0.0, b_bps=None if uni == 'A' else st)
            res = E.simulate(P, **kw)
            name = f"prem {'none' if ps is None else f'-{round((1-ps)*100)}%'} · struct {'none' if st is None else f'{st:g} bps'}"
            r = E.row(name, P, res, dict(prem=ps, struct=st))
            # realized loss on premium-stop exits (gaps through the stop)
            rs = res['legs'][0]['reason'] == 'prem_stop'; px = res['legs'][0]['price']
            if rs.any():
                real = px[rs] / P.ask0[rs] - 1
                mins = res['legs'][0]['exit_m'][rs] - P.e[rs]
                r.update(prem_stop_exits=int(rs.sum()), prem_stop_share=float(rs.mean()), realized_stop_mean=float(real.mean()), realized_stop_median=float(np.median(real)),
                         gap_beyond_5pts=float(np.mean(real < (ps - 1) - 0.05)), realized_stop_p10=float(np.percentile(real, 10)),
                         stop_within_3min_share=float(np.mean(mins <= 3)), stop_within_1min_share=float(np.mean(mins <= 1)), stop_median_minutes=float(np.median(mins)))
            rst = res['legs'][0]['reason'] == 'struct'
            if rst.any():
                real = px[rst] / P.ask0[rst] - 1
                r.update(struct_exits=int(rst.sum()), struct_share=float(rst.mean()), struct_realized_mean=float(real.mean()), struct_realized_p10=float(np.percentile(real, 10)))
            rows.append(r)
        df = write(rows, f't1_stops_{uni}.csv')
        print(df.select('rule', 'ev_pct_disc', 'win_rate_disc', 'avg_loss_pct_disc', 'ev_pct_check', 'win_rate_check', 'avg_loss_pct_check', 'prem_stop_share', 'realized_stop_mean', 'realized_stop_p10', 'gap_beyond_5pts', 'struct_share', 'struct_realized_mean'))
        # inside the full spec stack, swap the premium stop
        rows = []
        for ps in [None, 0.85, 0.80, 0.75, 0.68, 0.50]:
            kw = spec_kwargs(uni); kw['prem_stop'] = ps
            res = E.simulate(P, **kw); rows.append(E.row(f"spec stack, prem {'none' if ps is None else f'-{round((1-ps)*100)}%'}", P, res))
        for st in [None] + ([0.0, 2.0, 5.0] if uni == 'A' else [10.0, 15.0, 20.0]):
            kw = spec_kwargs(uni)
            if st is None: kw.update(struct_buffer=None, b_bps=None)
            else: kw.update(struct_buffer=st if uni == 'A' else 0.0, b_bps=None if uni == 'A' else st)
            res = E.simulate(P, **kw); rows.append(E.row(f"spec stack, struct {'none' if st is None else f'{st:g} bps'}", P, res))
        df = write(rows, f't1_stops_in_stack_{uni}.csv'); print(df.select('rule', 'ev_pct_disc', 'win_rate_disc', 'avg_loss_pct_disc', 'ev_pct_check', 'win_rate_check', 'avg_loss_pct_check'))
        # ---------- Test 2: breakeven lock
        rows = []
        for base_name, base in (('prem -32% + flat', dict(prem_stop=0.68)), ('prem -32% + T1 all-out', dict(prem_stop=0.68, targets=SPEC_T1)),
                                ('prem -32% + 2c T1/T2', dict(prem_stop=0.68, targets=SPEC_2C))):
            res0 = E.simulate(P, **base)
            for bl in [None, 0.0, 0.03, 0.06, 0.09, 0.12, 0.15, 0.20]:
                kw = dict(base); kw['be_lock'] = bl
                res = E.simulate(P, **kw)
                r = E.row(f"{base_name} · BE lock {'none' if bl is None else f'+{round(bl*100)}%'}", P, res, dict(base=base_name, be_lock=bl))
                if bl is not None:
                    lock_set = np.nanmax(P.Bw, axis=1) >= (1 + bl) * P.ask0 - 1e-9
                    rz = res['legs'][0]['reason'] == 'be_lock'; m = res['legs'][0]['exit_m']
                    # after a lock exit, did the bid go on to +25% / +45% before the hard flat?
                    later = np.where((P.M > m[:, None]) & (P.M <= P.hf[:, None]), P.Bw, np.nan); lmax = np.nanmax(np.where(np.isnan(later), -np.inf, later), axis=1)
                    go25 = rz & (lmax >= 1.25 * P.ask0); go45 = rz & (lmax >= 1.45 * P.ask0)
                    # the choke rate: of the trades that would have reached +25% after the lock exit, the share the lock sold first
                    r.update(lock_set_share=float(lock_set.mean()), lock_hit_share=float(rz.mean()), lock_hit_of_set=float(rz.sum() / max(lock_set.sum(), 1)),
                             choke25_share_of_all=float(go25.mean()), choke45_share_of_all=float(go45.mean()), choke25_of_lock_hits=float(go25.sum() / max(rz.sum(), 1)),
                             choke45_of_lock_hits=float(go45.sum() / max(rz.sum(), 1)), lock_exit_avg_pct=float(res['pct'][rz].mean()) if rz.any() else np.nan,
                             lock_hits_if_no_lock_pct=float(res0['pct'][rz].mean()) if rz.any() else np.nan,
                             lock_hits_if_no_lock_win_rate=float((res0['pnl'][rz] > 0).mean()) if rz.any() else np.nan,
                             lock_hits_check_pct=float(res['pct'][rz & P.is_check].mean()) if (rz & P.is_check).any() else np.nan,
                             lock_hits_check_if_no_lock_pct=float(res0['pct'][rz & P.is_check].mean()) if (rz & P.is_check).any() else np.nan)
                rows.append(r)
        df = write(rows, f't2_belock_{uni}.csv'); print(df.select('rule', 'ev_pct_disc', 'win_rate_disc', 'ev_pct_check', 'win_rate_check', 'lock_set_share', 'lock_hit_of_set', 'choke25_of_lock_hits', 'choke45_of_lock_hits', 'lock_exit_avg_pct'))
        # ---------- Test 3: trails
        rows = []
        for act in (0.06, None):
            for tr in [None, 'vix', 0.06, 0.10, 0.20, 0.30, 0.50]:
                res = E.simulate(P, prem_stop=0.68, trail=tr, trail_act=act)
                rz = res['legs'][0]['reason'] == 'trail'
                r = E.row(f"prem -32% · trail {tr if tr else 'none'} · active {'from +6%' if act else 'from entry'}", P, res, dict(trail=str(tr), act=act))
                r.update(trail_exit_share=float(rz.mean()), trail_exit_avg_pct=float(res['pct'][rz].mean()) if rz.any() else np.nan)
                rows.append(r)
        # the VIX tiers one by one (check period, from +6%)
        for lo, hi in ((0, 15), (15, 20), (20, 30), (30, 200)):
            mk = (P.vix >= lo) & (P.vix < hi)
            for tr in ['vix', 0.06, 0.10, 0.20, 0.30]:
                res = E.simulate(P, prem_stop=0.68, trail=tr, trail_act=0.06)
                r = dict(rule=f'VIX {lo}-{hi} · trail {tr}', trail=str(tr), act=0.06)
                for lab, m2 in (('disc', ~P.is_check), ('check', P.is_check)):
                    s = E.stats(P, res, mk & m2); r.update({f'{k}_{lab}': v for k, v in s.items()})
                rows.append(r)
        df = write(rows, f't3_trail_{uni}.csv'); print(df.select('rule', 'n_disc', 'ev_pct_disc', 'win_rate_disc', 'n_check', 'ev_pct_check', 'win_rate_check', 'trail_exit_share', 'trail_exit_avg_pct'))
        # ---------- Test 4: time stop
        rows = []
        for ts in [None, 5, 10, 15, 30, 60]:
            for prog, spot in (('premium +6%', None), ('premium +6% or spot 5 bps', 5.0)):
                if ts is None and spot is not None: continue
                res = E.simulate(P, prem_stop=0.68, time_stop=ts, time_prog=0.06, time_prog_spot_bps=spot)
                rz = res['legs'][0]['reason'] == 'time'
                r = E.row(f"prem -32% · time stop {ts or 'none'} min · progress: {prog}", P, res, dict(ts=ts, prog=prog))
                r.update(time_exit_share=float(rz.mean()), time_exit_avg_pct=float(res['pct'][rz].mean()) if rz.any() else np.nan)
                if rz.any():   # what the time-stopped trades would have done held to the flat with the same stop
                    alt = E.simulate(P, prem_stop=0.68); r['time_stopped_if_held_pct'] = float(alt['pct'][rz].mean())
                rows.append(r)
        df = write(rows, f't4_timestop_{uni}.csv'); print(df.select('rule', 'ev_pct_disc', 'win_rate_disc', 'ev_pct_check', 'win_rate_check', 'time_exit_share', 'time_exit_avg_pct', 'time_stopped_if_held_pct'))
        # ---------- Test 5: targets and scale-outs
        rows = []
        base = dict(prem_stop=0.68)
        maxb = np.nanmax(np.where(np.isnan(P.Bw) | (P.M > P.hf[:, None]), -np.inf, P.Bw), axis=1)
        stop_m = E.first_true(P.Bw <= 0.68 * P.ask0[:, None] + 1e-9)
        for tg in (1.25, 1.45, 1.50, 2.0):
            ti = E.first_true(P.Bw >= tg * P.ask0[:, None] - 1e-9)
            hit_any = (ti >= 0) & (ti <= P.hf); hit_before_stop = hit_any & ((stop_m < 0) | (ti < stop_m))
            for lab, mk in (('disc', ~P.is_check), ('check', P.is_check)):
                rows.append(dict(rule=f'target +{round((tg-1)*100)}% reached before 15:58', period=lab, n=int(mk.sum()), hit_rate=float(hit_any[mk].mean()), hit_before_32_stop=float(hit_before_stop[mk].mean())))
        write(rows, f't5_target_hits_{uni}.csv'); print(pl.DataFrame(rows))
        rows = []
        configs = [('all-out +25%', ((1, 1.25),)), ('all-out +45%', ((1, 1.45),)), ('all-out +50%', ((1, 1.50),)), ('all-out +100%', ((1, 2.0),)), ('no target (flat)', ((1, None),)),
                   ('2c: 1@+25, 1 trailed(vix,+6%)', ((1, 1.25), (1, None))), ('2c: 1@+25, 1@+50', SPEC_2C),
                   ('3c: 1@+25, 1@+50, 1 trailed', SPEC_3C), ('4c: 1@+25, 2@+50, 1 trailed', ((1, 1.25), (2, 1.50), (1, None)))]
        for name, tg in configs:
            trail = 'vix' if 'trailed' in name else None
            res = E.simulate(P, prem_stop=0.68, targets=tg, trail=trail, trail_act=0.06)
            r = E.row(f'prem -32% · {name}', P, res, dict(contracts=sum(c for c, _ in tg)))
            # the stop/avg-loss the targets need: break-even win rate = |avg loss| / (avg win + |avg loss|)
            for lab in ('disc', 'check'):
                aw, al = r.get(f'avg_win_pct_{lab}'), r.get(f'avg_loss_pct_{lab}')
                r[f'breakeven_win_rate_{lab}'] = float(-al / (aw - al)) if aw is not None and al is not None and not np.isnan(aw) and not np.isnan(al) else np.nan
            # fill realism: bid_size at each target leg's exit minute >= that leg's contracts
            fills = []
            for leg in res['legs']:
                tgt = leg['reason'] == 'target'
                if tgt.any():
                    bsz = P.BS[np.arange(P.n), leg['exit_m']][tgt]; fills.append((leg['contracts'], float(np.mean(bsz >= leg['contracts'])), float(np.median(bsz))))
            r['target_fill_ok'] = json.dumps(fills)
            rows.append(r)
        df = write(rows, f't5_scaleout_{uni}.csv'); print(df.select('rule', 'ev_pct_disc', 'win_rate_disc', 'avg_win_pct_disc', 'avg_loss_pct_disc', 'breakeven_win_rate_disc', 'ev_pct_check', 'win_rate_check', 'breakeven_win_rate_check', 'target_fill_ok'))
        # ---------- Test 6: liquidity at the quoted NBBO
        rows = []
        kw = spec_kwargs(uni); res = E.simulate(P, **kw); xm = res['legs'][0]['exit_m']
        bs_exit = P.BS[np.arange(P.n), xm]
        for k in (1, 2, 3, 5, 10):
            r = dict(contracts=k, entry_ask_size_ok=float(np.mean(P.df['entry_ask_size'].to_numpy() >= k)), exit_bid_size_ok=float(np.nanmean(bs_exit >= k)),
                     both_ok=float(np.nanmean((P.df['entry_ask_size'].to_numpy() >= k) & (bs_exit >= k))))
            for prod in E.PRODUCTS:
                mk = P.product == prod
                if mk.any(): r[f'both_ok_{prod}'] = float(np.nanmean((P.df['entry_ask_size'].to_numpy()[mk] >= k) & (bs_exit[mk] >= k)))
            rows.append(r)
        df = write(rows, f't6_liquidity_{uni}.csv'); print(df)
        # does the spec stack's result depend on quoted size (a proxy for what size would have told)?
        asz = P.df['entry_ask_size'].to_numpy(); rows = []
        for lo, hi in ((0, 5), (5, 20), (20, 100), (100, 1e9)):
            mk = (asz >= lo) & (asz < hi)
            for lab, m2 in (('disc', ~P.is_check), ('check', P.is_check)):
                s = E.stats(P, res, mk & m2); s.update(ask_size_bucket=f'{lo}-{hi}', period=lab, median_ask=float(np.median(P.ask0[mk & m2])) if (mk & m2).any() else np.nan); rows.append(s)
        df = write(rows, f't6_by_size_{uni}.csv'); print(df)
        # ---------- Test 7: circuit breaker
        rows = []; sim_rows = []
        for stack_name, kw in (('spec 1c', spec_kwargs(uni)), ('prem -32% + flat', dict(prem_stop=0.68))):
            res = E.simulate(P, **kw)
            for prod in E.PRODUCTS + ['ALL']:
                mk = P.product == prod if prod != 'ALL' else np.ones(P.n, bool)
                if mk.sum() < 60: continue
                order = np.lexsort((P.e[mk], P.session[mk])); pnl = res['pnl'][mk][order]; pct = res['pct'][mk][order]; chk = P.is_check[mk][order]; yr = P.year[mk][order]
                live, pf_hist = breaker(pnl)
                periods = [('all', np.ones(len(pnl), bool)), ('check', chk)] + [(y, yr == y) for y in sorted(set(yr))]
                for lab, m2 in periods:
                    rows.append(dict(stack=stack_name, product=prod, period=lab, trades=int(m2.sum()), ev_pct_no_breaker=float(pct[m2].mean()),
                                     ev_pct_live_only=float(pct[m2 & live].mean()) if (m2 & live).any() else np.nan, live_trades=int((m2 & live).sum()),
                                     paper_share=float(1 - live[m2].mean()), ev_pct_of_skipped=float(pct[m2 & ~live].mean()) if (m2 & ~live).any() else np.nan,
                                     total_usd_no_breaker=float(pnl[m2].sum()), total_usd_live_only=float(pnl[m2 & live].sum()),
                                     skipped_winners_share=float((pnl[m2 & ~live] > 0).mean()) if (m2 & ~live).any() else np.nan))
            # sampling noise: streams drawn from this stack's check-period outcomes, shifted to a true EV of +0, +5, +10, +20% of debit
            pct_c = res['pct'][P.is_check]
            for shift_to in (0.0, 0.05, 0.10, 0.20):
                sim_rows.append(dict(stack=stack_name, universe=uni, true_ev_pct=shift_to, **trip_rate(pct_c, shift_to)))
        df = write(rows, f't7_breaker_{uni}.csv'); print(df)
        df = write(sim_rows, f't7_breaker_noise_{uni}.csv'); print(df)
    json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1)

def breaker(pnl, window=30, pf_min=1.05):
    """rolling profit factor over the last `window` trades (live and paper alike); when < pf_min the next trade is paper"""
    n = len(pnl); live = np.ones(n, bool); pfs = np.full(n, np.nan)
    for i in range(n):
        if i >= window:
            w = pnl[i - window:i]; g = w[w > 0].sum(); l = -w[w < 0].sum()
            pf = g / l if l > 0 else np.inf; pfs[i] = pf
            live[i] = pf >= pf_min
    return live, pfs

def trip_rate(pct, true_ev, n_trades=200, window=30, pf_min=1.05, nsim=2000, seed=11):
    """draw i.i.d. streams from the empirical outcome distribution shifted so the mean is true_ev; how often the 30-trade PF trips"""
    x = pct - pct.mean() + true_ev; rng = np.random.default_rng(seed)
    tripped = 0; share = []; first = []
    for _ in range(nsim):
        s = rng.choice(x, n_trades); live, pfs = breaker(s, window, pf_min)
        t = ~live[window:]; tripped += t.any(); share.append(t.mean())
        if t.any(): first.append(window + np.argmax(t))
    return dict(p_trip_in_200=tripped / nsim, paper_share=float(np.mean(share)), median_first_trip=float(np.median(first)) if first else np.nan,
                win_rate=float((x > 0).mean()), avg_win=float(x[x > 0].mean()), avg_loss=float(x[x <= 0].mean()))

if __name__ == '__main__':
    main()
