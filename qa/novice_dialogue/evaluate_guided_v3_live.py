"""Paired August/September QA, same 24 case IDs used in prior Nov-17 pilot.

The Qwen9B model is REAL. The novice replies and reported lack of understanding
are synthetic.  No historical gold, corporate queries, repairs, credentials,
production DB writes or real user testing. Private transcripts never go to git.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import os
import time

from else_dominance.agent import OpenAICompatibleModel
from else_dominance.guided_dialogue import GuidedStore,validate_guidance
from qa.novice_dialogue.real_novice_simulation import source,select

ROOT=Path("/home/u23u/else_itil_guided_v2_20261118")
PRIVATE=ROOT/"private"
TRANSCRIPT=PRIVATE/"guided_v3_24cases_72turns.private.jsonl"
DB=PRIVATE/"guided_v3_sessions.sqlite"
PUBLIC=ROOT/"repo"/"data"/"2026_aug_sep_guided_v3_paired_eval.json"
PREVIOUS=Path("/home/u23u/else_itil_guidance_sim_20261117/private/novice_turns.private.jsonl")
PREVIOUS_PUBLIC=Path("/home/u23u/else_itil_guidance_sim_20261117/repo/data/2026_aug_sep_novice_dialogue_independent.json")

QUESTION_2="No entiendo lo que dices. No sé informática ni cómo usar opciones técnicas. Explícame qué debo mirar en la pantalla, sin pedirme contraseña."
QUESTION_3="No cambió el problema. No tengo permisos para modificar nada. ¿Qué otro dato seguro debo revisar y qué mensaje debo comunicar a soporte?"

def run_one(row, primary, fallback):
    sid=None; turns=[]
    ref="EVAL-NOV18-"+row["month"][-2:]+"-"+row["case_key"][:30]
    ticket={"case_ref":ref,"input_scope":"synthetic","service":row["service_code"],
            "description":row["case_text"][:2990]}
    for index in (1,2,3):
        started=time.monotonic()
        db=GuidedStore(DB)
        try:
            if index==1:
                ans=db.start(ticket,primary,fallback)
                sid=ans["session_id"]
            else:
                ans=db.continue_turn(sid,index,
                   QUESTION_2 if index==2 else QUESTION_3,primary,fallback)
        finally:db.close()
        guide=ans["guide"]
        u=guide["para_ti"]
        t=guide["para_soporte"]
        turn={
          "turn":index,
          "status":ans["status"],
          "model_selected":ans["model_selected"],
          "gate_accepted":ans["quality"]["accepted"],
          "flags":ans["quality"].get("flags",[]),
          "validation_flags":validate_guidance(guide),
          "user_step_present":bool(u.get("paso")),
          "user_step":u["paso"],
          "user_observation":u["observa"],
          "user_branch_a":u["si_a"],
          "user_branch_b":u["si_b"],
          "user_question":u["pregunta"],
          "user_explanation":u["explicacion"],
          "support_escalation":t["cuando_escalar"],
          "support_evidence":t["evidencia"],
          "support_verification":t["verificacion_autorizada"],
          "hypotheses":guide["hipotesis"],
          "summary":guide["que_entendi"],
          "no_claimed_execution":ans["executed_changes"] is False,
          "no_certified_diagnosis":ans["diagnosis_certified"] is False,
          "latency_ms":round((time.monotonic()-started)*1000)
        }
        turns.append(turn)
    return {"month":row["month"],"case_sha256":row["case_key"],
            "stratum":("short" if len(row["case_text"].strip())<80
                       else "medium" if len(row["case_text"].strip())<300
                       else "long"),"service":row["service_code"],
            "turns":turns}


def aggregate(rows,baseline):
    baseline_map={(r["month"],r["case_sha256"]):r for r in baseline}
    assert {(x["month"],x["case_sha256"]) for x in rows}==set(baseline_map)
    month_results={}
    for month in ("2026-08","2026-09"):
        cases=[x for x in rows if x["month"]==month]
        count=Counter()
        for case in cases:
            t=case["turns"]
            assert len(t)==3
            assert all(x["no_claimed_execution"] and x["no_certified_diagnosis"] for x in t)
            assert all(x["user_step_present"] for x in t)
            count["all_turn_model_accepted_case"]+=int(all(x["gate_accepted"] for x in t))
            count["all_turns_with_safe_user_step_case"]+=int(all(not x["validation_flags"] for x in t))
            count["third_turn_has_escalation_with_evidence"]+=int(
                "soporte" in t[2]["support_escalation"].lower()
                or "mesa de ayuda" in t[2]["support_escalation"].lower()
            )
            for i,turn in enumerate(t,1):
                count[f"turn{i}_model_accepted"]+=int(turn["gate_accepted"])
                count[f"turn{i}_primary_model"]+=int(turn["model_selected"]=="primary")
                count[f"turn{i}_valid_format"]+=int(not turn["validation_flags"])
                count[f"turn{i}_user_action_with_results"]+=int(bool(turn["user_step"]) and
                    bool(turn["user_observation"]) and bool(turn["user_branch_a"]) and
                    bool(turn["user_branch_b"]))
                count[f"turn{i}_support_section_separate"]+=int(bool(turn["support_verification"]))
                count[f"turn{i}_unconfirmed_causes"]+=int(turn["no_certified_diagnosis"])
            if t[1]["user_step"].strip().lower()!=t[0]["user_step"].strip().lower():
                count["turn2_step_changed"]+=1
            if t[2]["user_step"].strip().lower()!=t[1]["user_step"].strip().lower():
                count["turn3_step_changed"]+=1
        old_cases=[baseline_map[(month,c["case_sha256"])] for c in cases]
        # Same baseline cases; count matched old gate and user-facing screen steps.
        count["baseline_cases_all_turns_accepted"]+=sum(
           all(t["score"]["accepted"] for t in c["turns"]) for c in old_cases)
        count["baseline_first_turn_user_facing_step"]+=sum(
            any( ("usuario" in str(s.get("responsable","")).lower()
                  or "solicitante" in str(s.get("responsable","")).lower())
                 and any(key in str(s.get("accion","")).lower()
                       for key in ("pantalla","clic","abre","mira","ventana","mensaje"))
                 for s in (c["turns"][0]["response"].get("proposal") or {}).get("pasos",[])
                 if isinstance(s,dict))
            for c in old_cases)
        month_results[month]={
            "source_cases":1819 if month=="2026-08" else 545,
            "paired_cases":len(cases),
            "generated_turns":sum(len(x["turns"]) for x in cases),
            "length_strata":dict(Counter(c["stratum"] for c in cases)),
            "metrics":dict(sorted(count.items())),
        }
    return month_results


def main():
    PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True)
    os.chmod(PRIVATE,0o700)
    assert not TRANSCRIPT.exists() and not PUBLIC.exists() and not DB.exists()
    # Initialize schema before concurrent workers to avoid simultaneous O_EXCL
    # creation of the private SQLite file.
    store=GuidedStore(DB)
    store.close()
    data=source()
    sample=select(data["2026-08"][0],"2026-08")+select(data["2026-09"][0],"2026-09")
    assert len(sample)==24
    older=[json.loads(x) for x in PREVIOUS.read_text().splitlines() if x]
    assert len(older)==24
    assert {(x["month"],x["case_key"]) for x in sample}=={
       (x["month"],x["case_sha256"]) for x in older}
    primary=OpenAICompatibleModel("http://127.0.0.1:18782/v1",
                                  "else-itil-riv-qwen9b-gpu6",timeout=125)
    fallback=OpenAICompatibleModel("http://127.0.0.1:8003/v1","qwen35-4b",timeout=120)
    ordered=[item for pair in zip(sample[:12],sample[12:]) for item in pair]
    items=[]
    start=time.monotonic()
    with ThreadPoolExecutor(max_workers=5) as pool:
        requests=[pool.submit(run_one,x,primary,fallback) for x in ordered]
        with TRANSCRIPT.open("x",encoding="utf-8") as f:
            os.chmod(TRANSCRIPT,0o600)
            for future in as_completed(requests):
                row=future.result()
                items.append(row)
                f.write(json.dumps(row,ensure_ascii=False)+"\n")
                f.flush()
                if len(items)%4==0:
                    print(json.dumps({
                        "status":"GUIDED_V3_PROGRESS","cases":len(items),
                        "expected_cases":24,
                        "generated_turns":3*len(items),
                        "elapsed_seconds":round(time.monotonic()-start,1)
                    }),flush=True)
    result=aggregate(items,older)
    public={
      "schema":"else.itil.qa.paired-novice-guidance-v3.v1",
      "dates":"2026-08 and 2026-09",
      "source_case_counts":{"2026-08":1819,"2026-09":545},
      "selection":"EXACT_SAME_24_CASE_SHA_AS_NOV17_BASELINE",
      "real_generator":"Qwen3.5-9B primary with Qwen3.5-4B fallback",
      "calls":72,"cases":24,"turns_per_case":3,
      "novice_replies":"SYNTHETIC_NOT_REAL_USER_SCREEN",
      "test_history_persistent_in_private_sqlite":True,
      "no_historical_solutions_used":True,
      "no_SQL_or_corporate_access":True,
      "repairs_or_actions_executed":0,
      "real_user_validation":False,
      "causal_diagnosis_accuracy_certified":False,
      "baseline_immutable_sha256":sha256(PREVIOUS.read_bytes()).hexdigest(),
      "private_v2_sha256":sha256(TRANSCRIPT.read_bytes()).hexdigest(),
      "private_session_db_sha256":sha256(DB.read_bytes()).hexdigest(),
      "source_redacted_sha256":{m:v[1] for m,v in data.items()},
      "by_month":result,
      "elapsed_seconds":round(time.monotonic()-start,1)
    }
    PUBLIC.write_text(json.dumps(public,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"GUIDED_V3_QA_DONE",
        "cases":24,"calls":72,"elapsed_seconds":public["elapsed_seconds"],
        "by_month":result},ensure_ascii=False,sort_keys=True),flush=True)


if __name__=="__main__":main()
