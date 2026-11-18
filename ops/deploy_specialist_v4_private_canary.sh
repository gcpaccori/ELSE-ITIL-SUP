#!/usr/bin/env bash
# Does not modify the existing V2 systemd unit. Guarded source lease and rollback.
set -euo pipefail
umask 077
EXPECTED_SHA="${1:?Merged main SHA required}"
ROOT=/home/u23u/else_itil_guided_v4_20261118/release_main
UNIT=else-itil-novice-v4-canary.service
DEST=/home/u23u/.config/systemd/user/$UNIT
PRIVATE=/home/u23u/else_itil_guided_v4_20261118/canary_private
PY=/home/u23u/miniconda/envs/orquesta_py311/bin/python3.11

[ "$(git -C "$ROOT" rev-parse HEAD)" = "$EXPECTED_SHA" ] || {
 echo RELEASE_SHA_MISMATCH; exit 3;
}
[ ! -e "$DEST" ] || { echo CANARY_ALREADY_INSTALLED; exit 4; }
[ "$(systemctl --user is-active else-itil-specialist-v1.service)" = active ] || {
 echo V2_MUST_REMAIN_ACTIVE; exit 5;
}
[ ! -e "$PRIVATE" ] || { echo REQUIRE_FRESH_PRIVATE_CANARY_DIRECTORY; exit 6; }
install -d -m 700 "$PRIVATE"
install -m 600 "$ROOT/ops/systemd/$UNIT" "$DEST"
rollback() {
 systemctl --user stop "$UNIT" || true
 rm -f "$DEST"
 systemctl --user daemon-reload
 echo CANARY_ROLLBACK_V2_UNTOUCHED
}
trap rollback ERR
systemctl --user daemon-reload
systemctl --user start "$UNIT"
sleep 3
"$PY" - <<'PY'
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json
for port,expected_qa in ((18883,True),(18913,False)):
    base=f'http://127.0.0.1:{port}'
    with urlopen(base+'/health',timeout=5) as r:
        h=json.load(r)
    assert h['state']=='READY' and h['repairs_enabled'] is False
    assert h['guided_dialogue_enabled'] is True
    assert (h.get('qa_dispatch')=='QA_HISTORICAL_READY')==expected_qa
    for path in ('/v1/support','/v1/support/guided/start',
                 '/v1/support/guided/continue'):
        req=Request(base+path,data=b'{}',
            headers={'Content-Type':'application/json'})
        try:
            urlopen(req,timeout=4)
            raise AssertionError('AUTH_MISSING_BUT_ACCEPTED')
        except HTTPError as e:
            assert e.code==401,(port,path,e.code)
print('PRIVATE_V4_CANARY_WITH_V2_STILL_LIVE_PASS')
PY
[ "$(systemctl --user is-active "$UNIT")" = active ] || exit 8
[ "$(systemctl --user is-active else-itil-specialist-v1.service)" = active ] || exit 9
[ "$(ss -lnt | grep -c '127.0.0.1:18913')" -eq 1 ] || exit 10
echo CANARY_V4_READY_V2_UNMODIFIED
trap - ERR
