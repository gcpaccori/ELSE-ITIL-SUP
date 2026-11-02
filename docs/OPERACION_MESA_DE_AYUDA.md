# RIV: mesa de ayuda operativa (piloto privado)

Estado verificado 2026-11-02: servicio **operativo en loopback**, puerto **18881**,
host `elsecluster5`. Modelos privados Qwen 3.5 4B (GPU 7) y 9B de respaldo
(GPU 6). La interfaz acepta una incidencia suministrada por el solicitante,
genera orientación, ejecuta verificadores y guarda una respuesta en SQLite.

**No es un conector aprobado a los tickets históricos de ELSE** y no consulta
las bases corporativas. No desbloquea cuentas, cambia permisos, repara redes,
ni cierra tickets. Exigir evidencias funcionales y autorización para esos pasos.
La aceptación del plan acredita una propuesta de atención, no una reparación.

## Interfaz

- `GET http://127.0.0.1:18881/health` devuelve el estado general.
- `POST http://127.0.0.1:18881/v1/support` recibe JSON con
  `case_ref`, `input_scope`, `service`, `description` y
  `evidence` opcionales con IDs `E1...`.
- `input_scope`: únicamente `synthetic` o `requester_submitted`. No introducir
  expedientes corporativos, información de terceros ni secretos sin autorización
  de tratamiento. El marcador de origen NO demuestra aprobación institucional.
- Cabecera `Authorization: Bearer <token privado>`. Token solo en el host,
  fichero con permisos de propietario `600`. La API escucha únicamente en
  `127.0.0.1`; no se publica ni mediante Funnel ni en un dominio público.
- Respuesta: diagnóstico, hipótesis, condiciones, acciones, responsables
  propuestos, comprobaciones, estado operativo y alertas del auditor.
- El estado `ACTION_PLAN_AUTHORIZATION_PENDING` indica traspaso pendiente,
  `DIAGNOSTIC_GUIDANCE` indica investigación guiada, y
  `NEEDS_HUMAN_TRIAGE` indica que ningún modelo pasó el verificador.
- En todos los estados: `certified_repair=false` y `executed_changes=false`.

## Ejecución comprobada

- Comprobación HTTP health: 200, estado READY.
- Acceso POST sin token: 401.
- HTTP POST autenticado sobre caso sintético de conectividad: 200, respuesta
  del 4B, tres pasos, ~9.1 s, sin alertas de seguridad en esa respuesta.
- CLI sobre caso sintético de permisos con modelo principal inválido a propósito:
  el 9B atendió el caso como respaldo. Esta prueba NO se dejó en configuración
  permanente.
- 118/118 pruebas en entorno Python 3.11, incluyendo HTTP con acceso negativo,
  privacidad básica, fallback, persistencia y prevención de referencias duplicadas.

## Ejecución manual en el host

Usar el intérprete Python 3.11 del entorno autorizado y el repositorio
`/home/u23u/else_itil_sup_run/repo`. La variante CLI:

```bash
cd /home/u23u/else_itil_sup_run/repo
PYTHONPATH=. /home/u23u/miniconda/envs/orquesta_py311/bin/python \
  -m else_dominance.support_desk \
  --input /RUTA_PRIVADA/solicitud.json \
  --output /RUTA_PRIVADA/atencion.json \
  --db /RUTA_PRIVADA/atenciones.sqlite
```

Evitar publicar archivos privados, datos personales, tokens y respuestas de
incidentes reales en GitHub. Los ejemplos del repositorio deben ser ficticios.

## Frontera pendiente

Para atender retrospectivamente los 14,950 tickets de enero–septiembre 2026
se requiere el conjunto individual **autorizado y depurado**, con acceso a
antecedentes del entorno corporativo dentro del perímetro permitido. Ni el
dashboard QA agregado ni la API de solicitudes nuevas sustituyen esa capacidad.

Para resolver realmente se necesitan herramientas de diagnóstico de lectura,
roles oficiales comprobados, autorización de cambios cuando proceda y prueba
posterior del resultado con el solicitante. Nunca equiparar plan aceptado con
ticket cerrado.
