#!/usr/bin/env python3
"""thousand.py — "imagine I gave each strategy $1,000": walks every row of the final report's page-1 summary table
through its own trades, in date order, under two sizing rules, and writes THOUSAND_DOLLARS.md, its charts
(charts_1000/) and THOUSAND_DOLLARS.pdf.

    POLARS_MAX_THREADS=2 python3 thousand.py

Read-only with respect to the research: every trade list comes from registry.py's loaders, cut to the page-1 row by
the same slice logic build.py and registry._row use; no rule is recomputed, nothing is fetched, no holdout is opened.
Each trade's return is 100 × pnl ÷ cost, the report's own figure (costs already inside pnl).

Method A, "all in each day": each session the whole balance is split equally across that session's trades, so the
balance grows by the session's mean return. A session whose mean return is −100% or worse leaves nothing: the row is
"wiped out" on that date and stops.
Method B, "10% per trade": each trade gets 10% of the balance at the start of its session; with more than ten trades in a
session each gets 100% ÷ n, so the session never uses more than the whole balance.
A trade is booked on its entry session (the loaders carry the entry date only).
"""
from __future__ import annotations

import datetime as dt
import math
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402  (slices(): the report's own cut of a trade frame)
import registry as R  # noqa: E402
from base import WORK  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
CH = OUT / 'charts_1000'
for _old in CH.glob('r*_s*.png') if CH.exists() else []:
    _old.unlink()                     # a run writes every chart afresh
CH.mkdir(exist_ok=True)
START = 1000.0
UNIT = {'premium': '% of premium', 'risk': '% of max risk', 'stock': '% of notional', 'credit': '% of credit', 'capital': '% of cash set aside'}
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'
SUP = str.maketrans('0123456789-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁻')


# ---- the page-1 rows, exactly as registry._row picks them -----------------------------------------------------------------------------

def page1_rows():
    """[(st, inst, period, frame)] for every page-1 row; [(st)] for the studies with no trade-level result"""
    rows, na = [], []
    for st in R.STRATEGIES:
        if st.load is None:
            na.append(st)
            continue
        df = st.load()
        sl = B.slices(st, df)                       # (inst, period, frame, span), report order
        want = st.summary_slices
        if not want:
            vp = st.verdict_period or (sl[0][1] if sl else '')
            pooled = [s for s in sl if s[1] == vp and s[0] == 'all names']
            want = [('all names', vp)] if pooled else [(s[0], s[1]) for s in sl if s[1] == vp]
        for i, p in want:
            for inst, per, d, _span in sl:
                if inst == i and per == p:
                    rows.append((st, inst, per, d))
        print(f'#{st.sid}: {len(want)} row(s)', flush=True)
    return rows, na


# ---- the two walks ----------------------------------------------------------------------------------------------------------------------

def walk(df: pl.DataFrame, method: str) -> dict:
    d = df.with_columns((pl.col('pnl') / pl.col('cost')).alias('r'))
    g = d.group_by('date').agg(pl.col('r').mean().alias('mean'), pl.col('r').sum().alias('sum'), pl.len().alias('n')).sort('date')
    dates = g['date'].to_list()
    if method == 'A':
        step = g['mean'].to_numpy()
    else:
        n = g['n'].to_numpy().astype(float)
        step = np.minimum(0.10, 1.0 / n) * g['sum'].to_numpy()
    bal, path, wiped = START, [], None
    for day, s in zip(dates, step):
        bal = bal * (1.0 + s)
        if bal <= 0:
            path.append((day, 0.0))
            wiped = day
            bal = 0.0
            break
        path.append((day, bal))
    vals = np.array([START] + [v for _, v in path])
    days = ['start'] + [k for k, _ in path]
    peak = np.maximum.accumulate(vals)
    dd = (peak - vals) / peak
    lo = int(np.argmin(vals))
    return {'end': bal, 'ret': (bal / START - 1) * 100, 'low': float(vals[lo]), 'low_date': days[lo], 'mdd': float(dd.max() * 100),
            'wiped': wiped, 'path': path}


# ---- formatting -------------------------------------------------------------------------------------------------------------------------

def sci(x: float) -> str:
    e = int(math.floor(math.log10(abs(x))))
    m = x / 10 ** e
    if round(m, 2) >= 10:
        m, e = m / 10, e + 1
    return f'{m:.2f} × 10{str(e).translate(SUP)}'


def usd(x: float) -> str:
    if x == 0:
        return '$0'
    if x >= 1e7 or x < 0.01:
        return '$' + sci(x)
    return f'${x:,.2f}' if x < 100 else f'${x:,.0f}'


def pct(x: float) -> str:
    if abs(x) >= 1e6:
        return ('+' if x > 0 else '−') + sci(abs(x)) + '%'
    return f'{x:+,.1f}%'.replace('-', '−')


def end_cell(w: dict) -> str:
    return f"**wiped out** {w['wiped']}" if w['wiped'] else usd(w['end'])


def low_cell(w: dict) -> str:
    return f"{usd(w['low'])} ({w['low_date']})"


def tag(st) -> str:
    t = []
    if st.vendor:
        t.append('vendor-recorded, not re-marked')
    if 'PREVIEW' in st.verdict or 'PREVIEW' in st.name:
        t.append('PREVIEW')
    return (' — *' + '; '.join(t) + '*') if t else ''


# ---- charts -----------------------------------------------------------------------------------------------------------------------------

def chart(k: int, st, inst, per, wa, wb) -> str:
    fig, ax = plt.subplots(figsize=(3.3, 1.95), dpi=150)
    floor = None
    for w, col, lab in ((wa, '#1f4e79', 'A all in'), (wb, '#c0504d', 'B 10%')):
        X = [dt.date.fromisoformat(d) for d, _ in w['path']]
        Y = [v for _, v in w['path']]
        pos = [(x, y) for x, y in zip(X, Y) if y > 0]
        if pos:
            ax.plot([p[0] for p in pos], [p[1] for p in pos], lw=0.9, color=col, label=lab)
            m = min(p[1] for p in pos)
            floor = m if floor is None else min(floor, m)
        if w['wiped']:
            x = dt.date.fromisoformat(w['wiped'])
            ax.plot([x], [pos[-1][1] if pos else START], marker='x', color=col, ms=5, mew=1.4)
            ax.annotate('wiped out', (x, pos[-1][1] if pos else START), fontsize=5, color=col, xytext=(2, -7), textcoords='offset points')
    ax.axhline(START, color='#999999', lw=0.6, ls='--')
    ax.set_yscale('log')
    ax.tick_params(which='both', labelsize=5)
    lo_, hi_ = ax.get_ylim()
    fmt = matplotlib.ticker.FuncFormatter(lambda v, _p: usd(v) if v > 0 else '')
    ax.yaxis.set_major_formatter(fmt)
    if hi_ / lo_ >= 10:
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    else:
        ax.yaxis.set_minor_locator(matplotlib.ticker.MaxNLocator(4))
        ax.yaxis.set_minor_formatter(fmt)
    ax.xaxis.get_offset_text().set_fontsize(5)
    ax.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator(minticks=2, maxticks=4))
    ax.xaxis.set_major_formatter(matplotlib.dates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
    name = R.label(st)
    name = name if len(name) <= 46 else name[:44].rsplit(' ', 1)[0] + ' …'
    ax.set_title(f'#{st.sid} {name}\n{inst} · {per}', fontsize=5.6, loc='left')
    ax.legend(fontsize=4.8, frameon=False, loc='best')
    ax.set_ylabel('balance $ (log)', fontsize=5)
    fig.tight_layout(pad=0.4)
    p = CH / f'r{k:02d}_s{st.sid}.png'
    fig.savefig(p)
    plt.close(fig)
    return f'charts_1000/{p.name}'


# ---- the document -----------------------------------------------------------------------------------------------------------------------

METHOD = """**What this is.** Every row of the final report's page-1 table (`FINAL_RESEARCH_REPORT.md`, commit 14a30a7), each
on the same strategy, instrument and period as listed there, started with **$1,000** and walked through its own trades in
date order. The trades are the report's own (its loaders in `build/`); nothing was re-tested, re-priced or fetched.

**Method A, "all in each day".** Each session, the whole balance is split equally across that session's trades. Each
slice earns that trade's return in the row's own unit (% of premium paid, % of max risk, % of the credit received, % of
the cash set aside, or % of notional, as the table uses). The balance compounds session by session. A trade can lose more
than 100% of its unit (a short straddle, or a credit loss bigger than the credit), and a session whose only trades are
long options that all expire worthless loses 100%; if a session takes the balance to zero or below, the row is **wiped
out** on that date and stops.

**Method B, "10% per trade".** Each trade uses 10% of the balance at the start of its session. When a session has more
than ten trades, each uses 100% ÷ the number of trades, so a day never uses more than the whole balance. It compounds the
same way. On a session with ten or more trades, B uses the whole balance too, so a row that always trades ten or more a
session ends the same under A and B.

**For both.** Fractional contracts are allowed. That is not realistic: $1,000 often cannot buy one real SPXW contract,
or post the margin on a short straddle or strangle, and short-premium rows would need far more than $1,000 in a real
account. Costs are already inside each trade's return, as the study ran it. There are no taxes, no margin interest and
no slippage beyond the study's own fills. A trade is booked on its entry session (the trade lists carry the entry date
only), so a trade held for days or weeks is treated as if its money came back the same day. "Worst point" is the lowest
balance under method A and its date ("start" if it never fell below $1,000).
"""


def main():
    rows, na = page1_rows()
    res = []
    for st, inst, per, d in rows:
        d = d.sort('date')
        wa, wb = walk(d, 'A'), walk(d, 'B')
        res.append(dict(st=st, inst=inst, per=per, n=d.height, sess=d['date'].n_unique(), a0=d['date'].min(), a1=d['date'].max(),
                        A=wa, B=wb, mean=float((100 * d['pnl'] / d['cost']).mean())))
    # by the A ending balance; wiped-out rows last, the one that lasted longest first
    res.sort(key=lambda r: (-r['A']['end'], '' if not r['A']['wiped'] else ''.join(chr(255 - ord(ch)) for ch in r['A']['wiped'])))
    for k, r in enumerate(res, 1):
        r['chart'] = chart(k, r['st'], r['inst'], r['per'], r['A'], r['B'])
        r['k'] = k

    nA = sum(r['A']['end'] > START for r in res)
    nB = sum(r['B']['end'] > START for r in res)
    wA = sum(bool(r['A']['wiped']) for r in res)
    wB = sum(bool(r['B']['wiped']) for r in res)
    up = [r for r in res if r['A']['end'] > START]
    short_units = {'risk', 'credit', 'capital'}
    n_short = sum(r['st'].unit in short_units for r in up)
    n_stock = sum(r['st'].unit == 'stock' for r in up)
    n_vend = sum(r['st'].vendor for r in up)
    n_prev_rows = sum('PREVIEW' in r['st'].verdict for r in up)
    assert n_short + n_stock + n_vend + n_prev_rows == nA and n_vend == 1 and n_prev_rows == 1, 'rewrite the plain-words note'

    md = ['# $1,000 in each strategy', '',
          '**Repository:** georgeredo, branch `claude/lucid-heisenberg-bpyq7k`. **Built:** 2026-10-23 by '
          '`research_notes/FINAL REPORT/build/thousand.py`, from the trade lists of `FINAL_RESEARCH_REPORT.md` (14a30a7).', '',
          METHOD, '',
          f'**In plain words.** These are what each strategy did over its own study period, not a forecast of what it will do next. '
          f'Most rows lose: {len(res) - nA} of {len(res)} end below $1,000 under method A ({wA} of them wiped out) and '
          f'{len(res) - nB} of {len(res)} under method B. '
          f'The big gains come from short-premium and spread rows ({n_short} of the {nA} that end above $1,000 under A, led by '
          f'#{res[0]["st"].sid}), whose real-account margin or cash $1,000 could not post; the other {nA - n_short} are '
          f'{n_stock} stock rows with small gains, the vendor\'s own Epoch 1 cards and a five-session preview.', '',
          '## Page 1. Every row, sorted by the method A ending balance', '',
          '| # | strategy | instrument | period | trades | ending $ (A) | ending $ (B) | worst point (A) | verdict from the report |',
          '|' + '|'.join('-' * (3 * w) for w in (2, 18, 6, 9, 4, 7, 7, 9, 12)) + '|']
    for r in res:
        st = r['st']
        md.append(f"| {r['k']} | #{st.sid} {R.label(st)}{tag(st)} | {r['inst']} | {r['per']} | {r['n']:,} | {end_cell(r['A'])} | "
                  f"{end_cell(r['B'])} | {low_cell(r['A'])} | {R.short_verdict(st)} |")
    for st in na:
        why = st.na.replace('not available — ', '')
        why = why if len(why) <= 150 else why[:148].rsplit(' ', 1)[0] + ' …'
        md.append(f"| — | #{st.sid} {R.label(st)} | — | — | — | not available — {why} | not available | — | {R.short_verdict(st)} |")
    md += ['', f'**Counts.** Above $1,000 at the end: {nA} of {len(res)} rows under A, {nB} under B. Wiped out: {wA} under A, '
           f'{wB} under B. The {len(na)} studies at the foot of the table have no trade list with usable per-trade returns.', '',
           '## Every row in full', '',
           'Return unit is the row\'s own. "Sessions" counts the sessions with at least one trade. Max drawdown is the largest fall '
           'from a running peak of the balance, in %.', '',
           '| # | strategy | instrument | period | unit | start | end | sessions | trades | A: ending $ | A: total return | A: lowest (date) | A: max DD | B: ending $ | B: total return | B: lowest (date) | B: max DD |',
           '|' + '|'.join('-' * (3 * w) for w in (2, 14, 5, 7, 5, 5, 5, 4, 4, 6, 6, 8, 4, 6, 6, 8, 4)) + '|']
    for r in res:
        st, a, b = r['st'], r['A'], r['B']
        md.append(f"| {r['k']} | #{st.sid} {R.label(st)}{tag(st)} | {r['inst']} | {r['per']} | {UNIT.get(st.unit, st.unit)} | {r['a0']} | {r['a1']} | "
                  f"{r['sess']:,} | {r['n']:,} | {end_cell(a)} | {'−100% (wiped out)' if a['wiped'] else pct(a['ret'])} | {low_cell(a)} | {a['mdd']:.1f}% | "
                  f"{end_cell(b)} | {'−100% (wiped out)' if b['wiped'] else pct(b['ret'])} | {low_cell(b)} | {b['mdd']:.1f}% |")
    md += ['', '## Balance curves', '',
           'One chart a row, in the page-1 order: method A in blue, method B in red, the balance on a log scale, the dashed line '
           'at $1,000, an ✕ where a row is wiped out.', '',
           '<div class="grid">', '']
    for r in res:
        md.append(f"![]({r['chart']}){{width=24%}}")
    md += ['', '</div>', '']
    (OUT / 'THOUSAND_DOLLARS.md').write_text('\n'.join(md))
    print('wrote', OUT / 'THOUSAND_DOLLARS.md')

    # summary for the hand-off
    for r in res[:5] + res[-5:]:
        print(r['k'], '#' + r['st'].sid, r['inst'], r['per'], end_cell(r['A']), end_cell(r['B']), r['n'], f"{r['mean']:+.3f}")
    print('above A', nA, 'above B', nB, 'wiped A', wA, 'wiped B', wB, 'rows', len(res), 'na', len(na), 'short among up', n_short)
    render()


CSS = """
@page { size: A4 landscape; margin: 11mm 10mm 12mm 10mm; }
body { font-family: 'DejaVu Sans', Helvetica, Arial, sans-serif; font-size: 8.6pt; line-height: 1.32; color: #111; max-width: none; margin: 0; }
h1 { font-size: 17pt; margin: 0 0 6pt 0; }
h2 { font-size: 12pt; margin: 14pt 0 4pt 0; border-bottom: 1px solid #bbb; padding-bottom: 2pt; page-break-after: avoid; }
table { border-collapse: collapse; width: 100%; margin: 4pt 0 8pt 0; font-size: 6.6pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 0.5px solid #c8c8c8; padding: 1.2pt 3pt; vertical-align: top; }
th { background: #eef2f7; text-align: left; }
tbody tr:nth-child(even) { background: #fafafa; }
td { word-break: break-word; }
.grid img { display: inline-block; margin: 2pt 0.3%; page-break-inside: avoid; vertical-align: top; }
code { font-size: 7.6pt; background: #f3f3f3; padding: 0 2px; }
"""


def render():
    """the final report's way (render.py): pandoc to one self-contained HTML page, headless Chromium to the PDF"""
    WORK.mkdir(parents=True, exist_ok=True)
    css = WORK / 'thousand.css'
    css.write_text(CSS)
    src = (OUT / 'THOUSAND_DOLLARS.md').read_text()
    src = src.replace('\n## Every row in full', '\n<div style="page-break-before: always"></div>\n\n## Every row in full')
    src = src.replace('\n## Balance curves', '\n<div style="page-break-before: always"></div>\n\n## Balance curves')
    tmp = WORK / 'thousand_src.md'
    tmp.write_text(src)
    html = WORK / 'THOUSAND_DOLLARS.html'
    subprocess.run(['pandoc', str(tmp), '-f', 'markdown+pipe_tables-yaml_metadata_block-tex_math_dollars-implicit_figures', '-t', 'html5',
                    '--standalone', '--embed-resources', f'--resource-path={OUT}', '--css', str(css),
                    '--metadata', 'pagetitle=$1,000 in each strategy', '-o', str(html)], check=True)
    pdf = OUT / 'THOUSAND_DOLLARS.pdf'
    subprocess.run([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu', '--no-pdf-header-footer',
                    f'--print-to-pdf={pdf}', f'file://{html}'], check=True, capture_output=True)
    print('wrote', pdf, pdf.stat().st_size)


if __name__ == '__main__':
    main()
