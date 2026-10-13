"""Edge-case probe for the NBBO study: one ThetaData request per case, sequential. Run:
  set -a; . "$SP/secrets/research.env"; set +a; python3 -I nbbo_probe.py"""
import sys, os, datetime, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nbbo_common as N

rows = N.load_rows()
def pick(pred, n=1):
    out = [r for r in rows if pred(r)]
    return out[:n]
cases = []
cases += pick(lambda r: r['kind'] == 'opt' and r['t_root'] == 'SPXW' and r['label'] == 'E1')
cases += pick(lambda r: r['kind'] == 'opt' and r['t_strike'].endswith('.5'))
cases += pick(lambda r: r['kind'] == 'opt' and r['t_root'] == 'NDXP')
cases += pick(lambda r: r['kind'] == 'opt' and r['t_root'] == 'RUTW')
cases += pick(lambda r: r['kind'] == 'opt' and r['t_root'] == 'SPX')
cases += pick(lambda r: r['entry_dt'].time() < datetime.time(9, 30), 3)
cases += pick(lambda r: r['exit_dt'] is not None and r['exit_dt'].time() >= datetime.time(16, 0), 3)
cases += pick(lambda r: r['kind'] == 'stk')
cases += pick(lambda r: r['label'] == 'paper')
c = N.make_client(); print('auth OK', flush=True)
for r in cases:
    for which, t in (('entry', r['entry_dt']), ('exit', r['exit_dt'])):
        if t is None: continue
        ck = N.contract_key(r, t.strftime('%Y-%m-%d')); s, e = N.window_for(t)
        st = N.fetch_one(c, ck, s, e)
        px = r['entry_px'] if which == 'entry' else r['exit_px']
        _, q = N.load_window(ck, s, e)
        s0 = N.floor_s(t); q0 = q.get(s0); q1 = q.get(s0 + datetime.timedelta(seconds=1))
        print(f"{r['label']:5s} {r['trade_id']} {r['t_root']:5s} {r.get('t_strike',''):7s} {r.get('t_right',''):4s} {which:5s} {t.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} reported={px} | rows={st.get('rows')} ok={st.get('ok')} err={st.get('error','')[:120]} ms={st.get('ms')} | q0={q0} q1={q1}", flush=True)
