# Cinco escenarios ITIL agosto 2026 — guía de investigación

Las soluciones históricas se estudiaron separadas de la evaluación ciega. Estas rutas no constituyen reparaciones realizadas.

| Escenario | Tablas y condiciones de lectura | Restricción importante |
|---|---|---|
| Cambio de recurso de OT | OT, taPresupuesto, taPresupuestoTrabajoRecurso y auditoría | No actualizar estado en vez de corregir recurso/costo |
| Apellido y fiscalización | ITIL, padrón, OT instalación y taOrdenTrabajoEstadoHistorico | No alterar directamente una OT ya comunicada a OSINERGMIN |
| Fecha de cambio de medidor | OT + suministro + taMedidorSuministro + periodo + cambios | La PK del medidor incluye FechaInstalacion; no aplicar SQL del historial ITIL |
| Reapertura OT | OT + estado + historial OSINERGMIN + grupo supervisor | Requiere ruta controlada, no UPDATE libre |
| Presupuesto inicial cero | taPresupuesto + taComprobante + importes + validación tributaria | No generar comprobante forzado a cero |

En las cinco atenciones originales faltó una coincidencia empresarial exacta en las tablas QA consultadas: los controles positivos prueban que el lector funciona, pero no cierran esos expedientes.
