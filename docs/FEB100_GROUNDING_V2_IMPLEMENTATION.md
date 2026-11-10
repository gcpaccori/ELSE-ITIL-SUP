# ELSE-ITIL — Evidence Grounding V2 (febrero 2026)

**Objetivo:** reparar un defecto estructural detectado en 48 de las 100 respuestas E2E de febrero: referencias SQL cuya procedencia no estaba respaldada por una consulta verificada.

## Contrato de procedencia

1. El catálogo de tablas posibles NO es evidencia de lectura SQL.
2. Para la lectura ITIL de febrero con recibo O5/O13/O15, la única fuente observada es ITIL.taIncidente (tabla física fija ELSE70/dbITIL_D/dbo.taIncidente). Es metadato histórico, NO estado actual del sistema.
3. Cualquier otra mención SQL esquema.tabla en fuentes, hipótesis, diagnóstico, pasos o faltantes provoca rechazo. Las comprobaciones futuras se describen como tareas pendientes, sin inventar nombres de tablas.
4. El plan incluye evidence_refs no vacío, únicamente E1 y/o E2.
5. La respuesta no puede declarar modificaciones ni reparaciones ejecutadas o confirmadas.
6. Solo existe una regeneración opcional por Qwen9B después del primer rechazo. No se insertan nombres de fuentes post-hoc. La segunda respuesta atraviesa todo el gate; si falla queda para revisión humana.

## Componentes

- else_dominance/qa_evidence_grounding.py: política de procedencia, validador y reparación.
- else_dominance/qa_feb100_cluster.py: segundo turno real Qwen con barrera estricta de dos intentos.
- tests/test_qa_feb100_grounding.py: casos sintéticos y ataques de fuente, duplicación, recibo, mención solo en texto, falsas reparaciones y regeneración.
- qa/qa_feb100_grounding_replay.py: 100 nuevas inferencias sobre los mismos recibos O5 anteriores, sin repetir SQL.
- qa/qa_feb100_grounding_audit.py: reinspección independiente de los 100 resultados por SHA, recibo exacto y política.
- qa/qa_feb100_grounding_peer4b.py: comparación orientativa frente a resoluciones históricas ocultas durante generación.

## Interpretación

No confundir PASS contractual con diagnóstico acertado. La mejoría de formato y fundamentación de fuente no constituye precisión causal ni resolución funcional. La asignación de responsables requiere validación de un técnico. Qwen4B no es patrón oro. Prohibida promoción automática a memoria de aprendizaje.

## Cohorte congelada

100 casos distintos del febrero 2026 en 24 días con registros; población histórica 1.799. Baseline previo: 100 recibos O5/O13/O15 correctos, 51 contratos PASS y 49 rechazados, 48 de los cuales presentaron referencias SQL no vinculadas. Qwen4B: 12 compatibles, 10 posibles conflictos y 29 indeterminados entre 51 planes aceptados. Sin reparaciones ni causas confirmadas.

## Evidencia privada

El directorio /home/u23u/else_itil_feb100_grounding_qa_20261110 contiene los resultados nuevos de Qwen, que no sustituyen los artefactos originales. La auditoría produce independent_grounding_v2_audit.json, independent_grounding_v2_per_case.private.jsonl y grounded_v2_replay.private.jsonl. El comparador Qwen4B usa feb100_grounded_v2_peer4b.private.jsonl.

Rama de revisión. No hay despliegue en producción ni modificación del servicio habitual.
