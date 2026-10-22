"""
deviations.py — out/deviations.json: what the data forced, the departures the prereg itself lists, and the readings of the
prereg's text made before any result was read. Counts are read off the build outputs and the fetch's files.

  python3 -I deviations.py [expl|hold]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fcommon as C  # noqa: E402


def capped(split: str) -> dict:
    out = {}
    for route in ('flow_alerts', 'oi_chain', 'darkpool'):
        for tdir in sorted((C.UW / route).glob('*')):
            t = tdir.name
            u = 'SPXW' if t in ('SPX', 'SPXW') else t
            if split == 'expl' and u in C.HELD_T:
                continue
            n = 0
            for f in tdir.glob('*.meta.json'):
                d = f.name.split('.')[0]
                if split == 'expl' and C.held_month(d):
                    continue
                try:
                    if json.loads(f.read_text()).get('capped'):
                        n += 1
                except Exception:
                    pass
            if n:
                out[f'{route}/{t}'] = n
    return out


def staged_days(split: str) -> list[str]:
    out = []
    for kind in ('0dte',):
        for p in sorted((C.WORK / split / kind).glob('*.counts.json')):
            j = json.loads(p.read_text())
            n = j.get('counts', {}).get('day: chain read from the fetch staging', 0)
            if n:
                out.append(f"{j['name']} {n}")
    return out


def main():
    split = sys.argv[1] if len(sys.argv) > 1 else 'expl'
    C.set_split(split)
    st = json.loads((C.SP / 'features_data' / 'STATUS.json').read_text())
    spxw = st.get('theta', {}).get('notes', {}).get('spxw_eod_measure', {})
    nope = C.UW / 'nope' / '_start.json'
    nope_start = json.loads(nope.read_text()) if nope.exists() else None
    cal = C.calendar_disagreements()
    dev = dict(deviations=[], departures=[], readings=[])
    D = dev['deviations']
    caps = capped(split)
    D.append('UW pages capped by the fetch (a ticker-day whose answer reached the page cap; the rows past the cap are not on disk, '
             'so a contract or alert there is undefined): ' + (', '.join(f'{k} {v} days' for k, v in caps.items()) or 'none in this split') + '.')
    sd = staged_days(split)
    fails = C.staging_failures()
    ch = sorted(k for k in fails if '/chains_exp/' in k)
    read = [k for k in ch if C.staged_sound(C.STAGING / k)] if split == 'hold' else \
        [k for k in ch if k.split('/')[2] not in C.HELD_T and C.staged_sound(C.STAGING / k)]
    D.append(f'Single-name expiry-day chains 2026-10-12 → 21 that failed the fetch\'s verification and stayed in its staging folder '
             f'({len(ch)} files at the last pass). The complaint "N mids that are not (bid + ask) / 2" is the verifier\'s handling of '
             'NaN: polars orders NaN above every number, so each row WITHOUT a quote (NaN bid, ask and mid — the stored files\' '
             'convention) counts as a bad mid. A staged file is read only when that is its one complaint, N equals its rows with a '
             'NaN mid, every quoted row\'s mid is exactly (bid + ask) / 2 and no bid is negative or above its ask (fcommon.staged_sound); '
             'then bid and ask are read from staging. Any other complaint (one-sided strikes, under half the usual rows, INTC '
             '2026-10-19 with 1 strike) and the session is treated as not on disk (no 0DTE trade, no 1–7 exit there). '
             f'Read from staging in this split: {len(read)} file(s)' + (f" ({', '.join(k.split('/')[2] + ' ' + k.split('/')[3][:10] for k in read)})" if read else '')
             + '. All are in 2026-10, a held-out month: only the holdout reads them.')
    eod_bad = sorted(k for k in fails if '/eod_all/' in k)
    D.append('Option EOD weeks that failed the fetch\'s verification and stayed in staging are treated as not on disk: '
             + (', '.join(f"{k.split('/')[2]} {k.split('/')[3][:-8]} ({'; '.join(fails[k])})" for k in eod_bad) or 'none')
             + '. The SPXW weeks are mostly holiday weeks (the vendor answered rows dated on the exchange holiday, which the fetch\'s '
             'session check refused); they are not read. Each such week leaves its sessions without EOD for that name: no multi-day '
             'entry or EOD exit there (a trade whose exit falls there is not formed, counted), and the tier and IV-rank windows lose them '
             '(Tier U where a tier window is short; IV rank needs 200 of 252).')
    uw = st.get('uw', {}).get('datasets', {})
    D.append('UW answers logged by the fetch as empty on or after a route\'s served start ("gaps"; the value is undefined there): '
             + ', '.join(f"{k} {v.get('gaps')}" for k, v in uw.items() if v.get('gaps')) + '; gex-levels rows with every level null '
             '(stored .empty; SPY/SPX before 2024-05-13, as INVENTORY B5): ' + str(sum(1 for _ in (C.UW / 'gex_levels').glob('*/*.empty'))) + ' ticker-days.')
    D.append('A bug found on the FIRST holdout read and fixed before the read that carries the verdicts: two option-EOD inputs were '
             'not unique — SPY\'s 2015-03-30 and 03-31 sat in two weekly files (both read, so those sessions\' multi-day trades were '
             'doubled), and the next-session volumes for V3 were keyed by the last trading day rather than the listed expiry, so on a '
             'day with two expiries sharing a last trading day (2025-01-09, the market closure; 2026-10-21) the join doubled 0DTE '
             'trades. Every such day is in a held-out month, so the exploration screen was unaffected (its trade count is unchanged and '
             'no exploration row was duplicated); the holdout table had 777,571 rows for 580,274 base trades. Fixed: a trading day is '
             'read once (the first weekly file), EOD rows are unique per (date, expiration, strike, right), V3 joins on the listed '
             'expiry, and screen.py refuses a join that duplicates a base trade. The holdout was then run once more on the corrected '
             'table (out/holdout.json); the first, duplicated read is kept as out/holdout_run1_duplicated_rows.json and reported beside '
             'it. No feature, threshold or rule changed between the two reads.')
    D.append('IWM\'s 2026-10-21 same-day chain failed the fetch\'s first verification (one-sided strikes) and was merged on its second '
             'pass; it is read like any other file, a strike without a standing quote untradable by the prereg\'s rules (holdout month).')
    if spxw:
        D.append(f"SPXW option EOD: the fetch measured one week ({spxw.get('secs')} s, {spxw.get('mb')} MB; projected "
                 f"{spxw.get('projected_hours_at_1')} h, {spxw.get('projected_gb')} GB) and stored it with max_dte = 60, so SPXW is in "
                 'the 1–60 DTE buckets, V3 and V6 apply to SPXW and the VN1 pairs include 1–60 DTE. Because only expiries to 60 days '
                 'were fetched, SPXW\'s tier volume is the day\'s volume over those expiries only (not every expiry).')
    D.append('UW `nope` start: ' + (json.dumps(nope_start) if nope_start else 'see the fetch log') + '; D3 is undefined before it.')
    D.append('The calendar: the 2022 → rule against SPY\'s EOD file dates disagrees on ' + (str(len(cal)) + ' dates: ' + ', '.join(f'{a} ({b})' for a, b in cal)
                                                                                        if cal else '0 dates') + '.')
    P = dev['departures']
    P += ['The 0DTE grid keeps both named endpoints (09:45 and 15:30; the last step is 15 minutes) — prereg 2.3.',
          'V4 and V5 use the realized release dates (prereg 3.2 note), including the shutdown-moved CPI and NFP of October–December 2025.',
          'V2 reads the open_interest of the chain dated D (the count published the morning of D); the last session of the span has '
          'the chain only if the fetch stored it.',
          'D3 (NOPE) from its served start; D5 (dark pool) with the fetch\'s $1M premium floor (so 23 features are screened).']
    Rd = dev['readings']
    Rd += ['Expiries dated on a Saturday (the monthlies before 2015) or a non-trading day are read at their last trading day for the '
           'calendar DTE, T and the exits.',
           'The EOD entry is stamped 16:00 for T (so T = calendar days ÷ 365) and for every point-in-time rule; its underlying price is '
           'the 15:59 bar (SPXW: the SPX print stamped 15:59).',
           'Sessions in "the 5th / 10th session after", "the session before the expiry day", RV20 and the tier and IV-rank windows are '
           'full sessions (half days out, as prereg 2.1 defines sessions); the prior session of D7 is the previous trading day.',
           'RV20 needs 21 15:59 closes on consecutive full sessions; for a 0DTE entry it ends at the session before (point in time).',
           'The single names\' option EOD is read from 2022-11-01 for every EOD-based input (base trades, tiers, V3, V6), as the scope '
           'and section 2.7 set ("the singles before 2022-12" are Tier U), although older AAPL and FB weekly files are on disk.',
           'META before the 2022-06-09 renaming is FB in the stored chains (to 2022-06-03) and bars (to 2022-06-08); the META folder\'s '
           'ten overlapping expiry days are not read twice.',
           'The intraday no-bid fallback looks back at most 10 minutes and never before the entry minute.',
           'An expiry-day chain that is on disk but lacks the contract forms no 1–7 trade (counted).',
           'ES1/ES2 are defined at an entry when at least two of the three multi-day buckets have a value; the "without" arm is the '
           'trades of those buckets. ES4 chooses among the strike buckets whose contract has a solved IV; a tie in |delta| − 0.30 '
           'keeps the contract nearer the money (smaller |x|).',
           'VN1: two venues tie when their cost shares differ by ≤ 1e-12 (both kept).',
           'V4/V5 window: (16:00 of the trading day before the entry session, the expiry\'s 16:00), both ends open; an EOD entry on D '
           'is stamped 16:00 on D, so D−1\'s 16:00 is its last close before; a post-market report counts at 16:00 of its date.',
           'V2: UW\'s dated chain was fetched with exclude_zero_oi_chains = true, so a contract with no row (zero open interest '
           'included) is undefined, as the prereg says of a contract not found.',
           'D2 for SPXW sums the SPX- and SPXW-filed alerts; D5 counts every served print (cancelled ones included).',
           'The single names\' 0DTE V3 and V6 exist only where their 2022-11 → EOD files do.']
    C.jdump(dev, C.OUT / 'deviations.json')
    print(json.dumps(dev, indent=1)[:3000])


if __name__ == '__main__':
    main()
