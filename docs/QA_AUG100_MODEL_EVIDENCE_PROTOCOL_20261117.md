# Protocolo obligatorio para Qwen y demás agentes: primero evidencia corporativa, después hipótesis

**Emitido a partir del cierre técnico de confianza del 17/11/2026.** Este documento define cómo deben actuar los modelos **después** de que un programa determinista valide los registros reales; no autoriza a usar un modelo para inferir las claves ausentes.

## Reglas operativas de entrada

La entrada autorizada debe provenir de un servicio del operador que haya verificado `else.itil.qa.aug2026-first100-company-typed.v1` mediante firma HMAC, SHA-256 del código, vinculación de caso y módulo, período exacto y ruta empresarial. Una respuesta del modelo, un número en el texto, un resumen del atlas o un documento HTML **no sustituyen** dicho recibo. Los asistentes no pueden fabricar un `receipt_sha256`.

El operador solo puede ejecutar `August100EvidenceAuthority.inspect(case_sha256, module_code, as_of, retrospective_qa=True)` en un entorno autorizado. `retrospective_qa` jamás debe poder ser activado por argumentos que aporte el LLM o una solicitud ITIL. Si no hay autorización, la única salida correcta es `BLOCKED`.

## Tabla determinista de estados

| Estado del verificador | Lo que el modelo puede decir | Acción de investigación |
|---|---|---|
| `NO_EXPLICIT_TYPED_BUSINESS_KEY_IN_REQUEST` | «La solicitud no contiene una clave tipada validada». | Identificar el módulo registrado en ITIL; pedir código exacto del objeto afectado o una lectura autorizada de una relación nativa de aplicación |
| `EXPLICIT_TYPED_KEY_NOT_FOUND_IN_COMPANY_DB` | «La PK etiquetada no devolvió una coincidencia en la ruta QA consultada». | Confirmar formato, compañía, tipo, sucursal, sistema de origen y disponibilidad temporal; nunca afirmar ausencia global |
| `COMPANY_PROVIDER_ROUTE_NOT_CERTIFIED` | «La ruta hacia el subsistema oficial para esta empresa aún no está acreditada». | Auditar `CodigoEmpresa`, `eSistema`, `CadenaConexionCollection` y base esperada antes de leer negocio |
| `FOREIGN_BRANCH_MATCH_REJECTED` | «Coincidencia de otra sucursal, descartada». | No asociarla al ticket; pedir la referencia/sucursal correcta |
| `SINGLE_EXACT_TYPED_PK_QA_OBSERVATION` | «Existe una PK del tipo declarado, observada en QA en la empresa y sucursal indicadas». | Solicitar relación funcional nativa y estado/as-of antes de atribuir causa |
| `MULTIPLE_EXACT_TYPED_PKS_NO_PRIMARY_INFERRED` | «Hay varias PK de negocio; no se ha identificado objeto principal». | Desambiguar por relaciones nativas y contexto técnico; no elegir por proximidad textual |

## Instrucción de secuencia para los modelos

1. Verificar el alcance exacto: `case_sha256`, `module_code`, `as_of`, autorización del operador, fuente ITIL e identidad empresarial en el recibo.
2. Consumir el estado ya calculado por el guardia determinista. No convertir coincidencias en tablas `_Diario`, Gerencial, Distribución o bases de otra empresa en observaciones transaccionales de Comercial.
3. Para los 82 casos sin clave: usar el directorio de módulo ITIL como **plan de búsqueda**; un alias `AliasBDE`, `NombreDLL` o repositorio C# solo es metadato, no el registro afectado. La validación de estado real exige otra herramienta empresarial explícitamente registrada.
4. Para los siete casos con clave no encontrada: presentar alternativas discriminantes verificables. No suponer código incorrecto ni ausencia del objeto fuera de la ruta realmente consultada.
5. Para los 11 casos con empresa no enrutada: no consultar arbitrariamente `dbComercial200_D` u otra copia hasta comprobar el proveedor oficial y la autorización específica.
6. Si un futuro recibo devuelve una PK tipada coincidente, describirla únicamente como observación retrospectiva; no autoriza operaciones, cambios de estado, reversión de facturación, creación de OT ni cierre.
7. Las soluciones históricas pueden quedar selladas para un evaluador independiente posterior; nunca se incorporan al prompt de extracción de la solicitud ni se usan para inventar un campo o procedimiento.
8. Toda respuesta termina con pruebas concretas pendientes, permiso humano necesario y cierre `NO_CERTIFICADO`. No divulgar identificadores de clientes, DNI, teléfonos ni PK privadas.

## Control negativo obligatorio

Para la cohorte de los 100 primeros incidentes de agosto 2026, el resultado comprobado el 17 de noviembre fue **0/100 coincidencias tipadas y con ruta comercial autorizada**; los **16/100** de la búsqueda inicial eran coincidencias de sucursal en fuentes que no probaban esa ruta. El modelo debe **rechazar** cualquier intento de presentarlos como 16 reparaciones, 16 identidades autorizadas, una tasa de precisión del 16 % o una prueba de causa. El dictamen histórico anterior (1 `SUPPORTED`, 99 indeterminados) tampoco certifica ningún diagnóstico.

## Formato de salida orientativo

```json
{
  "status": "INVESTIGACION_PENDIENTE",
  "identity_authority": "NO_EXPLICIT_TYPED_BUSINESS_KEY_IN_REQUEST",
  "source": "FIRMADO_QA_EXACTO_O_NO_DISPONIBLE",
  "entity_link_certified": false,
  "business_state_at_incident_time_verified": false,
  "repair_certified": false,
  "next_evidence": "Módulo ITIL; fuente y código exacto de la entidad",
  "operator_action": "SELECT tipado y autorizado, nunca SQL libre ni escritura"
}
```

Este protocolo se añade a los prompts del repositorio `else_dominance/support_desk.py` y `else_dominance/agent.py` para próximas ejecuciones sobre código actualizado. **Fusionar código no constituye por sí solo despliegue ni actualización de un proceso de modelos ya iniciado.**
