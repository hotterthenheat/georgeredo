# trades.csv columns
- epoch_number / epoch_id / book: from /api/epochs and the pull used (`source_file`).
- side: CALL / PUT / SHARES parsed from `action`. strike: reported `strike`, or parsed from the OCC symbol when 0/missing.
- occ: GeorgeFi `optionSymbol` (the Massive/Polygon-style OCC of GeorgeFi's own provider, e.g. O:SPXW260227P06875000); occ_root: SPXW/NDXP/RUTW/SPY...; expiration: `expiration_date` or parsed from the OCC.
- entry_utc/exit_utc: `entryTime`/`exitTime` as given (UTC); *_et converted to America/New_York; hold_min = exit - entry.
- is_0dte: expiration equals the ET entry date.
- entry_premium/exit_premium/size/initial_size/pnl_reported/pnl_pct_reported: as reported by GeorgeFi (reported results, not independent).
- pnl_recomputed = (exit - entry) x 100 x size for options, x size for shares; pnl_mismatch = |reported - recomputed| > $1 (partials/scale-ins explain most).
- data_error: exit reason contains DATA ERROR / INVALID.
- n_confluence: number of confluence tags on the ledger; gex_regime/entry_source/confidence/high_water_mark: Epoch 2 only where present.
