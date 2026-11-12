# ELSE-ITIL-SUP — Verificación empresarial de cinco coincidencias de junio

**Corte QA:** 12 de noviembre de 2026. **Baseline:** main@8a75580ca7e1b879e6499219bb65014abd4b0946. **Fuentes reales:** ELSE62 → ELSE70, dbITIL_D y dbComercial001_D, SIELSEAccesoDatos 3.24.11.27, empresa 1. **Solo lectura**.

## Pregunta

La evaluación anterior revisó 1.621/1.621 incidentes de junio, obtuvo 72 coincidencias *documentales* exactas de operación SQL, tabla y campos empleando 500 antecedentes anteriores de mayo, y produjo cinco casos calificados por el juez Qwen4B como SAME_MECHANISM en una muestra ciega de Qwen9B de 100. Esta fase verifica si los cinco casos tienen identificador, fila empresarial y evidencia de cambio antes/después. **No equivale a auditar empresarialmente los 72 casos**.

## Las cinco comprobaciones ejecutadas

| Contexto histórico | Identificador y vínculo | Resultado SQL QA | Calidad técnica del plan |
|---|---|---|---|
| OT: modificación de centro de atención | Mismo ID en solicitud y nota | Fila de OT ausente; sin auditoría asociada | Objeto y campo alineados, sin validar cambio |
| OT: cambio de medidor | ID de OT en solicitud; la nota no repite el ID | Fila de OT ausente; sin auditoría asociada | Comprobó estado/subtipo, pero no la incompatibilidad del **pliego tarifario** |
| OT: retorno a estado inicial | Mismo ID en solicitud y nota | Fila de OT ausente; sin auditoría asociada | Objeto y estado alineados, sin validar cambio |
| Padrón: corrección de apellido | DNI mencionado en histórico, no en solicitud legible | **Al menos dos filas candidatas** para ese DNI; sin objeto único | Comprobación de apellido alineada, pero entidad ambigua |
| Campaña de supervisión: reapertura | Mismo ID de campaña en solicitud y nota | Fila de campaña ausente | **Objeto incorrecto:** plan trató de examinar una OT, no la campaña |

**Conteo:** 5/5 expedientes vinculados por SHA exacto con solicitudes y notas originales; 4/5 con identificador corroborado por solicitud; 3/5 con mismo ID en solicitud y nota; 4 búsquedas empresariales sin fila, 1 con dos o más candidatos; 0 filas únicas y 0 transiciones antes/después verificadas.

Las tres tablas principales tienen registros de otros objetos en QA; no están vacías globalmente. La ausencia de estos objetos en la copia QA **no demuestra que no existieran o no fueran modificados en producción en junio**.

## Evidencia temporal disponible

El sondeo firmado de seis tablas y 151 columnas indica que taOrdenTrabajo, taPadronRuc y taCampanaSupervision son NON_TEMPORAL_TABLE. La tabla OT tiene tres triggers; padrón y campaña no presentan triggers en esos metadatos QA. Se consultaron por ID exacto las tablas auxiliares taOrdenTrabajoAuditoriaCambio y taOrdenTrabajo_ModificacionIN, para campos pertinentes. No devolvieron eventos sobre esos IDs.

Sin registros de negocio únicos, auditoría específica, versión temporal, respaldo de junio o CDC conservado, **no se puede reconstruir el estado anterior y posterior**. Un UPDATE escrito en la nota histórica **no es evidencia de ejecución**. Tampoco el estado actual de noviembre constituye una fotografía de junio.

## Revisión conservadora de los cinco juicios SAME_MECHANISM

Una auditoría *posterior* a revelar las notas detectó **3 planes con objeto/observable alineados**, **1 con comprobación causal insuficiente** (faltó validar pliego tarifario y potencia contratada) y **1 con clase de objeto incorrecta** (OT frente a campaña de supervisión).

Estas son correcciones de interpretación del juez provisional, no nuevos aciertos ciegos, etiquetas humanas definitivas ni reparaciones certificadas.

## Reproducibilidad y custodia

- JuneBusinessMetaRead.cs: metadatos SQL de tablas, columnas, triggers y naturaleza temporal, firmados con HMAC-SHA256.
- JuneFiveExactBusinessRead.cs: valida manifiesto HMAC, usa SQL fijo SELECT parametrizado y fechas DateTime; verifica SHA-256 de solicitud y solución contra los cinco registros autorizados; lee objetos específicos solo dentro de dbComercial001_D; jamás ejecuta instrucciones SQL escritas por técnicos.
- score_five_business_evidence.py: revalida HMAC de selección, metadatos y objetos; exige identidades, distingue filas ausentes de ambiguas, y compara el objeto del plan con el de la nota.
- verify_private_five_adversarial.py: siete ataques (HMAC modificado, caso cruzado con firma recalculada, fila inexistente presentada como encontrada, reparación falsa, juez manipulado). **7/7 bloqueados**.
- data/2026_june5_business_evidence_audit.json: solo agregados y hashes de recibos, sin identificadores individuales, DNI, nombres, SQL ni texto de solicitudes o notas.

Los recibos originales, manifiesto de cinco casos y valores de negocio se conservan exclusivamente en el servidor QA privado.

## Siguiente contrato necesario

Para acreditar reparación histórica, se necesita acceso autorizado a una **copia de los objetos de negocio del período de junio**, o eventos de auditoría/CDC/ejecución retenidos que incluyan ID exacto, campo, valor anterior y posterior, fecha y operación. También hace falta la relación oficial de aplicación ITIL → entidad empresarial, no solo una mención textual.

Los 72 solapamientos documentales restantes se concentran en referencias de cobranza (35 menciones), OT (22) y adjuntos (10), entre otras. Esto prioriza próximas lecturas, pero no aporta verificaciones de filas adicionales en esta fase.

**Conclusión: 5/5 casos investigados en SQL QA; 0/5 filas empresariales únicas, 0/5 antes/después y 0 reparaciones verificadas. Se identificaron dos problemas de precisión en los cinco juicios originalmente calificados como específicos.**
