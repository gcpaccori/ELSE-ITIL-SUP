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
