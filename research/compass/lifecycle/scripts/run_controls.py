"""Amendment L-A2: the setup-versus-random comparison rerun with controls that use nothing the event did not know.
  ctrl_after  a random minute at or after the event, same session, same direction (5 seeds)
  ctrl_flip   the event's minute, the opposite direction (mirrored structures)
Stage-1 policies, daily sums, development and validation only. With 'holdout' as the second argument, ctrl_after is run
on the hold-out for the finalists' setups and structures alone (a post-hoc look at R2, reported as such)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lc import runner, policies as pol, chainmat as cm
roots = sys.argv[1].split(',')
which = sys.argv[2] if len(sys.argv) > 2 else 'devval'
log = lambda m: print(time.strftime('%H:%M:%S'), m, flush=True)
for root in roots:
    if which == 'devval':
        for mode in ('after', 'flip'):
            runner.run_root(root, f'ctrl_{mode}', pol.stage1(), mode='daily', log=log, ctrl_mode=mode)
    else:
        ss = [d for d in cm.sessions_0dte(root) if d >= runner.HOLDOUT_START]
        fin = ('M13_tpnone_s15', 'M13_tpnone_s20', 'M0_expiry', 'M13_tp25_snone')   # the six finalists' policies
        runner.run_root(root, 'ctrl_after_holdout', [p for p in pol.grid() if p[0] in fin], sessions=ss, mode='daily', include_holdout=True, log=log, ctrl_mode='after',
                        setups=('QS', 'BOp', 'BOr', 'TPp', 'MSS'), structures=('CSP', 'CPS'))
