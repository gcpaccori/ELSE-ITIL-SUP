"""October zero-case source-check and ALL September 545 deterministic maturity audit.

Inputs are private, independently source-bound September 2026 receipts and
previously frozen real-Qwen one-shot plans. No new models are called here;
a stub exercises each guided session/turn mechanically, NOT diagnosis.

Any individual incident text, hash, private receipt or token remains private.
Only aggregate counts, source hashes and honest maturity limits are published.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,os

from else_dominance.guided_dialogue import GuidedStore, _safe_fallback,validate_guidance
from qa.novice_dialogue.full_month_plan_guidance_audit import assess

BASE=Path("/home/u23u/else_itil_sep545_maturity_20261118")
SOURCE=Path("/home/u23u/else_itil_guidance_sim_20261117/private/september_blind.private.jsonl")
PLANS=Path("/home/u23u/else_itil_guidance_sim_20261117/private/september_plans_redacted.private.jsonl")
PUBLIC=BASE/"repo"/"data"/"2026_sep545_full_maturity_evidence.json"
PRIVATE=BASE/"private"/"sep545_guided_stub_only.sqlite"
SOURCE_HASH="b3030b78700470f4beda18c399e939ef2c8c24537aac8563d131557d9a9c91cb"
PLANS_HASH="a7a69ec49f0d3e6cc24daf4c5200b8bd7716ea23570b79833809e297e5ca366d"
WINDOWS_IDENTITY_ROOT="aabbd6c4e1eebedcb116b3c490e9fe253dcfc35550cfbf49f7fb27b09b6a9a9c"
WINDOWS_FULL_SOURCE_RECEIPT="d2e14b089e51789181043355e4b83143f060de939276ba8f9bc504b7b464a67e"
WINDOWS_OCT_ZERO_SOURCE_RECEIPT="fc5791ef59d4d43a45b0fa960f4fd0854b7699711ed8b60a16062c0e51893e52"


def read_private(path:Path,expected_sha:str)->list[dict]:
    actual=sha256(path.read_bytes()).hexdigest()
    if actual!=expected_sha:
        raise ValueError("PRIVATE_RECEIPT_SHA_MISMATCH")
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line]


STEPS=[
    "Mira la pantalla donde aparece el problema y anota el mensaje visible sin datos personales.",
    "Revisa en qué sección aparece el aviso y anota solamente su nombre.",
    "Observa si el aviso aparece al abrir la aplicación o al entrar en una sección.",
]
class Stub:
    """Never makes an LLM call. Structured only for mechanical session testing."""
    def __init__(self):
        self.calls=0
    def complete(self,messages):
        self.calls+=1
        query=json.loads(messages[1]["content"])
        turn=query["turno"]
        assert 1<=turn<=3
        proposal=_safe_fallback()
        proposal["para_ti"]["paso"]=STEPS[turn-1]
        assert not validate_guidance(proposal,STEPS[turn-2] if turn>1 else "")
        return json.dumps(proposal,ensure_ascii=False)


def audit():
    assert SOURCE.exists() and PLANS.exists() and not PUBLIC.exists() and not PRIVATE.exists()
    source=read_private(SOURCE,SOURCE_HASH)
    plans=read_private(PLANS,PLANS_HASH)
    assert len(source)==len(plans)==545
    src_id=[r["case_sha256"] for r in source]
    plan_id=[r["case_sha256"] for r in plans]
    assert len(set(src_id))==len(set(plan_id))==545
    assert set(src_id)==set(plan_id),"MODEL_SOURCE_CASE_SET_MISMATCH"
    root=sha256("\n".join(sorted(src_id)).encode()).hexdigest()
    assert root==WINDOWS_IDENTITY_ROOT,"LIVE_WINDOWS_COHORT_IDENTITY_MISMATCH"
    assert all(r["month"]=="2026-09" and r["historical_resolution"]=="WITHHELD"
               for r in source),"HISTORY_LEAKED_TO_BLIND_INPUT"
    assert all(r["month"]=="2026-09" and r["historical_solution_used"] is False
               for r in plans),"HISTORY_LEAKED_TO_OLD_MODEL"
    dates=[r["opened_at"] for r in source]
    assert min(dates).startswith("2026-09") and max(dates).startswith("2026-09")
    per_service=Counter(r["service_code"] for r in source)
    per_module=Counter(r["module_code"] for r in source)
    per_day=Counter(r["opened_at"][:10] for r in source)
    source_lengths=Counter(
        "short" if len(r["incident_text_redacted"].strip())<80
        else "medium" if len(r["incident_text_redacted"].strip())<300
        else "long" for r in source)
    assert all(len(r["incident_text_redacted"].strip())>=15 for r in source)

    scores=Counter()
    old_plans={p["case_sha256"]:p for p in plans}
    for r in source:
        p=old_plans[r["case_sha256"]]
        assert p["case_sha256"]==r["case_sha256"]
        scores["completed"]+=int(p["model_completed"] is True)
        scores["quality_gate_accepted"]+=int(p["quality_gate_accepted"] is True)
        a=assess(p["technical_plan"],p["structural_quality_accepted"])
        for k,val in a.items():scores[k]+=int(val)
        strict=(
           a["structural_accepted"] and a["nonempty_diagnosis"]
           and a["has_2_or_more_hypotheses"]
           and a["has_condition_and_result_steps"]
           and a["has_user_screen_check"]
           and a["has_result_branching"]
           and a["limited_technical_jargon_proxy"]
           and a["claim_no_changes"]
           and not a["sensitive_directive_flag"]
        )
        scores["strict_beginner_one_shot_proxy"]+=int(strict)
    assert scores["completed"]==543
    assert scores["structural_accepted"]==508
    assert scores["quality_gate_accepted"]==508
    assert scores["strict_beginner_one_shot_proxy"]==5

    PRIVATE.parent.mkdir(parents=True,mode=0o700,exist_ok=True)
    os.chmod(PRIVATE.parent,0o700)
    store=GuidedStore(PRIVATE)
    stub=Stub()
    mechanics=Counter()
    try:
        for r in source:
            case_ref="QA-SEP26-MECH-"+r["case_sha256"][:27]
            ticket={
              "case_ref":case_ref,"input_scope":"synthetic",
              "service":r["service_code"],
              "description":r["incident_text_redacted"],
            }
            first=store.start(ticket,stub)
            mechanics["accepted_first"]+=int(first["quality"]["accepted"])
            assert first["turn"]==1 and first["next_turn"]==2
            assert not first["executed_changes"] and not first["diagnosis_certified"]
            same=store.start(ticket,stub)
            assert same["replayed"] and same["session_id"]==first["session_id"]
            mechanics["exact_start_replay"]+=1
            second=store.continue_turn(first["session_id"],2,
                   "No entiendo la comprobación, necesito palabras sencillas.",stub)
            third=store.continue_turn(first["session_id"],3,
                   "Sigue fallando y no tengo permisos para modificar el sistema.",stub)
            assert second["turn"]==2 and third["turn"]==3
            assert second["presentacion_para_usuario"]["etapa"]=="ACLARAR_EN_LENGUAJE_SENCILLO"
            assert third["presentacion_para_usuario"]["mostrar_escalamiento"]
            assert all(x["quality"]["accepted"] for x in (first,second,third))
            assert not second["executed_changes"] and not third["executed_changes"]
            assert not third["diagnosis_certified"]
            repeated=store.continue_turn(first["session_id"],3,
                   "Sigue fallando y no tengo permisos para modificar el sistema.",stub)
            assert repeated["replayed"] and repeated["presentacion_para_usuario"]==third["presentacion_para_usuario"]
            mechanics["exact_turn_replay"]+=1
            mechanics["three_turns_stored"]+=1
            mechanics["escalation_visible_on_third"]+=1
            mechanics["separate_user_and_support"]+=1
        assert stub.calls==545*3
        assert store.db.execute("SELECT count(*) FROM guided_sessions").fetchone()[0]==545
        assert store.db.execute("SELECT count(*) FROM guided_turns").fetchone()[0]==1635
        mechanics["stub_generated_turns"]=stub.calls
    finally:
        store.close()
    assert PRIVATE.stat().st_mode & 0o077==0,"MECHANICAL_DB_PERMISSION_UNSAFE"

    result={
       "schema":"else.itil.qa.2026-september-full545-maturity.v1",
       "audit_date":"2026-11-18",
       "requested_last_closed_month":"2026-10",
       "authoritative_corporate_source":"ELSE70/dbITIL_D/dbo.taIncidente via ELSE62 provider",
       "fresh_read_only_windows_receipt":"2026-11-18",
       "october_cases_corporate":0,
       "october_case_rows_evaluated":0,
       "november_1_through_18_cases_corporate":0,
       "most_recent_populated_month":"2026-09",
       "september_total":545,
       "september_all_cases_independently_bound_to_windows":True,
       "september_unique_source_cases":545,
       "september_archived_model_plans":545,
       "september_first_date":min(dates)[:19],
       "september_last_date":max(dates)[:19],
       "september_days_with_cases":len(per_day),
       "september_unique_services":len(per_service),
       "september_unique_modules":len(per_module),
       "september_length_strata":dict(sorted(source_lengths.items())),
       "september_historical_nonempty_solution_records":455,
       "september_historical_answer_date_present":455,
       "september_historical_closed_date_present":382,
       "historical_solution_is_not_certified_ground_truth":True,
       "september_model_metrics":dict(sorted(scores.items())),
       "september_mechanical_stub_only":dict(sorted(mechanics.items())),
       "real_llm_calls_during_545_mechanical_check":0,
       "business_reads_from_guided_kernel":0,
       "business_writes":0,
       "certified_root_causes":0,
       "verified_end_user_comprehensions":0,
       "verified_repair_outcomes":0,
       "customer_text_or_hashes_published":False,
       "windows_september_source_receipt_sha256":WINDOWS_FULL_SOURCE_RECEIPT,
       "windows_october_zero_receipt_sha256":WINDOWS_OCT_ZERO_SOURCE_RECEIPT,
       "identity_case_set_sha256":root,
       "linux_redacted_source_sha256":SOURCE_HASH,
       "linux_archived_qwen_plan_sha256":PLANS_HASH,
       "limitations":[
          "October 2026 has zero records in the selected corporate ITIL QA source",
          "Historical 545 one-shot Qwen plans were not generated by current V4",
          "545 three-turn guided-session exercises used a deterministic STUB, not Qwen",
          "No 545 verified human-guidance evaluations and no case-level causal gold",
          "Correctness cannot be inferred from archival solution, closure or LLM format",
          "Only selected QA database was verified; other corporate helpdesk sources are untested",
       ],
    }
    PUBLIC.parent.mkdir(parents=True,exist_ok=True)
    PUBLIC.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    return {
        "status":"SEP_545_FULL_SOURCE_AND_ARCHIVED_PLAN_AUDIT_PASS",
        "total":545,
        "keyroot":root,
        "historical_model_completed":scores["completed"],
        "historical_structural_pass":scores["structural_accepted"],
        "historical_strict_beginner_proxy":scores["strict_beginner_one_shot_proxy"],
        "mechanical_guided_stub_sessions":mechanics["three_turns_stored"],
        "mechanical_stub_turns":mechanics["stub_generated_turns"],
        "real_qwen_calls_for_full545":0,
        "october_2026_source_cases":0,
    }


if __name__=="__main__":
    print(json.dumps(audit(),ensure_ascii=False,sort_keys=True))
