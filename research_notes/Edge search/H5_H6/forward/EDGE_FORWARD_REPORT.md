# Edge search H5 and H6: the forward tests

The rules: `PREREG_H5.md` and `PREREG_H6.md` (commit `e114e30`, committed alone before any forward session of either). Written by `edge_forward.py` (edge-forward-2026-10-23.1) from the append-only files in this folder. Dollars a trade after every spread and fee. **No verdict before N**; at N the verdict uses exactly the first N and is written once (`verdicts.json`).

| test | counted / N | trades | mean $ a trade | 95 % block interval | verdict |
|---|---|---|---|---|---|
| H5 SPY − SPXW straddle package, 15:30 → 15:58 (sessions; block 20) | 1 / 1,326 | 1 | +72.48 | — | **no verdict** (interim figures only) |
| H6 SPY + QQQ 0.30/0.15 put spreads, monthly (months; block 3) | 0 / 449 | 0 | — | — | **no verdict** (interim figures only) |

H5: sessions 2026-10-23 → 2026-10-23 (forward from 2026-10-23); traded 1; the mean at the mids, for reading only: +152.50. The mapped prior was negative (PREREG_H5.md section 1).
H6: entries 0 (from 2026-11-02), closed 0, open 0; by name, for reading only: SPY 0 closed, mean —, QQQ 0 closed, mean —. N = 449 months (898 spreads, about 37 years): no verdict is reachable in any useful time (PREREG_H6.md section 6).

No interval is printed under 60 sessions (H5) or 12 months (H6). The two tests are read separately; the ledger counts each as a hypothesis.

## At Robinhood fees (descriptive)

The same forward trades on the same fills, re-priced at Robinhood's fees (the research's default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`, `robinhood-2026-10-24.1`): the study's $0.68748 a SPY/QQQ contract a side and SPXW's $1.18748 / $1.27748 added back; Robinhood's $0.0403 a contract a side (plus TAF and SEC on an ETF sale) and SPXW $1.0403 / $1.1303 charged. **The pass rules and N stay on the pre-registered fees (PREREG_H5.md, PREREG_H6.md, frozen); the verdict column above is the only verdict.**

| test | trades | mean $ a trade at Robinhood fees | pre-registered fees |
|---|---|---|---|
| H5 | 1 | +98.85 | +72.48 |
| H6 | 0 | — | — |
