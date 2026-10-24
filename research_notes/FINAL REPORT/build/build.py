#!/usr/bin/env python3
"""build.py — writes FINAL_RESEARCH_REPORT.md (and its charts) from the committed trade-level outputs, the scratchpad
copies named in INVENTORY.md, and the two deterministic reruns (#31, #40). Then render.py turns it into the PDF.

    POLARS_MAX_THREADS=2 python3 build.py            # every strategy
    POLARS_MAX_THREADS=2 python3 build.py 29 26      # only these sections (for checking)

Nothing is fetched; no study's file is written; no holdout that INVENTORY.md lists as unopened is read.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics as M  # noqa: E402
from base import WORK  # noqa: E402
import registry as R  # noqa: E402
import verdict_rh as VR  # noqa: E402

HERE = Path(__file__).resolve().parent
OUTDIR = HERE.parent
CHARTS = OUTDIR / 'charts'
WORK.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(exist_ok=True)

UNIT_LABEL = {'premium': '% of premium', 'risk': '% of max risk', 'stock': '% of notional ($ = per 100 sh)', 'credit': '% of the credit received', 'capital': '% of the cash set aside'}
COLORS = ['#1f4e79', '#c0504d', '#4f8f3a', '#8064a2', '#f79646', '#4bacc6', '#7f7f7f', '#9e480e']


def sep(*w) -> str:
    """a pipe-table separator whose dash counts set pandoc's relative column widths"""
    return '|' + '|'.join('-' * (3 * k) for k in w) + '|'


def f(x, d=2):
    return M.fnum(x, d)


def slices(st, df):
    """(label, inst, period, frame, span) in report order: per period, each instrument, then all instruments pooled"""
    pers = st.period_order or sorted(df['period'].unique().to_list(), key=lambda p: df.filter(pl.col('period') == p)['date'].min())
    insts = sorted(df['inst'].unique().to_list())
    out = []
    for p in pers:
        dp = df.filter(pl.col('period') == p)
        if dp.height == 0:
            continue
        span = st.period_spans.get(p)
        for i in insts:
            di = dp.filter(pl.col('inst') == i)
            if di.height:
                out.append((i, p, di, span))
        if len(insts) > 1 and st.pooled and dp['inst'].n_unique() > 1:
            out.append(('all names', p, dp, span))
    for lab, ps in getattr(st, 'combined', {}).items():
        dp = df.filter(pl.col('period').is_in(ps))
        for i in insts:
            di = dp.filter(pl.col('inst') == i)
            if di.height:
                out.append((i, lab, di, None))
        if len(insts) > 1 and st.pooled:
            out.append(('all names', lab, dp, None))
    return out


def chart(st, df, df_st=None) -> str:
    fig, ax = plt.subplots(figsize=(7.2, 2.5), dpi=110)
    insts = sorted(df['inst'].unique().to_list())
    lines = insts if len(insts) <= 8 else []
    days = sorted(df['date'].unique().to_list())
    import datetime as dt
    X = [dt.date.fromisoformat(d) for d in days]
    if lines:
        for k, i in enumerate(lines):
            s = df.filter(pl.col('inst') == i).group_by('date').agg(pl.col('pnl').sum()).sort('date')
            m = dict(zip(s['date'].to_list(), s['pnl'].to_list()))
            c, y = 0.0, []
            for d in days:
                c += m.get(d, 0.0)
                y.append(c)
            ax.plot(X, y, lw=1.1, color=COLORS[k % len(COLORS)], label=i)
    s = df.group_by('date').agg(pl.col('pnl').sum()).sort('date')
    m = dict(zip(s['date'].to_list(), s['pnl'].to_list()))
    c, y = 0.0, []
    for d in days:
        c += m.get(d, 0.0)
        y.append(c)
    if len(lines) != 1:
        ax.plot(X, y, lw=1.4, color='black', label='all names')
    if df_st is not None:
        s2 = df_st.group_by('date').agg(pl.col('pnl').sum()).sort('date')
        m2 = dict(zip(s2['date'].to_list(), s2['pnl'].to_list()))
        c2, y2 = 0.0, []
        for d in days:
            c2 += m2.get(d, 0.0)
            y2.append(c2)
        ax.plot(X, y2, lw=1.0, ls='--', color='#7f7f7f', label='all, at the study\'s fees')
    # periods: shaded alternately, labelled at the top
    pers = st.period_order or sorted(df['period'].unique().to_list(), key=lambda p: df.filter(pl.col('period') == p)['date'].min())
    shade = ['#f2f2f2', '#dfe9f5', '#fbe5d6', '#e2efda', '#ede7f6']
    for k, p in enumerate(pers):
        dp = df.filter(pl.col('period') == p)
        if dp.height == 0:
            continue
        a, b = dt.date.fromisoformat(dp['date'].min()), dt.date.fromisoformat(dp['date'].max())
        if a == b:
            b = a + dt.timedelta(days=1)
        ax.axvspan(a, b, color=shade[k % len(shade)], zorder=0)
        ax.text(a, 1.0, ' ' + p, transform=ax.get_xaxis_transform(), fontsize=6.5, va='top', ha='left', color='#333333')
    ax.axhline(0, color='#999999', lw=0.6)
    ax.set_ylabel('cumulative $ (1 lot)', fontsize=7)
    ax.tick_params(labelsize=6.5)
    ax.legend(fontsize=6, loc='lower left', ncol=min(5, max(1, len(lines) + 1)), frameon=False)
    ax.set_title(f'#{st.sid} {st.name}: cumulative P&L at Robinhood fees (dashed: the study\'s fees), periods shaded', fontsize=7.5)
    fig.tight_layout()
    p = CHARTS / f's{st.sid}.png'
    fig.savefig(p)
    plt.close(fig)
    return f'charts/{p.name}'


def tables(st, df) -> tuple[str, list]:
    rows = []
    a_lines = ['| name | period | trades | sessions (traded / span) | win % | avg win %, $ | avg loss %, $ | median %, $ | mean %, $ | 20-session block 95% (%; $) |',
               sep(6, 10, 5, 7, 4, 8, 8, 8, 8, 16)]
    b_lines = ['| name | period | biggest win ($, %, date, contract) | biggest loss ($, %, date, contract) | profit factor | max DD $ | longest DD (sessions) | top-5 days\' share of profit |',
               sep(6, 10, 22, 22, 4, 5, 5, 12)]
    for inst, per, d, span in slices(st, df):
        m = M.metrics(d, st.unit, span)
        rows.append((inst, per, m))
        p1, p2 = (3, 3) if st.unit == 'stock' else (1, 2)
        a_lines.append(f"| {inst} | {per} | {m['trades']:,} | {m['sessions_traded']:,} / {m['sessions_span']:,} | {m['win_rate']:.1f} | "
                       f"{f(m['avg_win_pct'], p1)}, {f(m['avg_win_usd'])} | {f(m['avg_loss_pct'], p1)}, {f(m['avg_loss_usd'])} | "
                       f"{f(m['median_pct'], p1)}, {f(m['median_usd'])} | **{f(m['mean_pct'], p2)}**, {f(m['mean_usd'])} | "
                       f"{M.fci(m['ci_pct'], p2)}; {M.fci(m['ci_usd'])} |")
        bw, bl = m['best'], m['worst']
        share = (f"{m['top5_share']:.0f}%" if math.isfinite(m['top5_share']) else
                 f"total ≤ 0 (best 5 days {f(m['top5_usd'], 0)}; without them {f(m['without_top5_usd'], 0)})")
        pf = '∞' if m['profit_factor'] == float('inf') else f"{m['profit_factor']:.2f}"
        b_lines.append(f"| {inst} | {per} | {f(bw[0])}, {f(bw[1], 1)}%, {bw[2]}, {bw[3]} | {f(bl[0])}, {f(bl[1], 1)}%, {bl[2]}, {bl[3]} | "
                       f"{pf} | {M.fnum(m['max_dd_usd'], 0, False)} | {m['longest_dd_sessions']:,} | {share} |")
    return '\n'.join(a_lines) + '\n\n' + '\n'.join(b_lines), rows


def year_table(df) -> str:
    out = ['| year | name | trades | win % | mean % | mean $ | total $ |', '|---|---|---|---|---|---|---|']
    insts = sorted(df['inst'].unique().to_list())
    groups = [(i, df.filter(pl.col('inst') == i)) for i in insts]
    if len(insts) > 1:
        groups.append(('all names', df))
    for i, d in groups:
        for r in M.by_year(d):
            out.append(f"| {r['year']} | {i} | {r['n']:,} | {r['win'] * 100:.1f} | {f(r['mpct'])} | {f(r['musd'])} | {f(r['tot'], 0)} |")
    return '\n'.join(out)


def reasons(st, df) -> str:
    out = []
    pers = st.period_order or sorted(df['period'].unique().to_list())
    for p in pers:
        d = df.filter(pl.col('period') == p)
        if d.height == 0:
            continue
        vc = d['reason'].fill_null('').value_counts().sort('count', descending=True)
        parts = [f"{(r['reason'] or '(none recorded)')} {r['count'] / d.height * 100:.1f}%" for r in vc.iter_rows(named=True)][:8]
        out.append(f"- {p}: " + '; '.join(parts))
    return '\n'.join(out)


def fee_block(st, df, rows_rh, rows_st) -> str:
    """what the re-pricing did, and the study's own figures beside Robinhood's for every slice"""
    hw = df['fee_how'].value_counts().sort('count', descending=True)
    how = '; '.join(f"{r['fee_how']} ({r['count']:,} trades)" for r in hw.iter_rows(named=True))
    lines = [f"**Fees.** Every figure in this section is at **Robinhood's fees** (the default cost model from 2026-10-24, "
             f"`docs/FEES_ROBINHOOD.md`): the study's own fill prices, the study's modelled fee added back "
             f"(mean ${df['fee_old'].mean():,.2f} a trade) and Robinhood's charged instead (mean ${df['fee_rh'].mean():,.2f}). "
             f"The study's fees are given beside them below. Re-pricing: {how}.", '',
             '| name | period | trades | mean %, $ at Robinhood fees | mean %, $ at the study\'s fees | win % Robinhood / study | 20-session block 95% (mean %) Robinhood / study |',
             sep(6, 10, 4, 10, 10, 8, 18)]
    p = 3 if st.unit == 'stock' else 2
    for (i, per, a), (_, _, b) in zip(rows_rh, rows_st):
        lines.append(f"| {i} | {per} | {a['trades']:,} | **{f(a['mean_pct'], p)}**, {f(a['mean_usd'])} | {f(b['mean_pct'], p)}, {f(b['mean_usd'])} | "
                     f"{a['win_rate']:.1f} / {b['win_rate']:.1f} | {M.fci(a['ci_pct'], p)} / {M.fci(b['ci_pct'], p)} |")
    return '\n'.join(lines)


def section(st) -> tuple[str, list]:
    md = [f"## #{st.sid} {st.name}", '',
          f"**Folder:** `{st.folder}`. **Commits:** {st.commits}. **Dates:** {st.dates}.", '',
          f"**Hypothesis.** {st.hypothesis}", '',
          f"**Rule.** {st.rule}", '',
          f"**Fills and costs (as the study ran them; re-priced at Robinhood's fees below).** {st.costs}", '',
          f"**Data.** {st.data}", '',
          f"**Periods and holdouts.** {st.periods}", '',
          f"**Pass rule (as pre-registered).** {st.pass_rule}", '',
          f"**Verdict.** {st.verdict}", '']
    rows = []
    if st.vendor:
        md += ['> **Vendor-recorded, not re-marked.** Every figure below is the vendor\'s own recorded card P&L, as published; '
               'none was re-priced on market quotes.', '']
    if st.load is not None:
        df_st = st.load()
        df_st.write_parquet(WORK / f'trades_s{st.sid}.parquet')
        df = df_st.with_columns(pl.col('pnl_rh').alias('pnl'))      # the primary figures: Robinhood's fees
        md += [f"**Metrics at Robinhood fees** (return = {UNIT_LABEL[st.unit]}; win = P&L > 0 after fees; breakeven is a loss; the interval is "
               f"audit_lib's 20-session moving-block bootstrap over the period's calendar sessions):", '']
        t, rows = tables(st, df)
        rows_st = [(i, p, M.metrics(d, st.unit, span)) for i, p, d, span in slices(st, df_st)]
        for (i, p, m), (_, _, ms), (_, _, d_rh, _) in zip(rows, rows_st, slices(st, df)):
            m['study'] = ms
            m['fee_how'] = sorted(set(d_rh['fee_how'].to_list()))
            m['verdict_rh'] = VR.answer(st, i, p, m, ms, df, df_st, rows, rows_st)
        base_txt = st.baseline() if callable(st.baseline) else st.baseline
        md += [t, '', fee_block(st, df_st, rows, rows_st), '', f"**Random baseline** (as the study computed it, at its own fees): {base_txt}", '',
               '**Exit reasons (share of trades):**', '', reasons(st, df), '',
               '**By year** at Robinhood fees (all periods together, labelled by entry year):', '', year_table(df), '',
               f"![]({chart(st, df, df_st)})", '']
    else:
        md += [f"**Metrics.** {st.na}", '']
    if st.extra:
        md += [st.extra, '']
    md += [f"**Amendments, deviations and integrity checks.** {st.integrity}", '', f"**What it showed.** {st.finding}", '']
    return '\n'.join(md), rows


def main(argv):
    want = set(argv)
    secs, summary = [], []
    for st in R.STRATEGIES:
        if want and st.sid not in want:
            continue
        t0 = time.time()
        md, rows = section(st)
        secs.append((st, md))
        summary.append((st, rows))
        print(f'#{st.sid} {st.name}: {time.time() - t0:.1f}s', flush=True)
    json.dump([[st.sid, st.name, st.verdict_period, [(i, p, {k: v for k, v in m.items() if k != 'reasons'}) for i, p, m in rows]]
               for st, rows in summary], open(WORK / 'summary_rows.json', 'w'), default=str)
    R.write_report(secs, summary, OUTDIR, want)


if __name__ == '__main__':
    main(sys.argv[1:])
