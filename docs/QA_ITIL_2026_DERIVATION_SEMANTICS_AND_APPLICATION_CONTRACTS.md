# ELSE-ITIL-SUP — tipos de derivación y contratos de aplicación (900 expedientes)

**Corte:** 12 de noviembre de 2026. **Baseline:** main@6909f99f4fa129cc7b51845cfc7b439a05b45a04. **Entorno:** ELSE62 Windows QA, ELSE70/dbITIL_D, elsecluster5. Trabajo de solo lectura; no se activó atención autónoma.

## Tipos de derivación: la evidencia no permite fijar el significado

La muestra de 900 expedientes de enero-septiembre tiene 1.155 derivaciones por coincidencia exacta de CodigoIncidente y NumeroDerivacion.

| CodigoTipoDerivacionIncidente | Filas verificadas | Significado |
|---|---:|---|
| 1 | 900 | NO VERIFICADO |
| 2 | 90 | NO VERIFICADO |
| 3 | 165 | NO VERIFICADO |

Se realizó una inspección SQL real de metadatos mediante DerivationContractsProbe.cs, con recibo HMAC. El campo CodigoTipoDerivacionIncidente es de tipo tinyint, pero la consulta de tablas no encontró un catálogo de tipos distinto de taIncidenteDerivacion, y la inspección de módulos SQL visibles no encontró una definición de ese código o un procedimiento que lo interpretara. La búsqueda de la referencia exacta en los JavaScript de primer nivel disponibles de SielseWeb tampoco produjo coincidencia. No se inspeccionó la implementación compilada del aplicativo.

**Esto NO demuestra la inexistencia de la definición en otra capa de software.** Queda pendiente una fuente corporativa autorizada: implementación ITIL con versión conocida que asigne esos códigos, o un catálogo oficial de códigos. Mientras no aparezca, la capa VerifiedDerivationContracts.semantics devuelve meaning=null y allow_business_interpretation=false. No infiere que 1, 2 o 3 signifiquen alta, escalamiento, atención ni solución.

## Relaciones de módulo y servicio verificadas

ModuleRouteRead.cs seleccionó los últimos 100 incidentes de cada mes enero-septiembre con el mismo orden e identidad de los nueve recibos HMAC originales. El módulo y servicio fueron contrastados por la clave exacta con taModulo y taServicio dentro de dbITIL_D.

| Mes 2026 | Casos | Módulo con fila PK | Servicio con fila PK | AliasBDE declarado | NombreDLL declarado |
|---|---:|---:|---:|---:|---:|
| Enero | 100 | 100 | 100 | 76 | 100 |
| Febrero | 100 | 100 | 100 | 72 | 100 |
| Marzo | 100 | 100 | 100 | 79 | 100 |
| Abril | 100 | 100 | 100 | 65 | 100 |
| Mayo | 100 | 100 | 100 | 79 | 100 |
| Junio | 100 | 100 | 100 | 78 | 100 |
| Julio | 100 | 100 | 100 | 79 | 100 |
| Agosto | 100 | 100 | 100 | 63 | 100 |
| Septiembre | 100 | 100 | 100 | 71 | 100 |
| **Total** | **900** | **900** | **900** | **662** | **900** |

Hay 128 módulos únicos. Un segundo recibo SQL de metadatos, levantado de forma independiente, permitió cotejar alias, DLL y código de sistema de 65 de esos módulos, presentes en 760 de los 900 incidentes. Las 140 filas restantes están firmadas, pero sin un segundo cotejo independiente de sus alias.

La consulta SQL verifica la existencia de registros de módulo y servicio, pero no declara una FK que no exista en sys.foreign_keys. AliasBDE es una configuración declarada, no una prueba del servidor físico en ejecución. NombreDLL es nombre de componente declarado, no un rastro de ejecución de dicha DLL. Los 900 casos no incluyen un contrato oficial ITIL↔OT, ITIL↔suministro o ITIL↔cobranza.

Los incidentes operativos de Fiscalización usan CodigoIncidenteOperativo y no deben confundirse con el CodigoIncidente de ITIL. Los nombres semejantes no son una relación válida entre bases.

## Puerta funcional de contratos y seguridad

Se implementó la clase VerifiedDerivationContracts con doble verificación HMAC, SHA de ambos lectores, nueve recibos mensuales, enlace contra el ciclo de vida de los 900 casos y cotejo independiente de alias/DLL de los módulos disponibles.

La herramienta inspect_itil_application_contract solo permite una de estas consultas:

- view=module_route: devuelve la ruta declarada del módulo/servicio del caso y su recibo, con la advertencia de que no está demostrada la ruta física ni la fila empresarial.
- view=derivation_type, type_code=1, 2 o 3: comprueba que ese tipo está efectivamente presente entre las derivaciones firmadas del expediente, pero no proporciona una etiqueta funcional sin fuente acreditada.

El expediente, módulo y fecha se obtienen del contexto autorizado; el modelo no los puede sustituir en los argumentos de la herramienta. La ruta propuesta a una tabla empresarial siempre se abstiene mediante ABSTAIN_BUSINESS_JOIN_NOT_CERTIFIED hasta disponer de un contrato oficial y una lectura exacta del objeto.

Se incorporó la CLI qa-itil-application-contract, que abre recibos verificados, sin ejecutar SQL. Requiere TIC_QA_ITIL_APPLICATION_CONTRACT_ROOT, TIC_QA_ITIL_LIFECYCLE_ROOT, TIC_QA_MONTHEND_ROOT y TIC_QA_RECEIPT_SIGNING_KEY.

Los ataques con HMAC alterado, recibo vuelto a firmar con un alias distinto a la captura independiente, caso cruzado, una supuesta relación FK y un significado de código inventado deben producir BLOCKED. El agente conserva causal_diagnosis_confirmed=false, domain_business_state_verified=false, can_claim_resolved=false y can_execute_mutations=false cuando solo dispone de esta información.

## Evidencia y siguientes contratos pendientes

Informe agregado: data/2026_derivation_semantics_module_routes_900.json. Lectores: qa/derivation2026/DerivationContractsProbe.cs y ModuleRouteRead.cs. Verificación privada adversarial: qa/derivation2026/verify_private_contracts_adversarial.py.

Los recibos HMAC originales, notas, registros individuales y rutas por expediente permanecen privados en el servidor; ningún valor individual se publica en GitHub.

El siguiente salto a una intervención comparable al histórico real requiere **(a)** el significado de códigos tomado de una definición versionada de ITIL, **(b)** contrato formal de acceso de cada módulo a la base y operación concreta y **(c)** lectura empresarial de objeto/fila vinculada al ticket exacto. Una ruta declarada por sí sola no cumple estas condiciones.

**Resultado certificable:** 900 enlaces internos a módulo y servicio, 760 cotejos independientes de ruta declarada, tres tipos de derivación aún sin significado acreditado y **cero causas, reparaciones y cambios empresariales certificados**.
