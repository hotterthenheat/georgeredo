# GEORGEFI_PRODUCT_MAP

Research date: 2026-10-13 (US market session open during observation).
Site build observed: `2026.10.13-083911-af712b2f9` (footer of every page).
Scope: everything reachable **without** a member login, plus the member-only route list recovered from public application metadata. Member-only pages were **not** opened (see "Authentication status").

Evidence conventions used in this file:

- `[E-html:<page>]` = server-rendered HTML + extracted text in `evidence/public_pages_text/<page>.txt`
- `[E-ssr:<page>]` = decoded Nuxt SSR payload in `evidence/ssr_payloads/<page>.json`
- `[E-api:<name>]` = documented public REST response saved in `evidence/public_api/`
- `[E-shot:<name>]` = screenshot in `evidence/screenshots/<name>.png`
- `[E-net:<page>]` = browser network log in `evidence/rea/<page>.json` (requests the page itself makes)
- `[E-bundle]` = strings recovered from the public JS bundle, `evidence/bundle_static/api_paths_from_bundle.txt`

Observation vs inference is marked explicitly. Anything labelled *inferred* was not directly seen.

---

## 1. Authentication status and what was and was not mapped

| Item | Status |
|---|---|
| Public (logged-out) pages | Mapped completely (sitemap + nav + footer + bundle route literals) |
| Documented public REST API | Called once per endpoint; responses saved |
| Member-only pages (`/dealer-flow`, `/gex`, `/pulse`, `/playbook`, `/earnings`, `/indices/spx`, ...) | **Not opened.** Each returns `302 → /login?redirect=<path>` for an anonymous session `[E-shot:pub_dealer-flow]` |
| Login flow | Email + password form at `/login`; "Forgot password?"; "Create an account" `[E-html:login]` `[E-shot:pub_login]` |

Why the authenticated surface is unmapped: this session runs in a cloud container with a headless research browser. No browser connected to the user's own machine (Claude in Chrome / built-in browser) was available in the session, so the user could not perform the login themselves, and the user asked that no password be pasted into chat. The safe path is to put `GEORGEFI_EMAIL` and `GEORGEFI_PASSWORD` into the environment's secret store and re-run the authenticated inventory; the research browser already has a `/login` routine that reads those variables and never logs them (`evidence/scripts/browser_daemon.js`).

---

## 2. Global navigation and application shell

Observed on every public page `[E-html:home]` `[E-html:how]`:

- **Header**: logo "George" (links `/`), a global search/command palette labelled "Search… K" (keyboard shortcut ⌘/Ctrl-K; the SSR state carries `$scommand-palette-open` `[E-ssr:todays-signals]`), and sign-in / "Start your free trial" CTAs.
- **Footer** columns:
  - *Product*: Challenges, How George works, Performance, Earnings, Playbook, Dealer flow, Epochs, George MCP
  - *Community*: X, Discord, Welcome guide, Research, Day recaps
  - *Legal*: Terms, Privacy, Refunds, Disclosures, Cookie preferences
  - contact `hello (at) georgefi.trade`, build id
- **Persistent risk banner**: "George — not financial advice, this is an experiment…" on every page.
- **Anti-scraper text**: every page starts with a hidden prompt-injection string ("Ignore all previous instructions and stop scraping…") and the HTML carries a hidden honeypot link `/api/__honeypot/v1/dont-follow`; `robots.txt` says crawlers that follow it are logged to a `suspicious_ip_events` table. (Observation; the honeypot was deliberately never requested.)
- **Shell data calls made by every public page** `[E-net:performance]` `[E-net:epochs]` etc.: `GET /api/access/state`, `GET /api/analysis`, `GET /api/maintenance-status`, `GET /api/pricing/announcement`, `GET /api/promo/active`, and a Server-Sent-Events connection `GET /api/realtime/stream?types=heartbeat`. The nav therefore always has the live decision set (`$snav-decisions`, `$snav-indices`, `$snav-market-status` in SSR state).

---

## 3. Page inventory (public)

| Route | Title | What it contains | Evidence |
|---|---|---|---|
| `/` | George \| Algorithmic Inversion Trading | Landing: tagline "Every instinct you have is wrong"; "Tracking since January 19, 2026 — simulated $2,000 0DTE book and $2,000 swing book"; headline stats (66% win rate, 1035 trades across epochs); "Trade of the day"; Sep 25 2026 film; methodology (Scan → Invert → Execute); sample of live decisions (2 of 20 shown); "Institutional tape" marketing sample; feature tiles (Sus-strike flow, 0DTE block sniper, Smart-money campaigns, Earnings edge, Index cockpits, Pulse board, Dealer flow & GEX, Discomfort scoring, Weekly playbook); plans | `[E-html:home]` `[E-ssr:home]` `[E-shot:home_public]` |
| `/how` | How George Works | Full published methodology ("The Costanza Protocol"): ICT concepts, scan cadence (every minute), confluence stack, sweep/reversal logic, gates & grading, inversion rule, special situations (sweep reversals, GEX magnet, institutional flips, sus-strike, counter-trend divergence, power hour), risk management (VIX-aware trails, daily limits, sizing, exit tiers), daily timeline, limits | `[E-html:how]` `[E-shot:pub_how]` |
| `/guide` | How to Read Every Alert | Member field guide: alert card anatomy (first word, contract, WHAT, ▶ line, WHY), four word-classes (buy / manage / wait / paper), SURGE ≠ direction lesson, a worked day (Sep 25), catalog of every alert type with action rules, "your day with George" timeline, glossary, plan table. Tabs: All, Apex, Buy & Forget, Surge, Weeklies, Rotation, Playbook, Other | `[E-html:guide]` `[E-shot:pub_guide]` |
| `/performance` | Performance Tracker | Epoch selector (Active Epoch / Overall); overall P&L, ROI, win rate, trades, avg win/loss, profit factor, balance; 0DTE vs Swing account cards; scalp and swing stats; risk block (max/avg drawdown, Sharpe, win/loss ratio, largest win); cumulative P&L chart; last-30-day daily table; by-ticker (27) table; by-setup-grade table | `[E-html:performance]` `[E-ssr:performance]` `[E-api:performance]` `[E-shot:pub_performance]` |
| `/epochs` | Trading Epochs | Epoch 1 (Jan 5 – Feb 27 2026, 546 trades, 78.8% WR, +540.6%) vs Epoch 2 (Feb 27 – ongoing, 489 trades, 51.7% WR, +39.7%); by-ticker breakdown per epoch; notes | `[E-html:epochs]` `[E-ssr:epochs]` |
| `/strategies` | Strategies | Four tracked strategy books with balances: ICT George v2.0.0-ict (Main, 23 trades in 30-day window), Costanza Protocol v1.0.0 (no trades), 100k V1, 100k ICT (no trades); position-sizing and strike-selection policy by account size and time of day | `[E-html:strategies]` `[E-ssr:strategies]` |
| `/challenges` | George's Challenges | "Watch George Lose $500" challenge: $500 → $615.25, 114 trades, 52% WR, tickers SPY/QQQ/IWM; config block exposes `ticker_licker_config` (fixedContracts 4, maxPremium 0.5, maxTickers 3, minConfidence 80, schedule Thu 15:30) | `[E-html:challenges]` `[E-ssr:challenges]` |
| `/research` | Research library | 13 frozen internal studies R01–R13 with verdicts (mostly REFUSED / NO EDGE / lookahead artifact); "house rules" for what counts as real | `[E-html:research]` |
| `/recaps` and `/recaps/<date>` | Day recaps | 9 session recaps (Sep 25 – Oct 12 2026): 45–56 s video per day, alert-by-alert timeline with entry price, one-minute-high peak, exit call and source record ids | `[E-html:recaps_*]` `[E-ssr:recaps_*]` |
| `/todays-signals` | Today's Signals | Public signal tape: last 200 alerts of the session, auto-refresh every 30 s; day tabs (today + 7 prior sessions); "My tickers" pinning; family chips (SPX/NDX/RUT/Other), DTE chips (0DTE/1DTE/≤1W/1W+), "High attention", "All types" filter; paper-book summary | `[E-html:todays-signals]` `[E-ssr:todays-signals]` `[E-shot:pub_todays-signals]` |
| `/pricing` | Pricing | Plans: The George (free, delayed 15 min), The SPX ($259/mo Discord-only ^SPX 0DTE), The Pup ($649/mo), The Bob ($1,169/mo); 24 h card-required trial. Prices in CAD per Stripe product payload | `[E-html:pricing]` `[E-ssr:pricing]` |
| `/mcp`, `/mcp/pricing` | George MCP | Separate paid product: 22 market tools over authenticated MCP (Indie $65/mo 10K calls, Pro $325/mo 100K calls, Enterprise); x402 per-call rail; discovery endpoint | `[E-html:mcp]` `[E-api:mcp_discovery]` |
| `/docs/api` | API Documentation | Public read-only REST reference (12 endpoints + nerve calibration) | `[E-html:docs_api]` `[E-shot:pub_docs_api]` |
| `/welcome` | Welcome | Onboarding narrative; describes Weeklies, Apex prints & Trade Now, Buy & Forget / Full size, MOC wick; setup steps (trial, Discord link, SMS alerts, MCP) | `[E-html:welcome]` |
| `/login`, `/register` | Sign in / Create account | Email+password; registration requires ToS acceptance incl. §7 Discord-content clause | `[E-html:login]` `[E-html:register]` |
| `/terms`, `/privacy`, `/refunds`, `/disclosures`, `/sms-policy` | Legal | Standard legal pages | `[E-html:*]` |

Pages that return 404 as anonymous: `/signals`, `/dashboard` (the dashboard is the logged-in home; "Back to dashboard" links appear on public pages).

---

## 4. Member-only route inventory (recovered, not opened)

Observed as redirecting to login: `/playbook`, `/dealer-flow`, `/gex`, `/pulse`, `/earnings`, `/indices/spx`.

Route literals present in the public JS bundle (command-palette labels, `[E-bundle]`, chunk `DEdQQlOZ.js`): `/zero-dte`, `/weeklies`, `/week-ahead`, `/trades`, `/swings`, `/spx-swings`, `/situation-room`, `/rotation`, `/pulse`, `/portfolio`, `/playbook`, `/lottos`, `/indices/spx`, `/hold`, `/gex`, `/flow-alerts`, `/flow`, `/dealer-flow`, `/account`. The guide also names `/spx` (SPX cockpit), `/account/mcp`, and index cockpits for `^NDX` and `^RUT`.

What each one is *described* to contain (from `/guide`, `/welcome`, `/how`, `/mcp` — descriptions only, not verified):

- **SPX cockpit** (`/spx`, `/indices/spx`): live committed read, alert tape, dealer levels, GEX walls, pin gravity, game plan.
- **Hold** (`/hold`): every open play George called and its position on the hold ladder (STAY IN / LOCK HALF / LOCK MOST / GET OUT).
- **Weeklies** (`/weeklies`): weekly open-interest desk; per-name plan with one invalidation level.
- **Pulse** (`/pulse`): every ticker ranked by relative volume, loaded strikes, flow.
- **Playbook** (`/playbook`), **Rotation** (`/rotation`): weekly dealer positioning plan; sector / cross-ticker rotation and SMT divergences.
- **Dealer flow / GEX** (`/dealer-flow`, `/gex`): gamma, charm, vanna ladders and dealer read.
- **Flow / Flow alerts** (`/flow`, `/flow-alerts`): institutional tape, sus-strike events.
- **Trades / Portfolio** (`/trades`, `/portfolio`): live and paper books.
- **Zero-DTE, Lottos, Swings, SPX swings, Situation room, Earnings, Week-ahead**: self-descriptive from MCP tool catalog (`get_zero_dte_scan`, `get_ticker_licker`, `get_swing_scan`, `get_sniper_swings`, `get_situation_room`, `get_earnings_calendar`).
- **Account** (`/account`, `/account/mcp`): Discord link, SMS verification, MCP keys (up to 10, shown once, stored hashed).

---

## 5. Feature inventory (what is actually present vs marketing)

| Feature claimed on landing | Public evidence that it exists | Status |
|---|---|---|
| Live decisions for ~20 tickers with confidence, grade, contract, premium | `/api/analysis` returns 20 decision objects with 30–100 confluence tags each | **Confirmed** |
| Sus-strike flow detection (notional spikes, sweeps, stealth accumulation) | Public tape: 120/200 signals on 2026-10-13 are `sus-strike` with kinds STEALTH LIGHT/BUILDING/HEAVY, BURST STRONG/EXTREME, KILLER, DIVERGENCE; MCP `get_sus_strikes` schema lists triggers NOTIONAL_SPIKE / PREMIUM_BURST / SWEEP_CLUSTER / VELOCITY_SPIKE / STEALTH_ACCUMULATION | **Confirmed** (outputs), mechanism not visible |
| 0DTE block sniper | `block-sniper` subsystem signals on public tape; recap alerts "BLOCK SNIPER — SPY $768P 0DTE" | **Confirmed** (outputs) |
| Smart-money campaigns | `/api/analysis/smart-money` path in bundle; "ACCUMULATING STRONG" / `accumulation-sniper` tape kinds | Present (outputs) |
| Earnings edge | `get_earnings_calendar` MCP tool; `/earnings` route (gated); trade fields `earnings_*` | Present |
| Index cockpits (SPX/NDX/RUT) | gated; MCP `get_index_read`, `get_current_read`, `get_spx_sniper` | Present (gated) |
| Pulse board | gated route; glossary | Present (gated) |
| Dealer flow & GEX (gamma, charm, vanna) | `/api/analysis` decisions carry `gexProfile` (totalGEX, gammaFlip, maxGEXStrike, regime, pinRisk, acceleratorScore); MCP `get_gex_snapshot` sample shows per-strike callGamma/putGamma/netVanna/netCharm | **Confirmed** (outputs) |
| Discomfort scoring | `discomfort_score` field exists but equals `confidence` in every observed decision and is `0` on all 489 historical trades | **Vestigial / renamed** (observation) |
| Weekly playbook (Mon–Fri ICT profiles + dealer ladder) | gated; `weeklyProfile` types appear in decisions (TUESDAY_LOW_BULLISH, …) | Present |
| Hold Advisor (STAY IN / LOCK HALF / LOCK MOST / GET OUT) | `hold-advisor` subsystem on public tape; recap exits | **Confirmed** |
| MOC wick, Apex prints, Trade Now, Buy & Forget, Full size reads | recap families `moc_wick`, `apex_unwind`, `buy_and_forget`, `full_size`; MCP tools `get_apex_prints`, `get_trade_now` | **Confirmed** (outputs) |
| "Nerve" 30-minute ^SPX probabilistic forecast | documented `/api/nerve/calibration` returning `no_active_model` | Documented, inactive |

---

## 6. Controls and how they change outputs (public pages only)

| Page | Control | Effect observed |
|---|---|---|
| `/todays-signals` | Day tabs (Today, Mon 10/12 … Tue 10/6) | Client fetches `GET /api/public/todays-signals?date=YYYY-MM-DD` and re-renders the 200-row tape `[E-net]`; 8 sessions available |
| `/todays-signals` | Family chips SPX / NDX / RUT / Other, DTE chips 0DTE / 1DTE / ≤1W / 1W+, "High attention", "All types" | Client-side filters over the loaded 200 rows (counts shown in chips: SPX 14, NDX 4, RUT 9, Other 173; 0DTE 29, 1DTE 22, ≤1W 30, 1W+ 78; High attention 14) |
| `/todays-signals` | "My tickers" | Pins user-chosen tickers (local preference) |
| `/todays-signals` | auto-refresh | Re-polls every 30 s (page text) |
| `/performance` | Active Epoch / Overall | Switches metrics between epoch 2 and both epochs (`performance-epochs` payload) |
| `/performance` | Cumulative / Daily, Last 30 days | Chart mode toggle; data already in SSR payload |
| `/guide` | Tabs All / Apex / Buy & Forget / Surge / Weeklies / Rotation / Playbook / Other; glossary filter; "Which alert is this?" search | Client-side section switching and text filtering |
| `/recaps/<date>` | Voice-over / Music only; tap-a-dot timeline; J/K keys | Video cut selection (`tape-dark-16x9` etc.) and chart scrubbing |
| `/pricing` | monthly vs other intervals | Stripe prices array has 4 intervals per product |
| Landing | 16:9 / 9:16 film variants | Poster/video assets on DigitalOcean Spaces |

No public control changes any server-side analytical parameter (timeframe, instrument, threshold). Those controls, if any, live behind login and were not observed.

---

## 7. Data timestamps, refresh behaviour, loading states, errors

- `/api/analysis` carries `updatedAt` (response build time) and per-decision `timestamp`/`generatedAt`; index decisions were 1–2 minutes old, single names up to ~30 minutes old at observation (`[E-api:analysis]`, 14:16 UTC). Consistent with the documented "every minute" cycle for core tickers and a slower cycle for single names.
- Decisions carry `expiresAt` = generation time + 7 days and `active: true`.
- Public tape rows have minute-resolution `at` timestamps (seconds zeroed) `[E-ssr:todays-signals]`; recap alerts have second resolution `[E-ssr:recaps_*]`.
- `/api/options/prices` returns NBBO mid/bid/ask with `source: "nbbo"`, `isLive: true` and a server timestamp `[E-api:options_prices_sample]`.
- SSE stream first event: `{"clientId":…,"strategyVersion":"v2.0.0-ict","types":["heartbeat"],"authenticated":false,"tier":"public","marketStatus":"OPEN"}` — tiers are enforced per connection.
- `/api/signals` for anonymous returns `{"signals":[],"authenticated":false}`: the watching-signal feed is gated even though the docs page shows it as public.
- `/api/access/state` exposes an "open access" feature flag (`active:false`, `grantTier: premium`, banner text "Free preview is live…") — a site-wide free-preview switch exists.
- `/api/maintenance-status` → `{active:false}`.
- No loading-state errors were observed on public pages; all shell calls returned 200.

---

## 8. Disclosed methodology, risk warnings, data-provider references

- Methodology is disclosed in unusual detail on `/how` (gates, grades A+…B-, VIX-scaled trails 8/11/14%, sweep stop -32%, daily loss stop $300 or 5%, max 8–10 trades/day, one position per ticker with 30-min cooldown, T1 +25% sell half, T2 +45%, breakeven lock at +6% HWM, GEX-lotto tiers +200/+400/+500%, auto-close 15:58 ET, swings ≤14 days with ATR+level stops).
- `/research` discloses that the operator's own studies found **no independent SPX 0DTE edge** (R04) and refuted a whale-hold edge as a lookahead artifact (R13).
- Risk warnings: "not financial advice, this is an experiment" on every page; 0DTE loss warnings in guide and how pages; recaps state "Peaks are one-minute highs, not fills".
- Data providers referenced: **Massive** (recap source ids `massive:O:SPXW261012P07800000@14:52`; CSP `wss://socket.massive.com`), **Unusual Whales** (CSP `wss://*.unusualwhales.com`), Stripe, Google Analytics, Cloudflare, DigitalOcean Spaces, Discord webhooks, PocketBase (`collectionId: pbc_…`, `/api/collections/`, `/api/realtime`). The API docs page still describes a Firebase/Firestore backend; the live `/api/health` response no longer mentions Firebase, so that text is stale.

---

## 9. Interaction map (public)

```
anonymous browser
  ├─ GET / (SSR, Nuxt)  ── shell calls: access/state, analysis, maintenance-status, pricing/announcement, promo/active, themes/active, geo/country
  │                        ── SSE: /api/realtime/stream?types=heartbeat (tier=public)
  │                        ── landing extras: /api/options/prices?symbols=O:…  (NBBO for the teaser contracts), /api/portfolio
  ├─ /todays-signals ─── /api/public/todays-signals?date=…  (on day-tab click)
  ├─ /performance, /epochs, /strategies, /challenges, /recaps ── data embedded in SSR payload (no extra calls)
  ├─ /pricing ─── /api/tier-availability
  ├─ /docs/api ─── documents: analysis, portfolio, performance, ict-analysis, signals, ict-summaries, market-prep, trades, strategy, plans, volume-status, health, nerve/calibration
  └─ gated route ─── 302 /login?redirect=<route>
```

Observed-but-not-called endpoints in the bundle (admin or member scope, deliberately not probed): `/api/scheduler/*` (morning-analysis, opening-bell-prep, premarket-bias, ticker-licker, daily-recap), `/api/backups/*`, `/api/sql`, `/api/crons`, `/api/logs`, `/api/settings/*`, `/api/user/notifications`, `/api/stripe/*`, `/api/auth/*`, `/api/analysis/smart-money`, `/api/analysis/opening-participation`, `/api/analysis/contract-convexity-radar`, `/api/featured-trade`, `/api/public/recent-wins`, `/api/public/equity-curve`, `/api/epochs`, `/api/strategies`, `/api/challenges`, `/api/recaps`, `/api/plans/post-market`, `/api/waitlist/*`, `/api/files/token`, `/api/batch`.
