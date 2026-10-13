#!/bin/bash
# Public endpoint, no auth: one GET per trading day, 0.6 s apart; writes <date>.json and an index line (status, bytes, sha256).
OUT="$1"; DAYS="$2"
for d in $(python3 -I -c "import json,sys; print(' '.join(x for x in json.load(open(sys.argv[1])) if '2026-01-20'<=x<='2026-10-13'))" "$DAYS"); do
  code=$(curl -sS -o "$OUT/$d.json" -w '%{http_code}' --max-time 30 -A "Mozilla/5.0 (X11; Linux x86_64) Chrome/130.0" "https://georgefi.trade/api/public/todays-signals?date=$d")
  echo "$(date -u +%FT%TZ) $d $code $(stat -c %s "$OUT/$d.json") $(sha256sum "$OUT/$d.json" | cut -c1-16)" >> "$OUT/_index.txt"
  sleep 0.6
done
echo DONE >> "$OUT/_index.txt"
