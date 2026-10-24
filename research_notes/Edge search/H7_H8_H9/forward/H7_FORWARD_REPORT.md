# Edge search H7: the forward test

Rule: `FORWARD_RULE_H7.md` (`fcc1f4d`; its rule `PREREG_H7.md`, `edca472`). Written by `forward_h7_h9.py` (edge-forward-h7-2026-10-23.2) from the append-only file in this folder. Dollars a trade after costs (1×; 2× beside). **No verdict before N**; at N the verdict uses exactly the first N and is written once (`verdicts.json`). SPY and QQQ are read separately. (H9 was withdrawn from the forward job by the owner on 2026-10-23, before any forward datum was read.)

| test | name | counted / N | mean $ a trade 1× | 2× | 95 % block-20 interval | verdict |
|---|---|---|---|---|---|---|
| H7 | SPY | 0 / 366 | — | — | — | no verdict |
| H7 | QQQ | 0 / 483 | — | — | — | no verdict |

## H7 checkpoints (every 8 trades; descriptive)

SPY: no checkpoint yet (the first at 8 trades).
QQQ: no checkpoint yet (the first at 8 trades).

## At Robinhood fees (descriptive)

The same trades re-priced at Robinhood's fees (the research's default cost model from 2026-10-24, `docs/FEES_ROBINHOOD.md`): the $0.01 a share at the auction entry is fees and is replaced by Robinhood's (CAT only on a purchase); the $0.005 a share at the exit is half the spread and stays; the sale pays the SEC fee and the TAF, each rounded up to the cent. **The pass rule and N stay on the pre-registered costs (FORWARD_RULE_H7.md, frozen); the verdict column above is the only verdict.**

| name | trades | mean $ a trade at Robinhood fees | pre-registered 1× |
|---|---|---|---|
| SPY | 0 | — | — |
| QQQ | 0 | — | — |

H7 meetings excluded (no trade): none.
