# Directorio real de módulos ITIL y repositorios de código corporativo

Fecha de referencia: 11/11/2026. Fuente de datos: SELECT fijo de solo lectura
ELSE70/dbITIL_D/dbo.taModulo mediante SIELSEAccesoDatos en ELSE62 QA.

## Cobertura verificada

| Observación | Cantidad |
|---|---:|
| Filas de módulos ITIL | 3 037 |
| Códigos CodigoModulo distintos | 3 037 |
| Valores de CodigoSistema distintos de ITIL | 27 |
| Código de módulo con espacios de relleno de almacenamiento | 51 |
| AliasBDE informado en la fila ITIL | 2 533 |
| NombreDLL informado en la fila ITIL | 3 036 |
| Coincidencia de nombre con repositorio local M+CodigoModulo | 463 |
| Coincidencia con repositorio local que contiene al menos un archivo C# | 421 |
| Coincidencia sin archivo C# localizado | 42 |

**Limitación:** la coincidencia por nombre del repositorio no demuestra que la versión de código
sea la compilada ni desplegada en QA. Tampoco revela la lógica completa de sus procedimientos.
Los nombres, aliases y DLL declarados son metadatos de referencia; NO son credenciales.

## Distribución por CodigoSistema ITIL

| CodigoSistema ITIL | Módulos registrados |
|---|---:|
| 100 | 874 |
| 3 | 717 |
| 2 | 610 |
| 1 | 450 |
| 6 | 126 |
| 0 | 58 |
| 7 | 41 |
| 5 | 34 |
| 36 | 28 |
| 15 | 14 |
| 38 | 13 |
| 50 | 11 |
| 61 | 9 |
| 60 | 7 |
| 31 | 6 |
| 70 | 6 |
| 8 | 6 |
| 9 | 6 |
| 22 | 4 |
| 25 | 4 |
| 12 | 3 |
| 20 | 3 |
| 4 | 2 |
| 51 | 2 |
| 14 | 1 |
| 37 | 1 |
| 62 | 1 |

## Ejemplos confirmados del directorio

| Código | Nombre ITIL | Repositorio candidato | C# presentes |
|---|---|---|---:|
| 0101100101000 | Reclamos | M0101100101000 | 117 |
| 0101100102000 | Comprobantes | M0101100102000 | 54 |
| 0101100107000 | Supervisión de OTs | M0101100107000 | 16 |
| 0101100110000 | Ordenes de Trabajo de Cambio de Medidor | M0101100110000 | 16 |
| 0101100111000 | Ordenes de Trabajo de Contrastacion de Medidor | M0101100111000 | 12 |
| 0101100112000 | Ordenes de Trabajo de Cambio de Datos | M0101100112000 | 12 |
| 0101100113000 | Ordenes de Trabajo de Mejoramiento de Suministro | M0101100113000 | 11 |
| 0101100116000 | Ordenes de Trabajo para Trabajos Varios | M0101100116000 | 8 |
| 0101100123000 | Ordenes de Trabajo de Instalacion Nueva | M0101100123000 | 39 |
| 0101300100000 | Administrador de Clientes | M0101300100000 | 95 |
| 0003300004000 | Perfiles y Accesos de Usuarios | M0003300004000 | 8 |
| 1601100001000 | Envio de SMS | M1601100001000 | 15 |

## Ruta de diagnóstico para una atención

1. Recuperar la fila exacta del incidente en ITIL; vincular CodigoEmpresa, CodigoModulo,
   CodigoSistema, CodigoServicio, estado y fecha.
2. Resolver CodigoModulo contra el directorio ITIL; conservar los espacios originales
   de los códigos tipo nchar(13). Para buscar repositorios se pueden retirar solo espacios
   finales, sin rellenar ceros ni transformar códigos de aplicaciones móviles.
3. Buscar un repositorio M+CodigoModulo en el inventario corporativo, y comprobar
   versión/commit, archivos fuente y dependencias de los componentes.
4. Comparar alias de base y DLL declarada con el despliegue que realmente atiende la solicitud.
   La declaración de ITIL NO prueba la ruta de SIELSEAccesoDatos.
5. Localizar tablas, PK, FK, esquema y procedimiento de la operación específica; verificar
   si un SELECT registrado de negocio puede ejecutarse en QA sobre empresa y periodo correctos.
6. Separar evidencia de lectura, relación entre sistemas, hipótesis causal y cambio aplicado.

## Advertencia sobre identificadores de sistema

CodigoSistema en dbo.taModulo usa 27 valores, incluidos 100, 36 y 50.
El enum eSistema del conector tiene 32 categorías distintas. Sus valores NO
deben equipararse automáticamente; se requiere contrato explícito o evidencia de código.

## Limitaciones de esta fase

El directorio ITIL es una consulta de referencia QA de solo lectura con fuente de .NET
identificada por SHA-256. No se generó nueva firma HMAC para esta extracción.
No se ejecutaron procedimientos empresariales ni se modificaron módulos.
La integración del atlas en ELSE-ITIL-SUP Beta y sus pruebas se dejan para la fase siguiente.
