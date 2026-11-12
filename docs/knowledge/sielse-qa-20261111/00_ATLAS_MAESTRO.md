# ELSE-ITIL-SUP — Atlas maestro de conocimiento SIELSE QA

Estudio estructural del 11/11/2026. No implica integración, prueba funcional ni reparación empresarial.
Fuente: ELSE70, SIELSEAccesoDatos 3.24.11.27 en ELSE62, capturas de sys.* de SQL Server.

## Alcance cuantificado

| Métrica | Cobertura |
|---|---:|
| Bases SQL de usuario en línea | 69 |
| Bases con metadatos de tablas accesibles | 52 |
| Denegaciones SQL 916 | 16 |
| Base de nombre especial sin explorar | 1 |
| Tablas catalogadas por base/esquema | 22 242 |
| Vistas contabilizadas | 220 |
| Descripciones de columnas de la primera extracción | 33 143 |
| Descripciones adicionales en tablas prioritarias | 4 292 |
| Columnas recuperadas para las primeras tablas ancla | 445 |
| Columnas de cinco dominios adicionales | 469 |
| Tablas ancla funcionales con columnas capturadas | 78/78 |
| Tablas con detalle de al menos una columna | 3,331 |
| Tablas todavía sin detalle de columnas | 18,911 |
| Pares columna-FK con ambos esquemas identificados | 796 |
| Pares de columnas de PK/UNIQUE | 37 439 |
| Bases con firmas de procedimientos inspeccionadas | 23 |
| Procedimientos declarados sumados por base | 63 357 |
| Descripciones de parámetros capturados | 78 625 |
| Sistemas lógicos eSistema | 32 |
| Módulos de ITIL registrados | 3 037 |
| Valores distintos CodigoSistema en ITIL | 27 |
| Módulos ITIL con repo corporativo de nombre coincidente | 463 |
| Repositorios coincidentes que incluyen al menos un archivo C# | 421 |
| Combinaciones sistema/empresa comprobadas | 64 |
| Rutas resueltas hacia QA | 38 |
| Dominios de datos documentados | 20 |

## Cinco niveles de confiabilidad

1. Base en sys.databases: existe el contenedor, no necesariamente permisos sobre sus tablas.
2. Tabla/columna/PK/FK en sys: existe el objeto estructural; no demuestra la existencia de registros de negocio.
3. Enrutamiento SIELSEAccesoDatos: define base para sistema+empresa, pero no acredita lectura de la tabla.
4. Consulta funcional: exige entidad y empresa, clave correcta, fecha, predicado, SELECT tipado y recibo verificable.
5. Reparación: requiere efectos comprobados, auditoría, invariantes, cierre y verificación independiente; esta fase no realiza ninguna.

## Límites

Los primeros 11 lotes de metadatos/rutas fueron firmados por el trabajador QA.
Las nuevas extracciones de todas las tablas, claves y procedimientos conservan procedencia de archivos QA y SHA, pero no tienen nueva revalidación HMAC.
La enumeración de procedimientos no es ejecución y nueve bases alcanzaron el límite de 7000 parámetros.
Varias bases siguen sin metadatos y hay tablas prioritarias sin columnas completas.
No se debe inferir relación entre tablas iguales de Comercial, Distribución, Administración o esquema EXT.

El artefacto estructurado completo se conserva en derived/SIELSE_QA_CROSS_DOMAIN_ATLAS_20261111.json.gz dentro del directorio privado.
