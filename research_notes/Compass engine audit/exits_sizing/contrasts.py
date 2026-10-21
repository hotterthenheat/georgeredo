"""Paired contrasts between exit rules: the per-trade difference in % of debit (rule B minus rule A) on the same trades,
with a bootstrap-by-session 95% interval, on 2022-2024 (pick) and 2025-2026 (read) separately, and the difference
without the 5 sessions that favour B most. Writes out/contrasts.csv.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I contrasts.py
"""
import os, sys, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
from run_tests import spec_kwargs, SPEC_T1, SPEC_2C, SPEC_3C
pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_rows(100); pl.Config.set_tbl_formatting('ASCII_MARKDOWN'); pl.Config.set_tbl_hide_column_data_types(True); pl.Config.set_tbl_hide_dataframe_shape(True)

def boot_diff(d, sess, seed=5, nb=2000):
    days = np.unique(sess); s = np.array([d[sess == x].sum() for x in days]); n = np.array([(sess == x).sum() for x in days])
    rng = np.random.default_rng(seed); m = []
    for _ in range(nb):
        k = rng.integers(0, len(days), len(days)); m.append(s[k].sum() / n[k].sum())
    top5 = np.argsort(s)[-5:]; keep = np.ones(len(days), bool); keep[top5] = False
    return float(d.mean()), float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5)), float(s[keep].sum() / n[keep].sum()), int((s > 0).sum()), int((s < 0).sum())

rows = []
for uni in ('A', 'B'):
    P = E.load(universe=uni); sk = spec_kwargs(uni)
    C = [('VIX-tiered trail vs flat 10% (from +6%, with -32% stop)', dict(prem_stop=0.68, trail='vix', trail_act=0.06), dict(prem_stop=0.68, trail=0.10, trail_act=0.06)),
         ('VIX-tiered trail vs flat 6%', dict(prem_stop=0.68, trail='vix', trail_act=0.06), dict(prem_stop=0.68, trail=0.06, trail_act=0.06)),
         ('VIX trail from +6% vs no trail (-32% stop + flat)', dict(prem_stop=0.68), dict(prem_stop=0.68, trail='vix', trail_act=0.06)),
         ('BE lock +6% vs none (T1 all-out, -32% stop)', dict(prem_stop=0.68, targets=SPEC_T1), dict(prem_stop=0.68, targets=SPEC_T1, be_lock=0.06)),
         ('BE lock +12% vs +6% (T1 all-out, -32% stop)', dict(prem_stop=0.68, targets=SPEC_T1, be_lock=0.06), dict(prem_stop=0.68, targets=SPEC_T1, be_lock=0.12)),
         ('BE lock +0% vs +6% (T1 all-out, -32% stop)', dict(prem_stop=0.68, targets=SPEC_T1, be_lock=0.06), dict(prem_stop=0.68, targets=SPEC_T1, be_lock=0.0)),
         ('BE lock +6% vs none (flat, -32% stop)', dict(prem_stop=0.68), dict(prem_stop=0.68, be_lock=0.06)),
         ('time stop 5 min vs none (-32% stop + flat)', dict(prem_stop=0.68), dict(prem_stop=0.68, time_stop=5)),
         ('time stop 15 min vs 5 min', dict(prem_stop=0.68, time_stop=5), dict(prem_stop=0.68, time_stop=15)),
         ('premium stop -20% vs -32% (flat)', dict(prem_stop=0.68), dict(prem_stop=0.80)),
         ('premium stop -50% vs -32% (flat)', dict(prem_stop=0.68), dict(prem_stop=0.50)),
         ('premium stop -20% vs -32% inside the spec stack', sk, dict(sk, prem_stop=0.80)),
         ('structural stop vs none inside the spec stack', dict(sk, struct_buffer=None, b_bps=None), sk),
         ('spec 3c vs spec 1c', sk, dict(sk, targets=SPEC_3C)),
         ('T1 +25% all-out vs no target (-32% stop + flat)', dict(prem_stop=0.68), dict(prem_stop=0.68, targets=SPEC_T1)),
         ('spec 1c stack vs -32% stop + flat alone', dict(prem_stop=0.68), sk),
         ('spec 1c stack vs -32% stop + flat 10% trail from +6%', dict(prem_stop=0.68, trail=0.10, trail_act=0.06), sk)]
    for name, ka, kb in C:
        d = E.simulate(P, **kb)['pct'] - E.simulate(P, **ka)['pct']
        r = dict(universe=uni, contrast=name)
        for lab, mk in (('disc', ~P.is_check), ('check', P.is_check)):
            m, lo, hi, wo5, up, dn = boot_diff(d[mk], P.session[mk])
            r.update({f'diff_{lab}': m, f'lo_{lab}': lo, f'hi_{lab}': hi, f'wo_best5_{lab}': wo5, f'days_B_better_{lab}': up, f'days_A_better_{lab}': dn})
        rows.append(r)
df = pl.DataFrame(rows); df = df.with_columns([pl.col(c).round(4) for c, t in df.schema.items() if t == pl.Float64])
df.write_csv(os.path.join(E.OUT, 'contrasts.csv')); print(df)
