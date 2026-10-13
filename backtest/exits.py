"""Exit engines on 1-minute option bars. All return a list of legs [(fraction, exit_price, exit_time, reason)]."""
import datetime
def _close_time(d): return d.replace(hour=15, minute=55, second=0, microsecond=0)

def simulate(bars, entry_idx, entry_px, engine, params=None):
    p = dict(stop=-0.25, t1=0.25, t2=0.45, be_arm=0.06, guard_arm=0.15, guard_giveback=0.35, time_stop_min=30, hard_close=True)
    p.update(params or {})
    legs = []; remaining = 1.0; hwm = 0.0; half_done = False; be_active = False
    e_t = bars[entry_idx]['t']; last = None
    for b in bars[entry_idx + 1:]:
        last = b
        if b['t'] >= _close_time(b['t']): break
        r_h = b['h'] / entry_px - 1; r_l = b['l'] / entry_px - 1; r_c = b['c'] / entry_px - 1
        held = (b['t'] - e_t).total_seconds() / 60
        if engine == 'hold': continue
        if engine == 'bracket':
            if r_l <= p['stop']: legs.append((remaining, entry_px * (1 + p['stop']), b['t'], 'STOP')); remaining = 0; break
            if r_h >= p['t1']: legs.append((remaining, entry_px * (1 + p['t1']), b['t'], 'TARGET')); remaining = 0; break
            continue
        # ladder / trail engines share the protective logic
        stop_lvl = p['stop']
        if be_active: stop_lvl = max(stop_lvl, 0.0)
        if hwm >= p['guard_arm']: stop_lvl = max(stop_lvl, hwm * (1 - p['guard_giveback']))
        if r_l <= stop_lvl:
            legs.append((remaining, entry_px * (1 + stop_lvl), b['t'], 'STOP' if stop_lvl == p['stop'] else ('BREAKEVEN' if stop_lvl == 0.0 else 'TRAIL'))); remaining = 0; break
        if engine == 'ladder':
            if not half_done and r_h >= p['t1']:
                legs.append((remaining * 0.5, entry_px * (1 + p['t1']), b['t'], 'T1')); remaining *= 0.5; half_done = True
            if half_done and r_h >= p['t2']:
                legs.append((remaining, entry_px * (1 + p['t2']), b['t'], 'T2')); remaining = 0; break
        hwm = max(hwm, r_h)
        if hwm >= p['be_arm']: be_active = True
        if p['time_stop_min'] and held >= p['time_stop_min'] and r_c <= 0 and engine in ('ladder', 'trail'):
            legs.append((remaining, b['c'], b['t'], 'TIME_STOP')); remaining = 0; break
    if remaining > 0 and last is not None:
        legs.append((remaining, last['c'], last['t'], 'CLOSE'))
    return legs
