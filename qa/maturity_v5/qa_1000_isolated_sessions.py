"""1,000 synthetic non-model sessions with 10 isolated principals.

Stress-tests SQLite ownership, replay and fast safety paths. It deliberately
calls NO LLM, NO company SQL and NO real incident sources.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
import json,os,time

from else_dominance.guided_dialogue import GuidedStore

ROOT=Path("/home/u23u/else_itil_maturity_v5_20261118")
PRIVATE=ROOT/"private"/"qa_1000_principal_sessions.private.sqlite"
OUT=ROOT/"repo"/"data"/"2026_v5_1000_isolated_synthetic_sessions.json"


class ForbiddenModel:
    def complete(self,messages):
        raise AssertionError("LLM_MUST_NOT_BE_CALLED_FOR_MISSING_PERMISSIONS")


def run():
    assert not PRIVATE.exists() and not OUT.exists()
    PRIVATE.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
    os.chmod(PRIVATE.parent,0o700)
    db=GuidedStore(PRIVATE,require_principal=True,fast_handoff=True)
    model=ForbiddenModel()
    session_ids=set()
    stats=Counter()
    start=time.monotonic()
    try:
        for a in range(10):
            subject=f"synthetic_employee_{a:02d}"
            for b in range(100):
                # Same visible references across ten principals deliberately.
                ticket={
                  "case_ref":f"QA-V5-SHARED-REF-{b:04d}",
                  "input_scope":"synthetic",
                  "service":"Aplicación inventada de pruebas",
                  "description":"No tengo permisos para entrar en esta aplicación de ejemplo y quiero orientación segura.",
                }
                one=db.start(ticket,model,subject_id=subject)
                assert one["session_id"] not in session_ids
                session_ids.add(one["session_id"])
                assert one["status"]=="NEEDS_HUMAN_TRIAGE"
                assert not one["quality"]["accepted"]
                assert one["inference_skipped_for_safe_escalation"] is True
                replay=db.start(ticket,model,subject_id=subject)
                assert replay["replayed"] and replay["session_id"]==one["session_id"]
                two=db.continue_turn(one["session_id"],2,
                    "No tengo permisos para continuar; necesito soporte.",model,
                    subject_id=subject)
                three=db.continue_turn(one["session_id"],3,
                    "Sigue fallando y no tengo permisos para hacer cambios.",model,
                    subject_id=subject)
                assert two["turn"]==2 and three["turn"]==3
                assert all(not x["diagnosis_certified"] and
                           not x["executed_changes"] and
                           not x["quality"]["accepted"] for x in (one,two,three))
                assert three["presentacion_para_usuario"]["mostrar_escalamiento"]
                assert two["inference_skipped_for_safe_escalation"]
                assert three["inference_skipped_for_safe_escalation"]
                stats["sessions"]+=1;stats["fast_no_model_turns"]+=3
                stats["exact_start_replays"]+=1
        assert db.db.execute(
             "SELECT COUNT(*) FROM guided_sessions").fetchone()[0]==1000
        assert db.db.execute(
             "SELECT COUNT(*) FROM guided_turns").fetchone()[0]==3000
        assert db.db.execute(
             "SELECT COUNT(DISTINCT subject_id) FROM guided_sessions"
        ).fetchone()[0]==10
        stats["subjects"]=10
    finally:db.close()
    assert PRIVATE.stat().st_mode & 0o077==0
    result={
       "schema":"else.itil.qa.v5-1000-principal-isolation.v1",
       "source":"SYNTHETIC_ONLY",
       "no_real_corporate_incidents":True,
       "no_llm_requests":True,
       "no_business_reads_or_writes":True,
       "results":dict(stats),
       "same_visible_refs_across_principals":True,
       "sqlite_private_0600":True,
       "no_model_quality_or_causal_accuracy_measured":True,
       "root_causes_certified":0,
       "real_human_participants":0,
       "elapsed_seconds_mechanical_only":round(time.monotonic()-start,3),
    }
    OUT.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":"V5_1000_CASES_3000_TURNS_PRINCIPAL_ISOLATION_PASS",
                      "elapsed_seconds":result["elapsed_seconds_mechanical_only"],
                      "results":result["results"]},sort_keys=True))


if __name__=="__main__":run()
