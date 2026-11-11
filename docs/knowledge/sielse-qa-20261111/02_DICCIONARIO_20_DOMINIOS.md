# Diccionario funcional — 20 dominios SIELSE

Todos los nombres proceden de nombres reales de tablas y catálogos SQL QA.
Los procedimientos citados son candidatos por su nombre, NO contratos ejecutables.
La clave se obtiene de sys.key_constraints y puede ser compuesta.


## PLANIFICACION_JORNADAS

Base de referencia: dbComercial001_D
Ruta conceptual: Jornada, fecha y centro operativo; validar asignación y recursos sin mezclar planificación con ejecución OT.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taPlanificacionJornada | CodigoPlanificacionJornada+CodigoProceso+CodigoSubProceso | CodigoPlanificacionJornada, CodigoSucursal, CodigoCentroOperacion, CodigoProceso, CodigoSubProceso, CodigoTipoTdC, GeneracionAutomatica, FechaGeneracionAutomatica, CodigoEstadoPlanificacionJornada, CodigoTrabajadorSupervisa, CodigoOperadorContratista ... |
| dbo.taPlanificacionJornadaDetalle | CodigoPlanificacionJornada+OrdenRuta+OrdenVencimiento+CodigoTdC | CodigoPlanificacionJornada, CodigoTdC, OrdenRuta, OrdenVencimiento, CodigoTipoIntervencion, NroFotosIntervencion, CodigoRecursoJornada, CodigoEstadoTdC, CodigoOrdenTrabajo, CodigoSuministro, CodigoOperadorSupervisa ... |
| dbo.taRecursoJornada | CodigoRecursoJornada+CodigoRecursoTdC+CodigoCentroOperacion+CodigoOperador | CodigoRecursoJornada, CodigoRecursoTdC, CodigoCentroOperacion, CodigoOperador, UsuarioOperador, CodigoEstadoRecursoJornada, FechaJornada, FechaProgramaInicioJornada, FechaProgramaFinJornada, FechaEnvioCampo, FechaDescargaPlanificacion ... |
| dbo.gnEstadoPlanificacionJornada | CodigoEstadoEstadoPlanificacionJornada | CodigoEstadoEstadoPlanificacionJornada, NombreEstadoEstadoPlanificacionJornada, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## COBRANZAS_CAJAS

Base de referencia: dbComercial001_D
Ruta conceptual: Caja, cobranza y documento contable; diferenciar movimiento, saldo, conciliación y reversión.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taCobranza | CodigoCobranza | CodigoCobranza, CodigoSuministro, CodigoComprobante, ComprobanteExterno, CodigoSucursal, CodigoSucursalDestino, CodigoPaqueteCobranza, Talon, TalonActivo, MontoCobrado, MontoRecibido ... |
| dbo.taCaja | CodigoCaja | CodigoCaja, CodigoEstadoCaja, CodigoSucursal, CodigoContratista, CodigoContratistaContrato, CodigoCentroRecaudacion, CodigoTrabajador, FechaApertura, FechaCierre, FechaCobranzaReferencial, FechaDepositoReferencial ... |
| dbo.taCarteraCobranza | CodigoCarteraCobranza | CodigoCarteraCobranza, CodigoEstadoCarteraCobranza, CodigoSucursal, CodigoComprobante, FechaVencimiento, CodigoMovimientoBancario, ContactoNombre, ContactoTelefono1, ContactoTelefono2, ContactoEmail, SolicitanteNombre ... |
| dbo.taComprobanteCajaDetalle | CodigoComprobanteCaja | CodigoComprobanteCaja, CodigoTipoComprobanteCaja, CodigoSucursalAsociado, CodigoCRPAsociado, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |

Procedimientos identificados por nombre (no ejecutados): dbo.spListarTaGrupoCobranza, dbo.sgGrupoCobranzaPorCodigo, dbo.smPaqueteDetalleCobranza, dbo.spCobranzaListarPorFiltro, dbo.srGrupoCobranzaListadoDetalle, dbo.sfGrupoCobranzaListarPorFiltro, dbo.spPaqueteCobranzaListarActivos, dbo.spPaqueteCobranzaListarPorCaja, dbo.spCobranzaDetallePaquetePorTipo

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## SUBSIDIOS_FISE_FOSE

Base de referencia: dbComercial001_D
Ruta conceptual: Beneficiario, suministro, vigencia, solicitud y programas FISE/FOSE; no inferir elegibilidad.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taFISEBeneficiario | CodigoBeneficiarioFISE+CodigoSucursal | CodigoBeneficiarioFISE, CodigoSucursal, CodigoEstadoBeneficiarioFISE, CodigoSuministro, ApellidoPaterno, ApellidoMaterno, Nombre, CodigoTipoDocumentoIdentidad, NumeroDocumentoIdentidad, Telefono, CorreoElectronico ... |
| dbo.taSolicitudFISEBeneficiario | CodigoSolicitudFISEBeneficiario | CodigoSolicitudFISEBeneficiario, CodigoSucursal, CodigoZonaAdministrativa, CodigoEstadoSolicitudFISE, CodigoSubEstadoSolicitudFISE, CodigoTipoSolicitudFISE, CodigoClaseSolicitudFISE, CodigoMotivoSolicitudFISE, DescripcionSolicitudFISE, NotificacionSolicitudFISE, CodigoPadronRUCBeneficiario ... |
| dbo.taSuministroFOSE | CodigoSuministro | CodigoSuministro, FOSEEstratoValido, FOSEPromedioValido, FOSEUsuarioAcepta, FOSEBeneficiario, CodigoTipoEstratoFOSE, CodigoMotivoExclusionFOSE, PEA3, PEA12, UsuarioCrea, UsuarioModifica ... |
| dbo.taSolicitudExclusionFOSE | CodigoSolicitudExclusionFOSE | CodigoSolicitudExclusionFOSE, FechaSolicitud, NombreSolicitante, CodigoTipoDocumentoIdentidad, NumeroDocumentoIdentidadSolicitante, CodigoMotivoExclusionFOSE, CodigoEstadoSolicitudExclusionFOSE, CodigoSucursal, CodigoSuministro, CorreoElectronico, NumeroCelular ... |

Procedimientos identificados por nombre (no ejecutados): dbo.spFISE_Buscar_Suministro, dbo.smFiseListarClientesColectivos, dbo.smFiseListarPorClienteColectivo, dbo.spGerencialConsultarFOSEClientes, dbo.spFISE_Buscar_Ubicacion_Suministro, dbo.smFiseListarClientesColectivoFiltro, dbo.spSuministroCtaCteFOSEBeneficiarioPorCodigo, dbo.spFOSEClientes, dbo.spSuministroFOSE

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## VALORIZACIONES_PENALIDADES

Base de referencia: dbComercial001_D
Ruta conceptual: Contrato, valorización, penalidad, acta y estado; diferenciar valorización comercial, distribución y compras.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taContratistaValorizacion | CodigoContratistaValorizacion | CodigoContratistaValorizacion, CodigoEstadoContratistaValorizacion, CodigoContratista, CodigoContratistaContrato, CodigoTipoValorizacionContratista, CodigoSucursal, CodigoTrabajadorElabora, CodigoTrabajadorSupervisa, CodigoTrabajadorAprueba, FechaInicio, FechaFin ... |
| dbo.taContratistaValorizacionDetalle | CodigoContratistaValorizacion+CodigoContratistaContrato+CodigoTipoOrdenTrabajo+CodigoSubTipoOrdenTrabajo+CodigoTrabajoContratoContratista+CodigoSucursal+CodigoZonaAdministrativa+Factor | CodigoContratistaValorizacion, CodigoContratistaContrato, CodigoTipoOrdenTrabajo, CodigoSubTipoOrdenTrabajo, CodigoTrabajoContratoContratista, CodigoSucursal, CodigoZonaAdministrativa, Factor, PorcentajeCumplimiento, Cantidad, PrecioUnitario ... |
| dbo.taPenalidadContratista | CodigoContratista+CodigoContratistaContrato+NumeroPenalidad | CodigoContratista, CodigoContratistaContrato, NumeroPenalidad, CodigoEstadoPenalidadContratista, CodigoPenalidadContratoContratista, CodigoContratistaValorizacion, UsuarioRegistra, UsuarioAprueba, FechaRegistro, FechaAprobacion, DescripcionRegistro ... |
| dbo.taActaValorizacion | CodigoActaValorizacion | CodigoActaValorizacion, CodigoSuministro, CodigoSucursal, CodigoOrdenTrabajo, CodigoEstadoActaValorizacion, CodigoTipoActaValorizacion, EsPropietario, FechaSolicitud, FechaValorizacion, NombreSolicitante, CodigoTipoDocumentoIdentidad ... |

Procedimientos identificados por nombre (no ejecutados): dbo.spOTCambioMedidorGeneraValorizacion, dbo.gnTipoOrdenTrabajoConceptoValorizacionGuardar, dbo.gnTipoOrdenTrabajoConceptoValorizacionListaConceptosParaContrato

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## RRHH_ASISTENCIAS

Base de referencia: dbELSEA
Ruta conceptual: Trabajador, planilla, asistencia y período; la semántica laboral requiere validación propia.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taTrabajador | CodigoTrabajador | CodigoTrabajador, CodigoGerencia, CodigoAreaAdministrativa, CodigoUnidadNegocio, CodigoCAP, CodigoTipoDocumentoIdentidad, NumeroDocumentoIdentidad, CodigoEstadoTrabajador |
| saelse.taRegistroAsistencia | no declarada | CodigoTrabajador, CodigoLocalTrabajo, FechaHoraRegistro, CodigoSucursal, CodigoTipoRegistroAsistencia, CodigoMetodoRegistroAsistencia, CodigoTurnoTrabajo, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion ... |
| saelse.taTrabajadorVacacion | CodigoTrabajador+CodigoEjercicioContable | CodigoTrabajador, CodigoEjercicioContable, CodigoEjercicioContableAfecto, CodigoEstadoVacacion, NumeroDiasVacaciones, NumeroDiasGozado, FechaInicioPrevista, FechaFinPrevista, FechaInicioDerecho, FechaFinDerecho, DocumentoPostergacion ... |
| saelse.taAsistenciaPlanilla | no declarada | CodigoTrabajador, CodigoConceptoPlanilla, CodigoEjercicioContable, MesEjercicioContable, Cantidad, Generado, Observacion, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |

VARIANTES NO EQUIVALENTES: ELSE70/dbELSEA/saelse.taTrabajador

Procedimientos identificados por nombre (no ejecutados): dbo.taTrabajadorDocumentoPorCodigo, mgd.taTrabajadorLegajoDocumentosListar, sst.taTrabajadorContratistaBuscarPorNumeroDocumento, dbo.taSolicitudRegistroAsistenciaWebRegistroPorCodigo, dbo.taOrdenTrabajoPermisoTrabajadorRegistroPorCodigoOT, dbo.spTaGrupoTrabajador, saelse.spTaTrabajadoresPorGrupo, dbo.smTrabajadorTiposPorUsuario, saelse.spTaGrupoTrabajadorPlanilla

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## GESTION_INCIDENTES_ITIL

Base de referencia: dbITIL_D
Ruta conceptual: Incidente → módulo/servicio → derivaciones → cierre registrado; una solución escrita no demuestra ejecución.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taIncidente | CodigoIncidente | CodigoIncidente, CodigoEstadoIncidente, UsuarioSolicita, CodigoEmpresa, CodigoSucursal, CodigoArea, IP, CodigoSLA, CodigoServicioSLA, CodigoServicio, CodigoSistema ... |
| dbo.taIncidenteAtencion | CodigoIncidente+Atencion | CodigoIncidente, Atencion, CodigoEstadoAtencionIncidente, CodigoTipoEscaladoIncidente, CodigoKB, LoginUsuarioPrograma, LoginUsuarioAtiende, FechaProgramacionAtencion, FechaHoraInicioAtencion, FechaHoraFinAtencion, Solucionado ... |
| dbo.taIncidenteDerivacion | CodigoIncidente+NumeroDerivacion | CodigoIncidente, CodigoTipoDerivacionIncidente, NumeroDerivacion, UsuarioDeriva, UsuarioDerivado, MotivoDerivacion, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |
| dbo.taServicio | CodigoServicio | CodigoServicio, NombreServicio, CodigoGrupoServicio, EMailGestorIncidente, EMailGestorServicio, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion, EnviarNotificacionCorreo |
| dbo.taModulo | CodigoModulo | CodigoModulo, CodigoTipoModulo, CodigoSistema, NombreModulo, VersionModulo, UltimaFechaRevisionModulo, AutorModulo, NombreDLL, ParametrosAdicionales, PathRelativo, AliasBDE ... |
| dbo.gnEstadoIncidente | CodigoEstadoIncidente | CodigoEstadoIncidente, NombreEstadoIncidente, Descripcion, Atendido, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |

Procedimientos identificados por nombre (no ejecutados): dbo.gnSistemaListarModulos, dbo.spListarModulosDivision, dbo.spIncidenteDetalleAtencion, dbo.taIncidenteBuscarPorFiltro, supervision.taIncidenteBuscarPorFiltro, dbo.taIncidenteRegistroPorCodigo, dbo.taIncidenteDetalleParaEncuesta, dbo.taTareaAtencionRegistroPorCodigo, dbo.srIncidenteDetalleMensualPorEstado

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## ACCESOS_PERMISOS

Base de referencia: dbSeguridad_D
Ruta conceptual: Validar usuario, rol/grupo, módulo, sucursal, estado y trazas antes de atribuir un error a permisos.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taUsuario | LoginUsuario | LoginUsuario, CodigoTipoUsuario, NombreUsuario, FechaVencimientoUsuario, ExpiraPasswordUsuario, CambiaPasswordUsuario, ActivoUsuario, FechaExpiraPasswordUsuario, Administrador, NumeroMaximoConexiones, AccesoWeb ... |
| dbo.taGrupoUsuario | CodigoGrupoUsuario | CodigoGrupoUsuario, NombreGrupoUsuario, Activo, Observacion, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |
| dbo.taGrupoUsuarioUsuario | CodigoGrupoUsuario+LoginUsuario+CodigoSucursal | CodigoGrupoUsuario, LoginUsuario, CodigoSucursal, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |
| dbo.taGrupoUsuarioModulo | CodigoGrupoUsuario+CodigoModulo+CodigoAccion | CodigoGrupoUsuario, CodigoModulo, CodigoAccion, Monitorea, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |
| dbo.taModulo | CodigoModulo | CodigoModulo, CodigoTipoModulo, CodigoSistema, NombreModulo, VersionModulo, UltimaFechaRevisionModulo, AutorModulo, NombreDLL, ParametrosAdicionales, PathRelativo, AliasBDE ... |
| dbo.taEvaluacionAccesoUsuarioModulo | CodigoEvaluacionAcceso+CodigoModulo+LoginUsuario | CodigoEvaluacionAcceso, CodigoModulo, LoginUsuario, TienePermiso, NoTienePermiso, CodigoGrupoUsuario, Descripcion, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |

Procedimientos identificados por nombre (no ejecutados): dbo.sfModuloBuscar, dbo.sfUsuarioBuscar, dbo.taModuloPorCodigo, dbo._sptaUsuarioBuscar, dbo.taUsuarioPorCodigo, dbo.taGrupoUsuarioListar, dbo.taUsuarioPorCodigoV2, dbo.spListarUsuarioPerfil, dbo.spListarUsuariosSIELSE

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## ORDENES_COMERCIALES

Base de referencia: dbComercial001_D
Ruta conceptual: Empresa+OT → estado y subestado → fiscalización → auditoría; no equiparar con OT de Distribución.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taOrdenTrabajo | CodigoOrdenTrabajo | CodigoOrdenTrabajo, CodigoEstadoOrdenTrabajo, CodigoSubEstadoOrdenTrabajo, CodigoSuministro, CodigoPadronRUC, CodigoPeriodoComercial, CodigoSucursal, CodigoZonaAdministrativa, CodigoComprobante, CodigoComprobanteAdicional, CodigoFormaSolicitud ... |
| dbo.taOTInstalacion | CodigoOrdenTrabajo | CodigoOrdenTrabajo, CodigoTipoEntidadSuministro, CodigoCategoria, CodigoClaseSuministro, CodigoTipoSuministro, CodigoOTComplementaria, CodigoTarifa, CodigoTipoRedElectrica, CodigoTipoTension, CodigoTipoSistema, CodigoTension ... |
| dbo.taOrdenTrabajoEstadoHistorico | CodigoRegistroFiscalizacion | CodigoRegistroFiscalizacion, CodigoOrdenTrabajo, CodigoEstadoOT, CodigoSubEstadoOT, CodigoAsuntoOsinergmin, CodigoAtencion, CodigoAccion, CodigoEstadoAtencionAccion, CodigoTabla, Activo, FechaRegistroAtencion ... |
| dbo.taOrdenTrabajoAuditoriaCambio | CodigoOrdenTrabajo+ItemAuditoriaCambio | CodigoOrdenTrabajo, ItemAuditoriaCambio, NombreCampo, ValorAnterior, ValorActual, MotivoCambio, UsuarioModifica, FechaModificacion |
| dbo.gnEstadoOrdenTrabajo | CodigoEstadoOrdenTrabajo | CodigoEstadoOrdenTrabajo, NombreEstadoOrdenTrabajo, CodigoTipoTrabajoCampanaOT, CodigoEnlace, Observacion, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |

VARIANTES NO EQUIVALENTES: ELSE70/dbComercial001_D/EXT.taOrdenTrabajo, ELSE70/dbComercial001_D/EXT.gnEstadoOrdenTrabajo

Procedimientos identificados por nombre (no ejecutados): dbo.gnTipoOrdenTrabajoListar, dbo.gnEstadoOrdenTrabajoListar, dbo.gnMotivoOrdenTrabajoListar, dbo.spOrdenTrabajoBuscarPorFiltro, dbo.gnSubTipoOrdenTrabajoListarPorTipo, dbo.gnTipoOrdenTrabajoRegistroPorCodigo, dbo.spOrdenTrabajoListarEstadosSiguientes, dbo.gnSubTipoOrdenTrabajoListarPorCodigoTipo, dbo.spSuministroOrdenTrabajoConsultaPorCodigo

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## PRESUPUESTOS_RECURSOS

Base de referencia: dbComercial001_D
Ruta conceptual: OT verificada → estado de presupuesto → recursos y costos; no asumir que UPDATE manual reproduce procedimiento de negocio.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taPresupuesto | CodigoOrdenTrabajo | CodigoOrdenTrabajo, CodigoEstadoPresupuesto, CodigoPlantillaTrabajo, CodigoMovimiento, CodigoMoneda, TipoCambio, GirarEnRecibo, NumeroCuotas, MontoInicial, MontoRecursoPre, MontoRecurso ... |
| dbo.taPresupuestoTrabajo | CodigoOrdenTrabajo+CodigoTrabajo | CodigoOrdenTrabajo, CodigoTrabajo, CodigoEstadoPresupuestoTrabajo, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |
| dbo.taPresupuestoTrabajoRecurso | CodigoOrdenTrabajo+CodigoTrabajo+CodigoRecurso | CodigoOrdenTrabajo, CodigoTrabajo, CodigoRecurso, CodigoTipoRecurso, CodigoConcepto, CodigoMovimiento, ItemMovimiento, CodigoUnidadMedida, PrecioUnitarioPre, PrecioUnitario, CantidadPre ... |
| dbo.gnEstadoPresupuesto | CodigoEstadoPresupuesto | CodigoEstadoPresupuesto, NombreEstadoPresupuesto, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |

Procedimientos identificados por nombre (no ejecutados): dbo.gnRecursoBuscar, dbo.sfRecursoBuscar, dbo.sfRecursoBuscarPorTipo, dbo.gnRecursoRegistroPorCodigo, dbo.sfRecursoPresupuestoBuscar, dbo.gnPlantillaRecursoDetalleGuardar, dbo.gnRecursoRegistroPorCodigoEnlace, dbo.gnPlantillaRecursoDetalleEliminar, dbo.gnTrabajoRecursoRegistroPorCodigo

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## COMPROBANTES_FACTURACION

Base de referencia: dbComercial001_D
Ruta conceptual: Comprobante, emisión, monto, periodo, impuestos, SUNAT; diferenciar de emisión electrónica y registro de ventas.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taComprobante | CodigoComprobante | CodigoComprobante, CodigoTipoComprobante, CodigoEstadoComprobante, CodigoPeriodoComercial, CodigoSucursal, CodigoSuministro, CodigoPadronRUC, CodigoOrdenTrabajo, NumeroRUC, FechaComprobante, FechaImpresion ... |
| dbo.taComprobanteDetalle | CodigoComprobante+ItemComprobante+CodigoConcepto | CodigoComprobante, ItemComprobante, CodigoConcepto, CodigoComprobanteReferencia, CodigoMovimientoReferencia, ItemComprobanteReferencia, CodigoUnidadMedidaReferencia, CantidadReferencia, PrecioUnitarioReferencia, DebeReferencia, HaberReferencia ... |
| dbo.taFacturacion | no declarada | CodigoEmpresa, CodigoSuministro, CodigoPeriodoComercial, Reprocesado, Refacturado, CodigoSucursal, CodigoZonaAdministrativa, CodigoCRP, CodigoSector, CodigoLibro, CodigoTipoSuministro ... |
| dbo.gnTipoComprobante | CodigoTipoComprobante | CodigoTipoComprobante, NombreTipoComprobante, CodigoClasePaquete, CodigoTipoPaquete, CodigoTipoPaqueteDistribuir, Simbolo, RegistroVenta, GeneracionManual, CodigoTipoCorrelativoSerie, MostrarDetalleImpresion, CalcularIGVAutomatico ... |

Procedimientos identificados por nombre (no ejecutados): dbo.sgComprobantePorCodigo, dbo.gnTipoComprobanteListar, dbo.gnEstadoComprobanteListar, alq.taComprobanteDatosPorCodigo, dbo.spComprobanteBuscarPorFiltro, dbo.spComprobanteListarPorFiltro, dbo.sp_sunat_ConsultaComprobante, dbo.smFacturacionValidacionConsulta, dbo.spConsultacomprobanteMayorMenor

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## SUMINISTROS_CLIENTES

Base de referencia: dbComercial001_D
Ruta conceptual: Empresa+sum+cliente → estado y sucursal → medidor y período de vigencia; no revelar información personal.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taSuministro | CodigoSuministro | CodigoSuministro, CodigoEstadoSuministro, CodigoTipoEntidadSuministro, CodigoClaseSuministro, CodigoTipoSuministro, CodigoSituacionSuministro, NombreSuministro, Mayor, CodigoUbicacionElectricaSED, CodigoPadronRUC, CodigoGrupoCobranza ... |
| dbo.taCliente | CodigoCliente | CodigoCliente, CodigoEstadoCliente, Nombre, ApellidoPaterno, ApellidoMaterno, RazonSocial, Direccion, CodigoTipoDocumentoIdentidad, NumeroDocumentoIdentidad, CodigoEmpresa, CodigoPostal ... |
| dbo.taMedidorSuministro | CodigoMedidor+FechaInstalacion | CodigoMedidor, FechaInstalacion, CodigoSuministro, CodigoEstadoMedidorSuministro, CodigoUbicacionMedidor, CodigoTipoMedicionMedidor, CodigoFaseAlimentacion, CodigoTipoTension, CodigoTension, CodigoTipoRedElectrica, CodigoTipoMaterialCajatoma ... |

Procedimientos identificados por nombre (no ejecutados): dbo.sfSuministroBuscar, dbo.spCCBuscarSuministro, dbo.spClienteLibreDetalle, dbo.gnTipoSuministroListar, dbo.gnClaseSuministroListar, dbo.spFISE_Buscar_Suministro, dbo.spSuministroBT8PorCodigo, dbo.spBuscarSuministroPorRuta, dbo.spSuministroConsultaDatos

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## MEDIDORES_LECTURAS

Base de referencia: dbComercial001_D
Ruta conceptual: Suministro→medidor vigente por fecha→lectura y consistencia; medidor no equivale a suministro.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taMedidor | CodigoMedidor | CodigoMedidor, CodigoEstadoMedidor, CodigoMarca, CodigoModelo, Serie, NIM, AnoFabricacion, Hilos, Fases, ConstanteRotacion, AmperajeMenor ... |
| dbo.taMedidorSuministro | CodigoMedidor+FechaInstalacion | CodigoMedidor, FechaInstalacion, CodigoSuministro, CodigoEstadoMedidorSuministro, CodigoUbicacionMedidor, CodigoTipoMedicionMedidor, CodigoFaseAlimentacion, CodigoTipoTension, CodigoTension, CodigoTipoRedElectrica, CodigoTipoMaterialCajatoma ... |
| dbo.taLecturaMayor | CodigoPeriodoComercial+CodigoSuministro+CodigoMedidor+NumeroLectura+CodigoEstadoLectura | CodigoPeriodoComercial, CodigoSuministro, CodigoMedidor, NumeroLectura, CodigoEstadoLectura, PorCronograma, FechaLectura, CodigoTipoLectura, CodigoObservacionLectura, CodigoRefacturacion, EA ... |
| dbo.taLecturaMenor | CodigoPeriodoComercial+CodigoSuministro+CodigoMedidor+NumeroLectura+CodigoEstadoLectura | CodigoPeriodoComercial, CodigoSuministro, CodigoMedidor, NumeroLectura, CodigoEstadoLectura, PorCronograma, FechaLectura, CodigoTipoLectura, CodigoObservacionLectura, CodigoRefacturacion, EA ... |

VARIANTES NO EQUIVALENTES: ELSE70/dbComercial001_D/smi.taLecturaMenor

Procedimientos identificados por nombre (no ejecutados): dbo.gnTipoLecturaListar, dbo.gnTipoMedidorListar, dbo.gnClaseMedidorListar, dbo.gnEstadoMedidorListar, dbo.ListarLecturaPorFranja, dbo.gnUbicacionMedidorListar, dbo.spMedidorBuscarPorFiltro, dbo.spPadronLecturaConsultar, dbo.spMedidorPorCodigoDetalle

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## RECLAMOS_ATENCIONES

Base de referencia: dbComercial001_D
Ruta conceptual: Núm. reclamo→suministro→motivo/estado→historial, distinguiendo denuncia/fiscalización.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taReclamoComercial | CodigoReclamo | CodigoReclamo, CodigoEstadoReclamo, NumeroOsinerg, CodigoSituacionReclamo, CodigoPeriodoComercial, CodigoClaseReclamo, CodigoTipoReclamo, CodigoSectorTipico, CodigoTipoResolucionReclamo, ClasificadoOSINERG, CodigoMotivoNoAdmisionReclamo ... |
| dbo.taReclamoComercialAtencion | CodigoReclamoComercial | CodigoReclamoComercial, CodigoAtencion, CodigoAsuntoOsinergmin, Enviado, NombreArchivoRespuesta, FechaEnvioOsinergmin, UsuarioCrea, FechaCreacion |
| dbo.taSuministro | CodigoSuministro | CodigoSuministro, CodigoEstadoSuministro, CodigoTipoEntidadSuministro, CodigoClaseSuministro, CodigoTipoSuministro, CodigoSituacionSuministro, NombreSuministro, Mayor, CodigoUbicacionElectricaSED, CodigoPadronRUC, CodigoGrupoCobranza ... |

Procedimientos identificados por nombre (no ejecutados): dbo.gnTipoReclamoListar, dbo.sfTipoReclamoBuscar, dbo.gnClaseReclamoListar, dbo.gnFormaReclamoListar, dbo.sfClaseReclamoBuscar, dbo.gnEstadoReclamoListar, dbo.sfDenunciaListaReclamos, dbo.spListarReclamoSinAudio, dbo.sfLocalidadReclamoBuscar

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## CORTES_RECONEXIONES

Base de referencia: dbComercial001_D
Ruta conceptual: Suministro→situación comercial→OT o evento→restricciones; nunca reponer servicio por instrucción textual.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taOTCorte | CodigoOrdenTrabajo | CodigoOrdenTrabajo, CodigoAccionCorte, CodigoEstadoSuministro, CodigoTipoCorte, CodigoComprobante, MontoDeuda, CodigoOTCorteAnterior, CodigoOTReconexion, MedidorRetirado, FechaRetiroMedidor, Testigo ... |
| dbo.taOTReconexion | CodigoOrdenTrabajo | CodigoOrdenTrabajo, CodigoAccionCorte, CodigoFaseAlimentacion, Testigo, InformeReconexion, CodigoCobranza, CodigoOTCorte, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |
| dbo.taSuministro | CodigoSuministro | CodigoSuministro, CodigoEstadoSuministro, CodigoTipoEntidadSuministro, CodigoClaseSuministro, CodigoTipoSuministro, CodigoSituacionSuministro, NombreSuministro, Mayor, CodigoUbicacionElectricaSED, CodigoPadronRUC, CodigoGrupoCobranza ... |

Procedimientos identificados por nombre (no ejecutados): dbo.gnTipoCorteListar, dbo.gnMotivoCorteListar, dbo.gnLibroListarPorZonaPorCorte, dbo.gnMotivoCorteInspeccionListar, dbo.srCorteReconexionResumenDetalle, dbo.srCampanaSupervisionCorteDetalle, dbo.spAccionCorteListarPorTipoTension, dbo.spSuministroConsultaCortePorDeuda, dbo.spSuministroCortesReconexionesPorCodigo

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## DISTRIBUCION_INTERRUPCIONES

Base de referencia: dbDistribucion_D
Ruta conceptual: Código OT distribución≠OT comercial; tramo afectado→interrupción→suministros y período.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taOrdenTrabajo | CodigoOrdenTrabajo | CodigoOrdenTrabajo, CodigoEstadoOrdenTrabajo, NombreOrdenTrabajo, CodigoClaseOrdenTrabajo, CodigoTipoOrdenTrabajo, CodigoSubTipoOrdenTrabajo, CodigoSucursal, CodigoAlmacen, CodigoFuenteFinanciamiento, CodigoAreaAdministrativa, CodigoTipoEjecutorMantenimiento ... |
| dbo.taInterrupcionEnergia | CodigoInterrupcion | CodigoInterrupcion, CodigoInterrupcionNTCSE, CodigoTipoInterrupcion, CodigoEstadoInterrupcion, FHInicioInterrupcionPro, FHFinInterrupcionPro, FHInicioInterrupcion, FHFinInterrupcion, CodigoSucursal, CodigoCausaInterrupcionPro, CodigoCausaInterrupcion ... |
| dbo.taSolicitudInterrupcionEnergiaRedAfectadaSuministro | CodigoSolicitudInterrupcion+ItemUE+CodigoSuministro | CodigoSolicitudInterrupcion, ItemUE, CodigoSuministro, DireccionElectrica, EsRural, CodigoSectorTipico, EnAnexo, DireccionElectricaDinamica |

Procedimientos identificados por nombre (no ejecutados): dbo.spOrdenTrabajoListar, dbo.spListarInterrupciones, dbo.taOrdenTrabajoSAPDetalle, dbo.spInterrupcionesDetalleGIS, dbo.taOrdenTrabajoUEEquipoListar, dbo.taInterrupcionArchivoPorCodigo, dbo.taInterrupcionEnergiaPorCodigo, dbo.gnTipoArchivoInterrupcionListar, dbo.rsInterrupcionSuministroDetalle

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## FISCALIZACION_OPERATIVA

Base de referencia: dbSIELSEFiscalizacion
Ruta conceptual: Incidente operativo → atención y acción → OT comercial/mantenimiento; validar cruce entre bases.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taIncidenteOperativo | CodigoIncidenteOperativo | CodigoIncidenteOperativo, CodigoEstadoIncidenteOperativo, CodigoSituacionIncidenteOperativo, CodigoPeriodoComercial, CodigoMotivoAtencion, CodigoClaseAtencion, CodigoTipoAtencion, CodigoCanalAtencion, SolicitanteNombres, SolicitanteApPaterno, SolicitanteApMaterno ... |
| dbo.taIncidenteOperativoOrdenTrabajoComercial | CodigoIncidenteOperativo+CodigoOrdenTrabajo | CodigoIncidenteOperativo, CodigoOrdenTrabajo, FechaRegistroOrdentrabajo, FechaEjecucionOrdentrabajo, CodigoEstadoOrdenTrabajo, NombreEstadoOrdenTrabajo, CodigoSubEstadoOrdenTrabajo, NombreSubEstadoOrdenTrabajo, CodigoTipoOrdenTrabajo, NombreTipoOrdenTrabajo, CodigoSucursal ... |
| dbo.taIncidenteOperativoAtencionAccion | CodigoIncidenteOperativo+ItemAccion | CodigoIncidenteOperativo, ItemAccion, CodigoAtencion, CodigoAccion, CodigoEstadoIncidenteOperativo, CodigoSituacionIncidenteOperativo, CodigoEstadoAtencion, FechaRegistroAccion, DescripcionAccion, Activo, UsuarioCrea ... |
| dbo.taSuministro | CodigoSuministro | CodigoSuministro, CodigoEstadoSuministro, CodigoTipoEntidadSuministro, CodigoClaseSuministro, CodigoTipoSuministro, CodigoSituacionSuministro, NombreSuministro, DireccionPredio, ReferenciaUbicacionPredio, CodigoPadronRUC, CodigoTipoCorte ... |

Procedimientos identificados por nombre (no ejecutados): dbo.taIncidenteOperativoPorCodigos, dbo.spValidarDetalleIncidenteOperativo, dbo.taIncidenteOperativoInformePorCodigo, dbo.taIncidenteOperativoRegistroPorCodigo, dbo.taIncidenteOperativoAccionRegistroPorCodigo, dbo.taIncidenteOperativoArchivoRegistroPorCodigo, dbo.taIncidenteOperativoInformeRegistroPorCodigo, dbo.taIncidenteOperativoTensionRegistroPorCodigo, dbo.taIncidenteOperativoDatosAdicionalesPorCodigo

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## DOCUMENTOS_MGD

Base de referencia: dbMGD_D
Ruta conceptual: Expediente documental→estado→permisos/versión; distinguir archivos binarios de metadatos.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| mgd.taDocumento | CodigoDocumento | CodigoDocumento, NombreDocumento, CodigoEstadoDocumento, CodigoTipoPiePaginaDocumento, Simbolo, NumeroArchivo, Bloqueado, BloqueadoPor, InicioBloqueo, FinBloqueo, SinFinDeBloqueo ... |
| mgd.taExpediente | CodigoExpediente | CodigoExpediente, CodigoExpedientePadre, CodigoTipoExpediente, CodigoTipoSoporteExpediente, FechaExpediente, CodigoTipoDocumento, NumeroExpediente, NumeroCorrelativo, Asunto, CodigoEstadoExpediente, CodigoNivelConfidencialidad ... |
| mgd.taSitioUsuario | CodigoSitio+LoginUsuario | CodigoSitio, LoginUsuario, CodigoRolUsuarioSitio, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |

Procedimientos identificados por nombre (no ejecutados): emision.spListargndocumentoDestino, mgd.taDocumentoDetallePorCodigo, emision.taDocumentoRegistroPorCodigo, mgd.taDocumentoRegistroPorCodigo, emision.gnDocumentoTipoFirmanteListar, emision.spListarFirmantespordocumento, emision.taDocumentoPorCodigoDocumento, emision.spListargnDocumentoTipoFirmante, emision.spBuscarNumeroDocumentoIdentidad

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## FACTURACION_ELECTRONICA

Base de referencia: dbComprobanteElectronico_D
Ruta conceptual: Comprobante comercial → comprobante electrónico/SUNAT; relación entre bases aún no certificada.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| dbo.taComprobante | CodigoComprobante | CodigoComprobante, CodigoTipoComprobante, CodigoEstadoComprobante, FechaComprobante, MontoTotal, NumeroSerie, NumeroComprobante, RazonSocial, CodigoTipoDocumentoIdentidad, NumeroDocumento, UsuarioCrea ... |
| dbo.taResumenDiarioComprobante | IDResumenDiario+CodigoComprobante | IDResumenDiario, CodigoComprobante, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion, CodigoSucursal, CodigoTipoComprobante, EstadoEnvioSunat |
| dbo.gnTipoComprobante | no declarada | CodigoTipoComprobante, NombreTipoComprobante |

Procedimientos identificados por nombre (no ejecutados): dbo.spTipoComprobantePagoListar, dbo.taComprobantePorEstadoListar, dbo.spEstadoComprobanteSunatListar, dbo.taRERComprobanteArchivoConsultar, dbo.taComprobanteDuplicadoDSPorCodigo, dbo.taComprobanteElectronicoPorCodigo, dbo.taRERComprobanteArchivoConsultarLista, dbo.taComprobanteRSPResumenPeriodoPorCodigo, dbo.taComprobanteArchivoLeerPorCodigoComprobante

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## ADMINISTRACION

Base de referencia: dbELSEA
Ruta conceptual: Operaciones administrativas no intercambiables con tablas homónimas de Comercial.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| saelse.taOrdenTrabajo | CodigoOrdenTrabajo+CodigoOrigenOrdenTrabajo | CodigoOrdenTrabajo, CodigoOrigenOrdenTrabajo, CodigoSucursal, ReferenciaTipo, DescripcionOrdenTrabajo, CodigoContratistaContrato, CodigoEstadoOrdenTrabajo, CodigoAlmacen, FechaGeneracion, FechaLiquidacion, UsuarioCrea ... |
| saelse.taPresupuesto | no declarada | CodigoEjercicioContable, CodigoGerencia, CodigoSucursal, CuentaContable, CodigoTipoPresupuesto, MontoPresupuestoInicial, MontoPresupuestoAprobado, MontoPresupuestoActual, MontoCompromiso, MontoGasto, UsuarioCrea ... |
| saelse.taUsuario | no declarada | LoginUsuario, NombreUsuario, CodigoTrabajador, CodigoAreaAdministrativa, CodigoSucursal, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion, FechaReplicacion |
| dbo.taDocumento | CodigoDocumento | CodigoDocumento, NombreDocumento, UbicacionOriginal, NombreArchivo, Extension, TamanoArchivo, FechaCreacionArchivo, Archivo, Descripcion, UsuarioCrea, FechaCreacion |

Procedimientos identificados por nombre (no ejecutados): finanzas.spPresupuestoPartidasDetalle, finanzas.taPresupuestoRegistroPorCodigo, dbo.taPresupuestoDetalleListaPorFiltro, finanzas.taPresupuestoItemRegistroPorCodigo, dbo.taPedidoAlmacenDetallePorOrdenTrabajo, dbo.taViaticoPresupuestoRegistroPorCodigo, finanzas.taPresupuestoRegistroPorCodigoYUsuario, finanzas.taPresupuestoItemProyectoDetalleGuardar, finanzas.taPresupuestoItemProyectoDetalleEliminar

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.

## COMUNICACIONES_SMS

Base de referencia: dbSComunicaciones_D
Ruta conceptual: Contacto/avisos por suministro; trazabilidad sin exponer teléfonos o identidades.

| Tabla real | Clave primaria declarada | Columnas capturadas |
|---|---|---|
| marketing.taPersonaSuministro | CodigoPersona+CodigoSuministro | CodigoPersona, CodigoSuministro, CodigoRelacionSuministroPersona, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |
| dbo.taSuministroComunicacion | CodigoSuministro+CodigoPersona+CodigoSolicitudComunicacion | CodigoPersona, CodigoSuministro, Activo, CodigoSolicitudComunicacion, CodigoSolicitudComunicacionDesafiliacion, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |
| dbo.taSolicitudComunicacionSuministro | CodigoSolicitudComunicacion+CodigoSuministro | CodigoSolicitudComunicacion, CodigoSuministro, UsuarioCrea, UsuarioModifica, FechaCreacion, FechaModificacion |

Procedimientos identificados por nombre (no ejecutados): dbo.taSuministroPersonaGuardar, dbo.smSolicitudComunicacionTipos, dbo.spGetSuministrosPorDocumento, dbo.swCrearSolicitudComunicacion, dbo.smSolicitudesComunicacionTipos, dbo.taSolicitudComunicacionGuardar, dbo.taSolicitudComunicacionRechazar, dbo.taSuministroComunicacionGuardar, com.uspRegistrarSolicitudComunicacion

Condición de soporte: confirmar empresa, sistema, clase de entidad, clave completa, vigencia y un recibo de lectura de negocio antes de diagnosticar una causa.
