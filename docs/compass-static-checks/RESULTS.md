# Compass static checks — results of the demonstration run (2026-10-21)

**What this is.** The three scripts in this folder are the module 15–16 verification of
`docs/compass-core-spec-v2.md` (cents normalization, dead-code quarantine, Helix isolation). They take a code root
as an argument. **The Compass bot's own code is not in any repository on this machine**, so the run below is a
demonstration on the terminal's source, `/home/user/3abida/src` (Slayer, read-only; nothing there was edited). The
bot's root must be passed when it exists; every line below is about the terminal, not the bot.

Run from this folder (Python 3, standard library only; `-I` isolates the interpreter from the scanned tree):

```
python3 -I check_cents.py           <root> --boundary <glob> ... --selftest
python3 -I check_dead_code.py       <root> [--names A,B --value A=0.35 --names-file removed.txt]
python3 -I check_helix_isolation.py <root> --decision <glob> ... [--telemetry <glob|name> ... --field <regex> ...]
```

Each exits 0 on a pass and 1 on a finding; `--json` prints the full result.

## 1. check_cents.py — one price unit at the vendor boundary

Boundary declared for the terminal: `data/feed/uw.ts`, `data/feed/client.ts` (UW's numeric strings read by `num()`),
`data/feed/theta.ts`, `data/feed/massive.ts`. The round-trip harness ran on the reference engine with the audit's
known contract (SPY 20261030 808 C at 0.55 / 0.56 on 2026-10-09): 16 of 16 figures to the cent, and the float32 case
behind spec 0.1 reproduced (1.05 stored as float32 reads back 1.0499999523; `round(x, 4)` restores it).

Reading the 31 "price-unit" findings on the terminal (a human reads this list; that is the check's job):
- **One genuine second decoder of a vendor unit outside the boundary:** `data/feed/trailModel.ts:137` reads the OCC
  option symbol's strike (`× 1000`) with its own `/ 1000` — the same conversion `data/feed/uw.ts:1057` does inside
  the boundary. Under spec 15.1 that decode belongs in one place.
- The rest are not unit changes and are named by a price-like word the classifier cannot tell from a time or a
  share: epoch seconds ↔ milliseconds on a bar's `open` / `close` / `time` (NetFlowPane 136, RecapWatcher 146,
  levelview 59–60, replayFrame 149/409/410, oiChange 100, journalFigures 223, StrikeChart 5702), SVG bar widths out of
  a 0–100 figure (TraceGuide 129/990, StocksGuide 53/129), an implied vol in vol points (VolCurves 60), rho per 1%
  (weigherDesk 254), a percent change or distance (CompareTapes 63, dossier 602/603/649), a 0–100 figure (trace 326),
  the contract multiplier in exposure arithmetic (simulator 229/542/543/588/589: OI × 100 × greek × spot — the
  house's own units), intrinsic × 100 to dollars a contract (paper/feed 195), and a dollar floor printed in
  thousands (Watchers 509, Windows 449, MultiLeg 608).
- The classes listed apart (not findings): cent-rounding 52, cents-keyed map 113 (the simulator keys its book by
  integer cents — dollars in, dollars out), contract-multiplier 77, lot-rounding 3, percent 296, time-ms 150,
  vol-points, other 125, comments 9.

Result on the terminal: **1 finding to act on (trailModel's OCC decode), 30 to read and dismiss**; exit code 1.

```
check_cents: /home/user/3abida/src
  boundary globs: ['data/feed/uw.ts', 'data/feed/client.ts', 'data/feed/theta.ts', 'data/feed/massive.ts']
  hits by class: boundary 3, cent-rounding 52, cents-keyed-map 113, comment 9, contract-multiplier 77, lot-rounding 3, other 125, percent 296, price-unit 31, time-ms 150, vol-points 30
  FINDINGS (price-unit conversions outside the boundary): 31
    components/trace/NetFlowPane.tsx:136: const first = Math.floor(s.open / 1000);
    components/trace/TraceGuide.tsx:129: <rect x={12} y={r.y - 6} width={70 * (r.ask / 100)} height={4} rx={2} fill={BULL} />
    components/trace/TraceGuide.tsx:990: <rect x={296} y={r.y - 6} width={(r.c / 100) * 64} height={3} rx={1.5} fill={r.ink} opacity={0.8} />
    components/review/RecapWatcher.tsx:146: book: f.cols.map(([m, spot, cells]): GexSnapshot => ({ time: m / 1000, spot, rebuilt: true, levels: cells.map(([strike, value]) => ({ strike, value })) })),
    components/weigher/VolCurves.tsx:60: const iv = contractIvFor(ticker, spot, 'C') * 100;
    components/record/StocksGuide.tsx:53: <rect x={x} y={y} width={(w * v) / 100} height={4} rx={2} fill={v > 50 ? BULL : BEAR} fillOpacity={v > 50 ? 1 : 0.7} />
    components/record/StocksGuide.tsx:129: <rect x={10} y={r.y - 6} width={140 * (r.v / 100)} height={4} rx={2} fill={r.ink} fillOpacity={r.ink === BULL ? 1 : 0.7} />
    components/gex/StrikeChart.tsx:5702: {k(beadCard.strike)} · {cellBar > 60 ? barSpanLabel(beadCard.time, beadCard.time + cellBar) : nyClockOf(beadCard.time * 1000, { zone: true })}
    components/gex/CompareTapes.tsx:63: for (const bar of bars) m.set(bar.time, { p: (bar.close / open0 - 1) * 100, c: bar.close });
    data/oiChange.ts:100: return fromLevels(ticker, spot, a.levels, b.levels, nyDay(lastEnd * 1000), nyDay(beforeEnd * 1000));
    data/weigherDesk.ts:254: (((right === 'C' ? 1 : -1) * strike * t * Math.exp(-r * t) * (right === 'C' ? nd2 : 1 - nd2)) / 100).toFixed(4)
    data/levelview.ts:59: const lo = open / 1000;
    data/levelview.ts:60: const hi = close / 1000;
    data/replayFrame.ts:149: if (guard) pitRead(guard, 'day bar', sessionSpan(d).close * 1000);
    data/replayFrame.ts:409: const open = span.first * 1000;
    data/replayFrame.ts:410: const close = span.close * 1000;
    data/review/journalFigures.ts:223: const by = groupBy(rows, r => String(Math.floor(nyAt(instantOf(r, r.t.opened) * 1000).minutes / 60)));
    data/paper/feed.ts:195: const itm = past(c.strike) * 100;
    data/feed/trailModel.ts:137: return { root: m[1], expiry: `20${m[2]}-${m[3]}-${m[4]}`, right: m[5] as 'C' | 'P', strike: Number(m[6]) / 1000 };
    data/feed/dossier.ts:602: const away = Number.isFinite(px) && px > 0 ? ((r.strike - px) / px) * 100 : NaN;
    data/feed/dossier.ts:603: const be = Number.isFinite(px) && px > 0 && Number.isFinite(mid) ? (right === 'C' ? ((r.strike + mid - px) / px) * 100 : ((px - (r.strike - mid)) / px) * 100) : NaN;
    data/feed/dossier.ts:649: const moves = reported.map(x => (x.postMove1d == null ? NaN : x.postMove1d * 100));
    data/feed/trace.ts:326: flowScore: Number.isFinite(width) ? Math.round((fillPos * 2 - 1) * 100) : 0,
    core/simulator.ts:229: const refWall = (20000 * 2.4 * 100 * price * price * 0.01 * 0.54) / (2.5066 * denom);
    core/simulator.ts:542: const dex = callOI * 100 * u.deltaCall * spot * -0.55 + putOI * 100 * u.deltaPut * spot * -0.53;
    core/simulator.ts:543: const vex = (callOI * -0.55 + putOI * -0.53) * 100 * u.vega * spot;
    core/simulator.ts:588: const dex = entry.callOI * 100 * u.deltaCall * spot * -0.55 + entry.putOI * 100 * u.deltaPut * spot * -0.53;
    core/simulator.ts:589: const vex = (entry.callOI * -0.55 + entry.putOI * -0.53) * 100 * u.vega * spot;
    pages/trace/Watchers.tsx:509: sub={`${activeRule ? `${activeRule.label} — ${activeRule.phrase} · newest first` : "Every reason a contract is flagged — the desk's and yours, newest first"}${onFeed ? ` · flags of $${ALERT_FL
    pages/trace/Windows.tsx:449: sub={`${activeCut.label} — ${activeCut.hint}${onFeed ? ` · prints of $${WINDOW_FLOOR / 1000}K and up` : ''} · a row opens the contract's card`}
    pages/trace/MultiLeg.tsx:608: sub={`${activeKind ? `${activeKind.label} — ${activeKind.read}` : 'Every structure on the tape today, newest first'}${onFeed ? ` · orders of $${SPREAD_FLOOR / 1000}K and up` : ''} · a row open
round trip — SPY 20261030 808 C at 0.55 / 0.56 on 2026-10-09 (ThetaData bulk file):
  [ok ] load bid (dollars a share): got 0.55 want 0.55 ($)
  [ok ] load ask (dollars a share): got 0.56 want 0.56 ($)
  [ok ] pick: strike (dollars): got 808.0 want 808.0 ($)
  [ok ] pick: ask (dollars a share): got 0.56 want 0.56 ($)
  [ok ] entry debit, one contract ($): got 56.0 want 56.0 ($)
  [ok ] backstop 0.68 x ask (dollars a share): got 0.3808 want 0.3808 ($)
  [ok ] T1 1.25 x ask: got 0.7 want 0.7 ($)
  [ok ] lock level = ask: got 0.56 want 0.56 ($)
  [ok ] trail from a 0.80 peak (0.90 x): got 0.72 want 0.72 ($)
  [ok ] P&L: T1 fill at 0.70, 1 contract, fees in ($): got 12.7 want 12.7 ($)
  [ok ] P&L: backstop bid 0.38, 1 contract ($): got -19.3 want -19.3 ($)
  [ok ] P&L: lock exit at the ask 0.56 ($): got -1.3 want -1.3 ($)
  [ok ] P&L: worthless expiry, no sale fee ($): got -56.65 want -56.65 ($)
  [ok ] P&L: 3 contracts at T1 ($): got 38.1 want 38.1 ($)
  [ok ] float32 of 1.05 reads back: got 1.0499999523162842 want 1.05 (raw)
  [ok ] round(float32(1.05), 4) restores the threshold: got 1.05 want 1.05 ($)
  round trip: PASS
```

## 2. check_dead_code.py — the removed names resolve nowhere

Names checked: the three the owner named (SWEEP_FLOOR, BONUS_CAP, CONFIDENCE_CAP). None resolves in the terminal
(they never existed there; the bot's root is where the proof matters). The classes the audit named without naming
are listed as "names to review": in the terminal `PREMIUM_FLOOR` / `PRINT_PREMIUM_FLOOR` are Trace's dollar floors on
a print (a feed rule, kept knowingly) and the `GRADE_*` / `CONFLUENCE*` / `SCORE` / `*_WEIGHT` names are the
terminal's own (the review grid's inks and ranks, the confluence panel, a chart weight) — the terminal's `npm run
words:check` bans the words on screen, not in code. For the bot, every such name is either listed in `--names`
(removed) or kept on purpose. The tsc half is printed: delete the exports and `npx tsc -p tsconfig.json --noEmit`
must pass; then the fixed-day replay diff.

```
check_dead_code: /home/user/3abida/src
  removed names checked: SWEEP_FLOOR, BONUS_CAP, CONFIDENCE_CAP
  RESOLVES (a finding): 0
  names to review (the audit's classes; list a removed one in --names, keep the rest knowingly):
    class:premium cap/floor: 7 hit(s) in 3 file(s) — PREMIUM_FLOOR, PRINT_PREMIUM_FLOOR
    class:delta floor/ceiling: 0 hit(s) in 0 file(s)
    class:OI floor: 0 hit(s) in 0 file(s)
    class:min/max DTE: 0 hit(s) in 0 file(s)
    class:weight/score/grade: 63 hit(s) in 18 file(s) — A_WEIGHT, CONFLUENCE, CONFLUENCE_EMA, CONFLUENCE_TFS, GRADE_BAR, GRADE_FILL, GRADE_INK, GRADE_RANK, GRADE_WORD, OVERWEIGHT, SCORE, UNDERWEIGHT ...
  static half: delete the exports of SWEEP_FLOOR, BONUS_CAP, CONFIDENCE_CAP and run  npx tsc -p /home/user/3abida/tsconfig.json --noEmit  (the project's typecheck); it must pass with nothing else changed. Then replay a fixed day and diff the engine's output byte for byte: only a removed cap that used to bind may differ, each listed.
  result: PASS — no removed name resolves
```

## 3. check_helix_isolation.py — telemetry is read by no decision

Helix does not exist in the terminal (it is the bot's), so the run names the terminal's nearest equivalents as the
telemetry modules — `data/dealerTimeline.ts`, `data/feed/trailModel.ts`, `data/feed/trailField.ts` (the modeled
dealer field and the regime strip, spec 1.2's "display telemetry") — and Compass as the decision root.

Run A, the whole Compass folder (its React panels included): 4 import paths reach the trail model, every one through
`components/gex/StrikeChart.tsx` — the chart the Compass panels draw. That is the UI reading telemetry to draw it,
which spec 16.2 allows; the check cannot tell a drawing component from a decision by its imports, which is why the
decision globs must name the decision modules, not the screens.

Run B, Compass's pure logic (`components/compass/*.ts`: setupProcess, campaignStore, trackModel, setupMarksPrimitive;
`data/compass.ts`, `data/compassStandIn.ts`, `data/compassView.ts`): **0 import paths, 0 field reads — PASS.** The
(c) replay test (decisions identical with the telemetry fields null) is the owner's to run on the bot.

```
check_helix_isolation: /home/user/3abida/src
  decision files: 22 (globs ['components/compass/*', 'data/compass.ts', 'data/compassStandIn.ts', 'data/compassView.ts'])
  telemetry modules present: 3 — data/dealerTimeline.ts, data/feed/trailModel.ts, data/feed/trailField.ts
  (b) import paths from a decision file to a telemetry module: 4
    components/compass/CampaignAnalysis.tsx  ->  components/gex/StrikeChart.tsx  ->  data/feed/trailModel.ts
    components/compass/CampaignAnalysis.tsx  ->  components/gex/StrikeChart.tsx  ->  data/feed/trailField.ts
    components/compass/ContractTrack.tsx  ->  components/gex/ChartToolbar.tsx  ->  components/gex/StrikeChart.tsx  ->  data/feed/trailModel.ts
    components/compass/ContractTrack.tsx  ->  components/gex/ChartToolbar.tsx  ->  components/gex/StrikeChart.tsx  ->  data/feed/trailField.ts
  (a)/(d) telemetry fields read inside decision files: 0
  (c) run the engine on one fixed replay day twice — once as is, once with every telemetry field set to null — and diff the decisions byte for byte; they must be identical.
  result: FAIL
```

```
check_helix_isolation: /home/user/3abida/src
  decision files: 7 (globs ['components/compass/*.ts', 'data/compass.ts', 'data/compassStandIn.ts', 'data/compassView.ts'])
  telemetry modules present: 3 — data/dealerTimeline.ts, data/feed/trailModel.ts, data/feed/trailField.ts
  (b) import paths from a decision file to a telemetry module: 0
  (a)/(d) telemetry fields read inside decision files: 0
  (c) run the engine on one fixed replay day twice — once as is, once with every telemetry field set to null — and diff the decisions byte for byte; they must be identical.
  result: PASS
```

## What the bot's run must pass

- check_cents: the bot's boundary module(s) declared with `--boundary`; zero price-unit findings outside them; the
  round trip plugged into the bot's own picker / stops / P&L (see the docstring's method list) passing to the cent.
- check_dead_code: `--names` carrying every removed cap and floor by name and `--value` their literals; zero
  resolves; the tsc half and the fixed-day byte diff done by hand and their output kept beside this file.
- check_helix_isolation: `--decision` naming the gate, the picker, the stops, the scale-outs, the sizing and the
  governor; `--telemetry helix` plus the bot's Physics / Nerve modules and `charm_pressure`, `moc_score`,
  `sign(GEX_book)`, the flow fields; zero paths, zero reads; the (c) replay diff kept beside this file.
