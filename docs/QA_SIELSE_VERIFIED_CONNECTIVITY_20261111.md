# Conectividad QA SIELSE — evidencia de ejecución real (11 noviembre 2026)

La conexión fue comprobada en ELSE62 mediante SIELSEAccesoDatos, consultando SQL Server ELSE70. El trabajador utilizó perfiles fijos de consulta, sin SQL procedente del modelo y sin escrituras.

## Resultado

| Comprobación | Resultado |
|---|---|
| Pruebas SQL de perfil | 11 positivas de 11 |
| Clave real y segunda consulta por parámetro tipado | 11 de 11 |
| Clave negativa de control | 11 de 11 devolvieron cero |
| Bases | ITIL, Seguridad, Distribución, Comercial 001 y Comercial 003 |
| Áreas comerciales | OT, suministros, presupuestos, comprobantes |
| Mutaciones de datos | Cero |
| Firma HMAC de trabajador ELSE62 comprobada en Linux | Sí |
| Identificadores de clientes divulgados | Ninguno |
| Reparaciones empresariales certificadas | Ninguna |
| Consultas de caso realizadas al pedir el recibo de conexión | Ninguna |

SHA-256 del recibo SQL privado:
411bc7ede750d8b0186492d196c7ee5373df90fa843168b7c7c65f1b86dc65e2

SHA-256 del código fuente del lector Windows:
251160343a05b9ae3b21cc0bbf6cefa96438aaa282c6614fe8aa6091e141c5f9

## Hallazgos reales

La primera ejecución funcionó para cinco perfiles, y seis fallaron porque se cerraba el objeto reutilizado por SIELSEAccesoDatos.Obtener. Se corrigió el ciclo de vida del lector QA privado, se volvió a compilar y se repitieron las 11 pruebas; todas dieron positivo.

Se comprobó un desfase de aproximadamente 11 minutos entre ELSE62 y elsecluster5. El verificador permite como máximo 15 minutos de desfase futuro de QA, lo declara explícitamente y rechaza recibos caducados, firmas inválidas, campos modificados y cambios de empresa.

## Comprobación integrada en Beta

El CLI acepta TIC_QA_CONNECTIVITY_ROOT apuntando a la ruta privada del recibo, y dispone del subcomando qa-connectivity con --profile opcional. La herramienta del investigador inspect_qa_connection acepta únicamente un profile_id de 11 perfiles autorizados. La respuesta indica QA_SNAPSHOT_SOURCE_CONFIRMED_NOT_CASE_READ: NO se entrega como evidencia de causa, reparación ni consulta fresca de un ticket.

El recibo caduca como máximo a las 12 horas. La renovación exige volver a ejecutar el trabajador Windows y transferir su nueva firma; no existe un proceso de refresco automático certificado en esta entrega.

El fuente C# del trabajador y sus pruebas de ejecución se conservan en el directorio privado de QA. El repositorio versiona únicamente el verificador, la herramienta de inspección y pruebas sintéticas; no incluye claves ni SQL real de producción.

## Verificación del código

Se ejecutaron pruebas negativas de firma, empresa, destino, clave, estado de lectura, reloj y alcances no registrados. Regresión local completa: 380 aprobadas, 24 omitidas, 71 subpruebas aprobadas.

**Limitación:** la conexión ya es comprobable, pero no sustituye una Hand por caso con CódigoEmpresa ligado, lectura recién ejecutada y verificación independiente O5/O13/O15. Esta entrega no afirma que los 21 dominios estén resueltos.
