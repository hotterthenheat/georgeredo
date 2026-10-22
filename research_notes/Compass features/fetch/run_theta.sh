#!/bin/bash
# Detached ThetaData fetch (one SDK login; waits out 00:00-01:45 New York itself). Resumable: just run it again.
SP=/tmp/claude-0/-home-user-georgeredo/c2861f8a-c5af-5ae3-9258-5ee40d17d74a/scratchpad
cd "$(dirname "$0")"
set -a; . "$SP/secrets/research.env"; set +a
python3 -I fetch_features.py theta 2>&1 | sed -u -E 's/td1_prod_[A-Za-z0-9_-]+/[key]/g' >> "$SP/features_data/theta_stdout.log"
