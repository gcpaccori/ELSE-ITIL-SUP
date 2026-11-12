# ELSE-ITIL-SUP: agosto de 2026, cohorte completa QA

Fecha: 10 de noviembre de 2026. Estado: campaña Qwen9B en ejecución bajo QA, sin escrituras SQL.

## Identificación del mes
El lector NuGet autorizado de ELSE70/dbITIL_D/dbo.taIncidente confirmó agosto 2026 con **1.819 incidencias** (1–31 de agosto). Septiembre 2026 tiene 545, octubre y noviembre tienen 0. Agosto es el penúltimo mes con datos disponibles.

## Evidencia
Se extrajeron a ELSE62 1.819 solicitudes y 1.819 registros de solución histórica, todos identificados por SHA-256 de ticket y por mes. Los textos de solución histórica se mantuvieron sellados en Windows. Solo las solicitudes redactadas, con campo histórico WITHHELD, fueron transmitidas al Qwen interno.

El exportador finalizó con un IOException posterior a la creación de ambos archivos; se conservó ese hecho, sin declararlo éxito. Un auditor posterior independiente comprobó la integridad de los 1.819 JSON de solicitudes y soluciones, identidad exacta entre los 1.819 IDs únicos, fechas, SHA de fuentes y SHA del paquete redactado. El resultado post-exportación fue PASS.

SHA-256 del archivo de solicitudes redactadas:
7200e6ea8f015b97475c482c9d128c0a0e2ed504b6e090421b99e4442566cfc0.

## Composición
- 1.819 solicitudes.
- 1.664 con solución histórica; 155 sin solución.
- 1.149 soluciones históricas de 80 caracteres o más; 515 breves no vacías.
- 4 solicitudes redactadas demasiado breves para un diagnóstico fundamentado.
- Servicio código 1: 967; 60: 165; 3: 152; 61: 152; 70: 124.

Los códigos de servicio se conservan sin inventar nombres.

## Ejecución
- Modelo original: Qwen3.5 9B del servidor interno, endpoint 127.0.0.1:18782.
- Script: qa/qa_aug2026_full.py, con 12 trabajadores, reanudable, un resultado por SHA.
- Servicio: else-itil-aug2026-full-qa.service. Reinicia ante una falla sin rehacer casos asentados.
- Evidencia conocida: extracción corporativa QA de ITIL.taIncidente (histórica, **NO** lectura dinámica individual O5 por cada caso).
- Salida: hipótesis, procedimiento condicional, pruebas de cierre, estado no ejecutado, fuente ITIL.taIncidente y recibo E1.
- Se rechazan referencias SQL no observadas, afirmaciones falsas de reparación y roles oficiales no certificados.
- El progreso se encuentra en aug2026_progress.json. El resultado privado completo en aug2026_qwen9b.private.jsonl.
- La auditoría qa/qa_aug2026_independent_audit.py verifica la integridad y no permite emitir la auditoría final con menos de 1.819 registros.
- Aprobación estructural **no** significa exactitud de causa ni reparación certificada.

## Rutas privadas
En Linux: /home/u23u/else_itil_aug2026_qa_20261110/
En Windows: C:\Temp\ELSE_ITIL_AUG2026_QA_20261110

No subir datos de solicitudes, soluciones históricas, credenciales, ni journal privado a GitHub.

## Estado de integración
La campaña se inició tras un piloto 12/12 estructuralmente aprobado; se está procesando el resto de los 1.819 expedientes en una instancia persistente. No declarar finalización antes de auditoría final independiente.
