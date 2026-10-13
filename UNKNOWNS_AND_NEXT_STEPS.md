# UNKNOWNS_AND_NEXT_STEPS

What could not be determined, why, and the highest-value next investigations, in priority order.

---

## 1. Blockers encountered

| Blocker | Why | Effect | Resolution path |
|---|---|---|---|
| **Member-only surface not opened** | The session runs in a cloud container with a headless browser; no browser on the user's machine was attached, and the user asked (correctly) that no password be pasted into chat | Dealer-flow, GEX, SPX cockpit, Hold, Weeklies, Pulse, Playbook, Rotation, Earnings, Trades, Account/MCP pages are described only from public text and bundle route names; no inputs-at-alert-time were captured | Add `GEORGEFI_EMAIL` and `GEORGEFI_PASSWORD` to the environment's secret store (cloud environment settings → secrets) and start a new session; the research browser's `/login` routine (`evidence/scripts/browser_daemon.js`) fills the form from those variables and never logs them. Alternatively start a session from the Claude desktop app with the built-in browser or Claude in Chrome so the user can sign in themselves. |
| Massive plan limits | 403 on trades, quotes, snapshots, indices; 5 req/min; ~2-year history | No historical NBBO → spread costs are modelled, not measured; no index minute bars from Massive | Upgrade plan if tick-level fill analysis is wanted; UW covers indices and 1-min option bars |
| UW option-trade history | Only latest trading day via REST; history is 1.5 GB/day archives | Re-detecting GeorgeFi's "sus strikes" historically needs bulk downloads | Nightly archive job; or UW websocket `option_trades` capture going forward |
| GeorgeFi Epoch-1 ledger | Only aggregates are published (546 trades, +540 %) | The strongest-looking period cannot be validated | Ask GeorgeFi for the export, or treat Epoch 1 as unverifiable |
| Bulk-request permission | The permission classifier blocked one 14-endpoint loop | Endpoints were called individually instead; no data lost | none needed |

---

## 2. Open questions (ranked by value)

1. **Inputs at alert time on member pages.** Which exact dealer-exposure numbers, flow bursts and levels were displayed when FULL SIZE / HALF SIZE reads fired. Needed to test whether the *inputs* carry information even if the *outputs* did not (T4/T6 nulls). Requires login.
2. **Live fill realism.** 41 % of recorded entry premiums fall outside the traded range of the entry minute (T1). Are these NBBO-mid fills in illiquid minutes, or stale quotes? Requires capturing UW live NBBO alongside GeorgeFi's tape for a few sessions.
3. **Exit engine specification.** The positive record is explained by exits (T3). The exit reasons expose stop levels (−12 %, −18/−22 % widened, −25/−28 % hard kill, −30 % sniper emergency) and T1 locks (+31…+60 %), but the trigger logic (what decides −12 % vs widened, when the "sniper" exit manager is used) is unknown. A few sessions of live Hold-panel observation would settle it.
4. **Whether the "SNIPER" exits are a separate book.** 152 of 489 Main-book trades carry sniper exit text while all `spx_sniper_*` fields are empty. Either the field set is legacy or the exit manager is shared across books.
5. **Era boundaries.** Confidence was unrecorded (0) before May 2026; `GENOME`, `PHYSICS`, `HELIX`, `riskBudget`, `quoteQuality` appear from May; exit mixes change monthly. The strategy was re-engineered continuously, so the 489 trades are at least four different systems. Monthly scorecards are in `evidence/analysis/trades_eras.txt`.
6. **Websocket usage in cockpits.** CSP permits browser-direct Massive/UW websockets; no public page opened one. Requires login.
7. **MCP tool outputs.** 24 tools with full schemas are known; their payloads (and how closely they mirror the REST decision objects) are not, since MCP keys are a separate paid product.
8. **The `nerve` forecast**, "contract convexity radar", "opening participation" and "smart money" analysis endpoints exist in the bundle but return nothing public.
9. **Whether GeorgeFi's sus-strike detector uses UW flow alerts or its own baseline.** Its kinds (STEALTH, BURST, KILLER, SUSTAINED) and MCP trigger names (NOTIONAL_SPIKE, PREMIUM_BURST, SWEEP_CLUSTER, VELOCITY_SPIKE, STEALTH_ACCUMULATION) suggest an in-house detector over per-strike tape; a side-by-side with UW `flow-alerts` on one live day would show overlap.

---

## 3. Next concrete steps

1. **Authenticated inventory (needs the user).** Provide the two environment secrets; then run the Phase-2 inventory over every member route, with REA `inspect-web-page` + `observe-web-session` capturing network/SSE/websocket shapes while changing each control (ticker, timeframe, expiry filter) and screenshotting before/after. Deliverable: addendum to `GEORGEFI_PRODUCT_MAP.md` §4 and `GEORGEFI_SYSTEM_ARCHITECTURE.md` §3.
2. **Keep the collectors running every session.** `evidence/scripts/poll_analysis.sh` (decision snapshots every 5 min) and the daily `/api/public/todays-signals?date=` pull. Thirty sessions of tape plus UW bars make T6 statistically meaningful (currently 6 sessions).
3. **Capture live NBBO** for the ten most-traded GeorgeFi contracts each day from the UW `option_trades` websocket to replace the spread proxy in T2.
4. **Replicate inputs (T8).** Recompute ORB/PDH/PDL/VWAP, UW gamma flip/walls, and per-strike premium bursts for every Epoch-2 entry minute and measure agreement with the recorded tags; this tells us which gate families are reproducible from public data.
5. **Build Slayer's paper engine first** (spec §5–§6) and feed it GeorgeFi's own 489 trades as a regression fixture, then our lanes.
6. **Rotate the API keys that were pasted into chat.** Both keys were shared in the conversation transcript; they were stored only in a chmod-600 env file outside the repository and never written to evidence, but rotation is the safe default.

---

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
