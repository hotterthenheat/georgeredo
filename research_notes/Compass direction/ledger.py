#!/usr/bin/env python3
"""
ledger.py — the opened ledger's name list, the unopened population, and the seeded draws of PREREG_DIRECTION.md.

Reads ONLY metadata: the UW earnings calendar's (ticker, report_date, report_type, report_time) — never a reported or
estimated EPS, a surprise or a price —, ThetaData's list of expirations per option root, and the repository's lists of
names earlier studies used (from git history; see OPENED below and PREREG_DIRECTION.md §1). It opens no bar, quote,
return or P&L of any name. Deterministic.

    python3 -I ledger.py            → ledger.json beside this file (and prints the counts)
"""
from __future__ import annotations

import gzip
import json
import re
from pathlib import Path

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

# ---- every single name an earlier study read against an outcome BEFORE 2023 (2023 onward: every optionable name is opened) ----
# sources (PREREG_DIRECTION.md §1): the 41 names of the S05/S06/atlas/V4/V6 1-minute bar cache (2017-06 →); the lifecycle daily
# tier's 40 Tier A roots (2017-06 →, FB done); the engine audit's top 20 (daily bars 2020 →, earnings-day moves 1996 →); the
# Compass features 11 singles (0DTE 2017-06 →, EOD 2022-11 →) and V3's same 11; AAPL option EOD 2015-03 →; FB 2017-06 → 2022-06.
# Added conservatively although no outcome of theirs before 2023 was read: the step-0 inventory's 30 singles and 10 ETFs, the
# recorder's 24 names, and the union of the 2025 and 2026 Tier A lists (top 100 by dollar volume, `data_lake/universe/tiers
# .parquet` at 75c29c9^ — the S05 pull's queue).
BAR_CACHE_41 = '''AAPL ADBE AMD AMZN AVGO BAC COIN COST CRM DIA FB GLD GOOG GOOGL HYG INTC IVV JPM LLY LQD META MSFT MSTR MU NFLX
NVDA PLTR QCOM SMCI SMH SOXL SQQQ TLT TQQQ TSLA TSM UNH V VOO XLF XOM'''.split()
TOP20 = 'NVDA TSLA AAPL MU SPCX INTC AMZN TLT META EWZ PLTR AMD IBIT MSFT GOOGL MSTR HYG AVGO SOFI ORCL GME'.split()
FEATURES_11 = 'AAPL AMZN AVGO GOOGL MSFT NVDA TSLA AMD INTC MU META'.split()
INVENTORY_30 = '''NVDA TSLA AAPL MU SPCX INTC AMZN META PLTR AMD MSFT GOOGL MSTR AVGO SOFI ORCL GME IREN NFLX CRWV HOOD NBIS ASTS
MRVL SMCI MARA WULF SNDK SKHY WMT TLT EWZ IBIT HYG SLV SOXL TQQQ XLF GLD SMH'''.split()
RECORDER_24 = 'AAPL AMD AMZN AVGO EWZ GME GOOGL HYG IBIT INTC IWM META MSFT MSTR MU NVDA ORCL PLTR QQQ SOFI SPX SPY TLT TSLA'.split()
INDEX_ETF = 'SPY QQQ IWM SPX SPXW XSP NDX NDXP RUT RUTW DIA VIX VIXW'.split()
TIERS_GIT = '75c29c9^:data_lake/universe/tiers.parquet'     # removed by the Fresh start; read from git

# ---- the holdout's months, and the exploration's ------------------------------------------------------------------------------
HOLD_FROM, HOLD_TO = '2019-04-01', '2022-12-31'          # report dates; every session of a trade inside 2019-04 → 2022-12
EXPL_FROM, EXPL_TO = '2019-04-01', '2026-09-30'          # report dates; exits by 2026-10-21 (checked when trades are built)
SEED_SPLIT, SEED_ORDER_H, SEED_ORDER_X = 20261024, 20261025, 20261026
DISK_NAMES = ('AAPL', 'AMZN', 'AVGO', 'GOOGL', 'MSFT', 'NVDA', 'TSLA', 'AMD', 'INTC', 'MU', 'META')   # + FB: option EOD on disk


def opened_names() -> list[str]:
    import io, subprocess
    t = pl.read_parquet(io.BytesIO(subprocess.run(['git', '-C', str(REPO), 'show', TIERS_GIT], capture_output=True, check=True).stdout))
    tier_a = t.filter(pl.col('tier') == 'A')['symbol'].to_list()
    s = set(BAR_CACHE_41) | set(TOP20) | set(FEATURES_11) | set(INVENTORY_30) | set(RECORDER_24) | set(INDEX_ETF) | set(tier_a) | {'FB'}
    return sorted(s)


def events() -> pl.DataFrame:
    """quarterly reports with a known time (premarket / postmarket), one row per (ticker, report_date); metadata only"""
    e = pl.read_parquet(REPO / 'data_lake' / 'unusualwhales' / 'earnings.parquet',
                        columns=['ticker', 'report_type', 'report_date', 'report_time'])
    e = e.filter(pl.col('report_type') == 'quarterly').select('ticker', 'report_date', 'report_time').unique(maintain_order=False)
    # a (ticker, date) carried twice with two different times is ambiguous: dropped (counted)
    n_time = e.group_by('ticker', 'report_date').agg(pl.col('report_time').n_unique().alias('k'), pl.col('report_time').first())
    return n_time.rename({'report_time': 'report_time'}).sort('ticker', 'report_date')


def roots() -> dict[str, tuple[str, str]]:
    out = {}
    with gzip.open(REPO / 'data_lake' / 'universe' / 'expirations.jsonl.gz', 'rt') as f:
        for line in f:
            r = json.loads(line)
            out[r['root']] = (r['first'], r['last'])
    return out


def main():
    opened = set(opened_names())
    ev = events()
    amb = ev.filter(pl.col('k') > 1)
    ev = ev.filter(pl.col('k') == 1).drop('k')
    rt = roots()
    ok_sym = re.compile(r'^[A-Z]{1,5}$')

    def pop(a, b):
        w = ev.filter((pl.col('report_date') >= a) & (pl.col('report_date') <= b))
        timed = w.filter(pl.col('report_time').is_in(['premarket', 'postmarket']))
        names = sorted(t for t in timed['ticker'].unique().to_list()
                       if ok_sym.match(t) and t in rt and rt[t][0] <= b and rt[t][1] >= a)
        return w, timed, names

    wh, th, ph = pop(HOLD_FROM, HOLD_TO)
    p_unopened = [t for t in ph if t not in opened]
    # the split of the unopened names: half holdout (H), half exploration (X)
    k = len(p_unopened) // 2
    H = sorted(np.random.default_rng(SEED_SPLIT).choice(p_unopened, size=k, replace=False).tolist())
    Hs = set(H)
    X = [t for t in p_unopened if t not in Hs]
    # the events of each set, in a seeded order (the fetch walks them in this order and stops at its budget)
    th_h = th.filter(pl.col('ticker').is_in(H)).sort('ticker', 'report_date')
    wx, tx, _ = pop(EXPL_FROM, EXPL_TO)
    tx_x = tx.filter(pl.col('ticker').is_in(X)).sort('ticker', 'report_date')
    order_h = np.random.default_rng(SEED_ORDER_H).permutation(th_h.height).tolist()
    order_x = np.random.default_rng(SEED_ORDER_X).permutation(tx_x.height).tolist()
    ev_h = [dict(ticker=r[0], report_date=r[1], report_time=r[2]) for r in (th_h.row(i) for i in order_h)]
    ev_x = [dict(ticker=r[0], report_date=r[1], report_time=r[2]) for r in (tx_x.row(i) for i in order_x)]
    # the on-disk exploration names' events (their option EOD is already on disk; every one is an opened name)
    disk = ev.filter(pl.col('ticker').is_in(list(DISK_NAMES)) & pl.col('report_time').is_in(['premarket', 'postmarket'])
                     & (pl.col('report_date') >= '2015-03-01') & (pl.col('report_date') <= EXPL_TO)).sort('ticker', 'report_date')
    import hashlib
    ev_d = [dict(ticker=a, report_date=b, report_time=c) for a, b, c in disk.iter_rows()]
    blob = lambda x: json.dumps(x, separators=(',', ':')).encode()
    out = dict(
        opened_names=sorted(opened), n_opened=len(opened),
        hold_window=[HOLD_FROM, HOLD_TO], expl_window=[EXPL_FROM, EXPL_TO],
        seeds=dict(split=SEED_SPLIT, order_hold=SEED_ORDER_H, order_expl=SEED_ORDER_X),
        ambiguous_time_pairs=amb.height,
        hold_window_reports_quarterly=wh.height, hold_window_reports_timed=th.height,
        optionable_names_in_hold_window=len(ph), unopened_names=len(p_unopened),
        holdout_names=H, exploration_names=X,
        n_holdout_events=len(ev_h), n_exploration_events=len(ev_x), n_disk_events=len(ev_d),
        sha256_holdout_events=hashlib.sha256(blob(ev_h)).hexdigest(),
        sha256_exploration_events=hashlib.sha256(blob(ev_x)).hexdigest(),
        sha256_disk_events=hashlib.sha256(blob(ev_d)).hexdigest(),
    )
    (HERE / 'ledger.json').write_text(json.dumps(out, indent=1))
    with gzip.open(HERE / 'events.json.gz', 'wt') as fh:
        json.dump(dict(holdout=ev_h, exploration=ev_x, disk=ev_d), fh, separators=(',', ':'))
    print('sha256 holdout events', out['sha256_holdout_events'])
    print('sha256 exploration events', out['sha256_exploration_events'])
    print('opened names', len(opened), '| optionable names with timed reports', HOLD_FROM, '→', HOLD_TO, len(ph),
          '| unopened', len(p_unopened), '| H', len(H), 'X', len(X))
    print('holdout events (timed)', len(ev_h), '| exploration events (X names', EXPL_FROM, '→', EXPL_TO, ')', len(ev_x),
          '| on-disk events', disk.height, '| ambiguous time pairs', amb.height)


if __name__ == '__main__':
    main()
