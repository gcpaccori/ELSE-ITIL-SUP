#!/usr/bin/env bash
# Guarded additive V4 activation. Preserves the original and V2 systemd chain.
set -euo pipefail
umask 077
EXPECTED_SHA="${1:?Provide exact merged SHA}"
ROOT=/home/u23u/else_itil_guided_v4_20261118/release_main
UNIT=else-itil-specialist-v1.service
DROP_DIR=/home/u23u/.config/systemd/user/else-itil-specialist-v1.service.d
DROP="$DROP_DIR/40-guided-v4.conf"
PREVIOUS="$DROP_DIR/30-guided-v2.conf"
PY=/home/u23u/miniconda/envs/orquesta_py311/bin/python3.11
[ "$(git -C "$ROOT" rev-parse HEAD)" = "$EXPECTED_SHA" ] || {
  echo RELEASE_SHA_MISMATCH; exit 3;
}
[ -f "$PREVIOUS" ] || { echo PREVIOUS_GUIDED_VERSION_NOT_INSTALLED; exit 4; }
[ ! -e "$DROP" ] || { echo REFUSE_OVERWRITE_V4_DROPIN; exit 5; }
[ "$(systemctl --user is-active "$UNIT")" = active ] || {
  echo OLD_SERVICE_NOT_ACTIVE; exit 6;
}
cd "$ROOT"
"$PY" -m pytest -q "$ROOT/tests/test_guided_novice_v4.py"                        "$ROOT/tests/test_guided_dialogue_v2.py" >/dev/null
rollback() {
  rm -f "$DROP"
  systemctl --user daemon-reload
  systemctl --user restart "$UNIT"
  echo "ROLLBACK_TO_GUIDED_V2"
}
trap rollback ERR
install -d -m 700 "$DROP_DIR"
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
base="http://127.0.0.1:18883"
with urlopen(base+"/health",timeout=5) as r:
    h=json.load(r)
assert h["state"]=="READY"
assert h["guided_dialogue_enabled"] is True
assert h["qa_dispatch"]=="QA_HISTORICAL_READY"
assert h["repairs_enabled"] is False
for route in ("/v1/support","/v1/support/guided/start",
              "/v1/support/guided/continue","/v1/qa/investigate"):
    req=Request(base+route,method="POST",data=b'{}',
                headers={"Content-Type":"application/json"})
    try:
        urlopen(req,timeout=5)
        raise AssertionError("UNAUTHENTICATED_REQUEST_ACCEPTED")
    except HTTPError as err:
        assert err.code==401,(route,err.code)
print("GUIDED_V4_HEALTH_AUTH_QA_AND_NO_REPAIRS_PASS")
PY
[ "$(systemctl --user is-active "$UNIT")" = active ] || exit 7
test "$(ss -lnt | grep -c '127.0.0.1:18883')" -eq 1
echo DEPLOY_GUIDED_V4_VERIFIED
trap - ERR
