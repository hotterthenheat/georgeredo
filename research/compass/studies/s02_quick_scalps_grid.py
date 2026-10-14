"""Study S02: single-factor grid and ablations around the Quick Scalps baseline on the 0DTE cache (04_protocol.md §8),
one configuration per run directory, run in parallel processes. Walk-forward selection is post-processing
(engine.walkforward) over these directories. Usage: python3 s02_quick_scalps_grid.py [workers] [only_name]"""
import datetime as dt, json, os, sys, multiprocessing as mp
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SP = os.environ.get('SP', '/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad')
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'v1', 's02_quick_scalps_grid')

VARIANTS = {
    # signal parameters
    'rsi7': {'signal': {'rsi_period': 7}}, 'rsi9': {'signal': {'rsi_period': 9}}, 'rsi21': {'signal': {'rsi_period': 21}},
    'lead3': {'signal': {'ema_lead': 3}}, 'lead5': {'signal': {'ema_lead': 5}}, 'lead8': {'signal': {'ema_lead': 8}}, 'lead13': {'signal': {'ema_lead': 13}},
    'mid21': {'signal': {'ema_mid': 21}}, 'mid34': {'signal': {'ema_mid': 34}},
    'slow100': {'signal': {'ema_slow': 100}}, 'slow200': {'signal': {'ema_slow': 200}},
    'relvol_off': {'signal': {'use_relvol': False}}, 'relvol125': {'signal': {'relvol_min': 1.25}}, 'relvol150': {'signal': {'relvol_min': 1.5}}, 'relvol200': {'signal': {'relvol_min': 2.0}},
    'no_15m': {'signal': {'use_align_15m': False}}, 'daily_trend': {'signal': {'use_daily_trend': True}},
    'no_structure': {'signal': {'use_structure': False}}, 'no_5m': {'signal': {'use_confirm_5m': False}},
    'rsi_60_40': {'signal': {'rsi_up': 60.0, 'rsi_down': 40.0}}, 'rsi_50_50': {'signal': {'rsi_up': 50.0, 'rsi_down': 50.0}},
    # contract selection
    'delta20_40': {'select': {'delta_lo': 0.20, 'delta_hi': 0.40, 'delta_target': 0.30}}, 'delta30_50': {'select': {'delta_lo': 0.30, 'delta_hi': 0.50, 'delta_target': 0.40}},
    'delta40_60': {'select': {'delta_lo': 0.40, 'delta_hi': 0.60, 'delta_target': 0.50}},
    'spread5': {'select': {'max_spread_pct': 0.05}}, 'spread8': {'select': {'max_spread_pct': 0.08}}, 'spread10': {'select': {'max_spread_pct': 0.10}}, 'spread15': {'select': {'max_spread_pct': 0.15}},
    'pick_tightest': {'select': {'pick': 'tightest_spread'}},
    # exits
    'stop20': {'exits': {'stop_pct': 0.20}}, 'stop30': {'exits': {'stop_pct': 0.30}}, 'stop40': {'exits': {'stop_pct': 0.40}},
    'no_vwap_loss': {'exits': {'use_vwap_loss': False}}, 'no_invalidation': {'exits': {'use_invalidation': False}}, 'no_ema_target': {'exits': {'use_ema_target': False}},
    'no_partial': {'exits': {'tp1_frac': 0.0}}, 'tp100': {'exits': {'tp2_pct': 1.00}}, 'tp50_100': {'exits': {'tp1_pct': 0.50, 'tp2_pct': 1.00}},
    'hold30': {'exits': {'max_hold_min': 30}}, 'hold120': {'exits': {'max_hold_min': 120}},
    'invalidation_only': {'exits': {'use_vwap_loss': False, 'use_ema_target': False, 'tp1_frac': 0.0, 'tp2_pct': 100.0, 'stop_pct': 1.0}},
}

def one(name):
    from engine import store, run
    cfg = VARIANTS[name]
    st = store.CacheStore(f'{SP}/theta/data/underlying', f'{SP}/theta/data_full/chains', f'{SP}/theta/data/index', f'{SP}/universe/expirations.jsonl')
    out = os.path.join(ROOT, name)
    if os.path.exists(os.path.join(out, 'summary.json')): return name, 'exists'
    sel = {'min_oi': None, 'min_volume': None, **cfg.get('select', {})}
    s = run.run_family(st, 'quick_scalps', ['SPY', 'QQQ', 'IWM'], dt.date(2022, 11, 11), dt.date(2026, 10, 9), out, signal_params=cfg.get('signal'),
                       select_params=sel, exit_params=cfg.get('exits'), log=lambda *a: None)
    return name, {k: s.get(k) for k in ('filled',)} | ({'mean': s['all']['mean'], 'ci': (s['all']['ci_lo'], s['all']['ci_hi'])} if s.get('all') else {})

if __name__ == '__main__':
    workers = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    names = [sys.argv[2]] if len(sys.argv) > 2 else list(VARIANTS)
    os.makedirs(ROOT, exist_ok=True)
    with mp.get_context('fork').Pool(workers) as pool:
        for name, res in pool.imap_unordered(one, names):
            print(name, res, flush=True)
