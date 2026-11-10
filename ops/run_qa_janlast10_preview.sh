#!/usr/bin/env bash
# Jan 22–31 2026 QA-only cohort; separate queue and O5 receipt identity.
set -euo pipefail
umask 077
exec /home/u23u/miniconda/envs/orquesta_py311/bin/python \
 -m else_dominance.support_http \
 --host 127.0.0.1 --port 18885 \
 --db /home/u23u/else_itil_dispatch_janlast10_20261110/attention.preview.sqlite \
 --token-file /home/u23u/else_itil_sup_run/support_live_private/service.token \
 --base-url http://127.0.0.1:18782/v1 \
 --model else-itil-riv-qwen9b-gpu6 \
 --fallback-url http://127.0.0.1:8003/v1 \
 --fallback-model qwen35-4b \
 --qa-queue-db /home/u23u/else_itil_dispatch_janlast10_20261110/queue.sqlite \
 --qa-allowlist /home/u23u/else_itil_dispatch_janlast10_20261110/allowed_sha256.txt \
 --qa-cohort 2026-01-last10
