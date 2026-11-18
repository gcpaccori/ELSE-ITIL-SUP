#!/usr/bin/env bash
# Independent private novice guidance canary, NEVER replaces the V2 service.
set -euo pipefail
umask 077
exec /home/u23u/miniconda/envs/orquesta_py311/bin/python \
 -m else_dominance.support_http \
 --host 127.0.0.1 --port 18913 \
 --db /home/u23u/else_itil_guided_v4_20261118/canary_private/legacy_attention.sqlite \
 --guided-db /home/u23u/else_itil_guided_v4_20261118/canary_private/guided_sessions.sqlite \
 --token-file /home/u23u/else_itil_sup_run/support_live_private/service.token \
 --base-url http://127.0.0.1:18782/v1 \
 --model else-itil-riv-qwen9b-gpu6 \
 --fallback-url http://127.0.0.1:8003/v1 \
 --fallback-model qwen35-4b
