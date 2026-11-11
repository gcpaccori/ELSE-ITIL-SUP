# ELSE-ITIL-SUP V1 Beta: cinco rutas funcionales y control real positivo

**Fecha:** 11/11/2026. **Baseline:** rama
feature/v1beta-company-authority-routing-20261111, commit
da0b0acb103945e8e65a31d548349be9c518a7c9, PR #27.

## Evidencia, hechos y límites

La cohorte congelada de 1819 incidentes ITIL de agosto de 2026 se leyó desde
ELSE70/dbITIL_D/dbo.taIncidente. Cinco tickets mencionan una OT explícita;
diez adicionales mencionan un suministro sin OT. La Hand V2 resuelve
CodigoEmpresa desde ITIL y selecciona exclusivamente
dbComercial001_D (4 tickets) o dbComercial003_D (11 tickets), con
15 recibos firmados en Windows y replay O5/O13/O15 independiente.

**Los 15 recibos tienen cero coincidencias exactas en las tablas consultadas.
Esto NO prueba inexistencia global ni soluciona los tickets.**

## Error temporal SQL detectado y corregido

Un inventario anterior utilizó literales como '2026-08-01' sin conversión
ni parámetros tipados, afectados por la configuración de fecha de SQL Server.
Esta evidencia temporal es inválida. Al repetir la búsqueda con estilo 112
(YYYYMMDD) o SqlParameter SqlDbType.DateTime se confirmó:

- dbComercial001_D: contiene órdenes de trabajo registradas en agosto 2026.
  Última fecha de registro observada: 21/10/2026.
- dbComercial003_D: no se encontraron OT con fecha de registro en agosto 2026.
  Última fecha observada: 30/11/2025.
- dbComercial004_D y dbComercialADINELSA_P: también contienen OT de agosto
  2026, **sin** que ello autorice asumir que albergan las OT de empresas 1/3.
- dbComercial100_D: fecha de registro reciente (11/11/2026), pero sin OT
  registradas en agosto en la consulta de fecha corregida.

Se exploraron 17 bases Comercial/Distribución enumeradas en sys.databases.
Al consultar taOrdenTrabajo de dbComercial003_mayo, dbComercial001_Diario
y dbComercial001_20230131 se obtuvo SQL Server **229** (SELECT denegado).
No se inspeccionaron sus datos ni se probó su ausencia. Las tres bases de
Distribución con error SQL Server **207** no exponen el campo comercial
FechaRegistroSolicitud con el mismo esquema.

## Controles positivos reales .NET8 + SIELSEAccesoDatos NuGet

- qa/PositiveControlRead.cs SHA-256
  9fc41bc9a511586be2d0e084dedea282b9c219d6aaf67218c87f1be17b4d133a
- qa/FunctionalQueries.cs SHA-256
  e9ada48e9c15ce894e5a563e09d32c31b52282d35118c81b3ffe2f43aaea2c58
- .NET 8, NuGet SIELSEAccesoDatos 3.24.11.27, compilados y ejecutados
  en ELSE62 con **0 errores y 0 warnings** tras corregir una lectura
  de tabla no presente en empresa 3.
- Empresa 1: una OT de agosto 2026 real fue reencontrada por igualdad exacta
  y tiene un presupuesto de origen. La consulta al catálogo de estados
  también resolvió su código.
- Empresa 3: una OT histórica real fue reencontrada por igualdad exacta
  y tiene presupuesto. No es una OT del periodo agosto 2026.
- Ambas: suministros y enlaces OT↔suministro de control dieron
  coincidencias positivas, sin devolver identificadores.
- El test de perfiles cruzó tablas de OT, presupuesto, recursos,
  comprobantes, historiales de OSINERGMIN, bitácoras de cambio,
  instalación e información de medidor. Consulta una muestra positiva
  distinta de las cinco OT reportadas: **no demuestra que esos cinco
  incidentes fueran atendidos en Comercial QA**.
- Empresa 3: dbo.taOrdenTrabajo_ModificacionIN no está disponible;
  el campo de auditoría se devuelve como null (fuente ausente),
  **no** como 0 (tabla consultada sin coincidencias).
- Todas las consultas son SELECT fijas; cero cambios empresariales.
  Recibos privados bajo
  /home/u23u/else_itil_positive_controls_20261111/, sin IDs crudos.

Recepción independiente:

- Control básico HMAC:
  c87d449bf6a5bfd377865be81dffdd54c0312e2b7c684a5aace5dddb0befb1
- Control funcional HMAC:
  77e5ec8ec30c07ba07a4e427f36a5493f5eda308ff97cdfff27e981dfdc28757
- Reloj Windows adelantado ~10 min vs Linux, por lo que los verificadores
  permiten máximo 15 min de tolerancia de reloj; no omiten HMAC ni hashes.

## Cinco rutas de diagnóstico específicas ejecutadas sobre tickets reales

Se determinan desde el texto de solicitud (no desde DescripcionSolucion),
CodigoModulo y la empresa provenientes de la Hand firmada. Cada ruta contiene
predicados, tabla/campo, siguiente perfil de consulta, pruebas obligatorias
y acciones prohibidas:

1. RESOURCE_CODE_CORRECTION (M0101100123000): presupuesto, recurso
   existente/nuevo, recálculo y auditoría; nunca sustituir la corrección
   de recursos por UPDATE directo de estado OT.
2. CLIENT_SURNAME_AND_OSINERGMIN (M0101100123000): identidad en padrón,
   estado fiscalizado, prohibición de cambiar OT ya informada y revisión
   de continuidad mediante nueva OT cuando corresponda.
3. METER_EXECUTION_DATE_CORRECTION (M0101300100000): FechaEjecucionInicio,
   FechaEjecucionFin, suministro, cambio de medidor, periodo de facturación
   y traza original; nunca ejecutar SQL de fechas tomado del ticket.
4. REOPEN_INSTALLATION_OT (M0101100123000): grupo supervisor 9,
   verificación sp_Control_AtencionAccion_OT_IN, informe OSINERGMIN,
   justificación, estado y cambio de recurso. No habilitar directamente.
5. ZERO_INITIAL_BUDGET_VOUCHER (M0101100116000): monto presupuestado,
   comprobante y control de emisión. No forzar comprobantes de importe cero
   ni anular comprobantes automáticamente.

**El código SIELSE de M0101100123000, f_ma_OTInstalacion.cs líneas
4465-4473 y 4525-4550, confirma los gates de supervisor, OSINERGMIN,
justificación y los procedimientos de habilitación.** El código del módulo
de presupuesto contiene el cálculo y uso de taPresupuestoTrabajoRecurso.
El módulo Administrador de Clientes contiene campos de fecha de ejecución
de la OT en su dataset.

El mismo árbol de repositorios corporativos se inspeccionó antes de
formalizar estas reglas; la autoría de reglas es humana y se conocían
soluciones históricas en la conversación de investigación. Por ello
**no se debe reportar 5/5 como precisión ciega de un modelo**.
En ejecución, el planificador NO accede a las soluciones históricas
ni alimenta un generador LLM con ellas.

## Pruebas y ejecución reproducible

- 5/5 triages reales distintos, con 15 recibos V2 válidos y O5/O13/O15.
- Positivos en dos bases, cinco perfiles de lectura funcional.
- Tests adversariales: identidad y empresa, HMAC falsos, rebind de OT,
  fuente sin tabla, desambiguación textual, fechas y mutaciones.
- No se certifica operación de reparación, autorización concreta de
  supervisor, unión definitiva ITIL↔OT, ni causa raíz empresarial.
- El estado de cada una de las cinco OT sigue
  QA_REFERENCE_NOT_FOUND_ROUTE_TO_VERIFIED_BUSINESS_SOURCE.

Para auditoría privada, desde raíz del repositorio:

    PYTHONPATH=/home/u23u/elsecore_itil_janlast10_20261110/src:. \
      python tools/qa_v1beta_functional_readiness_audit.py

Tests CI portables:

    python -m unittest -v tests.test_aug_functional_triage_unittest \
      tests.test_aug_functional_profiles_unittest

Todos los HMAC y recibos privados permanecen fuera del repositorio.
Ninguna tabla corporativa se modificó. No se fusionó main ni se hizo
despliegue a producción.
