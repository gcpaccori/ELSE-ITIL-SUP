# ELSE-ITIL-SUP: vínculo de evidencia incidente ITIL a objeto empresarial

**Auditoría:** 12 de noviembre de 2026. **Ámbito:** 57 incidentes de junio, 22 órdenes de trabajo y 35 cobranzas, seleccionados retrospectivamente entre las 72 coincidencias documentales de mayo a junio. **Datos:** ELSE62/ELSE70 QA. **Permisos:** solo lectura.

## 1. Relación nativa buscada

Se consultaron cuatro catálogos de SQL Server, entre ellos sys.tables, sys.columns, sys.foreign_keys y sys.foreign_key_columns. Se revisaron 14 bases autorizadas (ITIL y 13 fuentes empresariales), sin errores.

**Hallazgos:** cero tablas con columnas exactas CodigoIncidente y CodigoOrdenTrabajo o CodigoCobranza coexistentes; cero claves foráneas declaradas en la base ITIL hacia o desde taIncidente. CodigoIncidenteOperativo de Fiscalización designa otra clase de incidente, no el ticket de mesa de ayuda.

Esto **no excluye contratos de aplicación, API, otros campos o sistemas externos**. No hay fundamento para afirmar que existe una FK nativa ITIL–OT o ITIL–cobranza. En SQL Server las FK declaradas no atraviesan bases de datos, por lo que la integración interbase requiere un contrato de aplicación o una tabla de enlace autorizada.

## 2. Vínculos positivos establecidos

Se creó un registro privado HMAC-SHA256 que liga cada expediente con las PK encontradas previamente en SQL QA. La identidad de origen es el SHA del ticket, módulo, SHA del texto ITIL original y sucursal; cada destino conserva categoría, columna PK, ID privado, base, sucursal, handle y comprobante de coincidencia.

| Resultado | Cantidad |
|---|---:|
| Incidentes del universo fijo | 57 |
| Incidentes con una PK del tipo esperado | **13** |
| Incidentes con varias PK del tipo esperado | **42** |
| Incidentes sin PK del tipo esperado | **2** |
| Relaciones expediente–PK | **619** |
| Identificadores empresariales distintos | **525** |
| Claves repetidas entre tickets | 87 |
| Membresías adicionales repetidas | 94 |
| FK nativas certificadas | **0** |
| Reparaciones empresariales certificadas | **0** |

Desglose de las 619: 489 CodigoCobranza en dbComercial001_Diario, 127 CodigoOrdenTrabajo en dbGerencial_D y tres OT en dbDistribucion_D. Las sucursales empresariales coincidieron con ITIL en los 619 casos relacionados. Son **observaciones de existencia/igualdad de PK**, no pruebas de que la base Gerencial sea autoridad transaccional ni de una modificación ocurrida durante junio.

La categoría OT/cobranza ya se conocía por una selección retrospectiva que usó históricos; esto **no es una prueba ciega de clasificación de tickets nuevos**. La extracción de los números y su búsqueda empresarial, en cambio, se realizó desde las solicitudes originales, sin consultar las soluciones.

## 3. Modelo de vinculación

Cada fila del registro privado representa un arco comprobado:

incidente ITIL firmado + módulo + solicitud original
→ referencia numérica de 19 dígitos
→ clave primaria empresarial del tipo esperado
→ misma sucursal
→ base QA específica + recibo firmado.

Los arcos son muchos-a-muchos. Un ticket con 42 referencias no genera automáticamente 42 reparaciones ni 42 incidencias diferentes. Una PK compartida entre varios tickets no se interpreta como vínculo causal.

El estado de cada incidente se expresa como:

- SINGLE_QA_PK_MATCH: una PK observada; relación funcional y reparación aún no certificadas.
- MULTIPLE_QA_PK_MATCHES_PRIMARY_UNDETERMINED: varias PK, sin elegir arbitrariamente un objeto principal.
- UNRESOLVED: no hay PK del tipo esperado dentro de las fuentes examinadas.
- BLOCKED: caso, módulo, mes, vista o firma no autorizados.

Para los dos expedientes no resueltos, se mantiene la abstención; una coincidencia de cobranza con otra sucursal no se convierte en una OT.

## 4. Artefacto privado, API y permisos

Registro real (contiene los IDs completos):
/home/u23u/else_itil_ticket_object_link_20261112/private/verified_ticket_business_links.private.json

Firma HMAC:
/home/u23u/else_itil_ticket_object_link_20261112/private/verified_ticket_business_links.private.json.proof.json

Se publica únicamente el agregado sin PII en data/2026_june57_verified_ticket_business_links.json. El registro se reconstruye y verifica contra los recibos originales, el lector SQL de metadatos y el SHA del código. Si un vínculo o su firma difiere, el cargador falla.

La herramienta inspect_itil_business_links admite únicamente view=summary o view=objects con contexto exacto case_sha256, module_code y as_of de junio de 2026. La segunda opción devuelve handles opacos, categoría, origen y hashes; nunca la PK privada.

La CLI qa-itil-business-links ofrece la misma lectura controlada con rutas privadas configuradas por el operador. Un método interno resolve_for_authorized_reader traduce el handle a la PK **solo para un conector de lectura autorizado y del mismo expediente**. No es una herramienta expuesta al LLM, ni ejecuta SQL, ni concede permisos de escritura.

La versión activa del servicio persistente no se altera automáticamente por la fusión del código de Git.

## 5. Qué faltaría para formalizar una relación oficial

- Contrato de negocio que demuestre por qué un objeto se vincula con el incidente y cuál es el objeto o lote relevante.
- Contrato de integración aprobado, autoridad de base y reglas de empresa/sucursal en el momento de la solicitud.
- Migración de esquema o API oficial si se quiere una FK lógica persistente en SIELSE, con permisos, versionado, pruebas y auditoría.
- Evidencia temporal de antes/después, postcondición y autorización del técnico antes de certificar reparación.

No se propone crear directamente una nueva tabla productiva con datos inferidos.

## 6. Código y pruebas

- qa/june2026_link/JuneITILNativeLinkSchemaRead.cs: catálogos de 14 bases, firma y cero escrituras.
- qa/june2026_link/build_verified_ticket_links.py: constructor de 57 incidentes y 619 relaciones privado, con firma HMAC.
- else_dominance/qa_ticket_business_links.py: verificación criptográfica y control de alcance.
- else_dominance/sources.py, agent.py y operational_cli.py: integración de la herramienta y la CLI.
- qa/june2026_link/private_adversarial_ticket_links.py: ataques con firmas manipuladas, cruce de casos, módulo erróneo, falsas FK, reparaciones ficticias y objetos principales inventados.
- tests/test_june2026_ticket_business_links.py: regresión pública de cardinalidad y de límites de evidencia.

**Resultado:** se ha establecido una vinculación operacional comprobable a nivel de PK, caso y sucursal para 55 de 57 expedientes, con 619 relaciones verificadas. No se ha establecido aún una FK corporativa oficial ni la causalidad o reparación histórica.
