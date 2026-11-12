# ELSE-ITIL-SUP — Recuperación de objetos históricos de junio en QA

**Corte:** 12 de noviembre de 2026. **Baseline:** main@bd66536dd89f629193b5cbb7708b78f94e1f292c. **Infraestructura:** Windows ELSE62 QA, SQL ELSE70, SIELSEAccesoDatos 3.24.11.27. **Alcance:** los mismos cinco casos firmados de junio, sin operaciones modificadoras ni restauraciones.

## Causa de los registros anteriormente «no encontrados»

La primera auditoría buscaba los objetos empresariales únicamente en dbComercial001_D, porque la fila ITIL declaraba CodigoEmpresa=1. Ese supuesto fue incorrecto: el código de empresa del incidente ITIL **no certifica la empresa comercial/sucursal del objeto al que se refiere**.

Se ejecutó una segunda búsqueda por identificadores originales firmados en **13 bases permitidas del mismo servidor QA**, con SELECT fijo, parámetros tipados, sin SQL de las notas y sin divulgar los IDs. Se recuperaron tres órdenes de trabajo en otras fuentes.

Para certificar la ruta de aplicación, un lector independiente interrogó el factory SIELSEAccesoDatos eSistema.Comercial:

| Código de empresa | Base devuelta y comprobada mediante DB_NAME() |
|---|---|
| 1 | dbComercial001_D |
| 4 | dbComercial004_D |
| 100 | dbComercial100_D |

Las tres rutas y respuestas SQL quedaron firmadas HMAC. Son rutas **actuales** de la factoría corporativa de QA; no constituyen una FK de ITIL con la orden ni certifican qué contexto tenía la ejecución original de junio.

## Los cinco casos: hallazgos de búsqueda

| Objeto del ticket | Hallazgo en QA | Evidencia y limitación |
|---|---|---|
| OT, cambio de centro de atención | Fila en dbComercial100_D, sucursal 100, y en dbGerencial_D | **Dos estados divergentes**: centro actual 12 en base comercial y 11 en gerencial. La nota histórica menciona 11; ninguna auditoría certifica su ejecución en junio. |
| OT, cambio de medidor | Fila en dbComercial004_D, sucursal 4, y gerencial | Estado y subtipo actuales compatibles entre copias, pero no se verificó el pliego tarifario ni una reparación. |
| OT, retorno a estado inicial | Fila en dbGerencial_D, ausente de las bases comerciales autorizadas comprobadas | **Solo Gerencial**: no puede declararse una fuente transaccional de escritura verificada. |
| Padrón, corrección de apellido | El DNI figura solo en la nota histórica, no en la solicitud legible. Devolvió múltiples coincidencias en distintas bases. | **Ambigüedad de identidad**. No existe un vínculo oficial de esa persona con el ticket. |
| Campaña de supervisión | Código no encontrado en las 13 bases; dbGerencial_D no dispone de la tabla específica. | **No localizado en el ámbito comprobado**; no significa necesariamente inexistencia en producción o históricos externos. |

En total: **5 casos investigados, 3 con una fila de OT en al menos una base, 2 con ruta transaccional actual de empresa verificada y 1 únicamente gerencial**. Hay **una divergencia entre copias**. Los otros dos casos no se pueden emparejar con un único objeto empresarial.

El centro de atención 12 de la OT en dbComercial100_D presenta modificación de fila en junio de 2026; la copia gerencial con centro 11 presenta modificación de fila en octubre. No se puede derivar un cambio de valor concreto de la sola marca de modificación.

## Por qué no se puede reconstruir el «antes y después» todavía

Cuatro bases relevantes de ELSE70 (dbComercial001_D, dbComercial004_D, dbComercial100_D y dbGerencial_D) aparecen ONLINE, con is_cdc_enabled=false a la fecha de consulta. No aparecieron entradas de backups con finalización en junio de 2026 para estas cuatro bases dentro del catálogo msdb.dbo.backupset de ELSE70.

Esto **no prueba** que nunca hubo CDC, que las copias de seguridad no existen fuera de este servidor, ni que no haya respaldos/archivos de aplicación. Las tablas de negocio principales no tienen versionado temporal SQL Server en el esquema inspeccionado. Las tablas de auditoría de OT consultadas tampoco devolvieron transiciones de esos objetos.

La pérdida de la fila en una base transaccional no significa que el dato nunca existió. Tampoco una fila actual de la base gerencial acredita que el técnico aplicó la sentencia SQL que escribió en el histórico.

## Desarrollo entregado al especialista

Se agregó VerifiedJuneBusinessRoute con **cinco recibos firmados y encadenados**: selección exacta del caso, búsqueda en 13 bases, detalles de registros recuperados, rutas de empresa verificadas y disponibilidad de metadatos históricos. Valida SHA del código lector, HMAC, pertenencia a los cinco incidentes y contradicciones entre las fuentes.

Herramienta inspect_june_business_route, en tres vistas controladas:

- route: indica la ruta empresarial candidata cuando el identificador viene de la solicitud y CodigoSucursal concuerda con la ruta oficial de la factoría.
- state: solo los campos no personales observados en QA al momento de la lectura, más discrepancias con Gerencial. No los presenta como estados históricos de junio.
- audit: existencia o falta de eventos firmados consultados, sin inventar cambios.

La herramienta recibe la identidad de caso, módulo y fecha únicamente del contexto autorizado. No permite SQL libre, reemplazo del código de empresa, mezcla de casos ni ejecución de mutaciones. Incluye la CLI qa-june-business-route sobre recibos privados ya verificados.

Estados fail-closed disponibles: ROUTED_ROW_WITH_GERENCIAL_DIVERGENCE, ROUTED_ROW_FOUND_CAUSALITY_UNVERIFIED, GERENCIAL_ONLY_NO_ROUTED_TRANSACTIONAL_ROW, PERSONAL_IDENTIFIER_NOTE_ONLY_AMBIGUOUS y CAMPAIGN_NOT_FOUND_IN_13_ALLOWLISTED_QA_DATABASES.

Las cinco ramas conservan diagnóstico causal no certificado, relación ITIL-negocio no certificada, reparación no certificada y 0 escrituras.

## Reproducibilidad, privacidad y orientación

Lectores .NET8: JuneCrossDatabaseFind.cs, JuneRecoveredObjectsRead.cs, JuneCommercialCompanyRouteRead.cs y JuneHistoricalAvailabilityRead.cs, bajo qa/june2026_rootcause. Todos usan SELECT predefinido y rutas en allowlist. Los nombres de clientes y el apellido de la nota histórica **no se consultan ni se guardan** en los nuevos lectores.

Herramientas: qa/june2026_rootcause/evaluate_signed_crossdb.py y verify_private_crossdb_adversarial.py. Informe público agregado: data/2026_june5_business_crossdb_recovered.json, sin tickets, DNI, personas, identificadores de objeto ni datos crudos.

La comprobación adversarial privada bloqueó **11 intentos** de alterar HMAC o volver a firmar rutas falsas, filas inventadas, auditorías y metadatos históricos, más **3 pruebas de acceso cruzado a caso, módulo o mes**.

El orden de investigación recomendado queda fijado como: caso ITIL firmado → identificador original corroborado → identificar rutas comerciales elegibles → buscar en bases autorizadas → validar fila única y CodigoSucursal → cotejar Gerencial sin asumir que es fuente transaccional → exigir evidencia temporal para inferir cambio → ABSTAIN si falta.

Para una reconstrucción histórica verificable se requiere una instantánea de negocio de junio, o backups/CDC/auditoría de aplicación conservados en otro sistema, con identificador exacto, valor anterior, valor posterior, fecha y operación certificables.

La siguiente ampliación lógica es repetir este método sobre los 22 casos de OT y 35 referencias de cobranza del corte documental de junio. **Esta PR solamente realiza nuevas lecturas empresariales para los cinco casos originales.**

**Conclusión certificada:** causa de enrutamiento incorrecto parcialmente resuelta, tres órdenes recuperadas, dos con ruta comercial actual verificada, una solo en Gerencial. No hay una modificación histórica de negocio ejecutada ni una reparación empresarial acreditada.
