# ELSE-ITIL Preview — acompañamiento supervisado (2026-11-09)

## Alcance

Cinco incidentes sintéticos enviados a la API activa de ELSE-ITIL en
127.0.0.1:18883/v1/support (modelo Qwen 9B primario, Qwen 4B de respaldo).
**No modifica el servicio ni su interfaz.**

Secuencia: ingreso → inferencia real → persistencia exacta en SQLite
→ retroalimentación posterior de un técnico.

## Prueba efectuada

- 5/5 solicitudes procesadas por la API del servicio activo.
- 5/5 respondidas por el modelo primario.
- 5/5 estado DIAGNOSTIC_GUIDANCE.
- 5/5 respuestas coincidentes con las filas de atención del SQLite activo.
- 5/5 cumplen el contrato de salida; la relevancia técnica requiere evaluación.
- 0 valoraciones humanas registradas inicialmente: no se simula conformidad.
- 0 reparaciones certificadas y 0 promociones a memoria.

Los cinco escenarios están definidos en
examples/accompaniment_preview_5.synthetic.json:
acceso SIELSE 403, impresión, pedido SAP, DNS y diferencia comercial.

## Ejecutar y comprobar (en el servidor QA)

Desde el repositorio privado de la rama Preview:

~~~bash
cd /home/u23u/else_itil_preview_e2e_feedback_20261109
PYTHONPATH=. /home/u23u/miniconda/envs/orquesta_py311/bin/python \
  -m else_dominance.accompaniment_preview run \
  --scenarios examples/accompaniment_preview_5.synthetic.json \
  --output /home/u23u/else_itil_preview_e2e_qa_20261109/results \
  --token-file /home/u23u/else_itil_sup_run/support_live_private/service.token \
  --active-db /home/u23u/else_itil_sup_run/support_specialist_v1_private/attention.sqlite
~~~

El recibo privado de cada caso queda en el directorio results y su hash
se registra en feedback.sqlite. Las ejecuciones no pueden reutilizar un ID
con una respuesta cambiada.

Verificación independiente de los cinco recibos y SQLite:

~~~bash
PYTHONPATH=. /home/u23u/miniconda/envs/orquesta_py311/bin/python \
  -m else_dominance.accompaniment_preview audit \
  --scenarios examples/accompaniment_preview_5.synthetic.json \
  --output /home/u23u/else_itil_preview_e2e_qa_20261109/results \
  --active-db /home/u23u/else_itil_sup_run/support_specialist_v1_private/attention.sqlite
~~~

## Retroalimentación humana (sin cambios de interfaz)

Cuando un técnico revise el caso, el operador registra su conclusión:

~~~bash
PYTHONPATH=. /home/u23u/miniconda/envs/orquesta_py311/bin/python \
  -m else_dominance.accompaniment_preview feedback \
  --db /home/u23u/else_itil_preview_e2e_qa_20261109/results/feedback.sqlite \
  --case PREVIEW-20261109-SAPPEND \
  --role TECHNICIAN \
  --decision PARTIAL \
  --note "Falta confirmar los identificadores antes de revisar permisos." \
  --observed-result NOT_CHECKED
~~~

Ejemplo didáctico: **no se ha enviado como valoración real**.

Las decisiones admitidas son USEFUL, PARTIAL, INCORRECT y ESCALATE. El
resultado observado puede quedar en NOT_CHECKED, CHECKED_NOT_RESOLVED o
CHECKED_RESOLVED_BY_TECHNICIAN. Se vincula la revisión al hash de la
respuesta exacta. Las rectificaciones son eventos adicionales, no
sobrescrituras.

Consultar estadísticas y pendientes:

~~~bash
PYTHONPATH=. /home/u23u/miniconda/envs/orquesta_py311/bin/python \
  -m else_dominance.accompaniment_preview report \
  --db /home/u23u/else_itil_preview_e2e_qa_20261109/results/feedback.sqlite
~~~

## Guía de revisión del técnico

**El PASS de contrato no significa que la causa esté confirmada.**
En todos los casos se observó alerta de correspondencia de roles pendiente.
Se deben comprobar especialmente:

- SIELSE 403: no derivar directamente de HTTP 403 que falte un grupo.
- Impresión: distinguir cola cliente/servidor de permisos no demostrados.
- SAP: obtener número/fecha de pedido antes de hipótesis de permisos.
- DNS: reproducir desde otra estación/VLAN y resolver fallos alternativos.
- Comercial: contrastar fecha de corte y criterios; roles oficiales por validar.

Registrar si el plan distingue hechos de hipótesis, pide primero la evidencia
determinante, asigna un responsable verificable y propone una prueba posterior.

## Criterio para compartir la Preview

Los cinco E2E automatizados y sus persistencias quedaron verificados.
Falta que técnicos de Soporte realicen la revisión y dejen retroalimentación.
Esta Preview no afirma cierre de tickets, reparaciones ni entrenamiento.
