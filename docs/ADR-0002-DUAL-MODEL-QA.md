# ADR-0002 — Modelos complementarios y verificación de procedimientos

Estado: aceptado para laboratorio, NO producción. Fecha: 2026-11-02.

## Ruta

- Qwen 3.5 4B ofrece un primer procedimiento de investigación.
- Qwen 3.5 9B actúa como segundo candidato para los casos difíciles o rechazados.
- La selección acepta únicamente propuestas que pasan el verificador de RIV.
- Los modelos deben usar la misma huella de histórico y cohorte; la reanudación rechaza conjuntos modificados.
- No se certifican reparaciones ni se ejecutan cambios mediante la selección. Toda propuesta requiere revisión humana.

## Evidencia de la prueba de integración

- GPU 7: Qwen 3.5 4B; GPU 6: Qwen 3.5 9B.
- Cohorte: **12 incidentes ficticios de septiembre de 2026**, no tickets corporativos.
- Tras corrección de salida y una segunda oportunidad controlada: 4B = 11/12 planes aceptados; 9B = 12/12.
- Combinación: 12/12 planes revisables; 11 con validación estructural de ambos modelos.
- Resultados clasificados como procedimientos, **0 reparaciones certificadas**.
- Los contadores vLLM confirmaron solicitudes y tokens generados; el indicador puntual nvidia-smi mostró 0% durante parte de las pruebas, por lo que no se usa solo como evidencia de inferencia.

## Criterio pendiente para producción

No hay autorización verificada para usar las descripciones individuales de septiembre en un endpoint GPU externo al host QA. Los **545 registros reales** todavía no han sido procesados con RIV. La autorización debe acreditarse por un mecanismo externo verificable, no por el simple campo booleano privacy_reviewed. No cargar datos individuales en el repositorio público.

El ensemble NO constituye un árbitro causal. Ambos modelos pueden compartir un error; la adjudicación requiere evidencia externa y, para reparaciones, comprobación funcional.
