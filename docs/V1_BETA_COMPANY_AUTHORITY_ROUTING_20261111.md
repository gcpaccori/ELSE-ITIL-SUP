# ELSE-ITIL-SUP V1 Beta — autoridad empresarial por incidente (11/11/2026)

## Resultado real en QA, no certificación de cierre empresarial

**Predecesor:** rama feature/v1beta-commercial-third-hand-20261111, commit
1153d978bf733c818c786ef7d256490632efd273, PR #26. Este cambio se
implementó en una rama separada, sin fusionar main ni desplegar producción.

1. Origen autorizado: ELSE70/dbITIL_D/dbo.taIncidente, agosto de 2026,
   **1819** incidentes de cohorte inmutable. El código lee CodigoEmpresa,
   CodigoSucursal, CodigoModulo, CodigoSistema, CodigoServicio y
   CodigoIncidente, pero **nunca** las soluciones históricas.
2. Selección obligatoria: cinco tickets con OT expresamente mencionada
   + diez tickets nuevos con suministro explícito, seleccionados por
   SHA-256 determinista sobre la cohorte. No se aceptan otros casos.
3. Resolución: CodigoEmpresa 1 -> ELSE70/dbComercial001_D,
   CodigoEmpresa 3 -> ELSE70/dbComercial003_D. Cualquier otra empresa,
   mismatch del proveedor o ticket ambiguo hace FAIL cerrado. La empresa
   proviene de la fila ITIL, **no** de texto, LLM ni archivo de petición.
4. Windows ELSE62 ejecutó **63** sentencias SELECT **fijas y
   parametrizadas**, 15 casos: 4 en base de empresa 1, 11 en base
   de empresa 3. Todas tuvieron cero coincidencias exactas en los predicados
   consultados; se ejecutaron **cero** modificaciones de negocio.
5. Cada resultado tiene recibo JSON base64 con SHA-256 exacto, HMAC-SHA256
   de trabajador Windows QA, huella del archivo C# original, caso, ID
   mencionado **solo como SHA-256**, empresa ITIL y base Comercial exacta.
   No se subieron IDs, claves ni recibos privados a GitHub.
6. Revalidación independiente Linux: **15/15** SHA+HMAC+esquemas+IDs,
   módulo O5/O13/O15 **15/15 PASS** con verificador separado. No se
   ejecutó SQL durante el replay. Manifest de recibos:
   f79693c43882e14c7395db59410fc7e8c79645c83bcb1c5b263c4b7d0db5c9b2.
7. Fuente compilada y ejecutada en Windows (.NET 8, SIELSEAccesoDatos
   3.24.11.27): qa/CompanyRoutedIdentity.cs; SHA-256
   c0a6071bf730dfd41d01939794ed7bba8f22b91ffc5b4a4a3ace4fb7637368a3.
   No se solicita a un LLM construir SQL ni seleccionar tabla, base o empresa.

## Corrección del false PASS previo

Los cinco OT más diez suministros se habían buscado erróneamente contra
dbComercial001_D. El origen ITIL demuestra cuatro casos de empresa 1 y once
de empresa 3. Las recepciones antiguas sin CodigoEmpresa respaldado por ITIL
se clasifican como **LEGACY_UNROUTED / NO_ADMISSIBLE_FOR_V2** incluso cuando
su HMAC y su búsqueda exacta anterior eran válidos. No se puede convertir
el resultado negativo de esas lecturas en evidencia del estado de otra empresa.

Las pruebas sintéticas adversariales incluyen un recibo legítimamente
re-firmado contra la empresa/base equivocada, cambio de empresa, HMAC falso,
casos ambiguos, recibos V1, recuentos fuera de límites, falsa coincidencia,
alteración de fuente/cohorte, soluciones históricas y flags de mutación.

## Limitación de cobertura empresarial (confirmada, no inferida)

- dbComercial001_D: última FechaRegistroSolicitud de OT observada
  **21/10/2026**; no se encontró una OT con registro en agosto de 2026.
- dbComercial003_D: última fecha observada **30/11/2025**.
- Ambas contienen tablas de órdenes y suministros; el resultado negativo
  para agosto **no** prueba la inexistencia de los objetos reales fuera
  de las bases/tablas QA comprobadas. No se certifican uniones ITIL-OT,
  ejecución de cambios, causas raíz ni reparación de ninguna atención.
- dbITIL_D sí registra los incidentes del período y contiene módulos,
  servicio y soluciones históricas. Estas últimas se mantuvieron fuera
  del flujo generador y del lector V2.

## Archivos y reproducción

- qa/CompanyRoutedIdentity.cs y .csproj: trabajador SQL solo lectura.
  Se ejecutó en ELSE62 con rutas temporales privadas ya existentes.
  El paquete NuGet corporativo se resuelve con configuración Windows QA.
- else_dominance/company_routed_verified.py: ingesta y verificación
  criptográfica exacta de 15 recibos; falla sin claves privadas y cohorte.
- else_dominance/company_routed_o5_hand.py: O5 con Guardian O13/O15.
- else_dominance/company_routed_o5_verifier.py: evaluador independiente.
- tests/test_aug_company_route_unittest.py: pruebas CI con datos y HMAC
  **sintéticos**, sin secretos ni conexión a QA.
- tools/qa_v1beta_company_route_audit.py: replay privado, desde raíz repo:
  PYTHONPATH=/home/u23u/elsecore_itil_janlast10_20261110/src:. python tools/qa_v1beta_company_route_audit.py

Los recibos privados se conservaron en
/home/u23u/else_itil_company_route_qa_20261111/outbox/, fuera de Git.
El lector no ejecuta INSERT, UPDATE, DELETE, MERGE ni procedimientos de escritura.

## Próxima dependencia, sin false PASS

Solicitar y verificar **fuente corporativa autoritativa para las OT y
suministros existentes en agosto de 2026**, con empresa, sucursal, módulo,
y política de solo lectura. Una vez disponibles datos operativos positivos,
comparar cada predicado exacto contra la historia ITIL y verificar estados,
presupuestos, cambios y autorizaciones sin reutilizar el texto de resolución
histórica como oracle del modelo. La nueva capa no convierte cierres ITIL
en reparaciones certificadas.
