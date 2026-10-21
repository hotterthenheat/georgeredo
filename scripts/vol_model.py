#!/usr/bin/env python3
"""
vol_model.py — the FROZEN SPY t2 volatility model (Hypothesis E's refit of Hypothesis D's t2 GBM) and its live inputs,
for paper_tracker.py candidate 3. Nothing here fits anything: the models are the files scripts/models/<name>.txt
(LightGBM's text model), <name>.cuts.json and <name>.manifest.json, written once by scripts/models/freeze_t2_spy.py;
loading checks both files' sha256 against the manifest and refuses a mismatch.

SCORING without LightGBM: `TextBooster` reads the text model and walks its trees the way LightGBM's NumericalDecision
does (a NaN goes the node's default side when its missing type is NaN, else is read as 0.0; `fval <= threshold` goes
left), sums the leaves and takes the sigmoid. tests/test_paper_tracker.py checks it against LightGBM's own scores on
fixture rows (tests/fixtures/t2_feature_rows.json); where LightGBM is installed the freeze script's rows match to 1e-12.

THE FEATURES (exactly research_notes/Compass phase 2/hyp_d_vol_breakout/lib.py `session_rows`, read off live inputs):
  minute m = 0 is 09:30 New York; a 1-minute bar stamped t (UW's `start_time`; its `end_time` is t+1) closes at t+1, so
  bar index m holds the bar stamped 09:30 + (m−1) and c[m] is the price known at m — UW's convention is the one the
  model assumed (Theta's bars, also stamped at their open). spot = c carried forward. ret/aret k (k = 1, 5, 15, 30) in
  bps off spot[m−k]; rng k = (max h − min l over the bars closing m−k+1..m) / c[m] in bps; range_pos and or_pos (the
  first 30 bars' range, m > 30); day_move_atr = (c[m] − prev_close) / atr14, day_range_atr = the session's running
  range / atr14 — prev_close = the session before's last regular bar close and atr14 = the mean true range of the 14
  sessions before (the day table of hyp_d / the audit's sweeplib.build_day_table, rebuilt from the cached minute bars
  of the sessions before; at least 10 true ranges); rv_session = the RMS of the 1-minute log returns from the bar
  closing at 2 to m (m >= 3), in bps; vix = the VIX print at m (stamped m), vix_chg_open = vix[m] − the 09:31 print,
  vix_chg30 = vix[m] − vix[m−30], vix_chg_prev = vix[m] − the session before's last print at or before 16:00;
  straddle_rel = (call mid + put mid at the strike nearest spot among the five nearest with both sides quoted —
  bid, ask present, ask >= bid >= 0, ask > 0) / spot; implied30 = straddle_rel × sqrt(30 / (390 − m)); rel_vol = the
  volume of the five bars closing m−4..m over the median of the same five bars' volume in the up to 20 sessions before
  (at least 10, a missing minute counted as 0).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODELS_DIR = HERE / 'models'
CLOSE_M = 390
FULL, NOVIX = 't2_spy_full', 't2_spy_novix'
VIX_FEATS = ('vix', 'vix_chg_open', 'vix_chg30', 'vix_chg_prev')
NAN = float('nan')


def isnan(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


# ---- the frozen booster ----------------------------------------------------------------------------------------------------------

class TextBooster:
    """A LightGBM text model (binary objective, numerical splits) scored in plain Python"""

    def __init__(self, text: str):
        self.trees = []
        self.sigmoid = 1.0
        head, _, rest = text.partition('\nTree=')
        for line in head.splitlines():
            if line.startswith('objective='):
                for part in line.split()[1:]:
                    if part.startswith('sigmoid:'):
                        self.sigmoid = float(part.split(':')[1])
                if not line.split('=', 1)[1].startswith('binary'):
                    raise ValueError(f'not a binary model: {line}')
            if line.startswith('max_feature_idx='):
                self.n_features = int(line.split('=')[1]) + 1
            if line.startswith('num_class=') and line.strip() != 'num_class=1':
                raise ValueError('one class only')
        for block in ('Tree=' + rest).split('\nTree=')[0:]:
            if not block.strip() or block.startswith('end of trees'):
                continue
            kv = {}
            for line in block.splitlines():
                if line.startswith('end of trees'):
                    break
                if '=' in line:
                    k, v = line.split('=', 1)
                    kv[k] = v
            if 'leaf_value' not in kv:
                continue
            leaves = [float(x) for x in kv['leaf_value'].split()]
            if int(kv.get('num_leaves', '1')) == 1:
                self.trees.append(((), (), (), (), (), leaves))
                continue
            if kv.get('num_cat', '0') != '0':
                raise ValueError('categorical splits are not supported')
            self.trees.append((tuple(int(x) for x in kv['split_feature'].split()),
                               tuple(float(x) for x in kv['threshold'].split()),
                               tuple(int(x) for x in kv['decision_type'].split()),
                               tuple(int(x) for x in kv['left_child'].split()),
                               tuple(int(x) for x in kv['right_child'].split()), leaves))

    def raw(self, x: list) -> float:
        total = 0.0
        for feat, thr, dec, left, right, leaves in self.trees:
            if not feat:
                total += leaves[0]
                continue
            node = 0
            while node >= 0:
                f = x[feat[node]]
                f = NAN if f is None else float(f)
                miss = (dec[node] >> 2) & 3            # 0 none, 1 zero, 2 NaN
                if math.isnan(f) and miss != 2:
                    f = 0.0
                if (miss == 1 and abs(f) <= 1e-35) or (miss == 2 and math.isnan(f)):
                    node = left[node] if dec[node] & 2 else right[node]
                elif f <= thr[node]:
                    node = left[node]
                else:
                    node = right[node]
            total += leaves[~node]
        return total

    def predict(self, x: list) -> float:
        return 1.0 / (1.0 + math.exp(-self.sigmoid * self.raw(x)))


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class FrozenModel:
    def __init__(self, name: str, manifest: dict, booster: TextBooster, cuts: list):
        self.name, self.manifest, self.booster, self.cuts = name, manifest, booster, cuts
        self.features = list(manifest['features'])
        self.sha = manifest['model_sha256']

    @classmethod
    def load(cls, name: str, models_dir: Path = MODELS_DIR) -> 'FrozenModel':
        d = Path(models_dir)
        man = json.loads((d / f'{name}.manifest.json').read_text(encoding='utf-8'))
        mf, cf = d / man['model_file'], d / man['cuts_file']
        if sha256_of(mf) != man['model_sha256']:
            raise ValueError(f'{mf.name}: sha256 differs from the manifest — the frozen model was changed')
        if sha256_of(cf) != man['cuts_sha256']:
            raise ValueError(f'{cf.name}: sha256 differs from the manifest — the frozen cuts were changed')
        cuts = json.loads(cf.read_text(encoding='utf-8'))['cuts']
        if len(cuts) != 9 or cuts != sorted(cuts):
            raise ValueError(f'{cf.name}: nine ascending cuts expected')
        b = TextBooster(mf.read_text(encoding='utf-8'))
        if b.n_features != len(man['features']):
            raise ValueError(f'{name}: the model has {b.n_features} features, the manifest {len(man["features"])}')
        return cls(name, man, b, cuts)

    def decile(self, score: float) -> int:
        """hyp_d model.decile_of: clip(searchsorted(cuts, score, side='right'), 0, 9) + 1"""
        n = sum(1 for c in self.cuts if c <= score)
        return min(max(n, 0), 9) + 1

    def score(self, feats: dict) -> tuple[float, int]:
        p = self.booster.predict([feats.get(f, NAN) for f in self.features])
        return p, self.decile(p)


# ---- bars ------------------------------------------------------------------------------------------------------------------------------

def _num(v):
    if v is None or v == '':
        return NAN
    try:
        x = float(v)
    except (TypeError, ValueError):
        return NAN
    return x if math.isfinite(x) else NAN


def _parse_utc(v) -> dt.datetime | None:
    if not isinstance(v, str) or not v:
        return None
    s = v.strip().replace('Z', '+00:00')
    try:
        t = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def bars_from_uw(rows: list, day: str, before_m: int | None = None) -> dict:
    """UW /ohlc/1m rows → {'o','h','l','c','v'}: lists of 391 floats indexed by the minute the bar CLOSES (1..390; index
    0 NaN), regular-session rows (`market_time` 'r') of `day` alone. A bar is placed by its start_time (New York) + 1
    minute. `before_m`: keep only bars closing at or before it (a live capture never reads a bar still forming)."""
    from zoneinfo import ZoneInfo
    ny = ZoneInfo('America/New_York')
    arr = {k: [NAN] * 391 for k in 'ohlcv'}
    n = 0
    last = None
    for r in rows:
        if r.get('market_time') not in (None, 'r'):
            continue
        t = _parse_utc(r.get('start_time'))
        if t is None:
            continue
        tn = t.astimezone(ny)
        if tn.strftime('%Y-%m-%d') != day:
            continue
        m = tn.hour * 60 + tn.minute - 570 + 1
        if m < 1 or m > CLOSE_M or (before_m is not None and m > before_m):
            continue
        c = _num(r.get('close'))
        if math.isnan(c):
            continue
        arr['o'][m], arr['h'][m], arr['l'][m], arr['c'][m], arr['v'][m] = _num(r.get('open')), _num(r.get('high')), _num(r.get('low')), c, _num(r.get('volume'))
        n += 1
        if last is None or m > last:
            last = m
    arr['n'] = n
    arr['last_m'] = last
    return arr


def ffill(a: list) -> list:
    out, cur = [], NAN
    for x in a:
        if not isnan(x):
            cur = x
        out.append(cur)
    return out


def _nanmax(xs):
    v = [x for x in xs if not isnan(x)]
    return max(v) if v else NAN


def _nanmin(xs):
    v = [x for x in xs if not isnan(x)]
    return min(v) if v else NAN


def day_summary(bars: dict) -> dict | None:
    """One row of the audit's day table (sweeplib.build_day_table) from a whole session's bars: high, low, close
    (the last regular bar's), half, and the volume by minute (missing → 0). None under 30 bars (read_bars)."""
    if bars.get('n', 0) < 30:
        return None
    last = bars.get('last_m') or 0
    half = last < (15 * 60 - 570 + 1)          # read_bars: the last bar's stamp before 15:00
    close_m = 210 if half else CLOSE_M
    h, l, c = bars['h'][1:close_m + 1], bars['l'][1:close_m + 1], bars['c'][1:close_m + 1]
    cs = [x for x in c if not isnan(x)]
    if not cs:
        return None
    return {'high': _nanmax(h), 'low': _nanmin(l), 'close': cs[-1], 'half': half,
            'volume': [0.0 if isnan(x) else float(x) for x in bars['v'][:391]]}


def day_table_inputs(prior: list) -> dict:
    """prior: the sessions before today, oldest first, each a day_summary or None (a session missing from the cache).
    → prev_close (the session just before), atr14 (the mean true range of the 14 before, >= 10 present — a true range
    needs its own session and the one before it), the volume reference (the up to 20 most recent present sessions)."""
    out = {'prev_close': NAN, 'atr14': NAN, 'atr_n': 0, 'vol_ref': [], 'missing': sum(1 for p in prior if p is None)}
    if prior and prior[-1] is not None:
        out['prev_close'] = prior[-1]['close']
    trs = []
    for i in range(max(0, len(prior) - 14), len(prior)):
        s = prior[i]
        if s is None:
            continue
        pc = prior[i - 1]['close'] if i >= 1 and prior[i - 1] is not None else None
        parts = [s['high'] - s['low']] + ([abs(s['high'] - pc), abs(s['low'] - pc)] if pc is not None else [])
        trs.append(max(parts))
    out['atr_n'] = len(trs)
    if len(trs) >= 10:
        out['atr14'] = sum(trs) / len(trs)
    out['vol_ref'] = [p['volume'] for p in prior[-20:] if p is not None]
    return out


def _median(xs):
    v = sorted(x for x in xs if not isnan(x))
    if not v:
        return NAN
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def atm_straddle(quotes: dict, spot: float) -> tuple[float | None, float]:
    """hyp_d atm_strike: quotes {strike: (call (bid, ask) | None, put (bid, ask) | None)} — a side counts when bid and
    ask are there, ask >= bid >= 0 and ask > 0. The strike list is every strike with a side counted; j = the nearest
    to spot (a tie: the lower); of the five strikes j−2..j+2 nearest first, the first with both sides. → (K, mid sum)"""
    def ok(q):
        return q is not None and not isnan(q[0]) and not isnan(q[1]) and q[1] >= q[0] >= 0 and q[1] > 0
    strikes = sorted(k for k, (c, p) in quotes.items() if ok(c) or ok(p))
    if not strikes or isnan(spot):
        return None, NAN
    j = min(range(len(strikes)), key=lambda i: (abs(strikes[i] - spot), i))
    for jj in sorted(range(max(0, j - 2), min(len(strikes), j + 3)), key=lambda q: abs(strikes[q] - spot)):
        c, p = quotes[strikes[jj]]
        if ok(c) and ok(p):
            return strikes[jj], 0.5 * (c[0] + c[1]) + 0.5 * (p[0] + p[1])
    return None, NAN


def vix_array(prints: list) -> list:
    """[(minute m 0..390 — the print stamped m, price), ...] → 391 prices, carried forward (sweeplib.read_prints)"""
    a = [NAN] * 391
    for m, px in prints:
        if 0 <= m <= CLOSE_M and not isnan(px) and px > 0:
            a[m] = px
    return ffill(a)


def features_at(m: int, bars: dict, table: dict, vix: list | None, vix_prev: float | None, straddle: float) -> dict:
    """The 25 features at minute m (hyp_d lib.session_rows), from today's bars to m, the day-table inputs, the VIX
    array (or None), the session before's last VIX print and the ATM straddle (mid sum) read at m"""
    o, h, l, c, v = bars['o'], bars['h'], bars['l'], bars['c'], bars['v']
    spot = ffill(c)
    Sm = spot[m]
    f = {'m': float(m)}
    for k in (1, 5, 15, 30):
        p = spot[m - k] if m - k >= 1 else NAN
        r = (Sm / p - 1.0) * 1e4 if not isnan(p) and p > 0 and not isnan(Sm) else NAN
        f[f'ret{k}'] = r
        f[f'aret{k}'] = abs(r) if not isnan(r) else NAN
        lo = max(1, m - k + 1)
        f[f'rng{k}'] = (_nanmax(h[lo:m + 1]) - _nanmin(l[lo:m + 1])) / c[m] * 1e4 if not isnan(c[m]) else NAN
    runhi = _nanmax(h[:m + 1])
    runlo = _nanmin(l[:m + 1])
    runhi = -math.inf if isnan(runhi) else runhi
    runlo = math.inf if isnan(runlo) else runlo
    f['range_pos'] = (c[m] - runlo) / (runhi - runlo) if runhi > runlo and not isnan(c[m]) else NAN
    orh, orl = _nanmax(h[1:31]), _nanmin(l[1:31])
    f['or_pos'] = (c[m] - orl) / (orh - orl) if (m > 30 and not isnan(orh) and not isnan(orl) and orh > orl and not isnan(c[m])) else NAN
    atr = table.get('atr14', NAN)
    atr = atr if not isnan(atr) and atr > 0 else NAN
    pc = table.get('prev_close', NAN)
    f['day_move_atr'] = (c[m] - pc) / atr if not (isnan(c[m]) or isnan(pc) or isnan(atr)) else NAN
    f['day_range_atr'] = (runhi - runlo) / atr if not isnan(atr) and math.isfinite(runhi - runlo) else NAN
    if m >= 3:
        sq = []
        for i in range(2, m + 1):
            a, b = c[i], c[i - 1]
            if not (isnan(a) or isnan(b)) and a > 0 and b > 0:
                sq.append(math.log(a / b) ** 2)
        f['rv_session'] = math.sqrt(sum(sq) / len(sq)) * 1e4 if sq else NAN
    else:
        f['rv_session'] = NAN
    if vix is not None:
        vm = vix[m]
        first = vix[1] if not isnan(vix[1]) else vix[0]
        f['vix'] = vm
        f['vix_chg_open'] = vm - first if not (isnan(vm) or isnan(first)) else NAN
        b30 = vix[max(m - 30, 1)]
        f['vix_chg30'] = vm - b30 if not (isnan(vm) or isnan(b30)) else NAN
        f['vix_chg_prev'] = vm - vix_prev if not (isnan(vm) or vix_prev is None or isnan(vix_prev)) else NAN
    else:
        for k in VIX_FEATS:
            f[k] = NAN
    ref = table.get('vol_ref') or []
    if len(ref) >= 10:
        cur = sum(x for x in v[m - 4:m + 1] if not isnan(x))
        r = _median([sum(row[m - 4:m + 1]) for row in ref])
        f['rel_vol'] = cur / r if not isnan(r) and r > 0 else NAN
    else:
        f['rel_vol'] = NAN
    st = straddle
    f['straddle_rel'] = st / Sm if not (isnan(st) or isnan(Sm)) else NAN
    f['implied30'] = f['straddle_rel'] * math.sqrt(30.0 / (CLOSE_M - m)) if not isnan(f['straddle_rel']) else NAN
    f['_spot'] = Sm
    return f


# ---- VIX from the owner's Theta Terminal -------------------------------------------------------------------------------------------

THETA_BASE = 'http://127.0.0.1:25503/v3'    # never "localhost" (the terminal's error 476); the terminal holds the key


class ThetaIndex:
    """GET /v3/index/history/price?symbol=VIX&date=YYYYMMDD&interval=1m&format=ndjson from the terminal on 127.0.0.1
    (no key on the request — the terminal holds it; no proxy). Rows: {"timestamp": "2026-10-13T09:30:00.000" (New York
    wall clock), "price": ...}; a price of 0 is no print. → [(m, price)] or None (the error in .error)"""

    def __init__(self, base: str = THETA_BASE, timeout_s: float = 10.0, opener=None):
        self.base = base.rstrip('/')
        self.timeout_s = timeout_s
        self.opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.error: str | None = None
        self.calls = 0

    def prints(self, symbol: str, day: str) -> list | None:
        q = urllib.parse.urlencode({'symbol': symbol, 'date': day.replace('-', ''), 'interval': '1m', 'format': 'ndjson'})
        url = f'{self.base}/index/history/price?{q}'
        self.calls += 1
        try:
            with self.opener.open(urllib.request.Request(url, headers={'Accept': 'application/x-ndjson'}), timeout=self.timeout_s) as res:
                body = res.read().decode('utf-8', 'replace')
        except Exception as e:  # refused, timeout, 4xx/5xx (472 = no data)
            self.error = f'{type(e).__name__}: {str(e)[:120]}'
            return None
        out = []
        lines = body.splitlines()
        if body.lstrip().startswith('{') and len(lines) == 1:
            try:
                obj = json.loads(body)
                rows = obj.get('response') or obj.get('rows') or [obj]
                lines = [json.dumps(r) for r in rows]
            except Exception:
                pass
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            ts, px = r.get('timestamp'), _num(r.get('price'))
            if not isinstance(ts, str) or len(ts) < 16 or ts[:10] != day:
                continue
            m = int(ts[11:13]) * 60 + int(ts[14:16]) - 570
            if 0 <= m <= CLOSE_M and not isnan(px) and px > 0:
                out.append((m, px))
        self.error = None if out else 'no VIX prints in the answer'
        return out or None
