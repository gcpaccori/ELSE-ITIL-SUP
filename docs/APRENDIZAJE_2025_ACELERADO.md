# ELSE-ITIL-SUP — Aprendizaje acelerado 2025 y examen final 2026

Fecha: 2026-11-03. Operación sobre `ELSE62` y `elsecluster5`, usando Servidores de Gabriel. **No se modifica ITIL, SIELSE ni el sistema de permisos.**

## Regla temporal obligatoria

El **año 2025 completo (enero a diciembre)** es el único universo de estudio y adaptación del especialista en esta fase. **2026 se reserva como conjunto de examen final**, después de concluir la cobertura de 2025 y aprobar la calidad de las lecciones. No incorporar las soluciones de 2026 a los prompts de entrenamiento, a los adaptadores LoRA ni a la selección de hiperparámetros.

En una etapa anterior se usaron 12 solicitudes de **agosto de 2026** como prueba exploratoria del primer LoRA, además de cinco pilotos de septiembre que ya fueron procesados por el modelo. Por esa exposición **no pueden contarse como examen ciego final**; el examen final tendrá que excluir esos casos, seleccionar una cohorte no vista y predefinir el protocolo.

La ejecución de `blind_exam.py` en `elsecluster5` fue bloqueada mediante una puerta de control que exige un artefacto explícito de finalización y revisión del estudio de 2025. Esto es una precaución operativa; por sí sola no equivale a una firma de aprobación institucional.

## Cambios ejecutados en ELSE62

La tarea existente **`ELSE-RIV-Continuous-Apprenticeship`** (Windows Task Scheduler) se actualizó en el mismo equipo y con la misma identidad de servicio. No se crearon duplicados.

| Parámetro | Anterior | Actual |
|---|---|---|
| Intento de inicio | Cada 15 min | **Cada 1 min** |
| Máximo por ejecución | 3 episodios | **8 episodios** |
| Tiempo objetivo de lote | 700 s | **255 s**, comprobado antes de abrir el siguiente caso |
| Instancias simultáneas | No | **No: IgnoreNew** |
| Ejemplos | Mezcla seudorrandómica de casos de 2025 | **Orden por fecha ascendente de enero a diciembre de 2025** |
| Student | Qwen 3.5 4B | Qwen 3.5 4B, GPU 7 |
| Revisor | Qwen 3.5 9B | Qwen 3.5 9B, GPU 6 |
| Corrección inmediata en casos rechazados | General | Solo una muestra determinista de 1/8; el resto conserva la crítica para revisión posterior |
| Examen de 2026 | Existieron pilotos previos | **Embargado durante los ciclos de estudio de 2025** |

Un disparador de 1 minuto **no implica una inferencia completada por minuto**: cuando la tarea sigue ejecutándose, Windows omite otro arranque y espera el siguiente. Los pasos de inferencia pueden superar el tiempo objetivo de lote cuando ya se inició un episodio.

No se alteraron los endpoints de inferencia de Qwen ni los modelos compartidos de ELSE CORE.

## Inventario y cobertura inicial

Fuente privada de QA: `cases_2025_redacted.jsonl`, 24,129 registros del año 2025. Se analizó todo el inventario, sin extraer textos al repositorio.

- **24,129** registros 2025 inventariados.
- **12,482** candidatos iniciales legibles y sujetos a filtros de privacidad/calidad.
- **11,647** no elegibles en esta pasada automática; requieren depuración o revisión. **No contarlos como aprendidos.**
- La cola de estudio ahora empieza en **enero 2025** y continúa hacia diciembre. Enero contiene **1,364** candidatos.
- Los 14 episodios anteriores al cambio de orden permanecen en el registro histórico; después de activar la frecuencia acelerada se comprobó el avance a **24 episodios únicos estudiados**. La cifra evoluciona durante las ejecuciones.
- Las lecciones que no pasan los controles son **rechazadas o quedan pendientes**, nunca se convierten automáticamente en verdades ni reparaciones certificadas.

El progreso agregado por mes se conserva localmente en `C:\Temp\ELSE_ITIL_LEARNING_20261103\curriculum_2025_status.json`. El cuaderno de episodios permanece privado en el mismo directorio. El programa de lectura revisa exclusivamente la exportación QA 2025; **no lee 2026**.

## Consolidación de pesos y evaluación

El primer adaptador LoRA de Qwen 4B se entrenó por separado, con 57 etiquetas históricas débiles de 2025 (32 pasos); **no está desplegado** ni representa una capacidad validada. Los ciclos de estudio generan diagnósticos, revisiones adversariales y propuestas de lección; **no actualizan pesos en cada inferencia**.

Solo debe iniciarse la evaluación final sobre casos nuevos de 2026 después de cubrir todos los meses de 2025, revisar casos no elegibles y las objeciones de los supervisores, consolidar la versión candidata y congelar parámetros, prompts, conjunto de evaluación y criterios de éxito. Un examen de 2026 no puede utilizarse para seguir ajustando el modelo y después presentarse como prueba ciega.

**Seguimiento:** [G1 — Ingesta](https://github.com/gcpaccori/ELSE-ITIL-SUP/issues/1) y [G2 — Atención y evaluación](https://github.com/gcpaccori/ELSE-ITIL-SUP/issues/2).

No se incluyen textos de tickets, nombres, credenciales, adaptadores, modelos ni conjuntos de entrenamiento en el repositorio.
