#!/usr/bin/env bash
# Controlled source-to-systemd activation, with immediate rollback on failure.
# Run only after a reviewed, CI-green merge and release worktree verification.
set -euo pipefail
umask 077
EXPECTED_SHA="${1:?Expected verified main SHA required}"
ROOT=/home/u23u/else_itil_guided_v2_20261118/release_main
UNIT=else-itil-specialist-v1.service
DROP_DIR=/home/u23u/.config/systemd/user/else-itil-specialist-v1.service.d
DROP="$DROP_DIR/30-guided-v2.conf"
PRIVATE=/home/u23u/else_itil_sup_run/support_guided_v2_private
PY=/home/u23u/miniconda/envs/orquesta_py311/bin/python3.11
[ "$(git -C "$ROOT" rev-parse HEAD)" = "$EXPECTED_SHA" ] || {
  echo RELEASE_SHA_MISMATCH; exit 3;
}
[ ! -e "$DROP" ] || { echo REFUSE_OVERWRITE_EXISTING_DROPIN; exit 4; }
[ "$(systemctl --user is-active "$UNIT")" = active ] || {
  echo PREVIOUS_SERVICE_NOT_ACTIVE; exit 5;
}
install -d -m 700 "$PRIVATE"
install -d -m 700 "$DROP_DIR"
rollback() {
  rm -f "$DROP"
  systemctl --user daemon-reload
  systemctl --user restart "$UNIT"
  echo "ROLLED_BACK_TO_PREVIOUS_SYSTEMD_CHAIN"
}
trap rollback ERR
cat > "$DROP" <<EOF
[Service]
WorkingDirectory=$ROOT
ExecStart=
ExecStart=/bin/bash $ROOT/ops/run_specialist_v2_guided.sh
EOF
chmod 600 "$DROP"
systemctl --user daemon-reload
systemctl --user restart "$UNIT"
sleep 3
"$PY" - <<'PY'
from urllib.request import urlopen, Request
from urllib.error import HTTPError
import json
base='http://127.0.0.1:18883'
with urlopen(base+'/health',timeout=6) as r:
    h=json.load(r)
assert h["state"]=="READY"
assert h["guided_dialogue_enabled"] is True
assert h["qa_dispatch"]=="QA_HISTORICAL_READY"
assert h["repairs_enabled"] is False
for path in ('/v1/support','/v1/support/guided/start',
             '/v1/support/guided/continue','/v1/qa/investigate'):
    req=Request(base+path,method='POST',
        data=b'{}',headers={'Content-Type':'application/json'})
    try:
        urlopen(req,timeout=5)
        raise AssertionError('UNAUTHENTICATED_REQUEST_ACCEPTED')
    except HTTPError as err:
        assert err.code==401,(path,err.code)
print('GUIDED_V2_HEALTH_QA_LEGACY_AUTH_AND_PRIVATE_BIND_PASS')
PY
systemctl --user is-active "$UNIT"
echo DEPLOYMENT_GUIDED_V2_SOURCE_VERIFIED
trap - ERR
