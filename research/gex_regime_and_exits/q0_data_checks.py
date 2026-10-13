"""Data definition checks: gex-levels snapshot time-of-day and `source` field over all cached records; spot-exposures field behaviour on one day."""
import glob, gzip, json, os, collections
from common import *
src = collections.Counter(); tm = collections.Counter(); rows = []
for f in sorted(glob.glob(os.environ.get('BT_CACHE', BT + '/cache') + '/*gex-levels*')):
    d = json.load(gzip.open(f, 'rt')).get('data') or {}
    src[d.get('source')] += 1; tm[(d.get('time') or '')[11:16]] += 1
    rows.append(dict(file=os.path.basename(f), date=d.get('date'), time=d.get('time'), source=d.get('source'), gamma_flip=d.get('gamma_flip'), call_wall=d.get('call_wall'), put_wall=d.get('put_wall'), gamma_magnet=d.get('gamma_magnet')))
write_csv(OUT + '/q0_gex_levels_meta.csv', rows)
print('gex-levels records', len(rows), 'source', dict(src), 'snapshot time (UTC HH:MM)', tm.most_common(6))
print('all snapshots at/after 18:00Z (post 14:00 ET):', all((r['time'] or '')[11:13] >= '18' for r in rows))
d = data.get('stock/SPY/spot-exposures', {'date': '2026-04-06'})['data']; d = sorted(d, key=lambda r: r['start_time'])
F = ['gamma_per_one_percent_move_oi', 'gamma_per_one_percent_move_vol', 'gamma_per_one_percent_move_dir', 'charm_per_one_percent_move_oi', 'vanna_per_one_percent_move_oi']
pre = [r for r in d if r['start_time'] < '2026-04-06T13:30:00']; rth = [r for r in d if r['start_time'] >= '2026-04-06T13:30:00']
print('spot-exposures 2026-04-06 rows', len(d), 'first', d[0]['start_time'], 'last', d[-1]['start_time'], '| pre-RTH rows with vol/dir == 0:', sum(1 for r in pre if float(r[F[1]]) == 0 and float(r[F[2]]) == 0), '/', len(pre), '| RTH rows with vol != 0:', sum(1 for r in rth if float(r[F[1]]) != 0), '/', len(rth))
print('keys', sorted(d[0].keys()))
