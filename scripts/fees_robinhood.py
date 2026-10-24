"""fees_robinhood.py — Robinhood's options and stock fee schedule, the research's DEFAULT cost model from 2026-10-24
(the owner: "use that math for everything from now on"). The schedule, its sources (read 2026-10-24) and every
conservative choice are in docs/FEES_ROBINHOOD.md; this module is the one place the numbers live. Fills do not change
(a buy at the ask, a sale at the bid): only the fees.

Per contract, per side (one leg of one order):
  every option     $0.04 ORF + OCC clearing, $0.0003 CAT                                  (buy and sell)
  stock/ETF option + on a sale: FINRA TAF $0.00329 a contract (at most $9.79) and the SEC fee $20.60 per $1M of the
                     sale's proceeds, EACH ROUNDED UP to the cent per sold leg (the conservative reading of Robinhood's
                     per-order rounding; a 1-lot sale pays $0.01 + $0.01)
  index option     + Robinhood's index contract fee $0.50 (non-Gold; Gold $0.35) + the exchange fee it passes through
                     (SPXW $0.50 under $1.00 of premium, $0.59 at $1.00 and up; SPX $0.57 / $0.66; …) — no TAF, no SEC fee
  expiry, exercise, assignment, cash settlement: $0
Stock (100-share studies): $0 commission; on a sale the SEC fee (rounded up) and the TAF $0.000195 a share (at most
$9.79, rounded up); CAT $0.000003 a share each side.

    option_fee(root, price, qty, side)          one leg, one side ('buy' | 'sell'), dollars
    option_fee_expr(root, price, qty, side)     the same as a polars expression (root may be a column or a str)
    stock_fee(price, shares, side)              one stock fill, dollars
"""
from __future__ import annotations

import math

VERSION = 'robinhood-2026-10-24.1'
READ_ON = '2026-10-24'

ORF_OCC = 0.04            # a contract, buys and sells (Robinhood's combined, blended ORF + OCC clearing fee)
CAT = 0.0003              # a contract, buys and sells
TAF_OPT = 0.00329         # a contract sold (stock and ETF options), at most TAF_MAX a trade
TAF_SHARE = 0.000195      # a share sold
TAF_MAX = 9.79
SEC_RATE = 20.60e-6       # of the sale's principal (stock and stock/ETF options), rounded up to the cent
INDEX_FEE = 0.50          # Robinhood's index option contract fee, non-Gold (Gold 0.35) — the conservative choice
INDEX_FEE_GOLD = 0.35
CAT_SHARE = 0.000003

# the exchange fee Robinhood passes through on an index option, a contract: (under $1.00 of premium, $1.00 and up).
# Where Robinhood quotes a range the top of it is taken (conservative).
EXCHANGE = {
    'SPXW': (0.50, 0.59), 'SPX': (0.57, 0.66),
    'VIX': (0.45, 0.45), 'VIXW': (0.45, 0.45),
    'NDX': (0.75, 0.75), 'NDXP': (0.75, 0.75),
    'RUT': (0.18, 0.18), 'RUTW': (0.18, 0.18),
    'XSP': (0.07, 0.07), 'DJX': (0.07, 0.07), 'MRUT': (0.07, 0.07), 'XND': (0.0, 0.0),
}
INDEX_ROOTS = frozenset(EXCHANGE)


def ceil_cent(x: float) -> float:
    """rounded UP to the next cent (a sub-cent amount above zero is a cent)"""
    if not (x > 0):
        return 0.0
    return math.ceil(x * 100.0 - 1e-9) / 100.0


def is_index(root: str) -> bool:
    return str(root).upper() in INDEX_ROOTS


def option_fee(root: str, price: float, qty: float, side: str) -> float:
    """Robinhood's fees on one leg of one order: `qty` contracts of `root` at `price` (per share), side 'buy' | 'sell'"""
    if not (qty and qty > 0):
        return 0.0
    f = qty * (ORF_OCC + CAT)
    r = str(root).upper()
    if r in INDEX_ROOTS:
        lo, hi = EXCHANGE[r]
        return f + qty * (INDEX_FEE + (lo if (price is not None and price < 1.0 - 1e-9) else hi))
    if side == 'sell':
        f += ceil_cent(min(TAF_OPT * qty, TAF_MAX))
        f += ceil_cent(SEC_RATE * max(price or 0.0, 0.0) * 100.0 * qty)
    return f


def stock_fee(price: float, shares: float, side: str) -> float:
    f = CAT_SHARE * shares
    if side == 'sell':
        f += ceil_cent(min(TAF_SHARE * shares, TAF_MAX)) + ceil_cent(SEC_RATE * price * shares)
    return f


def _ceil_cent_expr(e):
    import polars as pl
    return pl.when(e > 0).then(((e * 100.0) - 1e-9).ceil() / 100.0).otherwise(0.0)


def option_fee_expr(root, price, qty, side: str):
    """option_fee as a polars expression; `root` is a column expression or a plain root string, `price` and `qty`
    expressions or numbers. A quantity of 0 (a leg never traded) costs nothing."""
    import polars as pl
    R = pl.lit(root) if isinstance(root, str) else root
    P = price if isinstance(price, pl.Expr) else pl.lit(float(price))
    Q = qty if isinstance(qty, pl.Expr) else pl.lit(float(qty))
    R = R.cast(pl.Utf8).str.to_uppercase()
    exch = pl.lit(0.0)
    for r, (lo, hi) in EXCHANGE.items():
        exch = pl.when(R == r).then(pl.when(P < 1.0 - 1e-9).then(lo).otherwise(hi)).otherwise(exch)
    idx = R.is_in(list(INDEX_ROOTS))
    base = Q * (ORF_OCC + CAT)
    out = base + pl.when(idx).then(Q * (INDEX_FEE + exch)).otherwise(0.0)
    if side == 'sell':
        taf = _ceil_cent_expr(pl.min_horizontal(Q * TAF_OPT, pl.lit(TAF_MAX)))
        sec = _ceil_cent_expr(pl.lit(SEC_RATE) * pl.max_horizontal(P.fill_null(0.0), pl.lit(0.0)) * 100.0 * Q)
        out = out + pl.when(idx).then(0.0).otherwise(taf + sec)
    return pl.when(Q > 0).then(out).otherwise(0.0)


def per_contract_table() -> list[tuple[str, str, str]]:
    """the one-line summary for reports: (instrument, buy, sell) per contract, a 1-lot"""
    return [('ETF / single-name option', f'${ORF_OCC + CAT:.4f}', f'${ORF_OCC + CAT:.4f} + $0.01 TAF + $0.01 SEC (1-lot) = ${ORF_OCC + CAT + 0.02:.4f}'),
            ('SPXW under $1.00', f'${ORF_OCC + CAT + INDEX_FEE + 0.50:.4f}', 'the same'),
            ('SPXW $1.00 and up', f'${ORF_OCC + CAT + INDEX_FEE + 0.59:.4f}', 'the same')]


SUMMARY = ('Robinhood fees (docs/FEES_ROBINHOOD.md, read 2026-10-24): $0 commission; $0.0403 a contract a side on ETF options '
           '(+ TAF and SEC on a sale, each rounded up to the cent: a 1-lot sale $0.0603); SPXW $1.0403 a contract a side under '
           '$1.00 of premium, $1.1303 at $1.00 and up (non-Gold index fee); nothing at expiry or settlement. Fills unchanged.')
