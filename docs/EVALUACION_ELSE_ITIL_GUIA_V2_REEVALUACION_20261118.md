# ELSE-ITIL — reevaluación de diagnóstico guiado para principiantes

**Fecha:** 18/11/2026. **Objetivo:** orientar a personas sin conocimientos informáticos, **sin reparar ni modificar sistemas automáticamente**. Esta evaluación reemplaza la interpretación errónea del porcentaje de planes estructurados como porcentaje de incidentes resueltos.

## Dictamen para la empresa

**SÍ mejoró de manera comprobable la entrega inicial de instrucciones al usuario y ya existe memoria conversacional persistente. NO está todavía certificada su precisión diagnóstica ni la comprensión real de una persona principiante.** La habilitación debe permanecer restringida a un piloto supervisado con respuesta de soporte ante falta de evidencia.

## Comparación emparejada y verificable

Los dos meses de referencia siguen siendo **agosto 2026 (1.819 incidentes)** y **septiembre 2026 (545)**. El universo histórico de **2.364 planes** fue revisado anteriormente. La nueva generación **NO** recorrió de nuevo los 2.364 tickets: se usaron **exactamente los mismos 24 casos** de la simulación anterior, 12 de cada mes, seleccionados de forma determinista, con solicitudes anonimizadas y longitudes balanceadas (**3 breves, 4 medianas, 5 largas por mes**).

Cada caso tiene **tres turnos**: consulta inicial, «no entiendo» y «sigue fallando; no tengo permisos». Se ejecutaron dos rondas nuevas del modelo real, 72 turnos de solicitud por ronda, Qwen3.5 9B como modelo principal y Qwen3.5 4B como alternativa. La segunda ronda añade el intento correctivo de Qwen9B y una guía de seguimiento específica. Las respuestas del usuario son **simuladas**, no corresponden a pruebas reales sobre una pantalla o aplicación.

| Métrica sobre los mismos 24 casos | Sistema anterior | Primera V2 | V2 corregida |
|---|---:|---:|---:|
| Primera indicación por pantalla asignada al usuario final y libre de acciones administrativas, indicador automático | **4/24** | **23/24** | **24/24** |
| Caso con sus tres turnos aceptados por los controles correspondientes | **21/24** | **10/24** | **20/24** |
| Último turno con evidencia y escalamiento detectables en el texto generado | **21/24** | — | **17/24** |
| V2 corregida: conversación que además cambia pasos y tiene escalamiento sustentado en el texto | — | — | **16/24** |

La última métrica es un **indicador automático conservador**, no una tasa de éxito ni evidencia de que el diagnóstico sea correcto. La V2 corregida conservó mejores pasos iniciales, pero el escalamiento **generado por el modelo** todavía no supera al modelo anterior en el conteo emparejado. Esta es una brecha abierta, no debe ocultarse.

### Por mes

| Indicador | Agosto (12) | Septiembre (12) |
|---|---:|---:|
| Nueva V2: primera acción dirigida al principiante | **12** | **12** |
| Nueva V2: los tres turnos aceptados | **11** | **9** |
| Nueva V2: cambio detectable de paso tras «no entiendo» | **12** | **11** |
| Nueva V2: cambio detectable tras «sigue fallando» | **11** | **9** |
| Nueva V2: evidencia y escalamiento en la respuesta final del modelo | **8** | **9** |
| Nueva V2: candidato bajo rúbrica combinada estricta | **8** | **8** |

Los **cuatro casos no aprobados** en la conversación completa no fueron promovidos artificialmente. La capa de seguridad presenta instrucciones conservadoras y mantiene `NEEDS_HUMAN_TRIAGE` cuando el modelo falla sus validaciones.

## Mejoras implementadas en código

1. **Memoria real por sesión:** SQLite privado con identificación aleatoria, vínculo a caso original, turnos consecutivos, idempotencia, rechazo de replays cambiados, vencimiento y purga a 30 días, máximo seis turnos. La versión previa reconstruía artificialmente el contexto en cada solicitud.
2. **Dos capas separadas de respuesta:** `para_ti` tiene explicación, una comprobación de usuario, qué observar, dos ramas alternativas y una pregunta; `para_soporte` contiene verificación reservada a responsables autorizados.
3. **Control de seguridad y veracidad:** SQL, comandos, cambios administrativos, solicitudes de secretos, privilegios y causas afirmadas sin evidencia nunca obtienen un PASS. El modelo no consulta datos de negocio.
4. **Corrección del formato sin relajar validaciones:** reintento del modelo primario con códigos exactos del defecto, luego fallback; ambos pasan el mismo control. Si tampoco cumplen, se abstiene.
5. **Escalamiento garantizado por regla, no atribuido al modelo:** una nueva sección de respuesta `escalamiento_para_usuario` indica cuándo contactar la mesa de ayuda, qué evidencia inocua anotar y qué **no** compartir. Esto corrige una debilidad de experiencia de usuario, pero **no se cuenta como un acierto del modelo** en los 72 turnos ya medidos.
6. **Compatibilidad y aislamiento:** endpoints nuevos sólo mediante habilitación explícita, autenticación existente, dirección loopback, bloqueo concurrente por sesión y no por toda la mesa de ayuda; el servicio `/v1/support` y el despacho QA conservan sus rutas.

## Control de calidad y límites

La prueba emparejada verificó la igualdad de los 24 hashes de caso con la campaña anterior. Hubo 0 consultas corporativas de negocio desde el módulo guiado, 0 cambios, 0 reparaciones certificadas y 0 causas raíz certificadas. Las fuentes, transcripciones privadas y la memoria SQLite de evaluación no se subieron a GitHub; sólo agregados sin identificadores.

Una auditoría adicional con Qwen4B sobre la primera V2 produjo **sólo 6 dictámenes válidos de 24**; los otros 18 quedaron sin calificación. **No se utiliza** para establecer conclusiones de mejora. Las mediciones principales proceden de verificadores deterministas y del contrato de salida, no de «opiniones favorables» de otro modelo.

Faltan **pruebas con personas principiantes reales y especialistas que contrasten los diagnósticos con evidencias**, preferentemente con evaluación ciega de los mismos casos, medición de comprensión y criterio de abstención. Hasta entonces NO es correcto afirmar una tasa de acierto diagnóstico de 100 %, 83 % o cualquier otro porcentaje.

## Dictamen de salida

- **SÍ:** memoria por incidente, guía inicial ejecutable sin privilegios, explicaciones más claras y rutas separadas para usuario y soporte.
- **PARCIAL:** continuidad de tres turnos y escalamiento generado por IA, con abstención segura cuando falta evidencia.
- **NO CERTIFICADO:** causa raíz correcta, capacidad de un principiante real para seguirlo, eficacia en el puesto de trabajo o cierre de incidentes.
- **NO SE DEBE HABILITAR:** reparaciones automáticas ni permisos de mutación.

**Decisión técnica:** liberar como **piloto privado supervisado de diagnóstico guiado**, no como reemplazo del especialista. Mantener el viejo endpoint, el mismo sistema de autorización y una vía de reversión si falla la nueva función.

## Evidencia reproducible

`qa/novice_dialogue/evaluate_guided_v2_live.py`, `evaluate_guided_v3_live.py`, `paired_guidance_v2_independent.py`, `paired_guidance_v3_independent.py`.

Agregados: `data/2026_aug_sep_guided_v2_paired_eval.json`, `data/2026_aug_sep_guided_v3_paired_eval.json`, `data/2026_aug_sep_guided_v2_independent_paired.json`, `data/2026_aug_sep_guided_v3_independent_paired.json`, `data/2026_aug_sep_guided_v2_final_comparison.json`.

Implementación: `else_dominance/guided_dialogue.py`, `else_dominance/support_http.py` y `ops/run_specialist_v2_guided.sh`. Activación con SHA exacto y rollback: `ops/deploy_specialist_guided_v2_with_rollback.sh`.

El informe no reproduce solicitudes, nombres de clientes, claves empresariales, contraseñas ni historial de resoluciones.
