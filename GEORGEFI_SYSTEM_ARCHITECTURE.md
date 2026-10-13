# GEORGEFI_SYSTEM_ARCHITECTURE

Evidence-backed description of GeorgeFi's observable architecture and data flow, as of build `2026.10.13-083911-af712b2f9`. Every statement is tagged **[observed]** (seen directly in a response, header, payload or bundle string), **[inferred]** (a conclusion drawn from observations, with the basis stated) or **[unknown]**.

Evidence files referenced: `evidence/public_pages_text/home_response_headers.txt`, `evidence/bundle_static/api_paths_from_bundle.txt`, `evidence/rea/inspect_home.json`, `evidence/rea/bundle_home.json`, `evidence/rea/*.json` (per-page network logs), `evidence/public_api/*.json`, `evidence/ssr_payloads/*.json`, `evidence/public_api/trades_all.json.gz`.

---

## 1. Platform summary

| Layer | Finding | Basis |
|---|---|---|
| Edge / CDN | Cloudflare in front of the origin (`server: cloudflare`, `cf-ray`, `cf-cache-status: DYNAMIC`, Cloudflare Insights beacon, NEL reporting) | [observed] response headers |
| Web framework | Nuxt 3 (Vue 3, Vite build) with full server-side rendering; `x-powered-by: Nuxt`, `__NUXT_DATA__` devalue payloads, `/_nuxt/*.js` hashed chunks, `/api/_nuxt_icon/*` icon proxy | [observed] headers + HTML; REA bundle inference "Vite", "Vue" (`evidence/rea/bundle_home.json`) |
| App server / API | Same origin `https://georgefi.trade/api/*` (Nuxt server routes / Nitro). CSP also allows `https://api.georgefi.trade` and `https://*.georgefi.trade` | [observed] CSP `connect-src` |
| Primary database | **PocketBase**: trade and challenge records carry `collectionId: "pbc_2293394539"`, `collectionName: "trades"`, PocketBase-style 15-char ids (`c24vergs851zp5d`); the bundle contains the PocketBase JS SDK (`/api/collections/`, `/api/realtime`, `/api/batch`, `/api/files/token`, `pocketbase.io` link); `robots.txt` mentions a `PB suspicious_ip_events` table | [observed] `/api/trades` payload, bundle strings, robots.txt |
| Legacy DB reference | The `/docs/api` page still says "Firebase Admin connected" / "Firestore database is secured", but the live `/api/health` returns `{"status":"success","message":"Server is healthy"}` with no collection list | [observed]; the Firebase text is **stale documentation** [inferred] |
| Realtime to browser | Server-Sent Events: `GET /api/realtime/stream?types=…` (first event `connected` carries `clientId`, `strategyVersion`, `tier`, `authenticated`, `marketStatus`); bundle also has a "Futures SSE" client and the PocketBase realtime client | [observed] SSE sample in `evidence/public_api/` and bundle strings |
| Realtime from providers | CSP `connect-src` allows `wss://socket.massive.com`, `wss://*.massive.com`, `wss://*.unusualwhales.com`. No websocket was opened on any public page (REA and Playwright both recorded zero websocket connections) | [observed]; browser-direct provider websockets on member cockpits are therefore **[inferred, unverified]** |
| Payments | Stripe (Checkout, customer portal, product/price payloads in SSR; prices denominated in CAD) | [observed] |
| Media / files | DigitalOcean Spaces bucket `george-bucket.nyc3.digitaloceanspaces.com` (recap MP4/WebM/poster assets) | [observed] |
| Alerting channels | Discord webhooks per challenge/trade (`discordWebhookUrl`, `discord_enabled` fields; webhook URLs are exposed in the public challenge payload — a hygiene issue for the operator, not used here), SMS (Twilio-style SMS policy page), web tape | [observed] |
| Analytics | Google Analytics 4 (`G-K684CRH5Z3`), Cloudflare RUM | [observed] |
| Agent surface | MCP server at `POST /api/mcp` (streamable-http, bearer `mcp_live_…` keys), discovery at `/api/mcp/discovery` (schema `george.mcp.discovery.v1`, 24 tools), x402 pay-per-call rail (USDC on Base, facilitator `x402.org`, payTo currently placeholder `0x…0001`, `configured:false`) | [observed] |
| Anti-bot | Honeypot route under `/api/__honeypot/`, prompt-injection text in every page, `suspicious_ip_events` logging | [observed] |

---

## 2. Engine components visible through outputs

The analytical engine is **entirely server-side**. The browser receives finished objects (decisions, signals, trades) and renders them; no indicator math was found in the client bundle (REA parsed 156 scripts, 448k AST nodes; the only "endpoints" it inferred were head-tag helpers). [observed + inferred]

### 2.1 Strategy versions / books

`/api/trades` exposes four **books** [observed]:

| `version` | name | isMain | blended |
|---|---|---|---|
| `v2.0.0-ict` | ICT Main | true | true |
| `singles_today_v1` | Singles TODAY | false | false |
| `spx_plan_v1` | SPX Plans | false | false |
| `trade_now_v1` | Trade Now | false | false |

All 489 Epoch-2 trades belong to `v2.0.0-ict`. The 30-day scorecards for the other books (`closed` 42 / 8 / 21) show they trade but their trades are not in the public `trades` array.

### 2.2 Decision cycle

- `/api/analysis` returns 20 `decisions` (one per covered ticker) and the same 20 objects again as `signals`; `marketStatus`, `indices` (6 quotes), `updatedAt`. [observed]
- Core index/ETF decisions (`^SPX`, `^RUT`, `SPY`, `QQQ`, `IWM`, `^NDX`) share one `generatedAt` to the millisecond (`2026-10-13T14:14:54.474Z`), single names have individual earlier timestamps → **[inferred]** one scheduler pass per minute computes the core six together, single names on a slower/independent loop (`/how` says "every minute during market hours"; MWF single-name board per `/mcp`).
- Each decision object carries: `direction`, `action` (`WATCHING`, `WAITING FOR TRIGGER`, `WATCHING (Pending Entry)`, `BUY_CALLS`, `BLOCKED: <reason>`), `confidence` (0–100), `setupGrade` (A+…B-), `contract` (`0DTE $7800 P`), `premium`, `optionSymbol` (OCC, e.g. `O:SPXW261013P07800000` — Massive/Polygon symbology), `confluenceSignals[]` (the gate ledger), `reason` text, `ictContext` (price, rsi, sparkline[20], volumeAnalysis incl. VIX, weeklyProfile, gexSummary), `gexProfile` (totalGEX, gammaFlip, maxGEXStrike, regime, pinRisk, acceleratorScore, directionalBias), `watchLevels` (nearest bullish/bearish level, `sweepsToday[]` with `sweptAt`, `primaryTarget`, `hasTripleConfirmation`), `chopState`, `isChopDay`, `shouldWaitForPM`, `grindingState`, `crowd_mood`, `strategyVersion`, `expiresAt`. Both camelCase and snake_case duplicates are present (`setupGrade`/`setup_grade`) → **[inferred]** a serialization layer that merges a Python-style backend record with a JS-style view model, or a migration between the two.
- The watch-level vocabulary (ORH/ORL, PDH/PDL, PWH/PWL, PMH/PML, GEX_SUPPORT/GEX_RESISTANCE, EM_1SD/2SD) matches the `/how` description exactly. [observed]

### 2.3 Subsystems seen on the public tape (6 sessions, 972 rows)

`sus-strike` (498), `hold-advisor` (232), `momentum-ignition` (91), `index-read` (35), `relative-burst` (23), `moc-wick` (19), `block-sniper` (17), `big-print` (13), `feed-headline` (13), `accumulation-sniper` (11), `script-flip` (6), `power-hour` (5), `anchor-book` (5), `trade-now` (3), `chop-day` (1), plus `opening-range`, `volume-crescendo`, `5m-wick`, `press-terminal` on 10/13. Each row has `at` (minute), `ticker`, `title`, `kind`, `play`, `direction` (LONG/SHORT/NEUTRAL/blank), `loud`, `subsystem`, `paper`, `family` (SPX/NDX/RUT/OTHER). [observed] `evidence/public_api/todays_signals_history/`

### 2.4 Scheduler

Bundle strings name admin scheduler triggers (`/api/scheduler/morning-analysis`, `opening-bell-prep`, `premarket-bias`, `ticker-licker`, `ticker-licker-0dte`, `daily-recap`) [observed, never called]. They line up with the published daily clock (8:00 morning analysis, 9:25 opening bell prep, 15:30 ticker-licker lotto schedule in the challenge config, 16:05 daily recap). [inferred]

### 2.5 Trade lifecycle fields (from the 489-trade export)

Entry: `entryTime`, `entryPremium`, `entryDebit`, `entryPrice` (underlying), `size`/`initial_size`, `quoteQuality` (bid, ask, mid, last, spreadPct, ageMs, `source: "websocket"`, `fillProfile: SINGLE_NAME | INDEX_CASH`, `maxSpreadPct` 0.25–0.30, `maxAgeMs` 2000, `isExecutable`, `reason: WEBSOCKET_EXECUTABLE | WEBSOCKET_QUOTE_TOO_OLD`), `riskBudget` (availableBuyingPower, positionDebit, maxLossDollars, stopLossPercent, settlement CASH/PHYSICAL, exerciseStyle), `entryEnvironment` (direction, gexRegime AT_PIN/POSITIVE_GAMMA/NEGATIVE_GAMMA/FAR_FROM_PIN, timeBucket OPENING/MORNING/LUNCH/PM_SESSION/POWER_HOUR/CLOSE, vixRegime, volumeTier COLD/NORMAL/WARM/HOT/VOLCANIC), `dayTypeGateVerdict` (CPI, VIX_SETTLE, OPEX_* gates), `physicsVerdictEntry` (RENORM/LAMINAR), `confluenceSignals[]` (60–100 tags), `confidence`, `confidencePreCap`, `setupGrade`. [observed]
Exit: `exitTime`, `exitPremium`, `exitReason` (free text, see SIGNAL_RESEARCH), `highWaterMark`, `pnl`, `pnlPercent`, `partial_*`, `scaled_out_at_*`, `lotto_t1..t3`. [observed]
Greeks at entry (`entryDelta`, `entryIV`, …) are present as fields but are **zero on every record** → not populated. [observed]

---

## 3. Data-flow diagram

```mermaid
flowchart LR
  subgraph Providers
    M[Massive / Polygon<br/>OCC option symbols, NBBO, bars]
    UW[Unusual Whales<br/>option tape, GEX/vanna/charm, dark pool]
    N[News / social sources<br/>Situation Room]
  end
  subgraph Server["georgefi.trade origin (Nuxt/Nitro + PocketBase)"]
    WS[Provider websocket cache<br/>'live websocket cache' per /mcp FAQ]
    ENG[Analysis engine<br/>1-min cycle: ICT levels, sweeps, GEX regime,<br/>gates, grading, inversion, sizing]
    SUB[Subsystems: sus-strike, index-read,<br/>hold-advisor, block-sniper, moc-wick,<br/>apex prints, trade-now, ticker-licker]
    PB[(PocketBase<br/>trades, signals, decisions,<br/>plans, challenges, alert_send_ledger,<br/>hold_advisor_states, moc_wick_events)]
    SSE[/api/realtime/stream SSE/]
    API[/api/* REST + /api/mcp/]
    SCH[Schedulers: morning-analysis,<br/>opening-bell-prep, premarket-bias,<br/>ticker-licker, daily-recap]
  end
  subgraph Clients
    B[Browser (Nuxt SSR + client)]
    D[Discord webhooks / SMS]
    A[MCP agents / x402]
  end
  M --> WS --> ENG
  UW --> WS
  N --> SUB
  ENG --> PB
  SUB --> PB
  SCH --> ENG
  PB --> API --> B
  PB --> SSE --> B
  PB --> D
  API --> A
  M -. CSP allows direct wss .-> B
  UW -. CSP allows direct wss .-> B
```

Solid edges are observed (an endpoint, payload or field proves the link). Dotted edges are allowed by CSP but were never seen in use.

Evidence for the provider edges: recap `sources` arrays cite `massive:O:SPXW261012P07800000@14:52` as the price source for one-minute highs; `quoteQuality.source = "websocket"` with NBBO fields; MCP FAQ "dealer GEX from the live websocket cache"; CSP websocket hosts; `/api/options/prices` returns `source: "nbbo"`. Which provider feeds which field is **[inferred]**: option bars/NBBO → Massive; sus-strike/flow/GEX → Unusual Whales (UW is the only allowed host that offers per-strike flow and dealer Greeks). Unusual Whales' own `gex-levels` endpoint uses the field names `gamma_flip`, `call_wall`, `put_wall`, `gamma_magnet`, which correspond to GeorgeFi's `gammaFlip`, `GEX_RESISTANCE/SUPPORT`, `maxGEXStrike` concepts, but GeorgeFi's `totalGEX` values ($8.4B for ^SPX) are on a different scale from UW's per-strike `call_gex` numbers, so GeorgeFi aggregates its own exposure from chain data rather than copying UW's summary. [inferred from numbers; unverified]

---

## 4. Client-side vs server-side

| Output | Where computed | Basis |
|---|---|---|
| Decisions, confidence, grades, gates, contracts, levels, GEX regime | Server | Full objects arrive from `/api/analysis` with ids and timestamps; identical on repeat requests within the minute |
| Trade P&L, scorecards, epochs, performance metrics | Server | `/api/performance` and SSR payloads deliver computed metrics (Sharpe, drawdown, by-grade) |
| Public tape filtering (family / DTE / loud / ticker pin) | Client | Payload holds all 200 rows; chips only filter |
| Option mark prices on landing | Server proxy | `/api/options/prices?symbols=…` returns NBBO bid/ask/mid per OCC symbol |
| Recap "peak" statistics | Server (precomputed) | SSR `summary.alerts[].peak` with `basis: "one-minute high"` and source refs |
| Performance "cumulative" chart | Client render of server daily array | daily series embedded in payload |

---

## 5. Observable identifiers, confidence values and intermediate calculations

- Decision/trade ids are PocketBase ids; recap sources expose internal collection names: `alert_send_ledger`, `hold_advisor_states`, `moc_wick_events`. [observed]
- Confidence is exposed pre- and post-cap (`confidencePreCap`, and tags like `CONFIDENCE_CAP:100->82:CRITICAL_CONFLICT_CLUSTER`, `BONUS_CAP:45->20`, `GRADE_CAPPED:A+→A:STRUCTURAL_CONFLICTS`, `SWEEP_FLOOR:51->65`, `SESSION_ADJ:+20`), i.e. the gate ledger reveals the *additive scoring pipeline* in enough detail to reconstruct its structure (see SIGNAL_RESEARCH §3). [observed]
- Intermediate values exposed: ORB range %, chop score components, expected-move % and exhaustion %, breaker/OB strength numbers, sweep counts, GEX accelerator before/after values in exit reasons, VIX level, RVOL, SPX velocity, helix/physics/genome scores. [observed]
- MCP responses add `timestamp`, `expiryFallbackUsed`, freshness metadata. [observed in sample]

---

## 6. Time and freshness conventions

- All API timestamps are ISO-8601 UTC (`Z`), occasionally with a space separator (`2026-10-20 14:14:54.749Z`) → mixed serializers. [observed]
- `timestamp` on `/api/analysis` root is epoch milliseconds. [observed]
- Trade `expirationDate` is midnight UTC of the expiry date. [observed]
- Minute-level cycle; SSE heartbeat; public tape refresh 30 s. [observed]
- Massive OCC symbology (`O:SPXW…`, `O:NDXP…`, `O:RUTW…`) is used end-to-end, including in recap sources. [observed]

---

## 7. What remains unknown about the architecture

- Whether member cockpits open browser-direct websockets to Massive/Unusual Whales (CSP permits it) or only consume the server SSE; which `types=` values the SSE supports beyond `heartbeat`.
- The internal composition of the engine (language/runtime). Clues: snake_case/camelCase duplication, Python-style datetime strings, "§293/§310" section references in MCP descriptions (an internal spec document), `ENV_BACKFILLED:v5.x` tags.
- Exact provider→field mapping and whether UW's REST or websocket feeds are used for sus-strike detection.
- Any rate limiting on `/api/*` (none advertised; none hit during ~30 requests).
- Everything behind `/account`, admin routes, schedulers and PocketBase collections beyond the names exposed.

---

## 8. Addendum: authenticated surface (observed 2026-10-13 with the user's "The Bob" account)

Evidence: `evidence/auth_pages/`, `evidence/auth_api/`, `evidence/auth_interactions/`, `evidence/auth_pages/_sse_capture.json`, `evidence/rea/inspect_spx_cockpit.json`.

### 8.1 Corrections to earlier inferences
- **Provider websockets are server-side, not browser-side.** Zero websocket connections were opened across 27 member page loads. `/api/gex/by-expiry` answers `"source": "websocket"` and `/api/indices/spx/gex` carries `sourceOldestTimestamp`, i.e. the server keeps a provider websocket cache and serves it over REST + SSE. [observed] The CSP websocket allowances are unused by the client.
- **Hybrid deployment.** `/api/health/hybrid` returns `{"role":"cloud-standby","source":"cloud-instance","macAlive":true,"heartbeatAgeSec":23}` and SSE `gex` events carry `isCloud` / `dataSource`: the engine runs on a Mac host with a cloud standby that serves the web app. [observed]
- **Lineage metadata.** Cockpit payloads carry `lineage: {source: live_native | live_replay | live_proxy | unavailable, label, computedFor, generatedAt, ageSec, isFresh}` — e.g. ^SPX dark pool and DP levels are computed on **SPY as a proxy** (`live_proxy`, `ratio ≈ 10.03`), watch levels were `live_replay`, physics and displacement were `unavailable` at observation. [observed]

### 8.2 Member API map (98 unique endpoints seen; full table in `evidence/auth_pages/` network logs)
- **Per-index cockpit feeds** `/api/indices/{spx,ndx,rut}/…`: `gex` (51-strike ladder with callGamma/putGamma/netGEX, totals for GEX/gross GEX/vanna/charm, gammaFlip, maxGEXStrike, regime, `massiveStrike` concentration, `analysis` {directionalBias, acceleratorScore, pathOfLeastResistance, pinRisk, breakoutRisk, concentrationZones}); `dealer-read` (action side/strike/stop/target/urgency, alignment, badges, callWall/putWall, charmDecayRate, hedgeFlowPer1Pct, pinPressureScore, playbook mode FADE/…, invalidation); `dealer-flow` (character TRANSITION/…, charmBias, vannaBias with horizons and zones); `delta-flow` (call/put premium, ask/bid side premium, sweep/block premium, NOPE score, institutionalBias, tradeCount — "[PB cache]"); `watch-levels` (PDL/PDH/ORH/ORL/PWH/PWL/PMH/PML/GEX_SUPPORT/RESISTANCE with sweepsToday); `timing` (charm/gamma/vanna pressure, velocity phase, hedging windows with weights, quality Q, urgency); `reversal-clock` (ten session windows with dealerBias and charmMultiplier); `market-tide` (5-min net call/put premium); `dark-pool` (NBBO-tagged buy-initiated %, dark volume %); `dp-levels` (dark-pool notional levels with polarity/status); `sigma-ladder` (σ rungs from VIX close, call/put walls by gross share); `displacement-signal`; `physics`.
- **Cross-ticker**: `/api/gex/expected-moves{,-batch}` (straddle-implied 1σ/2σ daily and weekly bands), `/api/gex/history`, `/api/gex/by-expiry`, `/api/gex/events` (ACCELERATOR_SURGE events with previous/current accelerator), `/api/dealer-chart/{t}/history` (per-minute GEX snapshots: `t,p,s[51],gf,mx,r,a,tg,tv,tc`), `/api/analysis/positioning-heatmap`, `/api/two-sided/desk` (per-ticker session stats: ADV, ATR, RS vs SPY/sector, rvol, classified share %), `/api/market-data/bars?ticker=&timeframe=1M|5M|1D&limit=` (server-proxied bars incl. index tickers), `/api/pulse/universe` (44 tickers with classification CORE/MAG7/EXTENDED, tradingMode, expiresToday), `/api/day-type/today` (OPEX_WEEK_TUE etc.), `/api/spx/config` (`paperTradeOnly: true, maxTradesPerDay: 3`), `/api/spx/paper-trades?days=30&ticker=&strategy=` (a separate `spx_gex_engine` paper book: 21 ^SPX trades in 30 days, confluence like `SPX_GEX:REGIME_BREAKOUT:BULLISH(100%)`, exits `SPX STOP LOSS (-26%)`), `/api/plays/today` (today's INDEX READ plan: contract, entry premium, 2× target, bell time), `/api/singles-surge/today` (single-name ignition records with chase limit, stop, aggressor, ask share, surge lots), `/api/lottos`, `/api/commander/flips`, `/api/flow-proxy` (Unusual Whales screener pass-through), `/api/trades?book=` (four books).
- **Admin-flagged config reads** made by ordinary pages: `/api/admin/dealer-chart-variant/config`, `/api/admin/pulse-redesign/config` (feature-flag reads; not probed further).

### 8.3 SSE event catalog (111 subscribed types; counts over a 100-second sample during RTH)
High-frequency: `sus_strike` 160, `block_snipe` 68, `physics` 55, `genome` 55, `dealer_read` 18, `velocity_burst` 18, `index_read` 12, `spx_timing` 11, `smart_money_campaign` 9, `dark_pool` 6, `reversal_clock` 5, and every ~20 s `gex`, `watch_levels`, `imbalances`, `delta_flow`, `market_tide`; `heartbeat` every ~25 s. On connect the server pushes one `*_snapshot` per subsystem (index_read, hold_advisor, trade_now, moc_wick, chop_day, positioning_heatmap, block_snipe, sus_strike, cross_index, cross_ticker, unified_trade_alert, etc.), then deltas. Payload samples (tokens redacted) are in `evidence/auth_pages/_sse_capture.json`; the first 600 events are kept.

Observed payload highlights:
- `index_read` / `index_read_snapshot`: `contributors[]` = {price, dealer, gex, flow, ict} each with a signed `vote` (e.g. price −0.64 "below VWAP/displacement", others 0), `conviction` (19–26), `tier`, `playSide`, `playStrike`, `exitBracket`, `sessionRange`, `dealerNodeContext` ("199k put OI (top-decile)"), `gexBook`, `loudIntent`, `shakeout`, `participation`. This is the committed-read lane: a five-contributor weighted vote, not the 100-tag ledger.
- `dealer_read`: same object as the REST endpoint, pushed every ~5 s.
- `sus_strike`: `{ticker, strike, side, expiration, triggers[PREMIUM_BURST|VELOCITY_SPIKE|…], severity, notional, tradeCount, sweepCount, blockCount, askSideCount, bidSideCount, largePrints, baselineMultiple, conviction, windowStartMs/EndMs (2-minute window), message, promotedFromStealth}`.
- `velocity_burst`: `{occ, burstLots, windowSec 90, ambientPerMin, relMult, sessionLots, premiumAtBurst, aggressor, askAggression, outcomeStatus}` — the "SURGE" family (lots vs ambient rate).
- `block_snipe`: candidate print (size, price, notional, askRatio, distancePct) scored on askAggression / gex / proximity / stall (range compression, volume dry-up).
- `trade_now_snapshot`: `{tier STRONG, trigger WICK_ARROW, entryNow, entryPremiumNow, reason text with WHAT/WHEN/WHEN TO SELL ("full close at +50% or hard stop at −40%; otherwise flat before the bell")}`.
- `hold_advisor_snapshot`: per contract `{family, verdict EXHAUSTING|…, track STALL, currentPct, peakPct, givebackFromPeakPct, minutesHeld, reasons[], ratchet floor}` — confirms the guardian ratchet (R05 in /research) and "gave back 34 % of the +59 % peak" style rules.
- `moc_wick_snapshot`: wick candidates with `wickLow`, `flushBodyTop`, `lateHigh`, `drawdownPct`, `volRatio`, `form TWO_BAR`, campaign tier.
- `chop_day_snapshot`: scored legs (premarketBalance, orCompression, rangeVsExpected, pinRegime, tapeChurn) summing to a chop score (7 → CONFIRMED) with ORB high/low and pin strike.
- `accumulation_snipe`: score breakdown (absorption, keyLevel, reclaim, velocity, volume) and metrics (spikeRatio, concentration, declineDecel, absorptionRatio, reclaimPct).
- `monster_capture`: multi-leg "desk rotation" detection (legs with askRatio, intent PUT_BUYING, notional, windowSecs).
- `genome` / `physics`: the exotic scoring families (codons per dimension TREND/MOMENTUM/STRUCTURE/LIQUIDITY/VOLATILITY/FLOW/GAMMA/ALIGNMENT…; helix condG, kappa, ricciMean, warp, tau) — internal metaphors over price/flow series; their outputs are the `GENOME:*` / `PHYSICS:*` / `HELIX_*` ledger tags.
- `signals` / `plans` / `trades`: raw PocketBase records (`collectionId pbc_…`) for the `signals`, `plans`, `trades` collections; `imbalances` exposes an `imbalance_zones` collection.

### 8.4 Books and engines (authenticated view)
`/api/trades?book=` returns four books. Beyond the 489-trade ICT Main book: **Trade Now** (`trade_now_v1`, 52 ^SPX trades 2026-07-09 → 10-12, total −$8,952, win rate 26.9 %, sizes up to 25 contracts, exits CLOSE_GUARDIAN_BREAKEVEN / TIME_STOP / GUARDIAN_TRAIL / WICK_STOP), **Singles TODAY** (`singles_today_v1`, 44 single-name trades 10-05 → 10-13, −$867, 34 % WR, context carries entry bid/ask, `maxTradeDebit 500`, `seed 25000`), **SPX Plans** (`spx_plan_v1`, 9 trades, +$370, publicationId `^SPX|P|2026-10-13|7800|INDEX_READ`, `liveConjuncts`). The `/trades` page shows only 30-day scorecards (Trade Now +$5,080 for the window), which hide the books' full-history results. A fifth paper engine (`spx_gex_engine`, `spx_displacement_sniper`) is visible only via `/api/spx/paper-trades`.
