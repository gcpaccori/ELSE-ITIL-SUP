#!/usr/bin/env bash
# Additive, lease-locked canary; never modifies existing V2/V4 systemd units.
set -euo pipefail
umask 077
SHA="${1:?Supply exact reviewed merged main SHA}"
ROOT=/home/u23u/else_itil_maturity_v5_20261118/release_main
PRIVATE=/home/u23u/else_itil_maturity_v5_20261118/canary_private
UNIT=else-itil-novice-v5-canary.service
DEST=/home/u23u/.config/systemd/user/$UNIT
PY=/home/u23u/miniconda/envs/orquesta_py311/bin/python3.11
[ "$(git -C "$ROOT" rev-parse HEAD)" = "$SHA" ] || { echo SHA_LEASE_MISMATCH;exit 3; }
[ ! -e "$PRIVATE" ] || { echo PRIVATE_DIR_MUST_BE_FRESH;exit 4; }
[ ! -e "$DEST" ] || { echo V5_UNIT_ALREADY_EXISTS;exit 5; }
[ "$(systemctl --user is-active else-itil-specialist-v1.service)" = active ] || {
 echo V2_MUST_STAY_ACTIVE;exit 6;
}
[ "$(systemctl --user is-active else-itil-novice-v4-canary.service)" = active ] || {
 echo V4_MUST_STAY_ACTIVE;exit 7;
}
test -f "$ROOT/data/2026_sep545_all_features_maturity_scorecard.json"
test -f "$ROOT/data/2026_sep545_full_maturity_evidence.json"
install -d -m 700 "$PRIVATE"
rollback() {
  systemctl --user stop "$UNIT" >/dev/null 2>&1 || true
  rm -f "$DEST"
  systemctl --user daemon-reload
  echo "V5_CANARY_ROLLBACK_V2_V4_UNCHANGED"
}
trap rollback ERR

# Generate non-corporate QA principal tokens privately on the server only.
# Token bytes are NEVER written to GitHub, log files, stdout or the manifest.
"$PY" - <<'PY'
import os,secrets,json,hashlib
from pathlib import Path
private=Path("/home/u23u/else_itil_maturity_v5_20261118/canary_private")
principals=[]
for i in (1,2):
    subject=f"qa_pilot_{i:02d}"
    token=secrets.token_urlsafe(48)
    f=private/f"{subject}.private_token"
    with f.open("x") as out:
        os.fchmod(out.fileno(),0o600)
        out.write(token)
    principals.append({
      "subject":subject,"token_sha256":hashlib.sha256(token.encode()).hexdigest(),
      "enabled":True,"roles":["guided_user"],
    })
manifest=private/"guided_principals.sha256.private.json"
with manifest.open("x") as out:
    os.fchmod(out.fileno(),0o600)
    json.dump({"schema":"else.itil.guided-principals.v1",
               "principals":principals},out)
print("TWO_PRIVATE_NONCORPORATE_QA_PRINCIPAL_IDENTITIES_CREATED")
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
canary="http://127.0.0.1:18914"
private=Path("/home/u23u/else_itil_maturity_v5_20261118/canary_private")
service=Path("/home/u23u/else_itil_sup_run/support_live_private/service.token").read_text().strip()
alice=(private/"qa_pilot_01.private_token").read_text().strip()
bob=(private/"qa_pilot_02.private_token").read_text().strip()
def post(obj,path,token=None):
    h={'Content-Type':'application/json'}
    if token:h['Authorization']='Bearer '+token
    req=Request(canary+path,data=json.dumps(obj).encode(),headers=h)
    try:
        with urlopen(req,timeout=7) as resp:
            return resp.status,json.load(resp)
    except HTTPError as e:
        return e.code,json.load(e)
with urlopen(canary+"/health",timeout=5) as r:
    health=json.load(r)
assert health['state']=="READY"
assert health['repairs_enabled'] is False
assert health['guided_principal_required'] is True
assert health['guided_fast_safe_handoff'] is True
assert health['guided_dialogue_enabled'] is True
assert 'qa_dispatch' not in health
r=Request(canary+"/v1/support/readiness",
    headers={'Authorization':'Bearer '+service})
with urlopen(r,timeout=5) as s:
    audit=json.load(s)
assert audit["decision"]=="NO_GO"
assert audit["source_freshness_certified"] is False
assert audit["root_cause_accuracy_certified"] is False
assert audit["private_principal_scope_enabled"] is True
assert audit["guided_admission_limit"]==2
case={"case_ref":"QA-V5-DEPLOY-SYNTH-1","input_scope":"synthetic",
      "service":"Aplicación sintética",
      "description":"No tengo permisos para entrar al módulo de prueba y no sé qué observar."}
assert post(case,"/v1/support/guided/start")[0]==401
assert post(case,"/v1/support/guided/start",service)[0]==401
status,a=post(case,"/v1/support/guided/start",alice)
assert status==200 and a["status"]=="NEEDS_HUMAN_TRIAGE"
assert a["inference_skipped_for_safe_escalation"] is True
assert a["quality"]["accepted"] is False
assert a["presentacion_para_usuario"]["mostrar_escalamiento"] is True
assert post({"session_id":a["session_id"],"expected_turn":2,
             "reply":"Sigo teniendo el mismo problema y no tengo permisos."},
            "/v1/support/guided/continue",bob)[0]==422
status,again=post(case,"/v1/support/guided/start",bob)
assert status==200 and again["session_id"]!=a["session_id"]
r=Request(canary+"/v1/support/readiness",
    headers={'Authorization':'Bearer '+service})
with urlopen(r,timeout=5) as s:
    readiness=json.load(s)
assert readiness["guided_runtime"]["requests"]==2
assert readiness["guided_runtime"]["immediate_safe_handoffs"]==2
assert readiness["guided_runtime"]["model_accepted"]==0
print("V5_PRIVATE_IDENTITY_SCOPE_FAST_NO_LLM_NO_GO_READINESS_PASS")
PY
for service in else-itil-specialist-v1.service else-itil-novice-v4-canary.service "$UNIT"; do
 [ "$(systemctl --user is-active "$service")" = active ]
done
test "$(ss -lnt | grep -c '127.0.0.1:18914')" -eq 1
echo V5_PRIVATE_CANARY_DEPLOYED_WITH_V2_V4_INTACT
trap - ERR
