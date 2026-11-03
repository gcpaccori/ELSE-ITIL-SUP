#!/usr/bin/env bash
set -euo pipefail
umask 077
BASE_DIR=/home/u23u/else_itil_sup_run
PRIVATE_DIR="$BASE_DIR/support_specialist_v1_private"
TOKEN_FILE="$BASE_DIR/support_live_private/service.token"
PYTHON_BIN=/home/u23u/miniconda/envs/orquesta_py311/bin/python
if [[ ! -f "$TOKEN_FILE" ]]; then
  echo "ERROR: SERVICE_TOKEN_MISSING" >&2
  exit 1
fi
mkdir -p "$PRIVATE_DIR"
chmod 700 "$PRIVATE_DIR"
# Strict localhost, Qwen9B primary, Qwen4B unmodified backup.
exec "$PYTHON_BIN" -m else_dominance.support_http \
  --host 127.0.0.1 --port 18883 \
  --db "$PRIVATE_DIR/attention.sqlite" \
  --token-file "$TOKEN_FILE" \
  --base-url http://127.0.0.1:18782/v1 \
  --model else-itil-riv-qwen9b-gpu6 \
  --fallback-url http://127.0.0.1:18781/v1 \
  --fallback-model else-itil-riv-gpu7
