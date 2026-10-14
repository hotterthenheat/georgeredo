"""Study S16a (amendment A5, underlying part): overnight gap behaviour on SPY/QQQ/IWM 2017-06 -> 2026-10 from minute bars.
Signals at the open: the overnight gap (open vs prior close) and the prior session's close-to-close move; directions
continuation (+sign) and fade (-sign); horizons open -> same close, open -> next close, open -> third close.
Cells: all days, |gap| >= 0.5 %, |signal| >= 1 %. CIs clustered by date. Usage: python3 s16a_overnight_gaps_underlying.py"""
import datetime as dt, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np, polars as pl
from engine import bars, stats
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'results', 'v1', 's16a_overnight_gaps_underlying'); os.makedirs(OUT, exist_ok=True)
log = lambda *a: print(dt.datetime.now(dt.timezone.utc).strftime('%H:%M:%S'), *a, flush=True)
rows = []
for sym in ('SPY', 'QQQ', 'IWM'):
    df1 = bars.load_minutes(sym, f'{SP}/theta/data/underlying', dt.date(2017, 6, 1), dt.date(2026, 10, 9))
    d = df1.group_by('session').agg(pl.col('open').first().alias('open'), pl.col('close').last().alias('close')).sort('session')
    d = d.with_columns([pl.col('close').shift(1).alias('pc'), pl.col('close').shift(2).alias('pc2'), pl.col('close').shift(-1).alias('nc1'), pl.col('close').shift(-2).alias('nc2')])
    d = d.with_columns([(pl.col('open') / pl.col('pc') - 1).alias('gap'), (pl.col('pc') / pl.col('pc2') - 1).alias('prev_cc'),
                        (pl.col('close') / pl.col('open') - 1).alias('r_same'), (pl.col('nc1') / pl.col('open') - 1).alias('r_next'), (pl.col('nc2') / pl.col('open') - 1).alias('r_third'), pl.col('session').dt.year().alias('year')]).drop_nulls()
    for sig_name, sig_col in (('overnight gap', 'gap'), ('prior close-to-close', 'prev_cc')):
        for filt, cond in (('all days', pl.lit(True)), ('|gap| >= 0.5%', pl.col('gap').abs() >= 0.005), ('|signal| >= 1%', pl.col(sig_col).abs() >= 0.01)):
            s = d.filter(cond & (pl.col(sig_col) != 0)); sign = np.sign(s[sig_col].to_numpy()); days = s['session'].cast(pl.Utf8).to_numpy(); yrs = s['year'].to_numpy()
            for mode, k in (('continuation', 1), ('fade', -1)):
                for cell, col in (('open->close', 'r_same'), ('open->next close', 'r_next'), ('open->third close', 'r_third')):
                    r = s[col].to_numpy() * sign * k * 1e4; m, lo, hi = stats.cluster_bootstrap_ci(r, days, n_boot=2000)
                    by = {int(y): round(float(r[yrs == y].mean()), 1) for y in np.unique(yrs)}
                    rows.append({'symbol': sym, 'signal': sig_name, 'filters': filt, 'mode': mode, 'cell': cell, 'n': int(r.size), 'mean_bp': m, 'lo': lo, 'hi': hi, 'hit': float((r > 0).mean()), 'by_year': by})
                    if mode == 'continuation': log(f'{sym} {sig_name:20s} {filt:15s} {cell:18s} n {r.size:5d} cont {m:+6.1f} [{lo:+6.1f}, {hi:+6.1f}] hit {(r > 0).mean() * 100:.0f}% | years {by}')
json.dump(rows, open(os.path.join(OUT, 'rows.json'), 'w'), indent=1, default=str)
pos = [(r['symbol'], r['signal'], r['filters'], r['mode'], r['cell'], round(r['lo'], 1)) for r in rows if r['lo'] > 0]
log('cells with a positive lower bound:', pos); log('S16a DONE')
