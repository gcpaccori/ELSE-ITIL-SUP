# ELSE-ITIL-SUP — auditoría de los 1.288 casos de junio sin PK empresariales

**Fecha:** 16 de noviembre de 2026. **Baseline:** `main@70ae2189119cc5fa328a4c648dffccf24b0adcd5` (PR #43). **Universo:** los 1.621 incidentes originales de junio de 2026. No se seleccionaron expedientes a partir de su solución histórica.

## 1. Qué se ejecutó

Se inspeccionaron *en elsecluster5* tres artefactos privados ya existentes de QA: solicitudes de junio con texto redactado, descubrimiento SQL dual OT/cobranza y grafo de PK por expediente. Los tres recibos cumplieron su hash SHA-256 byte a byte y se verificó la correspondencia por posición, SHA de caso, SHA de solicitud, código de módulo, servicio y fecha de apertura. **Esta etapa no revalidó independientemente los HMAC** (esa comprobación es parte del cierre de la PR #43); por tanto, el resultado es una auditoría derivada de tres artefactos antes certificados, no una nueva lectura SQL.

El script `qa/june2026_full_link/triage_unmatched_june1621.py` genera solamente estadísticas agregadas. No escribe claves de OT, cobranza, datos personales, textos de solicitudes ni hashes por expediente en Git. Tampoco lee notas de solución.

## 2. Resultado completo sin ocultar los casos negativos

| Estado basado en las solicitudes originales | Incidentes |
|---|---:|
| Sin ningún número candidato de 19 dígitos | **1.162** |
| Con candidato de 19 dígitos, sin PK de sucursal coincidente | **126** |
| Con una PK empresarial observada retrospectivamente | 158 |
| Con varias PK empresariales observadas retrospectivamente | 175 |
| **Total** | **1.621** |

Dentro de los **126** tickets con número candidato pero sin PK aceptada, **113** sí tienen alguna coincidencia empresarial en **otra sucursal**, que debe rechazarse; **13** no tienen PK en ninguna de las tablas del alcance ya consultado. Esto evita dos errores: tratar una sucursal ajena como vínculo positivo y confundir ausencia en las tablas consultadas con ausencia global del objeto.

## 3. Vocabulario funcional disponible en los 1.162 sin candidato de 19 dígitos

Las menciones detectadas en el *texto redactado de la solicitud*, con coincidencias múltiples permitidas, son:

| Pista léxica, no identidad empresarial | Tickets |
|---|---:|
| Accesos, usuarios o permisos | 279 |
| Documentos, archivos o firma | 221 |
| Suministros | 208 |
| Facturación, recibos o comprobantes | 119 |
| Órdenes de trabajo | 116 |
| Solicitudes | 122 |
| Lectura o medidores | 96 |
| Reclamos | 82 |
| Cobranza, caja o arqueos | 55 |
| Sin ninguna de esas palabras | 348 |

Estas cifras **no deben sumarse**, pues el mismo ticket puede mencionar varias pistas. Se basan en términos y no identifican con certeza el módulo, un objeto concreto ni el procedimiento a ejecutar.

## 4. Priorización funcional inmediata

1. **Recuperar tipos adicionales de referencia:** inspeccionar, en QA y sin consultar soluciones históricas, claves de `CodigoSuministro`, solicitud, documento, cliente u otros contratos del módulo, sin asumir que siempre tienen 19 dígitos. El mayor subconjunto de 1.162 casos carece de la longitud esperada por el lector anterior.
2. **Resolver autoridad de sucursal antes de asociar PK:** examinar los 113 casos con coincidencias exclusivamente en otra sucursal usando el módulo ITIL, ruta SIELSEAccesoDatos y objeto tipado; una coincidencia externa no puede habilitar un vínculo.
3. **Depurar búsqueda de objetos para los 13 candidatos sin PK:** comprobar si las referencias representan otros identificadores, si fueron borradas del QA o si pertenecen a bases fuera del alcance. Concluir únicamente sobre las fuentes consultadas.
4. **Desambiguar los 175 multíobjeto:** separar lote, objetos secundarios y posible objeto principal mediante evidencia funcional del propio texto y contratos de aplicación, conservando la abstención si no hay una prueba suficiente.

## 5. Límites

Las coincidencias de PK de la PR #43 fueron observadas en **noviembre de 2026**, no representan un estado `AS OF` junio. La clasificación del texto de junio tampoco demuestra operaciones de reparación. El número de reparaciones E2E acreditadas sigue en cero y no se realizó escritura SQL ni reinicio del servicio.

**Artefactos de reproducción:** `data/2026_june1621_unresolved_source_triage.json`, el script señalado y `tests/test_june1621_source_triage.py`. Para regenerarlos se requieren los recibos privados originales, alojados únicamente en QA.
