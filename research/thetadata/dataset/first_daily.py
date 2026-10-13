import csv, datetime as dt, sys
CAL='/home/user/georgeredo/research/thetadata/index_tests/code/calendar_2017_2026.csv'
hol={r['date'] for r in csv.DictReader(open(CAL)) if r['type']=='full_close'}
def sessions(a,b):
    d=a; out=[]
    while d<=b:
        if d.weekday()<5 and d.isoformat() not in hol: out.append(d)
        d+=dt.timedelta(days=1)
    return out
END=dt.date(2026,10,9)
for sym in ('SPY','QQQ','IWM','SPXW'):
    exps={r['expiration'] for r in csv.DictReader(open(f'{sys.argv[1]}/expirations_{sym}.csv'))}
    ses=sessions(dt.date(2017,1,3),END)
    # walk backwards from END: first session (from the end) that is NOT an expiration
    missing=[d for d in ses if d.isoformat() not in exps]
    last_missing=missing[-1] if missing else None
    first_daily=next(d for d in ses if last_missing is None or d>last_missing)
    n=len([d for d in ses if d>=first_daily])
    # also report expirations present but not sessions (holiday-shifted?), and the few missing before first_daily
    extra=sorted(e for e in exps if first_daily.isoformat()<=e<=END.isoformat() and dt.date.fromisoformat(e) not in set(ses))
    print(sym, 'first_daily', first_daily, 'sessions_to_end', n, 'last_missing_session', last_missing, 'prior_missing_tail', [m.isoformat() for m in missing[-6:]], 'expirations_not_sessions', extra[:10], 'max_exp', max(exps))
    # weekday distribution in the 90 days before first_daily
    before=[d for d in ses if first_daily-dt.timedelta(days=60)<=d<first_daily]
    print('   before window:', ''.join('X' if d.isoformat() in exps else '.' for d in before))
