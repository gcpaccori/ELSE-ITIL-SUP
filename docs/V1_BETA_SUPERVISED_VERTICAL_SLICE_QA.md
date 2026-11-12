# ELSE-ITIL-SUP: V1 Beta supervised vertical slice (QA)

Fecha: 10 de noviembre de 2026. Estado: QA ejecutable, sin despliegue en producción.

## Alcance

El endpoint POST /v1/beta/investigate acepta únicamente un SHA perteneciente a los 100 expedientes autorizados de febrero de 2026. Para los 16 casos que contienen una OT única reportada y disponen de un recibo original, realiza:

1. Validación nativa O5/O13/O15 del recibo ITIL y del lector exacto Feb100ExactRead.cs.
2. Validación nativa e independiente O5/O13/O15 del segundo recibo OT/SAP y del lector exacto Feb100SapOtRead.cs.
3. Transmisión al modelo Qwen9B exclusivamente de las tres observaciones E1, E2 y E3 verificadas.
4. Validación determinista de fuentes, ausencia de modificaciones, pasos condicionales y estado de rol.
5. Persistencia auditada de la respuesta y estado PENDING_TECHNICIAN_REVIEW, o NEEDS_HUMAN_TRIAGE si no supera los controles.

El número OT proviene de texto redactado. No existe todavía un join oficial ITIL↔Distribución. Tres órdenes aparecen en la tabla QA específica, trece no aparecen; ello no prueba ausencia fuera de estas tablas. Las consultas NuGet de los 16 casos se ejecutaron anteriormente. El slice revalida esos recibos SIN consultar SQL nuevamente; no es una lectura productiva en tiempo real.

## Contrato V1.1 de roles y vinculación

Como aún no existe una matriz oficial cargada, el campo responsable de cada paso debe ser exactamente: Responsable autorizado por confirmar.

Los campos del plan vinculacion_comercial_verificada, rol_oficial_validado, ejecutado y confirmado deben ser false. Si hay una declaración contraria, la respuesta se rechaza. Ningún plan concede permisos ni afirma una reparación.

## API QA

Servicio local de usuario else-itil-beta-supervised-qa.service en 127.0.0.1:18886. El servicio 18883 no se sustituye.

- GET /health: salud del servicio sin datos corporativos.
- POST /v1/beta/investigate: cuerpo JSON con case_sha256.
- GET /v1/beta/result/{case_sha256}: respuesta de Qwen verificada.
- GET /v1/beta/status/{case_sha256}: estado de revisión.
- GET /v1/beta/summary: agregados.
- POST /v1/beta/review: case_sha256, reviewer_id, reviewer_secret, decision y note.

Se requiere el bearer privado del servicio para los endpoints de negocio. La revisión humana exige además un roster de revisores aprobado y credenciales independientes; no está configurado todavía. Decisiones disponibles: USEFUL_FOR_TECHNICIAN, NEEDS_MORE_EVIDENCE e INCORRECT_OR_UNSAFE. Ninguna equivale a cierre funcional o reparación.

## Evidencia privada

Ruta: /home/u23u/else_itil_beta_vslice_qa_20261110

Recibos originales: sap_ot_original_receipts.private/
Auditoría O5 de 16 casos: sap_ot_o5_real16_audit.json
Campaña HTTP original: beta_http16_e2e_summary.json
Campaña HTTP V1.1: beta_http16_e2e_v11_summary.json
Ledger técnico: beta_supervision_v11.sqlite
Auditoría independiente definitiva: beta_v11_independent_audit.json

Las rutas y recibos reales, datos de tickets y resoluciones permanecen en QA; no se incluyen en Git.

## Criterios pendientes para liberar V1 Beta

- Matriz oficial de roles y equipos responsables, sin inferencias del modelo.
- Clave comercial verificable de relación ITIL↔OT, no solo mención textual.
- Revisión humana de al menos 30 casos distintos con validación de la utilidad y pruebas de cierre. Actualmente solo hay 16 casos OT elegibles.
- Worker que realice consultas SAP/OT nuevas por solicitud, en lugar de reutilizar únicamente recibos históricos.
- Aprobación y fusión ordenada de PR apiladas, CI de integración y monitoreo.
- Interfaz visual y política de seguridad corporativa, fuera de este slice técnico si se decide incluirlas.

V1 Beta técnica supervisada en QA no equivale a liberación corporativa de V1 Beta.



## Resultado de auditoría definitiva V1.1

La auditoría independiente de la campaña HTTP V1.1 verificó:

| Indicador QA | Resultado |
|---|---:|
| Expedientes elegibles para dos Hands reales | 16 |
| Investigaciones HTTP finalizadas | 16/16 |
| Recibos ITIL O5/O13/O15 revalidados | 16/16 |
| Recibos SAP/OT O5/O13/O15 revalidados | 16/16 |
| Planes aceptados por contrato V1.1 | 16/16 |
| Planes para triaje por falla contractual | 0 |
| OT existentes en tabla específica consultada | 3/16 |
| SQL nuevo durante el replay | 0 |
| Nombres de equipos oficialmente aprobados | 0 |
| Relaciones ITIL-OT certificadas por business-key | 0 |
| Revisiones humanas reales | 0 |
| Causas raíz verificadas | 0 |
| Reparaciones confirmadas | 0 |

La métrica 16/16 es una tasa de **cumplimiento contractual sobre la
muestra elegible**, no de precisión de causa ni resolución.
No se infiere que las otras 84 incidencias puedan consultar SAP/OT:
para ellas el flujo se abstiene con REQUIRES_OT_CORPORATE_EVIDENCE.

**Pruebas automatizadas del repositorio:** 298 PASS usando las
dependencias nativas del Hand O5 de ELSE CORE.

**Hash SHA-256 exacto del código fuente ejecutado:**
81c8da152f428c0d1c6273aa24d6ca4b01cbe4a2fedd17fcb1cefce41fc37be1.
El archivo fuente original de Windows conserva una línea final adicional
en la rama de QA; la regla de Git para ese archivo preserva sus bytes
porque un cambio de whitespace rompería la identidad del recibo.

Auditoría definitiva en QA: beta_v11_independent_audit.json y
beta_v11_case_audit.private.jsonl. No se suben al repositorio.
