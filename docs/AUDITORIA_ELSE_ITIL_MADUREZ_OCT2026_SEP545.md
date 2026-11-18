# ELSE-ITIL — auditoría de madurez del último mes cerrado de 2026

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
| Planes históricos generados por Qwen | 543/545 | Emisión del plan, no exactitud |
| Planes históricos aprobados estructuralmente | 508/545 | Formato y contrato |
| Paso seguro de pantalla asignado a principiante, rúbrica estricta | 5/545 | Candidato textual, no comprensión |
| Plan con rol explícito de usuario final | 80/545 | Detección por lenguaje |
| Solicitudes de evidencia comprensible | 190/545 | Patrón textual |
| Planes con ramificación de resultados | 543/545 | No verifica discriminación causal |
| Recorridos de sesión V4 con stub determinista | 545/545 | **Prueba mecánica, no modelo Qwen** |
| Turnos generados por ese stub y persistidos | 1.635 | Persistencia, replay, seguridad |

Para los **545 incidentes no se ejecutaron 1.635 diagnósticos Qwen nuevos**.
La prueba integral de almacenamiento usó respuestas simuladas predefinidas y
verificó estructura, idempotencia, aislamiento de sesión y derivación. Las salidas
de Qwen de esta tabla son **planes históricos**, anteriores a V4.

## 3. Modelo actual V4, prueba emparejada y latencia

El único piloto conversacional Qwen real comparable contiene 24 casos históricos
de agosto/septiembre, 12 por mes y 72 turnos con respuestas de usuario simuladas.

- Qwen V4: **17/24** conversaciones con los tres turnos aceptados por el gate;
  V2 previa: **20/24**.
- Septiembre en la submuestra V4: **9/12** conversaciones
  con tres turnos aceptados; escalamiento seguro determinista **12/12**.
- Globalmente en V4 se aceptaron **64/72** turnos.
- Latencia observada en los 72 turnos: mediana **36.18 s**, p95 (rango más próximo)
  **175.01 s**, máximo **180.41 s**; no hay SLO validado.
- Prueba nueva del canario real con ticket sintético: tres turnos, calidad del modelo
  [False, True, True], latencias **[112.86, 11.2, 24.11] s**.
  El primer turno fue rechazado por el gate y derivado con seguridad; esto
  no se puede contabilizar como diagnóstico acertado.

Esto impide declarar que la V4 ya haya superado a V2 o que sus tiempos de respuesta
estén listos para cualquier usuario sin supervisión.

## 4. Evaluación de **todas las características relevantes**

| Característica | Estado | Evidencia o brecha |
|---|---|---|
| Corporate October 2026 intake freshness | FAIL | 0 source incidents in October; November through 18 also 0; no proof of active ingestion |
| Full latest-available September source provenance | VERIFIED MECHANISM | 545/545 signed Windows SQL records; case identity binds to 545 old plans |
| One-shot archival Qwen plan generation | PARTIAL | 543/545 completed; 508/545 structural approval; old model, not V4 |
| Safe step directed at beginner in archival corpus | NOT MATURE | 5/545 strict textual candidates under conservative rubric, not human success |
| Current guided V4 model quality | NOT MATURE | 9/12 September three-turn complete, 17/24 August+September; regressed versus V2 20/24 |
| Guided session persistence and idempotency | VERIFIED MECHANISM | 545/545 three-turn mechanical cases, 1635 stub outputs; synthetic live V4 replay |
| Plain-language presentation and feedback stages | PARTIAL | V4 text and stage checks, but novice comprehension never observed |
| Deterministic escalation path to authorized support | VERIFIED MECHANISM | Third turn handoff visible 24/24 sampled conversations and live canary |
| Read-only guardrail and blocked automatic repair | VERIFIED MECHANISM | both services show repairs_enabled:false and zero QA writes |
| Service-level API authentication and replay guard | VERIFIED MECHANISM | 401 unauthorized; changed replay 422; shared service token only |
| Individual user and ticket authorization | NOT CERTIFIED | no per-employee identity and no per-case authorization proven |
| Privacy, retention and incident confidentiality | PARTIAL | private signed receipts and redaction; independent privacy approval pending |
| Corporate object/source grounding | NOT CERTIFIED | no exact live domain identity or historical root cause verified for all September cases |
| Diagnostic causal correctness | NOT CERTIFIED | 0 independently adjudicated true root causes; prior historical solutions are not gold |
| Real novice comprehension and success | NOT CERTIFIED | 0 verified real end-user guided tests |
| Module and service breadth | PARTIAL | 105 observed module codes / 10 service codes, but coverage does not prove competence |
| Conditional hypotheses and checks in archival plans | PARTIAL | 543/545 plans show two hypotheses and result branches; no correct-cause validation |
| Response-time and reliability maturity | NOT MATURE | Real 72-turn V4 median 36.18s, p95 175.01s, max 180.41s; no proven SLO |
| Concurrency, failover and production load | NOT CERTIFIED | unit concurrency tests exist; no independent production failover or full-month LLM load test |
| Read-only case/solution lifecycle evidence | PARTIAL | 455 historical solutions and 382 closed flags from separate SQL; not verified AI outcomes |

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

Fuente Windows privada: `C:\Temp\ELSE_ITIL_OCT2026_FRESH_20261118` y
`C:\Temp\ELSE_ITIL_SEPTFULL2026_FRESH_20261118`,
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
