# ELSE-ITIL V6 — prueba operativa con Qwen y entrega verificable a soporte

**Fecha:** 19 de noviembre de 2026.
**Código desplegado:** `main@024daf9e08cf2d6a6bbf18ee6a9c84822e170409`, PR #55, CI #211 SUCCESS.

## Resultado del escenario sintético ejecutado

Se inició un caso de aplicación imaginaria en el canario V6 `127.0.0.1:18915`,
utilizando un token privado del piloto. El caso no procedía de una base empresarial
y no contenía ningún ticket real.

| Turno | Solicitud del usuario simulado | Resultado | Latencia |
|---|---|---|---:|
| 1 | Error en pantalla ficticia | Qwen local, contrato aceptado | **20,169 s** |
| 2 | «No entiendo» | Qwen local, contrato aceptado | **10,465 s** |
| 3 | «Sigue fallando y no tengo permisos» | Derivación determinista, **no llamada a Qwen** y **no PASS del modelo** | **0,004 s** |

Después de estos turnos, se comprobó el recorrido:
1. Lectura del caso propio e historial de tres turnos.
2. Emisión de paquete firmado con consentimiento explícito.
3. Comprobación de firma HMAC y registro de consentimiento por token de técnico.
4. Presentación de los tres objetivos técnicos preexistentes del Core:
   `ITIL_CASE_EXISTS`, `ITIL_SERVICE` e `ITIL_MODULE`,
   **sin disparar ninguna consulta QA**.
5. Revocación de los recibos del usuario; la verificación posterior respondió
   `HTTP 422 HANDOFF_RECEIPT_NOT_ACTIVE_OR_BOUND`, como debe ocurrir.

La primera ejecución del verificador había tratado ese **422 esperado** como
una excepción no manejada. Se conservó la evidencia de los tres turnos
y se completó la verificación con un recibo nuevo en la misma sesión,
**sin volver a generar respuestas de Qwen**.

## Qué demuestra y qué NO

**Demuestra:** funcionamiento de la API privada, memoria conversacional,
salida guiada validada por formato, derivación rápida, firma, consentimiento,
revocación y preflight técnico sin ejecución.

**No demuestra:** comprensión de una persona real, identidad corporativa,
relación entre el paquete y un ticket ITIL real, exactitud causal,
reparación efectuada, p95 bajo carga o madurez para autoservicio público.
El resultado de un escenario sintético no es una tasa de éxito.

Los cuatro servicios V2, V4, V5 y V6 continuaron activos con
`repairs_enabled:false`; el piloto no efectuó operaciones empresariales.

Código reproducible: `qa/workbench_v6/live_handoff_smoke.py`. Resumen agregado
(sin conversaciones, nombres, tokens ni IDs privados):
`data/2026_v6_live_qwen_consent_handoff_aggregate.json`.

**Dictamen:** V6 es usable como piloto interno supervisado, con transferencia
a soporte verificable. La madurez diagnóstica corporativa sigue en `NO_GO`.
