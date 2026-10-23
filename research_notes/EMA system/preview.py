"""
preview.py — runs RULEBOOK_v0.md on the five sessions 2026-10-12 .. 2026-10-16 and writes PREVIEW_last_week.md and
out/ (the trade lists). PREVIEW — 5 sessions, no verdict.
"""
from __future__ import annotations

import csv
import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np

import ema_system as E

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(E.REPO / 'research_notes' / 'Compass phase 3' / 'backtest_audit'))
import audit_lib as AL  # noqa: E402

LBL = '**PREVIEW — 5 sessions, no verdict.**'


def money(x):
    return '—' if x is None or not np.isfinite(x) else (f'−${abs(x):,.0f}' if x < 0 else f'+${x:,.0f}')


def money2(x):
    return '—' if x is None or not np.isfinite(x) else (f'−${abs(x):,.2f}' if x < 0 else f'+${x:,.2f}')


def pct(x, d=1):
    return '—' if x is None or not np.isfinite(x) else (f'−{abs(100 * x):.{d}f}%' if x < 0 else f'+{100 * x:.{d}f}%')


def stats(T):
    n = len(T)
    if n == 0:
        return dict(n=0)
    net = np.array([t['net'] for t in T]); gross = np.array([t['gross'] for t in T])
    cost = sum(t['cost'] for t in T)
    w, l_ = net[net > 0], net[net <= 0]
    hold = np.array([t['hold'] for t in T])
    lg = [t for t in T if t['side'] > 0]; sh = [t for t in T if t['side'] < 0]
    return dict(n=n, win=float((net > 0).mean()), avg_w=float(w.mean()) if w.size else np.nan,
                avg_l=float(l_.mean()) if l_.size else np.nan, exp=float(net.mean()), exp_pct=float(net.sum() / cost),
                gross=float(gross.sum()), net=float(net.sum()), fees=float(sum(t['fees'] for t in T)),
                pf=float(w.sum() / -l_.sum()) if l_.size and l_.sum() < 0 else np.inf,
                hold=float(hold.mean()), hold_med=float(np.median(hold)),
                mfe=float(np.mean([t['mfe'] for t in T])), mae=float(np.mean([t['mae'] for t in T])),
                nl=len(lg), netl=float(sum(t['net'] for t in lg)), ns=len(sh), nets=float(sum(t['net'] for t in sh)))


def row(label, st):
    if st['n'] == 0:
        return f'| {label} | 0 |' + ' — |' * 13
    pf = '∞' if not np.isfinite(st['pf']) else f"{st['pf']:.2f}"
    return (f"| {label} | {st['n']} | {100 * st['win']:.0f}% | {money2(st['avg_w'])} / {money2(st['avg_l'])} | "
            f"{money2(st['exp'])} | {pct(st['exp_pct'])} | {money(st['gross'])} | {money(st['net'])} | {pf} | "
            f"{st['hold']:.0f} / {st['hold_med']:.0f} | {pct(st['mfe'], 0)} / {pct(st['mae'], 0)} | "
            f"{st['nl']} {money(st['netl'])} | {st['ns']} {money(st['nets'])} |")


HEAD = ('| | trades | win | avg win / avg loss | expectancy $ | expectancy % | gross | net | PF | hold avg / med (min) | '
        'MFE / MAE (option) | long (calls) | short (puts) |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|')


def spread_cost(t):
    """half-spreads paid: (ask − mid) at entry and (mid − bid) at each exit, $ (CALCULATED)"""
    K, bid, ask = E.S.chain(t['name'], t['day'])
    i, r = int(np.where(K == t['K'])[0][0]), 0 if t['right'] == 'C' else 1
    c = t['qty'] * (t['ask'] - t['bid_in']) / 2 * 100
    for q, ex, px, _ in t['legs']:
        a, b = ask[ex, i, r], bid[ex, i, r]
        if np.isfinite(a) and np.isfinite(b) and a > b:
            c += q * (a - b) / 2 * 100
    return c


def main():
    L = []
    P = L.append
    full = {}
    skips = {}
    for cfg in 'AB':
        for x in E.EXITS:
            full[(cfg, x)], skips[(cfg, x)] = E.run(cfg, x)
    base = {}
    for cfg in 'AB':
        for sig in ('cross', 'align'):
            base[(cfg, sig)] = E.run(cfg, 'X2', sig)
    rnd = {cfg: E.random_baseline(full[(cfg, 'X2')], cfg) for cfg in 'AB'}

    # trade lists
    keys = ['cfg', 'exit', 'name', 'day', 'entry', 'm', 'side', 'right', 'K', 'ask', 'bid_in', 'spread', 'delta', 'oi', 'pvol',
            'qty', 'entry_u', 'level', 'R', 'exit_m', 'hold', 'reason', 'exit_u', 'gross', 'fees', 'net', 'cost', 'mfe', 'mae',
            'move_bp', 'move_R', 'ctx200', 'struct', 'legs']
    with open(OUT / 'trades_full.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(keys)
        for k in sorted(full):
            for t in full[k]:
                w.writerow([t[c] if c != 'legs' else ';'.join(f'{q}@{E.S.mtxt(ex)}:{px:.2f}:{why}' for q, ex, px, why in t['legs'])
                            for c in keys])

    lib = {p: hashlib.sha256((HERE / p).read_bytes()).hexdigest()[:16] for p in ('ema_system.py', 'preview.py',
                                                                                  'test_ema_system.py', 'verify_plain.py')
           if (HERE / p).exists()}
    rb = subprocess.run(['git', 'log', '-1', '--format=%h', '--', 'RULEBOOK_v0.md'], cwd=HERE, capture_output=True,
                        text=True).stdout.strip()

    P('# EMA system — PREVIEW on last week (2026-10-12 → 2026-10-16)\n')
    P(f'{LBL} Five full sessions (Mon–Fri), run exactly as written in RULEBOOK_v0.md (commit {rb}), on the owner\'s request '
      '"test just on last weeks data so i can see the results fast". Five sessions cannot separate a rule from luck: '
      'one large SPXW move can make a whole row. Nothing here is a finding, and nothing is selected from it.\n')
    P('Labels: **OBSERVED** = read off the data (the bars, the NBBO, open interest, volume); **CALCULATED** = arithmetic '
      'of observed (P&L, fees, R, bp); **MODELED** = the Black-Scholes delta used to choose the contract. All P&L is '
      'CALCULATED from OBSERVED quotes: bought at the ask, sold at the bid, fees each way.\n')
    P('Earlier results to keep in mind: every pre-registered 0DTE long-option rule run on this data has lost after costs '
      '(the Compass scanner study stopped at its signal gate, 9e3888e; the EMA ladder preview lost in all 13 versions, '
      'cb79c23; the "nearest EMA targets" preview lost in both versions and both months, e9d13c0). This same week was '
      'already read by the forward paper-tracker replays of other rules (research_notes/Compass phase 3/'
      'forward_2026-10-12_2026-10-21), so it is neither fresh nor held out.\n')
    P(f'Code: `ema_system.py` (engine), `preview.py` (this report), `test_ema_system.py`, `verify_plain.py`; sha256 (16): '
      + ', '.join(f'`{k}` {v}' for k, v in lib.items()) + '. Trade list: `out/trades_full.csv`.\n')

    # 0. read this first
    fA, fB = stats(full[('A', 'X2')]), stats(full[('B', 'X2')])
    puts = np.mean([t['side'] < 0 for k in full for t in full[k]])
    big = {cfg: max(full[(cfg, 'X2')], key=lambda t: t['net']) for cfg in 'AB'}
    wk = {}
    for nm, src in (('SPY', 'SPY'), ('QQQ', 'QQQ'), ('IWM', 'IWM'), ('SPX', 'SPXW')):
        a = E.raw_bars(src, '2026-10-09')[3]; b = E.raw_bars(src, '2026-10-16')[3]
        wk[nm] = b[np.isfinite(b)][-1] / a[np.isfinite(a)][-1] - 1
    P('## 0. Read this first\n')
    P(LBL + '\n')
    P(f"- **The week fell**: from the 2026-10-09 close to the 2026-10-16 close SPX {pct(wk['SPX'], 2)}, SPY {pct(wk['SPY'], 2)}, "
      f"QQQ {pct(wk['QQQ'], 2)}, IWM {pct(wk['IWM'], 2)} (OBSERVED). The 15-minute bias put most signals on the put side: "
      f"{100 * puts:.0f}% of all full-strategy trades are puts. A rule that buys puts in a falling week shows a profit for that reason alone.")
    P(f"- **Every row of the full strategy is net positive this week** (X2: Config A {fA['n']} trades, {money(fA['net'])}, "
      f"{money2(fA['exp'])} a trade, {pct(fA['exp_pct'])} of premium; Config B {fB['n']}, {money(fB['net'])}, {money2(fB['exp'])}, "
      f"{pct(fB['exp_pct'])}); IWM is the exception, negative in most rows.")
    rA, rB = rnd['A'], rnd['B']
    P(f"- **The random baseline is positive too**: the same count per name, the same minutes and the same put share, entered at random, "
      f"made {money2(np.nanmean(rA['per']))} a trade on average (Config A's draws; band 5–95% {money2(np.nanpercentile(rA['per'], 5))} to "
      f"{money2(np.nanpercentile(rA['per'], 95))}). The full strategy's total sits at the {100 * float((rA['total'] < fA['net']).mean()):.0f}th "
      f"(A) and {100 * float((rB['total'] < fB['net']).mean()):.0f}th (B) percentile of the random trials — inside the band, not beyond it.")
    P(f"- **One trade moves a row**: the largest X2 trade is {big['A']['name']} {big['A']['day']} {big['A']['entry']} "
      f"{money(big['A']['net'])} (A) — {100 * big['A']['net'] / fA['net']:.0f}% of A's X2 total. The session bootstrap intervals "
      "(§4) all include zero.")
    P("- **The filters did beat the plain baselines this week**: (a) the 1m crossover and (b) alignment alone made less or lost (§5). "
      "One week of one direction cannot say whether that holds.")
    P("- **Costs were small here** (0DTE near-the-money, |delta| ≈ 0.45, spreads ≈ 1–2% of mid): fees ≈ 0.5–0.6% and half-spreads "
      "≈ 1.5–2% of premium (§7). The EMA ladder previews traded far more (≈2,800 trades in a month) and their best-R/R pick sat far out of the money (median |delta| 0.18); their ATM version still lost (−3.61%), cb79c23.")
    P("- Against the record: every pre-registered 0DTE long-option rule on this data lost after costs over months and years. "
      "Five positive sessions in a trending week do not move that; they make the rule worth writing down, not trading.\n")

    # 1. headline
    P('## 1. The full strategy, all four names together\n')
    P(LBL + ' 1 contract (X4: 10). Expectancy % = net ÷ premium paid. MFE / MAE = the best / worst bid during the hold '
      'against the entry ask (mean over trades). Hold in minutes.\n')
    P(HEAD)
    for cfg in 'AB':
        for x in E.EXITS:
            P(row(f'Config {cfg} · {x}', stats(full[(cfg, x)])))
    P('')
    P('Without SPXW (SPY, QQQ, IWM only — SPXW premiums are ~10× an ETF\'s, so its dollars dominate):\n')
    P(HEAD)
    for cfg in 'AB':
        for x in E.EXITS:
            P(row(f'Config {cfg} · {x}', stats([t for t in full[(cfg, x)] if t['name'] != 'SPXW'])))
    P('')

    # 2. per instrument
    P('## 2. By instrument\n')
    P(LBL + ' SPXW: signals on SPX prints, RVOL condition dropped (no volume), VWAP is the time-weighted stand-in.\n')
    for cfg in 'AB':
        P(f'### Config {cfg}\n')
        P(HEAD)
        for x in E.EXITS:
            for nm in E.NAMES:
                lab = f'{x} · {nm}' + (' (no RVOL)' if nm == 'SPXW' else '')
                P(row(lab, stats([t for t in full[(cfg, x)] if t['name'] == nm])))
        P('')

    # 3. no trades
    P('## 3. Signals without a trade, by reason\n')
    P(LBL + ' A minute whose rule held while no position was open but no contract passed §4 (each such minute counted). '
      'Identical across exit variants unless the timing of earlier trades differs.\n')
    P('| config · exit | ' + ' | '.join(E.NAMES) + ' |\n|---|' + '---|' * len(E.NAMES))
    for cfg in 'AB':
        for x in E.EXITS:
            k = skips[(cfg, x)]
            cells = []
            for nm in E.NAMES:
                c = {a: b for (n2, a), b in k.items() if n2 == nm}
                cells.append(', '.join(f'{a}: {b}' for a, b in sorted(c.items())) or '0')
            P(f'| {cfg} · {x} | ' + ' | '.join(cells) + ' |')
    P('')

    # 4. exits and by hour, by day
    P('## 4. How trades ended, by hour of entry, by day\n')
    P(LBL + '\n')
    P('| config · exit | stop | +1R | +2R | runner | flat 15:58 |\n|---|---|---|---|---|---|')
    for cfg in 'AB':
        for x in E.EXITS:
            T = full[(cfg, x)]
            cnt = {r: sum(1 for t in T if t['reason'] == r) for r in ('stop', '+1R', '+2R', 'runner', 'flat')}
            P(f'| {cfg} · {x} | ' + ' | '.join(str(cnt[r]) for r in ('stop', '+1R', '+2R', 'runner', 'flat')) + ' |')
    P('\nBy hour of entry (trades · net $):\n')
    hrs = list(range(9, 16))
    P('| config · exit | ' + ' | '.join(f'{h}:xx' for h in hrs) + ' |\n|---|' + '---|' * len(hrs))
    for cfg in 'AB':
        for x in E.EXITS:
            T = full[(cfg, x)]
            cells = []
            for h in hrs:
                tt = [t for t in T if (570 + t['m']) // 60 == h]
                cells.append(f"{len(tt)} · {money(sum(t['net'] for t in tt))}" if tt else '0')
            P(f'| {cfg} · {x} | ' + ' | '.join(cells) + ' |')
    P('\nBy session (trades · net $):\n')
    P('| config · exit | ' + ' | '.join(E.DAYS) + ' |\n|---|' + '---|' * len(E.DAYS))
    for cfg in 'AB':
        for x in E.EXITS:
            T = full[(cfg, x)]
            cells = []
            for d in E.DAYS:
                tt = [t for t in T if t['day'] == d]
                cells.append(f"{len(tt)} · {money(sum(t['net'] for t in tt))}")
            P(f'| {cfg} · {x} | ' + ' | '.join(cells) + ' |')
    P('')
    P('Session bootstrap (iid over the 5 sessions, audit_lib.session_stats, 2,000 draws) of net per trade — printed to '
      'show how wide five sessions are, not as an interval anyone should lean on:\n')
    P('| config · exit | net per trade | 95% (sessions) | without SPXW | 95% |\n|---|---|---|---|---|')
    for cfg in 'AB':
        for x in E.EXITS:
            out = []
            for flt in (lambda t: True, lambda t: t['name'] != 'SPXW'):
                T = [t for t in full[(cfg, x)] if flt(t)]
                Sx = np.array([sum(t['net'] for t in T if t['day'] == d) for d in E.DAYS])
                Nx = np.array([sum(1 for t in T if t['day'] == d) for d in E.DAYS], float)
                st = AL.session_stats(Sx, Nx, blocks=(1,))
                lo, hi = st.get('ci_trade_b1', (np.nan, np.nan))
                out += [money2(st.get('mean_trade', np.nan)), f'[{money2(lo)}, {money2(hi)}]']
            P(f'| {cfg} · {x} | ' + ' | '.join(out) + ' |')
    P('')

    # 5. baselines
    P('## 5. Baselines (X2 exit, same contract rule, same stop definition)\n')
    P(LBL + ' (a) and (b) under the same risk rules; (c) RANDOM: 500 seeded trials, the full strategy\'s X2 count per name, '
      'minutes drawn from its entry minutes, its call share.\n')
    P(HEAD)
    for cfg in 'AB':
        P(row(f'Config {cfg} · FULL strategy · X2', stats(full[(cfg, 'X2')])))
        P(row(f'Config {cfg} · (a) crossover', stats(base[(cfg, 'cross')][0])))
        P(row(f'Config {cfg} · (b) alignment only', stats(base[(cfg, 'align')][0])))
    P('')
    P('| (c) RANDOM | trades a trial | call share | net per trade: mean [5%, 95%] | total net: mean [5%, 95%] | win: mean | '
      'full strategy X2: per trade / total | full\'s percentile among the trials (total) |\n|---|---|---|---|---|---|---|---|')
    for cfg in 'AB':
        r = rnd[cfg]
        fs = stats(full[(cfg, 'X2')])
        q = float((r['total'] < fs['net']).mean())
        P(f"| Config {cfg} | {r['n']} | {100 * r['callp']:.0f}% | {money2(np.nanmean(r['per']))} "
          f"[{money2(np.nanpercentile(r['per'], 5))}, {money2(np.nanpercentile(r['per'], 95))}] | "
          f"{money(r['total'].mean())} [{money(np.percentile(r['total'], 5))}, {money(np.percentile(r['total'], 95))}] | "
          f"{100 * np.nanmean(r['win']):.0f}% | {money2(fs['exp'])} / {money(fs['net'])} | {100 * q:.0f}th |")
    P('')
    P('Baselines without SPXW:\n')
    P(HEAD)
    for cfg in 'AB':
        for lab, T in ((f'Config {cfg} · FULL · X2', full[(cfg, 'X2')]), (f'Config {cfg} · (a) crossover', base[(cfg, 'cross')][0]),
                       (f'Config {cfg} · (b) alignment only', base[(cfg, 'align')][0])):
            P(row(lab, stats([t for t in T if t['name'] != 'SPXW'])))
    P('')

    # 6. stock-only
    P('## 6. Stock-only study: the underlying\'s move, entry → exit\n')
    P(LBL + ' CALCULATED: the signed move of the underlying (SPX for SPXW) from C[s] at entry to the close of the exit '
      'bar (X4: the quantity-weighted exit), in bp and in R. Signal quality apart from the option\'s spread, decay and fees.\n')
    P('| config · exit | trades | mean bp | median bp | mean R | median R | share > 0 | SPXW mean bp | SPY | QQQ | IWM |\n'
      '|---|---|---|---|---|---|---|---|---|---|---|')
    for cfg in 'AB':
        for x in E.EXITS:
            T = full[(cfg, x)]
            bp = np.array([t['move_bp'] for t in T]); rr = np.array([t['move_R'] for t in T])
            per = [np.mean([t['move_bp'] for t in T if t['name'] == nm]) if any(t['name'] == nm for t in T) else np.nan
                   for nm in E.NAMES]
            P(f'| {cfg} · {x} | {len(T)} | {bp.mean():+.1f} | {np.median(bp):+.1f} | {rr.mean():+.2f} | {np.median(rr):+.2f} | '
              f'{100 * (bp > 0).mean():.0f}% | ' + ' | '.join(f'{v:+.1f}' if np.isfinite(v) else '—' for v in per) + ' |')
    P('\nThe same for the baselines (X2):\n')
    P('| baseline | trades | mean bp | median bp | mean R | share > 0 |\n|---|---|---|---|---|---|')
    for cfg in 'AB':
        for sig, lab in (('cross', '(a) crossover'), ('align', '(b) alignment only')):
            T = base[(cfg, sig)][0]
            bp = np.array([t['move_bp'] for t in T]); rr = np.array([t['move_R'] for t in T])
            P(f'| Config {cfg} · {lab} | {len(T)} | {bp.mean():+.1f} | {np.median(bp):+.1f} | {rr.mean():+.2f} | '
              f'{100 * (bp > 0).mean():.0f}% |')
    P('')

    # 7. costs
    P('## 7. Costs\n')
    P(LBL + ' CALCULATED. Fees at the rulebook\'s rates; the half-spreads are what the ask-in / bid-out fills paid over the '
      'mid (exit half-spread read on the exit row; a missing exit quote counts 0).\n')
    P('| config · exit | gross | fees | half-spreads paid | net | fees ÷ premium | half-spreads ÷ premium | gross mid-to-mid (gross + half-spreads) |\n'
      '|---|---|---|---|---|---|---|---|')
    for cfg in 'AB':
        for x in E.EXITS:
            T = full[(cfg, x)]
            g = sum(t['gross'] for t in T); f_ = sum(t['fees'] for t in T); c = sum(t['cost'] for t in T)
            sp = sum(spread_cost(t) for t in T)
            P(f'| {cfg} · {x} | {money(g)} | {money(-f_)} | {money(-sp)} | {money(g - f_)} | {pct(f_ / c, 2)} | {pct(sp / c, 2)} | '
              f'{money(g + sp)} |')
    P('')

    # 8. context
    P('## 8. Context columns (reported, not required in v0)\n')
    P(LBL + ' Full strategy, X2. "With" = the 15m close on the trade\'s side of EMA200(15m) / the last two confirmed '
      '5-bar swings (2 each side, known 2 bars later) rising for calls, falling for puts.\n')
    P('| config | 200 EMA with: n · net | against: n · net | structure with: n · net | not: n · net |\n|---|---|---|---|---|')
    for cfg in 'AB':
        T = full[(cfg, 'X2')]
        a = [t for t in T if t['ctx200'] == t['side']]; b = [t for t in T if t['ctx200'] != t['side']]
        c = [t for t in T if t['struct'] == t['side']]; d = [t for t in T if t['struct'] != t['side']]
        P(f'| {cfg} | ' + ' | '.join(f"{len(z)} · {money(sum(t['net'] for t in z))}" for z in (a, b, c, d)) + ' |')
    P('')

    # 9. A vs B
    P('## 9. Config A against Config B\n')
    P(LBL + ' Trades shared = the same name, session, entry minute and side.\n')
    P('| exit | A trades | B trades | shared | A net | B net | A − B net |\n|---|---|---|---|---|---|---|')
    for x in E.EXITS:
        A, B = full[('A', x)], full[('B', x)]
        ka = {(t['name'], t['day'], t['m'], t['side']) for t in A}
        kb = {(t['name'], t['day'], t['m'], t['side']) for t in B}
        na, nb = sum(t['net'] for t in A), sum(t['net'] for t in B)
        P(f'| {x} | {len(A)} | {len(B)} | {len(ka & kb)} | {money(na)} | {money(nb)} | {money(na - nb)} |')
    P('')
    P('## 11. What a full program would need\n')
    P('- **Data ranges**: the 0DTE 1-minute chains on disk (SPY, QQQ, SPXW, IWM) and the underlying bars back to 2017 (SPX prints too); '
      'open interest from UW\'s dated chain only from 2023-11-21 (before it the OI ≥ 250 filter cannot be applied — run it as a '
      'stated variant without OI there); previous-session volume from ThetaData EOD. Non-0DTE 1-minute quotes are not on disk: '
      'any 1–7 DTE version of the spec needs them fetched first.')
    P('- **Splits, fixed before a result**: a development (Pick) span, a check span and a held-out span drawn once by month '
      '(as the scanner study did, scanner_lib HELD_M), with this week and every week the forward trackers already read marked '
      'as seen. Every v0 choice above (EMA warm-up, SPX bars and VWAP stand-in, targets on closes, the "crossed EMA50" reading, '
      'the delta band and pick, the 12% spread cap, the cooldown) becomes a named variant tested on Pick only, the winner fixed '
      'and committed before Check and the holdout are read once.')
    P('- **Regimes**: up, down and flat weeks, high- and low-VIX months, FOMC/CPI days, and the call side alone (this week had '
      'almost no calls). Gate on the random baseline (same minutes, same side mix) per regime, not on the raw P&L.')
    P('- **Statistics**: a session-block bootstrap with at least ~250 sessions per name, Bonferroni over the configs × exits '
      'chosen from, and a forward paper run after the holdout before any money.')
    P('- **Caveats of this preview**: the EMA warm-up read the 60 sessions from 2026-07-17, which include 2026-08, a month the '
      'scanner study holds out — only the underlying bars were read there, for EMA warm-up, no option or outcome; SPX bars are '
      'one print a minute (high = low = close), so its pullback and stop read closes only; X4 is 10 contracts, so its dollars '
      'are ~10× the others.\n')
    return L, full


if __name__ == '__main__':
    L, full = main()
    ver = HERE / 'out' / 'verify_summary.md'
    if ver.exists():
        L.append(ver.read_text())
    tst = HERE / 'out' / 'tests.txt'
    if tst.exists():
        L.append('Unit tests (`python3 test_ema_system.py`): ' + tst.read_text().strip() + ' — EMA, Wilder RSI against an independent loop, VWAP (and SPX\'s time-weighted stand-in), ROC across the session edge, the 5m/15m candle completion, RVOL, the swing confirmation two bars late, the fees; no-lookahead = every decision at m identical when every bar after m − 1 is perturbed.\n')
    (HERE / 'PREVIEW_last_week.md').write_text('\n'.join(L) + '\n')
    print('written', len(L), 'lines')
