"""The management-policy grid of the lifecycle protocol §5, as named parameter vectors for lc.position.

Every policy has an id, a family (M0 ... M13), a short name and its parameters. `stage1()` is the baseline set every
setup x structure cell is run under; `grid()` is the full pre-registered grid for the management research. The count of
configurations evaluated is the length of these lists times the cells they run on (logged per run)."""
from __future__ import annotations
import itertools
from . import position as ps

CUT = 380      # 15:50

def _p(**kw): return ps.params(CUTOFF=kw.pop('CUTOFF', CUT), **kw)

def stage1():
    return [
        ('M0_cutoff', 'M0', _p()),
        ('M0_expiry', 'M0', _p(CUTOFF=-1)),
        ('M1_t30', 'M1', _p(TIME_EXIT=30)),
        ('M1_t60', 'M1', _p(TIME_EXIT=60)),
        ('M2_s35_t50', 'M2', _p(STOP=0.35, TARGET=0.50)),
        ('M5_thesis1m', 'M5', _p(THESIS=1)),
        ('M13_tp50_s2', 'M13', _p(CREDIT_TP=0.5, CREDIT_STOP=2.0)),
    ]

def grid():
    out = list(stage1())
    seen = {n for n, _, _ in out}
    def add(name, fam, **kw):
        if name in seen: return
        seen.add(name); out.append((name, fam, _p(**kw)))
    # M1 time exits
    for t in (15, 30, 60, 120): add(f'M1_t{t}', 'M1', TIME_EXIT=t)
    # M2 stop x target
    for s, t in itertools.product((0.20, 0.35, 0.50, -1), (0.20, 0.50, 1.00, -1)):
        if s < 0 and t < 0: continue
        add(f'M2_s{int(s * 100) if s > 0 else "none"}_t{int(t * 100) if t > 0 else "none"}', 'M2', STOP=s, TARGET=t)
    # M3 partials and a runner (stop 35 % on the whole position until the first partial; the runner exits by its rule)
    for f1, a1 in itertools.product((0.25, 0.50), (0.20, 0.50)):
        for second in (None, (0.25, 0.50), (0.25, 1.00)):
            if second and second[1] <= a1: continue
            for rx in ('trail20', 'trail35', 'struct', 'time60'):
                kw = dict(STOP=0.35, P1_FRAC=f1, P1_AT=a1)
                if second: kw.update(P2_FRAC=second[0], P2_AT=second[1])
                if rx.startswith('trail'): kw.update(TRAIL_ARM=a1, TRAIL_GIVE=int(rx[5:]) / 100)
                elif rx == 'struct': kw.update(RUNNER_STRUCT=1)
                else: kw.update(RUNNER_TIME=60)
                sec = f'_p2{int(second[0] * 100)}at{int(second[1] * 100)}' if second else ''
                add(f'M3_p{int(f1 * 100)}at{int(a1 * 100)}{sec}_{rx}', 'M3', **kw)
    # M4 trailing only (stop 35 % until armed)
    for arm, give in itertools.product((0.20, 0.50), (0.15, 0.25, 0.40)):
        add(f'M4_arm{int(arm * 100)}_give{int(give * 100)}', 'M4', STOP=0.35, TRAIL_ARM=arm, TRAIL_GIVE=give)
    # M5 thesis
    add('M5_thesis1m', 'M5', THESIS=1); add('M5_thesis5m', 'M5', THESIS=2); add('M5_reduce1m', 'M5', THESIS=3)
    add('M5_thesis1m_s35', 'M5', THESIS=1, STOP=0.35)
    # M6 add on confirmation (with the M2 35/50 frame and without)
    for k, mx in itertools.product((1.0, 2.0), (1, 2)):
        add(f'M6_k{int(k)}_max{mx}', 'M6', ADD_K=k, ADD_MAX=mx)
        add(f'M6_k{int(k)}_max{mx}_s35t50', 'M6', ADD_K=k, ADD_MAX=mx, STOP=0.35, TARGET=0.50)
    # M7 double down
    for d in (0.25, 0.40):
        add(f'M7_dd{int(d * 100)}', 'M7', DD_AT=d, DD_MAX=1)
        add(f'M7_dd{int(d * 100)}_thesis', 'M7', DD_AT=d, DD_MAX=1, THESIS=1)
    # M8 scale in
    add('M8_thirds', 'M8', SCALE=1); add('M8_thirds_s35t50', 'M8', SCALE=1, STOP=0.35, TARGET=0.50)
    # M9 warnings: each alone, reduce or exit
    for bit, wname in ((1, 'W1rsi'), (2, 'W2iv'), (4, 'W3spread'), (8, 'W4adverse')):
        add(f'M9_{wname}_reduce', 'M9', WARN_MASK=bit, WARN_ACTION=1)
        add(f'M9_{wname}_exit', 'M9', WARN_MASK=bit, WARN_ACTION=2)
    # M12 straddle/strangle legs
    for tgt in (0.25, 0.50): add(f'M12_both_t{int(tgt * 100)}', 'M12', TARGET=tgt)
    for k in (0.5, 1.0): add(f'M12_leg_k{str(k).replace(".", "")}_trail25', 'M12', LEG_K=k, LEG_TRAIL=0.25)
    # M13 short premium
    for tp, st in itertools.product((0.25, 0.50, 0.75, -1), (1.5, 2.0, 3.0, -1)):
        if tp < 0 and st < 0: continue
        add(f'M13_tp{int(tp * 100) if tp > 0 else "none"}_s{str(st).replace(".", "") if st > 0 else "none"}', 'M13', CREDIT_TP=tp, CREDIT_STOP=st)
    add('M13_tp50_touch', 'M13', CREDIT_TP=0.5, STRIKE_TOUCH=1)
    add('M13_expiry', 'M13', CUTOFF=-1)
    add('M13_tp50_expiry', 'M13', CUTOFF=-1, CREDIT_TP=0.5)
    return out

FAMILY_FOR_STRUCTURE = {
    # which families apply to which structures (others are not run on them)
    'debit': {'M0', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9'},
    'straddle': {'M0', 'M1', 'M2', 'M12'},
    'credit': {'M0', 'M1', 'M5', 'M13'},
}

def kind_of(code: str) -> str:
    if code in ('STR', 'STG'): return 'straddle'
    if code in ('CPS', 'CSP'): return 'credit'
    return 'debit'
