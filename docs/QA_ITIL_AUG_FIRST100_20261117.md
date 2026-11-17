# ELSE-ITIL-SUP — Evaluación de los primeros 100 incidentes de agosto de 2026

**Fecha de ejecución:** 17 de noviembre de 2026. **Base:** `main@2198eccf6696a5ecce4d8994d288ae7b982dbb19`. **Período:** agosto de 2026. **Selección reproducible:** `ORDER BY FechaSolicitud ASC, CodigoIncidente ASC`; los primeros 100 de los 1.819 expedientes de la tabla QA `ELSE70/dbITIL_D/dbo.taIncidente`, del 1/8/2026 08:06 al 3/8/2026 15:15.

## 1. Separación de las dos evaluaciones

**Evaluación histórica de diagnóstico:** reutiliza los 100 diagnósticos que Qwen 9B produjo en la campaña de 1.819 casos del 10–11 de noviembre; **el modelo no fue vuelto a ejecutar el día 17**. La evaluación enlaza por SHA original la solicitud ciega, el diagnóstico y el dictamen de Qwen 4B almacenado anteriormente. Los tres archivos se comprobaron íntegros con SHA-256 frente a los manifiestos conservados. La solución del técnico no ingresó a Qwen 9B.

**Evaluación nueva de identidad empresarial:** desarrollé un lector .NET8 que consultó físicamente ELSE62/ELSE70 **hoy 17 de noviembre**, para los primeros 100 casos, contra el registro original de ITIL. Los cien SHA de caso, servicio, módulo, texto original de solicitud y fecha de apertura coincidieron con el exportador de agosto. Se compararon valores de 19 dígitos extraídos de la **solicitud original**, no del histórico de solución, contra las PK de OT/cobranza de 13 bases autorizadas, y se comprobó `CodigoSucursal` de la fila antes de aceptar la relación observacional.

## 2. Los 100 diagnósticos previos de Qwen 9B

| Medida | Casos |
|---|---:|
| Plan válido por contrato estructural | **100/100** |
| Evaluador histórico: relación `SUPPORTED` | **1/100**, juicio del evaluador, no acierto certificado |
| Evaluador histórico: `NOT_DETERMINABLE` | **99/100** |
| Histórico con actuación `ACTIONABLE` según el evaluador | **1/100** |
| Histórico `VAGUE` según el evaluador | **88/100** |
| Histórico `EMPTY` según el evaluador | **11/100** |
| Reparaciones E2E acreditadas | **0/100** |

La cifra 1/100 **no es una precisión histórica del 1 %**: el evaluador no pudo determinar concordancia en 99 casos, sobre todo por la calidad de las notas. Tampoco 100/100 de validez del contrato significa 100 soluciones correctas.

## 3. Nueva búsqueda real de identificadores empresariales

| Medida de la lectura física | Resultado |
|---|---:|
| Expedientes SQL reconfirmados y vinculados al original | 100/100 |
| Bases empresariales de QA inspeccionadas | 13 |
| Lotes SQL de PK parametrizados | 21 |
| Valores candidatos de 19 dígitos por expediente | 90 |
| Valores numéricos distintos globales | 78 |
| Observaciones caso–PK–base | 113 |
| Observaciones con sucursal coincidente | 105 |
| Observaciones con sucursal diferente y rechazadas | 8 |
| Casos con alguna PK observada de su sucursal | **16/100** |
| Casos con una PK lógica de su sucursal | 4 |
| Casos con varias PK lógicas de su sucursal | 12 |
| De esos 16, casos que tienen OT y cobranza | 8 |
| Casos sin número candidato de 19 dígitos | **79** |
| Casos con coincidencias solo en otra sucursal | **5** |
| Casos con candidato pero sin PK en las tablas consultadas | 0 |

**Interpretación:** 113 observaciones no equivalen a 113 objetos ni a 113 reparaciones. Los 16 incidentes constituyen **identificación retrospectiva de PK en noviembre**, no autoridad del objeto en agosto. Entre los 84 sin vínculo de la misma sucursal, 79 no contienen un número del formato explorado y 5 tienen coincidencia de otra sucursal, que no se asignó de manera incorrecta.

## 4. Pruebas y cadena reproducible

- `qa/aug2026_first100/AugFirst100PkRead.cs`: lector de solo lectura en ELSE62, contrato de 100 filas y coincidencia exacta con el snapshot ITIL, consultas `SELECT` parametrizadas a Comercial/Distribución/Gerencial y recibo HMAC.
- `qa/aug2026_first100/verify_windows_private_receipt.py`: verificador independiente en ELSE62 de la firma HMAC, SHA-256 del lector, SHA de PK, pertenencia del caso y sucursal y todos los conteos; **PASS**.
- `qa/aug2026_first100/score_first100_blind_history.py`: enlaza los tres diarios históricos de 1.819 casos, sin acceso a la solución para el modelo, y publica únicamente agregados de los primeros 100.
- `data/2026_aug_first100_business_pk_summary.json` y `data/2026_aug_first100_blind_history_evaluation.json`: resultados públicos libres de identificadores originales y datos personales.
- **Recibo físico Windows:** `716ba5023d947ff0d8f89896aa7b495efe8431691616c234f73b6374ee86a0ae`, con firma comprobada independientemente. Los registros completos y secretos permanecen en `C:\Temp\ELSE_ITIL_AUG_FIRST100_20261117`.

La cadena de consulta no seleccionó `DescripcionSolucion`; no se ejecutaron UPDATE, DELETE ni reparación de OT/cobranza. Las lecturas empresariales se hicieron en noviembre, por tanto no son un «antes/después» histórico del incidente.

## 5. Brecha técnica y siguiente paso

El siguiente salto más útil no es seguir aumentando el porcentaje estructural de planes: **recuperar la identidad correcta a partir de referencias de tipo suministro, solicitud, medidor, reclamo y documento que no cumplen el patrón bigint de 19 dígitos**, y comprobar el contrato propio de cada módulo. En los 12 casos multíobjeto no debe inventarse un objeto principal. Cuando existan relaciones empresariales comprobadas, contrastar el campo y estado exactos contra la actuación histórica y abstenerse cuando las notas no describen un mecanismo verificable.

**Balance:** 100/100 planes estructuralmente válidos de la campaña previa; 16/100 casos con PK de la sucursal corroborada en una lectura nueva; 1 concordancia preliminar de un evaluador histórico; **cero causas o reparaciones empresariales certificadas**. No se actualizó el proceso persistente.
