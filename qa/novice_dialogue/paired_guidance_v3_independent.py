"""Independent immutable-pair assessment of guided V2 vs November 17 baseline.

Only private local source-based generated transcripts. Deterministic source
identity, action safety, persistence, fallback and evidence criteria. It does
NOT score verified diagnostic accuracy, real user comprehension or repairs.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,re

from else_dominance.guided_dialogue import validate_guidance
from qa.novice_dialogue.verify_novice_dialogue import (
    NOVICE_ACTION, ESCALATION, RECORD_EVIDENCE, unsafe_phrase, normalized
)
from qa.novice_dialogue.full_month_plan_guidance_audit import (
    USER,VISIBLE, ACTION,ADMIN
)

ROOT=Path("/home/u23u/else_itil_guided_v2_20261118")
V3=ROOT/"private"/"guided_v3_24cases_72turns.private.jsonl"
BASELINE=Path("/home/u23u/else_itil_guidance_sim_20261117/private/novice_turns.private.jsonl")
RESULT=ROOT/"repo"/"data"/"2026_aug_sep_guided_v3_independent_paired.json"
BASELINE_SHA="f74cfe287d61d99919aa7a065831ac7733d0fbcb884a742c46d030212b11225e"

def old_step(c,turn):
    p=c["turns"][turn]["response"].get("proposal") or {}
    steps=p.get("pasos") or []
    return [x for x in steps if isinstance(x,dict)]

def old_user_step(c,turn):
    for x in old_step(c,turn):
        action=str(x.get("accion",""))
        role=str(x.get("responsable",""))
        check=str(x.get("verificacion",""))
        if USER.search(role) and VISIBLE.search(action) and ACTION.search(action) and not ADMIN.search(action) and len(check.strip())>=12:
            return action
    return ""

def old_evidence_and_escalation(c):
    p=c["turns"][2]["response"].get("proposal") or {}
    text=" ".join([str(p.get("diagnostico","")),
       *(str(v) for v in (p.get("faltantes") or [])),
       *(str(x.get("accion",""))+" "+str(x.get("responsable",""))
          for x in old_step(c,2))])
    return bool(ESCALATION.search(text) and RECORD_EVIDENCE.search(text))

def reconstructed_guide(t):
    """Re-validate against CURRENT hardened source, not only historical gate."""
    return {
      "estado":"INVESTIGACION_PENDIENTE",
      "que_entendi":t["summary"],
      "hipotesis":t["hypotheses"],
      "para_ti":{
        "explicacion":t["user_explanation"],
        "paso":t["user_step"],
        "observa":t["user_observation"],
        "si_a":t["user_branch_a"],
        "si_b":t["user_branch_b"],
        "pregunta":t["user_question"],
      },
      "para_soporte":{
        "cuando_escalar":t["support_escalation"],
        "evidencia":t["support_evidence"],
        "verificacion_autorizada":t["support_verification"],
      },
      "causa_confirmada":False,
      "ejecutado":False
    }

def v3_step(c,turn):
    t=c["turns"][turn]
    old_step=c["turns"][turn-1]["user_step"] if turn else ""
    flags=validate_guidance(reconstructed_guide(t),old_step)
    return t["user_step"] if t["gate_accepted"] and not flags else ""

def v3_evidence_and_escalation(c):
    t=c["turns"][2]
    if not t["gate_accepted"] or t["validation_flags"]:return False
    txt=t["support_escalation"]+" "+t["support_evidence"]
    return bool(ESCALATION.search(txt) and RECORD_EVIDENCE.search(txt))

def meaningful_delta(a:str,b:str)->bool:
    if not a or not b:return False
    sa=normalized(a); sb=normalized(b)
    return len(sa&sb)/max(1,len(sa|sb))<0.82


def evaluate():
    assert BASELINE.exists() and V3.exists() and not RESULT.exists()
    assert sha256(BASELINE.read_bytes()).hexdigest()==BASELINE_SHA
    old=[json.loads(line) for line in BASELINE.read_text().splitlines() if line]
    new=[json.loads(line) for line in V3.read_text().splitlines() if line]
    assert len(old)==len(new)==24
    keys=lambda rows:{(r["month"],r["case_sha256"]) for r in rows}
    assert keys(old)==keys(new),"PAIRED_CASE_SET_DRIFT"
    old_by_key={(r["month"],r["case_sha256"]):r for r in old}
    monthly={}
    for month in ("2026-08","2026-09"):
        cases=[r for r in new if r["month"]==month]
        assert len(cases)==12
        c=Counter()
        for current in cases:
            baseline=old_by_key[(month,current["case_sha256"])]
            turns=current["turns"]
            assert len(turns)==len(baseline["turns"])==3
            assert [t["turn"] for t in turns]==[1,2,3]
            for i,t in enumerate(turns):
                # Re-audit against current source code (not just the result
                # already accepted at initial generation time).
                assert t["no_claimed_execution"] and t["no_certified_diagnosis"]
                assert t["user_step_present"] and t["user_observation"]
                if unsafe_phrase(t["user_step"]):
                    c["v3_unsafe_request"]+=1
                if t["gate_accepted"]:
                    c[f"v3_turn{i+1}_accepted"]+=1
                else:
                    c[f"v3_turn{i+1}_human_triage"]+=1
                    assert t["status"]=="NEEDS_HUMAN_TRIAGE"
                c[f"v3_turn{i+1}_model_primary"]+=int(t["model_selected"]=="primary")
                c[f"v3_turn{i+1}_model_fallback"]+=int(t["model_selected"]=="fallback")
                assert t["validation_flags"]==[],"ORIGINAL_RESULT_SCHEMA_DRIFT"
                if validate_guidance(reconstructed_guide(t),
                                     turns[i-1]["user_step"] if i else ""):
                    c[f"v3_turn{i+1}_hardened_revalidation_failed"]+=1
                c[f"baseline_turn{i+1}_accepted"]+=int(baseline["turns"][i]["score"]["accepted"])
                c[f"baseline_turn{i+1}_safe_user_action"]+=int(bool(old_user_step(baseline,i)))
                c[f"v3_turn{i+1}_safe_user_action"]+=int(bool(v3_step(current,i)))
            old_first=old_user_step(baseline,0)
            new_first=v3_step(current,0)
            c["baseline_case_good_first_turn"]+=bool(old_first)
            c["v3_case_good_first_turn"]+=bool(new_first)
            c["baseline_turn3_evidence_escalation"]+=int(old_evidence_and_escalation(baseline))
            c["v3_turn3_evidence_escalation"]+=int(v3_evidence_and_escalation(current))
            old_all=all(t["score"]["accepted"] and t["score"]["safety_protocol_pass"]
                        for t in baseline["turns"])
            new_all=all(bool(v3_step(current,i)) for i in (0,1,2))
            c["baseline_all_three_gates_accepted"]+=int(old_all)
            c["v3_all_three_gates_accepted"]+=int(new_all)
            c["v3_second_step_changed"]+=int(
                meaningful_delta(v3_step(current,0),v3_step(current,1)))
            c["v3_third_step_changed"]+=int(
                meaningful_delta(v3_step(current,1),v3_step(current,2)))
            c["v3_case_staged_guide_candidate"]+=int(
                new_all and all(v3_step(current,i) for i in (0,1,2))
                and meaningful_delta(v3_step(current,0),v3_step(current,1))
                and meaningful_delta(v3_step(current,1),v3_step(current,2))
                and v3_evidence_and_escalation(current))
        monthly[month]={"cases":12,"turns":36,"metrics":dict(sorted(c.items()))}
    result={
        "schema":"else.itil.qa.guided-v3-paired-independent.v1",
        "exact_same_case_set":True,
        "months":["2026-08","2026-09"],
        "source_august_cases":1819,
        "source_september_cases":545,
        "paired_sample_size":24,
        "total_turns_old":72,
        "total_turns_new":72,
        "old_assistant":"Qwen3.5-9B service one-shot with manually reconstructed conversation",
        "new_assistant":"Qwen3.5-9B guided_v2 native private SQLite session memory with bounded retry",
        "principals_replies_synthetic":True,
        "real_human_comprehension_tested":False,
        "true_causal_diagnostic_accuracy_tested":False,
        "one_shot_documental_2364_audit_unchanged":True,
        "method":"identical cases; strict conservative action/evidence heuristics and gate acceptance",
        "source_month_rates_not_inferred_from_sample":True,
        "no_repair_executed":True,
        "baseline_sha256":BASELINE_SHA,
        "new_private_sha256":sha256(V3.read_bytes()).hexdigest(),
        "per_month":monthly,
    }
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"PAIRED_GUIDED_V3_INDEPENDENT_AUDIT_PASS",
                      "per_month":monthly},ensure_ascii=False,sort_keys=True))
    return result


if __name__=="__main__":evaluate()
