# ELSE-ITIL — Capacidad Pareto real: investigación transversal

10 de noviembre de 2026. Esta capacidad NO es un Pareto de casos.
Ataca el bloqueo central: el agente multietapa ya podía pedir herramientas,
pero no estaba vinculado de forma reutilizable con el worker NuGet real.

## Qué hace

Dado un caso QA autorizado y los objetivos de evidencia, selecciona
el conjunto mínimo de Hands registrados que cubra la mayor cantidad
de esos objetivos dentro de un presupuesto de operaciones.

- Ejecuta únicamente capacidades con backend real registrado.
- Inicia lectura ITIL exacta mediante la cola SQLite y Windows ELSE62.
- Recupera el recibo, el estado O5/O13/O15 y el diagnóstico post-evidencia.
- Declara evidencia faltante cuando no existe un Hand instalado.
- No certifica reparaciones, causas raíz ni precisión estadística.

Actualmente la única lectura corporativa integrada en este núcleo es la
de incidentes ITIL de septiembre QA. SAP, comercial, permisos y estado
de aplicaciones siguen siendo capacidades pendientes de integración.

## Implementación

- else_dominance/core_capability.py: planificador de mínimo conjunto real de Hands.
- else_dominance/qa_live_adapter.py: puente desde InvestigationAgent.query_live
  hasta la cola real, con identidad exacta del caso y lectura pendiente
  claramente diferenciada de lectura verificada.
- else_dominance/agent.py: impide que lecturas PENDING o catálogos de
  demostración fundamenten afirmaciones de observación corporativa.
- else_dominance/qa_dispatch_queue.py: cola duradera y reverificación O5;
  controla temporalidad mediante recepción en Linux (los relojes de Linux
  y ELSE62 tienen aproximadamente 11 minutos de diferencia).
- qa/qa_outbound_worker_windows.py: trabajador real programado en ELSE62.
- else_dominance/support_http.py: rutas nuevas de invocación y seguimiento,
  conservando el contrato anterior de /v1/support.
- Pruebas sintéticas separadas para planificación, ejecución, retorno y
  rechazo de consultas/identidades inválidas.

## Rutas QA nuevas

POST /v1/qa/core/investigate
GET /v1/qa/core/jobs/{job_id}

No se modificó la interfaz. Se verificó primero en la Preview 18884.

## Evidencia real del 10 de noviembre

Ejecutamos un caso permitido con los objetivos ITIL_CASE_EXISTS,
ITIL_MODULE y SAP_ORDER_RESPONSE. El núcleo seleccionó solo el
Hand real itil.qa.nuget.exact.read.v1 y devolvió SAP_ORDER_RESPONSE
como objetivo pendiente, sin simular acceso SAP.

Trabajo: f11d0b212ffe40e9aa30b49366c3db2b
Estado: COMPLETED, EVIDENCE_VERIFIED
Recibo SHA256: 3b49015b359202ffcb3fe8daae8caa19dbbd61f228685c04ed928e9f2883cc57
Diagnóstico: DIAGNOSTIC_GUIDANCE (aprobado por contrato)
Causa raíz certificada: NO. Reparación ejecutada: NO.

Un primer trabajo de prueba quedó RUNNING durante la corrección de
verificación temporal; NO se cuenta como E2E exitoso.

## Aclaración de alcance

La PR #15 de enero estudió el Pareto de los tickets. Es información
auxiliar para elegir dónde añadir el siguiente Hand, pero NO es esta
capacidad ni prueba que se resuelva el 80 % de los problemas.

Siguiente objetivo: extender el Hand exacto ITIL a enero con receipt
nuevo y conectar lectura comercial/OT sobre identificadores de negocio
comprobados. Después evaluar resultados con especialistas.

No existe estimación empírica de precisión resolutiva a partir del
primer E2E. Esta versión sigue siendo un núcleo de acompañamiento QA.
