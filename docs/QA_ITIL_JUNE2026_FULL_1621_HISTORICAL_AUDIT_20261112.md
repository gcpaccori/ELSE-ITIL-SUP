# ELSE-ITIL-SUP — Evaluación histórica de TODO junio de 2026

**Corte de evaluación:** 12 de noviembre de 2026. **Rango SQL:** `FechaSolicitud >= '2026-06-01' AND FechaSolicitud < '2026-07-01'`. **Fuente real:** ELSE70 / `dbITIL_D.dbo.taIncidente`, acceso QA de solo lectura mediante ELSE62 y SIELSEAccesoDatos 3.24.11.27.

**Estado de este informe:** contraste estructurado del mes COMPLETO, con una muestra adicional incompleta de planes Qwen 9B. Las cifras son indicadores de concordancia documental y no de reparaciones ejecutadas.

## 1. Integridad de fuentes y cobertura

- **1.621/1.621 incidentes de junio de 2026** leídos con orden `FechaSolicitud DESC, CodigoIncidente DESC`, sin limitar el SQL a `TOP 100`.
- Dos productos separados, firmados mediante HMAC-SHA256: las **solicitudes sin soluciones** y, en una extracción posterior, los **históricos de solución**.
- Identidades de casos, posiciones y fechas verificadas entre ambas extracciones: **1.621/1.621**.
- Contraste independiente con los recibos anteriores de los últimos cien de junio: **100/100** coincidencias tanto en identidad y hash de solicitud como en hash de nota histórica.
- Todas las 1.621 solicitudes contienen descripción no vacía.
- **1.610/1.621** tienen texto histórico de solución; **1.612/1.621**, fecha de respuesta; **1.605/1.621**, fecha de cierre.
- El proceso de extracción no ejecutó operaciones empresariales modificadoras.

Recibo de solicitudes: `b1303359fb72aee6720fba660555fe6a8332cb1af26232239d19650061dab5fd`.

Recibo histórico: `cf071c227432996c50a328e03703c28b851ce883235b46f0bfb60f979398ae10`.

Los documentos individuales, los textos y las firmas completas permanecen en el servidor QA privado; no se incluyen en este informe ni se publican.

## 2. Cobertura de enrutamiento de todo el mes

| Resultado por solicitud | Incidentes |
|---|---:|
| Total contrastado | **1.621** |
| Código de módulo reconocido por directorio corporativo | 1.621 |
| Dominio funcional identificado por el enrutador determinista | **1.318** |
| Dominio funcional no identificado (`UNKNOWN`) | **303** |
| Casos elegibles para ensayo de planes LLM por dominio y texto suficiente | **1.312** |

Los principales dominios inferidos fueron: órdenes de trabajo comerciales (**438**), cajas/cobranzas (**121**), facturación (**111**), personal (**89**), materiales (**65**), correo (**57**), suministros/consultas (**55**), gestión documental (**56**) y medidores (**52**).

**Advertencia:** enrutamiento no equivale a diagnóstico correcto. Los 303 casos `UNKNOWN` están incluidos en el denominador, y no se excluyen para elevar artificialmente los porcentajes.

## 3. Qué documentan las soluciones históricas

| Indicador de notas históricas | Expedientes |
|---|---:|
| Texto de resolución no vacío | 1.610 |
| Alguna referencia SQL reconocible por patrones amplios | 536 |
| Mención SQL estructurada (tipo de operación/tabla/campos) | **462** |
| Referencia textual de recomendación/instrucción (heurística, no excluyente) | 359 |
| Narración de acción pasada reconocida (heurística, no excluyente) | 115 |

Las categorías de notas pueden superponerse. Un `UPDATE`, `DELETE`, `EXEC` o `SELECT` **escrito** en el ticket es una **referencia documental**, no un registro de ejecución. Las fechas de cierre y las narraciones de técnicos tampoco certifican por sí solas un cambio empresarial.

## 4. Evaluación temporal frente a antecedentes de mayo (sin fuga de junio)

Se compararon, para **cada uno de los 1.621 casos**, patrones de SQL presentes en incidentes de mayo **anteriores al 1 de junio**. Las predicciones se obtuvieron utilizando módulo y texto de la solicitud; solo después se contrastaron con la nota de solución del **mismo** incidente de junio. Se midió la igualdad de **tipo de operación + tabla + conjunto de campos**.

| Métrica documental sobre los mismos 1.621 incidentes | 300 antecedentes mayo | 500 antecedentes mayo |
|---|---:|---:|
| Predicciones con patrón SQL sustentado por la solicitud | 299 | 302 |
| En ambos lados hay alguna referencia SQL estructurada | 160 | 160 |
| Coincidencia de tipo de operación y tabla | **95** | **95** |
| Coincidencia exacta de operación, tabla y campos | **69** | **72** |
| Reparación empresarial ejecutada y certificada | 0 | 0 |

El corpus ampliado de 500 provino de **cinco cohortes previas de mayo**, cada una con solicitud/histórico firmados y 100 casos distintos. La mejora frente a los 300 anteriores fue **+3 concordancias exactas**, un incremento modesto.

**Lectura correcta de los resultados:** hay **72 coincidencias exactas documentales**, no cero. No obstante, eso no demuestra que la SQL citada se ejecutase, ni que fuera apropiada para el objeto exacto, ni que se haya reparado el incidente. Las 95 coincidencias de tabla/operación también incluyen casos cuya lista de campos difiere.

## 5. Experimento ciego Qwen 9B — estado comprobado

Se preseleccionaron **100 posiciones sistemáticas distribuidas entre el primero y el último incidente de junio**, no solamente los últimos cien. El autor Qwen 9B recibió únicamente la solicitud anonimizada y el nombre de módulo verificado; **no recibió el histórico de solución**. La validación local del plan exige comprobaciones discriminantes, estado `NOT_READ`, ejecución `NOT_EXECUTED` y citas ancladas a la solicitud.

Al último estado verificable del registro privado, **85 de las 100 posiciones** tenían resultado:

| Salida de Qwen 9B, en 85 casos comprobados | Casos |
|---|---:|
| `FUNCTIONAL_DRAFT_CONTRACT_PASS` | **60** |
| `CLARIFICATION_REQUIRED` | **19** |
| `FUNCTIONAL_DRAFT_REJECTED` | **6** |
| **Total de planes/abstenciones procesados** | **85** |

**No se han contabilizado los 15 restantes ni se ha completado en este informe un juicio independiente Qwen4B para todos esos 85 planes.** Por tanto, las 60 aprobaciones son **validez de contrato de un borrador diagnóstico**, no 60 coincidencias históricas ni 60 soluciones.

La última ejecución se interrumpió al perderse la conexión con el servidor. Se conserva el diario individual para reanudar sin duplicar posiciones, pero **no se certifica como completa la muestra de 100**.

## 6. Hallazgos y prioridades

1. El enrutador puede asignar dominio a **1.318/1.621** solicitudes, pero hay 303 sin un sistema bien identificado. Se necesita mejorar esa cobertura sin inventar contexto.
2. Las **72 coincidencias exactas** con menciones de SQL histórico son una señal de transferencia desde mayo, pero el salto de 300 a 500 antecedentes solo aporta tres coincidencias adicionales. Mejorar la representación de mecanismo y la vinculación al objeto parece más importante que agregar indiscriminadamente más notas.
3. **462** históricos contienen referencias SQL estructuradas, pero su calidad como evidencia de intervención es heterogénea. Para demostrar reparación hacen falta contrato de aplicación, objeto exacto, estados previos y posteriores y comprobación independiente de ejecución.
4. Una evaluación independiente de los planes contra el histórico debe distinguir coincidencia de mecanismo, coincidencia parcial de proceso, nota genérica, referencia SQL no ejecutada y caso no evaluable. No se debe convertir un juicio de modelo en verdad de negocio.

**Situación del código:** los lectores y evaluadores específicos de junio quedaron preparados y ejecutados en el servidor QA, pero, por interrupción de la conexión, no se incorporan como código fuente en esta PR de documentación. El informe no afirma que exista CI del nuevo lector ni que la batería Qwen de 100 se haya terminado.

**Conclusión:** contraste estructurado **1.621/1.621**, con **72 concordancias exactas de mecanismo SQL documentado** al entrenar con mayo; **0 reparaciones empresariales ejecutadas por el especialista y certificadas**. Esas cantidades miden aspectos distintos y deben informarse por separado.
