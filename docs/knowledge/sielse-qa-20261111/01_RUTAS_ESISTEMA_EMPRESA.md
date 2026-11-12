# Enrutamiento real eSistema + empresa

Los 32 sistemas del proveedor corporativo se consultaron para las empresas 1 y 3.
Una conexión resultante no constituye permiso SQL ni vínculo ITIL con otra tabla.

| Sistema | Empresa 1 | Empresa 3 |
|---|---|---|
| Administrativo | ELSE70/dbELSEA | ELSE70/dbELSEA |
| Archivos | ELSE70/SIELSE_Archivos_D | ELSE70/SIELSE_Archivos_D |
| ArchivosMGDv1 | ELSE70/MGDArchivos_D | ELSE70/MGDArchivos_D |
| Auxiliar | ELSE70/dbIntranet_D | ELSE70/dbIntranet_D |
| BSC | NO_RESUELTA (SqlException) | NO_RESUELTA (Exception) |
| BibliotecaIntranet | ELSE70/dbBibliotecaIntranet_D | NO_RESUELTA (Exception) |
| Comercial | ELSE70/dbComercial001_D | ELSE70/dbComercial003_D |
| Distribucion | ELSE70/dbDistribucion_D | ELSE70/dbDistribucion_D |
| ELSEWeb | NO_RESUELTA (SqlException) | NO_RESUELTA (SqlException) |
| FacturacionElectronica | ELSE70/dbComprobanteElectronico_D | ELSE70/dbComprobanteElectronico_D |
| General | ELSE70/dbComercial001_D | ELSE70/dbComercial001_D |
| GeneralAdministrativo | NO_RESUELTA (SqlException) | NO_RESUELTA (SqlException) |
| Geografico | NO_RESUELTA (Exception) | NO_RESUELTA (Exception) |
| Gerencial | ELSE70/dbGerencial_D | ELSE70/dbComercial003_D |
| GestionCompraEnergia | NO_RESUELTA (SqlException) | NO_RESUELTA (Exception) |
| GestionSMS | ELSE70/dbSMS_D | ELSE70/dbSMS_D |
| GoSv1 | NO_RESUELTA (SqlException) | NO_RESUELTA (Exception) |
| GoSv2 | ELSE70/dbSIELSEGoS_D | NO_RESUELTA (Exception) |
| ITIL | ELSE70/dbITIL_D | NO_RESUELTA (Exception) |
| Intranet | ELSE70/dbIntranet_D | NO_RESUELTA (Exception) |
| MGDv2 | ELSE70/dbMGD_D | NO_RESUELTA (Exception) |
| Mediciones | ELSE70/dbMediciones_D | ELSE70/dbMediciones_D |
| PIDE | ELSE70/dbSIELSEPIDE | ELSE70/dbSIELSEPIDE |
| Planeamiento | ELSE70/dbPlaneamiento_D | ELSE70/dbPlaneamiento_D |
| SFV_RER | ELSE70/dbSIELSERER_D | ELSE70/dbSIELSERER_D |
| SIG | NO_RESUELTA (SqlException) | NO_RESUELTA (Exception) |
| Seguridad | ELSE70/dbSeguridad_D | ELSE70/dbSeguridad_D |
| SeguridadCentralizada | ELSE70/dbSeguridad_D | NO_RESUELTA (Exception) |
| SeguridadCliente | ELSE70/dbSeguridadCliente_D | ELSE70/dbSeguridadCliente_D |
| SistemaControlInterno | NO_RESUELTA (SqlException) | NO_RESUELTA (Exception) |
| SistemaMantenimiento | NO_RESUELTA (SqlException) | NO_RESUELTA (SqlException) |
| SistemaSeguridadv1 | NO_RESUELTA (Exception) | NO_RESUELTA (SqlException) |

## Excepciones críticas

La lectura ITIL con empresa 3 no resuelve una ruta específica, aunque dbITIL_D contiene incidentes CodigoEmpresa=3 recuperados a través de la ruta existente de ITIL.
General apunta a dbComercial001_D para ambas empresas; no usarlo en lugar de Comercial/empresa 3.
Gerencial/empresa 3 resuelve dbComercial003_D; Gerencial/empresa 1 utiliza dbGerencial_D.
Seguridad y Distribucion son rutas compartidas para ambos códigos de empresa.
Una ruta no resuelta debe permanecer como no resuelta; no construir cadenas de conexión alternativas por inferencia.
