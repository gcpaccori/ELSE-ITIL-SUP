# ELSE-ITIL-SUP: catálogo técnico de procedimientos históricos

**Fecha:** 12 noviembre 2026. **Baseline antes del cambio:** main@8f0da149eb07c122f7800dbb72f16ba9fe341d88.

## Objetivo y límites

Aproximar el especialista a los procedimientos que documentaron los técnicos de ELSE, sin atender ni modificar los incidentes por su cuenta. Una referencia a una tabla, columna o procedimiento almacenado dentro de una nota no es evidencia de una operación ejecutada. Las consultas de este catálogo son de solo lectura.

## Fuentes y separación de entrenamiento

Se leyeron cinco páginas sucesivas de 100 incidentes de mayo de 2026 desde ELSE70/dbITIL_D, por fecha y código. Los 500 casos son distintos. La consulta de la solicitud y la de la solución histórica originaron recibos separados, firmados, verificables en el entorno privado. El corpus de mayo completo contiene 1.714 casos.

- Las primeras tres páginas, **300 atenciones**, se utilizaron para extraer precedentes de dominio técnico.
- Las páginas 4 y 5 quedaron **excluidas de la construcción**; se utilizaron exclusivamente como pruebas independientes.
- La extracción inicial de las 300 notas reconoció **45 atenciones con referencias estructuradas**, distribuidas entre 74 módulos con historial y 41 patrones únicos por módulo. El piloto previo conservó 42, pero uno se descartó por tener una referencia SQL truncada.
- Los patrones conservan únicamente tipo de referencia, tabla, campos y frecuencia. Se eliminan valores, identificadores, SQL completo y descripciones personales.
- Las referencias se contrastan contra metadatos de tabla y columnas del atlas QA. No acreditan que la tabla estuviera vinculada a la incidencia, ni que el SQL documentado se ejecutara.

## Consulta

Se añadió el comando qa-history-patterns con variable de entorno TIC_QA_HISTORICAL_PATTERNS_PATH que apunta al índice privado. Permite consultar el resumen del corpus o un módulo corporativo con el argumento --module.

Para el agente, la herramienta inspect_historical_procedures acepta exactamente un módulo y exige que sea el mismo módulo del incidente. No acepta SQL u otros argumentos y bloquea la consulta si falta el catálogo. Sus resultados son pistas que deben contrastarse con el expediente actual y no justifican una conclusión causal.

## Prueba independiente: lote 4

| Comprobación sobre 100 expedientes reales | Resultado |
|---|---:|
| Existe algún precedente estructurado del módulo | 51 |
| La propia solución histórica contiene una referencia SQL estructurada | 26 |
| La clase de acción, tabla y conjunto de campos coinciden exactamente | **9** |
| Causas verificadas o cambios empresariales ejecutados | **0** |

La coincidencia textual exacta no demuestra que la acción se realizara ni resolviera la incidencia.

## Prueba independiente: lote 5

Otros 100 expedientes de mayo de 2026, distintos a los 400 anteriores. En 43 de ellos hay antecedentes estructurados del mismo módulo. Los diagnósticos Qwen 3.5 9B se generan sin enseñar al modelo la solución del propio incidente. Para esos 43 se realizó una comparación pareada de los planes: módulo sin antecedentes, y módulo con referencias anteriores no concluyentes.

La prueba completa ejecutó 43 pares de Qwen 3.5 9B: 86 diagnósticos. En ambos grupos hubo **36 planes válidos, 6 aclaraciones y 1 rechazo**. El evaluador Qwen 3.5 4B encontró **13 coincidencias específicas candidatas sin pistas y 14 con pistas**; solo una nueva coincidencia estimada, ninguna mejora en cantidad de planes aprobados. Las etiquetas siguen siendo estimaciones, no aciertos certificados.

Además, en los 100 casos del quinto lote había 27 notas con referencias SQL reconocibles y **9 coincidieron exactamente con patrones del corpus anterior**. Esto concuerda con la escasa cobertura del catálogo de referencias exactas.

Para reproducir los 43 pares se conservó un índice experimental privado inmutable (SHA-256 098d8ed10f606fad8af8ba887d751f9c9b8f542fe5e99ce25d9f15255e1a4f87). El índice final depurado (SHA-256 5d552674a140527108a91da6c9be3210de20ba92a51c7c012053be11ab29ffd3) excluye una referencia truncada. Los archivos privados no están en Git.

Se evalúan por separado: cumplimiento del contrato de plan y proximidad a la acción histórica según otro modelo evaluador. Estas calificaciones son provisionales y no se convertirán en precisión histórica certificada sin confirmación independiente del mecanismo exacto.

## Decisión operativa

El catálogo queda disponible como **herramienta optativa de consulta**. Ninguna pista histórica se añade automáticamente al diagnóstico. Se requiere verificación del hecho empresarial actual antes de afirmar su causa.

**Cero reparaciones E2E certificadas, cero alteraciones de registros y cero cierres automáticos.**
