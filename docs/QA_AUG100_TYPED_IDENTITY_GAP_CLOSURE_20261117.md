# ELSE-ITIL-SUP — Auditoría y límite de autoridad de las primeras 100 solicitudes de agosto

**Fecha:** 17 de noviembre de 2026. **Modo:** 100/100 solicitudes originales, excluyendo `DescripcionSolucion`; lectura de ELSE62 hacia ELSE70, de solo lectura, con firma HMAC y verificación independiente. No se usó Qwen ni otro modelo para la extracción, consulta o certificación. Los diagnósticos anteriores no se reutilizaron para escoger claves.

## Resultado que reemplaza la interpretación inicial

La evaluación anterior de PR #45 descubrió **16 de 100** tickets con números de 19 dígitos encontrados como PK de OT/cobranza en alguna de 13 bases, en filas con `CodigoSucursal` coincidente. **La interpretación de esos números como relaciones autorizadas de empresa fue demasiado fuerte**. Al rastrear la procedencia de 105 observaciones con sucursal coincidente:

- 79 observaciones: `dbComercial001_Diario`
- 5: `dbComercial200_D`
- 8: `dbDistribucion_D`
- 13: `dbGerencial_D`

**Ninguno de los 16 casos** tiene una coincidencia de ese tipo en la base Comercial oficialmente enrutada para su `CodigoEmpresa` (1→`dbComercial001_D`, 3→`dbComercial003_D`). Esto **no** prueba que las coincidencias de otros sistemas sean falsas: Distribución, Gerencial y copias tienen contratos diferentes. **Sí** impide llamarlas vinculaciones comerciales ITIL→objeto autorizadas por simple coincidencia numérica.

## Paso ejecutado de manera determinista, sin IA

1. Se cotejaron los 100 casos de ITIL QA por SHA del código de incidente, fecha, servicio, módulo y texto original contra la extracción congelada.
2. Se inspeccionó `DescripcionSolicitud` completa hasta 12.000 caracteres, conservando el prefijo original exportado de 1.800. Solo se aceptaron números junto a etiquetas inequívocas como `suministro`, `OT`, `cobranza`, `reclamo`, `medidor` o `solicitud FISE`.
3. Se separaron rutas por `CodigoEmpresa`: 1 y 3 tienen proveedores `eSistema.Comercial` verificados en el atlas y exigidos por el lector. Los otros códigos se abstienen. Se comprobaron por SQL `SELECT` parametrizados las PK tipadas correspondientes. Para medidor se exige `taMedidor.CodigoSuministro → taSuministro.CodigoSucursal`.
4. Los números de DNI, teléfonos, fechas y tickets genéricos no se promovieron a PK. La existencia de un código en otra sucursal tampoco se aceptó.
5. El lector produjo **100 decisiones**, con recibo privado firmado e inmutable, comprobado independientemente mediante HMAC de 32 bytes, SHA del código y contrato de identidad/empresa.

| Decisión final por expediente | Cantidad |
|---|---:|
| `NO_EXPLICIT_TYPED_BUSINESS_KEY_IN_REQUEST` | **82** |
| `EXPLICIT_TYPED_KEY_NOT_FOUND_IN_COMPANY_DB` | **7** |
| `COMPANY_PROVIDER_ROUTE_NOT_CERTIFIED` | **11** |
| `SINGLE_EXACT_TYPED_PK_QA_OBSERVATION` | **0** |
| `MULTIPLE_EXACT_TYPED_PKS_NO_PRIMARY_INFERRED` | **0** |
| Total | **100** |

El texto de fuente contenía etiquetas tipadas en 11 casos; 89 casos pertenecen a empresas 1 o 3 con ruta comprobable y 11 a otros códigos. Tres consultas tipadas SQL fueron ejecutadas para los candidatos en esas rutas, sin filas PK coincidentes. Estos resultados no son fallos del código ni prueba de inexistencia universal de los objetos: son **ausencia de evidencia afirmativa dentro del alcance exacto**.

## Cierre alcanzado vs. brecha abierta

**Cerrado y probado:** la brecha de *falsos vínculos autorizados*: no se promueven claves genéricas, archivos, copias, Distribución o Gerencial a PK Comercial; cada caso se etiqueta de modo determinista, con HMAC, empresa, sucursal, tipo y fuente. Se bloquea que un modelo elija el objeto principal o presente estos 16 cruces como reparaciones.

**No cerrado:** la *recuperación de una entidad real* para esos 100: faltan identificadores en 82 solicitudes, 7 claves no devolvieron PK en la ruta oficial y 11 exigen definir y verificar las rutas de sus empresas. La ausencia de claves puede requerir investigación por módulo, contratos de aplicación, lectura autorizada del estado operativo y pruebas de un técnico. **No se puede transformar esa ausencia en 100 enlaces verdaderos sin datos adicionales**.

**Módulos:** los 100 están registrados en el directorio ITIL del atlas; 63 tienen alias de base declarados y 60 tienen archivos C# candidatos. Esas rutas son pistas de investigación, no identidad causal certificada ni despliegue/versionado confirmado.

## Implementación

- `qa/aug2026_first100/AugFirst100TypedRead.cs` — lector firmado de origen y seis tipos de PK comerciales.
- `qa/aug2026_first100/verify_typed_signed_windows.py` — verificación HMAC/empresa/sucursal del recibo Windows.
- `qa/aug2026_first100/audit_generic_company_scope_windows.py` — desclasificación de cruces genéricos anteriores.
- `else_dominance/qa_august_identity_authority.py` — consumidor de recibos firmados que devuelve únicamente decisiones seguras por expediente exacto y requiere habilitación retrospectiva explícita del operador.
- `tests/test_august_identity_authority.py` — diez pruebas adversariales: fraude de PK/sucursal/empresa, falsas reparaciones y cambios de HMAC/caso.
- `data/2026_aug_first100_company_typed_authority.json` — resumen agregado sin PII.
- `docs/QA_AUG100_MODEL_EVIDENCE_PROTOCOL_20261117.md` — instrucciones que deben usar Qwen/otros asistentes **solo después de que el validador independiente haya emitido el resultado**, nunca como sustituto de este.

El servicio persistente no recibe permiso SQL de escritura. No se renovaron autorizaciones, ni se expusieron datos personales, ni se certificó ninguna reparación histórica. Las fuentes privadas y la firma permanecen en ELSE62; GitHub solo contiene código y agregados.
