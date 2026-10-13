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
