# ELSE-ITIL-SUP — Evidencia de estado QA por expediente, campo y OT reportada

**Corte:** 12 de noviembre de 2026. **Entornos autorizados:** ELSE62 Windows QA; ELSE70 SQL Server QA; elsecluster5 Linux. **Baseline inicial:** main@16c4612321d6b94b501e16ee5bcf1f5f1d6342bd.

## Meta y límite

Separar «un patrón histórico parece aplicable» de «se observó un campo concreto de una fila empresarial», conservando la procedencia, la identidad del caso y el instante de lectura. Un valor observado **no prueba causalidad, ni reparación, ni un vínculo FK con otra aplicación**.

## Lectura física por expediente de ITIL

El lector en qa/case_state/CaseStateRead.cs tomó los diez puestos predeterminados de los últimos cien incidentes de enero a septiembre de 2026: **90 expedientes únicos**. Para cada uno verificó primero los nueve recibos HMAC originales, releyó los cien puestos de cada mes en su orden fijo y realizó un segundo SELECT exacto por CodigoIncidente (parámetro BigInt), con rango de fecha. Rechazó cualquier desviación en el hash de identidad, empresa, módulo, fecha o selección.

Se obtuvieron **90/90 registros exactos** y **720 observaciones de ocho campos** en ELSE70 / dbITIL_D / dbo.taIncidente. Los campos son CodigoEstadoIncidente, CodigoModulo, CodigoEmpresa, CodigoCalificacion, CodigoOrigenIncidente, CodigoServicio y presencia de FechaRespuestaSolucion y FechaCierre.

En la lectura QA, **77** expedientes presentaron FechaCierre y **0** cambiaron su CodigoEstadoIncidente respecto al recibo mensual anterior. Son metadatos ITIL de la fecha de lectura; no son estado de cobranzas, suministros ni OT.

El archivo privado, firmado con HMAC SHA-256, se verifica de nuevo en Python. VerifiedCaseStateIndex exige el SHA del código fuente real y todas las pruebas de origen. La función verify_claim exige expediente, módulo, fecha, campo, valor observado y hash exactos. Una coincidencia incompleta devuelve BLOCKED.

## Lectura física de órdenes de trabajo reportadas

El segundo lector en qa/case_state/ReportedOtDomainRead.cs revisó los **900 expedientes** disponibles. Aceptó únicamente un **único identificador numérico de OT expresamente mencionado** en el texto original del ticket, para empresa 1. No generó SQL a partir de propuestas de un modelo. Consultó de forma parametrizada la fuente ELSE70 / dbDistribucion_D / dbo.taOrdenTrabajo.

| Resultado | Casos |
|---|---:|
| No contienen un identificador OT inequívoco | 841 |
| Identificadores OT ambiguos | 5 |
| Empresa distinta de la fuente QA permitida | 12 |
| **Código OT explícito, consultado** | **42** |
| Exactamente una fila encontrada en la tabla consultada | **9** |
| Consulta sin fila en la tabla consultada | **33** |

Para las **9 órdenes encontradas** se comprobaron **63 valores** en siete campos: CodigoEstadoOrdenTrabajo, CodigoClaseOrdenTrabajo, CodigoTipoOrdenTrabajo, CodigoSubTipoOrdenTrabajo y presencia de FechaElaboracion, FechaInicio y FechaFin.

Cada lectura queda vinculada por hashes al ticket, al código de OT reportado y al recibo firmado de origen. No se publica ningún identificador original ni el texto de usuario.

**Una OT que aparece en el texto de un incidente no constituye una FK ITIL↔OT certificada.** Por eso la lectura puede confirmar un campo en esa fila de Distribución QA, pero **no** confirmar la causa del ticket. Cero filas significa únicamente cero resultados en esa tabla y empresa durante la consulta; nunca ausencia global de la OT.

## Conexión con los planes de Qwen 9B

La validación sobre los 90 expedientes seleccionados utilizó los planes ciegos creados en la evaluación mensual, **sin revelar las soluciones históricas**:

| Indicador | Cantidad |
|---|---:|
| Casos con observaciones ITIL firmadas | 90 |
| Campos ITIL observados y cotejados | 720 |
| Verificaciones de negocio propuestas por el modelo | 135 |
| Verificaciones sin prueba empresarial oficial de relación causal | 135 |
| Causas confirmadas y reparaciones certificadas | **0** |

La nueva herramienta inspect_case_qa_state solo admite un nombre de campo de la lista cerrada y usa el expediente, módulo y fecha del contexto, no un identificador que el LLM pueda sustituir. inspect_reported_ot_qa_state hace lo mismo para los registros de OT inequívocos, siempre con la advertencia de que el vínculo empresarial ITIL↔OT no está demostrado.

El validador de propuestas nunca promociona los recibos a evidencia de causa. Puede registrar la observación limitada de un valor de un campo, pero exige evidencia empresarial específica y verificación independiente antes de cualquier afirmación de solución.

## Pruebas de manipulación y reproducibilidad

Los lectores .NET 8 usan SIELSEAccesoDatos 3.24.11.27, rutas QA concretas, instrucciones SELECT predefinidas, parámetros tipados, límites de filas y HMAC. No aceptan SQL suministrado por el modelo ni ejecutan operaciones DML.

- qa/case_state/verify_real_qa_adversarial.py comprueba HMAC, valor falso, campo arbitrario, caso cruzado, módulo incorrecto, mes diferente y hash de OT alterado con los recibos físicos privados.
- qa/case_state/evaluate_90_case_fields.py produce el informe agregado de los 90 casos sin publicar los valores ni sus SHA individuales.
- qa/case_state/evaluate_900_reported_ot.py reconstruye las 42 lecturas de OT y las 63 observaciones empresariales, verificando de nuevo los recibos originales.

Los archivos privados permanecen en ELSE62 y elsecluster5. Los informes públicos son agregados y no contienen nombres, soluciones, claves, IDs corporativos, códigos OT ni SQL extraído de tickets.

## Resultado y siguiente restricción

La mejora de evidencia por caso quedó implementada y ejecutada físicamente contra **dos bases QA**. La ampliación siguiente requerirá un contrato oficial que relacione un expediente ITIL con el objeto de negocio, en lugar de suponer que el código mencionado en una solicitud constituye esa relación.

**Cero operaciones empresariales modificadoras, cero reparaciones E2E certificadas y cero despliegues automáticos al servicio persistente.**
