# ELSE-ITIL-SUP — grafo empresarial retrospectivo de los 1.621 incidentes de junio

**Fecha QA:** 13 de noviembre de 2026. **Origen:** ELSE70/dbITIL_D/dbo.taIncidente mediante ELSE62 y SIELSEAccesoDatos. **Alcance:** mes completo de junio 2026, no la anterior submuestra de 57 casos elegida por notas de solución. Todos los lectores y verificadores solo realizan SELECT en las bases empresariales.

## 1. Mejoras frente al índice anterior de 57

El experimento de 57 expedientes había seleccionado su categoría OT/cobranza retrospectivamente, tras observar coincidencias documentales con notas de solución históricas. Su cobertura 55/57 no podía usarse para medir cómo identificar un ticket completamente nuevo.

En el nuevo estudio se consultaron las 1.621 solicitudes ITIL originales. El lector seleccionó DescripcionSolicitud, CodigoIncidente, FechaSolicitud, CodigoModulo, CodigoServicio, CodigoEmpresa y CodigoSucursal, y **no seleccionó DescripcionSolucion**. Cada incidente y su solicitud se verificaron por SHA256 contra la fuente original congelada y firmada HMAC.

Se extrajeron valores de 19 dígitos representables en bigint del texto de la solicitud, no de los bloques del campo RT. Cada valor se comparó, sin etiqueta histórica previa, con las PK empresariales CodigoOrdenTrabajo y CodigoCobranza en tablas permitidas de 13 bases SQL QA. Fueron 168 consultas parametrizadas, 0 errores de consulta y 0 escrituras.

## 2. Cifras y denominadores exactos

| Medida | Resultado |
|---|---:|
| Incidentes originales examinados | **1.621** |
| Candidatos numéricos distintos por expediente | 1.342 |
| Candidatos globalmente distintos | 1.125 |
| Casos con alguna PK encontrada antes de verificar sucursal | 446 |
| Coincidencias caso–PK–base, antes de verificar sucursal | 1.813 |
| Observaciones con sucursal distinta del ticket, excluidas | **215** |
| Casos con solo coincidencias de sucursal incorrecta | 113 |
| Casos con al menos una PK y sucursal coincidentes | **333** |
| Observaciones caso–PK–base con sucursal correcta | 1.598 |
| Observaciones duplicadas de copias, colapsadas | 107 |
| Relaciones lógicas incidente–PK tras deduplicar | **1.491** |
| Claves empresariales distintas por tipo | **1.236** |
| Casos con una sola PK lógica coincidente | 158 |
| Casos con varias PK lógicas coincidentes | 175 |
| Casos sin PK coincidente con sucursal correcta | 1.288 |
| Casos con coincidencias tanto de OT como de cobranza | **107** |
| Claves compartidas entre múltiples tickets | 232 |
| Membresías repetidas adicionales entre tickets | 255 |
| Máximo de tickets que comparten la misma PK | 5 |
| Claves compartidas por distintos módulos ITIL | **10** |

**Interpretación:** las 1.813 coincidencias iniciales no son 1.813 relaciones aprobadas. Se excluyeron 215 por sucursal errónea, luego se consolidaron 107 observaciones de la misma PK en distintas bases, resultando 1.491 relaciones lógicas de 333 incidentes con 1.236 PK distintas.

Los 1.288 expedientes sin coincidencia bajo estas condiciones **no demuestran ausencia de objetos empresariales**. Muchos pueden utilizar formatos numéricos diferentes, referencias de otra naturaleza o sistemas fuera del alcance consultado.

Los **107 casos que mencionan identificadores correspondientes a OT y a cobranza** requieren interpretación funcional, sin inferir cuál categoría o PK es la principal. Las 232 PK repetidas entre tickets y las 10 compartidas por módulos diferentes tampoco constituyen causa compartida.

## 3. Identidad, fuente y temporalidad

Cada enlace lógico del grafo reúne: SHA de ticket, módulo, SHA de la solicitud original, tipo de objeto, PK empresariales, sucursal idéntica y una o varias bases QA donde apareció la misma PK. El identificador se agrupa por tipo + valor dentro de cada expediente, sin contar las copias como objetos adicionales.

**Observación decisiva:** la consulta SQL que encontró estas PK se ejecutó en noviembre de 2026. No acredita el estado empresarial en junio, la existencia de la fila en el momento de apertura del ticket, la autoridad transaccional de Gerencial ni la ejecución de una reparación. Los resultados declaran expresamente que el estado histórico, la FK oficial y la causalidad no están certificados.

Los handles expuestos al especialista son HMAC con clave privada y alcance de ticket + módulo + tipo + PK, sin identificadores de negocio en claro. No conceden facultades de escritura ni lectura libre.

## 4. Acceso controlado por el operador

La herramienta nueva se llama inspect_june_full_qa_business_graph. Admite vistas summary, objects y overlaps. El modo overlaps revela únicamente cantidades de claves compartidas y módulos involucrados, sin identidades de otros tickets.

El agente solo puede utilizarla cuando el operador establece ambas variables de entorno:

- TIC_QA_JUNE1621_RETROSPECTIVE_OPERATOR_ENABLED = 1
- TIC_QA_JUNE1621_OPERATOR_CASE_SCOPE_SHA256 = el SHA exacto del caso autorizado

No basta un argumento del LLM o del texto del ticket. Además se necesitan los recibos HMAC privados, el caso y módulo correctos, una fecha de junio válida no anterior a la apertura, y un permiso real para consultar el entorno QA. La CLI qa-june-full-business-graph requiere explícitamente el indicador --retrospective-qa. La ausencia del indicador bloquea la consulta.

La fecha as_of comprueba el alcance temporal del expediente, pero **no convierte la lectura de noviembre en una observación histórica de junio**. Esta herramienta no debe alimentar un benchmark histórico ciego como si fuera verdad de la época.

## 5. Artefactos

- qa/june2026_full_link/JuneAllSourceOnlyPkRead.cs: lector SQL .NET8 con verificación de los 1.621 hashes de origen y búsquedas PK tipadas en 13 bases.
- qa/june2026_full_link/build_signed_june1621_links.py: verificación de recibos fuente, filtrado por sucursal, deduplicación de copias y firma del grafo.
- else_dominance/qa_june_full_source_links.py: consulta de grafo firmada, control de fecha, módulo y caso, y salidas sin PK en claro.
- else_dominance/operational_cli.py y sources.py: acceso operator-only retrospectivo.
- qa/june2026_full_link/private_adversarial_full_graph.py: pruebas adversariales de firmas, casos, PK, rutas, fechas y falsos resultados.
- data/2026_june1621_source_only_link_graph.json: informe público agregado, sin datos personales.

Grafo de evidencia privado (permisos 0600):

    /home/u23u/else_itil_alljune_business_link_20261113/private/june1621_verified_case_graph.private.json

Comprobante HMAC en el mismo directorio, con sufijo .proof.json. Nunca subir a Git los IDs, casos, solicitudes o archivos privados.

### Compatibilidad con la evaluación anterior

Se revalidaron ambos recibos HMAC, el del lector de 57 casos y el nuevo
lector de 1.621 casos. **Los 619 pares expediente–PK–base anteriores
se conservaron exactamente (619/619, pérdida 0)**. La expansión no
eliminó relaciones empresariales ya comprobadas; únicamente añadió
observaciones nuevas y una clasificación de incertidumbre más estricta.

Verificación: qa/june2026_full_link/verify_old57_nonregression.py.

## 6. Pendientes

Falta validar con contratos corporativos la relación funcional entre ticket y negocio, decidir la autoridad de cada tabla, identificar correctamente qué objetos de un lote necesitan intervención y reconstruir estados anteriores/posteriores. Cero reparaciones y cero FK oficiales quedaron certificadas.

**Conclusión:** el registro creció a todo junio sin utilizar notas históricas para clasificar objetos y ahora impide sobrecontar copias, aceptar sucursales incorrectas o convertir coincidencias de tipos distintos en relaciones causales. Es una mejora de trazabilidad, no una autorización para modificar SIELSE.
