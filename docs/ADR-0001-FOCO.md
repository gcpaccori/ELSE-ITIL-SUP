# ADR-0001 — Una ruta resolutiva, no nueve motores

**Estado:** adoptado para el prototipo público — 2026-11-02.

## Decisión

El **único runtime de producción aspiracional** será el agente LLM con las herramientas: `search_precedents`, `find_sources`, `describe_source`, `inspect_relation`, `query_live` (registrada). La memoria no adjudica soluciones por frecuencia. La IA formula hipótesis y planes; el verificador comprueba referencias, autorización, acceso y pruebas de cierre. Sin evidencia suficiente, devuelve una investigación específica y un responsable condicionado.

## Integrar ahora

- Memoria temporal y lexical/FTS; incorporar reranking híbrido solo si mejora benchmark ciego.
- Catálogo con metadata verificada, claves/joins válidos, temporalidad y estado de permisos.
- LLM único con complejidad adaptativa, escalamiento selectivo si hay discrepancia.
- Read-only QA mediante queries registradas y principal corporativo autorizado.
- Procedimientos condicionados, handoff por dominio, verificación posterior.
- Replay ciego y métricas de utilidad revisadas por ingeniería.

## No integrar / dejar como legado

| Pieza | Decisión | Razón |
|---|---|---|
| v0.1–v0.4 predictor, dashboards y heurísticas de consistencia | Archivar, no runtime | KPI y etiquetas no resuelven incidentes |
| 50 reglas de actuación fija | Documentación de dominios, no decisiones | Impiden generalización; riesgos de respuestas genéricas |
| v0.5/v0.6 buscadores y ensayos separados | Reemplazados por memoria canónica | Duplicidad de índices y semánticas |
| Multiagente permanente de muchos modelos | Posponer | Latencia, costo, conflictos y falta de evidencia de mejora |
| Fine-tuning masivo con 214k textos no adjudicados | Posponer | Soluciones antiguas, breves, ambiguas o erróneas |
| Puntuación automática sintética como KPI de éxito | No usar | Falló en detectar SQL/roles incorrectos |
| Motor paralelo de evaluación como resolver de producción | Prohibir | Evalúa, no actúa ni certifica corrección |

## Condición para promoción

545/545 expedientes de septiembre 2026 (o un conjunto autorizado equivalente) procesados con solución oculta; revisión por profesionales de muestras estratificadas; cero SQL de escritura; cero acceso denegado reintentado; auditoría de falsos positivos y procedimiento reproducible. La prueba de cierre es independiente del texto histórico.
