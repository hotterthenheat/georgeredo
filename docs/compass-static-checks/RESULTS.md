# Compass static checks — results of the demonstration run (2026-10-21, second run: zero findings)

**What this is.** The three scripts in this folder are the module 15–16 verification of
`docs/compass-core-spec-v2.md` (cents normalization, dead-code quarantine, Helix isolation). They take a code root
as an argument. **The Compass bot's own code is not in any repository on this machine**, so the run below is a
demonstration on the terminal's source, `/home/user/3abida/src` (Slayer). The bot's root must be passed when it
exists; every line below is about the terminal, not the bot.

Run from this folder (Python 3, standard library only; `-I` isolates the interpreter from the scanned tree). These
are the exact commands of the run recorded below:

```
python3 -I check_cents.py           /home/user/3abida/src --boundary 'data/feed/occ.ts' --allow allow.3abida.json --selftest
python3 -I check_dead_code.py       /home/user/3abida/src --names SWEEP_FLOOR,BONUS_CAP,CONFIDENCE_CAP
python3 -I check_helix_isolation.py /home/user/3abida/src --decision 'components/compass/*.ts' --decision data/compass.ts \
                                    --decision data/compassStandIn.ts --decision data/compassView.ts \
                                    --telemetry data/dealerTimeline.ts --telemetry data/feed/trailModel.ts --telemetry data/feed/trailField.ts
```

Each exits 0 on a pass and 1 on a finding (check_cents also on a stale `--allow` entry); `--json` prints the full result.
Result: **all three at zero findings, exit 0.**

## What changed between the first run and this one

The first run (the same day, earlier) put 31 price-unit hits outside the boundary. One was real; the rest were
lines the classifier read by a price-like word (`open`, `close`, `strike`, `move`) that on that line meant an instant,
a share or a greek. They were brought to zero three ways, and in no case by loosening a rule:

1. **Fixed in the terminal — the OCC boundary.** The genuine finding, a second decoder of the OCC strike (`/ 1000`
   in `data/feed/trailModel.ts`), and its inverse found on the second run (`Math.round(c.strike * 1000)` in
   `data/feed/massive.ts`, the retired Massive provider's `occTicker`), now live in ONE module:
   `src/data/feed/occ.ts` — `parseOcc`, `strikeFromThousandths`, `occStrike` (the decode) and `thousandthsFromStrike`,
   `occSymbol` (the encode). `uw.ts`'s multi-leg legs, `trailModel.ts` (re-exporting `parseOcc` for the server) and
   `massive.ts` read and write through it. `occTicker`'s output is byte-identical before and after (checked on 192
   contracts across four roots, three expiries, both rights and eight strikes, 167.5 and 225.0001 among them). That
   module is the declared boundary: `--boundary 'data/feed/occ.ts'`; the earlier four-file boundary (uw, client,
   theta, massive) is no longer needed, since none of those files converts a unit any more.
2. **The checker classifies what text can settle.** `check_cents.py` gained classes and rules that read the words on
   the line: `time-ms` when the ×1000 / ÷1000 feeds a clock function (the `ny*` / `viewer*` of core/nyTime.ts,
   `readerClock`, `sessionSpan`, `new Date`) or a `time:` field, or its operand is a span's or bar's instant
   (`span.close`, `s.open`, `x.time`); `percent` for `(a / b − 1) * 100`, a `score` or a `move` × 100, and
   `((strike − spot) / spot) * 100` (a distance in percent, which the first run's rule had been calling a contract
   multiplier); `vol-points` for `iv = … * 100`; `greek-per-point` for rho or vega over 100; `svg-width` for a
   `width={… / 100}`; `thousands-label` for `/ 1000}K`; `contract-multiplier` extended to `callOI * 100`,
   `* 100 * u.vega`, `past(strike) * 100` and `* 100 * contracts` / `* size`. A continuation line (opening with a
   bracket, an operator or a ternary's `?` / `:`) is read with the line before it, which is how `const rho = Number(`
   names the `/ 100` on the next line. Every hit whose class changed between the two runs was read by hand
   (a JSON diff of the two runs): 28 of the 31 moved into the class their text names, and no hit moved into
   `price-unit`. Two over-reaches found in that diff were taken back before the run below — `(side ? 1 : −1) * 100
   * contracts` had matched the change-in-percent shape (it is the multiplier) and `impliedMovePct = … * 100` had
   matched the vol rule (it is a percent).
3. **A reviewed allowlist for what a line alone cannot settle** — `allow.3abida.json`, one entry a line, a reason
   each, passed with `--allow`. An entry is narrow (one path, a regex on the line), only ever turns a price-unit hit
   into `allowed`, and an entry that matches nothing is STALE and fails the run, so the list cannot outlive the code.
   The three entries:
   - `data/levelview.ts:59` `const lo = open / 1000;` — `open` is an epoch-millisecond instant destructured from
     `nySession()` on the line before, divided to the bars' seconds; the line alone reads as a price named open.
   - `data/levelview.ts:60` `const hi = close / 1000;` — `close` is the session's closing instant from the same
     `nySession()` call, milliseconds to seconds; not the closing price.
   - `core/simulator.ts:229` `const refWall = (20000 * 2.4 * 100 * price * price * 0.01 * 0.54) / …` — the house
     simulator's reference wall: 20,000 contracts of open interest × gamma × the contract's 100 shares × price², the
     exposure arithmetic of a seeded shelf, the literal OI unnamed on the line; no vendor unit is changed.

   What was NOT made a rule, on purpose: `/ 100).toFixed(n)` as a percent signal — that is exactly the shape a
   cents-to-dollars conversion would take, so it stays a finding unless the figure's name settles it (as `rho` does
   through the continuation rule).

## 1. check_cents.py — one price unit at the vendor boundary

Boundary: `data/feed/occ.ts` alone. The round-trip harness ran on the reference engine with the audit's known
contract (SPY 20261030 808 C at 0.55 / 0.56 on 2026-10-09): 16 of 16 figures to the cent, and the float32 case behind
spec 0.1 reproduced. The classes listed apart (not findings) are the terminal's own arithmetic: cent-rounding,
the simulator's integer-cents map keys (dollars in, dollars out), the contract multiplier in exposure and P&L,
percent, time-ms, vol points, the three allowed lines, and 78 `other` (a ×100 or ÷1000 on no price-like word —
listed for a human in `--json`).

Result on the terminal: **0 findings, 3 allowed with reasons, 0 stale; exit code 0.**

```
check_cents: /home/user/3abida/src
  boundary globs: ['data/feed/occ.ts']
  hits by class: allowed 3, boundary 3, cent-rounding 52, cents-keyed-map 113, comment 9, contract-multiplier 83, greek-per-point 2, lot-rounding 3, other 78, percent 320, svg-width 5, thousands-label 8, time-ms 178, vol-points 32
  FINDINGS (price-unit conversions outside the boundary): 0
  ALLOWED (reviewed by hand in allow.3abida.json, a reason each; not findings): 3
    data/levelview.ts:59: const lo = open / 1000;
      reason: `open` is an epoch-millisecond instant destructured from nySession() on the line before, divided to the bars' seconds; the line alone reads as a price named open.
    data/levelview.ts:60: const hi = close / 1000;
      reason: `close` is the session's closing instant from the same nySession() call, milliseconds to seconds; not the closing price.
    core/simulator.ts:229: const refWall = (20000 * 2.4 * 100 * price * price * 0.01 * 0.54) / (2.5066 * denom);
      reason: The house simulator's reference wall: 20,000 contracts of open interest x gamma x the contract's 100 shares x price^2 — the exposure arithmetic of a seeded shelf, the literal OI unnamed on the line; no vendor unit is changed.
  STALE allow entries (match no price-unit hit — remove them): 0
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

Result: **0 resolves; exit code 0.**

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
dealer field and the regime strip, spec 1.2's "display telemetry") — and Compass's pure logic as the decision root
(`components/compass/*.ts`: setupProcess, campaignStore, trackModel, setupMarksPrimitive; `data/compass.ts`,
`data/compassStandIn.ts`, `data/compassView.ts`).

A note kept from the first run: with the Compass folder's React screens in the decision glob
(`components/compass/*`) the same arguments show 4 import paths, every one through `components/gex/StrikeChart.tsx`,
the chart the panels draw — the UI reading telemetry to draw it, which spec 16.2 allows. The decision globs must
name the decision modules, not the screens; that run is a lesson about the glob, not a finding, and is not the run
on record. The (c) replay test (decisions identical with the telemetry fields null) is the owner's to run on the bot.

Result: **0 import paths, 0 field reads; exit code 0.**

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

- check_cents: the bot's boundary module(s) declared with `--boundary`; zero price-unit findings outside them, every
  `--allow` entry (if any) reviewed with a true reason and none stale; the round trip plugged into the bot's own
  picker / stops / P&L (see the docstring's method list) passing to the cent.
- check_dead_code: `--names` carrying every removed cap and floor by name and `--value` their literals; zero
  resolves; the tsc half and the fixed-day byte diff done by hand and their output kept beside this file.
- check_helix_isolation: `--decision` naming the gate, the picker, the stops, the scale-outs, the sizing and the
  governor; `--telemetry helix` plus the bot's Physics / Nerve modules and `charm_pressure`, `moc_score`,
  `sign(GEX_book)`, the flow fields; zero paths, zero reads; the (c) replay diff kept beside this file.

## Rerun after the terminal's rebase (2026-10-21, 58 upstream commits taken in)

The terminal's default branch had moved 58 commits while the occ.ts change was made; the change was rebased onto it
(parseOcc in trailModel now wraps occ.ts's decoder and keeps upstream's `tradingExpiry`, which dates a Saturday-stamped
monthly to its Friday). The three checks were run again on the rebased tree with the same commands:

- check_cents: FINDINGS 0, ALLOWED 5, STALE 0. Two lines the upstream commits added were reviewed and allowlisted with
  their reasons — `data/feed/trailModel.ts` `wallObsOf(r.m / 1000, …)` (a store row's minute, milliseconds to the
  seconds wallObsOf takes) and `data/feed/forward.ts` `.vega * 100` (vega per unit of vol scaled to a full point, so a
  quote's width reads in vol points).
- check_dead_code: RESOLVES 0 — PASS.
- check_helix_isolation: 0 import paths, 0 field reads — PASS.
- The terminal's typecheck passes; its trail-field, priced-move, feed and field-store proofs pass (47, 20, 29, 30).
