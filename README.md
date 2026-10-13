# GeorgeFi reverse-engineering research for Slayer Terminal

Research workspace produced on 2026-10-13. Read the deliverables in this order:

1. `GEORGEFI_PRODUCT_MAP.md` — pages, features, controls, navigation (public surface complete; member surface blocked, see §1).
2. `GEORGEFI_SYSTEM_ARCHITECTURE.md` — evidence-backed architecture and data flow.
3. `GEORGEFI_SIGNAL_RESEARCH.md` — signal taxonomy, reconstructed rules, hypotheses with evidence and confidence, validation results.
4. `DATA_PROVIDER_AUDIT.md` — Unusual Whales and Massive entitlements, endpoints, limits.
5. `VALIDATION_PLAN.md` — datasets, tests, bias controls, metrics.
6. `SLAYER_INDEPENDENT_IMPLEMENTATION_SPEC.md` — original spec for Slayer Terminal.
7. `UNKNOWNS_AND_NEXT_STEPS.md` — blockers, open questions, next steps.

`evidence/` holds sanitized evidence: public page text, documented API responses, decoded SSR payloads, screenshots, REA observation output, provider catalogs and response samples, analysis outputs and the scripts that produced them. No credentials, cookies or tokens are stored anywhere in this repository. The minified GeorgeFi JS bundle and the raw market-data bar files are intentionally excluded (`.gitignore`); only derived listings are kept.
