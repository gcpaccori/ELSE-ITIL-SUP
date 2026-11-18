"""Assemble a PRIVATE, unscored novice/technical review packet from paired QA.

It contains operational incident excerpts: never commit its outputs or share
them without a separate authorized privacy review. Does NOT simulate humans.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
import json,os,random

from else_dominance.guided_dialogue import _presentation,_scrub
from qa.novice_dialogue.real_novice_simulation import source, select

ROOT=Path("/home/u23u/else_itil_guided_v4_20261118")
PRIVATE=ROOT/"private"
MODEL=Path("/home/u23u/else_itil_guided_v4_20261118/private/guided_v4_final_24cases_72turns.private.jsonl")
OUTPUT=PRIVATE/"novice_human_review_packet_v4.private.jsonl"
META=PRIVATE/"novice_human_review_metadata_v4.private.json"
FEEDBACK=[
    "La primera respuesta es al problema original.",
    "No entiendo ese paso; necesito que lo expliques sin tecnicismos.",
    "Sigue el problema y no puedo cambiar permisos."
]
DIMENSIONS=[
    "claridad_para_principiante_0a2",
    "puede_ejecutar_paso_sin_privilegios_0a2",
    "distingue_resultados_posibles_0a2",
    "adapta_la_guia_al_feedback_0a2",
    "evidencia_no_sensible_y_escalamiento_0a2",
    "incertidumbre_causal_correcta_0a2",
    "prueba_seguridad_pasa_si_no",
    "usuario_pudo_expicar_paso_con_sus_palabras_0a1",
]


def run():
    assert MODEL.exists() and not OUTPUT.exists() and not META.exists()
    PRIVATE.mkdir(parents=True,mode=0o700,exist_ok=True)
    os.chmod(PRIVATE,0o700)
    data=source()
    subset=select(data["2026-08"][0],"2026-08")+select(data["2026-09"][0],"2026-09")
    bykey={(r["month"],r["case_key"]):r for r in subset}
    previous=[json.loads(x) for x in MODEL.read_text().splitlines() if x]
    assert len(previous)==24
    assert {(r["month"],r["case_sha256"]) for r in previous}==set(bykey)
    rng=random.Random("PRIVATE_ELSE_ITIL_BLIND_REVIEW_V4_2026_11_18")
    rng.shuffle(previous)
    outputs=[]
    for idx,case in enumerate(previous,1):
        key=(case["month"],case["case_sha256"])
        original=bykey[key]
        rounds=[]
        for i,t in enumerate(case["turns"]):
            guide={
              "que_entendi":_scrub(t["summary"]),
              "para_ti":{
                "explicacion":_scrub(t["user_explanation"]),
                "paso":_scrub(t["user_step"]),
                "observa":_scrub(t["user_observation"]),
                "si_a":_scrub(t["user_branch_a"]),
                "si_b":_scrub(t["user_branch_b"]),
                "pregunta":_scrub(t["user_question"]),
              },
              "para_soporte":{
                "cuando_escalar":_scrub(t["support_escalation"]),
                "evidencia":_scrub(t["support_evidence"]),
                "verificacion_autorizada":_scrub(t["support_verification"]),
              },
            }
            result={
              "guide":guide,
              "status":t["status"],
              "quality":{"accepted":t["gate_accepted"]}
            }
            rendered=_presentation(i+1,FEEDBACK[i],result)
            rounds.append({
              "turn":i+1,
              "scenario_feedback_synthetic":FEEDBACK[i],
              "presentacion":rendered["respuesta_sencilla"],
              "model_gate_accepted":t["gate_accepted"],
              "requires_human_verification":True,
              "questions_for_reviewer":{
                  field:None for field in DIMENSIONS
              },
              "free_text_evidence":None,
              "reviewer_role":None,
            })
        outputs.append({
            "blind_case_code":f"QA-{idx:02d}",
            "month":case["month"],
            "request_privately_redacted":_scrub(original["case_text"])[:1400],
            "model_answers_are_not_operational_facts":True,
            "historical_resolution_excluded":True,
            "privacy_clearance_before_distribution_required":True,
            "turns":rounds,
        })
    with OUTPUT.open("x",encoding="utf8") as out:
        os.chmod(OUTPUT,0o600)
        for rec in outputs:
            out.write(json.dumps(rec,ensure_ascii=False)+"\n")
    metadata={
       "schema":"else.itil.qa.human-novice-review-packet.v1",
       "cases":len(outputs),"turns":sum(len(r["turns"]) for r in outputs),
       "requested_independent_reviewers_per_case":2,
       "minimum_novice_observation_participants":6,
       "reviewer_marks_filled":0,
       "actual_human_participants":0,
       "human_success_certified":False,
       "dimensions":DIMENSIONS,
       "source_private_sha256":sha256(MODEL.read_bytes()).hexdigest(),
       "private_packet_sha256":sha256(OUTPUT.read_bytes()).hexdigest(),
       "packet_has_private_incident_excerpts":True,
       "forbidden_to_publish_without_approval":True
    }
    META.write_text(json.dumps(metadata,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    os.chmod(META,0o600)
    print(json.dumps({
       "status":"PRIVATE_UNSCORED_HUMAN_REVIEW_PACKET_READY",
       "cases":24,"turns":72,
       "human_scores_present":False,
       "privacy_clearance_required":True,
       "packet_sha256":metadata["private_packet_sha256"]
    },ensure_ascii=False))


if __name__=="__main__":run()
