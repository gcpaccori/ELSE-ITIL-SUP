#!/usr/bin/env bash
# Backwards-compatible ELSE-ITIL shadow service + optional QA NuGet dispatcher.
# /v1/support is unchanged; new /v1/qa/* routes use the outbound Windows worker.
set -euo pipefail
umask 077
exec /home/u23u/miniconda/envs/orquesta_py311/bin/python \
 -m else_dominance.support_http \
 --host 127.0.0.1 --port 18883 \
 --db /home/u23u/else_itil_sup_run/support_specialist_v1_private/attention.sqlite \
 --token-file /home/u23u/else_itil_sup_run/support_live_private/service.token \
 --base-url http://127.0.0.1:18782/v1 \
 --model else-itil-riv-qwen9b-gpu6 \
 --fallback-url http://127.0.0.1:8003/v1 \
 --fallback-model qwen35-4b \
 --qa-queue-db /home/u23u/else_itil_dispatch_qa_20261110/queue.sqlite \
 --qa-allowlist /home/u23u/else_itil_dispatch_qa_20261110/allowed_sha256.txt
