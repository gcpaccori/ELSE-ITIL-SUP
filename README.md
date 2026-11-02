# ELSE-ITIL-SUP — RIV (Investigación Resolutiva Verificable)

**Meta:** un especialista de Soporte TIC dirigido por un LLM que investiga incidentes, recupera antecedentes y propone procedimientos concretos, con pruebas y roles condicionados. No es un bot de etiquetas ni un sistema que ejecuta cambios sin autorización.

> Estado al 2026-11-02: prototipo experimental. **0 reparaciones reales certificadas por IA**. Los resultados sintéticos y las pruebas unitarias no constituyen tasas de resolución.

## Ruta de producto

- **Agente:** el LLM formula hipótesis y solicita herramientas.
- **Memoria:** SQLite/FTS5, antecedentes con fechas, provenance y revisión independiente.
- **Fuentes:** catálogo privado verificado, relaciones, roles y controles de acceso.
- **Conector QA:** únicamente consultas registradas, parametrizadas, con identidad corporativa de solo lectura.
- **Verificador:** rechaza evidencia inventada, SQL no verificable y afirmaciones de resolución sin prueba de cierre.
- **Evaluación:** casos de 2026 con solución humana oculta; revisión independiente del diagnóstico y el procedimiento.

## Decisión: qué no integrar

No se llevan al runtime los predictores v0.1–v0.4, las 50 reglas de respuesta fija, los motores duplicados v0.5/v0.6, la orquestación multiagente permanente ni el fine-tuning sobre soluciones no adjudicadas. Se conservan solamente como historia de investigación, **fuera del ejecutable**.

La rama pública debe contener **solo código depurado y ejemplos ficticios**. Nunca expedientes, soluciones históricas reales, credenciales, DNS/hosts internos ni el catálogo completo de bases de ELSE. La configuración institucional se mantiene fuera de Git.

## Verificación

```bash
python -m pip install -e '.[test]'
python -m pytest -q
```

Un test aprobado acredita funcionalidad del código, **no** resolución de incidentes reales.

Ver documentación de arquitectura, seguridad y fases de aceptación junto con el código consolidado.
