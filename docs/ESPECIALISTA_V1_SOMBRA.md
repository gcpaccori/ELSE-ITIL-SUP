# ELSE-ITIL Especialista V1 — activación en sombra

Operación: 2026-11-03. Servidor elsecluster5.

## Servicio privado de atención

- URL: http://127.0.0.1:18883; acceso local y token existente.
- Principal: Qwen3.5 9B GPU6, puerto localhost 18782.
- Respaldo: Qwen3.5 4B original GPU7, puerto localhost 18781.
- Persistencia privada: support_specialist_v1_private/attention.sqlite.
- API existente: GET /health y POST /v1/support, autenticada.
- Estado operativo: source_access=USER_SUBMITTED_ONLY; repairs_enabled=false.
- Comando reproducible en primer plano: bash ops/run_specialist_v1.sh.

Se ejecutaron dos incidencias sintéticas en la API: acceso SIELSE 403
con sesión válida e impresora alcanzable por red con cola atascada.
En ambas, model_selected=primary, status=DIAGNOSTIC_GUIDANCE,
tres pasos condicionados, cero banderas de esquema/seguridad,
executed_changes=false y certified_repair=false.

No se probó una reparación real ni existe acceso automático a la BD corporativa.

## Aprendizaje 2025 con 4B estudiante y 9B mentor

Módulo: else_dominance/apprenticeship_v1.py.
Runner: tools/v1_2025_apprentice.py.
A partir de los 3,857 casos privados prefiltrados de 2025 se seleccionaron
240, veinte por mes, de enero a diciembre, mediante orden determinista.
Las soluciones humanas de 2025 permanecen ocultas al estudiante hasta que
éste genere su procedimiento. El mentor las recibe expresamente como
ANTECEDENTES NO VERIFICADOS; no puede certificar una reparación.

Se ejecutó piloto real de dos casos de enero 2025. Resultado:
2 HUMAN_REVIEW_PENDING, 0 errores, 0 ejemplos aprobados para entrenar y
0 reparaciones certificadas. Los artefactos de expediente, solución y
respuestas quedan exclusivamente en el directorio privado
/home/u23u/else_itil_sup_run/experiments/specialist_v1_curriculum_20261103_v2.

El primer intento falló por discrepancia entre campos originales y campos
normalizados. Se corrigió el contrato y se repitió con éxito; la primera
ejecución queda como error de QA y no como episodio aprendido.

## Puertas de promoción

El LoRA experimental anterior NO está desplegado. Se observó bajo cumplimiento
de formato en julio 2026, examen en ejecución de forma independiente.
Todo 2026 queda excluido de nuevo entrenamiento y selección de ejemplos.

Para habilitar un nuevo SFT no basta una preferencia automática de Qwen9B.
ProcedureMemory, ya presente en ELSE-ITIL-SUP, requiere verificaciones
independientes y un recibo de resultado comprobable antes de marcar VALIDATED.
Hasta contar con esa evidencia el material V1 es sólo DRAFT_NEEDS_REVIEW.

## Próxima ampliación

1. Añadir herramientas de diagnóstico REAL de solo lectura y recibos de
   procedencia confirmada, sin SQL libre ni privilegios nuevos.
2. Revisar los borradores con evidencia real y verificar la idoneidad técnica.
3. Entrenar un LoRA BF16 aislado usando exactamente el contrato JSON del servicio.
4. Medir diagnóstico y cierre funcional con ensayos independientes.

No publicar descripciones, soluciones, credenciales, tokens ni pesos privados.
