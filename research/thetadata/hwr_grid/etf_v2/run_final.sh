#!/bin/bash
# After every ticker's stage: TEST evaluation, integrity summary, band validation, settlement, stress, gates, RESULTS.md.
set -e
cd "$(dirname "$0")"
echo "$(date -u +%FT%TZ) final start"
python3 analyze.py test
python3 integrity_summary.py
python3 validate_band.py
python3 settlement.py
python3 stress.py
python3 gates.py
python3 report.py
echo "$(date -u +%FT%TZ) final done"
