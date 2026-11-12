# ELSE-ITIL — capacidad de investigación real, ventana 22–31 enero 2026

**Fecha:** 10 de noviembre de 2026. **Origen:** ELSE70 / dbITIL_D / dbo.taIncidente en QA.

## Qué se amplió

Esta iteración **no construye otro clasificador Pareto de tickets**. Amplía el
núcleo ejecutable de investigación de la PR #16 para permitir la lectura
NuGet real de incidencias ITIL de los últimos diez días de enero de 2026.

- Hand O5 registrado separadamente en ELSE CORE PR #362, query exacta
  `ITIL_2026_01_LAST10_CASE_EXACT_READ`; origen/manifest de
  `qa/JanLast10ExactRead.cs`, distinto del Hand septiembre.
- Lector Windows NuGet/.NET 8 de solo lectura que busca un identificador
  mediante SHA-256 dentro de la ventana SQL fija 2026-01-22 inclusivo hasta
  2026-02-01 exclusivo. El export conserva el SHA y no transmite soluciones.
- Dispatch `POST /v1/qa/core/investigate` y
  `GET /v1/qa/core/jobs/{job_id}`; cola independiente SQLite, catálogo
  inmutable de **574 hashes**, trabajador ELSE62 en tarea de un minuto y
  servicio local `18885`.
- Seis observaciones ITIL reutilizables por un mismo Hand: existencia del
  caso, servicio, módulo, clasificación, origen y estado del ticket. Estos
  metadatos **no prueban causas raíz**, permisos efectivos, estado de SAP ni
  una reparación.
- El verificador de finalización compara código fuente exacto, identidad,
  fecha, metadatos, recibos O5/O13/O15 y salida del modelo. Un resultado
  pendiente o rechazado no se cuenta como evidencia obtenida.

## Cohorte, evidencia y resultados

Se auditaron **574 casos únicos** del 22 al 31 de enero (10 días calendario),
usando el snapshot de enero de 1.987 expedientes. La consulta nueva no
incorporó la resolución humana en los prompts. **572** tienen resolución
histórica no vacía; la evaluación retrospectiva considera esas resoluciones
solo después, para describir la calidad de las referencias, no para dirigir
el Hand.

Se realizaron **12 nuevas ejecuciones E2E** distribuidas entre los 10 días
(una por día y dos adicionales disparadas desde la API). Las 12
ejecutaron una consulta NuGet nueva y una nueva evaluación de Qwen 9B.
La auditoría independiente de los 12 expedientes constató:

| Indicador | Resultado |
|---|---:|
| Lecturas SQL nuevas con recibo O5/O13/O15 | **12/12** |
| Recibos alterados rechazados sin ejecutar el Hand | **12/12** |
| Propuestas diagnósticas aceptadas por contrato | **5/12** |
| Derivadas a revisión humana | **7/12** |
| Reparaciones funcionales certificadas | **0** |
| Confirmaciones humanas de causa raíz | **0** |
| Cobertura de ejecución nueva sobre los 574 | **2,09 %** |

La evidencia agregada queda en
`/home/u23u/else_itil_janlast10_qa_20261110/independent_audit_12.json`
y `typed_metadata_audit_12.json`. El informe completo de los 574
registros está en
`C:\Temp\ELSE_ITIL_JANLAST10_DYNAMIC_20261110\evaluation_v2\janlast10_summary.json`;
los datos por caso permanecen privados en ELSE62.

La evaluación histórica previa de los mismos 574 muestra: 573
inferencias Qwen9B completadas; 538 planes con aprobación de vinculación
posterior de fuentes; 283 planes con fuentes añadidas post generación;
280 de esos añadidos también aprobaron la vinculación. **538 no es una
tasa de precisión**, pues agregar fuentes textuales no demuestra su
consulta. El evaluador de referencia Qwen4B emitió 462
`NOT_DETERMINABLE`, 54 `CONFLICT` y 54 `SUPPORTED` entre sus 570
evaluaciones completadas; no son etiquetas humanas de verdad.

## Pruebas y ejecución

- **220 pruebas aprobadas** con ELSE CORE enero integrado.
- **200 PASS, 14 SKIP** en pruebas independientes antes de la última
  prueba añadida (ejecución adicional de esta cohorte; no se confunde
  omisión por dependencias con PASS).
- C# `JanLast10ExactRead.csproj` compiló con 0 errores y 0 advertencias
  en ELSE62.
- Servicio `else-itil-janlast10-preview.service`: ACTIVE (localhost:18885).
- Tarea `ELSE-ITIL-QA-JanLast10-OutboundNuGet`: habilitada, último
  resultado de ejecución consultado = 0.
- El servicio histórico 18883 conserva su configuración y cola anteriores.

**Aún falta:** incorporar otros Hands de evidencia corporativa real,
como órdenes comerciales/OT, SAP y permisos; luego comparar las
hipótesis con verificación de técnicos y pruebas de cierre. No se
declara capacidad de resolver el 80 % de incidentes ni precisión causal.

## Dependencias de integración

1. ELSE CORE PR #360 — Hand NuGet de septiembre.
2. ELSE CORE PR #362 — Hand independiente de enero.
3. ELSE-ITIL PR #16 — núcleo ejecutable y despacho de septiembre.
4. Esta ampliación ELSE-ITIL de enero, apilada sobre #16.

Se mantiene en ramas/PR de revisión, sin fusionar `main`.
