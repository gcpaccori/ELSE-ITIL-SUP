# ELSE-ITIL-SUP — Auditoría comparativa de agosto de 2026

**Alcance:** 1.819 expedientes ITIL de agosto, extracción QA de ELSE70/dbITIL_D/dbo.taIncidente. Evaluación realizada después de completar y sellar la campaña de Qwen9B. No se modificaron los planes originales ni se ejecutaron reparaciones.

## Fuente original y control de filtraciones

La campaña terminó con **1.810 planes aceptados estructuralmente** y **9 rechazados**. Sus soluciones históricas fueron separadas desde el origen en Windows ELSE62. Solo después de cerrar el generador se creó un archivo redactado para el segundo evaluador Qwen4B. El histórico nunca llegó a Qwen9B durante la generación.

SHA-256 del journal original: 9a1e81478dbf89e3ba14ce759ceb3291bb0b1e977044a5fc98a305d0d08b01b1.

## Los nueve rechazos

| Motivo | Casos |
|---|---:|
| Descripción insuficiente | 4 |
| Mención de SQL no observado | 2 |
| Cierre declarado sin evidencia | 2 |
| Fallo técnico o JSON | 1 |

Se regeneraron de forma aislada solo los cinco casos con información suficiente: **3/5** obtuvieron un plan estructuralmente aceptable. Los dos restantes insistieron en mencionar SQL no acreditado. Los cuatro expedientes breves permanecen bloqueados hasta recibir contexto. El registro original 1.810/1.819 **no cambió**.

## Comparación histórica de los 1.810 aceptados

- 1.656 tenían solución histórica no vacía.
- 154 no tenían histórico comparable.
- Qwen4B evaluó 1.655 pares y un par no pudo evaluarse, incluso tras reintento.
- Evaluación Qwen4B: **46 compatibles**, **12 posibles contradicciones**, **1.597 indeterminados**.
- Calidad de histórico estimada por Qwen4B: **57 notas accionables**, **1.598 vagas**.
- Especificidad de planes según Qwen4B: **342 específicos**, **1.157 parciales**, **156 genéricos**.
- Prueba de cierre insuficiente según Qwen4B: **360** planes.

De las 12 posibles contradicciones, **7** corresponden a notas calificadas como accionables y **5** a notas calificadas como vagas. Estas etiquetas son opiniones automáticas, no conclusiones certificadas.

## Control textual sobre los 1.656 pares

Se calculó similitud TF-IDF del plan (diagnóstico, hipótesis, pasos y cierre) respecto de su resolución histórica, comparando contra un emparejamiento aleatorio dentro del mismo código de servicio:

| Indicador | Resultado |
|---|---:|
| Coseno medio del par histórico correspondiente | 0,04201 |
| Coseno medio del control aleatorio mismo servicio | 0,00844 |
| Par verdadero por encima de su control | 658/1.656 |
| Mediana del par verdadero | 0 |

Es un control de coincidencia de términos; **no mide exactitud causal**, reparaciones efectivas ni validez de las notas originales.

## Cola privada para el siguiente incremento

Se seleccionaron **466 casos distintos** sin incorporar su texto al informe: 7 contradicciones con históricos accionables; 5 con históricos vagos; 357 cuya prioridad principal es la prueba de cierre; 87 planes genéricos; 9 rechazados contractualmente y 1 evaluación no disponible.

El total de planes con prueba de cierre insuficiente sigue siendo 360, porque tres están priorizados primero como contradicciones.

## Hallazgo y recomendación técnica

El 99,5 % de aceptación formal del mes **no demuestra** 99,5 % de diagnósticos acertados. Hay dos prioridades técnicas: un catálogo de fuentes consultadas que impida a Qwen introducir nombres SQL no observados, y pruebas de cierre con precondición y resultado concretos. La capacidad de explicar causas reales también exige datos funcionales adicionales; la extracción histórica de una sola tabla no basta.

La auditoría no certifica causas raíz, aprobaciones humanas, reparaciones ni soluciones reales.

## Evidencias privadas — no subir a GitHub

Directorio de la auditoría: /home/u23u/else_itil_aug2026_review_private_20261110/

Archivos: aug2026_rejected9_independent_report.json; aug2026_rejected5_targeted_summary.json; aug2026_full_1810_lexical_comparison.json; aug2026_peer4b.private.jsonl; aug2026_peer4b_unavailable_retry.private.jsonl; aug2026_peer_independent_final_audit.json; aug2026_peer_followup_priority.private.jsonl.

El código reproducible y este resumen agregado pueden publicarse. No se incluyen tickets, soluciones históricas ni resultados por expediente.
