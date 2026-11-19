# ELSE-ITIL V6 — flujo unificado para usuario y soporte

**Fecha:** 19 de noviembre de 2026
**Línea base:** `main@5d5a04f93642cd69b3a31ccffd742bc92f40bfc8`
**Objetivo:** usar las capacidades existentes de ELSE-ITIL sin duplicar motores, inventar relaciones entre tickets o ejecutar reparaciones.

## Flujo útil, completo y seguro

```text
┌──────────────────────┐
│ Usuario principiante │
│ Interfaz web privada │
└──────────┬───────────┘
           │ token individual de PILOTO
           ▼
┌─────────────────────────────────────────────┐
│ Conversación guiada con memoria (máx. 6)    │
│ • descripción, una comprobación segura       │
│ • observación A / B / no entiendo / persiste  │
│ • Qwen9B, fallback 4B, control de seguridad  │
│ • derivación inmediata si faltan permisos    │
└──────────┬──────────────────────────────────┘
           │ consulta de historial propia
           │ consentimiento explícito
           ▼
┌─────────────────────────────────────────────┐
│ Paquete de entrega firmado por V6            │
│ • observaciones del usuario                  │
│ • pasos sugeridos y validación del formato   │
│ • 72 h / revocable / HMAC SHA-256             │
│ • ningún dato empresarial certificado        │
└──────────┬──────────────────────────────────┘
           │ entrega manual por canal aprobado
           ▼
┌─────────────────────────────────────────────┐
│ Técnico autorizado: verifica firma y        │
│ existencia del consentimiento               │
│ • detecta alteraciones, caducidad, revocación│
│ • conoce los objetivos QA registrados       │
│ • no trata el número ingresado como FK/PK    │
└──────────┬──────────────────────────────────┘
           │ VINCULACIÓN OFICIAL PENDIENTE
           ▼
┌─────────────────────────────────────────────┐
│ Núcleo técnico existente de ELSE-ITIL       │
│ • Hand real QA mediante cola autorizada      │
│ • evidencia exacta + O5/O13/O15             │
│ • revisión humana y causa aún por demostrar │
└─────────────────────────────────────────────┘
```

El último bloque existe previamente en el repositorio. **La V6 no dispara el Hand QA por recibir un paquete.** Sería incorrecto inferir un `case_sha256` corporativo desde una referencia escrita por la persona. El técnico debe identificar y autorizar el ticket exacto, después consultar las herramientas QA registradas con sus recibos independientes. La entrega V6 facilita ese trabajo, pero no lo sustituye.

## Qué puede hacer una persona sin conocimientos técnicos

Desde `http://127.0.0.1:18915/v1/support/ui` **en el equipo autorizado o tras un túnel privado aprobado**:

1. Introducir el **token del piloto** (no su contraseña empresarial), una referencia y la descripción de lo que aparece en pantalla.
2. Recibir una sola comprobación segura y dos resultados alternativos. La página incluye respuestas rápidas: *Opción A*, *Opción B*, *No entiendo*, *Sigue fallando* y *Ya funciona*.
3. Continuar sin perder el historial de esa sesión. El navegador no almacena el token, el historial ni el expediente en `localStorage`, cookies o servicios externos.
4. Consultar el historial que le pertenece. El servidor rechaza solicitudes de otras identidades del piloto.
5. Autorizar explícitamente la preparación de una entrega a soporte. El usuario revisa la advertencia de privacidad y recibe un JSON firmado que puede copiar por un canal autorizado.
6. Revocar un recibo concreto o todos los recibos de esa conversación. Una revocación impide verificaciones futuras en el servidor, **pero no borra una copia ya distribuida**.

La página web estática se sirve desde la misma API privada; usa CSS y JS propios, política CSP `default-src 'none'`, sin fuentes remotas, analítica ni `innerHTML` para datos recibidos. Ningún endpoint está expuesto a Internet. Solo se autoriza el modo piloto interno supervisado.

## API — rutas nuevas

Las rutas anteriores `/v1/support`, `/v1/support/guided/start`, `/continue`, `/health`, `/readiness` y `/capabilities` conservan su significado.

| Ruta | Autorización | Función |
|---|---|---|
| `GET /v1/support/ui` | Página estática, solo red privada | Interfaz de ayuda |
| `GET /v1/support/ui.js`, `/ui.css` | Estáticos | Recursos locales con CSP |
| `GET /v1/support/guided/case/{session_id}` | Token individual del piloto | Vista del caso propio, sin fuentes QA |
| `POST /v1/support/guided/handoff` | Token individual | Emite paquete firmado, exigiendo consentimiento |
| `POST /v1/support/guided/revoke` | Token individual | Revoca recibo del caso propio |
| `POST /v1/support/guided/revoke-all` | Token individual | Revoca todas las entregas de esa sesión |
| `POST /v1/support/technician/verify-handoff` | **Token de servicio** (no de usuario) | Comprueba firma, vigencia, recibo en SQLite y revocación |

Ejemplo de autorización explícita de una entrega:

```json
{
  "session_id": "<identificador de 48 caracteres hexadecimales>",
  "consent_to_share": true,
  "privacy_notice_acknowledged": true
}
```

El recibo contiene un `case_handle` pseudónimo, observaciones y comprobaciones, con el contrato `USER_REPORTED_NO_CORPORATE_BINDING`, y banderas inmutables `qa_evidence_bound:false`, `cause_certified:false`, `repair_performed:false`. Firmado con clave **independiente** del Bearer de API. El servidor registra el hash de contenido y permite revocar sin modificar datos del negocio.

La respuesta de verificación para el técnico agrega:

- Integridad criptográfica y registro de consentimiento válidos o rechazo.
- Versión de la conversación al emitir el recibo y si existen turnos posteriores.
- Objetivos de evidencia **reales registrados** en el Core (`ITIL_CASE_EXISTS`, `ITIL_SERVICE`, `ITIL_MODULE`).
- Comprobación explícita de que **NO** se vinculó la identidad corporativa del ticket, **NO** se verificaron relaciones a objetos empresariales y **NO** se ejecutó ningún Hand QA automáticamente.

**Una firma válida acredita que el servidor emitió el paquete con consentimiento de la identidad del piloto. No certifica la identidad del trabajador, la veracidad de los mensajes, un diagnóstico ni la autorización sobre un ticket corporativo.**

## Despliegue aislado

`ops/deploy_specialist_v6_workbench_canary.sh <SHA_MAIN_FUSIONADO>` requiere lease exacto. Crea archivos privados 0600, genera dos identidades sintéticas QA y una clave de firma de 256 bits, activa una unidad nueva `else-itil-workbench-v6-canary.service` en `127.0.0.1:18915`, prueba todos los endpoints, revocación y estados de V2, V4 y V5. Si falla, quita la unidad nueva; no reinicia ni sustituye los servicios previos.

El servicio V6 sigue usando Qwen9B con fallback Qwen4B solo en los turnos que realmente requieren generación. Continúa con reparación automática deshabilitada, sin dispatcher QA en este canario.

Para conectarse desde otra máquina es necesario un **túnel autenticado autorizado**. La URL `127.0.0.1` por sí sola solo es accesible desde el propio servidor. No abrir públicamente el puerto ni distribuir tokens de QA como credenciales de trabajadores.

## Qué no resuelve todavía

- **Fuente corporativa vigente:** ITIL QA observada no presenta incidentes de octubre/noviembre de 2026. La V6 no repara ingesta.
- **SSO y autorización de usuario real:** los tokens actuales son identidades de prueba, no credenciales corporativas verificadas.
- **Diagnósticos causales independientes:** el paquete solo documenta observaciones; se requieren vínculos oficiales entre ticket, módulo y objeto de negocio y lectura contemporánea autorizada.
- **Comprensión humana probada:** falta el estudio con usuarios reales que evalúe que las explicaciones funcionen.
- **Rendimiento de Qwen bajo carga:** una interfaz y recibos firmados no prueban p95, failover ni precisión diagnóstica.

**Dictamen: integración operativa mucho más utilizable para un piloto supervisado. No elevar a autoservicio corporativo sin estos controles externos.**
