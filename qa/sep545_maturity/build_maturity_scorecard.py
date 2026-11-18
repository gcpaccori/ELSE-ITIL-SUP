"""Decision-gated ELSE-ITIL maturity evidence, latest populated Sep 2026.

Strictly no customer text, hashed case identities, private model transcripts
or unreviewed historical solution content in public outputs. Pass for technical
mechanisms is not equivalent to causally correct incident diagnosis.
"""
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,statistics,math

ROOT=Path("/home/u23u/else_itil_sep545_maturity_20261118")
DATA=ROOT/"repo"/"data"
DOCS=ROOT/"repo"/"docs"
FULL=DATA/"2026_sep545_full_maturity_evidence.json"
V4=DATA/"2026_aug_sep_guided_v4_final_live_paired_comparison.json"
PRIVATE=ROOT/"private"/"runtime_canary_e2e.private.json"
V4_PRIVATE=Path("/home/u23u/else_itil_guided_v4_20261118/private/guided_v4_final_24cases_72turns.private.jsonl")
SCORE=DATA/"2026_sep545_all_features_maturity_scorecard.json"
REPORT=DOCS/"AUDITORIA_ELSE_ITIL_MADUREZ_OCT2026_SEP545.md"

def load(path:Path):
    return json.loads(path.read_text())

def decision():
    assert all(p.exists() for p in (FULL,V4,PRIVATE,V4_PRIVATE))
    assert not SCORE.exists() and not REPORT.exists()
    full=load(FULL)
    v4=load(V4)
    smoke=load(PRIVATE)
    assert full["requested_last_closed_month"]=="2026-10"
    assert full["october_cases_corporate"]==0
    assert full["september_total"]==545
    assert full["september_all_cases_independently_bound_to_windows"] is True
    assert full["september_historical_nonempty_solution_records"]==455
    assert full["september_historical_closed_date_present"]==382
    assert full["september_mechanical_stub_only"]["three_turns_stored"]==545
    assert full["september_mechanical_stub_only"]["stub_generated_turns"]==1635
    assert full["real_llm_calls_during_545_mechanical_check"]==0
    assert full["identity_case_set_sha256"]=="aabbd6c4e1eebedcb116b3c490e9fe253dcfc35550cfbf49f7fb27b09b6a9a9c"
    assert v4["case_set_identical"] and v4["same_24_historical_source_cases"]
    assert v4["certified_diagnoses"]==0 and v4["real_repairs_executed"]==0
    assert smoke["real_qwen_requests_for_synthetic_case"]==3
    assert smoke["unauthorized_http_status"]==401
    assert smoke["changed_replay_http_status"]==422
    assert smoke["replay_exact"] and smoke["repair_actions_executed"]==0
    assert smoke["human_handoff_third"]
    assert smoke["diagnoses_certified"]==0
    rows=[json.loads(l) for l in V4_PRIVATE.read_text().splitlines() if l]
    assert len(rows)==24 and len({(r["month"],r["case_sha256"]) for r in rows})==24
    turns=[t for r in rows for t in r["turns"]]
    assert len(turns)==72
    latencies=sorted(float(t["latency_ms"])/1000 for t in turns)
    median=round(statistics.median(latencies),2)
    p95=round(latencies[math.ceil(.95*len(latencies))-1],2)
    mx=round(latencies[-1],2)

    counts=full["september_model_metrics"]
    results=v4["per_month"]
    sep=results["2026-09"]["counts"]
    aug=results["2026-08"]["counts"]
    v4_complete=sum(v["counts"]["new_all_three_accepted"] for v in results.values())
    prior_complete=sum(v["counts"]["prior_all_three_accepted"] for v in results.values())
    v4_turn_accepted=sum(sum(t["gate_accepted"] for t in r["turns"]) for r in rows)
    assert v4_complete==17 and prior_complete==20
    assert sep["new_all_three_accepted"]==9
    assert sep["turn3_user_handoff_visible"]==12
    assert aug["turn3_user_handoff_visible"]==12
    assert v4_turn_accepted==64

    domains=[
      ("Corporate October 2026 intake freshness","FAIL",
       "0 source incidents in October; November through 18 also 0; no proof of active ingestion"),
      ("Full latest-available September source provenance","VERIFIED_MECHANISM",
       "545/545 signed Windows SQL records; case identity binds to 545 old plans"),
      ("One-shot archival Qwen plan generation","PARTIAL",
       "543/545 completed; 508/545 structural approval; old model, not V4"),
      ("Safe step directed at beginner in archival corpus","NOT_MATURE",
       "5/545 strict textual candidates under conservative rubric, not human success"),
      ("Current guided V4 model quality","NOT_MATURE",
       "9/12 September three-turn complete, 17/24 August+September; regressed versus V2 20/24"),
      ("Guided session persistence and idempotency","VERIFIED_MECHANISM",
       "545/545 three-turn mechanical cases, 1635 stub outputs; synthetic live V4 replay"),
      ("Plain-language presentation and feedback stages","PARTIAL",
       "V4 text and stage checks, but novice comprehension never observed"),
      ("Deterministic escalation path to authorized support","VERIFIED_MECHANISM",
       "Third turn handoff visible 24/24 sampled conversations and live canary"),
      ("Read-only guardrail and blocked automatic repair","VERIFIED_MECHANISM",
       "both services show repairs_enabled:false and zero QA writes"),
      ("Service-level API authentication and replay guard","VERIFIED_MECHANISM",
       "401 unauthorized; changed replay 422; shared service token only"),
      ("Individual user and ticket authorization","NOT_CERTIFIED",
       "no per-employee identity and no per-case authorization proven"),
      ("Privacy, retention and incident confidentiality","PARTIAL",
       "private signed receipts and redaction; independent privacy approval pending"),
      ("Corporate object/source grounding","NOT_CERTIFIED",
       "no exact live domain identity or historical root cause verified for all September cases"),
      ("Diagnostic causal correctness","NOT_CERTIFIED",
       "0 independently adjudicated true root causes; prior historical solutions are not gold"),
      ("Real novice comprehension and success","NOT_CERTIFIED",
       "0 verified real end-user guided tests"),
      ("Module and service breadth","PARTIAL",
       "105 observed module codes / 10 service codes, but coverage does not prove competence"),
      ("Conditional hypotheses and checks in archival plans","PARTIAL",
       "543/545 plans show two hypotheses and result branches; no correct-cause validation"),
      ("Response-time and reliability maturity","NOT_MATURE",
       f"Real 72-turn V4 median {median}s, p95 {p95}s, max {mx}s; no proven SLO"),
      ("Concurrency, failover and production load","NOT_CERTIFIED",
       "unit concurrency tests exist; no independent production failover or full-month LLM load test"),
      ("Read-only case/solution lifecycle evidence","PARTIAL",
       "455 historical solutions and 382 closed flags from separate SQL; not verified AI outcomes"),
    ]
    result={
      "schema":"else.itil.qa.2026-sep545-maturity-decision.v1",
      "date":"2026-11-18",
      "decision":"NO",
      "decision_label":"NOT_MATURE_ACROSS_ALL_CHARACTERISTICS",
      "eligible_for_supervised_private_pilot":True,
      "eligible_for_unsupervised_corporate_rollout":False,
      "source_october_2026_cases":0,
      "source_november_1_to_18_cases":0,
      "latest_populated_month":"2026-09",
      "september_all_incidents_bound":545,
      "september_archived_model_completion":counts["completed"],
      "september_archived_structural_quality":counts["structural_accepted"],
      "september_archived_beginner_proxy":counts["strict_beginner_one_shot_proxy"],
      "september_archived_role_for_end_user":counts["has_end_user_assigned_role_pattern"],
      "september_archived_evidence_request":counts["has_user_friendly_evidence_request"],
      "september_archived_branches":counts["has_result_branching"],
      "september_historical_solution_present":455,
      "september_historical_closed_date_present":382,
      "full_545_mechanical_sessions_with_stub":545,
      "full_545_mechanical_turns_stub_not_model":1635,
      "qwen_full545_guided_calls_made":0,
      "v4_recent_paired_cases":24,
      "v4_recent_paired_turns":72,
      "v4_accepted_turns":v4_turn_accepted,
      "v4_three_turn_cases":v4_complete,
      "v2_three_turn_cases":prior_complete,
      "v4_september_sample_three_turn_cases":sep["new_all_three_accepted"],
      "v4_september_sample_denominator":12,
      "v4_escalation_deterministic_sample":24,
      "v4_synthetic_canary_first_model_quality_accepted":smoke["model_gate_accepted"][0],
      "v4_synthetic_canary_model_gate_sequence":smoke["model_gate_accepted"],
      "v4_synthetic_canary_live_response_seconds":smoke["latency_seconds_per_turn"],
      "v4_sample72_response_latency_seconds":{"p50":median,"p95_nearest_rank":p95,"max":mx},
      "individual_human_reviews":0,
      "independently_certified_diagnoses":0,
      "business_writes":0,
      "hmac_source_and_history_verified_on_windows":True,
      "live_synthetic_case_only_not_business_grounded":True,
      "services_operating_mode":"V2 MAIN ON 18883; V4 PRIVATE CANARY ON 18913; REPAIRS DISABLED",
      "maturity_domains":[{"area":a,"status":s,"evidence":e} for a,s,e in domains],
      "failure_gates":[
        "no October 2026 incidents in the selected corporate QA ITIL data source",
        "no independent adjudication of model causes against authoritative records",
        "no real novice comprehension or user-observed outcomes",
        "V4 three-turn gate acceptance 17/24 below prior V2 20/24",
        "no demonstrated response-time SLO or HA/load maturity",
      ],
      "private_sources_not_distributed":True,
      "source_binding_fingerprint":full["identity_case_set_sha256"],
      "sha256_v4_private_sample":sha256(V4_PRIVATE.read_bytes()).hexdigest(),
      "sha256_private_synthetic_canary_smoke":sha256(PRIVATE.read_bytes()).hexdigest(),
      "limits":"Not a diagnostic accuracy score or evidence of business incidents being resolved",
    }
    SCORE.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    DOCS.mkdir(parents=True,exist_ok=True)
    rows_md="\n".join(f"| {a} | {s.replace('_',' ')} | {e} |" for a,s,e in domains)
    report=f"""# ELSE-ITIL — auditoría de madurez del último mes cerrado de 2026

Fecha de verificación: **18 de noviembre de 2026**. Dictamen: **NO ESTÁ MADURO PARA TODAS SUS CARACTERÍSTICAS**.

## 1. Alcance y evidencia corporativa

Se verificó octubre de 2026, el último mes calendario completo, directamente contra
`ELSE70/dbITIL_D/dbo.taIncidente` mediante `SIELSEAccesoDatos` de SOLO LECTURA
en `ELSE62`. **Octubre registró 0 incidentes en esta fuente.** Noviembre del 1 al 18
también registró 0. La última solicitud visible es del **16 de septiembre de 2026**.
**No se afirma que la empresa tuviera cero incidentes**, sino que la fuente seleccionada
no contiene datos para esas fechas. Urge verificar la ingesta y la fuente oficial.

Por ello se auditó el **último mes con registros disponible: septiembre de 2026**.
Una segunda lectura fresca del mes dio **545/545** incidentes, 10 códigos de servicio,
105 códigos de módulo y siete días con eventos. El conjunto íntegro de identidades
coincidió exactamente con los **545 planes históricos**. Los recibos de fuente e
historial se firmaron en ELSE62 y se verificaron criptográficamente por HMAC
sin transferir clientes ni credenciales.

Las respuestas históricas presentes son **455**, y los registros con fecha de cierre
son **382**. Son datos administrativos. No prueban ni un diagnóstico ni una reparación
ejecutada por la IA.

## 2. Qué se midió en los 545 casos

| Métrica, planes de septiembre | Resultado | Lectura correcta |
|---|---:|---|
| Casos originales con descripción | 545/545 | Cobertura documental |
| Planes históricos generados por Qwen | {counts["completed"]}/545 | Emisión del plan, no exactitud |
| Planes históricos aprobados estructuralmente | {counts["structural_accepted"]}/545 | Formato y contrato |
| Paso seguro de pantalla asignado a principiante, rúbrica estricta | {counts["strict_beginner_one_shot_proxy"]}/545 | Candidato textual, no comprensión |
| Plan con rol explícito de usuario final | {counts["has_end_user_assigned_role_pattern"]}/545 | Detección por lenguaje |
| Solicitudes de evidencia comprensible | {counts["has_user_friendly_evidence_request"]}/545 | Patrón textual |
| Planes con ramificación de resultados | {counts["has_result_branching"]}/545 | No verifica discriminación causal |
| Recorridos de sesión V4 con stub determinista | 545/545 | **Prueba mecánica, no modelo Qwen** |
| Turnos generados por ese stub y persistidos | 1.635 | Persistencia, replay, seguridad |

Para los **545 incidentes no se ejecutaron 1.635 diagnósticos Qwen nuevos**.
La prueba integral de almacenamiento usó respuestas simuladas predefinidas y
verificó estructura, idempotencia, aislamiento de sesión y derivación. Las salidas
de Qwen de esta tabla son **planes históricos**, anteriores a V4.

## 3. Modelo actual V4, prueba emparejada y latencia

El único piloto conversacional Qwen real comparable contiene 24 casos históricos
de agosto/septiembre, 12 por mes y 72 turnos con respuestas de usuario simuladas.

- Qwen V4: **{v4_complete}/24** conversaciones con los tres turnos aceptados por el gate;
  V2 previa: **{prior_complete}/24**.
- Septiembre en la submuestra V4: **{sep["new_all_three_accepted"]}/12** conversaciones
  con tres turnos aceptados; escalamiento seguro determinista **12/12**.
- Globalmente en V4 se aceptaron **{v4_turn_accepted}/72** turnos.
- Latencia observada en los 72 turnos: mediana **{median} s**, p95 (rango más próximo)
  **{p95} s**, máximo **{mx} s**; no hay SLO validado.
- Prueba nueva del canario real con ticket sintético: tres turnos, calidad del modelo
  {smoke["model_gate_accepted"]}, latencias **{smoke["latency_seconds_per_turn"]} s**.
  El primer turno fue rechazado por el gate y derivado con seguridad; esto
  no se puede contabilizar como diagnóstico acertado.

Esto impide declarar que la V4 ya haya superado a V2 o que sus tiempos de respuesta
estén listos para cualquier usuario sin supervisión.

## 4. Evaluación de **todas las características relevantes**

| Característica | Estado | Evidencia o brecha |
|---|---|---|
{rows_md}

**Regla de decisión:** cada área con estado *VERIFIED MECHANISM* certifica
únicamente un mecanismo técnico probado, no un resultado correcto para el negocio.
Un sistema no alcanza madurez integral si faltan registros actuales, no se han
comprobado causas raíz, ninguna persona principiante ha demostrado comprensión
y la continuidad del modelo todavía retrocede.

## 5. Resultado operacional y decisión

La V2 permanece como atención principal privada en `127.0.0.1:18883`,
con despacho QA. La V4 se ejecuta como canario privado independiente en
`127.0.0.1:18913`. Ambas reportan `READY` y
`repairs_enabled:false`. Se observaron 401 para llamadas sin token y 422
ante replay cambiado de la misma sesión. El token es de servicio compartido,
no representa identificación y autorización individual de empleados.

**SÍ** se ha demostrado procedencia del conjunto 545, ejecución de
controles, persistencia conversacional, autenticación básica y derivación.
**NO** se ha demostrado exactitud del diagnóstico, comprensión real,
cobertura de incidentes de octubre, madurez de tiempos de respuesta,
autorización por persona ni alta disponibilidad en carga.

**Dictamen final: NO GO para afirmar madurez integral o desplegar autoservicio
corporativo desatendido. SÍ puede continuar el piloto privado supervisado,
sin reparaciones automáticas.**

## 6. Trazabilidad

Fuente Windows privada: `C:\\Temp\\ELSE_ITIL_OCT2026_FRESH_20261118` y
`C:\\Temp\\ELSE_ITIL_SEPTFULL2026_FRESH_20261118`,
recibos HMAC con fuente e historial separados.
Conjunto privado Linux histórico: `september_blind.private.jsonl`,
`september_plans_redacted.private.jsonl`.
Scripts reproducibles: `qa/sep545_maturity/audit_full_545.py` y
`qa/sep545_maturity/build_maturity_scorecard.py`.
Agregados públicos: `data/2026_sep545_full_maturity_evidence.json` y
`data/2026_sep545_all_features_maturity_scorecard.json`.
No se incluyen transcripciones privadas, clientes, IDs de incidentes ni soluciones.

**Limitación material:** solo se verificó la ruta corporativa de ITIL indicada;
puede haber otras fuentes empresariales o falta de sincronización que deban
analizarse. Cero registros no equivale a cero actividad empresarial.
"""
    REPORT.write_text(report)
    return {
        "status":"FULL_545_MATURITY_SCORECARD_AND_REPORT_CREATED",
        "decision":result["decision"],
        "areas":len(domains),
        "september_archived_plan_quality":counts["structural_accepted"],
        "v4_september_three_turn":sep["new_all_three_accepted"],
        "v4_all24_three_turn":v4_complete,
        "latency_p95_s":p95,
        "unverified_human_diagnoses":0,
    }

if __name__=="__main__":
    print(json.dumps(decision(),ensure_ascii=False,sort_keys=True))
