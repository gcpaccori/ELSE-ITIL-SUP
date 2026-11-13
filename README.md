# ELSE-ITIL-SUP — RIV (Investigación Resolutiva Verificable)

**Objetivo:** asistente de soporte TIC dirigido por un LLM, con recuperación histórica, consultas corporativas autorizadas y propuestas de resolución **condicionadas a evidencia y roles**. No es un bot de etiquetas ni promete resolver todos los tickets.

> Estado real al 2026-11-02: código experimental, sin reparaciones de tickets reales certificadas. Las baterías sintéticas y pruebas unitarias **no son** tasas de resolución. Los antecedentes reales de ELSE **NO están publicados aquí**.

## Una sola ruta, sin ramas funcionales duplicadas

1. `else_dominance/agent.py`: orquestador LLM que decide pruebas y herramientas.
2. `else_dominance/memory.py`: almacenamiento local, FTS5 y procedencia de antecedentes, **solo dentro del perímetro autorizado**.
3. `else_dominance/sources.py`: descubrimiento de fuentes/relaciones a partir de catálogo validado externo.
4. `else_dominance/qa_adapter.py`: conector de queries **registradas en configuración privada**; no SQL libre del modelo.
5. `else_dominance/engineer.py`: verificador y expedientes con responsables condicionados, sin ejecutar cambios.
6. `else_dominance/learning.py`: revisión y promoción de evidencias independientes.

`resolution_batch.py` se conserva **solo como harness de evaluación retrospectiva** (no es un segundo motor de producción). `batch_2026.py` orquesta el núcleo LLM con holdout; nunca expone la solución del caso al modelo.

## Evidencia empresarial de junio y guía maestra

El mapa corporativo de fuentes, la metodología para interpretar notas
históricas y la escalera de evidencia E0–E5 se documentan en
[Dominio maestro SIELSE/ITIL](docs/ELSE_ITIL_SIELSE_DOMINIO_MAESTRO_EVIDENCIA_Y_RESOLUCION_20261112.md).

La evaluación firmada de junio cubre 1.621 incidentes; una ampliación
*retrospectiva* sobre 57 casos de órdenes de trabajo/cobranzas encontró
12 identificadores existentes en alguna copia QA, pero solo tres estaban
corroborados desde la solicitud original. **Encontrar una fila no implica
que el procedimiento histórico se haya ejecutado ni que exista una
reparación verificada.** La base Comercial001 no es destino universal:
verifica la empresa/sucursal comercial y la ruta corporativa del objeto.

### Identificadores de negocio de junio recuperados en QA

La extracción sobre las 57 solicitudes originales de junio (sin leer sus notas
de solución) obtuvo **619 relaciones expediente–PK**, equivalentes a **525
identificadores empresariales distintos**, para 55 de 57 expedientes. La lista
completa queda protegida en ELSE62/elsecluster5. La selección de los expedientes
fue retrospectiva: no es un nuevo benchmark ciego ni acredita reparaciones.

Metodología: [recuperación de identificadores originales](docs/QA_ITIL_JUNE2026_RECUPERACION_IDENTIFICADORES_ORIGINALES_20261112.md).

### Vínculo evidencial incidente ITIL–objeto de negocio

El registro privado de junio enlaza **619 relaciones expediente–PK** entre
**55 tickets** y **525 claves empresariales distintas**. Hay **13 casos con
una sola PK**, **42 con múltiples PK** y **dos sin objeto del tipo esperado**.
No existe una FK nativa certificada ni reparación histórica acreditada.
La herramienta inspect_itil_business_links consulta handles sin divulgar
identificadores reales.

[Informe de vinculación](docs/ITIL_SIELSE_VINCULACION_VERIFICADA_TICKET_OBJETO_20261112.md).

### Grafo de objetos empresariales para junio completo (QA retrospectiva)

Se auditaron **1.621 solicitudes ITIL originales**, sin utilizar notas
históricas para elegir OT/cobranza. Se recuperaron **333 tickets** con
PK de negocio y sucursal coincidentes, con **1.491 relaciones lógicas**
y **1.236 claves empresariales distintas** tras deduplicar copias.
Los casos de tipo ambiguo y las claves compartidas entre tickets se
mantienen en revisión. **Ninguna coincidencia certifica reparación**.

La CLI qa-june-full-business-graph requiere --retrospective-qa, y el
agente solo puede usarla si el operador habilita el modo con SHA exacto
de expediente. Los datos privados permanecen fuera de GitHub.

[Informe de junio completo](docs/QA_ITIL_JUNE2026_FULL_1621_SOURCE_PK_GRAPH_20261113.md).

## Ejecutar pruebas

```bash
python -m pip install pytest
python -m pytest -q
```

Para integración operativa, se exige un catálogo real de fuentes y un endpoint de inferencia aprobado, ambos privados:

```bash
export TIC_CATALOG_PATH=/secure/qa/catalog_verified.json
export TIC_LLM_BASE_URL=http://127.0.0.1:8000/v1
export TIC_LLM_MODEL=approved-local-llm
python -m else_dominance.operational_cli --db /secure/qa/knowledge.sqlite stats
```

El catálogo `data/source_catalog.json` es **ficticio**: solo sirve para tests y ejemplos. Reemplazarlo por evidencia corporativa únicamente en una ruta privada externa. El adaptador QA lee `TIC_PRIVATE_QA_CONFIG` y DSN privados. No subas la configuración ni los tickets.

## Qué NO hacemos

- No incluimos los motores predictivos v0.1–v0.4 ni 50 procedimientos codificados como `if/else`.
- No usamos una puntuación sintética como prueba de resolución real.
- No damos permisos de administrador ni modificamos sistemas sin autorización.
- No publicamos datos personales, incidentes, soluciones humanas ni esquemas internos.
- No hacemos fine-tuning hasta disponer de expedientes revisados y un benchmark ciego de aceptación.

Ver [decisión de arquitectura](docs/ADR-0001-FOCO.md), [ruta de entrega](docs/ROADMAP.md) y [seguridad](SECURITY.md).

See [QA ITIL 2026 retrieval and live-support status](docs/OPERACION_ITIL_20261103_RECUPERACION_QA.md) for the November 3 operational evidence.
