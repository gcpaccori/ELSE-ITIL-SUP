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

---

## Resultado final de la revisión V2.1 sobre la cohorte original

**Auditoría independiente final:** las 100 respuestas nuevas fueron unidas
por SHA-256 con los 100 recibos NuGet originales y los 100 resultados anteriores.
El lector C# de febrero no se reejecutó. Se revalidaron nativamente los
100 recibos mediante O5/O13/O15; se comprobó que ningún plan aceptado citara
fuentes fuera de la única tabla efectivamente observada.

| Indicador | Anterior | V2.1 |
|---|---:|---:|
| Casos E2E con recibo O5 válido | 100 | 100 reinspeccionados |
| Planes aceptados por CONTRATO | 51 | **98** |
| Planes devueltos a revisión | 49 | **2** |
| Planes antiguos recuperados | — | **47** |
| Planes antiguos perdidos | — | **0** |
| Planes finales aceptados con procedencia verificada | — | **98/98** |
| Consultas NuGet nuevas en este replay | — | **0** |
| Reparaciones funcionales certificadas | 0 | **0** |
| Confirmaciones humanas de causa raíz | 0 | **0** |

V2.1 cerró además un bypass detectado por la propia auditoría: dos
expedientes citaban el nombre de un objeto SQL **sin** su prefijo de esquema,
evadiendo el detector inicial. Se volvió a pedir una salida a Qwen
para esos dos expedientes bajo el verificador más estricto; ambos
superaron el contrato después de la regeneración, sin tocar los recibos
originales. Los otros 98 resultados se validaron de nuevo con V2.1.
Se añadieron pruebas para nombres SQL aislados, entre corchetes y
entre comillas, así como para no confundir el final de una oración
(por ejemplo ITIL. El ...) con un nombre de tabla.

**La mejora 51→98 es de fundamentación y calidad contractual, NO de
exactitud diagnóstica.** Los 98 planes siguen necesitando revisión de
los responsables y condiciones reales.

### Segundo evaluador y resolución histórica

Las notas de resolución estuvieron aisladas de Qwen9B durante toda la
generación. Se conservó el juicio Qwen4B de los 98 planes idénticos y
se reexaminaron las dos respuestas modificadas. En los 98 planes
finales aceptados, Qwen4B señaló:

- 43 SUPPORTED, compatibilidad semántica sin confirmación de causa.
- 22 CONFLICT, posible incompatibilidad.
- 33 NOT_DETERMINABLE, insuficiencia de evidencia para decidir.
- 76 planes SPECIFIC, 17 PARTIAL y 5 GENERIC según Qwen4B.
- 73 notas históricas VAGUE, 25 ACTIONABLE; 46 planes señalaron
  carencia de pruebas de cierre verificables según el evaluador.

Qwen4B no es patrón oro: al comparar los mismos 51 casos anteriormente
evaluables, cambió 26 de sus etiquetas de relación debido a los nuevos
planes y/o a variabilidad del revisor. Los 47 casos recién aceptados
no habían sido comparables en la línea base. No se transforma ninguno
de estos conteos en precisión causal.

### Evidencias privadas

- /home/u23u/else_itil_feb100_grounding_qa_20261110/grounded_v2_replay.private.jsonl
- /home/u23u/else_itil_feb100_grounding_qa_20261110/v21/independent_grounding_v21_summary.json
- /home/u23u/else_itil_feb100_grounding_qa_20261110/v21/independent_grounding_v21_core_audit.json
- /home/u23u/else_itil_feb100_grounding_qa_20261110/v21/independent_grounding_v21_per_case.private.jsonl
- /home/u23u/else_itil_feb100_grounding_qa_20261110/v21/feb100_grounded_v21_peer4b.private.jsonl
- /home/u23u/else_itil_feb100_grounding_qa_20261110/v21/peer4b_grounded_v21_comparison.json

No se han trasladado identificadores de tickets, historiales, texto de
usuarios, credenciales o recibos corporativos privados a GitHub.

### Límite de despliegue

Esta es una implementación completa **en la ruta QA de febrero**,
publicada para revisión como PR apilada, no una actualización
fusionada a main ni un servicio productivo ya desplegado. El siguiente
incremento Pareto será incorporar el Hand nativo O5 comercial/OT y
resolver la evidencia de roles/acciones específicas con revisión humana.
