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
- Un intento de crear un túnel `localhost` desde `ELSE62` hacia el puerto local del modelo se quedó sin respuesta dentro del tiempo del conector; llamadas posteriores a `ELSE62` también agotaron el tiempo de cola. **No se obtuvo una inferencia comprobable de septiembre** en esa prueba.
- Por tanto: **545/545 solicitudes individuales recuperadas en QA; 0/545 inferencias LLM del mes confirmadas; 0 reparaciones certificadas.**

## Operación pendiente, sin desarrollo de software

1. Restablecer un canal de ejecución confiable entre el entorno QA que conserva las solicitudes y el modelo on-premises, con tratamiento de datos autorizado, sin enviar material crudo a GitHub.
2. Revisar la anonimización, especialmente las tres coincidencias de posibles secretos y los identificadores libres.
3. Presentar cada solicitud al especialista sin exponerle la solución histórica, y conservar una respuesta privada por `case_ref`.
4. Revisar diagnósticos, actuaciones y pruebas de cierre; reflejar explícitamente lo pendiente de autorización o de verificación.
5. Publicar solo métricas y recibos agregados, no descripciones ni soluciones corporativas.

**No confundir recuperación de expedientes, triage por palabras clave o disponibilidad de Qwen con atención o reparación finalizada.** Los expedientes individuales permanecen privados en QA.
