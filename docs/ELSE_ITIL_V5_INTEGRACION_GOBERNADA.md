# ELSE-ITIL V5 — integración gobernada de capacidades

**Fecha:** 18/11/2026. **Base auditada:** `main@40173839922c1aa1274daa4ee984d44872a20014`.

## Objetivo real

ELSE-ITIL debe **diagnosticar provisionalmente, orientar a una persona sin conocimientos técnicos, pedir observaciones y derivar con evidencia**, sin ejecutar reparaciones, aprobar cambios, extraer datos corporativos sin autorización ni atribuirse causas raíz. El porcentaje de respuestas que pasan un validador NO es una tasa de problemas resueltos.

La auditoría anterior revisó 20 características; descubrió que octubre 2026 tenía **cero incidentes en la fuente SQL QA específica**, mientras septiembre tenía **545**. El modelo V4 obtuvo **17/24** conversaciones con tres turnos aceptados frente a **20/24** en V2. **No hay certificación humana ni causal.** Esta versión cierra controles de operación y seguridad, no los requisitos externos ausentes.

## Arquitectura de integración

```text
                       Cliente interno del piloto
                                  │
                    Identidad piloto (token propio)
                                  │
                  ┌───────────────▼────────────────────┐
                  │ ELSE-ITIL V5 / 127.0.0.1:18914    │
                  │ Control de admisión ≤2 simultáneas │
                  │ Solo 1 solicitud activa/principal  │
                  └────────────────┬───────────────────┘
                                   │
                  ┌────────────────▼──────────────────┐
                  │ Store privado SQLite               │
                  │ Tenant = SHA256(principal,case_ref)│
                  │ 6 turnos · 30 días · replay exacto │
                  └────────────────┬──────────────────┘
                                   │
                ┌──────────────────▼─────────────────┐
                │ ¿Faltan permisos, persiste el caso  │
                │ o se reporta mejoría?               │
                └────────────┬────────────┬──────────┘
                             │            │
                  Regla segura            Investigación restante
                  determinista            │
                             │      Qwen 9B (timeout 35 s)
                             │            │
                             │      Retry controlado
                             │            │
                             │      Qwen 4B (timeout 20 s)
                             │            │
                             └────────────┤
                                          ▼
                              Gate de seguridad,
                              privacidad y certeza
                                          │
                        ┌─────────────────┴──────────────┐
                        ▼                                ▼
                     ACEPTADO                        ABSTENCIÓN
               Guía legible y pruebas             Derivación humana
               sin causa confirmada               NO modelo aceptado
```

La espera de red está limitada por cada intento del cliente HTTP, **no** es un SLO de tiempo total garantizado; las respuestas demasiado lentas producen abstención. Los límites de simultaneidad no sustituyen una evaluación real de carga o alta disponibilidad.

## Cambios integrados

| Brecha anterior | Mejora técnica V5 | Evidencia / limitación |
|---|---|---|
| Token de servicio compartido | Manifiesto privado de **tokens de alta entropía por principal**; solo se almacenan sus SHA256. Las rutas guiadas exigen ese token en modo estricto | Autorización de sesión por principal, **NO SSO corporativo ni validación de empleado** |
| Riesgo de acceso cruzado | Sesiones con `subject_id` y clave interna derivada de principal+referencia; reutilizar el mismo `case_ref` no mezcla usuarios | Pruebas de acceso ajeno, replays y migración de sesiones V2 |
| Turnos con permisos insuficientes tardan mucho | Derivación determinista inmediata sin Qwen; se marca `quality.accepted=false` | No se infla el éxito del modelo |
| Usuario dice «ya funciona» | Confirmación por pantalla sin afirmar reparación; omite llamada innecesaria | `USER_REPORTED_IMPROVEMENT_UNVERIFIED`, no certifica cierre |
| GPU saturada / respuestas concurrentes | Admisión opcional de hasta 2 peticiones y una por principal, con respuesta HTTP 429 para exceso | No certifica SLA, solo evita sobrecarga local |
| Qwen puede repetir datos privados | Gate sobre campos del modelo, identificadores redactables y secretos; revisita recibos antiguos | Redacción heurística, aún requiere revisión de privacidad |
| El runtime no exhibe las brechas | Endpoint privado `GET /v1/support/readiness` con snapshot `NO_GO`, fuente, antigüedad, métricas agregadas e informe humano pendiente | La fuente SQL NO se consulta automáticamente desde esta API |
| Muchas funciones difíciles de distinguir | `GET /v1/support/capabilities`: catálogo de las **12 capacidades del proceso** y estado real, no de todos los módulos del repositorio | Capacidades sin conexión o sin evidencia se marcan explícitamente |
| Evaluación humana ausente | Validador privado de rúbrica ciega; obliga dos revisiones técnicas por caso y observaciones de principiantes | 0 personas revisadas por ahora; sin autoridad corporativa, no certifica causa |
| Concurrencia y replay a escala | 1.000 sesiones sintéticas separadas, 3.000 turnos, diez principales; misma referencia de prueba compartida sin colisión | **Stub determinista, cero llamadas Qwen** |

## Contratos de API

Con el parámetro `--guided-principals-file` habilitado, `/v1/support/guided/start` y `/continue` **rechazan el token compartido de servicio**. Exigen token individual provisionado fuera de la API; el cuerpo del usuario nunca puede elegir `subject_id`.

`GET /health` continúa anónimo, mínimo y sin identidades. Los endpoints `GET /v1/support/readiness` y `/v1/support/capabilities` requieren el token de servicio existente. Se devuelven solo agregados; ninguna transcripción, contraseña, PK, identificador del caso o nombre de persona.

Las rutas `/v1/support` y el dispatcher QA existente no cambian. Activar V5 es **opt-in** con flags nuevos de `support_http`, no una migración destructiva.

El endpoint `/readiness` declara que la fuente observada **solo alcanza el 16/09/2026**, que octubre y noviembre no aparecen en el snapshot de `ELSE70/dbITIL_D`, y que no existe acreditación de frescura. Cero registros **no es una prueba de ausencia de incidentes empresariales**. La API no puede cambiar el dictamen a `GO` modificando únicamente el JSON; si ve un `GO` que no corresponde a su contrato verificable, falla en arranque.

La revisión humana registra 24 casos del paquete privado, cero calificaciones recibidas y estado `PENDING_HUMAN_REVIEW`. Una rúbrica autocumplimentada tampoco equivale a prueba corporativa de causa raíz.

## Verificación

Pruebas unitarias y de API: identidad, claves duplicadas, acceso cruzado negado, hash de credenciales, archivos privados `0600`, estados de abstención, HTTP 401/429, límite de concurrencia, replay 422, información de madurez y bloqueo de causas infundadas.

Carga mecánica de calidad: `qa/maturity_v5/qa_1000_isolated_sessions.py` (1.000 sesiones, 3.000 turnos sin Qwen) y salidas en `data/2026_v5_1000_isolated_synthetic_sessions.json`. Esto NO mide latencia de inferencia, exactitud ni satisfacción.

Validación humana: `qa/maturity_v5/human_review_gate.py`, paquete de revisión exclusivamente privado. No reproducir ni distribuir solicitudes sin revisión de privacidad.

## Despliegue aislado y reversión

* V2 principal: `127.0.0.1:18883` — continúa con despacho QA.
* V4 piloto: `127.0.0.1:18913` — no se altera.
* V5 nuevo canario: `127.0.0.1:18914` — sin despacho QA ni reparaciones.

`ops/deploy_specialist_v5_governed_canary.sh <SHA_EXACTO>` exige el commit fusionado, V2 y V4 activos, puerto privado, autenticación distinta, `NO_GO` y rollback; genera dos credenciales de **solo prueba sintética**, en archivos `0600`, que no se imprimen ni suben al repositorio. No son identidades reales de empleados.

Para detener el piloto sin afectar servicios anteriores:

```bash
systemctl --user stop else-itil-novice-v5-canary.service
```

La V5 **no debe sustituir V2** mientras no supere el benchmark a ciegas, las revisiones humanas y los SLO. Tampoco autoriza operaciones de cambio.

## Bloqueos que NO se pueden cerrar solo con código

1. Identificar la fuente ITIL corporativa vigente, restaurar la ingesta y demostrar su frescura con un recibo independiente. El snapshot revisado tiene cero octubre y noviembre y no autoriza conclusiones sobre toda la empresa.
2. Conectar SSO/identidad oficial y los permisos por expediente con aprobación de Seguridad. Un token local no prueba identidad laboral ni derecho al ticket.
3. Solicitar a especialistas la verificación causal de las hipótesis, **sin utilizar notas históricas como gold automático**; adjudicar con evidencia independiente y discrepancias documentadas.
4. Observar a personas principiantes reales, con privacidad aprobada, y comprobar que pueden seguir instrucciones y entender resultados; no solo completar JSON.
5. Demostrar latencia p95, capacidad, restauración, alta disponibilidad y resistencia ante fallas de Qwen en condiciones de trabajo, con objetivos de servicio establecidos.

**Dictamen posterior a la integración técnica V5:** más seguro y gobernable como piloto, pero **NO_GO para autoservicio corporativo no supervisado**. Esto es deliberado: el sistema no debe mentir sobre su madurez.
