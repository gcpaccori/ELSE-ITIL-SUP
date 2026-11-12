# QA de diez incidentes reales de marzo de 2026

Fecha de la prueba: 12 de noviembre de 2026. Plataforma: ELSE62 Windows QA, ELSE70 SQL Server, elsecluster5 (Qwen 3.5 9B local).

## Cohorte exacta

Lectura real en dbITIL_D.dbo.taIncidente mediante SIELSEAccesoDatos 3.24.11.27, entre 2026-03-01 00:00 (inclusive) y 2026-04-01 00:00 (exclusivo). Criterio: FechaSolicitud ascendente y CodigoIncidente ascendente.

Hay 1 869 registros en marzo. Se recuperaron los primeros diez, todos del 2 de marzo de 2026, entre las 07:30 y las 08:37; ocho pertenecen a empresa 1 y dos a empresa 3. No se consultaron las soluciones históricas ni se modificaron datos.

## Resultados del modelo y del enrutamiento funcional

| Nº | Hora | Empresa | Módulo | Dominio | Contrato del plan |
|---:|---|---:|---|---|---|
| 1 | 07:30 | 1 | 0109200111000 — Facturar | Facturación | PASS |
| 2 | 07:46 | 1 | 2606 — SIELSE instalación/configuración | Software cliente | PASS |
| 3 | 07:51 | 1 | 0109200111000 — Facturar | Facturación | PASS |
| 4 | 08:00 | 3 | 0102100100000 — Digitación de Cobranza | Cobranzas y cajas | PASS |
| 5 | 08:01 | 3 | 0102100100000 — Digitación de Cobranza | Cobranzas y cajas | PASS |
| 6 | 08:18 | 1 | 2507 — MGD trámite documentario | MGD | PASS |
| 7 | 08:20 | 1 | 2507 — MGD trámite documentario | MGD | PASS |
| 8 | 08:24 | 1 | 0203100284000 — Gestión de Deficiencias | Software/carga de archivos | PASS |
| 9 | 08:35 | 1 | 0301100097010 — Encargatura de Gerencia/Área | Identidades/permisos | PASS |
| 10 | 08:37 | 1 | 2701 — SIELSE | Identidades/permisos | PASS |

Primera prueba con enrutamiento por texto: 3 planes pasaron, 6 solicitaron aclaración y 1 fue rechazado.

Segunda prueba, vinculando el código del módulo con el nombre observado en el directorio corporativo: 10 dominios identificados y 10 de 10 planes aprobados por el validador, con un intento de Qwen por caso. El nombre del módulo solo se utilizó para escoger el dominio, no para modificar la solicitud ni inventar una lectura empresarial.

PASS significa que el borrador satisface el contrato determinista de diagnóstico; no significa causa demostrada, reparación ni E2E físico.

## Consultas a fuentes empresariales reales

Se ejecutaron nueve SELECT de solo lectura: ocho fuentes con registros, una vacía y cero consultas bloqueadas.

| Área | Fuentes QA | Resultado |
|---|---|---|
| Facturación, empresa 1 | dbComercial001_D: dbo.taFacturacion y dbo.taComprobante | Vacía y con filas |
| Cobranzas, empresa 3 | dbComercial003_D: dbo.taCaja y dbo.taCobranza | Ambas con filas |
| MGD, empresa 1 | dbMGD_D: mgd.taDocumento, mgd.taExpediente y firma.taTrabajadorFirmaMGD | Tres con filas |
| Identidades | dbSeguridad_D: dbo.taUsuario y dbo.taGrupoUsuarioModulo | Ambas con filas |

En los dos casos de software no se reprodujo el error en la aplicación cliente. Las fuentes SQL positivas aún no equivalen a un vínculo verificado entre un caso y su objeto empresarial.

## Evidencia de la ejecución

- SHA-256 del recibo de los diez registros SQL: 7f43487f06326115a8677cde15c58edd33853c969d88f488e059b4467c668275
- SHA-256 del recibo de nueve fuentes SQL: 0727d4870b85543719605c4e057057cc02d3305aaf816b9c0f2626a632329e9f
- Las dos firmas Windows HMAC fueron verificadas de forma independiente en Linux, junto con el código fuente de los lectores.
- Solicitudes, identificadores de incidentes y resultados detallados del modelo se mantienen en el directorio privado /home/u23u/else_itil_march10_qa_20261112/private/.
- Cero cambios empresariales, cero reparaciones certificadas y cero E2E físicos completos.

Los resultados de clasificación y las comprobaciones faltantes permiten continuar las pruebas por objeto exacto (caja/cobranza, documento/firma, usuario/rol, comprobante y pantalla/error), sin confundir disponibilidad de tablas con verificación de incidencias.
