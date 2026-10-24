"""mde_prereg.py — Compass Final: the planned trade counts and the MDE of every test, committed with the prereg, before any
fetch. Reads only: the session lists stage1_sessions.py wrote, the event calendars (dates), and SDs measured on PREVIOUSLY
READ periods (the final report's trade lists at Robinhood fees, and AFTERHOURS.md's period-ii case (b) rows), written to
out/sd_previous.json by sd_previous.py. No new data is read.

MDE (80% power, one-sided at the test's level alpha = 0.05 / (2k), k = 7 tests: the lower end of a two-sided 1 - 0.05/k
interval) = (z_{1-alpha} + z_{0.80}) * SD / sqrt(n). Two forms: per trade (SD of the per-trade return, n trades) and per
session (SD of the per-session mean return, n sessions) - the second respects that a session's trades move together.
"""
import csv, datetime as dt, io, json, math, subprocess
from pathlib import Path
from statistics import NormalDist
HERE = Path(__file__).resolve().parent; REPO = HERE.parents[1]
K = 7
alpha = 0.05 / (2 * K)
z = NormalDist().inv_cdf(1 - alpha); z80 = NormalDist().inv_cdf(0.80)
sd = json.loads((HERE / 'out' / 'sd_previous.json').read_text())

def rows(fam):
    return [r for r in csv.DictReader(open(HERE / f'sessions_{fam}.csv')) if r['excluded_by'] == '']

# event days (H13: FOMC/CPI/NFP; H15: FOMC + month-end), dates only
ev = list(csv.DictReader(io.StringIO(subprocess.run(['git', '-C', str(REPO), 'show', '7dfea57:research/thetadata/vol_filters/events.csv'], capture_output=True, text=True).stdout)))
evd = {e: {r['date'] for r in ev if r['event'] == e} for e in ('FOMC', 'CPI', 'NFP')}
fomc_json = json.loads((REPO / 'research_notes/Edge search/H7_H8_H9/data/fomc_statements_2012_2026.json').read_text())
fomc_extra = {x['date'] for x in fomc_json['scheduled'] if x.get('date') and '2017-01-01' <= x['date'] < '2017-06-01'}
BLS_2017 = {'CPI': ['2017-01-18', '2017-02-15', '2017-03-15', '2017-04-14', '2017-05-12'],
            'NFP': ['2017-01-06', '2017-02-03', '2017-03-10', '2017-04-07', '2017-05-05']}
evd['FOMC'] |= fomc_extra; evd['CPI'] |= set(BLS_2017['CPI']); evd['NFP'] |= set(BLS_2017['NFP'])
cal = list(csv.DictReader(io.StringIO(subprocess.run(['git', '-C', str(REPO), 'show', '7dfea57:research/thetadata/dataset/calendar_2017_2026.csv'], capture_output=True, text=True).stdout)))
closed = {r['date'] for r in cal if r['type'] == 'full_close'}
_d0 = dt.date(2017, 1, 2)
sess = sorted(x for x in ((_d0 + dt.timedelta(i)).isoformat() for i in range((dt.date(2026, 12, 31) - _d0).days + 1))
              if dt.date.fromisoformat(x).weekday() < 5 and x not in closed)   # the calendar lists only the exceptions
month_end = {max(d for d in sess if d[:7] == m) for m in {d[:7] for d in sess}}

out = {'k': K, 'alpha_one_sided': alpha, 'z': z, 'z80': z80, 'fomc_jan_may_2017': sorted(fomc_extra), 'bls_jan_may_2017': BLS_2017, 'tests': {}}
def add(name, n_trades, n_sess, sd_t, sd_s, src, note=''):
    out['tests'][name] = dict(planned_trades_max=n_trades, sessions=n_sess, sd_trade=sd_t, sd_session=sd_s, sd_source=src,
                              mde_trade=(z + z80) * sd_t / math.sqrt(n_trades), mde_session=(z + z80) * sd_s / math.sqrt(n_sess), note=note)

f = rows('fly5'); fs = {r['session'] for r in f}
b = sd['caseb']
add('fly5_iron', 2 * len(f), len(fs), b['fly5']['sd_b'], b['fly5']['sd_sess_b'], 'AFTERHOURS period ii, fly5 iron, case (b), Robinhood fees', '2 entry minutes x name-sessions')
for fam, per in (('condor_em1', 5), ('condor_d20', 5)):
    r = rows(fam)
    add(fam, per * len(r), len(r), b['condor_d20']['sd_b'], b['condor_d20']['sd_sess_b'], 'AFTERHOURS period ii, condor_d20, case (b), Robinhood fees' + (' (proxy for em1: AFTERHOURS ran no em1)' if fam == 'condor_em1' else ''), '5 entry minutes a session')
r = rows('touch_d25')
add('touch_d25', round(6.019 * len(r)), len(r), b['condor_d20']['sd_b'], b['condor_d20']['sd_sess_b'], 'proxy: condor_d20 case (b) (no case (b) was run on the touch spreads)', 'planned count = 6.019 touch rows a session (2025-26 OOS rate) x sessions: an estimate, touches are not scheduled')
r13 = [x for x in rows('h13_te') if not any(x['session'] in evd[e] for e in ('FOMC', 'CPI', 'NFP'))]
add('h13_te', len(r13), len(r13), sd['prev']['6d|TEST|SPXW']['sd_trade'], sd['prev']['6d|TEST|SPXW']['sd_session_mean'], 'final report 6d TEST at Robinhood fees (settled at the official close: no exercise risk on SPXW)')
r15 = [x for x in rows('h15_s2') if not (x['session'] in evd['FOMC'] or x['session'] in month_end)]
add('h15_s2', len(r15), len(r15), sd['prev']['6e|TEST|SPXW']['sd_trade'], sd['prev']['6e|TEST|SPXW']['sd_session_mean'], 'final report 6e TEST at Robinhood fees')
h1 = [d for d in sess if '2025-10-13' <= d <= '2026-10-22']
hd = {r['date'] for r in cal if r['type'] == 'early_close'}
h1 = [d for d in h1 if d not in hd]
add('h1_qqq', len(h1), len(h1), sd['prev']['32|single test|QQQ']['sd_trade'], sd['prev']['32|single test|QQQ']['sd_session_mean'], 'final report 32 QQQ single test at Robinhood fees (% of notional)', 'one trade a session at most (flat when the close equals the 15:00 price)')
out['h1_sessions'] = [h1[0], h1[-1], len(h1)]
out['h1_half_days_in_span'] = sorted(d for d in hd if '2025-10-13' <= d <= '2026-10-22')
out['prev_means'] = {'fly5_iron_ii_caseb': b['fly5']['mean_b'], 'condor_d20_ii_caseb': b['condor_d20']['mean_b'],
                     'h13_test': sd['prev']['6d|TEST|SPXW']['mean'], 'h15_test': sd['prev']['6e|TEST|SPXW']['mean'],
                     'h1_qqq': sd['prev']['32|single test|QQQ']['mean'], 'touch_oos_case0': sd['prev']['20a|OOS 2025–26|SPY']['mean'],
                     'em1_ii_case0': sd['prev']['26a|ii|SPY']['mean'], 'fly5_ii_case0_all': sd['prev']['26b|ii|ALL']['mean']}
# forward N for 80% power at one-sided 5% (the forward test of a single rule): n = ((z95 + z80) SD / mean)^2
z95 = NormalDist().inv_cdf(0.95)
fw = {}
for key, lab in (('7j-atm_put|2012-06→2026-10|SPY', 'S17 ATM put SPY'), ('7j-atm_put|2012-06→2026-10|QQQ', 'S17 ATM put QQQ'),
                 ('7j-put_30d|2012-06→2026-10|SPY', 'S17 0.30-delta put SPY'), ('7j-put_30d|2012-06→2026-10|QQQ', 'S17 0.30-delta put QQQ'),
                 ('32|single test|QQQ', 'H1 QQQ')):
    s = sd['prev'][key]
    fw[lab] = dict(mean=s['mean'], sd=s['sd_trade'], n_80=math.ceil(((z95 + z80) * s['sd_trade'] / s['mean']) ** 2) if s['mean'] > 0 else None)
s1 = sd['prev']['7j-atm_put|2012-06→2026-10|SPY']; s2 = sd['prev']['7j-atm_put|2012-06→2026-10|QQQ']
pm = (s1['mean'] * s1['n'] + s2['mean'] * s2['n']) / (s1['n'] + s2['n']); psd = max(s1['sd_trade'], s2['sd_trade'])
fw['S17 ATM put, SPY + QQQ pooled (the forward primary)'] = dict(mean=pm, sd=psd, n_80=math.ceil(((z95 + z80) * psd / pm) ** 2))
out['forward_n'] = fw
(HERE / 'out' / 'mde_prereg.json').write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
