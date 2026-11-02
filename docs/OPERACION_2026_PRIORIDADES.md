# ELSE-ITIL-SUP: cobertura 2026 y prioridades de atención

Fecha de comprobación: 2026-11-02. Fuente: QA ELSE70/dbITIL_D, **solo agregados**.

## Resultado retrospectivo, sin falsos cierres

Se reejecutó dentro de ELSE62:

```text
dotnet run --project C:\Temp\ELSE_TIC_BENCHMARK_QA_2026_ALL\QAResolutionBenchmark.csproj --configuration Release
```

El evaluador consulta incidentes en memoria, con antecedentes de 2025. No exporta
descripciones, respuestas individuales ni datos personales. No prueba soluciones con IA,
ni ejecuta cambios. Los valores consolidados están en
`data/qa_2026_monthly_aggregate.csv` y se validan con
`python -m else_dominance.year_2026 --input data/qa_2026_monthly_aggregate.csv`.

| Tipo de oportunidad | Casos | Regla operacional |
|---|---:|---|
| P1: consenso histórico de familia de actuación | 1,155 | Prioridad para **investigación supervisada**; validar causas y vigencia. No equivale a una acción correcta. |
| P2: antecedente similar sin consenso suficiente | 12,390 | Razonamiento LLM, pruebas discriminantes, verificación de sistema y versión; no copiar soluciones. |
| P3: sin antecedente relacionado | 1,405 | Investigación desde cero, delimitar evidencia necesaria, reglas del dominio y escalamiento concreto. |
| **Total del conjunto QA** | **14,950** | Cero reparaciones certificadas por IA. |

Existe acuerdo de *familia textual de actuación* en **292 de 367** casos evaluables
dentro de los 1,155 candidatos. **NO** debe presentarse como tasa de reparación
(son etiquetas léxicas y los demás casos no tienen resultado comparado).

## Cobertura mensual comprobada

2026-01 a 2026-08 según copia QA y 2026-09 parcial (545 casos). Octubre y
noviembre: la copia QA anteriormente consultada reportó cero registros, lo cual
NO demuestra ausencia de actividad en producción. Diciembre 2026 aún no ocurrió.

## Qué significa atender

Estados admitidos por orden de evidencia:

- `INVESTIGATION_REQUIRED`: solicitar fuentes concretas, pruebas discriminantes y actor.
- `AUTHORIZED_HANDOFF_REQUIRED`: solución posible, pero requiere aprobación y rol validado.
- `PROCEDURE_FOR_HUMAN_REVIEW`: plan estructuralmente revisable, jamás cambio ejecutado.
- `REJECT`: fuente/rol inventado, restricción no autorizada, mutación, falsedad de cierre.

Las clases P1–P3 son **prioridades históricas** y NO predicen estos estados
operativos por sí mismas.

## Controles incorporados

`else_dominance.support_quality` verifica que:
1. Las referencias de evidencia citadas existan en el expediente suministrado.
2. Los roles administrativos inventados y órdenes de restricción injustificadas sean rechazados.
3. Las frases negativas (como "no congelar") no se confundan con órdenes.
4. Una prueba futura redactada como reparación ya hecha se rechace si no existe recibo.
5. El resultado **nunca** certifique reparación ni determine la matriz real de permisos.
6. La asignación de un grupo resolutor requiera comprobación contra una matriz autorizada externa.

Prueba manual reproducible con datos ficticios:

```bash
python -m else_dominance.support_quality \
 --plan /RUTA_PRIVADA/engineer.json \
 --evidence-registry data/mock_evidence_registry.json
```

Se verificó sobre dos versiones de un runbook sintético producido por Engineer
(ELSE CORE): ambos fueron rechazados, por falsa atribución de rol/mutación propuesta
o por cierre en pasado sin prueba funcional. El anterior auditor LLM había producido
un `PASS_CONDITIONAL` sobre estas respuestas; por ello no puede ser el único juez.

## Bloqueo pendiente para los incidentes individuales

**No se ha ejecutado el LLM sobre los 14,950 tickets reales**: no existe en el
ejecutor una cohorte de solicitudes individuales depurada y autorizada para el
modelo. El booleano `privacy_reviewed=true` NO constituye evidencia independiente
de aprobación. No se extraerán expedientes por una vía alternativa para eludir
los controles de acceso. G1/G2 siguen abiertos hasta disponer de autorización
verificable, rol/permiso y ejecución E2E bajo QA.

La siguiente puerta es **procesamiento dentro del límite autorizado de datos**,
follow-up humano y evaluación ciega por mes. No confundir pruebas de software
o inferencia sobre casos ficticios con tickets corporativos atendidos.
