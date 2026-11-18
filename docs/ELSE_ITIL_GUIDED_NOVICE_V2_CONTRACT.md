# ELSE-ITIL — guía de diagnóstico para principiantes V2

**Objetivo:** ayudar a una persona sin experiencia a entender su problema, distinguir hipótesis con una comprobación segura por turno, interpretar alternativas y preparar evidencia para escalar. **Nunca reparar automáticamente**.

## Diferencias frente al servicio anterior

- **Memoria de conversación por incidente:** los turnos, respuestas y pasos se almacenan en SQLite privado, con identificador impredecible de sesión, contador monotónico, idempotencia exacta, rechazo de cambios en solicitudes ya registradas, vencimiento y purga a los 30 días. Máximo seis turnos.
- **Dos destinatarios separados:** `para_ti` contiene una única comprobación que puede hacer una persona sin permisos especiales; `para_soporte` documenta verificaciones que requieren personal autorizado.
- **Diferenciación explícita:** cada respuesta incluye dos hipótesis no confirmadas, qué observar, qué significan dos resultados alternativos y una pregunta breve sobre esa observación.
- **Control determinista antes de responder:** rechaza acciones de SQL, permisos, consola, credenciales, cambios de bases, configuraciones, alegaciones de reparación o certeza causal sin evidencia. Si ninguno de los modelos entrega una respuesta conforme, no se inventa una solución: se devuelve `NEEDS_HUMAN_TRIAGE` con un paso conservador y `quality.accepted=false`.
- **No se otorgan privilegios:** nunca consulta las bases corporativas, ni permite operaciones de negocio. Los casos y respuestas del usuario son datos NO confiables. Las consultas originales de QA quedan ajenas al nuevo endpoint.

## API privada, autenticada y opcional

Activación explícita mediante `--guided-db /ruta/privada/sessions.sqlite`. Sin ese argumento, los endpoints nuevos devuelven 404 y el comportamiento del servicio anterior no cambia.

La misma autorización Bearer privada existente se requiere para ambos endpoints. Ningún token debe copiarse al repositorio.

Inicio:

```http
POST /v1/support/guided/start
Content-Type: application/json
Authorization: Bearer [token privado]

{"case_ref":"CASO-EJEMPLO-001","input_scope":"requester_submitted",
 "service":"Aplicación de oficina",
 "description":"No puedo iniciar sesión; aparece un aviso en la pantalla."}
```

Continuación:

```http
POST /v1/support/guided/continue
Content-Type: application/json
Authorization: Bearer [token privado]

{"session_id":"[identificador devuelto por start]",
 "expected_turn":2,
 "reply":"No entiendo cómo mirar eso desde mi pantalla."}
```

El servidor devuelve `session_id`, `turn`, `next_turn`, `status`, `guide`, `quality`, `model_selected`, `executed_changes:false`, `diagnosis_certified:false` y `replayed` cuando se repite exactamente un turno.

Si cambia el contenido de un turno ya registrado, se rechaza. Si se intenta saltar turnos, se rechaza. Si caduca la sesión o se excede el máximo, se rechaza. No se pueden insertar soluciones históricas ni fuentes adicionales por la API.

## Despliegue y reversión

El lanzador `ops/run_specialist_v2_guided.sh` conserva el puerto privado 18883, el modelo Qwen 9B, su fallback 4B, los flags de despacho QA, el almacén antiguo de atención y el archivo de token ya existente. Añade exclusivamente un almacén SQLite independiente para las conversaciones.

No se debe sustituir el servicio anterior sin comprobar previamente, mediante pruebas automatizadas y un canario loopback, que los endpoints heredados siguen operativos. Un despliegue por drop-in systemd con nuevo `WorkingDirectory` y `ExecStart` debe conservar el archivo de reversión; al retirarlo debe restablecer el servicio anterior.

## Evaluación

La comparación emparejada utiliza exactamente los mismos 24 incidentes de agosto/septiembre 2026 que la campaña anterior y tres turnos hipotéticos por caso. Se contabilizan por separado:

- Respuestas conformes entregadas realmente por el modelo primario/fallback.
- Casos que exigen intervención humana (`NEEDS_HUMAN_TRIAGE`).
- Primera comprobación de pantalla asignada al usuario, resultados alternativos y explicación sencilla.
- Adaptación al «no entiendo» y al «sigue fallando», sin repetir instrucciones indistinguibles.
- Evidencia sin datos sensibles y escalamiento.
- Integridad e idempotencia de la memoria conversacional.

**Ni los 72 turnos de prueba, ni un evaluador LLM independiente, ni las pruebas unitarias prueban comprensión real, precisión de causa raíz o solución efectiva.** Para demostrarlo se necesitan operadores y personas de soporte evaluando casos con comprobaciones físicas/documentales. No se reescriben los datos ni se finge haber consultado el sistema empresarial.
