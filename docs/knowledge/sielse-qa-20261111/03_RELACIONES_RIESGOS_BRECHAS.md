# Semántica relacional, riesgos y próxima fase

## Relaciones y claves

Se recuperaron 796 pares columna-FK. 19 están asociados a restricciones deshabilitadas y 21 a restricciones no confiables.
Estas cifras cuentan pares columna y no restricciones únicas, por las FK compuestas.
Los esquemas de origen y destino están explícitos; los 35 destinos ambiguos del inventario inicial tienen ahora datos de esquema en esta segunda captura.

| Objeto | PK observada | Diagnóstico de soporte |
|---|---|---|
| ELSE70/dbITIL_D/dbo.taIncidente | CodigoIncidente | La PK del ticket no es una FK hacia una OT comercial. |
| ELSE70/dbComercial001_D/dbo.taOrdenTrabajo | CodigoOrdenTrabajo | Distinguir de EXT.taOrdenTrabajo y de distribución. |
| ELSE70/dbComercial003_D/dbo.taOrdenTrabajo | CodigoOrdenTrabajo | Mismo nombre, otra empresa/base y cobertura temporal. |
| ELSE70/dbComercial001_D/dbo.taPresupuesto | CodigoOrdenTrabajo | Se identifica por OT; vigilar estados y recursos. |
| ELSE70/dbComercial001_D/dbo.taComprobante | CodigoComprobante | No equiparar con el comprobante electrónico ni asumir estado SUNAT. |
| ELSE70/dbComercial001_D/dbo.taMedidorSuministro | CodigoMedidor+FechaInstalacion | PK compuesta: considerar FechaInstalacion y posibles periodos sucesivos. |
| ELSE70/dbSeguridad_D/dbo.taUsuario | LoginUsuario | Login, grupo, módulo y sucursal deben contrastarse. |
| ELSE70/dbELSEA/saelse.taOrdenTrabajo | CodigoOrdenTrabajo+CodigoOrigenOrdenTrabajo | Clave y dominio administrativo diferentes. |

## Controles conceptuales exigibles a Beta

La mera igualdad de nombres no certifica una unión, sobre todo si cruza bases SQL.
Cada FK compuesta exige comparar todos sus componentes y el ordinal de las columnas.
Una FK disabled o not trusted no puede usarse como garantía de integridad.
Los nombres de procedimientos Guardar, Eliminar, Actualizar, Procesar o CambiarEstado solo sugieren efectos de escritura; ninguno se ejecutó.
Los procedimientos Listar, RegistroPorCodigo o Consultar tampoco se ejecutan por su nombre sin contrato revisado.
Usar parámetros DateTime tipados o ISO explícito; hubo un diagnóstico temporal equivocado por un literal ambiguo.
No confundir tabla inexistente, lectura denegada, tabla vacía, clave inexistente en alcance y fuente desactualizada.

## Brechas conocidas

- 16 bases con metadatos denegados y una de nombre especial.
- 18 943 tablas catalogadas sin detalle de columnas; se extraerán bajo demanda de cada operación.
- Nueve bases llegaron al límite de metadatos de parámetros de procedimientos.
- Debe verificarse cobertura temporal y claves empresariales de las cinco OT reales.
- No existe unión ITIL→OT certificada; el ticket puede contener referencias solo en texto.
- El código y semántica de procedimientos requieren revisión específica antes de una Hand.

## Próxima fase, solo cuando se solicite

Mapear funcionalidades Beta contra los 15 dominios; registrar SELECTs tipados de alcance fijo y pruebas positivas por empresa; unir recibos con O5/O13/O15; luego pruebas negativas/adversariales, CI y despliegue independiente.
Esta fase se limitó al estudio. Cero procedimientos empresariales ejecutados, cero escrituras y cero reparaciones certificadas.
