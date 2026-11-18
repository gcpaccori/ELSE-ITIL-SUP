#!/usr/bin/env bash
# Governed V5 canary only. V2/V4 run independently and are never replaced.
set -euo pipefail
umask 077
ROOT=/home/u23u/else_itil_maturity_v5_20261118/release_main
PRIVATE=/home/u23u/else_itil_maturity_v5_20261118/canary_private
exec /home/u23u/miniconda/envs/orquesta_py311/bin/python3.11 \
 -m else_dominance.support_http \
 --host 127.0.0.1 --port 18914 \
 --db "$PRIVATE/legacy_attention.sqlite" \
 --guided-db "$PRIVATE/guided_sessions.sqlite" \
 --token-file /home/u23u/else_itil_sup_run/support_live_private/service.token \
 --guided-principals-file "$PRIVATE/guided_principals.sha256.private.json" \
 --guided-fast-handoff \
 --guided-max-inflight 2 \
 --guided-primary-timeout 35 \
 --guided-fallback-timeout 20 \
 --maturity-scorecard "$ROOT/data/2026_sep545_all_features_maturity_scorecard.json" \
 --maturity-source-summary "$ROOT/data/2026_sep545_full_maturity_evidence.json" \
 --human-review-status-file "$ROOT/data/novice_human_review_readiness_v5.json" \
 --base-url http://127.0.0.1:18782/v1 \
 --model else-itil-riv-qwen9b-gpu6 \
 --fallback-url http://127.0.0.1:8003/v1 \
 --fallback-model qwen35-4b
