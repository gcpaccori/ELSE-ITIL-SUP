# G2: Ejecución de septiembre de 2026 con frontera de datos

Fecha: 2026-11-03. Objetivo: 545 expedientes QA de septiembre de 2026.

## Hechos comprobados

- El evaluador retrospectivo en `ELSE62` confirma **545 registros de septiembre**, dentro de 14,950 de enero–septiembre. Los datos individuales NO salieron de QA.
- La API de solicitudes nuevas de ELSE-ITIL-SUP en GPU funciona, pero tiene `source_access=USER_SUBMITTED_ONLY`. No puede leer tickets corporativos por sí sola.
- En `ELSE62` no hay configuración operativa de `TIC_PRIVATE_QA_CONFIG`, `TIC_CATALOG_PATH` ni `TIC_LLM_BASE_URL`; se comprobaron únicamente booleanos, sin revelar secretos.
- Un lote de **545 casos enteramente sintéticos**, con un modelo de prueba, se procesó y reanudó sin duplicar respuestas; esto prueba el mecanismo del lote, no diagnósticos reales.
- Las inferencias con Qwen 4B/9B sobre incidentes ficticios se demostraron anteriormente, pero NO constituyen 545 atenciones en QA.
- No existen pruebas de reparación ejecutada, ni confirmación de usuarios para ningún caso de la cohorte.

## Ejecutar un mes completo sin mezclarlo con pruebas

`else_dominance.month_2026` implementa una puerta previa al modelo:

1. Comprobar mes `2026-09` y exactamente 545 entradas únicas.
2. Ocultar las soluciones del analista de los expedientes evaluados.
3. Validar históricos anteriores al 1 de enero de 2026.
4. Exigir un artefacto de aprobación gestionado por una autoridad externa, con HMAC de una clave separada, fechas, host, modelo, endpoint y SHA-256 de ambos archivos.
5. Vincular una reanudación al histórico, casos, modelo y autorización exactos; rechazar cambios de cohorte.
6. Conservar expedientes y recibos en rutas privadas; el resumen no contiene solicitudes ni respuestas individuales.
7. Publicar `PLAN_REVIEWABLE`, `PLAN_REJECTED` o `MODEL_ERROR`; nunca `CERTIFIED_FIX` sin prueba corporativa.

El código **no incluye** una función de firma para aprobarse a sí mismo: la autorización debe originarse en el mecanismo institucional de control. La firma técnica no demuestra por sí misma autoridad jurídica, ni sustituye la comprobación de las políticas de datos.

### Contrato de datos

Los archivos privados JSONL se ubican en el host autorizado; las solicitudes de septiembre deben tener exactamente:
`case_ref`, `opened_at`, `description`, `service_code`, `module_code`, `classification_code`, `privacy_reviewed`, y una versión cuando exista.
NUNCA deben incluir `solution_text`, `DescripcionSolucion` ni la solución humana del mismo expediente.

Los antecedentes necesitan fecha de apertura, fecha de resolución y de última modificación **anteriores a 2026**, además de servicio, módulo, texto de solicitud y solución histórica. Esa solución es **antecedente no verificado**, no verdad certificada.

### Comando cuando la autorización y el corpus estén presentes

```bash
python -m else_dominance.month_2026 \
 --history /RUTA_PRIVADA/history_pre2026.jsonl \
 --holdout /RUTA_PRIVADA/septiembre2026_solicitudes.jsonl \
 --output /RUTA_PRIVADA/septiembre2026_resultados.jsonl \
 --approval-file /RUTA_PRIVADA/aprobacion_externa_firmada.json \
 --model MODELO_AUTORIZADO \
 --base-url URL_DEL_ENDPOINT_AUTORIZADO \
 --expected-count 545
```

NO ejecutar ni transportar expedientes con un túnel GPU o endpoint externo a QA
sin que la autorización de tratamiento incluya explícitamente ese destino.
El permiso de consulta a una base no implica permiso de transmitir sus textos a otro host.

### Pruebas sintéticas

`--synthetic-only` habilita una verificación del lote sin aprobación corporativa
**solo** con IDs `itil-SYN...` y marca `synthetic: true` tanto en
histórico como en solicitudes. No usar este modo con expedientes reales.

### Criterio para declarar septiembre atendido

La cobertura requiere 545 expedientes identificados, 545 resultados individuales,
todos los fallos contabilizados, revisión técnica adversarial y comprobación de
acciones y responsables según roles corporativos autorizados. Plan revisable no
equivale a reparación; un ticket puede estar legítimamente pendiente de autorización.

**Estado actual:** 0/545 tickets reales inferidos por este flujo; 0 reparaciones
corporativas certificadas. Seguimiento [G2](https://github.com/gcpaccori/ELSE-ITIL-SUP/issues/2).
