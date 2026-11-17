# Evaluación demostrable de ELSE-ITIL-SUP: agosto de 2026 completo

**Cohorte:** 1.819 incidencias reales de agosto 2026. **Evidencia:** extracción ITIL original, diario privado de Qwen3.5 9B, revisión independiente automatizada Qwen 4B, atlas corporativo de módulos ITIL y nuevas lecturas SQL de solo lectura en ELSE62→ELSE70. **Fecha de auditoría complementaria:** 17 de noviembre de 2026.

## Dictamen ejecutivo

**Demostrado:** el sistema procesó la totalidad de las **1.819 solicitudes** de un mes operativo, 1.810 resultados cumplieron su contrato de salida (**99,51 %**), los 1.819 casos se pudieron cotejar contra los originales corporativos y el catálogo ITIL reconoció sus 166 módulos distintos. Se construyó un procedimiento determinista de validación de identidad empresarial con 1.819 decisiones y pruebas HMAC independientes. No se ejecutaron operaciones sobre los datos empresariales.

**No demostrado:** precisión causal del 99,51 %, reparación autónoma, coincidencia comprobada con soluciones históricas o un vínculo SQL nativo ITIL→objeto para todos los casos. La evidencia disponible solo sustenta **10 expedientes** con alguna PK empresarial tipada en la ruta comercial de su empresa, **sin probar su causa histórica ni su solución**. Presentar esta diferencia es parte de la veracidad de la demostración.

## 1. Universo, fuentes y separación de información

El universo no es una muestra ni una selección manual: se recuperaron los incidentes `ELSE70/dbITIL_D/dbo.taIncidente` con `FechaSolicitud >= 2026-08-01` y `< 2026-09-01`, ordenados por fecha e ID. Se cotejaron SHA del ID, fecha, código de servicio, código de módulo y texto original de los **1.819/1.819** registros contra el snapshot del 10/11. Las fechas extremas son **01/08/2026 08:06** y **31/08/2026 20:07**.

- Fuente original preservada: SHA-256 `48f6a30ca879de08bb419a3599d2594f91fcd3c0805de115e57337feeecdbde6`.
- Diario redactado ciego: SHA-256 `7200e6ea8f015b97475c482c9d128c0a0e2ed504b6e090421b99e4442566cfc0`.
- Diario previo de respuestas Qwen9B: SHA-256 `9a1e81478dbf89e3ba14ce759ceb3291bb0b1e977044a5fc98a305d0d08b01b1`.
- Revisión independiente histórica, por caso: SHA-256 `b44150f1f78a6284d65c83c667347c6df91f12621ebbf762711ed4c831006235`.

La generación previa de Qwen se hizo con la resolución histórica **WITHHELD**. **No se reentrenó ni se ejecutó de nuevo Qwen para esta fase de demostración**; sus resultados proceden de la campaña de noviembre 10–11 y fueron reanalizados de forma íntegra. El lector SQL corporativo y la recuperación de PK **no utilizan modelos**. No se trasladaron textos privados ni claves del cliente a GitHub.

## 2. Resultado completo de los 1.819 diagnósticos generados por Qwen

| Estado | Expedientes | Qué significa |
|---|---:|---|
| `MODEL_STRUCTURAL_PASS` | **1.810** | Estructura y contrato de respuesta aceptados |
| `INSUFFICIENT_REQUEST_TEXT` | 4 | Fuente redactada demasiado escueta |
| `MODEL_REQUIRES_TRIAGE` | 4 | Contrato no aceptado; requiere revisión |
| `MODEL_TRANSPORT_OR_JSON_FAILURE` | 1 | Fallo de transporte o formato |
| **Total** | **1.819** | **99,51 %** aceptados estructuralmente |

Un `PASS` estructural **no es un PASS de diagnóstico correcto, ni un ticket resuelto**. Esta medición prueba la producción y validación de planes técnicos en una cohorte mensual completa.

## 3. Evaluación histórica independiente, con límites explícitos

El segundo modelo revisó la relación entre el plan de Qwen9B y la nota histórica disponible, pero sus dictámenes **no son verdad clínica/técnica certificada**. No hubo adjudicación por humanos ni comprobación de la reparación en las bases empresariales.

| Evidencia de comparación | Casos |
|---|---:|
| `PEER_COMPLETED` | **1.655** |
| Sin nota histórica comparable | 154 |
| Respuesta de Qwen rechazada para comparar | 9 |
| Revisor no disponible | 1 |
| **Total** | **1.819** |

Entre los **1.655 casos comparados**, el revisor opinó: **46** `SUPPORTED`, **12** `CONFLICT` y **1.597** `NOT_DETERMINABLE`. De las notas, **57** se consideraron `ACTIONABLE`, **1.598** `VAGUE`, **154** `EMPTY` y 10 quedaron sin clasificación. Solo en las 57 notas accionables aparecen **46 apoyos preliminares, 7 conflictos y 4 indeterminados**; otros 5 conflictos se marcaron en notas vagas.

El revisor consideró los planes **342 específicos, 1.157 parcialmente específicos y 156 genéricos**, y registró **1.295** con prueba verificable presente frente a **360** con prueba faltante. Son evaluaciones automáticas, no auditorías humanas de precisión diagnóstica.

Una comparación léxica previa de los 1.810 planes estructuralmente aceptados obtuvo similitud TF-IDF media **0,04201** para pares del mismo caso frente a **0,00844** para un control barajado del mismo servicio. Esto muestra una asociación léxica exploratoria, **no** causalidad ni corrección de soluciones.

## 4. Auditoría SQL real y determinista de los 1.819

El programa `qa/aug2026_first100/AugFullMonthTypedRead.cs`, ejecutado físicamente en **ELSE62** con el proveedor `SIELSEAccesoDatos`, accedió a `ELSE70` mediante `SELECT` parametrizados, sin SQL generado por modelos. Una clave se acepta solo si aparece etiquetada explícitamente por tipo en el texto de la solicitud original, su empresa tiene ruta `eSistema.Comercial` verificada, la PK existe en la tabla oficial de su tipo y la sucursal coincide.

| Decisión de evidencia empresarial | Casos |
|---|---:|
| Sin referencia tipada explícita en la solicitud | **1.531** |
| Referencia explícita no encontrada en la base comercial oficial consultada | **162** |
| Empresa sin ruta comercial verificada | **116** |
| Exactamente una PK tipada observada en empresa/sucursal correcta | **9** |
| Dos o más PK tipadas observadas; objeto principal no determinado | **1** |
| **Total** | **1.819** |

Se observaron **201 expedientes** con alguna etiqueta de referencia tipada; el total de valores etiquetados fue 242. **1.703 expedientes** corresponden a empresas con rutas comerciales verificadas; **116** requieren certificación de ruta. Se ejecutaron **10 lotes SELECT** comerciales de PK, de los cuales resultaron **11 observaciones exactas** en **10 expedientes**. Los 1.809 restantes carecen de ese vínculo confirmado en el alcance consultado.

**La tasa de cobertura empresarial tipada es 10/1.819 = 0,55 %**, no la tasa de acierto del modelo. La ausencia de PK en la tabla consultada no demuestra ausencia universal del objeto. La lectura es de **noviembre 2026**, no una reconstrucción del estado de agosto. Ninguna PK permite afirmar la causa ni autoriza modificar datos.

### Evidencia de integridad

- Proyecto .NET 8: **0 errores, 0 advertencias** en compilación Windows.
- Recibo privado firmado, SHA-256: `7aebcc04c798128b0ba313374c76cf522fd0da2028455c5bb08eafc22bb1f637`.
- Segundo programa Python comprobó **HMAC**, SHA exacto del lector, 1.819 decisiones, vínculo del ticket, ruta de empresa, tipo y sucursal: `AUG_FULL1819_WINDOWS_INDEPENDENT_HMAC_AND_CASE_BINDING_PASS`.
- Un auditor adicional verificó las tres firmas de la evaluación mensual y de las muestras de **primeros y últimos 100**: coincidencia exacta de **200/200** expedientes en identidad, fuente, sucursal, empresa y decisión, con resultado `AUG_FULL1819_FIRST_LAST100_OVERLAP_HMAC_INDEPENDENT_PASS`.
- **0 cambios empresariales, 0 reparaciones certificadas, 0 claves de clientes divulgadas**.

## 5. Alcance funcional de SIELSE

El atlas ITIL capturado de SQL corporativo contiene entradas para **1.819/1.819** incidentes; hay **166 módulos distintos** en la cohorte. En 1.177 registros se declaró un alias de base y en 1.116 se localizaron archivos C# candidatos. Son **pistas de trazabilidad funcional**, no evidencia de que el binario candidato estuviera desplegado en agosto.

El mes tiene **28 días con incidentes**, 13 códigos de servicio y una distribución heterogénea; los más frecuentes fueron códigos **1 (967)**, **60 (165)**, **3 (152)**, **61 (152)**, **70 (124)** y **50 (113)**. No se inventaron nombres para los códigos.

## 6. Qué puede demostrar ELSE-ITIL hoy

| Capacidad demostrada | Resultado | Dictamen |
|---|---|---|
| Recibir y cotejar 1.819 solicitudes de un mes completo | 1.819/1.819 | **PASS** |
| Producir planes conformes a contrato | 1.810/1.819 = **99,51 %** | **PASS ESTRUCTURAL** |
| Mantener segregación del histórico y de claves privadas | Manifiestos, HMAC y negativa a escribir | **PASS DE CONTROLES EVALUADOS** |
| Determinar el módulo de origen ITIL | 1.819/1.819 en catálogo | **PASS DE METADATOS** |
| Identificar un objeto comercial por PK tipada autorizada | 10/1.819 | **COBERTURA LIMITADA** |
| Demostrar causa raíz verdadera por incidente | 0 certificadas | **NO DEMOSTRADO** |
| Demostrar reparación ejecutada y validada | 0 certificadas | **NO DEMOSTRADO** |

**Frase de demostración defendible:** *«En una evaluación retrospectiva de los 1.819 incidentes de agosto de 2026, ELSE-ITIL generó 1.810 propuestas que cumplieron el contrato estructural; auditamos los 1.819 expedientes contra SQL corporativo, con verificadores independientes y sin modificar sistemas de negocio. Seguimos separando la calidad del plan de la validación real de causa y reparación».*

**Frase que NO debe utilizarse:** *«ELSE-ITIL resolvió correctamente el 99,51 % de los incidentes»*.

## 7. Condición para una demostración de precisión diagnóstica

Para demostrar diagnóstico funcional, no solo formato, se necesita una **referencia verificable por expertos**. La vía más defendible es adjudicar a ciegas los **57 expedientes con nota histórica accionable** (y una muestra representativa de notas vagas), con al menos dos revisores competentes y reglas de desacuerdo, confirmación de datos corporativos `as-of` y criterios de verificación de cierre. Separar entrenamiento, evaluación y revisión; registrar por tipo de falla la prueba que corresponde. Las métricas posteriores deben incluir exactitud de causa, tasa de abstención apropiada, cobertura, evidencia de entidad, pasos ejecutables autorizados y cierre validado. No atribuir una precisión real al sistema hasta completar ese proceso.

## 8. Reproducción y archivos

- `qa/aug2026_first100/score_full1819_blind_history.py` — cobertura completa y comparaciones con diarios firmados por SHA.
- `qa/aug2026_first100/AugFullMonthTypedRead.cs` y `.csproj` — lector SQL real y recibo HMAC, de solo lectura.
- `else_dominance/qa_august_full1819_identity_authority.py` — consumidor fail-closed de recibo exacto, sin PK privadas y con autorización retrospectiva.
- `qa/aug2026_first100/verify_full1819_signed_windows.py` — verificador HMAC independiente de 1.819 expedientes.
- `qa/aug2026_first100/verify_full1819_cohort_overlap_windows.py` — comparación de las 3 ejecuciones HMAC con los primeros/últimos 100.
- `qa/aug2026_first100/score_full1819_module_catalog.py` — cobertura de módulos y repositorios candidatos.
- `data/2026_aug_full1819_*.json` — agregados sanitizados; no incluyen solicitudes, soluciones, clientes, claves privadas ni credenciales.
- `tests/test_aug2026_full1819_*.py` — pruebas adversariales sintéticas: pérdida de casos, fuga de gold, cambio de cohorte, empresa y sucursal equivocadas, falsos PASS y reparaciones ficticias.

**Estado del proceso activo:** el servicio de mesa de ayuda no se utilizó para modificar bases ni se le otorgó capacidad de reparación autónoma. La ejecución histórica de Qwen se conserva y no equivale a una nueva inferencia bajo los prompts actuales.
