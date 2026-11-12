# ELSE-ITIL-SUP — Recuperación de claves desde solicitudes originales de junio

**Corte QA:** 12 de noviembre de 2026. **Origen:** ELSE70/dbITIL_D/dbo.taIncidente, consultado mediante SIELSEAccesoDatos 3.24.11.27 desde ELSE62. **Alcance:** 57 incidentes de junio previamente seleccionados por coincidencias documentales con 500 antecedentes de mayo: 22 OT y 35 cobranzas. Solo lectura.

## Hallazgo principal

El corpus anonimizado había reemplazado numerosas referencias por el marcador [NUMERO]. Eso impedía resolver claves desde la versión anonimizada, **pero no significa que faltasen en la solicitud original**.

Un lector Windows QA recuperó y verificó 57 descripciones originales por SHA-256, comparando además la versión enriquecida DescripcionSolicitudRT para estudiar etiquetas. El lector que hace la recuperación masiva solo utiliza DescripcionSolicitud: algunas versiones RT contienen bloques enormes de números correspondientes al formato enriquecido que podrían generar falsos positivos. **DescripcionSolucion nunca se selecciona en los lectores de identificación**.

Se extrajeron valores de 19 dígitos válidos para bigint, y se buscaron como posibles claves CodigoOrdenTrabajo o CodigoCobranza mediante 43 consultas SELECT tipadas en 13 bases permitidas. El código de sucursal de cada fila encontrada se cotejó con la sucursal de ITIL.

| Evidencia | Resultado |
|---|---:|
| Casos de junio auditados | 57 |
| Candidatos distintos por relación expediente–número | 620 |
| Relaciones expediente–PK coincidentes con una base QA | **619** |
| Claves de negocio globalmente distintas | **525** |
| Casos con al menos una coincidencia empresarial | **55/57** |
| Casos sin coincidencia PK del tipo esperado | 2 |
| Claves repetidas en más de un ticket | 87 |
| Membresías repetidas adicionales | 94 |
| Casos recuperados adicionalmente frente a extracción estricta anterior | **52** |
| Cambios históricos o reparaciones certificados | **0** |

El total de 619 es un recuento de **relaciones expediente–PK**, no de 619 claves globalmente distintas ni de reparaciones. Cada incidente puede enumerar varias órdenes o cobranzas; un mismo ID puede repetirse en varios incidentes.

## Rutas donde aparecieron los ID de origen

| Tabla/campo PK | Base SQL QA | Relaciones |
|---|---|---:|
| taCobranza.CodigoCobranza | dbComercial001_Diario | **489** |
| taOrdenTrabajo.CodigoOrdenTrabajo | dbGerencial_D | **127** |
| taOrdenTrabajo.CodigoOrdenTrabajo | dbDistribucion_D | **3** |
| Total | | **619** |

Las 619 coincidencias empresariales presentaron sucursal coincidente con el expediente ITIL. Es una vinculación de valor, tipo y sucursal, **no una FK oficial ITIL–objeto**, y tampoco prueba que la base Gerencial sea autoridad de escritura ni que el cambio haya ocurrido en junio.

## Los dos expedientes pendientes

- Una solicitud OT contiene un candidato de 19 dígitos que no aparece como PK de OT en las fuentes verificadas. Una revisión alternativa lo identifica como CodigoCobranza en Comercial001_Diario, con sucursal diferente: **se rechaza como identificación de OT**.
- Otra solicitud OT carece de candidato de 19 dígitos y no arrojó coincidencias del tipo esperado en la búsqueda de números de 9 a 19 dígitos.

La búsqueda complementaria ejecutó 102 consultas SELECT. No se asignó un objeto ficticio a ninguno de los dos casos.

## Dónde están los identificadores reales

Se conservaron solo en el entorno autorizado, no en GitHub, con permisos restringidos:

- /home/u23u/else_itil_june57_identifier_recovery_20261112/private/june57_verified_primary_keys.private.csv — contiene las 619 relaciones con PK real, categoría, base, sucursal, SHA del ticket y clasificación de evidencia; no nombres de clientes.
- /home/u23u/else_itil_june57_identifier_recovery_20261112/private/june57_verified_primary_keys.private.csv.proof.json — comprobante HMAC-SHA256 de la exportación.
- /home/u23u/else_itil_june57_identifier_recovery_20261112/private/june57_bulk_pk_request_matches.private.json — recibo original firmado de SQL Windows, con los identificadores que efectivamente devolvió la base empresarial.
- Los recibos privados complementarios están en ese mismo directorio.

El CSV debe permanecer en el entorno QA privado. Los reportes públicos del repositorio solo incluyen agregados y hashes de recibos, nunca los IDs, notas o datos personales.

## Componentes desarrollados

- qa/june2026_identity/June57RequestIdentifiersRead.cs: explora solicitudes originales y RT, comprueba SHA de cada incidente y solo extrae candidatos acotados a etiquetas.
- qa/june2026_identity/June57BulkPrimaryKeyMatch.cs: lector de 19 dígitos de texto original; compara con PK reales en 13 bases autorizadas, con parámetros SQL bigint.
- qa/june2026_identity/June57ResidualRelationRead.cs: examina solo los dos casos pendientes mediante claves alternativas, sin mutaciones.
- qa/june2026_identity/score_request_pk_recovery.py: valida los HMAC y hashes entre los 57 expedientes, las fuentes anteriores, las PK y sus sucursales; publica únicamente resultados agregados.
- qa/june2026_identity/export_private_recovered_pk.py: crea un CSV privado de permisos 0600 y un recibo HMAC.
- qa/june2026_identity/private_adversarial_source_pks.py: pruebas de alteración de IDs, expediente, sucursal, base, referencia histórica y firma.
- data/2026_june57_original_request_pk_recovery.json: resumen público sin IDs individuales.
- tests/test_june2026_original_request_pk.py: regresión sintética/estructural de privacidad y límites del resultado.

## Alcance de la conclusión

El conjunto de 57 fue elegido **después** de observar los solapamientos documentales de mayo y junio. La categoría OT/cobranza utilizada en las consultas es, por tanto, una etiqueta retrospectiva; **55/57 no es precisión ciega de clasificación de un nuevo ticket**.

Lo comprobado es que los valores numéricos extraídos de la solicitud original coinciden exactamente con las PK de filas empresariales QA y sus sucursales. Aún faltan la relación funcional oficial ticket–objeto, estado anterior/posterior y acreditación de la reparación. Ningún lector ejecutó SQL de las notas históricas ni efectuó escrituras.
