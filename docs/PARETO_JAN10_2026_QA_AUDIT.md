# ELSE-ITIL QA — Pareto de evidencias, 1–10 enero 2026

**Fecha de auditoría:** 10 de noviembre de 2026.
**Origen:** ELSE62, base QA ELSE70/dbITIL_D/dbo.taIncidente.

## Censo real de SQL QA

Nuevo SELECT fijo y de solo lectura ejecutado con SIELSEAccesoDatos
3.24.11.27 (archivo qa/Jan10QaCount.cs): 638 filas,
638 códigos distintos, fecha primera 2026-01-02, última 2026-01-10.
La ventana solicitada es 2026-01-01 inclusivo a 2026-01-11 exclusivo.
No existían registros fechados el día 1 en la copia QA.
No se extrajeron soluciones en esta nueva consulta, ni se modificó SQL.

## Pareto por código de servicio

| Código | Casos |
|:--|--:|
| 1 | 392 |
| 3 | 67 |
| 2 | 54 |
| 70 | 43 |
| 61 | 28 |
| 60 | 25 |
| 50 | 17 |
| 34 | 10 |
| 62 | 2 |
| **Total** | **638** |

Los tres primeros códigos representan 513/638 = 80,41%.
Código de clasificación 101 = 518 casos (81,2%). No se inventaron
nombres oficiales para los códigos; la interpretación de dominios
se basa exclusivamente en el texto de las solicitudes de la copia QA.

### Rutas heurísticas de evidencia requerida

| Ruta | Casos |
|:--|--:|
| Comercial / órdenes de trabajo | 241 |
| ITIL general | 211 |
| Aplicaciones / configuración | 109 |
| SAP e integraciones | 44 |
| Accesos y permisos | 33 |

Las rutas son **hipótesis de clasificación, no diagnósticos**.
La primera lectura especializada que promete mayor cobertura es
comercial/órdenes de trabajo; el número de OT comunicado por un
solicitante nunca se toma como vinculación SQL verificada.
En 46 expedientes se detectó un posible patrón de número OT, pero
0 vínculos corporativos fueron confirmados mediante ese texto.

## Auditoría integral de los planes históricos de Qwen

Se analizaron todos los 638 casos desde el snapshot privado de enero
con resultados previos de Qwen 9B y revisor Qwen 4B, unidos exclusivamente
por SHA-256, no por textos parecidos.

| Indicador | Casos |
|:--|--:|
| Qwen 9B completó su inferencia | 632 |
| Contrato original, sin normalizar | 304 |
| Contrato tras vinculación posterior | 604 |
| Fuentes añadidas posteriormente al plan | 309 |
| De esas 309, con gate posterior aprobado | 300 |
| Resolución histórica incluida en la generación | 0 |

Una vinculación posterior al modelo no equivale a leer la tabla de origen.

El revisor Qwen 4B evaluó 628 casos y emitió 546 etiquetas
NOT_DETERMINABLE, 42 CONFLICT y 40 SUPPORTED, comparando con
historiales humanos. Calificó 623 historiales como VAGUE y 5 como
ACTIONABLE. No son tasas de acierto: son juicios de otro modelo.
De los 638 expedientes, 634 tenían resolución histórica no vacía
(203 breves, 431 más largas), 4 estaban vacíos.

## Cambios funcionales implementados

- else_dominance/pareto_evidence.py: ruta determinista con categorías
  de evidencia necesarias para ITIL, comercial/OT, SAP, permisos y aplicación.
- else_dominance/qa_dynamic_nuget_cluster.py: un recibo O5 de la
  incidencia ITIL ya no se acepta como prueba de permiso efectivo,
  enlace SAP/OT ni estado comercial. Bloqueo a revisión por evidencia faltante.
- qa/jan10_pareto_eval.py: auditoría exhaustiva, sin muestreo,
  de 638 expedientes, fuentes posteriores, calidad y procedencia.
- qa/Jan10QaCount.cs + proyecto: censo SQL real nuevo de enero.
- Pruebas unitarias de casos sintéticos, regresión y cohorte determinista.

El gate nuevo sobre los 638 recibos históricos clasificó:
604 MISSING_VERIFIED_EVIDENCE, 28 MODEL_CONTRACT_REJECTED
y 6 MODEL_INCOMPLETE. Esto no indica 604 errores causales,
sino **604 planes que aprobaron formato sin consulta nueva
de fuente corporativa para esta cohorte**.

Pantallas/identificadores, consultas específicas y contraseñas
no se guardaron en el repositorio.

## Riesgos detectados sin exagerar certeza

15 planes mencionan tablas no declaradas entre sus fuentes;
un modelo revisor señaló 6 posibles mutaciones no justificadas y
2 posibles discordancias de dominio. Se requiere evaluación humana.
No hay reparaciones certificadas ni validaciones de técnicos.

## Evidencia privada y reproducibilidad

Los resultados por los 638 casos y el resumen están en ELSE62:
C:\Temp\ELSE_ITIL_JAN10_PARETO_20261110\results_v2

SHA-256 del snapshot privado de solicitudes:
c3b8e4cbfa1deb5b36ba97de8f2a73662d1ae63976e5f15ba2bf72af5ff05cb9

SHA-256 de los 638 recibos auditados en la salida v2:
1983ed6f44acf7c0c8d2e7a8b600b7ab9ee1ff549f38b0336b27b621eeb588e4

La generación del reporte se repitió en una ejecución independiente:
638/638 coincidieron y el SHA de los resultados fue idéntico.
No hay historiales ni descripciones personales en Git.

## Alcance exacto y próximo objetivo

El piloto de enero actual es una **auditoría retrospectiva de
638 planes previamente generados**, con lectura SQL nueva del
recuento total. **No se han ejecutado 638 lecturas NuGet de
expediente ni 638 nuevas inferencias.**

Para llevar esto a V1 Beta, la prioridad técnica es:
1. Extender el Hand ITIL exacto a enero con recibo O5/O13/O15.
2. Conectar la lectura comercial/OT y su identidad de negocio.
3. Evaluar E2E esa fuente en una muestra de casos, con
   revisión técnica y métricas de causalidad separadas.
SAP y accesos siguen como rutas posteriores.
