#!/usr/bin/env python3
"""
power_h7_h8.py — the a-priori power figures of PREREG_H7.md and PREREG_H8.md (run before either prereg was committed).

    PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=1 python3 -I -B power_h7_h8.py

Sign-free only: the root-mean-square of the close-to-close return of EVERY session on disk (official close to official
close; ThetaData EOD before 2025-10-13, Unusual Whales' daily bar from it), per name — no mean of anything, no FOMC or
turn-of-month cut. These sessions include the FOMC and turn-of-month sessions (about 3 % and 20 % of them), so the figure is
the window's typical size, not its effect. Prints the standard error and the minimum detectable effect (80 % power, 5 %
two-sided, iid trades) of a 100-share trade for each rule's trade count, at the 2026-10-22 official close.
"""
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('run_h4', HERE.parent / 'H4' / 'run_h4.py')
R4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R4)

FIRST = {'SPY': '2017-01-03', 'QQQ': '2012-06-01'}
TRADES = {'H7': {'SPY': 77, 'QQQ': 108}, 'H8': {'SPY': 117, 'QQQ': 172}}
WINDOW_SESSIONS = {'H7': 1.0, 'H8': 4.0}     # H7: close -> 13:58 next session, taken as one session's variance (an upper figure)


def main():
    cal = R4.calendar()
    TE, UW = R4.theta_eod(), R4.uw_closes()

    def off(nm, d):
        return (TE if d < '2025-10-13' else UW).get((nm, d))
    out = {}
    for nm in ('SPY', 'QQQ'):
        ds = [d for d in cal if FIRST[nm] <= d <= '2026-10-22']
        sq, n = 0.0, 0
        for a, b in zip(ds, ds[1:]):
            ca, cb = off(nm, a), off(nm, b)
            if ca and cb:
                sq += (cb / ca - 1) ** 2
                n += 1
        rms = math.sqrt(sq / n)
        px = off(nm, '2026-10-22')
        o = {'sessions': n, 'rms_daily_bp': 1e4 * rms, 'close_2026_10_22': px}
        for h in ('H7', 'H8'):
            sd = rms * math.sqrt(WINDOW_SESSIONS[h]) * 100 * px
            k = TRADES[h][nm]
            se = sd / math.sqrt(k)
            o[h] = {'trades': k, 'sd_trade_usd': sd, 'se_usd': se, 'mde_usd': 2.8 * se, 'mde_bp': 1e4 * 2.8 * se / (100 * px)}
        out[nm] = o
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
