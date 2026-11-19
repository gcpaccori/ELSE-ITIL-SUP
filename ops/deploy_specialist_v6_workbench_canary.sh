#!/usr/bin/env bash
# Exact main SHA, separate port, separate secrets and rollback. No V2-V5 edits.
set -euo pipefail
umask 077
EXPECTED="${1:?Specify exact postmerge main SHA}"
ROOT=/home/u23u/else_itil_workbench_v6_20261119/release_main
PRIVATE=/home/u23u/else_itil_workbench_v6_20261119/canary_private
UNIT=else-itil-workbench-v6-canary.service
DEST=/home/u23u/.config/systemd/user/$UNIT
PY=/home/u23u/miniconda/envs/orquesta_py311/bin/python3.11

[ "$(git -C "$ROOT" rev-parse HEAD)" = "$EXPECTED" ] || {
 echo HANDOFF_RELEASE_LEASE_MISMATCH;exit 3; }
[ ! -e "$PRIVATE" ] || { echo HANDOFF_PRIVATE_DIR_EXISTS;exit 4; }
[ ! -e "$DEST" ] || { echo HANDOFF_UNIT_ALREADY_PRESENT;exit 5; }
for svc in else-itil-specialist-v1.service \
  else-itil-novice-v4-canary.service else-itil-novice-v5-canary.service; do
 [ "$(systemctl --user is-active "$svc")" = active ] || {
   echo PREDECESSOR_SERVICE_NOT_ACTIVE;exit 6; }
done
install -d -m 700 "$PRIVATE"
rollback() {
 systemctl --user stop "$UNIT" >/dev/null 2>&1 || true
 rm -f "$DEST"
 systemctl --user daemon-reload
 echo V6_ROLLBACK_V2_V4_V5_UNMODIFIED
}
trap rollback ERR
# QA identities only; NEVER issue employee credentials or print secrets.
"$PY" - <<'PY'
import json,secrets,hashlib,os
from pathlib import Path
p=Path("/home/u23u/else_itil_workbench_v6_20261119/canary_private")
identities=[]
for i in (1,2):
    token=secrets.token_urlsafe(48)
    name=f"qa_support_{i:02d}"
    path=p/f"{name}.token"
    with path.open("x") as stream:
        os.fchmod(stream.fileno(),0o600)
        stream.write(token)
    identities.append({
        "subject":name,"token_sha256":hashlib.sha256(token.encode()).hexdigest(),
        "roles":["guided_user"],"enabled":True,
    })
with (p/"principals.sha256.json").open("x") as stream:
    os.fchmod(stream.fileno(),0o600)
    json.dump({"schema":"else.itil.guided-principals.v1",
               "principals":identities},stream)
with (p/"handoff_key.hex").open("x") as stream:
    os.fchmod(stream.fileno(),0o600)
    stream.write(secrets.token_hex(32))
print("V6_QA_IDENTITIES_AND_ISOLATED_HANDOFF_SIGNING_KEY_CREATED")
PY
install -m 600 "$ROOT/ops/systemd/$UNIT" "$DEST"
systemctl --user daemon-reload
systemctl --user start "$UNIT"
sleep 3
"$PY" - <<'PY'
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from pathlib import Path
import json
base="http://127.0.0.1:18915"
private=Path("/home/u23u/else_itil_workbench_v6_20261119/canary_private")
alice=(private/"qa_support_01.token").read_text()
bob=(private/"qa_support_02.token").read_text()
service=Path("/home/u23u/else_itil_sup_run/support_live_private/service.token").read_text().strip()
def post(path,body,token=None):
    h={"Content-Type":"application/json"}
    if token:h["Authorization"]="Bearer "+token
    req=Request(base+path,data=json.dumps(body).encode(),headers=h)
    try:
        with urlopen(req,timeout=9) as x:return x.status,json.load(x)
    except HTTPError as e:return e.code,json.load(e)
with urlopen(base+"/health",timeout=4) as x:h=json.load(x)
assert h["state"]=="READY"
assert h["repairs_enabled"] is False
assert h["guided_principal_required"] is True
assert h["user_consent_handoff_enabled"] is True
assert "qa_dispatch" not in h
with urlopen(base+"/v1/support/ui",timeout=4) as x:
    assert x.status==200 and "script-src 'self'" in x.headers["Content-Security-Policy"]
case={
    "case_ref":"QA-V6-INSTALL-SYNTHETIC-00001",
    "input_scope":"synthetic",
    "service":"Aplicación de prueba",
    "description":"No tengo permisos para visualizar la pantalla de esta aplicación inventada.",
}
assert post("/v1/support/guided/start",case)[0]==401
assert post("/v1/support/guided/start",case,service)[0]==401
code,first=post("/v1/support/guided/start",case,alice)
assert code==200 and first["status"]=="NEEDS_HUMAN_TRIAGE"
assert first["quality"]["accepted"] is False
assert first["inference_skipped_for_safe_escalation"] is True
sid=first["session_id"]
assert post("/v1/support/guided/handoff",{
 "session_id":sid,"consent_to_share":False,
 "privacy_notice_acknowledged":True},alice)[0]==422
code,envelope=post("/v1/support/guided/handoff",{
 "session_id":sid,"consent_to_share":True,
 "privacy_notice_acknowledged":True},alice)
assert code==200 and envelope["packet"]["technical_review"]["qa_evidence_bound"] is False
assert post("/v1/support/technician/verify-handoff",{"envelope":envelope},alice)[0]==401
code,verified=post("/v1/support/technician/verify-handoff",
                   {"envelope":envelope},service)
assert code==200 and verified["signature_valid"] and verified["consent_record_valid"]
assert verified["root_cause_certified"] is False
assert post("/v1/support/guided/revoke",{
    "session_id":sid,"receipt_id":envelope["packet"]["receipt_id"]},bob)[0]==422
assert post("/v1/support/guided/revoke",{
    "session_id":sid,"receipt_id":envelope["packet"]["receipt_id"]},alice)[0]==200
assert post("/v1/support/technician/verify-handoff",
            {"envelope":envelope},service)[0]==422
with urlopen(Request(base+"/v1/support/readiness",
    headers={"Authorization":"Bearer "+service}),timeout=4) as x:r=json.load(x)
assert r["decision"]=="NO_GO"
assert r["user_consent_handoff_enabled"] is True
assert r["root_cause_accuracy_certified"] is False
print("V6_QA_CONSENT_SIGN_VERIFY_REVOKE_BROWSER_AND_READYNESS_PASS")
PY
for svc in else-itil-specialist-v1.service \
  else-itil-novice-v4-canary.service else-itil-novice-v5-canary.service "$UNIT"; do
 [ "$(systemctl --user is-active "$svc")" = active ]
done
test "$(ss -lnt | grep -c '127.0.0.1:18915')" -eq 1
echo V6_WORKBENCH_READY_NO_EXISTING_SERVICE_REPLACED
trap - ERR
