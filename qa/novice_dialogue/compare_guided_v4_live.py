"""Source-bound paired V3 vs V4 real Qwen responses, deterministic review.

Every case must have the same anonymous case hash and month. Never compare
aggregates from different samples. A model quality gate is NOT causal accuracy.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json,re

from else_dominance.guided_dialogue import (
    _presentation,validate_guidance
)
from qa.novice_dialogue.replay_guided_v4_presentation import _reconstruct, QUESTION2,QUESTION3

ROOT=Path("/home/u23u/else_itil_guided_v4_20261118")
PREVIOUS=Path("/home/u23u/else_itil_guided_v2_20261118/private/guided_v3_24cases_72turns.private.jsonl")
NEW=ROOT/"private"/"guided_v4_24cases_72turns.private.jsonl"
RESULT=ROOT/"repo"/"data"/"2026_aug_sep_guided_v4_live_paired_comparison.json"


def score_case(case):
    out=Counter()
    assert len(case["turns"])==3
    for index,t in enumerate(case["turns"]):
        expected=index+1
        assert t["turn"]==expected
        assert t["no_claimed_execution"] and t["no_certified_diagnosis"]
        out[f"turn{expected}_model_accepted"]+=int(t["gate_accepted"])
        out[f"turn{expected}_human_triage"]+=int(t["status"]=="NEEDS_HUMAN_TRIAGE")
        out[f"turn{expected}_primary"]+=int(t["model_selected"]=="primary")
        out[f"turn{expected}_primary_retry"]+=int(t["model_selected"]=="primary_retry")
        out[f"turn{expected}_fallback"]+=int(t["model_selected"]=="fallback")
    out["all_three_accepted"]+=int(all(t["gate_accepted"] for t in case["turns"]))
    return out


def eval_one(month:str,cases_old:list,cases_new:list):
    prior={(r["month"],r["case_sha256"]):r for r in cases_old}
    current={(r["month"],r["case_sha256"]):r for r in cases_new}
    assert set(prior)==set(current) and len(prior)==12
    counts=Counter()
    for key in prior:
        old=prior[key]; new=current[key]
        oldscore=score_case(old);newscore=score_case(new)
        for k,v in oldscore.items():counts["prior_"+k]+=v
        for k,v in newscore.items():counts["new_"+k]+=v
        oldfirst=old["turns"][0]
        newfirst=new["turns"][0]
        counts["prior_first_safe_model_step"]+=int(oldfirst["gate_accepted"])
        counts["new_first_safe_model_step"]+=int(newfirst["gate_accepted"])
        for t in new["turns"]:
            assert t["user_text_illustration_present"] and t["handoff_deterministic"]
            assert t["presentation_no_execution"] and t["presentation_no_causal_certification"]
        assert new["turns"][2]["handoff_visible"]
        counts["turn3_user_handoff_visible"]+=1
        counts["turn2_stage_clarification_or_escalation"]+=int(
           new["turns"][1]["presentation_stage"] in
           ("ACLARAR_EN_LENGUAJE_SENCILLO","ESCALAR_CON_APOYO_HUMANO",
            "ESCALAR_SIN_PRIVILEGIOS"))
        counts["turn3_stage_escalates"]+=int(
           new["turns"][2]["presentation_stage"] in
           ("RECOPILAR_EVIDENCIA_Y_ESCALAR","ESCALAR_CON_APOYO_HUMANO",
            "ESCALAR_SIN_PRIVILEGIOS"))
        for i,t in enumerate(new["turns"]):
            proposal=_reconstruct(t)
            previous_step=new["turns"][i-1]["user_step"] if i else ""
            flags=validate_guidance(proposal,previous_step)
            counts["v4_hardened_rejection_flags"]+=len(flags)
            counts["v4_current_gate_pass"]+=int(t["gate_accepted"] and not flags)
            if t["gate_accepted"] and flags:
                counts["v4_model_accepted_but_current_gate_rejected"]+=1
            if t["status"]=="NEEDS_HUMAN_TRIAGE":
                assert t["model_selected"] is None
    return {"cases":12,"turns_per_version":36,
            "counts":dict(sorted(counts.items()))}


def main():
    assert PREVIOUS.is_file() and NEW.is_file() and not RESULT.exists()
    old=[json.loads(s) for s in PREVIOUS.read_text().splitlines() if s]
    new=[json.loads(s) for s in NEW.read_text().splitlines() if s]
    assert len(old)==len(new)==24
    identity=lambda l:{(r["month"],r["case_sha256"]) for r in l}
    assert identity(old)==identity(new)
    month={}
    for m in ("2026-08","2026-09"):
        month[m]=eval_one(m,[r for r in old if r["month"]==m],
                            [r for r in new if r["month"]==m])
    outcome={
       "schema":"else.itil.qa.paired-guided-v4-v3.v1",
       "date":"2026-11-18",
       "baseline":"f46976aa7f21a35b8c7f8e53e5926ca1addf8c1b",
       "case_set_identical":True,
       "months":{"2026-08":1819,"2026-09":545},
       "same_24_historical_source_cases":True,
       "real_model_turns_previous":72,
       "real_model_turns_new":72,
       "user_feedback_simulated":True,
       "human_comprehension_tested":False,
       "certified_diagnoses":0,
       "real_repairs_executed":0,
       "metric_is_not_causal_accuracy":True,
       "actual_model_outputs_compared":True,
       "private_previous_sha256":sha256(PREVIOUS.read_bytes()).hexdigest(),
       "private_new_sha256":sha256(NEW.read_bytes()).hexdigest(),
       "per_month":month,
    }
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(outcome,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"PAIRED_V4_V3_LIVE_QA_COMPLETE","per_month":month},ensure_ascii=False,sort_keys=True))


if __name__=="__main__":main()
