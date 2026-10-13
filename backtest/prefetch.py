"""Prefetch underlying bars, GEX levels and IV context for every ticker/day in range (parallel, cached)."""
import os, sys, json, concurrent.futures, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data
days = json.load(open(os.path.dirname(os.path.abspath(__file__)) + '/probe/trading_days.json'))
START, END = sys.argv[1], sys.argv[2]; TICKERS = sys.argv[3].split(',')
sel = [d for d in days if START <= d <= END]
# include 6 prior sessions for prior-week levels
i0 = days.index(sel[0]); sel_all = days[max(0, i0 - 6):days.index(sel[-1]) + 1]
jobs = [(t, d) for t in TICKERS for d in sel_all]
def work(j):
    t, d = j
    r, p = data.underlying_bars(t, d); g = data.gex_levels(t, d); iv = data.iv_context(t, d)
    return (t, d, len(r), len(p), g.get('gamma_flip') is not None, iv.get('iv1d') is not None)
bad = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
    for i, res in enumerate(ex.map(work, jobs)):
        if res[2] < 300: bad += 1; print('short day', res)
        if i % 200 == 0: print('progress', i, '/', len(jobs), data.STATS, flush=True)
print('done', len(jobs), 'short days', bad, data.STATS)
