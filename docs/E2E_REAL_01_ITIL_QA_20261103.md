# ELSE-ITIL-SUP — E2E-REAL-01: evidencia ITIL QA → Qwen9B

**Fecha:** 2026-11-03. **Estado:** tres consultas QA y tres diagnósticos condicionados completados. **No hay reparaciones certificadas.**

## Objetivo ejecutado

Se verificó el puente de diagnóstico entre un incidente real de ITIL de 2025, su evidencia vigente en el entorno QA autorizado y el especialista Qwen3.5 9B en el clúster privado. La herramienta SQL y los archivos del incidente permanecen en QA; no se introdujeron credenciales ni textos de tickets en este repositorio.

El procedimiento usa el acceso existente de `SIELSEAccesoDatos` del servidor Windows QA a la base ITIL de QA y **una única consulta parametrizada, predefinida y de lectura**. Se rechazan resultados con más o menos de una fila, servidor/base ajenos a QA, referencias incorrectas o desajustes de fecha, servicio o módulo. El modelo no puede suministrar SQL.

El modelo recibe descripción previamente depurada del archivo privado de entrenamiento 2025, evidencia `E1` de existencia y metadatos consultados directamente en QA, el catálogo de fuentes permitido y una advertencia explícita: el estado del ticket no es evidencia de causa ni de reparación. La solución humana histórica se mantiene fuera de la entrada del modelo.

## Resultados verificados

| Caso real de 2025 | Lectura directa QA | Hipótesis | Acciones condicionadas | Pruebas propuestas de cierre | Gate estructural/seguridad |
|---|---|---:|---:|---:|---|
| Impresión | 1 registro y procedencia confirmada | 3 | 3 | 3 | PASS |
| Conectividad | 1 registro y procedencia confirmada | 3 | 3 | 3 | PASS |
| Aplicación SIELSE | 1 registro y procedencia confirmada | 3 | 3 | 3 | PASS |

**Resumen:** 3/3 referencias de caso distintas; tres lecturas SQL verificadas; tres respuestas de Qwen3.5 9B terminadas; tres controles independientes aceptados como `DIAGNOSTIC_GUIDANCE`; 0 fallos de esquema, 0 hard flags de seguridad, **9 observaciones `ROLE_MAPPING_PENDING`**; 0 modificaciones corporativas, 0 causas raíz confirmadas y 0 reparaciones certificadas.

Se contrastaron identificador, fecha, servicio y módulo con la exportación histórica. **No** se certificó equivalencia exacta del texto íntegro de la solicitud: la exportación estaba redactada y su digest puede diferir del texto original de SQL. Los casos son retrospectivos de 2025: tampoco se observó en vivo el estado de dispositivos, cuentas o aplicaciones afectadas. Se requiere evidencia operativa adicional para confirmar cualquier causa.

## Dónde quedaron las evidencias

Las consultas, entradas, diagnósticos y recibos **privados** se conservan únicamente en el entorno QA, bajo el directorio local protegido `C:\Temp\ELSE_ITIL_E2E_REAL_20261103`. Incluyen una selección auditada por familia, prueba de acceso a base QA y el resultado independiente. Los identificadores de incidentes reales no se publican en GitHub.

La API regular de Especialista V1, `127.0.0.1:18883`, continúa funcionando con el modo `USER_SUBMITTED_ONLY`. Este experimento utilizó un **operador QA autorizado separado**; no significa que se haya habilitado todavía el endpoint de ingesta automática corporativa. La distinción protege las fronteras de origen y permiso.

## Próxima puerta técnica

1. Incorporar el operador de consulta parametrizada como herramienta de solo lectura registrada, con identidad autorizada y recibos verificables; no aceptar como verdaderas simples declaraciones de procedencia enviadas por un usuario o modelo.
2. Consultar fuentes específicas de diagnóstico (red, impresoras, identidad o SIELSE) solo dentro de los permisos del sistema. No ejecutar cambios ni elevar privilegios.
3. Resolver las nueve advertencias de asignación de responsables según la matriz corporativa vigente.
4. Contrastar las hipótesis con observaciones funcionales o validación técnica independiente. **No** convertir sugerencias del modelo o soluciones humanas históricas sin verificar en etiquetas de verdad.
5. Mantener 2026 fuera del nuevo entrenamiento; las cohortes anteriormente expuestas no sirven como examen final nuevo y ciego.

Esta prueba valida **un E2E de lectura y diagnóstico**. No constituye todavía **un E2E de reparación de extremo a extremo**.
