"""Append experiment records to research/compass/registry.jsonl (04_protocol.md §11): every run, with its configuration
hash, result directory, headline numbers and verdict, so no result exists outside the registry."""
from __future__ import annotations
import datetime as dt
import hashlib, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, '..', 'registry.jsonl')

def config_hash(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest()[:12]

def append(entry: dict) -> dict:
    entry = {'recorded_utc': dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'), **entry}
    with open(REGISTRY, 'a') as fh: fh.write(json.dumps(entry, default=str) + '\n')
    return entry

def record_study(study_id: str, out_dir: str, family: str, window: str, instruments: str, verdict: str, notes: str = '', kind: str = 'experiment') -> dict:
    cfg = json.load(open(os.path.join(out_dir, 'config.json')))
    summ = json.load(open(os.path.join(out_dir, 'summary.json')))
    a = summ.get('all', {})
    res = {'signals': summ.get('signals'), 'filled': summ.get('filled'), 'status_counts': summ.get('status_counts'),
           'mean': a.get('mean'), 'ci_lo': a.get('ci_lo'), 'ci_hi': a.get('ci_hi'), 'win_rate': a.get('win_rate'), 'profit_factor': a.get('profit_factor'),
           'max_drawdown': a.get('max_drawdown'), 'net_total': a.get('net_total'), 'days': a.get('days'),
           'baseline_pooled': summ.get('baseline_pooled'), 'strategy_minus_baseline': summ.get('strategy_minus_baseline'), 'by_year': summ.get('by_year')}
    return append({'id': study_id, 'kind': kind, 'family': family, 'window': window, 'instruments': instruments, 'fills': f"ask in / bid out at 1-minute NBBO, ${cfg['exits']['commission']}/contract/side",
                   'config_hash': config_hash(cfg), 'result_dir': os.path.relpath(out_dir, os.path.join(HERE, '..', '..', '..')), 'result': res, 'verdict': verdict, 'notes': notes})
