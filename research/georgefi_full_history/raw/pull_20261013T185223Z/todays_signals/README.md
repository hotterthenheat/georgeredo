# Public /api/public/todays-signals?date= history pull (2026-10-13)

184 trading days 2026-01-20..2026-10-13 were requested (see _index.txt: status, bytes, sha256 per request). The endpoint only honours dates listed in its `availableSessions` (the last 8 sessions); for every other date it returned the CURRENT session payload (sessionEt=2026-10-13, historical=false). Those non-historical duplicates were deleted; only payloads whose sessionEt equals the requested date are kept: 2026-10-06, 2026-10-07, 2026-10-08, 2026-10-09, 2026-10-12.
