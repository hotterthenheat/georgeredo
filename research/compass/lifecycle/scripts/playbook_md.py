"""Writes 12_per_ticker_playbook.md: the prose in scripts/playbook_template.md with its tables {T1} .. {T8} rendered from
results/playbook/*.csv (written by per_ticker_playbook.py), so every figure in a table comes from the CSVs."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import paths

P = f'{paths.RESULTS}/playbook'
TICK = ['SPY', 'QQQ', 'IWM', 'SPXW']
NAME = {'LC-S': 'Steady call', 'LP-S': 'Steady put', 'LC-B': 'Big Payoff call', 'LP-B': 'Big Payoff put', 'DCS': 'Call debit spread',
        'DPS': 'Put debit spread', 'CSP': 'Cash-secured put', 'CPS': 'Put credit spread'}
BUCK = {'W': 'Weekly (1–7 days)', 'S': 'Swing (8–45)', 'P': 'Position (46–90)', 'L': 'Long-dated (91–269)', 'X': 'LEAPS (270+)'}
def pct(x, d=0): return '—' if x is None else f"{x * 100:.{d}f} %".replace('-', '−')
def spct(x, d=0): return '—' if x is None else (f"{x * 100:+.{d}f} %").replace('-', '−')
def usd(x): return '—' if x is None else (f"{x:+,.0f}" if abs(x) >= 10 else f"{x:+.1f}").replace('-', '−')
def row(cells): return '| ' + ' | '.join(str(c) for c in cells) + ' |'
def head(cols): return row(cols) + '\n' + row(['---'] * len(cols))
out = []

# day shape
d = pl.read_csv(f'{P}/day_shape.csv')
out.append('### T1 day shape\n' + head(['Ticker', 'Sessions', 'Median day range', 'Quiet day (25th pct)', 'Wild day (90th pct)', 'High set 9:30–10:00',
       'Low set 9:30–10:00', 'First 30 min holds the high or low', 'High set after 3:00', 'Low set after 3:00', 'Close, share of the way up the range']))
for t in TICK:
    r = d.filter(pl.col('root') == t).row(0, named=True)
    out.append(row([t if t != 'SPXW' else 'SPX', f"{r['sessions']} ({r['first'][:7]} → {r['last'][:7]})", pct(r['range_med'] / 100, 2), pct(r['range_p25'] / 100, 2), pct(r['range_p90'] / 100, 2),
                    pct(r['high_first30']), pct(r['low_first30']), pct(r['first30_has_high_or_low']), pct(r['high_last60']), pct(r['low_last60']), pct(r['close_location_med'])]))

# after entry
a = pl.read_csv(f'{P}/after_entry.csv').filter(pl.col('entries') == 'setup')
out.append('\n### T2 after entry\n' + head(['Ticker', 'Structure', 'Typical price', 'Spread', 'Ever +50 %', 'Ever +100 %', 'Minutes to the best (median)',
                                           'Ever −50 %', 'Best came before worst', 'Held to 3:30, average', 'Green at 3:30']))
for t in TICK:
    for s in ('LC-S', 'LP-S', 'LC-B', 'LP-B', 'DCS', 'DPS'):
        r = a.filter((pl.col('root') == t) & (pl.col('structure') == s)).row(0, named=True)
        out.append(row([t if t != 'SPXW' else 'SPX', NAME[s], f"${r['cost_med'] / 100:,.2f}", pct(r['spread_med'], 1), pct(r['reach_50']), pct(r['reach_100']), f"{r['min_to_best_med']:.0f}",
                        pct(r['hit_minus50']), pct(r['best_came_first']), spct(r['at_cutoff_mean']), pct(r['green_at_cutoff'])]))

# exits, debit
x = pl.read_csv(f'{P}/exits.csv')
RULES = [('M0_cutoff', 'Hold to 3:30'), ('M0_expiry', 'Hold to 4:00'), ('M1_t15', 'Out after 15 min'), ('M1_t60', 'Out after 60 min'),
         ('M2_s20_t20', 'Stop −20 % / target +20 %'), ('M2_s35_t50', 'Stop −35 % / target +50 %'), ('M2_snone_t50', 'Target +50 %, no stop'),
         ('M2_s50_tnone', 'Stop −50 %, no target'), ('M4_arm20_give25', 'Trail: from +20 %, give back 25 %')]
out.append('\n### T3 exits (dollars a contract, development / validation)\n' + head(['Ticker', 'Structure'] + [n for _, n in RULES] + ['Rules tested', 'Any with a lower bound above zero']))
for t in TICK:
    for s in ('LC-S', 'LP-S', 'LC-B', 'LP-B'):
        g = x.filter((pl.col('root') == t) & (pl.col('structure') == s))
        cells = []
        for p, _ in RULES:
            dv = g.filter((pl.col('pname') == p) & (pl.col('split') == 'dev'))['exp']; vl = g.filter((pl.col('pname') == p) & (pl.col('split') == 'val'))['exp']
            cells.append(f"{usd(dv[0])} / {usd(vl[0])}")
        ex = g.filter(pl.col('pname').str.contains(r'^M(0|1|2|3|4|5|8|9|12)_'))
        pos = ex.filter(pl.col('exp_lo') > 0)
        out.append(row([t if t != 'SPXW' else 'SPX', NAME[s]] + cells + [ex['pname'].n_unique(), 'none' if pos.height == 0 else ', '.join(f"{a} ({b})" for a, b in zip(pos['pname'], pos['split']))]))

# adds
deb = ['LC-S', 'LP-S', 'LC-B', 'LP-B', 'DCS', 'DPS']
ad = x.filter(pl.col('structure').is_in(deb) & pl.col('pname').is_in(['M6_k1_max1', 'M7_dd25', 'M7_dd40', 'M8_thirds']))
def w(c): return (pl.col(c) * pl.col('n')).sum() / pl.col('n').sum()
A = ad.group_by(['root', 'pname', 'split']).agg(w('lot_initial_per_trade').alias('first'), w('lot_add_per_trade').alias('add'), w('lot_dd_per_trade').alias('dd'), w('lot_scale_per_trade').alias('scale'))
out.append('\n### T4 adds (dollars a trade on the added contracts, development / validation)\n' + head(['Ticker', 'First contract (no add)', 'Add once it moves your way', 'Double down at −25 %', 'Double down at −40 %', 'Scale in by thirds (the later two-thirds)']))
for t in TICK:
    def g(p, c, sp): return A.filter((pl.col('root') == t) & (pl.col('pname') == p) & (pl.col('split') == sp))[c][0]
    out.append(row([t if t != 'SPXW' else 'SPX', f"{usd(g('M6_k1_max1', 'first', 'dev'))} / {usd(g('M6_k1_max1', 'first', 'val'))}",
                    f"{usd(g('M6_k1_max1', 'add', 'dev'))} / {usd(g('M6_k1_max1', 'add', 'val'))}", f"{usd(g('M7_dd25', 'dd', 'dev'))} / {usd(g('M7_dd25', 'dd', 'val'))}",
                    f"{usd(g('M7_dd40', 'dd', 'dev'))} / {usd(g('M7_dd40', 'dd', 'val'))}", f"{usd(g('M8_thirds', 'scale', 'dev'))} / {usd(g('M8_thirds', 'scale', 'val'))}"]))

# put sales
CR = [('M13_expiry', 'Hold to 4:00'), ('M13_tp25_snone', 'Take 25 % of the credit'), ('M13_tp50_snone', 'Take 50 %'), ('M13_tp50_touch', 'Take 50 %, or close if the strike is touched'),
      ('M13_tpnone_s15', 'Stop at 1.5× the credit'), ('M13_tpnone_s20', 'Stop at 2×'), ('M13_tpnone_s30', 'Stop at 3×')]
out.append('\n### T5 put sales (dollars a contract, development / validation; * interval above zero in that period)\n' + head(['Ticker', 'Structure'] + [n for _, n in CR] + ['Win rate, hold to 4:00']))
for t in TICK:
    for s in ('CSP', 'CPS'):
        g = x.filter((pl.col('root') == t) & (pl.col('structure') == s))
        cells = []
        for p, _ in CR:
            dv = g.filter((pl.col('pname') == p) & (pl.col('split') == 'dev')).row(0, named=True); vl = g.filter((pl.col('pname') == p) & (pl.col('split') == 'val')).row(0, named=True)
            cells.append(f"{usd(dv['exp'])}{'*' if dv['exp_lo'] > 0 else ''} / {usd(vl['exp'])}{'*' if vl['exp_lo'] > 0 else ''}")
        wr = g.filter((pl.col('pname') == 'M13_expiry') & (pl.col('split') == 'val'))['win_rate'][0]
        out.append(row([t if t != 'SPXW' else 'SPX', NAME[s]] + cells + [pct(wr)]))

# entry hour
h = pl.read_csv(f'{P}/entry_hour.csv')
out.append('\n### T6 entry hour (spread; and the average held to 3:30, for a random entry in that hour)\n' + head(['Ticker', 'Structure', 'Spread 9:30', 'Spread 12:00', 'Spread 3:00', 'Held to 3:30 from 9:30–10', 'from 10–11', 'from 12–1', 'from 2–3']))
for t in TICK:
    for s in ('LC-S', 'LP-S', 'LC-B', 'CSP'):
        g = h.filter((pl.col('root') == t) & (pl.col('structure') == s))
        su = g.filter(pl.col('entries') == 'setup'); rn = g.filter(pl.col('entries') == 'random later minute')
        def v(f, hr, c): r = f.filter(pl.col('hour') == hr)[c]; return r[0] if r.len() else None
        out.append(row([t if t != 'SPXW' else 'SPX', NAME[s], pct(v(su, 9, 'spread_med'), 1), pct(v(su, 12, 'spread_med'), 1), pct(v(su, 15, 'spread_med'), 1),
                        spct(v(rn, 9, 'held_to_cutoff_mean')), spct(v(rn, 10, 'held_to_cutoff_mean')), spct(v(rn, 12, 'held_to_cutoff_mean')), spct(v(rn, 14, 'held_to_cutoff_mean'))]))

# daily tier
da = pl.read_csv(f'{P}/daily_after.csv').filter(pl.col('entries') == 'setup')
dx = pl.read_csv(f'{P}/daily_exits.csv')
out.append('\n### T7 daily tier, after entry (setup entries, 2013–2023; FB 2017–2022)\n' + head(['Ticker', 'Expiry', 'Steady call: ever +50 %', 'ever −50 %', 'held to expiry, average', 'Steady put: ever +50 %', 'ever −50 %', 'held to expiry, average']))
for t in ['SPY', 'QQQ', 'IWM', 'FB']:
    for b in ('W', 'S', 'P', 'L', 'X'):
        c = da.filter((pl.col('root') == t) & (pl.col('bucket') == b) & (pl.col('structure') == 'LC-S'))
        p = da.filter((pl.col('root') == t) & (pl.col('bucket') == b) & (pl.col('structure') == 'LP-S'))
        if c.height == 0: continue
        c = c.row(0, named=True); p = p.row(0, named=True) if p.height else {}
        out.append(row([t, BUCK[b], pct(c['reach_50']), pct(c['hit_minus50']), spct(c['held_to_expiry_mean']), pct(p.get('reach_50')), pct(p.get('hit_minus50')), spct(p.get('held_to_expiry_mean'))]))
DR = [('LC-S', 'D0_expiry', 'Steady call, hold to expiry'), ('LC-S', 'D1_t10', 'Steady call, out after 10 sessions'), ('LP-S', 'D0_expiry', 'Steady put, hold to expiry'),
      ('LP-S', 'D1_t5', 'Steady put, out after 5 sessions'), ('CSP', 'D0_expiry', 'Cash-secured put, hold to expiry'), ('CSP', 'D13_tp50', 'Cash-secured put, take 50 %')]
out.append('\n### T8 daily tier, exits (dollars a contract, development 2013–2021 / validation 2022–2023; * interval above zero)\n' + head(['Ticker', 'Expiry'] + [n for _, _, n in DR]))
for t in ['SPY', 'QQQ', 'IWM', 'FB']:
    for b in ('W', 'S', 'P', 'L', 'X'):
        cells = []
        for s, p, _ in DR:
            g = dx.filter((pl.col('root') == t) & (pl.col('bucket') == b) & (pl.col('structure') == s) & (pl.col('pname') == p))
            if g.height == 0: cells.append('—'); continue
            dv = g.filter(pl.col('split') == 'dev'); vl = g.filter(pl.col('split') == 'val')
            f = lambda q: '—' if q.height == 0 or q['n'][0] < 30 else f"{usd(q['exp'][0])}{'*' if q['exp_lo'][0] > 0 else ''}"
            cells.append(f"{f(dv)} / {f(vl)}")
        out.append(row([t, BUCK[b]] + cells))
TABLES = {}
for block in '\n'.join(out).split('### ')[1:]:
    key, _, body = block.partition(' ')
    TABLES[key] = body.split('\n', 1)[1].strip()
TEMPLATE = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playbook_template.md')).read()
doc = TEMPLATE
for k, v in TABLES.items(): doc = doc.replace('{' + k + '}', v)
open(os.path.join(os.path.dirname(paths.RESULTS), '12_per_ticker_playbook.md'), 'w').write(doc)
print('written 12_per_ticker_playbook.md', sorted(TABLES))
