# GeorgeFi reverse-engineering research for Slayer Terminal

Research workspace produced on 2026-10-13. Read the deliverables in this order:

1. `GEORGEFI_PRODUCT_MAP.md` — pages, features, controls, navigation (public surface complete; member surface blocked, see §1).
2. `GEORGEFI_SYSTEM_ARCHITECTURE.md` — evidence-backed architecture and data flow.
3. `GEORGEFI_SIGNAL_RESEARCH.md` — signal taxonomy, reconstructed rules, hypotheses with evidence and confidence, validation results.
4. `DATA_PROVIDER_AUDIT.md` — Unusual Whales and Massive entitlements, endpoints, limits.
5. `VALIDATION_PLAN.md` — datasets, tests, bias controls, metrics.
6. `SLAYER_INDEPENDENT_IMPLEMENTATION_SPEC.md` — original spec for Slayer Terminal.
7. `UNKNOWNS_AND_NEXT_STEPS.md` — blockers, open questions, next steps.
8. `BACKTEST_RESULTS.md` — independent backtest of the reconstructed strategy (144 variants, SPY/QQQ/IWM 0DTE, Jun 2025 – Oct 2026) with cost models, baselines and IS/OOS.
9. `STRATEGY_SPEC.md` — the strategy as reconstructed and tested: exact rules, parameters, verdict, and the paper-only configuration recommended for Slayer Terminal.
10. `reports/Finding a 0DTE options edge.md` — deep-research report on where a tradeable 0DTE edge could come from (per-strike bursts, dealer gamma/charm/vanna, dark pool, market tide, session effects, exit engineering): published evidence plus our own tests on 339 sessions. Verdict: no long-premium edge after costs; the only real premium is short vol, one spread wide.

`backtest/` holds the reproducible backtest code and the run outputs.

`research/` holds the code and derived outputs of the three empirical edge-search studies (`short_vol_session/`, `flow_predictors/`, `gex_regime_and_exits/`; each has a README or run script). `research_notes/Finding a 0DTE options edge/` holds the six research notes (three literature reviews, three empirical studies) the report was synthesized from. Raw bar pickles and grid arrays are gitignored and regenerable.

`evidence/` holds sanitized evidence: public page text, documented API responses (all four trade books, gzipped), decoded SSR payloads, screenshots, REA observation output, provider catalogs and response samples, the authenticated member-surface capture (`auth_pages/`, `auth_api/`, `auth_interactions/`, SSE sample), analysis outputs and the scripts that produced them. No credentials, cookies, auth tokens or the account e-mail are stored anywhere in this repository (automated redaction, then grep-verified). The minified GeorgeFi JS bundle and the raw market-data bar files are intentionally excluded (`.gitignore`); only derived listings and compressed archives are kept.
