# ELSE-ITIL V5 — prueba en canario privado con Qwen real

Fecha: **18 de noviembre de 2026**.

**Código realmente desplegado:** `main@1234b8d4f85b53d9483c8958015ba61d269b1a99`, PR #53, CI #205 SUCCESS.

## Prueba sintética de tres turnos

Se usó la API V5 en `127.0.0.1:18914`, con una credencial piloto individual de alta entropía conservada en el servidor. Ningún dato de incidentes reales de Electro Sur Este se envió en la prueba; todo el texto era sintético. Se verificó respuesta HTTP 200, secuenciación de memoria, indicadores de calidad y prohibición de cambios.

| Turno | Entrada sintética | Origen | Gate de respuesta | Latencia medida |
|---|---|---|---|---|
| 1 | La pantalla de una aplicación ficticia aparece en blanco | Qwen 9B primario real | Aceptado | **10,45 s** |
| 2 | Persona principiante indica «no entiendo» | Qwen 9B primario real | Aceptado | **10,17 s** |
| 3 | «Sigue fallando; no tengo permisos» | Regla determinista, **sin Qwen** | **No** computado como PASS del modelo; derivación humana | **inferior a 0,01 s** según la medición redondeada |

El tercer turno tiene `NEEDS_HUMAN_TRIAGE`, `quality.accepted=false` y `model_selected=null`. Evita que se invente otra comprobación o se soliciten privilegios, pero NO certifica causa ni reparación.

## Integración operativa y seguridad comprobadas

- Los servicios V2 `18883`, V4 `18913` y V5 `18914` siguieron `active/READY` simultáneamente.
- V5 usa `guided_principal_required=true` y claves independientes por principal; un usuario no puede continuar la sesión de otro.
- HTTP 401 si no hay token válido; control de concurrencia con HTTP 429; replay alterado rechazado.
- Directorio privado con modo `0700`, credenciales y SQLite con `0600`.
- `GET /v1/support/capabilities` enumera solo las capacidades realmente adjuntas a esta API.
- `GET /v1/support/readiness` conserva el dictamen `NO_GO`, última fecha registrada 16/09/2026, sin frescura de ingesta certificada ni revisiones humanas.
- Las tres instancias mantienen `repairs_enabled=false`; no se consultaron ni modificaron objetos empresariales desde la prueba guiada.

## Interpretación responsable

Este experimento contiene **un único caso sintético**. Dos turnos aceptados indican que el modelo cumplió el contrato; no demuestran precisión diagnóstica ni comprensibilidad para personas reales. La latencia es una observación puntual, no una certificación SLO ni comparación estadística con V2/V4.

La regresión previa con 24 casos reales anonimizados todavía indica V4 **17/24** conversaciones de tres turnos aceptadas contra V2 **20/24**. No hay benchmark emparejado de V5 de 545 casos Qwen reales. No promover V5 a servicio principal sin esa evaluación, revisión humana y datos corporativos vigentes.

## Archivos

- Ejecución reproducible: `qa/maturity_v5/live_v5_real_model_canary.py`.
- Resultado agregado sin identificadores: `data/2026_v5_live_model_guidance_synthetic.json`.
- Seguridad, identidad y decisión de `NO_GO`: `docs/ELSE_ITIL_V5_INTEGRACION_GOBERNADA.md`.

**Dictamen:** V5 operativa en piloto privado, con derivación rápida y seguridad verificada; **madurez diagnóstica integral todavía NO CERTIFICADA**.
