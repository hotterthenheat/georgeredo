"""Study S04 (diagnosis, 04_protocol.md §13 and the brief's §13): does the baseline signal predict the underlying at all?
On SPY/QQQ/IWM 1-minute bars 2017-06-01 -> 2026-10-09 (no options), for every baseline signal: the signed underlying
return (direction x return, basis points) over the 5, 15, 30 and 60 minutes AFTER the decision bar and to the session
close, and over the 15 and 30 minutes BEFORE it (how much of the move the signal chases). Compared with random minutes
matched by symbol/date (same count, uniformly inside the entry window, 5 seeds) and with each component of the rule
switched off. Day-clustered 95% CIs. Output: results/v1/s04_signal_underlying_validity/{table.csv, summary.json}."""
import datetime as dt, json, os, sys
import numpy as np, polars as pl
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from engine import bars, signals, stats
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'v1', 's04_signal_underlying_validity'); os.makedirs(OUT, exist_ok=True)
HORIZONS = [5, 15, 30, 60]
VARIANTS = {'baseline': {}, 'no_relvol': {'use_relvol': False}, 'no_structure': {'use_structure': False}, 'no_15m': {'use_align_15m': False}, 'no_5m': {'use_confirm_5m': False},
            'cross_only': {'use_relvol': False, 'use_structure': False, 'use_align_15m': False, 'use_confirm_5m': False}, 'daily_trend': {'use_daily_trend': True}}

def forward_returns(feat: pl.DataFrame, idx: np.ndarray, direction: np.ndarray) -> dict:
    close = feat['close'].to_numpy(); sess = feat['session'].cast(pl.Int32).to_numpy(); n = close.size
    out = {}
    for h in HORIZONS:
        j = np.minimum(idx + h, n - 1); same = sess[j] == sess[idx]
        r = np.where(same, (close[j] / close[idx] - 1) * 1e4 * direction, np.nan); out[f'fwd_{h}m_bp'] = r
    for h in (15, 30):
        j = np.maximum(idx - h, 0); same = sess[j] == sess[idx]
        r = np.where(same, (close[idx] / close[j] - 1) * 1e4 * direction, np.nan); out[f'pre_{h}m_bp'] = r
    # to the session close
    last = {}
    for i in range(n - 1, -1, -1): last.setdefault(sess[i], i)
    jc = np.array([last[s] for s in sess[idx]]); out['fwd_close_bp'] = (close[jc] / close[idx] - 1) * 1e4 * direction
    return out

rows = []; summary = {}
log = lambda *a: print(dt.datetime.utcnow().strftime('%H:%M:%S'), *a, flush=True)
for sym in ['SPY', 'QQQ', 'IWM']:
    df1 = bars.load_minutes(sym, f'{SP}/theta/data/underlying', dt.date(2017, 6, 1), dt.date(2026, 10, 9))
    feat = signals.features(df1).with_row_index('idx')
    log(sym, 'bars', df1.height)
    for name, p in VARIANTS.items():
        ev = signals.baseline_events(feat, {**p, 'entry_end_minute': 320})
        if ev.height == 0: continue
        idx = ev['idx'].to_numpy(); direction = ev['direction'].to_numpy()
        fr = forward_returns(feat, idx, direction)
        days = ev['session'].cast(pl.Utf8).to_numpy()
        rec = {'symbol': sym, 'variant': name, 'n': int(ev.height), 'days': int(np.unique(days).size), 'calls_share': float((direction > 0).mean())}
        for k, v in fr.items():
            ok = np.isfinite(v); m, lo, hi = stats.cluster_bootstrap_ci(v[ok], days[ok], n_boot=2000); rec[k] = m; rec[k + '_lo'] = lo; rec[k + '_hi'] = hi
            rec[k + '_hit'] = float((v[ok] > 0).mean())
        rows.append(rec)
        # matched random minutes: same symbol and date, same direction, uniformly inside the entry window
        if name == 'baseline':
            sess_arr = feat['session'].cast(pl.Int32).to_numpy(); minute = feat['minute'].to_numpy()
            by_sess = {}
            for i, s in enumerate(sess_arr): by_sess.setdefault(s, []).append(i)
            for seed in (11, 12, 13, 14, 15):
                rng = np.random.default_rng(seed); ridx = []
                for s in ev['session'].cast(pl.Int32).to_numpy():
                    cand = [i for i in by_sess[s] if 15 <= minute[i] <= 320]
                    ridx.append(cand[rng.integers(0, len(cand))])
                ridx = np.array(ridx); frr = forward_returns(feat, ridx, direction)
                rec = {'symbol': sym, 'variant': f'random_{seed}', 'n': int(ridx.size), 'days': int(np.unique(days).size), 'calls_share': float((direction > 0).mean())}
                for k, v in frr.items():
                    ok = np.isfinite(v); m, lo, hi = stats.cluster_bootstrap_ci(v[ok], days[ok], n_boot=1000); rec[k] = m; rec[k + '_lo'] = lo; rec[k + '_hi'] = hi; rec[k + '_hit'] = float((v[ok] > 0).mean())
                rows.append(rec)
        log(sym, name, 'n', ev.height, 'fwd30 bp', round(rec.get('fwd_30m_bp', float('nan')), 2))
tab = pl.DataFrame(rows); tab.write_csv(os.path.join(OUT, 'table.csv'))
json.dump({'generated_utc': dt.datetime.utcnow().isoformat(), 'rows': rows}, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=str)
print(tab.select(['symbol', 'variant', 'n', 'pre_30m_bp', 'fwd_5m_bp', 'fwd_15m_bp', 'fwd_30m_bp', 'fwd_60m_bp', 'fwd_close_bp', 'fwd_30m_bp_lo', 'fwd_30m_bp_hi']).to_pandas().round(2).to_string())
EOF
