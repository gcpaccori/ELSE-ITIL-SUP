# ELSE-ITIL-SUP — tercera Hand Comercial y auditoría funcional V1 Beta (2026-11-11)

## Objetivo y resultado

Se extendió el circuito de lectura ITIL + Distribución/SAP a una **tercera fuente corporativa distinta**, la base QA ELSE70/dbComercial001_D/dbo.taOrdenTrabajo, accedida mediante SIELSEAccesoDatos y consulta SQL fija parametrizada. No se tocó producción ni se generó SQL a partir del modelo.

- La exploración de solo metadatos confirmó la fuente Comercial y sus campos reales de OT: CodigoOrdenTrabajo, CodigoEstadoOrdenTrabajo, CodigoSubEstadoOrdenTrabajo, CodigoTipoOrdenTrabajo, CodigoSubTipoOrdenTrabajo, FechaRegistroSolicitud, FechaEjecucionInicio y FechaEjecucionFin.
- El lector Comercial V2 ejecutó **5 nuevas consultas** parametrizadas para los cinco incidentes de agosto con una OT textual única, conservando los identificadores en privado. **0/5** encontró una coincidencia en dbo.taOrdenTrabajo de esa base, lo cual solo describe el alcance consultado.
- Se entregaron cinco recibos HMAC con SHA del código fuente y cinco verificaciones independientes mediante **Hand O5 + Guardian O13 + O15**. Los cinco casos revalidaron además las dos Hands ya existentes de Distribución y SAP: **15/15 verificaciones de Hands** sobre cinco incidentes, aunque únicamente las cinco lecturas comerciales son nuevas en esta entrega.
- En el primer pase de Qwen9B, **5/5** respuestas pasaron un contrato demasiado permisivo; **tres copiaron frases de plantilla**. Ese resultado fue detectado en inspección y **no se considera calidad funcional certificada**.
- El contrato V3.1 impide copiar los ejemplos genéricos y exige observables y acciones discriminantes con longitud mínima. En una **segunda generación independiente**: **4/5** planes superaron el contrato endurecido y **1/5** quedó bloqueado por un destino de comprobación no autorizado. Los cuatro aún necesitan evaluación técnica humana; su aceptación **no implica causa raíz correcta**.
- No se validó una unión empresarial oficial ITIL–OT, tampoco inexistencia global de órdenes, resolución funcional ni reparaciones.

## Fronteras de confianza y correcciones

- qa/AugCommercialOtRead.cs: lector .NET 8 fijo; SHA-256 ejecutado **e2e8899dce02a849e91f22fba8cdae9d1617613e4368e4372d8554a3a556fcad**. Compiló en ELSE62 con **0 errores / 0 advertencias**.
- commercial_ot_verified.py: verifica esquema, caso/OT, job, SHA del lector, HMAC, target Comercial, fila y fechas; publica recibos exactos al directorio QA privado.
- commercial_ot_o5_hand.py y commercial_ot_o5_verifier.py: nueva capability, evaluador independiente, O1 desde código exacto, y prohibición de mutación/causa certificada/relación empresarial ficticia.
- Se detectó que el archivo qa/AugOperationalOtRead.cs versionado omitía un salto de línea final presente en el archivo C# ejecutado y firmado en Windows. Se restauraron exactamente los bytes originales: SHA-256 **b6453fee7d6fa8bc4b953b3167074dc6fa6b15cccefd74ae93c740e37288eb00**. No hubo cambio semántico del lector.
- Las fechas DateTime.UtcNow.ToString("O") de .NET usan fracciones de siete dígitos, incompatibles con datetime.fromisoformat del Python 3.9 del worker. Se corrigió **solo el parsing para comparar tiempos**, conservando intacto el recibo firmado. Con ambos ajustes, las tres verificaciones O5/O13/O15 pasan para los cinco incidentes.
- functional_live_triple_v3_1.py devuelve diagnóstico condicional con tres contextos certificados, sin ejecutar otras consultas ni declarar reparaciones. Las salidas rechazadas no se promueven como planes.
- tools/qa_v1beta_three_hand_audit.py reproduce la validación de los cinco casos y de sus respuestas selladas, sin repetir inferencia, SQL o acceso a soluciones históricas.

## Evidencias y alcance

Artefactos privados de QA (no copiar al repositorio):
- Windows: C:\Temp\ELSE_ITIL_COMMERCIAL_OT_QA_20261111\
- Clúster: /home/u23u/else_itil_comm_ot_qa_20261111/outbox_v2/, commercial_verified/, triple_v3_1_diagnostics/.

Resultado del replay completo: 5/5 casos con tres Hands nativas verificadas; 4 diagnósticos contractualmente aceptados, 1 bloqueado; seal manifest SHA-256 03b0b54f2c70c0dc62fc1ffd44ea6207de2da7be1bb25e83760a7d3c34e71856.

Lo no demostrado: relación empresarial ITIL–OT, existencia o inexistencia general de la OT, precisión diagnóstica, estados reales de otras aplicaciones o cierre de incidentes. El siguiente aporte funcional requerirá una fuente autorizada para **clasificar y recuperar el identificador de negocio de origen** (por ejemplo solicitud, suministro, instalación u OT) antes de decidir qué lectura de estado corresponde.

Estado: candidato QA para auditoría; no fusionado ni desplegado en servicio productivo.
