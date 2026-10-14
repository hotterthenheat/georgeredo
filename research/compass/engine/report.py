"""Markdown report for a study directory: headline, by year, by symbol, by direction, by exit reason, by regime, baselines,
status counts, costs (04_protocol.md §7)."""
from __future__ import annotations
import datetime as dt
import json, os
import numpy as np
import polars as pl
from . import stats, regime

def _f(x, d=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)): return '—'
    return f'{x:,.{d}f}'

def _row(name, s):
    return f"| {name} | {s.get('n', 0)} | {s.get('days', '—')} | {_f(s.get('mean'))} | [{_f(s.get('ci_lo'))}, {_f(s.get('ci_hi'))}] | {_f(100 * s.get('win_rate', float('nan')), 1)} % | {_f(s.get('profit_factor'))} | {_f(s.get('max_drawdown'), 0)} | {_f(s.get('net_total'), 0)} |"

HEAD = '| cell | trades | days | mean $/contract | 95 % CI (day-clustered) | win | PF | max DD $ | net $ |\n|---|---|---|---|---|---|---|---|---|'

def grouped(trades: pl.DataFrame, key: str, title: str) -> str:
    if key not in trades.columns: return ''
    g = stats.by_group(trades, [key], n_boot=2000)
    if g.height == 0: return ''
    lines = [f'### {title}', '', HEAD]
    for r in g.sort(key).iter_rows(named=True): lines.append(_row(str(r[key]), r))
    return '\n'.join(lines) + '\n'

def write(out_dir: str, title: str, index_root: str | None = None, extra: str = '') -> str:
    cfg = json.load(open(os.path.join(out_dir, 'config.json')))
    summ = json.load(open(os.path.join(out_dir, 'summary.json')))
    trades = pl.read_parquet(os.path.join(out_dir, 'trades.parquet'))
    filled = trades.filter(pl.col('status') == 'filled').with_columns(pl.col('session').dt.year().alias('year'))
    if filled.height: filled = regime.annotate(filled, index_root)
    L = [f'# {title}', '', f"Generated {dt.datetime.utcnow():%Y-%m-%d %H:%M} UTC from `{os.path.relpath(out_dir)}` (engine {cfg.get('engine_version')}). Family `{cfg['family']}`, symbols {', '.join(cfg['symbols'])}, {cfg['start']} → {cfg['end']}. Fills: entry at the ask, exits at the bid, ${cfg['exits']['commission']:.2f}/contract/side, 1 contract; one open position per symbol: {cfg['one_position']}.", '']
    L += ['## Signals and fills', '', '| status | count |', '|---|---|'] + [f'| {k} | {v} |' for k, v in sorted(summ.get('status_counts', {}).items(), key=lambda kv: -kv[1])] + ['']
    if not filled.height: return '\n'.join(L + ['No filled trades.'])
    a = summ['all']
    L += ['## Headline (all filled trades)', '', HEAD, _row('all', a), '',
          f"Median $ {_f(a['median'])}; average win {_f(a['avg_win'])} / loss {_f(a['avg_loss'])}; MAE mean {_f(a.get('mae_mean'))} (p95 {_f(a.get('mae_p95'))}); MFE mean {_f(a.get('mfe_mean'))}; hold {_f(a.get('hold_min_mean'), 0)} min mean; commissions ${_f(a.get('commission_mean'))} per trade; gross-to-cost share {_f(a.get('cost_share'), 3)}; daily Sharpe (annualised) {_f(a.get('sharpe_daily_ann'))}, Sortino {_f(a.get('sortino_daily_ann'))}; worst 5 trades {[round(x) for x in a['worst_5_trades']]}; worst 5 days {[round(x) for x in a['worst_5_days']]}.", '']
    if summ.get('baseline_pooled'):
        b = summ['baseline_pooled']; d = summ.get('strategy_minus_baseline', {})
        L += ['## Matched random-entry baseline (5 seeds, same symbol/date/direction/contract rule/exits, random minute within ±45)', '', HEAD, _row('baseline pooled', b), _row('strategy', a), '',
              f"Strategy − baseline, paired by signal: n = {d.get('n_pairs')}, mean {_f(d.get('mean'))} [{_f(d.get('ci_lo'))}, {_f(d.get('ci_hi'))}] per contract against a mean round-trip cost (spread + fees) of {_f(d.get('round_trip_cost_mean'))}.", '']
    L += [grouped(filled, 'year', 'By year'), grouped(filled, 'symbol', 'By symbol'), grouped(filled, 'direction', 'By direction (+1 calls, −1 puts)'),
          grouped(filled, 'exit_reason', 'By exit reason'), grouped(filled, 'event', 'By event day (FOMC/CPI/NFP; unknown before 2017-02)'),
          grouped(filled, 'vix_tercile', 'By VIX open tercile (point-in-time, prior 252 sessions; 0 = warming up)'), grouped(filled, 'month_end', 'Month-end sessions'),
          grouped(filled, 'weekday', 'By weekday (0 = Monday)')]
    # hour-of-day buckets
    hb = filled.with_columns((pl.col('minute') // 60).alias('hour_bucket'))
    L.append(grouped(hb, 'hour_bucket', 'By entry hour bucket (0 = 09:30–10:29)'))
    L.append(extra)
    text = '\n'.join(L)
    open(os.path.join(out_dir, 'REPORT.md'), 'w').write(text)
    return text
