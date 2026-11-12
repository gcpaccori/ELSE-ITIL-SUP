# ELSE-ITIL — Hand NuGet dinámico con ciclo Qwen → O5 → Qwen (QA)

Fecha: 2026-11-09. Alcance: QA histórico septiembre 2026,
ELSE62 Windows, backend ELSE70/dbITIL_D. No es el listener HTTP activo ni V1.

## Capacidad nueva

Anteriormente la PR #360 verificaba recibos NuGet ya existentes.
La PR #12 permitía que Qwen pidiese consumir ese recibo preexistente.

Esta rama añade un ejecutor QA por demanda:

1. El operador inicia la prueba para uno de los 545 casos de septiembre
   autorizados mediante SHA-256.
2. Windows entrega al modelo solo la solicitud redactada, servicio y módulo,
   sin la solución histórica.
3. Qwen 9B solicita la herramienta exacta qa_exact_read con el query_id fijo
   ITIL_2026_09_CASE_EXACT_READ y el SHA del caso. Los argumentos extra,
   SQL, servidor o cambio de caso se bloquean antes de consultar.
4. Windows ejecuta una lectura NuGet nueva mediante SELECT fijo y parametrizado,
   limitada a una fila en ELSE70/dbITIL_D/dbo.taIncidente en septiembre 2026.
   Nunca lee DescripcionSolucion.
5. El recibo, su hash y el código fuente exacto se transfieren al clúster.
   O5 valida contrato, SHA y manifest O1; Guardian O13 ejecuta una
   verificación independiente y O15 emite su certificado de evidencia.
6. Solo después del PASS, Qwen recibe el dato nuevo y razona nuevamente.
   El diagnóstico está sujeto a un segundo evaluador de calidad.
7. Recibos y resultados quedan en carpeta privada; ninguna reparación ni
   entrenamiento se certifica automáticamente.

El piloto todavía se inicia desde una orden del operador QA. La lectura SQL
ocurre **después de la petición del modelo** dentro de ese proceso. El
listener habitual 127.0.0.1:18883 permanece intacto.

Dependencias:
- ELSE CORE PR #360, commit 313a45d3302dc552e67803380ad193bfd98bbcc2.
- ELSE-ITIL-SUP PR #12, commit 58f292a39b291a43d0a1189016cbd2100a9644bf.

## Resultados en casos reales (2026-11-09)

Se utilizaron tres expedientes distintos, de servicios 2, 1 y 70,
provenientes de la cohorte QA septiembre de 2026:

| Prefijo de SHA de caso | Consulta NuGet nueva | O5/O13/O15 | Diagnóstico |
| --- | --- | --- | --- |
| 714795f62f8382bd | una fila | PASS | DIAGNOSTIC_GUIDANCE |
| 0128b53454ddcb9e | una fila | PASS | NEEDS_HUMAN_TRIAGE |
| 02099c9add5020c7 | una fila | PASS | DIAGNOSTIC_GUIDANCE |

El segundo caso quedó bloqueado porque se mencionó ITIL.taIncidenteDerivacion
sin declararla entre las fuentes de ese procedimiento. No es fallo de NuGet:
es un rechazo correcto del verificador.

La auditoría volvió a validar los tres recibos y además ejecutó tres
negativos alterando los bytes de los recibos: 3/3 terminaron no-PASS y
con cero ejecuciones del Hand.

Resumen:
- 3/3 nuevas lecturas QA exitosas.
- 3/3 verificaciones O5/O13/O15 PASS.
- 2/3 diagnósticos aceptados, 1/3 derivado a revisión.
- 0 causas raíz certificadas, 0 reparaciones, 0 promociones a entrenamiento.
- Roles de los tres diagnósticos pendientes de contraste con la matriz real.

Recibos privados (no se incorporan al repositorio):
/home/u23u/else_itil_dynamic_nuget_qa_20261109/runs/

Auditoría:
 /home/u23u/else_itil_dynamic_nuget_qa_20261109/independent_audit_v2.json

Catálogo privado sin soluciones históricas:
C:\Temp\ELSE_ITIL_DYNAMIC_NUGET_20261109\qa_allowlist.private.jsonl

## Reproducción

Preparar en ELSE62 el catálogo autorizado a partir del export QA existente,
ejecutando el script qa/qa_dynamic_nuget_windows.py con la acción prepare,
--source para el archivo cases_2026_sep_oct.private.jsonl y --out para
qa_allowlist.private.jsonl.

Ejecutar el mismo script con la acción run y parámetros:
- --case-sha: SHA-256 exacto de uno de los 545 casos.
- --allowlist: ruta al catálogo privado autorizado.
- --out-root: carpeta privada de recibos de salida.
- --project: qa/LiveITILQARead.csproj.
- --source-file: qa/LiveITILQARead.cs.

El script Python invoca NuGet .NET 8 desde Windows después de validar la
llamada de herramienta solicitada por Qwen. Envía solo el caso redactado,
la petición y el recibo al clúster autorizado. No transfiere soluciones humanas.

Auditar desde el clúster con:
python -m else_dominance.qa_dynamic_nuget_audit
y los argumentos --root, --source, --expected y --out.

La implementación debe ejecutarse con PYTHONPATH que incluya el checkout
ELSE-ITIL-SUP de esta rama y el checkout ELSE CORE PR #360.

## Lo que todavía NO está conectado

El servicio HTTP existente no despacha por sí mismo peticiones a Windows.
Falta un worker/dispatcher persistente, auditable, antes de dar por cerrado
el ciclo desde la interfaz habitual.

El Hand actual investiga el registro ITIL y sus metadatos, no el estado
operativo de SAP, los permisos de usuarios ni los dispositivos de red.
Para ello hacen falta Hands específicos de lectura autorizada.

La retroalimentación humana de la Preview PR #13 permanece pendiente.
Ninguno de estos resultados autoriza aprender o cerrar tickets sin prueba
funcional y revisión técnica.

## Matriz de pruebas / CI

Las pruebas puras de ELSE-ITIL-SUP funcionan en GitHub Actions sin instalar
ELSE CORE. Las 13 parametrizaciones que ejercitan el Hand real se omiten
en ese runner cuando falta la dependencia externa PR #360; **no se sustituyen
por mocks de O5 que pudieran dar un PASS ficticio**.

En el entorno QA autorizado, con ambos checkouts exactamente fijados,
se ejecutaron todas las pruebas (180 PASS). La evidencia más fuerte siguen
siendo las tres consultas Windows NuGet reales y el re-verificador
O5/O13/O15 con tres negativos de pre-ejecución.
