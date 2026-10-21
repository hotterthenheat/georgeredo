"""Per-product view of the main contrasts (both universes, both periods). Writes out/by_product.csv.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I by_product.py
"""
import os, sys, numpy as np, polars as pl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E
from run_tests import spec_kwargs, SPEC_T1, SPEC_2C, SPEC_3C
pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(300); pl.Config.set_tbl_rows(200)
rows = []
for uni in ('A', 'B'):
    P = E.load(universe=uni)
    variants = [('spec 1c', spec_kwargs(uni)), ('spec 3c', dict(spec_kwargs(uni), targets=SPEC_3C)), ('prem -32% + flat', dict(prem_stop=0.68)),
                ('prem -32% + flat + trail10 (+6%)', dict(prem_stop=0.68, trail=0.10, trail_act=0.06)),
                ('prem -32% + T1 all-out', dict(prem_stop=0.68, targets=SPEC_T1)), ('prem -32% + T1 + BE lock +6%', dict(prem_stop=0.68, targets=SPEC_T1, be_lock=0.06)),
                ('prem -32% + T1 + BE lock +12%', dict(prem_stop=0.68, targets=SPEC_T1, be_lock=0.12)),
                ('prem -32% + time stop 5', dict(prem_stop=0.68, time_stop=5)), ('struct only (A 2bps / B 15bps)', dict(prem_stop=None, struct_buffer=2.0 if uni == 'A' else 0.0, b_bps=None if uni == 'A' else 15.0)),
                ('hold to 15:58', dict(prem_stop=None))]
    for name, kw in variants:
        res = E.simulate(P, **kw)
        for prod in E.PRODUCTS:
            mk = P.product == prod
            if not mk.any(): continue
            r = dict(universe=uni, product=prod, rule=name)
            for lab, m2 in (('disc', ~P.is_check), ('check', P.is_check)):
                s = E.stats(P, res, mk & m2); r.update({f'{k}_{lab}': v for k, v in s.items()})
            st = E.stress(P, res, mk & P.is_check); r.update({f's_{k}': v for k, v in st.items() if not k.startswith('y')})
            rows.append(r)
df = pl.DataFrame(rows, infer_schema_length=None); df = df.with_columns([pl.col(c).round(5) for c, t in df.schema.items() if t == pl.Float64])
df.write_csv(os.path.join(E.OUT, 'by_product.csv'))
print(df.select('universe', 'product', 'rule', 'n_disc', 'ev_pct_disc', 'win_rate_disc', 'n_check', 'ev_pct_check', 'win_rate_check', 'avg_loss_pct_check', 's_boot_lo', 's_boot_hi', 's_without_best5', 's_days_up', 's_days'))
