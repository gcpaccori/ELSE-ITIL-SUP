# Registro de soporte operativo — 3 de noviembre de 2026

**Estado de la misión:** `G2_SEPT_2026_INCIDENT_INTAKE` · seguimiento [G1](https://github.com/gcpaccori/ELSE-ITIL-SUP/issues/1) y [G2](https://github.com/gcpaccori/ELSE-ITIL-SUP/issues/2). La operación se realiza con **Servidores de Gabriel**, sin cambiar el código de soporte ni la base corporativa.

## Conectividad y consulta QA comprobadas

- `ELSE62` respondió y ejecutó programas .NET preexistentes por `host_run`.
- `FullYearITIL.csproj` y `QAResolutionBenchmark.csproj` comprobaron el destino **ELSE70 / dbITIL_D** y la disponibilidad de 545 solicitudes en septiembre 2026. Octubre/noviembre no aparecen en esa copia.
- Se ejecutó el lector existente `KnowledgeExport.csproj` (código ya presente antes de esta intervención), que usa `SIELSEAccesoDatos` y rechaza servidores o bases distintos a QA. Resultado confirmado:

| Exportación interna en ELSE62 | Registros | Bytes reportados |
|---|---:|---:|
| Antecedentes de 2025 (`cases_2025_redacted.jsonl`) | 24,129 | 26,707,531 |
| Solicitudes de enero–septiembre de 2026 (`holdout_requests_2026_redacted.jsonl`) | 14,950 | 12,421,308 |
| Septiembre de 2026 (subconjunto del archivo anterior) | **545** | No se creó un archivo aparte |

**Ubicación privada de los archivos originales del lector:** `ELSE62:C:\Temp\ELSE_TIC_KB_QA_2025\`. Los archivos **no están en este repositorio**. El de solicitudes 2026 presenta, entre otros, los campos `case_ref`, `opened_at`, `service_code`, `module_code`, `classification_code`, `origin_code`, `status_code`, `request_text`. La solución humana de 2026 no aparece en esa exportación.

## Controles de integridad aplicados al subconjunto de septiembre

El conteo se efectuó en `ELSE62` sobre el archivo local, sin mostrar contenido individual:

| Comprobación | Resultado |
|---|---:|
| Filas 2026 totales | 14,950 |
| Solicitudes septiembre 2026 | **545** |
| Referencias de caso duplicadas en septiembre | **0** |
| Solicitudes vacías en septiembre | **0** |
| Longitud máxima de solicitud de septiembre, caracteres | 4,775 |
| Solicitudes que contienen un patrón de secreto potencial tras la redacción inicial | **3** |

El último indicador **no demuestra que haya tres credenciales reales**; es una señal de revisión. La anonimización por expresiones regulares de `KnowledgeExport` es básica y no acredita eliminación de nombres u otros identificadores libres. No transmitir ni publicar automáticamente el corpus como “anónimo” sin revisión.

## Familias de solicitudes encontradas — triage por palabras clave

| Familia indicativa (no clasificación definitiva) | Tickets con coincidencia |
|---|---:|
| Accesos / identidad | 170 |
| Impresión / equipos | 71 |
| Red / VPN | 64 |
| Aplicación / SIELSE | 235 |
| Comercial / facturación | 136 |
| Correo / ofimática | 237 |
| Sin coincidencia en estas familias | 129 |

**Las categorías se superponen.** No sumarlas para inferir número de tickets. La coincidencia de una palabra clave no identifica la causa, no autoriza una acción ni implica resolución.

## Atención e inferencia LLM

- `elsecluster5`: Qwen 4B `127.0.0.1:18781`, Qwen 9B `127.0.0.1:18782`, mesa de ayuda `127.0.0.1:18881/health=READY`; verificaciones previas.
- Se comprobó `ssh -o BatchMode=yes u23u@elsecluster5 hostname` desde `ELSE62`: conexión básica **PASS**.
- Un intento inicial de crear un túnel persistente se quedó sin respuesta. Se recuperó el agente y se usó **SSH por solicitud**, con datos UTF-8 codificados en base64 por la entrada estándar hacia `curl` ejecutado en `elsecluster5`. El endpoint Qwen 9B local respondió correctamente, sin exponer el puerto a la red.
- Se seleccionaron **cinco solicitudes individuales, reales y distintas de septiembre**, de perfiles técnicos de acceso, equipos, red y proceso comercial. Se filtraron coincidencias obvias de secretos antes del envío. **No** se proporcionó al modelo la solución humana de 2026. Las respuestas permanecen privadas en `ELSE62`, en ficheros `itil_sep_*.private_result.json`.
- **5/545 inferencias individuales reales confirmadas**: todas devolvieron JSON con 3 hipótesis/pruebas y/o 3 acciones condicionadas según la plantilla; la primera muestra fue revisada con controles estructurales equivalentes. Las cuatro restantes se guardaron explícitamente como `PLAN_REVIEWABLE` por comprobación básica de campos, no certificación funcional. Cinco referencias de caso **únicas**, cero flags de estructura en las comprobaciones aplicadas, `resuelto=false` y `ejecutado=false` en las cinco.
- **Resultado global:** 545/545 solicitudes recuperadas en QA; **5/545 analizadas por Qwen 9B**; **0 reparaciones ejecutadas o certificadas**. El resto del mes está pendiente. Estos cinco planes requieren revisión técnica y evidencia adicional para considerarse atenciones cerradas.

## Operación pendiente, sin desarrollo de software

1. Utilizar el canal SSH privado verificado por solicitud (sin túnel persistente), con tratamiento de datos autorizado y sin publicar el contenido corporativo.
2. Revisar la anonimización, especialmente las tres coincidencias de posibles secretos y los identificadores libres.
3. Ampliar de los cinco pilotos a las solicitudes restantes, sin exponer al modelo la solución histórica, y conservar una respuesta privada por `case_ref`.
4. Revisar diagnósticos, actuaciones y pruebas de cierre; reflejar explícitamente lo pendiente de autorización o de verificación.
5. Publicar solo métricas y recibos agregados, no descripciones ni soluciones corporativas.

**No confundir recuperación de expedientes, triage por palabras clave o disponibilidad de Qwen con atención o reparación finalizada.** Los expedientes individuales permanecen privados en QA.

## Identidad de los archivos exportados (sin revelar contenido)

- `cases_2025_redacted.jsonl`: SHA-256 `b0ff2a2e718cf3628de167ad556597e6285e0898ed46f267016cb0284c59ba87`.
- `holdout_requests_2026_redacted.jsonl`: SHA-256 `f204854798e1a7bfbfd213c6c30b38dfe7cce958d320755cda156f29739c3816`.
- Las huellas se calcularon sobre los archivos **privados** en ELSE62, después de la exportación. No dan acceso a sus textos y permiten identificar exactamente la cohorte.
- **No se subió ninguna solicitud, solución, token ni respuesta privada al repositorio.**
