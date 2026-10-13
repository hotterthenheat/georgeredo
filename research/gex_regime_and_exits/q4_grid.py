"""Q4: run the 576-configuration exit grid on the strategy entries and the random-entry control; save per-trade $ outcomes."""
import pickle, time
from common import *
import q4_engine as E
P = pickle.load(open(OUT + '/q4_bars.pkl', 'rb'))
for name, trades in (('strategy', P['rows']), ('random', P['rand'])):
    t0 = time.time(); M = E.build(trades, P['cache']); n = len(E.GRID)
    usd = {m: np.zeros((n, M['N']), np.float32) for m in ('usd_mid', 'usd_spread', 'usd_adverse', 'usd_spread_floor', 'ret_mid', 'ret_spread')}
    first = np.zeros((n, M['N']), np.int8); last = np.zeros((n, M['N']), np.int8); exit_min = np.zeros((n, M['N']), np.float32)
    for i, c in enumerate(E.GRID):
        R = E.run(M, **c); S = E.settle(M, R)
        for m in usd: usd[m][i] = S[m]
        first[i] = R['first']; last[i] = R['last']; exit_min[i] = R['exit_min']
        if i % 100 == 0: print(name, i, '/', n, round(time.time() - t0, 1), 's', flush=True)
    keep = M['keep']; meta = dict(ticker=np.array([trades[k]['ticker'] for k in keep]), date=np.array([trades[k]['date'] for k in keep]), entry_t=np.array([trades[k]['entry_t'] for k in keep]),
                                 variant=np.array([trades[k].get('variant', 'RANDOM') for k in keep]), direction=np.array([trades[k]['direction'] for k in keep]), entry_px=M['entry_px'], entry_min=np.array([hhmm(datetime.datetime.fromisoformat(trades[k]['entry_t'])) for k in keep], float),
                                 level=np.array([trades[k].get('level', '') for k in keep]), regime=np.array([trades[k].get('regime', '') for k in keep]))
    np.savez_compressed(OUT + f'/q4_grid_{name}.npz', cfg=np.array([E.cfg_name(c) for c in E.GRID]), first=first, last=last, exit_min=exit_min, **usd, **meta)
    print(name, 'done', M['N'], 'trades', round(time.time() - t0, 1), 's', flush=True)
