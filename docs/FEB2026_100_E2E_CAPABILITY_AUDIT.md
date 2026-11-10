# ELSE-ITIL: 100 casos reales de febrero de 2026

**QA 10/11/2026.** Rama apilada sobre ELSE-ITIL-SUP PR #17; dependencia ELSE CORE PR #363 (a su vez #362 y #360). No fusionar automáticamente a main.

## Objetivo y ejecución

Evaluar CAPACIDAD ejecutable (no un Pareto de categorías): Qwen9B solicita una lectura de evidencia exacta, ELSE62 ejecuta un SELECT NuGet fijo, el nuevo Hand O5 verifica recibo, O13 Guardian y O15 Dominance, Qwen9B reevalúa el caso, y un auditor independiente reinspecciona la evidencia. Las soluciones históricas se mantuvieron fuera de las inferencias.

Cohorte real: 1.799 incidentes únicos del 1 al 28 de febrero, de los que se seleccionaron 100 SHA de 24 días con registros. Estratificación por tipo de prueba: OT 18, SAP 12, comercial 22, accesos 18, redes 12, otros 18. La selección no es una muestra aleatoria de representatividad poblacional.

## Auditoría independiente

| Control | Resultado |
|---|---:|
| E2E Qwen9B → NuGet → O5/O13/O15 → Qwen9B | 100/100 |
| Recibos independientes verificados | 100/100 |
| Ataques de recibo alterado rechazados antes de O5 | 100/100 |
| Planes aceptados por CONTRATO, no verdad causal | 51/100 |
| Planes rechazados o derivados | 49/100 |
| Rechazos por tablas SQL no vinculadas a fuentes declaradas | 48 |
| Otro rechazo por paso/rol incompleto | 1 |
| Casos con validación de responsable pendiente | 100 |
| Reparaciones certificadas / causas raíz confirmadas por técnico | 0 / 0 |

El primer lote produjo timeouts por SSH en paralelo; 41 respuestas se recuperaron verificando recibos ya ejecutados sin repetir SQL, y los 54 casos restantes se terminaron por transferencia de lote. Cuatro directorios incompletos NO cuentan como resultados.

## Comparación ciega posterior con historial

100/100 resoluciones históricas disponibles en holdout, no visibles durante la inferencia. Qwen4B evaluó 51/51 planes aceptados, excluyendo los 49 rechazados: 12 SUPPORTED, 10 CONFLICT y 29 NOT_DETERMINABLE. Sus etiquetas son una segunda opinión, no pruebas de verdad causal. Evaluó 46/51 notas históricas como VAGUE, 5 ACTIONABLE y observó 36 planes con prueba verificable faltante. No hay tasa de precisión causal certificada.

## Segunda fuente corporativa: OT/SAP

Se creó un nuevo lector de SELECT parametrizado para ELSE70/dbDistribucion_D sobre dbo.taOrdenTrabajoSAP y dbo.taOrdenTrabajoSAPEnvioRespuesta. Para 16 casos con un único número OT mencionado en el ticket, 16/16 lecturas de fuente y recibo válidas: 3 órdenes encontradas en ESA tabla, 13 sin registro en ESA tabla. Una ausencia no prueba que el negocio no tenga la OT en otro sistema, ni se ha hecho un join corporativo certificado ITIL–Distribución.

Reevaluación Qwen9B con la nueva evidencia: 7/16 planes aceptados antes; 10/16 después. Hubo 5 mejoras, 2 regresiones, 5 estables aceptados y 4 estables rechazados. El lector OT/SAP está verificado contra su fuente y esquema, pero aún necesita su propio Hand nativo O5; no se debe confundir con los 100 recibos ITIL O5.

## Brechas para Beta

1. Corregir el patrón dominante de referencias a tablas sin evidencia o declaración verificable (48 casos).
2. Verificar asignaciones de roles y cerrar con pruebas técnicas reales, no solo texto.
3. Integrar OT/SAP bajo un Hand O5 nativo y confirmar vinculación inequívoca de la entidad ITIL con la comercial.
4. Realizar revisión humana de las discrepancias y pasos de cierre; no promocionar automáticamente casos históricos a ejemplos confiables.

**Los 51 contratos PASS no son 51 incidentes resueltos.**

## Evidencia privada en elsecluster5

La ruta /home/u23u/else_itil_feb100_qa_20261110/ contiene independent_audit_100.json, feb100_independent_scorecard.json, feb100_per_case_scorecard.private.jsonl, feb100_peer4b_historical_review.private.jsonl, feb100_historical_holdout.private.jsonl, feb100_ot_independent_audit.private.json, ot_augmented_model_review.private.jsonl y los recibos runs/case_*/verified_final.private.json. Ningún ticket ni resolución histórica se publica en GitHub.
