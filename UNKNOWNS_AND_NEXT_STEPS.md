# UNKNOWNS_AND_NEXT_STEPS

What could not be determined, why, and the highest-value next investigations, in priority order.

---

## 1. Blockers encountered

| Blocker | Why | Effect | Resolution path |
|---|---|---|---|
| **Member-only surface** | Resolved: the user supplied credentials, the research browser signed in through the normal form, and all 27 member routes were inventoried (plan "The Bob", 24-hour trial ending 2026-10-14 11:09 ET) | Inputs at alert time, the SSE event catalog, four trade books and the `spx_gex_engine` paper book were captured (`evidence/auth_*`) | Trial expires 2026-10-14; a second day of capture needs the subscription kept active. The password was shared in chat and should be changed after this research. |
| MCP access on the account | `/account/mcp` reports `mcp_access_disabled` (separate product; 403 on every call) | MCP tool payloads were not captured; their descriptions and schemas are from the public discovery endpoint | Subscribe to an MCP plan if tool payloads are wanted; REST/SSE already expose equivalent objects |
| Massive plan limits | 403 on trades, quotes, snapshots, indices; 5 req/min; ~2-year history | No historical NBBO → spread costs are modelled, not measured; no index minute bars from Massive | Upgrade plan if tick-level fill analysis is wanted; UW covers indices and 1-min option bars |
| UW option-trade history | Only latest trading day via REST; history is 1.5 GB/day archives | Re-detecting GeorgeFi's "sus strikes" historically needs bulk downloads | Nightly archive job; or UW websocket `option_trades` capture going forward |
| GeorgeFi Epoch-1 ledger | Only aggregates are published (546 trades, +540 %) | The strongest-looking period cannot be validated | Ask GeorgeFi for the export, or treat Epoch 1 as unverifiable |
| Bulk-request permission | The permission classifier blocked one 14-endpoint loop | Endpoints were called individually instead; no data lost | none needed |

---

## 2. Open questions (ranked by value)

1. **Do the inputs carry information?** The member capture now exposes every input (per-strike GEX, flip, walls, accelerator, delta flow, timing, levels, σ ladder) with timestamps and lineage, and the committed read is a five-contributor vote. One session of inputs is not enough to test them; a multi-week collector of `/api/indices/*` payloads and the SSE stream (both available only while the subscription is active) is the prerequisite for T8.
2. **Live fill realism.** 41 % of recorded entry premiums fall outside the traded range of the entry minute (T1). Are these NBBO-mid fills in illiquid minutes, or stale quotes? Requires capturing UW live NBBO alongside GeorgeFi's tape for a few sessions.
3. **Exit engine specification.** The positive record is explained by exits (T3). The exit reasons expose stop levels (−12 %, −18/−22 % widened, −25/−28 % hard kill, −30 % sniper emergency) and T1 locks (+31…+60 %), but the trigger logic (what decides −12 % vs widened, when the "sniper" exit manager is used) is unknown. A few sessions of live Hold-panel observation would settle it.
4. **Whether the "SNIPER" exits are a separate book.** 152 of 489 Main-book trades carry sniper exit text while all `spx_sniper_*` fields are empty. Either the field set is legacy or the exit manager is shared across books.
5. **Era boundaries.** Confidence was unrecorded (0) before May 2026; `GENOME`, `PHYSICS`, `HELIX`, `riskBudget`, `quoteQuality` appear from May; exit mixes change monthly. The strategy was re-engineered continuously, so the 489 trades are at least four different systems. Monthly scorecards are in `evidence/analysis/trades_eras.txt`.
6. **Websocket usage in cockpits.** Resolved: no member page opens a websocket; provider websockets terminate on the server (`source: "websocket"` in GEX payloads) and reach the browser over SSE.
7. **MCP tool outputs.** 24 tools with full schemas are known; their payloads (and how closely they mirror the REST decision objects) are not, since MCP keys are a separate paid product.
8. **The `nerve` forecast**, "contract convexity radar", "opening participation" and "smart money" analysis endpoints exist in the bundle but return nothing public.
9. **Whether GeorgeFi's sus-strike detector uses UW flow alerts or its own baseline.** Its kinds (STEALTH, BURST, KILLER, SUSTAINED) and MCP trigger names (NOTIONAL_SPIKE, PREMIUM_BURST, SWEEP_CLUSTER, VELOCITY_SPIKE, STEALTH_ACCUMULATION) suggest an in-house detector over per-strike tape; a side-by-side with UW `flow-alerts` on one live day would show overlap.

---

## 3. Next concrete steps

1. **Keep the member capture running while the subscription is active.** The authenticated inventory is done (Product Map §4, Architecture §8, Signal Research §8). The high-value follow-up is a collector that stores, every minute during RTH, the `/api/indices/{spx,ndx,rut}/*` payloads, `/api/gex/expected-moves`, `/api/plays/today`, `/api/singles-surge/today` and the SSE stream, so that the inputs behind each FULL SIZE / HALF SIZE read can be joined with UW bars (validation test T8). The replay script (`evidence/scripts/replay_auth_api.py`) and SSE capture (`evidence/scripts/sse_capture2.js`) are the building blocks.
2. **Keep the collectors running every session.** `evidence/scripts/poll_analysis.sh` (decision snapshots every 5 min) and the daily `/api/public/todays-signals?date=` pull. Thirty sessions of tape plus UW bars make T6 statistically meaningful (currently 6 sessions).
3. **Capture live NBBO** for the ten most-traded GeorgeFi contracts each day from the UW `option_trades` websocket to replace the spread proxy in T2.
4. **Replicate inputs (T8).** Recompute ORB/PDH/PDL/VWAP, UW gamma flip/walls, and per-strike premium bursts for every Epoch-2 entry minute and measure agreement with the recorded tags; this tells us which gate families are reproducible from public data.
5. **Build Slayer's paper engine first** (spec §5–§6) and feed it GeorgeFi's own 489 trades as a regression fixture, then our lanes.
6. **Rotate the API keys that were pasted into chat.** Both keys were shared in the conversation transcript; they were stored only in a chmod-600 env file outside the repository and never written to evidence, but rotation is the safe default.

---

## 3b. Backtest outcome (added after the independent backtest)

The reconstructed strategy (level-sweep reversal and continuation entries on SPY/QQQ/IWM 0DTE contracts, GEX gates, session windows, GeorgeFi-style exit engines) was run over 345 sessions (2025-06-02 → 2026-10-09) in 144 variants. None has positive expectancy after a 1–2 % half-spread and $0.70/side fees; the best variant is −$2.4 per contract-trade (95 % CI −4.1 … −0.5) against a random-entry baseline of −$3.2. The reconstruction coincides with GeorgeFi's own SPY/QQQ/IWM entries only 7–9 % of the time within ±5 minutes, so GeorgeFi's live entry rule is **not** reproduced by the published description. Details in `BACKTEST_RESULTS.md`; what this means for Slayer in `STRATEGY_SPEC.md`.

Open items this creates:
- Which inputs GeorgeFi actually keys on (the 46 % direction agreement within 30 minutes says its entries are not plain level sweeps). The member-surface collector is the way to find out.
- SPX index bars require a CBOE-approved UW entitlement; the backtest therefore excluded SPX, GeorgeFi's most profitable ticker.
- Spread assumptions are modelled; live NBBO capture would replace them.

## 3c. Edge-search outcome (added after the deep-research round)

Six parallel studies (three literature reviews, three empirical tests on our Unusual Whales data, 339 sessions 2025-06-02 → 2026-10-09, SPY/QQQ/IWM) looked for a tradeable 0DTE input among per-strike flow bursts, signed net premium / net delta / market tide, dark-pool prints, dealer gamma regime and intraday gamma/charm/vanna, walls/magnet pinning, session effects (ORB, half-hour seasonality, first→last-30 momentum, gap fill) and exit engineering. Full report: `reports/Finding a 0DTE options edge.md`; notes in `research_notes/Finding a 0DTE options edge/`; code and outputs in `research/`.

- 0 of 62 predictive feature×horizon×ticker cells survive multiple-testing correction; the only survivors are the *negative* net returns of burst contracts. Flow aggregates are 0.5–0.67 rank-correlated with the trailing 15-minute move and ≤0.02 with the forward move.
- Prior-day gamma regime does not separate continuation from reversal (POS−NEG slope +0.03 [−0.12, +0.19], sign flips IS→OOS). Intraday negative gamma predicts larger absolute moves (IC −0.21) but not their sign. Walls and magnet behave like distance-matched random levels.
- 0 of 576 exit-engine configurations have positive spread-model expectancy on strategy or random entries; the gross ceiling of any path-shaping rule is ≈1.5 % of premium against a 3–6 % measured round trip.
- Short ATM straddles earn +$7 to +$17 per straddle at mid at every entry time (13:00 strongest), but every pooled spread-model interval spans zero and two tail days outweigh sixteen months of income.

Open items this creates (in priority order):
1. Capture live NBBO for SPY/QQQ ATM 0DTE contracts in the early afternoon (UW `option_trades` websocket) for a few weeks; the executable half-spread is the one number that can move the 13:00 short-straddle interval off zero.
2. Run directional ideas (gamma-conditioned last-30-minute momentum, noise-band intraday momentum) in shares/futures, where a 1 bp effect clears costs; our gamma test had ~1,016 ticker-days against ~6,000 in the published sample.
3. Extend the flow panel back to 2022-09-28 (~1,000 sessions) and use strike-level `spot-exposures` and same-day `gex-levels` for a proper wall test.
4. Obtain the SPX index-bar entitlement so $5–10 premium SPXW contracts (half the proportional cost) can be tested, short-premium first.

## 4. Confidence summary

| Claim | Confidence | Basis |
|---|---|---|
| GeorgeFi is a Nuxt/PocketBase app with a server-side engine fed by Massive and Unusual Whales | High | headers, bundle, payload ids, CSP, recap source refs |
| Decision objects expose a ~100-tag additive scoring ledger with caps and grades | High | 489 trade ledgers + 20 live decisions |
| `crowd_mood` is an RSI threshold label (45/55) | High | 60/60 observations |
| The product does *not* mechanically trade against the crowd label | High for the observed sample | 13/20 same-side, 2/20 opposite |
| Positive Epoch-2 record is driven by exit management, not entry timing | Medium-high | T3/T4 on 443 scalps with independent bars |
| Recorded Epoch-2 P&L is not distinguishable from zero and is negative under realistic costs | Medium-high | T2 bootstrap CI includes 0; adverse model strongly negative |
| Setup grades / confidence do not separate outcomes out of sample | Medium | T5 pre-registered tests, n=171 OOS |
| Public-tape alerts (sus-strike etc.) have no stand-alone directional value | Low-medium | 6 sessions only (T6) |
| Member cockpit inputs add information | Unknown | not observed |
| No tested UW input (flow, tide, dark pool, bursts, gamma regime, walls, session effects) times long 0DTE entries better than random after costs | High for SPY/QQQ/IWM, Jun 2025–Oct 2026 | 62 cells, 576 exit configs, 144 variants; report §2–§4 |
| Short ATM straddle premium is real at mid but within one modelled spread | Medium | 30,510 straddle-days; spreads modelled, not measured |
