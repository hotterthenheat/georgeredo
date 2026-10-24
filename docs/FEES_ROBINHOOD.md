# Robinhood options fees: the research's default cost model from 2026-10-24

The owner trades on Robinhood and asked for its fee math to be used everywhere ("use that math for everything from now
on"). From 2026-10-24 the research repo's **default cost model** is Robinhood's options fee schedule below, in place of
the $0.65-a-contract-each-way commission (plus pass-throughs) that the studies used.

**Fills do not change.** A buy fills at the ask and a sale at the bid of the NBBO, exactly as before. Only the fees change.

Every figure below was read on **2026-10-24** from public pages only. No account page or login was used.

## Each fee

| fee | amount | side | applies to | source |
|---|---|---|---|---|
| Commission | $0 | both | stock, ETF and index options | Robinhood Financial fee schedule (PDF, document 20260929-5969628-19014374): "Commission-free trading refers to $0 commissions … and their options"; Robinhood support, *Trading fees on Robinhood* |
| Options Regulatory Fee (ORF) and OCC clearing fee, combined | $0.04 per contract | buy and sell | every option | fee schedule PDF: "Options Regulatory and OCC Clearing Fee: $0.04 per options contract (buys and sells)"; support page: combined $0.04 from 2025-01-10. Robinhood's blended rate, not the exchange's own ORF. |
| FINRA Trading Activity Fee (TAF) | $0.00329 per contract, at most $9.79 a trade; a total under one cent rounds down to $0, otherwise to the nearest cent | sell only | stock and ETF options; **not** index options | fee schedule PDF (effective 2026-01-01); FINRA fee adjustment schedule (SR-FINRA-2024-019: $0.00279 in 2024–25, $0.00329 in 2026, $0.00390 in 2027). The support page says it is paused 2026-10-01 → 2026-12-31 "per FINRA". |
| SEC fee (Section 31) | $20.60 per $1,000,000 of sale principal, rounded **up** to the cent | sell only | stock and ETF options; **not** index options | fee schedule PDF (effective 2026-04-04; $0.00 before that); SEC Fee Rate Advisory 2026-2; FINRA Information Notice 2026-03-17 |
| Consolidated Audit Trail (CAT) fee | $0.0003 per contract; a total under one cent rounds down to $0 | buy and sell | every option | fee schedule PDF and support page |
| Index options contract fee (Robinhood's own) | **$0.50** per contract without Gold; $0.35 with Gold | buy and sell | index options (SPX, SPXW, …) | fee schedule PDF: "Non-Gold Rate: $0.50 per options contract (buys and sells) / Gold Rate: $0.35" |
| Index exchange fee passed through: SPXW | $0.50 per contract under $1.00 of premium; $0.59 at $1.00 and up | buy and sell | SPXW | support page, *Trading fees on Robinhood* (index options exchange fees table) |
| Index exchange fee passed through: SPX (AM, monthly) | $0.57 under $1.00; $0.66 at $1.00 and up | buy and sell | SPX | same table |
| Exercise and assignment | $0 | — | every option; cash settlement of an index option included | none listed in the fee schedule PDF; the support article *Expiration, exercise, and assignment* names no fee |

Source URLs (all read 2026-10-24):

- Robinhood Financial fee schedule (PDF, the US standard schedule): https://cdn.robinhood.com/assets/robinhood/legal/RHF%20Fee%20Schedule.pdf
- Robinhood support, *Trading fees on Robinhood*: https://robinhood.com/us/en/support/articles/trading-fees-on-robinhood
- Robinhood support, *Expiration, exercise, and assignment*: https://robinhood.com/us/en/support/articles/expiration-exercise-and-assignment
- FINRA TAF fee adjustment schedule: https://www.finra.org/rules-guidance/rule-filings/sr-finra-2024-019/fee-adjustment-schedule
- SEC Fee Rate Advisory 2026-2: https://www.sec.gov/rules-regulations/fee-rate-advisories/2026-2
- FINRA Information Notice 2026-03-17 (Section 31 rate): https://www.finra.org/rules-guidance/notices/information-notice-20260317
- Cboe filing SR-CBOE-2026-031 (Cboe's own customer SPXW rates, effective 2026-04-01): https://cdn.cboe.com/resources/regulation/rule_filings/approved/2026/SR-CBOE-2026-031.pdf

## What could not be confirmed, and the conservative figure used

Each choice below uses the higher figure. Each is labelled where it is used.

1. **Gold or not.** It is not known whether the owner's account has Gold. The model uses the **non-Gold $0.50** index
   contract fee. With Gold, every SPXW contract-side is $0.15 cheaper.
2. **SPXW exchange fee.** Cboe's own customer rate in SR-CBOE-2026-031 is $0.36 a contract under $1.00 of premium (fee
   code CS), plus the $0.14 SPXW electronic execution surcharge: $0.50. The same filing sets $0.40 at $1.00 and up (fee
   code CT, proposed to cover SPX including SPXW), which gives $0.54 with the surcharge. Robinhood's table says $0.50 and
   **$0.59**. The model uses Robinhood's figures, the higher ones.
3. **TAF pause.** Robinhood's support page says the TAF is paused from 2026-10-01 to 2026-12-31. The model charges it
   anyway, at $0.00329, because the pause is temporary.
4. **CAT.** The fee schedule and the support page both list $0.0003 a contract. A secondary summary says regulators
   stopped charging CAT on 2025-12-01. The model charges the $0.0003.
5. **Rounding.** Robinhood rounds the SEC fee up to the cent, and rounds a TAF or CAT total to the nearest cent (a total
   under a cent goes to $0), on each order. The model takes the higher figure on every sold leg: it rounds each sold
   leg's TAF and SEC fee **up** to the next cent, so a 1-lot ETF option sale pays $0.01 + $0.01. CAT is charged per
   contract, unrounded.
6. **Exercise and assignment.** No fee is listed, and no page states the fee is $0 outright. There is no published
   figure to take the higher of, so the model uses $0. A contract held to expiry or settlement pays no exit fee. That is
   also how every study treated expiry.
7. **The SEC rate in the past.** The SEC fee was $0.00 before 2026-04-04. The model charges today's $20.60 per million
   on every historical sale. That is the higher figure, and it is today's schedule.

## The default model

Per contract, per side. "Price" is the option's per-share premium at the fill.

| instrument | buy (opening or closing) | sell (opening or closing) | held to expiry or settlement |
|---|---|---|---|
| **ETF and single-name options** (SPY, QQQ, IWM, stocks) | **$0.0403** ($0.04 ORF+OCC, $0.0003 CAT) | **$0.0403** + TAF $0.00329 + SEC $20.60 per million of proceeds, each rounded up to the cent per sold leg. **A 1-lot sale pays $0.0603.** A 10-lot sale at $1.00 pays $0.403 + $0.04 + $0.03 = $0.473 ($0.0473 a contract). | $0 |
| **SPXW** (cash-settled, PM) | **$1.0403** under $1.00 of premium; **$1.1303** at $1.00 and up ($0.50 index fee, non-Gold, + $0.50 / $0.59 Cboe + $0.04 + $0.0003) | the same: no TAF and no SEC fee on an index option | $0 (cash settlement) |
| SPX (AM, monthly) | $1.1103 under $1.00; $1.2003 at $1.00 and up | the same | $0 |

In short:

- **ETF options (SPY, QQQ, IWM):** $0 commission plus pass-throughs of about **$0.04 a contract to buy and $0.06 to
  sell** (a 1-lot).
- **SPXW:** **$1.04 a contract a side under $1.00 of premium, $1.13 at $1.00 and up**. With Gold, $0.89 and $0.98.

The studies before 2026-10-24 charged instead:

- SPY, QQQ and IWM: $0.65 a contract each way, or $0.68748 with the pass-throughs.
- SPXW: $1.18748 / $1.27748 a contract each way.
- The older Compass studies (S01–S17, V1–V8, the lifecycle): $0.70 a contract each side.

Robinhood's schedule is about $0.63 a contract-side cheaper on the ETFs, and $0.15 cheaper on SPXW.

**Stock trades** (100 shares, the H-series edge studies) also follow the schedule:

- Commission: $0.
- On each sale (a long's exit, or a short's entry): the SEC fee of $20.60 per million of proceeds, rounded up to the
  cent, and the TAF of $0.000195 a share (at most $9.79), rounded up to the cent.
- CAT: $0.000003 a share each side.

The stock studies charged two different things:

- **$0.01 a share on an auction or opening fill** (the official close or the 09:30 print). Their preregs (PREREG_H1.md
  §2, PREREG_H7.md, PREREG_H4.md) define this as fees only: commission, auction and clearing fees, TAF and the SEC fee.
  It is replaced by Robinhood's fees for that side.
- **$0.005 a share on a fill at a bar's print.** This is half the one-cent spread, so it is a fill cost. It stays, as a
  fill does, and Robinhood's fees for that side are added to it.

For a 100-share SPY sale at $600, Robinhood's fees are $1.24 (SEC) + $0.02 (TAF) + $0.0003 (CAT). That is about $1.26,
against the study's $1.00 for the same sale.

The code that applies this is `scripts/fees_robinhood.py`. The final report's build (`research_notes/FINAL REPORT/build/`)
and the daily forward job's reports (`scripts/paper_backtest.py`, the Compass features and edge forward tests) read that
same module.
