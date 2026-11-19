"""Re-run fully synthetic V6 with real Qwen and consented human handoff.

Requires private authenticated 18915 canary and two locally provisioned token
files. NEVER publishes token, session ID or incident text. No business queries.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json,secrets,time

ROOT=Path("/home/u23u/else_itil_workbench_v6_20261119")
PRIVATE=ROOT/"canary_private"
OUT=ROOT/"private"/"next_v6_live_smoke.private.json"
BASE="http://127.0.0.1:18915"


def post(path,body,token):
    req=Request(BASE+path,
        data=json.dumps(body,ensure_ascii=False).encode("utf8"),
        headers={"Content-Type":"application/json",
                 "Authorization":"Bearer "+token})
    begun=time.monotonic()
    try:
        with urlopen(req,timeout=190) as r:
            return r.status,json.load(r),round(time.monotonic()-begun,3)
    except HTTPError as e:
        return e.code,json.load(e),round(time.monotonic()-begun,3)


def run():
    assert not OUT.exists(),"REFUSE_TO_OVERWRITE_EVIDENCE"
    user=(PRIVATE/"qa_support_01.token").read_text().strip()
    operator=Path(
      "/home/u23u/else_itil_sup_run/support_live_private/service.token"
      ).read_text().strip()
    ticket={
       "case_ref":"QA-V6-RUN-"+secrets.token_hex(10),
       "input_scope":"synthetic",
       "service":"Portal de oficina ficticio",
       "description":"Un portal de ejemplo muestra la pantalla vacía al abrir un menú y no sé qué revisar.",
    }
    user_replies=[
       "No entiendo cómo realizar ese paso desde mi pantalla.",
       "Sigue fallando y no tengo permisos para hacer cambios en el sistema.",
    ]
    stages=[];accepted=[];models=[];timings=[]
    for turn in (1,2,3):
        if turn==1:
            status,r,sec=post("/v1/support/guided/start",ticket,user)
            session=r["session_id"]
        else:
            status,r,sec=post("/v1/support/guided/continue",{
                "session_id":session,"expected_turn":turn,
                "reply":user_replies[turn-2]},user)
        assert status==200 and r["turn"]==turn
        assert r["diagnosis_certified"] is False
        assert r["executed_changes"] is False
        stages.append(r["status"])
        accepted.append(r["quality"]["accepted"])
        models.append(r["model_selected"])
        timings.append(sec)
        print("TURN",turn,"ACCEPTED",accepted[-1],"SECONDS",sec,flush=True)
    assert stages[-1]=="NEEDS_HUMAN_TRIAGE"
    assert models[-1] is None and accepted[-1] is False
    assert timings[-1]<5

    status,signed,_=post("/v1/support/guided/handoff",{
        "session_id":session,"consent_to_share":True,
        "privacy_notice_acknowledged":True},user)
    assert status==200
    status,verified,_=post("/v1/support/technician/verify-handoff",
                           {"envelope":signed},operator)
    assert status==200 and verified["signature_valid"]
    assert verified["consent_record_valid"]
    assert not verified["business_evidence_verified"]
    assert not verified["root_cause_certified"]
    assert verified["technical_investigation_preflight"][
        "qa_hand_execution_started"] is False
    status,rev,_=post("/v1/support/guided/revoke-all",
                      {"session_id":session},user)
    assert status==200 and rev["revoked_count"]>=1
    status,err,_=post("/v1/support/technician/verify-handoff",
                      {"envelope":signed},operator)
    assert status==422 and err["error"]=="HANDOFF_RECEIPT_NOT_ACTIVE_OR_BOUND"
    result={
      "schema":"else.itil.qa.v6-live-qwen-human-handoff.v1",
      "sample_type":"ONE_FULLY_SYNTHETIC_CASE",
      "date":datetime.now(timezone.utc).date().isoformat(),
      "turns":3,"model_selected_per_turn":models,
      "model_contract_accepted_per_turn":accepted,
      "statuses":stages,"wall_seconds_per_turn":timings,
      "final_handoff_skips_qwen":True,
      "signed_consent_validated":True,
      "online_revocation_validated":True,
      "registered_core_qa_goals_available":3,
      "corporate_ticket_link_established":False,
      "qa_hand_started":False,
      "corporate_business_data_read":False,
      "repair_executed":False,
      "diagnostic_accuracy_certified":False,
      "human_observations_tested":0,
      "no_private_text_in_report":True,
    }
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    OUT.chmod(0o600)
    print("V6_REAL_QWEN_CONSENT_HANDOFF_FINAL_SUCCESS")


if __name__=="__main__":run()
