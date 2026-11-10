# ELSE-ITIL-SUP — V1 Beta: fresh SAP/OT evidence slice

QA: 10 de noviembre de 2026. **Solo QA; no se ha desplegado en producción.**
Dependencias: ELSE-ITIL-SUP PR #20 y ELSE CORE PR #364, ambas apiladas sobre otras PR.

## Función

API privada en 127.0.0.1:18887, diferente al servicio histórico 18886 y al original 18883. Un cliente autorizado envía POST /v1/beta/refresh-ot con un case_sha256 de una lista fija de 100 casos de febrero 2026. Qwen9B pide exclusivamente qa_sap_ot_exact_read(case_sha256); ni el modelo ni el cliente pueden escoger SQL, servidor, identificador OT, credenciales ni rutas.

ELSE62 busca solicitudes privadas por SSH cada 5 minutos, verifica expediente y único número OT reportado, ejecuta el lector .NET8 NuGet de SELECT fijo en ELSE70/dbDistribucion_D, produce un recibo SHA/HMAC y lo envía por SSH. El clúster lo vincula con la solicitud de Qwen, la fuente original C# y la identidad del caso antes de pasar O5/O13/O15. La API POST /v1/beta/investigate usa el recibo ITIL original y el SAP/OT recién verificado para pedir un diagnóstico adicional. El ledger de supervisión es diferente del histórico.

## Evidencia real y controles

| Control | Resultado |
|---|---:|
| Solicitudes nuevas exactas de Qwen | 16/16 |
| SELECT NuGet nuevos en ELSE62 | 16/16 |
| Recibos HMAC y nativos O5/O13/O15 | 16/16 |
| Diagnósticos nuevos completos por API | 16/16 |
| Planes aceptados por contrato | 16/16 |
| Órdenes encontradas en tablas QA específicas | 3 |
| Órdenes ausentes allí | 13 |
| Cambios de presencia OT / estado SAP / conteo de respuestas respecto al archivo | 0 / 0 / 0 |
| Reparaciones certificadas | 0 |
| Relación oficial ITIL–OT certificada | 0 |
| Roles corporativos aprobados | 0 |
| Aprobaciones humanas reales | 0 |

Los 16/16 planes aceptados representan estructura y procedencia verificadas, NO precisión causal ni incidentes resueltos. El número OT procede de un texto redactado, no de una clave empresarial certificada. No existe cierre automático.

## Ejecución y aislamiento

- Servicio Linux QA: else-itil-beta-fresh-qa.service en loopback 127.0.0.1:18887.
- Tarea Windows: ELSE_ITIL_BETA_FRESH_OT_QA; cuenta de QA, logon S4U, cada cinco minutos, hasta 3 minutos por ejecución, repetición configurada durante 365 días. Se probó con Last Result = 0; no reejecutó SQL ya entregado.
- Lector fijo: qa/Feb100SapOtRead.cs, SHA-256 81c8da152f428c0d1c6273aa24d6ca4b01cbe4a2fedd17fcb1cefce41fc37be1.
- Clave HMAC: archivo Windows con acceso NTFS exclusivo para cuenta QA, SYSTEM y administradores, sin BUILTIN Users; archivo Linux modo 0600.
- Auth HTTP: bearer privado. Revisión humana: credencial independiente y roster formal, todavía NO configurados.
- Abstención: vinculacion_comercial_verificada=false; rol_oficial_validado=false; ejecutado=false; confirmado=false; responsable=Responsable autorizado por confirmar.
- No se alteraron los servicios históricos ni se ejecutaron modificaciones de SQL.

## Cola de evaluación humana

Preparados 30 casos PRIVADOS: 16 con dos Hands y evidencias nuevas; 14 ITIL-only explícitamente pendientes de nueva fuente, no aptos todavía para afirmar una solución. 0 revisiones reales completadas.

## Archivos privados (NO subir al repositorio)

Ruta /home/u23u/else_itil_beta_fresh_qa_20261110/:
requests/*.private.json; outbox/*.private.json; verified/*/receipt.private.json; fresh_http16_campaign_audit.json; fresh_independent_e2e16_audit.json; human_review30_queue.private.jsonl; beta_supervision_fresh.sqlite. No subir texto de tickets, soluciones, tokens ni secretos a GitHub.

## Impedimentos para declarar V1 Beta corporativa

- Acreditar una vinculación ITIL↔OT oficial usando claves/contratos corporativos.
- Obtener la matriz aprobada de responsables. No inferir roles por Qwen.
- Recibir validación de técnicos reales de 30 casos y pruebas de cierre; hasta ahora 0.
- Ampliar el autorizador a tickets nuevos fuera de los 100 históricos de febrero.
- Completar integración de las PR apiladas y evaluar despliegue y seguridad corporativos.

El 80 % de utilidad revisada por técnicos sería un objetivo propuesto, no una métrica conseguida.
