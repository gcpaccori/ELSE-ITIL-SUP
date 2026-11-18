#!/usr/bin/env bash
# Opt-in guided support V2. Preserves legacy /v1/support and QA dispatcher.
# This script is designed for the authenticated, loopback-only systemd user unit.
set -euo pipefail
umask 077
exec /home/u23u/miniconda/envs/orquesta_py311/bin/python \
  -m else_dominance.support_http \
  --host 127.0.0.1 --port 18883 \
  --db /home/u23u/else_itil_sup_run/support_specialist_v1_private/attention.sqlite \
  --guided-db /home/u23u/else_itil_sup_run/support_guided_v2_private/sessions.sqlite \
  --token-file /home/u23u/else_itil_sup_run/support_live_private/service.token \
  --base-url http://127.0.0.1:18782/v1 \
  --model else-itil-riv-qwen9b-gpu6 \
  --fallback-url http://127.0.0.1:8003/v1 \
  --fallback-model qwen35-4b \
  --qa-queue-db /home/u23u/else_itil_dispatch_qa_20261110/queue.sqlite \
  --qa-allowlist /home/u23u/else_itil_dispatch_qa_20261110/allowed_sha256.txt
