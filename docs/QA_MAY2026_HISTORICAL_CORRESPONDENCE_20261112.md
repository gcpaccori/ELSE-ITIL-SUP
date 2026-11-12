# ELSE-ITIL-SUP: mayo 2026, comparacion con historico de soporte

**Alcance:** experimento QA de solo lectura; no es atencion autonoma de tickets ni despliegue a produccion.

## Cohortes y procedimiento

Cuatro paginas consecutivas de 100 incidentes de ELSE70 / dbITIL_D / dbo.taIncidente, seleccionados por FechaSolicitud y CodigoIncidente ascendente en mayo de 2026 (1 714 incidentes totales). Los 400 registros son diferentes; se comprobaron ocho recibos de SQL Server firmados: cuatro de solicitudes y cuatro de soluciones historicas, recuperados de forma independiente.

El modelo autor Qwen 3.5 9B recibio la solicitud original y el nombre del modulo corporativo cotejado contra CodigoModulo, **no la solucion historica**. Los lotes 1, 2 y 3 se usaron durante el perfeccionamiento del enrutador y ya no constituyen una prueba independiente. El lote 4 (registros 301-400) no se utilizo para ajustar esas reglas antes de su primera evaluacion ciega; tras revisar sus resultados ya tampoco constituye un holdout para ajustes posteriores.

| Prueba | Resultado |
|---|---:|
| Primer lote con enrutador original: planes funcionales validos | 56/100 |
| Primer lote con nuevo enrutador: planes funcionales validos | 97/100 |
| Cuarto lote independiente: dominios reconocidos | **88/100** |
| Cuarto lote independiente: planes funcionales validos | **85/100** |
| Cuarto lote independiente: aclaraciones | 12/100 |
| Cuarto lote independiente: planes rechazados | 3/100 |

Un plan valido cumple el contrato determinista de investigacion. No confirma la causa real ni el funcionamiento de la operacion de negocio.

## Comparacion independiente posterior con historico

Tras cerrar los cien resultados del cuarto lote, Qwen 3.5 4B evaluo por separado los chequeos propuestos frente a las notas historicas de los tecnicos.

| Indicador provisional de evaluacion | Resultado |
|---|---:|
| Notas que describen una accion tecnica especifica | 37/100 |
| Notas clasificadas como cierre generico | 63/100 |
| Planes considerados relacionados con el historico | 50/100 |
| Candidatos relacionados y con accion historica especifica | 31/100 |
| De esos, con cita literal historica comprobada | **23/100** |
| Causas reales y reparaciones E2E independientemente certificadas | **0/100** |

Estas relaciones **no son precision real certificada**. Una cita literal acredita que ciertas palabras figuran en la nota, no que el modelo identifico la causa. El evaluador es otro LLM; la auditoria directa encontro falsos positivos incluso con etiquetas de alta confianza. Ademas, varios historicos contienen consultas o actualizaciones SQL comentadas: su presencia no demuestra que se ejecutaran.

## Errores y patrones examinados

- Ordenes de trabajo: el tecnico atribuyo una incidencia a coordenadas ausentes en el suministro vecino; el modelo reviso duplicacion/estado de la OT y omitio ese mecanismo.
- Correo: el historico reportaba un simulacro de phishing, mientras el modelo proponia verificar entrega SMTP y filtros; mismo sistema, causa distinta.
- Cobranzas: los chequeos de caja y centro autorizado son prometedores cuando el historico describe ese atributo, pero una consulta generica de saldos no equivale al ajuste de CodigoCaja.
- SAP: comprobar registros en estado EP es pertinente frente a una nota sobre una transicion EP -> RG, pero no demuestra que el modelo identificara ni ejecutara la correccion.
- MGD: una comprobacion de permisos para borrar adjuntos no equivale a ejecutar una eliminacion; varios historicos incluyen SQL comentado.
- Se necesita reconocer, por caso, tabla de negocio, atributo exacto, estado anterior, cambio documentado y evidencia de verificacion. El nombre de modulo no aporta esos hechos por si solo.

## Cambios en Beta

El enrutador incorporo semantica determinista para arqueos, bancos, cobranzas, reclamos, suministros, contratistas, valorizaciones, materiales, usuarios, MGD, trabajo de campo, ofimatica, telecomunicaciones, GIS, viaticos, flota y adquisiciones. Solo orienta el diagnostico, sin modificar solicitudes ni declarar hechos empresariales no leidos.

El script qa/may2026/score_private_history.py reproduce la auditoria de los recibos y de los enlaces ticket-prediccion-historico, publicando solo totales agregados. Los identificadores, datos personales, descripciones y soluciones permanecen en los archivos privados autorizados. Las pruebas de regresion sinteticas no contienen tickets reales.

**Siguiente etapa:** recuperador de precedentes tecnicos historicos de solo lectura, por caso y objeto exacto, y nuevo lote independiente para medir coincidencia en campo/estado real, no solo en dominio de aplicacion. No habilitar ejecucion autonoma.
