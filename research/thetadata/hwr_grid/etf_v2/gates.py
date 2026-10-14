"""COMPASS_RESEARCH_PLAN.md §10 gate verdicts, item by item, for every TRAIN-selected configuration (etf_v2).  Reads results/
selected_test.csv, integrity.json, data_manifest.csv, settlement_spy.csv, stress_selected.csv and $HWR_WORK/integrity_*.parquet.
Writes results/gates.csv.  Items: data integrity, execution realism, statistical validity, tail survival, forward validation,
classification; carry-lane verdict = all six; signal-lane verdict = all six + beats random entry on the same days by > one round trip."""
import os, sys, json
import numpy as np
import polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
import analyze as A

DATA_REASONS = ['out_of_band', 'out_of_band_spot', 'no_quote', 'no_spot', 'no_em']


def main():
    S = pl.read_csv(os.path.join(C.OUT, 'selected_test.csv'))
    ST = pl.read_csv(os.path.join(C.OUT, 'stress_selected.csv'))
    SE = pl.read_csv(os.path.join(C.OUT, 'settlement_spy.csv'))
    M = pl.read_csv(os.path.join(C.OUT, 'data_manifest.csv'))
    integ = {}
    for tk in C.TICKERS:
        fp = os.path.join(C.WORK, f'integrity_{tk}_TEST.parquet')
        if os.path.exists(fp): integ[tk] = pl.read_parquet(fp)
    rows = []
    for r in S.iter_rows(named=True):
        scope, cfg, tag = r['scope'], r['cfg'], r['selection']
        sk, e, tp, st, ex, f = cfg.split('|')
        posthoc = tag.startswith('PH')
        # ---- data integrity: every TEST session has a hashed full-chain file; every strike the configuration needs exists at its entry
        miss = 0; slots = 0; files_ok = True
        for tk in A.SCOPES[scope]:
            m = M.filter((pl.col('tk') == tk) & (pl.col('date') >= C.TEST[0]) & (pl.col('date') <= C.TEST[1]))
            files_ok &= bool(m['full_file'].all() and m['sha256'].null_count() == 0)
            I = integ[tk]
            if f == 'F2':
                I = pl.concat([I.filter((pl.col('T') == e) & ~pl.col('date').is_in(list(A.FOMC))), I.filter((pl.col('T') == '14:05') & pl.col('date').is_in(list(A.FOMC)))])
            else:
                I = I.filter(pl.col('T') == e)
            if f == 'F1': I = I.filter(~pl.col('date').is_in(list(A.FOMC)))
            if f == 'F3': I = I.filter(~pl.col('date').is_in(list(A.FOMC | A.ME)))
            slots += I.height; miss += I.filter(pl.col(f'st_{sk}').is_in(DATA_REASONS)).height
        g_data = files_ok and miss == 0
        d_data = f'{slots} TEST entry slots, {miss} with a needed strike or quote missing; every TEST session has a full-chain file with sha256 (data_manifest.csv)'
        # ---- execution realism
        if ex == 'E2':
            se = SE.filter((pl.col('cfg') == cfg) & (pl.col('period') == 'TEST'))
            ah = (f"SPY pessimistic after-hours re-valuation {se['pessimistic_ah_mean'][0]:+.2f} [{se['pessimistic_ah_lo'][0]:+.2f}, {se['pessimistic_ah_hi'][0]:+.2f}] "
                  f"(n = {se['n_with_ah'][0]})" if se.height and 'SPY' in A.SCOPES[scope] else 'no after-hours data for this ticker')
            g_exec = False
            d_exec = ('E2 holds physically settled American ETF options through the 16:00 close and values them at intrinsic against the 15:59-bar close; '
                      'no official settlement value exists and after-hours exercise/assignment is ignored (optimistic); ' + ah)
        else:
            g_exec = True
            d_exec = ('NBBO bid/ask fills at entry and at the 15:55 exit, $0.70/contract/side; only legs with ask <= $0.05 (and zero-bid longs) are left to expire, '
                      'valued at the 16:00 close (caveat: their after-hours exercise risk is not modelled)')
        # ---- statistical validity on complete data, out of sample, after multiplicity accounting (Bonferroni over the 8 pre-registered selections)
        g_stat = bool(r['test_lo'] > 0 and r['test_lo_bonf8'] > 0)
        d_stat = (f"TEST n = {r['test_n']}, mean {r['test_mean']:+.2f} [{r['test_lo']:+.2f}, {r['test_hi']:+.2f}]; Bonferroni-8 lower bound {r['test_lo_bonf8']:+.2f}; "
                  f"Romano-Wolf rejected in the TEST grid: {'yes' if r['rw_rejected_test'] else 'no'}")
        # ---- tail survival
        s = ST.filter((pl.col('scope') == scope) & (pl.col('selection') == tag)).row(0, named=True)
        w15 = min(s['pnl_-15.00_median'], s['pnl_+15.00_median']); wh = min(s['pnl_hist_down_worst'], s['pnl_hist_up_worst'])
        g_tail = False
        d_tail = (f"unprotected settlement P&L per lot, median trade: -15 % {s['pnl_-15.00_median']:+.0f}, +15 % {s['pnl_+15.00_median']:+.0f}, "
                  f"-8.42 % {s['pnl_-8.42_median']:+.0f}, +8.42 % {s['pnl_+8.42_median']:+.0f}; worst trade at the worst historical move {wh:+.0f}; "
                  f"capital per lot for an 8 % budget at +-15 %: {s['capital_8pct_budget_15pct_median']:.0f} (median trade); margin estimates (formula, not broker-verified): "
                  f"Reg-T {s['regt_20pct_median']:.0f} (20 %) / {s['regt_15pct_median']:.0f} (15 %), PM-style -8/+6 % {s['pm_scen_-8_+6_median']:.0f}; "
                  'loss is stated, but no sizing rule or broker margin has been adopted for this lane -> not passed')
        # ---- forward validation and classification
        g_fwd = False; d_fwd = '0 forward paper sessions with live NBBO logging (needs >= 150 sessions and >= 7 calendar months)'
        g_cls = True; d_cls = 'carry: sells same-day premium, claims no timing skill (signal version requires beating random entry)'
        g_rand = bool(r['gate_beats_random_matched'])
        d_rand = (f"matched days: lane {r['matched_lane_mean']:+.2f} vs random {r['matched_base_mean']:+.2f}, paired diff {r['paired_diff']:+.2f} "
                  f"[{r['paired_lo']:+.2f}, {r['paired_hi']:+.2f}] vs round trip {r['test_cost']:.2f}; pre-registered unpaired diff {r['lane_minus_base']:+.2f}")
        carry = all([g_data, g_exec, g_stat, g_tail, g_fwd, g_cls])
        rows.append(dict(scope=scope, selection=tag, post_hoc=posthoc, cfg=cfg, desc=r['desc'],
                         data_integrity=g_data, data_integrity_detail=d_data, execution_realism=g_exec, execution_realism_detail=d_exec,
                         statistical_validity=g_stat, statistical_validity_detail=d_stat, tail_survival=g_tail, tail_survival_detail=d_tail,
                         forward_validation=g_fwd, forward_validation_detail=d_fwd, classification=g_cls, classification_detail=d_cls,
                         beats_random_matched=g_rand, beats_random_detail=d_rand,
                         carry_verdict='PASS' if carry and not posthoc else 'FAIL', signal_verdict='PASS' if carry and g_rand and not posthoc else 'FAIL',
                         items_passed_carry=sum([g_data, g_exec, g_stat, g_tail, g_fwd, g_cls])))
    G = pl.DataFrame(rows); G.write_csv(os.path.join(C.OUT, 'gates.csv'))
    print(G.select(['scope', 'selection', 'cfg', 'data_integrity', 'execution_realism', 'statistical_validity', 'tail_survival', 'forward_validation', 'beats_random_matched', 'carry_verdict']))


if __name__ == '__main__':
    main()
