# Recuperacion de las dos pruebas de 50 en ELSE-ITIL-SUP

Fecha: 11 de noviembre de 2026. Consultas SQL QA ejecutadas desde ELSE62 con SIELSEAccesoDatos sobre ELSE70.

## 50 capacidades preventivas y sus 100 indicadores originales

El backtest retrospectivo original termino 50/50 ABSTAIN porque carecia de las dos senales tecnicas de cada capacidad por activo y ventana temporal. Se ha recuperado el contrato de 50 pares originales de indicadores, conservando los nombres del archivo historico results.json: CO (9), EUC (8), ID (8), NET (11), OP (10), SEC (4).

Ejecutamos 50 SELECT TOP(1) sobre cinco bases: ITIL, Seguridad, Administrativo, Distribucion y Comercial; 12 consultas adicionales calcularon estadisticas de columnas reales.

| Evidencia QA | Resultado |
|---|---:|
| Tablas examinadas en SQL real | 50 |
| Tablas con filas | 44 |
| Tablas vacias | 5 |
| Lecturas bloqueadas | 1 |
| Indicadores agregados leidos | 10 de 12 |
| Capacidades con fuentes relacionadas que contienen filas | 34 de 50 |
| Capacidades solo con fuentes vacias o bloqueadas | 2 de 50 |
| Capacidades sin fuentes relacionadas registradas en esta muestra | 14 de 50 |
| Pares originales de senales alineados por activo y tiempo | 0 de 50 |

Hallazgos: 415 asociaciones de equipos CMDB; solo 40 tienen fecha de ultimo monitoreo y ninguna es de 2026. Las cuatro tablas seleccionadas de respaldo estan vacias. Seis mantenimientos de equipo registrados, sin solicitudes del periodo 2026. La tabla de sesiones consultada devolvio denegacion. El periodo ITIL enero-septiembre de 2026 contiene 14 950 incidentes, coincidiendo con el recuento historico.

Estas comprobaciones acreditan fuentes y disponibilidad, NO que la capacidad original estuviera prediciendo fallas. El 50/50 ABSTAIN permanece como resultado predictivo. El recibo de las 50 lecturas esta firmado y fue verificado con HMAC en Linux; SHA-256:
18ab261e88adfb740d5313930215e981b80b9da96106d5b505428b441e2e2a58.

## Campana fisica 22 octubre: dos grupos de 50 requerimientos

Los directorios originales y sus 100 recibos siguen en elsegov/artifacts/itil_night100_20261022. Recuperamos las 50 claves exactas de cada carril desde su manifiesto y ejecutamos 100 consultas parametrizadas por CodigoPeticion bigint en dbITIL_D.dbo.taMantenimientoSoftware.

| Evidencia | Carril A | Carril B |
|---|---:|---:|
| Expedientes consultados | 50 | 50 |
| Filas exactas encontradas en QA | 50 | 50 |
| Modulo del expediente coincide con manifiesto | 50 | 50 |
| Ausentes o bloqueadas | 0 | 0 |
| Fecha pase produccion presente en QA actual | 50 | 50 |
| Fecha de cierre presente en QA actual | 46 | 42 |
| Estado numerico de QA actual | 9 | 9 |
| E2E del codigo producido por campana de octubre certificados | 0 | 0 |

Que el registro empresarial tenga estado 9 y fecha de pase no certifica que el agente de octubre haya compilado ni implantado su codigo. La campana original creo tres Source B y cero certificaciones E2E de negocio.

SHA-256 de los recibos QA nuevos:
- Carril A: 172558d8d2645519f66e6298feca3c5b660c1eeed84e9f082c711d33529eb825
- Carril B: c7246aae5eccbc1b325224d2ccf25d00c2dc85097e9c27699729f2580dcc21dd

## Integracion en Beta

El catalogo Preventive50Catalog registra los 50 identificadores originales, los 100 nombres exactos de senales y las tablas candidatas observadas. La herramienta de investigacion inspect_preventive50_source acepta solo capability_id. Informa de fuentes concretas y falta de senales, sin emitir predicciones ficticias ni modificar negocios.

CLI:
  python -m else_dominance.operational_cli qa-50-coverage
  python -m else_dominance.operational_cli qa-50-coverage --id EUC04

Todos los manifiestos con claves y los lectores Windows se conservan exclusivamente en la carpeta privada /home/u23u/else_itil_db_knowledge_20261111/qa50.

## Avance siguiente

La fuente ITIL para el lote fisico esta recuperada 100/100. Falta enlazar cada codigo de modulo con su fuente, compilar el cambio real en Windows y ejecutar pruebas funcionales. Para las 50 reglas de prevencion, falta telemetria primaria y secundaria real, temporal y asociada al mismo activo.
