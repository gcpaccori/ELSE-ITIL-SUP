"""Re-score V3 model-generated transcripts through V4 deterministic presentation.

No fresh model calls; this evaluates the PRODUCT/PRESENTATION layer, not new
model quality, novice comprehension, diagnostic accuracy or incident resolution.
Outputs aggregates only; all corporate case text remains on private host.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

from else_dominance.guided_dialogue import (
    _presentation,validate_guidance
)

SOURCE=Path("/home/u23u/else_itil_guided_v2_20261118/private/guided_v3_24cases_72turns.private.jsonl")
PAIRED=Path("/home/u23u/else_itil_guided_v2_20261118/release_main/data/2026_aug_sep_guided_v2_final_comparison.json")
RESULT=Path("/home/u23u/else_itil_guided_v4_20261118/repo/data/2026_aug_sep_guided_v4_projection_audit.json")
QUESTION2="No entiendo lo que dices. No sé informática ni cómo usar opciones técnicas. Explícame qué debo mirar en la pantalla, sin pedirme contraseña."
QUESTION3="No cambió el problema. No tengo permisos para modificar nada. ¿Qué otro dato seguro debo revisar y qué mensaje debo comunicar a soporte?"


def _reconstruct(t):
    return {
      "estado":"INVESTIGACION_PENDIENTE",
      "que_entendi":t["summary"],
      "hipotesis":t["hypotheses"],
      "para_ti":{
         "explicacion":t["user_explanation"],"paso":t["user_step"],
         "observa":t["user_observation"],"si_a":t["user_branch_a"],
         "si_b":t["user_branch_b"],"pregunta":t["user_question"],
      },
      "para_soporte":{
         "cuando_escalar":t["support_escalation"],
         "evidencia":t["support_evidence"],
         "verificacion_autorizada":t["support_verification"],
      },
      "causa_confirmada":False,"ejecutado":False,
    }


def main():
    assert SOURCE.is_file() and PAIRED.is_file() and not RESULT.exists()
    rows=[json.loads(x) for x in SOURCE.read_text().splitlines() if x]
    previous=json.loads(PAIRED.read_text())
    assert len(rows)==24
    assert len({(r["month"],r["case_sha256"]) for r in rows})==24
    grouped={}
    for month in ("2026-08","2026-09"):
        subset=[r for r in rows if r["month"]==month]
        assert len(subset)==12
        metrics=Counter()
        for r in subset:
            assert len(r["turns"])==3
            previous_step=""
            for i,t in enumerate(r["turns"]):
                assert t["turn"]==i+1
                guide=_reconstruct(t)
                original_status=t["status"]
                proposal={"status":original_status,"guide":guide,
                          "quality":{"accepted":t["gate_accepted"]}}
                reply=QUESTION2 if i==1 else QUESTION3 if i==2 else "Tengo un problema y necesito instrucciones sencillas."
                decorated=_presentation(i+1,reply,proposal)
                assert decorated["diagnostico_confirmado"] is False
                assert decorated["accion_ejecutada"] is False
                assert "Una sola comprobación segura:" in decorated["respuesta_sencilla"]
                assert "Si ocurre la primera opción:" in decorated["respuesta_sencilla"]
                assert "Si ocurre la segunda opción:" in decorated["respuesta_sencilla"]
                flags=validate_guidance(guide,previous_step)
                metrics[f"turn{i+1}_hardened_proposal_accepted"]+=int(t["gate_accepted"] and not flags)
                for flag in flags:metrics["hardened_gate_"+flag]+=1
                metrics[f"turn{i+1}_presentation_rendered"]+=1
                if i==1:
                    metrics["turn2_simplification_stage"]+=int(
                        decorated["etapa"]=="ACLARAR_EN_LENGUAJE_SENCILLO"
                        or decorated["etapa"]=="ESCALAR_CON_APOYO_HUMANO")
                if i==2:
                    metrics["turn3_handoff_visible"]+=int(
                        decorated["mostrar_escalamiento"] and
                        decorated["escalamiento"]["mostrar_ahora"])
                    metrics["turn3_handoff_in_simple_text"]+=int(
                        "contacta a la mesa de ayuda" in
                        decorated["respuesta_sencilla"].lower() and
                        "no envíes contraseñas" in
                        decorated["respuesta_sencilla"].lower())
                    metrics["turn3_handoff_due_to_human_triage"]+=int(
                        decorated["etapa"]=="ESCALAR_CON_APOYO_HUMANO")
                    metrics["turn3_handoff_due_to_persistence"]+=int(
                        decorated["etapa"]=="RECOPILAR_EVIDENCIA_Y_ESCALAR")
                    assert len(decorated["escalamiento"]["que_anotar"])==3
                    assert decorated["escalamiento"]["origen"]=="GUARDRAIL_DETERMINISTA_NO_CONCLUSION_DEL_MODELO"
                previous_step=t["user_step"]
        grouped[month]={"cases":12,"previous_model_turns":36,
                        "metrics":dict(sorted(metrics.items()))}
    assert all(grouped[m]["metrics"]["turn3_handoff_visible"]==12 for m in grouped)
    result={
       "schema":"else.itil.qa.guided-v4-output-projection.v1",
       "date":"2026-11-18",
       "source_original_cases":{"2026-08":1819,"2026-09":545},
       "identical_paired_sample_24":True,
       "method":"OFFLINE_REPLAY_OF_PREVIOUS_72_REAL_QWEN_GUIDES",
       "fresh_llm_calls":0,
       "original_llm_sample_calls":72,
       "replayed_cases":24,
       "evaluation":grouped,
       "original_baseline_model_third_turn_escalation":previous["aggregate_counts"]["third_turn_evidence_and_escalation_model_baseline"],
       "model_v3_third_turn_escalation":previous["aggregate_counts"]["third_turn_evidence_and_escalation_model_v2_corrected"],
       "deterministic_v4_third_turn_escalation":24,
       "deterministic_handoff_is_not_model_diagnostic_success":True,
       "historical_solutions_used":False,
       "understanding_tested_with_real_people":False,
       "real_diagnoses_certified":0,
       "real_repairs_executed":0,
       "private_transcripts_sha256":sha256(SOURCE.read_bytes()).hexdigest(),
       "private_transcripts_not_published":True,
       "limitations":["No human comprehension test","No actual screen events",
                      "Potential V4 gate rejects additional former accepted response",
                      "All stage-specific human replies simulated"],
    }
    RESULT.parent.mkdir(parents=True,exist_ok=True)
    RESULT.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"GUIDED_V4_OFFLINE_PAIRED_PROJECTION_PASS",
                      "grouped":grouped},ensure_ascii=False,sort_keys=True))
if __name__=="__main__":main()
