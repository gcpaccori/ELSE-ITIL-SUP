# Matriz de las 21 categorías funcionales de ELSE-ITIL-SUP Beta

Base: el enrutador real else_dominance/functional_domain_v2.py del repositorio de soporte.
La matriz es un estudio de cobertura: no integra Hands ni comprueba funcionalidad de Beta.

| Dominio Beta | Fuentes de conocimiento | Clasificación |
|---|---|---|
| COMMERCIAL_OT (SIELSE/órdenes de trabajo) | ORDENES_COMERCIALES, CORTES_RECONEXIONES, DISTRIBUCION_INTERRUPCIONES, FISCALIZACION_OPERATIVA | Mapa de metadatos SQL; faltan reads por caso |
| COMMERCIAL_SCHEDULE (SIELSE/planificación de jornadas) | PLANIFICACION_JORNADAS | Mapa de metadatos SQL; faltan reads por caso |
| COMMERCIAL_BILLING (SIELSE/facturación) | COMPROBANTES_FACTURACION, MEDIDORES_LECTURAS, FACTURACION_ELECTRONICA | Mapa de metadatos SQL; faltan reads por caso |
| COMMERCIAL_MATERIALS (SIELSE/liquidación de materiales) | PRESUPUESTOS_RECURSOS, ADMINISTRACION | Mapa de metadatos SQL; faltan reads por caso |
| COMMERCIAL_CASH (SIELSE/cobranzas y cajas) | COBRANZAS_CAJAS | Mapa de metadatos SQL; faltan reads por caso |
| COMMERCIAL_FISE (SIELSE/FISE-FOSE) | SUBSIDIOS_FISE_FOSE | Mapa de metadatos SQL; faltan reads por caso |
| SAP (SAP/gestión empresarial) | SAP/ERP externo: SQL SIELSE no certifica transacciones SAP | Requiere otras herramientas, no basta SQL |
| IAM (Gestión de identidades y permisos) | ACCESOS_PERMISOS | Mapa de metadatos SQL; faltan reads por caso |
| ENDPOINT_NETWORK (Equipo/conectividad) | Host, DNS, rutas y conectividad: requiere observación de red | Requiere otras herramientas, no basta SQL |
| ENDPOINT_SOFTWARE (Equipo/aplicación cliente) | Equipo y aplicación: requiere inventario/versiones/logs | Requiere otras herramientas, no basta SQL |
| ENDPOINT_PRINT (Impresión/exportación de documentos) | Impresoras, colas, renderizadores y servicios de impresión | Requiere otras herramientas, no basta SQL |
| EMAIL (Correo y transporte SMTP) | SMTP, transporte, cuotas y trazas de correo | Requiere otras herramientas, no basta SQL |
| CONTRACT_VALUATION (SIELSE/valorizaciones y penalidades) | VALORIZACIONES_PENALIDADES, ADMINISTRACION | Mapa de metadatos SQL; faltan reads por caso |
| TELECOM (Telefonía corporativa/SIM) | Telefonía, SIM, inventario del operador y equipo | Requiere otras herramientas, no basta SQL |
| MGD (Gestión documental MGD) | DOCUMENTOS_MGD | Mapa de metadatos SQL; faltan reads por caso |
| HR (Sistema de personal y asistencia) | RRHH_ASISTENCIAS | Mapa de metadatos SQL; faltan reads por caso |
| TAX_REPORTING (Reportes tributarios PLE/SIRE) | FACTURACION_ELECTRONICA, COMPROBANTES_FACTURACION | Mapa de metadatos SQL; faltan reads por caso |
| METER_DATA (Sistema de medidores) | MEDIDORES_LECTURAS | Mapa de metadatos SQL; faltan reads por caso |
| SECURITY_VIDEO (Videovigilancia PTZ) | Cámaras, grabador, red y privilegios de PTZ | Requiere otras herramientas, no basta SQL |
| ITIL_PROCESS (Gestión de tickets ITIL) | GESTION_INCIDENTES_ITIL | Mapa de metadatos SQL; faltan reads por caso |
| UNKNOWN (Sistema sin identificar) | Aún sin sistema identificado: el catálogo SQL no define la causa | Requiere otras herramientas, no basta SQL |

## Criterios previos a integrar

Cada dominio SQL necesita ruta sistema+empresa, tabla/esquema, tipo de identificador, FK o contrato declarado, vigencia, permisos y recibo de lectura positiva.
Un dominio fuera de SQL necesita un conector específico: API de negocio, sistema operativo, telemetría de red, logs o servicio corporativo.
El registro actual de Hands de solo lectura sigue siendo limitado. Ninguna columna SQL se convierte en consulta ejecutable simplemente por figurar en el atlas.
La integración futura deberá registrar qué Hand soporta qué categoría, sin falsos PASS por clasificación correcta.

## Casos particulares

Un incidente ITIL puede pertenecer a empresa 3 aunque la ruta eSistema.ITIL/empresa 3 no resuelva: se constató su presencia bajo dbITIL_D a través de la conexión ITIL existente.
Sistemas General y Gerencial no son alias inocuos de Comercial: su destino depende de eSistema/empresa y puede divergir.
Una OT de Distribución, una OT Comercial y una OT administrativa son objetos distintos, incluso si sus columnas tienen nombres similares.
La misma lectura de medidor puede depender del período y clase de suministro (mayor/menor), no de un solo campo.

## Estado

21 dominios clasificados; 13 con posibles fuentes SQL y 8 sin cobertura de SQL suficiente.
0 nuevas Hands integradas, 0 procedimientos empresariales ejecutados, 0 reparaciones certificadas en esta fase.
