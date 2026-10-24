"""analyze_final.py — Compass Final: every test's statistics and verdict (PREREG_COMPASS_FINAL.md 6-9) from the trade files
the run scripts wrote (out/t123_trades.parquet, t4_trades.parquet, t56_trades.parquet, t7_trades.parquet). Writes
out/results.json, out/tables.md (the report's tables) and charts/*.png. Reads no market data itself.

    POLARS_MAX_THREADS=2 python3 -I analyze_final.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from statistics import NormalDist

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib_final as LF  # noqa: E402

import os
OUT = Path(os.environ.get('CF_OUTDIR', str(HERE / 'out')))   # CF_OUTDIR: the dry test on previously read data
CH = OUT.parent / 'charts' if os.environ.get('CF_OUTDIR') else HERE / 'charts'
CH.mkdir(exist_ok=True)
MDE0 = json.loads((HERE / 'out' / 'mde_prereg.json').read_text())

TESTS = {
    'T1 fly5_iron': dict(fam='fly5', unit='% of max risk', settle='case (b)'),
    'T2 condor_em1': dict(fam='condor_em1', unit='% of max risk', settle='case (b)'),
    'T3 condor_d20': dict(fam='condor_d20', unit='% of max risk', settle='case (b)'),
    'T4 touch_d25': dict(fam='touch_d25', unit='% of max risk', settle='case (b)'),
    'T5 h13_te': dict(fam='h13_te', unit='% of credit', settle='Cboe close (cash)'),
    'T6 h15_s2': dict(fam='h15_s2', unit='% of credit', settle='Cboe close (cash)'),
    'T7 h1_qqq': dict(fam=None, unit='% of notional', settle='stock, next 09:30 open'),
}


def sess_rows(fam: str) -> list[dict]:
    return [r for r in csv.DictReader(open(HERE / f'sessions_{fam}.csv')) if r['excluded_by'] == '']


def sessions_of(fam: str) -> list[str]:
    return sorted({r['session'] for r in sess_rows(fam)})


def frames() -> dict:
    """test -> (trade frame with date, entry, inst, cost, pnl, pnl_old and line_* columns, sessions, notes)"""
    F = {}
    t = pl.read_parquet(OUT / 't123_trades.parquet')
    for key, cand in (('T1 fly5_iron', 'fly5'), ('T2 condor_em1', 'condor_em1'), ('T3 condor_d20', 'condor_d20')):
        x = t.filter(pl.col('candidate') == cand)
        allx = x
        if cand == 'fly5':
            x = x.filter(pl.col('structure') == 'iron')
        F[key] = (x, sessions_of(TESTS[key]['fam']), allx)
    F['T4 touch_d25'] = (pl.read_parquet(OUT / 't4_trades.parquet'), sessions_of('touch_d25'), None)
    s = pl.read_parquet(OUT / 't56_trades.parquet')
    F['T5 h13_te'] = (s.filter(pl.col('test') == 'h13_te'), sessions_of('h13_te'), None)
    F['T6 h15_s2'] = (s.filter(pl.col('test') == 'h15_s2'), sessions_of('h15_s2'), None)
    h = pl.read_parquet(OUT / 't7_trades.parquet')
    h1s = pl.read_parquet(OUT / 't7_sessions.parquet')
    F['T7 h1_qqq'] = (h, sorted(h1s['day'].to_list()), None)
    return F


def primary(key: str, x: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """the judged frame (pnl = Robinhood under the primary settlement) and what was left out"""
    note = {}
    if TESTS[key]['settle'] == 'case (b)':
        n0 = x.height
        miss = x.filter(pl.col('pnl_b').is_null())
        note = {'trades_before_universe_B': n0, 'left_out_no_decision_price_or_open_or_close': miss.height,
                'name_sessions_without_D': miss.filter(pl.col('decision_px').is_null()).select('name', 'date').unique().height,
                'name_sessions_without_O': miss.filter(pl.col('next_open_0930').is_null()).select('name', 'date').unique().height,
                'name_sessions_without_C': miss.filter(pl.col('official').is_null()).select('name', 'date').unique().height,
                'name_sessions_total': x.select('name', 'date').unique().height}
        note['decision_price_coverage'] = 1 - note['name_sessions_without_D'] / max(1, note['name_sessions_total'])
        x = x.filter(pl.col('pnl_b').is_not_null()).with_columns(pl.col('pnl_b').alias('pnl'), pl.col('pnl_b_old').alias('pnl_old'))
    return x, note


def lines(key: str, x: pl.DataFrame, sess: list[str]) -> dict:
    out = {}
    if TESTS[key]['settle'] == 'case (b)':
        for nm, col in (('(0) intrinsic at the official close [carries the exercise risk it does not price]', 'pnl_0'),
                        ('(a) exercise by exception on C', 'pnl_a'), ('(c) both sides decided at D', 'pnl_c')):
            out[nm] = LF.mean_line(x, sess, col)
        if 'pnl_1558' in x.columns:
            out["the tracker's 15:58 exit (NBBO, Robinhood both sides)"] = LF.mean_line(x, sess, 'pnl_1558')
        if 'pnl_0_old' in x.columns and key != 'T4 touch_d25':
            out["the study's own convention: (0) at the official close, $0.65 a leg"] = LF.mean_line(x, sess, 'pnl_0_old')
        if key == 'T4 touch_d25':
            out["the study's own convention: the 16:00 bar's close, $0.65 a leg"] = LF.mean_line(x, sess, 'pnl_study_own')
    out["primary settlement at the study's own fees"] = LF.mean_line(x, sess, 'pnl_old')
    return out


def walk_chart(key: str, x: pl.DataFrame, fname: str) -> None:
    y = x.sort(['date', 'entry', 'inst'])
    cum = y['pnl'].cum_sum().to_list()
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.2))
    ax[0].plot(range(len(cum)), cum, lw=1.1, color='#2b5c8a')
    ax[0].axhline(0, color='#888', lw=0.6)
    ax[0].set_title(f'{key}: cumulative $ P&L, 1 lot (Robinhood fees, primary settlement)', fontsize=8)
    ax[0].set_xlabel('trade number (entry order)', fontsize=7); ax[0].tick_params(labelsize=7)
    bal, b = 1000.0, []
    for d, g in y.group_by('date', maintain_order=True):
        r = (g['pnl'] / g['cost']).to_numpy()
        bal = max(0.0, bal * (1 + min(0.10, 1.0 / len(r)) * r.sum()))
        b.append(bal)
    ax[1].plot(range(len(b)), b, lw=1.1, color='#8a4b2b', label='10% per trade')
    ax[1].plot(range(len(cum)), [1000 + c for c in cum], lw=0.9, color='#2b5c8a', alpha=0.6, label='fixed 1 lot (x: trades)')
    ax[1].axhline(1000, color='#888', lw=0.6)
    ax[1].set_title('$1,000: 10% per trade (x: sessions) and a fixed 1 lot', fontsize=8)
    ax[1].legend(fontsize=6); ax[1].tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(CH / fname, dpi=110)
    plt.close(fig)


def main() -> None:
    F = frames()
    res = {}
    z = NormalDist().inv_cdf(0.95) + NormalDist().inv_cdf(0.80)
    flags = {r['session']: r for fam in ('fly5', 'condor_em1', 'h13_te') for r in sess_rows(fam)}
    for key, (x0, sess, allx) in F.items():
        x, note = primary(key, x0)
        stray = set(x['date'].to_list()) - set(sess)
        assert not stray or os.environ.get('CF_OUTDIR'), f'{key}: trades on sessions outside the test: {sorted(stray)[:5]}'
        d = LF.describe(x, sess, TESTS[key]['unit'])
        v = LF.verdict(d)
        if TESTS[key]['settle'] == 'case (b)' and note['decision_price_coverage'] < 0.5:
            v['pass'] = False
            v['not_judged'] = 'the decision price covers fewer than 50 % of the sessions'
        pct = (x['pnl'] / x['cost'] * 100)
        sess_mean = x.with_columns((pl.col('pnl') / pl.col('cost') * 100).alias('p')).group_by('date').agg(pl.col('p').mean())['p']
        prev = MDE0['tests'][{'T1 fly5_iron': 'fly5_iron', 'T2 condor_em1': 'condor_em1', 'T3 condor_d20': 'condor_d20', 'T4 touch_d25': 'touch_d25',
                              'T5 h13_te': 'h13_te', 'T6 h15_s2': 'h15_s2', 'T7 h1_qqq': 'h1_qqq'}[key]]
        r = {'unit': TESTS[key]['unit'], 'settlement': TESTS[key]['settle'], 'describe': d, 'verdict': v, 'universe': note,
             'lines': lines(key, x, sess),
             'mde_prereg_sd_at_realised_n': LF.mde(prev['sd_trade'], x.height, prev['sd_session'], d['sessions_traded']),
             'mde_realised_sd': LF.mde(float(pct.std()) if x.height > 1 else float('nan'), x.height,
                                        float(sess_mean.std()) if sess_mean.len() > 1 else float('nan'), d['sessions_traded']),
             'sd_trade_realised': float(pct.std()) if x.height > 1 else float('nan')}
        m, sd = d['mean_pct'], r['sd_trade_realised']
        r['forward_n_80'] = math.ceil((z * sd / m) ** 2) if (m and m > 0 and sd == sd) else None
        # sensitivity lines
        if key != 'T7 h1_qqq':
            cc = {s for s, row in flags.items() if row.get('compass_close_pnl_sample') == 'true'}
            xs = x.filter(~pl.col('date').is_in(sorted(cc)))
            ss = [s for s in sess if s not in cc]
            r['sensitivity'] = {"Compass Close's P&L-sample sessions out": LF.mean_line(xs, ss, 'pnl') if xs.height else {'trades': 0},
                                'EOD-marked sessions out': {'trades': 0, 'note': 'every in-test session carries an EOD mark (stage 1): n = 0'}}
            if 'official' in x.columns and 'close_1559' in x.columns:
                fl = x.filter((pl.col('official') - pl.col('close_1559')).abs() > 0.25)
                r['sensitivity']['sessions with |official - 15:59 bar| > $0.25 out'] = LF.mean_line(
                    x.filter(~pl.col('date').is_in(fl['date'].unique().to_list())), sess, 'pnl')
                r['flagged_close_sessions'] = sorted(set(fl['date'].to_list()))
        if allx is not None and key == 'T1 fly5_iron':
            r['reported_structures'] = {}
            for stc in ('call', 'put'):
                y, _ = primary(key, allx.filter(pl.col('structure') == stc))
                r['reported_structures'][f'fly5 {stc} (case (b), Robinhood)'] = LF.mean_line(y, sess, 'pnl')
            r['by_name'] = {nm: LF.mean_line(x.filter(pl.col('name') == nm), sorted(set(x.filter(pl.col('name') == nm)['date'].to_list())), 'pnl')
                            for nm in ('SPY', 'QQQ')}
        res[key] = r
        walk_chart(key, x, f"{key.split()[0].lower()}.png")
    (OUT / 'results.json').write_text(json.dumps(res, indent=1, default=str))
    for k, r in res.items():
        d = r['describe']
        print(f"{k}: trades {d['trades']}, mean {d['mean_pct']:+.2f} {r['unit']} 95% [{d['ci95'][0]:+.2f}, {d['ci95'][1]:+.2f}] "
              f"Bonf [{d['ci_bonf'][0]:+.2f}, {d['ci_bonf'][1]:+.2f}] win {d['win_rate']:.3f} -> {'PASS' if r['verdict']['pass'] else 'FAIL'} {r['verdict']['conditions']}")


if __name__ == '__main__':
    main()
