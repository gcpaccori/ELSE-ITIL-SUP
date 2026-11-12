# ELSE-ITIL-SUP — Dominio maestro de SIELSE, soporte y evidencia

**Fecha:** 12 de noviembre de 2026. **Ámbito:** gcpaccori/ELSE-ITIL-SUP, repositorio, SQL QA de ELSE62/ELSE70 y recibos HMAC. No hay reparaciones automáticas autorizadas.

## 1. Arquitectura y autoridad de cada fuente

El proyecto es un investigador de soporte TIC: conserva antecedentes, identifica módulos, propone comprobaciones, consulta fuentes autorizadas y somete conclusiones a evidencia independiente. La generación de un JSON correcto no acredita una reparación.

| Capa | Evidencia y componentes comprobados | Lo que NO certifica |
|---|---|---|
| ITIL | dbITIL_D.dbo.taIncidente, módulo, servicio, derivaciones; memory.py y qa_itil_native_lifecycle.py | No es una FK oficial a OT, cobranza o campañas |
| Clasificación | functional_domain_v2.py y functional_investigator_v2.py | Un dominio o plan correcto no equivale a causa |
| Orquestación | agent.py, sources.py y operational_cli.py | El LLM no puede crear SQL libre ni seleccionar credenciales |
| Comercial | SIELSEAccesoDatos, eSistema.Comercial, CodigoSucursal y tablas de negocio | CodigoEmpresa de ITIL no demuestra la base propietaria |
| Gerencial | dbGerencial_D; posibles copias comparativas | No es prueba de fuente transaccional ni reparación |
| Distribución | dbDistribucion_D y su propia taOrdenTrabajo | No es intercambiable con taOrdenTrabajo comercial |
| Históricos | historical_procedures.py y historical_mechanism_matching.py | Una sentencia pegada en la nota no prueba ejecución |
| Seguridad | HMAC/SHA, QA read-only, verificadores, O5/Guardian cuando aplica | No habilita mutaciones empresariales |

**Regla principal:** empresa ITIL, empresa/sucursal del objeto comercial y base con una copia son identidades distintas. La primera auditoría erró al imponer una equivalencia entre las tres.

### Rutas reales verificadas

En ELSE70, SIELSEAccesoDatos.Obtener(eSistema.Comercial, empresa) devolvió, con verificación mediante DB_NAME(): empresa 1 → dbComercial001_D; empresa 4 → dbComercial004_D; empresa 100 → dbComercial100_D. La auditoría previa de agosto confirmó rutas para empresas 1 y 3 en otra cohorte. Estas pruebas no certifican todas las empresas en todo momento, ni una relación formal del ticket con la orden.

### Contratos empresariales a distinguir

| Objeto | Identidad y campos relevantes | Precaución |
|---|---|---|
| Orden comercial | taOrdenTrabajo, CodigoOrdenTrabajo, CodigoSucursal, estado, subtipo y centro | Comercial y Gerencial mostraron distintos valores del centro de una misma OT |
| Cobranza | taCobranza, CodigoCobranza, CodigoSuministro, caja, sucursal y fechas | Dos PK históricas se localizaron en dbComercial001_Diario, sin enlace desde solicitud |
| Campaña | taCampanaSupervision, código y estado | Una comprobación de OT no sustituye una comprobación de campaña |
| Padrón | taPadronRuc | Una identidad extraída solo de una nota no autoriza seleccionar un cliente de varias filas |
| Auditoría OT | taOrdenTrabajoAuditoriaCambio, taOrdenTrabajo_ModificacionIN | Se requieren objeto, campo, valor antes/después y sello temporal |
| Documentos | taDocumentoTramiteAdjunto | Las menciones en notas no implican ejecución ni un objeto único |

Distribución tiene taOrdenTrabajo homónima pero de esquema diferente; por ejemplo, no tiene CodigoCentroAtencion. Nunca se debe utilizar el mismo SELECT indiscriminadamente contra tablas de sistemas distintos.

## 2. Estado de la evidencia real a noviembre de 2026

| Evaluación | Universo | Resultado verificable |
|---|---:|---|
| Últimos 100 expedientes de nueve meses de 2026 | 900 | Historial: 104 notas juzgadas específicas, 728 genéricas, 35 vacías, 33 juicios rechazados; 94 notas específicas tenían citas SQL escritas, no ejecutadas de forma verificada |
| Junio completo | 1.621 | Solicitudes/históricos firmados y enlazados 1.621/1.621; 1.318 dominios detectados, 303 UNKNOWN |
| Transferencia temporal mayo→junio | 500 antecedentes de mayo → 1.621 de junio | 72 expedientes con coincidencias documentales exactas, que se agrupan en **13 firmas distintas** y 76 relaciones expediente/familia; 95 coincidencias menos específicas de operación y tabla |
| Autor Qwen 9B y juez Qwen 4B | 100 casos ciegos de junio | 72 planes conformes, 22 aclaraciones y 6 rechazos; cinco SAME_MECHANISM provisionales |
| Investigación SQL de los cinco SAME_MECHANISM | 5 | Tres OT recuperadas, dos en base comercial de ruta actual verificada y una solo en Gerencial; cero cambios históricos certificados |
| Ampliación a OT y cobranzas | 57 de los 72 | 22 OT y 35 cobranzas; 41 sin PK explícita segura, 9 con PK solo en la nota, 3 con PK igual en solicitud y nota, 3 ambiguos y 1 con conflicto |
| SQL QA de los 57 | 13 bases de ELSE70 | 12 casos con coincidencia de PK: 10 en Gerencial y 2 en dbComercial001_Diario; solo 3 con identidad de solicitud corroborada |

**Importante:** los primeros cinco casos proceden del juicio de un modelo; los otros 57 se seleccionaron retrospectivamente por similitud SQL. No sumar ambos grupos ni llamar al estudio retrospectivo una evaluación ciega independiente.

## 3. Por qué 72 coincidencias no equivalen a 72 habilidades

La deduplicación de notas firmadas de junio observó **13 familias de procedimientos** en los 72 casos, con 76 relaciones expediente/familia porque ciertos tickets contienen más de una operación documentada.

| Procedimiento mencionado, no ejecutado de forma acreditada | Expedientes |
|---|---:|
| UPDATE de CodigoCaja en taCobranza | 35 |
| UPDATE de CodigoEstadoOrdenTrabajo en taOrdenTrabajo | 13 |
| DELETE de taDocumentoTramiteAdjunto | 10 |
| Llamada a spRegistrarOTReconexion | 4 |
| Otras firmas de OT, contrato, suministro y procedimientos | 14 relaciones entre casos y familias |

Los 35 casos de cobranza corresponden al módulo real **Digitación de Cobranza** (0102100100000). Una familia puede repetirse en decenas de tickets sin que el especialista conozca todavía la clave, el estado previo o la condición precisa de aplicación. Para evaluar diversidad técnica se deben informar **familias distintas, casos, parámetros anclados y mecanismos funcionales** por separado.

Informe verificable: data/2026_june72_procedure_family_taxonomy.json. Todas las firmas provienen de menciones históricas; no son evidencia de ejecución de SQL.

### Contratos de investigación propuestos para las 13 firmas

Las comprobaciones siguientes son **requisitos de diseño sugeridos**, no procedimientos corporativos aprobados ni acciones ejecutadas.

| Firma histórica observada | Comprobación diferencial propuesta |
|---|---|
| taCobranza / UPDATE CodigoCaja (35) | PK, sucursal, caja origen/destino, unicidad, fechas y relación con expediente; sin PK, abstenerse |
| taOrdenTrabajo / UPDATE CodigoEstadoOrdenTrabajo (13) | OT, sucursal, estado actual, subtipo, transición permitida y auditoría |
| taDocumentoTramiteAdjunto / DELETE (10) | Identificador adjunto/trámite, retención, autorización y respaldo; no ejecutar |
| spRegistrarOTReconexion (4) | Firma oficial del procedimiento, parámetros, estado OT y prerrequisitos; no invocar sin contrato |
| taOrdenTrabajo / CodigoContratista y CodigoContratistaContrato (3) | Vincular OT con contratista y contrato activos |
| taOrdenTrabajo / FechaEjecucionProgramacion (3) | Verificar objeto, programación y cronología |
| taOrdenTrabajo / FechaFactibilidadEjecucion (2) | Verificar estado y factibilidad del mismo objeto |
| taSuministro / estado y FechaAnulacion (1) | PK, autorizaciones y contrato vinculado |
| taContrato / estado, motivo y FechaAnulacion (1) | Contrato exacto, motivo válido y postcondición |
| taSuministroGuardar (1) | Parámetros y firma oficial desconocidos; no ejecutar |
| taOTLecturaMenor / CodigoMedidor (1) | Identidad de medidor, suministro y OT |
| taOTCambioMedidorRegistroPorCodigo (1) | Firma, contexto y protocolo de medidor certificados |
| taOrdenTrabajo / CodigoContratistaContrato (1) | Contrato exacto y evidencia de asignación |

Son 13 tipos de firma, **no 13 funciones automáticas listas para ejecutarse**. Para aprobar una habilidad se necesitan contrato de entrada, conector seguro, pruebas positivas/negativas, evidencia de postcondición, permisos y reversión.

## 3. Escalera de evidencia

| Grado | Qué demuestra | Conclusión autorizada |
|---|---|---|
| E0 | Solicitud y síntoma, sin objeto claro | Reporte, hipótesis o aclaración |
| E1 | Nota histórica o procedimiento previo | El técnico documentó cierta operación; no que se ejecutara |
| E2 | PK inequívoca corroborada desde solicitud y contexto | Objeto mencionado con suficiente precisión, aún sin estado |
| E3 | PK única en ruta corporativa verificada y lectura QA | Estado actual observado; no estado de junio |
| E4 | Auditoría confiable de objeto/campo/antes/después/fecha | Cambio histórico documentado por evidencia independiente |
| E5 | Cambio autorizado, postcondición empresarial y validación humana | Reparación certificada dentro del alcance permitido |

Ningún expediente estudiado de esta serie ha alcanzado E4 o E5. Un UPDATE en el historial, una FechaModificacion o una fecha de cierre ITIL no acreditan por sí solas transición ni reparación.

## 4. Procedimiento de investigación por expediente

1. Fijar identidad ITIL, SHA de solicitud, código de módulo, fecha, servicio y empresa ITIL.
2. Mantener la solución histórica cerrada durante cualquier prueba ciega de modelos.
3. Extraer entidad y clave sin invención: CodigoOrdenTrabajo, CodigoCobranza u otra PK explícita. Si es de la nota histórica solamente, etiquetar NOTE_ONLY, no promover a identidad de solicitud.
4. Resolver empresa/sucursal empresarial por fuentes corporativas y rutas verificadas. No convertir automáticamente CodigoEmpresa ITIL en base comercial.
5. Validar fuente, tabla, columna y tipo por esquema. No mezclar OT comercial y OT Distribución.
6. Consultar solo SQL parametrizado y allowlisted; registrar 0/1/múltiples/error/no accesible sin concluir ausencia global.
7. Comparar estado de la base transaccional con Gerencial, señalando discrepancias. Nunca elegir la copia favorable a una hipótesis.
8. Validar cronología: auditoría, CDC retenido, backups de época, journal de aplicación o pruebas equivalentes.
9. Clasificar coincidencia documental, comprobación de procedimiento, estado observado, causa comprobada y reparación por separado.
10. Si la identidad o la evidencia faltan, ABSTAIN y pedir la comprobación humana concreta. No ejecutar cambios.

## 5. Brechas técnicas detectadas

- **Identidad:** en 57 expedientes documentales, 45 no contienen bajo el extractor actual una PK segura utilizable en una consulta: 41 sin clave, 3 ambiguos y 1 contradictorio. Esto no implica que otros formatos más ricos no permitan recuperarla, sino que todavía no hay contrato seguro para hacerlo.
- **Enrutamiento:** una búsqueda en Comercial001 dio falsos negativos; algunas OTs se localizaron en Comercial004, Comercial100 o Gerencial. Dos cobranza aparecieron en Comercial001_Diario.
- **Semántica de negocio:** se comprobó un error de objeto del juez Qwen (OT frente a campaña) y otro plan que omitía validar pliego tarifario.
- **Temporalidad:** cuatro bases SQL QA tenían CDC deshabilitado actualmente y msdb de ELSE70 no mostraba respaldos finalizados en junio para ellas. No se excluyen archivos externos, backups de otros servidores o histórico de aplicación.
- **Calidad de notas:** muchos cierres son genéricos y las referencias SQL se escriben en texto. Solo un registro de ejecución o transición ligado a la misma entidad puede elevar la certeza.
- **Generalización:** modificar reglas a partir de junio obliga a medir después en una cohorte posterior intacta y no vista.

## 6. Mejoras prioritarias para acercarse al técnico histórico

**P0, seguridad y rutas.** Contratos separados para empresa ITIL, sucursal comercial, base de transacción y copia Gerencial. Verificar coherencia de nombre, esquema y ruta corporativa antes de ejecutar SELECT. Un 0 de Comercial001 nunca demuestra ausencia global.

**P1, extracción controlada.** Ampliar patrones de solicitud (HTML, referencias de OT y suministro, documentos, cobranza, múltiples IDs) conservando estados explícitos de ambiguo, conflicto, clave solo histórica y clave verificada. No usar el histórico para adivinar la identidad en predicciones ciegas.

**P2, evidencia histórica.** Buscar mediante acceso autorizado respaldos externos, auditoría/CDC archivados o transacciones de aplicación. Se requieren PK, campo, antes/después, fecha, rol y prueba de postcondición.

**P3, evaluación independiente.** Benchmarks por dominio, selección de objeto, tipo de base, hipótesis de causa, check discriminante, validez del plan y coincidencia histórica independiente. La métrica de reparación real queda separada.

**P4, cambios supervisados.** Solo después de evidencias E4 y contrato de cambio reversible, desarrollar un flujo de intervención controlada fuera de producción, con autorización y rollback. No habilitar mutaciones desde el servicio persistente actual.

## 7. Evidencia trazable

- Informe de junio completo: docs/QA_ITIL_JUNE2026_FULL_1621_HISTORICAL_AUDIT_20261112.md.
- Cinco casos Qwen: docs/QA_ITIL_JUNE2026_FIVE_BUSINESS_BEFORE_AFTER_AUDIT_20261112.md.
- Problema de rutas: docs/QA_ITIL_JUNE2026_CROSSDB_ROOTCAUSE_RECOVERY_20261112.md.
- Nuevo lector read-only: qa/june2026_57/June57SourceAndTargetsRead.cs.
- Selección HMAC: qa/june2026_57/build_private_57_manifest.py.
- Score HMAC/independiente: qa/june2026_57/verify_and_score_57.py.
- Prueba adversarial privada: qa/june2026_57/private_adversarial_57.py.
- Resultado agregado sin datos personales: data/2026_june57_business_source_trace.json.
- Deduplicación de familias: qa/june2026_57/score_72_procedure_families.py y data/2026_june72_procedure_family_taxonomy.json.
- Pruebas CI: tests/test_june2026_57_business_trace.py.

**Estado correcto:** hemos recuperado más fuentes y sabemos dónde fallaban las búsquedas, pero no se ha certificado todavía una reparación histórica. Dominar realmente la operación exige relaciones de negocio verificadas, causa discriminada, evidencia temporal y postcondiciones, no etiquetas optimistas.
