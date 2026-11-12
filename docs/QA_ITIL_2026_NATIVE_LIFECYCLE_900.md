# ELSE-ITIL-SUP — Reconstrucción QA de derivaciones por clave nativa ITIL

**Fecha:** 12 de noviembre de 2026. **Base de integración:** main@e86dca3370511c41779dd2dafb4cd4879db67beb.

## Objetivo

Superar la limitación de notas históricas genéricas o con SQL no ejecutado usando eventos reales del ciclo de vida ITIL. No se habilita atención autónoma, ni se confunde igualdad de claves con una FK declarada.

## Procedencia de las lecturas

Se verificaron los nueve recibos HMAC de las solicitudes de los últimos cien incidentes de enero–septiembre de 2026. Los dos nuevos lectores .NET 8 se ejecutaron en ELSE62 utilizando SIELSEAccesoDatos 3.24.11.27 contra ELSE70/dbITIL_D. No hubo DML.

El primer lector, qa/lifecycle2026/CaseLifecycleRead.cs, volvió a consultar los 900 registros ordenados exactamente por FechaSolicitud DESC y CodigoIncidente DESC. Contrastó los SHA-256 de caso, módulo, empresa y estado contra los nueve recibos originales. Leyó, por igualdad de CodigoIncidente, conteos de tablas de atención, derivación y encuesta. También comprobó, por igualdad de código, los catálogos de módulo y estado.

Mediante metadatos SQL verificó las formas declaradas de las seis claves primarias implicadas. La consulta a sys.foreign_keys encontró **cero FKs declaradas desde las tablas de incidentes examinadas**: la relación certificada aquí es únicamente igualdad de claves observada, no una restricción FK.

El segundo lector, qa/lifecycle2026/DerivationEventsRead.cs, validó el HMAC del primer recibo y recuperó los eventos de derivación, verificando que cada CodigoIncidente pertenece a la cohorte exacta y cada par (CodigoIncidente, NumeroDerivacion) es único. Los 1.155 eventos coincidieron con los conteos por expediente de la primera lectura. Se excluyeron usuarios, motivos, descripciones y valores de otros sistemas.

## Resultados

| Mes 2026 | Incidentes | Eventos de derivación | Casos con múltiples derivaciones |
|---|---:|---:|---:|
| Enero | 100 | 129 | 24 |
| Febrero | 100 | 128 | 24 |
| Marzo | 100 | 137 | 31 |
| Abril | 100 | 117 | 13 |
| Mayo | 100 | 130 | 26 |
| Junio | 100 | 138 | 26 |
| Julio | 100 | 120 | 14 |
| Agosto | 100 | 132 | 32 |
| Septiembre | 100 | 124 | 22 |
| **Total** | **900** | **1.155** | **212** |

Los otros 688 casos tuvieron una derivación. Los 1.155 eventos tenían fecha de creación. Por tipo de derivación, se observaron 900 registros de código 1, 90 de código 2 y 165 de código 3; **sus significados funcionales aún no están certificados**. No se debe traducir automáticamente un código a «escalado», «solucionado» o «cerrado».

Los 900 casos coincidieron por código con los catálogos de módulo y estado. Las consultas a taIncidenteAtencion y taIncidenteEncuesta no encontraron filas para estos 900 casos en esta fotografía QA. Eso no demuestra que no haya habido trabajo técnico en otros sistemas.

El reporte agregado sin identificadores está en data/2026_itil_native_lifecycle_900.json. Los recibos completos y las fechas por caso permanecen privados.

## Herramienta y validación

inspect_itil_lifecycle permite únicamente los modos summary y derivation_events. El expediente, módulo y fecha proceden del contexto del caso, no de parámetros libres de Qwen. summary muestra conteos y coincidencias de catálogos; derivation_events devuelve hasta ocho eventos codificados y declara cuántos otros se omitieron.

VerifiedItILNativeLifecycle exige HMAC válido del recibo de 900 casos, del recibo de los 1.155 eventos y de los nueve recibos mensuales, además de código fuente y enlace de identidad exactos. verify_lifecycle_field_claim exige caso, módulo, fecha, fuente, campo, valor y hash exactos. Un valor distinto se bloquea.

El agente puede registrar evidencia de igualdad de claves y fecha de lectura QA, pero mantiene causal_diagnosis_confirmed=false, domain_business_state_verified=false, can_claim_resolved=false y can_execute_mutations=false. Una derivación no prueba corrección de una cobranza, OT o suministro.

La consulta por CLI es qa-itil-lifecycle; requiere variables privadas TIC_QA_ITIL_LIFECYCLE_ROOT, TIC_QA_MONTHEND_ROOT y TIC_QA_RECEIPT_SIGNING_KEY. La CLI solo abre recibos firmados en el servidor autorizado, nunca ejecuta SQL libre.

## Límites y próximos requisitos

La igualdad CodigoIncidente entre tablas ITIL sí permite reconstruir una secuencia de derivaciones observada. **No demuestra un FK SQL declarado, relación entre ITIL y tablas de Distribución, causa empresarial ni reparación**. Antes de dar por solucionado un ticket hacen falta contrato de aplicación confirmado, lectura del objeto empresarial exacto y comprobación funcional/temporal independiente.

Se probaron ataques sobre HMAC, datos de eventos cruzados entre casos, FK falsa, fecha, módulo, tabla y valores alterados. Ninguno puede promocionarse a reparación certificada.

**Cero modificaciones empresariales, cero causas o reparaciones E2E certificadas y cero despliegues automáticos del servicio persistente.**
