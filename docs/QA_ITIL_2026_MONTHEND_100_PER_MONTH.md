# ELSE-ITIL-SUP — Últimos 100 incidentes de cada mes de 2026

**Corte:** 12 noviembre 2026. **Origen autorizado:** ELSE62 Windows QA, ELSE70 (dbITIL_D/dbo.taIncidente), elsecluster5. **Baseline:** main f282f133354479ee5b7c3e88740f51ce40f15238.

## Objetivo

Evaluar si los antecedentes históricos ayudan a reconocer objetos, campos y mecanismos específicos. Un expediente cerrado no equivale a reparación certificada. Toda esta fase es de lectura y diagnóstico, sin cambios de negocio.

## Selección y comprobación

La selección utiliza fechas parametrizadas y SELECT TOP(100) con orden FechaSolicitud DESC, CodigoIncidente DESC. Las solicitudes se recuperan primero; sus soluciones históricas se consultan por separado y se cotejan exactamente los hashes del mismo identificador corporativo.

**22 recibos** de 11 meses, firmados en Windows, volvieron a verificarse con HMAC SHA-256 en Linux. Los **900 incidentes seleccionados son distintos**.

Octubre y noviembre carecen de registros en esta fotografía de dbITIL_D QA. Septiembre solo llega al 16 de septiembre según sus fechas disponibles, lo cual limita la interpretación de «últimos del mes». No se presupone que la compañía dejara de generar incidentes, sino que esta fuente no los contiene. Diciembre es futuro respecto del corte.

## Resultados estructurales sobre los 900

| Mes 2026 | Total QA | Seleccionados | Dominio reconocido | Solución escrita | Referencia SQL en histórico | Concordancia SQL estricta, anclada en solicitud |
|---|---:|---:|---:|---:|---:|---:|
| Enero | 1 987 | 100 | 79 | 100 | 29 | 2 |
| Febrero | 1 799 | 100 | 83 | 100 | 35 | 1 |
| Marzo | 1 869 | 100 | 86 | 100 | 28 | 5 |
| Abril | 1 907 | 100 | 83 | 100 | 38 | 1 |
| Mayo | 1 714 | 100 | 89 | 100 | 29 | 3 |
| Junio | 1 621 | 100 | 82 | 98 | 25 | 4 |
| Julio | 1 689 | 100 | 89 | 98 | 33 | 2 |
| Agosto | 1 819 | 100 | 88 | 89 | 23 | 5 |
| Septiembre | 545 | 100 | 84 | 80 | 16 | 3 |
| Octubre | 0 | 0 | — | — | — | — |
| Noviembre (parcial) | 0 | 0 | — | — | — | — |
| **Total disponible** | | **900** | **763** | **865** | **256** | **26** |

Los 763 dominios representan **84,8 % de cobertura de enrutamiento**, no precisión diagnóstica. Con el requisito adicional de texto suficiente, 761/900 son elegibles para generar un plan con Qwen: elegible tampoco significa PASS.

El índice técnico previo de mayo encontró referencias del mismo módulo para 333/900 casos. La mejora exige que el texto del nuevo ticket también mencione un objeto o campo distintivo: 133/900 conservaron una pista. Entre esos 133, **26** coincidieron exactamente con referencias SQL escritas en su solución histórica; son coincidencias textuales de clase de acción, tabla y conjunto de columnas, **no causas certificadas**.

## Qué tan informativas son las soluciones históricas

Qwen 3.5 4B clasificó las 900 notas de forma separada, y las 104 categorizadas inicialmente como acciones específicas debían tener citas literales verificables. La distribución fue:

- 728 notas clasificadas como cierres genéricos.
- 35 notas vacías o sin solución escrita.
- 33 notas cuya clasificación no superó la validación.
- 104 notas clasificadas como específicas inicialmente, con una cita literal.

Una segunda validación determinista de las 104 citas indicó que **94** eran SQL escrito o referido (sin ejecución probada), **8** eran instrucciones o solicitudes y **2** narraban una acción técnica (sin verificación independiente). Así, las 104 etiquetas no son reparaciones probadas; tampoco las 26 coincidencias SQL son aciertos causales certificados.

## Separación entre conocimiento y evaluación

Los índices privados se construyeron solo con los primeros 300 casos de mayo de 2026. Los últimos 100 de mayo no coinciden con esos casos, igual que los otros meses seleccionados. Para enero-abril, es una evaluación retrospectiva utilizando información posterior: **no** representa conocimiento disponible en el momento histórico de esas incidencias.

Se añadió recuperación condicionada por solicitud:

- inspect_historical_procedures: no promueve patrones que solo comparten módulo; requiere ancla textual en un objeto o campo concreto.
- inspect_historical_mechanisms: exige simultáneamente referencia anterior del mismo módulo y mecanismo explícito en la solicitud; en caso contrario devuelve ABSTAIN.

Ambas herramientas son de solo lectura y muestran hipótesis documentales, nunca estado empresarial verificado.

## Verificación adicional del LLM

Se realiza por separado un submuestreo predeterminado de **10 casos de los últimos 100 de cada mes disponible** (ranks 1, 12, 23, 34, 45, 56, 67, 78, 89 y 100). Qwen 3.5 9B debe producir planes sin ver la nota histórica; posteriormente un evaluador distinto contrasta cada plan contra la nota. Esta prueba es de **90 casos**, no 900, y debe reportarse como tal.

### Resultado de la prueba generativa (90 casos)

Se completaron 90 diagnósticos de Qwen 3.5 9B, sin entregarle los históricos: **68 planes aceptados**, 17 aclaraciones y 5 rechazados. Estas 90 solicitudes se eligieron con posiciones predeterminadas en cada último centenar mensual; **no son 900 inferencias del LLM**.

Un evaluador Qwen 3.5 4B, al que se mostraron las notas históricas solo después de la prueba de Qwen 9B, devolvió 67 resultados provisionales validados y 23 rechazados por contrato. Entre los 67: **1 coincidencia específica candidata**, 25 relaciones parciales, 15 no relacionadas, 20 sin plan válido y 6 no evaluables. Una relación parcial puede indicar solamente el mismo dominio operativo. Ninguna equivale a causa comprobada ni a reparación.

Los reportes agregados están en data/2026_monthend_qwen9b_90sample.json; las propuestas y notas individuales permanecen privadas. La comparación posterior de modelos distintos **no constituye una verdad terreno humana**.

## Reproducción y límites

El lector QA .NET 8 es qa/monthend2026/MonthEnd100Read.cs, utilizando SIELSEAccesoDatos 3.24.11.27. La auditoría está en qa/monthend2026/evaluate_monthend.py; los informes públicos contienen solo totales por mes y hashes de recibos, sin textos, identificadores, SQL completo ni datos personales. Los originales están bajo almacenamiento privado del servidor autorizado.

**Resultado verificable:** 900 expedientes de nueve meses, 763 dominios reconocidos, 26 concordancias SQL textuales estrictas, **0 reparaciones o causas E2E independientemente certificadas**.
