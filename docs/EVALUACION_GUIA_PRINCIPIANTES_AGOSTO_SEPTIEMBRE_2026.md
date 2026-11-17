# ELSE-ITIL-SUP — ¿Puede diagnosticar y guiar a una persona sin experiencia?

**Evaluación controlada del 17/11/2026, agosto + septiembre 2026.**

## Dictamen en lenguaje sencillo

**NO ESTÁ DEMOSTRADO QUE YA PUEDA GUIAR BIEN A UNA PERSONA PRINCIPIANTE.**

Sí puede preparar hipótesis y planes estructurados para analistas, y los modelos locales reales permiten reformular indicaciones cuando se les presenta el historial. Pero el servicio actual **no guarda conversaciones entre turnos**: cada llamada a `/v1/support` es una solicitud individual. El harness QA reconstruye el contexto anterior en una nueva solicitud para estudiar la conducta del modelo; **esto no equivale a un diálogo persistente desplegado**.

**No se está evaluando si repara solo**, ni se le pide hacerlo. El objetivo es orientar, distinguir hipótesis con pruebas, adaptarse a dudas de usuario y escalar con evidencia.

## Dos capas de prueba: universal e interactiva

| Prueba | Agosto | Septiembre | Qué demuestra |
|---|---:|---:|---|
| Planes históricos existentes examinados con la misma rúbrica | **1.819** | **545** | Cobertura documental de 2.364 casos |
| Cumple el contrato estructural original | **1.810** | **508** | Formato, no acierto ni comprensión |
| Plan contiene un paso con palabra de pantalla/interfaz | **466** | **229** | Indicio textual de operación visible, no necesariamente realizable |
| Plan asigna algún paso a un rol de usuario final (detección textual) | **0** | **80** | Orientación explícita de destinatario |
| Paso asignado al usuario, realizable en pantalla, con resultado y sin administración (rúbrica estricta) | **0** | **5** | Indicador conservador de autoservicio; podría subcontar |
| Plan con todos los pasos a «Responsable autorizado por confirmar» | **1.814** | **0** | Brecha de destinatario en salida de agosto |

### Conclusión de esta capa

En la campaña de agosto, **1.814 planes** asignan sus procedimientos a un «responsable autorizado por confirmar». No distinguen de forma explícita un bloque de instrucciones al usuario y otro al especialista. Por eso no basta citar un porcentaje de éxito estructural. Septiembre incorpora más roles específicos, pero la mayoría de pasos sigue siendo técnica.

Estos son **indicadores automáticos por patrones**, no un examen de comprensión realizado con usuarios. La diferencia entre agosto y septiembre no permite inferir evolución causal: los dos conjuntos se generaron con prompts, fuentes y criterios estructurales parcialmente diferentes.

## Simulación de conversación

Se eligieron casos de forma determinista sin consultar la respuesta histórica: **12 solicitudes por mes**, de tres niveles de longitud (3 breves, 4 medianas y 5 extensas por mes), con diversidad de códigos de servicio. La selección procede de los **1.819 y 545** originales anonimizados.

Cada incidente seleccionado se presenta al soporte real a través del código operativo `else_dominance.support_desk.make_attention`, con **Qwen 9B** primario y el fallback registrado por el servicio. Se generan **tres respuestas del sistema por caso**:

1. Usuario principiante presenta el problema y pide diagnóstico explicado con comprobaciones que puede hacer sin permisos.
2. Usuario hipotético dice «no entiendo el primer paso» y solicita explicación sencilla.
3. Usuario hipotético dice «la comprobación no ayudó, no tengo privilegios» y pide alternativa, evidencia y escalamiento.

El proceso utiliza **el modelo real de Qwen**, no respuestas pregrabadas. Pero las respuestas del usuario son **sintéticas**: nadie operó un dispositivo real ni comprobó que la causa sugerida fuese verdadera. El servicio no conserva el contexto y el runner debe proporcionarlo de nuevo.

La ejecución final generó **72 respuestas auténticas de Qwen** para **24 casos** (12 por mes, 3 turnos), bajo el código de atención del servicio. Las tres respuestas por caso se cuentan incluso si algún turno fue rechazado y se registra explícitamente ese rechazo. No se atribuye ejecución en sistemas.

| Prueba de interacción | Agosto (12 casos) | Septiembre (12 casos) |
|---|---:|---:|
| Respuestas aprobadas estructuralmente y por el gate actual (sobre 36) | **36** | **33** |
| Primera respuesta que incluye un paso concreto realizable por usuario final | **1** | **0** |
| Segunda respuesta que incluye un paso concreto realizable por usuario final | **3** | **3** |
| Tercera respuesta que incluye evidencia no sensible y derivación (marcadores textuales) | **10** | **8** |
| Casos que superan TODO el indicador automatizado estricto de guía a principiante | **1** | **0** |

**Interpretación:** la diferencia de texto entre la segunda y la tercera respuesta solo prueba que el modelo cambió su lista de pasos, no que comprendió mejor ni acertó la causa. El indicador estricto combina estructura, seguridad, una instrucción de interfaz dirigida al usuario, respuesta no idéntica y escalamiento. **1/24 es un indicador automatizado de candidatos para revisión, NO una tasa de éxito real del 4,17 %.**

**No aprobados:** tres turnos de septiembre fueron rechazados por el gate del servicio y no se promovieron a orientación satisfactoria. Los otros planes recibieron comprobaciones de seguridad y de formato; estas no certifican su contenido técnico.

Se conservó un piloto inicial en almacenamiento privado y **se excluyó** de las métricas porque incluía etiquetas del mecanismo QA que sesgaban las respuestas. La ejecución final usa preguntas naturales de principiante, sin etiquetas internas ni resultados ficticios declarados como hechos.

## Errores cualitativos observados en planes reales (sin divulgar datos privados)

- **Demasiado técnico al inicio:** frente a solicitudes de usuario final, el asistente a veces comienza recomendando que un analista consulte catálogos, permisos o tablas, en lugar de iniciar por lo que la persona puede ver en pantalla.
- **Ajuste al pedir aclaración:** en un escenario de derivación de documentos, tras recibir «no entiendo», el asistente pasó de revisar catálogos a solicitar captura del mensaje visible y posteriormente a escalar el caso. Este comportamiento es útil, pero fue necesario solicitar una segunda explicación.
- **Controles de empresa aplicados donde no corresponden:** en un caso de alta de usuario, solicitó PK/recibos comerciales como condición de la guía. El control de identidad empresarial es necesario para atribuir objetos de negocio, no debe convertirse en prerrequisito indiscriminado para explicar cómo reportar una falla.
- **No inventar observaciones:** cuando un usuario simulado dice «sigue fallando», el asistente no debe concluir que una consulta administrativa devolvió cero resultados. El harness no dispone de ese dato.

Estas son observaciones de revisión del contenido por un asistente, **no valoraciones de usuarios reales ni certificación humana**.

## Qué es necesario cambiar antes de demostrarlo al público

1. **Conversación nativa y persistente:** cada caso debe tener estado, historial mínimo, respuestas recibidas y próxima pregunta; nunca fingir resultados que el usuario no dio.
2. **Dos capas de guía:** «Para ti, usuario final» con acciones por interfaz y resultados visibles; «Para soporte autorizado» con verificaciones técnicas y aprobaciones separadas.
3. **Una prueba por turno:** preguntar o pedir una comprobación concreta, explicar qué significa cada resultado y seleccionar la siguiente rama.
4. **Seguridad por defecto:** sin contraseñas, tokens ni documentación de identidad innecesaria en el chat; sin comandos, SQL o cambios administrativos exigidos a principiantes.
5. **Criterio de aceptación verificable:** dos especialistas y personas principiantes deben valorar claridad, acciones ejecutables, decisiones según respuesta y seguridad en una muestra representativa. Registrar tasa de abstención apropiada. Un evaluador automático no sustituye esa prueba.

## Fuentes, trazabilidad y seguridad

- Agosto, 1.819 respuestas históricas Qwen9B: SHA-256 `9a1e81478dbf89e3ba14ce759ceb3291bb0b1e977044a5fc98a305d0d08b01b1`.
- Septiembre, 545 respuestas Qwen9B privadas exportadas con redacción: SHA-256 `a7a69ec49f0d3e6cc24daf4c5200b8bd7716ea23570b79833809e297e5ca366d`.
- Rúbrica documental: `qa/novice_dialogue/full_month_plan_guidance_audit.py` y agregado `data/2026_aug_sep_full2364_novice_plan_audit.json`.
- Simulación real: `qa/novice_dialogue/real_novice_simulation.py` y `data/2026_aug_sep_novice_dialogue_simulation.json`.
- Verificación independiente de 72 respuestas: `qa/novice_dialogue/verify_novice_dialogue.py` y `data/2026_aug_sep_novice_dialogue_independent.json`.
- Scripts de exportación anonimizados desde ELSE62, material fuente y respuestas privadas guardadas fuera de GitHub.

**Seguridad:** ninguna solución histórica se mostró al modelo generador durante la prueba, y no se ejecutaron cambios sobre bases, usuarios, instalaciones ni producción. Las transcripciones con datos empresariales permanecen privadas en el clúster. No se publica información de clientes.

**Veredicto de liberación para atención autónoma de principiantes:** **NO APROBADO TODAVÍA**. El sistema sí aporta estructura y procedimientos condicionados para el soporte interno, pero todavía necesita simplificación, ramificación visible para no especialistas, memoria de conversación y validación con personas reales.
