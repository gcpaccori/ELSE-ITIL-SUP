"""Three-turn REAL Qwen guided V5 synthetic test, without business data.

Private token read only on cluster; no customer names, case IDs, raw replies,
tokens or sessions included in public aggregates.
"""
from __future__ import annotations
import json,os,time,secrets
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path("/home/u23u/else_itil_maturity_v5_20261118/repo")
PRIV=Path("/home/u23u/else_itil_maturity_v5_20261118/canary_private")
TOKEN=(PRIV/"qa_pilot_01.private_token").read_text().strip()
SERVICE=Path("/home/u23u/else_itil_sup_run/support_live_private/service.token").read_text().strip()
OUT=ROOT/"data"/"2026_v5_live_model_guidance_synthetic.json"
BASE="http://127.0.0.1:18914"


def post(path,body):
    req=Request(BASE+path,data=json.dumps(body,ensure_ascii=False).encode(),
        headers={"Authorization":"Bearer "+TOKEN,
                 "Content-Type":"application/json"})
    start=time.monotonic()
    with urlopen(req,timeout=190) as response:
        data=json.load(response)
        code=response.status
    return code,data,round(time.monotonic()-start,2)


def main():
    assert not OUT.exists()
    case={
      "case_ref":"QA-V5-REAL-QWEN-"+secrets.token_hex(12),
      "input_scope":"synthetic",
      "service":"Aplicación de oficina ficticia",
      "description":(
        "En una aplicación de ejemplo la pantalla aparece en blanco "
        "al intentar abrir una sección. No sé de informática y necesito "
        "una primera comprobación que pueda hacer solo mirando la pantalla."
      ),
    }
    statuses=[];selected=[];accepted=[];times=[];stages=[]
    for turn in (1,2,3):
        if turn==1:
            code,r,elapsed=post("/v1/support/guided/start",case)
            session=r["session_id"]
        else:
            prompt=("No entiendo cómo hacer esa comprobación. "
                    "Explícamelo sin tecnicismos y desde la pantalla."
                    if turn==2 else
                    "Sigue fallando; no tengo permisos para modificar nada. "
                    "¿Qué datos seguros llevo a soporte?")
            code,r,elapsed=post("/v1/support/guided/continue",{
               "session_id":session,"expected_turn":turn,"reply":prompt})
        assert code==200 and r["turn"]==turn
        assert r["diagnosis_certified"] is False and r["executed_changes"] is False
        assert r["presentacion_para_usuario"]["accion_ejecutada"] is False
        statuses.append(r["status"])
        selected.append(r["model_selected"])
        accepted.append(r["quality"]["accepted"])
        times.append(elapsed)
        stages.append(r["presentacion_para_usuario"]["etapa"])
        print(f"V5_REAL_QWEN_TURN_{turn}_FINISHED elapsed_s={elapsed} "
              f"model_accepted={r['quality']['accepted']}",flush=True)
        if turn==3:
            assert r["status"]=="NEEDS_HUMAN_TRIAGE"
            assert r["inference_skipped_for_safe_escalation"] is True
            assert r["model_selected"] is None
            assert r["presentacion_para_usuario"]["mostrar_escalamiento"]
            assert elapsed<5,"FAST_HANDOFF_WALL_LATENCY_EXCEEDED_5S"
    req=Request(BASE+"/v1/support/readiness",
        headers={"Authorization":"Bearer "+SERVICE})
    with urlopen(req,timeout=5) as response:
        status=json.load(response)
    assert status["decision"]=="NO_GO"
    assert status["human_review"]["status"]=="PENDING_HUMAN_REVIEW"
    assert status["private_principal_scope_enabled"]
    output={
       "schema":"else.itil.qa.v5-live-synthetic-real-qwen.v1",
       "date":"2026-11-18","synthetic_corporate_incidents":0,
       "actual_qwen_requests":2,
       "fast_rule_turns_without_model":1,
       "turns":3,
       "model_selected_per_turn":selected,
       "model_contract_accepted_per_turn":accepted,
       "status_per_turn":statuses,
       "presentation_stage_per_turn":stages,
       "measured_wall_seconds_per_turn":times,
       "main_safety_fast_handoff_latency_under_5s":times[2]<5,
       "business_reads_or_writes":0,
       "causal_diagnoses_certified":0,
       "human_reviews_certified":0,
       "root_cause_truth_not_measured":True,
       "not_a_slo_benchmark":True,
       "no_raw_text_or_identifying_customer_data_published":True,
       "runtime_readiness":"NO_GO",
       "legacy_v2_v4_not_modified":True,
    }
    OUT.write_text(json.dumps(output,ensure_ascii=False,
                              sort_keys=True,indent=2)+"\n")
    print("V5_REAL_QWEN_SYNTHETIC_AUTH_GUIDANCE_FAST_HANDOFF_PASS",flush=True)


if __name__=="__main__":
    main()
