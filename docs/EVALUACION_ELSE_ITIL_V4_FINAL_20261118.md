# ELSE-ITIL V4 — cierre de reevaluación de diagnóstico guiado

Fecha: 18 de noviembre de 2026. Objetivo: orientar al principiante sin ejecutar reparaciones.

## Veredicto

La V4 añade una presentación comprensible, controles sobre afirmaciones de certeza y una derivación explícita al soporte. La exactitud de causas raíz y la comprensión humana real siguen SIN CERTIFICAR.

## Alcance y metodología

El universo documental anterior abarca 1.819 incidentes de agosto y 545 de septiembre de 2026: 2.364 en total. Esta prueba nueva no convirtió todos esos incidentes en conversaciones. Evaluó exactamente los mismos 24 incidentes anonimizados (12 por mes) de la campaña anterior, con tres turnos por caso y 72 llamadas reales al generador Qwen 9B con respaldo Qwen 4B.

Las respuestas del principiante son simuladas. No se ha consultado ninguna solución histórica correcta ni una base empresarial, y no hubo acciones de reparación.

## Resultado emparejado

| Métrica por 24 casos | V2 corregida previa | V4 con código congelado |
|---|---:|---:|
| Primer turno de modelo aceptado por contrato | 24/24 | 22/24 |
| Tres turnos de modelo aceptados por contrato | 20/24 | 17/24 |
| Derivación visible al tercer turno por regla independiente | 24/24 | 24/24 |
| Segundo turno orientado a aclarar o derivar | No equivalente | 24/24 |

La aprobación del contrato mide estructura y seguridad, no diagnóstico causal acertado. Se detectaron 0 indicadores de rechazo en la segunda validación y 0 turnos originalmente aceptados que la validación más reciente rechazaría. No se oculta la posibilidad de regresión de aceptación.

| Mes | Casos probados | Primer turno aceptado V4 | Tres turnos aceptados V4 | Escalamiento visible |
|---|---:|---:|---:|---:|
| Agosto | 12 | 11 | 8 | 12 |
| Septiembre | 12 | 11 | 9 | 12 |

## Cambios implantables

1. Explicación y pregunta para usuario sin jerga, con una única prueba y dos posibles observaciones.
2. Conservación de la memoria de caso anterior, seis turnos máximo, idempotencia y purga a 30 días.
3. Escalamiento anticipado si faltan permisos y derivación cuando persiste el problema.
4. Si el usuario dice que ya funciona, no se declara reparación ni se cierra automáticamente; se propone verificación sin cambios técnicos.
5. Bloqueo de acciones administrativas, peticiones de contraseñas y afirmaciones no verificadas de causa raíz en los textos.
6. Continuidad segura de sesiones V2 existentes, revalidando los recibos anteriores sin sobrescribirlos.
7. Control de salud, autenticación y cola QA, con rollback automático a V2 si falla el despliegue.

## Decisión de despliegue

La V4 obtuvo 17 de 24 conversaciones con sus tres turnos aceptados,
frente a 20 de 24 de la V2 corregida. No representa una mejora
de continuidad y por tanto NO debe sustituir a la V2 en su servicio principal.
Se habilita solo como canario privado independiente en loopback 18913,
con base y memoria separadas y sin acceso externo. La V2 permanece activa
en el puerto privado 18883 y conserva la cola QA.
El script de despliegue es ops/deploy_specialist_v4_private_canary.sh.

## Límites

Las personas y las pantallas del escenario son hipotéticas. NO se ha medido comprensión con usuarios reales, no existe tasa certificada de diagnóstico correcto, y no hay reparaciones ejecutadas. El conjunto de 24 casos es no aleatorio y no debe extrapolarse al universo de 2.364 incidentes.

El paquete privado de revisión por al menos dos lectores y observación de personas principiantes contiene rúbricas vacías. No se rellenaron evaluaciones inexistentes. Antes de compartir ese paquete se requiere evaluación de privacidad y autorización.

## Trazabilidad

Evaluación real: qa/novice_dialogue/evaluate_guided_v4_final_live.py.
Verificador emparejado: qa/novice_dialogue/compare_guided_v4_final_live.py.
Agregados: data/2026_aug_sep_guided_v4_final_paired_eval.json y data/2026_aug_sep_guided_v4_final_live_paired_comparison.json.
Control de presentación: data/2026_aug_sep_guided_v4_projection_audit.json.
Código: else_dominance/guided_dialogue.py y else_dominance/support_http.py.
Despliegue reversivo: ops/deploy_specialist_guided_v4_with_rollback.sh.

Dictamen: apropiado exclusivamente como PILOTO PRIVADO SUPERVISADO, sin permisos para reparar. Los fallos de calidad llevan a atención humana.
