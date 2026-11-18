# ELSE-ITIL — experiencia conversacional segura V4

**Fecha:** 18 de noviembre de 2026.

## Para qué existe

La meta de ELSE-ITIL es **diagnosticar y orientar**, no ejecutar reparaciones. La aplicación debe ser útil a una persona que desconoce SQL, bases de datos, administración de sistemas y jerga de TI. El asistente sólo genera hipótesis y preguntas, nunca certifica una causa raíz ni convierte lo que dice el usuario en una lectura verificada del sistema.

La V2 existente ya ofrece memoria persistente por incidente, límites de seis turnos, vencimiento a 30 días, acciones seguras y un bloque de atención a soporte. La **V4 agrega una presentación directamente legible para el usuario**, una clasificación conservadora de lo que informó, defensas textuales de seguridad y compatibilidad con sesiones anteriores.

## Cambio principal: una respuesta apta para una pantalla de ayuda

Nuevo campo **aditivo**: `presentacion_para_usuario`. No retira campos de respuesta V2 ni modifica `/v1/support`.

- `etapa`: describe qué hace el asistente, sin porcentajes de progreso ni promesas de resolver. Ejemplos: `COMPROBAR_UNA_COSA`, `ACLARAR_EN_LENGUAJE_SENCILLO`, `ESCALAR_SIN_PRIVILEGIOS`, `RECOPILAR_EVIDENCIA_Y_ESCALAR`, `USUARIO_REPORTA_MEJORIA_NO_VERIFICADA`.
- `respuesta_sencilla`: explicación, una comprobación segura, qué observar, dos resultados posibles y la próxima pregunta. Cuando corresponde, agrega instrucciones para la mesa de ayuda y advertencia de no compartir secretos.
- `paso_para_principiante`: acción visible y sin privilegios.
- `pregunta_para_continuar`: qué dato o resultado pide al usuario.
- `mostrar_escalamiento` y `escalamiento`: vínculo con el plan **determinista**, no una conclusión del modelo.
- `evaluacion_automatica_aceptada`: indica la aprobación del contrato de salida, no que el usuario comprendió ni que la causa es correcta.
- `diagnostico_confirmado:false`, `accion_ejecutada:false` y `no_equivale_a_prueba_humana:true` permanecen explícitos.

Cuando alguien dice «no tengo permisos», la V4 informa que debe escalar **desde ese turno**, sin pedirle que consiga privilegios. Si dice «sigue fallando», la explicación muestra evidencia útil y derivación. Si dice «ya funciona», no cierra automáticamente el ticket ni presume una reparación: propone comprobar, sin cambios técnicos, la operación que antes fallaba.

## Condiciones de seguridad más estrictas

1. No basta con que `causa_confirmada=false`: el validador también rechaza afirmaciones textuales inequívocas como «se ha confirmado» o «la causa es…» cuando no existe prueba. Es una regla conservadora y puede rechazar condicionales ambiguos; el rechazo correcto lleva a revisión humana.
2. El input privado se sanea para contraseñas, claves, PIN, códigos de seguridad, encabezados Bearer, correos e identificadores contemplados por el redactor actual. Ninguna redacción automática reemplaza la revisión de privacidad de datos empresariales.
3. Ninguna instrucción a una persona sin privilegios puede pedir SQL, comandos, cambio de permisos, instalación ni suministro de secretos. Un plan rechazado nunca se convierte en PASS cambiando el texto de un campo booleano.
4. Si se repite un turno anterior a la V4 almacenado en SQLite, la respuesta obtiene la nueva presentación **sin reescribir el recibo original**. Un texto antiguo que no supere las reglas actuales no se entrega como guía válida: se muestra el paso conservador de atención humana.
5. Los controles de autenticación Bearer, loopback, idempotencia de turnos, vencimiento y segregación de la cola QA siguen vigentes.

### Límite de autenticación

El servicio tiene autenticación privada **a nivel de aplicación**, no autenticación individual de cada empleado final. La V4 sigue siendo una **función piloto interna supervisada**. Para exponerla en un portal multiusuario sería necesario un sistema de identidad por persona, autorización por caso y control de acceso a cada sesión, antes de mostrar tickets empresariales.

## Qué significa «progreso»

No existen barras que correspondan a diagnósticos reales certificados. `etapa` solo representa el estado del diálogo. «Comprobar», «aclarar» y «escalar» son decisiones del asistente, no puntos que prueben que el problema se arregló.

## Evaluación independiente y revisión humana

- **24 incidentes** de agosto y septiembre de 2026, los mismos de la evaluación V2, con tres turnos hipotéticos por caso.
- Verificadores de seguridad, replay, roles, petición de secretos, certeza causal, control de permisos y texto del usuario.
- La verificación de presentación puede reproducirse sin llamar nuevamente al modelo sobre las 72 respuestas previamente generadas. Ese replay **NO** se contabiliza como otra simulación real.
- Existe un generador de **paquete privado para revisión humana** con 24 casos, 72 turnos, rúbrica vacía y referencia a transcripciones anonimizadas. No hay calificaciones ni participantes inventados. El paquete contiene material operativo sensible y **requiere revisión de privacidad antes de distribuirse**.
- Ninguna tasa de aceptación automática significa tasa de causa raíz correcta. Se necesitan técnicos que verifiquen las hipótesis con evidencia y personas principiantes que sigan las instrucciones observando los resultados.

## Activación y reversión

El despliegue controlado utiliza un **SHA exacto** de `main` y genera el drop-in de systemd `40-guided-v4.conf`, sin sobrescribir `30-guided-v2.conf`. Mantiene el puerto loopback y el almacén privado de sesiones previo. Si falla el control de salud, autenticación, cola QA o permisos, elimina el nuevo drop-in y reinicia la V2 previa.

**No** habilitar reparaciones, consultas corporativas ni cambios de cuentas. El objeto del trabajo es explicar mejor y derivar con evidencia cuando no existen datos suficientes.
